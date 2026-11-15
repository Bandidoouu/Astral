import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { buildShareUrl, parseShareParams } from './shareLink.ts';
import { earthRegions, findHomePatch } from './homePatch.ts';
import type { PatchCatalog } from './homePatch.ts';

const cat = JSON.parse(readFileSync(new URL('../../public/data/offline1km/catalog.json', import.meta.url), 'utf8')) as PatchCatalog;

test('share links round-trip and reject invalid input', () => {
  const url = buildShareUrl('https://bandidoouu.github.io/Astral/', { body: 'mars', lat: 18.65, lon: -133.8, scale: 1000, gravity: true });
  assert.deepEqual(parseShareParams(new URL(url).search), { body: 'mars', lat: 18.65, lon: -133.8, scale: 1000, gravity: true });
  assert.equal(parseShareParams('?body=pluto&lat=0&lon=0'), null);
  assert.equal(parseShareParams('?body=moon&lat=120&lon=0'), null);
  assert.equal(parseShareParams('?lat=1&lon=2'), null);
  assert.equal(parseShareParams('?body=moon&lat=-87.3&lon=77&scale=60&gravity=1')?.gravity, false);
});

test('home patch: Monterrey and Mexico City map to nearby Earth patches; the open sea says so', () => {
  const mty = findHomePatch(cat, 25.6866, -100.3161);
  assert.ok(mty.index >= 0 && mty.distanceKm < 400, `Monterrey ${mty.distanceKm} km`);
  const cdmx = findHomePatch(cat, 19.4326, -99.1332);
  assert.ok(cdmx.index >= 0 && cdmx.distanceKm < 400);
  const sea = findHomePatch(cat, 20.0, -140.0);
  assert.ok(sea.notes.some(n => n.includes('water')));
  assert.ok(sea.index >= 0);
});

test('typed-place fallback lists region names we already have', () => {
  const regions = earthRegions(cat);
  assert.ok(regions.length > 100);
  assert.ok(regions.some(r => r.name.includes('Mexico')));
});
