"""Integrated plan (user goal 2026-10-07): physics result -> staffing -> finance -> funding need -> contract and investor
targets, for every design in results/bplan/viable_lit.json, and the pick: the smallest viable cucumber design.

Per design: finance.Project rebuilt from the saved cash-flow inputs, plus the salaried team, 24/7 alarm rota and packhouse
(staffing.py) as a fixed cost; senior debt sized the way a lender sizes it (LenderSizing: DSCR 1.25 on the lender-case
cash flow at yield -15 %), with finance.py's tax, DSRA and working capital; minimum price = the price at which the central
equity IRR reaches 12 % nominal. The vendor-finance minimum price (finance.py central scheme) is kept for comparison.

Viability test (all must hold), with debt sized on the lender case (LenderSizing): at the target price the central
equity IRR and the Monte Carlo P50 equity IRR (bplan_finance_risk ranges) are >= 12 % nominal and P(min DSCR < 1.0) <= 10 %.

Funding need adds what finance.py leaves at zero: interest during a 12-month build on the average drawn debt (half the
debt at the ECA rate, capitalised into the equity cheque), and pre-close development spend (the 5 % development line is
already in capex). Inputs in finance.py, staffing.py and below (PLACEHOLDER unless stated):
  * construction 12 months, financial close 9 months after the offtake letter of intent;
  * offtake target price = import parity x 0.95 (user: "slightly under" parity); floor = the lowest price at which the
    lender-case cash flow still covers the debt service 1.10 times (dividend lock-up level);
  * equity split: 50 % ordinary, 50 % 12 % preference shares (finance.py option) for the investor case.

    python bplan_plan.py        -> results/bplan/plan.json, results/bplan/PLAN.md
"""
import copy
import json

import numpy as np

import bplan_finance_risk as R
import finance as F
import staffing as S

OUT = F.OUT
CENTRAL = next(sc for sc in F.SCHEMES if sc.name == F.CENTRAL)
PREF = next(sc for sc in F.SCHEMES if sc.pref_frac)
UNDERCUT, LENDER_YIELD = 0.05, 0.85
BUILD_MONTHS = 12


SENIOR = F.Tranche("senior debt sized on the lender case", (), 1.0, 0.065, 15, grace=1, profile="sculpt",
                   gearing_cap=0.70, upfront_fee=0.015, capitalise_grace=True)


class LenderSizing:
    """Debt sized the way a lender sizes it: sculpted to DSCR 1.25 on the lender-case (yield -15 %) cash flow, capped at
    70 % gearing; equity then takes the central case. Rate 6.5 % = between the GBP CIRR 5.81 % and bank 6.75-7.0 %
    (PLACEHOLDER blend of ECA-covered and commercial tranches), 1-yr holiday with the year-1 interest capitalised
    (rolled into the loan), 1.5 % fees."""

    def __init__(self, project):
        self.p = project

    def scheme(self, price):
        r = F.Finance(self.p, F.Scheme("sizing", (SENIOR,)), F.Stress(yield_mult=LENDER_YIELD)).run(price)
        g, n = SENIOR.grace, SENIOR.tenor
        tr = F.replace(SENIOR, profile="given", fixed_amount=r["debt"], schedule=tuple(r["service"][g + 1:n + 1]))
        return F.Scheme("senior debt sized on the lender case", (tr,))

    def run(self, price, stress=F.Stress()):
        return F.Finance(self.p, self.scheme(price), stress).run(price)

    def min_price(self):
        lo, hi = 0.5, 4.0
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            lo, hi = (lo, mid) if (self.run(mid)["equity_irr"] or -1) >= F.EQUITY_HURDLE else (mid, hi)
        return hi


class Design:
    def __init__(self, row):
        self.row, self.d, self.crop = row, row["design"], row["crop"]
        self.ha = self.d["ha"]
        e = row["entry"]
        self.base = F.Project(e, row["parity_gbp_kg"])
        self.staff = S.Staffing(self.ha, e["kg_yr"], e["costs"]["labour"], row["harvest_share"]).summary()
        self.project = copy.deepcopy(self.base)
        self.project.costs["staff_salaried_packhouse_oncall"] = self.staff["added_cost"]
        self.price = row["parity_gbp_kg"] * (1 - UNDERCUT)
        self.ppa_mwh = self.d.get("ppa", 0.090) * 1e3

    def finance(self):
        ls = LenderSizing(self.project)
        scheme = ls.scheme(self.price)
        r = F.Finance(self.project, scheme).run(self.price)
        rl = F.Finance(self.project, scheme, F.Stress(yield_mult=LENDER_YIELD)).run(self.price)
        mc = R.MonteCarlo(self.project, scheme)
        mc.draws["price_x"] = mc.draws["price_x"] * self.price / (self.project.parity * 0.90)
        m = mc.run()
        idc = 0.5 * r["debt"] * SENIOR.rate * BUILD_MONTHS / 12
        vendor = F.Finance(self.project, CENTRAL)
        floor = self.floor(scheme)
        return dict(central=r, lender_case=F.Study.brief(rl), min_price=ls.min_price(),
                    min_price_vendor_dscr=vendor.min_price(lender_only=True),
                    min_price_vendor_dscr_no_staff=F.Finance(self.base, CENTRAL).min_price(lender_only=True),
                    monte_carlo=m, idc=idc, equity_need=r["equity"] + idc, floor_price=floor,
                    viable=bool(m["p_dscr_below_1.0"] <= 0.10 and m["equity_irr"]["P50"] >= F.EQUITY_HURDLE
                                and (r["equity_irr"] or -1) >= F.EQUITY_HURDLE))

    def floor(self, scheme, lockup=1.10):
        """Lowest price at which the lender-case cash flow still covers the (fixed) debt service 1.10 times."""
        lo, hi = 0.3, 4.0
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            ok = F.Finance(self.project, scheme, F.Stress(yield_mult=LENDER_YIELD)).run(mid)["min_dscr"] >= lockup
            lo, hi = (lo, mid) if ok else (mid, hi)
        return hi

    def targets(self, fin):
        e, s = self.row["entry"], self.row["summary"]
        kg = e["kg_yr"]
        share = np.asarray(self.row["harvest_share"])
        r = fin["central"]
        capex = sum(self.project.capex0.values())
        pref = F.Finance(self.project, F.replace(LenderSizing(self.project).scheme(self.price), pref_frac=0.5)).run(self.price)
        return dict(
            offtake=dict(volume_t_yr=kg / 1e3, monthly_t=(share * kg / 1e3).tolist(), target_price=self.price,
                         floor_price=fin["floor_price"], parity=self.row["parity_gbp_kg"],
                         indexation="CPI, annual", term_yr="10 + 5 (covers the 15-yr supplier credit)",
                         revenue_yr=kg * self.price, collection="retailer collects at the farm, bulk crates"),
            power=dict(wind_mwh_yr=e["costs"]["electricity_wind_from_turbine"] / self.ppa_mwh, ppa_price_gbp_mwh=self.ppa_mwh,
                       turbines=self.d["turbines"], grid_peak_kw=s["import_peak_kW"], term_yr=15),
            co2=dict(t_yr=e["costs"]["co2_purchased"] / 0.06 / 1e3 if e["costs"]["co2_purchased"] else 0.0,
                     price_gbp_kg=0.06, source="The Creamery by-product, piped or tankered"),
            epc=dict(capex=capex, glasshouse=sum(v for k, v in self.project.capex0.items() if k in F.STRUCT_KEYS),
                     plant=sum(v for k, v in self.project.capex0.items() if k in F.PLANT_KEYS),
                     heat_pump_kw=s["hp_kW_th"], store_mwh=s["store_kWh"] / 1e3, led_kw=s["led_kW"]),
            funding=dict(capex=capex, debt=r["debt"], gearing=r["gearing"],
                         dsra=r["dsra0"], working_capital=r["wc0"], fees=r["fees0"], idc=fin["idc"],
                         equity_total=fin["equity_need"], uses_total=capex + r["dsra0"] + r["wc0"] + r["fees0"] + fin["idc"]),
            investors=dict(equity=fin["equity_need"], ordinary=fin["equity_need"] - pref["pref"], pref=pref["pref"],
                           pref_coupon=0.12, ordinary_irr_p50=fin["monte_carlo"]["equity_irr"]["P50"],
                           ordinary_irr_central_all_ordinary=r["equity_irr"], ordinary_irr_with_pref=pref["equity_irr"],
                           payback_yr=r["equity_payback"], first_tax_yr=r["first_tax_year"],
                           multiple_30yr=float(np.sum(np.clip(r["equity_cf"][1:], 0, None)) / max(r["equity"], 1.0))))

    def result(self):
        fin = self.finance()
        return dict(crop=self.crop, product=self.d["product"], ha=self.ha, design=self.d, physics=self.row["summary"],
                    inputs=self.row.get("inputs"), staffing=self.staff, finance=fin, targets=self.targets(fin),
                    parity=self.row["parity_gbp_kg"], price=self.price)


MIXES = {"cucumber 6 ha + cherry tomato 2 ha": (8.0, (("cucumber", "cucumber", 0.75), ("tomato", "cherry", 0.25))),
         "cucumber 4 ha + vine tomato 2 ha + cherry tomato 2 ha": (8.0, (("cucumber", "cucumber", 0.5), ("tomato", "vine", 0.25),
                                                                         ("tomato", "cherry", 0.25)))}


class Mix:
    """Compartments of one house growing different crops, scaled linearly from the single-crop runs at the same total
    area. With a fixed mix, revenue and every cost line sum exactly, so the house behaves as one product at the
    kg-weighted average price; parity is the kg-weighted parity."""

    @staticmethod
    def row(rows, name, ha, parts):
        pick = [(next(r for r in rows if r["crop"] == c and r["design"]["product"] == pr and r["design"]["ha"] == ha), w)
                for c, pr, w in parts]
        e = {}
        e["capex"] = {k: sum(r["entry"]["capex"].get(k, 0.0) * w for r, w in pick) for k in pick[0][0]["entry"]["capex"]}
        e["costs"] = {k: sum(r["entry"]["costs"].get(k, 0.0) * w for r, w in pick) for k in pick[0][0]["entry"]["costs"]}
        e["kg_yr"] = sum(r["entry"]["kg_yr"] * w for r, w in pick)
        e["revenue"] = sum(r["entry"]["revenue"] * w for r, w in pick)
        e["price"] = e["revenue"] / e["kg_yr"]
        e["cashflow"] = list(np.sum([np.asarray(r["entry"]["cashflow"]) * w for r, w in pick], axis=0))
        e["ramp"] = pick[0][0]["entry"]["ramp"]
        e["capex_total"] = sum(e["capex"].values())
        kgw = [r["entry"]["kg_yr"] * w / e["kg_yr"] for r, w in pick]
        share = np.sum([np.asarray(r["harvest_share"]) * k for (r, _), k in zip(pick, kgw)], axis=0)
        summ = {k: sum(r["summary"][k] * w for r, w in pick) for k in ("capex", "import_peak_kW", "hp_kW_th", "store_kWh", "led_kW")}
        summ.update({k: sum(r["summary"][k] * k_ for (r, _), k_ in zip(pick, kgw)) for k in ("winter_share", "carbon")})
        summ["Y"] = e["kg_yr"] / (ha * 1e4)
        return dict(crop="mix", design={**pick[0][0]["design"], "product": name, "turbines": pick[0][0]["design"]["turbines"]},
                    summary=summ, entry=e, harvest_share=share.tolist(),
                    parity_gbp_kg=sum(r["parity_gbp_kg"] * k for (r, _), k in zip(pick, kgw)), inputs=pick[0][0].get("inputs"))


class Plan:
    def run(self):
        rows = [r for r in json.loads((OUT / "viable_lit.json").read_text())
                if not (r["design"].get("grid") or r["design"].get("hp_source") or r["design"].get("waste"))]
        rows += [Mix.row(rows, n, ha, parts) for n, (ha, parts) in MIXES.items()
                 if all(any(r["crop"] == c and r["design"]["product"] == pr and r["design"]["ha"] == ha for r in rows)
                        for c, pr, _ in parts)]
        res = [Design(r).result() for r in rows]
        base = lambda d: not (d.get("grid") or d.get("hp_source") or d.get("waste"))  # noqa: E731  (energy variants: bplan_energy_options)
        viable = [r for r in res if r["finance"]["viable"] and r["crop"] == "cucumber" and base(r["design"])]
        pick = min(viable, key=lambda r: r["ha"]) if viable else None      # smallest viable: least equity and market risk
        return dict(designs=res, pick=pick and {"crop": pick["crop"], "product": pick["product"], "ha": pick["ha"]})

    @staticmethod
    def markdown(res):
        pct = F.Report.pct
        L = ["# Integrated plan: physics -> staffing -> finance -> targets", "", "Inputs in bplan_plan.py, finance.py, staffing.py.",
             "", "| Crop / product | ha | Y kg/m2 | t/yr | Capex GBP M | FTE | Parity | Target price | Debt GBP M | Equity GBP M | "
             "Min price (equity 12 %) | P(DSCR<1) | Equity IRR central | Equity IRR P50 | Viable |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        for r in res["designs"]:
            f, p = r["finance"], r["physics"]
            L.append(f"| {r['crop']} / {r['product']} | {r['ha']} | {p['Y']:.1f} | {r['targets']['offtake']['volume_t_yr']:,.0f} | "
                     f"{r['targets']['epc']['capex'] / 1e6:.2f} | {r['staffing']['fte_total']:.0f} | {r['parity']:.2f} | {r['price']:.2f} | "
                     f"{f['central']['debt'] / 1e6:.2f} | {f['equity_need'] / 1e6:.2f} | {f['min_price']:.3f} | "
                     f"{f['monte_carlo']['p_dscr_below_1.0']:.0%} | {pct(f['central']['equity_irr'])} | "
                     f"{pct(f['monte_carlo']['equity_irr']['P50'])} | "
                     f"{'yes' if f['viable'] else 'no'} |")
        L += ["", f"Pick: {res['pick']}"]
        return "\n".join(L) + "\n"


if __name__ == "__main__":
    res = Plan().run()
    (OUT / "plan.json").write_text(json.dumps(res, indent=1, default=float))
    md = Plan.markdown(res)
    (OUT / "PLAN.md").write_text(md)
    print(md)
