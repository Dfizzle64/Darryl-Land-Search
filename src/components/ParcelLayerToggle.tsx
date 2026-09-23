"use client";

type ParcelLayerToggleProps = {
  visible: boolean;
  hint: string;
  onToggle: () => void;
};

export function ParcelLayerToggle({ visible, hint, onToggle }: ParcelLayerToggleProps) {
  return (
    <div data-parcel-toggle className="map-chrome max-w-[18rem]">
      <button
        type="button"
        aria-pressed={visible}
        aria-label={visible ? "Hide parcels" : "Show parcels"}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onToggle();
        }}
        className={`rounded-full border px-3.5 py-2 text-sm font-semibold ${
          visible
            ? "map-scrim text-white"
            : "border-ink-950 bg-clay-500 text-ink-950 shadow-[0_10px_28px_rgba(0,0,0,0.55)] hover:bg-clay-400"
        }`}
      >
        {visible ? "Hide parcels" : "Show parcels"}
      </button>
      <p className="map-scrim mt-1.5 rounded-lg border px-2 py-1 text-[11px] leading-snug text-ink-100">
        {hint}
      </p>
    </div>
  );
}
