from .BaseShape import BaseShape

from typing import Tuple, List

import numpy as np

class Line(BaseShape):
	'''This is how you create a line with two or more vertices'''
	def __init__(self, vertices:List[Tuple]=None, **kwargs):
		super().__init__(**kwargs)
		if vertices:
			self._set_vertices(vertices)

	@classmethod
	def from_array(cls, xy, **kwargs):
		'''Create a line from an (N, 2) or (N, 3) array-like of x, y[, z] coordinates.
		Builds the vertex array in one step, so it is fast for long polylines.'''
		line = cls(**kwargs)
		line._set_vertices(xy)
		return line

	def _set_vertices(self, xy):
		xy = np.asarray(xy, dtype=float)
		if xy.ndim != 2 or xy.shape[1] not in (2, 3):
			raise ValueError(f'Expected an (N, 2) or (N, 3) array of vertices, got shape {xy.shape}')
		z = xy[:, 2] if xy.shape[1] == 3 else np.zeros(len(xy))
		self._vertices = np.column_stack([xy[:, 0], xy[:, 1], z, np.ones(len(xy))])
