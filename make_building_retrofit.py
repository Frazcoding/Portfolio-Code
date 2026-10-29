"""make_building_retrofit.py
Annual (8760 h) commercial heat pump retrofit simulation + viewer for Building-Heatpump-Retrofit.

Four 40 kW R290 modules, 2 x 100 m3 thermal stores and a 60 kWe grid cap serving a 6,000 m2
Edinburgh office. Scenarios: price-aware TES, thermostatic TES, and direct (no TES, uncapped).
    python make_building_retrofit.py [--force]
"""
import json
import sys
from pathlib import Path

from generate_frontends import load_project_module, write_viewer

BASE_DIR = Path(__file__).resolve().parent
PROJECT = BASE_DIR / "Building-Heatpump-Retrofit"
sys.path.insert(0, str(PROJECT))

TITLE = "Commercial Heat Pump Retrofit under a 60 kWe Grid Cap"
SUBTITLE = "4 × 40 kW R290 cascade · 2 × 100 m³ thermal stores · 6,000 m² Edinburgh office · full-year 2023, 10-min control"
SOURCE = ("Annual model: CoolProp single-stage R290 module map, 5R1C building, 24-node stores, per-module frost/defrost, "
          "grid-capped dispatch; ERA5 2023 Edinburgh, NESO carbon, Agile prices")
RANGE = [-15, 75]
NOTES = {
    "tes_smart": "Stores are charged to 66 °C in the cheapest 55 % of each day's Agile prices and otherwise to the compensated "
                 "flow temperature + 8 K. Module staging and speed are chosen every 10 minutes so the whole heating plant "
                 "stays below the 60 kWe connection.",
    "tes_basic": "Same plant and cap with thermostatic charging (store recharged whenever its state of charge falls below 85 %).",
    "direct": "No thermal store: the cascade follows the building load through a 2 m³ buffer, a 120 kW electric boiler "
              "covers any shortfall, and no connection cap is applied — the counterfactual the stores were designed to avoid.",
}


def scenario_cfg(key, sc):
    return {
        "badge": sc["badge"], "source": SOURCE, "note": NOTES[key], "ledgerTitle": "Power at cursor (hourly mean)",
        "cmds": [{"key": "n_on", "label": "Modules on"}, {"key": "f_mod", "label": "Speed"}, {"key": "tes_soc", "label": "Store SOC"},
                 {"key": "cap_limited", "label": "Cap-limited"}, {"key": "occupied", "label": "Occupied"}, {"key": "price", "label": "Price"}],
        "sensors": [{"key": "T_amb"}, {"key": "Q_need"}, {"key": "Q_emit"}, {"key": "Q_hp"}, {"key": "W_total", "limit": 60.0},
                    {"key": "cop"}, {"key": "T_room", "ref": 21.0}, {"key": "T_flow", "refKey": "T_set_flow"}, {"key": "tesA_T1"},
                    {"key": "tesB_T12"}, {"key": "Te"}, {"key": "Pc"}, {"key": "T_dis"}, {"key": "price"}],
        "ledger": [{"key": "Q_need", "label": "Building need", "max": 300}, {"key": "Q_hp", "label": "Cascade heat", "max": 200, "color": "#c2410c"},
                   {"key": "Q_emit", "label": "Radiators", "max": 300, "color": "#b45309"},
                   {"key": "W_total", "label": "Plant electricity", "max": 60, "color": "#2f5bd3"},
                   {"key": "W_backup", "label": "Electric boiler", "max": 120, "color": "#b91c1c"},
                   {"key": "tes_loss", "label": "Store losses", "max": 6, "color": "#64748b"}],
        "chartDefault": ["T_amb", "Q_need", "Q_hp", "W_total", "tes_soc", "price"],
        "legend": {"title": "Water / refrigerant temperature, °C",
                   "gradient": "#1b2a6b 0%, #2b6cb0 18%, #3fa7a0 45%, #f08c2e 75%, #d7301f 100%",
                   "ticks": [{"pct": 0, "label": "−15"}, {"pct": 45, "label": "25"}, {"pct": 75, "label": "52"}, {"pct": 100, "label": "75"}]},
    }


def scene_cfg():
    bindings = []
    for j in range(1, 5):
        bindings.append({"type": "spin", "nodes": [f"Module_{j}_Fan_1", f"Module_{j}_Fan_2"], "key": f"mod{j}_run", "scale": 0.25, "axis": "y"})
    for j in range(1, 13):
        bindings.append({"type": "color", "nodes": [f"StoreA_Band_{j}"], "key": f"tesA_T{j}", "range": RANGE, "mix": 1.0})
        bindings.append({"type": "color", "nodes": [f"StoreB_Band_{j}"], "key": f"tesB_T{j}", "range": RANGE, "mix": 1.0})
    bindings.append({"type": "emissive", "nodes": ["Transformer_Kiosk"], "key": "over_cap", "range": [0, 60], "color": "#ff3b1f", "intensity": 1.2})
    flows = [
        {"path": "p_charge", "key": "W2_m", "colorKey": "W2_T", "range": RANGE, "scale": 0.25, "spacing": 0.5, "radius": 0.05},
        {"path": "p_return", "key": "W1_m", "colorKey": "W1_T", "range": RANGE, "scale": 0.25, "spacing": 0.5, "radius": 0.05},
        {"path": "p_series", "key": "W1_m", "colorKey": "tesA_T12", "range": RANGE, "scale": 0.25, "spacing": 0.5, "radius": 0.05},
        {"path": "p_discharge", "key": "Q_emit", "colorKey": "tesA_T1", "range": RANGE, "scale": 0.01, "spacing": 0.5, "radius": 0.05},
        {"path": "b_flow", "key": "Q_emit", "colorKey": "T_flow", "range": RANGE, "scale": 0.01, "spacing": 0.5, "radius": 0.05},
        {"path": "b_ret", "key": "Q_emit", "colorKey": "T_ret", "range": RANGE, "scale": 0.01, "spacing": 0.5, "radius": 0.05},
    ]
    tags = [
        {"label": "R290 cascade", "anchor": "Modules", "fmt": "{n_on|1} on · {Q_hp|0} kW · COP {cop|2}"},
        {"label": "Store A", "anchor": "StoreA", "fmt": "{tesA_T1|1} / {tesA_T12|1} °C"},
        {"label": "Store B", "anchor": "StoreB", "fmt": "{tesB_T1|1} / {tesB_T12|1} °C · SOC {tes_soc|0} %"},
        {"label": "Grid connection", "anchor": "Grid", "fmt": "{W_total|1} / 60 kWe", "alertKey": "over_cap", "alertAbove": 0.5},
        {"label": "Office", "anchor": "Building", "fmt": "{T_room|1} °C · {Q_emit|0} kW · {T_amb|1} °C out"},
    ]
    return {"glb": "retrofit_plant.glb", "meta": "retrofit_plant_meta.json", "fov": 32,
            "camera": {"pos": [44.0, 24.0, 24.0], "target": [12.0, 2.0, -1.0]}, "groundRadius": 90, "gridStep": 5, "grid": False,
            "bindings": bindings, "flows": flows, "tags": tags}


def generate(force=False):
    A = load_project_module(PROJECT / "annual_sim.py", "sim_building_retrofit")
    out = []
    pm = None
    for key, sc in A.SCENARIOS.items():
        if force or not (PROJECT / "viewer_data" / f"{key}.json").exists():
            pm = pm or A.build_map()
            R, _ = A.export(key, pm)
            info = R.write(PROJECT, scenario_cfg(key, sc))
            print(f"  {key}: {info['channels']} channels, {info['bytes'] / 1e6:.1f} MB")
        out.append({"key": key, "name": sc["name"], "badge": sc["badge"]})
    chans = {c["key"] for c in json.loads((PROJECT / "viewer_data" / f"{out[0]['key']}.json").read_text(encoding="utf-8"))["channels"]}
    sc = scene_cfg()
    refs = {b["key"] for b in sc["bindings"]} | {f["key"] for f in sc["flows"]} | {f["colorKey"] for f in sc["flows"]}
    if refs - chans:
        raise ValueError(f"scene references unknown channels: {sorted(refs - chans)}")
    print("Generated", write_viewer(PROJECT, TITLE, SUBTITLE, out, sc))


if __name__ == "__main__":
    generate(force="--force" in sys.argv)
