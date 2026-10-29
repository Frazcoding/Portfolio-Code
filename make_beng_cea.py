"""make_beng_cea.py
Annual dynamic greenhouse + two-stage R717 heat pump simulation and viewer for BEng-CEA-Heatpump.

Scenarios: air-, ground- and river-source heat pumps on the dynamic 2023 Chelmsford greenhouse model,
plus the BEng thesis' own calibrated results (2018) as a replay for comparison. The thesis notebooks and
data/outputs are not modified.
    python make_beng_cea.py [--force]
"""
import json
import sys
from pathlib import Path

from generate_frontends import load_project_module, write_viewer

BASE_DIR = Path(__file__).resolve().parent
PROJECT = BASE_DIR / "BEng-CEA-Heatpump"
sys.path.insert(0, str(PROJECT / "sim"))

TITLE = "Greenhouse Decarbonisation · Two-Stage Ammonia Heat Pump"
SUBTITLE = "20 × 20 m Venlo glasshouse, tomato crop, R717 open-intercooler heat pump · full-year 2023 at 10-min control"
SOURCE = ("Dynamic greenhouse (air/crop/floor/pipe nodes, humidity, screen, vents) + CoolProp R717 two-stage map; "
          "ERA5 2023 Chelmsford, NESO carbon, Agile prices")
RANGE = [-15, 80]
NOTES = {
    "air": "Ammonia air cooler outside the plant room; frost forms below about 5 °C in humid weather and is cleared by "
           "reverse-cycle defrost using heat from the 1.5 m³ buffer.",
    "ground": "Sixteen 120 m boreholes. Extraction draws the ground temperature down through the winter; it recovers "
              "over summer, coupling the heat pump's lift to the season.",
    "water": "River abstraction through a screened intake and plate exchanger. River temperature lags the 7-day mean "
             "air temperature, giving the highest winter source temperature.",
}


def scenario_cfg(key, sc):
    if key == "thesis":
        return {"badge": sc["badge"], "source": "BEng thesis calibrated_v2 outputs (static hourly heat load + cycle model), first 8,760 h of 2018",
                "note": "Replay of the thesis' own results. The thesis model holds the greenhouse at a fixed 18 °C; channels are "
                        "only those present in the thesis CSVs.",
                "sensors": [{"key": "T_amb"}, {"key": "Q_heat_demand"}, {"key": "cop_air"}, {"key": "cop_ground"}, {"key": "cop_water"},
                            {"key": "W_air"}, {"key": "W_ground"}, {"key": "W_water"}],
                "ledger": [{"key": "Q_heat_demand", "label": "Heat demand", "max": 160}, {"key": "W_air", "label": "Electric (air)", "max": 50},
                           {"key": "W_ground", "label": "Electric (ground)", "max": 50}, {"key": "W_water", "label": "Electric (water)", "max": 50}],
                "chartDefault": ["T_amb", "Q_heat_demand", "cop_air", "cop_ground", "cop_water"]}
    return {
        "badge": sc["badge"], "source": SOURCE, "note": NOTES[key], "ledgerTitle": "Greenhouse heat flows at cursor (hourly mean)",
        "cmds": [{"key": "vent", "label": "Vents"}, {"key": "screen", "label": "Screen"}, {"key": "f_lp", "label": "LP speed"},
                 {"key": "f_hp", "label": "HP speed"}, {"key": "on_frac", "label": "HP run"}, {"key": "buf_soc", "label": "Buffer"}],
        "sensors": [{"key": "T_amb"}, {"key": "ghi"}, {"key": "T_in", "ref": 18.0}, {"key": "RH_in", "limit": 90}, {"key": "VPD"},
                    {"key": "T_pipe"}, {"key": "Q_c"}, {"key": "cop"}, {"key": "T_src"}, {"key": "Pe"}, {"key": "Pi"}, {"key": "Pc"},
                    {"key": "T_dis_hp", "limit": 140}, {"key": "W_total"}],
        "ledger": [{"key": "Q_pipe", "label": "Pipe rails", "max": 150, "color": "#c2410c"},
                   {"key": "Q_sol", "label": "Solar gain", "max": 250, "color": "#e8ad00"},
                   {"key": "LE", "label": "Transpiration", "max": 120, "color": "#15803d"},
                   {"key": "Q_cover", "label": "Cover loss", "max": 150, "color": "#1d6fb8"},
                   {"key": "Q_vent", "label": "Ventilation", "max": 250, "color": "#64748b"},
                   {"key": "W_total", "label": "Electricity", "max": 60, "color": "#2f5bd3"}],
        "chartDefault": ["T_amb", "T_in", "RH_in", "Q_pipe", "cop", "vent"],
        "legend": {"title": "Fluid / pipe temperature, °C", "gradient": "#1b2a6b 0%, #2b6cb0 20%, #3fa7a0 40%, #f08c2e 70%, #d7301f 100%",
                   "ticks": [{"pct": 0, "label": "−15"}, {"pct": 40, "label": "23"}, {"pct": 70, "label": "52"}, {"pct": 100, "label": "80"}]},
    }


def scene_cfg():
    A = {"gateKey": "src_kind", "gateMax": 0.5}
    G = {"gateKey": "src_kind", "gateMin": 0.5, "gateMax": 1.5}
    W = {"gateKey": "src_kind", "gateMin": 1.5}
    flows = [
        {"path": "r_lp_dis", "key": "m_lp", "colorKey": "3_T", "range": RANGE, "scale": 0.02, "spacing": 0.25, "radius": 0.02},
        {"path": "r_hp_suc", "key": "m_hp", "colorKey": "4_T", "range": RANGE, "scale": 0.02, "spacing": 0.25, "radius": 0.02},
        {"path": "r_hp_dis", "key": "m_hp", "colorKey": "5_T", "range": RANGE, "scale": 0.02, "spacing": 0.25, "radius": 0.018},
        {"path": "r_liquid", "key": "m_hp", "colorKey": "6_T", "range": RANGE, "scale": 0.01, "spacing": 0.25, "radius": 0.014},
        {"path": "r_hp_liq", "key": "m_hp", "colorKey": "7_T", "range": RANGE, "scale": 0.01, "spacing": 0.25, "radius": 0.014},
        dict(A, path="air_suction", key="m_lp", colorKey="1_T", range=RANGE, scale=0.03, spacing=0.3, radius=0.03),
        dict(G, path="ground_loop", key="on_frac", colorKey="T_src", range=RANGE, scale=0.02, spacing=0.35, radius=0.03),
        dict(W, path="river_in", key="on_frac", colorKey="T_src", range=RANGE, scale=0.02, spacing=0.35, radius=0.04),
        {"path": "w_charge", "key": "W2_m", "colorKey": "W2_T", "range": RANGE, "scale": 0.6, "spacing": 0.3, "radius": 0.03},
        {"path": "h_flow", "key": "Q_pipe", "colorKey": "T_sup", "range": RANGE, "scale": 0.02, "spacing": 0.35, "radius": 0.03},
        {"path": "h_ret", "key": "Q_pipe", "colorKey": "T_pipe", "range": RANGE, "scale": 0.02, "spacing": 0.35, "radius": 0.03},
    ]
    bindings = [
        {"type": "rotate", "nodes": ["Vent_*"], "key": "vent", "range": [0, 100], "angles": [0, 32], "axis": "z"},
        {"type": "opacity", "nodes": ["Thermal_Screen"], "key": "screen", "range": [0, 100], "min": 0.0, "max": 0.85},
        {"type": "color", "nodes": ["Pipe_Rails"], "key": "T_pipe", "range": RANGE, "mix": 0.75},
        {"type": "visible", "nodes": ["Src_Air_*"], "key": "src_kind", "max": 0.5},
        {"type": "visible", "nodes": ["Src_Ground_*"], "key": "src_kind", "min": 0.5, "max": 1.5},
        {"type": "visible", "nodes": ["Src_Water_*"], "key": "src_kind", "min": 1.5},
        {"type": "spin", "nodes": ["Src_Air_Fan_*"], "key": "on_frac", "scale": 0.25, "axis": "y"},
        {"type": "color", "nodes": ["HP_Skid"], "key": "T_dis_hp", "range": [20, 150], "mix": 0.12},
    ]
    for j in range(1, 11):
        bindings.append({"type": "color", "nodes": [f"Buffer_Band_{j}"], "key": f"buf_T{j}", "range": RANGE, "mix": 1.0})
    tags = [
        {"label": "Greenhouse climate", "anchor": "Climate", "fmt": "{T_in|1} °C · {RH_in|0} % RH · vents {vent|0} %"},
        {"label": "Pipe rails", "anchor": "Pipes", "fmt": "{T_pipe|1} °C · {Q_pipe|0} kW"},
        {"label": "R717 heat pump", "anchor": "HP", "fmt": "{Q_c|0} kW · COP {cop|2} · {T_dis_hp|0} °C dis."},
        {"label": "Buffer 1.5 m³", "anchor": "Buffer", "fmt": "{buf_T1|1} / {buf_T10|1} °C"},
        {"label": "Heat source", "anchor": "Source", "fmt": "{T_src|1} °C · ground/river {T_ground|1} °C"},
        {"label": "Energy screen", "anchor": "Screen", "fmt": "{screen|0} % closed"},
    ]
    return {"glb": "greenhouse.glb", "meta": "greenhouse_meta.json", "fov": 32,
            "camera": {"pos": [34.0, 18.0, 30.0], "target": [3.0, 2.5, 0.0]}, "groundRadius": 70,
            "bindings": bindings, "flows": flows, "tags": tags}


def generate(force=False):
    A = load_project_module(PROJECT / "sim" / "annual_sim.py", "sim_beng_cea")
    out = []
    for key, sc in A.SCENARIOS.items():
        if force or not (PROJECT / "viewer_data" / f"{key}.json").exists():
            if key == "thesis":
                R = A.export_thesis()
            else:
                R, _ = A.export(key, A.build_map(key))
            info = R.write(PROJECT, scenario_cfg(key, sc))
            print(f"  {key}: {info['channels']} channels, {info['bytes'] / 1e6:.1f} MB")
        out.append({"key": key, "name": sc["name"], "badge": sc["badge"]})
    chans = {c["key"] for c in json.loads((PROJECT / "viewer_data" / "air.json").read_text(encoding="utf-8"))["channels"]}
    sc = scene_cfg()
    refs = {b["key"] for b in sc["bindings"]} | {f["key"] for f in sc["flows"]} | {f["colorKey"] for f in sc["flows"]}
    if refs - chans:
        raise ValueError(f"scene references unknown channels: {sorted(refs - chans)}")
    print("Generated", write_viewer(PROJECT, TITLE, SUBTITLE, out, sc))


if __name__ == "__main__":
    generate(force="--force" in sys.argv)
