"""Island wind-hydrogen harbour: 3 x 6.2 MW wind turbines, 8 MW PEM plant (4 x 2 MW containers), two-stage
compression to 350 bar, 188.5 m3 tube storage (8 x 23.6 m3), bunkering skid and a ro-ro ferry at the quay.
Named parts: WTG_{k}_Yaw / WTG_{k}_Rotor, PEM_{k}, Store_Vessels, Bunker_Arm, Ferry.
Run: blender -b --factory-startup -P create_hydrogen_asset.py
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / 'Tools'))

from blendlib import parts as pt  # noqa: E402
from blendlib.core import (MB, R, T, align, anchor, box, cyl, empty, export, extrude, lathe, loft, mat, pbr, reset,  # noqa: E402
                           sphere, tex_fins, texture, torus, tube)

reset(HERE / "textures")
P = pt.init()
rgb, nrm = tex_fins(512, 512, 6)
P["fins"] = mat("Aluminium fin pack", "#aeb6bb", 0.7, 0.42, tex=texture("fins", rgb), normal=texture("fins_n", nrm), tex_scale=4.0)
P["sea"] = mat("Sea", "#1d3a4a", 0.2, 0.06, coat=1.0)
P["hull"] = pbr("Hull paint dark blue", "paint_worn", "#1c2a3e", 2.5, tint="soft", rough=0.4, normal_strength=0.3, metal=0.0, coat=0.3)
P["boot"] = pbr("Antifouling red", "paint_worn", "#8c2219", 2.0, tint="soft", rough=0.6, metal=0.0)
P["super"] = pbr("Superstructure white", "paint_worn", "#e9e8e2", 2.0, tint="subtle", rough=0.35, metal=0.0, normal_strength=0.2)
P["windows"] = mat("Bridge glazing", "#0f1d29", 0.6, 0.05, coat=1.0)
P["funnel"] = pbr("Funnel teal", "paint_worn", "#1f6f74", 1.5, tint="subtle", rough=0.35, metal=0.0)
P["lifeboat"] = mat("Lifeboat orange", "#f06a12", 0.0, 0.4, coat=0.5)
P["quay"] = pbr("Quay concrete", "concrete_slab", "#a8a49b", 4.0, tint="full", metal=0.0)
P["container"] = pbr("Container RAL9006", "corrugated", "#b8bcbd", 1.0, tint="soft", metal=0.6, rough=0.4)
P["container_g"] = pbr("Container green", "corrugated", "#2f5d4a", 1.0, tint="soft", metal=0.3, rough=0.45)
P["h2_yellow"] = pbr("Hydrogen pipe yellow", "paint_worn", "#d9a400", 1.0, tint="subtle", rough=0.4, metal=0.0)
P["warn_h2"] = P.get("warn_h2")

root = empty("HydrogenHarbour", props={"title": "Island wind-hydrogen harbour", "spec": "Stornoway, Isle of Lewis · ERA5 2023"})

# ------------------------------------------------------------------ terrain, sea, quay
g = MB()
g.add(box(1600, 902, 0.2, center=(0, 449, -0.1), bevel=0.0), P["grass"])
# hill behind the plant for the turbines (raised plateau with slopes)
hill = []
for k in range(41):
    x = -800 + 40 * k
    hill.append((x, 0))
g.add(extrude([(-800, 150), (800, 150), (800, 900), (-800, 900)], 0.1, z0=0.0), P["grass"])
for (cx, cy, r, h) in ((-300, 420, 220, 22), (0, 500, 260, 28), (320, 450, 230, 24)):
    prof = [(0, h)] + [(r * (k / 10), h * (1 - (k / 10) ** 2)) for k in range(1, 11)]
    g.add(lathe(prof[::-1] if False else [(r * (1 - k / 10), h * (1 - (1 - k / 10) ** 2)) for k in range(11)][::-1] + [], 48),
          P["grass"], T(cx, cy, 0))
g.add(box(140, 60, 0.12, center=(10, 18, 0.06), bevel=0.0), P["gravel"])
g.add(box(1600, 1200, 0.1, center=(0, -616, -1.2), bevel=0.0), P["sea"])
g.add(box(1600, 14, 4.0, center=(0, -9.0, -2.0), bevel=0.0), P["quay"])
g.build("Terrain", root)
q = MB()
q.add(box(180, 14, 4.2, center=(0, -9.0, -0.0), bevel=0.15), P["quay"])
for k in range(18):
    x = -85 + k * 10
    q.add(lathe([(0, 0), (0.25, 0), (0.25, 0.5), (0.35, 0.65), (0.3, 0.75), (0, 0.75)], 24), P["paint_dark"], T(x, -14.4, 2.1))
    q.add(box(1.2, 0.6, 2.4, center=(x + 5, -16.3, 0.4), bevel=0.15), P["rubber"])
q.add(box(180, 0.25, 0.3, center=(0, -15.9, 2.25)), P["paint_yellow"])
q.build("Quay", root)

# ------------------------------------------------------------------ ferry (lofted hull + superstructure)
fe = MB()
Lh, B = 96.0, 17.0
x0 = 10.0
fy = -26.5
fb = MB()
pt.ship_hull(fe, fb, x0, Lh, B, fy, mat_top=P["hull"], mat_bot=P["boot"])
fb.build("Ferry_Underwater", root, props={"noShadow": 1})
# superstructure decks with window bands
for d, (xa, xb, hgt) in enumerate(((20, 82, 3.0), (28, 78, 3.0), (52, 76, 3.2))):
    z0 = 5.65 + d * 3.0
    fe.add(box(xb - xa, B - 1.6 - d * 1.2, hgt, center=((xa + xb) / 2, fy, z0 + hgt / 2), bevel=0.25), P["super"])
    for side in (-1, 1):
        fe.add(box(xb - xa - 2.0, 0.05, 1.0, center=((xa + xb) / 2, fy + side * ((B - 1.6 - d * 1.2) / 2 + 0.01), z0 + 1.7), bevel=0.0),
               P["windows"])
fe.add(box(9.0, B + 2.4, 2.6, center=(71.0, fy, 16.0), bevel=0.2), P["super"])      # bridge with wings
fe.add(box(0.05, B + 2.0, 1.1, center=(75.53, fy, 16.4), bevel=0.0), P["windows"])
fe.add(rbox(5.0, 3.6, 7.0, 1.4, 6, center=(-18.0, fy, 20.0)) if False else box(5.0, 3.8, 5.0, center=(40.0, fy, 17.4), bevel=0.8), P["funnel"])
fe.add(cyl(0.25, 9.0, 12, 17.3), P["paint_grey"], T(68.0, fy, 0))
fe.add(box(3.6, 0.2, 0.3, center=(68.0, fy, 25.5)), P["paint_grey"])
for xb_ in (34, 48, 60):
    for side in (-1, 1):
        fe.add(lathe([(0, 0), (1.1, 0.1), (1.2, 1.0), (0.8, 1.6), (0, 1.7)], 16), P["lifeboat"],
               T(xb_, fy + side * (B / 2 - 1.2), 11.8) @ R(0, 90, 0) @ S_(1.0) if False else T(xb_, fy + side * (B / 2 - 1.2), 11.8) @ R(0, 90, 0))
fe.add(box(0.4, 9.0, 4.0, center=(x0 + 0.3, fy, 7.6)), P["paint_dark"])         # stern door
fe.build("Ferry", root, props={"title": "Hydrogen ferry (hypothetical)", "spec": "96 m ro-pax analogue, fuel-cell propulsion, 1.2 t H₂/day bunker",
                               "live": "ferry_soc,bunker"})
anchor("Ferry", (60.0, fy, 27.0))

# ------------------------------------------------------------------ hydrogen plant on the quay apron
PX, PY = -30.0, 12.0
pl = MB()
for k in range(4):
    x = PX + k * 3.6
    pt.iso_container(pl, T(x, PY, 0.1) @ R(0, 0, 90), L=12.19, W=2.44, H=2.9, mat=P["container"])
    # roof dry coolers
    stat = MB()
    pt.ashp_unit(stat, T(x, PY - 2.0, 3.0) @ R(0, 0, 90), L=4.0, W=1.8, H=1.2, nfans=2, D_fan=0.8, casing=P["paint_grey"])
    stat.build(f"PEM_{k + 1}_Cooler", root)
    pt.sign(pl, T(x, PY - 6.12, 1.6) @ R(0, 0, 0), "warn_h2", 0.3)
pl.build("PEM_Containers", root, props={"title": "PEM electrolysers 4 x 2 MW", "spec": "412 cells x 1250 cm², Nafion 115, 30 bar(g) cathode, 65 °C",
                                         "live": "P_ely,n_on,V_cell,T_stack,h2_rate"})
for k in range(4):
    anchor(f"PEM{k + 1}", (PX + k * 3.6, PY, 6.0))
sk = MB()
for k, nm in enumerate(("sep_h2", "sep_o2")):
    pt.vessel_vertical(sk, T(PX + 16.0 + k * 2.0, PY - 3.0, 0.1), 1.0, 2.8, legs=4, leg_h=0.5, mat=P["stainless"],
                       nozzles=[("in", 0.7, 180, 0.08), ("out", "top", 0, 0.06)])
for k in range(2):
    pt.vessel_vertical(sk, T(PX + 16.0 + k * 1.4, PY + 3.0, 0.1), 0.7, 3.6, legs=3, leg_h=0.4, mat=P["paint_grey"],
                       nozzles=[("in", 0.1, 180, 0.06), ("out", "top", 0, 0.06)])
pt.iso_container(sk, T(PX + 26.0, PY, 0.1) @ R(0, 0, 90), L=12.19, W=2.44, H=2.9, mat=P["container_g"])
for k in range(4):
    sk.add(box(1.4, 0.05, 0.9, center=(PX + 24.8 + (k % 2) * 2.4, PY - 6.12 + 0.0, 1.6 + (k // 2) * 1.0)), P.get("louvre", P["paint_grey"]))
pt.sign(sk, T(PX + 26.0, PY - 6.12, 2.4), "warn_h2", 0.3)
# transformer / rectifier skids
for k in range(2):
    sk.add(box(3.2, 2.4, 2.6, center=(PX - 8.0, PY - 4.0 + k * 4.2, 1.4), bevel=0.06), P["paint_grey"])
    for f in range(12):
        sk.add(box(0.05, 2.2, 1.8, center=(PX - 9.7 - 0.0, PY - 4.0 + k * 4.2, 1.4), bevel=0.0), P["paint_grey"],
               T(-0.0, (f - 6) * 0.17, 0) @ R(0, 0, 90) @ T(0, 0, 0) if False else T(0, 0, 0))
    pt.sign(sk, T(PX - 8.0, PY - 5.21 + k * 4.2, 1.8), "warn_electric", 0.3)
sk.build("Process_Skids", root, props={"title": "Gas separators, dryer, compressor container, rectifiers",
                                         "spec": "Two-stage intercooled diaphragm compressor 30 → 350 bar", "live": "P_comp,store_P"})
anchor("Compressor", (PX + 26.0, PY, 5.0))

# storage: 8 vessels in two tiers (23.6 m3 each, D 1.42 m, shell 15.5 m)
sv = MB()
SX, SY = 20.0, 10.0
for tier in range(2):
    for k in range(4):
        y = SY + k * 1.7
        z = 0.9 + tier * 1.75
        sv.add(lathe(pt.dished_profile(0.71, 0.0, 15.5, 0.25, 10), 40), P["paint_white"], T(SX - 7.75, y, z) @ R(0, 90, 0))
for x in (SX - 6.0, SX, SX + 6.0):
    sv.add(box(0.3, 7.6, 0.3, center=(x, SY + 2.55, 0.15)), P["galv"])
    for tier in range(2):
        sv.add(box(0.25, 7.6, 0.25, center=(x, SY + 2.55, 0.25 + tier * 1.75)), P["galv"])
    for y in (SY - 1.0, SY + 6.1):
        sv.add(box(0.25, 0.25, 3.6, center=(x, y, 1.8)), P["galv"])
pt.nameplate(sv, T(SX - 7.5, SY - 0.72, 1.2), 0.4, 0.22, key="plate_tank")
pt.sign(sv, T(SX - 3.0, SY - 1.13, 1.4), "warn_h2", 0.35)
sv.add(cyl(0.12, 12.0, 16, 0.0), P["stainless"], T(SX + 10.0, SY + 2.5, 0))      # vent stack
sv.build("Store_Vessels", root, props={"title": "Hydrogen storage 188.5 m³", "spec": "8 x 23.6 m³ Type I vessels, 350 bar, ≈ 4.4 t at full",
                                        "live": "store_P,store_kg,store_T"})
anchor("Store", (SX, SY + 2.5, 5.0))
# firewall
fw = MB()
fw.add(box(0.3, 9.0, 4.0, center=(SX - 9.5, SY + 2.5, 2.0), bevel=0.04), P["concrete"])
fw.build("Firewall", root)

# bunkering skid and loading arm on the quay edge
bk = MB()
bk.add(box(3.0, 2.0, 2.4, center=(6.0, -12.5, 2.1 + 1.2), bevel=0.05), P["paint_grey"])
bk.add(box(0.8, 0.02, 0.5, center=(6.0, -13.51, 3.6)), P["hmi"])
pt.sign(bk, T(5.0, -13.51, 3.4), "warn_h2", 0.25)
arm = [(7.0, -12.5, 4.5), (7.0, -12.5, 9.0), (7.0, -17.5, 10.5), (7.0, -18.6, 7.0)]
pt.pipe(bk, arm, 0.2, P["h2_yellow"], bend=0.6, flow_name="bunker_hose")
bk.build("Bunker_Arm", root, props={"title": "Bunkering skid + loading arm", "spec": "Cascade + booster, 26.7 kg/min, breakaway coupling", "live": "bunker"})
anchor("Bunker", (7.0, -15.0, 11.5))
# hydrogen pipe rack: PEM -> separators -> compressor -> storage -> bunkering
hp = MB()
pt.pipe(hp, [(PX + 11.0, PY - 6.5, 3.2), (PX + 16.0, PY - 6.5, 3.2), (PX + 16.0, PY - 3.0, 3.2), (PX + 22.0, PY - 3.0, 3.2), (PX + 22.0, PY - 6.5, 3.2),
             (PX + 26.0, PY - 6.5, 3.2)], 0.08, P["h2_yellow"], flow_name="h2_lp", label="pipe_h2", label_at=0.3)
pt.pipe(hp, [(PX + 30.0, PY - 6.5, 3.2), (SX - 9.0, PY - 6.5, 3.2), (SX - 9.0, SY + 2.5, 3.2), (SX - 8.2, SY + 2.5, 3.2)], 0.06, P["h2_yellow"],
        flow_name="h2_hp", label="pipe_h2", label_at=0.5)
pt.pipe(hp, [(SX - 8.2, SY - 0.5, 0.6), (8.0, SY - 0.5, 0.6), (8.0, -12.5, 0.6), (7.0, -12.5, 2.1)], 0.06, P["h2_yellow"], flow_name="h2_bunker",
        label="pipe_h2", label_at=0.45)
for x in range(-20, 20, 6):
    hp.add(box(0.2, 0.2, 3.1, center=(x, PY - 6.5, 1.55)), P["galv"])
hp.build("H2_Pipework", root)
anchor("SP_C1", (PX + 11.5, PY - 6.5, 3.6))
anchor("SP_C2", (PX + 20.0, PY - 3.0, 3.6))
anchor("SP_C3", (PX + 26.0, PY - 6.0, 4.0))
anchor("SP_C4", (PX + 27.5, PY - 6.0, 4.0))
anchor("SP_C5", (PX + 29.0, PY - 6.0, 4.0))
anchor("SP_C6", (SX - 9.0, PY - 6.5, 3.6))
anchor("SP_C7", (SX - 2.0, SY - 0.8, 4.2))
anchor("SP_C8", (7.0, -17.0, 10.8))

# substation and fence
ss = MB()
ss.add(box(8.0, 6.0, 0.3, center=(-55.0, 20.0, 0.15)), P["concrete"])
ss.add(box(3.6, 2.6, 3.2, center=(-55.0, 20.0, 1.9), bevel=0.05), P["paint_grey"])
for k in range(14):
    ss.add(box(0.06, 0.5, 2.6, center=(-53.0, 18.9 + k * 0.17, 1.9), bevel=0.0), P["paint_grey"])
for k in range(3):
    ss.add(lathe([(0.12, 0), (0.18, 0.1), (0.12, 0.2), (0.18, 0.3), (0.12, 0.4), (0.18, 0.5), (0.1, 0.9), (0, 0.95)], 16), P["plastic_grey"],
           T(-56.0 + k * 1.0, 20.0, 3.5))
for (x, y) in ((-60, 16), (-50, 16), (-60, 24), (-50, 24)):
    ss.add(box(0.3, 0.3, 9.0, center=(x, y, 4.5)), P["galv"])
ss.add(box(10.4, 0.3, 0.3, center=(-55.0, 16.0, 9.0)), P["galv"])
ss.add(box(10.4, 0.3, 0.3, center=(-55.0, 24.0, 9.0)), P["galv"])
pt.sign(ss, T(-55.0, 18.68, 2.2), "warn_electric", 0.3)
ss.build("Substation", root, props={"title": "33/11 kV substation + 5 MW interconnector", "live": "export,import_,curtail"})
anchor("Grid", (-55.0, 20.0, 11.0))
fn = MB()
pt.fence(fn, [(-62, -2, 0.1), (36, -2, 0.1), (36, 30, 0.1), (-62, 30, 0.1), (-62, -2, 0.1)], 2.4, 3.0)
fn.build("Fence", root)

# ------------------------------------------------------------------ wind turbines on the hill
WTG = [(-300.0, 420.0, 22.0), (0.0, 500.0, 28.0), (320.0, 450.0, 24.0)]
for k, (x, y, z) in enumerate(WTG):
    stat, nacm = MB(), MB()
    pt.wind_turbine(stat, None, nacm, T(x, y, z - 0.5), hub_h=115.0, D=170.0)
    stat.build(f"WTG_{k + 1}_Tower", root, props={"title": f"Wind turbine {k + 1}", "spec": "6.2 MW, Ø170 m rotor, 115 m hub",
                                                  "live": f"wtg{k + 1},rpm{k + 1},v_hub"})
    yaw = empty(f"WTG_{k + 1}_Yaw", (x, y, z - 0.5 + 115.0 - 2.6), root)
    nac_obj = nacm.build(f"WTG_{k + 1}_Nacelle", yaw)
    mount = empty(f"WTG_{k + 1}_Mount", (10.0, 0, 2.6), yaw, rot=(0, -90, 0))
    rot = MB()
    pt.wtg_rotor(rot, 170.0)
    rot.build(f"WTG_{k + 1}_Rotor", mount)
    anchor(f"WTG{k + 1}", (x, y, z + 210.0))

import bpy  # noqa: E402
export(HERE, "hydrogen_microgrid", camera={"pos": (-95.0, -120.0, 55.0), "target": (15.0, 15.0, 14.0), "lens": 28})
print("done")
