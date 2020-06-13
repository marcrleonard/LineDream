# this should mirror what is available in an svg
from ..enviornment.Canvas import Canvas
from ..helpers.CircleMath import CircleMath

class BaseShape(object):
	def __init__(self, **kwargs):
		self._vertices = []
		self._fill_color='none'
		self._stroke_color='black'
		self._stroke_width=1
		self._close_path = False

		self.is_circle=False
		self.is_multipath = False

		for k,v in kwargs.items():
			if hasattr(self, k):
				setattr(self, k, v)
			else:
				print(f'attr "{k}" does not exist.')

		Canvas.draw_queue.append(self)


	def __str__(self):
		return f'<{__class__} fill_color: {self.fill_color}>'

	def __repr__(self):
		return f'<{__class__} fill_color: {self.fill_color}>'

	@property
	def fill_color(self):
		return self._fill_color

	@fill_color.setter
	def fill_color(self, v):
		self._fill_color = v


	@property
	def close_path(self):
		return self._close_path

	@close_path.setter
	def close_path(self, v:bool):
		self._close_path = v


	@property
	def stroke_color(self):
		return self._stroke_color

	@stroke_color.setter
	def stroke_color(self, v):
		self._stroke_color = v

	@property
	def stroke_width(self):
		return self._stroke_width

	@stroke_width.setter
	def stroke_width(self, v):
		self._stroke_width = v

	@property
	def vertices(self):

		return self._vertices

	@property
	def first_vertex(self):
		# or do you just raise an exception?
		rv = (None, None)
		if self.vertices:
			rv = self.vertices[0]

		return rv

	@property
	def last_vertex(self):
		# or do you just raise an exception?
		rv = (None, None)
		if self.vertices:
			rv = self.vertices[-1]

		return rv

	# @property
	# def length(self):
	# 	x = np.array(xcoordinates)
	# 	y = np.array(ycoordinates)
	#
	# 	dist_array = (x[:-1] - x[1:]) ** 2 + (y[:-1] - y[1:]) ** 2
	#
	# 	np.sum(np.sqrt(dist_array))

	def add_vertex(self, x, y, z=0):
		self._vertices.append((x, y))


	def transform(self, x, y):
		# THIS IS DEFAULT BEHAVIOR IF IT IS NOT OVERRIDEN IN THE DERIVED CLASS.
		# This will work for shapes/objects that user vertex's.. but not for things like Circles

		for idx, (o_x,o_y) in enumerate(self._vertices):
			o_x = o_x + x
			o_y = o_y + y

			self._vertices[idx] = (o_x, o_y)

	@property
	def min_x(self):
		rv = self.first_vertex[0]
		for x,y in self.vertices:
			if x < rv:
				rv = x
		return rv

	@property
	def max_x(self):
		rv = self.first_vertex[0]
		for x, y in self.vertices:
			if x > rv:
				rv = x
		return rv

	@property
	def min_y(self):
		rv = self.first_vertex[1]
		for x, y in self.vertices:
			if y < rv:
				rv = y
		return rv

	@property
	def max_y(self):
		rv = self.first_vertex[1]
		for x, y in self.vertices:
			if y > rv:
				rv = y
		return rv

	@property
	def center(self):
		x = ((self.max_x - self.min_x)/2) + self.min_x
		y = ((self.max_y - self.min_y)/2) + self.min_y
		return (x,y)

	def rotate(self, degrees, origin=None):

		if not origin:
			x = [p[0] for p in self.vertices]
			y = [p[1] for p in self.vertices]
			origin = (max(x) + min(x)) / 2, (max(y) + min(y)) / 2

		self._vertices = CircleMath.rotate(self.vertices, origin=origin, degrees=degrees)


	def scale(self, degrees, origin=None):
		raise Exception('Inherited class should implement')