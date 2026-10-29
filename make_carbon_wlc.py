"""make_carbon_wlc.py
Whole-life carbon office: hourly operational year (London 2023) for each of the four scenarios plus the
60-year lifecycle comparison from the project engine (src/carbon_calculator.py). Writes viewer data + viewer.html.
    python make_carbon_wlc.py [--force]
"""
import json
import sys
from pathlib import Path

from generate_frontends import load_project_module, write_viewer

BASE_DIR = Path(__file__).resolve().parent
PROJECT = BASE_DIR / "Whole-Carbon-Lifecycle-Assessment"
sys.path.insert(0, str(PROJECT))

TITLE = "Whole-Life Carbon · 7,500 m² Office"
SUBTITLE = "Four futures for one building: hourly operation in 2023 and 60-year whole-life carbon (A1–C4)"
SOURCE = "Hourly 5R1C + CoolProp heat-pump map on ERA5 2023 London; lifecycle from the project WLC engine (ICE v3, DESNZ trajectories)"


def year_cfg(key, short):
    return {"badge": short, "source": SOURCE, "ledgerTitle": "Electricity at cursor (kW)",
            "note": f"{short}: fabric, airtightness, MVHR and plant from src/config.py; occupancy 08:00-18:00 weekdays; "
                    "MVHR summer bypass and night purge provide free cooling.",
            "cmds": [{"key": "occ", "label": "Occupied"}, {"key": "T_flow", "label": "Flow T"}, {"key": "cop_h", "label": "HP COP"},
                     {"key": "pv", "label": "PV"}, {"key": "ci", "label": "Grid CI"}, {"key": "price", "label": "Price"}],
            "sensors": [{"key": "T_amb"}, {"key": "T_room", "ref": 21.0}, {"key": "Q_heat"}, {"key": "Q_cool"}, {"key": "W_total"},
                        {"key": "gas"}, {"key": "pv"}, {"key": "grid_imp"}, {"key": "co2"}],
            "ledger": [{"key": "W_heat", "label": "Heating", "max": 150, "color": "#c2410c"}, {"key": "W_cool", "label": "Cooling", "max": 150, "color": "#1d6fb8"},
                       {"key": "W_light", "label": "Lighting", "max": 80}, {"key": "W_power", "label": "Small power", "max": 80},
                       {"key": "W_fans", "label": "Fans", "max": 40}, {"key": "pv", "label": "PV", "max": 140, "color": "#e8ad00"},
                       {"key": "gas", "label": "Gas", "max": 700, "color": "#b91c1c"}],
            "chartDefault": ["T_amb", "T_room", "Q_heat", "Q_cool", "W_total", "co2"]}


def life_cfg():
    return {"badge": "60-year WLC", "source": "Project WLC engine (src/carbon_calculator.py), DESNZ central grid trajectory 2026-2086",
            "note": "Cumulative carbon per scenario including upfront A1-A5 and annual refrigerant leakage; the KPI panel lists 60-year totals "
                    "including end of life. The 3D view shows the deep-retrofit option.",
            "sensors": [{"key": f"cum_s{j}"} for j in range(1, 5)] + [{"key": f"op_s{j}"} for j in range(1, 5)],
            "ledger": [{"key": f"cum_s{j}", "max": 11000, "color": c} for j, c in zip(range(1, 5), ("#b91c1c", "#15803d", "#64748b", "#b45309"))],
            "chartDefault": [f"cum_s{j}" for j in range(1, 5)] + ["op_s1", "op_s2"]}


def scene_cfg():
    bindings = [{"type": "visible", "nodes": [f"Var{j}_*"], "key": "scenario_idx", "min": j - 0.5, "max": j + 0.5} for j in range(1, 5)]
    bindings.append({"type": "emissive", "nodes": ["Interior_Glow"], "key": "lights_on", "range": [0, 1], "color": "#ffe7c2", "intensity": 1.4})
    Y = {"gateKey": "is_lifecycle", "gateMax": 0.5}
    L = {"gateKey": "is_lifecycle", "gateMin": 0.5}
    tags = [dict(Y, label="Office", anchor="Building", fmt="{T_room|1} °C · heat {Q_heat|0} kW · cool {Q_cool|0} kW"),
            dict(Y, label="Roof plant + PV", anchor="Roof", fmt="PV {pv|0} kW · HP {W_heat|0} kW · CO₂ {co2|0} kg/h"),
            dict(L, label="Cumulative carbon", anchor="Building", fmt="base {cum_s1|0} · retrofit {cum_s2|0} · new {cum_s3|0} · timber {cum_s4|0} t")]
    return {"glb": "wlc_office.glb", "meta": "wlc_office_meta.json", "fov": 32, "groundRadius": 120,
            "camera": {"pos": [62.0, 42.0, 70.0], "target": [0.0, 8.0, 0.0]}, "bindings": bindings, "flows": [], "tags": tags}


def generate(force=False):
    A = load_project_module(PROJECT / "annual_sim.py", "sim_carbon_wlc")
    SCENARIO_CONFIGS = A.SCENARIO_CONFIGS
    out = []
    maps = None
    for j, (key, cfg) in enumerate(SCENARIO_CONFIGS.items(), 1):
        k = f"{key}_year"
        if force or not (PROJECT / "viewer_data" / f"{k}.json").exists():
            maps = maps or {"R290": A.hp_map("R290"), "R32": A.hp_map("R32")}
            R, cfg, H = A.export_year(key, maps, j)
            R.write(PROJECT, year_cfg(key, cfg.short_name))
        out.append({"key": k, "name": f"{cfg.short_name} · operational year 2023 (hourly)", "badge": cfg.short_name})
    if force or not (PROJECT / "viewer_data" / "lifecycle.json").exists():
        A.export_lifecycle().write(PROJECT, life_cfg())
    out.append({"key": "lifecycle", "name": "60-year whole-life carbon · all four scenarios", "badge": "60-year WLC"})
    speeds = None
    print("Generated", write_viewer(PROJECT, TITLE, SUBTITLE, out, scene_cfg()))


if __name__ == "__main__":
    generate(force="--force" in sys.argv)
