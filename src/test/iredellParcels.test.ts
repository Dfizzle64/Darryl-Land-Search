import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection } from "../lib/types";

const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37097/county.json");

type IredellCounty = {
  fips: string;
  source: string;
  featureCount: number;
  coverage: string;
  queryUrl: string;
  gaps: string[];
  municipalities?: Array<{
    name: string;
    independentGis: boolean;
    zoningUrl?: string | null;
    fluUrl?: string | null;
    fluGap?: string | null;
    zoningJoined?: number;
    fluJoined?: number;
  }>;
  unincorporated?: { fluUrl?: string | null; fluJoined?: number; note?: string };
  zoningJoinedCount?: number;
  fluJoinedCount?: number;
  path?: string;
};

describe("Iredell County parcels", () => {
  it("opens MapGeo for an Iredell parcel id", () => {
    const link = parcelAppraiserUrl({
      parcelId: "4751155000",
      countyFips: "37097",
      appraiserUrl: "https://iredellcountync.mapgeo.io/datasets/properties?query=4751155000",
    });
    expect(link.label).toContain("Iredell");
    expect(link.href).toContain("query=4751155000");
    expect(link.href.includes(".000")).toBe(false);
  });

  it("ships TaxSQL parcels with municipal zoning and documented gaps", () => {
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as IredellCounty;
    expect(county.fips).toBe("37097");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("nc-iredell-taxsql-37097");
    expect(county.queryUrl).toContain("TaxSQL_Parcels/FeatureServer/0");
    expect(county.featureCount).toBeGreaterThan(8000);
    expect(county.featureCount).toBeLessThan(15000);
    expect(county.gaps.join(" ").toLowerCase()).toContain("no multi-year sale history");
    expect(county.gaps.join(" ")).toContain("Municipal Planning Area");
    expect(county.gaps.join(" ").toLowerCase()).toContain("adjustment factor");

    const mooresville = county.municipalities?.find((item) => item.name === "Mooresville");
    expect(mooresville?.independentGis).toBe(true);
    expect(mooresville?.zoningUrl).toContain("gis.mooresvillenc.gov");
    expect(mooresville?.fluUrl).toContain("FCLU");
    expect(mooresville?.zoningJoined ?? 0).toBeGreaterThan(0);
    expect(mooresville?.fluJoined ?? 0).toBeGreaterThan(0);

    const statesville = county.municipalities?.find((item) => item.name === "Statesville");
    expect(statesville?.independentGis).toBe(false);
    expect(statesville?.zoningUrl).toContain("Zoning/MapServer/1");
    expect(statesville?.fluUrl ?? null).toBeNull();
    expect(statesville?.fluGap ?? "").toMatch(/PDF/i);

    for (const name of ["Troutman", "Harmony", "Love Valley", "Davidson"]) {
      const town = county.municipalities?.find((item) => item.name === name);
      expect(town?.zoningUrl).toBeTruthy();
      expect(town?.fluUrl ?? null).toBeNull();
    }
    expect(county.unincorporated?.fluUrl).toContain("Zoning/MapServer/7");
    expect(county.unincorporated?.note ?? "").toMatch(/stub/i);
    expect(county.zoningJoinedCount ?? 0).toBeGreaterThan(0);
    expect(county.fluJoinedCount ?? 0).toBeGreaterThan(0);

    const tiles = path.join(process.cwd(), county.path ?? "");
    const file = readdirSync(tiles).find((name) => name.endsWith(".geojson"));
    expect(file).toBeTruthy();
    const collection = JSON.parse(readFileSync(path.join(tiles, file as string), "utf8")) as ParcelCollection;
    expect(collection.features.length).toBeGreaterThan(0);
    let sawOwner = false;
    let sawAssessed = false;
    let sawSale = false;
    for (const feature of collection.features.slice(0, 40)) {
      const props = feature.properties;
      expect(props.countyFips).toBe("37097");
      expect(props.state).toBe("North Carolina");
      expect(props.source).toBe("nc-iredell-taxsql-37097");
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.parcelId.endsWith(".000")).toBe(false);
      expect(props.tax.marketValue).toBeNull();
      expect(props.appraiserUrl).toContain("iredellcountync.mapgeo.io");
      expect(props.dataGaps?.join(" ")).toMatch(/sale history/i);
      if (props.ownerName) sawOwner = true;
      if (props.tax.assessedValue) sawAssessed = true;
      if (props.lastSale.date || props.lastSale.price) sawSale = true;
    }
    expect(sawOwner).toBe(true);
    expect(sawAssessed).toBe(true);
    expect(sawSale).toBe(true);
  });
});
