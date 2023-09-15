from .BaseShape import BaseShape

from vpype.text import text_block



class Text(BaseShape):
	'''This is how to create an ellipse'''
	def __init__(self, text, x,y, width=200, font_size=18.0, align="left", line_spacing=1.0, font_name='futural',   **kwargs):
		''''''
		super().__init__(**kwargs)

		self.x = x
		self.y = y
		self.text = text

		self.is_text=True

		# This is a unique data structure to vpype. The canvas render has a different way to render them.
		self.a = text_block(text, width, font_name, font_size, align, 1.0)
		self.a.translate(x, y)
		self.text_lines = self.a.lines

	def add_vertex(self, *coords):
		raise Exception("Cannot accept additional vertexes")

	def transform(self, *coords):
		self.a.translate(*coords)
