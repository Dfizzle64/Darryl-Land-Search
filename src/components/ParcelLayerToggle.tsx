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
        className={`rounded-full border px-3.5 py-2 text-sm font-semibold shadow-2xl ${
          visible
            ? "border-moss-400/70 bg-ink-800 text-white"
            : "border-clay-400 bg-clay-500 text-ink-950 hover:bg-clay-400"
        }`}
      >
        {visible ? "Hide parcels" : "Show parcels"}
      </button>
      <p className="mt-1.5 rounded-lg border border-white/10 bg-ink-950/85 px-2 py-1 text-[11px] leading-snug text-ink-100">
        {hint}
      </p>
    </div>
  );
}
