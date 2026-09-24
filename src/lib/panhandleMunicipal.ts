/**
 * Panhandle city zoning and future land use.
 * Codes come from data/panhandle-municipal.json. This module does not invent
 * a district, a Freeport integer, a school grade, a base flood elevation, or
 * an Opportunity Zone.
 */

export const PANHANDLE_ZONING_EMPTY =
  "No Destin, Fort Walton Beach, DeFuniak Springs, Milton, Gulf Breeze, Jay, or Pensacola zoning covers this parcel. Freeport codes are not stored.";

export const PANHANDLE_FLU_EMPTY =
  "No Destin, Fort Walton Beach, DeFuniak Springs, Gulf Breeze, or Paxton future land use covers this parcel. Pensacola, Milton, and Jay future land use are still gaps.";

const FIPS = new Set(["12005", "12033", "12091", "12113", "12131"]);

export function zoningEmptyForPanhandle(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips && FIPS.has(countyFips)) return PANHANDLE_ZONING_EMPTY;
  return fallback;
}

export function fluEmptyForPanhandle(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips && FIPS.has(countyFips)) return PANHANDLE_FLU_EMPTY;
  return fallback;
}
