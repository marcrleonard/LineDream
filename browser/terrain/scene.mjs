// One scene format for presets, saved files and the URL hash: the area to load, where the eye, aim point, halo and
// strata centre are (as lat/lon, so they don't depend on how the area's grid happens to be rounded), the renderer and
// its parameters. A preset in schema.mjs is a scene without the format/version header; a saved file is a preset.
// No DOM in here, so it runs (and is tested) under Node: see test/scene.test.mjs.
import { MODES, defaults } from "./schema.mjs";
import { gridOrigin, metersPerPixel, toLatLon, toUV, MAX_ZOOM } from "./tiles.mjs";

export const FORMAT = "linedream-terrain-scene";
export const VERSION = 1;
export const SIZES = [512, 768, 1024];
export const DEFAULT_UV = { cam: [0.5, 0.93], target: [0.5, 0.45], center: [0.5, 0.5] };

const controls = (mode) => MODES[mode].groups.flatMap(([, items]) => items);
const round6 = (x) => Math.round(x * 1e6) / 1e6;
const isPoint = (p) => Array.isArray(p) && p.length === 2 && p.every((x) => typeof x === "number" && Number.isFinite(x));
const scalar = (v) => (typeof v === "number" && Number.isFinite(v)) || typeof v === "boolean" || (typeof v === "string" && v.length <= 200);

export const areaMeta = (area) => ({ ...area, ...gridOrigin(area) });
export const areaWidthKm = (area) => (metersPerPixel(area.lat, area.zoom) * area.size) / 1000;

// Parameters from anywhere (a preset, a file, a link) made safe for the UI: every control present and of its type,
// ranges clamped (except elevations, whose range comes from the terrain), unknown selects reset. Extra scalar keys
// pass through, since the Python renderers accept parameters the UI doesn't show (e.g. contour_above). Vista haze
// given in map widths (haze_near / haze_far, as the original renders were tuned) becomes km for this area.
export function sanitizeParams(mode, raw, area) {
  const warnings = [];
  const p = defaults(mode), src = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  if (raw !== undefined && src !== raw) warnings.push("params is not an object; using defaults");
  const known = new Set();
  for (const c of controls(mode)) {
    known.add(c.k);
    if (!(c.k in src)) continue;
    const v = src[c.k];
    if (c.type === "check") {
      if (typeof v === "boolean") p[c.k] = v;
      else warnings.push(`${c.k}: expected true/false`);
    } else if (c.type === "select") {
      const opt = c.options.find(([o]) => String(o) === String(v));
      if (opt) p[c.k] = opt[0];
      else warnings.push(`${c.k}: unknown option ${JSON.stringify(v)}`);
    } else {
      const n = typeof v === "number" ? v : typeof v === "string" && v.trim() !== "" ? Number(v) : NaN;
      if (!Number.isFinite(n)) { warnings.push(`${c.k}: not a number`); continue; }
      const clamped = c.elev ? n : Math.min(c.max, Math.max(c.min, n));
      if (clamped !== n) warnings.push(`${c.k}: ${n} is outside ${c.min}–${c.max}`);
      p[c.k] = clamped;
    }
  }
  if (mode === "vista") {
    const w = area ? areaWidthKm(area) : null;
    for (const [mw, km, def] of [["haze_near", "_haze_near_km", 0.1], ["haze_far", "_haze_far_km", 1.0]]) {
      known.add(mw);
      if (!(km in src) && w !== null) p[km] = (typeof src[mw] === "number" && Number.isFinite(src[mw]) ? src[mw] : def) * w;
    }
  }
  for (const [k, v] of Object.entries(src)) {
    if (known.has(k)) continue;
    if (scalar(v) && !k.startsWith("_")) p[k] = v;
    else warnings.push(`${k}: dropped`);
  }
  return { params: p, warnings };
}

export function sanitizeArea(a) {
  if (!a || typeof a !== "object") throw new Error("the scene has no area");
  const { lat, lon, zoom, size } = a;
  if (![lat, lon, zoom, size].every((x) => typeof x === "number" && Number.isFinite(x))) throw new Error("area needs numeric lat, lon, zoom and size");
  if (Math.abs(lat) > 85 || Math.abs(lon) > 180) throw new Error("area is off the map");
  return {
    lat, lon,
    zoom: Math.max(1, Math.min(MAX_ZOOM, Math.round(zoom))),
    size: SIZES.reduce((best, s) => (Math.abs(s - size) < Math.abs(best - size) ? s : best)),
  };
}

// raw scene (preset, parsed file, decoded hash) -> what the app keeps in its state: grid positions (0..1) and clean
// params. Throws on anything that can't be a scene; smaller problems are fixed and listed in `warnings`.
export function parseScene(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("not a scene (expected a JSON object)");
  if (raw.format !== undefined && raw.format !== FORMAT) throw new Error(`not a LineDream Terrain scene (format "${raw.format}")`);
  if (!(raw.mode in MODES)) throw new Error(`unknown renderer ${JSON.stringify(raw.mode)}`);
  const warnings = [];
  if (typeof raw.version === "number" && raw.version > VERSION) warnings.push(`made by a newer version (${raw.version}); some settings may be ignored`);
  const area = sanitizeArea(raw.area);
  const meta = areaMeta(area);
  const pin = (k, fallback) => {
    if (raw[k] === undefined || raw[k] === null) return fallback;
    if (!isPoint(raw[k])) { warnings.push(`${k}: expected [lat, lon]`); return fallback; }
    const uv = toUV(meta, raw[k][0], raw[k][1]);
    if (uv.every((x) => x >= 0 && x <= 1)) return uv;
    warnings.push(`${k}: outside the area`);
    return fallback;
  };
  const cam = pin("cam", DEFAULT_UV.cam), target = pin("target", DEFAULT_UV.target);
  const { params, warnings: pw } = sanitizeParams(raw.mode, raw.params, area);
  return {
    name: typeof raw.name === "string" ? raw.name.slice(0, 200) : "",
    mode: raw.mode, area, cam, target,
    halo: pin("halo", target.slice()), center: pin("center", DEFAULT_UV.center),
    params, warnings: [...warnings, ...pw],
  };
}

// app state -> scene, ready for JSON.stringify
export function sceneFromState(state, name = state.preset || "") {
  const meta = areaMeta(state.area), ll = (uv) => toLatLon(meta, uv[0], uv[1]).map(round6);
  return {
    format: FORMAT, version: VERSION, name, mode: state.mode, area: { ...state.area },
    cam: ll(state.cam), target: ll(state.target), halo: ll(state.halo), center: ll(state.center),
    params: { ...state.params[state.mode] },
  };
}

// The URL hash is the scene as JSON, URI-encoded. Links from before scenes existed ({m, a, c, t, ...} with grid
// positions) still open.
export function encodeHash(scene) {
  return "#" + encodeURIComponent(JSON.stringify(scene));
}

export function decodeHash(hash) {
  let s;
  try { s = JSON.parse(decodeURIComponent(String(hash).replace(/^#/, ""))); } catch { return null; }
  if (s && typeof s === "object" && s.m && s.a && !s.mode) {
    try {
      const meta = areaMeta(sanitizeArea(s.a)), ll = (uv) => (isPoint(uv) ? toLatLon(meta, uv[0], uv[1]) : undefined);
      s = { name: s.n, mode: s.m, area: s.a, cam: ll(s.c), target: ll(s.t), halo: ll(s.h), center: ll(s.ce), params: s.p };
    } catch { return null; }
  }
  try { return parseScene(s); } catch { return null; }
}

export function sceneFilename(name) {
  const slug = String(name || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
  return `${slug || "terrain-scene"}.json`;
}
