import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection } from "../lib/types";

/** Card targets for the 20 rural OZ Florida counties in this batch. */
const COUNTIES: Record<string, { name: string; min: number; sourceIncludes: string; urlIncludes: string }> = {
  "12005": { name: "Bay", min: 4500, sourceIncludes: "fl-bay-test-parcels-12005", urlIncludes: "TEST_Parcels/FeatureServer/1" },
  "12009": { name: "Brevard", min: 6500, sourceIncludes: "fl-brevard-accela-12009", urlIncludes: "AccelaGIS_Layers_WKID2881/MapServer/5" },
  "12013": { name: "Calhoun", min: 3000, sourceIncludes: "fl-fdor-cadastral-2025-12013", urlIncludes: "Florida_Statewide_Cadastral/FeatureServer/0" },
  "12019": { name: "Clay", min: 4400, sourceIncludes: "fl-clay-parcels-lgim-12019", urlIncludes: "Parcels_LGIM/MapServer/0" },
  "12021": { name: "Collier", min: 13000, sourceIncludes: "fl-collier-parceljoin", urlIncludes: "Parcels/FeatureServer/42" },
  "12023": { name: "Columbia", min: 9000, sourceIncludes: "fl-columbia-parcels-12023", urlIncludes: "Parcels_and_Addresses/MapServer/2" },
  "12039": { name: "Gadsden", min: 5000, sourceIncludes: "fl-fdor-cadastral-2025-12039", urlIncludes: "Florida_Statewide_Cadastral/FeatureServer/0" },
  "12043": { name: "Glades", min: 2100, sourceIncludes: "fl-glades-agol-2026-06-12043", urlIncludes: "glades_parcels_2026_06_01/FeatureServer/0" },
  "12049": { name: "Hardee", min: 5000, sourceIncludes: "fl-hardee-infomap-12049", urlIncludes: "InfoMap/MapServer/5" },
  "12051": { name: "Hendry", min: 2900, sourceIncludes: "fl-hendry-parcels-feb2024-12051", urlIncludes: "Parcels_Feb2024/FeatureServer/0" },
  "12055": { name: "Highlands", min: 5500, sourceIncludes: "fl-highlands-pao-12055", urlIncludes: "PAO_Parcels/FeatureServer/0" },
  "12061": { name: "Indian River", min: 3600, sourceIncludes: "fl-ircpa-parcels-12061", urlIncludes: "Parcels_MS/MapServer/0" },
  "12063": { name: "Jackson", min: 10000, sourceIncludes: "fl-fdor-cadastral-2025-12063", urlIncludes: "Florida_Statewide_Cadastral/FeatureServer/0" },
  "12077": { name: "Liberty", min: 1400, sourceIncludes: "fl-fdor-cadastral-2025-12077", urlIncludes: "Florida_Statewide_Cadastral/FeatureServer/0" },
  "12087": { name: "Monroe", min: 5000, sourceIncludes: "fl-monroe-apo-parcels-0", urlIncludes: "mcgis4.monroecounty-fl.gov" },
  "12091": { name: "Okaloosa", min: 9500, sourceIncludes: "fl-panhandle-12091", urlIncludes: "internet_webgis/MapServer/17" },
  "12093": { name: "Okeechobee", min: 1500, sourceIncludes: "fl-okeechobee-tyler-12093", urlIncludes: "Tyler_Technologies_Display_Map/FeatureServer/2" },
  "12107": { name: "Putnam", min: 4000, sourceIncludes: "fl-putnam-parcels-pa-12107", urlIncludes: "putnam" },
  "12113": { name: "Santa Rosa", min: 8500, sourceIncludes: "fl-panhandle-12113", urlIncludes: "SRC_Basemap_Districts_Overlay/MapServer/1" },
  "12131": { name: "Walton", min: 8500, sourceIncludes: "fl-walton-energov-12131", urlIncludes: "EnerGov/FeatureServer/4" },
};

const PA_UNVERIFIED = ["12005", "12013", "12019", "12021", "12039", "12043", "12049", "12061", "12063", "12077", "12087", "12091", "12131"];

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

function firstFeature(fips: string) {
  const row = countyFile(fips);
  const tiles = readdirSync(row.path).filter((name) => name.endsWith(".geojson"));
  expect(tiles.length).toBeGreaterThan(0);
  const collection = JSON.parse(readFileSync(path.join(row.path, tiles[0]), "utf8")) as ParcelCollection;
  const feature = collection.features[0];
  expect(feature).toBeTruthy();
  return { row, tiles, collection, feature };
}

describe("rural OZ Florida batch 2 parcel shelves", () => {
  it("lists every batch-2 county on the Coverage manifest", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    const byFips = new Map(loaded.map((county) => [county.fips, county]));
    for (const [fips, target] of Object.entries(COUNTIES)) {
      expect(byFips.get(fips)).toEqual({ fips, name: target.name, state: "Florida" });
      const row = countyFile(fips);
      expect(row.featureCount).toBeGreaterThanOrEqual(target.min);
      expect(row.coverage).toBe("complete-gte-5ac");
      expect(row.minAcres).toBe(5);
      expect(row.maxAcres).toBe(150);
      expect(row.source).toContain(target.sourceIncludes);
      expect(row.queryUrl).toContain(target.urlIncludes);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade|base flood/i);
      expect(`${row.source} ${row.queryUrl}`.toLowerCase()).not.toMatch(/regrid|reportall/);
    }
  });

  it("keeps household income on ACS B19013_001E", () => {
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    expect(source).toMatch(/for=tract:\*|tract:\*/);
  });

  it("uses the card FDOR keys and does not ingest Hendry SSN columns", () => {
    expect(countyFile("12019").gaps.join(" ")).toMatch(/PIN_DSP/);
    expect(countyFile("12055").gaps.join(" ")).toMatch(/PARCELNO/);
    expect(countyFile("12055").gaps.join(" ")).toMatch(/STRAP/);
    expect(countyFile("12091").gaps.join(" ")).toMatch(/PATPCL_PIN/);
    expect(countyFile("12113").gaps.join(" ")).toMatch(/deduped on Parcel/i);
    expect(countyFile("12021").gaps.join(" ")).toMatch(/CAST\(TOTALACRES AS FLOAT\)/);
    expect(countyFile("12087").gaps.join(" ")).toMatch(/SEC\+TWP/);
    expect(countyFile("12087").gaps.join(" ")).toMatch(/DigiCert/);
    expect(countyFile("12093").gaps.join(" ")).toMatch(/LND_SQFOOT/);
    expect(countyFile("12107").gaps.join(" ")).toMatch(/LND_SQFOOT/);
    for (const fips of ["12063", "12039", "12013", "12077"]) {
      const row = countyFile(fips);
      expect(row.gaps.join(" ")).toMatch(/CO_NO=/);
      expect(row.queryUrl).toContain("Florida_Statewide_Cadastral");
    }
    const hendry = countyFile("12051");
    expect(hendry.gaps.join(" ")).toMatch(/SSN1/);
    const tiles = readdirSync(hendry.path).filter((name) => name.endsWith(".geojson"));
    const sample = JSON.parse(readFileSync(path.join(hendry.path, tiles[0]), "utf8")) as ParcelCollection;
    const blob = JSON.stringify(sample.features[0]).toLowerCase();
    expect(blob).not.toMatch(/ssn1|ssn2|ss1cd|ss2cd|confd/);
  });

  it("stores unverified property-appraiser patterns without requiring a live check", () => {
    for (const fips of PA_UNVERIFIED) {
      const row = countyFile(fips);
      expect(row.paLinkVerified).toBe(false);
      expect(row.appraiserSearchUrl || "").toMatch(/^https?:\/\//);
      const { feature } = firstFeature(fips);
      expect(feature.properties.appraiserUrl || "").toMatch(/^https?:\/\//);
      expect(feature.properties.gisViewerUrl || "").toMatch(/^https?:\/\//);
    }
  });

  it("returns 5–150 acre parcels for a Columbia viewport and clears future sales", async () => {
    const { feature } = firstFeature("12023");
    expect(feature.properties.opportunityZone).toBeNull();
    expect(feature.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(feature.properties.acreage).toBeLessThanOrEqual(150);
    const [lon, lat] = feature.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const columbia = page.collection.features.filter((item) => item.properties.countyFips === "12023");
    expect(columbia.length).toBeGreaterThan(0);
    expect(columbia.every((item) => item.properties.source === "fl-columbia-parcels-12023")).toBe(true);
    expect(
      columbia.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150),
    ).toBe(true);
  });

  it("keeps every batch-2 parcel inside 5–150 acres with no future sale or contact fields", () => {
    const today = new Date().toISOString().slice(0, 10);
    const problems: string[] = [];
    for (const fips of Object.keys(COUNTIES)) {
      const row = countyFile(fips);
      const tiles = readdirSync(row.path).filter((name) => name.endsWith(".geojson"));
      for (const tile of tiles) {
        const collection = JSON.parse(readFileSync(path.join(row.path, tile), "utf8")) as ParcelCollection;
        for (const item of collection.features) {
          const acres = item.properties.acreage;
          if (acres == null || acres < 5 || acres > 150) {
            problems.push(`${fips} ${item.properties.parcelId} acres ${acres}`);
          }
          const sold = item.properties.lastSale?.date;
          if (sold && sold > "2026-09-28" && sold > today) {
            problems.push(`${fips} ${item.properties.parcelId} sale ${sold}`);
          }
          const keys = Object.keys(item.properties).join(" ");
          if (/phone|email|ssn/i.test(keys)) {
            problems.push(`${fips} ${item.properties.parcelId} keys ${keys}`);
          }
          if (problems.length > 8) break;
        }
        if (problems.length > 8) break;
      }
      if (problems.length > 8) break;
    }
    expect(problems).toEqual([]);
  }, 120_000);
});
