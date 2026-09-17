"use client";

import { DEFAULT_FILTERS, type FilterState, type ZoningConfig } from "@/lib/types";

type FilterSidebarProps = {
  filters: FilterState;
  onChange: (next: FilterState) => void;
  zoningConfig: ZoningConfig;
  matchedCount: number;
  totalCount: number;
  showExcluded: boolean;
  onShowExcluded: (value: boolean) => void;
  showTraffic: boolean;
  onShowTraffic: (value: boolean) => void;
  open: boolean;
  onClose: () => void;
  meta: Record<string, unknown>;
};

function Toggle({
  label,
  checked,
  onChange,
  hint,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  hint?: string;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-3">
      <span>
        <span className="block text-sm text-white">{label}</span>
        {hint ? <span className="mt-0.5 block text-xs text-ink-500">{hint}</span> : null}
      </span>
      <input
        type="checkbox"
        className="mt-1 h-4 w-4 accent-moss-400"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
    </label>
  );
}

export function FilterSidebar({
  filters,
  onChange,
  zoningConfig,
  matchedCount,
  totalCount,
  showExcluded,
  onShowExcluded,
  showTraffic,
  onShowTraffic,
  open,
  onClose,
  meta,
}: FilterSidebarProps) {
  const generatedAt = typeof meta.generatedAt === "string" ? meta.generatedAt.slice(0, 10) : null;

  return (
    <>
      {open ? <button type="button" className="fixed inset-0 z-20 bg-black/50 md:hidden" onClick={onClose} aria-label="Close filters" /> : null}
      <aside
        className={`sidebar-scroll fixed inset-y-0 left-0 z-30 w-[min(100%,22rem)] overflow-y-auto border-r border-white/10 bg-ink-900 px-4 py-4 transition-transform md:static md:z-0 md:block md:w-[22rem] md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className="mb-4 flex items-center justify-between md:hidden">
          <h2 className="text-lg text-white">Filters</h2>
          <button type="button" className="text-sm text-ink-300" onClick={onClose}>
            Done
          </button>
        </div>

        <section className="rounded-2xl border border-white/10 bg-ink-800/70 p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-ink-500">Results</p>
          <p className="mt-1 font-display text-3xl text-white">{matchedCount.toLocaleString()}</p>
          <p className="text-xs text-ink-500">matching {totalCount.toLocaleString()} sample parcels</p>
          <button
            type="button"
            className="mt-3 text-xs text-clay-400 underline-offset-2 hover:underline"
            onClick={() => onChange({ ...DEFAULT_FILTERS })}
          >
            Reset filters
          </button>
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Zoning</h2>
          <Toggle
            label="Multifamily zoning only"
            checked={filters.multifamilyZoningOnly}
            onChange={(multifamilyZoningOnly) => onChange({ ...filters, multifamilyZoningOnly })}
            hint="Uses the configurable district list in data/zoning-config.json"
          />
          <Toggle
            label="Include planned development"
            checked={filters.includePlannedDevelopment}
            onChange={(includePlannedDevelopment) => onChange({ ...filters, includePlannedDevelopment })}
            hint="PD / PUD can allow multifamily, but entitlements are site-specific"
          />
          <details className="rounded-xl border border-white/10 bg-ink-950/40 px-3 py-2 text-xs text-ink-300">
            <summary className="cursor-pointer text-ink-100">Allowed district codes</summary>
            <ul className="mt-2 space-y-1">
              {zoningConfig.multifamilyTokens.map((token) => (
                <li key={token.token}>
                  <span className="text-clay-400">{token.token}</span> — {token.label}
                </li>
              ))}
            </ul>
            <p className="mt-2 text-ink-500">{zoningConfig.notes}</p>
          </details>
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Area income</h2>
          <label className="block text-sm">
            Census geography
            <select
              className="mt-1 w-full rounded-lg border border-white/10 bg-ink-950 px-3 py-2 text-sm"
              value={filters.incomeGeography}
              onChange={(event) =>
                onChange({ ...filters, incomeGeography: event.target.value as FilterState["incomeGeography"] })
              }
            >
              <option value="tract">Census tract</option>
              <option value="blockGroup">Block group</option>
            </select>
          </label>
          <label className="block text-sm">
            Minimum median household income
            <input
              type="range"
              min={0}
              max={200000}
              step={5000}
              value={filters.minIncome}
              onChange={(event) => onChange({ ...filters, minIncome: Number(event.target.value) })}
              className="mt-2 w-full accent-clay-400"
            />
            <span className="mt-1 block text-ink-300">
              {filters.minIncome === 0 ? "No minimum" : `$${filters.minIncome.toLocaleString()}+`}
            </span>
          </label>
          <Toggle
            label="Include unknown income"
            checked={filters.includeUnknownIncome}
            onChange={(includeUnknownIncome) => onChange({ ...filters, includeUnknownIncome })}
          />
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Nearby traffic</h2>
          <label className="block text-sm">
            Minimum AADT on nearest FDOT segment
            <input
              type="range"
              min={0}
              max={100000}
              step={1000}
              value={filters.minAadt}
              onChange={(event) => onChange({ ...filters, minAadt: Number(event.target.value) })}
              className="mt-2 w-full accent-clay-400"
            />
            <span className="mt-1 block text-ink-300">
              {filters.minAadt === 0 ? "No minimum" : `${filters.minAadt.toLocaleString()}+ vehicles/day`}
            </span>
          </label>
          <Toggle
            label="Include unknown AADT"
            checked={filters.includeUnknownAadt}
            onChange={(includeUnknownAadt) => onChange({ ...filters, includeUnknownAadt })}
          />
          <Toggle
            label="Show major-road AADT overlay"
            checked={showTraffic}
            onChange={onShowTraffic}
            hint="FDOT segments with 15,000+ AADT"
          />
        </section>

        <section className="mt-5 space-y-3">
          <h2 className="text-xs uppercase tracking-[0.16em] text-ink-500">Map</h2>
          <Toggle
            label="Show parcels that fail filters"
            checked={showExcluded}
            onChange={onShowExcluded}
            hint="Failed parcels render as faded outlines"
          />
        </section>

        <p className="mt-6 text-[11px] leading-relaxed text-ink-500">
          Fixture snapshot {generatedAt ?? "unknown"}. Owner, sale, and tax fields come from the Orange County Property
          Appraiser public GIS layer. Income is ACS median household income. AADT is the nearest FDOT count segment.
        </p>
      </aside>
    </>
  );
}
