import fs from "node:fs";
import path from "node:path";
import {
  COBB_GAS_SOURCE,
  COBB_GAS_URL,
  COBB_SCHOOLS_NOTE,
  COBB_UTILITY_SOURCE,
  COBB_UTILITY_URL,
  GOSA_CCRPI_SOURCE,
  GOSA_CCRPI_URL,
  HIFLD_POWER_SOURCE,
  HIFLD_POWER_SOURCE_URL,
  describeFloodZone,
  toSchoolRating,
  type FloodAtPoint,
  type SchoolRating,
  type UtilityAtPoint,
} from "./screening";
import type { ParcelProperties, SiteScreeningJoin } from "./types";

export type CobbBatchSchool = {
  level: string;
  name: string;
  schoolId: string;
  ccrpi: number;
  distanceMiles: number | null;
};

export type CobbBatchParcel = {
  parcelId: string;
  assignment: "ccsd_zones" | "marietta_city" | string;
  district: string;
  schools: CobbBatchSchool[];
  flood: {
    zone: string;
    subtype: string | null;
    sfha: boolean;
    staticBfe: number | null;
    datum: string | null;
  };
  water: { provider: string; fromBoundary: boolean };
  sewer: { provider: string | null; gap: boolean; notAnticipated: boolean };
  electric: { provider: string; also: string[] };
  gas: { provider: null; gap: true };
};

export type CobbBatchFile = {
  countyFips: "13067";
  market: "Atlanta";
  asOf: string;
  schoolYear: string;
  parcelCount: number;
  letterGrades: string;
  omitted: string[];
  floodZoneCounts: Record<string, number>;
  parcels: Record<string, CobbBatchParcel>;
};

const FIXTURE_PATH = path.join(process.cwd(), "data/fixtures/screening/cobb-batch40.json");

let cache: CobbBatchFile | null | undefined;

export function loadCobbBatch40(): CobbBatchFile | null {
  if (cache !== undefined) return cache;
  try {
    cache = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf8")) as CobbBatchFile;
  } catch {
    cache = null;
  }
  return cache;
}

export function cobbBatchParcel(parcelId: string | null | undefined): CobbBatchParcel | null {
  if (!parcelId) return null;
  return loadCobbBatch40()?.parcels[parcelId] ?? null;
}

export function cobbSiteScreening(record: CobbBatchParcel): SiteScreeningJoin {
  return {
    floodZone: record.flood.zone,
    floodSubtype: record.flood.subtype,
    staticBfe: record.flood.staticBfe,
    schools: record.schools.map((school) => ({
      level: school.level,
      name: school.name,
      ccrpi: school.ccrpi,
      distanceMiles: school.distanceMiles,
    })),
    waterProvider: record.water.provider,
    waterFromBoundary: record.water.fromBoundary,
    sewerProvider: record.sewer.gap ? null : record.sewer.provider,
    sewerGap: record.sewer.gap,
    electricProvider: record.electric.provider,
    gasProvider: null,
  };
}

function cobbWater(record: CobbBatchParcel): UtilityAtPoint {
  const provider = record.water.provider;
  const summary = record.water.fromBoundary
    ? `Water service area: ${provider}. Cobb County service-boundary polygon. Not a connection or a will-serve letter.`
    : `Water: ${provider}. No city service-boundary polygon at this centroid, so this is the documented Cobb County Water System jurisdiction — not a drawn connection or a will-serve letter.`;
  return {
    kind: "water",
    status: "ok",
    providers: [provider],
    summary,
    source: COBB_UTILITY_SOURCE,
    sourceUrl: COBB_UTILITY_URL,
  };
}

function cobbSewer(record: CobbBatchParcel): UtilityAtPoint {
  if (record.sewer.gap || !record.sewer.provider) {
    const anticipated = record.sewer.notAnticipated ? " Cobb’s public layer marks this centroid Sewer Not Anticipated." : "";
    return {
      kind: "sewer",
      status: "unknown",
      providers: [],
      summary: `Sewer is a gap.${anticipated} Left unknown — not a will-serve and not a finding that a main exists.`,
      source: COBB_UTILITY_SOURCE,
      sourceUrl: COBB_UTILITY_URL,
    };
  }
  return {
    kind: "sewer",
    status: "ok",
    providers: [record.sewer.provider],
    summary: `Sewer: ${record.sewer.provider}. From Cobb service boundaries (city collection inside those polygons, otherwise CCWS). Not a connection or a will-serve letter.`,
    source: COBB_UTILITY_SOURCE,
    sourceUrl: COBB_UTILITY_URL,
  };
}

function cobbElectric(record: CobbBatchParcel): UtilityAtPoint {
  const provider = record.electric.provider;
  const overlap = record.electric.also.length
    ? ` HIFLD also contains ${record.electric.also.join(", ")} at this centroid; the joined name is the cooperative or smaller territory from that overlap, not a second connection.`
    : "";
  return {
    kind: "power",
    status: provider ? "ok" : "unknown",
    providers: provider ? [provider] : [],
    summary: provider
      ? `Electric retail territory: ${provider}.${overlap} Retail territory only — not a connection, capacity check, or will-serve.`
      : "No HIFLD electric retail territory was joined for this parcel. Power is unknown.",
    source: HIFLD_POWER_SOURCE,
    sourceUrl: HIFLD_POWER_SOURCE_URL,
  };
}

function cobbGas(): UtilityAtPoint {
  return {
    kind: "gas",
    status: "unknown",
    providers: [],
    summary:
      "No public gas service-area polygon is published for Cobb County. Gas availability is unknown — not a finding that gas is unavailable.",
    source: COBB_GAS_SOURCE,
    sourceUrl: COBB_GAS_URL,
  };
}

export function cobbFlood(record: CobbBatchParcel): FloodAtPoint {
  return describeFloodZone({
    featuresFound: true,
    zone: record.flood.zone,
    subtype: record.flood.subtype,
    sfhaFlag: record.flood.sfha ? "T" : "F",
    staticBfe: record.flood.staticBfe,
    datum: record.flood.datum,
  });
}

export function cobbSchools(record: CobbBatchParcel, lon: number, lat: number, year: string): SchoolRating[] {
  const file = loadCobbBatch40();
  const schoolYear = year || file?.schoolYear || "2025";
  return record.schools.map((school) => {
    const score = school.ccrpi.toFixed(1);
    const rated = toSchoolRating({
      id: `cobb-${school.schoolId}`,
      name: school.name,
      city: null,
      state: "GA",
      level: `${school.level} attendance zone`,
      rating: score,
      ratingKind: "ccrpi",
      year: schoolYear,
      source: GOSA_CCRPI_SOURCE,
      sourceUrl: GOSA_CCRPI_URL,
      reportCardUrl: "https://ccrpi.gadoe.org/",
      lon,
      lat,
      zoned: true,
    });
    return { ...rated, distanceMiles: school.distanceMiles };
  });
}

export type CobbScreeningOverlay = {
  flood: FloodAtPoint;
  utilities: UtilityAtPoint[];
  schools: SchoolRating[];
  schoolsNote: string;
  siteScreening: SiteScreeningJoin;
};

export function cobbScreeningOverlay(record: CobbBatchParcel, lon: number, lat: number): CobbScreeningOverlay {
  const file = loadCobbBatch40();
  return {
    flood: cobbFlood(record),
    utilities: [cobbWater(record), cobbSewer(record), cobbElectric(record), cobbGas()],
    schools: cobbSchools(record, lon, lat, file?.schoolYear ?? "2025"),
    schoolsNote: COBB_SCHOOLS_NOTE,
    siteScreening: cobbSiteScreening(record),
  };
}

/** Join batch-40 school, flood, and utility fields onto a Cobb parcel. Other counties are unchanged. */
export function attachCobbSiteScreening<T extends { properties: ParcelProperties }>(feature: T): T {
  if (feature.properties.countyFips !== "13067") return feature;
  const record = cobbBatchParcel(feature.properties.parcelId);
  if (!record) return feature;
  feature.properties.siteScreening = cobbSiteScreening(record);
  return feature;
}
