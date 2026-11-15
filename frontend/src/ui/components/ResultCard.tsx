import { ArrowUpRight, MapPin } from 'lucide-react';
import type { Analog, Dimension } from '../../api/types';
import { bodyColors } from '../../api/bodies';

export const dimensions: Dimension[] = ['terrain', 'operations', 'thermal', 'albedo', 'ice', 'soil', 'aridity'];
export const labels: Record<Dimension, string> = { terrain: 'Terrain', operations: 'Operations', thermal: 'Thermal', albedo: 'Albedo', ice: 'Ice', soil: 'Rock / dust', aridity: 'Aridity' };
export function RadarChart({ scores }: { scores: Analog['scores'] }) {
  const axes = dimensions.map((_, i) => {
    const angle = i * Math.PI * 2 / dimensions.length - Math.PI / 2;
    return [120 + Math.cos(angle) * 78, 110 + Math.sin(angle) * 78];
  });
  return <svg viewBox="0 0 240 220" role="img" aria-label="Similarity by dimension. Missing dimensions are omitted." className="radar">
    {[0.33, 0.66, 1].map(scale => <polygon key={scale} points={axes.map(([x, y]) => `${120 + (x - 120) * scale},${110 + (y - 110) * scale}`).join(' ')} fill="none" stroke="#34434b" />)}
    {axes.map(([x, y], i) => <line key={i} x1="120" y1="110" x2={x} y2={y} stroke="#34434b" />)}
    {dimensions.map((d, i) => {
      const value = scores[d];
      const [ax, ay] = axes[i];
      return <g key={d}>
        {value !== null && <><line x1="120" y1="110" x2={120 + (ax - 120) * value} y2={110 + (ay - 110) * value} stroke="#c9f68b" strokeWidth="3" /><circle cx={120 + (ax - 120) * value} cy={110 + (ay - 110) * value} r="4" fill="#c9f68b" /></>}
        <text x={120 + (ax - 120) * 1.22} y={114 + (ay - 110) * 1.22} textAnchor="middle">{labels[d]}</text>
      </g>;
    })}
  </svg>;
}

export default function ResultCard({ result, index, active, onSelect, demo }: {
  result: Analog; index: number; active: boolean; onSelect: () => void; demo: boolean;
}) {
  return <button className={`result-card ${active ? 'active' : ''}`} onClick={onSelect} aria-pressed={active}>
    <div className="result-top"><span className="rank">{String(index + 1).padStart(2, '0')}</span><span className="body-tag" style={{ color: bodyColors[result.body] }}>{result.body}</span><ArrowUpRight size={16} /></div>
    <div className="result-title"><h3>{result.region}</h3><strong>{Math.round(result.score * 100)}<small>%</small></strong></div>
    <div className="result-coords"><MapPin size={11} />{result.lat.toFixed(2)}°, {result.lon.toFixed(2)}° <span>{demo ? 'Illustrative score' : 'Weighted similarity'}</span></div>
    <p className="card-scale">{result.scale_m === 1000 ? '1 km/pixel · 128 km patch' : '60 m/pixel · 7.68 km patch'}</p>
    <div className="score-bars">{dimensions.map(d => <div key={d}><span>{labels[d]}</span><div className="track">{result.scores[d] !== null && <i style={{ width: `${result.scores[d]! * 100}%` }} />}</div><b>{result.scores[d] === null ? 'No data' : `${Math.round(result.scores[d]! * 100)}%`}</b></div>)}</div>
  </button>;
}
