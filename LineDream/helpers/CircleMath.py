import math

class CircleMath:
	def __init__(self):
		pass

	@staticmethod
	def distance_to_coords(degrees, distance):
		angle_radians = degrees * math.pi / 180
		x = math.cos(angle_radians) * distance
		y = math.sin(angle_radians) * distance
		return x, y