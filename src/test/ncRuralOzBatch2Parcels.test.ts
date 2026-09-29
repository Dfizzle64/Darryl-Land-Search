import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

/**
 * Next 20 pass-1 rows starting at Hertford with status verified or fixed that
 * were not already a complete 5–150 acre extract.
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
  "37091": { name: "Hertford", min: 2701, market: "Raleigh-Durham", sourceIncludes: "nc-hertford-parcels-37091", urlIncludes: "TaxParcels/MapServer/2", paLinkVerified: false },
  "37093": { name: "Hoke", min: 3202, market: "Raleigh-Durham", sourceIncludes: "nc-hoke-parcels-37093", urlIncludes: "June2025/FeatureServer/1", paLinkVerified: true },
  "37095": { name: "Hyde", min: 2394, market: "Wilmington", sourceIncludes: "nc-hyde-parcels-37095", urlIncludes: "Hyde_AGOL/FeatureServer/3", paLinkVerified: false },
  "37099": { name: "Jackson", min: 6732, market: "Asheville", sourceIncludes: "nc-jackson-parcels-37099", urlIncludes: "Tax_Admin/Parcels/FeatureServer/0", paLinkVerified: true },
  "37103": { name: "Jones", min: 2349, market: "Wilmington", sourceIncludes: "nc-jones-parcels-37103", urlIncludes: "Jones_Bitek/FeatureServer/0", paLinkVerified: true },
  "37107": { name: "Lenoir", min: 5242, market: "Wilmington", sourceIncludes: "nc-lenoir-parcels-37107", urlIncludes: "Parcels_Zoning_Addressing/FeatureServer/6", paLinkVerified: false },
  "37111": { name: "McDowell", min: 1736, market: "Asheville", sourceIncludes: "nc-mcdowell-parcels-37111", urlIncludes: "NC/McDowell/MapServer/2", paLinkVerified: true },
  "37113": { name: "Macon", min: 6321, market: "Asheville", sourceIncludes: "nc-macon-parcels-37113", urlIncludes: "JustParcels/MapServer/0", paLinkVerified: true },
  "37115": { name: "Madison", min: 6897, market: "Asheville", sourceIncludes: "nc-madison-parcels-37115", urlIncludes: "2025_Parcels/FeatureServer/19", paLinkVerified: false },
  "37117": { name: "Martin", min: 3561, market: "Raleigh-Durham", sourceIncludes: "nc-martin-parcels-37117", urlIncludes: "TaxParcels/FeatureServer/0", paLinkVerified: false },
  "37121": { name: "Mitchell", min: 3835, market: "Asheville", sourceIncludes: "nc-mitchell-parcels-37121", urlIncludes: "WebMapNew/MapServer/12", paLinkVerified: false },
  "37123": { name: "Montgomery", min: 5957, market: "Charlotte", sourceIncludes: "nc-montgomery-parcels-37123", urlIncludes: "NC/Montgomery/MapServer/1", paLinkVerified: true },
  "37125": { name: "Moore", min: 12638, market: "Raleigh-Durham", sourceIncludes: "nc-moore-parcels-37125", urlIncludes: "Tax/Tax_Layers/FeatureServer/0", paLinkVerified: true },
  "37131": { name: "Northampton", min: 4840, market: "Raleigh-Durham", sourceIncludes: "nc-northampton-parcels-37131", urlIncludes: "NorthamptonService/FeatureServer/8", paLinkVerified: false },
  "37137": { name: "Pamlico", min: 3154, market: "Wilmington", sourceIncludes: "nc-pamlico-parcels-37137", urlIncludes: "Pamlico_ParcelService/FeatureServer/5", paLinkVerified: true },
  "37139": { name: "Pasquotank", min: 2779, market: "Raleigh-Durham", sourceIncludes: "nc-pasquotank-parcels-37139", urlIncludes: "PasquotankCountyNC_20260101/FeatureServer/0", paLinkVerified: true },
  "37147": { name: "Pitt", min: 7800, market: "Raleigh-Durham", sourceIncludes: "nc-pitt-parcels-37147", urlIncludes: "PittOpenData/CadastralPitt/MapServer/0", paLinkVerified: false },
  "37149": { name: "Polk", min: 4683, market: "Asheville", sourceIncludes: "nc-polk-parcels-37149", urlIncludes: "23uf7jKvz6SRPFWJ/arcgis/rest/services/Parcels/FeatureServer/0", paLinkVerified: true },
  "37153": { name: "Richmond", min: 5219, market: "Charlotte", sourceIncludes: "nc-richmond-parcels-37153", urlIncludes: "GISWebsite/ParcelViewer/MapServer/12", paLinkVerified: false },
  "37155": { name: "Robeson", min: 12583, market: "Wilmington", sourceIncludes: "nc-robeson-parcels-37155", urlIncludes: "Robeson_County_Parcels/FeatureServer/0", paLinkVerified: true },
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

describe("North Carolina rural OZ batch 2 parcels", () => {
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
      expect(row.markets).toHaveLength(1);
      expect(row.source).toContain(target.sourceIncludes);
      expect(row.queryUrl).toContain(target.urlIncludes);
      expect(row.gaps.join(" ")).toMatch(/No Opportunity Zone status/);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade:\s*[A-F]|base flood elevation:\s*\d/i);
      expect(`${row.source} ${row.queryUrl}`.toLowerCase()).not.toMatch(/regrid|reportall/);
      expect(row.paLinkVerified).toBe(target.paLinkVerified);
      expect(row.appraiserSearchUrl || "").toMatch(/^https?:\/\//);
      expect(row.gisViewerUrl || "").toMatch(/^https?:\/\//);
    }
    expect(countyFile("37099").gaps.join(" ")).toMatch(/resultRecordCount/);
    expect(countyFile("37093").gaps.join(" ")).toMatch(/June2025/);
    expect(countyFile("37155").gaps.join(" ")).toMatch(/land and improvement/);
    expect(Object.keys(index.markets).some((market) => /fayetteville/i.test(market))).toBe(false);
  });

  it("keeps household income on ACS B19013_001E", () => {
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    expect(source).toMatch(/for=tract:\*|tract:\*/);
  });

  it("returns in-band Hertford parcels for the Raleigh-Durham shelf", async () => {
    let sample: ParcelFeature | undefined;
    eachFeature("37091", (feature) => {
      sample ??= feature;
    });
    expect(sample).toBeTruthy();
    expect(sample!.properties.countyName).toBe("Hertford");
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.nearestRoad).toBeNull();
    expect(sample!.properties.incomeTract).toBeNull();
    expect(sample!.properties.marketIds).toEqual(["Raleigh-Durham"]);
    expect(sample!.properties.state).toBe("North Carolina");
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const hertford = page.collection.features.filter((item) => item.properties.countyFips === "37091");
    expect(hertford.length).toBeGreaterThan(0);
    expect(hertford.every((item) => item.properties.source === "nc-hertford-parcels-37091")).toBe(true);
    expect(hertford.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );
  });

  it("keeps every batch parcel inside 5–150 acres with no future sale or contact fields", () => {
    const today = new Date().toISOString().slice(0, 10);
    const problems: string[] = [];
    let hokeOwners = 0;
    let pittDates = 0;
    const baked = new Map<string, number>();
    for (const fips of Object.keys(COUNTIES)) {
      eachFeature(fips, (item) => {
        const acres = item.properties.acreage;
        if (acres == null || acres < 5 || acres > 150) {
          problems.push(`${fips} ${item.properties.parcelId} acres ${acres}`);
        }
        if (item.properties.countyName !== COUNTIES[fips].name) {
          problems.push(`${fips} name ${item.properties.countyName}`);
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
        if (/\d{6,}/.test(url)) baked.set(url, (baked.get(url) || 0) + 1);
        if (fips === "37093" && item.properties.ownerName) hokeOwners += 1;
        if (fips === "37147" && sold) pittDates += 1;
      });
      if (problems.length > 8) break;
    }
    const repeated = [...baked.entries()].filter(([, count]) => count >= 25);
    expect(problems).toEqual([]);
    expect(repeated).toEqual([]);
    expect(hokeOwners).toBe(0);
    expect(pittDates).toBeGreaterThan(4000);
  }, 240_000);
});
