import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

/**
 * First 20 pass-1 rows with status verified or fixed that were not already a
 * complete 5–150 acre extract. Buncombe and Henderson were already live.
 */
const COUNTIES: Record<
  string,
  {
    name: string;
    min: number;
    market: string;
    sourceIncludes: string;
    urlIncludes: string;
    paLinkVerified: boolean;
  }
> = {
  "37003": { name: "Alexander", min: 5900, market: "Charlotte", sourceIncludes: "nc-alexander-parcels-37003", urlIncludes: "Website_map/MapServer/26", paLinkVerified: true },
  "37005": { name: "Alleghany", min: 3500, market: "Winston-Salem", sourceIncludes: "nc-alleghany-parcels-37005", urlIncludes: "NC/Alleghany/MapServer/11", paLinkVerified: true },
  "37009": { name: "Ashe", min: 8800, market: "Asheville", sourceIncludes: "nc-ashe-parcels-37009", urlIncludes: "OpenData/TaxParcel/MapServer/0", paLinkVerified: false },
  "37011": { name: "Avery", min: 3800, market: "Asheville", sourceIncludes: "nc-avery-parcels-37011", urlIncludes: "Avery_AGOL/FeatureServer/21", paLinkVerified: true },
  "37013": { name: "Beaufort", min: 7900, market: "Wilmington", sourceIncludes: "nc-beaufort-parcels-37013", urlIncludes: "Beaufort_Service/FeatureServer/4", paLinkVerified: false },
  "37015": { name: "Bertie", min: 4300, market: "Raleigh-Durham", sourceIncludes: "nc-bertie-parcels-37015", urlIncludes: "Bertie_Parcel_Viewer/FeatureServer/4", paLinkVerified: true },
  "37017": { name: "Bladen", min: 8000, market: "Wilmington", sourceIncludes: "nc-bladen-parcels-37017", urlIncludes: "BladenCounty/MapServer/1", paLinkVerified: true },
  "37023": { name: "Burke", min: 7700, market: "Asheville", sourceIncludes: "nc-burke-parcels-37023", urlIncludes: "ProdParcelViewFC/MapServer/0", paLinkVerified: true },
  "37027": { name: "Caldwell", min: 7900, market: "Asheville", sourceIncludes: "nc-caldwell-parcels-37027", urlIncludes: "NCOnemap/NCOneMap/FeatureServer/45", paLinkVerified: false },
  "37031": { name: "Carteret", min: 3100, market: "Wilmington", sourceIncludes: "nc-carteret-parcels-37031", urlIncludes: "Layers/Parceldata/FeatureServer/0", paLinkVerified: false },
  "37033": { name: "Caswell", min: 5100, market: "Raleigh-Durham", sourceIncludes: "nc-caswell-parcels-37033", urlIncludes: "NC/Caswell/MapServer/9", paLinkVerified: true },
  "37039": { name: "Cherokee", min: 6100, market: "Asheville", sourceIncludes: "nc-cherokee-parcels-37039", urlIncludes: "OfficeView/MapServer/1", paLinkVerified: true },
  "37041": { name: "Chowan", min: 2000, market: "Raleigh-Durham", sourceIncludes: "nc-chowan-parcels-37041", urlIncludes: "Chowan_Feature_Service/FeatureServer/0", paLinkVerified: true },
  "37049": { name: "Craven", min: 5800, market: "Wilmington", sourceIncludes: "nc-craven-parcels-37049", urlIncludes: "JustParcels/MapServer/0", paLinkVerified: false },
  "37055": { name: "Dare", min: 1900, market: "Wilmington", sourceIncludes: "nc-dare-parcels-37055", urlIncludes: "gis_polygons/FeatureServer/0", paLinkVerified: true },
  "37065": { name: "Edgecombe", min: 4100, market: "Raleigh-Durham", sourceIncludes: "nc-edgecombe-parcels-37065", urlIncludes: "webmap/MapServer/10", paLinkVerified: false },
  "37075": { name: "Graham", min: 1800, market: "Asheville", sourceIncludes: "nc-graham-parcels-37075", urlIncludes: "GrahamAGOL/FeatureServer/6", paLinkVerified: true },
  "37079": { name: "Greene", min: 3400, market: "Raleigh-Durham", sourceIncludes: "nc-greene-parcels-37079", urlIncludes: "Greene_Service/FeatureServer/4", paLinkVerified: false },
  "37083": { name: "Halifax", min: 6200, market: "Raleigh-Durham", sourceIncludes: "nc-halifax-parcels-37083", urlIncludes: "OpenGov_RR_Layers/FeatureServer/22", paLinkVerified: false },
  "37087": { name: "Haywood", min: 5200, market: "Asheville", sourceIncludes: "nc-haywood-parcels-37087", urlIncludes: "SmartGov/SmartGovTaxView/FeatureServer/0", paLinkVerified: true },
};

const NC_SHELVES = new Set(["Asheville", "Charlotte", "Raleigh-Durham", "Wilmington", "Winston-Salem"]);

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

describe("North Carolina rural OZ batch 1 parcels", () => {
  it("lists every batch county on the Coverage manifest", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    const byFips = new Map(loaded.map((county) => [county.fips, county]));
    for (const [fips, target] of Object.entries(COUNTIES)) {
      expect(byFips.get(fips)).toEqual({ fips, name: target.name, state: "North Carolina" });
      const row = countyFile(fips);
      expect(row.featureCount).toBeGreaterThanOrEqual(target.min);
      expect(row.coverage).toBe("complete-gte-5ac");
      expect(row.minAcres).toBe(5);
      expect(row.maxAcres).toBe(150);
      expect(row.state).toBe("North Carolina");
      expect(row.markets.every((market) => NC_SHELVES.has(market))).toBe(true);
      expect(row.markets).toContain(target.market);
      expect(row.source).toContain(target.sourceIncludes);
      expect(row.queryUrl).toContain(target.urlIncludes);
      expect(row.gaps.join(" ")).toMatch(/No Opportunity Zone status/);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade:\s*[A-F]|base flood elevation:\s*\d/i);
      expect(`${row.source} ${row.queryUrl}`.toLowerCase()).not.toMatch(/regrid|reportall/);
      expect(row.paLinkVerified).toBe(target.paLinkVerified);
      expect(row.appraiserSearchUrl || "").toMatch(/^https?:\/\//);
      expect(row.gisViewerUrl || "").toMatch(/^https?:\/\//);
    }
    expect(countyFile("37003").gaps.join(" ")).toMatch(/orderByFields/);
    expect(countyFile("37003").gaps.join(" ")).toMatch(/PROPERTY 99999/);
    expect(countyFile("37009").gaps.join(" ")).toMatch(/resultRecordCount/);
  });

  it("leaves Buncombe and Henderson on their existing complete extracts", () => {
    expect(countyFile("37021")).toMatchObject({
      source: "nc-buncombe-opendata-37021",
      coverage: "complete-gte-5ac",
      featureCount: 10523,
    });
    expect(countyFile("37089")).toMatchObject({
      source: "nc-henderson-parcels-37089",
      coverage: "complete-gte-5ac",
      featureCount: 6270,
    });
  });

  it("keeps household income on ACS B19013_001E", () => {
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    expect(source).toMatch(/for=tract:\*|tract:\*/);
  });

  it("returns in-band Craven parcels for the Wilmington shelf", async () => {
    let sample: ParcelFeature | undefined;
    eachFeature("37049", (feature) => {
      sample ??= feature;
    });
    expect(sample).toBeTruthy();
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.nearestRoad).toBeNull();
    expect(sample!.properties.incomeTract).toBeNull();
    expect(sample!.properties.marketIds).toContain("Wilmington");
    expect(sample!.properties.state).toBe("North Carolina");
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const craven = page.collection.features.filter((item) => item.properties.countyFips === "37049");
    expect(craven.length).toBeGreaterThan(0);
    expect(craven.every((item) => item.properties.source === "nc-craven-parcels-37049")).toBe(true);
    expect(craven.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );
  });

  it("keeps every batch parcel inside 5–150 acres with no future sale or contact fields", () => {
    const today = new Date().toISOString().slice(0, 10);
    const problems: string[] = [];
    let chowanMarket = 0;
    let bladenSampleAccount = 0;
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
        if (item.properties.nearestRoad != null) problems.push(`${fips} ${item.properties.parcelId} aadt`);
        const url = item.properties.appraiserUrl || "";
        if (fips === "37017" && /ownerID=0539346&parcelID=0018189/i.test(url)) bladenSampleAccount += 1;
        if (fips === "37041" && item.properties.tax?.marketValue != null) chowanMarket += 1;
      });
      if (problems.length > 8) break;
    }
    expect(problems).toEqual([]);
    expect(chowanMarket).toBe(0);
    expect(bladenSampleAccount).toBe(1);
  }, 180_000);
});
