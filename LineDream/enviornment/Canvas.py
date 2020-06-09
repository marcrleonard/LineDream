import drawSvg


'''
SHAPES TO ADD:
	- Rectangle/Square?
	- Mesh?
	- Curves (via paths)


'''

class BaseCanvas(object):
	def __init__(self, x=1200, y=800, units=None):
		self.width = x
		self.height = y

		self.units=units

		self.background_color= None

		self.draw_queue = []

		self._frame_index = 0

	@property
	def frame_index(self):
		return self._frame_index



	def draw(self):

		for d in self.draw_queue:
			print(d)

	def save(self, filename, open_viewer=False):
		svg_canvas = drawSvg.Drawing(self.width, self.height, origin=(0, 0), displayInline=False)

		# There may be a better way to do this through the init above, but I found it confusing.
		# it was much easier to just hardcode it.
		svg_canvas.viewBox = (0, 0, self.width, self.height)

		if self.units:
			svg_canvas.width = f'{self.width}{self.units}'
			svg_canvas.height = f'{self.height}{self.units}'

		if self.background_color:
			svg_canvas.append(
				drawSvg.Rectangle(x=0, y=0, width='100%', height='100%', fill=self.background_color)
			)

		for shape in self.draw_queue:

			if shape.is_circle:

				# the lib wants to always make Y coods negative. This is likely because of the assumption
				# the moving physically down on the Y axis puts an object in the correct region.
				# Basically, negative Y is 'viewable' where as in P5, positive Y is viewable.

				svg_obj = drawSvg.Ellipse(shape.x, shape.y*-1, shape.radius_x, shape.radius_y,
							fill=shape.fill_color, stroke=shape.stroke_color,
							stroke_width=shape.stroke_width)

			elif len(shape.verticies) > 0:

				verts = shape.verticies


				# verts = vertices.tolist()
				if verts == [[0.0, 0.0, 0.0]]:
					# print(f'verts contains one item of {[[0.0, 0.0, 0.0]]} ... continuing.')
					continue

				start_l = verts.pop(0)
				start_x = start_l[0]

				# the lib wants to always make Y coods negative. This is likely because of the assumption
				# the moving physically down on the Y axis puts an object in the correct region.
				# Basically, negative Y is 'viewable' where as in P5, positive Y is viewable.
				start_y = -start_l[1]

				other_verts = []
				for o_v in verts:
					x = o_v[0]

					# See note above about negative Y values.
					y = -o_v[1]

					# z = o_v[2]
					other_verts.append(x)
					other_verts.append(y)

				svg_obj = drawSvg.Lines(start_x, start_y, *other_verts, fill=shape.fill_color, stroke=shape.stroke_color,
										stroke_width=shape.stroke_width, close=shape.close_path)

			else:
				print("Shape found with no verticies... Skipping...")
				continue

			svg_canvas.append(svg_obj)

		svg_canvas.saveSvg(filename)

		if open_viewer:
			import webbrowser
			webbrowser.open('http://example.com')  # Go to example.com

	def flush(self):
		self.draw_queue=[]

Canvas = BaseCanvas()