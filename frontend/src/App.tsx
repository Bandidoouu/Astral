import { lazy } from 'react';
import ExplorerApp from './ui/ExplorerApp';

// Shared composition only. UI and 3D implementations stay in their own folders.
const PlanetaryScene = lazy(() => import('./scenes').then(module => ({ default: module.PlanetaryScene })));
const LunarSuitabilityMap = lazy(() => import('./scenes').then(module => ({ default: module.LunarSuitabilityMap })));

export default function App() {
  return <ExplorerApp PlanetaryScene={PlanetaryScene} LunarSuitabilityMap={LunarSuitabilityMap} />;
}
