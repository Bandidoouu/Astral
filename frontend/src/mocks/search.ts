import precomputedFile from './precomputed-results.json' with { type: 'json' };
import galaxyFixture from '../../../contracts/galaxy.example.json' with { type: 'json' };
import type { Analog, Body, GalaxyPoint, Precomputed, SearchQuery, SearchResult, SimilarResponse } from '../api/types.ts';
import { toApiRequest } from '../api/coordinates.ts';

export const demoGalaxy = galaxyFixture as GalaxyPoint[];

// Real outputs of the ASTRAL search (model v2, RRF, general profile, k = 10), precomputed
// with `python -m ml.demo_results` for curated sites: Artemis candidates, Mars missions,
// Earth analog stations. Scores are never recalculated in the browser.
export interface CuratedSite {
  id: string; name: string; group: string; body: Body; lat: number; lon: number;
  responses: Record<string, SimilarResponse & { precomputed: Precomputed }>;
}
const precomputed = precomputedFile as unknown as { precomputed: Precomputed; sites: CuratedSite[] };
export const curatedSites: CuratedSite[] = precomputed.sites;

function angularDistanceDeg(aLat: number, aLon: number, bLat: number, bLon: number) {
  const r = Math.PI / 180;
  const c = Math.sin(aLat * r) * Math.sin(bLat * r) + Math.cos(aLat * r) * Math.cos(bLat * r) * Math.cos((bLon - aLon) * r);
  return Math.acos(Math.min(1, Math.max(-1, c))) / r;
}

export function nearestCuratedSite(body: Body, lat: number, lon: number, key: string) {
  return curatedSites.filter(s => s.body === body && s.responses[key])
    .map(site => ({ site, distance: angularDistanceDeg(lat, lon, site.lat, site.lon) }))
    .sort((a, b) => a.distance - b.distance)[0];
}

export function demoSearch(query: SearchQuery): SearchResult {
  toApiRequest(query);
  const key = query.scale_m === 1000 && query.scale_mode === 'gravity_scaled' ? '1000_gravity' : String(query.scale_m);
  const hit = nearestCuratedSite(query.body, query.lat, query.lon, key);
  if (!hit) {
    return {
      query: { ...query, method: 'rrf' }, results: [], demo: true,
      warnings: [query.scale_m === 60
        ? 'Offline mode: precomputed 60 m results exist only for the lunar south pole candidates and El Pinacate. Switch to Global (1 km).'
        : 'Offline mode: no precomputed results for this body.'],
    };
  }
  const response = hit.site.responses[key];
  const results: Analog[] = query.target_bodies.flatMap(target =>
    response.results.filter(r => r.body === target).slice(0, query.k));
  const patches: SimilarResponse['query']['patches'] = {};
  for (const target of query.target_bodies) {
    const patch = response.query.patches?.[target];
    if (patch) patches[target] = patch;
  }
  const { body, lat, lon, profile, scale_m, target_bodies } = query;
  return {
    query: { body, lat, lon, profile, scale_m, target_bodies, method: response.query.method, patches,
      attributes: response.query.attributes },
    results,
    warnings: [`Offline mode: precomputed results of the ASTRAL model v2 for the nearest curated site, ${hit.site.name} (${hit.distance.toFixed(1)}° away). Ranking uses the general profile.`,
      ...response.warnings],
    demo: true,
    precomputed: { ...response.precomputed, site: hit.site.name },
  };
}
