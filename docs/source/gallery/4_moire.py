"""Moiré
Two families of circles, slightly offset, interfering."""
from LineDream import Canvas, Circle

Canvas.width = 600
Canvas.height = 600
Canvas.background_color = '#F4EEE1'

for r in range(6, 300, 6):
	Circle(270, 280, r, stroke_color='#1C1B18', stroke_width=0.8)
	Circle(340, 320, r, stroke_color='#1F5FAE', stroke_width=0.8)

Canvas.save("moire.svg")
