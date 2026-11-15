import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { celsius, CREDITS, defaultPills, FOOTER_LINK, FOOTER_NOTE, PUBLIC_SITE, QR_FILE, QR_URL, SCALE, shortPlace, siteLabel } from './shareCard.ts';

test('share image shows the fixed public URL, never the page address', () => {
  assert.equal(PUBLIC_SITE, 'bandidoouu.github.io/Astral');
  assert.equal(FOOTER_LINK, 'find yours → bandidoouu.github.io/Astral');
  const src = readFileSync(new URL('./shareCard.ts', import.meta.url), 'utf8');
  assert.ok(!/window\.location|location\.href|location\.host/.test(src), 'shareCard must not read window.location');
  assert.match(FOOTER_NOTE, /not a habitability rating/);
  assert.match(CREDITS, /blue marble/);
});

test('planets to scale, lower-case names, at most three sourced pills', () => {
  assert.deepEqual(SCALE, { earth: 1, mars: 0.532, moon: 0.273 });
  assert.equal(shortPlace('Nuevo León, Mexico'), 'nuevo león, mx');
  assert.equal(shortPlace('México, Mexico'), 'méxico, mx');
  assert.deepEqual(defaultPills(), ['0.38 g', '6 hPa', '≈80× radiation']);
  assert.equal(siteLabel('an unnamed site at -31.2°, 12.0°', 'moon'), 'unnamed site, moon');
  assert.equal(siteLabel('Acheron Fossae, Mars', 'mars'), 'acheron fossae, mars');
  assert.equal(celsius(null), 'No data');
});

test('QR is a static SVG for the fixed public URL', () => {
  assert.equal(QR_URL, 'https://bandidoouu.github.io/Astral/');
  const svg = readFileSync(new URL(`../../public/${QR_FILE}`, import.meta.url), 'utf8');
  assert.match(svg, /^<svg /);
  assert.ok(svg.includes(QR_URL), 'QR SVG records the URL it encodes');
});
