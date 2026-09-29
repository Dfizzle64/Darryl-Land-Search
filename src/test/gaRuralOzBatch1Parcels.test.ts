import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import { PARCEL_MIN_ZOOM } from "../lib/parcelVisibility";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

/**
 * First 20 pass-2 rows with pass 1 usable that were not already a complete
 * 5–150 acre extract and whose public county GIS endpoint answered.
 * Carroll and Walton were already complete. Franklin and Habersham timed out.
 * Gilmer and Mitchell are partial clips, not county-wide.
 */
const GA_SHELVES = new Set(["Atlanta", "Savannah", "Chattanooga", "Valdosta", "Macon", "Athens"]);

const ALREADY_COMPLETE: Record<string, { source: string; featureCount: number }> = {
  "13089": { source: "ga-dekalb-assessment-view-2", featureCount: 3401 },
  "13045": { source: "oa-carroll-ga-910028", featureCount: 9217 },
  "13297": { source: "ga-walton-choosewalton-parcels", featureCount: 5824 },
  "13255": { source: "ga-spalding-parcels-public", featureCount: 3832 },
};

type Pulled = {
  order: number;
  fips: string;
  name: string;
  featureCount: number;
  markets: string[];
  shelf: string;
  source: string;
  queryUrl: string;
  appraiserSearchUrl?: string | null;
  gisViewerUrl?: string | null;
  paLinkVerified?: boolean;
};

type Report = {
  pulled: Pulled[];
  nextOrder: number;
  remainingUsable: number;
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
  queryUrl: string;
  gaps: string[];
  path: string;
  paLinkVerified?: boolean;
  appraiserSearchUrl?: string | null;
  gisViewerUrl?: string | null;
};

const report = JSON.parse(readFileSync("data/ga-parcel-cards/batch1-result.json", "utf8")) as Report;

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

describe("Georgia rural OZ batch 1 parcels", () => {
  it("loads the first 20 reachable counties and leaves complete extracts alone", async () => {
    expect(report.pulled).toHaveLength(20);
    expect(report.totalParcels).toBe(report.pulled.reduce((sum, item) => sum + item.featureCount, 0));
    expect(report.nextOrder).toBeGreaterThan(report.pulled[report.pulled.length - 1]?.order ?? 0);
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    const byFips = new Map(loaded.map((county) => [county.fips, county]));
    const orders = report.pulled.map((item) => item.order);
    expect(orders).toEqual([...orders].sort((a, b) => a - b));
    for (const item of report.pulled) {
      expect(byFips.get(item.fips)).toEqual({ fips: item.fips, name: item.name, state: "Georgia" });
      const row = countyFile(item.fips);
      expect(row.featureCount).toBe(item.featureCount);
      expect(row.featureCount).toBeGreaterThan(50);
      expect(row.coverage).toBe("complete-gte-5ac");
      expect(row.minAcres).toBe(5);
      expect(row.maxAcres).toBe(150);
      expect(row.state).toBe("Georgia");
      expect(row.markets.every((market) => GA_SHELVES.has(market))).toBe(true);
      expect(row.markets).toContain(item.shelf);
      expect(row.source).toBe(item.source);
      expect(row.queryUrl).toBe(item.queryUrl);
      expect(`${row.source} ${row.queryUrl}`.toLowerCase()).not.toMatch(/regrid|reportall/);
      expect(row.gaps.join(" ")).toMatch(/No Opportunity Zone status/);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade:\s*[A-F]|base flood elevation:\s*\d/i);
      expect(row.appraiserSearchUrl || "").toMatch(/^https?:\/\//);
      expect(row.appraiserSearchUrl || "").toContain("{parcelId}");
      expect(row.gisViewerUrl || "").toMatch(/^https?:\/\//);
      expect(row.paLinkVerified).toBe(item.paLinkVerified);
    }
    for (const [fips, prior] of Object.entries(ALREADY_COMPLETE)) {
      expect(countyFile(fips)).toMatchObject({
        source: prior.source,
        coverage: "complete-gte-5ac",
        featureCount: prior.featureCount,
      });
    }
    expect(countyFile("13083").markets).toContain("Chattanooga");
    expect(countyFile("13129").markets).toEqual(["Atlanta"]);
    expect(countyFile("13251").markets).toContain("Savannah");
    expect(countyFile("13295").markets).toContain("Chattanooga");
  });

  it("keeps household income on ACS B19013_001E and parcel zoom at 10", () => {
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    expect(source).toMatch(/for=tract:\*|tract:\*/);
    expect(PARCEL_MIN_ZOOM).toBe(10);
  });

  it("returns in-band parcels for whatever shelf is on screen", async () => {
    const sampleCounty = report.pulled[0];
    let sample: ParcelFeature | undefined;
    eachFeature(sampleCounty.fips, (feature) => {
      sample ??= feature;
    });
    expect(sample).toBeTruthy();
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.nearestRoad).toBeNull();
    expect(sample!.properties.incomeTract).toBeNull();
    expect(sample!.properties.marketIds).toEqual(sampleCounty.markets);
    expect(sample!.properties.state).toBe("Georgia");
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05]);
    expect(page.covered).toBe(true);
    const mine = page.collection.features.filter((item) => item.properties.countyFips === sampleCounty.fips);
    expect(mine.length).toBeGreaterThan(0);
    expect(mine.every((item) => item.properties.source === sampleCounty.source)).toBe(true);
    expect(mine.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );
  });

  it("keeps distinct parcel ids inside 5–150 acres with per-parcel appraiser links", () => {
    const today = new Date().toISOString().slice(0, 10);
    const problems: string[] = [];
    for (const item of report.pulled) {
      const ids = new Set<string>();
      const urls = new Set<string>();
      let urlCount = 0;
      const row = countyFile(item.fips);
      const sample = row.appraiserSearchUrl?.match(/KeyValue=([^&]+)/)?.[1];
      eachFeature(item.fips, (feature) => {
        const acres = feature.properties.acreage;
        if (acres == null || acres < 5 || acres > 150) {
          problems.push(`${item.fips} ${feature.properties.parcelId} acres ${acres}`);
        }
        if (ids.has(feature.properties.parcelId)) problems.push(`${item.fips} duplicate ${feature.properties.parcelId}`);
        ids.add(feature.properties.parcelId);
        const sold = feature.properties.lastSale?.date;
        if (sold && sold > today) problems.push(`${item.fips} ${feature.properties.parcelId} sale ${sold}`);
        const keys: string[] = [];
        propertyKeys(feature.properties, keys);
        if (keys.some((key) => /phone|e-?mail|ssn/i.test(key))) {
          problems.push(`${item.fips} ${feature.properties.parcelId} keys ${keys.join(" ")}`);
        }
        const owner = `${feature.properties.ownerName || ""} ${feature.properties.ownerName2 || ""}`;
        const mail = feature.properties.mailingAddress;
        const contact = `${owner} ${mail?.line1 || ""} ${mail?.line2 || ""}`;
        if (/[^@\s]+@[^@\s]+\.[A-Za-z]{2,}/.test(contact) || /\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b/.test(contact)) {
          problems.push(`${item.fips} ${feature.properties.parcelId} contact ${contact}`);
        }
        if (feature.properties.opportunityZone != null || feature.properties.oz2Eligibility != null) {
          problems.push(`${item.fips} ${feature.properties.parcelId} oz`);
        }
        if (feature.properties.nearestRoad != null) problems.push(`${item.fips} ${feature.properties.parcelId} aadt`);
        const url = feature.properties.appraiserUrl || "";
        if (url) {
          urlCount += 1;
          urls.add(url);
          if (sample && url.includes(sample) && !feature.properties.parcelId.includes(decodeURIComponent(sample))) {
            problems.push(`${item.fips} sample id on ${feature.properties.parcelId}`);
          }
        }
        if (row.gisViewerUrl) expect(feature.properties.gisViewerUrl).toBe(row.gisViewerUrl);
      });
      expect(ids.size).toBe(item.featureCount);
      if (urlCount > 10) expect(urls.size).toBeGreaterThan(1);
      if (problems.length > 8) break;
    }
    expect(problems).toEqual([]);
  }, 180_000);
});
