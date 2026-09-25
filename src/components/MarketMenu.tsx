"use client";

import { useEffect, useRef, useState } from "react";
import type { MarketStateGroup } from "@/lib/marketGroups";
import type { SearchMarketId } from "@/lib/types";

type MarketMenuProps = {
  value: SearchMarketId;
  groups: MarketStateGroup[];
  onChange: (market: SearchMarketId) => void;
};

export function MarketMenu({ value, groups, onChange }: MarketMenuProps) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [flyoutTop, setFlyoutTop] = useState(0);
  const [flyoutRight, setFlyoutRight] = useState(true);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setExpanded(null);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        setExpanded(null);
      }
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
    setExpanded(null);
  };

  const placeFlyout = (row: HTMLElement) => {
    const menu = menuRef.current;
    if (!menu) return;
    const menuBox = menu.getBoundingClientRect();
    const rowBox = row.getBoundingClientRect();
    setFlyoutTop(rowBox.top - menuBox.top);
    const spaceOnRight = window.innerWidth - menuBox.right;
    setFlyoutRight(spaceOnRight < 240 && menuBox.left > spaceOnRight);
  };

  const reveal = (state: string, row: HTMLElement) => {
    placeFlyout(row);
    setExpanded(state);
  };

  const expandedGroup = groups.find((group) => group.state === expanded) ?? null;

  return (
    <div ref={rootRef} className="relative z-50">
      <button
        type="button"
        aria-label="Market"
        aria-haspopup="menu"
        aria-expanded={open}
        className="rounded-full border border-white/30 bg-ink-800 px-3 py-1.5 text-sm text-white"
        onClick={() => {
          setOpen((current) => {
            if (current) setExpanded(null);
            return !current;
          });
        }}
      >
        {value}
        <span className="ml-2 text-xs text-clay-300">{open ? "▴" : "▾"}</span>
      </button>
      {open ? (
        <div ref={menuRef} className="absolute right-0 z-30 mt-1">
          <div
            role="menu"
            aria-label="Markets by state"
            className="max-h-[70vh] w-60 overflow-y-auto rounded-2xl border border-white/15 bg-ink-900 p-1.5 shadow-2xl"
          >
            {groups.map((group) => {
              const shown = expanded === group.state;
              const selectedHere = group.markets.includes(value);
              return (
                <div key={group.state}>
                  <button
                    type="button"
                    role="menuitem"
                    aria-expanded={shown}
                    aria-haspopup="menu"
                    className={`flex w-full items-center justify-between rounded-xl px-2 py-1.5 text-left text-sm ${
                      selectedHere ? "bg-white/10 text-white" : "text-ink-100 hover:bg-white/5"
                    }`}
                    onMouseEnter={(event) => reveal(group.state, event.currentTarget)}
                    onClick={(event) => {
                      if (event.detail !== 0) return;
                      setExpanded((current) => (current === group.state ? null : group.state));
                    }}
                    onPointerUp={(event) => {
                      if (event.pointerType === "mouse") return;
                      placeFlyout(event.currentTarget);
                      setExpanded((current) => (current === group.state ? null : group.state));
                    }}
                  >
                    <span>{group.state}</span>
                    <span className="text-xs text-clay-300" aria-hidden>
                      {shown ? "◂" : "▸"}
                    </span>
                  </button>
                  {shown ? (
                    <div role="menu" aria-label={`${group.state} markets`} className="mb-1 ml-2 space-y-0.5 sm:hidden">
                      {group.markets.map((market) => (
                        <button
                          key={market}
                          type="button"
                          role="menuitemradio"
                          aria-checked={market === value}
                          className={`block w-full rounded-lg px-2 py-1.5 text-left text-sm ${
                            market === value ? "bg-white/15 text-white" : "text-ink-100 hover:bg-white/10"
                          }`}
                          onClick={() => choose(market)}
                        >
                          {market}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
          {expandedGroup ? (
            <div
              role="menu"
              aria-label={`${expandedGroup.state} markets`}
              className="absolute hidden w-56 rounded-2xl border border-white/15 bg-ink-900 p-1.5 shadow-2xl sm:block"
              style={
                flyoutRight
                  ? { top: flyoutTop, right: "calc(100% - 8px)" }
                  : { top: flyoutTop, left: "calc(100% - 8px)" }
              }
              onMouseEnter={() => setExpanded(expandedGroup.state)}
            >
              {expandedGroup.markets.map((market) => (
                <button
                  key={market}
                  type="button"
                  role="menuitemradio"
                  aria-checked={market === value}
                  className={`block w-full rounded-xl px-2 py-1.5 text-left text-sm ${
                    market === value ? "bg-white/15 text-white" : "text-ink-100 hover:bg-white/10"
                  }`}
                  onClick={() => choose(market)}
                >
                  {market}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
