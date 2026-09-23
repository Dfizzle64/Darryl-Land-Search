import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { describeOpportunityZone, describeOz2Eligibility } from "../lib/opportunityZone";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37169/county.json");

type StokesCounty = {
  fips: string;
  source: string;
  featureCount: number;
  coverage: string;
  minAcres: number;
  maxAcres: number;
  gaps: string[];
  qa: {
    parcelPageSize: number;
    zones: {
      eligibleGeoids: string[];
      designatedGeoids: string[];
      sameGeoid: number;
      eligibleParcels: number;
      designatedParcels: number;
    };
    king: { pageSize: number; forsythLeaked: number; forsythExcluded: number };
  };
};

function loadStokes(): { county: StokesCounty; features: ParcelCollection["features"] } {
  const county = JSON.parse(readFileSync(countyPath, "utf8")) as StokesCounty;
  const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37169/tiles");
  const features: ParcelCollection["features"] = [];
  for (const name of readdirSync(tileDir)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tileDir, name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return { county, features };
}

describe("Stokes County NC parcels", () => {
  it("does not describe a designated miss as an Orange County geography miss", () => {
    const described = describeOpportunityZone({
      inOpportunityZone: false,
      tractGeoid: null,
      tractName: null,
      source: "hud-opportunity-zones-2010",
      designatedRural: null,
    });
    expect(described.inZone).toBe(false);
    expect(described.detail).not.toMatch(/Orange County/i);
    const eligible = describeOz2Eligibility({
      eligible: false,
      rural: null,
      tractGeoid: null,
      tractName: null,
      designation: "not-eligible",
      source: "rev-proc-2026-14",
    });
    expect(eligible.detail).not.toMatch(/Orange County/i);
    expect(eligible.detail).toMatch(/not a 2027 QOZ designation/i);
  });

  it("keeps the county GIS extract inside 5–150 acres and does not treat eligibility as designation", () => {
    const { county, features } = loadStokes();
    expect(county.fips).toBe("37169");
    expect(county.source).toBe("nc-stokes-alllayers-24");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.minAcres).toBe(5);
    expect(county.maxAcres).toBe(150);
    expect(county.featureCount).toBe(features.length);
    expect(county.featureCount).toBeGreaterThan(8000);
    expect(county.qa.parcelPageSize).toBe(2000);
    expect(county.qa.king.pageSize).toBeLessThanOrEqual(1000);
    expect(county.qa.king.forsythLeaked).toBe(0);
    expect(county.qa.king.forsythExcluded).toBeGreaterThan(0);
    expect(county.qa.zones.sameGeoid).toBe(0);
    expect(county.qa.zones.eligibleGeoids).toEqual(["37169070101", "37169070302"]);
    expect(county.qa.zones.designatedGeoids).not.toEqual(expect.arrayContaining(county.qa.zones.eligibleGeoids));
    expect(county.gaps.join(" ")).toMatch(/not a designated QOZ/i);

    let eligible = 0;
    let designated = 0;
    for (const feature of features) {
      const props = feature.properties;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.countyFips).toBe("37169");
      expect(props.source).toBe("nc-stokes-alllayers-24");
      expect(props.marketIds).toEqual(["Winston-Salem"]);
      const oz2 = props.oz2Eligibility;
      const oz = props.opportunityZone;
      expect(oz2).toBeTruthy();
      expect(oz).toBeTruthy();
      expect(oz2?.designation === "eligible-for-nomination" || oz2?.designation === "not-eligible").toBe(true);
      if (oz2?.eligible) {
        eligible += 1;
        expect(oz2.designation).toBe("eligible-for-nomination");
        expect(oz2.rural).toBe(true);
        expect(oz2.tractGeoid && county.qa.zones.eligibleGeoids.includes(oz2.tractGeoid)).toBe(true);
        expect(oz?.tractGeoid).not.toBe(oz2.tractGeoid);
        expect(oz?.source).not.toMatch(/rev-proc|eligible/i);
      } else {
        expect(oz2?.designation).toBe("not-eligible");
        expect(oz2?.tractGeoid ?? null).toBeNull();
      }
      if (oz?.inOpportunityZone) {
        designated += 1;
        expect(oz.source).toBe("hud-opportunity-zones-2010");
        expect(oz.tractGeoid && county.qa.zones.eligibleGeoids.includes(oz.tractGeoid)).toBe(false);
      }
    }
    expect(eligible).toBe(county.qa.zones.eligibleParcels);
    expect(designated).toBe(county.qa.zones.designatedParcels);
    expect(eligible).toBeGreaterThan(0);
  });
});
