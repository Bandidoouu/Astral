import { useEffect, useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Line } from '@react-three/drei';
import { CanvasTexture, SRGBColorSpace, Vector3 } from 'three';
import type { PerspectiveCamera, Sprite } from 'three';
import { orbitPoint, orbitRadii } from './orbitLayout';
import type { Point3 } from './orbitLayout';

export function WorldLabel({ text, position, color = '#c6d6e3' }: { text: string; position: Point3; color?: string }) {
  const sprite = useRef<Sprite>(null);
  const { camera, size } = useThree();
  const cameraPoint = useMemo(() => new Vector3(), []);
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas'); canvas.width = 512; canvas.height = 96;
    const ctx = canvas.getContext('2d')!;
    ctx.font = '500 30px Segoe UI, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = color; ctx.shadowBlur = 10; ctx.shadowColor = '#000'; ctx.fillText(text, 256, 48);
    const map = new CanvasTexture(canvas); map.colorSpace = SRGBColorSpace; return map;
  }, [text, color]);
  useEffect(() => () => texture.dispose(), [texture]);
  useFrame(() => {
    if (!sprite.current) return;
    sprite.current.getWorldPosition(cameraPoint).applyMatrix4(camera.matrixWorldInverse);
    const unitsPerPixel = 2 * Math.tan((camera as PerspectiveCamera).fov * Math.PI / 360) * Math.abs(cameraPoint.z) / size.height;
    sprite.current.scale.set(192 * unitsPerPixel, 36 * unitsPerPixel, 1);
  });
  return <sprite ref={sprite} position={position} scale={[2.4, 0.45, 1]} raycast={() => {}}><spriteMaterial map={texture} transparent depthTest={false} /></sprite>;
}

function OrbitRing({ radius, center = [0, 0, 0], color }: { radius: number; center?: Point3; color: string }) {
  const points = useMemo(() => Array.from({ length: 181 }, (_, i) => {
    const [x, y, z] = orbitPoint(radius, i * Math.PI * 2 / 180);
    return [x + center[0], y + center[1], z + center[2]] as Point3;
  }), [radius, center[0], center[1], center[2]]);
  return <Line points={points} color={color} transparent opacity={0.35} lineWidth={1} raycast={() => {}} />;
}

export default function OrbitalGuides({ earth }: { earth: Point3 }) {
  return <>
    <OrbitRing radius={orbitRadii.earth} color="#6fa8c8" />
    <OrbitRing radius={orbitRadii.mars} color="#c68d68" />
    <OrbitRing radius={orbitRadii.moon} center={earth} color="#c9c8bb" />
  </>;
}
