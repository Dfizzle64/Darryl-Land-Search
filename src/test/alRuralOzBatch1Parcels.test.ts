import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

/**
 * First 20 priority-list counties with a public parcel layer that were not
 * already a complete 5–150 acre extract and whose card endpoint answered.
 */
const COUNTIES: Record<
  string,
  { name: string; min: number; max?: number; market: string; sourceIncludes: string; urlIncludes: string }
> = {
  "01015": { name: "Calhoun", min: 9000, market: "Birmingham", sourceIncludes: "al-calhoun-parcels-01015", urlIncludes: "Parcel_Viewer_IPV/MapServer/106" },
  "01047": { name: "Dallas", min: 6000, market: "Montgomery", sourceIncludes: "al-dallas-parcels-01047", urlIncludes: "Dallas_ParcelViewer_Service/FeatureServer/2" },
  "01049": { name: "DeKalb", min: 15000, market: "Huntsville", sourceIncludes: "al-dekalb-parcels-01049", urlIncludes: "Dekalb_Public_ISV/MapServer/48" },
  "01055": { name: "Etowah", min: 10000, market: "Birmingham", sourceIncludes: "al-etowah-parcels-01055", urlIncludes: "Etowah_Public_ISV/MapServer/91" },
  "01121": { name: "Talladega", min: 9000, market: "Birmingham", sourceIncludes: "al-talladega-parcels-01121", urlIncludes: "Talladega911/Public/MapServer/7" },
  "01087": { name: "Macon", min: 5000, market: "Montgomery", sourceIncludes: "al-macon-parcels-01087", urlIncludes: "MaconAL/MaconCapture/MapServer/1" },
  "01071": { name: "Jackson", min: 12000, market: "Huntsville", sourceIncludes: "al-jackson-parcels-01071", urlIncludes: "Public_ISV_Jackson/MapServer/1" },
  "01005": { name: "Barbour", min: 6500, market: "Montgomery", sourceIncludes: "al-barbour-parcels-01005", urlIncludes: "BarbourAL/BarbourCapture/MapServer/213" },
  "01059": { name: "Franklin", min: 7000, market: "Huntsville", sourceIncludes: "al-franklin-parcels-01059", urlIncludes: "Franklin_Public_ISV/MapServer/105" },
  "01077": { name: "Lauderdale", min: 3000, max: 6000, market: "Huntsville", sourceIncludes: "al-lauderdale-parcels-01077", urlIncludes: "Lauderdale_Public_ISV/MapServer/120" },
  "01099": { name: "Monroe", min: 8000, market: "Mobile", sourceIncludes: "al-monroe-parcels-01099", urlIncludes: "Monroe12092025/MapServer/84" },
  "01009": { name: "Blount", min: 10000, market: "Birmingham", sourceIncludes: "al-blount-parcels-01009", urlIncludes: "Blount/Public/MapServer/32" },
  "01043": { name: "Cullman", min: 13000, market: "Birmingham", sourceIncludes: "al-cullman-parcels-01043", urlIncludes: "Cullman_Public_ISV/MapServer/107" },
  "01011": { name: "Bullock", min: 3000, market: "Montgomery", sourceIncludes: "al-bullock-parcels-01011", urlIncludes: "BullockCapture/MapServer/3" },
  "01063": { name: "Greene", min: 4000, market: "Tuscaloosa", sourceIncludes: "al-greene-parcels-01063", urlIncludes: "GreeneAL_Service/FeatureServer/5" },
  "01119": { name: "Sumter", min: 4500, market: "Tuscaloosa", sourceIncludes: "al-sumter-parcels-01119", urlIncludes: "Sumter03282024/MapServer/2" },
  "01131": { name: "Wilcox", min: 5000, max: 16604, market: "Montgomery", sourceIncludes: "al-wilcox-parcels-01131", urlIncludes: "Wilcox_03122025/MapServer/10" },
  "01065": { name: "Hale", min: 5500, market: "Tuscaloosa", sourceIncludes: "al-hale-parcels-01065", urlIncludes: "Hale_Web_Service/FeatureServer/10" },
  "01133": { name: "Winston", min: 7000, market: "Huntsville", sourceIncludes: "al-winston-parcels-01133", urlIncludes: "Winston_Public_ISV/MapServer/141" },
  "01019": { name: "Cherokee", min: 7000, market: "Huntsville", sourceIncludes: "al-cherokee-parcels-01019", urlIncludes: "Cherokee/Public/MapServer/116" },
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

describe("Alabama rural OZ batch 1 parcels", () => {
  it("lists every batch county on the Coverage manifest", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    const byFips = new Map(loaded.map((county) => [county.fips, county]));
    for (const [fips, target] of Object.entries(COUNTIES)) {
      expect(byFips.get(fips)).toEqual({ fips, name: target.name, state: "Alabama" });
      const row = countyFile(fips);
      expect(row.featureCount).toBeGreaterThanOrEqual(target.min);
      if (target.max != null) expect(row.featureCount).toBeLessThan(target.max);
      expect(row.coverage).toBe("complete-gte-5ac");
      expect(row.minAcres).toBe(5);
      expect(row.maxAcres).toBe(150);
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

  it("leaves Colbert unloaded and keeps Mobile and Shelby extracts", () => {
    expect(existsSync("data/fixtures/market-parcels/counties/01033/county.json")).toBe(false);
    expect(countyFile("01097").featureCount).toBe(17270);
    expect(countyFile("01117")).toMatchObject({
      source: "al-shelby-cadastral-2025",
      coverage: "complete-gte-5ac",
      featureCount: 11994,
    });
  });

  it("keeps household income on ACS B19013_001E", () => {
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    expect(source).toMatch(/for=tract:\*|tract:\*/);
  });

  it("stores integral Cullman pins and returns in-band Blount parcels on Birmingham", async () => {
    let dotted = 0;
    eachFeature("01043", (feature) => {
      if (feature.properties.parcelId.endsWith(".0")) dotted += 1;
      const url = feature.properties.appraiserUrl || "";
      if (url.includes(".0")) dotted += 1;
    });
    expect(dotted).toBe(0);

    let sample: ParcelFeature | undefined;
    eachFeature("01009", (feature) => {
      sample ??= feature;
    });
    expect(sample).toBeTruthy();
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.marketIds).toContain("Birmingham");
    expect(sample!.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(sample!.properties.acreage).toBeLessThanOrEqual(150);
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const blount = page.collection.features.filter((item) => item.properties.countyFips === "01009");
    expect(blount.length).toBeGreaterThan(0);
    expect(blount.every((item) => item.properties.source === "al-blount-parcels-01009")).toBe(true);
    expect(blount.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );
  });

  it("keeps every batch parcel inside 5–150 acres with no future sale or contact fields", () => {
    const today = new Date().toISOString().slice(0, 10);
    const problems: string[] = [];
    for (const fips of Object.keys(COUNTIES)) {
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
      });
      if (problems.length > 8) break;
    }
    expect(problems).toEqual([]);
  }, 120_000);
});
