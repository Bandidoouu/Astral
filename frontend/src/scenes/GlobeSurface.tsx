import { useEffect, useMemo } from 'react';
import { ObjectSpaceNormalMap, Vector2 } from 'three';
import type { Body } from '../api/types';
import type { HeightGrid } from './lunarElevation';
import type { SurfaceLayer } from './textureLayers';
import type { BodySurface } from './useSurfaceTextures';
import { buildTerrainGeometry } from './terrain';
import { applyGeographicNormals, geographicNormalCacheKey } from './normalShader';

const fallback: Record<Body, string> = { earth: '#234c60', moon: '#6a6c70', mars: '#874e35' };

export function SurfaceMaterial({ body, maps, layer, normalRatio = 0 }: {
  body: Body; maps?: BodySurface; layer: SurfaceLayer; normalRatio?: number;
}) {
  const scale = useMemo(() => new Vector2(normalRatio, normalRatio), [normalRatio]);
  const colored = layer === 'color' || layer === 'suitability';
  const map = colored ? maps?.color : maps?.display ?? maps?.color;
  const normal = colored && normalRatio > 0 ? maps?.normal : undefined;
  if (!colored && maps?.display) return <meshBasicMaterial key={map?.uuid} map={map} toneMapped={false} />;
  return <meshStandardMaterial key={`${map?.uuid ?? body}:${normal?.uuid ?? 'mesh'}`} map={map ?? null}
    color={map ? '#ffffff' : fallback[body]} normalMap={normal ?? null} normalMapType={ObjectSpaceNormalMap}
    normalScale={scale} onBeforeCompile={applyGeographicNormals} customProgramCacheKey={geographicNormalCacheKey}
    roughness={body === 'earth' ? 0.82 : 1} metalness={0} />;
}

export function useGeographicGeometry(body: Body, field: HeightGrid | undefined, exaggeration: number) {
  const geometry = useMemo(() => buildTerrainGeometry(body, field, exaggeration, field ? 512 : 96), [body, field, exaggeration]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return geometry;
}
