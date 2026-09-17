import { readFile } from "node:fs/promises";
import path from "node:path";
import type { ParcelCollection, TrafficFeature, ZoningConfig } from "../types";

const DATA_DIR = path.join(process.cwd(), "data");

export async function loadParcelCollection(): Promise<ParcelCollection> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/parcels.geojson"), "utf8");
  return JSON.parse(raw) as ParcelCollection;
}

export async function loadTrafficCollection(): Promise<GeoJSON.FeatureCollection<GeoJSON.LineString>> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/traffic.geojson"), "utf8");
  return JSON.parse(raw) as GeoJSON.FeatureCollection<GeoJSON.LineString, TrafficFeature["properties"]>;
}

export async function loadZoningConfig(): Promise<ZoningConfig> {
  const raw = await readFile(path.join(DATA_DIR, "zoning-config.json"), "utf8");
  return JSON.parse(raw) as ZoningConfig;
}

export async function loadFixtureMeta(): Promise<Record<string, unknown>> {
  const raw = await readFile(path.join(DATA_DIR, "fixtures/meta.json"), "utf8");
  return JSON.parse(raw) as Record<string, unknown>;
}
