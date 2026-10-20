"""Strata - one pipeline that turns an elevation grid into abstract line art for LineDream.

    elevation grid
      -> FIELD     reshape the terrain itself       (blur, gamma, terrace, domain warp)
      -> PATHS     choose a family of curves        (scan, radial, spiral, rings, contour, flow, hatch)
      -> DISPLACE  let height bend the curves       (lift into 3D, or offset sideways in 2D)
      -> CAMERA    orthographic view                (yaw, pitch; pitch=90 is plan view)
      -> HIDE      ray-march visibility             (hidden-line removal against the terrain)
      -> MODULATE  decide where ink lands           (mask by noise/slope/height, circle clip, jitter)
      -> LineDream Lines

Every random choice flows from Params.seed, so a (terrain, params) pair is a reproducible artwork.
"""
from dataclasses import dataclass, replace

import numpy as np
from scipy import ndimage
from skimage import measure

from LineDream import Canvas, Line


@dataclass
class Params:
	seed: int = 0

	# FIELD
	size: int = 400            # working grid resolution
	blur: float = 1.0          # gaussian sigma, in grid px
	gamma: float = 1.0         # >1 pushes lowlands flat, <1 inflates them
	terrace: int = 0           # quantize height into N steps (0 = off)
	terrace_soft: float = 0.0  # 0 = hard steps, 1 = no terracing
	warp: float = 0.0          # domain-warp amplitude (fraction of the map)
	warp_scale: float = 0.12   # feature size of the warp noise

	# PATHS
	paths: str = "scan"        # scan | radial | spiral | rings | contour | flow | hatch
	count: int = 80            # lines / rays / rings / levels / particles / hatch cells per side
	angle: float = 0.0         # scan + hatch orientation, flow bias (degrees)
	center: tuple = (0.5, 0.5)
	inner: float = 0.0         # radial / spiral / rings start at this radius
	turns: int = 60            # spiral turns
	flow_len: int = 400        # max steps per flow line
	flow_sep: float = 0.006    # min spacing between flow lines (fraction of map)
	flow_noise: float = 0.0    # blend a seeded curl-ish noise into the flow direction

	# DISPLACE
	mode: str = "lift"         # lift (3D height) | offset (2D push along the path normal)
	relief: float = 0.2        # vertical exaggeration (fraction of map width)
	highpass: float = 0.0      # displace by local detail only (H - blur(H, sigma px)); 0 = raw height
	jitter: float = 0.0        # per-line random scaling of relief

	# CAMERA
	yaw: float = 0.0
	pitch: float = 35.0        # degrees above horizon; 90 = straight down
	occlude: bool = True

	# MODULATE
	mask: str = "none"         # none | noise | slope | height | inv_slope
	mask_threshold: float = 0.5
	mask_scale: float = 0.06
	mask_mix: float = 0.0      # blend height into the mask: noise dissolves the lowlands first
	clip: str = "square"       # square | circle
	min_run: int = 3           # drop fragments shorter than this many samples

	# OUTPUT
	canvas: tuple = (1200, 1200)
	margin: float = 0.08
	stroke: str = "#eee"
	background: str = "#111"
	stroke_width: float = 1.0


# ---------------------------------------------------------------- helpers

def _noise(rng, n, scale):
	'''Smooth seeded noise in [-1, 1], tileable.'''
	f = ndimage.gaussian_filter(rng.standard_normal((n, n)), max(scale * n, 0.5), mode="wrap")
	return f / (np.abs(f).max() + 1e-9)


def _sample(F, xy):
	'''Bilinear sample of grid F at unit-square coords xy (k,2), x right, y down.'''
	n = F.shape[0] - 1
	return ndimage.map_coordinates(F, [xy[:, 1] * n, xy[:, 0] * n], order=1, mode="nearest")


def _densify(poly, step):
	seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
	d = np.concatenate([[0], np.cumsum(seg)])
	if d[-1] == 0:
		return poly
	t = np.linspace(0, d[-1], max(int(d[-1] / step), 2))
	return np.column_stack([np.interp(t, d, poly[:, 0]), np.interp(t, d, poly[:, 1])])


def _runs(keep, min_run):
	'''Index ranges of consecutive True values.'''
	k = np.concatenate([[False], keep, [False]]).astype(np.int8)
	edges = np.flatnonzero(np.diff(k))
	return [(a, b) for a, b in zip(edges[::2], edges[1::2]) if b - a >= min_run]


# ---------------------------------------------------------------- FIELD

def prepare_field(dem, p, rng):
	H = np.nan_to_num(dem.astype(np.float64))
	H = ndimage.zoom(H, p.size / H.shape[0], order=1)[:p.size, :p.size]
	if p.blur:
		H = ndimage.gaussian_filter(H, p.blur)
	H = (H - H.min()) / (np.ptp(H) + 1e-9)
	H = H ** p.gamma

	if p.terrace:
		q = np.floor(H * p.terrace) / p.terrace
		H = q + (H - q) * p.terrace_soft

	if p.warp:
		n = p.size
		yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
		wx, wy = _noise(rng, n, p.warp_scale), _noise(rng, n, p.warp_scale)
		H = ndimage.map_coordinates(H, [yy + wy * p.warp * n, xx + wx * p.warp * n], order=1, mode="reflect")
	return H


# ---------------------------------------------------------------- PATHS

def _clip_square(poly):
	inside = np.all((poly >= 0) & (poly <= 1), axis=1)
	return [poly[a:b] for a, b in _runs(inside, 2)]


def paths_scan(H, p, rng, step):
	a = np.radians(p.angle + p.yaw)
	d, nrm = np.array([np.cos(a), np.sin(a)]), np.array([-np.sin(a), np.cos(a)])
	c = np.array(p.center)
	out = []
	for s in np.linspace(-0.72, 0.72, p.count):
		line = _densify(np.array([c + s * nrm - 0.75 * d, c + s * nrm + 0.75 * d]), step)
		out += _clip_square(line)
	return out


def paths_radial(H, p, rng, step):
	c, phase = np.array(p.center), rng.uniform(0, 2 * np.pi)
	return [poly for th in np.linspace(0, 2 * np.pi, p.count, endpoint=False) + phase
			for poly in _clip_square(_densify(np.array([c + p.inner * np.array([np.cos(th), np.sin(th)]), c + 0.75 * np.array([np.cos(th), np.sin(th)])]), step))]


def paths_spiral(H, p, rng, step):
	R, th_max = 0.72, p.turns * 2 * np.pi
	length = 0.5 * R * th_max
	th = np.sqrt(np.linspace(0, 1, int(length / step))) * th_max + rng.uniform(0, 2 * np.pi)
	r = p.inner + (R - p.inner) * (th - th.min()) / th_max
	return _clip_square(np.array(p.center) + np.column_stack([r * np.cos(th), r * np.sin(th)]))


def paths_rings(H, p, rng, step):
	c, out = np.array(p.center), []
	for r in np.linspace(max(p.inner, 0.72 / p.count), 0.72, p.count):
		th = np.linspace(0, 2 * np.pi, max(int(2 * np.pi * r / step), 8))
		out += _clip_square(c + r * np.column_stack([np.cos(th), np.sin(th)]))
	return out


def paths_contour(H, p, rng, step):
	n, out = H.shape[0] - 1, []
	for lvl in np.linspace(0, 1, p.count + 2)[1:-1]:
		for cnt in measure.find_contours(H, lvl):
			out.append(_densify(cnt[:, ::-1] / n, step))
	return out


def paths_flow(H, p, rng, step):
	'''Seeded streamlines over the slope field, kept apart with an occupancy grid.'''
	n = H.shape[0]
	gy, gx = np.gradient(ndimage.gaussian_filter(H, 2))
	a = np.radians(p.angle)
	# rotate the downhill vector by `angle`: 0 = rivers, 90 = follow contours
	vx, vy = -gx * np.cos(a) + gy * np.sin(a), -gx * np.sin(a) - gy * np.cos(a)
	mag = np.hypot(vx, vy) + 1e-12
	vx, vy = vx / mag, vy / mag
	if p.flow_noise:
		t = _noise(rng, n, 0.08) * np.pi
		vx, vy = vx + p.flow_noise * np.cos(t), vy + p.flow_noise * np.sin(t)
		mag = np.hypot(vx, vy) + 1e-12
		vx, vy = vx / mag, vy / mag

	cells = max(int(1 / p.flow_sep), 8)
	owner = -np.ones((cells, cells), dtype=np.int64)
	h = 0.5 / n
	out = []
	for i, (x, y) in enumerate(rng.uniform(0.01, 0.99, (p.count, 2))):
		cx, cy = int(x * cells), int(y * cells)
		if owner[cy, cx] != -1:
			continue
		owner[cy, cx] = i
		pts = [(x, y)]
		for _ in range(p.flow_len):
			gi, gj = min(int(y * n), n - 1), min(int(x * n), n - 1)
			x, y = x + vx[gi, gj] * h * 2, y + vy[gi, gj] * h * 2
			if not (0 <= x < 1 and 0 <= y < 1):
				break
			ncx, ncy = int(x * cells), int(y * cells)
			if (ncx, ncy) != (cx, cy):
				# stop on other lines, and on our own trail (we're circling in a pit)
				if owner[ncy, ncx] != -1:
					break
				cx, cy = ncx, ncy
				owner[cy, cx] = i
			pts.append((x, y))
		if len(pts) > 4:
			out.append(np.array(pts))
	return out


def paths_hatch(H, p, rng, step):
	'''Short strokes along the contour direction, length by slope - an engraving look.'''
	n = H.shape[0]
	gy, gx = np.gradient(ndimage.gaussian_filter(H, 1.5))
	slope = np.hypot(gx, gy)
	slope /= np.percentile(slope, 99) + 1e-12
	a = np.radians(p.angle)
	out = []
	cell = 1.0 / p.count
	for (x, y) in (np.stack(np.meshgrid(np.arange(p.count), np.arange(p.count)), -1).reshape(-1, 2) + rng.uniform(0, 1, (p.count ** 2, 2))) * cell:
		gi, gj = min(int(y * n), n - 1), min(int(x * n), n - 1)
		s = min(slope[gi, gj], 1.0)
		if s < 0.05:
			continue
		dx, dy = -gy[gi, gj], gx[gi, gj]
		m = np.hypot(dx, dy) + 1e-12
		dx, dy = dx / m, dy / m
		dx, dy = dx * np.cos(a) - dy * np.sin(a), dx * np.sin(a) + dy * np.cos(a)
		L = cell * (0.3 + 1.6 * s)
		out += _clip_square(_densify(np.array([[x - dx * L, y - dy * L], [x + dx * L, y + dy * L]]), step))
	return out


PATHS = dict(scan=paths_scan, radial=paths_radial, spiral=paths_spiral, rings=paths_rings,
			 contour=paths_contour, flow=paths_flow, hatch=paths_hatch)


# ---------------------------------------------------------------- DISPLACE + CAMERA + HIDE

def _camera(p):
	yaw, pit = np.radians(p.yaw), np.radians(p.pitch)
	R = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
	# direction toward the camera, world space
	to_cam = R.T @ np.array([0, -np.cos(pit), np.sin(pit)])
	return R, pit, to_cam


def _visible(H, P, p, to_cam):
	'''March from each surface point toward the camera; hidden if terrain rises above the ray.'''
	if not p.occlude or p.pitch >= 89:
		return np.ones(len(P), dtype=bool)
	n = H.shape[0]
	horiz = np.hypot(to_cam[0], to_cam[1])
	dt = 1.5 / n / horiz
	t_max = min(1.5 / horiz, p.relief * 1.05 / max(to_cam[2], 1e-3))
	ts = np.arange(2 * dt, t_max, dt)
	vis = np.ones(len(P), dtype=bool)
	Hr = H * p.relief
	for c0 in range(0, len(P), 20000):
		Q = P[c0:c0 + 20000]
		alive = np.ones(len(Q), dtype=bool)
		for t in ts:
			idx = np.flatnonzero(alive)
			if not len(idx):
				break
			R = Q[idx] + t * to_cam
			# world (X right, Y north) back to unit grid coords (x right, y down)
			gx, gy = R[:, 0] + 0.5, 0.5 - R[:, 1]
			inside = (gx >= 0) & (gx <= 1) & (gy >= 0) & (gy <= 1)
			ground = ndimage.map_coordinates(Hr, [gy * (n - 1), gx * (n - 1)], order=1, mode="nearest")
			blocked = inside & (ground > R[:, 2] + 0.25 / n)
			alive[idx[blocked]] = False
			alive[idx[~inside]] = False  # left the map: clear sky
			vis[c0 + idx[blocked]] = False
	return vis


def _mask_field(H, p, rng):
	if p.mask == "none":
		return None
	if p.mask == "noise":
		return (1 - p.mask_mix) * (_noise(rng, H.shape[0], p.mask_scale) + 1) / 2 + p.mask_mix * H
	gy, gx = np.gradient(H)
	slope = np.hypot(gx, gy)
	slope = np.clip(slope / (np.percentile(slope, 98) + 1e-12), 0, 1)
	return {"slope": slope, "inv_slope": 1 - slope, "height": H}[p.mask]


def _normals(poly):
	d = np.gradient(poly, axis=0)
	d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
	return np.column_stack([-d[:, 1], d[:, 0]])


def build(dem, p):
	'''Run the whole pipeline. Returns a list of screen-space polylines (x right, y up).'''
	rng = np.random.default_rng(p.seed)
	H = prepare_field(dem, p, rng)
	step = 1.0 / p.size
	polys = PATHS[p.paths](H, p, rng, step)
	M = _mask_field(H, p, rng)
	D = H - ndimage.gaussian_filter(H, p.highpass) if p.highpass else H
	R, pit, to_cam = _camera(p)

	out = []
	for poly in polys:
		if len(poly) < 2:
			continue
		h = _sample(D, poly)
		relief = p.relief * (1 + p.jitter * rng.standard_normal())
		keep = np.ones(len(poly), dtype=bool)
		if M is not None:
			keep &= _sample(M, poly) > p.mask_threshold
		if p.clip == "circle":
			keep &= np.hypot(*(poly - np.array(p.center)).T) <= 0.5

		if p.mode == "offset":
			flat = poly + _normals(poly) * (h * relief)[:, None]
			scr = np.column_stack([flat[:, 0], -flat[:, 1]])
		else:
			P = np.column_stack([poly[:, 0] - 0.5, 0.5 - poly[:, 1], h * relief])
			keep &= _visible(D, P, p, to_cam) if keep.any() else keep
			V = P @ R.T
			scr = np.column_stack([V[:, 0], V[:, 1] * np.sin(pit) + V[:, 2] * np.cos(pit)])

		out += [scr[a:b] for a, b in _runs(keep, p.min_run)]
	return out


# ---------------------------------------------------------------- RENDER

def render(dem, p, filename):
	polys = build(dem, p)
	W, Hc = p.canvas
	allp = np.concatenate(polys)
	lo, hi = allp.min(0), allp.max(0)
	s = min(W * (1 - 2 * p.margin) / (hi[0] - lo[0]), Hc * (1 - 2 * p.margin) / (hi[1] - lo[1]))
	off = np.array([W, Hc]) / 2 - s * (lo + hi) / 2 * np.array([1, -1])

	Canvas.flush()
	Canvas.width, Canvas.height = W, Hc
	Canvas.background_color = p.background
	for poly in polys:
		xy = poly * np.array([s, -s]) + off
		xy = measure.approximate_polygon(xy, tolerance=0.25)
		if len(xy) < 2:
			continue
		Line.from_array(xy, stroke_color=p.stroke, stroke_width=p.stroke_width)
	Canvas.save(filename)
	return len(polys)


def variant(p, **kw):
	return replace(p, **kw)
