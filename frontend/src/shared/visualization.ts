import type { ComponentType } from 'react';
import type { Analog, GalaxyPoint, Location } from '../api/types';

/** Integration boundary: coordinate changes with both frontend owners. */
export interface PlanetarySceneProps {
  selected: Location;
  results: Analog[];
  onSelect: (location: Location) => void;
  galaxy: GalaxyPoint[];
  view: 'system' | 'galaxy';
  focusedMatch: Analog | null;
  onInspect: (patchId: string) => void;
  resetKey: number;
}

export interface LunarSuitabilityMapProps {
  imageUrl: string;
  label: string;
  crs: string;
  pixelM: number;
  onError: () => void;
}

export interface VisualizationComponents {
  PlanetaryScene: ComponentType<PlanetarySceneProps>;
  LunarSuitabilityMap: ComponentType<LunarSuitabilityMapProps>;
}
