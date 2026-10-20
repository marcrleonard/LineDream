"""Perspective 'vista' renders from real viewpoints."""
import pathlib
import sys
import time

import cairosvg

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from dem import fetch_dem
from vista import Scene, Vista, place

OUT = pathlib.Path(__file__).parent / "renders"
OUT.mkdir(exist_ok=True)

NIGHT = dict(paper="#14161a", ink="#e9e4d8", accent="#e3a940")

# name -> (dem center lat, lon, zoom), cam lat/lon, target lat/lon, scene kwargs
VISTAS = {
	# Tunnel View, after Ansel Adams' "Clearing Winter Storm": mist in the valley floor
	"yosemite": ((37.735, -119.61, 12), (37.7156, -119.6773), (37.7459, -119.5332), dict(
		eye=25, target_eye=-350, fov=36, shift=-0.1, shade_floor=0.12, hatch_angle=-8, cross=0.85, sun_az=235, sun_alt=20,
		mist=1290, mist_lines=40, rings=360, haze=0.55, haze_near=0.05, haze_far=0.6,
		contours=((2400, "accent"),), sky_lines=7)),
	# Matterhorn at first light from above Riffelsee: one accent line marks 3800 m
	"matterhorn": ((45.98, 7.70, 13), (45.9877, 7.7570), (45.9763, 7.6586), dict(
		eye=10, target_eye=-200, fov=24, shift=-0.2, sun_az=120, sun_alt=10, hatch_angle=12, cross=0.9, smooth=0, exaggeration=1.6, shade_floor=0.08,
		sun_disc=0.11, sun_pos=(-0.5, 0.3), sun_lines=12,
		rings=380, haze=0.2, haze_near=0.03, haze_far=0.5, contours=((3800, "accent"),))),
	# Fuji from Kawaguchiko at dusk: sea of clouds, snowcap contours, sun disc behind the slope
	"fuji": ((35.44, 138.74, 12), (35.5150, 138.7550), (35.3606, 138.7274), dict(
		eye=650, target_eye=-1400, fov=40, shift=-0.18, sun_az=275, sun_alt=6, hatch_angle=-20,
		mist=1150, mist_lines=55, rings=300, haze=0.45, haze_near=0.1, haze_far=0.8,
		contour_every=150, contour_above=3050, sun_disc=0.17, sun_pos=(0.42, 0.06), sun_lines=17, sky_lines=5)),
	# Grand Canyon from the south rim at sunset: deep shadow hatching, rim traced in one line
	"canyon": ((36.10, -112.12, 12), (36.0617, -112.1077), (36.12, -112.11), dict(
		eye=15, target_eye=-450, fov=55, shift=0.0, sun_az=255, sun_alt=13, hatch_spacing=3.4, tone_scale=0.8,
		window=("circle", 0.12, 0.0, 0.5),
		rings=420, haze=0.7, haze_near=0.03, haze_far=0.55, contours=((2150, "accent"),), silhouettes=True)),
	# St. Helens at night from Johnston Ridge: a ring hovers over the crater, valleys drowned in fog
	"helens_night": ((46.24, -122.20, 12), (46.2766, -122.2172), (46.2000, -122.1890), dict(
		eye=20, target_eye=-200, fov=50, shift=-0.1, sun_az=85, sun_alt=18, shade_floor=0.1, shadows=True,
		mist=1150, mist_lines=45, rings=280, haze=0.55, haze_near=0.05, haze_far=0.7,
		sun_disc=0.06, sun_pos=(-0.55, 0.42), sun_lines=9, sky_lines=0, invert=True, hatch_spacing=3.4,
		halo_latlon=(46.2000, -122.1890, 3050, 1100), **NIGHT)),
}


def render(name):
	(clat, clon, z), cam, tgt, kw = VISTAS[name]
	dem, info = fetch_dem(clat, clon, zoom=z, size=1024, meta=True)
	halo = kw.pop("halo_latlon", None)
	scene = place(Scene(**{k: v for k, v in kw.items()}), info, cam, tgt, halo)
	t = time.time()
	svg = OUT / f"vista_{name}.svg"
	n = Vista(dem, info, scene).render(str(svg))
	cairosvg.svg2png(url=str(svg), write_to=str(svg.with_suffix(".png")), output_width=1600, background_color=scene.paper)
	print(f"{name:14s} {n:6d} strokes  {time.time() - t:5.1f}s  {svg.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
	for name in sys.argv[1:] or VISTAS:
		render(name)
