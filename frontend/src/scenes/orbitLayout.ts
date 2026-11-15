import type { Body } from '../api/types';

export type Point3 = [number, number, number];
// Fixed visual composition for the analog explorer, not an orbital simulation.
export const orbitRadii = { earth: 4.6, mars: 7.01, moon: 1.6 };
// Bodies and the lunar guide are enlarged for selection. This view is not to scale.
export const displayRadii: Record<Body, number> = { earth: 0.78, moon: 0.28, mars: 0.56 };
export function orbitPoint(radius: number, angle: number): Point3 {
  return [radius * Math.cos(angle), 0, -radius * Math.sin(angle)];
}
const earth = orbitPoint(orbitRadii.earth, 3.8);
const moonOffset = orbitPoint(orbitRadii.moon, 0.2);
export const atlasPositions: Record<Body, Point3> = {
  earth,
  mars: orbitPoint(orbitRadii.mars, 0.55),
  moon: [earth[0] + moonOffset[0], 0, earth[2] + moonOffset[2]],
};
