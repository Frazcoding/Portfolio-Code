"""Urban microclimate, stormwater, particulate matter bio-deposition, and carbon offset accounting."""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from src.config import EcosystemConfig, GeometricConfig


class UrbanEcosystemServices:
    """Quantification engine for urban ecosystem services and microclimate co-benefits."""

    def __init__(
        self,
        geom: Optional[GeometricConfig] = None,
        eco: Optional[EcosystemConfig] = None
    ):
        self.geom = geom or GeometricConfig()
        self.eco = eco or EcosystemConfig()

    def evaporative_cooling(
        self,
        df_hydrology: pd.DataFrame,
        df_weather: pd.DataFrame
    ) -> pd.DataFrame:
        transp_kg_h = df_hydrology['irr_delivered_l'].values
        # Latent heat flux: Q_cool = m * h_fg
        cooling_w = (transp_kg_h * self.eco.latent_heat_vaporization_j_kg) / 3600.0
        cooling_kwh_th = (transp_kg_h * self.eco.latent_heat_vaporization_j_kg) / 3.6e6

        return pd.DataFrame({
            'transpiration_l_h': transp_kg_h,
            'cooling_power_w': cooling_w,
            'cooling_energy_kwh_th': cooling_kwh_th
        }, index=df_weather.index)

    def stormwater_attenuation(
        self,
        df_hydrology: pd.DataFrame,
        df_weather: pd.DataFrame
    ) -> Dict[str, float]:
        total_precip_mm = float(np.sum(df_weather['precip_mm_h'].values))
        total_rain_l = total_precip_mm * self.geom.area_catchment_m2
        harvested_l = float(df_hydrology['rain_harvested_l'].sum())
        overflow_l = float(df_hydrology['overflow_l'].sum())
        retained_l = harvested_l - overflow_l

        retention_pct = (retained_l / total_rain_l * 100.0) if total_rain_l > 0 else 0.0
        capture_pct = (harvested_l / total_rain_l * 100.0) if total_rain_l > 0 else 0.0

        return {
            'total_precipitation_mm': round(total_precip_mm, 1),
            'total_rain_volume_l': round(total_rain_l, 1),
            'harvested_volume_l': round(harvested_l, 1),
            'retained_in_reservoir_l': round(retained_l, 1),
            'overflow_volume_l': round(overflow_l, 1),
            'capture_efficiency_pct': round(capture_pct, 1),
            'net_retention_pct': round(retention_pct, 1)
        }

    def particulate_biofiltration(
        self,
        df_weather: pd.DataFrame,
        df_crop: pd.DataFrame,
        city_key: str = 'bologna'
    ) -> Dict[str, float]:
        lai_map = dict(zip(df_crop['month'], df_crop['lai']))
        leaf_area_m2 = df_weather['month'].map(lai_map).values * self.geom.foliage_area_total_m2

        city_pm = self.eco.pm_concentrations.get(city_key, self.eco.pm_concentrations['bologna'])
        v_d_m_h = self.eco.pm_deposition_velocity_m_s * 3600.0

        # Dry deposition flux: F = v_d * C * A_leaf (ug/h)
        pm25_g = float(np.sum(v_d_m_h * city_pm['pm25'] * leaf_area_m2) / 1e6)
        pm10_g = float(np.sum(v_d_m_h * city_pm['pm10'] * leaf_area_m2) / 1e6)

        return {
            'city': city_key,
            'mean_leaf_area_m2': round(float(np.mean(leaf_area_m2)), 2),
            'ambient_pm25_ug_m3': city_pm['pm25'],
            'ambient_pm10_ug_m3': city_pm['pm10'],
            'annual_pm25_filtered_g': round(pm25_g, 2),
            'annual_pm10_filtered_g': round(pm10_g, 2)
        }

    def avoided_grid_carbon(
        self,
        lighting_hours: float,
        city_key: str = 'bologna'
    ) -> Dict[str, Any]:
        grid_factor = self.eco.grid_carbon_italy_g_kwh if city_key == 'bologna' else self.eco.grid_carbon_uk_g_kwh

        kwh_hps = (self.eco.hps_baseline_power_w * lighting_hours) / 1000.0
        kwh_led = (self.eco.grid_led_baseline_power_w * lighting_hours) / 1000.0
        co2_hps_kg = (kwh_hps * grid_factor) / 1000.0
        co2_led_kg = (kwh_led * grid_factor) / 1000.0

        return {
            'lighting_hours_yr': round(lighting_hours, 0),
            'grid_intensity_g_kwh': grid_factor,
            'avoided_kwh_vs_hps': round(kwh_hps, 1),
            'avoided_kwh_vs_grid_led': round(kwh_led, 1),
            'avoided_co2e_vs_hps_kg': round(co2_hps_kg, 1),
            'avoided_co2e_vs_grid_led_kg': round(co2_led_kg, 1)
        }


# Functional adapters
def calculate_evaporative_cooling(df_h, df_w, eco=None):
    return UrbanEcosystemServices(eco=eco).evaporative_cooling(df_h, df_w)

def calculate_stormwater_attenuation(df_h, df_w, geom=None):
    return UrbanEcosystemServices(geom=geom).stormwater_attenuation(df_h, df_w)

def calculate_particulate_biofiltration(df_w, df_c, city='bologna', geom=None, eco=None):
    return UrbanEcosystemServices(geom, eco).particulate_biofiltration(df_w, df_c, city)

def calculate_avoided_grid_carbon(lit_h, city='bologna', eco=None):
    return UrbanEcosystemServices(eco=eco).avoided_grid_carbon(lit_h, city)
