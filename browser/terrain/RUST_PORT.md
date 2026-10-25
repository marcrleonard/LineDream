# Porting LineDream's renderer to Rust

> Design notes, not a plan of record. Written while the terrain renderers lived in `experiments/terrain/` on the
> `terrain-strata` branch; the same files now ship as `browser/terrain/py/` (`strata.py`, `vista.py`,
> `fastpaths.py`), and `dem.py`'s job is done in the browser by `tiles.mjs`. Line counts are from that time.

**Goal:** keep writing LineDream in Python exactly as today, but have all rendering happen in one Rust engine
that runs both natively (behind the Python API) and in a web browser (compiled to WebAssembly), producing
identical output in both places.

**Recommendation:** build a single Rust crate, `linedream-core`. Expose it to Python with PyO3/maturin, and to the
browser with wasm-bindgen. Treat every scene as *data*: a small, versioned description of primitives plus
generator parameters that either engine can render. Start by porting the existing Numba kernels behind the
current Python functions. That step takes a few days, exercises the whole toolchain on real code, and gives a
measured Rust-vs-Numba number before committing to the full rewrite.

---

## 1. Where things stand

### Code inventory

| area | files | lines | notes |
|---|---|---|---|
| LineDream core | `BaseShape`, `Line`, `Ellipse`, `Rectangle`, `Group`, `Canvas`, `CircleMath` | ~800 | Thin layer: 4×4 vertex matrices → drawsvg → SVG |
| Hershey text | `hershey/`, `TextLine`, `Text` | ~2,300 | Mostly font data plus an inkex helper; `Text` uses vpype |
| Terrain: Strata (top-down / orthographic) | `strata.py` | 333 | Path families, orthographic camera, hidden-line removal |
| Terrain: Vista (perspective) | `vista.py` | 623 | Camera, shadows, per-pixel ray-cast render, hatching, streamlines, silhouettes, compose |
| Terrain: kernels | `fastpaths.py` | 332 | Numba: ray march, visibility, shadows, streamlines, Douglas–Peucker |
| Terrain: data | `dem.py` | 67 | Terrarium elevation tiles (AWS open data) → numpy grid |

The code that actually renders is about 2,000 lines, plus font data. That is a small port.

### Performance today (Jackass Pass scene, 1024² elevation grid)

| stage | numpy original | Numba (current) |
|---|---|---|
| flow hatch (streamlines) | 19.7 s | 1.1 s |
| per-pixel ray-cast render | 6.7 s | 0.6 s |
| draw: simplify + SVG | 2.9 s | 0.4 s |
| setup + cast shadows | 1.2 s | 0.5 s |
| silhouettes (visibility) | 1.1 s | 0.5 s |
| **total** | **31.4 s** | **3.6 s** |

What remains is a dozen vectorised numpy steps of 0.2–0.7 s each: resampling, Gaussian blurs, contour
tracing, projections, and many small `map_coordinates` calls.

### Why move off Python for rendering at all

- **The browser.** Numba doesn't run in Pyodide (CPython compiled to WASM), so the current terrain pipeline
  cannot run in a web page at a usable speed. Rust compiles to WASM directly.
- **Installation.** Numba, scipy and scikit-image are heavy dependencies for a generative-art library. A Rust
  extension ships as a single prebuilt wheel per platform.
- **No warm-up.** Numba compiles on first call (cached afterwards). Rust is compiled ahead of time.
- **The remaining glue.** The leftover numpy steps disappear into compiled code, and threading (rayon)
  covers whole stages rather than individual kernels.

---

## 2. Architecture

```
       your Python script (unchanged style: Line, Group, Canvas, Scene(...), Vista(...))
                                       │
                    scene description (versioned data, JSON / MessagePack)
             primitives (polylines, styles, groups) + generators (Vista params, Strata params)
                  ┌────────────────────┴─────────────────────┐
         native: PyO3 extension                      browser: WASM module
         (pip install linedream)                     (wasm-bindgen + canvas / SVG / WebGL)
                  └────────────────────┬─────────────────────┘
                              linedream-core (Rust)
     geometry · terrain pipeline · plotter optimisation · SVG writer · Hershey text
```

### Scene-as-data is the key decision

Today a script mutates a global `Canvas` draw queue and `Canvas.save()` writes SVG. In the new design:

1. Python builds a `Scene`: primitives you created directly, plus high-level generators such as `Vista(...)`
   that are stored as *parameters*, not as expanded geometry.
2. The scene serialises to a compact, versioned document.
3. Any engine renders it: the native extension (from `Canvas.save()`, as now), or the browser.

This is what makes interactive browser work cheap. A slider for sun angle, line spacing or camera height just
edits a number in the document and re-renders in WASM. No Python is involved, and the result is identical to
what Python would produce, because it is the same Rust code.

The `Canvas` singleton stays as Python convenience on top of an explicit scene object, so existing scripts
keep working.

### Crate layout

```
linedream/
  crates/
    linedream-core/      # pure Rust, no Python or JS types. Everything renders here.
      geom/              #   polyline, clip (rect/circle), dashes, Douglas-Peucker, transforms
      scene/             #   scene document types (serde), versioning, validation
      svg/               #   SVG writer with Inkscape layers (one pen per layer)
      plot/              #   line merge + greedy sort (what vpype linemerge/linesort does), stats
      text/              #   Hershey fonts (data compiled in)
      terrain/           #   optional feature: grid ops, camera, raymarch, shadow, streamlines,
                         #   contours, silhouettes, strata path families, vista compose
    linedream-py/        # PyO3 bindings + numpy interop (rust-numpy), built with maturin
    linedream-wasm/      # wasm-bindgen bindings + a minimal JS/TS API
  python/linedream/      # the Python package: Line, Group, Canvas, Scene... (thin wrappers)
  web/                   # browser viewer: load a scene document, render, parameter sliders
```

The terrain code sits behind a cargo feature flag, so the core stays small (see §6 on what belongs in core).

---

## 3. Getting Python into the browser

| option | what runs in the browser | pros | cons |
|---|---|---|---|
| **A. Python makes the scene, browser renders it** (recommended) | WASM engine only | Fast, small download, live sliders, identical output | The Python script itself runs elsewhere (locally, or a server) |
| **B. Pyodide** | CPython + numpy + the LineDream extension compiled for Pyodide | Literally your script, running in a web page | Multi-MB download; slower start; Numba unavailable (fine once the kernels are in Rust) |

Build A first; it is the foundation either way. B can be layered on top later, because maturin can build PyO3
extensions for Pyodide (the emscripten target), so the same Rust engine would serve a Python-in-browser
notebook or playground.

---

## 4. Replacing the Python dependencies

| used today | for | Rust replacement | difficulty |
|---|---|---|---|
| numpy arrays | grids, polylines | `Vec<f32>` / `ndarray`; zero-copy to Python via `rust-numpy` | easy |
| `scipy.ndimage.map_coordinates` (order 1) | bilinear sampling | the `bilinear()` already written in `fastpaths.py` | easy |
| `ndimage.zoom` | resampling the elevation grid | bilinear resample | easy |
| `ndimage.gaussian_filter` | smoothing, noise fields | separable convolution (or `image`/`imageproc`) | easy |
| `np.percentile`, `np.gradient` | normalisation, normals | `select_nth_unstable`, finite differences | easy |
| `skimage.measure.find_contours` | contours, silhouettes | marching squares + segment assembly (the `contour` crate, or about 150 lines) | moderate |
| `skimage.measure.approximate_polygon` | simplification | already ported (`fastpaths.simplify`, verified identical) | done |
| drawsvg | SVG output | hand-written writer (paths, layers, styles) | easy |
| vpype (`linemerge`, `linesort`, stats, text) | plotter prep | greedy merge/sort, k-d tree for nearest neighbour (`kiddo`) | moderate |
| PIL + urllib | tile fetch + PNG decode | native: `ureq` + `png`; browser: `fetch` + `createImageBitmap` | easy |
| cairosvg | PNG previews | `resvg` (native and WASM) | easy |
| `numpy.random.default_rng` | seeds | `rand_pcg::Pcg64` | easy, but see risks |

---

## 5. Plan and effort

Rough estimates for focused work. Each phase leaves the Python side working.

| phase | what | effort | done when |
|---|---|---|---|
| **0. Kernels to Rust** | Port `fastpaths.py` to a PyO3 extension with the same function signatures; Vista and Strata call it unchanged | a few days | Same comparison checks used for the Numba port pass (identical Strata output; Vista visually identical); benchmark vs Numba |
| **1. Core + Python API** | Primitives, transforms, groups, SVG writer in Rust; Python `Line`/`Group`/`Canvas` become wrappers | ~1 week | The existing golden SVG test passes byte for byte |
| **2. Terrain pipeline** | Move the remaining Vista/Strata stages (resample, blur, contours, silhouettes, hatching, compose) into `terrain/`; scene document for Vista/Strata params | ~1–2 weeks | All presets render from a scene document natively |
| **3. Plotter + text** | merge/sort/stats, Hershey text | a few days | Plot stats match vpype within a few percent |
| **4. Packaging** | maturin wheels for macOS (arm64/x86), Linux, Windows via CI; publish | a few days | `pip install linedream` with no compiler, Numba or scipy |
| **5. Browser viewer** | WASM build, load a scene document, canvas render, sliders, low-res preview while dragging | ~1 week for something usable | Vista scenes adjustable live in a browser |
| 6. (optional) Pyodide | build the extension for Pyodide; small playground page | days | Write and run a LineDream script in a web page |

Total to a solid MVP (phases 0–5): roughly a month.

---

## 6. What belongs in core vs. a separate package

The terrain renderers (Vista, Strata, DEM fetching) are specialised, and their dependencies (Numba, scipy,
scikit-image, network access for tiles) are far heavier than LineDream's. I recommend:

- **Core LineDream:** general plotter utilities every piece can use.
  - Bulk geometry: `Line.from_array`, `Group.extend` (PR #4)
  - Polyline simplification, clipping to a rectangle or circle, dashing
  - Plotter optimisation on save (merge + sort + stats)
  - Later, possibly a small 3D camera/projection helper
- **Separate package (e.g. `linedream-terrain`) or its own repo:**
  - Vista, Strata, elevation tile loading, presets, render scripts
  - Depends on LineDream; free to carry heavy dependencies

In the Rust design this maps onto the `terrain` cargo feature: one engine, but core users never pay for it.

---

## 7. Risks and open questions

- **Seeds won't reproduce the current renders.** numpy's `default_rng` uses PCG64 seeded through `SeedSequence`.
  Reproducing that bit-for-bit in Rust is possible but fiddly; simplest is to treat the Rust engine as a new
  seed space and re-pick favourite seeds.
- **WASM speed.**
  - WASM is single-threaded unless the page is served with cross-origin isolation headers (COOP/COEP), which
    enable `SharedArrayBuffer` and wasm threads.
  - Expect roughly 1.5–2× slower than native single-core. A full Vista render would take a few seconds in the
    browser, so live sliders need a low-resolution preview that sharpens afterwards (resolution is already a
    parameter).
  - The per-pixel ray cast is a natural later candidate for WebGPU.
- **Elevation tiles in the browser.** Fetching AWS Terrarium tiles directly from a page requires the bucket to
  allow cross-origin requests. Not yet verified; a tiny caching proxy solves it if not.
- **Floating-point drift.** Streamline packing amplifies tiny numeric differences (seen in the Numba port).
  Expect visually identical rather than byte-identical Vista output between engines and versions; Strata-style
  pipelines can stay exact.
- **API surface.** Decide which Python API is frozen (`Line`, `Group`, `Canvas`, shape styling, transforms) and
  which can change (the `Canvas` singleton becomes sugar over an explicit scene object).

### Expected performance

| target | estimate for the Jackass Pass scene |
|---|---|
| Numba (today) | 3.6 s |
| native Rust, all cores | ~1 s (2–5× faster: no numpy glue, whole-stage threading) |
| browser WASM, single thread | a few seconds full quality; well under a second at preview resolution |

These are estimates; phase 0 replaces them with measured numbers.
