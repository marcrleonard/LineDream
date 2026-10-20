# Changelog

## 0.4.0 (unreleased)

### Changed
- vpype is no longer a dependency. `Text` uses a vendored copy of vpype's Hershey text layout (MIT) with the 32 fonts
  shipped as JSON; output is bit-identical to 0.3.15. This drops Shapely, scipy, click and the rest of vpype's tree.
- `drawsvg[all]` (cairosvg, imageio-ffmpeg, pwkit) is skipped under Pyodide/emscripten. It only backs
  `Canvas.save(open_viewer=True)`.
- beautifulsoup4 moved from the runtime dependencies to the `docs` extra.
- `LineDream.__version__` now matches the package version (it was stuck at 0.3.14).

### Added
- Runs in the browser: `micropip.install("linedream")` works under Pyodide, and there is a live playground at
  https://linedream.marcrleonard.com/playground/.
- `Line.from_array(xy, **style)` builds a line from an (N, 2) or (N, 3) array.
- `Group.extend(items)` adds many shapes in one pass.

### Fixed
- `Text` honours its `line_spacing` argument (it was always 1.0).

### Performance
- `BaseShape.add_vertex` and `Line(vertices)` no longer round-trip through Python lists (5,000 vertices: ~6 s to
  ~0.03 s).
- `Group.extend` avoids one draw-queue scan per item (3,000 items behind 20k shapes: 3.1 s to 0.002 s).

### Packaging
- Built with uv; `setup.py` and `tox.ini` are gone. CI tests Python 3.9 to 3.14 on Linux plus macOS and Windows, the
  built wheel, and the suite under Pyodide.
- Releases are published to PyPI from GitHub Actions with trusted publishing when a `v*` tag is pushed.
