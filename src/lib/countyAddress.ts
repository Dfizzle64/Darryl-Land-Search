import { canonicalStreetName, parseAddressQuery } from "./parcelAddress";

export type CountyPlace = {
  lng: number;
  lat: number;
  label: string;
  score: number;
};

export type CountyService = "orange" | "union" | "tennessee";

const ORANGE_URL = "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/0/query";
const UNION_URL = "https://atlas.unioncountync.gov/server/rest/services/UNION_COUNTY_LAYERS/MapServer/152/query";
const TENNESSEE_URL =
  "https://tnmap.tn.gov/arcgis/rest/services/LOCATORS/TN_ADDRESSPOINTS/GeocodeServer/findAddressCandidates";

const ORANGE_CITIES = new Set([
  "WINTER GARDEN",
  "ORLANDO",
  "APOPKA",
  "OCOEE",
  "WINTER PARK",
  "MAITLAND",
  "BELLE ISLE",
  "EDGEWOOD",
  "OAKLAND",
  "EATONVILLE",
  "WINDERMERE",
  "BAY LAKE",
  "LAKE BUENA VISTA",
]);

const UNION_CITIES = new Set([
  "INDIAN TRAIL",
  "STALLINGS",
  "MONROE",
  "WEDDINGTON",
  "WAXHAW",
  "MARVIN",
  "WINGATE",
  "MINERAL SPRINGS",
  "HEMBY BRIDGE",
  "FAIRVIEW",
  "MARSHVILLE",
  "UNIONVILLE",
]);

const DIRECTION = new Set(["N", "S", "E", "W", "NE", "NW", "SE", "SW"]);
const STREET_TYPE = new Set(["ST", "AVE", "RD", "DR", "LN", "BLVD", "CT", "PL", "CIR", "WAY", "TRL", "PKWY", "HWY", "TER", "PIKE", "ALY"]);

/**
 * Orange County FL, Union County NC, and the Tennessee statewide address-point
 * locator. Lancaster County SC has no stable public query endpoint.
 */
export function countyRequests(query: string): Array<{ service: CountyService; url: string }> {
  const parsed = parseAddressQuery(query);
  if (!parsed.state || !parsed.number || !parsed.street) return [];
  const requests: Array<{ service: CountyService; url: string }> = [];
  if (parsed.state === "TN") {
    const url = new URL(TENNESSEE_URL);
    url.searchParams.set("SingleLine", query);
    url.searchParams.set("f", "json");
    url.searchParams.set("outSR", "4326");
    url.searchParams.set("maxLocations", "5");
    requests.push({ service: "tennessee", url: url.toString() });
  }
  if (parsed.state === "FL" && (mentions(query, "orange county") || cityIn(parsed.city, ORANGE_CITIES))) {
    const url = orangeUrl(parsed.number, parsed.street);
    if (url) requests.push({ service: "orange", url });
  }
  if (parsed.state === "NC" && (mentions(query, "union county") || cityIn(parsed.city, UNION_CITIES))) {
    const url = unionUrl(parsed.number, parsed.street);
    if (url) requests.push({ service: "union", url });
  }
  return requests;
}

export function countyPlaces(service: CountyService, body: unknown, query: string): { hit: CountyPlace | null; suggestions: CountyPlace[] } {
  if (service === "tennessee") return tennesseePlaces(body, query);
  if (service === "orange") return orangePlaces(body, query);
  return unionPlaces(body, query);
}

function orangeUrl(number: string, street: string): string | null {
  const token = distinctiveToken(street);
  if (!token) return null;
  const url = new URL(ORANGE_URL);
  url.searchParams.set("where", `FULL_ADDRESS_NUMBER=${quote(number)} AND COMPLETE_STREETNAME LIKE ${quote(`%${token}%`)}`);
  url.searchParams.set("outFields", "COMPLETE_ADDRESS,FULL_ADDRESS_NUMBER,COMPLETE_STREETNAME,LATITUDE,LONGITUDE");
  url.searchParams.set("returnGeometry", "false");
  url.searchParams.set("resultRecordCount", "5");
  url.searchParams.set("f", "json");
  return url.toString();
}

function unionUrl(number: string, street: string): string | null {
  const parts = splitStreet(street);
  if (!parts) return null;
  const clauses = [`NUM=${quote(number)}`, `NAME=${quote(parts.name)}`, `TYPE=${quote(parts.type)}`];
  if (parts.dir) clauses.push(`DIR=${quote(parts.dir)}`);
  const url = new URL(UNION_URL);
  url.searchParams.set("where", clauses.join(" AND "));
  url.searchParams.set("outFields", "NUM,NAME,TYPE,DIR,DISPLAY");
  url.searchParams.set("returnGeometry", "true");
  url.searchParams.set("outSR", "4326");
  url.searchParams.set("resultRecordCount", "5");
  url.searchParams.set("f", "json");
  return url.toString();
}

function orangePlaces(body: unknown, query: string): { hit: CountyPlace | null; suggestions: CountyPlace[] } {
  const parsed = parseAddressQuery(query);
  for (const attributes of featureAttributes(body)) {
    const number = text(attributes.FULL_ADDRESS_NUMBER);
    const street = canonicalStreetName(text(attributes.COMPLETE_STREETNAME));
    if (!parsed.number || !parsed.street || number !== parsed.number || street !== parsed.street) continue;
    const lng = Number(attributes.LONGITUDE);
    const lat = Number(attributes.LATITUDE);
    if (!usable(lng, lat)) continue;
    const label = text(attributes.COMPLETE_ADDRESS) || `${number} ${street}`;
    return { hit: { lng, lat, label, score: 100 }, suggestions: [] };
  }
  return { hit: null, suggestions: [] };
}

function unionPlaces(body: unknown, query: string): { hit: CountyPlace | null; suggestions: CountyPlace[] } {
  const parsed = parseAddressQuery(query);
  const expected = parsed.street ? splitStreet(parsed.street) : null;
  if (!parsed.number || !expected) return { hit: null, suggestions: [] };
  for (const feature of features(body)) {
    const attributes = feature.attributes;
    const name = text(attributes.NAME).toUpperCase();
    const type = text(attributes.TYPE).toUpperCase();
    const dir = text(attributes.DIR).toUpperCase();
    if (text(attributes.NUM) !== parsed.number || name !== expected.name || type !== expected.type) continue;
    if (expected.dir && dir && dir !== expected.dir) continue;
    const point = geometryPoint(feature.geometry);
    if (!point) continue;
    const label = text(attributes.DISPLAY) || [parsed.number, expected.dir, expected.name, expected.type].filter(Boolean).join(" ");
    return { hit: { ...point, label, score: 100 }, suggestions: [] };
  }
  return { hit: null, suggestions: [] };
}

function tennesseePlaces(body: unknown, query: string): { hit: CountyPlace | null; suggestions: CountyPlace[] } {
  const suggestions: CountyPlace[] = [];
  for (const candidate of locatorCandidates(body)) {
    if (candidate.score >= 90 && candidate.addrType !== "Postal" && candidate.addrType !== "Locality") {
      return { hit: candidate, suggestions: [] };
    }
    if (candidate.score < 70 || candidate.addrType === "Postal" || candidate.addrType === "Locality") continue;
    if (!streetOverlaps(query, candidate.label)) continue;
    suggestions.push(candidate);
  }
  suggestions.sort((a, b) => b.score - a.score);
  return { hit: null, suggestions: suggestions.slice(0, 5) };
}

function locatorCandidates(body: unknown): Array<CountyPlace & { addrType: string }> {
  if (!body || typeof body !== "object" || !("candidates" in body)) return [];
  const candidates = (body as { candidates?: unknown }).candidates;
  if (!Array.isArray(candidates)) return [];
  const places: Array<CountyPlace & { addrType: string }> = [];
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== "object") continue;
    const row = candidate as {
      address?: unknown;
      score?: unknown;
      location?: { x?: unknown; y?: unknown };
      attributes?: { Score?: unknown; Addr_type?: unknown };
    };
    const score = Number(row.score ?? row.attributes?.Score);
    const lng = Number(row.location?.x);
    const lat = Number(row.location?.y);
    const label = text(row.address);
    if (!label || !Number.isFinite(score) || !usable(lng, lat)) continue;
    places.push({ lng, lat, label, score, addrType: text(row.attributes?.Addr_type) });
  }
  return places;
}

function featureAttributes(body: unknown): Array<Record<string, unknown>> {
  return features(body).map((feature) => feature.attributes);
}

function features(body: unknown): Array<{ attributes: Record<string, unknown>; geometry?: unknown }> {
  if (!body || typeof body !== "object" || !("features" in body)) return [];
  const rows = (body as { features?: unknown }).features;
  if (!Array.isArray(rows)) return [];
  return rows.flatMap((row) => {
    if (!row || typeof row !== "object") return [];
    const feature = row as { attributes?: unknown; geometry?: unknown };
    const attributes = feature.attributes;
    if (!attributes || typeof attributes !== "object") return [];
    return [{ attributes: attributes as Record<string, unknown>, geometry: feature.geometry }];
  });
}

function geometryPoint(geometry: unknown): { lng: number; lat: number } | null {
  if (!geometry || typeof geometry !== "object") return null;
  const point = geometry as { x?: unknown; y?: unknown };
  const lng = Number(point.x);
  const lat = Number(point.y);
  return usable(lng, lat) ? { lng, lat } : null;
}

function splitStreet(street: string): { dir: string; name: string; type: string } | null {
  const tokens = street.split(" ").filter(Boolean);
  if (tokens.length < 2 || !STREET_TYPE.has(tokens[tokens.length - 1])) return null;
  const type = tokens.pop() ?? "";
  let dir = "";
  if (tokens.length > 1 && DIRECTION.has(tokens[0])) dir = tokens.shift() ?? "";
  const name = tokens.join(" ");
  if (!name) return null;
  return { dir, name, type };
}

function distinctiveToken(street: string): string | null {
  const tokens = street.split(" ").filter((token) => token.length >= 4 && !STREET_TYPE.has(token) && !DIRECTION.has(token));
  tokens.sort((a, b) => b.length - a.length);
  const token = tokens[0]?.replace(/[%_]/g, "");
  return token || null;
}

function streetOverlaps(query: string, label: string): boolean {
  const parsed = parseAddressQuery(query);
  const words = (parsed.street ?? "").split(" ").filter((word) => word.length >= 4 && !STREET_TYPE.has(word) && word !== "PARK" && word !== "PARKS" && word !== "POINT");
  if (!words.length) return false;
  const hay = (label.split(",")[0] ?? label).toUpperCase();
  return words.some((word) => hay.includes(word));
}

function cityIn(city: string | null, cities: Set<string>): boolean {
  if (!city) return false;
  return cities.has(city.toUpperCase().replace(/[^A-Z0-9]+/g, " ").replace(/\s+/g, " ").trim());
}

function mentions(query: string, phrase: string): boolean {
  return query.toLowerCase().includes(phrase);
}

function quote(value: string): string {
  return `'${value.replace(/'/g, "''")}'`;
}

function text(value: unknown): string {
  return typeof value === "string" || typeof value === "number" ? String(value).trim() : "";
}

function usable(lng: number, lat: number): boolean {
  return Number.isFinite(lng) && Number.isFinite(lat) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180;
}
