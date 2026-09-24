import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37197");

function loadFeatures(): ParcelFeature[] {
  const tiles = path.join(COUNTY, "tiles");
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(tiles)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

describe("Yadkin County NC parcels", () => {
  it("uses county GIS, keeps town zoning, and does not treat cropland as future land use", () => {
    const countyPath = path.join(COUNTY, "county.json");
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      source: string;
      queryUrl: string;
      featureCount: number;
      coverage: string;
      gaps: string[];
      yadkin: {
        fluJoined: number;
        fluGap: string;
        onemapWhere: string;
        designatedQozGeoids: string[];
        oz2EligibleGeoids: string[];
        zoningByPrefix: Record<string, number>;
        ignoredLandUseClasses: string[];
      };
    };
    expect(county.fips).toBe("37197");
    expect(county.source).toBe("nc-yadkin-county-gis");
    expect(county.queryUrl).toContain("CountyGISmap/MapServer/1");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBeGreaterThan(8000);
    expect(county.featureCount).toBeLessThan(9000);
    const gapText = county.gaps.join(" ");
    expect(gapText).toMatch(/cntyfips='197'/);
    expect(gapText).toMatch(/Boonville/);
    expect(gapText).toMatch(/East Bend/);
    expect(gapText).toMatch(/Jonesville/);
    expect(gapText).toMatch(/Yadkinville/);
    expect(gapText).toMatch(/cropland/i);
    expect(gapText).toMatch(/PDF-only/);
    expect(gapText).toMatch(/not a designated QOZ/i);
    expect(county.yadkin.fluJoined).toBe(0);
    expect(county.yadkin.fluGap).toBe("pdf-only");
    expect(county.yadkin.onemapWhere).toContain("cntyfips='197'");
    expect(county.yadkin.ignoredLandUseClasses.some((name) => /cropland|soybean|corn/i.test(name))).toBe(true);
    expect(county.yadkin.designatedQozGeoids).toEqual(["37197050501"]);
    expect(county.yadkin.oz2EligibleGeoids).toEqual(["37197050401", "37197050502"]);
    for (const prefix of ["YAD", "BVN", "EBD", "JVL", "YVL"]) {
      expect(county.yadkin.zoningByPrefix[prefix]).toBeGreaterThan(0);
    }

    const features = loadFeatures();
    expect(features.length).toBe(county.featureCount);
    const prefixes = new Set<string>();
    let eligible = 0;
    let designated = 0;
    const blocked = new Set(county.yadkin.ignoredLandUseClasses.map((name) => name.toUpperCase()));
    for (const feature of features) {
      const props = feature.properties;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.countyFips).toBe("37197");
      expect(props.source).toBe("nc-yadkin-county-gis");
      expect(props.marketIds).toEqual(["Winston-Salem"]);
      expect(props.flu).toBeNull();
      if (props.jurisdictionPrefix) prefixes.add(props.jurisdictionPrefix);
      const zoning = (props.zoningCode || "").toUpperCase();
      const district = (props.zoningDistrict || "").toUpperCase();
      expect(blocked.has(zoning)).toBe(false);
      expect(blocked.has(district)).toBe(false);
      expect(zoning).not.toMatch(/CROPLAND|SOYBEAN/);
      const oz = props.opportunityZone;
      const oz2 = props.oz2Eligibility;
      expect(oz?.source).toBe("hud-fs-13");
      expect(oz2?.source).toBe("rev-proc-2026-14");
      expect(oz2?.designation === "eligible-for-nomination" || oz2?.designation === "not-eligible").toBe(true);
      if (oz2?.eligible) {
        eligible += 1;
        expect(oz2.designation).toBe("eligible-for-nomination");
        expect(["37197050401", "37197050502"]).toContain(oz2.tractGeoid);
        expect(oz2.rural).toBe(true);
        expect(oz?.inOpportunityZone === true && oz.tractGeoid === oz2.tractGeoid).toBe(false);
      }
      if (oz?.inOpportunityZone) {
        designated += 1;
        expect(oz.tractGeoid).toBe("37197050501");
        expect(oz.designatedRural).toBe(true);
        expect(oz2?.tractGeoid).not.toBe(oz.tractGeoid);
      }
    }
    expect(prefixes).toEqual(new Set(["YAD", "BVN", "EBD", "JVL", "YVL"]));
    expect(eligible).toBe(county.yadkin.oz2EligibleParcels);
    expect(designated).toBe(county.yadkin.designatedQozParcels);
    expect(eligible).toBeGreaterThan(0);
  });
});
