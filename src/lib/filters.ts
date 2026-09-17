import { zoningAllowsMultifamily } from "./zoning";
import type { FilterState, ParcelFeature, ZoningConfig } from "./types";

export function parcelIncome(feature: ParcelFeature, geography: FilterState["incomeGeography"]): number | null {
  const info = geography === "tract" ? feature.properties.incomeTract : feature.properties.incomeBlockGroup;
  return info?.medianHouseholdIncome ?? null;
}

export function parcelAadt(feature: ParcelFeature): number | null {
  return feature.properties.nearestRoad?.aadt ?? null;
}

export function parcelMatchesFilters(
  feature: ParcelFeature,
  filters: FilterState,
  zoningConfig: ZoningConfig,
): boolean {
  if (filters.multifamilyZoningOnly) {
    const allowed = zoningAllowsMultifamily(
      feature.properties.zoningCode,
      feature.properties.zoningDistrict,
      zoningConfig,
      filters.includePlannedDevelopment,
    );
    if (!allowed) return false;
  }

  const income = parcelIncome(feature, filters.incomeGeography);
  if (income == null) {
    if (!filters.includeUnknownIncome) return false;
  } else if (income < filters.minIncome) {
    return false;
  }

  const aadt = parcelAadt(feature);
  if (aadt == null) {
    if (!filters.includeUnknownAadt) return false;
  } else if (aadt < filters.minAadt) {
    return false;
  }

  return true;
}

export function filterParcels(
  features: ParcelFeature[],
  filters: FilterState,
  zoningConfig: ZoningConfig,
): ParcelFeature[] {
  return features.filter((feature) => parcelMatchesFilters(feature, filters, zoningConfig));
}
