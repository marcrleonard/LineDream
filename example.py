
from Shaper import Path, Canvas, Rectangle, Square, Ellipse, Point

Canvas.width=200
Canvas.height=200
Canvas.background_color='beige'

r = Point((100, 100))
r.stroke_color = 'black'

p=Path([(3,3),(30,20),(4,18)])
p.close_path=True
p.fill_color='blue'
p.stroke_color='none'

r = Rectangle(130,130,20,15)
r.fill_color='green'

s = Square(20, 170, 5)
s.stroke_color='yellow'
s.fill_color='red'

e = Ellipse((120, 30), 5, 8)
e.fill_color='orange'

Canvas.save(f'test.svg')
