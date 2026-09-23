import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  applyMunicipalOverlay,
  bboxInFlorida,
  cityIndexFromFixture,
  findMunicipalHit,
  FLORIDA_BBOX,
  municipalZoningCode,
  overlayCityUsable,
  parcelIdAliases,
  REJECTED_EDGEWOOD_TEXAS_URL,
  type MunicipalCityIndex,
  type MunicipalOverlayIndex,
} from "../lib/municipalOverlays";
import type { ParcelFeature } from "../lib/types";

const maitlandSquare = [
  [
    [
      [-81.37, 28.62],
      [-81.35, 28.62],
      [-81.35, 28.64],
      [-81.37, 28.64],
      [-81.37, 28.62],
    ],
  ],
];

function parcel(overrides: Partial<ParcelFeature["properties"]> = {}): ParcelFeature {
  return {
    type: "Feature",
    id: "12095:292135000000144",
    geometry: {
      type: "Polygon",
      coordinates: maitlandSquare[0],
    },
    properties: {
      id: "12095:292135000000144",
      parcelId: "292135000000144",
      countyFips: "12095",
      countyName: "Orange",
      state: "Florida",
      situsAddress: "1 TEST",
      situsCity: "MAITLAND",
      situsZip: "32751",
      jurisdictionCode: "ORG",
      ownerName: "OWNER",
      ownerName2: null,
      propertyName: null,
      zoningCode: "ORG-R-1AA",
      zoningDistrict: "R-1AA",
      jurisdictionPrefix: "ORG",
      dorCode: "0000",
      acreage: 12.5,
      centroid: [-81.36, 28.63],
      lastSale: { date: null, price: null, qualified: null },
      tax: { marketValue: null, assessedValue: null, taxableValue: null, taxes: null },
      mailingAddress: { line1: null, line2: null, city: null, state: null, zip: null },
      incomeTract: null,
      incomeBlockGroup: null,
      nearestRoad: null,
      flu: { code: "City", label: "City", jurisdiction: "ORG", source: "county" },
      opportunityZone: null,
      oz2Eligibility: null,
      source: "test",
      ...overrides,
    },
  };
}

function city(partial: Partial<MunicipalCityIndex> & Pick<MunicipalCityIndex, "id" | "name" | "prefix">): MunicipalCityIndex {
  return {
    status: "active",
    bbox: [-81.4, 28.6, -81.3, 28.7],
    attributes: new Map(),
    spatial: [],
    ...partial,
  };
}

describe("municipal overlay joins", () => {
  it("normalizes Orange parcel ids with and without the 12095 prefix", () => {
    expect(parcelIdAliases("292135000000144")).toEqual(["292135000000144", "12095-292135000000144"]);
    expect(parcelIdAliases("12095-292135000000144")).toEqual(["292135000000144", "12095-292135000000144"]);
    expect(parcelIdAliases("12095:292135000000144")).toEqual(["292135000000144", "12095-292135000000144"]);
  });

  it("prefers an attribute join and labels City of Maitland", () => {
    const index: MunicipalOverlayIndex = {
      cities: [
        city({
          id: "maitland",
          name: "City of Maitland",
          prefix: "MTL",
          attributes: new Map([
            ["292135000000144", { zoningCode: "RSF-2", zoningLabel: null, fluCode: "Traditional Neighborhood", fluLabel: "Established neighborhoods" }],
          ]),
        }),
      ],
    };
    const result = applyMunicipalOverlay(parcel({ parcelId: "12095-292135000000144" }), index);
    expect(result.properties.zoningCode).toBe("MTL-RSF-2");
    expect(result.properties.zoningDistrict).toBe("RSF-2");
    expect(result.properties.zoningAuthority).toBe("City of Maitland");
    expect(result.properties.jurisdictionPrefix).toBe("MTL");
    expect(result.properties.countyZoningCode).toBe("ORG-R-1AA");
    expect(result.properties.flu?.code).toBe("Traditional Neighborhood");
    expect(result.properties.flu?.jurisdictionName).toBe("City of Maitland");
    expect(result.properties.flu?.jurisdiction).toBe("MTL");
    expect(result.properties.municipalOverlay?.join).toBe("attribute");
    expect(result.properties.acreage).toBe(12.5);
    expect(result.properties.ownerName).toBe("OWNER");
  });

  it("uses a spatial join when the parcel id does not match", () => {
    const index: MunicipalOverlayIndex = {
      cities: [
        city({
          id: "winter-park",
          name: "City of Winter Park",
          prefix: "WP",
          spatial: [
            {
              zoningCode: "R-3",
              zoningLabel: null,
              fluCode: "Medium Density Residential",
              fluLabel: null,
              bbox: [-81.37, 28.62, -81.35, 28.64],
              polygons: maitlandSquare,
              parcelId: null,
              area: 0.0004,
            },
          ],
        }),
      ],
    };
    const result = applyMunicipalOverlay(parcel({ parcelId: "999" }), index);
    expect(result.properties.zoningCode).toBe("WP-R-3");
    expect(result.properties.zoningAuthority).toBe("City of Winter Park");
    expect(result.properties.municipalOverlay?.join).toBe("spatial");
    expect(result.properties.flu?.code).toBe("Medium Density Residential");
  });

  it("does not keep county zoning when the city record has no district code", () => {
    const index: MunicipalOverlayIndex = {
      cities: [
        city({
          id: "ocoee",
          name: "City of Ocoee",
          prefix: "OCO",
          attributes: new Map([["292135000000144", { zoningCode: null, zoningLabel: null, fluCode: null, fluLabel: null }]]),
        }),
      ],
    };
    const result = applyMunicipalOverlay(parcel(), index);
    expect(result.properties.zoningCode).toBeNull();
    expect(result.properties.zoningAuthority).toBe("City of Ocoee");
    expect(result.properties.countyZoningCode).toBe("ORG-R-1AA");
    expect(result.properties.flu?.code).toBeNull();
    expect(result.properties.flu?.jurisdictionName).toBe("City of Ocoee");
  });

  it("does not apply a gap city or a Texas extent", () => {
    const texas = city({
      id: "edgewood-tx",
      name: "Edgewood, Texas",
      prefix: "EDG",
      bbox: [-95.9, 32.6, -95.8, 32.7],
      attributes: new Map([["292135000000144", { zoningCode: "R-1", zoningLabel: null, fluCode: null, fluLabel: null }]]),
    });
    const gap = city({
      id: "edgewood",
      name: "City of Edgewood",
      prefix: "EDG",
      status: "gap",
      attributes: new Map([["292135000000144", { zoningCode: "R-1AA", zoningLabel: null, fluCode: null, fluLabel: null }]]),
    });
    expect(overlayCityUsable(texas)).toBe(false);
    expect(bboxInFlorida(texas.bbox)).toBe(false);
    expect(bboxInFlorida(FLORIDA_BBOX)).toBe(true);
    const result = applyMunicipalOverlay(parcel(), { cities: [texas, gap] });
    expect(result.properties.zoningCode).toBe("ORG-R-1AA");
    expect(result.properties.municipalOverlay).toBeUndefined();
    expect(findMunicipalHit(parcel(), { cities: [texas, gap] })).toBeNull();
  });

  it("leaves parcels outside Orange County alone", () => {
    const index: MunicipalOverlayIndex = {
      cities: [
        city({
          id: "maitland",
          name: "City of Maitland",
          prefix: "MTL",
          attributes: new Map([["292135000000144", { zoningCode: "DM", zoningLabel: null, fluCode: null, fluLabel: null }]]),
        }),
      ],
    };
    const result = applyMunicipalOverlay(parcel({ countyFips: "12069", countyName: "Lake" }), index);
    expect(result.properties.zoningCode).toBe("ORG-R-1AA");
  });

  it("refuses the CITY stub and keeps an existing jurisdiction prefix", () => {
    expect(municipalZoningCode("MTL", "CITY")).toBeNull();
    expect(municipalZoningCode("OCO", "OUT")).toBeNull();
    expect(municipalZoningCode("ORL", "ORL-R-3B/T")).toBe("ORL-R-3B/T");
    expect(municipalZoningCode("OCO", "r-3")).toBe("OCO-R-3");
  });

  it("does not label an Ocoee OUT row as city zoning", () => {
    const index: MunicipalOverlayIndex = {
      cities: [
        city({
          id: "ocoee",
          name: "City of Ocoee",
          prefix: "OCO",
          attributes: new Map([["292135000000144", { zoningCode: "OUT", zoningLabel: null, fluCode: "LDR", fluLabel: null }]]),
        }),
      ],
    };
    const result = applyMunicipalOverlay(parcel(), index);
    expect(result.properties.zoningCode).toBe("ORG-R-1AA");
    expect(result.properties.municipalOverlay).toBeUndefined();
  });

  it("builds an index only from Florida polygons", () => {
    const index = cityIndexFromFixture({
      id: "orlando",
      name: "City of Orlando",
      prefix: "ORL",
      bbox: [-81.5, 28.4, -81.2, 28.6],
      attributes: {},
      spatial: [
        { z: "R-3A", b: [-95.9, 32.6, -95.8, 32.7], g: maitlandSquare },
        { z: "R-3B", b: [-81.37, 28.62, -81.35, 28.64], g: maitlandSquare },
      ],
    });
    expect(index.spatial).toHaveLength(1);
    expect(index.spatial[0]?.zoningCode).toBe("R-3B");
  });
});

describe("municipal overlay registry", () => {
  const registry = JSON.parse(readFileSync(path.join(process.cwd(), "data/municipal-overlays.json"), "utf8")) as {
    cities: Array<{ id: string; status: string; name: string; layers?: Array<{ url: string }> }>;
    rejected: Array<{ id: string; url: string }>;
  };

  it("keeps Edgewood, Florida as a gap and rejects the Texas service", () => {
    const edgewood = registry.cities.find((city) => city.id === "edgewood");
    expect(edgewood?.status).toBe("gap");
    expect(edgewood?.layers).toBeUndefined();
    expect(registry.rejected.map((item) => item.url)).toContain(REJECTED_EDGEWOOD_TEXAS_URL);
    const activeUrls = registry.cities
      .filter((city) => city.status === "active")
      .flatMap((city) => city.layers ?? [])
      .map((layer) => layer.url);
    expect(activeUrls.some((url) => url.toLowerCase().includes("etcog.org"))).toBe(false);
    for (const id of ["windermere", "belle-isle", "oakland", "bay-lake", "lake-buena-vista"]) {
      expect(registry.cities.find((city) => city.id === id)?.status).toBe("gap");
    }
  });

  it("joins a real Maitland parcel id to city zoning and FLU", () => {
    const raw = JSON.parse(
      readFileSync(path.join(process.cwd(), "data/fixtures/municipal-overlays/maitland.json"), "utf8"),
    ) as { attributes: Record<string, { z?: string; f?: string }> };
    const parcelId = Object.keys(raw.attributes).find(
      (key) => !key.startsWith("12095-") && raw.attributes[key]?.z && raw.attributes[key]?.f,
    );
    expect(parcelId).toBeTruthy();
    const index: MunicipalOverlayIndex = { cities: [cityIndexFromFixture(raw)] };
    const result = applyMunicipalOverlay(parcel({ parcelId: parcelId! }), index);
    expect(result.properties.zoningAuthority).toBe("City of Maitland");
    expect(result.properties.zoningCode?.startsWith("MTL-")).toBe(true);
    expect(result.properties.zoningCode).not.toBe("ORG-R-1AA");
    expect(result.properties.flu?.jurisdictionName).toBe("City of Maitland");
    expect(result.properties.flu?.code).toBe(raw.attributes[parcelId!]?.f);
    expect(result.properties.acreage).toBe(12.5);
  });

  it("verifies every wired city fixture sits in Florida", () => {
    const active = registry.cities.filter((city) => city.status === "active");
    expect(active.map((city) => city.id).sort()).toEqual(
      ["apopka", "eatonville", "maitland", "ocoee", "orlando", "winter-garden", "winter-park"].sort(),
    );
    for (const city of active) {
      const fixture = JSON.parse(
        readFileSync(path.join(process.cwd(), `data/fixtures/municipal-overlays/${city.id}.json`), "utf8"),
      ) as { bbox: [number, number, number, number]; attributes: Record<string, unknown>; spatial: unknown[] };
      expect(bboxInFlorida(fixture.bbox), city.id).toBe(true);
      expect(fixture.bbox[0]).toBeGreaterThan(-83);
      expect(fixture.bbox[2]).toBeLessThan(-80);
      expect(fixture.bbox[1]).toBeGreaterThan(27.5);
      expect(fixture.bbox[3]).toBeLessThan(29.2);
      const blob = JSON.stringify(fixture.attributes).slice(0, 500) + JSON.stringify(fixture.spatial).slice(0, 200);
      expect(blob.toLowerCase()).not.toContain("owner");
      expect(JSON.stringify(fixture).toLowerCase()).not.toContain("etcog");
    }
  });
});
