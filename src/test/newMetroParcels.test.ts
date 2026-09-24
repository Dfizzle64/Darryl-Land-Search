import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import { catalogForMarket } from "../lib/markets";
import type { MarketParcelIndex } from "../lib/marketParcels";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelFeature } from "../lib/types";

const ROOT = process.cwd();

function readJson<T>(relative: string): T {
  return JSON.parse(readFileSync(path.join(ROOT, relative), "utf8")) as T;
}

const COUNTIES = ["13185", "13021", "13059", "45013", "28121", "28089", "28049", "28029", "28127", "28149", "28163"];

describe("new metro parcel shelves", () => {
  const index = readJson<MarketParcelIndex>("data/fixtures/market-parcels/index.json");
  const doc = readFileSync(path.join(ROOT, "docs/new-metro-parcels.md"), "utf8");

  it("registers the five shelves without borrowing Jackson, Tennessee", () => {
    for (const market of ["Valdosta", "Macon", "Athens", "Hilton Head", "Jackson MS"]) {
      expect(index.markets[market]?.parcelCount).toBeGreaterThan(0);
      expect(catalogForMarket({ markets: [] } as never, { markets: [] } as never, { markets: [] } as never, market as "Valdosta").market).toBe(market);
    }
    expect(index.markets.Jackson.counties.map((county) => county.fips)).toEqual(["47113"]);
    expect(index.markets["Jackson MS"].counties.map((county) => county.fips)).toEqual(
      expect.arrayContaining(["28121", "28089", "28049"]),
    );
    expect(doc).toMatch(/Winterville/);
    expect(doc).toMatch(/Port Royal/);
    expect(doc).toMatch(/gis3\.cmpdd\.org/);
    expect(doc).toMatch(/exlu2019/);
  });

  it("keeps every new county on a public source inside 5–150 acres", () => {
    for (const fips of COUNTIES) {
      const county = readJson<{
        source: string;
        queryUrl: string;
        featureCount: number;
        coverage: string;
        gaps: string[];
        join: { zoningJoined: number; fluJoined: number; salePriceNonNull: number };
      }>(`data/fixtures/market-parcels/counties/${fips}/county.json`);
      expect(county.coverage).toBe("complete-gte-5ac");
      expect(county.featureCount).toBeGreaterThan(0);
      expect(county.queryUrl).not.toContain("gis3.cmpdd.org");
      expect(county.queryUrl).not.toContain("portal.cmpdd.org");
      expect(county.gaps.join(" ")).toMatch(/No Opportunity Zone/);
      const tiles = path.join(ROOT, "data/fixtures/market-parcels/counties", fips, "tiles");
      const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"));
      expect(file).toBeTruthy();
      const collection = readJson<ParcelCollection>(`data/fixtures/market-parcels/counties/${fips}/tiles/${file}`);
      for (const feature of collection.features.slice(0, 12)) {
        expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
        expect(feature.properties.opportunityZone).toBeNull();
        expect(feature.properties.oz2Eligibility).toBeNull();
        expect(feature.properties.countyFips).toBe(fips);
      }
    }
  });

  it("joins the layers the cards actually published", () => {
    const lowndes = readJson<{ queryUrl: string; join: { zoningJoined: number; fluJoined: number } }>(
      "data/fixtures/market-parcels/counties/13185/county.json",
    );
    const bibb = readJson<{ queryUrl: string; join: { zoningJoined: number; fluJoined: number } }>(
      "data/fixtures/market-parcels/counties/13021/county.json",
    );
    const clarke = readJson<{
      queryUrl: string;
      join: { zoningJoined: number; fluJoined: number; byJurisdiction: Record<string, number> };
    }>("data/fixtures/market-parcels/counties/13059/county.json");
    const beaufort = readJson<{
      queryUrl: string;
      markets: string[];
      join: { zoningJoined: number; fluJoined: number; byJurisdiction: Record<string, number> };
    }>("data/fixtures/market-parcels/counties/45013/county.json");
    const rankin = readJson<{ queryUrl: string; join: { zoningJoined: number; fluJoined: number } }>(
      "data/fixtures/market-parcels/counties/28121/county.json",
    );
    const hinds = readJson<{
      queryUrl: string;
      join: { zoningJoined: number; fluJoined: number; byJurisdiction: Record<string, number> };
      gaps: string[];
    }>("data/fixtures/market-parcels/counties/28049/county.json");
    expect(lowndes.queryUrl).toContain("valorgis.com");
    expect(lowndes.join.zoningJoined).toBeGreaterThan(0);
    expect(lowndes.join.fluJoined).toBeGreaterThan(0);
    expect(bibb.queryUrl).toContain("ParcelCAMA_Current_2025");
    expect(bibb.join.zoningJoined).toBeGreaterThan(0);
    expect(clarke.queryUrl).toContain("enigma.accgov.com");
    expect(clarke.join.zoningJoined).toBeGreaterThan(0);
    expect(clarke.join.fluJoined).toBeGreaterThan(0);
    expect(beaufort.queryUrl).toContain("EnerGov/MapServer/1");
    expect(beaufort.markets).toEqual(expect.arrayContaining(["Hilton Head", "Savannah"]));
    expect(beaufort.join.byJurisdiction["Town of Hilton Head Island"]).toBeGreaterThan(0);
    expect(beaufort.join.zoningJoined).toBeGreaterThan(0);
    expect(rankin.queryUrl).toContain("gis.cmpdd.org");
    expect(rankin.join.zoningJoined).toBeGreaterThan(0);
    expect(rankin.join.fluJoined).toBeGreaterThan(0);
    expect(hinds.queryUrl).toContain("MS_Parcels_August_2024");
    expect(hinds.gaps.join(" ")).toMatch(/STCNTYFIPS/);
    expect(hinds.join.fluJoined).toBe(0);
    expect(hinds.join.byJurisdiction["City of Jackson"]).toBeGreaterThan(0);
    expect(hinds.gaps.join(" ")).toMatch(/Unincorporated/);
    expect(hinds.gaps.join(" ")).toMatch(/Byram/);
  });

  it("rejects lookalike geography in the sampled tiles", () => {
    const sample = (fips: string) => {
      const tiles = path.join(ROOT, "data/fixtures/market-parcels/counties", fips, "tiles");
      const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"))!;
      return readJson<ParcelCollection>(`data/fixtures/market-parcels/counties/${fips}/tiles/${file}`).features[0];
    };
    const centroid = (feature: ParcelFeature) => feature.properties.centroid!;
    expect(centroid(sample("13185"))[1]).toBeGreaterThan(30.4);
    expect(centroid(sample("13185"))[1]).toBeLessThan(31.3);
    expect(centroid(sample("13021"))[1]).toBeGreaterThan(32.4);
    expect(centroid(sample("13021"))[1]).toBeLessThan(33.2);
    expect(centroid(sample("13059"))[1]).toBeGreaterThan(33.8);
    expect(centroid(sample("13059"))[1]).toBeLessThan(34.2);
    expect(centroid(sample("28089"))[1]).toBeLessThan(33.3);
    expect(existsSync(path.join(ROOT, "data/fixtures/market-parcels/counties/13059/tiles"))).toBe(true);
  });

  it("points appraisers at the county on the card", () => {
    expect(parcelAppraiserUrl({ parcelId: "001", countyFips: "13185" }).href).toContain("LowndesCountyGA");
    expect(parcelAppraiserUrl({ parcelId: "001", countyFips: "13021" }).href).toContain("BibbCountyGA");
    expect(parcelAppraiserUrl({ parcelId: "001", countyFips: "13059" }).href).toContain("ClarkeCountyGA");
    expect(parcelAppraiserUrl({ parcelId: "001", countyFips: "45013" }).href).toContain("beaufort");
    expect(parcelAppraiserUrl({ parcelId: "001", countyFips: "28049" }).href).toContain("hinds.ms.us");
    expect(parcelAppraiserUrl({ parcelId: "001", countyFips: "28089" }).label).toMatch(/Mississippi/);
  });
});
