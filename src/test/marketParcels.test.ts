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
import { parcelAppraiserUrl } from "../lib/format";
import type { ParcelCollection } from "../lib/types";

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

describe("Pender County Energov extract", () => {
  const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37141/county.json");

  it("uses county Energov parcels and does not treat nomination eligibility as a designated QOZ", () => {
    const row = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      source: string;
      coverage: string;
      featureCount: number;
      minAcres: number;
      maxAcres: number;
      queryUrl: string;
      gaps: string[];
      zoningJoinedCount?: number;
      fluJoinedCount?: number;
      oz2EligibleCount?: number;
      atkinsonUnzonedCount?: number;
    };
    expect(row.fips).toBe("37141");
    expect(row.source).toBe("nc-pender-energov-37141");
    expect(row.queryUrl).toContain("/Energov/MapServer/1/query");
    expect(row.coverage).toBe("complete-gte-5ac");
    expect(row.minAcres).toBe(5);
    expect(row.maxAcres).toBe(150);
    expect(row.featureCount).toBeGreaterThan(7000);
    expect(row.featureCount).toBeLessThan(8000);
    expect(row.zoningJoinedCount).toBeGreaterThan(0);
    expect(row.fluJoinedCount).toBeGreaterThan(0);
    const gaps = row.gaps.join(" ");
    expect(gaps).toMatch(/Atkinson/i);
    expect(gaps).toMatch(/no public zoning layer/i);
    expect(gaps).toMatch(/Wallace/);
    expect(row.atkinsonUnzonedCount).toBeGreaterThan(0);
    expect(gaps).toMatch(/cntyfips='141'/);
    expect(gaps).toMatch(/eligible-for-nomination/);
    expect(gaps).toMatch(/not a 2027 QOZ designation/i);
    expect(gaps).toMatch(/37141920601/);
    expect(row.oz2EligibleCount).toBeGreaterThan(0);

    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37141/tiles");
    const files = readdirSync(tileDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let counted = 0;
    let zoning = 0;
    let flu = 0;
    let oz2 = 0;
    let atkinson = 0;
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tileDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        counted += 1;
        expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
        expect(feature.properties.countyFips).toBe("37141");
        expect(feature.properties.source).toBe("nc-pender-energov-37141");
        expect(feature.properties.marketIds).toEqual(["Wilmington"]);
        expect(feature.properties.opportunityZone).toBeNull();
        const eligibility = feature.properties.oz2Eligibility;
        if (eligibility) {
          oz2 += 1;
          expect(eligibility.eligible).toBe(true);
          expect(eligibility.designation).toBe("eligible-for-nomination");
          expect(eligibility.tractGeoid === "37141920204" || eligibility.tractGeoid === "37141920403").toBe(true);
        }
        if (feature.properties.zoningCode) zoning += 1;
        if (feature.properties.flu?.code) flu += 1;
        const gapText = (feature.properties.dataGaps ?? []).join(" ");
        if (/Atkinson/i.test(gapText)) {
          atkinson += 1;
          expect(feature.properties.zoningCode).toBeNull();
        }
      }
    }
    expect(counted).toBe(row.featureCount);
    expect(zoning).toBe(row.zoningJoinedCount);
    expect(flu).toBe(row.fluJoinedCount);
    expect(oz2).toBe(row.oz2EligibleCount);
    expect(atkinson).toBe(row.atkinsonUnzonedCount);
  });

  it("links Pender parcels to the county real estate search instead of Orange County", () => {
    const link = parcelAppraiserUrl({ parcelId: "2229-41-7914-0000", countyFips: "37141" });
    expect(link.href).toContain("pendercountync.gov");
    expect(link.label).toMatch(/Pender/i);
    expect(link.href).not.toContain("ocpafl.org");
  });
});
