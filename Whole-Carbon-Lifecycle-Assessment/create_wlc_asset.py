"""7,500 m2 office (50 x 30 m, 5 x 3.8 m storeys, 45 % WWR) with four facade/plant variants matching the WLC scenarios.

  Var1_*  baseline: 1970s precast ribbon windows, air-cooled R410A chillers, gas boiler flue
  Var2_*  deep retrofit: insulated render, triple-glazed punched windows with solar fins, R290 ASHPs, 100 kWp PV
  Var3_*  standard new build: unitised curtain wall, R32 ASHPs, 72 kWp PV
  Var4_*  timber exemplar: expressed glulam frame, larch louvres, R290 ASHPs, 158 kWp PV, green roof
Shared: site, roof core, interior volume (Interior_Glow lights when occupied and dark).
Run: blender -b --factory-startup -P create_wlc_asset.py
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / 'Tools'))

from blendlib import parts as pt  # noqa: E402
from blendlib.core import (MB, R, T, anchor, box, cyl, empty, export, extrude, lathe, mat, pbr, reset, tex_fins, tex_pv,  # noqa: E402
                           texture, torus, tube)

reset(HERE / "textures")
P = pt.init()
rgb, nrm = tex_fins(512, 512, 6)
P["fins"] = mat("Aluminium fin pack", "#aeb6bb", 0.7, 0.42, tex=texture("fins", rgb), normal=texture("fins_n", nrm), tex_scale=4.0)
P["pv"] = mat("PV module", "#16233d", 0.4, 0.12, tex=texture("pv_cells", tex_pv(6, 10, 48)), tex_scale=0.95, coat=0.9)
P["precast"] = pbr("Precast 1970s", "concrete_smooth", "#b9b1a2", 2.0, tint="full", metal=0.0)
P["old_glass"] = mat("Bronze tinted single glazing", "#4a4232", 0.5, 0.06, coat=1.0)
P["render"] = pbr("Insulated render", "render", "#e6e1d6", 2.0, tint="soft", metal=0.0)
P["tg_glass"] = mat("Triple glazing", "#6d8a96", 0.5, 0.04, alpha=0.78, coat=1.0)
P["cw_glass"] = mat("Curtain wall glass", "#7f9aa6", 0.6, 0.03, alpha=0.8, coat=1.0)
P["spandrel"] = mat("Spandrel glass", "#2e3a40", 0.6, 0.05, coat=1.0)
P["mullion"] = pbr("Mullion PPC RAL7016", "paint_worn", "#383e42", 0.8, tint="subtle", rough=0.35, metal=0.3, normal_strength=0.2)
P["glulam"] = pbr("Glulam", "wood_glulam", "#b9875a", 1.2, tint="full", metal=0.0, rough=0.55)
P["larch"] = pbr("Larch louvres", "wood_cladding", "#a88a6c", 1.0, tint="full", metal=0.0, rough=0.6)
P["green_roof"] = pbr("Sedum roof", "grass_lawn", "#6b7a3f", 1.5, tint="full", metal=0.0)
P["interior"] = mat("Interior (lit)", "#2b2f33", 0.0, 0.9, emit="#fff1d6", emit_strength=0.0)

root = empty("Office", props={"title": "7,500 m² office (WLC archetype)", "spec": "50 x 30 m, 5 storeys x 3.8 m, 45 % WWR, London"})
W, D, NF, FH = 50.0, 30.0, 5, 3.8
Hb = NF * FH

# ------------------------------------------------------------------ site
s = MB()
s.add(box(160, 120, 0.1, center=(10, 0, -0.05), bevel=0.0), P["grass"])
s.add(box(70, 22, 0.08, center=(0, -28, 0.0), bevel=0.0), P["asphalt"])
s.add(box(58, 38, 0.06, center=(0, 0, 0.02), bevel=0.0), P["paving"] if "paving" in P else P["slab"])
for k in range(12):
    s.add(box(0.12, 4.8, 0.005, center=(-30 + k * 5.5, -28, 0.045), bevel=0.0), mat("Bay marking", "#e8e6dc", 0, 0.6))
s.build("Site", root)

# shared interior + slabs + core
sh = MB()
sh.add(box(W - 0.8, D - 0.8, Hb - 0.2, center=(0, 0, Hb / 2)), P["interior"])
sh.build("Interior_Glow", root, props={"title": "Office floors", "spec": "Occupied 08:00-18:00 weekdays", "live": "occ,lights_on,T_room"})
sl = MB()
for f in range(NF + 1):
    sl.add(box(W + 0.1, D + 0.1, 0.3, center=(0, 0, f * FH + 0.15 - (0.15 if f == 0 else 0))), P["concrete"])
sl.add(box(8, 6, 3.2, center=(-12, 4, Hb + 1.6), bevel=0.1), P["concrete"])                 # lift / stair core overrun
sl.build("Slabs_Core", root)
anchor("Building", (0, -D / 2, Hb + 5))
anchor("Roof", (8, 0, Hb + 4))


def ribbon_facade(mb, glass, solid, mull, band=1.1):
    for f in range(NF):
        z = f * FH + 0.3
        for (ax, a0, a1, c) in (("x", -W / 2, W / 2, -D / 2), ("x", -W / 2, W / 2, D / 2), ("y", -D / 2, D / 2, -W / 2), ("y", -D / 2, D / 2, W / 2)):
            L, mid = a1 - a0, (a0 + a1) / 2
            if ax == "x":
                mb.add(box(L + 0.6, 0.35, band, center=(mid, c, z + band / 2)), solid)
                mb.add(box(L, 0.05, FH - band - 0.3, center=(mid, c, z + band + (FH - band - 0.3) / 2), bevel=0.0), glass)
                for k in range(int(L / 1.5) + 1):
                    mb.add(box(0.08, 0.14, FH - band - 0.3, center=(a0 + k * 1.5, c, z + band + (FH - band - 0.3) / 2)), mull)
            else:
                mb.add(box(0.35, L + 0.6, band, center=(c, mid, z + band / 2)), solid)
                mb.add(box(0.05, L, FH - band - 0.3, center=(c, mid, z + band + (FH - band - 0.3) / 2), bevel=0.0), glass)
                for k in range(int(L / 1.5) + 1):
                    mb.add(box(0.14, 0.08, FH - band - 0.3, center=(c, a0 + k * 1.5, z + band + (FH - band - 0.3) / 2)), mull)
    mb.add(box(W + 0.6, D + 0.6, 1.0, center=(0, 0, Hb + 0.5)), solid)


def punched_facade(mb, wall, glass, frame, fin):
    for (ax, a0, a1, c, nrm) in (("x", -W / 2, W / 2, -D / 2, -1), ("x", -W / 2, W / 2, D / 2, 1), ("y", -D / 2, D / 2, -W / 2, -1),
                                  ("y", -D / 2, D / 2, W / 2, 1)):
        L, mid = a1 - a0, (a0 + a1) / 2
        if ax == "x":
            mb.add(box(L + 0.5, 0.25, Hb + 1.0, center=(mid, c + nrm * 0.15, (Hb + 1.0) / 2)), wall)
        else:
            mb.add(box(0.25, L + 0.5, Hb + 1.0, center=(c + nrm * 0.15, mid, (Hb + 1.0) / 2)), wall)
        nwin = int(L / 3.0)
        for f in range(NF):
            z = f * FH + 0.9 + 1.2
            for k in range(nwin):
                u = a0 + (k + 0.5) * L / nwin
                pos = (u, c + nrm * 0.31, z) if ax == "x" else (c + nrm * 0.31, u, z)
                sz = (1.9, 0.03, 2.3) if ax == "x" else (0.03, 1.9, 2.3)
                mb.add(box(*sz, center=pos, bevel=0.0), glass)
                fr = (2.05, 0.08, 2.45) if ax == "x" else (0.08, 2.05, 2.45)
                fpos = (u, c + nrm * 0.29, z) if ax == "x" else (c + nrm * 0.29, u, z)
                mb.add(box(*fr, center=fpos, bevel=0.01), frame)
                if fin and nrm != 0:
                    fp = (u + 1.1, c + nrm * 0.62, z) if ax == "x" else (c + nrm * 0.62, u + 1.1, z)
                    fs = (0.06, 0.6, 2.6) if ax == "x" else (0.6, 0.06, 2.6)
                    mb.add(box(*fs, center=fp), fin)


def curtain_facade(mb):
    for (ax, a0, a1, c) in (("x", -W / 2, W / 2, -D / 2), ("x", -W / 2, W / 2, D / 2), ("y", -D / 2, D / 2, -W / 2), ("y", -D / 2, D / 2, W / 2)):
        L, mid = a1 - a0, (a0 + a1) / 2
        for f in range(NF):
            z0 = f * FH
            if ax == "x":
                mb.add(box(L, 0.04, FH * 0.6, center=(mid, c - 0.25 * (1 if c < 0 else -1), z0 + 0.95 + FH * 0.3), bevel=0.0), P["cw_glass"])
                mb.add(box(L, 0.04, FH * 0.4, center=(mid, c - 0.25 * (1 if c < 0 else -1), z0 + 0.76), bevel=0.0), P["spandrel"])
            else:
                mb.add(box(0.04, L, FH * 0.6, center=(c - 0.25 * (1 if c < 0 else -1), mid, z0 + 0.95 + FH * 0.3), bevel=0.0), P["cw_glass"])
                mb.add(box(0.04, L, FH * 0.4, center=(c - 0.25 * (1 if c < 0 else -1), mid, z0 + 0.76), bevel=0.0), P["spandrel"])
            for k in range(int(L / 1.5) + 1):
                u = a0 + k * 1.5
                if ax == "x":
                    mb.add(box(0.06, 0.2, FH, center=(u, c, z0 + FH / 2)), P["mullion"])
                else:
                    mb.add(box(0.2, 0.06, FH, center=(c, u, z0 + FH / 2)), P["mullion"])
            if ax == "x":
                mb.add(box(L, 0.2, 0.08, center=(mid, c, z0 + 1.52)), P["mullion"])
            else:
                mb.add(box(0.2, L, 0.08, center=(c, mid, z0 + 1.52)), P["mullion"])
    mb.add(box(W + 0.5, D + 0.5, 1.1, center=(0, 0, Hb + 0.55)), P["mullion"])


def timber_facade(mb):
    for (ax, a0, a1, c, nrm) in (("x", -W / 2, W / 2, -D / 2, -1), ("x", -W / 2, W / 2, D / 2, 1), ("y", -D / 2, D / 2, -W / 2, -1),
                                  ("y", -D / 2, D / 2, W / 2, 1)):
        L, mid = a1 - a0, (a0 + a1) / 2
        # glazing line set back behind the frame
        if ax == "x":
            mb.add(box(L, 0.04, Hb, center=(mid, c - nrm * 0.2, Hb / 2), bevel=0.0), P["tg_glass"])
        else:
            mb.add(box(0.04, L, Hb, center=(c - nrm * 0.2, mid, Hb / 2), bevel=0.0), P["tg_glass"])
        for k in range(int(L / 6.0) + 1):                 # glulam columns
            u = a0 + k * L / int(L / 6.0)
            p_ = (u, c, Hb / 2) if ax == "x" else (c, u, Hb / 2)
            sz = (0.4, 0.5, Hb) if ax == "x" else (0.5, 0.4, Hb)
            mb.add(box(*sz, center=p_, bevel=0.02), P["glulam"])
        for f in range(NF + 1):                              # glulam edge beams
            p_ = (mid, c, f * FH + 0.2) if ax == "x" else (c, mid, f * FH + 0.2)
            sz = (L + 0.5, 0.5, 0.45) if ax == "x" else (0.5, L + 0.5, 0.45)
            mb.add(box(*sz, center=p_, bevel=0.02), P["glulam"])
        for k in range(int(L / 0.45)):                       # vertical larch louvres
            u = a0 + 0.2 + k * 0.45
            if (k // 3) % 2:
                continue
            p_ = (u, c + nrm * 0.45, Hb / 2) if ax == "x" else (c + nrm * 0.45, u, Hb / 2)
            sz = (0.05, 0.22, Hb - 0.6) if ax == "x" else (0.22, 0.05, Hb - 0.6)
            mb.add(box(*sz, center=p_, bevel=0.005), P["larch"])


def roof_plant(mb, kind, pv_kwp):
    """Heat pump modules and a south-tilted PV field sized to the scenario's array (0.42 kWp modules)."""
    if True:
        nm = {"retrofit": 6, "newbuild": 6, "timber": 6}[kind]
        for k in range(nm):
            st_ = MB()
            pt.ashp_unit(st_, T(-4 + (k % 3) * 4.2, -8 + (k // 3) * 2.6, Hb + 1.0) @ R(0, 0, 0), L=3.4, W=1.25, H=1.9, nfans=2, D_fan=0.72,
                         casing=P["paint_white"])
            _merge(mb, st_)
        n_pan = int(pv_kwp / 0.42)
        slots = []
        for y in [1.6 + r * 2.3 for r in range(6)] + [-13.4 + r * 2.3 for r in range(3)]:
            for c_ in range(38):
                x = -21.5 + c_ * 1.15
                if -16.5 < x < -7.5 and 0.5 < y < 7.5:          # lift / stair core
                    continue
                if -7.5 < x < 10.0 and -10.5 < y < -3.5:         # heat pump modules
                    continue
                slots.append((x, y))
        for x, y in slots[:n_pan]:
            mb.add(box(1.13, 1.76, 0.04), P["pv"], T(x, y, Hb + 1.45) @ R(10, 0, 0))
            mb.add(box(0.04, 1.6, 0.05), P["alu"], T(x - 0.5, y, Hb + 1.3) @ R(10, 0, 0))


def _merge(dst, src):
    """Append one MB's geometry and materials to another (face indices re-based)."""
    base = sum(len(x) for x in dst.v)
    dst.v += src.v
    for fc, m, uv in zip(src.f, src.mi, src.uv):
        dst.f.append([i + base for i in fc])
        dst.mi.append(dst._mi(src.mats[m]))
        dst.uv.append(uv)


variants = [("Var1", "baseline", 0.0), ("Var2", "retrofit", 100.8), ("Var3", "newbuild", 72.0), ("Var4", "timber", 158.3)]
for nm, kind, kwp in variants:
    f = MB()
    if kind == "baseline":
        ribbon_facade(f, P["old_glass"], P["precast"], P["mullion"])
    elif kind == "retrofit":
        punched_facade(f, P["render"], P["tg_glass"], P["mullion"], P["alu"])
        f.add(box(W + 0.6, D + 0.6, 1.0, center=(0, 0, Hb + 0.5)), P["render"])
    elif kind == "newbuild":
        curtain_facade(f)
    else:
        timber_facade(f)
        f.add(box(W - 1, D - 1, 0.12, center=(0, 0, Hb + 0.36)), P["green_roof"])
    f.build(f"{nm}_Facade", root, props={"title": {"baseline": "1970s precast ribbon facade", "retrofit": "Deep-retrofit insulated render + triple glazing",
                                                   "newbuild": "Unitised curtain wall", "timber": "Glulam frame + larch louvres"}[kind],
                                         "live": "Q_heat,Q_cool,T_room"})
    r_ = MB()
    if kind == "baseline":
        for k in range(2):
            st_ = MB()
            pt.ashp_unit(st_, T(4 + k * 9, -6, Hb + 1.0), L=7.0, W=2.3, H=2.4, nfans=4, D_fan=0.9, casing=P["paint_grey"])
            _merge(r_, st_)
        r_.add(cyl(0.35, 6.0, 24, Hb + 1.0), P["stainless"], T(-18, 8, 0))
        pt.sign(r_, T(4, -7.17, Hb + 2.0), "warn_electric", 0.3)
    else:
        roof_plant(r_, kind, kwp)
    r_.build(f"{nm}_Roof", root, props={"title": "Roof plant", "spec": {"baseline": "2 x R410A air-cooled chillers + gas boiler flue",
                                                                         "retrofit": "6 x R290 ASHP modules, 101 kWp PV",
                                                                         "newbuild": "6 x R32 ASHP modules, 72 kWp PV",
                                                                         "timber": "6 x R290 ASHP modules, 158 kWp PV, sedum roof"}[kind],
                                       "live": "W_heat,W_cool,pv"})

import bpy  # noqa: E402
for o in bpy.data.objects:
    if o.name.startswith(("Var1", "Var2", "Var3")):
        o.hide_render = True
export(HERE, "wlc_office", camera={"pos": (62.0, -70.0, 42.0), "target": (0.0, 0.0, 8.0), "lens": 32})
print("done")
