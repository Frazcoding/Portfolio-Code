"""Hydrology, FAO-56 Penman-Monteith crop evapotranspiration, and reservoir mass balance."""

import math
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from src.config import GeometricConfig, HydraulicConfig


class PenmanMonteithHydrology:
    """Standardized FAO-56 Penman-Monteith reference crop evapotranspiration model."""

    @staticmethod
    def saturation_vapor_pressure_kpa(temp_c: float) -> float:
        return 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))

    @classmethod
    def vapor_pressure_slope_kpa_c(cls, temp_c: float) -> float:
        e_sat = cls.saturation_vapor_pressure_kpa(temp_c)
        return (4098.0 * e_sat) / ((temp_c + 237.3) ** 2)

    @staticmethod
    def psychrometric_constant_kpa_c(pressure_pa: float) -> float:
        return 0.000665 * (pressure_pa / 1000.0)

    @staticmethod
    def wind_speed_2m(wind_speed_10m: float) -> float:
        # FAO-56 logarithmic conversion: u2 = u10 * 0.748
        return max(0.2, wind_speed_10m * 0.748)

    @classmethod
    def hourly_et0(
        cls,
        temp_air_c: float,
        rh_percent: float,
        wind_speed_10m: float,
        ghi_w_m2: float,
        pressure_pa: float,
        is_daylight: bool
    ) -> float:
        t_c = float(temp_air_c)
        rh = max(5.0, min(100.0, float(rh_percent)))
        u2 = cls.wind_speed_2m(float(wind_speed_10m))
        p = float(pressure_pa) if pressure_pa > 50000.0 else 101325.0

        delta = cls.vapor_pressure_slope_kpa_c(t_c)
        gamma = cls.psychrometric_constant_kpa_c(p)
        e_sat = cls.saturation_vapor_pressure_kpa(t_c)
        e_act = e_sat * (rh / 100.0)
        vpd = max(0.0, e_sat - e_act)

        # Net radiation Rn (MJ/m^2/h)
        rs = ghi_w_m2 * 0.0036
        rns = (1.0 - 0.23) * rs

        sigma = 2.043e-10
        t_k = t_c + 273.16
        cloud = 0.2 + 0.8 * min(1.0, max(0.1, rs / 2.5)) if is_daylight else 0.4
        emissivity = 0.34 - 0.14 * math.sqrt(max(0.1, e_act))
        rnl = sigma * (t_k ** 4) * emissivity * cloud

        rn = max(0.0, rns - rnl) if is_daylight else max(-0.2, -rnl)
        g = 0.1 * rn if is_daylight else 0.5 * rn
        cd = 0.24 if is_daylight else 0.96

        num = 0.408 * delta * (rn - g) + gamma * (37.0 / (t_c + 273.0)) * u2 * vpd
        den = delta + gamma * (1.0 + cd * u2)
        return max(0.0, num / den)

    @classmethod
    def compute_et0_series(cls, df_weather: pd.DataFrame) -> pd.Series:
        et0_vals = [
            cls.hourly_et0(
                row['temp_air_c'], row['rh_percent'], row['wind_speed_m_s'],
                row['ghi_w_m2'], row['pressure_pa'], row['is_daylight']
            )
            for _, row in df_weather.iterrows()
        ]
        return pd.Series(et0_vals, index=df_weather.index, name='et0_mm_h')


class ReservoirMassBalance:
    """Dynamic rainwater storage, runoff capture, and irrigation mass balance."""

    def __init__(
        self,
        geom: Optional[GeometricConfig] = None,
        hydr: Optional[HydraulicConfig] = None
    ):
        self.geom = geom or GeometricConfig()
        self.hydr = hydr or HydraulicConfig()

    def simulate(
        self,
        df_weather: pd.DataFrame,
        df_crop: pd.DataFrame,
        use_dynamic_fao56: bool = True
    ) -> pd.DataFrame:
        n_hours = len(df_weather)
        precip = df_weather['precip_mm_h'].values
        rain_l = precip * self.geom.area_catchment_m2 * self.hydr.runoff_coefficient * self.hydr.filter_efficiency

        if use_dynamic_fao56:
            et0_series = PenmanMonteithHydrology.compute_et0_series(df_weather)
            kc_map = dict(zip(df_crop['month'], df_crop['kc']))
            kc_hourly = df_weather['month'].map(kc_map).values
            irr_req_l = (et0_series.values * kc_hourly * self.geom.foliage_area_total_m2) / self.hydr.irrigation_drip_efficiency
        else:
            irr_req_l = np.full(n_hours, self.hydr.baseline_irrigation_l_day / 24.0)

        df_daily = pd.DataFrame({'doy': df_weather['day_of_year'], 'req': irr_req_l})
        daily_reqs = df_daily.groupby('doy')['req'].sum()

        current_tank_l = self.hydr.tank_initial_volume_l
        tank_vol_arr = np.zeros(n_hours)
        water_level_arr = np.zeros(n_hours)
        overflow_arr = np.zeros(n_hours)
        delivered_arr = np.zeros(n_hours)
        deficit_arr = np.zeros(n_hours)
        drought_arr = np.zeros(n_hours, dtype=bool)

        for t in range(n_hours):
            current_tank_l += rain_l[t]
            if current_tank_l > self.geom.volume_tank_max_l:
                overflow_arr[t] = current_tank_l - self.geom.volume_tank_max_l
                current_tank_l = self.geom.volume_tank_max_l
            else:
                overflow_arr[t] = 0.0

            # Morning pulse delivery at 07:00 AM
            if df_weather['hour'].iloc[t] == 7:
                req = daily_reqs.loc[df_weather['day_of_year'].iloc[t]]
                if current_tank_l >= req:
                    delivered_arr[t] = req
                    current_tank_l -= req
                    deficit_arr[t] = 0.0
                    drought_arr[t] = False
                else:
                    delivered_arr[t] = current_tank_l
                    deficit_arr[t] = req - current_tank_l
                    current_tank_l = 0.0
                    drought_arr[t] = True

            tank_vol_arr[t] = current_tank_l
            water_level_arr[t] = (current_tank_l / 1000.0) / self.geom.area_tank_m2

        return pd.DataFrame({
            'rain_harvested_l': rain_l,
            'irr_required_l': irr_req_l,
            'irr_delivered_l': delivered_arr,
            'irr_deficit_l': deficit_arr,
            'tank_volume_l': tank_vol_arr,
            'tank_water_level_m': water_level_arr,
            'overflow_l': overflow_arr,
            'is_drought_stress': drought_arr
        }, index=df_weather.index)

    @staticmethod
    def evaluate(sim_df: pd.DataFrame) -> Dict[str, Any]:
        h_rain = sim_df['rain_harvested_l'].sum()
        req = sim_df['irr_required_l'].sum()
        deliv = sim_df['irr_delivered_l'].sum()
        defic = sim_df['irr_deficit_l'].sum()
        over = sim_df['overflow_l'].sum()
        d_days = int(sim_df['is_drought_stress'].sum())
        suff = (deliv / req * 100.0) if req > 0 else 100.0

        return {
            'total_rain_harvested_l': round(h_rain, 1),
            'total_irr_required_l': round(req, 1),
            'total_irr_delivered_l': round(deliv, 1),
            'total_irr_deficit_l': round(defic, 1),
            'total_overflow_l': round(over, 1),
            'water_self_sufficiency_pct': round(suff, 1),
            'drought_stress_days': d_days,
            'min_tank_volume_l': round(sim_df['tank_volume_l'].min(), 1),
            'mean_tank_volume_l': round(sim_df['tank_volume_l'].mean(), 1)
        }


# Functional adapters
def calculate_hourly_fao56_penman_monteith_et0(t, rh, ws, ghi, p, dayl):
    return PenmanMonteithHydrology.hourly_et0(t, rh, ws, ghi, p, dayl)

def compute_hourly_et0_series(df_w):
    return PenmanMonteithHydrology.compute_et0_series(df_w)

def simulate_hydrology_and_storage(df_w, df_c, geom=None, hydr=None, use_dynamic_fao56=True):
    return ReservoirMassBalance(geom, hydr).simulate(df_w, df_c, use_dynamic_fao56)

def evaluate_hydrology_performance(sim_df):
    return ReservoirMassBalance.evaluate(sim_df)
