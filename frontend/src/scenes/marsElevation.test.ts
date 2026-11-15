import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { decodeMola, MARS_REFERENCE_RADIUS_KM } from './marsElevation.ts';
import { sampleHeight } from './lunarElevation.ts';

const file = readFileSync(new URL('./assets/mars-height.img', import.meta.url));
const buffer = file.buffer.slice(file.byteOffset, file.byteOffset + file.byteLength) as ArrayBuffer;

test('official MOLA preserves meters-to-kilometers conversion and signed heights', () => {
  const grid = decodeMola(buffer);
  assert.equal(grid.width, 1440);
  assert.equal(grid.height, 720);
  let min = Infinity, max = -Infinity;
  for (const value of grid.values) { min = Math.min(min, value); max = Math.max(max, value); }
  assert.ok(min < -7 && min > -10, `minimum ${min} km`);
  assert.ok(max > 20 && max < 23, `maximum ${max} km`);
  assert.ok(1 + max / MARS_REFERENCE_RADIUS_KM < 1.01);
});

test('MOLA is aligned with east-positive coordinates: Olympus Mons high, Hellas low', () => {
  const grid = decodeMola(buffer);
  const at = (lat: number, lon: number) => sampleHeight(grid, (lon + 180) / 360, (lat + 90) / 180);
  assert.ok(at(18.65, -133.8) > 15, `Olympus Mons: ${at(18.65, -133.8)} km`);
  assert.ok(at(-42.4, 70.5) < -5, `Hellas: ${at(-42.4, 70.5)} km`);
  assert.equal(at(0, -180), at(0, 180));
});

test('MOLA rejects incomplete files and invalid sentinel heights', () => {
  assert.throws(() => decodeMola(buffer.slice(0, 128)));
  const invalid = buffer.slice(0);
  new DataView(invalid).setInt16(0, -32768, false);
  assert.throws(() => decodeMola(invalid));
});
