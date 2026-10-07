"""BP36: the BP33 financing model (finance.py) on the lit lead and the three verified year-round designs, levered
phasing to ~10 ha, and a Monte Carlo on the cash-flow layer (no physics rerun).

Verified designs (results/bplan/yearround_wind_verify_cucumber.json) carry totals only, so their capex and opex lines
are apportioned on the lit lead's split (LEDs and packing per kg taken from the design itself); the replacement schedule
and residual value come exactly from their saved cashflow_lender. Their price basis is the lead's import parity
(GBP 1.555/kg) as a proxy: their winter share is higher (36 % vs 26 %), so their own parity is slightly higher and the
proxy is conservative.

Phasing: modules of the lead (2.9 ha) at years 0 and 3 and the 4.4 ha lit design (lit_open design 4) at year 6 =
10.2 ha; each module on the central vendor scheme, no shared-cost saving (each pays its own HV connection: conservative).
Phase gaps PLACEHOLDER (lenders usually want 2-3 years of operating record before the next phase).

Monte Carlo (PLACEHOLDER ranges, triangular low/mode/high unless stated): yield x 0.80/1.00/1.05 (model yield sits
near the 105 kg/m2 ceiling, so the tail is downside); price = parity x 0.80/0.90/0.97; capex x 0.90/1.00/1.30 (class 4
estimate); power x 0.85/1.00/1.40; CO2 uniform GBP 0.03-0.10/kg; labour x 0.95/1.00/1.25; half of labour scales with
kg (site_opt.LABOUR_KG_SHARE). 2,000 draws per design, seed 7.

    python bplan_finance_risk.py   -> results/bplan/finance_risk.json, results/bplan/FINANCE_RISK.md
"""
import json

import numpy as np

import finance as F

OUT = F.OUT
CENTRAL = next(sc for sc in F.SCHEMES if sc.name == F.CENTRAL)


class VerifiedProject:
    @staticmethod
    def build(v, lead, parity):
        lp = lead.capex0
        led = v["led_gbp"]
        rest = {k: c for k, c in lp.items() if k != "led_lighting"}
        scale = (v["capex"] - led) / sum(rest.values())
        capex = {k: c * scale for k, c in rest.items()} | {"led_lighting": led}
        pack = lead.per_kg * v["kg_yr"]
        other = {k: c for k, c in lead.costs.items() if k not in F.PER_KG_KEYS}
        oscale = (v["opex"] - pack) / sum(other.values())
        costs = {k: c * oscale for k, c in other.items()} | {"packing": pack, "haulage_to_rdc": 0.0}
        entry = dict(price=v["price_lender"], capex=capex, costs=costs, kg_yr=v["kg_yr"], ramp=lead.ramp,
                     revenue=v["price_lender"] * v["kg_yr"], cashflow=v["cashflow_lender"])
        return F.Project(entry, parity)


class Designs:
    def __init__(self):
        self.lead, self.lead_case = F.Project.from_lit_open(2)
        self.big, self.big_case = F.Project.from_lit_open(4)
        ver = json.loads((OUT / "yearround_wind_verify_cucumber.json").read_text())
        self.items = {"lit lead 2.9 ha 150 umol 2T": (self.lead, self.lead_case["design"])}
        for v in ver:
            d = v["design"]
            name = f"verified {d['site']} {d['ha']} ha {d['ppfd']:.0f} umol {d['turbines']}T"
            self.items[name] = (VerifiedProject.build(v, self.lead, self.lead.parity), d)


class Phasing:
    STARTS = (0, 3, 6)

    def __init__(self, designs):
        self.modules = [(designs.lead, 2.9), (designs.lead, 2.9), (designs.big, 4.4)]

    def run(self, undercut=0.10):
        n = max(self.STARTS) + F.YEARS + 1
        eq, rows = np.zeros(n), []
        for start, (p, ha) in zip(self.STARTS, self.modules):
            r = F.Finance(p, CENTRAL).run(p.parity * (1 - undercut))
            eq[start:start + F.YEARS + 1] += np.asarray(r["equity_cf"])
            rows.append(dict(start=start, ha=ha, capex=sum(p.capex0.values()), debt=r["debt"], equity=r["equity"],
                             min_dscr=r["min_dscr"], equity_irr=r["equity_irr"]))
        cum = np.cumsum(eq)
        return dict(modules=rows, total_ha=sum(ha for _, ha in self.modules), peak_external_equity=float(-cum.min()),
                    peak_year=int(cum.argmin()), equity_irr=F.irr(eq), equity_payback=F.cashflow.payback(eq),
                    debt_total=sum(m["debt"] for m in rows), capex_total=sum(m["capex"] for m in rows),
                    first_three_years_eq=eq[:8].tolist())


class MonteCarlo:
    N, SEED = 2000, 7

    def __init__(self, project, scheme=CENTRAL):
        self.p, self.scheme = project, scheme
        rng = np.random.default_rng(self.SEED)
        tri = lambda a, m, b: rng.triangular(a, m, b, self.N)  # noqa: E731
        self.draws = dict(yield_mult=tri(0.80, 1.0, 1.05), price_x=tri(0.80, 0.90, 0.97), capex_mult=tri(0.90, 1.0, 1.30),
                          power_mult=tri(0.85, 1.0, 1.40), co2_gbp_kg=rng.uniform(0.03, 0.10, self.N),
                          labour_mult=tri(0.95, 1.0, 1.25))

    def run(self):
        keys = ("project_irr_real_pretax", "equity_irr", "min_dscr", "equity_payback")
        res = {k: [] for k in keys}
        for i in range(self.N):
            d = {k: float(v[i]) for k, v in self.draws.items()}
            s = F.Stress(**{k: d[k] for k in ("yield_mult", "capex_mult", "power_mult", "co2_gbp_kg", "labour_mult")})
            r = F.Finance(self.p, self.scheme, s).run(self.p.parity * d["price_x"])
            for k in keys:
                res[k].append(np.nan if r[k] is None else r[k])
        a = {k: np.asarray(v, float) for k, v in res.items()}
        self.arrays = a
        q = {k: dict(P10=float(np.nanpercentile(v, 10)), P50=float(np.nanpercentile(v, 50)),
                     P90=float(np.nanpercentile(v, 90))) for k, v in a.items()}
        q["p_dscr_below_1.25"] = float((a["min_dscr"] < F.DSCR_MIN).mean())
        q["p_dscr_below_1.0"] = float((a["min_dscr"] < 1.0).mean())
        q["p_equity_irr_below_12"] = float((np.nan_to_num(a["equity_irr"], nan=-1) < F.EQUITY_HURDLE).mean())
        q["p_no_payback"] = float(np.isnan(a["equity_payback"]).mean())
        return q


class Study:
    def run(self):
        ds = Designs()
        out = dict(designs={}, phasing=Phasing(ds).run())
        for name, (p, d) in ds.items.items():
            f = F.Finance(p, CENTRAL)
            out["designs"][name] = dict(design=d, capex=sum(p.capex0.values()), kg_yr=p.kg, parity=p.parity,
                                        at_parity_10=F.Study.brief(f.run(p.parity * 0.9)),
                                        at_lender_102=F.Study.brief(f.run(1.02)),
                                        min_price=f.min_price(), monte_carlo=MonteCarlo(p).run())
        return out

    @staticmethod
    def markdown(res):
        pct = F.Report.pct
        L = ["# BP36: financing on the verified designs, phasing and Monte Carlo", "",
             f"Central scheme: {F.CENTRAL}. Nominal, post-tax (finance.py). Inputs in the bplan_finance_risk.py docstring.", "",
             "## Designs at parity -10 % (central scheme)", "",
             "| Design | Capex GBP M | kg/yr (t) | Min price GBP/kg | DSCR yr 1 | min DSCR | Project IRR real pre-tax | "
             "Equity IRR nom. | at GBP 1.02: min DSCR |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for n, d in res["designs"].items():
            r, l = d["at_parity_10"], d["at_lender_102"]
            L.append(f"| {n} | {d['capex'] / 1e6:.2f} | {d['kg_yr'] / 1e3:,.0f} | {d['min_price'] and round(d['min_price'], 3)} | "
                     f"{r['dscr_yr1']:.2f} | {r['min_dscr']:.2f} | {pct(r['project_irr_real_pretax'])} | "
                     f"{pct(r['equity_irr'])} | {l['min_dscr']:.2f} |")
        L += ["", "## Monte Carlo (2,000 draws, central scheme)", "",
              "| Design | Project IRR P10 / P50 / P90 | Equity IRR P10 / P50 / P90 | min DSCR P10 / P50 / P90 | "
              "P(min DSCR < 1.25) | P(< 1.0) | P(equity IRR < 12 %) |", "|---|---|---|---|---:|---:|---:|"]
        for n, d in res["designs"].items():
            m = d["monte_carlo"]
            trio = lambda k, f: " / ".join(f(m[k][p]) for p in ("P10", "P50", "P90"))  # noqa: E731
            L.append(f"| {n} | {trio('project_irr_real_pretax', pct)} | {trio('equity_irr', pct)} | "
                     f"{trio('min_dscr', lambda x: f'{x:.2f}')} | {m['p_dscr_below_1.25']:.0%} | {m['p_dscr_below_1.0']:.0%} | "
                     f"{m['p_equity_irr_below_12']:.0%} |")
        ph = res["phasing"]
        L += ["", f"## Phasing to {ph['total_ha']:.1f} ha (parity -10 %, central scheme per module)", "",
              "| Start yr | ha | Capex GBP M | Debt GBP M | Equity GBP M | min DSCR | Equity IRR nom. |",
              "|---:|---:|---:|---:|---:|---:|---:|"]
        for m in ph["modules"]:
            L.append(f"| {m['start']} | {m['ha']} | {m['capex'] / 1e6:.2f} | {m['debt'] / 1e6:.2f} | {m['equity'] / 1e6:.2f} | "
                     f"{m['min_dscr']:.2f} | {pct(m['equity_irr'])} |")
        L += ["", f"Total capex GBP {ph['capex_total'] / 1e6:.1f} M, debt GBP {ph['debt_total'] / 1e6:.1f} M. Peak external "
              f"equity GBP {ph['peak_external_equity'] / 1e6:.2f} M (year {ph['peak_year']}): later phases are part-funded "
              f"from phase-1 cash. Combined equity IRR {pct(ph['equity_irr'])}, payback {ph['equity_payback']:.1f} yr."]
        return "\n".join(L) + "\n"


if __name__ == "__main__":
    res = Study().run()
    (OUT / "finance_risk.json").write_text(json.dumps(res, indent=1, default=float))
    md = Study.markdown(res)
    (OUT / "FINANCE_RISK.md").write_text(md)
    print(md)
