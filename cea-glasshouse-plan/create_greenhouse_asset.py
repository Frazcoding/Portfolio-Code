"""20 x 20 m Venlo glasshouse with tomato crop and a two-stage R717 heat pump plant room.

Geometry follows the thesis boundary (20 x 20 m, 5 m gutter, 1.5 m3 buffer) and the annual model:
five 4 m Venlo spans (22 deg roof), galvanised columns at 4 x 5 m with lattice girders, aluminium
gutters/ridges/glazing bars, hinged roof vents (Vent_*), an energy screen (Thermal_Screen), 900 m of
51 mm pipe rail (Pipe_Rails), ~350 high-wire tomato plants, and an open-sided plant room housing the
LP/HP reciprocating ammonia compressors, open intercooler, condenser and buffer. Source equipment
for each scenario (Src_Air_*, Src_Ground_*, Src_Water_*) is shown by the viewer as appropriate.
Run: blender -b --factory-startup -P create_greenhouse_asset.py
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / 'Tools'))

from blendlib import parts as pt  # noqa: E402
from blendlib.core import (MB, R, T, align, anchor, box, cyl, decal_mat, empty, export, extrude, lathe, mat, pbr,  # noqa: E402
                           reset, sphere, tex_fins, texture, torus, tube)

reset(HERE / "textures")
P = pt.init()
rgb, nrm = tex_fins(512, 512, 6)
P["fins"] = mat("Aluminium fin pack", "#aeb6bb", 0.7, 0.42, tex=texture("fins", rgb), normal=texture("fins_n", nrm), tex_scale=4.0)
P["gh_glass"] = mat("Horticultural glass (diffuse)", "#e9f2f2", 0.0, 0.04, alpha=0.16)
P["gh_alu"] = pbr("Glazing bar aluminium", "brushed", "#d5d9dc", 0.6, tint="soft", metal=0.9, rough=0.35)
P["screen"] = mat("Energy screen fabric", "#efece2", 0.0, 0.9, alpha=0.82)
P["cover"] = pbr("Ground cover (woven PP)", "plastic_rough", "#e9e9e4", 0.4, tint="soft", metal=0.0, rough=0.8)
P["substrate"] = mat("Substrate slab wrap", "#f2f2ee", 0.0, 0.55)
P["leaf"] = decal_mat("Tomato leaf", "leaf_tomato", 0.55, 0.0)
P["stem"] = mat("Tomato stem", "#4f7a34", 0.0, 0.6)
P["fruit_red"] = mat("Tomato ripe", "#c0281c", 0.0, 0.25, coat=0.6)
P["fruit_or"] = mat("Tomato turning", "#e07a22", 0.0, 0.25, coat=0.6)
P["fruit_gr"] = mat("Tomato green", "#6f9c3a", 0.0, 0.3, coat=0.5)
P["string"] = mat("Crop twine", "#d8d2bf", 0.0, 0.9)
P["roof_sheet"] = pbr("Plant-room roof sheet", "corrugated", "#9aa1a4", 1.0, tint="soft", metal=0.8, rough=0.4)

root = empty("Greenhouse", props={"title": "Venlo glasshouse with R717 heat pump", "spec": "20 x 20 x 5 m, Chelmsford (thesis site)"})
GZ = 5.0
SPAN = 4.0
SLOPE = math.radians(22.0)
RIDGE_DZ = (SPAN / 2) * math.tan(SLOPE)
GUTTERS = [-10.0 + SPAN * k for k in range(6)]
RIDGES = [-8.0 + SPAN * k for k in range(5)]
COLS_Y = [-10.0, -5.0, 0.0, 5.0, 10.0]

# ------------------------------------------------------------------ site
site = MB()
site.add(box(60, 44, 0.1, center=(4, 0, -0.05), bevel=0.0), P["grass"])
site.add(box(21.0, 21.0, 0.14, center=(0, 0, 0.0), bevel=0.02), P["slab"])
site.add(box(19.8, 19.8, 0.01, center=(0, 0, 0.075), bevel=0.0), P["cover"])
site.add(box(19.8, 1.4, 0.02, center=(0, 0, 0.08), bevel=0.0), P["concrete"])          # central concrete path
site.add(box(9.0, 8.5, 0.15, center=(15.2, 0, 0.0), bevel=0.02), P["slab"])
site.add(box(4.0, 30.0, 0.05, center=(-13.0, 0, 0.0), bevel=0.0), P["gravel"])
site.build("Site", root)

# ------------------------------------------------------------------ structure
st = MB()
for x in GUTTERS:
    for y in COLS_Y:
        st.add(box(0.12, 0.08, GZ, center=(x, y, GZ / 2)), P["galv"])
        st.add(box(0.25, 0.25, 0.02, center=(x, y, 0.08)), P["galv"])
    # gutter (W-profile aluminium) along y
    gprof = [(-0.16, 0.0), (0.16, 0.0), (0.16, 0.12), (0.10, 0.06), (0.04, 0.12), (-0.04, 0.12), (-0.10, 0.06), (-0.16, 0.12)]
    st.add(extrude(gprof, 20.2, z0=-10.1), P["gh_alu"], T(x, 0, GZ - 0.06) @ R(90, 0, 0))
for y in COLS_Y:
    # lattice girder along x at each column line
    for z in (GZ - 0.05, GZ - 0.65):
        st.add(box(20.0, 0.06, 0.06, center=(0, y, z)), P["galv"])
    nd = 40
    for k in range(nd):
        x0 = -10 + 20 * k / nd
        x1 = -10 + 20 * (k + 1) / nd
        a, b = (x0, y, GZ - 0.65), (x1, y, GZ - 0.05)
        if k % 2:
            a, b = (x0, y, GZ - 0.05), (x1, y, GZ - 0.65)
        st.add(tube([a, b], 0.012, 6), P["galv"])
for x in RIDGES:
    st.add(box(0.06, 20.2, 0.1, center=(x, 0, GZ + RIDGE_DZ)), P["gh_alu"])
    # roof bars from ridge to both gutters every 1.25 m
    for side in (-1, 1):
        L = (SPAN / 2) / math.cos(SLOPE)
        for k in range(17):
            y = -10 + k * 1.25
            mid = (x + side * SPAN / 4, y, GZ + RIDGE_DZ / 2)
            st.add(box(L, 0.035, 0.045), P["gh_alu"], T(*mid) @ R(0, side * math.degrees(SLOPE), 0))
# side walls and gables: glazing bars + kick wall
for (cx, cy, ax, Lw) in ((0, -10.0, "x", 20.0), (0, 10.0, "x", 20.0), (-10.0, 0, "y", 20.0), (10.0, 0, "y", 20.0)):
    if ax == "x":
        st.add(box(Lw, 0.12, 0.6, center=(cx, cy, 0.3)), P["concrete"])
        for k in range(17):
            st.add(box(0.035, 0.05, GZ - 0.6, center=(-10 + k * 1.25, cy, 0.6 + (GZ - 0.6) / 2)), P["gh_alu"])
        st.add(box(Lw, 0.05, 0.05, center=(cx, cy, 2.6)), P["gh_alu"])
    else:
        st.add(box(0.12, Lw, 0.6, center=(cx, cy, 0.3)), P["concrete"])
        for k in range(17):
            st.add(box(0.05, 0.035, GZ - 0.6, center=(cx, -10 + k * 1.25, 0.6 + (GZ - 0.6) / 2)), P["gh_alu"])
        st.add(box(0.05, Lw, 0.05, center=(cx, cy, 2.6)), P["gh_alu"])
# door on the south gable
st.add(box(2.4, 0.08, 2.6, center=(0, -10.04, 1.3)), P["gh_alu"])
st.build("Structure", root, props={"title": "Venlo structure", "spec": "Galvanised columns 4 x 5 m grid, lattice girders, Al gutters and bars"})

gl = MB()
for x in RIDGES:
    for side in (-1, 1):
        L = (SPAN / 2) / math.cos(SLOPE)
        gl.add(box(L, 20.0, 0.004, bevel=0.0), P["gh_glass"], T(x + side * SPAN / 4, 0, GZ + RIDGE_DZ / 2 + 0.025) @ R(0, side * math.degrees(SLOPE), 0))
for (cx, cy, ax) in ((0, -10.0, "x"), (0, 10.0, "x"), (-10.0, 0, "y"), (10.0, 0, "y")):
    sx, sy = (20.0, 0.004) if ax == "x" else (0.004, 20.0)
    gl.add(box(sx, sy, GZ - 0.6, center=(cx, cy, 0.6 + (GZ - 0.6) / 2), bevel=0.0), P["gh_glass"])
    # gable triangles
    if ax == "x":
        for x in RIDGES:
            tri = [(x - 2, 0), (x + 2, 0), (x, RIDGE_DZ)]
            gl.add(extrude(tri, 0.004, z0=-0.002), P["gh_glass"], T(0, cy, GZ) @ R(90, 0, 0))
gl.build("Glazing", root, props={"noShadow": 1, "title": "Diffuse horticultural glass", "spec": "4 mm, τ ≈ 0.70 (thesis)"})

# hinged roof vents (east facet of each span), origin on the ridge hinge
for si, x in enumerate(RIDGES):
    for vi, y in enumerate((-7.5, -2.5, 2.5, 7.5)):
        v = MB()
        Lv, Wv = 1.05, 2.4
        for (cx_, cy_, sx_, sy_) in ((Lv / 2, -Wv / 2 + 0.025, Lv, 0.05), (Lv / 2, Wv / 2 - 0.025, Lv, 0.05),
                                     (0.025, 0, 0.05, Wv), (Lv - 0.025, 0, 0.05, Wv)):
            v.add(box(sx_, sy_, 0.045, center=(cx_, cy_, 0.0)), P["gh_alu"])
        v.add(box(Lv - 0.08, Wv - 0.08, 0.006, center=(Lv / 2, 0, 0.022), bevel=0.0), P["gh_glass"])
        v.add(box(0.04, 0.04, 0.5, center=(Lv * 0.8, 0, -0.25)), P["galv"])
        o = v.build(f"Vent_{si}_{vi}", root, props={"title": "Roof vent", "spec": "Hinged at ridge, rack-and-pinion, max 35°", "live": "vent"})
        o.location = (x, y, GZ + RIDGE_DZ + 0.06)
        o.rotation_euler = (0.0, SLOPE, 0.0)

sc = MB()
for x in RIDGES:
    sc.add(box(SPAN - 0.1, 19.8, 0.004, center=(x, 0, GZ - 0.25), bevel=0.0), P["screen"])
_scr = sc.build("Thermal_Screen", root, props={"noShadow": 1, "title": "Energy screen", "spec": "Aluminised fabric, 45 % saving when closed", "live": "screen"})

# ------------------------------------------------------------------ crop and heating
rng = np.random.default_rng(5)
rails = MB()
crop = MB()
fruit = MB()
ROW_X = [c + d for c in RIDGES for d in (-1.0, 1.0)]
for rx in ROW_X:
    for px in (rx - 0.32, rx + 0.32):
        rails.add(tube([(px, -9.4, 0.14), (px, 9.4, 0.14)], 0.0255, 16), P["steel"])
    rails.add(tube([(rx - 0.32, 9.4, 0.14), (rx - 0.32, 9.65, 0.14), (rx + 0.32, 9.65, 0.14), (rx + 0.32, 9.4, 0.14)], 0.0255, 12), P["steel"])
    # hanging substrate gutter + slabs
    crop.add(box(0.28, 17.6, 0.05, center=(rx, 0, 0.42)), P["galv"])
    for k in range(17):
        crop.add(box(0.2, 0.95, 0.08, center=(rx, -8.3 + k * 1.04, 0.49), bevel=0.01), P["substrate"])
    crop.add(tube([(rx, -9.2, 3.65), (rx, 9.2, 3.65)], 0.004, 6), P["galv"])            # crop wire
    for k in range(35):
        y = -8.5 + k * 0.5 + rng.normal(0, 0.03)
        lean = rng.normal(0, 0.06)
        h = 3.1 + rng.normal(0, 0.12)
        base = (rx + rng.normal(0, 0.03), y, 0.53)
        top = (rx + lean, y + rng.normal(0, 0.05), 0.53 + h)
        crop.add(tube([base, (base[0] + lean * 0.5, y, 0.53 + h * 0.5), top], 0.009, 6, cap=False), P["stem"])
        crop.add(tube([top, (rx, y, 3.65)], 0.0015, 4, cap=False), P["string"])
        nleaf = 7
        for j in range(nleaf):
            z = 0.53 + h * (0.35 + 0.62 * j / nleaf)
            ang = 137.5 * j + rng.uniform(-20, 20)
            droop = rng.uniform(25, 45)
            Ls = 0.55 + rng.uniform(-0.05, 0.08) - 0.03 * (j > 4)
            Ml = T(base[0] + lean * (z - 0.53) / h, y, z) @ R(0, 0, ang) @ R(0, -(90 - droop), 0)
            w = Ls * 0.5
            crop.add(([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, Ls), (-w / 2, 0, Ls)], [(0, 1, 2, 3)],
                      [[(0, 0), (1, 0), (1, 1), (0, 1)]]), P["leaf"], Ml)
        for t in range(3):
            zt = 0.53 + h * (0.22 + 0.11 * t)
            col = P["fruit_red"] if t == 0 else (P["fruit_or"] if t == 1 else P["fruit_gr"])
            a0 = rng.uniform(0, 360)
            for f in range(4):
                a = math.radians(a0 + 70 * f)
                fruit.add(sphere(0.032, 8, 6), col, T(base[0] + 0.08 * math.cos(a), y + 0.08 * math.sin(a), zt - 0.03 * f))
# headers to the plant room
rails.add(tube([(-9.0, 9.65, 0.3), (10.6, 9.65, 0.3)], 0.045, 16), P["steel"])
rails.add(tube([(-9.0, 9.85, 0.45), (10.6, 9.85, 0.45)], 0.045, 16), P["steel"])
rails.build("Pipe_Rails", root, props={"title": "Pipe-rail heating", "spec": "51 mm steel, 900 m, doubles as trolley rail", "live": "T_pipe,T_sup,Q_pipe"})
crop.build("Crop", root, props={"title": "High-wire tomato crop", "spec": "~350 plants, 2.5 stems/m², LAI ≈ 3", "live": "LE,trans_kg,VPD"})
fruit.build("Crop_Fruit", root)
anchor("Climate", (0, 0, GZ + 2.0))
anchor("Pipes", (-6.0, -6.0, 0.8))
anchor("Screen", (8.0, -9.0, GZ - 0.2))

# ------------------------------------------------------------------ plant room (open-sided canopy)
pr = MB()
for x in (11.4, 19.0):
    for y in (-3.8, 3.8):
        pr.add(box(0.15, 0.15, 3.4, center=(x, y, 1.7)), P["paint_dark"])
pr.add(box(8.2, 8.2, 0.08, center=(15.2, 0, 3.45)), P["roof_sheet"])
pr.add(box(8.0, 0.12, 0.25, center=(15.2, -3.8, 3.3)), P["paint_dark"])
pr.add(box(8.0, 0.12, 0.25, center=(15.2, 3.8, 3.3)), P["paint_dark"])
pr.add(box(0.06, 7.6, 2.6, center=(19.0, 0, 1.5)), P["blockwall"])
pr.build("Plant_Room", root, props={"title": "Plant room canopy", "spec": "Open-sided, ammonia detection + extract fan"})
hp = MB()
lp = pt.recip_compressor(hp, T(12.2, -2.6, 0.08), ncyl=4, bore=0.13, L=1.05, motor_L=0.9, motor_D=0.48)
hpc = pt.recip_compressor(hp, T(12.2, -0.7, 0.08), ncyl=2, bore=0.10, L=0.7, motor_L=0.75, motor_D=0.4)
ic = pt.vessel_vertical(hp, T(16.4, -2.2, 0.08), 0.6, 1.4, legs=3, leg_h=0.35, mat=P["paint_grey"],
                        nozzles=[("in", 0.8, 180, 0.08), ("vap", "top", 0, 0.08), ("liq", "bottom", 0, 0.05), ("lpin", 0.4, 90, 0.08)],
                        sight=-90, insulated=True, clad_mat=P["alu_clad"])
cnd, czc = pt.shell_tube(hp, T(14.8, 1.6, 0.08), L=2.6, D=0.42, nozzle_od=0.08)
rcv, rzc = pt.vessel_horizontal(hp, T(15.0, 3.0, 0.08), 0.45, 1.6, nozzles=[("in", 0.2, "top", 0.04), ("out", 0.8, "bottom", 0.04)])
pt.sign(hp, T(17.5, -3.86, 1.6) @ R(0, 0, 0), "warn_ammonia", 0.22)
pt.sign(hp, T(17.9, -3.86, 1.6), "warn_pressure", 0.22)
pt.panel(hp, T(18.4, 2.2, 0.08) @ R(0, 0, 90), 1.2, 0.5, 2.0, 2)
pt.pipe(hp, [lp["discharge"], (lp["discharge"][0] - 0.3, lp["discharge"][1], lp["discharge"][2]), (11.6, -3.2, 1.6), (16.4, -3.2, 1.6),
             (16.4, -3.2, ic["lpin"][2]), ic["lpin"]], 0.06, P["steel"], flow_name="r_lp_dis")
pt.pipe(hp, [ic["vap"], (16.4, -2.2, 2.6), (11.6, -1.4, 2.6) if False else (11.6, -2.2, 2.6), (11.6, -1.03, 2.6), (hpc["suction"][0], hpc["suction"][1], 2.6),
             hpc["suction"]], 0.06, P["steel"], insul=0.03, flow_name="r_hp_suc")
pt.pipe(hp, [hpc["discharge"], (hpc["discharge"][0] - 0.3, hpc["discharge"][1], hpc["discharge"][2]), (11.6, -0.37, 2.2), (14.0, -0.37, 2.2),
             (14.0, cnd["shell_in"][1], 2.2), cnd["shell_in"]], 0.05, P["steel"], flow_name="r_hp_dis", label="pipe_refrig_discharge")
pt.pipe(hp, [cnd["shell_out"], (cnd["shell_out"][0], cnd["shell_out"][1], 0.25), (15.0, 3.0, 0.25), rcv["in"]], 0.04, P["steel"], flow_name="r_liquid")
pt.pipe(hp, [rcv["out"], (rcv["out"][0], rcv["out"][1], 0.2), (16.9, 3.0, 0.2), (16.9, -2.2, 0.2), (16.9, -2.2, ic["in"][2]), ic["in"]],
        0.04, P["steel"], flow_name="r_hp_liq")
pt.control_valve(hp, T(16.9, 0.5, 0.2) @ R(0, 0, 90), 0.04)
anchor("HP", (13.0, -1.6, 2.4))
for sid, xyz in {"1": (11.5, -3.6, 1.0), "2": (11.6, -2.93, 1.3), "3": (12.6, -3.2, 1.75), "4": (16.4, -2.2, 2.75), "5": (12.6, -0.37, 2.35),
                 "6": (15.9, 1.6, 0.4), "7": (16.9, -1.0, 0.35), "8": (16.4, -2.2, 2.1), "9": (16.4, -2.2, 0.25), "10": (11.6, -3.8, 0.4)}.items():
    anchor(f"SP_{sid}", xyz)
# buffer 1.5 m3 with indicator strip
bf = pt.storage_cylinder(hp, T(17.4, 0.3, 0.08), 1.05, 1.75, P["paint_grey"],
                         ports=[("top", 0.9, 180, 0.054), ("bot", 0.08, 180, 0.054), ("hf", 0.85, 90, 0.054), ("hr", 0.12, 90, 0.054)])
pt.nameplate(hp, T(17.4, 0.3 - 0.535, 0.9), 0.16, 0.09, key="plate_tank")
pt.pipe(hp, [cnd["tube_out"], (cnd["tube_out"][0], cnd["tube_out"][1] - 0.3, cnd["tube_out"][2]), (17.4 - 0.7, 0.3, cnd["tube_out"][2]),
             (17.4 - 0.7, 0.3, bf["top"][2] - 0.25), bf["top"]], 0.054, P["steel"], insul=0.02, flow_name="w_charge", label="pipe_lthw_flow")
pt.pipe(hp, [bf["hf"], (bf["hf"][0], 2.0, bf["hf"][2]), (10.6, 2.0, bf["hf"][2]), (10.6, 9.65, bf["hf"][2]), (10.6, 9.65, 0.3)], 0.054,
        P["steel"], insul=0.02, flow_name="h_flow", label="pipe_lthw_flow", label_at=0.35)
pt.pipe(hp, [bf["hr"], (bf["hr"][0], 2.3, bf["hr"][2]), (10.8, 2.3, bf["hr"][2]), (10.8, 9.85, bf["hr"][2]), (10.8, 9.85, 0.45)], 0.054,
        P["steel"], insul=0.02, flow_name="h_ret", label="pipe_lthw_return", label_at=0.35)
hp.build("HP_Skid", root, props={"title": "Two-stage R717 heat pump", "spec": "Open reciprocating LP (4-cyl) + HP (2-cyl), open intercooler, shell-and-tube condenser",
                                  "refrigerant": "R717 ammonia", "live": "Q_c,cop,f_lp,f_hp,T_dis_hp"})
anchor("Buffer", (17.4, 0.3, 2.3))
for j in range(10):
    bb = MB()
    za = 0.08 + 0.12 + 0.07 + (1.75 - 0.2) * (9 - j) / 10
    bb.add(lathe([(0.531, za + 0.008), (0.536, za + 0.012), (0.536, za + 1.55 / 10 - 0.012), (0.531, za + 1.55 / 10 - 0.008)], 48,
                 math.radians(230), math.radians(300)), mat("Buffer band", "#9aa3aa", 0, 0.5), T(17.4, 0.3, 0))
    bb.build(f"Buffer_Band_{j + 1}", root, props={"noShadow": 1})

# ------------------------------------------------------------------ source equipment (one shown per scenario)
sa = MB()
hubs = pt.ashp_unit(sa, T(23.0, 0.0, 0.0) @ R(0, 0, 90), L=5.2, W=2.2, H=2.3, nfans=3, D_fan=0.92, casing=P["paint_grey"], louvre=P["paint_grey"])
pt.pipe(sa, [(23.0, -2.4, 0.6), (19.6, -2.4, 0.6), (19.6, -3.6, 0.6), (11.4, -3.6, 0.6), (11.4, -2.93, 0.6), lp["suction"]], 0.076, P["steel"],
        insul=0.03, flow_name="air_suction", label="pipe_refrig_suction")
sa.build("Src_Air_Unit", root, props={"title": "Air-source evaporator", "spec": "Ammonia air cooler, 3 x Ø900 mm EC fans, UA 18 kW/K", "live": "frost,defrosts,T_src"})
for k, Mh in enumerate(hubs):
    rot = MB()
    pt.fan_rotor(rot, T(0, 0, 0), 0.92, 5)
    o = rot.build(f"Src_Air_Fan_{k + 1}", root)
    o.matrix_world = Mh
sg = MB()
sg.add(box(1.6, 1.2, 0.5, center=(22.5, -1.5, 0.15), bevel=0.03), P["concrete"])
sg.add(box(1.4, 1.0, 0.04, center=(22.5, -1.5, 0.42)), P["diamond"])
for i_ in range(4):
    for j_ in range(4):
        sg.add(cyl(0.12, 0.05, 20), P["concrete"], T(25.0 + i_ * 1.6, -4.0 + j_ * 2.4, 0.0))
pt.pipe(sg, [(22.5, -1.5, 0.45), (22.5, -1.5, 0.9), (20.0, -1.5, 0.9), (20.0, -3.6, 0.9), (11.4, -3.6, 0.9), (11.4, -2.93, 0.9)], 0.076,
        P["plastic_black"], flow_name="ground_loop")
pt.plate_hx_dummy = None
pt.gasketed_phe(sg, T(19.6, -2.8, 0.08) @ R(0, 0, 90), plates=60, pitch=0.004, W=0.4, H=0.9)
sg.build("Src_Ground_Manifold", root, props={"title": "Ground-source collector", "spec": "16 x 120 m boreholes, 25 % MEG brine, manifold chamber",
                                             "live": "T_src,T_ground"})
sw = MB()
pt.pipe(sw, [(30.0, 6.0, -0.4), (24.0, 6.0, -0.4), (24.0, 6.0, 0.8), (20.2, 6.0, 0.8), (20.2, -2.0, 0.8)], 0.11, P["paint_blue"], flow_name="river_in")
pt.strainer(sw, align((1, 0, 0), (22.5, 6.0, 0.8)), 0.11)
pt.inline_pump(sw, T(21.3, 6.0, 0.8), 0.1, 0.3, 0.42)
pt.gasketed_phe(sw, T(19.6, -2.8, 0.08) @ R(0, 0, 90), plates=80, pitch=0.004, W=0.45, H=1.0)
sw.add(box(3.0, 2.0, 0.6, center=(30.5, 6.0, -0.2)), P["concrete"])
sw.build("Src_Water_Intake", root, props={"title": "River abstraction", "spec": "Screened intake, 5 kg/s, gasketed plate HX isolates river water",
                                          "live": "T_src,T_ground"})
anchor("Source", (23.0, 0.0, 3.0))

_scr.hide_render = True
export(HERE, "greenhouse", camera={"pos": (34.0, -30.0, 18.0), "target": (2.0, 0.0, 2.5), "lens": 30})
print("done")
