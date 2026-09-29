import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

/**
 * Pass-2 orders 26–47 with pass-1 status usable, minus Barrow and Bartow
 * (already complete) and Butts (Schneider WFS timed out).
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
    tax: "rest" | "partial" | "none";
    owner: boolean;
  }
> = {
  "13001": { name: "Appling", min: 4215, market: "Savannah", sourceIncludes: "ga-appling-parcels-13001", urlIncludes: "Appling_County_Wide_View/FeatureServer/19", paLinkVerified: false, tax: "none", owner: false },
  "13003": { name: "Atkinson", min: 1400, market: "Valdosta", sourceIncludes: "ga-atkinson-parcels-13003", urlIncludes: "Atkinson/PropertyInformation/MapServer/1", paLinkVerified: false, tax: "rest", owner: true },
  "13009": { name: "Baldwin", min: 3062, market: "Macon", sourceIncludes: "ga-baldwin-parcels-13009", urlIncludes: "Parcels_Feb2026/FeatureServer/0", paLinkVerified: false, tax: "none", owner: true },
  "13011": { name: "Banks", min: 4057, market: "Atlanta", sourceIncludes: "ga-banks-parcels-13011", urlIncludes: "Zoning_Base_WFL1/FeatureServer/10", paLinkVerified: false, tax: "none", owner: false },
  "13017": { name: "Ben Hill", min: 1962, market: "Valdosta", sourceIncludes: "ga-ben-hill-parcels-13017", urlIncludes: "BenHill/Property/MapServer/4", paLinkVerified: false, tax: "rest", owner: true },
  "13025": { name: "Brantley", min: 2980, market: "Valdosta", sourceIncludes: "ga-brantley-parcels-13025", urlIncludes: "Brantley_Parcels_view/FeatureServer/0", paLinkVerified: true, tax: "rest", owner: true },
  "13027": { name: "Brooks", min: 3009, market: "Valdosta", sourceIncludes: "ga-brooks-parcels-13027", urlIncludes: "Brooks/Boundaries/MapServer/0", paLinkVerified: false, tax: "rest", owner: true },
  "13031": { name: "Bulloch", min: 8833, market: "Savannah", sourceIncludes: "ga-bulloch-parcels-13031", urlIncludes: "Bullochparcels_CAMA/FeatureServer/1189", paLinkVerified: false, tax: "none", owner: true },
  "13039": { name: "Camden", min: 3218, market: "Savannah", sourceIncludes: "ga-camden-parcels-13039", urlIncludes: "2025_Tax_Parcels/FeatureServer/0", paLinkVerified: false, tax: "partial", owner: true },
  "13043": { name: "Candler", min: 2287, market: "Savannah", sourceIncludes: "ga-candler-parcels-13043", urlIncludes: "Candler_County_Wide_View/FeatureServer/18", paLinkVerified: false, tax: "none", owner: false },
  "13049": { name: "Charlton", min: 1704, market: "Valdosta", sourceIncludes: "ga-charlton-parcels-13049", urlIncludes: "Parcels_Charlton_County/FeatureServer/7", paLinkVerified: false, tax: "none", owner: false },
  "13053": { name: "Chattahoochee", min: 322, market: "Macon", sourceIncludes: "ga-chattahoochee-parcels-13053", urlIncludes: "ParcelsChattCo/FeatureServer/0", paLinkVerified: false, tax: "none", owner: true },
  "13061": { name: "Clay", min: 729, market: "Macon", sourceIncludes: "ga-clay-parcels-13061", urlIncludes: "Clay_County_Parcels_10_23/FeatureServer/0", paLinkVerified: true, tax: "rest", owner: true },
  "13069": { name: "Coffee", min: 4923, market: "Valdosta", sourceIncludes: "ga-coffee-parcels-13069", urlIncludes: "Coffee/CoffeeBackgroundLayers/MapServer/2", paLinkVerified: false, tax: "rest", owner: false },
  "13075": { name: "Cook", min: 2437, market: "Valdosta", sourceIncludes: "ga-cook-parcels-13075", urlIncludes: "Cook/Cook_Parcels/MapServer/0", paLinkVerified: true, tax: "rest", owner: true },
  "13079": { name: "Crawford", min: 2933, market: "Macon", sourceIncludes: "ga-crawford-parcels-13079", urlIncludes: "CrawfordCountyParcels_Jan2026/FeatureServer/0", paLinkVerified: false, tax: "none", owner: false },
  "13081": { name: "Crisp", min: 1873, market: "Macon", sourceIncludes: "ga-crisp-parcels-13081", urlIncludes: "CrispParcels/FeatureServer/0", paLinkVerified: true, tax: "rest", owner: true },
  "13087": { name: "Decatur", min: 3520, market: "Valdosta", sourceIncludes: "ga-decatur-parcels-13087", urlIncludes: "SmartGov_Parcel_Layer_6_2025/FeatureServer/0", paLinkVerified: false, tax: "none", owner: true },
  "13091": { name: "Dodge", min: 3733, market: "Macon", sourceIncludes: "ga-dodge-parcels-13091", urlIncludes: "Dodge_County_Wide_View/FeatureServer/38", paLinkVerified: false, tax: "none", owner: false },
};

const GA_SHELVES = new Set(["Atlanta", "Savannah", "Chattanooga", "Valdosta", "Macon", "Athens"]);

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

describe("Georgia rural OZ batch 2 parcels", () => {
  it("lists every loaded county on the Coverage manifest", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    const byFips = new Map(loaded.map((county) => [county.fips, county]));
    for (const [fips, target] of Object.entries(COUNTIES)) {
      expect(byFips.get(fips)).toEqual({ fips, name: target.name, state: "Georgia" });
      const row = countyFile(fips);
      expect(row.featureCount).toBeGreaterThanOrEqual(target.min);
      expect(row.coverage).toBe("complete-gte-5ac");
      expect(row.minAcres).toBe(5);
      expect(row.maxAcres).toBe(150);
      expect(row.state).toBe("Georgia");
      expect(row.markets.every((market) => GA_SHELVES.has(market))).toBe(true);
      expect(row.markets).toContain(target.market);
      expect(row.markets).toHaveLength(1);
      expect(row.source).toContain(target.sourceIncludes);
      expect(row.queryUrl).toContain(target.urlIncludes);
      expect(row.gaps.join(" ")).toMatch(/No Opportunity Zone status/);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade:\s*[A-F]|base flood elevation:\s*\d/i);
      expect(`${row.source} ${row.queryUrl}`.toLowerCase()).not.toMatch(/regrid|reportall/);
      expect(row.paLinkVerified).toBe(target.paLinkVerified);
      expect(row.appraiserSearchUrl || "").toMatch(/\{parcelId\}/);
      expect(row.gisViewerUrl || "").toMatch(/^https?:\/\//);
    }
    expect(countyFile("13013").featureCount).toBe(4251);
    expect(countyFile("13013").source).toBe("ga-barrow-parcels");
    expect(countyFile("13015").featureCount).toBe(7077);
    expect(countyFile("13015").source).toBe("ga-bartow-land");
    expect(countyFile("13035").featureCount).toBe(0);
    expect(countyFile("13035").coverage).toBe("gap");
    expect(countyFile("13053").gaps.join(" ")).toMatch(/Total_acre|geodesic|parsed/i);
    expect(countyFile("13039").gaps.join(" ")).toMatch(/Juvare_Parcels/);
    expect(Object.keys(index.markets).some((market) => /columbus|albany|augusta|macon-msa/i.test(market))).toBe(false);
  });

  it("keeps household income on ACS B19013_001E", () => {
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    expect(source).toMatch(/for=tract:\*|tract:\*/);
  });

  it("returns in-band Appling parcels for the Savannah shelf", async () => {
    let sample: ParcelFeature | undefined;
    eachFeature("13001", (feature) => {
      sample ??= feature;
    });
    expect(sample).toBeTruthy();
    expect(sample!.properties.countyName).toBe("Appling");
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.nearestRoad).toBeNull();
    expect(sample!.properties.incomeTract).toBeNull();
    expect(sample!.properties.marketIds).toEqual(["Savannah"]);
    expect(sample!.properties.state).toBe("Georgia");
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const appling = page.collection.features.filter((item) => item.properties.countyFips === "13001");
    expect(appling.length).toBeGreaterThan(0);
    expect(appling.every((item) => item.properties.source === "ga-appling-parcels-13001")).toBe(true);
    expect(appling.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );
  });

  it("keeps every batch parcel inside 5–150 acres with distinct ids and per-parcel appraiser links", () => {
    const today = new Date().toISOString().slice(0, 10);
    const problems: string[] = [];
    let camdenTax = 0;
    let applingTax = 0;
    let crispSale = 0;
    let crawfordSale = 0;
    const baked = new Map<string, number>();
    for (const [fips, target] of Object.entries(COUNTIES)) {
      const ids = new Set<string>();
      let owners = 0;
      let tax = 0;
      eachFeature(fips, (item) => {
        ids.add(item.properties.parcelId);
        const acres = item.properties.acreage;
        if (acres == null || acres < 5 || acres > 150) {
          problems.push(`${fips} ${item.properties.parcelId} acres ${acres}`);
        }
        if (item.properties.countyName !== target.name) {
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
        if (!url.includes("KeyValue=")) problems.push(`${fips} ${item.properties.parcelId} missing appraiser url`);
        if (url.includes("{parcelId}")) problems.push(`${fips} unfilled template`);
        baked.set(url, (baked.get(url) || 0) + 1);
        if (item.properties.ownerName) owners += 1;
        if (item.properties.tax?.marketValue) tax += 1;
        if (fips === "13039" && item.properties.tax?.marketValue) camdenTax += 1;
        if (fips === "13001" && item.properties.tax?.marketValue) applingTax += 1;
        if (fips === "13081" && (item.properties.lastSale?.price || item.properties.lastSale?.date)) crispSale += 1;
        if (fips === "13079" && (item.properties.lastSale?.price || item.properties.lastSale?.date)) crawfordSale += 1;
      });
      if (ids.size !== countyFile(fips).featureCount) {
        problems.push(`${fips} distinct ${ids.size} vs ${countyFile(fips).featureCount}`);
      }
      if (target.owner && owners === 0) problems.push(`${fips} owner missing`);
      if (!target.owner && owners !== 0) problems.push(`${fips} owner stamped ${owners}`);
      if (target.tax === "rest" && tax === 0) problems.push(`${fips} tax missing`);
      if (target.tax === "none" && tax !== 0) problems.push(`${fips} tax stamped ${tax}`);
      if (problems.length > 12) break;
    }
    const repeated = [...baked.entries()].filter(([, count]) => count >= 25);
    expect(problems).toEqual([]);
    expect(repeated).toEqual([]);
    expect(applingTax).toBe(0);
    expect(camdenTax).toBeGreaterThan(0);
    expect(camdenTax).toBeLessThan(3218);
    expect(crispSale).toBe(0);
    expect(crawfordSale).toBe(0);
  }, 300_000);
});
