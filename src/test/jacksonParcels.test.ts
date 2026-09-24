import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY = path.join(process.cwd(), "data/fixtures/market-parcels/counties/13157");
const CITY_STUBS = new Set([
  "JEFFERSON",
  "COMMERCE",
  "HOSCHTON",
  "BRASELTON",
  "PENDERGRASS",
  "ARCADE",
  "NICHOLSON",
  "MAYSVILLE",
  "TALMO",
]);

function loadFeatures(): ParcelFeature[] {
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(path.join(COUNTY, "tiles"))) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(COUNTY, "tiles", name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

describe("Jackson County GA parcels", () => {
  it("keeps the TOTALACRES extract and does not invent sales or opportunity zones", () => {
    const county = JSON.parse(readFileSync(path.join(COUNTY, "county.json"), "utf8")) as {
      fips: string;
      source: string;
      queryUrl: string;
      featureCount: number;
      coverage: string;
      dropped: number;
      gaps: string[];
    };
    expect(county.fips).toBe("13157");
    expect(county.source).toBe("ga-jackson-tax-parcels-9");
    expect(county.queryUrl).toContain("Tax_Parcels/FeatureServer/9");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.featureCount).toBe(6674);
    expect(county.dropped).toBe(2);
    const gaps = county.gaps.join(" ");
    expect(gaps).toMatch(/TOTALACRES/);
    expect(gaps).toMatch(/acre_calc is not the filter/);
    expect(gaps).toMatch(/FMVRES \+ FMVCOM \+ FMVACC/);
    expect(gaps).toMatch(/AppID=797/);
    expect(gaps).toMatch(/Maysville has no zoning_maysville/);
    expect(gaps).toMatch(/ZONING_BRASELTON/);
    expect(gaps).toMatch(/NEGRC/);
    expect(gaps).toMatch(/Missouri/);
    expect(gaps).toMatch(/Jefferson Parish/);
    expect(gaps).toMatch(/LandPro/);
    expect(gaps).toMatch(/does not assign Opportunity Zone/);
    expect(gaps).toMatch(/6674 parcel ids kept/);
    expect(gaps).toMatch(/none 141/);
    expect(gaps).toMatch(/none 988/);

    const features = loadFeatures();
    expect(features).toHaveLength(6674);
    const zoning = {
      JEFFERSON: 0,
      COMMERCE: 0,
      HOSCHTON: 0,
      BRASELTON: 0,
      PENDERGRASS: 0,
      ARCADE: 0,
      NICHOLSON: 0,
      TALMO: 0,
      JACKSON: 0,
      none: 0,
    };
    const flu = {
      jefferson: 0,
      commerce: 0,
      hoschton: 0,
      braselton: 0,
      pendergrass: 0,
      arcade: 0,
      nicholson: 0,
      talmo: 0,
      county: 0,
      none: 0,
    };
    let maysville = 0;
    let sample: ParcelFeature | undefined;
    for (const feature of features) {
      const props = feature.properties;
      expect(props.countyFips).toBe("13157");
      expect(props.marketIds).toEqual(["Atlanta"]);
      expect(props.source).toBe("ga-jackson-tax-parcels-9");
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.lastSale).toEqual({ date: null, price: null, qualified: null });
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.situsZip).toBeNull();
      expect(CITY_STUBS.has((props.zoningCode || "").toUpperCase())).toBe(false);
      expect(props.zoningCode || "").not.toMatch(/FMV|REALPROP/);
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-83.9);
      expect(lon).toBeLessThan(-83.3);
      expect(lat).toBeGreaterThan(33.94);
      expect(lat).toBeLessThan(34.35);
      expect(props.appraiserUrl ?? "").toContain("App=JacksonCountyGA");
      expect(props.appraiserUrl ?? "").toContain(encodeURIComponent(props.parcelId));
      if (props.situsCity === "Maysville") {
        maysville += 1;
        expect(props.zoningCode).toBeNull();
        expect(props.flu).toBeNull();
      }
      const prefix = props.jurisdictionPrefix;
      if (
        prefix === "JEFFERSON" ||
        prefix === "COMMERCE" ||
        prefix === "HOSCHTON" ||
        prefix === "BRASELTON" ||
        prefix === "PENDERGRASS" ||
        prefix === "ARCADE" ||
        prefix === "NICHOLSON" ||
        prefix === "TALMO" ||
        prefix === "JACKSON"
      ) {
        zoning[prefix] += 1;
        expect(props.zoningCode).toBeTruthy();
      } else {
        zoning.none += 1;
        expect(props.zoningCode).toBeNull();
      }
      const fluSource = props.flu?.source;
      if (fluSource === "negrc-jefferson-420") flu.jefferson += 1;
      else if (fluSource === "negrc-commerce-418") flu.commerce += 1;
      else if (fluSource === "negrc-hoschton-419") flu.hoschton += 1;
      else if (fluSource === "negrc-braselton-417") flu.braselton += 1;
      else if (fluSource === "negrc-pendergrass-422") flu.pendergrass += 1;
      else if (fluSource === "negrc-arcade-414") flu.arcade += 1;
      else if (fluSource === "negrc-nicholson-421") flu.nicholson += 1;
      else if (fluSource === "negrc-talmo-425") flu.talmo += 1;
      else if (fluSource === "jackson-flu-15") {
        flu.county += 1;
        expect(props.flu?.jurisdiction).toBe("JACKSON");
        expect(CITY_STUBS.has((props.flu?.code || "").toUpperCase())).toBe(false);
      } else {
        flu.none += 1;
        expect(props.flu).toBeNull();
      }
      if (props.parcelId === "001    003A") sample = feature;
    }
    expect(zoning).toEqual({
      JEFFERSON: 410,
      COMMERCE: 197,
      HOSCHTON: 62,
      BRASELTON: 95,
      PENDERGRASS: 46,
      ARCADE: 93,
      NICHOLSON: 81,
      TALMO: 71,
      JACKSON: 5478,
      none: 141,
    });
    expect(flu).toEqual({
      jefferson: 406,
      commerce: 202,
      hoschton: 65,
      braselton: 96,
      pendergrass: 47,
      arcade: 93,
      nicholson: 84,
      talmo: 73,
      county: 4620,
      none: 988,
    });
    expect(maysville).toBe(51);
    expect(sample?.properties.acreage).toBe(7.5);
    expect(sample?.properties.ownerName).toBe("PARKER BARBARA LOUISE");
    expect(sample?.properties.situsAddress).toBe("282 COWART ROAD");
    expect(sample?.properties.situsCity).toBeNull();
    expect(sample?.properties.mailingAddress.city).toBe("COMMERCE");
    expect(sample?.properties.zoningCode).toBe("A2");
    expect(sample?.properties.jurisdictionPrefix).toBe("JACKSON");
    expect(sample?.properties.tax.marketValue).toBe(19091);
    expect(sample?.properties.flu).toEqual({ code: "R", label: "R", jurisdiction: "JACKSON", source: "jackson-flu-15" });
    expect(sample?.properties.centroid[0]).toBeGreaterThan(-83.41);
    expect(sample?.properties.centroid[0]).toBeLessThan(-83.39);
    expect(sample?.properties.centroid[1]).toBeGreaterThan(34.19);
    expect(sample?.properties.centroid[1]).toBeLessThan(34.2);

    const linked = parcelAppraiserUrl({
      parcelId: "001    003A",
      countyFips: "13157",
      appraiserUrl: sample?.properties.appraiserUrl,
    });
    expect(linked.href).toContain("App=JacksonCountyGA");
    expect(linked.href).toContain("PageType=Report");
    expect(linked.label).toBe("Open this parcel in Jackson County qPublic");
    const search = parcelAppraiserUrl({ parcelId: "001    003A", countyFips: "13157" });
    expect(search.href).toContain("PageType=Search");
    expect(search.label).toBe("Open Jackson County qPublic search");
  });
});
