import { showOzTractInScMarkets } from "./scNominatedTracts";
import { formatTractCounty } from "./tractCounty";

/**
 * County-scale gate for 2020 census tract outlines.
 * Below this, a typical screen covers more than a few counties and the
 * boundary layer would turn into a national mesh.
 */
export const TRACT_MIN_ZOOM = 8;

/** Each TIGERweb request stays inside this span so a pan does not pull a state. */
export const TRACT_TILE_DEGREES = 2;

/** Cap parallel tiles. The center of the view is kept when the screen is wider. */
export const TRACT_MAX_TILES = 12;

export const CENSUS_TRACT_LINE_LAYER = "census-tract-line";

export const CENSUS_TRACTS_SOURCE =
  "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/6/query";

const STATE_NAME_BY_FIPS: Record<string, string> = {
  "01": "Alabama",
  "02": "Alaska",
  "04": "Arizona",
  "05": "Arkansas",
  "06": "California",
  "08": "Colorado",
  "09": "Connecticut",
  "10": "Delaware",
  "11": "District of Columbia",
  "12": "Florida",
  "13": "Georgia",
  "15": "Hawaii",
  "16": "Idaho",
  "17": "Illinois",
  "18": "Indiana",
  "19": "Iowa",
  "20": "Kansas",
  "21": "Kentucky",
  "22": "Louisiana",
  "23": "Maine",
  "24": "Maryland",
  "25": "Massachusetts",
  "26": "Michigan",
  "27": "Minnesota",
  "28": "Mississippi",
  "29": "Missouri",
  "30": "Montana",
  "31": "Nebraska",
  "32": "Nevada",
  "33": "New Hampshire",
  "34": "New Jersey",
  "35": "New Mexico",
  "36": "New York",
  "37": "North Carolina",
  "38": "North Dakota",
  "39": "Ohio",
  "40": "Oklahoma",
  "41": "Oregon",
  "42": "Pennsylvania",
  "44": "Rhode Island",
  "45": "South Carolina",
  "46": "South Dakota",
  "47": "Tennessee",
  "48": "Texas",
  "49": "Utah",
  "50": "Vermont",
  "51": "Virginia",
  "53": "Washington",
  "54": "West Virginia",
  "55": "Wisconsin",
  "56": "Wyoming",
  "72": "Puerto Rico",
};

export type TractBbox = [number, number, number, number];

export type ViewportTractProperties = {
  tractGeoid: string;
  name: string | null;
  stateName: string | null;
  county: string | null;
  state: string | null;
  /** Present only when this GEOID is in an OZ 2.0 fixture. Never defaulted. */
  rural?: boolean;
  eligible?: boolean;
  /** Present only when this GEOID is in the designated QOZ extract. */
  designatedQoz?: boolean;
  /** Present only when ACS B19013 has a positive median for this GEOID. */
  medianHouseholdIncome?: number;
};

export type ViewportTractFeature = GeoJSON.Feature<
  GeoJSON.Polygon | GeoJSON.MultiPolygon,
  ViewportTractProperties
>;

/** Joined from fixtures already on the map. Absence means we do not know. */
export type KnownTractAttributes = {
  county: string | null;
  state: string | null;
  rural: boolean | null;
  eligible: boolean;
  designated: boolean;
  medianHouseholdIncome?: number;
};

export function tractsVisibleAtZoom(zoom: number): boolean {
  return Number.isFinite(zoom) && zoom >= TRACT_MIN_ZOOM;
}

export function stateNameFromFips(fips: string | null | undefined): string | null {
  if (!fips) return null;
  const key = String(fips).padStart(2, "0").slice(-2);
  return STATE_NAME_BY_FIPS[key] ?? null;
}

export function normalizeTractGeoid(value: unknown): string | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(Math.trunc(value)).padStart(11, "0");
  }
  if (typeof value !== "string") return null;
  const digits = value.replace(/\D/g, "");
  if (!digits) return null;
  if (digits.length > 11) return digits.slice(0, 11);
  return digits.padStart(11, "0");
}

export function generalizationBand(zoom: number): "far" | "mid" | "near" {
  if (zoom < 10) return "far";
  if (zoom < 12) return "mid";
  return "near";
}

/** Degrees of generalization for TIGERweb `maxAllowableOffset`. Coarser when zoomed out. */
export function maxAllowableOffset(zoom: number): number {
  const band = generalizationBand(zoom);
  if (band === "far") return 0.012;
  if (band === "mid") return 0.004;
  return 0.0015;
}

export function tractTilesForBbox(bbox: TractBbox): TractBbox[] {
  const [west, south, east, north] = bbox;
  if (![west, south, east, north].every((value) => Number.isFinite(value))) return [];
  if (east <= west || north <= south) return [];
  const width = east - west;
  const height = north - south;
  const cols = Math.max(1, Math.ceil(width / TRACT_TILE_DEGREES));
  const rows = Math.max(1, Math.ceil(height / TRACT_TILE_DEGREES));
  const colSize = width / cols;
  const rowSize = height / rows;
  const tiles: TractBbox[] = [];
  for (let col = 0; col < cols; col += 1) {
    for (let row = 0; row < rows; row += 1) {
      tiles.push([
        west + col * colSize,
        south + row * rowSize,
        col === cols - 1 ? east : west + (col + 1) * colSize,
        row === rows - 1 ? north : south + (row + 1) * rowSize,
      ]);
    }
  }
  if (tiles.length <= TRACT_MAX_TILES) return tiles;
  const centerX = (west + east) / 2;
  const centerY = (south + north) / 2;
  const distance = (tile: TractBbox) => {
    const x = (tile[0] + tile[2]) / 2 - centerX;
    const y = (tile[1] + tile[3]) / 2 - centerY;
    return x * x + y * y;
  };
  return tiles.sort((a, b) => distance(a) - distance(b)).slice(0, TRACT_MAX_TILES);
}

export function buildTigerQuery(bbox: TractBbox, zoom: number): string {
  const [west, south, east, north] = bbox;
  const url = new URL(CENSUS_TRACTS_SOURCE);
  url.searchParams.set("where", "1=1");
  url.searchParams.set("geometry", `${west},${south},${east},${north}`);
  url.searchParams.set("geometryType", "esriGeometryEnvelope");
  url.searchParams.set("inSR", "4326");
  url.searchParams.set("spatialRel", "esriSpatialRelIntersects");
  url.searchParams.set("outFields", "GEOID,NAME,STATE,COUNTY,BASENAME");
  url.searchParams.set("returnGeometry", "true");
  url.searchParams.set("outSR", "4326");
  url.searchParams.set("f", "geojson");
  url.searchParams.set("maxAllowableOffset", String(maxAllowableOffset(zoom)));
  return url.toString();
}

function isPolygonGeometry(
  geometry: GeoJSON.Geometry | null | undefined,
): geometry is GeoJSON.Polygon | GeoJSON.MultiPolygon {
  return geometry?.type === "Polygon" || geometry?.type === "MultiPolygon";
}

export function normalizeTigerFeature(feature: GeoJSON.Feature): ViewportTractFeature | null {
  if (!isPolygonGeometry(feature.geometry)) return null;
  const props = (feature.properties ?? {}) as Record<string, unknown>;
  const tractGeoid = normalizeTractGeoid(props.GEOID ?? props.geoid ?? props.tractGeoid);
  if (!tractGeoid) return null;
  const stateFips = typeof props.STATE === "string" || typeof props.STATE === "number" ? String(props.STATE) : null;
  const name =
    typeof props.NAME === "string" && props.NAME.trim()
      ? props.NAME.trim()
      : typeof props.BASENAME === "string" && props.BASENAME.trim()
        ? `Census Tract ${props.BASENAME.trim()}`
        : null;
  return {
    type: "Feature",
    geometry: feature.geometry,
    properties: {
      tractGeoid,
      name,
      stateName: stateNameFromFips(stateFips),
      county: null,
      state: stateNameFromFips(stateFips),
    },
  };
}

export function parseTigerCollection(body: unknown): ViewportTractFeature[] {
  if (!body || typeof body !== "object") return [];
  const features = (body as { features?: unknown }).features;
  if (!Array.isArray(features)) return [];
  const parsed: ViewportTractFeature[] = [];
  for (const feature of features) {
    if (!feature || typeof feature !== "object") continue;
    const next = normalizeTigerFeature(feature as GeoJSON.Feature);
    if (next) parsed.push(next);
  }
  return parsed;
}

/**
 * Copy a positive ACS B19013 median onto a tract. GEOIDs missing from the
 * table are left untouched — no zero, no null placeholder.
 */
export function stampKnownIncome<T extends { properties: { tractGeoid?: string; medianHouseholdIncome?: number } }>(
  features: T[],
  income: ReadonlyMap<string, number>,
): T[] {
  for (const feature of features) {
    const geoid = feature.properties.tractGeoid;
    if (!geoid) continue;
    const value = income.get(geoid);
    if (value == null || !Number.isFinite(value) || value <= 0) continue;
    feature.properties.medianHouseholdIncome = value;
  }
  return features;
}

type IndexableFeature = {
  properties: {
    tractGeoid?: string;
    county?: string | null;
    state?: string | null;
    rural?: boolean | null;
    medianHouseholdIncome?: number | null;
  };
};

export function buildTractAttributeIndex(collections: {
  eligible?: { features: IndexableFeature[] };
  rural?: { features: IndexableFeature[] };
  oz2?: { features: IndexableFeature[] };
  designated?: { features: IndexableFeature[] };
}): Map<string, KnownTractAttributes> {
  const index = new Map<string, KnownTractAttributes>();
  const addEligible = (feature: IndexableFeature) => {
    const geoid = feature.properties.tractGeoid;
    if (!geoid) return;
    const current = index.get(geoid) ?? {
      county: null,
      state: null,
      rural: null,
      eligible: false,
      designated: false,
    };
    current.eligible = true;
    if (feature.properties.county) current.county = feature.properties.county;
    if (feature.properties.state) current.state = feature.properties.state;
    if (feature.properties.rural === true || feature.properties.rural === false) {
      current.rural = feature.properties.rural;
    }
    const income = feature.properties.medianHouseholdIncome;
    if (typeof income === "number" && Number.isFinite(income) && income > 0) {
      current.medianHouseholdIncome = income;
    }
    index.set(geoid, current);
  };
  for (const feature of collections.eligible?.features ?? []) addEligible(feature);
  for (const feature of collections.rural?.features ?? []) addEligible(feature);
  for (const feature of collections.oz2?.features ?? []) addEligible(feature);
  for (const feature of collections.designated?.features ?? []) {
    const geoid = feature.properties.tractGeoid;
    if (!geoid) continue;
    const current = index.get(geoid) ?? {
      county: null,
      state: null,
      rural: null,
      eligible: false,
      designated: false,
    };
    current.designated = true;
    if (feature.properties.county) current.county = feature.properties.county;
    if (feature.properties.state) current.state = feature.properties.state;
    index.set(geoid, current);
  }
  return index;
}

/**
 * Attach fixture attributes onto a viewport tract. South Carolina tracts that
 * are not on the governor list stay outline-only. Income is copied only when
 * a positive median is already known.
 */
export function annotateViewportTract(
  feature: ViewportTractFeature,
  index: ReadonlyMap<string, KnownTractAttributes>,
): ViewportTractFeature {
  const hit = index.get(feature.properties.tractGeoid);
  const next: ViewportTractProperties = {
    tractGeoid: feature.properties.tractGeoid,
    name: feature.properties.name,
    stateName: feature.properties.stateName,
    county: feature.properties.county,
    state: feature.properties.state,
  };
  if (typeof feature.properties.medianHouseholdIncome === "number" && feature.properties.medianHouseholdIncome > 0) {
    next.medianHouseholdIncome = feature.properties.medianHouseholdIncome;
  }
  if (!hit) return { ...feature, properties: next };

  if (hit.county) next.county = hit.county;
  if (hit.state) next.state = hit.state;
  if (hit.medianHouseholdIncome != null && next.medianHouseholdIncome == null) {
    next.medianHouseholdIncome = hit.medianHouseholdIncome;
  }
  const eligible =
    hit.eligible &&
    showOzTractInScMarkets({
      state: hit.state ?? next.state,
      geoid: feature.properties.tractGeoid,
    });
  if (eligible) {
    next.eligible = true;
    if (hit.rural === true || hit.rural === false) next.rural = hit.rural;
  }
  if (hit.designated) next.designatedQoz = true;
  return { ...feature, properties: next };
}

export function annotateViewportTracts(
  features: ViewportTractFeature[],
  index: ReadonlyMap<string, KnownTractAttributes>,
): ViewportTractFeature[] {
  return features.map((feature) => annotateViewportTract(feature, index));
}

export function mergeTractFeatures(groups: ViewportTractFeature[][]): ViewportTractFeature[] {
  const byGeoid = new Map<string, ViewportTractFeature>();
  for (const group of groups) {
    for (const feature of group) {
      byGeoid.set(feature.properties.tractGeoid, feature);
    }
  }
  return [...byGeoid.values()];
}

export function viewportTractPlace(properties: ViewportTractProperties): string {
  if (properties.county || properties.state) return formatTractCounty(properties.county, properties.state);
  if (properties.stateName && properties.name) return `${properties.name}, ${properties.stateName}`;
  if (properties.stateName) return properties.stateName;
  if (properties.name) return properties.name;
  return "2020 census tract";
}
