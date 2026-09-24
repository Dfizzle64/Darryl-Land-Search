import { readFile } from "node:fs/promises";
import path from "node:path";
import type { BBox, IncomeInfo, NearestRoad, ParcelFeature } from "./types";

/**
 * ACS median household income and FDOT AADT joined at query time.
 * Tiles do not store these fields (they would duplicate the same tract and
 * road onto every parcel). The income fixture is ACS B19013 for Florida
 * parcel counties plus Atlanta and Charleston parcel counties, joined by
 * centroid-in-tract on `medianHouseholdIncome`. AADT segments are statewide
 * FDOT counts. Points outside that coverage stay unknown.
 */

const DATA_DIR = path.join(process.cwd(), "data", "fixtures");
const M_PER_DEG = 111_320;
/** Nearest FDOT segment farther than this is unknown, not a distant highway. */
export const MAX_AADT_DISTANCE_METERS = 15_000;
const ROAD_CELL_DEG = 0.2;

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
  roadGrid: Map<string, number[]>;
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

export function indexRoads(roads: SignalRoad[], cell = ROAD_CELL_DEG): Map<string, number[]> {
  const grid = new Map<string, number[]>();
  roads.forEach((road, index) => {
    const [west, south, east, north] = road.bbox;
    const ix0 = Math.floor(west / cell);
    const ix1 = Math.floor(east / cell);
    const iy0 = Math.floor(south / cell);
    const iy1 = Math.floor(north / cell);
    for (let ix = ix0; ix <= ix1; ix += 1) {
      for (let iy = iy0; iy <= iy1; iy += 1) {
        const key = `${ix}:${iy}`;
        const bucket = grid.get(key);
        if (bucket) bucket.push(index);
        else grid.set(key, [index]);
      }
    }
  });
  return grid;
}

export function nearestRoad(
  x: number,
  y: number,
  roads: SignalRoad[],
  grid?: Map<string, number[]>,
  maxMeters = MAX_AADT_DISTANCE_METERS,
): NearestRoad | null {
  const maxDeg = maxMeters / M_PER_DEG;
  // A closure assignment is not visible to control-flow narrowing, so keep
  // the winner on an object. Otherwise `best` stays `null` and the return is `never`.
  const state: { best: SignalRoad | null; bestDist: number } = { best: null, bestDist: maxDeg };
  const consider = (index: number) => {
    const road = roads[index];
    if (!road || bboxGap(x, y, road.bbox) >= state.bestDist) return;
    const dist = minDistToLine(x, y, road.coords);
    if (dist < state.bestDist) {
      state.bestDist = dist;
      state.best = road;
    }
  };
  if (grid && grid.size) {
    const reach = Math.max(1, Math.ceil(maxDeg / ROAD_CELL_DEG));
    const ix = Math.floor(x / ROAD_CELL_DEG);
    const iy = Math.floor(y / ROAD_CELL_DEG);
    const seen = new Set<number>();
    for (let dx = -reach; dx <= reach; dx += 1) {
      for (let dy = -reach; dy <= reach; dy += 1) {
        for (const index of grid.get(`${ix + dx}:${iy + dy}`) ?? []) {
          if (seen.has(index)) continue;
          seen.add(index);
          consider(index);
        }
      }
    }
  } else {
    for (let index = 0; index < roads.length; index += 1) consider(index);
  }
  if (!state.best) return null;
  return {
    aadt: state.best.aadt,
    year: state.best.year,
    roadwayId: state.best.roadwayId,
    from: state.best.from,
    to: state.best.to,
    distanceMeters: Math.round(state.bestDist * M_PER_DEG),
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
    roadGrid: indexRoads(roads),
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
    feature.properties.nearestRoad = nearestRoad(lon, lat, index.roads, index.roadGrid);
  }
}

export async function loadOrangeSignalIndex(): Promise<OrangeSignalIndex> {
  if (!indexPromise) {
    indexPromise = (async () => {
      const segmentsPath = path.join(DATA_DIR, "aadt-segments.geojson");
      const [tractsRaw, blockGroupsRaw, trafficRaw] = await Promise.all([
        readFile(path.join(DATA_DIR, "income-tracts.geojson"), "utf8"),
        readFile(path.join(DATA_DIR, "income-block-groups.geojson"), "utf8"),
        readFile(segmentsPath, "utf8").catch(() => readFile(path.join(DATA_DIR, "traffic.geojson"), "utf8")),
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
