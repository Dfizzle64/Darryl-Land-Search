import { describe, expect, it } from "vitest";
import { MAX_AADT_DISTANCE_METERS, buildOrangeSignalIndex, nearestRoad } from "../lib/orangeSignals";
import type { ParcelFeature } from "../lib/types";
import { annotateParcelSignals } from "../lib/orangeSignals";

function road(lon: number, lat: number, aadt: number) {
  return {
    type: "Feature" as const,
    geometry: {
      type: "LineString" as const,
      coordinates: [
        [lon, lat],
        [lon + 0.001, lat],
      ],
    },
    properties: { aadt, year: 2025, roadwayId: "1", from: "A", to: "B" },
  };
}

describe("parcel income and AADT join", () => {
  it("leaves a parcel unknown when the nearest FDOT segment is farther than 15 km", () => {
    const index = buildOrangeSignalIndex(
      { type: "FeatureCollection", features: [] },
      { type: "FeatureCollection", features: [] },
      { type: "FeatureCollection", features: [road(-81.4, 28.5, 40000)] },
    );
    const close = nearestRoad(-81.4, 28.5, index.roads, index.roadGrid);
    expect(close?.aadt).toBe(40000);
    expect(close!.distanceMeters).toBeLessThan(MAX_AADT_DISTANCE_METERS);

    const far = nearestRoad(-81.0, 28.5, index.roads, index.roadGrid);
    expect(far).toBeNull();
  });

  it("does not invent income for a point outside the tract fixture", () => {
    const index = buildOrangeSignalIndex(
      {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: {
              type: "Polygon",
              coordinates: [
                [
                  [-81.5, 28.4],
                  [-81.3, 28.4],
                  [-81.3, 28.6],
                  [-81.5, 28.6],
                  [-81.5, 28.4],
                ],
              ],
            },
            properties: {
              geoid: "12095000100",
              name: "Census Tract 1",
              medianHouseholdIncome: 72000,
              medianHouseholdIncomeMoe: 1000,
            },
          },
        ],
      },
      { type: "FeatureCollection", features: [] },
      { type: "FeatureCollection", features: [] },
    );
    const outside = {
      type: "Feature",
      geometry: { type: "Polygon", coordinates: [] },
      properties: { centroid: [-84, 33] },
    } as unknown as ParcelFeature;
    annotateParcelSignals(outside, index);
    expect(outside.properties.incomeTract).toBeUndefined();

    const inside = {
      type: "Feature",
      geometry: { type: "Polygon", coordinates: [] },
      properties: { centroid: [-81.4, 28.5], incomeTract: null, incomeBlockGroup: null, nearestRoad: null },
    } as unknown as ParcelFeature;
    annotateParcelSignals(inside, index);
    expect(inside.properties.incomeTract?.medianHouseholdIncome).toBe(72000);
  });
});
