import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadFluConfig, loadZoningConfig } from "../lib/data/loadFixtures";
import { fluAllowsMultifamily } from "../lib/flu";
import { formatParcelPlace, parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";
import { zoningAllowsMultifamily } from "../lib/zoning";

const COUNTY_DIR = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13067");

describe("Cobb County place line and assessor link", () => {
  it("names Georgia and the Cobb assessor, not Orange County", () => {
    expect(formatParcelPlace({ countyName: "Cobb", state: "Georgia", situsCity: null, situsZip: null })).toBe(
      "Cobb County, Georgia",
    );
    expect(formatParcelPlace({ countyName: "Orange", state: "Florida", situsCity: null, situsZip: null })).toBe(
      "Orange County, FL",
    );
    expect(formatParcelPlace({ situsCity: "Marietta", situsZip: "30060", countyName: "Cobb", state: "Georgia" })).toBe(
      "Marietta 30060",
    );
    const link = parcelAppraiserUrl({ parcelId: "16004500010", countyFips: "13067" });
    expect(link.href).toBe("https://www.cobbcounty.gov/tax-assessor");
    expect(link.label).toContain("Cobb");
    expect(link.href).not.toContain("ocpa");
    expect(link.href).not.toContain("cob.org");
  });

  it("does not score Cobb zoning or FLU as Orange County multifamily", async () => {
    const zoning = await loadZoningConfig();
    const flu = await loadFluConfig();
    expect(zoningAllowsMultifamily("PD", "Unincorporated Cobb:PD", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("R-20", "Mableton:R-20", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("PUD", "Smyrna:PUD", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("PD", "PD", zoning, true, true)).toBe(true);
    expect(
      fluAllowsMultifamily(
        { code: "NAC", label: "Neighborhood Activity Center", jurisdiction: "Smyrna", source: "smyrna-ga-flu-2040" },
        flu,
      ),
    ).toBeNull();
    expect(fluAllowsMultifamily({ code: "NAC", label: "NAC", jurisdiction: "ORG", source: "org" }, flu)).toBe(true);
  });
});

describe("Cobb County 5–150 acre extract", () => {
  it("uses Tax Assessors Daily, joins cities, and keeps eligible separate from designated", async () => {
    const countyPath = path.join(COUNTY_DIR, "county.json");
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      coverage: string;
      featureCount: number;
      source: string;
      queryUrl: string;
      sourceCount: number;
      gaps: string[];
    };
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(4500);
    expect(county.featureCount).toBeLessThan(5200);
    expect(county.sourceCount).toBeGreaterThanOrEqual(county.featureCount);
    expect(county.source).toBe("ga-cobb-taxassessorsdaily");
    expect(county.queryUrl).toContain("gis.cobbcounty.gov");
    expect(county.queryUrl).toContain("taxassessorsdaily/MapServer/0");
    expect(county.queryUrl).not.toContain("cobbcounty.org");
    expect(county.queryUrl).not.toContain("cob.org");

    const gaps = county.gaps.join("\n");
    expect(gaps).toMatch(/CobbZoningData/);
    expect(gaps).toMatch(/Future_Land_Use/);
    expect(gaps).toMatch(/ParcelSales/);
    expect(gaps).toMatch(/STEB=FMV/);
    expect(gaps).toMatch(/Mableton zoning stays blank/);
    expect(gaps).toMatch(/Marietta/);
    expect(gaps).toMatch(/Smyrna/);
    expect(gaps).toMatch(/Kennesaw/);
    expect(gaps).toMatch(/Powder Springs/);
    expect(gaps).toMatch(/Acworth/);
    expect(gaps).toMatch(/Austell/);
    expect(gaps).toMatch(/Smyrna, Tennessee/);
    expect(gaps).toMatch(/Boulder/);
    expect(gaps).toMatch(/cob\.org/);
    expect(gaps).toMatch(/Sampson/);
    expect(gaps).toMatch(/Orange County, Virginia/);
    expect(gaps).toMatch(/Athens-Clarke/);
    expect(gaps).toMatch(/not designated/i);
    expect(gaps).not.toMatch(/Smyrna, Tennessee was used/);
    expect(gaps).not.toMatch(/was not joined:/);
    expect(gaps).toMatch(/matched zoning 361/);
    expect(gaps).toMatch(/Smyrna, Georgia Zoning_Overlay/);
    expect(gaps).toMatch(/Kennesaw Zoning_Polygons/);
    expect(gaps).toMatch(/Powder Springs Zoning/);

    const zoning = await loadZoningConfig();
    const flu = await loadFluConfig();
    const tilesDir = path.join(COUNTY_DIR, "tiles");
    const files = readdirSync(tilesDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);

    let checked = 0;
    let seenOwner = false;
    let seenTax = false;
    let seenMail = false;
    let seenUse = false;
    let seenSale = 0;
    let zoningCount = 0;
    let fluCount = 0;
    const cities = new Set<string>();
    const gapCities = new Set<string>();
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tilesDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("13067");
        expect(props.state).toBe("Georgia");
        expect(props.countyName).toBe("Cobb");
        expect(props.source).toBe("ga-cobb-taxassessorsdaily");
        expect(props.marketIds).toContain("Atlanta");
        expect(props.opportunityZone).toBeNull();
        expect(props.oz2Eligibility).toBeNull();
        expect(props.appraiserUrl).toContain("cobbcounty.gov");
        expect(props.appraiserUrl).not.toContain("ocpa");
        const [lon, lat] = props.centroid;
        expect(lon).toBeGreaterThan(-84.8);
        expect(lon).toBeLessThan(-84.32);
        expect(lat).toBeGreaterThan(33.7);
        expect(lat).toBeLessThan(34.15);
        if (props.ownerName) seenOwner = true;
        if (props.tax.marketValue != null && props.tax.marketValue > 0 && props.tax.assessedValue != null) seenTax = true;
        if (props.mailingAddress.line1 && props.mailingAddress.city && props.mailingAddress.zip) seenMail = true;
        if (props.dorCode) seenUse = true;
        if (props.lastSale.qualified != null) {
          expect(props.lastSale.qualified).toBe("FMV");
          expect(props.lastSale.price).toBeGreaterThan(0);
          expect(props.lastSale.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
          seenSale += 1;
        } else {
          expect(props.lastSale.price).toBeNull();
        }
        expect(zoningAllowsMultifamily(props.zoningCode, props.zoningDistrict, zoning, true, true)).toBe(false);
        expect(fluAllowsMultifamily(props.flu, flu)).toBeNull();
        if (props.zoningCode) {
          zoningCount += 1;
          expect(props.zoningDistrict).toBe(`${props.jurisdictionCode}:${props.zoningCode}`);
          expect(props.zoningDistrict?.includes(":")).toBe(true);
        }
        if (props.flu?.code) {
          fluCount += 1;
          expect(props.flu.jurisdiction).toBeTruthy();
          expect(props.flu.jurisdiction).not.toBe("ORG");
          expect(props.flu.jurisdiction).not.toBe("ORL");
        }
        const city = props.situsCity || props.jurisdictionCode;
        if (city === "Acworth" || city === "Austell" || city === "Mableton") {
          expect(props.zoningCode).toBeNull();
          expect(props.flu).toBeNull();
          gapCities.add(city);
        } else if (props.jurisdictionCode) {
          cities.add(props.jurisdictionCode);
        }
        checked += 1;
      }
    }
    expect(checked).toBe(county.featureCount);
    expect(seenOwner).toBe(true);
    expect(seenTax).toBe(true);
    expect(seenMail).toBe(true);
    expect(seenUse).toBe(true);
    expect(seenSale).toBeGreaterThan(500);
    expect(zoningCount).toBeGreaterThan(500);
    expect(fluCount).toBeGreaterThan(300);
    expect(zoningCount).toBeLessThan(checked);
    expect(cities.has("Unincorporated Cobb")).toBe(true);
    expect(cities.has("Mableton") || gaps.includes("Mableton")).toBe(true);
    for (const city of ["Marietta", "Smyrna", "Kennesaw", "Powder Springs"]) {
      expect(cities.has(city) || gapCities.has(city)).toBe(true);
    }
  });
});
