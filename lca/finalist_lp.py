"""Item 4: heat store, heat pump, turbine and battery sized together by LP (PyPSA + HiGHS) for the Gate B finalists.

For each finalist (refined design at its site, results/site_opt/refined_<crop>.json) the hourly greenhouse heat
demand (pipe heat, from greenhouse_fast with the site's waste heat) and the other electricity load are met at least
annual cost by:
  * waste heat: up to the site's mean waste-heat rate when the source runs (site_opt.availability: planned shutdown
    + one unplanned week in the coldest week), at GBP 10/MWh (central heat price)
  * R717 heat pump (electricity -> heat, hourly COP from a heat-pump-only run of the same design): DEA ch. 40 air
    source capex by size, 25 yr. Two rules: 'lp' (the LP chooses the size, so the store can cover part of the
    outage) and 'standby' (heat output at the design hour >= design heat load: the Gate B central rule, user
    2026-10-03)
  * hot-water heat store: DEA (2019) Technology Data for Energy Storage, ch. 'large-scale hot water tanks':
    CAPEX 7,450 V^-0.47 EUR2015/m3 (V tank m3), standing loss 0.2 %/day, life 40 yr, fixed O&M 8.6 EUR2015/MWh/yr;
    EUR2015 -> EUR2025 x 1.2876 (Eurostat HICP euro area annual average index, prc_hicp_aind, 2025/2015);
    25 K useful swing (29 kWh/m3, design choice: return ~30 C, R717 supply ~55 C). Cost per kWh depends on size,
    so the LP is re-solved with the cost at the previous solution's volume (3 passes)
  * wind (wind bus: serves the load, charges the battery, surplus is exported) and a battery that charges from our
    own wind only, as energy_grid; export earns nothing in the LP (sizing for own use, user 2026-10-03) and is
    credited at SEG afterwards
  * grid import at the hourly Agile shape scaled to the DESNZ mean; the 2026 TNUoS band increase is applied after
    the LP from the import peak (site_opt.network_inc_gbp)
Writes results/site_opt/lp_<crop>.json and prints the comparison with the sweep's dispatch for the same design.
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import energy_grid  # noqa: E402
import greenhouse_fast  # noqa: E402
import offgrid  # noqa: E402
import optimise  # noqa: E402
import site_opt  # noqa: E402

EUR15_EUR25 = 128.76 / 100.0
STORE = {"capex_a": 7450.0, "capex_b": -0.47, "loss_day": 0.002, "life": 40.0, "om_eur_mwh": 8.6,
         "kwh_m3": 4.186 * 25 / 3.6}
HEAT_PRICE = 10.0 / 1e3        # GBP/kWh
# Zero-grid supply (user 2026-10-07: no grid top-ups). Firm backup engines and PV from the Danish Energy Agency technology
# data (data/dea_el_dh_datasheets_2026.xlsx, 2030 column, EUR 2020 x 1.20 to 2025 x EUR_GBP); fuels:
#   natural gas 4.4 p/kWh: DESNZ Quarterly Energy Prices June 2026, non-domestic medium, Q1 2026 (secondary: search extract
#   of table 3.4.2); biomethane = gas + RGGO certificates ~GBP 40/MWh (Green Gas Certification Scheme, Feb 2024 level);
#   HVO GBP 1.50/l = 0.153 GBP/kWh at 9.8 kWh/l (PLACEHOLDER: pump median 206 p/l incl. duty and VAT, bulk 10-30 % above diesel)
DEA_EUR = 1.20 * 0.8567
BACKUP = {
    "gas_chp": dict(capex_kwe=957.0 * DEA_EUR, fom_kwe=9.889 * DEA_EUR, vom_kwhe=0.00542 * DEA_EUR, eff_e=0.47, eff_h=0.47,
                    fuel=0.044, ci_fuel=0.183, life=25.0, label="Natural-gas engine CHP (DEA 06)"),
    "biomethane_chp": dict(capex_kwe=957.0 * DEA_EUR, fom_kwe=9.889 * DEA_EUR, vom_kwhe=0.00542 * DEA_EUR, eff_e=0.47,
                           eff_h=0.47, fuel=0.084, ci_fuel=0.03, life=25.0, label="Engine CHP on certified biomethane (DEA 06)"),
    "biomethane_chp_2025": dict(capex_kwe=957.0 * DEA_EUR, fom_kwe=9.889 * DEA_EUR, vom_kwhe=0.00542 * DEA_EUR, eff_e=0.47,
                                eff_h=0.47, fuel=0.059, ci_fuel=0.03, life=25.0,
                                label="Engine CHP on biomethane, certified-waste RGGOs at GBP 13-15/MWh (C-Zero Markets, Jul 2025)"),
    "hvo": dict(capex_kwe=362.0 * DEA_EUR, fom_kwe=8.983 * DEA_EUR, vom_kwhe=0.00638 * DEA_EUR, eff_e=0.35, eff_h=0.0,
                fuel=0.153, ci_fuel=0.03, life=25.0, label="HVO engine generator, no heat recovery (DEA 50)"),
}
PV = dict(capex_kw=595.4 * DEA_EUR / 1.20, fom_kw=10.03 * DEA_EUR / 1.20, pr=0.82, life=25.0,
          label="Utility-scale PV, DEA 22 (2025, already 2025 EUR)")
FINALISTS = 3


def store_gbp_kwh(kwh):
    v = max(kwh / STORE["kwh_m3"], 50.0)
    return STORE["capex_a"] * v ** STORE["capex_b"] * EUR15_EUR25 * site_opt.EUR_GBP / STORE["kwh_m3"]


def profiles(site, x, crop, o=None):
    import simstore
    oo = {**site_opt.TRACK_OPTS, **(o or {})}
    def build():
        P = _profiles(site, x, crop, o)
        P.pop("S")                                       # weather state is cheap to rebuild and large to store
        return P
    P = simstore.get_or_compute("profiles", (site, x, crop, oo), build)
    return {**P, "S": site_opt.site_state(site)}


def _profiles(site, x, crop, o=None):
    """o: site_opt options (R10: no_waste, hum_rh, hrd)."""
    o = {**site_opt.TRACK_OPTS, **(o or {})}
    S = site_opt.site_state(site)
    d, a, cfg, low, avail, waste_kw = site_opt.site_setup(site, x, crop, o)
    ts = site_opt.source_series(S, low, o)
    H, *_r, meta, _ = greenhouse_fast.simulate_fast(cfg, i_floor=a["I_floor"], waste_kw=waste_kw, t_source=ts)
    Hh, *_ = greenhouse_fast.simulate_fast(cfg, i_floor=a["I_floor"], waste_kw=None, t_source=ts)
    cop = offgrid.cop_profile(Hh["Q_c"][:8760], Hh["W_comp"][:8760])
    return dict(q=H["Q_pipe"][:8760], w_other=(H["W_total"] - H["W_comp"])[:8760], cop=cop, avail=avail,
                waste_kw=0.0 if low or o.get("no_waste") else site["heat_GWh"] * 1e6 / 8760, design_kw=meta["design_heat_loss_kw"],
                low=low, hp_kind=site_opt.hp_kind(low, o), d=d, S=S)


IO_API = os.environ.get("CEA_LP_IO", "direct")      # "direct": model passed to HiGHS in memory (no LP files); "lp" = old path


def solve(P, rule, price, pu, store_cost, elec=None, hp_min_el=0.0, store_min=0.0, boiler=False, store=True,
          import_cap_kw=None, design_kw=None, backup=None, pv=False):
    """elec: energy_grid.ELEC_OPTIONS key (default site_opt.CENTRAL_ELEC). Fixed turbine / PPA routes: the greenhouse
    takes wind up to the turbine's hourly output at the transfer price (turbine LCOE) or the PPA price; the surplus is
    the turbine owner's (as energy_grid.supply_option).
    boiler: add an electric peak boiler (site_opt.BOILER, DEA ch. 41) sized by the LP together with heat pump and store;
    rule 'standby' then means heat pump + boiler output at the design hour >= design heat load (BP19a).
    BP27 (2026-10-05): store=False removes the hot-water store (two-component plant: heat pump + boiler, or heat pump +
    store, never all three); import_cap_kw caps the grid import so the HV connection stays in a cheaper SPEN step
    (cashflow.hv_conn_gbp; the step is not in the LP, so callers enumerate caps); design_kw overrides the standby
    design load (e.g. the screened design load)."""
    design = P["design_kw"] if design_kw is None else design_kw
    elec = elec or site_opt.CENTRAL_ELEC
    O = energy_grid.ELEC_OPTIONS[elec]
    ann = offgrid.annuity
    q, cop = P["q"], P["cop"]
    cop_design = float(np.percentile(cop, 1))
    hp_kw_th_guess = P["design_kw"]
    hp_gbp_kwth = site_opt.hp_gbp_per_kw(hp_kw_th_guess / 1e3, P.get("hp_kind", "waste" if P["low"] else "air"))
    hp_cc = hp_gbp_kwth * cop_design * ann(site_opt.HP_LIFE) \
        + site_opt.DEA_OM_EUR_MW * site_opt.EUR_GBP / 1e3 * cop_design
    w_cc = energy_grid.WIND_CAPEX * (ann(offgrid.P["wind_life"][0]) + offgrid.P["wind_om_frac"][0])
    B = energy_grid.BATT
    n = pypsa.Network()
    n.set_snapshots(pd.RangeIndex(8760))
    for b in ("el", "heat", "wind", "battery"):
        n.add("Bus", b)
    n.add("Load", "heat_demand", bus="heat", p_set=q)
    n.add("Load", "aux", bus="el", p_set=P["w_other"])
    if P["waste_kw"] > 0:
        n.add("Generator", "waste", bus="heat", p_nom=P["waste_kw"], p_max_pu=P["avail"], marginal_cost=HEAT_PRICE)
    n.add("Link", "heat_pump", bus0="el", bus1="heat", efficiency=cop, p_nom_extendable=True, capital_cost=hp_cc,
          p_nom_min=design / cop_design if rule == "standby" and not boiler else hp_min_el)
    BO = site_opt.BOILER
    if boiler:
        b_gbp_kw = BO["meur_mw"] * 1e3 * site_opt.EUR_GBP
        n.add("Link", "boiler", bus0="el", bus1="heat", efficiency=BO["eff"], p_nom_extendable=True,
              capital_cost=(b_gbp_kw * ann(BO["life"]) + BO["om_eur_mw"] * site_opt.EUR_GBP / 1e3) * BO["eff"])
    if O["kind"] == "own_fixed":
        pu = P["S"]["pu80"]
        s_kw = O["kw"]
        cc_t = (s_kw * O["capex"] + O.get("conn", 0.0)) * ann(offgrid.P["wind_life"][0]) + s_kw * O["om_kw_yr"]
        n.add("Generator", "wind", bus="wind", p_nom=s_kw, p_max_pu=pu, marginal_cost=cc_t / float((s_kw * pu).sum()))
    elif O["kind"] == "ppa":
        pu = P["S"]["pu80"]
        s_kw = O["kw"] if "kw" in O else O["cap_x_peak"] * float((P["w_other"] + P["q"] / np.maximum(cop, 1.0)).max())
        n.add("Generator", "wind", bus="wind", p_nom=s_kw, p_max_pu=pu, marginal_cost=O["ppa"])
    elif O["kind"] == "grid":
        n.add("Generator", "wind", bus="wind", p_nom=0.0, p_max_pu=pu)
    else:                                                  # own-sized turbines (energy_grid.supply rule)
        if elec == "farm_share":                           # utility turbines: 80 m hub, as site_opt.evaluate
            pu = P["S"]["pu80"]
        if "capex" in O:
            w_cc = O["capex"] * (ann(offgrid.P["wind_life"][0]) + offgrid.P["wind_om_frac"][0])
        n.add("Generator", "wind", bus="wind", p_nom_extendable=True, p_max_pu=pu, capital_cost=w_cc)
    n.add("Link", "wind_to_load", bus0="wind", bus1="el", p_nom=1e7)
    eta = B["rte"][0] ** 0.5
    n.add("Store", "battery", bus="battery", e_nom_extendable=True, e_cyclic=True,
          capital_cost=B["capex_kwh"][0] * (ann(B["life"][0]) + B["om_frac"][0]))
    n.add("Link", "charge", bus0="wind", bus1="battery", p_nom_extendable=True, efficiency=eta,
          capital_cost=B["capex_kw"][0] * (ann(B["life"][0]) + B["om_frac"][0]))
    n.add("Link", "discharge", bus0="battery", bus1="el", p_nom=1e7, efficiency=eta)
    n.add("Generator", "grid", bus="el", p_nom=1e7 if import_cap_kw is None else import_cap_kw, marginal_cost=price)
    engines = backup.split("+") if backup else []        # "biomethane_chp+hvo": the LP sizes a CHP and a peaker together
    for b in engines:                                      # firm engine: fuel -> electricity (+ recovered heat for CHP)
        E = BACKUP[b]
        n.add("Bus", f"fuel_{b}")
        n.add("Generator", f"fuel_{b}", bus=f"fuel_{b}", p_nom=1e7, marginal_cost=E["fuel"])
        n.add("Link", f"engine_{b}", bus0=f"fuel_{b}", bus1="el", efficiency=E["eff_e"], bus2="heat",
              efficiency2=E["eff_h"], p_nom_extendable=True,
              capital_cost=(E["capex_kwe"] * ann(E["life"]) + E["fom_kwe"]) * E["eff_e"], marginal_cost=E["vom_kwhe"] * E["eff_e"])
    if pv:
        pv_pu = np.clip(P["S"]["wx"]["ghi"].to_numpy()[:8760] / 1000.0, 0, 1) * PV["pr"]
        n.add("Generator", "pv", bus="wind", p_nom_extendable=True, p_max_pu=pv_pu,
              capital_cost=PV["capex_kw"] * ann(PV["life"]) + PV["fom_kw"])
    n.add("Store", "heat_store", bus="heat", e_nom_extendable=True, e_cyclic=True, e_nom_min=store_min,
          e_nom_max=np.inf if store else 0.0,
          standing_loss=STORE["loss_day"] / 24,
          capital_cost=store_cost * ann(STORE["life"]) + STORE["om_eur_mwh"] * EUR15_EUR25 * site_opt.EUR_GBP / 1e3)
    extra = None
    if boiler and rule == "standby":
        def extra(net, snapshots):
            pn = net.model["Link-p_nom"]
            net.model.add_constraints(pn.loc["heat_pump"] * cop_design + pn.loc["boiler"] * BO["eff"] >= design,
                                      name="standby_capacity")
    status, cond = n.optimize(solver_name="highs", solver_options={"output_flag": False}, extra_functionality=extra,
                              io_api=IO_API)
    if status != "ok":
        raise Infeasible(f"LP {status}/{cond} (import cap {import_cap_kw}, store {store}, boiler {boiler})")
    g, L = n.generators_t.p, n.links_t
    wind_kw = float(n.generators.p_nom_opt["wind"]) if O["kind"] == "own_sized" else float(n.generators.p_nom["wind"])
    gen_avail = wind_kw * pu
    to_load = L.p0["wind_to_load"].to_numpy()
    charge = L.p0["charge"].to_numpy()
    exported = np.maximum(gen_avail - to_load - charge, 0.0)        # surplus after own load and battery
    imp = g["grid"].to_numpy()
    hp_el = L.p0["heat_pump"].to_numpy()
    res = dict(rule=rule, objective=float(n.objective), cop_design=cop_design,
               hp_kW_th=float(n.links.p_nom_opt["heat_pump"]) * cop_design,
               hp_kW_el=float(n.links.p_nom_opt["heat_pump"]), store_kWh=float(n.stores.e_nom_opt["heat_store"]),
               store_gbp_kwh=store_cost, wind_kW=wind_kw, batt_kWh=float(n.stores.e_nom_opt["battery"]),
               batt_kW=float(n.links.p_nom_opt["charge"]), import_MWh=float(imp.sum() / 1e3),
               import_peak_kW=float(imp.max()), export_MWh=float(exported.sum() / 1e3),
               waste_MWh=float(g["waste"].sum() / 1e3) if "waste" in g else 0.0, hp_heat_MWh=float(
                   (hp_el * cop).sum() / 1e3), hp_elec_MWh=float(hp_el.sum() / 1e3),
               used_wind_MWh=float((to_load.sum() + charge.sum()) / 1e3))
    res["elec"] = elec
    if engines:
        res["backup"], res["engines"] = backup, {}
        for b in engines:
            E = BACKUP[b]
            fuel = L.p0[f"engine_{b}"].to_numpy()
            kwe = float(n.links.p_nom_opt[f"engine_{b}"]) * E["eff_e"]
            res["engines"][b] = dict(kWe=kwe, MWh_e=float(fuel.sum() * E["eff_e"] / 1e3),
                                     heat_MWh=float(fuel.sum() * E["eff_h"] / 1e3), fuel_cost_gbp=float(fuel.sum() * E["fuel"]),
                                     capex_gbp=kwe * E["capex_kwe"],
                                     om_gbp=kwe * E["fom_kwe"] + float(fuel.sum()) * E["eff_e"] * E["vom_kwhe"],
                                     carbon_kg=float(fuel.sum() * E["ci_fuel"]), hours=int((fuel > 1.0).sum()))
        tot = {k: sum(e[k] for e in res["engines"].values()) for k in next(iter(res["engines"].values()))}
        res.update(engine_kWe=tot["kWe"], engine_MWh_e=tot["MWh_e"], engine_heat_MWh=tot["heat_MWh"],
                   fuel_cost_gbp=tot["fuel_cost_gbp"], engine_capex_gbp=tot["capex_gbp"], engine_om_gbp=tot["om_gbp"],
                   engine_carbon_kg=tot["carbon_kg"], engine_hours=max(e["hours"] for e in res["engines"].values()))
    if pv:
        res.update(pv_kW=float(n.generators.p_nom_opt["pv"]), pv_MWh=float(g["pv"].sum() / 1e3),
                   pv_capex_gbp=float(n.generators.p_nom_opt["pv"]) * PV["capex_kw"],
                   pv_om_gbp=float(n.generators.p_nom_opt["pv"]) * PV["fom_kw"])
    if boiler:
        b_el = L.p0["boiler"].to_numpy()
        res.update(boiler_kW_th=float(n.links.p_nom_opt["boiler"]) * BO["eff"], boiler_MWh=float(b_el.sum() * BO["eff"] / 1e3),
                   boiler_capex_gbp=float(n.links.p_nom_opt["boiler"]) * BO["eff"] * b_gbp_kw, boiler_kW_el=float(n.links.p_nom_opt["boiler"]))
        res["hp_heat_MWh"] = float((hp_el * cop).sum() / 1e3)
    # cost breakdown for the cash flow (cashflow.py): capital by item and the annual energy spend
    res["hp_capex_gbp"] = res["hp_kW_th"] * hp_gbp_kwth
    res["store_capex_gbp"] = res["store_kWh"] * store_cost
    res["batt_capex_gbp"] = res["batt_kWh"] * B["capex_kwh"][0] + res["batt_kW"] * B["capex_kw"][0]
    res["grid_cost_gbp"] = float(imp @ price)
    res["wind_cost_gbp"] = float(g["wind"].to_numpy().sum() * n.generators.at["wind", "marginal_cost"])         if O["kind"] in ("own_fixed", "ppa") else float(n.generators.p_nom_opt["wind"]) * w_cc
    # export earns SEG only for own-sized turbines; for the fixed turbine / PPA the surplus belongs to the turbine owner
    res["export_credit_gbp"] = res["export_MWh"] * 1e3 * energy_grid.SEG if O["kind"] == "own_sized" else 0.0
    res["net_gbp"] = 0.0 if import_cap_kw == 0 else site_opt.network_inc_gbp(res["import_peak_kW"])
    res["annual_gbp"] = res["objective"] - res["export_credit_gbp"] + res["net_gbp"]
    res["carbon_kg"] = float(imp @ CI) + res["used_wind_MWh"] * 1e3 * energy_grid.WIND_CI \
        + res["batt_kWh"] * B["co2_kwh"][0] / B["life"][0] + res.get("engine_carbon_kg", 0.0)
    return res


class Infeasible(RuntimeError):
    pass


def run(site, x, crop, row, price, rule, store_kwh0=None, o=None, boiler=False, elec=None, **plant):
    """plant (BP27): store (bool), import_cap_kw, screen_design (bool: standby design load with the roof screen shut).
    The cached solve is keyed on the values it reads (hourly profiles incl. the 2010 check, wind, prices, carbon
    intensity, plant cost constants), not on the cost ledger in `row`; the GBP/kg and kg CO2e/kg roll-up on `row` is
    applied afterwards, so cost-only edits reuse the solve (2026-10-05)."""
    import coldyear
    import simstore
    elec_key = elec or site_opt.CENTRAL_ELEC
    P = profiles(site, x, crop, o)
    vals = dict(P={k: v for k, v in P.items() if k not in ("S", "d")}, pu=P["S"]["pu"], pu80=P["S"]["pu80"], price=price,
                ci=CI, rule=rule, store_kwh0=store_kwh0, boiler=boiler, elec=energy_grid.ELEC_OPTIONS[elec_key], plant=plant,
                const=dict(dea=site_opt.DEA, om=site_opt.DEA_OM_EUR_MW, life=site_opt.HP_LIFE, boiler=site_opt.BOILER,
                           eur=site_opt.EUR_GBP, net=site_opt.NET_INC, store=STORE, eur15=EUR15_EUR25))
    if elec_key == "farm_share":
        vals["hub"] = 80                                   # 2026-10-06: farm_share solves were on the 45 m profile
    if rule == "lp":
        P10 = profiles(coldyear.alias(site, 2010), x, crop, o)
        vals["P10"] = {k: v for k, v in P10.items() if k not in ("S", "d")}
    if plant.get("screen_design"):
        vals["screen_kw"] = site_opt.site_setup(site, x, crop, o)[2].design_heat_loss_w(screen=True) / 1e3
    r = dict(simstore.get_or_compute("lp", (vals,), lambda: _run(site, x, crop, price, rule, store_kwh0, o, boiler, elec,
                                                                 **plant)))
    A, Y = P["d"].floor, row["Y"]
    sweep_energy = row["en_cost_gbp"] + row["hp_ann_gbp"] + row["net_gbp_yr"] + row["heat_MWh_per_kg"] * 10.0 * Y * A
    sweep_gbp_kg = row["gbp_kg_ex_heat"] + row["heat_MWh_per_kg"] * 10.0
    r["gbp_kg"] = sweep_gbp_kg + (r["annual_gbp"] - sweep_energy) / (A * Y)
    r["sweep_gbp_kg"] = sweep_gbp_kg
    r["kg_kg"] = row["kg_kg"] + (r["carbon_kg"] - row["elec_ci"] * row["elec_kWh_m2"] * A) / (A * Y)
    return r


def _run(site, x, crop, price, rule, store_kwh0=None, o=None, boiler=False, elec=None, store=True,
         import_cap_kw=None, screen_design=False, backup=None, pv=False):
    """rule 'lp': the LP sizes heat pump and store on 2023, then the pair is checked on the 2010 heat demand (coldest
    recent year, coldyear.py); if 2010 leaves heat unmet the heat pump is floored at the 2010 requirement with that
    store and the LP re-solved (R10, 2026-10-03: the 2023-only sizing left 76-444 h unmet in 2010)."""
    P = profiles(site, x, crop, o)
    pu = P["S"]["pu"]
    design = P["design_kw"]
    if screen_design:
        cfg = site_opt.site_setup(site, x, crop, o)[2]
        design = cfg.design_heat_loss_w(screen=True) / 1e3
    plant = dict(store=store, import_cap_kw=import_cap_kw, design_kw=design, backup=backup, pv=pv)
    sc = store_gbp_kwh(store_kwh0 if store_kwh0 else P["design_kw"] * 6)
    floor = dict(hp_min_el=0.0, store_min=0.0)
    for _ in range(3 if store else 1):
        r = solve(P, rule, price, pu, sc, boiler=boiler, elec=elec, **floor, **plant)
        new = store_gbp_kwh(max(r["store_kWh"], 1.0))
        if abs(new - sc) / sc < 0.05:
            break
        sc = new
    if rule == "lp" and not boiler:
        import coldyear
        P10 = profiles(coldyear.alias(site, 2010), x, crop, o)
        q10 = np.maximum(P10["q"] - (P10["waste_kw"] * P10["avail"] if P10["waste_kw"] else 0.0), 0.0)
        un, hrs = coldyear.store_check(q10, P10["cop"], r["hp_kW_el"], r["store_kWh"])
        r["unmet_2010_kWh_first"], r["unmet_2010_h_first"] = un, hrs
        r["hp_frac_2023_only"] = r["hp_kW_th"] / P["design_kw"]
        if un > 0:
            f = coldyear.min_frac(q10, P10["cop"], r["store_kWh"], P["design_kw"], r["cop_design"])
            floor = dict(hp_min_el=f * P["design_kw"] / r["cop_design"], store_min=r["store_kWh"])
            r2 = solve(P, rule, price, pu, sc, elec=elec, **floor, **plant)
            for k in ("unmet_2010_kWh_first", "unmet_2010_h_first", "hp_frac_2023_only"):
                r2[k] = r[k]
            r = r2
        r["unmet_2010_kWh"], r["unmet_2010_h"] = coldyear.store_check(q10, P10["cop"], r["hp_kW_el"], r["store_kWh"])
    if rule == "lp" and boiler:                           # BP19i: report-only check, the LP boiler is not re-sized on 2010
        import coldyear
        P10 = profiles(coldyear.alias(site, 2010), x, crop, o)
        q10 = np.maximum(P10["q"] - (P10["waste_kw"] * P10["avail"] if P10["waste_kw"] else 0.0), 0.0)
        r["unmet_2010_kWh"], r["unmet_2010_h"] = coldyear.store_check(q10, P10["cop"], r["hp_kW_el"], r["store_kWh"],
                                                                      r.get("boiler_kW_th", 0.0))
    r["design_kW"] = P["design_kw"]
    r["standby_design_kW"] = design
    r["plant"] = dict(store=store, boiler=boiler, import_cap_kw=import_cap_kw, screen_design=screen_design, backup=backup, pv=pv)
    return r


CI = None


def _job(args):
    global CI
    site, s, crop, rule, kwh0 = args
    _, price, CI = energy_grid.inputs()
    return site["site_key"], crop, rule, run(site, s["best"]["x"], crop, s["best"], price, rule, kwh0)


def main(crops, workers=6):   # 6 on the 32 GB / 6-core desktop (12 LPs in two waves); use 2 on the 8 GB laptop
    """All finalists x rules x crops in parallel (each LP ~1.3 GB RAM and one core; on this 4-core laptop the 2026-10-03 run with 3 workers + IPM took 50 min vs 36 min sequential with simplex: use workers = physical cores - 1 on a bigger machine)."""
    t = time.time()
    SL = {s["site_key"]: s for s in json.loads((HERE / "data" / "siting" / "shortlist.json").read_text())}
    prev = {}
    for f in site_opt.OUT.glob("lp*/lp_*.json"):         # warm start for the store cost
        for s in json.loads(f.read_text())["sites"]:
            for rule in ("standby", "lp"):
                prev[(f.stem[3:], s["site"], rule)] = s[rule]["store_kWh"]
    R = {c: json.loads((site_opt.OUT / f"refined_{c}.json").read_text()) for c in crops}
    jobs = [(SL[s["site"]], s, c, rule, prev.get((c, s["site"], rule))) for c in crops
            for s in R[c]["sites"][:FINALISTS] for rule in ("standby", "lp")]
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(_job, jobs))
    for c in crops:
        res = []
        for s in R[c]["sites"][:FINALISTS]:
            rr = {rule: r for key, cc, rule, r in out if key == s["site"] and cc == c}
            res.append(dict(site=s["site"], name=s["name"], area_ha=s["best"]["area_ha"], **rr))
            for rule, r in rr.items():
                print(f"{c:<9}{s['name'][:30]:<31}{rule:<8} GBP/kg {r['gbp_kg']:.3f} (sweep {r['sweep_gbp_kg']:.3f}) "
                      f"kg {r['kg_kg']:.3f} | HP {r['hp_kW_th'] / 1e3:.2f} MWth (design {r['design_kW'] / 1e3:.2f}) "
                      f"store {r['store_kWh'] / 1e3:.1f} MWh at GBP {r['store_gbp_kwh']:.2f}/kWh, wind "
                      f"{r['wind_kW'] / 1e3:.2f} MW, batt {r['batt_kWh'] / 1e3:.2f} MWh, export {r['export_MWh']:.0f} "
                      f"MWh, waste {r['waste_MWh'] / 1e3:.1f} GWh, HP heat {r['hp_heat_MWh']:.0f} MWh", flush=True)
        (site_opt.OUT / f"lp_{c}.json").write_text(json.dumps(
            {"store": STORE, "eur15_eur25": EUR15_EUR25, "wholesale_share": energy_grid.WHOLESALE_SHARE[0],
             "sites": res}, indent=1, default=float))
    print(f"LP done: {time.time() - t:.0f} s")


if __name__ == "__main__":
    main(sys.argv[1:] or ["cucumber", "tomato"])
