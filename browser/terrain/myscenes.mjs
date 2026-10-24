// "My scenes": saved scenes kept in this browser's localStorage, one JSON array of scene objects (the same shape as a
// saved file, see scene.mjs), keyed by name. Storage is passed in so it can be tested under Node, and because it can
// be missing or throw (private windows, blocked site data): reads then give an empty list; writes throw, and the app
// says the scene wasn't kept and offers the file download instead.
import { parseScene } from "./scene.mjs";

export const STORAGE_KEY = "linedream-terrain/my-scenes";

function valid(s) {
  if (!s || typeof s.name !== "string" || !s.name.trim()) return false;
  try { parseScene(s); return true; } catch { return false; }
}

export function listMyScenes(storage) {
  let raw;
  try { raw = JSON.parse(storage?.getItem(STORAGE_KEY) ?? "[]"); } catch { return []; }
  return Array.isArray(raw) ? raw.filter(valid) : [];
}

// Add a scene, replacing one with the same name. Returns the new list.
export function saveMyScene(storage, scene) {
  if (!valid(scene)) throw new Error("a scene needs a name");
  const list = listMyScenes(storage);
  const i = list.findIndex((s) => s.name === scene.name);
  if (i >= 0) list[i] = scene;
  else list.push(scene);
  storage.setItem(STORAGE_KEY, JSON.stringify(list));
  return list;
}

export function deleteMyScene(storage, name) {
  const list = listMyScenes(storage).filter((s) => s.name !== name);
  storage.setItem(STORAGE_KEY, JSON.stringify(list));
  return list;
}
