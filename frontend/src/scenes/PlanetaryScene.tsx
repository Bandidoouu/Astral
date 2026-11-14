import { Component, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Line, OrbitControls, Stars } from '@react-three/drei';
import { Color, CubicBezierCurve3, Vector3 } from 'three';
import { fromVector, toVector } from '../api/coordinates';
import type { Analog, Body, GalaxyPoint, Location } from '../api/types';
import type { PlanetarySceneProps } from '../shared/visualization';
import type { OrbitControls as Controls } from 'three-stdlib';
import OrbitalGuides, { WorldLabel } from './OrbitalGuides';
import { displayRadii as radii, atlasPositions as positions } from './orbitLayout';
import type { Point3 } from './orbitLayout';

import { bodyColors } from '../api/bodies';

function Graticule({ radius, color }: { radius: number; color: string }) {
  const lines = useMemo(() => {
    const latitude = [-60, -30, 0, 30, 60].map(lat => Array.from({ length: 97 }, (_, i) => toVector(lat, i * 360 / 96, radius)));
    const longitude = Array.from({ length: 12 }, (_, j) => Array.from({ length: 49 }, (_, i) => toVector(i * 180 / 48 - 90, j * 30, radius)));
    return [...latitude, ...longitude];
  }, [radius]);
  return <>{lines.map((points, i) => <Line key={i} points={points} color={color} transparent opacity={0.18} lineWidth={0.6} />)}</>;
}
function Marker({ location, radius, color, onClick }: { location: Location; radius: number; color: string; onClick?: () => void }) {
  return <mesh position={toVector(location.lat, location.lon, radius)} onClick={onClick ? e => { if (e.delta <= 5) { e.stopPropagation(); onClick(); } } : undefined}>
    <sphereGeometry args={[0.055, 16, 16]} /><meshBasicMaterial color={color} />
  </mesh>;
}
function Globe({ body, position, selected, results, onSelect, onInspect, focusedMatch }: {
  body: Body; position: Point3; selected: Location; results: Analog[]; onSelect: (location: Location) => void; onInspect: (patchId: string) => void; focusedMatch: Analog | null;
}) {
  const radius = radii[body];
  return <group position={position}>
    <mesh onClick={e => {
      if (e.delta > 5) return;
      e.stopPropagation();
      const point = e.object.worldToLocal(e.point.clone());
      onSelect({ body, ...fromVector(point.x, point.y, point.z) });
    }}>
      <sphereGeometry args={[radius, 64, 48]} />
      <meshStandardMaterial color={body === 'earth' ? '#234c60' : body === 'moon' ? '#6a6c70' : '#874e35'} roughness={0.88} metalness={0.08} />
    </mesh>
    <Graticule radius={radius + 0.006} color={bodyColors[body]} />
    <WorldLabel text={body.toUpperCase()} position={[0, (body === 'moon' ? -1 : 1) * (radius + 0.38), 0]} color={bodyColors[body]} />
    {selected.body === body && <Marker location={selected} radius={radius + 0.03} color="#c9f68b" />}
    {results.filter(r => r.body === body).map(r => <Marker key={r.patch_id} location={r} radius={radius + 0.035} color={focusedMatch?.patch_id === r.patch_id ? '#c9f68b' : bodyColors[body]} onClick={() => onInspect(r.patch_id)} />)}
  </group>;
}
function Arc({ origin, target, positions }: { origin: Location; target: Analog; positions: Record<Body, Point3> }) {
  const points = useMemo(() => {
    const a = new Vector3(...toVector(origin.lat, origin.lon, radii[origin.body] + 0.04)).add(new Vector3(...positions[origin.body]));
    const b = new Vector3(...toVector(target.lat, target.lon, radii[target.body] + 0.04)).add(new Vector3(...positions[target.body]));
    return new CubicBezierCurve3(a, a.clone().add(new Vector3(0, 2.8, 0.7)), b.clone().add(new Vector3(0, 2.8, 0.7)), b).getPoints(64);
  }, [origin, target, positions]);
  return <Line points={points} color={bodyColors[target.body]} lineWidth={1.4} transparent opacity={0.65} dashed dashSize={0.12} gapSize={0.08} raycast={() => {}} />;
}
class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <div className="scene-fallback">The 3D view is unavailable. You can still explore using the coordinates and result cards.</div> : this.props.children;
  }
}
function supportsWebGL() {
  try { const canvas = document.createElement('canvas'); return !!canvas.getContext('webgl2'); } catch { return false; }
}
function Galaxy({ points }: { points: GalaxyPoint[] }) {
  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(points.length * 3);
    const colors = new Float32Array(points.length * 3);
    points.forEach((point, i) => {
      positions.set([point.x, point.y, point.z], i * 3);
      new Color(bodyColors[point.body]).toArray(colors, i * 3);
    });
    return { positions, colors };
  }, [points]);
  return <points><bufferGeometry>
    <bufferAttribute attach="attributes-position" args={[positions, 3]} />
    <bufferAttribute attach="attributes-color" args={[colors, 3]} />
  </bufferGeometry><pointsMaterial vertexColors size={0.13} sizeAttenuation /></points>;
}
function CameraNavigation({ match, positions }: { match: Analog | null; positions: Record<Body, Point3> }) {
  const { camera, size } = useThree();
  const controls = useRef<Controls>(null);
  const flight = useRef<{ position: Vector3; target: Vector3 } | null>(null);
  useEffect(() => {
    flight.current = null;
    if (!match) return;
    const center = new Vector3(...positions[match.body]);
    const direction = new Vector3(...toVector(match.lat, match.lon));
    const goal = { position: center.clone().addScaledVector(direction, radii[match.body] + 4), target: center };
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      camera.position.copy(goal.position); controls.current?.target.copy(goal.target); controls.current?.update();
    } else flight.current = goal;
  }, [camera, match, positions]);
  useEffect(() => {
    if (match) return;
    // Keep all three worlds in frame on narrow screens as well as desktop.
    const distance = Math.max(17, 17 * size.height / Math.max(size.width, 1));
    camera.position.set(0, distance * 0.65, distance);
    controls.current?.target.set(0, 0, 0); controls.current?.update();
  }, [camera, size.width, size.height, match]);
  useFrame((_, delta) => {
    const goal = flight.current;
    if (!goal || !controls.current) return;
    const step = 1 - Math.exp(-delta * 5);
    camera.position.lerp(goal.position, step); controls.current.target.lerp(goal.target, step); controls.current.update();
    if (camera.position.distanceTo(goal.position) < 0.01) flight.current = null;
  });
  return <OrbitControls ref={controls} makeDefault enablePan={false} minDistance={1.4} maxDistance={90} onStart={() => { flight.current = null; }} />;
}

export default function PlanetaryScene({ selected, results, onSelect, galaxy, view, resetKey, focusedMatch, onInspect }: PlanetarySceneProps) {
  const [available] = useState(supportsWebGL);
  if (!available) return <div className="scene-fallback">WebGL is unavailable. Use the site selector or coordinates below to explore.</div>;
  return <SceneBoundary><Canvas key={resetKey} camera={{ position: [0, 3.2, 12.8], fov: 43 }} dpr={[1, 1.5]}>
    <ambientLight intensity={0.6} />
    <directionalLight position={[-4, 5, 7]} intensity={3} color="#e3ecff" />
    <directionalLight position={[4, -1, -3]} intensity={1.3} color="#91b0d0" />
    <Stars radius={70} depth={40} count={3200} factor={3.5} saturation={0.15} fade speed={0} />
    {view === 'system' ? <>
      <OrbitalGuides earth={positions.earth} />
      {(['earth', 'moon', 'mars'] as Body[]).map(body => <Globe key={body} body={body} position={positions[body]} selected={selected} results={results} onSelect={onSelect} onInspect={onInspect} focusedMatch={focusedMatch} />)}
      {results.map(r => <Arc key={r.patch_id} origin={selected} target={r} positions={positions} />)}
    </> : <Galaxy points={galaxy} />}
    <CameraNavigation match={view === 'system' ? focusedMatch : null} positions={positions} />
  </Canvas></SceneBoundary>;
}
