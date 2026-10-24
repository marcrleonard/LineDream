// Compose: find the summit, frame it, light it (node --test browser/terrain/test/)
import { test } from "node:test";
import assert from "node:assert/strict";
import { compose, findSummit, headingOf } from "../compose.mjs";

// a flat plain with gaussian peaks: [u, v, height m, radius m]
function terrain(peaks, { size = 256, width_m = 40000, base = 300 } = {}) {
  const grid = new Float32Array(size * size);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    let z = base;
    for (const [u, v, h, r] of peaks) {
      const d = Math.hypot((x / (size - 1) - u) * width_m, (y / (size - 1) - v) * width_m);
      z += h * Math.exp(-(d * d) / (2 * r * r));
    }
    grid[y * size + x] = z;
  }
  return { grid, size, width_m };
}

const angleDiff = (a, b) => Math.abs((((a - b) % 360) + 540) % 360 - 180);

test("headings are compass bearings", () => {
  assert.equal(headingOf(0, -1), 0);    // north (v grows southward)
  assert.equal(headingOf(1, 0), 90);
  assert.equal(headingOf(0, 1), 180);
  assert.equal(headingOf(-1, 0), 270);
});

test("finds the highest peak near the line of sight, not the aim point", () => {
  const dem = terrain([[0.62, 0.3, 1500, 1500], [0.4, 0.35, 800, 1500]]);
  const s = findSummit(dem, [0.5, 0.9], 310, 0);
  assert.ok(Math.abs(s.u - 0.62) < 0.01 && Math.abs(s.v - 0.3) < 0.01, `${s.u}, ${s.v}`);
  assert.ok(Math.abs(s.z - 1800) < 15);
});

test("ignores peaks outside the search cone", () => {
  const dem = terrain([[0.95, 0.85, 3000, 1000], [0.5, 0.3, 900, 1500]]);  // the big one is due east of the eye
  const s = findSummit(dem, [0.5, 0.9], 310, 0);
  assert.ok(Math.abs(s.u - 0.5) < 0.01 && Math.abs(s.v - 0.3) < 0.01);
});

test("a peak hidden behind a nearer ridge loses to the ridge", () => {
  // eye low behind a tall wall; a slightly higher peak far behind it can't be seen
  const dem = terrain([[0.5, 0.75, 1200, 600], [0.5, 0.2, 1300, 800]]);
  const s = findSummit(dem, [0.5, 0.9], 305, 0);
  assert.ok(Math.abs(s.v - 0.75) < 0.02, `picked v=${s.v}`);
});

test("compose aims at the summit, frames it in the upper third, and cross-lights it", () => {
  const dem = terrain([[0.6, 0.3, 1600, 2500]]);
  const view = { cam: [0.5, 0.9], target: [0.5, 0.5] };
  const params = { eye: 30 };
  const c = compose(dem, view, params);
  assert.ok(Math.abs(c.target[0] - 0.6) < 0.01 && Math.abs(c.target[1] - 0.3) < 0.01);
  const D = c.peak.d;
  assert.ok(Math.abs(D - Math.hypot(0.1, 0.6) * 40000) < 300);
  // lens: ~10 km across at the subject
  assert.ok(c.params.fov >= 14 && c.params.fov <= 55);
  assert.ok(Math.abs(2 * D * Math.tan((c.params.fov * Math.PI) / 360) - 10000) < 1500);
  // the summit sits a third of the way down the frame: angle above the aim = vfov/6
  // aim height is measured from the ground under the aim point, which is now the summit
  const eyeAbs = 300 + 30, aimAbs = c.peak.z + c.params.target_eye;
  const drop = (D * D * 0.87) / (2 * 6.371e6);
  const up = Math.atan((c.peak.z - drop - eyeAbs) / D) - Math.atan((aimAbs - drop - eyeAbs) / D);
  const vfov = ((c.params.fov * Math.PI) / 180) * 10 / 16;
  assert.ok(Math.abs(up - vfov / 6) < 0.003, `${up} vs ${vfov / 6}`);
  // light from the front-left, low
  assert.ok(angleDiff(c.params.sun_az, c.peak.bearing - 65) < 1);
  assert.equal(c.params.sun_alt, 16);
  // haze scaled to the distance; curvature only for far subjects
  assert.ok(c.params._haze_near_km < D / 1000 && c.params._haze_far_km > D / 1000);
  assert.equal(c.params.curvature, D > 20000);
});

test("far subjects get a long lens and Earth curvature", () => {
  const dem = terrain([[0.5, 0.1, 2500, 4000]], { width_m: 60000 });
  const c = compose(dem, { cam: [0.5, 0.95], target: [0.5, 0.5] }, { eye: 10 });
  assert.ok(c.peak.d > 45000);
  assert.ok(c.params.fov <= 15, `fov ${c.params.fov}`);
  assert.equal(c.params.curvature, true);
});

test("flat ground: nothing to compose", () => {
  const dem = terrain([], { size: 64 });
  const c = compose(dem, { cam: [0.5, 0.9], target: [0.5, 0.5] }, { eye: 30 });
  // a perfectly flat plain still has a "highest point", but it's the far edge; compose must not crash either way
  assert.ok(c === null || c.params.fov >= 14);
});
