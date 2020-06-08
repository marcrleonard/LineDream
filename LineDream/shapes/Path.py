from .BaseShape import BaseShape

from typing import Tuple
class Path(BaseShape):
	def __init__(self, verticies:[Tuple]=None, **kwargs):
		super().__init__(**kwargs)

		if verticies:
			for coords in verticies:
				self.add_vertex(coords)




# if __name__ == '__main__':
# 	p = Path([(1,2),(2,5) ])