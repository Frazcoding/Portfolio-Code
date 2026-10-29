"""On-site wind + battery + grid for each crop's hourly electricity demand, sized by least-cost LP (PyPSA + HiGHS).

Per crop and system variant (results/profiles/*.npy from run_crops.py, kW/m2), for a 1 ha site:
  * wind: medium turbine(s) at 50 m hub, Chelmsford 2023 100 m wind (Open-Meteo/ERA5) sheared with alpha = 1/7,
    generic power curve (cut-in 3, rated 12, cut-out 25 m/s); capacity is continuous (several units in practice)
  * battery: Li-ion, 4 h, 90 % round trip
  * grid import at the hourly Agile shape scaled to the DESNZ non-domestic mean (17.3 p/kWh incl. CCL);
    hourly NESO carbon intensity shape scaled to the DESNZ 2025 factor (0.245 kg/kWh incl. T&D and WTT)
  * export of surplus wind at a flat price (estimate), carbon not credited

Wind sits on its own bus so only wind can be exported (grid power cannot be re-exported; Agile has negative-price
hours). Cases: "hybrid" (least cost, unlimited import), "wind80" (least cost with grid import <= 20 % of demand),
both with medium on-site turbine cost, and "hybrid_utility" (least cost at utility-scale turbine cost, i.e. a share
of a larger onshore project).
Cases already in results/energy_systems.json are kept unless run with --all. Writes results/energy_systems.json: per case the delivered cost (GBP/kWh) and carbon (kg/kWh) of electricity,
capacities and energy flows. compare.py feeds these into the comparison page.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pypsa

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))
from simcore import grid, weather  # noqa: E402

sys.path.insert(0, str(HERE))
import breakeven  # noqa: E402

AREA = 1.0e4
P = {  # value, unit, confidence, source
    "wind_capex": (3200.0, "GBP/kW", "estimated",
                   "Medium turbines 100-500 kW, UK project cost incl. tower, install and connection: 100 kW "
                   "GBP 350-450k, 250 kW GBP 700-900k, 500 kW GBP 1.5-2.0 M (Renewables First, accessed 2026). "
                   "Utility-scale onshore is GBP 1,241-1,588/kW (Arup 2024 for DESNZ) if bought via a PPA instead"),
    "wind_capex_utility": (1400.0, "GBP/kW", "sourced",
                           "Onshore wind capex GBP 1,241/kW (2023) to 1,588/kW (2025), Arup (2024) for DESNZ"),
    "wind_om_frac": (0.025, "1/yr", "estimated", "Annual O&M as fraction of capex"),
    "wind_life": (20.0, "yr", "estimated", "Typical turbine design life"),
    "wind_ci": (0.011, "kg/kWh", "sourced", "Onshore wind life cycle median, IPCC AR5 WGIII Annex III"),
    "hub_m": (50.0, "m", "estimated", "Medium turbine hub height"),
    "battery_capex": (400.0, "GBP/kWh", "sourced",
                      "Li-ion GBP 400,000/MWh (DESNZ long-duration electricity storage scenario analysis, 2024)"),
    "battery_life": (15.0, "yr", "estimated", ""),
    "battery_om_frac": (0.015, "1/yr", "estimated", ""),
    "export_price": (0.05, "GBP/kWh", "estimated", "Export / Smart Export Guarantee-type rate for surplus wind"),
    "import_price_mean": (breakeven.P["elec_price"][0], "GBP/kWh", "sourced", breakeven.P["elec_price"][3]),
    "grid_ci_mean": (breakeven.SUPPLY["grid_2025"][0], "kg/kWh", "sourced", breakeven.SUPPLY["grid_2025"][1]),
}


def annuity(life):
    r = breakeven.RATE
    return r / (1 - (1 + r) ** -life)


def power_curve(v):
    v = np.asarray(v, float)
    p = np.clip((v ** 3 - 3.0 ** 3) / (12.0 ** 3 - 3.0 ** 3), 0, 1)
    return np.where((v < 3.0) | (v > 25.0), 0.0, p)


def inputs():
    wx = weather.load("chelmsford")
    gr = grid.load()
    v = wx["wind100"].to_numpy() * (P["hub_m"][0] / 100.0) ** (1 / 7)
    pu = power_curve(v)[:8760]
    price = gr.price.to_numpy()[:8760]
    ci = gr.ci.to_numpy()[:8760]
    price = price / price.mean() * P["import_price_mean"][0]
    ci = ci / ci.mean() * P["grid_ci_mean"][0]
    return pu, price, ci


def size(demand_kw, pu, price, ci, import_cap=None, wind_capex=None):
    wind_capex = P["wind_capex"][0] if wind_capex is None else wind_capex
    w_cc = wind_capex * (annuity(P["wind_life"][0]) + P["wind_om_frac"][0])
    b_cc = 4.0 * P["battery_capex"][0] * (annuity(P["battery_life"][0]) + P["battery_om_frac"][0])
    n = pypsa.Network()
    n.set_snapshots(pd.RangeIndex(len(demand_kw)))
    n.add("Bus", "el")
    n.add("Bus", "wind_bus")
    n.add("Load", "greenhouse", bus="el", p_set=demand_kw)
    n.add("Generator", "wind", bus="wind_bus", p_nom_extendable=True, p_max_pu=pu, capital_cost=w_cc)
    n.add("Link", "wind_to_site", bus0="wind_bus", bus1="el", p_nom=1e6)
    n.add("Generator", "export", bus="wind_bus", p_nom=1e6, p_max_pu=0.0, p_min_pu=-1.0,
          marginal_cost=P["export_price"][0])
    n.add("Generator", "grid", bus="el", p_nom=1e6, marginal_cost=np.maximum(price, 0.0),
          e_sum_max=import_cap if import_cap is not None else np.inf)
    n.add("StorageUnit", "battery", bus="el", p_nom_extendable=True, max_hours=4.0, efficiency_store=0.95,
          efficiency_dispatch=0.95, capital_cost=b_cc)
    n.optimize(solver_name="highs", solver_options={"output_flag": False})
    g = n.generators_t.p
    E = float(demand_kw.sum())
    wind_gen, imp, exp = float(g["wind"].sum()), float(g["grid"].sum()), float(-g["export"].sum())
    wind_kw = float(n.generators.p_nom_opt["wind"])
    bat_kw = float(n.storage_units.p_nom_opt["battery"])
    cost = wind_kw * w_cc + bat_kw * b_cc + float((g["grid"] * price).sum()) - exp * P["export_price"][0]
    carbon = float((g["grid"] * ci).sum()) + (wind_gen - exp) * P["wind_ci"][0]
    return {"demand_MWh": E / 1e3, "wind_kW": wind_kw, "battery_kWh": bat_kw * 4, "wind_MWh": wind_gen / 1e3,
            "import_MWh": imp / 1e3, "export_MWh": exp / 1e3, "self_share": 1 - imp / E,
            "wind_cf": float(pu.mean()), "price": cost / E, "ci": carbon / E, "wind_capex": wind_capex,
            "grid_only_price": float((demand_kw * price).sum() / E), "grid_only_ci": float((demand_kw * ci).sum() / E)}


def _job(args):
    key, d, pu, price, ci = args
    return key, {"hybrid": size(d, pu, price, ci), "wind80": size(d, pu, price, ci, 0.2 * d.sum()),
                 "hybrid_utility": size(d, pu, price, ci, wind_capex=P["wind_capex_utility"][0])}


def main():
    pu, price, ci = inputs()
    path = HERE / "results" / "energy_systems.json"
    done = json.loads(path.read_text())["cases"] if path.exists() and "--all" not in sys.argv else {}
    out = {"inputs": {k: {"value": v[0], "unit": v[1], "confidence": v[2], "source": v[3]} for k, v in P.items()},
           "wind_cf": float(pu.mean()), "cases": done}
    jobs = []
    for f in sorted((HERE / "results" / "profiles").glob("*.npy")):
        key = f.stem.replace("__", "|")
        if key not in done:
            jobs.append((key, np.load(f).astype(float)[:8760] * AREA, pu, price, ci))
    with ProcessPoolExecutor(max_workers=6) as ex:
        for key, res in ex.map(_job, jobs):
            out["cases"][key] = res
    path.write_text(json.dumps(out, indent=1, default=float))
    print(f"wind capacity factor at {P['hub_m'][0]:.0f} m: {out['wind_cf']:.3f}")
    print(f"{'case':<24}{'grid p':>8}{'grid kg':>8} | {'hyb kW':>7}{'bat kWh':>8}{'self':>6}{'£/kWh':>7}{'kg':>7}"
          f" | {'w80 kW':>7}{'bat':>6}{'£/kWh':>7}{'kg':>7} | {'util kW':>7}{'self':>6}{'£/kWh':>7}{'kg':>7}")
    for k, c in out["cases"].items():
        h, w, u = c["hybrid"], c["wind80"], c["hybrid_utility"]
        print(f"{k:<24}{h['grid_only_price']:>8.3f}{h['grid_only_ci']:>8.3f} | {h['wind_kW']:>7.0f}{h['battery_kWh']:>8.0f}"
              f"{h['self_share']:>6.2f}{h['price']:>7.3f}{h['ci']:>7.3f} | {w['wind_kW']:>7.0f}{w['battery_kWh']:>6.0f}"
              f"{w['price']:>7.3f}{w['ci']:>7.3f} | {u['wind_kW']:>7.0f}{u['self_share']:>6.2f}{u['price']:>7.3f}{u['ci']:>7.3f}")


if __name__ == "__main__":
    main()
