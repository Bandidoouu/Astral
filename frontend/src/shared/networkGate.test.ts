import assert from 'node:assert/strict';
import test from 'node:test';
import { beginForeground, createBackgroundQueue, foregroundBusy } from './networkGate.ts';

test('background tasks wait while a foreground request is pending and then run one at a time', async () => {
  const log: string[] = [];
  const done = beginForeground();
  const q = createBackgroundQueue();
  let running = 0, maxRunning = 0;
  for (const name of ['a', 'b']) q.add(async () => {
    running++; maxRunning = Math.max(maxRunning, running);
    log.push(name); await new Promise(r => setTimeout(r, 5)); running--;
  });
  await new Promise(r => setTimeout(r, 20));
  assert.deepEqual(log, [], 'nothing runs while the foreground holds the gate');
  assert.ok(foregroundBusy());
  done();
  await new Promise(r => setTimeout(r, 40));
  assert.deepEqual(log, ['a', 'b']);
  assert.equal(maxRunning, 1);
});
