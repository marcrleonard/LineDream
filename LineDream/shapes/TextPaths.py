from .hershey.hershey import Hershey
from .Path import Path
import copy



class TextPaths():
	'''This is a collection of paths that create text'''
	def __init__(self, input_text, kerning=5, **kwargs):
		self.kwargs = kwargs

		self.input_text = input_text
		self.is_multipath=True

		self.h = Hershey()
		self.h.effect(self.input_text, 'futural')

		self._kerning = kerning

		self.letters = []

		self._run()


	def _run(self):
		for idx, l in enumerate(self.input_text):
			all_info = self.h.letter_paths[idx]

			offset = all_info['offset']
			midpoint= all_info['midpoint']
			ps = all_info['paths']

			l_x, l_y = self._get_min(copy.deepcopy(ps))
			h_x, h_y = self._get_max(copy.deepcopy(ps))
			letter = []
			for lp in ps:
				p = Path(lp, **self.kwargs)
				p.transform(midpoint+(self.kerning*idx), 0)

				letter.append(p)

			self.letters.append(letter)

	@property
	def kerning(self):
		return self._kerning
	@kerning.setter
	def kerning(self, v):
		self._kerning = v

	def _get_min(self, v):

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
		for letter in self.letters:
			for path in letter:
				path.transform(x,y)


	def scale(self, percentage):
		'''

		(1 - scale) * currentPosition.

		If the center is (10, 20) and you are scaling by 3 then translate by (1 - 3)*10, (1 - 3)*20 = (-20, -40):

		:param percentage:
		:return:
		'''

		for letter in self.letters:
			al = copy.deepcopy(letter)
			max_x, _ = al[0].verticies.pop()
			min_x = max_x
			letter_center_x = (max_x+min_x)/2
			for p in al:
				for x,y in p.verticies:
					if x>max_x:
						max_x = x
					if x<min_x:
						min_x = x

			for p in letter:

				_, origin_y = p.center
				for idx, (x,y) in enumerate(p.verticies):

					dist_x =  x - letter_center_x
					dist_y =  y - origin_y

					d_x = percentage* dist_x
					d_y = percentage * dist_y

					new_x = letter_center_x+d_x
					new_y = origin_y+d_y

					p.verticies[idx] = (new_x, new_y)

				# print(f'{vertex} -> {x}, {y}')