import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

/** First 20 interim-list counties that were not already a complete 5–150 acre extract and whose card endpoint answered. */
const COUNTIES: Record<string, { name: string; min: number; sourceIncludes: string; urlIncludes: string }> = {
  "45001": { name: "Abbeville", min: 5000, sourceIncludes: "sc-abbeville-parcels-45001", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18" },
  "45003": { name: "Aiken", min: 14000, sourceIncludes: "sc-aiken-parcels-45003", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18" },
  "45005": { name: "Allendale", min: 1800, sourceIncludes: "sc-allendale-parcels-45005", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18" },
  "45009": { name: "Bamberg", min: 2900, sourceIncludes: "sc-bamberg-parcels-45009", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18" },
  "45011": { name: "Barnwell", min: 4000, sourceIncludes: "sc-barnwell-parcels-45011", urlIncludes: "ParcelData_ExportFeatures/FeatureServer/2" },
  "45021": { name: "Cherokee", min: 6000, sourceIncludes: "sc-cherokee-parcels-45021", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18" },
  "45023": { name: "Chester", min: 5000, sourceIncludes: "sc-chester-parcels-45023", urlIncludes: "Parcels_10_7_24/FeatureServer/0" },
  "45025": { name: "Chesterfield", min: 8000, sourceIncludes: "sc-chesterfield-parcels-45025", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18" },
  "45027": { name: "Clarendon", min: 6000, sourceIncludes: "sc-clarendon-parcels-45027", urlIncludes: "Clarendon_County_Map_WFL1/FeatureServer/9" },
  "45029": { name: "Colleton", min: 8000, sourceIncludes: "sc-colleton-parcels-45029", urlIncludes: "WebDataLayers/FeatureServer/11" },
  "45031": { name: "Darlington", min: 6000, sourceIncludes: "sc-darlington-parcels-45031", urlIncludes: "PARCELS/FeatureServer/1" },
  "45033": { name: "Dillon", min: 3300, sourceIncludes: "sc-dillon-parcels-45033", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18" },
  "45037": { name: "Edgefield", min: 5500, sourceIncludes: "sc-edgefield-parcels-45037", urlIncludes: "Edgefield_McCormick_Greenwood_Web_Map_WFL1/FeatureServer/9" },
  "45039": { name: "Fairfield", min: 4800, sourceIncludes: "sc-fairfield-parcels-45039", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18" },
  "45041": { name: "Florence", min: 9500, sourceIncludes: "sc-florence-parcels-45041", urlIncludes: "County_Tax_Parcel/FeatureServer/0" },
  "45043": { name: "Georgetown", min: 3700, sourceIncludes: "sc-georgetown-parcels-45043", urlIncludes: "GCGIS_OpenData/FeatureServer/2" },
  "45047": { name: "Greenwood", min: 5000, sourceIncludes: "sc-greenwood-parcels-45047", urlIncludes: "Parcels_Search_and_Select/MapServer/0" },
  "45049": { name: "Hampton", min: 3200, sourceIncludes: "sc-hampton-parcels-45049", urlIncludes: "Parcels_Published_view/FeatureServer/1" },
  "45051": { name: "Horry", min: 11000, sourceIncludes: "sc-horry-parcels-45051", urlIncludes: "HorryCountyGIS_GS/MapServer/24" },
  "45053": { name: "Jasper", min: 3400, sourceIncludes: "sc-jasper-parcels-45053", urlIncludes: "Parcel_Cama_HDV/FeatureServer/0" },
};

type CountyManifest = {
  name: string;
  fips: string;
  state: string;
  featureCount: number;
  coverage: string;
  minAcres: number;
  maxAcres: number;
  source: string;
  queryUrl: string;
  gaps: string[];
  path: string;
  paLinkVerified?: boolean;
  appraiserSearchUrl?: string | null;
  gisViewerUrl?: string | null;
};

function countyFile(fips: string): CountyManifest {
  return JSON.parse(
    readFileSync(path.join("data/fixtures/market-parcels/counties", fips, "county.json"), "utf8"),
  ) as CountyManifest;
}

function eachFeature(fips: string, visit: (feature: ParcelFeature) => void) {
  const row = countyFile(fips);
  const tiles = readdirSync(row.path).filter((name) => name.endsWith(".geojson"));
  expect(tiles.length).toBeGreaterThan(0);
  for (const tile of tiles) {
    const collection = JSON.parse(readFileSync(path.join(row.path, tile), "utf8")) as ParcelCollection;
    for (const feature of collection.features) visit(feature);
  }
}

function propertyKeys(value: unknown, into: string[]) {
  if (!value || typeof value !== "object") return;
  if (Array.isArray(value)) {
    for (const item of value) propertyKeys(item, into);
    return;
  }
  for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
    into.push(key);
    propertyKeys(child, into);
  }
}

describe("South Carolina rural OZ batch 1 parcels", () => {
  it("lists every batch county on the Coverage manifest", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    const byFips = new Map(loaded.map((county) => [county.fips, county]));
    for (const [fips, target] of Object.entries(COUNTIES)) {
      expect(byFips.get(fips)).toEqual({ fips, name: target.name, state: "South Carolina" });
      const row = countyFile(fips);
      expect(row.featureCount).toBeGreaterThanOrEqual(target.min);
      expect(row.coverage).toBe("complete-gte-5ac");
      expect(row.minAcres).toBe(5);
      expect(row.maxAcres).toBe(150);
      expect(row.source).toContain(target.sourceIncludes);
      expect(row.queryUrl).toContain(target.urlIncludes);
      expect(row.gaps.join(" ")).toMatch(/No Opportunity Zone status/);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade:\s*[A-F]|base flood elevation:\s*\d/i);
      expect(`${row.source} ${row.queryUrl}`.toLowerCase()).not.toMatch(/regrid|reportall/);
      expect(row.paLinkVerified).toBe(false);
      expect(row.appraiserSearchUrl || "").toMatch(/^https?:\/\//);
      expect(row.gisViewerUrl || "").toMatch(/^https?:\/\//);
    }
  });

  it("keeps the existing Berkeley extract", () => {
    const berkeley = countyFile("45015");
    expect(berkeley).toMatchObject({
      source: "sc-berkeley-addr-muni",
      coverage: "complete-gte-5ac",
      featureCount: 7886,
    });
  });

  it("keeps household income on ACS B19013_001E", () => {
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    expect(source).toMatch(/for=tract:\*|tract:\*/);
  });

  it("stores summed Barnwell and Jasper values and does not promote Florence building value", () => {
    let barnwellMarket = 0;
    let barnwellTaxable = 0;
    eachFeature("45011", (feature) => {
      if ((feature.properties.tax?.marketValue ?? 0) > 0) barnwellMarket += 1;
      if ((feature.properties.tax?.taxableValue ?? 0) > 0) barnwellTaxable += 1;
    });
    expect(barnwellMarket).toBeGreaterThan(1000);
    expect(barnwellTaxable).toBeGreaterThan(1000);

    let jasperMarket = 0;
    let jasperTaxable = 0;
    eachFeature("45053", (feature) => {
      if ((feature.properties.tax?.marketValue ?? 0) > 0) jasperMarket += 1;
      if ((feature.properties.tax?.taxableValue ?? 0) > 0) jasperTaxable += 1;
    });
    expect(jasperMarket).toBeGreaterThan(1000);
    expect(jasperTaxable).toBeGreaterThan(1000);
    let spacedJasperLinks = 0;
    eachFeature("45053", (feature) => {
      const url = feature.properties.appraiserUrl || "";
      if (!url.startsWith("https://") || url.includes(" ")) spacedJasperLinks += 1;
    });
    expect(spacedJasperLinks).toBe(0);

    const florenceMarket: string[] = [];
    eachFeature("45041", (feature) => {
      if (feature.properties.tax?.marketValue != null) florenceMarket.push(feature.properties.parcelId);
    });
    expect(florenceMarket).toEqual([]);
  });

  it("returns in-band Edgefield parcels for a viewport on the existing Columbia shelf", async () => {
    let sample: ParcelFeature | undefined;
    eachFeature("45037", (feature) => {
      sample ??= feature;
    });
    expect(sample).toBeTruthy();
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.marketIds).toContain("Columbia");
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const edgefield = page.collection.features.filter((item) => item.properties.countyFips === "45037");
    expect(edgefield.length).toBeGreaterThan(0);
    expect(edgefield.every((item) => item.properties.source === "sc-edgefield-parcels-45037")).toBe(true);
    expect(edgefield.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );
  });

  it("keeps every batch parcel inside 5–150 acres with no future sale or contact fields", () => {
    const today = new Date().toISOString().slice(0, 10);
    const problems: string[] = [];
    for (const fips of Object.keys(COUNTIES)) {
      eachFeature(fips, (item) => {
        const acres = item.properties.acreage;
        if (acres == null || acres < 5 || acres > 150) {
          problems.push(`${fips} ${item.properties.parcelId} acres ${acres}`);
        }
        const sold = item.properties.lastSale?.date;
        if (sold && sold > today) problems.push(`${fips} ${item.properties.parcelId} sale ${sold}`);
        const keys: string[] = [];
        propertyKeys(item.properties, keys);
        if (keys.some((key) => /phone|e-?mail|ssn/i.test(key))) {
          problems.push(`${fips} ${item.properties.parcelId} keys ${keys.join(" ")}`);
        }
        if (item.properties.opportunityZone != null || item.properties.oz2Eligibility != null) {
          problems.push(`${fips} ${item.properties.parcelId} oz`);
        }
      });
      if (problems.length > 8) break;
    }
    expect(problems).toEqual([]);
  }, 120_000);
});
