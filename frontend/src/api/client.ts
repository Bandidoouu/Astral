import { demoGalaxy, demoSearch } from '../mocks/search';
import { toApiRequest } from './coordinates';
import { parseSearchResponse, parseSuitability } from './validation';
import type { Criterion, GalaxyPoint, Scale, SearchQuery, SearchResult, SuitabilityBody } from './types';
import moonSuitabilityFile from '../../../contracts/suitability_moon_south.json' with { type: 'json' };
import marsSuitabilityFile from '../../../contracts/suitability_mars.json' with { type: 'json' };

export const demoMode = import.meta.env.VITE_DATA_MODE !== 'api';
export const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const suitabilityUrl = (import.meta.env.VITE_SUITABILITY_URL || `${apiUrl}/api/suitability/moon_south`).replace(/\/$/, '');
async function request(url: string, signal: AbortSignal, init?: RequestInit) {
  const response = await fetch(url, {
    ...init, signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
  });
  if (!response.ok) throw new Error(`The API returned ${response.status}. Check the backend and try again.`);
  return response;
}
export async function search(query: SearchQuery, signal: AbortSignal): Promise<SearchResult> {
  const payload = toApiRequest(query);
  if (demoMode) return demoSearch(payload);
  const response = await request(`${apiUrl}/api/similar`, signal, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  return { ...parseSearchResponse(await response.json(), payload), demo: false };
}
export async function getGalaxy(scale: Scale, signal: AbortSignal): Promise<GalaxyPoint[]> {
  // The only shared galaxy fixture is at 60 m. Do not relabel it as global data.
  if (demoMode) return scale === 60 ? demoGalaxy : [];
  const data: unknown = await (await request(`${apiUrl}/api/galaxy?scale=${scale}`, signal)).json();
  if (!Array.isArray(data) || !data.every(p => p && typeof p.id === 'string' && ['earth','moon','mars'].includes(p.body) &&
    [p.x, p.y, p.z].every(n => typeof n === 'number' && Number.isFinite(n)))) throw new Error('Invalid galaxy data.');
  return data;
}
const suitabilityUrls: Record<SuitabilityBody, string> = {
  moon: suitabilityUrl, mars: `${apiUrl}/api/suitability/mars`,
};
// Real ML exports (release v2-1km-r4), bundled so the panel works offline or before the
// backend serves the Mars endpoint. Same content the backend serves.
const bundledSuitability = { moon: moonSuitabilityFile, mars: marsSuitabilityFile };
export function bundledSuitabilityFor(body: SuitabilityBody) {
  return parseSuitability(bundledSuitability[body], body);
}
export async function getSuitability(signal: AbortSignal, body: SuitabilityBody = 'moon') {
  return parseSuitability(await (await request(suitabilityUrls[body], signal)).json(), body);
}
export async function getSuitabilityImage(criterion: Criterion, signal: AbortSignal, body: SuitabilityBody = 'moon') {
  const response = await request(`${suitabilityUrls[body]}/${criterion}`, signal);
  if (!response.headers.get('Content-Type')?.startsWith('image/png')) throw new Error('The suitability layer must be a PNG image.');
  return response.blob();
}
export function gradcamUrl(queryPatchId: string, resultPatchId: string) {
  return `${apiUrl}/api/gradcam/${encodeURIComponent(queryPatchId)}/${encodeURIComponent(resultPatchId)}`;
}
