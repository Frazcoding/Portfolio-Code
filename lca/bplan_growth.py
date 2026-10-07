"""Growth model (user, 2026-10-07): when, and by how much, to expand from the 2.9 ha lit lead.

Cash-flow layer only (finance.py on lit_open.json, no physics rerun). Each module is financed on its own with the central
scheme (ECA supplier credit + plant asset finance, 1-yr holiday, DSRA, working capital) and built in one year.

Modules: the 2.9 ha lit lead (lit_open design 2) and the 4.4 ha lit design (design 4), the only two lit sizes run.
'Same site': a later module on the Stranraer site extends the existing HV connection at the SP Energy Networks
incremental rate (Nov 2025 charging statement, Ex. 18: +GBP 75 k per extra 800 kVA unit) instead of buying a new
connection; development and contingency are kept (conservative).

Expansion triggers (a module may start in year s only if all hold):
  * lender record: every operating module has had at least RECORD full-output years with DSCR >= 1.25
    (PLACEHOLDER: lenders usually want 1-3 years of trading before a further phase);
  * self-funding: retained equity cash (cumulative to the end of year s-1, no dividends paid) covers the new module's
    equity cheque, so no outside money after the first phase;
  * market: total area <= MAX_HA (PLACEHOLDER 10.2 ha = ~9.5 kt/yr, ~4.7 % of UK cucumber imports; each step needs its
    own offtake contract).
Policy: in each year, start the largest module the triggers allow. Compared with expanding on the lender trigger alone
using new outside equity, and with no expansion.

Also the yield each phase must prove before a lender will fund the next: the lowest yield (kg/m2) at which the central
scheme keeps DSCR >= 1.25, by contract price.

    python bplan_growth.py      -> results/bplan/growth.json, results/bplan/GROWTH.md
"""
import json
from dataclasses import dataclass

import numpy as np

import cashflow
import finance as F

OUT = F.OUT
CENTRAL = next(sc for sc in F.SCHEMES if sc.name == F.CENTRAL)
HV_UNIT_KVA, HV_UNIT_GBP = 800.0, 75e3


@dataclass(frozen=True)
class Module:
    name: str
    ha: float
    project: F.Project
    Y: float


class Modules:
    def __init__(self):
        lit = json.loads((OUT / "lit_open.json").read_text())
        self.first, self.extra = {}, {}
        for d in (2, 4):
            c = lit[d]
            ha = c["design"]["ha"]
            p = F.Project(c["prices"]["undercut 3%"], c["parity_gbp_kg"])
            self.first[ha] = Module(f"{ha} ha", ha, p, c["Y"])
            q = F.Project(c["prices"]["undercut 3%"], c["parity_gbp_kg"])
            units = np.ceil(c["import_peak_kW"] / 0.95 / HV_UNIT_KVA)
            q.capex0["hv_import_connection"] = units * HV_UNIT_GBP
            self.extra[ha] = Module(f"{ha} ha (same site)", ha, q, c["Y"])


class Growth:
    RECORD, MAX_HA, HORIZON = 1, 10.2, 20

    def __init__(self, modules, price, stress=F.Stress(), self_funded=True):
        self.m, self.price, self.s, self.self_funded = modules, price, stress, self_funded
        self.cache = {}

    def module_run(self, mod):
        if mod.name not in self.cache:
            self.cache[mod.name] = F.Finance(mod.project, CENTRAL, self.s).run(self.price)
        return self.cache[mod.name]

    def run(self):
        n = self.HORIZON + F.YEARS + 2
        eq = np.zeros(n)
        built, area = [], 0.0
        first = self.m.first[2.9]
        r0 = self.module_run(first)
        eq[:F.YEARS + 1] += r0["equity_cf"]
        built.append(dict(year=0, module=first.name, ha=first.ha, equity=r0["equity"], min_dscr=r0["min_dscr"]))
        area = first.ha
        for s in range(1, self.HORIZON + 1):
            record_ok = all(s >= b["year"] + 2 + self.RECORD and b["min_dscr"] >= F.DSCR_MIN - 1e-9 for b in built)
            if not record_ok:
                continue
            cash = float(eq[1:s].sum())
            for ha in (4.4, 2.9):
                mod = self.m.extra[ha]
                r = self.module_run(mod)
                fits = area + ha <= self.MAX_HA + 1e-9
                funded = cash >= r["equity"] or not self.self_funded
                if fits and funded:
                    eq[s:s + F.YEARS + 1] += r["equity_cf"]
                    built.append(dict(year=s, module=mod.name, ha=ha, equity=r["equity"], min_dscr=r["min_dscr"]))
                    area += ha
                    break
        cum = np.cumsum(eq)
        area_by = {y: sum(b["ha"] for b in built if b["year"] < y) for y in (3, 5, 8, 10, 15)}
        return dict(price=self.price, yield_mult=self.s.yield_mult, self_funded=self.self_funded, steps=built,
                    final_ha=area, area_operating_by_year=area_by, outside_equity=float(-cum.min()),
                    equity_irr=F.irr(eq), equity_npv_12=cashflow.npv(eq, F.EQUITY_HURDLE),
                    cash_by_year_10=float(cum[10]))


class YieldGate:
    """Lowest yield (kg/m2) the first phase must show for the central scheme to keep DSCR >= 1.25 at a price."""

    def __init__(self, module):
        self.m = module

    def at(self, price):
        ok = lambda ym: F.Finance(self.m.project, CENTRAL, F.Stress(yield_mult=ym)).run(price)["min_dscr"] >= F.DSCR_MIN  # noqa: E731
        lo, hi = 0.4, 1.3
        if not ok(hi):
            return None
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            lo, hi = (lo, mid) if ok(mid) else (mid, hi)
        return hi * self.m.Y


class Study:
    PRICES = (1.30, 1.40, 1.48)
    YIELDS = {"model 93 kg/m2": 1.0, "lender case 79 kg/m2": 0.85}

    def run(self):
        mods = Modules()
        out = dict(modules={}, scenarios=[], yield_gate={})
        for key, d in (("first", mods.first), ("same site", mods.extra)):
            for ha, m in d.items():
                f = F.Finance(m.project, CENTRAL)
                r = f.run(1.40)
                out["modules"][m.name] = dict(ha=ha, capex=sum(m.project.capex0.values()), kg=m.project.kg,
                                              equity=r["equity"], equity_irr=r["equity_irr"], min_price=f.min_price(),
                                              min_dscr_140=r["min_dscr"])
        for yk, ym in self.YIELDS.items():
            for p in self.PRICES:
                for sf in (True, False):
                    g = Growth(mods, p, F.Stress(yield_mult=ym), sf).run()
                    g["yield_case"] = yk
                    out["scenarios"].append(g)
        gate = YieldGate(mods.first[2.9])
        out["yield_gate"] = {f"{p:.2f}": gate.at(p) for p in (1.24, 1.30, 1.35, 1.40, 1.45, 1.48)}
        return out

    @staticmethod
    def markdown(res):
        pct = F.Report.pct
        L = ["# Growth model: when to expand from 2.9 ha", "", "Inputs and triggers in the bplan_growth.py docstring. "
             "Central financing per module; prices real (today's money).", "", "## Modules at GBP 1.40/kg", "",
             "| Module | Capex GBP M | t/yr | Equity GBP M | Min price GBP/kg | Equity IRR nom. |", "|---|---:|---:|---:|---:|---:|"]
        for n, m in res["modules"].items():
            L.append(f"| {n} | {m['capex'] / 1e6:.2f} | {m['kg'] / 1e3:,.0f} | {m['equity'] / 1e6:.2f} | {m['min_price']:.3f} | "
                     f"{pct(m['equity_irr'])} |")
        L += ["", "## Yield phase 1 must prove before a lender funds the next phase (DSCR >= 1.25)", "",
              "| Contract price GBP/kg | Minimum yield kg/m2 |", "|---:|---:|"]
        for p, y in res["yield_gate"].items():
            L.append(f"| {p} | {'-' if y is None else round(y, 1)} |")
        L += ["", "## Expansion paths", "",
              "| Yield | Price | Funding | Steps (year: module) | ha operating yr 5 / 10 / 15 | Outside equity GBP M | "
              "Equity IRR nom. | Equity NPV 12 % GBP M |", "|---|---:|---|---|---|---:|---:|---:|"]
        for g in res["scenarios"]:
            steps = ", ".join(f"{b['year']}: {b['ha']}" for b in g["steps"])
            a = g["area_operating_by_year"]
            L.append(f"| {g['yield_case']} | {g['price']:.2f} | {'self-funded' if g['self_funded'] else 'new equity'} | {steps} | "
                     f"{a[5]:.1f} / {a[10]:.1f} / {a[15]:.1f} | {g['outside_equity'] / 1e6:.2f} | {pct(g['equity_irr'])} | "
                     f"{g['equity_npv_12'] / 1e6:.1f} |")
        return "\n".join(L) + "\n"


if __name__ == "__main__":
    res = Study().run()
    (OUT / "growth.json").write_text(json.dumps(res, indent=1, default=float))
    md = Study.markdown(res)
    (OUT / "GROWTH.md").write_text(md)
    print(md)
