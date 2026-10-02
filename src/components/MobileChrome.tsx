"use client";

import { activeFiltersLabel } from "@/lib/activeFilters";
import { formatCountyLabel, countyKey } from "@/lib/markets";
import type { MarketStateGroup } from "@/lib/marketGroups";
import type { SearchMarketId } from "@/lib/types";
import { JumpToBar } from "./JumpToBar";
import { MarketMenu } from "./MarketMenu";
import { SouthCarolinaStatusNote } from "./SouthCarolinaStatusNote";
import { ZoningKnowledgePanel } from "./ZoningKnowledgePanel";
import type { GeocodeSuggestion } from "@/lib/jumpTo";
import type { FluConfig, ZoningConfig } from "@/lib/types";

type CountyOption = { county: string; state: string; count: number; outerEdge: boolean };

type MobileHeaderActionsProps = {
  searchOpen: boolean;
  onToggleSearch: () => void;
  activeCount: number;
  onOpenFilters: () => void;
  moreOpen: boolean;
  onToggleMore: () => void;
};

export function MobileHeaderActions({
  searchOpen,
  onToggleSearch,
  activeCount,
  onOpenFilters,
  moreOpen,
  onToggleMore,
}: MobileHeaderActionsProps) {
  return (
    <div className="dls-narrow shrink-0 items-center gap-1">
      <button
        type="button"
        className="dls-hit inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/20 bg-ink-800 text-white"
        aria-expanded={searchOpen}
        aria-label="Jump to address"
        onClick={onToggleSearch}
      >
        <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
          <circle cx="7.5" cy="7.5" r="5" fill="none" stroke="currentColor" strokeWidth="1.8" />
          <path d="M11.5 11.5 L16 16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </button>
      <button
        type="button"
        className="dls-hit relative inline-flex h-11 items-center gap-1 rounded-full border border-white/20 bg-ink-800 px-3 text-sm text-white"
        aria-label={activeFiltersLabel(activeCount)}
        onClick={onOpenFilters}
      >
        Filters
        {activeCount > 0 ? (
          <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-clay-500 px-1 text-[11px] font-semibold text-ink-950">
            {activeCount}
          </span>
        ) : null}
      </button>
      <button
        type="button"
        className="dls-hit inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/20 bg-ink-800 text-lg text-white"
        aria-expanded={moreOpen}
        aria-label="More"
        onClick={onToggleMore}
      >
        ···
      </button>
    </div>
  );
}

type MobileSearchBarProps = {
  open: boolean;
  busy: boolean;
  note: string | null;
  error: string | null;
  suggestions: GeocodeSuggestion[];
  onJump: (query: string) => void;
  onSuggestion: (suggestion: GeocodeSuggestion) => void;
};

export function MobileSearchBar({ open, busy, note, error, suggestions, onJump, onSuggestion }: MobileSearchBarProps) {
  if (!open) return null;
  return (
    <div className="dls-narrow-block border-b border-white/10 bg-ink-950 px-[max(0.75rem,env(safe-area-inset-left))] py-2 pr-[max(0.75rem,env(safe-area-inset-right))]">
      <JumpToBar
        statusId="jump-to-status-mobile"
        busy={busy}
        note={note}
        error={error}
        suggestions={suggestions}
        onJump={onJump}
        onSuggestion={onSuggestion}
      />
    </div>
  );
}

type MobileMoreSheetProps = {
  open: boolean;
  onClose: () => void;
  market: SearchMarketId;
  marketGroups: MarketStateGroup[];
  onMarket: (market: SearchMarketId) => void;
  county: string | null;
  countyState: string | null;
  countyOptions: CountyOption[];
  countyTotal: number;
  onCounty: (key: string) => void;
  showSites: boolean;
  siteCount: number;
  tractCount: number;
  onOpenSites: () => void;
  onOpenTracts: () => void;
  onOpenOzHelp: () => void;
  caveat: string;
  statusHelp: string | null;
  zoningConfig: ZoningConfig;
  fluConfig: FluConfig;
  fluJoinedCount: number | null;
  parcelCount: number;
};

export function MobileMoreSheet(props: MobileMoreSheetProps) {
  if (!props.open) return null;
  const countyValue = props.county && props.countyState ? countyKey(props.county, props.countyState) : "";
  return (
    <div className="dls-narrow-block fixed inset-0 z-50">
      <button type="button" className="absolute inset-0 bg-black/50" aria-label="Close menu" onClick={props.onClose} />
      <div className="absolute inset-x-0 bottom-0 flex max-h-[min(92dvh,100%)] flex-col rounded-t-3xl border border-white/10 bg-ink-900 pb-[max(1rem,env(safe-area-inset-bottom))] shadow-2xl">
        <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
          <h2 className="text-lg text-white">Menu</h2>
          <button
            type="button"
            className="dls-hit rounded-full border border-white/20 px-4 text-sm text-white"
            aria-label="Close menu"
            onClick={props.onClose}
          >
            Close
          </button>
        </div>
        <div className="sidebar-scroll min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.16em] text-ink-500">Market</p>
            <MarketMenu value={props.market} groups={props.marketGroups} onChange={props.onMarket} buttonClassName="dls-hit" />
          </div>
          <label className="block text-sm text-ink-300">
            County
            <select
              aria-label="County"
              className="dls-hit mt-1 w-full rounded-xl border border-white/15 bg-ink-800 px-3 text-base text-white"
              value={countyValue}
              onChange={(event) => props.onCounty(event.target.value)}
            >
              <option value="">All counties ({props.countyTotal})</option>
              {props.countyOptions.map((item) => (
                <option key={countyKey(item.county, item.state)} value={countyKey(item.county, item.state)}>
                  {formatCountyLabel(item.county, item.state)} ({item.count}
                  {item.outerEdge ? ", outer edge" : ""})
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-2">
            {props.showSites ? (
              <button
                type="button"
                className="dls-hit rounded-xl border border-white/15 bg-ink-800 px-3 text-sm text-white"
                onClick={props.onOpenSites}
              >
                Sites ({props.siteCount.toLocaleString()})
              </button>
            ) : null}
            <button
              type="button"
              className="dls-hit rounded-xl border border-white/15 bg-ink-800 px-3 text-sm text-white"
              onClick={props.onOpenTracts}
            >
              Tracts ({props.tractCount.toLocaleString()})
            </button>
          </div>
          <button
            type="button"
            className="dls-hit w-full rounded-xl border border-white/15 bg-ink-800 px-3 text-left text-sm text-white"
            onClick={props.onOpenOzHelp}
          >
            How OZ 2.0 works
          </button>
          <details className="rounded-xl border border-white/10 bg-ink-800/70 p-3">
            <summary className="dls-hit cursor-pointer text-sm text-white">Notes</summary>
            <p className="mt-2 text-sm leading-relaxed text-ink-300">{props.caveat}</p>
            {props.statusHelp ? (
              <SouthCarolinaStatusNote note={props.statusHelp} className="mt-2 text-sm leading-relaxed text-ink-300" />
            ) : null}
          </details>
          <details className="rounded-xl border border-white/10 bg-ink-800/70 p-3">
            <summary className="dls-hit cursor-pointer text-sm text-white">Zoning reference</summary>
            <ZoningKnowledgePanel
              zoningConfig={props.zoningConfig}
              fluConfig={props.fluConfig}
              fluJoinedCount={props.fluJoinedCount}
              parcelCount={props.parcelCount}
            />
          </details>
        </div>
      </div>
    </div>
  );
}
