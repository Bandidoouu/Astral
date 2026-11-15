import type { LunarSuitabilityMapProps } from '../shared/visualization';
import './scenes.css';

/** ML exports a plotted polar figure, without the bounds needed for a globe overlay. */
export default function LunarSuitabilityMap({ imageUrl, label, crs, pixelM, onError }: LunarSuitabilityMapProps) {
  return <figure className="astral-lunar-map">
    <img src={imageUrl} alt={`Lunar south pole: ${label}, score from 0 to 1`} onError={onError} />
    <figcaption>{crs} · {pixelM} m/pixel. Polar map exported by ML; not a globe texture.</figcaption>
  </figure>;
}
