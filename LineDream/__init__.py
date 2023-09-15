from .primitives.Line import Line
from .primitives.BaseShape import BaseShape
from .primitives.Ellipse import Circle, Ellipse, Point, Arc
from .primitives.Rectangle import Rectangle, Square
from .primitives.Rectangle import Rectangle, Square
from .primitives.Group import Group
from .primitives.Text import Text
from .enviornment.Canvas import _Canvas
from .helpers.CircleMath import CircleMath
# from .primitives.TextLine import TextLine
# from .enviornment.Tweaks import Tweaks

Canvas = _Canvas
"""
Canvas Singleton Object. This controls the output 'canvas', and rendering of the draw loop.

### Attributes
- width
- height
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
	'Group',
	'CircleMath',
	'BaseShape',
	'Canvas',
	'Text'
]


