
from LineDream import Path, Canvas, Rectangle, Square, Ellipse, Point

Canvas.width=200
Canvas.height=200
Canvas.background_color='beige'

pt = Point(100, 100)
pt.stroke_color = 'black'

pt2 = Point(100, 100)
pt2.stroke_color = 'black'
pt2.transform(20,5)

p=Path([(3,3),(30,20),(4,18)])
p.close_path=True
p.fill_color='blue'
p.stroke_color='none'

p2=Path([(3,3),(30,20),(4,18)])
p2.close_path=True
p2.fill_color='blue'
p2.stroke_color='none'
p2.transform(20,5)

r = Rectangle(130,130,20,15)
r.fill_color='green'

r2 = Rectangle(130,130,20,15)
r2.fill_color='green'
r2.transform(20, 5)

s = Square(20, 170, 5)
s.stroke_color='yellow'
s.fill_color='red'

s2 = Square(20, 170, 5)
s2.stroke_color='yellow'
s2.fill_color='red'
s2.transform(20,5)

e = Ellipse(120, 30, 5, 8)
e.fill_color='orange'

e2 = Ellipse(120, 30, 5, 8)
e2.fill_color='orange'
e2.transform(20,5)

output_file_name = 'test_output.svg'
Canvas.save(output_file_name)



with open(output_file_name, 'r') as t:
	with open('test_master_output.svg', 'r') as m:
		assert t.read() == m.read()
