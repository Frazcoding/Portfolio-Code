"""
Photovoltaic generation, lighting load schedules, and LiFePO4 battery microgrid engine.
Simulates hourly solar power, astronomical dusk-to-dawn lighting, auxiliary loads,
and discrete battery state-of-charge (SoC) dynamics with temperature derating.
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from src.config import GeometricConfig, ElectricalConfig


def calculate_cell_temperature(
    ambient_temp_c: float,
    irradiance_w_m2: float,
    noct_c: float = 45.0
) -> float:
    """Calculate PV cell temperature from ambient temperature and irradiance."""
    return ambient_temp_c + (irradiance_w_m2 / 800.0) * (noct_c - 20.0)


def calculate_hourly_pv_power(
    df_weather: pd.DataFrame,
    geom: Optional[GeometricConfig] = None,
    elec: Optional[ElectricalConfig] = None
) -> pd.Series:
    """
    Calculate hourly electrical power output from the circular PV canopy in Watts.
    
    Accounts for canopy area, cell efficiency, MPPT and BOS wiring losses,
    temperature derating, and circular canopy geometry calibration factor.
    """
    if geom is None:
        geom = GeometricConfig()
    if elec is None:
        elec = ElectricalConfig()

    # Effective aperture area
    area_pv = geom.area_catchment_m2  # 3.14 m^2

    # Calculate cell temperatures across all hours
    cell_temps = calculate_cell_temperature(
        df_weather['temp_air_c'].values,
        df_weather['ghi_w_m2'].values
    )

    # Temperature derating factor: 1 + gamma * (T_cell - 25°C)
    temp_derating = 1.0 + elec.pv_temp_coeff_per_k * (cell_temps - 25.0)
    # Floor derating at 0.5 to prevent negative or unphysical values
    temp_derating = np.clip(temp_derating, 0.5, 1.2)

    # Instantaneous PV output (Watts)
    pv_power_w = (
        area_pv *
        elec.pv_efficiency_ref *
        df_weather['ghi_w_m2'].values *
        temp_derating *
        elec.bos_combined_efficiency *
        elec.canopy_geometry_factor
    )

    return pd.Series(np.maximum(0.0, pv_power_w), index=df_weather.index, name='p_pv_w')


def calculate_hourly_lighting_load(
    df_weather: pd.DataFrame,
    elec: Optional[ElectricalConfig] = None
) -> pd.Series:
    """
    Calculate instantaneous public lighting power draw in Watts.
    The luminaire activates strictly from dusk to dawn when solar elevation <= -6 deg.
    """
    if elec is None:
        elec = ElectricalConfig()

    is_civil_night = df_weather['is_civil_night'].values
    light_power_w = np.where(is_civil_night, elec.power_light_w, 0.0)
    return pd.Series(light_power_w, index=df_weather.index, name='p_light_w')


def simulate_battery_microgrid(
    df_weather: pd.DataFrame,
    pv_power_w: pd.Series,
    light_power_w: pd.Series,
    pump_power_w: Optional[pd.Series] = None,
    battery_capacity_kwh: Optional[float] = None,
    geom: Optional[GeometricConfig] = None,
    elec: Optional[ElectricalConfig] = None
) -> pd.DataFrame:
    """
    Simulate LiFePO4 battery storage dynamics over the 8760-hour annual profile.
    
    Tracks:
        - Total load (lighting + pump + auxiliary BMS)
        - Net power flow (surplus vs deficit)
        - Battery state of charge: SoC(t) in [SoC_min, 1.0]
        - Battery stored energy: E_bat(t) in kWh
        - Energy curtailed (overflow) and unserved energy (blackout)
        - Loss of Load Probability (LOLP)
    """
    if geom is None:
        geom = GeometricConfig()
    if elec is None:
        elec = ElectricalConfig()

    c_bat = battery_capacity_kwh if battery_capacity_kwh is not None else elec.battery_nominal_capacity_kwh
    e_min = c_bat * elec.battery_soc_min
    e_max = c_bat * elec.battery_soc_max
    
    # Starting energy
    current_energy_kwh = c_bat * elec.battery_initial_soc

    # Total electrical load
    if pump_power_w is None:
        pump_power_w = pd.Series(0.0, index=df_weather.index)

    p_aux = elec.power_aux_w
    p_load = light_power_w.values + pump_power_w.values + p_aux
    p_pv = pv_power_w.values
    temp_air = df_weather['temp_air_c'].values

    n_hours = len(df_weather)
    soc_array = np.zeros(n_hours)
    energy_array = np.zeros(n_hours)
    curtailed_kwh = np.zeros(n_hours)
    unserved_kwh = np.zeros(n_hours)
    loss_of_load = np.zeros(n_hours, dtype=bool)

    eta_chg = elec.battery_charge_efficiency
    eta_dis = elec.battery_discharge_efficiency
    subzero_derate = elec.subzero_charge_derate

    for t in range(n_hours):
        net_w = p_pv[t] - p_load[t]
        dt_h = 1.0

        if net_w >= 0.0:
            # Solar surplus: charge battery
            # Apply low-temperature charge derating if below freezing
            effective_eta_chg = eta_chg * (subzero_derate if temp_air[t] < 0.0 else 1.0)
            charge_energy_kwh = (net_w / 1000.0) * effective_eta_chg * dt_h
            
            space_kwh = e_max - current_energy_kwh
            if charge_energy_kwh <= space_kwh:
                current_energy_kwh += charge_energy_kwh
                curtailed_kwh[t] = 0.0
            else:
                current_energy_kwh = e_max
                # Excess solar curtailed
                curtailed_kwh[t] = (charge_energy_kwh - space_kwh) / effective_eta_chg

            unserved_kwh[t] = 0.0
            loss_of_load[t] = False

        else:
            # Load deficit: discharge battery
            curtailed_kwh[t] = 0.0
            req_discharge_kwh = (abs(net_w) / 1000.0) / eta_dis * dt_h
            available_kwh = max(0.0, current_energy_kwh - e_min)

            if available_kwh >= req_discharge_kwh:
                current_energy_kwh -= req_discharge_kwh
                unserved_kwh[t] = 0.0
                loss_of_load[t] = False
            else:
                # Blackout / partial unserved load
                delivered_discharge_kwh = available_kwh
                current_energy_kwh = e_min
                delivered_w = p_pv[t] + (delivered_discharge_kwh * eta_dis / dt_h) * 1000.0
                unserved_w = max(0.0, p_load[t] - delivered_w)
                unserved_kwh[t] = (unserved_w / 1000.0) * dt_h
                loss_of_load[t] = True if unserved_w > 1.0 else False

        energy_array[t] = current_energy_kwh
        soc_array[t] = current_energy_kwh / c_bat

    res_df = pd.DataFrame({
        'p_pv_w': p_pv,
        'p_light_w': light_power_w.values,
        'p_pump_w': pump_power_w.values,
        'p_load_total_w': p_load,
        'battery_energy_kwh': energy_array,
        'battery_soc': soc_array,
        'battery_curtailed_kwh': curtailed_kwh,
        'unserved_energy_kwh': unserved_kwh,
        'is_loss_of_load': loss_of_load
    }, index=df_weather.index)

    return res_df


def evaluate_microgrid_performance(
    sim_df: pd.DataFrame,
    c_bat_kwh: float
) -> Dict[str, Any]:
    """Calculate high-level key performance metrics for the electrical microgrid."""
    total_pv_kwh = sim_df['p_pv_w'].sum() / 1000.0
    total_lighting_kwh = sim_df['p_light_w'].sum() / 1000.0
    total_pump_kwh = sim_df['p_pump_w'].sum() / 1000.0
    total_load_kwh = sim_df['p_load_total_w'].sum() / 1000.0
    total_curtailed_kwh = sim_df['battery_curtailed_kwh'].sum()
    total_unserved_kwh = sim_df['unserved_energy_kwh'].sum()

    lighting_hours = (sim_df['p_light_w'] > 0).sum()
    blackout_hours = sim_df['is_loss_of_load'].sum()
    lolp = (blackout_hours / lighting_hours) if lighting_hours > 0 else 0.0

    min_soc = sim_df['battery_soc'].min()
    mean_soc = sim_df['battery_soc'].mean()

    # Discharged energy throughput (kWh) for battery wear estimation
    # When battery_energy decreases, that is discharge
    energy_diff = np.diff(sim_df['battery_energy_kwh'].values)
    discharges_kwh = -np.sum(energy_diff[energy_diff < 0])
    equivalent_full_cycles = discharges_kwh / c_bat_kwh

    return {
        'total_pv_generation_kwh': round(total_pv_kwh, 2),
        'total_lighting_demand_kwh': round(total_lighting_kwh, 2),
        'total_pump_demand_kwh': round(total_pump_kwh, 2),
        'total_load_demand_kwh': round(total_load_kwh, 2),
        'total_curtailed_kwh': round(total_curtailed_kwh, 2),
        'total_unserved_kwh': round(total_unserved_kwh, 3),
        'lighting_hours': int(lighting_hours),
        'blackout_hours': int(blackout_hours),
        'loss_of_load_probability_lolp': round(lolp, 4),
        'electrical_reliability_pct': round((1.0 - lolp) * 100.0, 2),
        'min_soc': round(min_soc, 3),
        'mean_soc': round(mean_soc, 3),
        'equivalent_full_cycles': round(equivalent_full_cycles, 1)
    }

