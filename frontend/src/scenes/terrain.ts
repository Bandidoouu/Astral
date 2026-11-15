import { SphereGeometry, Vector3 } from 'three';
import { displayRadii as globeRadii } from './orbitLayout.ts';
import { toVector } from '../api/coordinates.ts';
import type { Body, Location } from '../api/types.ts';
import { sampleHeight } from './lunarElevation.ts';
import type { HeightGrid } from './lunarElevation.ts';

export const referenceKm: Record<Body, number> = { earth: 6371, moon: 1737.4, mars: 3396 };
export type TerrainFields = Partial<Record<Body, HeightGrid>>;
export { displayRadii as globeRadii, atlasPositions as globeCenters } from './orbitLayout.ts';

/** ATH1: little-endian width/height followed by signed integer meters, north first. */
export function decodeHeightMap(buffer: ArrayBuffer): HeightGrid {
  const view = new DataView(buffer);
  if (buffer.byteLength < 8 || view.getUint32(0, false) !== 0x41544831) throw new Error('Invalid height map');
  const width = view.getUint16(4, true), height = view.getUint16(6, true);
  if (width < 2 || height < 2 || width * height > 4_000_000 || buffer.byteLength !== 8 + width * height * 2) throw new Error('Invalid height dimensions');
  const values = new Float32Array(width * height);
  for (let i = 0; i < values.length; i++) {
    const meters = view.getInt16(8 + i * 2, true);
    if (meters < -15000 || meters > 30000) throw new Error('Invalid height value');
    values[i] = meters / 1000;
  }
  return { width, height, values };
}

const poleCache = new WeakMap<HeightGrid, [number, number]>();
function poles(field: HeightGrid): [number, number] {
  const cached = poleCache.get(field);
  if (cached) return cached;
  let north = 0, south = 0;
  for (let x = 0; x < field.width; x++) {
    north += field.values[x];
    south += field.values[(field.height - 1) * field.width + x];
  }
  const result: [number, number] = [north / field.width, south / field.width];
  poleCache.set(field, result);
  return result;
}

export function elevationKm(field: HeightGrid | undefined, lat: number, lon: number): number {
  if (!field) return 0;
  if (lat >= 90) return poles(field)[0];
  if (lat <= -90) return poles(field)[1];
  return sampleHeight(field, (lon + 180) / 360, (lat + 90) / 180);
}

export function surfaceRadius(body: Body, lat: number, lon: number, field: HeightGrid | undefined, exaggeration: number): number {
  const km = elevationKm(field, lat, lon);
  // Sea floor remains in the data, but oceans render at sea level, never as trenches.
  const visibleKm = body === 'earth' ? Math.max(0, km) : km;
  const factor = Math.max(1, Math.min(30, exaggeration));
  return globeRadii[body] * (1 + visibleKm * factor / referenceKm[body]);
}

export function surfacePoint(location: Location, fields: TerrainFields, exaggeration: number, clearance = 0): [number, number, number] {
  return toVector(location.lat, location.lon,
    surfaceRadius(location.body, location.lat, location.lon, fields[location.body], exaggeration) + clearance);
}

/** CPU displacement keeps Three's raycaster and the visible mesh in agreement. */
export function buildTerrainGeometry(body: Body, field: HeightGrid | undefined, exaggeration: number, segments = 512): SphereGeometry {
  const rows = segments / 2;
  const geometry = new SphereGeometry(globeRadii[body], segments, rows);
  const vertices = geometry.getAttribute('position'), uv = geometry.getAttribute('uv');
  for (let i = 0; i < vertices.count; i++) {
    // Three sphere coordinates put u=0 at -90E; texture maps start at -180E.
    const u = uv.getX(i) + 0.25;
    uv.setX(i, u);
    const lat = uv.getY(i) * 180 - 90;
    // Pole UVs have a half-cell offset; their position must not depend on it.
    const lon = ((i % (segments + 1)) / segments) * 360 - 90;
    const radius = surfaceRadius(body, lat, lon, field, exaggeration);
    const point = toVector(lat, lon, radius);
    vertices.setXYZ(i, ...point);
  }
  geometry.computeVertexNormals();
  const normals = geometry.getAttribute('normal');
  // SphereGeometry duplicates the meridian and pole vertices for UV mapping.
  // Share normals at those identical positions to eliminate a lighting seam.
  const smooth = (indices: number[]) => {
    const normal = new Vector3();
    for (const index of indices) normal.add(new Vector3().fromBufferAttribute(normals, index));
    normal.normalize();
    for (const index of indices) normals.setXYZ(index, normal.x, normal.y, normal.z);
  };
  for (let row = 1; row < rows; row++) smooth([row * (segments + 1), row * (segments + 1) + segments]);
  smooth(Array.from({ length: segments + 1 }, (_, i) => i));
  smooth(Array.from({ length: segments + 1 }, (_, i) => rows * (segments + 1) + i));
  geometry.computeBoundingSphere();
  return geometry;
}
