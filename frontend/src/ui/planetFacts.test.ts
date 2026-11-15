import assert from 'node:assert/strict';
import test from 'node:test';
import { FACTS, pressureAtElevationHpa } from './planetFacts.ts';

test('standard barometric formula: 1013.25 hPa at sea level, about 616 hPa at 4,000 m', () => {
  assert.equal(pressureAtElevationHpa(0), 1013.25);
  assert.ok(Math.abs(pressureAtElevationHpa(4000) - 616.4) < 1);
  assert.equal(pressureAtElevationHpa(-100), 1013.25);
});

test('every shown fact carries a source; unsourced radiation stays null (never invented)', () => {
  for (const body of ['earth', 'moon', 'mars'] as const) {
    for (const key of ['gravity', 'pressure', 'day'] as const) assert.ok(FACTS[body][key].source.length > 10);
  }
  assert.ok(FACTS.moon.radiation?.source.includes('Zhang'));
  assert.equal(FACTS.mars.radiation, null);
  assert.equal(FACTS.earth.radiation, null);
});
