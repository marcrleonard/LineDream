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

	def transform(self, x=0, y=0):
		self.x = self.x + x
		self.y = self.y + y

	def scale(self, percent_x, percent_y=1):
		self.radius_x = self.radius_x * percent_x
		self.radius_y = self.radius_y * percent_y

class Circle(Ellipse):
	def __init__(self,x,y, radius, **kwargs):
		super().__init__(x,y, radius, radius, **kwargs)

	def scale(self, percent, _percent_y=0):
		self.radius_x = self.radius_x * percent
		self.radius_y = self.radius_y * percent

class Point(Circle):
	def __init__(self,x,y, **kwargs):
		super().__init__(x,y, .5, **kwargs)

	def scale(self, percent_x=1, _percent_y=1):
		raise Exception('Cannot scale a Point')