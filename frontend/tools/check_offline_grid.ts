// Compares the offline 1 km grid with the live API on random clicks and profiles.
//   node frontend/tools/check_offline_grid.ts http://127.0.0.1:8000 300
import { readdirSync, readFileSync } from 'node:fs';
import { gridSearch } from '../src/mocks/offlineGrid.ts';
import type { OfflineBlocks, OfflineCatalog } from '../src/mocks/offlineGrid.ts';
import type { Body, Profile } from '../src/api/types.ts';

const [api = 'http://127.0.0.1:8000', nArg = '300', mode = 'same_size'] = process.argv.slice(2);
const dir = new URL(`../public/data/offline1km${mode === 'gravity_scaled' ? '_gravity' : ''}/`, import.meta.url);
const cat = JSON.parse(readFileSync(new URL('catalog.json', dir), 'utf8')) as OfflineCatalog;
const blocks: OfflineBlocks = {};
for (const f of readdirSync(dir)) {
  const m = /^results_(\w+)_(\d+)\.bin$/.exec(f);
  if (!m) continue;
  const buf = readFileSync(new URL(f, dir));
  blocks[`${m[1]}/${Number(m[2])}`] = new Uint16Array(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
}
const profiles: Profile[] = ['general', 'rover', 'isru', 'habitat', 'eva', 'astrobiology'];
let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
let ok = 0, orderBad = 0, scoreBad = 0, pctBad = 0, warnBad = 0;
for (let i = 0; i < Number(nArg); i++) {
  const body = (['earth', 'moon', 'mars'] as Body[])[i % 3];
  const lat = Math.round((Math.asin(2 * rnd() - 1) * 180 / Math.PI) * 1e4) / 1e4, lon = Math.round((rnd() * 360 - 180) * 1e4) / 1e4;
  const profile = body === 'mars' ? profiles[i % 6] : profiles[i % 5];
  const targets = (['earth', 'moon', 'mars'] as Body[]).filter(b => b !== body);
  const q = { body, lat, lon, profile, k: 10, scale_m: 1000 as const, target_bodies: targets };
  const live = await (await fetch(`${api}/api/similar`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...q, method: 'rrf', scale_mode: mode }) })).json();
  const off = gridSearch({ ...q, scale_mode: mode as 'same_size' | 'gravity_scaled' }, cat, blocks);
  if (off.results.some((r, j) => r.window_km !== live.results[j]?.window_km)) { orderBad++; continue; }
  const same = JSON.stringify(off.results.map(r => r.patch_id)) === JSON.stringify(live.results.map((r: { patch_id: string }) => r.patch_id));
  if (!same) { orderBad++; continue; }
  let bad = false;
  off.results.forEach((r, j) => {
    if (Math.abs(r.score - live.results[j].score) > 1.0001e-4) { scoreBad++; bad = true; }
    if (Math.round(r.score * 100) !== Math.round(live.results[j].score * 100)) { pctBad++; bad = true; }
  });
  if (off.warnings.length - 1 !== live.warnings.length) warnBad++;
  if (!bad) ok++;
}
console.log({ mode, queries: Number(nArg), fully_identical: ok, order_mismatch: orderBad, score_off: scoreBad, shown_pct_off: pctBad, warning_count_diff: warnBad });
