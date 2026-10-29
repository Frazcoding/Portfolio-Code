"""make_industrial_hthp.py
Annual (8760 h) industrial high-temperature heat pump simulations + viewer for High-Temp-Waste-Heat-Recovery.

Scenarios: dairy effluent -> 95 C hot water on n-butane and on R1234ze(Z); spray-dryer exhaust -> 2.7 bar
steam on R1233zd(E). Writes viewer_data/*.json|.bin, results/*.csv.gz and viewer.html.
    python make_industrial_hthp.py [--force]
"""
import json
import sys
from pathlib import Path

from generate_frontends import load_project_module, write_viewer

BASE_DIR = Path(__file__).resolve().parent
PROJECT = BASE_DIR / "High-Temp-Waste-Heat-Recovery"
sys.path.insert(0, str(PROJECT))

TITLE = "Industrial High-Temperature Heat Pumps"
SUBTITLE = "Dairy waste-heat recovery · screw HTHP with economiser and IHX · full-year 2023 at 15-min control steps"
SOURCE = ("Annual model: CoolProp cycle maps (two-zone condenser, economiser port, IHX), sump/store/boiler site model; "
          "ERA5 2023 Cheshire weather, NESO carbon intensity, 2023 industrial two-rate tariff")
RANGE = [20, 165]

NOTES = {
    "dairy_butane": "Effluent from a 100 m³ sump (fed by production and twice-daily CIP) is cooled from ~45 °C to ~31 °C while an "
                    "n-butane screw heat pump charges an 80 m³ stratified store at 95 °C. The gas boiler only trims delivery "
                    "when the store top falls below 95 °C.",
    "dairy_r1234zez": "Identical site and controls with the HFO R1234ze(Z): lower pressures, higher discharge temperature and "
                      "slightly better COP than butane at this lift — a like-for-like refrigerant comparison.",
    "steam_r1233": "A run-around coil in the spray-dryer exhaust heats a 30 m³ water loop; the R1233zd(E) heat pump evaporates "
                   "from it and boils deaerated feedwater to 2.7 bar(a) steam. Recovering heat cools the loop, so source "
                   "availability couples to dryer load. The boiler covers the remaining steam demand.",
}


def scenario_cfg(key, sc):
    steam = sc["kind"] == "steam"
    sensors = [{"key": "T_amb"}, {"key": "production"}, {"key": "Q_dem"}, {"key": "Q_hp"}, {"key": "W_hp"}, {"key": "cop"},
               {"key": "Pe"}, {"key": "Pc"}, {"key": "T_dis", "limit": 160 if steam else 125}, {"key": "Q_boiler"}]
    sensors += ([{"key": "T_loop"}, {"key": "steam_kgh"}] if steam else
                [{"key": "T_sump"}, {"key": "src_level", "lower": 15}, {"key": "T_deliv", "lower": 94}])
    return {
        "badge": sc["badge"], "source": SOURCE, "note": NOTES[key], "ledgerTitle": "Heat and power at cursor (hourly mean)",
        "cmds": [{"key": "cap", "label": "Capacity"}, {"key": "on_frac", "label": "Run"}, {"key": "econ_frac", "label": "Econ ratio"},
                 {"key": "production", "label": "Production"}, {"key": "hp_share", "label": "HP share"},
                 {"key": "tariff", "label": "Tariff"}],
        "sensors": sensors,
        "ledger": [{"key": "Q_dem", "label": "Process demand", "max": 1200},
                   {"key": "Q_hp", "label": "Heat pump", "max": 800, "color": "#c2410c"},
                   {"key": "Q_src", "label": "Waste heat in", "max": 600, "color": "#1d6fb8"},
                   {"key": "W_hp", "label": "Compressor", "max": 250, "color": "#2f5bd3"},
                   {"key": "Q_boiler", "label": "Gas boiler", "max": 1200, "color": "#b91c1c"},
                   {"key": "Ex_prod", "label": "Product exergy", "max": 250, "color": "#15803d"}],
        "chartDefault": ["production", "Q_hp", "Q_boiler", "cop", "T_loop" if steam else "T_sump", "co2_saved"],
        "legend": {"title": "Fluid temperature, °C",
                   "gradient": "#1b2a6b 0%, #2b6cb0 15%, #3fa7a0 30%, #f08c2e 60%, #d7301f 100%",
                   "ticks": [{"pct": 0, "label": "20"}, {"pct": 30, "label": "65"}, {"pct": 60, "label": "110"},
                             {"pct": 100, "label": "165"}]},
    }


def scene_cfg():
    D = {"gateKey": "layout", "gateMax": 0.5}
    St = {"gateKey": "layout", "gateMin": 0.5}
    flows = []
    for pref, gate in (("d", D), ("s", St)):
        for path, key, ck, scale, r in [("suction", "m_ref", "2_T", 0.4, 0.025), ("discharge", "m_ref", "5_T", 0.4, 0.02),
                                        ("hotgas", "m_ref", "5_T", 0.4, 0.02), ("liquid", "m_ref", "6_T", 0.25, 0.015),
                                        ("subcool", "m_ref", "6_T", 0.25, 0.012), ("econ_vap", "m_econ", "8_T", 0.6, 0.012),
                                        ("main_liq", "m_ref", "9_T", 0.25, 0.012), ("evap_feed", "m_ref", "11_T", 0.25, 0.012)]:
            flows.append(dict(gate, path=f"{pref}_{path}", key=key, colorKey=ck, range=RANGE, scale=scale, spacing=0.3, radius=r))
    flows += [dict(D, path="d_eff_in", key="on_frac", colorKey="S1_T", range=RANGE, scale=0.015, spacing=0.35, radius=0.03),
              dict(D, path="d_eff_out", key="on_frac", colorKey="S2_T", range=RANGE, scale=0.015, spacing=0.35, radius=0.03),
              dict(D, path="d_hw_flow", key="K2_m", colorKey="K2_T", range=RANGE, scale=0.3, spacing=0.4, radius=0.035),
              dict(D, path="d_hw_ret", key="K1_m", colorKey="K1_T", range=RANGE, scale=0.3, spacing=0.4, radius=0.035),
              dict(D, path="d_process", key="Q_dem", colorKey="T_deliv", range=RANGE, scale=0.002, spacing=0.4, radius=0.04),
              dict(St, path="s_loop_in", key="on_frac", colorKey="S1_T", range=RANGE, scale=0.015, spacing=0.35, radius=0.035),
              dict(St, path="s_loop_out", key="on_frac", colorKey="S2_T", range=RANGE, scale=0.015, spacing=0.35, radius=0.035),
              dict(St, path="s_steam", key="steam_kgh", colorKey="K2_T", range=RANGE, scale=0.004, spacing=0.3, radius=0.04),
              dict(St, path="s_header", key="steam_kgh", colorKey="K2_T", range=RANGE, scale=0.004, spacing=0.45, radius=0.05),
              dict(St, path="s_feedwater", key="steam_kgh", colorKey="K1_T", range=RANGE, scale=0.001, spacing=0.3, radius=0.02)]
    bindings = [
        {"type": "visible", "nodes": ["Dairy_*"], "key": "layout", "threshold": 0.5, "invert": True},
        {"type": "visible", "nodes": ["Steam_*"], "key": "layout", "threshold": 0.5},
        {"type": "color", "nodes": ["Dairy_Compressor", "Steam_Compressor"], "key": "T_dis", "range": [60, 165], "mix": 0.3},
        {"type": "scale", "nodes": ["Dairy_Sump_LevelFill"], "key": "src_level", "range": [0, 100], "axis": "y",
         "from": 0.02, "to": 1.0},
        {"type": "emissive", "nodes": ["Gas_Boiler"], "key": "Q_boiler", "range": [0, 1200], "color": "#ff7a2f", "intensity": 0.35},
    ]
    for j in range(1, 13):
        bindings.append({"type": "color", "nodes": [f"Dairy_Store_Band_{j}"], "key": f"st_T{j}", "range": RANGE, "mix": 1.0})
    tags = [
        {"label": "Screw HTHP", "anchor": "Comp", "fmt": "{cap|0} % · COP {cop|2} · {W_hp|0} kWe"},
        {"label": "Gas boiler", "anchor": "Boiler", "fmt": "{Q_boiler|0} kW top-up"},
        dict(D, label="Store 80 m³", anchor="Store", fmt="{T_deliv|1} °C · {store_soc|0} %"),
        dict(D, label="Effluent sump", anchor="Sump", fmt="{T_sump|1} °C · {src_level|0} m³"),
        dict(St, label="Dryer exhaust loop", anchor="Dryer", fmt="{T_loop|1} °C · {Q_recov|0} kW"),
        dict(St, label="Steam generator", anchor="SteamGen", fmt="{steam_kgh|0} kg/h · {Tc|1} °C cond."),
    ]
    return {"glb": "industrial_hthp.glb", "meta": "industrial_hthp_meta.json", "fov": 34,
            "camera": {"pos": [12.0, 10.5, 14.5], "target": [-0.5, 1.5, 0.0]}, "groundRadius": 40, "gridStep": 1,
            "bindings": bindings, "flows": flows, "tags": tags}


def generate(force=False):
    A = load_project_module(PROJECT / "annual_sim.py", "sim_industrial_hthp")
    out = []
    for key, sc in A.SCENARIOS.items():
        if force or not (PROJECT / "viewer_data" / f"{key}.json").exists():
            pm = A.build_map(key)
            R, _ = A.export(key, pm)
            info = R.write(PROJECT, scenario_cfg(key, sc))
            print(f"  {key}: {info['channels']} channels, {info['bytes'] / 1e6:.1f} MB")
        out.append({"key": key, "name": sc["name"], "badge": sc["badge"]})
    chans = set()
    for o in out:
        chans |= {c["key"] for c in json.loads((PROJECT / "viewer_data" / f"{o['key']}.json").read_text(encoding="utf-8"))["channels"]}
    sc = scene_cfg()
    refs = {b["key"] for b in sc["bindings"]} | {f["key"] for f in sc["flows"]} | {f["colorKey"] for f in sc["flows"]}
    if refs - chans:
        raise ValueError(f"scene references unknown channels: {sorted(refs - chans)}")
    print("Generated", write_viewer(PROJECT, TITLE, SUBTITLE, out, sc))


if __name__ == "__main__":
    generate(force="--force" in sys.argv)
