import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import { PARCEL_MIN_ZOOM } from "../lib/parcelVisibility";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

/** Pass-2 orders 48–69 with usable pass-1 status, excluding counties already complete or still unreachable. */
const COUNTIES: Record<
  string,
  {
    name: string;
    count: number;
    shelf: string;
    sourceIncludes: string;
    urlIncludes: string;
    paLinkVerified: boolean;
  }
> = {
  "13093": { name: "Dooly", count: 2140, shelf: "Macon", sourceIncludes: "ga-dooly-parcels-13093", urlIncludes: "Dooly_County_Parcels/FeatureServer/14", paLinkVerified: true },
  "13101": { name: "Echols", count: 630, shelf: "Valdosta", sourceIncludes: "ga-echols-parcels-13101", urlIncludes: "Echols/echols_parcels/MapServer/0", paLinkVerified: false },
  "13107": { name: "Emanuel", count: 4498, shelf: "Macon", sourceIncludes: "ga-emanuel-parcels-13107", urlIncludes: "Emanuel_CountyWide_GeoData_View/FeatureServer/20", paLinkVerified: true },
  "13109": { name: "Evans", count: 1740, shelf: "Savannah", sourceIncludes: "ga-evans-parcels-13109", urlIncludes: "Evan_CountyWide_GeoData_View/FeatureServer/16", paLinkVerified: false },
  "13115": { name: "Floyd", count: 7575, shelf: "Chattanooga", sourceIncludes: "ga-floyd-parcels-13115", urlIncludes: "CurrentParcels/FeatureServer/0", paLinkVerified: true },
  "13127": { name: "Glynn", count: 2099, shelf: "Savannah", sourceIncludes: "ga-glynn-parcels-13127", urlIncludes: "Parcels/Parcels/FeatureServer/0", paLinkVerified: false },
  "13133": { name: "Greene", count: 3009, shelf: "Athens", sourceIncludes: "ga-greene-parcels-13133", urlIncludes: "Parcel_Regions_w_WinGAP_view/FeatureServer/0", paLinkVerified: true },
  "13139": { name: "Hall", count: 6904, shelf: "Atlanta", sourceIncludes: "ga-hall-parcels-13139", urlIncludes: "HallCo_Addr_Pcl_Rds/MapServer/1", paLinkVerified: false },
  "13153": { name: "Houston", count: 3691, shelf: "Macon", sourceIncludes: "ga-houston-parcels-13153", urlIncludes: "HoustonCoParcels_withOwner/FeatureServer/0", paLinkVerified: false },
  "13155": { name: "Irwin", count: 2088, shelf: "Valdosta", sourceIncludes: "ga-irwin-parcels-13155", urlIncludes: "Irwin/ParcelInformation/MapServer/5", paLinkVerified: false },
  "13157": { name: "Jackson", count: 6659, shelf: "Atlanta", sourceIncludes: "ga-jackson-parcels-13157", urlIncludes: "Tax_Parcels/FeatureServer/9", paLinkVerified: false },
  "13161": { name: "Jeff Davis", count: 2603, shelf: "Valdosta", sourceIncludes: "ga-jeff-davis-parcels-13161", urlIncludes: "JeffDavis_County_Wide_GeoData_view/FeatureServer/19", paLinkVerified: false },
  "13173": { name: "Lanier", count: 1263, shelf: "Valdosta", sourceIncludes: "ga-lanier-parcels-13173", urlIncludes: "Lanier_Parcels/FeatureServer/23", paLinkVerified: false },
  "13175": { name: "Laurens", count: 6986, shelf: "Macon", sourceIncludes: "ga-laurens-parcels-13175", urlIncludes: "Laurens_County_Wide_View/FeatureServer/25", paLinkVerified: false },
  "13179": { name: "Liberty", count: 2269, shelf: "Savannah", sourceIncludes: "ga-liberty-parcels-13179", urlIncludes: "ParcelsService/FeatureServer/15", paLinkVerified: false },
  "13183": { name: "Long", count: 1662, shelf: "Savannah", sourceIncludes: "ga-long-parcels-13183", urlIncludes: "Long/Property_Data/MapServer/0", paLinkVerified: false },
  "13187": { name: "Lumpkin", count: 3872, shelf: "Atlanta", sourceIncludes: "ga-lumpkin-parcels-13187", urlIncludes: "Lumpkin_2025Parcels/FeatureServer/0", paLinkVerified: false },
  "13189": { name: "McDuffie", count: 2638, shelf: "Athens", sourceIncludes: "ga-mcduffie-parcels-13189", urlIncludes: "Public/MapServer/10", paLinkVerified: false },
};

const GA_SHELVES = new Set(["Atlanta", "Savannah", "Chattanooga", "Valdosta", "Macon", "Athens"]);

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
  markets: string[];
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

function keyValue(url: string): string {
  const query = new URL(url).searchParams.get("KeyValue") || "";
  return decodeURIComponent(query.replace(/\+/g, "%20"));
}

describe("Georgia rural OZ batch 3 parcels", () => {
  it("loads orders 48-69 at zoom 10 on existing Georgia shelves", async () => {
    expect(PARCEL_MIN_ZOOM).toBe(10);
    const census = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(census).toContain("B19013_001E");
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    const byFips = new Map(loaded.map((county) => [county.fips, county]));
    let total = 0;
    for (const [fips, target] of Object.entries(COUNTIES)) {
      expect(byFips.get(fips)).toEqual({ fips, name: target.name, state: "Georgia" });
      const row = countyFile(fips);
      expect(row.featureCount).toBe(target.count);
      total += row.featureCount;
      expect(row.coverage).toBe("complete-gte-5ac");
      expect(row.minAcres).toBe(5);
      expect(row.maxAcres).toBe(150);
      expect(row.state).toBe("Georgia");
      expect(row.markets).toEqual([target.shelf]);
      expect(row.markets.every((market) => GA_SHELVES.has(market))).toBe(true);
      expect(row.source).toContain(target.sourceIncludes);
      expect(row.queryUrl).toContain(target.urlIncludes);
      expect(`${row.source} ${row.queryUrl}`.toLowerCase()).not.toMatch(/regrid|reportall|naip/);
      expect(row.gaps.join(" ")).toMatch(/No Opportunity Zone status/);
      expect(row.gaps.join(" ")).not.toMatch(/designated QOZ|school grade:\s*[A-F]|base flood elevation:\s*\d/i);
      expect(row.paLinkVerified).toBe(target.paLinkVerified);
      expect(row.appraiserSearchUrl || "").toContain("{parcelId}");
      expect(row.gisViewerUrl || "").toMatch(/^https?:\/\//);
    }
    expect(total).toBe(62326);
    expect(Object.keys(index.markets).some((market) => /columbus|augusta|albany|rome|brunswick/i.test(market))).toBe(
      false,
    );
  });

  it("leaves Fayette, Henry, and Lowndes on their existing extracts and does not load Grady", () => {
    expect(countyFile("13113")).toMatchObject({
      source: "ga-fayette-parcels",
      coverage: "complete-gte-5ac",
      featureCount: 4725,
      markets: ["Atlanta"],
    });
    expect(countyFile("13151")).toMatchObject({
      source: "ga-henry-parcels",
      coverage: "complete-gte-5ac",
      featureCount: 7418,
      markets: ["Atlanta"],
    });
    expect(countyFile("13185")).toMatchObject({
      source: "ga-lowndes-valor-taxparcels",
      coverage: "complete-gte-5ac",
      featureCount: 5815,
      markets: ["Valdosta"],
    });
    expect(existsSync(path.join("data/fixtures/market-parcels/counties/13131"))).toBe(false);
  });

  it("returns in-band Floyd parcels for the Chattanooga shelf", async () => {
    let sample: ParcelFeature | undefined;
    eachFeature("13115", (feature) => {
      sample ??= feature;
    });
    expect(sample).toBeTruthy();
    expect(sample!.properties.countyName).toBe("Floyd");
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.marketIds).toEqual(["Chattanooga"]);
    expect(sample!.properties.state).toBe("Georgia");
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const floyd = page.collection.features.filter((item) => item.properties.countyFips === "13115");
    expect(floyd.length).toBeGreaterThan(0);
    expect(floyd.every((item) => item.properties.source === "ga-floyd-parcels-13115")).toBe(true);
    expect(floyd.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );
  });

  it("keeps distinct ids, in-band acres, per-parcel appraiser links, and no contact fields", () => {
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
        if (acres == null || acres < 5 || acres > 150) problems.push(`${fips} ${item.properties.parcelId} acres ${acres}`);
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
        if (!url) {
          problems.push(`${fips} ${item.properties.parcelId} missing appraiser url`);
        } else {
          links.set(url, (links.get(url) || 0) + 1);
          const key = keyValue(url);
          if (fips === "13179") {
            if (!key.includes("_") || key === item.properties.parcelId) {
              problems.push(`${fips} ${item.properties.parcelId} pin ${key}`);
            }
          } else if (key !== item.properties.parcelId) {
            problems.push(`${fips} ${item.properties.parcelId} key ${key}`);
          }
          if (fips === "13127" && !key.includes("-")) problems.push(`${fips} ${item.properties.parcelId} lost dashes`);
        }
      });
      if (ids.size !== features || features !== COUNTIES[fips].count) {
        problems.push(`${fips} distinct ${ids.size} of ${features}`);
      }
      if ([...links.values()].some((count) => count >= 25)) problems.push(`${fips} repeated appraiser url`);
      if (problems.length > 8) break;
    }
    expect(problems).toEqual([]);
  }, 180_000);

  it("stores WinGAP land value, Hall privacy, and empty Lanier and Floyd sale fields", () => {
    let doolyLand = 0;
    let doolyAssessed = 0;
    eachFeature("13093", (feature) => {
      const tax = feature.properties.tax as { assessedValue: number | null; landValue?: number | null };
      if (tax.assessedValue != null) doolyAssessed += 1;
      if (tax.landValue != null) doolyLand += 1;
    });
    expect(doolyAssessed).toBe(0);
    expect(doolyLand).toBeGreaterThan(1000);

    let hallHidden = 0;
    let hallLeak = 0;
    eachFeature("13139", (feature) => {
      if (feature.properties.ownerName) return;
      hallHidden += 1;
      const mail = feature.properties.mailingAddress;
      if (mail?.line1 || mail?.line2 || mail?.city || mail?.state || mail?.zip) hallLeak += 1;
    });
    expect(hallHidden).toBe(4);
    expect(hallLeak).toBe(0);

    let lanierOwners = 0;
    eachFeature("13173", (feature) => {
      if (feature.properties.ownerName) lanierOwners += 1;
    });
    expect(lanierOwners).toBe(0);
    expect(countyFile("13173").gaps.join(" ")).toMatch(/LASTNAME/);

    let floydSales = 0;
    eachFeature("13115", (feature) => {
      if (feature.properties.lastSale?.date || feature.properties.lastSale?.price) floydSales += 1;
    });
    expect(floydSales).toBe(0);
    expect(countyFile("13127").gaps.join(" ")).toMatch(/square feet/);
  });
});
