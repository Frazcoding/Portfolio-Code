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
    python bplan_viable.py crops <ha>   sweet pepper (red) and tomato (round, vine, cherry) at that area, same house
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


for _n in range(5, 9):                                    # PPA contracts for 5-8 turbines (zero-grid designs)
    Y.energy_grid.ELEC_OPTIONS.setdefault(f"tp_2p5MW_x{_n}", {**Y.energy_grid.ELEC_OPTIONS["tp_2p5MW"],
                                                             "kw": 2500.0 * _n, "label": f"{_n} x third-party 2.5 MW"})
SEA_INTAKE_EUR_KW = 240.0   # DEA technology data 2026: '40 Comp. hp, seawater 20 MW' 1.19 less '40 waste heat 3 MW' 0.95 MEUR/MW_h


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
        if d.get("hp_source") == "sea":                  # DEA 2026: seawater HP 1.19 vs waste-heat HP 0.95 MEUR/MW_h (2025)
            r["capex"]["sea_water_intake"] = SEA_INTAKE_EUR_KW * site_opt.EUR_GBP * row["hp_kW_th"]
            r["capex_total"] = sum(r["capex"].values())
            r["cashflow"][0] = -r["capex_total"]
        entry = dict(price=r["price_gbp_kg"], capex=r["capex"], capex_total=r["capex_total"], costs=r["costs"],
                     kg_yr=r["kg_yr"], revenue=r["revenue_gbp_yr"], cashflow=r["cashflow"], ramp=cashflow.v("ramp"),
                     lcop_008=r["lcop_0.08"], monthly_price_defra=r["monthly_price"])
        return row, entry, r["monthly_share"]


class PepperParity(L.ImportParity):
    """Monthly CIF from the diversification import table (Comtrade 2023-25, World) + the same UK haul."""

    def __init__(self):
        import pandas as pd
        im = pd.read_csv(Y.B5.HERE / "data" / "imports_monthly_diversify.csv")
        im = im[(im["crop"] == "pepper") & (im["origin"] == "World")]
        self.haul = L.ImportParity("cucumber").haul
        self.monthly = im.groupby("month")["gbp_per_kg_cif"].mean().reindex(range(1, 13)).to_numpy() + self.haul


class Parity:
    def __init__(self):
        self.cuc, self.tom, self.pep = L.ImportParity("cucumber"), L.ImportParity("tomato"), PepperParity()
        self.tom.monthly = self.tom.monthly - self.tom.haul + self.cuc.haul       # ImportParity derives haul from cucumber

    def of(self, crop, product, share):
        if crop == "cucumber":
            return self.cuc.price(share, 0.0)
        if crop == "pepper":
            return self.pep.price(share, 0.0)
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
        d = {**BASE, "ha": ha, "product": product or crop, "turbines": min(4, max(2, round(ha / 2.2))), **kw}
        if crop == "tomato":
            d["hours"] = min(d["hours"], Y.HOURS_MAX["tomato"])
        return d

    def run_one(self, crop, d):
        key = json.dumps({"crop": crop, **d}, sort_keys=True)
        if any(r["key"] == key for r in self.rows):
            return
        row, entry, share = self.point(crop).run(d)
        par = self.parity.of(crop, d["product"], share)
        self.rows = json.loads(OUT.read_text()) if OUT.exists() else []       # another run may have written since
        self.rows.append(dict(key=key, crop=crop, design=d, summary={k: v for k, v in row.items()
                                                                         if k not in ("cashflow_lender", "cashflow_wholesale")},
                              entry=entry, harvest_share=list(share), parity_gbp_kg=par,
                              inputs="cloud" if os.environ.get("CEA_WEATHER_SOURCE") == "era5_s3" else "api"))
        OUT.write_text(json.dumps(self.rows, indent=1, default=float))
        s = row
        print(f"{crop}/{d['product']} {d['ha']} ha {d.get('hp_source', '')}{' waste' if d.get('waste') else ''}"
              f"{' zero-grid T' + str(d['turbines']) + ' ' + d['plant']['backup'] if d.get('grid') == 'none' else ''}: Y {s['Y']:.1f}, capex {s['capex'] / 1e6:.2f} M, opex {s['opex_gbp_kg']:.3f}/kg, "
              f"LCOP8 {s['lcop8']:.3f}, parity {par:.3f}, winter {s['winter_share']:.0%}, carbon {s['carbon']:.2f}, "
              f"HP {s['hp_kW_th']:.0f} kW, store {s['store_kWh'] / 1e3:.0f} MWh, import {s['import_peak_kW']:.0f} kW", flush=True)

    def scale(self):
        for ha in self.SCALE:
            self.run_one("cucumber", self.design("cucumber", ha))

    def energy(self, ha):
        """Heat-source options on the lit cucumber house: Loch Ryan sea water and The Creamery's waste heat."""
        self.run_one("cucumber", self.design("cucumber", ha, hp_source="sea"))
        self.run_one("cucumber", self.design("cucumber", ha, waste=True))

    def zero_grid(self, ha, turbines=(4, 6, 8), backups=("gas_chp", "biomethane_chp", "hvo")):
        """No grid import: the LP sizes battery, heat store and the backup engine (and may add PV) against the turbines."""
        for n in turbines:
            for b in backups:
                self.run_one("cucumber", {**self.design("cucumber", ha), "turbines": n, "grid": "none",
                                          "plant": {"backup": b, "pv": True}})

    def cheapest(self, ha, ppa=0.082):
        """Least-cost zero grid: four turbines on a cost-reflective PPA (developer break-even at 8 %), biomethane CHP backup,
        with and without The Creamery's waste heat."""
        for waste in (False, True):
            self.run_one("cucumber", {**self.design("cucumber", ha), "grid": "none", "ppa": ppa,
                                      "plant": {"backup": "biomethane_chp", "pv": True}, **({"waste": True} if waste else {})})
        for b in ("biomethane_chp+hvo", "biomethane_chp_2025", "biomethane_chp_2025+hvo"):
            self.run_one("cucumber", {**self.design("cucumber", ha), "grid": "none", "ppa": ppa, "plant": {"backup": b, "pv": True}})

    def crops(self, ha):
        self.run_one("pepper", self.design("pepper", ha, "red"))
        for product in ("round", "vine", "cherry"):
            self.run_one("tomato", self.design("tomato", ha, product))


if __name__ == "__main__":
    st = Study()
    if sys.argv[1] == "scale":
        st.scale()
    elif sys.argv[1] == "zerogrid":
        st.zero_grid(float(sys.argv[2]))
    elif sys.argv[1] == "cheapest":
        st.cheapest(float(sys.argv[2]))
    elif sys.argv[1] == "energy":
        st.energy(float(sys.argv[2]))
    else:
        st.crops(float(sys.argv[2]))
