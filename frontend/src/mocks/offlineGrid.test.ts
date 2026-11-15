import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import test from 'node:test';
import { gridSearch, profileScore, PROFILES } from './offlineGrid.ts';
import type { OfflineBlocks, OfflineCatalog } from './offlineGrid.ts';
import { parseSearchResponse } from '../api/validation.ts';
import type { Profile, SearchQuery } from '../api/types.ts';

const dir = new URL('../../public/data/offline1km/', import.meta.url);
const catalog = JSON.parse(readFileSync(new URL('catalog.json', dir), 'utf8')) as OfflineCatalog;
const blocks: OfflineBlocks = {};
for (const f of readdirSync(dir)) {
  const m = /^results_(\w+)_(\d+)\.bin$/.exec(f);
  if (!m) continue;
  const buf = readFileSync(new URL(f, dir));
  blocks[`${m[1]}/${Number(m[2])}`] = new Uint16Array(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
}
// Real API responses saved for the curated sites (same model, general profile, k = 10).
const curated = JSON.parse(readFileSync(new URL('./precomputed-results.json', import.meta.url), 'utf8'));

test('offline 1 km grid reproduces the real API responses for every curated site', () => {
  for (const site of curated.sites) {
    const api = site.responses['1000'];
    if (!api) continue;
    const query: SearchQuery = { body: site.body, lat: site.lat, lon: site.lon, profile: 'general', k: 10,
      scale_m: 1000, target_bodies: api.query.target_bodies };
    const off = gridSearch(query, catalog, blocks);
    parseSearchResponse(off, query);
    assert.deepEqual(off.results.map(r => r.patch_id), api.results.map((r: { patch_id: string }) => r.patch_id), site.name);
    off.results.forEach((r, i) => {
      assert.deepEqual(r.scores, api.results[i].scores, `${site.name} #${i + 1} scores`);
      // Floating-point sums can land on the other side of a 4th-decimal rounding tie (±0.0001).
      assert.ok(Math.abs(r.score - api.results[i].score) <= 1.0001e-4, `${site.name} #${i + 1} total`);
      assert.equal(Math.round(r.score * 100), Math.round(api.results[i].score * 100), `${site.name} #${i + 1} shown %`);
      assert.equal(r.region, api.results[i].region);
    });
  }
});

test('video query: Olympus Mons offline keeps Hawaii in the top 5', () => {
  const r = gridSearch({ body: 'mars', lat: 18.65, lon: -133.8, profile: 'general', k: 5, scale_m: 1000, target_bodies: ['earth'] }, catalog, blocks);
  assert.ok(r.results.slice(0, 5).some(x => x.region === 'Hawaii, USA'));
});

test('profiles change the score but not the terrain order', () => {
  const q: SearchQuery = { body: 'moon', lat: 14, lon: -56, profile: 'general', k: 10, scale_m: 1000, target_bodies: ['earth'] };
  const general = gridSearch(q, catalog, blocks);
  for (const p of Object.keys(PROFILES) as Profile[]) {
    const r = gridSearch({ ...q, profile: p }, catalog, blocks);
    assert.deepEqual(r.results.map(x => x.patch_id), general.results.map(x => x.patch_id));
    r.results.forEach(x => assert.equal(x.score, profileScore(x.scores, p).score));
  }
});
