import { eligibleClassCut } from "./markets";
import { describeOz2Eligibility } from "./opportunityZone";
import type { ScreeningPoint, SchoolRating } from "./screening";
import { tractIncomeFilterActive, tractIncomePasses } from "./tractIncome";
import {
  RENT_SLIDERS,
  formatTractRentLines,
  tractRentFilterActive,
  tractRentPasses,
  type TractRentFields,
} from "./tractRent";
import type { FilterState, ParcelFeature, ParcelProperties, TractClassView } from "./types";
import {
  aadtEmptyMessage,
  aadtFieldLabel,
  formatAcres,
  formatNumber,
  formatParcelPlace,
  formatRoadLabel,
  formatSale,
  formatUsd,
  isFloridaParcel,
  missingPublicParcelValue,
  parcelAppraiserUrl,
  showAadtField,
  vintageFieldLabel,
} from "./format";
import { jurisdictionGisViewers } from "./jurisdictionLinks";
import { SitePdfError } from "./sitePdfGeometry";

export { SitePdfError } from "./sitePdfGeometry";
export {
  chooseScaleBar,
  contextBbox,
  geometryBbox,
  haversineMeters,
  locatorBbox,
} from "./sitePdfGeometry";

/** Same sentence the parcel panel uses when OZ 2.0 was not joined. */
export const OZ2_NOT_JOINED =
  "OZ 2.0 eligibility is not joined for this parcel. That is not a designation.";

export const SITE_PDF_DISCLAIMER = "Public data; verify before relying on it.";

export type SitePdfFact = { label: string; value: string };

export type SitePdfLink = { label: string; href: string };

export type TractGeometryRecord = {
  geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon;
  /** Rural flag on the tract polygon the map paints. */
  rural: boolean;
  /** ACS median stamped on that polygon. Null when the overlay has no estimate. */
  medianHouseholdIncome: number | null;
};

export type SitePdfImages = {
  main: string;
  locator: string;
  scaleLabel: string;
  logo: string | null;
};

export type SitePdfModel = {
  fileName: string;
  title: "Site summary";
  generatedOn: string;
  headline: string;
  subhead: string;
  parcelFacts: SitePdfFact[];
  tractFacts: SitePdfFact[];
  screeningFacts: SitePdfFact[];
  links: SitePdfLink[];
  sources: string[];
  disclaimer: string;
  parcelGeometry: GeoJSON.Polygon | GeoJSON.MultiPolygon;
  centroid: [number, number];
  /** Null when the eligible-tract overlay would not paint this tract. */
  eligibleTract: TractGeometryRecord | null;
};

export type SitePdfInput = {
  parcel: ParcelFeature;
  /** Zoning line the panel shows when a code is known. Null hides the row. */
  zoningLine: string | null;
  /** Future land use line the panel shows when a code is known. Null hides the row. */
  fluLine: string | null;
  screeningPoint?: ScreeningPoint | null;
  screeningStatus?: "idle" | "loading" | "error";
  rent?: Partial<TractRentFields> | null;
  /** Tract polygon for the parcel GEOID, when the app has one. */
  eligibleTract?: TractGeometryRecord | null;
  /** Eligible-tract overlay toggle. Off means the tint is not on the map. */
  showTracts?: boolean;
  tractClass?: TractClassView;
  filters: FilterState;
  generatedAt?: Date;
  /** Passed through to the date formatter. Tests pin UTC. */
  timeZone?: string;
};

const DEKALB_FIPS = "13089";
/** Monroe stores `PC` on dorCode. The land-use mapping is not confirmed. */
const MONROE_FIPS = "12087";

type IndexedTract = {
  geometry: GeoJSON.Geometry | null;
  properties: {
    tractGeoid?: string | null;
    rural?: boolean | null;
    medianHouseholdIncome?: number | null;
  } | null;
};

export function indexTractGeometries(
  collections: Array<{ features: IndexedTract[] }>,
): Map<string, TractGeometryRecord> {
  const index = new Map<string, TractGeometryRecord>();
  for (const collection of collections) {
    for (const feature of collection.features) {
      const geoid = feature.properties?.tractGeoid;
      if (!geoid || index.has(geoid)) continue;
      const geometry = feature.geometry;
      if (!geometry || (geometry.type !== "Polygon" && geometry.type !== "MultiPolygon")) continue;
      const income = feature.properties?.medianHouseholdIncome;
      index.set(geoid, {
        geometry,
        rural: feature.properties?.rural === true,
        medianHouseholdIncome: typeof income === "number" && Number.isFinite(income) ? income : null,
      });
    }
  }
  return index;
}

/** 2020 tract GEOID the parcel panel can already see. OZ 2.0 wins over tract income. */
export function tractGeoidForParcel(properties: {
  oz2Eligibility?: { tractGeoid?: string | null } | null;
  incomeTract?: { geoid?: string | null } | null;
}): string | null {
  const oz = properties.oz2Eligibility?.tractGeoid;
  if (typeof oz === "string" && /^\d{11}$/.test(oz)) return oz;
  const income = properties.incomeTract?.geoid;
  if (typeof income === "string" && /^\d{11}$/.test(income)) return income;
  return null;
}

export function sitePdfFileName(countyName: string | null | undefined, parcelId: string): string {
  const county = fileToken(countyName || "county", true);
  const id = fileToken(parcelId || "parcel", false);
  return `CDP-site-${county}-${id}.pdf`;
}

function fileToken(value: string, lower: boolean): string {
  const raw = lower ? value.trim().toLowerCase() : value.trim();
  const cleaned = raw.replace(/[^a-zA-Z0-9]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
  return cleaned || "unknown";
}

export function formatGeneratedDate(date: Date, timeZone?: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone,
  }).format(date);
}

export function googleMapsUrl(lat: number, lon: number): string {
  return `https://www.google.com/maps?q=${lat.toFixed(6)},${lon.toFixed(6)}`;
}

export function clipText(value: string, max = 140): string {
  const clean = value.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 3).trimEnd()}...`;
}

/**
 * Whether the PDF should tint the eligible tract. This follows the overlay
 * switches: hidden tracts, omitted South Carolina tracts, and tracts the
 * income or rent filters remove stay off the page.
 */
export function eligibleTractIsVisible(input: {
  showTracts: boolean;
  eligible: boolean | null;
  shown: boolean;
  rural: boolean | null;
  tractClass: TractClassView;
  filters: FilterState;
  medianHouseholdIncome: number | null;
  rent: Partial<TractRentFields> | null;
  hasGeometry: boolean;
}): boolean {
  if (!input.showTracts || !input.hasGeometry) return false;
  if (input.eligible !== true || !input.shown) return false;
  const cut = eligibleClassCut(input.tractClass, input.filters.ozFilter);
  if (cut === "none") return false;
  if (cut === "rural" && input.rural !== true) return false;
  if (cut === "urban" && input.rural !== false) return false;
  if (
    tractIncomeFilterActive(input.filters.incomeGeography, input.filters.minIncome, input.filters.includeUnknownIncome) &&
    !tractIncomePasses(input.medianHouseholdIncome, input.filters.minIncome, input.filters.includeUnknownIncome)
  ) {
    return false;
  }
  if (tractRentFilterActive(input.filters)) {
    for (const slider of RENT_SLIDERS) {
      if (!tractRentPasses(input.rent?.[slider.property], input.filters[slider.key])) return false;
    }
  }
  return true;
}

function countyStateLabel(countyName: string | null | undefined, state: string | null | undefined): string | null {
  const county = countyName?.trim();
  const stateLabel = state?.trim();
  if (!county && !stateLabel) return null;
  const countyPart = county ? (/county$/i.test(county) ? county : `${county} County`) : null;
  return [countyPart, stateLabel].filter(Boolean).join(", ");
}

function moneyFact(label: string, value: number | null | undefined, vintage?: string | null): SitePdfFact | null {
  if (value == null || !Number.isFinite(value) || value <= 0) return null;
  return { label: vintageFieldLabel(label, vintage, true), value: formatUsd(value) };
}

function landUseFact(properties: ParcelProperties): SitePdfFact | null {
  const code = properties.dorCode?.trim();
  if (!code) return null;
  if (properties.countyFips === DEKALB_FIPS) return { label: "Tax district", value: code };
  if (properties.countyFips === MONROE_FIPS) return null;
  return { label: "Land use", value: code };
}

function validCentroid(centroid: [number, number] | null | undefined): centroid is [number, number] {
  return (
    Array.isArray(centroid) &&
    centroid.length >= 2 &&
    Number.isFinite(centroid[0]) &&
    Number.isFinite(centroid[1]) &&
    Math.abs(centroid[0]) <= 180 &&
    Math.abs(centroid[1]) <= 90
  );
}

function rentFacts(geoid: string | null, rent: Partial<TractRentFields> | null | undefined): SitePdfFact[] {
  if (!geoid && !rent) return [];
  return formatTractRentLines(rent).map((line) => {
    const splitAt = line.indexOf(": ");
    if (splitAt === -1) return { label: "Rent", value: line };
    return { label: line.slice(0, splitAt), value: line.slice(splitAt + 2) };
  });
}

function schoolLine(school: SchoolRating): string {
  const grade = school.rating
    ? school.ratingKind === "ccrpi"
      ? `CCRPI ${school.rating}`
      : school.rating
    : "No grade";
  const where = [school.level, school.distanceMiles != null ? `${school.distanceMiles.toFixed(1)} mi` : null]
    .filter(Boolean)
    .join(", ");
  const zoned = school.zoned ? "Zoned · " : "";
  return where ? `${zoned}${grade} · ${school.name} (${where})` : `${zoned}${grade} · ${school.name}`;
}

/** Status chip only. The 2020 GEOID is its own row, so the panel's GEOID suffix is not repeated. */
export function ozPdfStatus(oz: {
  eligible: boolean | null;
  rural: boolean | null;
  label: string;
  statusChip: string | null;
  shown: boolean;
}): string {
  if (oz.eligible == null) return OZ2_NOT_JOINED;
  if (!oz.shown) return oz.label;
  if (!oz.eligible) return "Not eligible";
  return oz.statusChip ?? (oz.rural === false ? "Eligible, not rural" : "Eligible");
}

function firstSentence(text: string): string {
  const match = text.match(/^[\s\S]{1,220}?[.!?](?=\s|$)/);
  return (match?.[0] ?? text).trim();
}

/** One clean clause for the PDF. Does not add a hazard, a grade, or a provider the summary does not already state. */
export function pdfScreeningLine(kind: "flood" | "wetland" | "utility" | "note", summary: string): string {
  const text = summary.replace(/\s+/g, " ").trim();
  if (!text) return text;
  if (kind === "flood") {
    const zone = text.match(/^FEMA zone ([A-Z0-9]+) at the parcel centroid\b/i);
    if (zone) {
      if (/AREA OF MINIMAL FLOOD HAZARD/i.test(text)) {
        return `FEMA zone ${zone[1].toUpperCase()} at the parcel centroid (minimal flood hazard).`;
      }
      if (/Special Flood Hazard Area/i.test(text)) {
        return `FEMA zone ${zone[1].toUpperCase()} at the parcel centroid (Special Flood Hazard Area).`;
      }
      return `FEMA zone ${zone[1].toUpperCase()} at the parcel centroid.`;
    }
  }
  if (kind === "wetland") {
    if (/^No NWI wetland polygon within about 70 feet/i.test(text)) {
      return "No NWI wetland polygon within ~70 ft.";
    }
    const hit = text.match(/^NWI (.+?) within about 70 feet/i);
    if (hit) return `NWI ${hit[1]} within ~70 ft.`;
  }
  if (kind === "utility") {
    const area = text.match(/^(?:Water|Sewer|Electric) service area: ([^.]+)\./i);
    if (area && /will-serve/i.test(text)) return `${area[1].trim()} service area. Not a will-serve.`;
    const retail = text.match(/^Electric retail territory: ([^.]+)\./i);
    if (retail && /will-serve/i.test(text)) return `${retail[1].trim()}. Not a will-serve.`;
  }
  if (text.length <= 110) return text;
  return firstSentence(text);
}

function utilityLabel(kind: ScreeningPoint["utilities"][number]["kind"]): string {
  if (kind === "power") return "Electric";
  if (kind === "gas") return "Gas";
  if (kind === "water") return "Water";
  return "Sewer";
}

function aadtFact(properties: ParcelProperties): SitePdfFact | null {
  const known = properties.nearestRoad?.aadt != null;
  if (!showAadtField(properties.state, known)) return null;
  const label = aadtFieldLabel(properties.state);
  if (!known || !properties.nearestRoad) {
    return { label, value: aadtEmptyMessage(properties.state) };
  }
  const road = properties.nearestRoad;
  const florida = isFloridaParcel(properties.state);
  const parts = [
    `${formatNumber(road.aadt)} vehicles/day (${road.year ?? "year n/a"})`,
    formatRoadLabel(road, florida ? "FDOT" : null),
  ];
  if (road.distanceMeters != null) parts.push(`${formatNumber(road.distanceMeters)} m from centroid`);
  return { label, value: parts.join(" · ") };
}

function screeningFacts(
  properties: ParcelProperties,
  point: ScreeningPoint | null,
  status: "idle" | "loading" | "error",
): SitePdfFact[] {
  const facts: SitePdfFact[] = [];
  const traffic = aadtFact(properties);
  if (traffic) facts.push(traffic);
  if (status === "loading" && !point) {
    facts.push({
      label: "Site screening",
      value: "Looking up flood, wetlands, utilities, and nearby public school ratings…",
    });
    return facts;
  }
  if (status === "error" && !point) {
    facts.push({
      label: "Site screening",
      value: "Screening services did not respond. That is unknown, not a clear site.",
    });
    return facts;
  }
  if (!point) return facts;
  facts.push({ label: "Flood zone", value: pdfScreeningLine("flood", point.flood.summary) });
  if (point.tract?.summary) facts.push({ label: "Census tract", value: pdfScreeningLine("note", point.tract.summary) });
  facts.push({ label: "Wetlands", value: pdfScreeningLine("wetland", point.wetland.summary) });
  for (const utility of point.utilities) {
    if (!utility.summary?.trim()) continue;
    facts.push({ label: utilityLabel(utility.kind), value: pdfScreeningLine("utility", utility.summary) });
  }
  if (point.schools.length) {
    const lines = point.schools.slice(0, 3).map(schoolLine);
    if (point.schools.length > 3) lines.push(`+${point.schools.length - 3} more`);
    facts.push({ label: "Schools", value: lines.join("\n") });
  } else {
    facts.push({ label: "Schools", value: "No public school in this extract within 3 miles." });
  }
  return facts;
}

function pushSource(sources: string[], value: string | null | undefined) {
  const text = value?.replace(/\s+/g, " ").trim();
  if (!text || sources.includes(text)) return;
  sources.push(text);
}

export function assembleSiteSummary(input: SitePdfInput): SitePdfModel {
  const { parcel, filters } = input;
  const properties = parcel.properties;
  const geometry = parcel.geometry;
  if (!geometry || (geometry.type !== "Polygon" && geometry.type !== "MultiPolygon")) {
    throw new SitePdfError("Could not export the PDF. This parcel has no boundary to draw.");
  }
  if (!validCentroid(properties.centroid)) {
    throw new SitePdfError("Could not export the PDF. This parcel has no centroid.");
  }

  const place = countyStateLabel(properties.countyName, properties.state);
  const street = properties.situsAddress?.trim() || missingPublicParcelValue("situs");
  const cityLine = formatParcelPlace(properties);
  const address = cityLine && cityLine !== street ? `${street}, ${cityLine}` : street;
  const [lon, lat] = properties.centroid;

  const parcelFacts: SitePdfFact[] = [
    { label: "Parcel ID", value: properties.parcelId },
  ];
  if (place) parcelFacts.push({ label: "County", value: place });
  parcelFacts.push({ label: "Address", value: address });
  parcelFacts.push({ label: "Acreage", value: formatAcres(properties.acreage) });
  const owner = [properties.ownerName, properties.ownerName2]
    .map((name) => name?.trim())
    .filter((name): name is string => Boolean(name))
    .join(", ");
  if (owner) parcelFacts.push({ label: "Owner", value: owner });
  if (input.zoningLine?.trim()) parcelFacts.push({ label: "Zoning", value: input.zoningLine.trim() });
  if (input.fluLine?.trim()) parcelFacts.push({ label: "Future land use", value: input.fluLine.trim() });
  const landUse = landUseFact(properties);
  if (landUse) parcelFacts.push(landUse);
  for (const fact of [
    moneyFact("Market value", properties.tax.marketValue, properties.tax.vintage),
    moneyFact("Assessed value", properties.tax.assessedValue, properties.tax.vintage),
    moneyFact("Taxable value", properties.tax.taxableValue, properties.tax.vintage),
    moneyFact("Taxes", properties.tax.taxes, properties.tax.vintage),
  ]) {
    if (fact) parcelFacts.push(fact);
  }
  const sale = formatSale(properties.lastSale);
  if (sale) {
    parcelFacts.push({
      label: vintageFieldLabel("Last sale", properties.lastSale.vintage, true),
      value: sale.replace(/\n/g, " · "),
    });
  }
  parcelFacts.push({ label: "Centroid", value: `${lat.toFixed(5)}, ${lon.toFixed(5)}` });

  const oz = describeOz2Eligibility(properties.oz2Eligibility);
  const geoid = tractGeoidForParcel(properties);
  const tractFacts: SitePdfFact[] = [];
  if (geoid) tractFacts.push({ label: "2020 GEOID", value: geoid });
  tractFacts.push({ label: "OZ 2.0", value: ozPdfStatus(oz) });
  if (oz.rural === true) tractFacts.push({ label: "Rural", value: "Rural" });
  else if (oz.rural === false) tractFacts.push({ label: "Rural", value: "Non-rural" });
  const income = properties.incomeTract;
  if (income?.medianHouseholdIncome != null) {
    const vintage = income.vintage?.trim();
    tractFacts.push({
      label: "Median household income",
      value: `${formatUsd(income.medianHouseholdIncome)}${vintage ? ` · ${vintage}` : ""}`,
    });
  } else if (income?.geoid) {
    tractFacts.push({
      label: "Median household income",
      value: "ACS did not publish a median for this tract",
    });
  }
  tractFacts.push(...rentFacts(geoid, input.rent));

  const point = input.screeningPoint ?? null;
  const status = input.screeningStatus ?? "idle";
  const screening = screeningFacts(properties, point, status);

  const appraiser = parcelAppraiserUrl({
    parcelId: properties.parcelId,
    countyFips: properties.countyFips,
    appraiserUrl: properties.appraiserUrl,
  });
  const gis = jurisdictionGisViewers({
    countyFips: properties.countyFips,
    gisViewerUrl: properties.gisViewerUrl,
    gisViewerUrlAlt: properties.gisViewerUrlAlt,
  });
  const links: SitePdfLink[] = [];
  if (appraiser.href) links.push({ label: appraiser.label, href: appraiser.href });
  if (gis) {
    links.push(gis.primary);
    if (gis.alt) links.push(gis.alt);
  }
  links.push({ label: "Google Maps", href: googleMapsUrl(lat, lon) });

  const sources: string[] = [];
  pushSource(sources, properties.source);
  pushSource(sources, "ACS 5-year 2020–2024 B19013 median household income");
  pushSource(sources, "Rent: ACS B25064, HUD SAFMR 2BR, Zillow ZORI, Apartment List");
  pushSource(sources, "Basemap: Esri World Street Map");
  if (point) {
    pushSource(sources, point.flood.source);
    pushSource(sources, point.wetland.source);
    for (const utility of point.utilities) pushSource(sources, utility.source);
    if (point.schools[0]?.source) pushSource(sources, point.schools[0].source);
  }

  const tract = input.eligibleTract ?? null;
  const showTract = eligibleTractIsVisible({
    showTracts: input.showTracts !== false,
    eligible: oz.eligible,
    shown: oz.shown,
    rural: oz.rural,
    tractClass: input.tractClass ?? "both",
    filters,
    medianHouseholdIncome: tract?.medianHouseholdIncome ?? null,
    rent: input.rent ?? null,
    hasGeometry: tract != null,
  });

  return {
    fileName: sitePdfFileName(properties.countyName, properties.parcelId),
    title: "Site summary",
    generatedOn: formatGeneratedDate(input.generatedAt ?? new Date(), input.timeZone),
    headline: street,
    subhead: place || cityLine,
    parcelFacts,
    tractFacts,
    screeningFacts: screening,
    links,
    sources,
    disclaimer: SITE_PDF_DISCLAIMER,
    parcelGeometry: geometry,
    centroid: [lon, lat],
    eligibleTract: showTract && tract ? tract : null,
  };
}
