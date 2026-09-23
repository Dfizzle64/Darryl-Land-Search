import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import {
  featuresInAcreageBand,
  inMarketAcreageBand,
  MARKET_PARCEL_ACREAGE,
  MARKET_PARCEL_TILE,
  showMarketParcels,
  type MarketParcelIndex,
} from "../lib/marketParcels";
import { ORLANDO_PARCEL_TILE, showOrlandoParcels } from "../lib/orlandoParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const index: MarketParcelIndex = {
  generatedAt: "2026-09-23T00:00:00Z",
  coreMinAcres: 5,
  coreMaxAcres: 150,
  tile: { originLon: -83, originLat: 27, tileDeg: 0.25 },
  markets: {
    Tampa: {
      tier: "primary",
      parcelCount: 10,
      completeCountyCount: 1,
      sampleCountyCount: 0,
      gapCountyCount: 1,
      path: "data/fixtures/market-parcels/markets/tampa/meta.json",
      counties: [
        { name: "Hillsborough", state: "Florida", fips: "12057", featureCount: 10, coverage: "complete-gte-5ac" },
        { name: "Pinellas", state: "Florida", fips: "12103", featureCount: 0, coverage: "gap" },
      ],
    },
    Savannah: {
      tier: "other",
      parcelCount: 0,
      completeCountyCount: 0,
      sampleCountyCount: 0,
      gapCountyCount: 1,
      path: "data/fixtures/market-parcels/markets/savannah/meta.json",
      counties: [{ name: "Chatham", state: "Georgia", fips: "13051", featureCount: 0, coverage: "gap" }],
    },
  },
};

describe("market parcel gating and acreage", () => {
  it("keeps the inclusive 5 through 150 acre band", () => {
    expect(MARKET_PARCEL_ACREAGE).toEqual({ min: 5, max: 150 });
    expect(inMarketAcreageBand(5)).toBe(true);
    expect(inMarketAcreageBand(150)).toBe(true);
    expect(inMarketAcreageBand(5.0001)).toBe(true);
    expect(inMarketAcreageBand(149.999)).toBe(true);
    expect(inMarketAcreageBand(4.999)).toBe(false);
    expect(inMarketAcreageBand(150.001)).toBe(false);
    expect(inMarketAcreageBand(null)).toBe(false);
    expect(inMarketAcreageBand(undefined)).toBe(false);
    const kept = featuresInAcreageBand([
      { properties: { acreage: 5 } },
      { properties: { acreage: 4.9 } },
      { properties: { acreage: 150 } },
      { properties: { acreage: 151 } },
      { properties: { acreage: null } },
    ]);
    expect(kept.map((feature) => feature.properties.acreage)).toEqual([5, 150]);
  });

  it("loads parcel mode only for the selected market that has polygons", () => {
    expect(showMarketParcels("Orlando", null, null, index)).toBe(false);
    expect(showOrlandoParcels("Tampa", null, null)).toBe(false);
    expect(showOrlandoParcels("Orlando", null, null)).toBe(true);
    expect(showMarketParcels("Tampa", null, null, index)).toBe(true);
    expect(showMarketParcels("Tampa", "Hillsborough", "Florida", index)).toBe(true);
    expect(showMarketParcels("Tampa", "Pinellas", "Florida", index)).toBe(true);
    expect(showMarketParcels("Tampa", "Polk", "Florida", index)).toBe(false);
    expect(showMarketParcels("Tampa", "Hillsborough", "Georgia", index)).toBe(false);
    expect(showMarketParcels("Savannah", null, null, index)).toBe(false);
    expect(showMarketParcels("Atlanta", null, null, index)).toBe(false);
    expect(showMarketParcels("Charlotte", null, null, null)).toBe(false);
  });

  it("shares the Orlando tile grid so viewports hit the same files", () => {
    expect(MARKET_PARCEL_TILE).toEqual(ORLANDO_PARCEL_TILE);
  });

  it("keeps seeded market fixtures inside the acreage band when a pull exists", () => {
    const indexPath = path.join(process.cwd(), "data/fixtures/market-parcels/index.json");
    if (!existsSync(indexPath)) return;
    const seeded = JSON.parse(readFileSync(indexPath, "utf8")) as MarketParcelIndex;
    expect(seeded.coreMinAcres).toBe(5);
    expect(seeded.coreMaxAcres).toBe(150);
    expect(seeded.markets.Orlando).toBeUndefined();
    for (const [market, summary] of Object.entries(seeded.markets)) {
      expect(showOrlandoParcels(market, null, null)).toBe(false);
      if (summary.parcelCount > 0) {
        expect(showMarketParcels(market, null, null, seeded)).toBe(true);
      } else {
        expect(showMarketParcels(market, null, null, seeded)).toBe(false);
      }
      for (const county of summary.counties) {
        if (county.coverage === "complete-gte-5ac") {
          expect(county.minAcres).toBe(5);
          expect(county.maxAcres).toBe(150);
          expect(county.featureCount).toBeGreaterThan(0);
        }
      }
    }
    const tileRoot = path.join(process.cwd(), "data/fixtures/market-parcels/counties");
    if (!existsSync(tileRoot)) return;
    const fipsDirs = readdirSync(tileRoot);
    let checked = 0;
    for (const fips of fipsDirs) {
      const tiles = path.join(tileRoot, fips, "tiles");
      if (!existsSync(tiles)) continue;
      const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"));
      if (!file) continue;
      const collection = JSON.parse(readFileSync(path.join(tiles, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features.slice(0, 25)) {
        expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
        expect(feature.properties.countyFips).toBe(fips);
        expect(feature.properties.marketIds?.includes("Orlando")).toBe(false);
        checked += 1;
      }
      if (checked >= 25) break;
    }
  });
});

describe("Atlanta ring county extracts", () => {
  const root = path.join(process.cwd(), "data/fixtures/market-parcels");

  function countyMeta(fips: string) {
    return JSON.parse(readFileSync(path.join(root, "counties", fips, "county.json"), "utf8")) as {
      coverage: string;
      featureCount: number;
      source: string;
      queryUrl: string;
      gaps: string[];
      minAcres: number;
      maxAcres: number;
    };
  }

  function firstFeature(fips: string): ParcelFeature {
    const tiles = path.join(root, "counties", fips, "tiles");
    const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"));
    if (!file) throw new Error(`No tiles for ${fips}`);
    const collection = JSON.parse(readFileSync(path.join(tiles, file), "utf8")) as {
      features: ParcelFeature[];
    };
    const feature = collection.features[0];
    if (!feature) throw new Error(`Empty tile for ${fips}`);
    return feature;
  }

  it("ships Gwinnett from GC_Parcel with zoning, tax, and unqualified sales", () => {
    const county = countyMeta("13135");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(1000);
    expect(county.minAcres).toBe(5);
    expect(county.maxAcres).toBe(150);
    expect(county.source).toBe("ga-gwinnett-gc-parcel");
    expect(county.queryUrl).toContain("GC_Parcel/MapServer/6");
    expect(county.queryUrl).not.toContain("FeatureServer/0");
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/qualified/i);
    expect(gaps).toMatch(/Lawrenceville/);
    expect(gaps).toMatch(/unincorporated/i);
    expect(gaps).toMatch(/Future Development/);
    const feature = firstFeature("13135");
    expect(feature.properties.countyFips).toBe("13135");
    expect(feature.properties.marketIds).toContain("Atlanta");
    expect(feature.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(feature.properties.acreage).toBeLessThanOrEqual(150);
    expect(feature.properties.ownerName).toBeTruthy();
    expect(feature.properties.lastSale.qualified).toBeNull();
    expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
  });

  it("documents the Gwinnett gaps and does not claim untiled counties are complete", () => {
    const docs = readFileSync(path.join(process.cwd(), "docs/market-parcels.md"), "utf8");
    expect(docs).toMatch(/no sale qualified flag/i);
    expect(docs).toMatch(/Lawrenceville/);
    expect(docs).toMatch(/FeatureServer\/0 is geometry and PIN only/);
    expect(docs).toMatch(/\| Gwinnett \| Georgia \| 13135 \| complete-gte-5ac \|/);
    expect(docs).not.toMatch(/Cherokee, Clayton, and Gwinnett are complete/);
  });
});
