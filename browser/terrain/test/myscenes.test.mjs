// My scenes in localStorage (node --test browser/terrain/test/)
import { test } from "node:test";
import assert from "node:assert/strict";
import { PRESETS } from "../schema.mjs";
import { parseScene, sceneFromState } from "../scene.mjs";
import { STORAGE_KEY, deleteMyScene, listMyScenes, saveMyScene } from "../myscenes.mjs";

class MemoryStorage {
  constructor() { this.m = new Map(); }
  getItem(k) { return this.m.has(k) ? this.m.get(k) : null; }
  setItem(k, v) { this.m.set(k, String(v)); }
}

function sceneNamed(name, i = 0) {
  const sc = parseScene(PRESETS[i]);
  return sceneFromState({ ...sc, params: { [sc.mode]: sc.params } }, name);
}

test("empty storage lists nothing", () => {
  assert.deepEqual(listMyScenes(new MemoryStorage()), []);
  assert.deepEqual(listMyScenes(null), []);
});

test("saved scenes come back in the order they were saved, and open as they were", () => {
  const st = new MemoryStorage();
  saveMyScene(st, sceneNamed("Dawn", 0));
  saveMyScene(st, sceneNamed("Dusk", 3));
  const list = listMyScenes(st);
  assert.deepEqual(list.map((s) => s.name), ["Dawn", "Dusk"]);
  const back = parseScene(list[1]), orig = parseScene(sceneNamed("Dusk", 3));
  assert.deepEqual(back.params, orig.params);
  assert.deepEqual(back.area, orig.area);
});

test("saving under an existing name replaces it in place", () => {
  const st = new MemoryStorage();
  saveMyScene(st, sceneNamed("A", 0));
  saveMyScene(st, sceneNamed("B", 1));
  saveMyScene(st, sceneNamed("A", 2));
  const list = listMyScenes(st);
  assert.deepEqual(list.map((s) => s.name), ["A", "B"]);
  assert.deepEqual(list[0].area, sceneNamed("A", 2).area);
});

test("deleting removes only that name", () => {
  const st = new MemoryStorage();
  for (const n of ["A", "B", "C"]) saveMyScene(st, sceneNamed(n));
  assert.deepEqual(deleteMyScene(st, "B").map((s) => s.name), ["A", "C"]);
  assert.deepEqual(listMyScenes(st).map((s) => s.name), ["A", "C"]);
  assert.deepEqual(deleteMyScene(st, "nope").map((s) => s.name), ["A", "C"]);
});

test("a scene without a name isn't saved", () => {
  const st = new MemoryStorage();
  assert.throws(() => saveMyScene(st, sceneNamed("   ")), /needs a name/);
  assert.equal(st.getItem(STORAGE_KEY), null);
});

test("corrupt storage reads as empty, and broken entries are skipped", () => {
  const st = new MemoryStorage();
  st.setItem(STORAGE_KEY, "{not json");
  assert.deepEqual(listMyScenes(st), []);
  st.setItem(STORAGE_KEY, JSON.stringify({ a: 1 }));
  assert.deepEqual(listMyScenes(st), []);
  st.setItem(STORAGE_KEY, JSON.stringify([sceneNamed("Good"), { name: "Bad", mode: "cubism" }, null, 7, { ...sceneNamed("x"), name: "" }]));
  assert.deepEqual(listMyScenes(st).map((s) => s.name), ["Good"]);
  // and saving over a corrupt store starts a clean one
  st.setItem(STORAGE_KEY, "garbage");
  saveMyScene(st, sceneNamed("Fresh"));
  assert.deepEqual(listMyScenes(st).map((s) => s.name), ["Fresh"]);
});

test("storage that throws: reads are empty, writes report the failure", () => {
  const blocked = { getItem() { throw new Error("SecurityError"); }, setItem() { throw new Error("QuotaExceededError"); } };
  assert.deepEqual(listMyScenes(blocked), []);
  assert.throws(() => saveMyScene(blocked, sceneNamed("A")), /QuotaExceeded/);
});
