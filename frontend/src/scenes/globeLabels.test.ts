import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { labelTier } from './labelTier.ts';

const labels = JSON.parse(readFileSync(new URL('./assets/globe-labels.json', import.meta.url), 'utf8')) as { body: string; name: string; tier: number; lat: number; lon: number }[];

test('labels: every body has a small top tier and valid coordinates', () => {
  for (const body of ['earth', 'moon', 'mars']) {
    const t1 = labels.filter(l => l.body === body && l.tier === 1);
    assert.ok(t1.length >= 5 && t1.length <= 12, `${body} tier 1: ${t1.length}`);
  }
  assert.ok(labels.every(l => Math.abs(l.lat) <= 90 && Math.abs(l.lon) <= 180));
  assert.ok(labels.some(l => l.body === 'mars' && l.name === 'Olympus Mons'));
  assert.ok(labels.some(l => l.body === 'moon' && l.name === 'Shackleton'));
});

test('zoom tiers: none in the whole-system view, tier 1 when approaching, then 2 and 3', () => {
  assert.equal(labelTier(20), 0);
  assert.equal(labelTier(8), 1);
  assert.equal(labelTier(4), 2);
  assert.equal(labelTier(1.6), 3);
});
