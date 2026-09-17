from dataclasses import dataclass
from typing import Dict, Tuple
from src.config import ScenarioConfig, SCENARIO_CONFIGS
from src.carbon_calculator import LifeCycleCarbonResult


@dataclass
class BenchmarkComplianceResult:
    scenario_id: str
    upfront_kg_per_m2: float
    net_eui_kwh_per_m2: float
    leti_embodied_band: str
    leti_operational_pass: bool
    riba_2025_pass: bool
    riba_2030_pass: bool
    nzcbs_upfront_pass: bool
    nzcbs_operational_pass: bool


class SustainabilityBenchmarkScorer:
    """LETI Climate Emergency Design Guide, RIBA 2030, and UK NZCBS scoring engine."""

    # LETI Upfront Embodied Carbon Bands for Commercial Offices (kg CO2e/m2 GIA)
    LETI_BANDS: list[Tuple[float, str]] = [
        (150.0, "A++"),
        (225.0, "A+"),
        (300.0, "A"),
        (450.0, "B"),
        (600.0, "C"),
        (750.0, "D"),
        (900.0, "E"),
        (1050.0, "F"),
    ]

    LETI_OFFICE_EUI_LIMIT: float = 55.0  # kWh/m2/yr
    RIBA_2030_UPFRONT_LIMIT: float = 500.0  # kg CO2e/m2 GIA
    RIBA_2030_EUI_LIMIT: float = 55.0  # kWh/m2/yr
    RIBA_2025_UPFRONT_LIMIT: float = 750.0  # kg CO2e/m2 GIA
    RIBA_2025_EUI_LIMIT: float = 70.0  # kWh/m2/yr

    NZCBS_NEW_BUILD_UPFRONT_LIMIT: float = 420.0  # kg CO2e/m2
    NZCBS_RETROFIT_UPFRONT_LIMIT: float = 240.0  # kg CO2e/m2
    NZCBS_EUI_LIMIT: float = 55.0  # kWh/m2/yr

    def score_scenario(
        self, scenario: ScenarioConfig, carbon_res: LifeCycleCarbonResult
    ) -> BenchmarkComplianceResult:
        upfront_m2 = carbon_res.upfront_per_m2()
        net_eui = scenario.net_operational_eui

        # Determine LETI Band
        band = "G"
        for threshold, letter in self.LETI_BANDS:
            if upfront_m2 < threshold:
                band = letter
                break

        leti_oper = net_eui <= self.LETI_OFFICE_EUI_LIMIT
        riba_2025 = (upfront_m2 <= self.RIBA_2025_UPFRONT_LIMIT) and (net_eui <= self.RIBA_2025_EUI_LIMIT)
        riba_2030 = (upfront_m2 <= self.RIBA_2030_UPFRONT_LIMIT) and (net_eui <= self.RIBA_2030_EUI_LIMIT)

        # NZCBS upfront limit differs for retrofit vs new build
        is_retrofit = scenario.structure_retained_pct >= 1.0
        nzcbs_upfront_limit = (
            self.NZCBS_RETROFIT_UPFRONT_LIMIT if is_retrofit else self.NZCBS_NEW_BUILD_UPFRONT_LIMIT
        )
        nzcbs_upfront = upfront_m2 <= nzcbs_upfront_limit
        nzcbs_oper = net_eui <= self.NZCBS_EUI_LIMIT

        return BenchmarkComplianceResult(
            scenario_id=scenario.scenario_id,
            upfront_kg_per_m2=upfront_m2,
            net_eui_kwh_per_m2=net_eui,
            leti_embodied_band=band,
            leti_operational_pass=leti_oper,
            riba_2025_pass=riba_2025,
            riba_2030_pass=riba_2030,
            nzcbs_upfront_pass=nzcbs_upfront,
            nzcbs_operational_pass=nzcbs_oper,
        )

    def score_all(
        self, carbon_results: Dict[str, LifeCycleCarbonResult]
    ) -> Dict[str, BenchmarkComplianceResult]:
        scores: Dict[str, BenchmarkComplianceResult] = {}
        for sc_id, sc_cfg in SCENARIO_CONFIGS.items():
            scores[sc_id] = self.score_scenario(sc_cfg, carbon_results[sc_id])
        return scores
