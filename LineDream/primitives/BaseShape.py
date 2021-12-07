# this should mirror what is available in an svg
import math
import sys

import numpy as np

from ..enviornment.Canvas import Canvas
from ..helpers.CircleMath import CircleMath

class BaseShape(object):
	def __init__(self, **kwargs):
		self._vertices = np.array([])
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
		if  self.vertices.size > 0:
			_rv = self.vertices[0]
			rv = (_rv[0], _rv[1])

		return rv

	# Not sure why this was here, but it was not used so I'm commenting out.
	# @property
	# def last_vertex(self):
	# 	# or do you just raise an exception?
	# 	rv = (None, None)
	# 	if  self.vertices.size > 0:
	# 		_rv = self.vertices[-1]
	# 		rv = (_rv[0], _rv[1])
	#
	# 	return rv

	# @property
	# def length(self):
	# 	x = np.array(xcoordinates)
	# 	y = np.array(ycoordinates)
	#
	# 	dist_array = (x[:-1] - x[1:]) ** 2 + (y[:-1] - y[1:]) ** 2
	#
	# 	np.sum(np.sqrt(dist_array))

	def add_vertex(self, x, y, z=0):

		l = self._vertices.tolist()
		l.append([x,y,z,1])

		self._vertices = np.array(l)


	def transform(self, x, y, z=0):
		# THIS IS DEFAULT BEHAVIOR IF IT IS NOT OVERRIDEN IN THE DERIVED CLASS.
		# This will work for shapes/objects that user vertex's.. but not for things like Circles
		#
		# for idx, (o_x,o_y) in enumerate(self._vertices):
		# 	o_x = o_x + x
		# 	o_y = o_y + y
		#
		# 	self._vertices[idx] = (o_x, o_y)

		# tmat = matrix.translation_matrix(x, y, z)

		translate_matrix = np.identity(4)
		translate_matrix[0, -1] = x
		translate_matrix[1, -1] = y
		translate_matrix[2, -1] = z


		self._vertices = np.dot(self._vertices, translate_matrix.T)[:, :4]


	@property
	def min_x(self):
		rv = self.first_vertex[0]

		_v = self.vertices.tolist()

		for x,y, z, _ in _v:
			if x < rv:
				rv = x
		return rv

	@property
	def max_x(self):
		rv = self.first_vertex[0]

		_v = self.vertices.tolist()

		for x,y, z, _ in _v:
			if x > rv:
				rv = x
		return rv

	@property
	def min_y(self):
		rv = self.first_vertex[1]

		_v = self.vertices.tolist()

		for x,y, z, _ in _v:
			if y < rv:
				rv = y
		return rv

	@property
	def max_y(self):
		rv = self.first_vertex[1]

		_v = self.vertices.tolist()

		for x,y, z, _ in _v:
			if y > rv:
				rv = y
		return rv

	@property
	def center(self):
		x = ((self.max_x - self.min_x)/2) + self.min_x
		y = ((self.max_y - self.min_y)/2) + self.min_y
		return (x,y)

	# def rotate(self, degrees, origin=None):
	#
	# 	if not origin:
	# 		x = [p[0] for p in self.vertices]
	# 		y = [p[1] for p in self.vertices]
	# 		origin = (max(x) + min(x)) / 2, (max(y) + min(y)) / 2
	#
	# 	self._vertices = CircleMath.rotate(self.vertices, origin=origin, degrees=degrees)


	def rotate(self, theta, origin=None, axis=np.array([0, 0, 1])):
		"""Rotate the display by the given angle along the given axis.

		:param theta: The angle by which to rotate (in radians)
		:type theta: float

		:param axis: The axis along which to rotate (defaults to the z-axis)
		:type axis: np.ndarray or list

		:returns: The rotation matrix used to apply the transformation.
		:rtype: np.ndarray

	   """

		#CONVERT DEGREES TO RADIANS
		theta = theta * math.pi / 180

		axis = np.array(axis[:])

		#

		# tmat = matrix.rotation_matrix(axis, theta)

		#

		# NOTE: THIS ALL MIGHT NEED TO BE RADIANS
		# This might be the wrong interpretatino...
		x = axis[0]
		y = axis[1]
		z = axis[2]

		# x, y, z = _normalize(axis)

		s = np.sin(theta)
		c = np.cos(theta)
		c1 = 1 - c

		rotation = np.identity(4)

		rotation[0, 0] = x * x * c1 + c
		rotation[0, 1] = x * y * c1 - z * s
		rotation[0, 2] = x * z * c1 + y * s
		rotation[1, 0] = y * x * c1 + z * s
		rotation[1, 1] = y * y * c1 + c
		rotation[1, 2] = y * z * c1 - x * s
		rotation[2, 0] = x * z * c1 - y * s
		rotation[2, 1] = y * z * c1 + x * s
		rotation[2, 2] = z * z * c1 + c

		if origin == None:
			x_c,y_c = self.center
		else:
			x_c = origin[0]
			y_c = origin[1]

		self.transform(-x_c, -y_c)


		rotation[0, -1] = x_c
		rotation[1, -1] = y_c
		rotation[2, -1] = 1

		self._vertices = np.dot(self._vertices, rotation.T)[:, :4]

		# self.transform(x_c, y_c)
		# self._vertices = self._vertices.dot(rotation)


	def rotate_x(self, theta):
		"""Rotate the view along the x axis.

		:param theta: angle by which to rotate (in radians)
		:type theta: float

		:returns: The rotation matrix used to apply the transformation.
		:rtype: np.ndarray

		"""
		self.rotate(theta, axis=np.array([1, 0, 0]))

	def rotate_y(self, theta):
		"""Rotate the view along the y axis.

		:param theta: angle by which to rotate (in radians)
		:type theta: float

		:returns: The rotation matrix used to apply the transformation.
		:rtype: np.ndarray

	   """
		self.rotate(theta, axis=np.array([0, 1, 0]))

	def rotate_z(self, theta):
		"""Rotate the view along the z axis.

		:param theta: angle by which to rotate (in radians)
		:type theta: float

		:returns: The rotation matrix used to apply the transformation.
		:rtype: np.ndarray

	   """
		self.rotate(theta, axis=np.array([0, 0, 1]))


	def scale(self, amt, amt_y=None, origin=None):

		sys.stderr.write("Scale is not fully implemented yet.\n")

		if amt_y==None:
			amt_y = amt

		scale_matrix = np.identity(4)
		scale_matrix[0, 0] = amt
		scale_matrix[1, 1] = amt_y
		scale_matrix[2, 2] = 1 # default for z

		self._vertices = self._vertices.dot(scale_matrix)

		# raise Exception('Inherited class should implement')