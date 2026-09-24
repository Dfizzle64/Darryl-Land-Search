/**
 * Wave 0 South Florida. Miami-Dade, Monroe, Broward, and Palm Beach.
 * Eligible tracts are not invented.
 * Broward is partial: BCPA geometry is folio-only. The FDOR CAMA join was not applied.
 * Palm Beach kept the parcels that survived geometry normalize, not the full object-id count.
 */

export const SOUTH_FLORIDA_FIPS = ["12086", "12087", "12011", "12099"] as const;

export type SouthFloridaFips = (typeof SOUTH_FLORIDA_FIPS)[number];

const MIAMI_PA = "https://apps.miamidadepa.gov/ComparableSales/#/?folio=";
const MONROE_PA =
  "https://qpublic.schneidercorp.com/Application.aspx?AppID=605&LayerID=9946&PageTypeID=4&PageID=7635&KeyValue=";
const BROWARD_PA = "https://bcpa.net/RecInfo.asp?URL_Folio=";
const PALM_PA = "https://pbcpao.gov/Property/Details?parcelId=";

export function isSouthFloridaFips(fips: string | null | undefined): fips is SouthFloridaFips {
  return Boolean(fips && (SOUTH_FLORIDA_FIPS as readonly string[]).includes(fips));
}

export function southFloridaAppraiserLink(
  fips: string | null | undefined,
  parcelId: string,
  stored?: string | null,
): { href: string; label: string } | null {
  if (!isSouthFloridaFips(fips)) return null;
  if (fips === "12086") {
    const folio = parcelId.replace(/\D/g, "") || parcelId;
    return {
      href: `${MIAMI_PA}${encodeURIComponent(folio)}`,
      label: "Open Miami-Dade comparable sales for this folio",
    };
  }
  if (fips === "12087") {
    const href =
      stored && /schneidercorp\.com/i.test(stored) && stored.includes("KeyValue=")
        ? stored
        : `${MONROE_PA}${encodeURIComponent(parcelId)}`;
    return { href, label: "Open Monroe County property record" };
  }
  if (fips === "12011") {
    return {
      href: `${BROWARD_PA}${encodeURIComponent(parcelId)}`,
      label: "Open Broward County property record",
    };
  }
  return {
    href: `${PALM_PA}${encodeURIComponent(parcelId)}`,
    label: "Open Palm Beach County property details",
  };
}

export function zoningEmptyForSouthFlorida(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips === "12086") {
    return "No Miami-Dade zoning polygon contains this parcel. PRIMARY_ZONE on the parcel layer is a neighborhood code, not a zoning district.";
  }
  if (countyFips === "12087") {
    return "No Monroe land-use district contains this parcel. City zoning was not inventoried.";
  }
  if (countyFips === "12011") {
    return "No Broward zoning polygon contains this parcel. BMSD zoning is unincorporated only. The city zoning mosaic is partial and is not a city ordinance.";
  }
  if (countyFips === "12099") {
    return "No unincorporated Palm Beach zoning polygon contains this parcel. County zoning does not cover municipalities.";
  }
  return fallback;
}

export function fluEmptyForSouthFlorida(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips === "12086") {
    return "No Miami-Dade CDMP future-land-use polygon contains this parcel.";
  }
  if (countyFips === "12087") {
    return "No Monroe future-land-use polygon contains this parcel.";
  }
  if (countyFips === "12011") {
    return "No Broward land-use polygon contains this parcel. SLUC1 is a numeric code, not a plain-language future-land-use label.";
  }
  if (countyFips === "12099") {
    return "No Palm Beach future-land-use polygon contains this parcel. County zoning inside cities is a separate gap.";
  }
  return fallback;
}

const MIAMI_UNINC = "https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/18";
const MIAMI_CITY = "https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/19";
const MIAMI_PARCELS = "https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/26";
const MONROE_ZONING = "https://mcgis4.monroecounty-fl.gov/public/rest/services/APO_GIS/MapServer/19";
const MONROE_PARCELS = "https://mcgis4.monroecounty-fl.gov/public/rest/services/Parcels/MapServer/0";
const BROWARD_BMSD =
  "https://services.arcgis.com/JMAJrTsHNLrSsWf5/ArcGIS/rest/services/Broward_Municipal_Service_District_Zoning/FeatureServer/2";
const BROWARD_MOSAIC = "https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN26/MapServer/9";
const BROWARD_PARCELS = "https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN26/MapServer/16";
const PALM_ZONING = "https://maps.co.palm-beach.fl.us/arcgis/rest/services/OpenData/Planning_Open_Data/MapServer/9";
const PALM_PARCELS = "https://gis.pbcgov.org/arcgis/rest/services/Parcels/PARCEL_INFO/FeatureServer/4";

export type GisViewerLink = { href: string; label: string };

function trustedGisViewer(url: string): boolean {
  return /^https:\/\//i.test(url) && !/papa|maps\.monroecounty\.gov|gis\.bcpa\.net|BMSDParcelAddress/i.test(url);
}

function gisViewerHref(fips: SouthFloridaFips, jurisdiction: string | null | undefined, zoned: boolean): string {
  if (fips === "12086") {
    if (!zoned) return MIAMI_PARCELS;
    return jurisdiction === "Unincorporated" ? MIAMI_UNINC : MIAMI_CITY;
  }
  if (fips === "12087") return zoned ? MONROE_ZONING : MONROE_PARCELS;
  if (fips === "12011") {
    if (!zoned) return BROWARD_PARCELS;
    return jurisdiction === "Unincorporated" ? BROWARD_BMSD : BROWARD_MOSAIC;
  }
  return zoned ? PALM_ZONING : PALM_PARCELS;
}

function gisViewerLabel(fips: SouthFloridaFips, jurisdiction: string | null | undefined, zoned: boolean): string {
  if (fips === "12086") {
    if (!zoned) return "Miami-Dade parcel layer";
    return jurisdiction === "Unincorporated" ? "Miami-Dade unincorporated zoning" : "Miami-Dade municipal zoning";
  }
  if (fips === "12087") return zoned ? "Monroe land-use districts" : "Monroe parcel layer";
  if (fips === "12011") {
    if (!zoned) return "Broward parcel layer";
    return jurisdiction === "Unincorporated"
      ? "Broward unincorporated BMSD zoning"
      : "Broward city zoning mosaic (partial, not a Fort Lauderdale ordinance)";
  }
  return zoned ? "Palm Beach unincorporated zoning" : "Palm Beach parcel layer";
}

/** Jurisdiction GIS layer from the Wave 0 cards. Stored `gisViewerUrl` wins when it is one of those hosts. */
export function southFloridaGisViewer(input: {
  countyFips?: string | null;
  jurisdictionCode?: string | null;
  zoningCode?: string | null;
  gisViewerUrl?: string | null;
}): GisViewerLink | null {
  if (!isSouthFloridaFips(input.countyFips)) return null;
  const zoned = Boolean(input.zoningCode);
  const stored = input.gisViewerUrl?.trim() ?? "";
  const href = stored && trustedGisViewer(stored) ? stored : gisViewerHref(input.countyFips, input.jurisdictionCode, zoned);
  return { href, label: gisViewerLabel(input.countyFips, input.jurisdictionCode, zoned) };
}

export function saleEmptyForSouthFlorida(countyFips: string | null | undefined): string | null {
  if (countyFips === "12086") {
    return "No sale on this parcel row. Last sale is not on the Miami-Dade parcel layer. The folio API is the sales source and was not copied here.";
  }
  if (countyFips === "12011") {
    return "No sale on this Broward row. BCPA MapServer/16 is folio and geometry. Countywide sales are the FDOR CO_NO=16 join, not this polygon.";
  }
  return null;
}
