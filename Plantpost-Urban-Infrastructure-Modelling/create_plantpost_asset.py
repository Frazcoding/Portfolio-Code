"""Plantpost multifunctional street post in a pavement setting.

Dimensions from src/config.py: 4.5 m post, 2.0 m PV canopy (3.14 m2), four planter tiers at 1/2/3/4 m
(0.25 m2 plan each), 150 L tank in a 1.0 m base column (0.15 m2 footprint), 8 mm PE drip riser.
Named parts bound to the annual model: PV_Canopy, LED_Ring, Tank_Level, Tier_{1..4}_Plants, Riser.
Run: blender -b --factory-startup -P create_plantpost_asset.py
"""
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / 'Tools'))

from blendlib import parts as pt  # noqa: E402
from blendlib.core import (MB, R, T, anchor, box, cyl, decal_mat, empty, export, extrude, lathe, mat, pbr, reset,  # noqa: E402
                           sphere, tex_pv, texture, torus, tube)

reset(HERE / "textures")
P = pt.init()
P["post"] = pbr("Post powder coat RAL7021", "paint_worn", "#2c3134", 1.0, tint="subtle", rough=0.38, normal_strength=0.2, metal=0.0,
                coat=0.2)
P["corten"] = pbr("Weathering steel planter", "corten", "#6e4127", 0.8, tint="soft", metal=0.3, rough=0.75)
P["paving"] = pbr("Clay paviors", "paving", "#a59484", 1.2, tint="full", metal=0.0)
P["granite"] = pbr("Granite kerb", "granite", None, 0.8, tint=None, metal=0.0)
P["soil"] = pbr("Planter substrate + mulch", "soil", None, 0.5, tint=None, metal=0.0)
P["pv"] = mat("PV cells", "#16233d", 0.4, 0.12, tex=texture("pv_cells", tex_pv(6, 10, 48)), tex_scale=2.6, coat=0.9)
P["led"] = mat("LED diffuser", "#fffaf0", 0.0, 0.3, emit="#ffe9c4", emit_strength=0.0)
P["water"] = mat("Tank water", "#3b7ca8", 0.0, 0.05, alpha=0.7)
P["leaf_b"] = decal_mat("Perennial leaf", "leaf_broad", 0.55)
P["leaf_t"] = decal_mat("Trailing foliage", "leaf_tomato", 0.55)
P["bench_wood"] = pbr("Bench hardwood", "metal_plates", "#8a6545", 0.6, tint="full", metal=0.0, rough=0.6)
P["road_line"] = mat("Road marking", "#ecebe2", 0.0, 0.6)

root = empty("Plantpost", props={"title": "Plantpost street post", "spec": "4.5 m multifunctional post: PV, LED, rain harvesting, 4 planted tiers"})

# ------------------------------------------------------------------ street
s = MB()
s.add(box(10.0, 5.0, 0.15, center=(0, 0.5, -0.075), bevel=0.0), P["paving"])
s.add(box(10.0, 0.3, 0.27, center=(0, -2.15, -0.06), bevel=0.02), P["granite"])
s.add(box(10.0, 7.0, 0.1, center=(0, -5.8, -0.2), bevel=0.0), P["asphalt"])
for k in range(4):
    s.add(box(1.8, 0.12, 0.004, center=(-4 + k * 3.0, -5.8, -0.148), bevel=0.0), P["road_line"])
s.add(box(10.0, 0.1, 0.004, center=(0, -2.5, -0.148), bevel=0.0), mat("Road marking yellow", "#e1b400", 0.0, 0.6))
# bench and litter bin for scale
for x in (2.2, 3.6):
    s.add(box(0.08, 0.45, 0.42, center=(x, 1.6, 0.21)), P["post"])
for k in range(4):
    s.add(box(1.8, 0.09, 0.035, center=(2.9, 1.42 + k * 0.11, 0.45)), P["bench_wood"])
s.add(lathe([(0, 0), (0.22, 0), (0.24, 0.9), (0.2, 0.95), (0, 0.95)], 32), P["post"], T(-2.6, 1.7, 0))
s.build("Street", root)

# ------------------------------------------------------------------ post body
b = MB()
# base column (houses the 150 L tank, battery and controller)
b.add(lathe([(0, 0), (0.29, 0), (0.29, 0.02), (0.27, 0.04), (0.27, 1.0), (0.24, 1.04), (0.11, 1.06), (0, 1.06)], 64), P["post"])
# access hatch with hinges, lock and louvres
hatch = T(0, -0.272, 0.48) @ R(0, 0, 0)
b.add(lathe([(0.272, -0.3), (0.278, -0.3), (0.278, 0.3), (0.272, 0.3)], 32, math.radians(-115), math.radians(-65)), P["post"],
      T(0, 0, 0.48))
for z in (0.25, 0.7):
    b.add(cyl(0.012, 0.06, 12, -0.03), P["stainless"], T(0.11, -0.27, z))
b.add(cyl(0.016, 0.01, 16), P["stainless"], T(-0.08, -0.282, 0.5) @ R(90, 0, 0))
for k in range(6):
    b.add(box(0.12, 0.012, 0.012, center=(0, 0, 0), bevel=0.0), P["plastic_black"], T(0.0, -0.281, 0.72 + k * 0.025))
pt.nameplate(b, T(0, -0.282, 0.32), 0.16, 0.09)
# tapered pole
b.add(lathe([(0.10, 1.0), (0.10, 1.05), (0.075, 4.45), (0.07, 4.5)], 48), P["post"])
b.add(torus(0.105, 0.012, 48, 8), P["stainless"], T(0, 0, 1.06))
b.build("Post", root, props={"title": "Post and base column", "spec": "Tapered steel pole, RAL 7021 powder coat; base: 150 L tank, 12.8 V 100 Ah LiFePO4, MPPT, BMS",
                              "live": "soc,T_bat,v_tank"})
# tank level window (fill bound to tank volume)
tw = MB()
tw.add(box(0.05, 0.008, 0.8, center=(0.0, 0, 0.0)), P["glass"])
tw.build("Tank_Window", root, props={"noShadow": 1}).location = (0.2, -0.19, 0.55)
tl = MB()
tl.add(box(0.036, 0.006, 0.78, center=(0, 0, 0.39)), P["water"])
o = tl.build("Tank_Level", root, props={"title": "Tank level", "live": "v_tank"})
o.location = (0.2, -0.195, 0.16)
o.rotation_euler = (0, 0, math.radians(-46))

# ------------------------------------------------------------------ planter tiers and planting
rng = np.random.default_rng(9)
for j, z in enumerate((1.0, 2.0, 3.0, 4.0)):
    pm = MB()
    Ro, Ri, Hp = 0.30, 0.105, 0.28
    zb = z - Hp
    pm.add(lathe([(Ri, zb + 0.02), (Ro - 0.02, zb), (Ro, zb + 0.02), (Ro + 0.012, zb + Hp), (Ro - 0.004, zb + Hp + 0.01),
                  (Ro - 0.012, zb + Hp - 0.02), (Ri + 0.01, zb + 0.05)], 64), P["corten"])
    pm.add(lathe([(Ri + 0.005, zb + Hp - 0.04), (Ro - 0.01, zb + Hp - 0.04)], 64), P["soil"])
    for k in range(3):
        a = 2 * math.pi * k / 3
        pm.add(box(0.2, 0.012, 0.04, center=(0.2, 0, 0)), P["stainless"], T(0, 0, zb - 0.02) @ R(0, 0, math.degrees(a)))
    # drip ring
    pm.add(torus(0.2, 0.005, 48, 6), P["plastic_black"], T(0, 0, zb + Hp - 0.035))
    pm.build(f"Tier_{j + 1}", root, props={"title": f"Planter tier {j + 1}", "spec": "Weathering steel ring, 0.25 m² plan, 60 L substrate, PC drip ring",
                                           "live": f"theta{j + 1},et{j + 1},irr{j + 1}"})
    pl = MB()
    for k in range(64):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(Ri + 0.04, Ro - 0.03)
        base = (r * math.cos(a), r * math.sin(a), zb + Hp - 0.04)
        Ls = rng.uniform(0.22, 0.42) * (1.1 if j == 3 else 1.0)
        if k % 3 == 0:
            # trailing stems over the rim
            Mt = T(*base) @ R(0, 0, math.degrees(a) - 90) @ R(rng.uniform(95, 140), 0, 0)
            w = Ls * 0.5
            pl.add(([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, Ls * 1.4), (-w / 2, 0, Ls * 1.4)], [(0, 1, 2, 3)],
                    [[(0, 0), (1, 0), (1, 1), (0, 1)]]), P["leaf_t"], Mt)
        else:
            Mt = T(*base) @ R(0, 0, rng.uniform(0, 360)) @ R(rng.uniform(10, 50), 0, 0)
            w = Ls * 0.45
            pl.add(([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, Ls), (-w / 2, 0, Ls)], [(0, 1, 2, 3)],
                    [[(0, 0), (1, 0), (1, 1), (0, 1)]]), P["leaf_b"], Mt)
    pl.build(f"Tier_{j + 1}_Plants", root, props={"title": "Planting", "spec": "Drought-tolerant perennials + trailing ivy", "live": "stress"})
    anchor(f"Tier{j + 1}", (0.36, 0.0, z + 0.15))
    anchor(f"SP_N{j + 1}", (0.14, -0.11, z - 0.1))
anchor("SP_N0", (0.14, -0.11, 0.25))

# drip riser clipped to the pole (8 mm PE in 16 mm sleeve)
rs = MB()
riser = [(0.12, -0.08, 0.95), (0.105, -0.07, 1.6), (0.095, -0.065, 2.6), (0.088, -0.06, 3.6), (0.08, -0.055, 3.9)]
pt.pipe(rs, [(0.2, -0.17, 0.95)] + riser, 0.016, P["plastic_black"], bend=0.05, flow_name="riser")
for z in (1.3, 2.3, 3.3):
    rs.add(torus(0.104 - 0.01 * (z - 1), 0.006, 32, 6), P["stainless"], T(0, 0, z))
rs.build("Riser", root, props={"title": "Drip riser", "spec": "8 mm PE, Swamee-Jain friction, 2 m emitter head", "live": "N0_P,N4_P,pump_on"})

# ------------------------------------------------------------------ canopy, PV and LED
cp = MB()
Rc = 1.0
zc = 4.5
tilt = math.radians(15)
for k in range(8):
    a0, a1 = 2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8
    # PV facet: trapezoid from the hub ring to the rim, rising outward at 15 deg (dish)
    r0, r1 = 0.16, Rc - 0.04
    pts = [(r0 * math.cos(a0), r0 * math.sin(a0), zc), (r1 * math.cos(a0), r1 * math.sin(a0), zc + (r1 - r0) * math.tan(tilt)),
           (r1 * math.cos(a1), r1 * math.sin(a1), zc + (r1 - r0) * math.tan(tilt)), (r0 * math.cos(a1), r0 * math.sin(a1), zc)]
    pts = [(x, y, z + 0.05) for x, y, z in pts]
    uv = [(0, 0), (1, 0), (1, 0.9), (0, 0.1)]
    cp.add((pts, [(0, 1, 2, 3)], [uv]), P["pv"])
    # facet frame
    cp.add(tube([pts[1], pts[2]], 0.012, 8), P["alu"])
    cp.add(tube([pts[0], pts[1]], 0.008, 8), P["alu"])
# rim gutter (collects rain to the hub) and underside shell
rim_z = zc + 0.05 + (Rc - 0.2) * math.tan(tilt)
cp.add(torus(Rc, 0.035, 96, 12), P["alu"], T(0, 0, rim_z))
cp.add(lathe([(0.16, zc - 0.02), (Rc, rim_z - 0.06), (Rc + 0.02, rim_z - 0.02)], 96), P["paint_white"])
cp.add(lathe([(0, zc - 0.05), (0.17, zc - 0.05), (0.17, zc + 0.08), (0, zc + 0.12)], 32), P["post"])
for k in range(8):
    a = 2 * math.pi * k / 8 + math.pi / 8
    cp.add(tube([(0.15 * math.cos(a), 0.15 * math.sin(a), zc - 0.02), (0.9 * math.cos(a), 0.9 * math.sin(a), rim_z - 0.05)], 0.015, 8),
           P["post"])
cp.build("PV_Canopy", root, props={"title": "PV canopy", "spec": "Ø2.0 m dish, 8 mono-Si facets (21.5 %), MPPT 98 %; CAD-calibrated 258 kWh/yr (London)",
                                    "live": "p_pv,G_poa,T_cell,curtail"})
led = MB()
led.add(lathe([(0.2, zc - 0.07), (0.42, zc - 0.03), (0.42, zc - 0.045), (0.2, zc - 0.085)], 64), P["led"])
led.build("LED_Ring", root, props={"title": "LED luminaire", "spec": "47.1 W high-CRI ring, SOC-staged adaptive dimming", "live": "p_light,dim"})
anchor("Canopy", (0, 0, rim_z + 0.35))
anchor("LED", (0.45, -0.1, zc - 0.25))
anchor("LEDsrc", (0.0, 0.0, zc - 0.12))
# sensor pod and antenna
sp = MB()
sp.add(box(0.1, 0.07, 0.16, center=(0, -0.11, 3.55), bevel=0.01), P["paint_white"])
sp.add(cyl(0.004, 0.28, 8, 3.6), P["plastic_black"], T(0.03, -0.12, 0))
sp.build("Sensor_Pod", root, props={"title": "Air-quality + LoRa node", "spec": "PM2.5/PM10, T/RH, soil moisture x4; 0.8 W"})
anchor("Base", (0.0, -0.35, 1.2))

export(HERE, "plantpost", camera={"pos": (6.0, -7.4, 4.4), "target": (0.0, 0.0, 2.55), "lens": 30})
print("done")
