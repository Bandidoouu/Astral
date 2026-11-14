import fixture from './similar-response.any-body.json' with { type: 'json' };
import galaxyFixture from '../../../contracts/galaxy.example.json' with { type: 'json' };
import type { Analog, Attributes, Body, GalaxyPoint, QueryPatch, SearchQuery, SearchResult } from '../api/types.ts';
import { toApiRequest } from '../api/coordinates.ts';

export const demoGalaxy = galaxyFixture as GalaxyPoint[];
const noAttributes: Attributes = { tmax_k: null, tmin_k: null, trange_k: null, albedo: null, ice_distance_km: null, ice_frac: null, soil_raw: null, soil_pct: null, precip_mm: null };
// Exact team fixture from main @ ccc87b9, plus one explicit Moon UI example.
// Scores, weights and measurements are never recalculated in the browser.
const examples: Record<Body, Analog[]> = {
  earth: fixture.results.filter(r => r.body === 'earth') as Analog[],
  mars: fixture.results.filter(r => r.body === 'mars') as Analog[],
  moon: [{
    patch_id: 'demo-moon-1000', body: 'moon', lat: -89.5, lon: 130, scale_m: 1000,
    region: 'Lunar south pole · example', score: 0.82,
    scores: { terrain: 0.86, operations: 0.79, thermal: null, albedo: null, ice: null, soil: null, aridity: null },
    no_data: ['thermal', 'albedo', 'ice', 'soil', 'aridity'], attributes: { ...noAttributes },
    not_comparable: ['dust_and_wind', 'subsurface', 'gravity', 'vacuum', 'radiation'],
  }],
};
export function demoSearch(query: SearchQuery): SearchResult {
  toApiRequest(query);
  if (query.scale_m === 60) {
    return {
      query: { ...query, method: 'rrf' }, results: [], demo: true,
      warnings: ['No 60 m example index is bundled. Switch to Global (1 km) for the illustrative results.'],
    };
  }
  const results = query.target_bodies.flatMap(target => examples[target].slice(0, query.k))
    .map(result => ({ ...result, scores: { ...result.scores }, attributes: { ...result.attributes },
      not_comparable: ['dust_and_wind', 'subsurface', 'gravity', query.body === 'moon' || result.body === 'moon' ? 'vacuum' : 'atmosphere', 'radiation'],
    }));
  const patches: Partial<Record<Body, QueryPatch>> = {};
  for (const target of query.target_bodies) {
    patches[target] = query.body === 'moon'
      ? { ...fixture.query.patches.earth, scale_m: 1000 }
      : { patch_id: `demo-${query.body}-1000`, scale_m: 1000, distance_km: 0 };
  }
  return {
    query: { ...query, method: 'hybrid', patches, attributes: query.body === 'moon' ? { ...fixture.query.attributes } : { ...noAttributes } },
    results, warnings: [], demo: true,
  };
}
