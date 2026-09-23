import path from "node:path";
import { access, readFile } from "node:fs/promises";
import { featureIntersectsBbox, tileFileName, tileIndicesForBbox } from "../orlandoParcels";
import { featuresInAcreageBand, type MarketParcelIndex, type MarketParcelsMeta } from "../marketParcels";
import type { ParcelCollection, ParcelFeature, ParcelProperties, SearchMarketId } from "../types";
import { annotateParcelSignals, loadOrangeSignalIndex } from "../orangeSignals";
import { finalizeOrlandoParcelPage, type OrlandoParcelPage, type OrlandoParcelQuery } from "./orlandoParcelStore";

const INDEX_PATH = path.join(process.cwd(), "data/fixtures/market-parcels/index.json");

let cachedIndex: MarketParcelIndex | null = null;
const metaCache = new Map<string, MarketParcelsMeta>();
const tileCache = new Map<string, ParcelFeature[]>();
const lookupCache = new Map<string, Record<string, string>>();
const TILE_CACHE_LIMIT = 48;

const EMPTY_INDEX: MarketParcelIndex = {
  generatedAt: "",
  coreMinAcres: 5,
  coreMaxAcres: 150,
  tile: { originLon: -83, originLat: 27, tileDeg: 0.25 },
  markets: {},
};

export async function loadMarketParcelIndex(): Promise<MarketParcelIndex> {
  if (cachedIndex) return cachedIndex;
  try {
    const raw = await readFile(INDEX_PATH, "utf8");
    cachedIndex = JSON.parse(raw) as MarketParcelIndex;
  } catch {
    cachedIndex = EMPTY_INDEX;
  }
  return cachedIndex;
}

async function loadMarketMeta(market: string): Promise<MarketParcelsMeta | null> {
  const cached = metaCache.get(market);
  if (cached) return cached;
  const index = await loadMarketParcelIndex();
  const summary = index.markets[market];
  if (!summary?.path) return null;
  try {
    const raw = await readFile(path.join(process.cwd(), summary.path), "utf8");
    const meta = JSON.parse(raw) as MarketParcelsMeta;
    metaCache.set(market, meta);
    return meta;
  } catch {
    return null;
  }
}

function stampCountyGaps(features: ParcelFeature[], gaps: string[] | undefined): ParcelFeature[] {
  if (!gaps?.length) return features;
  for (const feature of features) {
    if (!feature.properties.dataGaps?.length) feature.properties.dataGaps = gaps;
  }
  return features;
}

function normalizeParcel(feature: ParcelFeature): ParcelFeature {
  const props = feature.properties as ParcelProperties;
  if (props.flu === undefined) props.flu = null;
  if (props.opportunityZone === undefined) props.opportunityZone = null;
  if (props.oz2Eligibility === undefined) props.oz2Eligibility = null;
  if (props.incomeTract === undefined) props.incomeTract = null;
  if (props.incomeBlockGroup === undefined) props.incomeBlockGroup = null;
  if (props.nearestRoad === undefined) props.nearestRoad = null;
  feature.properties = props;
  return feature;
}

async function readFeatureFile(relativePath: string): Promise<ParcelFeature[]> {
  const cached = tileCache.get(relativePath);
  if (cached) return cached;
  try {
    await access(path.join(process.cwd(), relativePath));
  } catch {
    return [];
  }
  const raw = await readFile(path.join(process.cwd(), relativePath), "utf8");
  const collection = JSON.parse(raw) as ParcelCollection;
  const features = collection.features.map((feature) => normalizeParcel(feature));
  tileCache.set(relativePath, features);
  if (tileCache.size > TILE_CACHE_LIMIT) {
    const oldest = tileCache.keys().next().value;
    if (oldest) tileCache.delete(oldest);
  }
  return features;
}

async function featuresForCounty(
  county: MarketParcelsMeta["counties"][number],
  bbox: [number, number, number, number] | null,
): Promise<ParcelFeature[]> {
  if (!county.path || county.partition === "none") return [];
  if (county.partition === "tiles") {
    if (!bbox) {
      const { readdir } = await import("node:fs/promises");
      try {
        const names = await readdir(path.join(process.cwd(), county.path));
        const groups = await Promise.all(
          names.filter((name) => name.endsWith(".geojson")).map((name) => readFeatureFile(path.join(county.path!, name))),
        );
        return stampCountyGaps(groups.flat(), county.gaps);
      } catch {
        return [];
      }
    }
    const { ix0, ix1, iy0, iy1 } = tileIndicesForBbox(bbox);
    const paths: string[] = [];
    for (let ix = ix0; ix <= ix1; ix += 1) {
      for (let iy = iy0; iy <= iy1; iy += 1) {
        paths.push(path.join(county.path, tileFileName(ix, iy)));
      }
    }
    const groups = await Promise.all(paths.map((tilePath) => readFeatureFile(tilePath)));
    return stampCountyGaps(groups.flat(), county.gaps);
  }
  return stampCountyGaps(await readFeatureFile(county.path), county.gaps);
}

async function finalizeMarketParcelPage(
  features: ParcelFeature[],
  query: OrlandoParcelQuery,
): Promise<OrlandoParcelPage> {
  // Same income/AADT join as Orlando. Counties outside the Florida fixtures stay unknown.
  return finalizeOrlandoParcelPage(features, query);
}

export async function queryMarketFixtureParcels(
  market: string,
  query: OrlandoParcelQuery = {},
): Promise<OrlandoParcelPage> {
  const meta = await loadMarketMeta(market);
  if (!meta) {
    return { collection: { type: "FeatureCollection", features: [] }, excluded: [], totalInBbox: 0, totalMatching: 0, truncated: false };
  }
  const county = query.county ?? null;
  const state = query.state ?? null;
  const counties = meta.counties.filter((item) => {
    if (!county || !state) return true;
    return item.name === county && item.state === state;
  });
  const bbox = query.bbox ?? null;
  const groups = await Promise.all(
    counties.map(async (item) => {
      let features = featuresInAcreageBand(await featuresForCounty(item, bbox));
      if (item.path?.includes("orlando-parcels")) {
        features = features.map((feature) => ({
          ...feature,
          properties: { ...feature.properties, marketIds: [market as SearchMarketId] },
        }));
      }
      if (!bbox) return features;
      return features.filter((feature) => featureIntersectsBbox(feature.properties.centroid, bbox));
    }),
  );
  return finalizeMarketParcelPage(groups.flat(), query);
}

export async function getMarketFixtureParcel(id: string): Promise<ParcelFeature | null> {
  const split = id.indexOf(":");
  if (split <= 0) return null;
  const fips = id.slice(0, split);
  const parcelId = id.slice(split + 1);
  const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips, "county.json");
  try {
    const row = JSON.parse(await readFile(countyPath, "utf8")) as MarketParcelsMeta["counties"][number] & {
      lookup?: string | null;
    };
    if (!row.path) return null;
    if (row.partition === "tiles" && row.lookup) {
      let lookup = lookupCache.get(fips);
      if (!lookup) {
        lookup = JSON.parse(await readFile(path.join(process.cwd(), row.lookup), "utf8")) as Record<string, string>;
        lookupCache.set(fips, lookup);
      }
      const tile = lookup[parcelId];
      if (!tile) return null;
      const features = stampCountyGaps(await readFeatureFile(path.join(row.path, `${tile}.geojson`)), row.gaps);
      return annotateLoadedParcel(features.find((feature) => feature.properties.id === id) ?? null);
    }
    const features = stampCountyGaps(await readFeatureFile(row.path), row.gaps);
    return annotateLoadedParcel(features.find((feature) => feature.properties.id === id) ?? null);
  } catch {
    return null;
  }
}

async function annotateLoadedParcel(feature: ParcelFeature | null): Promise<ParcelFeature | null> {
  if (!feature) return null;
  annotateParcelSignals(feature, await loadOrangeSignalIndex());
  return feature;
}
