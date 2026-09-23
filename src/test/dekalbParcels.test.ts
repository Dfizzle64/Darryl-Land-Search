import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadFluConfig, loadZoningConfig } from "../lib/data/loadFixtures";
import { fluAllowsMultifamily } from "../lib/flu";
import { formatParcelPlace, parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";
import { zoningAllowsMultifamily } from "../lib/zoning";

describe("DeKalb place line and assessor link", () => {
  it("names Georgia and the DeKalb appraiser, not Orange County or Decatur Illinois", () => {
    expect(formatParcelPlace({ countyName: "DeKalb", state: "Georgia", situsCity: null, situsZip: null })).toBe(
      "DeKalb County, Georgia",
    );
    expect(formatParcelPlace({ countyName: "Orange", state: "Florida", situsCity: null, situsZip: null })).toBe(
      "Orange County, FL",
    );
    const link = parcelAppraiserUrl({ parcelId: "06 249 01 004", countyFips: "13089" });
    expect(link.href).toBe("https://propertyappraisal.dekalbcountyga.gov/");
    expect(link.label).toContain("DeKalb");
    expect(link.href).not.toContain("ocpa");
    expect(link.href).not.toContain("decaturil");
  });

  it("does not score DeKalb or city zoning and FLU as Orange County multifamily", async () => {
    const zoning = await loadZoningConfig();
    const flu = await loadFluConfig();
    expect(zoningAllowsMultifamily("R-100", "DeKalb:R-100", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("RG-3", "Atlanta:RG-3", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("R-60", "Decatur:R-60", zoning, true, true)).toBe(false);
    expect(zoningAllowsMultifamily("PD", "PD", zoning, true, true)).toBe(true);
    expect(
      fluAllowsMultifamily({ code: "NC", label: "Neighborhood Center", jurisdiction: "Decatur", source: "decatur-ga" }, flu),
    ).toBeNull();
    expect(fluAllowsMultifamily({ code: "NC", label: "Neighborhood Center", jurisdiction: "ORG", source: "org" }, flu)).toBe(
      true,
    );
  });
});

describe("DeKalb County 5–150 acre extract", () => {
  it("uses the assessment view and keeps owner, tax, and city land use without sales", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13089/county.json");
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      coverage: string;
      featureCount: number;
      source: string;
      queryUrl: string;
      gaps: string[];
      municipalities: {
        name: string;
        zoningUrl: string | null;
        fluUrl: string | null;
        zoningJoined: number;
        fluJoined: number;
        fluGap: string | null;
        note: string | null;
      }[];
      sales: { joined: boolean };
      rejected: string[];
      zoningJoinedCount: number;
      fluJoinedCount: number;
    };
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(3000);
    expect(county.featureCount).toBeLessThan(4000);
    expect(county.source).toBe("ga-dekalb-assessment-view-2");
    expect(county.queryUrl).toContain("Tax_Parcels_Assessment_View/FeatureServer/2");
    expect(county.queryUrl).not.toContain("Tax_Parcels/FeatureServer/0");
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/[Nn]o sale/);
    expect(gaps).toMatch(/Chamblee/);
    expect(gaps).toMatch(/Stone Mountain/);
    expect(gaps).toMatch(/Decatur, Illinois/);
    expect(gaps).toMatch(/not a designated QOZ/);
    expect(county.sales.joined).toBe(false);
    expect(county.rejected.join(" ")).toMatch(/Illinois/);
    expect(county.rejected.join(" ")).toMatch(/Alabama/);
    expect(county.rejected.join(" ")).toMatch(/Tennessee/);

    const byName = new Map(county.municipalities.map((city) => [city.name, city]));
    for (const name of ["Decatur", "Brookhaven", "Dunwoody", "Doraville", "Tucker", "Stonecrest"]) {
      const city = byName.get(name);
      expect(city?.zoningUrl).toBeTruthy();
      expect(city?.fluUrl).toBeTruthy();
    }
    expect(byName.get("Decatur")?.zoningUrl).not.toContain("decaturil");
    const chamblee = byName.get("Chamblee");
    expect(chamblee?.zoningUrl ?? null).toBeNull();
    expect(chamblee?.fluUrl).toBeTruthy();
    expect(chamblee?.zoningJoined).toBe(0);
    for (const name of ["Stone Mountain", "Avondale Estates", "Clarkston", "Lithonia", "Pine Lake"]) {
      const city = byName.get(name);
      expect(city?.zoningUrl ?? null).toBeNull();
      expect(city?.fluUrl ?? null).toBeNull();
      expect(city?.fluGap || "").toMatch(/No public/);
    }
    expect(byName.get("Atlanta")?.note || county.gaps.join(" ")).toBeTruthy();

    const tilesDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13089/tiles");
    const files = readdirSync(tilesDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seenOwner = false;
    let seenTax = false;
    let seenMail = false;
    let seenDistrict = false;
    let zoning = 0;
    let flu = 0;
    let checked = 0;
    const places = new Set<string>();
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tilesDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("13089");
        expect(props.state).toBe("Georgia");
        expect(props.source).toBe("ga-dekalb-assessment-view-2");
        expect(props.marketIds).toContain("Atlanta");
        expect(props.lastSale.price).toBeNull();
        expect(props.lastSale.date).toBeNull();
        expect(props.opportunityZone).toBeNull();
        expect(props.oz2Eligibility).toBeNull();
        const lat = props.centroid[1];
        const lon = props.centroid[0];
        expect(lon).toBeGreaterThan(-84.5);
        expect(lon).toBeLessThan(-84.0);
        expect(lat).toBeGreaterThan(33.55);
        expect(lat).toBeLessThan(34.05);
        if (props.ownerName) seenOwner = true;
        if (props.tax.marketValue != null && props.tax.assessedValue != null) seenTax = true;
        if (props.mailingAddress.line1 && props.mailingAddress.zip) seenMail = true;
        if (props.dorCode) seenDistrict = true;
        if (props.zoningCode) {
          zoning += 1;
          expect(props.zoningDistrict?.endsWith(`:${props.zoningCode}`)).toBe(true);
          const place = props.zoningDistrict?.slice(0, -(props.zoningCode.length + 1));
          if (place) places.add(place);
        }
        if (props.flu?.code) {
          flu += 1;
          expect(props.flu.jurisdiction).toBeTruthy();
        }
        checked += 1;
      }
    }
    expect(checked).toBe(county.featureCount);
    expect(seenOwner).toBe(true);
    expect(seenTax).toBe(true);
    expect(seenMail).toBe(true);
    expect(seenDistrict).toBe(true);
    expect(zoning).toBe(county.zoningJoinedCount);
    expect(flu).toBe(county.fluJoinedCount);
    expect(zoning).toBeGreaterThan(0);
    expect(flu).toBeGreaterThan(0);
    expect(places.has("DeKalb") || places.has("Decatur") || places.has("Atlanta")).toBe(true);
  });
});
