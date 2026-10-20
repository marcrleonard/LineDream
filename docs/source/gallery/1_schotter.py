"""Schotter
After Georg Nees (1968): order dissolving into chaos, row by row."""
import random
from LineDream import Canvas, Square

random.seed(3)

Canvas.width = 360
Canvas.height = 600
Canvas.background_color = '#F4EEE1'

cols, rows, size = 10, 18, 26
x0 = (Canvas.width - cols * size) / 2 + size / 2

for row in range(rows):
	chaos = row / rows
	for col in range(cols):
		jitter_x = random.uniform(-1, 1) * chaos * 9
		jitter_y = random.uniform(-1, 1) * chaos * 9
		s = Square(x0 + col * size + jitter_x, 64 + row * size + jitter_y, size)
		s.rotate(random.uniform(-45, 45) * chaos)
		s.stroke_color = '#1C1B18'

Canvas.save("schotter.svg")
