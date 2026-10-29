"""Photovoltaic canopy generation and LiFePO4 battery microgrid engine."""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from src.config import GeometricConfig, ElectricalConfig


class PhotovoltaicCanopy:
    """Circular monocrystalline solar photovoltaic canopy model."""

    def __init__(
        self,
        geom: Optional[GeometricConfig] = None,
        elec: Optional[ElectricalConfig] = None
    ):
        self.geom = geom or GeometricConfig()
        self.elec = elec or ElectricalConfig()

    def cell_temperature(
        self,
        ambient_temp_c: np.ndarray,
        irradiance_w_m2: np.ndarray,
        noct_c: float = 45.0
    ) -> np.ndarray:
        return ambient_temp_c + (irradiance_w_m2 / 800.0) * (noct_c - 20.0)

    def calculate_power(self, df_weather: pd.DataFrame) -> pd.Series:
        cell_temps = self.cell_temperature(
            df_weather['temp_air_c'].values,
            df_weather['ghi_w_m2'].values
        )
        temp_derate = np.clip(1.0 + self.elec.pv_temp_coeff_per_k * (cell_temps - 25.0), 0.5, 1.2)

        power_w = (
            self.geom.area_catchment_m2 *
            self.elec.pv_efficiency_ref *
            df_weather['ghi_w_m2'].values *
            temp_derate *
            self.elec.bos_combined_efficiency *
            self.elec.canopy_geometry_factor
        )
        return pd.Series(np.maximum(0.0, power_w), index=df_weather.index, name='p_pv_w')

    def calculate_lighting_load(self, df_weather: pd.DataFrame) -> pd.Series:
        load_w = np.where(df_weather['is_civil_night'].values, self.elec.power_light_w, 0.0)
        return pd.Series(load_w, index=df_weather.index, name='p_light_w')


class BatteryMicrogrid:
    """12V LiFePO4 battery microgrid charge controller and energy storage engine."""

    def __init__(
        self,
        capacity_kwh: Optional[float] = None,
        elec: Optional[ElectricalConfig] = None
    ):
        self.elec = elec or ElectricalConfig()
        self.capacity_kwh = capacity_kwh if capacity_kwh is not None else self.elec.battery_nominal_capacity_kwh
        self.e_min = self.capacity_kwh * self.elec.battery_soc_min
        self.e_max = self.capacity_kwh * self.elec.battery_soc_max

    def simulate(
        self,
        df_weather: pd.DataFrame,
        pv_power_w: pd.Series,
        light_power_w: pd.Series,
        pump_power_w: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        current_energy_kwh = self.capacity_kwh * self.elec.battery_initial_soc
        p_pump = pump_power_w.values if pump_power_w is not None else np.zeros(len(df_weather))
        p_load = light_power_w.values + p_pump + self.elec.power_aux_w
        p_pv = pv_power_w.values
        temp_air = df_weather['temp_air_c'].values

        n_hours = len(df_weather)
        soc_arr = np.zeros(n_hours)
        energy_arr = np.zeros(n_hours)
        curtailed_arr = np.zeros(n_hours)
        unserved_arr = np.zeros(n_hours)
        blackout_arr = np.zeros(n_hours, dtype=bool)

        eta_chg = self.elec.battery_charge_efficiency
        eta_dis = self.elec.battery_discharge_efficiency
        subzero_derate = self.elec.subzero_charge_derate

        for t in range(n_hours):
            net_w = p_pv[t] - p_load[t]
            dt_h = 1.0

            if net_w >= 0.0:
                eff_eta = eta_chg * (subzero_derate if temp_air[t] < 0.0 else 1.0)
                charge_kwh = (net_w / 1000.0) * eff_eta * dt_h
                space_kwh = self.e_max - current_energy_kwh

                if charge_kwh <= space_kwh:
                    current_energy_kwh += charge_kwh
                    curtailed_arr[t] = 0.0
                else:
                    current_energy_kwh = self.e_max
                    curtailed_arr[t] = (charge_kwh - space_kwh) / eff_eta

                unserved_arr[t] = 0.0
                blackout_arr[t] = False
            else:
                curtailed_arr[t] = 0.0
                req_dis_kwh = (abs(net_w) / 1000.0) / eta_dis * dt_h
                avail_kwh = max(0.0, current_energy_kwh - self.e_min)

                if avail_kwh >= req_dis_kwh:
                    current_energy_kwh -= req_dis_kwh
                    unserved_arr[t] = 0.0
                    blackout_arr[t] = False
                else:
                    current_energy_kwh = self.e_min
                    delivered_w = p_pv[t] + (avail_kwh * eta_dis / dt_h) * 1000.0
                    unserved_w = max(0.0, p_load[t] - delivered_w)
                    unserved_arr[t] = (unserved_w / 1000.0) * dt_h
                    blackout_arr[t] = unserved_w > 1.0

            energy_arr[t] = current_energy_kwh
            soc_arr[t] = current_energy_kwh / self.capacity_kwh

        return pd.DataFrame({
            'p_pv_w': p_pv,
            'p_light_w': light_power_w.values,
            'p_pump_w': p_pump,
            'p_load_total_w': p_load,
            'battery_energy_kwh': energy_arr,
            'battery_soc': soc_arr,
            'battery_curtailed_kwh': curtailed_arr,
            'unserved_energy_kwh': unserved_arr,
            'is_loss_of_load': blackout_arr
        }, index=df_weather.index)

    def evaluate(self, sim_df: pd.DataFrame) -> Dict[str, Any]:
        pv_kwh = sim_df['p_pv_w'].sum() / 1000.0
        light_kwh = sim_df['p_light_w'].sum() / 1000.0
        pump_kwh = sim_df['p_pump_w'].sum() / 1000.0
        load_kwh = sim_df['p_load_total_w'].sum() / 1000.0
        curtailed_kwh = sim_df['battery_curtailed_kwh'].sum()
        unserved_kwh = sim_df['unserved_energy_kwh'].sum()

        lit_hours = (sim_df['p_light_w'] > 0).sum()
        blackout_hours = sim_df['is_loss_of_load'].sum()
        lolp = (blackout_hours / lit_hours) if lit_hours > 0 else 0.0

        ediff = np.diff(sim_df['battery_energy_kwh'].values)
        discharge_kwh = -np.sum(ediff[ediff < 0])
        cycles = discharge_kwh / self.capacity_kwh

        return {
            'total_pv_generation_kwh': round(pv_kwh, 2),
            'total_lighting_demand_kwh': round(light_kwh, 2),
            'total_pump_demand_kwh': round(pump_kwh, 2),
            'total_load_demand_kwh': round(load_kwh, 2),
            'total_curtailed_kwh': round(curtailed_kwh, 2),
            'total_unserved_kwh': round(unserved_kwh, 3),
            'lighting_hours': int(lit_hours),
            'blackout_hours': int(blackout_hours),
            'loss_of_load_probability_lolp': round(lolp, 4),
            'electrical_reliability_pct': round((1.0 - lolp) * 100.0, 2),
            'min_soc': round(sim_df['battery_soc'].min(), 3),
            'mean_soc': round(sim_df['battery_soc'].mean(), 3),
            'equivalent_full_cycles': round(cycles, 1)
        }


# Functional adapters
def calculate_hourly_pv_power(df_weather, geom=None, elec=None):
    return PhotovoltaicCanopy(geom, elec).calculate_power(df_weather)

def calculate_hourly_lighting_load(df_weather, elec=None):
    return PhotovoltaicCanopy(elec=elec).calculate_lighting_load(df_weather)

def simulate_battery_microgrid(df_weather, pv, light, pump=None, battery_capacity_kwh=None, geom=None, elec=None):
    return BatteryMicrogrid(battery_capacity_kwh, elec).simulate(df_weather, pv, light, pump)

def evaluate_microgrid_performance(sim_df, c_bat_kwh):
    return BatteryMicrogrid(c_bat_kwh).evaluate(sim_df)
