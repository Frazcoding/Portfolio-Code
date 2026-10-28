// Browser-only backend for the static build (tools/build_static.py): the same Python package runs in Pyodide and
// answers the calls the FastAPI server answers in the full app (ember_hub_simulator.webapi.WebApi). External data
// (OSRM routes and tables, Nominatim search, Overpass plots) is fetched here, in the browser, and handed to Python.

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/";   // Pyodide CDN (core + package wheels)
const OSRM = "https://router.project-osrm.org";
const NOMINATIM = "https://nominatim.openstreetmap.org/search";
const OVERPASS = "https://overpass-api.de/api/interpreter";
// Coach time = OSRM car time x factor, calibrated so Bristol Coach Station -> London Victoria gives the sheet's 3:07
// (same reference as ember_hub_simulator.geo.Router).
const REF = { a: [-2.593702, 51.458905], b: [-0.14807, 51.4926], sheet_min: 187.0 };
const YARD_MIN = 3.0;

export class LocalBackend {
  constructor() {
    this.py = null;
    this.api = null;
    this.factor = null;
    this.geoLoaded = false;
    this.lastGeocode = 0;
  }

  async init(status) {
    status("Loading the Python engine (first visit downloads ~25 MB)…");
    await new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = PYODIDE + "pyodide.js"; s.onload = resolve; s.onerror = () => reject(new Error("could not load Pyodide"));
      document.head.appendChild(s);
    });
    this.py = await window.loadPyodide({ indexURL: PYODIDE });
    status("Loading numpy and pandas…");
    await this.py.loadPackage(["numpy", "pandas"]);
    status("Loading the Ember model…");
    const bundle = await (await fetch("static/py_bundle.json")).json();
    for (const [path, text] of Object.entries(bundle)) {
      const full = "/app/" + path, dir = full.slice(0, full.lastIndexOf("/"));
      this.py.FS.mkdirTree(dir);
      this.py.FS.writeFile(full, text);
    }
    this.py.runPython(`
import sys
sys.path.insert(0, "/app/src")
from ember_hub_simulator.config import ProjectPaths
from ember_hub_simulator.runner import Runner
from ember_hub_simulator.webapi import WebApi
_paths = ProjectPaths.discover()
api = WebApi(_paths.baseline, Runner(_paths.root))
`);
    this.api = this.py.globals.get("api");
  }

  call(method, args) {
    try {
      return JSON.parse(this.api.call(method, JSON.stringify(args || {})));
    } catch (e) {
      const lines = String(e.message || e).trim().split("\n");
      throw new Error(lines[lines.length - 1].replace(/^\w+Error: /, ""));
    }
  }

  // ------------------------------------------------------------------ the server's API
  async schema() { return this.call("schema"); }
  async gis() { return this.call("gis"); }
  async evaluate(params, sites) { return this.call("evaluate", { params, sites }); }
  async swept(params) { return this.call("swept", { params }); }
  async save() { throw new Error("saving run folders needs the Python server version (uv run ember-hub-simulator app)"); }

  async json(url, opts) {
    const r = await fetch(url, opts);
    if (!r.ok) throw new Error(`${new URL(url).host} answered ${r.status}`);
    return r.json();
  }

  async geocode(q) {
    const wait = 1100 - (Date.now() - this.lastGeocode);      // Nominatim usage policy: max 1 request per second
    if (wait > 0) await new Promise((r) => setTimeout(r, wait));
    this.lastGeocode = Date.now();
    const u = `${NOMINATIM}?format=jsonv2&limit=5&countrycodes=gb&q=${encodeURIComponent(q)}`;
    const res = await this.json(u, { headers: { "Accept-Language": "en-GB" } });
    return res.map((r) => ({ name: r.display_name, lon: +r.lon, lat: +r.lat, type: r.type || "" }));
  }

  async osrmRoute(a, b, overview) {
    const u = `${OSRM}/route/v1/driving/${a[0]},${a[1]};${b[0]},${b[1]}?overview=${overview}&geometries=geojson&alternatives=false`;
    const r = await this.json(u);
    if (r.code !== "Ok" || !r.routes.length) throw new Error("no route found");
    return r.routes[0];
  }

  async coachFactor() {
    if (this.factor == null) {
      const r = await this.osrmRoute(REF.a, REF.b, "false");
      this.factor = REF.sheet_min / (r.duration / 60);
    }
    return this.factor;
  }

  async route(origin, dest) {
    const [r, k] = await Promise.all([this.osrmRoute(origin, dest, "full"), this.coachFactor()]);
    const pts = r.geometry.coordinates, step = Math.max(1, Math.floor(pts.length / 1500));
    const coords = pts.filter((_, i) => i % step === 0 || i === pts.length - 1).map(([x, y]) => [+x.toFixed(5), +y.toFixed(5)]);
    return { distance_km: Math.round(r.distance / 100) / 10, car_time_min: Math.round(r.duration / 6) / 10,
      drive_time_min: Math.round(r.duration / 60 * k), coach_factor: Math.round(k * 1000) / 1000,
      geometry: { type: "LineString", coordinates: coords } };
  }

  async table(origin, points) {
    const out = [];
    for (let i = 0; i < points.length; i += 90) {
      const chunk = points.slice(i, i + 90);
      const coords = [origin, ...chunk].map((p) => `${p[0].toFixed(6)},${p[1].toFixed(6)}`).join(";");
      const r = await this.json(`${OSRM}/table/v1/driving/${coords}?sources=0&annotations=distance,duration`);
      if (r.code !== "Ok") throw new Error("OSRM table failed");
      r.distances[0].slice(1).forEach((d, j) => {
        const t = r.durations[0][j + 1];
        out.push({ deadrun_km: d == null ? null : Math.round(d / 10) / 100, deadrun_min: t == null ? null : Math.round(t / 60 + YARD_MIN) });
      });
    }
    return out;
  }

  async deadruns(origin, sites) {
    const res = await this.table(origin, sites.map((s) => [s.lon, s.lat]));
    return sites.map((s, i) => ({ id: s.id, ...res[i] }));
  }

  async screen(origin, route) {
    if (!this.geoLoaded) { await this.py.loadPackage(["shapely", "pyproj"]); this.geoLoaded = true; }
    const q = this.call("screen_query", { origin });
    const data = await this.json(OVERPASS, { method: "POST", body: new URLSearchParams({ data: q }) });
    const scored = this.call("screen_score", { data, origin, route, top: 15 });
    let roads = [];
    try { roads = await this.table(origin, scored.best.map((r) => [r.lon, r.lat])); } catch (e) { /* estimates kept */ }
    return this.call("screen_finalize", { scored, roads });
  }
}
