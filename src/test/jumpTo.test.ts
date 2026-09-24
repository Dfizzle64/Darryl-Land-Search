import { describe, expect, it } from "vitest";
import {
  ADDRESS_NOT_FOUND,
  censusMatchPoint,
  coordinateError,
  geometryContains,
  parcelAtPoint,
  parseLatLng,
  pointInBounds,
  SOUTH_FLORIDA_BOUNDS,
} from "../lib/jumpTo";

describe("jump-to address bar", () => {
  it("parses lat, long and longitude-first pairs", () => {
    expect(parseLatLng("26.1224, -80.1373")).toEqual({ lat: 26.1224, lng: -80.1373 });
    expect(parseLatLng("26.1224 -80.1373")).toEqual({ lat: 26.1224, lng: -80.1373 });
    expect(parseLatLng("25.7617, -80.1918")).toEqual({ lat: 25.7617, lng: -80.1918 });
    expect(parseLatLng("-80.1918, 25.7617")).toEqual({ lat: 25.7617, lng: -80.1918 });
    expect(parseLatLng("123 Main St, Miami, FL")).toBeNull();
    expect(parseLatLng("25.7")).toBeNull();
    expect(parseLatLng("200, 400")).toBeNull();
    expect(coordinateError("200, 400")).toBe("Those coordinates are not valid.");
    expect(coordinateError("26.1224, -80.1373")).toBeNull();
    expect(coordinateError("123 Main St, Fort Lauderdale, FL")).toBeNull();
    expect(ADDRESS_NOT_FOUND).toBe("Couldn't find that address.");
  });

  it("reads a Census oneline match", () => {
    expect(
      censusMatchPoint({
        result: { addressMatches: [{ coordinates: { x: -80.1918, y: 25.7617 } }] },
      }),
    ).toEqual({ lng: -80.1918, lat: 25.7617 });
    expect(censusMatchPoint({ result: { addressMatches: [] } })).toBeNull();
  });

  it("selects the parcel polygon under the point", () => {
    const outer: GeoJSON.Feature<GeoJSON.Polygon> = {
      type: "Feature",
      properties: {},
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-80.2, 25.7],
            [-80.1, 25.7],
            [-80.1, 25.8],
            [-80.2, 25.8],
            [-80.2, 25.7],
          ],
        ],
      },
    };
    const inner: GeoJSON.Feature<GeoJSON.Polygon> = {
      type: "Feature",
      properties: { id: "inner" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-80.16, 25.74],
            [-80.14, 25.74],
            [-80.14, 25.76],
            [-80.16, 25.76],
            [-80.16, 25.74],
          ],
        ],
      },
    };
    expect(geometryContains(-80.15, 25.75, outer.geometry)).toBe(true);
    expect(geometryContains(-80.5, 25.75, outer.geometry)).toBe(false);
    expect(parcelAtPoint([outer, inner], -80.15, 25.75)).toBe(inner);
    expect(parcelAtPoint([outer], -81, 26)).toBeNull();
    expect(pointInBounds(-80.19, 25.76, SOUTH_FLORIDA_BOUNDS)).toBe(true);
    expect(pointInBounds(-84, 25.76, SOUTH_FLORIDA_BOUNDS)).toBe(false);
  });
});
