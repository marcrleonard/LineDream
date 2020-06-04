from .BaseShape import BaseShape

class TextShape(BaseShape):
	'''This is a collection of paths that create text'''
	def __init__(self, input_text, **kwargs):
		super().__init__(**kwargs)

		self.input_text = input_text

