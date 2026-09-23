import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { inMarketAcreageBand } from "../lib/marketParcels";
import { parcelAppraiserUrl } from "../lib/format";
import type { ParcelCollection } from "../lib/types";

const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47147/county.json");

describe("Robertson County, Tennessee parcels", () => {
  it("uses IMPACT county 74, not the empty FIPS suffix, and keeps 5–150 acres", () => {
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      coverage: string;
      featureCount: number;
      source: string;
      queryUrl: string;
      impactCountyId: number;
      impactJur: string;
      gaps: string[];
      rejectedSources: { id: string; url: string }[];
      municipalities: { name: string; zoning: string }[];
      minAcres: number;
      maxAcres: number;
    };
    expect(county.fips).toBe("47147");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(8000);
    expect(county.featureCount).toBeLessThan(9500);
    expect(county.source).toBe("tn-impact-47147");
    expect(county.impactCountyId).toBe(74);
    expect(county.impactJur).toBe("074");
    expect(county.queryUrl).toContain("/IMPACT/Parcels/FeatureServer/0/query");
    expect(county.queryUrl.toLowerCase()).not.toContain("greenbrierservice");
    expect(county.minAcres).toBe(5);
    expect(county.maxAcres).toBe(150);
    const gaps = county.gaps.join(" ");
    expect(gaps).toContain("COUNTY_ID 74");
    expect(gaps).toContain("Coopertown");
    expect(gaps).toContain("Cross Plains");
    expect(gaps).toContain("Ridgetop");
    expect(gaps).toContain("West Virginia");
    expect(gaps).toContain("not a designated");
    expect(county.rejectedSources.map((item) => item.id)).toContain("wv-greenbrier-service");
    expect(county.rejectedSources.map((item) => item.url).join(" ")).not.toContain("FeatureServer/0/query");
    const gapTowns = county.municipalities.filter((item) => item.zoning === "gap").map((item) => item.name);
    expect(gapTowns).toEqual(expect.arrayContaining(["Coopertown", "Cross Plains", "Ridgetop", "Portland"]));
    const appraiser = parcelAppraiserUrl({ parcelId: "074001", countyFips: "47147" });
    expect(appraiser.href).toContain("assessment.cot.tn.gov");
    expect(appraiser.label).toContain("Robertson");
  });

  it("does not mark nomination-eligible parcels as designated QOZs", () => {
    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47147/tiles");
    expect(existsSync(tileDir)).toBe(true);
    const files = readdirSync(tileDir).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seen = 0;
    let eligible = 0;
    let designated = 0;
    const cities = new Set<string>();
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tileDir, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("47147");
        expect(props.marketIds).toContain("Nashville");
        expect(props.marketIds).not.toContain("Orlando");
        const [lon, lat] = props.centroid;
        expect(lon).toBeGreaterThan(-87.4);
        expect(lon).toBeLessThan(-86.4);
        expect(lat).toBeGreaterThan(36.2);
        expect(lat).toBeLessThan(36.8);
        const oz2 = props.oz2Eligibility;
        expect(oz2?.designation === "eligible-for-nomination" || oz2?.designation === "not-eligible").toBe(true);
        if (oz2?.eligible) {
          eligible += 1;
          expect(oz2.designation).toBe("eligible-for-nomination");
          expect(oz2.rural).toBe(true);
          expect(oz2.tractGeoid?.startsWith("47147")).toBe(true);
        }
        if (props.opportunityZone?.inOpportunityZone) designated += 1;
        if (props.situsCity) cities.add(props.situsCity);
        const zoning = props.zoningCode ?? "";
        expect(zoning.toLowerCase()).not.toContain("greenbrierservice");
        seen += 1;
      }
    }
    expect(seen).toBeGreaterThan(8000);
    expect(eligible).toBeGreaterThan(0);
    expect(designated).toBe(0);
    expect(cities.has("Springfield") || cities.has("Greenbrier") || cities.has("White House")).toBe(true);
  });
});
