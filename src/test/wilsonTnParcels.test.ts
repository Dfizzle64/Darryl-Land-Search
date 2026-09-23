import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47189/county.json");
const ncCountyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37195/county.json");

describe("Wilson County, Tennessee parcels", () => {
  const county = JSON.parse(readFileSync(countyPath, "utf8")) as {
    fips: string;
    state: string;
    featureCount: number;
    coverage: string;
    source: string;
    queryUrl: string;
    gaps: string[];
    comptrollerCountyId?: number;
    joinStats?: { eligible?: number; designated?: number; hudDesignatedTracts?: number };
  };

  it("keeps Tennessee Wilson on IMPACT county id 95 and leaves North Carolina Wilson alone", () => {
    expect(county.fips).toBe("47189");
    expect(county.state).toBe("Tennessee");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("tn-impact-47189");
    expect(county.comptrollerCountyId).toBe(95);
    expect(county.queryUrl).toContain("maps.cot.tn.gov");
    expect(county.queryUrl).not.toMatch(/wilson-co\.com|geojobe|geopowered/i);
    expect(county.featureCount).toBeGreaterThan(9000);
    const nc = JSON.parse(readFileSync(ncCountyPath, "utf8")) as { fips: string; state: string; source: string };
    expect(nc.fips).toBe("37195");
    expect(nc.state).toBe("North Carolina");
    expect(nc.source).toBe("nc-onemap-37195");
  });

  it("documents the unincorporated, Watertown, North Carolina, and token-gated gaps", () => {
    const gaps = county.gaps.join("\n");
    expect(gaps).toMatch(/Unincorporated Wilson/i);
    expect(gaps).toMatch(/Watertown/i);
    expect(gaps).toMatch(/North Carolina/i);
    expect(gaps).toMatch(/GEOJobe|token-gated/i);
    expect(gaps).toMatch(/not a designated QOZ/i);
  });

  it("keeps 5–150 acre Tennessee parcels and does not mark eligible tracts as designated", () => {
    const tiles = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47189/tiles");
    const files = readdirSync(tiles).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let seen = 0;
    let eligible = 0;
    let lebanonZoned = 0;
    let mtJulietZoned = 0;
    let mtJulietFlu = 0;
    let watertown = 0;
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tiles, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe("47189");
        expect(props.state).toBe("Tennessee");
        expect(props.marketIds).toContain("Nashville");
        expect(props.source).toBe("tn-impact-47189");
        expect(props.parcelId.startsWith("095")).toBe(true);
        if (props.jurisdictionCode === "UNINC" || props.jurisdictionCode === "WAT" || props.jurisdictionCode == null) {
          expect(props.zoningCode).toBeNull();
          expect(props.flu).toBeNull();
        }
        if (props.flu) {
          expect(props.jurisdictionCode).toBe("MTJ");
          expect(props.flu.jurisdiction).toBe("MTJ");
        }
        if (props.jurisdictionCode === "LEB") {
          expect(props.flu).toBeNull();
          if (props.zoningCode) lebanonZoned += 1;
        }
        if (props.jurisdictionCode === "MTJ" && props.zoningCode) mtJulietZoned += 1;
        if (props.flu?.jurisdiction === "MTJ") mtJulietFlu += 1;
        if (props.jurisdictionCode === "WAT") watertown += 1;
        const oz2 = props.oz2Eligibility;
        const oz = props.opportunityZone;
        expect(oz?.inOpportunityZone).toBe(false);
        if (oz2?.eligible) {
          eligible += 1;
          expect(oz2.designation).toBe("eligible-for-nomination");
          expect(oz2.rural).toBe(true);
          expect(oz2.tractGeoid?.startsWith("47189")).toBe(true);
          expect(oz?.inOpportunityZone).toBe(false);
          expect(oz?.tractGeoid).not.toBe(oz2.tractGeoid);
        }
        seen += 1;
      }
    }
    expect(seen).toBe(county.featureCount);
    expect(eligible).toBeGreaterThan(0);
    expect(lebanonZoned).toBeGreaterThan(0);
    expect(mtJulietZoned).toBeGreaterThan(0);
    expect(mtJulietFlu).toBeGreaterThan(0);
    expect(watertown).toBeGreaterThan(0);
    expect(county.joinStats?.designated ?? 0).toBe(0);
    expect(county.joinStats?.hudDesignatedTracts).toBe(0);
  });
});
