/**
 * Manatee and Sarasota city zoning and future land use.
 * Codes come from data/manatee-sarasota-municipal.json. This module does not
 * invent a district, a county plan code, a school grade, a base flood elevation,
 * or an Opportunity Zone.
 */

export const MANATEE_SARASOTA_ZONING_EMPTY =
  "No Bradenton, Palmetto, Longboat Key, Sarasota, North Port, or Venice zoning covers this parcel. Anna Maria, Bradenton Beach, and Holmes Beach have no city zoning service.";

export const MANATEE_SARASOTA_FLU_EMPTY =
  "No Bradenton, Palmetto, Longboat Key, or Sarasota future land use covers this parcel. North Port and Venice future land use are still gaps.";

const FIPS = new Set(["12081", "12115"]);

export function zoningEmptyForManateeSarasota(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips && FIPS.has(countyFips)) return MANATEE_SARASOTA_ZONING_EMPTY;
  return fallback;
}

export function fluEmptyForManateeSarasota(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips && FIPS.has(countyFips)) return MANATEE_SARASOTA_FLU_EMPTY;
  return fallback;
}
