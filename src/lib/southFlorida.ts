/**
 * Wave 0 South Florida. Four counties only. Eligible tracts are not invented.
 * Broward is partial: BCPA geometry is folio-only, and CAMA is a FDOR join.
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

export function saleEmptyForSouthFlorida(countyFips: string | null | undefined): string | null {
  if (countyFips === "12086") {
    return "No sale on this parcel row. Last sale is not on the Miami-Dade parcel layer. The folio API is the sales source and was not copied here.";
  }
  if (countyFips === "12011") {
    return "No sale on this Broward row. BCPA MapServer/16 is folio and geometry. Countywide sales are the FDOR CO_NO=16 join, not this polygon.";
  }
  return null;
}
