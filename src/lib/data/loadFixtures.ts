import { readFile } from "node:fs/promises";
import path from "node:path";
import { buildTractRentLookup, TRACT_RENT_SOURCES, type TractRentFields } from "../tractRent";
import { flattenMultifamilyTokens } from "../zoning";
import { annotateOrangeDesignatedCounty, annotateTractCounty } from "../tractCounty";
import type {
  EligibleMarketsCatalog,
  EligiblePackTractCollection,
  FluConfig,
  OpportunityZoneCollection,
  Oz2TractCollection,
  ParcelCollection,
  RuralMarketTractCollection,
  RuralMarketsCatalog,
  ScMfPriorityCatalog,
  TrafficFeature,
  ZoningConfig,
} from "../types";

const DATA_DIR = path.join(process.cwd(), "data");

type IncomeStamped = { tractGeoid?: string; medianHouseholdIncome?: number };

let orangeTractIncome: Promise<Map<string, number>> | null = null;

export function loadOrangeTractIncomeMap(): Promise<Map<string, number>> {
  if (!orangeTractIncome) {
    orangeTractIncome = readFile(path.join(DATA_DIR, "fixtures/acs-b19013-tracts.json"), "utf8").then((raw) => {
      const table = JSON.parse(raw) as {
        tracts?: Record<string, { e?: number | null }>;
      };
      const lookup = new Map<string, number>();
      for (const [geoid, row] of Object.entries(table.tracts ?? {})) {
        const income = row?.e;
        if (geoid && typeof income === "number" && Number.isFinite(income) && income > 0) lookup.set(geoid, income);
      }
      return lookup;
    });
  }
  return orangeTractIncome;
}

function stampOrangeTractIncome<T extends IncomeStamped>(features: Array<{ properties: T }>, income: Map<string, number>) {
  for (const feature of features) {
    const geoid = feature.properties.tractGeoid;
    if (!geoid) continue;
    const value = income.get(geoid);
    if (value != null) feature.properties.medianHouseholdIncome = value;
  }
}

let tractRentLookup: Promise<Map<string, TractRentFields>> | null = null;

/**
 * GEOID to rent numbers for every series in `TRACT_RENT_SOURCES`.
 * There is no state allow-list: a rerun that adds Mississippi (FIPS 28)
 * stamps those tracts without a code change. Tracts omitted from a file
 * stay omitted here.
 */
export function loadTractRentLookup(): Promise<Map<string, TractRentFields>> {
  if (!tractRentLookup) {
    tractRentLookup = Promise.all(
      TRACT_RENT_SOURCES.map(async (source) => {
        const raw = await readFile(path.join(DATA_DIR, "fixtures", source.file), "utf8");
        return [source.file, JSON.parse(raw) as { tracts?: Record<string, Record<string, unknown>> }] as const;
      }),
    ).then((entries) => buildTractRentLookup(Object.fromEntries(entries)));
  }
  return tractRentLookup;
}

/**
 * Copies plain numbers from a GEOID lookup onto feature properties.
 * Non-numeric values are dropped, so join codes never reach the browser.
 */
export function stampGeoidMetrics<T extends { tractGeoid?: string }>(
  features: Array<{ properties: T }>,
  byGeoid: ReadonlyMap<string, Record<string, unknown>>,
): void {
  for (const feature of features) {
    const geoid = feature.properties.tractGeoid;
    if (!geoid) continue;
    const row = byGeoid.get(geoid);
    if (!row) continue;
    const props = feature.properties as Record<string, unknown>;
    for (const [key, value] of Object.entries(row)) {
      if (typeof value === "number" && Number.isFinite(value)) props[key] = value;
    }
  }
}

async function stampTractMetrics<T extends IncomeStamped>(features: Array<{ properties: T }>) {
  const [income, rent] = await Promise.all([loadOrangeTractIncomeMap(), loadTractRentLookup()]);
  stampOrangeTractIncome(features, income);
  stampGeoidMetrics(features, rent);
}

function normalizeZoningConfig(raw: ZoningConfig): ZoningConfig {
  const config = {
    ...raw,
    jurisdictions: raw.jurisdictions ?? [],
    plannedDevelopmentTokens: raw.plannedDevelopmentTokens ?? [],
    notAllowedExamples: raw.notAllowedExamples ?? [],
    sources: raw.sources ?? [],
    updatedAt: raw.updatedAt ?? "",
  };
  return {
    ...config,
    multifamilyTokens: flattenMultifamilyTokens(config),
  };
}

export async function loadParcelCollection(): Promise<ParcelCollection> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/parcels.geojson"), "utf8");
  const collection = JSON.parse(raw) as ParcelCollection;
  for (const feature of collection.features) {
    if (!("flu" in feature.properties) || feature.properties.flu === undefined) {
      feature.properties.flu = null;
    }
    if (!("opportunityZone" in feature.properties) || feature.properties.opportunityZone === undefined) {
      feature.properties.opportunityZone = null;
    }
    if (!("oz2Eligibility" in feature.properties) || feature.properties.oz2Eligibility === undefined) {
      feature.properties.oz2Eligibility = null;
    }
  }
  return collection;
}

export async function loadTrafficCollection(): Promise<GeoJSON.FeatureCollection<GeoJSON.LineString>> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/traffic.geojson"), "utf8");
  return JSON.parse(raw) as GeoJSON.FeatureCollection<GeoJSON.LineString, TrafficFeature["properties"]>;
}

export async function loadZoningConfig(): Promise<ZoningConfig> {
  const raw = await readFile(path.join(DATA_DIR, "zoning-config.json"), "utf8");
  return normalizeZoningConfig(JSON.parse(raw) as ZoningConfig);
}

export async function loadFluConfig(): Promise<FluConfig> {
  const raw = await readFile(path.join(DATA_DIR, "flu-config.json"), "utf8");
  return JSON.parse(raw) as FluConfig;
}

export async function loadOpportunityZones(): Promise<OpportunityZoneCollection> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/opportunity-zones.geojson"), "utf8");
  const collection = JSON.parse(raw) as OpportunityZoneCollection;
  annotateOrangeDesignatedCounty(collection.features);
  stampGeoidMetrics(collection.features, await loadTractRentLookup());
  return collection;
}

export async function loadOz2Tracts(): Promise<Oz2TractCollection> {
  const [raw, tableRaw] = await Promise.all([
    readFile(path.join(DATA_DIR, "fixtures/oz2-eligible.geojson"), "utf8"),
    readFile(path.join(DATA_DIR, "fixtures/oz2-eligible-tracts.json"), "utf8"),
  ]);
  const collection = JSON.parse(raw) as Oz2TractCollection;
  const table = JSON.parse(tableRaw) as { tracts?: { tractGeoid: string; county?: string; state?: string }[] };
  annotateTractCounty(collection.features, table.tracts ?? []);
  await stampTractMetrics(collection.features);
  return collection;
}

export async function loadRuralMarketsCatalog(): Promise<RuralMarketsCatalog> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/oz2-rural-markets.json"), "utf8");
  return JSON.parse(raw) as RuralMarketsCatalog;
}

export async function loadRuralMarketTracts(): Promise<RuralMarketTractCollection> {
  const [raw, catalogRaw] = await Promise.all([
    readFile(path.join(DATA_DIR, "fixtures/oz2-rural-markets.geojson"), "utf8"),
    readFile(path.join(DATA_DIR, "fixtures/oz2-rural-markets.json"), "utf8"),
  ]);
  const collection = JSON.parse(raw) as RuralMarketTractCollection;
  const catalog = JSON.parse(catalogRaw) as { rows?: { geoid: string; county?: string; state?: string }[] };
  annotateTractCounty(collection.features, catalog.rows ?? []);
  await stampTractMetrics(collection.features);
  return collection;
}

export async function loadUrbanMarketsCatalog(): Promise<EligibleMarketsCatalog> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/oz2-urban-markets.json"), "utf8");
  return JSON.parse(raw) as EligibleMarketsCatalog;
}

export async function loadOtherMarketsCatalog(): Promise<EligibleMarketsCatalog> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/oz2-other-msas.json"), "utf8");
  return JSON.parse(raw) as EligibleMarketsCatalog;
}

export async function loadEligibleOverview(): Promise<GeoJSON.FeatureCollection> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/oz2-eligible-overview.geojson"), "utf8");
  const collection = JSON.parse(raw) as GeoJSON.FeatureCollection;
  await stampTractMetrics(collection.features as Array<{ properties: IncomeStamped }>);
  return collection;
}

export async function loadEligiblePackTracts(): Promise<EligiblePackTractCollection> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/oz2-eligible-packs.geojson"), "utf8");
  const collection = JSON.parse(raw) as EligiblePackTractCollection;
  await stampTractMetrics(collection.features);
  return collection;
}

export async function loadMsStatewideTracts(): Promise<EligiblePackTractCollection> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/oz2-ms-statewide.geojson"), "utf8");
  const collection = JSON.parse(raw) as EligiblePackTractCollection;
  await stampTractMetrics(collection.features);
  return collection;
}

export async function loadScMfPriority(): Promise<ScMfPriorityCatalog> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/sc-oz2-mf-priority.json"), "utf8");
  return JSON.parse(raw) as ScMfPriorityCatalog;
}

export async function loadFixtureMeta(): Promise<Record<string, unknown>> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/meta.json"), "utf8");
  return JSON.parse(raw) as Record<string, unknown>;
}
