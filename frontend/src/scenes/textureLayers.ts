import type { Body } from '../api/types.ts';
import type { HeightGrid } from './lunarElevation.ts';

export type SurfaceLayer = 'color' | 'height' | 'shadows' | 'topography' | 'suitability';
export type HeightSource = 'packaged' | 'global';
export interface HeightMetadata {
  body: Body; width: number; height: number; min_m: number; max_m: number;
  source: string; normal_and_hillshade_vertical_exaggeration: number;
  notes: string[];
  topography: { min_m: number; max_m: number; legend: string };
}
export const layerFiles = {
  color: 'color_4k.jpg', height: 'height_4k.png', normal: 'normal_4k.jpg',
  shadows: 'hillshade_4k.jpg', topography: 'topography_4k.jpg',
  suitability: 'suitability_4k.png', metadata: 'height.json',
  topographyLegend: 'topography_legend.png', suitabilityLegend: 'suitability_legend.png',
} as const;

export function textureUrl(body: Body, kind: keyof typeof layerFiles, base = '/') {
  return `${base.replace(/\/?$/, '/')}textures/${body}/${layerFiles[kind]}`;
}

export function parseHeightMetadata(value: unknown, body: Body): HeightMetadata {
  if (!value || typeof value !== 'object') throw new Error('Missing height metadata');
  const data = value as Record<string, unknown>;
  const topo = data.topography as Record<string, unknown> | undefined;
  if (data.body !== body || data.projection !== 'equirectangular, lon -180..180, north up' ||
      data.encoding !== 'height_m = min_m + (pixel / 255) * (max_m - min_m)' ||
      !Number.isInteger(data.width) || !Number.isInteger(data.height) ||
      Number(data.width) !== Number(data.height) * 2 || Number(data.width) < 2 || Number(data.width) > 8192 ||
      typeof data.min_m !== 'number' || typeof data.max_m !== 'number' ||
      !Number.isFinite(data.min_m) || !Number.isFinite(data.max_m) || data.min_m >= data.max_m ||
      data.min_m < -15000 || data.max_m > 30000 || typeof data.source !== 'string' ||
      typeof data.normal_and_hillshade_vertical_exaggeration !== 'number' ||
      !Number.isFinite(data.normal_and_hillshade_vertical_exaggeration) || data.normal_and_hillshade_vertical_exaggeration <= 0 ||
      !Array.isArray(data.notes) || !data.notes.every(note => typeof note === 'string') ||
      !topo || typeof topo.min_m !== 'number' || typeof topo.max_m !== 'number' ||
      !Number.isFinite(topo.min_m) || !Number.isFinite(topo.max_m) || topo.min_m >= topo.max_m ||
      topo.legend !== 'topography_legend.png') throw new Error('Unsupported height map metadata');
  return data as unknown as HeightMetadata;
}

/** Canvas bytes are data, not sRGB-normalized heights. Keep the sidecar's units. */
export function decodeHeightPixels(pixels: ArrayLike<number>, width: number, height: number, metadata: HeightMetadata): HeightGrid {
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 2 || height < 2 ||
      width !== height * 2 || pixels.length !== width * height * 4) throw new Error('Invalid height image dimensions');
  const values = new Float32Array(width * height);
  for (let i = 0; i < values.length; i++) {
    const p = i * 4;
    if (pixels[p + 3] !== 255 || Math.abs(pixels[p] - pixels[p + 1]) > 1 || Math.abs(pixels[p] - pixels[p + 2]) > 1) {
      throw new Error('Height map must be opaque grayscale');
    }
    const zeroCode = Math.round(-metadata.min_m / (metadata.max_m - metadata.min_m) * 255);
    const meters = metadata.body === 'earth' && pixels[p] === zeroCode
      ? 0 : metadata.min_m + pixels[p] / 255 * (metadata.max_m - metadata.min_m);
    values[i] = meters / 1000;
  }
  return { width, height, values };
}
