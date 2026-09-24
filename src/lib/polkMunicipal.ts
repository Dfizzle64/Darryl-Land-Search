/**
 * Polk County, Florida city zoning and future land use.
 * The catalog in data/polk-municipal.json is the source list.
 * Codes are copied from those layers. Nothing here invents a district,
 * a county LDC zoning polygon, or an Opportunity Zone.
 */

export type PolkLayer = {
  url: string;
  fields: string[];
  labelFields?: string[];
};

export type PolkPlace = {
  id: string;
  name: string;
  countyFips: "12105";
  status: "usable";
  rank: number;
  prefix: string;
  join: "spatial" | "attribute-then-spatial";
  idField?: string;
  notes?: string;
  notWired?: { url: string; reason: string }[];
  zoning: PolkLayer;
  flu: PolkLayer;
};

export type PolkGap = {
  id: string;
  name: string;
  status: "gap" | "blocked";
  reason: string;
};

export type PolkCatalog = {
  version: number;
  county: "Polk";
  countyFips: "12105";
  doNotInventOpportunityZones: boolean;
  doNotInventCountyLdcZoning: boolean;
  stubCodes: string[];
  bbox: [number, number, number, number];
  countyLdcZoning: { status: "gap"; note: string };
  countyFluNotStamped: { url: string; reason: string };
  rejected: { id: string; name: string; url: string; reason: string }[];
  gaps: PolkGap[];
  places: PolkPlace[];
};

export type PolkOverlayValue = {
  code: string;
  label: string | null;
};

export type PolkOverlayHit = {
  placeId: string;
  areaSqM: number;
  rank: number;
  code: string;
  label: string | null;
  layerUrl: string;
};

const WIRE_READY_IDS = ["lakeland", "bartow", "auburndale", "lake-alfred", "lake-hamilton"] as const;

export const POLK_ZONING_EMPTY =
  "No Lakeland, Bartow, Auburndale, Lake Alfred, or Lake Hamilton zoning covers this parcel. Polk County does not publish an LDC zoning-district layer.";

export const POLK_FLU_EMPTY =
  "No city future land use covers this parcel. County future land use is not copied in as a zoning code.";

export function wireReadyPlaces(catalog: PolkCatalog): PolkPlace[] {
  const byId = new Map(catalog.places.map((place) => [place.id, place]));
  return WIRE_READY_IDS.map((id) => {
    const place = byId.get(id);
    if (!place) throw new Error(`Catalog is missing wire-ready place ${id}`);
    return place;
  });
}

export function normalizeServiceUrl(url: string): string {
  return url.trim().replace(/\/+$/, "").replace(/\/query$/, "");
}

export function isBlockedServiceUrl(catalog: PolkCatalog, url: string): boolean {
  const normalized = normalizeServiceUrl(url).toLowerCase();
  return catalog.rejected.some((item) => {
    const banned = normalizeServiceUrl(item.url).toLowerCase();
    if (banned.startsWith("http")) {
      return normalized === banned || normalized.startsWith(`${banned}/`);
    }
    return normalized.includes(banned);
  });
}

export function isStubCode(catalog: PolkCatalog, code: string | null | undefined): boolean {
  if (!code?.trim()) return false;
  return catalog.stubCodes.some((stub) => stub.trim().toLowerCase() === code.trim().toLowerCase());
}

/** Polk parcel ids on the shelf are long digit strings. Short Auburndale stubs are not. */
export function isPolkParcelKey(value: string | null | undefined): boolean {
  const text = value?.trim() ?? "";
  return /^\d{15,}$/.test(text);
}

export function cleanOverlayText(value: unknown): string | null {
  if (value == null || typeof value === "boolean") return null;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return null;
    return rejectBlank(Number.isInteger(value) ? String(value) : String(value));
  }
  if (typeof value === "string") return rejectBlank(value);
  return null;
}

function rejectBlank(value: string): string | null {
  const text = value.trim();
  if (!text) return null;
  const lower = text.toLowerCase();
  if (lower === "null" || lower === "none" || lower === "nan") return null;
  return text;
}

export function readOverlayValue(
  catalog: PolkCatalog,
  attrs: Record<string, unknown> | null | undefined,
  fields: string[],
  labelFields: string[] = [],
): PolkOverlayValue | null {
  if (!attrs) return null;
  let code: string | null = null;
  for (const field of fields) {
    const text = cleanOverlayText(attrs[field]);
    if (!text || isStubCode(catalog, text)) continue;
    code = text;
    break;
  }
  if (!code) return null;
  let label: string | null = null;
  for (const field of labelFields) {
    const text = cleanOverlayText(attrs[field]);
    if (!text || isStubCode(catalog, text)) continue;
    label = text;
    break;
  }
  if (label === code) label = null;
  return { code, label };
}

/** Smaller polygon wins. Rank breaks ties. */
export function mostLocalHit(hits: PolkOverlayHit[]): PolkOverlayHit | null {
  if (hits.length === 0) return null;
  return [...hits].sort((a, b) => {
    if (a.areaSqM !== b.areaSqM) return a.areaSqM - b.areaSqM;
    return a.rank - b.rank;
  })[0];
}

/** A Polk parcel-id match wins over a centroid hit. */
export function resolvePolkHit(attributeHit: PolkOverlayHit | null, spatialHits: PolkOverlayHit[]): PolkOverlayHit | null {
  if (attributeHit) return attributeHit;
  return mostLocalHit(spatialHits);
}

/**
 * Future land use stays on the city that supplied zoning.
 * A neighbor city's FLU is not used to fill a miss, and county FLU is not in this list.
 */
export function resolvePolkFlu(
  zoningPlaceId: string | null,
  attributeHit: PolkOverlayHit | null,
  spatialHits: PolkOverlayHit[],
): PolkOverlayHit | null {
  const scopedAttr = zoningPlaceId && attributeHit?.placeId !== zoningPlaceId ? null : attributeHit;
  const scopedSpatial = zoningPlaceId ? spatialHits.filter((hit) => hit.placeId === zoningPlaceId) : spatialHits;
  return resolvePolkHit(scopedAttr, scopedSpatial);
}

export function zoningEmptyForPolk(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips === "12105") return POLK_ZONING_EMPTY;
  return fallback;
}

export function fluEmptyForPolk(
  countyFips: string | null | undefined,
  fluGap: string | null | undefined,
  fallback: string,
): string {
  if (fluGap?.trim()) return fluGap;
  if (countyFips === "12105") return POLK_FLU_EMPTY;
  return fallback;
}

export function layerUrls(place: PolkPlace): string[] {
  return [...new Set([place.zoning.url, place.flu.url])];
}
