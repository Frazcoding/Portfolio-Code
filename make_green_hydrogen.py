"""make_green_hydrogen.py
Annual island wind-hydrogen microgrid simulation (Isle of Lewis, ERA5 2023) + viewer.
Scenarios: base case, constrained 2 MW interconnector, and a half-size 4 MW electrolyser.
    python make_green_hydrogen.py [--force]
"""
import json
import sys
from pathlib import Path

from generate_frontends import load_project_module, write_viewer

BASE_DIR = Path(__file__).resolve().parent
PROJECT = BASE_DIR / "PyPsa-Green-Hydrogen-Microgrid"
sys.path.insert(0, str(PROJECT))

TITLE = "Island Wind–Hydrogen Microgrid"
SUBTITLE = "3 × 6.2 MW wind, PEM electrolysis, 350 bar storage and ferry bunkering · Stornoway, full year 2023"
SOURCE = ("Hourly model: ERA5 2023 100 m wind (sheared, density-corrected), electrochemical PEM polarisation + stack thermal model, "
          "CoolProp real-gas hydrogen compression and storage")
NOTES = {
    "base": "Wind serves the island first, then the electrolysers (10-100 % per stack), then export over the 5 MW cable; "
            "curtailment occurs when the store is full and the cable is saturated. The ferry bunkers each evening.",
    "weak_grid": "With only a 2 MW interconnector the island imports less and curtails much more; hydrogen output is unchanged "
                 "because production is already limited by store headroom and ferry demand.",
    "half_pem": "Halving the electrolyser raises its capacity factor and lowers LCOH, but meets less of the ferry's hydrogen demand.",
}


def scenario_cfg(key, sc):
    return {
        "badge": sc["badge"], "source": SOURCE, "note": NOTES[key], "ledgerTitle": "Power balance at cursor (MW)",
        "cmds": [{"key": "v_hub", "label": "Hub wind"}, {"key": "n_on", "label": "Stacks on"}, {"key": "j_mean", "label": "j"},
                 {"key": "store_P", "label": "Store P"}, {"key": "ferry_soc", "label": "Ferry tank"}, {"key": "cf", "label": "Wind CF"}],
        "sensors": [{"key": "v_hub"}, {"key": "P_wind"}, {"key": "demand"}, {"key": "P_ely"}, {"key": "h2_rate"}, {"key": "V_cell"},
                    {"key": "T_stack"}, {"key": "spec_e"}, {"key": "store_P", "limit": 352}, {"key": "store_kg"}, {"key": "export"},
                    {"key": "curtail"}, {"key": "unserved", "limit": 0.01}],
        "ledger": [{"key": "P_wind", "label": "Wind", "max": 19, "color": "#2f5bd3"}, {"key": "demand", "label": "Island", "max": 8},
                   {"key": "P_ely", "label": "Electrolysers", "max": 9, "color": "#15803d"},
                   {"key": "export", "label": "Export", "max": 5, "color": "#0e7490"},
                   {"key": "import_", "label": "Import", "max": 5, "color": "#b45309"},
                   {"key": "curtail", "label": "Curtailed", "max": 19, "color": "#64748b"}],
        "chartDefault": ["v_hub", "P_wind", "P_ely", "h2_rate", "store_P", "curtail"],
        "legend": {"title": "Hydrogen temperature, °C", "gradient": "#1b2a6b 0%, #2b6cb0 25%, #3fa7a0 45%, #f08c2e 75%, #d7301f 100%",
                   "ticks": [{"pct": 0, "label": "0"}, {"pct": 45, "label": "60"}, {"pct": 100, "label": "160"}]},
    }


def scene_cfg():
    rng = [0, 160]
    bindings, tags = [], []
    for k in range(1, 4):
        bindings.append({"type": "rotate", "nodes": [f"WTG_{k}_Yaw"], "key": "wdir", "range": [0, 360], "angles": [90, -270], "axis": "y"})
        bindings.append({"type": "spin", "nodes": [f"WTG_{k}_Rotor"], "key": f"rpm{k}", "scale": 0.1047, "axis": "y"})
        tags.append({"label": f"WTG {k} · 6.2 MW", "anchor": f"WTG{k}", "fmt": f"{{wtg{k}|2}} MW · {{rpm{k}|1}} rpm"})
    flows = [
        {"path": "h2_lp", "key": "h2_rate", "colorKey": "C2_T", "range": rng, "scale": 0.03, "spacing": 0.6, "radius": 0.07},
        {"path": "h2_hp", "key": "h2_rate", "colorKey": "C6_T", "range": rng, "scale": 0.03, "spacing": 0.6, "radius": 0.06},
        {"path": "h2_bunker", "key": "bunker", "colorKey": "C8_T", "range": rng, "scale": 0.004, "spacing": 0.6, "radius": 0.06},
        {"path": "bunker_hose", "key": "bunker", "colorKey": "C8_T", "range": rng, "scale": 0.004, "spacing": 0.5, "radius": 0.12},
    ]
    tags += [
        {"label": "PEM electrolysers", "anchor": "PEM2", "fmt": "{P_ely|2} MW · {h2_rate|0} kg/h · {V_cell|3} V"},
        {"label": "Compression", "anchor": "Compressor", "fmt": "{P_comp|3} MW · {C5_T|0} °C stage 2"},
        {"label": "H₂ store 188.5 m³", "anchor": "Store", "fmt": "{store_P|0} bar · {store_kg|0} kg"},
        {"label": "Grid / interconnector", "anchor": "Grid", "fmt": "exp {export|2} · imp {import_|2} · curt {curtail|2} MW"},
        {"label": "Ferry", "anchor": "Ferry", "fmt": "tank {ferry_soc|0} % · bunker {bunker|0} kg/h"},
    ]
    return {"glb": "hydrogen_microgrid.glb", "meta": "hydrogen_microgrid_meta.json", "fov": 34, "groundTex": "", "groundRadius": 600,
            "camera": {"pos": [-150.0, 95.0, 210.0], "target": [40.0, 45.0, -220.0]}, "bindings": bindings, "flows": flows, "tags": tags}


def generate(force=False):
    A = load_project_module(PROJECT / "annual_sim.py", "sim_green_hydrogen")
    out = []
    for key, sc in A.SCENARIOS.items():
        if force or not (PROJECT / "viewer_data" / f"{key}.json").exists():
            R, _ = A.export(key)
            info = R.write(PROJECT, scenario_cfg(key, sc))
            print(f"  {key}: {info['channels']} channels, {info['bytes'] / 1e6:.1f} MB")
        out.append({"key": key, "name": sc["name"], "badge": sc["badge"]})
    chans = {c["key"] for c in json.loads((PROJECT / "viewer_data" / "base.json").read_text(encoding="utf-8"))["channels"]}
    sc = scene_cfg()
    refs = {b["key"] for b in sc["bindings"]} | {f["key"] for f in sc["flows"]} | {f["colorKey"] for f in sc["flows"]}
    if refs - chans:
        raise ValueError(f"scene references unknown channels: {sorted(refs - chans)}")
    print("Generated", write_viewer(PROJECT, TITLE, SUBTITLE, out, sc))


if __name__ == "__main__":
    generate(force="--force" in sys.argv)
