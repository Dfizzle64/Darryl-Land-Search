import { describe, expect, it } from "vitest";
import {
  appendMeasurePoint,
  distanceMiles,
  formatMiles,
  measureFeatureCollection,
  summarizeMeasure,
} from "../lib/measure";

describe("measure distances", () => {
  it("converts a degree of longitude at the equator to about 69.1 miles", () => {
    const miles = distanceMiles([0, 0], [1, 0]);
    expect(miles).toBeGreaterThan(69);
    expect(miles).toBeLessThan(69.2);
    expect(formatMiles(miles)).toBe("69.1 mi");
  });

  it("sums segment miles and ignores a duplicate click on the last vertex", () => {
    const points = appendMeasurePoint(
      [
        [0, 0],
        [1, 0],
      ],
      [1, 0],
    );
    expect(points).toHaveLength(2);
    const withThird = appendMeasurePoint(points, [1, 1]);
    const summary = summarizeMeasure(withThird);
    expect(summary.segmentsMiles).toHaveLength(2);
    expect(summary.totalMiles).toBeCloseTo(summary.segmentsMiles[0] + summary.segmentsMiles[1], 6);
    expect(summary.lastSegmentMiles).toBeCloseTo(summary.segmentsMiles[1], 6);
    expect(formatMiles(0.084)).toBe("0.084 mi");
    expect(formatMiles(1.2)).toBe("1.20 mi");
  });

  it("draws a line only after the second point", () => {
    expect(measureFeatureCollection([[-81.3, 28.5]]).features).toHaveLength(1);
    const drawn = measureFeatureCollection([
      [-81.3, 28.5],
      [-81.2, 28.6],
    ]);
    expect(drawn.features.map((feature) => feature.geometry.type)).toEqual(["LineString", "Point", "Point"]);
  });
});
