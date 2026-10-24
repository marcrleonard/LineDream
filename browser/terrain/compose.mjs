// "Compose": turn a rough eye + aim into a picture. Finds the highest summit the eye can actually see near where it
// is looking, aims at it, then picks the lens, light and haze the hand-tuned presets use for a subject that far away:
//   - lens: about 10 km of subject across the frame (a 30 km range gets ~19°, a peak 8 km away ~50°)
//   - aim: the summit a third of the way down from the top of the frame
//   - light: low (16°) and from the front-left, so faces turned to the eye are half lit and half shaded; a sun
//     behind the eye or behind the mountain lights every face alike and the drawing goes flat
//   - haze: starts at a third of the distance, full at a little over twice it; Earth curvature past 20 km
// Pure (no DOM), so it's tested under Node: test/compose.test.mjs.
import { sample } from "./tiles.mjs";

const R_EARTH = 6.371e6, REFRACTION = 0.13;
const deg = (r) => (r * 180) / Math.PI, rad = (d) => (d * Math.PI) / 180;
const wrap360 = (a) => ((a % 360) + 360) % 360;

// Compass heading (0 = north, clockwise) of grid direction (du, dv); v grows southward.
export const headingOf = (du, dv) => wrap360(deg(Math.atan2(du, -dv)));

// The highest point visible from the eye within +-span degrees of the heading, at least minDist away.
export function findSummit(dem, cam, eyeAbs, heading, { span = 30, minDist = null } = {}) {
  const { grid, size, width_m: W } = dem, px = W / size;
  const near = minDist ?? Math.max(1000, 0.03 * W);
  let best = null;
  for (let a = -span; a <= span + 1e-9; a += 0.5) {
    const h = rad(heading + a), du = Math.sin(h), dv = -Math.cos(h);
    let horizon = -Infinity;
    for (let d = px; ; d += px) {
      const u = cam[0] + (du * d) / W, v = cam[1] + (dv * d) / W;
      if (u < 0 || u > 1 || v < 0 || v > 1) break;
      const z = sample(grid, size, u, v), drop = (d * d * (1 - REFRACTION)) / (2 * R_EARTH);
      const t = (z - drop - eyeAbs) / d;
      if (t < horizon) continue;            // hidden behind nearer ground
      horizon = t;
      if (d >= near && (!best || z > best.z)) best = { u, v, z, d, bearing: wrap360(heading + a) };
    }
  }
  return best;
}

export function compose(dem, view, params) {
  const { grid, size, width_m: W } = dem;
  const ground = (uv) => sample(grid, size, uv[0], uv[1]);
  const eyeAbs = ground(view.cam) + params.eye;
  const heading = headingOf(view.target[0] - view.cam[0], view.target[1] - view.cam[1]);
  const peak = findSummit(dem, view.cam, eyeAbs, heading);
  if (!peak) return null;
  const D = peak.d, km = D / 1000;
  const fov = Math.round(Math.min(55, Math.max(14, deg(2 * Math.atan(5000 / D)))));
  const vfov = rad(fov) * 10 / 16;                                           // the drawing is 16:10
  const drop = (D * D * (1 - REFRACTION)) / (2 * R_EARTH);
  const pitch = Math.atan((peak.z - drop - eyeAbs) / D) - vfov / 6;          // summit a third down from the top
  const target_eye = Math.round(Math.max(-3000, Math.min(3000, eyeAbs + D * Math.tan(pitch) + drop - peak.z)));
  return {
    target: [peak.u, peak.v],
    peak,
    params: {
      fov, target_eye, shift: -0.05,
      sun_az: Math.round(wrap360(peak.bearing - 65)), sun_alt: 16,
      _haze_near_km: Math.round(km * 0.35 * 2) / 2, _haze_far_km: Math.max(1, Math.round(km * 2.2 * 2) / 2),
      curvature: D > 20000,
    },
  };
}
