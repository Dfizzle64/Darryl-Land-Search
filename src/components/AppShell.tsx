"use client";

import { useEffect, useMemo, useState } from "react";
import { FilterSidebar } from "./FilterSidebar";
import { ParcelDrawer } from "./ParcelDrawer";
import { SiteMap } from "./SiteMap";
import { filterParcels } from "@/lib/filters";
import { DEFAULT_FILTERS, type FilterState, type ParcelCollection, type ZoningConfig } from "@/lib/types";

type AppShellProps = {
  parcels: ParcelCollection;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  zoningConfig: ZoningConfig;
  meta: Record<string, unknown>;
};

export function AppShell({ parcels, traffic, zoningConfig, meta }: AppShellProps) {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(false);
  const [showTraffic, setShowTraffic] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [error] = useState<string | null>(null);

  const matched = useMemo(
    () => filterParcels(parcels.features, filters, zoningConfig),
    [parcels.features, filters, zoningConfig],
  );
  const matchedIds = useMemo(() => new Set(matched.map((feature) => feature.properties.id)), [matched]);
  const selected = parcels.features.find((feature) => feature.properties.id === selectedId) ?? null;

  useEffect(() => {
    if (selectedId && !matchedIds.has(selectedId) && !showExcluded) {
      setSelectedId(null);
    }
  }, [matchedIds, selectedId, showExcluded]);

  return (
    <div className="flex h-dvh min-h-0 flex-col bg-ink-950 text-ink-100">
      <header className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3 md:px-5">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-clay-400">Orange County, Florida</p>
          <h1 className="font-display text-xl tracking-tight text-white md:text-2xl">Multifamily site search</h1>
        </div>
        <div className="flex items-center gap-2">
          <p className="hidden text-right text-xs text-ink-500 sm:block">
            {matched.length.toLocaleString()} of {parcels.features.length.toLocaleString()} sample parcels
            <span className="block text-[11px]">Pilot · public GIS fixtures · not a complete county extract</span>
          </p>
          <button
            type="button"
            className="rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm md:hidden"
            onClick={() => setFiltersOpen(true)}
          >
            Filters
          </button>
        </div>
      </header>

      {error ? (
        <div className="border-b border-red-500/30 bg-red-950/60 px-4 py-2 text-sm text-red-100">{error}</div>
      ) : null}

      <div className="flex min-h-0 flex-1">
        <FilterSidebar
          filters={filters}
          onChange={setFilters}
          zoningConfig={zoningConfig}
          matchedCount={matched.length}
          totalCount={parcels.features.length}
          showExcluded={showExcluded}
          onShowExcluded={setShowExcluded}
          showTraffic={showTraffic}
          onShowTraffic={setShowTraffic}
          open={filtersOpen}
          onClose={() => setFiltersOpen(false)}
          meta={meta}
        />
        <main className="relative min-w-0 flex-1">
          <SiteMap
            parcels={parcels}
            traffic={traffic}
            matchedIds={matchedIds}
            selectedId={selectedId}
            hoveredId={hoveredId}
            showExcluded={showExcluded}
            showTraffic={showTraffic}
            onSelect={setSelectedId}
            onHover={setHoveredId}
          />
          {matched.length === 0 ? (
            <div className="pointer-events-none absolute inset-x-0 top-4 flex justify-center px-4">
              <div className="pointer-events-auto max-w-md rounded-2xl border border-white/10 bg-ink-900/95 px-4 py-3 text-sm shadow-2xl">
                <p className="font-medium text-white">No parcels match these filters</p>
                <p className="mt-1 text-ink-300">
                  Lower the income or AADT thresholds, include planned development, or turn off multifamily-only.
                </p>
              </div>
            </div>
          ) : null}
        </main>
        <ParcelDrawer
          parcel={selected}
          zoningConfig={zoningConfig}
          includePlannedDevelopment={filters.includePlannedDevelopment}
          incomeGeography={filters.incomeGeography}
          onClose={() => setSelectedId(null)}
        />
      </div>
    </div>
  );
}
