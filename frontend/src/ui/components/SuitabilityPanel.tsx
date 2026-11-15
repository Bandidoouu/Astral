import { Suspense, useEffect, useState } from 'react';
import { bundledSuitabilityFor, demoMode, getSuitability, getSuitabilityImage } from '../../api/client';
import type { Criterion, Location, Suitability, SuitabilityBody } from '../../api/types';

import type { VisualizationComponents } from '../../shared/visualization';

const criteriaFor: Record<SuitabilityBody, { id: Criterion; label: string }[]> = {
  moon: [
    { id: 'total', label: 'Combined suitability' }, { id: 'landing', label: 'Landing slope' },
    { id: 'rover', label: 'Rover slope' }, { id: 'ice', label: 'Stable-ice proximity' },
    { id: 'temperature', label: 'Temperature' },
  ],
  mars: [
    { id: 'total', label: 'Combined suitability' }, { id: 'landing', label: 'Landing slope' },
    { id: 'rover', label: 'Rover slope' }, { id: 'elevation', label: 'Low elevation (entry)' },
    { id: 'hydrogen', label: 'Hydrogen (water ice)' },
  ],
};
const titles: Record<SuitabilityBody, { eyebrow: string; caveat: string }> = {
  moon: { eyebrow: 'LUNAR SOUTH POLE',
    caveat: 'Suggestion, not a final site selection: illumination and Earth visibility are not included.' },
  mars: { eyebrow: 'MARS · 60° N TO 60° S',
    caveat: 'Suggestion, not a final site selection: only MOLA slope and elevation and Mars Odyssey hydrogen; thermal inertia, dust and radiation are not included.' },
};

export default function SuitabilityPanel({ onSelect, MapView }: { onSelect: (location: Location) => void; MapView: VisualizationComponents['LunarSuitabilityMap'] }) {
  const [body, setBody] = useState<SuitabilityBody>('moon');
  const [criterion, setCriterion] = useState<Criterion>('total');
  const [data, setData] = useState<Suitability | null>(null);
  const [bundled, setBundled] = useState(false);
  const [image, setImage] = useState<{ key: string; url: string } | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [imageError, setImageError] = useState('');
  const [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const criteria = criteriaFor[body];
  const key = `${body}:${criterion}`;

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setImage(null); setImageError(''); setImageFailed(false);
    let url: string | undefined;
    const metadata = demoMode
      ? Promise.reject(new Error('demo'))
      : getSuitability(controller.signal, body);
    metadata.then(d => { if (!controller.signal.aborted) { setData(d); setBundled(false); } })
      .catch(() => { if (!controller.signal.aborted) { setData(bundledSuitabilityFor(body)); setBundled(true); } });
    const picture = getSuitabilityImage(criterion, controller.signal, body);
    picture.then(blob => {
      if (controller.signal.aborted) return;
      url = URL.createObjectURL(blob);
      setImage({ key, url });
    }).catch(e => {
      if (controller.signal.aborted) return;
      const missing = e instanceof Error && e.message.includes('404');
      setImageError(missing
        ? `The ${body === 'mars' ? 'Mars' : 'lunar'} map image is not served yet. Turn on the Suitability surface layer on the 3D globe to see the combined score.`
        : e instanceof Error ? e.message : 'Suitability image unavailable.');
    })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [body, criterion, attempt, key]);

  const label = criteria.find(c => c.id === criterion)?.label ?? criterion;
  // recommended_zones: Moon {zones: [{rank, lat, lon, total, why}]}, Mars {method, zones: [...]}.
  const zones = ((data as unknown as { recommended_zones?: { zones?: { rank: number; lat: number; lon: number; total: number; why?: string }[] } } | null)
    ?.recommended_zones?.zones ?? []);
  return <section className="suitability-panel" aria-label="Base suitability">
    <div className="suitability-heading"><div><p className="eyebrow">{titles[body].eyebrow}</p><h2>Base suitability</h2></div>
      <label>BODY<select value={body} onChange={e => { setBody(e.target.value as SuitabilityBody); setCriterion('total'); }}>
        <option value="moon">Moon · south pole</option><option value="mars">Mars</option></select></label>
      <label>CRITERION<select value={criterion} onChange={e => setCriterion(e.target.value as Criterion)}>{criteria.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}</select></label></div>
    <p className="suitability-caveat">{titles[body].caveat}</p>
    {loading && <p role="status">Loading suitability layer…</p>}
    {!loading && (imageError || imageFailed) && <div className="empty-state" role="status"><p>{imageError || 'The layer image could not be displayed.'}</p>
      {!demoMode && <button onClick={() => setAttempt(a => a + 1)}>Retry layer</button>}</div>}
    {image?.key === key && !imageFailed && <>
      <Suspense fallback={<p role="status">Loading map…</p>}><MapView imageUrl={image.url} label={label} crs={data?.grid.crs ?? ''} pixelM={data?.grid.pixel_m ?? 0} onError={() => setImageFailed(true)} /></Suspense>
      <div className="suitability-legend"><span>0 · lower suitability</span><i /><span>1 · higher suitability</span></div>
    </>}
    {data && <>
      {bundled && <p className="selection-note">Showing the weights, rules and candidate scores exported by the ASTRAL model pipeline (bundled copy for offline use).</p>}
      <p className="selection-note">{data.rules[criterion]}</p>
      <h3>Criterion weights</h3><dl className="weights">{Object.entries(data.weights).map(([k, weight]) => <div key={k}><dt>{criteria.find(c => c.id === k)?.label ?? k}</dt><dd>{((weight ?? 0) * 100).toFixed(0)}%</dd></div>)}</dl>
      <p className="selection-note">Missing: {data.missing.join('; ')}. {data.caveat}</p>
      <h3>{body === 'moon' ? 'NASA candidate comparison' : 'Mars landing sites and candidates'}</h3><p className="selection-note">{data.candidate_coordinates}</p>
      <div className="candidate-list">{data.candidates.map(c => <button key={c.name} onClick={() => onSelect({ body, lat: c.lat, lon: c.lon })}>
        <strong>{c.name}</strong><span>{c.lat}°, {c.lon}° · {c.group}</span>
        <span>Area score (90th percentile): {c.total_p90 === null ? 'No data' : c.total_p90.toFixed(3)}</span>
        <span>Percentile vs random zones: {c.percentile_vs_random === null ? 'No data' : `${c.percentile_vs_random.toFixed(1)}%`}</span>
        <span className="find-analogs">Find Earth analogs →</span>
      </button>)}</div>
      {zones.length > 0 && <>
        <h3>Recommended zones</h3>
        <p className="selection-note">Top zones by the combined score (rules above). Pick one to search its Earth analogs.</p>
        <div className="candidate-list">{zones.slice(0, 8).map(z => <button key={`zone-${z.rank}`} onClick={() => onSelect({ body, lat: z.lat, lon: z.lon })}>
          <strong>Zone {z.rank}</strong><span>{z.lat.toFixed(2)}°, {z.lon.toFixed(2)}° · score {z.total.toFixed(3)}</span>
          {z.why && <span>{z.why}</span>}
          <span className="find-analogs">Find Earth analogs →</span>
        </button>)}</div>
      </>}
    </>}
  </section>;
}
