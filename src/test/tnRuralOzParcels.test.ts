import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { loadedParcelCounties } from "../lib/parcelCoverage";

/** Public 5–150 acre extracts for the 20 Tennessee rural-OZ counties in this batch. */
const COUNTIES = [
  { fips: "47001", name: "Anderson", source: "tn-oir-public-use-47001" },
  { fips: "47003", name: "Bedford", source: "tn-oir-public-use-47003" },
  { fips: "47013", name: "Campbell", source: "tn-oir-public-use-47013" },
  { fips: "47015", name: "Cannon", source: "tn-oir-public-use-47015" },
  { fips: "47023", name: "Chester", source: "tn-chester-capturecama-parcels12" },
  { fips: "47029", name: "Cocke", source: "tn-oir-public-use-47029" },
  { fips: "47043", name: "Dickson", source: "tn-oir-public-use-47043" },
  { fips: "47071", name: "Hardin", source: "tn-oir-public-use-47071" },
  { fips: "47081", name: "Hickman", source: "tn-hickman-capturecama-202305" },
  { fips: "47111", name: "Macon", source: "tn-oir-public-use-47111" },
  { fips: "47129", name: "Morgan", source: "tn-oir-public-use-47129" },
  { fips: "47133", name: "Overton", source: "tn-oir-public-use-47133" },
  { fips: "47141", name: "Putnam", source: "tn-oir-public-use-47141" },
  { fips: "47143", name: "Rhea", source: "tn-oir-public-use-47143" },
  { fips: "47145", name: "Roane", source: "tn-oir-public-use-47145" },
  { fips: "47147", name: "Robertson", source: "tn-oir-public-use-47147" },
  { fips: "47153", name: "Sequatchie", source: "tn-oir-public-use-47153" },
  { fips: "47155", name: "Sevier", source: "tn-oir-public-use-47155" },
  { fips: "47183", name: "Weakley", source: "tn-oir-public-use-47183" },
  { fips: "47189", name: "Wilson", source: "tn-oir-public-use-47189" },
] as const;

const REJECTED = ["regrid", "chesco.org", "pasda.psu.edu", "april2023parcels", "bedfordcountypa"];

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
  lookup: string;
  ingest?: {
    opportunityZoneDesignated?: number;
    simplified?: boolean;
    acreageBand?: number[];
    kept?: number;
  };
};

async function readManifest(fips: string): Promise<CountyManifest> {
  const raw = await readFile(
    path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips, "county.json"),
    "utf8",
  );
  return JSON.parse(raw) as CountyManifest;
}

describe("Tennessee rural parcel counties", () => {
  it("lists every loaded county on the coverage manifest", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    for (const county of COUNTIES) {
      expect(loaded.find((row) => row.fips === county.fips)).toEqual({
        fips: county.fips,
        name: county.name,
        state: "Tennessee",
      });
    }
  });

  it("keeps each county in the 5–150 acre public extract without a Pennsylvania or paid source", async () => {
    for (const county of COUNTIES) {
      const manifest = await readManifest(county.fips);
      expect(manifest.name).toBe(county.name);
      expect(manifest.state).toBe("Tennessee");
      expect(manifest.coverage).toBe("complete-gte-5ac");
      expect(manifest.featureCount).toBeGreaterThanOrEqual(500);
      expect(manifest.minAcres).toBe(5);
      expect(manifest.maxAcres).toBe(150);
      expect(manifest.source).toBe(county.source);
      expect(manifest.ingest?.kept).toBe(manifest.featureCount);
      expect(manifest.ingest?.opportunityZoneDesignated).toBe(0);
      expect(manifest.ingest?.simplified).toBe(false);
      expect(manifest.ingest?.acreageBand).toEqual([5, 150]);
      const endpoint = `${manifest.source} ${manifest.queryUrl}`.toLowerCase();
      for (const token of REJECTED) {
        expect(endpoint).not.toContain(token);
      }
      if (county.fips === "47003") {
        expect(manifest.queryUrl).toContain("Tennessee_Property_Boundaries_Public_Use");
      }
      if (county.fips === "47081") {
        expect(manifest.queryUrl).toContain("HickmanTN05182023");
      }
      if (county.fips === "47023") {
        expect(manifest.queryUrl).toContain("ChesterTN/ChesterCapture");
      }

      const lookup = JSON.parse(
        await readFile(path.join(process.cwd(), manifest.lookup), "utf8"),
      ) as Record<string, string>;
      expect(Object.keys(lookup)).toHaveLength(manifest.featureCount);

      const tileDir = path.join(process.cwd(), "data/fixtures/market-parcels/counties", county.fips, "tiles");
      const tiles = (await readdir(tileDir)).filter((name) => name.endsWith(".geojson"));
      expect(tiles.length).toBeGreaterThan(0);
      const collection = JSON.parse(await readFile(path.join(tileDir, tiles[0]), "utf8")) as {
        features: Array<{
          properties: {
            acreage: number;
            opportunityZone: unknown;
            oz2Eligibility: unknown;
            centroid: [number, number];
            lastSale?: { vintage?: string | null; price?: number | null; date?: string | null };
            tax?: { vintage?: string | null; marketValue?: number | null };
          };
          geometry: { type: string };
        }>;
      };
      const feature = collection.features[0];
      expect(feature).toBeTruthy();
      expect(feature.properties.acreage).toBeGreaterThanOrEqual(5);
      expect(feature.properties.acreage).toBeLessThanOrEqual(150);
      expect(feature.properties.opportunityZone).toBeNull();
      expect(feature.properties.oz2Eligibility).toBeNull();
      expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
      const [lon, lat] = feature.properties.centroid;
      expect(lon).toBeGreaterThan(-90.5);
      expect(lon).toBeLessThan(-81.4);
      expect(lat).toBeGreaterThan(34.8);
      expect(lat).toBeLessThan(36.8);
      const sale = feature.properties.lastSale;
      if (sale && (sale.price != null || sale.date != null)) {
        expect(sale.vintage).toBe("2023");
      }
      const tax = feature.properties.tax;
      if (tax?.marketValue != null && county.fips !== "47023") {
        expect(tax.vintage).toBe("2023");
      }
    }
  });
});
