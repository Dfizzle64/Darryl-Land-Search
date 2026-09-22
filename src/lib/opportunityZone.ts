import { RURAL_ELIGIBLE_STATUS_CHIP, type OpportunityZoneInfo, type Oz2EligibilityInfo, type ParcelFeature } from "./types";

export function parcelOpportunityZone(feature: ParcelFeature): OpportunityZoneInfo | null {
  return feature.properties.opportunityZone ?? null;
}

export function parcelOz2Eligibility(feature: ParcelFeature): Oz2EligibilityInfo | null {
  return feature.properties.oz2Eligibility ?? null;
}

/** true / false when joined; null when the join is missing. */
export function parcelInOpportunityZone(feature: ParcelFeature): boolean | null {
  const info = parcelOpportunityZone(feature);
  if (!info) return null;
  return info.inOpportunityZone;
}

export function describeOpportunityZone(info: OpportunityZoneInfo | null | undefined): {
  inZone: boolean | null;
  label: string;
  detail: string;
} {
  if (!info) {
    return {
      inZone: null,
      label: "Opportunity Zone unknown",
      detail:
        "This parcel has not been joined to HUD/Treasury Qualified Opportunity Zone polygons (2010 census tracts).",
    };
  }
  if (info.inOpportunityZone) {
    const tract = info.tractName || (info.tractGeoid ? `GEOID ${info.tractGeoid}` : "designated tract");
    const ruralNote =
      info.designatedRural === true
        ? " Notice 2025-50 lists this designated tract as comprised entirely of a rural area."
        : info.designatedRural === false
          ? " Notice 2025-50 does not list this designated tract as rural."
          : "";
    return {
      inZone: true,
      label: "In designated Opportunity Zone",
      detail: `Yes — parcel centroid falls in ${tract}${info.tractGeoid ? ` (${info.tractGeoid})` : ""}. This is a current designated QOZ (2010 Census tract certified by Treasury), not ACS 2020 geography and not a 2027 designation.${ruralNote}`,
    };
  }
  return {
    inZone: false,
    label: "Not in designated Opportunity Zone",
    detail: "No — the parcel centroid is outside Orange County’s current HUD/Treasury Qualified Opportunity Zone tracts.",
  };
}

export function describeOz2Eligibility(info: Oz2EligibilityInfo | null | undefined): {
  eligible: boolean | null;
  rural: boolean | null;
  label: string;
  statusChip: string | null;
  detail: string;
} {
  if (!info) {
    return {
      eligible: null,
      rural: null,
      label: "OZ 2.0 unknown",
      statusChip: null,
      detail:
        "This parcel has not been joined to the Rev. Proc. 2026-14 list of census tracts eligible for nomination as 2027 Qualified Opportunity Zones.",
    };
  }
  const geoid = info.tractGeoid || "unknown GEOID";
  const name = info.tractName ? ` (${info.tractName})` : "";
  if (info.eligible && info.rural === true) {
    return {
      eligible: true,
      rural: true,
      label: "OZ 2.0 rural-eligible",
      statusChip: RURAL_ELIGIBLE_STATUS_CHIP,
      detail: `Rural-eligible for nomination — GEOID ${geoid}${name}. Rev. Proc. 2026-14 lists this 2020 census tract as a low-income community comprised entirely of a rural area. It is eligible for nomination as a 2027 QOZ and has not been nominated or certified. Status: ${RURAL_ELIGIBLE_STATUS_CHIP}.`,
    };
  }
  if (info.eligible && info.rural === false) {
    return {
      eligible: true,
      rural: false,
      label: "OZ 2.0 eligible, not rural",
      statusChip: null,
      detail: `Eligible for nomination, not rural — GEOID ${geoid}${name}. Rev. Proc. 2026-14 marks this tract Non-rural. It has not been nominated or certified as a 2027 QOZ.`,
    };
  }
  if (info.eligible) {
    return {
      eligible: true,
      rural: null,
      label: "OZ 2.0 eligible",
      statusChip: null,
      detail: `Eligible for nomination — GEOID ${geoid}${name}. The Rev. Proc. 2026-14 appendix did not include a Rural Status for this tract, so it is not labeled rural. It has not been nominated or certified as a 2027 QOZ.`,
    };
  }
  return {
    eligible: false,
    rural: null,
    label: "Not OZ 2.0 eligible",
    statusChip: null,
    detail:
      "This parcel centroid is outside the Orange County census tracts Rev. Proc. 2026-14 lists as eligible for nomination. It is not a 2027 QOZ designation.",
  };
}
