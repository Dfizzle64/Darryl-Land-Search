/**
 * Public GIS viewers from research cards.
 * A new shelf adds one FIPS row here. The parcel drawer reads this catalog,
 * so a stored ArcGIS REST service URL does not replace the public viewer.
 */

export type PublicLink = { href: string; label: string };

export type JurisdictionGisViewers = {
  primary: PublicLink;
  alt: PublicLink | null;
};

type GisViewerCard = {
  gisViewerUrl: string;
  gisViewerLabel: string;
  gisViewerUrlAlt?: string;
  gisViewerAltLabel?: string;
};

/** Wave 0 South Florida. Add the next shelf as another FIPS key. */
export const JURISDICTION_GIS_VIEWERS: Record<string, GisViewerCard> = {
  "12086": {
    gisViewerUrl: "https://experience.arcgis.com/experience/74e9a9f78b094ba2b17d86a0bfeb2eeb",
    gisViewerLabel: "Open Miami-Dade GIS viewer",
    gisViewerUrlAlt: "https://mdc.maps.arcgis.com/home/index.html",
    gisViewerAltLabel: "Open Miami-Dade ArcGIS hub",
  },
  "12087": {
    gisViewerUrl:
      "https://monroecounty-fl.maps.arcgis.com/apps/webappviewer/index.html?id=2e52d422378e4b48a471d02959265ecc",
    gisViewerLabel: "Open Monroe County GIS viewer",
    gisViewerUrlAlt: "https://www.monroecounty-fl.gov/gis",
    gisViewerAltLabel: "Open Monroe County GIS page",
  },
  "12011": {
    gisViewerUrl: "https://geohub-bcgis.opendata.arcgis.com/",
    gisViewerLabel: "Open Broward County GeoHub",
    gisViewerUrlAlt: "https://web.bcpa.net/bcpaclient/#/Record-Search",
    gisViewerAltLabel: "Open Broward property record search",
  },
  "12099": {
    gisViewerUrl: "https://pbcgov.maps.arcgis.com/home/index.html",
    gisViewerLabel: "Open Palm Beach County GIS viewer",
    gisViewerUrlAlt: "https://pbcgov.maps.arcgis.com/apps/webappviewer/index.html",
    gisViewerAltLabel: "Open Palm Beach web map",
  },
  "12013": {
    gisViewerUrl: "https://qpublic.schneidercorp.com/Application.aspx?AppID=829&LayerID=15004&PageTypeID=2&PageID=6748",
    gisViewerLabel: "Open Calhoun County GIS viewer",
  },
  "12023": {
    gisViewerUrl: "https://columbia.floridapa.com/gis/",
    gisViewerLabel: "Open Columbia County GIS viewer",
    gisViewerUrlAlt: "https://search.ccpafl.com/map/",
    gisViewerAltLabel: "Open Columbia County map",
  },
  "12029": {
    gisViewerUrl: "https://qpublic.schneidercorp.com/Application.aspx?AppID=867&LayerID=16385&PageTypeID=2&PageID=7230",
    gisViewerLabel: "Open Dixie County GIS viewer",
  },
  "12035": {
    gisViewerUrl: "https://qpublic.schneidercorp.com/Application.aspx?AppID=598&LayerID=9801&PageTypeID=2&PageID=4328",
    gisViewerLabel: "Open Flagler County GIS viewer",
  },
  "12037": {
    gisViewerUrl: "https://franklin-search.gsacorp.io/map",
    gisViewerLabel: "Open Franklin County GIS viewer",
  },
  "12039": {
    gisViewerUrl: "https://qpublic.schneidercorp.com/Application.aspx?App=GadsdenCountyFL&PageType=Search",
    gisViewerLabel: "Open Gadsden County property search",
  },
  "12045": {
    gisViewerUrl: "https://beacon.schneidercorp.com/Application.aspx?AppID=819&LayerID=15077&PageTypeID=2&PageID=6812",
    gisViewerLabel: "Open Gulf County GIS viewer",
  },
  "12047": {
    gisViewerUrl: "https://beacon.schneidercorp.com/Application.aspx?AppID=817&LayerID=14544&PageTypeID=2&PageID=6409",
    gisViewerLabel: "Open Hamilton County GIS viewer",
  },
  "12059": {
    gisViewerUrl: "https://qpublic.schneidercorp.com/Application.aspx?AppID=821&LayerID=14700&PageTypeID=2&PageID=6565",
    gisViewerLabel: "Open Holmes County GIS viewer",
  },
  "12063": {
    gisViewerUrl: "https://qpublic.schneidercorp.com/Application.aspx?AppID=851&LayerID=15884&PageTypeID=2&PageID=7081",
    gisViewerLabel: "Open Jackson County GIS viewer",
  },
  "12065": {
    gisViewerUrl: "https://qpublic.schneidercorp.com/Application.aspx?AppID=866&LayerID=16381&PageTypeID=2&PageID=7228",
    gisViewerLabel: "Open Jefferson County GIS viewer",
  },
  "12067": {
    gisViewerUrl: "https://beacon.schneidercorp.com/Application.aspx?AppID=1396&LayerID=47258&PageTypeID=2&PageID=19927",
    gisViewerLabel: "Open Lafayette County GIS viewer",
  },
  "12077": {
    gisViewerUrl: "https://qpublic.schneidercorp.com/Application.aspx?AppID=828&LayerID=15003&PageTypeID=2&PageID=13691",
    gisViewerLabel: "Open Liberty County GIS viewer",
  },
  "12079": {
    gisViewerUrl: "https://planning.madisoncountyfla.com/gis/",
    gisViewerLabel: "Open Madison County GIS viewer",
  },
  "12083": {
    gisViewerUrl: "https://gis.marionfl.org/",
    gisViewerLabel: "Open Marion County GIS viewer",
  },
  "12121": {
    gisViewerUrl: "https://suwannee-search.gsacorp.io/map",
    gisViewerLabel: "Open Suwannee County GIS viewer",
  },
  "12123": {
    gisViewerUrl: "https://beacon.schneidercorp.com/Application.aspx?AppID=792&LayerID=11749&PageTypeID=2&PageID=5268",
    gisViewerLabel: "Open Taylor County GIS viewer",
  },
  "12125": {
    gisViewerUrl: "https://union.floridapa.com/GIS/",
    gisViewerLabel: "Open Union County GIS viewer",
  },
  "12129": {
    gisViewerUrl: "https://gis-portal-update-wakullaplanning.hub.arcgis.com/",
    gisViewerLabel: "Open Wakulla County GIS viewer",
  },
  "12133": {
    gisViewerUrl: "https://qpublic.schneidercorp.com/Application.aspx?AppID=896&LayerID=16944&PageTypeID=2&PageID=7613",
    gisViewerLabel: "Open Washington County GIS viewer",
  },
};

const REST_SERVICE = /\/(MapServer|FeatureServer)(\/\d+)?\/?$/i;
const REJECTED_VIEWER = /papa|maps\.monroecounty\.gov|gis\.bcpa\.net|BMSDParcelAddress/i;

/** A stored feature URL is a public viewer only when it is not a REST service or a rejected host. */
export function publicGisViewerUrl(url: string | null | undefined): string | null {
  const trimmed = url?.trim() ?? "";
  if (!/^https:\/\//i.test(trimmed)) return null;
  if (REJECTED_VIEWER.test(trimmed) || REST_SERVICE.test(trimmed)) return null;
  return trimmed;
}

export function jurisdictionGisViewers(input: {
  countyFips?: string | null;
  gisViewerUrl?: string | null;
  gisViewerUrlAlt?: string | null;
}): JurisdictionGisViewers | null {
  const card = input.countyFips ? JURISDICTION_GIS_VIEWERS[input.countyFips] : undefined;
  if (card) {
    return {
      primary: { href: card.gisViewerUrl, label: card.gisViewerLabel },
      alt: card.gisViewerUrlAlt
        ? { href: card.gisViewerUrlAlt, label: card.gisViewerAltLabel || "Open alternate GIS viewer" }
        : null,
    };
  }
  const stored = publicGisViewerUrl(input.gisViewerUrl);
  if (!stored) return null;
  const alt = publicGisViewerUrl(input.gisViewerUrlAlt);
  return {
    primary: { href: stored, label: "Open jurisdiction GIS viewer" },
    alt: alt ? { href: alt, label: "Open alternate GIS viewer" } : null,
  };
}
