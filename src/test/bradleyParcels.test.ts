import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import zoningConfigJson from "../../data/zoning-config.json";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature, ZoningConfig } from "../lib/types";
import { findZoningHit } from "../lib/zoning";

const zoningConfig = zoningConfigJson as ZoningConfig;

const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47011/county.json");
const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties/47011/tiles");

function loadBradley(): { meta: Record<string, unknown>; features: ParcelFeature[] } {
  const meta = JSON.parse(readFileSync(countyPath, "utf8")) as Record<string, unknown>;
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(tileDir)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tileDir, name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return { meta, features };
}

describe("Bradley County TN parcels", () => {
  const { meta, features } = loadBradley();

  it("keeps Cleveland inside Bradley on Census FIPS 47011", () => {
    expect(meta.fips).toBe("47011");
    expect(meta.name).toBe("Bradley");
    expect(meta.state).toBe("Tennessee");
    expect(meta.markets).toEqual(["Chattanooga"]);
    expect(meta.coverage).toBe("complete-gte-5ac");
    expect(meta.source).toBe("tn-cleveland-parcels-impact-47011");
    expect(String(meta.queryUrl)).toContain("OperationalLayersPRO/MapServer/2");
    expect(meta.minAcres).toBe(5);
    expect(meta.maxAcres).toBe(150);
    expect(meta.featureCount).toBe(features.length);
    expect(Number(meta.featureCount)).toBeGreaterThan(6000);
    expect(Number(meta.sourceCount)).toBeGreaterThan(Number(meta.featureCount));
    const gaps = (meta.gaps as string[]).join(" ");
    expect(gaps).toContain("City of Cleveland stays in Bradley");
    expect(gaps).toContain("47011");
    expect(gaps).toContain("ZONECLASS");
    expect(gaps).toContain("Charleston");
    expect(gaps).toContain("CAMA");
    expect(gaps).toContain("Future land use");
    expect(gaps).toContain("Opportunity Zone");
    expect(gaps).toContain("not 47107");
  });

  it("uses JUR 006 GISLINK ids inside the acreage band and does not invent zones", () => {
    expect(features.length).toBeGreaterThan(0);
    for (const feature of features) {
      const props = feature.properties;
      expect(props.countyFips).toBe("47011");
      expect(props.id.startsWith("47011:")).toBe(true);
      expect(props.parcelId.startsWith("006")).toBe(true);
      expect(props.parcelId.startsWith("007")).toBe(false);
      expect(props.parcelId.startsWith("011")).toBe(false);
      expect(props.marketIds).toEqual(["Chattanooga"]);
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.flu).toBeNull();
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.tax.assessedValue).toBeNull();
      expect(props.tax.taxableValue).toBeNull();
      expect(props.source).toBe("tn-cleveland-parcels-impact-47011");
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThan(-85.35);
      expect(lon).toBeLessThan(-84.55);
      expect(lat).toBeGreaterThan(34.9);
      expect(lat).toBeLessThan(35.4);
      if (props.jurisdictionPrefix !== "CLEVELAND") {
        expect(props.zoningDistrict == null || props.zoningDistrict.startsWith("CAMA first-pass")).toBe(true);
      }
      if (props.jurisdictionPrefix === "CHARLESTON") {
        expect(props.situsCity).toBe("Charleston");
      }
      if (props.jurisdictionPrefix === "CLEVELAND") {
        expect(props.situsCity).toBe("Cleveland");
      }
      expect(findZoningHit(props.zoningCode, props.zoningDistrict, zoningConfig)).toBeNull();
    }
  });

  it("links Bradley parcels to TPAD instead of a Florida appraiser", () => {
    const link = parcelAppraiserUrl({
      parcelId: "006034F J 02400",
      countyFips: "47011",
      appraiserUrl: "https://assessment.cot.tn.gov/TPAD/Parcel/GIS?GISlink=006034F%20J%2002400",
    });
    expect(link.label).toBe("Open Bradley County parcel in TPAD");
    expect(link.href).toContain("assessment.cot.tn.gov");
    expect(link.href).not.toContain("ocpafl.org");
  });
});
