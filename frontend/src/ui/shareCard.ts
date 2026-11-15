/** Minimal share image (1080×1350, 4:5) drawn in the browser. Whole planets to scale, each an
 * orthographic projection of its NASA mosaic (the globe textures this site already serves),
 * centered on the place. Nothing is uploaded: the image is a local file. */
export interface ShareCardData {
  homeRegion: string; homeLat: number; homeLon: number;
  marsName: string; marsLat: number; marsLon: number;
  moonName?: string; moonLat?: number; moonLon?: number;
  terrainPct: number;
  /** At most three sourced facts, shown as pills (e.g. "0.38 g"). */
  pills: string[];
}

const W = 1080, H = 1350;
/** Fixed public address shown on the image (never the current page address). */
export const PUBLIC_SITE = 'bandidoouu.github.io/Astral';
export const FOOTER_LINK = `find yours → ${PUBLIC_SITE}`;
export const FOOTER_NOTE = 'terrain similarity by a neural network · not a habitability rating';
export const CREDITS = 'imagery: nasa blue marble · viking mdim (mars trek) · lroc wac (svs cgi moon kit)';
/** Radii relative to Earth (NASA Planetary Fact Sheets, volumetric mean radius). */
export const SCALE = { earth: 1, mars: 0.532, moon: 0.273 } as const;
const FONT = 'Inter, "Segoe UI", Arial, sans-serif';
const MONO = 'Consolas, monospace';

/** Three sourced facts at most: Mars gravity relative to Earth, Mars surface pressure, radiation ratio. */
export function defaultPills() {
  return [`${(3.73 / 9.82).toFixed(2)} g`, '6 hPa', `${Math.round(640 / 8)}× radiation`];
}
/** "Nuevo León, Mexico" → "nuevo león, mx"; IAU names lower-cased. */
const CC: Record<string, string> = { mexico: 'mx', 'united states of america': 'us', usa: 'us', canada: 'ca', chile: 'cl', peru: 'pe', argentina: 'ar', china: 'cn', mongolia: 'mn', russia: 'ru', india: 'in', australia: 'au', brazil: 'br', spain: 'es', namibia: 'na', algeria: 'dz', egypt: 'eg', iran: 'ir', 'saudi arabia': 'sa', 'south africa': 'za' };
export function shortPlace(name: string) {
  const parts = name.split(',').map(p => p.trim());
  if (parts.length >= 2) {
    const c = parts[parts.length - 1].toLowerCase();
    return `${parts.slice(0, -1).join(', ')}, ${CC[c] ?? c}`.toLowerCase();
  }
  return name.toLowerCase();
}

/** IAU name as given; an unnamed site stays honest but short ("unnamed site, moon"). */
export function siteLabel(name: string, body: string) {
  return /^an unnamed site/i.test(name) ? `unnamed site, ${body}` : name.toLowerCase();
}

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => { const i = new Image(); i.onload = () => resolve(i); i.onerror = reject; i.src = src; });
}
function pixels(img: HTMLImageElement) {
  const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
  const x = c.getContext('2d', { willReadFrequently: true })!; x.drawImage(img, 0, 0);
  return { w: img.width, h: img.height, data: x.getImageData(0, 0, img.width, img.height).data };
}
/** Whole disk, orthographic projection centered on (lat0, lon0). */
function drawPlanet(ctx: CanvasRenderingContext2D, tex: ReturnType<typeof pixels>, lat0: number, lon0: number, cx: number, cy: number, r: number) {
  const size = Math.ceil(2 * r), out = ctx.createImageData(size, size);
  const p0 = lat0 * Math.PI / 180, l0 = lon0 * Math.PI / 180, sp0 = Math.sin(p0), cp0 = Math.cos(p0);
  for (let j = 0; j < size; j++) for (let i = 0; i < size; i++) {
    const x = (i + 0.5 - r) / r, y = (r - j - 0.5) / r, rho2 = x * x + y * y;
    if (rho2 > 1) continue;
    const cz = Math.sqrt(1 - rho2);
    const lat = Math.asin(cz * sp0 + y * cp0);
    const lon = l0 + Math.atan2(x, cz * cp0 - y * sp0);
    const u = ((((lon * 180 / Math.PI) + 180) % 360 + 360) % 360) / 360, v = (90 - lat * 180 / Math.PI) / 180;
    const k = (Math.min(tex.h - 1, Math.floor(v * tex.h)) * tex.w + Math.min(tex.w - 1, Math.floor(u * tex.w))) * 4;
    const shade = 0.55 + 0.45 * cz, o = (j * size + i) * 4;
    out.data[o] = tex.data[k] * shade; out.data[o + 1] = tex.data[k + 1] * shade; out.data[o + 2] = tex.data[k + 2] * shade;
    out.data[o + 3] = rho2 > 0.985 ? 255 * (1 - rho2) / 0.015 : 255;
  }
  const tmp = document.createElement('canvas'); tmp.width = size; tmp.height = size; tmp.getContext('2d')!.putImageData(out, 0, 0);
  ctx.drawImage(tmp, cx - r, cy - r);
}
function marker(ctx: CanvasRenderingContext2D, x: number, y: number, ring: number) {
  ctx.strokeStyle = '#c9f68b'; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y, ring, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = '#c9f68b'; ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2); ctx.fill();
}

export async function renderShareCard(d: ShareCardData, base: string): Promise<Blob> {
  const canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = '#0a0a0c'; ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < 40; i++) { ctx.fillStyle = `rgba(255,255,255,${0.08 + Math.random() * 0.12})`; ctx.fillRect(Math.random() * W, Math.random() * H, 1.4, 1.4); }
  ctx.textAlign = 'left'; ctx.fillStyle = '#c9f68b'; ctx.font = `400 34px ${FONT}`; ctx.fillText('astral', 80, 110);
  ctx.fillStyle = '#8a8f98'; ctx.font = `400 24px ${FONT}`; ctx.fillText('my planetary twin', 80, 146);

  const [earthImg, marsImg, moonImg] = await Promise.all(['earth', 'mars', 'moon'].map(b => loadImage(`${base}textures/${b}/color_4k.jpg`)));
  const RE = 190, base_y = 720;                                   // planets aligned by their base
  const rM = RE * SCALE.mars, rL = RE * SCALE.moon;
  const xE = 80 + RE, xM = xE + RE + 100 + rM, xL = xM + rM + 80 + rL;
  const yE = base_y - RE, yM = base_y - rM, yL = base_y - rL;
  drawPlanet(ctx, pixels(earthImg), d.homeLat, d.homeLon, xE, yE, RE);
  drawPlanet(ctx, pixels(marsImg), d.marsLat, d.marsLon, xM, yM, rM);
  const hasMoon = d.moonLat !== undefined && d.moonLon !== undefined;
  if (hasMoon) drawPlanet(ctx, pixels(moonImg), d.moonLat!, d.moonLon!, xL, yL, rL);
  ctx.setLineDash([3, 9]); ctx.strokeStyle = 'rgba(201,246,139,0.85)'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(xE, yE); ctx.quadraticCurveTo((xE + xM) / 2, Math.min(yE, yM) - 190, xM, yM); ctx.stroke(); ctx.setLineDash([]);
  marker(ctx, xE, yE, 16); marker(ctx, xM, yM, 13); if (hasMoon) marker(ctx, xL, yL, 10);
  ctx.textAlign = 'center'; ctx.fillStyle = '#d6d8dc'; ctx.font = `400 24px ${FONT}`;
  ctx.fillText(shortPlace(d.homeRegion), xE, base_y + 46);
  ctx.fillText(siteLabel(d.marsName, 'mars'), xM, base_y + 46);
  if (hasMoon && d.moonName) {
    ctx.font = `400 20px ${FONT}`; const t = siteLabel(d.moonName, 'moon');
    ctx.fillText(t, Math.min(xL, W - 60 - ctx.measureText(t).width / 2), base_y + 76);
  }
  ctx.fillStyle = '#5c6068'; ctx.font = `400 18px ${MONO}`; ctx.fillText('to scale', W / 2, base_y + 118);

  ctx.fillStyle = '#ffffff'; ctx.font = `800 150px ${FONT}`; ctx.fillText(`${d.terrainPct}%`, W / 2, 1000);
  ctx.fillStyle = '#8a8f98'; ctx.font = `400 28px ${FONT}`; ctx.fillText('terrain match', W / 2, 1044);

  ctx.font = `400 26px ${FONT}`;
  const pills = d.pills.slice(0, 3), pad = 26, gap = 18;
  const widths = pills.map(p => ctx.measureText(p).width + 2 * pad);
  let px = W / 2 - (widths.reduce((a, b) => a + b, 0) + gap * (pills.length - 1)) / 2;
  pills.forEach((p, i) => {
    ctx.strokeStyle = 'rgba(214,216,220,0.45)'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.roundRect(px, 1092, widths[i], 50, 25); ctx.stroke();
    ctx.fillStyle = '#d6d8dc'; ctx.fillText(p, px + widths[i] / 2, 1126); px += widths[i] + gap;
  });

  ctx.fillStyle = '#c9f68b'; ctx.font = `400 30px ${FONT}`; ctx.fillText(FOOTER_LINK, W / 2, 1238);
  ctx.fillStyle = '#5c6068'; ctx.font = `400 16px ${FONT}`; ctx.fillText(CREDITS, W / 2, 1290);
  ctx.fillText(FOOTER_NOTE, W / 2, 1314);
  return new Promise((resolve, reject) => canvas.toBlob(b => (b ? resolve(b) : reject(new Error('Could not render the card'))), 'image/png'));
}

/** Kelvin → °C text, never inventing missing values. */
export const celsius = (k: number | null | undefined) => (k == null ? 'No data' : `${Math.round(k - 273.15)} °C`);
