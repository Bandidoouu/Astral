import assert from 'node:assert/strict';
import test from 'node:test';
import { markTourSeen, tourSeen, TOUR_STEPS, TOUR_KEY } from './startTour.ts';

test('tour has three steps covering base site → Earth analogs → the analogy card', () => {
  assert.equal(TOUR_STEPS.length, 3);
  assert.deepEqual(TOUR_STEPS.map(s => s.panel), ['suitability', 'suitability', 'details']);
});

test('tour shows once, survives blocked storage', () => {
  const store = new Map<string, string>();
  const storage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); } };
  assert.equal(tourSeen(storage), false);
  markTourSeen(storage);
  assert.equal(store.get(TOUR_KEY), 'done');
  assert.equal(tourSeen(storage), true);
  const blocked = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } };
  assert.equal(tourSeen(blocked), false);
  assert.doesNotThrow(() => markTourSeen(blocked));
});
