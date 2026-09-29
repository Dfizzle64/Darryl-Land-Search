import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";

/**
 * Next 20 rural-OZ counties in pass1_order that were not already a complete
 * extract. Maury, Shelby, and Sumner were skipped because earlier pulls
 * already published complete extracts.
 */
const COUNTIES = [
  { fips: "47091", name: "Johnson", market: "Knoxville", vintage: "2023", zoning: "empty" },
  { fips: "47099", name: "Lawrence", market: "Nashville", vintage: "2025", zoning: "sales" },
  { fips: "47107", name: "McMinn", market: "Chattanooga", vintage: "2025", zoning: "polygon" },
  { fips: "47131", name: "Obion", market: "Memphis", vintage: "2023", zoning: "empty" },
  { fips: "47151", name: "Scott", market: "Knoxville", vintage: "2023", zoning: "empty" },
  { fips: "47163", name: "Sullivan", market: "Knoxville", vintage: "2023", zoning: "attribute" },
  { fips: "47167", name: "Tipton", market: "Memphis", vintage: "2026", zoning: "polygon" },
  { fips: "47181", name: "Wayne", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47027", name: "Clay", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47049", name: "Fentress", market: "Knoxville", vintage: null, zoning: "empty" },
  { fips: "47051", name: "Franklin", market: "Huntsville", vintage: "2023", zoning: "empty" },
  { fips: "47067", name: "Hancock", market: "Knoxville", vintage: "2023", zoning: "empty" },
  { fips: "47073", name: "Hawkins", market: "Knoxville", vintage: "2023", zoning: "empty" },
  { fips: "47085", name: "Humphreys", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47087", name: "Jackson", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47095", name: "Lake", market: "Memphis", vintage: "2023", zoning: "empty" },
  { fips: "47115", name: "Marion", market: "Chattanooga", vintage: "2025", zoning: "polygon" },
  { fips: "47137", name: "Pickett", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47005", name: "Benton", market: "Jackson", vintage: "2023", zoning: "empty" },
  { fips: "47019", name: "Carter", market: "Knoxville", vintage: "2023", zoning: "empty" },
] as const;

const REJECTED = ["regrid", "reportall", "chesco.org", "pasda.psu.edu", "bedfordcountypa"];

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
  markets: string[];
  gaps: string[];
  lookup: string;
  ingest?: {
    opportunityZoneDesignated?: number;
    simplified?: boolean;
    acreageBand?: number[];
    kept?: number;
    salesVintage?: string | null;
  };
};

async function readManifest(fips: string): Promise<CountyManifest> {
  const raw = await readFile(
    path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips, "county.json"),
    "utf8",
  );
  return JSON.parse(raw) as CountyManifest;
}

describe("Tennessee rural parcel batch 3", () => {
  it("lists the twenty counties and leaves Maury, Shelby, and Sumner on their earlier extracts", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    for (const county of COUNTIES) {
      expect(loaded.find((row) => row.fips === county.fips)).toEqual({
        fips: county.fips,
        name: county.name,
        state: "Tennessee",
      });
    }
    const maury = await readManifest("47119");
    expect(maury.name).toBe("Maury");
    expect(maury.featureCount).toBe(9033);
    expect(maury.source).toBe("tn-columbia-agol-47119");
    const shelby = await readManifest("47157");
    expect(shelby.name).toBe("Shelby");
    expect(shelby.featureCount).toBe(9667);
    expect(shelby.source).toBe("tn-shelby-current-parcels");
    const sumner = await readManifest("47165");
    expect(sumner.name).toBe("Sumner");
    expect(sumner.featureCount).toBe(15982);
    expect(sumner.source).toBe("tn-sumner-911-parcels-cama");
  });

  it("keeps each county on the public 5–150 acre extract without paid sources or owner contact fields", async () => {
    for (const county of COUNTIES) {
      const manifest = await readManifest(county.fips);
      expect(manifest.name).toBe(county.name);
      expect(manifest.state).toBe("Tennessee");
      expect(manifest.markets).toEqual([county.market]);
      expect(manifest.coverage).toBe("complete-gte-5ac");
      expect(manifest.featureCount).toBeGreaterThanOrEqual(500);
      expect(manifest.minAcres).toBe(5);
      expect(manifest.maxAcres).toBe(150);
      expect(manifest.source).toBe(`tn-oir-public-use-${county.fips}`);
      expect(manifest.queryUrl).toContain("Tennessee_Property_Boundaries_Public_Use");
      expect(manifest.ingest?.kept).toBe(manifest.featureCount);
      expect(manifest.ingest?.opportunityZoneDesignated).toBe(0);
      expect(manifest.ingest?.simplified).toBe(false);
      expect(manifest.ingest?.acreageBand).toEqual([5, 150]);
      expect(manifest.ingest?.salesVintage ?? null).toBe(county.vintage);
      const endpoint = `${manifest.source} ${manifest.queryUrl}`.toLowerCase();
      for (const token of REJECTED) expect(endpoint).not.toContain(token);
      expect(manifest.gaps.join(" ")).not.toMatch(/school grade|base flood|designated qoz/i);
      if (county.fips === "47049") {
        expect(manifest.gaps.join(" ")).toMatch(/stay empty/i);
      }
      if (county.fips === "47099") {
        expect(manifest.gaps.join(" ")).toContain("5SWQTB2G8AH9RQYE");
      }

      const lookup = JSON.parse(
        await readFile(path.join(process.cwd(), manifest.lookup), "utf8"),
      ) as Record<string, string>;
      expect(Object.keys(lookup)).toHaveLength(manifest.featureCount);

      const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties", county.fips, "tiles");
      const tiles = (await readdir(tileDir)).filter((name) => name.endsWith(".geojson"));
      expect(tiles.length).toBeGreaterThan(0);
      const today = new Date().toISOString().slice(0, 10);
      let sawSale = false;
      let sawValue = false;
      let sawZoning = false;
      for (const tile of tiles) {
        const collection = JSON.parse(await readFile(path.join(tileDir, tile), "utf8")) as {
          features: Array<{
            properties: Record<string, unknown> & {
              acreage: number;
              opportunityZone: unknown;
              oz2Eligibility: unknown;
              centroid: [number, number];
              parcelId?: string;
              marketIds?: string[];
              zoningCode?: string | null;
              lastSale?: { vintage?: string | null; price?: number | null; date?: string | null };
              tax?: { vintage?: string | null; marketValue?: number | null };
            };
            geometry: { type: string };
          }>;
        };
        for (const feature of collection.features) {
          const props = feature.properties;
          expect(props.acreage).toBeGreaterThanOrEqual(5);
          expect(props.acreage).toBeLessThanOrEqual(150);
          expect(props.opportunityZone).toBeNull();
          expect(props.oz2Eligibility).toBeNull();
          expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
          const [lon, lat] = props.centroid;
          expect(lon).toBeGreaterThan(-90.5);
          expect(lon).toBeLessThan(-81.4);
          expect(lat).toBeGreaterThan(34.8);
          expect(lat).toBeLessThan(36.8);
          expect(props.marketIds).toEqual([county.market]);
          const keys = JSON.stringify(props).toLowerCase();
          expect(keys).not.toMatch(/"phone"|"email"|ownerphone|owneremail/);
          if (props.zoningCode) sawZoning = true;
          const sale = props.lastSale;
          const tax = props.tax;
          if (sale && (sale.price != null || sale.date != null)) {
            sawSale = true;
            expect(sale.vintage).toBe(county.vintage);
            if (sale.date) expect(sale.date <= today).toBe(true);
          }
          if (tax?.marketValue != null) {
            sawValue = true;
            expect(tax.vintage).toBe(county.vintage);
          }
        }
      }
      if (county.fips === "47049") {
        expect(sawSale).toBe(false);
        expect(sawValue).toBe(false);
        expect(sawZoning).toBe(false);
      } else {
        expect(sawSale).toBe(true);
        expect(sawValue).toBe(true);
      }
      if (county.zoning === "empty") {
        expect(sawZoning).toBe(false);
        expect(manifest.gaps.join(" ")).toMatch(/stay empty/);
      } else {
        expect(sawZoning).toBe(true);
        expect(manifest.gaps.join(" ")).toMatch(/Zoning/);
      }
    }
  }, 240_000);

  it("returns Johnson parcels for a viewport on that county", async () => {
    const manifest = await readManifest("47091");
    const tileDir = path.join(process.cwd(), manifest.lookup.replace(/lookup\.json$/, "tiles"));
    const tiles = (await readdir(tileDir)).filter((name) => name.endsWith(".geojson"));
    const collection = JSON.parse(await readFile(path.join(tileDir, tiles[0]), "utf8")) as {
      features: Array<{ properties: { centroid: [number, number]; countyFips?: string } }>;
    };
    const [lon, lat] = collection.features[0].properties.centroid;
    const page = await queryParcelsInView([lon - 0.02, lat - 0.02, lon + 0.02, lat + 0.02]);
    expect(page.covered).toBe(true);
    expect(page.collection.features.some((item) => item.properties.countyFips === "47091")).toBe(true);
    expect(
      page.collection.features
        .filter((item) => item.properties.countyFips === "47091")
        .every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150),
    ).toBe(true);
  });
});
