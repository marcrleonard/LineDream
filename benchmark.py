from p5 import noise, Vector
import random
from LineDream import Path, Canvas, Rectangle, Square, Ellipse, Point, Circle, CircleMath, TextPaths
import math
import moderngl
import moderngl_window
import glfw


import moderngl_window as mglw

glfw.init()
window = glfw.create_window(800, 600, "My OpenGL window", None, None)
glfw.make_context_current(window)


class Test(mglw.WindowConfig):
	gl_version = (3, 3)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		print(self)

	def render(self, time, frametime):
		self.ctx.clear(1.0, 0.0, 0.0, 0.0)

mglw.run_window_config(Test)





seed_num = 7

# random.seed(11)
random.seed(seed_num)
# 29.7 x 42.0cm

Canvas.width=420
Canvas.height=297
Canvas.units = 'mm'
# Canvas.width=297
# Canvas.height=420
# Canvas.background_color='beige'

line_len_noise = 40

distance_range_min = 5
distance_range_max = 140
num_lines = 270

perlin_map = []

ctx = moderngl.create_standalone_context()

amt = 0
import time
seconds= 60
timeout = time.time() + seconds
while True:

	for ln in range(num_lines):

		p_delta = ln / num_lines

		n_delta = p_delta * (distance_range_max - distance_range_min)

		y = n_delta + distance_range_min

		sub_lines = random.randint(1, 3)

		x = 0

		# do not map y directly to a pixel by pixel basis. Insert the x amount of lines in a given space.
		# this will allow you to create many lines that are more/less than 1 unit apart.

		# NOTE: This does not have the noise value attached. So this first y value is vanilla and therefor weird looking.
		p = Path()
		p.stroke_width = .3
		noise_position = 4

		perlin_line_len = noise(line_len_noise)
		# perlin_line_len = 0

		line_len = 54

		for s in range(0, line_len):
			y_off = noise(noise_position, y / 22) * 10  # amplitude

			# z = y_off
			x = x + (s * .29) - perlin_line_len  # this multiplier will expand or contract the width
			y = ((y * .982) + y_off)  # this multiplier 'compresses' the end

			p.add_vertex((x, y))

			noise_position += .02

		line_len_noise += (.02 * .982)

	img = Canvas.save(None)




	# ctx = moderngl.create_standalone_context()
	# buf = ctx.buffer(b'Hello World!')  # allocated on the GPU
	# buf.read()

	# Test.ctx.buffer(img)

	Test.ctx.clear(b'Hello World!')

	Canvas.flush()

	amt+=1

	if time.time() > timeout:
		break

print(f'{amt/seconds}fps')

# Canvas.save(f'{seed_num}_2_output.svg')