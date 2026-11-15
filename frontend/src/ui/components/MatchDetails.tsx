import { useState } from 'react';
import { dimensions, labels } from './ResultCard';
import { gradcamUrl } from '../../api/client';
import type { Analog, Attributes, SearchResult } from '../../api/types';

const attributes: { key: keyof Attributes; label: string; unit: string }[] = [
  { key: 'tmax_k', label: 'Maximum temperature', unit: 'K' },
  { key: 'tmin_k', label: 'Minimum temperature', unit: 'K' },
  { key: 'trange_k', label: 'Temperature range', unit: 'K' },
  { key: 'albedo', label: 'Albedo', unit: '' },
  { key: 'ice_distance_km', label: 'Stable-ice distance', unit: 'km' },
  { key: 'ice_frac', label: 'Ice fraction', unit: '' },
  { key: 'soil_pct', label: 'Rockiness percentile within body (0–1)', unit: '' },
  { key: 'precip_mm', label: 'Annual precipitation', unit: 'mm' },
];
function value(value: number | null | undefined, unit: string) {
  return value == null ? 'No data' : `${value.toLocaleString('en-US', { maximumFractionDigits: 3 })}${unit ? ` ${unit}` : ''}`;
}
function windowKm(active: Analog) {
  return active.window_km ?? 128 * active.scale_m / 1000;
}
// Grad-CAM exists for the curated demo pairs at 1 km (same_size); other pairs return 404
// and the figure is simply not shown.
function GradCam({ queryId, patchId }: { queryId: string; patchId: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  return <figure className="gradcam">
    <h3>Where the network sees similarity</h3>
    <img src={gradcamUrl(queryId, patchId)} alt="Grad-CAM of the origin and matched terrain patches" loading="lazy" onError={() => setFailed(true)} />
    <figcaption>Grad-CAM of the terrain similarity (cosine) only, not the full ranking or the environmental dimensions. Coarse and approximate.</figcaption>
  </figure>;
}
export default function MatchDetails({ active, result }: { active: Analog; result: SearchResult }) {
  const patch = result.query.patches?.[active.body];
  return <section className="match-metadata" aria-label="Match measurements">
    <div>
      <h3>{result.demo ? 'Illustrative patch information' : 'Compared patch'}</h3>
      <p>{active.scale_m} m/pixel · {windowKm(active).toLocaleString('en-US', { maximumFractionDigits: 1 })} km across{patch?.window_km !== undefined && patch.window_km !== windowKm(active) ? ` (origin patch ${patch.window_km.toLocaleString('en-US', { maximumFractionDigits: 1 })} km, gravity-scaled)` : ''}</p>
      {active.land_cover && <p>Land cover at the match center: {active.land_cover} (MODIS)</p>}
      <p>Origin patch: <code>{patch?.patch_id ?? 'No data'}</code></p>
      <p>Center offset from requested point: {value(patch?.distance_km, 'km')}</p>
      <p>Ranking method: {result.query.method.toUpperCase()}</p>
      <small>The ranking order and weighted score are separate outputs. The frontend preserves the returned order.</small>
    </div>
    <div>
      <h3>Weights used in the total</h3>
      {active.weights_used === undefined ? <p>No data — weights were not supplied.</p> :
        <dl className="weights">{dimensions.map(d => <div key={d}><dt>{labels[d]}</dt><dd>{active.weights_used?.[d] == null ? 'Not used' : `${(active.weights_used[d]! * 100).toFixed(1)}%`}</dd></div>)}</dl>}
    </div>
    {!result.demo && active.scale_m === 1000 && patch?.patch_id && <GradCam key={`${patch.patch_id}-${active.patch_id}`} queryId={patch.patch_id} patchId={active.patch_id} />}
    <div className="measurement-table">
      <h3>{result.demo ? 'Illustrative site attributes' : 'Site attributes'}</h3>
      <table><thead><tr><th>Measurement</th><th>Origin</th><th>Match</th></tr></thead><tbody>
        {attributes.map(a => <tr key={a.key}><th scope="row">{a.label}</th><td>{value(result.query.attributes?.[a.key], a.unit)}</td><td>{value(active.attributes[a.key], a.unit)}</td></tr>)}
      </tbody></table>
      <small>Stable-ice distance is a site attribute, not a similarity score.</small>
    </div>
  </section>;
}
