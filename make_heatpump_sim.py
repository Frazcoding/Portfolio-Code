"""make_heatpump_sim.py
Annual (8760 h) two-stage R290 air-source heat pump simulation + viewer for Heat-Pump-Simulation.

Runs Heat-Pump-Simulation/annual_sim.py for each scenario (London, London Agile load-shifting,
Glasgow), writes viewer_data/*.json|.bin and results/*.csv.gz, and generates viewer.html.
    python make_heatpump_sim.py            # reuse results if present
    python make_heatpump_sim.py --force    # re-run the simulations
"""
import json
import sys
from pathlib import Path

from generate_frontends import load_project_module, write_viewer

BASE_DIR = Path(__file__).resolve().parent
PROJECT = BASE_DIR / "Heat-Pump-Simulation"
sys.path.insert(0, str(PROJECT))

TITLE = "Two-Stage R290 Air-Source Heat Pump"
SUBTITLE = "Inverter LP pair + HP scroll, flash economiser · 12-flat block · full-year 2023 simulation at 10-min control steps"

SOURCE = ("Annual model: CoolProp R290 cycle map (9,504 solves), 5R1C building, stratified stores, frost/defrost; "
          "ERA5 2023 weather, NESO carbon intensity, Octopus Agile prices")

REFR_RANGE = [-25, 100]


def scenario_cfg(key, sc):
    notes = {
        "london": "London 2023 with standard control: weather-compensated buffer charging, DHW priority with 47/55 °C hysteresis, "
                  "weekly 60 °C legionella cycle by immersion, reverse-cycle defrost triggered at 7 kg frost.",
        "london_agile": "Same plant with price-aware control that uses the building fabric as the store: +1 K room pre-heat and "
                        "+3 K buffer in the cheapest quartile of each day (when the spread is >30 %), coast 1 K and block the "
                        "compressor through the dearest hours unless comfort or the buffer falls too far.",
        "glasgow": "Glasgow 2023, 1960s block (2.4 kW/K) on 65 °C radiators. Higher lift, more frosting, and a capacity "
                   "shortfall that brings in the 18 kW backup elements on the coldest days.",
    }
    return {
        "badge": sc["badge"], "source": SOURCE, "note": notes[key],
        "ledgerTitle": "Power flows at cursor (hourly mean)",
        "cmds": [{"key": "f_lp", "label": "LP speed"}, {"key": "f_hp", "label": "HP speed"}, {"key": "fan", "label": "Fans"},
                 {"key": "on_frac", "label": "Run"}, {"key": "mode_dhw", "label": "DHW mode"}, {"key": "defrosts", "label": "Defrosts"}],
        "sensors": [
            {"key": "T_amb"}, {"key": "Q_c"}, {"key": "W_total"}, {"key": "cop"},
            {"key": "Pe"}, {"key": "Pi"}, {"key": "Pc"}, {"key": "T_dis_hp", "limit": 115},
            {"key": "T_room", "ref": 21.0}, {"key": "T_flow", "refKey": "T_flow_set"}, {"key": "T_tap", "lower": 45},
            {"key": "frost_kg"}, {"key": "price"}, {"key": "ci"},
        ],
        "ledger": [
            {"key": "Q_c", "label": "Condenser heat", "max": 70, "color": "#c2410c"},
            {"key": "Q_e", "label": "Ambient heat", "max": 60, "color": "#1d6fb8"},
            {"key": "W_comp", "label": "Compressors", "max": 35, "color": "#2f5bd3"},
            {"key": "W_fan", "label": "Fans", "max": 1.6, "color": "#64748b"},
            {"key": "W_backup", "label": "Backup elements", "max": 18, "color": "#b91c1c"},
            {"key": "Q_emit", "label": "Radiators", "max": 70, "color": "#b45309"},
            {"key": "dhw_energy", "label": "DHW at taps", "max": 40, "color": "#0e7490"},
            {"key": "Ex_prod", "label": "Product exergy", "max": 15, "color": "#15803d"},
        ],
        "chartDefault": ["T_amb", "Q_c", "cop", "T_room", "buf_T1", "price"],
        "legend": {"title": "Refrigerant / water temperature, °C", "gradient": "#1b2a6b 0%, #2b6cb0 24%, #3fa7a0 40%, #f08c2e 64%, #d7301f 100%",
                   "ticks": [{"pct": 0, "label": "−25"}, {"pct": 40, "label": "25"}, {"pct": 64, "label": "50"}, {"pct": 100, "label": "100"}]},
    }


def scene_cfg():
    flows = []
    for path, key, ck, scale in [("r_suction", "m_lp", "1_T", 0.025), ("r_lp_dis", "m_lp", "3_T", 0.025),
                                 ("r_hp_suc", "m_hp", "4_T", 0.02), ("r_vap_inj", "m_vap", "8_T", 0.04),
                                 ("r_hp_dis", "m_hp", "5_T", 0.02), ("r_liquid", "m_hp", "6_T", 0.01), ("r_lp_liq", "m_lp", "10_T", 0.01)]:
        flows.append({"path": path, "key": key, "colorKey": ck, "range": REFR_RANGE, "scale": scale, "spacing": 0.06, "radius": 0.009})
    for path, key, ck, scale, sp in [("w_flow", "W2_m", "W2_T", 0.9, 0.18), ("w_ret", "W1_m", "W1_T", 0.9, 0.18),
                                     ("h_flow", "Q_emit", "T_flow", 0.03, 0.2), ("h_ret", "Q_emit", "T_ret", 0.03, 0.2),
                                     ("dhw_charge", "mode_dhw", "dhw_T1", 0.012, 0.15), ("dhw_charge_ret", "mode_dhw", "dhw_T10", 0.012, 0.15),
                                     ("dhw_hot", "dhw_draw", "T_tap", 0.006, 0.15), ("dhw_cold", "dhw_draw", "T_mains", 0.006, 0.15)]:
        flows.append({"path": path, "key": key, "colorKey": ck, "range": REFR_RANGE, "scale": scale, "spacing": sp, "radius": 0.016})
    bindings = [
        {"type": "spin", "nodes": ["Fan_1_Rotor", "Fan_2_Rotor"], "key": "fan", "scale": 0.3, "axis": "y"},
        {"type": "opacity", "nodes": ["Coil_Frost"], "key": "frost_kg", "range": [0.3, 7.0], "min": 0.0, "max": 0.8},
        {"type": "color", "nodes": ["LP_Compressor_A", "LP_Compressor_B"], "key": "T_dis_lp", "range": [-10, 100], "mix": 0.35},
        {"type": "color", "nodes": ["HP_Compressor"], "key": "T_dis_hp", "range": [-10, 100], "mix": 0.4},
        {"type": "emissive", "nodes": ["Backup_Heater"], "key": "W_backup", "range": [0, 18], "color": "#ff5a1f", "intensity": 3},
    ]
    for j in range(1, 11):
        bindings.append({"type": "color", "nodes": [f"Buffer_Band_{j}"], "key": f"buf_T{j}", "range": REFR_RANGE, "mix": 1.0})
        bindings.append({"type": "color", "nodes": [f"DHW_Band_{j}"], "key": f"dhw_T{j}", "range": REFR_RANGE, "mix": 1.0})
    tags = [
        {"label": "Heat pump", "anchor": "Unit", "fmt": "{Q_c|1} kW · COP {cop|2}"},
        {"label": "Compressors", "anchor": "Comp", "fmt": "{f_lp|0}/{f_hp|0} Hz · {T_dis_hp|0} °C dis."},
        {"label": "Buffer 1 m³", "anchor": "Buffer", "fmt": "{buf_T1|1} / {buf_T10|1} °C"},
        {"label": "DHW 1 m³", "anchor": "DHW", "fmt": "{dhw_T1|1} °C · {dhw_soc|0} %"},
        {"label": "To building", "anchor": "HeatOut", "fmt": "{Q_emit|1} kW · room {T_room|1} °C"},
        {"label": "Grid", "anchor": "Panel", "fmt": "{price|1} p/kWh · {ci|0} g/kWh"},
        {"label": "Outdoor air", "anchor": "SP_A1", "fmt": "{T_amb|1} °C · {RH|0} % RH"},
        {"label": "Coil frost", "anchor": "SP_A2", "fmt": "{frost_kg|1} kg · UA {ua_frac|0} %", "alertKey": "frost_kg", "alertAbove": 5},
    ]
    return {"glb": "heatpump_rig.glb", "meta": "heatpump_rig_meta.json", "exposure": 1.0, "fov": 34,
            "camera": {"pos": [6.8, 5.6, 9.4], "target": [-0.3, 0.9, -0.2]}, "groundRadius": 30, "gridStep": 1,
            "bindings": bindings, "flows": flows, "tags": tags}


def generate(force=False):
    A = load_project_module(PROJECT / "annual_sim.py", "sim_heatpump_sim")
    out = []
    pm = None
    for key, sc in A.SCENARIOS.items():
        man = PROJECT / "viewer_data" / f"{key}.json"
        if force or not man.exists():
            pm = pm or A.build_map()
            R, _ = A.export(key, pm)
            info = R.write(PROJECT, scenario_cfg(key, sc))
            print(f"  {key}: {info['channels']} channels, {info['bytes'] / 1e6:.1f} MB")
        out.append({"key": key, "name": sc["name"], "badge": sc["badge"]})
    # check scene bindings against the exported channels
    chans = {c["key"] for c in json.loads((PROJECT / "viewer_data" / f"{out[0]['key']}.json").read_text(encoding="utf-8"))["channels"]}
    sc = scene_cfg()
    refs = {b["key"] for b in sc["bindings"]} | {f["key"] for f in sc["flows"]} | {f["colorKey"] for f in sc["flows"]}
    missing = refs - chans
    if missing:
        raise ValueError(f"scene references unknown channels: {sorted(missing)}")
    path = write_viewer(PROJECT, TITLE, SUBTITLE, out, sc)
    print(f"Generated {path}")


if __name__ == "__main__":
    generate(force="--force" in sys.argv)
