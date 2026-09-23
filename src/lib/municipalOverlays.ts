import { pointInRing } from "./orangeSignals";
import type { BBox, FluInfo, ParcelFeature, ParcelProperties } from "./types";

/**
 * Orange County municipal zoning and future land use.
 * Attribute join on the parcel id wins. A centroid-in-polygon join fills gaps.
 * Layers outside Florida, including Edgewood, Texas, are ignored.
 */

export const FLORIDA_BBOX: BBox = [-87.7, 24.3, -79.6, 31.1];
export const ORANGE_FL_BBOX: BBox = [-81.95, 28.15, -80.7, 28.95];

export const REJECTED_EDGEWOOD_TEXAS_URL =
  "https://maps.etcog.org/arcgis/rest/services/EDGEWOOD/EdgewoodZoning_Public/FeatureServer/4";

export type MunicipalJoin = "attribute" | "spatial";

export type MunicipalAttribute = {
  zoningCode: string | null;
  zoningLabel: string | null;
  fluCode: string | null;
  fluLabel: string | null;
};

export type MunicipalSpatialFeature = MunicipalAttribute & {
  bbox: BBox;
  polygons: number[][][][];
  parcelId: string | null;
  area: number;
};

export type MunicipalCityIndex = {
  id: string;
  name: string;
  prefix: string;
  status: "active" | "gap";
  bbox: BBox | null;
  attributes: Map<string, MunicipalAttribute>;
  spatial: MunicipalSpatialFeature[];
};

export type MunicipalOverlayIndex = {
  cities: MunicipalCityIndex[];
};

export type MunicipalHit = {
  id: string;
  name: string;
  prefix: string;
  join: MunicipalJoin;
  zoningCode: string | null;
  zoningLabel: string | null;
  fluCode: string | null;
  fluLabel: string | null;
  area: number;
};

type CompactAttr = { z?: string; zl?: string; f?: string; fl?: string };
type CompactSpatial = CompactAttr & { b?: number[]; g?: number[][][][]; id?: string };
type CompactCity = {
  id: string;
  name: string;
  prefix: string;
  status?: string;
  bbox?: number[] | null;
  attributes?: Record<string, CompactAttr>;
  spatial?: CompactSpatial[];
};

export function bboxInside(inner: BBox, outer: BBox): boolean {
  return inner[0] >= outer[0] && inner[1] >= outer[1] && inner[2] <= outer[2] && inner[3] <= outer[3];
}

export function bboxOverlaps(a: BBox, b: BBox): boolean {
  return a[0] <= b[2] && a[2] >= b[0] && a[1] <= b[3] && a[3] >= b[1];
}

export function bboxInFlorida(bbox: BBox | null | undefined): boolean {
  if (!bbox || bbox.length !== 4) return false;
  if (bbox.some((value) => !Number.isFinite(value))) return false;
  if (bbox[0] >= bbox[2] || bbox[1] >= bbox[3]) return false;
  return bboxInside(bbox, FLORIDA_BBOX);
}

export function overlayCityUsable(city: Pick<MunicipalCityIndex, "status" | "bbox">): boolean {
  return city.status === "active" && bboxInFlorida(city.bbox) && bboxOverlaps(city.bbox as BBox, ORANGE_FL_BBOX);
}

export function parcelIdAliases(parcelId: string | null | undefined): string[] {
  if (!parcelId?.trim()) return [];
  let raw = parcelId.trim().toUpperCase();
  if (raw.includes(":")) raw = raw.split(":").pop() ?? raw;
  const bare = raw.startsWith("12095-") ? raw.slice("12095-".length) : raw;
  const keys: string[] = [];
  for (const key of [bare, `12095-${bare}`]) {
    if (key && !keys.includes(key)) keys.push(key);
  }
  return keys;
}

/** County or joint-planning placeholders. They are not city district codes. */
const NON_CITY_ZONING = new Set(["CITY", "OUT", "UNC", "UNINCORPORATED"]);

export function municipalZoningCode(prefix: string, raw: string | null | undefined): string | null {
  if (!raw?.trim()) return null;
  const code = raw.trim().toUpperCase();
  if (!code || NON_CITY_ZONING.has(code)) return null;
  const head = prefix.toUpperCase();
  return code.startsWith(`${head}-`) ? code : `${head}-${code}`;
}

function clean(value: string | null | undefined): string | null {
  const text = value?.trim();
  return text ? text : null;
}

function ringArea(ring: number[][]): number {
  let area = 0;
  for (let i = 0; i < ring.length - 1; i += 1) {
    area += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
  }
  return Math.abs(area / 2);
}

function polygonArea(polygons: number[][][][]): number {
  return polygons.reduce((sum, rings) => sum + (rings[0] ? ringArea(rings[0]) : 0), 0);
}

function pointInPolygons(x: number, y: number, polygons: number[][][][]): boolean {
  for (const rings of polygons) {
    if (!rings.length || !pointInRing(x, y, rings[0])) continue;
    if (rings.slice(1).every((hole) => !pointInRing(x, y, hole))) return true;
  }
  return false;
}

function attributeFromCompact(raw: CompactAttr | undefined): MunicipalAttribute | null {
  if (!raw) return null;
  return {
    zoningCode: clean(raw.z),
    zoningLabel: clean(raw.zl),
    fluCode: clean(raw.f),
    fluLabel: clean(raw.fl),
  };
}

export function cityIndexFromFixture(raw: CompactCity): MunicipalCityIndex {
  const attributes = new Map<string, MunicipalAttribute>();
  for (const [key, value] of Object.entries(raw.attributes ?? {})) {
    const attr = attributeFromCompact(value);
    if (attr) attributes.set(key.toUpperCase(), attr);
  }
  const spatial: MunicipalSpatialFeature[] = [];
  for (const item of raw.spatial ?? []) {
    const bbox = item.b;
    const polygons = item.g;
    if (!bbox || bbox.length !== 4 || !polygons?.length) continue;
    const box = bbox as BBox;
    if (!bboxInFlorida(box)) continue;
    const attr = attributeFromCompact(item) ?? {
      zoningCode: null,
      zoningLabel: null,
      fluCode: null,
      fluLabel: null,
    };
    spatial.push({
      ...attr,
      bbox: box,
      polygons,
      parcelId: clean(item.id),
      area: polygonArea(polygons),
    });
  }
  const bbox = raw.bbox && raw.bbox.length === 4 ? (raw.bbox as BBox) : null;
  return {
    id: raw.id,
    name: raw.name,
    prefix: raw.prefix,
    status: raw.status === "gap" ? "gap" : "active",
    bbox,
    attributes,
    spatial,
  };
}

function firstText(...values: Array<string | null | undefined>): string | null {
  for (const value of values) {
    const text = clean(value);
    if (text && !NON_CITY_ZONING.has(text.toUpperCase())) return text;
  }
  return null;
}

function isNonCityZoning(code: string | null | undefined): boolean {
  return Boolean(code && NON_CITY_ZONING.has(code.toUpperCase()));
}

/**
 * An attribute row is a city match even when the district and FLU are blank.
 * A blank district clears county zoning instead of leaving it on screen.
 * CITY / OUT / UNC placeholders are not a city district, even when a FLU code is present.
 */
function claimsCity(attr: MunicipalAttribute | null, spatial: { zoningCode: string | null; fluCode: string | null } | null): boolean {
  if (attr) return !isNonCityZoning(attr.zoningCode);
  if (!spatial || isNonCityZoning(spatial.zoningCode)) return false;
  return Boolean(spatial.zoningCode || spatial.fluCode);
}

function spatialAt(city: MunicipalCityIndex, x: number, y: number): {
  zoningCode: string | null;
  zoningLabel: string | null;
  fluCode: string | null;
  fluLabel: string | null;
  area: number;
} | null {
  if (!city.bbox || x < city.bbox[0] || x > city.bbox[2] || y < city.bbox[1] || y > city.bbox[3]) return null;
  let zoning: MunicipalSpatialFeature | null = null;
  let flu: MunicipalSpatialFeature | null = null;
  let container: MunicipalSpatialFeature | null = null;
  for (const feature of city.spatial) {
    const [west, south, east, north] = feature.bbox;
    if (x < west || x > east || y < south || y > north) continue;
    if (!pointInPolygons(x, y, feature.polygons)) continue;
    if (!container || feature.area < container.area) container = feature;
    if (feature.zoningCode && (!zoning || feature.area < zoning.area)) zoning = feature;
    if (feature.fluCode && (!flu || feature.area < flu.area)) flu = feature;
  }
  if (!container && !zoning && !flu) return null;
  const area = Math.min(zoning?.area ?? Number.POSITIVE_INFINITY, flu?.area ?? container?.area ?? Number.POSITIVE_INFINITY);
  return {
    zoningCode: zoning?.zoningCode ?? null,
    zoningLabel: zoning?.zoningLabel ?? null,
    fluCode: flu?.fluCode ?? null,
    fluLabel: flu?.fluLabel ?? null,
    area: Number.isFinite(area) ? area : 0,
  };
}

function hitForCity(feature: ParcelFeature, city: MunicipalCityIndex): MunicipalHit | null {
  if (!overlayCityUsable(city)) return null;
  let attr: MunicipalAttribute | null = null;
  for (const key of parcelIdAliases(feature.properties.parcelId)) {
    const found = city.attributes.get(key);
    if (found) {
      attr = found;
      break;
    }
  }
  const [lon, lat] = feature.properties.centroid ?? [];
  const spatial = Number.isFinite(lon) && Number.isFinite(lat) ? spatialAt(city, lon, lat) : null;
  if (!claimsCity(attr, spatial)) return null;
  return {
    id: city.id,
    name: city.name,
    prefix: city.prefix,
    join: attr ? "attribute" : "spatial",
    zoningCode: firstText(attr?.zoningCode, spatial?.zoningCode),
    zoningLabel: firstText(attr?.zoningLabel, spatial?.zoningLabel),
    fluCode: firstText(attr?.fluCode, spatial?.fluCode),
    fluLabel: firstText(attr?.fluLabel, spatial?.fluLabel),
    area: spatial?.area ?? 0,
  };
}

export function findMunicipalHit(feature: ParcelFeature, index: MunicipalOverlayIndex): MunicipalHit | null {
  const hits: MunicipalHit[] = [];
  for (const city of index.cities) {
    const hit = hitForCity(feature, city);
    if (hit) hits.push(hit);
  }
  hits.sort((a, b) => {
    if (a.join !== b.join) return a.join === "attribute" ? -1 : 1;
    const aScore = a.zoningCode || a.fluCode ? 0 : 1;
    const bScore = b.zoningCode || b.fluCode ? 0 : 1;
    if (aScore !== bScore) return aScore - bScore;
    return a.area - b.area;
  });
  return hits[0] ?? null;
}

function isOrangeParcel(properties: ParcelProperties): boolean {
  if (properties.countyFips) return properties.countyFips === "12095";
  return (properties.countyName ?? "").toLowerCase() === "orange";
}

export function applyMunicipalOverlay(feature: ParcelFeature, index: MunicipalOverlayIndex): ParcelFeature {
  if (feature.properties.municipalOverlay || !isOrangeParcel(feature.properties)) return feature;
  const hit = findMunicipalHit(feature, index);
  if (!hit) return feature;
  const countyZoningCode = feature.properties.zoningCode;
  const zoningCode = municipalZoningCode(hit.prefix, hit.zoningCode);
  const district = zoningCode ? zoningCode.slice(hit.prefix.length + 1).split("/")[0] || null : null;
  const flu: FluInfo = {
    code: hit.fluCode,
    label: hit.fluLabel || hit.fluCode,
    jurisdiction: hit.prefix,
    jurisdictionName: hit.name,
    source: `municipal-overlay:${hit.id}:${hit.join}`,
  };
  return {
    ...feature,
    properties: {
      ...feature.properties,
      zoningCode,
      zoningDistrict: district,
      zoningLabel: hit.zoningLabel,
      zoningAuthority: hit.name,
      zoningSource: `municipal-overlay:${hit.id}:${hit.join}`,
      jurisdictionPrefix: hit.prefix,
      jurisdictionCode: hit.prefix,
      countyZoningCode,
      flu,
      municipalOverlay: {
        id: hit.id,
        name: hit.name,
        join: hit.join,
        coverage: "city-only",
      },
    },
  };
}

export const EMPTY_MUNICIPAL_INDEX: MunicipalOverlayIndex = { cities: [] };
