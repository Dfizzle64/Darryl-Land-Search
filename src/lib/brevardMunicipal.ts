/**
 * Brevard County city zoning and future land use.
 * data/brevard-municipal.json is the source list. Codes are copied from those
 * layers. Nothing here invents a district, a future land use category, a
 * school grade, a base flood elevation, or an Opportunity Zone.
 */

import type { MunicipalOverlayNote } from "./types";

export type MunicipalLayer = {
  url: string;
  fields: string[];
  labelFields?: string[];
  idFields?: string[];
  where?: string;
  alreadyCarded?: boolean;
};

export type MunicipalPlace = {
  id: string;
  name: string;
  county: "Brevard";
  countyFips: "12009";
  kind: "city";
  status: "usable" | "partial";
  rank: number;
  prefix: string;
  join: "spatial" | "attribute-then-spatial";
  newThisPass?: boolean;
  fluClose?: boolean;
  unofficial?: boolean;
  vintage?: string;
  notes?: string;
  fluGap?: string;
  zoning: MunicipalLayer | null;
  flu: MunicipalLayer | null;
};

export type SkippedPlace = {
  id: string;
  name: string;
  reason: string;
  hint?: string;
};

export type GapPlace = {
  id: string;
  name: string;
  reason: string;
};

export type MunicipalCatalog = {
  version: number;
  doNotInventOpportunityZones: boolean;
  doNotInventSchoolGrades: boolean;
  doNotInventBaseFloodElevations: boolean;
  brevardBbox: [number, number, number, number];
  namesakes: { id: string; reason: string }[];
  rejected: { id: string; url: string; reason: string }[];
  skippedAlreadyCarded: SkippedPlace[];
  gaps: GapPlace[];
  places: MunicipalPlace[];
};

export type OverlayValue = {
  code: string;
  label: string | null;
};

export type OverlayHit = {
  placeId: string;
  kind: MunicipalPlace["kind"];
  status: MunicipalPlace["status"];
  areaSqM: number;
  rank: number;
  code: string;
  label: string | null;
  layerUrl: string;
};

const WIRE_READY_IDS = ["melbourne", "west-melbourne", "rockledge", "satellite-beach", "cocoa"] as const;

export function wireReadyPlaces(catalog: MunicipalCatalog): MunicipalPlace[] {
  const byId = new Map(catalog.places.map((place) => [place.id, place]));
  return WIRE_READY_IDS.map((id) => {
    const place = byId.get(id);
    if (!place) throw new Error(`Catalog is missing wire-ready place ${id}`);
    return place;
  });
}

export function partialPlaces(catalog: MunicipalCatalog): MunicipalPlace[] {
  return catalog.places.filter((place) => place.status === "partial");
}

export function placeById(catalog: MunicipalCatalog, id: string): MunicipalPlace | null {
  return catalog.places.find((place) => place.id === id) ?? null;
}

export function normalizeServiceUrl(url: string): string {
  return url.trim().replace(/\/+$/, "").replace(/\/query$/, "");
}

export function isBlockedServiceUrl(catalog: MunicipalCatalog, url: string): boolean {
  const normalized = normalizeServiceUrl(url).toLowerCase();
  return catalog.rejected.some((item) => {
    const banned = normalizeServiceUrl(item.url).toLowerCase();
    return normalized === banned || normalized.startsWith(`${banned}/`);
  });
}

export function centroidInBrevard(catalog: MunicipalCatalog, lon: number, lat: number): boolean {
  const [west, south, east, north] = catalog.brevardBbox;
  return lon >= west && lon <= east && lat >= south && lat <= north;
}

export function cleanOverlayText(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return null;
    const text = Number.isInteger(value) ? String(value) : String(value);
    return rejectBlank(text);
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
  attrs: Record<string, unknown> | null | undefined,
  fields: string[],
  labelFields: string[] = [],
): OverlayValue | null {
  if (!attrs) return null;
  let code: string | null = null;
  for (const field of fields) {
    const text = cleanOverlayText(attrs[field]);
    if (!text) continue;
    code = text;
    break;
  }
  if (!code) return null;
  let label: string | null = null;
  for (const field of labelFields) {
    const text = cleanOverlayText(attrs[field]);
    if (!text) continue;
    label = text;
    break;
  }
  if (label === code) label = null;
  return { code, label };
}

/** Keys shared by a parcel id and a city TaxAcct, PID, RENUM, or Name. */
export function parcelAttributeKeys(value: string | number | null | undefined): string[] {
  const text = cleanOverlayText(value);
  if (!text) return [];
  const upper = text.toUpperCase();
  const keys = [upper, upper.replace(/\s+/g, " ")];
  const alnum = upper.replace(/[^A-Z0-9]/g, "");
  if (alnum) keys.push(alnum);
  const digits = upper.replace(/\D/g, "");
  if (digits.length >= 5) {
    keys.push(digits);
    const stripped = digits.replace(/^0+/, "");
    if (stripped) keys.push(stripped);
  }
  return [...new Set(keys)];
}

/** Smaller polygon wins. Rank breaks ties. */
export function mostLocalHit(hits: OverlayHit[]): OverlayHit | null {
  if (hits.length === 0) return null;
  return [...hits].sort((a, b) => {
    if (a.areaSqM !== b.areaSqM) return a.areaSqM - b.areaSqM;
    return a.rank - b.rank;
  })[0];
}

/**
 * A TaxAcct / PID / RENUM match wins over a centroid hit.
 * County zoning is never a candidate.
 */
export function resolveZoningHit(input: {
  attributeHit: OverlayHit | null;
  cityHits: OverlayHit[];
}): OverlayHit | null {
  if (input.attributeHit) return input.attributeHit;
  return mostLocalHit(input.cityHits);
}

/**
 * Future land use stays on the city that supplied zoning when that city has
 * a gap or its own FLU layer. A missing city FLU is not filled from a neighbor
 * or from county FLU.
 */
export function resolveFluHit(
  catalog: MunicipalCatalog,
  zoningPlaceId: string | null,
  fluHits: OverlayHit[],
  attributeHit: OverlayHit | null = null,
): OverlayHit | null {
  if (zoningPlaceId) {
    const place = placeById(catalog, zoningPlaceId);
    if (!place || place.fluGap || !place.flu) return null;
    if (attributeHit?.placeId === place.id) return attributeHit;
    return mostLocalHit(fluHits.filter((hit) => hit.placeId === place.id));
  }
  const usable = fluHits.filter((hit) => {
    const place = placeById(catalog, hit.placeId);
    return Boolean(place && !place.fluGap && place.flu);
  });
  if (attributeHit) {
    const place = placeById(catalog, attributeHit.placeId);
    if (place && !place.fluGap && place.flu) return attributeHit;
  }
  return mostLocalHit(usable);
}

export function layerUrls(place: MunicipalPlace): string[] {
  const urls: string[] = [];
  if (place.zoning?.url) urls.push(place.zoning.url);
  if (place.flu?.url) urls.push(place.flu.url);
  return urls;
}

export function formatJoinedZoning(
  code: string | null | undefined,
  municipal: Pick<MunicipalOverlayNote, "placeName" | "unofficial" | "vintage"> | null | undefined,
): string | null {
  if (!code?.trim()) return null;
  if (!municipal?.placeName) return code.trim();
  const unofficial = municipal.unofficial ? ` · unofficial ${municipal.vintage?.trim() || "vintage"}` : "";
  return `${code.trim()} · ${municipal.placeName}${unofficial}`;
}

export function brevardFluEmpty(fluGap: string | null | undefined): string {
  return fluGap?.trim() || "No city future land use covers this parcel. County FLU is not used inside these cities.";
}

export function brevardFluReason(
  baseReason: string,
  fluCode: string | null | undefined,
  municipal: Pick<MunicipalOverlayNote, "fluGap" | "unofficial" | "vintage"> | null | undefined,
  countyFips: string | null | undefined,
): string {
  if (countyFips !== "12009") return baseReason;
  if (!fluCode) return brevardFluEmpty(municipal?.fluGap);
  if (municipal?.unofficial) {
    return `${baseReason} The city layer is unofficial (${municipal.vintage?.trim() || "undated"}).`;
  }
  return baseReason;
}
