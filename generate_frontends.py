"""generate_frontends.py
Generates 3D simulation frontends for all 8 portfolio projects + Master Hub.
Architecture:
- Three.js WebGL 3D scene (OrbitControls, materials, lighting, Blender assets, 3D floating sensor tags)
- Top Navigation: Project branding, Scenario selector dropdown, 3D tags toggle, Hub navigation link
- Bottom Interactive Timeline Canvas: Scrubber, Play/Pause, speed selector, multi-variable curves with cursor tracking
- Right Aside: Run time, operational commands, telemetry table (Simulated vs Reference vs Delta), flux/energy ledger, subsystem status
- Embedded scenario data; Three.js loads from a CDN and Blender assets load from the local viewer server.
"""

import json
import math
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def build_common_html(title, subtitle, project_id, scenarios, three_setup_code, update_3d_code, extra_aside=""):
    geometry_source = "Blender model · documented dimensions and estimates" if project_id in {
        "BEng-CEA-Heatpump", "Building-Heatpump-Retrofit", "Heat-Pump-Simulation",
        "Plantpost-Urban-Infrastructure-Modelling", "Whole-Carbon-Lifecycle-Assessment",
        "High-Temp-Waste-Heat-Recovery", "PyPsa-Green-Hydrogen-Microgrid",
        "UniBoat-Powertrain-Cooling"
    } else "schematic geometry"
    for scenario_key, scenario in scenarios.items():
        series = scenario["series"]
        times = series["t"]
        if not times or any(not math.isfinite(t) for t in times) or any(b <= a for a, b in zip(times, times[1:])):
            raise ValueError(f"{project_id}/{scenario_key}: timestamps must be finite and strictly increasing")
        for name, values in series.items():
            if len(values) != len(times) or any(not isinstance(v, (int, float, str)) or (isinstance(v, (int, float)) and not math.isfinite(v)) for v in values):
                raise ValueError(f"{project_id}/{scenario_key}/{name}: expected {len(times)} valid samples")
        for item in scenario.get("chartSeries", []) + scenario.get("sensors", []) + scenario.get("ledger", []):
            if item["key"] not in series:
                raise ValueError(f"{project_id}/{scenario_key}: missing displayed channel {item['key']}")
            if item in scenario.get("chartSeries", []) + scenario.get("ledger", []) and any(not isinstance(v, (int, float)) for v in series[item["key"]]):
                raise ValueError(f"{project_id}/{scenario_key}/{item['key']}: displayed channel must be numeric")
    scenarios_json = json.dumps(scenarios)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} · Digital Twin & Simulation Viewer</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Semi+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root {{
  color-scheme: light;
  --ground: #eef1f4;
  --panel: #f8fafb;
  --line: #d5dce3;
  --ink: #15202b;
  --muted: #5d6b78;
  --faint: #8a97a3;
  --model: #2f5bd3;
  --meas: #15202b;
  --heat: #c2410c;
  --limit: #b91c1c;
  --ok: #15803d;
  --warn: #b45309;
  --scene: #e6ebf0;
  --grid: #c9d2db;
  --prev: #d55e00;
  --sans: "Barlow", "Segoe UI", system-ui, sans-serif;
  --cond: "Barlow Semi Condensed", "Barlow", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --ground: #0f141a; --panel: #161d25; --line: #28323d; --ink: #e4e9ee; --muted: #9aa7b3; --faint: #6c7a87;
    --model: #7c9cff; --meas: #e4e9ee; --heat: #fb923c; --limit: #f87171; --ok: #4ade80; --warn: #fbbf24;
    --scene: #121920; --grid: #2a3540; --prev: #ff8a4c;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --ground: #0f141a; --panel: #161d25; --line: #28323d; --ink: #e4e9ee; --muted: #9aa7b3; --faint: #6c7a87;
  --model: #7c9cff; --meas: #e4e9ee; --heat: #fb923c; --limit: #f87171; --ok: #4ade80; --warn: #fbbf24;
  --scene: #121920; --grid: #2a3540; --prev: #ff8a4c;
}}
* {{ box-sizing: border-box; }}
html, body {{ height: 100%; margin: 0; }}
body {{ background: var(--ground); color: var(--ink); font: 14px/1.4 var(--sans); }}
.app {{ display: grid; grid-template-rows: auto 1fr auto; height: 100vh; padding: 10px 16px; gap: 10px; }}
header {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 16px; }}
.brand {{ display: flex; flex-direction: column; }}
h1 {{ font: 700 18px/1.1 var(--cond); letter-spacing: 0.01em; margin: 0; text-wrap: balance; }}
.sub {{ color: var(--muted); font-size: 12.5px; margin-top: 1px; }}
.runs {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-left: auto; }}
.runs .pick {{ display: grid; gap: 1px; font: 600 10px var(--cond); letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted); }}
.runs .pick select {{ font: 500 13px var(--sans); color: var(--ink); background: var(--panel); border: 1px solid var(--line); border-radius: 4px; padding: 4px 8px; max-width: min(380px, 90vw); }}
.runs .pick select:focus-visible {{ outline: 2px solid var(--model); outline-offset: 2px; }}
.toggle {{ display: flex; align-items: center; gap: 6px; font: 500 13px var(--sans); color: var(--muted); cursor: pointer; user-select: none; }}
.navsep {{ width: 1px; height: 20px; background: var(--line); margin-inline: 4px; }}
.home-btn {{ font: 600 12px var(--cond); text-decoration: none; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); background: var(--panel); border: 1px solid var(--line); border-radius: 4px; padding: 4px 8px; transition: color 0.15s, border-color 0.15s; }}
.home-btn:hover {{ color: var(--model); border-color: var(--model); }}

main {{ display: grid; grid-template-columns: minmax(0, 1fr) 350px; gap: 10px; min-height: 0; }}
.stage {{ position: relative; min-height: 320px; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; background: var(--scene); }}
#three {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
#tags {{ position: absolute; inset: 0; pointer-events: none; overflow: hidden; }}
.tag {{ position: absolute; transform: translate(-50%, -100%); font: 500 11px/1.25 var(--mono); white-space: nowrap; background: color-mix(in srgb, var(--panel) 92%, transparent); border: 1px solid var(--line); border-radius: 3px; padding: 2px 6px; color: var(--ink); box-shadow: 0 2px 4px rgba(0,0,0,0.06); transition: opacity 0.2s; pointer-events: none; }}
.tag b {{ font: 600 10px var(--cond); letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); display: block; }}
.tag .m {{ color: var(--model); font-weight: 600; }}
.tag.alert {{ border-color: var(--limit); color: var(--limit); }}
.tag.heat {{ border-color: var(--heat); color: var(--heat); }}

.legend {{ position: absolute; left: 10px; top: 10px; display: grid; gap: 4px; font: 500 11px var(--mono); color: var(--muted); background: color-mix(in srgb, var(--panel) 92%, transparent); border: 1px solid var(--line); border-radius: 4px; padding: 6px 10px; }}
.ramp {{ position: relative; width: 200px; height: 8px; border-radius: 2px; }}
.ramp-ticks {{ position: relative; width: 200px; height: 13px; font-size: 10px; }}
.ramp-ticks span {{ position: absolute; transform: translateX(-50%); }}
.keys {{ display: flex; flex-wrap: wrap; gap: 4px 10px; margin-top: 4px; font-size: 10.5px; }}
.dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; vertical-align: 0; }}
.hint {{ position: absolute; right: 10px; bottom: 8px; font-size: 11px; color: var(--faint); pointer-events: none; }}

aside {{ display: flex; flex-direction: column; gap: 10px; overflow-y: auto; min-height: 0; padding-right: 2px; }}
section.card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; }}
h2 {{ font: 600 11.5px var(--cond); letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin: 0 0 8px; }}
.clock {{ display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }}
.clock .t {{ font: 500 22px var(--mono); font-variant-numeric: tabular-nums; }}
.clock .run-tag {{ font: 600 11px var(--cond); text-transform: uppercase; letter-spacing: 0.05em; color: var(--model); background: color-mix(in srgb, var(--model) 12%, transparent); padding: 2px 6px; border-radius: 3px; }}
.cmds {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-top: 8px; }}
.cmds div {{ font: 500 12px var(--mono); font-variant-numeric: tabular-nums; background: color-mix(in srgb, var(--ground) 60%, transparent); padding: 4px 6px; border-radius: 4px; }}
.cmds span {{ display: block; font: 600 9.5px var(--cond); letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted); }}

table {{ width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }}
th {{ font: 600 10px var(--cond); letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); text-align: right; padding: 0 0 4px; }}
th:first-child, td:first-child {{ text-align: left; }}
td {{ font: 400 12px var(--mono); text-align: right; padding: 3px 0; border-top: 1px solid var(--line); }}
td:first-child {{ font: 500 12.5px var(--sans); }}
td.m {{ color: var(--model); font-weight: 500; }}
td.bad {{ color: var(--limit); font-weight: 600; }}
td.warn {{ color: var(--warn); }}
td.okc {{ color: var(--ok); }}
.note {{ color: var(--faint); font-size: 11px; margin: 6px 0 0; line-height: 1.35; }}

.ledger {{ display: grid; gap: 6px; }}
.lrow {{ display: grid; grid-template-columns: 120px 1fr 58px; align-items: center; gap: 8px; font-size: 12px; }}
.lbar {{ height: 8px; background: color-mix(in srgb, var(--line) 60%, transparent); border-radius: 2px; overflow: hidden; }}
.lbar i {{ display: block; height: 100%; background: var(--heat); transition: width 0.1s; }}
.lrow .v {{ font: 500 11.5px var(--mono); text-align: right; font-variant-numeric: tabular-nums; }}

footer {{ display: grid; grid-template-columns: auto 1fr; gap: 10px; align-items: stretch; }}
.ctrl {{ display: flex; flex-direction: column; gap: 6px; justify-content: center; }}
.ctrl button {{ font: 600 13px var(--sans); background: var(--ink); color: var(--ground); border: none; border-radius: 4px; padding: 8px 14px; cursor: pointer; min-width: 84px; transition: opacity 0.15s; }}
.ctrl button:hover {{ opacity: 0.9; }}
.ctrl label {{ font: 600 10px var(--cond); letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted); display: grid; gap: 2px; }}
.ctrl select {{ font: 500 12px var(--sans); background: var(--panel); color: var(--ink); border: 1px solid var(--line); border-radius: 4px; padding: 3px 4px; }}
.chart {{ position: relative; height: 220px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); cursor: crosshair; touch-action: none; }}
#chart {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
.provenance {{ font: 500 11px var(--mono); color: var(--muted); max-width: 300px; }}
.view-tools {{ position: absolute; right: 10px; top: 10px; display: flex; gap: 4px; z-index: 2; }}
.view-tools button {{ font: 600 11px var(--sans); color: var(--ink); background: var(--panel); border: 1px solid var(--line); border-radius: 4px; padding: 5px 7px; cursor: pointer; }}
.view-tools button:focus-visible, .ctrl button:focus-visible {{ outline: 2px solid var(--model); outline-offset: 2px; }}
#modelStatus {{ position: absolute; left: 10px; bottom: 10px; max-width: 340px; font: 600 12px var(--sans); color: var(--limit); background: var(--panel); border-radius: 4px; padding: 4px 8px; z-index: 2; }}
#modelStatus:empty {{ display: none; }}

@media (max-width: 950px) {{
  .app {{ height: auto; grid-template-rows: auto auto auto; }}
  main {{ grid-template-columns: 1fr; }}
  .stage {{ height: 55vh; min-height: 320px; }}
  aside {{ overflow: visible; }}
  .runs {{ margin-left: 0; }}
}}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand">
      <h1>{title}</h1>
      <span class="sub">{subtitle}</span>
    </div>
    <nav class="runs" aria-label="Scenario navigation">
      <div class="pick">
        <label for="scenario">Scenario</label>
        <select id="scenario"></select>
      </div>
      <label class="toggle" for="labelsToggle"><input type="checkbox" id="labelsToggle" checked> 3D Tags</label>
      <span class="provenance" id="provenance" title="Data source and display mode"></span>
      <div class="navsep"></div>
      <a href="../index.html" class="home-btn" title="Return to Portfolio Hub">Hub ↗</a>
    </nav>
  </header>

  <main>
    <div class="stage">
      <div id="three"></div>
      <div id="tags"></div>
      <div id="modelStatus" role="status"></div>
      <div class="view-tools"><button id="topView" type="button" title="View from above">Top</button><button id="frontView" type="button" title="View from front">Front</button><button id="resetView" type="button" title="Restore initial camera view">Reset view</button></div>
      <div class="hint">drag to orbit · scroll to zoom · right-drag to pan</div>
      <div class="legend" id="legend"></div>
    </div>

    <aside>
      <section class="card" aria-label="Simulation state">
        <div class="clock">
          <div><h2 style="margin:0">Elapsed Time</h2><span class="t" id="clock">0:00</span></div>
          <span class="run-tag" id="scenarioBadge">Scenario</span>
        </div>
        <div class="cmds" id="cmds"></div>
      </section>

      <section class="card" aria-label="Sensors and telemetry">
        <h2>Telemetry · <span style="color:var(--model)">Simulated</span> vs Reference</h2>
        <table>
          <thead><tr><th>Channel</th><th>Sim.</th><th>Ref.</th><th>Δ</th></tr></thead>
          <tbody id="sens"></tbody>
        </table>
        <p class="note" id="sensorNote"></p>
      </section>

      <section class="card" aria-label="Flux and energy ledger">
        <h2 id="ledgerTitle">Energy & Flow Ledger</h2>
        <div class="ledger" id="ledger"></div>
      </section>

      {extra_aside}
    </aside>
  </main>

  <footer>
    <div class="ctrl">
      <button id="play" type="button">Play</button>
      <button id="stepBack" type="button" title="Previous sample">&#9664; Step</button>
      <button id="stepForward" type="button" title="Next sample">Step &#9654;</button>
      <label for="speed">Playback Speed
        <select id="speed">
          <option value="1">1×</option>
          <option value="5">5×</option>
          <option value="15" selected>15×</option>
          <option value="60">60×</option>
          <option value="3600">3600×</option>
        </select>
      </label>
    </div>
    <div class="chart" id="chartbox" aria-label="Interactive timeline scrubber">
      <canvas id="chart"></canvas>
    </div>
  </footer>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
<script>
const SCENARIOS = {scenarios_json};

const requestedScenario = new URLSearchParams(location.search).get("scenario");
let currentScenarioKey = requestedScenario && SCENARIOS[requestedScenario]
  ? requestedScenario : Object.keys(SCENARIOS)[0];
let currentScenario = SCENARIOS[currentScenarioKey];
let k = 0;
let playing = false;
let animSpeed = 15;
let playbackTime = 0;
function integratedDrive(key, reference) {{
  const times = currentScenario.series.t;
  const values = currentScenario.series[key];
  if (!values) return playbackTime - times[0];
  let area = 0;
  for (let i = 0; i + 1 < times.length && times[i] < playbackTime; i++) {{
    area += Math.max(0, values[i] / reference) * (Math.min(playbackTime, times[i + 1]) - times[i]);
  }}
  return area;
}}

const scenarioSelect = document.getElementById("scenario");
for (const [key, sc] of Object.entries(SCENARIOS)) {{
  const opt = document.createElement("option");
  opt.value = key;
  opt.textContent = sc.name;
  scenarioSelect.appendChild(opt);
}}
scenarioSelect.value = currentScenarioKey;
scenarioSelect.addEventListener("change", (e) => {{
  loadScenario(e.target.value);
  const url = new URL(location.href);
  url.searchParams.set("scenario", e.target.value);
  history.replaceState(null, "", url);
}});

function loadScenario(key) {{
  currentScenarioKey = key;
  currentScenario = SCENARIOS[key];
  k = 0;
  playbackTime = currentScenario.series.t[0];
  document.getElementById("provenance").textContent = (currentScenario.source || "Illustrative trajectory") + " · {geometry_source}";
  document.getElementById("scenarioBadge").textContent = currentScenario.badge || key;
  if (currentScenario.note) document.getElementById("sensorNote").textContent = currentScenario.note;
  if (currentScenario.ledgerTitle) document.getElementById("ledgerTitle").textContent = currentScenario.ledgerTitle;
  initLegend();
  drawChart();
  updateUI();
}}

const host = document.getElementById("three");
const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setSize(host.clientWidth, host.clientHeight);
renderer.shadowMap.enabled = true;
host.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, host.clientWidth / host.clientHeight, 1, 10000);
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 0.9));
const dirLight = new THREE.DirectionalLight(0xffffff, 0.65);
dirLight.position.set(500, 1000, 600);
scene.add(dirLight);

const tagsContainer = document.getElementById("tags");
const tagsList = [];
function addTag(name, getPos, getValue, className="") {{
  const el = document.createElement("div");
  el.className = "tag " + className;
  el.innerHTML = `<b>${{name}}</b><span class="m">--</span>`;
  tagsContainer.appendChild(el);
  tagsList.push({{ el, getPos, getValue }});
}}

document.getElementById("labelsToggle").addEventListener("change", (e) => {{
  tagsContainer.style.display = e.target.checked ? "block" : "none";
}});

// 3D Scene Specifics
{three_setup_code}

// Map selected simulation state onto named 3D parts.
{update_3d_code}

const initialView = {{position: camera.position.clone(), target: controls.target.clone()}};
const viewDistance = camera.position.distanceTo(controls.target);
document.getElementById("topView").addEventListener("click", () => {{
  camera.position.copy(controls.target).add(new THREE.Vector3(0.001, viewDistance, 0));
  controls.update();
}});
document.getElementById("frontView").addEventListener("click", () => {{
  camera.position.copy(controls.target).add(new THREE.Vector3(0, viewDistance * 0.22, viewDistance));
  controls.update();
}});
document.getElementById("resetView").addEventListener("click", () => {{
  camera.position.copy(initialView.position);
  controls.target.copy(initialView.target);
  controls.update();
}});

window.addEventListener("resize", () => {{
  const w = host.clientWidth, h = host.clientHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  drawChart();
}});

function initLegend() {{
  const leg = document.getElementById("legend");
  if (!currentScenario.legend) {{
    leg.style.display = "none";
    return;
  }}
  leg.style.display = "grid";
  leg.innerHTML = `
    <div>${{currentScenario.legend.title}}</div>
    <div class="ramp" style="background: linear-gradient(90deg, ${{currentScenario.legend.gradient}});"></div>
    <div class="ramp-ticks">
      ${{currentScenario.legend.ticks.map(t => `<span style="left:${{t.pct}}%">${{t.label}}</span>`).join("")}}
    </div>
    <div class="keys">
      ${{currentScenario.legend.keys.map(k => `<span><span class="dot" style="background:${{k.color}}"></span>${{k.label}}</span>`).join("")}}
    </div>
  `;
}}

function updateUI() {{
  const data = currentScenario.series;
  const t = data.t[k];
  const days = Math.floor(t / 86400);
  const mins = Math.floor((t % 86400) / 60);
  const secs = Math.floor(t % 60);
  document.getElementById("clock").textContent = currentScenario.timeUnit === "years"
    ? `Year ${{Number(t).toFixed(0)}}`
    : `${{days ? days + 'd ' : ''}}${{mins}}:${{secs < 10 ? '0' : ''}}${{secs}}`;

  const cmdsEl = document.getElementById("cmds");
  cmdsEl.innerHTML = "";
  if (currentScenario.cmds) {{
    for (const c of currentScenario.cmds) {{
      const val = data[c.key] ? data[c.key][k] : c.default;
      const d = document.createElement("div");
      d.innerHTML = `<span>${{c.label}}</span><b>${{typeof val === 'number' ? val.toFixed(c.dec ?? 1) : val}} ${{c.unit || ''}}</b>`;
      cmdsEl.appendChild(d);
    }}
  }}

  const tbody = document.getElementById("sens");
  tbody.innerHTML = "";
  if (currentScenario.sensors) {{
    for (const s of currentScenario.sensors) {{
      const simVal = data[s.key] ? data[s.key][k] : null;
      const refVal = data[s.refKey] ? data[s.refKey][k] : s.refStatic;
      const delta = (typeof simVal === "number" && typeof refVal === "number") ? (simVal - refVal) : null;
      let statusClass = "m";
      if (s.limit && typeof simVal === "number" && Math.abs(simVal) > s.limit) statusClass = "bad";
      else if (delta != null && Math.abs(delta) > (s.tol || 2)) statusClass = "warn";
      
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${{s.name}}</td>
        <td class="${{statusClass}}">${{simVal != null ? (typeof simVal === 'number' ? simVal.toFixed(s.dec ?? 1) : simVal) + (s.unit || '') : '--'}}</td>
        <td>${{refVal != null ? (typeof refVal === 'number' ? refVal.toFixed(s.dec ?? 1) : refVal) + (s.unit || '') : '--'}}</td>
        <td class="${{delta != null && Math.abs(delta) > (s.tol || 2) ? 'warn' : 'okc'}}">${{delta != null ? (delta > 0 ? '+' : '') + delta.toFixed(s.dec ?? 1) : '--'}}</td>
      `;
      tbody.appendChild(tr);
    }}
  }}

  const ledgerEl = document.getElementById("ledger");
  ledgerEl.innerHTML = "";
  if (currentScenario.ledger) {{
    for (const item of currentScenario.ledger) {{
      const v = data[item.key] ? data[item.key][k] : 0;
      const maxVal = item.max || 100;
      const pct = Math.min(100, Math.max(0, (Math.abs(v) / maxVal) * 100));
      const row = document.createElement("div");
      row.className = "lrow";
      row.innerHTML = `
        <span>${{item.label}}</span>
        <div class="lbar"><i style="width:${{pct}}%; background:${{item.color || 'var(--heat)'}}"></i></div>
        <span class="v">${{v.toFixed(item.dec ?? 1)}} ${{item.unit || ''}}</span>
      `;
      ledgerEl.appendChild(row);
    }}
  }}

  if (typeof update3D === "function") update3D(data, k);
  positionTags();
  drawChart();
}}

function positionTags() {{
  const data = currentScenario.series;
  const widthHalf = host.clientWidth / 2;
  const heightHalf = host.clientHeight / 2;
  const tempV = new THREE.Vector3();
  const placed = [];
  for (const item of tagsList) {{
    const pos = item.getPos();
    tempV.copy(pos).project(camera);
    if (tempV.z > -1 && tempV.z < 1 && Math.abs(tempV.x) < 1 && Math.abs(tempV.y) < 1) {{
      const x = (tempV.x * widthHalf) + widthHalf;
      let y = -(tempV.y * heightHalf) + heightHalf;
      const w = item.el.offsetWidth || 130, h = item.el.offsetHeight || 35;
      for (let tries = 0; tries < tagsList.length; tries++) {{
        const overlap = placed.find(p => Math.abs(p.x - x) < (p.w + w) / 2 + 6 && y > p.y - p.h - 6 && y - h < p.y + 6);
        if (!overlap) break;
        y = overlap.y + h + 8;
      }}
      y = Math.max(h + 4, Math.min(host.clientHeight - 4, y));
      item.el.style.left = `${{Math.max(w / 2 + 4, Math.min(host.clientWidth - w / 2 - 4, x))}}px`;
      item.el.style.top = `${{y}}px`;
      item.el.style.opacity = "1";
      placed.push({{x, y, w, h}});
      const valSpan = item.el.querySelector(".m");
      if (valSpan && item.getValue) valSpan.textContent = item.getValue(data, k);
    }} else {{
      item.el.style.opacity = "0";
    }}
  }}

}}

const chartCanvas = document.getElementById("chart");
const ctx = chartCanvas.getContext("2d");
let isDraggingChart = false;

function drawChart() {{
  const rect = chartCanvas.getBoundingClientRect();
  chartCanvas.width = rect.width * (window.devicePixelRatio || 1);
  chartCanvas.height = rect.height * (window.devicePixelRatio || 1);
  ctx.resetTransform();
  ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
  const cW = rect.width, cH = rect.height;

  ctx.clearRect(0, 0, cW, cH);

  const seriesCfg = currentScenario.chartSeries || [];
  const tArr = currentScenario.series.t;
  if (!tArr || tArr.length === 0) return;
  const n = tArr.length;

  const padLeft = 92, padRight = 70, padTop = 8, padBottom = 22;
  const plotW = cW - padLeft - padRight;
  const plotH = cH - padTop - padBottom;
  if (plotW <= 0 || plotH <= 0) return;
  const laneH = plotH / Math.max(1, seriesCfg.length);
  const css = getComputedStyle(document.documentElement);
  ctx.font = "10px IBM Plex Mono";

  ctx.textAlign = "center";
  const tSteps = 5;
  for (let i = 0; i <= tSteps; i++) {{
    const frac = i / tSteps;
    const xPx = padLeft + (plotW * frac);
    const tVal = tArr[0] + ((tArr[n - 1] - tArr[0]) * frac);
    const d = Math.floor(tVal / 86400), m = Math.floor((tVal % 86400) / 60), s = Math.floor(tVal % 60);
    ctx.fillStyle = css.getPropertyValue("--muted");
    ctx.fillText(currentScenario.timeUnit === "years" ? `Y${{tVal.toFixed(0)}}` : d ? `${{d}}d ${{Math.floor(m / 60)}}h` : `${{m}}:${{s < 10 ? '0' : ''}}${{s}}`, xPx, cH - 6);
  }}

  for (const [lane, cfg] of seriesCfg.entries()) {{
    const arr = currentScenario.series[cfg.key];
    if (!arr) continue;
    const finite = arr.filter(Number.isFinite);
    if (!finite.length) continue;
    let lo = Math.min(...finite), hi = Math.max(...finite);
    if (hi - lo < Math.max(1e-6, Math.abs(lo) * 1e-4)) {{ lo -= 0.5; hi += 0.5; }}
    const span = hi - lo;
    const top = padTop + lane * laneH;
    ctx.strokeStyle = "rgba(128, 140, 150, 0.25)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padLeft, top + laneH);
    ctx.lineTo(cW - padRight, top + laneH);
    ctx.stroke();
    ctx.fillStyle = cfg.color || "#2f5bd3";
    ctx.textAlign = "left";
    ctx.fillText(cfg.label, 5, top + 14);
    ctx.fillStyle = css.getPropertyValue("--muted");
    ctx.fillText(`${{lo.toFixed(1)}}–${{hi.toFixed(1)}}`, 5, top + 28);
    ctx.fillText(Number.isFinite(arr[k]) ? arr[k].toFixed(2) : "--", cW - padRight + 8, top + laneH / 2);
    ctx.strokeStyle = cfg.color || "#2f5bd3";
    ctx.lineWidth = cfg.width || 1.8;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {{
      if (!Number.isFinite(arr[i])) continue;
      const xPx = padLeft + plotW * (tArr[i] - tArr[0]) / (tArr[n - 1] - tArr[0] || 1);
      const yPx = top + laneH - 5 - (laneH - 10) * (arr[i] - lo) / span;
      if (i === 0) ctx.moveTo(xPx, yPx); else ctx.lineTo(xPx, yPx);
    }}
    ctx.stroke();
  }}

  const curFrac = (tArr[k] - tArr[0]) / (tArr[n - 1] - tArr[0] || 1);
  const curX = padLeft + (plotW * curFrac);
  ctx.strokeStyle = css.getPropertyValue("--ink");
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 3]);
  ctx.beginPath();
  ctx.moveTo(curX, padTop - 4);
  ctx.lineTo(curX, padTop + plotH + 4);
  ctx.stroke();
  ctx.setLineDash([]);

}}

function seekFromMouse(e) {{
  const rect = chartCanvas.getBoundingClientRect();
  const padLeft = 92, padRight = 70;
  const plotW = rect.width - padLeft - padRight;
  if (plotW <= 0) return;
  const x = Math.max(0, Math.min(plotW, (e.clientX - rect.left) - padLeft));
  const frac = x / plotW;
  const times = currentScenario.series.t;
  const target = times[0] + frac * (times[times.length - 1] - times[0]);
  k = times.reduce((best, t, i) => Math.abs(t - target) < Math.abs(times[best] - target) ? i : best, 0);
  playbackTime = times[k];
  updateUI();
}}

chartCanvas.addEventListener("pointerdown", (e) => {{
  isDraggingChart = true;
  chartCanvas.setPointerCapture(e.pointerId);
  seekFromMouse(e);
}});
chartCanvas.addEventListener("pointermove", (e) => {{
  if (isDraggingChart) seekFromMouse(e);
}});
chartCanvas.addEventListener("pointerup", (e) => {{
  isDraggingChart = false;
  chartCanvas.releasePointerCapture(e.pointerId);
}});

const playBtn = document.getElementById("play");
function setPlaying(value) {{
  playing = value;
  playBtn.textContent = playing ? "Pause" : "Play";
  playBtn.style.background = playing ? "var(--heat)" : "var(--ink)";
}}
playBtn.addEventListener("click", () => {{
  if (!playing && k === currentScenario.series.t.length - 1) {{
    k = 0;
    playbackTime = currentScenario.series.t[0];
    updateUI();
  }}
  setPlaying(!playing);
}});
for (const [id, direction] of [["stepBack", -1], ["stepForward", 1]]) {{
  document.getElementById(id).addEventListener("click", () => {{
    setPlaying(false);
    k = Math.max(0, Math.min(currentScenario.series.t.length - 1, k + direction));
    playbackTime = currentScenario.series.t[k];
    updateUI();
  }});
}}

document.getElementById("speed").addEventListener("change", (e) => {{
  animSpeed = parseInt(e.target.value, 10);
}});

let lastAnimTime = null;
function animate(time) {{
  requestAnimationFrame(animate);
  controls.update();
  positionTags();

  if (playing && lastAnimTime != null) {{
    const times = currentScenario.series.t;
    playbackTime = Math.min(times[times.length - 1], playbackTime + Math.min(0.25, (time - lastAnimTime) / 1000) * animSpeed);
    let next = k;
    while (next + 1 < times.length && times[next + 1] <= playbackTime) next++;
    if (next !== k) {{ k = next; updateUI(); }}
    if (playbackTime >= times[times.length - 1]) setPlaying(false);
  }}
  lastAnimTime = time;
  if (typeof renderFrame === "function") renderFrame(playbackTime * 1000);
  renderer.render(scene, camera);
}}

loadScenario(currentScenarioKey);
requestAnimationFrame(animate);
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Viewer v2: shared viewer_core/viewer.js + per-project config shell.
# Results are loaded from <project>/viewer_data/<scenario>.json/.bin at runtime.
# ---------------------------------------------------------------------------
VIEWER_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__TITLE__ · Annual Simulation Viewer</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="__DESC__">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Semi+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="../viewer_core/viewer.css">
<script type="importmap">{"imports": {"three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js", "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div class="app">
  <header>
    <div class="brand"><h1>__TITLE__</h1><span class="sub">__SUBTITLE__</span></div>
    <nav class="runs" aria-label="Scenario and display options">
      <div class="pick"><label for="scenario">Scenario</label><select id="scenario"></select></div>
      <label class="toggle"><input type="checkbox" id="labelsToggle" checked> Tags</label>
      <label class="toggle"><input type="checkbox" id="spToggle" checked> State points</label>
      <label class="toggle"><input type="checkbox" id="flowToggle" checked> Flow</label>
      <label class="toggle" title="Ambient occlusion (turn off on slow machines)"><input type="checkbox" id="aoToggle" checked> AO</label>
      <span class="navsep"></span>
      <a href="../index.html" class="btn" title="Return to portfolio hub">Hub ↗</a>
    </nav>
  </header>
  <main>
    <div class="stage">
      <div id="three"></div>
      <div id="tags"></div>
      <div id="tip"></div>
      <div id="inspect"></div>
      <div id="modelStatus" role="status"></div>
      <div class="view-tools"><button class="btn" id="topView" type="button">Top</button><button class="btn" id="frontView" type="button">Front</button><button class="btn" id="resetView" type="button">Reset</button></div>
      <div class="legend" id="legend"></div>
      <div class="hint">drag orbit · scroll zoom · right-drag pan · click equipment for specs</div>
    </div>
    <aside>
      <div class="clockbar">
        <div><div class="d" id="clockDate">–</div><div class="t" id="clock">–</div></div>
        <span class="run-tag" id="scenarioBadge">–</span>
      </div>
      <div class="tabs" role="tablist">
        <button data-tab="overview" aria-selected="true">Overview</button>
        <button data-tab="sp" id="tabSp" aria-selected="false">State points</button>
        <button data-tab="diag" id="tabDiag" aria-selected="false">Diagrams</button>
        <button data-tab="vars" aria-selected="false">Variables</button>
        <button data-tab="kpi" aria-selected="false">Annual KPIs</button>
      </div>
      <div class="tabpanes">
        <section class="pane on" data-tab="overview">
          <div class="cmds" id="cmds"></div>
          <h2>Live telemetry at cursor</h2>
          <table><thead id="sensHead"><tr><th>Channel</th><th>Sim.</th><th>Ref.</th><th>Δ</th></tr></thead><tbody id="sens"></tbody></table>
          <h2 id="ledgerTitle">Energy flows</h2>
          <div class="ledger" id="ledger"></div>
          <p class="note" id="sensorNote"></p>
          <p class="note" id="provenance"></p>
        </section>
        <section class="pane" data-tab="sp" id="spPane"><div id="spTables"></div>
          <p class="note">Hourly-mean states from full CoolProp equation-of-state solutions. Hover a row to locate the point in 3D.</p></section>
        <section class="pane" data-tab="diag" id="diagPane"></section>
        <section class="pane" data-tab="vars">
          <input class="vsearch" id="vsearch" type="search" placeholder="Search channels… (e.g. enthalpy, pressure, 5_T)">
          <p class="note" id="varCount" style="margin:0 0 6px"></p>
          <div class="vfocus" id="vfocus"><b id="vfTitle"></b><div class="stats" id="vfStats"></div><canvas id="monthly"></canvas></div>
          <div id="vars"></div>
        </section>
        <section class="pane" data-tab="kpi"><div id="kpis"></div></section>
      </div>
    </aside>
  </main>
  <footer>
    <div class="ctrl">
      <button id="play" type="button">Play</button>
      <div class="row"><button class="ghost" id="stepBack" type="button" title="Previous sample (←)">◀</button><button class="ghost" id="stepFwd" type="button" title="Next sample (→)">▶</button></div>
      <label for="speed">Playback
        <select id="speed">__SPEEDS__</select>
      </label>
    </div>
    <div class="chartwrap">
      <div class="charttools">
        __ZOOMS__
        <span class="sp"></span><span class="info" id="winInfo"></span>
      </div>
      <canvas id="chart" aria-label="Timeline: click or drag to seek, scroll to zoom"></canvas>
      <canvas id="overview" aria-label="Full-period overview: drag to move the window"></canvas>
    </div>
  </footer>
</div>
<script type="application/json" id="viewer-config">__CONFIG__</script>
<script type="module" src="../viewer_core/viewer.js"></script>
</body>
</html>
"""

HOURLY_SPEEDS = [(3600, "1 h / s"), (6 * 3600, "6 h / s"), (86400, "1 day / s"), (7 * 86400, "1 week / s"),
                 (30 * 86400, "1 month / s")]
HOURLY_ZOOMS = [(24, "Day"), (168, "Week"), (744, "Month"), (0, "Year")]


def write_viewer(project_dir, title, subtitle, scenarios, scene, speeds=None, zooms=None, description=""):
    """Write <project>/viewer.html for the shared viewer. scenarios: list of {key,name,badge}."""
    project_dir = Path(project_dir)
    for sc in scenarios:
        for ext in ("json", "bin"):
            f = project_dir / "viewer_data" / f"{sc['key']}.{ext}"
            if not f.exists():
                raise FileNotFoundError(f"missing results {f}; run the annual simulation first")
    speeds = speeds or HOURLY_SPEEDS
    zooms = zooms or HOURLY_ZOOMS
    default_speed = speeds[min(2, len(speeds) - 1)][0]
    cfg = {"title": title, "scenarios": scenarios, "scene": scene}
    html = (VIEWER_SHELL
            .replace("__TITLE__", title).replace("__SUBTITLE__", subtitle)
            .replace("__DESC__", (description or subtitle).replace('"', "'"))
            .replace("__SPEEDS__", "".join(
                f'<option value="{v}"{" selected" if v == default_speed else ""}>{lab}</option>' for v, lab in speeds))
            .replace("__ZOOMS__", "".join(
                f'<button class="btn{" on" if h == 0 else ""}" type="button" data-win="{h}">{lab}</button>' for h, lab in zooms))
            .replace("__CONFIG__", json.dumps(cfg, ensure_ascii=False).replace("</", "<\\u002f")))
    out = project_dir / "viewer.html"
    out.write_text(html, encoding="utf-8")
    return out



def load_project_module(path, alias):
    """Import a project's simulation module in isolation. Several projects share module names (annual_sim,
    model, src, params), so the project directory goes first on sys.path and colliding cached modules are dropped."""
    import importlib.util
    import sys
    path = Path(path)
    for name in list(sys.modules):
        if name in ("annual_sim", "model", "src", "params") or name.startswith(("model.", "src.")):
            del sys.modules[name]
    if str(path.parent) in sys.path:
        sys.path.remove(str(path.parent))
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(alias, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod
