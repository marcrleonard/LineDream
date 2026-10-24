"""Entry points for the terrain web app (browser/terrain): the worker hands over an elevation grid once, then asks
for renders with a mode, a dict of parameters straight from the UI, and a quality level.

    set_dem(grid, size, width_m)                 -> {"min", "max"} elevation in metres
    render(mode, params_json, quality)           -> json {"svg", "seconds", "strokes"}

mode is "vista" (perspective, vista.py) or "strata" (top-down / oblique, strata.py). Keys that aren't fields of
vista.Scene / strata.Params are ignored, so the UI can send its own bookkeeping alongside.
"""
import dataclasses
import json
import pathlib
import tempfile
import time

import numpy as np

from strata import Params, render as strata_render
from vista import Scene, Vista

DEM = None
INFO = None

# Vista: preview halves the grid, the ray count and the image; pixel-sized settings scale with the image so a
# preview looks like a small version of the full render rather than a coarser different one.
VISTA_QUALITY = {
	"preview": dict(size=512, gres=450, canvas=(800, 500)),
	"full": dict(size=1024, gres=900, canvas=(1600, 1000)),
}
VISTA_PX = ("flow_sep", "flow_sep_max", "hatch_spacing", "topo_label_size", "overshoot", "wobble", "stroke_width")
STRATA_QUALITY = {
	"preview": dict(size=300, canvas=(800, 800)),
	"full": dict(size=400, canvas=(1600, 1600)),  # 400 = strata.Params default, so presets match the original renders
}


class _Info:
	def __init__(self, width_m):
		self.width_m = width_m


def set_dem(grid, size, width_m):
	global DEM, INFO
	DEM = np.asarray(grid, dtype=np.float32).reshape(size, size)
	INFO = _Info(float(width_m))
	return {"min": float(DEM.min()), "max": float(DEM.max())}


def _tuples(v):
	return tuple(_tuples(x) for x in v) if isinstance(v, list) else v


def _fields(cls, params):
	names = {f.name for f in dataclasses.fields(cls)}
	return {k: _tuples(v) for k, v in params.items() if k in names}


def vista_scene(params, quality):
	kw = _fields(Scene, params)
	ratio = VISTA_QUALITY[quality]["canvas"][0] / Scene.canvas[0] if "canvas" not in kw else 1.0
	for k in VISTA_PX:
		kw[k] = kw.get(k, getattr(Scene, k)) * ratio
	kw.update(VISTA_QUALITY[quality])
	return Scene(**kw)


def strata_params(params, quality):
	kw = _fields(Params, params)
	ratio = STRATA_QUALITY[quality]["canvas"][0] / Params.canvas[0]
	kw["stroke_width"] = kw.get("stroke_width", Params.stroke_width) * ratio
	kw.update(STRATA_QUALITY[quality])
	return Params(**kw)


def render(mode, params_json, quality="preview"):
	if DEM is None:
		raise RuntimeError("no elevation data loaded yet")
	params = json.loads(params_json)
	out = pathlib.Path(tempfile.gettempdir()) / "terrain_app.svg"
	t = time.perf_counter()
	if mode == "vista":
		strokes = Vista(DEM, INFO, vista_scene(params, quality)).render(str(out))
	elif mode == "strata":
		strokes = strata_render(DEM, strata_params(params, quality), str(out))
	else:
		raise ValueError(f"unknown mode {mode!r}")
	return json.dumps({"svg": out.read_text(), "seconds": round(time.perf_counter() - t, 2), "strokes": strokes})
