"""Download CC0 PBR textures (ambientCG, Poly Haven) and HDRIs, normalised for the Blender pipeline.

Each texture set is stored in assets/textures/<name>/ as
  color.jpg   base colour (sRGB)
  tint.jpg    luminance-only base colour normalised to mean 0.85 (multiplied by a paint colour in Blender)
  normal.jpg  OpenGL normal map
  orm.jpg     glTF packed occlusion (R), roughness (G), metalness (B)
HDRIs go to assets/hdri/<name>.hdr. Licences: CC0 (ambientCG.com, polyhaven.com).
Run once:  python assets/fetch_assets.py
"""
import io
import json
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
TEX = ROOT / "textures"
HDRI = ROOT / "hdri"
UA = {"User-Agent": "Mozilla/5.0 portfolio-asset-fetch"}

# name: (source, id, metalness default, roughness scale)
SETS = {
    "paint_worn": ("acg", "PaintedMetal004", 0.0, 1.0),
    "paint_chipped": ("acg", "PaintedMetal006", 0.0, 1.0),
    "paint_smooth": ("acg", "PaintedMetal016", 0.0, 1.0),
    "paint_scratched": ("acg", "PaintedMetal012", 0.0, 1.0),
    "brushed": ("acg", "Metal012", 1.0, 1.0),
    "brushed2": ("acg", "Metal009", 1.0, 1.0),
    "sheet_galv": ("acg", "SheetMetal002", 1.0, 1.0),
    "sheet_galv2": ("acg", "SheetMetal004", 1.0, 1.0),
    "metal_plates": ("acg", "MetalPlates001", 1.0, 1.0),
    "diamond_plate": ("acg", "DiamondPlate008A", 1.0, 1.0),
    "corrugated": ("acg", "CorrugatedSteel005", 1.0, 1.0),
    "plastic_rough": ("acg", "Plastic006", 0.0, 1.0),
    "rubber": ("acg", "Rubber004", 0.0, 1.0),
    "foil": ("acg", "Foil002", 1.0, 1.0),
    "grating": ("acg", "Fence007A", 1.0, 1.0),
    "concrete_slab": ("ph", "concrete_floor_02", 0.0, 1.0),
    "concrete_smooth": ("ph", "brushed_concrete", 0.0, 1.0),
    "concrete_painted": ("ph", "painted_concrete", 0.0, 1.0),
    "asphalt": ("ph", "asphalt_02", 0.0, 1.0),
    "grass": ("ph", "sparse_grass", 0.0, 1.0),
    "gravel": ("ph", "gravel_floor", 0.0, 1.0),
    "rusty": ("ph", "rusty_metal_02", 1.0, 1.0),
    "blockwall": ("ph", "concrete_block_wall", 0.0, 1.0),
    "corrugated_iron": ("ph", "corrugated_iron_02", 1.0, 1.0),
    "grass_green": ("ph", "leafy_grass", 0.0, 1.0),
    "grass_lawn": ("ph", "grass_path_2", 0.0, 1.0),
    "roof_bitumen": ("ph", "asphalt_04", 0.0, 1.0),
    "paving": ("ph", "brick_pavement_02", 0.0, 1.0),
    "granite": ("ph", "granite_tile", 0.0, 1.0),
    "soil": ("ph", "brown_mud_leaves_01", 0.0, 1.0),
    "corten": ("ph", "rusty_metal_03", 1.0, 1.0),
    "wood_glulam": ("ph", "fine_grained_wood", 0.0, 1.0),
    "wood_cladding": ("ph", "brown_planks_04", 0.0, 1.0),
    "render": ("ph", "grey_plaster", 0.0, 1.0),
}
HDRIS = {"sky_partly_cloudy": "kloofendal_48d_partly_cloudy_puresky", "industrial": "industrial_sunset_puresky"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return r.read()


def load(b, mode=None):
    im = Image.open(io.BytesIO(b))
    if mode:
        im = im.convert(mode)
    return im


def fetch_acg(asset):
    z = zipfile.ZipFile(io.BytesIO(get(f"https://ambientcg.com/get?file={asset}_1K-JPG.zip")))
    out = {}
    for n in z.namelist():
        u = n.upper()
        key = ("color" if "_COLOR" in u else "normal" if "_NORMALGL" in u else "rough" if "_ROUGHNESS" in u
               else "metal" if "_METALNESS" in u else "ao" if "AMBIENTOCCLUSION" in u else "opacity" if "_OPACITY" in u else None)
        if key and n.lower().endswith((".jpg", ".png")):
            out[key] = z.read(n)
    return out


def fetch_ph(asset):
    files = json.loads(get(f"https://api.polyhaven.com/files/{asset}"))
    out = {}
    for key, ph in (("color", "Diffuse"), ("normal", "nor_gl"), ("rough", "Rough"), ("ao", "AO"), ("metal", "Metal")):
        try:
            out[key] = get(files[ph]["1k"]["jpg"]["url"])
        except KeyError:
            pass
    return out


def build_set(name, src, asset, metal_default):
    d = TEX / name
    if (d / "orm.jpg").exists():
        return
    d.mkdir(parents=True, exist_ok=True)
    raw = fetch_acg(asset) if src == "acg" else fetch_ph(asset)
    col = load(raw["color"], "RGB")
    size = col.size
    col.save(d / "color.jpg", quality=88)
    a = np.asarray(col, dtype=np.float32) / 255
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    lum = np.clip(lum / max(lum.mean(), 1e-3) * 0.85, 0, 1)
    Image.fromarray((lum * 255).astype(np.uint8)).convert("RGB").save(d / "tint.jpg", quality=88)
    load(raw["normal"], "RGB").resize(size).save(d / "normal.jpg", quality=92)
    rough = np.asarray(load(raw["rough"], "L").resize(size), np.float32) if "rough" in raw else np.full(size[::-1], 128.0)
    metal = np.asarray(load(raw["metal"], "L").resize(size), np.float32) if "metal" in raw else np.full(size[::-1], 255.0 * metal_default)
    ao = np.asarray(load(raw["ao"], "L").resize(size), np.float32) if "ao" in raw else np.full(size[::-1], 255.0)
    orm = np.dstack([ao, rough, metal]).astype(np.uint8)
    Image.fromarray(orm, "RGB").save(d / "orm.jpg", quality=92)
    if "opacity" in raw:
        op = load(raw["opacity"], "L").resize(size)
        rgba = col.copy()
        rgba.putalpha(op)
        rgba.save(d / "color_alpha.png")
    (d / "SOURCE.txt").write_text(f"{src}:{asset} (CC0)\n", encoding="utf-8")
    print("texture", name, asset)


def main():
    TEX.mkdir(parents=True, exist_ok=True)
    HDRI.mkdir(parents=True, exist_ok=True)
    for name, (src, asset, metal, _) in SETS.items():
        try:
            build_set(name, src, asset, metal)
        except Exception as e:
            print("FAILED", name, asset, e)
    for name, ph in HDRIS.items():
        p = HDRI / f"{name}.hdr"
        if not p.exists():
            p.write_bytes(get(f"https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/{ph}_2k.hdr"))
            print("hdri", name)
        pj = HDRI / f"{name}_1k.hdr"
        if not pj.exists():
            pj.write_bytes(get(f"https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/{ph}_1k.hdr"))


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# derived maps and decals
# ---------------------------------------------------------------------------
def soft_tints():
    """tint_soft.jpg: luminance map with 35 % contrast (subtle wear under a paint colour)."""
    for d in TEX.iterdir():
        t = d / "tint.jpg"
        out = d / "tint_soft.jpg"
        if t.exists() and not out.exists():
            a = np.asarray(Image.open(t).convert("L"), np.float32) / 255
            a = np.clip(0.85 + (a - a.mean()) * 0.35, 0, 1)
            Image.fromarray((a * 255).astype(np.uint8)).convert("RGB").save(out, quality=88)
        sub = d / "tint_subtle.jpg"
        if t.exists() and not sub.exists():
            a = np.asarray(Image.open(t).convert("L"), np.float32) / 255
            a = np.clip(0.88 + (a - a.mean()) * 0.10, 0, 1)
            Image.fromarray((a * 255).astype(np.uint8)).convert("RGB").save(sub, quality=88)


def _font(size, bold=True):
    from PIL import ImageFont
    for f in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans-Bold.ttf", "segoeuib.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def decals():
    from PIL import ImageDraw
    D = ROOT / "decals"
    D.mkdir(exist_ok=True)

    def warn(name, symbol, caption):
        W, H = 512, 640
        im = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        d = ImageDraw.Draw(im)
        tri = [(W / 2, 30), (W - 30, 430), (30, 430)]
        d.polygon(tri, fill=(250, 200, 0, 255))
        d.line(tri + [tri[0]], fill=(0, 0, 0, 255), width=26, joint="curve")
        f = _font(210)
        bw = d.textbbox((0, 0), symbol, font=f)
        d.text(((W - (bw[2] - bw[0])) / 2, 170), symbol, fill=(0, 0, 0, 255), font=f)
        fc = _font(46)
        for k, line in enumerate(caption.split("\n")):
            bw = d.textbbox((0, 0), line, font=fc)
            d.text(((W - (bw[2] - bw[0])) / 2, 465 + k * 56), line, fill=(0, 0, 0, 255), font=fc)
        im.save(D / f"{name}.png")

    warn("warn_flammable", "🔥" if False else "!", "FLAMMABLE GAS\nR290 PROPANE")
    warn("warn_electric", "⚡" if False else "!", "DANGER\n400 V")
    warn("warn_hot", "!", "HOT SURFACE\nDO NOT TOUCH")
    warn("warn_pressure", "!", "PRESSURE SYSTEM\nPSSR 2000")
    warn("warn_ammonia", "!", "TOXIC GAS\nR717 AMMONIA")
    warn("warn_h2", "!", "HYDROGEN\nNO NAKED FLAMES")

    def plate(name, lines, w=640, h=360, bg=(214, 218, 220), fg=(25, 30, 35)):
        im = Image.new("RGBA", (w, h), bg + (255,))
        d = ImageDraw.Draw(im)
        d.rectangle([6, 6, w - 7, h - 7], outline=(90, 95, 100, 255), width=6)
        d.rectangle([6, 6, w - 7, 70], fill=(30, 60, 110, 255))
        d.text((24, 14), lines[0], fill=(255, 255, 255, 255), font=_font(40))
        for k, ln in enumerate(lines[1:]):
            d.text((24, 92 + k * 52), ln, fill=fg + (255,), font=_font(34, bold=False))
        for x, y in ((20, h - 20), (w - 20, h - 20), (20, 88), (w - 20, 88)):
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(150, 155, 160, 255))
        im.save(D / f"{name}.png")

    plate("plate_hp", ["THERMAFLOW HT-60", "Refrigerant: R290  Charge: 9.6 kg", "PS high 31 bar / low 18 bar",
                       "Heating 60 kW (A-4/W55)   400V 3~ 50Hz", "S/N TF60-2026-0117   CE  UKCA"])
    plate("plate_hthp", ["THERMAFLOW HTHP-650", "Refrigerant: R600 / R1233zd(E)", "Heating 650 kW @ 95 °C",
                         "Motor 315 kW   690V 3~ 50Hz", "S/N HT650-2026-0042   PED Cat IV"])
    plate("plate_tank", ["STORAGE VESSEL", "Capacity 100 m³   Design 3 bar(g)", "Design temp 95 °C",
                         "Insulation 200 mm MW / Al clad", "Built 2026   Inspected PSSR"])
    plate("plate_generic", ["PLANT ITEM", "Ref: see O&M manual", "Isolate before maintenance",
                            "Inspection due: 2027-04", "QR: digital twin record"])

    def pipe_label(name, text, bg, fg=(255, 255, 255)):
        w, h = 1024, 128
        im = Image.new("RGBA", (w, h), bg + (255,))
        d = ImageDraw.Draw(im)
        f = _font(64)
        d.text((40, 26), text, fill=fg + (255,), font=f)
        for x in (760, 880):
            d.polygon([(x, 30), (x + 80, 64), (x, 98)], fill=fg + (255,))
        im.save(D / f"{name}.png")

    # BS 1710 basic identification colours with safety colour bands
    pipe_label("pipe_lthw_flow", "LTHW FLOW", (0, 102, 51))
    pipe_label("pipe_lthw_return", "LTHW RETURN", (0, 102, 51))
    pipe_label("pipe_refrig_suction", "R290 SUCTION", (196, 170, 120), (20, 20, 20))
    pipe_label("pipe_refrig_liquid", "R290 LIQUID", (196, 170, 120), (20, 20, 20))
    pipe_label("pipe_refrig_discharge", "R290 HOT GAS", (196, 170, 120), (20, 20, 20))
    pipe_label("pipe_steam", "STEAM 2.7 BAR", (160, 160, 160), (20, 20, 20))
    pipe_label("pipe_process", "PROCESS HW 95°C", (0, 102, 51))
    pipe_label("pipe_effluent", "EFFLUENT", (40, 40, 40))
    pipe_label("pipe_dhw", "DHW", (0, 102, 51))
    pipe_label("pipe_h2", "HYDROGEN", (201, 171, 0), (20, 20, 20))
    print("decals written")


if __name__ == "__main__":
    soft_tints()
    decals()


def foliage():
    """Alpha-cut leaf textures (procedural, CC0): tomato compound leaf and a single broad leaf."""
    from PIL import ImageDraw, ImageFilter
    D = ROOT / "decals"
    D.mkdir(exist_ok=True)
    rng = np.random.default_rng(3)

    def leaflet(d, cx, cy, L, W, ang, col):
        pts = []
        for k in range(25):
            t = k / 24
            r = W * np.sin(np.pi * t) ** 0.8 * (1 + 0.12 * np.sin(t * 40))
            pts.append((t * L, r))
        for k in range(24, -1, -1):
            t = k / 24
            r = W * np.sin(np.pi * t) ** 0.8 * (1 + 0.12 * np.sin(t * 40 + 1))
            pts.append((t * L, -r))
        ca, sa = np.cos(ang), np.sin(ang)
        poly = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]
        d.polygon(poly, fill=col)
        d.line([(cx, cy), (cx + L * 0.95 * ca, cy + L * 0.95 * sa)], fill=(150, 185, 110, 255), width=3)

    W, H = 512, 1024
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line([(W / 2, H - 10), (W / 2, 40)], fill=(70, 110, 45, 255), width=10)
    for k in range(5):
        y = H - 160 - k * 170
        g = int(95 + rng.integers(-15, 15))
        col = (45, g, 35, 255)
        for side in (-1, 1):
            leaflet(d, W / 2, y, 205 - k * 20, 44 - k * 4, -np.pi / 2 + side * np.pi * (0.36 + 0.03 * k), col)
    leaflet(d, W / 2, 140, 130, 55, -np.pi / 2, (50, 105, 38, 255))
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    im.save(D / "leaf_tomato.png")

    im = Image.new("RGBA", (256, 512), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    leaflet(d, 128, 500, 470, 105, -np.pi / 2, (52, 110, 40, 255))
    im.filter(ImageFilter.GaussianBlur(0.6)).save(D / "leaf_broad.png")
    print("foliage written")


if __name__ == "__main__":
    foliage()
