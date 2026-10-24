"""Numba kernels for vista's hot loops.

The numpy versions spent most of their time on per-step overhead (tiny array allocations, np.clip,
np.any) rather than arithmetic. Each kernel here is the same algorithm written as a plain loop, so
it compiles to straight machine code; the ray kernels also run across cores with prange.

Grid convention matches Vista.ground(): world (x, y) -> row = (1 - y) / px, col = x / px, bilinear,
coordinates clamped to the grid edge (= map_coordinates(order=1, mode="nearest")).
"""
import math
import os

import numpy as np

try:
	if os.environ.get("LINEDREAM_NO_NUMBA") == "1":
		raise ImportError("numba disabled by LINEDREAM_NO_NUMBA=1")
	from numba import njit, prange
	from numba.typed import List
	HAVE_NUMBA = True
except ImportError:
	# Pyodide (the browser) has no numba. The loop kernels below then run as plain Python, and the
	# ray kernels are swapped for vectorized numpy versions at the bottom of this file.
	HAVE_NUMBA = False
	prange, List = range, list

	def njit(*args, **kwargs):
		if args and callable(args[0]):
			return args[0]
		return lambda f: f


@njit(cache=True, fastmath=True, inline="always")
def bilinear(F, row, col):
	h, w = F.shape
	row = min(max(row, 0.0), h - 1.0)
	col = min(max(col, 0.0), w - 1.0)
	r0, c0 = int(row), int(col)
	r1, c1 = min(r0 + 1, h - 1), min(c0 + 1, w - 1)
	fr, fc = row - r0, col - c0
	top = F[r0, c0] * (1 - fc) + F[r0, c1] * fc
	bot = F[r1, c0] * (1 - fc) + F[r1, c1] * fc
	return top * (1 - fr) + bot * fr


# ------------------------------------------------------------------ rays

@njit(cache=True, parallel=True, fastmath=True)
def gbuffer_march(C, D, Z, px, zmax, slope, zmist, maxit):
	'''One ray per row of D from eye C. Returns (t, hit) with hit 0 = sky, 1 = terrain, 2 = mist.'''
	n = D.shape[0]
	t_out = np.empty(n)
	hit_out = np.zeros(n, dtype=np.int8)
	for i in prange(n):
		dx, dy, dz = D[i, 0], D[i, 1], D[i, 2]
		hf = math.sqrt(dx * dx + dy * dy) + 1e-9
		t = 2 * px
		for _ in range(maxit):
			x, y, z = C[0] + dx * t, C[1] + dy * t, C[2] + dz * t
			if x < 0 or x > 1 or y < 0 or y > 1 or (z > zmax and dz >= 0):
				break
			gap = z - bilinear(Z, (1 - y) / px, x / px)
			if gap <= 0:
				hit_out[i] = 1
				break
			if z < zmist:
				hit_out[i] = 2
				break
			t += max(0.7 * px, 0.8 * gap / slope) / hf
		t_out[i] = t
	return t_out, hit_out


@njit(cache=True, parallel=True, fastmath=True)
def visible(P, C, Z, px, zmax, slope, maxit):
	'''Sphere-trace each 3D point toward the eye; False where terrain blocks the ray.'''
	n = P.shape[0]
	vis = np.ones(n, dtype=np.bool_)
	bias = 0.35 * px
	for i in prange(n):
		dx, dy, dz = C[0] - P[i, 0], C[1] - P[i, 1], C[2] - P[i, 2]
		dist = math.sqrt(dx * dx + dy * dy + dz * dz)
		dx, dy, dz = dx / dist, dy / dist, dz / dist
		hf = math.sqrt(dx * dx + dy * dy) + 1e-9
		t = 2 * px / hf
		for _ in range(maxit):
			x, y, z = P[i, 0] + dx * t, P[i, 1] + dy * t, P[i, 2] + dz * t
			gap = z - bilinear(Z, (1 - y) / px, x / px)
			out = x < 0 or x > 1 or y < 0 or y > 1
			if t >= dist or z > zmax or out:
				break
			if gap < -bias:
				vis[i] = False
				break
			t += max(px, 0.8 * max(gap, 0.0) / slope) / hf
	return vis


@njit(cache=True, parallel=True, fastmath=True)
def cast_shadow(Zc, px, sx, sy, rise, zmax):
	'''March every cell toward the sun (horizontal unit dir sx, sy; rise per unit). 1 = in shadow.'''
	m = Zc.shape[0]
	out = np.zeros((m, m))
	for r in prange(m):
		for c in range(m):
			x0, y0, z0 = c * px, 1 - r * px, Zc[r, c]
			t = 1.5 * px
			while True:
				X, Y, Rz = x0 + sx * t, y0 + sy * t, z0 + rise * t
				if X < 0 or X > 1 or Y < 0 or Y > 1 or Rz > zmax:
					break
				if bilinear(Zc, (1 - Y) / px, X / px) > Rz + 0.3 * px:
					out[r, c] = 1.0
					break
				t += px
	return out


# ------------------------------------------------------------------ streamlines

@njit(cache=True, inline="always")
def in_window(x, y, win):
	if win[0] == 1:
		return math.hypot(x - win[1], y - win[2]) <= win[3]
	if win[0] == 2:
		return win[1] <= x <= win[3] and win[2] <= y <= win[4]
	return True


@njit(cache=True)
def cell_of(x, y, aspect, gh, gw):
	r = int((aspect - y) / (2 * aspect) * (gh - 1) + 0.5)
	c = int((x + 1) / 2 * (gw - 1) + 0.5)
	return r, c


@njit(cache=True)
def valid(x, y, floor, aspect, hit, flat, tone, lo, win):
	'''Buffer cell under screen point (x, y) if a stroke may pass there, else (-1, -1).'''
	if abs(x) > 1 or abs(y) > aspect:
		return -1, -1
	gh, gw = hit.shape
	r, c = cell_of(x, y, aspect, gh, gw)
	if hit[r, c] != 1 or flat[r, c] or tone[r, c] < lo * floor or not in_window(x, y, win):
		return -1, -1
	return r, c


@njit(cache=True)
def sep(t, lo, smin, smax):
	f = 1 - (t - lo) / (1 - lo + 1e-9)
	return smin + (smax - smin) * f * f


@njit(cache=True)
def crowded(occ, x, y, d, lid, cell, aspect):
	oh, ow = occ.shape
	cx, cy = int((x + 1) / cell), int((aspect - y) / cell)
	k = max(int(d / cell + 0.5), 1)
	for dy in range(-k, k + 1):
		yy = min(max(cy + dy, 0), oh - 1)
		for dx in range(-k, k + 1):
			if dx * dx + dy * dy > k * k:
				continue
			v = occ[yy, min(max(cx + dx, 0), ow - 1)]
			if v >= 0 and v != lid:
				return True
	return False


@njit(cache=True)
def mark(occ, line, lid, cell, aspect):
	oh, ow = occ.shape
	for i in range(line.shape[0]):
		occ[min(int((aspect - line[i, 1]) / cell), oh - 1), min(int((line[i, 0] + 1) / cell), ow - 1)] = lid


@njit(cache=True)
def trace(sx, sy, TH, tone, hit, flat, occ, win, lid, h, lo, smin, smax, cell, aspect, maxlen):
	'''Grow a streamline both ways from (sx, sy) until it leaves the tone, turns sharply or crowds a neighbour.'''
	fwd = np.empty((maxlen, 2))
	bwd = np.empty((maxlen, 2))
	counts = np.zeros(2, dtype=np.int64)
	for k in range(2):
		sign = 1.0 if k == 0 else -1.0
		buf = fwd if k == 0 else bwd
		x, y = sx, sy
		pvx, pvy, have_prev = 0.0, 0.0, False
		n = 0
		for _ in range(maxlen):
			r, c = valid(x, y, 0.7, aspect, hit, flat, tone, lo, win)
			if r < 0:
				break
			vx, vy = math.cos(TH[r, c]), math.sin(TH[r, c])
			if not have_prev:
				vx, vy = vx * sign, vy * sign
			else:
				if vx * pvx + vy * pvy < 0:
					vx, vy = -vx, -vy
				if vx * pvx + vy * pvy < 0.87:  # > 30 deg turn in one step: a vortex
					break
			qx, qy = x + h * vx, y + h * vy
			rq, cq = valid(qx, qy, 0.7, aspect, hit, flat, tone, lo, win)
			if rq < 0 or crowded(occ, qx, qy, 0.55 * sep(max(tone[rq, cq], lo), lo, smin, smax), lid, cell, aspect):
				break
			buf[n, 0], buf[n, 1] = qx, qy
			n += 1
			x, y, pvx, pvy, have_prev = qx, qy, vx, vy, True
		counts[k] = n
	nb, nf = counts[1], counts[0]
	line = np.empty((nb + 1 + nf, 2))
	for i in range(nb):
		line[i] = bwd[nb - 1 - i]
	line[nb, 0], line[nb, 1] = sx, sy
	line[nb + 1:] = fwd[:nf]
	return line


@njit(cache=True)
def flow_all(order, TH, tone, hit, flat, occ, win, h, lo, smin, smax, cell, aspect, min_len, maxlen):
	'''The whole Jobard-Lefer loop: random seeds (pre-shuffled `order`) plus a FIFO of seeds one
	spacing either side of each accepted line. Returns a list of (N, 2) streamlines.'''
	gh, gw = hit.shape
	cap = 1 << 20
	qx, qy = np.empty(cap), np.empty(cap)
	head, tail = 0, 0
	lines = List()
	nxt, lid = 0, 0
	while True:
		if head != tail:
			sx, sy = qx[head], qy[head]
			head = (head + 1) % cap
		elif nxt < order.shape[0]:
			r, c = order[nxt] // gw, order[nxt] % gw
			nxt += 1
			sx, sy = c / (gw - 1) * 2 - 1, aspect - r / (gh - 1) * 2 * aspect
		else:
			break
		r, c = valid(sx, sy, 1.0, aspect, hit, flat, tone, lo, win)
		if r < 0 or crowded(occ, sx, sy, sep(tone[r, c], lo, smin, smax), -2, cell, aspect):
			continue
		line = trace(sx, sy, TH, tone, hit, flat, occ, win, lid, h, lo, smin, smax, cell, aspect, maxlen)
		n = line.shape[0]
		if n < min_len:
			continue
		mark(occ, line, lid, cell, aspect)
		for i in range(0, n - 1, 3):
			a, b = max(i - 1, 0), min(i + 1, n - 1)
			nx, ny = -(line[b, 1] - line[a, 1]), line[b, 0] - line[a, 0]
			nn = math.sqrt(nx * nx + ny * ny) + 1e-12
			r, c = valid(line[i, 0], line[i, 1], 1.0, aspect, hit, flat, tone, lo, win)
			if r < 0:
				continue
			dd = sep(tone[r, c], lo, smin, smax) / nn
			for sgn in (1.0, -1.0):
				if (tail + 1) % cap != head:  # drop seeds if the ring is full (never in practice)
					qx[tail], qy[tail] = line[i, 0] + sgn * nx * dd, line[i, 1] + sgn * ny * dd
					tail = (tail + 1) % cap
		lines.append(line)
		lid += 1
	return lines


@njit(cache=True)
def simplify(xy, tol):
	'''Douglas-Peucker with segment distance - same vertices as skimage.measure.approximate_polygon.'''
	n = xy.shape[0]
	if n < 3:
		return xy.copy()
	keep = np.zeros(n, dtype=np.bool_)
	keep[0] = keep[n - 1] = True
	stack = np.empty((n, 2), dtype=np.int64)
	stack[0, 0], stack[0, 1] = 0, n - 1
	top = 1
	while top:
		top -= 1
		a, b = stack[top, 0], stack[top, 1]
		ax, ay, bx, by = xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1]
		dx, dy = bx - ax, by - ay
		L = math.sqrt(dx * dx + dy * dy)
		best, bi = -1.0, -1
		for i in range(a + 1, b):
			px, py = xy[i, 0], xy[i, 1]
			if (px - ax) * dx + (py - ay) * dy > 0 and (bx - px) * dx + (by - py) * dy > 0:
				d = abs(dy * px - dx * py + bx * ay - by * ax) / L
			else:  # projects outside the segment: distance to the nearer endpoint
				d = min(math.hypot(px - ax, py - ay), math.hypot(px - bx, py - by))
			if d > best:
				best, bi = d, i
		if best > tol:
			keep[bi] = True
			stack[top, 0], stack[top, 1] = a, bi
			stack[top + 1, 0], stack[top + 1, 1] = bi, b
			top += 2
	return xy[keep]


# ------------------------------------------------------------------ strata (orthographic)

@njit(cache=True, parallel=True, fastmath=True)
def visible_ortho(P, to_cam, Hr, ts, bias):
	'''Strata's camera is at infinity: every ray shares direction to_cam. Grid coords x = X + .5, y = .5 - Y.'''
	n = Hr.shape[0]
	vis = np.ones(P.shape[0], dtype=np.bool_)
	for i in prange(P.shape[0]):
		for t in ts:
			x = P[i, 0] + t * to_cam[0] + 0.5
			y = 0.5 - (P[i, 1] + t * to_cam[1])
			if x < 0 or x > 1 or y < 0 or y > 1:
				break  # left the map: clear sky
			if bilinear(Hr, y * (n - 1), x * (n - 1)) > P[i, 2] + t * to_cam[2] + bias:
				vis[i] = False
				break
	return vis


@njit(cache=True)
def flow_ortho(seeds, vx, vy, cells, flow_len):
	'''Strata's streamlines: step along (vx, vy), stop on another line's cell or our own trail.'''
	n = vx.shape[0]
	owner = -np.ones((cells, cells), dtype=np.int64)
	h = 0.5 / n
	buf = np.empty((flow_len + 1, 2))
	out = List()
	for i in range(seeds.shape[0]):
		x, y = seeds[i, 0], seeds[i, 1]
		cx, cy = int(x * cells), int(y * cells)
		if owner[cy, cx] != -1:
			continue
		owner[cy, cx] = i
		buf[0, 0], buf[0, 1] = x, y
		k = 1
		for _ in range(flow_len):
			gi, gj = min(int(y * n), n - 1), min(int(x * n), n - 1)
			x, y = x + vx[gi, gj] * h * 2, y + vy[gi, gj] * h * 2
			if not (0 <= x < 1 and 0 <= y < 1):
				break
			ncx, ncy = int(x * cells), int(y * cells)
			if ncx != cx or ncy != cy:
				if owner[ncy, ncx] != -1:
					break
				cx, cy = ncx, ncy
				owner[cy, cx] = i
			buf[k, 0], buf[k, 1] = x, y
			k += 1
		if k > 4:
			out.append(buf[:k].copy())
	return out


# ------------------------------------------------------------------ no-numba fallbacks
# Same stopping rules as the kernels above, vectorized over all rays/points that are still marching.

if not HAVE_NUMBA:
	from scipy import ndimage
	from skimage.measure import approximate_polygon

	def _bil(F, row, col):
		return ndimage.map_coordinates(F, [row, col], order=1, mode="nearest")

	def gbuffer_march(C, D, Z, px, zmax, slope, zmist, maxit):
		n = D.shape[0]
		t = np.full(n, 2 * px)
		hit = np.zeros(n, dtype=np.int8)
		hf = np.hypot(D[:, 0], D[:, 1]) + 1e-9
		a = np.arange(n)
		for _ in range(maxit):
			if not a.size:
				break
			R = C + D[a] * t[a, None]
			out = (R[:, 0] < 0) | (R[:, 0] > 1) | (R[:, 1] < 0) | (R[:, 1] > 1) | ((R[:, 2] > zmax) & (D[a, 2] >= 0))
			gap = R[:, 2] - _bil(Z, (1 - R[:, 1]) / px, R[:, 0] / px)
			ground = (gap <= 0) & ~out
			mist = (R[:, 2] < zmist) & ~ground & ~out
			hit[a[ground]] = 1
			hit[a[mist]] = 2
			stay = ~(out | ground | mist)
			a = a[stay]
			t[a] += np.maximum(0.7 * px, 0.8 * gap[stay] / slope) / hf[a]
		return t, hit

	def visible(P, C, Z, px, zmax, slope, maxit):
		D = C - P
		dist = np.linalg.norm(D, axis=1)
		Dn = D / dist[:, None]
		hf = np.hypot(Dn[:, 0], Dn[:, 1]) + 1e-9
		t = 2 * px / hf
		vis = np.ones(len(P), dtype=bool)
		bias = 0.35 * px
		a = np.arange(len(P))
		for _ in range(maxit):
			if not a.size:
				break
			R = P[a] + Dn[a] * t[a, None]
			gap = R[:, 2] - _bil(Z, (1 - R[:, 1]) / px, R[:, 0] / px)
			out = (R[:, 0] < 0) | (R[:, 0] > 1) | (R[:, 1] < 0) | (R[:, 1] > 1)
			done = (t[a] >= dist[a]) | (R[:, 2] > zmax) | out
			blocked = (gap < -bias) & ~done
			vis[a[blocked]] = False
			stay = ~(done | blocked)
			a = a[stay]
			t[a] += np.maximum(px, 0.8 * np.maximum(gap[stay], 0) / slope) / hf[a]
		return vis

	def cast_shadow(Zc, px, sx, sy, rise, zmax):
		m = Zc.shape[0]
		rr, cc = np.mgrid[0:m, 0:m]
		x0, y0, z0 = (cc * px).ravel(), (1 - rr * px).ravel(), Zc.ravel()
		out_arr = np.zeros(m * m)
		a = np.arange(m * m)
		t = 1.5 * px
		while a.size:
			X, Y, Rz = x0[a] + sx * t, y0[a] + sy * t, z0[a] + rise * t
			out = (X < 0) | (X > 1) | (Y < 0) | (Y > 1) | (Rz > zmax)
			blocked = ~out & (_bil(Zc, (1 - Y) / px, X / px) > Rz + 0.3 * px)
			out_arr[a[blocked]] = 1.0
			a = a[~(out | blocked)]
			t += px
		return out_arr.reshape(m, m)

	def visible_ortho(P, to_cam, Hr, ts, bias):
		n = Hr.shape[0]
		vis = np.ones(P.shape[0], dtype=bool)
		a = np.arange(P.shape[0])
		for t in ts:
			if not a.size:
				break
			x = P[a, 0] + t * to_cam[0] + 0.5
			y = 0.5 - (P[a, 1] + t * to_cam[1])
			out = (x < 0) | (x > 1) | (y < 0) | (y > 1)
			blocked = ~out & (_bil(Hr, y * (n - 1), x * (n - 1)) > P[a, 2] + t * to_cam[2] + bias)
			vis[a[blocked]] = False
			a = a[~(out | blocked)]
		return vis

	def simplify(xy, tol):
		return approximate_polygon(xy, tol)
