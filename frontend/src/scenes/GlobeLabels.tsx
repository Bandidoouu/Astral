import { useEffect, useMemo, useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { CanvasTexture, PerspectiveCamera, SRGBColorSpace, Vector3 } from 'three';
import type { Sprite } from 'three';
import type { Body } from '../api/types';
import labelsData from './assets/globe-labels.json' with { type: 'json' };
import { globeRadii, surfacePoint } from './terrain';
import { labelTier } from './labelTier';
import type { TerrainFields } from './terrain';

/** Feature names on the globes: IAU nomenclature (Moon, Mars) and Natural Earth (Earth).
 * Tier 1 (largest) always; tiers 2 and 3 appear as the camera gets closer. Only labels on
 * the hemisphere facing the camera are drawn. See frontend/tools/make_globe_labels.py. */
export interface GlobeLabel { body: Body; name: string; lat: number; lon: number; tier: 1 | 2 | 3; site?: boolean }
export const globeLabels = labelsData as GlobeLabel[];


const COLORS = { 1: '#e8ecdf', 2: '#c6d6e3', 3: '#9aa9b9' } as const;

function Label({ label, fields, exaggeration }: { label: GlobeLabel; fields: TerrainFields; exaggeration: number }) {
  const sprite = useRef<Sprite>(null);
  const world = useMemo(() => new Vector3(), []);
  const center = useMemo(() => new Vector3(), []);
  const toCam = useMemo(() => new Vector3(), []);
  const position = useMemo(() => surfacePoint(label, fields, exaggeration, globeRadii[label.body] * 0.02), [label, fields, exaggeration]);
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas'); canvas.width = 384; canvas.height = 64;
    const ctx = canvas.getContext('2d')!;
    ctx.font = `${label.tier === 1 ? 600 : 500} ${label.tier === 1 ? 27 : 24}px Segoe UI, sans-serif`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.shadowBlur = 8; ctx.shadowColor = '#000';
    ctx.fillStyle = label.site ? '#c9f68b' : COLORS[label.tier];
    ctx.fillText(label.name, 192, 32);
    const map = new CanvasTexture(canvas); map.colorSpace = SRGBColorSpace; return map;
  }, [label]);
  useEffect(() => () => texture.dispose(), [texture]);
  useFrame(({ camera, size }) => {
    const s = sprite.current;
    if (!s) return;
    s.getWorldPosition(world);
    s.parent?.getWorldPosition(center);
    toCam.copy(camera.position).sub(world);
    const normal = world.clone().sub(center).normalize();
    s.visible = normal.dot(toCam.clone().normalize()) > 0.3;          // facing side, away from the limb
    if (!s.visible) return;
    const depth = world.clone().applyMatrix4(camera.matrixWorldInverse).z;
    const unitsPerPixel = 2 * Math.tan((camera as PerspectiveCamera).fov * Math.PI / 360) * Math.abs(depth) / size.height;
    s.scale.set(150 * unitsPerPixel, 25 * unitsPerPixel, 1);
  });
  return <sprite ref={sprite} position={position} raycast={() => {}} renderOrder={5}>
    <spriteMaterial map={texture} transparent depthTest={false} />
  </sprite>;
}

export default function GlobeLabels({ body, fields, exaggeration }: { body: Body; fields: TerrainFields; exaggeration: number }) {
  const [tier, setTier] = useState<0 | 1 | 2 | 3>(0);
  const anchor = useRef<Sprite>(null);
  const center = useMemo(() => new Vector3(), []);
  useFrame(({ camera }) => {
    if (!anchor.current?.parent) return;
    anchor.current.parent.getWorldPosition(center);
    const next = labelTier(camera.position.distanceTo(center) / globeRadii[body]);
    if (next !== tier) setTier(next);
  });
  const shown = useMemo(() => globeLabels.filter(l => l.body === body && l.tier <= tier), [body, tier]);
  return <>
    <sprite ref={anchor} visible={false} raycast={() => {}} />
    {shown.map(l => <Label key={`${l.name}-${l.lat}`} label={l} fields={fields} exaggeration={exaggeration} />)}
  </>;
}
