const ENTITY_RE = /\b(LLC|L\.L\.C|INC|INCORPORATED|LP|L\.P|LLP|CORP|CORPORATION|LTD|TRUST|HOLDINGS|PARTNERS|COMPANY|CO)\b/i;

export function isEntityOwner(name: string | null | undefined): boolean {
  return Boolean(name && ENTITY_RE.test(name));
}

export function sunbizSearchUrl(name: string): string {
  const term = name.replace(/[.,]/g, " ").replace(/\s+/g, " ").trim();
  return `https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults?inquiryType=EntityName&searchTerm=${encodeURIComponent(term)}`;
}

export function ocpaParcelUrl(parcelId: string): string {
  return `https://ocpaweb.ocpafl.org/site/parcelsearch?pid=${encodeURIComponent(parcelId)}`;
}

export function comptrollerRecordsUrl(): string {
  return "https://or.occompt.com/recorder/web/";
}

const DEFAULT_APPRAISER_URLS: Record<string, string> = {
  "12009": "https://www.bcpao.us/PropertySearch/#/nav/Search",
  "12069": "https://www.lakecopropappr.com/",
  "12083": "https://www.pa.marion.fl.us/",
  "12095": "https://ocpaweb.ocpafl.org/site/parcelsearch",
  "12097": "https://www.property-appraiser.org/",
  "12105": "https://www.polkpa.org/",
  "12117": "https://www.scpafl.org/",
  "12119": "https://www.sumterpa.com/",
  "12127": "https://vcpa.vcgov.org/",
  "45015": "https://assessor.berkeleycountysc.gov/prop_card_search.php",
  "45019": "https://gisccweb.charlestoncounty.org/public_search/",
  "45035":
    "https://www.dorchestercountysc.gov/government/property-tax-services/assessor/real-estate-mobile-home-search/cama-property-lookup",
};

const APPRAISER_LABELS: Record<string, string> = {
  "12009": "Brevard",
  "12069": "Lake",
  "12083": "Marion",
  "12095": "Orange",
  "12097": "Osceola",
  "12105": "Polk",
  "12117": "Seminole",
  "12119": "Sumter",
  "12127": "Volusia",
  "45015": "Berkeley County",
  "45019": "Charleston County",
  "45035": "Dorchester County",
};

export function parcelAppraiserUrl(options: {
  parcelId: string;
  countyFips?: string | null;
  appraiserUrl?: string | null;
}): { href: string; label: string } {
  const fips = options.countyFips ?? null;
  if (fips === "12095" || (!fips && !options.appraiserUrl)) {
    return {
      href: ocpaParcelUrl(options.parcelId),
      label: "Open in Orange County Property Appraiser",
    };
  }
  const href = options.appraiserUrl || (fips ? DEFAULT_APPRAISER_URLS[fips] : null) || ocpaParcelUrl(options.parcelId);
  const countyLabel = (fips && APPRAISER_LABELS[fips]) || "county";
  return {
    href,
    label:
      fips === "12095"
        ? "Open in Orange County Property Appraiser"
        : `Open ${countyLabel} Property Appraiser search`,
  };
}

function stateAbbrev(state: string | null | undefined, countyFips: string | null | undefined): string | null {
  if (state === "Florida" || state === "FL") return "FL";
  if (state === "South Carolina" || state === "SC") return "SC";
  if (state === "North Carolina" || state === "NC") return "NC";
  if (state === "Georgia" || state === "GA") return "GA";
  if (state === "Tennessee" || state === "TN") return "TN";
  if (state === "Alabama" || state === "AL") return "AL";
  if (state === "Mississippi" || state === "MS") return "MS";
  if (state === "Arkansas" || state === "AR") return "AR";
  if (state && state.length === 2) return state.toUpperCase();
  if (state) return state;
  if (countyFips?.startsWith("12")) return "FL";
  if (countyFips?.startsWith("45")) return "SC";
  return null;
}

/** City and ZIP when present, otherwise county and state. Florida is not assumed. */
export function formatParcelPlace(properties: {
  situsCity: string | null;
  situsZip: string | null;
  countyName?: string | null;
  state?: string | null;
  countyFips?: string | null;
}): string {
  const cityZip = [properties.situsCity, properties.situsZip].filter(Boolean).join(" ");
  if (cityZip) return cityZip;
  const state = stateAbbrev(properties.state, properties.countyFips);
  if (properties.countyName && state) return `${properties.countyName} County, ${state}`;
  if (properties.countyName) return `${properties.countyName} County`;
  return state ?? "Location not available";
}

/** Sunbiz is a Florida entity search. Other states stay on the assessor link. */
export function showFloridaSunbiz(countyFips?: string | null, state?: string | null): boolean {
  if (state === "Florida" || state === "FL") return true;
  if (countyFips?.startsWith("12")) return true;
  return !state && !countyFips;
}

export function formatUsd(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "Not available";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "Not available";
  return new Intl.NumberFormat("en-US").format(Math.round(value));
}

export function formatAcres(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "Not available";
  return `${value.toLocaleString("en-US", { maximumFractionDigits: 2 })} ac`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Not available";
  const [year, month, day] = value.split("-");
  if (!year || !month || !day) return value;
  return `${month}/${day}/${year}`;
}

export function formatSale(sale: { date: string | null; price: number | null }): string {
  if (!sale.date && (sale.price == null || sale.price <= 0)) return "Not available";
  const date = sale.date ? formatDate(sale.date) : null;
  const price = sale.price != null && sale.price > 0 ? formatUsd(sale.price) : null;
  if (date && price) return `${date}\n${price}`;
  return date ?? price ?? "Not available";
}

export function formatMailing(address: {
  line1: string | null;
  line2: string | null;
  city: string | null;
  state: string | null;
  zip: string | null;
}): string | null {
  const lines = [address.line1, address.line2, [address.city, address.state, address.zip].filter(Boolean).join(" ")]
    .map((line) => line?.trim())
    .filter((line): line is string => Boolean(line));
  return lines.length ? lines.join("\n") : null;
}

export function formatRoadLabel(road: {
  from: string | null;
  to: string | null;
  roadwayId: string | null;
} | null): string {
  if (!road) return "Not available";
  if (road.from && road.to) return `${road.from} → ${road.to}`;
  if (road.from) return road.from;
  if (road.roadwayId) return `FDOT ${road.roadwayId}`;
  return "Nearest FDOT count segment";
}
