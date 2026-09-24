import { readFile } from "node:fs/promises";
import path from "node:path";
import type { Oz2EligibilityInfo, ParcelFeature } from "./types";

const CELL = 0.5;
const DATA_DIR = path.join(process.cwd(), "data/fixtures");

type BBox = [number, number, number, number];

type TractHit = {
  bbox: BBox;
  geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon;
  rural: boolean;
  tractGeoid: string;
  tractName: string | null;
  source: string;
};

export type Oz2CentroidIndex = {
  buckets: Map<string, TractHit[]>;
};

const NOT_ELIGIBLE: Oz2EligibilityInfo = {
  eligible: false,
  rural: null,
  tractGeoid: null,
  tractName: null,
  designation: "not-eligible",
  source: "rev-proc-2026-14",
};

let cached: Promise<Oz2CentroidIndex> | null = null;

function cellKey(lon: number, lat: number): string {
  return `${Math.floor(lon / CELL)}:${Math.floor(lat / CELL)}`;
}

export function pointInRing(lon: number, lat: number, ring: number[][]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / ((yj - yi) || 1e-18) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

export function pointInGeometry(lon: number, lat: number, geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon): boolean {
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
  for (const polygon of polygons) {
    if (!pointInRing(lon, lat, polygon[0])) continue;
    if (polygon.slice(1).some((hole) => pointInRing(lon, lat, hole))) continue;
    return true;
  }
  return false;
}

function geometryBBox(geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon): BBox | null {
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
  for (const polygon of polygons) {
    for (const ring of polygon) {
      for (const pair of ring) {
        west = Math.min(west, pair[0]);
        east = Math.max(east, pair[0]);
        south = Math.min(south, pair[1]);
        north = Math.max(north, pair[1]);
      }
    }
  }
  if (!Number.isFinite(west)) return null;
  return [west, south, east, north];
}

function addTract(index: Oz2CentroidIndex, seen: Set<string>, feature: GeoJSON.Feature): void {
  const properties = (feature.properties ?? {}) as Record<string, unknown>;
  const tractGeoid = typeof properties.tractGeoid === "string" ? properties.tractGeoid : "";
  const geometry = feature.geometry;
  if (!tractGeoid || seen.has(tractGeoid)) return;
  if (!geometry || (geometry.type !== "Polygon" && geometry.type !== "MultiPolygon")) return;
  const bbox = geometryBBox(geometry);
  if (!bbox) return;
  seen.add(tractGeoid);
  const hit: TractHit = {
    bbox,
    geometry,
    rural: properties.rural === true,
    tractGeoid,
    tractName: typeof properties.name === "string" ? properties.name : null,
    source: typeof properties.source === "string" ? properties.source : "rev-proc-2026-14",
  };
  const [west, south, east, north] = bbox;
  for (let lon = Math.floor(west / CELL); lon <= Math.floor(east / CELL); lon += 1) {
    for (let lat = Math.floor(south / CELL); lat <= Math.floor(north / CELL); lat += 1) {
      const key = `${lon}:${lat}`;
      const bucket = index.buckets.get(key);
      if (bucket) bucket.push(hit);
      else index.buckets.set(key, [hit]);
    }
  }
}

async function readFeatures(fileName: string): Promise<GeoJSON.Feature[]> {
  const raw = await readFile(path.join(DATA_DIR, fileName), "utf8");
  const collection = JSON.parse(raw) as GeoJSON.FeatureCollection;
  return collection.features ?? [];
}

export async function loadOz2CentroidIndex(): Promise<Oz2CentroidIndex> {
  if (!cached) {
    cached = (async () => {
      const index: Oz2CentroidIndex = { buckets: new Map() };
      const seen = new Set<string>();
      const [pack, rural] = await Promise.all([
        readFeatures("oz2-eligible-packs.geojson"),
        readFeatures("oz2-rural-markets.geojson"),
      ]);
      for (const feature of pack) addTract(index, seen, feature);
      for (const feature of rural) addTract(index, seen, feature);
      return index;
    })();
  }
  return cached;
}

export function lookupOz2Eligibility(index: Oz2CentroidIndex, lon: number, lat: number): Oz2EligibilityInfo {
  const bucket = index.buckets.get(cellKey(lon, lat)) ?? [];
  let chosen: TractHit | null = null;
  for (const hit of bucket) {
    const [west, south, east, north] = hit.bbox;
    if (lon < west || lon > east || lat < south || lat > north) continue;
    if (!pointInGeometry(lon, lat, hit.geometry)) continue;
    if (!chosen || (hit.rural && !chosen.rural)) chosen = hit;
  }
  if (!chosen) return { ...NOT_ELIGIBLE };
  return {
    eligible: true,
    rural: chosen.rural,
    tractGeoid: chosen.tractGeoid,
    tractName: chosen.tractName,
    designation: "eligible-for-nomination",
    source: chosen.source,
  };
}

/** Fill a missing OZ 2.0 field from the tract polygons already drawn on the map. */
export async function annotateMissingOz2Eligibility(features: ParcelFeature[]): Promise<void> {
  if (!features.some((feature) => feature.properties.oz2Eligibility == null)) return;
  const index = await loadOz2CentroidIndex();
  for (const feature of features) {
    if (feature.properties.oz2Eligibility != null) continue;
    const centroid = feature.properties.centroid;
    if (!centroid || centroid.length < 2) continue;
    feature.properties.oz2Eligibility = lookupOz2Eligibility(index, centroid[0], centroid[1]);
  }
}
