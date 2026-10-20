// Runs the LineDream test suite under Pyodide in Node.
//
//   uv build --wheel                      # from the repo root, puts the wheel in dist/
//   cd browser && npm install && npm test
//
// PYODIDE_INDEX_URL points at a full Pyodide distribution (a local unpacked release, say); without it the
// packages come from the jsDelivr CDN. Set LINEDREAM_TERRAIN=1 to also load and import scipy and scikit-image.
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";
import { CORE_PACKAGES, TERRAIN_PACKAGES } from "./packages.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const dist = path.join(root, "dist");
const wheel = readdirSync(dist).filter((f) => /^linedream-.*\.whl$/.test(f)).sort().pop();
if (!wheel) throw new Error(`no LineDream wheel in ${dist}; run "uv build --wheel" first`);

const terrain = process.env.LINEDREAM_TERRAIN === "1";
const py = await loadPyodide(process.env.PYODIDE_INDEX_URL ? { indexURL: process.env.PYODIDE_INDEX_URL } : {});
await py.loadPackage([...CORE_PACKAGES, "pytest", ...(terrain ? TERRAIN_PACKAGES : [])]);

// Install the built wheel, not the source tree, so this also checks the wheel's metadata resolves under micropip.
py.FS.mkdirTree("/wheels");
py.FS.writeFile(`/wheels/${wheel}`, readFileSync(path.join(dist, wheel)));
py.FS.mkdirTree("/tests");
for (const f of readdirSync(path.join(root, "tests"))) {
  if (/\.(py|svg)$/.test(f) && f !== "test_output.svg") py.FS.writeFile(`/tests/${f}`, readFileSync(path.join(root, "tests", f)));
}

py.globals.set("WHEEL", `emfs:/wheels/${wheel}`);
py.globals.set("TERRAIN", terrain);
const status = await py.runPythonAsync(`
import sys, micropip
from importlib.metadata import version
await micropip.install(WHEEL)

import LineDream, numpy, PIL, lxml
print(f"Python {sys.version.split()[0]} on {sys.platform}: LineDream {version("linedream")}, "
      f"numpy {numpy.__version__}, pillow {PIL.__version__}, lxml {lxml.__version__}")
if TERRAIN:
    import scipy, skimage
    from scipy import ndimage
    from skimage import measure
    print(f"scipy {scipy.__version__}, scikit-image {skimage.__version__}")

import pytest
pytest.main(["-v", "-p", "no:cacheprovider", "/tests"])
`);
process.exit(status);
