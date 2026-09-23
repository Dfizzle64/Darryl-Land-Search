import type { FluCategory, FluConfig, FluInfo } from "./types";

function normalizeCode(code: string): string {
  return code.trim().toUpperCase();
}

function candidateCodes(code: string): string[] {
  const upper = normalizeCode(code);
  const codes = [upper];
  const base = upper.split("/")[0];
  if (base && base !== upper) codes.push(base);
  return codes;
}

export function findFluCategory(flu: FluInfo | null | undefined, config: FluConfig): FluCategory | null {
  if (!flu?.code) return null;
  const jurisdiction = flu.jurisdiction?.toUpperCase() ?? null;
  for (const code of candidateCodes(flu.code)) {
    const matches = config.categories.filter((category) => normalizeCode(category.code) === code);
    if (matches.length === 0) continue;
    if (jurisdiction) {
      const scoped = matches.find((category) => category.jurisdiction === jurisdiction);
      if (scoped) return scoped;
    }
    return matches[0] ?? null;
  }
  return null;
}

export function fluAllowsMultifamily(
  flu: FluInfo | null | undefined,
  config: FluConfig,
  includeMaybe = true,
): boolean | null {
  if (!flu?.code) return null;
  const category = findFluCategory(flu, config);
  if (!category) return null;
  if (category.status === "no" || !category.allowsMultifamily) return false;
  if (category.status === "maybe") return includeMaybe;
  return true;
}

export function describeFluMatch(
  flu: FluInfo | null | undefined,
  config: FluConfig,
): { allows: boolean | null; reason: string; category: FluCategory | null } {
  if (!flu?.code) {
    const place = flu?.jurisdictionName;
    return {
      allows: null,
      category: null,
      reason: place
        ? `No ${place} Future Land Use code is joined for this parcel. County FLU is not used in its place.`
        : "No Future Land Use designation is joined to this parcel.",
    };
  }
  const category = findFluCategory(flu, config);
  const label = flu.label || flu.code;
  if (!category) {
    return {
      allows: null,
      category: null,
      reason: `FLU ${label} (${flu.jurisdiction ?? "unknown source"}) is not in data/flu-config.json, so it is treated as unknown rather than invented.`,
    };
  }
  const density =
    category.maxDensityDuAc != null ? ` Published max about ${category.maxDensityDuAc} du/ac.` : "";
  if (category.status === "no" || !category.allowsMultifamily) {
    return {
      allows: false,
      category,
      reason: `FLU ${category.label} is not treated as multifamily-supportive.${density} ${category.why}`,
    };
  }
  if (category.status === "maybe") {
    return {
      allows: true,
      category,
      reason: `FLU ${category.label} may support multifamily, but density is plan-specific.${density} ${category.why}`,
    };
  }
  return {
    allows: true,
    category,
    reason: `FLU ${category.label} supports multifamily / higher density.${density} ${category.why}`,
  };
}
