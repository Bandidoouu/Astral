import type { Analog, Attributes, Body, Dimension, Precomputed, Profile, QueryPatch, SearchQuery, SearchResult } from '../api/types.ts';

/** Offline 1 km search over EVERY index patch (frontend/tools/precompute_offline_grid.py).
 * The ranking (RRF terrain similarity) does not depend on the profile, so the browser only
 * recomputes the profile score from the seven stored dimension scores, exactly like
 * ml/search.py: weighted mean over the dimensions with data, weights renormalized. */

export interface OfflineCatalog {
  format: string; chunk: number; precomputed: Precomputed; bodies: Body[]; dims: Dimension[]; attr_cols: (keyof Attributes | 'h2o_wt_pct')[];
  regions: string[]; land_cover: string[];
  patch_id: string[]; body: number[]; lat: number[]; lon: number[]; region: number[]; lc: number[]; lc_code: number[];
  attrs: (number | null)[][];
  /** Pixel size per patch (gravity-scaled catalogs); absent = 1000 m everywhere. */
  scale_m?: number[];
}
/** Result chunks keyed by `${body}/${chunk}` (results_{body}_{chunk}.bin). */
export type OfflineBlocks = Partial<Record<string, Uint16Array>>;

const K = 10, NULL = 65535, ENTRY = 8;
const BODIES: Body[] = ['earth', 'moon', 'mars'];
// Same radii as ml/search.py RADIUS_KM (used for the nearest patch and its distance).
const RADIUS_KM: Record<Body, number> = { earth: 6371.0, moon: 1737.4, mars: 3389.5 };
const KEEP = new Set([7, 10, 15, 16]);
// Same weights as ml/search.py PROFILES (terrain never above 0.3).
export const PROFILES: Record<Profile, Record<Dimension, number>> = {
  general: { terrain: 1 / 7, operations: 1 / 7, thermal: 1 / 7, albedo: 1 / 7, ice: 1 / 7, soil: 1 / 7, aridity: 1 / 7 },
  rover: { terrain: 0.30, operations: 0.30, thermal: 0.05, albedo: 0.05, ice: 0.05, soil: 0.15, aridity: 0.10 },
  isru: { terrain: 0.10, operations: 0.10, thermal: 0.10, albedo: 0.15, ice: 0.35, soil: 0.15, aridity: 0.05 },
  habitat: { terrain: 0.15, operations: 0.25, thermal: 0.25, albedo: 0.05, ice: 0.15, soil: 0.10, aridity: 0.05 },
  eva: { terrain: 0.30, operations: 0.20, thermal: 0.05, albedo: 0.15, ice: 0.05, soil: 0.20, aridity: 0.05 },
  astrobiology: { terrain: 0.10, operations: 0.00, thermal: 0.15, albedo: 0.10, ice: 0.30, soil: 0.10, aridity: 0.25 },
};
const NOT_COMPARABLE: Record<Body, string[]> = {
  moon: ['dust_and_wind', 'subsurface', 'gravity', 'vacuum', 'radiation'],
  mars: ['dust_and_wind', 'subsurface', 'gravity', 'atmosphere', 'radiation'],
  earth: ['dust_and_wind', 'subsurface', 'gravity', 'atmosphere', 'radiation'],
};

const round = (v: number, n: number) => Math.round(v * 10 ** n) / 10 ** n;
const windowKm = (cat: OfflineCatalog, i: number) => round(128 * (cat.scale_m?.[i] ?? 1000) / 1000, 1);
function distanceKm(body: Body, lat1: number, lon1: number, lat2: number, lon2: number) {
  const r = Math.PI / 180;
  const c = Math.sin(lat1 * r) * Math.sin(lat2 * r) + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.cos((lon2 - lon1) * r);
  return RADIUS_KM[body] * Math.acos(Math.min(1, Math.max(-1, c)));
}

export function profileScore(scores: Record<Dimension, number | null>, profile: Profile) {
  const weights = PROFILES[profile];
  const avail = (Object.keys(weights) as Dimension[]).filter(d => scores[d] !== null && weights[d] > 0);
  const tot = avail.reduce((s, d) => s + weights[d], 0);
  const score = tot ? round(avail.reduce((s, d) => s + scores[d]! * weights[d], 0) / tot, 4) : 0;
  const used: Partial<Record<Dimension, number>> = {};
  for (const d of avail) used[d] = round(weights[d] / tot, 3);
  return { score, weights_used: used };
}

function attributesOf(cat: OfflineCatalog, i: number): Attributes {
  const out: Record<string, number | null> = {};
  cat.attr_cols.forEach((key, j) => { out[key] = cat.attrs[i][j]; });
  return out as unknown as Attributes;
}

/** Index of each patch within its body (the row of its block in results_{body}.bin). */
const positions = new WeakMap<OfflineCatalog, Int32Array>();
function rowOf(cat: OfflineCatalog, i: number) {
  let pos = positions.get(cat);
  if (!pos) {
    pos = new Int32Array(cat.patch_id.length);
    const seen = [0, 0, 0];
    cat.body.forEach((b, j) => { pos![j] = seen[b]++; });
    positions.set(cat, pos);
  }
  return pos[i];
}

export function nearestPatch(cat: OfflineCatalog, body: Body, lat: number, lon: number) {
  const b = BODIES.indexOf(body);
  let best = -1, bestD = Infinity;
  for (let i = 0; i < cat.body.length; i++) {
    if (cat.body[i] !== b) continue;
    const d = distanceKm(body, lat, lon, cat.lat[i], cat.lon[i]);
    if (d < bestD) { bestD = d; best = i; }
  }
  return { index: best, distance: bestD };
}

/** Which chunk file holds the results of the patch nearest to the clicked point. */
export function originChunk(cat: OfflineCatalog, body: Body, lat: number, lon: number) {
  const origin = nearestPatch(cat, body, lat, lon);
  const chunk = Math.floor(rowOf(cat, origin.index) / cat.chunk);
  return { ...origin, chunk, key: `${body}/${chunk}`, file: `results_${body}_${String(chunk).padStart(3, '0')}.bin` };
}

export function gridSearch(query: SearchQuery, cat: OfflineCatalog, blocks: OfflineBlocks): SearchResult {
  const { body, lat, lon, profile, target_bodies } = query;
  const origin = originChunk(cat, body, lat, lon);
  const block = blocks[origin.key];
  if (origin.index < 0 || !block) throw new Error(`No offline 1 km data for ${body}.`);
  const warnings: string[] = [];
  const order = BODIES.filter(t => t !== body);
  const base = (rowOf(cat, origin.index) % cat.chunk) * order.length * K * ENTRY;
  let landCover: { code: number; name: string; promising: boolean } | undefined;
  if (body === 'earth') {
    // Offline approximation: land cover at the nearest patch center (the API uses the clicked point).
    const code = cat.lc_code[origin.index], name = cat.lc[origin.index] >= 0 ? cat.land_cover[cat.lc[origin.index]] : 'unknown';
    landCover = { code, name, promising: KEEP.has(code) };
    if (!landCover.promising) warnings.push(`earth: the nearest 1 km patch center is ${name} (MODIS land cover class ${code}), outside the promising analog zones; search continues (offline approximation of the clicked point)`);
  }
  const patches: Partial<Record<Body, QueryPatch>> = {};
  const results: Analog[] = [];
  for (const target of target_bodies) {
    if (origin.distance > windowKm(cat, origin.index)) warnings.push(`${body}: the point is ${origin.distance.toFixed(0)} km from the nearest patch at 1000 m (outside coverage at this scale)`);
    patches[target] = { patch_id: cat.patch_id[origin.index], scale_m: 1000, distance_km: round(origin.distance, 2), window_km: windowKm(cat, origin.index) };
    const start = base + order.indexOf(target) * K * ENTRY;
    for (let k = 0; k < Math.min(K, query.k); k++) {
      const o = start + k * ENTRY;
      const j = block[o];
      if (j === NULL) break;
      const scores = {} as Record<Dimension, number | null>;
      cat.dims.forEach((d, n) => { const v = block[o + 1 + n]; scores[d] = v === NULL ? null : v / 10000; });
      const { score, weights_used } = profileScore(scores, profile);
      results.push({
        patch_id: cat.patch_id[j], body: target, lat: cat.lat[j], lon: cat.lon[j], region: cat.regions[cat.region[j]],
        scale_m: 1000, score, scores, no_data: cat.dims.filter(d => scores[d] === null), weights_used,
        attributes: attributesOf(cat, j), not_comparable: NOT_COMPARABLE[body === 'earth' ? target : body],
        land_cover: target === 'earth' && cat.lc[j] >= 0 ? cat.land_cover[cat.lc[j]] : null, window_km: windowKm(cat, j),
      });
    }
  }
  return {
    query: { body, lat, lon, profile, scale_m: 1000, target_bodies: [...target_bodies], method: 'rrf', patches,
      attributes: attributesOf(cat, origin.index), ...(landCover ? { land_cover: landCover } : {}) } as SearchResult['query'],
    results,
    warnings: ['Offline mode: precomputed results of the ASTRAL model v2 for the nearest 1 km patch; the profile score is recomputed in your browser from the stored dimension scores.', ...warnings],
    demo: true,
    precomputed: { ...cat.precomputed, site: `${body} patch ${cat.patch_id[origin.index]}` },
  };
}
