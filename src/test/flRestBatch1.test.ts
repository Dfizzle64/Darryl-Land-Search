import { readFileSync, existsSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl, parcelIdLabel } from "../lib/format";
import {
  FL_REST_FIPS,
  GEOPLAN_LABEL,
  flRestAppraiserLink,
  flRestMarketAt,
  fluEmptyForFlRest,
  saleEmptyForFlRest,
  zoningEmptyForFlRest,
} from "../lib/flRestBatch1";
import { jurisdictionGisViewers } from "../lib/jurisdictionLinks";
import { OTHER_MARKETS } from "../lib/types";

const LIVE = ["12013", "12023", "12035", "12039", "12063", "12065", "12077", "12083", "12129", "12133"];
const PARTIAL = ["12029", "12037", "12045", "12047", "12059", "12067", "12079", "12121", "12123", "12125"];
const SEARCH_ONLY = ["12039", "12079", "12083"];

describe("FL-rest batch 1 registration", () => {
  it("keeps the acre band and does not reorder the earlier markets", () => {
    expect(FL_REST_FIPS).toHaveLength(20);
    expect(OTHER_MARKETS[0]).toBe("South Florida");
    expect(OTHER_MARKETS[6]).toBe("North-Central Florida");
    expect(OTHER_MARKETS[7]).toBe("Big Bend");
    expect(OTHER_MARKETS.at(-2)).toBe("North Florida");
    expect(OTHER_MARKETS.at(-1)).toBe("Panhandle Florida");
    expect(flRestMarketAt(-85.045, 30.443)).toBe("Panhandle Florida");
    expect(flRestMarketAt(-82.64, 30.19)).toBe("North Florida");
    expect(flRestMarketAt(-82.14, 29.19)).toBe("North-Central Florida");
    expect(flRestMarketAt(-84.28, 30.44)).toBe("Big Bend");
    expect(flRestMarketAt(-87.2, 30.42)).toBeNull();
  });

  it("puts the parcel id in the appraiser URL except the search-only pages", () => {
    const wakulla = parcelAppraiserUrl({ parcelId: "12-5S-03W-063-00808-000", countyFips: "12129" });
    expect(wakulla.href).toContain("KeyValue=12-5S-03W-063-00808-000");
    expect(parcelAppraiserUrl({ parcelId: "26-5S-17-09398-000", countyFips: "12023" }).href).toContain("ParcelNo=26-5S-17-09398-000");
    expect(parcelIdLabel("12023")).toBe("Parcel Number");
    expect(parcelIdLabel("12035")).toBe("Parcel Number");
    expect(parcelIdLabel("12125")).toBe("PIN");
    for (const fips of SEARCH_ONLY) {
      const link = flRestAppraiserLink(fips, "SHOULD-NOT-APPEAR");
      expect(link?.href).not.toContain("SHOULD-NOT-APPEAR");
      expect(link?.href).not.toContain("KeyValue=");
    }
    expect(parcelAppraiserUrl({ parcelId: "34801-001-00", countyFips: "12083" }).href).toBe(
      "https://www.pa.marion.fl.us/PropertySearch.aspx",
    );
  });

  it("uses the card GIS viewer and honest empty states", () => {
    const columbia = jurisdictionGisViewers({
      countyFips: "12023",
      gisViewerUrl: "https://gis.columbiacountyfla.com/hosting/rest/services/Parcels_and_Addresses/MapServer/2",
    });
    expect(columbia?.primary.href).toBe("https://columbia.floridapa.com/gis/");
    expect(columbia?.alt?.href).toBe("https://search.ccpafl.com/map/");
    expect(jurisdictionGisViewers({ countyFips: "12065" })?.primary.href).not.toMatch(/MapServer|FeatureServer/);
    expect(zoningEmptyForFlRest("12029", "fallback")).toBe(GEOPLAN_LABEL);
    expect(fluEmptyForFlRest("12079", "fallback")).toBe(GEOPLAN_LABEL);
    expect(fluEmptyForFlRest("12123", "fallback")).toBe(GEOPLAN_LABEL);
    expect(zoningEmptyForFlRest("12039", "fallback")).toMatch(/land-use district/);
    expect(zoningEmptyForFlRest("12045", "fallback")).toMatch(/No queryable Gulf/);
    expect(saleEmptyForFlRest("12065")).toMatch(/FDOR roll year/);
    expect(zoningEmptyForFlRest("12086", "fallback")).toBe("fallback");
    expect(saleEmptyForFlRest("12011")).toBeNull();
  });

  it("loads each county extract inside 5.0–150.0 acres", () => {
    const index = JSON.parse(readFileSync("data/fixtures/market-parcels/index.json", "utf8")) as {
      markets: Record<string, { counties: { fips: string; coverage: string; featureCount: number }[] }>;
    };
    expect(index.markets["North Florida"].counties.map((row) => row.fips).sort()).toEqual(
      ["12023", "12035", "12047", "12067", "12121", "12125"].sort(),
    );
    expect(index.markets["Panhandle Florida"].counties.map((row) => row.fips).sort()).toEqual(
      ["12013", "12037", "12045", "12059", "12063", "12077", "12133"].sort(),
    );
    const indexed = [
      ...index.markets["North Florida"].counties,
      ...index.markets["Panhandle Florida"].counties,
      ...index.markets["Big Bend"].counties,
      ...index.markets["North-Central Florida"].counties,
    ];
    for (const fips of FL_REST_FIPS) {
      const path = `data/fixtures/market-parcels/counties/${fips}/county.json`;
      expect(existsSync(path)).toBe(true);
      const county = JSON.parse(readFileSync(path, "utf8")) as {
        fips: string;
        coverage: string;
        featureCount: number;
        minAcres: number;
        maxAcres: number;
        markets: string[];
        source: string;
        gaps: string[];
      };
      expect(county.fips).toBe(fips);
      expect(county.minAcres).toBe(5);
      expect(county.maxAcres).toBe(150);
      expect(county.featureCount).toBeGreaterThan(0);
      expect(county.coverage).toBe(PARTIAL.includes(fips) ? "partial" : "complete-gte-5ac");
      expect(LIVE.includes(fips)).toBe(county.coverage === "complete-gte-5ac");
      expect(county.markets.length).toBe(1);
      const row = indexed.find((item) => item.fips === fips);
      expect(row?.featureCount).toBe(county.featureCount);
      expect(row?.coverage).toBe(county.coverage);
      const joined = county.gaps.join(" ");
      expect(joined).not.toMatch(/Opportunity Zone|school grade|base flood/i);
      if (fips === "12039") expect(joined).toMatch(/swapped|FDOR owner/i);
      if (["12029", "12079", "12123"].includes(fips)) expect(joined).toContain(GEOPLAN_LABEL);
      const sampleTile = `data/fixtures/market-parcels/counties/${fips}/tiles`;
      expect(existsSync(sampleTile)).toBe(true);
    }
  });
});
