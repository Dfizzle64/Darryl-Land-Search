import { readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { loadParcelCoverage } from "../lib/data/parcelCoverageStore";
import {
  PARCEL_COVERAGE_DEFAULT_ON,
  PARCEL_COVERAGE_MIN_ZOOM,
  coverageCountyLabel,
  loadedParcelCounties,
  parcelCoverageFeatures,
} from "../lib/parcelCoverage";

describe("parcel coverage overlay", () => {
  it("starts off, uses the tract zoom floor, and names the county", () => {
    expect(PARCEL_COVERAGE_DEFAULT_ON).toBe(false);
    expect(PARCEL_COVERAGE_MIN_ZOOM).toBe(4);
    expect(coverageCountyLabel("Davidson", "Tennessee")).toBe("Davidson County, Tennessee");
  });

  it("builds the county list from the parcel manifests, including Orlando-only counties and skipping gaps", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    const davidson = loaded.find((county) => county.fips === "47037");
    expect(davidson).toEqual({ fips: "47037", name: "Davidson", state: "Tennessee" });
    expect(loaded.find((county) => county.fips === "47111")).toBeUndefined();
    expect(loaded.find((county) => county.fips === "12069")).toEqual({ fips: "12069", name: "Lake", state: "Florida" });
    expect(loaded.find((county) => county.fips === "12095")).toMatchObject({ name: "Orange", state: "Florida" });
    const fips = new Set(loaded.map((county) => county.fips));
    expect(fips.size).toBe(loaded.length);
  });

  it("joins those counties to Census cartographic shapes and drops a county that is not loaded", async () => {
    const collection = await loadParcelCoverage();
    const davidson = collection.features.find((feature) => feature.properties?.fips === "47037");
    expect(davidson?.properties).toMatchObject({ name: "Davidson", state: "Tennessee" });
    expect(davidson?.geometry.type === "Polygon" || davidson?.geometry.type === "MultiPolygon").toBe(true);
    expect(collection.features.find((feature) => feature.properties?.fips === "47111")).toBeUndefined();
    const raw = await readFile(path.join(process.cwd(), "data/fixtures/census/cb_2024_us_county_5m.geojson"), "utf8");
    expect(raw).toContain("cb_2024_us_county_5m");
    const boundaries = JSON.parse(raw) as GeoJSON.FeatureCollection;
    const joined = parcelCoverageFeatures(
      [{ fips: "47037", name: "Davidson", state: "Tennessee" }],
      boundaries,
    );
    expect(joined.features).toHaveLength(1);
    expect(joined.features[0]?.geometry).toEqual(davidson?.geometry);
  });
});
