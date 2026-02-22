#!/usr/bin/env python3
"""
Precise Race-by-Race Weight Analysis
Calculates exact energy costs, power changes, and normalized power for each TCX file.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import json

# Physical constants
G = 9.81

class TrackPoint:
    def __init__(self, time, elevation, speed, power=None):
        self.time = time
        self.elevation = elevation
        self.speed = speed
        self.power = power if power is not None else 0

class TCXParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = Path(filepath).name
        self.trackpoints = []
        self.parse()
    
    def parse(self):
        """Parse TCX file and extract trackpoints."""
        tree = ET.parse(self.filepath)
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
                tpx = tp_elem.find('.//ns3:TPX', ns)
                if tpx is not None:
                    speed_elem = tpx.find('ns3:Speed', ns)
                    if speed_elem is not None and speed_elem.text:
                        speed = float(speed_elem.text)
                
                # Try to get power
                power = None
                if tpx is not None:
                    power_elem = tpx.find('ns3:Watts', ns)
                    if power_elem is not None and power_elem.text:
                        power = float(power_elem.text)
                
                if time_elem is not None and elev_elem is not None:
                    tp = TrackPoint(
                        time=time_elem.text,
                        elevation=float(elev_elem.text),
                        speed=speed,
                        power=power
                    )
                    self.trackpoints.append(tp)
            except (ValueError, AttributeError):
                pass

def calculate_race_analysis(parser, rider_mass=75.0, extra_kg=1.0):
    """
    Calculate complete race analysis including exact energy costs and normalized power.
    """
    if len(parser.trackpoints) < 2:
        return None
    
    total_mass = rider_mass
    total_mass_plus = rider_mass + extra_kg
    
    # Arrays to store calculations
    speeds = []
    elevations = []
    measured_powers = []
    ke_costs = []
    pe_costs = []
    total_extra_power_costs = []
    new_total_powers = []
    
    total_elev_gain = 0
    
    # First pass: calculate per-second costs and collect data
    for i in range(1, len(parser.trackpoints)):
        curr = parser.trackpoints[i]
        prev = parser.trackpoints[i-1]
        
        # Velocity change
        v_curr = curr.speed
        v_prev = prev.speed
        speeds.append(v_curr)
        
        # Elevation change
        elev_delta = curr.elevation - prev.elevation
        elevations.append(curr.elevation)
        if elev_delta > 0:
            total_elev_gain += elev_delta
        
        # Kinetic energy cost for extra kg
        # ΔKE = ½m(v₂² - v₁²), Power = ΔKE/Δt (where Δt = 1 sec)
        ke_delta = 0.5 * extra_kg * (v_curr**2 - v_prev**2)
        ke_costs.append(ke_delta)
        
        # Potential energy cost for extra kg (uphill only, worst-case)
        pe_delta = 0
        if elev_delta > 0:
            pe_delta = extra_kg * G * elev_delta
        pe_costs.append(pe_delta)
        
        # Total extra power for 1kg (worst-case: no downhill benefit)
        extra_power = max(0, ke_delta + pe_delta)
        total_extra_power_costs.append(extra_power)
        
        # Measured power (if available)
        if curr.power:
            measured_powers.append(curr.power)
            # New total power = old + extra cost
            new_power = curr.power + extra_power
            new_total_powers.append(new_power)
        else:
            measured_powers.append(0)
            new_total_powers.append(extra_power)
    
    # Remove first point (no measurement yet)
    speeds = speeds[1:] if len(speeds) > 1 else speeds
    elevations = elevations[1:] if len(elevations) > 1 else elevations
    
    # Calculate summary statistics
    duration_sec = len(parser.trackpoints) - 1
    duration_min = duration_sec / 60
    duration_hr = duration_min / 60
    
    # Total energy costs
    total_energy_cost_joules = sum(total_extra_power_costs)
    total_energy_cost_kcal = total_energy_cost_joules / 4184
    
    # Average power (only for measured power points)
    has_measured_power = any(p > 0 for p in measured_powers)
    
    if has_measured_power:
        # Calculate original and new average power
        measured_power_with_data = [p for p in measured_powers if p > 0]
        avg_original_power = sum(measured_power_with_data) / len(measured_power_with_data) if measured_power_with_data else 0
        
        # New powers corresponding to measured power readings
        new_powers_with_data = [new_total_powers[i] for i in range(len(measured_powers)) if measured_powers[i] > 0]
        avg_new_power = sum(new_powers_with_data) / len(new_powers_with_data) if new_powers_with_data else 0
        
        # Increase in average power
        avg_power_increase = avg_new_power - avg_original_power
        
        # Calculate normalized power for original
        if measured_power_with_data:
            power_4 = [p**4 for p in measured_power_with_data]
            mean_p4 = sum(power_4) / len(power_4)
            np_original = mean_p4 ** 0.25
        else:
            np_original = 0
        
        # Calculate normalized power for new (1kg heavier)
        if new_powers_with_data:
            new_power_4 = [p**4 for p in new_powers_with_data]
            mean_new_p4 = sum(new_power_4) / len(new_power_4)
            np_new = mean_new_p4 ** 0.25
        else:
            np_new = 0
    else:
        # No measured power data - use calculated extra cost only
        avg_original_power = None
        avg_new_power = None
        avg_power_increase = sum(total_extra_power_costs) / len(total_extra_power_costs) if total_extra_power_costs else 0
        
        # NP from pure extra cost (won't have measured power baseline)
        if total_extra_power_costs:
            power_4 = [p**4 for p in total_extra_power_costs]
            mean_p4 = sum(power_4) / len(power_4)
            np_original = 0  # Not applicable
            np_new = mean_p4 ** 0.25
        else:
            np_original = 0
            np_new = 0
    
    return {
        'filename': parser.filename,
        'duration': {
            'seconds': duration_sec,
            'minutes': duration_min,
            'hours': duration_hr
        },
        'elevation': {
            'gain_total': total_elev_gain,
            'samples': len(elevations)
        },
        'speed': {
            'max_ms': max(speeds) if speeds else 0,
            'max_kmh': max(speeds) * 3.6 if speeds else 0,
            'avg_ms': sum(speeds) / len(speeds) if speeds else 0,
            'avg_kmh': (sum(speeds) / len(speeds) * 3.6) if speeds else 0
        },
        'energy': {
            'total_cost_joules': total_energy_cost_joules,
            'total_cost_kcal': total_energy_cost_kcal
        },
        'power': {
            'avg_original': avg_original_power,
            'avg_with_1kg': avg_new_power,
            'avg_increase': avg_power_increase,
            'np_original': np_original,
            'np_with_1kg': np_new,
            'has_measured_power': has_measured_power
        }
    }

def format_summary_table(results):
    """Format results as readable table."""
    print("\n" + "="*100)
    print("RACE-BY-RACE WEIGHT ANALYSIS SUMMARY (1kg Extra)")
    print("="*100)
    
    for result in results:
        filename = result['filename']
        dur_min = result['duration']['minutes']
        dur_sec = result['duration']['seconds']
        
        print(f"\n{filename}")
        print("-" * 100)
        
        print(f"Duration: {dur_min:.1f} minutes ({dur_sec} seconds)")
        
        speed_result = result['speed']
        print(f"Speed: {speed_result['avg_kmh']:.1f} km/h average (max {speed_result['max_kmh']:.1f} km/h)")
        
        elev = result['elevation']
        print(f"Elevation gain: {elev['gain_total']:.0f} m")
        
        energy = result['energy']
        print(f"\n1kg ENERGY COST:")
        print(f"  Total energy: {energy['total_cost_joules']:.0f} J ({energy['total_cost_kcal']:.2f} kcal)")
        print(f"  Average extra power: {result['power']['avg_increase']:.2f} W")
        
        if result['power']['has_measured_power']:
            print(f"\nPOWER PROFILE (with measured power data):")
            print(f"  Original avg power:       {result['power']['avg_original']:.1f} W")
            print(f"  With 1kg avg power:       {result['power']['avg_with_1kg']:.1f} W")
            print(f"  Increase:                 {result['power']['avg_increase']:.1f} W")
            print(f"\n  Original normalized power: {result['power']['np_original']:.1f} W")
            print(f"  With 1kg normalized power: {result['power']['np_with_1kg']:.1f} W")
            print(f"  NP increase:              {result['power']['np_with_1kg'] - result['power']['np_original']:.1f} W")
            
            if result['power']['np_original'] > 0:
                pct_increase = (result['power']['np_with_1kg'] - result['power']['np_original']) / result['power']['np_original'] * 100
                print(f"  Percentage increase:      {pct_increase:.2f}%")
        else:
            print(f"\nNO MEASURED POWER DATA (speed-based calculation only):")
            print(f"  Estimated extra NP from KE/PE: {result['power']['np_with_1kg']:.1f} W")

def main():
    """Main analysis."""
    tcx_dir = Path('/workspaces/np_weight_analysis')
    tcx_files = sorted(tcx_dir.glob('*.tcx'))
    
    if not tcx_files:
        print("No TCX files found!")
        return
    
    print(f"Found {len(tcx_files)} TCX files\n")
    
    results = []
    
    for tcx_file in tcx_files:
        print(f"Processing: {tcx_file.name}...", end=" ")
        try:
            parser = TCXParser(str(tcx_file))
            analysis = calculate_race_analysis(parser)
            
            if analysis:
                results.append(analysis)
                print(f"✓ ({len(parser.trackpoints)} trackpoints)")
            else:
                print("✗ (parsing failed)")
        except Exception as e:
            print(f"✗ (error: {e})")
    
    # Display summary table
    if results:
        format_summary_table(results)
        
        # Save detailed results to JSON
        json_output = []
        for r in results:
            json_output.append({
                'filename': r['filename'],
                'duration_minutes': r['duration']['minutes'],
                'duration_seconds': r['duration']['seconds'],
                'elevation_gain_m': r['elevation']['gain_total'],
                'speed_avg_kmh': r['speed']['avg_kmh'],
                'speed_max_kmh': r['speed']['max_kmh'],
                'energy_cost_joules': r['energy']['total_cost_joules'],
                'energy_cost_kcal': r['energy']['total_cost_kcal'],
                'avg_power_original_w': r['power']['avg_original'],
                'avg_power_with_1kg_w': r['power']['avg_with_1kg'],
                'avg_power_increase_w': r['power']['avg_increase'],
                'normalized_power_original_w': r['power']['np_original'],
                'normalized_power_with_1kg_w': r['power']['np_with_1kg'],
                'has_measured_power': r['power']['has_measured_power']
            })
        
        output_file = tcx_dir / 'detailed_race_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(json_output, f, indent=2)
        
        print(f"\n{'='*100}")
        print(f"Detailed results saved to: detailed_race_analysis.json")
        print("="*100)

if __name__ == '__main__':
    main()
