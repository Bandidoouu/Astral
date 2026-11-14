import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { X } from 'lucide-react';

/** Modeless inspector: the map stays interactive and Escape returns to its trigger. */
export default function MapPanel({ id, title, side = 'right', onClose, children }: {
  id: string; title: string; side?: 'left' | 'right'; onClose: () => void; children: ReactNode;
}) {
  const container = useRef<HTMLElement>(null);
  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const panel = container.current;
    panel?.focus();
    return () => {
      if (panel?.contains(document.activeElement) || document.activeElement === document.body) trigger?.focus();
    };
  }, [id]);

  return <section ref={container} id={id} className={`map-panel map-panel-${side}`} aria-labelledby={`${id}-title`} tabIndex={-1}
    onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); onClose(); } }}>
    <header className="map-panel-heading"><h2 id={`${id}-title`}>{title}</h2>
      <button className="icon-button" aria-label={`Close ${title}`} onClick={onClose}><X size={16} /></button>
    </header>
    <div className="map-panel-content">{children}</div>
  </section>;
}
