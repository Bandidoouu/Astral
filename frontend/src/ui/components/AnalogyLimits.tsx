import { useEffect, useState } from 'react';
import { Info } from 'lucide-react';
import type { Analog, Body, Location } from '../../api/types';
import { FACTS, pressureAtElevationHpa } from '../planetFacts';
import { earthElevationM } from '../earthElevation';

const names: Record<Body, string> = { earth: 'Earth', moon: 'Moon', mars: 'Mars' };
const fmt = (n: number, d = 0) => n.toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d });

/** "Where the analogy stops": measured physical context of each world, with sources.
 * The Earth column is the matched (or origin) Earth site; its pressure comes from its
 * elevation with the standard barometric formula — the closest Earth gets. */
export default function AnalogyLimits({ origin, match }: { origin: Location; match: Analog }) {
  const earthSite: Location | null = match.body === 'earth' ? match : origin.body === 'earth' ? origin : null;
  const worlds = [origin.body, match.body].filter((b, i, a) => b !== 'earth' && a.indexOf(b) === i);
  const [elev, setElev] = useState<number | null>(null);
  useEffect(() => {
    let live = true; setElev(null);
    if (earthSite) earthElevationM(earthSite.lat, earthSite.lon).then(v => { if (live) setElev(v); }).catch(() => {});
    return () => { live = false; };
  }, [earthSite?.lat, earthSite?.lon]);
  const rows: { label: string; key: 'gravity' | 'pressure' | 'radiation' | 'day' }[] = [
    { label: 'Gravity', key: 'gravity' }, { label: 'Surface pressure', key: 'pressure' },
    { label: 'Surface radiation dose', key: 'radiation' }, { label: 'Length of day', key: 'day' },
  ];
  const sources = Array.from(new Set([...worlds, ...(earthSite ? ['earth' as Body] : [])].flatMap(b =>
    rows.map(r => FACTS[b][r.key]?.source).filter(Boolean) as string[])));
  return <div className="limits">
    <Info size={18} /><h3>Where the analogy stops</h3>
    <p>Terrain similarity does not reproduce the full environment of another world.</p>
    <table className="limits-table"><thead><tr><th scope="col"></th>{worlds.map(b => <th key={b} scope="col">{names[b]}</th>)}{earthSite && <th scope="col">This Earth site</th>}</tr></thead>
      <tbody>{rows.map(r => <tr key={r.key}><th scope="row">{r.label}</th>
        {worlds.map(b => <td key={b}>{FACTS[b][r.key]?.value ?? <em>pending citation</em>}</td>)}
        {earthSite && <td>{r.key === 'pressure'
          ? (elev === null ? '…' : <>≈ {fmt(pressureAtElevationHpa(elev))} hPa at {fmt(Math.max(0, elev))} m <small>(closest Earth gets)</small></>)
          : FACTS.earth[r.key]?.value ?? <em>pending citation</em>}</td>}
      </tr>)}</tbody></table>
    <div className="limits-tags">{['dust_and_wind', 'subsurface'].filter(l => match.not_comparable.includes(l)).map(l => <span key={l}>{l.replaceAll('_', ' ')}</span>)}</div>
    <p className="limits-note">Dust/wind and subsurface: not modeled; future work.</p>
    <details className="limits-sources"><summary>Sources</summary><ul>{sources.map(s => <li key={s}>{s}</li>)}
      {earthSite && <li>Earth site pressure: standard barometric formula (ISA troposphere) at the site elevation from NASA SRTMGL30 (~10 km grid).</li>}</ul></details>
  </div>;
}
