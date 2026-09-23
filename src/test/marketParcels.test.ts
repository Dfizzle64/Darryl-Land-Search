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
});

describe("Mecklenburg County parcel extract", () => {
  const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37119/county.json");

  it("joins county outlines, CAMA attributes, zoning, sales, and city Place Types", () => {
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      source: string;
      featureCount: number;
      gaps: string[];
      minAcres: number;
      maxAcres: number;
    };
    expect(county.source).toBe("meck-taxparcel-camadata-37119");
    expect(county.featureCount).toBeGreaterThan(7000);
    expect(county.minAcres).toBe(5);
    expect(county.maxAcres).toBe(150);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/ParcelsViewer/);
    expect(gaps).toMatch(/Place Types/);
    expect(gaps).toMatch(/Cornelius/);
    expect(gaps).toMatch(/does not cover Mecklenburg towns/);
    expect(gaps).not.toMatch(/join failed/i);
    expect(gaps).toMatch(/phones and emails are not/);

    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37119/tiles");
    let owners = 0;
    let zoned = 0;
    let flu = 0;
    let townGap = 0;
    let polaris = 0;
    let total = 0;
    let zimmermann: ParcelCollection["features"][number] | undefined;
    for (const name of readdirSync(tileDir)) {
      if (!name.endsWith(".geojson")) continue;
      const collection = JSON.parse(readFileSync(path.join(tileDir, name), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        total += 1;
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("37119");
        expect(props.state).toBe("North Carolina");
        expect(props.marketIds).toEqual(["Charlotte"]);
        expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
        const [lon, lat] = props.centroid;
        expect(lon).toBeGreaterThan(-81.6);
        expect(lon).toBeLessThan(-80.3);
        expect(lat).toBeGreaterThan(34.9);
        expect(lat).toBeLessThan(35.6);
        if (props.ownerName) owners += 1;
        if (props.zoningCode) zoned += 1;
        if (props.flu?.code) {
          flu += 1;
          expect(props.flu.jurisdiction).toBe("Charlotte");
          expect(props.flu.source).toMatch(/2040/);
        }
        if (props.dataGaps?.some((gap) => gap.includes("Place Types"))) townGap += 1;
        if (props.appraiserUrl?.includes("polaris3g.mecklenburgcountync.gov/pid/")) polaris += 1;
        if (props.parcelId === "4661960387") zimmermann = feature;
      }
    }
    expect(total).toBe(county.featureCount);
    expect(owners).toBeGreaterThan(7000);
    expect(zoned).toBeGreaterThan(7000);
    expect(flu).toBeGreaterThan(500);
    expect(flu).toBeLessThan(total);
    expect(townGap).toBeGreaterThan(500);
    expect(polaris).toBe(total);
    expect(zimmermann?.properties.ownerName).toBe("ZIMMERMANN MARGARET U F");
    expect(zimmermann?.properties.zoningCode).toBe("R");
    expect(zimmermann?.properties.situsCity).toBe("HUNTERSVILLE");
    expect(zimmermann?.properties.appraiserUrl).toBe("https://polaris3g.mecklenburgcountync.gov/pid/01113108");
    expect(zimmermann?.properties.flu).toBeNull();
  });
});
