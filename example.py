import random

from shaper import Path, Canvas, Rectangle, Square, Ellipse, Point


Canvas.width=1000
Canvas.height=700
Canvas.background_color='black'

points = []
for pp in range(200):
	x = random.randint(0, Canvas.width)
	y = random.randint(0, 200)

	p = Point(x,y)
	p.stroke_color='white'


Canvas.save(f'example.svg')
