/**
 * Treasure Coast parcel labels. Eligible nomination tracts are not designated QOZs.
 * City of Ocoee is not Okeechobee County. Melbourne here is Brevard County, Florida.
 */

export const TREASURE_COAST_FIPS = ["12061", "12111", "12009", "12085", "12093"] as const;

export type TreasureCoastFips = (typeof TREASURE_COAST_FIPS)[number];

const LABELS: Record<TreasureCoastFips, string> = {
  "12061": "Open Indian River County Property Appraiser",
  "12111": "Open St. Lucie County Property Appraiser",
  "12009": "Open Brevard County Property Appraiser",
  "12085": "Open Martin County property record",
  "12093": "Open Okeechobee County Property Appraiser GIS",
};

export function isTreasureCoastFips(fips: string | null | undefined): fips is TreasureCoastFips {
  return Boolean(fips && (TREASURE_COAST_FIPS as readonly string[]).includes(fips));
}

export function treasureCoastAppraiserLabel(fips: string | null | undefined): string | null {
  if (!isTreasureCoastFips(fips)) return null;
  return LABELS[fips];
}

export function zoningLine(properties: {
  countyFips?: string | null;
  zoningCode?: string | null;
  jurisdictionCode?: string | null;
}): string | null {
  if (!properties.zoningCode) return null;
  if (!isTreasureCoastFips(properties.countyFips) || !properties.jurisdictionCode) {
    return properties.zoningCode;
  }
  return `${properties.zoningCode} · ${properties.jurisdictionCode}`;
}

export function zoningEmptyMessage(
  fips: string | null | undefined,
  jurisdiction: string | null | undefined,
): string | null {
  if (!isTreasureCoastFips(fips)) return null;
  if (jurisdiction && !/^unincorporated/i.test(jurisdiction) && jurisdiction !== "Okeechobee County") {
    return `No public ${jurisdiction} zoning polygon contains this parcel. County districts are not copied into a city layer.`;
  }
  if (fips === "12009") {
    return "No Brevard Accela unincorporated zoning polygon contains this parcel. Accela zoning is not a city ordinance.";
  }
  if (fips === "12093") {
    return "No Okeechobee County zoning polygon contains this parcel. This is not City of Ocoee zoning.";
  }
  return "No unincorporated zoning polygon contains this parcel.";
}

export function fluEmptyMessage(
  fips: string | null | undefined,
  jurisdiction: string | null | undefined,
): string | null {
  if (!isTreasureCoastFips(fips)) return null;
  if (jurisdiction && !/^unincorporated/i.test(jurisdiction) && jurisdiction !== "Okeechobee County") {
    return `No public ${jurisdiction} future land use layer contains this parcel.`;
  }
  return "No unincorporated future land use polygon contains this parcel. Eligible tracts are not designated QOZs.";
}
