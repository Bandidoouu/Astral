/** Elevation of an Earth point from the packaged NASA height map (SRTMGL30, 4096×2048,
 * public/textures/earth/height_4k.png + height.json): the same data the globe uses. */
let grid: Promise<{ w: number; h: number; px: Uint8ClampedArray; min: number; max: number }> | null = null;

function load() {
  const base = import.meta.env.BASE_URL.replace(/\/?$/, '/');
  grid ??= (async () => {
    const meta = await (await fetch(`${base}textures/earth/height.json`)).json() as { min_m: number; max_m: number };
    const bitmap = await createImageBitmap(await (await fetch(`${base}textures/earth/height_4k.png`)).blob(), { colorSpaceConversion: 'none' });
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width; canvas.height = bitmap.height;
    const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
    ctx.drawImage(bitmap, 0, 0);
    const px = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    bitmap.close();
    return { w: canvas.width, h: canvas.height, px, min: meta.min_m, max: meta.max_m };
  })().catch(e => { grid = null; throw e; });
  return grid;
}

export async function earthElevationM(lat: number, lon: number) {
  const g = await load();
  const x = Math.min(g.w - 1, Math.max(0, Math.floor((lon + 180) / 360 * g.w)));
  const y = Math.min(g.h - 1, Math.max(0, Math.floor((90 - lat) / 180 * g.h)));
  const v = g.px[(y * g.w + x) * 4];
  return g.min + (v / 255) * (g.max - g.min);
}
