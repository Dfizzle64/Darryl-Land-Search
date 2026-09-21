"use client";

import { useEffect, useRef } from "react";
import { formatAcres, formatUsd } from "@/lib/format";
import type { RankedSite } from "@/lib/score";
import { parcelAadt, parcelIncome } from "@/lib/filters";
import type { FilterState } from "@/lib/types";

type SitesPanelProps = {
  sites: RankedSite[];
  selectedId: string | null;
  hoveredId: string | null;
  incomeGeography: FilterState["incomeGeography"];
  landUseFilter: FilterState["landUseFilter"];
  fluUnknownCount: number;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  onClose?: () => void;
  variant?: "overlay" | "sheet";
};

export function SitesPanel({
  sites,
  selectedId,
  hoveredId,
  incomeGeography,
  landUseFilter,
  fluUnknownCount,
  onSelect,
  onHover,
  onClose,
  variant = "overlay",
}: SitesPanelProps) {
  const listRef = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    if (!selectedId || !listRef.current) return;
    const row = listRef.current.querySelector(`[data-site-id="${selectedId}"]`);
    row?.scrollIntoView({ block: "nearest" });
  }, [selectedId]);

  const shell =
    variant === "sheet"
      ? "flex h-full min-h-0 flex-col bg-ink-900"
      : "flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-white/10 bg-ink-900/95 shadow-2xl backdrop-blur-sm";

  return (
    <section className={shell} aria-label="Ranked matching sites">
      <header className="flex items-start justify-between gap-3 border-b border-white/10 px-3 py-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.16em] text-ink-500">Ranked sites</p>
          <p className="font-display text-2xl text-white">
            {sites.length.toLocaleString()} {sites.length === 1 ? "site" : "sites"}
          </p>
          <p className="mt-0.5 text-[11px] leading-relaxed text-ink-500">
            Score 0–100 from acreage, income, AADT, zoning/FLU fit
            {landUseFilter === "off" ? "" : ", and an OZ bonus when relevant"}.
          </p>
        </div>
        {onClose ? (
          <button type="button" className="rounded-full border border-white/15 px-3 py-1 text-sm" onClick={onClose}>
            Close
          </button>
        ) : null}
      </header>

      {landUseFilter === "rezoning" && fluUnknownCount > 0 ? (
        <p className="border-b border-clay-400/30 bg-clay-500/10 px-3 py-2 text-[11px] leading-relaxed text-clay-400">
          Rezoning candidates need joined FLU. {fluUnknownCount.toLocaleString()} sample parcels have no municipal FLU
          (often Winter Park, Ocoee, Winter Garden, Apopka) and cannot be classified.
        </p>
      ) : null}

      {sites.length === 0 ? (
        <p className="px-3 py-4 text-sm text-ink-300">No sites match the current filters.</p>
      ) : (
        <ul ref={listRef} className="sites-scroll min-h-0 flex-1 overflow-y-auto px-2 py-2">
          {sites.map((site) => {
            const props = site.feature.properties;
            const selected = props.id === selectedId;
            const hovered = props.id === hoveredId;
            const income = parcelIncome(site.feature, incomeGeography);
            const aadt = parcelAadt(site.feature);
            const oz = props.opportunityZone?.inOpportunityZone;
            return (
              <li key={props.id}>
                <button
                  type="button"
                  data-site-id={props.id}
                  className={`mb-1.5 w-full rounded-xl border px-2.5 py-2 text-left transition ${
                    selected
                      ? "border-clay-400/50 bg-clay-500/10"
                      : hovered
                        ? "border-moss-400/30 bg-white/5"
                        : "border-white/5 bg-ink-950/40 hover:border-white/15"
                  }`}
                  onClick={() => onSelect(props.id)}
                  onMouseEnter={() => onHover(props.id)}
                  onMouseLeave={() => onHover(null)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">
                      #{site.rank}
                      <span className="ml-2 font-display text-lg tracking-normal text-white">{site.score.toFixed(1)}</span>
                    </p>
                    {oz ? (
                      <span className="rounded-full border border-clay-400/40 px-1.5 py-px text-[10px] text-clay-400">
                        OZ
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-0.5 truncate text-sm text-white">{props.situsAddress || props.parcelId}</p>
                  <p className="truncate text-[11px] text-ink-500">
                    {[props.situsCity, formatAcres(props.acreage), props.zoningCode].filter(Boolean).join(" · ")}
                  </p>
                  <p className="mt-1 truncate text-[11px] text-ink-300">
                    {props.flu?.code ? `FLU ${props.flu.label || props.flu.code}` : "FLU not joined"}
                    {income != null ? ` · ${formatUsd(income)}` : ""}
                    {aadt != null ? ` · ${aadt.toLocaleString()} AADT` : ""}
                  </p>
                  {site.rezoningCandidate ? (
                    <p className="mt-1 text-[11px] text-clay-400">
                      Rezoning candidate: FLU {props.flu?.code ?? "?"} / Zoning {props.zoningCode ?? "?"}
                    </p>
                  ) : null}
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {site.chips.map((chip) => (
                      <span
                        key={chip.key}
                        className="rounded-full border border-white/10 bg-ink-800/80 px-1.5 py-px text-[10px] text-ink-300"
                      >
                        {chip.label} {chip.points.toFixed(0)}
                      </span>
                    ))}
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
