"""BP19b/d: itemisation of the SAC-calibrated structure residual (GBP/m2, costing.py) into systems, each tagged fixed per
site or per m2, and the resulting fixed share used by the workbook Scale sheet. Items marked 'placeholder' are NOT sourced:
they split the calibrated total, they do not change it. Quotes (RFQ_SPEC.md 3.7) replace them line by line.
Perimeter share (BP19d) is geometric: wall glazing and glazing bars over the priced structure."""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
XLSX_IN = HERE / "results" / "bplan" / "xlsx_inputs.json"
AREA_HA = 1.0


class ResidualItems:
    def __init__(self, resid_gbp_m2, area_m2=AREA_HA * 1e4):
        self.total, self.area = resid_gbp_m2, area_m2
        with open(HERE / "data" / "residual_items.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        fixed_m2 = sum(float(r["fixed_gbp_site"]) for r in rows) / area_m2
        named = sum(float(r["gbp_m2_central"]) for r in rows if r["gbp_m2_central"] != "REMAINDER")
        # BP27: when the residual per m2 falls below the named lines (fixed share at large area, or the WUR 4-8 ha anchor)
        # the named lines shrink pro rata and the remainder is zero, so the lines always reconcile with the capex
        k = min(1.0, resid_gbp_m2 / named) if named > 0 else 1.0
        self.rows = []
        for r in rows:
            c = max(resid_gbp_m2 - named, 0.0) if r["gbp_m2_central"] == "REMAINDER" else float(r["gbp_m2_central"]) * k
            self.rows.append({**r, "gbp_m2_central": c, "fixed_gbp_site": float(r["fixed_gbp_site"])})
        assert abs(sum(r["gbp_m2_central"] for r in self.rows) - resid_gbp_m2) < 1e-6
        self.fixed_share = fixed_m2 / resid_gbp_m2
        self.placeholder_share = sum(r["gbp_m2_central"] for r in self.rows if r["tier"] == "placeholder") / resid_gbp_m2

    def table(self):
        out = ["| Item | £/m² | Fixed per site (£) | Tier | Life (yr) |", "|---|---:|---:|---|---:|"]
        for r in self.rows:
            out.append(f"| {r['label']} | {r['gbp_m2_central']:.1f} | {r['fixed_gbp_site']:,.0f} | {r['tier']} | {r['life_yr']} |")
        out.append(f"| **Total** | **{self.total:.1f}** | **{sum(r['fixed_gbp_site'] for r in self.rows):,.0f}** | | |")
        return "\n".join(out)


class PerimeterShare:
    """Share of the priced (bottom-up) structure cost that scales with perimeter: wall glazing + its bars. Roof glazing,
    frame, pipe and screen scale with area. Gutter height x perimeter = wall area (gable triangles ignored)."""

    def __init__(self, inputs):
        s = inputs["scen"][0]
        cap = inputs["cashflow_S0"]["capex"]
        self.wall_frac = s["perimeter"] * inputs["x"]["gutter_h"] / s["glazed_m2"]
        priced = {k: v for k, v in cap.items() if k in ("steel", "aluminium", "glass_dbl_ar_m2", "concrete", "pir_panel_m2", "heating_pipe_m", "energy_screen_m2")}
        self.share = self.wall_frac * (priced["aluminium"] + priced["glass_dbl_ar_m2"]) / sum(priced.values())


if __name__ == "__main__":
    d = json.loads(XLSX_IN.read_text())
    R = ResidualItems(d["resid_gbp_m2"])
    P = PerimeterShare(d)
    print(R.table())
    print(f"fixed share of residual {R.fixed_share:.1%}; placeholder share {R.placeholder_share:.0%}; wall glazing fraction {P.wall_frac:.1%}; perimeter share of priced structure {P.share:.1%}")
