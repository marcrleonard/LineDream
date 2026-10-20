'''Hershey font text layout, vendored from vpype (vpype/text.py) so LineDream doesn't depend on vpype.

vpype adapted it from https://github.com/fogleman/axi; both are MIT licensed, see LineDream/fonts/LICENSE.
Differences from vpype: lines are plain lists of complex numpy arrays (no LineCollection), fonts are JSON
instead of pickles, and hyphenation (which needed pyphen) is not supported.
'''
import itertools
import json
import pathlib

import numpy as np

FONT_DIR = pathlib.Path(__file__).parent.parent / 'fonts'
FONT_NAMES = sorted(p.stem for p in FONT_DIR.glob('*.json'))


def _bounds(lines):
	if not lines:
		return None
	return (
		float(min(line.real.min() for line in lines)),
		float(min(line.imag.min() for line in lines)),
		float(max(line.real.max() for line in lines)),
		float(max(line.imag.max() for line in lines)),
	)


def _right_edge(lines):
	b = _bounds(lines)
	return b[2] if b else 0.0


class _Font:
	_FONTS = {}

	def __init__(self, name):
		path = FONT_DIR / (name + '.json')
		if not path.exists():
			raise ValueError(f"font '{name}' could not be found; available: {', '.join(FONT_NAMES)}")
		glyphs = json.loads(path.read_text())
		# each glyph: [left, right, [[x0, y0, x1, y1, ...], ...]]
		self.glyphs = [
			(lt, rt, [np.array(pts[0::2], dtype=complex) + 1j * np.array(pts[1::2], dtype=float) for pts in lines if len(pts) > 2])
			for lt, rt, lines in glyphs
		]
		all_lines = [line for _, _, lines in self.glyphs for line in lines]
		self.max_height = float(max(l.imag.max() for l in all_lines) - min(l.imag.min() for l in all_lines))

	@classmethod
	def get(cls, name):
		if name not in cls._FONTS:
			cls._FONTS[name] = _Font(name)
		return cls._FONTS[name]


def _text_line(txt, font, spacing=0.0, extra=0.0):
	result = []
	x = 0.0
	for ch in txt:
		index = ord(ch) - 32
		if index < 0 or index >= 96:
			x += spacing
			continue
		lt, rt, lines = font.glyphs[index]
		result.extend(line + complex(x - lt, 0.0) for line in lines)
		x += rt - lt + spacing
		if index == 0:
			x += extra
	return result


def _word_wrap(paragraph, width, measure):
	result = []
	for line in paragraph.split('\n'):
		if line == '':
			result.append('\n')
			continue
		fields = [''.join(g) for _, g in itertools.groupby(line, lambda c: c.isspace())]
		if len(fields) % 2 == 1:
			fields.append('')
		x = ''
		for a, b in zip(fields[::2], fields[1::2]):
			if measure(x + a) > width:
				if x == '':  # a single word wider than the block
					result.append(a)
					continue
				result.append(x)
				x = ''
				x += a + b
			else:
				x += a + b
		if x != '':
			result.append(x + '\n')
	return result


def _justify_text(txt, font, width):
	txt = txt.strip()
	lines = _text_line(txt, font)
	w = _right_edge(lines)
	spaces = txt.count(' ')
	if spaces == 0 or w >= width:
		return lines
	return _text_line(txt, font, extra=(width - w) / spaces)


def text_block(paragraph, width, font_name='futural', size=18.0, align='left', line_spacing=1.0, justify=False):
	'''Lay out `paragraph` wrapped to `width`, starting at (0, 0) and extending right and down.

	Returns a list of complex numpy arrays (x + iy), one per pen stroke.'''
	if align not in ('left', 'right', 'center'):
		raise ValueError(f"unknown value for align ('{align}')")
	font = _Font.get(font_name)
	scale = size / font.max_height
	width /= scale

	rows = [
		_justify_text(row, font, width) if justify and not row.endswith('\n') else _text_line(row, font)
		for row in _word_wrap(paragraph, width, lambda t: _right_edge(_text_line(t, font)))
	]

	result = []
	y = 0.0
	for row in rows:
		w = _right_edge(row)
		x = {'left': 0.0, 'right': width - w, 'center': width / 2 - w / 2}[align]
		result.extend(line + complex(x, y) for line in row)
		y += line_spacing * font.max_height

	for line in result:
		line.real *= scale
		line.imag *= scale
	return result
