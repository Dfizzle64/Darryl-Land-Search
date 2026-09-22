import { fluAllowsMultifamily } from "./flu";
import { isRezoningCandidate, parcelAadt, parcelAcreage, parcelIncome, zoningPasses } from "./filters";
import { parcelInOpportunityZone } from "./opportunityZone";
import type { FilterState, FluConfig, ParcelFeature, ZoningConfig } from "./types";
import { findZoningHit } from "./zoning";

/**
 * Ranked-list scoring for parcels that already passed filters.
 *
 * Total is 0–100. Weights sum to 1 and are renormalized when a factor is
 * inactive (Opportunity Zone weight is dropped for “Not in OZ”, because every
 * remaining row is outside a zone and the bonus would be a constant zero).
 *
 * Formula (see README for the product write-up):
 *   score = 100 * Σ (weight_i * component_i)
 *   acreage / income / AADT use a rising ramp from the active minimum toward
 *   a comfort margin (larger / higher-income / busier sites rank up).
 *   Land-use scores zoning + FLU fit, with a bonus for rezoning candidates.
 *   OZ is a 0/1 bonus for a current designated QOZ when the filter is Either,
 *   In OZ, or an OZ 2.0 eligibility filter. OZ 2.0 nomination status is a
 *   filter, not a score component. The weight is dropped only for “Not in OZ”.
 */
export const SCORE_WEIGHTS = {
  acreage: 0.28,
  income: 0.22,
  aadt: 0.18,
  landUse: 0.22,
  opportunityZone: 0.1,
} as const;

export const SCORE_REFERENCES = {
  acreageComfortAcres: 8,
  incomeComfortUsd: 40_000,
  incomeFloorWhenNoMin: 80_000,
  aadtComfort: 25_000,
  aadtFloorWhenNoMin: 15_000,
  unknownScore: 0.35,
} as const;

export type ScoreComponentKey = keyof typeof SCORE_WEIGHTS;

export type ScoreBreakdown = Record<ScoreComponentKey, number>;

export type ScoreChip = {
  key: ScoreComponentKey;
  label: string;
  points: number;
};

export type RankedSite = {
  feature: ParcelFeature;
  rank: number;
  score: number;
  breakdown: ScoreBreakdown;
  contributions: ScoreBreakdown;
  chips: ScoreChip[];
  rezoningCandidate: boolean;
};

export function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

export function risingScore(
  value: number | null,
  minimum: number,
  comfortDelta: number,
  unknownScore = SCORE_REFERENCES.unknownScore,
): number {
  if (value == null || !Number.isFinite(value)) return unknownScore;
  const floor = Math.max(0, minimum);
  const span = Math.max(comfortDelta, floor * 0.5, 0.25);
  return clamp01((value - floor) / span);
}

function zoningFitScore(
  feature: ParcelFeature,
  filters: FilterState,
  zoningConfig: ZoningConfig,
): number {
  const hit = findZoningHit(feature.properties.zoningCode, feature.properties.zoningDistrict, zoningConfig);
  if (!hit) return 0.12;
  if (hit.status === "permitted" && hit.kind === "district") return 1;
  if (hit.kind === "planned-development" || hit.status === "maybe") {
    return filters.includePlannedDevelopment ? 0.64 : 0.28;
  }
  if (hit.status === "conditional") {
    return filters.includeConditionalZoning ? 0.55 : 0.22;
  }
  return 0.12;
}

export function landUseFitScore(
  feature: ParcelFeature,
  filters: FilterState,
  zoningConfig: ZoningConfig,
  fluConfig: FluConfig,
): number {
  const zoning = zoningPasses(feature, filters, zoningConfig);
  const flu = fluAllowsMultifamily(feature.properties.flu, fluConfig, true);
  const rezoning = flu === true && !zoning;

  if (filters.landUseFilter === "rezoning") return 1;
  if (filters.landUseFilter === "non-mf") {
    if (rezoning) return 1;
    if (flu === true) return 0.88;
    if (flu == null) return 0.42;
    return 0.3;
  }

  const z = zoningFitScore(feature, filters, zoningConfig);
  const f = flu === true ? 1 : flu === false ? 0.18 : 0.4;
  const blend = 0.55 * z + 0.45 * f;
  if (rezoning) return Math.max(blend, 0.84);
  if (zoning && flu === true) return Math.max(blend, 0.96);
  return blend;
}

export function effectiveScoreWeights(filters: FilterState): ScoreBreakdown {
  const weights: ScoreBreakdown = { ...SCORE_WEIGHTS };
  if (filters.ozFilter === "out") {
    weights.opportunityZone = 0;
  }
  const total = Object.values(weights).reduce((sum, value) => sum + value, 0);
  if (total <= 0) return weights;
  (Object.keys(weights) as ScoreComponentKey[]).forEach((key) => {
    weights[key] = weights[key] / total;
  });
  return weights;
}

export function scoreParcel(
  feature: ParcelFeature,
  filters: FilterState,
  zoningConfig: ZoningConfig,
  fluConfig: FluConfig,
): Omit<RankedSite, "feature" | "rank"> {
  const weights = effectiveScoreWeights(filters);
  const acreage = risingScore(
    parcelAcreage(feature),
    filters.minAcreage,
    SCORE_REFERENCES.acreageComfortAcres,
  );
  const incomeFloor = filters.minIncome > 0 ? filters.minIncome : SCORE_REFERENCES.incomeFloorWhenNoMin;
  const income = risingScore(
    parcelIncome(feature, filters.incomeGeography),
    filters.minIncome,
    filters.minIncome > 0 ? SCORE_REFERENCES.incomeComfortUsd : incomeFloor,
  );
  const aadt = risingScore(
    parcelAadt(feature),
    filters.minAadt,
    filters.minAadt > 0 ? SCORE_REFERENCES.aadtComfort : SCORE_REFERENCES.aadtFloorWhenNoMin,
  );
  const landUse = landUseFitScore(feature, filters, zoningConfig, fluConfig);
  const inOz = parcelInOpportunityZone(feature);
  const opportunityZone = inOz === true ? 1 : inOz === false ? 0 : 0.25;

  const breakdown: ScoreBreakdown = { acreage, income, aadt, landUse, opportunityZone };
  const contributions: ScoreBreakdown = {
    acreage: weights.acreage * acreage * 100,
    income: weights.income * income * 100,
    aadt: weights.aadt * aadt * 100,
    landUse: weights.landUse * landUse * 100,
    opportunityZone: weights.opportunityZone * opportunityZone * 100,
  };
  const score =
    contributions.acreage +
    contributions.income +
    contributions.aadt +
    contributions.landUse +
    contributions.opportunityZone;

  const chipMeta: { key: ScoreComponentKey; label: string }[] = [
    { key: "acreage", label: "Acres" },
    { key: "income", label: "Income" },
    { key: "aadt", label: "AADT" },
    { key: "landUse", label: "Zoning/FLU" },
    { key: "opportunityZone", label: "OZ" },
  ];

  return {
    score: Math.round(score * 10) / 10,
    breakdown,
    contributions,
    chips: chipMeta
      .filter((chip) => weights[chip.key] > 0)
      .map((chip) => ({
        key: chip.key,
        label: chip.label,
        points: Math.round(contributions[chip.key] * 10) / 10,
      })),
    rezoningCandidate: isRezoningCandidate(feature, filters, zoningConfig, fluConfig),
  };
}

export function rankSites(
  features: ParcelFeature[],
  filters: FilterState,
  zoningConfig: ZoningConfig,
  fluConfig: FluConfig,
): RankedSite[] {
  const ranked = features
    .map((feature) => ({ feature, ...scoreParcel(feature, filters, zoningConfig, fluConfig) }))
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      const acresA = parcelAcreage(a.feature) ?? -1;
      const acresB = parcelAcreage(b.feature) ?? -1;
      if (acresB !== acresA) return acresB - acresA;
      return a.feature.properties.id.localeCompare(b.feature.properties.id);
    });
  return ranked.map((item, index) => ({ ...item, rank: index + 1 }));
}
