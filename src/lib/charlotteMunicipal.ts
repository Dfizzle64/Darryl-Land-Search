/**
 * Punta Gorda zoning and future land use for Charlotte County, Florida.
 * Codes come from data/charlotte-municipal.json. This module does not invent
 * a district, a county CITY stub, a school grade, a base flood elevation, or
 * an Opportunity Zone.
 */

export const CHARLOTTE_ZONING_EMPTY =
  "No Punta Gorda zoning covers this parcel. County ZONE_ CITY is not stored.";

export const CHARLOTTE_FLU_EMPTY =
  "No Punta Gorda future land use covers this parcel. County NEWLU City is not stored.";

const FIPS = new Set(["12015"]);

export function zoningEmptyForCharlotte(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips && FIPS.has(countyFips)) return CHARLOTTE_ZONING_EMPTY;
  return fallback;
}

export function fluEmptyForCharlotte(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips && FIPS.has(countyFips)) return CHARLOTTE_FLU_EMPTY;
  return fallback;
}
