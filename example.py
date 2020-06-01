import random

from LineDream import Path, Canvas, Rectangle, Square, Ellipse, Point


Canvas.width=1000
Canvas.height=700
Canvas.background_color='black'

points = []
for pp in range(200):
	x = random.randint(0, Canvas.width)
	y = random.randint(0, 200)

	coords = (x,y)
	points.append(coords)

	p = Point(*coords)
	p.stroke_color='white'

points.sort(key = lambda x: x[0])
for idx in range(0, len(points), 10):
	p_start_x, p_start_y = points[idx]

	l = Path([(p_start_x, 220),(p_start_x, 500)])
	l.stroke_color = 'white'

Canvas.save(f'example.svg')
