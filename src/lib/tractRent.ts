import { formatUsd } from "./format";

/**
 * Tract rent joined from public series. Every value is a plain number.
 * Join codes, ZIP, and county ids (j, z, c) stay in the fixture files and
 * are not copied onto features that reach the browser.
 *
 * A tract missing from a file has no property for that series. Zero is not
 * written as a stand-in. Mississippi (FIPS 28) is absent from the current
 * files and is stamped automatically when a later build adds it.
 */

export const ACS_MEDIAN_GROSS_RENT_TOP_CODE = 3501;

export type TractRentFields = {
  /** ACS 5-year 2020–2024 B25064 median gross rent. 3501 means $3,500+. */
  medianGrossRent?: number;
  medianGrossRentMoe?: number;
  /** Nominal percent change versus 2015–2019 where the tract footprint matches. */
  medianGrossRentGrowth?: number;
  /** HUD FY2026 Small Area FMR, 2-bedroom. */
  safmr2Br?: number;
  /** Zillow ZORI multifamily 5+, August 2026, metro-wide. */
  zoriMf5Plus?: number;
  zoriMf5PlusGrowth?: number;
  /** Zillow ZORI all home types, August 2026, ZIP with county fallback. */
  zoriAll?: number;
  zoriAllGrowth?: number;
  /** Apartment List overall median, September 2026, county or metro. */
  apartmentListCountyRent?: number;
  apartmentListCountyRentGrowth?: number;
};

export type TractRentMinimums = {
  minMedianGrossRent: number;
  minMedianGrossRentGrowth: number;
  minSafmr2Br: number;
  minZoriMf5Plus: number;
  minZoriMf5PlusGrowth: number;
  minZoriAll: number;
  minZoriAllGrowth: number;
  minApartmentListCountyRent: number;
  minApartmentListCountyRentGrowth: number;
};

export const DEFAULT_RENT_MINIMUMS: TractRentMinimums = {
  minMedianGrossRent: 0,
  minMedianGrossRentGrowth: 0,
  minSafmr2Br: 0,
  minZoriMf5Plus: 0,
  minZoriMf5PlusGrowth: 0,
  minZoriAll: 0,
  minZoriAllGrowth: 0,
  minApartmentListCountyRent: 0,
  minApartmentListCountyRentGrowth: 0,
};

export type RentMetricKind = "level" | "moe" | "growth";

export type RentSourceField = {
  from: "e" | "m" | "g";
  to: keyof TractRentFields;
  kind: RentMetricKind;
};

export type RentSource = {
  file: string;
  fields: readonly RentSourceField[];
};

/** Fixture names and the numeric fields copied onto tract features. */
export const TRACT_RENT_SOURCES: readonly RentSource[] = [
  {
    file: "acs-b25064-tracts.json",
    fields: [
      { from: "e", to: "medianGrossRent", kind: "level" },
      { from: "m", to: "medianGrossRentMoe", kind: "moe" },
      { from: "g", to: "medianGrossRentGrowth", kind: "growth" },
    ],
  },
  {
    file: "hud-safmr-2br-tracts.json",
    fields: [{ from: "e", to: "safmr2Br", kind: "level" }],
  },
  {
    file: "zillow-zori-mf-tracts.json",
    fields: [
      { from: "e", to: "zoriMf5Plus", kind: "level" },
      { from: "g", to: "zoriMf5PlusGrowth", kind: "growth" },
    ],
  },
  {
    file: "zillow-zori-all-tracts.json",
    fields: [
      { from: "e", to: "zoriAll", kind: "level" },
      { from: "g", to: "zoriAllGrowth", kind: "growth" },
    ],
  },
  {
    file: "apartmentlist-county-tracts.json",
    fields: [
      { from: "e", to: "apartmentListCountyRent", kind: "level" },
      { from: "g", to: "apartmentListCountyRentGrowth", kind: "growth" },
    ],
  },
];

export type RentSliderFormat = "dollars" | "percent";

export type RentSlider = {
  key: keyof TractRentMinimums;
  property: keyof TractRentFields;
  label: string;
  note: string;
  min: number;
  max: number;
  step: number;
  format: RentSliderFormat;
};

export const RENT_SLIDERS: readonly RentSlider[] = [
  {
    key: "minMedianGrossRent",
    property: "medianGrossRent",
    label: "ACS median gross rent",
    note: "ACS 5-year 2020–2024 table B25064, in 2024 dollars. A value of 3501 is the Census top-code and shows as $3,500+.",
    min: 0,
    max: 3500,
    step: 50,
    format: "dollars",
  },
  {
    key: "minMedianGrossRentGrowth",
    property: "medianGrossRentGrowth",
    label: "ACS median gross rent growth",
    note: "Percent change versus 2015–2019 where the 2020 tract matches one 2010 tract. Not inflation-adjusted. Split and merged tracts have no growth.",
    min: 0,
    max: 100,
    step: 1,
    format: "percent",
  },
  {
    key: "minSafmr2Br",
    property: "safmr2Br",
    label: "HUD SAFMR 2BR",
    note: "HUD FY2026 Small Area FMR, 2-bedroom, revised and effective May 21, 2026. ZIP where a ZCTA matches; otherwise the county FMR.",
    min: 0,
    max: 4000,
    step: 50,
    format: "dollars",
  },
  {
    key: "minZoriMf5Plus",
    property: "zoriMf5Plus",
    label: "Zillow MF 5+ (metro)",
    note: "Zillow MF 5+ is metro-wide (August 2026); rural non-metro tracts often have no value.",
    min: 0,
    max: 3000,
    step: 50,
    format: "dollars",
  },
  {
    key: "minZoriMf5PlusGrowth",
    property: "zoriMf5PlusGrowth",
    label: "Zillow MF 5+ growth",
    note: "Year-over-year percent versus August 2025 for that metro ZORI.",
    min: 0,
    max: 10,
    step: 0.5,
    format: "percent",
  },
  {
    key: "minZoriAll",
    property: "zoriAll",
    label: "Zillow all homes (ZIP)",
    note: "Zillow ZORI all home types, August 2026, at ZIP with a county fallback. Separate from the metro multifamily series.",
    min: 0,
    max: 7500,
    step: 100,
    format: "dollars",
  },
  {
    key: "minZoriAllGrowth",
    property: "zoriAllGrowth",
    label: "Zillow all homes growth",
    note: "Year-over-year percent versus August 2025 for the ZIP or county ZORI.",
    min: 0,
    max: 20,
    step: 0.5,
    format: "percent",
  },
  {
    key: "minApartmentListCountyRent",
    property: "apartmentListCountyRent",
    label: "Apartment List",
    note: "Apartment List overall median, September 2026, at county or metro. Many rural counties have no value.",
    min: 0,
    max: 2000,
    step: 25,
    format: "dollars",
  },
  {
    key: "minApartmentListCountyRentGrowth",
    property: "apartmentListCountyRentGrowth",
    label: "Apartment List growth",
    note: "Year-over-year percent from the same September 2026 Apartment List release.",
    min: 0,
    max: 10,
    step: 0.5,
    format: "percent",
  },
];

const RENT_FIELD_KEYS = [
  "medianGrossRent",
  "medianGrossRentMoe",
  "medianGrossRentGrowth",
  "safmr2Br",
  "zoriMf5Plus",
  "zoriMf5PlusGrowth",
  "zoriAll",
  "zoriAllGrowth",
  "apartmentListCountyRent",
  "apartmentListCountyRentGrowth",
] as const satisfies readonly (keyof TractRentFields)[];

export function finiteRentMetric(value: unknown, kind: RentMetricKind): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  if (kind === "growth") return value;
  return value > 0 ? value : null;
}

/** Copies e, m, and g only. Join codes and geography ids are ignored. */
export function rentFieldsFromRow(
  row: Record<string, unknown> | null | undefined,
  fields: readonly RentSourceField[],
): TractRentFields {
  const stamp: TractRentFields = {};
  if (!row) return stamp;
  for (const field of fields) {
    const value = finiteRentMetric(row[field.from], field.kind);
    if (value != null) stamp[field.to] = value;
  }
  return stamp;
}

export function buildTractRentLookup(
  files: Record<string, { tracts?: Record<string, Record<string, unknown>> } | null | undefined>,
): Map<string, TractRentFields> {
  const lookup = new Map<string, TractRentFields>();
  for (const source of TRACT_RENT_SOURCES) {
    const tracts = files[source.file]?.tracts ?? {};
    for (const [geoid, row] of Object.entries(tracts)) {
      if (!geoid) continue;
      const stamp = rentFieldsFromRow(row, source.fields);
      if (Object.keys(stamp).length === 0) continue;
      const prior = lookup.get(geoid);
      lookup.set(geoid, prior ? { ...prior, ...stamp } : stamp);
    }
  }
  return lookup;
}

/**
 * MapLibre filter for one numeric property. A minimum of 0 is off and hides
 * nothing. A raised minimum hides features below it and features that lack
 * the property, the same way a raised income slider switches off unknowns.
 */
export function tractMinimumLayerFilter(property: string, minimum: number): unknown[] | null {
  if (!property || typeof minimum !== "number" || !Number.isFinite(minimum) || minimum <= 0) return null;
  return ["all", ["has", property], [">=", ["to-number", ["get", property]], minimum]];
}

/** Slider values plus the Yes/No gate. Off ignores every threshold. */
export type TractRentFilterInput = TractRentMinimums & {
  rentFiltersOn: boolean;
};

export function tractRentFilterActive(minimums: TractRentFilterInput): boolean {
  if (!minimums.rentFiltersOn) return false;
  return RENT_SLIDERS.some((slider) => minimums[slider.key] > 0);
}

export function tractRentLayerFilter(minimums: TractRentFilterInput): unknown[] | null {
  if (!minimums.rentFiltersOn) return null;
  const parts: unknown[][] = [];
  for (const slider of RENT_SLIDERS) {
    const part = tractMinimumLayerFilter(slider.property, minimums[slider.key]);
    if (part) parts.push(part);
  }
  if (parts.length === 0) return null;
  if (parts.length === 1) return parts[0];
  return ["all", ...parts];
}

export function tractRentPasses(value: number | null | undefined, minimum: number): boolean {
  if (!(minimum > 0)) return true;
  if (value == null || !Number.isFinite(value)) return false;
  return value >= minimum;
}

export function filterTractRowsByRent<T extends { geoid: string }>(
  rows: T[],
  rentByGeoid: Readonly<Record<string, Partial<TractRentFields>>>,
  minimums: TractRentFilterInput,
): T[] {
  if (!tractRentFilterActive(minimums)) return rows;
  return rows.filter((row) => {
    const rent = rentByGeoid[row.geoid];
    return RENT_SLIDERS.every((slider) => tractRentPasses(rent?.[slider.property], minimums[slider.key]));
  });
}

export function rentByGeoidFromFeatures(
  collections: Array<{ features: Array<{ properties: { tractGeoid?: string } & Partial<TractRentFields> }> }>,
): Record<string, TractRentFields> {
  const lookup: Record<string, TractRentFields> = {};
  for (const collection of collections) {
    for (const feature of collection.features) {
      const geoid = feature.properties.tractGeoid;
      if (!geoid) continue;
      const stamp: TractRentFields = {};
      let any = false;
      for (const key of RENT_FIELD_KEYS) {
        const value = feature.properties[key];
        if (typeof value === "number" && Number.isFinite(value)) {
          stamp[key] = value;
          any = true;
        }
      }
      if (!any) continue;
      lookup[geoid] = lookup[geoid] ? { ...lookup[geoid], ...stamp } : stamp;
    }
  }
  return lookup;
}

export function readRentMetric(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

export function formatRentGrowth(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  const text = rounded.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (rounded > 0) return `+${text}%`;
  return `${text}%`;
}

export function formatRentDollars(value: number, topCode = false): string {
  if (topCode && value === ACS_MEDIAN_GROSS_RENT_TOP_CODE) return "$3,500+";
  return formatUsd(value);
}

const RENT_INFO_ROWS: ReadonlyArray<{
  label: string;
  level: keyof TractRentFields;
  growth?: keyof TractRentFields;
  moe?: keyof TractRentFields;
  topCode?: boolean;
}> = [
  {
    label: "ACS median gross rent",
    level: "medianGrossRent",
    growth: "medianGrossRentGrowth",
    moe: "medianGrossRentMoe",
    topCode: true,
  },
  { label: "HUD SAFMR 2BR", level: "safmr2Br" },
  { label: "Zillow MF 5+ (metro)", level: "zoriMf5Plus", growth: "zoriMf5PlusGrowth" },
  { label: "Zillow all homes (ZIP)", level: "zoriAll", growth: "zoriAllGrowth" },
  { label: "Apartment List", level: "apartmentListCountyRent", growth: "apartmentListCountyRentGrowth" },
];

/** One labeled line per source. Missing levels are an em dash. */
export function formatTractRentLines(fields: Record<string, unknown> | Partial<TractRentFields> | null | undefined): string[] {
  const source = (fields ?? {}) as Record<string, unknown>;
  return RENT_INFO_ROWS.map((row) => {
    const level = readRentMetric(source[row.level]);
    if (level == null) return `${row.label}: —`;
    let text = formatRentDollars(level, row.topCode === true);
    if (row.moe && level !== ACS_MEDIAN_GROSS_RENT_TOP_CODE) {
      const moe = readRentMetric(source[row.moe]);
      if (moe != null) text += ` ± ${formatUsd(moe)}`;
    }
    if (row.growth) {
      const growth = readRentMetric(source[row.growth]);
      text += growth == null ? " · —" : ` · ${formatRentGrowth(growth)}`;
    }
    return `${row.label}: ${text}`;
  });
}

export function formatRentSliderValue(slider: RentSlider, value: number): string {
  if (!(value > 0)) return "No minimum";
  if (slider.format === "percent") {
    const digits = slider.step < 1 ? 1 : 0;
    return `${value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%+`;
  }
  return `$${Math.round(value).toLocaleString("en-US")}+`;
}

/** Empty-list copy when income and/or rent minima removed every tract in the current county filter. */
export function tractMetricEmptyMessage(tractNoun: string, incomeActive: boolean, rentActive: boolean): string | null {
  if (!incomeActive && !rentActive) return null;
  if (incomeActive && rentActive) {
    return `No ${tractNoun} tracts pass the income and rent filters. ACS 5-year 2020–2024 B19013 is joined where that Southeast table has an estimate. A rent minimum hides tracts below it and tracts with no value for that source. Tracts without a joined median stay visible when Include unknown income is on.`;
  }
  if (incomeActive) {
    return `No ${tractNoun} tracts pass the median-income filter. ACS 5-year 2020–2024 B19013 is joined where that Southeast table has an estimate. Tracts without that attribute stay visible when Include unknown income is on.`;
  }
  return `No ${tractNoun} tracts pass the rent filter. A raised minimum hides tracts below it and tracts with no value for that source.`;
}
