"""Render a set of Strata presets + a seed sweep, as SVG (LineDream) and PNG previews."""
import pathlib
import sys

import cairosvg
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from dem import fetch_dem
from strata import Params, render, variant

OUT = pathlib.Path(__file__).parent / "renders"
OUT.mkdir(exist_ok=True)

PLACES = {
	"st_helens": (46.1914, -122.1956, 12),
	"fuji": (35.3606, 138.7274, 11),
	"matterhorn": (45.9763, 7.6586, 12),
	"grand_canyon": (36.075, -112.13, 11),
	"yosemite": (37.7400, -119.5700, 12),
	"kilimanjaro": (-3.0674, 37.3556, 12),
}

PRESETS = {
	# classic ridgeline stack, but with real hidden-line removal against the terrain
	"pleasures": ("st_helens", Params(paths="scan", count=120, pitch=24, relief=0.2, clip="circle")),
	# one continuous spiral, height pushes it sideways - a vinyl groove cut by the mountain
	"vinyl": ("fuji", Params(paths="spiral", mode="offset", turns=80, relief=0.12, highpass=8, inner=0.02, pitch=90, clip="circle", blur=1.0)),
	# concentric rings draped over the peak, seen from low and hidden behind ridges
	"halo": ("matterhorn", Params(paths="rings", count=70, pitch=32, relief=0.22, yaw=200, clip="circle")),
	# streamlines running downhill: the drainage network as veins
	"rain": ("grand_canyon", Params(paths="flow", count=9000, flow_sep=0.0045, flow_len=600, pitch=90, blur=1.2, mask="slope", mask_threshold=0.12, stroke_width=0.8)),
	# stacked terraced contours in 3D - layered paper
	"strata": ("st_helens", Params(paths="contour", count=36, pitch=30, relief=0.2, blur=2, clip="circle")),
	# engraving hatch, only where the rock is steep
	"engrave": ("yosemite", Params(paths="hatch", count=150, pitch=90, mask="slope", mask_threshold=0.18, stroke_width=0.9)),
	# warped + noise-masked scanlines: terrain dissolving into weather
	"dissolve": ("kilimanjaro", Params(paths="scan", count=150, pitch=26, relief=0.2, warp=0.04, warp_scale=0.1, mask="noise", mask_mix=0.6, mask_threshold=0.34, mask_scale=0.012, clip="circle", seed=3)),
	# contour-following streamlines lifted into 3D - wind-combed
	"combed": ("matterhorn", Params(paths="flow", angle=90, count=5000, flow_sep=0.008, flow_len=500, flow_noise=0.2, pitch=45, relief=0.2, clip="circle", stroke_width=0.8)),
	# radial rays, offset sideways: a sonar sweep
	"sonar": ("kilimanjaro", Params(paths="radial", count=240, mode="offset", relief=0.5, highpass=6, inner=0.12, pitch=90, clip="circle")),
}


def to_png(svg, bg, width=900):
	png = svg.with_suffix(".png")
	cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=width, background_color=bg)
	return png


def sheet(pngs, labels, path, cols=3, tile=600):
	rows = (len(pngs) + cols - 1) // cols
	im = Image.new("RGB", (cols * tile, rows * (tile + 28)), "#111")
	d = ImageDraw.Draw(im)
	for i, (png, label) in enumerate(zip(pngs, labels)):
		x, y = (i % cols) * tile, (i // cols) * (tile + 28)
		im.paste(Image.open(png).convert("RGB").resize((tile, tile)), (x, y))
		d.text((x + 10, y + tile + 7), label, fill="#bbb")
	im.save(path)


if __name__ == "__main__":
	only = set(sys.argv[1:])
	dems = {}
	pngs, labels = [], []
	for name, (place, p) in PRESETS.items():
		if only and name not in only:
			continue
		if place not in dems:
			lat, lon, z = PLACES[place]
			dems[place] = fetch_dem(lat, lon, zoom=z)
		svg = OUT / f"{name}.svg"
		n = render(dems[place], p, str(svg))
		pngs.append(to_png(svg, p.background))
		labels.append(f"{name}  ({place}, paths={p.paths}, mode={p.mode})")
		print(f"{name:10s} {n:6d} polylines  {svg.stat().st_size / 1e6:.1f} MB")
	if not only:
		sheet(pngs, labels, OUT / "contact_sheet.png")

		# seed sweep: same preset, different seeds -> different weather over the same mountain
		place, base = PRESETS["dissolve"]
		sweep = []
		for s in range(6):
			svg = OUT / f"seed_{s}.svg"
			render(dems[place], variant(base, seed=s, warp=0.03 + 0.015 * s), str(svg))
			sweep.append(to_png(svg, base.background))
		sheet(sweep, [f"dissolve seed={s}" for s in range(6)], OUT / "seed_sweep.png")
