import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";

/**
 * Next 20 rural-OZ counties in pass1_order that were not already loaded.
 * Bradley (47011) and Grainger (47057) were skipped because earlier pulls
 * already published complete extracts.
 */
const COUNTIES = [
  { fips: "47059", name: "Greene", market: "Knoxville", vintage: "2023" },
  { fips: "47079", name: "Henry", market: "Memphis", vintage: "2023" },
  { fips: "47177", name: "Warren", market: "Nashville", vintage: "2023" },
  { fips: "47017", name: "Carroll", market: "Jackson", vintage: "2023" },
  { fips: "47025", name: "Claiborne", market: "Knoxville", vintage: "2023" },
  { fips: "47031", name: "Coffee", market: "Nashville", vintage: "2023" },
  { fips: "47045", name: "Dyer", market: "Memphis", vintage: "2023" },
  { fips: "47053", name: "Gibson", market: "Memphis", vintage: "2023" },
  { fips: "47061", name: "Grundy", market: "Chattanooga", vintage: "2023" },
  { fips: "47063", name: "Hamblen", market: "Knoxville", vintage: "2026" },
  { fips: "47069", name: "Hardeman", market: "Memphis", vintage: "2023" },
  { fips: "47075", name: "Haywood", market: "Memphis", vintage: "2023" },
  { fips: "47097", name: "Lauderdale", market: "Memphis", vintage: "2023" },
  { fips: "47109", name: "McNairy", market: "Memphis", vintage: "2023" },
  { fips: "47123", name: "Monroe", market: "Knoxville", vintage: "2023" },
  { fips: "47007", name: "Bledsoe", market: "Chattanooga", vintage: "2023" },
  { fips: "47035", name: "Cumberland", market: "Knoxville", vintage: "2023" },
  { fips: "47039", name: "Decatur", market: "Jackson", vintage: "2023" },
  { fips: "47041", name: "DeKalb", market: "Nashville", vintage: "2023" },
  { fips: "47077", name: "Henderson", market: "Memphis", vintage: "2023" },
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
    salesVintage?: string;
  };
};

async function readManifest(fips: string): Promise<CountyManifest> {
  const raw = await readFile(
    path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips, "county.json"),
    "utf8",
  );
  return JSON.parse(raw) as CountyManifest;
}

describe("Tennessee rural parcel batch 2", () => {
  it("lists the twenty counties and leaves Bradley and Grainger on their earlier extracts", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    for (const county of COUNTIES) {
      expect(loaded.find((row) => row.fips === county.fips)).toEqual({
        fips: county.fips,
        name: county.name,
        state: "Tennessee",
      });
    }
    const bradley = await readManifest("47011");
    expect(bradley.name).toBe("Bradley");
    expect(bradley.featureCount).toBe(6336);
    expect(bradley.source).toBe("tn-cleveland-parcels-impact-47011");
    const grainger = await readManifest("47057");
    expect(grainger.name).toBe("Grainger");
    expect(grainger.featureCount).toBe(6406);
    expect(grainger.source).toBe("tn-impact-47057");
  });

  it("keeps each county on the OIR 5–150 acre extract without paid sources or owner contact fields", async () => {
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
      expect(manifest.ingest?.salesVintage).toBe(county.vintage);
      const endpoint = `${manifest.source} ${manifest.queryUrl}`.toLowerCase();
      for (const token of REJECTED) expect(endpoint).not.toContain(token);
      expect(manifest.gaps.join(" ")).not.toMatch(/school grade|base flood|designated qoz/i);
      if (county.fips === "47063") {
        expect(manifest.gaps.join(" ")).toContain("mh-gis.com");
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
      expect(sawSale).toBe(true);
      if (county.fips === "47075") {
        expect(sawValue).toBe(false);
        expect(manifest.gaps.join(" ")).toContain("Assessment_Data_38_APPRAISAL");
      } else {
        expect(sawValue).toBe(true);
      }
    }
  }, 180_000);

  it("returns Greene parcels for a viewport on that county", async () => {
    const manifest = await readManifest("47059");
    const tileDir = path.join(process.cwd(), manifest.lookup.replace(/lookup\.json$/, "tiles"));
    const tiles = (await readdir(tileDir)).filter((name) => name.endsWith(".geojson"));
    const collection = JSON.parse(await readFile(path.join(tileDir, tiles[0]), "utf8")) as {
      features: Array<{ properties: { centroid: [number, number]; countyFips?: string } }>;
    };
    const [lon, lat] = collection.features[0].properties.centroid;
    const page = await queryParcelsInView([lon - 0.02, lat - 0.02, lon + 0.02, lat + 0.02]);
    expect(page.covered).toBe(true);
    expect(page.collection.features.some((item) => item.properties.countyFips === "47059")).toBe(true);
    expect(
      page.collection.features
        .filter((item) => item.properties.countyFips === "47059")
        .every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150),
    ).toBe(true);
  });
});
