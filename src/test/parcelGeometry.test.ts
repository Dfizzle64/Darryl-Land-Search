import { describe, expect, it } from "vitest";
import {
  PARCEL_LOW_ZOOM_TOLERANCE,
  PARCEL_SIMPLIFY_MAX,
  esriRingsToGeoJSON,
  parcelVertexCount,
  representativePoint,
  signedArea,
  simplifyParcelFeature,
  simplifyRing,
} from "../lib/parcelGeometry";

/** Clockwise square (negative shoelace). Esri treats this as an exterior. */
const OUTER: number[][] = [
  [0, 0],
  [0, 1],
  [1, 1],
  [1, 0],
  [0, 0],
];

/** Counter-clockwise hole inside OUTER (positive shoelace). */
const HOLE: number[][] = [
  [0.2, 0.2],
  [0.4, 0.2],
  [0.4, 0.4],
  [0.2, 0.4],
  [0.2, 0.2],
];

/** A second clockwise exterior, not a hole of the first square. */
const OTHER: number[][] = [
  [3, 0],
  [3, 1],
  [4, 1],
  [4, 0],
  [3, 0],
];

describe("parcel geometry", () => {
  it("keeps an Esri hole as a hole and flips to GeoJSON winding", () => {
    const geometry = esriRingsToGeoJSON([OUTER, HOLE]);
    expect(geometry?.type).toBe("Polygon");
    if (geometry?.type !== "Polygon") return;
    expect(geometry.coordinates).toHaveLength(2);
    expect(signedArea(geometry.coordinates[0])).toBeGreaterThan(0);
    expect(signedArea(geometry.coordinates[1])).toBeLessThan(0);
    const point = representativePoint(geometry);
    expect(point).not.toBeNull();
    expect(point![0]).toBeGreaterThan(0);
    expect(point![0]).toBeLessThan(1);
  });

  it("does not stuff a second exterior ring in as a hole", () => {
    const geometry = esriRingsToGeoJSON([OUTER, OTHER]);
    expect(geometry?.type).toBe("MultiPolygon");
    if (geometry?.type !== "MultiPolygon") return;
    expect(geometry.coordinates).toHaveLength(2);
    expect(geometry.coordinates.every((poly) => poly.length === 1)).toBe(true);
    expect(geometry.coordinates.every((poly) => signedArea(poly[0]) > 0)).toBe(true);
  });

  it("keeps a wavy ring instead of collapsing it to the first three vertices", () => {
    const ring: number[][] = [[-81.2, 28.5]];
    for (let i = 1; i <= 40; i += 1) {
      const t = i / 40;
      ring.push([-81.2 + t * 0.01, 28.5 + Math.sin(t * Math.PI * 6) * 0.0004]);
    }
    ring.push([-81.19, 28.49], [-81.2, 28.49], ring[0]);
    const simplified = simplifyRing(ring);
    expect(simplified.length).toBeGreaterThan(8);
    expect(PARCEL_SIMPLIFY_MAX).toBeLessThan(0.0001);
    const geometry = esriRingsToGeoJSON([ring]);
    expect(geometry?.type).toBe("Polygon");
    if (geometry?.type !== "Polygon") return;
    expect(geometry.coordinates[0].length).toBeGreaterThan(8);
  });

  it("picks an interior point on a concave ring whose vertex average is outside", () => {
    const cShape: number[][] = [
      [0, 0],
      [3, 0],
      [3, 1],
      [1, 1],
      [1, 2],
      [3, 2],
      [3, 3],
      [0, 3],
      [0, 0],
    ];
    const geometry = esriRingsToGeoJSON([cShape]);
    expect(geometry).not.toBeNull();
    const point = representativePoint(geometry!);
    expect(point).not.toBeNull();
    expect(point![0]).toBeGreaterThanOrEqual(0);
    expect(point![0]).toBeLessThanOrEqual(1.05);
    expect(point![1]).toBeGreaterThan(0);
    expect(point![1]).toBeLessThan(3);
  });

  it("simplifies a dense parcel for zoom 8 without changing acreage", () => {
    const ring: number[][] = [[-81.5, 28.5]];
    for (let i = 1; i <= 40; i += 1) {
      const angle = (i / 40) * Math.PI * 2;
      ring.push([-81.5 + Math.cos(angle) * 0.01, 28.5 + Math.sin(angle) * 0.01]);
    }
    ring.push(ring[0]);
    const feature = {
      type: "Feature" as const,
      geometry: { type: "Polygon" as const, coordinates: [ring] },
      properties: { acreage: 12.5 },
    };
    const simplified = simplifyParcelFeature(feature, PARCEL_LOW_ZOOM_TOLERANCE);
    expect(simplified.properties.acreage).toBe(12.5);
    expect(parcelVertexCount(simplified.geometry)).toBeLessThan(parcelVertexCount(feature.geometry));
    expect(parcelVertexCount(simplified.geometry)).toBeGreaterThanOrEqual(4);
    expect(feature.geometry.coordinates[0].length).toBeGreaterThan(40);
  });
});
