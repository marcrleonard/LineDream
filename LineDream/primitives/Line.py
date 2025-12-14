from .BaseShape import BaseShape

from typing import Tuple, List

class Line(BaseShape):
	'''This is how you create a line with two or more vertices'''
	def __init__(self, vertices:List[Tuple]=None, **kwargs):
		super().__init__(**kwargs)
		if vertices:
			for (x,y) in vertices:
				self.add_vertex(x,y,0)