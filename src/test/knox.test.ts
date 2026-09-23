import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import {
  FARRAGUT_FLU_GAP,
  KNOX_ACREAGE,
  KNOX_CITY_FLU_GAP,
  KNOX_FIPS,
  KNOX_PARCEL_BLOCKER,
  geometryBbox,
  indexKnoxOverlays,
  joinKnoxDesignation,
  knoxAcreage,
  knoxAppraiserUrl,
  knoxDate,
  knoxMailing,
  knoxOverlaysAtPoint,
  knoxSitus,
  knoxZoningCode,
  mapKnoxParcel,
  pointInKnoxGeometry,
  resolveKnoxMunicipality,
  type KnoxFluProperties,
  type KnoxOverlayFeature,
  type KnoxPolygonGeometry,
  type KnoxZoningProperties,
  type FarragutZoningProperties,
} from "../lib/knox";

const square = (west: number, south: number, east: number, north: number): KnoxPolygonGeometry => ({
  type: "Polygon",
  coordinates: [
    [
      [west, south],
      [east, south],
      [east, north],
      [west, north],
      [west, south],
    ],
  ],
});

function feature<P>(properties: P, geometry: KnoxPolygonGeometry): KnoxOverlayFeature<P> {
  return { type: "Feature", properties, geometry };
}

describe("Knox parcel mapping", () => {
  it("filters on calculated acres and falls back to recorded acres only when calculated is missing", () => {
    expect(KNOX_ACREAGE).toEqual({ min: 5, max: 150 });
    expect(knoxAcreage({ CALCULATED_AREA: 5, RECORDED_AREA: 1 })).toMatchObject({ acres: 5, field: "CALCULATED_AREA", inBand: true });
    expect(knoxAcreage({ CALCULATED_AREA: 150, RECORDED_AREA: 1 })).toMatchObject({ inBand: true });
    expect(knoxAcreage({ CALCULATED_AREA: 4.9, RECORDED_AREA: 20 })).toMatchObject({
      acres: 4.9,
      field: "CALCULATED_AREA",
      inBand: false,
    });
    expect(knoxAcreage({ CALCULATED_AREA: null, RECORDED_AREA: 12 })).toMatchObject({
      acres: 12,
      field: "RECORDED_AREA",
      inBand: true,
    });
    expect(knoxAcreage({ SYS_CALC_AREA: 40 })).toMatchObject({ acres: null, inBand: false });
  });

  it("maps owner, mailing, situs, sale, and appraised values without inventing blanks", () => {
    const parcel = mapKnoxParcel(
      {
        PARCELID: "142 013",
        PARCELID_1: "142 013",
        BASE_PARCELID: "142013",
        PBAID: "pba-1",
        OWNER: "Example Holdings LLC",
        FULL_ADDRESS: "100 Main St",
        CALCULATED_AREA: 12.5,
        RECORDED_AREA: 12,
        FULL_MAIL_ADDRESS: "PO Box 1",
        MAIL_CITY: "Knoxville",
        MAIL_STATE: "TN",
        MAIL_ZIP_CODE: "37902",
        MAIL_ZIP_CODE_SUF: "1234",
        SALE_DATE: "2024-05-01T00:00:00Z",
        DATE_PURCHASED: 1714521600000,
        PURCHASE_PRICE: 250000,
        VALIDITY_FLAG: "Q",
        DEED_BOOK: "10",
        DEED_PAGE: "20",
        ODOC_BOOK: "11",
        ODOC_PAGE: "21",
        APPRAISED_LAND: 100000,
        APPRAISED_BLDG: 50000,
        APPRAISED_TOTAL: 150000,
        ASSESSED_TOTAL: 37500,
        LANDUSE: "100",
      },
      [-83.92, 35.96],
      null,
    );
    expect(parcel).toMatchObject({
      id: "47093:142 013",
      parcelId: "142 013",
      countyFips: KNOX_FIPS,
      state: "Tennessee",
      baseParcelId: "142013",
      pbaid: "pba-1",
      ownerName: "Example Holdings LLC",
      situsAddress: "100 Main St",
      acreage: 12.5,
      recordedAcreage: 12,
      source: "kgis-globalsearch",
      mailingAddress: { line1: "PO Box 1", city: "Knoxville", state: "TN", zip: "37902-1234" },
      lastSale: {
        date: "2024-05-01",
        price: 250000,
        qualified: "Q",
        deedBook: "10",
        deedPage: "20",
        odocBook: "11",
        odocPage: "21",
      },
      tax: {
        marketValue: 150000,
        assessedValue: 37500,
        appraisedLand: 100000,
        appraisedBuilding: 50000,
        taxableValue: null,
        taxes: null,
      },
    });
    expect(parcel?.appraiserUrl).toBe(knoxAppraiserUrl("142 013"));
    expect(parcel?.lastSale.datePurchased).toBe("2024-05-01");
  });

  it("drops parcels outside the acreage band and builds the Vision datalet link", () => {
    expect(mapKnoxParcel({ PARCELID: "094LE041", CALCULATED_AREA: 4 }, [-83.9, 35.9], null)).toBeNull();
    expect(mapKnoxParcel({ PARCELID: "094LE041", CALCULATED_AREA: 151 }, [-83.9, 35.9], null)).toBeNull();
    expect(knoxAppraiserUrl("094LE041")).toBe(
      "https://propertyinfo.knoxcountytn.gov/Datalets/Datalet.aspx?ParcelID=094LE041&UseSearch=yes",
    );
    expect(knoxAppraiserUrl("142 013")).toContain("ParcelID=142%20013");
    expect(parcelAppraiserUrl({ parcelId: "094LE041", countyFips: "47093" })).toEqual({
      href: knoxAppraiserUrl("094LE041"),
      label: "Open Knox County Property Assessor record",
    });
    expect(knoxSitus({ LOC_HOUSE_NUMBER: "10", LOC_STREET_NAME: "Kingston", LOC_STREET_TYPE: "Pike" })).toBe(
      "10 Kingston Pike",
    );
    expect(knoxZoningCode("C-G-2", "H")).toBe("C-G-2 H");
    expect(knoxZoningCode("RN-2", null)).toBe("RN-2");
    expect(knoxMailing({ FULL_MAIL_CITY_STATE_ZIP: "Knoxville TN 37902" }).city).toBe("Knoxville");
    expect(knoxDate(null)).toBeNull();
  });
});

describe("Knox municipality join", () => {
  const knoxville = square(-84.0, 35.9, -83.8, 36.05);
  const farragut = square(-84.25, 35.84, -84.1, 35.92);
  const cityZone = feature<KnoxZoningProperties>(
    { zone1: "RN-5", zone2: null, zoningCode: "RN-5", zoneType: "City of Knoxville", areaAcres: 10, source: "test" },
    square(-83.95, 35.94, -83.9, 35.98),
  );
  const countyZone = feature<KnoxZoningProperties>(
    { zone1: "CA", zone2: "H", zoningCode: "CA H", zoneType: "Knox County", areaAcres: 40, source: "test" },
    square(-83.7, 36.05, -83.6, 36.15),
  );
  const place = feature<KnoxFluProperties>(
    { placeType: "SR", gppCompatibility: null, source: "advance-knox" },
    square(-83.7, 36.05, -83.6, 36.15),
  );
  const farragutZone = feature<FarragutZoningProperties>(
    { zone: "R-2", type: null, codeUrl: null, acres: 8, source: "farragut-zoning" },
    farragut,
  );
  const context = {
    boundaries: { knoxville, farragut },
    zoning: indexKnoxOverlays([cityZone, countyZone]),
    countyFlu: indexKnoxOverlays([place]),
    farragutZoning: indexKnoxOverlays([farragutZone]),
  };

  it("keeps Farragut, Knoxville, and unincorporated on different layers", () => {
    expect(resolveKnoxMunicipality(-84.2, 35.88, context.boundaries)).toBe("farragut");
    expect(resolveKnoxMunicipality(-83.92, 35.96, context.boundaries)).toBe("knoxville");
    expect(resolveKnoxMunicipality(-83.65, 36.1, context.boundaries)).toBe("unincorporated");

    const city = joinKnoxDesignation(-83.92, 35.96, context);
    expect(city.municipality).toBe("knoxville");
    expect(city.zoningCode).toBe("RN-5");
    expect(city.flu).toBeNull();
    expect(city.dataGaps).toContain(KNOX_CITY_FLU_GAP);

    const town = joinKnoxDesignation(-84.2, 35.88, context);
    expect(town.zoningCode).toBe("R-2");
    expect(town.zoneType).toBe("Town of Farragut");
    expect(town.flu).toBeNull();
    expect(town.dataGaps).toContain(FARRAGUT_FLU_GAP);

    const county = joinKnoxDesignation(-83.65, 36.1, context);
    expect(county.zoningCode).toBe("CA H");
    expect(county.flu).toMatchObject({ code: "SR", jurisdiction: "KNOX-COUNTY", source: "advance-knox" });
    expect(county.dataGaps.join(" ")).not.toContain("Advance Knox");

    const mapped = mapKnoxParcel({ PARCELID: "1", CALCULATED_AREA: 8, OWNER: "County Owner" }, [-83.65, 36.1], county);
    expect(mapped?.municipality).toBe("Unincorporated Knox County");
    expect(mapped?.zoningCode).toBe("CA H");
    expect(mapped?.flu?.code).toBe("SR");
    expect(mapped?.jurisdictionPrefix).toBe("KNOX-COUNTY");
  });

  it("does not apply county place types inside the city", () => {
    const cityFluLeak = feature<KnoxFluProperties>(
      { placeType: "CMU", gppCompatibility: null, source: "advance-knox" },
      knoxville,
    );
    const leaked = joinKnoxDesignation(-83.92, 35.96, {
      ...context,
      countyFlu: indexKnoxOverlays([cityFluLeak, place]),
    });
    expect(leaked.flu).toBeNull();
    expect(knoxOverlaysAtPoint(indexKnoxOverlays([cityZone]), -83.92, 35.96)).toHaveLength(1);
    expect(pointInKnoxGeometry(-83.92, 35.96, knoxville)).toBe(true);
    expect(geometryBbox(knoxville)[0]).toBe(-84);
  });
});

describe("Knox overlay fixtures", () => {
  const summaryPath = path.join(process.cwd(), "data/fixtures/knox/summary.json");

  it("documents the parcel blocker and the public overlays", () => {
    expect(existsSync(summaryPath)).toBe(true);
    const summary = JSON.parse(readFileSync(summaryPath, "utf8")) as {
      impact: boolean;
      parcel: { blocked: boolean; globalSearchStatus: number; propertyStatus: number; queryUrl: string };
      zoning: { count: number; city: number; county: number; zoneTypes: string[]; farragutExcluded: boolean };
      countyFlu: { count: number; placeTypes: string[] };
      farragutZoning: { count: number; acres5to150: number };
      cityFlu: { gap: boolean };
      samples: Record<string, { municipality: string; zoningCode: string | null; placeType: string | null }>;
    };
    expect(summary.impact).toBe(false);
    expect(summary.parcel.blocked).toBe(true);
    expect(summary.parcel.globalSearchStatus).toBe(401);
    expect(summary.parcel.propertyStatus).toBe(401);
    expect(summary.parcel.queryUrl).not.toContain("cot.tn.gov");
    expect(summary.zoning.count).toBeGreaterThan(10000);
    expect(summary.zoning.city).toBeGreaterThan(9000);
    expect(summary.zoning.county).toBeGreaterThan(3000);
    expect(summary.zoning.zoneTypes).toEqual(["City of Knoxville", "Knox County"]);
    expect(summary.zoning.farragutExcluded).toBe(true);
    expect(summary.countyFlu.count).toBeGreaterThan(1000);
    expect(summary.countyFlu.placeTypes).toEqual(
      expect.arrayContaining(["BP", "CC", "CI", "CMU", "MHI", "POS", "RA", "RC", "RCC", "RL", "ROW", "SMR", "SR", "TCMU", "TN"]),
    );
    expect(summary.farragutZoning.count).toBeGreaterThan(100);
    expect(summary.farragutZoning.acres5to150).toBeGreaterThan(100);
    expect(summary.cityFlu.gap).toBe(true);
    expect(summary.samples.downtown.municipality).toBe("knoxville");
    expect(summary.samples.farragut.municipality).toBe("farragut");
    expect(summary.samples.unincorporated.municipality).toBe("unincorporated");
    expect(summary.samples.unincorporated.placeType).toBeTruthy();
    expect(KNOX_PARCEL_BLOCKER).toContain("ingestion blocker");

    const county = JSON.parse(
      readFileSync(path.join(process.cwd(), "data/fixtures/market-parcels/counties/47093/county.json"), "utf8"),
    ) as { coverage: string; featureCount: number; source: string; queryUrl: string; gaps: string[] };
    expect(county.coverage).toBe("gap");
    expect(county.featureCount).toBe(0);
    expect(county.source).toBe("kgis-globalsearch-blocked");
    expect(county.queryUrl).toContain("GlobalSearch/MapServer/0/query");
    expect(county.queryUrl).not.toContain("IMPACT");
    expect(county.gaps.join(" ")).toContain("ingestion blocker");
    expect(existsSync(path.join(process.cwd(), "data/fixtures/market-parcels/counties/47093/tiles"))).toBe(false);
    expect(existsSync(path.join(process.cwd(), "data/fixtures/knox/zoning.geojson"))).toBe(true);
    expect(existsSync(path.join(process.cwd(), "data/fixtures/knox/county-flu.geojson"))).toBe(true);
    expect(existsSync(path.join(process.cwd(), "data/fixtures/knox/farragut-zoning.geojson"))).toBe(true);
    expect(existsSync(path.join(process.cwd(), "docs/knox-parcels.md"))).toBe(true);
  });
});
