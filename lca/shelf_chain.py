"""BP15: soil-to-shelf boundary. Functional unit: 1 kg of cucumber on a Central Belt supermarket shelf.

Two chains (UK glasshouse, import from Spain/Netherlands/Morocco) share the downstream stages. Every stage carries a value,
tier and source; PLACEHOLDER tiers are labelled and must be replaced by quotes. Run: python shelf_chain.py
"""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class Stage:
    name: str
    gbp_kg: float
    tier: str
    source: str


class ImportChain:
    SHARE_ORIGINS = ("Spain", "Netherlands", "Morocco")
    MFN_DUTY, EU_MA_DUTY = 0.12, 0.0

    def cif(self):
        d = pd.read_csv(DATA / "imports_monthly.csv")
        c = d[(d.crop == "cucumber") & d.origin.isin(self.SHARE_ORIGINS)]
        return float((c.gbp_per_kg_cif * c.tonnes).sum() / c.tonnes.sum())

    def stages(self):
        cif = self.cif()
        return [
            Stage("CIF at the UK border (Spain/NL/Morocco weighted, 2023-25)", cif, "sourced", "UN Comtrade via data/imports_monthly.csv"),
            Stage("UK import duty (EU and Morocco origin 0 %; MFN 12 % would apply to others)", cif * self.EU_MA_DUTY, "sourced",
                  "UK Trade Tariff commodity 0707000520: third-country 12.00 %, preference EU 0.00 %, Morocco 0.00 %"),
            Stage("Border SPS checks / certificate (BTOM low-risk plant products: none)", 0.0, "sourced (secondary)",
                  "GOV.UK Border Target Operating Model Aug 2023, Fig. 4 low-risk 0 % checks; cucumber risk category to confirm"),
            Stage("Port handling, customs agent, haul to Central Belt RDC (balance to the plan's GBP 1.57 parity)", 1.57 - cif, "derived",
                  "BUSINESS_PLAN.md import parity GBP 1.57 less weighted CIF; not itemised. PLACEHOLDER split: needs forwarder quote"),
            Stage("Importer / packer margin", 0.0, "PLACEHOLDER", "none found; included in the haul balance above if at all"),
            Stage("Transit loss 3 % of upstream cost", 0.03 * cif / 0.97, "sourced (proxy)", "Blaauw et al. 2024 (avocado), data/chain_stages.csv"),
        ]


class UkChain:
    def __init__(self, ex_farm=1.17, packing=0.100, haul=0.046, commission=0.14):
        self.p, self.pk, self.h, self.c = ex_farm, packing, haul, commission

    def stages(self):
        return [
            Stage("Ex-farm price (DEFRA wholesale, harvest-weighted)", self.p, "sourced", "data/defra_wholesale_prices.csv"),
            Stage("Packing", self.pk, "model", "cashflow pack_gbp_kg; BP24c bulk crates not applied"),
            Stage("Haulage to RDC (own)", self.h, "model", "BP24c: 4.6 p/kg; zero if retailer collects"),
            Stage("Marketing commission 14 % of sale", self.c * self.p, "sourced (secondary)", "BritFarmers 2026, BP14"),
            Stage("Transit loss", 0.0, "assumption", "short chain, same-day to RDC; no UK figure found"),
        ]


COMMON = [
    Stage("RDC -> store haul and RDC handling", 0.10, "PLACEHOLDER", "no UK figure found; needs retailer or haulier input"),
    Stage("In-store shrink (waste at retail)", 0.0, "see note", "US produce shrink 4-6 % of sales (IFPA 2023); UK cucumber figure not found"),
]


def report():
    imp, uk = ImportChain(), UkChain()
    rows = []
    for chain, stages in (("Import", imp.stages()), ("UK glasshouse", uk.stages())):
        for s in stages:
            rows.append((chain, s.name, round(s.gbp_kg, 3), s.tier, s.source))
    for s in COMMON:
        rows.append(("Both", s.name, s.gbp_kg, s.tier, s.source))
    totals = {"Import at the RDC": sum(s.gbp_kg for s in imp.stages()), "UK at the RDC": sum(s.gbp_kg for s in uk.stages())}
    return rows, totals


if __name__ == "__main__":
    rows, totals = report()
    for r in rows:
        print(" | ".join(map(str, r)))
    print(totals)
