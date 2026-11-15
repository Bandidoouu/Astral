/** Visible label tier from the camera distance, in globe radii.
 * 0 = no labels (whole-system view, globes too small), 1 = largest features only. */
export function labelTier(distanceInRadii: number): 0 | 1 | 2 | 3 {
  return distanceInRadii > 11 ? 0 : distanceInRadii > 5 ? 1 : distanceInRadii > 2.6 ? 2 : 3;
}
