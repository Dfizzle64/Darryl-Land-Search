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

  it("opens Chatham County, Georgia in qPublic AppID 1094, not Chatham County, North Carolina", () => {
    const link = parcelAppraiserUrl({ parcelId: "10010 01001", countyFips: "13051" });
    expect(link.href).toContain("AppID=1094");
    expect(link.href).toContain("ChathamCountyGA");
    expect(link.href).not.toMatch(/chathamcountync/i);
    expect(link.label).toMatch(/Chatham County, Georgia/);
  });

  it("keeps Chatham County, Georgia parcels in-state, with countywide zoning codes and FLU only for Savannah or unincorporated", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13051/county.json");
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      state: string;
      coverage: string;
      source: string;
      queryUrl: string | null;
      featureCount: number;
      gaps: string[];
      minAcres: number;
      maxAcres: number;
    };
    expect(county.fips).toBe("13051");
    expect(county.state).toBe("Georgia");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(1000);
    expect(county.minAcres).toBe(5);
    expect(county.maxAcres).toBe(150);
    expect(county.source).toBe("sagis-chatham-ga-parcel-digest");
    expect(county.queryUrl).toContain("pub.sagis.org");
    expect(county.queryUrl).toContain("ParcelDigest/MapServer/0");
    expect(county.queryUrl).not.toMatch(/chathamcountync/i);
    expect(county.queryUrl).not.toMatch(/Zoning_BND_AGOL/i);
    expect(county.queryUrl).not.toMatch(/MapServer\/40/i);
    const gapText = county.gaps.join("\n");
    expect(gapText).toMatch(/North Carolina/);
    expect(gapText).toMatch(/CODE 01/);
    expect(gapText).toMatch(/unincorporated only/i);
    expect(gapText).toMatch(/Savannah only/i);
    expect(gapText).toMatch(/not a designated Qualified Opportunity Zone/);
    expect(gapText).toMatch(/AppID=1094/);
    expect(gapText).toMatch(/eligible is not stored as designated/);

    const tiles = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13051/tiles");
    const files = readdirSync(tiles).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seenFlu = 0;
    let seenOtherCityGap = 0;
    let checked = 0;
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tiles, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(props.countyFips).toBe("13051");
        expect(props.state).toBe("Georgia");
        expect(props.marketIds).toContain("Savannah");
        expect(props.marketIds).not.toContain("Orlando");
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        const [lon, lat] = props.centroid;
        expect(lon).toBeLessThan(-80.5);
        expect(lon).toBeGreaterThan(-81.5);
        expect(lat).toBeGreaterThan(31.7);
        expect(lat).toBeLessThan(32.4);
        expect(props.appraiserUrl).toContain("AppID=1094");
        expect(props.opportunityZone).toBeNull();
        expect(props.oz2Eligibility).toBeNull();
        if (props.jurisdictionCode) {
          expect(["01", "02", "03", "04", "05", "06", "07", "08", "09"]).toContain(props.jurisdictionCode);
        }
        if (props.flu) {
          expect(["SAV", "UNI"]).toContain(props.flu.jurisdiction);
          expect(props.flu.source).toBe("sagis-opendata-boundaries-3");
          seenFlu += 1;
        }
        if ((props.dataGaps || []).some((gap) => /other municipalities|this municipality/i.test(gap))) {
          seenOtherCityGap += 1;
          expect(props.flu).toBeNull();
        }
        checked += 1;
      }
    }
    expect(checked).toBe(county.featureCount);
    expect(seenFlu).toBeGreaterThan(100);
    expect(seenOtherCityGap).toBeGreaterThan(50);
  });
});
