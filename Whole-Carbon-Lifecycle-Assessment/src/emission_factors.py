from pathlib import Path
from typing import Dict, Optional
import pandas as pd


class EmissionFactorDatabase:
    """University of Bath ICE Database v3.0, CIBSE TM65, and IPCC AR6 carbon factors."""

    HGV_FREIGHT_FACTOR_KG_PER_TONNE_KM: float = 0.1069
    DEFAULT_A5_SITE_INSTALLATION_KG_PER_M2: float = 14.0
    DEMOLITION_C1_FULL_KG_PER_M2: float = 12.5
    DEMOLITION_C1_STRIPOUT_KG_PER_M2: float = 3.5
    WASTE_PROCESSING_C3_KG_PER_KG: float = 0.015

    REFRIGERANT_GWPS: Dict[str, float] = {
        "R410A": 2088.0,
        "R32": 675.0,
        "R290": 3.0,
        "R1234ze": 1.0,
        "R134a": 1530.0,
    }

    def __init__(self, data_path: Optional[Path] = None):
        if data_path is None:
            data_path = Path(__file__).resolve().parent.parent / "data" / "ice_database_v3_factors.csv"
        self.data_path = Path(data_path)
        self.df = pd.read_csv(self.data_path).set_index("material_id")

    def get_factor(self, material_id: str) -> pd.Series:
        if material_id not in self.df.index:
            raise KeyError(f"Material ID '{material_id}' not found in ICE v3.0 factor database.")
        return self.df.loc[material_id]

    def get_cradle_to_gate_ecf(self, material_id: str) -> float:
        if material_id == "none":
            return 0.0
        return float(self.get_factor(material_id)["cradle_to_gate_ecf"])

    def get_waste_rate(self, material_id: str) -> float:
        if material_id == "none":
            return 0.0
        return float(self.get_factor(material_id)["waste_rate"])

    def get_biogenic_factor(self, material_id: str) -> float:
        if material_id == "none":
            return 0.0
        return float(self.get_factor(material_id)["biogenic_carbon_factor"])

    def get_service_life(self, material_id: str) -> float:
        if material_id == "none":
            return 60.0
        return float(self.get_factor(material_id)["service_life_years"])

    def get_refrigerant_gwp(self, refrigerant_name: str) -> float:
        clean_name = refrigerant_name.strip().upper()
        if clean_name not in self.REFRIGERANT_GWPS:
            raise KeyError(f"Refrigerant '{refrigerant_name}' not recognized in IPCC AR6 table.")
        return self.REFRIGERANT_GWPS[clean_name]

