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

const COUNTY_SEARCH: Record<string, { href: string; county: string }> = {
  "12009": { href: "https://www.bcpao.us/PropertySearch/#/nav/Search", county: "Brevard" },
  "12069": { href: "https://www.lakecopropappr.com/", county: "Lake" },
  "12083": { href: "https://www.pa.marion.fl.us/", county: "Marion" },
  "12095": { href: "https://ocpaweb.ocpafl.org/site/parcelsearch", county: "Orange" },
  "12097": { href: "https://www.property-appraiser.org/", county: "Osceola" },
  "12105": { href: "https://www.polkpa.org/", county: "Polk" },
  "12117": { href: "https://www.scpafl.org/", county: "Seminole" },
  "12119": { href: "https://www.sumterpa.com/", county: "Sumter" },
  "12127": { href: "https://vcpa.vcgov.org/", county: "Volusia" },
  "01073": { href: "https://eringcapture.jccal.org/propsearch", county: "Jefferson" },
  "01115": { href: "https://isv.kcsgis.com/al.stclair_revenue/", county: "St. Clair" },
  "01117": { href: "https://ptc.shelbyal.com/propsearch", county: "Shelby" },
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
  const known = fips ? COUNTY_SEARCH[fips] : undefined;
  const href = options.appraiserUrl || known?.href || ocpaParcelUrl(options.parcelId);
  return {
    href,
    label: `Open ${known?.county ?? "county"} Property Appraiser search`,
  };
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
