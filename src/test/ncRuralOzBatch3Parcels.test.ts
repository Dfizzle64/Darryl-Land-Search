import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

/**
 * Remaining pass-1 rows starting at Rutherford, then the unloaded non-OZ
 * counties that still had a usable public parcel card.
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
  "37161": { name: "Rutherford", min: 11190, market: "Asheville", sourceIncludes: "nc-rutherford-parcels-37161", urlIncludes: "Addressing/MapServer/2", paLinkVerified: false },
  "37165": { name: "Scotland", min: 3348, market: "Charlotte", sourceIncludes: "nc-scotland-parcels-37165", urlIncludes: "Tax_Parcels_Scotland_County_view/FeatureServer/6", paLinkVerified: false },
  "37173": { name: "Swain", min: 2521, market: "Asheville", sourceIncludes: "nc-swain-parcels-37173", urlIncludes: "OperationalLayers/MapServer/4", paLinkVerified: true },
  "37175": { name: "Transylvania", min: 3926, market: "Asheville", sourceIncludes: "nc-transylvania-parcels-37175", urlIncludes: "Parcels/FeatureServer/2", paLinkVerified: false },
  "37177": { name: "Tyrrell", min: 1159, market: "Raleigh-Durham", sourceIncludes: "nc-tyrrell-parcels-37177", urlIncludes: "TyrrellService/FeatureServer/7", paLinkVerified: true },
  "37187": { name: "Washington", min: 1782, market: "Raleigh-Durham", sourceIncludes: "nc-washington-parcels-37187", urlIncludes: "Washington_Service/FeatureServer/9", paLinkVerified: true },
  "37189": { name: "Watauga", min: 7120, market: "Asheville", sourceIncludes: "nc-watauga-parcels-37189", urlIncludes: "TaxParcels/parcelsdbf/FeatureServer/0", paLinkVerified: true },
  "37193": { name: "Wilkes", min: 14195, market: "Winston-Salem", sourceIncludes: "nc-wilkes-parcels-37193", urlIncludes: "Parcels/MapServer/0", paLinkVerified: true },
  "37029": { name: "Camden", min: 1978, market: "Raleigh-Durham", sourceIncludes: "nc-camden-parcels-37029", urlIncludes: "Parcels/FeatureServer/1", paLinkVerified: false },
  "37043": { name: "Clay", min: 2425, market: "Asheville", sourceIncludes: "nc-clay-parcels-37043", urlIncludes: "Parcels04162026/FeatureServer/0", paLinkVerified: true },
  "37051": { name: "Cumberland", min: 8387, market: "Raleigh-Durham", sourceIncludes: "nc-cumberland-parcels-37051", urlIncludes: "Tax/Parcels/MapServer/0", paLinkVerified: true },
  "37053": { name: "Currituck", min: 2771, market: "Raleigh-Durham", sourceIncludes: "nc-currituck-parcels-37053", urlIncludes: "OperationalLayers/MapServer/20", paLinkVerified: false },
  "37073": { name: "Gates", min: 2326, market: "Raleigh-Durham", sourceIncludes: "nc-gates-parcels-37073", urlIncludes: "GatesParcelService/FeatureServer/5", paLinkVerified: true },
  "37143": { name: "Perquimans", min: 2873, market: "Raleigh-Durham", sourceIncludes: "nc-perquimans-parcels-37143", urlIncludes: "Perquimans_Service/FeatureServer/2", paLinkVerified: true },
  "37199": { name: "Yancey", min: 4517, market: "Asheville", sourceIncludes: "nc-yancey-parcels-37199", urlIncludes: "OperationalLayers2025/MapServer/0", paLinkVerified: true },
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

describe("North Carolina rural OZ batch 3 parcels", () => {
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
    expect(countyFile("37173").gaps.join(" ")).toMatch(/LegalLandType/);
    expect(countyFile("37043").gaps.join(" ")).toMatch(/LegalLandT/);
    expect(countyFile("37165").gaps.join(" ")).toMatch(/DeedStamps/);
    expect(countyFile("37199").gaps.join(" ")).toMatch(/card suffix/);
    expect(countyFile("37029").gaps.join(" ")).toMatch(/tax status is gap/);
    expect(Object.keys(index.markets).some((market) => /fayetteville|outer banks|boone|eastern nc/i.test(market))).toBe(
      false,
    );
  });

  it("keeps household income on ACS B19013_001E", () => {
    const source = readFileSync(path.join("src/lib/data/census.ts"), "utf8");
    expect(source).toContain("B19013_001E");
    expect(source).toMatch(/for=tract:\*|tract:\*/);
  });

  it("returns in-band Rutherford parcels for the Asheville shelf", async () => {
    let sample: ParcelFeature | undefined;
    eachFeature("37161", (feature) => {
      sample ??= feature;
    });
    expect(sample).toBeTruthy();
    expect(sample!.properties.countyName).toBe("Rutherford");
    expect(sample!.properties.opportunityZone).toBeNull();
    expect(sample!.properties.nearestRoad).toBeNull();
    expect(sample!.properties.incomeTract).toBeNull();
    expect(sample!.properties.marketIds).toEqual(["Asheville"]);
    expect(sample!.properties.state).toBe("North Carolina");
    const [lon, lat] = sample!.properties.centroid;
    const page = await queryParcelsInView([lon - 0.04, lat - 0.04, lon + 0.04, lat + 0.04]);
    expect(page.covered).toBe(true);
    const rutherford = page.collection.features.filter((item) => item.properties.countyFips === "37161");
    expect(rutherford.length).toBeGreaterThan(0);
    expect(rutherford.every((item) => item.properties.source === "nc-rutherford-parcels-37161")).toBe(true);
    expect(rutherford.every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150)).toBe(
      true,
    );
  });

  it("keeps every batch parcel inside 5–150 acres with no future sale or contact fields", () => {
    const today = new Date().toISOString().slice(0, 10);
    const problems: string[] = [];
    let yanceyPrices = 0;
    let yanceyLinks = 0;
    let scotlandPrices = 0;
    let swainDates = 0;
    let camdenMarket = 0;
    const baked = new Map<string, number>();
    for (const fips of Object.keys(COUNTIES)) {
      const ids = new Set<string>();
      eachFeature(fips, (item) => {
        ids.add(item.properties.parcelId);
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
        if (fips === "37199" && item.properties.lastSale?.price) yanceyPrices += 1;
        if (fips === "37199" && item.properties.appraiserUrl) yanceyLinks += 1;
        if (fips === "37165" && item.properties.lastSale?.price) scotlandPrices += 1;
        if (fips === "37173" && sold) swainDates += 1;
        if (fips === "37029" && item.properties.tax?.marketValue) camdenMarket += 1;
      });
      if (ids.size !== countyFile(fips).featureCount) {
        problems.push(`${fips} distinct ${ids.size} vs ${countyFile(fips).featureCount}`);
      }
      if (problems.length > 8) break;
    }
    const repeated = [...baked.entries()].filter(([, count]) => count >= 25);
    expect(problems).toEqual([]);
    expect(repeated).toEqual([]);
    expect(yanceyPrices).toBe(0);
    expect(yanceyLinks).toBe(0);
    expect(scotlandPrices).toBe(0);
    expect(swainDates).toBe(0);
    expect(camdenMarket).toBe(0);
  }, 300_000);
});
