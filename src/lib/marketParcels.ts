import type { BBox } from "./types";
import { ORLANDO_PARCEL_TILE, bboxIntersects, tileIndicesForBbox } from "./orlandoParcels";

/**
 * Inclusive acreage band for every non-Orlando market extract.
 * Same bounds as Orlando's complete counties.
 */
export const MARKET_PARCEL_ACREAGE = { min: 5, max: 150 } as const;

/** Same viewport grid as the Orlando tiles. Negative indexes cover Memphis and Atlanta. */
export const MARKET_PARCEL_TILE = ORLANDO_PARCEL_TILE;

export type MarketParcelCoverage = "complete-gte-5ac" | "sample" | "gap";

export type MarketParcelCountyRef = {
  name: string;
  state: string;
  fips: string;
  featureCount: number;
  coverage: MarketParcelCoverage;
  minAcres?: number;
  maxAcres?: number;
  gaps?: string[];
};

export type MarketParcelMarketSummary = {
  tier: "primary" | "other" | string;
  parcelCount: number;
  completeCountyCount: number;
  sampleCountyCount: number;
  gapCountyCount: number;
  path: string;
  counties: MarketParcelCountyRef[];
};

export type MarketParcelIndex = {
  generatedAt: string;
  coreMinAcres: number;
  coreMaxAcres: number;
  tile: { originLon: number; originLat: number; tileDeg: number };
  markets: Record<string, MarketParcelMarketSummary>;
};

export type MarketParcelCountyMeta = MarketParcelCountyRef & {
  partition: "tiles" | "file" | "none" | string;
  source: string;
  queryUrl?: string | null;
  path?: string | null;
  lookup?: string | null;
  tileCount?: number | null;
  sourceCount?: number | null;
};

export type MarketParcelsMeta = {
  generatedAt: string;
  market: string;
  tier?: string;
  parcelCount: number;
  coreMinAcres: number;
  coreMaxAcres: number;
  tile: { originLon: number; originLat: number; tileDeg: number };
  notes: string[];
  counties: MarketParcelCountyMeta[];
};

export function inMarketAcreageBand(
  acres: number | null | undefined,
  band: { min: number; max: number } = MARKET_PARCEL_ACREAGE,
): boolean {
  if (typeof acres !== "number" || !Number.isFinite(acres)) return false;
  return acres >= band.min && acres <= band.max;
}

export function featuresInAcreageBand<T extends { properties: { acreage: number | null } }>(
  features: T[],
  band: { min: number; max: number } = MARKET_PARCEL_ACREAGE,
): T[] {
  return features.filter((feature) => inMarketAcreageBand(feature.properties.acreage, band));
}

export function marketParcelSlug(market: string): string {
  return market.toLowerCase().replace(/ /g, "-");
}

/**
 * Parcel inventory for a non-Orlando market. Orlando stays on showOrlandoParcels.
 * A market with zero pulled parcels stays on the tract overlay. Selecting a
 * documented gap county inside a market that does have parcels keeps the
 * parcel shell so the empty county is visible.
 */
export function showMarketParcels(
  market: string,
  county: string | null,
  state: string | null,
  index: MarketParcelIndex | null | undefined,
): boolean {
  if (market === "Orlando") return false;
  const entry = index?.markets?.[market];
  if (!entry || entry.parcelCount <= 0) return false;
  if (!county && !state) return true;
  if (!county || !state) return false;
  return entry.counties.some((item) => item.name === county && item.state === state);
}

export function marketParcelCountyFips(
  entry: MarketParcelMarketSummary | null | undefined,
  county: string | null,
  state: string | null,
): string[] {
  if (!entry) return [];
  if (county && state) {
    return entry.counties.filter((item) => item.name === county && item.state === state).map((item) => item.fips);
  }
  return entry.counties.map((item) => item.fips);
}

export function countiesIntersectingBbox(
  counties: MarketParcelCountyRef[],
  bounds: Record<string, BBox>,
  bbox: BBox | null | undefined,
): MarketParcelCountyRef[] {
  if (!bbox) return counties;
  return counties.filter((county) => {
    const envelope = bounds[county.fips];
    return envelope ? bboxIntersects(bbox, envelope) : true;
  });
}

export { tileIndicesForBbox };
