/** Shared network priority. Foreground work (a search waiting for its results) holds the
 * gate; background downloads (globe layers not on screen yet) wait until it is free and then
 * run one at a time, so they never compete with what the user is waiting for. */
let busy = 0;
let waiters: (() => void)[] = [];

export function beginForeground(): () => void {
  busy++;
  let done = false;
  return () => {
    if (done) return;
    done = true;
    busy = Math.max(0, busy - 1);
    if (busy === 0) { const w = waiters; waiters = []; w.forEach(f => f()); }
  };
}
export function foregroundBusy() { return busy > 0; }
export function whenIdle(): Promise<void> {
  return busy === 0 ? Promise.resolve() : new Promise(resolve => waiters.push(resolve));
}

/** Runs background tasks one after another, each only when the foreground is idle. */
export function createBackgroundQueue() {
  let chain: Promise<void> = Promise.resolve();
  let cancelled = false;
  return {
    add(task: () => Promise<unknown>) {
      chain = chain.then(async () => {
        if (cancelled) return;
        await whenIdle();
        if (cancelled) return;
        try { await task(); } catch { /* the task reports its own errors */ }
      });
    },
    cancel() { cancelled = true; },
  };
}
