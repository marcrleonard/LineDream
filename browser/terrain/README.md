# LineDream Terrain

A web page that turns real elevation data into line art, separate from the playground. Deployed at `/terrain/`
(for example https://linedream.marcrleonard.com/terrain/), built by `docs/build_website.py`.

1. **Place:** pick an area on the topo map (or search, or choose a preset); elevation comes straight from the AWS
   Terrarium tiles.
2. **Camera:** drag the eye and aim handles on the top-down map; the cone shows the field of view and the compass
   shows the sun.
3. **Render:** every change re-renders (turn off **Live** to render on demand); switch **Preview | Full** to **Full** for the final drawing; **Download SVG**
   keeps the plotter layers (one pen per layer).

Two renderers, both the Python terrain experiments running unchanged in Pyodide:

- **Vista** (`py/vista.py`): a perspective view from a real spot. Tone hatching (form-following strokes, etching,
  distance rings), outlines with lost edges, labelled contours in the lit areas, haze, mist, sun disc, sky streaks,
  a floating ring, a tone window, plotter mode.
- **Strata** (`py/strata.py`): one family of curves across the whole map (scan lines, rays, a spiral, rings,
  contours, flow lines, engraving hatch), lifted in 3D or pushed sideways.

`py/fastpaths.py` holds the hot loops; it uses Numba when available and falls back to numpy / plain Python, which is
what runs in the browser. `py/terrain_app.py` is the small API the worker calls.

## Files

| file | what |
|---|---|
| `index.html` | layout and styles |
| `app.mjs` | UI: map, camera planner, controls, render queue, URL-hash state |
| `schema.mjs` | every control (defaults match `vista.Scene` / `strata.Params`) and the presets |
| `tiles.mjs` | fetches and decodes elevation tiles; hillshade for the planner |
| `worker.mjs` | Pyodide in a worker: loads numpy/scipy/scikit-image + the LineDream wheel, runs renders |
| `py/` | the renderers |

The whole scene (place, camera, mode, parameters) is kept in the URL hash, so a link reproduces a drawing.

## Far views

Vista only knows the ground inside the loaded square (512–1024 samples), so the camera and everything you want to
see (plus a little beyond it) have to be inside it. To look at a range from 30+ km away: zoom the map out and
**Use this view** (your eye and aim stay put if they're still inside), drag the eye out, then **Frame eye + aim** to
reload just the ground you can see at the finest zoom that fits. At zoom 11 (about 55 m per sample) a range 30 km
away still renders crisply. Haze is set in kilometres, so it means the same thing whatever area is loaded; **Earth
curvature** sinks distant ground (about 75 m at 33 km) and matters past roughly 20 km. See the two Grand Teton presets.

## Breakup

Vista can break its strokes into dashes that shrink to dots, so a single pen can suggest light and texture without
going grey (**Breakup**, under the controls). **Tails** (the default for new scenes) lets each stroke trail off into a
few dots at its ends; **Artist** dissolves strokes into the light: solid in shadow, stippled on the lit faces, with a
little dry-brush skipping. **Custom** exposes the four strengths (light, dry brush, tails, distance). Outlines are never
broken. Every dash is a pen lift, so heavy breakup plots slower; **Dash length** trades texture for plot time. Presets
made before breakup existed keep it off.

## Compose

Put the eye somewhere and point roughly at what you want, then press **Compose**. It finds the highest summit the eye
can actually see within 30° of that direction and aims at it, then sets what the presets were tuned by hand to have:
a lens that fits about 10 km of mountain across the frame (so a range 30 km away gets ~19°, not the 55° default), the
summit a third of the way down the frame, a low sun from the front-left, and haze and Earth curvature for that
distance. The usual reason a new place looks flat is the light: with the sun behind you or behind the mountain every
face is lit alike. New scenes also start with the fall-line strokes rather than a plain etching.

## Walking around

In Vista, the pad in the corner of the drawing (or the keyboard) moves the camera like a game: **W A S D** or **↑ ↓**
walk and step sideways, **← →** turn, **E / Q** rise and sink, **R / F** look up and down; hold **Shift** for bigger
steps. Eye and aim move together and fly level, so altitude, heading and pitch hold while you move; the eye only
rises where the ground comes up to meet it. Steps scale with the scene: about 8% of the distance to the aim point per step, turns of a sixth of
the field of view, height in ×1.4 steps. The drawing shifts at once as a rough preview of the move and is replaced
when the new render lands. Walk off the loaded square and a new area is loaded around you.

## Saving scenes

There's no server, so scenes live in this browser, in files and in links. The scene bar under the drawing: **Save to My
scenes** keeps the current scene under a name in **My scenes** (top of the preset menu; stored in localStorage, so per
browser), and **Delete from My scenes** removes the one selected. **Download .json** saves it as a file (area, eye,
aim, renderer and every parameter); **Open .json…**, or dropping the file on the drawing, brings it back. **Copy
link** copies the
address, which holds the same scene. A saved file has exactly the shape of a preset in `schema.mjs` (plus a
`format`/`version` header), so a scene you like can be pasted into `PRESETS` as is. Files and links are checked on
the way in (`scene.mjs`): values are clamped to their sliders, unknown options reset, and what was fixed is logged
to the console. Older links (from before the scene format) still open.

## Tests

```bash
cd browser && npm run test:terrain      # node --test: scene format, presets, files, links, My scenes, Compose
```

## Running locally

```bash
uv run --extra docs python docs/build_website.py    # builds public/, including public/terrain/
python -m http.server -d public 8000                # http://localhost:8000/terrain/
```

Query parameters: `?pyodide=<url>` loads Pyodide from a local distribution instead of the jsDelivr CDN;
`?wheel=<url>` installs a specific LineDream wheel.

## Speed

Measured in headless Chromium (Pyodide 314.0.7) on a 4-core machine: about 15–20 s to start Python the first time
(about 60 MB, cached by the browser afterwards), previews in 1–6 s, full-quality Vista renders in about 15–20 s.
Strata is faster (about 1 s previews). See `experiments/browser/README.md` on the `terrain-strata` branch for the
breakdown, and `experiments/terrain/RUST_PORT.md` for how a Rust/WebAssembly core would make it interactive.
