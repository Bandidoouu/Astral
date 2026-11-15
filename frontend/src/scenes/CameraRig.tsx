import { useEffect, useRef } from 'react';
import type { ComponentRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Box3, MathUtils, Vector3 } from 'three';
import type { PlanetarySceneProps } from '../shared/visualization';
import { globeRadii } from './terrain';
import { toVector } from '../api/coordinates';

type Props = Pick<PlanetarySceneProps, 'selected' | 'focusedMatch' | 'galaxy' | 'view' | 'resetKey'> & {
  centers: Record<PlanetarySceneProps['selected']['body'], [number, number, number]>;
};

/** Camera coordinates are presentation only; galaxy coordinates stay unchanged. */
export default function CameraRig({ selected, focusedMatch, galaxy, view, resetKey, centers }: Props) {
  const previousReset = useRef(resetKey);
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null);
  const previous = useRef({ body: selected.body, lat: selected.lat, lon: selected.lon, view, matchId: focusedMatch?.patch_id });
  const flight = useRef<{ position: Vector3; target: Vector3 } | null>(null);
  const camera = useThree(state => state.camera);
  const aspect = useThree(state => state.size.width / Math.max(1, state.size.height));
  const maxDistance = useRef(90);

  useEffect(() => {
    // A remount (including StrictMode effect replay) keeps the reset overview.
    const resetting = previousReset.current !== resetKey;
    previousReset.current = resetKey;
    const last = previous.current;
    previous.current = { body: selected.body, lat: selected.lat, lon: selected.lon, view, matchId: focusedMatch?.patch_id };
    if (resetting && view === 'system') {
      flight.current = null;
      const distance = Math.max(17, 17 / aspect);
      camera.position.set(0, distance * 0.65, distance);
      controls.current?.target.set(0, 0, 0);
      controls.current?.update();
      return;
    }
    if (view === 'system' && last.view === view && last.body === selected.body && last.lat === selected.lat && last.lon === selected.lon && last.matchId === focusedMatch?.patch_id) return;
    if (view === 'system') {
      const selectionChanged = last.body !== selected.body || last.lat !== selected.lat || last.lon !== selected.lon;
      const focus = focusedMatch && !selectionChanged ? focusedMatch : selected;
      const target = new Vector3(...centers[focus.body]);
      const direction = new Vector3(...toVector(focus.lat, focus.lon));
      // Avoid the singular camera orientation at either geographic pole.
      if (Math.abs(direction.y) > 0.98) direction.z += 0.15;
      flight.current = { target, position: target.clone().add(direction.normalize().multiplyScalar(globeRadii[focus.body] * 3.2)) };
      maxDistance.current = 90;
    } else {
      const bounds = new Box3();
      galaxy.forEach(point => {
        if ([point.x, point.y, point.z].every(Number.isFinite)) bounds.expandByPoint(new Vector3(point.x, point.y, point.z));
      });
      const target = bounds.isEmpty() ? new Vector3() : bounds.getCenter(new Vector3());
      const radius = bounds.isEmpty() ? 1 : Math.max(1, bounds.getSize(new Vector3()).length() / 2);
      const vertical = MathUtils.degToRad(43 / 2);
      const angle = Math.min(vertical, Math.atan(Math.tan(vertical) * aspect));
      const distance = Math.max(6, radius / Math.sin(angle) * 1.15);
      maxDistance.current = Math.max(90, distance * 2);
      flight.current = { target, position: target.clone().add(new Vector3(0, 0.24, 1).normalize().multiplyScalar(distance)) };
    }
  }, [selected.body, selected.lat, selected.lon, view, resetKey, focusedMatch, galaxy, centers, aspect, camera]);

  useFrame((_, delta) => {
    const orbit = controls.current;
    if (!orbit) return;
    orbit.maxDistance = maxDistance.current;
    const destination = flight.current;
    if (!destination) return;
    const alpha = 1 - Math.exp(-5 * Math.min(delta, 0.1));
    camera.position.lerp(destination.position, alpha);
    orbit.target.lerp(destination.target, alpha);
    if (camera.position.distanceToSquared(destination.position) < 0.00001 && orbit.target.distanceToSquared(destination.target) < 0.00001) {
      camera.position.copy(destination.position);
      orbit.target.copy(destination.target);
      flight.current = null;
    }
    orbit.update();
  });

  return <OrbitControls ref={controls} makeDefault enablePan={false} minDistance={view === 'system' ? globeRadii[(focusedMatch ?? selected).body] * 1.45 : 3} maxDistance={maxDistance.current}
    onStart={() => { flight.current = null; }} />;
}
