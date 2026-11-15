import type { Body } from './types';

export const bodyColors: Record<Body, string> = {
  earth: '#78c8df', moon: '#d8d5ca', mars: '#e59b75',
};

/** Terrain galaxy only: more distinct hues so the three bodies separate at a glance
 * (Earth saturated blue, Moon light gray, Mars orange). */
export const galaxyColors: Record<Body, string> = {
  earth: '#2f8cff', moon: '#e6e3da', mars: '#ff7a3d',
};
