"""Viable design search (user goal 2026-10-07): the lit glasshouse scaled up, and other crops in the same house.

Each design runs the full physics chain through bplan_yearround.Point (greenhouse climate, LED, crop model, heat pump +
store LP, grid connection step, water balance, carbon) and saves, besides Point's summary, the cash-flow inputs that
finance.Project rebuilds (capex and opex lines, kg, replacement schedule) and the monthly harvest. Lit-lead settings
(BP32/BP37): Stranraer site_028, single 2xAR glass, pipe 4.5 m/m2, LEDs 150 umol for up to 18 h to a 25 mol daily light
target, third-party turbines on a PPA (one per ~2.2 ha, at least two), by-product CO2, bulk crates.

Price basis: import parity by month (Comtrade CIF + GBP 0.162 haul, bplan_lit_open.ImportParity) weighted by the design's
own harvest. Tomato products other than round take round-tomato parity times their DEFRA wholesale premium over round
(the same chain margin assumed).

    python bplan_viable.py scale        cucumber at 4.4 / 6 / 8 / 10 ha  -> results/bplan/viable_lit.json
    python bplan_viable.py crops <ha>   tomato (round, vine, cherry) at that area, same house
Needs the physics inputs: on the cloud set CEA_WEATHER_SOURCE=era5_s3 CEA_GRID_SOURCE=proxy (simcore/era5_open.py,
grid_proxy.py); results then carry "inputs": "cloud".
"""
import json
import os
import sys

import numpy as np

import bplan_5ha  # noqa: F401  (track B is set at import time, before site_opt)
import bplan_lit_open as L
import bplan_yearround as Y
import cashflow
import site_opt

assert site_opt.TRACK == "B"
OUT = Y.OUT / "viable_lit.json"
BASE = dict(site="site_028", glazing="single_2ar", cap=500.0, follow=None, pipe=4.5, co2="byproduct", bulk=True,
            wind="ppa", inter_frac=0.0, hours=18.0, dli=25.0, ppfd=150.0)


class CapturePoint(Y.Point):
    """Point.run plus the lender cash-flow build it makes (its inputs are what finance.Project needs)."""

    def run(self, d):
        calls, build = [], cashflow.build

        def record(*a, **k):
            r = build(*a, **k)
            calls.append(r)
            return r

        cashflow.build = record
        try:
            row = super().run(d)
        finally:
            cashflow.build = build
        r = calls[0]
        entry = dict(price=r["price_gbp_kg"], capex=r["capex"], capex_total=r["capex_total"], costs=r["costs"],
                     kg_yr=r["kg_yr"], revenue=r["revenue_gbp_yr"], cashflow=r["cashflow"], ramp=cashflow.v("ramp"),
                     lcop_008=r["lcop_0.08"], monthly_price_defra=r["monthly_price"])
        return row, entry, r["monthly_share"]


class Parity:
    def __init__(self):
        self.cuc, self.tom = L.ImportParity("cucumber"), L.ImportParity("tomato")

    def of(self, crop, product, share):
        if crop == "cucumber":
            return self.cuc.price(share, 0.0)
        p = self.tom.price(share, 0.0)
        if product == "round":
            return p
        prem = cashflow.defra_monthly(*Y.PRODUCTS["tomato"][product]["item"])[0]
        rnd = cashflow.defra_monthly(*Y.PRODUCTS["tomato"]["round"]["item"])[0]
        return p * float(np.asarray(share) @ prem) / float(np.asarray(share) @ rnd)


class Study:
    SCALE = (4.4, 6.0, 8.0, 10.0)

    def __init__(self):
        self.parity = Parity()
        self.points = {}
        self.rows = json.loads(OUT.read_text()) if OUT.exists() else []

    def point(self, crop):
        if crop not in self.points:
            self.points[crop] = CapturePoint(Y.M.CapexCapStudy(), crop)
        return self.points[crop]

    def design(self, crop, ha, product=None, **kw):
        d = {**BASE, "ha": ha, "product": product or crop, "turbines": max(2, round(ha / 2.2)), **kw}
        if crop == "tomato":
            d["hours"] = min(d["hours"], Y.HOURS_MAX["tomato"])
        return d

    def run_one(self, crop, d):
        key = json.dumps({"crop": crop, **d}, sort_keys=True)
        if any(r["key"] == key for r in self.rows):
            return
        row, entry, share = self.point(crop).run(d)
        par = self.parity.of(crop, d["product"], share)
        self.rows.append(dict(key=key, crop=crop, design=d, summary={k: v for k, v in row.items()
                                                                         if k not in ("cashflow_lender", "cashflow_wholesale")},
                              entry=entry, harvest_share=list(share), parity_gbp_kg=par,
                              inputs="cloud" if os.environ.get("CEA_WEATHER_SOURCE") == "era5_s3" else "api"))
        OUT.write_text(json.dumps(self.rows, indent=1, default=float))
        s = row
        print(f"{crop}/{d['product']} {d['ha']} ha: Y {s['Y']:.1f}, capex {s['capex'] / 1e6:.2f} M, opex {s['opex_gbp_kg']:.3f}/kg, "
              f"LCOP8 {s['lcop8']:.3f}, parity {par:.3f}, winter {s['winter_share']:.0%}, carbon {s['carbon']:.2f}, "
              f"HP {s['hp_kW_th']:.0f} kW, store {s['store_kWh'] / 1e3:.0f} MWh, import {s['import_peak_kW']:.0f} kW", flush=True)

    def scale(self):
        for ha in self.SCALE:
            self.run_one("cucumber", self.design("cucumber", ha))

    def crops(self, ha):
        for product in ("round", "vine", "cherry"):
            self.run_one("tomato", self.design("tomato", ha, product))


if __name__ == "__main__":
    st = Study()
    if sys.argv[1] == "scale":
        st.scale()
    else:
        st.crops(float(sys.argv[2]))
