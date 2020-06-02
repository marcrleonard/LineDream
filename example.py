import random
from LineDream import Path, Canvas, Rectangle, Square, Ellipse, Point, Circle, CircleMath

Canvas.width=1000
Canvas.height=700
Canvas.background_color='black'


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

x,y = CircleMath.distance_to_coords(20, 220)
Circle(x)

Canvas.save(f'example.svg')
