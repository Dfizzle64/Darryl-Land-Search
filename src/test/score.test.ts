import { describe, expect, it } from "vitest";
import { filterParcels } from "../lib/filters";
import { effectiveScoreWeights, rankSites, risingScore, scoreParcel } from "../lib/score";
import type { FilterState, FluConfig, ParcelFeature, ZoningConfig } from "../lib/types";

const zoningConfig: ZoningConfig = {
  version: 2,
  county: "test",
  updatedAt: "2026-09-21",
  notes: "",
  jurisdictions: [
    {
      code: "ORG",
      name: "Orange County",
      coverage: "verified",
      districts: [{ token: "R-3", label: "MF", status: "permitted", why: "test" }],
    },
  ],
  multifamilyTokens: [],
  plannedDevelopmentTokens: [],
  notAllowedExamples: [],
};

const fluConfig: FluConfig = {
  version: 1,
  updatedAt: "2026-09-21",
  notes: "",
  sources: [],
  categories: [
    {
      code: "MD",
      jurisdiction: "ORG",
      label: "Medium Density Residential",
      allowsMultifamily: true,
      status: "yes",
      why: "MDR",
    },
  ],
};

const filters: FilterState = {
  landUseFilter: "off",
  includePlannedDevelopment: true,
  includeConditionalZoning: false,
  ozFilter: "either",
  minAcreage: 1,
  includeUnknownAcreage: true,
  minIncome: 50000,
  incomeGeography: "tract",
  includeUnknownIncome: true,
  minAadt: 10000,
  includeUnknownAadt: true,
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
      jurisdictionCode: "ORG",
      ownerName: "TEST LLC",
      ownerName2: null,
      propertyName: null,
      zoningCode: "ORG-R-3",
      zoningDistrict: "R-3",
      jurisdictionPrefix: "ORG",
      dorCode: "0300",
      acreage: 2,
      centroid: [-81.395, 28.505],
      lastSale: { date: "2020-01-01", price: 100, qualified: "Q" },
      tax: { marketValue: 1, assessedValue: 1, taxableValue: 1, taxes: 1 },
      mailingAddress: { line1: "PO BOX 1", line2: null, city: "ORLANDO", state: "FL", zip: "32801" },
      incomeTract: { geoid: "t", name: "tract", medianHouseholdIncome: 60000, medianHouseholdIncomeMoe: 1000 },
      incomeBlockGroup: null,
      nearestRoad: { aadt: 12000, year: 2025, roadwayId: "1", from: "A", to: "B", distanceMeters: 100 },
      flu: { code: "MD", label: "MDR", jurisdiction: "ORG", source: "test" },
      opportunityZone: { inOpportunityZone: false, tractGeoid: null, tractName: null, source: "test" },
      source: "test",
      ...partial,
    },
  };
}

describe("risingScore", () => {
  it("ramps from the minimum toward the comfort margin and treats null as a mid unknown", () => {
    expect(risingScore(1, 1, 8)).toBe(0);
    expect(risingScore(9, 1, 8)).toBe(1);
    expect(risingScore(5, 1, 8)).toBeCloseTo(0.5, 5);
    expect(risingScore(null, 1, 8)).toBe(0.35);
  });
});

describe("rankSites", () => {
  it("ranks larger, higher-income, busier, OZ parcels above weaker matches", () => {
    const parcels = [
      feature({
        id: "weak",
        parcelId: "weak",
        acreage: 1.1,
        incomeTract: { geoid: "t", name: "t", medianHouseholdIncome: 51000, medianHouseholdIncomeMoe: 1 },
        nearestRoad: { aadt: 11000, year: 2025, roadwayId: "1", from: "A", to: "B", distanceMeters: 100 },
      }),
      feature({
        id: "strong",
        parcelId: "strong",
        acreage: 12,
        incomeTract: { geoid: "t", name: "t", medianHouseholdIncome: 120000, medianHouseholdIncomeMoe: 1 },
        nearestRoad: { aadt: 45000, year: 2025, roadwayId: "1", from: "A", to: "B", distanceMeters: 100 },
        opportunityZone: {
          inOpportunityZone: true,
          tractGeoid: "12095017600",
          tractName: "Census tract 176",
          source: "test",
        },
      }),
    ];
    const ranked = rankSites(parcels, filters, zoningConfig, fluConfig);
    expect(ranked.map((item) => item.feature.properties.id)).toEqual(["strong", "weak"]);
    expect(ranked[0].score).toBeGreaterThan(ranked[1].score);
    expect(ranked[0].rank).toBe(1);
    expect(ranked[0].chips.some((chip) => chip.key === "opportunityZone" && chip.points > 0)).toBe(true);
  });

  it("gives an Opportunity Zone bonus when the filter is Either, and drops that weight when filtering Not in OZ", () => {
    const base = feature({ id: "a", parcelId: "a", acreage: 4 });
    const ozTwin = feature({
      id: "b",
      parcelId: "b",
      acreage: 4,
      opportunityZone: {
        inOpportunityZone: true,
        tractGeoid: "12095017600",
        tractName: "Census tract 176",
        source: "test",
      },
    });
    const either = rankSites([base, ozTwin], { ...filters, minAcreage: 0, minIncome: 0, minAadt: 0 }, zoningConfig, fluConfig);
    expect(either[0].feature.properties.id).toBe("b");
    expect(either[0].score).toBeGreaterThan(either[1].score);

    const outWeights = effectiveScoreWeights({ ...filters, ozFilter: "out" });
    expect(outWeights.opportunityZone).toBe(0);
    const eitherWeights = effectiveScoreWeights({ ...filters, ozFilter: "either" });
    expect(eitherWeights.opportunityZone).toBeCloseTo(0.1, 5);
  });

  it("scores rezoning candidates above already-zoned sites in all-parcels mode, and keeps list in sync with filters", () => {
    const candidate = feature({
      id: "rezoning",
      parcelId: "rezoning",
      zoningCode: "ORG-R-1",
      zoningDistrict: "R-1",
      acreage: 5,
    });
    const already = feature({ id: "mf", parcelId: "mf", acreage: 5 });
    const allMode = rankSites([candidate, already], { ...filters, landUseFilter: "off", minAcreage: 0, minIncome: 0, minAadt: 0 }, zoningConfig, fluConfig);
    expect(allMode.find((item) => item.feature.properties.id === "rezoning")?.rezoningCandidate).toBe(true);
    const rezoningOnly = filterParcels(
      [candidate, already],
      { ...filters, landUseFilter: "rezoning", minAcreage: 0, minIncome: 0, minAadt: 0 },
      zoningConfig,
      fluConfig,
    );
    expect(rezoningOnly.map((item) => item.properties.id)).toEqual(["rezoning"]);
    const scored = scoreParcel(candidate, { ...filters, landUseFilter: "rezoning" }, zoningConfig, fluConfig);
    expect(scored.rezoningCandidate).toBe(true);
    expect(scored.breakdown.landUse).toBe(1);
  });
});
