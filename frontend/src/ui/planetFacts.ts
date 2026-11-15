import type { Body } from '../api/types';

/** Physical context for "Where the analogy stops". Every number is quoted from the cited
 * source (docs/datos.md, "Contexto físico"); null = not yet sourced, shown as such. */
export interface Fact { value: string; source: string }
export interface BodyFacts { gravity: Fact; pressure: Fact; radiation: Fact | null; day: Fact }

const FS = 'NASA Planetary Fact Sheet';
export const FACTS: Record<Body, BodyFacts> = {
  moon: {
    gravity: { value: '1.62 m/s²', source: `${FS} (Moon/Earth comparison table)` },
    pressure: { value: '3 × 10⁻¹² hPa (night)', source: `${FS}: 3 × 10⁻¹⁵ bar (night)` },
    radiation: { value: '1,369 µSv/day', source: "Chang'E-4 LND, Zhang et al. 2020 (Sci. Adv. 6, eaaz1334); LRO/CRaTER measured the same dose rate (13.29 vs 13.2 µGy/h)" },
    day: { value: '708.7 h', source: `${FS} (comparison table, length of day)` },
  },
  mars: {
    gravity: { value: '3.73 m/s²', source: `${FS} (surface gravity, mean)` },
    pressure: { value: '6.36 hPa (4.0–8.7 by season)', source: `${FS}: 6.36 mb at mean radius` },
    radiation: null,   // MSL/RAD (Hassler et al. 2014, Science 343): number not yet verified from an accessible source
    day: { value: '24.66 h', source: `${FS} (length of day 24.6597 h)` },
  },
  earth: {
    gravity: { value: '9.82 m/s²', source: `${FS} (surface gravity, mean)` },
    pressure: { value: '1,014 hPa at sea level', source: `${FS}: 1014 mb` },
    radiation: null,
    day: { value: '24.0 h', source: `${FS} (length of day)` },
  },
};

/** Standard (ISA) barometric formula for the troposphere: p = 1013.25 hPa · (1 − 2.25577e-5 · h)^5.25588. */
export function pressureAtElevationHpa(elevationM: number) {
  const h = Math.max(0, Math.min(elevationM, 11000));
  return 1013.25 * Math.pow(1 - 2.25577e-5 * h, 5.25588);
}
