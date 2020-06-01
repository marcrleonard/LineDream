from .BaseShape import BaseShape

#TODO: Consider if we want to implement rounded edges:
# https://developer.mozilla.org/en-US/docs/Web/SVG/Element/rect

class Rectangle(BaseShape):
	def __init__(self, c_x, c_y, width, height, **kwargs):
		super().__init__(**kwargs)
		self.c_x = c_x
		self.c_y = c_y
		self.width = width
		self.height = height

		self.close_path=True

		# top left
		t_l_x = c_x - (width/2)
		t_l_y = c_y - (height/2)

		# top right
		t_r_x = c_x + (width/2)
		t_r_y = c_y - (height/2)

		#bottom right
		b_r_x = c_x + (width / 2)
		b_r_y = c_y + (height / 2)

		# bottom left
		b_l_x = c_x - (width/2)
		b_l_y = c_y + (height/2)

		# this order is very important.
		# It adds the vertex's in a clockwise rotation
		self.add_vertex((t_l_x, t_l_y))
		self.add_vertex((t_r_x, t_r_y))
		self.add_vertex((b_r_x, b_r_y))
		self.add_vertex((b_l_x, b_l_y))

class Square(Rectangle):
	def __init__(self, c_x, c_y, width, **kwargs):
		super().__init__(c_x, c_y, width, width,**kwargs)
