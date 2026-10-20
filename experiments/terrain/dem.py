"""Tiny DEM loader: pulls Terrarium-encoded elevation tiles (AWS open data, no key)
and returns a square float32 elevation grid in meters centered on a lat/lon.

Swap this out for your own GIS loader - strata only needs a 2D numpy array.
"""
import io
import math
import pathlib
import urllib.request

import numpy as np
from PIL import Image

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
CACHE = pathlib.Path(__file__).parent / "cache"


def _global_px(lat, lon, z):
	n = 2 ** z * 256
	x = (lon + 180.0) / 360.0 * n
	lat_r = math.radians(lat)
	y = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n
	return x, y


def _tile(z, x, y):
	CACHE.mkdir(exist_ok=True)
	path = CACHE / f"{z}_{x}_{y}.png"
	if not path.exists():
		with urllib.request.urlopen(TILE_URL.format(z=z, x=x, y=y), timeout=30) as r:
			path.write_bytes(r.read())
	rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
	return rgb[..., 0] * 256.0 + rgb[..., 1] + rgb[..., 2] / 256.0 - 32768.0


def fetch_dem(lat, lon, zoom=11, size=768):
	'''Return a size x size elevation grid (meters) centered on lat/lon.'''
	cx, cy = _global_px(lat, lon, zoom)
	x0, y0 = int(cx - size / 2), int(cy - size / 2)
	tx0, ty0 = x0 // 256, y0 // 256
	tx1, ty1 = (x0 + size) // 256, (y0 + size) // 256

	mosaic = np.zeros(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256), dtype=np.float32)
	for ty in range(ty0, ty1 + 1):
		for tx in range(tx0, tx1 + 1):
			mosaic[(ty - ty0) * 256:(ty - ty0 + 1) * 256, (tx - tx0) * 256:(tx - tx0 + 1) * 256] = _tile(zoom, tx, ty)

	ox, oy = x0 - tx0 * 256, y0 - ty0 * 256
	return mosaic[oy:oy + size, ox:ox + size]
