import path from "node:path";
import { readdir, readFile } from "node:fs/promises";
import { bboxIntersects, tileFileName, tileIndicesForBbox } from "../orlandoParcels";
import type { BBox, ParcelFeature } from "../types";
import { loadMarketParcelIndex } from "./marketParcelStore";
import { queryMarketFixtureParcels } from "./marketParcelStore";
import { loadOrlandoParcelsMeta, queryOrlandoFixtureParcels, type OrlandoParcelPage } from "./orlandoParcelStore";

type FileCoverage = { market: string; bbox: BBox };

type ParcelViewIndex = {
  tiles: Map<string, string[]>;
  files: FileCoverage[];
};

let cachedIndex: ParcelViewIndex | null = null;

function addTile(tiles: Map<string, Set<string>>, fileName: string, market: string) {
  const set = tiles.get(fileName) ?? new Set<string>();
  set.add(market);
  tiles.set(fileName, set);
}

function bboxOfGeometry(geometry: GeoJSON.Geometry | null | undefined, into: number[]) {
  const walk = (coords: unknown) => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      into[0] = Math.min(into[0], coords[0]);
      into[1] = Math.min(into[1], coords[1]);
      into[2] = Math.max(into[2], coords[0]);
      into[3] = Math.max(into[3], coords[1]);
      return;
    }
    for (const child of coords) walk(child);
  };
  if (geometry && "coordinates" in geometry) walk(geometry.coordinates);
}

async function fileBbox(relativePath: string): Promise<BBox | null> {
  try {
    const raw = await readFile(path.join(process.cwd(), relativePath), "utf8");
    const collection = JSON.parse(raw) as { features?: Array<{ geometry?: GeoJSON.Geometry }> };
    const bounds = [Infinity, Infinity, -Infinity, -Infinity];
    for (const feature of collection.features ?? []) bboxOfGeometry(feature.geometry, bounds);
    if (!bounds.every((value) => Number.isFinite(value))) return null;
    return [bounds[0], bounds[1], bounds[2], bounds[3]];
  } catch {
    return null;
  }
}

async function tileNames(relativeDir: string): Promise<string[]> {
  try {
    const names = await readdir(path.join(process.cwd(), relativeDir));
    return names.filter((name) => name.endsWith(".geojson"));
  } catch {
    return [];
  }
}

/** Which markets have a 5–150 acre extract touching this bbox. Cached after the first call. */
export async function marketsCoveringBbox(bbox: BBox): Promise<string[]> {
  const index = await loadParcelViewIndex();
  const found = new Set<string>();
  const { ix0, ix1, iy0, iy1 } = tileIndicesForBbox(bbox);
  for (let ix = ix0; ix <= ix1; ix += 1) {
    for (let iy = iy0; iy <= iy1; iy += 1) {
      for (const market of index.tiles.get(tileFileName(ix, iy)) ?? []) found.add(market);
    }
  }
  for (const file of index.files) {
    if (bboxIntersects(file.bbox, bbox)) found.add(file.market);
  }
  return [...found];
}

export async function loadParcelViewIndex(): Promise<ParcelViewIndex> {
  if (cachedIndex) return cachedIndex;
  const tiles = new Map<string, Set<string>>();
  const files: FileCoverage[] = [];

  const orlando = await loadOrlandoParcelsMeta();
  await Promise.all(
    orlando.counties.map(async (county) => {
      if (!county.path) return;
      if (county.partition === "tiles") {
        for (const name of await tileNames(county.path)) addTile(tiles, name, "Orlando");
        return;
      }
      const bbox = await fileBbox(county.path);
      if (bbox) files.push({ market: "Orlando", bbox });
    }),
  );

  const marketIndex = await loadMarketParcelIndex();
  await Promise.all(
    Object.keys(marketIndex.markets).map(async (market) => {
      const summary = marketIndex.markets[market];
      if (!summary?.path) return;
      try {
        const meta = JSON.parse(await readFile(path.join(process.cwd(), summary.path), "utf8")) as {
          counties?: Array<{ path?: string | null; partition?: string }>;
        };
        await Promise.all(
          (meta.counties ?? []).map(async (county) => {
            if (!county.path) return;
            if (county.partition === "tiles") {
              for (const name of await tileNames(county.path)) addTile(tiles, name, market);
              return;
            }
            const bbox = await fileBbox(county.path);
            if (bbox) files.push({ market, bbox });
          }),
        );
      } catch {
        // A market with no meta file contributes no parcels.
      }
    }),
  );

  cachedIndex = {
    tiles: new Map([...tiles.entries()].map(([name, markets]) => [name, [...markets]])),
    files,
  };
  return cachedIndex;
}

export type ParcelViewPage = OrlandoParcelPage & {
  markets: string[];
  covered: boolean;
};

/** Every 5–150 acre parcel in the bbox, from whichever market extract actually covers it. */
export async function queryParcelsInView(bbox: BBox): Promise<ParcelViewPage> {
  const markets = await marketsCoveringBbox(bbox);
  if (!markets.length) {
    return {
      collection: { type: "FeatureCollection", features: [] },
      excluded: [],
      totalInBbox: 0,
      totalMatching: 0,
      truncated: false,
      markets: [],
      covered: false,
    };
  }
  const pages = await Promise.all(
    markets.map((market) =>
      market === "Orlando"
        ? queryOrlandoFixtureParcels({ bbox, complete: true })
        : queryMarketFixtureParcels(market, { bbox, complete: true }),
    ),
  );
  const byId = new Map<string, ParcelFeature>();
  for (const page of pages) {
    for (const feature of page.collection.features) byId.set(feature.properties.id, feature);
  }
  const features = [...byId.values()];
  return {
    collection: { type: "FeatureCollection", features },
    excluded: [],
    totalInBbox: features.length,
    totalMatching: features.length,
    truncated: false,
    markets,
    covered: true,
  };
}
