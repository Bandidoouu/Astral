import { Component, useDeferredValue, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Line, Stars } from '@react-three/drei';
import { Color, CubicBezierCurve3, Vector3 } from 'three';
import type { Mesh } from 'three';
import { markerRadius } from './markerSize';
import { fromVector } from '../api/coordinates';
import type { Analog, Body, GalaxyPoint, Location } from '../api/types';
import type { PlanetarySceneProps } from '../shared/visualization';
import { bodyColors, galaxyColors } from '../api/bodies';
import CameraRig from './CameraRig';
import { useGeographicGeometry, SurfaceMaterial } from './GlobeSurface';
import { useSurfaceTextures } from './useSurfaceTextures';
import type { BodySurface } from './useSurfaceTextures';
import type { HeightSource, SurfaceLayer } from './textureLayers';
import LayerControls from './LayerControls';
import GlobeLabels from './GlobeLabels';
import OrbitalGuides, { WorldLabel } from './OrbitalGuides';
import { globeRadii, globeCenters, surfacePoint } from './terrain';
import type { TerrainFields } from './terrain';
import { useTerrain } from './useTerrain';
import './scenes.css';

type TerrainProps = { fields: TerrainFields; exaggeration: number };
const bodies: Body[] = ['earth', 'moon', 'mars'];
const landmarks: { label: string; location: Location }[] = [
  { label: 'Himalaya', location: { body: 'earth', lat: 28, lon: 86.9 } },
  { label: 'South Pole–Aitken', location: { body: 'moon', lat: -53, lon: -169 } },
  { label: 'Olympus Mons', location: { body: 'mars', lat: 18.65, lon: -133.8 } },
];

function Graticule({ body, fields, exaggeration }: TerrainProps & { body: Body }) {
  const lines = useMemo(() => {
    const point = (lat: number, lon: number) => surfacePoint({ body, lat, lon }, fields, exaggeration, globeRadii[body] * 0.004);
    const latitude = [-60, -30, 0, 30, 60].map(lat => Array.from({ length: 361 }, (_, i) => point(lat, i - 180)));
    const longitude = Array.from({ length: 12 }, (_, j) => Array.from({ length: 181 }, (_, i) => point(i - 90, j * 30 - 180)));
    return [...latitude, ...longitude];
  }, [body, fields, exaggeration]);
  return <>{lines.map((points, i) => <Line key={i} points={points} color={bodyColors[body]} transparent opacity={0.08} lineWidth={0.6} />)}</>;
}
function Marker({ location, color, fields, exaggeration, onClick }: TerrainProps & { location: Location; color: string; onClick?: () => void }) {
  // Constant size on screen: the sphere is rescaled every frame from its camera distance,
  // so zooming in reveals the site and the window_km footprint instead of hiding them.
  const mesh = useRef<Mesh>(null);
  const world = useMemo(() => new Vector3(), []);
  useFrame(({ camera }) => {
    if (!mesh.current) return;
    mesh.current.getWorldPosition(world);
    mesh.current.scale.setScalar(markerRadius(camera.position.distanceTo(world), globeRadii[location.body]));
  });
  return <mesh ref={mesh} position={surfacePoint(location, fields, exaggeration, globeRadii[location.body] * 0.004)}
    onClick={onClick ? event => { if (event.delta <= 5) { event.stopPropagation(); onClick(); } } : undefined}
    raycast={onClick ? undefined : () => {}}>
    <sphereGeometry args={[1, 32, 24]} /><meshBasicMaterial color={color} />
  </mesh>;
}
const bodyRadiusKm: Record<Body, number> = { earth: 6371, moon: 1737.4, mars: 3396.19 };
/** Outline of the compared patch: a circle of half the patch side (window_km / 2) on the body. */
function Footprint({ match, fields, exaggeration, active = true }: TerrainProps & { match: Analog; active?: boolean }) {
  const points = useMemo(() => {
    const windowKm = match.window_km ?? 128 * match.scale_m / 1000;
    const d = windowKm / 2 / bodyRadiusKm[match.body];
    const p1 = match.lat * Math.PI / 180, l1 = match.lon * Math.PI / 180;
    const out: Vector3[] = [];
    for (let i = 0; i <= 48; i++) {
      const b = i / 48 * 2 * Math.PI;
      const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
      const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
      const lon = ((l2 * 180 / Math.PI + 540) % 360) - 180;
      out.push(new Vector3(...surfacePoint({ body: match.body, lat: p2 * 180 / Math.PI, lon }, fields, exaggeration, globeRadii[match.body] * 0.01)));
    }
    return out;
  }, [match, fields, exaggeration]);
  return <Line points={points} color={active ? '#c9f68b' : bodyColors[match.body]} lineWidth={active ? 1.8 : 1} transparent opacity={active ? 0.95 : 0.55} />;
}
function Globe({ body, selected, results, onSelect, fields, exaggeration, onInspect, focusedMatch, layer, maps, normalRatio, labels = true }: TerrainProps & {
  labels?: boolean;
  body: Body; selected: Location; results: Analog[]; onSelect: (location: Location) => void; onInspect: (patchId: string) => void; focusedMatch: Analog | null; layer: SurfaceLayer; maps?: BodySurface; normalRatio: number;
}) {
  const geometry = useGeographicGeometry(body, fields[body], exaggeration);
  return <group position={globeCenters[body]}>
    <mesh geometry={geometry} onClick={e => {
      if (e.delta > 5) return;
      e.stopPropagation();
      const point = e.object.worldToLocal(e.point.clone());
      onSelect({ body, ...fromVector(point.x, point.y, point.z) });
    }}>
      <SurfaceMaterial body={body} maps={maps} layer={layer} normalRatio={normalRatio} />
    </mesh>
    {layer === 'suitability' && body !== 'earth' && maps?.overlay && <mesh geometry={geometry} scale={1.002} raycast={() => {}}>
      <meshBasicMaterial map={maps.overlay} transparent opacity={1} depthWrite={false} toneMapped={false} />
    </mesh>}
    <WorldLabel text={body.toUpperCase()} position={[0, (body === 'moon' ? -1 : 1) * (globeRadii[body] + 0.38), 0]} color={bodyColors[body]} />
    <Graticule body={body} fields={fields} exaggeration={exaggeration} />
    {labels && <GlobeLabels body={body} fields={fields} exaggeration={exaggeration} />}
    {selected.body === body && <Marker location={selected} fields={fields} exaggeration={exaggeration} color="#c9f68b" />}
    {results.filter(r => r.body === body).map(r => <Footprint key={`fp-${r.patch_id}`} match={r} fields={fields} exaggeration={exaggeration} active={focusedMatch?.patch_id === r.patch_id} />)}
    {results.filter(r => r.body === body).map(r => <Marker key={r.patch_id} location={r} fields={fields} exaggeration={exaggeration} color={focusedMatch?.patch_id === r.patch_id ? '#c9f68b' : bodyColors[body]} onClick={() => onInspect(r.patch_id)} />)}
  </group>;
}
function Arc({ origin, target, fields, exaggeration }: TerrainProps & { origin: Location; target: Analog }) {
  const points = useMemo(() => {
    const a = new Vector3(...surfacePoint(origin, fields, exaggeration, globeRadii[origin.body] * 0.025)).add(new Vector3(...globeCenters[origin.body]));
    const b = new Vector3(...surfacePoint(target, fields, exaggeration, globeRadii[target.body] * 0.025)).add(new Vector3(...globeCenters[target.body]));
    return new CubicBezierCurve3(a, a.clone().add(new Vector3(0, 2.8, 0.7)), b.clone().add(new Vector3(0, 2.8, 0.7)), b).getPoints(64);
  }, [origin, target, fields, exaggeration]);
  return <Line points={points} color={bodyColors[target.body]} lineWidth={1.4} transparent opacity={0.65} dashed dashSize={0.12} gapSize={0.08} raycast={() => {}} />;
}
class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <div className="astral-scene-fallback">The 3D view is unavailable. You can still explore using the coordinates and result cards.</div> : this.props.children;
  }
}
function supportsWebGL() {
  try { const canvas = document.createElement('canvas'); return !!canvas.getContext('webgl2'); } catch { return false; }
}
function Galaxy({ points }: { points: GalaxyPoint[] }) {
  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(points.length * 3), colors = new Float32Array(points.length * 3);
    points.forEach((point, i) => {
      positions.set([point.x, point.y, point.z], i * 3);
      new Color(galaxyColors[point.body]).toArray(colors, i * 3);
    });
    return { positions, colors };
  }, [points]);
  return <points><bufferGeometry>
    <bufferAttribute attach="attributes-position" args={[positions, 3]} />
    <bufferAttribute attach="attributes-color" args={[colors, 3]} />
  </bufferGeometry><pointsMaterial vertexColors size={0.13} sizeAttenuation /></points>;
}
export default function PlanetaryScene({ selected, results, onSelect, galaxy, view, resetKey, focusedMatch, onInspect }: PlanetarySceneProps) {
  const [available] = useState(supportsWebGL);
  const [exaggeration, setExaggeration] = useState(12);
  const renderedExaggeration = useDeferredValue(exaggeration);
  const [layer, setLayer] = useState<SurfaceLayer>('color');
  const [heightSource, setHeightSource] = useState<HeightSource>('packaged');
  const [normalLighting, setNormalLighting] = useState(true);
  const [featureNames, setFeatureNames] = useState(true);
  const { fields, status, metadata, origins } = useTerrain(available, heightSource, selected.body);
  const surfaceMaps = useSurfaceTextures(available, layer, normalLighting && heightSource === 'packaged', selected.body);
  if (!available) return <div className="astral-scene-fallback">WebGL is unavailable. Use the site selector or coordinates below to explore.</div>;
  return <SceneBoundary><div className="astral-planetary-scene">
    {view === 'system' && <div className="astral-terrain-controls">
      <label>Vertical exaggeration: <output>{renderedExaggeration}×{renderedExaggeration === 1 ? ' (true scale)' : ''}</output>
        <input aria-label="Vertical exaggeration" type="range" min="1" max="30" step="1" value={exaggeration}
          onChange={event => setExaggeration(Number(event.target.value))} />
      </label>
      <div className="astral-terrain-landmarks">{landmarks.map(landmark => <button type="button" key={landmark.label}
        onClick={() => onSelect(landmark.location)}>{landmark.label}</button>)}</div>
      <LayerControls featureNames={featureNames} onFeatureNames={setFeatureNames} layer={layer} onLayer={setLayer} heightSource={heightSource} onHeightSource={setHeightSource}
        normals={normalLighting} onNormals={setNormalLighting} selectedBody={selected.body} metadata={metadata}
        origins={origins} maps={surfaceMaps} status={status} />
    </div>}
    <Canvas camera={{ position: [0, 11.05, 17], fov: 43, near: 0.01 }} dpr={[1, 1.5]}>
      <ambientLight intensity={0.4} />
      <directionalLight position={[-4, 5, 7]} intensity={2} color="#ffffff" />
      <directionalLight position={[4, -1, -3]} intensity={0.65} color="#c2cfdf" />
      {/* Star field: a dense, crisp base layer plus a sparse layer of bright stars for contrast (decorative). */}
      <Stars radius={70} depth={30} count={3000} factor={6} saturation={0} fade speed={0} />
      <Stars radius={90} depth={20} count={420} factor={13} saturation={0} fade speed={0} />
      {view === 'system' ? <>
        <OrbitalGuides earth={globeCenters.earth} />
        {bodies.map(body => <Globe key={body} labels={featureNames} body={body} selected={selected} results={results} onSelect={onSelect} onInspect={onInspect} focusedMatch={focusedMatch} fields={fields} exaggeration={renderedExaggeration}
          layer={layer} maps={surfaceMaps[body]} normalRatio={normalLighting && origins[body] === 'packaged' ? renderedExaggeration / (metadata[body]?.normal_and_hillshade_vertical_exaggeration ?? 1) : 0} />)}
        {results.map(r => <Arc key={r.patch_id} origin={selected} target={r} fields={fields} exaggeration={renderedExaggeration} />)}
      </> : <Galaxy points={galaxy} />}
      <CameraRig selected={selected} focusedMatch={focusedMatch} galaxy={galaxy} view={view} resetKey={resetKey} centers={globeCenters} />
    </Canvas>
  </div></SceneBoundary>;
}
