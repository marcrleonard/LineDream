from .BaseShape import BaseShape


class Ellipse(BaseShape):
	def __init__(self,x,y, radius_x, radius_y,   **kwargs):
		super().__init__(**kwargs)
		self.x = x
		self.y = y
		self.radius_x = radius_x
		self.radius_y = radius_y

		self.is_circle=True

	def add_vertex(self, coords:tuple):
		raise Exception("Ellipses do not have vertexes")


class Circle(Ellipse):
	def __init__(self,x,y, radius, **kwargs):
		super().__init__(x,y, radius, radius, **kwargs)

class Point(Circle):
	def __init__(self,x,y, **kwargs):
		super().__init__(x,y, .5, **kwargs)