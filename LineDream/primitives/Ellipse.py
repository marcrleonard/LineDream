from .BaseShape import BaseShape
from ..helpers.CircleMath import CircleMath


class Ellipse(BaseShape):
	'''This is how to create an ellipse'''
	def __init__(self,x,y, radius_x, radius_y,   **kwargs):
		'''This is the init for creating an __init__
		:param x: x coord of center
		:param y: y coord of center
		:param radius_x: radius x
		:param radius_y: radius y
		:param kwargs: style kwargs


		.. todo:: THIS NEEDS WORK
		'''
		super().__init__(**kwargs)
		self.x = x
		""" x coord of center"""
		self.y = y
		self.radius_x = radius_x
		self.radius_y = radius_y

		self.is_circle=True

	def add_vertex(self, *coords):
		raise Exception("Ellipses do not have vertexes")

	def transform(self, x=0, y=0, z=0):
		'''
		Translate the ellipse by x/y/z
		:param x:
		:param y:
		:param z:
		:return:
		'''

		self.x = self.x + x
		self.y = self.y + y
		return self

	def scale(self, percent_x, percent_y=100, **kwargs):
		self.radius_x = self.radius_x * (percent_x/100)
		self.radius_y = self.radius_y * (percent_y/100)
		return self

class Circle(Ellipse):
	def __init__(self,x,y, radius, **kwargs):
		super().__init__(x,y, radius, radius, **kwargs)

	def scale(self, percent, _percent_y=0):
		self.radius_x = self.radius_x * (percent/100)
		self.radius_y = self.radius_y * (percent/100)
		return self

class Point(Circle):
	def __init__(self,x,y, **kwargs):
		super().__init__(x,y, .5, **kwargs)

	def scale(self, percent_x=1, _percent_y=1):
		raise Exception('Cannot scale a Point')


class Arc(BaseShape):
	'''This is how to create an ellipse'''

	def __init__(self, x, y, radius, start_angle, end_angle, x_y_start_coords=False, **kwargs):
		'''This is the init for creating an __init__
		:param x: x coord of center
		:param y: y coord of center
		:param radius_x: radius x
		:param radius_y: radius y
		:param x_y_start_coords: If true, this will use the x,y params as where the 0 degree location is - not the center of the arc. For example:
								If you specify Arc(10, 15, 3, 0, 270) the arc start will be at (10,15).
		:param kwargs: style kwargs


		.. todo:: THIS NEEDS WORK
		'''
		super().__init__(**kwargs)

		if x_y_start_coords:
			d_x, d_y = CircleMath.distance_to_coords(start_angle, radius)
			x = x-d_x
			y = y-d_y

		self.x = x
		self.y = y
		self.radius = radius
		self.start_angle = start_angle
		self.end_angle = end_angle

		self.is_arc = True

	@property
	def start_coords(self):
		'''For the give arc, get the x,y coordinates of the start of the arc'''
		d_x, d_y = CircleMath.distance_to_coords(self.start_angle, self.radius)
		return self.x + d_x, self.y +d_y

	@property
	def end_coords(self):
		'''For the give arc, get the x,y coordinates of the end start of the arc'''
		d_x, d_y = CircleMath.distance_to_coords(self.end_angle, self.radius)
		return self.x + d_x, self.y + d_y

	def scale(self, percent, _percent_y=0, origin=None):
		self.radius = self.radius * (percent/100)
		return self

	def rotate(self, theta, origin=None, axis=None):
		self.start_angle +=theta
		self.end_angle += theta
		return self

