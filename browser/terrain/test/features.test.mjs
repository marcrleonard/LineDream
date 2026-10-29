// Map features: vector tile decoding, clipping, tile choice (node --test browser/terrain/test/)
// fixtures/sample.mvt was written by the Python mapbox-vector-tile encoder, so the decoder is checked against an
// independent implementation rather than against itself.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { classify, clipPolyline, decodeTile, pack, tileFeatures, tilesFor, vectorZoom, MAX_ACROSS } from "../features.mjs";
import { areaMeta } from "../scene.mjs";

const sample = () => decodeTile(readFileSync(new URL("fixtures/sample.mvt", import.meta.url)));

test("decodes layers, properties of every value type, and geometry", () => {
  const layers = sample();
  assert.deepEqual(Object.keys(layers).sort(), ["poi", "transportation", "water", "waterway"]);
  const t = layers.transportation;
  assert.equal(t.extent, 4096);
  assert.equal(t.features.length, 4);
  const [path, primary] = t.features;
  assert.deepEqual(path.props, { class: "path", subclass: "footway", layer: 1 });
  assert.equal(path.type, 2);
  assert.deepEqual(path.parts, [[[100, 100], [2000, 100], [2000, 3000]]]);
  assert.equal(primary.props.oneway, true);
  assert.equal(primary.props.width, 7.5);
  assert.deepEqual(primary.parts, [[[-50, 2048], [4200, 2048]]]);
  assert.equal(layers.water.features[0].props.elev, -12);
  const ring = layers.water.features[0].parts[0];
  assert.equal(ring.length, 5);
  assert.deepEqual(ring[0], ring[4], "polygon rings come back closed");
  assert.deepEqual(layers.poi.features[0].parts, [[[5, 5]]]);
});

test("classifies roads, trails, rivers and lakes; skips clutter and tunnels", () => {
  assert.equal(classify("transportation", { class: "primary" }, 2), "roads");
  assert.equal(classify("transportation", { class: "track" }, 2), "roads");
  assert.equal(classify("transportation", { class: "path", subclass: "footway" }, 2), "trails");
  assert.equal(classify("transportation", { class: "service" }, 2), null);
  assert.equal(classify("transportation", { class: "minor", brunnel: "tunnel" }, 2), null);
  assert.equal(classify("transportation", { class: "path" }, 3), null, "pedestrian areas are polygons");
  assert.equal(classify("waterway", { class: "stream" }, 2), "rivers");
  assert.equal(classify("waterway", { class: "ditch" }, 2), null);
  assert.equal(classify("water", { class: "lake" }, 3), "lakes");
  assert.equal(classify("water", { class: "swimming_pool" }, 3), null);
});

test("clipPolyline keeps the inside pieces and cuts at the edges", () => {
  assert.deepEqual(clipPolyline([[-1, 0.5], [2, 0.5]], 0, 0, 1, 1), [[[0, 0.5], [1, 0.5]]]);
  // in, out, back in: two pieces
  const pieces = clipPolyline([[0.2, 0.5], [0.5, 2], [0.8, 0.5]], 0, 0, 1, 1);
  assert.equal(pieces.length, 2);
  assert.deepEqual(pieces[0][0], [0.2, 0.5]);
  assert.ok(Math.abs(pieces[0][1][1] - 1) < 1e-12);
  assert.deepEqual(pieces[1].at(-1), [0.8, 0.5]);
  assert.deepEqual(clipPolyline([[2, 2], [3, 3]], 0, 0, 1, 1), []);
  assert.deepEqual(clipPolyline([[0.1, 0.1], [0.2, 0.2], [0.3, 0.1]], 0, 0, 1, 1), [[[0.1, 0.1], [0.2, 0.2], [0.3, 0.1]]]);
});

test("vector zoom: as fine as possible within MAX_ACROSS tiles, never coarser than the area's own zoom", () => {
  const cirque = areaMeta({ lat: 42.77776, lon: -109.21715, zoom: 14, size: 1024 });
  assert.equal(vectorZoom(cirque), 14);
  const yosemite = areaMeta({ lat: 37.735, lon: -119.61, zoom: 12, size: 1024 });
  assert.equal(vectorZoom(yosemite), 12);
  const small = areaMeta({ lat: 37.735, lon: -119.61, zoom: 12, size: 512 });
  assert.equal(vectorZoom(small), 13);
  const deep = areaMeta({ lat: 45.98, lon: 7.7, zoom: 15, size: 1024 });
  assert.equal(vectorZoom(deep), 14);
  for (const m of [cirque, small, deep]) {
    const n = Math.sqrt(tilesFor(m).length);
    assert.ok(n <= MAX_ACROSS, `${n} tiles across`);
  }
});

test("tiles cover the area, and features land in grid coordinates clipped to it", () => {
  // an area at zoom 14 whose grid starts exactly on a tile corner, two tiles across
  const meta = { zoom: 14, size: 512, x0: 256 * 100, y0: 256 * 200 };
  assert.deepEqual(tilesFor(meta, 14), [[14, 100, 200], [14, 101, 200], [14, 102, 200], [14, 100, 201], [14, 101, 201], [14, 102, 201], [14, 100, 202], [14, 101, 202], [14, 102, 202]]);
  const out = tileFeatures(sample(), [14, 100, 200], meta);
  assert.equal(out.trails.length, 1);
  const [u, v] = out.trails[0][0];
  assert.ok(Math.abs(u - 100 / 4096 / 2) < 1e-9 && Math.abs(v - 100 / 4096 / 2) < 1e-9);
  // the primary road overshoots the tile on both sides (the tile buffer): clipped to the tile, so x in 0..0.5
  assert.equal(out.roads.length, 1);
  const xs = out.roads[0].map((p) => p[0]);
  assert.deepEqual([Math.min(...xs), Math.max(...xs)], [0, 0.5]);
  assert.equal(out.rivers.length, 1);
  assert.equal(out.lakes.length, 1);
  // a tile half outside the area: only the inside half of the road survives
  const shifted = { ...meta, x0: meta.x0 + 128 };
  const xs2 = tileFeatures(sample(), [14, 100, 200], shifted).roads[0].map((p) => p[0]);
  assert.deepEqual([Math.min(...xs2), Math.max(...xs2)], [0, 0.25]);
});

test("pack flattens polylines for the worker", () => {
  const p = pack({ roads: [[[0, 0], [1, 1]], [[0.5, 0.5], [0.25, 0.75], [0, 1]]], lakes: [] });
  assert.deepEqual([...p.roads.counts], [2, 3]);
  assert.deepEqual([...p.roads.coords], [0, 0, 1, 1, 0.5, 0.5, 0.25, 0.75, 0, 1]);
  assert.equal(p.lakes.coords.length, 0);
});
