"use client";

import { useEffect, useRef } from "react";
import { MfPriorityFilter } from "./MfPriorityFilter";
import { displayStatusChip, formatCountyLabel, showsGovernorFiledSoftCopy } from "@/lib/markets";
import { tractPlaceLabel } from "@/lib/scMfPriority";
import { SC_GOVERNOR_FILED_STATUS, type EligibleTractRow, type MfPriorityView } from "@/lib/types";

type TractPanelProps = {
  tracts: EligibleTractRow[];
  selectedGeoid: string | null;
  onSelect: (geoid: string) => void;
  onClose?: () => void;
  onCollapse?: () => void;
  variant?: "overlay" | "sheet";
  priorityView?: MfPriorityView;
  priorityCounts?: { all: number; priority: number; A: number; B: number };
  onPriorityView?: (view: MfPriorityView) => void;
  emptyMessage?: string;
};

export function TractPanel({
  tracts,
  selectedGeoid,
  onSelect,
  onClose,
  onCollapse,
  variant = "overlay",
  priorityView,
  priorityCounts,
  onPriorityView,
  emptyMessage = "No eligible tracts in this county filter.",
}: TractPanelProps) {
  const listRef = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    if (!selectedGeoid || !listRef.current) return;
    const row = listRef.current.querySelector(`[data-tract-geoid="${selectedGeoid}"]`);
    row?.scrollIntoView({ block: "nearest" });
  }, [selectedGeoid]);

  const shell =
    variant === "sheet"
      ? "flex h-full min-h-0 flex-col bg-ink-900"
      : "flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-white/10 bg-ink-900/95 shadow-2xl backdrop-blur-sm";

  return (
    <section className={shell} aria-label="Eligible tracts">
      <header className="flex items-start justify-between gap-3 border-b border-white/10 px-3 py-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.16em] text-ink-500">Eligible tracts</p>
          <p className="font-display text-2xl text-white">
            {tracts.length.toLocaleString()} {tracts.length === 1 ? "tract" : "tracts"}
          </p>
          <p className="mt-0.5 text-[11px] leading-relaxed text-ink-500">
            Rev. Proc. 2026-14 nomination eligibility only. Brown is rural. Blue is urban. Status stays eligible —
            not designated.
            {tracts.some((tract) => showsGovernorFiledSoftCopy(tract)) || priorityView
              ? ` South Carolina tracts: ${SC_GOVERNOR_FILED_STATUS}.`
              : ""}
          </p>
          {onPriorityView && priorityView && priorityCounts ? (
            <div className="mt-2">
              <MfPriorityFilter compact value={priorityView} counts={priorityCounts} onChange={onPriorityView} />
            </div>
          ) : null}
        </div>
        <div className="flex shrink-0 gap-1">
          {onCollapse ? (
            <button type="button" className="rounded-full border border-white/15 px-3 py-1 text-sm" onClick={onCollapse}>
              Collapse
            </button>
          ) : null}
          {onClose ? (
            <button type="button" className="rounded-full border border-white/15 px-3 py-1 text-sm" onClick={onClose}>
              Close
            </button>
          ) : null}
        </div>
      </header>
      {tracts.length === 0 ? (
        <p className="px-3 py-4 text-sm text-ink-300">{emptyMessage}</p>
      ) : (
        <ul ref={listRef} className="sites-scroll min-h-0 flex-1 overflow-y-auto px-2 py-2">
          {tracts.map((tract) => {
            const selected = tract.geoid === selectedGeoid;
            const rural = tract.rural === "Y";
            return (
              <li key={`${tract.market}-${tract.geoid}`}>
                <button
                  type="button"
                  data-tract-geoid={tract.geoid}
                  className={`mb-1.5 w-full rounded-xl border px-2.5 py-2 text-left transition ${
                    selected ? "border-clay-400/50 bg-clay-500/10" : "border-white/5 bg-ink-950/40 hover:border-white/15"
                  }`}
                  onClick={() => onSelect(tract.geoid)}
                >
                  <span
                    className={`inline-block rounded-full border px-1.5 py-px text-[10px] ${
                      rural
                        ? "border-[#a56b3c]/70 bg-[#a56b3c]/15 text-[#f6e6d4]"
                        : "border-[#3d7dff]/70 bg-[#3d7dff]/15 text-[#d6e4ff]"
                    }`}
                  >
                    {rural ? "Rural" : "Urban"} · {displayStatusChip(tract)}
                  </span>
                  {showsGovernorFiledSoftCopy(tract) ? (
                    <p className="mt-1 text-[11px] leading-snug text-ink-300">{SC_GOVERNOR_FILED_STATUS}</p>
                  ) : null}
                  {tract.mfPriority ? (
                    <span
                      className={`mt-1 inline-block rounded-full border px-1.5 py-px text-[10px] ${
                        tract.mfPriority.tier === "A"
                          ? "border-[#ffe08a]/80 text-[#ffe08a]"
                          : "border-[#7ec8ff]/80 text-[#d7eeff]"
                      }`}
                    >
                      Tier {tract.mfPriority.tier} · SC MF priority
                    </span>
                  ) : null}
                  <p className="mt-1 text-sm text-white">{tractPlaceLabel(tract)}</p>
                  {tract.mfPriority ? (
                    <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-ink-300">{tract.mfPriority.mfRationale}</p>
                  ) : null}
                  <p className="truncate text-[11px] text-ink-500">
                    {formatCountyLabel(tract.county, tract.state)} · {tract.geoid}
                  </p>
                  {tract.outerEdge ? (
                    <p className="mt-1 text-[11px] text-clay-400">Outer edge of the approximate 90-minute shed</p>
                  ) : null}
                  {tract.specialUse ? (
                    <p className="mt-1 text-[11px] text-clay-400">Special-use tract pattern — verify before pursuit</p>
                  ) : null}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
