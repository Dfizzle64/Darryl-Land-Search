import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const countyDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties");

function readCounty(fips: string) {
  return JSON.parse(readFileSync(path.join(countyDir, fips, "county.json"), "utf8")) as {
    source: string;
    queryUrl: string;
    featureCount: number;
    coverage: string;
    primaryId?: string;
    gaps: string[];
    municipalities?: { id: string; role: string; flu: string | null; parcelCount: number }[];
    followUps?: { fips: string; status: string }[];
    fluJoinedCount?: number;
    zoningJoinedCount?: number;
  };
}

function durhamFeatures(): ParcelFeature[] {
  const tiles = path.join(countyDir, "37063", "tiles");
  const files = readdirSync(tiles).filter((name) => name.endsWith(".geojson"));
  const features: ParcelFeature[] = [];
  for (const file of files) {
    const collection = JSON.parse(readFileSync(path.join(tiles, file), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

describe("Durham County market parcels", () => {
  const county = readCounty("37063");

  it("uses the county property layer and REID, with OneMap only as fallback", () => {
    expect(county.source).toBe("durham-property-37063");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.queryUrl).toContain("PublicServices/Property/MapServer/4");
    expect(county.primaryId).toBe("REID");
    expect(county.featureCount).toBeGreaterThan(4000);
    expect(county.gaps.join(" ")).toMatch(/REID/);
    expect(county.gaps.join(" ")).toMatch(/ImageServer/);
    expect(county.gaps.join(" ")).toMatch(/cntyfips='063'/);
    expect(county.followUps?.map((item) => item.fips).sort()).toEqual(["37135", "37183"]);
    expect(county.followUps?.every((item) => item.status === "nc-onemap")).toBe(true);
    expect(county.municipalities?.map((item) => item.id)).toEqual([
      "durham-city",
      "durham-county",
      "chapel-hill",
      "morrisville",
      "raleigh",
      "cary",
    ]);
    expect(county.fluJoinedCount).toBeGreaterThan(0);
    expect(county.zoningJoinedCount).toBeGreaterThan(0);
  });

  it("keeps Wake and Orange on NC OneMap with a follow-up hook", () => {
    for (const fips of ["37183", "37135"]) {
      const row = readCounty(fips);
      expect(row.source).toBe(`nc-onemap-${fips}`);
      expect(row.gaps.join(" ")).toMatch(/Follow-up/);
      expect(row.gaps.join(" ")).toMatch(/triangle_municipalities/);
    }
  });

  it("stamps 5–150 acre parcels with owner, zoning, and future land use", () => {
    const features = durhamFeatures();
    expect(features.length).toBe(county.featureCount);
    const withZoning = features.filter((feature) => feature.properties.zoningCode);
    const withFlu = features.filter((feature) => feature.properties.flu?.code);
    const tips = features.filter((feature) =>
      ["chapel-hill", "morrisville", "raleigh", "cary"].includes(feature.properties.municipalityId || ""),
    );
    expect(withZoning.length).toBeGreaterThan(features.length * 0.9);
    expect(withFlu.length).toBeGreaterThan(1000);
    expect(tips.length).toBeGreaterThan(0);
    for (const feature of features) {
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.countyFips).toBe("37063");
      expect(feature.properties.state).toBe("North Carolina");
      expect(feature.properties.source).toBe("durham-property-37063");
      expect(feature.properties.id).toBe(`37063:${feature.properties.parcelId}`);
      expect(feature.properties.parcelId).toBeTruthy();
      expect(feature.properties.appraiserUrl).toMatch(/taxcama\.dconc\.gov/);
      expect(feature.properties.municipalityId).toBeTruthy();
      expect(feature.properties.municipality).toBeTruthy();
    }
    for (const feature of tips) {
      expect(feature.properties.flu).toBeNull();
      expect((feature.properties.dataGaps || []).join(" ")).toMatch(/future land use|ImageServer/i);
    }
    const linked = parcelAppraiserUrl({
      parcelId: features[0].properties.parcelId,
      countyFips: "37063",
      appraiserUrl: features[0].properties.appraiserUrl,
    });
    expect(linked.label).toBe("Open Durham County property summary");
    expect(linked.href).toContain("taxcama.dconc.gov");
  });
});
