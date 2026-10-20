"""Round 3: form-following hatch, lost edges, hand wobble, split-light windows, sun sweeps, plotter mode."""
import pathlib
import subprocess
import sys
import time
from dataclasses import replace

import cairosvg
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from dem import fetch_dem
from render_vistas import VISTAS
from vista import Scene, Vista, compose, place

OUT = pathlib.Path(__file__).parent / "renders"
PEN = dict(plotter=True, frame=True, stroke_width=1.0, ink="#1c1b19", accent="#cf4a1f")


def scene(name, **kw):
	(clat, clon, z), cam, tgt, base = VISTAS[name]
	dem, info = fetch_dem(clat, clon, zoom=z, size=1024, meta=True)
	base = {k: v for k, v in base.items() if k != "halo_latlon"}
	return dem, info, place(Scene(**{**base, **kw}), info, cam, tgt)


def png(svg, bg, w=1600):
	cairosvg.svg2png(url=str(svg), write_to=str(svg.with_suffix(".png")), output_width=w, background_color=bg)
	return svg.with_suffix(".png")


def stats(svg):
	'''Pen-down / pen-up distance after vpype merges + sorts, on an A3 sheet.'''
	r = subprocess.run(["vpype", "read", str(svg), "scaleto", "40cm", "27cm", "linemerge", "-t", "0.3mm",
						"linesort", "stat"], capture_output=True, text=True)
	return r.stdout


def run(name, dem, info, sc, fn=None):
	t = time.time()
	svg = OUT / f"x_{name}.svg"
	(fn or (lambda: Vista(dem, info, sc).render(str(svg))))()
	p = png(svg, sc.paper)
	print(f"--- {name}  {time.time() - t:.1f}s")
	return p


def sheet(paths, labels, out, cols=3, tw=800):
	th = int(tw * 0.625)
	rows = (len(paths) + cols - 1) // cols
	im = Image.new("RGB", (cols * tw, rows * (th + 24)), "#f1ece2")
	d = ImageDraw.Draw(im)
	for i, (p, l) in enumerate(zip(paths, labels)):
		x, y = (i % cols) * tw, (i // cols) * (th + 24)
		im.paste(Image.open(p).convert("RGB").resize((tw, th)), (x, y))
		d.text((x + 12, y + th + 5), l, fill="#555")
	im.save(out)


if __name__ == "__main__":
	shots = []

	# 1. form-following hatch + lost edges + hand wobble
	dem, info, sc = scene("yosemite", tone="flow", cross=0.0, lost_edges=0.25, overshoot=4, wobble=0.8, sky_lines=4)
	shots.append((run("yosemite_flow", dem, info, sc), "yosemite: contour-following hatch, lost edges, wobble"))

	# 2. fall-line strokes, plotter-ready (2 pens, haze = dashes)
	dem, info, sc = scene("fuji", tone="flow", flow_dir=90, flow_sep=3.0, flow_sep_max=16, lost_edges=0.2, wobble=0.6, **PEN)
	shots.append((run("fuji_fall", dem, info, sc), "fuji: fall-line strokes, plotter mode"))

	# 3. split light: inside the circle is sunrise, outside is sunset - same mountain, same camera
	dem, info, a = scene("fuji", tone="flow", flow_sep=3.0, sun_az=95, sun_alt=8, sun_disc=0, window=("circle", 0.0, 0.05, 0.36), **PEN)
	b = replace(a, tone="screen", hatch_angle=-20, sun_az=275, sun_alt=6, window=None, sun_disc=0.12, sun_pos=(0.62, 0.32))
	svg = OUT / "x_fuji_split.svg"
	shots.append((run("fuji_split", dem, info, a, lambda: compose(dem, info, a, b, str(svg))), "fuji: sunrise inside / sunset outside"))

	# 4. split mode: canyon - inside full tone, outside only the accent rim + lost-edge outlines
	dem, info, a = scene("canyon", tone="flow", window=("rect", -0.62, -0.42, 0.18, 0.28), contours=((2150, "accent"),), **PEN)
	b = replace(a, tone="none", lost_edges=0.45, window=None)
	svg = OUT / "x_canyon_split.svg"
	shots.append((run("canyon_split", dem, info, a, lambda: compose(dem, info, a, b, str(svg))), "canyon: tone only through the window"))

	# 5. night, inverted flow (light ink records where the moon hits)
	dem, info, sc = scene("helens_night", tone="flow", flow_sep=3.2, invert=True, sun_az=80, sun_alt=15, lost_edges=0.0, wobble=0.5)
	shots.append((run("helens_flow", dem, info, sc), "st helens: moonlit flow hatch"))

	# 6. matterhorn, fall-line strokes only, no outlines at all
	dem, info, sc = scene("matterhorn", tone="flow", flow_dir=90, silhouettes=False, flow_sep=2.4, flow_sep_max=12, flow_min_tone=0.25, shade_floor=0.35, haze=0.1, **PEN)
	shots.append((run("matterhorn_fall", dem, info, sc), "matterhorn: strokes only, no outlines"))

	sheet([p for p, _ in shots], [l for _, l in shots], OUT / "explore_sheet.png")

	# sun sweep: one view, six hours of light
	dem, info, base = scene("yosemite", tone="flow", lost_edges=0.3, cross=0.0, sky_lines=0, contours=(), mist_lines=20, **PEN)
	frames = []
	for i, (az, alt) in enumerate([(100, 8), (130, 25), (170, 45), (210, 35), (245, 18), (270, 5)]):
		svg = OUT / f"x_sweep_{i}.svg"
		Vista(dem, info, replace(base, sun_az=az, sun_alt=alt, seed=i)).render(str(svg))
		frames.append(png(svg, base.paper, 900))
	sheet(frames, [f"sun az {a} / alt {b}" for a, b in [(100, 8), (130, 25), (170, 45), (210, 35), (245, 18), (270, 5)]], OUT / "sweep_sheet.png")

	for n in ["fuji_fall", "fuji_split", "canyon_split", "matterhorn_fall"]:
		print(n, stats(OUT / f"x_{n}.svg"))
