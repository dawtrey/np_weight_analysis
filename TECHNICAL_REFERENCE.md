# Technical Reference: Weight Power Analysis

## Physical Constants & Parameters

```
G (gravitational acceleration):  9.81 m/s²
Mass assumptions:                75 kg base rider + bike
Extra mass tested:               1.0 kg
Air density (sea level):         1.225 kg/m³
Cyclist drag coefficient:        1.1
Frontal area:                    0.40 m²
Rolling resistance coeff:        0.004
```

## Energy Equations Reference

### 1. Kinetic Energy

**Definition**: Energy due to motion
$$KE = \frac{1}{2}mv^2$$

**Change in kinetic energy**:
$$\Delta KE = \frac{1}{2}m(v_2^2 - v_1^2)$$

**Power requirement to create this change over time Δt**:
$$P_{KE} = \frac{\Delta KE}{\Delta t} = \frac{1}{2}m\frac{(v_2^2 - v_1^2)}{\Delta t}$$

**For 1kg additional mass from rest to 10 m/s:**
$$\Delta KE = \frac{1}{2} \times 1 \times (10^2 - 0^2) = 50 \text{ J}$$

If accomplished over 5 seconds:
$$P = \frac{50}{5} = 10 \text{ W}$$

### 2. Gravitational Potential Energy

**Definition**: Energy due to height in gravitational field
$$PE = mgh$$

**Change in gravitational PE while climbing**:
$$\Delta PE = mg\Delta h$$

**Power requirement to climb height Δh over time Δt**:
$$P_{PE} = \frac{\Delta PE}{\Delta t} = mg\frac{\Delta h}{\Delta t} = mg \times (\text{climb rate})$$

**For 1kg climbing at 5% grade (50m per 1km) at 7 m/s (25.2 km/h)**:
- Climb rate = 7 m/s × 0.05 = 0.35 m/s
- $P_{PE} = 1 \times 9.81 \times 0.35 = 3.43$ W

### 3. Total Worst-Case Power

**Without downhill recovery**:
$$P_{total,worst} = \max(0, P_{KE} + P_{PE})$$

**Real-world with recovery**:
$$P_{total,real} = P_{KE} + \max(0, P_{PE})$$

(PE is only added on climbs, ignored on descents for worst-case)

## Normalized Power Calculation

The cycling industry standard for measuring average effort intensity, accounting for effort distribution.

**Mathematical definition**:
$$NP = \left(\frac{1}{n}\sum_{i=1}^{n} P_i^4\right)^{1/4}$$

**Why the 4th power?** 
- Amplifies high power spikes
- Better correlates with physiological stress than simple average
- More predictive of performance outcome

**Example calculation for 1kg cost:**

Given power array: [0, 5, 8, 2, 15, 3] W

$$\text{Sum of } P^4 = 0 + 625 + 4096 + 16 + 50625 + 81 = 55443$$

$$\text{Mean} = \frac{55443}{6} = 9240.5$$

$$NP = 9240.5^{0.25} = 9.77 \text{ W}$$

(vs. simple average of 5.5 W - NP penalizes the 15W spike)

## Velocity to Power Conversion

### From GPS Data

TCX files contain instantaneous speed. To estimate power from speed changes alone:

**Method 1: Kinetic energy**
$$P = \frac{1}{2}m\frac{\Delta v^2}{\Delta t}$$

**Method 2: Using cadence and force**
$$P = T \times \omega = (\text{torque}) \times (2\pi \times \text{rpm}/60)$$

Where cadence from TCX: 103 RPM

**Method 3: Total resistance model**
$$P = F \times v$$

where F includes:
- Rolling resistance: $F_{rr} = C_{rr} \times m \times g$
- Air drag: $F_{drag} = \frac{1}{2}\rho C_D A v^2$  
- Gravity: $F_g = mg \sin(\theta)$

## Sample Calculations from Your Data

### Cambridge Crit File Analysis

**Trackpoint sequence (sampled):**

| Time | Elevation (m) | Speed (m/s) | Distance (m) | Est. Δv² | KE Cost |
|------|---------------|-------------|--------------|----------|---------|
| 15:15:53 | 0.4 | 0.0 | 0 | - | - |
| 15:15:54 | 0.4 | 0.0 | 4 | 0.0 | 0 W |
| 15:15:55 | 0.4 | 0.0 | 10.4 | 0.0 | 0 W |
| 15:15:56 | 0.4 | 5.6 | 16.8 | 31.36 | 15.7 W |
| 15:15:57 | 0.4 | 5.775 | 23.1 | 0.15 | 0.1 W |
| 15:15:58 | 0.4 | 6.74 | 33.7 | 0.92 | 0.5 W |
| 15:15:59 | 0.4 | 7.64 | 42.2 | 0.84 | 0.4 W |
| 15:16:00 | 0.4 | 7.66 | 48.7 | 0.0 | 0 W |
| 15:16:01 | 0.4 | varies | 59.3 | varies | varies |

**KE Cost = ½ × 1 × Δv²** (Δt = 1 second)

In this sequence: 5.6 m/s to 6.74 m/s requires **~15W** for the 1kg.

Given actual power for whole bike+rider going from ~200W to ~600W, the 15W for 1kg represents ~2-3% of total.

## Aero Power Loss (More Detailed)

While not included in worst-case, worth noting:

**Drag force**:
$$F_d = \frac{1}{2}\rho C_D A v^2$$

**Drag power** (power lost to aerodynamic drag):
$$P_d = F_d \times v = \frac{1}{2}\rho C_D A v^3$$

**If 1kg affects bike aero slightly** (e.g., shifts weight distribution):
- At 7 m/s (25.2 km/h): ρCAv³ ≈ 0.5 × 1.225 × 1.1 × 0.4 × 343 = ~92 W (total aero)
- 1kg might contribute small fraction: 0.1-0.5 W additional drag
- At 10 m/s: ≈ 0.2-1 W additional drag

**Conclusion**: Aero effect small but directionally similar to KE/PE costs.

## Rolling Resistance Detail

**Force from rolling resistance**:
$$F_{rr} = C_{rr} \times (m_{total} + m_{1kg}) \times g$$

**Power loss**:
$$P_{rr} = F_{rr} \times v = C_{rr} \times (m + 1) \times g \times v$$

**For 1kg increase at cruise speed 7 m/s**:
$$\Delta P_{rr} = C_{rr} \times 1 \times 9.81 \times 7 = 0.004 \times 9.81 \times 7 = 0.27 \text{ W}$$

Very small but accumulates over entire race (27 W for the full 3375-second event = ~91 kJ).

## Energy Conservation Summary for 1kg

Across a 62-minute (3742 sec) criterium race:

**Kinetic energy (variable accelerations)**:
- Average extra power: 3-5 W
- Total energy: 3 × 3742 = 11,226 J ≈ 2.7 kcal

**Potential energy (if minimal elevation)**:
- Average: 0 W
- Total: 0 J

**Rolling resistance (entire race)**:
- Average: 0.27 W
- Total: 0.27 × 3742 = 1,010 J ≈ 0.24 kcal

**Aero (if present)**:
- Average: 0.1-0.5 W
- Total: 50-200 J ≈ 0.01-0.05 kcal

**TOTAL for flat crit**: ~12-13 kJ ≈ 3 kcal penalty for 1kg

At 250W average normalized power: 12,000 J = 12,000 / (250 × 3742) = 0.013 = 1.3% penalty

## File Statistics Summary

### I_won_national_crit_champs.tcx
- Points: 3742 (1 per second resolution)
- Duration: 3742 seconds = 62.37 minutes
- Total distance: 45,265.4 m = 45.27 km
- Avg speed: 45,265.4 / 3742 = 12.09 m/s = 43.5 km/h
- Elevation range: 10.2m (flat circuit)
- Notes: Cadence consistently 103 RPM (structured hard effort)

### cambridge_crit_-_results_pending.tcx
- Points: 3375 (1 per second resolution)
- Duration: 3375 seconds = 56.25 minutes  
- Total distance: 41,319.8 m = 41.32 km
- Avg speed: 41,319.8 / 3375 = 12.24 m/s = 44.1 km/h
- Elevation range: 0.4m (completely flat)
- Avg HR: 177 bpm
- Max HR: 187 bpm
- Power: 163-593 W (actual measured data available!)
- Notes: Very hard effort, maximal heart rate for most of race

## Scaling to Other Weights

The formulas scale linearly for different weight assumptions:

**For 2kg**:
- Simply double all power costs
- KE cost scales as: $P \propto m$
- PE cost scales as: $P \propto m$  
- RR cost scales as: $P \propto m$

**For 0.5kg**:
- Halve all power costs
- Useful for ultra-light bike analysis

**General formula for any Δm**:
$$P_{extra} = \Delta m \times P_{1kg}$$

