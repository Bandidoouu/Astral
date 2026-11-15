import type { HeightGrid } from './lunarElevation';

// The product's map projection uses a 3396 km reference sphere.
export const MARS_REFERENCE_RADIUS_KM = 3396;

/** MEGT90N000CB: 1440×720 signed big-endian meters, north first, 0..360°E. */
export function decodeMola(buffer: ArrayBuffer): HeightGrid {
  const width = 1440, height = 720;
  if (buffer.byteLength !== width * height * 2) throw new Error('Invalid MOLA raster size');
  const data = new DataView(buffer);
  const values = new Float32Array(width * height);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      // Output starts at -180°E (180°E); matches the color map and shared sampler.
      const sourceX = (x + width / 2) % width;
      const meters = data.getInt16((y * width + sourceX) * 2, false);
      if (meters < -12000 || meters > 25000) throw new Error('Invalid MOLA elevation');
      values[y * width + x] = meters / 1000;
    }
  }
  return { width, height, values };
}
