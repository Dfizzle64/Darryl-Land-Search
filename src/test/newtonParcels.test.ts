import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { findFluCategory } from "../lib/flu";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { FluConfig, ParcelCollection, ParcelFeature, ZoningConfig } from "../lib/types";
import { findZoningHit } from "../lib/zoning";

const SOCIAL_CIRCLE_ZONING = new Set([
  "AG",
  "AG-2",
  "CBD",
  "GC",
  "I-1",
  "I-2",
  "IO",
  "NC",
  "PUD",
  "R-15",
  "R-25",
  "RHD",
  "RMD",
  "SSBP-T1",
]);

const NEWTON_FLU_JURISDICTIONS = new Set([
  "COVINGTON",
  "OXFORD",
  "PORTERDALE",
  "MANSFIELD",
  "NEWBORN",
  "SOCIAL CIRCLE",
  "NEWTON",
]);

describe("Newton County GA parcels", () => {
  it("keeps Newton County GA inside 13217, the acreage band, and the public-source gaps", () => {
    const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13217/county.json");
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
      fips: string;
      coverage: string;
      featureCount: number;
      source: string;
      gaps: string[];
    };
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.fips).toBe("13217");
    expect(county.source).toBe("ga-newton-uofmd-parcels");
    expect(county.featureCount).toBeGreaterThan(0);
    const gapText = county.gaps.join(" ");
    expect(gapText).toMatch(/University of Maryland/i);
    expect(gapText).toMatch(/2021/);
    expect(gapText).toMatch(/Covington/);
    expect(gapText).toMatch(/Social Circle/);
    expect(gapText).toMatch(/NEGRC/);
    const zoningConfig = JSON.parse(readFileSync(path.join(process.cwd(), "data/zoning-config.json"), "utf8")) as ZoningConfig;
    const fluConfig = JSON.parse(readFileSync(path.join(process.cwd(), "data/flu-config.json"), "utf8")) as FluConfig;
    const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13217/tiles");
    const features: ParcelFeature[] = [];
    for (const name of readdirSync(tileDir)) {
      if (!name.endsWith(".geojson")) continue;
      const collection = JSON.parse(readFileSync(path.join(tileDir, name), "utf8")) as ParcelCollection;
      features.push(...collection.features);
    }
    expect(features).toHaveLength(county.featureCount);
    let socialCircle = 0;
    let fluJoined = 0;
    const fluSources = new Set<string>();
    for (const feature of features) {
      const props = feature.properties;
      expect(props.countyFips).toBe("13217");
      expect(props.id.startsWith("13217:")).toBe(true);
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.marketIds).toEqual(["Atlanta"]);
      expect(props.ownerName).toBeNull();
      expect(props.ownerName2).toBeNull();
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.tax.marketValue).toBeNull();
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.lastSale.qualified).toBeNull();
      if (props.lastSale.date) {
        expect(props.lastSale.date <= "2021-12-31").toBe(true);
      }
      if (props.situsAddress) {
        expect(props.situsAddress).not.toMatch(/^\d+\s/);
      }
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-84.08);
      expect(lon).toBeLessThan(-83.64);
      expect(lat).toBeGreaterThan(33.34);
      expect(lat).toBeLessThan(33.77);
      expect(props.appraiserUrl ?? "").toContain("App=NewtonCountyGA");
      expect(props.appraiserUrl ?? "").toContain(encodeURIComponent(props.parcelId));
      if (props.zoningCode) {
        socialCircle += 1;
        expect(SOCIAL_CIRCLE_ZONING.has(props.zoningCode)).toBe(true);
        expect(props.jurisdictionPrefix).toBe("SOC");
        expect(findZoningHit(props.zoningCode, props.zoningDistrict, zoningConfig)).toBeNull();
      } else {
        expect(props.jurisdictionPrefix).toBeNull();
      }
      if (props.flu?.code) {
        fluJoined += 1;
        expect(NEWTON_FLU_JURISDICTIONS.has(props.flu.jurisdiction ?? "")).toBe(true);
        expect(findFluCategory(props.flu, fluConfig)).toBeNull();
        if (props.flu.source) fluSources.add(props.flu.source);
      }
    }
    expect(socialCircle).toBeGreaterThan(0);
    expect(fluJoined).toBeGreaterThan(0);
    expect(fluSources.has("negrc-newton-ca-454")).toBe(true);
    expect(fluSources.has("negrc-covington-flu-447")).toBe(true);
    expect(fluSources.has("negrc-social-circle-ca-469")).toBe(true);
  });
});
