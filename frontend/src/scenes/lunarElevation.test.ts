import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { decodeLolaTiff, sampleHeight, MOON_RADIUS_KM } from './lunarElevation.ts';

const original = readFileSync(new URL('./assets/moon-height.tif', import.meta.url));
const buffer = original.buffer.slice(original.byteOffset, original.byteOffset + original.byteLength) as ArrayBuffer;

test('official LOLA float raster preserves dimensions, negative elevations and kilometer units', () => {
  const grid = decodeLolaTiff(buffer);
  assert.equal(grid.width, 1440);
  assert.equal(grid.height, 720);
  assert.equal(grid.values.length, 1440 * 720);
  let min = Infinity, max = -Infinity;
  for (const value of grid.values) { min = Math.min(min, value); max = Math.max(max, value); }
  assert.ok(min < -5 && min > -15, `minimum ${min} km`);
  assert.ok(max > 5 && max < 15, `maximum ${max} km`);
  assert.ok(1 + min / MOON_RADIUS_KM > 0.99);
  assert.ok(1 + max / MOON_RADIUS_KM < 1.01);
});

test('height sampling respects north, south, pixel centers and wrapped longitude', () => {
  const grid = { width: 4, height: 2, values: new Float32Array([0, 2, 4, 6, 10, 12, 14, 16]) };
  assert.equal(sampleHeight(grid, 0.125, 1), 0);
  assert.equal(sampleHeight(grid, 0.125, 0), 10);
  assert.equal(sampleHeight(grid, 0.125, 0.5), 5);
  assert.equal(sampleHeight(grid, 0, 1), 3);
  assert.equal(sampleHeight(grid, 1, 1), 3);
  assert.equal(sampleHeight(grid, -0.25, 0.5), sampleHeight(grid, 0.75, 0.5));
});

test('truncated rasters and non-TIFF data are rejected instead of producing terrain', () => {
  assert.throws(() => decodeLolaTiff(buffer.slice(0, 100)));
  assert.throws(() => decodeLolaTiff(new ArrayBuffer(32)));
});
