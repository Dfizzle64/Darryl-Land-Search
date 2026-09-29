import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

/**
 * Remaining Alabama counties with a public parcel layer that were not already
 * a complete 5–150 acre extract and whose card endpoint answered. Henry,
 * Lawrence, and Coosa are first. Colbert was still stopped and is not loaded.
 */
const COUNTIES: Record<
  string,
  { name: string; min: number; market: string; sourceIncludes: string; urlIncludes: string }
> = {
  "01067": { name: "Henry", min: 6000, market: "Montgomery", sourceIncludes: "al-henry-parcels-01067", urlIncludes: "Henry/Henry05042023/MapServer/0" },
  "01079": { name: "Lawrence", min: 8000, market: "Huntsville", sourceIncludes: "al-lawrence-parcels-01079", urlIncludes: "Lawrence/Lawrence_Public_ISV/MapServer/49" },
  "01037": { name: "Coosa", min: 5500, market: "Montgomery", sourceIncludes: "al-coosa-parcels-01037", urlIncludes: "Coosa/Coosa03122026/MapServer/171" },
  "01029": { name: "Cleburne", min: 5500, market: "Birmingham", sourceIncludes: "al-cleburne-parcels-01029", urlIncludes: "Cleburne/CleburneParcels_06122024/MapServer/401" },
  "01069": { name: "Houston", min: 2500, market: "Montgomery", sourceIncludes: "al-houston-parcels-01069", urlIncludes: "Houston/Houston_Public_ISV/MapServer/29" },
  "01081": { name: "Lee", min: 8000, market: "Montgomery", sourceIncludes: "al-lee-parcels-01081", urlIncludes: "LeeCountyTaxParcels/FeatureServer/9" },
  "01113": { name: "Russell", min: 5000, market: "Montgomery", sourceIncludes: "al-russell-parcels-01113", urlIncludes: "Russell/Russell_02122026/MapServer/133" },
};

type CountyManifest = {
  name: string;
  fips: string;
  state: string;
  featureCount: number;
  coverage: string;
  minAcres: number;
  maxAcres: number;
  source: string;
  queryUrl: string;
  gaps: string[];
  path: string;
  markets?: string[];
  paLinkVerified?: boolean;
  appraiserSearchUrl?: string | null;
  gisViewerUrl?: string | null;
};

function countyFile(fips: string): CountyManifest {
  return JSON.parse(
    readFileSync(path.join("data/fixtures/market-parcels/counties", fips, "county.json"), "utf8"),
  ) as CountyManifest;
}

function eachFeature(fips: string, visit: (feature: ParcelFeature) => void) {
  const row = countyFile(fips);
  const tiles = readdirSync(row.path).filter((name) => name.endsWith(".geojson"));
  expect(tiles.length).toBeGreaterThan(0);
  for (const tile of tiles) {
    const collection = JSON.parse(readFileSync(path.join(row.path, tile), "utf8")) as ParcelCollection;
    for (const feature of collection.features) visit(feature);
  }
}

function propertyKeys(value: unknown, into: string[]) {
  if (!value || typeof value !== "object") return;
  if (Array.isArray(value)) {
    for (const item of value) propertyKeys(item, into);
    return;
  }
  for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
    into.push(key);
    propertyKeys(child, into);
  }
}

describe("Alabama rural OZ batch 2 parcels", () => {
  it("lists every batch county on the Coverage manifest", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    const byFips = new Map(loaded.map((county) => [county.fips, county]));
    for (const [fips, target] of Object.entries(COUNTIES)) {
      expect(byFips.get(fips)).toEqual({ fips, name: target.name, state: "Alabama" });
      const row = countyFile(fips);
      expect(row.featureCount).toBeGreaterThanOrEqual(target.min);
      expect(row.coverage).toBe("complete-gte-5ac");
      expect(row.minAcres).toBe(5);
      expect(row.maxAcres).toBe(150);
      expect(row.markets).toEqual([target.market]);
      expect(row.source).toContain(target.sourceIncludes);
      expect(row.queryUrl).toContain(target.urlIncludes);
      expect(row.gaps.join(" ")).toMatch(/No Opportunity Zone status/);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade:\s*[A-F]|base flood elevation:\s*\d/i);
      expect(`${row.source} ${row.queryUrl}`.toLowerCase()).not.toMatch(/regrid|reportall/);
      expect(row.paLinkVerified).toBe(false);
      expect(row.appraiserSearchUrl || "").toMatch(/^https?:\/\//);
      expect(row.gisViewerUrl || "").toMatch(/^https?:\/\//);
    }
  });

  it("leaves Colbert unloaded and keeps the Tuscaloosa extract", () => {
    expect(existsSync("data/fixtures/market-parcels/counties/01033/county.json")).toBe(false);
    expect(countyFile("01125")).toMatchObject({
      coverage: "complete-gte-5ac",
      featureCount: 11596,
    });
  });

  it("keeps household income on ACS B19013_001E", () => {
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    expect(source).toMatch(/for=tract:\*|tract:\*/);
  });

  it("returns in-band Lawrence parcels on Huntsville and does not copy a sample account", async () => {
    let sample: ParcelFeature | undefined;
    const urls = new Set<string>();
    eachFeature("01079", (feature) => {
      sample ??= feature;
      const url = feature.properties.appraiserUrl || "";
      if (url) urls.add(url);
      expect(feature.properties.parcelId.endsWith(".0")).toBe(false);
    });
    expect(sample).toBeTruthy();
    expect(urls.size).toBeGreaterThan(1000);
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.marketIds).toContain("Huntsville");
    expect(sample!.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(sample!.properties.acreage).toBeLessThanOrEqual(150);
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const lawrence = page.collection.features.filter((item) => item.properties.countyFips === "01079");
    expect(lawrence.length).toBeGreaterThan(0);
    expect(lawrence.every((item) => item.properties.source === "al-lawrence-parcels-01079")).toBe(true);
    expect(lawrence.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );

    const leeUrls = new Set<string>();
    eachFeature("01081", (feature) => {
      const url = feature.properties.appraiserUrl || "";
      if (url) leeUrls.add(url);
    });
    expect(leeUrls.size).toBe(countyFile("01081").featureCount);
  });

  it("keeps every batch parcel inside 5–150 acres with no future sale or contact fields", () => {
    const today = new Date().toISOString().slice(0, 10);
    const problems: string[] = [];
    for (const fips of Object.keys(COUNTIES)) {
      const urls = new Map<string, number>();
      eachFeature(fips, (item) => {
        const acres = item.properties.acreage;
        if (acres == null || acres < 5 || acres > 150) {
          problems.push(`${fips} ${item.properties.parcelId} acres ${acres}`);
        }
        const sold = item.properties.lastSale?.date;
        if (sold && sold > today) problems.push(`${fips} ${item.properties.parcelId} sale ${sold}`);
        const keys: string[] = [];
        propertyKeys(item.properties, keys);
        if (keys.some((key) => /phone|e-?mail|ssn/i.test(key))) {
          problems.push(`${fips} ${item.properties.parcelId} keys ${keys.join(" ")}`);
        }
        if (item.properties.opportunityZone != null || item.properties.oz2Eligibility != null) {
          problems.push(`${fips} ${item.properties.parcelId} oz`);
        }
        const url = item.properties.appraiserUrl;
        if (url) urls.set(url, (urls.get(url) || 0) + 1);
      });
      for (const [url, count] of urls) {
        if (count > 1) problems.push(`${fips} repeated appraiser ${count} ${url}`);
      }
      if (problems.length > 8) break;
    }
    expect(problems).toEqual([]);
  }, 120_000);
});
