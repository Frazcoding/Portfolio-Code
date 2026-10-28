"""Routing, geocoding and hub-site screening from public OpenStreetMap services (no API keys).

* :class:`Geocoder`  place search (Nominatim, max 1 request/s, identified user agent, cached),
* :class:`Router`    road route and distance / time tables (OSRM public demo server, car profile, cached). Coach drive time
  is the car time times a calibration factor fitted so Bristol Coach Station -> London Victoria gives the sheet's 3:07,
* :class:`SiteScreener` the QGIS screening (Ember-Site-Selection/scripts/01_screen_sites.py) in shapely: OSM brownfield /
  industrial / commercial / greenfield polygons and >= 33 kV substations around the origin (Overpass API), the same
  filters and weighted score, then road dead-runs for the best plots from an OSRM table.

The public servers are for light, non-commercial use; for anything beyond a prototype use an openrouteservice key
(driving-hgv profile) or a self-hosted OSRM / Overpass. Results are cached in ``data/cache`` so a shared prototype makes
few external calls.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, mapping
from shapely.ops import transform


class HttpCache:
    """GET-with-cache: responses stored as JSON under ``data/cache/<service>/<sha1>.json``."""

    USER_AGENT: ClassVar[str] = "EmberHubSimulator/0.1 (coach hub planning prototype)"

    def __init__(self, cache_dir: Path, service: str, min_interval_s: float = 0.0, timeout_s: float = 60.0):
        self.dir = Path(cache_dir) / service
        self.min_interval_s = min_interval_s
        self.timeout_s = timeout_s
        self._last = 0.0
        self._lock = threading.Lock()

    def get(self, url: str, params: dict | None = None, data: dict | None = None) -> Any:
        key = hashlib.sha1(json.dumps([url, params, data], sort_keys=True).encode()).hexdigest()
        path = self.dir / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        with self._lock:
            wait = self.min_interval_s - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            import httpx   # server only (the browser build fetches in JavaScript)

            headers = {"User-Agent": self.USER_AGENT, "Accept-Language": "en-GB"}
            with httpx.Client(timeout=self.timeout_s, headers=headers, follow_redirects=True) as c:
                r = c.post(url, data=data) if data is not None else c.get(url, params=params)
            self._last = time.monotonic()
        r.raise_for_status()
        out = r.json()
        self.dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out), encoding="utf-8")
        return out


class Geocoder:
    """Place search with Nominatim (https://nominatim.org/release-docs/latest/api/Search/)."""

    URL: ClassVar[str] = "https://nominatim.openstreetmap.org/search"

    def __init__(self, cache_dir: Path):
        self.http = HttpCache(cache_dir, "nominatim", min_interval_s=1.1)

    def search(self, q: str, limit: int = 5) -> list[dict]:
        q = q.strip()
        if not q:
            return []
        res = self.http.get(self.URL, {"q": q, "format": "jsonv2", "limit": limit, "countrycodes": "gb"})
        return [{"name": r["display_name"], "lon": float(r["lon"]), "lat": float(r["lat"]), "type": r.get("type", "")} for r in res]


class Router:
    """Road routes and distance / duration tables from OSRM (http://project-osrm.org/docs/v5.24.0/api/)."""

    URL: ClassVar[str] = "https://router.project-osrm.org"
    # Calibration: sheet drive time 187 min for Bristol Coach Station -> London Victoria (191.5 km). The coach factor is
    # sheet time / OSRM car time for that pair, computed on first use and cached.
    REF: ClassVar[tuple] = ((-2.593702, 51.458905), (-0.14807, 51.4926), 187.0)
    YARD_MIN: ClassVar[float] = 3.0          # yard time added to a dead run (as in the QGIS screening)

    def __init__(self, cache_dir: Path):
        self.http = HttpCache(cache_dir, "osrm", min_interval_s=0.3)
        self._factor: float | None = None

    @staticmethod
    def _coords(points) -> str:
        return ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in points)

    def raw_route(self, a, b) -> dict:
        res = self.http.get(f"{self.URL}/route/v1/driving/{self._coords([a, b])}",
                            {"overview": "full", "geometries": "geojson", "alternatives": "false"})
        if res.get("code") != "Ok" or not res.get("routes"):
            raise ValueError(f"no route found ({res.get('code')})")
        return res["routes"][0]

    @property
    def coach_factor(self) -> float:
        if self._factor is None:
            a, b, sheet_min = self.REF
            car_min = self.raw_route(a, b)["duration"] / 60.0
            self._factor = sheet_min / car_min
        return self._factor

    def route(self, a, b) -> dict:
        """One-way coach route: distance (km), coach drive time (min), car time (min) and the line (lon/lat)."""
        r = self.raw_route(a, b)
        return {"distance_km": round(r["distance"] / 1000.0, 1), "car_time_min": round(r["duration"] / 60.0, 1),
                "drive_time_min": round(r["duration"] / 60.0 * self.coach_factor), "coach_factor": round(self.coach_factor, 3),
                "geometry": self.thin(r["geometry"])}

    @staticmethod
    def thin(geometry: dict, tol_deg: float = 2e-4) -> dict:
        """Full-resolution route line simplified to ~20 m (keeps the map light without cutting corners)."""
        line = LineString(geometry["coordinates"]).simplify(tol_deg)
        return {"type": "LineString", "coordinates": [[round(x, 5), round(y, 5)] for x, y in line.coords]}

    def table_from(self, origin, points) -> list[dict]:
        """Road distance (km) and dead-run time (min, car time + yard time) from ``origin`` to each point."""
        if not points:
            return []
        out = []
        for k in range(0, len(points), 90):                  # public server limit is 100 coordinates
            chunk = points[k:k + 90]
            res = self.http.get(f"{self.URL}/table/v1/driving/{self._coords([origin] + chunk)}",
                                {"sources": "0", "annotations": "distance,duration"})
            if res.get("code") != "Ok":
                raise ValueError(f"OSRM table failed ({res.get('code')})")
            for d, t in zip(res["distances"][0][1:], res["durations"][0][1:]):
                out.append({"deadrun_km": None if d is None else round(d / 1000.0, 2),
                            "deadrun_min": None if t is None else round(t / 60.0 + self.YARD_MIN)})
        return out


@dataclass
class LocalProjection:
    """Azimuthal equidistant projection centred on a point (metres), adequate for distances and areas within ~30 km."""

    lon0: float
    lat0: float

    def __post_init__(self):
        proj = f"+proj=aeqd +lat_0={self.lat0} +lon_0={self.lon0} +datum=WGS84 +units=m"
        self.fwd = Transformer.from_crs("EPSG:4326", proj, always_xy=True).transform
        self.inv = Transformer.from_crs(proj, "EPSG:4326", always_xy=True).transform

    def to_m(self, geom):
        return transform(self.fwd, geom)

    def to_lonlat(self, geom):
        return transform(self.inv, geom)


class SiteScreener:
    """OSM hub-site screening around a route origin (criteria and weights from the QGIS screening, keep in step)."""

    OVERPASS: ClassVar[str] = "https://overpass-api.de/api/interpreter"
    MIN_AREA_M2: ClassVar[float] = 4000
    MAX_AREA_M2: ClassVar[float] = 60000
    MIN_SHORT_SIDE_M: ClassVar[float] = 40
    MAX_DEADRUN_KM: ClassVar[float] = 15
    ROAD_FACTOR: ClassVar[float] = 1.4
    WEIGHTS: ClassVar[dict] = dict(deadrun=0.40, grid=0.25, area=0.15, shape=0.10, landuse=0.10)
    LANDUSE_SCORE: ClassVar[dict] = {"brownfield": 1.0, "industrial": 1.0, "commercial": 0.6, "greenfield": 0.2}
    DEFAULT_LEASE_GBP_M2_YR: ClassVar[float] = 20.0
    DEFAULT_SPARE_GRID_KVA: ClassVar[float] = 1000.0

    def __init__(self, cache_dir: Path | None = None, router: Router | None = None):
        """``cache_dir`` and ``router`` are needed only by :meth:`screen` (network); scoring is pure."""
        self.http = HttpCache(cache_dir, "overpass", min_interval_s=2.0, timeout_s=120.0) if cache_dir else None
        self.router = router

    @staticmethod
    def lin(v, good, bad):
        """Linear 0..1 score: 1 at ``good``, 0 at ``bad``."""
        if good < bad:
            return max(0.0, min(1.0, (bad - v) / (bad - good)))
        return max(0.0, min(1.0, (v - bad) / (good - bad)))

    @classmethod
    def radius_m(cls) -> float:
        """Search radius around the origin: the dead-run limit as a straight line."""
        return cls.MAX_DEADRUN_KM * 1000.0 / cls.ROAD_FACTOR

    @classmethod
    def query_text(cls, lon: float, lat: float) -> str:
        """Overpass QL for land-use polygons and substations around the origin (the browser build posts this itself)."""
        lu = "^(brownfield|industrial|commercial|greenfield)$"
        r = cls.radius_m()
        return f"""[out:json][timeout:90];
(
  way["landuse"~"{lu}"](around:{r:.0f},{lat:.6f},{lon:.6f});
  node["power"="substation"](around:{r + 3000:.0f},{lat:.6f},{lon:.6f});
  way["power"="substation"](around:{r + 3000:.0f},{lat:.6f},{lon:.6f});
);
out tags geom;"""

    def screen(self, origin: tuple[float, float], route_geometry: dict | None = None, top: int = 15) -> dict:
        """Query Overpass, score the plots, add OSRM road dead-runs for the best ``top``."""
        data = self.http.get(self.OVERPASS, data={"data": self.query_text(*origin)})
        scored = self.score(data, origin, route_geometry, top)
        roads = self.router.table_from(origin, [(r["lon"], r["lat"]) for r in scored["best"]])
        return self.finalize(scored, roads)

    def score(self, data: dict, origin: tuple[float, float], route_geometry: dict | None = None, top: int = 15) -> dict:
        """Filter and score the Overpass result (pure: no network). Returns the best ``top`` rows and the substations."""
        lon0, lat0 = origin
        proj = LocalProjection(lon0, lat0)
        station = Point(0.0, 0.0)
        route = None
        if route_geometry:
            route = proj.to_m(LineString(route_geometry["coordinates"]))

        subs = []
        plots = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            if tags.get("power") == "substation":
                if el["type"] == "node":
                    pt = proj.to_m(Point(el["lon"], el["lat"]))
                elif el.get("geometry"):
                    pt = proj.to_m(Polygon([(g["lon"], g["lat"]) for g in el["geometry"]]) if len(el["geometry"]) >= 4
                                   else Point(el["geometry"][0]["lon"], el["geometry"][0]["lat"])).centroid
                else:
                    continue
                volts = [int(v) for v in tags.get("voltage", "").replace(" ", "").split(";") if v.isdigit()]
                subs.append({"pt": pt, "name": tags.get("name", "Substation"), "vmax": max(volts) if volts else 0})
            elif el["type"] == "way" and el.get("geometry") and len(el["geometry"]) >= 4:
                poly = Polygon([(g["lon"], g["lat"]) for g in el["geometry"]])
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if poly.is_empty:
                    continue
                plots.append((el["id"], tags, poly))
        primaries = [s for s in subs if s["vmax"] >= 33000]

        rows = []
        for osm_id, tags, poly_ll in plots:
            g = proj.to_m(poly_ll)
            area = g.area
            rect = g.minimum_rotated_rectangle
            xs = list(rect.exterior.coords)
            sides = sorted({round(math.dist(xs[i], xs[i + 1]), 3) for i in range(4)})
            short, long_ = (sides[0], sides[-1]) if sides else (0.0, 0.0)
            c = g.representative_point()
            direct = self.ROAD_FACTOR * c.distance(station)
            dr = direct
            if route is not None:
                dr = min(direct, route.project(c) + self.ROAD_FACTOR * route.distance(c))
            dr_km = dr / 1000.0
            prim = min(((c.distance(s["pt"]), s) for s in primaries), default=None, key=lambda x: x[0])
            reasons = []
            if area < self.MIN_AREA_M2:
                reasons.append("too small")
            if short < self.MIN_SHORT_SIDE_M:
                reasons.append("too narrow")
            if dr_km > self.MAX_DEADRUN_KM:
                reasons.append("dead-run > 15 km")
            if area > self.MAX_AREA_M2:
                reasons.append("whole estate - needs subdivision")
            if reasons and reasons != ["whole estate - needs subdivision"]:
                continue
            landuse = tags.get("landuse", "industrial")
            W = self.WEIGHTS
            score = 100 * (W["deadrun"] * self.lin(dr_km, 1, self.MAX_DEADRUN_KM)
                           + W["grid"] * self.lin(prim[0] if prim else 5000, 250, 2500)
                           + W["area"] * (1.0 if 5000 <= area <= 20000 else 0.6)
                           + W["shape"] * self.lin(short, 70, self.MIN_SHORT_SIDE_M)
                           + W["landuse"] * self.LANDUSE_SCORE.get(landuse, 0.5))
            cl = proj.to_lonlat(c)
            rows.append({"osm_id": osm_id, "landuse": landuse, "name": tags.get("name", ""), "area_m2": round(area),
                         "short_side_m": round(short, 1), "deadrun_est_km": round(dr_km, 2),
                         "primary_sub": prim[1]["name"] if prim else "", "grid_distance_m": round(prim[0]) if prim else 5000,
                         "score": round(score, 1), "note": "; ".join(reasons), "lon": round(cl.x, 6), "lat": round(cl.y, 6),
                         "geometry": json.loads(json.dumps(mapping(poly_ll.simplify(0.00002))),
                                                parse_float=lambda s: round(float(s), 6))})
        rows.sort(key=lambda r: -r["score"])
        subs_ll = [{"name": s["name"], "kv": s["vmax"] // 1000, "coordinates": list(proj.to_lonlat(s["pt"]).coords[0])}
                   for s in primaries]
        return {"origin": list(origin), "screened": len(plots), "passed": len(rows), "best": rows[:top], "substations": subs_ll}

    def finalize(self, scored: dict, roads: list[dict]) -> dict:
        """Candidate sites from the scored rows and their road dead-runs (``Router.table_from`` rows, or Nones)."""
        best = scored["best"]
        roads = list(roads) + [{"deadrun_km": None, "deadrun_min": None}] * (len(best) - len(roads))
        sites = []
        for k, (r, rd) in enumerate(zip(best, roads), 1):
            km = rd["deadrun_km"] if rd["deadrun_km"] is not None else r["deadrun_est_km"]
            mins = rd["deadrun_min"] if rd["deadrun_min"] is not None else round(km / 35 * 60 + 3)
            name = r["name"] or f"{r['landuse'].title()} plot"
            sites.append({"id": f"Q{k:02d}", "name": f"Q{k:02d} {name}", "lon": r["lon"], "lat": r["lat"],
                          "deadrun_km": km, "deadrun_min": mins, "area_m2": r["area_m2"],
                          "lease_gbp_per_m2_yr": self.DEFAULT_LEASE_GBP_M2_YR, "grid_distance_m": r["grid_distance_m"],
                          "spare_grid_kVA": self.DEFAULT_SPARE_GRID_KVA, "kind": "screened", "landuse": r["landuse"],
                          "score": r["score"], "screen_rank": k, "primary_sub": r["primary_sub"], "osm_id": r["osm_id"],
                          "geometry": r["geometry"], "note": r["note"],
                          "placeholder": ["lease_gbp_per_m2_yr", "spare_grid_kVA"]})
        return {"origin": scored["origin"], "screened": scored["screened"], "passed": scored["passed"], "sites": sites,
                "substations": scored["substations"]}
