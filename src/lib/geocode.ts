import { ADDRESS_NOT_FOUND, censusMatchPoint, LOOKUP_UNAVAILABLE, type JumpPoint } from "./jumpTo";

export type GeocodeProvider = "census" | "esri" | "nominatim";

export type GeocodeResult =
  | { ok: true; lng: number; lat: number; provider: GeocodeProvider }
  | { ok: false; status: 404 | 503; error: string };

export const GEOCODE_TIMEOUT_MS = {
  census: 3_500,
  esri: 2_500,
  nominatim: 2_500,
} as const;

/** Stop spelling variants once Census has already used this much of the request. */
const CENSUS_BUDGET_MS = 7_000;
const MAX_CENSUS_VARIANTS = 4;
const ESRI_MIN_SCORE = 90;

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
  timeouts?: { census?: number; esri?: number; nominatim?: number };
  now?: () => number;
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
  if (censusMiss && esri.kind === "miss" && nominatim.kind === "miss") {
    return { ok: false, status: 404, error: ADDRESS_NOT_FOUND };
  }
  return { ok: false, status: 503, error: LOOKUP_UNAVAILABLE };
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

async function queryEsri(address: string, fetchImpl: FetchLike, timeoutMs: number): Promise<Outcome> {
  const url = new URL(ESRI_URL);
  url.searchParams.set("SingleLine", address);
  url.searchParams.set("countryCode", "USA");
  url.searchParams.set("outFields", "Score,Addr_type,Country");
  url.searchParams.set("f", "json");
  url.searchParams.set("maxLocations", "3");
  url.searchParams.set("forStorage", "false");
  const response = await request(url, { headers: { Accept: "application/json" } }, timeoutMs, fetchImpl);
  if (response.kind !== "response") return { kind: "error", transient: true };
  if (!response.response.ok) return { kind: "error", transient: transientStatus(response.response.status) };
  const body = await readJson(response.response);
  if (body == null) return { kind: "error", transient: true };
  if (typeof body === "object" && body && "error" in body && (body as { error?: unknown }).error) {
    return { kind: "error", transient: true };
  }
  const point = esriMatchPoint(body);
  return point ? { kind: "hit", point } : { kind: "miss" };
}

async function queryNominatim(address: string, fetchImpl: FetchLike, timeoutMs: number): Promise<Outcome> {
  const url = new URL(NOMINATIM_URL);
  url.searchParams.set("q", address);
  url.searchParams.set("format", "jsonv2");
  url.searchParams.set("addressdetails", "1");
  url.searchParams.set("countrycodes", "us");
  url.searchParams.set("limit", "1");
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
  if (response.kind !== "response") return { kind: "error", transient: true };
  if (!response.response.ok) return { kind: "error", transient: transientStatus(response.response.status) };
  const body = await readJson(response.response);
  if (!Array.isArray(body)) return { kind: "error", transient: true };
  const point = nominatimMatchPoint(body);
  return point ? { kind: "hit", point } : { kind: "miss" };
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
