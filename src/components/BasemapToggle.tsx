"use client";

import { basemapAttribution, type BasemapMode } from "@/lib/basemap";

const OPTIONS: { value: BasemapMode; label: string }[] = [
  { value: "streets", label: "Streets" },
  { value: "satellite", label: "Satellite hybrid" },
  { value: "dark", label: "Dark" },
];

type BasemapToggleProps = {
  value: BasemapMode;
  onChange: (mode: BasemapMode) => void;
};

export function BasemapToggle({ value, onChange }: BasemapToggleProps) {
  return (
    <div className="pointer-events-auto">
      <div
        role="group"
        aria-label="Basemap"
        className="flex overflow-hidden rounded-full border border-white/15 bg-ink-900/92 shadow-2xl backdrop-blur-sm"
      >
        {OPTIONS.map((option) => {
          const active = value === option.value;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              aria-label={`${option.label} basemap`}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onChange(option.value);
              }}
              className={`whitespace-nowrap px-2.5 py-1.5 text-[11px] font-medium sm:px-3 sm:text-sm ${
                active ? "bg-white/15 text-white" : "text-ink-300 hover:text-white"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      <p className="mt-1.5 max-w-[16rem] rounded-lg bg-ink-950/75 px-2 py-1 text-[10px] leading-snug text-ink-300 sm:max-w-xs">
        {basemapAttribution(value)}
      </p>
    </div>
  );
}
