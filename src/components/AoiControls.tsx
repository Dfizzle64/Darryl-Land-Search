"use client";

import { bboxAreaAcres, type AoiLock } from "@/lib/aoi";
import { formatAcres } from "@/lib/format";

type AoiControlsProps = {
  drawing: boolean;
  aoi: AoiLock | null;
  matchedCount: number;
  truncated: boolean;
  loading: boolean;
  onDraw: () => void;
  onLockView: () => void;
  onClear: () => void;
  onCancelDraw: () => void;
};

export function AoiControls({
  drawing,
  aoi,
  matchedCount,
  truncated,
  loading,
  onDraw,
  onLockView,
  onClear,
  onCancelDraw,
}: AoiControlsProps) {
  const acres = aoi ? formatAcres(bboxAreaAcres(aoi.bbox)) : null;
  const countLabel = loading ? "loading…" : `${matchedCount.toLocaleString()} parcels`;

  return (
    <div
      data-aoi-controls
      className="pointer-events-auto absolute inset-x-3 top-14 z-30 flex flex-col items-end gap-2 sm:inset-x-auto sm:right-4 sm:top-4 sm:max-w-[22rem] xl:right-[22rem]"
    >
      <div className="flex max-w-full flex-wrap items-center justify-end gap-1.5">
        {aoi ? (
          <div
            className="flex max-w-full flex-wrap items-center gap-x-2 gap-y-1 rounded-full border border-clay-400/60 bg-ink-900/95 px-3 py-1.5 text-xs text-white shadow-2xl"
            aria-live="polite"
          >
            <span className="font-medium text-clay-400">AOI locked</span>
            <span>{acres}</span>
            <span className="text-ink-300">{countLabel}</span>
            {truncated ? <span className="text-clay-400">capped</span> : null}
            <button
              type="button"
              className="rounded-full border border-white/20 px-2 py-0.5 text-[11px] text-white hover:border-white/40"
              onClick={onClear}
            >
              Clear
            </button>
          </div>
        ) : null}
        <button
          type="button"
          aria-pressed={drawing}
          className={`rounded-full border px-3 py-1.5 text-xs shadow-2xl ${
            drawing
              ? "border-clay-400/70 bg-ink-800 text-white"
              : "border-white/15 bg-ink-900/92 text-white hover:border-white/30"
          }`}
          onClick={drawing ? onCancelDraw : onDraw}
        >
          {drawing ? "Cancel draw" : "Draw area"}
        </button>
        <button
          type="button"
          className="rounded-full border border-white/15 bg-ink-900/92 px-3 py-1.5 text-xs text-white shadow-2xl hover:border-white/30"
          onClick={onLockView}
        >
          Lock view
        </button>
      </div>
      {drawing ? (
        <p className="rounded-xl border border-white/10 bg-ink-900/95 px-3 py-2 text-xs leading-snug text-ink-100 shadow-2xl">
          Drag a rectangle on the map. Release to lock parcels inside it.
        </p>
      ) : null}
      {aoi && truncated ? (
        <p className="rounded-xl border border-white/10 bg-ink-900/95 px-3 py-2 text-[11px] leading-snug text-ink-300 shadow-2xl">
          This boundary has more parcels than the map will hold at once. The list stays put while you pan. Draw a
          smaller area to load every parcel in it.
        </p>
      ) : null}
    </div>
  );
}
