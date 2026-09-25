/**
 * FL-rest batch 1. Twenty Florida counties that had no 5–150 acre parcels,
 * or only a sample or gap row. Eligible tracts are not invented.
 * Dixie, Madison, and Taylor stay partial. Their future-land-use fallback is
 * the 2008 statewide broad category layer, labeled as such.
 */

export const FL_REST_FIPS = [
  "12013",
  "12023",
  "12029",
  "12035",
  "12037",
  "12039",
  "12045",
  "12047",
  "12059",
  "12063",
  "12065",
  "12067",
  "12077",
  "12079",
  "12083",
  "12121",
  "12123",
  "12125",
  "12129",
  "12133",
] as const;

export type FlRestFips = (typeof FL_REST_FIPS)[number];

export const GEOPLAN_LABEL = "2008 statewide broad land-use categories, not current zoning";

const SEARCH_ONLY = new Set(["12039", "12079", "12083"]);

const APPRAISER: Record<FlRestFips, { href: string; label: string; deepLink: boolean }> = {
  "12013": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?AppID=829&LayerID=15004&PageTypeID=4&PageID=6748&KeyValue=",
    label: "Open Calhoun County property record",
    deepLink: true,
  },
  "12023": {
    href: "https://www.columbiacountyfla.com/ParcelDetails.aspx?ParcelNo=",
    label: "Open Columbia County property record",
    deepLink: true,
  },
  "12029": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?AppID=867&LayerID=16385&PageTypeID=4&PageID=7230&KeyValue=",
    label: "Open Dixie County property record",
    deepLink: true,
  },
  "12035": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?AppID=598&LayerID=9801&PageTypeID=4&PageID=4330&KeyValue=",
    label: "Open Flagler County property record",
    deepLink: true,
  },
  "12037": {
    href: "https://franklin-search.gsacorp.io/parcel/",
    label: "Open Franklin County property record",
    deepLink: true,
  },
  "12039": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?App=GadsdenCountyFL&PageType=Search",
    label: "Open Gadsden County property search",
    deepLink: false,
  },
  "12045": {
    href: "https://beacon.schneidercorp.com/Application.aspx?AppID=819&LayerID=15077&PageTypeID=4&PageID=6812&KeyValue=",
    label: "Open Gulf County property record",
    deepLink: true,
  },
  "12047": {
    href: "https://beacon.schneidercorp.com/Application.aspx?AppID=817&LayerID=14544&PageTypeID=4&PageID=6409&KeyValue=",
    label: "Open Hamilton County property record",
    deepLink: true,
  },
  "12059": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?AppID=821&LayerID=14700&PageTypeID=4&PageID=6565&KeyValue=",
    label: "Open Holmes County property record",
    deepLink: true,
  },
  "12063": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?AppID=851&LayerID=15884&PageTypeID=4&PageID=7081&KeyValue=",
    label: "Open Jackson County property record",
    deepLink: true,
  },
  "12065": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?AppID=866&LayerID=16381&PageTypeID=4&PageID=7228&KeyValue=",
    label: "Open Jefferson County property record",
    deepLink: true,
  },
  "12067": {
    href: "https://beacon.schneidercorp.com/Application.aspx?AppID=1396&LayerID=47258&PageTypeID=4&PageID=19927&KeyValue=",
    label: "Open Lafayette County property record",
    deepLink: true,
  },
  "12077": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?AppID=828&LayerID=15003&PageTypeID=4&PageID=13691&KeyValue=",
    label: "Open Liberty County property record",
    deepLink: true,
  },
  "12079": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?App=MadisonCountyFL&Layer=Parcels&PageType=Search",
    label: "Open Madison County property search",
    deepLink: false,
  },
  "12083": {
    href: "https://www.pa.marion.fl.us/PropertySearch.aspx",
    label: "Open Marion County property search",
    deepLink: false,
  },
  "12121": {
    href: "https://suwannee-search.gsacorp.io/parcel/",
    label: "Open Suwannee County property record",
    deepLink: true,
  },
  "12123": {
    href: "https://beacon.schneidercorp.com/Application.aspx?AppID=792&LayerID=11749&PageTypeID=4&PageID=5268&KeyValue=",
    label: "Open Taylor County property record",
    deepLink: true,
  },
  "12125": {
    href: "https://union.floridapa.com/GIS/?pin=",
    label: "Open Union County property record",
    deepLink: true,
  },
  "12129": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?AppID=836&LayerID=15205&PageTypeID=4&PageID=6833&KeyValue=",
    label: "Open Wakulla County property record",
    deepLink: true,
  },
  "12133": {
    href: "https://qpublic.schneidercorp.com/Application.aspx?AppID=896&LayerID=16944&PageTypeID=4&PageID=7615&KeyValue=",
    label: "Open Washington County property record",
    deepLink: true,
  },
};

type Box = { market: "North Florida" | "North-Central Florida" | "Panhandle Florida" | "Big Bend"; west: number; south: number; east: number; north: number };

/** County boxes for jump-to. A shelf rectangle would swallow neighboring markets. */
const COUNTY_BOX: Record<FlRestFips, Box> = {
  "12013": { market: "Panhandle Florida", west: -85.45, south: 30.1, east: -84.8, north: 30.7 },
  "12023": { market: "North Florida", west: -82.95, south: 29.8, east: -82.25, north: 30.65 },
  "12029": { market: "Big Bend", west: -83.55, south: 29.3, east: -82.85, north: 29.95 },
  "12035": { market: "North Florida", west: -81.6, south: 29.25, east: -80.95, north: 29.8 },
  "12037": { market: "Panhandle Florida", west: -85.3, south: 29.5, east: -84.2, north: 30.1 },
  "12039": { market: "Big Bend", west: -85.05, south: 30.35, east: -84.2, north: 30.8 },
  "12045": { market: "Panhandle Florida", west: -85.5, south: 29.5, east: -84.85, north: 30.3 },
  "12047": { market: "North Florida", west: -83.35, south: 30.2, east: -82.5, north: 30.75 },
  "12059": { market: "Panhandle Florida", west: -86.15, south: 30.65, east: -85.45, north: 31.1 },
  "12063": { market: "Panhandle Florida", west: -85.55, south: 30.5, east: -84.65, north: 31.1 },
  "12065": { market: "Big Bend", west: -84.2, south: 30.15, east: -83.6, north: 30.7 },
  "12067": { market: "North Florida", west: -83.45, south: 29.8, east: -82.95, north: 30.3 },
  "12077": { market: "Panhandle Florida", west: -85.2, south: 29.9, east: -84.4, north: 30.6 },
  "12079": { market: "Big Bend", west: -83.9, south: 30.15, east: -83.15, north: 30.7 },
  "12083": { market: "North-Central Florida", west: -82.75, south: 28.9, east: -81.7, north: 29.6 },
  "12121": { market: "North Florida", west: -83.3, south: 29.9, east: -82.6, north: 30.55 },
  "12123": { market: "Big Bend", west: -84.05, south: 29.65, east: -83.2, north: 30.35 },
  "12125": { market: "North Florida", west: -82.6, south: 29.85, east: -82.15, north: 30.25 },
  "12129": { market: "Big Bend", west: -84.75, south: 29.9, east: -83.95, north: 30.35 },
  "12133": { market: "Panhandle Florida", west: -85.9, south: 30.35, east: -85.3, north: 30.9 },
};

const ZONING_EMPTY: Partial<Record<FlRestFips, string>> = {
  "12013": "No county zoning layer. Future land use is the FLUM category, not a zoning district.",
  "12029": GEOPLAN_LABEL,
  "12037": "No Franklin zoning attribute matched this parcel.",
  "12039": "No future-land-use polygon contains this parcel. County code uses that category as the land-use district.",
  "12045": "No queryable Gulf County zoning or future land use layer.",
  "12047": "No queryable Hamilton County zoning or future land use layer.",
  "12059": "Holmes future land use is a PDF. No zoning district layer was published.",
  "12063": "No countywide Jackson zoning layer. Future land use is the county FLUM.",
  "12067": "No queryable Lafayette County zoning or future land use layer.",
  "12077": "No countywide Liberty zoning layer. Future land use is the FLUM category.",
  "12079": GEOPLAN_LABEL,
  "12121": "No queryable Suwannee County zoning or future land use layer.",
  "12123": GEOPLAN_LABEL,
  "12125": "No queryable Union County, Florida zoning or future land use layer.",
  "12133": "No countywide Washington zoning layer. Future land use is the county FLUM.",
};

const FLU_EMPTY: Partial<Record<FlRestFips, string>> = {
  "12013": "No future-land-use category polygon contains this parcel.",
  "12029": GEOPLAN_LABEL,
  "12037": "Unincorporated Franklin future land use is not a queryable layer. Carrabelle is the city layer.",
  "12045": "No queryable Gulf County zoning or future land use layer.",
  "12047": "No queryable Hamilton County zoning or future land use layer.",
  "12059": "Holmes future land use is a PDF. No zoning district layer was published.",
  "12067": "No queryable Lafayette County zoning or future land use layer.",
  "12077": "No future-land-use category polygon contains this parcel.",
  "12079": GEOPLAN_LABEL,
  "12121": "No queryable Suwannee County zoning or future land use layer.",
  "12123": GEOPLAN_LABEL,
  "12125": "No queryable Union County, Florida zoning or future land use layer.",
  "12133": "No future-land-use polygon contains this parcel.",
};

const SALE_EMPTY: Partial<Record<FlRestFips, string>> = {
  "12065": "Sale history beyond the FDOR roll year is not on this extract.",
  "12129": "Sale history beyond the FDOR roll year is not on this extract.",
};

export function isFlRestFips(fips: string | null | undefined): fips is FlRestFips {
  return Boolean(fips && (FL_REST_FIPS as readonly string[]).includes(fips));
}

export function flRestAppraiserLink(
  fips: string | null | undefined,
  parcelId: string,
): { href: string; label: string } | null {
  if (!isFlRestFips(fips)) return null;
  const card = APPRAISER[fips];
  if (!card.deepLink || SEARCH_ONLY.has(fips)) {
    return { href: card.href, label: card.label };
  }
  return { href: `${card.href}${encodeURIComponent(parcelId)}`, label: card.label };
}

export function flRestMarketAt(lng: number, lat: number): Box["market"] | null {
  let found: Box | null = null;
  let area = Number.POSITIVE_INFINITY;
  for (const box of Object.values(COUNTY_BOX)) {
    if (lng < box.west || lng > box.east || lat < box.south || lat > box.north) continue;
    const next = (box.east - box.west) * (box.north - box.south);
    if (next < area) {
      found = box;
      area = next;
    }
  }
  return found?.market ?? null;
}

export function zoningEmptyForFlRest(countyFips: string | null | undefined, fallback: string): string {
  if (!isFlRestFips(countyFips)) return fallback;
  return ZONING_EMPTY[countyFips] ?? fallback;
}

export function fluEmptyForFlRest(countyFips: string | null | undefined, fallback: string): string {
  if (!isFlRestFips(countyFips)) return fallback;
  return FLU_EMPTY[countyFips] ?? fallback;
}

export function saleEmptyForFlRest(countyFips: string | null | undefined): string | null {
  if (!isFlRestFips(countyFips)) return null;
  return SALE_EMPTY[countyFips] ?? null;
}
