import type { ZoningConfig, ZoningToken } from "./types";

export type ParsedZoning = {
  jurisdictionPrefix: string | null;
  zoningDistrict: string | null;
};

export function parseZoningCode(code: string | null | undefined): ParsedZoning {
  if (!code?.trim()) {
    return { jurisdictionPrefix: null, zoningDistrict: null };
  }
  const raw = code.trim().toUpperCase();
  const [head, ...rest] = raw.split("-");
  let jurisdictionPrefix: string | null = null;
  let remainder = raw;
  if (head && /^[A-Z]{2,3}$/.test(head) && rest.length > 0) {
    jurisdictionPrefix = head;
    remainder = rest.join("-");
  }
  const zoningDistrict = remainder.split("/")[0]?.trim() || null;
  return { jurisdictionPrefix, zoningDistrict };
}

function tokenMatchesDistrict(token: string, district: string): boolean {
  const t = token.toUpperCase();
  const d = district.toUpperCase();
  if (d === t) return true;
  if (d.startsWith(t)) {
    const next = d.charAt(t.length);
    return next === "" || !/[0-9]/.test(next);
  }
  return false;
}

export function matchesTokens(district: string | null | undefined, tokens: ZoningToken[]): boolean {
  if (!district) return false;
  return tokens.some((item) => tokenMatchesDistrict(item.token, district));
}

export function zoningAllowsMultifamily(
  zoningCode: string | null | undefined,
  zoningDistrict: string | null | undefined,
  config: ZoningConfig,
  includePlannedDevelopment: boolean,
): boolean {
  const parsed = parseZoningCode(zoningCode);
  const district = (zoningDistrict || parsed.zoningDistrict || "").trim();
  if (!district) return false;
  if (matchesTokens(district, config.multifamilyTokens)) return true;
  if (includePlannedDevelopment && matchesTokens(district, config.plannedDevelopmentTokens)) {
    return true;
  }
  return false;
}

export function describeZoningMatch(
  zoningCode: string | null | undefined,
  zoningDistrict: string | null | undefined,
  config: ZoningConfig,
  includePlannedDevelopment: boolean,
): { allowed: boolean; reason: string } {
  const parsed = parseZoningCode(zoningCode);
  const district = zoningDistrict || parsed.zoningDistrict;
  if (!district) {
    return { allowed: false, reason: "Zoning code not available on this parcel." };
  }
  const mf = config.multifamilyTokens.find((token) => tokenMatchesDistrict(token.token, district));
  if (mf) {
    return { allowed: true, reason: `Treated as multifamily-capable: ${mf.label}. ${mf.why}` };
  }
  const pd = config.plannedDevelopmentTokens.find((token) => tokenMatchesDistrict(token.token, district));
  if (pd) {
    if (includePlannedDevelopment) {
      return {
        allowed: true,
        reason: `Treated as possible multifamily via ${pd.label}. ${pd.why}`,
      };
    }
    return {
      allowed: false,
      reason: `${pd.label} is excluded while “include planned development” is off. ${pd.why}`,
    };
  }
  return {
    allowed: false,
    reason: `District ${district} is not in the configurable multifamily list.`,
  };
}
