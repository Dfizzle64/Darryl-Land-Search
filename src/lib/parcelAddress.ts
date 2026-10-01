export type ParcelAddressHit = {
  lng: number;
  lat: number;
  label: string;
  city: string;
  zip: string;
  state: string;
};

export type ParsedAddress = {
  number: string | null;
  street: string | null;
  city: string | null;
  state: string | null;
  zip: string | null;
};

const SUFFIX: Record<string, string> = {
  STREET: "ST",
  AVENUE: "AVE",
  AVE: "AVE",
  ROAD: "RD",
  RD: "RD",
  DRIVE: "DR",
  DR: "DR",
  LANE: "LN",
  LN: "LN",
  BOULEVARD: "BLVD",
  BLVD: "BLVD",
  COURT: "CT",
  CT: "CT",
  PLACE: "PL",
  PL: "PL",
  CIRCLE: "CIR",
  CIR: "CIR",
  WAY: "WAY",
  TRAIL: "TRL",
  TRL: "TRL",
  PARKWAY: "PKWY",
  PKWY: "PKWY",
  HIGHWAY: "HWY",
  HWY: "HWY",
  TERRACE: "TER",
  TER: "TER",
  PIKE: "PIKE",
  ALLEY: "ALY",
  ALY: "ALY",
};

const STATE_BY_NAME: Record<string, string> = {
  alabama: "AL",
  alaska: "AK",
  arizona: "AZ",
  arkansas: "AR",
  california: "CA",
  colorado: "CO",
  connecticut: "CT",
  delaware: "DE",
  "district of columbia": "DC",
  florida: "FL",
  georgia: "GA",
  hawaii: "HI",
  idaho: "ID",
  illinois: "IL",
  indiana: "IN",
  iowa: "IA",
  kansas: "KS",
  kentucky: "KY",
  louisiana: "LA",
  maine: "ME",
  maryland: "MD",
  massachusetts: "MA",
  michigan: "MI",
  minnesota: "MN",
  mississippi: "MS",
  missouri: "MO",
  montana: "MT",
  nebraska: "NE",
  nevada: "NV",
  "new hampshire": "NH",
  "new jersey": "NJ",
  "new mexico": "NM",
  "new york": "NY",
  "north carolina": "NC",
  "north dakota": "ND",
  ohio: "OH",
  oklahoma: "OK",
  oregon: "OR",
  pennsylvania: "PA",
  "rhode island": "RI",
  "south carolina": "SC",
  "south dakota": "SD",
  tennessee: "TN",
  texas: "TX",
  utah: "UT",
  vermont: "VT",
  virginia: "VA",
  washington: "WA",
  "west virginia": "WV",
  wisconsin: "WI",
  wyoming: "WY",
};

const STATE_ABBR = new Set(Object.values(STATE_BY_NAME));
const STATE_NAMES = Object.keys(STATE_BY_NAME).sort((a, b) => b.length - a.length);

/** Two-letter postal abbreviation, or null when the text is not a state. */
export function stateAbbr(value: string | null | undefined): string | null {
  if (!value) return null;
  const text = value.trim().toLowerCase().replace(/\./g, "");
  if (!text) return null;
  if (text.length === 2 && STATE_ABBR.has(text.toUpperCase())) return text.toUpperCase();
  return STATE_BY_NAME[text] ?? null;
}

/**
 * House number plus a canonical street. "3874 Campbellsville Pike" and
 * "CAMPBELLSVILLE PIKE 3874" share a key. Street suffixes collapse to USPS form.
 */
function streetTokens(line: string): string[] {
  return line.toUpperCase().match(/[A-Z0-9]+/g) ?? [];
}

function withSuffix(tokens: string[]): string {
  if (!tokens.length) return "";
  const next = tokens.slice();
  const last = next[next.length - 1];
  if (SUFFIX[last]) next[next.length - 1] = SUFFIX[last];
  return next.join(" ");
}

export function canonicalStreet(line: string): { number: string | null; street: string | null } {
  const tokens = streetTokens(line);
  if (!tokens.length) return { number: null, street: null };
  let number: string | null = null;
  if (/^\d+$/.test(tokens[0])) number = tokens.shift() ?? null;
  else if (/^\d+$/.test(tokens[tokens.length - 1] ?? "")) number = tokens.pop() ?? null;
  else return { number: null, street: null };
  const street = withSuffix(tokens);
  return { number, street: street || null };
}

/** Street name only, for county layers that store the house number in another field. */
export function canonicalStreetName(line: string): string | null {
  const street = withSuffix(streetTokens(line));
  return street || null;
}

export function parseAddressQuery(input: string): ParsedAddress {
  const cleaned = input.trim().replace(/\s+/g, " ");
  const parts = cleaned.split(",").map((part) => part.trim()).filter(Boolean);
  const streetLine = parts[0] ?? cleaned;
  const rest = parts.slice(1).join(" ");
  const zip = rest.match(/\b(\d{5})(?:-\d{4})?\b/)?.[1] ?? null;
  const state = stateInText(rest);
  let city = rest;
  if (zip) city = city.replace(new RegExp(`\\b${zip}(?:-\\d{4})?\\b`), " ");
  if (state) {
    city = city.replace(new RegExp(`\\b${state}\\b`, "i"), " ");
    const name = STATE_NAMES.find((item) => stateAbbr(item) === state);
    if (name) city = city.replace(new RegExp(`\\b${name}\\b`, "i"), " ");
  }
  city = city.replace(/[^a-z0-9]+/gi, " ").replace(/\s+/g, " ").trim();
  const street = canonicalStreet(streetLine);
  return { ...street, city: city || null, state, zip };
}

export function parcelIndexKey(number: string, street: string): string {
  return `${number}\t${street}`;
}

/** Tab-separated rows: number, street, city, zip, lng, lat. */
export function findParcelHits(text: string, query: string): ParcelAddressHit[] {
  const parsed = parseAddressQuery(query);
  if (!parsed.state || !parsed.number || !parsed.street) return [];
  const prefix = `${parcelIndexKey(parsed.number, parsed.street)}\t`;
  const hits: ParcelAddressHit[] = [];
  let start = lineStart(text, prefix);
  while (start !== -1) {
    const end = text.indexOf("\n", start);
    const line = text.slice(start, end === -1 ? text.length : end);
    if (!line.startsWith(prefix)) break;
    const hit = hitFromLine(line, parsed.state);
    if (hit) {
      const cityOk = !parsed.city || (hit.city && normalizePlace(hit.city) === normalizePlace(parsed.city));
      const zipOk = !parsed.zip || !hit.zip || hit.zip === parsed.zip;
      if (cityOk && zipOk) hits.push(hit);
    }
    if (hits.length >= 5 || end === -1) break;
    start = end + 1;
  }
  return hits;
}

function lineStart(text: string, prefix: string): number {
  let from = 0;
  while (from < text.length) {
    const at = text.indexOf(prefix, from);
    if (at === -1) return -1;
    if (at === 0 || text.charCodeAt(at - 1) === 10) return at;
    from = at + 1;
  }
  return -1;
}

export function formatParcelLabel(hit: Pick<ParcelAddressHit, "label" | "city" | "state" | "zip">): string {
  return [hit.label, hit.city, [hit.state, hit.zip].filter(Boolean).join(" ")].filter(Boolean).join(", ");
}

function hitFromLine(line: string, state: string): ParcelAddressHit | null {
  const [number, street, city, zip, lngText, latText] = line.split("\t");
  const lng = Number(lngText);
  const lat = Number(latText);
  if (!number || !street || !Number.isFinite(lng) || !Number.isFinite(lat)) return null;
  const label = `${number} ${street}`;
  return { lng, lat, label, city: city ?? "", zip: zip ?? "", state };
}

function stateInText(text: string): string | null {
  const lower = text.toLowerCase();
  for (const name of STATE_NAMES) {
    if (new RegExp(`\\b${name}\\b`, "i").test(lower)) return STATE_BY_NAME[name];
  }
  const abbr = text.toUpperCase().match(/\b[A-Z]{2}\b/g) ?? [];
  for (let i = abbr.length - 1; i >= 0; i -= 1) {
    if (STATE_ABBR.has(abbr[i])) return abbr[i];
  }
  return null;
}

function normalizePlace(value: string): string {
  return value.toUpperCase().replace(/[^A-Z0-9]+/g, " ").replace(/\s+/g, " ").trim();
}
