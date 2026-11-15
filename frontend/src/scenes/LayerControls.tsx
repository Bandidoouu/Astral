import type { Body } from '../api/types';
import type { HeightMetadata, HeightSource, SurfaceLayer } from './textureLayers';
import type { TerrainOrigin, TerrainStatus } from './useTerrain';
import type { SurfaceMaps } from './useSurfaceTextures';
import { textureUrl } from './textureLayers';

const bodies: Body[] = ['earth', 'moon', 'mars'];
export default function LayerControls({ featureNames = true, onFeatureNames, layer, onLayer, heightSource, normals, onNormals, selectedBody,
  metadata, origins, maps, status }: {
  featureNames?: boolean; onFeatureNames?: (value: boolean) => void;
  layer: SurfaceLayer; onLayer: (layer: SurfaceLayer) => void;
  heightSource: HeightSource; onHeightSource?: (source: HeightSource) => void;
  normals: boolean; onNormals: (value: boolean) => void; selectedBody: Body;
  metadata: Partial<Record<Body, HeightMetadata>>; origins: Partial<Record<Body, TerrainOrigin>>;
  maps: SurfaceMaps; status: Record<Body, TerrainStatus>;
}) {
  const normalsApply = layer === 'color' || layer === 'suitability';
  const selectedMetadata = metadata[selectedBody];
  return <div className="astral-layer-controls">
    <label>Surface layer<select aria-label="Surface layer" value={layer} onChange={e => onLayer(e.target.value as SurfaceLayer)}>
      <option value="color">Visible color</option><option value="height">Height map</option>
      <option value="shadows">Shaded relief</option><option value="topography">Topography</option>
      <option value="suitability">Base suitability</option>
    </select></label>
    {/* Height source fixed to NASA elevation (LOLA, MOLA, SRTMGL30): the ETOPO (NOAA) option was removed so every layer is NASA data. */}
    <label className="astral-normal-toggle"><input type="checkbox" aria-label="Feature names" checked={featureNames} onChange={e => onFeatureNames?.(e.target.checked)} />Feature names <small>(IAU · Natural Earth)</small></label>
    <label className="astral-normal-toggle"><input type="checkbox" aria-label="Normal-map lighting" checked={normals}
      disabled={!normalsApply || heightSource !== 'packaged'} onChange={e => onNormals(e.target.checked)} />Normal-map lighting</label>
    <p aria-live="polite">{bodies.map(body => `${body[0].toUpperCase()}${body.slice(1)}: ${status[body] === 'ready' ? 'relief ready' : status[body] === 'loading' ? 'loading relief' : 'relief unavailable; color only'}`).join(' · ')}</p>
    <p aria-live="polite">Layer images: {bodies.map(body => {
      const images = maps[body];
      const kind = layer === 'suitability' ? 'overlay' : layer === 'color' ? 'color' : 'display';
      if (layer === 'suitability' && body === 'earth') return 'earth: color only';
      return `${body}: ${images?.[kind] ? 'ready' : images?.errors.includes(layer === 'suitability' ? 'suitability' : layer) ? 'unavailable; color fallback' : 'loading'}`;
    }).join(' · ')}</p>
    {normals && normalsApply && <p>{heightSource !== 'packaged' ? 'Global DEMs use mesh normals; packaged normal maps describe a different source.' : bodies.map(body =>
      `${body}: ${origins[body] === 'fallback' ? 'DEM fallback; mesh normals' : origins[body] !== 'packaged' ? 'loading heights' : maps[body]?.errors.includes('normal') ? 'normal map unavailable; mesh normals' : maps[body]?.normal ? 'normal map ready' : 'loading normal map'}`).join(' · ')}</p>}
    {bodies.some(body => maps[body]?.errors.length) && <p role="status">{bodies.flatMap(body => (maps[body]?.errors ?? []).map(error => `${body}: ${error} unavailable`)).join(' · ')}. Available color/mesh lighting is retained.</p>}
    {layer === 'shadows' && <p>Precomputed northwest illumination; this layer does not follow the scene light.</p>}
    {layer === 'suitability' && <p className="astral-layer-caveat">Suggestion, not a final site selection. Earth has no suitability layer. Transparent pixels mean no data. Moon: south-pole coverage; illumination and Earth visibility are not included. Mars: hydrogen coverage is limited to 60° N–60° S.</p>}
    <details className="astral-layer-reference"><summary>Layer legend & coverage</summary>
      <p>{selectedBody.toUpperCase()}{selectedMetadata ? ` · ${selectedMetadata.source}` : ' · global DEM or loading packaged metadata'}</p>
      {layer === 'topography' && maps[selectedBody]?.display && <img className="astral-layer-legend" src={textureUrl(selectedBody, 'topographyLegend', import.meta.env.BASE_URL)} alt={`${selectedBody} topography legend in meters`} />}
      {layer === 'height' && selectedMetadata && <p>Gray 0 → {selectedMetadata.min_m.toLocaleString()} m; gray 255 → {selectedMetadata.max_m.toLocaleString()} m. Per-body scale from the supplied metadata.</p>}
      {layer === 'suitability' && selectedBody !== 'earth' && maps[selectedBody]?.overlay && <img className="astral-layer-legend" src={textureUrl(selectedBody, 'suitabilityLegend', import.meta.env.BASE_URL)} alt={`${selectedBody} suitability score legend, 0 to 1`} />}
      {selectedMetadata?.notes.map(note => <p key={note}>{note}</p>)}
      <p>Visual context only. Layers do not change search results, ranking or mission scores.</p>
    </details>
  </div>;
}
