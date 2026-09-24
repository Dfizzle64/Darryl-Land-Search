import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand, type MarketParcelIndex, type MarketParcelsMeta } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const root = process.cwd();
const countyDir = path.join(root, "data/fixtures/market-parcels/counties/47021");

type ZoningBucket = { parcels: number; zoned: number; rate: number | null };

type CheathamCounty = {
  name: string;
  fips: string;
  state: string;
  featureCount: number;
  coverage: string;
  source: string;
  queryUrl: string;
  gaps: string[];
  sourceCount: number;
  dropped: number;
  comptrollerCountyId: number;
  comptrollerJur: string;
  rejectedTwins: string[];
  zoningJoin: Record<string, ZoningBucket>;
  flu: string;
  markets: string[];
};

const REJECTED_HOSTS = ["ashlandcountywi.gov", "ashlandky.gov", "chathamcounty", "gis.ashland"];

function readJson<T>(file: string): T {
  return JSON.parse(readFileSync(file, "utf8")) as T;
}

function loadParcels(): ParcelFeature[] {
  const tiles = path.join(countyDir, "tiles");
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(tiles)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = readJson<ParcelCollection>(path.join(tiles, name));
    features.push(...collection.features);
  }
  return features;
}

describe("Cheatham County TN parcel extract", () => {
  const county = readJson<CheathamCounty>(path.join(countyDir, "county.json"));
  const features = loadParcels();
  const lookup = readJson<Record<string, string>>(path.join(countyDir, "lookup.json"));

  it("uses APSU CheatGIS for FIPS 47021 and Comptroller county 11", () => {
    expect(county.fips).toBe("47021");
    expect(county.name).toBe("Cheatham");
    expect(county.state).toBe("Tennessee");
    expect(county.markets).toEqual(["Nashville"]);
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("apsu-cheatgis-47021");
    expect(county.queryUrl).toBe(
      "https://apnsgis4.apsu.edu/arcgis/rest/services/Cheatham/CheatGIS/MapServer/9/query",
    );
    expect(county.comptrollerCountyId).toBe(11);
    expect(county.comptrollerJur).toBe("011");
    expect(county.queryUrl).not.toContain("COUNTY_ID=21");
    expect(county.queryUrl).not.toContain("maps.cot.tn.gov");
    for (const host of REJECTED_HOSTS) {
      expect(county.queryUrl.toLowerCase()).not.toContain(host);
    }
    expect(county.rejectedTwins.join(" ")).toMatch(/Wisconsin/);
    expect(county.rejectedTwins.join(" ")).toMatch(/Ohio/);
    expect(county.rejectedTwins.join(" ")).toMatch(/Kentucky/);
    expect(county.rejectedTwins.join(" ")).toMatch(/Chatham/);
    expect(county.flu).toBe("gap");
    expect(county.gaps.join(" ")).toMatch(/honest REST gap/i);
    expect(county.gaps.join(" ")).toMatch(/cities-first/i);
    expect(county.gaps.join(" ")).toMatch(/not parcel FLU/i);
  });

  it("keeps the inclusive 5–150 acre type-1 band and replaces the FIPS-as-county-id pull", () => {
    expect(features.length).toBe(county.featureCount);
    expect(county.featureCount).toBeGreaterThan(5000);
    expect(county.featureCount).toBeLessThan(6000);
    expect(county.sourceCount).toBeGreaterThanOrEqual(county.featureCount);
    expect(Object.keys(lookup)).toHaveLength(features.length);
    const ids = new Set<string>();
    for (const feature of features) {
      const props = feature.properties;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.countyFips).toBe("47021");
      expect(props.countyName).toBe("Cheatham");
      expect(props.state).toBe("Tennessee");
      expect(props.marketIds).toEqual(["Nashville"]);
      expect(props.source).toBe("apsu-cheatgis-47021");
      expect(props.parcelId.startsWith("011")).toBe(true);
      expect(props.parcelId.startsWith("021")).toBe(false);
      expect(props.id).toBe(`47021:${props.parcelId}`);
      expect(lookup[props.parcelId]).toBeTruthy();
      expect(ids.has(props.parcelId)).toBe(false);
      ids.add(props.parcelId);
      const [lon, lat] = props.centroid;
      expect(lon).toBeGreaterThanOrEqual(-87.32);
      expect(lon).toBeLessThanOrEqual(-86.88);
      expect(lat).toBeGreaterThanOrEqual(36.02);
      expect(lat).toBeLessThanOrEqual(36.48);
      expect(props.flu).toBeNull();
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.appraiserUrl ?? "").toContain("assessment.cot.tn.gov");
      expect(props.appraiserUrl ?? "").not.toContain("ashlandcountywi");
      expect(props.appraiserUrl ?? "").not.toContain("ashlandky");
      expect(["ASH", "PVW", "KGS", "PEG", "CHE"]).toContain(props.jurisdictionPrefix);
      expect(props.jurisdictionCode).toBe(props.jurisdictionPrefix);
      if (props.zoningCode) {
        expect(props.jurisdictionPrefix).toBeTruthy();
      }
    }
  });

  it("joins zoning cities-first and leaves future land use empty", () => {
    const join = county.zoningJoin;
    expect(join["ASHLAND CITY"].parcels).toBeGreaterThan(40);
    expect(join["PLEASANT VIEW"].parcels).toBeGreaterThan(40);
    expect(join["KINGSTON SPRINGS"].parcels).toBeGreaterThan(40);
    expect(join.PEGRAM.parcels).toBeGreaterThan(20);
    expect(join.UNINCORPORATED.parcels).toBeGreaterThan(3000);
    for (const bucket of Object.values(join)) {
      expect(bucket.zoned).toBeGreaterThan(0);
      expect(bucket.rate).not.toBeNull();
      expect(bucket.rate ?? 0).toBeGreaterThan(0.5);
      expect(bucket.zoned).toBeLessThanOrEqual(bucket.parcels);
    }
    const byPrefix = new Map<string, number>();
    let zoned = 0;
    let owners = 0;
    for (const feature of features) {
      const prefix = feature.properties.jurisdictionPrefix ?? "";
      byPrefix.set(prefix, (byPrefix.get(prefix) ?? 0) + 1);
      if (feature.properties.zoningCode) zoned += 1;
      if (feature.properties.ownerName) owners += 1;
      expect(feature.properties.flu).toBeNull();
    }
    expect(byPrefix.get("ASH")).toBe(join["ASHLAND CITY"].parcels);
    expect(byPrefix.get("PVW")).toBe(join["PLEASANT VIEW"].parcels);
    expect(byPrefix.get("KGS")).toBe(join["KINGSTON SPRINGS"].parcels);
    expect(byPrefix.get("PEG")).toBe(join.PEGRAM.parcels);
    expect(byPrefix.get("CHE")).toBe(join.UNINCORPORATED.parcels);
    expect(zoned / features.length).toBeGreaterThan(0.5);
    expect(owners / features.length).toBeGreaterThan(0.9);
    const sample = features.find((feature) => feature.properties.parcelId === "011004    00100");
    expect(sample?.properties.acreage).toBeGreaterThanOrEqual(5);
    expect(sample?.properties.ownerName).toBeTruthy();
    expect(sample?.properties.jurisdictionPrefix).toBe("CHE");
  });

  it("updates only the Nashville market totals", () => {
    const index = readJson<MarketParcelIndex>(path.join(root, "data/fixtures/market-parcels/index.json"));
    const meta = readJson<MarketParcelsMeta>(path.join(root, "data/fixtures/market-parcels/markets/nashville/meta.json"));
    const summed = meta.counties.reduce((total, item) => total + item.featureCount, 0);
    expect(meta.parcelCount).toBe(summed);
    expect(index.markets.Nashville.parcelCount).toBe(summed);
    const indexed = index.markets.Nashville.counties.find((item) => item.fips === "47021");
    const listed = meta.counties.find((item) => item.fips === "47021");
    expect(indexed?.featureCount).toBe(county.featureCount);
    expect(listed?.featureCount).toBe(county.featureCount);
    expect(listed?.source).toBe("apsu-cheatgis-47021");
    expect(index.markets.Nashville.gapCountyCount).toBe(4);
    expect(index.markets.Nashville.completeCountyCount).toBe(13);
    const docs = readFileSync(path.join(root, "docs/market-parcels.md"), "utf8");
    expect(docs).toContain(`| Cheatham | Tennessee | 47021 | complete-gte-5ac | ${county.featureCount.toLocaleString("en-US")} | apsu-cheatgis-47021 |`);
    expect(county.gaps.join(" ")).toMatch(/JUR is 011/);
    expect(docs).not.toContain("tn-impact-47021");
  });
});
