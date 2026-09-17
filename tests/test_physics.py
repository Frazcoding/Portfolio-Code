"""Unit tests and analytical verification for Plantpost physical simulation suite (OOP)."""

import os
import pytest
import numpy as np
import pandas as pd

from src.config import GeometricConfig, ElectricalConfig, HydraulicConfig, EcosystemConfig
from src.weather import SolarAstronomy, WeatherDataPipeline
from src.energy import PhotovoltaicCanopy, BatteryMicrogrid
from src.hydraulics import VerticalHydraulicManifold
from src.hydrology import PenmanMonteithHydrology, ReservoirMassBalance
from src.ecosystem import UrbanEcosystemServices


def test_solar_geometry_and_twilight():
    # Summer Solstice (Day ~172)
    dec_summer = SolarAstronomy.solar_declination_rad(172)
    assert np.isclose(np.degrees(dec_summer), 23.45, atol=0.5)

    # Winter Solstice (Day ~355)
    dec_winter = SolarAstronomy.solar_declination_rad(355)
    assert np.isclose(np.degrees(dec_winter), -23.45, atol=0.5)

    # Solar elevation in Bologna at solar noon in summer should be ~68.9 degrees
    elev_summer_noon, _ = SolarAstronomy.solar_elevation_deg(44.4949, 11.3426, 172, 12.0)
    assert 65.0 < elev_summer_noon < 72.0

    # Solar elevation at midnight must be well below civil twilight (-6 deg)
    elev_midnight, _ = SolarAstronomy.solar_elevation_deg(44.4949, 11.3426, 172, 0.0)
    assert elev_midnight < -10.0


def test_hydraulic_friction_and_power():
    manifold = VerticalHydraulicManifold()

    # Dynamic head for Tier 4 (z = 4.0 m) with empty tank (water level = 0 m)
    res_empty = manifold.tier_dynamic_head(4.0, 0.0)
    assert res_empty['h_static_m'] == 4.0
    assert res_empty['h_friction_m'] > 0.0
    assert res_empty['h_emitter_m'] == 2.0
    assert res_empty['h_total_m'] > 6.0

    # Dynamic head with full tank (water level = 1.0 m) should decrease static head by 1.0 m
    res_full = manifold.tier_dynamic_head(4.0, 1.0)
    assert np.isclose(res_full['h_static_m'], 3.0)
    assert res_full['h_total_m'] < res_empty['h_total_m']

    # Pump power must scale with head
    p_empty = manifold.micro_pump_power_w(res_empty['h_total_m'])
    p_full = manifold.micro_pump_power_w(res_full['h_total_m'])
    assert p_empty > p_full > 0.0
    assert p_empty < 5.0


def test_excel_hydraulic_formula_audit():
    df_audit = VerticalHydraulicManifold.audit_excel_hydraulic_baseline()
    assert len(df_audit) == 4
    
    assert df_audit.loc[df_audit['Tier'].str.contains('Tier 4'), 'Discrepancy [%]'].iloc[0] == 0.0
    assert df_audit.loc[df_audit['Tier'].str.contains('Tier 3'), 'Discrepancy [%]'].iloc[0] == 0.0
    assert df_audit.loc[df_audit['Tier'].str.contains('Tier 1'), 'Discrepancy [%]'].iloc[0] == 0.0

    tier2_row = df_audit.loc[df_audit['Tier'].str.contains('Tier 2')].iloc[0]
    assert tier2_row['Discrepancy [%]'] > 100.0
    assert 'Excel formula bug' in tier2_row['Notes']


def test_fao56_penman_monteith_hourly():
    et0_midday = PenmanMonteithHydrology.hourly_et0(
        temp_air_c=30.0,
        rh_percent=40.0,
        wind_speed_10m=2.5,
        ghi_w_m2=800.0,
        pressure_pa=101325.0,
        is_daylight=True
    )
    assert 0.40 < et0_midday < 0.95

    et0_night = PenmanMonteithHydrology.hourly_et0(
        temp_air_c=10.0,
        rh_percent=95.0,
        wind_speed_10m=1.0,
        ghi_w_m2=0.0,
        pressure_pa=101325.0,
        is_daylight=False
    )
    assert np.isclose(et0_night, 0.0, atol=0.05)


def test_battery_microgrid_invariants():
    pipeline = WeatherDataPipeline()
    df_w = pipeline.load_weather_data('bologna')
    canopy = PhotovoltaicCanopy()
    pv = canopy.calculate_power(df_w)
    light = canopy.calculate_lighting_load(df_w)
    bat = BatteryMicrogrid(capacity_kwh=1.28)
    sim_bat = bat.simulate(df_w, pv, light)

    assert sim_bat['battery_soc'].min() >= 0.20 - 1e-6
    assert sim_bat['battery_soc'].max() <= 1.00 + 1e-6
    assert (sim_bat['unserved_energy_kwh'] >= 0.0).all()
    assert (sim_bat['battery_curtailed_kwh'] >= 0.0).all()


def test_stormwater_mass_balance():
    pipeline = WeatherDataPipeline()
    df_w = pipeline.load_weather_data('bologna')
    df_crop = pd.read_csv(os.path.join('data', 'crop_coefficients_vertical_foliage.csv'))
    res_model = ReservoirMassBalance()
    sim_h = res_model.simulate(df_w, df_crop)

    eco = UrbanEcosystemServices()
    metrics = eco.stormwater_attenuation(sim_h, df_w)

    harvested = metrics['harvested_volume_l']
    retained = metrics['retained_in_reservoir_l']
    overflow = metrics['overflow_volume_l']

    assert np.isclose(harvested, retained + overflow, atol=1.0)
    assert 0.0 <= metrics['capture_efficiency_pct'] <= 100.0
