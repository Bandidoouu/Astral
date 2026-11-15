import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import test from 'node:test';
import { Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { fromVector, toVector } from '../api/coordinates.ts';
import { buildTerrainGeometry, decodeHeightMap, elevationKm, globeRadii, surfacePoint, surfaceRadius } from './terrain.ts';
import type { Body } from '../api/types.ts';
import type { TerrainFields } from './terrain.ts';

const bodies: Body[] = ['earth', 'moon', 'mars'];
const fields: TerrainFields = {};
for (const body of bodies) {
  const bytes = gunzipSync(readFileSync(new URL(`./assets/${body}.height.gz`, import.meta.url)));
  fields[body] = decodeHeightMap(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer);
}

test('official maps locate Himalaya, Olympus Mons and South Pole–Aitken in the correct hemispheres', () => {
  assert.ok(elevationKm(fields.earth, 28, 86.9) > 3, 'Himalaya above 3 km after area averaging');
  assert.ok(elevationKm(fields.mars, 18.65, -133.8) > 15, 'Olympus Mons above 15 km');
  assert.ok(elevationKm(fields.moon, -53, -169) < -3, 'SPA basin below -3 km');
  assert.ok(elevationKm(fields.moon, -53, -169) < elevationKm(fields.moon, -20, -169), 'SPA below northern highlands');
  assert.ok(elevationKm(fields.earth, 0, -140) < 0, 'Pacific retains negative bathymetry in data');
});

test('ocean surface stays at sea level while exaggeration changes mountains and basins radially', () => {
  assert.equal(surfaceRadius('earth', 0, -140, fields.earth, 30), globeRadii.earth);
  const seaLevel = globeRadii.earth;
  const trueHeight = surfaceRadius('earth', 28, 86.9, fields.earth, 1) - seaLevel;
  const exaggerated = surfaceRadius('earth', 28, 86.9, fields.earth, 12) - seaLevel;
  assert.ok(Math.abs(exaggerated - trueHeight * 12) < 1e-12);
  assert.ok(surfaceRadius('moon', -53, -169, fields.moon, 12) < globeRadii.moon);
  for (const body of bodies) assert.equal(surfaceRadius(body, 0, 0, undefined, 12), globeRadii[body]);
});

for (const body of bodies) {
  test(`${body}: closed meridian/poles, seamless normals, and periodic ±180 heights`, () => {
    const segments = 128, rows = segments / 2;
    const geometry = buildTerrainGeometry(body, fields[body], 30, segments);
    const vertices = geometry.getAttribute('position'), normals = geometry.getAttribute('normal');
    const at = (i: number) => new Vector3().fromBufferAttribute(vertices, i);
    const normal = (i: number) => new Vector3().fromBufferAttribute(normals, i);
    for (let row = 0; row <= rows; row++) {
      const start = row * (segments + 1), end = start + segments;
      assert.ok(at(start).distanceTo(at(end)) < 1e-6);
      assert.ok(normal(start).distanceTo(normal(end)) < 1e-6);
    }
    for (let i = 0; i <= segments; i++) {
      assert.ok(at(i).distanceTo(at(0)) < 1e-6);
      assert.ok(at(rows * (segments + 1) + i).distanceTo(at(rows * (segments + 1))) < 1e-6);
    }
    for (const lat of [-89, -53, 0, 28, 89]) {
      assert.equal(elevationKm(fields[body], lat, -180), elevationKm(fields[body], lat, 180));
      assert.ok(Math.abs(elevationKm(fields[body], lat, -179.999999) - elevationKm(fields[body], lat, 179.999999)) < 0.001);
    }
    geometry.dispose();
  });

  test(`${body}: raycasting displaced triangles preserves geographic clicks and anchor directions`, () => {
    const geometry = buildTerrainGeometry(body, fields[body], 30, 256);
    const material = new MeshBasicMaterial();
    const mesh = new Mesh(geometry, material);
    mesh.updateMatrixWorld(true);
    for (const [lat, lon] of [[28, 86.9], [-53, -169], [18.65, -133.8], [0, 179.99]]) {
      const direction = new Vector3(...toVector(lat, lon));
      const hits = new Raycaster(direction.clone().multiplyScalar(4), direction.clone().negate()).intersectObject(mesh);
      assert.ok(hits.length);
      const point = hits[0].point;
      const selected = fromVector(point.x, point.y, point.z);
      assert.ok(Math.abs(selected.lat - lat) < 1e-6);
      assert.ok(Math.abs(selected.lon - lon) < 1e-6);
      const anchor = new Vector3(...surfacePoint({ body, lat, lon }, fields, 30, 0.024));
      assert.ok(anchor.length() > point.length(), 'marker and arc endpoint stay outside the mesh');
      assert.ok(anchor.clone().normalize().distanceTo(direction) < 1e-7);
    }
    material.dispose(); geometry.dispose();
  });
}

test('compact decoder rejects broken headers, truncated payloads and invalid heights', () => {
  assert.throws(() => decodeHeightMap(new ArrayBuffer(8)));
  const bytes = gunzipSync(readFileSync(new URL('./assets/moon.height.gz', import.meta.url)));
  const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
  assert.throws(() => decodeHeightMap(buffer.slice(0, 100)));
  const invalid = buffer.slice(0);
  new DataView(invalid).setInt16(8, -32768, true);
  assert.throws(() => decodeHeightMap(invalid));
});
