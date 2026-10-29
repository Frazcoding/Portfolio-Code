"""5 ha viable case (user aim, 2026-10-05): track B cucumber at Stranraer, area fixed at 5 ha, joint cost-carbon objective.
Grid of layout x glazing x electricity route; each case is sized by the LP with heat pump + electric peak boiler + store
(rule 'standby': heat pump + boiler >= design load, the relaxed user rule) on the design-search basis. The fixed share of
the residual (BP19b, 17.7 %) applies. Reports GBP/kg and kg CO2e/kg and flags the cost-carbon front.

    python bplan_5ha.py            # writes results/bplan/viable_5ha.json
"""
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from itertools import product
from pathlib import Path

os.environ["CEA_TRACK"] = "B"
os.environ.setdefault("CEA_RESID_FIXED", "0.177")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))           # repo copy of simcore first (cloud has no ../simcore)
import energy_grid  # noqa: E402
import finalist_lp  # noqa: E402
import site_opt  # noqa: E402

OUTDIR = HERE / "results" / "bplan"
CROP, HA, SITE = "cucumber", 5.0, "site_028"
GLAZING = ("single_2ar", "dbl_ar")
ELEC = ("own_2p5MW", "sleeved", "grid")


class Layouts:
    """'strip' = the size-study 5 ha design (1 ha aspect ratio kept: 4 spans x ~730 m, most wall-light credit);
    'compact' = the same spans and roof on a near-square footprint (practical Venlo block, ~225 m long)."""

    def __init__(self, x_strip):
        self.strip = x_strip

    def compact(self):
        y = dict(self.strip)
        side = math.sqrt(HA * 1e4)
        y["n_spans"] = max(1, round(side / y["span_w"]))
        y["length"] = HA * 1e4 / (y["n_spans"] * y["span_w"])
        return y

    def all(self):
        return {"strip": self.strip, "compact": self.compact()}


class ViableCase:
    def __init__(self):
        SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
        self.site = SL[SITE]
        size = json.loads((site_opt.OUT / f"size_{CROP}.json").read_text())
        row = next(r for r in size["rows"] if r["site"] == SITE and r["ha"] == HA)
        self.layouts = Layouts(row["x"]).all()
        _, self.price, finalist_lp.CI = energy_grid.inputs()

    def run_case(self, layout, glazing, elec, extra=None):
        x = {**self.layouts[layout], "glazing": glazing}
        extra = dict(extra or {})
        store0 = extra.pop("store_kwh0", None)                     # warm start: one LP solve when the guess is close
        o = {"elec": elec, **extra}
        row = site_opt.evaluate(self.site, x, CROP, {**o, "hp_boiler": 0.5})
        r = finalist_lp.run(self.site, x, CROP, row, self.price, "standby", store_kwh0=store0, o=o, boiler=True, elec=elec)
        return dict(layout=layout, glazing=glazing, elec=elec, extra=extra or {}, scop=r["hp_heat_MWh"] / max(r["hp_elec_MWh"], 1e-9),
                    area_m2=row.get("area_m2", HA * 1e4), Y=row["Y"],
                    gbp_kg=r["gbp_kg"], kg_kg=r["kg_kg"], hp_kW_th=r["hp_kW_th"], boiler_kW_th=r["boiler_kW_th"],
                    store_kWh=r["store_kWh"], design_kW=r["design_kW"], boiler_MWh=r["boiler_MWh"],
                    hp_heat_MWh=r["hp_heat_MWh"], hp_elec_MWh=r["hp_elec_MWh"], import_MWh=r["import_MWh"],
                    import_peak_kW=r["import_peak_kW"], used_wind_MWh=r["used_wind_MWh"], x=x)

    @staticmethod
    def front(rows):
        """Cost-carbon front: a case is on it if no other case is at least as good on both and better on one."""
        for a in rows:
            a["on_front"] = not any(b is not a and b["gbp_kg"] <= a["gbp_kg"] and b["kg_kg"] <= a["kg_kg"]
                                    and (b["gbp_kg"] < a["gbp_kg"] or b["kg_kg"] < a["kg_kg"]) for b in rows)
        return rows

    def run(self, workers=int(os.environ.get("CEA_WORKERS", 2))):
        jobs = list(product(self.layouts, GLAZING, ELEC))
        with ProcessPoolExecutor(max_workers=workers) as ex:               # ~1.3 GB per LP; 8 GB machine
            rows = self.front(list(ex.map(_case, jobs)))
        for r in sorted(rows, key=lambda r: r["gbp_kg"]):
            print(f"{'*' if r['on_front'] else ' '} {r['layout']:<8}{r['glazing']:<11}{r['elec']:<10} GBP/kg {r['gbp_kg']:.3f}  "
                  f"kgCO2e/kg {r['kg_kg']:.3f}  Y {r['Y']:.1f}  HP {r['hp_kW_th']:.0f} boiler {r['boiler_kW_th']:.0f} "
                  f"store {r['store_kWh']:.0f} kWh (design {r['design_kW']:.0f})  import peak {r['import_peak_kW']:.0f} kW", flush=True)
        OUTDIR.mkdir(parents=True, exist_ok=True)
        (OUTDIR / "viable_5ha.json").write_text(json.dumps(rows, indent=1, default=float))
        return rows


class FullCosting:
    """Investor basis (cashflow.build: development, contingency, consumables, commission, ramp, replacements) for the
    front cases, with the import-parity contract price and the CO2 price sensitivity."""
    IMPORT_PARITY = 1.57                                       # BUSINESS_PLAN.md: CIF + haul to RDC
    VARIANTS = {"base (DEFRA wholesale)": {}, "import-parity contract": {"price_flat": IMPORT_PARITY},
                "contract + CO2 +25 % (GBP 0.31/kg)": {"price_flat": IMPORT_PARITY, "co2_mult": 1.25},
                "contract + free CO2": {"price_flat": IMPORT_PARITY, "co2_mult": 0.0},
                "contract + capex -20 %": {"price_flat": IMPORT_PARITY, "capex_mult": 0.8},
                "contract + free CO2 + capex -20 %": {"price_flat": IMPORT_PARITY, "co2_mult": 0.0, "capex_mult": 0.8}}

    def __init__(self, study):
        self.study = study

    def case(self, row):
        import cashflow
        extra = dict(row.get("extra") or {})
        store0 = extra.pop("store_kwh0", None)
        o = {"elec": row["elec"], **extra}
        ev = site_opt.evaluate(self.study.site, row["x"], CROP, {**o, "hp_boiler": 0.5})
        lp = finalist_lp.run(self.study.site, row["x"], CROP, ev, self.study.price, "standby", store_kwh0=store0, o=o,
                             boiler=True, elec=row["elec"])
        entry = {"site": SITE, "name": self.study.site.get("name", SITE), "best": {"x": row["x"]}}
        out = {}
        for k, v in self.VARIANTS.items():
            r = cashflow.build(site_opt.OUT, CROP, entry, lp, "standby", {"eval": {**o, "hp_boiler": 0.5}, **v})
            out[k] = {f: r[f] for f in ("price_gbp_kg", "lcop_0.08", "lcop_0.035", "npv_0.08", "npv_0.035", "irr",
                                        "capex_total", "capex_gbp_m2", "opex_gbp_yr", "revenue_gbp_yr", "kg_yr")}
            out[k]["capex"] = r["capex"]
            out[k]["cost_gbp_kg"] = r["cost_gbp_kg"]
            out[k]["combined"] = r.get("combined")
        return out

    def run(self):
        rows = json.loads((OUTDIR / "viable_5ha.json").read_text())
        res = {}
        for r in rows:
            if r["layout"] == "compact" and r["elec"] == "own_2p5MW":
                key = f"{r['layout']}/{r['glazing']}/{r['elec']}"
                res[key] = self.case(r)
                for k, v in res[key].items():
                    print(f"{key:<32}{k:<28} price {v['price_gbp_kg']:.2f}  LCOP 8 % {v['lcop_0.08']:.3f}  3.5 % "
                          f"{v['lcop_0.035']:.3f}  NPV 8 % {v['npv_0.08'] / 1e6:+.2f} M  IRR {v['irr'] or float('nan'):.3f}  "
                          f"capex {v['capex_total'] / 1e6:.2f} M", flush=True)
        (OUTDIR / "viable_5ha_cashflow.json").write_text(json.dumps(res, indent=1, default=float))
        return res


class CopLevers:
    """Heat-pump COP levers on the front case (compact, single glass, own turbine): emitter length (pipe-rail plus grow
    pipe, m/m2: lower supply temperature) and evaporator/condenser area (hx_scale). Extra pipe is costed at the pipe-rail
    rate in the model; the larger heat exchangers are NOT costed in the LP (reported separately as a placeholder)."""
    PIPES = (2.25, 3.4, 4.5)
    HX = (1.0, 2.0)
    STORE0 = 385929.0                                          # viable_5ha.json compact/single/own_2p5MW LP store

    def run(self, workers=int(os.environ.get("CEA_WORKERS", 2))):
        jobs = [("compact", "single_2ar", "own_2p5MW", {"pipe_m2": p, "hx_scale": h, "store_kwh0": self.STORE0})
                for p in self.PIPES for h in self.HX]
        with ProcessPoolExecutor(max_workers=workers) as ex:
            rows = list(ex.map(_case, jobs))
        for r in rows:
            print(f"pipe {r['extra']['pipe_m2']:.2f} m/m2  hx x{r['extra']['hx_scale']:.0f}  SCOP {r['scop']:.2f}  GBP/kg {r['gbp_kg']:.3f}  "
                  f"kgCO2e/kg {r['kg_kg']:.3f}  HP elec {r['hp_elec_MWh']:.0f} MWh  HP {r['hp_kW_th']:.0f} kW", flush=True)
        (OUTDIR / "viable_5ha_cop.json").write_text(json.dumps(rows, indent=1, default=float))
        return rows


class LeanPlan:
    """BP27 (2026-10-05, user: no store + boiler + heat pump together). Two-component heat plant only:
      hp_boiler: heat pump + electric peak boiler, no store; standby = heat pump + boiler >= design load with the roof
                 energy screen shut (config.design_heat_loss_w(screen=True), Svensson 43-47 % energy saving)
      hp_store:  heat pump + hot-water store, no boiler; rule 'lp' (LP-sized, floored to meet the 2010 cold year)
    x grid-import cap at the SPEN connection steps (cashflow.hv_conn_steps: 2.4 / 1.0 / 0.8 MVA at pf 0.95; the LP
    cannot see the step, so each cap is solved) x electricity route (tp_2p5MW: third-party turbine on site with a
    private-wire PPA, no turbine capex; own_2p5MW: owned, connection double count removed). Structure residual on
    the WUR 4-8 ha anchor (CEA_RESID_ANCHOR=wur, costing.wur_gbp_m2). Ranked on project NPV at 8 % (greenhouse, plus
    the turbine business when owned) at the central scenario of the plan."""
    PLANTS = {"hp_boiler": dict(rule="standby", boiler=True, store=False, screen_design=True),
              "hp_store": dict(rule="lp", boiler=False, store=True)}
    CAPS_KVA = (None, 2400.0, 1000.0, 800.0)
    ELECS = ("tp_2p5MW", "own_2p5MW")
    YC = 49.453 * 1.0618 / 56.268                              # BP25 capped yield, as 'plan'

    def __init__(self):
        self.study = ViableCase()
        self.row = next(r for r in json.loads((OUTDIR / "viable_5ha_cop.json").read_text())
                        if r["extra"].get("pipe_m2") == 4.5 and r["extra"].get("hx_scale") == 1.0)
        self.central = {"price_flat": FullCosting.IMPORT_PARITY, "yield_mult": self.YC, "commission": 0.0}

    def lp(self, elec, plant, cap_kva):
        x, o = self.row["x"], {"elec": elec, "pipe_m2": 4.5, "hx_scale": 1.0}
        pl = dict(self.PLANTS[plant])
        rule = pl.pop("rule")
        boiler = pl.pop("boiler")
        ev = site_opt.evaluate(self.study.site, x, CROP, {**o, "hp_boiler": 0.5})
        lp = finalist_lp.run(self.study.site, x, CROP, ev, self.study.price, rule,
                             store_kwh0=CopLevers.STORE0 if pl["store"] else None, o=o, boiler=boiler, elec=elec,
                             import_cap_kw=None if cap_kva is None else cap_kva * 0.95, **pl)
        return o, rule, lp

    def cash(self, o, rule, lp, variant):
        import cashflow
        entry = {"site": SITE, "name": self.study.site.get("name", SITE), "best": {"x": self.row["x"]}}
        return cashflow.build(site_opt.OUT, CROP, entry, lp, rule, {"eval": {**o, "hp_boiler": 0.5}, **variant})

    @staticmethod
    def project_npv(r):
        return r["combined"]["npv_008"] if r.get("combined") else r["npv_0.08"]

    def developer(self, lp):
        """Third-party turbine: average revenue per MWh (private-wire sales + export) vs its LCOE at 8 %."""
        O, Oo = energy_grid.ELEC_OPTIONS["tp_2p5MW"], energy_grid.ELEC_OPTIONS["own_2p5MW"]
        gen = float((O["kw"] * site_opt.site_state(self.study.site)["pu80"][:8760]).sum()) / 1e3
        a8 = 0.08 / (1 - 1.08 ** -20)
        lcoe8 = (Oo["kw"] * Oo["capex"] * a8 + Oo["kw"] * Oo["om_kw_yr"]) / gen
        used = lp["used_wind_MWh"]
        rev = (used * O["ppa"] * 1e3 + (gen - used) * Oo["export"] * 1e3) / gen
        return dict(gen_MWh=gen, used_MWh=used, lcoe_8pct_gbp_mwh=lcoe8, revenue_gbp_mwh=rev, margin_gbp_mwh=rev - lcoe8)

    def run(self):
        os.environ["CEA_RESID_ANCHOR"] = "wur"
        grid = []
        for elec, plant, cap in product(self.ELECS, self.PLANTS, self.CAPS_KVA):
            try:
                o, rule, lp = self.lp(elec, plant, cap)
            except finalist_lp.Infeasible as e:
                print(f"{elec:<10}{plant:<10}cap {cap} kVA: infeasible ({e})", flush=True)
                grid.append(dict(elec=elec, plant=plant, cap_kva=cap, feasible=False))
                continue
            r = self.cash(o, rule, lp, self.central)
            g = dict(elec=elec, plant=plant, cap_kva=cap, feasible=True, rule=rule, project_npv_008=self.project_npv(r),
                     npv_008=r["npv_0.08"], irr=r["irr"], lcop_008=r["lcop_0.08"], capex_greenhouse=r["capex_total"],
                     capex_raise=r["combined"]["capex"] if r.get("combined") else r["capex_total"],
                     hp_kW_th=lp["hp_kW_th"], boiler_kW_th=lp.get("boiler_kW_th", 0.0), store_kWh=lp["store_kWh"],
                     boiler_MWh=lp.get("boiler_MWh", 0.0), import_peak_kW=lp["import_peak_kW"],
                     standby_design_kW=lp["standby_design_kW"], design_kW=lp["design_kW"],
                     unmet_2010_h=lp.get("unmet_2010_h"), capex=r["capex"])
            grid.append(g)
            print(f"{elec:<10}{plant:<10}cap {str(cap):<7} raise {g['capex_raise'] / 1e6:5.2f} M  greenhouse "
                  f"{g['capex_greenhouse'] / 1e6:5.2f} M  project NPV 8 % {g['project_npv_008'] / 1e6:+.2f} M  LCOP 8 % "
                  f"{g['lcop_008']:.3f}  HP {g['hp_kW_th']:.0f} boiler {g['boiler_kW_th']:.0f} store {g['store_kWh'] / 1e3:.0f} MWh"
                  f"  peak {g['import_peak_kW']:.0f} kW", flush=True)
            (OUTDIR / "viable_5ha_lean_grid.json").write_text(json.dumps(grid, indent=1, default=float))
        ok = [g for g in grid if g["feasible"]]
        out = {"grid": grid, "best": {}}
        for elec in self.ELECS:
            b = max((g for g in ok if g["elec"] == elec), key=lambda g: g["project_npv_008"])
            o, rule, lp = self.lp(b["elec"], b["plant"], b["cap_kva"])
            scen = {}
            variants = {"central: capped yield, direct retailer contract at import parity": self.central,
                        "UK wholesale price, marketing organisation": {"yield_mult": self.YC},
                        "upside: capex -20 % (builder quotes)": {**self.central, "capex_mult": 0.8},
                        "upside: free CO2": {**self.central, "co2_mult": 0.0},
                        "risk: yield -15 %": {**self.central, "yield_mult": self.YC * 0.85},
                        "risk: price -10 %": {**self.central, "price_flat": FullCosting.IMPORT_PARITY * 0.9},
                        "risk: capex +20 %": {**self.central, "capex_mult": 1.2}}
            for k, v in variants.items():
                r = self.cash(o, rule, lp, v)
                scen[k] = {f: r[f] for f in ("price_gbp_kg", "lcop_0.08", "lcop_0.035", "npv_0.08", "npv_0.035", "irr",
                                             "capex_total", "capex_gbp_m2", "opex_gbp_yr", "revenue_gbp_yr", "kg_yr")}
                scen[k].update(capex=r["capex"], cost_gbp_kg=r["cost_gbp_kg"], combined=r.get("combined"),
                               turbine_business=r.get("turbine_business"))
                print(f"[{elec} {b['plant']} cap {b['cap_kva']}] {k:<66} LCOP 8 % {r['lcop_0.08']:.3f}  NPV 8 % "
                      f"{r['npv_0.08'] / 1e6:+.2f} M  IRR {r['irr'] or float('nan'):.3f}", flush=True)
            out["best"][elec] = {"choice": b, "scenarios": scen,
                                 "developer": self.developer(lp) if elec == "tp_2p5MW" else None}
        (OUTDIR / "viable_5ha_plan_lean.json").write_text(json.dumps(out, indent=1, default=float))
        return out


_STUDY = None


def _case(job):
    global _STUDY
    _STUDY = _STUDY or ViableCase()
    return _STUDY.run_case(*job)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cashflow_cop":            # investor basis of the chosen COP case
        study = ViableCase()
        row = next(r for r in json.loads((OUTDIR / "viable_5ha_cop.json").read_text())
                   if r["extra"].get("pipe_m2") == 4.5 and r["extra"].get("hx_scale") == 1.0)
        row["extra"] = {**row["extra"], "store_kwh0": CopLevers.STORE0}
        res = FullCosting(study).case(row)
        for k, v in res.items():
            print(f"pipe 4.5 hx1  {k:<36} LCOP 8 % {v['lcop_0.08']:.3f}  NPV 8 % {v['npv_0.08'] / 1e6:+.2f} M  "
                  f"IRR {v['irr'] or float('nan'):.3f}  capex {v['capex_total'] / 1e6:.2f} M", flush=True)
        (OUTDIR / "viable_5ha_cop_cashflow.json").write_text(json.dumps(res, indent=1, default=float))
    elif len(sys.argv) > 1 and sys.argv[1] == "retailer":             # BP24c: direct retailer contract on the SCOP 4 case
        study = ViableCase()
        row = next(r for r in json.loads((OUTDIR / "viable_5ha_cop.json").read_text())
                   if r["extra"].get("pipe_m2") == 4.5 and r["extra"].get("hx_scale") == 1.0)
        row["extra"] = {**row["extra"], "store_kwh0": CopLevers.STORE0}
        P = FullCosting.IMPORT_PARITY
        FullCosting.VARIANTS = {
            "contract via marketing org (5 % commission)": {"price_flat": P},
            "direct retailer contract (no commission)": {"price_flat": P, "commission": 0.0},
            "direct + retailer backhaul (no haulage)": {"price_flat": P, "commission": 0.0, "haul_mult": 0.0},
            "direct + backhaul + bulk crates (packing x0.5, PLACEHOLDER)": {"price_flat": P, "commission": 0.0,
                                                                           "haul_mult": 0.0, "pack_mult": 0.5},
            "direct, no commission, price = parity - our haulage": {"price_flat": P - 0.046, "commission": 0.0,
                                                                    "haul_mult": 0.0}}
        res = FullCosting(study).case(row)
        for k, v in res.items():
            c = v["cost_gbp_kg"]
            print(f"{k:<60} pack+haul+comm {c['packing'] + c['haulage_to_rdc'] + c['sales_commission']:.3f}  LCOP 8 % "
                  f"{v['lcop_0.08']:.3f}  NPV 8 % {v['npv_0.08'] / 1e6:+.2f} M  IRR {v['irr'] or float('nan'):.3f}", flush=True)
        (OUTDIR / "viable_5ha_retailer.json").write_text(json.dumps(res, indent=1, default=float))
    elif len(sys.argv) > 1 and sys.argv[1] == "plan":                 # scenario set the business proposition reads
        study = ViableCase()
        row = next(r for r in json.loads((OUTDIR / "viable_5ha_cop.json").read_text())
                   if r["extra"].get("pipe_m2") == 4.5 and r["extra"].get("hx_scale") == 1.0)
        row["extra"] = {**row["extra"], "store_kwh0": CopLevers.STORE0}
        P, Yc = FullCosting.IMPORT_PARITY, 49.453 * 1.0618 / 56.268     # BP25: yield capped at light gain, elasticity 1.0
        central = {"price_flat": P, "yield_mult": Yc, "commission": 0.0}
        FullCosting.VARIANTS = {
            "central: capped yield, direct retailer contract at import parity": central,
            "model yield (unexplained +13.8 %)": {**central, "yield_mult": 1.0},
            "via marketing organisation (5 % commission)": {**central, "commission": 0.05},
            "UK wholesale price, marketing organisation": {"yield_mult": Yc},
            "upside: retailer backhaul": {**central, "haul_mult": 0.0},
            "upside: free CO2": {**central, "co2_mult": 0.0},
            "upside: capex -20 % (builder quotes)": {**central, "capex_mult": 0.8},
            "upside: free CO2 + capex -20 %": {**central, "co2_mult": 0.0, "capex_mult": 0.8},
            "risk: CO2 +25 % (to GBP 0.31/kg)": {**central, "co2_mult": 1.25},
            "risk: yield -15 %": {**central, "yield_mult": Yc * 0.85},
            "risk: price -10 %": {**central, "price_flat": P * 0.9},
            "risk: capex +20 %": {**central, "capex_mult": 1.2}}
        res = FullCosting(study).case(row)
        for k, v in res.items():
            print(f"{k:<66} LCOP 8 % {v['lcop_0.08']:.3f}  3.5 % {v['lcop_0.035']:.3f}  NPV 8 % {v['npv_0.08'] / 1e6:+.2f} M  "
                  f"IRR {v['irr'] or float('nan'):.3f}  capex {v['capex_total'] / 1e6:.2f} M", flush=True)
        (OUTDIR / "viable_5ha_plan.json").write_text(json.dumps({"row": row, "scenarios": res}, indent=1, default=float))
    elif len(sys.argv) > 1 and sys.argv[1] == "lean":                 # BP27: two-component plant, import cap, TP turbine
        LeanPlan().run()
    elif len(sys.argv) > 1 and sys.argv[1] == "cop":
        CopLevers().run()
    elif len(sys.argv) > 1 and sys.argv[1] == "cashflow":
        FullCosting(ViableCase()).run()
    elif len(sys.argv) > 1 and sys.argv[1] == "one":
        print(json.dumps(ViableCase().run_case("compact", "single_2ar", "own_2p5MW"), indent=1, default=float))
    else:
        ViableCase().run()
