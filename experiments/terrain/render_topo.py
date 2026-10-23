"""Two languages in one drawing: fall-line strokes on the shaded slopes, quiet labelled contours on the lit
slopes the strokes leave blank (Vista's `topo_*` layer). Contours and labels are their own plotter layer
(3-topo), so they can go to a finer or grey pen.
"""
import pathlib
import sys
import time

import cairosvg

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from dem import fetch_dem
from render_cirque import BETWEEN, JACKASS_PASS, LAKE, LAKE_AS_WATER, PEN, SHORT_HAZE
from render_explore import sheet
from vista import Scene, Vista, place

OUT = pathlib.Path(__file__).parent / "renders"

FALL = dict(tone="flow", flow_dir=90, flow_sep=2.4, flow_sep_max=9, flow_min_tone=0.3, shade_gamma=0.7,
			lost_edges=0.25, overshoot=3, wobble=0.6)

# name -> (dem center lat, lon, zoom), cam lat/lon, target lat/lon, scene kwargs
SCENES = {
	# Cirque of the Towers from Jackass Pass; USGS-style feet, index contours every 600 ft
	"cirque": ((*LAKE, 14), JACKASS_PASS, BETWEEN, dict(
		eye=15, target_eye=-120, fov=50, shift=-0.05, sun_az=165, sun_alt=28, exaggeration=1.0, smooth=0.5,
		topo_every=120, topo_units="ft", topo_label_every=5, topo_label_size=11,
		**FALL, **SHORT_HAZE, **LAKE_AS_WATER, **PEN)),
	# Fuji from above Kawaguchiko, low evening sun on the west face; metres, index every 500 m
	"fuji": ((35.44, 138.74, 12), (35.5150, 138.7550), (35.3606, 138.7274), dict(
		eye=650, target_eye=-1400, fov=40, shift=-0.18, sun_az=285, sun_alt=15, mist=1150, mist_lines=40,
		haze=0.3, haze_near=0.1, haze_far=0.9, topo_every=100, topo_units="m", topo_label_every=5, topo_label_size=11,
		**{**FALL, "shade_gamma": 1.0, "flow_min_tone": 0.42}, **PEN)),
	# Tunnel View: midday sun on El Capitan's south face, shadowed north-facing walls in strokes; feet
	"yosemite": ((37.735, -119.61, 12), (37.7156, -119.6773), (37.7459, -119.5332), dict(
		eye=25, target_eye=-350, fov=36, shift=-0.1, sun_az=200, sun_alt=35, mist=1290, mist_lines=30,
		haze=0.35, haze_near=0.05, haze_far=0.6, topo_every=200, topo_units="ft", topo_label_every=5, topo_label_size=11,
		**FALL, **PEN)),
}


def render(name):
	(clat, clon, z), cam, tgt, kw = SCENES[name]
	dem, info = fetch_dem(clat, clon, zoom=z, size=1024, meta=True)
	sc = place(Scene(**kw), info, cam, tgt)
	t = time.time()
	svg = OUT / f"topo_{name}.svg"
	n = Vista(dem, info, sc).render(str(svg))
	cairosvg.svg2png(url=str(svg), write_to=str(svg.with_suffix(".png")), output_width=1600, background_color=sc.paper)
	print(f"{name:10s} {n:5d} strokes  {time.time() - t:4.1f}s")
	return svg.with_suffix(".png")


if __name__ == "__main__":
	names = sys.argv[1:] or list(SCENES)
	pngs = [render(n) for n in names]
	if len(names) > 1:
		sheet(pngs, names, OUT / "topo_sheet.png", cols=2)
