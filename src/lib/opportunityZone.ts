import type { OpportunityZoneInfo, ParcelFeature } from "./types";

export function parcelOpportunityZone(feature: ParcelFeature): OpportunityZoneInfo | null {
  return feature.properties.opportunityZone ?? null;
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
    return {
      inZone: true,
      label: "In Opportunity Zone",
      detail: `Yes — parcel centroid falls in ${tract}${info.tractGeoid ? ` (${info.tractGeoid})` : ""}. QOZs are 2010 Census tracts certified by Treasury, not ACS 2020 geography.`,
    };
  }
  return {
    inZone: false,
    label: "Not in Opportunity Zone",
    detail: "No — the parcel centroid is outside Orange County’s HUD/Treasury Qualified Opportunity Zone tracts.",
  };
}
