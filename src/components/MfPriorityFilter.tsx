"use client";

import { MF_PRIORITY_DISCLAIMER } from "@/lib/scMfPriority";
import type { MfPriorityView } from "@/lib/types";

const OPTIONS: { value: MfPriorityView; label: string }[] = [
  { value: "all", label: "All rural" },
  { value: "priority", label: "SC MF priority" },
  { value: "A", label: "Tier A" },
  { value: "B", label: "Tier B" },
];

type MfPriorityFilterProps = {
  value: MfPriorityView;
  counts: { all: number; priority: number; A: number; B: number };
  onChange: (view: MfPriorityView) => void;
  compact?: boolean;
};

export function MfPriorityFilter({ value, counts, onChange, compact = false }: MfPriorityFilterProps) {
  return (
    <fieldset className={compact ? "space-y-1" : "space-y-2"}>
      <legend className={compact ? "sr-only" : "text-xs uppercase tracking-[0.16em] text-ink-500"}>
        SC multifamily priority
      </legend>
      <div className="flex flex-wrap gap-1" role="group" aria-label="SC multifamily priority">
        {OPTIONS.map((option) => {
          const selected = value === option.value;
          const count = counts[option.value];
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={selected}
              className={`rounded-full border px-2 py-1 text-[11px] ${
                selected ? "border-clay-400/70 bg-ink-800 text-white" : "border-white/10 bg-ink-950/40 text-ink-300"
              }`}
              onClick={() => onChange(option.value)}
            >
              {option.label} ({count.toLocaleString()})
            </button>
          );
        })}
      </div>
      {compact ? null : (
        <p className="text-xs leading-relaxed text-ink-500">
          {MF_PRIORITY_DISCLAIMER} Gold outlines are Tier A. Blue outlines are Tier B. Tract polygons have no center dot. The status chip
          stays eligible and not designated.
        </p>
      )}
    </fieldset>
  );
}
