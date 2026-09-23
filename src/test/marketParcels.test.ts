import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
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

  it("links Birmingham MSA counties to their public property search", () => {
    expect(parcelAppraiserUrl({ parcelId: "01 6 23 0 001 019.007", countyFips: "01117" })).toMatchObject({
      href: "https://ptc.shelbyal.com/propsearch",
      label: "Open Shelby Property Appraiser search",
    });
    expect(parcelAppraiserUrl({ parcelId: "2909320001023031", countyFips: "01115" }).href).toBe(
      "https://isv.kcsgis.com/al.stclair_revenue/",
    );
    expect(parcelAppraiserUrl({ parcelId: "1300163000001000", countyFips: "01073" }).href).toBe(
      "https://eringcapture.jccal.org/propsearch",
    );
    expect(parcelAppraiserUrl({ parcelId: "1300163000001000", countyFips: "01073" }).href).not.toContain("ocpafl");
  });

  it("keeps Shelby and St. Clair county parcels and city zoning overlays", () => {
    const root = path.join(process.cwd(), "data/fixtures/market-parcels/counties");
    const readCounty = (fips: string) => JSON.parse(readFileSync(path.join(root, fips, "county.json"), "utf8"));
    const shelby = readCounty("01117");
    const clair = readCounty("01115");
    const jefferson = readCounty("01073");
    const walker = readCounty("01127");
    expect(shelby.coverage).toBe("complete-gte-5ac");
    expect(shelby.source).toBe("al-shelby-cadastral-2025");
    expect(shelby.queryUrl).toContain("Cadastral_2025/MapServer/91");
    expect(shelby.featureCount).toBeGreaterThan(1000);
    expect(shelby.gaps.join(" ")).toMatch(/Alabaster/);
    expect(shelby.gaps.join(" ")).toMatch(/Municipal overlay/);
    expect(clair.coverage).toBe("complete-gte-5ac");
    expect(clair.source).toBe("al-stclair-owner-parcels");
    expect(clair.queryUrl).toContain("PublicParcelViewerStPln/MapServer/57");
    expect(clair.featureCount).toBeGreaterThan(1000);
    expect(jefferson.source).toBe("al-jefferson-parcels");
    expect(jefferson.queryUrl).toContain("jccgis.jccal.org");
    expect(jefferson.gaps.join(" ")).toMatch(/Gap-fill only/);
    expect(jefferson.gaps.join(" ")).toMatch(/Municipal overlay/);
    expect(jefferson.gaps.join(" ")).toMatch(/blank VH_ZONING/);
    expect(walker.coverage).toBe("gap");
    expect(walker.featureCount).toBe(0);
    expect(walker.gaps.join(" ")).toMatch(/no public ArcGIS MapServer/i);

    const sample = (fips: string) => {
      const tiles = path.join(root, fips, "tiles");
      const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"));
      expect(file).toBeTruthy();
      return JSON.parse(readFileSync(path.join(tiles, file!), "utf8")) as ParcelCollection;
    };
    const shelbyTile = sample("01117");
    const owned = shelbyTile.features.find((feature) => feature.properties.ownerName && feature.geometry);
    expect(owned?.properties.countyFips).toBe("01117");
    expect(owned?.properties.state).toBe("Alabama");
    expect(inMarketAcreageBand(owned?.properties.acreage)).toBe(true);
    expect(owned?.geometry.type === "Polygon" || owned?.geometry.type === "MultiPolygon").toBe(true);

    const countIn = (text: string, label: string) => {
      const match = text.match(new RegExp(`${label} (\\d+)`));
      return match ? Number(match[1]) : 0;
    };
    const jeffGaps = jefferson.gaps.join(" ");
    const shelbyGaps = shelby.gaps.join(" ");
    expect(countIn(jeffGaps, "Birmingham zoning")).toBeGreaterThan(0);
    expect(countIn(jeffGaps, "Birmingham FLU")).toBeGreaterThan(0);
    expect(countIn(jeffGaps, "Hoover")).toBeGreaterThan(0);
    expect(countIn(shelbyGaps, "Helena")).toBeGreaterThan(0);
    expect(countIn(shelbyGaps, "Pelham")).toBeGreaterThan(0);

    const clairTile = sample("01115");
    const clairOwned = clairTile.features.find(
      (feature) => feature.properties.ownerName && (feature.properties.tax.marketValue || feature.properties.lastSale.date),
    );
    expect(clairOwned?.properties.countyFips).toBe("01115");
    expect(inMarketAcreageBand(clairOwned?.properties.acreage)).toBe(true);
  });
});
