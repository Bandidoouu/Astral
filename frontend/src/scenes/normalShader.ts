import type { MeshStandardMaterial } from 'three';

/** Packaged normal RGB is east/north/up, not object-space XYZ.
 * Reconstruct that frame analytically from the geographic UV, replacing the
 * geometric lighting normal rather than adding the same DEM slope twice.
 * Three's object-space branch supplies the normalMatrix uniform in the fragment.
 */
export const applyGeographicNormals: MeshStandardMaterial['onBeforeCompile'] = shader => {
  shader.fragmentShader = shader.fragmentShader.replace('#include <normal_fragment_maps>', `
#ifdef USE_NORMALMAP_OBJECTSPACE
  vec3 astralN = texture2D(normalMap, vNormalMapUv).xyz * 2.0 - 1.0;
  astralN.xy *= normalScale;
  float astralLon = (vNormalMapUv.x - 0.5) * 6.28318530718;
  float astralLat = (vNormalMapUv.y - 0.5) * 3.14159265359;
  astralN.xy *= smoothstep(0.0, 0.02, abs(cos(astralLat)));
  vec3 astralRadial = vec3(cos(astralLat) * sin(astralLon), sin(astralLat), cos(astralLat) * cos(astralLon));
  vec3 astralEast = vec3(cos(astralLon), 0.0, -sin(astralLon));
  vec3 astralNorth = cross(astralRadial, astralEast);
  normal = normalize(normalMatrix * (astralEast * astralN.x + astralNorth * astralN.y + astralRadial * astralN.z));
#else
  #include <normal_fragment_maps>
#endif
`);
};
export const geographicNormalCacheKey = () => 'astral-geographic-normal-v1';
