from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from src.config import BuildingArchetype, ScenarioConfig, SCENARIO_CONFIGS
from src.emission_factors import EmissionFactorDatabase
from src.grid_decarbonisation import GridDecarbonisationModel
from src.inventory import BuildingInventory


@dataclass
class LifeCycleCarbonResult:
    scenario_id: str
    name: str
    gia: float
    a1_a3_product: float
    a4_transport: float
    a5_construction: float
    a1_a5_upfront: float
    b1_refrigerant_leakage: float
    b2_b3_maintenance: float
    b4_replacement: float
    b5_refurbishment: float
    b1_b5_inuse_embodied: float
    b6_operational_by_trajectory: Dict[str, float]
    b6_annual_timeseries: Dict[str, List[float]]
    c1_deconstruction: float
    c2_transport: float
    c3_waste_processing: float
    c4_disposal_and_venting: float
    c1_c4_end_of_life: float
    module_d_credits: float
    total_wlc_by_trajectory: Dict[str, float]
    elemental_a1_a5: Dict[str, float] = field(default_factory=dict)
    annual_cumulative_carbon: Dict[str, List[float]] = field(default_factory=dict)

    def upfront_per_m2(self) -> float:
        return self.a1_a5_upfront / self.gia

    def total_wlc_per_m2(self, trajectory: str = "desnz_central") -> float:
        return self.total_wlc_by_trajectory[trajectory] / self.gia

    def operational_per_m2(self, trajectory: str = "desnz_central") -> float:
        return self.b6_operational_by_trajectory[trajectory] / self.gia


class WholeLifeCarbonEngine:
    """EN 15978 / RICS 2nd Edition Whole-Life Carbon accounting engine."""

    ANNUAL_MEP_DECARB_RATE: float = 0.01  # 1% compound decarbonisation for future replacements

    def __init__(
        self,
        db: Optional[EmissionFactorDatabase] = None,
        grid: Optional[GridDecarbonisationModel] = None,
        inventory: Optional[BuildingInventory] = None,
        archetype: Optional[BuildingArchetype] = None,
    ):
        self.archetype = archetype or BuildingArchetype()
        self.db = db or EmissionFactorDatabase()
        self.grid = grid or GridDecarbonisationModel()
        self.inventory = inventory or BuildingInventory(archetype=self.archetype)

    def calculate_scenario(self, scenario: ScenarioConfig) -> LifeCycleCarbonResult:
        items = self.inventory.get_items_for_scenario(scenario.scenario_id)
        thermal_loads = self.inventory.calculate_peak_thermal_load(scenario)

        # 1. Modules A1-A3: Product Stage & Elemental Grouping
        elemental_a1_a3: Dict[str, float] = {
            "0.0 Demolition": 0.0,
            "1.0 Substructure": 0.0,
            "2.0 Superstructure": 0.0,
            "3.0 Facade & Envelope": 0.0,
            "4.0 Internal Finishes": 0.0,
            "5.0 MEP Services": 0.0,
        }
        total_a1_a3 = 0.0
        total_a4 = 0.0
        total_b4_replacements = 0.0
        module_d_credits = 0.0

        for _, row in items.iterrows():
            group = str(row["nrm_element_group"])
            mat_id = str(row["material_id"])
            qty = float(row["quantity"])
            waste = float(row["waste_rate"])
            dist_km = float(row["transport_distance_km"])
            lifespan = float(row["service_life_years"])

            if mat_id == "none" or qty <= 0.0:
                continue

            ecf = self.db.get_cradle_to_gate_ecf(mat_id)
            bio_ecf = self.db.get_biogenic_factor(mat_id)

            # A1-A3 Product Carbon [kg CO2e]
            item_a1_a3 = qty * ecf * (1.0 + waste)
            elemental_a1_a3[group] = elemental_a1_a3.get(group, 0.0) + item_a1_a3
            total_a1_a3 += item_a1_a3

            # Module D: Biogenic carbon sequestered (reported separately per RICS rules)
            if bio_ecf < 0.0:
                module_d_credits += qty * bio_ecf

            # A4 Transport: Mass (tonnes) * distance * EF
            item_mass_tonnes = qty / 1000.0 if row["unit"] == "kg" else (qty * 25.0) / 1000.0
            item_a4 = item_mass_tonnes * dist_km * self.db.HGV_FREIGHT_FACTOR_KG_PER_TONNE_KM
            total_a4 += item_a4

            # B4 Replacements over 60-year RSP: floor((60 - 1) / Lifespan)
            if lifespan < 60.0:
                num_replacements = int((self.archetype.reference_study_period - 1) // lifespan)
                for r in range(1, num_replacements + 1):
                    rep_year = int(r * lifespan)
                    decarb_discount = (1.0 - self.ANNUAL_MEP_DECARB_RATE) ** rep_year
                    total_b4_replacements += item_a1_a3 * decarb_discount

        # 2. Module A5: Site installation energy, waste handling & compound
        if scenario.scenario_id == "scenario_1":
            a5_construction = 2.0 * self.archetype.gia
        elif scenario.scenario_id == "scenario_2":
            a5_construction = 6.0 * self.archetype.gia
        else:
            a5_construction = self.db.DEFAULT_A5_SITE_INSTALLATION_KG_PER_M2 * self.archetype.gia

        total_a1_a5 = total_a1_a3 + total_a4 + a5_construction

        # 3. Module B1: In-Use Fugitive Refrigerant Leakage (CIBSE TM65 §4.2)
        initial_charge_kg = thermal_loads["initial_refrigerant_charge_kg"]
        gwp = self.db.get_refrigerant_gwp(scenario.refrigerant_type)
        annual_refrig_leak_kg_co2e = initial_charge_kg * scenario.annual_leakage_rate * gwp
        total_b1_refrig = annual_refrig_leak_kg_co2e * self.archetype.reference_study_period

        # 4. Modules B2-B3: Routine Maintenance & In-Use Repair
        b2_b3_maint = 0.03 * total_a1_a5

        # In B4 replacements, add refrigerant recovery loss at replacement intervals (15 years)
        hp_lifespan = 15
        num_hp_replacements = int((self.archetype.reference_study_period - 1) // hp_lifespan)
        ref_replacement_vent_loss = (
            num_hp_replacements * initial_charge_kg * (1.0 - scenario.eol_recovery_efficiency) * gwp
        )
        total_b4 = total_b4_replacements + ref_replacement_vent_loss
        b5_refurbishment = 0.0
        total_b1_b5 = total_b1_refrig + b2_b3_maint + total_b4 + b5_refurbishment

        # 5. Module B6: Dynamic Operational Energy across all grid trajectories
        b6_by_trajectory: Dict[str, float] = {}
        b6_annual_series: Dict[str, List[float]] = {}
        annual_cumulative_carbon: Dict[str, List[float]] = {}

        annual_elec_kwh = (
            max(0.0, scenario.elec_gross_kwh_per_m2_yr - scenario.pv_generation_kwh_per_m2_yr)
            * self.archetype.gia
        )
        annual_gas_kwh = scenario.gas_kwh_per_m2_yr * self.archetype.gia

        for traj in self.grid.trajectories:
            annual_emissions: List[float] = []
            cum_emissions: List[float] = []
            running_cum = total_a1_a5

            for yr_idx, calendar_year in enumerate(self.grid.years):
                ef_elec = self.grid.get_electricity_factor(calendar_year, traj)
                ef_gas = self.grid.get_gas_factor(calendar_year)
                yr_b6 = (annual_elec_kwh * ef_elec) + (annual_gas_kwh * ef_gas)

                # Add annual in-use embodied components (B1 leakage + pro-rated B2/B3/B4)
                yr_inuse = annual_refrig_leak_kg_co2e + (b2_b3_maint / 60.0)
                study_year = yr_idx + 1
                if study_year in [15, 30, 45]:
                    yr_inuse += (total_b4 / num_hp_replacements) if num_hp_replacements > 0 else 0.0

                annual_emissions.append(yr_b6)
                running_cum += yr_b6 + yr_inuse
                cum_emissions.append(running_cum)

            b6_by_trajectory[traj] = sum(annual_emissions)
            b6_annual_series[traj] = annual_emissions
            annual_cumulative_carbon[traj] = cum_emissions

        # 6. Modules C1-C4: End of Life Stage
        if scenario.structure_retained_pct >= 1.0 and scenario.scenario_id == "scenario_1":
            c1_deconstruction = 1.0 * self.archetype.gia
        elif scenario.structure_retained_pct >= 1.0:
            c1_deconstruction = self.db.DEMOLITION_C1_STRIPOUT_KG_PER_M2 * self.archetype.gia
        else:
            c1_deconstruction = self.db.DEMOLITION_C1_FULL_KG_PER_M2 * self.archetype.gia

        c2_transport = 1.5 * self.archetype.gia
        c3_processing = 2.0 * self.archetype.gia
        # C4 Refrigerant End of Life Venting
        c4_refrig_vent = initial_charge_kg * (1.0 - scenario.eol_recovery_efficiency) * gwp
        c4_disposal = (1.5 * self.archetype.gia) + c4_refrig_vent
        total_c1_c4 = c1_deconstruction + c2_transport + c3_processing + c4_disposal

        # 7. Total Whole-Life Carbon (A1-C4 strictly, Module D separate per RICS rules)
        total_wlc_by_traj = {
            traj: total_a1_a5 + total_b1_b5 + b6_by_trajectory[traj] + total_c1_c4
            for traj in self.grid.trajectories
        }

        return LifeCycleCarbonResult(
            scenario_id=scenario.scenario_id,
            name=scenario.name,
            gia=self.archetype.gia,
            a1_a3_product=total_a1_a3,
            a4_transport=total_a4,
            a5_construction=a5_construction,
            a1_a5_upfront=total_a1_a5,
            b1_refrigerant_leakage=total_b1_refrig,
            b2_b3_maintenance=b2_b3_maint,
            b4_replacement=total_b4,
            b5_refurbishment=b5_refurbishment,
            b1_b5_inuse_embodied=total_b1_b5,
            b6_operational_by_trajectory=b6_by_trajectory,
            b6_annual_timeseries=b6_annual_series,
            c1_deconstruction=c1_deconstruction,
            c2_transport=c2_transport,
            c3_waste_processing=c3_processing,
            c4_disposal_and_venting=c4_disposal,
            c1_c4_end_of_life=total_c1_c4,
            module_d_credits=module_d_credits,
            total_wlc_by_trajectory=total_wlc_by_traj,
            elemental_a1_a5=elemental_a1_a3,
            annual_cumulative_carbon=annual_cumulative_carbon,
        )

    def calculate_all(self) -> Dict[str, LifeCycleCarbonResult]:
        results: Dict[str, LifeCycleCarbonResult] = {}
        for sc_id, sc_cfg in SCENARIO_CONFIGS.items():
            results[sc_id] = self.calculate_scenario(sc_cfg)
        return results

    def calculate_payback_years(
        self,
        baseline_res: LifeCycleCarbonResult,
        scenario_res: LifeCycleCarbonResult,
        trajectory: str = "desnz_central",
    ) -> Optional[int]:
        """Calculates earliest year T* where cumulative carbon of intervention <= baseline."""
        base_cum = baseline_res.annual_cumulative_carbon[trajectory]
        scen_cum = scenario_res.annual_cumulative_carbon[trajectory]

        for yr_idx in range(len(base_cum)):
            if scen_cum[yr_idx] <= base_cum[yr_idx]:
                return yr_idx + 1
        return None

