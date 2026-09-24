/**
 * Seminole County, Florida city zoning and future land use.
 * Codes come from data/seminole-municipal.json. This module does not invent
 * a district, a county Land_Use CITY stub, or an Opportunity Zone.
 */

export const SEMINOLE_ZONING_EMPTY =
  "No Casselberry, Winter Springs, Lake Mary, Sanford, Oviedo, or Altamonte Springs zoning covers this parcel. Longwood has no public zoning service. County Land_Use CITY stubs are not stored.";

export const SEMINOLE_FLU_EMPTY =
  "No city future land use covers this parcel. Seminole County future land use was not copied in, and Longwood has no public future land use service.";

export function zoningEmptyForSeminole(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips === "12117") return SEMINOLE_ZONING_EMPTY;
  return fallback;
}

export function fluEmptyForSeminole(countyFips: string | null | undefined, fallback: string): string {
  if (countyFips === "12117") return SEMINOLE_FLU_EMPTY;
  return fallback;
}
