import {
  buildTigerQuery,
  parseTigerCollection,
  stampKnownIncome,
  type TractBbox,
  type ViewportTractFeature,
} from "./censusTracts";

const cache = new Map<string, ViewportTractFeature[]>();
const CACHE_LIMIT = 180;

function cacheKey(bbox: TractBbox, zoom: number): string {
  const rounded = bbox.map((value) => value.toFixed(3)).join(",");
  return `${rounded}|${zoom < 10 ? "far" : zoom < 12 ? "mid" : "near"}`;
}

export async function fetchCensusTractTile(
  bbox: TractBbox,
  zoom: number,
  income: ReadonlyMap<string, number> = new Map(),
  fetchImpl: typeof fetch = fetch,
): Promise<ViewportTractFeature[]> {
  const key = cacheKey(bbox, zoom);
  const cached = cache.get(key);
  if (cached) return cached.map((feature) => structuredClone(feature));

  const response = await fetchImpl(buildTigerQuery(bbox, zoom), {
    headers: { Accept: "application/json", "User-Agent": "Darryl-Land-Search census-tracts" },
    cache: "force-cache",
  });
  if (!response.ok) {
    throw new Error(`Census tract request failed (${response.status})`);
  }
  const body = (await response.json()) as unknown;
  const features = stampKnownIncome(parseTigerCollection(body), income);
  cache.set(key, features);
  if (cache.size > CACHE_LIMIT) {
    const oldest = cache.keys().next().value;
    if (oldest) cache.delete(oldest);
  }
  return features.map((feature) => structuredClone(feature));
}
