"""build_viewers.py
Generates high-fidelity, self-contained interactive 3D simulation frontends for all 8 portfolio projects.
Each viewer mirrors the architecture of galaxia_modelling (loopview.html):
- Interactive Three.js WebGL scene with orbit controls, realistic 3D component meshes, and fluid/energy flow particle animation
- Top navigation with Scenario selection dropdown, model parameters, and pipe/component label toggles
- Right-hand KPI panel with simulation clock, actuator states, sensor tables (model vs target/baseline), energy/mass flow ledger, and subsystem diagnostics
- Bottom interactive time-series chart with scrubber, playback controls (Play/Pause, speed multipliers), and multi-series curves
"""

import os
import json
import math
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent

def get_base_html(title, subtitle, project_id, scenarios_json, three_setup_js, update_3d_js, extra_aside_html=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} · Simulation Viewer</title>
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
.app {{ display: grid; grid-template-rows: auto 1fr auto; height: 100vh; padding: 12px 16px; gap: 10px; }}
header {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 18px; }}
.brand {{ display: flex; align-items: baseline; gap: 8px; }}
h1 {{ font: 700 18px/1.1 var(--cond); letter-spacing: 0.01em; margin: 0; text-wrap: balance; }}
.sub {{ color: var(--muted); font-size: 13px; }}
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
.tag {{ position: absolute; transform: translate(-50%, -100%); font: 500 11px/1.25 var(--mono); white-space: nowrap; background: color-mix(in srgb, var(--panel) 90%, transparent); border: 1px solid var(--line); border-radius: 3px; padding: 2px 6px; color: var(--ink); box-shadow: 0 2px 4px rgba(0,0,0,0.06); transition: opacity 0.2s; }}
.tag b {{ font: 600 10px var(--cond); letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); display: block; }}
.tag .m {{ color: var(--model); font-weight: 600; }}
.tag.alert {{ border-color: var(--limit); color: var(--limit); }}
.tag.heat {{ border-color: var(--heat); color: var(--heat); }}

.legend {{ position: absolute; left: 10px; top: 10px; display: grid; gap: 4px; font: 500 11px var(--mono); color: var(--muted); background: color-mix(in srgb, var(--panel) 90%, transparent); border: 1px solid var(--line); border-radius: 4px; padding: 6px 10px; }}
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
.cmds div {{ font: 500 12.5px var(--mono); font-variant-numeric: tabular-nums; background: color-mix(in srgb, var(--ground) 60%, transparent); padding: 4px 6px; border-radius: 4px; }}
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
.chart {{ position: relative; height: 155px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); cursor: crosshair; touch-action: none; }}
#chart {{ position: absolute; inset: 0; width: 100%; height: 100%; }}

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
      <div class="navsep"></div>
      <a href="../index.html" class="home-btn" title="Return to Portfolio Hub">Hub ↗</a>
    </nav>
  </header>

  <main>
    <div class="stage">
      <div id="three"></div>
      <div id="tags"></div>
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

      {extra_aside_html}
    </aside>
  </main>

  <footer>
    <div class="ctrl">
      <button id="play" type="button">Play</button>
      <label for="speed">Playback Speed
        <select id="speed">
          <option value="1">1×</option>
          <option value="5">5×</option>
          <option value="15" selected>15×</option>
          <option value="60">60×</option>
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
<script>
const SCENARIOS = {scenarios_json};

let currentScenarioKey = Object.keys(SCENARIOS)[0];
let currentScenario = SCENARIOS[currentScenarioKey];
let k = 0;
let playing = false;
let playTimer = null;
let animSpeed = 15;

// Build Scenario Dropdown
const scenarioSelect = document.getElementById("scenario");
for (const [key, sc] of Object.entries(SCENARIOS)) {{
  const opt = document.createElement("option");
  opt.value = key;
  opt.textContent = sc.name;
  scenarioSelect.appendChild(opt);
}}
scenarioSelect.addEventListener("change", (e) => {{
  loadScenario(e.target.value);
}});

function loadScenario(key) {{
  currentScenarioKey = key;
  currentScenario = SCENARIOS[key];
  k = 0;
  document.getElementById("scenarioBadge").textContent = currentScenario.badge || key;
  if (currentScenario.note) document.getElementById("sensorNote").textContent = currentScenario.note;
  if (currentScenario.ledgerTitle) document.getElementById("ledgerTitle").textContent = currentScenario.ledgerTitle;
  initLegend();
  drawChart();
  updateUI();
}}

// Three.js Scene Setup
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

// Tags container
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

// Specific project 3D setup
{three_setup_js}

window.addEventListener("resize", () => {{
  const w = host.clientWidth, h = host.clientHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  drawChart();
}});

// Legend Setup
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

// UI Update
function updateUI() {{
  const data = currentScenario.series;
  const t = data.t[k];
  const mins = Math.floor(t / 60);
  const secs = Math.floor(t % 60);
  document.getElementById("clock").textContent = `${{mins}}:${{secs < 10 ? '0' : ''}}${{secs}}`;

  // Commands / States
  const cmdsEl = document.getElementById("cmds");
  cmdsEl.innerHTML = "";
  if (currentScenario.cmds) {{
    for (const c of currentScenario.cmds) {{
      const val = data[c.key] ? data[c.key][k] : c.default;
      const d = document.createElement("div");
      d.innerHTML = `<span>${{c.label}}</span><b>${{val}} ${{c.unit || ''}}</b>`;
      cmdsEl.appendChild(d);
    }}
  }}

  // Telemetry table
  const tbody = document.getElementById("sens");
  tbody.innerHTML = "";
  if (currentScenario.sensors) {{
    for (const s of currentScenario.sensors) {{
      const simVal = data[s.key] ? data[s.key][k] : null;
      const refVal = data[s.refKey] ? data[s.refKey][k] : s.refStatic;
      const delta = (simVal != null && refVal != null) ? (simVal - refVal) : null;
      let statusClass = "m";
      if (s.limit && Math.abs(simVal) > s.limit) statusClass = "bad";
      else if (delta != null && Math.abs(delta) > (s.tol || 2)) statusClass = "warn";
      
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${{s.name}}</td>
        <td class="${{statusClass}}">${{simVal != null ? simVal.toFixed(s.dec ?? 1) + (s.unit || '') : '--'}}</td>
        <td>${{refVal != null ? (typeof refVal === 'number' ? refVal.toFixed(s.dec ?? 1) : refVal) + (s.unit || '') : '--'}}</td>
        <td class="${{delta != null && Math.abs(delta) > (s.tol || 2) ? 'warn' : 'okc'}}">${{delta != null ? (delta > 0 ? '+' : '') + delta.toFixed(s.dec ?? 1) : '--'}}</td>
      `;
      tbody.appendChild(tr);
    }}
  }}

  // Energy/flow ledger
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

  // Update 3D tags
  const widthHalf = host.clientWidth / 2;
  const heightHalf = host.clientHeight / 2;
  const tempV = new THREE.Vector3();
  for (const item of tagsList) {{
    const pos = item.getPos();
    tempV.copy(pos).project(camera);
    if (tempV.z < 1) {{
      const x = (tempV.x * widthHalf) + widthHalf;
      const y = -(tempV.y * heightHalf) + heightHalf;
      item.el.style.left = `${{x}}px`;
      item.el.style.top = `${{y}}px`;
      item.el.style.opacity = "1";
      const valSpan = item.el.querySelector(".m");
      if (valSpan && item.getValue) valSpan.textContent = item.getValue(data, k);
    }} else {{
      item.el.style.opacity = "0";
    }}
  }}

  // Call custom project 3D updates
  if (typeof update3D === "function") {{
    update3D(data, k);
  }}

  drawChart();
}}

// Timeline Canvas Chart
const chartCanvas = document.getElementById("chart");
const ctx = chartCanvas.getContext("2d");
let isDraggingChart = false;

function drawChart() {{
  const rect = chartCanvas.getBoundingClientRect();
  chartCanvas.width = rect.width * (window.devicePixelRatio || 1);
  chartCanvas.height = rect.height * (window.devicePixelRatio || 1);
  const W = chartCanvas.width, H = chartCanvas.height;
  ctx.resetTransform();
  ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
  const cW = rect.width, cH = rect.height;

  ctx.clearRect(0, 0, cW, cH);

  const seriesCfg = currentScenario.chartSeries || [];
  const tArr = currentScenario.series.t;
  if (!tArr || tArr.length === 0) return;
  const n = tArr.length;

  const padLeft = 46, padRight = 16, padTop = 16, padBottom = 22;
  const plotW = cW - padLeft - padRight;
  const plotH = cH - padTop - padBottom;

  // Compute min/max across displayed series
  let yMin = Infinity, yMax = -Infinity;
  for (const cfg of seriesCfg) {{
    const arr = currentScenario.series[cfg.key];
    if (!arr) continue;
    for (let i = 0; i < n; i++) {{
      if (arr[i] < yMin) yMin = arr[i];
      if (arr[i] > yMax) yMax = arr[i];
    }}
  }}
  if (yMin === Infinity) {{ yMin = 0; yMax = 100; }}
  if (yMax - yMin < 1e-4) {{ yMax += 1; yMin -= 1; }}
  const ySpan = yMax - yMin;

  // Grid lines
  ctx.strokeStyle = "rgba(128, 140, 150, 0.18)";
  ctx.lineWidth = 1;
  const gridSteps = 4;
  ctx.fillStyle = "var(--faint)";
  ctx.font = "10px IBM Plex Mono";
  ctx.textAlign = "right";
  for (let i = 0; i <= gridSteps; i++) {{
    const yVal = yMin + (ySpan * (i / gridSteps));
    const yPx = padTop + plotH - (plotH * (i / gridSteps));
    ctx.beginPath();
    ctx.moveTo(padLeft, yPx);
    ctx.lineTo(cW - padRight, yPx);
    ctx.stroke();
    ctx.fillText(yVal.toFixed(1), padLeft - 6, yPx + 3);
  }}

  // Time labels
  ctx.textAlign = "center";
  const tSteps = 5;
  for (let i = 0; i <= tSteps; i++) {{
    const frac = i / tSteps;
    const xPx = padLeft + (plotW * frac);
    const tVal = tArr[0] + ((tArr[n - 1] - tArr[0]) * frac);
    const m = Math.floor(tVal / 60), s = Math.floor(tVal % 60);
    ctx.fillText(`${{m}}:${{s < 10 ? '0' : ''}}${{s}}`, xPx, cH - 6);
  }}

  // Curves
  for (const cfg of seriesCfg) {{
    const arr = currentScenario.series[cfg.key];
    if (!arr) continue;
    ctx.strokeStyle = cfg.color || "#2f5bd3";
    ctx.lineWidth = cfg.width || 1.8;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {{
      const xPx = padLeft + (plotW * (i / (n - 1)));
      const yPx = padTop + plotH - (plotH * ((arr[i] - yMin) / ySpan));
      if (i === 0) ctx.moveTo(xPx, yPx);
      else ctx.lineTo(xPx, yPx);
    }}
    ctx.stroke();
  }}

  // Scrubber line
  const curFrac = k / (n - 1);
  const curX = padLeft + (plotW * curFrac);
  ctx.strokeStyle = "var(--ink)";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 3]);
  ctx.beginPath();
  ctx.moveTo(curX, padTop - 4);
  ctx.lineTo(curX, padTop + plotH + 4);
  ctx.stroke();
  ctx.setLineDash([]);

  // Legend at top right
  ctx.textAlign = "left";
  let legX = padLeft + 10;
  for (const cfg of seriesCfg) {{
    ctx.fillStyle = cfg.color || "#2f5bd3";
    ctx.fillRect(legX, 5, 8, 8);
    ctx.fillStyle = "var(--muted)";
    ctx.fillText(cfg.label, legX + 12, 12);
    legX += ctx.measureText(cfg.label).width + 24;
  }}
}}

function seekFromMouse(e) {{
  const rect = chartCanvas.getBoundingClientRect();
  const padLeft = 46, padRight = 16;
  const plotW = rect.width - padLeft - padRight;
  const x = Math.max(0, Math.min(plotW, (e.clientX - rect.left) - padLeft));
  const frac = x / plotW;
  const n = currentScenario.series.t.length;
  k = Math.round(frac * (n - 1));
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

// Playback logic
const playBtn = document.getElementById("play");
playBtn.addEventListener("click", () => {{
  playing = !playing;
  playBtn.textContent = playing ? "Pause" : "Play";
  playBtn.style.background = playing ? "var(--heat)" : "var(--ink)";
}});

document.getElementById("speed").addEventListener("change", (e) => {{
  animSpeed = parseInt(e.target.value, 10);
}});

let lastTime = performance.now();
function animate(time) {{
  requestAnimationFrame(animate);
  const dt = (time - lastTime) / 1000;
  lastTime = time;

  controls.update();

  if (playing) {{
    const n = currentScenario.series.t.length;
    k = (k + 1) % n;
    updateUI();
  }}

  renderer.render(scene, camera);
}}

// Initialize
loadScenario(currentScenarioKey);
requestAnimationFrame(animate);
</script>
</body>
</html>
"""

print("Base HTML generator template compiled.")
