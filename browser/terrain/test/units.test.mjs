// Display units (node --test browser/terrain/test/)
import { test } from "node:test";
import assert from "node:assert/strict";
import { displayRange, fmtDistance, fmtLength, fromDisplay, niceStep, toDisplay, unitName } from "../units.mjs";

test("feet and miles by name; metric is the identity", () => {
  assert.equal(unitName("imperial", "m"), "ft");
  assert.equal(unitName("imperial", "km"), "mi");
  assert.equal(unitName("metric", "m"), "m");
  assert.equal(toDisplay("metric", "m", 1234.5), 1234.5);
  assert.equal(toDisplay("metric", "km", 3), 3);
});

test("conversions are right and round-trip", () => {
  assert.ok(Math.abs(toDisplay("imperial", "m", 1916) - 6286) < 1);      // Mount Washington, 6,288 ft published
  assert.ok(Math.abs(toDisplay("imperial", "km", 26) - 16.16) < 0.01);
  for (const v of [0, 1, 30, 3000, -371, 0.5, 150]) for (const k of ["m", "km"])
    assert.ok(Math.abs(fromDisplay("imperial", k, toDisplay("imperial", k, v)) - v) < 1e-9);
});

test("an unknown system falls back to imperial", () => {
  assert.equal(unitName("furlongs", "m"), "ft");
});

test("slider steps stay round in feet and miles", () => {
  assert.equal(niceStep("imperial", "m", 5), 20);      // 16.4 ft
  assert.equal(niceStep("imperial", "m", 10), 25);     // 32.8 ft
  assert.equal(niceStep("imperial", "m", 1), 2.5);     // 3.3 ft
  assert.equal(niceStep("imperial", "km", 0.5), 0.25); // 0.31 mi
  assert.equal(niceStep("metric", "m", 5), 5);
});

test("slider ranges cover the stored range in whole steps", () => {
  const r = displayRange("imperial", "m", 0, 3000, 5);
  assert.deepEqual(r, { min: 0, max: 9860, step: 20 });
  const n = displayRange("imperial", "m", -3000, 3000, 10);
  assert.ok(n.min <= toDisplay("imperial", "m", -3000) && n.max >= toDisplay("imperial", "m", 3000));
  assert.equal(Math.abs(n.min % n.step), 0);
  assert.deepEqual(displayRange("metric", "km", 0.5, 150, 0.5), { min: 0.5, max: 150, step: 0.5 });
});

test("readouts", () => {
  assert.equal(fmtLength("imperial", 1916), "6,286 ft");
  assert.equal(fmtLength("metric", 1916), "1,916 m");
  assert.equal(fmtDistance("imperial", 26), "16 mi");
  assert.equal(fmtDistance("imperial", 11.7), "7.3 mi");
  assert.equal(fmtDistance("metric", 31.9), "32 km");
  assert.equal(fmtDistance("metric", 3.2), "3.2 km");
});
