from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class BuildingArchetype:
    gia: float = 7500.0
    storeys: int = 5
    floorplate_area: float = 1500.0
    floor_to_floor_height: float = 3.8
    total_height: float = 19.0
    perimeter_length: float = 160.0
    window_to_wall_ratio: float = 0.45
    gross_facade_area: float = 3040.0
    glazed_facade_area: float = 1368.0
    opaque_facade_area: float = 1672.0
    roof_area: float = 1500.0
    ground_slab_area: float = 1500.0
    upper_floor_slabs_area: float = 6000.0
    reference_study_period: int = 60
    base_year: int = 2026


@dataclass(frozen=True)
class EconomicParameters:
    discount_rate_yr1_30: float = 0.035
    discount_rate_yr31_60: float = 0.030
    electricity_tariff_base: float = 0.240
    gas_tariff_base: float = 0.075
    energy_real_escalation_rate: float = 0.005


@dataclass(frozen=True)
class ScenarioConfig:
    scenario_id: str
    name: str
    short_name: str
    structure_retained_pct: float
    u_wall: float
    u_window: float
    u_roof: float
    q50_air_permeability: float
    heating_cop: float
    cooling_seer: float
    mvhr_efficiency: float
    heating_fuel: str
    gas_kwh_per_m2_yr: float
    elec_gross_kwh_per_m2_yr: float
    pv_generation_kwh_per_m2_yr: float
    refrigerant_type: str
    refrigerant_charge_kg_per_kw: float
    annual_leakage_rate: float
    eol_recovery_efficiency: float
    upfront_capex_per_m2: float
    demolition_cost_per_m2: float
    annual_maintenance_per_m2: float
    mep_replacement_pct: float

    @property
    def net_operational_eui(self) -> float:
        return self.gas_kwh_per_m2_yr + max(0.0, self.elec_gross_kwh_per_m2_yr - self.pv_generation_kwh_per_m2_yr)


SCENARIO_CONFIGS: Dict[str, ScenarioConfig] = {
    "scenario_1": ScenarioConfig(
        scenario_id="scenario_1",
        name="Baseline Counterfactual (Do-Minimum Gas Replacement)",
        short_name="Baseline (Gas)",
        structure_retained_pct=1.0,
        u_wall=1.60,
        u_window=2.80,
        u_roof=1.20,
        q50_air_permeability=10.0,
        heating_cop=0.92,
        cooling_seer=2.80,
        mvhr_efficiency=0.00,
        heating_fuel="gas",
        gas_kwh_per_m2_yr=90.0,
        elec_gross_kwh_per_m2_yr=50.0,
        pv_generation_kwh_per_m2_yr=0.0,
        refrigerant_type="R410A",
        refrigerant_charge_kg_per_kw=0.45,
        annual_leakage_rate=0.050,
        eol_recovery_efficiency=0.90,
        upfront_capex_per_m2=420.0,
        demolition_cost_per_m2=0.0,
        annual_maintenance_per_m2=14.50,
        mep_replacement_pct=1.00,
    ),
    "scenario_2": ScenarioConfig(
        scenario_id="scenario_2",
        name="Deep Retrofit (Retained Structure + ASHP R290)",
        short_name="Deep Retrofit",
        structure_retained_pct=1.0,
        u_wall=0.18,
        u_window=0.85,
        u_roof=0.12,
        q50_air_permeability=2.0,
        heating_cop=3.60,
        cooling_seer=4.20,
        mvhr_efficiency=0.82,
        heating_fuel="electricity",
        gas_kwh_per_m2_yr=0.0,
        elec_gross_kwh_per_m2_yr=69.0,
        pv_generation_kwh_per_m2_yr=14.0,
        refrigerant_type="R290",
        refrigerant_charge_kg_per_kw=0.18,
        annual_leakage_rate=0.025,
        eol_recovery_efficiency=0.95,
        upfront_capex_per_m2=1450.0,
        demolition_cost_per_m2=35.0,
        annual_maintenance_per_m2=18.20,
        mep_replacement_pct=0.80,
    ),
    "scenario_3": ScenarioConfig(
        scenario_id="scenario_3",
        name="Standard New Build (Demolition + Steel/Concrete + R32)",
        short_name="Standard New Build",
        structure_retained_pct=0.0,
        u_wall=0.22,
        u_window=1.20,
        u_roof=0.15,
        q50_air_permeability=3.0,
        heating_cop=3.40,
        cooling_seer=3.80,
        mvhr_efficiency=0.75,
        heating_fuel="electricity",
        gas_kwh_per_m2_yr=0.0,
        elec_gross_kwh_per_m2_yr=65.0,
        pv_generation_kwh_per_m2_yr=10.0,
        refrigerant_type="R32",
        refrigerant_charge_kg_per_kw=0.32,
        annual_leakage_rate=0.035,
        eol_recovery_efficiency=0.95,
        upfront_capex_per_m2=2450.0,
        demolition_cost_per_m2=165.0,
        annual_maintenance_per_m2=19.50,
        mep_replacement_pct=0.85,
    ),
    "scenario_4": ScenarioConfig(
        scenario_id="scenario_4",
        name="Exemplar Low-Carbon New Build (Mass Timber + 70% GGBS)",
        short_name="Timber New Build",
        structure_retained_pct=0.0,
        u_wall=0.14,
        u_window=0.75,
        u_roof=0.10,
        q50_air_permeability=0.8,
        heating_cop=4.10,
        cooling_seer=4.80,
        mvhr_efficiency=0.88,
        heating_fuel="electricity",
        gas_kwh_per_m2_yr=0.0,
        elec_gross_kwh_per_m2_yr=67.0,
        pv_generation_kwh_per_m2_yr=22.0,
        refrigerant_type="R290",
        refrigerant_charge_kg_per_kw=0.18,
        annual_leakage_rate=0.020,
        eol_recovery_efficiency=0.95,
        upfront_capex_per_m2=2850.0,
        demolition_cost_per_m2=185.0,
        annual_maintenance_per_m2=21.00,
        mep_replacement_pct=0.80,
    ),
}

