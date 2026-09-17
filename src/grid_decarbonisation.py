from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd


class GridDecarbonisationModel:
    """Dynamic UK electrical grid and natural gas carbon factor model (2026-2086)."""

    TRAJECTORY_MAP: Dict[str, str] = {
        "desnz_central": "desnz_central_kg_co2e_per_kwh",
        "fes_leading_way": "fes_leading_way_kg_co2e_per_kwh",
        "sap10_static": "sap10_static_kg_co2e_per_kwh",
    }

    def __init__(self, data_path: Optional[Path] = None):
        if data_path is None:
            data_path = Path(__file__).resolve().parent.parent / "data" / "grid_emission_trajectories_2026_2086.csv"
        self.data_path = Path(data_path)
        self.df = pd.read_csv(self.data_path).set_index("year")

    @property
    def trajectories(self) -> List[str]:
        return list(self.TRAJECTORY_MAP.keys())

    @property
    def years(self) -> List[int]:
        return list(self.df.index)

    def get_electricity_factor(self, year: int, trajectory: str = "desnz_central") -> float:
        if trajectory not in self.TRAJECTORY_MAP:
            raise KeyError(f"Unknown grid trajectory '{trajectory}'. Choose from: {self.trajectories}")
        col = self.TRAJECTORY_MAP[trajectory]
        if year not in self.df.index:
            raise IndexError(f"Year {year} outside model horizon (2026-2086).")
        return float(self.df.loc[year, col])

    def get_gas_factor(self, year: int) -> float:
        if year not in self.df.index:
            raise IndexError(f"Year {year} outside model horizon (2026-2086).")
        return float(self.df.loc[year, "natural_gas_kg_co2e_per_kwh"])

    def get_shadow_carbon_price(self, year: int) -> float:
        if year not in self.df.index:
            raise IndexError(f"Year {year} outside model horizon (2026-2086).")
        return float(self.df.loc[year, "shadow_carbon_price_gbp_per_tonne"])

    def get_trajectory_series(self, trajectory: str = "desnz_central") -> pd.Series:
        if trajectory not in self.TRAJECTORY_MAP:
            raise KeyError(f"Unknown grid trajectory '{trajectory}'.")
        return self.df[self.TRAJECTORY_MAP[trajectory]]
