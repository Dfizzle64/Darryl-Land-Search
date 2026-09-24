import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const HEARTLAND = [
  { fips: "12055", name: "Highlands", source: "fl-highlands-pao-12055" },
  { fips: "12049", name: "Hardee", source: "fl-hardee-infomap-12049" },
  { fips: "12043", name: "Glades", source: "fl-glades-agol-2026-06-12043" },
  { fips: "12051", name: "Hendry", source: "fl-hendry-parcels-feb2024-12051" },
  { fips: "12027", name: "DeSoto", source: "fl-desoto-swfwmd-12027" },
] as const;

const HEARTLAND_BOX = { west: -82.25, south: 26.05, east: -80.65, north: 27.85 };
const SENTINELS = new Set(["LABELLE", "LA BELLE", "CLEWISTON", "CITY OF LABELLE", "CITY OF CLEWISTON"]);

function readCounty(fips: string) {
  return JSON.parse(readFileSync(path.join("data/fixtures/market-parcels/counties", fips, "county.json"), "utf8")) as {
    name: string;
    state: string;
    fips: string;
    markets: string[];
    featureCount: number;
    coverage: string;
    source: string;
    queryUrl?: string | null;
    gaps: string[];
  };
}

function eachFeature(fips: string, visit: (feature: ParcelFeature) => void) {
  const tiles = path.join("data/fixtures/market-parcels/counties", fips, "tiles");
  for (const name of readdirSync(tiles)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
    for (const feature of collection.features) visit(feature);
  }
}

describe("Florida Heartland shelf", () => {
  it("keeps Mississippi DeSoto on the Memphis extract", () => {
    const memphis = readCounty("28033");
    expect(memphis.name).toBe("DeSoto");
    expect(memphis.state).toBe("Mississippi");
    expect(memphis.source).toBe("ms-mdeq-2023-28033");
    expect(memphis.markets).toContain("Memphis");
    expect(memphis.markets).not.toContain("Heartland");
  });

  it("labels the five Florida counties and leaves documented gaps blank", () => {
    const index = JSON.parse(readFileSync("data/fixtures/market-parcels/index.json", "utf8")) as {
      markets: Record<string, { tier: string; counties: { fips: string; state: string; name: string }[] }>;
    };
    expect(index.markets.Heartland.tier).toBe("shelf");
    expect(index.markets.Heartland.counties.map((county) => county.fips)).toEqual([
      "12027",
      "12043",
      "12049",
      "12051",
      "12055",
    ]);

    for (const county of HEARTLAND) {
      const row = readCounty(county.fips);
      expect(row.name).toBe(county.name);
      expect(row.state).toBe("Florida");
      expect(row.source).toBe(county.source);
      expect(row.markets).toContain("Heartland");
      expect(row.featureCount).toBeGreaterThan(0);
      expect(row.queryUrl ?? "").not.toMatch(/hcpao\.org|highlands.*texas|desoto.*kansas/i);
      if (county.fips === "12049") expect(row.markets).toContain("Tampa");
      else expect(row.markets).not.toContain("Tampa");
      if (county.fips === "12027") {
        expect(row.coverage).toBe("partial");
        expect(row.gaps.join(" ")).toMatch(/Unincorporated DeSoto/);
      }
      if (county.fips === "12055") {
        expect(row.gaps.join(" ")).toMatch(/Sebring/);
        expect(row.gaps.join(" ")).not.toMatch(/root Parcels FeatureServer was used/i);
      }
      if (county.fips === "12051") expect(row.gaps.join(" ")).toMatch(/Feb 2024|February 2024/);
    }
  });

  it("keeps 5–150 acre Florida polygons and does not invent city sentinels", () => {
    for (const county of HEARTLAND) {
      let seen = 0;
      let zoned = 0;
      let arcadia = 0;
      let unincorporated = 0;
      eachFeature(county.fips, (feature) => {
        const props = feature.properties;
        seen += 1;
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.countyFips).toBe(county.fips);
        expect(props.state).toBe("Florida");
        expect(props.marketIds).toContain("Heartland");
        expect(props.marketIds).not.toContain("Orlando");
        expect(props.marketIds).not.toContain("Memphis");
        const [lon, lat] = props.centroid;
        expect(lon).toBeGreaterThanOrEqual(HEARTLAND_BOX.west);
        expect(lon).toBeLessThanOrEqual(HEARTLAND_BOX.east);
        expect(lat).toBeGreaterThanOrEqual(HEARTLAND_BOX.south);
        expect(lat).toBeLessThanOrEqual(HEARTLAND_BOX.north);
        const code = (props.zoningCode || "").toUpperCase();
        expect(SENTINELS.has(code)).toBe(false);
        if (props.zoningCode) zoned += 1;
        if (county.fips === "12027") {
          if (props.jurisdictionCode === "Arcadia") arcadia += 1;
          else unincorporated += 1;
          if (props.jurisdictionCode !== "Arcadia") {
            expect(props.zoningCode).toBeNull();
            expect(props.flu).toBeNull();
          }
        }
      });
      expect(seen).toBe(readCounty(county.fips).featureCount);
      expect(zoned).toBeGreaterThan(0);
      if (county.fips === "12027") {
        expect(arcadia).toBeGreaterThan(0);
        expect(unincorporated).toBeGreaterThan(0);
      }
    }
  });

  it("does not point the shelf at rejected services", () => {
    const text = readFileSync("scripts/heartland_parcels.py", "utf8");
    expect(text).toContain("gis1.hcpao.org");
    expect(text).toContain("REJECTED_GLADES_HCPAO");
    expect(text).not.toMatch(/gis1\.hcpao\.org[^"\n]*\/query/);
    const fixtureRoot = "data/fixtures/market-parcels/counties";
    for (const county of HEARTLAND) {
      const raw = readFileSync(path.join(fixtureRoot, county.fips, "county.json"), "utf8");
      expect(raw).not.toContain("https://gis1.hcpao.org");
      expect(raw).not.toContain("services/Parcels/FeatureServer");
    }
    expect(existsSync("data/fixtures/market-parcels/markets/heartland/meta.json")).toBe(true);
  });
});
