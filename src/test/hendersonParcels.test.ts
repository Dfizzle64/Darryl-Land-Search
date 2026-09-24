import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl } from "../lib/format";
import { catalogForMarket } from "../lib/markets";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { EligibleMarketsCatalog, ParcelCollection, RuralMarketsCatalog } from "../lib/types";

const countyPath = path.join(process.cwd(), "data/fixtures/market-parcels/counties/37089/county.json");

type CityRow = {
  name: string;
  independentGis?: boolean;
  zoningUrl?: string | null;
  fluUrl?: string | null;
  fluGap?: string | null;
  parcelCount?: number;
  zoningJoined?: number;
  fluJoined?: number;
  countyFluFallback?: number;
};

type HendersonCounty = {
  fips: string;
  source: string;
  featureCount: number;
  coverage: string;
  minAcres: number;
  maxAcres: number;
  queryUrl: string;
  gaps: string[];
  markets?: string[];
  municipalities?: CityRow[];
  unincorporated?: { zoningUrl?: string; fluUrl?: string; zoningJoined?: number; fluJoined?: number; note?: string };
  zoningJoinedCount?: number;
  fluJoinedCount?: number;
  citiesStubCount?: number;
  stubUsedAsZoning?: number;
  acreageField?: string;
  path?: string;
};

describe("Henderson County parcels", () => {
  it("opens the NCPTS parcel record for a Henderson parcel key", () => {
    const link = parcelAppraiserUrl({
      parcelId: "0507003820",
      countyFips: "37089",
      appraiserUrl: "https://lrcpwa.ncptscloud.com/henderson/parcel-detail/113959",
    });
    expect(link.label).toContain("Henderson");
    expect(link.href).toContain("/henderson/parcel-detail/113959");
  });

  it("does not invent an Asheville opportunity zone pack", () => {
    const other = JSON.parse(readFileSync("data/fixtures/oz2-other-msas.json", "utf8")) as EligibleMarketsCatalog;
    const rural = JSON.parse(readFileSync("data/fixtures/oz2-rural-markets.json", "utf8")) as RuralMarketsCatalog;
    const urban = JSON.parse(readFileSync("data/fixtures/oz2-urban-markets.json", "utf8")) as EligibleMarketsCatalog;
    const summary = catalogForMarket(rural, urban, other, "Asheville");
    expect(summary.rowCount).toBe(0);
    expect(summary.counties.map((item) => item.county)).toEqual(["Buncombe", "Henderson"]);
    expect(other.rows.some((row) => row.market === "Asheville")).toBe(false);
    expect(JSON.stringify(other)).not.toMatch(/Henderson County opportunity zone/i);
  });

  it("ships calculated-acre parcels with city zoning and documented FLU gaps", () => {
    expect(existsSync(countyPath)).toBe(true);
    const county = JSON.parse(readFileSync(countyPath, "utf8")) as HendersonCounty;
    expect(county.fips).toBe("37089");
    expect(county.coverage).toBe("complete-gte-5ac");
    expect(county.source).toBe("nc-henderson-parcels-37089");
    expect(county.acreageField).toBe("CALCULATED_ACRES");
    expect(county.queryUrl).toContain("Parcels/FeatureServer/0");
    expect(county.minAcres).toBe(5);
    expect(county.maxAcres).toBe(150);
    expect(county.featureCount).toBeGreaterThan(5500);
    expect(county.featureCount).toBeLessThan(7000);
    expect(county.markets).toContain("Asheville");
    expect(county.gaps.join(" ")).toMatch(/Cities/);
    expect(county.stubUsedAsZoning).toBe(0);
    expect(county.citiesStubCount ?? 0).toBeGreaterThan(0);

    const hendersonville = county.municipalities?.find((item) => item.name === "Hendersonville");
    expect(hendersonville?.independentGis).toBe(true);
    expect(hendersonville?.zoningUrl).toMatch(/COH_Zoning_Test|Primary_GISWeb_Layers\/83/);
    expect(hendersonville?.fluUrl).toContain("Future_Land_Use");
    expect(hendersonville?.fluGap ?? null).toBeNull();
    expect(hendersonville?.zoningJoined ?? 0).toBeGreaterThan(0);
    expect(hendersonville?.fluJoined ?? 0).toBeGreaterThan(0);

    for (const name of ["Fletcher", "Mills River", "Laurel Park", "Flat Rock"]) {
      const city = county.municipalities?.find((item) => item.name === name);
      expect(city?.independentGis).toBe(false);
      expect(city?.zoningUrl).toBeTruthy();
      expect(city?.fluUrl).toContain("Planning_and_Development/MapServer/88");
      expect(city?.fluGap ?? "").toMatch(/No dedicated public FLU/i);
      expect(city?.fluJoined ?? 0).toBe(0);
    }

    expect(county.unincorporated?.zoningUrl).toContain("MapServer/85");
    expect(county.unincorporated?.fluUrl).toContain("MapServer/88");
    expect(county.unincorporated?.note ?? "").toMatch(/stub/i);
    expect(county.zoningJoinedCount ?? 0).toBeGreaterThan(0);
    expect(county.fluJoinedCount ?? 0).toBeGreaterThan(0);

    const tiles = path.join(process.cwd(), county.path ?? "");
    const files = readdirSync(tiles).filter((name) => name.endsWith(".geojson"));
    expect(files.length).toBeGreaterThan(0);
    let sawOwner = false;
    let sawSale = false;
    let sawCityFlu = false;
    let sawCountyFlu = false;
    let counted = 0;
    for (const file of files) {
      const collection = JSON.parse(readFileSync(path.join(tiles, file), "utf8")) as ParcelCollection;
      for (const feature of collection.features) {
        const props = feature.properties;
        counted += 1;
        expect(props.countyFips).toBe("37089");
        expect(props.state).toBe("North Carolina");
        expect(props.countyName).toBe("Henderson");
        expect(props.source).toBe("nc-henderson-parcels-37089");
        expect(props.marketIds).toContain("Asheville");
        expect(inMarketAcreageBand(props.acreage)).toBe(true);
        expect(props.zoningCode).not.toBe("Cities");
        expect(props.zoningCode).not.toBe("NO");
        expect(props.opportunityZone).toBeNull();
        expect(props.oz2Eligibility).toBeNull();
        expect(props.appraiserUrl ?? "").toMatch(/ncptscloud\.com\/henderson\//);
        const [lon, lat] = props.centroid;
        expect(lon).toBeGreaterThan(-83.05);
        expect(lon).toBeLessThan(-82.05);
        expect(lat).toBeGreaterThan(35);
        expect(lat).toBeLessThan(35.65);
        if (props.ownerName) sawOwner = true;
        if (props.lastSale.date || props.lastSale.price) sawSale = true;
        if (props.flu?.source === "hendersonville-2045-flu") sawCityFlu = true;
        if (props.flu?.source === "henderson-county-flu-2024") sawCountyFlu = true;
      }
    }
    expect(counted).toBe(county.featureCount);
    expect(sawOwner).toBe(true);
    expect(sawSale).toBe(true);
    expect(sawCityFlu).toBe(true);
    expect(sawCountyFlu).toBe(true);
  });
});
