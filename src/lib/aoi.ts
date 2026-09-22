import { featureIntersectsBbox } from "./orlandoParcels";
import type { BBox } from "./types";

/** Fixture query cap for a locked AOI. Matches the `/api/parcels` hard max. */
export const AOI_PARCEL_LIMIT = 8000;

/** Ignore click-sized drags. About 50 m near Orlando. */
export const MIN_AOI_SPAN_DEG = 0.0005;

export type AoiSource = "bounds" | "draw";

export type AoiLock = {
  bbox: BBox;
  source: AoiSource;
};

const M_PER_DEG_LAT = 110_540;
const M_PER_DEG_LON_EQUATOR = 111_320;
const SQ_M_PER_ACRE = 4_046.8564224;

/**
 * Order a drag into west,south,east,north and reject boxes that are not a real boundary.
 */
export function normalizeBbox(west: number, south: number, east: number, north: number): BBox | null {
  if (![west, south, east, north].every((value) => Number.isFinite(value))) return null;
  const minWest = Math.min(west, east);
  const maxEast = Math.max(west, east);
  const minSouth = Math.min(south, north);
  const maxNorth = Math.max(south, north);
  if (maxEast - minWest < MIN_AOI_SPAN_DEG || maxNorth - minSouth < MIN_AOI_SPAN_DEG) return null;
  if (minWest < -180 || maxEast > 180 || minSouth < -90 || maxNorth > 90) return null;
  return [minWest, minSouth, maxEast, maxNorth];
}

/** Approximate ground area of a lng/lat box. Enough for the AOI chip, not a survey. */
export function bboxAreaAcres(bbox: BBox): number {
  const [west, south, east, north] = bbox;
  const midLatRad = ((south + north) / 2) * (Math.PI / 180);
  const widthM = Math.abs(east - west) * M_PER_DEG_LON_EQUATOR * Math.cos(midLatRad);
  const heightM = Math.abs(north - south) * M_PER_DEG_LAT;
  return (widthM * heightM) / SQ_M_PER_ACRE;
}

export function bboxPolygonFeature(bbox: BBox): GeoJSON.Feature<GeoJSON.Polygon, { kind: "aoi" }> {
  const [west, south, east, north] = bbox;
  return {
    type: "Feature",
    properties: { kind: "aoi" },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [west, south],
          [east, south],
          [east, north],
          [west, north],
          [west, south],
        ],
      ],
    },
  };
}

export function aoiFeatureCollection(
  bbox: BBox | null,
): GeoJSON.FeatureCollection<GeoJSON.Polygon, { kind: "aoi" }> {
  return {
    type: "FeatureCollection",
    features: bbox ? [bboxPolygonFeature(bbox)] : [],
  };
}

export function featuresIntersectingBbox<T extends { properties: { centroid?: [number, number] } }>(
  features: T[],
  bbox: BBox,
): T[] {
  return features.filter((feature) => featureIntersectsBbox(feature.properties.centroid, bbox));
}
