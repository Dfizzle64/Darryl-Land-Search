import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13103");

function loadFeatures(): ParcelFeature[] {
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(path.join(COUNTY, "tiles"))) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(COUNTY, "tiles", name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

describe("Effingham County GA parcels", () => {
  it("keeps the TOTALACRES extract and does not invent city zoning or opportunity zones", () => {
    const county = JSON.parse(readFileSync(path.join(COUNTY, "county.json"), "utf8")) as {
      fips: string;
      source: string;
      queryUrl: string;
      featureCount: number;
      coverage: string;
      dropped: number;
      markets: string[];
      gaps: string[];
    };
    expect(county.fips).toBe("13103");
    expect(county.markets).toEqual(["Savannah"]);
    expect(county.source).toBe("ga-effingham-parcels-2024");
    expect(county.queryUrl).toContain("Parcels2024/FeatureServer/0");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBe(6128);
    expect(county.dropped).toBe(2);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/TOTALACRES/);
    expect(gaps).toMatch(/ACRES is not the filter/);
    expect(gaps).toMatch(/ZCODE/);
    expect(gaps).toMatch(/no public city zoning FeatureServer/);
    expect(gaps).toMatch(/FLUM_20240903_BOC_APPR_2/);
    expect(gaps).toMatch(/ParcelUpdate/);
    expect(gaps).toMatch(/Illinois/);
    expect(gaps).toMatch(/does not assign Opportunity Zone/);
    expect(gaps).toMatch(/6128 parcel ids kept/);
    expect(gaps).toMatch(/Rincon 149/);
    expect(gaps).toMatch(/Future land use joined on 5444/);
    expect(gaps).toMatch(/sale price on 2147/);
    expect(gaps).toMatch(/current value on 5161/);

    const features = loadFeatures();
    expect(features).toHaveLength(6128);
    const cities = { Rincon: 0, Guyton: 0, Springfield: 0, unincorporated: 0 };
    let zoned = 0;
    let flu = 0;
    let priced = 0;
    let valued = 0;
    let sample: ParcelFeature | undefined;
    for (const feature of features) {
      const props = feature.properties;
      expect(props.countyFips).toBe("13103");
      expect(props.marketIds).toEqual(["Savannah"]);
      expect(props.source).toBe("ga-effingham-parcels-2024");
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.lastSale.qualified).toBeNull();
      expect(props.jurisdictionPrefix).toBe("EFFINGHAM");
      expect(["RINCON", "GUYTON", "SPRINGFIELD"]).not.toContain((props.zoningCode || "").toUpperCase());
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-81.65);
      expect(lon).toBeLessThan(-81.05);
      expect(lat).toBeGreaterThan(32);
      expect(lat).toBeLessThan(32.7);
      expect(props.appraiserUrl ?? "").toContain("AppID=666");
      expect(props.appraiserUrl ?? "").toContain(encodeURIComponent(props.parcelId));
      if (props.situsCity === "Rincon" || props.situsCity === "Guyton" || props.situsCity === "Springfield") cities[props.situsCity] += 1;
      else {
        cities.unincorporated += 1;
        expect(props.situsCity).toBeNull();
      }
      if (props.zoningCode) zoned += 1;
      if (props.flu) {
        flu += 1;
        expect(props.flu.source).toBe("flum-20240903");
        expect(props.flu.jurisdiction).toBe("EFFINGHAM");
      }
      if (props.lastSale.price != null) priced += 1;
      if (props.tax.marketValue != null) valued += 1;
      if (props.parcelId === "03320008") sample = feature;
    }
    expect(cities).toEqual({ Rincon: 149, Guyton: 38, Springfield: 83, unincorporated: 5858 });
    expect(zoned).toBe(6128);
    expect(flu).toBe(5444);
    expect(priced).toBe(2147);
    expect(valued).toBe(5161);
    expect(sample?.properties.acreage).toBe(5);
    expect(sample?.properties.ownerName).toBe("EDWARDS RANDALL E");
    expect(sample?.properties.situsAddress).toBe("2619 OLD RIVER RD");
    expect(sample?.properties.situsCity).toBeNull();
    expect(sample?.properties.mailingAddress.city).toBe("BLOOMINGDALE");
    expect(sample?.properties.zoningCode).toBe("AR-1");
    expect(sample?.properties.tax.marketValue).toBe(190511);
    expect(sample?.properties.tax.taxes).toBe(3964.85);
    expect(sample?.properties.lastSale).toEqual({ date: "1996-05-22", price: null, qualified: null });
    expect(sample?.properties.flu).toEqual({
      code: "Industrial",
      label: "Industrial",
      jurisdiction: "EFFINGHAM",
      source: "flum-20240903",
    });
    expect(sample?.properties.centroid[0]).toBeGreaterThan(-81.39);
    expect(sample?.properties.centroid[0]).toBeLessThan(-81.37);
    expect(sample?.properties.centroid[1]).toBeGreaterThan(32.1);
    expect(sample?.properties.centroid[1]).toBeLessThan(32.11);

    const linked = parcelAppraiserUrl({
      parcelId: "03320008",
      countyFips: "13103",
      appraiserUrl: sample?.properties.appraiserUrl,
    });
    expect(linked.href).toContain("AppID=666");
    expect(linked.label).toBe("Open this parcel in Effingham County qPublic");
    const search = parcelAppraiserUrl({ parcelId: "03320008", countyFips: "13103" });
    expect(search.href).toContain("App=EffinghamCountyGA");
    expect(search.label).toBe("Open Effingham County qPublic search");
  });
});
