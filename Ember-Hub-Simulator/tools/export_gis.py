"""Export the QGIS screening layers (Ember-Site-Selection/Outputs/ember_hub_analysis.gpkg, EPSG:27700) to
``data/bristol_gis.json`` in WGS84 for the web app. Run once with any Python that has shapely + pyproj:

    python tools/export_gis.py [path/to/ember_hub_analysis.gpkg]
"""
from __future__ import annotations

import json
import sqlite3
import struct
import sys
from pathlib import Path

from pyproj import Transformer
from shapely import wkb
from shapely.geometry import mapping
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GPKG = Path(r"D:\QGIS\Ember-Site-Selection\Outputs\ember_hub_analysis.gpkg")
TO_WGS = Transformer.from_crs(27700, 4326, always_xy=True).transform


class GpkgReader:
    """Minimal GeoPackage reader: strips the GPKG binary header and parses the WKB with shapely."""

    ENVELOPE_BYTES = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}

    def __init__(self, path: Path):
        self.con = sqlite3.connect(path)

    def geometry(self, blob: bytes):
        flags = blob[3]
        n_env = self.ENVELOPE_BYTES[(flags >> 1) & 0x07]
        return wkb.loads(bytes(blob[8 + n_env:]))

    def rows(self, table: str):
        cur = self.con.execute(f'select * from "{table}"')
        cols = [c[0] for c in cur.description]
        gcol = self.con.execute("select column_name from gpkg_geometry_columns where table_name=?", (table,)).fetchone()[0]
        for r in cur:
            d = dict(zip(cols, r))
            g = d.pop(gcol)
            yield d, (self.geometry(g) if g else None)


def wgs(geom, ndp=6):
    g = transform(TO_WGS, geom)
    return json.loads(json.dumps(mapping(g)), parse_float=lambda s: round(float(s), ndp))


def main(gpkg: Path) -> Path:
    r = GpkgReader(gpkg)
    route = next(g for _, g in r.rows("route"))
    if route.geom_type == "MultiLineString":
        route = max(route.geoms, key=lambda x: x.length)
    station = next(g for _, g in r.rows("coach_station"))
    listed = []
    for d, g in r.rows("listed_sites"):
        d = {k: v for k, v in d.items() if k != "fid"}
        d["geometry"] = wgs(g)
        listed.append(d)
    plots = []
    for d, g in r.rows("candidate_plots"):
        if not d.get("passes"):
            continue
        d = {k: v for k, v in d.items() if k != "fid"}
        d["geometry"] = wgs(g.simplify(1.0))
        d["centroid"] = wgs(g.representative_point())["coordinates"]
        plots.append(d)
    plots.sort(key=lambda p: p["rank"] or 1e9)
    subs = []
    for d, g in r.rows("substations"):
        if (d.get("kv") or 0) >= 33:
            subs.append({"name": d["name"], "kv": d["kv"], "coordinates": wgs(g)["coordinates"]})
    out = {
        "source": str(gpkg.name),
        "route": {"name": "Bristol Coach Station - London Victoria (ORS driving-hgv)", "length_km": round(route.length / 1000, 2),
                  "geometry": wgs(route.simplify(15.0), 5)},
        "coach_station": wgs(station)["coordinates"],
        "listed_sites": listed,
        "candidate_plots": plots[:40],
        "substations": subs,
    }
    path = ROOT / "data" / "bristol_gis.json"
    path.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} kB): route {out['route']['length_km']} km, "
          f"{len(listed)} listed sites, {len(out['candidate_plots'])} plots, {len(subs)} substations >= 33 kV")
    return path


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GPKG)
