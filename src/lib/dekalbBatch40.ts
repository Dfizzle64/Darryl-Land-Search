import fs from "node:fs";
import path from "node:path";
import {
  ATLANTA_DWM_SOURCE,
  ATLANTA_DWM_URL,
  DEKALB_GAS_SOURCE,
  DEKALB_GAS_URL,
  DEKALB_SCHOOLS_NOTE,
  DEKALB_UTILITY_SOURCE,
  DEKALB_UTILITY_URL,
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

export type DekalbBatchSchool = {
  level: string;
  name: string;
  schoolId: string;
  ccrpi: number;
  distanceMiles: number | null;
};

export type DekalbUtilityProxy = "dekalb-dwm" | "atlanta-dwm";

export type DekalbBatchParcel = {
  parcelId: string;
  assignment: "dcsd_zones" | "dcsd_over_nces_atlanta" | string;
  district: string;
  schools: DekalbBatchSchool[];
  flood: {
    zone: string;
    subtype: string | null;
    sfha: boolean;
    staticBfe: number | null;
    datum: string | null;
  };
  water: { provider: string; fromBoundary: boolean; proxy: DekalbUtilityProxy };
  sewer: { provider: string | null; gap: boolean; proxy: DekalbUtilityProxy };
  electric: { provider: string; also: string[] };
  gas: { provider: null; gap: true };
};

export type DekalbBatchFile = {
  countyFips: "13089";
  market: "Atlanta";
  asOf: string;
  schoolYear: string;
  parcelCount: number;
  letterGrades: string;
  omitted: string[];
  floodZoneCounts: Record<string, number>;
  parcels: Record<string, DekalbBatchParcel>;
};

const FIXTURE_PATH = path.join(process.cwd(), "data/fixtures/screening/dekalb-batch40.json");

let cache: DekalbBatchFile | null | undefined;

export function loadDekalbBatch40(): DekalbBatchFile | null {
  if (cache !== undefined) return cache;
  try {
    cache = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf8")) as DekalbBatchFile;
  } catch {
    cache = null;
  }
  return cache;
}

export function dekalbBatchParcel(parcelId: string | null | undefined): DekalbBatchParcel | null {
  if (!parcelId) return null;
  return loadDekalbBatch40()?.parcels[parcelId] ?? null;
}

export function dekalbSiteScreening(record: DekalbBatchParcel): SiteScreeningJoin {
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

function utilityCopy(record: DekalbBatchParcel, kind: "water" | "sewer"): { summary: string; source: string; sourceUrl: string } {
  const atlanta = (kind === "water" ? record.water.proxy : record.sewer.proxy) === "atlanta-dwm";
  const provider = kind === "water" ? record.water.provider : record.sewer.provider;
  const fromBoundary = kind === "water" ? record.water.fromBoundary : false;
  const label = kind === "water" ? "Water" : "Sewer";
  const source = atlanta ? ATLANTA_DWM_SOURCE : DEKALB_UTILITY_SOURCE;
  const sourceUrl = atlanta ? ATLANTA_DWM_URL : DEKALB_UTILITY_URL;
  if (fromBoundary && provider) {
    return {
      summary: `${label} service area: ${provider}. This is a published service-area polygon, not a connection or a will-serve letter.`,
      source,
      sourceUrl,
    };
  }
  if (atlanta) {
    return {
      summary: `${label}: ${provider}. The parcel centroid is inside the City of Atlanta municipal boundary in DeKalb County. DeKalb publishes no DWM service polygon, and Atlanta’s service-area layer did not hit this centroid, so this is a jurisdiction proxy — not a connection or a will-serve letter.`,
      source,
      sourceUrl,
    };
  }
  return {
    summary: `${label}: ${provider}. No public DeKalb DWM service-area polygon is published, so this is the documented county watershed jurisdiction — not a connection or a will-serve letter.`,
    source,
    sourceUrl,
  };
}

function dekalbWater(record: DekalbBatchParcel): UtilityAtPoint {
  const copy = utilityCopy(record, "water");
  return {
    kind: "water",
    status: "ok",
    providers: [record.water.provider],
    summary: copy.summary,
    source: copy.source,
    sourceUrl: copy.sourceUrl,
  };
}

function dekalbSewer(record: DekalbBatchParcel): UtilityAtPoint {
  if (record.sewer.gap || !record.sewer.provider) {
    return {
      kind: "sewer",
      status: "unknown",
      providers: [],
      summary: "Sewer is a gap. Left unknown — not a will-serve and not a finding that a main exists.",
      source: DEKALB_UTILITY_SOURCE,
      sourceUrl: DEKALB_UTILITY_URL,
    };
  }
  const copy = utilityCopy(record, "sewer");
  return {
    kind: "sewer",
    status: "ok",
    providers: [record.sewer.provider],
    summary: copy.summary,
    source: copy.source,
    sourceUrl: copy.sourceUrl,
  };
}

function dekalbElectric(record: DekalbBatchParcel): UtilityAtPoint {
  const provider = record.electric.provider;
  const overlap = record.electric.also.length
    ? ` HIFLD also contains ${record.electric.also.join(", ")} at this centroid; the joined name is the cooperative from that overlap, not a second connection.`
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

function dekalbGas(): UtilityAtPoint {
  return {
    kind: "gas",
    status: "unknown",
    providers: [],
    summary:
      "No public gas service-area polygon is published for DeKalb County or the City of Atlanta. Gas availability is unknown — not a finding that gas is unavailable.",
    source: DEKALB_GAS_SOURCE,
    sourceUrl: DEKALB_GAS_URL,
  };
}

export function dekalbFlood(record: DekalbBatchParcel): FloodAtPoint {
  return describeFloodZone({
    featuresFound: true,
    zone: record.flood.zone,
    subtype: record.flood.subtype,
    sfhaFlag: record.flood.sfha ? "T" : "F",
    staticBfe: record.flood.staticBfe,
    datum: record.flood.datum,
  });
}

export function dekalbSchools(record: DekalbBatchParcel, lon: number, lat: number, year: string): SchoolRating[] {
  const file = loadDekalbBatch40();
  const schoolYear = year || file?.schoolYear || "2025";
  return record.schools.map((school) => {
    const score = school.ccrpi.toFixed(1);
    const rated = toSchoolRating({
      id: `dekalb-${school.schoolId}`,
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

export type DekalbScreeningOverlay = {
  flood: FloodAtPoint;
  utilities: UtilityAtPoint[];
  schools: SchoolRating[];
  schoolsNote: string;
  siteScreening: SiteScreeningJoin;
};

export function dekalbScreeningOverlay(record: DekalbBatchParcel, lon: number, lat: number): DekalbScreeningOverlay {
  const file = loadDekalbBatch40();
  return {
    flood: dekalbFlood(record),
    utilities: [dekalbWater(record), dekalbSewer(record), dekalbElectric(record), dekalbGas()],
    schools: dekalbSchools(record, lon, lat, file?.schoolYear ?? "2025"),
    schoolsNote: DEKALB_SCHOOLS_NOTE,
    siteScreening: dekalbSiteScreening(record),
  };
}

/** Join batch-40 school, flood, and utility fields onto a DeKalb parcel. Other counties are unchanged. */
export function attachDekalbSiteScreening<T extends { properties: ParcelProperties }>(feature: T): T {
  if (feature.properties.countyFips !== "13089") return feature;
  const record = dekalbBatchParcel(feature.properties.parcelId);
  if (!record) return feature;
  feature.properties.siteScreening = dekalbSiteScreening(record);
  return feature;
}
