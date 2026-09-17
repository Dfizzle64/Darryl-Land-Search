import type { DistrictStatus, ZoningConfig, ZoningJurisdiction, ZoningToken } from "./types";

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
  if (d.endsWith(` ${t}`) || d.endsWith(`-${t}`)) return true;
  return false;
}

export function tokenMatches(token: ZoningToken, district: string): boolean {
  if (tokenMatchesDistrict(token.token, district)) return true;
  return (token.aliases ?? []).some((alias) => tokenMatchesDistrict(alias, district));
}

export function matchesTokens(district: string | null | undefined, tokens: ZoningToken[]): boolean {
  if (!district) return false;
  return tokens.some((item) => tokenMatches(item, district));
}

export function flattenMultifamilyTokens(config: ZoningConfig): ZoningToken[] {
  if (config.multifamilyTokens.length > 0) return config.multifamilyTokens;
  const tokens: ZoningToken[] = [];
  for (const jurisdiction of config.jurisdictions ?? []) {
    for (const district of jurisdiction.districts) {
      if (district.status === "permitted" || district.status === "conditional") {
        tokens.push({
          ...district,
          jurisdictions: district.jurisdictions ?? [jurisdiction.code],
        });
      }
    }
  }
  return tokens;
}

export function jurisdictionForPrefix(
  config: ZoningConfig,
  prefix: string | null | undefined,
): ZoningJurisdiction | null {
  if (!prefix) return null;
  return config.jurisdictions.find((item) => item.code === prefix.toUpperCase()) ?? null;
}

type DistrictHit = {
  token: ZoningToken;
  status: DistrictStatus;
  jurisdiction: ZoningJurisdiction | null;
  kind: "district" | "planned-development";
};

function findInList(district: string, tokens: ZoningToken[]): ZoningToken | null {
  return tokens.find((token) => tokenMatches(token, district)) ?? null;
}

export function findZoningHit(
  zoningCode: string | null | undefined,
  zoningDistrict: string | null | undefined,
  config: ZoningConfig,
): DistrictHit | null {
  const parsed = parseZoningCode(zoningCode);
  const district = (zoningDistrict || parsed.zoningDistrict || "").trim();
  if (!district) return null;

  const prefix = parsed.jurisdictionPrefix;
  const jurisdiction = jurisdictionForPrefix(config, prefix);

  if (jurisdiction) {
    const local = findInList(district, jurisdiction.districts);
    if (local) {
      return {
        token: local,
        status: local.status ?? "permitted",
        jurisdiction,
        kind: "district",
      };
    }
  } else if ((config.jurisdictions ?? []).length === 0) {
    const flat = findInList(district, flattenMultifamilyTokens(config));
    if (flat) {
      return { token: flat, status: flat.status ?? "permitted", jurisdiction: null, kind: "district" };
    }
  }

  const pd = findInList(district, config.plannedDevelopmentTokens);
  if (pd) {
    return { token: pd, status: pd.status ?? "maybe", jurisdiction, kind: "planned-development" };
  }
  return null;
}

export function zoningAllowsMultifamily(
  zoningCode: string | null | undefined,
  zoningDistrict: string | null | undefined,
  config: ZoningConfig,
  includePlannedDevelopment: boolean,
  includeConditionalZoning = false,
): boolean {
  const hit = findZoningHit(zoningCode, zoningDistrict, config);
  if (!hit) return false;
  if (hit.kind === "planned-development" || hit.status === "maybe") {
    return includePlannedDevelopment;
  }
  if (hit.status === "conditional") return includeConditionalZoning;
  if (hit.status === "permitted") return true;
  return false;
}

export function describeZoningMatch(
  zoningCode: string | null | undefined,
  zoningDistrict: string | null | undefined,
  config: ZoningConfig,
  includePlannedDevelopment: boolean,
  includeConditionalZoning = false,
): { allowed: boolean; reason: string; status: DistrictStatus | "none" } {
  const parsed = parseZoningCode(zoningCode);
  const district = zoningDistrict || parsed.zoningDistrict;
  if (!district) {
    return { allowed: false, reason: "Zoning code not available on this parcel.", status: "none" };
  }
  const hit = findZoningHit(zoningCode, zoningDistrict, config);
  if (!hit) {
    const juris = jurisdictionForPrefix(config, parsed.jurisdictionPrefix);
    const coverage = juris
      ? ` ${juris.name} coverage is ${juris.coverage}${juris.coverageNote ? ` — ${juris.coverageNote}` : "."}`
      : "";
    return {
      allowed: false,
      reason: `District ${district} is not in the configurable multifamily list.${coverage}`,
      status: "none",
    };
  }

  if (hit.kind === "planned-development" || hit.status === "maybe") {
    if (includePlannedDevelopment) {
      return {
        allowed: true,
        status: "maybe",
        reason: `Maybe — site-specific (${hit.token.label}). ${hit.token.why}`,
      };
    }
    return {
      allowed: false,
      status: "maybe",
      reason: `${hit.token.label} is excluded while “include planned development” is off. ${hit.token.why}`,
    };
  }

  if (hit.status === "conditional") {
    if (includeConditionalZoning) {
      return {
        allowed: true,
        status: "conditional",
        reason: `Conditional / not by-right: ${hit.token.label}. ${hit.token.why}`,
      };
    }
    return {
      allowed: false,
      status: "conditional",
      reason: `${hit.token.label} is conditional (Live Local, mixed-use, or limited multiplex). Turn on “include conditional zoning” to keep these sites. ${hit.token.why}`,
    };
  }

  return {
    allowed: true,
    status: hit.status,
    reason: `Treated as multifamily-capable: ${hit.token.label}. ${hit.token.why}`,
  };
}
