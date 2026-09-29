import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { loadMarketParcelIndex } from "../lib/data/marketParcelStore";
import { loadOrlandoParcelsMeta } from "../lib/data/orlandoParcelStore";
import { queryParcelsInView } from "../lib/data/parcelViewQuery";
import { loadedParcelCounties } from "../lib/parcelCoverage";

/**
 * Remaining rural-OZ counties after Carter (pass1 order 65) that were not
 * already a complete extract, then rest-of-state counties in rest order
 * until the batch reached 20. Jefferson, Knox, and the eight already-complete
 * rest-of-state counties stay on their earlier extracts.
 */
const COUNTIES = [
  { fips: "47117", name: "Marshall", market: "Nashville", vintage: "2023", zoning: "polygon" },
  { fips: "47135", name: "Perry", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47139", name: "Polk", market: "Chattanooga", vintage: "2023", zoning: "empty" },
  { fips: "47159", name: "Smith", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47161", name: "Stewart", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47173", name: "Union", market: "Knoxville", vintage: "2023", zoning: "empty" },
  { fips: "47185", name: "White", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47033", name: "Crockett", market: "Jackson", vintage: "2023", zoning: "empty" },
  { fips: "47047", name: "Fayette", market: "Memphis", vintage: "2023", zoning: "attribute" },
  { fips: "47055", name: "Giles", market: "Huntsville", vintage: "2023", zoning: "empty" },
  { fips: "47083", name: "Houston", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47101", name: "Lewis", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47103", name: "Lincoln", market: "Huntsville", vintage: "2023", zoning: "attribute" },
  { fips: "47105", name: "Loudon", market: "Knoxville", vintage: "2023", zoning: "empty" },
  { fips: "47121", name: "Meigs", market: "Chattanooga", vintage: "2025", zoning: "polygon" },
  { fips: "47127", name: "Moore", market: "Huntsville", vintage: "2023", zoning: "empty" },
  { fips: "47169", name: "Trousdale", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47171", name: "Unicoi", market: "Knoxville", vintage: "2026", zoning: "sales" },
  { fips: "47175", name: "Van Buren", market: "Nashville", vintage: "2023", zoning: "empty" },
  { fips: "47179", name: "Washington", market: "Knoxville", vintage: "2026", zoning: "polygon" },
] as const;

const ALREADY_COMPLETE = [
  { fips: "47089", name: "Jefferson", featureCount: 6586, source: "tn-impact-47089" },
  { fips: "47093", name: "Knox", featureCount: 4569, source: "kgis-parcel-search" },
  { fips: "47009", name: "Blount", featureCount: 8183, source: "tn-blount-agol-47009" },
  { fips: "47021", name: "Cheatham", featureCount: 5426, source: "apsu-cheatgis-47021" },
  { fips: "47037", name: "Davidson", featureCount: 9478, source: "tn-metro-davidson-parcels" },
  { fips: "47065", name: "Hamilton", featureCount: 9162, source: "tn-hamilton-live-parcels" },
  { fips: "47113", name: "Madison", featureCount: 6384, source: "tn-impact-47113" },
  { fips: "47125", name: "Montgomery", featureCount: 7038, source: "tn-mcgtn-cama-47125" },
  { fips: "47149", name: "Rutherford", featureCount: 9677, source: "tn-rutherford-agol-parcels" },
  { fips: "47187", name: "Williamson", featureCount: 10760, source: "tn-williamson-datapull-47187" },
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
    spatialParentMatched?: number;
  };
};

async function readManifest(fips: string): Promise<CountyManifest> {
  const raw = await readFile(
    path.join(process.cwd(), "data/fixtures/market-parcels/counties", fips, "county.json"),
    "utf8",
  );
  return JSON.parse(raw) as CountyManifest;
}

describe("Tennessee rural parcel batch 4", () => {
  it("lists the twenty counties and leaves already-complete extracts in place", async () => {
    const [index, orlando] = await Promise.all([loadMarketParcelIndex(), loadOrlandoParcelsMeta()]);
    const loaded = loadedParcelCounties(index.markets, orlando.counties);
    for (const county of COUNTIES) {
      expect(loaded.find((row) => row.fips === county.fips)).toEqual({
        fips: county.fips,
        name: county.name,
        state: "Tennessee",
      });
    }
    for (const prior of ALREADY_COMPLETE) {
      const manifest = await readManifest(prior.fips);
      expect(manifest.name).toBe(prior.name);
      expect(manifest.featureCount).toBe(prior.featureCount);
      expect(manifest.source).toBe(prior.source);
      expect(manifest.coverage).toBe("complete-gte-5ac");
    }
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
      if (county.fips === "47135") {
        expect(manifest.gaps.join(" ")).toMatch(/spatial-parent-2023/);
        expect(manifest.ingest?.spatialParentMatched).toBeGreaterThan(0);
      }
      if (county.fips === "47121") {
        expect(manifest.gaps.join(" ")).toContain("Meigs_Parcels_Joined");
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
      let sawSpatial = false;
      let sawDirect = false;
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
              joinMethod?: string;
              parentParcelId?: string;
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
          if (props.joinMethod === "spatial-parent-2023") {
            sawSpatial = true;
            expect(props.parentParcelId).toBeTruthy();
          } else {
            expect(props.joinMethod ?? null).toBeNull();
            sawDirect = true;
          }
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
      expect(sawValue).toBe(true);
      expect(sawDirect).toBe(true);
      if (county.fips === "47135") expect(sawSpatial).toBe(true);
      else expect(sawSpatial).toBe(false);
      if (county.zoning === "empty") {
        expect(sawZoning).toBe(false);
        expect(manifest.gaps.join(" ")).toMatch(/stay empty/);
      } else {
        expect(sawZoning).toBe(true);
        expect(manifest.gaps.join(" ")).toMatch(/zoning/i);
      }
    }
  }, 300_000);

  it("returns Marshall parcels for a viewport on that county", async () => {
    const manifest = await readManifest("47117");
    const tileDir = path.join(process.cwd(), manifest.lookup.replace(/lookup\.json$/, "tiles"));
    const tiles = (await readdir(tileDir)).filter((name) => name.endsWith(".geojson"));
    const collection = JSON.parse(await readFile(path.join(tileDir, tiles[0]), "utf8")) as {
      features: Array<{ properties: { centroid: [number, number]; countyFips?: string } }>;
    };
    const [lon, lat] = collection.features[0].properties.centroid;
    const page = await queryParcelsInView([lon - 0.02, lat - 0.02, lon + 0.02, lat + 0.02]);
    expect(page.covered).toBe(true);
    expect(page.collection.features.some((item) => item.properties.countyFips === "47117")).toBe(true);
    expect(
      page.collection.features
        .filter((item) => item.properties.countyFips === "47117")
        .every((item) => (item.properties.acreage ?? 0) >= 5 && (item.properties.acreage ?? 0) <= 150),
    ).toBe(true);
  });
});
