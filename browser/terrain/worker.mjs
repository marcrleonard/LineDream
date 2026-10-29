// Runs the terrain renderers (py/vista.py, py/strata.py via py/terrain_app.py) in Pyodide, off the main thread.
//   -> {type: "init", indexURL, wheel}                   <- {type: "progress", text} ... {type: "ready", versions}
//   -> {type: "dem", grid: Float32Array, size, width_m}  <- {type: "dem", min, max}
//   -> {type: "features", kinds: {kind: {coords, counts}}} <- {type: "features", counts: {kind: polylines}}
//   -> {type: "render", id, mode, params, quality}       <- {type: "result", id, svg, seconds, strokes} | {type: "error", id, error}
import { CORE_PACKAGES, TERRAIN_PACKAGES } from "./packages.mjs";

const MODULES = ["fastpaths.py", "strata.py", "vista.py", "terrain_app.py"];
let py, app;

async function init({ indexURL, wheel }) {
  const progress = (text) => postMessage({ type: "progress", text });
  progress("Starting Python…");
  const { loadPyodide } = await import(new URL("pyodide.mjs", indexURL).href);
  py = await loadPyodide({ indexURL });
  progress("Loading numpy, scipy, scikit-image…");
  await py.loadPackage([...CORE_PACKAGES, ...TERRAIN_PACKAGES], { messageCallback() {} });
  progress("Installing LineDream…");
  py.globals.set("WHEEL", wheel);
  await py.runPythonAsync("import micropip\nawait micropip.install(WHEEL)");
  progress("Loading the terrain renderers…");
  py.FS.mkdirTree("/terrain");
  for (const m of MODULES) py.FS.writeFile(`/terrain/${m}`, await (await fetch(new URL(`py/${m}`, import.meta.url))).text());
  py.runPython("import sys; sys.path.insert(0, '/terrain')");
  app = py.pyimport("terrain_app");
  const versions = py.runPython(`
import sys
from importlib.metadata import version
f"LineDream {version('linedream')} · Pyodide ${py.version} · Python {sys.version.split()[0]}"
`);
  postMessage({ type: "ready", versions });
}

function setDem({ grid, size, width_m }) {
  py.globals.set("GRID", grid);
  const stats = py.runPython(`
import numpy as np, terrain_app
terrain_app.set_dem(np.asarray(GRID.to_py(), dtype=np.float32), ${size}, ${width_m})
`).toJs({ dict_converter: Object.fromEntries });
  py.globals.delete("GRID");
  postMessage({ type: "dem", ...stats });
}

// map lines for the loaded area (features.mjs pack()); a new DEM clears them
function setFeatures({ kinds }) {
  const counts = {};
  for (const [kind, { coords, counts: n }] of Object.entries(kinds)) {
    Object.entries({ KIND: kind, COORDS: coords, COUNTS: n }).forEach(([k, v]) => py.globals.set(k, v));
    counts[kind] = py.runPython(`
import numpy as np, terrain_app
terrain_app.set_features(KIND, np.asarray(COORDS.to_py()), np.asarray(COUNTS.to_py()))
`);
  }
  for (const k of ["KIND", "COORDS", "COUNTS"]) py.globals.delete(k);
  postMessage({ type: "features", counts });
}

self.onmessage = async ({ data }) => {
  try {
    if (data.type === "init") await init(data);
    else if (data.type === "dem") setDem(data);
    else if (data.type === "features") setFeatures(data);
    else if (data.type === "render") {
      const out = JSON.parse(app.render(data.mode, JSON.stringify(data.params), data.quality));
      postMessage({ type: "result", id: data.id, quality: data.quality, ...out });
    }
  } catch (e) {
    const error = String((e && e.message) || e);
    postMessage(data.type === "init" ? { type: "fatal", error } : { type: "error", id: data.id, error });
  }
};
