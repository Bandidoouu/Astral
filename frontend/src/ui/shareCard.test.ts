import assert from 'node:assert/strict';
import test from 'node:test';
import { celsius } from './shareCard.ts';

test('share card temperatures: kelvin to °C, missing stays "No data"', () => {
  assert.equal(celsius(300.15), '27 °C');
  assert.equal(celsius(null), 'No data');
  assert.equal(celsius(undefined), 'No data');
});
