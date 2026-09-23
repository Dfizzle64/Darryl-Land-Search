import type { BBox, FluInfo, LastSale, MailingAddress, ParcelProperties, TaxInfo } from "./types";

/** Knox County, Tennessee. Not a Comptroller IMPACT county. */
export const KNOX_FIPS = "47093";

/** Tokenless countywide parcels. Direct kgis.org/arcgis GlobalSearch stays 401. */
export const KNOX_PARCEL_QUERY_URL =
  "https://www.kgis.org/gisportal/sharing/servers/871856067a1243bd899774b2072381c5/rest/services/Parcel_Search_Layer/MapServer/0/query";

export const KNOX_PROPERTY_PARCEL_QUERY_URL =
  "https://www.kgis.org/arcgis/rest/services/Maps/Property/MapServer/2/query";

export const KNOX_ZONING_QUERY_URL =
  "https://services1.arcgis.com/QWaOgwdmpqI9HUzf/arcgis/rest/services/KnoxvilleKnoxCountyZoning/FeatureServer/2/query";

export const KNOX_COUNTY_FLU_QUERY_URL =
  "https://services1.arcgis.com/QWaOgwdmpqI9HUzf/arcgis/rest/services/Knox_County_Future_Land_Use/FeatureServer/326/query";

export const FARRAGUT_ZONING_QUERY_URL =
  "https://services6.arcgis.com/Ff4u1o0TAdiPJay7/arcgis/rest/services/Farragut_Zoning/FeatureServer/1/query";

export const KNOX_APPRAISER_SEARCH_URL =
  "https://propertyinfo.knoxcountytn.gov/search/CommonSearch.aspx?mode=parid";

export const KNOX_ACREAGE = { min: 5, max: 150 } as const;

/**
 * Shown on the Knoxville market. Parcels are the 5–150 calculated-acre band.
 * City and Farragut future land use stay null.
 */
export const KNOX_PARCEL_NOTE =
  "Knox County parcels are the public KGIS Parcel Search layer, calculated acres 5.0 through 150.0. Direct kgis.org/arcgis parcel MapServers stay 401 and are not used. Comptroller IMPACT is not used. City of Knoxville and Farragut future land use stay null; unincorporated parcels use Advance Knox place types.";

export type KnoxMunicipalityId = "knoxville" | "farragut" | "unincorporated";

export const KNOX_MUNICIPALITY_NAME: Record<KnoxMunicipalityId, string> = {
  knoxville: "City of Knoxville",
  farragut: "Town of Farragut",
  unincorporated: "Unincorporated Knox County",
};

export const KNOX_CITY_FLU_GAP =
  "City of Knoxville future land use (PRLU) and the One Year Plan are not available to anonymous query. FLU stays null inside the city.";

export const FARRAGUT_FLU_GAP =
  "Town of Farragut has no public future-land-use FeatureServer. FLU stays null.";

type Ring = number[][];
type PolygonCoords = Ring[];
type MultiPolygonCoords = PolygonCoords[];

export type KnoxPolygonGeometry = {
  type: "Polygon" | "MultiPolygon";
  coordinates: PolygonCoords | MultiPolygonCoords;
};

export type KnoxZoningProperties = {
  zone1: string | null;
  zone2: string | null;
  zoningCode: string | null;
  zoneType: "City of Knoxville" | "Knox County" | string | null;
  areaAcres: number | null;
  source: string;
};

export type KnoxFluProperties = {
  placeType: string | null;
  gppCompatibility: string | null;
  source: string;
};

export type FarragutZoningProperties = {
  zone: string | null;
  type: string | null;
  codeUrl: string | null;
  acres: number | null;
  source: string;
};

export type KnoxBoundaryProperties = {
  municipality: "knoxville" | "farragut";
  name: string;
  source: string;
};

export type KnoxOverlayFeature<P> = {
  type: "Feature";
  properties: P;
  geometry: KnoxPolygonGeometry;
};

export type KnoxOverlayIndex<P> = {
  cell: number;
  buckets: Map<string, KnoxOverlayFeature<P>[]>;
};

function clean(value: unknown): string | null {
  if (value == null) return null;
  const text = String(value).trim();
  return text || null;
}

function num(value: unknown): number | null {
  if (value == null || value === "") return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function joinParts(parts: unknown[]): string | null {
  const texts = parts.map(clean).filter((part): part is string => Boolean(part));
  return texts.length ? texts.join(" ") : null;
}

export function knoxAppraiserUrl(parcelId: string | null | undefined): string {
  const id = parcelId?.trim() ?? "";
  if (!id) return KNOX_APPRAISER_SEARCH_URL;
  return `https://propertyinfo.knoxcountytn.gov/Datalets/Datalet.aspx?ParcelID=${encodeURIComponent(id)}&UseSearch=yes`;
}

/** Prefer ZONE1 and append a non-empty ZONE2. Farragut uses a single ZONE field. */
export function knoxZoningCode(zone1: unknown, zone2?: unknown): string | null {
  const primary = clean(zone1);
  const secondary = clean(zone2);
  if (primary && secondary && secondary !== primary) {
    if (secondary.startsWith("/") || secondary.startsWith("-")) return `${primary}${secondary}`;
    return `${primary} ${secondary}`;
  }
  return primary || secondary;
}

/**
 * Site-search acreage. CALCULATED_AREA is the filter field when it is present,
 * including when it falls outside 5–150. RECORDED_AREA is used only when calculated acres are missing.
 */
export function knoxAcreage(attrs: Record<string, unknown>): {
  acres: number | null;
  field: "CALCULATED_AREA" | "RECORDED_AREA" | null;
  inBand: boolean;
} {
  const calculated = num(attrs.CALCULATED_AREA);
  if (calculated != null) {
    return {
      acres: calculated,
      field: "CALCULATED_AREA",
      inBand: calculated >= KNOX_ACREAGE.min && calculated <= KNOX_ACREAGE.max,
    };
  }
  const recorded = num(attrs.RECORDED_AREA);
  if (recorded != null) {
    return {
      acres: recorded,
      field: "RECORDED_AREA",
      inBand: recorded >= KNOX_ACREAGE.min && recorded <= KNOX_ACREAGE.max,
    };
  }
  return { acres: null, field: null, inBand: false };
}

export function knoxDate(value: unknown): string | null {
  if (value == null || value === "") return null;
  if (typeof value === "number" && Number.isFinite(value)) {
    const ms = Math.abs(value) >= 1e11 ? value : Math.abs(value) > 1e9 ? value * 1000 : null;
    if (ms == null) return null;
    const date = new Date(ms);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString().slice(0, 10);
  }
  const text = String(value).trim();
  if (!text) return null;
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10);
  const parsed = Date.parse(text);
  if (!Number.isNaN(parsed)) return new Date(parsed).toISOString().slice(0, 10);
  return text;
}

function zipWithSuffix(zip: unknown, suffix: unknown): string | null {
  const base = clean(zip);
  if (!base) return null;
  const extra = clean(suffix);
  if (!extra || base.includes("-")) return base;
  return `${base}-${extra}`;
}

function parseCityStateZip(value: string | null): { city: string | null; state: string | null; zip: string | null } {
  if (!value) return { city: null, state: null, zip: null };
  const match = value.match(/^(.*?)(?:,)?\s+([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)$/);
  if (!match) return { city: value, state: null, zip: null };
  return {
    city: match[1].replace(/,$/, "").trim() || null,
    state: match[2].toUpperCase(),
    zip: match[3],
  };
}

export function knoxMailing(attrs: Record<string, unknown>): MailingAddress {
  const full = clean(attrs.FULL_MAIL_ADDRESS);
  const extra = clean(attrs.FULL_MAIL_ADDRESS_EXTRA);
  const street =
    full ??
    joinParts([attrs.MAIL_HOUSE_NUMBER, attrs.MAIL_UNIT, attrs.MAIL_STREET_NAME, attrs.MAIL_STREET_EXTRA]);
  const line2 = [extra && extra !== full ? extra : null, clean(attrs.MAIL_ATTENTION)]
    .filter((part): part is string => Boolean(part))
    .join(", ");
  let city = clean(attrs.MAIL_CITY);
  let state = clean(attrs.MAIL_STATE);
  let zip = zipWithSuffix(attrs.MAIL_ZIP_CODE, attrs.MAIL_ZIP_CODE_SUF);
  if (!city || !state || !zip) {
    const parsed = parseCityStateZip(clean(attrs.FULL_MAIL_CITY_STATE_ZIP));
    city = city ?? parsed.city;
    state = state ?? parsed.state;
    zip = zip ?? parsed.zip;
  }
  return {
    line1: street,
    line2: line2 || null,
    city,
    state,
    zip,
  };
}

export function knoxSitus(attrs: Record<string, unknown>): string | null {
  return (
    clean(attrs.FULL_ADDRESS) ??
    joinParts([
      attrs.LOC_HOUSE_NUMBER,
      attrs.LOC_HOUSE_NUM_SUF,
      attrs.LOC_STREET_PREFIX,
      attrs.LOC_STREET_NAME,
      attrs.LOC_STREET_TYPE,
      attrs.LOC_STREET_SUFFIX,
      clean(attrs.LOC_UNIT) ? `Unit ${clean(attrs.LOC_UNIT)}` : null,
    ])
  );
}

function money(value: unknown): number | null {
  return num(value);
}

function salePrice(value: unknown): number | null {
  const parsed = num(value);
  if (parsed == null || parsed <= 0) return null;
  return parsed;
}

export function pointInRing(lon: number, lat: number, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i]?.[0];
    const yi = ring[i]?.[1];
    const xj = ring[j]?.[0];
    const yj = ring[j]?.[1];
    if (xi == null || yi == null || xj == null || yj == null) continue;
    const intersect = yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi + 0.0) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function pointInPolygonCoords(lon: number, lat: number, coordinates: PolygonCoords): boolean {
  const outer = coordinates[0];
  if (!outer || !pointInRing(lon, lat, outer)) return false;
  for (let hole = 1; hole < coordinates.length; hole += 1) {
    const ring = coordinates[hole];
    if (ring && pointInRing(lon, lat, ring)) return false;
  }
  return true;
}

export function pointInKnoxGeometry(lon: number, lat: number, geometry: KnoxPolygonGeometry | null | undefined): boolean {
  if (!geometry) return false;
  if (geometry.type === "Polygon") return pointInPolygonCoords(lon, lat, geometry.coordinates as PolygonCoords);
  return (geometry.coordinates as MultiPolygonCoords).some((polygon) => pointInPolygonCoords(lon, lat, polygon));
}

export function geometryBbox(geometry: KnoxPolygonGeometry): BBox {
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  const visit = (value: unknown): void => {
    if (!Array.isArray(value)) return;
    if (typeof value[0] === "number" && typeof value[1] === "number") {
      const lon = value[0];
      const lat = value[1];
      if (lon < west) west = lon;
      if (lon > east) east = lon;
      if (lat < south) south = lat;
      if (lat > north) north = lat;
      return;
    }
    for (const child of value) visit(child);
  };
  visit(geometry.coordinates);
  if (!Number.isFinite(west)) return [0, 0, 0, 0];
  return [west, south, east, north];
}

function cellKey(lon: number, lat: number, cell: number): string {
  return `${Math.floor(lon / cell)}:${Math.floor(lat / cell)}`;
}

export function indexKnoxOverlays<P>(features: KnoxOverlayFeature<P>[], cell = 0.05): KnoxOverlayIndex<P> {
  const buckets = new Map<string, KnoxOverlayFeature<P>[]>();
  for (const feature of features) {
    const [west, south, east, north] = geometryBbox(feature.geometry);
    const i0 = Math.floor(west / cell);
    const i1 = Math.floor(east / cell);
    const j0 = Math.floor(south / cell);
    const j1 = Math.floor(north / cell);
    for (let i = i0; i <= i1; i += 1) {
      for (let j = j0; j <= j1; j += 1) {
        const key = `${i}:${j}`;
        const bucket = buckets.get(key);
        if (bucket) bucket.push(feature);
        else buckets.set(key, [feature]);
      }
    }
  }
  return { cell, buckets };
}

export function knoxOverlaysAtPoint<P>(
  index: KnoxOverlayIndex<P>,
  lon: number,
  lat: number,
): KnoxOverlayFeature<P>[] {
  const bucket = index.buckets.get(cellKey(lon, lat, index.cell)) ?? [];
  return bucket.filter((feature) => pointInKnoxGeometry(lon, lat, feature.geometry));
}

export function resolveKnoxMunicipality(
  lon: number,
  lat: number,
  boundaries: {
    knoxville: KnoxPolygonGeometry | null;
    farragut: KnoxPolygonGeometry | null;
  },
): KnoxMunicipalityId {
  if (pointInKnoxGeometry(lon, lat, boundaries.farragut)) return "farragut";
  if (pointInKnoxGeometry(lon, lat, boundaries.knoxville)) return "knoxville";
  return "unincorporated";
}

export type KnoxJoinContext = {
  boundaries: {
    knoxville: KnoxPolygonGeometry | null;
    farragut: KnoxPolygonGeometry | null;
  };
  zoning: KnoxOverlayIndex<KnoxZoningProperties>;
  countyFlu: KnoxOverlayIndex<KnoxFluProperties>;
  farragutZoning: KnoxOverlayIndex<FarragutZoningProperties>;
};

export type KnoxJoinedDesignation = {
  municipality: KnoxMunicipalityId;
  zoningCode: string | null;
  zoningDistrict: string | null;
  zoneType: string | null;
  flu: FluInfo | null;
  dataGaps: string[];
};

function smallest<P>(features: KnoxOverlayFeature<P>[]): KnoxOverlayFeature<P> | null {
  if (features.length === 0) return null;
  return features.reduce((best, feature) => {
    const [w, s, e, n] = geometryBbox(feature.geometry);
    const area = Math.abs((e - w) * (n - s));
    const [bw, bs, be, bn] = geometryBbox(best.geometry);
    const bestArea = Math.abs((be - bw) * (bn - bs));
    return area < bestArea ? feature : best;
  });
}

export function joinKnoxDesignation(lon: number, lat: number, context: KnoxJoinContext): KnoxJoinedDesignation {
  const municipality = resolveKnoxMunicipality(lon, lat, context.boundaries);
  const dataGaps: string[] = [];
  let zoningCode: string | null = null;
  let zoningDistrict: string | null = null;
  let zoneType: string | null = null;
  let flu: FluInfo | null = null;

  if (municipality === "farragut") {
    const hit = smallest(knoxOverlaysAtPoint(context.farragutZoning, lon, lat));
    zoneType = "Town of Farragut";
    zoningDistrict = hit?.properties.zone ?? null;
    zoningCode = knoxZoningCode(hit?.properties.zone);
    if (!zoningCode) dataGaps.push("No Farragut zoning polygon contained this parcel centroid.");
    dataGaps.push(FARRAGUT_FLU_GAP);
  } else {
    const wanted = municipality === "knoxville" ? "City of Knoxville" : "Knox County";
    const hits = knoxOverlaysAtPoint(context.zoning, lon, lat).filter(
      (feature) => feature.properties.zoneType === wanted,
    );
    const hit = smallest(hits);
    zoneType = wanted;
    zoningDistrict = hit?.properties.zone1 ?? null;
    zoningCode = hit?.properties.zoningCode ?? knoxZoningCode(hit?.properties.zone1, hit?.properties.zone2);
    if (!zoningCode) dataGaps.push(`No ${wanted} zoning polygon contained this parcel centroid.`);
    if (municipality === "knoxville") {
      dataGaps.push(KNOX_CITY_FLU_GAP);
    } else {
      const fluHit = smallest(knoxOverlaysAtPoint(context.countyFlu, lon, lat));
      const placeType = fluHit?.properties.placeType ?? null;
      if (placeType) {
        flu = {
          code: placeType,
          label: placeType,
          jurisdiction: "KNOX-COUNTY",
          source: fluHit?.properties.source ?? "advance-knox",
        };
      } else {
        dataGaps.push("No Advance Knox place type contained this parcel centroid.");
      }
    }
  }

  return { municipality, zoningCode, zoningDistrict, zoneType, flu, dataGaps };
}

export function mapKnoxParcel(
  attrs: Record<string, unknown>,
  centroid: [number, number],
  designation: KnoxJoinedDesignation | null,
): ParcelProperties | null {
  const parcelId = clean(attrs.PARCELID) || clean(attrs.PARCELID_1);
  if (!parcelId) return null;
  const acreage = knoxAcreage(attrs);
  if (!acreage.inBand || acreage.acres == null) return null;
  const municipality = designation?.municipality ?? null;
  const prefix =
    municipality === "knoxville" ? "KNOX-CITY" : municipality === "farragut" ? "FARRAGUT" : municipality === "unincorporated" ? "KNOX-COUNTY" : null;
  const sale: LastSale = {
    date: knoxDate(attrs.SALE_DATE),
    price: salePrice(attrs.PURCHASE_PRICE),
    qualified: clean(attrs.VALIDITY_FLAG),
    datePurchased: knoxDate(attrs.DATE_PURCHASED),
    deedBook: clean(attrs.DEED_BOOK),
    deedPage: clean(attrs.DEED_PAGE),
    odocBook: clean(attrs.ODOC_BOOK),
    odocPage: clean(attrs.ODOC_PAGE),
  };
  const tax: TaxInfo = {
    marketValue: money(attrs.APPRAISED_TOTAL),
    assessedValue: money(attrs.ASSESSED_TOTAL),
    taxableValue: null,
    taxes: null,
    appraisedLand: money(attrs.APPRAISED_LAND),
    appraisedBuilding: money(attrs.APPRAISED_BLDG),
  };
  const owner = clean(attrs.OWNER) || clean(attrs.KGIS_OWNER) || clean(attrs.ACCELA_OWNER);
  return {
    id: `${KNOX_FIPS}:${parcelId}`,
    parcelId,
    countyFips: KNOX_FIPS,
    countyName: "Knox",
    state: "Tennessee",
    marketIds: ["Knoxville"],
    situsAddress: knoxSitus(attrs),
    situsCity: null,
    situsZip: null,
    jurisdictionCode: prefix,
    ownerName: owner,
    ownerName2: null,
    propertyName: null,
    zoningCode: designation?.zoningCode ?? null,
    zoningDistrict: designation?.zoningDistrict ?? null,
    jurisdictionPrefix: prefix,
    dorCode: clean(attrs.LANDUSE),
    acreage: Math.round(acreage.acres * 10000) / 10000,
    centroid,
    lastSale: sale,
    tax,
    mailingAddress: knoxMailing(attrs),
    incomeTract: null,
    incomeBlockGroup: null,
    nearestRoad: null,
    flu: designation?.flu ?? null,
    opportunityZone: null,
    oz2Eligibility: null,
    appraiserUrl: knoxAppraiserUrl(parcelId),
    dataGaps: designation?.dataGaps ?? [],
    source: "kgis-globalsearch",
    municipality: municipality ? KNOX_MUNICIPALITY_NAME[municipality] : null,
    baseParcelId: clean(attrs.BASE_PARCELID),
    pbaid: clean(attrs.PBAID),
    recordedAcreage: num(attrs.RECORDED_AREA),
  };
}
