"use client";

import type { GeocodeSuggestion } from "@/lib/jumpTo";

type JumpToBarProps = {
  busy: boolean;
  note: string | null;
  error: string | null;
  suggestions?: GeocodeSuggestion[];
  onJump: (query: string) => void;
  onSuggestion?: (suggestion: GeocodeSuggestion) => void;
  /** Keeps the desktop status id when a second bar is mounted on a phone. */
  statusId?: string;
};

export function JumpToBar({
  busy,
  note,
  error,
  suggestions = [],
  onJump,
  onSuggestion,
  statusId = "jump-to-status",
}: JumpToBarProps) {
  return (
    <form
      className="flex flex-wrap items-center gap-1 max-[767px]:w-full"
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const query = String(data.get("jump") ?? "").trim();
        if (!query || busy) return;
        onJump(query);
      }}
    >
      <label className="text-[11px] text-ink-500 max-[767px]:min-w-0 max-[767px]:flex-1 max-[767px]:text-sm">
        Jump to
        <input
          name="jump"
          aria-label="Jump to address or coordinates"
          aria-invalid={error ? true : undefined}
          aria-describedby={error || note ? statusId : undefined}
          placeholder="Address or lat, long"
          className="ml-1 w-44 rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm text-white placeholder:text-ink-500 sm:w-56 max-[767px]:ml-0 max-[767px]:min-h-11 max-[767px]:w-full max-[767px]:flex-1 max-[767px]:text-base"
        />
      </label>
      <button
        type="submit"
        disabled={busy}
        className="rounded-full border border-white/20 bg-ink-800 px-3 py-1.5 text-sm text-white disabled:opacity-50 max-[767px]:min-h-11 max-[767px]:px-4"
      >
        {busy ? "Finding…" : "Go"}
      </button>
      {suggestions.length > 0 ? (
        <div className="flex basis-full flex-wrap items-center gap-1">
          <span className="text-[11px] text-ink-400">Did you mean</span>
          {suggestions.map((suggestion) => (
            <button
              key={`${suggestion.provider}:${suggestion.lng}:${suggestion.lat}:${suggestion.label}`}
              type="button"
              disabled={busy}
              className="rounded-full border border-white/20 bg-ink-800 px-2.5 py-1 text-left text-[11px] leading-snug text-white disabled:opacity-50 max-[767px]:min-h-11 max-[767px]:text-sm"
              onClick={() => onSuggestion?.(suggestion)}
            >
              {suggestion.label}
            </button>
          ))}
        </div>
      ) : error ? (
        <span id={statusId} role="alert" className="max-w-[18rem] text-[11px] leading-snug text-clay-300 max-[767px]:text-sm">
          {error}
        </span>
      ) : note ? (
        <span id={statusId} className="max-w-[18rem] text-[11px] leading-snug text-ink-400 max-[767px]:text-sm">
          {note}
        </span>
      ) : null}
    </form>
  );
}
