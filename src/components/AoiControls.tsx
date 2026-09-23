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
      className="map-chrome absolute inset-x-3 top-14 z-30 flex flex-col items-end gap-2 sm:inset-x-auto sm:right-4 sm:top-4 sm:max-w-[22rem]"
    >
      <div className="flex max-w-full flex-wrap items-center justify-end gap-1.5">
        {aoi ? (
          <div
            className="map-scrim flex max-w-full flex-wrap items-center gap-x-2 gap-y-1 rounded-full border px-3 py-1.5 text-xs text-white"
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
          className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
            drawing ? "map-scrim-active border-white" : "map-scrim text-white hover:bg-white/10"
          }`}
          onClick={drawing ? onCancelDraw : onDraw}
        >
          {drawing ? "Cancel draw" : "Draw area"}
        </button>
        <button
          type="button"
          className="map-scrim rounded-full border px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/10"
          onClick={onLockView}
        >
          Lock view
        </button>
      </div>
      {drawing ? (
        <p className="map-scrim rounded-xl border px-3 py-2 text-xs leading-snug text-ink-100">
          Drag a rectangle on the map. Release to lock parcels inside it.
        </p>
      ) : null}
      {aoi && truncated ? (
        <p className="map-scrim rounded-xl border px-3 py-2 text-[11px] leading-snug text-ink-100">
          This boundary has more parcels than the map will hold at once. The list stays put while you pan. Draw a
          smaller area to load every parcel in it.
        </p>
      ) : null}
    </div>
  );
}
