"""Topography
Concentric rings, each nudged by layered sine waves."""
import math
from LineDream import Canvas, Line

Canvas.width = 600
Canvas.height = 600
Canvas.background_color = '#263238'

cx, cy = 300, 300

for ring in range(1, 34):
	base = ring * 8
	pts = []
	for step in range(181):
		t = math.radians(step * 2)
		wobble = (math.sin(t * 3 + ring * 0.35) * 0.09
		          + math.sin(t * 7 - ring * 0.2) * 0.04)
		r = base * (1 + wobble)
		pts.append((cx + math.cos(t) * r, cy + math.sin(t) * r))
	color = '#FFCB6B' if ring % 6 == 0 else '#89DDFF'
	Line(pts, stroke_color=color, stroke_width=1.2 if ring % 6 == 0 else 0.7)

Canvas.save("topography.svg")
