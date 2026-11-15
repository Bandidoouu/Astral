import { Suspense, useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, ArrowUpRight, ChevronDown, Crosshair, ExternalLink, Info, Layers, Minimize2, Orbit, PanelsTopLeft, RotateCcw, Search, Sparkles } from 'lucide-react';
import ResultCard, { dimensions, labels, RadarChart } from './components/ResultCard';
import { demoMode, getGalaxy, search } from '../api/client';
import { detailAvailable, otherBodies, validCoordinates } from '../api/coordinates';
import MapPanel from './components/MapPanel';
import MatchDetails from './components/MatchDetails';
import SuitabilityPanel from './components/SuitabilityPanel';
import MissionPanel from './components/MissionPanel';
import AnalogEvidence from './components/AnalogEvidence';
import type { Body, GalaxyPoint, Location, Profile, Scale, ScaleMode, SearchResult } from '../api/types';

import type { VisualizationComponents } from '../shared/visualization';

const bodyNames = { earth: 'Earth', moon: 'Moon', mars: 'Mars' };
const sites: Record<Body, { name: string; lat: number; lon: number }[]> = {
  earth: [{ name: 'Sonora, Mexico', lat: 31.77, lon: -113.5 }, { name: 'Puebla, Mexico', lat: 19.02, lon: -98.62 }],
  moon: [{ name: 'Lunar south pole', lat: -89.5, lon: 130 }, { name: 'Montes Marius', lat: 14, lon: -56 }],
  mars: [{ name: 'Jezero region', lat: 18.38, lon: 77.58 }, { name: 'Gale region', lat: -5.4, lon: 137.8 }],
};
const profiles: { id: Profile; label: string }[] = [{ id: 'general', label: 'General · balanced comparison' }, { id: 'rover', label: 'Rover & mobility' }, { id: 'isru', label: 'Resources · ISRU' }, { id: 'habitat', label: 'Habitat & construction' }, { id: 'eva', label: 'Spacewalks · EVA' }, { id: 'astrobiology', label: 'Astrobiology' }];
const sources = [
  { title: 'Earthdata & Worldview', body: 'EARTH', text: 'Elevation and surface temperature', href: 'https://search.earthdata.nasa.gov/' },
  { title: 'LRO · LOLA & Diviner', body: 'MOON', text: 'Lunar terrain and polar temperatures', href: 'https://pds-geosciences.wustl.edu/missions/lro/' },
  { title: 'PDS · MOLA', body: 'MARS', text: 'Mars Global Surveyor topography', href: 'https://pds-geosciences.wustl.edu/missions/mgs/mola.html' },
];

export default function ExplorerApp({ PlanetaryScene, LunarSuitabilityMap }: VisualizationComponents) {
  const [body, setBody] = useState<Body>('moon');
  const [lat, setLat] = useState('-89.5');
  const [lon, setLon] = useState('130');
  const [profile, setProfile] = useState<Profile>('general');
  const [view, setView] = useState<'system' | 'galaxy'>('system');
  const [panel, setPanel] = useState<'search' | 'results' | 'details' | 'sources' | 'suitability' | 'missions' | null>(null);
  const [dockVisible, setDockVisible] = useState(true);
  const [focusedId, setFocusedId] = useState('');
  const [targets, setTargets] = useState<Body[]>(['earth', 'mars']);
  const [scale, setScale] = useState<Scale>(1000);
  const [scaleMode, setScaleMode] = useState<ScaleMode>('same_size');
  const [scaleNotice, setScaleNotice] = useState('');
  const [result, setResult] = useState<SearchResult | null>(null);
  const [activeId, setActiveId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [resetKey, setResetKey] = useState(0);
  const [galaxy, setGalaxy] = useState<GalaxyPoint[]>([]);
  const [galaxyError, setGalaxyError] = useState('');
  const [galaxyLoading, setGalaxyLoading] = useState(false);
  const coordinates = { body, lat: Number(lat), lon: Number(lon) };
  const valid = lat.trim() !== '' && lon.trim() !== '' && validCoordinates(coordinates);
  const detailAllowed = valid && detailAvailable(coordinates, targets);
  const supported = targets.length > 0 && (scale === 1000 || detailAllowed);
  const active = result?.results.find(r => r.patch_id === activeId) ?? result?.results[0];

  function resetDetailIfNeeded(location: Location, nextTargets: Body[]) {
    if (scale === 60 && !detailAvailable(location, nextTargets)) {
      setScale(1000);
      setScaleNotice('Switched to Global (1 km): detail is only available for Moon ↔ Earth within coverage.');
    }
  }
  function changeCoordinate(axis: 'lat' | 'lon', value: string) {
    resetDetailIfNeeded({ ...coordinates, [axis]: value.trim() ? Number(value) : NaN }, targets);
    if (axis === 'lat') setLat(value); else setLon(value);
  }
  function toggleTarget(target: Body) {
    const nextTargets = targets.includes(target) ? targets.filter(t => t !== target) : [...targets, target];
    resetDetailIfNeeded(coordinates, nextTargets);
    setTargets(nextTargets);
  }
  function selectLocation(location: Location) {
    const nextTargets = location.body === body ? targets : otherBodies(location.body);
    resetDetailIfNeeded(location, nextTargets);
    setTargets(nextTargets);
    setBody(location.body);
    setLat(String(Math.round(location.lat * 10000) / 10000));
    setLon(String(Math.round(location.lon * 10000) / 10000));
    if (location.body !== 'mars' && profile === 'astrobiology') setProfile('general');
  }
  useEffect(() => {
    const controller = new AbortController();
    setResult(null); setFocusedId(''); setError(''); setLoading(valid && supported);
    if (!valid || !supported) return () => controller.abort();
    const timer = setTimeout(() => {
      search({ body, lat: Number(lat), lon: Number(lon), profile, k: 5, scale_m: scale, scale_mode: scaleMode, target_bodies: targets }, controller.signal)
        .then(data => {
          if (controller.signal.aborted) return;
          setResult(data); setActiveId(data.results[0]?.patch_id ?? '');
        }).catch(e => {
          if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Search failed. Please try again.');
        }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 350);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [body, lat, lon, profile, targets, scale, scaleMode, valid, supported, attempt]);

  useEffect(() => {
    if (view !== 'galaxy') return;
    const controller = new AbortController();
    setGalaxy([]); setGalaxyError(''); setGalaxyLoading(true);
    getGalaxy(scale, controller.signal).then(data => { if (!controller.signal.aborted) setGalaxy(data); })
      .catch(e => { if (!controller.signal.aborted) setGalaxyError(e instanceof Error ? e.message : 'Galaxy unavailable.'); })
      .finally(() => { if (!controller.signal.aborted) setGalaxyLoading(false); });
    return () => controller.abort();
  }, [view, scale, attempt]);


  function chooseMission(nextProfile: Profile) {
    const nextTargets = body === 'earth' ? otherBodies(body) : ['earth' as Body];
    resetDetailIfNeeded(coordinates, nextTargets);
    setTargets(nextTargets); setProfile(nextProfile);
    setView('system'); setPanel('results');
  }
  const panelTitles = { search: 'Choose your origin', results: 'Analog results', details: 'Match details', sources: 'Data sources', suitability: 'Base suitability', missions: 'Plan an investigation' };
  function togglePanel(next: NonNullable<typeof panel>) {
    setPanel(current => current === next ? null : next);
  }
  function showMatch(patchId: string) {
    setActiveId(patchId); setFocusedId(patchId); setView('system'); setPanel('details');
  }

  return <div className="atlas-app">
    <header className="atlas-header">
      <a className="brand" href="#" aria-label="ASTRAL explorer" onClick={event => { event.preventDefault(); setPanel(null); }}><Orbit size={26} strokeWidth={1.3} /><span>ASTRAL<small>PLANETARY ANALOG EXPLORER</small></span></a>
      <nav className="view-switch" aria-label="Visualization">
        <button aria-pressed={view === 'system'} onClick={() => setView('system')}><Orbit size={14} /><span>System</span></button>
        <button aria-pressed={view === 'galaxy'} onClick={() => setView('galaxy')}><Sparkles size={14} /><span>Terrain galaxy</span></button>
        <button aria-expanded={panel === 'suitability'} aria-controls={panel === 'suitability' ? 'suitability-panel' : undefined} onClick={() => togglePanel('suitability')}><Layers size={14} /><span>Base suitability</span></button>
      </nav>
      <div className="header-actions">
        <button className="text-button mission-launcher" aria-label="Missions" aria-expanded={panel === 'missions'} onClick={() => togglePanel('missions')}><Crosshair size={15} /><span>Missions</span></button>
        <button className="text-button" aria-expanded={panel === 'sources'} onClick={() => togglePanel('sources')}><Info size={15} /><span>Data sources</span></button>
        <button className="search-launcher" aria-expanded={panel === 'search'} onClick={() => togglePanel('search')}><Search size={15} /><span>Explore</span></button>
      </div>
    </header>
    <main className="atlas-stage" aria-label="Planetary explorer">
      <h1 className="sr-only">ASTRAL planetary analog map</h1>
      <div className="scene" aria-label="Interactive planetary map">
        <Suspense fallback={<div className="scene-fallback">Loading planetary view…</div>}>
          <PlanetaryScene selected={valid ? coordinates : { body, lat: 0, lon: 0 }} results={result?.results ?? []} onSelect={selectLocation} galaxy={galaxy} view={view} resetKey={resetKey} focusedMatch={result?.results.find(r => r.patch_id === focusedId) ?? null} onInspect={showMatch} />
        </Suspense>
      </div>
      <div className="atlas-context">
        <p className="eyebrow">{view === 'system' ? 'ORBITAL ATLAS' : 'TERRAIN EMBEDDINGS'}</p>
        <button className="origin-chip" onClick={() => togglePanel('search')} aria-label="Edit origin" aria-expanded={panel === 'search'}>
          <span className={`body-disc ${body}`} /><strong>{bodyNames[body]}</strong><span>{valid ? `${coordinates.lat.toFixed(2)}°, ${coordinates.lon.toFixed(2)}°` : 'Check coordinates'}</span><ChevronDown size={13} />
        </button>
        <p className="map-caption">{view === 'system' ? 'Visual orbit guides · not to scale' : demoMode ? '3D UMAP of the model v2 terrain embeddings (bundled for offline use)' : `${galaxy.length.toLocaleString()} projected patches`}</p>
      </div>
      <div className="map-tools">
        <button className="icon-button" onClick={() => { setFocusedId(''); setResetKey(k => k + 1); }} aria-label="Reset camera" title="Reset camera"><RotateCcw size={17} /></button>
        <button className="icon-button" aria-label={dockVisible ? 'Hide match strip' : 'Show match strip'} title={dockVisible ? 'Hide match strip' : 'Show match strip'} aria-pressed={!dockVisible} onClick={() => setDockVisible(v => !v)}>{dockVisible ? <Minimize2 size={17} /> : <PanelsTopLeft size={17} />}</button>
      </div>
      {view === 'galaxy' && (galaxyLoading || galaxyError || galaxy.length === 0) && <div className="galaxy-status" role="status">{galaxyLoading ? 'Loading terrain galaxy…' : galaxyError || 'No galaxy points available at this scale.'}{galaxyError && <button onClick={() => setAttempt(a => a + 1)}>Retry</button>}</div>}
      <div className="map-notices" aria-live="polite">
        {loading && <p className="map-notice"><span className="loader" />Looking across worlds…</p>}
        {error && <button className="map-notice error" onClick={() => setPanel('results')}><Info size={14} />Search unavailable · View error</button>}
        {!valid && <button className="map-notice error" onClick={() => setPanel('search')}>Check origin coordinates</button>}
        {targets.length === 0 && <button className="map-notice" onClick={() => setPanel('search')}>Choose at least one destination</button>}
        {scaleNotice && <button className="map-notice" onClick={() => setPanel('search')}>Switched to global scale · View coverage</button>}
        {!!result?.warnings.length && <button className="map-notice" onClick={() => setPanel('results')}><Info size={14} />{result.warnings.length} coverage / data {result.warnings.length === 1 ? 'notice' : 'notices'}</button>}
      </div>
      {dockVisible && <section className="match-dock" aria-label="Match overview">
        <div className="dock-heading"><button onClick={() => togglePanel('results')} aria-expanded={panel === 'results'}><span>TERRAIN MATCHES</span><strong>{result?.results.length ?? '—'}</strong><ArrowRight size={14} /></button><span>{scale === 1000 ? '1 km / pixel' : '60 m / pixel'}</span></div>
        <div className="match-strip">
          {result?.results.map(r => <button key={r.patch_id} className={`match-chip ${active?.patch_id === r.patch_id ? 'active' : ''}`} aria-pressed={active?.patch_id === r.patch_id} aria-label={`Inspect ${r.region}`} onClick={() => showMatch(r.patch_id)}>
            <span className={`body-disc ${r.body}`} /><span className="match-chip-name"><small>{bodyNames[r.body]}</small><strong>{r.region}</strong></span>
            <span className="match-chip-score">{Math.round(r.score * 100)}<small>%</small></span><ArrowUpRight size={13} />
          </button>)}
          {!result?.results.length && <button className="dock-empty" onClick={() => setPanel(error ? 'results' : 'search')}>{loading ? 'Finding matches…' : error ? 'Search unavailable. Open results for details.' : 'No matches yet. Choose a location to explore.'}<ArrowRight size={14} /></button>}
        </div>
      </section>}
      <div className="atlas-status"><span><span className="status-dot" />{demoMode ? 'OFFLINE · Precomputed model v2 results · Similarity is not mission suitability' : 'LIVE API · Similarity is not mission suitability'}</span><span className="map-hint">Click a globe or match marker · Drag to orbit · Scroll to zoom</span></div>
      {panel && <MapPanel key={panel} id={`${panel}-panel`} title={panelTitles[panel]} side={panel === 'search' ? 'left' : 'right'} onClose={() => setPanel(null)}>
        {panel === 'missions' && <MissionPanel body={body} profile={profile} demo={demoMode} onChoose={chooseMission} />}
        {panel === 'search' && <>          <div className="selection-panel">
            <div className="section-label"><Crosshair size={14} /><h2>Choose your origin</h2><span>01</span></div>
            <div className="body-switch">{(['earth', 'moon', 'mars'] as Body[]).map(b => <button key={b} aria-pressed={body === b} onClick={() => selectLocation({ body: b, ...sites[b][0] })}><span className={`body-disc ${b}`} />{bodyNames[b]}<span className="selected-dot" /></button>)}</div>
            <form onSubmit={e => { e.preventDefault(); setAttempt(a => a + 1); }}>
              <div className="input-row"><label className="site-field">STARTING SITE<select value={sites[body].find(s => s.lat === Number(lat) && s.lon === Number(lon))?.name ?? 'custom'} onChange={e => { const site = sites[body].find(s => s.name === e.target.value); if (site) selectLocation({ body, ...site }); }}><option value="custom" disabled>Custom coordinates</option>{sites[body].map(s => <option key={s.name}>{s.name}</option>)}</select></label><label>LATITUDE<input aria-label="Latitude" type="number" min="-90" max="90" step="any" required value={lat} onChange={e => changeCoordinate('lat', e.target.value)} /></label><label>LONGITUDE<input aria-label="Longitude" type="number" min="-180" max="180" step="any" required value={lon} onChange={e => changeCoordinate('lon', e.target.value)} /></label></div>
              <div className="search-options">
                <fieldset className="target-selector"><legend>SEARCH IN</legend>
                  {otherBodies(body).map(target => <label key={target}><input type="checkbox" checked={targets.includes(target)} onChange={() => toggleTarget(target)} />{bodyNames[target]}</label>)}
                </fieldset>
                <label>SEARCH SCALE<select aria-describedby="scale-help" value={scale} onChange={e => { setScale(Number(e.target.value) as Scale); setScaleNotice(''); }}>
                  <option value={1000}>Global (1 km)</option><option value={60} disabled={!detailAllowed}>Detail (60 m)</option>
                </select></label>
                <label>WINDOW SIZE<select aria-label="Window size" aria-describedby="window-help" value={scale === 1000 ? scaleMode : 'same_size'} disabled={scale !== 1000} onChange={e => setScaleMode(e.target.value as ScaleMode)}>
                  <option value="same_size">Same size</option><option value="gravity_scaled">Gravity-scaled</option>
                </select></label>
              </div>
              <p id="window-help" className="selection-note">Gravity-scaled: landforms built under lower gravity are larger, so Moon windows are 6× and Mars windows 2.6× larger than Earth's (global scale only).</p>
              <p id="scale-help" className="selection-note">Detail: Moon south of 80° S ↔ Earth within 14–33° N, 118–86° W. Select only the other covered body. Global patches span 128 km; detail patches span 7.68 km.</p>
              <div className="mission-row"><label>MISSION PROFILE<select value={profile} onChange={e => setProfile(e.target.value as Profile)}>{profiles.filter(p => p.id !== 'astrobiology' || body === 'mars').map(p => <option key={p.id} value={p.id}>{p.label}</option>)}</select></label><button className="search-button" disabled={!valid || !supported || loading} type="submit"><Search size={16} />{loading ? 'Exploring…' : demoMode ? 'Explore example matches' : 'Find terrain analogs'}<ArrowRight size={17} /></button></div>
            </form>
            {!valid && <p className="validation" role="alert">Enter latitude from −90 to 90 and longitude from −180 to 180.</p>}
            {targets.length === 0 && <p className="validation" role="status">Choose at least one destination.</p>}
            {scaleNotice && <p className="validation" role="status">{scaleNotice}</p>}
            <p className="selection-note">{demoMode ? 'Offline mode: real ASTRAL model v2 results, precomputed for curated sites (Artemis candidates, Mars missions, Earth analog stations). Any click returns the nearest curated site; profiles do not rerank offline.' : `${scale} m/pixel · ${scale === 60 ? '7.68' : '128'} km terrain patches · ranking supplied by the API`}</p>
          </div></>}
        {panel === 'results' && <>        <aside className="results-panel" aria-label="Analog results">
          <div className="results-heading"><div><p className="eyebrow">ACROSS THE WORLDS</p><h2>Terrain matches</h2></div><span className="count">{result?.results.length ?? '—'}</span></div>
          <div className="mode-note"><Info size={16} /><p>{demoMode ? <><strong>Offline mode</strong> · Precomputed outputs of the ASTRAL model v2 for the nearest curated site. Similarity is not a safety or mission suitability assessment.</> : <><strong>Live API</strong> · Search across Earth, Moon and Mars. Similarity is not a safety or mission suitability assessment.</>}</p></div>
          {result && result.warnings.length > 0 && <div className="search-warnings" role="status">
            <strong>Coverage & data notices</strong><ul>{result.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul>
            {scale === 60 && <button onClick={() => { setScale(1000); setScaleNotice(''); }}>Search globally (1 km)</button>}
          </div>}
          <div className="result-list grouped" aria-live="polite" aria-busy={loading}>
            {loading && <div className="empty-state"><span className="loader" /><p>Looking across worlds…</p></div>}
            {error && <div className="empty-state error" role="alert"><p>{error}</p><button onClick={() => setAttempt(a => a + 1)}>Try again</button></div>}
            {!loading && !error && !result && <div className="empty-state"><Crosshair /><p>Select a supported origin to explore.</p></div>}
            {result && result.results.length === 0 && <div className="empty-state"><p>No analogs found for this location. Try another site.</p></div>}
            {result && targets.map(target => <section className="result-group" key={target} aria-label={`${bodyNames[target]} matches`}>
              <h3>{bodyNames[target]} <span>{result.results.filter(r => r.body === target).length} matches</span></h3>
              {result.results.filter(r => r.body === target).length === 0 && <p className="selection-note">No matches returned for this destination.</p>}
              {result.results.filter(r => r.body === target).map((r, i) => <ResultCard key={r.patch_id} result={r} index={i} active={r.patch_id === active?.patch_id} onSelect={() => showMatch(r.patch_id)} demo={result.demo} />)}
            </section>)}
          </div>
        </aside></>}
        {panel === 'details' && <><button className="back-button" onClick={() => setPanel('results')}><ArrowLeft size={14} />All matches</button>      {active && <section className="comparison" aria-label="Selected match details"><div className="comparison-title"><p className="eyebrow">READ THE ANALOGY</p><h2>Similar terrain.<br /><span>Different realities.</span></h2><p>{bodyNames[body]} <ArrowRight size={13} /> {active.region}</p>{result?.demo && <small>Precomputed model v2 scores for the nearest curated site.</small>}</div><RadarChart scores={active.scores} /><div className="dimension-detail"><h3>What the dimensions tell us</h3>{dimensions.map(d => <div key={d}><span>{labels[d]}</span><strong>{active.scores[d] === null ? 'No data' : `${Math.round(active.scores[d]! * 100)}% similarity`}</strong></div>)}</div><div className="limits"><Info size={18} /><h3>Where the analogy stops</h3><p>Terrain similarity does not reproduce the full environment of another world.</p><div>{Array.from(new Set([...active.not_comparable, 'gravity', body === 'moon' || active.body === 'moon' ? 'vacuum' : 'atmosphere', 'radiation'])).map(limit => <span key={limit}>{limit.replaceAll('_', ' ')}</span>)}</div></div></section>}
      {active && result && <><AnalogEvidence key={active.patch_id} match={active} result={result} /><MatchDetails active={active} result={result} /></>}
{!active && <p className="empty-state">Select a match to inspect its data.</p>}</>}
        {panel === 'suitability' && <SuitabilityPanel MapView={LunarSuitabilityMap} onSelect={location => { selectLocation(location); setView('system'); setPanel(null); }} />}
        {panel === 'sources' && <>      <section id="science" className="science"><div className="science-heading"><p className="eyebrow">GROUNDED IN PLANETARY SCIENCE</p><h2>Real worlds. Open data.</h2><p>The project uses NASA terrain data. Globe textures and relief come from NASA missions. Offline results are precomputed outputs of our model v2; live results and suitability maps come from the connected data service.</p></div><div className="sources">{sources.map(s => <a key={s.body} href={s.href} target="_blank" rel="noreferrer"><span>{s.body}<ExternalLink size={13} /></span><h3>{s.title}</h3><p>{s.text}</p></a>)}</div></section><a className="resource-link" href="https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/?tab=resources" target="_blank" rel="noreferrer">Challenge resources <ExternalLink size={14} /></a></>}
      </MapPanel>}
    </main>
  </div>;
}
