import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13035");

function loadFeatures(): ParcelFeature[] {
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(path.join(COUNTY, "tiles"))) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(COUNTY, "tiles", name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

describe("Butts County GA parcels", () => {
  it("keeps the TOTALACRES Schneider extract and does not invent sales or opportunity zones", () => {
    const county = JSON.parse(readFileSync(path.join(COUNTY, "county.json"), "utf8")) as {
      fips: string;
      source: string;
      queryUrl: string;
      featureCount: number;
      coverage: string;
      dropped: number;
      gaps: string[];
    };
    expect(county.fips).toBe("13035");
    expect(county.source).toBe("ga-butts-wfs-0");
    expect(county.queryUrl).toContain("ButtsCountyGA_WFS/MapServer/0");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBe(2738);
    expect(county.dropped).toBe(14);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/TOTALACRES/);
    expect(gaps).toMatch(/DEED_ACRES is not the filter/);
    expect(gaps).toMatch(/CURR_VAL/);
    expect(gaps).toMatch(/ESTTAX/);
    expect(gaps).toMatch(/SALES_AREA is a neighborhood code/);
    expect(gaps).toMatch(/MapServer\/4/);
    expect(gaps).toMatch(/Flowvilla/);
    expect(gaps).toMatch(/Zoning_02 and Zoning_03/);
    expect(gaps).toMatch(/Comprehensive Plan PDF/);
    expect(gaps).toMatch(/Butte County, California/);
    expect(gaps).toMatch(/Jackson, Mississippi/);
    expect(gaps).toMatch(/Jackson County, Georgia/);
    expect(gaps).toMatch(/LandPro/);
    expect(gaps).toMatch(/does not assign Opportunity Zone/);
    expect(gaps).toMatch(/2738 parcel ids kept/);
    expect(gaps).toMatch(/142 kept parcels/);

    const features = loadFeatures();
    expect(features).toHaveLength(2738);
    const zoning = { JACKSON: 0, FLOVILLA: 0, JENKINSBURG: 0, BUTTS: 0, none: 0 };
    let sample: ParcelFeature | undefined;
    for (const feature of features) {
      const props = feature.properties;
      expect(props.countyFips).toBe("13035");
      expect(props.marketIds).toEqual(["Atlanta"]);
      expect(props.source).toBe("ga-butts-wfs-0");
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.flu).toBeNull();
      expect(props.lastSale).toEqual({ date: null, price: null, qualified: null });
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.situsCity).not.toBe("County");
      expect(["JACKSON", "FLOVILLA", "JENKINSBURG", "FLOWVILLA", "COUNTY"]).not.toContain((props.zoningCode || "").toUpperCase());
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-84.2);
      expect(lon).toBeLessThan(-83.7);
      expect(lat).toBeGreaterThan(33.1);
      expect(lat).toBeLessThan(33.55);
      expect(props.appraiserUrl ?? "").toContain("App=ButtsCountyGA");
      expect(props.appraiserUrl ?? "").toContain(encodeURIComponent(props.parcelId));
      const prefix = props.jurisdictionPrefix;
      if (prefix === "JACKSON" || prefix === "FLOVILLA" || prefix === "JENKINSBURG" || prefix === "BUTTS") {
        zoning[prefix] += 1;
        expect(props.zoningCode).toBeTruthy();
      } else {
        zoning.none += 1;
        expect(props.zoningCode).toBeNull();
      }
      if (props.parcelId === "00010001") sample = feature;
    }
    expect(zoning).toEqual({ JACKSON: 98, FLOVILLA: 45, JENKINSBURG: 41, BUTTS: 2554, none: 0 });
    expect(sample?.properties.acreage).toBe(61.66);
    expect(sample?.properties.ownerName).toBe("JAMES PRESTON IV & HARDIE");
    expect(sample?.properties.situsAddress).toBe("HOSANNAH RD");
    expect(sample?.properties.situsCity).toBeNull();
    expect(sample?.properties.mailingAddress.city).toBe("LOCUST GROVE");
    expect(sample?.properties.zoningCode).toBe("A-R");
    expect(sample?.properties.jurisdictionPrefix).toBe("BUTTS");
    expect(sample?.properties.tax.marketValue).toBe(248646);
    expect(sample?.properties.tax.taxes).toBe(644.36);
    expect(sample?.properties.centroid[0]).toBeGreaterThan(-84.11);
    expect(sample?.properties.centroid[0]).toBeLessThan(-84.09);
    expect(sample?.properties.centroid[1]).toBeGreaterThan(33.29);
    expect(sample?.properties.centroid[1]).toBeLessThan(33.31);

    const linked = parcelAppraiserUrl({
      parcelId: "00010001",
      countyFips: "13035",
      appraiserUrl: sample?.properties.appraiserUrl,
    });
    expect(linked.href).toContain("App=ButtsCountyGA");
    expect(linked.href).toContain("PageType=Report");
    expect(linked.label).toBe("Open this parcel in Butts County qPublic");
    const search = parcelAppraiserUrl({ parcelId: "00010001", countyFips: "13035" });
    expect(search.href).toContain("PageType=Search");
    expect(search.label).toBe("Open Butts County qPublic search");
  });
});
