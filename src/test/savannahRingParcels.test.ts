import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

function loadCounty(fips: string): { meta: Record<string, unknown>; features: ParcelFeature[] } {
  const root = path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips);
  const meta = JSON.parse(readFileSync(path.join(root, "county.json"), "utf8")) as Record<string, unknown>;
  const features: ParcelFeature[] = [];
  const tiles = path.join(root, "tiles");
  for (const name of readdirSync(tiles)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return { meta, features };
}

describe("Bryan County GA parcels", () => {
  const { meta, features } = loadCounty("13029");

  it("keeps Bryan County, Georgia in the Savannah 5–150 acre band", () => {
    expect(meta.fips).toBe("13029");
    expect(meta.name).toBe("Bryan");
    expect(meta.state).toBe("Georgia");
    expect(meta.markets).toEqual(["Savannah"]);
    expect(meta.source).toBe("ga-bryan-property-details");
    expect(String(meta.queryUrl)).toContain("PropertyDetails/MapServer/0");
    expect(meta.coverage).toBe("complete-gte-5ac");
    expect(meta.featureCount).toBe(features.length);
    expect(Number(meta.featureCount)).toBeGreaterThan(2000);
    const gaps = (meta.gaps as string[]).join(" ");
    expect(gaps).toMatch(/Beacon/);
    expect(gaps).toMatch(/MAVCURR/);
    expect(gaps).toMatch(/Texas/);
    expect(gaps).toMatch(/SAGIS/);
    expect(gaps).toMatch(/Opportunity Zone/);
    for (const feature of features) {
      const props = feature.properties;
      expect(props.countyFips).toBe("13029");
      expect(props.id.startsWith("13029:")).toBe(true);
      expect(props.marketIds).toEqual(["Savannah"]);
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.lastSale).toEqual({ date: null, price: null, qualified: null });
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.zoningCode).not.toBe("CITY");
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-81.8);
      expect(lon).toBeLessThan(-81.05);
      expect(lat).toBeGreaterThan(31.65);
      expect(lat).toBeLessThan(32.3);
    }
  });

  it("links Bryan parcels to the Georgia Beacon record, not a Texas county", () => {
    const link = parcelAppraiserUrl({
      parcelId: "07100201",
      countyFips: "13029",
      appraiserUrl: "https://beacon.schneidercorp.com/Application.aspx?AppID=639&LayerID=11303&PageTypeID=4&KeyValue=07100201",
    });
    expect(link.href).toContain("AppID=639");
    expect(link.href).not.toContain("texas");
    expect(link.label).toContain("Bryan");
  });
});

describe("Effingham County GA parcels", () => {
  const { meta, features } = loadCounty("13103");

  it("keeps Effingham County, Georgia parcels and does not invent assessed value or sale quality", () => {
    expect(meta.fips).toBe("13103");
    expect(meta.name).toBe("Effingham");
    expect(meta.state).toBe("Georgia");
    expect(meta.markets).toEqual(["Savannah"]);
    expect(meta.source).toBe("ga-effingham-parcels-2024");
    expect(String(meta.queryUrl)).toContain("Parcels2024");
    expect(meta.coverage).toBe("complete-gte-5ac");
    expect(meta.featureCount).toBe(features.length);
    expect(Number(meta.featureCount)).toBeGreaterThan(5000);
    const gaps = (meta.gaps as string[]).join(" ");
    expect(gaps).toMatch(/ParcelUpdate/);
    expect(gaps).toMatch(/qualified/);
    expect(gaps).toMatch(/Illinois/);
    expect(gaps).toMatch(/Opportunity Zone/);
    let priced = 0;
    let dated = 0;
    let zoned = 0;
    let flu = 0;
    for (const feature of features) {
      const props = feature.properties;
      expect(props.countyFips).toBe("13103");
      expect(props.id.startsWith("13103:")).toBe(true);
      expect(props.marketIds).toEqual(["Savannah"]);
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.lastSale.qualified).toBeNull();
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-81.6);
      expect(lon).toBeLessThan(-81);
      expect(lat).toBeGreaterThan(31.95);
      expect(lat).toBeLessThan(32.6);
      if (props.lastSale.price) priced += 1;
      if (props.lastSale.date) dated += 1;
      if (props.zoningCode) zoned += 1;
      if (props.flu?.code) flu += 1;
    }
    expect(dated).toBeGreaterThan(features.length * 0.8);
    expect(priced).toBeGreaterThan(1000);
    expect(priced).toBeLessThan(features.length);
    expect(zoned).toBeGreaterThan(features.length * 0.9);
    expect(flu).toBeGreaterThan(1000);
    expect(flu).toBeLessThan(features.length);
  });

  it("links Effingham parcels to the Georgia qPublic app", () => {
    const link = parcelAppraiserUrl({ parcelId: "02010002", countyFips: "13103" });
    expect(link.href).toContain("EffinghamCountyGA");
    expect(link.label).toContain("Effingham");
  });
});
