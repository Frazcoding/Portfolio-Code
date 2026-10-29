"""Grid-backed wind for the shape optimisation: fast hourly dispatch, turbine and battery size by sweep.

Per design's hourly electricity demand (kW): on-site wind serves the load first; surplus wind charges an optional
battery; only what is left after the greenhouse's own needs (heat pump, fans, pumps, controls, lighting) is exported
at the Smart Export Guarantee rate. When wind falls short the battery discharges, then the grid supplies the rest at
the hourly Agile shape scaled to the DESNZ non-domestic mean (breakeven.P['elec_price']). The battery charges from
our own wind only (no grid arbitrage): it pays only if storing surplus wind for later beats exporting it at SEG and
buying back at the grid price.

Sizing rule (user, 2026-10-03): wind and battery are sized for the greenhouse's own use. The least-cost (turbine,
battery) pair is chosen on capex + grid imports with export revenue left out, so export never drives the size;
the export earned by that system is then credited in the reported cost. size_for_export=True restores the old rule
(export revenue counted in the sizing), for comparison only.

Carbon: grid imports at the hourly NESO intensity; wind life-cycle carbon on the wind used on site (directly or via
the battery); exported wind's life-cycle carbon belongs to the grid user who buys it. Battery manufacture annualised
over its life.

Sources: wind capex SAC/SRUC (2026) Table 17 (250 kW at 40-45 m GBP 550-700k -> GBP 2,500/kW); SEG ~5.5 p/kWh
(SAC/SRUC 2026 Table 17); wind life-cycle carbon 11 g/kWh (IPCC AR5 WGIII Annex III); grid carbon DESNZ 2025 incl.
T&D and WTT, hourly NESO shape. Battery: see BATT.
"""
import sys
from pathlib import Path

import numpy as np
from numba import njit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))           # repo copy of simcore first (cloud has no ../simcore)
sys.path.insert(0, str(HERE))
import breakeven  # noqa: E402
import offgrid  # noqa: E402
from simcore import grid  # noqa: E402

WIND_CAPEX = 2500.0
SEG = 0.055
WIND_CI = 0.011
BATT = {  # value, unit, tier, source
    "capex_kwh": (400.0, "GBP/kWh", "sourced", "DESNZ (2024) long-duration storage analysis: Li-ion GBP 400k/MWh "
                  "(offgrid.P)"),
    "capex_kw": (150.0, "GBP/kW", "estimated", "battery inverter / power conversion (offgrid.P; to source)"),
    "rte": (0.85, "-", "sourced", "NREL Annual Technology Baseline 2024, utility-scale battery storage: 85 % "
            "round-trip efficiency"),
    "life": (15.0, "yr", "sourced", "NREL ATB 2024 utility-scale battery storage: 15-year life"),
    "om_frac": (0.025, "1/yr of capex", "sourced", "NREL ATB 2024: fixed O&M 2.5 % of capex per year"),
    "co2_kwh": (75.0, "kg CO2e/kWh", "sourced", "IVL Swedish Environmental Research Institute report C444 (2019), "
                "Li-ion production 61-106 kg CO2e/kWh; mid value"),
    "hours": (2.0, "h", "design choice", "energy/power ratio of the battery (2 h), typical commercial unit"),
}
BATT_SIZES_H = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)     # battery energy as hours of mean electricity demand


WHOLESALE_SHARE = (0.32, "sourced (secondary)",
                   "UtilityBidder (16 Apr 2026) 'UK business energy costs 2026', citing Drax spring 2026 figures: wholesale "
                   "~31-32 % of a low-voltage small business electricity bill, non-commodity (network, policy, CCL) "
                   "~68 %. A large HV-connected site likely has a higher share: 0.5 is run as a sensitivity")


def inputs(wholesale_share=None):
    """Hourly price: the wholesale share of the DESNZ non-domestic mean follows the Agile shape, the non-commodity
    rest (network, policy, levies) is flat. (Before 2026-10-03 the whole price followed the shape, which made the
    cheapest hours nearly free.)"""
    w = WHOLESALE_SHARE[0] if wholesale_share is None else wholesale_share
    gr = grid.load()
    price = gr.price.to_numpy()[:8760].astype(float)
    ci = gr.ci.to_numpy()[:8760].astype(float)
    mean = breakeven.P["elec_price"][0]
    price = mean * (1 - w) + np.maximum(price / price.mean() * mean * w, 0.0)
    ci = ci / ci.mean() * breakeven.SUPPLY["grid_2025"][0]
    return offgrid.wind_pu(1.0), price, ci


@njit(cache=True)
def _dispatch(load, gen, e_max, p_max, eta):
    """Hourly wind -> load -> battery -> export / grid. Returns import, export, battery discharge (kWh per hour)."""
    n = load.shape[0]
    imp = np.zeros(n)
    exp = np.zeros(n)
    dis = np.zeros(n)
    soc = 0.0
    e_c = eta ** 0.5                      # split round-trip loss equally between charge and discharge
    for i in range(n):
        net = gen[i] - load[i]
        if net >= 0.0:
            c = min(net, p_max, (e_max - soc) / e_c) if e_max > 0 else 0.0
            soc += c * e_c
            exp[i] = net - c
        else:
            d = min(-net, p_max, soc * e_c) if e_max > 0 else 0.0
            soc -= d / e_c
            dis[i] = d
            imp[i] = -net - d
    return imp, exp, dis


@njit(cache=True)
def _sweep(load, pu, price, sizes, e_opts, hours, eta, w_cc, b_cc, seg, for_export):
    """Objective of every (battery, turbine) pair, same dispatch as _dispatch without storing the hourly arrays."""
    obj = np.empty((e_opts.shape[0], sizes.shape[0]))
    e_c = eta ** 0.5
    for a in range(e_opts.shape[0]):
        e_max = e_opts[a]
        p_max = e_max / hours
        for b in range(sizes.shape[0]):
            soc = 0.0
            cost = 0.0
            ex = 0.0
            for i in range(load.shape[0]):
                net = sizes[b] * pu[i] - load[i]
                if net >= 0.0:
                    c = min(net, p_max, (e_max - soc) / e_c) if e_max > 0 else 0.0
                    soc += c * e_c
                    ex += net - c
                else:
                    d = min(-net, p_max, soc * e_c) if e_max > 0 else 0.0
                    soc -= d / e_c
                    cost += (-net - d) * price[i]
            obj[a, b] = sizes[b] * w_cc + b_cc[a] + cost - (ex * seg if for_export else 0.0)
    return obj


def supply(load_kw, pu, price, ci, wind_capex=WIND_CAPEX, battery=True, size_for_export=False, batt_capex=None):
    """Least-cost turbine and battery size for load_kw (8760 h); annual cost (GBP, export credited), carbon (kg)."""
    load_kw = np.ascontiguousarray(load_kw, dtype=float)
    w_cc = wind_capex * (offgrid.annuity(offgrid.P["wind_life"][0]) + offgrid.P["wind_om_frac"][0])
    ckwh = BATT["capex_kwh"][0] if batt_capex is None else batt_capex
    b_ann = offgrid.annuity(BATT["life"][0]) + BATT["om_frac"][0]
    eta, hours = BATT["rte"][0], BATT["hours"][0]
    sizes = np.linspace(0, 2.0 * load_kw.max(), 41)
    e_opts = [h * load_kw.mean() for h in (BATT_SIZES_H if battery else (0.0,))]
    e_arr = np.array(e_opts, float)
    b_cc_arr = (e_arr * ckwh + e_arr / hours * BATT["capex_kw"][0]) * b_ann
    obj = _sweep(load_kw, np.ascontiguousarray(pu, float), np.ascontiguousarray(price, float), sizes, e_arr, hours,
                 eta, w_cc, b_cc_arr, SEG, size_for_export)
    ia, ib = np.unravel_index(int(np.argmin(obj)), obj.shape)
    s, e, b_cc = float(sizes[ib]), float(e_arr[ia]), float(b_cc_arr[ia])
    p = e / hours
    imp, exp, dis = _dispatch(load_kw, s * pu, e, p, eta)
    cost = s * w_cc + b_cc + float(imp @ price) - float(exp.sum()) * SEG
    gen = s * pu
    used = float(gen.sum() - exp.sum())                   # wind used on site, directly or through the battery
    carbon = float(imp @ ci + used * WIND_CI + e * BATT["co2_kwh"][0] / BATT["life"][0])
    E = float(load_kw.sum())
    return dict(wind_kW=float(s), batt_kWh=float(e), batt_kW=float(p), cost_gbp=float(cost), carbon_kg=carbon,
                price=cost / E, ci=carbon / E, self_share=used / E,
                import_MWh=float(imp.sum() / 1e3), export_MWh=float(exp.sum() / 1e3),
                batt_MWh_out=float(dis.sum() / 1e3), export_credit_gbp=float(exp.sum() * SEG),
                batt_gbp_yr=float(b_cc), grid_only_price=float(load_kw @ price / E),
                import_peak_kW=float(imp.max()))


# ---- Electricity supply options (R10, user 2026-10-03: "how do we get cheaper wind?") -------------------------------
# Each option is a different contract / ownership route for the same hourly load. Prices are 2025-26 GBP.
ELEC_OPTIONS = {
    "grid": dict(kind="grid", label="Grid only (DESNZ mean, Agile wholesale shape)"),
    "own_small": dict(kind="own_sized", label="Owned turbine(s) sized for own use, 250 kW class (central case)"),
    "own_2p5MW": dict(kind="own_fixed", label="Owned single 2.5 MW turbine, surplus sold on a utility PPA",
                      kw=2500.0, capex=2240.0, om_kw_yr=19.5 * 1.08, export=0.060, conn=0.0,
                      src="capex: Kilbirnie 2.5 MW community turbine, North Ayrshire, GBP 5.6 M blended finance, commercial "
                          "operation Mar 2026 (Envirotec, 5 Mar 2026) -> GBP 2,240/kW; O&M Arup (2025) for DESNZ, Renewable "
                          "Energy Generation Cost and Technical Assumptions 2024, Table 18: GBP 19.5k/MW/a (2023 GBP, x1.08 to "
                          "2026); export: utility/merchant PPA for a sub-5 MW merchant turbine, GBP 60/MWh = 10-yr pay-as-"
                          "forecast fair value ~GBP 70/MWh (Veyt UK PPA 2025) less ~GBP 10 shape/balancing/route-to-market "
                          "discount (estimate); CfD AR7a onshore GBP 72.24/MWh (Feb 2026) as the ceiling. conn: 0 "
                          "(2026-10-05, BP27): Kilbirnie's own connection is inside its GBP 5.6 M, so the former unsourced "
                          "GBP 0.3 M 'site-difference margin' double-counted it; a dearer connection is the conn_high case. "
                          "Kilbirnie: finance Oct 2023 -> operation Mar 2026 (~2.5 yr)"),
    "tp_2p5MW": dict(kind="ppa", label="Third-party-owned 2.5 MW turbine on site, private-wire PPA for energy taken",
                     kw=2500.0, ppa=0.090,
                     src="Same turbine and site as own_2p5MW, owned and financed by a developer (no greenhouse capex). "
                         "Private-wire PPA GBP 80-120/MWh fully delivered (Savills 2025, 'Unlocking the power of private "
                         "wire'), GBP 90 as private_wire; the developer exports the surplus. Developer check in "
                         "bplan_5ha.py lean (revenue/MWh vs turbine LCOE at 8 %)"),
    "own_2p5MW_conn_high": dict(kind="own_fixed", label="2.5 MW turbine, 33 kV connection at the high end", kw=2500.0,
                                capex=2240.0, om_kw_yr=19.5 * 1.08, export=0.060, conn=1.0e6,
                                src="33 kV generator connections GBP 0.3-1.0 M (solargridcheck.co.uk G99 guide 2026, DNO "
                                    "averages); SSEN/SPEN high-cost project threshold GBP 200/kW"),
    "own_2p5MW_no_export": dict(kind="own_fixed", label="2.5 MW turbine behind the meter, export not allowed (no "
                                "connection offer): surplus curtailed, greenhouse carries the whole turbine",
                                kw=2500.0, capex=2240.0, om_kw_yr=19.5 * 1.08, export=0.0, conn=0.0, no_export=True,
                                src="risk case: Scottish connection queue (NESO connections reform, Ofgem approval 15 Apr "
                                    "2025; TIA needed for >= 200 kW in Scotland)"),
    "farm_share": dict(kind="own_sized", label="Owned share of a wind farm (utility-scale capex), private wire",
                       capex=1590.0 * 1.08, src="Arup (2025) for DESNZ, Tables 13/15/17: predevelopment 81 + construction "
                       "1,204 + infrastructure 303 = GBP 1,588/kW (2023 GBP), x1.08 to 2026. Needs a wind farm developer "
                       "willing to sell a share and a private wire (not costed)"),
    "private_wire": dict(kind="ppa", label="Private-wire PPA from an adjacent wind farm, pay for energy taken",
                         ppa=0.090, cap_x_peak=3.0,
                         src="UK private-wire PPA GBP 80-120/MWh fully delivered (Savills 2025, 'Unlocking the power of "
                             "private wire'); low end used (GBP 90) since the farm sells only its surplus over our load at "
                             "market; 6 UK on-site deals, 33.5 MW in 2025 (Pexapark 2025). Needs a farm within a few km"),
    "sleeved": dict(kind="sleeved", label="Sleeved corporate PPA over the grid (annual volume matched)",
                    ppa=0.070, fee=0.005, src="PPA ~GBP 70/MWh (Veyt UK PPA 2025: 10-yr PAF fair value GBP 69.9); "
                    "sleeving/balancing fee ~GBP 5/MWh (estimate). Replaces only the wholesale share; network and policy "
                    "charges are still paid. Location-based carbon unchanged (market-based reported separately)"),
}


def supply_option(load_kw, pu, price, ci, option, wholesale_share=None, battery=True):
    """Annual electricity cost and carbon of load_kw under one ELEC_OPTIONS route. Returns the supply() dict keys plus,
    for an owned fixed turbine, the turbine as a separate business (it sells to the greenhouse at its levelised cost
    and exports the rest), with simple payback and NPV at the study rate."""
    O = ELEC_OPTIONS[option]
    load_kw = np.ascontiguousarray(load_kw, dtype=float)
    E = float(load_kw.sum())
    if O["kind"] == "grid":
        return supply(load_kw, pu, price, ci, battery=False, wind_capex=1e9) | dict(option=option)
    if O["kind"] == "own_sized":
        return supply(load_kw, pu, price, ci, wind_capex=O.get("capex", WIND_CAPEX), battery=battery) | dict(option=option)
    if O["kind"] == "sleeved":
        w = WHOLESALE_SHARE[0] if wholesale_share is None else wholesale_share
        flat = price.mean() * (1 - w)                       # non-commodity part (flat in inputs())
        p2 = np.full_like(price, flat + O["ppa"] + O["fee"])
        r = supply(load_kw, pu, p2, ci, battery=False, wind_capex=1e9)
        return r | dict(option=option, ci_market=WIND_CI)
    b_ann = offgrid.annuity(BATT["life"][0]) + BATT["om_frac"][0]
    eta, hours = BATT["rte"][0], BATT["hours"][0]
    if O["kind"] == "own_fixed":
        s = O["kw"]
        cc = (s * O["capex"] + O.get("conn", 0.0)) * offgrid.annuity(offgrid.P["wind_life"][0]) + s * O["om_kw_yr"]
        p_wind = cc / max(float((s * pu).sum()), 1.0)      # levelised cost of the turbine's output (transfer price)
    else:                                                   # private-wire PPA: contracted capacity, pay for energy taken
        s = O["kw"] if "kw" in O else O["cap_x_peak"] * float(load_kw.max())
        p_wind = O["ppa"]
    best = None
    for h in (BATT_SIZES_H if battery else (0.0,)):
        e = h * load_kw.mean()
        imp, exp, dis = _dispatch(load_kw, s * pu, e, e / hours, eta)
        used = float((s * pu).sum() - exp.sum())
        b_cc = (e * BATT["capex_kwh"][0] + e / hours * BATT["capex_kw"][0]) * b_ann
        cost = float(imp @ price) + used * (0.0 if O.get("no_export") else p_wind) + b_cc
        if best is None or cost < best[0]:
            best = (cost, e, imp, exp, dis, used, b_cc)
    cost, e, imp, exp, dis, used, b_cc = best
    if O.get("no_export"):                                  # surplus curtailed: the greenhouse pays the whole turbine
        cost = cost + cc
        p_wind = cc / max(used, 1.0)
    carbon = float(imp @ ci + used * WIND_CI + e * BATT["co2_kwh"][0] / BATT["life"][0])
    r = dict(option=option, wind_kW=float(s), batt_kWh=float(e), batt_kW=float(e / hours), cost_gbp=cost,
             carbon_kg=carbon, price=cost / E, ci=carbon / E, self_share=used / E, import_MWh=float(imp.sum() / 1e3),
             export_MWh=float(exp.sum() / 1e3), batt_MWh_out=float(dis.sum() / 1e3), export_credit_gbp=0.0,
             batt_gbp_yr=float(b_cc), grid_only_price=float(load_kw @ price / E), import_peak_kW=float(imp.max()),
             wind_price=p_wind)
    if O["kind"] == "own_fixed":
        capex = s * O["capex"] + O.get("conn", 0.0)
        gen = float((s * pu).sum())
        # Turbine as its own business: it saves the greenhouse the grid price on the energy it supplies and sells the
        # surplus at the PPA price (the greenhouse cost above uses the transfer price = turbine LCOE instead)
        rev_avoided = float((load_kw - imp) @ price) + float(exp.sum()) * O["export"]
        om = s * O["om_kw_yr"]
        rr = breakeven.RATE
        n = offgrid.P["wind_life"][0]
        af = (1 - (1 + rr) ** -n) / rr
        r.update(turbine=dict(capex_gbp=capex, gen_MWh=gen / 1e3, cf=gen / (s * 8760), lcoe_gbp_mwh=p_wind * 1e3,
                              used_MWh=used / 1e3, export_MWh=float(exp.sum() / 1e3), export_price=O["export"],
                              om_gbp_yr=om, cash_at_avoided_gbp_yr=rev_avoided - om,
                              payback_yr_at_avoided=capex / max(rev_avoided - om, 1.0),
                              npv_at_avoided_gbp=(rev_avoided - om) * af - capex,
                              export_only_npv_gbp=(gen / 1e0 * O["export"] - om) * af - capex))
    return r
