/**
 * Martin and Indian River city zoning and future land use.
 * Codes come from data/martin-irc-municipal.json. This module does not invent
 * a district, a county town-name stub, or an Opportunity Zone.
 */

export const MARTIN_IRC_ZONING_EMPTY =
  "No Stuart, Indiantown, Vero Beach, or Sebastian zoning covers this parcel. Sewall's Point, Jupiter Island, Ocean Breeze, Fellsmere, Indian River Shores, and Orchid stay blank. County town-name stubs are not stored.";

export const MARTIN_IRC_FLU_EMPTY =
  "No Stuart, Indiantown, or Vero Beach future land use covers this parcel. Sebastian future land use is still a gap. County NO DATA is not stored.";

const FIPS = new Set(["12085", "12061"]);

export function zoningEmptyForMartinIrc(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips && FIPS.has(countyFips)) return MARTIN_IRC_ZONING_EMPTY;
  return fallback;
}

export function fluEmptyForMartinIrc(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips && FIPS.has(countyFips)) return MARTIN_IRC_FLU_EMPTY;
  return fallback;
}
