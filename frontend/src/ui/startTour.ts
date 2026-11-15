/** "Start here" tour: shown once per browser; replayable from the header. */
export const TOUR_KEY = 'astral-start-tour-v1';
export const TOUR_STEPS = [
  { title: '1 · Pick a base site', text: 'Open Base suitability and choose a NASA candidate or a recommended zone on the Moon or Mars.', action: 'Open Base suitability', panel: 'suitability' },
  { title: '2 · Find Earth analogs', text: 'Press “Find Earth analogs →” on that site. Our network searches every Earth patch for terrain twins.', action: 'Open Base suitability', panel: 'suitability' },
  { title: '3 · Read the analogy', text: 'Open a match: the card scores seven dimensions, and “Where the analogy stops” shows what Earth cannot reproduce.', action: 'Open match details', panel: 'details' },
] as const;
export type TourPanel = (typeof TOUR_STEPS)[number]['panel'];

export function tourSeen(storage: Pick<Storage, 'getItem'> | undefined) {
  try { return storage?.getItem(TOUR_KEY) === 'done'; } catch { return false; }
}
export function markTourSeen(storage: Pick<Storage, 'setItem'> | undefined) {
  try { storage?.setItem(TOUR_KEY, 'done'); } catch { /* private mode: the tour may show again */ }
}
