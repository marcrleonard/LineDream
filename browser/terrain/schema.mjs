// Every control the terrain app shows, and the presets that recreate the pieces made with the terrain experiments.
//
// A control is {k, label, type, ...}: type "range" (min, max, step), "select" (options), or "check". `def` matches the
// Python default (vista.Scene / strata.Params). Keys starting with "_" are UI-only and are turned into real
// parameters by app.mjs (contours, mist, halo, window, palette...). `show(p)` hides controls that don't apply.
// `elev: true` ranges are in metres and get their min/max from the loaded terrain.

const has = (k, ...vals) => (p) => vals.includes(p[k]);

export const PALETTES = {
  vista: {
    paper: { label: "Paper", paper: "#f1ece2", ink: "#1c1b19", accent: "#cf4a1f" },
    white: { label: "White", paper: "#ffffff", ink: "#141414", accent: "#d0402a" },
    night: { label: "Night", paper: "#14161a", ink: "#e9e4d8", accent: "#e3a940" },
    blueprint: { label: "Blueprint", paper: "#173a5e", ink: "#e8eff7", accent: "#ffcf5a" },
  },
  strata: {
    dark: { label: "Dark", background: "#111111", stroke: "#eeeeee" },
    paper: { label: "Paper", background: "#f1ece2", stroke: "#1c1b19" },
    white: { label: "White", background: "#ffffff", stroke: "#141414" },
    blueprint: { label: "Blueprint", background: "#173a5e", stroke: "#e8eff7" },
  },
};

export const MODES = {
  vista: {
    label: "Vista",
    blurb: "Perspective: stand somewhere and look. Tone hatching, outlines, labelled contours, haze, mist.",
    groups: [
      ["Camera", [
        { k: "eye", label: "Eye height above ground (m)", type: "range", min: 0, max: 3000, step: 5, def: 30 },
        { k: "target_eye", label: "Aim height above ground (m)", type: "range", min: -3000, max: 3000, step: 10, def: 0 },
        { k: "fov", label: "Field of view (°)", type: "range", min: 8, max: 110, step: 1, def: 55 },
        { k: "shift", label: "Lens shift (+ moves the scene up)", type: "range", min: -0.6, max: 0.6, step: 0.01, def: 0 },
        { k: "exaggeration", label: "Vertical exaggeration", type: "range", min: 0.5, max: 3, step: 0.05, def: 1.3 },
        { k: "smooth", label: "Terrain smoothing (px)", type: "range", min: 0, max: 3, step: 0.1, def: 0.7 },
        { k: "curvature", label: "Earth curvature (matters past ~20 km)", type: "check", def: false },
      ]],
      ["Light", [
        { k: "sun_az", label: "Sun direction (° from north)", type: "range", min: 0, max: 360, step: 1, def: 120 },
        { k: "sun_alt", label: "Sun height (°)", type: "range", min: 1, max: 85, step: 1, def: 14 },
        { k: "shadows", label: "Cast shadows", type: "check", def: true },
        { k: "invert", label: "Hatch the light instead of the dark", type: "check", def: false },
      ]],
      ["Tone", [
        { k: "tone", label: "Hatching", type: "select", def: "screen", options: [
          ["flow", "Strokes that follow the form"], ["screen", "Etching (straight lines)"],
          ["rings", "Distance rings"], ["both", "Etching + rings"], ["none", "None (outlines only)"]] },
        { k: "flow_dir", label: "Stroke direction: contour ↔ fall line", type: "range", min: 0, max: 90, step: 1, def: 0, show: has("tone", "flow") },
        { k: "flow_sep", label: "Stroke spacing in shadow (px)", type: "range", min: 1.2, max: 8, step: 0.1, def: 2.6, show: has("tone", "flow") },
        { k: "flow_sep_max", label: "Stroke spacing in half-light (px)", type: "range", min: 3, max: 30, step: 0.5, def: 14, show: has("tone", "flow") },
        { k: "flow_min_tone", label: "Lightest tone that gets strokes", type: "range", min: 0.02, max: 0.95, step: 0.01, def: 0.3, show: has("tone", "flow") },
        { k: "hatch_angle", label: "Etching angle (°)", type: "range", min: -90, max: 90, step: 1, def: 0, show: has("tone", "screen", "both") },
        { k: "hatch_spacing", label: "Etching spacing (px)", type: "range", min: 1.2, max: 10, step: 0.1, def: 3, show: has("tone", "screen", "both") },
        { k: "rings", label: "Distance rings", type: "range", min: 40, max: 800, step: 10, def: 320, show: has("tone", "rings", "both") },
        { k: "cross", label: "Cross-hatch the darkest (0 = off)", type: "range", min: 0, max: 1, step: 0.01, def: 0, show: has("tone", "flow", "screen", "both") },
        { k: "cross_angle", label: "Cross-hatch angle (°)", type: "range", min: 10, max: 90, step: 1, def: 55, show: (p) => p.cross > 0 && p.tone !== "flow" },
        { k: "shade_gamma", label: "Tone curve (<1 darkens mid-tones)", type: "range", min: 0.3, max: 2.5, step: 0.05, def: 1 },
        { k: "shade_floor", label: "Base darkness everywhere", type: "range", min: 0, max: 0.6, step: 0.01, def: 0 },
        { k: "tone_scale", label: "Tone strength", type: "range", min: 0.2, max: 1, step: 0.01, def: 1 },
      ]],
      ["Lines", [
        { k: "silhouettes", label: "Outlines (silhouettes)", type: "check", def: true },
        { k: "lost_edges", label: "Lose outlines in the light", type: "range", min: 0, max: 0.9, step: 0.01, def: 0, show: has("silhouettes", true) },
        { k: "overshoot", label: "Outline overshoot (px)", type: "range", min: 0, max: 12, step: 0.5, def: 0, show: has("silhouettes", true) },
        { k: "wobble", label: "Hand wobble (px)", type: "range", min: 0, max: 4, step: 0.1, def: 0 },
      ]],
      ["Contours", [
        { k: "topo_every", label: "Labelled contours in the light, every (0 = off)", type: "range", min: 0, max: 1000, step: 10, def: 0 },
        { k: "topo_units", label: "Contour units", type: "select", def: "m", options: [["m", "metres"], ["ft", "feet"]], show: (p) => p.topo_every > 0 },
        { k: "topo_label_every", label: "Label every Nth contour (0 = no labels)", type: "range", min: 0, max: 10, step: 1, def: 5, show: (p) => p.topo_every > 0 },
        { k: "topo_label_size", label: "Label size (px)", type: "range", min: 4, max: 20, step: 0.5, def: 7, show: (p) => p.topo_every > 0 && p.topo_label_every > 0 },
        { k: "topo_gap", label: "Blank margin next to the strokes", type: "range", min: 0, max: 0.4, step: 0.01, def: 0.08, show: (p) => p.topo_every > 0 },
        { k: "contour_every", label: "Plain contours everywhere, every m (0 = off)", type: "range", min: 0, max: 1000, step: 10, def: 0 },
        { k: "_accent_on", label: "One accent contour", type: "check", def: false },
        { k: "_accent_elev", label: "Accent contour elevation (m)", type: "range", elev: true, step: 10, def: 0, show: has("_accent_on", true) },
      ]],
      ["Atmosphere", [
        { k: "haze", label: "Haze", type: "range", min: 0, max: 1, step: 0.01, def: 0.6 },
        { k: "_haze_near_km", label: "Haze starts (km)", type: "range", min: 0, max: 100, step: 0.5, def: 3, show: (p) => p.haze > 0 },
        { k: "_haze_far_km", label: "Haze full (km)", type: "range", min: 0.5, max: 150, step: 0.5, def: 30, show: (p) => p.haze > 0 },
        { k: "_mist_on", label: "Mist / water level", type: "check", def: false },
        { k: "_mist_elev", label: "Mist level (m)", type: "range", elev: true, step: 1, def: 0, show: has("_mist_on", true) },
        { k: "mist_lines", label: "Lines on the mist", type: "range", min: 0, max: 100, step: 1, def: 0, show: has("_mist_on", true) },
      ]],
      ["Sky & accents", [
        { k: "sun_disc", label: "Sun disc size (0 = off)", type: "range", min: 0, max: 0.35, step: 0.005, def: 0 },
        { k: "sun_lines", label: "Lines in the disc", type: "range", min: 3, max: 30, step: 1, def: 15, show: (p) => p.sun_disc > 0 },
        { k: "_sun_free", label: "Place the disc by hand", type: "check", def: false, show: (p) => p.sun_disc > 0 },
        { k: "_sun_x", label: "Disc x", type: "range", min: -1, max: 1, step: 0.01, def: 0.4, show: (p) => p.sun_disc > 0 && p._sun_free },
        { k: "_sun_y", label: "Disc y", type: "range", min: -0.6, max: 0.6, step: 0.01, def: 0.2, show: (p) => p.sun_disc > 0 && p._sun_free },
        { k: "sky_lines", label: "Sky streaks", type: "range", min: 0, max: 20, step: 1, def: 0 },
        { k: "_halo_on", label: "Floating ring (drag it on the map)", type: "check", def: false },
        { k: "_halo_elev", label: "Ring centre elevation (m)", type: "range", elev: true, step: 10, def: 0, show: has("_halo_on", true), headroom: 1500 },
        { k: "_halo_radius", label: "Ring radius (m)", type: "range", min: 20, max: 3000, step: 10, def: 300, show: has("_halo_on", true) },
        { k: "_window", label: "Tone only inside", type: "select", def: "none", options: [["none", "everywhere"], ["circle", "a circle"], ["rect", "a rectangle"]] },
        { k: "_window_x", label: "Window x", type: "range", min: -1, max: 1, step: 0.01, def: 0, show: (p) => p._window !== "none" },
        { k: "_window_y", label: "Window y", type: "range", min: -0.6, max: 0.6, step: 0.01, def: 0.05, show: (p) => p._window !== "none" },
        { k: "_window_size", label: "Window size", type: "range", min: 0.1, max: 1, step: 0.01, def: 0.4, show: (p) => p._window !== "none" },
      ]],
      ["Style", [
        { k: "_palette", label: "Palette", type: "select", def: "paper", options: Object.entries(PALETTES.vista).map(([k, v]) => [k, v.label]) },
        { k: "plotter", label: "Plotter mode (2 pens + contour pen, haze as dashes)", type: "check", def: false },
        { k: "frame", label: "Frame", type: "check", def: true },
        { k: "stroke_width", label: "Stroke width (px)", type: "range", min: 0.3, max: 2.5, step: 0.05, def: 0.8 },
        { k: "seed", label: "Seed", type: "range", min: 0, max: 999, step: 1, def: 0 },
      ]],
    ],
  },

  strata: {
    label: "Strata",
    blurb: "Top-down or oblique: one family of curves across the whole map, bent by the terrain.",
    groups: [
      ["Paths", [
        { k: "paths", label: "Curves", type: "select", def: "scan", options: [
          ["scan", "Scan lines (ridgelines)"], ["radial", "Radial rays"], ["spiral", "One spiral"], ["rings", "Concentric rings"],
          ["contour", "Contours"], ["flow", "Flow lines"], ["hatch", "Engraving hatch"]] },
        { k: "count", label: "How many", type: "range", min: 10, max: 10000, step: 10, def: 80, show: (p) => p.paths !== "spiral" },
        { k: "turns", label: "Spiral turns", type: "range", min: 5, max: 200, step: 1, def: 60, show: has("paths", "spiral") },
        { k: "angle", label: "Angle (° · flow: 0 downhill, 90 along contours)", type: "range", min: -180, max: 180, step: 1, def: 0, show: has("paths", "scan", "hatch", "flow") },
        { k: "inner", label: "Empty centre radius", type: "range", min: 0, max: 0.45, step: 0.005, def: 0, show: has("paths", "radial", "spiral", "rings") },
        { k: "flow_len", label: "Max flow line length", type: "range", min: 50, max: 1500, step: 10, def: 400, show: has("paths", "flow") },
        { k: "flow_sep", label: "Flow line spacing", type: "range", min: 0.002, max: 0.03, step: 0.0005, def: 0.006, show: has("paths", "flow") },
        { k: "flow_noise", label: "Flow noise", type: "range", min: 0, max: 1, step: 0.01, def: 0, show: has("paths", "flow") },
      ]],
      ["Displace", [
        { k: "mode", label: "Height becomes", type: "select", def: "lift", options: [["lift", "3D lift"], ["offset", "Sideways push (2D)"]] },
        { k: "relief", label: "Relief", type: "range", min: 0, max: 0.8, step: 0.005, def: 0.2 },
        { k: "highpass", label: "Detail only (high-pass px, 0 = off)", type: "range", min: 0, max: 20, step: 0.5, def: 0 },
        { k: "jitter", label: "Per-line relief jitter", type: "range", min: 0, max: 1, step: 0.01, def: 0 },
      ]],
      ["Camera", [
        { k: "pitch", label: "Pitch (90 = straight down)", type: "range", min: 5, max: 90, step: 1, def: 35 },
        { k: "yaw", label: "Yaw (°)", type: "range", min: 0, max: 360, step: 1, def: 0 },
        { k: "occlude", label: "Hidden-line removal", type: "check", def: true, show: has("mode", "lift") },
      ]],
      ["Terrain", [
        { k: "blur", label: "Blur (px)", type: "range", min: 0, max: 5, step: 0.1, def: 1 },
        { k: "gamma", label: "Gamma", type: "range", min: 0.3, max: 3, step: 0.05, def: 1 },
        { k: "terrace", label: "Terraces (0 = off)", type: "range", min: 0, max: 40, step: 1, def: 0 },
        { k: "terrace_soft", label: "Terrace softness", type: "range", min: 0, max: 1, step: 0.01, def: 0, show: (p) => p.terrace > 0 },
        { k: "warp", label: "Domain warp", type: "range", min: 0, max: 0.15, step: 0.002, def: 0 },
        { k: "warp_scale", label: "Warp scale", type: "range", min: 0.02, max: 0.4, step: 0.01, def: 0.12, show: (p) => p.warp > 0 },
      ]],
      ["Where ink lands", [
        { k: "mask", label: "Mask", type: "select", def: "none", options: [["none", "none"], ["noise", "noise"], ["slope", "steep ground"], ["inv_slope", "flat ground"], ["height", "high ground"]] },
        { k: "mask_threshold", label: "Mask threshold", type: "range", min: 0, max: 1, step: 0.01, def: 0.5, show: (p) => p.mask !== "none" },
        { k: "mask_scale", label: "Noise scale", type: "range", min: 0.005, max: 0.3, step: 0.005, def: 0.06, show: has("mask", "noise") },
        { k: "mask_mix", label: "Blend height into the noise", type: "range", min: 0, max: 1, step: 0.01, def: 0, show: has("mask", "noise") },
        { k: "clip", label: "Clip", type: "select", def: "square", options: [["square", "square"], ["circle", "circle"]] },
        { k: "min_run", label: "Drop fragments shorter than", type: "range", min: 2, max: 20, step: 1, def: 3 },
      ]],
      ["Style", [
        { k: "_palette", label: "Palette", type: "select", def: "dark", options: Object.entries(PALETTES.strata).map(([k, v]) => [k, v.label]) },
        { k: "stroke_width", label: "Stroke width (px)", type: "range", min: 0.3, max: 3, step: 0.05, def: 1 },
        { k: "seed", label: "Seed", type: "range", min: 0, max: 999, step: 1, def: 0 },
      ]],
    ],
  },
};

// ------------------------------------------------------------------------------------------- presets
// area: what to load (centre, tile zoom, grid size). cam / target / halo / center: lat/lon pinned to the map.

const CIRQUE = { lat: 42.77776, lon: -109.21715, zoom: 14, size: 1024 };
const JACKASS_PASS = [42.76894, -109.21114], CIRQUE_AIM = [42.779, -109.229];
const YOSEMITE = { lat: 37.735, lon: -119.61, zoom: 12, size: 1024 }, TUNNEL_VIEW = [37.7156, -119.6773], HALF_DOME = [37.7459, -119.5332];
const FUJI = { lat: 35.44, lon: 138.74, zoom: 12, size: 1024 }, KAWAGUCHIKO = [35.515, 138.755], FUJI_TOP = [35.3606, 138.7274];
const CANYON = { lat: 36.1, lon: -112.12, zoom: 12, size: 1024 };
const HELENS = { lat: 46.24, lon: -122.2, zoom: 12, size: 1024 };
const MATTERHORN = { lat: 45.98, lon: 7.7, zoom: 13, size: 1024 }, RIFFELSEE = [45.9877, 7.757], MATTERHORN_TOP = [45.9763, 7.6586];

const PEN = { plotter: true, stroke_width: 1.0 };
const FALL = { tone: "flow", flow_dir: 90, flow_sep: 2.4, flow_sep_max: 9, flow_min_tone: 0.3, shade_gamma: 0.7, lost_edges: 0.25, overshoot: 3, wobble: 0.6 };
const PASS = { eye: 15, target_eye: -120, fov: 50, shift: -0.05, sun_az: 215, sun_alt: 20, exaggeration: 1.0, smooth: 0.5,
  tone: "flow", flow_dir: 90, flow_sep: 2.8, flow_sep_max: 15, flow_min_tone: 0.3, shade_floor: 0.1, lost_edges: 0.25, overshoot: 3, wobble: 0.6,
  haze: 0.35, haze_near: 0.12, haze_far: 0.7, _mist_on: true, _mist_elev: 3101, mist_lines: 34, ...PEN };
const VY = { eye: 25, target_eye: -350, fov: 36, shift: -0.1, shade_floor: 0.12, hatch_angle: -8, cross: 0.85, sun_az: 235, sun_alt: 20,
  _mist_on: true, _mist_elev: 1290, mist_lines: 40, rings: 360, haze: 0.55, haze_near: 0.05, haze_far: 0.6, _accent_on: true, _accent_elev: 2400, sky_lines: 7 };
const VM = { eye: 10, target_eye: -200, fov: 24, shift: -0.2, sun_az: 120, sun_alt: 10, hatch_angle: 12, cross: 0.9, smooth: 0, exaggeration: 1.6,
  shade_floor: 0.08, sun_disc: 0.11, _sun_free: true, _sun_x: -0.5, _sun_y: 0.3, sun_lines: 12, rings: 380, haze: 0.2, haze_near: 0.03, haze_far: 0.5,
  _accent_on: true, _accent_elev: 3800 };

const GRAND_TETON = [43.7411, -110.8024];
const TETON_STYLE = { tone: "flow", flow_dir: 90, flow_sep: 2.4, flow_sep_max: 10, flow_min_tone: 0.3, shade_gamma: 0.8,
  lost_edges: 0.2, overshoot: 3, wobble: 0.5, ...PEN, curvature: true };

// Presets give haze in map widths (haze_near / haze_far, as the original renders did) or directly in km
// (_haze_near_km / _haze_far_km); app.mjs converts the former using the preset area's real width.
export const PRESETS = [
  { name: "Grand Tetons from Mount Leidy (33 km)", mode: "vista", area: { lat: 43.73316, lon: -110.60424, zoom: 11, size: 1024 },
    cam: [43.72521, -110.40607], target: GRAND_TETON,
    params: { ...TETON_STYLE, eye: 5, target_eye: 0, fov: 22, shift: -0.08, sun_az: 240, sun_alt: 22, haze: 0.5, _haze_near_km: 10, _haze_far_km: 60 } },
  { name: "Grand Tetons from Snake River Overlook", mode: "vista", area: { lat: 43.69925, lon: -110.7087, zoom: 12, size: 1024 },
    cam: [43.6574, -110.615], target: GRAND_TETON,
    params: { ...TETON_STYLE, eye: 5, target_eye: 0, fov: 26, shift: -0.1, sun_az: 250, sun_alt: 18, haze: 0.45, _haze_near_km: 4, _haze_far_km: 35 } },
  { name: "Topo duality · Cirque of the Towers", mode: "vista", area: CIRQUE, cam: JACKASS_PASS, target: CIRQUE_AIM,
    params: { ...PASS, ...FALL, shade_floor: 0, sun_az: 165, sun_alt: 28, topo_every: 120, topo_units: "ft", topo_label_every: 5, topo_label_size: 11 } },
  { name: "Topo duality · Yosemite", mode: "vista", area: YOSEMITE, cam: TUNNEL_VIEW, target: HALF_DOME,
    params: { eye: 25, target_eye: -350, fov: 36, shift: -0.1, sun_az: 200, sun_alt: 35, _mist_on: true, _mist_elev: 1290, mist_lines: 30,
      haze: 0.35, haze_near: 0.05, haze_far: 0.6, topo_every: 200, topo_units: "ft", topo_label_every: 5, topo_label_size: 11, ...FALL, ...PEN } },
  { name: "Topo duality · Fuji", mode: "vista", area: FUJI, cam: KAWAGUCHIKO, target: FUJI_TOP,
    params: { eye: 650, target_eye: -1400, fov: 40, shift: -0.18, sun_az: 285, sun_alt: 15, _mist_on: true, _mist_elev: 1150, mist_lines: 40,
      haze: 0.3, haze_near: 0.1, haze_far: 0.9, topo_every: 100, topo_units: "m", topo_label_every: 5, topo_label_size: 11,
      ...FALL, shade_gamma: 1.0, flow_min_tone: 0.42, ...PEN } },
  { name: "Fall lines · Jackass Pass", mode: "vista", area: CIRQUE, cam: JACKASS_PASS, target: CIRQUE_AIM, params: { ...PASS } },
  { name: "Contour strokes · Jackass Pass", mode: "vista", area: CIRQUE, cam: JACKASS_PASS, target: CIRQUE_AIM,
    params: { ...PASS, flow_dir: 0, _accent_on: true, _accent_elev: 3600 } },
  { name: "Sunset · Lonesome Lake", mode: "vista", area: CIRQUE, cam: [42.77814, -109.20685], target: CIRQUE_AIM,
    params: { ...PASS, eye: 2, target_eye: 350, fov: 40, shift: 0.12, sun_az: 262, sun_alt: 14, flow_min_tone: 0.45, tone_scale: 0.85,
      sun_disc: 0.08, sun_lines: 12, lost_edges: 0.15 } },
  { name: "Night ring · Pingora", mode: "vista", area: CIRQUE, cam: JACKASS_PASS, target: CIRQUE_AIM, halo: [42.77902, -109.22573],
    params: { ...PASS, _palette: "night", invert: true, sun_az: 120, sun_alt: 25, flow_sep: 3.0, lost_edges: 0, sun_disc: 0.05,
      _sun_free: true, _sun_x: 0.6, _sun_y: 0.4, sun_lines: 8, _halo_on: true, _halo_elev: 3760, _halo_radius: 140 } },
  { name: "Etching · Yosemite Tunnel View", mode: "vista", area: YOSEMITE, cam: TUNNEL_VIEW, target: HALF_DOME, params: { ...VY } },
  { name: "Contour strokes · Yosemite", mode: "vista", area: YOSEMITE, cam: TUNNEL_VIEW, target: HALF_DOME,
    params: { ...VY, tone: "flow", cross: 0, lost_edges: 0.25, overshoot: 4, wobble: 0.8, sky_lines: 4 } },
  { name: "Woodblock · Fuji at dusk", mode: "vista", area: FUJI, cam: KAWAGUCHIKO, target: FUJI_TOP,
    params: { eye: 650, target_eye: -1400, fov: 40, shift: -0.18, sun_az: 275, sun_alt: 6, hatch_angle: -20, _mist_on: true, _mist_elev: 1150,
      mist_lines: 55, rings: 300, haze: 0.45, haze_near: 0.1, haze_far: 0.8, contour_every: 150, contour_above: 3050,
      sun_disc: 0.17, _sun_free: true, _sun_x: 0.42, _sun_y: 0.06, sun_lines: 17, sky_lines: 5 } },
  { name: "Fall lines · Fuji", mode: "vista", area: FUJI, cam: KAWAGUCHIKO, target: FUJI_TOP,
    params: { eye: 650, target_eye: -1400, fov: 40, shift: -0.18, sun_az: 275, sun_alt: 6, _mist_on: true, _mist_elev: 1150, mist_lines: 55,
      haze: 0.45, haze_near: 0.1, haze_far: 0.8, contour_every: 150, contour_above: 3050, sun_disc: 0.17, _sun_free: true, _sun_x: 0.42,
      _sun_y: 0.06, sun_lines: 17, sky_lines: 5, tone: "flow", flow_dir: 90, flow_sep: 3.0, flow_sep_max: 16, lost_edges: 0.2, wobble: 0.6, ...PEN } },
  { name: "Window · Grand Canyon", mode: "vista", area: CANYON, cam: [36.0617, -112.1077], target: [36.12, -112.11],
    params: { eye: 15, target_eye: -450, fov: 55, sun_az: 255, sun_alt: 13, hatch_spacing: 3.4, tone_scale: 0.8, _window: "circle",
      _window_x: 0.12, _window_y: 0, _window_size: 0.5, rings: 420, haze: 0.7, haze_near: 0.03, haze_far: 0.55, _accent_on: true, _accent_elev: 2150 } },
  { name: "Night ring · Mount St. Helens", mode: "vista", area: HELENS, cam: [46.2766, -122.2172], target: [46.2, -122.189], halo: [46.2, -122.189],
    params: { eye: 20, target_eye: -200, fov: 50, shift: -0.1, sun_az: 85, sun_alt: 18, shade_floor: 0.1, _mist_on: true, _mist_elev: 1150,
      mist_lines: 45, rings: 280, haze: 0.55, haze_near: 0.05, haze_far: 0.7, sun_disc: 0.06, _sun_free: true, _sun_x: -0.55, _sun_y: 0.42,
      sun_lines: 9, invert: true, hatch_spacing: 3.4, _palette: "night", _halo_on: true, _halo_elev: 3050, _halo_radius: 1100 } },
  { name: "Minimal · Matterhorn", mode: "vista", area: MATTERHORN, cam: RIFFELSEE, target: MATTERHORN_TOP, params: { ...VM } },
  { name: "Strokes only · Matterhorn", mode: "vista", area: MATTERHORN, cam: RIFFELSEE, target: MATTERHORN_TOP,
    params: { ...VM, tone: "flow", flow_dir: 90, silhouettes: false, flow_sep: 2.4, flow_sep_max: 12, flow_min_tone: 0.25, shade_floor: 0.35, haze: 0.1, ...PEN } },

  // strata: the round-one presets (768-pixel grids, as rendered then)
  { name: "Ridgelines · Mount St. Helens", mode: "strata", area: { lat: 46.1914, lon: -122.1956, zoom: 12, size: 768 },
    params: { paths: "scan", count: 120, pitch: 24, relief: 0.2, clip: "circle" } },
  { name: "Vinyl · Fuji", mode: "strata", area: { lat: 35.3606, lon: 138.7274, zoom: 11, size: 768 },
    params: { paths: "spiral", mode: "offset", turns: 80, relief: 0.12, highpass: 8, inner: 0.02, pitch: 90, clip: "circle", blur: 1.0 } },
  { name: "Sonar · Kilimanjaro", mode: "strata", area: { lat: -3.0674, lon: 37.3556, zoom: 12, size: 768 },
    params: { paths: "radial", count: 240, mode: "offset", relief: 0.5, highpass: 6, inner: 0.12, pitch: 90, clip: "circle" } },
  { name: "Halo rings · Matterhorn", mode: "strata", area: { lat: 45.9763, lon: 7.6586, zoom: 12, size: 768 },
    params: { paths: "rings", count: 70, pitch: 32, relief: 0.22, yaw: 200, clip: "circle" } },
  { name: "Stacked contours · Mount St. Helens", mode: "strata", area: { lat: 46.1914, lon: -122.1956, zoom: 12, size: 768 },
    params: { paths: "contour", count: 36, pitch: 30, relief: 0.2, blur: 2, clip: "circle" } },
  { name: "Engraving · Yosemite", mode: "strata", area: { lat: 37.74, lon: -119.57, zoom: 12, size: 768 },
    params: { paths: "hatch", count: 150, pitch: 90, mask: "slope", mask_threshold: 0.18, stroke_width: 0.9 } },
  { name: "Dissolve · Kilimanjaro", mode: "strata", area: { lat: -3.0674, lon: 37.3556, zoom: 12, size: 768 },
    params: { paths: "scan", count: 150, pitch: 26, relief: 0.2, warp: 0.04, warp_scale: 0.1, mask: "noise", mask_mix: 0.6, mask_threshold: 0.34,
      mask_scale: 0.012, clip: "circle", seed: 3 } },
  { name: "Wind-combed · Matterhorn", mode: "strata", area: { lat: 45.9763, lon: 7.6586, zoom: 12, size: 768 },
    params: { paths: "flow", angle: 90, count: 5000, flow_sep: 0.008, flow_len: 500, flow_noise: 0.2, pitch: 45, relief: 0.2, clip: "circle", stroke_width: 0.8 } },
  { name: "Rain · Grand Canyon", mode: "strata", area: { lat: 36.075, lon: -112.13, zoom: 11, size: 768 },
    params: { paths: "flow", count: 9000, flow_sep: 0.0045, flow_len: 600, pitch: 90, blur: 1.2, mask: "slope", mask_threshold: 0.12, stroke_width: 0.8 } },
  { name: "Ridgelines · Cirque of the Towers", mode: "strata", area: CIRQUE,
    params: { paths: "scan", count: 130, pitch: 26, relief: 0.12, clip: "circle", yaw: 200, _palette: "paper" } },
];

export function defaults(mode) {
  const p = {};
  for (const [, items] of MODES[mode].groups) for (const c of items) p[c.k] = c.def;
  return p;
}
