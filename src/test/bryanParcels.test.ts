import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13029");

function loadFeatures(): ParcelFeature[] {
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(path.join(COUNTY, "tiles"))) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(COUNTY, "tiles", name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

describe("Bryan County GA parcels", () => {
  it("keeps the TOTALACRES extract and does not invent city future land use or opportunity zones", () => {
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
    expect(county.fips).toBe("13029");
    expect(county.markets).toEqual(["Savannah"]);
    expect(county.source).toBe("ga-bryan-property-details");
    expect(county.queryUrl).toContain("PropertyDetails/MapServer/0");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBe(2138);
    expect(county.dropped).toBe(94);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/TOTALACRES/);
    expect(gaps).toMatch(/Zoning\/MapServer\/0/);
    expect(gaps).toMatch(/ZONINGCODE/);
    expect(gaps).toMatch(/no city zoning FeatureServer/);
    expect(gaps).toMatch(/2023ComprehensivePlan\/MapServer\/4/);
    expect(gaps).toMatch(/city future land use was not invented/);
    expect(gaps).toMatch(/Sales stay null/);
    expect(gaps).toMatch(/Texas/);
    expect(gaps).toMatch(/Oklahoma/);
    expect(gaps).toMatch(/does not assign Opportunity Zone/);
    expect(gaps).toMatch(/2138 parcel ids kept/);
    expect(gaps).toMatch(/Pembroke 98/);
    expect(gaps).toMatch(/Richmond Hill 156/);
    expect(gaps).toMatch(/Future land use joined on 1880/);

    const features = loadFeatures();
    expect(features).toHaveLength(2138);
    const cities: Record<string, number> = {};
    let flu = 0;
    let cityFlu = 0;
    const zoned: Record<string, number> = {};
    for (const feature of features) {
      const props = feature.properties;
      expect(props.countyFips).toBe("13029");
      expect(props.marketIds).toEqual(["Savannah"]);
      expect(props.source).toBe("ga-bryan-property-details");
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.lastSale).toEqual({ date: null, price: null, qualified: null });
      expect(props.zoningCode).not.toBe("CITY");
      const [lon, lat] = props.centroid ?? [];
      expect(lon).toBeGreaterThan(-81.85);
      expect(lon).toBeLessThan(-81.05);
      expect(lat).toBeGreaterThan(31.7);
      expect(lat).toBeLessThan(32.3);
      expect(props.appraiserUrl ?? "").toContain("AppID=639");
      expect(props.appraiserUrl ?? "").toContain(encodeURIComponent(props.parcelId));
      const city = props.situsCity || "unincorporated";
      cities[city] = (cities[city] ?? 0) + 1;
      if (props.flu) {
        flu += 1;
        expect(props.situsCity).toBeNull();
        expect(props.flu.source).toBe("bryan-comp-plan-2023");
        expect(props.flu.jurisdiction).toBe("BRYAN");
      }
      if (props.situsCity && props.flu) cityFlu += 1;
      if (props.zoningCode) {
        const place = props.zoningDistrict?.split(":")[0] || "missing";
        zoned[place] = (zoned[place] ?? 0) + 1;
        if (props.situsCity) {
          expect(props.jurisdictionPrefix).toBe(props.situsCity.toUpperCase());
        } else {
          expect(props.jurisdictionPrefix).toBe("BRYAN");
        }
      }
    }
    expect(cities).toEqual({ Pembroke: 98, "Richmond Hill": 156, unincorporated: 1884 });
    expect(zoned).toEqual({ "Bryan County": 1884, Pembroke: 95, "Richmond Hill": 155 });
    expect(flu).toBe(1880);
    expect(cityFlu).toBe(0);

    const sample = features.find((feature) => feature.properties.parcelId === "07100201");
    expect(sample?.properties.acreage).toBe(32.64);
    expect(sample?.properties.ownerName).toBe("WOODLAND HAMMOCK LLC");
    expect(sample?.properties.situsAddress).toBeNull();
    expect(sample?.properties.situsCity).toBeNull();
    expect(sample?.properties.situsZip).toBe("31324");
    expect(sample?.properties.mailingAddress.city).toBe("RICHMOND HILL");
    expect(sample?.properties.zoningCode).toBe("A-5");
    expect(sample?.properties.zoningDistrict).toBe("Bryan County:A-5");
    expect(sample?.properties.tax.marketValue).toBe(675648);
    expect(sample?.properties.flu).toEqual({
      code: "Conservation",
      label: "Conservation",
      jurisdiction: "BRYAN",
      source: "bryan-comp-plan-2023",
    });
    expect(sample?.properties.centroid[0]).toBeGreaterThan(-81.22);
    expect(sample?.properties.centroid[0]).toBeLessThan(-81.21);
    expect(sample?.properties.centroid[1]).toBeGreaterThan(31.75);
    expect(sample?.properties.centroid[1]).toBeLessThan(31.76);

    const linked = parcelAppraiserUrl({
      parcelId: "07100201",
      countyFips: "13029",
      appraiserUrl: sample?.properties.appraiserUrl,
    });
    expect(linked.href).toContain("AppID=639");
    expect(linked.label).toBe("Open this parcel in Bryan County qPublic");
    const search = parcelAppraiserUrl({ parcelId: "07100201", countyFips: "13029" });
    expect(search.href).toContain("qpublic.net/ga/bryan");
    expect(search.label).toBe("Open Bryan County qPublic search");
  });
});
