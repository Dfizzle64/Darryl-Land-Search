import { readFile } from "node:fs/promises";
import path from "node:path";
import type { BBox, IncomeInfo, NearestRoad, ParcelFeature } from "./types";

/**
 * Orange County ACS income and FDOT AADT from the pilot fixtures.
 * The 5–150 acre extract does not store these fields. Viewport and AOI
 * queries attach them before filters run so the income and AADT sliders
 * hide non-matching Orange parcels the way the small sample did.
 */

const DATA_DIR = path.join(process.cwd(), "data", "fixtures");
const M_PER_DEG = 111_320;

export type SignalPolygon = {
  bbox: BBox;
  outer: number[][];
  holes: number[][][];
  info: IncomeInfo;
};

export type SignalRoad = {
  bbox: BBox;
  coords: [number, number][];
  aadt: number | null;
  year: number | null;
  roadwayId: string | null;
  from: string | null;
  to: string | null;
};

export type OrangeSignalIndex = {
  coverage: BBox;
  tracts: SignalPolygon[];
  blockGroups: SignalPolygon[];
  roads: SignalRoad[];
};

const EMPTY_INCOME: IncomeInfo = {
  geoid: null,
  name: null,
  medianHouseholdIncome: null,
  medianHouseholdIncomeMoe: null,
};

let indexPromise: Promise<OrangeSignalIndex> | null = null;

export function pointInRing(x: number, y: number, ring: number[][]): boolean {
  let inside = false;
  const n = ring.length;
  let j = n - 1;
  for (let i = 0; i < n; i += 1) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / ((yj - yi) || 1e-12) + xi) {
      inside = !inside;
    }
    j = i;
  }
  return inside;
}

export function pointInPolygon(x: number, y: number, polygon: SignalPolygon): boolean {
  const [west, south, east, north] = polygon.bbox;
  if (x < west || x > east || y < south || y > north) return false;
  if (!pointInRing(x, y, polygon.outer)) return false;
  return polygon.holes.every((hole) => !pointInRing(x, y, hole));
}

export function lookupIncome(x: number, y: number, polygons: SignalPolygon[]): IncomeInfo | null {
  for (const polygon of polygons) {
    if (pointInPolygon(x, y, polygon)) return polygon.info;
  }
  return null;
}

function distPointToSeg(px: number, py: number, ax: number, ay: number, bx: number, by: number): number {
  const dx = bx - ax;
  const dy = by - ay;
  if (dx === 0 && dy === 0) return Math.hypot(px - ax, py - ay);
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

export function minDistToLine(px: number, py: number, line: [number, number][]): number {
  let best = Number.POSITIVE_INFINITY;
  for (let i = 0; i < line.length - 1; i += 1) {
    const d = distPointToSeg(px, py, line[i][0], line[i][1], line[i + 1][0], line[i + 1][1]);
    if (d < best) best = d;
  }
  return best;
}

function bboxGap(x: number, y: number, bbox: BBox): number {
  const [west, south, east, north] = bbox;
  const dx = x < west ? west - x : x > east ? x - east : 0;
  const dy = y < south ? south - y : y > north ? y - north : 0;
  return Math.hypot(dx, dy);
}

export function nearestRoad(x: number, y: number, roads: SignalRoad[]): NearestRoad | null {
  let best: SignalRoad | null = null;
  let bestDist = Number.POSITIVE_INFINITY;
  for (const road of roads) {
    if (bboxGap(x, y, road.bbox) >= bestDist) continue;
    const dist = minDistToLine(x, y, road.coords);
    if (dist < bestDist) {
      bestDist = dist;
      best = road;
    }
  }
  if (!best) return null;
  return {
    aadt: best.aadt,
    year: best.year,
    roadwayId: best.roadwayId,
    from: best.from,
    to: best.to,
    distanceMeters: Math.round(bestDist * M_PER_DEG),
  };
}

function ringBbox(ring: number[][]): BBox {
  let west = Number.POSITIVE_INFINITY;
  let south = Number.POSITIVE_INFINITY;
  let east = Number.NEGATIVE_INFINITY;
  let north = Number.NEGATIVE_INFINITY;
  for (const coord of ring) {
    west = Math.min(west, coord[0]);
    east = Math.max(east, coord[0]);
    south = Math.min(south, coord[1]);
    north = Math.max(north, coord[1]);
  }
  return [west, south, east, north];
}

function incomeFromProps(props: GeoJSON.GeoJsonProperties): IncomeInfo {
  const income = props?.medianHouseholdIncome;
  const moe = props?.medianHouseholdIncomeMoe;
  return {
    geoid: typeof props?.geoid === "string" ? props.geoid : null,
    name: typeof props?.name === "string" ? props.name : null,
    medianHouseholdIncome: typeof income === "number" && Number.isFinite(income) ? income : null,
    medianHouseholdIncomeMoe: typeof moe === "number" && Number.isFinite(moe) ? moe : null,
  };
}

function polygonsFromCollection(collection: GeoJSON.FeatureCollection): SignalPolygon[] {
  const out: SignalPolygon[] = [];
  for (const feature of collection.features) {
    const info = incomeFromProps(feature.properties);
    const geometry = feature.geometry;
    if (!geometry) continue;
    const parts = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.type === "MultiPolygon" ? geometry.coordinates : [];
    for (const part of parts) {
      if (!part[0] || part[0].length < 3) continue;
      out.push({
        bbox: ringBbox(part[0]),
        outer: part[0],
        holes: part.slice(1),
        info,
      });
    }
  }
  return out;
}

function roadsFromCollection(collection: GeoJSON.FeatureCollection<GeoJSON.LineString>): SignalRoad[] {
  const out: SignalRoad[] = [];
  for (const feature of collection.features) {
    const coords = feature.geometry?.coordinates as [number, number][] | undefined;
    if (!coords || coords.length < 2) continue;
    const props = feature.properties ?? {};
    const aadt = props.aadt;
    const year = props.year;
    out.push({
      bbox: ringBbox(coords),
      coords,
      aadt: typeof aadt === "number" && Number.isFinite(aadt) ? aadt : null,
      year: typeof year === "number" && Number.isFinite(year) ? year : null,
      roadwayId: typeof props.roadwayId === "string" ? props.roadwayId : null,
      from: typeof props.from === "string" ? props.from : null,
      to: typeof props.to === "string" ? props.to : null,
    });
  }
  return out;
}

function unionBbox(boxes: BBox[]): BBox {
  if (!boxes.length) return [-81.66, 28.34, -80.86, 28.79];
  return boxes.reduce(
    (acc, box) => [
      Math.min(acc[0], box[0]),
      Math.min(acc[1], box[1]),
      Math.max(acc[2], box[2]),
      Math.max(acc[3], box[3]),
    ],
    [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY] as BBox,
  );
}

export function buildOrangeSignalIndex(
  tracts: GeoJSON.FeatureCollection,
  blockGroups: GeoJSON.FeatureCollection,
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>,
): OrangeSignalIndex {
  const tractPolygons = polygonsFromCollection(tracts);
  const blockGroupPolygons = polygonsFromCollection(blockGroups);
  const roads = roadsFromCollection(traffic);
  return {
    coverage: unionBbox([...tractPolygons.map((item) => item.bbox), ...roads.map((item) => item.bbox)]),
    tracts: tractPolygons,
    blockGroups: blockGroupPolygons,
    roads,
  };
}

export function coverageContains(index: OrangeSignalIndex, lon: number, lat: number): boolean {
  const [west, south, east, north] = index.coverage;
  return lon >= west && lon <= east && lat >= south && lat <= north;
}

/**
 * Fill missing Orange income and AADT on a parcel already in memory.
 * Points outside the Orange signal coverage are left unknown.
 */
export function annotateParcelSignals(feature: ParcelFeature, index: OrangeSignalIndex): void {
  const centroid = feature.properties.centroid;
  if (!centroid || !coverageContains(index, centroid[0], centroid[1])) return;
  const [lon, lat] = centroid;
  if (feature.properties.incomeTract == null) {
    feature.properties.incomeTract = lookupIncome(lon, lat, index.tracts) ?? EMPTY_INCOME;
  }
  if (feature.properties.incomeBlockGroup == null) {
    feature.properties.incomeBlockGroup = lookupIncome(lon, lat, index.blockGroups) ?? EMPTY_INCOME;
  }
  if (feature.properties.nearestRoad == null) {
    feature.properties.nearestRoad = nearestRoad(lon, lat, index.roads);
  }
}

export async function loadOrangeSignalIndex(): Promise<OrangeSignalIndex> {
  if (!indexPromise) {
    indexPromise = (async () => {
      const [tractsRaw, blockGroupsRaw, trafficRaw] = await Promise.all([
        readFile(path.join(DATA_DIR, "income-tracts.geojson"), "utf8"),
        readFile(path.join(DATA_DIR, "income-block-groups.geojson"), "utf8"),
        readFile(path.join(DATA_DIR, "traffic.geojson"), "utf8"),
      ]);
      return buildOrangeSignalIndex(
        JSON.parse(tractsRaw) as GeoJSON.FeatureCollection,
        JSON.parse(blockGroupsRaw) as GeoJSON.FeatureCollection,
        JSON.parse(trafficRaw) as GeoJSON.FeatureCollection<GeoJSON.LineString>,
      );
    })();
  }
  return indexPromise;
}
