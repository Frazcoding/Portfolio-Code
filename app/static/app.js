// Ember Hub Simulator front end: wires the Sim Workbench components (window.SimWorkbench, bundle.js) to the FastAPI
// endpoints. Inputs re-run the model live (POST /api/evaluate); one playhead (minute index of the operating day) drives the
// map, the hub plan, the 3D hub, the indicators and the time series.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const SW = window.SimWorkbench;
const LF = window.L;
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Design-system gap: timeSeries() hard-codes the axis label "t [Myr]" (astrophysics demo). Our time axis is hours.
const _fillText = CanvasRenderingContext2D.prototype.fillText;
CanvasRenderingContext2D.prototype.fillText = function (text, ...rest) {
  return _fillText.call(this, text === "t [Myr]" ? "t [h]" : text, ...rest);
};

const MODE = { PARKED: 0, OUT: 1, OUTBOUND: 2, TURN: 3, INBOUND: 4, IN: 5, QUEUED: 6, CHARGING: 7 };
const MODE_LABEL = ["Parked", "Dead run out", "Outbound", "Turnaround", "Inbound", "Dead run in", "Queued", "Charging"];
const AT_HUB = new Set([MODE.PARKED, MODE.QUEUED, MODE.CHARGING]);
const BRISTOL = [-2.593702, 51.458905];

/* ------------------------------------------------------------------------------------------------ helpers */
class Fmt {
  static num(v, dec = 0) {
    if (v == null || !isFinite(v)) return "â€“";
    return Number(v).toLocaleString("en-GB", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }
  static gbp(v) { return v == null || !isFinite(v) ? "â€“" : "Â£" + Fmt.num(v, 0); }
  static hm(min) {
    if (min == null || !isFinite(min)) return "â€“";
    const neg = min < 0, m = Math.round(Math.abs(min)), h = Math.floor(m / 60);
    return (neg ? "âˆ’" : "") + h + ":" + String(m % 60).padStart(2, "0");
  }
  static clock(hours) {
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const d = Math.floor(hours / 24), m = Math.round((hours - d * 24) * 60);
    return `${days[d % 7]} ${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
  }
  static km(a, b) {   // great-circle distance between [lon, lat] points (km)
    const R = 6371, r = Math.PI / 180, dLat = (b[1] - a[1]) * r, dLon = (b[0] - a[0]) * r;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * r) * Math.cos(b[1] * r) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }
}

class Ramps {
  // SOC 0..1 -> red / amber / green
  static soc(f) {
    f = Math.max(0, Math.min(1, f));
    const stops = [[0, [215, 48, 31]], [0.35, [240, 140, 46]], [0.65, [230, 205, 60]], [1, [47, 180, 110]]];
    for (let i = 1; i < stops.length; i++) {
      if (f <= stops[i][0]) {
        const [t0, c0] = stops[i - 1], [t1, c1] = stops[i], k = (f - t0) / (t1 - t0);
        return c0.map((c, j) => Math.round(c + (c1[j] - c) * k));
      }
    }
    return stops[stops.length - 1][1];
  }
  static css(rgb) { return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`; }
}

/* ------------------------------------------------------------------------------------------------ API */
class Api {
  async json(url, opts) {
    const r = await fetch(url, opts);
    if (!r.ok) {
      let detail = r.statusText;
      try { detail = (await r.json()).detail || detail; } catch (e) { /* not JSON */ }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return r.json();
  }
  post(url, body) { return this.json(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); }
  schema() { return this.json("/api/schema"); }
  gis() { return this.json("/api/gis"); }
  evaluate(params, sites) { return this.post("/api/evaluate", { params, sites }); }
  save(params, sites, name) { return this.post("/api/run", { params, sites, name }); }
  geocode(q) { return this.json("/api/geocode?q=" + encodeURIComponent(q)); }
  route(origin, dest) { return this.post("/api/route", { origin, dest }); }
  deadruns(origin, sites) { return this.post("/api/deadruns", { origin, sites }); }
  screen(origin, route) { return this.post("/api/screen", { origin, route, top: 15 }); }
  swept(params) { return this.post("/api/swept", { params }); }
}

/* ------------------------------------------------------------------------------------------------ design geometry */
// The hub design comes from Ember-Site-Selection (scripts/hub_design.py, EMB-HUB-003 / -005), in the project's local site
// grid (u along the railway boundary, v north-west, metres). frame.affine maps it to lon/lat for the map.
class Geo {
  static rings(g) {
    if (!g) return [];
    if (g.type === "Polygon") return [g.coordinates[0]];
    if (g.type === "MultiPolygon") return g.coordinates.map((p) => p[0]);
    return [];
  }
  static lines(g) {
    if (!g) return [];
    if (g.type === "LineString") return [g.coordinates];
    if (g.type === "MultiLineString") return g.coordinates;
    if (g.type === "Polygon" || g.type === "MultiPolygon") return Geo.rings(g);
    return [];
  }
  static centroid(ring) {
    let x = 0, y = 0;
    const n = ring.length - (ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1] ? 1 : 0);
    for (let i = 0; i < n; i++) { x += ring[i][0]; y += ring[i][1]; }
    return [x / n, y / n];
  }
  /** lon/lat of a local point: [lat, lon] for Leaflet. */
  static ll(frame, u, v) {
    const [lon0, lat0, lu, au, lv, av] = frame.affine;
    return [lat0 + au * u + av * v, lon0 + lu * u + lv * v];
  }
}

/** Colours and drawing order of the design features (the palette of scripts/12_blender_design.py). */
const DESIGN_STYLE = {
  title: { stroke: "#d4a72c", dash: [7, 5], width: 1.6 },
  yard: { fill: "#b4b2ab" },
  tree_bank: { fill: "#3c6b2f" },
  road_ext: { fill: "#55575b" },
  gate: { fill: "#f2c200", alpha: 0.55 },
  landscape: { fill: "#8fbf6f" },
  island: { fill: "#7fae63" },
  car_park: { fill: "#55575b" },
  footway: { fill: "#d9d2c3" },
  lane: { fill: "#3e4145", stroke: "#f2f2ee", width: 1 },
  lane_new: { fill: "#3e4145", stroke: "#f2c200", width: 1.4, dash: [5, 3] },
  car_bay: { stroke: "#f2f2ee", width: 0.8 },
  wash: { fill: "#9bd0ee" },
  building: { fill: "#e8e8e4", stroke: "#0f6e6e", width: 1.2 },
  grid: { fill: "#f2c200" },
  charger: { fill: "#9aa0a6" },
  kerb: { stroke: "#6d7a72", width: 1.6 },
  fence: { stroke: "#6d7a72", width: 2.2 },
  cable: { stroke: "#f2c200", width: 3 },
  aisle_arrow: { stroke: "#ffffff", width: 1.4, dash: [6, 4], arrow: true },
};
const DESIGN_ORDER = ["title", "yard", "tree_bank", "road_ext", "gate", "landscape", "island", "car_park", "footway", "lane",
  "lane_new", "car_bay", "wash", "building", "grid", "charger", "kerb", "fence", "cable", "aisle_arrow"];

/* ------------------------------------------------------------------------------------------------ fleet state */
class Fleet {
  constructor(run) {
    this.run = run;
    this.n = run.selected.fleet_total;
    this.layout = run.layout;
  }
  at(i) {
    const d = this.run.data, out = [];
    for (let j = 1; j <= this.n; j++) {
      out.push({ idx: j, mode: d[`c${j}_mode`][i], prog: d[`c${j}_prog`][i], soc: d[`c${j}_soc`][i] / 100, chg: d[`c${j}_chg`][i] });
    }
    return out;
  }
  /** Coaches at the hub placed in the design's drive-through lanes: charging coaches in the lanes wired to the gantry
   *  (lanes 1-4), parked coaches in the other lanes first, queued coaches on the inbound aisle behind the gate.
   *  Returns Map idx -> {x, y, heading, kind, lane}. A coach with no free lane is not drawn. */
  placements(coaches) {
    const L = this.layout, pos = new Map();
    if (!L || !L.slots) return pos;
    const wired = L.slots.filter((s) => s.wired), used = new Set();
    for (const c of coaches) {
      if (c.mode === MODE.CHARGING && c.chg >= 0) {
        const s = wired[c.chg % Math.max(wired.length, 1)];
        if (s && !used.has(s.n)) { pos.set(c.idx, { ...s, kind: "charging" }); used.add(s.n); }
      }
    }
    const free = L.slots.filter((s) => !used.has(s.n)).sort((a, b) => a.wired - b.wired || a.n - b.n);
    let q = 0;
    for (const c of coaches) {
      if (c.mode === MODE.PARKED) {
        const s = free.shift();
        if (s) pos.set(c.idx, { ...s, kind: "parked" });
      } else if (c.mode === MODE.QUEUED) {
        const spot = L.queue[q] || L.queue[L.queue.length - 1];
        if (spot) pos.set(c.idx, { ...spot, length: L.slots[0].length, width: L.slots[0].width, kind: "queued", lane: "queue" });
        q++;
      }
    }
    return pos;
  }
}

/* ------------------------------------------------------------------------------------------------ map view */
class MapView {
  constructor(el, page) {
    this.page = page;
    this.map = LF.map(el, { zoomControl: false, attributionControl: true }).setView([51.47, -1.6], 8);
    LF.control.zoom({ position: "bottomright" }).addTo(this.map);
    LF.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(this.map);
    this.route = LF.layerGroup().addTo(this.map);
    this.deadrun = LF.layerGroup().addTo(this.map);
    this.plots = LF.layerGroup().addTo(this.map);
    this.subs = LF.layerGroup();
    this.sites = LF.layerGroup().addTo(this.map);
    this.layout = LF.layerGroup().addTo(this.map);
    this.coaches = LF.layerGroup().addTo(this.map);
    LF.control.layers(null, { "Route": this.route, "Dead run": this.deadrun, "Candidate sites": this.sites,
      "Screened plots": this.plots, "33 kV+ substations": this.subs, "Hub design": this.layout, "Coaches": this.coaches },
    { collapsed: true }).addTo(this.map);
    LF.control.scale({ imperial: false, position: "bottomleft" }).addTo(this.map);
    this.map.on("click", (e) => page.onMapClick([e.latlng.lng, e.latlng.lat]));
    this.main = null;
    this.dead = null;
    this.frame = null;
  }
  invalidate() { setTimeout(() => this.map.invalidateSize(), 30); }

  /** A polyline (lon/lat) with cumulative chainage, for placing coaches by leg progress. */
  static path(coords) {
    const k = Math.cos(coords[0][1] * Math.PI / 180), cum = [0];
    for (let i = 1; i < coords.length; i++) {
      const a = coords[i - 1], b = coords[i];
      cum.push(cum[i - 1] + Math.hypot((b[0] - a[0]) * k, b[1] - a[1]));
    }
    return { coords, cum };
  }
  static along(path, f) {
    const c = path.cum, L = path.coords, s = Math.max(0, Math.min(1, f)) * c[c.length - 1];
    let lo = 0, hi = c.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (c[m] <= s) lo = m; else hi = m; }
    const t = c[hi] > c[lo] ? (s - c[lo]) / (c[hi] - c[lo]) : 0;
    return [L[lo][1] + (L[hi][1] - L[lo][1]) * t, L[lo][0] + (L[hi][0] - L[lo][0]) * t];
  }

  setRoute(geom, origin, dest, names) {
    this.route.clearLayers();
    const line = (geom && geom.coordinates) || [origin, dest];
    LF.polyline(line.map(([x, y]) => [y, x]), { color: SW.token("accent"), weight: 4, opacity: 0.85 }).addTo(this.route);
    const end = (p, label, col) => LF.circleMarker([p[1], p[0]], { radius: 8, color: "#fff", weight: 2, fillColor: col, fillOpacity: 1 })
      .bindTooltip(label, { direction: "top" }).addTo(this.route);
    end(origin, "Origin: " + names[0], SW.token("series-1"));
    end(dest, "Destination: " + names[1], SW.token("series-2"));
    this.main = MapView.path(line);
  }

  setSites(sites, selectedId, origin, deadrunRoute) {
    this.sites.clearLayers();
    this.plots.clearLayers();
    for (const s of sites) {
      const sel = s.id === selectedId;
      if (s.geometry && s.geometry.type !== "Point") {
        LF.geoJSON(s.geometry, { style: { color: sel ? SW.token("accent") : SW.token("series-3"), weight: sel ? 2.5 : 1.2, fillOpacity: sel ? 0.25 : 0.12 } })
          .on("click", (e) => { LF.DomEvent.stopPropagation(e); this.page.selectSite(s.id); })
          .bindTooltip(esc(s.name)).addTo(this.plots);
      }
      const color = s.kind === "listed" ? SW.token("series-6") : s.kind === "custom" ? SW.token("series-7") : SW.token("series-3");
      const m = LF.circleMarker([s.lat, s.lon], { radius: sel ? 9 : 6, color: sel ? SW.token("ink") : "#fff", weight: sel ? 3 : 1.5, fillColor: color, fillOpacity: 0.95 });
      const r = this.page.siteResult(s.id);
      const res = r ? `<br>Fleet ${r.fleet_total} Â· chargers ${r.total_chargers} Â· drivers ${r.drivers}<br>${Fmt.gbp(r.total_gbp_yr)}/yr Â· ${Fmt.gbp(r.gbp_per_trip)}/trip<br>${r.feasible ? '<span style="color:var(--ok)">Feasible</span>' + (r.rank ? ` Â· rank ${r.rank}` : "") : '<span style="color:var(--err)">Not feasible</span>'}` : "";
      m.bindPopup(`<b>${esc(s.name)}</b><br>Dead run ${Fmt.num(s.deadrun_km, 1)} km / ${Fmt.num(s.deadrun_min)} min Â· ${Fmt.num(s.area_m2)} mÂ²${s.status ? "<br>" + esc(s.status) : ""}${s.design ? `<br>Hub design: ${esc(s.design)}` : ""}${res}<br>${sel ? "<i>Selected</i>" : `<button class="sw-btn" data-pick="${esc(s.id)}">Use this site</button>`}`);
      m.on("popupopen", (e) => {
        const b = e.popup.getElement().querySelector("[data-pick]");
        if (b) b.addEventListener("click", () => { this.map.closePopup(); this.page.selectSite(b.dataset.pick); });
      });
      m.addTo(this.sites);
    }
    this.deadrun.clearLayers();
    this.dead = null;
    const s = sites.find((x) => x.id === selectedId);
    if (s && origin) {
      if (deadrunRoute) {          // the ORS route from the project (coach station -> hub)
        const c = deadrunRoute.geometry.coordinates;
        LF.polyline(c.map(([x, y]) => [y, x]), { color: SW.token("series-6"), weight: 4, opacity: 0.9 })
          .bindTooltip(`Dead run (ORS driving-hgv): ${Fmt.num(deadrunRoute.distance_km, 1)} km, ${Fmt.num(deadrunRoute.duration_min, 1)} min`).addTo(this.deadrun);
        this.dead = MapView.path(c);
      } else {
        LF.polyline([[s.lat, s.lon], [origin[1], origin[0]]], { color: SW.token("series-6"), weight: 2.5, dashArray: "6 6" })
          .bindTooltip(`Dead run ${Fmt.num(s.deadrun_km, 1)} km, ${Fmt.num(s.deadrun_min)} min (straight line shown)`).addTo(this.deadrun);
        this.dead = MapView.path([[origin[0], origin[1]], [s.lon, s.lat]]);
      }
    }
  }

  setSubstations(subs) {
    this.subs.clearLayers();
    for (const s of subs || []) {
      LF.circleMarker([s.coordinates[1], s.coordinates[0]], { radius: 4, color: SW.token("warn"), weight: 1, fillOpacity: 0.8 })
        .bindTooltip(`${esc(s.name)} (${s.kv} kV)`).addTo(this.subs);
    }
  }

  /** The hub design drawn in place (only for the site it was designed for). */
  setLayout(layout) {
    this.layout.clearLayers();
    this.frame = layout && layout.site_specific ? layout.frame : null;
    if (!this.frame) return;
    const kinds = new Set(["title", "yard", "tree_bank", "landscape", "island", "car_park", "lane", "lane_new", "wash", "building", "grid", "gate"]);
    for (const k of DESIGN_ORDER) {
      if (!kinds.has(k)) continue;
      const st = DESIGN_STYLE[k];
      for (const f of layout.features.filter((f) => f.kind === k)) {
        for (const r of Geo.rings(f.geom)) {
          LF.polygon(r.map(([u, v]) => Geo.ll(this.frame, u, v)), {
            color: k === "title" ? (layout.fits ? SW.token("ok") : SW.token("err")) : st.stroke || st.fill,
            weight: k === "title" ? 2 : 0.6, fill: k !== "title", fillColor: st.fill, fillOpacity: k === "yard" ? 0.55 : 0.85,
            dashArray: k === "title" ? "5 4" : null, interactive: !!f.label && k !== "yard" && k !== "title",
          }).bindTooltip(esc(f.label || k)).addTo(this.layout);
        }
      }
    }
  }

  setCoaches(coaches, placements, site) {
    this.coaches.clearLayers();
    if (!this.main || !site) return;
    const hub = [site.lat, site.lon];
    for (const c of coaches) {
      let ll;
      if (c.mode === MODE.OUT) ll = this.dead ? MapView.along(this.dead, 1 - c.prog) : hub;      // hub -> coach station
      else if (c.mode === MODE.OUTBOUND) ll = MapView.along(this.main, c.prog);
      else if (c.mode === MODE.TURN) ll = MapView.along(this.main, 1);
      else if (c.mode === MODE.INBOUND) ll = MapView.along(this.main, 1 - c.prog);
      else if (c.mode === MODE.IN) ll = this.dead ? MapView.along(this.dead, c.prog) : hub;      // coach station -> hub
      else {
        const p = placements.get(c.idx);
        ll = p && this.frame ? Geo.ll(this.frame, p.x, p.y) : hub;
      }
      const col = Ramps.css(Ramps.soc(c.soc));
      const icon = LF.divIcon({ className: "eb-coach-icon", iconSize: [18, 18], html: `<div style="background:${col}">${c.idx}</div>` });
      LF.marker(ll, { icon, interactive: true, keyboard: false })
        .bindTooltip(`Coach ${c.idx}: ${MODE_LABEL[c.mode]} Â· SOC ${Fmt.num(c.soc * 100)} %`).addTo(this.coaches);
    }
  }

  fitRoute(origin, dest, site) {
    this.map.invalidateSize();
    const pts = [[origin[1], origin[0]], [dest[1], dest[0]]];
    if (site) pts.push([site.lat, site.lon]);
    this.map.fitBounds(LF.latLngBounds(pts).pad(0.12));
  }
  fitSite(site) { if (site) this.map.setView([site.lat, site.lon], 17); }
}

/* ------------------------------------------------------------------------------------------------ plan view */
class PlanView {
  constructor(canvas, host) {
    this.canvas = canvas;
    this.host = host;
    this.layout = null;
    this.swept = null;
    this.view = null;           // {s, ox, oy}: px per m and origin
    this.drag = null;
    new ResizeObserver(() => this.draw()).observe(host);
    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      if (!this.view) return;
      const r = canvas.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top, k = Math.exp(-e.deltaY * 0.0015);
      this.view.ox = mx - (mx - this.view.ox) * k; this.view.oy = my - (my - this.view.oy) * k; this.view.s *= k;
      this.draw();
    }, { passive: false });
    canvas.addEventListener("pointerdown", (e) => { this.drag = [e.clientX, e.clientY]; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener("pointermove", (e) => {
      if (!this.drag || !this.view) return;
      this.view.ox += e.clientX - this.drag[0]; this.view.oy += e.clientY - this.drag[1]; this.drag = [e.clientX, e.clientY];
      this.draw();
    });
    canvas.addEventListener("pointerup", () => { this.drag = null; });
    canvas.addEventListener("dblclick", () => { this.view = null; this.draw(); });
  }

  setLayout(layout) {
    if (!this.layout || this.layout.name !== layout.name) { this.view = null; this.swept = null; }
    this.layout = layout;
    this.draw();
  }
  setSwept(envelopes) { this.swept = envelopes; this.draw(); }
  setState(coaches, placements) { this.coaches = coaches; this.placements = placements; this.draw(); }

  fitView(w, h) {
    const [x0, y0, x1, y1] = this.layout.bounds, pad = 6;
    const s = Math.min(w / (x1 - x0 + 2 * pad), h / (y1 - y0 + 2 * pad));
    this.view = { s, ox: (w - (x1 - x0) * s) / 2 - x0 * s, oy: (h + (y1 - y0) * s) / 2 + y0 * s };
  }

  draw() {
    if (this.canvas.hidden) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2), w = this.host.clientWidth, h = this.host.clientHeight;
    if (!w || !h) return;
    this.canvas.width = w * dpr; this.canvas.height = h * dpr;
    const ctx = this.canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = SW.token("bg-viewport"); ctx.fillRect(0, 0, w, h);
    const lay = this.layout;
    if (!lay || !lay.features) return;
    if (!this.view) this.fitView(w, h);
    const { s, ox, oy } = this.view, X = (u) => ox + u * s, Y = (v) => oy - v * s;
    const path = (pts, close) => {
      ctx.beginPath();
      pts.forEach(([u, v], k) => (k ? ctx.lineTo(X(u), Y(v)) : ctx.moveTo(X(u), Y(v))));
      if (close) ctx.closePath();
    };
    for (const k of DESIGN_ORDER) {
      const st = DESIGN_STYLE[k];
      for (const f of lay.features) {
        if (f.kind !== k) continue;
        const isPoly = f.geom.type === "Polygon" || f.geom.type === "MultiPolygon";
        const shapes = isPoly ? Geo.rings(f.geom) : Geo.lines(f.geom);
        for (const pts of shapes) {
          path(pts, isPoly);
          if (isPoly && st.fill) {
            ctx.globalAlpha = st.alpha ?? 1;
            ctx.fillStyle = k === "grid" && /substation|switch/i.test(f.label) ? "#6f7f6a" : st.fill;
            ctx.fill(); ctx.globalAlpha = 1;
          }
          if (st.stroke) {
            ctx.strokeStyle = k === "title" ? (lay.fits ? SW.token("ok") : SW.token("err")) : st.stroke;
            ctx.lineWidth = st.width || 1; ctx.setLineDash(st.dash || []); ctx.stroke(); ctx.setLineDash([]);
          }
          if (st.arrow && pts.length > 1) {
            const [ua, va] = pts[pts.length - 2], [ub, vb] = pts[pts.length - 1], a = Math.atan2(-(vb - va), ub - ua);
            ctx.fillStyle = st.stroke; ctx.beginPath();
            ctx.moveTo(X(ub), Y(vb));
            ctx.lineTo(X(ub) - 9 * Math.cos(a - 0.4), Y(vb) - 9 * Math.sin(a - 0.4));
            ctx.lineTo(X(ub) - 9 * Math.cos(a + 0.4), Y(vb) - 9 * Math.sin(a + 0.4));
            ctx.fill();
          }
        }
      }
    }
    // swept envelopes (the design's own checks)
    if (this.swept) {
      for (const f of this.swept) {
        const fail = /clearance -/.test(f.label);
        ctx.fillStyle = fail ? "rgba(255,90,80,0.22)" : "rgba(76,201,214,0.08)";
        ctx.strokeStyle = fail ? "rgba(255,90,80,0.9)" : "rgba(76,201,214,0.5)";
        ctx.lineWidth = 1;
        for (const r of Geo.rings(f.geom)) { path(r, true); ctx.fill(); ctx.stroke(); }
      }
    }
    // labels
    if (s > 3.2) {
      ctx.font = `${Math.min(12, Math.max(9, 0.75 * s))}px "IBM Plex Sans", sans-serif`;
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      for (const f of lay.features) {
        if (!["building", "grid", "wash", "lane", "lane_new", "car_park"].includes(f.kind) || !f.label) continue;
        const r = Geo.rings(f.geom)[0];
        if (!r) continue;
        const [cu, cv] = Geo.centroid(r);
        ctx.fillStyle = ["lane", "lane_new", "car_park"].includes(f.kind) ? "#f2f2ee" : "#161b22";
        const txt = f.kind === "lane" || f.kind === "lane_new" ? f.label.split(" ")[0] : f.label;
        const cx = f.kind === "lane" || f.kind === "lane_new" ? X(cu) + 9 * s : X(cu);
        if (f.kind === "lane" || f.kind === "lane_new" || ctx.measureText(txt).width < 14 * s) ctx.fillText(txt, cx, Y(cv));
      }
      ctx.textAlign = "left";
    }
    // coaches
    for (const c of this.coaches || []) {
      const p = this.placements && this.placements.get(c.idx);
      if (!p) continue;
      ctx.save();
      ctx.translate(X(p.x), Y(p.y)); ctx.rotate(-p.heading);
      const lw = p.length * s, ww = p.width * s;
      ctx.fillStyle = Ramps.css(Ramps.soc(c.soc));
      ctx.strokeStyle = p.kind === "charging" ? "#4cc9d6" : "#000000aa";
      ctx.lineWidth = p.kind === "charging" ? 3 : 1;
      ctx.beginPath(); ctx.roundRect(-lw / 2, -ww / 2, lw, ww, Math.min(4, ww / 3)); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#00000066"; ctx.fillRect(lw / 2 - 1.2 * s, -ww / 2 + 1, 0.9 * s, ww - 2);   // windscreen
      ctx.restore();
      if (s > 3) {
        ctx.fillStyle = "#000"; ctx.font = `600 ${Math.min(13, Math.max(9, 1.4 * s))}px "IBM Plex Mono", monospace`;
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(String(c.idx), X(p.x), Y(p.y)); ctx.textAlign = "left";
      }
    }
    // scale bar
    const m = [5, 10, 20, 50].find((v) => v * s > 60) || 50;
    ctx.fillStyle = SW.token("ink"); ctx.fillRect(16, h - 22, m * s, 3);
    ctx.font = '11px "IBM Plex Mono", monospace'; ctx.textBaseline = "alphabetic"; ctx.fillText(`${m} m`, 16, h - 30);
  }
}

/* ------------------------------------------------------------------------------------------------ 3D view */
class Scene3DView {
  // z0, z1 (m) and colour of the flat features, as in scripts/12_blender_design.py
  static SLAB = { yard: [0, 0.04, "#b4b2ab"], tree_bank: [0, 0.15, "#8fbf6f"], road_ext: [0, 0.03, "#55575b"],
    landscape: [0.04, 0.12, "#8fbf6f"], island: [0.04, 0.2, "#7fae63"], lane: [0.04, 0.055, "#3e4145"], lane_new: [0.04, 0.055, "#3e4145"],
    car_park: [0.04, 0.06, "#55575b"], footway: [0.04, 0.16, "#d9d2c3"], gate: [0, 0.05, "#55575b"] };

  constructor(canvas, host) {
    this.canvas = canvas; this.host = host;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.shadowMap.enabled = true;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(35, 1, 0.5, 3000);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.maxPolarAngle = Math.PI * 0.48;
    this.scene.add(new THREE.HemisphereLight(0xdfe9f5, 0x4a5a3a, 1.5));
    const sun = new THREE.DirectionalLight(0xffffff, 2.2);
    sun.position.set(-70, 130, 60); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    Object.assign(sun.shadow.camera, { left: -110, right: 110, top: 110, bottom: -110, far: 400 });
    this.scene.add(sun);
    this.group = new THREE.Group(); this.scene.add(this.group);
    this.coachGroup = new THREE.Group(); this.scene.add(this.coachGroup);
    this.coachMeshes = [];
    this.reels = [];
    this.layout = null;
    this.visible = false;
    this.setTheme();
    canvas.addEventListener("dblclick", () => this.resetCamera());
    new ResizeObserver(() => this.resize()).observe(host);
    this.renderer.setAnimationLoop(() => this.frame());
  }

  setTheme() { this.scene.background = new THREE.Color(0x9fbad6); }
  resize() {
    const w = this.host.clientWidth || 1, h = this.host.clientHeight || 1;
    this.renderer.setSize(w, h, false); this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
  }
  get centre() { const [x0, y0, x1, y1] = this.layout.bounds; return [(x0 + x1) / 2, (y0 + y1) / 2]; }
  xz(u, v) { const [cu, cv] = this.centre; return [u - cu, -(v - cv)]; }
  resetCamera() {
    // like design_aerial.png: from the south-west, above the railway
    this.camera.position.set(-70, 95, 120);
    this.controls.target.set(0, 0, 0); this.controls.update();
  }

  slab(ring, z0, z1, color) {
    const [cu, cv] = this.centre, shape = new THREE.Shape(ring.map(([u, v]) => new THREE.Vector2(u - cu, v - cv)));
    const geo = new THREE.ExtrudeGeometry(shape, { depth: Math.max(z1 - z0, 0.01), bevelEnabled: false });
    geo.rotateX(-Math.PI / 2);
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.9 }));
    m.position.y = z0; m.receiveShadow = true; m.castShadow = z1 - z0 > 0.5;
    this.group.add(m);
    return m;
  }
  wall(coords, z0, height, thick, color) {
    const mat = new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: 0.5, metalness: 0.4 });
    for (let i = 1; i < coords.length; i++) {
      const [x0, z0p] = this.xz(...coords[i - 1]), [x1, z1p] = this.xz(...coords[i]), L = Math.hypot(x1 - x0, z1p - z0p);
      if (L < 0.05) continue;
      const m = new THREE.Mesh(new THREE.BoxGeometry(L, height, thick), mat);
      m.position.set((x0 + x1) / 2, z0 + height / 2, (z0p + z1p) / 2);
      m.rotation.y = -Math.atan2(z1p - z0p, x1 - x0);
      m.castShadow = true;
      this.group.add(m);
    }
  }

  setLayout(layout, keepCamera = false) {
    const first = !this.layout || this.layout.name !== layout.name;
    this.layout = layout;
    this.group.clear(); this.reels = [];
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 300), new THREE.MeshStandardMaterial({ color: 0x7d8c62, roughness: 1 }));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -0.05; ground.receiveShadow = true; this.group.add(ground);
    // railway along the south boundary (as in the Blender scene)
    this.slab([[-80, -30], [230, -14], [230, -6], [-80, -22]], -0.05, 0.1, "#7a6a5a");
    for (const f of layout.features) {
      const k = f.kind, sl = Scene3DView.SLAB[k];
      if (sl) for (const r of Geo.rings(f.geom)) this.slab(r, sl[0], sl[1], sl[2]);
      if (k === "lane" || k === "lane_new") for (const r of Geo.rings(f.geom)) this.wall(r, 0.055, 0.02, 0.12, k === "lane" ? "#f2f2ee" : "#f2c200");
      if (k === "building") for (const r of Geo.rings(f.geom)) { this.slab(r, 0.04, 2.9, "#e8e8e4"); this.slab(r, 2.45, 2.65, "#0f6e6e"); }
      if (k === "grid") for (const r of Geo.rings(f.geom)) this.slab(r, 0.04, 2.5, /substation|switch/i.test(f.label) ? "#6f7f6a" : "#f2c200");
      if (k === "wash") {
        for (const r of Geo.rings(f.geom)) {
          if (/gantry/i.test(f.label)) { this.slab(r, 0.04, 0.08, "#9bd0ee"); this.slab(r, 5.0, 5.3, "#9bd0ee"); }
          else this.slab(r, 0.04, 5.0, "#9aa0a6");
        }
      }
      if (k === "charger") for (const r of Geo.rings(f.geom)) {
        const m = this.slab(r, 0.04, 5.8, "#9aa0a6");
        const [cu, cv] = Geo.centroid(r);
        m.material.emissive = new THREE.Color(0x4cc9d6); m.material.emissiveIntensity = 0;
        this.reels.push({ m, u: cu, v: cv });
      }
      if (k === "cable" && /gantry/i.test(f.label)) this.wall(f.geom.coordinates, 5.6, 0.5, 0.5, "#f2c200");
      if (k === "fence") for (const ln of Geo.lines(f.geom)) this.wall(ln, 0, 2.4, 0.08, "#6d7a72");
      if (k === "kerb") for (const ln of Geo.lines(f.geom)) this.wall(ln, 0, 1.1, 0.06, "#6d7a72");
      if (k === "car_bay") {
        const r = Geo.rings(f.geom)[0], [cu, cv] = Geo.centroid(r), [x, z] = this.xz(cu, cv);
        if ((Math.round(cu * 7 + cv * 3) % 3) !== 0) {
          const car = new THREE.Mesh(new THREE.BoxGeometry(1.75, 0.85, 4.2), new THREE.MeshStandardMaterial({ color: (Math.round(cu) % 2) ? 0xd0d4d8 : 0x2a3a5a, metalness: 0.5, roughness: 0.3 }));
          const e = [r[1][0] - r[0][0], r[1][1] - r[0][1]], e2 = [r[2][0] - r[1][0], r[2][1] - r[1][1]];
          const long = Math.hypot(...e) > Math.hypot(...e2) ? e : e2;
          car.rotation.y = Math.atan2(long[1], long[0]) + Math.PI / 2;
          car.position.set(x, 0.62, z); car.castShadow = true; this.group.add(car);
        }
      }
      if (k === "tree_bank") {
        const tm = new THREE.MeshStandardMaterial({ color: 0x3c6b2f, roughness: 0.9 }), trunk = new THREE.MeshStandardMaterial({ color: 0x5a4030 });
        for (const r of Geo.rings(f.geom)) {
          for (let i = 0; i < r.length; i += 3) {
            const h = 5 + ((i * 37) % 40) / 10, [x, z] = this.xz(r[i][0], r[i][1]);
            const t = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, h * 0.5, 8), trunk); t.position.set(x, h * 0.25, z); this.group.add(t);
            const c = new THREE.Mesh(new THREE.IcosahedronGeometry(h * 0.35, 1), tm); c.position.set(x, h * 0.65, z); c.castShadow = true; this.group.add(c);
          }
        }
      }
    }
    if (first || !keepCamera) this.resetCamera();
  }

  coachMesh(L, W) {
    const g = new THREE.Group(), box = (l, h, w, y, color, opts = {}) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(l, h, w), new THREE.MeshStandardMaterial({ color, roughness: 0.4, ...opts }));
      m.position.y = y; m.castShadow = true; g.add(m); return m;
    };
    const body = box(L, 3.35, W, 0.35 + 3.35 / 2, 0x0f6e6e, { metalness: 0.2 });
    box(L - 2.0, 1.3, W + 0.04, 2.25, 0x1b2630, { metalness: 0.6, roughness: 0.1 });
    const roof = box(6.0, 0.3, W - 0.8, 3.85, 0xe8e8e4);
    const band = box(L + 0.02, 0.3, W + 0.05, 1.1, 0x3fb8a0);
    g.userData = { body, roof, band };
    return g;
  }

  setState(coaches, placements) {
    if (!this.layout || !this.layout.slots) return;
    const s0 = this.layout.slots[0];
    while (this.coachMeshes.length < coaches.length) { const m = this.coachMesh(s0.length, s0.width); this.coachMeshes.push(m); this.coachGroup.add(m); }
    coaches.forEach((c, k) => {
      const m = this.coachMeshes[k], p = placements.get(c.idx);
      m.visible = !!p;
      if (!p) return;
      const [x, z] = this.xz(p.x, p.y);
      m.position.set(x, 0, z); m.rotation.y = p.heading;
      const col = new THREE.Color(Ramps.css(Ramps.soc(c.soc)));
      m.userData.band.material.color = col;
      m.userData.roof.material.color = col;
      m.userData.body.material.color = new THREE.Color(p.kind === "charging" ? 0x3fb8a0 : 0x0f6e6e);   // Blender: coach_c / coach
    });
    // light the cable reel next to every charging coach
    const lit = new Set();
    for (const c of coaches) {
      const p = placements.get(c.idx);
      if (!p || p.kind !== "charging") continue;
      let best = null, bd = 1e9;
      for (const r of this.reels) { const d = Math.abs(r.v - p.y) + 0.1 * Math.abs(r.u - p.x); if (d < bd) { bd = d; best = r; } }
      if (best) lit.add(best);
    }
    for (const r of this.reels) r.m.material.emissiveIntensity = lit.has(r) ? 1.2 : 0;
  }

  frame() {
    if (!this.visible) return;
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}

/* ------------------------------------------------------------------------------------------------ application */
class WorkbenchPage {
  constructor() {
    this.root = $("#wb");
    this.api = new Api();
    this.run = null;
    this.frame = 0;
    this.playing = false;
    this.speed = 60;            // simulated minutes per second
    this.view = "map";
    this.parts = {};
    this.params = {};
    this.base = {};
    this.text = {};
    this.sites = [];
    this.catalogue = [];
    this.routeGeom = null;
    this.baseRouteGeom = null;
    this.timer = null;
    this.seq = 0;
    this.picking = false;
  }

  q(sel) { return $(`[data-sw="${sel}"]`, this.root); }

  async start() {
    this.initTheme();
    if (window.EMBER_STATIC) {       // static build: the Python model runs in the browser (backend.js)
      const { LocalBackend } = await import("./backend.js");
      this.api = new LocalBackend();
      this.status("running", "Loading");
      await this.api.init((msg) => this.banner(msg));
      this.banner("");
      $("#save-run").hidden = true;
    }
    const [schema, gis] = await Promise.all([this.api.schema(), this.api.gis()]);
    this.schema = schema; this.gis = gis;
    $("#project-name").textContent = schema.project;
    for (const p of schema.params) { this.params[p.key] = p.value; this.base[p.key] = p.value; }
    this.text = { ...schema.text };
    this.baseText = { ...schema.text };
    this.catalogue = schema.sites.map((s) => ({ ...s }));
    this.qgisPlots = schema.screened || [];
    this.sites = schema.sites.map((s) => ({ ...s }));
    this.baseRouteGeom = gis.route ? gis.route.geometry : null;
    this.routeGeom = this.baseRouteGeom;
    this.buildInputs();
    this.layout();
    this.bindButtons();
    this.mapView = new MapView($("#map"), this);
    this.mapView.setSubstations(gis.substations);
    this.plan = new PlanView($("#plan"), this.q("viewport"));
    this.three = new Scene3DView($("#three"), this.q("viewport"));
    SW.onThemeChange(() => { this.three.setTheme(); this.plan.draw(); this.redrawMap(); });
    this.updateRouteInputs();
    this.redrawRoute(true);
    this.fillSiteSelect();
    await this.evaluate();
    this.mapView.fitRoute(this.origin(), this.dest(), this.currentSite());
  }

  initTheme() {
    document.documentElement.dataset.theme = "light";
    try { localStorage.setItem("sw-theme", "light"); } catch (e) { /* storage blocked */ }
  }

  layout() {
    const main = $(".sw-main", this.root), side = this.q("side"), left = this.q("left"), bottom = $(".sw-bottom", this.root);
    this.leftSplitter(this.q("split-l"), left, () => main.clientWidth * 0.4);
    SW.splitter(this.q("split-x"), { root: this.root, prop: "--wb-side", axis: "x", pane: side, min: 260, max: () => main.clientWidth * 0.45, storageKey: "eb:side" });
    SW.splitter(this.q("split-y"), { root: this.root, prop: "--wb-bottom", axis: "y", pane: bottom, min: 120, max: () => this.root.clientHeight - 48 - 220 - 8, storageKey: "eb:bottom" });
    const addBtn = this.q("add-plot");
    addBtn.addEventListener("click", () => this.parts.plots && this.parts.plots.add());
    SW.tabs(this.q("metric-tabs"), { storageKey: "eb:tab", onChange: (id, b) => { addBtn.hidden = b.getAttribute("data-tab") !== "plots"; } });
  }

  /** Splitter for a pane on the LEFT of its handle (SW.splitter assumes the pane is right of / below the handle). */
  leftSplitter(handle, pane, max) {
    const set = (px) => {
      px = Math.round(Math.max(240, Math.min(max(), px)));
      this.root.style.setProperty("--wb-left", px + "px");
      try { localStorage.setItem("eb:left", px); } catch (e) { /* storage blocked */ }
    };
    Object.assign(handle, { tabIndex: 0 });
    handle.setAttribute("role", "separator");
    handle.setAttribute("aria-orientation", "vertical");
    try { const s = localStorage.getItem("eb:left"); if (s) set(+s); } catch (e) { /* storage blocked */ }
    handle.addEventListener("pointerdown", (e) => {
      e.preventDefault(); handle.setPointerCapture(e.pointerId); handle.classList.add("is-dragging");
      const x0 = e.clientX, s0 = pane.getBoundingClientRect().width;
      const move = (ev) => set(s0 + ev.clientX - x0);
      const up = () => { handle.classList.remove("is-dragging"); handle.removeEventListener("pointermove", move); handle.removeEventListener("pointerup", up); };
      handle.addEventListener("pointermove", move); handle.addEventListener("pointerup", up);
    });
    handle.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); set(pane.getBoundingClientRect().width + (e.key === "ArrowRight" ? 16 : -16)); }
    });
  }

  /* ---------------------------------------------------------------- inputs */
  static HIDDEN = new Set(["route.origin_lon", "route.origin_lat", "route.dest_lon", "route.dest_lat", "site.lon", "site.lat"]);

  buildInputs() {
    const groups = {};
    for (const p of this.schema.params) (groups[p.group] = groups[p.group] || []).push(p);
    const host = $("#groups");
    for (const [g, ps] of Object.entries(groups)) {
      if (g === "Route" || g === "Site") continue;
      const det = document.createElement("details");
      det.className = "eb-group";
      det.open = g === "Timetable";
      det.innerHTML = `<summary>${esc(g)}<span class="eb-count"></span></summary><div class="eb-fields" data-group="${esc(g)}"></div>`;
      host.appendChild(det);
    }
    this.inputs = {};
    for (const p of this.schema.params) {
      if (WorkbenchPage.HIDDEN.has(p.key)) continue;
      const box = $(`.eb-fields[data-group="${p.group}"]`);
      if (!box) continue;
      const label = document.createElement("label");
      label.htmlFor = "in-" + p.key;
      label.innerHTML = `${esc(p.label)}<small>${esc(p.unit)}</small>`;
      const input = document.createElement("input");
      Object.assign(input, { className: "sw-input", type: "number", id: "in-" + p.key, min: p.min, max: p.max, step: p.step, value: p.value });
      input.title = `${p.label} [${p.unit}], ${p.min} to ${p.max}`;
      input.addEventListener("change", () => this.onInput(p, input));
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.blur(); });
      box.append(label, input);
      this.inputs[p.key] = input;
    }
  }

  onInput(p, input) {
    let v = Number(input.value);
    if (input.value === "" || !isFinite(v)) v = this.params[p.key];
    v = Math.max(p.min, Math.min(p.max, v));
    input.value = v;
    this.params[p.key] = v;
    if (p.key.startsWith("site.")) {   // keep the site list in step so the comparison uses the edited value
      const s = this.currentSite(), field = { "site.deadrun_km": "deadrun_km", "site.deadrun_min": "deadrun_min", "site.area_m2": "area_m2",
        "site.lease_gbp_per_m2_yr": "lease_gbp_per_m2_yr", "site.grid_distance_m": "grid_distance_m", "site.spare_grid_kVA": "spare_grid_kVA" }[p.key];
      if (s && field) { s[field] = v; s.edited = true; }
    }
    this.markChanged();
    this.schedule();
  }

  markChanged() {
    for (const [k, el] of Object.entries(this.inputs)) {
      el.classList.toggle("is-changed", Math.abs(this.params[k] - this.base[k]) > 1e-9 && !k.startsWith("site.") && !k.startsWith("route."));
      el.value = this.params[k];
    }
    document.querySelectorAll("#groups details").forEach((d) => {
      const n = d.querySelectorAll(".sw-input.is-changed").length;
      d.querySelector(".eb-count").textContent = n ? `${n} changed` : "";
    });
    const s = this.currentSite();
    for (const k of ["site.lease_gbp_per_m2_yr", "site.spare_grid_kVA"]) {
      const el = this.inputs[k], f = k.slice(5);
      if (el) el.classList.toggle("is-placeholder", !!(s && s.placeholder && s.placeholder.includes(f) && !s.edited));
    }
  }

  resetInputs() {
    this.params = { ...this.base };
    this.text = { ...this.baseText };
    this.sites = this.catalogue.map((s) => ({ ...s }));
    this.routeGeom = this.baseRouteGeom;
    this.updateRouteInputs();
    this.redrawRoute(true);
    this.fillSiteSelect();
    this.markChanged();
    this.schedule(0);
  }

  schedule(ms = 250) {
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.evaluate(), ms);
  }

  payload() {
    const params = { ...this.params };
    for (const [k, v] of Object.entries(this.text)) params[k] = v;
    const sites = this.sites.map(({ geometry, placeholder, ...s }) => s);
    return { params, sites };
  }

  async evaluate() {
    const my = ++this.seq;
    this.status("running", "Simulating");
    try {
      const { params, sites } = this.payload();
      const run = await this.api.evaluate(params, sites);
      if (my !== this.seq) return;     // a newer request superseded this one
      this.setRun(run);
      this.status(this.playing ? "running" : "paused", this.playing ? "Playing" : "Ready");
    } catch (e) {
      if (my !== this.seq) return;
      this.status("failed", "Failed");
      this.q("status").title = e.message;
      this.banner(e.message, true);
    }
  }

  /* ---------------------------------------------------------------- route */
  origin() { return [this.params["route.origin_lon"], this.params["route.origin_lat"]]; }
  originIsSheet() { return Fmt.km(this.origin(), BRISTOL) < 0.05; }
  dest() { return [this.params["route.dest_lon"], this.params["route.dest_lat"]]; }

  updateRouteInputs() {
    $("#origin-q").value = this.text["route.origin_name"];
    $("#dest-q").value = this.text["route.dest_name"];
  }

  bindSearch(which) {
    const input = $(`#${which}-q`), res = $(`#${which}-res`);
    let t = null, last = "";
    const run = async () => {
      const q = input.value.trim();
      if (q.length < 3 || q === last) return;
      last = q;
      try {
        const hits = await this.api.geocode(q);
        res.innerHTML = hits.length ? "" : '<button type="button" disabled>No match in Great Britain</button>';
        for (const h of hits) {
          const b = document.createElement("button");
          b.type = "button"; b.textContent = h.name;
          b.addEventListener("click", () => { res.classList.remove("is-open"); this.setEndpoint(which, h); });
          res.appendChild(b);
        }
        res.classList.add("is-open");
      } catch (e) { this.note("route-note", "Place search failed: " + e.message, true); }
    };
    input.addEventListener("input", () => { clearTimeout(t); t = setTimeout(run, 700); });
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") { clearTimeout(t); last = ""; run(); } if (e.key === "Escape") res.classList.remove("is-open"); });
    input.addEventListener("focus", () => input.select());
    document.addEventListener("click", (e) => { if (!res.contains(e.target) && e.target !== input) res.classList.remove("is-open"); });
  }

  async setEndpoint(which, place) {
    const oldOrigin = this.origin();
    const short = place.name.split(",").slice(0, 3).join(",");
    this.params[`route.${which}_lon`] = place.lon;
    this.params[`route.${which}_lat`] = place.lat;
    this.text[`route.${which === "origin" ? "origin" : "dest"}_name`] = short;
    this.updateRouteInputs();
    this.note("route-note", "Routingâ€¦");
    try {
      const r = await this.api.route(this.origin(), this.dest());
      this.params["route.distance_km"] = r.distance_km;
      this.params["route.drive_time_min"] = r.drive_time_min;
      this.routeGeom = r.geometry;
      this.note("route-note", `OSRM road route: ${Fmt.num(r.distance_km, 1)} km, car ${Fmt.hm(r.car_time_min)} â†’ coach ${Fmt.hm(r.drive_time_min)} (Ã— ${r.coach_factor} calibrated on the sheet's Bristolâ€“Victoria 3:07). Edit the fields to override.`);
    } catch (e) {
      const km = Fmt.km(this.origin(), this.dest()) * 1.25;
      this.params["route.distance_km"] = Math.round(km * 10) / 10;
      this.params["route.drive_time_min"] = Math.round(km / 61.4 * 60);
      this.routeGeom = null;
      this.note("route-note", `Routing service unavailable (${e.message}); distance estimated as 1.25 Ã— straight line at the sheet's average speed. Edit to correct.`, true);
    }
    this.markChanged();
    this.redrawRoute(true);
    if (which === "origin" && Fmt.km(oldOrigin, this.origin()) > 0.1) await this.originMoved();
    this.schedule(0);
  }

  async originMoved() {
    const o = this.origin();
    if (Fmt.km(o, BRISTOL) < 0.05) {       // back at the sheet origin: restore the sheet's dead runs
      for (const s of this.sites) { const c = this.catalogue.find((x) => x.id === s.id); if (c) Object.assign(s, { deadrun_km: c.deadrun_km, deadrun_min: c.deadrun_min }); }
    } else {
      try {
        const res = await this.api.deadruns(o, this.sites.map((s) => ({ id: s.id, lon: s.lon, lat: s.lat })));
        for (const r of res) {
          const s = this.sites.find((x) => x.id === r.id);
          if (s && r.deadrun_km != null) Object.assign(s, { deadrun_km: r.deadrun_km, deadrun_min: r.deadrun_min });
        }
      } catch (e) { this.banner("Dead runs not updated (routing service unavailable): " + e.message, true); }
    }
    const near = this.sites.filter((s) => s.deadrun_km <= 15);
    if (!near.length) {
      this.banner("No candidate hub within 15 km of the new origin, screening OSM plots near itâ€¦");
      await this.screen();
    }
    this.applySite(this.currentSite() && this.currentSite().deadrun_km <= 15 ? this.currentSite().id : this.bestSiteId());
  }

  redrawRoute(fit) {
    this.mapView && this.mapView.setRoute(this.routeGeom, this.origin(), this.dest(), [this.text["route.origin_name"], this.text["route.dest_name"]]);
    if (fit && this.mapView) this.mapView.fitRoute(this.origin(), this.dest(), this.currentSite());
  }

  /* ---------------------------------------------------------------- sites */
  currentSite() { return this.sites.find((s) => s.id === this.text["site.id"]); }
  siteResult(id) { return this.run && this.run.sites.find((r) => r.site_id === id); }
  bestSiteId() {
    const near = this.sites.filter((s) => s.deadrun_km <= 15).sort((a, b) => a.deadrun_km - b.deadrun_km);
    return (near[0] || this.sites[0]).id;
  }

  fillSiteSelect() {
    const sel = $("#site-select");
    sel.innerHTML = "";
    const groups = { listed: "Listed sites", screened: "Screened OSM plots", custom: "Custom" };
    for (const [kind, label] of Object.entries(groups)) {
      const list = this.sites.filter((s) => (s.kind || "listed") === kind);
      if (!list.length) continue;
      const og = document.createElement("optgroup"); og.label = label;
      for (const s of list) { const o = document.createElement("option"); o.value = s.id; o.textContent = s.name; og.appendChild(o); }
      sel.appendChild(og);
    }
    sel.value = this.text["site.id"];
    this.renderSiteMeta();
  }

  applySite(id) {
    const s = this.sites.find((x) => x.id === id);
    if (!s) return;
    this.text["site.id"] = s.id;
    this.text["site.name"] = s.name;
    Object.assign(this.params, { "site.lon": s.lon, "site.lat": s.lat, "site.deadrun_km": s.deadrun_km, "site.deadrun_min": s.deadrun_min,
      "site.area_m2": s.area_m2, "site.lease_gbp_per_m2_yr": s.lease_gbp_per_m2_yr, "site.grid_distance_m": s.grid_distance_m,
      "site.spare_grid_kVA": s.spare_grid_kVA });
    this.fillSiteSelect();
    this.markChanged();
  }

  selectSite(id) {
    this.applySite(id);
    this.schedule(0);
    if (this.view === "map") this.mapView.fitSite(this.currentSite());
  }

  renderSiteMeta() {
    const s = this.currentSite(), el = $("#site-meta");
    if (!s) { el.textContent = ""; return; }
    const tags = [s.kind === "listed" ? "Listed" : s.kind === "custom" ? "Custom" : `Screened Â· score ${Fmt.num(s.score)}`];
    if (s.landuse) tags.push(s.landuse);
    el.innerHTML = `<b>${esc(s.name)}</b><br>${tags.map((t) => `<span class="eb-tag">${esc(t)}</span>`).join("")}${s.status ? esc(s.status) : ""}`
      + (s.url ? ` Â· <a href="${esc(s.url)}" target="_blank" rel="noopener">listing</a>` : "")
      + (s.primary_sub ? `<br>Nearest 33 kV primary: ${esc(s.primary_sub)}` : "")
      + (s.placeholder && !s.edited ? `<br><span class="sw-muted">Dashed fields are placeholders (no agent's figures yet).</span>` : "");
  }

  async screen() {
    const btn = $("#screen-btn");
    btn.disabled = true;
    if (this.originIsSheet()) {     // the Bristol screening already exists: the QGIS candidate_plots layer
      const have = new Set(this.sites.map((s) => s.id));
      this.sites = this.sites.concat(this.qgisPlots.filter((s) => !have.has(s.id)).map((s) => ({ ...s })));
      this.note("screen-note", `Added the top ${this.qgisPlots.length} plots of the QGIS screening (candidate_plots: area, shape, dead run, 33 kV distance, land use). Lease and spare grid capacity are placeholders, so their costs are indicative only.`);
      this.fillSiteSelect();
      btn.disabled = false;
      return;
    }
    this.note("screen-note", "Screening OSM plots (Overpass + OSRM), up to a minuteâ€¦");
    try {
      const res = await this.api.screen(this.origin(), this.routeGeom);
      this.sites = this.sites.filter((s) => s.kind !== "screened" || !s.id.startsWith("Q")).concat(res.sites);
      if (Fmt.km(this.origin(), BRISTOL) > 15) this.sites = this.sites.filter((s) => s.kind === "custom" || s.id.startsWith("Q"));
      this.note("screen-note", `${res.screened} OSM polygons screened, ${res.passed} pass the area / shape / 15 km dead-run filters; the best ${res.sites.length} (road dead-runs from OSRM) are in the site list. Lease and spare grid capacity are placeholders.`);
      this.mapView.setSubstations(res.substations);
      this.fillSiteSelect();
      this.banner("");
    } catch (e) {
      this.note("screen-note", "Screening failed: " + e.message, true);
    } finally {
      btn.disabled = false;
    }
  }

  async onMapClick(lonlat) {
    if (!this.picking) return;
    this.picking = false;
    this.root.classList.remove("eb-picking");
    $("#pick-btn").textContent = "Pick on map";
    const n = this.sites.filter((s) => s.kind === "custom").length + 1;
    const subs = (this.gis.substations || []);
    const near = subs.reduce((m, s) => Math.min(m, Fmt.km(lonlat, s.coordinates) * 1000), 5000);
    const site = { id: `C${n}`, name: `C${n} Custom site`, lon: lonlat[0], lat: lonlat[1], deadrun_km: Fmt.km(lonlat, this.origin()) * 1.4,
      deadrun_min: 0, area_m2: 7000, lease_gbp_per_m2_yr: 20, grid_distance_m: Math.round(near), spare_grid_kVA: 1000, kind: "custom",
      placeholder: ["lease_gbp_per_m2_yr", "spare_grid_kVA"] };
    site.deadrun_min = Math.round(site.deadrun_km / 35 * 60 + 3);
    try {
      const [r] = await this.api.deadruns(this.origin(), [{ id: site.id, lon: site.lon, lat: site.lat }]);
      if (r && r.deadrun_km != null) Object.assign(site, { deadrun_km: r.deadrun_km, deadrun_min: r.deadrun_min });
    } catch (e) { this.banner("Dead run estimated as 1.4 Ã— straight line (routing unavailable)", true); }
    this.sites.push(site);
    this.selectSite(site.id);
  }

  /* ---------------------------------------------------------------- buttons */
  bindButtons() {
    this.q("play").addEventListener("click", () => (this.playing ? this.pause() : this.play()));
    this.q("reset").addEventListener("click", () => { this.pause(); this.go(0); });
    this.q("speed").addEventListener("change", (e) => { this.speed = Number(e.target.value) || 60; });
    $("#site-select").addEventListener("change", (e) => this.selectSite(e.target.value));
    $("#reset-inputs").addEventListener("click", () => this.resetInputs());
    $("#screen-btn").addEventListener("click", async () => { await this.screen(); this.schedule(0); });
    $("#pick-btn").addEventListener("click", () => {
      this.picking = !this.picking;
      this.root.classList.toggle("eb-picking", this.picking);
      $("#pick-btn").textContent = this.picking ? "Click the mapâ€¦" : "Pick on map";
      if (this.picking) this.setView("map");
    });
    $("#save-run").addEventListener("click", async () => {
      try {
        const { params, sites } = this.payload();
        const r = await this.api.save(params, sites, (this.text["site.id"] || "case").toLowerCase());
        this.banner(`Saved run folder results/${r.run_dir}`);
        setTimeout(() => this.banner(""), 4000);
      } catch (e) { this.banner("Save failed: " + e.message, true); }
    });
    $("#swept-btn").addEventListener("click", () => this.sweptChecks());
    for (const b of document.querySelectorAll("#view-seg button")) b.addEventListener("click", () => this.setView(b.dataset.view));
    this.bindSearch("origin");
    this.bindSearch("dest");
    document.addEventListener("keydown", (e) => {
      if (e.target.closest("input, select, textarea")) return;
      if (e.key === " ") { e.preventDefault(); this.playing ? this.pause() : this.play(); }
      if (e.key === "ArrowRight") this.go(this.frame + (e.shiftKey ? 60 : 5));
      if (e.key === "ArrowLeft") this.go(this.frame - (e.shiftKey ? 60 : 5));
    });
  }

  setView(v) {
    this.view = v;
    for (const b of document.querySelectorAll("#view-seg button")) b.setAttribute("aria-pressed", String(b.dataset.view === v));
    $("#map").hidden = v !== "map";
    $("#plan").hidden = v !== "plan";
    $("#three").hidden = v !== "3d";
    this.three.visible = v === "3d";
    $("#swept-btn").hidden = v === "map";
    $("#view-hint").textContent = v === "map" ? "drag to pan Â· scroll to zoom Â· click a site" : v === "plan" ? "drag to pan Â· scroll to zoom Â· double-click to fit" : "drag to orbit Â· scroll to zoom Â· double-click to reset";
    if (v === "map") this.mapView.invalidate();
    if (v === "plan") this.plan.draw();
    if (v === "3d") this.three.resize();
    this.go(this.frame);
  }

  async sweptChecks() {
    const btn = $("#swept-btn");
    if (this.plan.swept) { this.plan.setSwept(null); btn.textContent = "Swept paths"; this.banner(""); return; }
    btn.disabled = true;
    try {
      const { params } = this.payload();
      const r = await this.api.swept(params);
      this.plan.setSwept(r.envelopes);
      btn.textContent = "Hide swept paths";
      this.banner(`${r.drawing}: ${r.movements} coach movements, all forward-only, minimum clearance ${Fmt.num(r.min_clearance_m, 2)} m (swept-path model of the design${r.site_specific ? "" : "; this design is for S1 Temple Works"}).`);
      if (this.view === "map") this.setView("plan");
    } catch (e) { this.banner("Swept paths unavailable: " + e.message, true); }
    finally { btn.disabled = false; }
  }

  /* ---------------------------------------------------------------- run */
  setRun(payload) {
    const data = {};
    for (const k of Object.keys(payload.data)) data[k] = Float64Array.from(payload.data[k]);
    const keepFrame = this.run ? this.frame : 0;
    this.run = { ...payload, data };
    // design-system components get the aggregate variables only (not the four per coach)
    this.viewRun = { ...this.run, vars: this.run.vars.filter((v) => !/^c\d+_/.test(v.key)) };
    this.plotRun = { ...this.run, vars: this.run.vars.filter((v) => !/^c\d+_(mode|chg|prog)$/.test(v.key)) };
    this.fleet = new Fleet(this.run);
    this.plan.setLayout(this.run.layout);
    this.three.setLayout(this.run.layout, true);
    this.redrawMap();
    this.build();
    this.go(Math.min(keepFrame, this.run.n - 1));
    const sel = this.run.selected;
    const issues = [];
    if (!sel.battery_ok) issues.push("battery too small for the rotation");
    if (!sel.eu_ok) issues.push("EU driving hours breached");
    if (!sel.area_ok) issues.push("site smaller than the hub area required");
    if (this.run.layout.site_specific && !this.run.kpis.layout_fits) issues.push(`${sel.fleet_total} coaches but the Temple Works design holds ${this.run.layout.capacity}`);
    if (!sel.substation_kVA) issues.push("load above the largest standard substation");
    if (this.run.kpis.sim_on_time_pct < 99.5) issues.push(`only ${Fmt.num(this.run.kpis.sim_on_time_pct, 1)} % of simulated departures on time`);
    this.banner(issues.length ? "Check: " + issues.join(" Â· ") : "", issues.length > 0);
  }

  redrawMap() {
    if (!this.mapView) return;
    const lay = this.run ? this.run.layout : null;
    this.mapView.setSites(this.sites, this.text["site.id"], this.origin(), lay && lay.site_specific && this.originIsSheet() ? lay.deadrun_route : null);
    if (lay) this.mapView.setLayout(lay);
  }

  build() {
    const run = this.viewRun;
    for (const k of ["kpis", "plots", "ts-body", "ts-chips"]) this.q(k).innerHTML = "";
    this.annual();
    this.sitesTable();
    this.costs();
    this.parts.kpi = SW.kpis(this.q("kpis"), run, ["grid_kVA", "charging", "queued", "on_road", "soc_min", "drivers"]);
    this.parts.plots = SW.plotBuilder(this.q("plots"), this.plotRun, {
      fill: true, tile: false,
      plots: [{ x: "t", y: "grid_kVA", mode: "line" }, { x: "t", y: "soc_mean", mode: "line" }],
    });
    this.parts.ts = SW.timeSeries(this.q("ts-chips"), this.q("ts-body"), run, {
      keys: ["grid_kVA", "charging", "on_road", "soc_min"], onScrub: (i) => { this.pause(); this.go(i); },
    });
  }

  annual() {
    const k = this.run.kpis, s = this.run.selected, info = Object.fromEntries(this.schema.kpis.map((x) => [x.key, x]));
    const checks = [
      ["Battery", s.battery_ok, `SOC at plug-in ${Fmt.num(s.soc_plug_in * 100, 1)} %`],
      ["EU driving hours", s.eu_ok, `driving ${Fmt.hm(s.driving_min)} per shift`],
      ["Hub area (sheet)", s.area_ok, `${Fmt.num(s.area_req_m2)} of ${Fmt.num(k.site_area_m2)} mÂ²`],
      ["Hub design", k.layout_fits > 0, this.run.layout.site_specific ? `${Fmt.num(k.fleet_total)} coaches in ${this.run.layout.lanes} lanes (${this.run.layout.drawing})` : "no detailed design: sheet area check"],
      ["Substation", !!s.substation_kVA, s.substation_kVA ? `${Fmt.num(s.substation_kVA)} kVA` : "> 4,000 kVA"],
      ["Timetable (sim)", k.sim_on_time_pct >= 99.5, `${Fmt.num(k.sim_on_time_pct, 1)} % on time`],
    ];
    $("#checks").innerHTML = `<div class="eb-checks">${checks.map(([n, ok, t]) => `<span class="eb-check ${ok ? "ok" : "bad"}" title="${esc(t)}">${ok ? "âœ“" : "âœ—"} ${esc(n)}</span>`).join("")}</div>`;
    const tile = (key, val, sub, bad) => {
      const i = info[key] || { label: key, unit: "" };
      return `<div class="sw-kpi${bad ? " is-bad" : ""}"><div class="k-name" title="${esc(i.label)}">${esc(i.label)}</div><div class="k-val">${val}</div><div class="k-unit">${esc(i.unit === "min" ? "h:mm" : i.unit)}</div>${sub ? `<div class="k-delta" title="${esc(sub)}">${esc(sub)}</div>` : ""}</div>`;
    };
    const sections = [
      ["Fleet and drivers", [
        tile("fleet_total", Fmt.num(k.fleet_total), `${Fmt.num(k.fleet)} in service + ${Fmt.num(k.fleet_total - k.fleet)} spare`),
        tile("drivers", Fmt.num(k.drivers), `${Fmt.num(s.shifts_per_driver_week)} shifts/driver/week`),
        tile("peak_drivers", Fmt.num(k.peak_drivers), `sim peak on duty ${Fmt.num(k.sim_peak_drivers)}`),
        tile("shift_min", Fmt.hm(k.shift_min), `driving ${Fmt.hm(s.driving_min)}`),
        tile("cycle_min", Fmt.hm(k.cycle_min), `${Fmt.num(k.trips_per_day, 0)} return trips/day`),
        tile("slack_min", Fmt.hm(k.slack_min), "fleet Ã— headway âˆ’ cycle", k.slack_min < 0),
      ]],
      ["Charging and grid", [
        tile("total_chargers", Fmt.num(k.total_chargers), `${Fmt.num(k.active_chargers)} active + ${Fmt.num(k.total_chargers - k.active_chargers)} backup`),
        tile("charge_min", Fmt.hm(k.charge_min), `${Fmt.num(k.energy_rotation_kWh, 0)} kWh per rotation`),
        tile("soc_plug_in_pct", Fmt.num(k.soc_plug_in_pct, 1), `sim lowest ${Fmt.num(k.sim_min_soc_plug_in_pct, 1)} %`, !s.battery_ok),
        tile("peak_kVA", Fmt.num(k.peak_kVA), `sim peak ${Fmt.num(k.sim_peak_kVA)} kVA`),
        tile("substation_kVA", s.substation_kVA ? Fmt.num(k.substation_kVA) : "> 4,000", "peak Ã· utilisation â†’ BS EN 60076 size", !s.substation_kVA),
        tile("sim_grid_kWh_per_day", Fmt.num(k.sim_grid_kWh_per_day), `charger use ${Fmt.num(k.sim_charger_util_pct, 0)} %`),
      ]],
      ["Hub and site", [
        tile("area_req_m2", Fmt.num(k.area_req_m2), `site ${Fmt.num(k.site_area_m2)} mÂ²`, !s.area_ok),
        tile("design_lanes", Fmt.num(k.design_lanes), this.run.layout.site_specific ? `${this.run.layout.drawing} (${this.run.layout.name}), ${this.run.layout.capacity} max on site` : "S1 design shown for reference", !(k.layout_fits > 0)),
      ]],
      ["Cost", [
        tile("total_gbp_yr", Fmt.gbp(k.total_gbp_yr), s.rank ? `rank ${s.rank} of ${this.run.sites.filter((r) => r.feasible).length} feasible` : "not feasible: excluded"),
        tile("gbp_per_trip", Fmt.gbp(k.gbp_per_trip), `${Fmt.num(k.trips_per_day * 365 * this.params["timetable.days_per_week"] / 7, 0)} trips/yr`),
      ]],
      ["Simulated operation", [
        tile("sim_on_time_pct", Fmt.num(k.sim_on_time_pct, 1), `${Fmt.num(k.sim_departures)} departures, worst delay ${Fmt.num(k.sim_max_delay_min)} min`, k.sim_on_time_pct < 99.5),
        tile("sim_max_queue_min", Fmt.num(k.sim_max_queue_min), `mean ${Fmt.num(k.sim_mean_queue_min, 1)} min`),
      ]],
    ];
    $("#annual").innerHTML = sections.map(([t, tiles]) => `<div class="sw-section">${esc(t)}</div><div class="sw-kpis eb-annual">${tiles.join("")}</div>`).join("");
    const f = (v, n) => Fmt.num(v, n);
    this.q("ov-tr").innerHTML = `<b>${esc(this.text["site.name"])}</b><br>${f(k.fleet_total)} coaches Â· ${f(k.total_chargers)} Ã— ${f(this.params["hub.charge_power_kW"])} kW Â· ${f(k.drivers)} drivers<br>${Fmt.gbp(k.total_gbp_yr)}/yr Â· <b>${Fmt.gbp(k.gbp_per_trip)}</b>/trip`;
  }

  sitesTable() {
    const rows = [...this.run.sites].sort((a, b) => (a.rank || 1e9) - (b.rank || 1e9) || a.total_gbp_yr - b.total_gbp_yr);
    const sel = this.text["site.id"];
    const h = `<table class="eb-table"><thead><tr><th>#</th><th>Site</th><th class="num">Dead run</th><th class="num">Fleet</th><th class="num">Drivers</th><th class="num">Area</th><th class="num">Â£/trip</th></tr></thead><tbody>` +
      rows.map((r) => {
        const why = [!r.battery_ok && "battery", !r.eu_ok && "EU hours", !r.area_ok && "area", !r.substation_kVA && "grid"].filter(Boolean).join(", ");
        return `<tr data-id="${esc(r.site_id)}" class="${r.site_id === sel ? "is-sel" : ""}" title="${esc(r.site_name)}${why ? " Â· fails: " + why : ""}">
          <td>${r.rank ? r.rank : '<span class="bad">âœ—</span>'}</td><td>${esc(r.site_name.length > 34 ? r.site_name.slice(0, 33) + "â€¦" : r.site_name)}</td>
          <td class="num">${Fmt.num(r.site.deadrun_min)}â€²</td><td class="num">${r.fleet_total}</td><td class="num">${r.drivers}</td>
          <td class="num ${r.area_ok ? "" : "bad"}">${Fmt.num(r.area_req_m2 / 1000, 1)}/${Fmt.num(r.site.area_m2 / 1000, 1)}k</td>
          <td class="num">${Fmt.gbp(r.gbp_per_trip)}</td></tr>`;
      }).join("") + "</tbody></table>" +
      `<p class="eb-note">Ranked by annual cost among feasible sites (sheet rule). Area = required / available, thousand mÂ². Click a row to select the site. Screened and custom sites use placeholder lease (Â£20/mÂ²/yr) and spare grid capacity (1,000 kVA) until edited.</p>`;
    const host = $("#sites-table");
    host.innerHTML = h;
    host.querySelectorAll("tbody tr").forEach((tr) => tr.addEventListener("click", () => this.selectSite(tr.dataset.id)));
  }

  costs() {
    const s = this.run.selected, c = s.costs_gbp_yr, max = Math.max(...Object.values(c), 1);
    const names = { land_lease: "Land lease", site_works: "Site works", chargers: "Chargers", grid_connection: "Grid connection", fleet: "Fleet lease", driver_wages: "Driver wages", electricity: "Electricity" };
    let h = `<div class="sw-section">Annual cost, ${esc(this.text["site.name"])}</div>` + Object.entries(c).map(([k, v]) =>
      `<div class="eb-costrow"><span>${names[k]}</span><div><div class="eb-bar" style="width:${(100 * v / max).toFixed(1)}%"></div></div><span class="num">${Fmt.gbp(v)}</span></div>`).join("")
      + `<div class="eb-costrow"><b>Total</b><span></span><b class="num">${Fmt.gbp(s.total_gbp_yr)}</b></div>`
      + `<div class="eb-costrow"><span>Per return trip</span><span></span><span class="num">${Fmt.gbp(s.gbp_per_trip)}</span></div>`;
    const feas = this.run.sites.filter((r) => r.feasible).sort((a, b) => a.total_gbp_yr - b.total_gbp_yr);
    if (feas.length > 1) {
      h += `<div class="sw-section">Feasible sites</div><table class="eb-table"><thead><tr><th>Site</th>${Object.keys(names).map((k) => `<th class="num">${names[k].split(" ")[0]}</th>`).join("")}<th class="num">Total</th></tr></thead><tbody>` +
        feas.map((r) => `<tr class="${r.site_id === s.site_id ? "is-sel" : ""}"><td>${esc(r.site_id)}</td>${Object.keys(names).map((k) => `<td class="num">${Fmt.num(r.costs_gbp_yr[k] / 1000)}</td>`).join("")}<td class="num">${Fmt.num(r.total_gbp_yr / 1000)}</td></tr>`).join("") +
        `</tbody></table><p class="eb-note">Â£ thousand per year. Capital items annualised at the discount rate over the asset life (sheet PMT).</p>`;
    }
    $("#cost-panel").innerHTML = h;
  }

  /** Move the single playhead: views, indicators, time-series cursor, readouts. */
  go(i) {
    const run = this.run;
    if (!run) return;
    this.frame = Math.max(0, Math.min(run.n - 1, Math.round(i)));
    const f = this.frame, coaches = this.fleet.at(f), place = this.fleet.placements(coaches);
    if (this.view === "map") this.mapView.setCoaches(coaches, place, this.currentSite());
    if (this.view === "plan") this.plan.setState(coaches, place);
    if (this.view === "3d") this.three.setState(coaches, place);
    this.parts.kpi.setFrame(f);
    this.parts.plots.setCursor(f);
    this.parts.ts.setCursor(f);
    const label = Fmt.clock(run.data.t[f]);
    this.q("time").textContent = label;
    const counts = new Array(8).fill(0);
    for (const c of coaches) counts[c.mode]++;
    this.q("ov-tl").innerHTML = `${this.view === "3d" ? "perspective" : this.view} Â· <b>${label}</b>`;
    this.q("ov-bl").innerHTML = MODE_LABEL.map((l, m) => (counts[m] ? `${l} <b>${counts[m]}</b>` : null)).filter(Boolean).join(" Â· ")
      + `<br>Grid <b>${Fmt.num(run.data.grid_kVA[f])}</b> kVA Â· SOC min <b>${Fmt.num(run.data.soc_min[f])}</b> %`;
    if (f === run.n - 1 && this.playing) { this.playing = false; this.status("done", "Done"); }
  }

  status(kind, text) {
    const el = this.q("status");
    el.className = "sw-status is-" + kind;
    el.querySelector("span").textContent = text;
    el.removeAttribute("title");
    this.q("play").textContent = this.playing ? "Pause" : "Play";
  }

  banner(text, err = false) {
    const b = $("#banner");
    b.hidden = !text;
    b.textContent = text;
    b.classList.toggle("is-err", err);
  }

  note(id, text, err = false) {
    const el = $("#" + id);
    el.textContent = text;
    el.classList.toggle("is-err", err);
  }

  play() {
    if (!this.run) return;
    if (this.frame >= this.run.n - 1) this.go(0);
    this.playing = true;
    this.last = performance.now();
    this.carry = 0;
    this.status("running", "Playing");
    requestAnimationFrame((t) => this.tick(t));
  }

  pause() {
    if (!this.playing) return;
    this.playing = false;
    this.status("paused", "Paused");
  }

  tick(ts) {
    if (!this.playing) return;
    const dtSec = (ts - this.last) / 1000;
    this.last = ts;
    this.carry += this.speed * 60 / this.run.dt_s * dtSec;    // frames per second = simulated seconds per second / step
    const whole = Math.floor(this.carry);
    if (whole > 0) { this.carry -= whole; this.go(this.frame + whole); }
    if (this.playing) requestAnimationFrame((t) => this.tick(t));
  }
}

const page = new WorkbenchPage();
window.ember = page;            // handle for debugging and browser QA
page.start().catch((e) => {
  console.error(e);
  const el = document.querySelector('[data-sw="status"]');
  el.className = "sw-status is-failed";
  el.querySelector("span").textContent = "Error: " + e.message;
});
