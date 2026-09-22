import { describe, expect, it } from "vitest";
import { parcelFiltersFromSearchParams, stampFilterMatch, writeParcelFilters } from "../lib/filters";
import { loadFluConfig, loadZoningConfig } from "../lib/data/loadFixtures";
import { queryOrlandoFixtureParcels } from "../lib/data/orlandoParcelStore";
import { selectParcelPage } from "../lib/orlandoParcels";
import { parcelMatchFilter } from "../lib/basemap";
import { DEFAULT_FILTERS, type ParcelFeature } from "../lib/types";

function parcel(id: string, acreage: number, lon: number, lat: number): ParcelFeature {
  return {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [lon, lat],
          [lon + 0.001, lat],
          [lon + 0.001, lat + 0.001],
          [lon, lat],
        ],
      ],
    },
    properties: {
      id,
      parcelId: id,
      situsAddress: null,
      situsCity: null,
      situsZip: null,
      jurisdictionCode: null,
      ownerName: null,
      ownerName2: null,
      propertyName: null,
      zoningCode: null,
      zoningDistrict: null,
      jurisdictionPrefix: null,
      dorCode: null,
      acreage,
      centroid: [lon, lat],
      lastSale: { date: null, price: null, qualified: null },
      tax: { marketValue: null, assessedValue: null, taxableValue: null, taxes: null },
      mailingAddress: { line1: null, line2: null, city: null, state: null, zip: null },
      incomeTract: null,
      incomeBlockGroup: null,
      nearestRoad: null,
      flu: null,
      opportunityZone: null,
      oz2Eligibility: null,
      source: "test",
      dataGaps: [],
    },
  };
}

describe("parcel query filters", () => {
  it("filters before thinning so a match is not dropped for a larger non-match", () => {
    const features = [
      parcel("large", 50, -81.5, 28.5),
      parcel("mid", 40, -81.501, 28.501),
      parcel("small", 8, -81.502, 28.502),
    ];
    const page = selectParcelPage(features, 1, (feature) => (feature.properties.acreage ?? 0) < 10);
    expect(page.totalInBbox).toBe(3);
    expect(page.totalMatching).toBe(1);
    expect(page.truncated).toBe(false);
    expect(page.thinned.map((feature) => feature.properties.id)).toEqual(["small"]);
    expect(page.rejected).toHaveLength(2);
  });

  it("round-trips acreage, income, and AADT slider params", () => {
    const filters = {
      ...DEFAULT_FILTERS,
      landUseFilter: "off" as const,
      minAcreage: 12.5,
      includeUnknownAcreage: false,
      minIncome: 80000,
      includeUnknownIncome: false,
      minAadt: 15000,
      includeUnknownAadt: false,
      incomeGeography: "blockGroup" as const,
    };
    const params = new URLSearchParams();
    writeParcelFilters(params, filters, true);
    expect(params.get("filter")).toBe("1");
    expect(params.get("includeExcluded")).toBe("1");
    expect(parcelFiltersFromSearchParams(params)).toEqual(filters);
  });

  it("stamps a property the map can filter without an id list", async () => {
    const [zoningConfig, fluConfig] = await Promise.all([loadZoningConfig(), loadFluConfig()]);
    const features = [parcel("a", 6, -81.4, 28.5), parcel("b", 22, -81.41, 28.51)];
    const stamped = stampFilterMatch(
      features,
      { ...DEFAULT_FILTERS, landUseFilter: "off", minAcreage: 20 },
      zoningConfig,
      fluConfig,
    );
    expect(stamped.find((feature) => feature.properties.id === "a")?.properties.filterMatch).toBe(0);
    expect(stamped.find((feature) => feature.properties.id === "b")?.properties.filterMatch).toBe(1);
    expect(JSON.stringify(parcelMatchFilter)).toBe(JSON.stringify(["==", ["get", "filterMatch"], 1]));
    expect(JSON.stringify(parcelMatchFilter)).not.toContain('"literal"');
  });

  it("hides non-matching acreage, income, and AADT on a dense Orange viewport", async () => {
    const bbox = [-81.4, 28.55, -81.38, 28.57] as [number, number, number, number];
    const [zoningConfig, fluConfig] = await Promise.all([loadZoningConfig(), loadFluConfig()]);
    const open = await queryOrlandoFixtureParcels({
      bbox,
      county: "Orange",
      state: "Florida",
      limit: 8000,
      filters: { ...DEFAULT_FILTERS, landUseFilter: "off" },
      zoningConfig,
      fluConfig,
    });
    expect(open.totalInBbox).toBeGreaterThan(5);
    expect(open.collection.features.length).toBe(open.totalMatching);
    expect(open.collection.features.some((feature) => (feature.properties.acreage ?? 0) < 20)).toBe(true);
    expect(open.collection.features.some((feature) => (feature.properties.incomeTract?.medianHouseholdIncome ?? 0) > 0)).toBe(
      true,
    );
    expect(open.collection.features.some((feature) => (feature.properties.nearestRoad?.aadt ?? 0) > 0)).toBe(true);

    const large = await queryOrlandoFixtureParcels({
      bbox,
      county: "Orange",
      state: "Florida",
      limit: 8000,
      filters: { ...DEFAULT_FILTERS, landUseFilter: "off", minAcreage: 20, includeUnknownAcreage: false },
      zoningConfig,
      fluConfig,
    });
    expect(large.totalMatching).toBeGreaterThan(0);
    expect(large.totalMatching).toBeLessThan(open.totalMatching);
    expect(large.collection.features.every((feature) => (feature.properties.acreage ?? 0) >= 20)).toBe(true);

    const rich = await queryOrlandoFixtureParcels({
      bbox,
      county: "Orange",
      state: "Florida",
      limit: 8000,
      filters: {
        ...DEFAULT_FILTERS,
        landUseFilter: "off",
        minIncome: 200000,
        includeUnknownIncome: false,
      },
      zoningConfig,
      fluConfig,
    });
    expect(rich.totalMatching).toBeLessThan(open.totalMatching);
    expect(
      rich.collection.features.every((feature) => (feature.properties.incomeTract?.medianHouseholdIncome ?? 0) >= 200000),
    ).toBe(true);

    const busy = await queryOrlandoFixtureParcels({
      bbox,
      county: "Orange",
      state: "Florida",
      limit: 8000,
      filters: {
        ...DEFAULT_FILTERS,
        landUseFilter: "off",
        minAadt: 80000,
        includeUnknownAadt: false,
      },
      zoningConfig,
      fluConfig,
    });
    expect(busy.totalMatching).toBeLessThan(open.totalMatching);
    expect(busy.collection.features.every((feature) => (feature.properties.nearestRoad?.aadt ?? 0) >= 80000)).toBe(true);
  });
});
