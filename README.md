![](./example.svg)

LineDream is a generative art library for Python. It is heavily influenced by P5 and Processing. However, it takes a more object oriented approach, with less global state in regards to styling and transformations.

The current output target is SVG. As this provides a robust output set for vector graphics. There is not yet support for a draw loop - it is single frame output, but you could use a loop to simulate this. There are future plans to implement an OpenGL render window.

LineDream library was originally created to make art for a pen plotter, however, the inner object structure could be applied to many different rendering platforms.

Installation
------------
`pip install LineDream`

Documentation
-------------
https://linedream.marcrleonard.com/documentation/

Example
-------
```python
import random
from LineDream import Line, Canvas, Rectangle, Square, Ellipse, Point, Circle, CircleMath, TextLine

Canvas.width=900
Canvas.height=500
Canvas.background_color='black'

for pp in range(100):
	x = random.randint(0, Canvas.width)
	y = random.randint(0, 400)

	coords = (x,y)
	p = Point(*coords)

	p.stroke_color= 'white'

c_size = 180

circle_center = Canvas.width/2, Canvas.height+c_size/2
c = Circle(*circle_center, 180)
c.stroke_color='white'

c = Circle(*circle_center, 200)
c.stroke_color='white'

c = Circle(*circle_center, 220)
c.stroke_color='white'

long=True
for degrees in range(360,180,-10):

	dist_from_circle = 250

	line_len = 40
	if long:
		line_len = 100
		long=False
	else:
		long=True

	d_x_s, d_y_s = CircleMath.distance_to_coords(degrees, dist_from_circle)
	x1 = circle_center[0] + d_x_s
	y1 = circle_center[1] + d_y_s

	d_x, d_y = CircleMath.distance_to_coords(degrees, dist_from_circle + line_len)
	x2 = circle_center[0] + d_x
	y2 = circle_center[1] + d_y

	Line([(x1,y1), (x2,y2)], stroke_color='white')

# EXPERIMENTAL
tt = TextLine('LineDream', kerning=10, stroke_color='white', stroke_width=2)
tt.transform(100, 100)
tt.scale(1.4)

Canvas.save(f'example.svg')
```
# Custom LineDream Shapes

```python
import math
from LineDream.primitives.BaseShape import BaseShape

class Hexagon(BaseShape):

    def __init__(self, c_x, c_y, radius, **kwargs):
        super().__init__(_close_path=True, **kwargs)

        num_points = 6

        # Calculate the angle between each point
        angle_step = 2 * math.pi / num_points

        for i in range(num_points):
            angle = i * angle_step
            x = c_x + radius * math.cos(angle)
            y = c_y + radius * math.sin(angle)
            self.add_vertex(x, y)


if __name__ == "__main__":
    from LineDream import Canvas

    Canvas.width=356
    Canvas.height=276
    Canvas.units = "mm"
    Canvas.background_color = "beige"

    # Add a Hexagon in the middle of canvas with a radius of 50
    Hexagon(Canvas.width/2, Canvas.height/2, 50, )

    Canvas.save('', open_viewer=True)

```

Todos:
-----
- Better document colors/opacity/styles for the SVG
- Add 'tag' notion for lines
- Add `Group` to the example

---

## Development

### Installation for Development
LineDream uses [uv](https://docs.astral.sh/uv/) for development.
```bash
git clone https://github.com/marcrleonard/LineDream.git
cd LineDream

# Create .venv with LineDream (editable) and the dev tools, exactly as pinned in uv.lock
uv sync
```

### Running Tests
```bash
# Run the tests
uv run pytest

# Against a specific Python version (uv downloads it if needed)
uv run --python 3.9 pytest

# Coverage report
uv run coverage run -m pytest && uv run coverage html
```

CI runs the suite on Python 3.9 to 3.14 (plus macOS and Windows) on every pull request; see `.github/workflows/tests.yml`.

### Running in the browser (Pyodide)
LineDream runs under [Pyodide](https://pyodide.org). numpy, pillow and lxml come from the Pyodide distribution and
drawsvg from PyPI; the `drawsvg[all]` extras (only used by `Canvas.save(open_viewer=True)`) are skipped there.

```bash
# Run the test suite under Pyodide in Node
uv build --wheel
cd browser && npm install && npm test   # LINEDREAM_TERRAIN=1 also loads scipy and scikit-image

# Playground: serve the repo root and open http://localhost:8000/browser/?wheel=../dist/linedream-0.3.15-py3-none-any.whl
python -m http.server
```

The website build copies the playground to `/playground/` together with a wheel built from the same checkout.

In your own page, load the packages in `browser/packages.mjs` with `pyodide.loadPackage`, then
`await micropip.install("linedream")`. Releases up to 0.3.15 on PyPI still import vpype, so this needs the next release.

### Building the docs site
```bash
uv run --extra docs python docs/build_website.py   # output in public/
```

### Building and Publishing

```bash
# Build the sdist and wheel into dist/
uv build

# Upload to PyPI (or --publish-url https://test.pypi.org/legacy/ for TestPyPI)
uv publish
```

### Project Structure
All package metadata and dependencies are defined in `pyproject.toml` following modern Python packaging standards (PEP 517/518).
