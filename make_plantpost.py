"""make_plantpost.py
Annual Plantpost simulation (energy-water-ecosystem, 10-min internal steps) + viewer.
Scenarios: London, Edinburgh, Bologna (2023 ERA5) and Edinburgh with a doubled 200 Ah pack.
    python make_plantpost.py [--force]
"""
import json
import sys
from pathlib import Path

from generate_frontends import load_project_module, write_viewer

BASE_DIR = Path(__file__).resolve().parent
PROJECT = BASE_DIR / "Plantpost-Urban-Infrastructure-Modelling"
sys.path.insert(0, str(PROJECT))

TITLE = "Plantpost Autonomous Urban Infrastructure"
SUBTITLE = "4.5 m street post: PV canopy, LiFePO4 microgrid, rain-fed drip irrigation of four planted tiers · full year 2023"
SOURCE = "Annual model on src/config.py parameters (PV CAD-calibrated 258 kWh/yr London); ERA5 2023 weather incl. rain and FAO-56 ET₀"
NOTES = {
    "london": "London 2023. Adaptive dimming steps the luminaire to 70/50/30 % as the battery falls; summer surplus is curtailed.",
    "edinburgh": "Edinburgh 2023: long winter nights and low sun make lighting energy-limited from November to January.",
    "bologna": "Bologna 2023: high irradiance keeps the battery full, but hot summers drive the highest irrigation demand.",
    "edinburgh_200ah": "Edinburgh with a 200 Ah pack: doubling storage barely improves winter availability because the canopy "
                       "cannot harvest enough energy — the constraint is generation, not storage.",
}


def scenario_cfg(key, badge):
    return {
        "badge": badge, "source": SOURCE, "note": NOTES[key], "ledgerTitle": "Power at cursor (hourly mean, W)",
        "cmds": [{"key": "soc", "label": "SOC"}, {"key": "dim", "label": "Light level"}, {"key": "v_tank", "label": "Tank"},
                 {"key": "pump_on", "label": "Pump"}, {"key": "stress", "label": "Stress"}, {"key": "T_bat", "label": "Batt T"}],
        "sensors": [{"key": "T_amb"}, {"key": "ghi"}, {"key": "p_pv"}, {"key": "p_light"}, {"key": "soc", "lower": 25}, {"key": "v_bat"},
                    {"key": "i_bat"}, {"key": "T_bat"}, {"key": "v_tank", "lower": 10}, {"key": "rain"}, {"key": "theta4"}, {"key": "theta1"},
                    {"key": "N0_head"}, {"key": "unserved", "limit": 0.5}],
        "ledger": [{"key": "p_pv", "label": "PV", "max": 400, "color": "#e8ad00"}, {"key": "p_light", "label": "LED", "max": 50, "color": "#2f5bd3"},
                   {"key": "p_aux", "label": "BMS + IoT", "max": 5}, {"key": "p_pump", "label": "Pump", "max": 2},
                   {"key": "curtail", "label": "Curtailed", "max": 400, "color": "#64748b"},
                   {"key": "unserved", "label": "Unserved", "max": 50, "color": "#b91c1c"}],
        "chartDefault": ["ghi", "p_pv", "soc", "dim", "v_tank", "theta4"],
    }


def scene_cfg():
    bindings = [
        {"type": "emissive", "nodes": ["LED_Ring"], "key": "p_light", "range": [0, 47.1], "color": "#ffe2b0", "intensity": 6},
        {"type": "spotlight", "anchor": "LEDsrc", "key": "p_light", "range": [0, 47.1], "intensity": 140, "angle": 62, "distance": 16},
        {"type": "scale", "nodes": ["Tank_Level"], "key": "v_tank", "range": [0, 150], "axis": "y", "from": 0.02, "to": 1.0},
    ]
    for j in range(1, 5):
        bindings.append({"type": "color", "nodes": [f"Tier_{j}_Plants"], "key": f"theta{j}", "range": [12, 38], "ramp": "green", "mix": 0.55})
    flows = [{"path": "riser", "key": "pump_on", "colorKey": "T_amb", "range": [-5, 35], "scale": 0.08, "spacing": 0.08, "radius": 0.01}]
    tags = [
        {"label": "PV canopy", "anchor": "Canopy", "fmt": "{p_pv|0} W · SOC {soc|0} %"},
        {"label": "LED luminaire", "anchor": "LED", "fmt": "{p_light|1} W · {dim|0} %", "alertKey": "unserved", "alertAbove": 0.5},
        {"label": "Base: tank + battery", "anchor": "Base", "fmt": "{v_tank|0} L · {T_bat|1} °C cells"},
        {"label": "Tier 4", "anchor": "Tier4", "fmt": "{theta4|1} % vol · ET {et4|2} L/h"},
        {"label": "Tier 1", "anchor": "Tier1", "fmt": "{theta1|1} % vol · ET {et1|2} L/h"},
    ]
    return {"glb": "plantpost.glb", "meta": "plantpost_meta.json", "fov": 34, "groundTex": "paving", "groundColor": "#a59484",
            "groundTile": 1.2, "groundRadius": 20,
            "camera": {"pos": [7.6, 4.9, 9.4], "target": [0.0, 2.55, 0.0]}, "bindings": bindings, "flows": flows, "tags": tags}


def generate(force=False):
    A = load_project_module(PROJECT / "annual_sim.py", "sim_plantpost")
    out = []
    for key, (label, city, ci, cap) in A.CITIES.items():
        badge = label.replace(" 2023", "")
        if force or not (PROJECT / "viewer_data" / f"{key}.json").exists():
            R = A.export(key)
            info = R.write(PROJECT, scenario_cfg(key, badge))
            print(f"  {key}: {info['channels']} channels, {info['bytes'] / 1e6:.1f} MB")
        out.append({"key": key, "name": R.name if force else label, "badge": badge})
    chans = {c["key"] for c in json.loads((PROJECT / "viewer_data" / "london.json").read_text(encoding="utf-8"))["channels"]}
    sc = scene_cfg()
    refs = {b["key"] for b in sc["bindings"]} | {f["key"] for f in sc["flows"]} | {f["colorKey"] for f in sc["flows"]}
    if refs - chans:
        raise ValueError(f"scene references unknown channels: {sorted(refs - chans)}")
    print("Generated", write_viewer(PROJECT, TITLE, SUBTITLE, out, sc))


if __name__ == "__main__":
    generate(force="--force" in sys.argv)
