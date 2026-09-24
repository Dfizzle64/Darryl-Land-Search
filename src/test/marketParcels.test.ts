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

  it("ingests Spalding County on public GIS acres and leaves Griffin, FLU, sales, and tax empty", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13255/county.json");
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      markets: string[];
      featureCount: number;
      coverage: string;
      source: string;
      queryUrl: string;
      gaps: string[];
      lookup: string;
      path: string;
    };
    expect(county.fips).toBe("13255");
    expect(county.markets).toEqual(["Atlanta"]);
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("ga-spalding-parcels-public");
    expect(county.queryUrl).toContain("Parcels_Public_View/FeatureServer/1");
    expect(county.featureCount).toBe(3832);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/Griffin/);
    expect(gaps).toMatch(/FLU is null/);
    expect(gaps).toMatch(/qPublic AppID=766/);
    expect(gaps).toMatch(/Sunny Side/);
    expect(gaps).toMatch(/Regrid/);
    expect(gaps).toMatch(/LandPro/);
    expect(gaps).toMatch(/3624 JURISDICTION=COUNTY/);
    expect(gaps).toMatch(/199 Griffin CITY/);

    const lookup = JSON.parse(readFileSync(path.join(process.cwd(), county.lookup), "utf8")) as Record<string, string>;
    expect(Object.keys(lookup)).toHaveLength(county.featureCount);

    const tilesDir = path.join(process.cwd(), county.path);
    let count = 0;
    let zoned = 0;
    const byId = new Map<string, ParcelCollection["features"][number]>();
    for (const file of readdirSync(tilesDir)) {
      if (!file.endsWith(".geojson")) continue;
      const collection = JSON.parse(readFileSync(path.join(tilesDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        count += 1;
        const props = feature.properties;
        expect(props.countyFips).toBe("13255");
        expect(props.id.startsWith("13255:")).toBe(true);
        expect(feature.id).toBe(props.id);
        expect(props.marketIds).toEqual(["Atlanta"]);
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.flu).toBeNull();
        expect(props.opportunityZone).toBeNull();
        expect(props.oz2Eligibility).toBeNull();
        expect(props.ownerName).toBeNull();
        expect(props.situsAddress).toBeNull();
        expect(props.situsCity).toBeNull();
        expect(props.lastSale).toEqual({ date: null, price: null, qualified: null });
        expect(props.tax.marketValue).toBeNull();
        expect(props.tax.assessedValue).toBeNull();
        expect(props.tax.taxableValue).toBeNull();
        expect(JSON.stringify(props)).not.toMatch(/sunny side/i);
        const [lon, lat] = props.centroid;
        expect(lon).toBeGreaterThan(-84.55);
        expect(lon).toBeLessThan(-83.95);
        expect(lat).toBeGreaterThan(33.05);
        expect(lat).toBeLessThan(33.55);
        if (props.zoningCode) {
          zoned += 1;
          expect(props.zoningCode).toMatch(/^[A-Z0-9]+$/);
          expect(props.zoningDistrict).toBeNull();
        }
        byId.set(props.parcelId, feature);
      }
    }
    expect(count).toBe(county.featureCount);
    expect(zoned).toBe(3624);
    expect(count - zoned).toBe(208);

    const countyPin = byId.get("244 02001B");
    expect(countyPin?.properties.zoningCode).toBe("PRRRD");
    expect(countyPin?.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(countyPin?.properties.centroid[0]).toBeGreaterThan(-84.28);
    expect(countyPin?.properties.centroid[0]).toBeLessThan(-84.23);
    expect(countyPin?.properties.centroid[1]).toBeGreaterThan(33.3);
    expect(countyPin?.properties.centroid[1]).toBeLessThan(33.35);
    for (const parcelId of ["001 01001", "039 01003", "039 01004"]) {
      expect(byId.get(parcelId)?.properties.zoningCode).toBeNull();
    }

    const indexPath = path.join(process.cwd(), "data/fixtures/market-parcels/index.json");
    const seeded = JSON.parse(readFileSync(indexPath, "utf8")) as MarketParcelIndex;
    const atlanta = seeded.markets.Atlanta;
    expect(atlanta.parcelCount).toBe(atlanta.counties.reduce((sum, item) => sum + item.featureCount, 0));
    const spalding = atlanta.counties.find((item) => item.fips === "13255");
    expect(spalding?.coverage).toBe("complete-gte-5ac");
    expect(spalding?.featureCount).toBe(county.featureCount);
  });
});
