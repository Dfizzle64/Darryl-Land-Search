import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13139");

function loadFeatures(): ParcelFeature[] {
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(path.join(COUNTY, "tiles"))) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(COUNTY, "tiles", name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

describe("Hall County GA parcels", () => {
  it("keeps the deed-acre hallgis extract and does not invent sales or opportunity zones", () => {
    const county = JSON.parse(readFileSync(path.join(COUNTY, "county.json"), "utf8")) as {
      fips: string;
      source: string;
      queryUrl: string;
      featureCount: number;
      coverage: string;
      gaps: string[];
    };
    expect(county.fips).toBe("13139");
    expect(county.source).toBe("ga-hall-addr-pcl-1");
    expect(county.queryUrl).toContain("HallCo_Addr_Pcl_Rds/MapServer/1");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBe(6904);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/DEED_ACRE/);
    expect(gaps).toMatch(/NO_RELEASE/);
    expect(gaps).toMatch(/LAND_VALUE is not copied/);
    expect(gaps).toMatch(/AppID=724/);
    expect(gaps).toMatch(/MUNI/);
    expect(gaps).toMatch(/Lula/);
    expect(gaps).toMatch(/Gainesville FLU_2022/);
    expect(gaps).toMatch(/Nebraska/);
    expect(gaps).toMatch(/LandPro/);
    expect(gaps).toMatch(/does not assign Opportunity Zone/);
    expect(gaps).toMatch(/GAINESVILLE 418/);
    expect(gaps).toMatch(/266 parcels left unzoned/);

    const features = loadFeatures();
    expect(features).toHaveLength(6904);
    const zoning = { GVL: 0, FLB: 0, OAK: 0, HAL: 0, none: 0 };
    const flu = { gainesville: 0, county: 0, none: 0 };
    let sample: ParcelFeature | undefined;
    for (const feature of features) {
      const props = feature.properties;
      expect(props.countyFips).toBe("13139");
      expect(props.marketIds).toEqual(["Atlanta"]);
      expect(props.source).toBe("ga-hall-addr-pcl-1");
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.lastSale).toEqual({ date: null, price: null, qualified: null });
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.zoningCode).not.toBe("MUNI");
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-84.25);
      expect(lon).toBeLessThan(-83.45);
      expect(lat).toBeGreaterThan(34);
      expect(lat).toBeLessThan(34.65);
      expect(props.appraiserUrl ?? "").toContain("App=HallCountyGA");
      expect(props.appraiserUrl ?? "").toContain(encodeURIComponent(props.parcelId));
      const prefix = props.jurisdictionPrefix;
      if (prefix === "GVL" || prefix === "FLB" || prefix === "OAK" || prefix === "HAL") zoning[prefix] += 1;
      else {
        zoning.none += 1;
        expect(props.zoningCode).toBeNull();
      }
      if (props.flu?.source === "gnvl-flu-2022") {
        flu.gainesville += 1;
        expect(props.flu.jurisdiction).toBe("GAINESVILLE");
      } else if (props.flu?.source === "hc-flu-2024") {
        flu.county += 1;
        expect(props.flu.jurisdiction).toBe("HALL");
      } else {
        flu.none += 1;
        expect(props.flu).toBeNull();
      }
      if (props.parcelId === "12039 000008") sample = feature;
    }
    expect(zoning).toEqual({ GVL: 418, FLB: 115, OAK: 151, HAL: 5954, none: 266 });
    expect(flu).toEqual({ gainesville: 413, county: 5785, none: 706 });
    expect(sample?.properties.acreage).toBe(10.24);
    expect(sample?.properties.tax.marketValue).toBe(665530);
    expect(sample?.properties.ownerName).toBe("FATH, KENNETH B");
    expect(sample?.properties.centroid[0]).toBeGreaterThan(-83.81);
    expect(sample?.properties.centroid[0]).toBeLessThan(-83.78);
    expect(sample?.properties.centroid[1]).toBeGreaterThan(34.47);
    expect(sample?.properties.centroid[1]).toBeLessThan(34.49);
  });
});