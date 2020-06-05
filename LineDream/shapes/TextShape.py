from .hershey.hershey import Hershey
from .Path import Path
import copy

class TextShape():
	'''This is a collection of paths that create text'''
	def __init__(self, input_text, **kwargs):

		self.input_text = input_text
		self.is_multipath=True

		h = Hershey()
		h.effect(self.input_text, 'futural')

		self.paths = []

		kerning = 8
		x_offset = 0

		for l in self.input_text:
			ps = h.letter_paths.get(l)

			l_x, l_y = self._get_min(copy.deepcopy(ps))
			h_x, h_y = self._get_max(copy.deepcopy(ps))
			x_offset = x_offset + (h_x - l_x) + kerning
			for lp in ps:
				p = Path(lp, **kwargs)
				p.transform(x_offset, 0)

				self.paths.append(p)


	def _get_min(self, v):

		v = v

		l_x, l_y = v[0].pop()

		for path in v:

			for x,y in path:
				if x < l_x:
					l_x = x

				if y < l_y:
					l_y = y

		return l_x, l_y

	def _get_max(self, v):
		l_x, l_y = v[0].pop()

		for path in v:

			for x, y in path:
				if x > l_x:
					l_x = x

				if y > l_y:
					l_y = y

		return l_x, l_y

	def transform(self, x, y):
		for path in self.paths:
			path.transform(x,y)
