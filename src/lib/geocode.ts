import { countyPlaces, countyRequests, type CountyPlace } from "./countyAddress";
import { ADDRESS_NOT_FOUND, censusMatchPoint, LOOKUP_UNAVAILABLE, type GeocodeSuggestion, type JumpPoint } from "./jumpTo";
import { findParcelHits, formatParcelLabel, parseAddressQuery, stateAbbr } from "./parcelAddress";
import { parcelHits } from "./parcelIndex";

export type GeocodeProvider = "census" | "esri" | "nominatim" | "parcels" | "county";

export type GeocodeResult =
  | { ok: true; lng: number; lat: number; provider: GeocodeProvider }
  | { ok: false; status: 404 | 503; error: string; suggestions?: GeocodeSuggestion[] };

export const GEOCODE_TIMEOUT_MS = {
  census: 3_500,
  esri: 2_500,
  nominatim: 2_500,
  county: 2_000,
} as const;

/** Stop spelling variants once Census has already used this much of the request. */
const CENSUS_BUDGET_MS = 7_000;
const MAX_CENSUS_VARIANTS = 4;
const ESRI_MIN_SCORE = 90;
const SUGGESTION_MIN_SCORE = 70;

const CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress";
const ESRI_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates";
const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";

/**
 * Nominatim's usage policy requires an identifying User-Agent and asks callers
 * to stay at or below one request per second. This runs only after Census and
 * Esri miss, and only once per search.
 */
export const NOMINATIM_USER_AGENT =
  "CatalystLandSearch/1.0 (jump-to address search; +https://catalyst-land-search.vercel.app)";

type FetchLike = typeof fetch;

export type GeocodeDeps = {
  fetch?: FetchLike;
  timeouts?: { census?: number; esri?: number; nominatim?: number; county?: number };
  now?: () => number;
  /** State file text. Tests inject this so a miss does not read the built index. */
  parcelRead?: (state: string) => string | null;
};

type Outcome =
  | { kind: "hit"; point: JumpPoint }
  | { kind: "miss" }
  | { kind: "error"; transient: boolean };

const UNIT_PATTERN =
  /(?:,\s*|\s+)(?:(?:apartment|apt|suite|ste|unit|building|bldg|floor|room|rm|lot|space|spc)\.?\s*#?\s*(?:[a-z0-9-]*\d[a-z0-9-]*|[a-z])|#\s*[a-z0-9-]*\d[a-z0-9-]*)\b,?/gi;

/**
 * Census onelineaddress already matches many "Apt 4" forms. These variants cover
 * the ones it drops: a unit token, Hwy/SR/US/County Rd spellings, and a bad ZIP.
 * Full state names are intentionally not substituted. "Florida Highway 16" and
 * "North Carolina Highway 73" geocode to Florida St and Caroline Ct.
 */
export function addressVariants(input: string): string[] {
  const original = cleanup(input);
  const stripped = stripUnit(original);
  const expanded = expandRouteAbbreviations(stripped);
  const ordered = [
    original,
    stripped,
    expanded,
    withoutZip(expanded),
    withoutZip(stripped),
    withoutZip(original),
  ];
  const seen = new Set<string>();
  const variants: string[] = [];
  for (const variant of ordered) {
    const key = variant.toLowerCase();
    if (variant.length < 5 || seen.has(key)) continue;
    seen.add(key);
    variants.push(variant);
    if (variants.length >= MAX_CENSUS_VARIANTS) break;
  }
  return variants.length > 0 ? variants : [original];
}

export function esriMatchPoint(body: unknown): JumpPoint | null {
  if (!body || typeof body !== "object" || "error" in body) return null;
  const candidates = (body as { candidates?: unknown }).candidates;
  if (!Array.isArray(candidates)) return null;
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== "object") continue;
    const row = candidate as {
      score?: unknown;
      location?: { x?: unknown; y?: unknown };
      attributes?: { Score?: unknown; Country?: unknown };
    };
    const score = Number(row.score ?? row.attributes?.Score);
    if (!Number.isFinite(score) || score < ESRI_MIN_SCORE) continue;
    const country = row.attributes?.Country;
    if (country != null && String(country).trim() !== "") {
      const code = String(country).trim().toUpperCase();
      if (code !== "USA" && code !== "US") continue;
    }
    const point = asPoint(row.location?.x, row.location?.y);
    if (!point || !inUnitedStates(point.lng, point.lat)) continue;
    return point;
  }
  return null;
}

export function nominatimMatchPoint(body: unknown): JumpPoint | null {
  if (!Array.isArray(body)) return null;
  for (const row of body) {
    if (!row || typeof row !== "object") continue;
    const hit = row as { lat?: unknown; lon?: unknown; address?: { country_code?: unknown } };
    const country = hit.address?.country_code;
    if (country != null && String(country).trim() !== "" && String(country).toLowerCase() !== "us") continue;
    const point = asPoint(hit.lon, hit.lat);
    if (!point || !inUnitedStates(point.lng, point.lat)) continue;
    return point;
  }
  return null;
}

export async function geocodeAddress(query: string, deps: GeocodeDeps = {}): Promise<GeocodeResult> {
  const fetchImpl = deps.fetch ?? fetch;
  const timeouts = { ...GEOCODE_TIMEOUT_MS, ...deps.timeouts };
  const now = deps.now ?? Date.now;
  const cleaned = cleanup(query);

  let censusMiss = false;
  let retries = 1;
  const started = now();
  const variants = addressVariants(cleaned);
  for (let index = 0; index < variants.length; index += 1) {
    const variant = variants[index];
    if (now() - started > CENSUS_BUDGET_MS) break;
    let outcome = await queryCensus(variant, fetchImpl, timeouts.census, index > 0);
    if (outcome.kind === "error" && outcome.transient && retries > 0) {
      retries -= 1;
      outcome = await queryCensus(variant, fetchImpl, timeouts.census, index > 0);
    }
    if (outcome.kind === "hit") return hit("census", outcome.point);
    if (outcome.kind === "miss") {
      censusMiss = true;
      continue;
    }
    if (outcome.transient) break;
  }

  const esri = await queryEsri(cleaned, fetchImpl, timeouts.esri);
  if (esri.kind === "hit") return hit("esri", esri.point);
  const nominatim = await queryNominatim(cleaned, fetchImpl, timeouts.nominatim);
  if (nominatim.kind === "hit") return hit("nominatim", nominatim.point);
  if (!(censusMiss && esri.kind === "miss" && nominatim.kind === "miss")) {
    return { ok: false, status: 503, error: LOOKUP_UNAVAILABLE };
  }

  const suggestions: GeocodeSuggestion[] = [];
  for (const candidate of esri.candidates) suggestions.push(...esriSuggestion(cleaned, candidate));
  for (const candidate of nominatim.suggestions) suggestions.push(candidate);

  const parcels = lookupParcels(cleaned, deps.parcelRead);
  if (parcels.length === 1) {
    const [only] = parcels;
    return hit("parcels", { lng: only.lng, lat: only.lat });
  }
  for (const parcel of parcels) {
    suggestions.push({
      label: formatParcelLabel(parcel),
      lng: parcel.lng,
      lat: parcel.lat,
      score: 100,
      provider: "parcels",
    });
  }

  const county = await queryCounties(cleaned, fetchImpl, timeouts.county);
  if (county.hit) return hit("county", county.hit);
  for (const place of county.suggestions) {
    suggestions.push({ label: place.label, lng: place.lng, lat: place.lat, score: place.score, provider: "county" });
  }

  const ranked = rankSuggestions(suggestions);
  if (ranked.length > 0) return { ok: false, status: 404, error: ADDRESS_NOT_FOUND, suggestions: ranked };
  return { ok: false, status: 404, error: ADDRESS_NOT_FOUND };
}

function hit(provider: GeocodeProvider, point: JumpPoint): GeocodeResult {
  return { ok: true, lng: point.lng, lat: point.lat, provider };
}

async function queryCensus(
  address: string,
  fetchImpl: FetchLike,
  timeoutMs: number,
  checkStreet: boolean,
): Promise<Outcome> {
  const url = new URL(CENSUS_URL);
  url.searchParams.set("address", address);
  url.searchParams.set("benchmark", "Public_AR_Current");
  url.searchParams.set("format", "json");
  const response = await request(url, { headers: { Accept: "application/json" } }, timeoutMs, fetchImpl);
  if (response.kind !== "response") return { kind: "error", transient: true };
  if (!response.response.ok) return { kind: "error", transient: transientStatus(response.response.status) };
  const body = await readJson(response.response);
  if (body == null) return { kind: "error", transient: true };
  const point = censusMatchPoint(body);
  if (!point) return { kind: "miss" };
  // "150 Nexton Parkway, Summerville, SC" (ZIP removed) matches Newton Rd.
  // Keep the typed query's Census hit, and only keep a rewritten query when
  // the matched street still contains one of its distinctive words.
  if (checkStreet && !variantAgrees(address, censusMatchedAddress(body))) return { kind: "miss" };
  return { kind: "hit", point };
}

const GENERIC_STREET_WORDS = new Set([
  "road",
  "street",
  "avenue",
  "drive",
  "lane",
  "court",
  "boulevard",
  "highway",
  "parkway",
  "circle",
  "place",
  "trail",
  "county",
  "state",
  "route",
  "north",
  "south",
  "east",
  "west",
  "northeast",
  "northwest",
  "southeast",
  "southwest",
  "saint",
  "mount",
  "ridge",
  "creek",
  "lake",
  "point",
  "center",
  "centre",
]);

function variantAgrees(query: string, matched: string): boolean {
  if (!matched) return true;
  const street = (query.split(",")[0] ?? query).toLowerCase();
  const matchedStreet = (matched.split(",")[0] ?? matched).toLowerCase();
  const words = (street.match(/[a-z]{4,}/g) ?? []).filter((word) => !GENERIC_STREET_WORDS.has(word));
  if (words.length === 0) return false;
  return words.some((word) => matchedStreet.includes(word));
}

function censusMatchedAddress(body: unknown): string {
  const matches = (body as { result?: { addressMatches?: unknown[] } } | null)?.result?.addressMatches;
  const first = Array.isArray(matches) ? matches[0] : null;
  const matched = (first as { matchedAddress?: unknown } | null)?.matchedAddress;
  return typeof matched === "string" ? matched : "";
}

type EsriCandidate = {
  score: number;
  lng: number;
  lat: number;
  label: string;
  addrType: string;
  country: string | null;
  region: string | null;
};

type EsriQuery = { kind: "hit"; point: JumpPoint } | { kind: "miss"; candidates: EsriCandidate[] } | { kind: "error" };

type NominatimQuery =
  | { kind: "hit"; point: JumpPoint }
  | { kind: "miss"; suggestions: GeocodeSuggestion[] }
  | { kind: "error" };

async function queryEsri(address: string, fetchImpl: FetchLike, timeoutMs: number): Promise<EsriQuery> {
  const url = new URL(ESRI_URL);
  url.searchParams.set("SingleLine", address);
  url.searchParams.set("countryCode", "USA");
  url.searchParams.set("outFields", "Score,Addr_type,Country,Region,City,StAddr");
  url.searchParams.set("f", "json");
  url.searchParams.set("maxLocations", "5");
  url.searchParams.set("forStorage", "false");
  const response = await request(url, { headers: { Accept: "application/json" } }, timeoutMs, fetchImpl);
  if (response.kind !== "response") return { kind: "error" };
  if (!response.response.ok) return { kind: "error" };
  const body = await readJson(response.response);
  if (body == null) return { kind: "error" };
  if (typeof body === "object" && body && "error" in body && (body as { error?: unknown }).error) {
    return { kind: "error" };
  }
  const candidates = parseEsriCandidates(body);
  const point = esriAutoPoint(address, candidates);
  return point ? { kind: "hit", point } : { kind: "miss", candidates };
}

async function queryNominatim(address: string, fetchImpl: FetchLike, timeoutMs: number): Promise<NominatimQuery> {
  const url = new URL(NOMINATIM_URL);
  url.searchParams.set("q", address);
  url.searchParams.set("format", "jsonv2");
  url.searchParams.set("addressdetails", "1");
  url.searchParams.set("countrycodes", "us");
  url.searchParams.set("limit", "5");
  const response = await request(
    url,
    {
      headers: {
        Accept: "application/json",
        "User-Agent": NOMINATIM_USER_AGENT,
        Referer: "https://catalyst-land-search.vercel.app",
      },
    },
    timeoutMs,
    fetchImpl,
  );
  if (response.kind !== "response") return { kind: "error" };
  if (!response.response.ok) return { kind: "error" };
  const body = await readJson(response.response);
  if (!Array.isArray(body)) return { kind: "error" };
  const suggestions: GeocodeSuggestion[] = [];
  for (const row of body) {
    if (!row || typeof row !== "object") continue;
    const record = row as { display_name?: unknown; address?: { state?: unknown } };
    if (isLegacyNominatim(record)) {
      const point = nominatimMatchPoint([row]);
      if (point) return { kind: "hit", point };
      continue;
    }
    const suggestion = nominatimSuggestion(address, row);
    if (!suggestion) continue;
    if (suggestion.score >= ESRI_MIN_SCORE) return { kind: "hit", point: suggestion };
    suggestions.push(suggestion);
  }
  return { kind: "miss", suggestions };
}

const SUGGESTION_EXTRA_WORDS = new Set(["park", "parks"]);

function esriSuggestion(query: string, candidate: EsriCandidate): GeocodeSuggestion[] {
  if (candidate.score < SUGGESTION_MIN_SCORE || candidate.score >= ESRI_MIN_SCORE) return [];
  if (!countryOk(candidate.country) || !inUnitedStates(candidate.lng, candidate.lat)) return [];
  const addrType = candidate.addrType.trim().toLowerCase();
  if (addrType === "postal" || addrType === "locality") return [];
  if (!candidate.label || !sameState(query, candidate.label, candidate.region)) return [];
  if (!suggestionOverlap(query, candidate.label)) return [];
  return [
    {
      label: candidate.label,
      lng: candidate.lng,
      lat: candidate.lat,
      score: candidate.score,
      provider: "esri",
    },
  ];
}

function esriAutoPoint(query: string, candidates: EsriCandidate[]): JumpPoint | null {
  for (const candidate of candidates) {
    if (candidate.score < ESRI_MIN_SCORE) continue;
    if (!countryOk(candidate.country) || !inUnitedStates(candidate.lng, candidate.lat)) continue;
    if (!regionAgrees(query, candidate.region)) continue;
    return { lng: candidate.lng, lat: candidate.lat };
  }
  return null;
}

function parseEsriCandidates(body: unknown): EsriCandidate[] {
  const candidates = (body as { candidates?: unknown }).candidates;
  if (!Array.isArray(candidates)) return [];
  const parsed: EsriCandidate[] = [];
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== "object") continue;
    const row = candidate as {
      address?: unknown;
      score?: unknown;
      location?: { x?: unknown; y?: unknown };
      attributes?: { Score?: unknown; Country?: unknown; Addr_type?: unknown; Region?: unknown };
    };
    const score = Number(row.score ?? row.attributes?.Score);
    const point = asPoint(row.location?.x, row.location?.y);
    if (!Number.isFinite(score) || !point) continue;
    parsed.push({
      score,
      lng: point.lng,
      lat: point.lat,
      label: typeof row.address === "string" ? row.address : "",
      addrType: row.attributes?.Addr_type == null ? "" : String(row.attributes.Addr_type),
      country: row.attributes?.Country == null || String(row.attributes.Country).trim() === "" ? null : String(row.attributes.Country),
      region: row.attributes?.Region == null || String(row.attributes.Region).trim() === "" ? null : String(row.attributes.Region),
    });
  }
  return parsed;
}

function nominatimSuggestion(query: string, row: unknown): GeocodeSuggestion | null {
  if (!row || typeof row !== "object") return null;
  const hit = row as {
    lat?: unknown;
    lon?: unknown;
    display_name?: unknown;
    address?: { country_code?: unknown; state?: unknown };
  };
  const country = hit.address?.country_code;
  if (country != null && String(country).trim() !== "" && String(country).toLowerCase() !== "us") return null;
  const point = asPoint(hit.lon, hit.lat);
  const label = typeof hit.display_name === "string" ? hit.display_name.trim() : "";
  if (!point || !label || !inUnitedStates(point.lng, point.lat)) return null;
  const wanted = parseAddressQuery(query).state;
  const found = stateAbbr(typeof hit.address?.state === "string" ? hit.address.state : null);
  if (wanted && found && wanted !== found) return null;
  if (!suggestionOverlap(query, label)) return null;
  let score = 40 + 25;
  if (!wanted || found === wanted) score += 20;
  const number = parseAddressQuery(query).number;
  if (number && new RegExp(`\\b${number}\\b`).test(label)) score += 20;
  if (score < SUGGESTION_MIN_SCORE) return null;
  return { label, lng: point.lng, lat: point.lat, score, provider: "nominatim" };
}

function isLegacyNominatim(row: { display_name?: unknown; address?: { state?: unknown } }): boolean {
  const display = typeof row.display_name === "string" ? row.display_name.trim() : "";
  const state = typeof row.address?.state === "string" ? row.address.state.trim() : "";
  return !display && !state;
}

function lookupParcels(query: string, read: GeocodeDeps["parcelRead"]): ReturnType<typeof findParcelHits> {
  if (read) {
    const state = parseAddressQuery(query).state;
    if (!state) return [];
    return findParcelHits(read(state) ?? "", query);
  }
  return parcelHits(query);
}

async function queryCounties(
  query: string,
  fetchImpl: FetchLike,
  timeoutMs: number,
): Promise<{ hit: CountyPlace | null; suggestions: CountyPlace[] }> {
  const suggestions: CountyPlace[] = [];
  for (const item of countyRequests(query)) {
    let url: URL;
    try {
      url = new URL(item.url);
    } catch {
      continue;
    }
    const response = await request(url, { headers: { Accept: "application/json" } }, timeoutMs, fetchImpl);
    if (response.kind !== "response" || !response.response.ok) continue;
    const body = await readJson(response.response);
    if (body == null) continue;
    const places = countyPlaces(item.service, body, query);
    if (places.hit) return { hit: places.hit, suggestions: [] };
    suggestions.push(...places.suggestions);
  }
  return { hit: null, suggestions };
}

function rankSuggestions(items: GeocodeSuggestion[]): GeocodeSuggestion[] {
  const ranked: GeocodeSuggestion[] = [];
  const seen = new Set<string>();
  const sorted = items.slice().sort((a, b) => b.score - a.score || a.label.localeCompare(b.label));
  for (const item of sorted) {
    const key = `${item.lat.toFixed(4)},${item.lng.toFixed(4)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    ranked.push(item);
    if (ranked.length >= 5) break;
  }
  return ranked;
}

function sameState(query: string, label: string, region: string | null): boolean {
  const wanted = parseAddressQuery(query).state;
  if (!wanted) return false;
  const found = stateAbbr(region) ?? parseAddressQuery(label).state;
  return found === wanted;
}

function regionAgrees(query: string, region: string | null): boolean {
  const wanted = parseAddressQuery(query).state;
  const found = stateAbbr(region);
  if (!wanted || !found) return true;
  return wanted === found;
}

function countryOk(country: string | null): boolean {
  if (country == null || country.trim() === "") return true;
  const code = country.trim().toUpperCase();
  return code === "USA" || code === "US";
}

function suggestionOverlap(query: string, label: string): boolean {
  const street = (query.split(",")[0] ?? query).toLowerCase();
  const words = (street.match(/[a-z]{4,}/g) ?? []).filter(
    (word) => !GENERIC_STREET_WORDS.has(word) && !SUGGESTION_EXTRA_WORDS.has(word),
  );
  if (words.length === 0) return false;
  const hay = (label.split(",")[0] ?? label).toLowerCase();
  return words.some((word) => hay.includes(word));
}

async function request(
  url: URL,
  init: RequestInit,
  timeoutMs: number,
  fetchImpl: FetchLike,
): Promise<{ kind: "response"; response: Response } | { kind: "error" }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(url, { ...init, signal: controller.signal });
    return { kind: "response", response };
  } catch {
    return { kind: "error" };
  } finally {
    clearTimeout(timer);
  }
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function transientStatus(status: number): boolean {
  return status === 408 || status === 429 || status >= 500;
}

function asPoint(lng: unknown, lat: unknown): JumpPoint | null {
  const x = Number(lng);
  const y = Number(lat);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  if (Math.abs(y) > 90 || Math.abs(x) > 180) return null;
  return { lng: x, lat: y };
}

/** CONUS, Alaska, Hawaii, and Puerto Rico. Aleutian longitudes east of 180 are omitted. */
function inUnitedStates(lng: number, lat: number): boolean {
  return lat >= 17 && lat <= 72 && lng >= -180 && lng <= -64;
}

function stripUnit(input: string): string {
  return cleanup(
    input.replace(UNIT_PATTERN, (match) => {
      const trimmed = match.trim();
      if (trimmed.startsWith(",") || trimmed.endsWith(",")) return ", ";
      return " ";
    }),
  );
}

function withoutZip(input: string): string {
  return cleanup(input.replace(/[,\s]+\d{5}(?:-\d{4})?\s*$/i, "").replace(/[,\s]+usa\s*$/i, ""));
}

function expandRouteAbbreviations(input: string): string {
  let text = input;
  text = text.replace(/\bU\.?\s*S\.?\s*(?:Hwy|Highway)?\s*-?\s*(\d{1,4})(?!\d)/gi, "US Highway $1");
  text = text.replace(/\bS\.?\s*R\.?\s*-?\s*(\d{1,4})(?!\d)/gi, "State Road $1");
  text = text.replace(/\b(?:County|Co)\.?\s+(?:Hwy|Highway|Rd|Road)\.?\s*-?\s*(\d{1,4})(?!\d)/gi, "County Road $1");
  text = text.replace(/\bC\.?\s*R\.?\s*-?\s*(\d{1,4})(?!\d)/gi, "County Road $1");
  text = text.replace(/\bHwy\b/gi, "Highway");
  text = text.replace(/\bPkwy\b/gi, "Parkway");
  text = text.replace(/\bBlvd\b/gi, "Boulevard");
  return cleanup(text);
}

function cleanup(input: string): string {
  return input
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\s+,/g, ",")
    .replace(/,\s*,+/g, ",")
    .replace(/,\s*$/g, "")
    .trim();
}
