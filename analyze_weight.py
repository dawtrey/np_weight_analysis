#!/usr/bin/env python3
"""
TCX Weight Power Analysis - Standalone script
Analyzes the impact of 1kg on normalized power output in bike races
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass
import json

# Physical constants
G = 9.81  # gravitational acceleration (m/s²)

@dataclass
class TrackPoint:
    time: str
    latitude: float
    longitude: float
    elevation: float
    distance: float
    speed: float

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
                
                if (time_elem is not None and position is not None and 
                    elev_elem is not None and dist_elem is not None):
                    
                    lat = float(position.find('ns:LatitudeDegrees', ns).text)
                    lon = float(position.find('ns:LongitudeDegrees', ns).text)
                    
                    tp_obj = TrackPoint(
                        time=time_elem.text,
                        latitude=lat,
                        longitude=lon,
                        elevation=float(elev_elem.text),
                        distance=float(dist_elem.text),
                        speed=speed
                    )
                    self.trackpoints.append(tp_obj)
            except (ValueError, AttributeError):
                continue

def analyze_power_impact(analyzer, rider_mass=75.0, extra_weight=1.0):
    if len(analyzer.trackpoints) < 2:
        return None
    
    total_mass = rider_mass + extra_weight
    base_mass = rider_mass
    
    extra_kinetic_power = []
    extra_potential_power = []
    total_extra_power = []
    velocities = []
    
    prev_tp = analyzer.trackpoints[0]
    total_elev_gain = 0
    
    for tp in analyzer.trackpoints[1:]:
        dt = 1.0
        
        v_current = tp.speed
        v_prev = prev_tp.speed
        elev_delta = tp.elevation - prev_tp.elevation
        
        if elev_delta > 0:
            total_elev_gain += elev_delta
        
        # Kinetic energy change
        ke_change_base = 0.5 * base_mass * (v_current**2 - v_prev**2)
        ke_change_extra = 0.5 * total_mass * (v_current**2 - v_prev**2)
        kinetic_pw_delta = (ke_change_extra - ke_change_base) / dt
        
        # Potential energy change (uphill only)
        potential_pw_delta = 0
        if elev_delta > 0:
            pe_change = (total_mass - base_mass) * G * elev_delta / dt
            potential_pw_delta = pe_change
        
        # Total extra power (worst-case)
        total_delta = max(0, kinetic_pw_delta + potential_pw_delta)
        
        extra_kinetic_power.append(kinetic_pw_delta)
        extra_potential_power.append(potential_pw_delta)
        total_extra_power.append(total_delta)
        velocities.append(v_current)
        
        prev_tp = tp
    
    # Calculate normalized power
    if len(total_extra_power) > 0:
        power_4 = [max(0, p)**4 for p in total_extra_power]
        mean_power_4 = sum(power_4) / len(power_4)
        np_extra = mean_power_4**0.25 if mean_power_4 > 0 else 0
    else:
        np_extra = 0
    
    avg_power_extra = sum(total_extra_power) / len(total_extra_power) if total_extra_power else 0
    max_power_extra = max(total_extra_power) if total_extra_power else 0
    total_energy = sum(total_extra_power) if total_extra_power else 0
    duration_seconds = len(analyzer.trackpoints) - 1
    
    return {
        'file_name': Path(analyzer.file_path).name,
        'duration_seconds': duration_seconds,
        'distance_km': analyzer.trackpoints[-1].distance / 1000,
        'elevation_gain_m': total_elev_gain,
        'max_speed_kmh': max(velocities) * 3.6 if velocities else 0,
        'avg_speed_kmh': (sum(velocities) / len(velocities) * 3.6) if velocities else 0,
        'normalized_power_watts': np_extra,
        'average_power_watts': avg_power_extra,
        'max_power_watts': max_power_extra,
        'total_energy_kcal': total_energy / 4184,
        'rider_mass_kg': rider_mass,
        'extra_weight_kg': extra_weight
    }

# Main execution
def main():
    tcx_files = list(Path('.').glob('*.tcx'))
    
    print("=" * 80)
    print("TCX BIKE RACE WEIGHT POWER ANALYSIS")
    print("Impact of 1kg extra weight on normalized power output")
    print("=" * 80)
    print(f"\nFound {len(tcx_files)} TCX files\n")
    
    results = []
    for tcx_file in tcx_files:
        try:
            print(f"Analyzing: {tcx_file.name}")
            analyzer = TCXAnalyzer(str(tcx_file))
            result = analyze_power_impact(analyzer)
            
            if result:
                results.append(result)
                print(f"  ✓ Duration: {result['duration_seconds']/60:.1f} min")
                print(f"  ✓ Distance: {result['distance_km']:.1f} km")
                print(f"  ✓ Elevation: {result['elevation_gain_m']:.0f}m")
                print(f"  ✓ Speed: {result['avg_speed_kmh']:.1f}/{result['max_speed_kmh']:.1f} km/h")
                print(f"\n  => 1kg Extra Weight Impact:")
                print(f"     Normalized Power: {result['normalized_power_watts']:.1f}W")
                print(f"     Average Power:    {result['average_power_watts']:.1f}W") 
                print(f"     Max Power:        {result['max_power_watts']:.1f}W")
                print(f"     Total Energy:     {result['total_energy_kcal']:.1f} kcal\n")
        except Exception as e:
            print(f"  ✗ Error: {e}\n")
    
    # Summary
    if results:
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        for i, r in enumerate(results, 1):
            print(f"\n{i}. {r['file_name']}")
            print(f"   Duration:         {r['duration_seconds']/60:>7.1f} minutes")
            print(f"   Distance:         {r['distance_km']:>7.1f} km")
            print(f"   Elevation Gain:   {r['elevation_gain_m']:>7.0f} m")
            print(f"   Avg/Max Speed:    {r['avg_speed_kmh']:>6.1f}/{r['max_speed_kmh']:.1f} km/h")
            print(f"   ")
            print(f"   1kg EXTRA WEIGHT IMPACT (WORST-CASE):")
            print(f"   └─ Normalized Power: {r['normalized_power_watts']:>6.1f}W")
            print(f"   └─ Average Power:    {r['average_power_watts']:>6.1f}W")
            print(f"   └─ Peak Power:       {r['max_power_watts']:>6.1f}W")
            print(f"   └─ Total Energy:     {r['total_energy_kcal']:>6.1f} kcal")
        
        # Save JSON results
        output_file = 'weight_analysis_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n{'='*80}")
        print(f"Results saved to: {output_file}")
        print("="*80)
        
        # Analysis notes
        print("\nANALYSIS METHODOLOGY:")
        print("-" * 80)
        print("""
This worst-case scenario analysis calculates extra power needed for 1kg by:

1. KINETIC ENERGY (acceleration/deceleration):
   ΔKE = ½m(v₂² - v₁²) → Power = ΔKE/Δt
   The 1kg must accelerate/decelerate with you

2. GRAVITATIONAL POTENTIAL ENERGY (climbing):
   ΔPE = mg·Δh → Power = mg·Δh/Δt  
   Applied only for uphill segments (worst-case)

3. NORMALIZED POWER:
   NP = ⁴√(mean(power⁴))
   Industry standard that better reflects effort than average

KEY ASSUMPTIONS (WORST-CASE):
• No downhill benefits (energy is dissipated, not recovered)
• Constant rider mass (75kg assumption)
• No aerodynamic penalty changes calculated
• Pure physics-based energy model
""")

if __name__ == '__main__':
    main()
