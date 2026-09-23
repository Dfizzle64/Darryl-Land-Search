import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { formatJurisdiction, parcelAppraiserUrl, parcelPlaceLine, shelbyFluGap } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

describe("Shelby parcel display", () => {
  it("keeps Florida place lines and names Tennessee places", () => {
    expect(parcelPlaceLine({ situsCity: "Orlando", situsZip: "32801", countyName: "Orange", state: "Florida" })).toBe(
      "Orlando 32801",
    );
    expect(parcelPlaceLine({ countyName: "Orange", state: "Florida" })).toBe("Orange County, FL");
    expect(parcelPlaceLine({ situsCity: "Memphis", situsZip: "38103", countyName: "Shelby", state: "Tennessee" })).toBe(
      "Memphis 38103, Tennessee",
    );
    expect(parcelPlaceLine({ countyName: "Shelby", state: "Tennessee" })).toBe("Shelby County, Tennessee");
    expect(formatJurisdiction("MEMPHIS")).toBe("Memphis");
    expect(formatJurisdiction("UNINCORPORATED")).toBe("Unincorporated Shelby County");
    expect(shelbyFluGap("MEMPHIS")).toMatch(/Memphis 3\.0/);
    expect(shelbyFluGap("COLLIERVILLE")).toMatch(/City of Memphis only/);
    expect(shelbyFluGap("UNINCORPORATED")).not.toMatch(/Orlando/);
  });

  it("links Shelby parcels to the county assessor", () => {
    const linked = parcelAppraiserUrl({
      parcelId: "D0217   00225",
      countyFips: "47157",
      appraiserUrl: "https://www.assessormelvinburgess.com/propertyDetails?IR=true&parcelid=D0217%20%20%2000225",
    });
    expect(linked.href).toContain("assessormelvinburgess.com/propertyDetails");
    expect(linked.href).not.toContain("ocpafl.org");
    expect(linked.label).toContain("Shelby");
    const fallback = parcelAppraiserUrl({ parcelId: "D0217   00225", countyFips: "47157" });
    expect(fallback.href).toBe("https://www.assessormelvinburgess.com/PropertySearch");
  });
});

describe("Shelby County market parcels", () => {
  const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47157/county.json");

  it("ships a complete non-IMPACT extract with documented gaps", () => {
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      source: string;
      queryUrl: string;
      coverage: string;
      featureCount: number;
      gaps: string[];
    };
    expect(county.fips).toBe("47157");
    expect(county.source).toBe("tn-shelby-current-parcels");
    expect(county.queryUrl).toContain("scgis.shelbycountytn.gov");
    expect(county.queryUrl).not.toContain("IMPACT");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(1000);
    const gaps = county.gaps.join("\n");
    expect(gaps).toMatch(/not an IMPACT county/i);
    expect(gaps).toMatch(/tax values/i);
    expect(gaps).toMatch(/Token Required|no verified anonymous zoning/i);
    expect(gaps).toMatch(/Bartlett/);
    expect(gaps).toMatch(/Collierville/);
    expect(gaps).toMatch(/Germantown/);
    expect(gaps).toMatch(/Arlington/);
    expect(gaps).toMatch(/Lakeland/);
    expect(gaps).toMatch(/Millington/);
    expect(gaps).toMatch(/unincorporated/i);
    expect(gaps).toMatch(/equirectangular|4046\.8564224/);
    expect(gaps).toMatch(/UnsafeLegacyServerConnect|OP_LEGACY_SERVER_CONNECT/);
  });

  it("keeps Memphis future land use inside Memphis and acres inside the band", () => {
    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47157/tiles");
    const files = readdirSync(tileDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seen = 0;
    let memphis = 0;
    let memphisFlu = 0;
    let collierville = 0;
    let colliervilleZoned = 0;
    const munis = new Set<string>();
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tileDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("47157");
        expect(props.state).toBe("Tennessee");
        expect(props.source).toBe("tn-shelby-current-parcels");
        expect(props.marketIds).toContain("Memphis");
        expect(props.tax.marketValue).toBeNull();
        expect(props.tax.assessedValue).toBeNull();
        expect(props.appraiserUrl).toContain("assessormelvinburgess.com");
        const muni = props.jurisdictionCode;
        if (muni) munis.add(muni);
        if (props.flu) {
          expect(muni).toBe("MEMPHIS");
          expect(props.flu.jurisdiction).toBe("Memphis");
          expect(props.flu.code).toBeTruthy();
        }
        if (muni === "MEMPHIS") {
          memphis += 1;
          if (props.flu?.code) memphisFlu += 1;
        }
        if (muni === "COLLIERVILLE") {
          collierville += 1;
          if (props.zoningCode) colliervilleZoned += 1;
        }
        seen += 1;
      }
    }
    expect(seen).toBeGreaterThan(1000);
    expect(memphis).toBeGreaterThan(0);
    expect(memphisFlu).toBeGreaterThan(0);
    expect(collierville).toBeGreaterThan(0);
    expect(colliervilleZoned).toBeGreaterThan(0);
    expect(munis.has("MEMPHIS")).toBe(true);
    expect(munis.has("COLLIERVILLE")).toBe(true);
    expect(munis.has("UNINCORPORATED")).toBe(true);
    const sample = JSON.parse(readFileSync(path.join(tileDir, files[0]), "utf8")) as ParcelCollection;
    const feature = sample.features[0] as ParcelFeature;
    expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
  });
});
