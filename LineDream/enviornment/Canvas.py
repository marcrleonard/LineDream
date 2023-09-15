import drawsvg
from PIL import Image
import io


'''
SHAPES TO ADD:
	- Rectangle/Square?
	- Mesh?
	- Curves (via paths)


'''

def create_svg_object(shape:'BaseShape'):

	svg_obj = None


	if shape.is_arc:
			svg_obj = drawsvg.Arc(cx=shape.x, cy=shape.y * -1, r=shape.radius, cw=True,
								  start_deg=shape.start_angle, end_deg=shape.end_angle,
								  fill=shape.fill_color, stroke=shape.stroke_color,
								  stroke_width=shape.stroke_width, fill_opacity=shape.fill_opacity,
								  close=shape.close_path
								  )


	elif shape.is_circle:

		svg_obj = drawsvg.Ellipse(shape.x, shape.y, shape.radius_x, shape.radius_y,
								  fill=shape.fill_color, stroke=shape.stroke_color,
								  stroke_width=shape.stroke_width, fill_opacity=shape.fill_opacity)


	elif len(shape.vertices) > 0:

		verts = shape.vertices

		verts = verts.tolist()

		# # verts = vertices.tolist()
		if len(verts)== 0 :
			print(f'verts contains one item of {[[0.0, 0.0, 0.0]]} ... continuing.')
			return None

		start_l = verts.pop(0)
		start_x = start_l[0]
		start_y = start_l[1]

		other_verts = []
		for o_v in verts:
			x = o_v[0]

			y = o_v[1]

			# z = o_v[2]
			other_verts.append(x)
			other_verts.append(y)

		svg_obj = drawsvg.Lines(start_x, start_y, *other_verts, fill=shape.fill_color, stroke=shape.stroke_color,
								stroke_width=shape.stroke_width, fill_opacity=shape.fill_opacity, close=shape.close_path)

	return svg_obj

class BaseCanvas(object):
	'''The canvas object controls all the render controls.'''
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


	def save(self, filename, open_viewer=False, flush=True, as_string=False):

		bg = {}
		if self.background_color:
			bg = {
				"style": f'background-color:{self.background_color}'
			}

		svg_canvas = drawsvg.Drawing(
			self.width,
			self.height,
			origin=(0, 0),
			**bg,
			xmlns__inkscape = "http://www.inkscape.org/namespaces/inkscape"
		)

		# There may be a better way to do this through the init above, but I found it confusing.
		# it was much easier to just hardcode it.
		svg_canvas.viewBox = (0, 0, self.width, self.height)

		if self.units:
			svg_canvas.width = f'{self.width}{self.units}'
			svg_canvas.height = f'{self.height}{self.units}'

		for shape in self.draw_queue:

			if shape.is_text:

				for line in shape.text_lines:

					if len(line) <= 1:
						continue

					if len(line) == 2:
						svg_obj = drawsvg.Line(line[0].real, line[0].imag, line[1].real, line[1].imag, fill=shape.fill_color, stroke=shape.stroke_color,
											   stroke_width=shape.stroke_width, fill_opacity=shape.fill_opacity)
					else:

						start_x = line[0].real
						start_y = line[0].imag

						addl_points = []
						for c in line[1:]:
							addl_points.append(c.real)
							addl_points.append(c.imag)
						#*(c.real, c.imag) for c in line[1:]

						svg_obj = drawsvg.Lines(start_x, start_y, *addl_points,
						fill=shape.fill_color, stroke=shape.stroke_color,
						stroke_width=shape.stroke_width, fill_opacity=shape.fill_opacity
						)
					# else:
					# 	path = drawsvg.Lines((c.real, c.imag) for c in line)

					svg_canvas.append(svg_obj)


			if shape.is_group:
				g = drawsvg.Group(
					id=shape.id,
					inkscape__label=shape.label,
					inkscape__groupmode="layer"
				)
				for shape in shape.items:
					svg_obj = create_svg_object(shape)
					if svg_obj:
						g.append(svg_obj)
				svg_canvas.append(g)

			else:
				svg_obj = create_svg_object(shape)
				if svg_obj:
					svg_canvas.append(svg_obj)


		if open_viewer:
			c = svg_canvas.rasterize()
			image_stream = io.BytesIO(c.png_data)
			# Open the image using PIL from the BytesIO object
			im = Image.open(image_stream)

			# Display the image
			im.show()

			return True

		if as_string:
			return svg_canvas.as_svg(header='')

		else:

			svg_canvas.save_svg(filename)

		if flush:
			self.flush()

	def flush(self):
		'''Clear the render queue'''
		self.draw_queue=[]

	def remove_by_id(self, id):
		'''This function is used to remove an item from teh draw queue by its id. It is not particularly fast
		since it loops through the render queue. The reason why I added this is to remove an object after it's been
		added to a group. I haven't fully thought through a better way to implement groups, so this will have to do for now.
		Another idea would be to add a dict of id:obj for each, then when we delete the key, it somehow deletes the object too.
		I dunno. I'll think about it more.'''
		for idx, item in enumerate(self.draw_queue):
			if item.id == id:
				del self.draw_queue[idx]
				return True

_Canvas = BaseCanvas()
