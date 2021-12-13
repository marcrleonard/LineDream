from LineDream import Canvas, Rectangle

Canvas.width = 300
Canvas.height = 300
Canvas.background_color='#263238'

for x in range(18):
	r = Rectangle(150,150, 200, 200)
	r.rotate(10*x)
	r.stroke_color = '#FFCB6B'

Canvas.save("rectangles.svg")