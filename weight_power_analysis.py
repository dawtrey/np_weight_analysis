"""
Weight power analysis tool for TCX bike race files.

This tool analyzes the impact of an additional 1kg on normalized power output
by examining kinetic and gravitational potential energy changes.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import json
import statistics

# Physical constants
G = 9.81  # gravitational acceleration (m/s²)
RHO_AIR = 1.225  # air density at sea level (kg/m³)
CD = 1.1  # drag coefficient for road bike
A = 0.4  # frontal area (m²)
CRR = 0.004  # coefficient of rolling resistance

@dataclass
class TrackPoint:
    """A single trackpoint from the TCX file."""
    time: str
    latitude: float
    longitude: float
    elevation: float
    distance: float
    speed: float
    cadence: int = None
    
class TCXAnalyzer:
    """Parses and analyzes TCX bike race files."""
    
    def __init__(self, tcx_file_path: str):
        """Initialize the analyzer with a TCX file."""
        self.file_path = tcx_file_path
        self.trackpoints = []
        self.parse_tcx()
        
    def parse_tcx(self):
        """Parse TCX file and extract trackpoints."""
        tree = ET.parse(self.file_path)
        root = tree.getroot()
        
        # Define namespaces
        ns = {
            'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
            'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
        }
        
        # Find all trackpoints
        for tp in root.findall('.//ns:Trackpoint', ns):
            try:
                time_elem = tp.find('ns:Time', ns)
                position = tp.find('ns:Position', ns)
                elev_elem = tp.find('ns:AltitudeMeters', ns)
                dist_elem = tp.find('ns:DistanceMeters', ns)
                cadence_elem = tp.find('ns:Cadence', ns)
                
                # Get speed from extensions
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
                        speed=speed,
                        cadence=int(cadence_elem.text) if cadence_elem is not None and cadence_elem.text else None
                    )
                    self.trackpoints.append(tp_obj)
            except (ValueError, AttributeError) as e:
                continue
    
    def calculate_power_impact(self, rider_mass: float = 75.0, extra_weight: float = 1.0):
        """
        Calculate the power impact of extra weight due to kinetic and gravitational PE changes.
        
        Args:
            rider_mass: rider + bike mass in kg (default 75 kg)
            extra_weight: additional weight in kg (default 1 kg)
        
        Returns:
            dict containing analysis results
        """
        if len(self.trackpoints) < 2:
            return None
        
        total_mass = rider_mass + extra_weight
        base_mass = rider_mass
        
        # Initialize tracking variables
        kinetic_energy_extra = []  # watts needed for kinetic energy
        potential_energy_extra = []  # watts needed for gravitational PE
        total_extra_power = []  # total watts needed
        timestamps = []
        velocities = []
        elevation_gains = []
        
        prev_tp = self.trackpoints[0]
        total_elev_gain = 0
        
        for i, tp in enumerate(self.trackpoints[1:], start=1):
            # Time difference (should be 1 second for most TCX files)
            dt = 1.0  # assuming 1 second intervals
            
            # Current state
            v_current = tp.speed  # m/s
            v_prev = prev_tp.speed  # m/s
            elev_current = tp.elevation
            elev_prev = prev_tp.elevation
            
            # Calculate elevation gain (only count gains, worst case)
            elev_delta = elev_current - elev_prev
            if elev_delta > 0:
                total_elev_gain += elev_delta
            
            # Kinetic energy change: ½m(v² - v₀²)
            # Power = ΔKE / Δt
            ke_base = 0.5 * base_mass * (v_current**2 - v_prev**2) / dt if dt > 0 else 0
            ke_with_extra = 0.5 * total_mass * (v_current**2 - v_prev**2) / dt if dt > 0 else 0
            ke_delta = ke_with_extra - ke_base
            
            # Gravitational PE change: mg*Δh
            # Power = ΔPE / Δt (only count gains in worst case)
            if elev_delta > 0:
                pe_base = base_mass * G * elev_delta / dt
                pe_with_extra = total_mass * G * elev_delta / dt
                pe_delta = pe_with_extra - pe_base
            else:
                pe_delta = 0
            
            # Total extra power needed
            total_delta = max(0, ke_delta + pe_delta)  # worst case: no benefiting from descents
            
            kinetic_energy_extra.append(ke_delta)
            potential_energy_extra.append(pe_delta)
            total_extra_power.append(total_delta)
            timestamps.append(tp.time)
            velocities.append(v_current)
            elevation_gains.append(elev_delta)
            
            prev_tp = tp
        
        # Calculate statistics
        total_extra_power_arr = total_extra_power
        
        # Normalized Power (similar to TrainingPeaks algorithm, simplified)
        # NP = (avg(power^4))^(1/4)
        if len(total_extra_power_arr) > 0:
            power_4 = [p**4 for p in total_extra_power_arr]
            mean_power_4 = sum(power_4) / len(power_4)
            np_extra = mean_power_4**0.25 if mean_power_4 > 0 else 0
        else:
            np_extra = 0
        
        # Average power
        avg_power_extra = sum(total_extra_power_arr) / len(total_extra_power_arr) if len(total_extra_power_arr) > 0 else 0
        max_power_extra = max(total_extra_power_arr) if len(total_extra_power_arr) > 0 else 0
        
        # Total energy (Joules)
        total_energy = sum(total_extra_power_arr) if len(total_extra_power_arr) > 0 else 0
        
        # Duration
        duration_seconds = len(self.trackpoints) - 1
        duration_minutes = duration_seconds / 60
        duration_hours = duration_minutes / 60
        
        return {
            'file_name': Path(self.file_path).name,
            'duration': {
                'seconds': duration_seconds,
                'minutes': duration_minutes,
                'hours': duration_hours
            },
            'distance': {
                'meters': self.trackpoints[-1].distance,
                'km': self.trackpoints[-1].distance / 1000
            },
            'elevation': {
                'total_gain': total_elev_gain,
                'max_elevation': max([tp.elevation for tp in self.trackpoints]),
                'min_elevation': min([tp.elevation for tp in self.trackpoints])
            },
            'speed': {
                'max': max(velocities) if velocities else 0,
                'average': sum(velocities) / len(velocities) if velocities else 0
            },
            'extra_1kg_power': {
                'normalized_power': np_extra,
                'average_power': avg_power_extra,
                'max_power': max_power_extra,
                'total_energy_joules': total_energy,
                'total_energy_kilocalories': total_energy / 4184
            },
            'rider_mass_assumed': rider_mass,
            'extra_weight': extra_weight,
            'description': f'Worst-case scenario: extra {extra_weight}kg requires avg {avg_power_extra:.1f}W, NP {np_extra:.1f}W, max {max_power_extra:.1f}W'
        }


def analyze_all_tcx_files(directory: str = '/workspaces/np_weight_analysis'):
    """Analyze all TCX files in a directory."""
    results = []
    tcx_files = list(Path(directory).glob('*.tcx'))
    
    print(f"Found {len(tcx_files)} TCX files")
    print("=" * 80)
    
    for tcx_file in tcx_files:
        try:
            print(f"\nAnalyzing: {tcx_file.name}")
            analyzer = TCXAnalyzer(str(tcx_file))
            result = analyzer.calculate_power_impact()
            
            if result:
                results.append(result)
                
                # Print summary
                print(f"  Duration: {result['duration']['hours']:.2f}h ({result['duration']['minutes']:.0f}m)")
                print(f"  Distance: {result['distance']['km']:.1f} km")
                print(f"  Elevation gain: {result['elevation']['total_gain']:.0f}m")
                print(f"  Avg speed: {result['speed']['average']:.1f} m/s ({result['speed']['average']*3.6:.1f} km/h)")
                print(f"  Max speed: {result['speed']['max']:.1f} m/s ({result['speed']['max']*3.6:.1f} km/h)")
                print(f"\n  Extra 1kg impact (worst-case):")
                print(f"    Normalized Power: {result['extra_1kg_power']['normalized_power']:.1f} W")
                print(f"    Average Power: {result['extra_1kg_power']['average_power']:.1f} W")
                print(f"    Max Power: {result['extra_1kg_power']['max_power']:.1f} W")
                print(f"    Total Energy: {result['extra_1kg_power']['total_energy_kilocalories']:.1f} kcal")
        except Exception as e:
            print(f"  Error processing {tcx_file.name}: {e}")
    
    # Save results to JSON
    if results:
        output_file = Path(directory) / 'weight_analysis_results.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n{'='*80}")
        print(f"Results saved to: {output_file}")
    
    return results


if __name__ == '__main__':
    results = analyze_all_tcx_files()
    
    # Print comparative summary
    if results:
        print(f"\n{'='*80}")
        print("SUMMARY OF ALL RACES")
        print(f"{'='*80}")
        
        for result in results:
            print(f"\n{result['file_name']}")
            print(f"  NP cost of 1kg: {result['extra_1kg_power']['normalized_power']:.1f}W")
            print(f"  Avg cost of 1kg: {result['extra_1kg_power']['average_power']:.1f}W")
