"""Year-round study (BP34, user question 2026-10-05; constraints in CONSTRAINTS.md).

How can we grow crops in the UK year-round, as low-carbon and as cheaply as possible, while paying back soon enough to
attract investors? Stage 1 crops: cucumber and tomato.

  doe        Latin-hypercube design of experiments on the full model. Each point: site_opt.evaluate (physics + crop),
             finalist_lp (R717 heat pump + hot-water store, rule 'lp', 2010 winter check; the grid cap steps up when it
             cannot be met), cashflow.build at the lender price (DEFRA seasonal shape scaled to the GBP 1.01/kg UK
             farm-gate mean) and at the premium contract (GBP 1.57/kg), plus the minimum price for a 10-year payback.
             Results append to results/bplan/yearround_wind_doe_<crop>.json (resumable, cached).
  fit        Gaussian-process surrogates of every output against the design variables; optimise payback (lender case)
             against the constraint sheet on the surrogate; write the candidates.
  verify     re-run the surrogate's best candidates on the full model.

Yield used for money: model yield x the site's CBS light-anchor correction (bplan_10m.CapexCapStudy.yield_cap, taken
on the unlit run at 800 ppm), capped at the published lit ceiling (CONSTRAINTS.md #7): cucumber 105, tomato 100 kg/m2
(x usable floor share). Labour: half scales with kg (site_opt.LABOUR_KG_SHARE, placeholder) at the 2026 rate.

Wind (BP35b, user 2026-10-06): the electricity route is a design variable so wind scales with the glasshouse: owned
2.5 MW turbines (separate SPV, sells to the greenhouse at its LCOE, surplus exported; not in the capex cap), a
third-party on-site private-wire PPA, each with 1-4 turbines per module, or an LP-sized share of a wind farm.

    python bplan_yearround.py doe cucumber 60
    python bplan_yearround.py fit cucumber
    python bplan_yearround.py verify cucumber
"""
import json
import math
import sys

import numpy as np

import bplan_5ha as B5
import bplan_10m as M
import cashflow
import energy_grid
import finalist_lp
import site_opt

OUT = B5.OUTDIR
SITES = ("site_028", "site_002", "site_024")                 # Stranraer, Girvan, Ayr (south-west; Highlands screen BP31)
CEILING = {"cucumber": 105.0, "tomato": 100.0, "pepper": 35.0}   # kg/m2/yr, CONSTRAINTS.md #7; pepper PLACEHOLDER (lit ~30-40)
HOURS_MAX = {"cucumber": 20.0, "tomato": 18.0, "pepper": 18.0}               # tomato leaf injury under long photoperiods (to source)
CAPS = (500.0, 1000.0, 2400.0, None)
LENDER_MEAN, PREMIUM = 1.01, 1.57
# Water (CONSTRAINTS.md #16), PLACEHOLDERS until sourced: roof runoff coefficient 0.9 on the floor-area catchment;
# recirculating substrate system discharges 10 % on top of transpiration; lined basin GBP 15/m3
RUNOFF, DISCHARGE, BASIN_GBP_M3 = 0.9, 0.10, 15.0
# Products on the two calibrated crop models (2026-10-05). price = DEFRA wholesale variety (data/defra_wholesale_prices.csv,
# 2023-26 means: cucumber 1.16, round 1.26, vine 1.61, plum 2.34, cherry 3.13 GBP/kg); yield_f = fresh-weight yield vs the
# crop model; labour_f = labour per m2 vs the base crop; bulk = loose/bulk packing allowed. Sources: cherry 27-30 kg/m2
# high-tech (Dutch Greenhouses crop guide, secondary) vs CBS round 48 -> 0.6; others PLACEHOLDERS (KWIN not available).
PRODUCTS = {"cucumber": {"cucumber": dict(item=("cucumbers", "cucumbers"), yield_f=1.0, labour_f=1.0, bulk=True)},
            "pepper": {"red": dict(item=("capsicum", "red"), yield_f=1.0, labour_f=1.0, bulk=True)},
            "tomato": {"round": dict(item=("tomatoes", "round"), yield_f=1.0, labour_f=1.0, bulk=True),
                       "vine": dict(item=("tomatoes", "vine"), yield_f=0.95, labour_f=1.05, bulk=False),
                       "plum": dict(item=("tomatoes", "plum"), yield_f=0.80, labour_f=1.15, bulk=False),
                       "cherry": dict(item=("tomatoes", "cherry"), yield_f=0.60, labour_f=1.50, bulk=False)}}
# Lender price = DEFRA wholesale x the UK farm-gate / wholesale ratio for cucumber (DEFRA Horticulture Statistics 2023-25
# farm-gate GBP 1.01 vs wholesale 1.19 = 0.85), applied to every product (assumption: same chain margin)
FARMGATE_RATIO = 1.01 / 1.187
# By-product CO2 (Thanet-style recovery without combustion): fermentation/biomethane CO2 next door. Capture by dehydration
# and compression USD 6-35/t (IEA bioethanol CCS break-even 25-35; NETL screening estimates); delivered price GBP 0.06/kg
# PLACEHOLDER (range 0.03-0.10) incl. storage and a supplier margin, vs bought liquid GBP 0.20. Only where a source is
# adjacent: Stranraer (The Creamery, food/AD) and Girvan (Girvan + Ailsa Bay distilleries)
import breakeven  # noqa: E402

CO2_BYPRODUCT, CO2_BOUGHT, BYPRODUCT_SITES = 0.06, breakeven.P["co2_price"][0], ("site_028", "site_002")   # bought = study CO2 price (0.25 from 2026-10-07)
FOLLOW = (None, 0.15, 0.30)                                  # lights only while turbine output >= this per-unit level
PIPES = (2.25, 4.5)
WIND_ROUTES = ("own", "ppa", "farm_share")
TURBINE_KW, TURBINES_MAX = 2500.0, 4
# Constraint sheet for this study (user 2026-10-06): GBP 20 M per phase (was 10); carbon search ceiling 1.0 kg CO2e/kg
# (was 0.50), high-carbon designs are still reported and screened when ranking
CAP_GBP, CARBON_MAX = 20.0e6, 1.0
TAG = "yearround_wind"


class WindRoute:
    """energy_grid.ELEC_OPTIONS keys for n 2.5 MW turbines per module (own_2p5MW / tp_2p5MW scaled by count)."""
    BASE = {"own": "own_2p5MW", "ppa": "tp_2p5MW"}

    @classmethod
    def key(cls, route, n):
        if route == "farm_share":
            return "farm_share"
        base = cls.BASE[route]
        return base if n == 1 else f"{base}_x{n}"

    @classmethod
    def register(cls):
        for route, base in cls.BASE.items():
            for n in range(2, TURBINES_MAX + 1):
                O = energy_grid.ELEC_OPTIONS[base]
                energy_grid.ELEC_OPTIONS.setdefault(cls.key(route, n), {**O, "kw": O["kw"] * n,
                                                                        "label": f"{n} x {O['label']}"})


WindRoute.register()


class Space:
    """Design variables and their ranges; unit-cube <-> design mapping."""

    def __init__(self, crop):
        self.crop = crop
        self.products = tuple(PRODUCTS[crop])
        self.names = ("site", "ha", "ppfd", "inter_frac", "hours", "dli", "glazing", "cap", "product", "follow", "pipe",
                      "co2", "bulk", "wind", "turbines")
        self.lo = np.zeros(15)
        self.lo[[1, 4, 5, 14]] = (1.0, 16.0, 18.0, 1.0)
        self.hi = np.array([len(SITES), 8.0, 250.0, 0.5, HOURS_MAX[crop], 30.0, 2, len(CAPS) - 1, len(self.products),
                            len(FOLLOW), len(PIPES), 2, 2, len(WIND_ROUTES), TURBINES_MAX + 1])

    def design(self, u):
        v = self.lo + np.asarray(u) * (self.hi - self.lo)
        pick = lambda seq, x: seq[min(int(x), len(seq) - 1)]  # noqa: E731
        site, product = pick(SITES, v[0]), pick(self.products, v[8])
        ppfd = round(float(v[2]), 0)
        wind = pick(WIND_ROUTES, v[13])
        return dict(site=site, ha=round(float(v[1]), 2), ppfd=ppfd, inter_frac=round(float(v[3]), 2),
                    hours=round(float(v[4]) * 2) / 2, dli=round(float(v[5]), 1), glazing=pick(("single_2ar", "dbl_ar"), v[6]),
                    cap=CAPS[min(int(round(v[7])), len(CAPS) - 2)], product=product,
                    follow=pick(FOLLOW, v[9]) if ppfd > 0 else None, pipe=pick(PIPES, v[10]),
                    co2="byproduct" if v[11] >= 1 and site in BYPRODUCT_SITES else "bought",
                    bulk=bool(v[12] >= 1 and PRODUCTS[self.crop][product]["bulk"]), wind=wind,
                    turbines=0 if wind == "farm_share" else min(int(v[14]), TURBINES_MAX))

    def lhs(self, n, seed=34):
        rng = np.random.default_rng(seed)
        u = (np.argsort(rng.random((n, len(self.names))), axis=0) + rng.random((n, len(self.names)))) / n
        return [self.design(r) for r in u]

    def features(self, d):
        """Numeric feature vector for the surrogate (sites and glazing one-hot)."""
        return [*(1.0 if d["site"] == s else 0.0 for s in SITES), d["ha"], d["ppfd"], d["ppfd"] * d["inter_frac"], d["hours"],
                d["dli"], 1.0 if d["glazing"] == "dbl_ar" else 0.0, *(1.0 if d["product"] == p else 0.0 for p in self.products),
                d["follow"] or 0.0, d["pipe"], 1.0 if d["co2"] == "byproduct" else 0.0, 1.0 if d["bulk"] else 0.0,
                *(1.0 if d["wind"] == w else 0.0 for w in WIND_ROUTES), d["turbines"] * TURBINE_KW / 1e3 / d["ha"]]


class Water:
    @staticmethod
    def balance(transp_m, rain_m):
        """Monthly roof-rain vs irrigation per m2; basin (m3/m2) for 100 % on-site supply (sequent peak, cyclic)."""
        demand = np.asarray(transp_m) * (1 + DISCHARGE) / 1e3                # m3/m2
        supply = np.asarray(rain_m) * RUNOFF / 1e3
        net = np.tile(supply - demand, 2)
        k, peak = 0.0, 0.0
        for x in net:
            k = max(0.0, k - x)
            peak = max(peak, k)
        on_site = min(1.0, supply.sum() / max(demand.sum(), 1e-9))
        return dict(demand_m3_m2=float(demand.sum()), rain_m3_m2=float(supply.sum()), basin_m3_m2=peak,
                    on_site_share=on_site)


class Point:
    """One design on the full model."""

    def __init__(self, study, crop):
        self.st, self.crop = study, crop
        self.sites = {s["site_key"]: s for s in json.loads((B5.HERE / "data" / "siting" / "shortlist.json").read_text())}

    def opts(self, d):
        o = {"elec": WindRoute.key(d["wind"], d["turbines"]), "pipe_m2": d.get("pipe", 4.5), "hx_scale": 1.0}
        if d["ppfd"] > 0:
            h = d["hours"]
            o["light"] = {"ppfd": d["ppfd"], "inter_frac": d["inter_frac"], "dli_target": d["dli"],
                          "photoperiod": (13.0 - h / 2, 13.0 + h / 2)}
            if d.get("follow") is not None:
                o["light"]["follow_wind"] = d["follow"]
        return o

    def run(self, d):
        st, crop, site = self.st, self.crop, self.sites[d["site"]]
        x = st.layout(d["ha"], d["glazing"])
        o = self.opts(d)
        ev_o = {**o, "hp_boiler": 0.5, "co2": st.CO2, "labour_split": True}
        row = site_opt.evaluate(site, x, crop, ev_o)
        unlit = {k: v for k, v in o.items() if k != "light"}
        yc = st.yield_cap(site_opt.evaluate(site, x, crop, {**unlit, "hp_boiler": 0.5}))
        usable = row["usable"]
        prod = PRODUCTS[crop][d.get("product", crop if crop == "cucumber" else "round")]
        Y = min(row["Y"] * yc, CEILING[crop] * usable) * prod["yield_f"]
        ym = Y / row["Y"]
        row_c = site_opt.evaluate(site, x, crop, {**ev_o, "yield_mult": ym})
        lp, cap = None, None
        # Lights and auxiliaries are a fixed load the store cannot shift: a cap below it makes the LP buy batteries
        # (first pilot: 17 MWh, GBP 7.0 M against a GBP 0.6 M bigger connection). Start at the SPEN step above it.
        fixed_kw = float(np.max(finalist_lp.profiles(site, x, crop, o)["w_other"])) * 1.1
        first = next(i for i, c in enumerate(CAPS) if c is None or (c * 0.95 >= fixed_kw and i >= CAPS.index(d["cap"])))
        for c in CAPS[first:]:
            try:
                lp = finalist_lp.run(site, x, crop, row, st.study.price, "lp", store_kwh0=B5.CopLevers.STORE0 * d["ha"] / B5.HA,
                                     o=o, boiler=False, elec=o["elec"], store=True,
                                     **({} if c is None else {"import_cap_kw": c * 0.95}))
                cap = c
                break
            except finalist_lp.Infeasible:
                continue
        A = row["ledger"]["area_m2"]
        gbp_c, kg_c = st.search_basis(row_c, lp, A)
        entry = {"site": d["site"], "name": site["name"], "best": {"x": x}}
        pm, _ = cashflow.defra_monthly(*prod["item"])
        co2_mult = (CO2_BYPRODUCT if d.get("co2") == "byproduct" else CO2_BOUGHT) / CO2_BOUGHT
        pack_mult = 0.5 if d.get("bulk") else 1.0                  # bulk crates: BP24c PLACEHOLDER x0.5
        base = {"eval": ev_o, "yield_mult": ym, "commission": 0.0, "labour_mult": M.LABOUR_MULT * prod["labour_f"],
                "haul_mult": 0.0, "share": "crop", "price_item": prod["item"], "co2_mult": co2_mult, "pack_mult": pack_mult}
        lender = cashflow.build(site_opt.OUT, crop, entry, lp, "lp", {**base, "price_mult": FARMGATE_RATIO})
        prem = cashflow.build(site_opt.OUT, crop, entry, lp, "lp", {**base, "price_mult": 1.0})
        sh = np.asarray(row["monthly_share_crop"])
        w = Water.balance(row["transp_kg_m2_month"], row["rain_mm_month"])
        led = row["ledger"]
        c = lender["cost_gbp_kg"]
        adj = (c["co2_purchased"] * (1 - 1 / co2_mult) if co2_mult else -row_c["ledger"]["co2_gbp_yr"] / lender["kg_yr"])             + c["packing"] * (1 - 1 / pack_mult) + c["labour"] * (1 - 1 / prod["labour_f"])
        dose_kg = row["co2_dose_kg_m2"] * usable / Y
        # Owned turbines sell to the greenhouse at LCOE and lose on export, so the route is judged on the combined
        # greenhouse + turbine cash flow; the greenhouse-only figure is kept for reference
        own = d["wind"] == "own"
        min_p = self.min_price(entry, lp, base, crop, combined=own)
        min_p_gh = self.min_price(entry, lp, base, crop) if own else min_p
        return dict(design=d, cap_used=cap, Y_model=row["Y"], Y=Y, yield_mult=ym, usable=usable,
                    capex=lender["capex_total"] + w["basin_m3_m2"] * A * BASIN_GBP_M3 * 1.15, capex_ex_basin=lender["capex_total"],
                    opex=lender["opex_gbp_yr"], opex_gbp_kg=lender["opex_gbp_yr"] / lender["kg_yr"], kg_yr=lender["kg_yr"],
                    price_lender=lender["price_gbp_kg"], price_wholesale=prem["price_gbp_kg"], payback_lender=lender["payback"],
                    irr_lender=lender["irr"], npv8_lender=lender["npv_0.08"], lcop8=lender["lcop_0.08"],
                    payback_premium=prem["payback"], irr_premium=prem["irr"], min_price_10yr=min_p,
                    price_cover=min_p / lender["price_gbp_kg"], price_cover_gh=min_p_gh / lender["price_gbp_kg"],
                    search_gbp_kg_exfarm=gbp_c - row_c["logistics_gbp_kg"] + adj,
                    carbon=kg_c, carbon_dose_counted=kg_c + (dose_kg if d.get("co2") != "byproduct" else 0.0),
                    month_min_ratio=float(sh.min() / sh.mean()), winter_share=float(sh[[10, 11, 0, 1, 2]].sum()),
                    heat_kWh_m2=row["heat_kWh_m2"], elec_kWh_m2=row["elec_kWh_m2"], led_kW=led["led_kW"],
                    led_gbp=led["led_gbp"], hp_kW_th=lp["hp_kW_th"], store_kWh=lp["store_kWh"],
                    import_peak_kW=lp["import_peak_kW"], unmet_2010_h=lp.get("unmet_2010_h"), water=w,
                    labour_h_m2=row["ledger"]["labour_h_m2"] * prod["labour_f"], developer=HighlandDev.margin(site, lp, d),
                    cashflow_lender=lender["cashflow"], cashflow_wholesale=prem["cashflow"], area_m2=A,
                    turbine_spv=self.spv(lender))

    @staticmethod
    def spv(cf):
        """Owned-turbine route: the turbine business (sales to the greenhouse at LCOE + export) and greenhouse + turbine."""
        t = cf.get("turbine_business")
        if not t:
            return None
        return dict(capex=t["capex"], npv8=t["npv_008"], irr=t["irr"], payback=t["payback"],
                    combined_capex=cf["combined"]["capex"], combined_npv8=cf["combined"]["npv_008"],
                    combined_irr=cf["combined"]["irr"], combined_payback=cf["combined"]["payback"])

    @staticmethod
    def min_price(entry, lp, base, crop, target=10.0, combined=False):
        lo, hi = 0.5, 4.0
        for _ in range(16):
            mid = 0.5 * (lo + hi)
            cf = cashflow.build(site_opt.OUT, crop, entry, lp, "lp", {**base, "price_flat": mid})
            pb = cf["combined"]["payback"] if combined else cf["payback"]
            lo, hi = (lo, mid) if pb is not None and pb <= target else (mid, hi)
        return hi


class Phasing:
    """Scale-up over the years (user, 2026-10-05: the GBP 10 M limit applies per phase, not to the whole build). A module
    is one DOE design; a new module starts as soon as the project's cumulative cash covers its capex, until MAX_HA. Later
    modules share the site, the grid connection and the fixed part of the residual, worth SHARED of module capex
    (PLACEHOLDER: HV connection + fixed residual are ~5-8 % of a 2.5 ha module). Cash after year 30 is not counted; each
    module's replacements and residual follow its own start year, truncated at the horizon (conservative)."""
    MAX_HA, SHARED, YEARS = 10.0, 0.05, 30

    def __init__(self, point_result, case="cashflow_lender"):
        self.r, self.cf = point_result, np.asarray(point_result[case])
        self.capex = point_result["capex_ex_basin"]
        self.ha = point_result["area_m2"] / 1e4

    def run(self):
        n = self.YEARS + 1
        total = np.zeros(n)
        starts, area = [0], self.ha
        total[:] += self.cf[:n]
        for t in range(1, n):
            if area + self.ha > self.MAX_HA + 1e-9:
                break
            if total[:t].sum() >= self.capex * (1 - self.SHARED):
                m = self.cf.copy()
                m[0] *= (1 - self.SHARED)
                total[t:] += m[: n - t]
                starts.append(t)
                area += self.ha
        cum = np.cumsum(total)
        pb = next((t - 1 + (-cum[t - 1]) / total[t] for t in range(1, n) if cum[t] >= 0 > cum[t - 1]), None)
        return dict(starts=starts, final_ha=area, peak_funding=float(-cum.min()), payback=pb,
                    npv8=float(sum(c / 1.08 ** t for t, c in enumerate(total))), cash30=float(cum[-1]),
                    irr=cashflow.irr(total.tolist()))


class HighlandDev:
    @staticmethod
    def margin(site, lp, d):
        """Third-party developer margin per MWh (PPA route only): private-wire sales + export vs LCOE at 8 %."""
        if d["wind"] != "ppa":
            return None
        O, Oo = energy_grid.ELEC_OPTIONS["tp_2p5MW"], energy_grid.ELEC_OPTIONS["own_2p5MW"]
        gen = float((O["kw"] * d["turbines"] * site_opt.site_state(site)["pu80"][:8760]).sum()) / 1e3
        a8 = 0.08 / (1 - 1.08 ** -20)
        lcoe8 = (Oo["capex"] * a8 + Oo["om_kw_yr"]) * Oo["kw"] * d["turbines"] / gen
        used = lp["used_wind_MWh"]
        return (used * O["ppa"] * 1e3 + (gen - used) * Oo["export"] * 1e3) / gen - lcoe8


class DOE:
    def __init__(self, crop):
        self.crop, self.space = crop, Space(crop)
        self.file = OUT / f"{TAG}_doe_{crop}.json"

    def load(self):
        return json.loads(self.file.read_text()) if self.file.exists() else []

    def run(self, n, workers=None):
        """Pending designs run in parallel (CEA_WORKERS, default 1; ~1.5 GB per LP: on the 32 GB desktop use 5-6)."""
        import os
        from concurrent.futures import ProcessPoolExecutor, as_completed
        workers = workers or int(os.environ.get("CEA_WORKERS", 1))
        done = self.load()
        seen = {json.dumps(r["design"], sort_keys=True) for r in done}
        todo = [d for d in self.space.lhs(n) if json.dumps(d, sort_keys=True) not in seen]
        print(f"{self.crop}: {len(done)} done, {len(todo)} to run on {workers} worker(s)", flush=True)
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_point, self.crop, d): d for d in todo}
            for f in as_completed(futs):
                r = f.result()
                done.append(r)
                self.file.write_text(json.dumps(done, indent=1, default=float))
                self.report(r)
        return done

    @staticmethod
    def report(r):
        d = r["design"]
        if "error" in r:
            print(f"{d} ERROR {r['error']}", flush=True)
            return
        print(f"{d['site']} {d['product']:<8} {d['ha']:.1f} ha {d['glazing']:<10} ppfd {d['ppfd']:>3.0f} inter {d['inter_frac']:.2f} "
              f"{d['hours']:.0f} h dli {d['dli']:.0f} follow {d['follow']} pipe {d['pipe']} {d['co2']} bulk {d['bulk']} "
              f"wind {d['wind']} x{d['turbines']} | Y {r['Y']:.0f} "
              f"capex {r['capex'] / 1e6:.2f} M minP {r['min_price_10yr']:.2f} cover {r['price_cover']:.2f} CO2e {r['carbon']:.2f} "
              f"month-min {r['month_min_ratio']:.2f} water {r['water']['on_site_share']:.2f}", flush=True)


_PT = {}


def _point(crop, d):
    if crop not in _PT:
        _PT[crop] = Point(M.CapexCapStudy(), crop)
    try:
        return _PT[crop].run(d)
    except Exception as e:                                             # record and continue the batch
        return dict(design=d, error=repr(e)[:300])


class Surrogate:
    """Gaussian-process fits of each output on the design features; constraint-aware search on the surrogate."""
    OUTPUTS = ("capex", "opex_gbp_kg", "Y", "carbon", "month_min_ratio", "min_price_10yr", "price_cover", "lcop8",
               "search_gbp_kg_exfarm")

    def __init__(self, crop):
        self.crop, self.space = crop, Space(crop)
        self.rows = [r for r in DOE(crop).load() if "error" not in r]

    def fit(self):
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
        X = np.array([self.space.features(r["design"]) for r in self.rows])
        self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        Xn = (X - self.mu) / self.sd
        self.models, self.scores = {}, {}
        for k in self.OUTPUTS:
            y = np.array([r[k] for r in self.rows], float)
            gp = GaussianProcessRegressor(ConstantKernel() * RBF(np.ones(X.shape[1])) + WhiteKernel(), normalize_y=True,
                                          n_restarts_optimizer=3, random_state=0)
            self.models[k] = gp.fit(Xn, y)
            self.scores[k] = self.loo_r2(Xn, y, gp)
        return self

    @staticmethod
    def loo_r2(Xn, y, gp):
        """Leave-one-out R2 with the fitted kernel held fixed (honest check of predictive skill)."""
        from sklearn.base import clone
        pred = np.empty_like(y)
        for i in range(len(y)):
            m = np.ones(len(y), bool)
            m[i] = False
            g = clone(gp).set_params(kernel=gp.kernel_, optimizer=None).fit(Xn[m], y[m])
            pred[i] = g.predict(Xn[i:i + 1])[0]
        return float(1 - ((pred - y) ** 2).sum() / ((y - y.mean()) ** 2).sum())

    def predict(self, designs):
        Xn = (np.array([self.space.features(d) for d in designs]) - self.mu) / self.sd
        return {k: m.predict(Xn) for k, m in self.models.items()}

    def search(self, n=20000):
        """Candidates meeting CONSTRAINTS.md #1, #2 (per phase), #6 on the surrogate, ranked by price cover = minimum
        price for a 10-year payback / lender price of that product (<= 1 passes the lender test)."""
        cand = self.space.lhs(n, seed=7)
        p = self.predict(cand)
        ok = (p["capex"] < CAP_GBP) & (p["carbon"] <= CARBON_MAX) & (p["month_min_ratio"] >= 0.6)
        idx = [i for i in np.argsort(p["price_cover"]) if ok[i]][:10]
        best = [dict(design=cand[i], **{k: float(v[i]) for k, v in p.items()}) for i in idx]
        relaxed = [dict(design=cand[i], **{k: float(v[i]) for k, v in p.items()})
                   for i in np.argsort(p["price_cover"])[:5]]
        out = dict(scores=self.scores, n_points=len(self.rows), best_constrained=best, best_unconstrained=relaxed)
        (OUT / f"{TAG}_fit_{self.crop}.json").write_text(json.dumps(out, indent=1, default=float))
        print("LOO R2:", {k: round(v, 2) for k, v in self.scores.items()})
        for b in best[:5]:
            print("constrained", b["design"], {k: round(b[k], 3) for k in self.OUTPUTS})
        for b in relaxed[:3]:
            print("unconstrained", b["design"], {k: round(b[k], 3) for k in self.OUTPUTS})
        return out


if __name__ == "__main__":
    mode, crop = sys.argv[1], sys.argv[2]
    if mode == "doe":
        DOE(crop).run(int(sys.argv[3]) if len(sys.argv) > 3 else 60)
    elif mode == "fit":
        Surrogate(crop).fit().search()
    elif mode == "verify":
        fit = json.loads((OUT / f"{TAG}_fit_{crop}.json").read_text())
        pt = Point(M.CapexCapStudy(), crop)
        res = [pt.run(b["design"]) for b in fit["best_constrained"][:3]]
        for r in res:
            r["phasing"] = Phasing(r).run()
        (OUT / f"{TAG}_verify_{crop}.json").write_text(json.dumps(res, indent=1, default=float))
        for r in res:
            print(r["design"], {k: r[k] for k in ("Y", "capex", "payback_lender", "payback_premium", "min_price_10yr",
                                                  "carbon", "month_min_ratio")})
