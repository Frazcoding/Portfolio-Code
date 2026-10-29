from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from src.config import BuildingArchetype, EconomicParameters, ScenarioConfig, SCENARIO_CONFIGS
from src.carbon_calculator import LifeCycleCarbonResult
from src.grid_decarbonisation import GridDecarbonisationModel


@dataclass
class LifeCycleCostResult:
    scenario_id: str
    name: str
    gia: float
    initial_capex: float
    demolition_capex: float
    total_upfront_capex: float
    discounted_maintenance_opex: float
    discounted_energy_bills: float
    discounted_replacement_capex: float
    financial_npv: float
    discounted_societal_carbon_cost: float
    societal_npv: float
    marginal_abatement_cost_gbp_per_tonne: float
    annual_cashflows: List[float]
    annual_discount_factors: List[float]

    def financial_npv_per_m2(self) -> float:
        return self.financial_npv / self.gia

    def upfront_capex_per_m2(self) -> float:
        return self.total_upfront_capex / self.gia


class LifeCycleCostingEngine:
    """BS ISO 15686-5 Life Cycle Costing & HM Treasury Green Book discount engine."""

    def __init__(
        self,
        econ_params: Optional[EconomicParameters] = None,
        archetype: Optional[BuildingArchetype] = None,
        grid_model: Optional[GridDecarbonisationModel] = None,
    ):
        self.econ = econ_params or EconomicParameters()
        self.archetype = archetype or BuildingArchetype()
        self.grid = grid_model or GridDecarbonisationModel()
        self.discount_factors = self._compute_discount_factors()

    def _compute_discount_factors(self) -> List[float]:
        """HM Treasury Green Book discounting: 3.5% (Yr 1-30), 3.0% (Yr 31-60)."""
        df_list: List[float] = []
        cumulative_df = 1.0
        for t in range(1, self.archetype.reference_study_period + 1):
            rate = self.econ.discount_rate_yr1_30 if t <= 30 else self.econ.discount_rate_yr31_60
            cumulative_df *= 1.0 / (1.0 + rate)
            df_list.append(cumulative_df)
        return df_list

    def calculate_scenario(
        self,
        scenario: ScenarioConfig,
        carbon_result: LifeCycleCarbonResult,
        baseline_cost: Optional["LifeCycleCostResult"] = None,
        baseline_carbon: Optional[LifeCycleCarbonResult] = None,
    ) -> LifeCycleCostResult:
        gia = self.archetype.gia

        # Upfront Capital
        initial_construction_capex = scenario.upfront_capex_per_m2 * gia
        demolition_capex = scenario.demolition_cost_per_m2 * gia
        total_upfront = initial_construction_capex + demolition_capex

        # Initial MEP allocation (approx 35% of construction capex)
        initial_mep_capex = initial_construction_capex * 0.35

        # 60-Year Discounted Annual Cashflows
        disc_maint = 0.0
        disc_energy = 0.0
        disc_replacement = 0.0
        disc_social_carbon = 0.0

        annual_elec_kwh = (
            max(0.0, scenario.elec_gross_kwh_per_m2_yr - scenario.pv_generation_kwh_per_m2_yr) * gia
        )
        annual_gas_kwh = scenario.gas_kwh_per_m2_yr * gia

        annual_undiscounted_cashflows: List[float] = []

        for t_idx, df in enumerate(self.discount_factors):
            study_year = t_idx + 1
            calendar_year = self.archetype.base_year + t_idx

            # Escalated tariffs
            elec_price = self.econ.electricity_tariff_base * (
                (1.0 + self.econ.energy_real_escalation_rate) ** t_idx
            )
            gas_price = self.econ.gas_tariff_base * (
                (1.0 + self.econ.energy_real_escalation_rate) ** t_idx
            )

            # Energy bill for year t
            yr_energy = (annual_elec_kwh * elec_price) + (annual_gas_kwh * gas_price)
            disc_energy += yr_energy * df

            # Maintenance for year t
            yr_maint = scenario.annual_maintenance_per_m2 * gia
            disc_maint += yr_maint * df

            # Periodic MEP replacements at years 15, 30, 45
            yr_rep = 0.0
            if study_year in [15, 30, 45]:
                yr_rep = initial_mep_capex * scenario.mep_replacement_pct
                disc_replacement += yr_rep * df

            # Societal Carbon Cost in year t (DESNZ Shadow Price)
            # operational carbon in tonnes * shadow price [£/t]
            yr_oper_carbon_tonnes = (
                carbon_result.b6_annual_timeseries["desnz_central"][t_idx] / 1000.0
            )
            shadow_price = self.grid.get_shadow_carbon_price(calendar_year)
            disc_social_carbon += (yr_oper_carbon_tonnes * shadow_price) * df

            annual_undiscounted_cashflows.append(yr_energy + yr_maint + yr_rep)

        financial_npv = total_upfront + disc_maint + disc_energy + disc_replacement
        societal_npv = financial_npv + disc_social_carbon

        # Marginal Abatement Cost (MAC) relative to Baseline
        mac = 0.0
        if baseline_cost is not None and baseline_carbon is not None:
            cost_diff = financial_npv - baseline_cost.financial_npv
            carbon_diff_tonnes = (
                baseline_carbon.total_wlc_by_trajectory["desnz_central"]
                - carbon_result.total_wlc_by_trajectory["desnz_central"]
            ) / 1000.0

            if abs(carbon_diff_tonnes) > 1e-3:
                mac = cost_diff / carbon_diff_tonnes

        return LifeCycleCostResult(
            scenario_id=scenario.scenario_id,
            name=scenario.name,
            gia=gia,
            initial_capex=initial_construction_capex,
            demolition_capex=demolition_capex,
            total_upfront_capex=total_upfront,
            discounted_maintenance_opex=disc_maint,
            discounted_energy_bills=disc_energy,
            discounted_replacement_capex=disc_replacement,
            financial_npv=financial_npv,
            discounted_societal_carbon_cost=disc_social_carbon,
            societal_npv=societal_npv,
            marginal_abatement_cost_gbp_per_tonne=mac,
            annual_cashflows=annual_undiscounted_cashflows,
            annual_discount_factors=self.discount_factors,
        )

    def calculate_all(
        self, carbon_results: Dict[str, LifeCycleCarbonResult]
    ) -> Dict[str, LifeCycleCostResult]:
        results: Dict[str, LifeCycleCostResult] = {}
        # First compute baseline
        baseline_sc = SCENARIO_CONFIGS["scenario_1"]
        baseline_carbon = carbon_results["scenario_1"]
        base_cost = self.calculate_scenario(baseline_sc, baseline_carbon)
        results["scenario_1"] = base_cost

        # Then compute remaining scenarios with MAC against baseline
        for sc_id, sc_cfg in SCENARIO_CONFIGS.items():
            if sc_id == "scenario_1":
                continue
            results[sc_id] = self.calculate_scenario(
                sc_cfg, carbon_results[sc_id], baseline_cost=base_cost, baseline_carbon=baseline_carbon
            )

        return results

