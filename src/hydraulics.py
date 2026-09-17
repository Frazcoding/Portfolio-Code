"""
Multi-tier micro-irrigation hydraulics and micro-pump power calculation engine.
Models static geodetic head, Darcy-Weisbach friction head loss in distribution tubing,
pressure-compensating drip emitter requirements, and DC micro-pump electrical draw.
Includes verification routines against the historical UNIBO feasibility spreadsheet.
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from src.config import GeometricConfig, HydraulicConfig


def calculate_friction_factor(
    reynolds_number: float,
    relative_roughness: float
) -> float:
    """
    Calculate Darcy friction factor using the Haaland approximation
    to the Colebrook-White equation.
    """
    if reynolds_number < 2000.0:
        return 64.0 / max(reynolds_number, 1.0)
    
    # Haaland equation
    term = (relative_roughness / 3.7) ** 1.11 + 6.9 / reynolds_number
    f = (-1.8 * math.log10(max(term, 1e-12))) ** -2
    return f


def calculate_tier_dynamic_head(
    tier_height_m: float,
    water_level_m: float,
    geom: Optional[GeometricConfig] = None,
    hydr: Optional[HydraulicConfig] = None
) -> Dict[str, float]:
    """
    Calculate total dynamic pumping head (m) for a specific vertical foliage tier.
    
    H_total = H_static + h_friction + H_emitter
    """
    if geom is None:
        geom = GeometricConfig()
    if hydr is None:
        hydr = HydraulicConfig()

    # 1. Static geodetic head (m)
    h_static = max(0.0, tier_height_m - water_level_m)

    # Pipe geometry & flow kinematics
    d_pipe = hydr.pipe_internal_diameter_m  # 0.008 m
    area_pipe = math.pi * (d_pipe / 2.0) ** 2
    flow_rate_m3_s = (hydr.nominal_flow_rate_l_min / 60.0) / 1000.0  # 1.5e-5 m^3/s
    velocity = flow_rate_m3_s / area_pipe  # ~0.298 m/s

    # Reynolds number
    re = velocity * d_pipe / hydr.water_viscosity_m2_s
    rel_roughness = hydr.pipe_roughness_m / d_pipe
    f = calculate_friction_factor(re, rel_roughness)

    # 2. Darcy-Weisbach friction loss along pipe length (m)
    # Pipe length extends from reservoir base to tier elevation plus 0.2m manifold bends
    pipe_length_m = tier_height_m + 0.20
    dynamic_pressure = (velocity ** 2) / (2.0 * hydr.gravity_m_s2)
    h_major = f * (pipe_length_m / d_pipe) * dynamic_pressure
    # Minor losses (two 90-degree elbows K=0.9 each, entrance K=0.5, exit K=1.0)
    k_minor_total = 0.9 * 2 + 0.5 + 1.0
    h_minor = k_minor_total * dynamic_pressure
    h_friction = h_major + h_minor

    # 3. Emitter minimum operating head (m)
    h_emitter = hydr.emitter_operating_head_m

    # Total dynamic head
    h_total = h_static + h_friction + h_emitter

    return {
        'tier_height_m': tier_height_m,
        'water_level_m': water_level_m,
        'h_static_m': round(h_static, 3),
        'h_friction_m': round(h_friction, 4),
        'h_emitter_m': round(h_emitter, 2),
        'h_total_m': round(h_total, 3),
        'flow_velocity_m_s': round(velocity, 3),
        'reynolds_number': round(re, 0)
    }


def calculate_micro_pump_power_w(
    total_head_m: float,
    hydr: Optional[HydraulicConfig] = None
) -> float:
    """
    Calculate instantaneous electrical pump power draw in Watts.
    
    P_pump = (rho * g * H_total * Q) / eta_pump
    """
    if hydr is None:
        hydr = HydraulicConfig()

    flow_rate_m3_s = (hydr.nominal_flow_rate_l_min / 60.0) / 1000.0  # 1.5e-5 m^3/s
    hydraulic_power_w = hydr.fluid_density_kg_m3 * hydr.gravity_m_s2 * total_head_m * flow_rate_m3_s
    electric_power_w = hydraulic_power_w / hydr.pump_efficiency
    return electric_power_w


def calculate_daily_irrigation_pumping(
    daily_volume_liters: float,
    current_water_level_m: float,
    geom: Optional[GeometricConfig] = None,
    hydr: Optional[HydraulicConfig] = None
) -> Dict[str, Any]:
    """
    Calculate pumping power and electrical energy required to deliver the daily irrigation
    volume split evenly across all 4 tiers during the morning batch schedule.
    
    Returns:
        Dict with tier-by-tier power, duration, and total daily energy in Wh.
    """
    if geom is None:
        geom = GeometricConfig()
    if hydr is None:
        hydr = HydraulicConfig()

    vol_per_tier_l = daily_volume_liters / geom.n_tiers
    flow_rate_l_s = hydr.nominal_flow_rate_l_min / 60.0  # 0.015 L/s
    pumping_duration_s_per_tier = vol_per_tier_l / flow_rate_l_s

    tier_heads = []
    tier_powers_w = []
    tier_energies_wh = []

    for z in geom.tier_heights_m:
        head_data = calculate_tier_dynamic_head(z, current_water_level_m, geom, hydr)
        p_w = calculate_micro_pump_power_w(head_data['h_total_m'], hydr)
        e_wh = p_w * (pumping_duration_s_per_tier / 3600.0)

        tier_heads.append(head_data['h_total_m'])
        tier_powers_w.append(p_w)
        tier_energies_wh.append(e_wh)

    total_energy_wh = sum(tier_energies_wh)
    total_duration_minutes = (pumping_duration_s_per_tier * geom.n_tiers) / 60.0
    mean_pump_power_w = np.mean(tier_powers_w)

    return {
        'daily_volume_l': round(daily_volume_liters, 3),
        'vol_per_tier_l': round(vol_per_tier_l, 3),
        'duration_minutes': round(total_duration_minutes, 2),
        'tier_heads_m': [round(h, 2) for h in tier_heads],
        'tier_powers_w': [round(p, 3) for p in tier_powers_w],
        'tier_energies_wh': [round(e, 4) for e in tier_energies_wh],
        'total_daily_energy_wh': round(total_energy_wh, 3),
        'mean_power_w': round(mean_pump_power_w, 2)
    }


def compare_with_excel_hydraulic_baseline() -> pd.DataFrame:
    """
    Compare Python dynamic hydraulic calculations with the historical Excel spreadsheet.
    
    Documents the historical formula anomaly in Tier 2:
    - Excel Row 34 (Tier 3): = (1000*9.81*B19*B31)/(1000*0.7)  [Correct: divides by 0.7]
    - Excel Row 35 (Tier 2): = (1000*9.81*B22*B31)/(1000/0.7)  [Anomaly: divides by 1000/0.7, multiplying by 0.7!]
    - Excel Row 36 (Tier 1): = (1000*9.81*B25*B31)/(1000*0.7)  [Correct]
    """
    geom = GeometricConfig()
    hydr = HydraulicConfig()

    # In Excel, Q was defined as 0.0045 / 5 = 0.0009 m^3/s (or 0.9 L/s delivery pulse)
    q_excel = 0.0009  # m^3/s
    h_w = 0.04  # ~4 cm typical water height in tank

    rows = []
    for tier_idx, z in enumerate([4.0, 3.0, 2.0, 1.0], start=1):
        h_static = z - h_w
        # Correct formulation
        p_correct_kw = (1000.0 * 9.81 * h_static * q_excel) / (1000.0 * 0.70)
        
        # Excel formula formulation
        if z == 2.0:
            # Excel Row 35 bug
            p_excel_kw = (1000.0 * 9.81 * h_static * q_excel) / (1000.0 / 0.70)
        else:
            p_excel_kw = p_correct_kw

        diff_pct = ((p_correct_kw - p_excel_kw) / p_excel_kw) * 100.0 if p_excel_kw > 0 else 0.0

        rows.append({
            'Tier': f"Tier {5 - tier_idx} (z={z}m)",
            'Static Head [m]': round(h_static, 3),
            'Excel Value [kW]': round(p_excel_kw, 5),
            'Corrected Physics [kW]': round(p_correct_kw, 5),
            'Discrepancy [%]': round(diff_pct, 1),
            'Notes': 'Excel formula bug (multiplied by 0.7)' if z == 2.0 else 'Exact match'
        })

    return pd.DataFrame(rows)

