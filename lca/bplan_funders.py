"""Feasibility levers and funder-specific capital stacks for every saved design (2026-10-13; no physics rerun).

Three questions, answered on the finance.py engine with the bplan_plan.Design rebuild (staffing included):
  1. Price realism. The plan prices every kilo at import parity -5 % (GBP 1.47). UK growers are paid about GBP 1.01/kg for
     cucumbers (DEFRA Horticulture Statistics 2026, Table 18, farm-gate 2023-25) and 76 % of the lit harvest falls in
     April-October, when UK supply competes. PriceCase blends the harvest calendar with the monthly import parity (UN Comtrade
     2023-25 CIF + GBP 0.16/kg haul, as the plan) and UK prices, to give the price a retailer is likely to pay.
  2. Levers. Minimum price (ordinary equity 12 % nominal, debt sized on the lender case) under each lever and packages.
  3. Funder stacks. Each design financed the way a named class of funder would lend: bank club, vendor/ECA, long-tenor
     infrastructure, asset-light (heat ESCo + LED lease). Funding need by source, minimum price, return at the realistic
     price and at the plan target.

Inputs and tiers (PLACEHOLDER unless stated):
  * Farm-gate cucumber GBP 1.013/kg = mean 2023-25 (sourced, DEFRA). Contract uplift on farm-gate for a 10-yr, year-round,
    collected-at-farm programme: +10 % (placeholder; Sainsbury's 10-yr deals of 23 Jul 2026 do not disclose price).
  * Long-tenor infrastructure senior: 20 yr, 6.0 % fixed (15-yr gilt 5.09 % Apr 2026 + ~1 %), 75 % gearing cap, equity
    hurdle 10 % nominal post-tax (infrastructure / pension secured-income funds, e.g. the Greencoat glasshouse precedents).
  * LED operating lease: 6 yr, 8.0 %, 100 % of LED capex (BNP Paribas Leasing Solutions financed LEDs over 61-64 months for a
    Belgian tomato grower; rate placeholder).
  * Heat ESCo terms as finance.py (9 % nominal, 15 yr, buyout year 10).
  * Capital grant GBP 1.5 M: South of Scotland Enterprise awarded Arla Foods GBP 1.5 M (Apr-Jun 2026) for three 2 MW heat
    pumps at Lockerbie, in the same enterprise-agency area as Stranraer (sourced award list; eligibility for a glasshouse
    heat pump unconfirmed). Grants reduce qualifying cost for capital allowances (finance.py).
  * Liquid CO2 GBP 0.25/kg delivered bulk (business_plan/LIQUID_CO2_PRICING_SCOTLAND.md central case) as the downside to the
    by-product assumption: The Creamery's 10.6 kt/yr in SPRI 2023 is combustion CO2, not a captured by-product.

    python bplan_funders.py      -> results/bplan/funders.json, results/bplan/FUNDERS.md
"""
import copy
import json
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

import bplan_plan as P
import finance as F

DATA = Path(__file__).resolve().parent / "data"
OUT = F.OUT
HAUL_GBP_KG = 0.16
FARMGATE_YEARS = (2023, 2024, 2025)
CONTRACT_UPLIFT = 0.10
WINTER = (11, 12, 1, 2, 3)
LIQUID_CO2 = 0.25
SOSE_GRANT = 1.5e6


class MarketPrices:
    def __init__(self):
        im = pd.read_csv(DATA / "imports_monthly.csv")
        im = im[(im.crop == "cucumber") & (im.iso3 == "W00")]
        cif = im.groupby("month").apply(lambda g: float((g.gbp_per_kg_cif * g.tonnes).sum() / g.tonnes.sum()))
        self.parity = (cif + HAUL_GBP_KG).reindex(range(1, 13)).to_numpy()
        w = pd.read_csv(DATA / "defra_wholesale_prices.csv")
        w = w[w.item == "cucumbers"].assign(date=lambda d: pd.to_datetime(d.date))
        w = w[w.date >= "2023-01-01"]
        self.wholesale = w.groupby(w.date.dt.month).price.mean().reindex(range(1, 13)).to_numpy()
        t = pd.read_excel(DATA / "hort-dataset-25-20260625.ods", engine="odf", sheet_name="Table_18_Veg_Price_Value", header=None)
        years = list(t.iloc[5])
        row = t[t.iloc[:, 1] == "Cucumbers"].iloc[0]
        self.farmgate = float(np.mean([row.iloc[years.index(y)] for y in FARMGATE_YEARS])) / 1e3


@dataclass(frozen=True)
class PriceCase:
    name: str
    summer: str
    winter_undercut: float
    summer_uplift: float = 0.0

    def monthly(self, m: MarketPrices):
        summer = {"parity": m.parity * (1 - self.winter_undercut), "wholesale": m.wholesale,
                  "farmgate": np.full(12, m.farmgate * (1 + self.summer_uplift))}[self.summer]
        return np.array([m.parity[i] * (1 - self.winter_undercut) if i + 1 in WINTER else summer[i] for i in range(12)])

    def blended(self, m, share):
        return float(self.monthly(m) @ share)


PRICE_CASES = (
    PriceCase("plan: parity -5 % all year", "parity", 0.05),
    PriceCase("UK-season wholesale, winter parity -5 %", "wholesale", 0.05),
    PriceCase("UK-season farm-gate +10 %, winter parity -5 %", "farmgate", 0.05, CONTRACT_UPLIFT),
    PriceCase("UK-season farm-gate, winter parity -10 %", "farmgate", 0.10),
)
REALISTIC = PRICE_CASES[2].name


@dataclass(frozen=True)
class Stack:
    name: str
    funders: str
    senior_rate: float = 0.065
    senior_tenor: int = 15
    gearing_cap: float = 0.70
    hurdle: float = F.EQUITY_HURDLE
    mode: str = "lender"                 # lender | vendor | asset_light
    led_lease: bool = False


STACKS = (
    Stack("A. Bank club, senior sized on the lender case",
          "UK agri/specialist banks: Shawbrook (+ Tosca Debt Capital), Lloyds/Bank of Scotland, NatWest, HSBC, Barclays, "
          "Santander, Virgin Money, Rabobank London"),
    Stack("B. Vendor finance: ECA supplier credit + plant asset finance",
          "Atradius DSB cover via ING / Rabobank / ABN AMRO for the Dutch glasshouse; DLL, BNP Paribas Leasing, Lombard, "
          "Siemens Financial Services for plant", mode="vendor"),
    Stack("C. Long-tenor infrastructure (PropCo owns glass + plant)",
          "Secured-income infrastructure funds (Greencoat precedent: GBP 120 M Low Carbon Farming, GBP 85 M Fenland "
          "cucumber house); pension money via those funds", senior_rate=0.060, senior_tenor=20, gearing_cap=0.75,
          hurdle=0.10),
    Stack("D. Asset-light: heat ESCo + LED lease + ECA on the glass",
          "Heat-plant ESCo (infrastructure fund or the heat-pump supplier), LED operating lease, Atradius DSB supplier "
          "credit", mode="asset_light", led_lease=True),
)


class StackFinance:
    """One design financed by one stack: scheme, minimum price at the stack's equity hurdle, results at given prices."""

    def __init__(self, project, stack: Stack, grant=0.0):
        self.p, self.st, self.grant = project, stack, grant
        self.senior = replace(P.SENIOR, rate=stack.senior_rate, tenor=stack.senior_tenor, gearing_cap=stack.gearing_cap)

    def scheme(self, price, stress=F.Stress()):
        if self.st.mode == "vendor":
            return next(sc for sc in F.SCHEMES if sc.name == F.CENTRAL)
        if self.st.mode == "asset_light":
            led = F.Tranche("LED operating lease", ("led_lighting",), 1.0, 0.08, 6, grace=0)
            return F.Scheme("asset-light", (F.ECA, led), esco=True)
        lender_case = replace(stress, yield_mult=stress.yield_mult * P.LENDER_YIELD)
        r = F.Finance(self.p, F.Scheme("sizing", (self.senior,), grant=self.grant), lender_case).run(price)
        g, n = self.senior.grace, self.senior.tenor
        tr = replace(self.senior, profile="given", fixed_amount=r["debt"], schedule=tuple(r["service"][g + 1:n + 1]))
        return F.Scheme(self.st.name, (tr,))

    def run(self, price, sizing_price=None, stress=F.Stress()):
        return F.Finance(self.p, replace(self.scheme(sizing_price or price, stress), grant=self.grant), stress).run(price)

    def min_price(self, stress=F.Stress()):
        lo, hi = 0.5, 4.0
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            r = self.run(mid, stress=stress)
            ok = (r["equity_irr"] or -1) >= self.st.hurdle and r["min_dscr"] >= F.DSCR_MIN - 1e-6
            lo, hi = (lo, mid) if ok else (mid, hi)
        return hi

    def summary(self, price, realistic):
        r = self.run(price)
        rr = self.run(realistic, sizing_price=realistic)
        idc = 0.5 * r["debt"] * self.st.senior_rate * P.BUILD_MONTHS / 12
        idc_r = 0.5 * rr["debt"] * self.st.senior_rate * P.BUILD_MONTHS / 12
        capex = sum(self.p.capex0.values())
        return dict(stack=self.st.name, funders=self.st.funders, hurdle=self.st.hurdle, min_price=self.min_price(),
                    capex=capex, esco_capex=r["esco_capex"],
                    tranches=[dict(name=t["name"], amount=t["amount"], rate=t["rate"], tenor=t["tenor"]) for t in r["tranches"]],
                    debt=r["debt"], equity=r["equity"] + idc, uses=capex - r["esco_capex"] + r["dsra0"] + r["wc0"] + r["fees0"] + idc,
                    at_target=F.Study.brief(r), at_realistic=dict(price=realistic, debt=rr["debt"], equity=rr["equity"] + idc_r,
                                                                 equity_irr=rr["equity_irr"], min_dscr=rr["min_dscr"]))


@dataclass(frozen=True)
class Lever:
    name: str
    stress: F.Stress = F.Stress()
    stack: int = 0
    capex_mult: float = 1.0
    grant: float = 0.0


LEVERS = (
    Lever("Base (plan lead)"),
    Lever("Risk: CO2 bought as liquid, GBP 0.25/kg", F.Stress(co2_gbp_kg=LIQUID_CO2)),
    Lever("Risk: yield -15 %", F.Stress(yield_mult=0.85)),
    Lever("Capex -10 % (fixed-price turnkey, contingency released)", capex_mult=0.90),
    Lever("Capex -20 %", capex_mult=0.80),
    Lever("Power -15 % (PPA GBP 76/MWh or flexibility income)", F.Stress(power_mult=0.85)),
    Lever("Yield +10 % (lit-cucumber best practice)", F.Stress(yield_mult=1.10)),
    Lever("Labour -15 % (harvest automation)", F.Stress(labour_mult=0.85)),
    Lever("CO2 from own CHP exhaust or distillery, GBP 0.03/kg", F.Stress(co2_gbp_kg=0.03)),
    Lever("Long-tenor infrastructure money (stack C)", stack=2),
    Lever("Capital grant GBP 1.5 M (SOSE heat-pump precedent: Arla, Lockerbie, 2026)", grant=SOSE_GRANT),
    Lever("Package 1: capex -10 %, power -10 %, stack C", F.Stress(power_mult=0.90), stack=2, capex_mult=0.90),
    Lever("Package 2: package 1 + yield +5 %, labour -10 %", F.Stress(power_mult=0.90, yield_mult=1.05, labour_mult=0.90),
          stack=2, capex_mult=0.90),
    Lever("Package 1 + GBP 1.5 M grant", F.Stress(power_mult=0.90), stack=2, capex_mult=0.90, grant=SOSE_GRANT),
    Lever("Package 2 with liquid CO2 at GBP 0.25/kg", F.Stress(power_mult=0.90, yield_mult=1.05, labour_mult=0.90,
                                                               co2_gbp_kg=LIQUID_CO2), stack=2, capex_mult=0.90),
)


class DesignSet:
    LABELS = {4.4: "4.4 ha cucumber", 6.0: "6 ha cucumber", 8.0: "8 ha cucumber (lead)", 10.0: "10 ha cucumber"}

    def __init__(self):
        rows = json.loads((OUT / "viable_lit.json").read_text())
        base = [r for r in rows if not (r["design"].get("grid") or r["design"].get("hp_source") or r["design"].get("waste"))]
        self.rows = [(self.LABELS[r["design"]["ha"]], r) for r in base if r["crop"] == "cucumber"]
        zero = next(r for r in rows if r["design"].get("plant", {}).get("backup") == "biomethane_chp_2025+hvo")
        self.rows.append(("8 ha cucumber, zero grid (biomethane CHP + HVO)", zero))
        name, ha, parts = "cucumber 6 ha + cherry tomato 2 ha", *P.MIXES["cucumber 6 ha + cherry tomato 2 ha"]
        self.rows.append(("8 ha: 6 ha cucumber + 2 ha cherry tomato", P.Mix.row(base, name, ha, parts)))


class Study:
    def __init__(self):
        self.m = MarketPrices()
        self.designs = DesignSet()

    @staticmethod
    def project(row, capex_mult=1.0):
        d = P.Design(row)
        p = copy.deepcopy(d.project)
        if capex_mult != 1.0:
            p.capex0 = {k: v * capex_mult for k, v in p.capex0.items()}
            p.rep, p.resid = p.rep * capex_mult, p.resid * capex_mult
        return d, p

    def prices(self, row):
        share = np.asarray(row["harvest_share"], float)
        share = share / share.sum()
        return share, {c.name: c.blended(self.m, share) for c in PRICE_CASES}

    def levers(self):
        _, lead = self.designs.rows[2]
        share, prices = self.prices(lead)
        out = []
        for lv in LEVERS:
            d, p = self.project(lead, lv.capex_mult)
            sf = StackFinance(p, STACKS[lv.stack], lv.grant)
            out.append(dict(lever=lv.name, min_price=sf.min_price(lv.stress)))
        base = out[0]["min_price"]
        for o in out:
            o["delta"] = o["min_price"] - base
            o["gap_to_realistic"] = o["min_price"] - prices[REALISTIC]
        winter = np.isin(np.arange(1, 13), WINTER)
        win_rev = float(self.m.parity[winter] @ share[winter]) * 0.95
        need_summer = {o["lever"]: (o["min_price"] - win_rev) / share[~winter].sum() for o in out}
        return dict(prices=prices, winter_share=float(share[winter].sum()), levers=out, summer_price_needed=need_summer,
                    farmgate=self.m.farmgate, parity_monthly=self.m.parity.tolist(), wholesale_monthly=self.m.wholesale.tolist())

    def stacks(self):
        res = []
        _, lead = self.designs.rows[2]
        _, lead_prices = self.prices(lead)
        ratio = lead_prices[REALISTIC] / lead_prices[PRICE_CASES[0].name]
        for label, row in self.designs.rows:
            d, p = self.project(row)
            realistic = self.prices(row)[1][REALISTIC] if row["crop"] == "cucumber" else d.price * ratio
            res.append(dict(design=label, ha=d.ha, capex=sum(p.capex0.values()), t_yr=p.kg / 1e3, target=d.price,
                            realistic=realistic,
                            stacks=[StackFinance(p, st).summary(d.price, realistic) for st in STACKS]))
        return res

    def run(self):
        return dict(levers=self.levers(), designs=self.stacks(), price_cases=[c.name for c in PRICE_CASES], realistic=REALISTIC)


class Report:
    @staticmethod
    def markdown(res):
        pct, m = F.Report.pct, lambda x: f"{x / 1e6:.2f}"
        lv = res["levers"]
        L = ["# Feasibility levers and funder stacks (bplan_funders.py)", "",
             f"Farm-gate cucumber (DEFRA, 2023-25): GBP {lv['farmgate']:.3f}/kg. Winter (Nov-Mar) share of the lit harvest: "
             f"{lv['winter_share']:.0%}.", "", "## Price the 8 ha lead is likely to get", "", "| Contract structure | GBP/kg |", "|---|---:|"]
        L += [f"| {k} | {v:.3f} |" for k, v in lv["prices"].items()]
        L += ["", "## Minimum price for a 12 % equity return (10 % on stack C), 8 ha lead", "",
              "| Lever | Min price | Change | Gap to realistic | Summer price needed (winter at parity -5 %) |", "|---|---:|---:|---:|---:|"]
        L += [f"| {o['lever']} | {o['min_price']:.3f} | {o['delta']:+.3f} | {o['gap_to_realistic']:+.3f} | "
              f"{lv['summer_price_needed'][o['lever']]:.3f} |" for o in lv["levers"]]
        for d in res["designs"]:
            L += ["", f"## {d['design']}: capex GBP {m(d['capex'])} M, {d['t_yr']:,.0f} t/yr, target GBP {d['target']:.3f}, "
                      f"realistic GBP {d['realistic']:.3f}", "",
                  "| Stack | Debt GBP M | Equity GBP M | Total uses GBP M | Min price | Equity IRR at target | min DSCR at target | "
                  "Debt at realistic | Equity at realistic | Equity IRR at realistic | min DSCR at realistic |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
            for s in d["stacks"]:
                t, r = s["at_target"], s["at_realistic"]
                L.append(f"| {s['stack']} | {m(s['debt'])} | {m(s['equity'])} | {m(s['uses'])} | {s['min_price']:.3f} | "
                         f"{pct(t['equity_irr'])} | {t['min_dscr']:.2f} | {m(r['debt'])} | {m(r['equity'])} | {pct(r['equity_irr'])} | "
                         f"{r['min_dscr']:.2f} |")
        return "\n".join(L) + "\n"


if __name__ == "__main__":
    res = Study().run()
    (OUT / "funders.json").write_text(json.dumps(res, indent=1, default=float))
    (OUT / "FUNDERS.md").write_text(Report.markdown(res))
    print(Report.markdown(res))
