"""Commercial heat pump retrofit site: 1970s office block, fenced plant compound with four 40 kW
R290 modules, two 100 m3 thermal stores, pump-room container, transformer kiosk and pipe bridge.

Volumes and ratings follow the annual model (annual_sim.py): 4 x 40 kW modules, 2 x 100 m3 stores
(D 4.6 m x 6.5 m shell = 108 m3 each), 60 kWe connection, 6,000 m2 three-storey office.
Run: blender -b --factory-startup -P create_retrofit_asset.py
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / 'Tools'))

from blendlib import parts as pt  # noqa: E402
from blendlib.core import (MB, R, T, anchor, box, cyl, empty, export, lathe, mat, reset, tex_fins, tex_louvre,  # noqa: E402
                           texture, torus, tube)

reset(HERE / "textures")
P = pt.init()
rgb, nrm = tex_fins(512, 512, 6)
P["fins"] = mat("Aluminium fin pack", "#aeb6bb", 0.7, 0.42, tex=texture("fins", rgb), normal=texture("fins_n", nrm), tex_scale=4.0)
lr, ln = tex_louvre()
P["louvre"] = mat("Louvred panel", "#c8cac6", 0.0, 0.45, tex=texture("louvre", lr * 0.8), normal=texture("louvre_n", ln), tex_scale=2.0)
# chain-link fence texture (alpha)
w = 256
x = np.arange(w)[None, :] * np.ones((w, 1))
y = np.arange(w)[:, None] * np.ones((1, w))
wire = (np.abs(((x + y) % 32) - 16) < 1.6) | (np.abs(((x - y) % 32) - 16) < 1.6)
rgba = np.dstack([np.full((w, w), 0.62)] * 3 + [wire.astype(float)])
P["fence"] = mat("Chain-link mesh", "#9ea4a6", 0.8, 0.5, tex=texture("chainlink", rgba), alpha_clip=True, tex_scale=6.0)
from blendlib.core import pbr  # noqa: E402
P["precast"] = pbr("Precast concrete spandrel", "concrete_smooth", "#c7c0b2", 2.0, tint="full", metal=0.0)
P["curtain"] = mat("Glazing (low-e)", "#5f7d8c", 0.6, 0.08, alpha=0.75)
P["mullion"] = mat("Bronze anodised mullion", "#4a4036", 0.8, 0.35)
P["tarmac"] = P["asphalt"]

root = empty("RetrofitSite", props={"title": "Office heat pump retrofit (Edinburgh)",
                                     "spec": "4 x 40 kW R290 cascade, 2 x 100 m³ TES, 60 kWe connection"})

# ------------------------------------------------------------- ground
gnd = MB()
gnd.add(box(110, 70, 0.1, center=(-15, 0, -0.05), bevel=0.0), P["grass"])
gnd.add(box(36, 26, 0.12, center=(13.5, 0, 0.0)), P["tarmac"])
gnd.add(box(70, 6, 0.12, center=(-30, -23, 0.0)), P["tarmac"])
gnd.build("Ground", root)

# ------------------------------------------------------------- office block
BX0, BX1, BY0, BY1 = -62.0, -5.0, -17.5, 17.5
FLOORS, FH = 3, 3.8
bld = MB()
H_b = FLOORS * FH
bld.add(box(BX1 - BX0, BY1 - BY0, 0.4, center=((BX0 + BX1) / 2, 0, 0.2)), P["concrete"])
for f in range(FLOORS + 1):
    z = 0.4 + f * FH
    if f < FLOORS:
        bld.add(box(BX1 - BX0 + 0.3, BY1 - BY0 + 0.3, 0.35, center=((BX0 + BX1) / 2, 0, z + 0.175)), P["precast"])
    else:
        # parapet ring with coping around a bitumen-membrane roof
        for (cx, cy, sx, sy) in (((BX0 + BX1) / 2, BY0, BX1 - BX0 + 0.3, 0.3), ((BX0 + BX1) / 2, BY1, BX1 - BX0 + 0.3, 0.3),
                                 (BX0, 0, 0.3, BY1 - BY0 + 0.3), (BX1, 0, 0.3, BY1 - BY0 + 0.3)):
            bld.add(box(sx, sy, 1.2, center=(cx, cy, z + 0.6)), P["precast"])
            bld.add(box(sx + 0.06, sy + 0.06, 0.05, center=(cx, cy, z + 1.225)), P["alu"])
    if f < FLOORS:
        # spandrel band and glazing band on all four faces
        for (ax, a0, a1, c, n) in (("x", BX0, BX1, BY0, -1), ("x", BX0, BX1, BY1, 1), ("y", BY0, BY1, BX0, -1), ("y", BY0, BY1, BX1, 1)):
            L = a1 - a0
            mid = (a0 + a1) / 2
            if ax == "x":
                bld.add(box(L, 0.25, 1.0, center=(mid, c, z + 0.35 + 0.5)), P["precast"])
                bld.add(box(L, 0.04, FH - 1.4, center=(mid, c - n * 0.08, z + 1.35 + (FH - 1.4) / 2)), P["curtain"])
                for k in range(int(L / 1.5) + 1):
                    bld.add(box(0.07, 0.16, FH - 1.4, center=(a0 + k * 1.5, c, z + 1.35 + (FH - 1.4) / 2)), P["mullion"])
                bld.add(box(L, 0.16, 0.06, center=(mid, c, z + 1.35 + 0.9)), P["mullion"])
            else:
                bld.add(box(0.25, L, 1.0, center=(c, mid, z + 0.35 + 0.5)), P["precast"])
                bld.add(box(0.04, L, FH - 1.4, center=(c - n * 0.08, mid, z + 1.35 + (FH - 1.4) / 2)), P["curtain"])
                for k in range(int(L / 1.5) + 1):
                    bld.add(box(0.16, 0.07, FH - 1.4, center=(c, a0 + k * 1.5, z + 1.35 + (FH - 1.4) / 2)), P["mullion"])
                bld.add(box(0.16, L, 0.06, center=(c, mid, z + 1.35 + 0.9)), P["mullion"])
# solid interior volume behind glazing (dark) and roof
bld.add(box(BX1 - BX0 - 0.6, BY1 - BY0 - 0.6, H_b, center=((BX0 + BX1) / 2, 0, 0.4 + H_b / 2)), mat("Interior", "#2b3035", 0, 0.9))
bld.add(box(BX1 - BX0, BY1 - BY0, 0.25, center=((BX0 + BX1) / 2, 0, 0.4 + H_b + 0.1)), P["roof"])
# roof plant: AHU and lift motor room
bld.add(box(9, 3.2, 2.4, center=(-40, 6, 0.4 + H_b + 1.4), bevel=0.05), P["paint_grey"])
bld.add(box(5, 5, 3.0, center=(-25, -6, 0.4 + H_b + 1.7), bevel=0.05), P["precast"])
# entrance canopy
bld.add(box(8, 3.0, 0.3, center=(-33, BY0 - 1.5, 4.0)), P["mullion"])
for xx in (-36.8, -29.2):
    bld.add(cyl(0.12, 3.9, 16), P["stainless"], T(xx, BY0 - 2.8, 0))
bld.build("Office_Building", root, props={"title": "1970s office block (heat demand)", "spec": "6,000 m², 3 storeys, HLC ≈ 9.7 kW/K, existing 65 °C radiators",
                                          "live": "T_room,Q_emit,T_flow,T_ret"})
anchor("Building", (-20, 0, 0.4 + H_b + 2.5))

# ------------------------------------------------------------- compound
fn = MB()
pt.fence(fn, [(2.0, -11.5, 0), (25.5, -11.5, 0), (25.5, 11.5, 0), (2.0, 11.5, 0), (2.0, 2.0, 0)], 2.4, 2.6)
fn.build("Compound_Fence", root)
pl = MB()
pl.add(box(15.5, 3.4, 0.25, center=(10.5, -7.6, 0.125), bevel=0.03), P["slab"])
pl.add(box(13.0, 9.0, 0.3, center=(17.6, 3.6, 0.15), bevel=0.03), P["slab"])
pl.add(box(22.5, 21.5, 0.05, center=(13.75, 0, 0.04), bevel=0.0), P["gravel"])
pl.build("Compound_Plinths", root)

MOD_X = [4.6, 8.4, 12.2, 16.0]
for j, mx in enumerate(MOD_X):
    stat, = (MB(),)
    hubs = pt.ashp_unit(stat, T(mx, -7.6, 0.25) @ R(0, 0, 90), L=2.6, W=1.2, H=1.95, nfans=2, D_fan=0.72,
                        casing=P["paint_white"], louvre=P["louvre"])
    pt.sign(stat, T(mx - 0.62, -7.6 + 0.9, 0.25 + 1.0) @ R(0, 0, 180), "warn_flammable", 0.12)
    pt.nameplate(stat, T(mx + 0.62 + 0.004, -7.6 + 0.6, 0.25 + 0.45) @ R(0, 0, 90), 0.16, 0.09, key="plate_hp")
    stat.build(f"Module_{j + 1}", root, props={"title": f"R290 monobloc module {j + 1}",
                                                "spec": "40 kW at A7W55, inverter scroll 36 m³/h, 2 x EC fans, lead/lag rotation",
                                                "live": f"mod{j + 1}_run,f_mod,cop"})
    for k, Mh in enumerate(hubs):
        rot = MB()
        pt.fan_rotor(rot, T(0, 0, 0), 0.72, 5)
        o = rot.build(f"Module_{j + 1}_Fan_{k + 1}", root)
        o.matrix_world = Mh
anchor("Modules", (10.3, -7.6, 3.2))

# thermal stores (2 x 100 m3) with ladders, bands
TES = [(15.0, 3.6, "A"), (20.6, 3.6, "B")]
st = MB()
for cx, cy, nm in TES:
    D, Hs = 4.6, 6.5
    pts_ = pt.storage_cylinder(st, T(cx, cy, 0.3), D, Hs, P["alu_clad"],
                               ports=[("top", 0.93, 200, 0.15), ("bot", 0.06, 200, 0.15)], feet=False)
    for z in range(1, 20):
        st.add(cyl(0.015, 0.45, 8), P["galv"], T(cx + D / 2 + 0.25, cy - 0.22, 0.3 + z * 0.35) @ R(90, 0, 0))
    for dy in (-0.22, 0.23):
        st.add(box(0.06, 0.02, Hs + 1.1, center=(cx + D / 2 + 0.25, cy + dy, 0.3 + (Hs + 1.1) / 2)), P["galv"])
    for k in range(6):
        a = 2 * math.pi * k / 6
        st.add(box(0.05, 0.05, 1.0, center=(cx + (D / 2 - 0.1) * math.cos(a), cy + (D / 2 - 0.1) * math.sin(a), 0.3 + Hs + 0.65)),
               P["paint_yellow"])
    st.add(torus(D / 2 - 0.1, 0.025, 48, 6), P["paint_yellow"], T(cx, cy, 0.3 + Hs + 1.15))
    if nm == "A":
        tesA = pts_
    else:
        tesB = pts_
    anchor(f"Store{nm}", (cx, cy, 0.3 + Hs + 1.6))
    ang = -0.8
    import math as _m
    Mp = T(cx + (D / 2 + 0.01) * _m.cos(ang), cy + (D / 2 + 0.01) * _m.sin(ang), 1.6) @ R(0, 0, _m.degrees(ang) + 90)
    pt.nameplate(st, Mp, 0.32, 0.18, key="plate_tank")
    pt.sign(st, Mp @ T(0.3, 0, 0), "warn_pressure", 0.18)
st.build("Thermal_Stores", root, props={"title": "Thermal stores 2 x 100 m³", "spec": "Series-connected, stratified, 200 mm mineral wool, aluminium cladding",
                                        "live": "tes_soc,tes_loss"})
for cx, cy, nm in TES:
    for j in range(12):
        bb = MB()
        za = 0.3 + 0.12 + 0.07 + (6.5 - 0.2) * (11 - j) / 12
        bb.add(lathe([(2.3 + 0.006, za + 0.01), (2.3 + 0.012, za + 0.02), (2.3 + 0.012, za + 6.3 / 12 - 0.02), (2.3 + 0.006, za + 6.3 / 12 - 0.01)],
                     72, math.radians(282), math.radians(346)), mat("Store band", "#9aa3aa", 0, 0.5), T(cx, cy, 0))
        bb.build(f"Store{nm}_Band_{j + 1}", root, props={"noShadow": 1})

# pump-room container, transformer kiosk
ct = MB()
pt.iso_container(ct, T(7.2, 4.6, 0.25) @ R(0, 0, 0), mat=mat("Container RAL7016", "#3b4248", 0.3, 0.5))
for k in range(3):
    ct.add(box(0.8, 0.04, 0.5, center=(5.2 + k * 1.6, 4.6 - 1.24, 2.1)), P["louvre"])
ct.build("Pump_Room", root, props={"title": "Pump room container", "spec": "Primary, store and building circuit pumps; plate HX; controls",
                                    "live": "W_pump,T_flow"})
tk = MB()
pt.transformer_kiosk(tk, T(5.0, -0.8, 0.0))
pt.sign(tk, T(5.0 - 0.6, -0.8 - 0.92, 1.5), "warn_electric", 0.2)
tk.build("Transformer_Kiosk", root, props={"title": "Package substation", "spec": "Heating plant connection capped at 60 kWe",
                                            "live": "W_total,over_cap"})
anchor("Grid", (5.0, -0.8, 3.0))

# ------------------------------------------------------------- pipework
pp = MB()
hdr_y, hdr_z = -5.4, 0.9
# module headers (flow/return) along the plinth
for j, mx in enumerate(MOD_X):
    pt.pipe(pp, [(mx + 0.25, -6.9, 0.6), (mx + 0.25, hdr_y, 0.6), (mx + 0.25, hdr_y, hdr_z)], 0.054, P["steel"], insul=0.025)
    pt.pipe(pp, [(mx - 0.25, -6.9, 0.45), (mx - 0.25, hdr_y - 0.35, 0.45), (mx - 0.25, hdr_y - 0.35, hdr_z - 0.35)], 0.054, P["steel"], insul=0.025)
pt.pipe(pp, [(MOD_X[0] - 0.4, hdr_y, hdr_z), (MOD_X[-1] + 0.6, hdr_y, hdr_z), (MOD_X[-1] + 0.6, hdr_y, 1.6),
             (MOD_X[-1] + 0.6, 0.6, 1.6), (tesA["top"][0] - 2.6, 0.6, 1.6), (tesA["top"][0] - 2.6, 0.6, tesA["top"][2] - 0.2),
             (tesA["top"][0] - 1.0, 0.6, tesA["top"][2] - 0.2), (tesA["top"][0] - 1.0, tesA["top"][1] - 1.6, tesA["top"][2] - 0.2)],
        0.1, P["steel"], insul=0.04, flow_name="p_charge", label="pipe_lthw_flow", label_at=0.35)
pt.pipe(pp, [tesB["bot"], (tesB["bot"][0], tesB["bot"][1], 0.6), (tesB["bot"][0], 0.0, 0.6), (MOD_X[-1] + 1.0, 0.0, 0.6),
             (MOD_X[-1] + 1.0, hdr_y - 0.35, 0.6), (MOD_X[-1] + 1.0, hdr_y - 0.35, hdr_z - 0.35), (MOD_X[0] - 0.4, hdr_y - 0.35, hdr_z - 0.35)],
        0.1, P["steel"], insul=0.04, flow_name="p_return", label="pipe_lthw_return", label_at=0.6)
# series link A bottom -> B top
pt.pipe(pp, [tesA["bot"], (tesA["bot"][0], tesA["bot"][1] + 2.8, tesA["bot"][2]), (tesA["bot"][0] + 3.0, tesA["bot"][1] + 2.8, tesA["bot"][2]),
             (tesA["bot"][0] + 3.0, tesA["bot"][1] + 2.8, tesB["top"][2]), (tesB["top"][0], tesB["top"][1] + 2.8, tesB["top"][2]),
             tesB["top"]], 0.1, P["steel"], insul=0.04, flow_name="p_series")
# building circuit: container -> pipe bridge -> building wall
for dz, nm in ((3.9, "b_flow"), (3.5, "b_ret")):
    pt.pipe(pp, [(4.2, 4.6, 2.85), (4.2, 4.6, dz), (-5.0, 4.6, dz), (-5.3, 4.6, dz)], 0.1, P["steel"], insul=0.04, flow_name=nm,
            label="pipe_lthw_flow" if nm == "b_flow" else "pipe_lthw_return", label_at=0.5)
pt.pipe(pp, [tesA["top"], (tesA["top"][0], tesA["top"][1], 7.3), (9.8, tesA["top"][1], 7.3), (9.8, 4.6, 7.3), (9.8, 4.6, 2.85)],
        0.1, P["steel"], insul=0.04, flow_name="p_discharge")
for xx in (-1.5, 1.5):
    pp.add(box(0.15, 0.15, 4.2, center=(xx, 4.6, 2.1)), P["galv"])
    pp.add(box(0.2, 0.9, 0.12, center=(xx, 4.6, 3.3)), P["galv"])
pp.build("Pipework", root, props={"title": "Primary and building pipework", "spec": "DN100 insulated steel; pipe bridge to plant room",
                                  "live": "W1_T,W2_T,T_flow,T_ret"})

# state points around module 1 (lead module, rotates in the simulation)
m0 = MOD_X[0]
anchor("SP_1", (m0 - 0.4, -7.0, 1.2))
anchor("SP_2", (m0 - 0.3, -8.4, 0.9))
anchor("SP_3", (m0 + 0.1, -8.4, 1.4))
anchor("SP_4", (m0 + 0.35, -8.0, 0.7))
anchor("SP_5", (m0 + 0.6, -7.0, 1.0))
anchor("SP_W1", (m0 - 0.4, hdr_y - 0.35, hdr_z))
anchor("SP_W2", (m0 + 0.6, hdr_y, hdr_z + 0.4))

export(HERE, "retrofit_plant", camera={"pos": (36.0, -34.0, 22.0), "target": (6.0, 0.0, 3.0), "lens": 30})
print("done")
