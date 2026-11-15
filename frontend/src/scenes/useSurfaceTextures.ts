import { useEffect, useState } from 'react';
import { NoColorSpace, RepeatWrapping, SRGBColorSpace, TextureLoader } from 'three';
import type { Texture } from 'three';
import type { Body } from '../api/types';
import { textureUrl } from './textureLayers';
import type { SurfaceLayer } from './textureLayers';
import earthUrl from './assets/earth.jpg';
import moonUrl from './assets/moon.jpg';
import marsUrl from './assets/mars.jpg';

export interface BodySurface {
  color?: Texture; display?: Texture; normal?: Texture; overlay?: Texture;
  errors: string[];
}
export type SurfaceMaps = Partial<Record<Body, BodySurface>>;
const fallbacks: Record<Body, string> = { earth: earthUrl, moon: moonUrl, mars: marsUrl };

export function useSurfaceTextures(enabled: boolean, layer: SurfaceLayer, normals: boolean) {
  const [maps, setMaps] = useState<SurfaceMaps>({});
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const owned = new Set<Texture>();
    const loader = new TextureLoader();
    setMaps({});
    const update = (body: Body, patch: Partial<BodySurface>) => {
      if (active) setMaps(previous => ({ ...previous, [body]: { errors: [], ...previous[body], ...patch } }));
    };
    const failure = (body: Body, name: string) => {
      if (active) setMaps(previous => ({ ...previous, [body]: { ...previous[body], errors: [...(previous[body]?.errors ?? []), name] } }));
    };
    const load = (body: Body, key: 'color' | 'display' | 'normal' | 'overlay', url: string, fallback?: string) => {
      loader.load(url, texture => {
        if (!active) { texture.dispose(); return; }
        owned.add(texture);
        texture.wrapS = RepeatWrapping;
        texture.colorSpace = key === 'normal' ? NoColorSpace : SRGBColorSpace;
        texture.anisotropy = 4;
        update(body, { [key]: texture });
      }, undefined, () => {
        if (!active) return;
        if (fallback) load(body, key, fallback);
        else failure(body, key === 'display' ? layer : key === 'overlay' ? 'suitability' : key);
      });
    };
    for (const body of ['earth', 'moon', 'mars'] as Body[]) {
      const base = import.meta.env.BASE_URL;
      load(body, 'color', textureUrl(body, 'color', base), fallbacks[body]);
      if (['height', 'shadows', 'topography'].includes(layer)) load(body, 'display', textureUrl(body, layer, base));
      if (normals && (layer === 'color' || layer === 'suitability')) load(body, 'normal', textureUrl(body, 'normal', base));
      if (layer === 'suitability' && body !== 'earth') load(body, 'overlay', textureUrl(body, 'suitability', base));
    }
    return () => { active = false; owned.forEach(texture => texture.dispose()); };
  }, [enabled, layer, normals]);
  return maps;
}
