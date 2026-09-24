import { describe, expect, it } from "vitest";
import { queryMarketFixtureParcels } from "../lib/data/marketParcelStore";
import { loadFluConfig, loadZoningConfig } from "../lib/data/loadFixtures";
import { emptyStateHint } from "../lib/filters";
import {
  annotateMissingOz2Eligibility,
  lookupOz2Eligibility,
  pointInGeometry,
  pointInRing,
  type Oz2CentroidIndex,
} from "../lib/oz2CentroidJoin";
import { DEFAULT_FILTERS, type ParcelFeature } from "../lib/types";

const SQUARE: GeoJSON.Polygon = {
  type: "Polygon",
  coordinates: [
    [
      [-90.3, 35.0],
      [-90.1, 35.0],
      [-90.1, 35.2],
      [-90.3, 35.2],
      [-90.3, 35.0],
    ],
    [
      [-90.22, 35.08],
      [-90.18, 35.08],
      [-90.18, 35.12],
      [-90.22, 35.12],
      [-90.22, 35.08],
    ],
  ],
};

function cellKey(lon: number, lat: number): string {
  return `${Math.floor(lon / 0.5)}:${Math.floor(lat / 0.5)}`;
}

describe("OZ 2.0 centroid join", () => {
  it("treats a ring hole as outside and a miss as not designated", () => {
    const ring = SQUARE.coordinates[0];
    expect(pointInRing(-90.2, 35.1, ring)).toBe(true);
    expect(pointInRing(-91, 35.1, ring)).toBe(false);
    expect(pointInGeometry(-90.2, 35.15, SQUARE)).toBe(true);
    expect(pointInGeometry(-90.2, 35.1, SQUARE)).toBe(false);

    const miss = lookupOz2Eligibility({ buckets: new Map() }, -90.2, 35.1);
    expect(miss).toEqual({
      eligible: false,
      rural: null,
      tractGeoid: null,
      tractName: null,
      designation: "not-eligible",
      source: "rev-proc-2026-14",
    });

    const index: Oz2CentroidIndex = { buckets: new Map() };
    index.buckets.set(cellKey(-90.2, 35.15), [
      {
        bbox: [-90.3, 35.0, -90.1, 35.2],
        geometry: SQUARE,
        rural: true,
        tractGeoid: "05035000000",
        tractName: "fixture",
        source: "rev-proc-2026-14",
      },
    ]);
    const hit = lookupOz2Eligibility(index, -90.2, 35.15);
    expect(hit.eligible).toBe(true);
    expect(hit.rural).toBe(true);
    expect(hit.designation).toBe("eligible-for-nomination");
    expect(hit.tractGeoid).toBe("05035000000");
  });

  it("leaves a parcel that already has an OZ 2.0 stamp alone", async () => {
    const stamped = {
      eligible: true,
      rural: false,
      tractGeoid: "12095000100",
      tractName: "kept",
      designation: "eligible-for-nomination" as const,
      source: "orlando-seed",
    };
    const feature = {
      type: "Feature",
      geometry: { type: "Point", coordinates: [-81.4, 28.5] },
      properties: {
        id: "stamped",
        centroid: [-81.4, 28.5],
        oz2Eligibility: stamped,
        opportunityZone: { inOpportunityZone: false, tractGeoid: null, tractName: null, source: "seed" },
      },
    } as ParcelFeature;
    await annotateMissingOz2Eligibility([feature]);
    expect(feature.properties.oz2Eligibility).toBe(stamped);
    expect(feature.properties.opportunityZone?.inOpportunityZone).toBe(false);
  });

  it("keeps Crittenden parcels whose centroids sit in rural-eligible tracts", async () => {
    const [zoningConfig, fluConfig] = await Promise.all([loadZoningConfig(), loadFluConfig()]);
    const filters = {
      ...DEFAULT_FILTERS,
      considerOpportunityZone: true,
      considerZoning: false,
      landUseFilter: "off" as const,
      ozFilter: "rural-eligible" as const,
      minAcreage: 5,
      includeUnknownAcreage: false,
    };
    const bbox = [-90.35, 35.0, -90.05, 35.25] as [number, number, number, number];
    const page = await queryMarketFixtureParcels("Memphis", {
      bbox,
      county: "Crittenden",
      state: "Arkansas",
      limit: 8000,
      filters,
      zoningConfig,
      fluConfig,
    });

    expect(page.totalInBbox).toBeGreaterThan(0);
    expect(page.totalMatching).toBeGreaterThan(0);
    expect(page.collection.features.length).toBeGreaterThan(0);
    for (const feature of page.collection.features) {
      const oz2 = feature.properties.oz2Eligibility;
      const acres = feature.properties.acreage ?? 0;
      expect(oz2?.eligible).toBe(true);
      expect(oz2?.rural).toBe(true);
      expect(oz2?.designation).toBe("eligible-for-nomination");
      expect(oz2?.tractGeoid?.startsWith("05035")).toBe(true);
      expect(feature.properties.opportunityZone).toBeNull();
      expect(acres).toBeGreaterThanOrEqual(5);
      expect(acres).toBeLessThanOrEqual(150);
    }
    expect(emptyStateHint(filters, page.totalMatching, 0)).toBeNull();
    const empty = emptyStateHint(filters, 0, 0) ?? "";
    expect(empty).toMatch(/rural-eligible tract/);
    expect(empty).toMatch(/not a designated 2027 QOZ/);
  });
});
