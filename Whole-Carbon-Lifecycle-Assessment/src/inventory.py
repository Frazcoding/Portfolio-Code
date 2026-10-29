from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from src.config import BuildingArchetype, ScenarioConfig, SCENARIO_CONFIGS


class BuildingInventory:
    """Elemental Bill of Quantities (BoQ) and HVAC thermal capacity sizing engine."""

    AIR_HEAT_CAPACITY: float = 1.205 * 1005  # J/(m3*K) air density * specific heat
    WINTER_DESIGN_DELTA_T: float = 24.0  # Edinburgh: +21C internal, -3C design external
    INTERNAL_HEAT_GAIN_W_PER_M2: float = 25.0

    def __init__(self, data_path: Optional[Path] = None, archetype: Optional[BuildingArchetype] = None):
        if data_path is None:
            data_path = Path(__file__).resolve().parent.parent / "data" / "bill_of_quantities.csv"
        self.data_path = Path(data_path)
        self.df = pd.read_csv(self.data_path)
        self.archetype = archetype or BuildingArchetype()

    def get_items_for_scenario(self, scenario_id: str) -> pd.DataFrame:
        subset = self.df[self.df["scenario_id"] == scenario_id].copy()
        if subset.empty:
            raise KeyError(f"No items found for scenario '{scenario_id}'.")
        return subset

    def calculate_peak_thermal_load(self, scenario: ScenarioConfig) -> Dict[str, float]:
        """CIBSE Guide A thermal peak load sizing based on envelope U-values and infiltration."""
        u_wall = scenario.u_wall
        u_win = scenario.u_window
        u_roof = scenario.u_roof

        h_trans = (
            u_wall * self.archetype.opaque_facade_area
            + u_win * self.archetype.glazed_facade_area
            + u_roof * self.archetype.roof_area
        )  # W/K

        building_volume = self.archetype.gia * self.archetype.floor_to_floor_height  # m3
        n_inf = scenario.q50_air_permeability / 20.0  # Kronvall-Persily rule of thumb air changes / h
        n_vent = 1.2 * (1.0 - scenario.mvhr_efficiency)  # Effective ventilation air changes / h

        h_vent = (n_inf + n_vent) * building_volume * self.AIR_HEAT_CAPACITY / 3600.0  # W/K

        peak_heat_kw = (h_trans + h_vent) * self.WINTER_DESIGN_DELTA_T / 1000.0
        internal_heat_gain_kw = (self.INTERNAL_HEAT_GAIN_W_PER_M2 * self.archetype.gia) / 1000.0
        peak_cool_kw = max(200.0, internal_heat_gain_kw * 1.15)

        installed_capacity_kw = max(peak_heat_kw, peak_cool_kw)
        ref_charge_kg = installed_capacity_kw * scenario.refrigerant_charge_kg_per_kw

        return {
            "peak_heating_kw": peak_heat_kw,
            "peak_cooling_kw": peak_cool_kw,
            "installed_capacity_kw": installed_capacity_kw,
            "initial_refrigerant_charge_kg": ref_charge_kg,
        }

