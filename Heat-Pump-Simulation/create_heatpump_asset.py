"""Build the two-stage R290 air-source heat pump plant as an editable Blender model.

Run:  blender -b --factory-startup -P create_heatpump_asset.py
Outputs heatpump_rig.blend / .glb / _meta.json / _preview.png next to this file.

Equipment envelopes follow the annual model (model/params.py):
  LP pair 2 x 21 m3/h and HP 27 m3/h scrolls  -> Copeland ZH/ZP 15-20 kW envelopes (D 0.24 m, H 0.48-0.52 m)
  condenser 9 kW/K BPHE                         -> 60-plate 250 x 530 mm brazed plate unit
  coil 11 kW/K, 5.4 kg/s air                    -> two 2.1 x 1.6 m finned coils, 2 x 800 mm EC fans
  stores                                        -> 1 m3 buffer, 1 m3 DHW cylinder (as simulated)
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / 'Tools'))

from blendlib import parts as pt  # noqa: E402
from blendlib.core import (MB, R, T, align, anchor, box, cyl, empty, export, extrude, lathe, mat, plane, reset,  # noqa: E402
                           tex_fins, tex_louvre, texture, torus, tube)

reset(HERE / "textures")
P = pt.init()
rgb, nrm = tex_fins(512, 512, 6)
P["fins"] = mat("Aluminium fin pack", "#aeb6bb", 0.7, 0.42, tex=texture("fins", rgb), normal=texture("fins_n", nrm), tex_scale=4.0)
lrgb, lnrm = tex_louvre()
P["louvre"] = mat("Louvred panel RAL7035", "#c5c7c4", 0.0, 0.45, tex=texture("louvre", lrgb * [0.78, 0.79, 0.77]),
                  normal=texture("louvre_n", lnrm), tex_scale=2.0)
P["casing"] = mat("Casing RAL7035 powder coat", "#c9cbc7", 0.0, 0.4, coat=0.2)
P["casing_dark"] = mat("Casing RAL7024 graphite", "#474a51", 0.0, 0.42, coat=0.2)

root = empty("HeatPumpPlant", props={"title": "Two-stage R290 heat pump plant",
                                      "spec": "Annual simulation: London/Glasgow 2023, 12-flat residential block"})

# ---------------------------------------------------------------- site
site = MB()
site.add(box(8.4, 4.6, 0.18, center=(0, 0, 0.09), bevel=0.025), P["slab"])
for x in (-4.1, 4.1):
    site.add(box(0.12, 4.6, 0.25, center=(x, 0, 0.125), bevel=0.01), P["concrete"])
site.add(box(10.6, 6.8, 0.04, center=(0, 0, 0.0)), P["gravel"])
# kerb edging around the gravel
for (cx, cy, sx, sy) in ((0, 3.45, 10.8, 0.1), (0, -3.45, 10.8, 0.1), (5.35, 0, 0.1, 6.8), (-5.35, 0, 0.1, 6.8)):
    site.add(box(sx, sy, 0.12, center=(cx, cy, 0.04), bevel=0.01), P["concrete"])
site.build("Site_Plinth", root)
Z0 = 0.18

# ---------------------------------------------------------------- outdoor unit frame
UX0, UX1 = -4.0, -0.6          # unit length 3.4 m
UW = 1.25
frame = MB()
for y in (-UW / 2 + 0.05, UW / 2 - 0.05):
    frame.add(box(UX1 - UX0, 0.1, 0.14, center=((UX0 + UX1) / 2, y, Z0 + 0.07)), P["galv"])
for x in (UX0 + 0.05, (UX0 + UX1) / 2, UX1 - 0.05):
    frame.add(box(0.1, UW - 0.1, 0.12, center=(x, 0, Z0 + 0.06)), P["galv"])
frame.add(box(UX1 - UX0, UW, 0.02, center=((UX0 + UX1) / 2, 0, Z0 + 0.15)), P["casing_dark"])
H_UNIT = 2.05
for x in (UX0 + 0.03, UX0 + 2.2, UX1 - 0.03):
    for y in (-UW / 2 + 0.03, UW / 2 - 0.03):
        frame.add(box(0.06, 0.06, H_UNIT - 0.16, center=(x, y, Z0 + 0.16 + (H_UNIT - 0.16) / 2), bevel=0.006), P["casing"])
for y in (-UW / 2 + 0.03, UW / 2 - 0.03):
    frame.add(box(UX1 - UX0, 0.06, 0.08, center=((UX0 + UX1) / 2, y, Z0 + H_UNIT - 0.04), bevel=0.006), P["casing"])
# fan deck with two openings
FAN_X = [UX0 + 0.62, UX0 + 1.6]
deck_z = Z0 + H_UNIT
for x0, x1 in [(UX0, FAN_X[0] - 0.47), (FAN_X[0] + 0.47, FAN_X[1] - 0.47), (FAN_X[1] + 0.47, UX0 + 2.2)]:
    frame.add(box(x1 - x0, UW, 0.03, center=((x0 + x1) / 2, 0, deck_z)), P["casing"])
for fx in FAN_X:
    for y in (-1, 1):
        frame.add(box(0.94, (UW - 0.94) / 2, 0.03, center=(fx, y * (UW / 2 - (UW - 0.94) / 4), deck_z)), P["casing"])
# compressor-bay roof, rear and end panels (front left open as cut-away)
frame.add(box(UX1 - (UX0 + 2.2), UW, 0.03, center=((UX0 + 2.2 + UX1) / 2, 0, deck_z), bevel=0.004), P["casing"])
frame.add(box(UX1 - (UX0 + 2.2) - 0.06, 0.02, H_UNIT - 0.25, center=((UX0 + 2.2 + UX1) / 2, UW / 2 - 0.01, Z0 + 0.16 + (H_UNIT - 0.25) / 2)),
          P["louvre"])
frame.add(box(0.02, UW - 0.06, H_UNIT - 0.25, center=(UX1 - 0.01, 0, Z0 + 0.16 + (H_UNIT - 0.25) / 2)), P["louvre"])
# coil-end panel and service-side lower kick panel
frame.add(box(0.02, UW - 0.06, H_UNIT - 0.25, center=(UX0 + 0.01, 0, Z0 + 0.16 + (H_UNIT - 0.25) / 2)), P["casing"])
frame.add(box(UX1 - (UX0 + 2.2) - 0.06, 0.02, 0.18, center=((UX0 + 2.2 + UX1) / 2, -UW / 2 + 0.01, Z0 + 0.25)), P["casing"])
# partition between fan section and compressor bay
frame.add(box(0.02, UW - 0.06, H_UNIT - 0.25, center=(UX0 + 2.2, 0, Z0 + 0.16 + (H_UNIT - 0.25) / 2)), P["casing_dark"])
# lifting lugs, nameplate
for x in (UX0 + 0.1, UX1 - 0.1):
    for y in (-1, 1):
        frame.add(torus(0.035, 0.009, 16, 6), P["galv"], T(x, y * (UW / 2 + 0.012), Z0 + 0.08) @ R(90, 0, 0))
pt.nameplate(frame, T(UX1 - 0.6, -UW / 2 - 0.003, Z0 + 0.28), 0.2, 0.11, key="plate_hp")
pt.sign(frame, T(UX1 - 0.25, -UW / 2 - 0.004, Z0 + 0.3), "warn_flammable", 0.12)
pt.sign(frame, T(UX0 + 0.012, -0.3, Z0 + 1.3) @ R(0, 0, -90), "warn_flammable", 0.16)
pt.sign(frame, T(UX0 + 0.012, 0.15, Z0 + 1.3) @ R(0, 0, -90), "warn_electric", 0.16)
frame.build("Unit_Casing", root, props={"title": "Packaged two-stage air-source heat pump",
                                         "spec": "R290 (0.9 kg/kW charge class A3), 60 kW at A-4/W55, two-stage with flash economiser",
                                         "dimensions": "3.40 x 1.25 x 2.05 m", "sound_power": "~74 dB(A) est.",
                                         "live": "Q_c,cop,W_total,on_frac"})

# ---------------------------------------------------------------- coils and fans
COIL_L, COIL_H = 2.08, 1.62
for side, nm in ((-1, "Coil_Front"), (1, "Coil_Rear")):
    c = MB()
    pt.finned_coil(c, T(UX0 + 1.11, side * (UW / 2 - 0.09), Z0 + 0.28), COIL_L, COIL_H, 0.12)
    c.build(nm, root, props={"title": "Finned-tube evaporator coil", "spec": "Al fins 2.1 mm pitch, 3/8\" Cu tubes, 4 rows",
                             "face_area": "2 x 3.4 m²", "live": "Q_e,approach_e,frost_kg,ua_frac"})
# frost layer overlays (opacity bound to frost mass)
fr = MB()
frost_m = mat("Frost layer", "#f4f9ff", 0.0, 0.7, alpha=0.85)
for side in (-1, 1):
    fr.add(box(COIL_L, 0.004, COIL_H, center=(UX0 + 1.11, side * (UW / 2 - 0.02), Z0 + 0.28 + COIL_H / 2)), frost_m)
fo = fr.build("Coil_Frost", root, props={"noShadow": 1})
fo.hide_render = True
for i, fx in enumerate(FAN_X):
    stat, rot = MB(), MB()
    hub = pt.axial_fan(stat, rot, T(fx, 0, deck_z + 0.015), D=0.8, shroud_h=0.3, blades=5)
    stat.build(f"Fan_{i + 1}_Shroud", root, props={"title": f"EC axial fan {i + 1}", "spec": "Ø800 mm sickle blade, EC motor 0.75 kW",
                                                    "live": "fan,W_fan,m_air"})
    r = rot.build(f"Fan_{i + 1}_Rotor", root)
    r.location = hub.to_translation()

# ---------------------------------------------------------------- compressor bay
BAY = UX0 + 2.2
cb = MB()
cb.add(box(1.05, 0.5, 0.012, center=(BAY + 0.6, -0.22, Z0 + 0.166)), P["galv"])
cb.build("Bay_Rail", root)
comps = {}
for nm, x, H, title in (("LP_Compressor_A", BAY + 0.22, 0.48, "LP scroll A"), ("LP_Compressor_B", BAY + 0.55, 0.48, "LP scroll B"),
                        ("HP_Compressor", BAY + 0.92, 0.52, "HP scroll")):
    m = MB()
    body = P["paint_blue"] if nm.startswith("LP") else P["paint_dark"]
    comps[nm] = pt.scroll_compressor(m, T(x, -0.24, Z0 + 0.172) @ R(0, 0, -90), D=0.24, H=H, body_mat=body)
    m.build(nm, root, props={"title": title, "spec": ("Variable-speed hermetic scroll, 21 m³/h @50 Hz, 25-100 Hz"
                                                       if nm.startswith("LP") else "Variable-speed hermetic scroll, 27 m³/h @50 Hz, holds optimum Pi"),
                             "refrigerant": "R290", "live": "f_lp,pr_lp,eta_is_lp,T_dis_lp" if nm.startswith("LP") else "f_hp,pr_hp,eta_is_hp,T_dis_hp"})

fv = MB()
flash = pt.vessel_vertical(fv, T(BAY + 0.36, 0.3, Z0 + 0.17), 0.2, 0.5, legs=3, leg_h=0.12, mat=P["paint_grey"],
                           nozzles=[("vap", "top", 0, 0.03), ("liq", "bottom", 0, 0.025), ("in", 0.55, 180, 0.025)], sight=-90)
fv.build("Flash_Economiser", root, props={"title": "Flash economiser vessel", "spec": "Open flash tank, 16 L, PS 32 bar",
                                          "live": "Pi,Ti,x7,inj_ratio,m_vap"})
cd = MB()
cports = pt.bphe(cd, T(BAY + 0.86, 0.3, Z0 + 0.32), W=0.25, H=0.53, plates=60)
cd.add(box(0.3, 0.08, 0.15, center=(BAY + 0.86, 0.38, Z0 + 0.245)), P["galv"])
cd.build("Condenser_BPHE", root, props={"title": "Brazed-plate condenser", "spec": "60 plates, 316L/Cu brazed, UA ≈ 9 kW/K",
                                        "live": "Q_c,Tc,approach_c,T_w_out"})
# inverter / electrical box on rear wall
eb = MB()
eb.add(box(0.95, 0.22, 0.62, center=(BAY + 0.6, UW / 2 - 0.15, Z0 + 1.45), bevel=0.01), P["casing"])
for k in range(3):
    eb.add(box(0.26, 0.03, 0.5, center=(BAY + 0.28 + k * 0.32, UW / 2 - 0.275, Z0 + 1.45), bevel=0.004), P["paint_dark"])
    for f in range(9):
        eb.add(box(0.004, 0.02, 0.44, center=(BAY + 0.18 + k * 0.32 + f * 0.025, UW / 2 - 0.30, Z0 + 1.45)), P["alu"])
eb.add(box(0.16, 0.012, 0.1, center=(BAY + 0.2, UW / 2 - 0.265, Z0 + 1.82)), P["hmi"])
pt.sign(eb, T(BAY + 1.0, UW / 2 - 0.262, Z0 + 1.62), "warn_electric", 0.08)
pt.cable_tray(eb, [(BAY + 0.1, UW / 2 - 0.2, Z0 + 1.1), (BAY + 0.1, UW / 2 - 0.2, Z0 + 0.4)], 0.1, 0.04)
eb.build("Inverter_Panel", root, props={"title": "Inverter & control panel", "spec": "3 x compressor VFD, 2 x EC fan drives, PLC",
                                        "live": "W_comp,W_fan"})

# ---------------------------------------------------------------- refrigerant pipework
rp = MB()
cu = P["copper"]
ins = P["armaflex"]
Zs = Z0 + 0.172 + 0.09 + 0.48 * 0.28
# 1: evaporator outlet header (rear of coils, at partition)
evap_out = (BAY - 0.08, 0.0, Z0 + 1.55)
sp1 = evap_out
suc = pt.pipe(rp, [(BAY - 0.08, -0.45, Z0 + 1.55), evap_out, (BAY + 0.06, 0.0, Z0 + 1.55), (BAY + 0.06, -0.5, Z0 + 1.55),
                   (BAY + 0.06, -0.5, Zs), (BAY + 0.62, -0.5, Zs)], 0.042, cu, insul=0.013, flow_name="r_suction")
for x in (BAY + 0.22, BAY + 0.55):
    pt.pipe(rp, [(x, -0.5, Zs), (x, -0.24 - 0.24, Zs)], 0.035, cu, insul=0.012)
rp.add(cyl(0.028, 0.06, 16), ins, T(BAY + 0.06, -0.5, Zs) @ R(0, 90, 0))
# 3: LP discharge manifold -> mixing tee -> 4: HP suction
ztop = Z0 + 0.172 + 0.48 + 0.12
mix = (BAY + 0.72, -0.24, Z0 + 0.98)
pt.pipe(rp, [(BAY + 0.22, -0.24, ztop), (BAY + 0.22, -0.24, Z0 + 0.98), mix], 0.028, cu, flow_name="r_lp_dis")
pt.pipe(rp, [(BAY + 0.55, -0.24, ztop), (BAY + 0.55, -0.24, Z0 + 0.98)], 0.028, cu)
hp_suc_z = Z0 + 0.172 + 0.09 + 0.52 * 0.28
pt.pipe(rp, [mix, (BAY + 0.72, -0.5, Z0 + 0.98), (BAY + 0.72, -0.5, hp_suc_z), (BAY + 0.92, -0.5, hp_suc_z),
             (BAY + 0.92, -0.48, hp_suc_z)], 0.035, cu, flow_name="r_hp_suc")
# 8: flash vapour injection
pt.pipe(rp, [flash["vap"], (BAY + 0.36, 0.3, Z0 + 1.12), (BAY + 0.72, 0.3, Z0 + 1.12), (BAY + 0.72, -0.24, Z0 + 1.12),
             (BAY + 0.72, -0.24, Z0 + 0.98)], 0.022, cu, flow_name="r_vap_inj")
# 5: HP discharge to condenser top port
hp_top = Z0 + 0.172 + 0.52 + 0.12
pt.pipe(rp, [(BAY + 0.92, -0.24, hp_top), (BAY + 0.92, -0.24, Z0 + 1.0), (BAY + 0.92 - 0.075, -0.05, Z0 + 1.0),
             (cports["p1"][0], cports["p1"][1], Z0 + 1.0), cports["p1"]], 0.028, cu, flow_name="r_hp_dis")
# 6: liquid out -> filter drier -> sight glass -> HP EEV -> flash inlet
liq = [cports["p3"], (cports["p3"][0], 0.05, cports["p3"][2]), (BAY + 0.62, 0.05, cports["p3"][2]),
       (BAY + 0.62, 0.05, Z0 + 0.62), (flash["in"][0], 0.05, Z0 + 0.62), (flash["in"][0], flash["in"][1], flash["in"][2])]
pt.pipe(rp, liq, 0.022, cu, flow_name="r_liquid")
pt.filter_drier(rp, T(BAY + 0.62, 0.05, Z0 + 0.48 + 0.06), 0.022, 0.07, 0.22)
pt.sight_glass(rp, T(BAY + 0.62, 0.05, Z0 + 0.62 - 0.06) @ R(0, 0, 0), 0.022)
pt.eev(rp, T((BAY + 0.62 + flash["in"][0]) / 2, 0.05, Z0 + 0.62) @ R(0, 90, 0), 0.02)
# 9 -> 10: flash liquid -> LP EEV -> distributor to coils
lp_liq = [flash["liq"], (BAY + 0.36, 0.3, Z0 + 0.26), (BAY + 0.06, 0.3, Z0 + 0.26), (BAY - 0.06, 0.3, Z0 + 0.26),
          (BAY - 0.06, 0.3, Z0 + 0.6)]
pt.pipe(rp, lp_liq, 0.018, cu, flow_name="r_lp_liq")
pt.eev(rp, T(BAY + 0.2, 0.3, Z0 + 0.26) @ R(0, 90, 0), 0.018)
dist = (BAY - 0.06, 0.3, Z0 + 0.6)
rp.add(lathe([(0, 0), (0.03, 0.0), (0.035, 0.05), (0.02, 0.09), (0, 0.09)], 20), P["brass"], T(*dist))
for k in range(8):
    a = 2 * math.pi * k / 8
    pt.pipe(rp, [(dist[0], dist[1], dist[2] + 0.09), (dist[0] - 0.05 - 0.03 * math.cos(a), dist[1] + 0.06 * math.sin(a), dist[2] + 0.25),
                 (BAY - 0.1, (0.45 if k < 4 else -0.45), Z0 + 0.4 + 0.15 * k)], 0.0064, cu, bend=0.03, seg=8)
# gauges / transducers
pt.gauge(rp, T(BAY + 0.06, -0.5, Z0 + 1.62), 0.08)
pt.gauge(rp, T(BAY + 0.92 - 0.075, -0.05, Z0 + 1.06), 0.08)
pt.relief_valve(rp, T(BAY + 0.36, 0.3, Z0 + 1.2), 0.02)
rp.build("Refrigerant_Pipework", root, props={"title": "R290 pipework", "spec": "EN 12735 copper, brazed, suction insulated 13 mm",
                                              "live": "m_lp,m_hp,m_vap"})

# ---------------------------------------------------------------- state-point anchors (refrigerant + secondary)
anchor("SP_1", (evap_out[0], evap_out[1], evap_out[2] + 0.06))
anchor("SP_2", (BAY + 0.4, -0.52, Zs + 0.06))
anchor("SP_3", (BAY + 0.22, -0.24, Z0 + 1.04))
anchor("SP_4", (BAY + 0.82, -0.52, hp_suc_z + 0.06))
anchor("SP_5", (BAY + 0.92, -0.24, Z0 + 1.06))
anchor("SP_6", (cports["p3"][0], cports["p3"][1], cports["p3"][2] - 0.05))
anchor("SP_7", (flash["in"][0] + 0.05, 0.05, Z0 + 0.68))
anchor("SP_8", (BAY + 0.36, 0.3, Z0 + 1.18))
anchor("SP_9", (BAY + 0.36, 0.3, Z0 + 0.2))
anchor("SP_10", (BAY - 0.06, 0.3, Z0 + 0.72))
anchor("SP_A1", (UX0 + 1.1, -UW / 2 - 0.25, Z0 + 1.1))
anchor("SP_A2", (FAN_X[0], 0, deck_z + 0.75))
anchor("Unit", (UX0 + 1.7, 0, deck_z + 0.5))
anchor("Comp", (BAY + 0.55, -0.6, Z0 + 0.9))

# ---------------------------------------------------------------- hydraulic plant
PX = 0.4
hyd = MB()
# buffer (1 m3) and DHW (1 m3) stores
BUF = (1.25, 0.85)
DHW = (2.85, 0.85)
bufp = pt.storage_cylinder(hyd, T(BUF[0], BUF[1], Z0), 0.95, 1.95, P["paint_grey"],
                           ports=[("top_in", 0.9, 180, 0.054), ("bot_out", 0.1, 180, 0.054), ("heat_flow", 0.88, -90, 0.054),
                                  ("heat_ret", 0.12, -90, 0.054), ("backup", 0.5, -40, 0.06)])
dhwp = pt.storage_cylinder(hyd, T(DHW[0], DHW[1], Z0), 1.0, 1.8, P["paint_white"],
                           ports=[("hot_out", 0.92, 0, 0.035), ("cold_in", 0.06, 0, 0.035), ("charge_in", 0.85, -90, 0.035),
                                  ("charge_out", 0.08, -90, 0.035), ("imm", 0.12, 140, 0.05)])
hyd.build("Plant_Base", root)
# temperature-mapped jacket bands (10 nodes each) for stratification display
for nm, (cx, cy), D, H, z0 in (("Buffer", BUF, 0.95, 1.95, Z0 + 0.12), ("DHW", DHW, 1.0, 1.8, Z0 + 0.12)):
    for j in range(10):
        b = MB()
        za = z0 + 0.07 + (H - 0.2) * (9 - j) / 10
        b.add(lathe([(D / 2 + 0.004, za + 0.004), (D / 2 + 0.006, za + 0.008), (D / 2 + 0.006, za + (H - 0.2) / 10 - 0.008),
                     (D / 2 + 0.004, za + (H - 0.2) / 10 - 0.004)], 64, math.radians(272), math.radians(338)),
              mat(f"{nm} band", "#9aa3aa", 0.0, 0.5), T(cx, cy, 0))
        b.build(f"{nm}_Band_{j + 1}", root, props={"noShadow": 1})
anchor("Buffer", (BUF[0], BUF[1], Z0 + 2.3))
anchor("DHW", (DHW[0], DHW[1], Z0 + 2.15))

pl = MB()
pump1 = pt.inline_pump(pl, T(0.3, -0.75, Z0 + 0.62), 0.05, 0.18, 0.28)
pump2 = pt.inline_pump(pl, T(1.25, -0.95, Z0 + 0.62), 0.065, 0.2, 0.3)
pump3 = pt.inline_pump(pl, T(2.35, -0.25, Z0 + 0.45) @ R(0, 0, 180), 0.032, 0.14, 0.2)
pl.build("Pumps", root, props={"title": "Circulators", "spec": "Primary 1.55 kg/s, heating circuit (variable), DHW charge",
                               "live": "W_pump"})
ex = MB()
pt.expansion_vessel(ex, T(0.55, 1.65, Z0), 0.4, 0.6)
pt.expansion_vessel(ex, T(1.95, 1.75, Z0), 0.3, 0.45)
ex.build("Expansion_Vessels", root, props={"title": "Expansion vessels", "spec": "80 L heating, 35 L DHW (potable)"})
dh = MB()
dports = pt.bphe(dh, T(2.35, 0.35, Z0 + 0.95) @ R(0, 0, 90), W=0.2, H=0.38, plates=40)
dh.build("DHW_Plate_HX", root, props={"title": "DHW charging plate HX", "spec": "40 plates, stratified charging to 58 °C",
                                      "live": "mode_dhw,dhw_soc"})
bk = MB()
bk.add(lathe([(0, 0), (0.07, 0), (0.07, 0.03), (0.05, 0.035), (0.05, 0.14), (0.04, 0.16), (0, 0.16)], 32), P["paint_dark"],
       T(*bufp["backup"]) @ R(0, 90, 0) @ R(0, 0, 0) @ T(0, 0, -0.06))
bk.build("Backup_Heater", root, props={"title": "Backup immersion bank", "spec": "2 x 9 kW, 3-step contactor", "live": "W_backup"})
cp = MB()
pt.panel(cp, T(3.55, -1.55, Z0) @ R(0, 0, 0), 0.8, 0.35, 1.8, 2)
pt.sign(cp, T(3.75, -1.55 - 0.19, Z0 + 1.45), "warn_electric", 0.12)
pt.nameplate(cp, T(3.35, -1.55 - 0.19, Z0 + 1.62), 0.14, 0.08)
# cable tray on posts from the panel to the unit, with SWA power and control cables
for x in (3.55, 1.8, 0.0, UX1 + 0.3):
    cp.add(box(0.041, 0.041, 2.15, center=(x, -1.55 + (0.0 if x == 3.55 else 0.0), 1.075 + Z0)), P["galv"])
pt.cable_tray(cp, [(3.55, -1.55, Z0 + 2.2), (UX1 + 0.3, -1.55, Z0 + 2.2), (UX1 + 0.3, -UW / 2 - 0.3, Z0 + 2.2)], 0.15, 0.05)
for k, rr in enumerate((0.014, 0.011, 0.009)):
    pt.cable(cp, (UX1 + 0.3, -UW / 2 - 0.3 + 0.03 * k, Z0 + 2.17), (UX1 - 0.2, -UW / 2 + 0.05, Z0 + 1.6 - 0.05 * k), rr, 0.12)
cp.build("Control_Panel", root, props={"title": "Plant controller", "spec": "Weather compensation, DHW priority, Agile price signal",
                                       "live": "T_flow_set,price,blocked,boost"})

# hydronic pipework (insulated, with flow paths)
hp = MB()
ins_m = P["armaflex"]
wy_out = (UX1 + 0.12, 0.42, Z0 + 0.86)
pt.pipe(hp, [cports["p2"], (cports["p2"][0], cports["p2"][1] - 0.04, cports["p2"][2]), (cports["p2"][0], 0.42, cports["p2"][2]),
             (UX1 + 0.12, 0.42, cports["p2"][2]), (PX, 0.42, cports["p2"][2]), (PX, 0.42, Z0 + 1.95), (BUF[0] - 0.62, 0.42, Z0 + 1.95),
             (BUF[0] - 0.62, BUF[1], bufp["top_in"][2]), bufp["top_in"]], 0.054, P["steel"], insul=0.02, flow_name="w_flow",
        label="pipe_lthw_flow", label_at=0.42)
pt.pipe(hp, [bufp["bot_out"], (BUF[0] - 0.75, BUF[1], bufp["bot_out"][2]), (BUF[0] - 0.75, -0.75, bufp["bot_out"][2]),
             (BUF[0] - 0.75, -0.75, Z0 + 0.62), pump1["out"], pump1["in"], (-0.25, -0.75, Z0 + 0.62), (UX1 + 0.12, -0.75, Z0 + 0.62),
             (UX1 + 0.12, -0.75, cports["p4"][2]), (cports["p4"][0], -0.75, cports["p4"][2]), (cports["p4"][0], cports["p4"][1] - 0.04, cports["p4"][2]),
             cports["p4"]], 0.054, P["steel"], insul=0.02, flow_name="w_ret", label="pipe_lthw_return", label_at=0.12)
# heating circuit to building (leaves pad at y = -2.3)
pt.pipe(hp, [bufp["heat_flow"], (BUF[0], -0.2, bufp["heat_flow"][2]), (BUF[0] - 0.25, -0.2, bufp["heat_flow"][2]),
             (BUF[0] - 0.25, -0.95, bufp["heat_flow"][2]), (BUF[0] - 0.25, -2.1, bufp["heat_flow"][2]), (BUF[0] - 0.25, -2.1, -0.3)], 0.076, P["steel"], insul=0.025,
        flow_name="h_flow", label="pipe_lthw_flow", label_at=0.7)
pt.pipe(hp, [bufp["heat_ret"], (BUF[0], -0.2, bufp["heat_ret"][2]), (BUF[0] + 0.25, -0.2, bufp["heat_ret"][2]),
             (BUF[0] + 0.25, -0.95, bufp["heat_ret"][2]), (BUF[0] + 0.25, -0.75, bufp["heat_ret"][2]),
             (pump2["in"][0] - 0.25, -0.75, bufp["heat_ret"][2]), (pump2["in"][0] - 0.25, -0.95, Z0 + 0.62), pump2["in"], pump2["out"],
             (pump2["out"][0] + 0.12, -0.95, Z0 + 0.62), (pump2["out"][0] + 0.12, -2.1, Z0 + 0.62), (pump2["out"][0] + 0.12, -2.1, -0.3)], 0.076, P["steel"], insul=0.025, flow_name="h_ret",
        label="pipe_lthw_return", label_at=0.75)
# DHW charging loop and potable connections
pt.pipe(hp, [dports["p2"], (dports["p2"][0] + 0.15, dports["p2"][1], dports["p2"][2]), (DHW[0] - 0.2, dhwp["charge_in"][1], dports["p2"][2]),
             (dhwp["charge_in"][0], dhwp["charge_in"][1], dhwp["charge_in"][2])], 0.035, P["copper"], insul=0.013, flow_name="dhw_charge")
pt.pipe(hp, [dhwp["charge_out"], (dhwp["charge_out"][0], -0.25, dhwp["charge_out"][2]),
             (pump3["in"][0] + 0.1, -0.25, dhwp["charge_out"][2]), (pump3["in"][0] + 0.1, -0.25, Z0 + 0.45), pump3["in"], pump3["out"],
             (2.05, -0.25, Z0 + 0.45), (2.05, 0.35, Z0 + 0.45),
             (dports["p4"][0] + 0.15, dports["p4"][1], dports["p4"][2]), dports["p4"]], 0.035, P["copper"], insul=0.013,
        flow_name="dhw_charge_ret")
pt.pipe(hp, [dhwp["hot_out"], (DHW[0] + 0.85, DHW[1], dhwp["hot_out"][2]), (DHW[0] + 0.85, -2.1, dhwp["hot_out"][2]), (DHW[0] + 0.85, -2.1, -0.3)], 0.042,
        P["copper"], insul=0.013, flow_name="dhw_hot", label="pipe_dhw", label_at=0.6)
pt.pipe(hp, [dhwp["cold_in"], (DHW[0] + 0.7, DHW[1], dhwp["cold_in"][2]), (DHW[0] + 0.7, -2.1, dhwp["cold_in"][2]), (DHW[0] + 0.7, -2.1, -0.3)], 0.042,
        P["copper"], flow_name="dhw_cold")
# valves on the circuits
pt.ball_valve(hp, T(PX, 0.42, Z0 + 1.4), 0.054)
pt.ball_valve(hp, align((1, 0, 0), (-0.05, -0.75, Z0 + 0.62)), 0.054)
pt.strainer(hp, align((1, 0, 0), (0.0, -0.75, Z0 + 0.62)), 0.054)
pt.control_valve(hp, T(BUF[0] - 0.25, -0.55, bufp["heat_flow"][2]) @ R(0, 0, 90), 0.06)
for p_ in (dhwp["hot_out"], bufp["top_in"]):
    pt.sensor_well(hp, T(p_[0], p_[1], p_[2] + 0.05))
# pipe supports
for x in (PX - 0.5, PX + 0.3, BUF[0] - 0.25):
    pt.pipe_support(hp, T(x, -0.75, Z0), Z0 + 0.6 - Z0, 0.3)
for x in (BUF[0] - 0.25, None, DHW[0] + 0.85, DHW[0] + 0.7):
    pass
for x, r_ in ((BUF[0] - 0.25, 0.07), (pump2["out"][0] + 0.12, 0.07), (DHW[0] + 0.85, 0.045), (DHW[0] + 0.7, 0.045)):
    hp.add(lathe([(r_, Z0 - 0.02), (r_ + 0.03, Z0 - 0.02), (r_ + 0.03, Z0 + 0.05), (r_ + 0.015, Z0 + 0.06), (r_, Z0 + 0.06)], 24),
           P["plastic_black"], T(x, -2.1, 0))
hp.build("Hydronic_Pipework", root, props={"title": "Hydronic circuits", "spec": "Primary DN50, heating DN65, DHW DN32/40",
                                           "live": "T_w_in,T_w_out,T_flow,T_ret"})
anchor("SP_W1", (UX1 + 0.12, -0.75, Z0 + 0.78))
anchor("SP_W2", (UX1 + 0.12, 0.42, cports["p2"][2] + 0.1))
anchor("Pump1", (0.3, -0.75, Z0 + 1.25))
anchor("HeatOut", (BUF[0], -2.1, Z0 + 1.4))
anchor("Panel", (3.55, -1.6, Z0 + 2.0))

export(HERE, "heatpump_rig", camera={"pos": (5.2, -7.6, 4.6), "target": (-0.6, 0.0, 1.0), "lens": 34})
print("done")
