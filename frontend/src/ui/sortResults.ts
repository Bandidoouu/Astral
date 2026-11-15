import type { Analog } from '../api/types';

/** How the result list is ordered.
 * terrain: the order returned by the search (our network + terrain formula, RRF) — default.
 * overall: the SAME retrieved results re-sorted by their profile score (seven dimensions,
 * weights of the active mission profile), keeping each destination body grouped. */
export type SortMode = 'terrain' | 'overall';

export function sortResults(results: Analog[], mode: SortMode): Analog[] {
  if (mode === 'terrain') return results;
  const bodies: string[] = [];
  for (const r of results) if (!bodies.includes(r.body)) bodies.push(r.body);
  return bodies.flatMap(body => results
    .map((r, i) => ({ r, i }))
    .filter(x => x.r.body === body)
    .sort((a, b) => b.r.score - a.r.score || a.i - b.i)   // ties keep the terrain order
    .map(x => x.r));
}
