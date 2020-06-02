from LineDream import Canvas, Square


Canvas.width=1000
Canvas.height=700
Canvas.background_color='black'


s1 = Square(200,300, 30, stroke_color='white')
s2 = Square(200,300, 30, stroke_color='white')
s2.translate(20,30)

Canvas.save(f'translate_test.svg')
