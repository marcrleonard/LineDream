
from CreativeLib import Path, Canvas, Rectangle, Square, Ellipse, Point

Canvas.width=200
Canvas.height=200
Canvas.background_color='black'

r = Point((100, 100))
r.fill_color='red'
r.stroke_color = 'red'

Canvas.save(f'REC_TEST.svg')
