import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { MarketParcelIndex } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const NY_MIRROR = "EbVsqZ18sv1kVJ3k";
const ROOT = process.cwd();

function readJson<T>(relative: string): T {
  return JSON.parse(readFileSync(path.join(ROOT, relative), "utf8")) as T;
}

describe("Tuscaloosa and Montgomery MSA parcels", () => {
  const index = readJson<MarketParcelIndex>("data/fixtures/market-parcels/index.json");
  const doc = readFileSync(path.join(ROOT, "docs/tuscaloosa-montgomery-parcels.md"), "utf8");

  it("keeps Marshall, Daphne/Fairhope, and Alabaster counties untouched", () => {
    const marshall = index.markets.Huntsville.counties.find((county) => county.fips === "01095");
    const baldwin = index.markets.Mobile.counties.find((county) => county.fips === "01003");
    const shelby = index.markets.Birmingham.counties.find((county) => county.fips === "01117");
    const jefferson = index.markets.Birmingham.counties.find((county) => county.fips === "01073");
    expect(marshall?.featureCount).toBe(0);
    expect(baldwin?.featureCount).toBe(17987);
    expect(shelby?.featureCount).toBe(11994);
    expect(jefferson?.featureCount).toBe(15641);
    expect(index.markets.Birmingham.counties.some((county) => county.fips === "01125")).toBe(false);
  });

  it("loads the four county extracts and documents the gaps", () => {
    expect(index.markets.Tuscaloosa.parcelCount).toBeGreaterThan(0);
    expect(index.markets.Montgomery.parcelCount).toBeGreaterThan(0);
    const tuscaloosa = index.markets.Tuscaloosa.counties.find((county) => county.fips === "01125");
    const montgomery = index.markets.Montgomery.counties.find((county) => county.fips === "01101");
    const elmore = index.markets.Montgomery.counties.find((county) => county.fips === "01051");
    const autauga = index.markets.Montgomery.counties.find((county) => county.fips === "01001");
    expect(tuscaloosa?.coverage).toBe("complete-gte-5ac");
    expect(montgomery?.coverage).toBe("complete-gte-5ac");
    expect(elmore?.coverage).toBe("complete-gte-5ac");
    expect(autauga?.coverage).toBe("complete-gte-5ac");
    for (const fips of ["01065", "01107", "01063"]) {
      const county = index.markets.Tuscaloosa.counties.find((item) => item.fips === fips);
      expect(county?.featureCount).toBe(0);
      expect(county?.coverage).toBe("gap");
    }
    const lowndes = index.markets.Montgomery.counties.find((county) => county.fips === "01085");
    expect(lowndes?.featureCount).toBe(0);
    expect(doc).toMatch(/EbVsqZ18sv1kVJ3k/);
    expect(doc).toMatch(/499/);
    expect(doc).toMatch(/1987/);
    expect(doc).toMatch(/Hale/);
    expect(doc).toMatch(/Pickens/);
    expect(doc).toMatch(/Greene/);
    expect(doc).toMatch(/Bibb/);
    expect(doc).toMatch(/Nothing here is an Opportunity Zone designation/);
  });

  it("joins city zoning, keeps sale prices null, and rejects the NY mirror", () => {
    const counties = ["01125", "01101", "01051", "01001"].map((fips) =>
      readJson<{
        source: string;
        queryUrl: string;
        featureCount: number;
        gaps: string[];
        join: {
          zoningJoined: number;
          fluJoined: number;
          salePriceNonNull: number;
          saleDateNonNull: number;
          byJurisdiction: Record<string, number>;
          prattvilleJoined: number;
        };
      }>(`data/fixtures/market-parcels/counties/${fips}/county.json`),
    );
    const [tuscaloosa, montgomery, elmore, autauga] = counties;
    for (const county of counties) {
      expect(county.queryUrl).not.toContain(NY_MIRROR);
      expect(county.queryUrl).not.toContain("Montgomery_County_Parcels");
      expect(county.gaps.join(" ")).not.toMatch(/Framework_Zoning_Map was joined/i);
      expect(county.join.salePriceNonNull).toBe(0);
      expect(county.join.zoningJoined).toBeGreaterThan(0);
      expect(county.featureCount).toBeGreaterThan(0);
    }
    expect(tuscaloosa.queryUrl).toContain("AWzSDaKZ41uuVges");
    expect(tuscaloosa.source).toBe("al-tuscaloosa-parcels");
    expect(tuscaloosa.join.byJurisdiction["City of Tuscaloosa"]).toBeGreaterThan(0);
    expect(tuscaloosa.join.byJurisdiction.Northport).toBeGreaterThan(0);
    expect(tuscaloosa.join.fluJoined).toBeGreaterThan(0);
    expect(tuscaloosa.join.saleDateNonNull).toBeGreaterThan(0);
    expect(montgomery.queryUrl).toContain("gis.montgomeryal.gov");
    expect(montgomery.join.byJurisdiction["City of Montgomery"]).toBeGreaterThan(0);
    expect(montgomery.join.saleDateNonNull).toBe(0);
    expect(elmore.queryUrl).toContain("Elmore/Public/MapServer/133");
    expect(elmore.join.byJurisdiction.Millbrook).toBeGreaterThan(0);
    expect(elmore.join.prattvilleJoined).toBeGreaterThan(0);
    expect(autauga.queryUrl).toContain("Autauga_Parcels");
    expect(autauga.join.prattvilleJoined).toBeGreaterThan(0);
    expect(elmore.gaps.join(" ")).toMatch(/1987/);
    expect(autauga.gaps.join(" ")).toMatch(/1987/);
    expect(elmore.gaps.join(" ")).toMatch(/499/);
    expect(montgomery.gaps.join(" ")).toMatch(/EbVsqZ18sv1kVJ3k/);
  });

  it("keeps sampled tiles inside 5–150 acres with null sale prices", () => {
    for (const fips of ["01125", "01101", "01051", "01001"]) {
      const tiles = path.join(ROOT, "data/fixtures/market-parcels/counties", fips, "tiles");
      expect(existsSync(tiles)).toBe(true);
      const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"));
      expect(file).toBeTruthy();
      const collection = readJson<ParcelCollection>(`data/fixtures/market-parcels/counties/${fips}/tiles/${file}`);
      expect(collection.features.length).toBeGreaterThan(0);
      for (const feature of collection.features.slice(0, 20)) {
        expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
        expect(feature.properties.lastSale.price).toBeNull();
        expect(feature.properties.opportunityZone).toBeNull();
        expect(feature.properties.oz2Eligibility).toBeNull();
        expect(feature.properties.countyFips).toBe(fips);
        const markets = feature.properties.marketIds ?? [];
        if (fips === "01125") expect(markets).toContain("Tuscaloosa");
        else expect(markets).toContain("Montgomery");
        expect(markets).not.toContain("Birmingham");
      }
    }
  });
});
