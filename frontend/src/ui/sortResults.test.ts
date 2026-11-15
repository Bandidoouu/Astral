import assert from 'node:assert/strict';
import test from 'node:test';
import { sortResults } from './sortResults.ts';
import { demoSearch } from '../mocks/search.ts';
import type { SearchQuery } from '../api/types.ts';

const faustini: SearchQuery = { body: 'moon', lat: -87.3, lon: 77, profile: 'general', k: 5, scale_m: 60, target_bodies: ['earth'] };

test('Terrain keeps the search order: Faustini 60 m still has El Pinacate (Sonora) 3rd', () => {
  const r = demoSearch(faustini).results;
  const terrain = sortResults(r, 'terrain');
  assert.equal(terrain, r);
  assert.equal(terrain[2].region, 'Sonora, Mexico');
});

test('Overall re-sorts the same results by profile score, per destination body', () => {
  const r = demoSearch({ ...faustini, scale_m: 1000, target_bodies: ['earth', 'mars'] }).results;
  const overall = sortResults(r, 'overall');
  assert.deepEqual(new Set(overall.map(x => x.patch_id)), new Set(r.map(x => x.patch_id)));
  for (const body of ['earth', 'mars']) {
    const s = overall.filter(x => x.body === body).map(x => x.score);
    assert.deepEqual(s, [...s].sort((a, b) => b - a));
  }
  assert.deepEqual(overall.map(x => x.body), r.map(x => x.body).sort((a, b) => (a === 'earth' ? -1 : 1) - (b === 'earth' ? -1 : 1)));
});

test('changing the profile changes the Overall order (scores recomputed from stored dimensions)', () => {
  const general = sortResults(demoSearch({ ...faustini, k: 10 }).results, 'overall').map(x => x.patch_id);
  const changed = ['rover', 'isru', 'habitat', 'eva'].some(p =>
    JSON.stringify(sortResults(demoSearch({ ...faustini, k: 10, profile: p as SearchQuery['profile'] }).results, 'overall').map(x => x.patch_id)) !== JSON.stringify(general));
  assert.ok(changed);
});
