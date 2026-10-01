"use client";

import type { GeocodeSuggestion } from "@/lib/jumpTo";

type JumpToBarProps = {
  busy: boolean;
  note: string | null;
  error: string | null;
  suggestions?: GeocodeSuggestion[];
  onJump: (query: string) => void;
  onSuggestion?: (suggestion: GeocodeSuggestion) => void;
};

export function JumpToBar({ busy, note, error, suggestions = [], onJump, onSuggestion }: JumpToBarProps) {
  return (
    <form
      className="flex flex-wrap items-center gap-1"
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const query = String(data.get("jump") ?? "").trim();
        if (!query || busy) return;
        onJump(query);
      }}
    >
      <label className="text-[11px] text-ink-500">
        Jump to
        <input
          name="jump"
          aria-label="Jump to address or coordinates"
          aria-invalid={error ? true : undefined}
          aria-describedby={error || note ? "jump-to-status" : undefined}
          placeholder="Address or lat, long"
          className="ml-1 w-44 rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm text-white placeholder:text-ink-500 sm:w-56"
        />
      </label>
      <button
        type="submit"
        disabled={busy}
        className="rounded-full border border-white/20 bg-ink-800 px-3 py-1.5 text-sm text-white disabled:opacity-50"
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
              className="rounded-full border border-white/20 bg-ink-800 px-2.5 py-1 text-left text-[11px] leading-snug text-white disabled:opacity-50"
              onClick={() => onSuggestion?.(suggestion)}
            >
              {suggestion.label}
            </button>
          ))}
        </div>
      ) : error ? (
        <span id="jump-to-status" role="alert" className="max-w-[18rem] text-[11px] leading-snug text-clay-300">
          {error}
        </span>
      ) : note ? (
        <span id="jump-to-status" className="max-w-[18rem] text-[11px] leading-snug text-ink-400">
          {note}
        </span>
      ) : null}
    </form>
  );
}
