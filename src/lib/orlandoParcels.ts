import type { BBox } from "./types";

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

/**
 * Viewport tile grid for the complete 5–150 acre extracts.
 * Keep in sync with ORIGIN_LON / ORIGIN_LAT / TILE_DEG in scripts/seed_orlando_parcels.py.
 */
export const ORLANDO_PARCEL_TILE = {
  originLon: -83,
  originLat: 27,
  tileDeg: 0.25,
} as const;

/** Inclusive acreage band for the five complete counties (FDOR land area). */
export const ORLANDO_CORE_ACREAGE = { min: 5, max: 150 } as const;

/** FDOR LND_SQFOOT bounds for that band (acres × 43,560). */
export const ORLANDO_CORE_SQFT = { min: 217_800, max: 6_534_000 } as const;

/** Counties whose fixtures are every public parcel from 5.0 through 150.0 acres. */
export const ORLANDO_FULL_5AC_COUNTIES = ["Lake", "Orange", "Osceola", "Polk", "Seminole"] as const;

export const ORLANDO_SAMPLE_COUNTIES = ["Brevard", "Marion", "Sumter", "Volusia"] as const;

export function isFull5AcCounty(county: string | null | undefined): boolean {
  return Boolean(county && (ORLANDO_FULL_5AC_COUNTIES as readonly string[]).includes(county));
}

export function tileIndicesForBbox(bbox: BBox): { ix0: number; ix1: number; iy0: number; iy1: number } {
  const [west, south, east, north] = bbox;
  const { originLon, originLat, tileDeg } = ORLANDO_PARCEL_TILE;
  return {
    ix0: Math.floor((west - originLon) / tileDeg),
    ix1: Math.floor((east - originLon) / tileDeg),
    iy0: Math.floor((south - originLat) / tileDeg),
    iy1: Math.floor((north - originLat) / tileDeg),
  };
}

export function tileFileName(ix: number, iy: number): string {
  return `${ix}_${iy}.geojson`;
}

/**
 * When a viewport holds more parcels than the browser should draw, keep a
 * spatially even subset (largest acreage first inside each cell).
 */
export function spatiallyThinFeatures<T extends { properties: { centroid?: [number, number]; acreage: number | null } }>(
  features: T[],
  limit: number,
  cellDeg = 0.045,
): T[] {
  if (features.length <= limit) return features;
  const buckets = new Map<string, T[]>();
  for (const feature of features) {
    const centroid = feature.properties.centroid;
    if (!centroid) {
      const list = buckets.get("none") ?? [];
      list.push(feature);
      buckets.set("none", list);
      continue;
    }
    const key = `${Math.floor(centroid[0] / cellDeg)}:${Math.floor(centroid[1] / cellDeg)}`;
    const list = buckets.get(key) ?? [];
    list.push(feature);
    buckets.set(key, list);
  }
  for (const list of buckets.values()) {
    list.sort((a, b) => (b.properties.acreage ?? 0) - (a.properties.acreage ?? 0));
  }
  const keys = Array.from(buckets.keys());
  const out: T[] = [];
  let depth = 0;
  while (out.length < limit) {
    let progressed = false;
    for (const key of keys) {
      const list = buckets.get(key);
      if (!list || depth >= list.length) continue;
      out.push(list[depth]);
      progressed = true;
      if (out.length >= limit) break;
    }
    if (!progressed) break;
    depth += 1;
  }
  return out;
}

/**
 * Attribute filters run before the draw cap. Thinning first keeps the largest
 * parcel in each cell, then a slider can only see that sample — a smaller
 * parcel that actually matches never comes back, and non-matches stay in the
 * payload the map has to hide.
 */
export function selectParcelPage<T extends { properties: { centroid?: [number, number]; acreage: number | null } }>(
  features: T[],
  limit: number,
  predicate: (feature: T) => boolean,
): {
  matches: T[];
  rejected: T[];
  thinned: T[];
  totalInBbox: number;
  totalMatching: number;
  truncated: boolean;
} {
  const matches: T[] = [];
  const rejected: T[] = [];
  for (const feature of features) {
    if (predicate(feature)) matches.push(feature);
    else rejected.push(feature);
  }
  const thinned = spatiallyThinFeatures(matches, limit);
  return {
    matches,
    rejected,
    thinned,
    totalInBbox: features.length,
    totalMatching: matches.length,
    truncated: thinned.length < matches.length,
  };
}

export function isOrlandoShedCounty(county: string | null, state: string | null): boolean {
  if (!county || state !== "Florida") return false;
  return Boolean(ORLANDO_FIPS_BY_NAME[county]);
}

/**
 * Show parcel inventory for the Orlando shed (all nine counties or a selected
 * Florida shed county). Other metros stay tract-only for now.
 */
export function showOrlandoParcels(market: string, county: string | null, state: string | null): boolean {
  if (market !== "Orlando") return false;
  if (!county && !state) return true;
  return isOrlandoShedCounty(county, state);
}

/** Orange-only layers: designated QOZ, FDOT traffic, OCPA zoning/FLU richness. */
export function showOrangeCountyPilot(market: string, county: string | null, state: string | null): boolean {
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
