import { fluAllowsMultifamily } from "./flu";
import { zoningAllowsMultifamily } from "./zoning";
import type { FilterState, FluConfig, ParcelFeature, ZoningConfig } from "./types";

export function parcelIncome(feature: ParcelFeature, geography: FilterState["incomeGeography"]): number | null {
  const info = geography === "tract" ? feature.properties.incomeTract : feature.properties.incomeBlockGroup;
  return info?.medianHouseholdIncome ?? null;
}

export function parcelAadt(feature: ParcelFeature): number | null {
  return feature.properties.nearestRoad?.aadt ?? null;
}

export function parcelAcreage(feature: ParcelFeature): number | null {
  const value = feature.properties.acreage;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function zoningPasses(feature: ParcelFeature, filters: FilterState, zoningConfig: ZoningConfig): boolean {
  return zoningAllowsMultifamily(
    feature.properties.zoningCode,
    feature.properties.zoningDistrict,
    zoningConfig,
    filters.includePlannedDevelopment,
    filters.includeConditionalZoning,
  );
}

export function fluPasses(feature: ParcelFeature, filters: FilterState, fluConfig: FluConfig): boolean | null {
  return fluAllowsMultifamily(feature.properties.flu, fluConfig, true);
}

function landUsePasses(
  feature: ParcelFeature,
  filters: FilterState,
  zoningConfig: ZoningConfig,
  fluConfig: FluConfig,
): boolean {
  if (filters.landUseFilter === "off") return true;
  const zoning = zoningPasses(feature, filters, zoningConfig);
  const flu = fluPasses(feature, filters, fluConfig);

  if (filters.landUseFilter === "zoning") return zoning;
  if (filters.landUseFilter === "flu") {
    if (flu == null) return false;
    return flu;
  }
  if (filters.landUseFilter === "either") {
    if (zoning) return true;
    if (flu === true) return true;
    return false;
  }
  if (flu == null) return false;
  return zoning && flu;
}

export function parcelMatchesFilters(
  feature: ParcelFeature,
  filters: FilterState,
  zoningConfig: ZoningConfig,
  fluConfig: FluConfig,
): boolean {
  if (!landUsePasses(feature, filters, zoningConfig, fluConfig)) return false;

  const acreage = parcelAcreage(feature);
  if (acreage == null) {
    if (!filters.includeUnknownAcreage) return false;
  } else if (acreage < filters.minAcreage) {
    return false;
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
  fluConfig: FluConfig,
): ParcelFeature[] {
  return features.filter((feature) => parcelMatchesFilters(feature, filters, zoningConfig, fluConfig));
}

export function emptyStateHint(filters: FilterState, matched: number, fluUnknownCount: number): string | null {
  if (matched > 0) return null;
  if (filters.landUseFilter === "flu" && fluUnknownCount > 0) {
    return "No joined FLU designations in this sample currently match the multifamily-supportive list. Municipal FLU besides Orlando is a known gap — try Either, or turn land-use filtering off.";
  }
  return "Lower the acreage, income, or AADT thresholds, include planned development or conditional zoning, or switch the land-use mode to Either / Off.";
}
