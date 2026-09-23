"use client";

type ParcelLayerToggleProps = {
  visible: boolean;
  hint: string;
  onToggle: () => void;
};

export function ParcelLayerToggle({ visible, hint, onToggle }: ParcelLayerToggleProps) {
  return (
    <div
      data-parcel-toggle
      className="pointer-events-auto max-w-[16.5rem]"
    >
      <button
        type="button"
        aria-pressed={visible}
        aria-label={visible ? "Hide parcels" : "Show parcels"}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onToggle();
        }}
        className={`rounded-full border px-3 py-1.5 text-xs font-medium shadow-2xl ${
          visible
            ? "border-moss-400/70 bg-ink-800 text-white"
            : "border-white/15 bg-ink-900/92 text-ink-100 hover:border-white/30"
        }`}
      >
        Parcels {visible ? "on" : "off"}
      </button>
      <p className="mt-1.5 rounded-lg border border-white/10 bg-ink-950/80 px-2 py-1 text-[10px] leading-snug text-ink-300">
        {hint}
      </p>
    </div>
  );
}
