import math
import numpy as np

class CircleMath:
	def __init__(self):
		pass

	@staticmethod
	def distance_to_coords(degrees, distance):
		angle_radians = degrees * math.pi / 180
		x = math.cos(angle_radians) * distance
		y = math.sin(angle_radians) * distance
		return x, y

	@staticmethod
	def rotate(p, origin=(0, 0), degrees=0):
		# https://stackoverflow.com/a/58781388/6775715
		angle = np.deg2rad(degrees)
		R = np.array([[np.cos(angle), -np.sin(angle)],
					  [np.sin(angle), np.cos(angle)]])
		o = np.atleast_2d(origin)
		p = np.atleast_2d(p)
		rv = np.squeeze((R @ (p.T - o.T) + o.T).T)
		#todo: remove this once native numpy arrays are supported
		return rv.tolist()
