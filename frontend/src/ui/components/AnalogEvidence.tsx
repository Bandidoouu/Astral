import { useState } from 'react';
import { Download } from 'lucide-react';
import type { Analog, Dimension, SearchResult } from '../../api/types';
import { dimensionContext, missionById } from '../missions';
import { dimensions, labels } from './ResultCard';

export default function AnalogEvidence({ match, result }: { match: Analog; result: SearchResult }) {
  const mission = missionById(result.query.profile);
  const [dimension, setDimension] = useState<Dimension>('terrain');
  const score = match.scores[dimension];
  const available = dimensions.filter(d => match.scores[d] !== null);
  function downloadBrief() {
    const lines = ['# ASTRAL analog investigation brief', '', result.precomputed ? `**PRECOMPUTED — real ASTRAL model ${result.precomputed.model} outputs for ${result.precomputed.site ?? 'a curated site'}, not a validated site recommendation.**` : result.demo ? '**ILLUSTRATIVE DEMO — fixed examples, not validated findings.**' : '**API-provided comparison — not a validated site recommendation.**', '',
      `Mission: ${mission.title}`, `Question: ${mission.question}`,
      `Origin: ${result.query.body} (${result.query.lat}, ${result.query.lon})`,
      `Match: ${match.region} — ${match.body} (${match.lat}, ${match.lon})`,
      `Patch: ${match.patch_id}; scale: ${match.scale_m} m/pixel; method: ${result.query.method}`, '',
      '## Reported evidence', ...dimensions.map(d => `- ${labels[d]}: ${match.scores[d] === null ? 'No data' : match.scores[d]}; weight: ${match.weights_used?.[d] ?? 'not supplied'}`), '',
      '## Site attributes (raw API fields)', 'Origin: ' + JSON.stringify(result.query.attributes ?? null), 'Match: ' + JSON.stringify(match.attributes), '',
      '## Investigation to design', mission.exercise, 'This is a proposed exercise, not proof that the site is suitable.', '',
      '## Limits and open questions', mission.limitation, ...match.not_comparable.map(limit => '- ' + limit.replaceAll('_', ' ')),
      '- Verify data provenance, local geology, access, permissions and field conditions before any field study.',
      '- No cave, subsurface or biological measurements are supplied by these scores.', ...result.warnings.map(w => '- ' + w), '',
      '## Data context', 'Challenge: https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/',
      'Earthdata: https://search.earthdata.nasa.gov/', 'LRO: https://pds-geosciences.wustl.edu/missions/lro/',
      'Mars PDS: https://pds-geosciences.wustl.edu/missions/mgs/',
      'These are discovery portals; per-patch dataset identifiers must be supplied by the data service.', ''];
    const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = 'astral-analog-brief.md'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <section className="analog-evidence" aria-label="Mission evidence">
    <p className="eyebrow">WHY THIS ANALOG?</p><h3>{mission.title}</h3><p>{mission.question}</p>
    <p className="evidence-coverage">{available.length} / {dimensions.length} dimensions have data{result.demo ? ' in this illustrative example' : ''}. Missing data is not zero similarity.</p>
    <div className="evidence-tabs" aria-label="Evidence dimensions">{dimensions.map(d => <button key={d} aria-pressed={dimension === d} onClick={() => setDimension(d)}>{labels[d]}{match.scores[d] === null ? ' · —' : ''}</button>)}</div>
    <div className="evidence-explanation" aria-live="polite"><strong>{labels[dimension]}: {score === null ? 'No data' : `${Math.round(score * 100)}% ${result.demo ? 'illustrative similarity' : 'reported similarity'}`}</strong>
      <p>{dimensionContext[dimension]}</p><p>{score === null ? 'This response provides no evidence for this dimension. It cannot support a match claim.' : 'This score describes one dimension; it does not validate the site or explain the entire ranking.'}</p>
      <p>Weight supplied: {match.weights_used?.[dimension] == null ? 'Not supplied' : `${(match.weights_used[dimension]! * 100).toFixed(1)}%`}</p>
    </div>
    <h4>Investigation to design</h4><p>{mission.exercise}</p><p className="mission-notice">{mission.limitation}</p>
    <p>Geology, caves, subsurface conditions and biology need independent evidence; these scores do not establish them.</p>
    <button className="brief-download" onClick={downloadBrief}><Download size={14} />Download investigation brief</button>
  </section>;
}
