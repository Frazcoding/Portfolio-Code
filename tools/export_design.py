"""Import the final Temple Works hub design from the Ember-Site-Selection project into ``data/temple_works_design.json``.

Sources (Ember-Site-Selection/Outputs/design, written by scripts/hub_design.py):
  design_step5_local.json + summary.json                 base design, EMB-HUB-003 (8 drive-through lanes)
  design_expansion_local.json + summary_expansion.json   expansion, EMB-HUB-005 (11 lanes)
  D:/QGIS/ors-route_*.json                               ORS route Bristol Coach Station -> hub (dead run)

Geometry stays in the project's local site grid (scripts/site_frame.py: origin at the SW corner of title 19736799, u
along the railway boundary, metres); an affine map local -> lon/lat (fitted on the exact BNG transform) is stored for
the web map. Run once with the project environment:

    uv run python tools/export_design.py [path/to/Ember-Site-Selection] [path/to/ors-route.json]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = Path(r"D:\QGIS\Ember-Site-Selection")
DEFAULT_ROUTE = Path(r"D:\QGIS\ors-route_1793182610105.json")

# scripts/site_frame.py
ORIGIN = (359471.2, 171814.0)
THETA = math.atan2(171879.7 - 171814.0, 359596.3 - 359471.2)
TO_WGS = Transformer.from_crs(27700, 4326, always_xy=True).transform

# feature kinds kept for the views (labels, dimensions and notes stay in the drawings)
KEEP = {"title", "yard", "tree_bank", "road_ext", "gate", "fence", "lane", "lane_new", "coach", "swept", "aisle_arrow",
        "island", "cable", "charger", "grid", "kerb", "wash", "building", "landscape", "car_park", "car_bay", "footway"}


class SiteFrame:
    """Local site grid (u, v) <-> BNG <-> WGS84."""

    @staticmethod
    def to_bng(u: float, v: float) -> tuple[float, float]:
        return (ORIGIN[0] + u * math.cos(THETA) - v * math.sin(THETA), ORIGIN[1] + u * math.sin(THETA) + v * math.cos(THETA))

    @classmethod
    def to_lonlat(cls, u: float, v: float) -> tuple[float, float]:
        return TO_WGS(*cls.to_bng(u, v))

    @classmethod
    def affine(cls) -> list[float]:
        """[lon0, lat0, dlon/du, dlat/du, dlon/dv, dlat/dv] fitted at the origin with 100 m legs (error < 1 cm on site)."""
        (x0, y0), (xu, yu), (xv, yv) = cls.to_lonlat(0, 0), cls.to_lonlat(100, 0), cls.to_lonlat(0, 100)
        return [x0, y0, (xu - x0) / 100, (yu - y0) / 100, (xv - x0) / 100, (yv - y0) / 100]


class DesignExport:
    def __init__(self, project: Path):
        self.design = project / "Outputs" / "design"

    @staticmethod
    def rounded(geom: dict, tol: float) -> dict:
        g = shape(geom)
        if tol and g.geom_type in ("Polygon", "MultiPolygon", "LineString"):
            g = g.simplify(tol)
        return json.loads(json.dumps(mapping(g)), parse_float=lambda s: round(float(s), 2))

    @staticmethod
    def slot(f: dict, lanes: dict) -> dict:
        """Centre and heading of a parked coach from its rectangle; nose towards -u (the lanes are entered from the east)."""
        ring = f["geom"]["coordinates"][0][:4]
        cx, cy = sum(p[0] for p in ring) / 4, sum(p[1] for p in ring) / 4
        (x0, y0), (x1, y1), (x2, y2) = ring[0], ring[1], ring[2]
        e1, e2 = math.hypot(x1 - x0, y1 - y0), math.hypot(x2 - x1, y2 - y1)
        dx, dy = ((x1 - x0), (y1 - y0)) if e1 >= e2 else ((x2 - x1), (y2 - y1))
        heading = math.atan2(dy, dx)
        if math.cos(heading) > 0:                    # face west (the lanes are entered from the run-in on the east)
            heading += math.pi
        name = f["label"].replace("bus in ", "")
        return {"lane": name, "n": int(name[1:]), "x": round(cx, 2), "y": round(cy, 2), "heading": round(heading, 4),
                "length": round(max(e1, e2), 2), "width": round(min(e1, e2), 2), "wired": lanes.get(name, False)}

    @staticmethod
    def queue_spots(features: list[dict], n: int = 3) -> list[dict]:
        """Waiting positions on the inbound aisle behind the gate, 16 m apart."""
        arrow = next(f for f in features if f["kind"] == "aisle_arrow" and f["label"] == "IN")
        pts = arrow["geom"]["coordinates"]
        out, acc, k = [], 0.0, 0
        targets = [6.0 + 16.0 * i for i in range(n)]
        for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
            seg = math.hypot(xb - xa, yb - ya)
            while k < len(targets) and acc + seg >= targets[k]:
                t = (targets[k] - acc) / seg if seg else 0
                out.append({"x": round(xa + (xb - xa) * t, 2), "y": round(ya + (yb - ya) * t, 2),
                            "heading": round(math.atan2(yb - ya, xb - xa), 4)})
                k += 1
            acc += seg
        return out

    def variant(self, name: str, local: str, summary: str, drawing: str) -> dict:
        feats = json.loads((self.design / local).read_text(encoding="utf-8"))
        summ = json.loads((self.design / summary).read_text(encoding="utf-8"))
        lanes = {}
        for f in feats:
            if f["kind"] in ("lane", "lane_new"):
                lanes[f["label"].split()[0]] = "charge" in f["label"]
        slots = sorted((self.slot(f, lanes) for f in feats if f["kind"] == "coach"), key=lambda s: s["n"])
        keep = []
        for f in feats:
            if f["kind"] not in KEEP or f["kind"] == "coach":
                continue
            tol = 0.08 if f["kind"] in ("swept", "tree_bank", "title", "yard") else 0.0
            keep.append({"kind": f["kind"], "label": f["label"], "geom": self.rounded(f["geom"], tol)})
        xs = [c for f in keep if f["kind"] in ("title", "yard") for c in shape(f["geom"]).bounds]
        return {"name": name, "drawing": drawing, "lanes": len(slots), "slots": slots, "queue": self.queue_spots(feats),
                "features": keep, "summary": summ, "bounds": [min(xs[0::4]), min(xs[1::4]), max(xs[2::4]), max(xs[3::4])]}

    def build(self, route_path: Path) -> dict:
        route = json.loads(route_path.read_text(encoding="utf-8"))["features"][0]
        seg = route["properties"]["summary"]
        coords = [[round(c[0], 6), round(c[1], 6)] for c in route["geometry"]["coordinates"]]
        return {
            "source": "Ember-Site-Selection/Outputs/design (scripts/hub_design.py), EMB-HUB-003 / EMB-HUB-005",
            "site_id": "S1",
            "frame": {"origin_bng": list(ORIGIN), "theta_rad": THETA, "affine": SiteFrame.affine()},
            "variants": [self.variant("base", "design_step5_local.json", "summary.json", "EMB-HUB-003"),
                         self.variant("expansion", "design_expansion_local.json", "summary_expansion.json", "EMB-HUB-005")],
            "deadrun_route": {"name": "Bristol Coach Station -> Temple Works hub (ORS driving-hgv)",
                              "distance_km": round(seg["distance"] / (1000 if seg["distance"] > 100 else 1), 3),
                              "duration_min": round(seg["duration"] / 60, 1),
                              "geometry": {"type": "LineString", "coordinates": coords}},
        }


def main(project: Path, route: Path) -> Path:
    out = DesignExport(project).build(route)
    path = ROOT / "data" / "temple_works_design.json"
    path.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    for v in out["variants"]:
        print(f"{v['name']}: {v['lanes']} lanes ({sum(s['wired'] for s in v['slots'])} wired), {len(v['features'])} features, "
              f"{len(v['queue'])} queue spots")
    print(f"dead run {out['deadrun_route']['distance_km']} km / {out['deadrun_route']['duration_min']} min; "
          f"wrote {path} ({path.stat().st_size / 1024:.0f} kB)")
    return path


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PROJECT, Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_ROUTE)
