/** Marker radius (world units) that keeps a constant on-screen size.
 * At the default 45° field of view, 0.011 × distance is ~6 px on a 900 px tall canvas.
 * Capped at the former fixed size (3.5 % of the globe radius) so far away it never grows
 * beyond what it was, and floored so it never vanishes. */
export const MARKER_SCREEN_FACTOR = 0.011;
export function markerRadius(distance: number, globeRadius: number) {
  const r = Math.max(distance, 0) * MARKER_SCREEN_FACTOR;
  return Math.min(Math.max(r, globeRadius * 0.002), globeRadius * 0.035);
}
