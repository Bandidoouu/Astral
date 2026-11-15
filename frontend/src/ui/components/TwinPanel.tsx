import { useEffect, useMemo, useState } from 'react';
import { loadPatchCatalog } from '../../api/client';
import { earthRegions, findHomePatch } from '../homePatch';
import type { HomePatch, PatchCatalog } from '../homePatch';

/** "Find your planetary twin": browser location or a typed region → nearest valid 1 km Earth
 * patch → search toward the Moon and Mars. The location never leaves this browser. */
export default function TwinPanel({ gravity, onGravity, onFound }: {
  gravity: boolean; onGravity: (v: boolean) => void; onFound: (home: HomePatch, label: string) => void;
}) {
  const [cat, setCat] = useState<PatchCatalog | null>(null);
  const [status, setStatus] = useState('');
  const [place, setPlace] = useState('');
  useEffect(() => {
    const c = new AbortController();
    loadPatchCatalog(c.signal).then(d => setCat(d as unknown as PatchCatalog)).catch(() => setStatus('Could not load the patch catalog.'));
    return () => c.abort();
  }, []);
  const regions = useMemo(() => (cat ? earthRegions(cat) : []), [cat]);
  function useLocation() {
    if (!cat) return;
    if (!('geolocation' in navigator)) { setStatus('This browser has no location service. Type a place instead.'); return; }
    setStatus('Asking your browser for your location…');
    navigator.geolocation.getCurrentPosition(
      pos => { setStatus(''); onFound(findHomePatch(cat, pos.coords.latitude, pos.coords.longitude), 'your location'); },
      err => setStatus(err.code === err.PERMISSION_DENIED ? 'Location permission denied. Type a place instead.' : 'Location unavailable. Type a place instead.'),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
  }
  function usePlace() {
    if (!cat) return;
    const r = regions.find(x => x.name.toLowerCase() === place.trim().toLowerCase())
      ?? regions.find(x => x.name.toLowerCase().startsWith(place.trim().toLowerCase()));
    if (!r) { setStatus('Place not found. Pick one of the suggested region names.'); return; }
    setStatus(''); onFound(findHomePatch(cat, r.lat, r.lon), r.name);
  }
  return <section className="twin-panel" aria-label="Find your planetary twin">
    <p className="eyebrow">FIND YOUR PLANETARY TWIN</p>
    <h2>Where on the Moon and Mars looks like home?</h2>
    <p className="selection-note">Your location stays in this browser: it is not stored or sent anywhere.</p>
    <button className="search-launcher" disabled={!cat} onClick={useLocation}>Use my location</button>
    <form onSubmit={e => { e.preventDefault(); usePlace(); }} className="twin-place">
      <label>OR TYPE A PLACE (state / province, country)
        <input list="twin-regions" value={place} onChange={e => setPlace(e.target.value)} placeholder="e.g. Nuevo León, Mexico" aria-label="Place" />
      </label>
      <datalist id="twin-regions">{regions.map(r => <option key={r.name} value={r.name} />)}</datalist>
      <button className="text-button" type="submit" disabled={!cat || !place.trim()}>Find twin</button>
    </form>
    <label className="twin-gravity"><input type="checkbox" checked={gravity} onChange={e => onGravity(e.target.checked)} /> Gravity-scaled windows (Moon 6×, Mars 2.6×)</label>
    {status && <p className="selection-note" role="status">{status}</p>}
  </section>;
}
