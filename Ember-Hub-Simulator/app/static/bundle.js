/* Sim Workbench — vanilla JS helpers for the scientific workbench layout. No dependencies. */
(function () {
  'use strict';
  var NS = {};
  var DPR = function () { return Math.max(1, window.devicePixelRatio || 1); };

  /* ---------- tokens & theme ---------- */
  function token(name, el) {
    return getComputedStyle(el || document.documentElement).getPropertyValue('--' + name).trim();
  }
  function onThemeChange(cb) {
    var mo = new MutationObserver(cb);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class', 'style'] });
    if (window.matchMedia) {
      var mq = window.matchMedia('(prefers-color-scheme: dark)');
      if (mq.addEventListener) mq.addEventListener('change', cb);
    }
    return function () { mo.disconnect(); };
  }
  NS.token = token; NS.onThemeChange = onThemeChange;

  /* ---------- formatting ---------- */
  function fmt(v) {
    if (v == null || !isFinite(v)) return '—';
    var a = Math.abs(v);
    if (a === 0) return '0';
    if (a >= 1e5 || a < 1e-2) return v.toExponential(2).replace('-', '−');
    var s = a >= 100 ? v.toFixed(1) : a >= 10 ? v.toFixed(2) : v.toFixed(3);
    return s.replace('-', '−');
  }
  NS.fmt = fmt;

  /* ---------- seeded demo run ---------- */
  function rng(seed) {
    var s = seed >>> 0 || 1;
    return function () { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 1e9) / 1e9; };
  }
  function gauss(r) { var u = r() || 1e-9, v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }

  var SCENARIOS = {
    disk: { name: 'Disk relaxation', seed: 7, arms: 2, bar: 0.25, merger: 0 },
    bar: { name: 'Bar instability', seed: 21, arms: 2, bar: 0.9, merger: 0 },
    merger: { name: 'Minor merger', seed: 42, arms: 3, bar: 0.4, merger: 1 }
  };
  NS.scenarios = SCENARIOS;

  /* demoRun(key) -> { name, n, vars:[{key,label,unit}], data:{key:Float64Array}, particles } */
  function demoRun(key) {
    var sc = SCENARIOS[key] || SCENARIOS.disk, r = rng(sc.seed), n = 600, i;
    var vars = [
      { key: 't', label: 'Time', unit: 'Myr' },
      { key: 'E_kin', label: 'Kinetic energy', unit: '10⁵¹ erg' },
      { key: 'E_pot', label: 'Potential energy', unit: '10⁵¹ erg' },
      { key: 'E_tot', label: 'Total energy', unit: '10⁵¹ erg' },
      { key: 'L_z', label: 'Angular momentum', unit: '10⁶⁷ g cm² s⁻¹' },
      { key: 'r_half', label: 'Half-mass radius', unit: 'kpc' },
      { key: 'sigma_v', label: 'Velocity dispersion', unit: 'km s⁻¹' },
      { key: 'Q', label: 'Toomre Q', unit: '' },
      { key: 'A2', label: 'Bar amplitude A₂', unit: '' },
      { key: 'SFR', label: 'Star formation rate', unit: 'M☉ yr⁻¹' }
    ];
    var d = {};
    vars.forEach(function (v) { d[v.key] = new Float64Array(n); });
    for (i = 0; i < n; i++) {
      var t = i, osc = Math.exp(-t / 120) * Math.cos(t / 25);
      var hit = sc.merger ? Math.exp(-Math.pow((t - 320) / 30, 2)) : 0;
      d.t[i] = t;
      d.E_kin[i] = 4.2 + 0.6 * osc + 0.9 * hit + 0.004 * gauss(r);
      d.E_pot[i] = -8.4 - 0.6 * osc - 0.9 * hit + 0.004 * gauss(r);
      d.E_tot[i] = d.E_kin[i] + d.E_pot[i] - 0.000012 * t * (1 + 4 * sc.merger);
      d.L_z[i] = 3.1 - 0.00012 * t + 0.25 * hit + 0.004 * gauss(r);
      d.r_half[i] = 4 + 1.2 * (1 - Math.exp(-t / 150)) + 0.15 * Math.sin(t / 30) + 0.6 * hit;
      d.sigma_v[i] = 35 + 18 * (1 - Math.exp(-t / 200)) + 12 * hit + 0.4 * gauss(r);
      d.Q[i] = 1.2 + 0.6 * (1 - Math.exp(-t / 180)) + 0.01 * gauss(r);
      d.A2[i] = 0.02 + sc.bar * 0.33 / (1 + Math.exp(-(t - 250) / 40)) + 0.004 * gauss(r);
      d.SFR[i] = Math.max(0, 2.4 * Math.exp(-t / 300) * (1 + 0.3 * Math.sin(t / 40)) + 3 * hit + 0.08 * gauss(r));
    }
    var particles = [], np = 1800, nb = 320;
    for (i = 0; i < np; i++) {
      var R = Math.min(13, -2.6 * Math.log(r() || 1e-6) + 0.4);
      var arm = Math.floor(r() * sc.arms);
      var th = arm * 2 * Math.PI / sc.arms + Math.log(R) * 2.1 + gauss(r) * 0.35;
      particles.push({ R: R, th: th, z: gauss(r) * 0.28 * Math.exp(-R / 7), kind: 0 });
    }
    for (i = 0; i < nb; i++) {
      var rr = Math.abs(gauss(r)) * 1.1, ph = r() * 2 * Math.PI, ct = r() * 2 - 1, st = Math.sqrt(1 - ct * ct);
      particles.push({ R: rr * st, th: ph, z: rr * ct * 0.7, kind: 1 });
    }
    if (sc.merger) for (i = 0; i < 260; i++) particles.push({ R: Math.abs(gauss(r)) * 0.8, th: r() * 6.283, z: gauss(r) * 0.5, kind: 2 });
    return { key: key, name: sc.name, n: n, vars: vars, data: d, particles: particles, bar: sc.bar, merger: sc.merger };
  }
  NS.demoRun = demoRun;
  NS.varOf = function (run, key) { for (var i = 0; i < run.vars.length; i++) if (run.vars[i].key === key) return run.vars[i]; return null; };
  function axisTitle(v) { return v ? v.label + (v.unit ? ' [' + v.unit + ']' : '') : ''; }

  /* ---------- canvas helpers ---------- */
  function fit(canvas) {
    var w = canvas.clientWidth, h = canvas.clientHeight, dpr = DPR();
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    }
    var ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx: ctx, w: w, h: h };
  }
  function watch(el, draw) {
    var raf = 0, sched = function () { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw); };
    if (window.ResizeObserver) new ResizeObserver(sched).observe(el);
    onThemeChange(sched);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(sched);
    return sched;
  }
  function niceTicks(lo, hi, count) {
    if (!(hi > lo)) { hi = lo + 1; lo = lo - 1; }
    var span = hi - lo, step = Math.pow(10, Math.floor(Math.log10(span / count))), err = span / count / step;
    if (err >= 7.5) step *= 10; else if (err >= 3.5) step *= 5; else if (err >= 1.5) step *= 2;
    var out = [], v = Math.ceil(lo / step) * step;
    for (; v <= hi + step * 1e-9; v += step) out.push(Math.abs(v) < step * 1e-9 ? 0 : v);
    return out;
  }
  function tickLabel(v) {
    var a = Math.abs(v);
    if (a !== 0 && (a >= 1e5 || a < 1e-3)) return v.toExponential(1).replace('-', '−');
    return (+v.toPrecision(6)).toString().replace('-', '−');
  }
  function extent(arr) {
    var lo = Infinity, hi = -Infinity;
    for (var i = 0; i < arr.length; i++) { var v = arr[i]; if (v < lo) lo = v; if (v > hi) hi = v; }
    var pad = (hi - lo) * 0.06 || Math.abs(hi) * 0.1 || 1;
    return [lo - pad, hi + pad];
  }
  function withAlpha(c, a) { var ctx = withAlpha._c || (withAlpha._c = document.createElement('canvas').getContext('2d')); ctx.fillStyle = c; var h = ctx.fillStyle; if (h[0] === '#') { var n = parseInt(h.slice(1), 16); return 'rgba(' + (n >> 16 & 255) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + a + ')'; } return h.replace(/rgba?\(([^)]+?)(,\s*[\d.]+)?\)/, 'rgba($1,' + a + ')'); }
  NS.fit = fit; NS.niceTicks = niceTicks;

  /* plot(canvas, {x:{values,label}, series:[{values,label,color}], mode:'line'|'scatter', cursor}) */
  function plot(canvas, o) {
    var f = fit(canvas), ctx = f.ctx, w = f.w, h = f.h;
    if (w < 40 || h < 40) return;
    var mono = token('font-mono'), axisCol = token('line-strong'), grid = token('line'), faint = token('ink-faint'), muted = token('ink-muted'), accent = token('accent');
    var m = { l: 52, r: 12, t: o.compact ? 10 : 22, b: 30 };
    var xs = o.x.values, xe = o.xDomain || extent(xs), ye = [Infinity, -Infinity];
    o.series.forEach(function (s) { var e = extent(s.values); ye[0] = Math.min(ye[0], e[0]); ye[1] = Math.max(ye[1], e[1]); });
    if (o.yDomain) ye = o.yDomain;
    var X = function (v) { return m.l + (v - xe[0]) / (xe[1] - xe[0]) * (w - m.l - m.r); };
    var Y = function (v) { return h - m.b - (v - ye[0]) / (ye[1] - ye[0]) * (h - m.t - m.b); };
    ctx.font = '10px ' + mono; ctx.lineWidth = 1;
    var xt = niceTicks(xe[0], xe[1], Math.max(2, Math.floor((w - m.l) / 70))), yt = niceTicks(ye[0], ye[1], Math.max(2, Math.floor((h - m.t - m.b) / 34)));
    ctx.strokeStyle = grid; ctx.fillStyle = faint;
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    yt.forEach(function (v) { var y = Math.round(Y(v)) + 0.5; ctx.beginPath(); ctx.moveTo(m.l, y); ctx.lineTo(w - m.r, y); ctx.stroke(); ctx.fillText(tickLabel(v), m.l - 6, y); });
    ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    xt.forEach(function (v) { var x = Math.round(X(v)) + 0.5; ctx.beginPath(); ctx.moveTo(x, m.t); ctx.lineTo(x, h - m.b); ctx.stroke(); ctx.fillText(tickLabel(v), x, h - m.b + 5); });
    ctx.strokeStyle = axisCol; ctx.beginPath(); ctx.moveTo(m.l + 0.5, m.t); ctx.lineTo(m.l + 0.5, h - m.b + 0.5); ctx.lineTo(w - m.r, h - m.b + 0.5); ctx.stroke();
    ctx.fillStyle = muted; ctx.textAlign = 'left'; ctx.textBaseline = 'top'; if (!o.compact) ctx.fillText(o.series.length === 1 ? o.series[0].label : '', m.l, 4);
    ctx.textAlign = 'right'; ctx.textBaseline = 'bottom'; ctx.fillText(o.x.label || '', w - m.r, h - m.b - 3);
    ctx.save(); ctx.beginPath(); ctx.rect(m.l, m.t - 2, w - m.l - m.r, h - m.t - m.b + 4); ctx.clip();
    var cur = o.cursor == null ? xs.length - 1 : o.cursor;
    o.series.forEach(function (s) {
      var vs = s.values, i;
      [[0, xs.length - 1, 0.22], [0, cur, 1]].forEach(function (pass) {
        if (pass[1] < 0) return;
        if (o.mode === 'scatter') {
          ctx.fillStyle = withAlpha(s.color, pass[2] * 0.85);
          for (i = pass[0]; i <= pass[1]; i++) { ctx.beginPath(); ctx.arc(X(xs[i]), Y(vs[i]), 1.6, 0, 6.283); ctx.fill(); }
        } else {
          ctx.strokeStyle = withAlpha(s.color, pass[2]); ctx.lineWidth = 1.5; ctx.lineJoin = 'round'; ctx.beginPath();
          for (i = pass[0]; i <= pass[1]; i++) { if (i === pass[0]) ctx.moveTo(X(xs[i]), Y(vs[i])); else ctx.lineTo(X(xs[i]), Y(vs[i])); }
          ctx.stroke();
        }
      });
      if (cur >= 0 && cur < xs.length) {
        ctx.fillStyle = accent; ctx.strokeStyle = token('bg-viewport'); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(X(xs[cur]), Y(vs[cur]), 4, 0, 6.283); ctx.stroke(); ctx.fill();
      }
    });
    ctx.restore();
  }
  NS.plot = plot;

  /* ---------- 3D viewport (canvas point renderer with orbit) ---------- */
  function viewport(canvas, run, opts) {
    opts = opts || {};
    var yaw = opts.yaw != null ? opts.yaw : 0.6, pitch = opts.pitch != null ? opts.pitch : 0.95, zoom = 1, frame = 0, drag = null;
    function draw() {
      var f = fit(canvas), ctx = f.ctx, w = f.w, h = f.h;
      var c1 = token('series-2'), c2 = token('series-1'), c3 = token('series-7');
      var t = run.data.t[frame], cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
      var scale = Math.min(w, h) * 0.065 * zoom, dist = 40, pts = [];
      var barAngle = t * 0.012;
      run.particles.forEach(function (p) {
        var om = p.kind === 1 ? 0.03 : 0.22 / Math.max(0.6, p.R), th = p.th - om * t * 0.25, R = p.R;
        var x = R * Math.cos(th), y = R * Math.sin(th), z = p.z;
        if (p.kind !== 2 && R < 4 && run.bar > 0.3) { /* stretch the inner disk along a rotating bar axis */
          var grow = 1 + run.bar * 0.8 * Math.min(1, t / 300) * (1 - R / 4), cb = Math.cos(barAngle), sb = Math.sin(barAngle);
          var u = x * cb + y * sb, v = -x * sb + y * cb; u *= grow; v /= Math.sqrt(grow); x = u * cb - v * sb; y = u * sb + v * cb;
        }
        if (p.kind === 2) { var a = Math.max(0, 1 - t / 380), ox = 14 * a * Math.cos(t / 60), oy = 14 * a * Math.sin(t / 60), oz = 4 * a; x += ox; y += oy; z += oz; }
        var x1 = x * cy - y * sy, y1 = x * sy + y * cy;
        var y2 = y1 * cp - z * sp, z2 = y1 * sp + z * cp;
        var k = dist / (dist + y2);
        pts.push([w / 2 + x1 * scale * k, h / 2 - z2 * scale * k, k, p.kind]);
      });
      pts.sort(function (a, b) { return a[2] - b[2]; });
      ctx.globalCompositeOperation = 'source-over';
      pts.forEach(function (q) {
        ctx.fillStyle = q[3] === 1 ? c2 : q[3] === 2 ? c3 : c1;
        ctx.globalAlpha = q[3] === 1 ? 0.75 : 0.55;
        var s = 1.3 * q[2];
        ctx.fillRect(q[0] - s / 2, q[1] - s / 2, s, s);
      });
      ctx.globalAlpha = 1;
      // axis gizmo
      var gx = 34, gy = h - 34, L = 18;
      [[1, 0, 0, 'x', token('series-6')], [0, 1, 0, 'y', token('series-3')], [0, 0, 1, 'z', token('series-5')]].forEach(function (a) {
        var x1 = a[0] * cy - a[1] * sy, y1 = a[0] * sy + a[1] * cy, z2 = y1 * sp + a[2] * cp;
        ctx.strokeStyle = a[4]; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(gx, gy); ctx.lineTo(gx + x1 * L, gy - z2 * L); ctx.stroke();
        ctx.fillStyle = a[4]; ctx.font = '10px ' + token('font-mono'); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(a[3], gx + x1 * (L + 8), gy - z2 * (L + 8));
      });
    }
    var sched = watch(canvas.parentNode, draw);
    canvas.addEventListener('pointerdown', function (e) { drag = [e.clientX, e.clientY, yaw, pitch]; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener('pointermove', function (e) { if (!drag) return; yaw = drag[2] - (e.clientX - drag[0]) * 0.008; pitch = Math.max(0.05, Math.min(1.55, drag[3] - (e.clientY - drag[1]) * 0.008)); sched(); });
    canvas.addEventListener('pointerup', function () { drag = null; });
    canvas.addEventListener('wheel', function (e) { e.preventDefault(); zoom = Math.max(0.4, Math.min(4, zoom * Math.exp(-e.deltaY * 0.0015))); sched(); }, { passive: false });
    canvas.addEventListener('dblclick', function () { yaw = 0.6; pitch = 0.95; zoom = 1; sched(); });
    return { setFrame: function (i) { frame = i; sched(); }, redraw: sched };
  }
  NS.viewport = viewport;

  /* ---------- Splitter ---------- */
  /* splitter(handle, {root, prop, axis:'x'|'y', pane, min, max:fn, step}) — drags the size of `pane` (the pane AFTER the handle). */
  function splitter(handle, o) {
    var min = o.min || 220, step = o.step || 16, horiz = o.axis === 'y';
    handle.setAttribute('role', 'separator');
    handle.setAttribute('aria-orientation', horiz ? 'horizontal' : 'vertical');
    handle.tabIndex = 0;
    function size() { var r = o.pane.getBoundingClientRect(); return horiz ? r.height : r.width; }
    function set(px) {
      var max = o.max ? o.max() : Infinity;
      px = Math.round(Math.max(min, Math.min(max, px)));
      o.root.style.setProperty(o.prop, px + 'px');
      handle.setAttribute('aria-valuenow', px);
      try { if (o.storageKey) localStorage.setItem(o.storageKey, px); } catch (e) {}
      if (o.onResize) o.onResize(px);
    }
    try { var saved = o.storageKey && localStorage.getItem(o.storageKey); if (saved) set(+saved); } catch (e) {}
    handle.addEventListener('pointerdown', function (e) {
      e.preventDefault(); handle.setPointerCapture(e.pointerId); handle.classList.add('is-dragging'); document.body.classList.add('sw-resizing');
      var start = horiz ? e.clientY : e.clientX, s0 = size();
      function move(ev) { var d = (horiz ? ev.clientY : ev.clientX) - start; set(s0 - d); }
      function up() { handle.classList.remove('is-dragging'); document.body.classList.remove('sw-resizing'); handle.removeEventListener('pointermove', move); handle.removeEventListener('pointerup', up); handle.removeEventListener('pointercancel', up); }
      handle.addEventListener('pointermove', move); handle.addEventListener('pointerup', up); handle.addEventListener('pointercancel', up);
    });
    handle.addEventListener('keydown', function (e) {
      var k = e.key, d = e.shiftKey ? step * 4 : step;
      var grow = horiz ? 'ArrowUp' : 'ArrowLeft', shrink = horiz ? 'ArrowDown' : 'ArrowRight';
      if (k === grow) set(size() + d); else if (k === shrink) set(size() - d);
      else if (k === 'Home') set(min); else if (k === 'End') set(o.max ? o.max() : size());
      else return;
      e.preventDefault();
    });
    handle.addEventListener('dblclick', function () { o.root.style.removeProperty(o.prop); try { if (o.storageKey) localStorage.removeItem(o.storageKey); } catch (e) {} if (o.onResize) o.onResize(size()); });
    return { set: set };
  }
  NS.splitter = splitter;

  /* ---------- KPI tiles ---------- */
  function kpis(container, run, keys) {
    container.classList.add('sw-kpis');
    var els = keys.map(function (k) {
      var v = NS.varOf(run, k), d = document.createElement('div');
      d.className = 'sw-kpi';
      d.innerHTML = '<div class="k-name"></div><div class="k-val"></div><div class="k-unit"></div><div class="k-delta"></div>';
      d.children[0].textContent = v.label; d.children[2].textContent = v.unit || ' ';
      container.appendChild(d); return d;
    });
    function setFrame(i) {
      keys.forEach(function (k, j) {
        var a = run.data[k], v = a[i], v0 = a[0], rel = v0 ? (v - v0) / Math.abs(v0) : 0;
        els[j].children[1].textContent = fmt(v);
        var dEl = els[j].children[3];
        dEl.textContent = (rel >= 0 ? '+' : '−') + Math.abs(rel * 100).toFixed(1) + '% vs t₀';
        dEl.className = 'k-delta' + (k === 'E_tot' && Math.abs(rel) > 0.004 ? ' is-warn' : '');
      });
    }
    setFrame(0);
    return { setFrame: setFrame };
  }
  NS.kpis = kpis;

  /* ---------- Plot builder: pick any simulated variable for x and y ---------- */
  function plotBuilder(container, run, o) {
    o = o || {};
    container.classList.add('sw-plots');
    var cards = [], cursor = 0, colorIdx = 0;
    if (o.fill) container.classList.add('is-fill');
    function addNext() { addPlot({ x: 't', y: run.vars[1 + (cards.length % (run.vars.length - 1))].key, mode: 'line', edit: true }); }
    var add = null;
    if (o.tile !== false) {
      add = document.createElement('button');
      add.className = 'sw-add-plot'; add.type = 'button'; add.textContent = '+ Add plot';
      add.addEventListener('click', addNext);
    }
    function count() { container.style.setProperty('--plot-count', cards.length); }
    function options(sel) { return run.vars.map(function (v) { return '<option value="' + v.key + '"' + (v.key === sel ? ' selected' : '') + '>' + v.label + '</option>'; }).join(''); }
    function addPlot(spec) {
      var c = document.createElement('div'), color = 'series-' + ((colorIdx++ % 7) + 1);
      c.className = 'sw-plot-card';
      var X_ICON = '<svg viewBox="0 0 16 16"><path d="M4.2 3.1 8 6.9l3.8-3.8 1.1 1.1L9.1 8l3.8 3.8-1.1 1.1L8 9.1l-3.8 3.8-1.1-1.1L6.9 8 3.1 4.2z"/></svg>';
      var CHEV = '<svg viewBox="0 0 16 16"><path d="M4 6l4 4 4-4z"/></svg>';
      c.innerHTML = '<div class="sw-plot-head">' +
        '<button type="button" class="sw-plot-title" aria-expanded="false">' + CHEV + '<span class="sw-plot-name"></span></button>' +
        '<button type="button" class="sw-btn is-ghost is-icon sw-plot-remove" aria-label="Remove plot" title="Remove plot">' + X_ICON + '</button></div>' +
        '<div class="sw-plot-controls" hidden>' +
        '<span class="sw-axis">y</span><select class="sw-select" aria-label="Y variable">' + options(spec.y) + '</select>' +
        '<span class="sw-seg" role="group" aria-label="Plot type"><button type="button" data-m="line">Line</button><button type="button" data-m="scatter">Points</button></span>' +
        '<span class="sw-axis">x</span><select class="sw-select" aria-label="X variable">' + options(spec.x) + '</select>' +
        '</div><div class="sw-plot-canvas"><canvas></canvas></div>';
      container.insertBefore(c, add);

      var ys = c.querySelectorAll('select')[0], xs = c.querySelectorAll('select')[1], segs = c.querySelectorAll('.sw-seg button'), cv = c.querySelector('canvas');
      var card = { spec: spec, draw: null };
      var title = c.querySelector('.sw-plot-title'), ctrls = c.querySelector('.sw-plot-controls'), nameEl = c.querySelector('.sw-plot-name');
      function sync() {
        segs.forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.m === spec.mode)); });
        nameEl.innerHTML = ''; nameEl.appendChild(document.createTextNode(NS.varOf(run, spec.y).label + ' '));
        var vs = document.createElement('span'); vs.className = 'sw-vs'; vs.textContent = 'vs'; nameEl.appendChild(vs);
        nameEl.appendChild(document.createTextNode(' ' + NS.varOf(run, spec.x).label));
      }
      function edit(open) { ctrls.hidden = !open; title.setAttribute('aria-expanded', String(open)); }
      title.addEventListener('click', function () { edit(ctrls.hidden); });
      if (spec.edit) edit(true);
      card.draw = watch(cv.parentNode, function () {
        var xv = NS.varOf(run, spec.x), yv = NS.varOf(run, spec.y);
        plot(cv, { x: { values: run.data[spec.x], label: axisTitle(xv) }, series: [{ values: run.data[spec.y], label: axisTitle(yv), color: token(color) }], mode: spec.mode, cursor: cursor, compact: true });
      });
      ys.addEventListener('change', function () { spec.y = ys.value; sync(); card.draw(); });
      xs.addEventListener('change', function () { spec.x = xs.value; if (spec.x !== 't' && spec.mode === 'line') spec.mode = 'scatter'; sync(); card.draw(); });
      segs.forEach(function (b) { b.addEventListener('click', function () { spec.mode = b.dataset.m; sync(); card.draw(); }); });
      c.querySelector('.sw-plot-remove').addEventListener('click', function () { c.remove(); cards.splice(cards.indexOf(card), 1); count(); });
      sync(); cards.push(card); count();
    }
    if (add) container.appendChild(add);
    (o.plots || [{ x: 't', y: 'E_tot', mode: 'line' }]).forEach(addPlot);
    return { addPlot: addPlot, add: addNext, setCursor: function (i) { cursor = i; cards.forEach(function (c) { c.draw(); }); } };
  }
  NS.plotBuilder = plotBuilder;

  /* ---------- Time series: stacked small multiples sharing the time axis ---------- */
  function timeSeries(head, body, run, o) {
    o = o || {};
    var on = (o.keys || ['E_tot', 'L_z', 'r_half', 'A2']).slice(), cursor = 0, canvas = document.createElement('canvas');
    body.appendChild(canvas);
    var chips = document.createElement('div'); chips.style.cssText = 'display:flex;gap:var(--space-1)';
    run.vars.slice(1).forEach(function (v, i) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'sw-chip'; b.style.setProperty('--c', 'var(--series-' + ((i % 7) + 1) + ')');
      b.innerHTML = '<i></i>'; b.appendChild(document.createTextNode(v.label));
      b.setAttribute('aria-pressed', String(on.indexOf(v.key) >= 0));
      b.addEventListener('click', function () { var j = on.indexOf(v.key); if (j >= 0) on.splice(j, 1); else on.push(v.key); b.setAttribute('aria-pressed', String(j < 0)); sched(); });
      chips.appendChild(b);
    });
    head.appendChild(chips);
    function colorOf(k) { for (var i = 1; i < run.vars.length; i++) if (run.vars[i].key === k) return token('series-' + (((i - 1) % 7) + 1)); }
    function draw() {
      var f = fit(canvas), ctx = f.ctx, w = f.w, h = f.h, ml = 12, mr = 96, mb = 22, n = on.length;
      if (w < 60 || h < 40) return;
      var t = run.data.t, X = function (v) { return ml + v / (t[t.length - 1]) * (w - ml - mr); }, rowH = (h - mb) / Math.max(1, n);
      var mono = token('font-mono'), faint = token('ink-faint'), muted = token('ink-muted'), grid = token('line'), ink = token('ink');
      ctx.font = '10px ' + mono;
      niceTicks(0, t[t.length - 1], Math.max(2, Math.floor(w / 90))).forEach(function (v) {
        var x = Math.round(X(v)) + 0.5; ctx.strokeStyle = grid; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h - mb); ctx.stroke();
        ctx.fillStyle = faint; ctx.textAlign = 'center'; ctx.textBaseline = 'top'; ctx.fillText(tickLabel(v), x, h - mb + 5);
      });
      ctx.textAlign = 'right'; ctx.fillText('t [Myr]', w - 8, h - mb + 5);
      on.forEach(function (k, r) {
        var a = run.data[k], e = extent(a), y0 = r * rowH, Y = function (v) { return y0 + 20 + (1 - (v - e[0]) / (e[1] - e[0])) * (rowH - 26); }, v = NS.varOf(run, k), col = colorOf(k), i;
        if (r > 0) { ctx.strokeStyle = grid; ctx.beginPath(); ctx.moveTo(0, Math.round(y0) + 0.5); ctx.lineTo(w, Math.round(y0) + 0.5); ctx.stroke(); }
        ctx.strokeStyle = withAlpha(col, 0.22); ctx.lineWidth = 1.25; ctx.beginPath();
        for (i = 0; i < a.length; i++) { if (!i) ctx.moveTo(X(t[i]), Y(a[i])); else ctx.lineTo(X(t[i]), Y(a[i])); } ctx.stroke();
        ctx.strokeStyle = col; ctx.beginPath();
        for (i = 0; i <= cursor; i++) { if (!i) ctx.moveTo(X(t[i]), Y(a[i])); else ctx.lineTo(X(t[i]), Y(a[i])); } ctx.stroke();
        ctx.lineWidth = 1;
        ctx.textAlign = 'left'; ctx.textBaseline = 'top'; ctx.fillStyle = muted; ctx.font = '11px ' + token('font-sans');
        ctx.fillText(v.label + (v.unit ? ' [' + v.unit + ']' : ''), ml + 4, y0 + 4);
        ctx.font = '12px ' + mono; ctx.fillStyle = ink; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
        ctx.fillText(fmt(a[cursor]), w - 10, y0 + rowH / 2);
        ctx.font = '10px ' + mono;
      });
      var cx = Math.round(X(t[cursor])) + 0.5; ctx.strokeStyle = token('accent'); ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, h - mb); ctx.stroke(); ctx.lineWidth = 1;
    }
    var sched = watch(body, draw), scrub = null;
    canvas.addEventListener('pointerdown', function (e) {
      canvas.setPointerCapture(e.pointerId); scrub = true; move(e);
    });
    function move(e) {
      if (!scrub) return; var r = canvas.getBoundingClientRect(), tt = run.data.t, frac = (e.clientX - r.left - 12) / (r.width - 12 - 96);
      var i = Math.max(0, Math.min(tt.length - 1, Math.round(frac * (tt.length - 1)))); if (o.onScrub) o.onScrub(i); else api.setCursor(i);
    }
    canvas.addEventListener('pointermove', move);
    canvas.addEventListener('pointerup', function () { scrub = null; });
    var api = { setCursor: function (i) { cursor = i; sched(); } };
    return api;
  }
  NS.timeSeries = timeSeries;

  /* ---------- Tabs: switch between panels in one pane (no scrolling) ---------- */
  /* tabs(tablist, {storageKey, onChange}) — buttons with role=tab and aria-controls=<panel id>. */
  function tabs(list, o) {
    o = o || {};
    var btns = Array.prototype.slice.call(list.querySelectorAll('[role="tab"]'));
    function select(b, focus) {
      btns.forEach(function (x) {
        var on = x === b, panel = document.getElementById(x.getAttribute('aria-controls'));
        x.setAttribute('aria-selected', String(on)); x.tabIndex = on ? 0 : -1;
        if (panel) panel.hidden = !on;
      });
      if (focus) b.focus();
      try { if (o.storageKey) localStorage.setItem(o.storageKey, b.id || btns.indexOf(b)); } catch (e) {}
      if (o.onChange) o.onChange(b.getAttribute('aria-controls'), b);
    }
    btns.forEach(function (b, i) {
      b.addEventListener('click', function () { select(b); });
      b.addEventListener('keydown', function (e) {
        var j = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? btns.length - 1 : null;
        if (j == null) return; e.preventDefault(); select(btns[(j + btns.length) % btns.length], true);
      });
    });
    var start = btns.filter(function (b) { return b.getAttribute('aria-selected') === 'true'; })[0] || btns[0];
    try { var k = o.storageKey && localStorage.getItem(o.storageKey); if (k) start = document.getElementById(k) || btns[+k] || start; } catch (e) {}
    select(start);
    return { select: function (i) { select(btns[i]); } };
  }
  NS.tabs = tabs;

  /* ---------- Workbench: wire a .sw-workbench root built from the documented markup ---------- */
  function workbench(root, o) {
    o = o || {};
    var q = function (s) { return root.querySelector(s); };
    var run = demoRun(o.scenario || 'disk'), frame = 0, playing = false, last = 0, speed = 1;
    var parts = {};
    function build() {
      q('[data-sw="kpis"]').innerHTML = ''; q('[data-sw="plots"]').innerHTML = ''; q('[data-sw="ts-body"]').innerHTML = '';
      var chipHost = q('[data-sw="ts-chips"]'); chipHost.innerHTML = '';
      if (!parts.view) parts.view = viewport(q('[data-sw="viewport"] canvas'), run); else { parts.view = null; var old = q('[data-sw="viewport"] canvas'), nc = document.createElement('canvas'); old.replaceWith(nc); parts.view = viewport(nc, run); }
      parts.kpi = kpis(q('[data-sw="kpis"]'), run, o.kpis || ['E_tot', 'L_z', 'r_half', 'sigma_v', 'Q', 'SFR']);
      parts.plots = plotBuilder(q('[data-sw="plots"]'), run, { fill: true, tile: false, plots: o.plots || [{ x: 't', y: 'E_tot', mode: 'line' }, { x: 'r_half', y: 'sigma_v', mode: 'scatter' }] });
      parts.ts = timeSeries(chipHost, q('[data-sw="ts-body"]'), run, { onScrub: function (i) { pause(); go(i); } });
      go(frame);
    }
    function go(i) {
      frame = Math.max(0, Math.min(run.n - 1, i));
      parts.view.setFrame(frame); parts.kpi.setFrame(frame); parts.plots.setCursor(frame); parts.ts.setCursor(frame);
      var tEl = q('[data-sw="time"]'); if (tEl) tEl.textContent = run.data.t[frame].toFixed(1);
      var sEl = q('[data-sw="step"]'); if (sEl) sEl.textContent = (frame * 250).toLocaleString('en-GB');
      if (frame === run.n - 1 && playing) { playing = false; status('done'); }
    }
    function status(s) {
      var el = q('[data-sw="status"]'); if (!el) return;
      el.className = 'sw-status is-' + s; el.querySelector('span').textContent = { running: 'Running', paused: 'Paused', done: 'Done', ready: 'Ready' }[s] || s;
      if (s === 'ready') el.className = 'sw-status is-paused';
      var pb = q('[data-sw="play"]'); if (pb) { pb.setAttribute('aria-label', playing ? 'Pause' : 'Run'); pb.innerHTML = playing ? '<svg viewBox="0 0 16 16"><path d="M4 3h3v10H4zM9 3h3v10H9z"/></svg>Pause' : '<svg viewBox="0 0 16 16"><path d="M4 2.5v11l9-5.5z"/></svg>Run'; }
    }
    function tick(ts) { if (!playing) return; if (ts - last > 30) { last = ts; go(frame + speed); } requestAnimationFrame(tick); }
    function play() { if (frame >= run.n - 1) frame = 0; playing = true; status('running'); requestAnimationFrame(tick); }
    function pause() { if (!playing) return; playing = false; status('paused'); }
    var pb = q('[data-sw="play"]'); if (pb) pb.addEventListener('click', function () { playing ? pause() : play(); });
    var rb = q('[data-sw="reset"]'); if (rb) rb.addEventListener('click', function () { playing = false; go(0); status('ready'); });
    var sim = q('[data-sw="sim"]'); if (sim) sim.addEventListener('change', function () { playing = false; run = demoRun(sim.value); frame = 0; build(); status('ready'); });
    var sp = q('[data-sw="speed"]'); if (sp) sp.addEventListener('change', function () { speed = +sp.value || 1; });
    var addBtn = q('[data-sw="add-plot"]'); if (addBtn) addBtn.addEventListener('click', function () { parts.plots.add(); });
    var tl = q('[data-sw="metric-tabs"]');
    if (tl) tabs(tl, { storageKey: o.storageKey && o.storageKey + ':tab', onChange: function (id, b) { if (addBtn) addBtn.hidden = b.getAttribute('data-tab') !== 'plots'; } });
    var main = q('.sw-main'), side = q('[data-sw="side"]'), bottom = q('.sw-bottom');
    splitter(q('[data-sw="split-x"]'), { root: root, prop: '--wb-side', axis: 'x', pane: side, min: 220, max: function () { return main.clientWidth - 220 - 24; }, storageKey: o.storageKey && o.storageKey + ':side' });
    splitter(q('[data-sw="split-y"]'), { root: root, prop: '--wb-bottom', axis: 'y', pane: bottom, min: 120, max: function () { return root.clientHeight - 48 - 220 - 8; }, storageKey: o.storageKey && o.storageKey + ':bottom' });
    build(); status('ready');
    if (o.autoplay) play();
    return { play: play, pause: pause, go: go };
  }
  NS.workbench = workbench;

  window.SimWorkbench = NS;
})();
