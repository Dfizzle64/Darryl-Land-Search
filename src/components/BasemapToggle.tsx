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
    <div className="map-chrome">
      <div
        role="group"
        aria-label="Basemap"
        className="map-scrim flex overflow-hidden rounded-full border"
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
              className={`whitespace-nowrap px-2.5 py-1.5 text-[11px] font-semibold sm:px-3 sm:text-sm ${
                active ? "map-scrim-active" : "text-white hover:bg-white/15"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      <p className="map-scrim mt-1.5 max-w-[16rem] rounded-lg border px-2 py-1 text-[10px] leading-snug text-ink-100 sm:max-w-xs">
        {basemapAttribution(value)}
      </p>
    </div>
  );
}
