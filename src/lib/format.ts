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
  "13089": "https://propertyappraisal.dekalbcountyga.gov/",
};

/**
 * County property-appraiser homepages. Parcel-id deep links exist only where the
 * county site supports them (Orange). A missing county stays a gap — never a
 * link to a different county's appraiser.
 */
const APPRAISER_LINKS: Record<string, { href: string; label: string }> = {
  "12009": { href: DEFAULT_APPRAISER_URLS["12009"], label: "Open Brevard Property Appraiser search" },
  "12031": { href: "https://www.coj.net/departments/property-appraiser", label: "Open Duval County Property Appraiser" },
  "12057": { href: "https://www.hcpafl.org/", label: "Open Hillsborough County Property Appraiser" },
  "12069": { href: DEFAULT_APPRAISER_URLS["12069"], label: "Open Lake Property Appraiser search" },
  "12083": { href: DEFAULT_APPRAISER_URLS["12083"], label: "Open Marion Property Appraiser search" },
  "12091": { href: "https://www.okaloosapa.com/", label: "Open Okaloosa County Property Appraiser" },
  "12095": { href: "https://ocpaweb.ocpafl.org/site/parcelsearch", label: "Open in Orange County Property Appraiser" },
  "12097": { href: DEFAULT_APPRAISER_URLS["12097"], label: "Open Osceola Property Appraiser search" },
  "12101": { href: "https://www.pascopa.com/", label: "Open Pasco County Property Appraiser" },
  "12103": { href: "https://www.pcpao.gov/", label: "Open Pinellas County Property Appraiser" },
  "12105": { href: DEFAULT_APPRAISER_URLS["12105"], label: "Open Polk Property Appraiser search" },
  "12111": { href: "https://www.paslc.gov/", label: "Open St. Lucie County Property Appraiser" },
  "12115": { href: "https://www.sc-pa.com/", label: "Open Sarasota County Property Appraiser" },
  "12117": { href: DEFAULT_APPRAISER_URLS["12117"], label: "Open Seminole Property Appraiser search" },
  "12119": { href: DEFAULT_APPRAISER_URLS["12119"], label: "Open Sumter Property Appraiser search" },
  "12127": { href: DEFAULT_APPRAISER_URLS["12127"], label: "Open Volusia Property Appraiser search" },
  "13089": { href: DEFAULT_APPRAISER_URLS["13089"], label: "Open DeKalb Property Appraiser search" },
};

export function parcelAppraiserUrl(options: {
  parcelId: string;
  countyFips?: string | null;
  appraiserUrl?: string | null;
}): { href: string | null; label: string } {
  const fips = options.countyFips ?? null;
  if (options.appraiserUrl) {
    return { href: options.appraiserUrl, label: "Open county property appraiser" };
  }
  if (fips === "12095") {
    return { href: ocpaParcelUrl(options.parcelId), label: "Open in Orange County Property Appraiser" };
  }
  // Orange County pilot parcels omit FIPS. Do not send a known other-county parcel to OCPA.
  if (!fips) {
    return { href: ocpaParcelUrl(options.parcelId), label: "Open in Orange County Property Appraiser" };
  }
  const known = APPRAISER_LINKS[fips];
  if (known) return known;
  return {
    href: null,
    label: "No county property-appraiser search is cataloged for this parcel. The mailing address above is the public contact path.",
  };
}

const ENTITY_SEARCH: Record<string, { label: string; href: (name: string) => string; prefilled: boolean }> = {
  FL: {
    label: "Search Florida Sunbiz for this entity",
    href: (name) => sunbizSearchUrl(name),
    prefilled: true,
  },
  GA: {
    label: "Georgia Secretary of State business search",
    href: () => "https://ecorp.sos.ga.gov/BusinessSearch",
    prefilled: false,
  },
  NC: {
    label: "North Carolina Secretary of State business search",
    href: (name) =>
      `https://www.sosnc.gov/online_services/search/Business_Registration_Results?SearchCriteria=${encodeURIComponent(name)}`,
    prefilled: true,
  },
  SC: {
    label: "South Carolina business entity search",
    href: () => "https://businessfilings.sc.gov/BusinessFiling/Entity/Search",
    prefilled: false,
  },
  TN: {
    label: "Tennessee Secretary of State business search",
    href: () => "https://tncab.tnsos.gov/business-entity-search",
    prefilled: false,
  },
  AL: {
    label: "Alabama Secretary of State business entity search",
    href: () => "https://www.sos.alabama.gov/government-records/business-entity-records",
    prefilled: false,
  },
};

const STATE_CODES: Record<string, string> = {
  fl: "FL",
  florida: "FL",
  ga: "GA",
  georgia: "GA",
  nc: "NC",
  "north carolina": "NC",
  sc: "SC",
  "south carolina": "SC",
  tn: "TN",
  tennessee: "TN",
  al: "AL",
  alabama: "AL",
};

export function entitySearchLink(
  state: string | null | undefined,
  name: string,
  countyFips?: string | null,
): { href: string; label: string; prefilled: boolean } | null {
  const code =
    STATE_CODES[(state ?? "").trim().toLowerCase()] ??
    (countyFips?.startsWith("12") || !countyFips ? "FL" : null);
  if (!code) return null;
  const entry = ENTITY_SEARCH[code];
  if (!entry) return null;
  return { href: entry.href(name), label: entry.label, prefilled: entry.prefilled };
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

export function formatParcelPlace(properties: {
  situsCity?: string | null;
  situsZip?: string | null;
  countyName?: string | null;
  state?: string | null;
}): string {
  const cityZip = [properties.situsCity, properties.situsZip].filter(Boolean).join(" ");
  if (cityZip) return cityZip;
  if (properties.countyName) {
    const stateLabel =
      properties.state === "Georgia" ? "Georgia" : properties.state && properties.state !== "Florida" ? properties.state : "FL";
    return `${properties.countyName} County, ${stateLabel}`;
  }
  return properties.state || "Florida";
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
