import { test } from 'node:test';
import assert from 'node:assert/strict';
import { detailAvailable, fromVector, inDetailCoverage, otherBodies, toApiRequest, toVector, validCoordinates } from './coordinates.ts';
import type { Body, SearchQuery } from './types.ts';

test('globe clicks preserve latitude and east-positive longitude across hemispheres', () => {
  for (const [lat, lon] of [[-89.5, 130], [31.77, -113.5], [18.38, 77.58], [0, 180], [0, -180], [90, 0], [-90, 0]]) {
    const actual = fromVector(...toVector(lat, lon, 1.25));
    assert.ok(Math.abs(actual.lat - lat) < 1e-6);
    assert.ok(Math.abs(actual.lon - lon) < 1e-6);
  }
});
test('invalid coordinates are rejected instead of wrapping or becoming NaN', () => {
  for (const [lat, lon] of [[91, 0], [-91, 0], [0, 181], [0, -181], [NaN, 0], [0, Infinity]]) {
    assert.equal(validCoordinates({ lat, lon }), false);
  }
  assert.throws(() => fromVector(0, 0, 0));
});
const query: SearchQuery = { body: 'moon', lat: -89.5, lon: 130, profile: 'rover', k: 5, scale_m: 1000, target_bodies: ['earth', 'mars'] };
test('all three origins can search the other two globally, with explicit scale and destinations', () => {
  for (const body of ['earth', 'moon', 'mars'] as Body[]) {
    const request = toApiRequest({ ...query, body, target_bodies: otherBodies(body) });
    assert.equal(request.scale_m, 1000);
    assert.equal(request.target_bodies.length, 2);
    assert.ok(!request.target_bodies.includes(body));
    assert.equal('method' in request, false, 'ranking defaults belong to the backend');
  }
});
test('60 m is only valid in the specified coverage and between Earth and Moon', () => {
  assert.equal(inDetailCoverage({body:'moon', lat:-80, lon:0}), false);
  assert.equal(inDetailCoverage({body:'moon', lat:-80.001, lon:180}), true);
  assert.equal(inDetailCoverage({body:'earth', lat:14, lon:-118}), true);
  assert.equal(inDetailCoverage({body:'earth', lat:33, lon:-86}), true);
  assert.equal(inDetailCoverage({body:'earth', lat:33.01, lon:-86}), false);
  assert.equal(detailAvailable(query, ['earth', 'mars']), false);
  assert.equal(detailAvailable(query, ['earth']), true);
  assert.equal(toApiRequest({...query, scale_m:60, target_bodies:['earth']}).scale_m, 60);
  assert.throws(() => toApiRequest({...query, scale_m:60}), /Detail/);
  assert.throws(() => toApiRequest({...query, scale_m:60, lat:14, target_bodies:['earth']}), /Detail/);
});
test('reject invalid destinations, missing destinations, scales and profiles', () => {
  assert.throws(() => toApiRequest({...query, target_bodies:[]}), /destination/);
  assert.throws(() => toApiRequest({...query, target_bodies:['moon']}), /destination/);
  assert.throws(() => toApiRequest({...query, target_bodies:['earth','earth']}), /destination/);
  assert.throws(() => toApiRequest({...query, scale_m:500 as 1000}), /scale/);
  assert.throws(() => toApiRequest({...query, profile:'astrobiology'}), /Mars only/);
  assert.throws(() => toApiRequest({...query, lat:91}), /latitude/);
});
