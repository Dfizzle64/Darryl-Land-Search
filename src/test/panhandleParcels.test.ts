import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const root = process.cwd();
const manifestPath = path.join(root, "data/panhandle-parcel-sources.json");

const WIRE = ["12005", "12091", "12131", "12033", "12113"] as const;

describe("panhandle shelf parcel sources", () => {
  it("keeps the card wire order and refuses the Destin FGDL false-positive", () => {
    const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as {
      wireOrder: string[];
      acreage: { min: number; max: number };
      phonesOrEmails: boolean;
      rejected: { url?: string; name?: string; reason: string }[];
      layers: Record<string, string>;
      pensacolaCityZoning: { status: string; url: string };
      freeportZoning: { caveat: string; url: string };
    };
    expect(manifest.wireOrder).toEqual([...WIRE]);
    expect(manifest.acreage).toEqual({ min: 5, max: 150 });
    expect(manifest.phonesOrEmails).toBe(false);
    expect(manifest.pensacolaCityZoning.status).toBe("blocked-523");
    expect(manifest.pensacolaCityZoning.url).toContain("gis.cityofpensacola.com");
    expect(manifest.freeportZoning.caveat.toLowerCase()).toContain("numeric");
    const rejected = manifest.rejected.map((item) => `${item.url ?? ""} ${item.name ?? ""} ${item.reason}`).join("\n");
    expect(rejected).toContain("GcvM6vDlR2gM4x31");
    expect(rejected.toLowerCase()).toContain("walton county tax parcels");
    for (const url of Object.values(manifest.layers)) {
      expect(url.toLowerCase()).not.toContain("gcvm6vdlr2gm4x31");
      expect(url.toLowerCase()).not.toContain("phone");
      expect(url.toLowerCase()).not.toContain("email");
    }
  });

  it("seeds each shelf county from county GIS inside 5–150 acres", () => {
    for (const fips of WIRE) {
      const metaPath = path.join(root, "data/fixtures/market-parcels/counties", fips, "county.json");
      expect(existsSync(metaPath), metaPath).toBe(true);
      const meta = JSON.parse(readFileSync(metaPath, "utf8")) as {
        source: string;
        featureCount: number;
        coverage: string;
        minAcres: number;
        maxAcres: number;
        markets: string[];
        gaps: string[];
        zoningJoinedCount: number;
        fluJoinedCount: number;
        queryUrl: string;
      };
      expect(meta.source).toBe(`fl-panhandle-${fips}`);
      expect(meta.coverage).toBe("complete-gte-5ac");
      expect(meta.minAcres).toBe(5);
      expect(meta.maxAcres).toBe(150);
      expect(meta.markets).toContain("Pensacola");
      expect(meta.featureCount).toBeGreaterThan(3000);
      expect(meta.zoningJoinedCount).toBeGreaterThan(100);
      expect(meta.fluJoinedCount).toBeGreaterThan(100);
      expect(meta.queryUrl.toLowerCase()).not.toContain("floridahealth.gov");
      expect(meta.queryUrl.toLowerCase()).not.toContain("gcvm6vdlr2gm4x31");
      const gapText = meta.gaps.join("\n");
      expect(gapText.toLowerCase()).not.toContain("phone number");
      const tiles = path.join(root, "data/fixtures/market-parcels/counties", fips, "tiles");
      const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"));
      expect(file).toBeTruthy();
      const collection = JSON.parse(readFileSync(path.join(tiles, file as string), "utf8")) as ParcelCollection;
      expect(collection.features.length).toBeGreaterThan(0);
      for (const feature of collection.features.slice(0, 20)) {
        expect(inMarketAcreageBand(feature.properties.acreage)).toBe(true);
        expect(feature.properties.countyFips).toBe(fips);
        expect(feature.properties.source).toBe(`fl-panhandle-${fips}`);
        expect(feature.properties.marketIds).toContain("Pensacola");
        for (const key of Object.keys(feature.properties)) {
          expect(key.toLowerCase()).not.toMatch(/email|phone/);
        }
      }
    }
  });

  it("documents the Pensacola 523 block and the Freeport numeric zoning caveat", () => {
    const escambia = JSON.parse(
      readFileSync(path.join(root, "data/fixtures/market-parcels/counties/12033/county.json"), "utf8"),
    ) as { gaps: string[] };
    const walton = JSON.parse(
      readFileSync(path.join(root, "data/fixtures/market-parcels/counties/12131/county.json"), "utf8"),
    ) as { gaps: string[] };
    expect(escambia.gaps.join("\n")).toContain("523");
    expect(escambia.gaps.join("\n")).toContain("Accela");
    expect(walton.gaps.join("\n").toLowerCase()).toContain("freeport");
    expect(walton.gaps.join("\n").toLowerCase()).toContain("numeric");
  });
});
