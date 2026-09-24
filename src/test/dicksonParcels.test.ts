import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY_DIR = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47043");

const GAP_TOWNS = new Set(["Burns", "Charlotte", "Vanleer", "Slayden"]);

type IngestJurisdiction = { parcels: number; zoningJoined: number };

type DicksonCounty = {
  fips: string;
  featureCount: number;
  source: string;
  sourceCount: number;
  gaps: string[];
  ingest: {
    impactCountyId: number;
    jur: string;
    geoidFips: string;
    parcelType: number;
    kept: number;
    themesMatched: number;
    ownerCount: number;
    situsCount: number;
    mailingCount: number;
    saleCount: number;
    appraisalCount: number;
    zoningJoined: number;
    fluJoined: number;
    opportunityZoneDesignated: number;
    assessedValueInvented: boolean;
    jurisdictions: Record<string, IngestJurisdiction>;
    camaZoningNonBlankIgnored: number;
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

  it("uses Comptroller county 22 and FIPS 47043, not the FIPS suffix", () => {
    expect(county.fips).toBe("47043");
    expect(county.source).toBe("tn-impact-47043");
    expect(county.ingest.impactCountyId).toBe(22);
    expect(county.ingest.jur).toBe("022");
    expect(county.ingest.geoidFips).toBe("47043");
    expect(county.ingest.parcelType).toBe(1);
    expect(county.ingest.assessedValueInvented).toBe(false);
    expect(county.ingest.fluJoined).toBe(0);
    expect(county.ingest.opportunityZoneDesignated).toBe(0);
    expect(county.gaps.join(" ")).toMatch(/Burns/);
    expect(county.gaps.join(" ")).toMatch(/future-land-use/i);
    expect(county.gaps.join(" ")).toMatch(/COUNTY_ID=22/);
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

  it("matches published owner, sale, and zoning join counts", () => {
    const prefixes: Record<string, IngestJurisdiction> = {};
    let owners = 0;
    let situs = 0;
    let mailing = 0;
    let sales = 0;
    let appraisals = 0;
    let zoned = 0;
    for (const feature of features) {
      const props = feature.properties;
      if (props.ownerName) owners += 1;
      if (props.situsAddress) situs += 1;
      if (props.mailingAddress.line1 || props.mailingAddress.city) mailing += 1;
      if (props.lastSale.date || props.lastSale.price) sales += 1;
      if (props.tax.marketValue) appraisals += 1;
      if (props.zoningCode) zoned += 1;
      const prefix = props.jurisdictionPrefix || "missing";
      const bucket = prefixes[prefix] ?? { parcels: 0, zoningJoined: 0 };
      bucket.parcels += 1;
      if (props.zoningCode) bucket.zoningJoined += 1;
      prefixes[prefix] = bucket;
    }
    expect(owners).toBe(county.ingest.ownerCount);
    expect(situs).toBe(county.ingest.situsCount);
    expect(mailing).toBe(county.ingest.mailingCount);
    expect(sales).toBe(county.ingest.saleCount);
    expect(appraisals).toBe(county.ingest.appraisalCount);
    expect(zoned).toBe(county.ingest.zoningJoined);
    expect(Object.keys(prefixes).sort()).toEqual(Object.keys(county.ingest.jurisdictions).sort());
    for (const [name, bucket] of Object.entries(county.ingest.jurisdictions)) {
      expect(prefixes[name]).toEqual({ parcels: bucket.parcels, zoningJoined: bucket.zoningJoined });
    }
    expect(county.ingest.themesMatched).toBeGreaterThan(features.length * 0.9);
    expect(zoned).toBeGreaterThan(0);
    expect(prefixes["Dickson County"]?.parcels ?? 0).toBeGreaterThan(0);
    expect(county.ingest.camaZoningNonBlankIgnored).toBeGreaterThanOrEqual(0);
  });
});
