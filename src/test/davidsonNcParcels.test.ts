import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl, parcelPlaceLine } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY_PATH = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37057/county.json");
const TN_PATH = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47037/county.json");
const TILE_DIR = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37057/tiles");

const MUNICIPALITIES = new Set([
  "Lexington",
  "Thomasville",
  "Midway",
  "Denton",
  "Wallburg",
  "High Point",
  "Unincorporated",
]);

const CITY_CODES: Record<string, string> = {
  "07": "Lexington",
  "28": "Thomasville",
  "32": "Denton",
  "33": "Wallburg",
  "34": "Midway",
  "39": "High Point",
};

function loadDavidsonParcels(): ParcelFeature[] {
  const names = readdirSync(TILE_DIR).filter((name) => name.endsWith(".geojson"));
  const features: ParcelFeature[] = [];
  for (const name of names) {
    const collection = JSON.parse(readFileSync(path.join(TILE_DIR, name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

describe("Davidson County, North Carolina place and tax links", () => {
  it("does not label Davidson NC as Florida or send it to the Orange appraiser", () => {
    expect(
      parcelPlaceLine({
        situsCity: "Lexington",
        countyName: "Davidson",
        state: "North Carolina",
      }),
    ).toBe("Lexington · Davidson County, NC");
    expect(
      parcelPlaceLine({
        situsCity: "Unincorporated",
        countyName: "Davidson",
        state: "North Carolina",
      }),
    ).toBe("Unincorporated · Davidson County, NC");
    expect(parcelPlaceLine({ countyName: "Davidson", state: "Tennessee" })).toBe("Davidson County, TN");
    expect(parcelPlaceLine({ situsCity: "ORLANDO", situsZip: "32801", countyName: "Orange", state: "Florida" })).toBe(
      "ORLANDO 32801",
    );
    expect(parcelPlaceLine({ countyName: "Orange", state: "Florida" })).toBe("Orange County, FL");
    const link = parcelAppraiserUrl({ parcelId: "6843-04-80-0128", countyFips: "37057" });
    expect(link.href).toBe("https://taxsearch.co.davidson.nc.us/RealEstateSearch");
    expect(link.label).toMatch(/North Carolina/);
    expect(link.href).not.toMatch(/ocpafl/);
  });
});

describe("Davidson County NC 5–150 acre extract", () => {
  const row = JSON.parse(readFileSync(COUNTY_PATH, "utf8")) as {
    fips: string;
    state: string;
    name: string;
    source: string;
    coverage: string;
    featureCount: number;
    markets: string[];
    gaps: string[];
    minAcres: number;
    maxAcres: number;
  };
  const tennessee = JSON.parse(readFileSync(TN_PATH, "utf8")) as { fips: string; state: string; source: string };
  const features = loadDavidsonParcels();

  it("is North Carolina FIPS 37057 from the county roll, not Tennessee or OneMap", () => {
    expect(row.fips).toBe("37057");
    expect(row.name).toBe("Davidson");
    expect(row.state).toBe("North Carolina");
    expect(row.source).toBe("nc-davidson-opengov-37057");
    expect(row.coverage).toBe("complete-gte-5ac");
    expect(row.minAcres).toBe(5);
    expect(row.maxAcres).toBe(150);
    expect(row.featureCount).toBe(features.length);
    expect(row.featureCount).toBeGreaterThan(5000);
    expect(row.markets).toEqual(["Charlotte", "Winston-Salem"]);
    expect(row.gaps.join(" ")).toMatch(/not Davidson County, Tennessee/i);
    expect(row.gaps.join(" ")).toMatch(/not a designated/i);
    expect(tennessee.fips).toBe("47037");
    expect(tennessee.state).toBe("Tennessee");
    expect(tennessee.source).toBe("tn-impact-47037");
  });

  it("keeps every parcel in band, in North Carolina, and in a known municipality", () => {
    const cities = new Set<string>();
    for (const feature of features) {
      const props = feature.properties;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.countyFips).toBe("37057");
      expect(props.state).toBe("North Carolina");
      expect(props.countyName).toBe("Davidson");
      expect(props.source).toBe("nc-davidson-opengov-37057");
      expect(props.marketIds).toEqual(["Charlotte", "Winston-Salem"]);
      expect(props.marketIds).not.toContain("Nashville");
      expect(props.situsCity && MUNICIPALITIES.has(props.situsCity)).toBe(true);
      expect(props.jurisdictionPrefix).toBe(props.situsCity);
      if (props.jurisdictionCode) {
        expect(CITY_CODES[props.jurisdictionCode]).toBe(props.situsCity);
      } else {
        expect(props.situsCity).toBe("Unincorporated");
      }
      expect(props.centroid[0]).toBeLessThan(-79.8);
      expect(props.centroid[0]).toBeGreaterThan(-80.75);
      expect(props.centroid[1]).toBeGreaterThan(35.3);
      expect(props.centroid[1]).toBeLessThan(36.2);
      expect(props.appraiserUrl).toBe("https://taxsearch.co.davidson.nc.us/RealEstateSearch");
      cities.add(props.situsCity || "");
    }
    expect(cities.has("Unincorporated")).toBe(true);
    expect(cities.has("Lexington")).toBe(true);
    expect(cities.has("Thomasville")).toBe(true);
    expect(cities.has("Wallburg")).toBe(true);
    expect(cities.has("Midway")).toBe(true);
    expect(cities.has("Denton")).toBe(true);
    expect(cities.has("High Point")).toBe(true);
  });

  it("does not treat OZ 2.0 eligibility as a designated Qualified Opportunity Zone", () => {
    let eligible = 0;
    let designated = 0;
    let eligibleNotDesignated = 0;
    let ruralEligible = 0;
    for (const feature of features) {
      const oz2 = feature.properties.oz2Eligibility;
      const oz = feature.properties.opportunityZone;
      expect(oz2?.designation === "eligible-for-nomination" || oz2?.designation === "not-eligible").toBe(true);
      expect(oz2?.source).toBe("rev-proc-2026-14");
      expect(oz?.source).not.toBe("rev-proc-2026-14");
      if (oz) expect(oz.source).toBe("hud-fs-13");
      if (oz2?.eligible) {
        eligible += 1;
        expect(oz2.designation).toBe("eligible-for-nomination");
        expect(oz2.tractGeoid?.startsWith("37057")).toBe(true);
        if (oz?.inOpportunityZone !== true) eligibleNotDesignated += 1;
      }
      if (oz?.inOpportunityZone) designated += 1;
      if (oz2?.tractGeoid === "37057061903") {
        ruralEligible += 1;
        expect(oz2.eligible).toBe(true);
        expect(oz2.rural).toBe(true);
        expect(oz2.designation).toBe("eligible-for-nomination");
        expect(oz?.inOpportunityZone).not.toBe(true);
      }
      if (oz2?.tractGeoid === "37057061400" && oz?.inOpportunityZone) {
        expect(oz2.eligible).toBe(true);
        expect(oz2.designation).toBe("eligible-for-nomination");
        expect(oz.source).toBe("hud-fs-13");
        expect(oz.tractGeoid).toBe("37057061400");
      }
      const fluJurisdiction = feature.properties.flu?.jurisdiction;
      if (fluJurisdiction) expect(fluJurisdiction).toBe("Wallburg");
      if (feature.properties.situsCity !== "Wallburg") {
        expect(feature.properties.flu).toBeNull();
      }
    }
    expect(eligible).toBeGreaterThan(0);
    expect(eligibleNotDesignated).toBeGreaterThan(0);
    expect(ruralEligible).toBeGreaterThan(0);
    expect(designated).toBeGreaterThanOrEqual(0);
  });
});
