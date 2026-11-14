import { Suspense, useEffect, useState } from 'react';
import { demoMode, getSuitability, getSuitabilityImage } from '../../api/client';
import type { Criterion, Location, Suitability } from '../../api/types';

import type { VisualizationComponents } from '../../shared/visualization';

const criteria: { id: Criterion; label: string }[] = [
  { id: 'total', label: 'Combined suitability' }, { id: 'landing', label: 'Landing slope' },
  { id: 'rover', label: 'Rover slope' }, { id: 'ice', label: 'Stable-ice proximity' },
  { id: 'temperature', label: 'Temperature' },
];
export default function SuitabilityPanel({ onSelect, MapView }: { onSelect: (location: Location) => void; MapView: VisualizationComponents['LunarSuitabilityMap'] }) {
  const [criterion, setCriterion] = useState<Criterion>('total');
  const [data, setData] = useState<Suitability | null>(null);
  const [image, setImage] = useState<{ criterion: Criterion; url: string } | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (demoMode) return;
    const controller = new AbortController();
    setLoading(true); setData(null); setImage(null); setError(''); setImageFailed(false);
    let url: string | undefined;
    Promise.all([getSuitability(controller.signal), getSuitabilityImage(criterion, controller.signal)])
      .then(([metadata, blob]) => {
        if (controller.signal.aborted) return;
        url = URL.createObjectURL(blob);
        setData(metadata); setImage({ criterion, url });
      }).catch(e => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Lunar layer unavailable.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [criterion, attempt]);
  return <section className="suitability-panel" aria-label="Lunar suitability">
    <div className="suitability-heading"><div><p className="eyebrow">LUNAR SOUTH POLE</p><h2>Base suitability</h2></div>
      <label>CRITERION<select value={criterion} onChange={e => setCriterion(e.target.value as Criterion)}>{criteria.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}</select></label></div>
    <p className="suitability-caveat">Suggestion, not a final site selection: illumination and Earth visibility are not included.</p>
    {demoMode && <div className="empty-state"><p>No lunar raster is bundled with this demo.</p><p>Connect the suitability data service to view the exported polar maps, weights and NASA candidate comparison.</p></div>}
    {!demoMode && loading && <p role="status">Loading lunar layer…</p>}
    {!demoMode && (error || imageFailed) && <div className="empty-state error" role="alert"><p>{error || 'The lunar layer image could not be displayed.'}</p><button onClick={() => setAttempt(a => a + 1)}>Retry lunar layer</button></div>}
    {data && image?.criterion === criterion && !imageFailed && <>
      <Suspense fallback={<p role="status">Loading lunar map…</p>}><MapView imageUrl={image.url} label={criteria.find(c => c.id === criterion)!.label} crs={data.grid.crs} pixelM={data.grid.pixel_m} onError={() => setImageFailed(true)} /></Suspense>
      <div className="suitability-legend"><span>0 · lower suitability</span><i /><span>1 · higher suitability</span></div>
      <p className="selection-note">{data.rules[criterion]}</p>
      <h3>Criterion weights</h3><dl className="weights">{Object.entries(data.weights).map(([key, weight]) => <div key={key}><dt>{criteria.find(c => c.id === key)?.label}</dt><dd>{(weight * 100).toFixed(0)}%</dd></div>)}</dl>
      <p className="selection-note">Missing: {data.missing.join('; ')}. {data.caveat}</p>
      <h3>NASA candidate comparison</h3><p className="selection-note">{data.candidate_coordinates}</p>
      <div className="candidate-list">{data.candidates.map(c => <button key={c.name} onClick={() => onSelect({ body: 'moon', lat: c.lat, lon: c.lon })}>
        <strong>{c.name}</strong><span>{c.lat}°, {c.lon}° · {c.group}</span>
        <span>Area score (90th percentile): {c.total_p90 === null ? 'No data' : c.total_p90.toFixed(3)}</span>
        <span>Percentile vs random zones: {c.percentile_vs_random === null ? 'No data' : `${c.percentile_vs_random.toFixed(1)}%`}</span>
      </button>)}</div>
    </>}
  </section>;
}
