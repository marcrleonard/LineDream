LineDream is a creative coding library for Python. It is heavily influenced by P5 and Processing. However, it takes a more object oriented approach, with less global states.

Currently, output files are saved as SVGs. There is not yet support for a draw loop - it is single frame output, but you could use a loop to simulate this.

The library was originally created to make art for a pen plotter, however, the inner object structure could be applied to many different rendering platforms.

Todos:
-----
- Integrate TextPath with Hershey
- Convert all vertexes to Numpy arrays
- Add .transform()
- Add .rotate()
- Add .scale()