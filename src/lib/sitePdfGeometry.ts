export class SitePdfError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SitePdfError";
  }
}

export function geometryBbox(
  geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon,
): [number, number, number, number] | null {
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
  for (const polygon of polygons) {
    for (const ring of polygon) {
      for (const pair of ring) {
        const x = pair[0];
        const y = pair[1];
        if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
        if (x < west) west = x;
        if (x > east) east = x;
        if (y < south) south = y;
        if (y > north) north = y;
      }
    }
  }
  if (![west, south, east, north].every((value) => Number.isFinite(value))) return null;
  if (east <= west || north <= south) return null;
  return [west, south, east, north];
}

/** Parcel extent plus neighborhood context, with a floor so a small lot is not a speck. */
export function contextBbox(
  geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon,
): [number, number, number, number] | null {
  const box = geometryBbox(geometry);
  if (!box) return null;
  const [west, south, east, north] = box;
  const minSpan = 0.012;
  const width = Math.max(east - west, minSpan);
  const height = Math.max(north - south, minSpan);
  const cx = (west + east) / 2;
  const cy = (south + north) / 2;
  return [cx - (width * 1.9) / 2, cy - (height * 1.9) / 2, cx + (width * 1.9) / 2, cy + (height * 1.9) / 2];
}

/** Regional frame for the locator inset. About a few hundred miles across. */
export function locatorBbox(lon: number, lat: number): [number, number, number, number] {
  const halfLon = 2.4;
  const halfLat = 1.8;
  return [lon - halfLon, Math.max(-85, lat - halfLat), lon + halfLon, Math.min(85, lat + halfLat)];
}

/**
 * Ground length for a scale bar near `targetPx` CSS pixels.
 * `metersPerPixel` is measured from the map, so tile size does not matter.
 */
export function chooseScaleBar(
  metersPerPixel: number,
  targetPx = 110,
): { label: string; pixels: number } {
  const feetPerPixel = metersPerPixel * 3.280839895;
  const steps = [
    { label: "100 ft", feet: 100 },
    { label: "200 ft", feet: 200 },
    { label: "500 ft", feet: 500 },
    { label: "1000 ft", feet: 1000 },
    { label: "0.25 mi", feet: 1320 },
    { label: "0.5 mi", feet: 2640 },
    { label: "1 mi", feet: 5280 },
    { label: "2 mi", feet: 10560 },
    { label: "5 mi", feet: 26400 },
    { label: "10 mi", feet: 52800 },
  ];
  let best = steps[0];
  let bestScore = Infinity;
  let fallback = steps[0];
  let fallbackScore = Infinity;
  for (const step of steps) {
    const pixels = step.feet / feetPerPixel;
    const score = Math.abs(pixels - targetPx);
    if (score < fallbackScore) {
      fallback = step;
      fallbackScore = score;
    }
    if (pixels >= 64 && pixels <= 180 && score < bestScore) {
      best = step;
      bestScore = score;
    }
  }
  const chosen = bestScore === Infinity ? fallback : best;
  return { label: chosen.label, pixels: chosen.feet / feetPerPixel };
}

export function haversineMeters(a: [number, number], b: [number, number]): number {
  const radius = 6_371_008.8;
  const toRad = (degrees: number) => (degrees * Math.PI) / 180;
  const dLat = toRad(b[1] - a[1]);
  const dLon = toRad(b[0] - a[0]);
  const lat1 = toRad(a[1]);
  const lat2 = toRad(b[1]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * radius * Math.asin(Math.min(1, Math.sqrt(h)));
}
