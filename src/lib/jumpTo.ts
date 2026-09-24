import { pointInRing } from "@/lib/orangeSignals";

export type JumpPoint = { lng: number; lat: number };

export type MapFlyTarget = JumpPoint & { key: number };

/** South Florida shelf camera box. Same corners as the parcel-only market. */
export const SOUTH_FLORIDA_BOUNDS: [[number, number], [number, number]] = [
  [-83.05, 24.4],
  [-79.95, 27.05],
];

export function pointInBounds(
  lng: number,
  lat: number,
  bounds: [[number, number], [number, number]],
): boolean {
  const [[west, south], [east, north]] = bounds;
  return lng >= west && lng <= east && lat >= south && lat <= north;
}

export function bboxContains(bbox: [number, number, number, number], lng: number, lat: number): boolean {
  const [west, south, east, north] = bbox;
  return lng >= west && lng <= east && lat >= south && lat <= north;
}

/**
 * `lat, long` or `lat long`. A longitude-first pair is accepted when the first
 * number cannot be a latitude.
 */
export function parseLatLng(input: string): JumpPoint | null {
  const parts = input.trim().split(/[,\s]+/).filter(Boolean);
  if (parts.length !== 2) return null;
  const first = Number(parts[0]);
  const second = Number(parts[1]);
  if (!Number.isFinite(first) || !Number.isFinite(second)) return null;
  if (Math.abs(first) <= 90 && Math.abs(second) <= 180) {
    // Western longitude written first: "-80.19, 25.76".
    if (first < 0 && second > 0 && Math.abs(second) <= 90) {
      return { lat: second, lng: first };
    }
    return { lat: first, lng: second };
  }
  if (Math.abs(first) <= 180 && Math.abs(second) <= 90) {
    return { lat: second, lng: first };
  }
  return null;
}

export function censusMatchPoint(body: unknown): JumpPoint | null {
  const matches = (body as { result?: { addressMatches?: unknown[] } } | null)?.result?.addressMatches;
  const first = Array.isArray(matches) ? matches[0] : null;
  const coordinates = (first as { coordinates?: { x?: unknown; y?: unknown } } | null)?.coordinates;
  const lng = Number(coordinates?.x);
  const lat = Number(coordinates?.y);
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return null;
  return { lng, lat };
}

function polygonContains(lng: number, lat: number, rings: number[][][]): boolean {
  const outer = rings[0];
  if (!outer || !pointInRing(lng, lat, outer)) return false;
  return rings.slice(1).every((hole) => !pointInRing(lng, lat, hole));
}

export function geometryContains(lng: number, lat: number, geometry: GeoJSON.Geometry | null | undefined): boolean {
  if (!geometry) return false;
  if (geometry.type === "Polygon") return polygonContains(lng, lat, geometry.coordinates);
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates.some((polygon) => polygonContains(lng, lat, polygon));
  }
  return false;
}

function geometryArea(geometry: GeoJSON.Geometry): number {
  const rings =
    geometry.type === "Polygon"
      ? geometry.coordinates
      : geometry.type === "MultiPolygon"
        ? geometry.coordinates.flat()
        : [];
  let area = 0;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
      area += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
    }
  }
  return Math.abs(area) / 2;
}

/** Smallest polygon that contains the point. Overlaps keep the tighter parcel. */
export function parcelAtPoint<T extends { geometry: GeoJSON.Geometry }>(
  features: T[],
  lng: number,
  lat: number,
): T | null {
  let best: T | null = null;
  let bestArea = Infinity;
  for (const feature of features) {
    if (!geometryContains(lng, lat, feature.geometry)) continue;
    const area = geometryArea(feature.geometry);
    if (area < bestArea) {
      best = feature;
      bestArea = area;
    }
  }
  return best;
}
