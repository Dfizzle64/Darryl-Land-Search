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
    <div className="pointer-events-auto flex max-w-[18rem] flex-col-reverse items-end gap-1.5">
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
        className={`rounded-full border px-3 py-1.5 text-xs font-semibold sm:text-sm ${
          active ? "map-scrim-active border-white" : "map-scrim text-white hover:bg-white/10"
        }`}
      >
        Measure
      </button>
      {active ? (
        <div className="map-scrim rounded-xl border px-3 py-2 text-xs leading-snug text-ink-100">
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
