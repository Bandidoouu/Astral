import { useEffect, useRef, useState } from 'react';
import { NoColorSpace, RepeatWrapping, SRGBColorSpace, TextureLoader } from 'three';
import type { Texture } from 'three';
import type { Body } from '../api/types';
import { textureUrl } from './textureLayers';
import { createBackgroundQueue } from '../shared/networkGate';
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

/** Loads what is on screen first (the active body's visible layer), then the rest one at a
 * time in the background, paused while a search waits for its results. */
export function useSurfaceTextures(enabled: boolean, layer: SurfaceLayer, normals: boolean, focusBody: Body = 'earth') {
  const [maps, setMaps] = useState<SurfaceMaps>({});
  // Priority order only: changing the active body later must not reload what is already loaded.
  const focus = useRef(focusBody);
  focus.current = focusBody;
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const owned = new Set<Texture>();
    const loader = new TextureLoader();
    const queue = createBackgroundQueue();
    setMaps({});
    const update = (body: Body, patch: Partial<BodySurface>) => {
      if (active) setMaps(previous => ({ ...previous, [body]: { errors: [], ...previous[body], ...patch } }));
    };
    const failure = (body: Body, name: string) => {
      if (active) setMaps(previous => ({ ...previous, [body]: { ...previous[body], errors: [...(previous[body]?.errors ?? []), name] } }));
    };
    const load = (body: Body, key: 'color' | 'display' | 'normal' | 'overlay', url: string, fallback?: string): Promise<void> => new Promise(resolve => {
      loader.load(url, texture => {
        resolve();
        if (!active) { texture.dispose(); return; }
        owned.add(texture);
        texture.wrapS = RepeatWrapping;
        texture.colorSpace = key === 'normal' ? NoColorSpace : SRGBColorSpace;
        texture.anisotropy = 4;
        update(body, { [key]: texture });
      }, undefined, () => {
        if (!active) { resolve(); return; }
        if (fallback) load(body, key, fallback).then(resolve);
        else { failure(body, key === 'display' ? layer : key === 'overlay' ? 'suitability' : key); resolve(); }
      });
    });
    const base = import.meta.env.BASE_URL;
    const first = focus.current;
    const ordered = [first, ...(['earth', 'moon', 'mars'] as Body[]).filter(b => b !== first)];
    const layerLoads = (body: Body) => {
      const tasks: (() => Promise<void>)[] = [];
      if (['height', 'shadows', 'topography'].includes(layer)) tasks.push(() => load(body, 'display', textureUrl(body, layer as 'height' | 'shadows' | 'topography', base)));
      if (layer === 'suitability' && body !== 'earth') tasks.push(() => load(body, 'overlay', textureUrl(body, 'suitability', base)));
      return tasks;
    };
    // Foreground: what is on screen (active body's color and selected layer).
    load(first, 'color', textureUrl(first, 'color', base), fallbacks[first]);
    layerLoads(first).forEach(t => t());
    // Background, one at a time when no search is waiting: other bodies' color and layer, then normals.
    for (const body of ordered.slice(1)) {
      queue.add(() => load(body, 'color', textureUrl(body, 'color', base), fallbacks[body]));
      layerLoads(body).forEach(t => queue.add(t));
    }
    if (normals && (layer === 'color' || layer === 'suitability')) {
      for (const body of ordered) queue.add(() => load(body, 'normal', textureUrl(body, 'normal', base)));
    }
    return () => { active = false; queue.cancel(); owned.forEach(texture => texture.dispose()); };
  }, [enabled, layer, normals]);
  return maps;
}
