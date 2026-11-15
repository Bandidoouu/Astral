/** "Find your planetary twin": from a home location to the nearest valid 1 km Earth patch.
 * Valid = a patch in the index (land; the ocean has no patches) whose center land cover is a
 * promising analog zone (MODIS IGBP 7, 10, 15, 16). Nothing here is stored or sent anywhere. */
export interface PatchCatalog { body: number[]; lat: number[]; lon: number[]; region: number[]; regions: string[]; lc: number[]; lc_code: number[]; land_cover: string[] }
export interface HomePatch { index: number; lat: number; lon: number; region: string; distanceKm: number; notes: string[] }

const R = 6371;
const KEEP = new Set([7, 10, 15, 16]);
const dist = (a: number, b: number, c: number, d: number) => {
  const r = Math.PI / 180;
  const x = Math.sin(a * r) * Math.sin(c * r) + Math.cos(a * r) * Math.cos(c * r) * Math.cos((d - b) * r);
  return R * Math.acos(Math.min(1, Math.max(-1, x)));
};

function nearest(cat: PatchCatalog, lat: number, lon: number, ok: (i: number) => boolean) {
  let best = -1, bestD = Infinity;
  for (let i = 0; i < cat.body.length; i++) {
    if (cat.body[i] !== 0 || !ok(i)) continue;            // 0 = earth
    const d = dist(lat, lon, cat.lat[i], cat.lon[i]);
    if (d < bestD) { bestD = d; best = i; }
  }
  return { index: best, distanceKm: bestD };
}

export function findHomePatch(cat: PatchCatalog, lat: number, lon: number): HomePatch {
  const notes: string[] = [];
  const any = nearest(cat, lat, lon, () => true);
  if (any.distanceKm > 128) notes.push(`This point is in the water or far from any 1 km land patch (${Math.round(any.distanceKm)} km away).`);
  const lcName = (i: number) => (cat.lc[i] >= 0 ? cat.land_cover[cat.lc[i]] : 'unknown land cover');
  let pick = any;
  if (any.index >= 0 && !KEEP.has(cat.lc_code[any.index])) {
    const valid = nearest(cat, lat, lon, i => KEEP.has(cat.lc_code[i]));
    if (valid.index >= 0) {
      notes.push(`Your area is ${lcName(any.index)}, outside the promising analog zones; using the nearest promising patch instead.`);
      pick = valid;
    }
  }
  return { index: pick.index, lat: cat.lat[pick.index], lon: cat.lon[pick.index], region: cat.regions[cat.region[pick.index]],
    distanceKm: Math.round(pick.distanceKm), notes };
}

/** Typed-place fallback: Earth region names we already have (state/province, country), with a representative patch. */
export function earthRegions(cat: PatchCatalog) {
  const seen = new Map<string, { lat: number; lon: number }>();
  for (let i = 0; i < cat.body.length; i++) {
    if (cat.body[i] !== 0) continue;
    const name = cat.regions[cat.region[i]];
    if (name && name !== 'Earth' && !seen.has(name)) seen.set(name, { lat: cat.lat[i], lon: cat.lon[i] });
  }
  return [...seen.entries()].map(([name, p]) => ({ name, ...p })).sort((a, b) => a.name.localeCompare(b.name));
}
