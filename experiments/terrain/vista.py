"""Vista - a perspective, painterly terrain renderer for LineDream.

Where strata.py is a far-away parametric diagram, vista stands you *in* the landscape:

    CAMERA      a pinhole camera at a real place and eye height, aimed at a real place
    LIGHT       a low sun; lambert shading + cast shadows (ray-marched over the DEM)
    HATCH       arcs of constant distance from the eye, perspective-spaced, thinned by
                light: lit slopes go blank, shadowed slopes go dense (tonal hatching)
    LINEWORK    silhouettes (where the surface turns away from the eye), plus a few
                deliberately chosen contours instead of a full topo stack
    ATMOSPHERE  haze fades ink with distance; a mist plane floods everything below a level
    ABSTRACT    sun disc of lines, broken sky streaks, a floating ring - all occluded by
                the real skyline / terrain so they sit *in* the scene

Everything shares one visibility test (march from a 3D point toward the eye), so any
3D curve - on the ground, on the mist, floating in the air - is hidden correctly.
"""
from dataclasses import dataclass, replace

import numpy as np
from scipy import ndimage
from skimage import measure

from LineDream import Canvas, Group, Line


@dataclass
class Scene:
	seed: int = 0
	size: int = 1024             # working grid resolution
	exaggeration: float = 1.3
	smooth: float = 0.7          # DEM blur (px)

	# CAMERA - unit map coords (u right, v down); use place() to set from lat/lon
	cam: tuple = (0.5, 0.95)
	eye: float = 30.0            # meters above ground
	target: tuple = (0.5, 0.4)
	target_eye: float = 0.0      # meters above ground at the aim point
	fov: float = 55.0            # horizontal field of view, degrees
	shift: float = 0.0           # vertical lens shift; + pushes the scene up the frame

	# LIGHT
	sun_az: float = 120.0        # compass degrees (0 = N, 90 = E)
	sun_alt: float = 14.0
	shadows: bool = True

	# HATCH (tone)
	tone: str = "screen"         # screen (etching) | flow (strokes follow the form) | rings (cross-sections) | both | none
	flow_dir: float = 0.0        # flow hatch direction on the surface: 0 = along contours, 90 = down the fall line
	flow_sep: float = 2.6        # canvas px between flow lines in the darkest tone ...
	flow_sep_max: float = 14.0   # ... and in the lightest tone that still gets lines
	flow_min_tone: float = 0.3   # lighter than this stays blank paper
	flow_min_len: int = 6        # drop streamlines shorter than this (steps)
	hatch_angle: float = 0.0     # screen hatch direction, degrees
	hatch_spacing: float = 3.0   # canvas px between screen hatch lines
	cross: float = 0.0           # darkness above which a second, crossing hatch appears (0 = never)
	cross_angle: float = 55.0
	gres: int = 900              # g-buffer width (rays)
	rings: int = 320
	ring_near: float = 0.01      # map units from the eye
	ring_far: float = 1.3
	tiers: int = 4               # tone levels; a ring of tier k draws where darkness > (k+.5)/tiers
	shade_gamma: float = 1.0
	shade_floor: float = 0.0     # darkness added everywhere (0 = lit slopes go blank)
	keyline_every: int = 0       # always draw every Nth ring, regardless of light
	tone_scale: float = 1.0      # <1 keeps the darkest areas from going solid
	window: tuple = None         # ("circle", x, y, r) | ("rect", x0, y0, x1, y1): tone only inside, outline elsewhere
	window_border: bool = True
	invert: bool = False         # hatch the light instead of the dark (light ink on dark paper)

	# LINEWORK
	silhouettes: bool = True
	lost_edges: float = 0.0      # drop silhouette where the rock is lit (darkness below this): lost & found edges
	overshoot: float = 0.0       # extend silhouette ends by this many px, like a quick pen stroke
	wobble: float = 0.0          # hand tremor amplitude (px), seeded per stroke
	sil_min: int = 10
	contours: tuple = ()         # ((elevation_m, "ink" | "accent"), ...)
	contour_every: float = 0.0   # regular contours, meters (0 = off) ...
	contour_above: float = -1e9  # ... only inside this elevation band
	contour_below: float = 1e9

	# ATMOSPHERE
	haze: float = 0.6
	haze_near: float = 0.1
	haze_far: float = 1.0
	mist: float = None           # elevation (m); terrain below becomes white sea
	mist_lines: int = 0

	# ABSTRACT
	sun_disc: float = 0.0        # radius, fraction of half frame width (0 = off)
	sun_pos: tuple = None        # override disc screen position (x, y in frame units)
	sun_lines: int = 15
	sky_lines: int = 0
	halo: tuple = None           # (u, v, elevation_m, radius_m) vertical ring facing the eye

	# OUTPUT
	canvas: tuple = (1600, 1000)
	margin: float = 0.05
	paper: str = "#f1ece2"
	ink: str = "#1c1b19"
	accent: str = "#cf4a1f"
	stroke_width: float = 0.8
	frame: bool = True
	plotter: bool = False        # two pens only (ink + accent), uniform width; haze becomes dashes, not grey


def place(scene, info, cam_latlon, target_latlon, halo_latlon=None, **kw):
	'''Set camera/target (and optional halo center) from lat/lon using a DemInfo.'''
	kw["cam"] = info.to_uv(*cam_latlon)
	kw["target"] = info.to_uv(*target_latlon)
	if halo_latlon:
		kw["halo"] = (*info.to_uv(*halo_latlon[:2]), *halo_latlon[2:])
	return replace(scene, **kw)


def _hex(c):
	c = c.lstrip("#")
	return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)


def _mix(a, b, t):
	return "#%02x%02x%02x" % tuple(np.round(_hex(a) * (1 - t) + _hex(b) * t).astype(int))


def _runs(key):
	'''(start, end, value) for runs of equal non-negative values in an int array.'''
	out, n = [], len(key)
	if not n:
		return out
	cuts = np.flatnonzero(np.diff(key)) + 1
	for a, b in zip(np.concatenate([[0], cuts]), np.concatenate([cuts, [n]])):
		if key[a] >= 0 and b - a >= 2:
			out.append((a, b, key[a]))
	return out


class Vista:
	def __init__(self, dem, info, s: Scene):
		self.s = s
		self.rng = np.random.default_rng(s.seed)
		n = self.n = s.size
		E = ndimage.zoom(np.nan_to_num(dem.astype(np.float64)), n / dem.shape[0], order=1)[:n, :n]
		self.E = ndimage.gaussian_filter(E, s.smooth) if s.smooth else E
		self.k = s.exaggeration / info.width_m       # meters -> world units (map width = 1)
		self.Z = self.E * self.k
		self.zmax = self.Z.max()
		self.px = 1.0 / (n - 1)

		gv, gu = np.gradient(ndimage.gaussian_filter(self.Z, 1.2), self.px)
		self.dzdx, self.dzdy = gu, -gv                # world y points north = -v
		self.slope = np.percentile(np.hypot(gu, gv), 99.9)
		self._camera()
		self._shade()

	# ------------------------------------------------------------ geometry

	def ground(self, x, y, F=None):
		F = self.Z if F is None else F
		return ndimage.map_coordinates(F, [(1 - y) / self.px, x / self.px], order=1, mode="nearest")

	def _world(self, u, v, F=None):
		u, v = np.asarray(u, float), np.asarray(v, float)
		return np.column_stack([u, 1 - v, self.ground(u, 1 - v, F)])

	def _camera(self):
		s = self.s
		C = self._world([s.cam[0]], [s.cam[1]])[0]
		C[2] += s.eye * self.k
		T = self._world([s.target[0]], [s.target[1]])[0]
		T[2] += s.target_eye * self.k
		f = (T - C) / np.linalg.norm(T - C)
		r = np.cross(f, [0, 0, 1.0])
		r /= np.linalg.norm(r)
		self.C, self.f, self.r, self.up = C, f, r, np.cross(r, f)
		self.focal = 1 / np.tan(np.radians(s.fov) / 2)
		W, H = s.canvas
		m = s.margin * W
		self.aspect = (H - 2 * m) / (W - 2 * m)

	def project(self, P):
		d = P - self.C
		zc = d @ self.f
		zs = np.where(zc > 1e-6, zc, 1e-6)
		return np.column_stack([(d @ self.r) / zs * self.focal, (d @ self.up) / zs * self.focal + self.s.shift]), zc

	def in_frame(self, S, zc):
		return (zc > 1e-4) & (np.abs(S[:, 0]) <= 1) & (np.abs(S[:, 1]) <= self.aspect)

	def in_window(self, S):
		w = self.s.window
		if not w:
			return np.ones(len(S), dtype=bool)
		if w[0] == "circle":
			return np.hypot(S[:, 0] - w[1], S[:, 1] - w[2]) <= w[3]
		return (S[:, 0] >= w[1]) & (S[:, 0] <= w[3]) & (S[:, 1] >= w[2]) & (S[:, 1] <= w[4])

	def visible(self, P):
		'''Sphere-trace each point toward the eye; False where terrain blocks the ray.'''
		D = self.C - P
		dist = np.linalg.norm(D, axis=1)
		Dn = D / dist[:, None]
		hf = np.hypot(Dn[:, 0], Dn[:, 1]) + 1e-9
		t = 2 * self.px / hf
		vis = np.ones(len(P), dtype=bool)
		alive = np.ones(len(P), dtype=bool)
		bias = 0.35 * self.px
		for _ in range(4 * self.n):
			idx = np.flatnonzero(alive)
			if not len(idx):
				break
			R = P[idx] + Dn[idx] * t[idx, None]
			gap = R[:, 2] - self.ground(R[:, 0], R[:, 1])
			out = (R[:, 0] < 0) | (R[:, 0] > 1) | (R[:, 1] < 0) | (R[:, 1] > 1)
			done = (t[idx] >= dist[idx]) | (R[:, 2] > self.zmax) | out
			blocked = (gap < -bias) & ~done
			vis[idx[blocked]] = False
			alive[idx[done | blocked]] = False
			t[idx] += np.maximum(self.px, 0.8 * np.maximum(gap, 0) / self.slope) / hf[idx]
		return vis

	# ------------------------------------------------------------ light

	def _shade(self):
		s = self.s
		az, alt = np.radians(s.sun_az), np.radians(s.sun_alt)
		self.sun = np.array([np.sin(az) * np.cos(alt), np.cos(az) * np.cos(alt), np.sin(alt)])
		N = np.dstack([-self.dzdx, -self.dzdy, np.ones_like(self.Z)])
		N /= np.linalg.norm(N, axis=2, keepdims=True)
		light = np.clip(N @ self.sun, 0, None)

		if s.shadows:
			light *= 1 - self._cast_shadow()
		ref = np.percentile(light, 95) + 1e-9
		dark = 1 - np.clip(light / ref, 0, 1)
		if s.invert:
			dark = 1 - dark
		self.dark = (s.shade_floor + (1 - s.shade_floor) * dark ** s.shade_gamma) * s.tone_scale
		self.N = N

	def _cast_shadow(self):
		m = min(self.n, 320)
		Zc = ndimage.zoom(self.Z, m / self.n, order=1)
		px = 1.0 / (m - 1)
		vv, uu = np.mgrid[0:m, 0:m] * px
		x, y, z0 = uu.ravel(), 1 - vv.ravel(), Zc.ravel()
		hs = np.hypot(self.sun[0], self.sun[1])
		dx, dy, rise = self.sun[0] / hs, self.sun[1] / hs, self.sun[2] / hs
		shadow = np.zeros(len(x))
		alive = np.ones(len(x), dtype=bool)
		t = 1.5 * px
		while alive.any():
			idx = np.flatnonzero(alive)
			X, Y, Rz = x[idx] + dx * t, y[idx] + dy * t, z0[idx] + rise * t
			out = (X < 0) | (X > 1) | (Y < 0) | (Y > 1) | (Rz > self.zmax)
			g = ndimage.map_coordinates(Zc, [(1 - Y) / px, X / px], order=1, mode="nearest")
			blocked = (g > Rz + 0.3 * px) & ~out
			shadow[idx[blocked]] = 1
			alive[idx[out | blocked]] = False
			t += px
		sh = ndimage.zoom(shadow.reshape(m, m), self.n / m, order=1)[:self.n, :self.n]
		return np.clip(ndimage.gaussian_filter(sh, 1.5), 0, 1)

	# ------------------------------------------------------------ stroke collection

	def fade(self, P):
		d = np.linalg.norm(P[:, :2] - self.C[:2], axis=1)
		f = np.clip((d - self.s.haze_near) / (self.s.haze_far - self.s.haze_near), 0, 1)
		return self.s.haze * f * f * (3 - 2 * f)

	def emit(self, P, keep, role, check_vis=True):
		'''Project 3D points, hide what the terrain covers, split into runs by role + haze depth.'''
		S, zc = self.project(P)
		keep = keep & self.in_frame(S, zc)
		if role in ("hatch", "mist"):
			keep &= self.in_window(S)
		if check_vis and keep.any():
			sub = np.flatnonzero(keep)
			keep[sub[~self.visible(P[sub])]] = False
		depth = np.minimum((self.fade(P) * 4).astype(int), 3)
		key = np.where(keep, depth, -1)
		for a, b, d in _runs(key):
			self.strokes.append((role, int(d), S[a:b]))

	# ------------------------------------------------------------ layers

	def hatch(self):
		s = self.s
		yaw = np.arctan2(self.f[1], self.f[0])
		half = np.radians(s.fov) / 2 * 1.1
		dth = np.radians(s.fov) / s.canvas[0] * 1.5
		th = np.arange(yaw - half, yaw + half, dth)
		order = [int(format(i, f"0{max(s.tiers - 1, 1).bit_length()}b")[::-1], 2) for i in range(2 ** max(s.tiers - 1, 1).bit_length())]
		order = [o for o in order if o < s.tiers]
		phase = self.rng.integers(s.tiers)
		for i, r in enumerate(np.geomspace(s.ring_near, s.ring_far, s.rings)):
			r *= 1 + self.rng.uniform(-0.25, 0.25) / s.rings
			u, y = self.C[0] + r * np.cos(th), self.C[1] + r * np.sin(th)
			ok = (u >= 0) & (u <= 1) & (y >= 0) & (y <= 1)
			if not ok.any():
				continue
			P = self._world(u[ok], 1 - y[ok])
			thr = (order[(i + phase) % s.tiers] + 0.5) / s.tiers
			dark = self.ground(P[:, 0], P[:, 1], self.dark) * (1 - self.fade(P))
			keep = dark > thr
			if s.keyline_every and i % s.keyline_every == 0:
				keep[:] = True
			if s.mist is not None:
				keep &= self.ground(P[:, 0], P[:, 1], self.E) > s.mist
			self.emit(P, keep, "hatch")

	def gbuffer(self):
		'''Cast one ray per buffer pixel: what the eye sees there (tone, haze, mist, sky).'''
		s = self.s
		gw = s.gres
		gh = int(gw * self.aspect)
		SX, SY = np.meshgrid(np.linspace(-1, 1, gw), np.linspace(self.aspect, -self.aspect, gh))
		D = (self.f[None] + np.outer(SX.ravel() / self.focal, self.r) + np.outer((SY.ravel() - s.shift) / self.focal, self.up))
		D /= np.linalg.norm(D, axis=1, keepdims=True)
		hf = np.hypot(D[:, 0], D[:, 1]) + 1e-9
		zm = -np.inf if s.mist is None else s.mist * self.k
		hit = np.zeros(len(D), dtype=np.int8)   # 0 sky, 1 terrain, 2 mist
		t = np.full(len(D), 2 * self.px)
		alive = np.ones(len(D), dtype=bool)
		for _ in range(4 * self.n):
			idx = np.flatnonzero(alive)
			if not len(idx):
				break
			R = self.C + D[idx] * t[idx, None]
			gap = R[:, 2] - self.ground(R[:, 0], R[:, 1])
			out = (R[:, 0] < 0) | (R[:, 0] > 1) | (R[:, 1] < 0) | (R[:, 1] > 1) | ((R[:, 2] > self.zmax) & (D[idx, 2] >= 0))
			on_mist = (R[:, 2] < zm) & (gap > 0) & ~out
			on_ground = (gap <= 0) & ~out
			hit[idx[on_ground]] = 1
			hit[idx[on_mist]] = 2
			alive[idx[out | on_ground | on_mist]] = False
			t[idx] += np.maximum(0.7 * self.px, 0.8 * np.maximum(gap, 0) / self.slope) / hf[idx]
		P = self.C + D * t[:, None]
		tone = np.where(hit == 1, self.ground(P[:, 0], P[:, 1], self.dark) * (1 - self.fade(P)), -1.0)
		self.g_tone = ndimage.gaussian_filter(tone.reshape(gh, gw), 0.7)
		self.g_tone[hit.reshape(gh, gw) != 1] = -1
		self.g_depth = np.minimum((self.fade(P) * 4).astype(int), 3).reshape(gh, gw)
		self.g_hit = hit.reshape(gh, gw)
		self.g_P = P.reshape(gh, gw, 3)

	def flow_field(self, angle):
		"""Screen-space angle field of a surface direction (smoothed sign-free, via doubled angles)."""
		gh, gw = self.g_hit.shape
		P = self.g_P.reshape(-1, 3)
		gx, gy = self.ground(P[:, 0], P[:, 1], self.dzdx), self.ground(P[:, 0], P[:, 1], self.dzdy)
		T = np.column_stack([-gy, gx, np.zeros_like(gx)])                  # along contour
		Fd = np.column_stack([-gx, -gy, -(gx * gx + gy * gy)])              # down the fall line
		T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
		Fd /= np.linalg.norm(Fd, axis=1, keepdims=True) + 1e-12
		a = np.radians(angle)
		Dw = np.cos(a) * T + np.sin(a) * Fd
		S0, _ = self.project(P)
		S1, _ = self.project(P + 0.5 * self.px * Dw)
		v = S1 - S0
		th = np.arctan2(v[:, 1], v[:, 0]).reshape(gh, gw)
		m = self.g_hit == 1
		c = ndimage.gaussian_filter(np.where(m, np.cos(2 * th), 0), 1.5)
		sn = ndimage.gaussian_filter(np.where(m, np.sin(2 * th), 0), 1.5)
		return 0.5 * np.arctan2(sn, c)

	def flow_hatch(self, angle, gate=0.0):
		"""Evenly spaced streamlines along a surface direction (Jobard-Lefer style seeding);
		spacing tightens with darkness, so the strokes carry both form and tone."""
		from collections import deque
		s = self.s
		gh, gw = self.g_hit.shape
		TH = self.flow_field(angle)
		P = self.g_P.reshape(-1, 3)
		grad = np.hypot(self.ground(P[:, 0], P[:, 1], self.dzdx), self.ground(P[:, 0], P[:, 1], self.dzdy)).reshape(gh, gw)
		flat = grad < np.percentile(grad[self.g_hit == 1], 8)
		tone = ndimage.gaussian_filter(np.where(self.g_hit == 1, np.maximum(self.g_tone, 0), 0), 1.8)
		tone[self.g_hit != 1] = -1
		half = (s.canvas[0] * (1 - 2 * s.margin)) / 2
		smin, smax = s.flow_sep / half, s.flow_sep_max / half
		h = 1.2 * 2 / gw
		cell = smin / 2.5
		ow, oh = int(2 / cell) + 1, int(2 * self.aspect / cell) + 1
		occ = -np.ones((oh, ow), dtype=np.int32)
		disks = {}
		lo = max(s.flow_min_tone, gate)

		def sep(t):
			return smin + (smax - smin) * (1 - (t - lo) / (1 - lo + 1e-9)) ** 2

		def crowded(p, d, lid):
			cx, cy = int((p[0] + 1) / cell), int((self.aspect - p[1]) / cell)
			k = max(int(d / cell + 0.5), 1)
			if k not in disks:
				yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
				msk = xx * xx + yy * yy <= k * k
				disks[k] = (yy[msk], xx[msk])
			dy, dx = disks[k]
			v = occ[np.clip(cy + dy, 0, oh - 1), np.clip(cx + dx, 0, ow - 1)]
			return bool(np.any((v >= 0) & (v != lid)))

		def mark(p, lid):
			occ[min(int((self.aspect - p[1]) / cell), oh - 1), min(int((p[0] + 1) / cell), ow - 1)] = lid

		def valid(p, floor=1.0):
			if abs(p[0]) > 1 or abs(p[1]) > self.aspect:
				return None
			r = int((self.aspect - p[1]) / (2 * self.aspect) * (gh - 1) + 0.5)
			c = int((p[0] + 1) / 2 * (gw - 1) + 0.5)
			if self.g_hit[r, c] != 1 or flat[r, c] or tone[r, c] < lo * floor or not self.in_window(p[None])[0]:
				return None
			return r, c

		def trace(seed, lid):
			line = [seed]
			for sign in (1, -1):
				p, prev, pts = seed, None, []
				for _ in range(3000):
					rc = valid(p, 0.7)
					if rc is None:
						break
					v = np.array([np.cos(TH[rc]), np.sin(TH[rc])])
					if prev is None:
						v = v * sign
					else:
						if v @ prev < 0:
							v = -v
						if v @ prev < 0.87:  # turning > 30 deg in one step: a vortex, stop
							break
					q = p + h * v
					rq = valid(q, 0.7)
					if rq is None or crowded(q, 0.55 * sep(max(tone[rq], lo)), lid):
						break
					pts.append(q)
					p, prev = q, v
				line = (pts[::-1] + line) if sign == -1 else (line + pts)
			return np.array(line)

		order = np.flatnonzero((self.g_hit.ravel() == 1) & (tone.ravel() >= lo))
		self.rng.shuffle(order)
		randoms = iter(order)
		queue = deque()
		lid = 0
		while True:
			if queue:
				seed = queue.popleft()
			else:
				nxt = next(randoms, None)
				if nxt is None:
					break
				r, c = divmod(int(nxt), gw)
				seed = np.array([c / (gw - 1) * 2 - 1, self.aspect - r / (gh - 1) * 2 * self.aspect])
			rc = valid(seed)
			if rc is None or crowded(seed, sep(tone[rc]), -2):
				continue
			line = trace(seed, lid)
			if len(line) < s.flow_min_len:
				continue
			for p in line:
				mark(p, lid)
			# seeds one spacing to either side, so neighbours grow parallel
			for i in range(0, len(line) - 1, 3):
				d = line[min(i + 1, len(line) - 1)] - line[max(i - 1, 0)]
				nrm = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-12)
				rc = valid(line[i])
				if rc is not None:
					dd = sep(tone[rc])
					queue.append(line[i] + nrm * dd)
					queue.append(line[i] - nrm * dd)
			depth = self._gsample(self.g_depth, line).astype(int)
			for a0, b0, dep in _runs(depth):
				self.strokes.append(("hatch", int(dep), line[a0:b0]))
			lid += 1

	def _gsample(self, F, S, order=0):
		gh, gw = F.shape
		col = (S[:, 0] + 1) / 2 * (gw - 1)
		row = (self.aspect - S[:, 1]) / (2 * self.aspect) * (gh - 1)
		return ndimage.map_coordinates(F, [row, col], order=order, mode="nearest")

	def screen_hatch(self, angle, gate=None):
		'''Straight etching lines at even screen spacing; tier thresholds turn tone into density.'''
		s = self.s
		half = (s.canvas[0] * (1 - 2 * s.margin)) / 2
		sp = s.hatch_spacing / half
		a = np.radians(angle)
		d, nrm = np.array([np.cos(a), np.sin(a)]), np.array([-np.sin(a), np.cos(a)])
		L = np.hypot(1, self.aspect)
		order = [0, 2, 1, 3][:s.tiers] if s.tiers <= 4 else list(range(s.tiers))
		phase = self.rng.integers(s.tiers)
		ts = np.arange(-L, L, 1.0 / s.gres)
		for i, o in enumerate(np.arange(-L, L, sp)):
			S = o * nrm + np.outer(ts, d)
			inside = (np.abs(S[:, 0]) <= 1) & (np.abs(S[:, 1]) <= self.aspect)
			if not inside.any():
				continue
			S = S[inside]
			tone = self._gsample(self.g_tone, S, order=1)
			thr = (order[(i + phase) % s.tiers] + 0.5) / s.tiers
			keep = (tone > (thr if gate is None else max(gate, thr))) & self.in_window(S)
			key = np.where(keep, self._gsample(self.g_depth, S), -1)
			for a0, b0, dep in _runs(key):
				if b0 - a0 >= 3:
					self.strokes.append(("hatch", int(dep), S[a0:b0]))

	def silhouettes(self):
		s = self.s
		vv, uu = np.mgrid[0:self.n, 0:self.n] * self.px
		V = np.dstack([self.C[0] - uu, self.C[1] - (1 - vv), self.C[2] - self.Z])
		F = np.sum(self.N * V, axis=2) / np.linalg.norm(V, axis=2)
		for cnt in measure.find_contours(ndimage.gaussian_filter(F, 1.0), 0):
			if len(cnt) < s.sil_min:
				continue
			P = self._world(cnt[:, 1] * self.px, cnt[:, 0] * self.px)
			keep = np.ones(len(P), dtype=bool)
			if s.mist is not None:
				keep &= self.ground(P[:, 0], P[:, 1], self.E) > s.mist
			if s.lost_edges:
				dk = ndimage.uniform_filter1d(self.ground(P[:, 0], P[:, 1], self.dark), 7)
				keep &= dk >= s.lost_edges
			self.emit(P, keep, "sil")

	def contours(self):
		s = self.s
		levels = list(s.contours)
		if s.contour_every:
			lo = max(self.E.min(), s.contour_above)
			hi = min(self.E.max(), s.contour_below)
			levels += [(e, "ink") for e in np.arange(np.ceil(lo / s.contour_every) * s.contour_every, hi, s.contour_every)]
		if s.mist is not None:
			levels = [lv for lv in levels if lv[0] > s.mist] + [(s.mist, "contour")]
		for elev, style in levels:
			for cnt in measure.find_contours(self.E, elev):
				P = self._world(cnt[:, 1] * self.px, cnt[:, 0] * self.px)
				self.emit(P, np.ones(len(P), dtype=bool), "accent" if style == "accent" else "contour")

	def mist_surface(self):
		s = self.s
		if s.mist is None or not s.mist_lines:
			return
		yaw = np.arctan2(self.f[1], self.f[0])
		half = np.radians(s.fov) / 2 * 1.1
		th = np.arange(yaw - half, yaw + half, np.radians(s.fov) / s.canvas[0] * 1.5)
		zm = s.mist * self.k
		for r in 1 / np.linspace(1 / max(s.ring_near, 0.03), 1 / s.ring_far, s.mist_lines):
			u, y = self.C[0] + r * np.cos(th), self.C[1] + r * np.sin(th)
			ok = (u >= 0) & (u <= 1) & (y >= 0) & (y <= 1)
			if not ok.any():
				continue
			P = np.column_stack([u[ok], y[ok], np.full(ok.sum(), zm)])
			keep = self.ground(P[:, 0], P[:, 1]) < zm
			# broken, breathing lines
			keep &= np.sin(th[ok] * self.rng.uniform(30, 90) + self.rng.uniform(0, 6.3)) > -0.2
			self.emit(P, keep, "mist")

	def skyline(self, cols=800):
		'''Highest screen y of the terrain per screen column.'''
		st = 2
		vv, uu = np.mgrid[0:self.n:st, 0:self.n:st] * self.px
		P = np.column_stack([uu.ravel(), 1 - vv.ravel(), self.Z[::st, ::st].ravel()])
		S, zc = self.project(P)
		ok = (zc > 1e-4) & (np.abs(S[:, 0]) <= 1.05)
		sky = np.full(cols, -np.inf)
		c = np.clip(((S[ok, 0] + 1) / 2 * (cols - 1)).astype(int), 0, cols - 1)
		np.maximum.at(sky, c, S[ok, 1])
		sky = ndimage.maximum_filter1d(sky, 5)
		return lambda x: sky[np.clip(((x + 1) / 2 * (cols - 1)).astype(int), 0, cols - 1)]

	def sky(self):
		s = self.s
		if not (s.sun_disc or s.sky_lines):
			return
		top = self.skyline()
		gap = 0.012
		sun = None
		if s.sun_disc:
			if s.sun_pos is not None:
				sun = np.array(s.sun_pos, float)
			else:
				zc = self.sun @ self.f
				sun = np.array([self.sun @ self.r / zc * self.focal, self.sun @ self.up / zc * self.focal + s.shift]) if zc > 0 else None
		if sun is not None:
			R = s.sun_disc
			for y in np.linspace(sun[1] - R, sun[1] + R, s.sun_lines + 2)[1:-1]:
				w = np.sqrt(max(R * R - (y - sun[1]) ** 2, 0))
				x = np.linspace(sun[0] - w, sun[0] + w, max(int(w * 600), 2))
				self._sky_stroke(x, y, top(x) + gap, "sun")
		for i in range(s.sky_lines):
			y = self.aspect * (1 - 1.6 * (i + 0.5) / s.sky_lines) ** 1.0
			x = np.linspace(-1, 1, 1200)
			ph, fr = self.rng.uniform(0, 100), self.rng.uniform(2, 6)
			keep = (np.sin(x * fr + ph) + 0.6 * np.sin(x * fr * 2.7 + ph * 1.3)) > 0.5
			if sun is not None:
				keep &= np.hypot(x - sun[0], y - sun[1]) > s.sun_disc * 1.25
			self._sky_stroke(x, y, top(x) + gap * 3, "sky", keep)

	def _sky_stroke(self, x, y, floor, role, keep=None):
		S = np.column_stack([x, np.full(len(x), y)])
		k = (S[:, 1] > floor) & (np.abs(S[:, 0]) <= 1) & (np.abs(S[:, 1]) <= self.aspect)
		if keep is not None:
			k &= keep
		for a, b, _ in _runs(np.where(k, 0, -1)):
			self.strokes.append((role, 0, S[a:b]))

	def halo(self):
		s = self.s
		if not s.halo:
			return
		u, v, elev, rad = s.halo
		c = np.array([u, 1 - v, elev * self.k])
		toward = self.C[:2] - c[:2]
		toward /= np.linalg.norm(toward)
		a = np.array([-toward[1], toward[0], 0])
		th = np.linspace(0, 2 * np.pi, 1500)
		P = c + rad * self.k / s.exaggeration * (np.outer(np.cos(th), a) + np.outer(np.sin(th), [0, 0, 1]))
		self.emit(P, np.ones(len(P), dtype=bool), "accent")

	# ------------------------------------------------------------ render

	def build(self):
		self.strokes = []
		s = self.s
		if s.tone in ("screen", "both"):
			self.gbuffer()
			self.screen_hatch(s.hatch_angle)
			if s.cross:
				self.screen_hatch(s.hatch_angle + s.cross_angle, gate=s.cross)
		if s.tone == "flow":
			self.gbuffer()
			self.flow_hatch(s.flow_dir)
			if s.cross:
				self.flow_hatch(s.flow_dir + 90, gate=s.cross)
		if s.tone in ("rings", "both"):
			self.hatch()
		if self.s.silhouettes:
			self.silhouettes()
		self.contours()
		self.mist_surface()
		self.sky()
		self.halo()
		self.window_border()
		return self.strokes

	def window_border(self):
		w = self.s.window
		if not (w and self.s.window_border):
			return
		if w[0] == "circle":
			th = np.linspace(0, 2 * np.pi, 1200)
			S = np.column_stack([w[1] + w[3] * np.cos(th), w[2] + w[3] * np.sin(th)])
		else:
			S = np.array([[w[1], w[2]], [w[3], w[2]], [w[3], w[4]], [w[1], w[4]], [w[1], w[2]]])
		self.strokes.append(("accent", 0, S))

	def render(self, filename):
		return self.draw(self.build(), filename)

	def _handmade(self, xy, role):
		s = self.s
		if s.overshoot and role == "sil" and len(xy) > 2:
			a, b = xy[1] - xy[0], xy[-1] - xy[-2]
			a, b = a / (np.hypot(*a) + 1e-9), b / (np.hypot(*b) + 1e-9)
			xy = np.vstack([xy[0] - a * s.overshoot, xy, xy[-1] + b * s.overshoot])
		if s.wobble and len(xy) > 2:
			d = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
			fr, ph = self.rng.uniform(0.01, 0.05, 3), self.rng.uniform(0, 6.3, 3)
			off = sum(np.sin(d * f + p) for f, p in zip(fr, ph)) / 3 * s.wobble
			t = np.gradient(xy, axis=0)
			nrm = np.column_stack([-t[:, 1], t[:, 0]]) / (np.hypot(t[:, 0], t[:, 1])[:, None] + 1e-9)
			xy = xy + nrm * off[:, None]
		return xy

	def _dashes(self, xy, depth):
		# plotter haze: distant lines break into dashes instead of turning grey
		if depth == 0 or len(xy) < 2:
			return [xy]
		d = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
		period, duty = 9.0, 1 - 0.22 * depth
		on = (d % period) < period * duty
		return [xy[a:b] for a, b, _ in _runs(np.where(on, 0, -1))]

	def draw(self, strokes, filename):
		s = self.s
		W, H = s.canvas
		m = s.margin * W
		half = (W - 2 * m) / 2

		styles = {  # role -> (width multiplier, base color)
			"hatch": (1.0, s.ink), "sil": (1.6, s.ink), "contour": (1.1, s.ink),
			"mist": (0.8, _mix(s.ink, s.paper, 0.45)), "sky": (0.9, _mix(s.ink, s.paper, 0.35)),
			"sun": (1.2, s.accent), "accent": (1.6, s.accent),
		}
		Canvas.flush()
		Canvas.width, Canvas.height = W, H
		Canvas.background_color = s.paper
		layers = {}
		for role, depth, S in strokes:
			xy = np.column_stack([W / 2 + S[:, 0] * half, H / 2 - S[:, 1] * half])
			xy = self._handmade(xy, role)
			accent = role in ("sun", "accent")
			if s.plotter:
				col, width = (s.accent if accent else s.ink), s.stroke_width
				parts = self._dashes(xy, depth) if role in ("sil", "contour") else [xy]
				label = "2-accent" if accent else "1-ink"
			else:
				wm, col = styles[role]
				if not accent:
					col = _mix(col, s.paper, depth / 4 * 0.85)
				width = s.stroke_width * wm * (1 - depth * 0.12)
				parts, label = [xy], f"{role}-{depth}"
			for part in parts:
				part = measure.approximate_polygon(part, tolerance=0.3)
				if len(part) < 2:
					continue
				layers.setdefault(label, []).append(Line.from_array(part, stroke_color=col, stroke_width=width))

		if s.frame:
			Line([(m, m), (W - m, m), (W - m, H - m), (m, H - m), (m, m)], stroke_color=s.ink, stroke_width=s.stroke_width)

		# one inkscape layer per label = one pen per layer on a plotter
		for label, lines in sorted(layers.items()):
			Group(label=label).extend(lines)
		Canvas.save(filename)
		return len(strokes)


def compose(dem, info, inside: Scene, outside: Scene, filename):
	"""Two scenes, one camera: inside.window shows scene A, the rest of the frame shows scene B
	(different sun, season, mist, tone style...). The window edge is drawn in accent."""
	win = inside.window
	a = Vista(dem, info, replace(inside, window=None))
	b = Vista(dem, info, replace(outside, window=None))
	sa, sb = a.build(), b.build()
	a.s = replace(inside, window=win)   # in_window() below must see the real window
	out = []
	for strokes, want in ((sa, True), (sb, False)):
		for role, depth, S in strokes:
			if role == "sun":
				if not want:
					out.append((role, depth, S))
				continue
			m = a.in_window(S)
			for i0, i1, _ in _runs(np.where(m == want, 0, -1)):
				out.append((role, depth, S[i0:i1]))
	a.s = replace(inside, window=win)
	a.strokes = out
	a.window_border()
	return a.draw(a.strokes, filename)
