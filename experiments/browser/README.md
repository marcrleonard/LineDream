# LineDream in the browser (Pyodide)

The unmodified Python (LineDream, Strata and Vista) running in a web page via [Pyodide](https://pyodide.org)
(CPython compiled to WebAssembly). This is the "how fast is it as it is?" baseline before any Rust port.

```bash
# 1. get a Pyodide release (runtime + prebuilt WebAssembly wheels for numpy, scipy, scikit-image, ...)
curl -LO https://github.com/pyodide/pyodide/releases/download/314.0.7/pyodide-314.0.7.tar.bz2
mkdir pyodide-dist && tar -xjf pyodide-314.0.7.tar.bz2 -C pyodide-dist

# 2. assemble a self-contained site (copies only the 22 packages needed, ~63 MB; no CDN at runtime)
python experiments/browser/build_site.py pyodide-dist/pyodide

# 3a. open it yourself
python -m http.server -d experiments/browser/site 8000      # http://localhost:8000

# 3b. or run it headless and print the timings as JSON (needs `pip install playwright`)
python experiments/browser/run_headless.py

# native comparison: same script, with and without numba
python experiments/browser/bench.py
LINEDREAM_NO_NUMBA=1 python experiments/browser/bench.py
```

## What runs

`bench.py` runs three workloads, identically in both places:

1. **Plain LineDream**: 3,000 random 50-point polylines, saved as an SVG string.
2. **Strata `pleasures`**: St. Helens ridgelines with orthographic hidden-line removal (768² grid).
3. **Vista, Jackass Pass with fall-line strokes**: the full perspective pipeline on a 1024² grid, timed per stage.

Numba doesn't exist in Pyodide, so `experiments/terrain/fastpaths.py` falls back automatically:
- the ray kernels (per-pixel render, visibility, cast shadows, Strata visibility) switch to vectorised numpy;
- the streamline loops run as plain Python;
- simplification uses scikit-image.

Set `LINEDREAM_NO_NUMBA=1` to run that same fallback code natively. All three environments produce the same
1,454-stroke Vista drawing.

## Results

Measured 2026-10-20 on a 4-core cloud container, headless Chromium 141, Pyodide 314.0.7 (Python 3.14.2).
Native runs are CPython 3.13. Browser numbers are the range over two runs.

| workload | native + numba | native, no numba | browser (Pyodide) | browser vs native no-numba |
|---|---|---|---|---|
| LineDream: 3,000 lines → SVG | 0.44 s | 0.42 s | 1.04–1.08 s | 2.5× |
| Strata `pleasures` | 0.30 s | 1.04 s | 1.92–2.01 s | 1.9× |
| **Vista Jackass Pass, total** | **2.79 s** | **11.8 s** | **21.9–22.3 s** | **1.9×** |
| · setup + cast shadows | 0.72 s | 1.11 s | 1.26–1.30 s | 1.2× |
| · per-pixel ray cast | 0.52 s | 4.99 s | 8.69–8.90 s | 1.8× |
| · flow hatch (streamlines) | 0.92 s | 3.93 s | 8.79–8.97 s | 2.3× |
| · silhouettes | 0.36 s | 0.78 s | 1.08–1.30 s | 1.5× |
| · draw (simplify + SVG) | 0.25 s | 1.00 s | 1.83–1.93 s | 1.9× |

Startup before the first render, browser only:

| phase | time |
|---|---|
| boot Pyodide | 2.4–3.1 s |
| load numpy / scipy / scikit-image / pillow / lxml | 6.3–6.8 s |
| install LineDream + drawsvg wheels | 0.6 s |
| fetch modules + elevation data (local server) | 0.2–0.3 s |
| import LineDream, Strata, Vista (mostly scipy / scikit-image) | 5.3–5.8 s |
| **total** | **~15–16 s** |

That startup assumes a local server. On the real web, add the 63 MB download on a first visit; the browser caches
it after that.

## What this says

- **It works today, unmodified.** A full Vista render takes about 22 s in the browser. That's fine for
  "click render, wait", but too slow for live sliders.
- **WebAssembly costs about 2× over native for the same Python code.** The bigger loss is Numba itself: about
  8× on Vista (22 s in the browser vs 2.8 s native with Numba).
- **Startup is as big a problem as compute.** About 15 s before anything draws, dominated by loading and
  importing scipy and scikit-image, which the pipeline only uses for a handful of functions (blur, resample,
  contour tracing, simplification).
- **Where a Rust/WASM core would help most:**
  - the per-pixel ray cast and the streamline tracer (17.6 of the 22 s);
  - startup: a few-MB WASM module instead of CPython plus the scientific stack.

  See `experiments/terrain/RUST_PORT.md`.
- **Cheaper interim win in Python:** replace the few scipy/scikit-image calls with numpy versions. That would
  cut roughly 6–8 s of package loading and import from startup, but wouldn't change compute time.
