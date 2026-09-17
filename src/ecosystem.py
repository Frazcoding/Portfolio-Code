"""
Urban ecosystem services and environmental co-benefits quantification module.
Calculates localized microclimate evaporative cooling, stormwater retention,
air quality particulate matter (PM2.5/PM10) bio-deposition, and avoided grid carbon.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from src.config import EcosystemConfig, GeometricConfig, CITIES


def calculate_evaporative_cooling(
    df_hydrology: pd.DataFrame,
    df_weather: pd.DataFrame,
    eco: Optional[EcosystemConfig] = None
) -> pd.DataFrame:
    """
    Calculate localized sensible-to-latent heat conversion provided by foliage transpiration.
    
    Q_cool = m_transp * h_fg [Watts or kW_th]
    """
    if eco is None:
        eco = EcosystemConfig()

    # Transpired water volume in liters (assuming irrigation delivered is transpired)
    # Convert L to kg (1 L = 1 kg)
    transp_kg_h = df_hydrology['irr_delivered_l'].values

    # Instantaneous latent heat flux (Watts)
    # Energy in Joules = kg * 2.45e6 J/kg. Over 1 hour: Watts = Joules / 3600
    cooling_power_w = (transp_kg_h * eco.latent_heat_vaporization_j_kg) / 3600.0
    cooling_energy_kwh_th = (transp_kg_h * eco.latent_heat_vaporization_j_kg) / 3.6e6

    res_df = pd.DataFrame({
        'transpiration_l_h': transp_kg_h,
        'cooling_power_w': cooling_power_w,
        'cooling_energy_kwh_th': cooling_energy_kwh_th
    }, index=df_weather.index)

    return res_df


def calculate_stormwater_attenuation(
    df_hydrology: pd.DataFrame,
    df_weather: pd.DataFrame,
    geom: Optional[GeometricConfig] = None
) -> Dict[str, float]:
    """
    Calculate annual stormwater volume diverted from municipal storm drains.
    """
    if geom is None:
        geom = GeometricConfig()

    precip_mm = df_weather['precip_mm_h'].values
    total_precip_mm = float(np.sum(precip_mm))
    total_rain_volume_l = total_precip_mm * geom.area_catchment_m2

    harvested_l = float(df_hydrology['rain_harvested_l'].sum())
    overflow_l = float(df_hydrology['overflow_l'].sum())
    retained_l = harvested_l - overflow_l

    retention_efficiency_pct = (retained_l / total_rain_volume_l) * 100.0 if total_rain_volume_l > 0 else 0.0
    capture_efficiency_pct = (harvested_l / total_rain_volume_l) * 100.0 if total_rain_volume_l > 0 else 0.0

    return {
        'total_precipitation_mm': round(total_precip_mm, 1),
        'total_rain_volume_l': round(total_rain_volume_l, 1),
        'harvested_volume_l': round(harvested_l, 1),
        'retained_in_reservoir_l': round(retained_l, 1),
        'overflow_volume_l': round(overflow_l, 1),
        'capture_efficiency_pct': round(capture_efficiency_pct, 1),
        'net_retention_pct': round(retention_efficiency_pct, 1)
    }


def calculate_particulate_biofiltration(
    df_weather: pd.DataFrame,
    df_crop: pd.DataFrame,
    city_key: str = 'bologna',
    geom: Optional[GeometricConfig] = None,
    eco: Optional[EcosystemConfig] = None
) -> Dict[str, float]:
    """
    Calculate annual particulate matter dry deposition (PM2.5 and PM10)
    onto the vertical living foliage column in grams per year.
    
    F_pm = v_d * C_pm * A_leaf [ug/h]
    """
    if geom is None:
        geom = GeometricConfig()
    if eco is None:
        eco = EcosystemConfig()

    # Map month to LAI
    lai_map = dict(zip(df_crop['month'], df_crop['lai']))
    lai_hourly = df_weather['month'].map(lai_map).values
    leaf_area_m2 = lai_hourly * geom.foliage_area_total_m2  # Total one-sided leaf surface area

    # Get atmospheric ambient PM concentrations (ug/m^3)
    city_pm = eco.pm_concentrations.get(city_key, eco.pm_concentrations['bologna'])
    c_pm25 = city_pm['pm25']
    c_pm10 = city_pm['pm10']

    # Deposition velocity: 0.005 m/s = 18.0 m/h
    v_d_m_h = eco.pm_deposition_velocity_m_s * 3600.0

    # Hourly deposition: v_d (m/h) * C (ug/m^3) * A_leaf (m^2) = ug/h
    pm25_hourly_ug = v_d_m_h * c_pm25 * leaf_area_m2
    pm10_hourly_ug = v_d_m_h * c_pm10 * leaf_area_m2

    # Annual sum converted to grams (1e6 ug = 1 g)
    annual_pm25_g = float(np.sum(pm25_hourly_ug) / 1e6)
    annual_pm10_g = float(np.sum(pm10_hourly_ug) / 1e6)

    return {
        'city': city_key,
        'mean_leaf_area_m2': round(float(np.mean(leaf_area_m2)), 2),
        'ambient_pm25_ug_m3': c_pm25,
        'ambient_pm10_ug_m3': c_pm10,
        'annual_pm25_filtered_g': round(annual_pm25_g, 2),
        'annual_pm10_filtered_g': round(annual_pm10_g, 2)
    }


def calculate_avoided_grid_carbon(
    lighting_hours: float,
    city_key: str = 'bologna',
    eco: Optional[EcosystemConfig] = None
) -> Dict[str, Any]:
    """
    Calculate avoided municipal grid electricity and CO2e emissions relative to:
      1. Legacy High-Pressure Sodium (150 W)
      2. Contemporary Grid-Tied LED (50 W)
    """
    if eco is None:
        eco = EcosystemConfig()

    grid_intensity = eco.grid_carbon_italy_g_kwh if city_key == 'bologna' else eco.grid_carbon_uk_g_kwh

    # Electricity demand in kWh
    kwh_hps = (eco.hps_baseline_power_w * lighting_hours) / 1000.0
    kwh_grid_led = (eco.grid_led_baseline_power_w * lighting_hours) / 1000.0

    # Avoided emissions in kg CO2e
    co2_hps_kg = (kwh_hps * grid_intensity) / 1000.0
    co2_grid_led_kg = (kwh_grid_led * grid_intensity) / 1000.0

    return {
        'lighting_hours_yr': round(lighting_hours, 0),
        'grid_intensity_g_kwh': grid_intensity,
        'avoided_kwh_vs_hps': round(kwh_hps, 1),
        'avoided_kwh_vs_grid_led': round(kwh_grid_led, 1),
        'avoided_co2e_vs_hps_kg': round(co2_hps_kg, 1),
        'avoided_co2e_vs_grid_led_kg': round(co2_grid_led_kg, 1)
    }

