import type { Body, Profile } from '../../api/types';
import { missions } from '../missions';
import { labels } from './ResultCard';

export default function MissionPanel({ body, profile, demo, onChoose }: { body: Body; profile: Profile; demo: boolean; onChoose: (profile: Profile) => void }) {
  return <div className="mission-panel">
    <p className="eyebrow">EARTH AS A FIELD LABORATORY</p>
    <h3>What are you preparing for?</h3>
    <p>Choose an investigation, search for analogs, then examine the evidence and its limits.</p>
    <p className="mission-notice">{body === 'earth' ? 'Earth is your origin. Compare this field location with the Moon and Mars.' : 'This search will target Earth analogs for your selected planetary origin.'}</p>
    {demo && <p className="mission-notice">Offline mode: at Global (1 km) the profile recomputes each match's profile score from the stored dimension scores; the default order (terrain similarity) does not depend on the profile; choose Sort by: Overall score to rank by it. At 60 m, the curated sites recompute the score the same way.</p>}
    <div className="mission-cards">{missions.map(m => <button key={m.id} disabled={m.id === 'astrobiology' && body !== 'mars'} aria-pressed={profile === m.id} onClick={() => onChoose(m.id)}>
      <span className="eyebrow">{m.id === profile ? 'CURRENT MISSION' : m.id.toUpperCase()}</span><strong>{m.title}</strong><span>{m.question}</span>
      <small>Investigate: {m.focus.map(d => labels[d]).join(' · ')}</small>
      {m.id === 'astrobiology' && body !== 'mars' && <small>Select a Mars origin to use this profile.</small>}
    </button>)}</div>
  </div>;
}
