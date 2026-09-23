/**
 * Esri polygon rings to GeoJSON.
 *
 * ArcGIS exteriors are clockwise and holes are counter-clockwise. GeoJSON
 * (RFC 7946) wants the opposite. A positive shoelace area is a hole, not a
 * new exterior. Simplify stays near 1–7 meters so a shoreline is not replaced
 * by its first three vertices.
 */

/** ~1.3 m at Florida latitudes. */
export const PARCEL_SIMPLIFY_TOLERANCE = 0.000012;
/** ~4 m, used only when a ring is still very dense. */
export const PARCEL_SIMPLIFY_RELAXED = 0.000035;
/** ~7 m ceiling. The old seed jumped to ~30 m. */
export const PARCEL_SIMPLIFY_MAX = 0.00006;

export function signedArea(coords: number[][]): number {
  let area = 0;
  for (let i = 0; i < coords.length - 1; i += 1) {
    area += coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1];
  }
  return area / 2;
}

function perpDist(p: [number, number], a: [number, number], b: [number, number]): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  if (dx === 0 && dy === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}

function douglasPeucker(points: [number, number][], tol: number): [number, number][] {
  if (points.length <= 2) return points;
  const stack: Array<[number, number]> = [[0, points.length - 1]];
  const keep = new Set<number>([0, points.length - 1]);
  while (stack.length) {
    const [start, end] = stack.pop()!;
    let maxD = 0;
    let idx: number | null = null;
    for (let i = start + 1; i < end; i += 1) {
      const dist = perpDist(points[i], points[start], points[end]);
      if (dist > maxD) {
        maxD = dist;
        idx = i;
      }
    }
    if (idx != null && maxD > tol) {
      keep.add(idx);
      stack.push([start, idx], [idx, end]);
    }
  }
  return [...keep].sort((a, b) => a - b).map((i) => points[i]);
}

function close(points: [number, number][]): [number, number][] {
  if (!points.length) return points;
  const first = points[0];
  const last = points[points.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) return [...points, first];
  return points;
}

function roundRing(points: [number, number][]): number[][] {
  return points.map(([x, y]) => [Math.round(x * 1e6) / 1e6, Math.round(y * 1e6) / 1e6]);
}

export function simplifyRing(coords: number[][], tol = PARCEL_SIMPLIFY_TOLERANCE): number[][] {
  if (coords.length < 4) return [];
  const open = coords[0][0] === coords[coords.length - 1][0] && coords[0][1] === coords[coords.length - 1][1]
    ? coords.slice(0, -1)
    : coords.slice();
  const pts = open.map(([x, y]) => [x, y] as [number, number]);
  if (pts.length < 3) return [];
  if (pts.length <= 4) return roundRing(close(pts));
  let simplified = douglasPeucker(pts, tol);
  if (simplified.length > 500) simplified = douglasPeucker(pts, Math.max(tol, PARCEL_SIMPLIFY_RELAXED));
  if (simplified.length > 800) simplified = douglasPeucker(pts, Math.max(tol, PARCEL_SIMPLIFY_MAX));
  if (simplified.length < 3) {
    const step = Math.max(1, Math.floor(pts.length / 80));
    simplified = pts.filter((_, index) => index % step === 0);
    if (simplified.length < 3) simplified = pts;
  }
  simplified = close(simplified);
  if (simplified.length < 4) simplified = close(pts);
  return roundRing(simplified);
}

function ensureClosed(raw: number[][]): number[][] {
  const first = raw[0];
  const last = raw[raw.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) return [...raw, [...first]];
  return raw;
}

/** Group Esri rings into polygons and emit RFC 7946 winding. */
export function esriRingsToGeoJSON(
  rings: number[][][] | undefined,
  tol = PARCEL_SIMPLIFY_TOLERANCE,
): GeoJSON.Polygon | GeoJSON.MultiPolygon | null {
  const polygons: number[][][][] = [];
  let current: number[][][] = [];
  for (const ring of rings ?? []) {
    let raw = ring.map(([x, y]) => [x, y]);
    if (raw.length < 4) continue;
    raw = ensureClosed(raw);
    const area = signedArea(raw);
    if (Math.abs(area) < 1e-14) continue;
    const coords = simplifyRing(raw, tol);
    if (coords.length < 4) continue;
    const isHole = area > 0;
    if (isHole && current.length) current.push(coords);
    else {
      if (current.length) polygons.push(current);
      current = [coords];
    }
  }
  if (current.length) polygons.push(current);
  if (!polygons.length) return null;

  const normalized = polygons.map((poly) => {
    let outer = poly[0];
    if (signedArea(outer) < 0) outer = [...outer].reverse();
    const holes = poly.slice(1).map((hole) => (signedArea(hole) > 0 ? [...hole].reverse() : hole));
    return [outer, ...holes];
  });
  if (normalized.length === 1) return { type: "Polygon", coordinates: normalized[0] };
  return { type: "MultiPolygon", coordinates: normalized };
}

function pointInRing(x: number, y: number, ring: number[][]): boolean {
  let inside = false;
  let j = ring.length - 1;
  for (let i = 0; i < ring.length; i += 1) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi || 1e-12) + xi) inside = !inside;
    j = i;
  }
  return inside;
}

function insidePolygon(x: number, y: number, poly: number[][][]): boolean {
  if (!poly.length || !pointInRing(x, y, poly[0])) return false;
  return poly.slice(1).every((hole) => !pointInRing(x, y, hole));
}

function partsOf(geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon): number[][][][] {
  return geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
}

/** A point inside the largest part. Vertex averages fall outside concave rings. */
export function representativePoint(geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon): [number, number] | null {
  let best: number[][][] | null = null;
  let bestArea = -1;
  for (const poly of partsOf(geometry)) {
    if (!poly[0]) continue;
    const area = Math.abs(signedArea(poly[0]));
    if (area > bestArea) {
      bestArea = area;
      best = poly;
    }
  }
  if (!best) return null;
  const ring = best[0];
  const body = ring.slice(0, -1);
  if (!body.length) return null;
  const lon = body.reduce((sum, p) => sum + p[0], 0) / body.length;
  const lat = body.reduce((sum, p) => sum + p[1], 0) / body.length;
  const round = (x: number, y: number): [number, number] => [Math.round(x * 1e6) / 1e6, Math.round(y * 1e6) / 1e6];
  if (insidePolygon(lon, lat, best)) return round(lon, lat);
  const xs = body.map((p) => p[0]);
  const ys = body.map((p) => p[1]);
  const bx = (Math.min(...xs) + Math.max(...xs)) / 2;
  const by = (Math.min(...ys) + Math.max(...ys)) / 2;
  if (insidePolygon(bx, by, best)) return round(bx, by);
  const step = Math.max(1, Math.floor(body.length / 16));
  for (let i = 0; i < body.length; i += step) {
    const qlon = body[i][0] * 0.8 + lon * 0.2;
    const qlat = body[i][1] * 0.8 + lat * 0.2;
    if (insidePolygon(qlon, qlat, best)) return round(qlon, qlat);
  }
  return round(body[0][0], body[0][1]);
}
