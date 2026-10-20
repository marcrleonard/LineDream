"""Assemble a self-contained site/ that runs bench.py in the browser with Pyodide (no CDN needed).

    python experiments/browser/build_site.py /path/to/extracted/pyodide-314.0.7
    python -m http.server -d experiments/browser/site 8000      # then open http://localhost:8000

The Pyodide release (https://github.com/pyodide/pyodide/releases, pyodide-<version>.tar.bz2) provides the
runtime and the prebuilt WebAssembly wheels for numpy, scipy, scikit-image, pillow and lxml; only the files
this benchmark needs are copied.
"""
import json
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
SITE = HERE / "site"
PACKAGES = ["numpy", "scipy", "scikit-image", "pillow", "lxml", "micropip"]
CORE = ["pyodide.js", "pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
MODULES = ["fastpaths.py", "dem.py", "strata.py", "vista.py"]


DATA = {"st_helens": (46.1914, -122.1956, 12, 768), "cirque": (42.77776, -109.21715, 14, 1024)}


def ensure_data():
	"""Write the benchmark's elevation grids to data/ (from the AWS Terrarium tiles, cached by dem.py)."""
	import numpy as np
	sys.path.insert(0, str(REPO / "experiments" / "terrain"))
	from dem import fetch_dem
	(HERE / "data").mkdir(exist_ok=True)
	for name, (lat, lon, zoom, size) in DATA.items():
		if (HERE / "data" / f"{name}.npy").exists():
			continue
		grid, info = fetch_dem(lat, lon, zoom=zoom, size=size, meta=True)
		np.save(HERE / "data" / f"{name}.npy", grid.astype(np.float32))
		(HERE / "data" / f"{name}.json").write_text(json.dumps(dict(x0=info.x0, y0=info.y0, zoom=zoom, size=size, lat=lat)))


def norm(name):
	return name.lower().replace("_", "-")


def main(pyodide_dir):
	pyodide_dir = pathlib.Path(pyodide_dir)
	if SITE.exists():
		shutil.rmtree(SITE)
	(SITE / "pyodide").mkdir(parents=True)

	lock = json.loads((pyodide_dir / "pyodide-lock.json").read_text())
	pk = lock["packages"]
	need, stack = set(), list(PACKAGES)
	while stack:
		n = norm(stack.pop())
		if n not in need:
			need.add(n)
			stack += pk[n]["depends"]
	for f in CORE + [pk[n]["file_name"] for n in need]:
		shutil.copy(pyodide_dir / f, SITE / "pyodide" / f)

	wheels = SITE / "wheels"
	subprocess.run(["uv", "build", "--wheel", "-q", "-o", str(wheels), str(REPO)], check=True)
	subprocess.run([sys.executable, "-m", "pip", "download", "-q", "--no-deps", "--only-binary", ":all:",
					"--python-version", "3.14", "-d", str(wheels), "drawsvg~=2.4.0"], check=True)

	(SITE / "py").mkdir()
	for m in MODULES:
		shutil.copy(REPO / "experiments" / "terrain" / m, SITE / "py" / m)
	shutil.copy(HERE / "bench.py", SITE / "py" / "bench.py")
	ensure_data()
	shutil.copytree(HERE / "data", SITE / "data")
	shutil.copy(HERE / "index.html", SITE / "index.html")

	manifest = {
		"packages": sorted(need),
		"wheels": sorted(p.name for p in wheels.glob("*.whl")),
		"modules": MODULES + ["bench.py"],
		"data": sorted(p.name for p in (SITE / "data").iterdir()),
	}
	(SITE / "manifest.json").write_text(json.dumps(manifest, indent=1))
	size = sum(p.stat().st_size for p in SITE.rglob("*") if p.is_file())
	print(f"site/ built: {len(need)} pyodide packages, wheels {manifest['wheels']}, {size / 1e6:.0f} MB")


if __name__ == "__main__":
	main(sys.argv[1])
