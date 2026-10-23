// Elevation data for the terrain app: Terrarium-encoded tiles from the AWS open terrain dataset (no key, CORS open),
// stitched into a square Float32Array of metres, plus the small amount of Web Mercator math the planner needs.
// Mirrors experiments/terrain/dem.py on the terrain branch, so the same lat/lon/zoom gives the same grid.

export const TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png";
export const MAX_ZOOM = 15;

export function globalPx(lat, lon, z) {
  const n = 2 ** z * 256;
  const latR = (lat * Math.PI) / 180;
  return [((lon + 180) / 360) * n, ((1 - Math.log(Math.tan(latR) + 1 / Math.cos(latR)) / Math.PI) / 2) * n];
}

export function metersPerPixel(lat, z) {
  return (156543.03392 * Math.cos((lat * Math.PI) / 180)) / 2 ** z;
}

async function decodeTile(z, x, y) {
  const url = TILE_URL.replace("{z}", z).replace("{x}", x).replace("{y}", y);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`elevation tile ${z}/${x}/${y}: HTTP ${res.status}`);
  // no colour management or premultiplication: the RGB bytes *are* the elevation
  const bmp = await createImageBitmap(await res.blob(), { colorSpaceConversion: "none", premultiplyAlpha: "none" });
  const canvas = new OffscreenCanvas(256, 256);
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(bmp, 0, 0);
  const px = ctx.getImageData(0, 0, 256, 256).data;
  const out = new Float32Array(256 * 256);
  for (let i = 0; i < out.length; i++) out[i] = px[i * 4] * 256 + px[i * 4 + 1] + px[i * 4 + 2] / 256 - 32768;
  return out;
}

// A size x size grid of elevations (metres) centred on lat/lon at the given tile zoom.
export async function fetchDEM(lat, lon, zoom, size, onProgress = () => {}) {
  const [cx, cy] = globalPx(lat, lon, zoom);
  const x0 = Math.floor(cx - size / 2), y0 = Math.floor(cy - size / 2);
  const tx0 = Math.floor(x0 / 256), ty0 = Math.floor(y0 / 256);
  const tx1 = Math.floor((x0 + size) / 256), ty1 = Math.floor((y0 + size) / 256);
  const jobs = [];
  for (let ty = ty0; ty <= ty1; ty++) for (let tx = tx0; tx <= tx1; tx++) jobs.push([tx, ty]);
  let done = 0;
  const tiles = await Promise.all(jobs.map(async ([tx, ty]) => {
    const t = await decodeTile(zoom, tx, ty);
    onProgress(++done, jobs.length);
    return [tx, ty, t];
  }));
  const grid = new Float32Array(size * size);
  for (const [tx, ty, t] of tiles) {
    for (let r = 0; r < 256; r++) {
      const gy = ty * 256 + r - y0;
      if (gy < 0 || gy >= size) continue;
      for (let c = 0; c < 256; c++) {
        const gx = tx * 256 + c - x0;
        if (gx >= 0 && gx < size) grid[gy * size + gx] = t[r * 256 + c];
      }
    }
  }
  let min = Infinity, max = -Infinity;
  for (const v of grid) { if (v < min) min = v; if (v > max) max = v; }
  const mpp = metersPerPixel(lat, zoom);
  return { grid, meta: { lat, lon, zoom, size, x0, y0, mpp, width_m: mpp * size, min, max } };
}

// grid coordinates: u right, v down, both 0..1 across the grid
export function toUV(meta, lat, lon) {
  const [x, y] = globalPx(lat, lon, meta.zoom);
  return [(x - meta.x0) / meta.size, (y - meta.y0) / meta.size];
}

export function toLatLon(meta, u, v) {
  const n = 2 ** meta.zoom * 256;
  const x = meta.x0 + u * meta.size, y = meta.y0 + v * meta.size;
  return [(Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n))) * 180) / Math.PI, (x / n) * 360 - 180];
}

export function sample(grid, size, u, v) {
  const x = Math.min(Math.max(u * (size - 1), 0), size - 1), y = Math.min(Math.max(v * (size - 1), 0), size - 1);
  const x0 = Math.floor(x), y0 = Math.floor(y), x1 = Math.min(x0 + 1, size - 1), y1 = Math.min(y0 + 1, size - 1);
  const fx = x - x0, fy = y - y0;
  const top = grid[y0 * size + x0] * (1 - fx) + grid[y0 * size + x1] * fx;
  const bot = grid[y1 * size + x0] * (1 - fx) + grid[y1 * size + x1] * fx;
  return top * (1 - fy) + bot * fy;
}

// A soft hillshade (light from the north-west) with faint elevation tint, drawn at out x out pixels.
export function hillshade(grid, size, metersPerPx, out) {
  const img = new ImageData(out, out);
  const step = size / out;
  const z = 2.5 / (metersPerPx * step); // a little vertical exaggeration so gentle ground still reads
  const h = (i, j) => grid[Math.min(size - 1, Math.max(0, Math.round(j * step))) * size + Math.min(size - 1, Math.max(0, Math.round(i * step)))];
  let lo = Infinity, hi = -Infinity;
  for (let k = 0; k < grid.length; k += 7) { lo = Math.min(lo, grid[k]); hi = Math.max(hi, grid[k]); }
  const lx = -0.6, ly = -0.6, lz = 0.53;
  for (let j = 0; j < out; j++) {
    for (let i = 0; i < out; i++) {
      const dx = (h(i + 1, j) - h(i - 1, j)) * z / 2, dy = (h(i, j + 1) - h(i, j - 1)) * z / 2;
      const len = Math.hypot(dx, dy, 1);
      const shade = Math.max(0, (-dx * lx - dy * ly + lz) / len);
      const t = (h(i, j) - lo) / (hi - lo || 1);
      const g = 150 + 105 * shade;
      const k = (j * out + i) * 4;
      img.data[k] = g * (0.93 + 0.07 * t); img.data[k + 1] = g * (0.9 + 0.08 * t); img.data[k + 2] = g * (0.82 + 0.1 * t); img.data[k + 3] = 255;
    }
  }
  return img;
}
