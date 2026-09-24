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

export function osceolaParcelUrl(parcelId: string): string {
  return `https://maps.property-appraiser.org/?Pin=${encodeURIComponent(parcelId)}`;
}

export function lakeAppraiserUrl(url: string): string {
  return url.replace(/^http:\/\/www\.lakecopropappr\.com/i, "https://www.lakecopropappr.com");
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
  if (fips === "12097") {
    const stored = options.appraiserUrl;
    return {
      href: stored && stored.includes("Pin=") ? stored : osceolaParcelUrl(options.parcelId),
      label: "Open Osceola Property Appraiser map",
    };
  }
  if (fips === "12069" && options.appraiserUrl) {
    return {
      href: lakeAppraiserUrl(options.appraiserUrl),
      label: "Open Lake County Property Appraiser record",
    };
  }
  if (fips === "12119" && options.appraiserUrl?.includes("sumterpa.com")) {
    return {
      href: options.appraiserUrl,
      label: "Open Sumter Property Appraiser record",
    };
  }
  const href = options.appraiserUrl || (fips ? DEFAULT_APPRAISER_URLS[fips] : null) || ocpaParcelUrl(options.parcelId);
  const countyLabel =
    fips === "12009"
      ? "Brevard"
      : fips === "12069"
        ? "Lake"
        : fips === "12083"
          ? "Marion"
          : fips === "12097"
            ? "Osceola"
            : fips === "12105"
              ? "Polk"
              : fips === "12117"
                ? "Seminole"
                : fips === "12119"
                  ? "Sumter"
                  : fips === "12127"
                    ? "Volusia"
                    : fips === "13089"
                      ? "DeKalb"
                      : "county";
  return {
    href,
    label: fips === "12095" ? "Open in Orange County Property Appraiser" : `Open ${countyLabel} Property Appraiser search`,
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
