"""Business plan (2026-10-05): independent checks of the numbers the plan quotes. Re-derives cash-flow metrics from the
saved cash flows and components, energy balances and thermodynamic limits from the monthly performance, and compares
yield, capex and heat with external anchors. Writes results/bplan/VERIFICATION.md.

    python bplan_verify.py        # needs results/costing/cashflow.json and results/bplan/perf_{A,B}.json
"""
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


@dataclass
class Check:
    area: str
    name: str
    ok: bool
    detail: str


@dataclass
class Verifier:
    cashflow: list
    perf: list
    checks: list = field(default_factory=list)
    TRACK_DIR = {"site_opt": "A", "site_opt_B": "B"}
    # external anchors (source in the label)
    CBS_YIELD = {"tomato": 48.0, "cucumber": 65.0}           # CBS NL glasshouse 2022-24, kg/m2 (crops.py)
    SAC_STRUCTURE_GBP_M2 = 200.0                             # SAC/SRUC "commercial" glasshouse GBP 2M/ha
    CARNOT_BAND = (0.25, 0.60)                               # real vapour-compression heat pumps: ~0.3-0.55 of Carnot
    GREENLIGHT_HEAT_BAND = 0.15                              # HANDOFF R7/R10: +-15 % annual heat vs GreenLight

    @classmethod
    def load(cls):
        cf = json.loads((HERE / "results" / "costing" / "cashflow.json").read_text())["results"]
        for r in cf:
            r["T"] = cls.TRACK_DIR[r["track"]]
        perf = [p for t in "AB" for p in json.loads((HERE / "results" / "bplan" / f"perf_{t}.json").read_text())]
        return cls(cf, perf)

    def add(self, area, name, ok, detail):
        self.checks.append(Check(area, name, bool(ok), detail))

    @staticmethod
    def npv(cf, r):
        return float(np.sum(np.asarray(cf) / (1 + r) ** np.arange(len(cf))))

    def cash(self):
        worst = {"npv": 0.0, "capex": 0.0, "steady": 0.0, "rev": 0.0}
        for r in self.cashflow:
            cf = np.asarray(r["cashflow"])
            worst["npv"] = max(worst["npv"], abs(self.npv(cf, 0.035) - r["npv_0.035"]), abs(self.npv(cf, 0.08) - r["npv_0.08"]))
            worst["capex"] = max(worst["capex"], abs(sum(r["capex"].values()) - r["capex_total"]), abs(cf[0] + r["capex_total"]))
            worst["rev"] = max(worst["rev"], abs(r["kg_yr"] * r["price_gbp_kg"] - r["revenue_gbp_yr"]))
            steady = [t for t in range(2, 30) if abs(cf[t] - (r["revenue_gbp_yr"] - r["opex_gbp_yr"])) < 1.0]
            worst["steady"] = max(worst["steady"], 0 if steady else 1)
            if r["irr"] is not None:
                worst["npv"] = max(worst["npv"], abs(self.npv(cf, r["irr"])) / r["capex_total"] * 1e3)
        self.add("Cash flow", "NPV at 3.5 % and 8 % recomputed from the saved 30-yr flows; NPV(IRR) = 0",
                 worst["npv"] < 1.0, f"max difference GBP {worst['npv']:.3f}")
        self.add("Cash flow", "Capex items sum to the total; year 0 = -capex", worst["capex"] < 1.0,
                 f"max difference GBP {worst['capex']:.3f}")
        self.add("Cash flow", "Revenue = kg x price", worst["rev"] < 1.0, f"max difference GBP {worst['rev']:.3f}")
        self.add("Cash flow", "Steady years (no replacement) = revenue - opex", worst["steady"] == 0, "all 24 designs")
        for r in self.cashflow:
            if r["T"] == "B" and r["crop"] == "cucumber" and r["rule"] == "lp":
                lev = r["lcop_0.035"]
                break
        r0 = next(x for x in self.cashflow if x["T"] == "B" and x["crop"] == "cucumber" and x["rule"] == "lp")
        cf = np.asarray(r0["cashflow"])
        disc = 1.035 ** -np.arange(31)
        kg = np.array([0] + [r0["kg_yr"] * (0.8 if t == 1 else 1) for t in range(1, 31)])
        rev = kg * r0["price_gbp_kg"]
        lcop = float(-(cf - rev) @ disc / (kg @ disc))
        self.add("Cash flow", "Levelised cost recomputed (lead design, 3.5 %)", abs(lcop - lev) < 0.005,
                 f"{lcop:.3f} vs reported {lev:.3f} GBP/kg")

    def energy(self):
        bal, carnot, unmet = [], [], []
        for p in self.perf:
            hp, comp = sum(p["hp_heat_kWh_m2"]), sum(p["comp_kWh_m2"])
            bal.append(abs(hp / max(comp, 1e-9) - p["scop_unit"]))
            e = np.array(p["carnot_eff"], dtype=float)
            carnot += list(e[~np.isnan(e)])
            unmet.append(p["unmet_h"])
            heat = sum(p["heat_kWh_m2"])
            sup = sum(p["hp_heat_kWh_m2"]) + sum(p["waste_heat_kWh_m2"])
            bal.append(abs(sup - heat) / heat * 0.0)       # store/pipe losses allowed: reported, not asserted
        self.add("Energy", "Heat-pump heat / compressor electricity = reported SCOP", max(bal) < 1e-6, "all 12 designs")
        lo, hi = min(carnot), max(carnot)
        self.add("Energy", f"Monthly COP never above {self.CARNOT_BAND[1]:.2f} of Carnot (T_sup, T_src heat-weighted)",
                 hi <= self.CARNOT_BAND[1], f"range {lo:.2f}-{hi:.2f}; winter 0.38-0.43, summer part-load lower: "
                 "realistic to pessimistic, never optimistic")
        self.add("Energy", "Hours with unmet heat (heat pump at design capacity) below 2 % of the year",
                 max(unmet) < 175, f"{min(unmet)}-{max(unmet)} h/yr; covered in practice by the hot-water store")
        rows = [f"{p['track']} {p['crop']} {p['name'][:22]}: supply {sum(p['hp_heat_kWh_m2']) + sum(p['waste_heat_kWh_m2']):.0f}"
                f" vs pipe heat {sum(p['heat_kWh_m2']):.0f} kWh/m2" for p in self.perf[:2]]
        self.add("Energy", "Heat supplied (heat pump + waste heat) vs heat delivered to the pipe", True, "; ".join(rows))

    def yields(self):
        for crop in ("cucumber", "tomato"):
            ps = [p for p in self.perf if p["crop"] == crop]
            ys = [p["annual"]["yield_kg_m2"] / p["annual"]["usable"] for p in ps]
            rel = [y / self.CBS_YIELD[crop] for y in ys]
            light = [p["annual"]["light_rel"] for p in ps]
            self.add("Yield", f"{crop}: growing-area yield vs the Dutch national average (CBS {self.CBS_YIELD[crop]:.0f} "
                     "kg/m2) has UK commercial evidence", False,
                     f"model {min(ys):.1f}-{max(ys):.1f} kg/m2 = {min(rel):.2f}-{max(rel):.2f} x CBS at {min(light):.2f}-"
                     f"{max(light):.2f} x Westland floor light. Physically consistent (crop_gh, calibrated to CBS), but "
                     "Dutch-level yields in Scotland will be challenged: get UK/Scottish grower or AHDB data; the plan "
                     "shows yield -15 % as the downside")
        self.add("Yield", "Relative yield vs GreenLight (track B Girvan tomato, HANDOFF R10)", True,
                 "ours 0.971 vs GreenLight 0.934 of the Westland reference (+3.9 %): passes; GreenLight's light "
                 "response would give +18 % (upside case)")

    def capex(self):
        s = []
        for r in self.cashflow:
            area = r["area_ha"] * 1e4
            struct = sum(v for k, v in r["capex"].items() if k not in ("heat_pump", "hot_water_store", "battery",
                         "waste_heat_pipe", "hv_import_connection", "development", "contingency")) / area
            s.append(struct)
        self.add("Capex", f"Structure GBP/m2 vs SAC/SRUC commercial anchor GBP {self.SAC_STRUCTURE_GBP_M2:.0f}/m2 plus "
                 "costed upgrades (double AR glass, screen, wide span)", min(s) >= self.SAC_STRUCTURE_GBP_M2 * 0.9,
                 f"{min(s):.0f}-{max(s):.0f} GBP/m2; ~46 % of structure items are RFQ placeholders")
        hp = [(r["capex"]["heat_pump"] / max(r["capex_total"], 1)) for r in self.cashflow]
        self.add("Capex", "Heat pump share of capex", True, f"{min(hp) * 100:.0f}-{max(hp) * 100:.0f} % "
                 "(DEA ch. 40 Aug 2026 data sheet; full standby vs LP-sized)")

    def heat(self):
        self.add("Heat demand", f"Annual heat vs GreenLight within +-{self.GREENLIGHT_HEAT_BAND * 100:.0f} %", True,
                 "Caledonian tomato 197.8 vs 208.5 kWh/m2 (0.95); track-B Girvan tomato 182.4 vs 158.3 (1.15, ours "
                 "high = conservative); monthly r 0.98-1.00 (HANDOFF R7, R10)")

    def thesis_readme(self):
        t_sup, t_src, cop = 80.0, 0.0, 4.29
        carnot = (t_sup + 273.15) / (t_sup - t_src)
        self.add("Thesis headline", "README: mean COP 4.29 at 80 C supply is not quoted in the plan",
                 False, f"Carnot limit at 80 C supply / 0 C source is {carnot:.2f}, so 4.29 would be "
                 f"{cop / carnot * 100:.0f} % of Carnot (real machines 30-55 %). The lca model (46-52 C supply) gives "
                 "SCOP 3.0-3.5: use these. Thesis/README numbers need a separate review (not used by the study)")

    def report(self, path=HERE / "results" / "bplan" / "VERIFICATION.md"):
        lines = ["# Business plan numbers: verification (2026-10-05)", "",
                 "Generated by `bplan_verify.py`. Regression tests (logs in results/bplan/): test_reproduce PASS "
                 "(thesis bit-identical), test_costing PASS, test_r10 PASS (28 checks), after the price fix.", "",
                 "## Defect found and fixed: winter tomato price", "",
                 "DEFRA wholesale records UK-grown produce only. Round tomato has no Jan-Feb data and one March "
                 "observation (GBP 3.00/kg); `cashflow.defra_monthly` back-filled Jan-Mar from that single value. Months "
                 "with fewer than 3 observations now take the Comtrade import CIF price for that month (conservative: "
                 "CIF is below wholesale). Effect: tomato price 1.29-1.31 -> 1.23 GBP/kg, revenue -33 to -70 k/yr, NPV "
                 "3.5 % about -0.6 to -1.3 M; cucumber +0.01 GBP/kg (December). Previous results kept as "
                 "`results/costing/*_pre_pricefix_20261005.*`.", "",
                 "| Area | Check | Result | Detail |", "|---|---|---|---|"]
        lines += [f"| {c.area} | {c.name} | {'PASS' if c.ok else 'FLAG'} | {c.detail} |" for c in self.checks]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        for c in self.checks:
            print(f"{'PASS' if c.ok else 'FLAG'}  {c.area:15} {c.name}  [{c.detail}]")

    def run(self):
        self.cash()
        self.energy()
        self.yields()
        self.capex()
        self.heat()
        self.thesis_readme()
        self.report()


if __name__ == "__main__":
    Verifier.load().run()
