import type { Dimension, Profile } from '../api/types';

export interface Mission {
  id: Profile; title: string; question: string; exercise: string; focus: Dimension[]; limitation: string;
}
// Editorial mission questions, not model weights or claims that a site is suitable.
export const missions: Mission[] = [
  { id: 'general', title: 'Scout an Earth analog', question: 'Which environments offer evidence across several dimensions?', exercise: 'Design a field survey to verify the similarities and missing observations.', focus: ['terrain', 'operations', 'thermal', 'albedo', 'ice', 'soil', 'aridity'], limitation: 'No single site reproduces every planetary condition.' },
  { id: 'rover', title: 'Test a rover route', question: 'Where could we investigate mobility and navigation?', exercise: 'Plan a traverse to test route planning, traction and obstacle detection.', focus: ['terrain', 'operations', 'soil'], limitation: 'A terrain match does not establish traversability or reproduce reduced gravity.' },
  { id: 'isru', title: 'Investigate resources', question: 'Where could we study resource detection methods?', exercise: 'Plan instrument trials and independent sampling to investigate water or ice proxies.', focus: ['ice', 'soil', 'albedo'], limitation: 'A remote-sensing ice proxy is not a confirmed accessible or extractable deposit.' },
  { id: 'habitat', title: 'Prepare a habitat study', question: 'Where could we investigate terrain and thermal challenges?', exercise: 'Design field tests for site surveys, deployment procedures and thermal monitoring.', focus: ['operations', 'thermal', 'terrain'], limitation: 'Similarity is not a landing, construction or settlement safety assessment.' },
  { id: 'eva', title: 'Rehearse a surface traverse', question: 'Where could we evaluate a surface-work procedure?', exercise: 'Plan navigation, sampling and communication workflow rehearsals.', focus: ['terrain', 'operations', 'soil'], limitation: 'Earth cannot reproduce lunar vacuum, reduced gravity or the radiation environment.' },
  { id: 'astrobiology', title: 'Explore habitability analogs', question: 'Where could we investigate environmental proxies relevant to Mars?', exercise: 'Design a sampling strategy with contamination control and independent biological analysis.', focus: ['ice', 'aridity', 'thermal'], limitation: 'These scores do not measure life, biosignatures or actual habitability.' },
];
export const missionById = (id: Profile) => missions.find(m => m.id === id)!;
export const dimensionContext: Record<Dimension, string> = {
  terrain: 'Terrain-pattern similarity from the model; it does not establish common geology or formation history.',
  operations: 'A comparison of terrain-related operations proxies, not a route-safety assessment.',
  thermal: 'Compares temperature maxima, minima and range where measurements are available.',
  albedo: 'Compares surface reflectivity. Similar albedo does not identify the same minerals.',
  ice: 'Compares ice-related fractions or proxies. The underlying observations differ between bodies.',
  soil: 'Compares rockiness percentiles within each body; the underlying physical measurements are different.',
  aridity: 'Compares precipitation. Lunar and Martian liquid precipitation is set to zero in the model, not observed with an Earth rain sensor.',
};
