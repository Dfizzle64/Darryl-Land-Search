import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { PARCEL_MIN_ZOOM } from "../lib/parcelVisibility";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const SERVERS_DOWN =
  '{"status":"error","messages":["Could not access any server machines. Please contact your system administrator."]}';

type Report = {
  pulled: { fips: string; name: string; featureCount: number; source: string; queryUrl: string; markets: string[] }[];
  skipped: { fips: string; name: string; reason: string; queryUrl: string }[];
  totalParcels: number;
};

type CountyManifest = {
  name: string;
  fips: string;
  state: string;
  markets: string[];
  featureCount: number;
  coverage: string;
  minAcres: number;
  maxAcres: number;
  source: string;
  queryUrl: string | null;
  gaps: string[];
  path: string | null;
};

const report = JSON.parse(readFileSync("data/fixtures/market-parcels/rural-oz-retry-result.json", "utf8")) as Report;

function countyFile(fips: string): CountyManifest {
  return JSON.parse(
    readFileSync(path.join("data/fixtures/market-parcels/counties", fips, "county.json"), "utf8"),
  ) as CountyManifest;
}

function eachFeature(fips: string, visit: (feature: ParcelFeature) => void) {
  const row = countyFile(fips);
  expect(row.path).toBeTruthy();
  const tiles = readdirSync(row.path!).filter((name) => name.endsWith(".geojson"));
  expect(tiles.length).toBeGreaterThan(0);
  for (const tile of tiles) {
    const collection = JSON.parse(readFileSync(path.join(row.path!, tile), "utf8")) as ParcelCollection;
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

describe("rural Opportunity Zone parcel retry", () => {
  it("loads Sumter and records the Schneider counties that stayed down", async () => {
    expect(report.totalParcels).toBe(6759);
    expect(report.pulled.map((item) => item.fips)).toEqual(["45085"]);
    expect(report.skipped.map((item) => item.fips).sort()).toEqual(["13035", "13119", "13131", "13137"]);
    for (const item of report.skipped) {
      expect(item.reason).toContain(SERVERS_DOWN);
      expect(item.queryUrl).toContain("wfs.schneidercorp.com");
      expect(`${item.queryUrl} ${item.reason}`.toLowerCase()).not.toMatch(/regrid|reportall/);
    }
    expect(report.skipped.find((item) => item.fips === "13137")?.reason).toContain(
      "Service habersham/habersham_rokmaps/MapServer not found",
    );
    expect(report.skipped.find((item) => item.fips === "13035")?.reason).toContain(
      "TimeoutError: The read operation timed out",
    );

    const row = countyFile("45085");
    expect(row).toMatchObject({
      name: "Sumter",
      state: "South Carolina",
      featureCount: 6759,
      coverage: "complete-gte-5ac",
      minAcres: 5,
      maxAcres: 150,
      source: "sc-sumter-parcels-45085",
      markets: ["Columbia"],
    });
    expect(row.queryUrl).toContain("Sumter_City_County/FeatureServer/7");
    expect(row.gaps.join(" ")).toMatch(/No Opportunity Zone status/);
    expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade:\s*[A-F]|base flood elevation:\s*\d/i);

    expect(countyFile("13035")).toMatchObject({ featureCount: 0, coverage: "gap" });
    for (const fips of ["13119", "13131", "13137"]) {
      expect(existsSync(path.join("data/fixtures/market-parcels/counties", fips, "county.json"))).toBe(false);
    }

    const index = await loadMarketParcelIndex();
    const columbia = index.markets.Columbia;
    const listed = columbia.counties.find((county) => county.fips === "45085");
    expect(listed?.featureCount).toBe(6759);
    expect(columbia.parcelCount).toBe(columbia.counties.reduce((sum, county) => sum + county.featureCount, 0));
  });

  it("keeps parcel zoom at 10 and returns in-band Sumter parcels on Columbia", async () => {
    expect(PARCEL_MIN_ZOOM).toBe(10);
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    let sample: ParcelFeature | undefined;
    eachFeature("45085", (feature) => {
      sample ??= feature;
    });
    expect(sample).toBeTruthy();
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.oz2Eligibility).toBeNull();
    expect(sample!.properties.marketIds).toEqual(["Columbia"]);
    expect(sample!.properties.state).toBe("South Carolina");
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const mine = page.collection.features.filter((item) => item.properties.countyFips === "45085");
    expect(mine.length).toBeGreaterThan(0);
    expect(mine.every((item) => item.properties.source === "sc-sumter-parcels-45085")).toBe(true);
    expect(mine.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(true);
  });

  it("counts distinct Sumter parcel ids inside 5–150 acres without phone, email, or future sales", () => {
    const today = new Date().toISOString().slice(0, 10);
    const ids = new Set<string>();
    const problems: string[] = [];
    eachFeature("45085", (feature) => {
      const acres = feature.properties.acreage;
      if (acres == null || acres < 5 || acres > 150) problems.push(`acres ${feature.properties.parcelId} ${acres}`);
      if (ids.has(feature.properties.parcelId)) problems.push(`duplicate ${feature.properties.parcelId}`);
      ids.add(feature.properties.parcelId);
      const sold = feature.properties.lastSale?.date;
      if (sold && sold > today) problems.push(`sale ${feature.properties.parcelId} ${sold}`);
      const keys: string[] = [];
      propertyKeys(feature.properties, keys);
      if (keys.some((key) => /phone|e-?mail|ssn/i.test(key))) problems.push(`keys ${feature.properties.parcelId}`);
      if (feature.properties.opportunityZone != null || feature.properties.oz2Eligibility != null) {
        problems.push(`oz ${feature.properties.parcelId}`);
      }
      if (feature.properties.nearestRoad != null) problems.push(`aadt ${feature.properties.parcelId}`);
    });
    expect(ids.size).toBe(6759);
    expect(problems).toEqual([]);
  });
});
