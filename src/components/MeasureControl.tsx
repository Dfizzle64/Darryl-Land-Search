"use client";

import { formatMiles, summarizeMeasure, type LngLat } from "@/lib/measure";

type MeasureControlProps = {
  active: boolean;
  points: LngLat[];
  onStart: () => void;
  onClear: () => void;
  onCancel: () => void;
};

export function MeasureControl({ active, points, onStart, onClear, onCancel }: MeasureControlProps) {
  const summary = summarizeMeasure(points);
  return (
    <div className="pointer-events-auto flex max-w-[18rem] flex-col items-start gap-1.5">
      <button
        type="button"
        aria-pressed={active}
        aria-label="Measure distance"
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          if (active) onCancel();
          else onStart();
        }}
        className={`rounded-full border px-3 py-1.5 text-xs font-medium shadow-2xl sm:text-sm ${
          active ? "border-white/40 bg-white/15 text-white" : "border-white/15 bg-ink-900/92 text-ink-100 hover:text-white"
        }`}
      >
        Measure
      </button>
      {active ? (
        <div className="rounded-xl border border-white/15 bg-ink-900/95 px-3 py-2 text-xs leading-snug text-ink-100 shadow-2xl">
          <p className="font-medium text-white">Distance</p>
          {summary.segmentsMiles.length === 0 ? (
            <p className="mt-1 text-ink-300">Click the map to add points. Each click extends the line.</p>
          ) : (
            <ul className="mt-1 space-y-0.5">
              {summary.segmentsMiles.map((miles, index) => (
                <li key={`${index}-${miles.toFixed(4)}`}>
                  Segment {index + 1}: {formatMiles(miles)}
                </li>
              ))}
              <li className="pt-1 font-medium text-white">Total: {formatMiles(summary.totalMiles)}</li>
            </ul>
          )}
          <div className="mt-2 flex gap-1.5">
            <button
              type="button"
              className="rounded-full border border-white/20 px-2 py-0.5 text-[11px] text-white hover:border-white/40"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onClear();
              }}
            >
              Clear
            </button>
            <button
              type="button"
              className="rounded-full border border-white/20 px-2 py-0.5 text-[11px] text-white hover:border-white/40"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onCancel();
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
