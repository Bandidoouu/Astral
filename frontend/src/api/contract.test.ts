import { test } from 'node:test';
import assert from 'node:assert/strict';
import fixture from '../mocks/similar-response.any-body.json' with { type: 'json' };
import { demoSearch } from '../mocks/search.ts';
import { otherBodies, toApiRequest } from './coordinates.ts';
import { parseSearchResponse, parseSuitability } from './validation.ts';
import type { Body, SearchQuery } from './types.ts';

const query: SearchQuery = {body:'moon', lat:-89.5, lon:130, profile:'general', k:10, scale_m:1000, target_bodies:['earth','mars']};
test('accept the current main fixture, including seven dimensions and omitted weights', () => {
  const result = parseSearchResponse(fixture, query);
  assert.equal(result.results[0].scores.thermal, null);
  assert.equal(result.results[0].weights_used, undefined);
  assert.equal(result.query.profile, 'general');
  assert.deepEqual(Object.keys(result.results[0].scores).sort(), ['albedo', 'aridity', 'ice', 'operations', 'soil', 'terrain', 'thermal']);
  assert.deepEqual(result.results.map(r => r.body), ['earth','earth','mars']);
  assert.equal(result.query.patches?.mars?.distance_km, 21.4);
});
test('accept warning-only and partial responses without requiring unavailable patches', () => {
  const empty = {query:{...query, method:'rrf'}, results:[], warnings:['Index unavailable']};
  assert.deepEqual(parseSearchResponse(empty, query).warnings, ['Index unavailable']);
  const partial = structuredClone(fixture);
  partial.results = partial.results.filter(r => r.body === 'earth');
  Reflect.deleteProperty(partial.query.patches, 'mars');
  assert.equal(parseSearchResponse(partial, query).results.length, 2);
});
test('reject mismatched scale, unrequested bodies, missing dimension fields and invalid measurements', () => {
  for (const mutate of [
    (r: typeof fixture) => {r.results[0].scale_m = 500;},
    (r: typeof fixture) => {r.results[0].body = 'moon';},
    (r: typeof fixture) => {Reflect.deleteProperty(r.results[0].scores, 'albedo');},
    (r: typeof fixture) => {Reflect.deleteProperty(r.results[0].scores, 'ice');},
    (r: typeof fixture) => {Reflect.deleteProperty(r.results[0].scores, 'soil');},
    (r: typeof fixture) => {Reflect.deleteProperty(r.results[0].scores, 'aridity');},
    (r: typeof fixture) => {r.results[0].scores.terrain = 1.1;},
    (r: typeof fixture) => {r.query.lat = 25;},
    (r: typeof fixture) => {r.results[0].no_data = [];},
    (r: typeof fixture) => {r.query.attributes.ice_distance_km = -3;},
  ]) {
    const malformed = structuredClone(fixture); mutate(malformed);
    assert.throws(() => parseSearchResponse(malformed, query), /contract/);
  }
});
test('offline demo serves precomputed v2 results that satisfy the contract', () => {
  for (const body of ['earth','moon','mars'] as Body[]) {
    const request = {...query, body, target_bodies:otherBodies(body), k:1};
    const data = demoSearch(request);
    assert.ok(data.results.length >= 1 && data.results.length <= 2);
    assert.ok(data.results.every(r => r.body !== body));
    assert.equal(data.precomputed?.model, 'v2');
    parseSearchResponse(data, request);
  }
  assert.ok(demoSearch({...query, target_bodies:['mars']}).results.every(r => r.body === 'mars'));
  const detail = demoSearch({...query, scale_m:60, target_bodies:['earth']});
  assert.ok(detail.results.length > 0 && detail.results.every(r => r.scale_m === 60));
  parseSearchResponse(detail, {...query, scale_m:60, target_bodies:['earth']});
});
test('suitability metadata keeps missing candidate data null and rejects invalid weights', () => {
  const data = {weights:{landing:0.3,rover:0.2,ice:0.3,temperature:0.2},
    rules:{landing:'slope',rover:'slope',ice:'distance',temperature:'temperature',total:'weighted mean'},
    missing:['illumination','Earth visibility'],caveat:'Suggestion only',grid:{crs:'Polar',pixel_m:480},
    candidate_coordinates:'Approximate centers',candidates:[{name:'Example',lat:-85,lon:30,group:'Test',total_p90:null,percentile_vs_random:null}]};
  assert.equal(parseSuitability(data).candidates[0].total_p90, null);
  assert.throws(() => parseSuitability({...data,weights:{...data.weights,ice:NaN}}), /metadata/);
});
test('Mars suitability uses its own criteria and the bundled ML exports parse', async () => {
  const mars = (await import('../../../contracts/suitability_mars.json', { with: { type: 'json' } })).default;
  const moon = (await import('../../../contracts/suitability_moon_south.json', { with: { type: 'json' } })).default;
  assert.equal(parseSuitability(mars, 'mars').candidates.length > 0, true);
  assert.equal(parseSuitability(moon, 'moon').candidates.length > 0, true);
  assert.throws(() => parseSuitability(mars, 'moon'), /lunar/);
});
test('scale_mode is sent only at the global scale and demo mode serves the gravity-scaled results', () => {
  const global = toApiRequest({...query, body:'mars', lat:18.38, lon:77.58, target_bodies:['earth'], scale_mode:'gravity_scaled'});
  assert.equal(global.scale_mode, 'gravity_scaled');
  const detail = toApiRequest({...query, scale_m:60, target_bodies:['earth'], scale_mode:'gravity_scaled'});
  assert.equal(detail.scale_mode, 'same_size');
  const same = demoSearch({...query, body:'mars', lat:18.38, lon:77.58, target_bodies:['earth'], k:3});
  const grav = demoSearch({...query, body:'mars', lat:18.38, lon:77.58, target_bodies:['earth'], k:3, scale_mode:'gravity_scaled'});
  assert.ok((grav.query.patches?.earth?.window_km ?? 0) > (same.query.patches?.earth?.window_km ?? 0));
});
