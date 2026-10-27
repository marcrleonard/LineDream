// LineDream Terrain: pick a place, stand somewhere, render it as line art. The renderers are the Python terrain
// experiments (py/vista.py, py/strata.py) running in Pyodide in a worker; this file is the UI around them.
//
// Query parameters, all optional:
//   ?pyodide=<url>  a Pyodide distribution to load from (default: the jsDelivr CDN)
//   ?wheel=<url>    a LineDream wheel to install (the website build sets data-wheel on <html>; otherwise PyPI)
// The whole scene (place, camera, mode, every parameter) lives in the URL hash, so a link reproduces a drawing.
import { MODES, PALETTES, PRESETS, breakupParams, defaults } from "./schema.mjs";
import { fetchDEM, hillshade, metersPerPixel, sample, toLatLon, toUV, MAX_ZOOM } from "./tiles.mjs";
import { compose } from "./compose.mjs";
import { DEFAULT_SYSTEM, SYSTEMS, displayRange, fmtDistance, fmtLength, fromDisplay, niceStep, toDisplay, unitName } from "./units.mjs";
import { deleteMyScene, listMyScenes, saveMyScene } from "./myscenes.mjs";
import { decodeHash, encodeHash, parseScene, sceneFilename, sceneFromState } from "./scene.mjs";

const PYODIDE_VERSION = "314.0.7";
const query = new URLSearchParams(location.search);
const indexURL = new URL(query.get("pyodide") || `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`, location.href).href;
const wheelParam = query.get("wheel") || document.documentElement.dataset.wheel;
const wheel = wheelParam ? new URL(wheelParam, location.href).href : "linedream";

const $ = (id) => document.getElementById(id);
const fmt = (n) => Math.round(n).toLocaleString("en-US");

// ------------------------------------------------------------------------------------------- state

const state = {
  mode: "vista",
  params: { vista: defaults("vista"), strata: defaults("strata") },
  area: null,             // {lat, lon, zoom, size}
  cam: [0.5, 0.93], target: [0.5, 0.45], halo: [0.5, 0.45], center: [0.5, 0.5],
  preset: "",
};
let dem = null;           // {grid, meta}
let shadeImg = null;      // hillshade canvas for the planner
let worker, workerReady = false, demSent = false;
let busy = false, pending = null, reqId = 0, previewTimer = null;
let lastSvg = null, lastQuality = null, lastUrl = null;
// Preview (half size, ~4x faster) or full; a per-browser preference, not part of the scene.
let quality = (() => { try { return localStorage.getItem("linedream-terrain/quality") === "full" ? "full" : "preview"; } catch { return "preview"; } })();
let placing = "cam";
// feet/miles or metres/kilometres for what's shown; everything stored stays metric (units.mjs)
let units = (() => { try { const u = localStorage.getItem("linedream-terrain/units"); return u in SYSTEMS ? u : DEFAULT_SYSTEM; } catch { return DEFAULT_SYSTEM; } })();
let navT = { s: 1, x: 0, y: 0 }, sentNav = navT, navLoading = false;  // see "navigation" below

// ------------------------------------------------------------------------------------------- worker

function startWorker() {
  worker = new Worker(new URL("worker.mjs", import.meta.url), { type: "module" });
  worker.onmessage = ({ data }) => {
    if (data.type === "progress") setStatus(data.text, "busy");
    else if (data.type === "ready") {
      workerReady = true;
      $("versions").textContent = data.versions;
      setStatus("Python ready", "ok");
      sendDem();
    } else if (data.type === "fatal") setStatus("Python failed to start: " + data.error, "err");
    else if (data.type === "dem") { demSent = true; schedulePreview(0); }
    else if (data.type === "result") {
      busy = false;
      showSvg(data.svg, data.quality);
      setStatus(`${data.quality === "full" ? "Full render" : "Preview"} · ${data.seconds.toFixed(1)} s · ${fmt(data.strokes)} strokes`, "ok");
      pump();
    } else if (data.type === "error") {
      busy = false;
      setStatus("Render failed: " + data.error, "err");
      pump();
    }
  };
  worker.postMessage({ type: "init", indexURL, wheel });
}

function sendDem() {
  if (!workerReady || !dem) return;
  demSent = false;
  const grid = dem.grid.slice();
  worker.postMessage({ type: "dem", grid, size: dem.meta.size, width_m: dem.meta.width_m }, [grid.buffer]);
}

function requestRender(quality) {
  pending = { quality };
  pump();
}

function pump() {
  if (!workerReady || !demSent || busy || !pending) return;
  const { quality } = pending;
  pending = null;
  busy = true;
  sentNav = { ...navT };
  setStatus(quality === "full" ? "Rendering at full quality…" : "Rendering preview…", "busy");
  worker.postMessage({ type: "render", id: ++reqId, mode: state.mode, params: buildParams(), quality });
}

function schedulePreview(delay = 450) {
  saveHash();
  if (!$("auto").checked) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(() => requestRender(quality), delay);
}

// ------------------------------------------------------------------------------------------- params for Python

function buildParams() {
  const m = state.mode;
  const p = { ...state.params[m] };
  if (m === "vista") {
    const pal = PALETTES.vista[p._palette] || PALETTES.vista.paper;
    Object.assign(p, { paper: pal.paper, ink: pal.ink, accent: pal.accent, cam: state.cam, target: state.target });
    p.contours = p._accent_on ? [[p._accent_elev, "accent"]] : [];
    p.mist = p._mist_on ? p._mist_elev : null;
    Object.assign(p, breakupParams(p));
    p.haze_km = [p._haze_near_km, Math.max(p._haze_far_km, p._haze_near_km + 0.1)];
    p.halo = p._halo_on ? [state.halo[0], state.halo[1], p._halo_elev, p._halo_radius] : null;
    p.sun_pos = p.sun_disc > 0 && p._sun_free ? [p._sun_x, p._sun_y] : null;
    const [x, y, s] = [p._window_x, p._window_y, p._window_size];
    p.window = p._window === "circle" ? ["circle", x, y, s] : p._window === "rect" ? ["rect", x - s * 1.3, y - s * 0.75, x + s * 1.3, y + s * 0.75] : null;
  } else {
    const pal = PALETTES.strata[p._palette] || PALETTES.strata.dark;
    Object.assign(p, { background: pal.background, stroke: pal.stroke, center: state.center });
  }
  for (const k of Object.keys(p)) if (k.startsWith("_")) delete p[k];
  return p;
}

// ------------------------------------------------------------------------------------------- controls

function buildControls() {
  const box = $("controls");
  box.textContent = "";
  $("mode-blurb").textContent = MODES[state.mode].blurb;
  const p = state.params[state.mode];
  for (const [title, items] of MODES[state.mode].groups) {
    const group = document.createElement("details");
    group.open = ["Camera", "Light", "Tone", "Breakup", "Contours", "Paths", "Displace"].includes(title);
    group.innerHTML = `<summary>${title}</summary>`;
    for (const c of items) {
      const row = document.createElement("div");
      row.className = "ctl " + c.type;
      row.dataset.key = c.k;
      const id = `c-${state.mode}-${c.k}`;
      if (c.type === "check") {
        row.innerHTML = `<label><input type="checkbox" id="${id}"> <span>${labelOf(c)}</span></label>`;
        const el = row.querySelector("input");
        el.checked = !!p[c.k];
        el.onchange = () => { p[c.k] = el.checked; afterChange(); };
      } else if (c.type === "select") {
        row.innerHTML = `<label for="${id}">${labelOf(c)}</label><select id="${id}">${c.options.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select>`;
        const el = row.querySelector("select");
        el.value = p[c.k];
        el.onchange = () => { p[c.k] = el.value; afterChange(); };
      } else {
        row.innerHTML = `<label for="${id}">${labelOf(c)}<output></output></label><input type="range" id="${id}">`;
        const el = row.querySelector("input"), out = row.querySelector("output");
        setRange(c, el);
        syncRange(c, el, p[c.k]);
        el.oninput = () => { p[c.k] = c.unit ? fromDisplay(units, c.unit, +el.value) : +el.value; out.textContent = show(c, p[c.k]); afterChange(); };
      }
      group.appendChild(row);
    }
    box.appendChild(group);
  }
  refreshVisibility();
}

const labelOf = (c) => (c.unit ? c.label.replace("{u}", unitName(units, c.unit)) : c.label);

function setRange(c, el) {
  let { min, max } = c;
  if (c.elev) {
    min = dem ? Math.floor(dem.meta.min) : 0;
    max = dem ? Math.ceil(dem.meta.max) + (c.headroom || 0) : 5000;
  }
  Object.assign(el, c.unit ? displayRange(units, c.unit, min, max, c.step) : { min, max, step: c.step });
}

// v is the stored (metric) value; the slider and its readout are in display units
function syncRange(c, el, v) {
  el.value = c.unit ? toDisplay(units, c.unit, v) : v;
  el.closest(".ctl").querySelector("output").textContent = show(c, v);
}

function show(c, v) {
  if (c.unit === "m" && c.elev) return fmtLength(units, v);
  const step = c.unit ? niceStep(units, c.unit, c.step) : c.step;
  const decimals = (String(step).split(".")[1] || "").length;
  const n = c.unit ? toDisplay(units, c.unit, v) : Number(v);
  return c.unit ? n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) : n.toFixed(decimals);
}

function refreshVisibility() {
  const p = state.params[state.mode];
  for (const [, items] of MODES[state.mode].groups) {
    for (const c of items) {
      const row = document.querySelector(`.ctl[data-key="${c.k}"]`);
      if (row) row.hidden = c.show ? !c.show(p) : false;
    }
  }
}

function afterChange() {
  refreshVisibility();
  drawPlanner();
  schedulePreview();
}

// Elevation-based controls get their range from the terrain; pull values that fall outside it back inside.
function fitElevationControls() {
  if (!dem) return;
  const { min, max } = dem.meta, p = state.params.vista;
  const inside = (v) => v >= min && v <= max + 1500;
  if (!inside(p._mist_elev) || p._mist_elev > max) p._mist_elev = Math.round(min + 0.12 * (max - min));
  if (!inside(p._accent_elev) || p._accent_elev > max) p._accent_elev = Math.round(min + 0.6 * (max - min));
  if (!inside(p._halo_elev)) p._halo_elev = Math.round(max + 200);
}

// ------------------------------------------------------------------------------------------- terrain + presets

// pins: {cam, target, halo} as [lat, lon]; each is placed in the new area if it falls inside it.
function showAreaInfo() {
  if (!dem) return;
  const m = dem.meta;
  $("area-info").textContent = `${fmtDistance(units, m.width_m / 1000)} across · ${fmtLength(units, m.min)}–${fmtLength(units, m.max)} · ${fmtLength(units, m.mpp)} per sample · zoom ${m.zoom}`;
}

function setUnits(u) {
  units = u;
  try { localStorage.setItem("linedream-terrain/units", u); } catch {}
  for (const b of document.querySelectorAll("[data-units]")) b.setAttribute("aria-pressed", b.dataset.units === u ? "true" : "false");
  buildControls();
  showAreaInfo();
  updatePlannerInfo();
}

async function loadArea(area, { keepCamera = false, pins = null } = {}) {
  state.area = { ...area };
  setStatus("Loading elevation…", "busy");
  $("area-info").textContent = "Loading elevation tiles…";
  try {
    dem = await fetchDEM(area.lat, area.lon, area.zoom, area.size, (i, n) => { $("area-info").textContent = `Loading elevation tiles ${i}/${n}…`; });
  } catch (e) {
    setStatus("Could not load elevation: " + e.message, "err");
    return;
  }
  const m = dem.meta;
  showAreaInfo();
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  c.getContext("2d").putImageData(hillshade(dem.grid, m.size, m.mpp, 512), 0, 0);
  shadeImg = c;
  if (!keepCamera) {
    const fallback = { cam: [0.5, 0.93], target: [0.5, 0.45], halo: [0.5, 0.45] };
    for (const k of Object.keys(fallback)) {
      const uv = pins && pins[k] ? toUV(m, pins[k][0], pins[k][1]) : null;
      state[k] = uv && uv.every((x) => x >= 0 && x <= 1) ? uv : fallback[k];
    }
    state.center = [0.5, 0.5];
  }
  fitElevationControls();
  buildControls();
  drawPlanner();
  syncMap();
  sendDem();
  saveHash();
}

// Show a scene (a preset, an opened file or a link; see scene.mjs).
async function applyScene(sc, choice) {
  state.mode = sc.mode;
  state.preset = sc.name;
  state.params[sc.mode] = sc.params;
  Object.assign(state, { cam: sc.cam, target: sc.target, halo: sc.halo, center: sc.center });
  selectPreset(choice ?? choiceFor(sc.name));
  syncModeButtons();
  await loadArea(sc.area, { keepCamera: true });
}

const applyPreset = (i) => applyScene(parseScene(PRESETS[i]), String(i));

// The dropdown holds presets ("3") and My scenes ("my:0"); a scene that is neither selects nothing.
const storage = (() => { try { return window.localStorage; } catch { return null; } })();
let myScenes = listMyScenes(storage);

function choiceFor(name) {
  if (!name) return "";
  const m = myScenes.findIndex((s) => s.name === name);
  if (m >= 0) return `my:${m}`;
  const i = PRESETS.findIndex((p) => p.name === name);
  return i >= 0 ? String(i) : "";
}

function selectPreset(value) {
  $("preset").value = value;
  $("scene-delete").hidden = !value.startsWith("my:");
}

// ------------------------------------------------------------------------------------------- planner (top-down camera placement)

const planner = $("planner");
const handles = () => {
  if (state.mode === "strata") return { center: state.center };
  const h = { cam: state.cam, target: state.target };
  if (state.params.vista._halo_on) h.halo = state.halo;
  return h;
};

function drawPlanner() {
  const ctx = planner.getContext("2d");
  const W = planner.width, H = planner.height;
  ctx.clearRect(0, 0, W, H);
  if (!shadeImg) return;
  ctx.drawImage(shadeImg, 0, 0, W, H);
  const P = ([u, v]) => [u * W, v * H];
  const dpr = W / planner.clientWidth || 1;
  ctx.lineWidth = 1.5 * dpr;

  if (state.mode === "vista") {
    const p = state.params.vista;
    const [cx, cy] = P(state.cam), [tx, ty] = P(state.target);
    const yaw = Math.atan2(ty - cy, tx - cx), half = (p.fov * Math.PI) / 360, R = Math.hypot(W, H);
    ctx.fillStyle = "rgba(207, 74, 31, 0.13)";
    ctx.strokeStyle = "rgba(207, 74, 31, 0.6)";
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + R * Math.cos(yaw - half), cy + R * Math.sin(yaw - half));
    ctx.lineTo(cx + R * Math.cos(yaw + half), cy + R * Math.sin(yaw + half));
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.setLineDash([4 * dpr, 4 * dpr]);
    ctx.strokeStyle = "#1c1b18";
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(tx, ty); ctx.stroke();
    ctx.setLineDash([]);
    if (p._halo_on) dot(ctx, P(state.halo), 7 * dpr, "transparent", "#c98a12", 2.5 * dpr);
    dot(ctx, [tx, ty], 7 * dpr, "#fbf8f1", "#1c1b18", 2 * dpr);
    dot(ctx, [cx, cy], 7 * dpr, "#1c1b18", "#fbf8f1", 2 * dpr);
    compass(ctx, W, H, dpr, p.sun_az, p.sun_alt);
  } else {
    const paths = state.params.strata.paths;
    if (["radial", "spiral", "rings"].includes(paths)) dot(ctx, P(state.center), 7 * dpr, "#1c1b18", "#fbf8f1", 2 * dpr);
  }
  updatePlannerInfo();
}

function dot(ctx, [x, y], r, fill, stroke, w) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fillStyle = fill; ctx.fill();
  ctx.lineWidth = w; ctx.strokeStyle = stroke; ctx.stroke();
}

function compass(ctx, W, H, dpr, az, alt) {
  const r = 26 * dpr, x = W - r - 12 * dpr, y = r + 12 * dpr, a = (az * Math.PI) / 180;
  ctx.fillStyle = "rgba(251, 248, 241, 0.85)";
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = "rgba(28, 27, 24, 0.35)"; ctx.lineWidth = dpr; ctx.stroke();
  ctx.fillStyle = "#1c1b18";
  ctx.font = `${10 * dpr}px "JetBrains Mono", monospace`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText("N", x, y - r + 8 * dpr);
  const k = 1 - Math.min(alt, 85) / 110; // a high sun sits nearer the middle
  const sx = x + Math.sin(a) * r * 0.8 * k, sy = y - Math.cos(a) * r * 0.8 * k;
  ctx.strokeStyle = "#c98a12"; ctx.lineWidth = 2 * dpr;
  ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(x, y); ctx.stroke();
  dot(ctx, [sx, sy], 5 * dpr, "#ffcb6b", "#c98a12", 1.5 * dpr);
}

function updatePlannerInfo() {
  if (!dem) return;
  const m = dem.meta, el = (uv) => sample(dem.grid, m.size, uv[0], uv[1]);
  if (state.mode === "vista") {
    const p = state.params.vista;
    const dist = Math.hypot(state.target[0] - state.cam[0], state.target[1] - state.cam[1]) * m.width_m;
    const edge = Math.min(...state.cam, ...state.target.map((x) => x), 1 - Math.max(...state.cam, ...state.target));
    $("planner-info").textContent = `Eye ${fmtLength(units, el(state.cam) + p.eye)} (ground ${fmtLength(units, el(state.cam))}) · aim ${fmtLength(units, el(state.target) + p.target_eye)} · ${fmtDistance(units, dist / 1000)} away`
      + (edge < 0.04 ? " · at the edge of the loaded area: zoom the map out and “Use this view” to go farther, then “Frame eye + aim”" : "");
  } else {
    $("planner-info").textContent = `Strata draws the whole map; the dot is the centre for radial, spiral and ring paths.`;
  }
}

function plannerUV(e) {
  const r = planner.getBoundingClientRect();
  return [Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), Math.min(1, Math.max(0, (e.clientY - r.top) / r.height))];
}

let dragging = null;
planner.addEventListener("pointerdown", (e) => {
  if (!dem) return;
  const uv = plannerUV(e), r = planner.getBoundingClientRect();
  let best = null, bestD = 16 / r.width;
  for (const [k, h] of Object.entries(handles())) {
    const d = Math.hypot(h[0] - uv[0], h[1] - uv[1]);
    if (d < bestD) { best = k; bestD = d; }
  }
  dragging = best || (state.mode === "strata" ? "center" : placing === "halo" && !state.params.vista._halo_on ? "cam" : placing);
  state[dragging] = uv;
  planner.setPointerCapture(e.pointerId);
  drawPlanner();
});
planner.addEventListener("pointermove", (e) => {
  if (!dragging) return;
  state[dragging] = plannerUV(e);
  drawPlanner();
  syncMapOverlay();
});
const endDrag = () => { if (dragging) { dragging = null; syncMapOverlay(); schedulePreview(150); } };
planner.addEventListener("pointerup", endDrag);
planner.addEventListener("pointercancel", endDrag);

for (const b of document.querySelectorAll("[data-place]")) {
  b.onclick = () => {
    placing = b.dataset.place;
    for (const o of document.querySelectorAll("[data-place]")) o.setAttribute("aria-pressed", o === b ? "true" : "false");
  };
}

function resizePlanner() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = planner.clientWidth;
  planner.width = planner.height = Math.round(w * dpr);
  drawPlanner();
}
new ResizeObserver(resizePlanner).observe(planner);

// ------------------------------------------------------------------------------------------- navigation
// Walk the camera through the scene with the Move and Look gizmos under the drawing, or the keyboard. Moves carry the eye and the aim
// together and fly level, so the view keeps its altitude, pitch and heading (the eye only rises where the ground comes up
// to meet it); steps scale with how far away the aim is (moves) and how high the eye is (up/down). The current drawing is shifted and scaled at once as a rough stand-in until the new preview
// lands. Walking off the loaded area loads a new one around the camera.

const NAV_KEYS = {
  w: "forward", arrowup: "forward", s: "back", arrowdown: "back", a: "left", d: "right",
  arrowleft: "turn-left", arrowright: "turn-right", e: "up", q: "down", r: "tilt-up", f: "tilt-down",
};

function setParam(k, v) {
  state.params.vista[k] = v;
  const el = $(`c-vista-${k}`), c = MODES.vista.groups.flatMap(([, items]) => items).find((c) => c.k === k);
  if (!el || !c) return;
  if (c.type === "check") el.checked = !!v;
  else if (c.type === "select") el.value = v;
  else syncRange(c, el, v);
}

// Aim at the highest summit in view and pick lens, light and haze for it (see compose.mjs).
function composeView() {
  if (state.mode !== "vista" || !dem) return;
  const c = compose({ grid: dem.grid, size: dem.meta.size, width_m: dem.meta.width_m }, state, state.params.vista);
  if (!c) { setStatus("Nothing stands out from here: move the eye or aim somewhere else", "err"); return; }
  state.target = c.target;
  for (const [k, v] of Object.entries(c.params)) setParam(k, v);
  state.preset = "";
  selectPreset("");
  refreshVisibility();
  drawPlanner();
  syncMapOverlay();
  schedulePreview(0);
  setStatus(`Composed on the summit at ${fmtLength(units, c.peak.z)}, ${fmtDistance(units, c.peak.d / 1000)} away`, "ok");
}

function applyNavTransform(animate = true) {
  const img = $("drawing");
  img.style.transition = animate ? "transform 160ms ease-out" : "none";
  img.style.transform = navT.s === 1 && !navT.x && !navT.y ? "" : `translate(${navT.x * 100}%, ${navT.y * 100}%) scale(${navT.s})`;
}

// screen effect of a move, applied after the ones already showing: scale about the centre, then shift
function navShift(scale, dx, dy) {
  navT = { s: navT.s * scale, x: navT.x * scale + dx, y: navT.y * scale + dy };
  applyNavTransform();
}

function navigate(action, big = false) {
  if (state.mode !== "vista" || !dem || navLoading) return;
  const p = state.params.vista, m = dem.meta, W = m.width_m;
  const ground = (uv) => sample(dem.grid, m.size, uv[0], uv[1]);
  const [cu, cv] = state.cam, [tu, tv] = state.target;
  const D = Math.max(Math.hypot(tu - cu, tv - cv) * W, 1);                 // metres to the aim point
  const fx = (tu - cu) * W / D, fy = (tv - cv) * W / D;                      // heading, unit vector in metres
  const eyeAbs = ground(state.cam) + p.eye, aimAbs = ground(state.target) + p.target_eye;
  const tanH = Math.tan((p.fov * Math.PI) / 360), tanV = tanH * 10 / 16;   // the drawing is 16:10
  const k = big ? 4 : 1;
  let cam = state.cam, target = state.target, eye = p.eye, aim = aimAbs;

  if (["forward", "back", "left", "right"].includes(action)) {
    const step = Math.max(20, 0.08 * D) * k;
    const [mx, my] = { forward: [fx, fy], back: [-fx, -fy], left: [fy, -fx], right: [-fy, fx] }[action];
    cam = [cu + (mx * step) / W, cv + (my * step) / W];
    target = [tu + (mx * step) / W, tv + (my * step) / W];
    // fly level: same altitude, unless the ground comes up to meet the eye
    const lift = Math.max(0, Math.min(p.eye, 2) - (eyeAbs - ground(cam)));
    eye = Math.min(3000, Math.round(eyeAbs + lift - ground(cam)));
    aim += lift;
    if (action === "forward" || action === "back") { const d = action === "forward" ? step : -step; navShift(D / Math.max(D - d, D * 0.2), 0, 0); }
    else navShift(1, (action === "left" ? 1 : -1) * step / (2 * D * tanH), 0);
  } else if (action === "turn-left" || action === "turn-right") {
    const a = (action === "turn-left" ? -1 : 1) * Math.max(2, p.fov / 6) * (big ? 3 : 1) * Math.PI / 180;
    const [rx, ry] = [fx * Math.cos(a) - fy * Math.sin(a), fx * Math.sin(a) + fy * Math.cos(a)];
    target = [cu + (rx * D) / W, cv + (ry * D) / W];
    navShift(1, -Math.tan(a) / (2 * tanH), 0);
  } else if (action === "up" || action === "down") {
    const f = 1.4 ** (big ? 3 : 1);
    eye = Math.min(3000, Math.max(0, action === "up" ? (p.eye + 10) * f - 10 : (p.eye + 10) / f - 10));
    eye = Math.round(eye);
    aim += eye - p.eye;
    navShift(1, 0, (eye - p.eye) / (2 * D * tanV));
  } else if (action === "tilt-up" || action === "tilt-down") {
    const pitch = Math.atan((aimAbs - eyeAbs) / D), d = (action === "tilt-up" ? 1 : -1) * 3 * (big ? 3 : 1) * Math.PI / 180;
    const next = Math.max(-1.2, Math.min(1.2, pitch + d));
    aim = eyeAbs + D * Math.tan(next);
    navShift(1, 0, (Math.tan(next) - Math.tan(pitch)) / (2 * tanV));
  }

  state.cam = cam; state.target = target;
  state.preset = "";
  selectPreset("");
  if (eye !== p.eye) setParam("eye", eye);
  const inside = (uv) => uv.every((x) => x >= 0.002 && x <= 0.998);
  if (!inside(cam) || !inside(target)) {
    // walked off the loaded terrain: load a new area around the camera (pins work outside 0..1), then restore the
    // aim height, which is measured from the ground under the aim point
    const absEye = eyeAbs + (action === "up" || action === "down" ? eye - p.eye : 0);
    navLoading = true;
    frameView(1.0).then(() => {
      navLoading = false;
      setParam("eye", Math.min(3000, Math.max(Math.min(p.eye, 2), Math.round(absEye - sample(dem.grid, dem.meta.size, ...state.cam)))));
      setParam("target_eye", Math.max(-3000, Math.min(3000, Math.round(aim - sample(dem.grid, dem.meta.size, ...state.target)))));
      drawPlanner();
    });
    return;
  }
  setParam("target_eye", Math.max(-3000, Math.min(3000, Math.round(aim - ground(target)))));
  drawPlanner();
  syncMapOverlay();
  schedulePreview(350);
}

const navHint = $("nav-hint"), navHintIdle = navHint.textContent;
for (const b of document.querySelectorAll("[data-nav]")) {
  let timer = null;
  for (const ev of ["pointerenter", "focus"]) b.addEventListener(ev, () => { navHint.textContent = b.dataset.label; });
  for (const ev of ["pointerleave", "blur"]) b.addEventListener(ev, () => { navHint.textContent = navHintIdle; });
  const stop = () => { clearInterval(timer); timer = null; };
  b.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    navigate(b.dataset.nav, e.shiftKey);
    stop();
    timer = setInterval(() => navigate(b.dataset.nav, e.shiftKey), 260);
  });
  for (const ev of ["pointerup", "pointerleave", "pointercancel"]) b.addEventListener(ev, stop);
  b.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigate(b.dataset.nav, e.shiftKey); } });
}
document.addEventListener("keydown", (e) => {
  if (e.metaKey || e.ctrlKey || e.altKey || e.target.closest("input, select, textarea, .leaflet-container")) return;
  const action = NAV_KEYS[e.key.toLowerCase()];
  if (!action || state.mode !== "vista") return;
  e.preventDefault();
  navigate(action, e.shiftKey);
});

// ------------------------------------------------------------------------------------------- map (Leaflet, optional)

let map = null, areaRect = null, sightLine = null;

function initMap() {
  if (!window.L) {
    $("map").innerHTML = `<p class="map-missing">The map didn't load. Presets still work; you can also type a place below.</p>`;
    return;
  }
  map = L.map("map", { zoomControl: true, attributionControl: true, worldCopyJump: true }).setView([42.78, -109.21], 11);
  L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    maxZoom: 17, subdomains: "abc",
    attribution: 'Map data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, SRTM · style © <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)',
  }).addTo(map);
}

function syncMap() {
  if (!map || !dem) return;
  const m = dem.meta;
  const b = [toLatLon(m, 0, 1), toLatLon(m, 1, 0)];
  if (areaRect) areaRect.setBounds(b);
  else areaRect = L.rectangle(b, { color: "#cf4a1f", weight: 1.5, fill: false, interactive: false }).addTo(map);
  map.fitBounds(b, { padding: [12, 12] });
  syncMapOverlay();
}

function syncMapOverlay() {
  if (!map || !dem) return;
  if (state.mode !== "vista") { if (sightLine) { sightLine.remove(); sightLine = null; } return; }
  const pts = [toLatLon(dem.meta, ...state.cam), toLatLon(dem.meta, ...state.target)];
  if (sightLine) sightLine.setLatLngs(pts);
  else sightLine = L.polyline(pts, { color: "#1c1b18", weight: 2, dashArray: "4 4", interactive: false }).addTo(map);
}

function currentPins() {
  if (!dem) return null;
  const ll = (uv) => toLatLon(dem.meta, uv[0], uv[1]);
  return { cam: ll(state.cam), target: ll(state.target), halo: ll(state.halo) };
}

// Load an area that just fits the eye, the aim point and the ground 25% beyond it, at the finest zoom that does.
function frameView(beyond = 0.25) {
  if (!dem) return Promise.resolve();
  const pins = currentPins(), { cam, target } = pins;
  const back = [target[0] + (target[0] - cam[0]) * beyond, target[1] + (target[1] - cam[1]) * beyond];
  const lat = (cam[0] + back[0]) / 2, lon = (cam[1] + back[1]) / 2;
  const span = Math.max(Math.abs(back[1] - cam[1]) * 111320 * Math.cos((lat * Math.PI) / 180), Math.abs(back[0] - cam[0]) * 110540) * 1.15 + 1500;
  const size = +$("area-size").value;
  const zoom = Math.max(4, Math.min(MAX_ZOOM, Math.floor(Math.log2((size * metersPerPixel(lat, 0)) / span))));
  state.preset = "";
  selectPreset("");
  return loadArea({ lat, lon, zoom, size }, { pins });
}

function useMapView() {
  if (!map) return;
  const size = +$("area-size").value;
  const c = map.getCenter();
  const widthPx = $("map").clientWidth || 360;
  const zoom = Math.max(4, Math.min(MAX_ZOOM, Math.round(map.getZoom() + Math.log2(size / widthPx))));
  state.preset = "";
  selectPreset("");
  loadArea({ lat: c.lat, lon: c.lng, zoom, size }, { pins: currentPins() });
}

async function search() {
  const q = $("search").value.trim();
  if (!q) return;
  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(q)}`, { headers: { Accept: "application/json" } });
    const hits = await res.json();
    if (!hits.length) { $("area-info").textContent = `Nothing found for “${q}”.`; return; }
    const { lat, lon, boundingbox: bb } = hits[0];
    if (map) {
      if (bb) map.fitBounds([[+bb[0], +bb[2]], [+bb[1], +bb[3]]], { maxZoom: 13 });
      else map.setView([+lat, +lon], 12);
      $("area-info").textContent = `Found ${hits[0].display_name}. Frame it, then “Use this view”.`;
    } else {
      loadArea({ lat: +lat, lon: +lon, zoom: 12, size: +$("area-size").value });
    }
  } catch (e) {
    $("area-info").textContent = "Search failed: " + e.message;
  }
}

// ------------------------------------------------------------------------------------------- output

function showSvg(svg, quality) {
  lastSvg = svg; lastQuality = quality;
  if (lastUrl) URL.revokeObjectURL(lastUrl);
  lastUrl = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
  $("drawing").src = lastUrl;
  // the new drawing already includes the moves made before it was requested; keep showing only the later ones
  const s = navT.s / sentNav.s;
  navT = { s, x: navT.x - s * sentNav.x, y: navT.y - s * sentNav.y };
  sentNav = { s: 1, x: 0, y: 0 };
  applyNavTransform(false);
  $("drawing").hidden = false;
  $("empty").hidden = true;
  $("download").disabled = false;
  $("download").textContent = quality === "full" ? "Download SVG" : "Download SVG (preview)";
}

function download() {
  if (!lastSvg) return;
  const name = (state.preset || `${state.mode}-${state.area.lat.toFixed(3)}-${state.area.lon.toFixed(3)}`).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const a = document.createElement("a");
  a.href = lastUrl;
  a.download = `linedream-${name}-${lastQuality}.svg`;
  a.click();
}

// The status line also drives the overlay on the drawing: anything "busy" blurs the sheet and shows a spinner, with a
// running clock while a render is in progress. The nav gizmos sit outside it, so moves keep queueing.
let busySince = 0, busyTimer = null;
function setStatus(text, kind) {
  const el = $("status");
  el.textContent = text;
  el.className = kind || "";
  const busy = kind === "busy";
  $("sheet").classList.toggle("is-busy", busy);
  clearInterval(busyTimer);
  if (!busy) return;
  const rendering = text.startsWith("Rendering");
  busySince = performance.now();
  const tick = () => { $("busy-label").textContent = rendering ? `${text} ${((performance.now() - busySince) / 1000).toFixed(1)} s` : text; };
  tick();
  if (rendering) busyTimer = setInterval(tick, 100);
  $("busy-note").textContent = workerReady ? "" : "Python and the scientific stack: about 60 MB the first time, cached after that.";
}

// ------------------------------------------------------------------------------------------- URL hash

function saveHash() {
  if (!state.area) return;
  history.replaceState(null, "", encodeHash(sceneFromState(state)));
}

// ------------------------------------------------------------------------------------------- saving and opening scenes
// No server: a scene saves as a small JSON file (the same shape as the presets in schema.mjs) and opens again from
// the file picker or by dropping it on the drawing. The link in the address bar holds the same scene.

function keepScene() {
  if (!state.area) return;
  const name = (prompt("Save to My scenes as", state.preset || "") ?? "").trim();
  if (!name) return;
  if (myScenes.some((s) => s.name === name) && !confirm(`Replace “${name}” in My scenes?`)) return;
  try {
    myScenes = saveMyScene(storage, sceneFromState(state, name));
  } catch {
    setStatus("This browser won't keep scenes (private window or storage blocked): use Download instead", "err");
    return;
  }
  state.preset = name;
  populatePresets();
  selectPreset(choiceFor(name));
  saveHash();
  setStatus(`Saved “${name}” to My scenes`, "ok");
}

function deleteScene() {
  const v = $("preset").value;
  if (!v.startsWith("my:")) return;
  const name = myScenes[+v.slice(3)].name;
  if (!confirm(`Delete “${name}” from My scenes?`)) return;
  try { myScenes = deleteMyScene(storage, name); } catch { setStatus("Couldn't change My scenes in this browser", "err"); return; }
  populatePresets();
  selectPreset("");
  setStatus(`Deleted “${name}”`, "ok");
}

function downloadScene() {
  if (!state.area) return;
  const name = prompt("Name this scene", state.preset || "");
  if (name === null) return;
  const blob = new Blob([JSON.stringify(sceneFromState(state, name.trim()), null, 2) + "\n"], { type: "application/json" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: sceneFilename(name) });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

async function openScene(file) {
  let sc;
  try {
    sc = parseScene(JSON.parse(await file.text()));
  } catch (e) {
    setStatus(`Couldn't open ${file.name}: ${e instanceof SyntaxError ? "not valid JSON" : e.message}`, "err");
    return;
  }
  if (sc.warnings.length) console.warn(`${file.name}:`, sc.warnings);
  await applyScene(sc);
  if (sc.warnings.length) setStatus(`Opened ${file.name} with ${sc.warnings.length} setting(s) fixed (details in the console)`, "ok");
}

async function copyLink() {
  saveHash();
  try {
    await navigator.clipboard.writeText(location.href);
    setStatus("Link copied: it opens this exact scene", "ok");
  } catch {
    setStatus("Couldn't copy; the address bar has the link", "err");
  }
}

// ------------------------------------------------------------------------------------------- wiring

function syncModeButtons() {
  for (const b of document.querySelectorAll("[data-mode]")) b.setAttribute("aria-pressed", b.dataset.mode === state.mode ? "true" : "false");
  $("vista-tools").hidden = state.mode !== "vista";
  $("frame-row").hidden = $("compose-row").hidden = state.mode !== "vista";
  $("nav").hidden = state.mode !== "vista";
  $("sheet").classList.toggle("square", state.mode === "strata");
}

function populatePresets() {
  const sel = $("preset");
  const option = (value, text) => Object.assign(document.createElement("option"), { value, textContent: text });
  const group = (label, options) => { const g = Object.assign(document.createElement("optgroup"), { label }); g.append(...options); return g; };
  sel.replaceChildren(option("", "Presets…"));
  if (myScenes.length) sel.append(group("My scenes", myScenes.map((s, i) => option(`my:${i}`, s.name))));
  const groups = { vista: "Vista (perspective)", strata: "Strata (top-down / oblique)" };
  for (const [m, label] of Object.entries(groups))
    sel.append(group(label, PRESETS.flatMap((p, i) => (p.mode === m ? [option(String(i), p.name)] : []))));
}

for (const b of document.querySelectorAll("[data-mode]")) {
  b.onclick = () => {
    state.mode = b.dataset.mode;
    state.preset = "";
    selectPreset("");
    syncModeButtons();
    buildControls();
    drawPlanner();
    syncMapOverlay();
    schedulePreview(0);
  };
}
$("preset").onchange = (e) => {
  const v = e.target.value;
  if (v.startsWith("my:")) applyScene(parseScene(myScenes[+v.slice(3)]), v);
  else if (v !== "") applyPreset(+v);
  else selectPreset("");
};
function setQuality(q) {
  quality = q;
  for (const b of document.querySelectorAll("[data-quality]")) b.setAttribute("aria-pressed", b.dataset.quality === q ? "true" : "false");
  try { localStorage.setItem("linedream-terrain/quality", q); } catch {}
}
for (const b of document.querySelectorAll("[data-quality]")) b.onclick = () => { setQuality(b.dataset.quality); schedulePreview(0); };
setQuality(quality);
$("render").onclick = () => requestRender(quality);
$("auto").onchange = () => { $("render").hidden = $("auto").checked; if ($("auto").checked) schedulePreview(0); };
$("download").onclick = download;
$("use-view").onclick = useMapView;
$("frame-view").onclick = () => frameView();
$("compose").onclick = composeView;
for (const b of document.querySelectorAll("[data-units]")) b.onclick = () => setUnits(b.dataset.units);
for (const b of document.querySelectorAll("[data-units]")) b.setAttribute("aria-pressed", b.dataset.units === units ? "true" : "false");
$("scene-save").onclick = keepScene;
$("scene-delete").onclick = deleteScene;
$("scene-download").onclick = downloadScene;
$("scene-open").onclick = () => $("scene-file").click();
$("scene-file").onchange = (e) => { const f = e.target.files[0]; e.target.value = ""; if (f) openScene(f); };
$("scene-link").onclick = copyLink;
$("sheet").addEventListener("dragover", (e) => { if ([...e.dataTransfer.items].some((i) => i.kind === "file")) { e.preventDefault(); $("sheet").classList.add("drop"); } });
$("sheet").addEventListener("dragleave", () => $("sheet").classList.remove("drop"));
$("sheet").addEventListener("drop", (e) => {
  e.preventDefault();
  $("sheet").classList.remove("drop");
  const f = e.dataTransfer.files[0];
  if (f) openScene(f);
});
$("search-go").onclick = search;
$("search").onkeydown = (e) => { if (e.key === "Enter") search(); };
$("reset").onclick = () => { state.params[state.mode] = defaults(state.mode); fitElevationControls(); buildControls(); afterChange(); };

populatePresets();
initMap();
startWorker();

const saved = location.hash.length > 1 ? decodeHash(location.hash) : null;
if (saved) applyScene(saved);
else applyPreset(0);
