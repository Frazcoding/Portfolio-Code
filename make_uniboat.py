"""make_uniboat.py
UniBoat electric hydrofoil: full 2023 season (hourly) and the 8 July race at 1 s resolution, with powertrain losses
and a pumped two-phase R1233zd(E) cooling loop. Writes viewer data and viewer.html.
    python make_uniboat.py [--force]
"""
import json
import sys
from pathlib import Path

from generate_frontends import load_project_module, write_viewer

BASE_DIR = Path(__file__).resolve().parent
PROJECT = BASE_DIR / "UniBoat-Powertrain-Cooling"
sys.path.insert(0, str(PROJECT))

TITLE = "UniBoat Electric Hydrofoil · Two-Phase Cooling"
SUBTITLE = "Monaco Energy Class catamaran, 10 kWh cap · pumped R1233zd(E) loop · 2023 season and race day"
SOURCE = ("Physics model: catamaran resistance + foil L/D, PMSM/SiC/battery loss models, CoolProp R1233zd(E) loop states; "
          "Open-Meteo marine 2023 sea temperature and waves at Monaco")


def scenario_cfg(key):
    note = ("Hourly season: sessions are integrated at 1 s and reported as session means (peaks in the Season group). The "
            "loop runs at T_sat = T_sea + 8 K; physics gives ~2.9 kW peak heat, well inside the 11.6 kW design rating."
            if key == "season" else
            "Sprint heats on 8 July at 1 s: 36 kt bursts draw ~36 kW DC; heat follows I²R, inverter and motor losses; "
            "the pump holds exit quality near 0.5.")
    return {
        "badge": "Season 2023" if key == "season" else "Race · 1 s", "source": SOURCE, "note": note,
        "ledgerTitle": "Heat loads at cursor (kW)",
        "cmds": [{"key": "v", "label": "Speed"}, {"key": "foil", "label": "Foil-borne"}, {"key": "soc", "label": "SOC"},
                 {"key": "Tsat", "label": "T_sat"}, {"key": "m_r", "label": "Ref. flow"}, {"key": "x5", "label": "Exit x"}],
        "sensors": [{"key": "v"}, {"key": "P_elec"}, {"key": "soc", "lower": 5}, {"key": "T_b", "limit": 45}, {"key": "T_i", "limit": 90},
                    {"key": "T_m", "limit": 120}, {"key": "Tsat"}, {"key": "1_P"}, {"key": "x5", "limit": 0.75}, {"key": "m_r"},
                    {"key": "W_pump"}],
        "ledger": [{"key": "Q_b", "label": "Battery", "max": 4, "color": "#2f5bd3"}, {"key": "Q_i", "label": "Inverter", "max": 1},
                   {"key": "Q_m", "label": "Motor", "max": 4, "color": "#c2410c"}, {"key": "Q_cond", "label": "Condenser", "max": 8, "color": "#0e7490"}],
        "chartDefault": ["v", "P_elec", "soc", "T_b", "Tsat", "x5"],
        "legend": {"title": "Refrigerant / component temperature, °C", "gradient": "#1b2a6b 0%, #3fa7a0 40%, #f08c2e 75%, #d7301f 100%",
                   "ticks": [{"pct": 0, "label": "15"}, {"pct": 40, "label": "29"}, {"pct": 100, "label": "50"}]},
    }


def scene_cfg():
    rng = [15, 50]
    bindings = [
        {"type": "translate", "nodes": ["Boat"], "key": "foil", "range": [0, 100], "axis": "y", "from": 0.0, "to": 0.95},
        {"type": "spin", "nodes": ["Propeller"], "key": "v", "scale": 1.2, "axis": "y"},
        {"type": "color", "nodes": ["Battery_Pack"], "key": "T_b", "range": rng, "mix": 0.6},
        {"type": "color", "nodes": ["Inverter"], "key": "T_i", "range": rng, "mix": 0.6},
        {"type": "color", "nodes": ["Motor"], "key": "T_m", "range": rng, "mix": 0.6},
    ]
    flows = [{"path": p, "key": "m_r", "colorKey": ck, "range": rng, "scale": 20.0, "spacing": 0.05, "radius": 0.012}
             for p, ck in (("r_pump_batt", "2_T"), ("r_batt_inv", "3_T"), ("r_inv_motor", "4_T"), ("r_motor_cond", "5_T"), ("r_cond_pump", "6_T"))]
    tags = [
        {"label": "UniBoat", "anchor": "BoatTag", "fmt": "{v|1} kt · {P_elec|1} kW · SOC {soc|0} %"},
        {"label": "Battery 10 kWh", "anchor": "Battery", "fmt": "{T_b|1} °C · {Q_b|2} kW heat"},
        {"label": "Motor", "anchor": "Motor", "fmt": "{T_m|1} °C · {Q_m|2} kW heat"},
        {"label": "Sea", "anchor": "Sea", "fmt": "{T_sea|1} °C · waves {wave_h|2} m"},
    ]
    return {"glb": "uniboat_cooling.glb", "meta": "uniboat_cooling_meta.json", "fov": 34, "groundTex": "", "groundRadius": 60,
            "camera": {"pos": [11.0, 5.5, 12.5], "target": [-0.6, 0.3, 0.0]}, "bindings": bindings, "flows": flows, "tags": tags}


def generate(force=False):
    A = load_project_module(PROJECT / "annual_sim.py", "sim_uniboat")
    out = [{"key": "season", "name": "Monaco 2023 · training season + race week (hourly)", "badge": "Season 2023"},
           {"key": "race", "name": "Monaco 8 July 2023 · sprint heats at 1 s", "badge": "Race · 1 s"}]
    if force or not (PROJECT / "viewer_data" / "season.json").exists():
        R, race, wx = A.export_season()
        R.write(PROJECT, scenario_cfg("season"))
        Rr = A.export_race(race, wx)
        Rr.write(PROJECT, scenario_cfg("race"))
        print("  season + race written")
    chans = {c["key"] for c in json.loads((PROJECT / "viewer_data" / "race.json").read_text(encoding="utf-8"))["channels"]}
    sc = scene_cfg()
    refs = {b["key"] for b in sc["bindings"]} | {f["key"] for f in sc["flows"]} | {f["colorKey"] for f in sc["flows"]}
    if refs - chans:
        raise ValueError(f"scene references unknown channels: {sorted(refs - chans)}")
    speeds = [(1, "1 s / s"), (10, "10 s / s"), (60, "1 min / s"), (3600, "1 h / s"), (86400, "1 day / s"), (7 * 86400, "1 week / s")]
    zooms = [(1, "Hour"), (24, "Day"), (168, "Week"), (0, "All")]
    print("Generated", write_viewer(PROJECT, TITLE, SUBTITLE, out, sc, speeds=speeds, zooms=zooms))


if __name__ == "__main__":
    generate(force="--force" in sys.argv)
