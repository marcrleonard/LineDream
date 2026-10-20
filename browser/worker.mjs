// Runs Pyodide off the main thread, so the page stays responsive and a run can be cancelled by terminating the worker.
//   -> {type: "init", indexURL, wheel}      <- {type: "progress", text} ... {type: "ready", versions} | {type: "fatal", error}
//   -> {type: "run", id, code}              <- {type: "result", id, svg} | {type: "error", id, error}
import { CORE_PACKAGES } from "./packages.mjs";

let py;

async function init({ indexURL, wheel }) {
  const progress = (text) => postMessage({ type: "progress", text });
  progress("Starting Python…");
  const { loadPyodide } = await import(new URL("pyodide.mjs", indexURL).href);
  py = await loadPyodide({ indexURL });
  progress("Loading numpy, pillow, lxml…");
  await py.loadPackage(CORE_PACKAGES, { messageCallback() {} });
  progress("Installing LineDream…");
  py.globals.set("WHEEL", wheel);
  await py.runPythonAsync(`
import micropip
await micropip.install(WHEEL)
`);
  const versions = py.runPython(`
import sys
from importlib.metadata import version
f"LineDream {version('linedream')} · Pyodide ${py.version} · Python {sys.version.split()[0]}"
`);
  postMessage({ type: "ready", versions });
}

self.onmessage = async ({ data }) => {
  if (data.type === "init") {
    try { await init(data); }
    catch (e) { postMessage({ type: "fatal", error: String((e && e.stack) || e) }); }
  } else if (data.type === "run") {
    try {
      const svg = await py.runPythonAsync(data.code);
      if (typeof svg !== "string") throw new Error("The last line should return SVG text, e.g. Canvas.save('', as_string=True)");
      postMessage({ type: "result", id: data.id, svg });
    } catch (e) {
      postMessage({ type: "error", id: data.id, error: e.message || String(e) });
    }
  }
};
