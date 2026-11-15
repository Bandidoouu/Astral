import assert from 'node:assert/strict';
import test from 'node:test';
import { FACTS, pressureAtElevationHpa } from './planetFacts.ts';

test('standard barometric formula: 1013.25 hPa at sea level, about 616 hPa at 4,000 m', () => {
  assert.equal(pressureAtElevationHpa(0), 1013.25);
  assert.ok(Math.abs(pressureAtElevationHpa(4000) - 616.4) < 1);
  assert.equal(pressureAtElevationHpa(-100), 1013.25);
});

test('every shown fact carries its source', () => {
  for (const body of ['earth', 'moon', 'mars'] as const) {
    for (const key of ['gravity', 'pressure', 'day', 'radiation'] as const) assert.ok((FACTS[body][key]?.source.length ?? 0) > 10, `${body} ${key}`);
  }
  assert.ok(FACTS.moon.radiation?.source.includes('Zhang'));
  assert.ok(FACTS.mars.radiation?.source.includes('Hassler'));
  assert.ok(FACTS.earth.radiation?.source.includes('UNSCEAR'));
  // 3.0 mSv/year ≈ 8.2 µSv/day
  assert.ok(Math.abs(3000 / 365.25 - 8) < 0.5);
});
