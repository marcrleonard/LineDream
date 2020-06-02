import random
from LineDream import Path, Canvas, Rectangle, Square, Ellipse, Point, Circle, CircleMath

Canvas.width=1000
Canvas.height=700
Canvas.background_color='black'

#todo: add 'LineDream' text

for pp in range(100):
	x = random.randint(0, Canvas.width)
	y = random.randint(0, 400)

	coords = (x,y)
	p = Point(*coords)

	p.stroke_color= 'white'

c_size = 180

circle_center = Canvas.width/2, Canvas.height+c_size/2
c = Circle(*circle_center, 180)
c.stroke_color='white'

c = Circle(*circle_center, 200)
c.stroke_color='white'

c = Circle(*circle_center, 220)
c.stroke_color='white'

#180 to 0
# make rays

long=True
for degrees in range(360,180,-10):

	dist_from_circle = 250

	line_len = 100
	if long:
		line_len = 200
		long=False
	else:
		long=True

	d_x_s, d_y_s = CircleMath.distance_to_coords(degrees, dist_from_circle)
	x1 = circle_center[0] + d_x_s
	y1 = circle_center[1] + d_y_s

	d_x, d_y = CircleMath.distance_to_coords(degrees, dist_from_circle + line_len)
	x2 = circle_center[0] + d_x
	y2 = circle_center[1] + d_y

	Path([(x1,y1), (x2,y2)], stroke_color='white')

Canvas.save(f'example.svg')
