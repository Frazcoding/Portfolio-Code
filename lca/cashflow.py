"""Item 7: lifecycle cash flow and sales report on the final designs of both tracks (R10, 2026-10-03).

For each track (A waste heat: results/site_opt, B no waste heat: results/site_opt_B), crop and finalist (top TOP refined
designs) and heat-pump rule ('standby' = full design load, Gate B central; 'lp' = LP-sized heat pump + hot-water store,
floored to meet the 2010 cold year), a 30-year real-terms, pre-tax, unlevered (cash purchase) project cash flow:

  year 0      capital: structure (BOM x rates + SAC-calibrated residual), heat pump and hot-water store (finalist_lp), battery,
              waste-heat connection pipe (track A), greenhouse HV import connection, development costs, contingency
  years 1-30  revenue: kg x DEFRA wholesale price by month (what the supermarket pays, user decision), weighted by the
              design's monthly harvest share; year 1 at RAMP of full yield
              costs: electricity (LP dispatch: grid + wind bought from the turbine at its levelised cost), waste heat at
              GBP 10/MWh, labour, CO2, growing consumables, packing, haulage to the RDCs, structure O&M + insurance, heat-pump
              and store O&M, network charge increase, overheads, land rent, sales commission
              replacements at each item's life (rates.csv life_yr; heat pump 25 yr, battery 15 yr); residual value of
              the replaced items at year 30 (straight line)
  turbine     the owned 2.5 MW turbine (central route) is a separate business: capex + connection, O&M, sales to the
              greenhouse at its levelised cost, export at the PPA price; reported alone and combined with the greenhouse

Metrics: NPV at 3.5 % (Green Book) and 8 % (commercial), IRR, simple and discounted payback, levelised cost GBP/kg,
margin per kg. Sensitivities: price -10 %, yield -15 %, capex +20 %, consumables high, 8 % rate, vine tomato price,
import-parity price. Writes results/costing/cashflow.json and results/costing/FULL_COSTING.md.
"""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import breakeven  # noqa: E402
import offgrid  # noqa: E402

YEARS = 30
RATES = (0.035, 0.08)
TOP = 3
OUTD = HERE / "results" / "costing"
HEAT_GBP_MWH = 10.0
# ---- inputs added for the full costing (value, unit, tier, source) ----------------------------------------------------
C = {
    "ramp": (0.80, "-", "estimate", "year-1 output vs full (first crop establishment; Dutch practice for new houses)"),
    "dev_frac": (0.05, "of capex", "estimate", "design, planning, legal, site investigation (feasibility-stage allowance)"),
    "contingency": (0.10, "of capex", "estimate", "feasibility-stage contingency (estimate class 4, +-30 %)"),
    "import_conn_gbp": (150e3, "GBP", "sourced (range)", "11 kV connection near a substation GBP 50-150k (solargridcheck.co.uk "
                        "G99 guide 2026, DNO averages); upper end"),
    "hv_conn_steps": ([(800.0, 143000.0), (1000.0, 153900.0), (2400.0, 633900.0)], "kVA upper, GBP", "sourced",
                      "SP Energy Networks 'Statement of Methodology and Charges for Connection' (Nov 2025) worked demand "
                      "examples: Ex. 5 p.52 600 kVA, 800 kVA substation teed, 150 m 11 kV = GBP 143,000; Ex. 17 p.74 1 MVA "
                      "GBP 153,900; Ex. 18 p.76 2 MVA, 3 x 800 kVA + 1.2 km 11 kV = GBP 633,900. Above 2.4 MVA: +GBP 75k "
                      "per extra 800 kVA unit (Ex. 18 rate). Cable length is site-specific; reinforcement excluded"),
    "overheads_m2": (3.0, "GBP/m2/yr", "placeholder", "management, office, certification, accounts (no UK source found)"),
    "land_gbp_ha": (1000.0, "GBP/ha/yr", "placeholder", "land rent near an industrial host; Scottish arable rent is "
                    "~GBP 250-500/ha, industrial land more"),
    "commission": (0.05, "of revenue", "placeholder", "marketing organisation / sales commission, typical 3-8 %"),
    "plants_m2": ({"tomato": 4.0, "cucumber": 3.5, "pepper": 4.0}, "GBP/m2/yr", "sourced (range)",
                  "UK greenhouse tomato plant material GBP 1.61-2.01/m2 (Life cycle cost analysis of tomato production in "
                  "innovative urban agriculture systems, J. Cleaner Production 2022); KWIN 2023: tomato seedling EUR 3.00/plant "
                  "(grafted, ~2.5 plants/m2 -> ~GBP 6.4/m2); central between. Cucumber: three crops/yr of cheaper plants (estimate)"),
    "substrate_m2": (0.75, "GBP/m2/yr", "sourced", "KWIN 2023 growing media EUR 0.86/m2"),
    "materials_m2": ({"tomato": 2.4, "cucumber": 2.0, "pepper": 2.4}, "GBP/m2/yr", "sourced (secondary)",
                     "UK greenhouse tomato other materials GBP 2.27-2.48/m2 (J. Cleaner Production 2022, as above): "
                     "fertiliser, crop protection, pollination, strings, water; cucumber without bumblebees (estimate)"),
    "consumables_high": (1.5, "x", "sensitivity", "consumables x1.5"),
}
PRICE_ITEM = {"tomato": ("tomatoes", "round"), "cucumber": ("cucumbers", "cucumbers"), "pepper": ("capsicum", "red")}
PRICE_YEARS = (2023, 2026)


def hv_conn_gbp(peak_kw, pf=0.95):
    """Customer charge for the HV import connection, stepped on peak kVA (SPEN Nov 2025 worked examples)."""
    kva = peak_kw / pf
    for cap, gbp in v("hv_conn_steps"):
        if kva <= cap:
            return gbp
    cap, gbp = v("hv_conn_steps")[-1]
    return gbp + math.ceil((kva - cap) / 800.0) * 75000.0


def v(k):
    return C[k][0]


MIN_OBS = 3       # fewer DEFRA observations than this in a calendar month = no real UK market that month
CIF_CROP = {"tomatoes": "tomato", "cucumbers": "cucumber"}


def defra_monthly(item, variety):
    """Mean DEFRA wholesale price by calendar month over PRICE_YEARS (GBP/kg).

    DEFRA records UK-grown produce only, so winter months are thin or empty (round tomato: Jan-Feb none, Mar one
    observation). Before 2026-10-05 those months were back-filled from the single March value (GBP 3.00/kg), which
    overstated winter revenue. Now months with < MIN_OBS observations take the UK import CIF price for that month
    (Comtrade 2023-25, data/imports_monthly.csv, World): what the UK actually pays for the product then. CIF is below
    wholesale (no port handling or margin), so this is conservative. Items without import data still interpolate."""
    d = pd.read_csv(HERE / "data" / "defra_wholesale_prices.csv", parse_dates=["date"])
    d = d[(d["item"] == item) & (d["variety"] == variety) & (d["date"].dt.year.between(*PRICE_YEARS))]
    g = d.groupby(d["date"].dt.month)["price"]
    m = g.mean().reindex(range(1, 13))
    n = g.count().reindex(range(1, 13)).fillna(0)
    if item in CIF_CROP:
        im = pd.read_csv(HERE / "data" / "imports_monthly.csv")
        im = im[(im["crop"] == CIF_CROP[item]) & (im["origin"] == "World")]
        cif = im.groupby("month")["gbp_per_kg_cif"].mean().reindex(range(1, 13))
        m = m.where(n >= MIN_OBS, cif)
    return m.interpolate(limit_direction="both").to_numpy(), int(len(d))


def annuity_at(r, life):
    return r / (1 - (1 + r) ** -life)


def npv(cf, r):
    return float(sum(c / (1 + r) ** t for t, c in enumerate(cf)))


def irr(cf):
    lo, hi = -0.5, 1.0
    if npv(cf, lo) * npv(cf, hi) > 0:
        return None
    for _ in range(100):
        m = 0.5 * (lo + hi)
        if npv(cf, lo) * npv(cf, m) <= 0:
            hi = m
        else:
            lo = m
    return 0.5 * (lo + hi)


def payback(cf, r=0.0):
    cum = 0.0
    for t, c in enumerate(cf):
        prev = cum
        cum += c / (1 + r) ** t
        if t > 0 and cum >= 0 > prev:
            return t - 1 + (-prev) / (cum - prev)
    return None


def replacements(items_gbp, lives):
    """Capital outlays by year for items with life < YEARS, and their residual value at YEARS."""
    out = np.zeros(YEARS + 1)
    resid = 0.0
    for k, cost in items_gbp.items():
        L = lives.get(k) or YEARS
        if L >= YEARS:
            continue
        t = L
        while t < YEARS:
            out[int(round(t))] += cost
            last = t
            t += L
        resid += cost * (1 - (YEARS - last) / L)
    return out, resid


def build(track_dir, crop, entry, lp, rule, opts=None):
    """One project cash flow. entry: refined site entry; lp: finalist_lp result for this site and rule."""
    import costing
    import site_opt
    o = opts or {}
    site = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}[entry["site"]]
    ev = site_opt.evaluate(site, entry["best"]["x"], crop, o.get("eval", {}))
    L = ev["ledger"]
    A, usable = L["area_m2"], ev["usable"]
    kg = L["kg_yr"] * o.get("yield_mult", 1.0)
    R = costing.rates()
    lives = {k: R[k]["life_yr"] for k in L["structure_items"]}
    cm = o.get("capex_mult", 1.0)
    struct = {k: c * cm for k, c in L["structure_items"].items()}
    struct["residual (SAC-calibrated: install, climate computer, irrigation, vents ...)"] = L["structure_resid_gbp"] * cm
    plant = {"heat_pump": lp["hp_capex_gbp"] * cm, "peak_boiler": lp.get("boiler_capex_gbp", 0.0) * cm,
             "hot_water_store": lp["store_capex_gbp"] * cm,
             "battery": lp["batt_capex_gbp"] * cm, "waste_heat_pipe": L["pipe_gbp"] * cm,
             "hv_import_connection": hv_conn_gbp(lp["import_peak_kW"]) * cm, "led_lighting": L.get("led_gbp", 0.0) * cm}
    lives.update(heat_pump=site_opt.HP_LIFE, peak_boiler=site_opt.BOILER["life"], hot_water_store=40.0, battery=15.0, waste_heat_pipe=YEARS,
                 hv_import_connection=YEARS, led_lighting=L.get("led_life", 15.0))
    base = sum(struct.values()) + sum(plant.values())
    capex = dict(**struct, **plant, development=base * v("dev_frac"), contingency=base * v("contingency"))
    capex_total = sum(capex.values())
    # ---- revenue -------------------------------------------------------------------------------------------------
    share_key = "monthly_share_crop" if o.get("share") == "crop" else "monthly_share"     # BP34: crop model (sun + LED)
    share = np.roll(np.asarray(ev[share_key]), 1)                 # harvest lags light by ~1 month (site_rank.LAG_MONTHS)
    item, var = o.get("price_item", PRICE_ITEM[crop])
    pm, n_obs = defra_monthly(item, var)
    pm = pm * o.get("price_mult", 1.0)
    price = float(share @ pm) if o.get("price_flat") is None else o["price_flat"]
    revenue = kg * price
    # ---- annual costs ----------------------------------------------------------------------------------------------
    cons = o.get("cons_mult", 1.0)
    from finalist_lp import STORE, EUR15_EUR25
    costs = {
        "electricity_grid": lp["grid_cost_gbp"],
        "electricity_wind_from_turbine": lp["wind_cost_gbp"],
        "network_charge_increase": lp["net_gbp"],
        "waste_heat_purchase": L["waste_heat_MWh"] * HEAT_GBP_MWH,
        "labour": L["labour_gbp_yr"] * o.get("labour_mult", 1.0),
        "co2_purchased": L["co2_gbp_yr"] * o.get("co2_mult", 1.0),
        "young_plants": v("plants_m2")[crop] * A * usable * cons,
        "substrate": v("substrate_m2") * A * usable * cons,
        "fertiliser_protection_other": v("materials_m2")[crop] * A * usable * cons,
        "packing": L["pack_gbp_kg"] * kg * o.get("pack_mult", 1.0),
        "haulage_to_rdc": L["logistics_gbp_kg"] * kg * o.get("haul_mult", 1.0),
        "structure_om_insurance": L["om_gbp_yr"] * cm,
        "heat_pump_om": lp["hp_kW_th"] / 1e3 * site_opt.DEA_OM_EUR_MW * site_opt.EUR_GBP,
        "store_om": lp["store_kWh"] / 1e3 * STORE["om_eur_mwh"] * EUR15_EUR25 * site_opt.EUR_GBP,
        "boiler_om": lp.get("boiler_kW_th", 0.0) / 1e3 * site_opt.BOILER["om_eur_mw"] * site_opt.EUR_GBP,
        "overheads": v("overheads_m2") * A,
        "land_rent": v("land_gbp_ha") * A / 1e4 * 1.3,             # 30 % extra land for access, packhouse, plant
        "sales_commission": o.get("commission", v("commission")) * revenue,
    }
    opex = sum(costs.values())
    import bplan_residual
    lump = "residual (SAC-calibrated: install, climate computer, irrigation, vents ...)"
    lines = bplan_residual.ResidualItems(L["structure_resid_gbp"] / A).rows           # BP19b: each system replaced at its own life
    rep_items = {k: c for k, c in capex.items() if k != lump} | {r["key"]: r["gbp_m2_central"] * A * cm for r in lines}
    rep, resid = replacements(rep_items, lives | {r["key"]: float(r["life_yr"]) for r in lines})
    cf = np.zeros(YEARS + 1)
    cf[0] = -capex_total
    for t in range(1, YEARS + 1):
        f = v("ramp") if t == 1 else 1.0
        var_items = ("packing", "haulage_to_rdc", "sales_commission")
        c_t = opex - (1 - f) * sum(costs[k] for k in var_items)
        cf[t] = f * revenue - c_t - rep[t]
    cf[YEARS] += resid
    kg_t = np.array([0.0] + [kg * (v("ramp") if t == 1 else 1.0) for t in range(1, YEARS + 1)])
    disc = lambda r: np.array([(1 + r) ** -t for t in range(YEARS + 1)])  # noqa: E731
    res = dict(track=track_dir.name, crop=crop, site=entry["site"], name=entry["name"], rule=rule, area_ha=A / 1e4,
               kg_yr=kg, yield_kg_m2=kg / A, price_gbp_kg=price, price_basis=f"DEFRA wholesale {item}/{var} "
               f"{PRICE_YEARS[0]}-{PRICE_YEARS[1]} ({n_obs} obs), monthly x harvest share", revenue_gbp_yr=revenue,
               capex=capex, capex_total=capex_total, capex_gbp_m2=capex_total / A, costs=costs, opex_gbp_yr=opex,
               cost_gbp_kg={k: c / kg for k, c in costs.items()}, cashflow=cf.tolist(),
               ebitda_gbp_yr=revenue - opex, monthly_price=pm.tolist(), monthly_share=share.tolist(),
               hp_frac=lp["hp_kW_th"] / max(lp.get("design_kW", lp["hp_kW_th"]), 1.0), store_kWh=lp["store_kWh"],
               turbine=ev["turbine"])
    t = ev["turbine"]
    dwind = {r: 0.0 for r in RATES}                                 # BP8: transfer price = turbine LCOE at the rate being tested
    if t:
        lcoe = {r: (t["capex_gbp"] * annuity_at(r, offgrid.P["wind_life"][0]) + t["om_gbp_yr"]) / max(t["gen_MWh"] * 1e3, 1.0)
                for r in (breakeven.RATE,) + RATES}
        for r in RATES:                                             # LP wind cost was priced at breakeven.RATE (3.5 %)
            dwind[r] = lp["wind_cost_gbp"] * (lcoe[r] / lcoe[breakeven.RATE] - 1.0)
    cf_r = {}
    for r in RATES:
        D = disc(r)
        cf_r[r] = cf.copy()
        cf_r[r][1:] -= dwind[r]
        res[f"npv_{r}"] = float(cf_r[r] @ D)
        costs_pv = -(cf_r[r] - np.array([0.0] + [revenue * (v("ramp") if t_ == 1 else 1.0) for t_ in range(1, YEARS + 1)])) @ D
        res[f"lcop_{r}"] = float(costs_pv / (kg_t @ D))          # levelised cost of production, GBP/kg
        res[f"dpayback_{r}"] = payback(cf_r[r], r)
    res["irr"] = irr(cf)
    res["payback"] = payback(cf)
    res["margin_gbp_kg_3.5"] = price - res["lcop_0.035"]
    if t:   # turbine business (central route): 20-yr turbine re-powered once, i.e. a constant annuity over 30 yr
        tcf = np.zeros(YEARS + 1)
        tcf[0] = -t["capex_gbp"]
        sales = lp["wind_cost_gbp"]
        exp_rev = t["export_MWh"] * 1e3 * t["export_price"]
        for yr in range(1, YEARS + 1):
            tcf[yr] = sales + exp_rev - t["om_gbp_yr"] - (t["capex_gbp"] if yr == 20 else 0.0)
        tcf[YEARS] += t["capex_gbp"] * 0.5                         # repowered turbine half way through its life
        res["turbine_business"] = dict(capex=t["capex_gbp"], sales_to_greenhouse=sales, export_revenue=exp_rev,
                                       om=t["om_gbp_yr"], cf=tcf.tolist(), npv_0035=npv(tcf, 0.035),
                                       npv_008=npv(tcf, 0.08), irr=irr(tcf), payback=payback(tcf))
        comb = cf + tcf
        tcf8 = tcf.copy()
        tcf8[1:] += dwind[0.08]                                     # sales to the greenhouse at the 8 % LCOE
        res["turbine_business"]["npv_008"] = npv(tcf8, 0.08)
        res["combined"] = dict(npv_0035=npv(comb, 0.035), npv_008=npv(comb, 0.08), irr=irr(comb), payback=payback(comb),
                               capex=capex_total + t["capex_gbp"])
    return res


# BP20b: priced CO2 routes replace the zero-cost "co2_free" as the realistic upside. Recovered biogenic CO2 delivered as
# liquid: production USD 30-80 per short ton plus distribution about USD 30 (Ethanol Producer Magazine, 'Carbon Dioxide
# Use, Sequestration And New Markets'; US ethanol plants, secondary), USD 1 = GBP 0.73, 907 kg per short ton:
# (30+30..80+30) x 0.73 / 907 = GBP 0.048-0.088/kg. No capex on our side beyond the supplier's tank (not costed: quote needed).
CO2_ROUTE_GBP_KG = {"recovered_low": 0.048, "recovered_high": 0.088}
_CO2_BASE = breakeven.P["co2_price"][0]
SENS = {
    "price_-10%": dict(price_mult=0.9), "yield_-15%": dict(yield_mult=0.85), "capex_+20%": dict(capex_mult=1.2),
    "consumables_x1.5": dict(cons_mult=1.5),
    # upside levers (what would close the gap): zero-cost CO2 (an upper bound; priced routes are above), distillery host, GreenLight's yield response (refine.py yield_greenlight_x1.18), capex -20 %
    # (supplier quotes vs placeholders, which are ~half of structure capex), and all three together
    "co2_free": dict(co2_mult=0.0), "co2_recovered_low": dict(co2_mult=CO2_ROUTE_GBP_KG["recovered_low"] / _CO2_BASE),
    "co2_recovered_high": dict(co2_mult=CO2_ROUTE_GBP_KG["recovered_high"] / _CO2_BASE), "yield_+18%": dict(yield_mult=1.18), "capex_-20%": dict(capex_mult=0.8),
    "levers_combined": dict(co2_mult=0.0, yield_mult=1.18, capex_mult=0.8),
}


def run_track(track):
    os.environ["CEA_TRACK"] = track
    import importlib
    import site_opt
    importlib.reload(site_opt)
    out = []
    for crop in ("cucumber", "tomato"):
        R = json.loads((site_opt.OUT / f"refined_{crop}.json").read_text())
        LP = {s["site"]: s for s in json.loads((site_opt.OUT / f"lp_{crop}.json").read_text())["sites"]}
        B = R["benchmarks"]
        for entry in R["sites"][:TOP]:
            if entry["site"] not in LP:
                continue
            for rule in ("standby", "lp"):
                lp = LP[entry["site"]][rule]
                r = build(site_opt.OUT, crop, entry, lp, rule)
                r["import_parity_gbp_kg"] = B["gbp_annual"]
                r["sens"] = {}
                for k, o in SENS.items():
                    s = build(site_opt.OUT, crop, entry, lp, rule, o)
                    r["sens"][k] = dict(npv_0035=s["npv_0.035"], npv_008=s["npv_0.08"], irr=s["irr"],
                                            lcop=s["lcop_0.035"])
                extra = {"import_parity_price": dict(price_flat=B["gbp_annual"]),
                         "levers_combined_import_parity": dict(co2_mult=0.0, yield_mult=1.18, capex_mult=0.8,
                                                               price_flat=B["gbp_annual"])}
                if crop == "tomato":
                    extra["vine_price"] = dict(price_item=("tomatoes", "vine"))
                for k, o in extra.items():
                    s = build(site_opt.OUT, crop, entry, lp, rule, o)
                    r["sens"][k] = dict(npv_0035=s["npv_0.035"], npv_008=s["npv_0.08"], irr=s["irr"], price=s["price_gbp_kg"])
                out.append(r)
                print(f"[{track}] {crop:9}{entry['name'][:24]:25}{rule:8} capex {r['capex_total'] / 1e6:5.2f} M "
                      f"({r['capex_gbp_m2']:.0f}/m2)  price {r['price_gbp_kg']:.2f}  LCOP {r['lcop_0.035']:.2f}/"
                      f"{r['lcop_0.08']:.2f}  EBITDA {r['ebitda_gbp_yr'] / 1e3:6.0f} k  NPV3.5 {r['npv_0.035'] / 1e6:+.2f} M  "
                      f"NPV8 {r['npv_0.08'] / 1e6:+.2f} M  IRR {r['irr'] if r['irr'] is None else round(r['irr'] * 100, 1)} %  "
                      f"payback {r['payback'] and round(r['payback'], 1)}", flush=True)
    return out


if __name__ == "__main__":
    OUTD.mkdir(parents=True, exist_ok=True)
    tracks = sys.argv[1:] or ["A", "B"]
    allres = []
    for tr in tracks:
        allres += run_track(tr)
    (OUTD / "cashflow.json").write_text(json.dumps({"inputs": C, "results": allres}, indent=1, default=float))
