import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13013");
const CITY_STUBS = new Set(["WINDER", "AUBURN", "STATHAM", "BRASELTON", "BETHLEHEM", "CARL"]);

describe("Barrow County parcel extract", () => {
  it("ships the Project/1 landbase inside the inclusive 5–150 GIS-acre band", () => {
    const county = JSON.parse(readFileSync(path.join(COUNTY, "county.json"), "utf8")) as {
      fips: string;
      featureCount: number;
      coverage: string;
      source: string;
      queryUrl: string;
      gaps: string[];
      minAcres: number;
      maxAcres: number;
    };
    expect(county.fips).toBe("13013");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("ga-barrow-parcels");
    expect(county.featureCount).toBeGreaterThan(4000);
    expect(county.minAcres).toBe(5);
    expect(county.maxAcres).toBe(150);
    expect(county.queryUrl).toContain("BarrowParcelswOwner_Project/FeatureServer/1");
    expect(county.queryUrl).not.toContain("HfsHDBmkGwb1UtID");
    expect(county.queryUrl).not.toContain("LandPro");
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/GIS area/);
    expect(gaps).toMatch(/qPublic/);
    expect(gaps).toMatch(/Winder/);
    expect(gaps).toMatch(/Auburn/);
    expect(gaps).toMatch(/Norwalk/);

    const lookup = JSON.parse(readFileSync(path.join(COUNTY, "lookup.json"), "utf8")) as Record<string, string>;
    const tiles = readdirSync(path.join(COUNTY, "tiles")).filter((name) => name.endsWith(".geojson"));
    expect(tiles.length).toBeGreaterThan(0);
    let count = 0;
    let withZoning = 0;
    let withFlu = 0;
    let withSitus = 0;
    let cityFlu = 0;
    for (const tile of tiles) {
      const collection = JSON.parse(readFileSync(path.join(COUNTY, "tiles", tile), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        count += 1;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("13013");
        expect(props.id.startsWith("13013:")).toBe(true);
        expect(props.marketIds).toEqual(["Atlanta"]);
        expect(props.source).toBe("ga-barrow-parcels");
        expect(props.opportunityZone).toBeNull();
        expect(props.oz2Eligibility).toBeNull();
        expect(props.tax.marketValue).toBeNull();
        expect(props.tax.assessedValue).toBeNull();
        expect(props.tax.taxableValue).toBeNull();
        expect(props.lastSale.price).toBeNull();
        expect(props.lastSale.date).toBeNull();
        expect(props.appraiserUrl ?? "").toContain("App=BarrowCountyGA");
        expect(props.appraiserUrl ?? "").toContain("KeyValue=");
        const zone = props.zoningCode?.toUpperCase();
        if (zone) {
          expect(CITY_STUBS.has(zone)).toBe(false);
          withZoning += 1;
        }
        if (props.flu?.code) withFlu += 1;
        if (props.flu?.source && props.flu.source !== "barrow-flu2023") cityFlu += 1;
        if (props.situsAddress) withSitus += 1;
        const [lon, lat] = props.centroid;
        expect(lon).toBeGreaterThan(-84.05);
        expect(lon).toBeLessThan(-83.4);
        expect(lat).toBeGreaterThan(33.8);
        expect(lat).toBeLessThan(34.25);
        expect(lookup[props.parcelId]).toBe(tile.replace(".geojson", ""));
      }
    }
    expect(count).toBe(county.featureCount);
    expect(Object.keys(lookup)).toHaveLength(count);
    expect(withZoning).toBeGreaterThan(1000);
    expect(withFlu).toBeGreaterThan(1000);
    expect(withSitus).toBeGreaterThan(100);
    expect(cityFlu).toBeGreaterThan(0);
  });
});
