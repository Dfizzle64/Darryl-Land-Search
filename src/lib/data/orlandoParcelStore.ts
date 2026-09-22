import path from "node:path";
import { access, readFile } from "node:fs/promises";
import {
  ORLANDO_DOH_LAYER_BY_FIPS,
  ORLANDO_DOH_PARCELS_BASE,
  ORLANDO_NAME_BY_FIPS,
  featureIntersectsBbox,
  fipsForOrlandoCountyFilter,
  fipsIntersectingBbox,
  spatiallyThinFeatures,
  tileFileName,
  tileIndicesForBbox,
} from "../orlandoParcels";
import type {
  BBox,
  OrlandoParcelCountyMeta,
  OrlandoParcelsMeta,
  ParcelCollection,
  ParcelFeature,
  ParcelProperties,
} from "../types";

const DATA_DIR = path.join(process.cwd(), "data");
const PARTITION_DIR = path.join(DATA_DIR, "fixtures/orlando-parcels");

const DOH_OUT_FIELDS = [
  "PARCEL_ID",
  "OWN_NAME",
  "PHY_ADDR1",
  "PHY_CITY",
  "PHY_ZIPCD",
  "LND_SQFOOT",
  "JV",
  "AV_SD",
  "TV_SD",
  "DOR_UC",
  "SALE_PRC1",
  "SALE_YR1",
  "SALE_MO1",
  "QUAL_CD1",
  "OWN_ADDR1",
  "OWN_ADDR2",
  "OWN_CITY",
  "OWN_STATE",
  "OWN_ZIPCD",
].join(",");

let cachedMeta: OrlandoParcelsMeta | null = null;
const tileCache = new Map<string, ParcelFeature[]>();
const lookupCache = new Map<string, Record<string, string>>();
const TILE_CACHE_LIMIT = 48;

export type OrlandoParcelPage = {
  collection: ParcelCollection;
  totalInBbox: number;
  truncated: boolean;
};

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

export async function loadOrlandoParcelsMeta(): Promise<OrlandoParcelsMeta> {
  if (cachedMeta) return cachedMeta;
  const raw = await readFile(path.join(PARTITION_DIR, "meta.json"), "utf8");
  cachedMeta = JSON.parse(raw) as OrlandoParcelsMeta;
  return cachedMeta;
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

function countyByFips(meta: OrlandoParcelsMeta, fips: string): OrlandoParcelCountyMeta | undefined {
  return meta.counties.find((county) => county.fips === fips);
}

async function featuresForCountyBbox(county: OrlandoParcelCountyMeta, bbox: BBox | null): Promise<ParcelFeature[]> {
  if (county.partition === "tiles") {
    if (!bbox) {
      const { readdir } = await import("node:fs/promises");
      const dir = path.join(process.cwd(), county.path);
      const names = await readdir(dir);
      const groups = await Promise.all(
        names.filter((name) => name.endsWith(".geojson")).map((name) => readFeatureFile(path.join(county.path, name))),
      );
      return groups.flat();
    }
    const { ix0, ix1, iy0, iy1 } = tileIndicesForBbox(bbox);
    const paths: string[] = [];
    for (let ix = ix0; ix <= ix1; ix += 1) {
      for (let iy = iy0; iy <= iy1; iy += 1) {
        paths.push(path.join(county.path, tileFileName(ix, iy)));
      }
    }
    const groups = await Promise.all(paths.map((tilePath) => readFeatureFile(tilePath)));
    return groups.flat();
  }
  return readFeatureFile(county.path);
}

export type OrlandoParcelQuery = {
  bbox?: BBox | null;
  county?: string | null;
  state?: string | null;
  limit?: number;
};

export async function queryOrlandoFixtureParcels(query: OrlandoParcelQuery = {}): Promise<OrlandoParcelPage> {
  const meta = await loadOrlandoParcelsMeta();
  const fipsAllow = fipsIntersectingBbox(
    query.bbox ?? null,
    fipsForOrlandoCountyFilter(query.county ?? null, query.state ?? "Florida"),
  );
  const bbox = query.bbox ?? null;
  const limit = query.limit ?? 4000;
  const groups = await Promise.all(
    fipsAllow.map(async (fips) => {
      const county = countyByFips(meta, fips);
      if (!county) return [];
      const features = await featuresForCountyBbox(county, bbox);
      if (!bbox) return features;
      return features.filter((feature) => featureIntersectsBbox(feature.properties.centroid, bbox));
    }),
  );
  const matched = groups.flat();
  const thinned = spatiallyThinFeatures(matched, limit);
  return {
    collection: { type: "FeatureCollection", features: thinned },
    totalInBbox: matched.length,
    truncated: thinned.length < matched.length,
  };
}

export async function getOrlandoFixtureParcel(id: string): Promise<ParcelFeature | null> {
  const split = id.indexOf(":");
  if (split <= 0) return null;
  const fips = id.slice(0, split);
  const parcelId = id.slice(split + 1);
  const meta = await loadOrlandoParcelsMeta();
  const county = countyByFips(meta, fips);
  if (!county) return null;
  if (county.partition === "tiles") {
    let lookup = lookupCache.get(fips);
    if (!lookup) {
      const raw = await readFile(path.join(PARTITION_DIR, "lookup", `${fips}.json`), "utf8");
      lookup = JSON.parse(raw) as Record<string, string>;
      lookupCache.set(fips, lookup);
    }
    const tile = lookup[parcelId];
    if (!tile) return null;
    const features = await readFeatureFile(path.join(county.path, `${tile}.geojson`));
    return features.find((feature) => feature.properties.id === id) ?? null;
  }
  const features = await readFeatureFile(county.path);
  return features.find((feature) => feature.properties.id === id) ?? null;
}

function num(value: unknown): number | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function clean(value: unknown): string | null {
  if (value == null) return null;
  const text = String(value).trim();
  return text || null;
}

function zipStr(value: unknown): string | null {
  const n = num(value);
  if (n == null) return clean(value);
  return String(Math.trunc(n)).padStart(5, "0").slice(0, 5);
}

function saleDate(year: unknown, month: unknown): string | null {
  const y = num(year);
  if (y == null || y < 1900 || y > 2100) return null;
  const m = num(month);
  const monthNum = m && m >= 1 && m <= 12 ? Math.trunc(m) : 1;
  return `${Math.trunc(y).toString().padStart(4, "0")}-${monthNum.toString().padStart(2, "0")}-01`;
}

function ringsToGeometry(rings: number[][][] | undefined): GeoJSON.Polygon | GeoJSON.MultiPolygon | null {
  if (!rings?.length) return null;
  const polygons: number[][][][] = [];
  let current: number[][][] = [];
  for (const ring of rings) {
    if (ring.length < 4) continue;
    const coords = ring.map(([x, y]) => [Math.round(x * 1e6) / 1e6, Math.round(y * 1e6) / 1e6]);
    if (coords[0][0] !== coords[coords.length - 1][0] || coords[0][1] !== coords[coords.length - 1][1]) {
      coords.push([...coords[0]]);
    }
    let area = 0;
    for (let i = 0; i < coords.length - 1; i += 1) {
      area += coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1];
    }
    if (!current.length || area > 0) {
      if (current.length) polygons.push(current);
      current = [coords];
    } else {
      current.push(coords);
    }
  }
  if (current.length) polygons.push(current);
  if (!polygons.length) return null;
  if (polygons.length === 1) return { type: "Polygon", coordinates: polygons[0] };
  return { type: "MultiPolygon", coordinates: polygons };
}

function centroidOf(geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon): [number, number] | null {
  const ring = geometry.type === "Polygon" ? geometry.coordinates[0] : geometry.coordinates[0]?.[0];
  if (!ring?.length) return null;
  const pts = ring.slice(0, -1);
  if (!pts.length) return null;
  const lon = pts.reduce((sum, p) => sum + p[0], 0) / pts.length;
  const lat = pts.reduce((sum, p) => sum + p[1], 0) / pts.length;
  return [Math.round(lon * 1e6) / 1e6, Math.round(lat * 1e6) / 1e6];
}

function normalizeLiveFeature(
  attrs: Record<string, unknown>,
  geometryRaw: { rings?: number[][][] } | null,
  fips: string,
): ParcelFeature | null {
  const geometry = ringsToGeometry(geometryRaw?.rings);
  if (!geometry) return null;
  const center = centroidOf(geometry);
  if (!center) return null;
  const parcelId = clean(attrs.PARCEL_ID);
  if (!parcelId) return null;
  const sqft = num(attrs.LND_SQFOOT);
  const acreage = sqft && sqft > 0 ? Math.round((sqft / 43560) * 10000) / 10000 : null;
  const price = num(attrs.SALE_PRC1);
  const id = `${fips}:${parcelId}`;
  const countyName = ORLANDO_NAME_BY_FIPS[fips] ?? null;
  const properties: ParcelProperties = {
    id,
    parcelId,
    countyFips: fips,
    countyName,
    state: "Florida",
    marketIds: ["Orlando"],
    situsAddress: clean(attrs.PHY_ADDR1),
    situsCity: clean(attrs.PHY_CITY),
    situsZip: zipStr(attrs.PHY_ZIPCD),
    jurisdictionCode: null,
    ownerName: clean(attrs.OWN_NAME),
    ownerName2: null,
    propertyName: null,
    zoningCode: null,
    zoningDistrict: null,
    jurisdictionPrefix: null,
    dorCode: clean(attrs.DOR_UC),
    acreage,
    centroid: center,
    lastSale: {
      date: saleDate(attrs.SALE_YR1, attrs.SALE_MO1),
      price: price && price > 0 ? price : null,
      qualified: clean(attrs.QUAL_CD1),
    },
    tax: {
      marketValue: num(attrs.JV),
      assessedValue: num(attrs.AV_SD),
      taxableValue: num(attrs.TV_SD),
      taxes: null,
    },
    mailingAddress: {
      line1: clean(attrs.OWN_ADDR1),
      line2: clean(attrs.OWN_ADDR2),
      city: clean(attrs.OWN_CITY),
      state: clean(attrs.OWN_STATE),
      zip: zipStr(attrs.OWN_ZIPCD),
    },
    incomeTract: null,
    incomeBlockGroup: null,
    nearestRoad: null,
    flu: null,
    opportunityZone: null,
    oz2Eligibility: null,
    source: `fl-doh-ehwaters-live-${fips}`,
    dataGaps: ["Live DOH extract has no zoning/FLU/AADT join"],
  };
  return { type: "Feature", id, properties, geometry };
}

async function queryDohLayer(fips: string, bbox: BBox, limit: number): Promise<ParcelFeature[]> {
  const layerId = ORLANDO_DOH_LAYER_BY_FIPS[fips];
  if (layerId == null) return [];
  const [west, south, east, north] = bbox;
  const params = new URLSearchParams({
    where: "LND_SQFOOT >= 217800",
    geometry: JSON.stringify({
      xmin: west,
      ymin: south,
      xmax: east,
      ymax: north,
      spatialReference: { wkid: 4326 },
    }),
    geometryType: "esriGeometryEnvelope",
    inSR: "4326",
    spatialRel: "esriSpatialRelIntersects",
    outFields: DOH_OUT_FIELDS,
    returnGeometry: "true",
    outSR: "4326",
    resultRecordCount: String(Math.min(limit, 400)),
    f: "json",
  });
  const response = await fetch(`${ORLANDO_DOH_PARCELS_BASE}/${layerId}/query?${params.toString()}`, {
    headers: { Accept: "application/json", "User-Agent": "darryl-land-search/orlando-live" },
    next: { revalidate: 60 * 30 },
  });
  if (!response.ok) {
    throw new Error(`DOH parcel query failed for ${fips} (${response.status})`);
  }
  const body = (await response.json()) as {
    error?: unknown;
    features?: Array<{ attributes?: Record<string, unknown>; geometry?: { rings?: number[][][] } }>;
  };
  if (body.error) {
    throw new Error(`DOH parcel query error for ${fips}`);
  }
  const out: ParcelFeature[] = [];
  for (const item of body.features ?? []) {
    const feature = normalizeLiveFeature(item.attributes ?? {}, item.geometry ?? null, fips);
    if (feature) out.push(feature);
  }
  return out;
}

/**
 * Live viewport query against public DOH layers. Caps total features so the
 * browser stays usable; fixtures remain the offline/demo path.
 */
export async function queryOrlandoLiveParcels(query: OrlandoParcelQuery): Promise<ParcelCollection> {
  const bbox = query.bbox;
  if (!bbox) {
    throw new Error("Live parcel queries require a bbox");
  }
  const countyFips = fipsIntersectingBbox(
    bbox,
    fipsForOrlandoCountyFilter(query.county ?? null, query.state ?? "Florida"),
  );
  const limit = query.limit ?? 800;
  const perCounty = Math.max(80, Math.floor(limit / Math.max(1, countyFips.length)));
  const batches = await Promise.all(countyFips.map((fips) => queryDohLayer(fips, bbox, perCounty)));
  const byId = new Map<string, ParcelFeature>();
  for (const batch of batches) {
    for (const feature of batch) {
      byId.set(feature.properties.id, feature);
    }
  }
  return {
    type: "FeatureCollection",
    features: Array.from(byId.values()).slice(0, limit),
  };
}
