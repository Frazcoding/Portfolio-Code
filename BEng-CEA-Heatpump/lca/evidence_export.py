"""Flatten study results into tidy CSV tables for the Evidence dashboard (../dashboard).

Run from lca/: python evidence_export.py
"""
import csv
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

LCA = Path(__file__).resolve().parent
OUT = LCA.parent / "dashboard" / "sources" / "cea"
LEAD = {"ha": 2.9, "ppfd": 150.0, "turbines": 2}


@dataclass
class Table:
    name: str
    rows: list = field(default_factory=list)

    def add(self, **row):
        self.rows.append(row)

    def write(self, folder: Path):
        if not self.rows:
            raise ValueError(f"table {self.name} is empty")
        columns = list(dict.fromkeys(k for row in self.rows for k in row))
        with open(folder / f"{self.name}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows({k: None if isinstance(v, float) and not math.isfinite(v) else v
                              for k, v in row.items()} for row in self.rows)


class LitOpenExport:
    """Lit lead study (BP37a): designs x price cases, with cash flow, capex, cost and finance."""

    def __init__(self, path: Path):
        self.cases = json.loads(path.read_text())

    @staticmethod
    def case_id(design):
        return f"{design['ha']:g}ha_{design['ppfd']:.0f}umol_{design['turbines']}T"

    @staticmethod
    def label(design):
        light = "unlit" if design["ppfd"] == 0 else f"{design['ppfd']:.0f} umol"
        return f"{design['ha']:g} ha, {light}, {design['turbines']} turbine{'s' * (design['turbines'] > 1)}"

    @staticmethod
    def is_lead(design):
        return all(design[k] == v for k, v in LEAD.items())

    def tables(self):
        cases, cashflow, capex, cost, monthly, finance, tranches = (
            Table(n) for n in ("lead_cases", "lead_cashflow", "lead_capex", "lead_cost_per_kg",
                               "lead_monthly", "lead_finance", "lead_tranches"))
        for case in self.cases:
            design = case["design"]
            cid = self.case_id(design)
            for month, (share, parity) in enumerate(zip(case["harvest_share"], case["parity_monthly"]), 1):
                monthly.add(case_id=cid, month=month, harvest_share=share, parity_gbp_kg=parity)
            first = next(iter(case["prices"].values()))
            for component, gbp in first["capex"].items():
                capex.add(case_id=cid, component=component.split("(")[0].strip(), gbp=gbp)
            for item, gbp_kg in first["cost_gbp_kg"].items():
                cost.add(case_id=cid, item=item, gbp_kg=gbp_kg)
            for price_case, p in case["prices"].items():
                cases.add(case_id=cid, label=self.label(design), is_lead=self.is_lead(design),
                          price_case=price_case, ha=design["ha"], ppfd=design["ppfd"],
                          turbines=design["turbines"], glazing=design["glazing"],
                          price_gbp_kg=p["price"], parity_gbp_kg=case["parity_gbp_kg"],
                          capex_gbp=p["capex_total"], kg_yr=p["kg_yr"], yield_kg_m2=case["Y"],
                          opex_gbp=p["opex"], revenue_gbp=p["revenue"], ebitda_gbp=p["ebitda"],
                          lcop_8pct=p["lcop_008"], lcop_3p5pct=p["lcop_0035"], npv_8pct=p["npv_008"],
                          irr=p["irr"], payback_yr=p["payback"], carbon_kg_kg=case["carbon"],
                          winter_share=case["winter_share"], hp_kw_th=case["hp_kW_th"],
                          store_kwh=case["store_kWh"])
                cumulative = 0.0
                for year, cash in enumerate(p["cashflow"]):
                    cumulative += cash
                    cashflow.add(case_id=cid, price_case=price_case, year=year,
                                 cashflow_gbp=cash, cumulative_gbp=cumulative)
                for structure, f in p["finance"].items():
                    finance.add(case_id=cid, price_case=price_case, structure=structure,
                                debt_gbp=f["debt"], equity_gbp=f["equity"],
                                debt_service_yr1_gbp=f["debt_service_yr1"], min_dscr=f["min_dscr"],
                                equity_irr=f["equity_irr"], project_irr=f["project_irr"],
                                equity_payback_yr=f["equity_payback"], min_price_gbp_kg=f.get("min_price"))
                    for t in f["tranches"]:
                        tranches.add(case_id=cid, price_case=price_case, structure=structure,
                                     tranche=t["name"], amount_gbp=t["amount"], rate=t["rate"],
                                     tenor_yr=t["tenor"], payment_gbp=t["payment"])
        return [cases, cashflow, capex, cost, monthly, finance, tranches]


class DesignStudyExport:
    """Year-round design-of-experiments points (BP35/BP35b), wind scaled with area."""

    METRICS = ("Y", "capex", "opex", "kg_yr", "lcop8", "price_cover", "irr_lender", "payback_lender",
               "npv8_lender", "carbon", "winter_share", "heat_kWh_m2", "elec_kWh_m2", "hp_kW_th",
               "store_kWh", "led_kW", "month_min_ratio")

    def __init__(self, results: Path):
        self.files = {(crop, stage): results / f"yearround_wind_{stage}_{crop}.json"
                      for crop in ("cucumber", "tomato") for stage in ("doe", "verify")}

    def tables(self):
        table = Table("design_study")
        for (crop, stage), path in self.files.items():
            if not path.exists():
                continue
            for i, point in enumerate(json.loads(path.read_text())):
                design = {f"d_{k}": v for k, v in point["design"].items() if k != "product"}
                table.add(crop=crop, stage=stage, point=i, **design,
                          **{m.lower(): point.get(m) for m in self.METRICS})
        return [table]


class HandoffExport:
    """Task list in HANDOFF.md: done, open or BLOCKED."""

    ITEM = re.compile(r"^\s*- \[( |x)\] (?:~~)?((?:BP)?\d+[a-z]?)\.\s*(.*)")

    def __init__(self, path: Path):
        self.lines = path.read_text(encoding="utf-8").splitlines()

    def tables(self):
        table = Table("handoff_items")
        for line in self.lines:
            match = self.ITEM.match(line)
            if not match:
                continue
            done, item, text = match.groups()
            state = "done" if done == "x" else "blocked" if "BLOCKED" in text else "open"
            table.add(item=item, parent=re.sub(r"[a-z]$", "", item), state=state,
                      text=text[:220] + ("..." if len(text) > 220 else ""))
        return [table]


class InputsExport:
    """Input register, residual capex items and the price evidence."""

    SOURCED = ("sourced", "standard", "decided", "user decision", "design choice", "calibrated",
               "model calibration anchor", "derived")
    WEAK = ("placeholder", "pending", "unsourced", "to be replaced")

    def __init__(self, data: Path):
        self.data = data

    def read(self, name):
        with open(self.data / name, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def number(text):
        """design_pm is the anchored remainder (REMAINDER), computed in costing, not stored."""
        try:
            return float(text)
        except ValueError:
            return None

    def quality(self, status):
        status = (status or "").strip().lower()
        if status.startswith(self.WEAK):
            return "placeholder"
        if status.startswith(self.SOURCED):
            return "sourced"
        return "estimate"

    def tables(self):
        register, residual, defra, imports = (
            Table(n) for n in ("input_register", "residual_items", "uk_wholesale", "import_cif"))
        for row in self.read("input_register.csv"):
            register.add(group=row["group"], input=row["input"], value=row["value"], unit=row["unit"],
                         status=row["status"], quality=self.quality(row["status"]),
                         source=(row["source"] or "")[:200])
        for row in self.read("residual_items.csv"):
            residual.add(key=row["key"], label=row["label"].split("(")[0].strip()[:80],
                         gbp_m2=self.number(row["gbp_m2_central"]), fixed_gbp=self.number(row["fixed_gbp_site"]),
                         life_yr=row["life_yr"], tier=row["tier"], rfq_to=row["rfq_to"])
        for row in self.read("defra_wholesale_prices.csv"):
            if row["item"] in ("cucumbers", "tomatoes"):
                defra.add(crop=row["item"].rstrip("s").replace("tomatoe", "tomato"), variety=row["variety"],
                          date=row["date"], gbp_kg=float(row["price"]))
        for row in self.read("imports_monthly.csv"):
            if row["iso3"] == "W00":
                imports.add(crop=row["crop"], date=f"{row['year']}-{int(row['month']):02d}-01",
                            tonnes=float(row["tonnes"]), gbp_kg_cif=float(row["gbp_per_kg_cif"]))
        return [register, residual, defra, imports]


class DashboardExport:
    def __init__(self):
        self.sources = [LitOpenExport(LCA / "results" / "bplan" / "lit_open.json"),
                        DesignStudyExport(LCA / "results" / "bplan"),
                        HandoffExport(LCA / "HANDOFF.md"),
                        InputsExport(LCA / "data")]

    def run(self):
        OUT.mkdir(parents=True, exist_ok=True)
        for source in self.sources:
            for table in source.tables():
                table.write(OUT)
                print(f"{table.name:18s} {len(table.rows):6d} rows")


if __name__ == "__main__":
    DashboardExport().run()
