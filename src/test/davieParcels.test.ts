import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const countyDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37059");

function loadDavie(): { featureCount: number; features: ParcelFeature[] } {
  const county = JSON.parse(readFileSync(path.join(countyDir, "county.json"), "utf8")) as { featureCount: number };
  const features = readdirSync(path.join(countyDir, "tiles"))
    .filter((name) => name.endsWith(".geojson"))
    .flatMap((name) => {
      const collection = JSON.parse(readFileSync(path.join(countyDir, "tiles", name), "utf8")) as ParcelCollection;
      return collection.features;
    });
  return { featureCount: county.featureCount, features };
}

describe("Davie County NC parcels", () => {
  const { featureCount, features } = loadDavie();

  it("keeps a complete 5–150 acre county extract", () => {
    expect(features.length).toBe(featureCount);
    expect(features.length).toBeGreaterThan(5000);
    for (const feature of features) {
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.countyFips).toBe("37059");
      expect(feature.properties.state).toBe("North Carolina");
      expect(feature.properties.marketIds).toEqual(["Winston-Salem"]);
      expect(feature.properties.source).toBe("davie-county-gis-parcels");
    }
  });

  it("does not treat OZ 2.0 eligibility as a designated Opportunity Zone", () => {
    let designated = 0;
    for (const feature of features) {
      const zone = feature.properties.opportunityZone;
      const eligibility = feature.properties.oz2Eligibility;
      expect(eligibility?.eligible).toBe(false);
      expect(eligibility?.designation).toBe("not-eligible");
      expect(eligibility?.tractGeoid?.startsWith("37059")).toBe(true);
      if (zone?.inOpportunityZone) {
        designated += 1;
        expect(zone.tractGeoid).toBe("37059080500");
        expect(zone.designatedRural).toBe(true);
        expect(eligibility?.eligible).toBe(false);
      }
    }
    expect(designated).toBeGreaterThan(0);
  });

  it("joins local zoning and does not store emails", () => {
    const zoned = features.filter((feature) => feature.properties.zoningCode).length;
    expect(zoned).toBeGreaterThan(features.length * 0.9);
    const jurisdictions = new Set(features.map((feature) => feature.properties.jurisdictionCode).filter(Boolean));
    expect(jurisdictions).toEqual(new Set(["DAVIE COUNTY", "MOCKSVILLE", "BERMUDA RUN", "COOLEEMEE"]));
    for (const feature of features) {
      expect(JSON.stringify(feature.properties)).not.toContain("@");
      expect(feature.properties.flu?.code).not.toBe("TOWN");
    }
  });
});
