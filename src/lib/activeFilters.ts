import type { ScreeningToggles } from "./screening";
import { DEFAULT_SCREENING_TOGGLES } from "./screening";
import { RENT_SLIDERS } from "./tractRent";
import { DEFAULT_FILTERS, type FilterState, type LandUseFilter } from "./types";

export type ActiveFilterInput = {
  filters: FilterState;
  /** Land-use value Restore uses. Orlando resets to off; other markets use the type default. */
  resetLandUse: LandUseFilter;
  showExcluded: boolean;
  showTraffic: boolean;
  showOz: boolean;
  showOz2: boolean;
  screening: ScreeningToggles;
};

/**
 * How many sidebar controls differ from the idle map. Master switches count
 * on their own. A raised slider counts only while its Yes/No switch is on,
 * matching what the sidebar actually applies.
 */
export function countActiveFilters(input: ActiveFilterInput): number {
  const { filters } = input;
  let count = 0;

  if (filters.considerOpportunityZone) count += 1;
  if (filters.considerOpportunityZone && filters.ozFilter !== DEFAULT_FILTERS.ozFilter) count += 1;
  if (input.showOz2 !== true) count += 1;
  if (input.showOz) count += 1;

  (Object.keys(DEFAULT_SCREENING_TOGGLES) as (keyof ScreeningToggles)[]).forEach((key) => {
    if (input.screening[key]) count += 1;
  });

  if (filters.considerZoning) count += 1;
  if (filters.considerZoning && filters.landUseFilter !== input.resetLandUse) count += 1;
  if (filters.considerZoning && filters.includePlannedDevelopment !== DEFAULT_FILTERS.includePlannedDevelopment) {
    count += 1;
  }
  if (filters.considerZoning && filters.includeConditionalZoning !== DEFAULT_FILTERS.includeConditionalZoning) {
    count += 1;
  }

  if (filters.minAcreage > 0) count += 1;
  if (!filters.includeUnknownAcreage) count += 1;
  if (filters.incomeGeography !== DEFAULT_FILTERS.incomeGeography) count += 1;
  if (filters.minIncome > 0) count += 1;
  if (!filters.includeUnknownIncome) count += 1;

  if (filters.rentFiltersOn) {
    count += 1;
    for (const slider of RENT_SLIDERS) {
      if (filters[slider.key] > 0) count += 1;
    }
  }

  if (filters.minAadt > 0) count += 1;
  if (!filters.includeUnknownAadt) count += 1;
  if (!input.showTraffic) count += 1;
  if (input.showExcluded) count += 1;

  return count;
}

/** Badge copy. Zero stays visible so the control always says how many are on. */
export function activeFiltersLabel(count: number): string {
  return `${count} ${count === 1 ? "filter" : "filters"} active`;
}
