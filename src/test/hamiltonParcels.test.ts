import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl, parcelPlaceLine } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47065/county.json");

describe("Hamilton County assessor links", () => {
  it("labels the county card separately from the search portal", () => {
    expect(
      parcelAppraiserUrl({
        parcelId: "002  001",
        countyFips: "47065",
        appraiserUrl: "https://assessor.hamiltontn.gov/card/002_001",
      }),
    ).toEqual({
      href: "https://assessor.hamiltontn.gov/card/002_001",
      label: "Open Hamilton County Assessor property card",
    });
    expect(parcelAppraiserUrl({ parcelId: "002  001", countyFips: "47065" })).toEqual({
      href: "https://assessor.hamiltontn.gov/search",
      label: "Open Hamilton County Assessor search",
    });
  });

  it("names the parcel state instead of assuming Florida", () => {
    expect(
      parcelPlaceLine({
        countyName: "Hamilton",
        state: "Tennessee",
        situsCity: null,
        situsZip: null,
      }),
    ).toBe("Hamilton County, Tennessee");
    expect(parcelPlaceLine({ countyName: "Orange", state: "Florida" })).toBe("Orange County, Florida");
  });
});

describe("Hamilton County parcel extract", () => {
  const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
    source: string;
    queryUrl: string;
    coverage: string;
    featureCount: number;
    gaps: string[];
  };

  it("uses Live_Parcels instead of Comptroller IMPACT", () => {
    expect(county.source).toBe("tn-hamilton-live-parcels");
    expect(county.queryUrl).toContain("/Live_Parcels/MapServer/0/query");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(8000);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/not an IMPACT county/i);
    expect(gaps).not.toMatch(/tn-impact/);
    expect(gaps).toMatch(/Place Type/);
    expect(gaps).toMatch(/FeatureServer/);
    expect(gaps).toMatch(/East Ridge/);
    expect(gaps).toMatch(/Live_East_Ridge/);
    expect(gaps).toMatch(/Collegedale/);
    expect(gaps).toMatch(/Red Bank/);
    expect(gaps).toMatch(/Soddy Daisy/);
    expect(gaps).toMatch(/Signal Mountain/);
    expect(gaps).toMatch(/Lookout Mountain/);
    expect(gaps).toMatch(/Lakesite/);
    expect(gaps).toMatch(/Walden/);
    expect(gaps).toMatch(/Ridgeside/);
  });

  it("keeps outlines and assessor attributes on the tiled parcels", () => {
    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47065/tiles");
    const files = readdirSync(tileDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seen = 0;
    let owners = 0;
    let cards = 0;
    let zoned = 0;
    let municipal = 0;
    let flu = 0;
    let chattanooga = 0;
    let eastRidge = 0;
    const municipalNames = new Set(["Chattanooga", "East Ridge", "Collegedale", "Red Bank", "Soddy Daisy", "Signal Mountain"]);
    const gapCities = new Set(["Lookout Mountain", "Lakesite", "Walden", "Ridgeside"]);
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tileDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("47065");
        expect(props.state).toBe("Tennessee");
        expect(props.source).toBe("tn-hamilton-live-parcels");
        expect(props.marketIds).toContain("Chattanooga");
        expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
        const ring =
          feature.geometry.type === "Polygon" ? feature.geometry.coordinates[0] : feature.geometry.coordinates[0][0];
        expect(ring.length).toBeGreaterThanOrEqual(4);
        expect(ring[0][0]).toBeGreaterThan(-86.4);
        expect(ring[0][0]).toBeLessThan(-84.5);
        expect(ring[0][1]).toBeGreaterThan(34.6);
        expect(ring[0][1]).toBeLessThan(35.6);
        if (props.ownerName) owners += 1;
        if (props.appraiserUrl?.includes("assessor.hamiltontn.gov/card/")) cards += 1;
        if (props.zoningDistrict) zoned += 1;
        if (props.jurisdictionPrefix && municipalNames.has(props.jurisdictionPrefix)) municipal += 1;
        if (props.jurisdictionPrefix === "Chattanooga") {
          chattanooga += 1;
          expect(props.flu?.code ?? null).toBeNull();
        }
        if (props.jurisdictionPrefix === "East Ridge") {
          eastRidge += 1;
          expect(props.flu?.code ?? null).toBeNull();
        }
        if (props.jurisdictionPrefix && gapCities.has(props.jurisdictionPrefix)) {
          expect(props.zoningCode ?? null).toBeNull();
          expect(props.flu?.code ?? null).toBeNull();
          expect(props.dataGaps?.join(" ") ?? "").toMatch(/no dedicated zoning REST/i);
        }
        if (props.flu?.code) {
          flu += 1;
          expect(props.jurisdictionPrefix).toBe("Unincorporated Hamilton");
          expect(props.flu.jurisdiction).toBe("Plan Hamilton");
          expect(props.flu.source).toContain("PlanHamilton/MapServer/3");
        }
        seen += 1;
      }
    }
    expect(seen).toBe(county.featureCount);
    expect(owners).toBeGreaterThan(1000);
    expect(cards).toBeGreaterThan(1000);
    expect(zoned).toBeGreaterThan(1000);
    expect(municipal).toBeGreaterThan(0);
    expect(chattanooga).toBeGreaterThan(0);
    expect(eastRidge).toBeGreaterThan(0);
    expect(flu).toBeGreaterThan(0);
    expect(flu).toBeLessThan(seen);
    const sample = JSON.parse(readFileSync(path.join(tileDir, files[0]), "utf8")) as ParcelCollection;
    const rich = sample.features.find((feature: ParcelFeature) => feature.properties.ownerName && feature.properties.appraiserUrl);
    expect(rich?.properties.mailingAddress).toBeTruthy();
    expect(rich?.properties.tax.marketValue == null || typeof rich.properties.tax.marketValue === "number").toBe(true);
  });
});
