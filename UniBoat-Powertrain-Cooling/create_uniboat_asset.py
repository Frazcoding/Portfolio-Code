"""UniBoat electric hydrofoil catamaran with pumped two-phase R1233zd(E) cooling loop (open service bay).

Envelope from MODEL_DIMENSIONS.md (10 x 4.4 m catamaran, 10 kWh pack 0.75 x 0.45 x 0.25 m, motor 0.32 x 0.40 m,
SiC inverter 0.32 x 0.22 x 0.13 m, seawater plate condenser 0.30 x 0.18 x 0.38 m, 12 mm lines).
The whole boat is parented to `Boat` (raised by the viewer when foil-borne); `Propeller` spins with speed.
Run: blender -b --factory-startup -P create_uniboat_asset.py
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / 'Tools'))

from blendlib import parts as pt  # noqa: E402
from blendlib.core import (MB, R, T, anchor, box, cyl, empty, export, extrude, lathe, loft, mat, pbr, reset, sphere,  # noqa: E402
                           torus, tube)

reset(HERE / "textures")
P = pt.init()
P["sea"] = mat("Sea", "#1f4656", 0.15, 0.05, coat=1.0, alpha=0.72)
P["gelcoat"] = pbr("Gelcoat white", "paint_worn", "#f0f0ec", 1.5, tint="subtle", rough=0.25, normal_strength=0.15, metal=0.0, coat=0.6)
P["carbon"] = pbr("Carbon fibre", "metal_plates", "#1b1d20", 0.25, tint="soft", metal=0.2, rough=0.25)
P["antifoul"] = pbr("Antifouling", "paint_worn", "#2a2f36", 1.5, tint="soft", rough=0.6, metal=0.0)
P["foil"] = pbr("Foil (anodised Al)", "brushed", "#4a5560", 0.4, tint="soft", metal=0.85, rough=0.3)
P["accent"] = mat("Team accent", "#0e7cc2", 0.0, 0.35, coat=0.6)
P["battery"] = pbr("Battery case", "paint_worn", "#2b3d55", 0.6, tint="subtle", rough=0.4, metal=0.0, normal_strength=0.2)
P["coldplate"] = P["alu"]
P["ptfe"] = mat("Refrigerant hose", "#2a2a2a", 0.0, 0.5)

root = empty("UniBoatScene", props={"title": "UniBoat electric hydrofoil", "spec": "Monaco Energy Class catamaran, 10 kWh, pumped two-phase cooling"})
sea = MB()
sea.add(box(400, 400, 0.05, center=(0, 0, -0.025), bevel=0.0), P["sea"])
sea.build("Sea", root, props={"noShadow": 1})

boat = empty("Boat", (0, 0, 0), root)
hulls = MB()
under = MB()
for fy in (-1.7, 1.7):
    pt.ship_hull(hulls, under, -4.8, 9.6, 0.78, fy, deck_z=0.62, wl_z=0.0, keel_z=-0.3, stations=34, mat_top=P["gelcoat"],
                 mat_bot=P["antifoul"], mat_deck=P["gelcoat"])
    hulls.add(box(7.5, 0.03, 0.12, center=(-0.5, fy - 0.39 * (1 if fy < 0 else -1), 0.32), bevel=0.0), P["accent"])
# bridge deck and cockpit pod
deck = [(-4.2, -1.4), (2.2, -1.4), (3.4, -0.6), (3.4, 0.6), (2.2, 1.4), (-4.2, 1.4)]
hulls.add(extrude(deck, 0.08, z0=0.6), P["carbon"])
pod = []
for k in range(14):
    s = k / 13
    x = -3.0 + 6.0 * s
    w = 0.55 * math.sin(math.pi * min(1, s * 1.3)) ** 0.6 + 0.05
    h = 0.55 * math.sin(math.pi * s) ** 0.5 + 0.02
    pod.append([(x, w * math.cos(a), 0.68 + h * max(0, math.sin(a)) ** 0.8) for a in [math.pi * i / 12 for i in range(13)]])
hulls.add(loft(pod, closed=False), P["gelcoat"])
hulls.add(loft([[(1.0 + 0.6 * s, 0.5 * math.cos(a) * (1 - 0.3 * s), 1.05 + 0.25 * math.sin(a) * (1 - s) - 0.1 * s)
                 for a in [math.pi * i / 10 for i in range(11)]] for s in (0.0, 0.5, 1.0)], closed=False), P["glass"])
hulls.add(box(0.5, 0.45, 0.08, center=(-0.6, 0, 0.82)), P["rubber"])                    # seat
hulls.add(box(0.12, 0.45, 0.5, center=(-0.85, 0, 1.08)), P["rubber"])
hulls.add(torus(0.17, 0.018, 24, 8), P["rubber"], T(0.35, 0, 1.08) @ R(0, 70, 0))
hulls.build("Hull", boat, props={"title": "Catamaran hull + cockpit", "spec": "Standard Energy Class catamaran, 750 kg with pilot",
                                 "live": "v,foil,D"})
under.build("Hull_Underwater", boat)

# ------------------------------------------------------------------ foils, struts, Z-drive
fo = MB()


def naca(c, t, n=14):
    up, lo = [], []
    for i in range(n + 1):
        x = (1 - math.cos(math.pi * i / n)) / 2
        y = 5 * t * (0.2969 * math.sqrt(x) - 0.126 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1015 * x ** 4)
        up.append((x * c, y * c))
        lo.append((x * c, -y * c))
    return up + lo[::-1][1:-1]


# front main foil spanning the hulls at z = -1.25, chord 0.30, dihedral tips
secs = []
for k in range(15):
    s = -1 + 2 * k / 14
    y = 2.0 * s
    c = 0.30 * (1 - 0.45 * abs(s) ** 2)
    z = -1.25 + 0.15 * abs(s) ** 3
    secs.append([(2.6 - x + c * 0.25, y, z + yy) for x, yy in naca(c, 0.12)])
fo.add(loft(secs), P["foil"])
for fy in (-1.7, 1.7):
    st = [[(2.65 - x + 0.05, fy + yy, z) for x, yy in naca(0.2, 0.10)] for z in (-1.25, -0.2, 0.15)]
    fo.add(loft(st), P["foil"])
# rear Z-drive: vertical strut, gearbox pod, T-stabiliser
st = [[(-4.35 - x + 0.1, yy, z) for x, yy in naca(0.24, 0.11)] for z in (-1.05, -0.3, 0.35)]
fo.add(loft(st), P["foil"])
fo.add(lathe([(0, -0.42), (0.055, -0.38), (0.075, -0.25), (0.075, 0.12), (0.05, 0.22), (0, 0.26)], 24), P["foil"],
       T(-4.32, 0, -1.12) @ R(0, -90, 0))
secs = [[(-4.42 - x + 0.06, 0.8 * s, -1.12 + yy) for x, yy in naca(0.16 * (1 - 0.4 * abs(s)), 0.11)] for s in (-1, -0.5, 0, 0.5, 1)]
fo.add(loft(secs), P["foil"])
fo.build("Foils", boat, props={"title": "Hydrofoils", "spec": "Main foil 4.0 m span NACA 2412-class, Z-drive strut + T-stabiliser, take-off ≈ 13.6 kt",
                               "live": "foil,D"})
mount = empty("Prop_Mount", (-4.74, 0, -1.12), boat, rot=(0, -90, 0))
pr = MB()
pr.add(lathe([(0, -0.06), (0.04, -0.05), (0.045, 0.03), (0.02, 0.07), (0, 0.08)], 20), P["brass"])
for b in range(3):
    secs = []
    for k in range(7):
        s = k / 6
        r = 0.04 + 0.18 * s
        c = 0.09 * math.sin(math.pi * (0.25 + 0.75 * s)) + 0.02
        tw = math.radians(55 - 30 * s)
        ring = []
        for x, yy in naca(c, 0.06, 6):
            xr = (x - c / 2) * math.cos(tw) - yy * math.sin(tw)
            zr = (x - c / 2) * math.sin(tw) + yy * math.cos(tw)
            ring.append((r, xr, zr))
        secs.append(ring)
    pr.add(loft(secs), P["brass"], R(0, 0, 120 * b))
pr.build("Propeller", mount, props={"title": "Propeller", "spec": "3-blade Ø0.44 m bronze, ηprop ≈ 0.72"})

# ------------------------------------------------------------------ powertrain + cooling loop in the service bay
sv = MB()
bx, by, bz = -2.4, 0.0, 0.69
sv.add(box(0.75, 0.45, 0.25, center=(bx, by, bz + 0.155)), P["battery"])                   # 10 kWh pack
sv.add(box(0.75, 0.45, 0.03, center=(bx, by, bz + 0.015)), P["coldplate"])                 # cold plate
for k in range(6):
    sv.add(box(0.7, 0.012, 0.012, center=(bx, by - 0.2 + k * 0.08, bz + 0.29)), P["paint_orange"])
pt.sign(sv, T(bx + 0.2, by - 0.228, bz + 0.17), "warn_electric", 0.08)
ix = -3.25
sv.add(box(0.32, 0.22, 0.13, center=(ix, 0.45, bz + 0.095)), P["alu"])                      # SiC inverter
sv.add(box(0.34, 0.24, 0.03, center=(ix, 0.45, bz + 0.015)), P["coldplate"])
for k in range(8):
    sv.add(box(0.3, 0.004, 0.03, center=(ix, 0.36 + k * 0.025, bz + 0.175)), P["alu"])
mx_ = -4.05
sv.add(lathe([(0, 0), (0.16, 0), (0.16, 0.4), (0, 0.4)], 32), P["paint_dark"], T(mx_, 0, bz + 0.05))          # axial-flux motor (vertical)
sv.add(lathe([(0.16, 0.05), (0.19, 0.05), (0.19, 0.35), (0.16, 0.35)], 32), P["coldplate"], T(mx_, 0, bz + 0.05))  # jacket
pt.pump = getattr(pt, "pump", None)
sv.add(lathe([(0, 0), (0.07, 0), (0.075, 0.12), (0.06, 0.18), (0, 0.18)], 24), P["stainless"], T(-1.75, -0.45, bz))     # canned pump
sv.add(lathe(pt.dished_profile(0.08, 0.05, 0.32, 0.4, 6), 24), P["stainless"], T(-1.75, 0.45, bz))                    # accumulator
cond = (-3.6, -1.7, -0.22)
under2 = MB()
under2.add(box(0.30, 0.18, 0.38, center=cond, bevel=0.01), P["stainless"])                 # sea-chest condenser
under2.build("Condenser", boat, props={"title": "Seawater plate condenser", "spec": "Sea chest, 33 L/min seawater, ε≈0.47", "live": "Q_cond,T_sw_out,Tsat"})
pts_ = [(-1.75, -0.45, bz + 0.18), (-1.75, -0.45, bz + 0.35), (bx + 0.45, -0.3, bz + 0.35), (bx + 0.38, -0.2, bz + 0.03)]
pt.pipe(sv, pts_, 0.016, P["ptfe"], bend=0.06, flow_name="r_pump_batt")
pt.pipe(sv, [(bx - 0.38, 0.2, bz + 0.03), (bx - 0.5, 0.3, bz + 0.03), (ix + 0.17, 0.45, bz + 0.03)], 0.016, P["ptfe"], bend=0.06, flow_name="r_batt_inv")
pt.pipe(sv, [(ix - 0.17, 0.45, bz + 0.03), (mx_ + 0.2, 0.3, bz + 0.03), (mx_ + 0.2, 0.0, bz + 0.15)], 0.016, P["ptfe"], bend=0.06, flow_name="r_inv_motor")
pt.pipe(sv, [(mx_, 0.2, bz + 0.38), (mx_, 0.4, bz + 0.5), (-3.6, -1.0, bz + 0.5), (-3.6, -1.7, 0.4), (cond[0], cond[1], cond[2] + 0.19)],
        0.02, P["ptfe"], bend=0.1, flow_name="r_motor_cond")
pt.pipe(sv, [(cond[0] + 0.15, cond[1], cond[2]), (-2.0, -1.7, 0.1), (-2.0, -1.7, 0.55), (-1.75, -0.6, bz + 0.05), (-1.75, -0.45, bz + 0.02)],
        0.016, P["ptfe"], bend=0.1, flow_name="r_cond_pump")
sv.build("Cooling_Loop", boat, props={"title": "Pumped two-phase loop", "spec": "R1233zd(E), pump → battery → inverter → motor → condenser, T_sat = T_sea + 8 K",
                                      "live": "m_r,x5,Tsat,W_pump"})
bt = MB()
bt.add(box(0.74, 0.44, 0.245, center=(bx, by, bz + 0.155)), P["battery"])
bt.build("Battery_Pack", boat, props={"title": "10 kWh battery", "spec": "Energy Class cap 10 kWh, R_pack 0.089 Ω @25 °C", "live": "soc,T_b,Q_b,I"})
iv = MB()
iv.add(box(0.31, 0.21, 0.125, center=(ix, 0.45, bz + 0.095)), P["alu"])
iv.build("Inverter", boat, props={"title": "SiC inverter", "live": "T_i,Q_i"})
mo = MB()
mo.add(lathe([(0, 0), (0.158, 0), (0.158, 0.398), (0, 0.398)], 32), P["paint_dark"], T(mx_, 0, bz + 0.051))
mo.build("Motor", boat, props={"title": "Axial-flux PMSM", "spec": "120 kW peak, Z-drive", "live": "T_m,Q_m,P_shaft"})
for sid, xyz in {"1": (-1.75, -0.45, bz + 0.25), "2": (-1.9, -0.3, bz + 0.42), "3": (bx - 0.45, 0.25, bz + 0.12),
                 "4": (ix - 0.2, 0.45, bz + 0.12), "5": (mx_, 0.35, bz + 0.6), "6": (-2.6, -1.7, 0.2)}.items():
    from blendlib.core import anchor as _a
    _a(f"SP_{sid}", xyz)
anchor("Battery", (bx, 0, 1.4))
anchor("Motor", (mx_, 0, 1.4))
anchor("BoatTag", (1.0, 0, 2.2))
anchor("Sea", (-6.0, -2.5, 0.4))

export(HERE, "uniboat_cooling", camera={"pos": (11.0, -12.5, 5.5), "target": (-0.6, 0.0, 0.0), "lens": 32})
print("done")
