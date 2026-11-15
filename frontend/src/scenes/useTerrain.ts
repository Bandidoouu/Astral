import { useEffect, useState } from 'react';
import earthUrl from './assets/earth.height.gz?url';
import moonUrl from './assets/moon.height.gz?url';
import marsUrl from './assets/mars.height.gz?url';
import { decodeHeightMap } from './terrain';
import type { TerrainFields } from './terrain';
import type { Body } from '../api/types';
import { decodeHeightPixels, parseHeightMetadata, textureUrl } from './textureLayers';
import type { HeightMetadata, HeightSource } from './textureLayers';

const urls: Record<Body, string> = { earth: earthUrl, moon: moonUrl, mars: marsUrl };
export type TerrainStatus = 'loading' | 'ready' | 'unavailable';
export type TerrainOrigin = 'packaged' | 'global' | 'fallback';

async function globalHeight(body: Body, signal: AbortSignal) {
  const response = await fetch(urls[body], { signal });
  if (!response.ok) throw new Error('Height resource unavailable');
  const bytes = await response.arrayBuffer();
  const signature = new Uint8Array(bytes, 0, Math.min(2, bytes.byteLength));
  const buffer = signature[0] === 0x1f && signature[1] === 0x8b
    ? await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer()
    : bytes;
  return decodeHeightMap(buffer);
}

async function packagedHeight(body: Body, signal: AbortSignal) {
  const base = import.meta.env.BASE_URL;
  const [sidecar, image] = await Promise.all([
    fetch(textureUrl(body, 'metadata', base), { signal }),
    fetch(textureUrl(body, 'height', base), { signal }),
  ]);
  if (!sidecar.ok || !image.ok) throw new Error('Packaged height resource unavailable');
  const metadata = parseHeightMetadata(await sidecar.json(), body);
  const bitmap = await createImageBitmap(await image.blob(), { colorSpaceConversion: 'none' });
  const canvas = document.createElement('canvas');
  try {
    if (bitmap.width !== metadata.width || bitmap.height !== metadata.height) throw new Error('Height image does not match its metadata');
    // Browser-sized field; source remains unmodified. Both use north-first pixel centers.
    canvas.width = 1440; canvas.height = 720;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) throw new Error('Height image cannot be decoded');
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    return { field: decodeHeightPixels(pixels, canvas.width, canvas.height, metadata), metadata };
  } finally { bitmap.close(); canvas.width = 0; canvas.height = 0; }
}

export function useTerrain(enabled: boolean, source: HeightSource = 'packaged') {
  const [fields, setFields] = useState<TerrainFields>({});
  const [status, setStatus] = useState<Record<Body, TerrainStatus>>({ earth: 'loading', moon: 'loading', mars: 'loading' });
  const [metadata, setMetadata] = useState<Partial<Record<Body, HeightMetadata>>>({});
  const [origins, setOrigins] = useState<Partial<Record<Body, TerrainOrigin>>>({});
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    setFields({}); setMetadata({}); setOrigins({});
    setStatus({ earth: 'loading', moon: 'loading', mars: 'loading' });
    for (const body of ['earth', 'moon', 'mars'] as Body[]) {
      (async () => {
        try {
          if (source === 'global') {
            const field = await globalHeight(body, controller.signal);
            if (!controller.signal.aborted) {
              setFields(previous => ({ ...previous, [body]: field }));
              setOrigins(previous => ({ ...previous, [body]: 'global' }));
            }
          } else {
            try {
              const result = await packagedHeight(body, controller.signal);
              if (!controller.signal.aborted) {
                setFields(previous => ({ ...previous, [body]: result.field }));
                setMetadata(previous => ({ ...previous, [body]: result.metadata }));
                setOrigins(previous => ({ ...previous, [body]: 'packaged' }));
              }
            } catch (error) {
              if (controller.signal.aborted) throw error;
              const field = await globalHeight(body, controller.signal);
              if (!controller.signal.aborted) {
                setFields(previous => ({ ...previous, [body]: field }));
                setOrigins(previous => ({ ...previous, [body]: 'fallback' }));
              }
            }
          }
          if (!controller.signal.aborted) setStatus(previous => ({ ...previous, [body]: 'ready' }));
        } catch {
          if (!controller.signal.aborted) setStatus(previous => ({ ...previous, [body]: 'unavailable' }));
        }
      })();
    }
    return () => controller.abort();
  }, [enabled, source]);
  return { fields, status, metadata, origins };
}
