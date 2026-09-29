import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

/** Anderson retry plus interim-list counties after Jasper that were not already complete and whose endpoint answered. */
const COUNTIES: Record<string, { name: string; min: number; sourceIncludes: string; urlIncludes: string; shelf: string }> = {
  "45007": { name: "Anderson", min: 11000, sourceIncludes: "sc-anderson-parcels-45007", urlIncludes: "NewPropertyViewer/MapServer/5", shelf: "Greenville" },
  "45055": { name: "Kershaw", min: 8000, sourceIncludes: "sc-kershaw-parcels-45055", urlIncludes: "Fairfield_Kershaw_Richland_Map_WFL1/FeatureServer/7", shelf: "Columbia" },
  "45057": { name: "Lancaster", min: 12000, sourceIncludes: "sc-lancaster-parcels-45057", urlIncludes: "LC_Parcels/FeatureServer/0", shelf: "Charlotte" },
  "45059": { name: "Laurens", min: 8000, sourceIncludes: "sc-laurens-parcels-45059", urlIncludes: "Pebble/TaxParcel/MapServer/5", shelf: "Greenville" },
  "45061": { name: "Lee", min: 3500, sourceIncludes: "sc-lee-parcels-45061", urlIncludes: "Web_Parcels/FeatureServer/0", shelf: "Columbia" },
  "45065": { name: "McCormick", min: 1600, sourceIncludes: "sc-mccormick-parcels-45065", urlIncludes: "Edgefield_McCormick_Greenwood_Web_Map_WFL1/FeatureServer/7", shelf: "Columbia" },
  "45067": { name: "Marion", min: 3300, sourceIncludes: "sc-marion-parcels-45067", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18", shelf: "Charleston" },
  "45069": { name: "Marlboro", min: 3200, sourceIncludes: "sc-marlboro-parcels-45069", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18", shelf: "Charleston" },
  "45071": { name: "Newberry", min: 6000, sourceIncludes: "sc-newberry-parcels-45071", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18", shelf: "Columbia" },
  "45073": { name: "Oconee", min: 8500, sourceIncludes: "sc-oconee-parcels-45073", urlIncludes: "PARCELDATA_owner/MapServer/1", shelf: "Greenville" },
  "45075": { name: "Orangeburg", min: 11000, sourceIncludes: "sc-orangeburg-parcels-45075", urlIncludes: "Main_Public_Tax_Parcel_Map_WFL1/FeatureServer/0", shelf: "Columbia" },
  "45077": { name: "Pickens", min: 8500, sourceIncludes: "sc-pickens-parcels-45077", urlIncludes: "Pickens_Open_data/FeatureServer/6", shelf: "Greenville" },
  "45079": { name: "Richland", min: 8000, sourceIncludes: "sc-richland-parcels-45079", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/8", shelf: "Columbia" },
  "45081": { name: "Saluda", min: 5200, sourceIncludes: "sc-saluda-parcels-45081", urlIncludes: "PublicWebsite_Pro/MapServer/4", shelf: "Columbia" },
  "45087": { name: "Union", min: 4000, sourceIncludes: "sc-union-parcels-45087", urlIncludes: "Lexington_Richland_Web_Map_WFL1/FeatureServer/18", shelf: "Greenville" },
  "45089": { name: "Williamsburg", min: 6500, sourceIncludes: "sc-williamsburg-parcels-45089", urlIncludes: "Georgetown_Williamsburg_Web_Map_WFL1/FeatureServer/4", shelf: "Charleston" },
  "45091": { name: "York", min: 10000, sourceIncludes: "sc-york-parcels-45091", urlIncludes: "Parcels/FeatureServer/0", shelf: "Charlotte" },
};

const EXISTING_SHELVES = new Set(["Charleston", "Charlotte", "Columbia", "Greenville", "Hilton Head", "Savannah"]);

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
  markets?: string[];
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

describe("South Carolina rural OZ batch 2 parcels", () => {
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
      expect(row.markets || []).toContain(target.shelf);
      expect((row.markets || []).every((market) => EXISTING_SHELVES.has(market))).toBe(true);
      expect(row.gaps.join(" ")).toMatch(/No Opportunity Zone status/);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade:\s*[A-F]|base flood elevation:\s*\d/i);
      expect(`${row.source} ${row.queryUrl}`.toLowerCase()).not.toMatch(/regrid|reportall/);
      expect(row.paLinkVerified).toBe(false);
      expect(row.appraiserSearchUrl || "").toMatch(/^https?:\/\//);
      if (row.gisViewerUrl) expect(row.gisViewerUrl).toMatch(/^https?:\/\//);
    }
  });

  it("leaves Calhoun unloaded, keeps Lexington and Spartanburg, and records the later Sumter retry", () => {
    expect(countyFile("45085")).toMatchObject({
      source: "sc-sumter-parcels-45085",
      coverage: "complete-gte-5ac",
      featureCount: 6759,
      markets: ["Columbia"],
    });
    expect(countyFile("45017")).toMatchObject({ coverage: "gap", featureCount: 0 });
    expect(countyFile("45063")).toMatchObject({
      source: "sc-lexington-property-4",
      coverage: "complete-gte-5ac",
      featureCount: 13975,
    });
    expect(countyFile("45083")).toMatchObject({
      source: "sc-spartanburg-cama-parcels",
      coverage: "complete-gte-5ac",
      featureCount: 16205,
    });
  });

  it("returns in-band Richland parcels for a viewport on the existing Columbia shelf", async () => {
    let sample: ParcelFeature | undefined;
    eachFeature("45079", (feature) => {
      sample ??= feature;
    });
    expect(sample).toBeTruthy();
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.marketIds).toContain("Columbia");
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const richland = page.collection.features.filter((item) => item.properties.countyFips === "45079");
    expect(richland.length).toBeGreaterThan(0);
    expect(richland.every((item) => item.properties.source === "sc-richland-parcels-45079")).toBe(true);
    expect(richland.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );
  });

  it("keeps distinct parcel ids, in-band acres, and does not copy one appraiser account", () => {
    const today = new Date().toISOString().slice(0, 10);
    const problems: string[] = [];
    for (const fips of Object.keys(COUNTIES)) {
      const ids = new Set<string>();
      const links = new Map<string, number>();
      let features = 0;
      eachFeature(fips, (item) => {
        features += 1;
        ids.add(item.properties.parcelId);
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
        const url = item.properties.appraiserUrl;
        if (url) links.set(url, (links.get(url) || 0) + 1);
      });
      if (ids.size !== features) problems.push(`${fips} distinct ${ids.size} of ${features}`);
      const repeated = [...links.values()].some((count) => count > 1);
      if (repeated) problems.push(`${fips} repeated appraiser url`);
      if (problems.length > 8) break;
    }
    expect(problems).toEqual([]);
  }, 120_000);

  it("stores Anderson owners, Richland sale dates, and Lee mailing cities", () => {
    let andersonOwners = 0;
    eachFeature("45007", (feature) => {
      if (feature.properties.ownerName) andersonOwners += 1;
    });
    expect(andersonOwners).toBeGreaterThan(10000);

    let richlandDates = 0;
    eachFeature("45079", (feature) => {
      if (feature.properties.lastSale?.date) richlandDates += 1;
    });
    expect(richlandDates).toBeGreaterThan(5000);

    let leeCities = 0;
    eachFeature("45061", (feature) => {
      if (feature.properties.mailingAddress?.city) leeCities += 1;
    });
    expect(leeCities).toBeGreaterThan(3000);
  });
});
