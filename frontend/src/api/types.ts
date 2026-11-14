export type Body = 'earth' | 'moon' | 'mars';
export type Profile = 'general' | 'rover' | 'isru' | 'habitat' | 'eva' | 'astrobiology';
export type Dimension = 'terrain' | 'operations' | 'thermal' | 'albedo' | 'ice' | 'soil' | 'aridity';
export type Scale = 60 | 1000;
export type Method = 'rrf' | 'hybrid' | 'net' | 'baseline' | 'random';
export interface Location { body: Body; lat: number; lon: number }
export interface SearchQuery extends Location {
  profile: Profile; k: number; scale_m: Scale; target_bodies: Body[];
}
export type SimilarRequest = SearchQuery;
export interface Attributes {
  tmax_k: number | null; tmin_k: number | null; trange_k: number | null;
  albedo: number | null; ice_distance_km: number | null;
  ice_frac: number | null; soil_raw: number | null; soil_pct: number | null; precip_mm: number | null;
}
export interface QueryPatch { patch_id: string; scale_m: Scale; distance_km: number }
export interface Analog extends Location {
  patch_id: string; region: string; scale_m: Scale; score: number;
  scores: Record<Dimension, number | null>;
  no_data: Dimension[];
  // Omitted in the team's example fixture; never infer missing weights.
  weights_used?: Partial<Record<Dimension, number>>;
  attributes: Attributes;
  not_comparable: string[];
}
export interface SimilarResponse {
  query: Omit<SimilarRequest, 'k'> & {
    method: Method; patches?: Partial<Record<Body, QueryPatch>>; attributes?: Attributes;
  };
  results: Analog[];
  warnings: string[];
}
export interface Precomputed {
  source: string; model: string; encoder?: string; release?: string; method?: string;
  profile?: string; k?: number; generated: string; site?: string;
}
// demo = offline (no API). precomputed = the offline results are real model outputs.
export interface SearchResult extends SimilarResponse { demo: boolean; precomputed?: Precomputed }
export interface GalaxyPoint { id: string; body: Body; x: number; y: number; z: number }
export type Criterion = 'landing' | 'rover' | 'ice' | 'temperature' | 'total';
export interface Suitability {
  weights: Record<Exclude<Criterion, 'total'>, number>;
  rules: Record<Criterion, string>;
  missing: string[]; caveat: string; grid: { crs: string; pixel_m: number };
  candidate_coordinates: string;
  candidates: { name: string; lat: number; lon: number; group: string;
    total_p90: number | null; percentile_vs_random: number | null }[];
}
