"""One benchmark, run unchanged natively and in the browser (Pyodide).

    python experiments/browser/bench.py                        # native, numba if installed
    LINEDREAM_NO_NUMBA=1 python experiments/browser/bench.py   # native, the browser's code path

In the browser, index.html imports this module and calls run(data_dir).
"""
import json
import os
import pathlib
import platform
import sys
import tempfile
import time
from dataclasses import replace

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
if (HERE.parent / "terrain").exists():  # native checkout; in the browser the modules sit next to this file
	sys.path.insert(0, str(HERE.parent / "terrain"))

import fastpaths  # noqa: E402
from dem import DemInfo  # noqa: E402
from LineDream import Canvas, Line  # noqa: E402
from strata import Params, render as strata_render  # noqa: E402
from vista import Scene, Vista, place  # noqa: E402

JACKASS_PASS = (42.76894, -109.21114)
BETWEEN = (42.7790, -109.2290)
PASS_FALL = dict(
	eye=15, target_eye=-120, fov=50, shift=-0.05, sun_az=215, sun_alt=20, exaggeration=1.0, smooth=0.5,
	tone="flow", flow_dir=90, flow_sep=2.8, flow_sep_max=15, flow_min_tone=0.3, shade_floor=0.1, lost_edges=0.25,
	overshoot=3, wobble=0.6, haze=0.35, haze_near=0.12, haze_far=0.7, mist=3101, mist_lines=34,
	plotter=True, stroke_width=1.0, ink="#1c1b19", accent="#cf4a1f", paper="#f1ece2",
)


def load(data_dir, name):
	grid = np.load(pathlib.Path(data_dir) / f"{name}.npy")
	meta = json.loads((pathlib.Path(data_dir) / f"{name}.json").read_text())
	return grid, DemInfo(**meta)


def timed(results, key, fn):
	t = time.perf_counter()
	out = fn()
	results[key] = round(time.perf_counter() - t, 3)
	return out


def run(data_dir=HERE / "data", log=print):
	tmp = pathlib.Path(tempfile.gettempdir())
	R = {"python": sys.version.split()[0], "platform": platform.platform(), "numba": fastpaths.HAVE_NUMBA}
	svgs = {}

	# 1. plain LineDream: 3000 random polylines of 50 points, saved as SVG
	def plain():
		Canvas.flush()
		Canvas.width, Canvas.height = 1000, 1000
		rng = np.random.default_rng(0)
		for _ in range(3000):
			Line.from_array(np.cumsum(rng.normal(size=(50, 2)), axis=0) + 500)
		return Canvas.save("", as_string=True)
	svg = timed(R, "linedream_3000_lines", plain)
	log(f"linedream 3000 lines: {R['linedream_3000_lines']}s")

	# 2. strata 'pleasures': ridgelines with orthographic hidden-line removal
	helens, _ = load(data_dir, "st_helens")
	out = tmp / "strata.svg"
	timed(R, "strata_pleasures", lambda: strata_render(helens, Params(paths="scan", count=120, pitch=24, relief=0.2, clip="circle"), str(out)))
	svgs["strata"] = out.read_text()
	log(f"strata pleasures: {R['strata_pleasures']}s")

	# 3. vista: Jackass Pass, fall-line strokes, timed per stage
	cirque, info = load(data_dir, "cirque")
	sc = place(Scene(**PASS_FALL), info, JACKASS_PASS, BETWEEN)
	v = timed(R, "vista_setup", lambda: Vista(cirque, info, sc))
	v.strokes = []
	timed(R, "vista_gbuffer", v.gbuffer)
	timed(R, "vista_flow_hatch", lambda: v.flow_hatch(sc.flow_dir))
	timed(R, "vista_silhouettes", v.silhouettes)
	timed(R, "vista_rest", lambda: (v.contours(), v.mist_surface(), v.sky()))
	out = tmp / "vista.svg"
	timed(R, "vista_draw", lambda: v.draw(v.strokes, str(out)))
	R["vista_strokes"] = len(v.strokes)
	R["vista_total"] = round(sum(R[k] for k in R if k.startswith("vista_") and k not in ("vista_strokes", "vista_total")), 3)
	svgs["vista"] = out.read_text()
	log(f"vista total: {R['vista_total']}s ({R['vista_strokes']} strokes)")
	return R, svgs


if __name__ == "__main__":
	from build_site import ensure_data
	ensure_data()
	results, _ = run()
	print(json.dumps(results, indent=2))
