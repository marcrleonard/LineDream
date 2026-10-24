// Display units. Everything is stored in metres and kilometres (the renderers, scenes, links and presets never
// change); this only converts what the controls and readouts show. "imperial" shows feet and miles, "metric" metres
// and kilometres. Pure, so it's tested under Node: test/units.test.mjs.

export const SYSTEMS = {
  imperial: { m: { name: "ft", f: 3.28084 }, km: { name: "mi", f: 0.621371 } },
  metric: { m: { name: "m", f: 1 }, km: { name: "km", f: 1 } },
};
export const DEFAULT_SYSTEM = "imperial";

const unit = (sys, kind) => (SYSTEMS[sys] || SYSTEMS[DEFAULT_SYSTEM])[kind];
export const unitName = (sys, kind) => unit(sys, kind).name;
export const toDisplay = (sys, kind, v) => v * unit(sys, kind).f;
export const fromDisplay = (sys, kind, v) => v / unit(sys, kind).f;

// A round slider step near `step` (in stored units) once converted: 1, 2, 2.5 or 5 times a power of ten.
export function niceStep(sys, kind, step) {
  const x = toDisplay(sys, kind, step);
  if (unit(sys, kind).f === 1) return step;
  const p = 10 ** Math.floor(Math.log10(x)), r = x / p;
  return (r < 1.5 ? 1 : r < 2.25 ? 2 : r < 3.5 ? 2.5 : r < 7.5 ? 5 : 10) * p;
}

// A slider's range in display units: min/max rounded outward to whole steps.
export function displayRange(sys, kind, min, max, step) {
  const s = niceStep(sys, kind, step);
  return { min: Math.floor(toDisplay(sys, kind, min) / s) * s, max: Math.ceil(toDisplay(sys, kind, max) / s) * s, step: s };
}

const group = (n, digits = 0) => n.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const fmtLength = (sys, m) => `${group(Math.round(toDisplay(sys, "m", m)))} ${unitName(sys, "m")}`;
export function fmtDistance(sys, km) {
  const v = toDisplay(sys, "km", km);
  return `${group(v, v < 10 ? 1 : 0)} ${unitName(sys, "km")}`;
}
