import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { inMarketAcreageBand, type MarketParcelIndex } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

describe("Spalding County GA parcels", () => {
  it("ingests Spalding County on public GIS acres and leaves Griffin, FLU, sales, and tax empty", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13255/county.json");
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      markets: string[];
      featureCount: number;
      coverage: string;
      source: string;
      queryUrl: string;
      gaps: string[];
      lookup: string;
      path: string;
    };
    expect(county.fips).toBe("13255");
    expect(county.markets).toEqual(["Atlanta"]);
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("ga-spalding-parcels-public");
    expect(county.queryUrl).toContain("Parcels_Public_View/FeatureServer/1");
    expect(county.featureCount).toBe(3832);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/Griffin/);
    expect(gaps).toMatch(/FLU is null/);
    expect(gaps).toMatch(/qPublic AppID=766/);
    expect(gaps).toMatch(/Sunny Side/);
    expect(gaps).toMatch(/Regrid/);
    expect(gaps).toMatch(/LandPro/);
    expect(gaps).toMatch(/3624 JURISDICTION=COUNTY/);
    expect(gaps).toMatch(/199 Griffin CITY/);

    const lookup = JSON.parse(readFileSync(path.join(process.cwd(), county.lookup), "utf8")) as Record<string, string>;
    expect(Object.keys(lookup)).toHaveLength(county.featureCount);

    const tilesDir = path.join(process.cwd(), county.path);
    let count = 0;
    let zoned = 0;
    const byId = new Map<string, ParcelCollection["features"][number]>();
    for (const file of readdirSync(tilesDir)) {
      if (!file.endsWith(".geojson")) continue;
      const collection = JSON.parse(readFileSync(path.join(tilesDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        count += 1;
        const props = feature.properties;
        expect(props.countyFips).toBe("13255");
        expect(props.id.startsWith("13255:")).toBe(true);
        expect(feature.id).toBe(props.id);
        expect(props.marketIds).toEqual(["Atlanta"]);
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.flu).toBeNull();
        expect(props.opportunityZone).toBeNull();
        expect(props.oz2Eligibility).toBeNull();
        expect(props.ownerName).toBeNull();
        expect(props.situsAddress).toBeNull();
        expect(props.situsCity).toBeNull();
        expect(props.lastSale).toEqual({ date: null, price: null, qualified: null });
        expect(props.tax.marketValue).toBeNull();
        expect(props.tax.assessedValue).toBeNull();
        expect(props.tax.taxableValue).toBeNull();
        expect(JSON.stringify(props)).not.toMatch(/sunny side/i);
        const [lon, lat] = props.centroid;
        expect(lon).toBeGreaterThan(-84.55);
        expect(lon).toBeLessThan(-83.95);
        expect(lat).toBeGreaterThan(33.05);
        expect(lat).toBeLessThan(33.55);
        if (props.zoningCode) {
          zoned += 1;
          expect(props.zoningCode).toMatch(/^[A-Z0-9]+$/);
          expect(props.zoningDistrict).toBeNull();
        }
        byId.set(props.parcelId, feature);
      }
    }
    expect(count).toBe(county.featureCount);
    expect(zoned).toBeGreaterThan(1000);
    expect(count - zoned).toBeGreaterThanOrEqual(50);

    const countyPin = byId.get("244 02001B");
    expect(countyPin?.properties.zoningCode).toBe("PRRRD");
    expect(countyPin?.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(countyPin?.properties.centroid[0]).toBeGreaterThan(-84.28);
    expect(countyPin?.properties.centroid[0]).toBeLessThan(-84.23);
    expect(countyPin?.properties.centroid[1]).toBeGreaterThan(33.3);
    expect(countyPin?.properties.centroid[1]).toBeLessThan(33.35);
    for (const parcelId of ["001 01001", "039 01003", "039 01004"]) {
      expect(byId.get(parcelId)?.properties.zoningCode).toBeNull();
    }

    const indexPath = path.join(process.cwd(), "data/fixtures/market-parcels/index.json");
    const seeded = JSON.parse(readFileSync(indexPath, "utf8")) as MarketParcelIndex;
    const atlanta = seeded.markets.Atlanta;
    expect(atlanta.parcelCount).toBe(atlanta.counties.reduce((sum, item) => sum + item.featureCount, 0));
    const spalding = atlanta.counties.find((item) => item.fips === "13255");
    expect(spalding?.coverage).toBe("complete-gte-5ac");
    expect(spalding?.featureCount).toBe(county.featureCount);
  });
});
