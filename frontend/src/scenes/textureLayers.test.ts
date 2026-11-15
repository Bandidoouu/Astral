import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { inflateSync } from 'node:zlib';
import test from 'node:test';
import type { Body } from '../api/types.ts';
import { decodeHeightPixels, parseHeightMetadata, textureUrl } from './textureLayers.ts';
import { elevationKm, surfaceRadius, globeRadii } from './terrain.ts';

function metadata(body: Body) {
  return parseHeightMetadata(JSON.parse(readFileSync(new URL(`../../public/textures/${body}/height.json`, import.meta.url), 'utf8')), body);
}

// Independent PNG reader for the repository's non-interlaced, 8-bit grayscale heights.
// No browser/Canvas or package dependency: validates the actual shipped image bytes.
function heightPng(body: Body) {
  const bytes = readFileSync(new URL(`../../public/textures/${body}/height_4k.png`, import.meta.url));
  assert.equal(bytes.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
  const width = bytes.readUInt32BE(16), height = bytes.readUInt32BE(20);
  assert.equal(bytes[24], 8); assert.equal(bytes[25], 0); assert.equal(bytes[28], 0);
  const chunks: Buffer[] = [];
  for (let offset = 8; offset < bytes.length;) {
    const size = bytes.readUInt32BE(offset), type = bytes.toString('ascii', offset + 4, offset + 8);
    if (type === 'IDAT') chunks.push(bytes.subarray(offset + 8, offset + 8 + size));
    offset += size + 12;
  }
  const packed = inflateSync(Buffer.concat(chunks)), values = new Uint8Array(width * height);
  assert.equal(packed.length, height * (width + 1));
  const paeth = (a: number, b: number, c: number) => {
    const p = a + b - c, da = Math.abs(p - a), db = Math.abs(p - b), dc = Math.abs(p - c);
    return da <= db && da <= dc ? a : db <= dc ? b : c;
  };
  for (let y = 0; y < height; y++) {
    const filter = packed[y * (width + 1)]; assert.ok(filter <= 4);
    for (let x = 0; x < width; x++) {
      const left = x ? values[y * width + x - 1] : 0;
      const above = y ? values[(y - 1) * width + x] : 0;
      const corner = x && y ? values[(y - 1) * width + x - 1] : 0;
      const delta = filter === 0 ? 0 : filter === 1 ? left : filter === 2 ? above : filter === 3 ? Math.floor((left + above) / 2) : paeth(left, above, corner);
      values[y * width + x] = (packed[y * (width + 1) + x + 1] + delta) & 255;
    }
  }
  return { width, height, values };
}

test('public height sidecars and pixels preserve meter ranges and reject invalid units/projections', () => {
  for (const body of ['earth', 'moon', 'mars'] as Body[]) {
    const data = metadata(body);
    const field = decodeHeightPixels(new Uint8ClampedArray([0,0,0,255, 255,255,255,255, 127,127,127,255, 128,128,128,255, 0,0,0,255, 255,255,255,255, 0,0,0,255, 255,255,255,255]), 4, 2, data);
    assert.ok(Math.abs(field.values[0] * 1000 - data.min_m) < 0.002);
    assert.ok(Math.abs(field.values[1] * 1000 - data.max_m) < 0.002);
    assert.throws(() => parseHeightMetadata({ ...data, projection: 'polar' }, body));
    assert.throws(() => parseHeightMetadata({ ...data, encoding: 'normalize sRGB' }, body));
    assert.throws(() => parseHeightMetadata({ ...data, body: 'wrong' }, body));
    assert.throws(() => decodeHeightPixels(new Uint8ClampedArray(32), 4, 2, data));
  }
});

for (const [body, lat, lon, threshold] of [['earth',28,86.9,3],['moon',-53,-169,-3],['mars',18.65,-133.8,15]] as const) {
  test(`${body}: actual public PNG aligns the known terrain feature with geographic selection`, () => {
    const image = heightPng(body), data = metadata(body);
    assert.equal(image.width, data.width); assert.equal(image.height, data.height);
    // Retain a 4 px/degree sample of the actual PNG for the shared geographic sampler.
    const width = 1440, height = 720, values = new Float32Array(width * height);
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
      const pixel = image.values[Math.min(image.height - 1, Math.floor((y + 0.5) * image.height / height)) * image.width + Math.min(image.width - 1, Math.floor((x + 0.5) * image.width / width))];
      values[y * width + x] = (data.min_m + pixel / 255 * (data.max_m - data.min_m)) / 1000;
    }
    const field = { width, height, values }, km = elevationKm(field, lat, lon);
    assert.ok(body === 'moon' ? km < threshold : km > threshold, `${body} height ${km} km`);
    assert.equal(elevationKm(field, 10, -180), elevationKm(field, 10, 180));
    if (body === 'earth') {
      const pixel = image.values[Math.floor(image.height / 2) * image.width + Math.floor((40 / 360) * image.width)];
      const ocean = decodeHeightPixels(Uint8ClampedArray.from({ length: 32 }, (_, i) => i % 4 === 3 ? 255 : pixel), 4, 2, data);
      assert.equal(surfaceRadius(body, 0, -140, ocean, 30), globeRadii[body], 'the encoded sea-level bin renders exactly at water level');
    }
  });
}

test('resource paths work under a static-host subpath and only map georeferenced suitability PNGs', () => {
  assert.equal(textureUrl('mars', 'normal', '/Astral/'), '/Astral/textures/mars/normal_4k.jpg');
  assert.equal(textureUrl('moon', 'suitability', '/Astral'), '/Astral/textures/moon/suitability_4k.png');
  for (const body of ['moon', 'mars'] as const) {
    const header = readFileSync(new URL(`../../public/textures/${body}/suitability_4k.png`, import.meta.url)).subarray(0, 29);
    assert.equal(header.readUInt32BE(16), header.readUInt32BE(20) * 2);
    assert.equal(header[25], 6, 'RGBA retains no-data alpha');
  }
});
