#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from pathlib import Path
import json
import sys

G = 9.81

class TrackPoint:
    def __init__(self, time, elevation, speed, power=None):
        self.time = time
        self.elevation = elevation
        self.speed = speed
        self.power = power if power is not None else 0

def parse_tcx(filepath):
    trackpoints = []
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {
        'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
        'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
    }
    
    for tp_elem in root.findall('.//ns:Trackpoint', ns):
        try:
            time_elem = tp_elem.find('ns:Time', ns)
            elev_elem = tp_elem.find('ns:AltitudeMeters', ns)
            speed = 0.0
            power = None
            
            tpx = tp_elem.find('.//ns3:TPX', ns)
            if tpx is not None:
                speed_elem = tpx.find('ns3:Speed', ns)
                if speed_elem is not None and speed_elem.text:
                    speed = float(speed_elem.text)
                power_elem = tpx.find('ns3:Watts', ns)
                if power_elem is not None and power_elem.text:
                    power = float(power_elem.text)
            
            if time_elem is not None and elev_elem is not None:
                tp = TrackPoint(time_elem.text, float(elev_elem.text), speed, power)
                trackpoints.append(tp)
        except:
            pass
    
    return trackpoints

def analyze(trackpoints, extra_kg=1.0, rider_mass=75.0):
    if len(trackpoints) < 2:
        return None
    
    speeds = []
    elevations = []
    measured_powers = []
    ke_costs = []
    pe_costs = []
    total_extra_costs = []
    new_powers = []
    
    total_elev = 0.0
    
    for i in range(1, len(trackpoints)):
        curr = trackpoints[i]
        prev = trackpoints[i-1]
        
        v_curr = curr.speed
        v_prev = prev.speed
        speeds.append(v_curr)
        
        elev_delta = curr.elevation - prev.elevation
        elevations.append(curr.elevation)
        if elev_delta > 0:
            total_elev += elev_delta
        
        ke = 0.5 * extra_kg * (v_curr**2 - v_prev**2)
        ke_costs.append(ke)
        
        pe = 0
        if elev_delta > 0:
            pe = extra_kg * G * elev_delta
        pe_costs.append(pe)
        
        extra = max(0, ke + pe)
        total_extra_costs.append(extra)
        
        if curr.power:
            measured_powers.append(curr.power)
            new_powers.append(curr.power + extra)
        else:
            measured_powers.append(0)
            new_powers.append(extra)
    
    duration_sec = len(trackpoints) - 1
    total_energy_j = sum(total_extra_costs)
    total_energy_kcal = total_energy_j / 4184
    avg_extra_power = total_energy_j / duration_sec if duration_sec > 0 else 0
    
    has_power = any(p > 0 for p in measured_powers)
    
    if has_power:
        meas_w_data = [p for p in measured_powers if p > 0]
        avg_orig = sum(meas_w_data) / len(meas_w_data) if meas_w_data else 0
        new_w_data = [new_powers[i] for i in range(len(measured_powers)) if measured_powers[i] > 0]
        avg_new = sum(new_w_data) / len(new_w_data) if new_w_data else 0
        
        if meas_w_data:
            p4 = [p**4 for p in meas_w_data]
            np_orig = (sum(p4) / len(p4)) ** 0.25
        else:
            np_orig = 0
        
        if new_w_data:
            p4_new = [p**4 for p in new_w_data]
            np_new = (sum(p4_new) / len(p4_new)) ** 0.25
        else:
            np_new = 0
    else:
        avg_orig = None
        avg_new = None
        if total_extra_costs:
            p4 = [max(0, p)**4 for p in total_extra_costs]
            np_orig = 0
            np_new = (sum(p4) / len(p4)) ** 0.25 if p4 else 0
        else:
            np_orig = 0
            np_new = 0
    
    return {
        'duration_sec': duration_sec,
        'duration_min': duration_sec / 60,
        'elev_gain': total_elev,
        'speed_avg_kmh': (sum(speeds) / len(speeds) * 3.6) if speeds else 0,
        'speed_max_kmh': (max(speeds) * 3.6) if speeds else 0,
        'energy_j': total_energy_j,
        'energy_kcal': total_energy_kcal,
        'avg_extra_power': avg_extra_power,
        'avg_orig': avg_orig,
        'avg_new': avg_new,
        'np_orig': np_orig,
        'np_new': np_new,
        'has_power': has_power
    }

# Main execution
tcx_dir = Path('/workspaces/np_weight_analysis')
tcx_files = sorted(tcx_dir.glob('*.tcx'))

output_lines = []
output_lines.append("\n" + "="*110)
output_lines.append("PRECISE RACE-BY-RACE WEIGHT ANALYSIS (1kg Extra)")
output_lines.append("="*110)

results = []

for tcx_file in tcx_files:
    try:
        trackpoints = parse_tcx(str(tcx_file))
        if len(trackpoints) > 1:
            analysis = analyze(trackpoints)
            results.append((tcx_file.name, analysis))
            output_lines.append(f"\n✓ {tcx_file.name}")
        else:
            output_lines.append(f"\n✗ {tcx_file.name} (insufficient data)")
    except Exception as e:
        output_lines.append(f"\n✗ {tcx_file.name} (error: {str(e)[:50]})")

output_lines.append("\n" + "="*110)
output_lines.append("DETAILED RESULTS")
output_lines.append("="*110)

for fname, analysis in results:
    output_lines.append(f"\n{fname}")
    output_lines.append("-" * 110)
    output_lines.append(f"Duration:        {analysis['duration_min']:.1f} minutes ({analysis['duration_sec']} seconds)")
    output_lines.append(f"Speed:           {analysis['speed_avg_kmh']:.1f} km/h avg (max {analysis['speed_max_kmh']:.1f} km/h)")
    output_lines.append(f"Elevation gain:  {analysis['elev_gain']:.0f} m")
    output_lines.append(f"")
    output_lines.append(f"1kg ENERGY COST - TOTAL:")
    output_lines.append(f"  Total energy:        {analysis['energy_j']:.0f} J ({analysis['energy_kcal']:.2f} kcal)")
    output_lines.append(f"  Average extra power: {analysis['avg_extra_power']:.2f} W")
    output_lines.append(f"")
    
    if analysis['has_power']:
        output_lines.append(f"POWER ANALYSIS (with measured power data):")
        output_lines.append(f"  Original avg power:      {analysis['avg_orig']:.1f} W")
        output_lines.append(f"  With 1kg avg power:      {analysis['avg_new']:.1f} W")
        output_lines.append(f"  Increase in avg power:   {analysis['avg_new'] - analysis['avg_orig']:.1f} W")
        output_lines.append(f"")
        output_lines.append(f"  Original NP:             {analysis['np_orig']:.1f} W")
        output_lines.append(f"  With 1kg NP:             {analysis['np_new']:.1f} W")
        output_lines.append(f"  Increase in NP:          {analysis['np_new'] - analysis['np_orig']:.1f} W")
        if analysis['np_orig'] > 0:
            pct = ((analysis['np_new'] - analysis['np_orig']) / analysis['np_orig']) * 100
            output_lines.append(f"  Percentage increase:     {pct:.2f}%")
    else:
        output_lines.append(f"(No measured power data - calculated from speed/elevation only)")
        output_lines.append(f"  Estimated NP cost:   {analysis['np_new']:.1f} W")

output_lines.append("\n" + "="*110)
output_lines.append("SUMMARY TABLE")
output_lines.append("="*110)
output_lines.append(f"{'Race':<50} {'Duration':<12} {'Avg Power':<15} {'NP':<15} {'NP + 1kg':<15} {'Increase':<10}")
output_lines.append("-" * 110)

for fname, analysis in results:
    short_name = fname[:45]
    dur = f"{analysis['duration_min']:.0f} min"
    if analysis['has_power']:
        avg_p = f"{analysis['avg_orig']:.0f}W → {analysis['avg_new']:.0f}W"
        np_p = f"{analysis['np_orig']:.0f}W"
        np_new = f"{analysis['np_new']:.0f}W"
        inc = f"+{analysis['np_new']-analysis['np_orig']:.1f}W"
    else:
        avg_p = "N/A"
        np_p = f"(calc)"
        np_new = f"{analysis['np_new']:.1f}W"
        inc = f"+{analysis['np_new']:.1f}W"
    output_lines.append(f"{short_name:<50} {dur:<12} {avg_p:<15} {np_p:<15} {np_new:<15} {inc:<10}")

output_lines.append("="*110)

# Write to file
output_text = "\n".join(output_lines)
with open('/workspaces/np_weight_analysis/race_analysis_output.txt', 'w') as f:
    f.write(output_text)

print(output_text)

# Save JSON
json_results = []
for fname, analysis in results:
    json_results.append({
        'filename': fname,
        'duration_minutes': round(analysis['duration_min'], 1),
        'duration_seconds': analysis['duration_sec'],
        'elevation_gain_m': round(analysis['elev_gain'], 0),
        'speed_avg_kmh': round(analysis['speed_avg_kmh'], 1),
        'speed_max_kmh': round(analysis['speed_max_kmh'], 1),
        'energy_cost_j': round(analysis['energy_j'], 0),
        'energy_cost_kcal': round(analysis['energy_kcal'], 2),
        'avg_power_increase_w': round(analysis['avg_extra_power'], 2),
        'avg_power_original_w': round(analysis['avg_orig'], 1) if analysis['avg_orig'] else None,
        'avg_power_with_1kg_w': round(analysis['avg_new'], 1) if analysis['avg_new'] else None,
        'np_original_w': round(analysis['np_orig'], 1),
        'np_with_1kg_w': round(analysis['np_new'], 1),
        'np_increase_w': round(analysis['np_new'] - analysis['np_orig'], 1),
        'has_measured_power': analysis['has_power']
    })

with open('/workspaces/np_weight_analysis/race_analysis.json', 'w') as f:
    json.dump(json_results, f, indent=2)

print(f"\nResults saved to race_analysis.json and race_analysis_output.txt")
