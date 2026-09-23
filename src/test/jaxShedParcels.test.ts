import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand } from "../lib/marketParcels";
import { parcelAppraiserUrl } from "../lib/format";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const COUNTY_BBOX: Record<string, [number, number, number, number]> = {
  "12031": [-82.0795, 30.0739, -81.3508, 30.6158],
  "12109": [-81.6993, 29.5929, -81.1827, 30.283],
  "12019": [-82.0843, 29.6885, -81.5727, 30.2249],
  "12089": [-82.0854, 30.2434, -81.3945, 30.8626],
  "12003": [-82.4895, 30.1069, -82.0192, 30.6143],
};

const SOURCES: Record<string, string> = {
  "12031": "fl-coj-citybiz-parcels-12031",
  "12109": "fl-sjc-hosted-parcel-12109",
  "12019": "fl-clay-parcels-lgim-12019",
  "12089": "fl-nassau-taxmap-12089",
  "12003": "fl-baker-parcels-web2-12003",
};

function readCounty(fips: string) {
  const file = path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips, "county.json");
  return JSON.parse(readFileSync(file, "utf8")) as {
    featureCount: number;
    coverage: string;
    source: string;
    gaps: string[];
    markets: string[];
  };
}

function featuresFor(fips: string): ParcelFeature[] {
  const tiles = path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips, "tiles");
  const features: ParcelFeature[] = [];
  for (const name of readdirSync(tiles)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
    features.push(...collection.features);
  }
  return features;
}

describe("Jacksonville shed parcels", () => {
  it("points Duval and Baker appraiser links at the public search sites", () => {
    expect(parcelAppraiserUrl({ parcelId: "044183 0000", countyFips: "12031" })).toEqual({
      href: "https://paopropertysearch.coj.net/",
      label: "Open Duval Property Appraiser search",
    });
    expect(parcelAppraiserUrl({ parcelId: "19-2S-22-0000-0000-0315", countyFips: "12003" }).label).toBe(
      "Open Baker Property Appraiser search",
    );
    expect(parcelAppraiserUrl({ parcelId: "pin", countyFips: "12109" }).href).toBe("https://www.sjcpa.gov/");
  });

  it("keeps seeded Jacksonville counties inside 5–150 acres and their Florida extents", () => {
    const indexPath = path.join(process.cwd(), "data/fixtures/market-parcels/index.json");
    expect(existsSync(indexPath)).toBe(true);
    const index = JSON.parse(readFileSync(indexPath, "utf8")) as {
      markets: { Jacksonville?: { parcelCount: number; counties: { fips: string; coverage: string }[] } };
    };
    const market = index.markets.Jacksonville;
    expect(market?.parcelCount).toBeGreaterThan(20000);
    expect(market?.counties.map((county) => county.fips).sort()).toEqual(["12003", "12019", "12031", "12089", "12109"]);

    for (const fips of Object.keys(COUNTY_BBOX)) {
      const meta = readCounty(fips);
      expect(meta.coverage).toBe("complete-gte-5ac");
      expect(meta.source).toBe(SOURCES[fips]);
      expect(meta.markets).toContain("Jacksonville");
      expect(meta.gaps.join(" ")).not.toMatch(/overlay failed|Download failed/i);
      const [west, south, east, north] = COUNTY_BBOX[fips];
      const features = featuresFor(fips);
      expect(features.length).toBe(meta.featureCount);
      expect(features.length).toBeGreaterThan(1000);
      for (const feature of features) {
        expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
        expect(feature.properties.countyFips).toBe(fips);
        expect(feature.properties.marketIds).toContain("Jacksonville");
        expect(feature.properties.marketIds).not.toContain("Orlando");
        const [lon, lat] = feature.properties.centroid;
        expect(lon).toBeGreaterThanOrEqual(west);
        expect(lon).toBeLessThanOrEqual(east);
        expect(lat).toBeGreaterThanOrEqual(south);
        expect(lat).toBeLessThanOrEqual(north);
      }
    }
  });

  it("keeps Jacksonville zoning off the beach cities that have no public REST layer", () => {
    const duval = readCounty("12031");
    const text = duval.gaps.join(" ");
    expect(text).toMatch(/Sale price is not on CityBiz/);
    expect(text).toMatch(/Atlantic Beach parcels left without city zoning: (?!0)\d+/);
    expect(text).toMatch(/Neptune Beach parcels left without city zoning: (?!0)\d+/);
    expect(text).toMatch(/Baldwin parcels left without city zoning: (?!0)\d+/);
    expect(text).toMatch(/Jacksonville Beach zoning applied to (?!0)\d+/);
    const features = featuresFor("12031");
    const sample = features.find((feature) => feature.properties.parcelId === "044183 0000");
    expect(sample?.properties.acreage).toBeCloseTo(8.19, 2);
    expect(sample?.properties.zoningCode).toBe("PUD");
    expect(sample?.properties.flu?.code).toBe("CGC");
    expect(sample?.properties.lastSale.date).toBe("2019-04-04");
    expect(sample?.properties.lastSale.price).toBeNull();
    const beach = features.filter((feature) => feature.properties.jurisdictionCode === "Jacksonville Beach");
    expect(beach.length).toBeGreaterThan(0);
    expect(beach.some((feature) => feature.properties.zoningCode)).toBe(true);
    expect(beach.every((feature) => feature.properties.flu == null)).toBe(true);
    for (const city of ["Atlantic Beach", "Neptune Beach", "Baldwin"]) {
      const rows = features.filter((feature) => feature.properties.jurisdictionCode === city);
      expect(rows.length).toBeGreaterThan(0);
      expect(rows.every((feature) => feature.properties.zoningCode == null && feature.properties.flu == null)).toBe(true);
    }
  });

  it("records city overlays and the remaining municipal gaps", () => {
    const johns = readCounty("12109").gaps.join(" ");
    expect(johns).toMatch(/St\. Augustine parcels in the 5–150 acre band:/);
    expect(johns).toMatch(/St\. Augustine Beach FLU is a gap/);
    expect(johns).toMatch(/Sale price and tax values are not on the public parcel layer/);
    const clay = readCounty("12019").gaps.join(" ");
    expect(clay).toMatch(/Green Cove Springs zoning applied to/);
    expect(clay).toMatch(/Orange Park parcels left without city zoning:/);
    expect(clay).toMatch(/Keystone Heights parcels left without city zoning:/);
    expect(clay).toMatch(/Penney Farms parcels left without city zoning:/);
    const nassau = readCounty("12089").gaps.join(" ");
    expect(nassau).toMatch(/Fernandina Beach parcels in the 5–150 acre band:/);
    expect(nassau).toMatch(/Hilliard parcels in the 5–150 acre band:/);
    expect(nassau).toMatch(/Callahan has no separate zoning layer/);
    const baker = readCounty("12003").gaps.join(" ");
    expect(baker).toMatch(/unlabeled cama0827/);
    expect(baker).toMatch(/Macclenny and Glen St\. Mary/);
    const fluJoined = Number(baker.match(/FLU joined on (\d+) of/)?.[1] ?? 0);
    expect(fluJoined).toBeGreaterThan(2500);
    expect(nassau).toMatch(/Repeated PINs on the tax map were kept once/);
    const nassauParcel = featuresFor("12089").find((feature) => feature.properties.parcelId === "00-00-30-0087-0000-0000");
    expect(nassauParcel?.properties.ownerName).toBe("AMELIA RETREAT");
    expect(nassauParcel?.properties.acreage).toBeGreaterThan(7);
    expect(nassauParcel?.properties.acreage).toBeLessThan(8);
  });
});
