"""Flow Field
Hundreds of polylines following a smooth vector field."""
import math
import random
from LineDream import Canvas, Line

random.seed(11)

Canvas.width = 600
Canvas.height = 600

def angle_at(x, y):
	return (math.sin(x * 0.009 + math.cos(y * 0.011) * 1.4)
	        + math.cos(y * 0.007 - x * 0.003)) * math.pi * 0.75

for gx in range(-20, 620, 28):
	for gy in range(-20, 620, 28):
		x, y = gx + random.uniform(-10, 10), gy + random.uniform(-10, 10)
		pts = []
		for _ in range(random.randint(18, 40)):
			pts.append((x, y))
			a = angle_at(x, y)
			x += math.cos(a) * 5
			y += math.sin(a) * 5
		accent = random.random() < 0.07
		Line(pts, stroke_color='#E8A33D' if accent else '#1C1B18',
		     stroke_width=1.6 if accent else 0.8)

Canvas.save("flow_field.svg")
