import { scNominatedOverlayFilter, showOzTractInScMarkets } from "./scNominatedTracts";

/**
 * Eligible tracts draw from a Southeast-wide view. Below this zoom the overlay
 * stays off so a continental pan does not paint the whole country.
 */
export const TRACT_MIN_ZOOM = 4;

/**
 * Zooms 4–7 use the precomputed dissolved overlay. At this zoom the map
 * switches to per-tract geometry.
 */
export const TRACT_DETAIL_MIN_ZOOM = 8;

/** Wait until the camera rests before merging another viewport of tract tiles. */
export const TRACT_VIEWPORT_DEBOUNCE_MS = 350;

/**
 * Stable degree grid for the detail cache. Keys are independent of zoom so a
 * tile loaded at tract scale is not fetched again after a small zoom change.
 */
export const TRACT_TILE_DEGREES = 2;

export type TractBbox = [number, number, number, number];

export type TractProps = {
  tractGeoid?: string;
  state?: string | null;
  county?: string | null;
  rural?: boolean | null;
};

export type IndexedTractFeature = GeoJSON.Feature<GeoJSON.Geometry, TractProps>;

export type TractDetailBucket = {
  rural: IndexedTractFeature[];
  eligible: IndexedTractFeature[];
  oz2: IndexedTractFeature[];
};

export type EligibleTractTileCache = {
  signature: string;
  tiles: Map<string, TractDetailBucket>;
  loaded: Set<string>;
  rural: Map<string, IndexedTractFeature>;
  eligible: Map<string, IndexedTractFeature>;
  oz2: Map<string, IndexedTractFeature>;
};

export type TractClassCut = "all" | "rural" | "urban" | "none";

export function tractsVisibleAtZoom(zoom: number): boolean {
  return Number.isFinite(zoom) && zoom >= TRACT_MIN_ZOOM;
}

export function detailTractsVisibleAtZoom(zoom: number): boolean {
  return Number.isFinite(zoom) && zoom >= TRACT_DETAIL_MIN_ZOOM;
}

/** Inclusive of zoom 4, exclusive of the detail zoom. */
export function overviewTractsVisibleAtZoom(zoom: number): boolean {
  return tractsVisibleAtZoom(zoom) && zoom < TRACT_DETAIL_MIN_ZOOM;
}

/**
 * A tract is drawn only when a fixture already marked it eligible (rural true
 * or false). Missing eligibility is left off the map. South Carolina keeps the
 * governor-nominated list only.
 */
export function isDrawnEligibleTract(properties: TractProps | null | undefined): boolean {
  if (!properties?.tractGeoid) return false;
  if (properties.rural !== true && properties.rural !== false) return false;
  return showOzTractInScMarkets({ state: properties.state, geoid: properties.tractGeoid });
}

export function geometryBbox(geometry: GeoJSON.Geometry | null | undefined): TractBbox | null {
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  let found = false;
  const walk = (coords: unknown) => {
    if (!Array.isArray(coords)) return;
    if (coords.length >= 2 && typeof coords[0] === "number" && typeof coords[1] === "number") {
      found = true;
      const lng = coords[0];
      const lat = coords[1];
      if (lng < west) west = lng;
      if (lng > east) east = lng;
      if (lat < south) south = lat;
      if (lat > north) north = lat;
      return;
    }
    for (const child of coords) walk(child);
  };
  if (geometry && "coordinates" in geometry) walk(geometry.coordinates);
  if (!found) return null;
  return [west, south, east, north];
}

/** Absolute grid keys for a bbox. The same area always returns the same keys. */
export function tractGridKeysForBbox(bbox: TractBbox, tileDegrees = TRACT_TILE_DEGREES): string[] {
  const [west, south, east, north] = bbox;
  if (![west, south, east, north].every((value) => Number.isFinite(value))) return [];
  if (east < west || north < south) return [];
  const x0 = Math.floor(west / tileDegrees);
  const x1 = Math.floor(Math.max(west, east - 1e-9) / tileDegrees);
  const y0 = Math.floor(south / tileDegrees);
  const y1 = Math.floor(Math.max(south, north - 1e-9) / tileDegrees);
  const keys: string[] = [];
  for (let x = x0; x <= x1; x += 1) {
    for (let y = y0; y <= y1; y += 1) {
      keys.push(`${x}:${y}`);
    }
  }
  return keys;
}

function emptyBucket(): TractDetailBucket {
  return { rural: [], eligible: [], oz2: [] };
}

function indexBuckets(groups: TractDetailBucket): Map<string, TractDetailBucket> {
  const tiles = new Map<string, TractDetailBucket>();
  const add = (kind: keyof TractDetailBucket, feature: IndexedTractFeature) => {
    if (!isDrawnEligibleTract(feature.properties)) return;
    const bbox = geometryBbox(feature.geometry);
    if (!bbox) return;
    for (const key of tractGridKeysForBbox(bbox)) {
      let bucket = tiles.get(key);
      if (!bucket) {
        bucket = emptyBucket();
        tiles.set(key, bucket);
      }
      bucket[kind].push(feature);
    }
  };
  for (const feature of groups.rural) add("rural", feature);
  for (const feature of groups.eligible) add("eligible", feature);
  for (const feature of groups.oz2) add("oz2", feature);
  return tiles;
}

export function createEligibleTractTileCache(): EligibleTractTileCache {
  return {
    signature: "",
    tiles: new Map(),
    loaded: new Set(),
    rural: new Map(),
    eligible: new Map(),
    oz2: new Map(),
  };
}

/**
 * Build the grid once per fixture signature. Repeat calls with the same
 * signature keep tiles that were already merged into the map sources.
 */
export function syncEligibleTractTileCache(
  cache: EligibleTractTileCache,
  groups: TractDetailBucket,
  signature: string,
): void {
  if (cache.signature === signature) return;
  cache.signature = signature;
  cache.tiles = indexBuckets(groups);
  cache.loaded.clear();
  cache.rural.clear();
  cache.eligible.clear();
  cache.oz2.clear();
}

/**
 * Merge grid cells that are not already loaded. Loaded keys are skipped, so a
 * pan back across the same ground does not rebuild those tiles.
 */
export function absorbEligibleTractTiles(
  cache: EligibleTractTileCache,
  keys: string[],
): { rural: boolean; eligible: boolean; oz2: boolean } {
  const changed = { rural: false, eligible: false, oz2: false };
  for (const key of keys) {
    if (cache.loaded.has(key)) continue;
    cache.loaded.add(key);
    const bucket = cache.tiles.get(key);
    if (!bucket) continue;
    for (const kind of ["rural", "eligible", "oz2"] as const) {
      const stored = cache[kind];
      for (const feature of bucket[kind]) {
        const id = feature.properties?.tractGeoid;
        if (!id || stored.has(id)) continue;
        stored.set(id, feature);
        changed[kind] = true;
      }
    }
  }
  return changed;
}

/**
 * Detail-layer filter. No market clause: every eligible tract in the viewport
 * stays on the map. The header market only moves the camera.
 */
export function eligibleTractOverlayFilter(options: {
  hideOrangeCounty?: boolean;
  geoids?: string[] | null;
  classCut?: TractClassCut;
} = {}): unknown[] {
  const classCut = options.classCut ?? "all";
  const parts: unknown[] = [];
  if (options.hideOrangeCounty) {
    parts.push(["!", ["all", ["==", ["get", "state"], "Florida"], ["==", ["get", "county"], "Orange"]]]);
  }
  if (classCut === "none") parts.push(["==", ["get", "tractGeoid"], "__none__"]);
  if (classCut === "urban") parts.push(["==", ["get", "rural"], false]);
  if (classCut === "rural") parts.push(["==", ["get", "rural"], true]);
  if (options.geoids) {
    parts.push(
      options.geoids.length === 0
        ? ["==", ["get", "tractGeoid"], "__none__"]
        : ["in", ["get", "tractGeoid"], ["literal", options.geoids]],
    );
  }
  parts.push(scNominatedOverlayFilter());
  if (parts.length === 1) return parts[0] as unknown[];
  return ["all", ...parts];
}

/** Far-zoom filter. Dissolved features have rural/urban, not a tract GEOID list. */
export function eligibleOverviewFilter(classCut: TractClassCut): unknown[] | null {
  if (classCut === "none") return ["==", ["get", "eligible"], "__hide__"];
  if (classCut === "rural") return ["==", ["get", "rural"], true];
  if (classCut === "urban") return ["==", ["get", "rural"], false];
  return null;
}
