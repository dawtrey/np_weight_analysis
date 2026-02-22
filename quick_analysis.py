#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from pathlib import Path
import json

G = 9.81

class TCXAnalyzer:
    def __init__(self, tcx_file_path):
        self.file_path = tcx_file_path
        self.trackpoints = []
        self.parse_tcx()
        
    def parse_tcx(self):
        tree = ET.parse(self.file_path)
        root = tree.getroot()
        ns = {
            'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
            'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
        }
        
        for tp in root.findall('.//ns:Trackpoint', ns):
            try:
                time_elem = tp.find('ns:Time', ns)
                position = tp.find('ns:Position', ns)
                elev_elem = tp.find('ns:AltitudeMeters', ns)
                dist_elem = tp.find('ns:DistanceMeters', ns)
                speed = 0
                tpx = tp.find('.//ns3:TPX', ns)
                if tpx is not None:
                    speed_elem = tpx.find('ns3:Speed', ns)
                    if speed_elem is not None and speed_elem.text:
                        speed = float(speed_elem.text)
                if time_elem and position and elev_elem and dist_elem:
                    lat = float(position.find('ns:LatitudeDegrees', ns).text)
                    lon = float(position.find('ns:LongitudeDegrees', ns).text)
                    self.trackpoints.append({
                        'time': time_elem.text,
                        'lat': lat, 'lon': lon,
                        'elev': float(elev_elem.text),
                        'dist': float(dist_elem.text),
                        'speed': speed
                    })
            except: pass

def analyze(analyzer, rider_mass=75.0):
    if len(analyzer.trackpoints) < 2:
        return None
    
    results = {'extra_power': [], 'elev': [], 'vel': []}
    total_elev = 0
    
    for i in range(1, len(analyzer.trackpoints)):
        curr = analyzer.trackpoints[i]
        prev = analyzer.trackpoints[i-1]
        
        v_curr = curr['speed']
        v_prev = prev['speed']
        e_delta = curr['elev'] - prev['elev']
        
        if e_delta > 0:
            total_elev += e_delta
        
        ke_delta = 0.5 * (v_curr**2 - v_prev**2)
        pe_delta = 0
        if e_delta > 0:
            pe_delta = G * e_delta
        
        total_power = max(0, ke_delta + pe_delta)
        results['extra_power'].append(total_power)
        results['vel'].append(v_curr * 3.6)
        results['elev'].append(e_delta)
    
    power_arr = results['extra_power']
    p4 = [p**4 for p in power_arr]
    np_val = (sum(p4) / len(p4))**0.25 if p4 else 0
    avg_p = sum(power_arr) / len(power_arr) if power_arr else 0
    
    return {
        'file': Path(analyzer.file_path).name,
        'dur_s': len(analyzer.trackpoints) - 1,
        'dist': analyzer.trackpoints[-1]['dist'] / 1000,
        'elev': total_elev,
        'speed_avg': sum(results['vel']) / len(results['vel']) if results['vel'] else 0,
        'speed_max': max(results['vel']) if results['vel'] else 0,
        'np_w': np_val,
        'avg_w': avg_p,
        'max_w': max(power_arr) if power_arr else 0,
        'energy_kcal': sum(power_arr) / 4184
    }

# Run analysis
tcx_files = list(Path('/workspaces/np_weight_analysis').glob('*.tcx'))
results = []

for f in tcx_files:
    try:
        analyzer = TCXAnalyzer(str(f))
        res = analyze(analyzer)
        if res:
            results.append(res)
    except:
        pass

# Save to file
with open('/workspaces/np_weight_analysis/results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("Analysis complete. Results saved.")
for r in results:
    print(f"{r['file']}: NP={r['np_w']:.1f}W, Avg={r['avg_w']:.1f}W")
