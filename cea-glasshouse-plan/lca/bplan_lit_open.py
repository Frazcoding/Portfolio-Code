"""BP37 (user, 2026-10-07): lit crop with the capex cap removed, priced just under imports, and paid for with supplier /
asset finance (vendor_finance.py).

Design: the BP32 lit lead (Stranraer site_028, single 2xAR glass, pipe 4.5 m/m2, third-party turbine PPA at GBP 90/MWh
on a private wire) with by-product CO2 from The Creamery (bplan_yearround CO2_BYPRODUCT GBP 0.06/kg, PLACEHOLDER) and
bulk crates (pack x0.5, PLACEHOLDER); retailer collects at the farm. No capex cap: the grid import cap steps up as
the lighting load needs (bplan_yearround CAPS).

Price (user: "slightly undercut the imports"): monthly import parity = Comtrade CIF by month (data/imports_monthly.csv,
2023-25, World) + UK haul to the RDC (GBP 1.57 annual parity - 1.408 tonnage-weighted CIF = GBP 0.162/kg), times
(1 - undercut), weighted by our own monthly harvest. Ex-farm, since the retailer collects: the retailer still saves
its import haul, so the undercut is real.

    python bplan_lit_open.py            -> results/bplan/lit_open.json
"""
import json
import sys

import numpy as np
import pandas as pd

import bplan_5ha as B5
import bplan_yearround as Y
import cashflow
import finalist_lp
import site_opt
import vendor_finance as VF

assert site_opt.TRACK == "B", "import bplan_5ha before site_opt: track B (no waste heat) is set at import time"
OUT = Y.OUT / "lit_open.json"
PARITY_ANNUAL = B5.FullCosting.IMPORT_PARITY


class ImportParity:
    def __init__(self, crop="cucumber"):
        im = pd.read_csv(Y.B5.HERE / "data" / "imports_monthly.csv")
        im = im[(im["crop"] == crop) & (im["origin"] == "World")]
        cif_w = float((im["tonnes"] * im["gbp_per_kg_cif"]).sum() / im["tonnes"].sum())
        self.haul = PARITY_ANNUAL - cif_w
        self.monthly = im.groupby("month")["gbp_per_kg_cif"].mean().reindex(range(1, 13)).to_numpy() + self.haul

    def price(self, harvest_share, undercut):
        return float(np.asarray(harvest_share) @ self.monthly) * (1.0 - undercut)


class LitOpen:
    BASE = dict(site="site_028", glazing="single_2ar", cap=500.0, product="cucumber", follow=None, pipe=4.5,
                co2="byproduct", bulk=True, wind="ppa", inter_frac=0.4, hours=18.0, dli=25.0)
    DESIGNS = [dict(ha=2.9, ppfd=0.0, turbines=1, inter_frac=0.0), dict(ha=2.9, ppfd=150.0, turbines=1),
               dict(ha=2.9, ppfd=150.0, turbines=2), dict(ha=2.9, ppfd=200.0, turbines=2),
               dict(ha=4.4, ppfd=150.0, turbines=2)]
    UNDERCUTS = (0.03, 0.05, 0.10)

    def __init__(self):
        self.st = Y.M.CapexCapStudy()
        self.pt = Y.Point(self.st, "cucumber")
        self.parity = ImportParity()

    def solve(self, d):
        st, crop, site = self.st, "cucumber", self.pt.sites[d["site"]]
        x = st.layout(d["ha"], d["glazing"])
        o = self.pt.opts(d)
        ev_o = {**o, "hp_boiler": 0.5, "co2": st.CO2, "labour_split": True}
        row = site_opt.evaluate(site, x, crop, ev_o)
        unlit = {k: v for k, v in o.items() if k != "light"}
        yc = st.yield_cap(site_opt.evaluate(site, x, crop, {**unlit, "hp_boiler": 0.5}))
        Yv = min(row["Y"] * yc, Y.CEILING[crop] * row["usable"])
        ym = Yv / row["Y"]
        fixed_kw = float(np.max(finalist_lp.profiles(site, x, crop, o)["w_other"])) * 1.1
        first = next(i for i, c in enumerate(Y.CAPS) if c is None or (c * 0.95 >= fixed_kw and i >= Y.CAPS.index(d["cap"])))
        lp, cap = None, None
        for c in Y.CAPS[first:]:
            try:
                lp = finalist_lp.run(site, x, crop, row, st.study.price, "lp", store_kwh0=B5.CopLevers.STORE0 * d["ha"] / B5.HA,
                                     o=o, boiler=False, elec=o["elec"], store=True,
                                     **({} if c is None else {"import_cap_kw": c * 0.95}))
                cap = c
                break
            except finalist_lp.Infeasible:
                continue
        entry = {"site": d["site"], "name": site["name"], "best": {"x": x}}
        co2_mult = Y.CO2_BYPRODUCT / Y.CO2_BOUGHT if d["co2"] == "byproduct" else 1.0
        base = {"eval": ev_o, "yield_mult": ym, "commission": 0.0, "labour_mult": Y.M.LABOUR_MULT, "haul_mult": 0.0,
                "share": "crop", "co2_mult": co2_mult, "pack_mult": 0.5 if d["bulk"] else 1.0}
        return row, lp, cap, entry, base, Yv

    def carbon(self, d, lp, base):
        """kg CO2e per kg on the design-search basis (bplan_10m.search_basis), by-product CO2 dose not counted, and with
        the dosed CO2 counted as emitted (bought liquid CO2 case)."""
        site = self.pt.sites[d["site"]]
        x = self.st.layout(d["ha"], d["glazing"])
        row_c = site_opt.evaluate(site, x, "cucumber", {**base["eval"], "yield_mult": base["yield_mult"]})
        _, kg_c = self.st.search_basis(row_c, lp, row_c["ledger"]["area_m2"])
        dose = row_c["co2_dose_kg_m2"] * row_c["usable"] / row_c["Y"]
        return kg_c, kg_c + dose

    def case(self, d):
        row, lp, cap, entry, base, Yv = self.solve(d)
        share = np.roll(np.asarray(row["monthly_share_crop"]), 1)          # same harvest lag as cashflow.build
        kg_c, kg_c_dose = self.carbon(d, lp, base)
        out = dict(design=d, cap_used=cap, Y=Yv, hp_kW_th=lp["hp_kW_th"], store_kWh=lp["store_kWh"],
                   import_peak_kW=lp["import_peak_kW"], winter_share=float(share[[10, 11, 0, 1, 2]].sum()),
                   carbon=kg_c, carbon_dose_counted=kg_c_dose, harvest_share=share.tolist(),
                   parity_monthly=self.parity.monthly.tolist(), parity_gbp_kg=self.parity.price(share, 0.0), prices={})
        for u in self.UNDERCUTS:
            p = self.parity.price(share, u)
            r = cashflow.build(site_opt.OUT, "cucumber", entry, lp, "lp", {**base, "price_flat": p})
            ramp = cashflow.v("ramp")
            kg_t = np.array([0.0] + [r["kg_yr"] * (ramp if t == 1 else 1.0) for t in range(1, cashflow.YEARS + 1)])
            var = sum(r["costs"][k] for k in ("packing", "haulage_to_rdc", "sales_commission"))
            ebitda_t = np.array([0.0] + [r["ebitda_gbp_yr"] - (1 - ramp) * (r["revenue_gbp_yr"] - var) if t == 1
                                         else r["ebitda_gbp_yr"] for t in range(1, cashflow.YEARS + 1)])
            fin = VF.VendorFinance(r["cashflow"], r["capex"], kg_t, ebitda_t).run(p)
            out["prices"][f"undercut {u:.0%}"] = dict(
                price=p, capex_total=r["capex_total"], capex=r["capex"], kg_yr=r["kg_yr"], opex=r["opex_gbp_yr"],
                cost_gbp_kg=r["cost_gbp_kg"], costs=r["costs"], revenue=r["revenue_gbp_yr"], cashflow=r["cashflow"],
                ramp=ramp, ebitda=r["ebitda_gbp_yr"], lcop_008=r["lcop_0.08"],
                lcop_0035=r["lcop_0.035"], npv_008=r["npv_0.08"], irr=r["irr"], payback=r["payback"], finance=fin)
        return out

    def run(self, only=None):
        rows = []
        for i, d in enumerate(self.DESIGNS):
            if only is not None and i not in only:
                continue
            c = self.case({**self.BASE, **d})
            rows.append(c)
            OUT.write_text(json.dumps(rows, indent=1, default=float))
            self.report(c)
        return rows

    @staticmethod
    def report(c):
        d = c["design"]
        print(f"\n{d['ha']} ha ppfd {d['ppfd']:.0f} turbines {d['turbines']}: Y {c['Y']:.1f} kg/m2, winter {c['winter_share']:.0%}, "
              f"CO2e {c['carbon']:.2f} ({c['carbon_dose_counted']:.2f} dose counted), HP {c['hp_kW_th']:.0f} kW, store {c['store_kWh'] / 1e3:.0f} MWh, cap {c['cap_used']}, parity {c['parity_gbp_kg']:.3f}", flush=True)
        for k, s in c["prices"].items():
            print(f"  {k}: price {s['price']:.3f}  capex {s['capex_total'] / 1e6:.2f} M  opex {s['opex'] / s['kg_yr']:.3f}/kg  "
                  f"LCOP8 {s['lcop_008']:.3f}  NPV8 {s['npv_008'] / 1e6:+.2f} M  IRR {s['irr'] and s['irr'] * 100:.1f} %  "
                  f"payback {s['payback'] and round(s['payback'], 1)}", flush=True)
            for n, f in s["finance"].items():
                print(f"     {n:<52} debt {f['debt'] / 1e6:5.2f} M equity {f['equity'] / 1e6:5.2f} M  minDSCR {f['min_dscr']:.2f}  "
                      f"eqIRR {f['equity_irr'] and f['equity_irr'] * 100:.1f} %  min price {f['min_price']:.3f}", flush=True)


if __name__ == "__main__":
    LitOpen().run([int(a) for a in sys.argv[1:]] or None)
