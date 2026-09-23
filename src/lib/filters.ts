import { fluAllowsMultifamily } from "./flu";
import { parcelInOpportunityZone, parcelOz2Eligibility } from "./opportunityZone";
import { zoningAllowsMultifamily } from "./zoning";
import {
  DEFAULT_FILTERS,
  LAND_USE_FILTERS,
  OZ_FILTERS,
  type FilterState,
  type FluConfig,
  type ParcelFeature,
  type ZoningConfig,
} from "./types";

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

/** Parcel OZ and zoning radios apply only while their master switches are on. */
export function appliedParcelFilters(filters: FilterState): FilterState {
  return {
    ...filters,
    ozFilter: filters.considerOpportunityZone ? filters.ozFilter : "either",
    landUseFilter: filters.considerZoning ? filters.landUseFilter : "off",
  };
}

function ozPasses(feature: ParcelFeature, filters: FilterState): boolean {
  if (filters.ozFilter === "either") return true;
  if (filters.ozFilter === "in" || filters.ozFilter === "out") {
    const inOz = parcelInOpportunityZone(feature);
    if (filters.ozFilter === "in") return inOz === true;
    return inOz === false;
  }
  const oz2 = parcelOz2Eligibility(feature);
  if (!oz2) return false;
  if (filters.ozFilter === "rural-eligible") return oz2.eligible === true && oz2.rural === true;
  if (filters.ozFilter === "non-rural-eligible") return oz2.eligible === true && oz2.rural === false;
  return true;
}

export function parcelMatchesFilters(
  feature: ParcelFeature,
  filters: FilterState,
  zoningConfig: ZoningConfig,
  fluConfig: FluConfig,
): boolean {
  const applied = appliedParcelFilters(filters);
  if (!landUsePasses(feature, applied, zoningConfig, fluConfig)) return false;
  if (!ozPasses(feature, applied)) return false;

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

/** Stable key so viewport and AOI requests refetch when a slider moves. */
export function parcelFilterKey(filters: FilterState): string {
  return [
    filters.considerOpportunityZone ? 1 : 0,
    filters.considerZoning ? 1 : 0,
    filters.landUseFilter,
    filters.includePlannedDevelopment ? 1 : 0,
    filters.includeConditionalZoning ? 1 : 0,
    filters.ozFilter,
    filters.minAcreage,
    filters.includeUnknownAcreage ? 1 : 0,
    filters.minIncome,
    filters.incomeGeography,
    filters.includeUnknownIncome ? 1 : 0,
    filters.minAadt,
    filters.includeUnknownAadt ? 1 : 0,
  ].join("|");
}

function finiteNumber(value: string | null, fallback: number): number {
  if (value == null || value.trim() === "") return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

/** Query-string form shared by the map client and `/api/parcels`. */
export function writeParcelFilters(
  params: URLSearchParams,
  filters: FilterState,
  includeExcluded = false,
): void {
  params.set("filter", "1");
  params.set("ozOn", filters.considerOpportunityZone ? "1" : "0");
  params.set("zoneOn", filters.considerZoning ? "1" : "0");
  params.set("landUse", filters.landUseFilter);
  params.set("pd", filters.includePlannedDevelopment ? "1" : "0");
  params.set("cond", filters.includeConditionalZoning ? "1" : "0");
  params.set("oz", filters.ozFilter);
  params.set("minAcres", String(filters.minAcreage));
  params.set("unkAcres", filters.includeUnknownAcreage ? "1" : "0");
  params.set("minIncome", String(filters.minIncome));
  params.set("geo", filters.incomeGeography);
  params.set("unkIncome", filters.includeUnknownIncome ? "1" : "0");
  params.set("minAadt", String(filters.minAadt));
  params.set("unkAadt", filters.includeUnknownAadt ? "1" : "0");
  if (includeExcluded) params.set("includeExcluded", "1");
}

export function parcelFiltersFromSearchParams(params: { get(name: string): string | null }): FilterState {
  const geo = params.get("geo");
  return {
    considerOpportunityZone: params.get("ozOn") === "1",
    considerZoning: params.get("zoneOn") === "1",
    landUseFilter: landUseParam(params.get("landUse") ?? params.get("mf")),
    includePlannedDevelopment: params.get("pd") !== "0",
    includeConditionalZoning: params.get("cond") === "1",
    ozFilter: ozParam(params.get("oz")),
    minAcreage: finiteNumber(params.get("minAcres"), DEFAULT_FILTERS.minAcreage),
    includeUnknownAcreage: params.get("unkAcres") !== "0",
    minIncome: finiteNumber(params.get("minIncome"), DEFAULT_FILTERS.minIncome),
    incomeGeography: geo === "blockGroup" ? "blockGroup" : "tract",
    includeUnknownIncome: params.get("unkIncome") !== "0",
    minAadt: finiteNumber(params.get("minAadt"), DEFAULT_FILTERS.minAadt),
    includeUnknownAadt: params.get("unkAadt") !== "0",
  };
}

function landUseParam(value: string | null): FilterState["landUseFilter"] {
  if (value && (LAND_USE_FILTERS as string[]).includes(value)) {
    return value as FilterState["landUseFilter"];
  }
  if (value === "0" || value === "all") return "off";
  if (value === "mf") return "zoning";
  return DEFAULT_FILTERS.landUseFilter;
}

function ozParam(value: string | null): FilterState["ozFilter"] {
  if (value && (OZ_FILTERS as string[]).includes(value)) {
    return value as FilterState["ozFilter"];
  }
  return DEFAULT_FILTERS.ozFilter;
}

/**
 * MapLibre `in` filters with thousands of ids fail open on a dense viewport,
 * so non-matching parcels stay drawn. A single property check does not.
 */
export function stampFilterMatch(
  features: ParcelFeature[],
  filters: FilterState,
  zoningConfig: ZoningConfig,
  fluConfig: FluConfig,
): ParcelFeature[] {
  return features.map((feature) => ({
    ...feature,
    properties: {
      ...feature.properties,
      filterMatch: parcelMatchesFilters(feature, filters, zoningConfig, fluConfig) ? 1 : 0,
    },
  }));
}

export function emptyStateHint(filters: FilterState, matched: number, fluUnknownCount: number): string | null {
  if (matched > 0) return null;
  filters = appliedParcelFilters(filters);
  if (filters.landUseFilter === "rezoning") {
    return "No rezoning candidates match: that mode needs joined FLU that supports multifamily / higher density and current zoning that is not MF-capable. Municipal FLU besides Orlando is often missing — those parcels are omitted rather than guessed. Try All parcels or Non-multifamily zoning, or turn FLU-unknown jurisdictions off your mental map.";
  }
  if (filters.landUseFilter === "flu" && fluUnknownCount > 0) {
    return "No joined FLU designations in this view currently match the multifamily-supportive list. Municipal FLU besides Orlando is a known gap — try Either, or turn land-use filtering off.";
  }
  if (filters.ozFilter === "in") {
    return "No matching parcels sit in a current designated Qualified Opportunity Zone under the other filters. Clear the OZ filter or lower acreage / income / AADT thresholds.";
  }
  if (filters.ozFilter === "rural-eligible") {
    return "No matching parcels have a centroid in an OZ 2.0 rural-eligible tract. In Orange County, Rev. Proc. 2026-14 rural-eligible is census tract 12095016605 (eligible for nomination, not a designated 2027 QOZ). Try All parcels if the land-use mode is hiding it, or clear the OZ filter.";
  }
  if (filters.ozFilter === "non-rural-eligible") {
    return "No matching parcels have a centroid in an OZ 2.0 eligible tract that Rev. Proc. 2026-14 marks Non-rural. Try All parcels, or clear the OZ filter.";
  }
  if (filters.landUseFilter === "non-mf") {
    return "No non-multifamily parcels match the other filters. Lower acreage, income, or AADT, or switch to All parcels.";
  }
  return "Lower the acreage, income, or AADT thresholds, include planned development or conditional zoning, or switch the land-use mode to All parcels / Either.";
}
