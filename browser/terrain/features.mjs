// Roads, trails and water for the terrain app: OpenStreetMap vector tiles from OpenFreeMap (no key, CORS open,
// OpenMapTiles schema), decoded here (a Mapbox Vector Tile is a small protobuf, so no library), clipped to the loaded
// area and returned as polylines in grid coordinates (u right, v down, 0..1), ready to drape on the terrain.
// No DOM in here except fetch, so the decoding and clipping run (and are tested) under Node: see test/features.test.mjs.

export const TILEJSON_URL = "https://tiles.openfreemap.org/planet";
export const MAX_VECTOR_ZOOM = 14;  // OpenFreeMap's deepest tiles; footpaths only appear at 13-14
export const MAX_ACROSS = 6;        // at most 6 x 6 tiles per area: finer zooms for small areas, coarser for big ones
export const KINDS = ["roads", "trails", "rivers", "lakes"];
export const ATTRIBUTION = "Map data © OpenStreetMap contributors · tiles OpenFreeMap";

// OpenMapTiles layer + class -> what the app calls it. Service roads (driveways, car parks), ditches and swimming
// pools are left out: at landscape scale they are clutter.
const ROADS = new Set(["motorway", "trunk", "primary", "secondary", "tertiary", "minor", "track"]);
const RIVERS = new Set(["river", "stream", "canal"]);
const LAKES = new Set(["lake", "pond", "river", "ocean"]);

export function classify(layer, props, type) {
  if (props.brunnel === "tunnel") return null;
  if (layer === "transportation" && type === 2) return ROADS.has(props.class) ? "roads" : props.class === "path" ? "trails" : null;
  if (layer === "waterway" && type === 2) return RIVERS.has(props.class) ? "rivers" : null;
  if (layer === "water" && type === 3) return LAKES.has(props.class) ? "lakes" : null;
  return null;
}

// ------------------------------------------------------------------------------------------- protobuf / MVT

class Reader {
  constructor(buf) { this.b = buf; this.i = 0; }
  varint() {
    let v = 0, mul = 1, byte;
    do { byte = this.b[this.i++]; v += (byte & 0x7f) * mul; mul *= 128; } while (byte & 0x80);
    return v;
  }
  int64() {  // negatives are ten-byte two's complement, beyond what a double holds exactly
    let v = 0n, shift = 0n, byte;
    do { byte = this.b[this.i++]; v |= BigInt(byte & 0x7f) << shift; shift += 7n; } while (byte & 0x80);
    return Number(BigInt.asIntN(64, v));
  }
  bytes() { const n = this.varint(), s = this.b.subarray(this.i, this.i + n); this.i += n; return s; }
  skip(wire) {
    if (wire === 0) this.varint();
    else if (wire === 1) this.i += 8;
    else if (wire === 2) this.i += this.varint();
    else if (wire === 5) this.i += 4;
    else throw new Error(`vector tile: unknown wire type ${wire}`);
  }
  *fields() {
    while (this.i < this.b.length) { const key = this.varint(); yield [key >>> 3, key & 7]; }
  }
  packed() {
    const end = this.varint() + this.i, out = [];
    while (this.i < end) out.push(this.varint());
    return out;
  }
}

const text = new TextDecoder();
const zigzag = (n) => (n % 2 ? -(n + 1) / 2 : n / 2);

function readValue(buf) {
  const r = new Reader(buf), view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  let v = null;
  for (const [f, w] of r.fields()) {
    if (f === 1) v = text.decode(r.bytes());
    else if (f === 2) { v = view.getFloat32(r.i, true); r.i += 4; }
    else if (f === 3) { v = view.getFloat64(r.i, true); r.i += 8; }
    else if (f === 4) v = r.int64();
    else if (f === 5) v = r.varint();
    else if (f === 6) v = zigzag(r.varint());
    else if (f === 7) v = !!r.varint();
    else r.skip(w);
  }
  return v;
}

// geometry commands -> rings / lines as [[x, y], ...] in tile units; polygon rings come back closed
export function decodeGeometry(cmds, type) {
  const parts = [];
  let x = 0, y = 0, cur = null;
  for (let i = 0; i < cmds.length;) {
    const id = cmds[i] & 7, count = cmds[i++] >>> 3;
    if (id === 7) { if (cur && cur.length) cur.push(cur[0].slice()); continue; }
    for (let k = 0; k < count; k++) {
      x += zigzag(cmds[i++]);
      y += zigzag(cmds[i++]);
      if (id === 1) parts.push((cur = [[x, y]]));
      else cur.push([x, y]);
    }
  }
  return type === 1 ? parts : parts.filter((p) => p.length > 1);
}

// {layerName: {extent, features: [{type, props, parts}]}}
export function decodeTile(buf) {
  const r = new Reader(buf instanceof Uint8Array ? buf : new Uint8Array(buf)), layers = {};
  for (const [f, w] of r.fields()) {
    if (f !== 3) { r.skip(w); continue; }
    const lr = new Reader(r.bytes()), keys = [], values = [], raw = [];
    let name = "", extent = 4096;
    for (const [lf, lw] of lr.fields()) {
      if (lf === 1) name = text.decode(lr.bytes());
      else if (lf === 2) raw.push(lr.bytes());
      else if (lf === 3) keys.push(text.decode(lr.bytes()));
      else if (lf === 4) values.push(readValue(lr.bytes()));
      else if (lf === 5) extent = lr.varint();
      else lr.skip(lw);
    }
    const features = raw.map((fb) => {
      const fr = new Reader(fb);
      let tags = [], type = 0, geom = [];
      for (const [ff, fw] of fr.fields()) {
        if (ff === 2) tags = fr.packed();
        else if (ff === 3) type = fr.varint();
        else if (ff === 4) geom = fr.packed();
        else fr.skip(fw);
      }
      const props = {};
      for (let i = 0; i + 1 < tags.length; i += 2) props[keys[tags[i]]] = values[tags[i + 1]];
      return { type, props, parts: decodeGeometry(geom, type) };
    });
    layers[name] = { extent, features };
  }
  return layers;
}

// ------------------------------------------------------------------------------------------- clipping

// The pieces of a polyline inside [x0, x1] x [y0, y1] (Liang-Barsky per segment). Tiles overlap a little at their
// edges, so each is clipped to its own square to keep shared lines from being drawn twice.
export function clipPolyline(pts, x0, y0, x1, y1) {
  const out = [];
  let run = null;
  const end = () => { if (run && run.length > 1) out.push(run); run = null; };
  for (let i = 0; i + 1 < pts.length; i++) {
    const [ax, ay] = pts[i], [bx, by] = pts[i + 1], dx = bx - ax, dy = by - ay;
    let t0 = 0, t1 = 1, ok = true;
    for (const [p, q] of [[-dx, ax - x0], [dx, x1 - ax], [-dy, ay - y0], [dy, y1 - ay]]) {
      if (p === 0) { if (q < 0) { ok = false; break; } continue; }
      const t = q / p;
      if (p < 0) { if (t > t1) { ok = false; break; } if (t > t0) t0 = t; }
      else { if (t < t0) { ok = false; break; } if (t < t1) t1 = t; }
    }
    if (!ok) { end(); continue; }
    const a = [ax + t0 * dx, ay + t0 * dy], b = [ax + t1 * dx, ay + t1 * dy];
    if (!run) run = [a];
    else if (t0 > 0) { end(); run = [a]; }
    run.push(b);
    if (t1 < 1) end();
  }
  end();
  return out;
}

// ------------------------------------------------------------------------------------------- area -> tiles

// The finest vector zoom whose tiles over this area number at most MAX_ACROSS across.
export function vectorZoom(meta) {
  for (let vz = Math.min(MAX_VECTOR_ZOOM, meta.zoom + 3); vz > 0; vz--) {
    const s = 2 ** (vz - meta.zoom) / 256;
    const n = Math.floor((meta.x0 + meta.size) * s) - Math.floor(meta.x0 * s) + 1;
    if (n <= MAX_ACROSS || vz <= meta.zoom) return vz;
  }
  return 0;
}

export function tilesFor(meta, vz = vectorZoom(meta)) {
  const s = 2 ** (vz - meta.zoom) / 256, tiles = [];
  const tx0 = Math.floor(meta.x0 * s), ty0 = Math.floor(meta.y0 * s);
  const tx1 = Math.floor((meta.x0 + meta.size) * s), ty1 = Math.floor((meta.y0 + meta.size) * s);
  for (let ty = ty0; ty <= ty1; ty++) for (let tx = tx0; tx <= tx1; tx++) tiles.push([vz, tx, ty]);
  return tiles;
}

// One decoded tile -> {kind: [[[u, v], ...], ...]} in the area's grid coordinates, clipped to tile and area.
export function tileFeatures(layers, [vz, tx, ty], meta) {
  const out = Object.fromEntries(KINDS.map((k) => [k, []]));
  const scale = 2 ** (meta.zoom - vz) * 256;  // tile units -> area-zoom global px, per tile
  for (const [name, { extent, features }] of Object.entries(layers)) {
    const toUV = ([x, y]) => [((tx + x / extent) * scale - meta.x0) / meta.size, ((ty + y / extent) * scale - meta.y0) / meta.size];
    for (const f of features) {
      const kind = classify(name, f.props, f.type);
      if (!kind) continue;
      for (const part of f.parts) {
        for (const piece of clipPolyline(part, 0, 0, extent, extent)) {
          out[kind].push(...clipPolyline(piece.map(toUV), 0, 0, 1, 1));
        }
      }
    }
  }
  return out;
}

// {kind: [[u, v]...][]} -> {kind: {coords: Float32Array (u, v, u, v...), counts: Uint32Array}} for the worker
export function pack(lines) {
  const out = {};
  for (const [kind, polys] of Object.entries(lines)) {
    const counts = Uint32Array.from(polys, (p) => p.length);
    const coords = new Float32Array(counts.reduce((a, b) => a + b, 0) * 2);
    let i = 0;
    for (const p of polys) for (const [u, v] of p) { coords[i++] = u; coords[i++] = v; }
    out[kind] = { coords, counts };
  }
  return out;
}

// ------------------------------------------------------------------------------------------- fetching

let tileUrl = null;

async function tileTemplate() {
  if (!tileUrl) {
    tileUrl = fetch(TILEJSON_URL).then((r) => {
      if (!r.ok) throw new Error(`map tiles: HTTP ${r.status}`);
      return r.json();
    }).then((j) => j.tiles[0]);
    tileUrl.catch(() => { tileUrl = null; });
  }
  return tileUrl;
}

async function fetchTile(template, z, x, y) {
  const res = await fetch(template.replace("{z}", z).replace("{x}", x).replace("{y}", y));
  if (res.status === 204 || res.status === 404) return new Uint8Array(0);  // nothing mapped here (open sea)
  if (!res.ok) throw new Error(`map tile ${z}/${x}/${y}: HTTP ${res.status}`);
  let buf = new Uint8Array(await res.arrayBuffer());
  if (buf[0] === 0x1f && buf[1] === 0x8b) {  // still gzipped (served without Content-Encoding)
    buf = new Uint8Array(await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer());
  }
  return buf;
}

// meta: the loaded area as fetchDEM returns it ({zoom, size, x0, y0, ...})
export async function fetchFeatures(meta, onProgress = () => {}) {
  const template = await tileTemplate();
  const tiles = tilesFor(meta);
  const lines = Object.fromEntries(KINDS.map((k) => [k, []]));
  let done = 0;
  await Promise.all(tiles.map(async (t) => {
    const per = tileFeatures(decodeTile(await fetchTile(template, ...t)), t, meta);
    for (const k of KINDS) lines[k].push(...per[k]);
    onProgress(++done, tiles.length);
  }));
  return { lines, zoom: tiles[0][0] };
}
