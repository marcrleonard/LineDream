from .BaseShape import BaseShape

from typing import Tuple
class Line(BaseShape):
	def __init__(self, verticies:[Tuple]=None, **kwargs):
		super().__init__(**kwargs)

		if verticies:
			for (x,y) in verticies:
				self.add_vertex(x,y)




# if __name__ == '__main__':
# 	p = Path([(1,2),(2,5) ])