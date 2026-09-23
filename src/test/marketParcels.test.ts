import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl } from "../lib/format";
import {
  featuresInAcreageBand,
  inMarketAcreageBand,
  MARKET_PARCEL_ACREAGE,
  MARKET_PARCEL_TILE,
  showMarketParcels,
  type MarketParcelIndex,
} from "../lib/marketParcels";
import { ORLANDO_PARCEL_TILE, showOrlandoParcels } from "../lib/orlandoParcels";
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

describe("Greenville–Spartanburg parcel enrich", () => {
  it("links Greenville and Spartanburg assessor searches", () => {
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "45045" })).toEqual({
      href: "https://www.greenvillecounty.org/AppsAS400/RealProperty/",
      label: "Open Greenville County Property Appraiser search",
    });
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "45083" })).toEqual({
      href: "https://www.spartanburgcounty.gov/288/Assessor-Property-Records-Search",
      label: "Open Spartanburg County Property Appraiser search",
    });
  });

  it("keeps countywide 5–150 acre rolls with owner, mail, situs, tax, and city zoning", () => {
    const root = path.join(process.cwd(), "data/fixtures/market-parcels/counties");
    const expected = [
      {
        fips: "45045",
        source: "sc-greenville-gcgia-tax-parcel",
        url: "GCGIA_FeatureAccess/FeatureServer/10",
      },
      {
        fips: "45083",
        source: "sc-spartanburg-cama-parcels",
        url: "GIS/CAMA_Parcels/FeatureServer/0",
      },
    ];
    for (const county of expected) {
      const meta = JSON.parse(readFileSync(path.join(root, county.fips, "county.json"), "utf8")) as {
        coverage: string;
        source: string;
        queryUrl: string;
        featureCount: number;
        gaps: string[];
        markets: string[];
      };
      expect(meta.coverage).toBe("complete-gte-5ac");
      expect(meta.source).toBe(county.source);
      expect(meta.queryUrl).toContain(county.url);
      expect(meta.queryUrl.includes("Greenville_Base_Data")).toBe(false);
      expect(meta.queryUrl.includes("Campobello")).toBe(false);
      expect(meta.featureCount).toBeGreaterThan(1000);
      expect(meta.markets).toContain("Greenville");
      expect(meta.gaps.join(" ").includes("EnerGov") || county.fips === "45045").toBe(true);
      const tiles = readdirSync(path.join(root, county.fips, "tiles")).filter((name) => name.endsWith(".geojson"));
      expect(tiles.length).toBeGreaterThan(0);
      let sawOwner = false;
      let sawMail = false;
      let sawSitus = false;
      let sawTax = false;
      let sawZoning = false;
      let checked = 0;
      for (const tile of tiles) {
        const collection = JSON.parse(readFileSync(path.join(root, county.fips, "tiles", tile), "utf8")) as ParcelCollection;
        for (const feature of collection.features) {
          if (checked < 30) {
            expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
            expect(feature.properties.countyFips).toBe(county.fips);
            expect(feature.properties.marketIds).toContain("Greenville");
            expect(feature.properties.source).toBe(county.source);
            checked += 1;
          }
          expect(String(feature.properties.zoningSource || "").toLowerCase().includes("energov")).toBe(false);
          if (feature.properties.ownerName) sawOwner = true;
          if (feature.properties.mailingAddress?.line1) sawMail = true;
          if (feature.properties.situsAddress) sawSitus = true;
          if (feature.properties.tax?.marketValue || feature.properties.tax?.taxes || feature.properties.tax?.taxableValue) sawTax = true;
          if (feature.properties.zoningCode && feature.properties.municipality) sawZoning = true;
        }
      }
      expect(sawOwner).toBe(true);
      expect(sawMail).toBe(true);
      expect(sawSitus).toBe(true);
      expect(sawTax).toBe(true);
      expect(sawZoning).toBe(true);
    }
  });
});
