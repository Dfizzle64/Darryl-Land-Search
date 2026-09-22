import { describe, expect, it } from "vitest";
import {
  AOI_PARCEL_LIMIT,
  aoiFeatureCollection,
  bboxAreaAcres,
  bboxPolygonFeature,
  featuresIntersectingBbox,
  normalizeBbox,
} from "../lib/aoi";

describe("area of interest", () => {
  it("normalizes drag corners and rejects click-sized boxes", () => {
    expect(normalizeBbox(-81.2, 28.6, -81.5, 28.4)).toEqual([-81.5, 28.4, -81.2, 28.6]);
    expect(normalizeBbox(-81.2, 28.5, -81.2, 28.6)).toBeNull();
    expect(normalizeBbox(Number.NaN, 28, -81, 29)).toBeNull();
  });

  it("estimates bbox acreage near Orlando", () => {
    const acres = bboxAreaAcres([-81.4, 28.5, -81.39, 28.51]);
    expect(acres).toBeGreaterThan(240);
    expect(acres).toBeLessThan(300);
  });

  it("draws a closed rectangle ring", () => {
    const feature = bboxPolygonFeature([-81.5, 28.4, -81.2, 28.6]);
    const ring = feature.geometry.coordinates[0];
    expect(ring).toHaveLength(5);
    expect(ring[0]).toEqual(ring[4]);
    expect(ring[1]).toEqual([-81.2, 28.4]);
    expect(aoiFeatureCollection(null).features).toHaveLength(0);
  });

  it("keeps only centroids inside the locked boundary", () => {
    const features = [
      { properties: { centroid: [-81.3, 28.5] as [number, number] } },
      { properties: { centroid: [-80.1, 27.1] as [number, number] } },
      { properties: { centroid: [-81.5, 28.4] as [number, number] } },
    ];
    const inside = featuresIntersectingBbox(features, [-81.5, 28.4, -81.2, 28.6]);
    expect(inside).toHaveLength(2);
    expect(inside.map((feature) => feature.properties.centroid[0])).toEqual([-81.3, -81.5]);
  });

  it("asks the parcel API for a stable set up to the server cap", () => {
    expect(AOI_PARCEL_LIMIT).toBe(8000);
    expect(AOI_PARCEL_LIMIT).toBeLessThanOrEqual(8000);
  });
});
