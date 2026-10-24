// Scene format: presets, saved files and links (node --test browser/terrain/test/)
import { test } from "node:test";
import assert from "node:assert/strict";
import { MODES, PRESETS, defaults } from "../schema.mjs";
import { DEFAULT_UV, FORMAT, VERSION, areaWidthKm, decodeHash, encodeHash, parseScene, sanitizeParams, sceneFilename, sceneFromState } from "../scene.mjs";

const TETONS = PRESETS.find((p) => p.name.startsWith("Grand Tetons from Mount Leidy"));
const OLD_HAZE = PRESETS.find((p) => p.mode === "vista" && "haze_near" in p.params);
const STRATA = PRESETS.find((p) => p.mode === "strata");
const close = (a, b, tol, msg) => a.forEach((x, i) => assert.ok(Math.abs(x - b[i]) < tol, `${msg}: ${a} vs ${b}`));

// what the app keeps for a scene: state as applyScene() leaves it
function toState(sc) {
  return { mode: sc.mode, area: sc.area, cam: sc.cam, target: sc.target, halo: sc.halo, center: sc.center, preset: sc.name,
    params: { vista: defaults("vista"), strata: defaults("strata"), [sc.mode]: sc.params } };
}

function assertSameScene(a, b) {
  assert.equal(a.mode, b.mode);
  assert.equal(a.name, b.name);
  assert.deepEqual(a.area, b.area);
  for (const k of ["cam", "target", "halo", "center"]) close(a[k], b[k], 1e-5, k);
  assert.deepEqual(Object.keys(a.params).sort(), Object.keys(b.params).sort());
  for (const [k, v] of Object.entries(a.params)) {
    if (typeof v === "number") assert.ok(Math.abs(v - b.params[k]) < 1e-9, `${k}: ${v} vs ${b.params[k]}`);
    else assert.equal(v, b.params[k], k);
  }
}

test("every preset parses cleanly, with no fixes needed", () => {
  for (const pr of PRESETS) {
    const sc = parseScene(pr);
    assert.deepEqual(sc.warnings, [], pr.name);
    assert.equal(sc.name, pr.name);
    for (const k of ["cam", "target"]) assert.ok(sc[k].every((x) => x >= 0 && x <= 1), `${pr.name}: ${k} inside its area`);
  }
});

test("preset names are unique (a link reselects its preset by name)", () => {
  assert.equal(new Set(PRESETS.map((p) => p.name)).size, PRESETS.length);
});

test("every preset survives saving to a file and opening it again", () => {
  for (const pr of PRESETS) {
    const sc = parseScene(pr);
    const file = JSON.stringify(sceneFromState(toState(sc)), null, 2);
    const back = parseScene(JSON.parse(file));
    assert.deepEqual(back.warnings, [], pr.name);
    assertSameScene(back, sc);
  }
});

test("every preset survives a round trip through the URL hash", () => {
  for (const pr of PRESETS) {
    const sc = parseScene(pr);
    const hash = encodeHash(sceneFromState(toState(sc)));
    assert.match(hash, /^#[A-Za-z0-9%\-_.!~*'()]+$/, "hash is URI-safe");
    assertSameScene(decodeHash(hash), sc);
  }
});

test("a saved file has the header and lat/lon pins, and is itself a valid preset", () => {
  const sc = parseScene(TETONS);
  const saved = sceneFromState(toState(sc), "My Tetons");
  assert.equal(saved.format, FORMAT);
  assert.equal(saved.version, VERSION);
  assert.equal(saved.name, "My Tetons");
  close(saved.cam, TETONS.cam, 1e-5, "eye lat/lon");
  close(saved.target, TETONS.target, 1e-5, "aim lat/lon");
  const { format, version, ...preset } = saved;
  assertSameScene(parseScene(preset), parseScene(saved));
});

test("names with awkward characters survive the hash", () => {
  const sc = parseScene({ ...TETONS, name: "Teton #1 & 50% — Ñuñoa \"quoted\" 🏔️" });
  assert.equal(decodeHash(encodeHash(sceneFromState(toState(sc)))).name, sc.name);
});

test("links from before the scene format still open", () => {
  const sc = parseScene(TETONS);
  const old = { m: sc.mode, a: sc.area, c: sc.cam, t: sc.target, h: sc.halo, ce: sc.center, p: sc.params, n: sc.name };
  assertSameScene(decodeHash("#" + encodeURIComponent(JSON.stringify(old))), sc);
});

test("garbage hashes are ignored, not thrown", () => {
  for (const h of ["", "#", "#%E0%A4%A", "#not-json", "#" + encodeURIComponent("[1,2]"), "#" + encodeURIComponent('{"mode":"nope"}')])
    assert.equal(decodeHash(h), null, h);
});

test("files that aren't scenes are rejected with a reason", () => {
  assert.throws(() => parseScene(null), /not a scene/);
  assert.throws(() => parseScene([1, 2]), /not a scene/);
  assert.throws(() => parseScene({ ...TETONS, format: "something-else" }), /not a LineDream Terrain scene/);
  assert.throws(() => parseScene({ ...TETONS, mode: "cubism" }), /unknown renderer/);
  assert.throws(() => parseScene({ ...TETONS, area: undefined }), /no area/);
  assert.throws(() => parseScene({ ...TETONS, area: { lat: "43", lon: -110, zoom: 11, size: 1024 } }), /numeric/);
  assert.throws(() => parseScene({ ...TETONS, area: { lat: 89, lon: -110, zoom: 11, size: 1024 } }), /off the map/);
});

test("a scene from a newer version opens with a warning", () => {
  const sc = parseScene({ ...TETONS, format: FORMAT, version: VERSION + 1 });
  assert.equal(sc.warnings.length, 1);
  assert.match(sc.warnings[0], /newer version/);
});

test("area zoom and grid size are snapped to what the app can load", () => {
  const sc = parseScene({ ...TETONS, area: { ...TETONS.area, zoom: 22.4, size: 700 } });
  assert.equal(sc.area.zoom, 15);
  assert.equal(sc.area.size, 768);
});

test("missing, malformed or out-of-area pins fall back to the defaults", () => {
  const sc = parseScene({ ...TETONS, cam: undefined, target: [0, 0], halo: "here" });
  assert.deepEqual(sc.cam, DEFAULT_UV.cam);
  assert.deepEqual(sc.target, DEFAULT_UV.target);
  assert.deepEqual(sc.halo, DEFAULT_UV.target);
  assert.deepEqual(sc.warnings.sort(), ["halo: expected [lat, lon]", "target: outside the area"]);
});

test("params: missing ones take defaults, bad ones are fixed and reported", () => {
  const { params, warnings } = sanitizeParams("vista", {
    fov: 500,              // clamped to the slider
    eye: "40",             // numeric string accepted
    shadows: "yes",        // not a boolean: default kept
    tone: "pointillism",   // unknown option: default kept
    _mist_elev: 9000,      // elevations aren't clamped (their range comes from the terrain)
    contour_above: 1500,   // renderer parameter without a control: passes through
    _secret: 1,            // private keys without a control are dropped
    nested: { a: 1 },      // so is anything that isn't a plain value
  }, TETONS.area);
  const d = defaults("vista");
  assert.equal(params.fov, 110);
  assert.equal(params.eye, 40);
  assert.equal(params.shadows, d.shadows);
  assert.equal(params.tone, d.tone);
  assert.equal(params._mist_elev, 9000);
  assert.equal(params.contour_above, 1500);
  assert.ok(!("_secret" in params) && !("nested" in params));
  assert.equal(params.sun_az, d.sun_az);
  assert.deepEqual(warnings, ["fov: 500 is outside 8–110", "shadows: expected true/false", "tone: unknown option \"pointillism\"", "_secret: dropped", "nested: dropped"]);
  for (const k of Object.keys(d)) assert.ok(k in params, `${k} present`);
});

test("params that aren't an object give defaults", () => {
  const { params, warnings } = sanitizeParams("strata", "oops", STRATA.area);
  assert.deepEqual(params, defaults("strata"));
  assert.equal(warnings.length, 1);
});

test("haze in map widths becomes kilometres for the scene's area", () => {
  const sc = parseScene(OLD_HAZE), w = areaWidthKm(sc.area);
  assert.ok(Math.abs(sc.params._haze_near_km - OLD_HAZE.params.haze_near * w) < 1e-9);
  assert.ok(Math.abs(sc.params._haze_far_km - OLD_HAZE.params.haze_far * w) < 1e-9);
  assert.ok(!("haze_near" in sc.params) && !("haze_far" in sc.params));
  // km given explicitly wins, and saved files carry km, so reopening never converts twice
  assert.equal(parseScene(TETONS).params._haze_far_km, TETONS.params._haze_far_km);
});

test("sanitising is idempotent", () => {
  for (const mode of Object.keys(MODES)) for (const pr of PRESETS.filter((p) => p.mode === mode)) {
    const once = parseScene(pr).params, twice = sanitizeParams(mode, once, pr.area);
    assert.deepEqual(twice.warnings, []);
    assert.deepEqual(twice.params, once);
  }
});

test("file names come from the scene name", () => {
  assert.equal(sceneFilename("Grand Tetons from Mount Leidy (33 km)"), "grand-tetons-from-mount-leidy-33-km.json");
  assert.equal(sceneFilename("Ñuñoa · café"), "nunoa-cafe.json");
  assert.equal(sceneFilename(""), "terrain-scene.json");
  assert.equal(sceneFilename("🏔️"), "terrain-scene.json");
});

test("new places get the fall-line strokes; presets written for the old etching default keep it", () => {
  assert.equal(defaults("vista").tone, "flow");
  const etching = PRESETS.find((p) => p.name === "Etching · Yosemite Tunnel View");
  assert.equal(parseScene(etching).params.tone, "screen");
  assert.equal(parseScene(TETONS).params.tone, "flow");
});
