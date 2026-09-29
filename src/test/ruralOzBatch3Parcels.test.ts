import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection } from "../lib/types";

/** Card targets for the 19 rural OZ Florida counties in this batch. */
const COUNTIES: Record<string, { name: string; min: number; sourceIncludes: string; urlIncludes: string }> = {
  "12001": { name: "Alachua", min: 12000, sourceIncludes: "fl-alachua-parcels35-12001", urlIncludes: "Parcels35/FeatureServer/0" },
  "12003": { name: "Baker", min: 2800, sourceIncludes: "fl-baker-parcels-web2-12003", urlIncludes: "parcels_web2/FeatureServer/0" },
  "12015": { name: "Charlotte", min: 3800, sourceIncludes: "fl-charlotte-ccgis-12015", urlIncludes: "CCGISLayers/MapServer/27" },
  "12033": { name: "Escambia", min: 8000, sourceIncludes: "fl-panhandle-12033", urlIncludes: "Individual_Layers/parcels/MapServer/0" },
  "12037": { name: "Franklin", min: 700, sourceIncludes: "fl-franklin-parcels-2023-12037", urlIncludes: "Parcels_2023/FeatureServer/0" },
  "12045": { name: "Gulf", min: 1100, sourceIncludes: "fl-gulf-gomaps4-12045", urlIncludes: "GoMaps4/MapServer/12" },
  "12057": { name: "Hillsborough", min: 11000, sourceIncludes: "fl-hillsborough-parcelpublishing-12", urlIncludes: "ParcelPublishing/MapServer/12" },
  "12065": { name: "Jefferson", min: 4500, sourceIncludes: "fl-jefferson-pa-parcels-12065", urlIncludes: "JC__PARCELS_view/FeatureServer/0" },
  "12071": { name: "Lee", min: 8000, sourceIncludes: "fl-lee-parceladdress", urlIncludes: "ParcelAddress/MapServer/0" },
  "12073": { name: "Leon", min: 4800, sourceIncludes: "fl-leon-overlay-parcel-12073", urlIncludes: "TLC_OverlayPar" },
  "12085": { name: "Martin", min: 3200, sourceIncludes: "fl-martin-geoweb-12085", urlIncludes: "base_map/MapServer/10" },
  "12086": { name: "Miami-Dade", min: 12000, sourceIncludes: "fl-miami-dade-landinformation-26", urlIncludes: "MD_LandInformation/MapServer/26" },
  "12089": { name: "Nassau", min: 4500, sourceIncludes: "fl-nassau-taxmap-12089", urlIncludes: "NassauCountyPublicTaxMap/MapServer/144" },
  "12095": { name: "Orange", min: 9000, sourceIncludes: "fl-orange-agol-open-data-12095", urlIncludes: "AGOL_Open_Data/MapServer/56" },
  "12097": { name: "Osceola", min: 5500, sourceIncludes: "osceola-parcels-12097", urlIncludes: "Parcels/MapServer/3" },
  "12111": { name: "St. Lucie", min: 4800, sourceIncludes: "fl-slc-parcels-12111", urlIncludes: "Parcel_Boundaries/FeatureServer/0" },
  "12127": { name: "Volusia", min: 10000, sourceIncludes: "fl-volusia-open-data-12127", urlIncludes: "Open_Data_3/FeatureServer/34" },
  "12129": { name: "Wakulla", min: 4000, sourceIncludes: "fl-wakulla-parcelm-12129", urlIncludes: "ParcelM/FeatureServer/0" },
  "12133": { name: "Washington", min: 6000, sourceIncludes: "fl-washington-agol-12133", urlIncludes: "WashingtonParcelsAGOL/FeatureServer/0" },
};

const PA_UNVERIFIED = ["12097", "12129", "12065", "12133", "12073", "12045", "12111", "12071"];

type CountyManifest = {
  name: string;
  fips: string;
  state: string;
  markets: string[];
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

describe("rural OZ Florida batch 3 parcel shelves", () => {
  it("lists every batch-3 county on the Coverage manifest", async () => {
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
      expect(row.queryUrl).not.toMatch(/MIL1|Washington_2024_DOR_Parcels|regrid|reportall/i);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade|base flood/i);
      expect(row.gaps.join(" ")).toMatch(/CO_NO=/);
    }
    const bigBend = index.markets["Big Bend"].counties.map((county) => county.fips);
    expect(bigBend).toEqual(expect.arrayContaining(["12037", "12045"]));
    const pensacola = index.markets.Pensacola.counties.map((county) => county.fips);
    expect(pensacola).toContain("12133");
    expect(index.markets["South Florida"].counties.map((county) => county.fips).sort()).toEqual([
      "12011",
      "12086",
      "12087",
      "12099",
    ]);
  });

  it("keeps household income on ACS B19013_001E", () => {
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    expect(source).toMatch(/for=tract:\*|tract:\*/);
  });

  it("uses the card FDOR keys and privacy notes", () => {
    const gaps = (fips: string) => countyFile(fips).gaps.join(" ");
    expect(gaps("12033")).toMatch(/CONFCD/);
    expect(gaps("12033")).toMatch(/REFERENCE/);
    expect(gaps("12065")).toMatch(/OwnerPhone/);
    expect(gaps("12073")).toMatch(/SECURE/);
    expect(gaps("12057")).toMatch(/Confidential/);
    expect(gaps("12057")).toMatch(/STRAP/);
    expect(gaps("12057")).toMatch(/MapServer/);
    expect(gaps("12071")).toMatch(/CONDOTYPE/);
    expect(gaps("12086")).toMatch(/FOLIO/);
    expect(gaps("12086")).toMatch(/PRIMARY_ZONE/);
    expect(gaps("12095")).toMatch(/BETWEEN/);
    expect(gaps("12085")).toMatch(/re-dashed/);
    expect(gaps("12127")).toMatch(/PID/);
    expect(gaps("12127")).toMatch(/DORPID/);
    expect(gaps("12037")).toMatch(/geodesic|shape/i);
    expect(gaps("12133")).toMatch(/Washington_2024/);
    expect(gaps("12097")).toMatch(/MapServer/);
    expect(gaps("12111")).toMatch(/ParcelID/);
    expect(gaps("12003")).toMatch(/removed/);
    expect(gaps("12089")).toMatch(/removed/);
    expect(countyFile("12097").queryUrl).toContain("MapServer/3");
    expect(countyFile("12097").queryUrl).not.toContain("FeatureServer/3");
    expect(countyFile("12057").queryUrl).toContain("MapServer/12");
    expect(countyFile("12057").queryUrl).not.toContain("FeatureServer/12");
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

  it("returns 5–150 acre Gulf parcels for the viewport that is already on screen", async () => {
    const { feature } = firstFeature("12045");
    expect(feature.properties.opportunityZone).toBeNull();
    expect(feature.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(feature.properties.acreage).toBeLessThanOrEqual(150);
    const [lon, lat] = feature.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const gulf = page.collection.features.filter((item) => item.properties.countyFips === "12045");
    expect(gulf.length).toBeGreaterThan(0);
    expect(gulf.every((item) => item.properties.source === "fl-gulf-gomaps4-12045")).toBe(true);
    expect(gulf.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(true);
    expect(gulf.every((item) => item.properties.marketIds?.includes("Big Bend"))).toBe(true);
  });

  it("keeps every batch-3 parcel inside 5–150 acres with no future sale or contact fields", () => {
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
          if (sold && sold > today) {
            problems.push(`${fips} ${item.properties.parcelId} sale ${sold}`);
          }
          const keys = Object.keys(item.properties).join(" ");
          if (/phone|email|ssn/i.test(keys)) {
            problems.push(`${fips} ${item.properties.parcelId} keys ${keys}`);
          }
          const blob = JSON.stringify(item.properties);
          if (/OwnerPhone|OwnerEmail/i.test(blob)) {
            problems.push(`${fips} ${item.properties.parcelId} contact`);
          }
          if (problems.length > 8) break;
        }
        if (problems.length > 8) break;
      }
      if (problems.length > 8) break;
    }
    expect(problems).toEqual([]);
  }, 180_000);
});
