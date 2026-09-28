import { TRACT_MIN_ZOOM } from "./censusTracts";

/** Same floor as the tract overlay. The wash stays on as you zoom in. */
export const PARCEL_COVERAGE_MIN_ZOOM = TRACT_MIN_ZOOM;

/** The Coverage button starts off. */
export const PARCEL_COVERAGE_DEFAULT_ON = false;

export type ParcelCoverageCounty = {
  fips: string;
  name: string;
  state: string;
};

type ManifestCounty = {
  fips?: string;
  name?: string;
  state?: string;
  featureCount?: number;
  coverage?: string;
};

/**
 * Counties that actually have parcel features in the repo manifests.
 * Gap counties are documented only. The list is not typed by hand.
 */
export function loadedParcelCounties(
  markets: Record<string, { counties?: ManifestCounty[] } | undefined>,
  orlandoCounties: ManifestCounty[],
): ParcelCoverageCounty[] {
  const byFips = new Map<string, ParcelCoverageCounty & { featureCount: number }>();
  const add = (county: ManifestCounty, fallbackState?: string) => {
    const fips = county.fips?.padStart(5, "0");
    const name = county.name?.trim();
    const state = (county.state ?? fallbackState)?.trim();
    const featureCount = county.featureCount ?? 0;
    if (!fips || !name || !state) return;
    if (featureCount <= 0 || county.coverage === "gap") return;
    const existing = byFips.get(fips);
    if (existing && existing.featureCount >= featureCount) return;
    byFips.set(fips, { fips, name, state, featureCount });
  };
  for (const market of Object.values(markets)) {
    for (const county of market?.counties ?? []) add(county);
  }
  for (const county of orlandoCounties) add(county, "Florida");
  return [...byFips.values()]
    .map(({ fips, name, state }) => ({ fips, name, state }))
    .sort((a, b) => a.fips.localeCompare(b.fips));
}

export function coverageCountyLabel(name: string, state: string): string {
  const county = /county$/i.test(name) ? name : `${name} County`;
  return `${county}, ${state}`;
}

/** Join manifest counties to Census county shapes. Counties with no boundary are skipped. */
export function parcelCoverageFeatures(
  counties: ParcelCoverageCounty[],
  boundaries: GeoJSON.FeatureCollection,
): GeoJSON.FeatureCollection {
  const byGeoid = new Map<string, GeoJSON.Geometry>();
  for (const feature of boundaries.features) {
    const geoid = feature.properties && (feature.properties as { GEOID?: string }).GEOID;
    if (!geoid || !feature.geometry) continue;
    byGeoid.set(String(geoid).padStart(5, "0"), feature.geometry);
  }
  const features: GeoJSON.Feature[] = [];
  for (const county of counties) {
    const geometry = byGeoid.get(county.fips);
    if (!geometry) continue;
    features.push({
      type: "Feature",
      id: county.fips,
      geometry,
      properties: { fips: county.fips, name: county.name, state: county.state },
    });
  }
  return { type: "FeatureCollection", features };
}
