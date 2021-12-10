from .BaseShape import BaseShape


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
		"""
		Send a message to a recipient

		:param str sender: The person sending the message
		:param str recipient: The recipient of the message
		:param str message_body: The body of the message
		:param priority: The priority of the message, can be a number 1-5
		:type priority: integer or None
		:return: the message id
		:rtype: int
		:raises ValueError: if the message_body exceeds 160 characters
		:raises TypeError: if the message_body is not a basestring
		"""

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


class Arc(BaseShape):
	'''This is how to create an ellipse'''

	def __init__(self, x, y, radius, start_angle, end_angle, **kwargs):
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
		self.y = y
		self.radius = radius
		self.start_angle = start_angle
		self.end_angle = end_angle

		self.is_arc = True