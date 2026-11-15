import assert from 'node:assert/strict';
import test from 'node:test';
import { MARKER_SCREEN_FACTOR, markerRadius } from './markerSize.ts';

test('markers keep a constant on-screen size while zooming and never exceed the old fixed size', () => {
  const R = 1;
  for (const d of [1.0, 1.5, 2.0]) assert.ok(Math.abs(markerRadius(d, R) / d - MARKER_SCREEN_FACTOR) < 1e-12);
  assert.equal(markerRadius(100, R), R * 0.035);
  assert.ok(markerRadius(0, R) > 0);
});

test('when zoomed in, a 128 km footprint on Earth is wider than the marker', () => {
  const earthGlobeRadius = 1, footprintRadius = 64 / 6371 * earthGlobeRadius;
  const closeDistance = earthGlobeRadius * 0.45;   // camera at minDistance 1.45 R, above the surface
  assert.ok(markerRadius(closeDistance, earthGlobeRadius) < footprintRadius);
});
