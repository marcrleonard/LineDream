from .BaseShape import BaseShape


class Ellipse(BaseShape):
	def __init__(self,coords:tuple, radius_x, radius_y,   **kwargs):
		super().__init__(**kwargs)
		self.x, self.y = coords
		self.radius_x = radius_x
		self.radius_y = radius_y

		self.is_circle=True

	def add_vertex(self, coords:tuple):
		raise Exception("Ellipses do not have vertexes")


class Circle(Ellipse):
	def __init__(self,coords:tuple, radius, **kwargs):
		super().__init__(coords, radius, radius, **kwargs)

class Point(Circle):
	def __init__(self,coords:tuple, **kwargs):
		super().__init__(coords, .5, **kwargs)