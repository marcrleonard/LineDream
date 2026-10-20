from .BaseShape import BaseShape
from .hershey_text import text_block


class Text(BaseShape):
	'''A block of single-stroke Hershey text, wrapped to `width`, with its top-left corner at (x, y).
	See hershey_text.FONT_NAMES for the available fonts.'''
	def __init__(self, text, x,y, width=200, font_size=18.0, align="left", line_spacing=1.0, font_name='futural',   **kwargs):
		''''''
		super().__init__(**kwargs)

		self.x = x
		self.y = y
		self.text = text

		self.is_text=True

		# a list of complex arrays (x + iy), one per pen stroke; the canvas renders these directly
		self.text_lines = text_block(text, width, font_name, font_size, align, line_spacing)
		self.transform(x, y)

	def add_vertex(self, *coords):
		raise Exception("Cannot accept additional vertexes")

	def transform(self, x, y, z=0):
		c = complex(x, y)
		for line in self.text_lines:
			line += c
		return self
