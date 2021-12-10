from .primitives.Line import Line
from .primitives.BaseShape import BaseShape
from .primitives.Ellipse import Circle, Ellipse, Point, Arc
from .primitives.Rectangle import Rectangle, Square
from .enviornment.Canvas import _Canvas
from .helpers.CircleMath import CircleMath
# from .primitives.TextLine import TextLine
# from .enviornment.Tweaks import Tweaks

# def parse_readme():
# 	rv = open('../README.md').readlines()
#
#
#
# 	# print(rv)
# 	if '.svg' in rv[0]:
# 		rv.pop(0)
# 		if '\n' in rv[0]:
# 			rv.pop(0)
#
# 	return ''.join(rv)
#
# __doc__ = parse_readme()

Canvas = _Canvas
"""
Canvas Singleton Object. This controls the output 'canvas', and rendering of the draw loop.

# Attributes
	width
	height
"""
# Note, I had to do this Canvas=_Canvas thing so these ^ doc strings would work.

__all__ = [
	'Line',
	'Circle',
	'Ellipse',
	'Arc',
	'Point',
	'Rectangle',
	'Square',
	'CircleMath',
	'BaseShape',
	'Canvas',
]


