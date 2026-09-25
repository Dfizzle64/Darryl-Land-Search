import { flRestAppraiserLink } from "./flRestBatch1";
import { southFloridaAppraiserLink } from "./southFlorida";

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

/** Alt Key embedded in a Lake Property Appraiser record URL. Not the Parcel Number. */
export function lakeAltKey(url: string | null | undefined): string | null {
  if (!url) return null;
  const match = url.match(/[?&]AltKey=([^&]+)/i);
  if (!match) return null;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return match[1];
  }
}

/**
 * What the county calls the id stored on `parcelId`.
 * Lake's shelf field is ParcelNumber; the PA record is opened with Alt Key.
 */
const PARCEL_ID_LABELS: Record<string, string> = {
  "12011": "Folio",
  "12023": "Parcel Number",
  "12035": "Parcel Number",
  "12069": "Parcel Number",
  "12086": "Folio",
  "12087": "RE Number",
  "12095": "Parcel ID",
  "12097": "PIN",
  "12105": "Parcel ID",
  "12117": "Parcel ID",
  "12125": "PIN",
  "13013": "Parcel Number",
  "13089": "Parcel ID",
  "37021": "PIN",
  "47011": "Parcel ID",
};

export function parcelIdLabel(countyFips?: string | null): string {
  if (!countyFips) return "Parcel ID";
  return PARCEL_ID_LABELS[countyFips] ?? "Parcel ID";
}

export const APPRAISER_UNAVAILABLE = "Property appraiser not available";

export function comptrollerRecordsUrl(): string {
  return "https://or.occompt.com/recorder/web/";
}

const DEFAULT_APPRAISER_URLS: Record<string, string> = {
  "12009": "https://www.bcpao.us/PropertySearch/#/nav/Search",
  "12061": "https://www.ircpa.org/",
  "12069": "https://www.lakecopropappr.com/",
  "12083": "https://www.pa.marion.fl.us/",
  "12085": "https://www.pamartinfl.gov/",
  "12093": "https://www.okeechobeepa.com/gis/",
  "12095": "https://ocpaweb.ocpafl.org/site/parcelsearch",
  "12097": "https://www.property-appraiser.org/",
  "12105": "https://www.polkpa.org/",
  "12111": "https://www.paslc.gov/",
  "12117": "https://www.scpafl.org/",
  "12119": "https://www.sumterpa.com/",
  "12127": "https://vcpa.vcgov.org/",
  "12001": "https://www.acpafl.org/",
  "12007": "https://www.bradfordappraiser.com/",
  "12017": "https://www.citruspa.org/",
  "12041": "https://www.qpublic.net/fl/gilchrist/",
  "12053": "https://hernandocountypa-florida.us/",
  "12075": "https://www.qpublic.net/fl/levy/",
  "12107": "https://pa.putnam-fl.com/",
  "13013": "https://qpublic.schneidercorp.com/Application.aspx?AppID=635&LayerID=11218&PageTypeID=2&PageID=0",
  "13077": "https://qpublic.schneidercorp.com/Application.aspx?AppID=704&LayerID=11412&PageTypeID=1",
  "13089": "https://propertyappraisal.dekalbcountyga.gov/",
  "01003": "https://isv.kcsgis.com/al.baldwin_revenue/",
  "01095": "https://isv.kcsgis.com/al.marshall_revenue/",
  "01117": "https://ptc.shelbyal.com/propsearch",
  "13045": "https://qpublic.schneidercorp.com/Application.aspx?AppID=663&LayerID=15076&PageTypeID=1",
  "13297": "https://qpublic.schneidercorp.com/Application.aspx?App=waltonCountyGA&Layer=Parcels&PageType=Search",
  "13217": "https://qpublic.schneidercorp.com/Application.aspx?App=NewtonCountyGA&Layer=Parcels&PageType=Search",
  "13255": "https://qpublic.schneidercorp.com/Application.aspx?AppID=766&PageTypeID=2",
  "13029": "https://qpublic.net/ga/bryan/",
  "13103": "https://qpublic.schneidercorp.com/Application.aspx?App=EffinghamCountyGA&Layer=Parcels&PageType=Search",
  "13185": "https://qpublic.schneidercorp.com/Application.aspx?App=LowndesCountyGA&Layer=Parcels&PageType=Search",
  "13021": "https://qpublic.schneidercorp.com/Application.aspx?App=BibbCountyGA&Layer=Parcels&PageType=Search",
  "13059": "https://qpublic.schneidercorp.com/Application.aspx?App=ClarkeCountyGA&Layer=Parcels&PageType=Search",
  "45013": "https://sc-beaufort.publicaccessnow.com/Searches/Real.aspx",
  "28121": "https://www.deltacomputersystems.com/ms/ms61/plinkquerym.html",
  "28089": "https://www.madison-co.com/elected-offices/tax-assessor/real-property-search",
  "28049": "https://www.co.hinds.ms.us/pgs/apps/landroll_query.asp",
  "28029": "https://cmpdd.org/maps/",
  "28127": "https://cmpdd.org/maps/",
  "28149": "https://cmpdd.org/maps/",
  "28163": "https://cmpdd.org/maps/",
  "47011": "https://assessment.cot.tn.gov/tpad/",
  "37089": "https://lrcpwa.ncptscloud.com/henderson/parcel-search",
};

/**
 * County property-appraiser homepages. Parcel-id deep links exist only where the
 * county site supports them (Orange). A missing county stays a gap — never a
 * link to a different county's appraiser.
 */
const APPRAISER_LINKS: Record<string, { href: string; label: string }> = {
  "12009": { href: DEFAULT_APPRAISER_URLS["12009"], label: "Open Brevard Property Appraiser search" },
  "12031": { href: "https://www.coj.net/departments/property-appraiser", label: "Open Duval County Property Appraiser" },
  "12061": { href: DEFAULT_APPRAISER_URLS["12061"], label: "Open Indian River County Property Appraiser" },
  "12057": { href: "https://www.hcpafl.org/", label: "Open Hillsborough County Property Appraiser" },
  "12069": { href: DEFAULT_APPRAISER_URLS["12069"], label: "Open Lake Property Appraiser search" },
  "12083": { href: DEFAULT_APPRAISER_URLS["12083"], label: "Open Marion Property Appraiser search" },
  "12085": { href: DEFAULT_APPRAISER_URLS["12085"], label: "Open Martin County property record" },
  "12093": { href: DEFAULT_APPRAISER_URLS["12093"], label: "Open Okeechobee County Property Appraiser GIS" },
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
  "12001": { href: DEFAULT_APPRAISER_URLS["12001"], label: "Open Alachua Property Appraiser search" },
  "12007": { href: DEFAULT_APPRAISER_URLS["12007"], label: "Open Bradford Property Appraiser search" },
  "12017": { href: DEFAULT_APPRAISER_URLS["12017"], label: "Open Citrus Property Appraiser search" },
  "12041": { href: DEFAULT_APPRAISER_URLS["12041"], label: "Open Gilchrist Property Appraiser search" },
  "12053": { href: DEFAULT_APPRAISER_URLS["12053"], label: "Open Hernando Property Appraiser search" },
  "12075": { href: DEFAULT_APPRAISER_URLS["12075"], label: "Open Levy Property Appraiser search" },
  "12107": { href: DEFAULT_APPRAISER_URLS["12107"], label: "Open Putnam Property Appraiser search" },
  "01003": { href: DEFAULT_APPRAISER_URLS["01003"], label: "Open Baldwin County revenue search" },
  "01095": { href: DEFAULT_APPRAISER_URLS["01095"], label: "Open Marshall County revenue search" },
  "01117": { href: DEFAULT_APPRAISER_URLS["01117"], label: "Open Shelby County property search" },
  "13013": { href: DEFAULT_APPRAISER_URLS["13013"], label: "Open Barrow County qPublic search" },
  "13077": { href: DEFAULT_APPRAISER_URLS["13077"], label: "Open Coweta County property appraiser (qPublic)" },
  "13089": { href: DEFAULT_APPRAISER_URLS["13089"], label: "Open DeKalb Property Appraiser search" },
  "13045": { href: DEFAULT_APPRAISER_URLS["13045"], label: "Open Carroll County qPublic search" },
  "13297": { href: DEFAULT_APPRAISER_URLS["13297"], label: "Open Walton Property Appraiser search" },
  "13217": { href: DEFAULT_APPRAISER_URLS["13217"], label: "Open Newton County qPublic search" },
  "13255": { href: DEFAULT_APPRAISER_URLS["13255"], label: "Open Spalding County qPublic search" },
  "13029": { href: DEFAULT_APPRAISER_URLS["13029"], label: "Open Bryan County qPublic search" },
  "13103": { href: DEFAULT_APPRAISER_URLS["13103"], label: "Open Effingham County qPublic search" },
  "13185": { href: DEFAULT_APPRAISER_URLS["13185"], label: "Open Lowndes County qPublic search" },
  "13021": { href: DEFAULT_APPRAISER_URLS["13021"], label: "Open Bibb County qPublic search" },
  "13059": { href: DEFAULT_APPRAISER_URLS["13059"], label: "Open Clarke County qPublic search" },
  "45013": { href: DEFAULT_APPRAISER_URLS["45013"], label: "Open Beaufort County property search" },
  "28121": { href: DEFAULT_APPRAISER_URLS["28121"], label: "Open Rankin County property search" },
  "28089": { href: DEFAULT_APPRAISER_URLS["28089"], label: "Open Madison County, Mississippi property search" },
  "28049": { href: DEFAULT_APPRAISER_URLS["28049"], label: "Open Hinds County land roll search" },
  "28029": { href: DEFAULT_APPRAISER_URLS["28029"], label: "Open CMPDD maps" },
  "28127": { href: DEFAULT_APPRAISER_URLS["28127"], label: "Open CMPDD maps" },
  "28149": { href: DEFAULT_APPRAISER_URLS["28149"], label: "Open CMPDD maps" },
  "28163": { href: DEFAULT_APPRAISER_URLS["28163"], label: "Open CMPDD maps" },
  "47011": { href: DEFAULT_APPRAISER_URLS["47011"], label: "Open Bradley County parcel in TPAD" },
  "37089": { href: DEFAULT_APPRAISER_URLS["37089"], label: "Open Henderson County property appraiser" },
};

export function parcelAppraiserUrl(options: {
  parcelId: string;
  countyFips?: string | null;
  appraiserUrl?: string | null;
}): { href: string | null; label: string } {
  const fips = options.countyFips ?? null;
  const southFlorida = southFloridaAppraiserLink(fips, options.parcelId, options.appraiserUrl);
  if (southFlorida) return southFlorida;
  const flRest = flRestAppraiserLink(fips, options.parcelId);
  if (flRest) return flRest;
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
      label: "Lake County Property Appraiser",
    };
  }
  if (fips === "12069") {
    return {
      href: DEFAULT_APPRAISER_URLS["12069"],
      label: "Lake County Property Appraiser search",
    };
  }
  if (fips === "12119" && options.appraiserUrl?.includes("sumterpa.com")) {
    return {
      href: options.appraiserUrl,
      label: "Open Sumter Property Appraiser record",
    };
  }
  const named = fips ? APPRAISER_LINKS[fips] : undefined;
  if (fips === "37021" || options.appraiserUrl?.includes("prc-buncombe.spatialest.com")) {
    return {
      href: options.appraiserUrl || `https://prc-buncombe.spatialest.com/#/property/${encodeURIComponent(options.parcelId)}`,
      label: "Open Buncombe property card",
    };
  }
  if (fips === "13013") {
    return {
      href: options.appraiserUrl || named?.href || null,
      label: options.appraiserUrl ? "Open this parcel in Barrow County qPublic" : named?.label || "Open Barrow County qPublic search",
    };
  }
  if (fips === "13045") {
    return {
      href: options.appraiserUrl || named?.href || null,
      label: "Open Carroll County qPublic",
    };
  }
  if (fips === "13297") {
    return {
      href: options.appraiserUrl || named?.href || null,
      label: named?.label || "Open Walton Property Appraiser search",
    };
  }
  if (fips === "47011") {
    return {
      href: options.appraiserUrl || named?.href || null,
      label: "Open Bradley County parcel in TPAD",
    };
  }
  if (
    fips === "13217" ||
    fips === "13255" ||
    fips === "13029" ||
    fips === "13103" ||
    fips === "13185" ||
    fips === "13021" ||
    fips === "13059" ||
    fips === "45013" ||
    fips === "28121" ||
    fips === "28089" ||
    fips === "28049" ||
    fips === "28029" ||
    fips === "28127" ||
    fips === "28149" ||
    fips === "28163"
  ) {
    return {
      href: options.appraiserUrl || named?.href || null,
      label: named?.label || "Open county property appraiser",
    };
  }
  if (fips === "37089" || fips === "13077") {
    return {
      href: options.appraiserUrl || named?.href || null,
      label: named?.label || "Open county property appraiser",
    };
  }
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
    label: APPRAISER_UNAVAILABLE,
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

export function formatSale(sale: { date: string | null; price: number | null }): string | null {
  if (!sale.date && (sale.price == null || sale.price <= 0)) return null;
  const date = sale.date ? formatDate(sale.date) : null;
  const price = sale.price != null && sale.price > 0 ? formatUsd(sale.price) : null;
  if (date && price) return `${date}\n${price}`;
  return date ?? price;
}

/**
 * Honest empty states for public parcel rows. These sentences describe a gap
 * in the extract. They are not a zoning code and not an IRS designation.
 */
export function missingPublicParcelValue(
  field: "propertyName" | "situs" | "sale" | "saleQualified" | "zoning" | "designatedOz",
  countyFips?: string | null,
): string {
  if (field === "propertyName") return "No property name on this public parcel row.";
  if (field === "situs") return "No street address on this public parcel row.";
  if (field === "sale") return "No sale date or price on this public parcel row.";
  if (field === "saleQualified") return "No sale-qualification code on this public parcel row.";
  if (field === "designatedOz") {
    return "Designated QOZ status is not joined for this parcel. That is not a yes or no, and it is not a 2027 designation.";
  }
  if (countyFips === "12095") return "Not on the OCPA parcel.";
  if (countyFips === "13089") return "No municipal or county zoning joined for this parcel.";
  return "Zoning is not on this county's public parcel row. Missing zoning is not a zoning code.";
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

export function formatRoadLabel(
  road: {
    from: string | null;
    to: string | null;
    roadwayId: string | null;
  } | null,
  agency?: string | null,
): string {
  if (!road) return "Not available";
  if (road.from && road.to) return `${road.from} → ${road.to}`;
  if (road.from) return road.from;
  if (road.roadwayId) return agency ? `${agency} ${road.roadwayId}` : road.roadwayId;
  return agency ? `Nearest ${agency} count segment` : "Nearest count segment";
}

export function isFloridaParcel(state: string | null | undefined): boolean {
  return !state || state === "Florida";
}

/** Tract income is joined for every Southeast market. Block group stays Orange County. */
export function incomeEmptyMessage(
  geography: "tract" | "blockGroup",
  income: { geoid?: string | null } | null | undefined,
  orangeCounty: boolean,
): string {
  if (geography === "blockGroup") {
    return orangeCounty
      ? "No block-group income for this location"
      : "Block-group income is joined for Orange County only";
  }
  if (income?.geoid) return "ACS did not publish a median for this tract";
  return "No ACS tract join for this location";
}

/** Hide the AADT row outside Florida when no count was joined. */
export function showAadtField(state: string | null | undefined, hasCount: boolean): boolean {
  return isFloridaParcel(state) || hasCount;
}

export function aadtFieldLabel(state: string | null | undefined): string {
  return isFloridaParcel(state) ? "Nearest FDOT AADT" : "Nearest AADT";
}

export function aadtEmptyMessage(state: string | null | undefined): string {
  return isFloridaParcel(state) ? "No FDOT count segment within 15 km" : "No AADT count joined for this location";
}
