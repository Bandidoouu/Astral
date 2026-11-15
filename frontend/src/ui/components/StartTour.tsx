import { useState } from 'react';
import { X } from 'lucide-react';
import { TOUR_STEPS } from '../startTour';
import type { TourPanel } from '../startTour';

/** Three short steps; Skip closes it, the header "Start here" button reopens it. */
export default function StartTour({ onClose, onOpen }: { onClose: () => void; onOpen: (panel: TourPanel) => void }) {
  const [step, setStep] = useState(0);
  const s = TOUR_STEPS[step];
  const last = step === TOUR_STEPS.length - 1;
  return <aside className="start-tour" role="dialog" aria-label="Start here">
    <div className="start-tour-head"><span className="eyebrow">START HERE · {step + 1}/{TOUR_STEPS.length}</span>
      <button className="icon-button" aria-label="Close tour" onClick={onClose}><X size={14} /></button></div>
    <h3>{s.title}</h3>
    <p>{s.text}</p>
    <div className="start-tour-actions">
      <button className="inline-action" onClick={() => onOpen(s.panel)}>{s.action}</button>
      <span className="start-tour-nav">
        <button className="text-button" onClick={onClose}>Skip</button>
        {step > 0 && <button className="text-button" onClick={() => setStep(step - 1)}>Back</button>}
        <button className="search-launcher" onClick={() => (last ? onClose() : setStep(step + 1))}>{last ? 'Done' : 'Next'}</button>
      </span>
    </div>
  </aside>;
}
