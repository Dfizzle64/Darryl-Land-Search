import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13015");

function loadFeatures(): ParcelFeature[] {
  const tiles = path.join(COUNTY, "tiles");
  return readdirSync(tiles)
    .filter((name) => name.endsWith(".geojson"))
    .flatMap((name) => {
      const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
      return collection.features;
    });
}

describe("Bartow County parcel extract", () => {
  it("dissolves the 5–150 acre BartowLand roll and records the public gaps", () => {
    const county = JSON.parse(readFileSync(path.join(COUNTY, "county.json"), "utf8"));
    const lookup = JSON.parse(readFileSync(path.join(COUNTY, "lookup.json"), "utf8")) as Record<string, string>;
    const features = loadFeatures();
    const gaps = (county.gaps as string[]).join("\n");

    expect(county.fips).toBe("13015");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("ga-bartow-land");
    expect(county.featureCount).toBe(features.length);
    expect(county.featureCount).toBe(Object.keys(lookup).length);
    expect(county.featureCount).toBe(7077);
    expect(county.sourceCount).toBe(13412);
    expect(county.zoningJoined).toBe(6352);
    expect(county.zoningCityStub).toBe(713);
    expect(county.zoningMissed).toBe(12);
    expect(county.distinctPartParcels).toBe(70);
    expect(gaps).toMatch(/dissolved to/);
    expect(gaps).toMatch(/County zoning join:/);
    expect(gaps).toMatch(/Incorporated/);
    expect(gaps).toMatch(/qPublic AppID=791/);
    expect(gaps).toMatch(/FLU gap/);
    expect(gaps).toMatch(/LandPro_2012/);
    expect(gaps).toMatch(/City of Bartow, Florida/);
    expect(gaps).toMatch(/ParcelInfo\/11/);
    expect(gaps).toMatch(/Eligible is not designated/);
    expect(county.zoningJoined).toBeGreaterThan(0);
    expect(county.zoningJoined + county.zoningCityStub + county.zoningMissed).toBe(county.featureCount);

    const ids = new Set<string>();
    for (const feature of features) {
      const props = feature.properties;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.countyFips).toBe("13015");
      expect(props.marketIds).toEqual(["Atlanta"]);
      expect(props.source).toBe("ga-bartow-land");
      expect(props.lastSale).toEqual({ date: null, price: null, qualified: null });
      expect(props.flu).toBeNull();
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.zoningCode?.toLowerCase()).not.toBe("incorporated");
      const [lon, lat] = props.centroid;
      expect(lon).toBeLessThan(-84.5);
      expect(lon).toBeGreaterThan(-85.2);
      expect(lat).toBeGreaterThan(34);
      expect(lat).toBeLessThan(34.5);
      expect(ids.has(props.parcelId)).toBe(false);
      ids.add(props.parcelId);
      expect(lookup[props.parcelId]).toBeTruthy();
    }

    const wayside = features.find((feature) => feature.properties.parcelId === "0002-0059-002");
    expect(wayside?.properties.acreage).toBe(10.23);
    expect(wayside?.properties.situsAddress).toBe("3745 WAYSIDE RD");
    expect(wayside?.properties.situsZip).toBe("30103");
    expect(wayside?.properties.situsCity).toBe("Bartow County");
    expect(wayside?.properties.ownerName).toContain("TERRY");
    expect(wayside?.properties.mailingAddress.city).toBe("ADAIRSVILLE");
    expect(wayside?.properties.tax.marketValue).toBe(534532);
    expect(wayside?.properties.zoningCode).toBe("A-1");
  });
});
