import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadFluConfig, loadZoningConfig } from "../lib/data/loadFixtures";
import { fluAllowsMultifamily } from "../lib/flu";
import { formatParcelPlace, parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";
import { zoningAllowsMultifamily } from "../lib/zoning";

describe("Fulton place line and assessor link", () => {
  it("names Georgia and the Fulton assessor, not Orange County", () => {
    expect(formatParcelPlace({ countyName: "Fulton", state: "Georgia", situsCity: null, situsZip: null })).toBe(
      "Fulton County, Georgia",
    );
    expect(formatParcelPlace({ countyName: "Orange", state: "Florida", situsCity: null, situsZip: null })).toBe(
      "Orange County, FL",
    );
    expect(
      formatParcelPlace({ situsCity: "ATLANTA", situsZip: "30303", countyName: "Fulton", state: "Georgia" }),
    ).toBe("ATLANTA 30303");
    const link = parcelAppraiserUrl({ parcelId: "07 410001590187", countyFips: "13121" });
    expect(link.href).toBe("https://fultonassessor.org/");
    expect(link.label).toContain("Fulton");
    expect(link.href).not.toContain("ocpa");
  });

  it("does not score City of Atlanta zoning or FLU as Orange County multifamily", async () => {
    const zoning = await loadZoningConfig();
    const flu = await loadFluConfig();
    expect(zoningAllowsMultifamily("PD-H", "Atlanta:PD-H", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("RG-3", "Atlanta:RG-3", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("PD", "PD", zoning, true, true)).toBe(true);
    expect(
      fluAllowsMultifamily({ code: "HD", label: "High Density", jurisdiction: "ATL", source: "atl" }, flu),
    ).toBeNull();
    expect(fluAllowsMultifamily({ code: "HD", label: "HDR", jurisdiction: "ORG", source: "org" }, flu)).toBe(true);
  });
});

describe("Fulton County 5–150 acre extract", () => {
  it("uses Property Map Viewer MapServer/11 and keeps owner, tax, and city-only land use", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13121/county.json");
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      coverage: string;
      featureCount: number;
      source: string;
      queryUrl: string;
      gaps: string[];
    };
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(1000);
    expect(county.source).toBe("ga-fulton-pmv-mapserver-11");
    expect(county.queryUrl).toContain("PropertyMapViewer/MapServer/11");
    expect(county.queryUrl).not.toContain("CurrentParcels");
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/CurrentParcels/);
    expect(gaps).toMatch(/north-Fulton subset/);
    expect(gaps).toMatch(/Hapeville/);
    expect(gaps).toMatch(/Palmetto/);
    expect(gaps).toMatch(/Chattahoochee Hills/);
    expect(gaps).toMatch(/Mountain Park/);
    expect(gaps).toMatch(/Tyler_YearlySales/);

    const tilesDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13121/tiles");
    const files = readdirSync(tilesDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seenOwner = false;
    let seenTax = false;
    let seenMail = false;
    let seenUse = false;
    let seenSouth = false;
    let seenNorth = false;
    let seenFarNorth = false;
    const zoningCities = new Set<string>();
    const fluCities = new Set<string>();
    let zoning = 0;
    let flu = 0;
    let checked = 0;
    const cities = new Set([
      "Atlanta",
      "Sandy Springs",
      "Roswell",
      "Alpharetta",
      "Johns Creek",
      "Milton",
      "East Point",
      "College Park",
      "South Fulton",
      "Fairburn",
      "Union City",
    ]);
    const northside = new Set(["Sandy Springs", "Roswell", "Alpharetta", "Johns Creek", "Milton"]);
    const southside = new Set(["East Point", "College Park", "South Fulton", "Fairburn", "Union City"]);
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tilesDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("13121");
        expect(props.state).toBe("Georgia");
        expect(props.source).toBe("ga-fulton-pmv-mapserver-11");
        expect(props.marketIds).toContain("Atlanta");
        const lat = props.centroid[1];
        const lon = props.centroid[0];
        expect(lon).toBeGreaterThan(-85.05);
        expect(lon).toBeLessThan(-83.95);
        expect(lat).toBeGreaterThan(33.35);
        expect(lat).toBeLessThan(34.3);
        if (lat < 33.65) seenSouth = true;
        if (lat > 33.95) seenNorth = true;
        if (lat > 34.05) seenFarNorth = true;
        if (props.ownerName) seenOwner = true;
        if (props.tax.marketValue != null && props.tax.assessedValue != null) seenTax = true;
        if (props.mailingAddress.line1 && props.mailingAddress.zip) seenMail = true;
        if (props.dorCode) seenUse = true;
        if (props.zoningCode) {
          zoning += 1;
          expect(props.zoningDistrict?.endsWith(`:${props.zoningCode}`)).toBe(true);
          const city = props.zoningDistrict?.slice(0, -(props.zoningCode.length + 1));
          expect(city && cities.has(city)).toBe(true);
          if (city) zoningCities.add(city);
        }
        if (props.flu?.code) {
          flu += 1;
          expect(props.flu.jurisdiction && cities.has(props.flu.jurisdiction)).toBe(true);
          if (props.flu.jurisdiction) fluCities.add(props.flu.jurisdiction);
        }
        checked += 1;
      }
    }
    expect(checked).toBe(county.featureCount);
    expect(seenOwner).toBe(true);
    expect(seenTax).toBe(true);
    expect(seenMail).toBe(true);
    expect(seenUse).toBe(true);
    expect(seenSouth).toBe(true);
    expect(seenNorth).toBe(true);
    expect(seenFarNorth).toBe(true);
    expect(zoning).toBeGreaterThan(0);
    expect(flu).toBeGreaterThan(0);
    expect(zoning).toBeLessThan(checked);
    expect(flu).toBeLessThan(checked);
    expect(zoningCities.has("Atlanta")).toBe(true);
    expect([...zoningCities].some((city) => northside.has(city))).toBe(true);
    expect([...zoningCities].some((city) => southside.has(city))).toBe(true);
    expect(fluCities.has("Atlanta")).toBe(true);
    expect([...fluCities].some((city) => northside.has(city))).toBe(true);
    expect([...fluCities].some((city) => southside.has(city))).toBe(true);
  });
});
