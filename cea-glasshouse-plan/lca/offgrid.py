"""Perthshire off-grid scenario, step 2: dedicated wind turbines, battery and a hot-water heat store sized by least
cost (PyPSA + HiGHS) for each crop's hourly demand. No grid connection, no export.

Buses: electricity and heat. The heat pump is a link electricity -> heat with the hourly COP from the simulation and
its installed electrical capacity (peak simulated draw x 1.1), so with the heat store it can run when it is windy.
Heat load = heat-pump output in the simulation; electricity load = fans, pumps, controls. Battery = store + charge /
discharge links (energy and power sized separately). Any shortfall is served by penalty generators (VoLL) and
reported; surplus wind is curtailed.

Wind: Carse of Gowrie 2023 100 m wind (Open-Meteo/ERA5) sheared to a 45 m hub (alpha 1/7), generic medium-turbine
power curve; "ridge" sensitivity scales wind speed by 1.15 (ERA5 smooths terrain). Turbine life-cycle carbon is
charged on everything it could generate, including curtailed output. Writes
results/perthshire/offgrid.json.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))           # repo copy of simcore first (cloud has no ../simcore)
sys.path.insert(0, str(HERE))
import breakeven  # noqa: E402
from simcore import weather  # noqa: E402

OUT = HERE / "results" / "perthshire"
AREA = 1.0e4
P = {  # value, unit, confidence, source
    "wind_capex": (2500.0, "GBP/kW", "sourced",
                   "SAC/SRUC (2026) CEA guide for the Highlands & Islands, Table 17: 250 kW turbine (40-45 m) "
                   "GBP 550-700k; 75 kW GBP 250k"),
    "wind_om_frac": (0.025, "1/yr", "estimated", ""),
    "wind_life": (20.0, "yr", "estimated", ""),
    "hub_m": (45.0, "m", "sourced", "SAC/SRUC guide Table 17: 250 kW turbine at 40-45 m"),
    "wind_ci": (0.011, "kg/kWh generated", "sourced", "IPCC AR5 WGIII Annex III onshore wind life-cycle median"),
    "battery_capex": (400.0, "GBP/kWh", "sourced", "DESNZ (2024) long-duration storage analysis: Li-ion GBP 400k/MWh"),
    "inverter_capex": (150.0, "GBP/kW", "estimated", "Battery inverter / power conversion"),
    "battery_life": (15.0, "yr", "estimated", ""),
    "battery_co2": (75.0, "kg CO2e/kWh capacity", "estimated", "Li-ion pack manufacturing, literature 60-100"),
    "heat_store_capex": (5.0, "GBP/kWh_th", "estimated",
                         "Large insulated hot-water tank, ~GBP 150/m3 at 30 K useful swing (~35 kWh/m3)"),
    "heat_store_life": (30.0, "yr", "estimated", ""),
    "heat_store_loss": (0.01, "1/day", "estimated", "Standing loss"),
    "voll_elec": (10.0, "GBP/kWh", "estimated", "Penalty for unserved electricity"),
    "voll_heat": (2.0, "GBP/kWh_th", "estimated", "Penalty for unserved heat"),
}


def annuity(life):
    r = breakeven.RATE
    return r / (1 - (1 + r) ** -life)


def wind_pu(scale=1.0):
    weather.SITES.setdefault("perth_carse", (56.42, -3.20, 0, "Carse of Gowrie, Perthshire, UK"))
    v = weather.load("perth_carse")["wind100"].to_numpy()[:8760] * (P["hub_m"][0] / 100.0) ** (1 / 7) * scale
    p = np.clip((v ** 3 - 3.0 ** 3) / (12.0 ** 3 - 3.0 ** 3), 0, 1)
    return np.where((v < 3.0) | (v > 25.0), 0.0, p)


def cop_profile(q, w):
    on = w > 0.02 * max(w.max(), 1e-12)
    cop = pd.Series(np.where(on, q / np.maximum(w, 1e-12), np.nan))
    return cop.interpolate(limit_direction="both").clip(1.5, 7.0).to_numpy()


def size(q_hp, w_hp, w_other, pu):
    cop = cop_profile(q_hp, w_hp)
    n = pypsa.Network()
    n.set_snapshots(pd.RangeIndex(8760))
    for b in ("el", "heat", "battery"):
        n.add("Bus", b)
    n.add("Load", "aux", bus="el", p_set=w_other)
    n.add("Load", "heat_demand", bus="heat", p_set=q_hp)
    n.add("Generator", "wind", bus="el", p_nom_extendable=True, p_max_pu=pu,
          capital_cost=P["wind_capex"][0] * (annuity(P["wind_life"][0]) + P["wind_om_frac"][0]))
    n.add("Link", "heat_pump", bus0="el", bus1="heat", p_nom=1.1 * w_hp.max(), efficiency=cop)
    n.add("Store", "battery", bus="battery", e_nom_extendable=True, e_cyclic=True,
          capital_cost=P["battery_capex"][0] * (annuity(P["battery_life"][0]) + 0.015))
    n.add("Link", "charge", bus0="el", bus1="battery", p_nom_extendable=True, efficiency=0.95,
          capital_cost=P["inverter_capex"][0] * annuity(P["battery_life"][0]))
    n.add("Link", "discharge", bus0="battery", bus1="el", p_nom_extendable=True, efficiency=0.95)
    n.add("Store", "heat_store", bus="heat", e_nom_extendable=True, e_cyclic=True,
          standing_loss=P["heat_store_loss"][0] / 24,
          capital_cost=P["heat_store_capex"][0] * annuity(P["heat_store_life"][0]))
    n.add("Generator", "unserved_el", bus="el", p_nom=1e6, marginal_cost=P["voll_elec"][0])
    n.add("Generator", "unserved_heat", bus="heat", p_nom=1e6, marginal_cost=P["voll_heat"][0])
    n.optimize(solver_name="highs", solver_options={"output_flag": False})
    g = n.generators_t.p
    wind_kw = float(n.generators.p_nom_opt["wind"])
    bat_kwh = float(n.stores.e_nom_opt["battery"])
    inv_kw = float(n.links.p_nom_opt["charge"])
    hs_kwh = float(n.stores.e_nom_opt["heat_store"])
    gen = float(g["wind"].sum())
    avail = wind_kw * float(pu.sum())          # turbine output before curtailment
    curtailed = avail - gen
    un_el, un_heat = float(g["unserved_el"].sum()), float(g["unserved_heat"].sum())
    hp_el = float(n.links_t.p0["heat_pump"].sum())
    elec_used = float(w_other.sum()) + hp_el - un_el
    capex_ann = (wind_kw * P["wind_capex"][0] * (annuity(P["wind_life"][0]) + P["wind_om_frac"][0])
                 + bat_kwh * P["battery_capex"][0] * (annuity(P["battery_life"][0]) + 0.015)
                 + inv_kw * P["inverter_capex"][0] * annuity(P["battery_life"][0])
                 + hs_kwh * P["heat_store_capex"][0] * annuity(P["heat_store_life"][0]))
    carbon = avail * P["wind_ci"][0] + bat_kwh * P["battery_co2"][0] / P["battery_life"][0]
    return {"wind_kW": wind_kw, "battery_kWh": bat_kwh, "inverter_kW": inv_kw, "heat_store_kWh": hs_kwh,
            "wind_MWh": avail / 1e3, "curtailed_share": curtailed / max(avail, 1e-9),
            "unserved_el_share": un_el / float(w_other.sum() + hp_el), "unserved_heat_share": un_heat / float(q_hp.sum()),
            "elec_used_MWh": elec_used / 1e3, "hp_elec_MWh": hp_el / 1e3, "capex_ann_gbp": capex_ann,
            "price": capex_ann / elec_used, "ci": carbon / elec_used, "cf": float(pu.mean())}


def _job(args):
    key, scale = args
    d = np.load(OUT / f"{key.replace('|', '__')}.npz")
    pu = wind_pu(scale)
    return key, scale, size(d["q_hp"] * AREA, d["w_hp"] * AREA, d["w_other"] * AREA, pu)


def main():
    keys = [f.stem.replace("__", "|") for f in sorted(OUT.glob("*.npz"))]
    out = {"inputs": {k: {"value": v[0], "unit": v[1], "confidence": v[2], "source": v[3]} for k, v in P.items()},
           "cf": {"base": float(wind_pu().mean()), "ridge": float(wind_pu(1.15).mean())}, "cases": {}}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for key, scale, res in ex.map(_job, [(k, s) for k in keys for s in (1.0, 1.15)]):
            out["cases"].setdefault(key, {})["base" if scale == 1.0 else "ridge"] = res
    (OUT / "offgrid.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"capacity factor: base {out['cf']['base']:.3f}, ridge {out['cf']['ridge']:.3f}")
    print(f"{'case':<22}{'wind kW':>8}{'bat kWh':>8}{'heat kWh':>9}{'curt':>6}{'unsrv':>7}{'£/kWh':>7}{'kg/kWh':>8}"
          f" | ridge {'kW':>6}{'£/kWh':>7}")
    for k, c in out["cases"].items():
        b, r = c["base"], c["ridge"]
        print(f"{k:<22}{b['wind_kW']:>8.0f}{b['battery_kWh']:>8.0f}{b['heat_store_kWh']:>9.0f}{b['curtailed_share']:>6.2f}"
              f"{max(b['unserved_el_share'], b['unserved_heat_share']):>7.3f}{b['price']:>7.3f}{b['ci']:>8.3f}"
              f" | {r['wind_kW']:>12.0f}{r['price']:>7.3f}")


if __name__ == "__main__":
    main()
