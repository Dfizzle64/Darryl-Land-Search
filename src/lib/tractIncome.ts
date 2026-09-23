import type { FilterState, IncomeGeography } from "./types";

/**
 * Numeric tract filtering.
 *
 * Eligible-tract GeoJSON does not carry acreage or AADT. Those sliders stay
 * parcel-only. Median household income exists only where a tract GEOID is in
 * the Orange County ACS fixture (`income-tracts.geojson`). Other tracts are
 * unknown income, not a fabricated zero.
 */
export function tractIncomePasses(
  income: number | null | undefined,
  minIncome: number,
  includeUnknownIncome: boolean,
): boolean {
  if (income == null || !Number.isFinite(income)) return includeUnknownIncome;
  return income >= minIncome;
}

/** Block-group income is a parcel attribute. Tract overlays use tract medians only. */
export function tractIncomeFilterActive(
  geography: IncomeGeography,
  minIncome: number,
  includeUnknownIncome: boolean,
): boolean {
  if (geography !== "tract") return false;
  return minIncome > 0 || !includeUnknownIncome;
}

export function filterTractRowsByIncome<T extends { geoid: string }>(
  rows: T[],
  incomeByGeoid: Readonly<Record<string, number>>,
  filters: Pick<FilterState, "incomeGeography" | "minIncome" | "includeUnknownIncome">,
): T[] {
  if (!tractIncomeFilterActive(filters.incomeGeography, filters.minIncome, filters.includeUnknownIncome)) {
    return rows;
  }
  return rows.filter((row) => {
    const income = incomeByGeoid[row.geoid];
    return tractIncomePasses(income, filters.minIncome, filters.includeUnknownIncome);
  });
}

/**
 * MapLibre filter for layers whose features were stamped with
 * `medianHouseholdIncome` only when the Orange County ACS fixture has that GEOID.
 * Returns null when the income slider should not touch tracts.
 */
export function tractIncomeLayerFilter(
  geography: IncomeGeography,
  minIncome: number,
  includeUnknownIncome: boolean,
): unknown[] | null {
  if (!tractIncomeFilterActive(geography, minIncome, includeUnknownIncome)) return null;
  const known: unknown[] = [
    "all",
    ["has", "medianHouseholdIncome"],
    [">=", ["to-number", ["get", "medianHouseholdIncome"]], minIncome],
  ];
  if (!includeUnknownIncome) return known;
  return ["any", ["!", ["has", "medianHouseholdIncome"]], known];
}

export function incomeByGeoidFromFeatures(
  collections: Array<{ features: Array<{ properties: { tractGeoid?: string; medianHouseholdIncome?: number | null } }> }>,
): Record<string, number> {
  const lookup: Record<string, number> = {};
  for (const collection of collections) {
    for (const feature of collection.features) {
      const geoid = feature.properties.tractGeoid;
      const income = feature.properties.medianHouseholdIncome;
      if (geoid && typeof income === "number" && Number.isFinite(income)) lookup[geoid] = income;
    }
  }
  return lookup;
}
