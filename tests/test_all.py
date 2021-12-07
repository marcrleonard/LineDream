
from LineDream import Line, Canvas, Rectangle, Square, Ellipse, Point

def test_all():

	Canvas.width=200
	Canvas.height=200
	Canvas.background_color='beige'

	pt = Point(100, 100)
	pt.stroke_color = 'black'

	pt2 = Point(100, 100)
	pt2.stroke_color = 'black'
	pt2.transform(20,5)

	p=Line([(3, 3), (30, 20), (4, 18)])
	p.close_path=True
	p.fill_color='blue'
	p.stroke_color='none'

	p2=Line([(3, 3), (30, 20), (4, 18)])
	p2.close_path=True
	p2.fill_color='blue'
	p2.stroke_color='none'
	p2.transform(20,5)

	r = Rectangle(130,130,20,15)
	r.fill_color='green'

	r = Rectangle(40,40,20,15)
	r.fill_color='blue'
	r.rotate(20)

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


	assert s2.center == (40.0, 175.0)
	Point(*s2.center)

	# s2.scale(2, 3, (s2.center[0] - 2, s2.center[1]- 2))

	e = Ellipse(120, 30, 5, 8)
	e.fill_color='orange'

	e = Ellipse(5, 100, 20, 20, fill_color='red', stroke_color='white')
	e.stroke_width=10

	e2 = Ellipse(120, 30, 5, 8)
	e2.fill_color='orange'
	e2.transform(20,5)

	output_file_name = 'tests/test_output.svg'
	Canvas.save(output_file_name)

	assert Canvas.frame_index == 0

	with open(output_file_name, 'r') as t:
		with open('tests/test_master_output.svg', 'r') as m:

			t_l = t.readlines()
			t_m = m.readlines()

			zipped_lines = zip(t_l, t_m)

			for idx, (test_line, master_line) in enumerate(zipped_lines):

				test_line = test_line.lstrip().rstrip()
				master_line = master_line.lstrip().rstrip()

				if not (test_line == master_line):
					print(f"{idx} Line Failed:")
					print(f"   Master Line: {master_line}")
					print(f"   Test Line:   {test_line}")

					assert test_line == master_line
				# assert t.read() == m.read()

if __name__ == '__main__':
	test_all()