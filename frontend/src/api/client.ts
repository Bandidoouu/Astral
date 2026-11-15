import { demoSearch, exactCuratedSite } from '../mocks/search';
import { gridSearch, originChunk } from '../mocks/offlineGrid';
import type { OfflineBlocks, OfflineCatalog } from '../mocks/offlineGrid';
import { toApiRequest } from './coordinates';
import { parseSearchResponse, parseSuitability } from './validation';
import type { Criterion, GalaxyPoint, Scale, SearchQuery, SearchResult, SuitabilityBody } from './types';
import moonSuitabilityFile from '../../../contracts/suitability_moon_south.json' with { type: 'json' };
import marsSuitabilityFile from '../../../contracts/suitability_mars.json' with { type: 'json' };

export const demoMode = import.meta.env.VITE_DATA_MODE !== 'api';
const staticBase = import.meta.env.BASE_URL.replace(/\/?$/, '/');
export const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const suitabilityUrl = (import.meta.env.VITE_SUITABILITY_URL || `${apiUrl}/api/suitability/moon_south`).replace(/\/$/, '');
async function request(url: string, signal: AbortSignal, init?: RequestInit, timeoutMs = 15000) {
  const response = await fetch(url, {
    ...init, signal: AbortSignal.any([signal, AbortSignal.timeout(timeoutMs)]),
  });
  if (!response.ok) throw new Error(`The API returned ${response.status}. Check the backend and try again.`);
  return response;
}
export async function search(query: SearchQuery, signal: AbortSignal): Promise<SearchResult> {
  const payload = toApiRequest(query);
  if (demoMode) {
    prefetchOffline();
    // 1 km, same size: every index patch is precomputed (loaded on first use). Otherwise
    // (60 m, gravity-scaled) the nearest curated site is served.
    if (payload.scale_m === 1000 && (payload.scale_mode ?? 'same_size') === 'same_size'
        && !exactCuratedSite(payload.body, payload.lat, payload.lon, '1000')) {
      const catalog = await loadCatalog(signal);
      const where = originChunk(catalog, payload.body, payload.lat, payload.lon);
      return gridSearch(payload, catalog, await loadChunk(where.key, where.file, signal));
    }
    return demoSearch(payload);
  }
  const response = await request(`${apiUrl}/api/similar`, signal, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  return { ...parseSearchResponse(await response.json(), payload), demo: false };
}
export async function getGalaxy(scale: Scale, signal: AbortSignal): Promise<GalaxyPoint[]> {
  // Offline: the real galaxy files (3D UMAP of the model embeddings) are bundled in public/data.
  const url = demoMode ? `${staticBase}data/galaxy_${scale}.json` : `${apiUrl}/api/galaxy?scale=${scale}`;
  const data: unknown = await (await request(url, signal)).json();
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
  // Offline: the exported PNGs are bundled in public/data/suitability.
  const url = demoMode ? `${staticBase}data/suitability/${body}_${criterion}.png` : `${suitabilityUrls[body]}/${criterion}`;
  const response = await request(url, signal);
  if (!response.headers.get('Content-Type')?.startsWith('image/png')) throw new Error('The suitability layer must be a PNG image.');
  return response.blob();
}
export function gradcamUrl(queryPatchId: string, resultPatchId: string) {
  if (demoMode) return `${staticBase}data/gradcam/${encodeURIComponent(queryPatchId)}__${encodeURIComponent(resultPatchId)}.png`;
  return `${apiUrl}/api/gradcam/${encodeURIComponent(queryPatchId)}/${encodeURIComponent(resultPatchId)}`;
}

let catalogPromise: Promise<OfflineCatalog> | null = null;
const blockPromises: Partial<Record<string, Promise<Uint16Array>>> = {};
const blocks: OfflineBlocks = {};
function loadCatalog(signal: AbortSignal) {
  catalogPromise ??= request(`${staticBase}data/offline1km/catalog.json`, signal, undefined, 180000).then(r => r.json() as Promise<OfflineCatalog>)
    .catch(e => { catalogPromise = null; throw e; });
  return catalogPromise;
}
async function loadChunk(key: string, file: string, signal: AbortSignal): Promise<OfflineBlocks> {
  blockPromises[key] ??= request(`${staticBase}data/offline1km/${file}`, signal, undefined, 180000)
    .then(r => r.arrayBuffer()).then(b => new Uint16Array(b))
    .catch(e => { delete blockPromises[key]; throw e; });
  blocks[key] = await blockPromises[key]!;
  return blocks;
}

/** After the first offline search, fetch the 1 km catalog in the background (low priority)
 * so later arbitrary clicks only need one ~80 KB result chunk. */
let prefetched = false;
function prefetchOffline() {
  if (prefetched || typeof window === 'undefined') return;
  prefetched = true;
  window.setTimeout(() => { loadCatalog(new AbortController().signal).catch(() => { prefetched = false; }); }, 4000);
}
