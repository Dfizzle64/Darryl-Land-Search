import { readFile } from "node:fs/promises";
import path from "node:path";
import { flattenMultifamilyTokens } from "../zoning";
import type { FluConfig, ParcelCollection, TrafficFeature, ZoningConfig } from "../types";

const DATA_DIR = path.join(process.cwd(), "data");

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

export async function loadFixtureMeta(): Promise<Record<string, unknown>> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/meta.json"), "utf8");
  return JSON.parse(raw) as Record<string, unknown>;
}
