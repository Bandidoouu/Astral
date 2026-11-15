/** Instagram-style share card (1080×1350, 4:5) drawn in the browser from real NASA mosaics
 * (the globe textures this site already serves). Nothing is uploaded: the image is a local file. */
export interface ShareCardData {
  homeRegion: string; homeLat: number; homeLon: number;
  marsName: string; marsLat: number; marsLon: number;
  moonName?: string;
  stats: { label: string; home: string; twin: string }[];
  terrainPct: number; url: string;
}

const W = 1080, H = 1350;

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => { const i = new Image(); i.onload = () => resolve(i); i.onerror = reject; i.src = src; });
}
/** Crop of an equirectangular mosaic around (lat, lon), drawn as a circle. */
function drawCrop(ctx: CanvasRenderingContext2D, img: HTMLImageElement, lat: number, lon: number, spanDeg: number, cx: number, cy: number, r: number, ring: string) {
  const sx = ((lon + 180) / 360) * img.width, sy = ((90 - lat) / 180) * img.height;
  const sw = (spanDeg / 360) * img.width, sh = sw;
  ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.clip();
  ctx.drawImage(img, sx - sw / 2, sy - sh / 2, sw, sh, cx - r, cy - r, 2 * r, 2 * r);
  const g = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 0.2, cx, cy, r); g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(1, 'rgba(0,0,0,0.45)');
  ctx.fillStyle = g; ctx.fillRect(cx - r, cy - r, 2 * r, 2 * r); ctx.restore();
  ctx.lineWidth = 8; ctx.strokeStyle = ring; ctx.beginPath(); ctx.arc(cx, cy, r + 6, 0, Math.PI * 2); ctx.stroke();
}
function fit(ctx: CanvasRenderingContext2D, text: string, max: number, size: number, weight = 700) {
  let s = size; do { ctx.font = `${weight} ${s}px Inter, Segoe UI, system-ui, sans-serif`; s -= 2; } while (ctx.measureText(text).width > max && s > 20);
}

export async function renderShareCard(d: ShareCardData, base: string): Promise<Blob> {
  const canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d')!;
  const bg = ctx.createLinearGradient(0, 0, W, H); bg.addColorStop(0, '#0b1119'); bg.addColorStop(0.55, '#1a1230'); bg.addColorStop(1, '#3a1a12');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < 260; i++) { ctx.fillStyle = `rgba(255,255,255,${Math.random() * 0.7 + 0.2})`; ctx.beginPath(); ctx.arc(Math.random() * W, Math.random() * H, Math.random() * 1.8 + 0.4, 0, Math.PI * 2); ctx.fill(); }
  ctx.textBaseline = 'alphabetic'; ctx.fillStyle = '#c9f68b'; ctx.font = '700 34px Inter, Segoe UI, system-ui, sans-serif';
  ctx.fillText('A S T R A L', 70, 100); ctx.fillStyle = '#9aa9b9'; ctx.font = '500 22px Consolas, monospace'; ctx.fillText('PLANETARY ANALOG EXPLORER', 70, 134);
  ctx.fillStyle = '#e8ecdf'; fit(ctx, 'My home’s twin on Mars', W - 140, 64, 800); ctx.fillText('My home’s twin on Mars', 70, 236);
  const [earth, mars] = await Promise.all([loadImage(`${base}textures/earth/color_4k.jpg`), loadImage(`${base}textures/mars/color_4k.jpg`)]);
  drawCrop(ctx, earth, d.homeLat, d.homeLon, 6, 300, 470, 170, '#2f8cff');
  drawCrop(ctx, mars, d.marsLat, d.marsLon, 12, 780, 470, 170, '#ff7a3d');
  ctx.setLineDash([16, 14]); ctx.lineWidth = 6; ctx.strokeStyle = '#c9f68b'; ctx.beginPath(); ctx.moveTo(470, 470); ctx.quadraticCurveTo(540, 330, 610, 470); ctx.stroke(); ctx.setLineDash([]);
  ctx.textAlign = 'center'; ctx.fillStyle = '#9fc8ff'; fit(ctx, d.homeRegion, 380, 34, 700); ctx.fillText(d.homeRegion, 300, 700);
  ctx.fillStyle = '#ffb08a'; fit(ctx, d.marsName, 380, 34, 700); ctx.fillText(d.marsName, 780, 700);
  ctx.fillStyle = '#c9f68b'; ctx.font = '800 120px Inter, Segoe UI, system-ui, sans-serif'; ctx.fillText(`${d.terrainPct}%`, W / 2, 850);
  ctx.fillStyle = '#c3c2b7'; ctx.font = '500 30px Inter, Segoe UI, system-ui, sans-serif'; ctx.fillText('terrain similarity · our neural network', W / 2, 896);
  ctx.textAlign = 'left'; let y = 955;
  ctx.font = '600 24px Consolas, monospace'; ctx.fillStyle = '#9aa9b9'; ctx.fillText('', 70, y);
  ctx.fillStyle = '#9fc8ff'; ctx.fillText('HOME', 520, y); ctx.fillStyle = '#ffb08a'; ctx.fillText('MARS TWIN', 790, y); y += 42;
  for (const s of d.stats.slice(0, 6)) {
    ctx.fillStyle = '#c3c2b7'; ctx.font = '500 28px Inter, Segoe UI, system-ui, sans-serif'; ctx.fillText(s.label, 70, y);
    ctx.fillStyle = '#e8ecdf'; ctx.font = '700 28px Inter, Segoe UI, system-ui, sans-serif'; ctx.fillText(s.home, 520, y); ctx.fillText(s.twin, 790, y); y += 40;
  }
  if (d.moonName) { ctx.fillStyle = '#e6e3da'; ctx.font = '500 26px Inter, Segoe UI, system-ui, sans-serif'; ctx.fillText(`On the Moon: ${d.moonName}`, 70, y + 4); }
  ctx.fillStyle = '#c9f68b'; ctx.font = '700 30px Inter, Segoe UI, system-ui, sans-serif'; ctx.fillText('Find yours →', 70, H - 70);
  ctx.fillStyle = '#e8ecdf'; ctx.font = '600 28px Consolas, monospace';
  ctx.fillText(new URL(d.url).host + new URL(d.url).pathname.replace(/\/$/, ''), 300, H - 70);
  ctx.fillStyle = '#9aa9b9'; ctx.font = '400 17px Inter, Segoe UI, system-ui, sans-serif'; ctx.fillText('Imagery: NASA Blue Marble, Viking MDIM · Radiation: UNSCEAR, MSL/RAD · Not a mission suitability rating', 70, H - 28);
  return new Promise((resolve, reject) => canvas.toBlob(b => (b ? resolve(b) : reject(new Error('Could not render the card'))), 'image/png'));
}

/** Kelvin → °C text, never inventing missing values. */
export const celsius = (k: number | null | undefined) => (k == null ? 'No data' : `${Math.round(k - 273.15)} °C`);
