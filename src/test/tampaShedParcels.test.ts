import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { getParcelProvider } from "../lib/data/adapters";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

type CountyRow = {
  fips: string;
  source: string;
  queryUrl: string;
  featureCount: number;
  coverage: string;
  gaps: string[];
  path: string;
  zoningJoinedCount: number;
  fluJoinedCount: number;
  municipalityCounts: Record<string, number>;
  rejected?: string[];
  overlays?: { role: string; url: string }[];
};

const root = process.cwd();

function countyRow(fips: string): CountyRow {
  const file = path.join(root, "data/fixtures/market-parcels/counties", fips, "county.json");
  expect(existsSync(file)).toBe(true);
  return JSON.parse(readFileSync(file, "utf8")) as CountyRow;
}

function sampleFeatures(relativeTiles: string, limit: number): ParcelFeature[] {
  const folder = path.join(root, relativeTiles);
  const files = readdirSync(folder).filter((name) => name.endsWith(".geojson"));
  expect(files.length).toBeGreaterThan(0);
  const features: ParcelFeature[] = [];
  for (const file of files) {
    const collection = JSON.parse(readFileSync(path.join(folder, file), "utf8")) as ParcelCollection;
    features.push(...collection.features);
    if (features.length >= limit) break;
  }
  return features.slice(0, limit);
}

describe("Tampa shed county cards", () => {
  it("wires Hillsborough, Pasco, Pinellas, and the Polk upgrade", () => {
    const sources = JSON.parse(readFileSync(path.join(root, "data/tampa-shed-parcel-sources.json"), "utf8")) as {
      counties: { fips: string; source: string; queryUrl: string }[];
    };
    for (const expected of sources.counties) {
      const row = countyRow(expected.fips);
      expect(row.source).toBe(expected.source);
      expect(row.queryUrl).toBe(expected.queryUrl);
      expect(row.coverage).toBe("complete-gte-5ac");
      expect(row.featureCount).toBeGreaterThan(1000);
      expect(row.path.startsWith(`data/fixtures/market-parcels/counties/${expected.fips}/`)).toBe(true);
      expect(row.path.includes("orlando-parcels")).toBe(false);
    }
  });

  it("rejects the Pasco hosted master-list subset and keeps city stubs out of zoning codes", () => {
    const pasco = countyRow("12101");
    expect(pasco.queryUrl).toContain("PascoMapper/Parcels/MapServer/7");
    expect(pasco.queryUrl).not.toContain("County_Master_Property_List");
    expect(pasco.rejected?.join(" ")).toContain("County_Master_Property_List");
    expect(pasco.featureCount).toBeGreaterThan(10_000);
    expect(pasco.gaps.join(" ")).toMatch(/placeholder/i);
    const features = sampleFeatures(pasco.path, 400);
    for (const feature of features) {
      const code = feature.properties.zoningCode?.toUpperCase();
      expect(code === "NPR" || code === "PR" || code === "SA").toBe(false);
      expect(feature.properties.municipality).toBeTruthy();
    }
    expect(pasco.municipalityCounts["Unincorporated Pasco"]).toBeGreaterThan(1000);
    expect(pasco.municipalityCounts["New Port Richey"]).toBeGreaterThan(0);
  });

  it("labels Hillsborough municipalities and does not treat VI as a qualified sale", () => {
    const hillsborough = countyRow("12057");
    expect(hillsborough.queryUrl).toContain("ParcelPublishing/FeatureServer/12");
    expect(hillsborough.zoningJoinedCount).toBeGreaterThan(8000);
    expect(hillsborough.fluJoinedCount).toBeGreaterThan(8000);
    for (const label of ["Tampa", "Temple Terrace", "Plant City", "Unincorporated Hillsborough"]) {
      expect(hillsborough.municipalityCounts[label]).toBeGreaterThan(20);
    }
    expect(hillsborough.gaps.join(" ")).toMatch(/VI/);
    const features = sampleFeatures(hillsborough.path, 80);
    for (const feature of features) {
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.municipality).toBeTruthy();
      expect(feature.properties.lastSale.qualified === "V" || feature.properties.lastSale.qualified === "I").toBe(false);
      expect(feature.properties.marketIds).toEqual(["Tampa"]);
    }
  });

  it("keeps Pinellas market value empty and labels St. Petersburg, Clearwater, and Largo", () => {
    const pinellas = countyRow("12103");
    expect(pinellas.queryUrl).toContain("PublicWebGIS/Parcels/MapServer/1");
    expect(pinellas.gaps.join(" ")).toMatch(/just\/market/i);
    expect(pinellas.municipalityCounts["St. Petersburg"]).toBeGreaterThan(20);
    expect(pinellas.municipalityCounts.Clearwater).toBeGreaterThan(20);
    expect(pinellas.municipalityCounts.Largo).toBeGreaterThan(20);
    expect(pinellas.municipalityCounts["Unincorporated Pinellas"]).toBeGreaterThan(20);
    const features = sampleFeatures(pinellas.path, 120);
    for (const feature of features) {
      expect(feature.properties.tax.marketValue).toBeNull();
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
    }
    const appraiser = parcelAppraiserUrl({ parcelId: "1", countyFips: "12103" });
    expect(appraiser.href).toContain("pcpao.org");
    expect(appraiser.label).toContain("Pinellas");
  });

  it("upgrades Polk parcels without inventing zoning districts", () => {
    const polk = countyRow("12105");
    expect(polk.queryUrl).toContain("Property_Appraiser/MapServer/134");
    expect(polk.path.includes("orlando-parcels")).toBe(false);
    expect(polk.zoningJoinedCount).toBe(0);
    expect(polk.fluJoinedCount).toBeGreaterThan(2000);
    expect(polk.gaps.join(" ")).toMatch(/zoning-district/i);
    expect(polk.gaps.join(" ")).toMatch(/Lakeland/i);
    expect(polk.rejected?.join(" ")).toContain("lakelandgov.net");
    const features = sampleFeatures(polk.path, 60);
    for (const feature of features) {
      expect(feature.properties.zoningCode).toBeNull();
      expect(feature.properties.marketIds?.includes("Orlando")).toBe(false);
      expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
      expect(feature.properties.municipality).toBeTruthy();
    }
    const orlandoTile = path.join(root, "data/fixtures/orlando-parcels/tiles/12105");
    expect(existsSync(orlandoTile)).toBe(true);
  });

  it("returns the Polk upgrade by id when the Orlando extract shares the parcel id", async () => {
    const parcel = await getParcelProvider().getParcel("12105:222601000000021030");
    expect(parcel?.properties.source).toBe("fl-polk-property-appraiser-134");
    expect(parcel?.properties.municipality).toBe("Kathleen");
    expect(parcel?.properties.zoningCode).toBeNull();
    expect(parcel?.properties.flu?.code).toBeTruthy();
    expect(parcel?.properties.marketIds).toEqual(["Tampa"]);
  });
});
