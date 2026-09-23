export type LngLat = [number, number];

/** Mean Earth radius in statute miles (WGS84). */
const EARTH_RADIUS_MILES = 3958.7613;

function toRadians(degrees: number): number {
  return (degrees * Math.PI) / 180;
}

/** Great-circle distance in statute miles. */
export function distanceMiles(from: LngLat, to: LngLat): number {
  const dLat = toRadians(to[1] - from[1]);
  const dLng = toRadians(to[0] - from[0]);
  const lat1 = toRadians(from[1]);
  const lat2 = toRadians(to[1]);
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_MILES * Math.asin(Math.min(1, Math.sqrt(h)));
}

export type MeasureSummary = {
  segmentsMiles: number[];
  totalMiles: number;
  lastSegmentMiles: number | null;
};

export function summarizeMeasure(points: LngLat[]): MeasureSummary {
  const segmentsMiles: number[] = [];
  for (let index = 1; index < points.length; index += 1) {
    segmentsMiles.push(distanceMiles(points[index - 1], points[index]));
  }
  const totalMiles = segmentsMiles.reduce((sum, miles) => sum + miles, 0);
  return {
    segmentsMiles,
    totalMiles,
    lastSegmentMiles: segmentsMiles.length > 0 ? segmentsMiles[segmentsMiles.length - 1] : null,
  };
}

/** Drop a click that lands on the previous vertex (double-click sends two clicks). */
export function appendMeasurePoint(points: LngLat[], next: LngLat): LngLat[] {
  const last = points[points.length - 1];
  if (last && Math.abs(last[0] - next[0]) < 1e-7 && Math.abs(last[1] - next[1]) < 1e-7) {
    return points;
  }
  return [...points, next];
}

export function formatMiles(miles: number): string {
  if (!Number.isFinite(miles)) return "—";
  const absolute = Math.abs(miles);
  if (absolute < 0.1) return `${miles.toFixed(3)} mi`;
  if (absolute < 10) return `${miles.toFixed(2)} mi`;
  return `${miles.toFixed(1)} mi`;
}

export function measureFeatureCollection(points: LngLat[]): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];
  if (points.length >= 2) {
    features.push({
      type: "Feature",
      properties: { kind: "line" },
      geometry: { type: "LineString", coordinates: points },
    });
  }
  points.forEach((coordinates, index) => {
    features.push({
      type: "Feature",
      properties: { kind: "vertex", index },
      geometry: { type: "Point", coordinates },
    });
  });
  return { type: "FeatureCollection", features };
}

export const MEASURE_LINE_COLOR = "#1d4ed8";
export const MEASURE_CASING_COLOR = "#ffffff";
