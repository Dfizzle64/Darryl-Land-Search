"use client";

type JumpToBarProps = {
  busy: boolean;
  note: string | null;
  onJump: (query: string) => void;
};

export function JumpToBar({ busy, note, onJump }: JumpToBarProps) {
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
      {note ? <span className="max-w-[18rem] text-[11px] leading-snug text-ink-400">{note}</span> : null}
    </form>
  );
}
