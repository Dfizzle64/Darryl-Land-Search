import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parcelAppraiserUrl } from "../lib/format";
import { inMarketAcreageBand } from "../lib/marketParcels";
import type { ParcelCollection, ParcelProperties } from "../lib/types";

const root = process.cwd();

function countyMeta(fips: string) {
  const file = path.join(root, "data/fixtures/market-parcels/counties", fips, "county.json");
  return JSON.parse(readFileSync(file, "utf8")) as {
    featureCount: number;
    coverage: string;
    source: string;
    queryUrl: string | null;
    gaps: string[];
    minAcres: number;
    maxAcres: number;
  };
}

function eachParcel(fips: string, visit: (props: ParcelProperties) => void) {
  const tiles = path.join(root, "data/fixtures/market-parcels/counties", fips, "tiles");
  expect(existsSync(tiles)).toBe(true);
  for (const name of readdirSync(tiles)) {
    if (!name.endsWith(".geojson")) continue;
    const collection = JSON.parse(readFileSync(path.join(tiles, name), "utf8")) as ParcelCollection;
    for (const feature of collection.features) visit(feature.properties);
  }
}

describe("Alabama appraiser links", () => {
  it("points Baldwin, Marshall, and Shelby at their own public search", () => {
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "01003" }).href).toBe(
      "https://isv.kcsgis.com/al.baldwin_revenue/",
    );
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "01095" }).href).toBe(
      "https://isv.kcsgis.com/al.marshall_revenue/",
    );
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "01117" }).href).toBe(
      "https://ptc.shelbyal.com/propsearch",
    );
    const walker = parcelAppraiserUrl({ parcelId: "1", countyFips: "01127" });
    expect(walker.href).toBeNull();
  });
});

describe("Alabama GIS re-chase extracts", () => {
  it("keeps Walker, Washington AL, and Escambia AL as gaps", () => {
    for (const fips of ["01127", "01129", "01053"]) {
      const row = countyMeta(fips);
      expect(row.featureCount).toBe(0);
      expect(row.coverage).toBe("gap");
    }
    const morgan = countyMeta("01103");
    expect(morgan.featureCount).toBe(827);
    expect(morgan.source).toBe("al-morgan-vam-10");
    expect(morgan.coverage).toBe("complete-gte-5ac");
    const gaps = morgan.gaps.join(" ");
    expect(gaps.toLowerCase()).not.toContain("decatur, illinois");
    expect(gaps.toLowerCase()).not.toContain("decatur il");
    expect(gaps).toMatch(/MapGeo/);
  });

  it("loads Marshall County from web5 Public/37 using CalcAcres, not the Huntsville fringe sample", () => {
    const row = countyMeta("01095");
    expect(row.coverage).toBe("complete-gte-5ac");
    expect(row.featureCount).toBeGreaterThan(8000);
    expect(row.minAcres).toBe(5);
    expect(row.maxAcres).toBe(150);
    expect(row.source).toBe("al-marshall-public-37");
    expect(row.queryUrl).toContain("web5.kcsgis.com");
    expect(row.queryUrl).toContain("Marshall/Public/MapServer/37");
    expect(row.queryUrl).not.toContain("CombinedParcels");
    expect(row.queryUrl).not.toContain("web3.kcsgis.com");
    expect(row.queryUrl).not.toContain("web4.kcsgis.com");
    expect(row.queryUrl).not.toContain("web6.kcsgis.com");
    const gaps = row.gaps.join(" ");
    expect(gaps).toContain("CombinedParcels");
    expect(gaps).toMatch(/zoning is left null/i);
    let parcels = 0;
    eachParcel("01095", (props) => {
      parcels += 1;
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.zoningCode).toBeNull();
      expect(props.zoningOverlay ?? null).toBeNull();
      expect(props.flu).toBeNull();
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.countyFips).toBe("01095");
      expect(props.marketIds).toContain("Huntsville");
      expect(props.marketIds).not.toContain("Orlando");
    });
    expect(parcels).toBe(row.featureCount);
  });

  it("joins Daphne Class zoning and FLU, and Fairhope base districts, onto Baldwin parcels", () => {
    const row = countyMeta("01003");
    expect(row.coverage).toBe("complete-gte-5ac");
    expect(row.featureCount).toBeGreaterThan(10000);
    expect(row.source).toBe("al-baldwin-public-isv");
    expect(row.queryUrl).toContain("Baldwin_Public_ISV/MapServer/31");
    expect(row.queryUrl).not.toContain("BJisQXdgVScP0JMy");
    expect(row.queryUrl).not.toContain("al05baldrevenue");
    const gaps = row.gaps.join(" ");
    expect(gaps).toContain("Class");
    expect(gaps).toContain("Future_Dev");
    expect(gaps).toContain("Master_COF_ZoningDistrict");
    expect(gaps).toMatch(/AO\/MO|overlay/i);
    expect(gaps).toContain("BJis");
    expect(gaps).not.toContain("Envision_Placetype_Map/3 is the FLU source");
    const counts = { daphne: 0, daphneFlu: 0, fairhope: 0, overlayAsCode: 0, overlayNoted: 0 };
    const fairhopeCodes = new Set<string>();
    eachParcel("01003", (props) => {
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.marketIds).toEqual(expect.arrayContaining(["Mobile", "Pensacola"]));
      const code = props.zoningCode?.toLowerCase() ?? "";
      if (code.includes("overlay") || code === "airport overlay district" || code === "medical overlay district") {
        counts.overlayAsCode += 1;
      }
      if (props.jurisdictionCode === "Daphne") {
        counts.daphne += 1;
        expect(props.zoningCode == null || props.zoningCode.length <= 16).toBe(true);
        expect(props.zoningCode ?? "").not.toMatch(/Residential|Business|Density/i);
      }
      if (props.flu?.code) {
        counts.daphneFlu += 1;
        expect(props.flu.jurisdiction).toBe("Daphne");
        expect(props.flu.source).toContain("APRIL_2026");
        expect(props.jurisdictionCode).toBe("Daphne");
      }
      if (props.jurisdictionCode === "Fairhope") {
        counts.fairhope += 1;
        if (props.zoningCode) fairhopeCodes.add(props.zoningCode);
        expect(props.flu).toBeNull();
      }
      if (props.zoningOverlay) counts.overlayNoted += 1;
    });
    expect(counts.overlayAsCode).toBe(0);
    expect(counts.daphne).toBeGreaterThan(150);
    expect(counts.daphneFlu).toBeGreaterThan(100);
    expect(counts.fairhope).toBeGreaterThan(80);
    expect(fairhopeCodes.has("R-1") || fairhopeCodes.has("PUD") || fairhopeCodes.has("M-1")).toBe(true);
    expect([...fairhopeCodes].some((code) => /overlay/i.test(code))).toBe(false);
    expect(counts.overlayNoted).toBeGreaterThan(0);
  });

  it("joins Alabaster ZoneCode onto Shelby parcels by the city layer, not layer 78", () => {
    const row = countyMeta("01117");
    expect(row.coverage).toBe("complete-gte-5ac");
    expect(row.featureCount).toBeGreaterThan(8000);
    expect(row.source).toBe("al-shelby-cadastral-2025");
    expect(row.queryUrl).toContain("Cadastral_2025/MapServer/91");
    expect(row.queryUrl).not.toContain("Zone_Layer_VIEW");
    expect(row.queryUrl).not.toContain("/78");
    const gaps = row.gaps.join(" ");
    expect(gaps).toContain("Zoning_Current_VIEWONLY");
    expect(gaps).toContain("400");
    let alabaster = 0;
    const codes = new Set<string>();
    eachParcel("01117", (props) => {
      expect(inMarketAcreageBand(props.acreage)).toBe(true);
      expect(props.opportunityZone).toBeNull();
      expect(props.oz2Eligibility).toBeNull();
      expect(props.flu).toBeNull();
      expect(props.marketIds).toContain("Birmingham");
      if (props.jurisdictionCode === "Alabaster") {
        alabaster += 1;
        expect(props.zoningCode).toBeTruthy();
        expect(props.zoningCode ?? "").not.toMatch(/overlay/i);
        codes.add(props.zoningCode ?? "");
      }
    });
    expect(alabaster).toBeGreaterThan(250);
    expect(codes.size).toBeGreaterThan(1);
  });
});
