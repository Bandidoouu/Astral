import type { Body, Scale } from '../api/types';

/** Shareable links: ?body=moon&lat=-87.3&lon=77&scale=60&gravity=1 open the result directly. */
export interface ShareState { body: Body; lat: number; lon: number; scale: Scale; gravity: boolean }

export function parseShareParams(search: string): ShareState | null {
  const p = new URLSearchParams(search);
  const body = p.get('body'), lat = Number(p.get('lat')), lon = Number(p.get('lon'));
  if (!body || !['earth', 'moon', 'mars'].includes(body) || !p.has('lat') || !p.has('lon')) return null;
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  const scale: Scale = p.get('scale') === '60' ? 60 : 1000;
  return { body: body as Body, lat, lon, scale, gravity: scale === 1000 && p.get('gravity') === '1' };
}

export function buildShareUrl(base: string, s: ShareState) {
  const u = new URL(base);
  u.search = new URLSearchParams({ body: s.body, lat: String(Math.round(s.lat * 10000) / 10000),
    lon: String(Math.round(s.lon * 10000) / 10000), scale: String(s.scale), ...(s.gravity ? { gravity: '1' } : {}) }).toString();
  u.hash = '';
  return u.toString();
}
