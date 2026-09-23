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
import { parcelAppraiserUrl } from "../lib/format";
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

  it("keeps Forsyth County GA on the Atlanta 5–150 acre extract and records the real gaps", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13117/county.json");
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      state: string;
      markets: string[];
      featureCount: number;
      coverage: string;
      source: string;
      queryUrl: string;
      gaps: string[];
      appraiserSearchUrl?: string;
      ownerJoinedCount?: number;
      fluJoinedCount?: number;
      cummingParcelCount?: number;
      characterAreaCount?: number;
    };
    expect(county.fips).toBe("13117");
    expect(county.state).toBe("Georgia");
    expect(county.markets).toContain("Atlanta");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(3500);
    expect(county.source).toBe("ga-forsyth-tax-parcels");
    expect(county.queryUrl).toContain("geo.forsythco.com");
    expect(county.queryUrl.toLowerCase()).not.toContain("forsyth.cc");
    expect(county.appraiserSearchUrl).toBe("https://www.qpublic.net/ga/forsyth/search.html");
    expect(county.ownerJoinedCount ?? 0).toBeGreaterThan(3000);
    expect(county.characterAreaCount).toBe(11);
    expect(county.fluJoinedCount ?? 0).toBeGreaterThan(0);
    expect(county.cummingParcelCount ?? 0).toBeGreaterThan(0);
    const gapText = county.gaps.join(" ").toLowerCase();
    expect(gapText).toContain("qpublic");
    expect(gapText).toContain("character");
    expect(gapText).toContain("cumming");
    expect(gapText).toContain("forsyth county, north carolina");
    expect(gapText).toContain("athens-clarke");
    expect(gapText).not.toContain("forsyth.cc parcel");

    const tiles = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13117/tiles");
    const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"));
    expect(file).toBeTruthy();
    const collection = JSON.parse(readFileSync(path.join(tiles, file as string), "utf8")) as ParcelCollection;
    const feature = collection.features[0];
    expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
    expect(feature.properties.countyFips).toBe("13117");
    expect(feature.properties.state).toBe("Georgia");
    expect(feature.properties.marketIds).toEqual(["Atlanta"]);
    expect(feature.properties.lastSale).toEqual({ date: null, price: null, qualified: null });
    expect(feature.properties.tax.assessedValue).toBeNull();
    const [lon, lat] = feature.properties.centroid;
    expect(lon).toBeGreaterThan(-84.45);
    expect(lon).toBeLessThan(-83.9);
    expect(lat).toBeGreaterThan(33.95);
    expect(lat).toBeLessThan(34.45);
    expect(feature.properties.appraiserUrl || "").not.toMatch(/forsyth\.cc/i);
    const link = parcelAppraiserUrl({
      parcelId: feature.properties.parcelId,
      countyFips: "13117",
      appraiserUrl: feature.properties.appraiserUrl,
    });
    expect(link.label).toMatch(/Forsyth/);
    expect(link.href).not.toMatch(/forsyth\.cc/i);
  });
});
