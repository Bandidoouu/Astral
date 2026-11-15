/** Restricted decoder for NASA SVS's uncompressed, single-channel float32 LOLA TIFF. */
export interface HeightGrid { width: number; height: number; values: Float32Array }
export const MOON_RADIUS_KM = 1737.4;

export function decodeLolaTiff(buffer: ArrayBuffer): HeightGrid {
  const data = new DataView(buffer);
  const byteOrder = data.getUint16(0);
  if (byteOrder !== 0x4949 && byteOrder !== 0x4d4d) throw new Error('Invalid TIFF byte order');
  const little = byteOrder === 0x4949;
  if (data.getUint16(2, little) !== 42) throw new Error('Unsupported TIFF version');
  const directory = data.getUint32(4, little);
  const count = data.getUint16(directory, little);
  const tags = new Map<number, number[]>();
  for (let i = 0; i < count; i++) {
    const entry = directory + 2 + i * 12;
    const type = data.getUint16(entry + 2, little);
    const length = data.getUint32(entry + 4, little);
    if (type !== 3 && type !== 4) continue;
    const size = type === 3 ? 2 : 4;
    if (length > buffer.byteLength / size) throw new Error('Invalid TIFF tag length');
    const offset = length * size <= 4 ? entry + 8 : data.getUint32(entry + 8, little);
    const values = Array.from({ length }, (_, j) => type === 3
      ? data.getUint16(offset + j * size, little) : data.getUint32(offset + j * size, little));
    tags.set(data.getUint16(entry, little), values);
  }
  const tag = (id: number, fallback = 0) => tags.get(id)?.[0] ?? fallback;
  const width = tag(256), height = tag(257);
  if (!width || !height || width * height > 4_000_000 || tag(258) !== 32 || tag(339) !== 3 ||
      tag(259, 1) !== 1 || tag(277, 1) !== 1 || tag(274, 1) !== 1 || tag(284, 1) !== 1) {
    throw new Error('Unsupported LOLA raster layout');
  }
  const offsets = tags.get(273), byteCounts = tags.get(279);
  if (!offsets || !byteCounts || offsets.length !== byteCounts.length) throw new Error('Invalid TIFF strips');
  const values = new Float32Array(width * height);
  let index = 0;
  offsets.forEach((offset, strip) => {
    const bytes = byteCounts[strip];
    if (bytes % 4 || offset + bytes > buffer.byteLength || index + bytes / 4 > values.length) throw new Error('Invalid TIFF strip bounds');
    for (let j = 0; j < bytes; j += 4) {
      const value = data.getFloat32(offset + j, little);
      if (!Number.isFinite(value) || Math.abs(value) > 20) throw new Error('Invalid lunar elevation');
      values[index++] = value;
    }
  });
  if (index !== values.length) throw new Error('Incomplete LOLA raster');
  return { width, height, values };
}

/** Longitude wraps at the antimeridian; north/south clamp to the edge pixels. */
export function sampleHeight(grid: HeightGrid, u: number, v: number): number {
  const x = ((u % 1 + 1) % 1) * grid.width - 0.5;
  const y = Math.max(0, Math.min(grid.height - 1, (1 - v) * grid.height - 0.5));
  const x0 = Math.floor(x), y0 = Math.floor(y);
  const tx = x - x0, ty = y - y0;
  const at = (column: number, row: number) => grid.values[row * grid.width + (column + grid.width) % grid.width];
  const top = at(x0, y0) * (1 - tx) + at(x0 + 1, y0) * tx;
  const bottom = at(x0, Math.min(grid.height - 1, y0 + 1)) * (1 - tx) + at(x0 + 1, Math.min(grid.height - 1, y0 + 1)) * tx;
  return top * (1 - ty) + bottom * ty;
}
