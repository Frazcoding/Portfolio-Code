"""
Unit tests and analytical verification for Plantpost physical simulation suite.
Tests solar geometry, hydraulic head losses, FAO-56 Penman-Monteith ET0,
battery state-of-charge conservation, and baseline Excel parity.
"""

import os
import pytest
import numpy as np
import pandas as pd

from src.config import GeometricConfig, ElectricalConfig, HydraulicConfig, EcosystemConfig
from src.weather import (
    calculate_solar_declination_rad,
    calculate_equation_of_time_min,
    calculate_solar_elevation_deg,
    load_weather_data
)
from src.energy import (
    calculate_hourly_pv_power,
    calculate_hourly_lighting_load,
    simulate_battery_microgrid,
    evaluate_microgrid_performance
)
from src.hydraulics import (
    calculate_tier_dynamic_head,
    calculate_micro_pump_power_w,
    calculate_daily_irrigation_pumping,
    compare_with_excel_hydraulic_baseline
)
from src.hydrology import (
    calculate_hourly_fao56_penman_monteith_et0,
    simulate_hydrology_and_storage,
    evaluate_hydrology_performance
)
from src.ecosystem import (
    calculate_stormwater_attenuation,
    calculate_particulate_biofiltration,
    calculate_avoided_grid_carbon
)


def test_solar_geometry_and_twilight():
    """Verify astronomical calculations for Bologna at solstices and equinoxes."""
    # Summer Solstice (Day ~172)
    dec_summer = calculate_solar_declination_rad(172)
    assert np.isclose(np.degrees(dec_summer), 23.45, atol=0.5)

    # Winter Solstice (Day ~355)
    dec_winter = calculate_solar_declination_rad(355)
    assert np.isclose(np.degrees(dec_winter), -23.45, atol=0.5)

    # Solar elevation in Bologna at solar noon in summer should be ~68.9 degrees
    elev_summer_noon, _ = calculate_solar_elevation_deg(44.4949, 11.3426, 172, 12.0)
    assert 65.0 < elev_summer_noon < 72.0

    # Solar elevation at midnight must be well below civil twilight (-6 deg)
    elev_midnight, _ = calculate_solar_elevation_deg(44.4949, 11.3426, 172, 0.0)
    assert elev_midnight < -10.0


def test_hydraulic_friction_and_power():
    """Verify multi-tier dynamic head and micro-pump power calculations."""
    geom = GeometricConfig()
    hydr = HydraulicConfig()

    # Dynamic head for Tier 4 (z = 4.0 m) with empty tank (water level = 0 m)
    res_empty = calculate_tier_dynamic_head(4.0, 0.0, geom, hydr)
    assert res_empty['h_static_m'] == 4.0
    assert res_empty['h_friction_m'] > 0.0  # Friction loss must be positive
    assert res_empty['h_emitter_m'] == 2.0  # Operating pressure head
    assert res_empty['h_total_m'] > 6.0

    # Dynamic head with full tank (water level = 1.0 m) should decrease static head by 1.0 m
    res_full = calculate_tier_dynamic_head(4.0, 1.0, geom, hydr)
    assert np.isclose(res_full['h_static_m'], 3.0)
    assert res_full['h_total_m'] < res_empty['h_total_m']

    # Pump power must be positive and scale with head
    p_empty = calculate_micro_pump_power_w(res_empty['h_total_m'], hydr)
    p_full = calculate_micro_pump_power_w(res_full['h_total_m'], hydr)
    assert p_empty > p_full > 0.0
    assert p_empty < 5.0  # Micro-pump power should be on the order of 1 - 2 Watts for 0.9 L/min


def test_excel_hydraulic_formula_audit():
    """Verify that the historical Excel Row 35 anomaly is detected accurately."""
    df_audit = compare_with_excel_hydraulic_baseline()
    assert len(df_audit) == 4
    
    # Tier 4, 3, 1 should match within 0.1%
    assert df_audit.loc[df_audit['Tier'].str.contains('Tier 4'), 'Discrepancy [%]'].iloc[0] == 0.0
    assert df_audit.loc[df_audit['Tier'].str.contains('Tier 3'), 'Discrepancy [%]'].iloc[0] == 0.0
    assert df_audit.loc[df_audit['Tier'].str.contains('Tier 1'), 'Discrepancy [%]'].iloc[0] == 0.0

    # Tier 2 had the formula bug where it was multiplied by 0.7 instead of divided by 0.7
    tier2_row = df_audit.loc[df_audit['Tier'].str.contains('Tier 2')].iloc[0]
    assert tier2_row['Discrepancy [%]'] > 100.0
    assert 'Excel formula bug' in tier2_row['Notes']


def test_fao56_penman_monteith_hourly():
    """Verify reference evapotranspiration ET0 behavior under sunny vs humid night conditions."""
    # Sunny warm summer midday: 30°C, 40% RH, 2 m/s wind, 800 W/m^2 solar
    et0_midday = calculate_hourly_fao56_penman_monteith_et0(
        temp_air_c=30.0,
        rh_percent=40.0,
        wind_speed_10m_m_s=2.5,
        ghi_w_m2=800.0,
        pressure_pa=101325.0,
        is_daylight=True
    )
    assert 0.40 < et0_midday < 0.95  # Typical high summer hourly ET0 is ~0.6-0.8 mm/h

    # Cool humid night: 10°C, 95% RH, 1 m/s wind, 0 W/m^2 solar
    et0_night = calculate_hourly_fao56_penman_monteith_et0(
        temp_air_c=10.0,
        rh_percent=95.0,
        wind_speed_10m_m_s=1.0,
        ghi_w_m2=0.0,
        pressure_pa=101325.0,
        is_daylight=False
    )
    assert np.isclose(et0_night, 0.0, atol=0.05)


def test_battery_microgrid_invariants():
    """Verify LiFePO4 battery simulation respects SoC constraints and conservation."""
    df_w = load_weather_data('bologna')
    pv = calculate_hourly_pv_power(df_w)
    light = calculate_hourly_lighting_load(df_w)
    sim_bat = simulate_battery_microgrid(df_w, pv, light, battery_capacity_kwh=1.28)

    # Battery SoC must never violate boundaries
    assert sim_bat['battery_soc'].min() >= 0.20 - 1e-6
    assert sim_bat['battery_soc'].max() <= 1.00 + 1e-6

    # Unserved energy must be non-negative
    assert (sim_bat['unserved_energy_kwh'] >= 0.0).all()
    assert (sim_bat['battery_curtailed_kwh'] >= 0.0).all()


def test_stormwater_mass_balance():
    """Verify rainwater harvesting mass balance: harvested = retained + overflow."""
    df_w = load_weather_data('bologna')
    df_crop = pd.read_csv(os.path.join('data', 'crop_coefficients_vertical_foliage.csv'))
    sim_h = simulate_hydrology_and_storage(df_w, df_crop)
    metrics = calculate_stormwater_attenuation(sim_h, df_w)

    harvested = metrics['harvested_volume_l']
    retained = metrics['retained_in_reservoir_l']
    overflow = metrics['overflow_volume_l']

    assert np.isclose(harvested, retained + overflow, atol=1.0)
    assert 0.0 <= metrics['capture_efficiency_pct'] <= 100.0

