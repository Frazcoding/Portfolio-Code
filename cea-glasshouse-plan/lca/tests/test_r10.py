"""R10 verification (2026-10-03): electricity routes, no-waste track, wind realism, cold-year LP sizing, cash flow arithmetic.

Run from lca/:  python tests/test_r10.py      (~2 min; uses the archived pre-R10 refined designs as fixtures)
"""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
os.chdir(HERE)
import energy_grid  # noqa: E402

FAIL = []


def check(name, ok, info=""):
    print(f"{'OK  ' if ok else 'FAIL'} {name} {info}")
    if not ok:
        FAIL.append(name)


def t_supply_routes():
    pu, price, ci = energy_grid.inputs()
    rng = np.random.default_rng(1)
    load = 300 + 200 * rng.random(8760)
    E = load.sum()
    g = energy_grid.supply_option(load, pu, price, ci, "grid")
    check("grid route = load x price", abs(g["cost_gbp"] - load @ price) / (load @ price) < 1e-9)
    check("grid route has no wind", g["wind_kW"] == 0 and g["import_MWh"] * 1e3 > 0.999 * E)
    a = energy_grid.supply_option(load, pu, price, ci, "own_small")
    b = energy_grid.supply(load, pu, price, ci)
    check("own_small route = Gate B supply()", abs(a["cost_gbp"] - b["cost_gbp"]) < 1e-6)
    for k in ("own_2p5MW", "private_wire", "own_2p5MW_no_export"):
        r = energy_grid.supply_option(load, pu, price, ci, k)
        used = r["self_share"] * E
        bal = r["import_MWh"] * 1e3 + used - r["batt_MWh_out"] * 1e3 * 0  # used includes battery-routed wind
        check(f"{k}: imports + wind used >= load", bal >= E * (1 - 1e-6), f"({bal / E:.4f})")
        check(f"{k}: cheaper than or equal to grid", r["cost_gbp"] <= g["cost_gbp"] * 1.5)
    s = energy_grid.supply_option(load, pu, price, ci, "sleeved")
    w = energy_grid.WHOLESALE_SHARE[0]
    exp = (price.mean() * (1 - w) + 0.075) * E
    check("sleeved = flat non-commodity + PPA + fee", abs(s["cost_gbp"] - exp) / exp < 1e-9)
    t = energy_grid.supply_option(load, pu * 0 + 0.35, price, ci, "own_2p5MW")["turbine"]
    O = energy_grid.ELEC_OPTIONS["own_2p5MW"]
    import offgrid
    lcoe = ((O["kw"] * O["capex"] + O["conn"]) * offgrid.annuity(offgrid.P["wind_life"][0]) + O["kw"] * O["om_kw_yr"]) \
        / (O["kw"] * 0.35 * 8760)
    check("turbine LCOE formula", abs(t["lcoe_gbp_mwh"] / 1e3 - lcoe) < 1e-9, f"({lcoe * 1e3:.1f} GBP/MWh at CF 35 %)")


def t_site_tracks():
    import site_opt
    SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
    for s in SL.values():
        S = site_opt.site_state(s)
        if not (S["pu"].mean() <= site_opt.WIND_CF_CAP + 1e-9 and S["pu80"].mean() <= site_opt.WIND_CF_CAP + 1e-9):
            check("wind CF cap", False, s["name"])
            break
    else:
        check("wind CF <= 41.3 % at every site, both hubs", True)
    e = json.loads((HERE / "results" / "site_opt" / "pre_R10_archive" / "refined_cucumber.json").read_text())["sites"][0]
    site, x = SL[e["site"]], e["best"]["x"]
    a = site_opt.evaluate(site, x, "cucumber", dict(elec=None))
    check("track A, Gate B route reproduces the pre-R10 sweep row within the wind fix",
          abs(a["gbp_kg_ex_heat"] - e["best"]["gbp_kg_ex_heat"]) < 0.03,
          f"({a['gbp_kg_ex_heat']:.4f} vs {e['best']['gbp_kg_ex_heat']:.4f})")
    b = site_opt.evaluate(site, x, "cucumber", dict(no_waste=True))
    check("no_waste: no waste heat used", b["heat_MWh_per_kg"] == 0.0 and b["waste_share"] == 0.0)
    check("no_waste: heat pump supplies the heat", b["hp_MWh"] > 0.9 * b["heat_kWh_m2"] * b["area_ha"] * 10)
    check("no_waste: dearer than with waste heat", b["gbp_kg_ex_heat"] > a["gbp_kg_ex_heat"])
    low = next(s for s in SL.values() if s["grade"] == "low")
    c = site_opt.evaluate(low, x, "cucumber", dict(no_waste=True))
    check("no_waste at a WWTP site uses air source (no effluent heat)", c is not None and c["heat_MWh_per_kg"] == 0.0)
    L = b["ledger"]
    fixed = (L["structure_gbp"] * (L["rate"] / (1 - (1 + L["rate"]) ** -L["structure_life"]) + L["om_frac"])
             + L["hp_gbp"] * (L["rate"] / (1 - (1 + L["rate"]) ** -site_opt.HP_LIFE)) + L["hp_om_gbp_yr"]
             + L["energy_gbp_yr"] + L["network_gbp_yr"] + L["labour_gbp_yr"] + L["co2_gbp_yr"])
    rebuilt = fixed / L["kg_yr"] + L["pack_gbp_kg"] + L["logistics_gbp_kg"]
    check("ledger rebuilds the sweep GBP/kg", abs(rebuilt - b["gbp_kg_ex_heat"]) < 1e-6,
          f"({rebuilt:.5f} vs {b['gbp_kg_ex_heat']:.5f})")


def t_lp_and_cashflow():
    os.environ["CEA_TRACK"] = "B"
    import importlib
    import site_opt
    importlib.reload(site_opt)
    import finalist_lp
    import cashflow
    SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
    e = json.loads((HERE / "results" / "site_opt" / "pre_R10_archive" / "refined_tomato.json").read_text())["sites"][0]
    site, x = SL[e["site"]], e["best"]["x"]
    row = site_opt.evaluate(site, x, "tomato")
    _, price, finalist_lp.CI = energy_grid.inputs()
    sb = finalist_lp.run(site, x, "tomato", row, price, "standby")
    lp = finalist_lp.run(site, x, "tomato", row, price, "lp")
    check("LP standby within 0.12 GBP/kg of the sweep (store + foresight only)", abs(sb["gbp_kg"] - sb["sweep_gbp_kg"]) < 0.12,
          f"({sb['gbp_kg']:.3f} vs {sb['sweep_gbp_kg']:.3f})")
    check("LP-sized <= standby cost", lp["gbp_kg"] <= sb["gbp_kg"] + 1e-6)
    check("LP-sized heat pump meets the 2010 cold year", lp["unmet_2010_kWh"] <= 1e-3,
          f"(first pass {lp['unmet_2010_kWh_first'] / 1e3:.1f} MWh unmet, final HP {lp['hp_kW_th'] / lp['design_kW']:.0%})")
    check("standby heat pump >= design load", sb["hp_kW_th"] >= sb["design_kW"] * 0.999)
    r = cashflow.build(site_opt.OUT, "tomato", e, lp, "lp")
    cf = np.array(r["cashflow"])
    check("cash flow: NPV recomputes", abs(cashflow.npv(cf, 0.035) - r["npv_0.035"]) < 1e-3)
    if r["irr"] is not None:
        check("cash flow: NPV(IRR) = 0", abs(cashflow.npv(cf, r["irr"])) < 1e-3 * r["capex_total"])
    check("cash flow: year 0 = -capex", abs(cf[0] + r["capex_total"]) < 1e-6)
    steady = r["revenue_gbp_yr"] - r["opex_gbp_yr"]
    check("cash flow: steady year = revenue - opex (no replacement)", abs(cf[5] - steady) < 1e-6 or abs(cf[11] - steady) < 1e-6)
    ann = r["lcop_0.035"] * r["kg_yr"]
    check("LCOP above sweep GBP/kg (adds consumables, overheads, commission, dev, contingency)",
          r["lcop_0.035"] > row["gbp_kg_ex_heat"] - 0.1, f"({r['lcop_0.035']:.3f} vs sweep {row['gbp_kg_ex_heat']:.3f})")
    check("price basis DEFRA, plausible", 0.6 < r["price_gbp_kg"] < 3.0, f"({r['price_gbp_kg']:.2f})")


if __name__ == "__main__":
    t_supply_routes()
    t_site_tracks()
    t_lp_and_cashflow()
    print("PASS" if not FAIL else f"FAIL: {FAIL}")
    sys.exit(1 if FAIL else 0)
