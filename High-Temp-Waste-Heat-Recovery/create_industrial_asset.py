"""Industrial high-temperature heat pump plant room (dairy) with two alternative layouts.

  Dairy_*  : n-butane / R1234ze(Z) screw HTHP, effluent sump source, 95 C hot-water store
  Steam_*  : R1233zd(E) screw HTHP, spray-dryer exhaust recovery loop, kettle steam generator
Shared   : plant room slab, existing gas-fired shell boiler and flue, MCC/VFD, pipe rack.
The viewer shows one layout at a time (binding on the 'layout' channel).

Envelopes from the annual model: 920 m3/h screw at 50 Hz (~190 kWe motor), condenser UA 75 kW/K
(~150 plate gasketed PHE), evaporator UA 95 kW/K (shell and tube, effluent tube-side),
80 m3 hot-water store, 520 kW steam generator.

Run: blender -b --factory-startup -P create_industrial_asset.py
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / 'Tools'))

from blendlib import parts as pt  # noqa: E402
from blendlib.core import (MB, R, T, align, anchor, box, cyl, empty, export, extrude, lathe, mat, reset,  # noqa: E402
                           tex_grating, tex_louvre, texture, torus, tube)

reset(HERE / "textures")
P = pt.init()
lr, ln = tex_louvre()
P["louvre"] = mat("Louvre panel", "#b8bbb7", 0.2, 0.5, tex=texture("louvre", lr * 0.8), normal=texture("louvre_n", ln), tex_scale=2.0)
from blendlib.core import pbr, decal_mat  # noqa: E402
P["boiler"] = pbr("Boiler casing (stucco Al)", "sheet_galv2", "#cfc8b4", 0.8, tint="soft", metal=0.7, rough=0.38)
P["brick"] = P["blockwall"]
P["plate_hthp"] = decal_mat("Nameplate HTHP", "plate_hthp", 0.35, 0.4)
P["insul_al"] = P["alu_clad"]

root = empty("IndustrialHTHP", props={"title": "Dairy high-temperature heat pump plant room",
                                       "spec": "Two alternative HTHP layouts; annual simulation on 2023 Cheshire weather"})

# --------------------------------------------------------------- shared building
b = MB()
b.add(box(18.0, 12.0, 0.25, center=(0, 0, -0.125)), P["slab"])
b.add(box(16.0, 10.0, 0.02, center=(0, 0, 0.01)), P["epoxy"])
for x0, x1, y in ((-9, 9, 6.0),):
    b.add(box(x1 - x0, 0.3, 0.6, center=((x0 + x1) / 2, y - 0.15, 0.3)), P["brick"])
b.add(box(0.3, 12.0, 0.6, center=(-8.85, 0, 0.3)), P["brick"])
# housekeeping plinths
for cx, cy, sx, sy in ((-1.6, 0.0, 4.4, 1.4), (1.6, 2.6, 4.0, 1.6), (-5.4, 2.6, 4.4, 1.4)):
    b.add(box(sx, sy, 0.12, center=(cx, cy, 0.06), bevel=0.02), P["concrete"])
b.build("Room_Slab", root)

# pipe rack along y = -4.6 and drop columns
rk = MB()
for x in (-7.5, -4.5, -1.5, 1.5, 4.5):
    for y in (4.9, 5.6):
        rk.add(box(0.15, 0.15, 3.6, center=(x, y, 1.8)), P["paint_yellow"])
    rk.add(box(0.15, 0.85, 0.15, center=(x, 5.25, 3.55)), P["paint_yellow"])
    rk.add(box(0.15, 0.85, 0.15, center=(x, 5.25, 2.6)), P["paint_yellow"])
for y in (4.9, 5.6):
    rk.add(box(12.2, 0.12, 0.12, center=(-1.5, y, 3.55)), P["paint_yellow"])
pt.cable_tray(rk, [(-8.0, 5.45, 3.75), (5.0, 5.45, 3.75)], 0.3, 0.08)
rk.build("Pipe_Rack", root, props={"title": "Pipe rack", "spec": "Two-tier steel rack, 3.6 m"})

# MCC / VFD / PLC line-up against the back wall
mc = MB()
for i, (w, nm) in enumerate(((1.2, "VFD"), (0.8, "PLC"), (1.6, "MCC"))):
    pt.panel(mc, T(-8.3, -3.6 + i * 1.3 + w / 2, 0) @ R(0, 0, -90), w, 0.6, 2.1, 2 if w > 1 else 1)
mc.build("MCC_Lineup", root, props={"title": "MCC, compressor VFD and PLC", "spec": "315 kW VFD, ATEX gas detection interlocks",
                                    "live": "W_hp,cap,on_frac"})
# gas-fired shell boiler (existing) with burner and flue
bo = MB()
A = T(4.2, -2.3, 0)
bo.add(box(4.6, 2.0, 0.3, center=(0, 0, 0.15)), P["paint_dark"], A)
bo.add(lathe([(0, 0), (1.0, 0), (1.0, 4.2), (0, 4.2)], 48), P["boiler"], A @ T(-2.1, 0, 1.35) @ R(0, 90, 0))
for k in range(1, 6):
    bo.add(torus(1.004, 0.01, 48, 4), P["stainless"], A @ T(-2.1 + 0.7 * k, 0, 1.35) @ R(0, 90, 0))
bo.add(lathe([(0, 0), (0.55, 0), (0.6, 0.1), (0.6, 0.9), (0.45, 1.1), (0, 1.15)], 32), P["paint_blue"], A @ T(2.1, 0, 1.35) @ R(0, 90, 0))
bo.add(box(0.5, 0.6, 0.5, center=(2.9, 0.65, 1.35), bevel=0.02), P["paint_blue"], A)
pt.gauge(bo, A @ T(-1.0, -0.9, 2.45), 0.15)
bo.add(cyl(0.3, 2.0, 32, 2.3), P["stainless"], A @ T(-1.8, 0, 0))
bo.add(cyl(0.32, 0.06, 32, 2.3), P["stainless"], A @ T(-1.8, 0, 0))
bo.add(tube([(-1.8, 0, 4.3), (-1.8, 0, 5.2), (-1.8, -2.6, 5.2), (-1.8, -2.6, 9.5)], 0.3, 32), P["stainless"], A)
pt.relief_valve(bo, A @ T(-0.4, 0, 2.38), 0.06)
pt.sign(bo, A @ T(0.6, -1.012, 1.6), "warn_hot", 0.2)
pt.sign(bo, A @ T(1.0, -1.012, 1.6), "warn_pressure", 0.2)
pt.nameplate(bo, A @ T(-0.2, -1.006, 1.6), 0.24, 0.13, key="plate_tank")
bo.build("Gas_Boiler", root, props={"title": "Existing gas-fired shell boiler", "spec": "2 MW, 88 % seasonal efficiency, trims HP shortfall",
                                    "live": "Q_boiler,cost_g"})
anchor("Boiler", (4.2, -2.3, 3.0))

# --------------------------------------------------------------- per-layout equipment
def compressor_package(prefix, disp_label):
    m = MB()
    A = T(-3.5, 0.0, 0.12)
    pts = pt.screw_compressor(m, A, L=1.7, D=0.6, motor_L=1.1, motor_D=0.66)
    pt.nameplate(m, T(-2.6, -0.47, 0.5), 0.2, 0.11, key="plate_hthp")
    pt.sign(m, T(-1.9, -0.47, 0.5), "warn_flammable" if prefix == "Dairy" else "warn_hot", 0.12)
    m.build(f"{prefix}_Compressor", root, props={"title": "Open twin-screw compressor package",
                                                  "spec": f"{disp_label}, slide valve + VFD 25-100 %, IE4 motor",
                                                  "live": "cap,pr,eta_is,T_dis,W_hp"})
    os_ = MB()
    v = pt.vessel_vertical(os_, T(-0.3, -1.25, 0.12), 0.6, 1.4, legs=3, leg_h=0.35, mat=P["paint_grey"],
                           nozzles=[("in", 0.75, 180, 0.1), ("out", "top", 0, 0.1), ("oil", "bottom", 0, 0.04)], sight=-60)
    pt.bphe(os_, T(0.6, -1.35, 0.6), W=0.2, H=0.45, plates=40)
    pt.sign(os_, T(-0.3, -1.25 - 0.32, 1.25), "warn_pressure", 0.1)
    os_.build(f"{prefix}_OilSep", root, props={"title": "Oil separator + oil cooler", "spec": "Coalescing, 3 ppm carry-over"})
    return pts, v


for prefix, layout_kind in (("Dairy", "water"), ("Steam", "steam")):
    comp, osep = compressor_package(prefix, "920 m³/h @50 Hz" if prefix == "Dairy" else "620 m³/h @50 Hz, CSH-class HT screw")
    ev = MB()
    evn, ezc = pt.shell_tube(ev, T(-7.4, 2.6, 0.12), L=3.8, D=0.72 if prefix == "Dairy" else 0.6, nozzle_od=0.15)
    ev.build(f"{prefix}_Evaporator", root, props={
        "title": "Evaporator (shell & tube)", "spec": "Effluent tube-side, refrigerant flooded shell, UA 95 kW/K"
        if prefix == "Dairy" else "Recovery-loop water tube-side, UA 50 kW/K", "live": "Q_src,Te,approach_e"})
    ec = MB()
    eco = pt.bphe(ec, T(1.0, -0.9, 0.4) @ R(0, 0, 90), W=0.32, H=0.8, plates=70)
    ihx_n, ihx_z = pt.shell_tube(ec, T(-2.5, -2.4, 0.12), L=1.8, D=0.3, nozzle_od=0.08, heads=False)
    ec.build(f"{prefix}_Economiser", root, props={"title": "Economiser subcooler + IHX", "spec": "Closed BPHE economiser, port injection; IHX 0.45 effectiveness",
                                                  "live": "Q_econ,econ_frac,Q_ihx"})
    rc = MB()
    recv, rzc = pt.vessel_horizontal(rc, T(0.6, -3.1, 0.12), 0.7, 2.2, nozzles=[("in", 0.2, "top", 0.05), ("out", 0.8, "bottom", 0.05),
                                                                              ("rv", 0.5, "top", 0.03)])
    pt.relief_valve(rc, T(*recv["rv"]), 0.03)
    rc.build(f"{prefix}_Receiver", root, props={"title": "Liquid receiver", "spec": "350 L, PS 25 bar"})
    if prefix == "Dairy":
        cd = MB()
        cports = pt.gasketed_phe(cd, T(0.0, 2.6, 0.12), plates=150, pitch=0.0042, W=0.6, H=1.6)
        cd.build("Dairy_Condenser", root, props={"title": "Condenser (gasketed plate)", "spec": "150 plates 316L, two-zone desuperheat/condense, UA 75 kW/K",
                                                 "live": "Q_hp,Tc,approach_c"})
        # effluent sump pit with grating, level gauge and feed pumps
        sp = MB()
        sp.add(box(4.2, 3.2, 0.06, center=(-6.6, -2.8, 0.03)), P["concrete"])
        sp.add(box(4.0, 3.0, 0.03, center=(-6.6, -2.8, 0.075)), P["grating"])
        sp.add(box(4.3, 0.12, 0.3, center=(-6.6, -1.2, 0.15)), P["concrete"])
        pt.handrail(sp, [(-8.7, -1.25, 0.0), (-4.5, -1.25, 0.0), (-4.5, -4.3, 0.0)], 1.1, 1.4)
        for x in (-7.6, -6.4):
            pt.inline_pump(sp, T(x, -2.2, 0.75), 0.1, 0.32, 0.45)
        pt.strainer(sp, align((1, 0, 0), (-5.4, -2.2, 0.75)), 0.1)
        sp.build("Dairy_Sump", root, props={"title": "Effluent sump (100 m³, below grating)", "spec": "Duty/standby effluent pumps 28.5 m³/h, self-cleaning strainer",
                                            "live": "T_sump,src_level,eff_flow"})
        sl = MB()
        sl.add(box(0.08, 0.04, 1.6, center=(0, 0, 0.8)), P["glass"])
        sl.build("Dairy_Sump_Level", root, props={"noShadow": 1})
        sl_obj = sl
        lvl = MB()
        lvl.add(box(0.06, 0.03, 1.6, center=(0, 0, 0.8)), mat("Sump level", "#2b6cb0", 0.0, 0.3))
        lo = lvl.build("Dairy_Sump_LevelFill", root, props={"noShadow": 1})
        lo.location = (-4.65, -1.2, 0.3)
        bpy_obj = sl.build if False else None
        # 80 m3 hot water store outside the wall
        st = MB()
        stp = pt.storage_cylinder(st, T(7.6, 3.6, 0.0), 3.6, 8.2, P["alu_clad"],
                                  ports=[("top", 0.95, 200, 0.15), ("bot", 0.05, 200, 0.15), ("load_out", 0.93, 160, 0.15),
                                         ("load_ret", 0.07, 160, 0.15)], feet=False)
        st.add(box(4.2, 4.2, 0.4, center=(7.6, 3.6, -0.15), bevel=0.04), P["concrete"])
        # cage ladder
        for z in range(1, 25):
            st.add(cyl(0.015, 0.45, 8), P["galv"], T(7.6 + 1.85, 3.6 - 0.22, z * 0.35) @ R(90, 0, 0))
        for dy in (-0.22, 0.23):
            st.add(box(0.06, 0.02, 8.6, center=(7.6 + 1.85, 3.6 + dy, 4.3)), P["galv"])
        st.build("Dairy_Store", root, props={"title": "Hot-water store 80 m³", "spec": "Stratified, 95 °C top / 60 °C return, 150 mm insulation",
                                              "live": "store_soc,T_deliv,store_loss"})
        for j in range(12):
            bb = MB()
            za = 0.12 + 0.07 + (8.2 - 0.2) * (11 - j) / 12
            bb.add(lathe([(1.8 + 0.006, za + 0.01), (1.8 + 0.01, za + 0.02), (1.8 + 0.01, za + 8.0 / 12 - 0.02), (1.8 + 0.006, za + 8.0 / 12 - 0.01)],
                         72, math.radians(250), math.radians(316)), mat("Store band", "#9aa3aa", 0, 0.5), T(7.6, 3.6, 0))
            bb.build(f"Dairy_Store_Band_{j + 1}", root, props={"noShadow": 1})
        # pipework (dairy)
        pp = MB()
        pt.pipe(pp, [(-5.6, -2.2, 0.75), (-5.0, -2.2, 0.75), (-5.0, 1.6, 0.75), (-5.0, 1.6, 0.6), (evn["tube_in"][0] - 0.5, 1.6, 0.6),
                     (evn["tube_in"][0] - 0.5, evn["tube_in"][1], evn["tube_in"][2]), evn["tube_in"]], 0.1, P["stainless"], flow_name="d_eff_in",
                label="pipe_effluent", label_at=0.3)
        pt.pipe(pp, [evn["tube_out"], (evn["tube_out"][0] + 0.4, evn["tube_out"][1], evn["tube_out"][2]),
                     (evn["tube_out"][0] + 0.4, evn["tube_out"][1], 0.35), (evn["tube_out"][0] + 0.4, 0.6, 0.35), (-8.2, 0.6, 0.35),
                     (-8.2, 0.6, -0.2)], 0.1, P["stainless"], flow_name="d_eff_out")
        # refrigerant: evaporator shell outlet -> IHX -> suction; discharge -> oil sep -> condenser -> receiver -> economiser
        pt.pipe(pp, [evn["shell_in"], (evn["shell_in"][0], 2.6, 1.9), (-3.0, 2.6, 1.9), (-3.0, 0.0, 1.9), comp["suction"]], 0.15,
                P["steel"], insul=0.04, flow_name="d_suction")
        pt.pipe(pp, [comp["discharge"], (comp["discharge"][0], -1.25, comp["discharge"][2]), (osep["in"][0] - 0.3, -1.25, osep["in"][2]),
                     osep["in"]], 0.11, P["steel"], flow_name="d_discharge")
        pt.pipe(pp, [osep["out"], (osep["out"][0], osep["out"][1], 2.6), (-0.3, cports["a_in"][1], 2.6),
                     (cports["a_in"][0] - 0.6, cports["a_in"][1], 2.6), (cports["a_in"][0] - 0.6, cports["a_in"][1], cports["a_in"][2]),
                     cports["a_in"]], 0.11, P["steel"], flow_name="d_hotgas")
        pt.pipe(pp, [cports["a_out"], (cports["a_out"][0] - 0.5, cports["a_out"][1], cports["a_out"][2]),
                     (cports["a_out"][0] - 0.5, cports["a_out"][1], 0.3), (0.6, 0.6, 0.3), (0.6, -3.1, 0.3), recv["in"]], 0.065,
                P["steel"], flow_name="d_liquid")
        pt.pipe(pp, [recv["out"], (recv["out"][0], -3.1, 0.18), (1.6, -3.1, 0.18), (1.6, -0.9, 0.18), (1.6, -0.9, 0.6),
                     eco["p3"]], 0.05, P["steel"], flow_name="d_subcool")
        pt.pipe(pp, [eco["p1"], (eco["p1"][0], eco["p1"][1] - 0.2, eco["p1"][2]), (eco["p1"][0], -0.5, 1.6), (-3.0, -0.5, 1.6),
                     (-3.0, -0.3, 1.0)], 0.05, P["steel"], insul=0.03, flow_name="d_econ_vap")
        pt.pipe(pp, [eco["p4"], (eco["p4"][0], -2.4, eco["p4"][2]), (ihx_n["tube_out"][0], -2.4, 0.5), ihx_n["tube_out"]], 0.05,
                P["steel"], flow_name="d_main_liq")
        pt.pipe(pp, [ihx_n["tube_in"], (ihx_n["tube_in"][0] - 0.4, ihx_n["tube_in"][1], ihx_n["tube_in"][2]),
                     (-6.0, -1.0, 0.45), (-6.0, 2.6, 0.45), (evn["shell_out"][0], 2.6, 0.45), evn["shell_out"]], 0.05, P["steel"],
                insul=0.03, flow_name="d_evap_feed")
        pt.control_valve(pp, T(-6.0, 0.6, 0.45) @ R(0, 0, 90), 0.05)
        # condenser water side to store
        pt.pipe(pp, [cports["b_out"], (cports["b_out"][0] - 0.4, cports["b_out"][1], cports["b_out"][2]),
                     (cports["b_out"][0] - 0.4, cports["b_out"][1], 3.1), (cports["b_out"][0] - 0.4, 4.4, 3.1), (stp["top"][0] - 1.0, 4.4, 3.1),
                     (stp["top"][0] - 1.0, 4.4, stp["top"][2]), (stp["top"][0] - 0.6, stp["top"][1] + 0.3, stp["top"][2]), stp["top"]],
                0.125, P["steel"], insul=0.05, flow_name="d_hw_flow", label="pipe_process", label_at=0.45)
        pt.pipe(pp, [stp["bot"], (stp["bot"][0], stp["bot"][1], 0.5), (2.2, 3.6, 0.5), (2.2, cports["b_in"][1], 0.5),
                     (cports["b_in"][0] - 0.4, cports["b_in"][1], 0.5), (cports["b_in"][0] - 0.4, cports["b_in"][1], cports["b_in"][2]),
                     cports["b_in"]], 0.125, P["steel"], insul=0.05, flow_name="d_hw_ret")
        pt.inline_pump(pp, T(2.2, 3.0, 0.5) @ R(0, 0, 90), 0.125, 0.3, 0.42)
        pt.pipe(pp, [stp["load_out"], (stp["load_out"][0] - 0.3, stp["load_out"][1], stp["load_out"][2]),
                     (stp["load_out"][0] - 0.3, stp["load_out"][1], 7.2), (5.2, stp["load_out"][1], 7.2), (5.2, -0.5, 7.2),
                     (5.2, -0.5, 3.6), (8.8, -0.5, 3.6)], 0.15, P["steel"], insul=0.05, flow_name="d_process",
                label="pipe_process", label_at=0.55)
        pp.build("Dairy_Pipework", root, props={"title": "Dairy HTHP pipework", "spec": "Refrigerant carbon steel (butane ATEX zone 2), effluent 316L",
                                                "live": "m_ref,m_econ"})
        anchor("Store", (7.6, 3.6, 8.9))
        anchor("Sump", (-6.6, -2.8, 1.4))
    else:
        sg = MB()
        A = T(0.2, 2.6, 0.12)
        sg.add(box(3.6, 1.4, 0.4, center=(1.8, 0, 0.2)), P["paint_dark"], A)
        sg.add(lathe([(0, 0), (0.75, 0), (0.75, 3.5), (0, 3.5)], 48), P["alu_clad"], A @ T(0, 0, 1.25) @ R(0, 90, 0))
        sg.add(lathe(pt.dished_profile(0.75, 0.0, 3.5, 0.25, 8, True, True), 48), P["alu_clad"], A @ T(-0.17, 0, 1.25) @ R(0, 90, 0))
        for k in range(1, 6):
            sg.add(torus(0.755, 0.008, 48, 4), P["stainless"], A @ T(0.58 * k, 0, 1.25) @ R(0, 90, 0))
        dome = pt.vessel_vertical(sg, A @ T(1.75, 0, 1.6), 0.7, 1.0, legs=0, leg_h=0.2, mat=P["alu_clad"],
                                  nozzles=[("steam", "top", 0, 0.15)], sight=0)
        pt.relief_valve(sg, A @ T(2.6, 0, 2.02), 0.05)
        pt.gauge(sg, A @ T(1.2, -0.75, 2.0), 0.15)
        sg.build("Steam_Generator", root, props={"title": "Kettle steam generator", "spec": "R1233zd(E) condensing shell-side, 2.7 bar(a) saturated steam, separator dome",
                                                  "live": "Q_hp,Tc,steam_kgh"})
        cports = {"a_in": (2.0, 2.6, 2.1)}
        da = MB()
        dpts, dz = pt.vessel_horizontal(da, T(5.0, 3.6, 2.2), 1.2, 3.0, nozzles=[("vent", 0.2, "top", 0.05), ("out", 0.7, "bottom", 0.1)])
        for x in (5.4, 7.6):
            for y in (3.1, 4.1):
                da.add(box(0.15, 0.15, 2.2, center=(x, y, 1.1)), P["paint_grey"])
        da.add(box(2.6, 1.3, 0.12, center=(6.5, 3.6, 2.2)), P["grating"])
        da.build("Steam_Deaerator", root, props={"title": "Deaerator / feedwater tank", "spec": "105 °C, 6 m³"})
        ex_ = MB()
        ex_.add(box(1.8, 1.8, 6.0, center=(-6.9, -2.8, 3.6)), P["galv"])
        ex_.add(box(2.1, 2.1, 1.8, center=(-6.9, -2.8, 2.0), bevel=0.03), P["paint_grey"])
        for z in (1.25, 2.75):
            ex_.add(box(2.3, 2.3, 0.08, center=(-6.9, -2.8, z)), P["paint_grey"])
        pt.finned_coil(ex_, T(-6.9, -3.85, 1.25), 1.7, 1.5, 0.12, headers=True)
        ex_.add(box(1.8, 3.0, 1.8, center=(-6.9, -0.8, 5.7)), P["galv"])
        ex_.build("Steam_ExhaustDuct", root, props={"title": "Spray-dryer exhaust duct + run-around coil", "spec": "Exhaust ~82 °C, coil UA 38 kW/K, 30 m³ loop buffer",
                                                    "live": "T_loop,Q_recov,dryer"})
        hd = MB()
        pt.pipe(hd, [(-8.0, 5.25, 3.85), (5.0, 5.25, 3.85)], 0.2, P["steel"], insul=0.06, flow_name="s_header",
                label="pipe_steam", label_at=0.25)
        for x in (-4.0, 0.0):
            pt.ball_valve(hd, align((0, 0, 1), (x, 5.25, 4.25)), 0.1)
            hd.add(cyl(0.05, 0.4, 16, 4.0), P["steel"], T(x, 5.25, 0))
        hd.build("Steam_Header", root, props={"title": "2.7 bar steam header", "spec": "DN200, to process users"})
        pp = MB()
        pt.pipe(pp, [(-6.0, -2.8, 2.0), (-6.0, -1.0, 2.0), (-6.0, 1.6, 2.0), (evn["tube_in"][0] - 0.5, 1.6, 2.0),
                     (evn["tube_in"][0] - 0.5, evn["tube_in"][1], evn["tube_in"][2]), evn["tube_in"]], 0.15, P["steel"], insul=0.04,
                flow_name="s_loop_in")
        pt.pipe(pp, [evn["tube_out"], (evn["tube_out"][0] + 0.4, evn["tube_out"][1], evn["tube_out"][2]),
                     (evn["tube_out"][0] + 0.4, evn["tube_out"][1], 1.0), (-5.6, -2.0, 1.0), (-6.0, -2.4, 1.0)], 0.15, P["steel"],
                insul=0.04, flow_name="s_loop_out")
        pt.pipe(pp, [evn["shell_in"], (evn["shell_in"][0], 2.6, 1.9), (-3.0, 2.6, 1.9), (-3.0, 0.0, 1.9), comp["suction"]], 0.15,
                P["steel"], insul=0.04, flow_name="s_suction")
        pt.pipe(pp, [comp["discharge"], (comp["discharge"][0], -1.25, comp["discharge"][2]), (osep["in"][0] - 0.3, -1.25, osep["in"][2]),
                     osep["in"]], 0.11, P["steel"], insul=0.04, flow_name="s_discharge")
        pt.pipe(pp, [osep["out"], (osep["out"][0], osep["out"][1], 2.7), (0.6, 2.6, 2.7), (0.6, 2.6, 2.05)], 0.11, P["steel"],
                insul=0.04, flow_name="s_hotgas")
        pt.pipe(pp, [(0.6, 2.0, 1.0), (0.6, 0.6, 0.3), (0.6, -3.1, 0.3), recv["in"]], 0.065, P["steel"], flow_name="s_liquid")
        pt.pipe(pp, [recv["out"], (recv["out"][0], -3.1, 0.18), (1.6, -3.1, 0.18), (1.6, -0.9, 0.18), (1.6, -0.9, 0.6), eco["p3"]],
                0.05, P["steel"], flow_name="s_subcool")
        pt.pipe(pp, [eco["p1"], (eco["p1"][0], eco["p1"][1] - 0.2, eco["p1"][2]), (eco["p1"][0], -0.5, 1.6), (-3.0, -0.5, 1.6),
                     (-3.0, -0.3, 1.0)], 0.05, P["steel"], insul=0.03, flow_name="s_econ_vap")
        pt.pipe(pp, [eco["p4"], (eco["p4"][0], -2.4, eco["p4"][2]), (ihx_n["tube_out"][0], -2.4, 0.5), ihx_n["tube_out"]], 0.05,
                P["steel"], flow_name="s_main_liq")
        pt.pipe(pp, [ihx_n["tube_in"], (ihx_n["tube_in"][0] - 0.4, ihx_n["tube_in"][1], ihx_n["tube_in"][2]), (-6.0, -1.0, 0.45),
                     (-6.0, 2.6, 0.45), (evn["shell_out"][0], 2.6, 0.45), evn["shell_out"]], 0.05, P["steel"], insul=0.03,
                flow_name="s_evap_feed")
        pt.pipe(pp, [dome["steam"], (dome["steam"][0], dome["steam"][1], 3.85), (dome["steam"][0], 5.25, 3.85)], 0.15, P["steel"],
                insul=0.05, flow_name="s_steam")
        pt.pipe(pp, [dpts["out"], (dpts["out"][0], 3.6, 0.5), (2.4, 3.6, 0.5), (2.4, 2.6, 0.5), (2.0, 2.6, 0.8)], 0.065, P["steel"],
                insul=0.03, flow_name="s_feedwater")
        pt.inline_pump(pp, T(3.2, 3.6, 0.5), 0.065, 0.25, 0.35)
        pp.build("Steam_Pipework", root, props={"title": "Steam HTHP pipework", "spec": "Carbon steel, insulated 40-60 mm",
                                                "live": "m_ref,m_econ,steam_kgh"})
        anchor("Dryer", (-6.9, -2.8, 6.9))
        anchor("SteamGen", (1.8, 2.6, 3.2))

# state-point anchors (same locations for both layouts)
anchor("SP_1", (-5.6, 2.6, 1.95))
anchor("SP_2", (-3.0, 0.4, 2.05))
anchor("SP_3", (-2.7, -0.25, 1.35))
anchor("SP_4", (-2.3, -0.25, 1.35))
anchor("SP_5", (-0.9, -1.25, 1.35))
anchor("SP_6", (0.6, 0.9, 0.45))
anchor("SP_7", (1.0, -0.9, 1.35))
anchor("SP_8", (-2.2, -0.5, 1.75))
anchor("SP_9", (1.6, -1.8, 0.35))
anchor("SP_10", (-2.0, -2.4, 0.95))
anchor("SP_11", (-6.0, 1.4, 0.6))
anchor("SP_S1", (-5.0, 0.8, 0.95))
anchor("SP_S2", (-3.2, 2.6, 2.4))
anchor("SP_K1", (1.2, 3.2, 0.7))
anchor("SP_K2", (1.2, 2.6, 3.0))
anchor("Comp", (-2.6, 0.0, 2.2))

import bpy  # noqa: E402
for o in bpy.data.objects:
    if o.name.startswith("Steam_"):
        o.hide_render = True
export(HERE, "industrial_hthp", camera={"pos": (11.5, -14.0, 10.0), "target": (-0.5, 0.0, 1.5), "lens": 32})
print("done")
