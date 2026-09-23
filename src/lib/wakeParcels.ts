/** Wake County planning-jurisdiction codes from the county parcel layer. */
export const WAKE_JURISDICTION_LABELS: Record<string, string> = {
  RA: "Raleigh",
  CA: "Cary",
  AP: "Apex",
  HS: "Holly Springs",
  FV: "Fuquay-Varina",
  GA: "Garner",
  KN: "Knightdale",
  MO: "Morrisville",
  RO: "Rolesville",
  WF: "Wake Forest",
  WE: "Wendell",
  ZB: "Zebulon",
  AN: "Angier",
  WC: "Wake County",
  DU: "Durham",
  CL: "Clayton",
  RD: "RDU Airport",
  RP: "Research Triangle Park",
};

export function wakeJurisdictionLabel(code: string | null | undefined): string | null {
  if (!code) return null;
  return WAKE_JURISDICTION_LABELS[code.trim().toUpperCase()] ?? null;
}

/** Drawer zoning line: jurisdiction name plus the GIS designation. Not a multifamily call. */
export function wakeZoningLabel(
  zoningCode: string | null | undefined,
  jurisdictionCode: string | null | undefined,
): string | null {
  const code = zoningCode?.trim() || null;
  const jurisdiction = wakeJurisdictionLabel(jurisdictionCode);
  if (jurisdiction && code) return `${jurisdiction} · ${code}`;
  return code;
}
