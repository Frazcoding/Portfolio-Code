"""
Hydrology, rainwater harvesting, FAO-56 Penman-Monteith crop evapotranspiration,
and base reservoir dynamic mass balance engine.
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from src.config import GeometricConfig, HydraulicConfig


def calculate_saturation_vapor_pressure_kpa(temp_c: float) -> float:
    """Calculate saturation vapor pressure e_sat (kPa) at given temperature."""
    return 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))


def calculate_vapor_pressure_slope_kpa_c(temp_c: float) -> float:
    """Calculate slope of saturation vapor pressure curve Delta (kPa/°C)."""
    e_sat = calculate_saturation_vapor_pressure_kpa(temp_c)
    return (4098.0 * e_sat) / ((temp_c + 237.3) ** 2)


def calculate_psychrometric_constant_kpa_c(pressure_pa: float) -> float:
    """Calculate psychrometric constant gamma (kPa/°C) from atmospheric pressure."""
    p_kpa = pressure_pa / 1000.0
    return 0.000665 * p_kpa


def convert_wind_speed_10m_to_2m(wind_speed_10m: float) -> float:
    """Convert 10 m wind speed to 2 m height using FAO-56 logarithmic profile."""
    # u2 = u10 * 4.87 / ln(67.8 * 10 - 5.42) = u10 * 0.748
    return max(0.2, wind_speed_10m * 0.748)


def calculate_hourly_fao56_penman_monteith_et0(
    temp_air_c: float,
    rh_percent: float,
    wind_speed_10m_m_s: float,
    ghi_w_m2: float,
    pressure_pa: float,
    is_daylight: bool
) -> float:
    """
    Calculate hourly reference evapotranspiration ET0 (mm/h) using the standardized
    ASCE / FAO-56 Penman-Monteith equation for hourly time steps.
    """
    temp_c = float(temp_air_c)
    rh = max(5.0, min(100.0, float(rh_percent)))
    u2 = convert_wind_speed_10m_to_2m(float(wind_speed_10m_m_s))
    press = float(pressure_pa) if pressure_pa > 50000.0 else 101325.0

    delta = calculate_vapor_pressure_slope_kpa_c(temp_c)
    gamma = calculate_psychrometric_constant_kpa_c(press)

    e_sat = calculate_saturation_vapor_pressure_kpa(temp_c)
    e_act = e_sat * (rh / 100.0)
    vpd = max(0.0, e_sat - e_act)

    # Net radiation Rn (MJ/m^2/h)
    # Solar incoming in MJ/m^2/h: 1 W/m^2 = 0.0036 MJ/m^2/h
    rs_mj_m2_h = ghi_w_m2 * 0.0036
    # Net shortwave radiation (albedo for green grass reference = 0.23)
    rns = (1.0 - 0.23) * rs_mj_m2_h

    # Net longwave radiation approximation Rnl (MJ/m^2/h)
    # Stefan-Boltzmann constant sigma = 2.043e-10 MJ/K^4/m^2/h
    sigma = 2.043e-10
    t_k = temp_c + 273.16
    cloud_factor = 0.2 + 0.8 * min(1.0, max(0.1, rs_mj_m2_h / 2.5)) if is_daylight else 0.4
    emissivity = 0.34 - 0.14 * math.sqrt(max(0.1, e_act))
    rnl = sigma * (t_k ** 4) * emissivity * cloud_factor

    rn = max(0.0, rns - rnl) if is_daylight else max(-0.2, -rnl)

    # Soil heat flux G (MJ/m^2/h)
    g = 0.1 * rn if is_daylight else 0.5 * rn

    # FAO-56 hourly parameters for grass reference crop
    # Cn = 37 for hourly, Cd = 0.24 (daytime) or 0.96 (nighttime)
    cd = 0.24 if is_daylight else 0.96
    cn = 37.0

    numerator = 0.408 * delta * (rn - g) + gamma * (cn / (temp_c + 273.0)) * u2 * vpd
    denominator = delta + gamma * (1.0 + cd * u2)

    et0_mm_h = max(0.0, numerator / denominator)
    return et0_mm_h


def compute_hourly_et0_series(df_weather: pd.DataFrame) -> pd.Series:
    """Compute the 8760-hour ET0 series (mm/h) for the weather dataset."""
    et0_list = []
    for _, row in df_weather.iterrows():
        et0 = calculate_hourly_fao56_penman_monteith_et0(
            temp_air_c=row['temp_air_c'],
            rh_percent=row['rh_percent'],
            wind_speed_10m_m_s=row['wind_speed_m_s'],
            ghi_w_m2=row['ghi_w_m2'],
            pressure_pa=row['pressure_pa'],
            is_daylight=row['is_daylight']
        )
        et0_list.append(round(et0, 4))
    return pd.Series(et0_list, index=df_weather.index, name='et0_mm_h')


def simulate_hydrology_and_storage(
    df_weather: pd.DataFrame,
    df_crop: pd.DataFrame,
    geom: Optional[GeometricConfig] = None,
    hydr: Optional[HydraulicConfig] = None,
    use_dynamic_fao56: bool = True
) -> pd.DataFrame:
    """
    Simulate full-year hourly rainwater harvesting, crop water demand,
    reservoir mass balance, and drought deficit tracking.
    
    Returns:
        DataFrame with hourly storage volume, harvesting, irrigation delivered,
        overflow, and drought stress indicators.
    """
    if geom is None:
        geom = GeometricConfig()
    if hydr is None:
        hydr = HydraulicConfig()

    n_hours = len(df_weather)

    # 1. Rainwater inflow (Liters/h)
    # V_harvest = P_rain [mm] * A_catch [m^2] * C_runoff * eta_filter
    precip_mm = df_weather['precip_mm_h'].values
    rain_harvested_l = precip_mm * geom.area_catchment_m2 * hydr.runoff_coefficient * hydr.filter_efficiency

    # 2. Crop evapotranspiration and irrigation demand
    if use_dynamic_fao56:
        et0_series = compute_hourly_et0_series(df_weather)
        # Map month to crop coefficient Kc
        kc_map = dict(zip(df_crop['month'], df_crop['kc']))
        kc_hourly = df_weather['month'].map(kc_map).values

        # Daily irrigation required (Liters/day) = sum_day(ET0 * Kc) * Area_foliage / eta_drip
        # We calculate hourly demand, then aggregate to daily morning batch
        hourly_crop_et_mm = et0_series.values * kc_hourly
        hourly_irr_req_l = (hourly_crop_et_mm * geom.foliage_area_total_m2) / hydr.irrigation_drip_efficiency
    else:
        # Static baseline from UNIBO spreadsheet (1.096 L/day)
        hourly_irr_req_l = np.full(n_hours, hydr.baseline_irrigation_l_day / 24.0)

    # 3. Dynamic reservoir mass balance simulation
    v_tank_max = geom.volume_tank_max_l  # 150.0 L
    current_tank_l = hydr.tank_initial_volume_l  # 75.0 L (50% full on Jan 1)

    tank_volume_l = np.zeros(n_hours)
    tank_water_level_m = np.zeros(n_hours)
    overflow_l = np.zeros(n_hours)
    irr_delivered_l = np.zeros(n_hours)
    irr_deficit_l = np.zeros(n_hours)
    drought_stress_flag = np.zeros(n_hours, dtype=bool)

    # Group daily irrigation to morning pulse at 07:00 AM
    # First, calculate daily total demand
    df_temp = pd.DataFrame({
        'day_of_year': df_weather['day_of_year'],
        'hour': df_weather['hour'],
        'req_l': hourly_irr_req_l
    })
    daily_totals = df_temp.groupby('day_of_year')['req_l'].sum()

    for t in range(n_hours):
        # Add harvested rainwater
        inflow = rain_harvested_l[t]
        current_tank_l += inflow

        # Check for overflow
        if current_tank_l > v_tank_max:
            overflow_l[t] = current_tank_l - v_tank_max
            current_tank_l = v_tank_max
        else:
            overflow_l[t] = 0.0

        # Deliver irrigation pulse at 07:00 AM
        hour = df_weather['hour'].iloc[t]
        doy = df_weather['day_of_year'].iloc[t]

        if hour == 7:
            daily_req = daily_totals.loc[doy]
            if current_tank_l >= daily_req:
                irr_delivered_l[t] = daily_req
                current_tank_l -= daily_req
                irr_deficit_l[t] = 0.0
                drought_stress_flag[t] = False
            else:
                # Partial delivery or tank empty
                irr_delivered_l[t] = current_tank_l
                irr_deficit_l[t] = daily_req - current_tank_l
                current_tank_l = 0.0
                drought_stress_flag[t] = True
        else:
            irr_delivered_l[t] = 0.0
            irr_deficit_l[t] = 0.0
            drought_stress_flag[t] = False

        tank_volume_l[t] = current_tank_l
        # Water level h_w = V / (A_tank * 1000)
        tank_water_level_m[t] = (current_tank_l / 1000.0) / geom.area_tank_m2

    res_df = pd.DataFrame({
        'rain_harvested_l': rain_harvested_l,
        'irr_required_l': hourly_irr_req_l,
        'irr_delivered_l': irr_delivered_l,
        'irr_deficit_l': irr_deficit_l,
        'tank_volume_l': tank_volume_l,
        'tank_water_level_m': tank_water_level_m,
        'overflow_l': overflow_l,
        'is_drought_stress': drought_stress_flag
    }, index=df_weather.index)

    return res_df


def evaluate_hydrology_performance(sim_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate annual hydrological summary metrics."""
    total_rain_harvested = sim_df['rain_harvested_l'].sum()
    total_irr_required = sim_df['irr_required_l'].sum()
    total_irr_delivered = sim_df['irr_delivered_l'].sum()
    total_irr_deficit = sim_df['irr_deficit_l'].sum()
    total_overflow = sim_df['overflow_l'].sum()

    drought_days = int(sim_df['is_drought_stress'].sum())
    water_self_sufficiency_pct = (
        (total_irr_delivered / total_irr_required) * 100.0 if total_irr_required > 0 else 100.0
    )

    min_storage_l = sim_df['tank_volume_l'].min()
    mean_storage_l = sim_df['tank_volume_l'].mean()

    return {
        'total_rain_harvested_l': round(total_rain_harvested, 1),
        'total_irr_required_l': round(total_irr_required, 1),
        'total_irr_delivered_l': round(total_irr_delivered, 1),
        'total_irr_deficit_l': round(total_irr_deficit, 1),
        'total_overflow_l': round(total_overflow, 1),
        'water_self_sufficiency_pct': round(water_self_sufficiency_pct, 1),
        'drought_stress_days': drought_days,
        'min_tank_volume_l': round(min_storage_l, 1),
        'mean_tank_volume_l': round(mean_storage_l, 1)
    }

