import { RURAL_ELIGIBLE_STATUS_CHIP } from "./types";

export type TractClickKind = "eligible" | "designated";

export type TractClickDetails = {
  geoid: string;
  county: string | null;
  state: string | null;
  placeLabel: string;
  status: string;
  ruralLabel: string;
  kind: TractClickKind;
  /** Rural-eligible catalog tracts open the tract drawer. Other clicks use the popup. */
  opensRuralDrawer: boolean;
};

/** IRS appendix rows say "Orange County"; the rural pack stores "Orange". */
export function normalizeCountyName(county: string | null | undefined): string | null {
  if (!county) return null;
  const trimmed = county.trim();
  if (!trimmed) return null;
  return trimmed.replace(/ County$/i, "");
}

export function formatTractCounty(county: string | null | undefined, state: string | null | undefined): string {
  const name = normalizeCountyName(county);
  const stateName = state?.trim() || null;
  if (!name && !stateName) return "County unavailable";
  const countyLabel = name ? `${name} County` : "County unavailable";
  return stateName ? `${countyLabel}, ${stateName}` : countyLabel;
}

function readString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function readBool(value: unknown): boolean | null {
  if (value === true || value === "true") return true;
  if (value === false || value === "false") return false;
  return null;
}

export function tractClickFromFeature(input: {
  layerId: string;
  properties: Record<string, unknown> | null | undefined;
}): TractClickDetails | null {
  const properties = input.properties ?? {};
  const geoid = readString(properties.tractGeoid);
  if (!geoid) return null;
  const kind: TractClickKind = input.layerId === "oz-fill" || input.layerId === "oz-line" ? "designated" : "eligible";
  const county = normalizeCountyName(readString(properties.county));
  const state = readString(properties.state);
  const rural = readBool(properties.rural);
  const opensRuralDrawer = kind === "eligible" && rural === true;
  return {
    geoid,
    county,
    state,
    placeLabel: formatTractCounty(county, state),
    status: statusFor(kind, rural),
    ruralLabel: ruralLabelFor(kind, rural),
    kind,
    opensRuralDrawer,
  };
}

function statusFor(kind: TractClickKind, rural: boolean | null): string {
  if (kind === "designated") return "Current designated QOZ — not a 2027 designation";
  if (rural === true) return RURAL_ELIGIBLE_STATUS_CHIP;
  if (rural === false) return "Eligible for nomination, not rural — not designated";
  return "Eligible for nomination — not designated";
}

/** Eligible "Rural: yes/no" repeats the status sentence, so the tract popup omits it. */
export function tractPopupRuralLine(ruralLabel: string): string | null {
  if (ruralLabel.startsWith("Rural:")) return null;
  return ruralLabel;
}

function ruralLabelFor(kind: TractClickKind, rural: boolean | null): string {
  if (kind === "designated") {
    if (rural === true) return "Notice 2025-50 rural: yes";
    if (rural === false) return "Notice 2025-50 rural: no";
    return "Notice 2025-50 rural: unknown";
  }
  if (rural === true) return "Rural: yes";
  if (rural === false) return "Rural: no";
  return "Rural: not labeled";
}

type CountyRow = { tractGeoid?: string; geoid?: string; county?: string | null; state?: string | null };

export function annotateTractCounty<T extends { properties: { tractGeoid: string; county?: string | null; state?: string | null } }>(
  features: T[],
  rows: CountyRow[],
): T[] {
  const byGeoid = new Map<string, CountyRow>();
  for (const row of rows) {
    const geoid = row.tractGeoid || row.geoid;
    if (geoid) byGeoid.set(geoid, row);
  }
  for (const feature of features) {
    const row = byGeoid.get(feature.properties.tractGeoid);
    const county = normalizeCountyName(row?.county);
    const state = row?.state?.trim() || null;
    if (county && !feature.properties.county) feature.properties.county = county;
    if (state && !feature.properties.state) feature.properties.state = state;
  }
  return features;
}

/** Orange County designated QOZ overlay is the HUD extract for FIPS 12095. */
export function annotateOrangeDesignatedCounty<
  T extends { properties: { tractGeoid: string; county?: string | null; state?: string | null } },
>(features: T[]): T[] {
  for (const feature of features) {
    if (!feature.properties.tractGeoid.startsWith("12095")) continue;
    if (!feature.properties.county) feature.properties.county = "Orange";
    if (!feature.properties.state) feature.properties.state = "Florida";
  }
  return features;
}
