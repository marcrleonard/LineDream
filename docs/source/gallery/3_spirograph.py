"""Spirograph
A single hypotrochoid: one continuous stroke, ideal for a pen plotter."""
import math
from LineDream import Canvas, Line

Canvas.width = 600
Canvas.height = 600
Canvas.background_color = '#F4EEE1'

R, r, d = 200, 72, 150
cx, cy = 300, 300

pts = []
for step in range(0, 9 * 360 * 2 + 1):
	t = math.radians(step / 2)
	x = (R - r) * math.cos(t) + d * math.cos((R - r) / r * t)
	y = (R - r) * math.sin(t) - d * math.sin((R - r) / r * t)
	pts.append((cx + x, cy + y))

Line(pts, stroke_color='#C2410C', stroke_width=0.7)

Canvas.save("spirograph.svg")
