import { bodies, validCoordinates } from './coordinates.ts';
import type { Analog, Attributes, SimilarRequest, SimilarResponse, Suitability } from './types.ts';

const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const score = (v: unknown) => finite(v) && v >= 0 && v <= 1;
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(s => typeof s === 'string');
const dimensions = ['terrain', 'operations', 'thermal', 'albedo', 'ice', 'soil', 'aridity'];
function attributes(v: unknown): v is Attributes {
  return record(v) && ['tmax_k', 'tmin_k', 'trange_k', 'albedo', 'ice_distance_km', 'ice_frac', 'soil_raw', 'soil_pct', 'precip_mm']
    .every(key => v[key] === null || (finite(v[key]) && v[key] >= 0));
}
function analog(v: unknown): v is Analog {
  if (!record(v) || !record(v.scores) || !strings(v.no_data)) return false;
  const scores = v.scores;
  return bodies.includes(v.body as Analog['body']) && finite(v.lat) && finite(v.lon) &&
    validCoordinates({ lat: v.lat, lon: v.lon }) && typeof v.patch_id === 'string' && typeof v.region === 'string' &&
    (v.scale_m === 60 || v.scale_m === 1000) && score(v.score) && attributes(v.attributes) &&
    strings(v.not_comparable) && dimensions.every(d => scores[d] === null || score(scores[d])) &&
    dimensions.every(d => (scores[d] === null) === (v.no_data as string[]).includes(d)) &&
    v.no_data.every(d => dimensions.includes(d)) &&
    (v.weights_used === undefined || (record(v.weights_used) && Object.entries(v.weights_used)
      .every(([key, value]) => dimensions.includes(key) && scores[key] !== null && score(value))));
}

export function parseSearchResponse(value: unknown, request: SimilarRequest): SimilarResponse {
  const fail = () => { throw new Error('The API response does not match the any-body ASTRAL contract.'); };
  if (!record(value) || !record(value.query) || !Array.isArray(value.results) || !strings(value.warnings)) return fail();
  const q = value.query;
  if (q.body !== request.body || q.lat !== request.lat || q.lon !== request.lon ||
    q.profile !== request.profile || q.scale_m !== request.scale_m || !strings(q.target_bodies) ||
    q.target_bodies.length !== request.target_bodies.length ||
    new Set(q.target_bodies).size !== q.target_bodies.length ||
    !q.target_bodies.every(t => request.target_bodies.includes(t as Analog['body'])) ||
    !['rrf', 'hybrid', 'net', 'baseline', 'random'].includes(String(q.method)) ||
    (q.attributes !== undefined && !attributes(q.attributes))) return fail();
  // A missing index may legitimately return only warnings: patches/attributes absent.
  if (q.patches !== undefined && (!record(q.patches) || !Object.entries(q.patches).every(([target, p]) =>
    request.target_bodies.includes(target as Analog['body']) && record(p) && typeof p.patch_id === 'string' &&
    p.scale_m === request.scale_m && finite(p.distance_km) && p.distance_km >= 0))) return fail();
  if (!value.results.every(r => analog(r) && request.target_bodies.includes(r.body) &&
    r.scale_m === request.scale_m && record(q.patches) && record(q.patches[r.body]))) return fail();
  const results = value.results as Analog[];
  if (new Set(results.map(r => r.patch_id)).size !== results.length ||
    request.target_bodies.some(t => results.filter(r => r.body === t).length > request.k)) return fail();
  return value as unknown as SimilarResponse;
}

export function parseSuitability(value: unknown): Suitability {
  const criteria = ['landing', 'rover', 'ice', 'temperature'];
  if (!record(value) || !record(value.weights) || !record(value.rules) ||
    !criteria.every(c => score((value.weights as Record<string, unknown>)[c])) ||
    ![...criteria, 'total'].every(c => typeof (value.rules as Record<string, unknown>)[c] === 'string') ||
    !strings(value.missing) || typeof value.caveat !== 'string' || typeof value.candidate_coordinates !== 'string' ||
    !record(value.grid) || !finite(value.grid.pixel_m) || value.grid.pixel_m <= 0 || typeof value.grid.crs !== 'string' ||
    !Array.isArray(value.candidates) || !value.candidates.every(c => record(c) && typeof c.name === 'string' &&
      typeof c.group === 'string' && finite(c.lat) && finite(c.lon) && validCoordinates({lat:c.lat, lon:c.lon}) &&
      (c.total_p90 === null || score(c.total_p90)) && (c.percentile_vs_random === null ||
        (finite(c.percentile_vs_random) && c.percentile_vs_random >= 0 && c.percentile_vs_random <= 100)))) {
    throw new Error('Invalid lunar suitability metadata.');
  }
  return value as unknown as Suitability;
}
