import { readFileSync, existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl, parcelPlaceLine } from "../lib/format";
import { catalogForMarket, isOtherMarketId, isParcelMarketId, isPrimaryMarket, isSearchMarketId } from "../lib/markets";
import {
  buncombePropCardUrl,
  castBuncombeMoney,
  composeBuncombeSitus,
  parseBuncombeDeedDate,
  trustedBuncombeSalePrice,
} from "../lib/buncombeParcels";
import { OTHER_MARKETS, type ParcelCollection, type RuralMarketsCatalog, type EligibleMarketsCatalog } from "../lib/types";
import { inMarketAcreageBand } from "../lib/marketParcels";

describe("Buncombe sale, situs, and property card", () => {
  it("drops stamp-like and stamp-inconsistent prices and keeps plausible ones", () => {
    expect(trustedBuncombeSalePrice({ salePrice: 0, stamps: 0, landValue: 100000, marketValue: 100000 })).toBeNull();
    expect(trustedBuncombeSalePrice({ salePrice: 1100, stamps: 4000, landValue: 359700, marketValue: 776900 })).toBeNull();
    expect(trustedBuncombeSalePrice({ salePrice: 2700, stamps: 0, landValue: 33300, marketValue: 348000 })).toBeNull();
    expect(trustedBuncombeSalePrice({ salePrice: 21700, stamps: 0, landValue: 218400, marketValue: 709000 })).toBeNull();
    expect(trustedBuncombeSalePrice({ salePrice: 632100, stamps: 70921, landValue: 1951300, marketValue: 42101600 })).toBeNull();
    const matched = trustedBuncombeSalePrice({
      salePrice: 200000,
      stamps: 400,
      landValue: 150000,
      marketValue: 250000,
    });
    expect(matched).toBe(200000);
    expect(
      trustedBuncombeSalePrice({ salePrice: 370100, stamps: 0, landValue: 489200, marketValue: 859300 }),
    ).toBe(370100);
    expect(
      trustedBuncombeSalePrice({ salePrice: 5450500, stamps: 0, landValue: 4274900, marketValue: 16723400 }),
    ).toBe(5450500);
  });

  it("composes situs from street parts and does not use the mailing address", () => {
    expect(
      composeBuncombeSitus({
        houseNumber: "438",
        numberSuffix: "",
        streetPrefix: "",
        streetName: "SANDY MUSH CREEK",
        streetType: "RD",
        postDirection: "",
      }),
    ).toBe("438 SANDY MUSH CREEK RD");
    expect(
      composeBuncombeSitus({
        houseNumber: "440",
        numberSuffix: "A",
        streetName: "WINDSWEPT",
        streetType: "DR",
      }),
    ).toBe("440A WINDSWEPT DR");
    expect(castBuncombeMoney("348000")).toBe(348000);
    expect(castBuncombeMoney("")).toBeNull();
    expect(parseBuncombeDeedDate("20250626")).toBe("2025-06-26");
    expect(parseBuncombeDeedDate("")).toBeNull();
    expect(buncombePropCardUrl("963470749800000", "https://example.com/963470749800000")).toBe(
      "https://prc-buncombe.spatialest.com/#/property/963470749800000",
    );
  });

  it("opens the Spatialest property card for Buncombe", () => {
    const link = parcelAppraiserUrl({
      parcelId: "963470749800000",
      countyFips: "37021",
      appraiserUrl: "https://prc-buncombe.spatialest.com/#/property/963470749800000",
    });
    expect(link.href).toBe("https://prc-buncombe.spatialest.com/#/property/963470749800000");
    expect(link.label).toBe("Open Buncombe property card");
    expect(
      parcelPlaceLine({ situsCity: null, situsZip: null, countyName: "Buncombe", state: "North Carolina" }),
    ).toBe("Buncombe County, NC");
    expect(parcelPlaceLine({ situsCity: "Weaverville", situsZip: null, countyName: "Buncombe", state: "North Carolina" })).toBe(
      "Weaverville",
    );
    expect(parcelPlaceLine({ situsCity: null, countyName: "Orange", state: "Florida" })).toBe("Orange County, FL");
  });

  it("adds Asheville as a parcel market without treating it as an OZ screening market", () => {
    expect(OTHER_MARKETS).not.toContain("Asheville");
    expect(isSearchMarketId("Asheville")).toBe(true);
    expect(isParcelMarketId("Asheville")).toBe(true);
    expect(isOtherMarketId("Asheville")).toBe(false);
    expect(isPrimaryMarket("Asheville")).toBe(false);
    const summary = catalogForMarket({} as RuralMarketsCatalog, {} as EligibleMarketsCatalog, {} as EligibleMarketsCatalog, "Asheville");
    expect(summary.rowCount).toBe(0);
    expect(summary.ruralCount).toBe(0);
    expect(summary.urbanCount).toBe(0);
    expect(summary.counties).toEqual([
      { county: "Buncombe", state: "North Carolina", count: 0, outerEdge: false },
      { county: "Henderson", state: "North Carolina", count: 0, outerEdge: false },
    ]);
  });
});

describe("Buncombe 5–150 acre extract", () => {
  const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37021/county.json");
  const statsPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37021/join-stats.json");

  it("keeps the county Property acreage band and does not invent opportunity zones", () => {
    expect(existsSync(countyPath)).toBe(true);
    expect(existsSync(statsPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      featureCount: number;
      coverage: string;
      source: string;
      minAcres: number;
      maxAcres: number;
    };
    expect(county.fips).toBe("37021");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("nc-buncombe-opendata-37021");
    expect(county.minAcres).toBe(5);
    expect(county.maxAcres).toBe(150);
    expect(county.featureCount).toBeGreaterThan(10000);
    const stats = JSON.parse(readFileSync(statsPath, "utf8")) as {
      kept: number;
      sale: { trusted: number; nulledUntrusted: number };
      byCity: Record<string, { parcels: number; zoning: number; flu: number; zoningGap?: string }>;
    };
    expect(stats.kept).toBe(county.featureCount);
    expect(stats.byCity["Biltmore Forest"].zoning).toBe(0);
    expect(stats.byCity["Biltmore Forest"].zoningGap).toBe("pdf-only");
    expect(stats.byCity.Asheville.parcels).toBeGreaterThan(0);
    expect(stats.sale.nulledUntrusted).toBeGreaterThan(stats.sale.trusted);
    const tiles = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37021/tiles");
    const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"));
    expect(file).toBeTruthy();
    const collection = JSON.parse(readFileSync(path.join(tiles, file!), "utf8")) as ParcelCollection;
    expect(collection.features.length).toBeGreaterThan(0);
    for (const feature of collection.features.slice(0, 40)) {
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.countyFips).toBe("37021");
      expect(feature.properties.marketIds).toEqual(["Asheville"]);
      expect(feature.properties.opportunityZone).toBeNull();
      expect(feature.properties.oz2Eligibility).toBeNull();
      expect(feature.properties.appraiserUrl).toContain("prc-buncombe.spatialest.com/#/property/");
      expect(feature.properties.appraiserUrl).toContain(feature.properties.parcelId);
    }
  });
});
