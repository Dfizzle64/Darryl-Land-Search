import { fluAllowsMultifamily } from "./flu";
import { parcelInOpportunityZone } from "./opportunityZone";
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

export function fluPasses(feature: ParcelFeature, _filters: FilterState, fluConfig: FluConfig): boolean | null {
  return fluAllowsMultifamily(feature.properties.flu, fluConfig, true);
}

/**
 * FLU supports multifamily / higher density, but current zoning is not
 * MF-capable under the PD / conditional toggles. Missing FLU is never a match.
 */
export function isRezoningCandidate(
  feature: ParcelFeature,
  filters: FilterState,
  zoningConfig: ZoningConfig,
  fluConfig: FluConfig,
): boolean {
  const flu = fluPasses(feature, filters, fluConfig);
  if (flu !== true) return false;
  return !zoningPasses(feature, filters, zoningConfig);
}

export function describeRezoningCandidate(
  feature: ParcelFeature,
  filters: FilterState,
  zoningConfig: ZoningConfig,
  fluConfig: FluConfig,
): { isCandidate: boolean; label: string | null; reason: string } {
  const flu = fluPasses(feature, filters, fluConfig);
  const zoning = zoningPasses(feature, filters, zoningConfig);
  const zoningCode = feature.properties.zoningCode || feature.properties.zoningDistrict || "unknown zoning";
  const fluCode = feature.properties.flu?.label || feature.properties.flu?.code;

  if (flu == null) {
    return {
      isCandidate: false,
      label: null,
      reason:
        "FLU is not joined for this parcel, so it cannot be classified as a rezoning candidate. Municipal FLU besides Orlando is a known gap.",
    };
  }
  if (flu && !zoning) {
    return {
      isCandidate: true,
      label: `Rezoning candidate: FLU ${fluCode ?? "MF-supportive"} / Zoning ${zoningCode}`,
      reason: `Future Land Use supports multifamily / higher density (${fluCode}), but current zoning (${zoningCode}) is not treated as MF-capable. Confirm a rezoning or PD amendment — this is a screen, not an entitlement.`,
    };
  }
  if (flu && zoning) {
    return {
      isCandidate: false,
      label: null,
      reason: `Not a rezoning candidate — current zoning is already MF-capable and FLU ${fluCode} also supports multifamily.`,
    };
  }
  if (!flu && !zoning) {
    return {
      isCandidate: false,
      label: null,
      reason: `Not a rezoning candidate — FLU ${fluCode} is not treated as multifamily-supportive, and current zoning is not MF-capable.`,
    };
  }
  return {
    isCandidate: false,
    label: null,
    reason: `Not a rezoning candidate — current zoning is MF-capable, but FLU ${fluCode} is not treated as multifamily-supportive.`,
  };
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
  if (filters.landUseFilter === "non-mf") return !zoning;
  if (filters.landUseFilter === "rezoning") {
    return isRezoningCandidate(feature, filters, zoningConfig, fluConfig);
  }
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

function ozPasses(feature: ParcelFeature, filters: FilterState): boolean {
  if (filters.ozFilter === "either") return true;
  const inOz = parcelInOpportunityZone(feature);
  if (filters.ozFilter === "in") return inOz === true;
  return inOz === false;
}

export function parcelMatchesFilters(
  feature: ParcelFeature,
  filters: FilterState,
  zoningConfig: ZoningConfig,
  fluConfig: FluConfig,
): boolean {
  if (!landUsePasses(feature, filters, zoningConfig, fluConfig)) return false;
  if (!ozPasses(feature, filters)) return false;

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
  if (filters.landUseFilter === "rezoning") {
    return "No rezoning candidates match: that mode needs joined FLU that supports multifamily / higher density and current zoning that is not MF-capable. Municipal FLU besides Orlando is often missing — those parcels are omitted rather than guessed. Try All parcels or Non-multifamily zoning, or turn FLU-unknown jurisdictions off your mental map.";
  }
  if (filters.landUseFilter === "flu" && fluUnknownCount > 0) {
    return "No joined FLU designations in this sample currently match the multifamily-supportive list. Municipal FLU besides Orlando is a known gap — try Either, or turn land-use filtering off.";
  }
  if (filters.ozFilter === "in") {
    return "No matching parcels sit in a Qualified Opportunity Zone under the current filters. Clear the OZ filter or lower acreage / income / AADT thresholds.";
  }
  if (filters.landUseFilter === "non-mf") {
    return "No non-multifamily parcels match the other filters. Lower acreage, income, or AADT, or switch to All parcels.";
  }
  return "Lower the acreage, income, or AADT thresholds, include planned development or conditional zoning, or switch the land-use mode to All parcels / Either.";
}
