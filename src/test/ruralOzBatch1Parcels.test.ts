import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection } from "../lib/types";

/** Card targets for counties this batch adds or replaces. Live shelves stay put. */
const TARGETS: Record<string, { name: string; min: number }> = {
  "12007": { name: "Bradford", min: 3000 },
  "12017": { name: "Citrus", min: 5800 },
  "12029": { name: "Dixie", min: 3000 },
  "12047": { name: "Hamilton", min: 3900 },
  "12059": { name: "Holmes", min: 6200 },
  "12067": { name: "Lafayette", min: 2900 },
  "12075": { name: "Levy", min: 9000 },
  "12079": { name: "Madison", min: 6800 },
  "12083": { name: "Marion", min: 16000 },
  "12099": { name: "Palm Beach", min: 11500 },
  "12109": { name: "St. Johns", min: 4900 },
  "12119": { name: "Sumter", min: 9000 },
  "12121": { name: "Suwannee", min: 11000 },
  "12123": { name: "Taylor", min: 3500 },
  "12125": { name: "Union", min: 2100 },
};

const UNCHANGED: Record<string, number> = {
  "12027": 4677,
  "12053": 6601,
  "12101": 12372,
  "12105": 20263,
};

function countyFile(fips: string) {
  return JSON.parse(readFileSync(path.join("data/fixtures/market-parcels/counties", fips, "county.json"), "utf8")) as {
    name: string;
    fips: string;
    featureCount: number;
    coverage: string;
    minAcres: number;
    maxAcres: number;
    source: string;
    queryUrl: string;
    gaps: string[];
    path: string;
  };
}

describe("rural OZ batch 1 parcel shelves", () => {
  it("lists every pass-1 county on the Coverage manifest and keeps the live shelves", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    const byFips = new Map(loaded.map((county) => [county.fips, county]));
    for (const [fips, target] of Object.entries(TARGETS)) {
      expect(byFips.get(fips)?.name).toBe(target.name);
      const row = countyFile(fips);
      expect(row.featureCount).toBeGreaterThanOrEqual(target.min);
      expect(row.coverage).not.toBe("gap");
      expect(row.minAcres).toBe(5);
      expect(row.maxAcres).toBe(150);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade|base flood/i);
    }
    for (const [fips, count] of Object.entries(UNCHANGED)) {
      expect(countyFile(fips).featureCount).toBe(count);
    }
    const lake = orlando.counties.find((county) => county.fips === "12069");
    expect(lake?.featureCount).toBe(16753);
    expect(lake?.source).toBe("lakecounty-tax-parcels");
  });

  it("uses the card sources and does not ingest the Union maintenance layer", () => {
    const palm = countyFile("12099");
    expect(palm.queryUrl).toContain("/MapServer/4");
    expect(palm.queryUrl).not.toContain("FeatureServer");
    expect(palm.gaps.join(" ")).toMatch(/CONDO/);
    expect(palm.gaps.join(" ")).toMatch(/TLS/);
    const union = countyFile("12125");
    expect(union.source).toContain("srwmd");
    expect(union.queryUrl).toContain("SRWMD_Parcels/FeatureServer/13");
    expect(union.gaps.join(" ")).toMatch(/MaintenanceRequests|not ingested/i);
    expect(union.queryUrl).not.toMatch(/UnionMaintenanceRequests/);
    const bradford = countyFile("12007");
    expect(bradford.source).toContain("srwmd");
    expect(bradford.queryUrl.startsWith("http://")).toBe(true);
  });

  it("returns 5–150 acre parcels for a Bradford viewport", async () => {
    const row = countyFile("12007");
    const tiles = readdirSync(row.path).filter((name) => name.endsWith(".geojson"));
    expect(tiles.length).toBeGreaterThan(0);
    const collection = JSON.parse(readFileSync(path.join(row.path, tiles[0]), "utf8")) as ParcelCollection;
    const feature = collection.features[0];
    expect(feature.properties.opportunityZone).toBeNull();
    expect(feature.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(feature.properties.acreage).toBeLessThanOrEqual(150);
    const [lon, lat] = feature.properties.centroid;
    const page = await queryParcelsInView([lon - 0.02, lat - 0.02, lon + 0.02, lat + 0.02]);
    expect(page.covered).toBe(true);
    expect(page.collection.features.length).toBeGreaterThan(0);
    expect(page.collection.features.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );
    expect(page.collection.features.some((item) => item.properties.countyFips === "12007")).toBe(true);
  });
});
