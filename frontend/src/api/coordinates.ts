import type { Body, Location, SearchQuery, SimilarRequest } from './types.ts';

export const bodies: Body[] = ['earth', 'moon', 'mars'];
export const otherBodies = (body: Body) => bodies.filter(b => b !== body);
export function inDetailCoverage(location: Location) {
  if (!validCoordinates(location)) return false;
  return location.body === 'moon' ? location.lat < -80 : location.body === 'earth' &&
    location.lat >= 14 && location.lat <= 33 && location.lon >= -118 && location.lon <= -86;
}
export function detailAvailable(location: Location, targets: Body[]) {
  return inDetailCoverage(location) && targets.length === 1 &&
    targets[0] === (location.body === 'earth' ? 'moon' : 'earth');
}

export function validCoordinates({ lat, lon }: Pick<Location, 'lat' | 'lon'>) {
  return Number.isFinite(lat) && Number.isFinite(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
}

export function toVector(lat: number, lon: number, radius = 1): [number, number, number] {
  const phi = lat * Math.PI / 180;
  const theta = lon * Math.PI / 180;
  return [radius * Math.cos(phi) * Math.sin(theta), radius * Math.sin(phi), radius * Math.cos(phi) * Math.cos(theta)];
}

export function fromVector(x: number, y: number, z: number) {
  const radius = Math.hypot(x, y, z);
  if (!radius) throw new Error('Cannot select the center of a globe.');
  return { lat: Math.asin(Math.max(-1, Math.min(1, y / radius))) * 180 / Math.PI, lon: Math.atan2(x, z) * 180 / Math.PI };
}

export function toApiRequest(query: SearchQuery): SimilarRequest {
  if (!validCoordinates(query)) throw new Error('Enter latitude from −90 to 90 and longitude from −180 to 180.');
  if (!bodies.includes(query.body)) throw new Error('Unsupported origin.');
  if (!query.target_bodies.length || query.target_bodies.some(t => !bodies.includes(t) || t === query.body) ||
      new Set(query.target_bodies).size !== query.target_bodies.length) throw new Error('Choose at least one distinct destination.');
  if (query.scale_m !== 60 && query.scale_m !== 1000) throw new Error('Choose a supported scale.');
  if (!Number.isInteger(query.k) || query.k < 1) throw new Error('Choose a positive result count.');
  if (query.scale_m === 60 && !detailAvailable(query, query.target_bodies)) throw new Error('Detail (60 m) is limited to Moon ↔ Earth within coverage. Use Global (1 km).');
  if (query.profile === 'astrobiology' && query.body !== 'mars') throw new Error('Astrobiology is available for Mars only.');
  if (query.scale_mode !== undefined && query.scale_mode !== 'same_size' && query.scale_mode !== 'gravity_scaled') throw new Error('Choose a supported window size.');
  // gravity_scaled only exists at the global scale.
  const scale_mode = query.scale_m === 1000 ? (query.scale_mode ?? 'same_size') : 'same_size';
  return { ...query, scale_mode, target_bodies: [...query.target_bodies] };
}
