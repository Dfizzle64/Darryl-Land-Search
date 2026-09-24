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
