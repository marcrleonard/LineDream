from .BaseShape import BaseShape

from typing import Tuple
class Line(BaseShape):
	'''This is how you create a line with two or more vertices'''
	def __init__(self, vertices:[Tuple]=None, **kwargs):
		super().__init__(**kwargs)
		if vertices:
			for (x,y) in vertices:
				self.add_vertex(x,y,0)




# if __name__ == '__main__':
# 	p = Path([(1,2),(2,5) ])