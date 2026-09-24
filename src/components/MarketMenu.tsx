"use client";

import { useEffect, useRef, useState } from "react";
import { isOtherMarketId } from "@/lib/markets";
import { MARKETS, OTHER_MARKETS, PARCEL_MARKETS, type SearchMarketId } from "@/lib/types";

type MarketMenuProps = {
  value: SearchMarketId;
  onChange: (market: SearchMarketId) => void;
};

export function MarketMenu({ value, onChange }: MarketMenuProps) {
  const [open, setOpen] = useState(false);
  const [otherOpen, setOtherOpen] = useState(() => isOtherMarketId(value));
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("mousedown", onPointer);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onPointer);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const choose = (market: SearchMarketId) => {
    onChange(market);
    setOpen(false);
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label="Market"
        aria-haspopup="listbox"
        aria-expanded={open}
        className="rounded-full border border-white/30 bg-ink-800 px-3 py-1.5 text-sm text-white"
        onClick={() => {
          setOpen((current) => !current);
          if (isOtherMarketId(value)) setOtherOpen(true);
        }}
      >
        {value}
        <span className="ml-2 text-xs text-clay-300">{open ? "▴" : "▾"}</span>
      </button>
      {open ? (
        <div
          role="listbox"
          aria-label="Markets"
          className="absolute right-0 z-30 mt-1 max-h-[70vh] w-64 overflow-y-auto rounded-2xl border border-white/15 bg-ink-900 p-1.5 shadow-2xl"
        >
          <p className="px-2 pb-1 pt-1.5 text-[10px] uppercase tracking-[0.16em] text-ink-500">Primary</p>
          {MARKETS.map((market) => (
            <button
              key={market}
              type="button"
              role="option"
              aria-selected={market === value}
              className={`block w-full rounded-xl px-2 py-1.5 text-left text-sm ${
                market === value ? "bg-white/10 text-white" : "text-ink-100 hover:bg-white/5"
              }`}
              onClick={() => choose(market)}
            >
              {market}
            </button>
          ))}
          <button
            type="button"
            aria-expanded={otherOpen}
            className="mt-1.5 flex w-full items-center justify-between rounded-xl border border-clay-400/70 bg-ink-800 px-2.5 py-2 text-left text-ink-100 hover:border-clay-400 hover:bg-ink-700"
            onClick={() => setOtherOpen((current) => !current)}
          >
            <span>
              <span className="block text-[10px] uppercase tracking-[0.16em] text-clay-300">More markets</span>
              <span className="text-sm font-medium text-white">Other MSAs ({OTHER_MARKETS.length + PARCEL_MARKETS.length})</span>
            </span>
            <span className="text-sm text-clay-300" aria-hidden>
              {otherOpen ? "▾" : "▸"}
            </span>
          </button>
          {otherOpen
            ? [...OTHER_MARKETS, ...PARCEL_MARKETS].map((market) => (
                <button
                  key={market}
                  type="button"
                  role="option"
                  aria-selected={market === value}
                  className={`block w-full rounded-xl py-1.5 pl-4 pr-2 text-left text-sm ${
                    market === value ? "bg-white/15 text-white" : "text-ink-100 hover:bg-white/10"
                  }`}
                  onClick={() => choose(market)}
                >
                  {market}
                </button>
              ))
            : null}
        </div>
      ) : null}
    </div>
  );
}
