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

export const DAVIDSON_WEBPRO_URL = "https://portal.padctn.org/OFS/WP/PropertySearch/QuickSearch";

export function davidsonParcelViewerUrl(parcelId: string): string {
  return `https://maps.nashville.gov/ParcelViewer/?parcelID=${encodeURIComponent(parcelId)}`;
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
};

export function parcelAppraiserUrl(options: {
  parcelId: string;
  countyFips?: string | null;
  appraiserUrl?: string | null;
}): { href: string; label: string } {
  const fips = options.countyFips ?? null;
  if (fips === "47037") {
    return {
      href: options.appraiserUrl || davidsonParcelViewerUrl(options.parcelId),
      label: "Open in Metro Nashville Parcel Viewer",
    };
  }
  if (fips === "12095" || (!fips && !options.appraiserUrl)) {
    return {
      href: ocpaParcelUrl(options.parcelId),
      label: "Open in Orange County Property Appraiser",
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
                    : "county";
  return {
    href,
    label: fips === "12095" ? "Open in Orange County Property Appraiser" : `Open ${countyLabel} Property Appraiser search`,
  };
}

export function parcelPublicLinks(options: {
  parcelId: string;
  countyFips?: string | null;
  appraiserUrl?: string | null;
}): { href: string; label: string }[] {
  if (options.countyFips === "47037") {
    const viewer = parcelAppraiserUrl(options);
    return [
      viewer,
      { href: DAVIDSON_WEBPRO_URL, label: "Open Davidson County Assessor (WebPro)" },
    ];
  }
  return [parcelAppraiserUrl(options)];
}

export function formatParcelPlace(options: {
  situsCity?: string | null;
  situsZip?: string | null;
  countyName?: string | null;
  state?: string | null;
}): string {
  const cityZip = [options.situsCity, options.situsZip].filter(Boolean).join(" ");
  if (!options.state || options.state === "Florida") {
    return cityZip || (options.countyName ? `${options.countyName} County, FL` : "Florida");
  }
  const region = options.countyName ? `${options.countyName} County, ${options.state}` : options.state;
  return cityZip ? `${cityZip} · ${region}` : region;
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
