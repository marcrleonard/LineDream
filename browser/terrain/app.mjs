// LineDream Terrain: pick a place, stand somewhere, render it as line art. The renderers are the Python terrain
// experiments (py/vista.py, py/strata.py) running in Pyodide in a worker; this file is the UI around them.
//
// Query parameters, all optional:
//   ?pyodide=<url>  a Pyodide distribution to load from (default: the jsDelivr CDN)
//   ?wheel=<url>    a LineDream wheel to install (the website build sets data-wheel on <html>; otherwise PyPI)
// The whole scene (place, camera, mode, every parameter) lives in the URL hash, so a link reproduces a drawing.
import { MODES, PALETTES, PRESETS, defaults } from "./schema.mjs";
import { fetchDEM, hillshade, metersPerPixel, sample, toLatLon, toUV, MAX_ZOOM } from "./tiles.mjs";

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
let placing = "cam";

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
  setStatus(quality === "full" ? "Rendering at full quality…" : "Rendering preview…", "busy");
  worker.postMessage({ type: "render", id: ++reqId, mode: state.mode, params: buildParams(), quality });
}

function schedulePreview(delay = 450) {
  saveHash();
  if (!$("auto").checked) return;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(() => requestRender("preview"), delay);
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
    group.open = ["Camera", "Light", "Tone", "Contours", "Paths", "Displace"].includes(title);
    group.innerHTML = `<summary>${title}</summary>`;
    for (const c of items) {
      const row = document.createElement("div");
      row.className = "ctl " + c.type;
      row.dataset.key = c.k;
      const id = `c-${state.mode}-${c.k}`;
      if (c.type === "check") {
        row.innerHTML = `<label><input type="checkbox" id="${id}"> <span>${c.label}</span></label>`;
        const el = row.querySelector("input");
        el.checked = !!p[c.k];
        el.onchange = () => { p[c.k] = el.checked; afterChange(); };
      } else if (c.type === "select") {
        row.innerHTML = `<label for="${id}">${c.label}</label><select id="${id}">${c.options.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select>`;
        const el = row.querySelector("select");
        el.value = p[c.k];
        el.onchange = () => { p[c.k] = el.value; afterChange(); };
      } else {
        row.innerHTML = `<label for="${id}">${c.label}<output></output></label><input type="range" id="${id}">`;
        const el = row.querySelector("input"), out = row.querySelector("output");
        setRange(c, el);
        el.value = p[c.k];
        out.textContent = show(c, p[c.k]);
        el.oninput = () => { p[c.k] = +el.value; out.textContent = show(c, +el.value); afterChange(); };
      }
      group.appendChild(row);
    }
    box.appendChild(group);
  }
  refreshVisibility();
}

function setRange(c, el) {
  let { min, max } = c;
  if (c.elev) {
    min = dem ? Math.floor(dem.meta.min) : 0;
    max = dem ? Math.ceil(dem.meta.max) + (c.headroom || 0) : 5000;
  }
  Object.assign(el, { min, max, step: c.step });
}

function show(c, v) {
  if (c.elev) return `${fmt(v)} m`;
  const decimals = (String(c.step).split(".")[1] || "").length;
  return Number(v).toFixed(decimals);
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
  $("area-info").textContent = `${(m.width_m / 1000).toFixed(1)} km across · ${fmt(m.min)}–${fmt(m.max)} m · ${m.mpp.toFixed(0)} m per sample · zoom ${m.zoom}`;
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

async function applyPreset(i) {
  const pr = PRESETS[i];
  state.mode = pr.mode;
  state.preset = pr.name;
  state.params[pr.mode] = { ...defaults(pr.mode), ...pr.params };
  if (pr.mode === "vista") {
    // older presets give haze in map widths; turn that into km for this preset's area
    const widthKm = (metersPerPixel(pr.area.lat, pr.area.zoom) * pr.area.size) / 1000, p = state.params.vista;
    if (pr.params._haze_near_km === undefined) p._haze_near_km = (pr.params.haze_near ?? 0.1) * widthKm;
    if (pr.params._haze_far_km === undefined) p._haze_far_km = (pr.params.haze_far ?? 1.0) * widthKm;
    delete p.haze_near; delete p.haze_far;
  }
  syncModeButtons();
  const meta = { ...pr.area, ...gridOrigin(pr.area) };
  const uv = (ll) => toUV(meta, ll[0], ll[1]);
  state.cam = pr.cam ? uv(pr.cam) : [0.5, 0.93];
  state.target = pr.target ? uv(pr.target) : [0.5, 0.45];
  state.halo = pr.halo ? uv(pr.halo) : state.target.slice();
  state.center = [0.5, 0.5];
  await loadArea(pr.area, { keepCamera: true });
}

function gridOrigin(area) {
  // same rounding as tiles.fetchDEM, so presets can be pinned before the tiles arrive
  const n = 2 ** area.zoom * 256, latR = (area.lat * Math.PI) / 180;
  const cx = ((area.lon + 180) / 360) * n, cy = ((1 - Math.log(Math.tan(latR) + 1 / Math.cos(latR)) / Math.PI) / 2) * n;
  return { x0: Math.floor(cx - area.size / 2), y0: Math.floor(cy - area.size / 2) };
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
    $("planner-info").textContent = `Eye ${fmt(el(state.cam) + p.eye)} m (ground ${fmt(el(state.cam))} m) · aim ${fmt(el(state.target) + p.target_eye)} m · ${(dist / 1000).toFixed(1)} km away`
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
function frameView() {
  if (!dem) return;
  const pins = currentPins(), { cam, target } = pins;
  const back = [target[0] + (target[0] - cam[0]) * 0.25, target[1] + (target[1] - cam[1]) * 0.25];
  const lat = (cam[0] + back[0]) / 2, lon = (cam[1] + back[1]) / 2;
  const span = Math.max(Math.abs(back[1] - cam[1]) * 111320 * Math.cos((lat * Math.PI) / 180), Math.abs(back[0] - cam[0]) * 110540) * 1.15 + 1500;
  const size = +$("area-size").value;
  const zoom = Math.max(4, Math.min(MAX_ZOOM, Math.floor(Math.log2((size * metersPerPixel(lat, 0)) / span))));
  state.preset = "";
  $("preset").value = "";
  loadArea({ lat, lon, zoom, size }, { pins });
}

function useMapView() {
  if (!map) return;
  const size = +$("area-size").value;
  const c = map.getCenter();
  const widthPx = $("map").clientWidth || 360;
  const zoom = Math.max(4, Math.min(MAX_ZOOM, Math.round(map.getZoom() + Math.log2(size / widthPx))));
  state.preset = "";
  $("preset").value = "";
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
  $("drawing").hidden = false;
  $("empty").hidden = true;
  $("download").disabled = false;
  $("download").textContent = quality === "full" ? "Download SVG" : "Download preview SVG";
}

function download() {
  if (!lastSvg) return;
  const name = (state.preset || `${state.mode}-${state.area.lat.toFixed(3)}-${state.area.lon.toFixed(3)}`).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const a = document.createElement("a");
  a.href = lastUrl;
  a.download = `linedream-${name}-${lastQuality}.svg`;
  a.click();
}

function setStatus(text, kind) {
  const el = $("status");
  el.textContent = text;
  el.className = kind || "";
}

// ------------------------------------------------------------------------------------------- URL hash

function saveHash() {
  if (!state.area) return;
  const s = { m: state.mode, a: state.area, c: state.cam, t: state.target, h: state.halo, ce: state.center, p: state.params[state.mode], n: state.preset };
  history.replaceState(null, "", "#" + encodeURIComponent(JSON.stringify(s)));
}

function readHash() {
  try {
    const s = JSON.parse(decodeURIComponent(location.hash.slice(1)));
    if (!s.a || !MODES[s.m]) return null;
    return s;
  } catch { return null; }
}

// ------------------------------------------------------------------------------------------- wiring

function syncModeButtons() {
  for (const b of document.querySelectorAll("[data-mode]")) b.setAttribute("aria-pressed", b.dataset.mode === state.mode ? "true" : "false");
  $("vista-tools").hidden = state.mode !== "vista";
  $("frame-row").hidden = state.mode !== "vista";
  $("sheet").classList.toggle("square", state.mode === "strata");
}

function populatePresets() {
  const sel = $("preset");
  const groups = { vista: "Vista (perspective)", strata: "Strata (top-down / oblique)" };
  sel.innerHTML = `<option value="">Presets…</option>` + Object.entries(groups).map(([m, label]) =>
    `<optgroup label="${label}">${PRESETS.map((p, i) => (p.mode === m ? `<option value="${i}">${p.name}</option>` : "")).join("")}</optgroup>`).join("");
}

for (const b of document.querySelectorAll("[data-mode]")) {
  b.onclick = () => {
    state.mode = b.dataset.mode;
    state.preset = "";
    $("preset").value = "";
    syncModeButtons();
    buildControls();
    drawPlanner();
    syncMapOverlay();
    schedulePreview(0);
  };
}
$("preset").onchange = (e) => { if (e.target.value !== "") applyPreset(+e.target.value); };
$("render-full").onclick = () => requestRender("full");
$("render-preview").onclick = () => requestRender("preview");
$("auto").onchange = () => { if ($("auto").checked) schedulePreview(0); };
$("download").onclick = download;
$("use-view").onclick = useMapView;
$("frame-view").onclick = frameView;
$("search-go").onclick = search;
$("search").onkeydown = (e) => { if (e.key === "Enter") search(); };
$("reset").onclick = () => { state.params[state.mode] = defaults(state.mode); fitElevationControls(); buildControls(); afterChange(); };

populatePresets();
initMap();
startWorker();

const saved = readHash();
if (saved) {
  state.mode = saved.m;
  state.params[saved.m] = { ...defaults(saved.m), ...saved.p };
  Object.assign(state, { cam: saved.c, target: saved.t, halo: saved.h || saved.t, center: saved.ce || [0.5, 0.5], preset: saved.n || "" });
  syncModeButtons();
  loadArea(saved.a, { keepCamera: true });
} else {
  $("preset").value = "0";
  applyPreset(0);
}
