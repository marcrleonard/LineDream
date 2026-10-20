"""Cirque of the Towers, Wind River Range, Wyoming.

Landmarks located on the DEM (z13): Lonesome Lake is the flat basin at ~3097 m, Pingora the 3628 m
summit just west of it, and Jackass Pass the ~3287 m saddle directly south of the lake.
"""
import pathlib
import sys
import time
from dataclasses import replace

import cairosvg

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from dem import fetch_dem
from render_explore import sheet, stats
from strata import Params, render as strata_render
from vista import Scene, Vista, compose, place

OUT = pathlib.Path(__file__).parent / "renders"

LAKE = (42.77776, -109.21715)
LAKE_EAST_SHORE = (42.77814, -109.20685)
PINGORA = (42.77902, -109.22573)
WOLFS_HEAD = (42.78054, -109.23311)
JACKASS_PASS = (42.76894, -109.21114)
BETWEEN = (42.7790, -109.2290)     # aim point between Pingora and Wolfs Head

PEN = dict(plotter=True, stroke_width=1.0, ink="#1c1b19", accent="#cf4a1f", paper="#f1ece2")
LAKE_AS_WATER = dict(mist=3101, mist_lines=34)   # the lake surface drawn as sparse broken water lines
SHORT_HAZE = dict(haze=0.35, haze_near=0.12, haze_far=0.7)


def run(name, sc, dem, info, fn=None):
	t = time.time()
	svg = OUT / f"cirque_{name}.svg"
	(fn or (lambda: Vista(dem, info, sc).render(str(svg))))(*([str(svg)] if fn else []))
	cairosvg.svg2png(url=str(svg), write_to=str(svg.with_suffix(".png")), output_width=1600, background_color=sc.paper)
	print(f"{name:12s} {time.time() - t:5.1f}s")
	return svg


if __name__ == "__main__":
	dem, info = fetch_dem(*LAKE, zoom=14, size=1024, meta=True)
	shots = []

	# 1. the postcard view from Jackass Pass, late light from the west: tower faces toward us fall into shadow
	base = Scene(eye=15, target_eye=-120, fov=50, shift=-0.05, sun_az=215, sun_alt=20, exaggeration=1.0, smooth=0.5,
				 tone="flow", flow_sep=2.8, flow_sep_max=15, flow_min_tone=0.3, shade_floor=0.1, lost_edges=0.25, overshoot=3, wobble=0.6, contours=((3600, "accent"),), **SHORT_HAZE, **LAKE_AS_WATER, **PEN)
	pass_view = place(base, info, JACKASS_PASS, BETWEEN)
	shots.append((run("pass", pass_view, dem, info), "jackass pass: contour-following strokes, 3600 m line in accent"))

	# 2. same view, strokes down the fall line - the towers drawn the way they were carved
	shots.append((run("pass_fall", replace(pass_view, flow_dir=90, contours=()), dem, info), "jackass pass: fall-line strokes"))

	# 3. from the lake shore at sunset, looking up at Pingora and Wolfs Head; the sun slips behind a tower
	lake_view = place(replace(base, eye=2, target_eye=350, fov=40, shift=0.12, sun_az=262, sun_alt=14, tone="flow", flow_dir=90,
							  flow_sep=2.8, flow_min_tone=0.45, tone_scale=0.85, sun_disc=0.08, sun_lines=12, contours=(), lost_edges=0.15),
					  info, LAKE_EAST_SHORE, BETWEEN)
	shots.append((run("lake_sunset", lake_view, dem, info), "lonesome lake shore: sunset behind the towers"))

	# 4. last light through a circle around Pingora; outside, only bare outlines
	inside = replace(pass_view, sun_az=255, sun_alt=8, flow_min_tone=0.3, window=("circle", -0.08, 0.1, 0.42), contours=())
	outside = replace(inside, tone="none", lost_edges=0.12, window=None)
	shots.append((run("alpenglow", inside, dem, info, lambda f: compose(dem, info, inside, outside, f)), "last-light window: tone inside, bare outlines outside"))

	# 5. night: moonlit strokes in light ink, a ring standing over Pingora
	night = place(replace(pass_view, paper="#14161a", ink="#e9e4d8", accent="#e3a940", invert=True, sun_az=120, sun_alt=25,
						  flow_sep=3.0, lost_edges=0.0, contours=(), sun_disc=0.05, sun_pos=(0.6, 0.4), sun_lines=8),
				  info, JACKASS_PASS, BETWEEN, halo_latlon=(*PINGORA, 3760, 140))
	shots.append((run("night", night, dem, info), "night: moonlit strokes, a ring over Pingora"))

	# 6. strata (round 1) on the same ground for comparison: ridgelines with hidden-line removal
	svg = OUT / "cirque_strata.svg"
	strata_render(dem, Params(paths="scan", count=130, pitch=26, relief=0.12, clip="circle", yaw=200, stroke="#1c1b19", background="#f1ece2"), str(svg))
	cairosvg.svg2png(url=str(svg), write_to=str(svg.with_suffix(".png")), output_width=1600, background_color="#f1ece2")
	shots.append((svg, "strata: ridgelines from the south-southwest"))

	sheet([s.with_suffix(".png") for s, _ in shots], [l for _, l in shots], OUT / "cirque_sheet.png")
	for s, _ in shots[:4]:
		print(s.stem, " ".join(l.strip() for l in stats(s).splitlines() if "Totals" in l or l.strip().startswith(("Length", "Path count")))[-120:])
