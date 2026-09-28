import { readFile } from "node:fs/promises";
import path from "node:path";
import { loadedParcelCounties, parcelCoverageFeatures } from "../parcelCoverage";
import { loadMarketParcelIndex } from "./marketParcelStore";
import { loadOrlandoParcelsMeta } from "./orlandoParcelStore";

/** Census Bureau cartographic boundary file, 1:5,000,000. Geometries only. */
const BOUNDARY_PATH = path.join(process.cwd(), "data/fixtures/census/cb_2024_us_county_5m.geojson");

let cachedBoundaries: Promise<GeoJSON.FeatureCollection> | null = null;
let cachedCoverage: Promise<GeoJSON.FeatureCollection> | null = null;

function loadCountyBoundaries(): Promise<GeoJSON.FeatureCollection> {
  if (!cachedBoundaries) {
    cachedBoundaries = readFile(BOUNDARY_PATH, "utf8").then(
      (raw) => JSON.parse(raw) as GeoJSON.FeatureCollection,
    );
  }
  return cachedBoundaries;
}

/** Covered counties for the current manifests, with simplified Census shapes. Cached after the first call. */
export function loadParcelCoverage(): Promise<GeoJSON.FeatureCollection> {
  if (!cachedCoverage) {
    cachedCoverage = Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta(), loadCountyBoundaries()]).then(
      ([index, orlando, boundaries]) =>
        parcelCoverageFeatures(loadedParcelCounties(index.markets, orlando.counties), boundaries),
    );
  }
  return cachedCoverage;
}
