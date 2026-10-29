"""Capex-cap study (user goal, 2026-10-05): total raise under GBP 10 M, production cost at or below GBP 1.00/kg,
carbon at or below 0.50 kg CO2e/kg, and opex low enough that the project pays back within 5-10 years.

Starts from the BP27 lean design (track B cucumber, Stranraer, single 2xAR glass, R717 heat pump + hot-water store,
rule 'lp' floored to the 2010 winter, third-party 2.5 MW turbine on a private wire, so no turbine capex) and varies what
moves the raise: floor area (compact block), emitter pipe length (m/m2) and the grid-import cap (SPEN connection step).

Two cost bases, both reported:
  search    finalist_lp gbp_kg / kg_kg, the design-search basis behind the GBP 0.996/kg, 0.486 kg/kg 5 ha front case
            (BP23); shown at the model yield and at the BP25a light-anchored yield (yield_cap), delivered and ex-farm
  investor  cashflow.build: development, contingency, consumables, ramp, replacements; LCOP at 8 % and 3.5 %, simple
            and discounted payback at the sale price
The opex ceiling for an N-year payback is revenue - capex / N (steady year, no replacements inside N).

    python bplan_10m.py          # writes results/bplan/capex10m.json
"""
import json
import math
import os
import sys
from itertools import product

import bplan_5ha as B5
import finalist_lp
import site_opt

OUTDIR = B5.OUTDIR
CAP_GBP = 10.0e6
COST_TARGET, CARBON_TARGET = 1.00, 0.50
PAYBACK_YR = (5, 10)
# BP27a(h): the model's GBP 15/h rests on the April 2025 National Living Wage (GBP 12.21). April 2026 NLW GBP 12.71 (UK
# Government, Budget 26 Nov 2025) + holiday 12.07 % + employer NI 15 % above GBP 5,000/yr + 3 % auto-enrolment pension
# = ~GBP 16.3 per productive hour (CAPEX_OPEX_AUDIT.md finding 11)
LABOUR_MULT = 16.3 / 15.0


class CapexCapStudy:
    AREAS_HA = (2.9, 2.95)
    GLAZING = ("single_2ar",)
    PIPES = (4.5,)
    CAPS_KVA = (1000.0, 500.0)
    ELEC = "tp_2p5MW"
    P = B5.FullCosting.IMPORT_PARITY
    SCEN = {"contract at import parity": {"price_flat": P},
            "contract + retailer backhaul": {"price_flat": P, "haul_mult": 0.0},
            "sale at GBP 1.00/kg": {"price_flat": 1.00}}
    # CO2 dosing with vents closed: AHDB 'CO2 best practice guide: how much to use' (horticulture.ahdb.org.uk): "On sunny
    # days when the vents are closed, supplement with 1,000 ppm"; cucumber 800-1000 ppm spring/summer. Model default 800.
    CO2 = {"setpoint_closed": 1000.0}

    @staticmethod
    def yield_cap(row):
        """BP25a (2026-10-05): the crop model is calibrated to CBS 65 kg/m2 on the Westland house glazed with SINGLE plain glass
        (crop_gh.reference_house). Against that anchor scaled by light alone (elasticity 1, upper end of Marcelis et al. 2006
        0.8-1), single 2xAR glass at Stranraer is 2 % above and double AR 4-5 % below: the BP25 gap is mostly a double-glass
        shortfall. Yield is capped at the light-only CBS expectation, never raised. The ratio is taken at the model's
        default dosing (800 ppm, the calibration condition) and applied to the case yield, so a dosing change keeps its
        modelled effect."""
        import crop_gh
        return min(1.0, crop_gh.CBS_REF[B5.CROP] * row["light_rel"] / row["yield_m2_ex_usable"])

    def __init__(self):
        os.environ["CEA_RESID_ANCHOR"] = "wur"                 # WUR 4-8 ha anchor where valid, SAC + fixed share below
        self.study = B5.ViableCase()
        self.lean = B5.LeanPlan()
        self.x0 = self.lean.row["x"]

    def layout(self, ha, glazing="single_2ar"):
        x = dict(self.x0, glazing=glazing)
        side = math.sqrt(ha * 1e4)
        x["n_spans"] = max(1, round(side / x["span_w"]))
        x["length"] = ha * 1e4 / (x["n_spans"] * x["span_w"]) * (1 + 1e-9)
        return x

    @staticmethod
    def search_basis(row, lp, A):
        """finalist_lp's design-search GBP/kg and kg CO2e/kg recomputed on a given evaluate row (yield)."""
        sweep_energy = row["en_cost_gbp"] + row["hp_ann_gbp"] + row["net_gbp_yr"] + row["heat_MWh_per_kg"] * 10.0 * row["Y"] * A
        gbp = row["gbp_kg_ex_heat"] + row["heat_MWh_per_kg"] * 10.0 + (lp["annual_gbp"] - sweep_energy) / (A * row["Y"]) \
            + row["labour_gbp_m2"] * (LABOUR_MULT - 1.0) / row["Y"]
        kg = row["kg_kg"] + (lp["carbon_kg"] - row["elec_ci"] * row["elec_kWh_m2"] * A) / (A * row["Y"])
        return gbp, kg

    def case(self, ha, pipe, cap_kva, glazing="single_2ar"):
        x = self.layout(ha, glazing)
        o = {"elec": self.ELEC, "pipe_m2": pipe, "hx_scale": 1.0}
        ev_o = {**o, "hp_boiler": 0.5, "co2": self.CO2}
        row = site_opt.evaluate(self.study.site, x, B5.CROP, ev_o)
        yc = self.yield_cap(site_opt.evaluate(self.study.site, x, B5.CROP, {**o, "hp_boiler": 0.5}))  # anchor is at 800 ppm
        row_c = site_opt.evaluate(self.study.site, x, B5.CROP, {**ev_o, "yield_mult": yc})
        lp = finalist_lp.run(self.study.site, x, B5.CROP, row, self.study.price, "lp",
                             store_kwh0=B5.CopLevers.STORE0 * ha / B5.HA, o=o, boiler=False, elec=self.ELEC,
                             import_cap_kw=cap_kva * 0.95, store=True)
        A = row["ledger"]["area_m2"]
        gbp_c, kg_c = self.search_basis(row_c, lp, A)
        gbp_farm = gbp_c - row_c["logistics_gbp_kg"]
        out = dict(ha=A / 1e4, glazing=glazing, pipe_m2=pipe, cap_kva=cap_kva, x=x, Y_model=row["Y"], Y_capped=row_c["Y"],
                   search_gbp_kg=lp["gbp_kg"], search_kg_kg=lp["kg_kg"], search_gbp_kg_capped=gbp_c,
                   search_kg_kg_capped=kg_c, search_gbp_kg_exfarm=gbp_farm, yield_cap=yc, light_rel=row["light_rel"],
                   co2_dose_kg_m2=row["co2_dose_kg_m2"], heat_kWh_m2=row["heat_kWh_m2"], hp_kW_th=lp["hp_kW_th"], store_kWh=lp["store_kWh"],
                   design_kW=lp["design_kW"], import_peak_kW=lp["import_peak_kW"], unmet_2010_h=lp.get("unmet_2010_h"),
                   developer=self.developer(lp), scenarios={})
        entry = {"site": B5.SITE, "name": self.study.site.get("name", B5.SITE), "best": {"x": x}}
        import cashflow
        for name, sc in self.SCEN.items():
            price = sc["price_flat"]
            r = cashflow.build(site_opt.OUT, B5.CROP, entry, lp, "lp",
                               {"eval": ev_o, "yield_mult": yc, "commission": 0.0, "labour_mult": LABOUR_MULT, **sc})
            steady = r["revenue_gbp_yr"] - r["opex_gbp_yr"]
            out["scenarios"][name] = dict(
                price=price, capex_total=r["capex_total"], capex_gbp_m2=r["capex_gbp_m2"], capex=r["capex"],
                revenue=r["revenue_gbp_yr"], opex=r["opex_gbp_yr"], ebitda=steady, kg_yr=r["kg_yr"],
                opex_gbp_kg=r["opex_gbp_yr"] / r["kg_yr"], cost_gbp_kg=r["cost_gbp_kg"],
                lcop_008=r["lcop_0.08"], lcop_0035=r["lcop_0.035"], npv_008=r["npv_0.08"], npv_0035=r["npv_0.035"],
                irr=r["irr"], payback=r["payback"], dpayback_008=r["dpayback_0.08"],
                opex_ceiling={n: r["revenue_gbp_yr"] - r["capex_total"] / n for n in PAYBACK_YR})
        return out

    def developer(self, lp):
        self.lean.study = self.study
        return self.lean.developer(lp)

    @staticmethod
    def passes(c):
        s = c["scenarios"]["contract + retailer backhaul"]
        return dict(capex=s["capex_total"] < CAP_GBP, cost=c["search_gbp_kg_exfarm"] <= COST_TARGET,
                    carbon=c["search_kg_kg_capped"] <= CARBON_TARGET,
                    payback=s["payback"] is not None and s["payback"] <= PAYBACK_YR[1])

    def run(self, cases=None):
        rows = []
        for ha, glazing, pipe, cap in cases or product(self.AREAS_HA, self.GLAZING, self.PIPES, self.CAPS_KVA):
            try:
                c = self.case(ha, pipe, cap, glazing)
            except finalist_lp.Infeasible as e:
                print(f"{ha:.1f} ha {glazing} pipe {pipe} cap {cap}: infeasible ({e})", flush=True)
                continue
            c["pass"] = self.passes(c)
            rows.append(c)
            s, s1 = c["scenarios"]["contract at import parity"], c["scenarios"]["sale at GBP 1.00/kg"]
            sb = c["scenarios"]["contract + retailer backhaul"]
            print(f"{c['ha']:.2f} ha {glazing:<10} pipe {pipe:<4} cap {cap:<6.0f} capex {s['capex_total'] / 1e6:5.2f} M ({s['capex_gbp_m2']:.0f}/m2)"
                  f"  search {c['search_gbp_kg_capped']:.3f} GBP/kg {c['search_kg_kg_capped']:.3f} kg/kg (model Y "
                  f"{c['search_gbp_kg']:.3f}/{c['search_kg_kg']:.3f})  opex {s['opex_gbp_kg']:.3f}/kg  LCOP8 {s['lcop_008']:.3f}"
                  f"  payback {s['payback'] and round(s['payback'], 1)} yr (backhaul {sb['payback'] and round(sb['payback'], 1)}, at 1.00: {s1['payback'] and round(s1['payback'], 1)})"
                  f"  HP {c['hp_kW_th']:.0f} kW store {c['store_kWh'] / 1e3:.0f} MWh peak {c['import_peak_kW']:.0f} kW"
                  f"  pass {all(c['pass'].values())}", flush=True)
            self.save(c)
        return rows

    @staticmethod
    def save(c):
        """Merge into results/bplan/capex10m.json, one row per (area, glazing, pipe, import cap)."""
        f = OUTDIR / "capex10m.json"
        key = lambda r: (round(r["ha"], 2), r.get("glazing", "single_2ar"), r["pipe_m2"], r["cap_kva"])  # noqa: E731
        old = [r for r in (json.loads(f.read_text()) if f.exists() else []) if key(r) != key(c)]
        f.write_text(json.dumps(old + [c], indent=1, default=float))


class LeadCase:
    """The chosen design (2.9 ha, single glass, pipe 4.5 m/m2, 500 kVA import cap) with the plan's sensitivities. Central =
    direct retailer contract at import parity, retailer collects at the farm (ECF/REWE model, BP24c)."""
    HA, GLAZING, PIPE, CAP = 2.9, "single_2ar", 4.5, 500.0
    SENS = {"central (retailer collects)": {"haul_mult": 0.0},
            "own haulage to RDC": {},
            "risk: price -10 %": {"haul_mult": 0.0, "price_mult_flat": 0.9},
            "risk: yield -10 %": {"haul_mult": 0.0, "yield_x": 0.9},
            "risk: capex +10 %": {"haul_mult": 0.0, "capex_mult": 1.1},
            "risk: PPA GBP 100/MWh": {"haul_mult": 0.0, "ppa_x": 100.0 / 90.0},
            "UK wholesale (DEFRA) price": {"haul_mult": 0.0, "wholesale": True},
            "sale at GBP 1.00/kg": {"haul_mult": 0.0, "price_flat": 1.00}}

    def run(self):
        import cashflow
        st = CapexCapStudy()
        x = st.layout(self.HA, self.GLAZING)
        o = {"elec": st.ELEC, "pipe_m2": self.PIPE, "hx_scale": 1.0}
        ev_o = {**o, "hp_boiler": 0.5, "co2": st.CO2}
        row = site_opt.evaluate(st.study.site, x, B5.CROP, ev_o)
        yc = st.yield_cap(site_opt.evaluate(st.study.site, x, B5.CROP, {**o, "hp_boiler": 0.5}))
        lp = finalist_lp.run(st.study.site, x, B5.CROP, row, st.study.price, "lp",
                             store_kwh0=B5.CopLevers.STORE0 * self.HA / B5.HA, o=o, boiler=False, elec=st.ELEC,
                             import_cap_kw=self.CAP * 0.95, store=True)
        entry = {"site": B5.SITE, "name": st.study.site.get("name", B5.SITE), "best": {"x": x}}
        out = {}
        for k, v in self.SENS.items():
            v = dict(v)
            opt = {"eval": ev_o, "yield_mult": yc * v.pop("yield_x", 1.0), "commission": 0.0, "labour_mult": LABOUR_MULT,
                   "price_flat": st.P * v.pop("price_mult_flat", 1.0)}
            if v.pop("wholesale", False):
                opt.pop("price_flat")
                opt["commission"] = 0.05
            ppa = v.pop("ppa_x", 1.0)
            opt.update(v)
            l2 = dict(lp, wind_cost_gbp=lp["wind_cost_gbp"] * ppa)
            r = cashflow.build(site_opt.OUT, B5.CROP, entry, l2, "lp", opt)
            out[k] = dict(price=r["price_gbp_kg"], capex_total=r["capex_total"], capex=r["capex"], revenue=r["revenue_gbp_yr"],
                          opex=r["opex_gbp_yr"], ebitda=r["revenue_gbp_yr"] - r["opex_gbp_yr"], kg_yr=r["kg_yr"],
                          cost_gbp_kg=r["cost_gbp_kg"], opex_gbp_kg=r["opex_gbp_yr"] / r["kg_yr"], lcop_008=r["lcop_0.08"],
                          lcop_0035=r["lcop_0.035"], npv_008=r["npv_0.08"], npv_0035=r["npv_0.035"], irr=r["irr"],
                          payback=r["payback"], dpayback_008=r["dpayback_0.08"], cashflow=r["cashflow"],
                          opex_ceiling={n: r["revenue_gbp_yr"] - r["capex_total"] / n for n in PAYBACK_YR})
            print(f"{k:<30} price {r['price_gbp_kg']:.2f}  capex {r['capex_total'] / 1e6:.2f} M  opex {r['opex_gbp_yr'] / 1e6:.3f} M "
                  f"({r['opex_gbp_yr'] / r['kg_yr']:.3f}/kg)  EBITDA {(r['revenue_gbp_yr'] - r['opex_gbp_yr']) / 1e6:.3f} M  payback "
                  f"{r['payback'] and round(r['payback'], 1)}  NPV8 {r['npv_0.08'] / 1e6:+.2f} M  IRR {r['irr'] and round(r['irr'] * 100, 1)} %"
                  f"  ceiling10 {out[k]['opex_ceiling'][10] / 1e6:.3f} M", flush=True)
        rows = {(round(c["ha"], 2), c["cap_kva"]): c for c in json.loads((OUTDIR / "capex10m.json").read_text())}
        res = dict(design=rows[(self.HA, self.CAP)], yield_cap=yc, scenarios=out)
        (OUTDIR / "capex10m_lead.json").write_text(json.dumps(res, indent=1, default=float))
        return res


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "lead":
        LeadCase().run()
    elif args and args[0] == "one":
        cases = [(float(a.split(",")[0]), a.split(",")[1], float(a.split(",")[2]), float(a.split(",")[3])) for a in args[1:]]
        CapexCapStudy().run(cases)
    else:
        CapexCapStudy().run()
