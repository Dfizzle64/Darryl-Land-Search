"use client";

import type { CoverageLevel, DistrictStatus, FluConfig, ZoningConfig, ZoningJurisdiction } from "@/lib/types";

function coverageLabel(level: CoverageLevel): string {
  if (level === "verified") return "Use table reviewed";
  if (level === "partial") return "Partial — some districts verified";
  return "Use table not fully verified";
}

function statusLabel(status: DistrictStatus | undefined): string {
  if (status === "conditional") return "Conditional";
  if (status === "maybe") return "Maybe — site-specific";
  if (status === "not-mf") return "Not MF";
  return "Permitted";
}

function statusClass(status: DistrictStatus | undefined): string {
  if (status === "conditional") return "border-clay-400/40 text-clay-400";
  if (status === "maybe") return "border-white/20 text-ink-300";
  if (status === "not-mf") return "border-white/10 text-ink-500";
  return "border-moss-400/40 text-moss-400";
}

export function ZoningKnowledgePanel({
  zoningConfig,
  fluConfig,
  fluJoinedCount,
  parcelCount,
}: {
  zoningConfig: ZoningConfig;
  fluConfig: FluConfig;
  fluJoinedCount: number | null;
  parcelCount: number;
}) {
  const verified = zoningConfig.jurisdictions.filter((item) => item.coverage === "verified").length;
  const fluYes = fluConfig.categories.filter((item) => item.allowsMultifamily && item.status === "yes").length;

  return (
    <section className="mt-5 rounded-2xl border border-white/10 bg-ink-950/50 p-3">
      <p className="text-xs uppercase tracking-[0.16em] text-ink-500">Zoning knowledge</p>
      <p className="mt-1 text-sm text-white">Offline research notes, not a live model</p>
      <p className="mt-1 text-[11px] leading-relaxed text-ink-500">
        Updated {zoningConfig.updatedAt || "unknown"}. {verified} of {zoningConfig.jurisdictions.length}{" "}
        jurisdictions have a reviewed use table. FLU config {fluConfig.updatedAt}: {fluYes} categories treated as
        MF-supportive. Joined FLU on {fluJoinedCount ?? "—"} / {parcelCount} sample parcels.
      </p>

      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-ink-100">Jurisdictions and districts</summary>
        <ul className="mt-2 space-y-3">
          {zoningConfig.jurisdictions.map((jurisdiction) => (
            <JurisdictionBlock key={jurisdiction.code} jurisdiction={jurisdiction} />
          ))}
        </ul>
      </details>

      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-ink-100">Planned development — maybe, site-specific</summary>
        <ul className="mt-2 space-y-2 text-xs text-ink-300">
          {zoningConfig.plannedDevelopmentTokens.map((token) => (
            <li key={token.token}>
              <span className="text-clay-400">{token.token}</span> — {token.label}. {token.why}
            </li>
          ))}
        </ul>
      </details>

      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-ink-100">Official code sources</summary>
        <ul className="mt-2 space-y-1 text-xs">
          {(zoningConfig.sources ?? []).map((source) => (
            <li key={source.url}>
              <a className="text-moss-400 underline-offset-2 hover:underline" href={source.url} target="_blank" rel="noreferrer">
                {source.label}
              </a>
            </li>
          ))}
          {fluConfig.sources.map((source) => (
            <li key={source.url}>
              <a className="text-moss-400 underline-offset-2 hover:underline" href={source.url} target="_blank" rel="noreferrer">
                {source.label}
              </a>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}

function JurisdictionBlock({ jurisdiction }: { jurisdiction: ZoningJurisdiction }) {
  return (
    <li className="rounded-lg border border-white/5 bg-ink-900/60 p-2">
      <p className="text-xs text-white">
        <span className="text-clay-400">{jurisdiction.code}</span> {jurisdiction.name}
      </p>
      <p className="mt-0.5 text-[11px] text-ink-500">{coverageLabel(jurisdiction.coverage)}</p>
      {jurisdiction.coverageNote ? <p className="mt-1 text-[11px] leading-relaxed text-ink-500">{jurisdiction.coverageNote}</p> : null}
      {jurisdiction.codeSource ? (
        <a
          className="mt-1 inline-block text-[11px] text-moss-400 underline-offset-2 hover:underline"
          href={jurisdiction.codeSource.url}
          target="_blank"
          rel="noreferrer"
        >
          {jurisdiction.codeSource.label}
        </a>
      ) : null}
      {jurisdiction.districts.length === 0 ? (
        <p className="mt-1 text-[11px] text-ink-500">No MF districts documented — use table not verified; no loopholes invented.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {jurisdiction.districts.map((district) => (
            <li key={`${jurisdiction.code}-${district.token}`} className="text-[11px] leading-relaxed text-ink-300">
              <span className="text-ink-100">{district.token}</span> — {district.label}{" "}
              <span className={`ml-1 inline-block rounded-full border px-1.5 py-px ${statusClass(district.status)}`}>
                {statusLabel(district.status)}
              </span>
              <span className="mt-0.5 block text-ink-500">{district.why}</span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
