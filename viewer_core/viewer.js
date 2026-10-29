// Shared simulation viewer: loads annual results (viewer_data/<scenario>.json + .bin)
// and a Blender-exported GLB, binds simulated channels to the 3D scene, and provides
// KPI, state-point, thermodynamic-diagram, variable-browser and timeline views.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { RGBELoader } from "three/addons/loaders/RGBELoader.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { GTAOPass } from "three/addons/postprocessing/GTAOPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const CFG = JSON.parse(document.getElementById("viewer-config").textContent);
const $ = (id) => document.getElementById(id);
const css = () => getComputedStyle(document.documentElement);
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const S = {
  key: null, sc: null, data: {}, meta: {}, n: 0, k: 0, kf: 0, playing: false,
  speed: 86400, win: [0, 0], pinned: [], focus: null, cache: {}, tab: "overview",
};

// ---------------------------------------------------------------- formatting
function fmt(v, dec = 2) {
  if (v === null || v === undefined || !Number.isFinite(v)) return "–";
  const a = Math.abs(v);
  if (a >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (a >= 1e4 && dec > 0) dec = 0;
  return v.toLocaleString("en-GB", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
function val(key, k = S.k) {
  const a = S.data[key];
  return a ? a[k] : NaN;
}
function chMeta(key) { return S.meta[key] || { label: key, unit: "", dec: 2 }; }
function timeOf(i) {
  const sc = S.sc;
  if (sc.timeUnit === "years") return { short: `Year ${Math.round(sc.t0 + i * sc.dt)}`, long: `Year ${Math.round(sc.t0 + i * sc.dt)}`, date: null };
  const d = new Date(Date.parse(sc.t0) + i * sc.dt * 1000);
  const hh = String(d.getUTCHours()).padStart(2, "0"), mm = String(d.getUTCMinutes()).padStart(2, "0");
  const day = `${DAYS[d.getUTCDay()]} ${String(d.getUTCDate()).padStart(2, "0")} ${MONTHS[d.getUTCMonth()]}`;
  return { short: `${day} ${hh}:${mm}`, long: `${day} ${d.getUTCFullYear()}`, clock: `${hh}:${mm}`, date: d };
}
function rampColor(name, t) {
  t = Math.max(0, Math.min(1, t));
  const R = {
    thermal: [[0, [27, 42, 107]], [.3, [43, 108, 176]], [.5, [63, 167, 160]], [.72, [240, 140, 46]], [1, [215, 48, 31]]],
    cool: [[0, [230, 240, 250]], [1, [29, 111, 184]]],
    green: [[0, [180, 83, 9]], [.5, [234, 179, 8]], [1, [21, 128, 61]]],
    power: [[0, [100, 116, 139]], [1, [250, 204, 21]]],
  }[name] || [[0, [80, 90, 100]], [1, [194, 65, 12]]];
  for (let i = 1; i < R.length; i++) {
    if (t <= R[i][0]) {
      const [t0, c0] = R[i - 1], [t1, c1] = R[i];
      const f = (t - t0) / (t1 - t0);
      return new THREE.Color(...c0.map((c, j) => (c + (c1[j] - c) * f) / 255)).convertSRGBToLinear();
    }
  }
  return new THREE.Color(...R[R.length - 1][1].map(c => c / 255)).convertSRGBToLinear();
}

// ---------------------------------------------------------------- 3D scene
const host = $("three");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = CFG.scene.exposure ?? 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
host.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(renderer), 0.04).texture;   // fallback until the HDRI loads
const ASSETS = "../assets/";
const camera = new THREE.PerspectiveCamera(CFG.scene.fov || 35, 1, 0.05, 20000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI * 0.495;
const hemi = new THREE.HemisphereLight(0xf4f7ff, 0x5a5348, 0.25);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff1df, 2.6);
sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
sun.shadow.bias = -0.00015;
sun.shadow.normalBias = 0.025;
sun.shadow.radius = 3;
scene.add(sun, sun.target);
let sunDir = new THREE.Vector3(0.55, 0.75, 0.38).normalize();

// --- image-based lighting: real sky HDRI for reflections, ambient light and background
function loadSky() {
  const name = CFG.scene.hdri || "sky_partly_cloudy";
  new RGBELoader().setDataType(THREE.FloatType).load(`${ASSETS}hdri/${name}_1k.hdr`, (tex) => {
    tex.mapping = THREE.EquirectangularReflectionMapping;
    // align the key light with the brightest texel (the sun) in the HDRI
    const { data, width, height } = tex.image;
    let best = -1, bi = 0;
    const stride = data.length / (width * height);
    for (let i = 0; i < width * height; i++) {
      const L = data[i * stride] + data[i * stride + 1] + data[i * stride + 2];
      const v = typeof L === "number" ? L : 0;
      if (v > best) { best = v; bi = i; }
    }
    const u = (bi % width) / width, vv = Math.floor(bi / width) / height;
    const phi = (u - 0.5) * 2 * Math.PI, theta = vv * Math.PI;
    const d = new THREE.Vector3(Math.cos(phi) * Math.sin(theta), Math.cos(theta), Math.sin(phi) * Math.sin(theta)).normalize();
    if (d.y > 0.15) sunDir = d; else sunDir.set(0.55, 0.75, 0.38).normalize();
    scene.environment = pmrem.fromEquirectangular(tex).texture;
    if (CFG.scene.skyBackground !== false) {
      scene.background = tex;
      scene.backgroundBlurriness = 0.0;
      scene.backgroundIntensity = 0.9;
      host.parentElement.style.background = "none";
    }
    placeSun();
  }, undefined, () => console.warn("HDRI unavailable; using studio lighting"));
}
function placeSun() {
  const c = modelBox.getCenter(new THREE.Vector3());
  const r = modelBox.getSize(new THREE.Vector3()).length() * 0.6;
  sun.position.copy(c).addScaledVector(sunDir, r * 2.2);
  sun.target.position.copy(c);
  Object.assign(sun.shadow.camera, { left: -r, right: r, top: r, bottom: -r, near: 0.1, far: r * 6 });
  sun.shadow.camera.updateProjectionMatrix();
}

// --- textured ground fading into atmospheric haze
function makeGround() {
  const R = CFG.scene.groundRadius || 60;
  const kind = CFG.scene.groundTex === undefined ? "grass_lawn" : CFG.scene.groundTex;
  scene.fog = new THREE.Fog(0xc9d3dc, R * 1.6, R * 5.0);
  if (!kind) return;
  const tl = new THREE.TextureLoader();
  const rep = (2 * R) / (CFG.scene.groundTile || 6.0);
  const tx = (f, srgb) => {
    const t = tl.load(`${ASSETS}textures/${kind}/${f}`);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(rep, rep);
    t.anisotropy = 8;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    return t;
  };
  const orm = tx("orm.jpg", false);
  const tints = { grass_lawn: "#5f8040", asphalt: "#55585b", gravel: "#c9c4bb", concrete_slab: "#bdbcb6" };
  const tint = CFG.scene.groundColor || tints[kind];
  const mat = new THREE.MeshStandardMaterial({ map: tx(tint ? "tint.jpg" : "color.jpg", true), normalMap: tx("normal.jpg", false),
    roughnessMap: orm, roughness: 1.0, metalness: 0.0, color: new THREE.Color(tint || "#ffffff") });
  const g = new THREE.Mesh(new THREE.CircleGeometry(R * 6, 96), mat);
  g.rotation.x = -Math.PI / 2;
  g.position.y = (CFG.scene.groundY ?? 0) - 0.03;
  g.receiveShadow = true;
  scene.add(g);
}

// --- post-processing: multisampled HDR target, ground-truth ambient occlusion, tone-mapped output
const rt = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
const composer = new EffectComposer(renderer, rt);
composer.addPass(new RenderPass(scene, camera));
const gtao = new GTAOPass(scene, camera, 1, 1);
gtao.blendIntensity = 0.85;
composer.addPass(gtao);
composer.addPass(new OutputPass());
function aoOn() { const el = document.getElementById("aoToggle"); return !el || el.checked; }

const parts = {};          // name -> Object3D
let modelReady = false;
const bindings = [];       // runtime binding objects
const flows = [];          // particle systems
let META = { anchors: {}, paths: {} };
let modelBox = new THREE.Box3(new THREE.Vector3(-5, 0, -5), new THREE.Vector3(5, 3, 5));

function resize() {
  const w = host.clientWidth, h = host.clientHeight;
  camera.aspect = w / Math.max(h, 1);
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  composer.setPixelRatio(renderer.getPixelRatio());
  composer.setSize(w, h);
}
new ResizeObserver(resize).observe(host);

function setStatus(msg, err = false) {
  const el = $("modelStatus");
  el.textContent = msg;
  el.classList.toggle("err", err);
}

function findParts(spec) {
  const names = Array.isArray(spec) ? spec : [spec];
  const out = [];
  for (const nm of names) {
    if (nm.endsWith("*")) {
      const p = nm.slice(0, -1);
      for (const [k, o] of Object.entries(parts)) if (k.startsWith(p)) out.push(o);
    } else if (parts[nm]) out.push(parts[nm]);
  }
  return out;
}
function meshesOf(obj) {
  const m = [];
  obj.traverse(o => { if (o.isMesh) m.push(o); });
  return m;
}
function ownMaterial(mesh) {
  if (!mesh.userData._ownMat) {
    mesh.material = mesh.material.clone();
    mesh.userData._ownMat = true;
    mesh.userData._baseColor = mesh.material.color.clone();
    mesh.userData._baseEm = mesh.material.emissive ? mesh.material.emissive.clone() : null;
  }
  return mesh.material;
}

async function loadModel() {
  const sc = CFG.scene;
  makeGround();
  loadSky();
  if (sc.grid === true) {
    const g = new THREE.GridHelper((sc.groundRadius || 60) * 2, Math.round((sc.groundRadius || 60) * 2 / (sc.gridStep || 1)), 0x8899aa, 0x8899aa);
    g.material.transparent = true; g.material.opacity = 0.13; g.position.y = (sc.groundY ?? 0) + 0.002;
    scene.add(g);
  }
  try {
    if (sc.meta) META = await (await fetch(sc.meta)).json();
  } catch (e) { console.warn("meta", e); }
  const loader = new GLTFLoader();
  const draco = new DRACOLoader();
  draco.setDecoderPath("https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/libs/draco/gltf/");
  loader.setDRACOLoader(draco);
  setStatus("Loading 3D model…");
  loader.load(sc.glb, (gltf) => {
    gltf.scene.traverse((o) => {
      if (o.name) parts[o.name] = o;
      if (o.isMesh) {
        o.castShadow = o.userData.noShadow ? false : true;
        o.receiveShadow = true;
        if (o.material && o.material.transparent) o.castShadow = false;
      }
    });
    scene.add(gltf.scene);
    modelBox = new THREE.Box3().setFromObject(gltf.scene);
    const size = modelBox.getSize(new THREE.Vector3()), c = modelBox.getCenter(new THREE.Vector3());
    placeSun();
    // AO radius in world units scaled to the plant size
    gtao.updateGtaoMaterial({ radius: Math.min(2.5, Math.max(0.25, size.length() * 0.012)), distanceExponent: 1.5, thickness: 1.0, scale: 1.0 });
    gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 16 });
    setupBindings();
    setupFlows();
    modelReady = true;
    document.body.dataset.model = "ok";
    setStatus("");
    update3D();
  }, (ev) => {
    if (ev.total) setStatus(`Loading 3D model… ${Math.round(ev.loaded / ev.total * 100)} %`);
  }, (err) => {
    console.error(err);
    document.body.dataset.model = "error: " + (err && err.message ? err.message : err);
    setStatus("3D model unavailable · open with run_viewer.cmd (local server)", true);
  });
}

function setupBindings() {
  bindings.length = 0;
  for (const b of (CFG.scene.bindings || [])) {
    if (b.type === "spotlight") {
      const p = anchorPos(b.anchor) || new THREE.Vector3();
      const L = new THREE.SpotLight(b.color || "#ffe2b0", 0, b.distance || 20, THREE.MathUtils.degToRad(b.angle || 60), 0.6, 1.6);
      L.position.copy(p);
      L.target.position.copy(p).add(new THREE.Vector3(0, -1, 0));
      L.castShadow = true;
      L.shadow.mapSize.set(1024, 1024);
      scene.add(L, L.target);
      bindings.push({ ...b, light: L, objs: [], meshes: [] });
      continue;
    }
    const objs = findParts(b.nodes || []);
    if (!objs.length && b.type !== "flow") { console.warn("binding without nodes", b); continue; }
    const meshes = objs.flatMap(meshesOf);
    const rb = { ...b, objs, meshes, base: objs.map(o => ({ rot: o.rotation.clone(), pos: o.position.clone(), scl: o.scale.clone() })), phase: 0 };
    if (["color", "emissive", "opacity", "glow"].includes(b.type)) meshes.forEach(ownMaterial);
    if (b.type === "opacity") meshes.forEach(m => { m.material.transparent = true; m.material.depthWrite = false; });
    bindings.push(rb);
  }
}

function setupFlows() {
  for (const f of flows) scene.remove(f.mesh);
  flows.length = 0;
  for (const b of (CFG.scene.flows || [])) {
    const p = META.paths?.[b.path];
    if (!p || p.pts.length < 2) { console.warn("missing path", b.path); continue; }
    const pts = p.pts.map(v => new THREE.Vector3(...v));
    const curve = new THREE.CatmullRomCurve3(pts, false, "centripetal", 0.0);
    const len = curve.getLength();
    const count = Math.max(6, Math.min(400, Math.round(len / (b.spacing || 0.25))));
    const geo = b.shape === "box" ? new THREE.BoxGeometry(1, 1, 1) : new THREE.SphereGeometry(1, 10, 8);
    const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0x000000, roughness: 0.35, metalness: 0.0, transparent: true, opacity: 0.95 });
    const mesh = new THREE.InstancedMesh(geo, mat, count);
    mesh.castShadow = false;
    mesh.frustumCulled = false;
    scene.add(mesh);
    flows.push({ ...b, curve, len, count, mesh, offset: Math.random(), radius: b.radius || p.radius * 0.55 || 0.02, speed: 0, color: new THREE.Color(1, 1, 1) });
  }
}

const tmpM = new THREE.Matrix4(), tmpQ = new THREE.Quaternion(), tmpS = new THREE.Vector3(), tmpP = new THREE.Vector3();
function animateFlows(dt) {
  for (const f of flows) {
    if (!gateOk(f)) { f.mesh.visible = false; continue; }
    const v = val(f.key);
    const active = Number.isFinite(v) && Math.abs(v) > (f.min ?? 1e-6);
    f.mesh.visible = active && $("flowToggle").checked;
    if (!f.mesh.visible) continue;
    const sp = Math.min(f.maxSpeed || 3, Math.abs(v) * (f.scale || 1));
    f.offset = (f.offset + Math.sign(v) * sp * dt / f.len + 1) % 1;
    if (f.colorKey) {
      const cv = val(f.colorKey);
      const [lo, hi] = f.range || [0, 100];
      f.mesh.material.color.copy(rampColor(f.ramp || "thermal", (cv - lo) / (hi - lo)));
      f.mesh.material.emissive.copy(f.mesh.material.color).multiplyScalar(0.35);
    } else if (f.color) {
      f.mesh.material.color.set(f.color);
    }
    const r = f.radius;
    for (let i = 0; i < f.count; i++) {
      const u = (i / f.count + f.offset) % 1;
      f.curve.getPointAt(u, tmpP);
      tmpS.set(r, r, r);
      tmpM.compose(tmpP, tmpQ, tmpS);
      f.mesh.setMatrixAt(i, tmpM);
    }
    f.mesh.instanceMatrix.needsUpdate = true;
  }
}

function gateOk(o) {
  if (!o.gateKey) return true;
  const g = val(o.gateKey);
  return g >= (o.gateMin ?? -Infinity) && g <= (o.gateMax ?? Infinity);
}
// day/night: scale sun, sky and exposure with the simulated irradiance when the scenario provides it
function updateDaylight() {
  const g = S.data && S.data.ghi ? val("ghi") : NaN;
  if (!Number.isFinite(g)) return;
  const d = Math.max(0.0, Math.min(1, g / 450));
  const twilight = Math.max(0.04, Math.min(1, g / 60));
  sun.intensity = 2.6 * Math.pow(d, 0.7);
  hemi.intensity = 0.06 + 0.2 * twilight;
  scene.backgroundIntensity = 0.06 + 0.84 * twilight;
  renderer.toneMappingExposure = (CFG.scene.exposure ?? 1.0) * (0.42 + 0.58 * twilight);
  if (scene.fog) scene.fog.color.setRGB(0.79 * (0.15 + 0.85 * twilight), 0.83 * (0.15 + 0.85 * twilight), 0.86 * (0.17 + 0.83 * twilight));
}
function update3D() {
  updateDaylight();
  for (const b of bindings) {
    const v = val(b.key);
    const [lo, hi] = b.range || [0, 1];
    const t = Number.isFinite(v) ? Math.max(0, Math.min(1, (v - lo) / (hi - lo))) : 0;
    if (b.type === "color") {
      const c = rampColor(b.ramp || "thermal", t);
      for (const m of b.meshes) {
        m.material.color.copy(m.userData._baseColor).lerp(c, b.mix ?? 0.85);
        if (!Number.isFinite(v)) m.material.color.copy(m.userData._baseColor);
      }
    } else if (b.type === "emissive" || b.type === "glow") {
      const col = new THREE.Color(b.color || "#ffd27a");
      for (const m of b.meshes) {
        m.material.emissive = col.clone().multiplyScalar(t * (b.intensity || 2));
        if (b.type === "glow") m.material.emissiveIntensity = 1;
      }
    } else if (b.type === "opacity") {
      for (const m of b.meshes) { m.material.opacity = (b.min ?? 0) + t * ((b.max ?? 1) - (b.min ?? 0)); m.visible = m.material.opacity > 0.01; }
    } else if (b.type === "visible") {
      const vis = (b.min !== undefined || b.max !== undefined)
        ? (v >= (b.min ?? -Infinity) && v <= (b.max ?? Infinity))
        : (b.invert ? !(v > (b.threshold ?? 0.5)) : v > (b.threshold ?? 0.5));
      for (const o of b.objs) o.visible = vis;
    } else if (b.type === "scale") {
      const ax = b.axis || "y";
      b.objs.forEach((o, i) => { o.scale[ax] = b.base[i].scl[ax] * Math.max(1e-3, (b.from ?? 0) + t * ((b.to ?? 1) - (b.from ?? 0))); });
    } else if (b.type === "rotate") {
      const ax = b.axis || "x";
      const [a0, a1] = b.angles || [0, 90];
      b.objs.forEach((o, i) => { o.rotation[ax] = b.base[i].rot[ax] + THREE.MathUtils.degToRad(a0 + t * (a1 - a0)); });
    } else if (b.type === "spotlight") {
      b.light.intensity = (b.intensity || 60) * t;
    } else if (b.type === "translate") {
      const ax = b.axis || "y";
      b.objs.forEach((o, i) => { o.position[ax] = b.base[i].pos[ax] + (b.from ?? 0) + t * ((b.to ?? 1) - (b.from ?? 0)); });
    }
  }
}
function animateBindings(dt) {
  for (const b of bindings) {
    if (b.type !== "spin") continue;
    const v = val(b.key);
    const w = Number.isFinite(v) ? v * (b.scale || 1) : 0;
    const ax = b.axis || "y";
    b.phase += Math.min(w, b.maxRate || 40) * dt;
    b.objs.forEach((o, i) => { o.rotation[ax] = b.base[i].rot[ax] + b.phase; });
  }
}

// ---- tags and state-point markers
const tagsEl = $("tags");
const tags = [];
function anchorPos(a) {
  if (Array.isArray(a)) return new THREE.Vector3(...a);
  if (META.anchors && META.anchors[a]) return new THREE.Vector3(...META.anchors[a]);
  const o = parts[a];
  if (o) {
    const b = new THREE.Box3().setFromObject(o);
    return new THREE.Vector3((b.min.x + b.max.x) / 2, b.max.y, (b.min.z + b.max.z) / 2);
  }
  return null;
}
function buildTags() {
  tagsEl.innerHTML = "";
  tags.length = 0;
  for (const t of (S.sc?.tags || CFG.scene.tags || [])) {
    const el = document.createElement("div");
    el.className = "tag";
    el.innerHTML = `<b>${t.label}</b><span class="m">–</span>`;
    tagsEl.appendChild(el);
    tags.push({ ...t, el, kind: "tag" });
  }
  for (const sp of (S.sc?.statePoints || [])) {
    const anchor = `SP_${sp.id}`;
    if (!META.anchors || !META.anchors[anchor]) continue;
    const el = document.createElement("div");
    el.className = "spm";
    el.textContent = sp.id;
    el.dataset.sid = sp.id;
    el.addEventListener("pointerenter", (e) => showSpTip(sp, e));
    el.addEventListener("pointerleave", hideTip);
    tagsEl.appendChild(el);
    tags.push({ anchor, el, kind: "sp", sp });
  }
}
function tagText(t) {
  if (t.fmt) {
    return t.fmt.replace(/\{([\w.]+)(?:\|(\d))?\}/g, (_, k, d) => fmt(val(k), d === undefined ? chMeta(k).dec : +d));
  }
  return (t.keys || []).map(k => `${fmt(val(k), chMeta(k).dec)} ${chMeta(k).unit}`).join(" · ");
}
function spClass(sp) {
  const x = val(`${sp.id}_x`), T = val(`${sp.id}_T`);
  if (Number.isFinite(x) && x > 0 && x < 1) return "mid";
  if (Number.isFinite(x) && x <= 0) return "liq";
  return T > 45 ? "hot" : "cold";
}
const tv = new THREE.Vector3();
function positionTags() {
  const w = host.clientWidth, h = host.clientHeight;
  const show = $("labelsToggle").checked, showSp = $("spToggle").checked;
  const placed = [];
  for (const t of tags) {
    const visible = (t.kind === "sp" ? showSp : show) && gateOk(t);
    const p = anchorPos(t.anchor || t.pos);
    if (!visible || !p) { t.el.style.display = "none"; continue; }
    tv.copy(p).project(camera);
    if (tv.z < -1 || tv.z > 1 || Math.abs(tv.x) > 1.05 || Math.abs(tv.y) > 1.05) { t.el.style.display = "none"; continue; }
    t.el.style.display = "";
    let x = (tv.x * 0.5 + 0.5) * w, y = (-tv.y * 0.5 + 0.5) * h;
    if (t.kind === "tag") {
      const ew = t.el.offsetWidth || 120, eh = t.el.offsetHeight || 32;
      for (let n = 0; n < 8; n++) {
        const o = placed.find(q => Math.abs(q.x - x) < (q.w + ew) / 2 + 4 && Math.abs(q.y - y) < eh + 4);
        if (!o) break;
        y = o.y - eh - 6;
      }
      placed.push({ x, y, w: ew });
      t.el.querySelector(".m").textContent = tagText(t);
      const lim = t.alertKey ? val(t.alertKey) > t.alertAbove : false;
      t.el.classList.toggle("alert", !!lim);
    } else {
      t.el.className = "spm " + spClass(t.sp) + (t.el.classList.contains("hl") ? " hl" : "");
    }
    t.el.style.left = `${x}px`;
    t.el.style.top = `${y}px`;
  }
}
const tip = $("tip");
function showSpTip(sp, e) {
  const g = (f, d) => fmt(val(`${sp.id}_${f}`), d);
  tip.innerHTML = `<b>${sp.id} · ${sp.name}</b>${sp.fluid} · ${sp.loop}<br>T ${g("T", 1)} °C · P ${g("P", 2)} bar<br>h ${g("h", 1)} kJ/kg · s ${g("s", 4)} kJ/kgK<br>x ${g("x", 3)} · ṁ ${g("m", 4)} kg/s`;
  const r = host.getBoundingClientRect();
  tip.style.display = "block";
  tip.style.left = `${e.clientX - r.left + 14}px`;
  tip.style.top = `${e.clientY - r.top + 10}px`;
}
function hideTip() { tip.style.display = "none"; }

// ---- picking for component specs
const ray = new THREE.Raycaster();
const ndc = new THREE.Vector2();
let downAt = null;
renderer.domElement.addEventListener("pointerdown", e => { downAt = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener("pointerup", e => {
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 4) return;
  const r = renderer.domElement.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObjects(scene.children, true).find(h => h.object.isMesh && !h.object.isInstancedMesh);
  let o = hit?.object;
  while (o && !(o.userData && (o.userData.spec || o.userData.title))) o = o.parent;
  const box = $("inspect");
  if (!o) { box.style.display = "none"; return; }
  const ud = o.userData;
  const rows = Object.entries(ud).filter(([k]) => !["spec", "title", "name", "noShadow"].includes(k) && !k.startsWith("_"));
  box.innerHTML = `<button class="x" aria-label="Close">×</button><h3>${ud.title || o.name.replace(/_/g, " ")}</h3>
    <p class="note" style="margin:0 0 6px">${ud.spec || ""}</p><dl>${rows.map(([k, v]) => `<dt>${k.replace(/_/g, " ")}</dt><dd>${v}</dd>`).join("")}</dl>
    ${ud.live ? `<h2>Live</h2><dl>${ud.live.split(",").map(k => `<dt>${chMeta(k).label}</dt><dd>${fmt(val(k), chMeta(k).dec)} ${chMeta(k).unit}</dd>`).join("")}</dl>` : ""}`;
  box.style.display = "block";
  box.querySelector(".x").onclick = () => { box.style.display = "none"; };
});

// ---- camera views
function setView(kind) {
  const c = modelBox.getCenter(new THREE.Vector3());
  const r = modelBox.getSize(new THREE.Vector3()).length() * 0.62;
  const v = CFG.scene.camera;
  if (kind === "reset" && v) {
    camera.position.set(...v.pos);
    controls.target.set(...v.target);
  } else if (kind === "top") {
    controls.target.copy(c);
    camera.position.copy(c).add(new THREE.Vector3(0.001, r * 1.7, 0.001));
  } else if (kind === "front") {
    controls.target.copy(c);
    camera.position.copy(c).add(new THREE.Vector3(0, r * 0.35, r * 1.55));
  } else {
    controls.target.copy(c);
    camera.position.copy(c).add(new THREE.Vector3(r * 1.1, r * 0.75, r * 1.2));
  }
  controls.update();
}
$("topView").onclick = () => setView("top");
$("frontView").onclick = () => setView("front");
$("resetView").onclick = () => setView("reset");

// ---------------------------------------------------------------- data
async function loadScenario(key) {
  setStatus("Loading simulation results…");
  if (!S.cache[key]) {
    const [man, buf] = await Promise.all([
      fetch(`viewer_data/${key}.json`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
      fetch(`viewer_data/${key}.bin`).then(r => { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); }),
    ]);
    const all = new Float32Array(buf);
    const data = {}, meta = {};
    man.channels.forEach((c, j) => { data[c.key] = all.subarray(j * man.n, (j + 1) * man.n); meta[c.key] = c; });
    S.cache[key] = { man, data, meta };
  }
  const { man, data, meta } = S.cache[key];
  const first = S.sc === null;
  S.key = key; S.sc = man; S.data = data; S.meta = meta; S.n = man.n;
  const qt = new URLSearchParams(location.search).get("t");
  if (first) S.k = qt !== null ? +qt : (man.start ?? 0);
  S.k = Math.max(0, Math.min(S.k, S.n - 1)); S.kf = S.k;
  S.pinned = (man.chartDefault || man.channels.slice(0, 4).map(c => c.key)).slice();
  if (S.win[1] <= S.win[0] || S.win[1] > S.n) S.win = [0, S.n];
  $("scenarioBadge").textContent = man.badge || key;
  $("provenance").textContent = man.source || "";
  $("sensorNote").textContent = man.note || "";
  buildLegend(); buildKpis(); buildSensors(); buildLedger(); buildSpTable(); buildDiagrams(); buildVars(); buildTags();
  setStatus(modelReady ? "" : "Loading 3D model…");
  refresh(true);
}

// ---------------------------------------------------------------- panels
function buildLegend() {
  const L = S.sc.legend || CFG.scene.legend, el = $("legend");
  if (!L) { el.style.display = "none"; return; }
  el.style.display = "grid";
  el.innerHTML = `<div>${L.title}</div><div class="ramp" style="background:linear-gradient(90deg,${L.gradient})"></div>
  <div class="ramp-ticks">${L.ticks.map(t => `<span style="left:${t.pct}%">${t.label}</span>`).join("")}</div>`;
}
function buildKpis() {
  const el = $("kpis");
  const groups = {};
  for (const k of (S.sc.kpis || [])) (groups[k.group] ||= []).push(k);
  el.innerHTML = Object.entries(groups).map(([g, ks]) => `<h2>${g}</h2><div class="kgrid">${ks.map(k =>
    `<div class="kpi${k.label.startsWith("  ") ? " sub" : ""}" title="${k.note || ""}"><div class="l">${k.label.trim()}</div><div class="v">${fmt(k.value, k.dec)}<small>${k.unit}</small></div></div>`).join("")}</div>`).join("");
}
function buildSensors() {
  $("sens").innerHTML = (S.sc.sensors || []).map((s, i) => {
    const m = chMeta(s.key);
    return `<tr><td class="n">${s.label || m.label}</td><td class="m" id="sv${i}"></td><td id="sr${i}"></td><td id="sd${i}"></td></tr>`;
  }).join("");
  $("sensHead").style.display = (S.sc.sensors || []).some(s => s.refKey || s.ref !== undefined) ? "" : "none";
}
function updateSensors() {
  (S.sc.sensors || []).forEach((s, i) => {
    const m = chMeta(s.key), v = val(s.key);
    const ref = s.refKey ? val(s.refKey) : s.ref;
    const c = $(`sv${i}`);
    c.textContent = `${fmt(v, m.dec)} ${m.unit}`;
    c.className = (s.limit !== undefined && v > s.limit) || (s.lower !== undefined && v < s.lower) ? "bad" : "m";
    $(`sr${i}`).textContent = ref !== undefined && ref !== null ? fmt(ref, m.dec) : "";
    $(`sd${i}`).textContent = ref !== undefined && ref !== null && Number.isFinite(v) ? (v - ref >= 0 ? "+" : "") + fmt(v - ref, m.dec) : "";
  });
  $("cmds").innerHTML = (S.sc.cmds || []).map(c => {
    const m = chMeta(c.key);
    return `<div><span>${c.label || m.label}</span><b>${fmt(val(c.key), c.dec ?? m.dec)}</b> ${c.unit ?? m.unit}</div>`;
  }).join("");
}
function buildLedger() {
  $("ledgerTitle").textContent = S.sc.ledgerTitle || "Energy flows";
  $("ledger").innerHTML = (S.sc.ledger || []).map((l, i) =>
    `<div class="lrow"><span>${l.label || chMeta(l.key).label}</span><div class="lbar"><i id="lb${i}" style="background:${l.color || "var(--heat)"}"></i></div><span class="v" id="lv${i}"></span></div>`).join("");
}
function updateLedger() {
  (S.sc.ledger || []).forEach((l, i) => {
    const v = val(l.key), m = chMeta(l.key);
    const max = l.max || m.max || 1;
    $(`lb${i}`).style.width = `${Math.max(0, Math.min(100, Math.abs(v) / max * 100))}%`;
    $(`lv${i}`).textContent = `${fmt(v, l.dec ?? m.dec)} ${m.unit}`;
  });
}
function buildSpTable() {
  const sps = S.sc.statePoints || [];
  $("spPane").style.display = sps.length ? "" : "none";
  $("tabSp").style.display = sps.length ? "" : "none";
  const loops = {};
  for (const sp of sps) (loops[sp.loop] ||= []).push(sp);
  $("spTables").innerHTML = Object.entries(loops).map(([loop, list]) => `<h2>${loop} · ${list[0].fluid}</h2>
    <table><thead><tr><th>Point</th><th>T °C</th><th>P bar</th><th>h kJ/kg</th><th>s kJ/kgK</th><th>x</th><th>ṁ kg/s</th></tr></thead>
    <tbody>${list.map(sp => `<tr class="sp" data-sid="${sp.id}"><td class="n"><span class="sid">${sp.id}</span>${sp.name}</td>
    ${["T", "P", "h", "s", "x", "m"].map(f => `<td id="sp_${sp.id}_${f}"></td>`).join("")}</tr>`).join("")}</tbody></table>`).join("");
  document.querySelectorAll("tr.sp").forEach(tr => {
    tr.addEventListener("pointerenter", () => document.querySelectorAll(`.spm[data-sid="${tr.dataset.sid}"]`).forEach(e => e.classList.add("hl")));
    tr.addEventListener("pointerleave", () => document.querySelectorAll(".spm.hl").forEach(e => e.classList.remove("hl")));
  });
}
function updateSpTable() {
  const dec = { T: 1, P: 2, h: 1, s: 4, x: 3, m: 4 };
  for (const sp of (S.sc.statePoints || [])) {
    for (const f of ["T", "P", "h", "s", "x", "m"]) {
      const c = $(`sp_${sp.id}_${f}`);
      if (c) c.textContent = S.data[`${sp.id}_${f}`] ? fmt(val(`${sp.id}_${f}`), dec[f]) : "";
    }
  }
}

// ---- thermodynamic and profile diagrams
function buildDiagrams() {
  const ds = S.sc.diagrams || [];
  $("tabDiag").style.display = ds.length ? "" : "none";
  $("diagPane").innerHTML = ds.map((d, i) => `<h2>${d.title}</h2><canvas class="diag${d.type === "bars" || d.type === "profile" ? " short" : ""}" id="dg${i}"></canvas>`).join("")
    + `<p class="note">Diagrams show the hourly mean operating state at the cursor; faint traces are the preceding 24 hours.</p>`;
}
function canvasCtx(cv) {
  const r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  if (cv.width !== Math.round(r.width * dpr) || cv.height !== Math.round(r.height * dpr)) {
    cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr);
  }
  const c = cv.getContext("2d");
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.clearRect(0, 0, r.width, r.height);
  return [c, r.width, r.height];
}
function niceTicks(lo, hi, n = 5) {
  const span = hi - lo, step0 = span / n, mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map(s => s * mag).find(s => span / s <= n) || mag * 10;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(10));
  return out;
}
function drawDiagrams() {
  const ds = S.sc.diagrams || [];
  const st = css(), ink = st.getPropertyValue("--ink"), mut = st.getPropertyValue("--muted"), line = st.getPropertyValue("--line");
  ds.forEach((d, i) => {
    const cv = $(`dg${i}`);
    if (!cv) return;
    const [c, W, H] = canvasCtx(cv);
    c.font = "10px IBM Plex Mono, monospace";
    if (d.type === "ph" || d.type === "ts") {
      const ph = d.type === "ph";
      const dome = d.dome;
      const X = ph ? [...dome.hl, ...dome.hv] : [...dome.sl, ...dome.sv];
      const Y = ph ? dome.P : dome.T;
      const ids = [...new Set(d.paths.flat())];
      const xs = ids.map(id => val(`${id}_${ph ? "h" : "s"}`)).filter(Number.isFinite);
      const ys = ids.map(id => val(`${id}_${ph ? "P" : "T"}`)).filter(Number.isFinite);
      let x0 = Math.min(...X, ...xs), x1 = Math.max(...X, ...xs);
      let y0 = Math.min(...Y, ...ys), y1 = Math.max(...Y, ...ys);
      const padx = (x1 - x0) * 0.06; x0 -= padx; x1 += padx;
      if (ph) { y0 = Math.max(y0 * 0.7, 1e-3); y1 *= 1.4; } else { const p = (y1 - y0) * 0.08; y0 -= p; y1 += p; }
      const L = 44, R = 10, T = 8, B = 26;
      const fx = v => L + (v - x0) / (x1 - x0) * (W - L - R);
      const fy = ph ? v => T + (1 - (Math.log10(v) - Math.log10(y0)) / (Math.log10(y1) - Math.log10(y0))) * (H - T - B)
        : v => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
      c.strokeStyle = line; c.lineWidth = 1; c.fillStyle = mut;
      for (const t of niceTicks(x0, x1, 6)) { c.beginPath(); c.moveTo(fx(t), T); c.lineTo(fx(t), H - B); c.stroke(); c.textAlign = "center"; c.fillText(t, fx(t), H - B + 12); }
      const yt = ph ? [0.5, 1, 2, 5, 10, 20, 50, 100, 200].filter(v => v >= y0 && v <= y1) : niceTicks(y0, y1, 5);
      for (const t of yt) { c.beginPath(); c.moveTo(L, fy(t)); c.lineTo(W - R, fy(t)); c.stroke(); c.textAlign = "right"; c.fillText(t, L - 4, fy(t) + 3); }
      c.textAlign = "center"; c.fillText(ph ? "h  kJ/kg" : "s  kJ/(kg·K)", (L + W - R) / 2, H - 3);
      c.save(); c.translate(10, (T + H - B) / 2); c.rotate(-Math.PI / 2); c.fillText(ph ? "P  bar (log)" : "T  °C", 0, 0); c.restore();
      // dome
      c.strokeStyle = mut; c.lineWidth = 1.4; c.beginPath();
      const lx = ph ? dome.hl : dome.sl, vx = ph ? dome.hv : dome.sv;
      lx.forEach((v, j) => j ? c.lineTo(fx(v), fy(Y[j])) : c.moveTo(fx(v), fy(Y[j])));
      for (let j = vx.length - 1; j >= 0; j--) c.lineTo(fx(vx[j]), fy(Y[j]));
      c.stroke();
      // trail
      const draw = (k, alpha, width) => {
        c.globalAlpha = alpha; c.lineWidth = width;
        for (const path of d.paths) {
          c.beginPath();
          let ok = false;
          path.forEach((id, j) => {
            const x = val(`${id}_${ph ? "h" : "s"}`, k), y = val(`${id}_${ph ? "P" : "T"}`, k);
            if (!Number.isFinite(x) || !Number.isFinite(y) || (ph && y <= 0)) return;
            if (!ok) { c.moveTo(fx(x), fy(y)); ok = true; } else c.lineTo(fx(x), fy(y));
          });
          c.stroke();
        }
        c.globalAlpha = 1;
      };
      c.strokeStyle = st.getPropertyValue("--model");
      for (let j = 24; j >= 1; j -= 3) if (S.k - j >= 0) draw(S.k - j, 0.10, 1);
      c.strokeStyle = st.getPropertyValue("--heat");
      draw(S.k, 1, 2);
      for (const id of ids) {
        const x = val(`${id}_${ph ? "h" : "s"}`), y = val(`${id}_${ph ? "P" : "T"}`);
        if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
        c.fillStyle = ink; c.beginPath(); c.arc(fx(x), fy(y), 3, 0, 7); c.fill();
        c.fillStyle = mut; c.textAlign = "left"; c.fillText(id, fx(x) + 4, fy(y) - 4);
      }
    } else if (d.type === "profile") {
      const L = 40, R = 10, T = 8, B = 22;
      const all = d.series.flatMap(s => s.keys.map(k => val(k))).filter(Number.isFinite);
      let x0 = Math.min(...all), x1 = Math.max(...all);
      if (!(x1 > x0)) { x0 -= 1; x1 += 1; }
      const p = (x1 - x0) * 0.1; x0 -= p; x1 += p;
      const fx = v => L + (v - x0) / (x1 - x0) * (W - L - R);
      c.strokeStyle = line; c.fillStyle = mut;
      for (const t of niceTicks(x0, x1, 6)) { c.beginPath(); c.moveTo(fx(t), T); c.lineTo(fx(t), H - B); c.stroke(); c.textAlign = "center"; c.fillText(t, fx(t), H - B + 12); }
      c.textAlign = "left"; c.fillText("top", 4, T + 8); c.fillText("base", 4, H - B);
      c.textAlign = "center"; c.fillText(d.xLabel || "", (L + W - R) / 2, H - 2);
      d.series.forEach((s, si) => {
        const n = s.keys.length;
        c.strokeStyle = s.color; c.fillStyle = s.color; c.lineWidth = 2; c.beginPath();
        s.keys.forEach((k, j) => {
          const y = T + (j + 0.5) / n * (H - T - B), x = fx(val(k));
          j ? c.lineTo(x, y) : c.moveTo(x, y);
        });
        c.stroke();
        c.textAlign = "right"; c.fillText(s.label, W - R, T + 10 + si * 12);
      });
    } else if (d.type === "bars") {
      const items = d.items.map(it => ({ ...it, v: val(it.key) }));
      const max = Math.max(1e-9, ...items.map(it => Math.abs(it.v) || 0));
      const L = 78, R = 46, rowH = (H - 6) / items.length;
      items.forEach((it, j) => {
        const y = 3 + j * rowH;
        c.fillStyle = mut; c.textAlign = "right"; c.fillText(it.label, L - 6, y + rowH * 0.65);
        c.fillStyle = it.color || st.getPropertyValue("--heat");
        c.fillRect(L, y + rowH * 0.2, Math.max(0, (Math.abs(it.v) || 0) / max * (W - L - R)), rowH * 0.6);
        c.fillStyle = ink; c.textAlign = "left";
        c.fillText(fmt(it.v, 2), L + Math.max(0, (Math.abs(it.v) || 0) / max * (W - L - R)) + 4, y + rowH * 0.65);
      });
    }
  });
}

// ---- variable browser
function buildVars() {
  const groups = {};
  for (const c of S.sc.channels) (groups[c.group] ||= []).push(c);
  $("varCount").textContent = `${S.sc.channels.length} channels · ${S.n.toLocaleString()} samples each`;
  $("vars").innerHTML = Object.entries(groups).map(([g, cs]) => `<details class="vgroup" ${g.startsWith("State") ? "" : "open"}><summary><span>${g}</span><span>${cs.length}</span></summary>
    ${cs.map(c => `<div class="vrow" data-key="${c.key}" data-search="${(c.label + " " + c.key + " " + g).toLowerCase()}"><input type="checkbox" ${S.pinned.includes(c.key) ? "checked" : ""} title="Plot on timeline">
    <span class="lab" title="${c.label} [${c.key}]">${c.label}</span><span class="val" id="vv_${c.key}"></span></div>`).join("")}</details>`).join("");
  $("vars").querySelectorAll(".vrow").forEach(row => {
    const key = row.dataset.key;
    row.querySelector("input").addEventListener("change", e => {
      if (e.target.checked) { if (!S.pinned.includes(key)) S.pinned.push(key); } else S.pinned = S.pinned.filter(x => x !== key);
      drawChart();
    });
    row.querySelector(".lab").addEventListener("click", () => { S.focus = key; drawFocus(); });
  });
}
$("vsearch").addEventListener("input", e => {
  const q = e.target.value.trim().toLowerCase();
  $("vars").querySelectorAll(".vrow").forEach(r => { r.style.display = !q || r.dataset.search.includes(q) ? "" : "none"; });
  if (q) $("vars").querySelectorAll("details").forEach(d => { d.open = true; });
});
function updateVars() {
  for (const c of S.sc.channels) {
    const el = document.getElementById(`vv_${c.key}`);
    if (el && el.offsetParent) el.innerHTML = `${fmt(val(c.key), c.dec)} <small>${c.unit}</small>`;
  }
}
function drawFocus() {
  const box = $("vfocus");
  if (!S.focus || !S.data[S.focus]) { box.classList.remove("on"); return; }
  box.classList.add("on");
  const m = chMeta(S.focus), a = S.data[S.focus];
  let mn = Infinity, mx = -Infinity, sum = 0, cnt = 0;
  for (const v of a) if (Number.isFinite(v)) { mn = Math.min(mn, v); mx = Math.max(mx, v); sum += v; cnt++; }
  const isPower = ["kW", "W", "MW", "kWh"].includes(m.unit) && S.sc.timeUnit !== "years";
  const integ = isPower ? sum * S.sc.dt / 3600 / (m.unit === "W" ? 1e3 : 1) : null;
  $("vfTitle").textContent = `${m.label} [${m.unit}]`;
  $("vfStats").innerHTML = `<div><span>min</span>${fmt(mn, m.dec)}</div><div><span>mean</span>${fmt(sum / cnt, m.dec)}</div><div><span>max</span>${fmt(mx, m.dec)}</div>
    <div><span>${isPower ? (m.unit === "MW" ? "MWh/yr" : "kWh/yr") : "samples"}</span>${isPower ? fmt(integ, 0) : cnt}</div>`;
  // monthly min/mean/max bars
  const cv = $("monthly");
  const [c, W, H] = canvasCtx(cv);
  if (S.sc.timeUnit === "years") return;
  const t0 = Date.parse(S.sc.t0);
  const mm = Array.from({ length: 12 }, () => ({ mn: Infinity, mx: -Infinity, s: 0, n: 0 }));
  for (let i = 0; i < S.n; i++) {
    const v = a[i];
    if (!Number.isFinite(v)) continue;
    const mo = new Date(t0 + i * S.sc.dt * 1000).getUTCMonth();
    const q = mm[mo]; q.mn = Math.min(q.mn, v); q.mx = Math.max(q.mx, v); q.s += v; q.n++;
  }
  const lo = Math.min(0, mn), hi = Math.max(mx, 1e-9);
  const st = css(), bw = (W - 30) / 12;
  const fy = v => 6 + (1 - (v - lo) / (hi - lo || 1)) * (H - 22);
  c.font = "10px IBM Plex Mono, monospace";
  mm.forEach((q, j) => {
    const x = 24 + j * bw;
    if (!q.n) return;
    c.fillStyle = st.getPropertyValue("--line");
    c.fillRect(x + bw * 0.3, fy(q.mx), bw * 0.4, Math.max(1, fy(q.mn) - fy(q.mx)));
    c.fillStyle = st.getPropertyValue("--model");
    c.fillRect(x + bw * 0.2, fy(q.s / q.n) - 1.5, bw * 0.6, 3);
    c.fillStyle = st.getPropertyValue("--muted"); c.textAlign = "center";
    c.fillText(MONTHS[j][0], x + bw / 2, H - 4);
  });
  c.textAlign = "right"; c.fillText(fmt(hi, 0), 22, 12); c.fillText(fmt(lo, 0), 22, H - 16);
}

// ---------------------------------------------------------------- timeline chart
const chart = $("chart"), ov = $("overview");
const LANE_COLORS = ["#c2410c", "#2f5bd3", "#15803d", "#7c3aed", "#b45309", "#0e7490", "#be123c", "#4d7c0f"];
const PAD_L = 150, PAD_R = 64;
function drawChart() {
  if (!S.sc) return;
  const [c, W, H] = canvasCtx(chart);
  const st = css(), mut = st.getPropertyValue("--muted"), ink = st.getPropertyValue("--ink");
  const keys = S.pinned.filter(k => S.data[k]).slice(0, 8);
  const [i0, i1] = S.win;
  const span = i1 - i0;
  const plotW = W - PAD_L - PAD_R, laneH = (H - 16) / Math.max(1, keys.length);
  c.font = "10.5px IBM Plex Mono, monospace";
  // time ticks
  c.fillStyle = mut; c.strokeStyle = "rgba(128,140,150,.18)"; c.textAlign = "center";
  const ticks = timeTicks(i0, i1);
  for (const [i, lab] of ticks) {
    const x = PAD_L + (i - i0) / span * plotW;
    c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H - 14); c.stroke();
    c.fillText(lab, x, H - 3);
  }
  keys.forEach((key, lane) => {
    const a = S.data[key], m = chMeta(key), col = LANE_COLORS[lane % LANE_COLORS.length];
    const top = lane * laneH;
    let lo = Infinity, hi = -Infinity;
    for (let i = i0; i < i1; i++) { const v = a[i]; if (Number.isFinite(v)) { if (v < lo) lo = v; if (v > hi) hi = v; } }
    if (!Number.isFinite(lo)) { lo = 0; hi = 1; }
    if (hi - lo < 1e-9) { lo -= 0.5; hi += 0.5; }
    const fy = v => top + laneH - 4 - (laneH - 10) * (v - lo) / (hi - lo);
    c.strokeStyle = "rgba(128,140,150,.25)";
    c.beginPath(); c.moveTo(PAD_L, top + laneH); c.lineTo(W - PAD_R, top + laneH); c.stroke();
    c.textAlign = "left"; c.fillStyle = col;
    c.fillText(clip(m.label, 22), 4, top + 13);
    c.fillStyle = mut;
    c.fillText(`${fmt(lo, m.dec)}–${fmt(hi, m.dec)} ${m.unit}`.slice(0, 24), 4, top + 26);
    c.fillStyle = col; c.font = "600 11px IBM Plex Mono, monospace";
    c.fillText(fmt(a[S.k], m.dec), W - PAD_R + 6, top + laneH / 2 + 4);
    c.font = "10.5px IBM Plex Mono, monospace";
    // min/max envelope per pixel column + mean line
    const cols = Math.max(1, Math.floor(plotW));
    const per = span / cols;
    c.fillStyle = col + "33"; c.strokeStyle = col; c.lineWidth = 1.4;
    const mean = [];
    for (let px = 0; px < cols; px++) {
      const a0 = Math.floor(i0 + px * per), a1 = Math.max(a0 + 1, Math.floor(i0 + (px + 1) * per));
      let mn = Infinity, mx = -Infinity, s = 0, n = 0;
      for (let i = a0; i < a1 && i < i1; i++) { const v = a[i]; if (Number.isFinite(v)) { mn = Math.min(mn, v); mx = Math.max(mx, v); s += v; n++; } }
      if (!n) { mean.push(null); continue; }
      if (per > 1.5) c.fillRect(PAD_L + px, fy(mx), 1, Math.max(1, fy(mn) - fy(mx)));
      mean.push(fy(s / n));
    }
    c.beginPath();
    let pen = false;
    mean.forEach((y, px) => { if (y === null) { pen = false; return; } if (!pen) { c.moveTo(PAD_L + px, y); pen = true; } else c.lineTo(PAD_L + px, y); });
    c.stroke();
  });
  if (S.k >= i0 && S.k < i1) {
    const x = PAD_L + (S.kf - i0) / span * plotW;
    c.strokeStyle = ink; c.lineWidth = 1.2; c.setLineDash([4, 3]);
    c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H - 14); c.stroke(); c.setLineDash([]);
  }
  drawOverview();
  $("winInfo").textContent = `${timeOf(i0).short} → ${timeOf(Math.max(i0, i1 - 1)).short}`;
}
function clip(s, n) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }
function timeTicks(i0, i1) {
  const out = [];
  if (S.sc.timeUnit === "years") {
    const step = Math.max(1, Math.ceil((i1 - i0) / 8));
    for (let i = i0; i < i1; i += step) out.push([i, `Y${Math.round(S.sc.t0 + i * S.sc.dt)}`]);
    return out;
  }
  const hours = (i1 - i0) * S.sc.dt / 3600;
  const t0 = Date.parse(S.sc.t0);
  const stepH = hours > 24 * 60 ? null : hours > 24 * 14 ? 24 * 7 : hours > 24 * 3 ? 24 : hours > 24 ? 6 : 3;
  for (let i = i0; i < i1; i++) {
    const d = new Date(t0 + i * S.sc.dt * 1000);
    const h = d.getUTCHours(), m = d.getUTCMinutes();
    if (m !== 0) continue;
    if (stepH === null) { if (d.getUTCDate() === 1 && h === 0) out.push([i, MONTHS[d.getUTCMonth()]]); }
    else if (stepH >= 24) { if (h === 0 && (stepH === 24 || d.getUTCDay() === 1)) out.push([i, `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`]); }
    else if (h % stepH === 0) out.push([i, h === 0 ? `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}` : `${String(h).padStart(2, "0")}:00`]);
  }
  return out;
}
function drawOverview() {
  const [c, W, H] = canvasCtx(ov);
  const st = css();
  const key = S.pinned.find(k => S.data[k]);
  c.fillStyle = st.getPropertyValue("--panel-2"); c.fillRect(PAD_L, 0, W - PAD_L - PAD_R, H);
  c.fillStyle = st.getPropertyValue("--muted"); c.font = "10px IBM Plex Mono, monospace"; c.textAlign = "left";
  c.fillText("full period · drag window", 4, H / 2 + 3);
  if (key) {
    const a = S.data[key], m = chMeta(key);
    const lo = m.min, hi = m.max === m.min ? m.min + 1 : m.max;
    const plotW = W - PAD_L - PAD_R, per = S.n / plotW;
    c.fillStyle = st.getPropertyValue("--faint");
    for (let px = 0; px < plotW; px++) {
      let mn = Infinity, mx = -Infinity;
      for (let i = Math.floor(px * per); i < Math.floor((px + 1) * per); i++) { const v = a[i]; if (Number.isFinite(v)) { mn = Math.min(mn, v); mx = Math.max(mx, v); } }
      if (mn === Infinity) continue;
      const y1 = H - 2 - (H - 4) * (mx - lo) / (hi - lo), y2 = H - 2 - (H - 4) * (mn - lo) / (hi - lo);
      c.fillRect(PAD_L + px, y1, 1, Math.max(1, y2 - y1));
    }
  }
  const plotW = W - PAD_L - PAD_R;
  const x0 = PAD_L + S.win[0] / S.n * plotW, x1 = PAD_L + S.win[1] / S.n * plotW;
  c.fillStyle = st.getPropertyValue("--model") + "22"; c.strokeStyle = st.getPropertyValue("--model");
  c.fillRect(x0, 0, Math.max(2, x1 - x0), H); c.strokeRect(x0 + 0.5, 0.5, Math.max(2, x1 - x0) - 1, H - 1);
  const xc = PAD_L + S.kf / S.n * plotW;
  c.fillStyle = st.getPropertyValue("--ink"); c.fillRect(xc - 0.5, 0, 1.5, H);
}
function setWindow(len, center = S.k) {
  len = Math.min(S.n, Math.max(12, Math.round(len)));
  let a = Math.round(center - len / 2);
  a = Math.max(0, Math.min(S.n - len, a));
  S.win = [a, a + len];
  drawChart();
}
document.querySelectorAll("[data-win]").forEach(b => b.addEventListener("click", () => {
  const h = +b.dataset.win;
  const len = h === 0 ? S.n : h * 3600 / S.sc.dt;
  setWindow(len);
  document.querySelectorAll("[data-win]").forEach(x => x.classList.toggle("on", x === b));
}));
function seekChart(e) {
  const r = chart.getBoundingClientRect();
  const f = (e.clientX - r.left - PAD_L) / (r.width - PAD_L - PAD_R);
  seek(S.win[0] + Math.max(0, Math.min(1, f)) * (S.win[1] - S.win[0] - 1));
}
let dragChart = false;
chart.addEventListener("pointerdown", e => { dragChart = true; chart.setPointerCapture(e.pointerId); seekChart(e); });
chart.addEventListener("pointermove", e => { if (dragChart) seekChart(e); });
chart.addEventListener("pointerup", () => { dragChart = false; });
chart.addEventListener("wheel", e => {
  e.preventDefault();
  const r = chart.getBoundingClientRect();
  const f = Math.max(0, Math.min(1, (e.clientX - r.left - PAD_L) / (r.width - PAD_L - PAD_R)));
  const len = S.win[1] - S.win[0];
  const nl = Math.min(S.n, Math.max(12, len * (e.deltaY > 0 ? 1.25 : 0.8)));
  const anchor = S.win[0] + f * len;
  let a = Math.round(anchor - f * nl);
  a = Math.max(0, Math.min(S.n - nl, a));
  S.win = [a, Math.round(a + nl)];
  drawChart();
}, { passive: false });
let dragOv = null;
ov.addEventListener("pointerdown", e => {
  ov.setPointerCapture(e.pointerId);
  const r = ov.getBoundingClientRect(), pw = r.width - PAD_L - PAD_R;
  const i = (e.clientX - r.left - PAD_L) / pw * S.n;
  if (i < S.win[0] || i > S.win[1]) { const len = S.win[1] - S.win[0]; setWindow(len, i); }
  dragOv = { x: e.clientX, w0: S.win.slice(), pw };
});
ov.addEventListener("pointermove", e => {
  if (!dragOv) return;
  const d = Math.round((e.clientX - dragOv.x) / dragOv.pw * S.n), len = dragOv.w0[1] - dragOv.w0[0];
  const a = Math.max(0, Math.min(S.n - len, dragOv.w0[0] + d));
  S.win = [a, a + len];
  drawChart();
});
ov.addEventListener("pointerup", () => { dragOv = null; });

// ---------------------------------------------------------------- playback
function seek(i) {
  S.kf = Math.max(0, Math.min(S.n - 1, i));
  const k = Math.floor(S.kf);
  const changed = k !== S.k;
  S.k = k;
  if (changed) refresh(); else drawChart();
}
let lastRefresh = 0;
function refresh(force = false) {
  const now = performance.now();
  const t = timeOf(S.k);
  $("clock").textContent = S.sc.timeUnit === "years" ? t.short : t.clock;
  $("clockDate").textContent = S.sc.timeUnit === "years" ? `sample ${S.k + 1} / ${S.n}` : t.long;
  update3D();
  updateSensors(); updateLedger();
  if (force || now - lastRefresh > 90 || !S.playing) {
    lastRefresh = now;
    if (S.tab === "sp") updateSpTable();
    if (S.tab === "diag") drawDiagrams();
    if (S.tab === "vars") updateVars();
  }
  if (S.playing && (S.k >= S.win[1] - 1 || S.k < S.win[0])) {
    const len = S.win[1] - S.win[0];
    const a = Math.min(S.n - len, Math.max(0, S.k - Math.round(len * 0.1)));
    S.win = [a, a + len];
  }
  drawChart();
}
const playBtn = $("play");
function setPlaying(p) { S.playing = p; playBtn.textContent = p ? "Pause" : "Play"; }
playBtn.onclick = () => { if (!S.playing && S.k >= S.n - 1) seek(0); setPlaying(!S.playing); };
$("stepBack").onclick = () => { setPlaying(false); seek(S.k - 1); };
$("stepFwd").onclick = () => { setPlaying(false); seek(S.k + 1); };
$("speed").onchange = e => { S.speed = +e.target.value; };
document.addEventListener("keydown", e => {
  if (e.target.matches("input, select, textarea")) return;
  if (e.code === "Space") { e.preventDefault(); playBtn.click(); }
  if (e.code === "ArrowRight") seek(S.k + (e.shiftKey ? 24 : 1));
  if (e.code === "ArrowLeft") seek(S.k - (e.shiftKey ? 24 : 1));
});

// tabs
document.querySelectorAll(".tabs button").forEach(b => b.addEventListener("click", () => {
  S.tab = b.dataset.tab;
  document.querySelectorAll(".tabs button").forEach(x => x.setAttribute("aria-selected", x === b ? "true" : "false"));
  document.querySelectorAll(".pane").forEach(p => p.classList.toggle("on", p.dataset.tab === S.tab));
  refresh(true);
  if (S.tab === "vars") drawFocus();
}));

// scenario picker
const sel = $("scenario");
for (const s of CFG.scenarios) {
  const o = document.createElement("option");
  o.value = s.key; o.textContent = s.name;
  sel.appendChild(o);
}
const req = new URLSearchParams(location.search).get("scenario");
const startKey = CFG.scenarios.some(s => s.key === req) ? req : CFG.scenarios[0].key;
sel.value = startKey;
sel.onchange = () => {
  loadScenario(sel.value).catch(err => setStatus(`Could not load results: ${err}`, true));
  const u = new URL(location.href); u.searchParams.set("scenario", sel.value); history.replaceState(null, "", u);
};

const qtab = new URLSearchParams(location.search).get("tab");
if (qtab) setTimeout(() => document.querySelector(`.tabs button[data-tab="${qtab}"]`)?.click(), 0);
let last = performance.now();
function loop(now) {
  requestAnimationFrame(loop);
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  if (S.playing && S.sc) {
    const di = dt * S.speed / S.sc.dt;
    if (S.kf + di >= S.n - 1) { seek(S.n - 1); setPlaying(false); } else seek(S.kf + di);
  }
  controls.update();
  animateBindings(dt);
  animateFlows(dt);
  positionTags();
  if (aoOn()) composer.render(); else renderer.render(scene, camera);
}

setView("reset");
resize();
loadModel();
loadScenario(startKey).catch(err => setStatus(`Could not load results (${err}). Serve via run_viewer.cmd.`, true));
requestAnimationFrame(loop);
window.addEventListener("resize", () => { drawChart(); if (S.tab === "diag") drawDiagrams(); });
