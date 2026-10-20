// Packages to load from the Pyodide distribution (pyodide-lock.json), shared by the demo page and the test runner.
// Everything else (drawsvg, LineDream itself) is pure Python and comes in through micropip.

// LineDream's own compiled dependencies. lxml is only used by the experimental TextLine.
export const CORE_PACKAGES = ["numpy", "pillow", "lxml", "micropip"];

// The terrain experiments (scipy.ndimage, skimage.measure). scikit-image's Pyodide recipe pulls in matplotlib,
// networkx, pywavelets, imageio and friends, about 20 packages, so load these only when needed.
export const TERRAIN_PACKAGES = ["scipy", "scikit-image"];
