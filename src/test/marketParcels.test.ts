import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { findFluCategory } from "../lib/flu";
import {
  featuresInAcreageBand,
  inMarketAcreageBand,
  MARKET_PARCEL_ACREAGE,
  MARKET_PARCEL_TILE,
  showMarketParcels,
  type MarketParcelIndex,
} from "../lib/marketParcels";
import { ORLANDO_PARCEL_TILE, showOrlandoParcels } from "../lib/orlandoParcels";
import type { FluConfig, ParcelCollection, ParcelFeature, ZoningConfig } from "../lib/types";
import { findZoningHit } from "../lib/zoning";

const SOCIAL_CIRCLE_ZONING = new Set([
  "AG",
  "AG-2",
  "CBD",
  "GC",
  "I-1",
  "I-2",
  "IO",
  "NC",
  "PUD",
  "R-15",
  "R-25",
  "RHD",
  "RMD",
  "SSBP-T1",
]);

const NEWTON_FLU_JURISDICTIONS = new Set([
  "COVINGTON",
  "OXFORD",
  "PORTERDALE",
  "MANSFIELD",
  "NEWBORN",
  "SOCIAL CIRCLE",
  "NEWTON",
]);

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

  it("keeps Newton County GA inside 13217, the acreage band, and the public-source gaps", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13217/county.json");
    if (!existsSync(countyPath)) return;
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      coverage: string;
      featureCount: number;
      source: string;
      gaps: string[];
    };
    if (county.coverage !== "complete-gte-5ac") return;
    expect(county.fips).toBe("13217");
    expect(county.source).toBe("ga-newton-uofmd-parcels");
    expect(county.featureCount).toBeGreaterThan(0);
    const gapText = county.gaps.join(" ");
    expect(gapText).toMatch(/University of Maryland/i);
    expect(gapText).toMatch(/2021/);
    expect(gapText).toMatch(/Covington/);
    expect(gapText).toMatch(/Social Circle/);
    expect(gapText).toMatch(/NEGRC/);
    const zoningConfig = JSON.parse(
      readFileSync(path.join(process.cwd(), "data/zoning-config.json"), "utf8"),
    ) as ZoningConfig;
    const fluConfig = JSON.parse(readFileSync(path.join(process.cwd(), "data/flu-config.json"), "utf8")) as FluConfig;
    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13217/tiles");
    const features: ParcelFeature[] = [];
    for (const name of readdirSync(tileDir)) {
      if (!name.endsWith(".geojson")) continue;
      const collection = JSON.parse(readFileSync(path.join(tileDir, name), "utf8")) as ParcelCollection;
      features.push(...collection.features);
    }
    expect(features).toHaveLength(county.featureCount);
    let socialCircle = 0;
    let fluJoined = 0;
    const fluSources = new Set<string>();
    for (const feature of features) {
      const props = feature.properties;
      expect(props.countyFips).toBe("13217");
      expect(props.id.startsWith("13217:")).toBe(true);
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.marketIds).toEqual(["Atlanta"]);
      expect(props.ownerName).toBeNull();
      expect(props.ownerName2).toBeNull();
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.tax.marketValue).toBeNull();
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.lastSale.qualified).toBeNull();
      if (props.lastSale.date) {
        expect(props.lastSale.date <= "2021-12-31").toBe(true);
      }
      if (props.situsAddress) {
        expect(props.situsAddress).not.toMatch(/^\d+\s/);
      }
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-84.08);
      expect(lon).toBeLessThan(-83.64);
      expect(lat).toBeGreaterThan(33.34);
      expect(lat).toBeLessThan(33.77);
      expect(props.appraiserUrl ?? "").toContain("App=NewtonCountyGA");
      expect(props.appraiserUrl ?? "").toContain(encodeURIComponent(props.parcelId));
      if (props.zoningCode) {
        socialCircle += 1;
        expect(SOCIAL_CIRCLE_ZONING.has(props.zoningCode)).toBe(true);
        expect(props.jurisdictionPrefix).toBe("SOC");
        expect(findZoningHit(props.zoningCode, props.zoningDistrict, zoningConfig)).toBeNull();
      } else {
        expect(props.jurisdictionPrefix).toBeNull();
      }
      if (props.flu?.code) {
        fluJoined += 1;
        expect(NEWTON_FLU_JURISDICTIONS.has(props.flu.jurisdiction ?? "")).toBe(true);
        expect(findFluCategory(props.flu, fluConfig)).toBeNull();
        if (props.flu.source) fluSources.add(props.flu.source);
      }
    }
    expect(socialCircle).toBeGreaterThan(0);
    expect(fluJoined).toBeGreaterThan(0);
    expect(fluSources.has("negrc-newton-ca-454")).toBe(true);
    expect(fluSources.has("negrc-covington-flu-447")).toBe(true);
    expect(fluSources.has("negrc-social-circle-ca-469")).toBe(true);
  });
});
