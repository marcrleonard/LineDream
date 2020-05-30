class BaseCanvas(object):
	def __init__(self, x=1200, y=800):
		self.width = x
		self.height = y

		self.draw_queue = []

	def draw(self):
		for d in self.draw_queue:
			print(d)


Canvas = BaseCanvas()