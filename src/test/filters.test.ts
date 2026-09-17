import { describe, expect, it } from "vitest";
import { filterParcels } from "../lib/filters";
import type { FilterState, ParcelFeature, ZoningConfig } from "../lib/types";
import { parseZoningCode, zoningAllowsMultifamily } from "../lib/zoning";

const config: ZoningConfig = {
  version: 1,
  county: "test",
  notes: "",
  multifamilyTokens: [
    { token: "R-3", label: "MF", why: "test" },
    { token: "R-3B", label: "Orlando R-3B", why: "test" },
    { token: "AC-3", label: "Activity center", why: "test" },
  ],
  plannedDevelopmentTokens: [{ token: "P-D", label: "PD", why: "verify" }],
  notAllowedExamples: [],
};

function feature(partial: Partial<ParcelFeature["properties"]>): ParcelFeature {
  return {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [-81.4, 28.5],
          [-81.39, 28.5],
          [-81.39, 28.51],
          [-81.4, 28.51],
          [-81.4, 28.5],
        ],
      ],
    },
    properties: {
      id: "1",
      parcelId: "1",
      situsAddress: "100 TEST ST",
      situsCity: "ORLANDO",
      situsZip: "32801",
      jurisdictionCode: "ORL",
      ownerName: "TEST LLC",
      ownerName2: null,
      propertyName: null,
      zoningCode: "ORL-R-3B/T/AN",
      zoningDistrict: "R-3B",
      jurisdictionPrefix: "ORL",
      dorCode: "0300",
      acreage: 1,
      centroid: [-81.395, 28.505],
      lastSale: { date: "2020-01-01", price: 100, qualified: "Q" },
      tax: { marketValue: 1, assessedValue: 1, taxableValue: 1, taxes: 1 },
      mailingAddress: { line1: "PO BOX 1", line2: null, city: "ORLANDO", state: "FL", zip: "32801" },
      incomeTract: { geoid: "t", name: "tract", medianHouseholdIncome: 80000, medianHouseholdIncomeMoe: 1000 },
      incomeBlockGroup: { geoid: "b", name: "bg", medianHouseholdIncome: 50000, medianHouseholdIncomeMoe: 1000 },
      nearestRoad: {
        aadt: 20000,
        year: 2025,
        roadwayId: "1",
        from: "A",
        to: "B",
        distanceMeters: 100,
      },
      source: "test",
      ...partial,
    },
  };
}

const baseFilters: FilterState = {
  multifamilyZoningOnly: true,
  includePlannedDevelopment: true,
  minIncome: 0,
  incomeGeography: "tract",
  includeUnknownIncome: true,
  minAadt: 0,
  includeUnknownAadt: true,
};

describe("parseZoningCode", () => {
  it("strips Orlando overlays", () => {
    expect(parseZoningCode("ORL-R-3B/T/AN")).toEqual({
      jurisdictionPrefix: "ORL",
      zoningDistrict: "R-3B",
    });
  });

  it("keeps Orange County U-R-3", () => {
    expect(parseZoningCode("ORG-U-R-3")).toEqual({
      jurisdictionPrefix: "ORG",
      zoningDistrict: "U-R-3",
    });
  });
});

describe("zoningAllowsMultifamily", () => {
  it("allows R-3 family districts including R-3A via R-3 token", () => {
    expect(zoningAllowsMultifamily("ORG-R-3", "R-3", config, false)).toBe(true);
    expect(zoningAllowsMultifamily("ORL-R-3A", "R-3A", config, false)).toBe(true);
    expect(zoningAllowsMultifamily("ORL-R-1", "R-1", config, false)).toBe(false);
  });

  it("does not treat public-use P as planned development", () => {
    expect(zoningAllowsMultifamily("ORL-P/T/AN", "P", config, true)).toBe(false);
  });

  it("gates planned development on the include flag", () => {
    expect(zoningAllowsMultifamily("ORG-P-D", "P-D", config, true)).toBe(true);
    expect(zoningAllowsMultifamily("ORG-P-D", "P-D", config, false)).toBe(false);
  });
});

describe("filterParcels", () => {
  it("filters by income geography independently", () => {
    const parcels = [feature({})];
    const tractPass = filterParcels(parcels, { ...baseFilters, minIncome: 70000, incomeGeography: "tract" }, config);
    const bgFail = filterParcels(parcels, { ...baseFilters, minIncome: 70000, incomeGeography: "blockGroup" }, config);
    expect(tractPass).toHaveLength(1);
    expect(bgFail).toHaveLength(0);
  });

  it("filters by AADT and zoning together", () => {
    const parcels = [
      feature({}),
      feature({
        id: "2",
        parcelId: "2",
        zoningCode: "ORG-R-1",
        zoningDistrict: "R-1",
        nearestRoad: { aadt: 40000, year: 2025, roadwayId: "2", from: "A", to: "B", distanceMeters: 50 },
      }),
      feature({
        id: "3",
        parcelId: "3",
        nearestRoad: { aadt: 5000, year: 2025, roadwayId: "3", from: "A", to: "B", distanceMeters: 50 },
      }),
    ];
    const result = filterParcels(parcels, { ...baseFilters, minAadt: 15000 }, config);
    expect(result.map((item) => item.properties.id)).toEqual(["1"]);
  });

  it("can include unknown income when the toggle is on", () => {
    const parcels = [feature({ incomeTract: { geoid: "x", name: "x", medianHouseholdIncome: null, medianHouseholdIncomeMoe: null } })];
    expect(filterParcels(parcels, { ...baseFilters, minIncome: 60000, includeUnknownIncome: true }, config)).toHaveLength(1);
    expect(filterParcels(parcels, { ...baseFilters, minIncome: 60000, includeUnknownIncome: false }, config)).toHaveLength(0);
  });
});
