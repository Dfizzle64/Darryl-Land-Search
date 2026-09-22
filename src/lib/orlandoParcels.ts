import type { BBox, MarketId } from "./types";

/** Orlando ~90-minute shed counties (authoritative handoff list). */
export const ORLANDO_SHED_COUNTIES = [
  { name: "Brevard", fips: "12009" },
  { name: "Lake", fips: "12069" },
  { name: "Marion", fips: "12083" },
  { name: "Orange", fips: "12095" },
  { name: "Osceola", fips: "12097" },
  { name: "Polk", fips: "12105" },
  { name: "Seminole", fips: "12117" },
  { name: "Sumter", fips: "12119" },
  { name: "Volusia", fips: "12127" },
] as const;

export type OrlandoShedCountyName = (typeof ORLANDO_SHED_COUNTIES)[number]["name"];

export const ORLANDO_FIPS_BY_NAME: Record<string, string> = Object.fromEntries(
  ORLANDO_SHED_COUNTIES.map((county) => [county.name, county.fips]),
);

export const ORLANDO_NAME_BY_FIPS: Record<string, string> = Object.fromEntries(
  ORLANDO_SHED_COUNTIES.map((county) => [county.fips, county.name]),
);

/** DOH EHWATER MapServer layer ids used for live viewport queries. */
export const ORLANDO_DOH_LAYER_BY_FIPS: Record<string, number> = {
  "12009": 4,
  "12069": 33,
  "12083": 40,
  "12095": 47,
  "12097": 48,
  "12105": 52,
  "12117": 58,
  "12119": 59,
  "12127": 63,
};

export const ORLANDO_DOH_PARCELS_BASE =
  "https://gis.floridahealth.gov/server/rest/services/EHWATER/Parcels/MapServer";

export function isOrlandoShedCounty(county: string | null, state: string | null): boolean {
  if (!county || state !== "Florida") return false;
  return Boolean(ORLANDO_FIPS_BY_NAME[county]);
}

/**
 * Show parcel inventory for the Orlando shed (all nine counties or a selected
 * Florida shed county). Other metros stay tract-only for now.
 */
export function showOrlandoParcels(market: MarketId, county: string | null, state: string | null): boolean {
  if (market !== "Orlando") return false;
  if (!county && !state) return true;
  return isOrlandoShedCounty(county, state);
}

/** Orange-only layers: designated QOZ, FDOT traffic, OCPA zoning/FLU richness. */
export function showOrangeCountyPilot(market: MarketId, county: string | null, state: string | null): boolean {
  if (market !== "Orlando") return false;
  if (!county && !state) return true;
  return county === "Orange" && state === "Florida";
}

export function bboxIntersects(a: BBox, b: BBox): boolean {
  const [aw, as, ae, an] = a;
  const [bw, bs, be, bn] = b;
  return aw <= be && ae >= bw && as <= bn && an >= bs;
}

export function featureIntersectsBbox(
  centroid: [number, number] | undefined,
  bbox: BBox | null | undefined,
): boolean {
  if (!bbox || !centroid) return true;
  const [lon, lat] = centroid;
  const [west, south, east, north] = bbox;
  return lon >= west && lon <= east && lat >= south && lat <= north;
}

/** Approximate county envelopes for live query routing (not cadastral bounds). */
export const ORLANDO_COUNTY_BOUNDS: Record<string, BBox> = {
  "12009": [-80.97, 27.82, -80.4, 28.79],
  "12069": [-81.97, 28.33, -81.33, 29.22],
  "12083": [-82.55, 28.97, -81.67, 29.52],
  "12095": [-81.68, 28.34, -80.99, 28.79],
  "12097": [-81.67, 27.84, -80.86, 28.43],
  "12105": [-82.12, 27.64, -81.37, 28.39],
  "12117": [-81.48, 28.6, -81.08, 28.88],
  "12119": [-82.3, 28.54, -81.88, 28.98],
  "12127": [-81.54, 28.75, -80.73, 29.44],
};

export function fipsForOrlandoCountyFilter(county: string | null, state: string | null): string[] {
  if (county && state === "Florida" && ORLANDO_FIPS_BY_NAME[county]) {
    return [ORLANDO_FIPS_BY_NAME[county]];
  }
  return ORLANDO_SHED_COUNTIES.map((item) => item.fips);
}

export function fipsIntersectingBbox(bbox: BBox | null | undefined, countyFips: string[]): string[] {
  if (!bbox) return countyFips;
  return countyFips.filter((fips) => {
    const envelope = ORLANDO_COUNTY_BOUNDS[fips];
    return envelope ? bboxIntersects(bbox, envelope) : true;
  });
}
