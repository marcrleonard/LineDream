import random
from collections import defaultdict
from LineDream import Line, Canvas, Text, Rectangle, Square, Ellipse, Point, Circle, CircleMath

random.seed(10)

Canvas.width=900
Canvas.height=500
Canvas.background_color='beige'
Canvas.units = 'mm'

for pp in range(100):
	x = random.randint(0, Canvas.width)
	y = random.randint(0, 400)

	coords = (x,y)
	p = Point(*coords)

	p.stroke_color= 'black'

circ_rad = 150

_c_x, _c_y = Canvas.width/2, Canvas.height

Circle(_c_x, _c_y, circ_rad)

last_coords = defaultdict(lambda: (_c_x, _c_y, circ_rad))

BASE_SPACING = 2

for i in range(0, 360, 2):

	d = circ_rad

	for ss in range(1,6):

		d_point_x, d_point_y = CircleMath.distance_to_coords(i, d)
		start_point_x, start_point_y = _c_x + d_point_x, _c_y + d_point_y

		_dist = random.randint(4,(12*ss*2))

		dr_point_x, dr_point_y = CircleMath.distance_to_coords(i, _dist)
		end_point_x, end_point_y = start_point_x + dr_point_x, start_point_y + dr_point_y

		Line([(start_point_x, start_point_y), (end_point_x, end_point_y)])

		Circle(end_point_x, end_point_y, 2, fill_color='beige')

		d += _dist+ BASE_SPACING*(ss)


tt = Text('LineDream',0,Canvas.height - 50, width=Canvas.width, align='center', font_size=32, stroke_color='black')

Canvas.save(f'example.svg')

