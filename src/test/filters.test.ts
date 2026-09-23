import { describe, expect, it } from "vitest";
import { describeRezoningCandidate, filterParcels, isRezoningCandidate } from "../lib/filters";
import { fluAllowsMultifamily } from "../lib/flu";
import type { FilterState, FluConfig, ParcelFeature, ZoningConfig } from "../lib/types";
import { parseZoningCode, zoningAllowsMultifamily } from "../lib/zoning";

const config: ZoningConfig = {
  version: 2,
  county: "test",
  updatedAt: "2026-09-17",
  notes: "",
  jurisdictions: [
    {
      code: "ORG",
      name: "Orange County",
      coverage: "verified",
      districts: [
        { token: "R-3", label: "MF", status: "permitted", why: "test" },
        { token: "R-2", label: "R-2 MF table", status: "permitted", why: "sec 38-77" },
        { token: "C-2", label: "Live Local commercial", status: "conditional", why: "condition 24" },
      ],
    },
    {
      code: "ORL",
      name: "Orlando",
      coverage: "verified",
      districts: [{ token: "R-3B", label: "Orlando R-3B", status: "permitted", why: "test" }],
    },
    {
      code: "OCO",
      name: "Ocoee",
      coverage: "verified",
      districts: [{ token: "R-3", label: "Ocoee R-3", status: "permitted", why: "table 5-1" }],
    },
  ],
  multifamilyTokens: [],
  plannedDevelopmentTokens: [{ token: "P-D", label: "PD", status: "maybe", why: "verify" }],
  notAllowedExamples: [],
};

const fluConfig: FluConfig = {
  version: 1,
  updatedAt: "2026-09-17",
  notes: "",
  sources: [],
  categories: [
    {
      code: "MD",
      jurisdiction: "ORG",
      label: "Medium Density Residential",
      allowsMultifamily: true,
      status: "yes",
      maxDensityDuAc: 20,
      why: "MDR",
    },
    {
      code: "LD",
      jurisdiction: "ORG",
      label: "Low Density Residential",
      allowsMultifamily: false,
      status: "no",
      maxDensityDuAc: 4,
      why: "LDR",
    },
    {
      code: "RES-MED",
      jurisdiction: "ORL",
      label: "Residential Medium",
      allowsMultifamily: true,
      status: "yes",
      maxDensityDuAc: 30,
      why: "Orlando",
    },
  ],
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
      flu: { code: "RES-MED", label: "Residential Medium", jurisdiction: "ORL", source: "test" },
      opportunityZone: { inOpportunityZone: false, tractGeoid: null, tractName: null, source: "test" },
      oz2Eligibility: null,
      source: "test",
      ...partial,
    },
  };
}

const baseFilters: FilterState = {
  considerOpportunityZone: true,
  considerZoning: true,
  landUseFilter: "zoning",
  includePlannedDevelopment: true,
  includeConditionalZoning: false,
  ozFilter: "either",
  minAcreage: 0,
  includeUnknownAcreage: true,
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
  it("allows R-3 in Orange County and Ocoee but not as a generic Orlando code", () => {
    expect(zoningAllowsMultifamily("ORG-R-3", "R-3", config, false)).toBe(true);
    expect(zoningAllowsMultifamily("OCO-R-3", "R-3", config, false)).toBe(true);
    expect(zoningAllowsMultifamily("ORL-R-3A", "R-3A", config, false)).toBe(false);
    expect(zoningAllowsMultifamily("ORL-R-3B", "R-3B", config, false)).toBe(true);
  });

  it("does not treat public-use P as planned development", () => {
    expect(zoningAllowsMultifamily("ORL-P/T/AN", "P", config, true)).toBe(false);
  });

  it("gates planned development on the include flag", () => {
    expect(zoningAllowsMultifamily("ORG-P-D", "P-D", config, true)).toBe(true);
    expect(zoningAllowsMultifamily("ORG-P-D", "P-D", config, false)).toBe(false);
  });

  it("gates commercial Live Local districts on the conditional flag", () => {
    expect(zoningAllowsMultifamily("ORG-C-2", "C-2", config, false, false)).toBe(false);
    expect(zoningAllowsMultifamily("ORG-C-2", "C-2", config, false, true)).toBe(true);
  });
});

describe("fluAllowsMultifamily", () => {
  it("treats MDR as supportive and LDR as not", () => {
    expect(fluAllowsMultifamily({ code: "MD", label: "MDR", jurisdiction: "ORG", source: "t" }, fluConfig)).toBe(true);
    expect(fluAllowsMultifamily({ code: "LD", label: "LDR", jurisdiction: "ORG", source: "t" }, fluConfig)).toBe(false);
  });

  it("matches overlay suffixes to the base FLU code", () => {
    expect(
      fluAllowsMultifamily({ code: "RES-MED/RES-PRO", label: "x", jurisdiction: "ORL", source: "t" }, fluConfig),
    ).toBe(true);
  });

  it("returns null when FLU is missing rather than inventing a match", () => {
    expect(fluAllowsMultifamily(null, fluConfig)).toBeNull();
  });

  it("does not treat NashvilleNext community character as an Orange County FLU entitlement", () => {
    const policy = {
      code: "MD",
      label: "Urban Mixed Use Neighborhood",
      jurisdiction: "NashvilleNext",
      source: "nashville-next-ccm",
    };
    expect(fluAllowsMultifamily(policy, fluConfig)).toBeNull();
    const parcel = feature({
      countyFips: "47037",
      state: "Tennessee",
      zoningCode: "AR2A",
      zoningDistrict: "AR2A",
      flu: policy,
    });
    expect(isRezoningCandidate(parcel, baseFilters, config, fluConfig)).toBe(false);
    expect(describeRezoningCandidate(parcel, baseFilters, config, fluConfig).reason).toMatch(/not a Future Land Use entitlement/i);
  });
});

describe("filterParcels", () => {
  it("filters by income geography independently", () => {
    const parcels = [feature({})];
    const tractPass = filterParcels(parcels, { ...baseFilters, minIncome: 70000, incomeGeography: "tract" }, config, fluConfig);
    const bgFail = filterParcels(parcels, { ...baseFilters, minIncome: 70000, incomeGeography: "blockGroup" }, config, fluConfig);
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
        jurisdictionPrefix: "ORG",
        nearestRoad: { aadt: 40000, year: 2025, roadwayId: "2", from: "A", to: "B", distanceMeters: 50 },
      }),
      feature({
        id: "3",
        parcelId: "3",
        nearestRoad: { aadt: 5000, year: 2025, roadwayId: "3", from: "A", to: "B", distanceMeters: 50 },
      }),
    ];
    const result = filterParcels(parcels, { ...baseFilters, minAadt: 15000 }, config, fluConfig);
    expect(result.map((item) => item.properties.id)).toEqual(["1"]);
  });

  it("can include unknown income when the toggle is on", () => {
    const parcels = [feature({ incomeTract: { geoid: "x", name: "x", medianHouseholdIncome: null, medianHouseholdIncomeMoe: null } })];
    expect(filterParcels(parcels, { ...baseFilters, minIncome: 60000, includeUnknownIncome: true }, config, fluConfig)).toHaveLength(1);
    expect(filterParcels(parcels, { ...baseFilters, minIncome: 60000, includeUnknownIncome: false }, config, fluConfig)).toHaveLength(0);
  });

  it("filters by minimum acreage and unknown acreage", () => {
    const parcels = [
      feature({ id: "small", parcelId: "small", acreage: 0.4 }),
      feature({ id: "mid", parcelId: "mid", acreage: 2.5 }),
      feature({ id: "unk", parcelId: "unk", acreage: null }),
    ];
    expect(filterParcels(parcels, { ...baseFilters, minAcreage: 1 }, config, fluConfig).map((item) => item.properties.id)).toEqual([
      "mid",
      "unk",
    ]);
    expect(
      filterParcels(parcels, { ...baseFilters, minAcreage: 1, includeUnknownAcreage: false }, config, fluConfig).map(
        (item) => item.properties.id,
      ),
    ).toEqual(["mid"]);
  });

  it("finds parcels whose FLU allows multifamily even when current zoning does not", () => {
    const parcels = [
      feature({
        id: "rezoning-candidate",
        parcelId: "rezoning-candidate",
        zoningCode: "ORG-R-1A",
        zoningDistrict: "R-1A",
        jurisdictionPrefix: "ORG",
        flu: { code: "MD", label: "Medium Density Residential", jurisdiction: "ORG", source: "test" },
      }),
      feature({
        id: "already-zoned",
        parcelId: "already-zoned",
        flu: { code: "LD", label: "Low Density Residential", jurisdiction: "ORG", source: "test" },
      }),
    ];
    const fluOnly = filterParcels(parcels, { ...baseFilters, landUseFilter: "flu" }, config, fluConfig);
    expect(fluOnly.map((item) => item.properties.id)).toEqual(["rezoning-candidate"]);
    const zoningOnly = filterParcels(parcels, { ...baseFilters, landUseFilter: "zoning" }, config, fluConfig);
    expect(zoningOnly.map((item) => item.properties.id)).toEqual(["already-zoned"]);
    const either = filterParcels(parcels, { ...baseFilters, landUseFilter: "either" }, config, fluConfig);
    expect(either.map((item) => item.properties.id).sort()).toEqual(["already-zoned", "rezoning-candidate"]);
    const both = filterParcels(parcels, { ...baseFilters, landUseFilter: "both" }, config, fluConfig);
    expect(both).toHaveLength(0);
  });

  it("does not treat missing FLU as supportive in FLU-only mode", () => {
    const parcels = [
      feature({
        id: "gap",
        parcelId: "gap",
        zoningCode: "ORG-R-1",
        zoningDistrict: "R-1",
        jurisdictionPrefix: "ORG",
        flu: null,
      }),
    ];
    expect(filterParcels(parcels, { ...baseFilters, landUseFilter: "flu" }, config, fluConfig)).toHaveLength(0);
    expect(filterParcels(parcels, { ...baseFilters, landUseFilter: "off" }, config, fluConfig)).toHaveLength(1);
  });

  it("keeps only parcels that are not currently MF-capable in non-mf mode", () => {
    const parcels = [
      feature({ id: "mf", parcelId: "mf" }),
      feature({
        id: "sf",
        parcelId: "sf",
        zoningCode: "ORG-R-1A",
        zoningDistrict: "R-1A",
        jurisdictionPrefix: "ORG",
      }),
    ];
    expect(filterParcels(parcels, { ...baseFilters, landUseFilter: "non-mf" }, config, fluConfig).map((item) => item.properties.id)).toEqual([
      "sf",
    ]);
  });

  it("treats rezoning candidates as FLU-yes and zoning-not-MF, and skips missing FLU", () => {
    const parcels = [
      feature({
        id: "candidate",
        parcelId: "candidate",
        zoningCode: "ORG-R-1A",
        zoningDistrict: "R-1A",
        jurisdictionPrefix: "ORG",
        flu: { code: "MD", label: "Medium Density Residential", jurisdiction: "ORG", source: "test" },
      }),
      feature({
        id: "already-mf",
        parcelId: "already-mf",
      }),
      feature({
        id: "gap",
        parcelId: "gap",
        zoningCode: "ORG-R-1",
        zoningDistrict: "R-1",
        jurisdictionPrefix: "ORG",
        flu: null,
      }),
      feature({
        id: "flu-no",
        parcelId: "flu-no",
        zoningCode: "ORG-R-1",
        zoningDistrict: "R-1",
        jurisdictionPrefix: "ORG",
        flu: { code: "LD", label: "Low Density Residential", jurisdiction: "ORG", source: "test" },
      }),
    ];
    const rezoning = filterParcels(parcels, { ...baseFilters, landUseFilter: "rezoning" }, config, fluConfig);
    expect(rezoning.map((item) => item.properties.id)).toEqual(["candidate"]);
    expect(isRezoningCandidate(parcels[0], baseFilters, config, fluConfig)).toBe(true);
    expect(isRezoningCandidate(parcels[2], baseFilters, config, fluConfig)).toBe(false);
    expect(describeRezoningCandidate(parcels[2], baseFilters, config, fluConfig).reason).toMatch(/not joined/i);
  });

  it("filters Opportunity Zone in / out / either", () => {
    const parcels = [
      feature({
        id: "in-oz",
        parcelId: "in-oz",
        opportunityZone: {
          inOpportunityZone: true,
          tractGeoid: "12095017600",
          tractName: "Census tract 176",
          source: "test",
        },
      }),
      feature({ id: "out-oz", parcelId: "out-oz" }),
    ];
    expect(filterParcels(parcels, { ...baseFilters, ozFilter: "in" }, config, fluConfig).map((item) => item.properties.id)).toEqual([
      "in-oz",
    ]);
    expect(filterParcels(parcels, { ...baseFilters, ozFilter: "out" }, config, fluConfig).map((item) => item.properties.id)).toEqual([
      "out-oz",
    ]);
    expect(filterParcels(parcels, { ...baseFilters, ozFilter: "either" }, config, fluConfig)).toHaveLength(2);
  });

  it("filters OZ 2.0 rural-eligible and non-rural eligible without treating them as designated", () => {
    const parcels = [
      feature({
        id: "rural",
        parcelId: "rural",
        oz2Eligibility: {
          eligible: true,
          rural: true,
          tractGeoid: "12095016605",
          tractName: "Census Tract 166.05",
          designation: "eligible-for-nomination",
          source: "rev-proc-2026-14",
        },
      }),
      feature({
        id: "urban-eligible",
        parcelId: "urban-eligible",
        oz2Eligibility: {
          eligible: true,
          rural: false,
          tractGeoid: "12095010400",
          tractName: "Census Tract 104",
          designation: "eligible-for-nomination",
          source: "rev-proc-2026-14",
        },
      }),
      feature({ id: "outside", parcelId: "outside" }),
    ];
    expect(
      filterParcels(parcels, { ...baseFilters, ozFilter: "rural-eligible" }, config, fluConfig).map((item) => item.properties.id),
    ).toEqual(["rural"]);
    expect(
      filterParcels(parcels, { ...baseFilters, ozFilter: "non-rural-eligible" }, config, fluConfig).map(
        (item) => item.properties.id,
      ),
    ).toEqual(["urban-eligible"]);
    expect(filterParcels(parcels, { ...baseFilters, ozFilter: "in" }, config, fluConfig)).toHaveLength(0);
    expect(parcels[0].properties.oz2Eligibility?.designation).toBe("eligible-for-nomination");
  });

  it("ignores opportunity zone and zoning constraints until those switches are on", () => {
    const parcels = [
      feature({
        id: "oz-non-mf",
        zoningCode: "ORG-R-1",
        zoningDistrict: "R-1",
        opportunityZone: { inOpportunityZone: true, tractGeoid: "1", tractName: null, source: "t" },
      }),
      feature({ id: "plain" }),
    ];
    const gatedOff = {
      ...baseFilters,
      considerOpportunityZone: false,
      considerZoning: false,
      ozFilter: "in" as const,
      landUseFilter: "non-mf" as const,
    };
    expect(filterParcels(parcels, gatedOff, config, fluConfig)).toHaveLength(2);
    expect(
      filterParcels(parcels, { ...gatedOff, considerOpportunityZone: true }, config, fluConfig).map(
        (item) => item.properties.id,
      ),
    ).toEqual(["oz-non-mf"]);
    expect(
      filterParcels(parcels, { ...gatedOff, considerZoning: true }, config, fluConfig).map((item) => item.properties.id),
    ).toEqual(["oz-non-mf"]);
  });
});
