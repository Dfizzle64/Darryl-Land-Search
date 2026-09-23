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

describe("Mobile MSA Alabama parcels", () => {
  it("links Baldwin and Mobile appraisers", () => {
    const baldwin = parcelAppraiserUrl({ parcelId: "5404203000004000", countyFips: "01003" });
    expect(baldwin.href).toContain("al.baldwin_revenue");
    expect(baldwin.label).toContain("Baldwin");
    const mobile = parcelAppraiserUrl({
      parcelId: "0208280000002.000",
      countyFips: "01097",
      appraiserUrl: "https://esearch.mobilecopropertytax.com/Property/View/14870?year=2024",
    });
    expect(mobile.href).toContain("/Property/View/14870");
    expect(mobile.label).toContain("Mobile");
    expect(mobile.href).not.toContain("ocpafl.org");
  });

  it("keeps Escambia Alabama and Washington as Flagship gaps", () => {
    const escambia = JSON.parse(
      readFileSync(path.join(process.cwd(), "data/fixtures/market-parcels/counties/01053/county.json"), "utf8"),
    );
    const washington = JSON.parse(
      readFileSync(path.join(process.cwd(), "data/fixtures/market-parcels/counties/01129/county.json"), "utf8"),
    );
    expect(escambia.coverage).toBe("gap");
    expect(escambia.featureCount).toBe(0);
    expect(escambia.gaps.join(" ")).toMatch(/Flagship HTML/);
    expect(escambia.gaps.join(" ")).toMatch(/not Escambia County, Florida/);
    expect(washington.coverage).toBe("gap");
    expect(washington.featureCount).toBe(0);
    expect(washington.gaps.join(" ")).toMatch(/Flagship HTML/);
  });

  it("ships Baldwin and Mobile 5–150 acre parcels with city zoning overlays", () => {
    const root = path.join(process.cwd(), "data/fixtures/market-parcels/counties");
    const baldwin = JSON.parse(readFileSync(path.join(root, "01003/county.json"), "utf8"));
    const mobile = JSON.parse(readFileSync(path.join(root, "01097/county.json"), "utf8"));
    expect(baldwin.coverage).toBe("complete-gte-5ac");
    expect(baldwin.featureCount).toBeGreaterThan(1000);
    expect(baldwin.queryUrl).toContain("Baldwin_Public_ISV/MapServer/31");
    expect(baldwin.queryUrl).not.toContain("al05baldrevenue");
    expect(baldwin.source).toBe("al-baldwin-public-isv");
    const baldwinGaps = baldwin.gaps.join(" ");
    expect(baldwinGaps).toMatch(/CalcAcre/);
    expect(baldwinGaps).toMatch(/Zoning\/42/);
    expect(baldwinGaps).toMatch(/Foley zoning is a PID join/);
    expect(baldwinGaps).toMatch(/Gulf Shores zoning overlay/);
    expect(baldwinGaps).toMatch(/Orange Beach zoning overlay/);
    expect(baldwinGaps).toMatch(/Daphne has no public zoning REST/);
    expect(baldwinGaps).toMatch(/Fairhope base zoning was not found/);

    expect(mobile.coverage).toBe("complete-gte-5ac");
    expect(mobile.featureCount).toBeGreaterThan(1000);
    expect(mobile.queryUrl).toContain("Mobile_County_Facilities/FeatureServer/0");
    expect(mobile.source).toBe("al-mobile-agol-capturecama");
    const mobileGaps = mobile.gaps.join(" ");
    expect(mobileGaps).toMatch(/CaptureCAMA/);
    expect(mobileGaps).toMatch(/EG_Data_MS\/MapServer\/20/);
    expect(mobileGaps).toMatch(/EG_Data_MS\/1 is an alternate/);
    expect(mobileGaps).toMatch(/2023\/06\/21/);

    const baldwinStats = tallyCounty(path.join(root, "01003/tiles"), "01003");
    expect(baldwinStats.features).toBe(baldwin.featureCount);
    expect(baldwinStats.owners).toBeGreaterThan(baldwinStats.features * 0.8);
    expect(baldwinStats.withTax).toBeGreaterThan(baldwinStats.features * 0.5);
    expect(baldwinStats.zones).toBeGreaterThan(100);
    expect(baldwinStats.cities["Foley"] ?? 0).toBeGreaterThan(0);
    expect(baldwinStats.markets.has("Mobile")).toBe(true);
    expect(baldwinStats.markets.has("Pensacola")).toBe(true);
    expect(baldwinStats.appraiser).toContain("baldwin_revenue");

    const mobileStats = tallyCounty(path.join(root, "01097/tiles"), "01097");
    expect(mobileStats.features).toBe(mobile.featureCount);
    expect(mobileStats.owners).toBeGreaterThan(mobileStats.features * 0.8);
    expect(mobileStats.withTax).toBeGreaterThan(mobileStats.features * 0.5);
    expect(mobileStats.cities["City of Mobile"] ?? 0).toBeGreaterThan(0);
    expect(mobileStats.markets.has("Mobile")).toBe(true);
    expect(mobileStats.markets.has("Pensacola")).toBe(false);
    expect(mobileStats.appraiser).toContain("esearch.mobilecopropertytax.com");
  });
});

function tallyCounty(tiles: string, fips: string) {
  const names = readdirSync(tiles).filter((name) => name.endsWith(".geojson"));
  let features = 0;
  let owners = 0;
  let withTax = 0;
  let zones = 0;
  const cities: Record<string, number> = {};
  const markets = new Set<string>();
  let appraiser = "";
  for (const name of names) {
    const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
    for (const feature of collection.features) {
      const props = feature.properties;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.countyFips).toBe(fips);
      expect(props.state).toBe("Alabama");
      expect(props.marketIds?.includes("Orlando")).toBe(false);
      features += 1;
      if (props.ownerName) owners += 1;
      if (props.tax?.marketValue != null) withTax += 1;
      if (props.zoningCode) zones += 1;
      if (props.jurisdictionCode) cities[props.jurisdictionCode] = (cities[props.jurisdictionCode] ?? 0) + 1;
      for (const market of props.marketIds ?? []) markets.add(market);
      if (!appraiser && props.appraiserUrl) appraiser = props.appraiserUrl;
    }
  }
  return { features, owners, withTax, zones, cities, markets, appraiser };
}
