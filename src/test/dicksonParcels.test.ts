import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY_DIR = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47043");

const GAP_TOWNS = new Set(["Burns", "Charlotte", "Vanleer", "Slayden"]);

type DicksonCounty = {
  fips: string;
  featureCount: number;
  source: string;
  queryUrl: string;
  sourceCount: number;
  gaps: string[];
  ingest: {
    kept: number;
    ownerCount: number;
    saleCount: number;
    appraisalCount: number;
    tncpmLayer: number;
    opportunityZoneDesignated: number;
    simplified: boolean;
  };
};

function loadFeatures(): ParcelFeature[] {
  const tiles = path.join(COUNTY_DIR, "tiles");
  return readdirSync(tiles)
    .filter((name) => name.endsWith(".geojson"))
    .flatMap((name) => {
      const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
      return collection.features;
    });
}

describe("Dickson County TN parcel extract", () => {
  const county = JSON.parse(readFileSync(path.join(COUNTY_DIR, "county.json"), "utf8")) as DicksonCounty;
  const features = loadFeatures();
  const lookup = JSON.parse(readFileSync(path.join(COUNTY_DIR, "lookup.json"), "utf8")) as Record<string, string>;

  it("uses OIR geometry for FIPS 47043 and Comptroller GISLINK 022, not the FIPS suffix", () => {
    expect(county.fips).toBe("47043");
    expect(county.source).toBe("tn-oir-public-use-47043");
    expect(county.queryUrl).toContain("Tennessee_Property_Boundaries_Public_Use");
    expect(county.queryUrl).not.toContain("April2023Parcels");
    expect(county.ingest.tncpmLayer).toBe(64);
    expect(county.ingest.simplified).toBe(false);
    expect(county.ingest.opportunityZoneDesignated).toBe(0);
    expect(county.gaps.join(" ")).toMatch(/2023/);
    expect(county.gaps.join(" ")).toMatch(/future land use/i);
    expect(county.gaps.join(" ")).toMatch(/Regrid/);
  });

  it("keeps the inclusive 5–150 acre band and replaces the COUNTY_ID=43 extract", () => {
    expect(features.length).toBe(county.featureCount);
    expect(features.length).toBe(county.ingest.kept);
    expect(Object.keys(lookup)).toHaveLength(features.length);
    expect(features.length).toBeGreaterThan(7000);
    for (const feature of features) {
      const props = feature.properties;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.countyFips).toBe("47043");
      expect(props.countyName).toBe("Dickson");
      expect(props.state).toBe("Tennessee");
      expect(props.marketIds).toEqual(["Nashville"]);
      expect(props.parcelId.startsWith("022")).toBe(true);
      expect(props.parcelId.startsWith("043")).toBe(false);
      expect(props.id).toBe(`47043:${props.parcelId}`);
      expect(lookup[props.parcelId]).toBeTruthy();
      expect(props.flu).toBeNull();
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-87.9);
      expect(lon).toBeLessThan(-87.0);
      expect(lat).toBeGreaterThan(35.8);
      expect(lat).toBeLessThan(36.5);
      if (props.zoningCode) {
        expect(props.zoningCode).toMatch(/^[A-Za-z0-9][A-Za-z0-9 \-/]{0,24}$/);
      }
      if (GAP_TOWNS.has(props.jurisdictionPrefix || "")) {
        expect(props.zoningCode).toBeNull();
      }
    }
  });

  it("matches published owner, situs, and 2023 sale counts", () => {
    let owners = 0;
    let situs = 0;
    let sales = 0;
    let appraisals = 0;
    let vintageSales = 0;
    let zoned = 0;
    for (const feature of features) {
      const props = feature.properties;
      if (props.ownerName) owners += 1;
      if (props.situsAddress) situs += 1;
      if (props.lastSale.date || props.lastSale.price) {
        sales += 1;
        if (props.lastSale.vintage === "2023") vintageSales += 1;
      }
      if (props.tax.marketValue) {
        appraisals += 1;
        expect(props.tax.vintage).toBe("2023");
      }
      if (props.zoningCode) zoned += 1;
      expect(props.tax.assessedValue).toBeNull();
    }
    expect(owners).toBe(county.ingest.ownerCount);
    expect(situs).toBe(features.length);
    expect(sales).toBe(county.ingest.saleCount);
    expect(vintageSales).toBe(sales);
    expect(appraisals).toBe(county.ingest.appraisalCount);
    expect(zoned).toBe(0);
    expect(owners).toBeGreaterThan(features.length * 0.9);
  });
});
