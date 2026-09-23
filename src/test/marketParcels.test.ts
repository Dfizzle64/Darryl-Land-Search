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

describe("Henry County GA parcels", () => {
  const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13151/county.json");

  it("opens Henry qPublic from the parcel deep link", () => {
    const deep =
      "https://qpublic.schneidercorp.com/Application.aspx?AppID=1035&LayerID=22139&PageTypeID=4&PageID=15803&KeyValue=002-01002000";
    expect(parcelAppraiserUrl({ parcelId: "002-01002000", countyFips: "13151", appraiserUrl: deep })).toEqual({
      href: deep,
      label: "Open in Henry County qPublic",
    });
    expect(parcelAppraiserUrl({ parcelId: "002-01002000", countyFips: "13151" }).href).toContain("App=HenryCountyGA");
  });

  it("keeps the 5–150 acre Atlanta extract and does not invent CAMA fields", () => {
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      coverage: string;
      featureCount: number;
      source: string;
      queryUrl: string;
      gaps: string[];
      markets: string[];
    };
    expect(county.fips).toBe("13151");
    expect(county.markets).toContain("Atlanta");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(1000);
    expect(county.source).toBe("ga-henry-parcels");
    expect(county.queryUrl).toContain("Parcels/MapServer/12");
    expect(county.queryUrl).not.toContain("gbzZfTaSTnfRdQPt");
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/qPublic/i);
    expect(gaps).toMatch(/last sale/i);
    expect(gaps).toMatch(/Mustang/i);
    expect(gaps).toMatch(/Hampton/i);
    expect(gaps).toMatch(/Flippen/i);
    expect(gaps).toMatch(/FLU2023=CITY/);

    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13151/tiles");
    const files = readdirSync(tileDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seen = 0;
    let zoned = 0;
    let fluJoined = 0;
    let owners = 0;
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tileDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        seen += 1;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("13151");
        expect(props.state).toBe("Georgia");
        expect(props.marketIds).toEqual(["Atlanta"]);
        expect(props.appraiserUrl || "").toContain("schneidercorp.com");
        expect(props.appraiserUrl || "").toContain("KeyValue=");
        expect(props.lastSale.date).toBeNull();
        expect(props.lastSale.price).toBeNull();
        expect(props.lastSale.qualified).toBeNull();
        expect(props.tax.marketValue).toBeNull();
        expect(props.tax.assessedValue).toBeNull();
        expect(props.tax.taxableValue).toBeNull();
        expect(props.mailingAddress.line1).toBeNull();
        expect(props.flu?.code).not.toBe("CITY");
        if (props.zoningCode) zoned += 1;
        if (props.flu?.code) fluJoined += 1;
        if (props.ownerName) {
          owners += 1;
          expect(props.dataGaps?.join(" ") || "").toMatch(/McDonough/);
        }
      }
    }
    expect(seen).toBe(county.featureCount);
    expect(zoned).toBeGreaterThan(seen * 0.5);
    expect(fluJoined).toBeGreaterThan(0);
    expect(owners).toBeGreaterThan(0);
  });
});
