/**
 * Volusia and Flagler city zoning / future land use overlay rules.
 * The catalog in data/volusia-flagler-municipal.json is the source list.
 * Codes are copied from those layers. Nothing here invents a district, a
 * future land use category, or an Opportunity Zone.
 */

export type MunicipalLayer = {
  url: string;
  fields: string[];
  labelFields?: string[];
  /** Holly Hill parcel id join. Used only when the parcel id matches. */
  attributeUrl?: string;
  idFields?: string[];
};

export type MunicipalPlace = {
  id: string;
  name: string;
  county: "Volusia" | "Flagler";
  countyFips: "12127" | "12035";
  kind: "city" | "unincorporated";
  status: "usable" | "partial";
  rank: number;
  prefix: string;
  join: "spatial" | "attribute-then-spatial" | "countywide";
  notes?: string;
  countywideJurisd?: string;
  countywideFallback?: string;
  zoning: MunicipalLayer | null;
  flu: MunicipalLayer | null;
  fluGap?: string;
};

export type MunicipalCatalog = {
  version: number;
  doNotInventOpportunityZones: boolean;
  stubZoningCodes: string[];
  flaglerHost: { host: string; note: string };
  countywideZoning: {
    url: string;
    fields: string[];
    labelFields?: string[];
    filterField: string;
    vintage?: string;
    note: string;
  };
  rejected: { id: string; url: string; reason: string }[];
  avoid: { id: string; url: string; reason: string }[];
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

const WIRE_READY_IDS = [
  "daytona-beach",
  "port-orange",
  "ormond-beach",
  "deltona",
  "deland",
  "edgewater",
  "south-daytona",
  "holly-hill",
  "oak-hill",
  "ponce-inlet",
  "palm-coast",
  "flagler-beach",
  "bunnell",
  "marineland",
] as const;

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
  const blocked = [...catalog.rejected, ...catalog.avoid];
  return blocked.some((item) => {
    const banned = normalizeServiceUrl(item.url).toLowerCase();
    return normalized === banned || normalized.startsWith(`${banned}/`);
  });
}

export function isStubZoningCode(catalog: MunicipalCatalog, code: string | null | undefined): boolean {
  if (!code?.trim()) return false;
  const text = code.trim();
  return catalog.stubZoningCodes.some((stub) => stub.trim() === text);
}

export function readOverlayValue(
  catalog: MunicipalCatalog,
  attrs: Record<string, unknown> | null | undefined,
  fields: string[],
  labelFields: string[] = [],
): OverlayValue | null {
  if (!attrs) return null;
  let code: string | null = null;
  for (const field of fields) {
    const text = cleanOverlayText(attrs[field]);
    if (!text || isStubZoningCode(catalog, text)) continue;
    code = text;
    break;
  }
  if (!code) return null;
  let label: string | null = null;
  for (const field of labelFields) {
    const text = cleanOverlayText(attrs[field]);
    if (!text || isStubZoningCode(catalog, text)) continue;
    label = text;
    break;
  }
  if (label === code) label = null;
  return { code, label };
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

/** Smaller polygon wins. Rank breaks ties. Countywide is not in this list. */
export function mostLocalHit(hits: OverlayHit[]): OverlayHit | null {
  if (hits.length === 0) return null;
  return [...hits].sort((a, b) => {
    if (a.areaSqM !== b.areaSqM) return a.areaSqM - b.areaSqM;
    return a.rank - b.rank;
  })[0];
}

/**
 * City REST wins over unincorporated and over CountywideZoning.
 * A Holly Hill PID/ALTKEY match wins over a spatial zoning hit.
 */
export function resolveZoningHit(input: {
  attributeHit: OverlayHit | null;
  cityHits: OverlayHit[];
  unincorporatedHit: OverlayHit | null;
  countywideHit: OverlayHit | null;
}): OverlayHit | null {
  if (input.attributeHit) return input.attributeHit;
  const city = mostLocalHit(input.cityHits);
  if (city) return city;
  if (input.unincorporatedHit) return input.unincorporatedHit;
  return input.countywideHit;
}

export function placeForCountywideJurisd(catalog: MunicipalCatalog, jurisd: string | null | undefined): MunicipalPlace | null {
  const name = jurisd?.trim();
  if (!name) return null;
  return (
    catalog.places.find((place) => place.countywideJurisd === name || place.countywideFallback === name) ?? null
  );
}

/**
 * Future land use stays on the city that supplied zoning when that city has
 * a gap or its own FLU layer. A missing city FLU is not filled from a neighbor
 * or from a county dump.
 */
export function resolveFluHit(
  catalog: MunicipalCatalog,
  zoningPlaceId: string | null,
  fluHits: OverlayHit[],
): OverlayHit | null {
  if (!zoningPlaceId) return mostLocalHit(fluHits);
  const place = placeById(catalog, zoningPlaceId);
  if (!place || place.fluGap || !place.flu) return null;
  return fluHits.find((hit) => hit.placeId === place.id) ?? null;
}

export function hollyHillAttributeKeys(parcelId: string | null | undefined): string[] {
  const raw = parcelId?.trim();
  if (!raw) return [];
  const keys = new Set<string>([raw]);
  const stripped = raw.replace(/^0+/, "");
  if (stripped) keys.add(stripped);
  return [...keys];
}

export function zoningEmptyForCounty(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips === "12127" || countyFips === "12035") {
    return "No municipal zoning polygon covers this parcel.";
  }
  return fallback;
}

export function fluEmptyForMunicipal(fluGap: string | null | undefined): string {
  return fluGap?.trim() || "Not joined for this county";
}

export function layerUrls(place: MunicipalPlace): string[] {
  const urls: string[] = [];
  if (place.zoning?.url) urls.push(place.zoning.url);
  if (place.zoning?.attributeUrl) urls.push(place.zoning.attributeUrl);
  if (place.flu?.url) urls.push(place.flu.url);
  return urls;
}
