"use client";

import { useEffect, useRef } from "react";
import { formatCountyLabel, isSouthCarolinaState } from "@/lib/markets";
import { RURAL_ELIGIBLE_STATUS_CHIP, SC_GOVERNOR_FILED_STATUS, type RuralMarketTractRow } from "@/lib/types";

type TractPanelProps = {
  tracts: RuralMarketTractRow[];
  selectedGeoid: string | null;
  onSelect: (geoid: string) => void;
  onClose?: () => void;
  variant?: "overlay" | "sheet";
};

export function TractPanel({ tracts, selectedGeoid, onSelect, onClose, variant = "overlay" }: TractPanelProps) {
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
    <section className={shell} aria-label="Rural-eligible tracts">
      <header className="flex items-start justify-between gap-3 border-b border-white/10 px-3 py-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.16em] text-ink-500">Rural-eligible tracts</p>
          <p className="font-display text-2xl text-white">
            {tracts.length.toLocaleString()} {tracts.length === 1 ? "tract" : "tracts"}
          </p>
          <p className="mt-0.5 text-[11px] leading-relaxed text-ink-500">
            Rev. Proc. 2026-14 entirely rural tracts. Nomination eligibility only.
            {tracts.some((tract) => isSouthCarolinaState(tract.state))
              ? ` South Carolina tracts: ${SC_GOVERNOR_FILED_STATUS}.`
              : ""}
          </p>
        </div>
        {onClose ? (
          <button type="button" className="rounded-full border border-white/15 px-3 py-1 text-sm" onClick={onClose}>
            Close
          </button>
        ) : null}
      </header>
      {tracts.length === 0 ? (
        <p className="px-3 py-4 text-sm text-ink-300">No rural-eligible tracts in this county filter.</p>
      ) : (
        <ul ref={listRef} className="sites-scroll min-h-0 flex-1 overflow-y-auto px-2 py-2">
          {tracts.map((tract) => {
            const selected = tract.geoid === selectedGeoid;
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
                  <span className="inline-block rounded-full border border-[#f15a08]/70 bg-[#f15a08]/15 px-1.5 py-px text-[10px] text-[#ffc7a3]">
                    {RURAL_ELIGIBLE_STATUS_CHIP}
                  </span>
                  {isSouthCarolinaState(tract.state) ? (
                    <p className="mt-1 text-[11px] leading-snug text-ink-300">{SC_GOVERNOR_FILED_STATUS}</p>
                  ) : null}
                  <p className="mt-1 text-sm text-white">{tract.placeOrCorridor}</p>
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
