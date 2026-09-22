"use client";

import { useEffect, useMemo, useState } from "react";
import { FilterSidebar } from "./FilterSidebar";
import { ParcelDrawer } from "./ParcelDrawer";
import { SiteMap } from "./SiteMap";
import { SitesPanel } from "./SitesPanel";
import { emptyStateHint, filterParcels } from "@/lib/filters";
import { rankSites } from "@/lib/score";
import {
  DEFAULT_FILTERS,
  type FilterState,
  type FluConfig,
  type OpportunityZoneCollection,
  type Oz2TractCollection,
  type ParcelCollection,
  type ZoningConfig,
} from "@/lib/types";

type AppShellProps = {
  parcels: ParcelCollection;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  opportunityZones: OpportunityZoneCollection;
  oz2Tracts: Oz2TractCollection;
  zoningConfig: ZoningConfig;
  fluConfig: FluConfig;
  meta: Record<string, unknown>;
};

export function AppShell({
  parcels,
  traffic,
  opportunityZones,
  oz2Tracts,
  zoningConfig,
  fluConfig,
  meta,
}: AppShellProps) {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(false);
  const [showTraffic, setShowTraffic] = useState(true);
  const [showOz, setShowOz] = useState(false);
  const [showOz2, setShowOz2] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [sitesOpen, setSitesOpen] = useState(false);
  const [error] = useState<string | null>(null);

  const matched = useMemo(
    () => filterParcels(parcels.features, filters, zoningConfig, fluConfig),
    [parcels.features, filters, zoningConfig, fluConfig],
  );
  const ranked = useMemo(
    () => rankSites(matched, filters, zoningConfig, fluConfig),
    [matched, filters, zoningConfig, fluConfig],
  );
  const matchedIds = useMemo(() => new Set(matched.map((feature) => feature.properties.id)), [matched]);
  const selected = parcels.features.find((feature) => feature.properties.id === selectedId) ?? null;
  const fluUnknownCount = useMemo(
    () => parcels.features.filter((feature) => !feature.properties.flu?.code).length,
    [parcels.features],
  );
  const fluJoinedCount =
    typeof meta.fluJoinedCount === "number" ? meta.fluJoinedCount : parcels.features.length - fluUnknownCount;
  const hint = emptyStateHint(filters, matched.length, fluUnknownCount);

  useEffect(() => {
    if (selectedId && !matchedIds.has(selectedId) && !showExcluded) {
      setSelectedId(null);
    }
  }, [matchedIds, selectedId, showExcluded]);

  const selectSite = (id: string) => {
    setSelectedId(id);
    setSitesOpen(false);
    setFiltersOpen(false);
  };

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
            className="rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm xl:hidden"
            onClick={() => setSitesOpen(true)}
          >
            Sites ({matched.length.toLocaleString()})
          </button>
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
          fluConfig={fluConfig}
          matchedCount={matched.length}
          totalCount={parcels.features.length}
          fluJoinedCount={fluJoinedCount}
          showExcluded={showExcluded}
          onShowExcluded={setShowExcluded}
          showTraffic={showTraffic}
          onShowTraffic={setShowTraffic}
          showOz={showOz}
          onShowOz={setShowOz}
          showOz2={showOz2}
          onShowOz2={setShowOz2}
          open={filtersOpen}
          onClose={() => setFiltersOpen(false)}
          meta={meta}
        />
        <main className="relative min-w-0 flex-1">
          <SiteMap
            parcels={parcels}
            traffic={traffic}
            opportunityZones={opportunityZones}
            oz2Tracts={oz2Tracts}
            matchedIds={matchedIds}
            selectedId={selectedId}
            hoveredId={hoveredId}
            showExcluded={showExcluded}
            showTraffic={showTraffic}
            showOz={showOz}
            showOz2={showOz2}
            ozFilter={filters.ozFilter}
            onSelect={selectSite}
            onHover={setHoveredId}
          />
          <div className="pointer-events-none absolute bottom-3 right-3 top-16 z-10 hidden w-80 xl:block">
            <div className="pointer-events-auto h-full min-h-0">
              <SitesPanel
                sites={ranked}
                selectedId={selectedId}
                hoveredId={hoveredId}
                incomeGeography={filters.incomeGeography}
                landUseFilter={filters.landUseFilter}
                fluUnknownCount={fluUnknownCount}
                onSelect={selectSite}
                onHover={setHoveredId}
              />
            </div>
          </div>
          {hint ? (
            <div className="pointer-events-none absolute inset-x-0 top-4 flex justify-center px-4 xl:pr-[22rem]">
              <div className="pointer-events-auto max-w-md rounded-2xl border border-white/10 bg-ink-900/95 px-4 py-3 text-sm shadow-2xl">
                <p className="font-medium text-white">No parcels match these filters</p>
                <p className="mt-1 text-ink-300">{hint}</p>
              </div>
            </div>
          ) : null}
        </main>
        <ParcelDrawer
          parcel={selected}
          zoningConfig={zoningConfig}
          fluConfig={fluConfig}
          filters={filters}
          onClose={() => setSelectedId(null)}
        />
      </div>

      {sitesOpen ? (
        <div className="fixed inset-0 z-40 xl:hidden">
          <button type="button" className="absolute inset-0 bg-black/50" aria-label="Close sites" onClick={() => setSitesOpen(false)} />
          <div className="absolute inset-x-0 bottom-0 flex h-[75vh] flex-col rounded-t-3xl border border-white/10 bg-ink-900 shadow-2xl">
            <SitesPanel
              variant="sheet"
              sites={ranked}
              selectedId={selectedId}
              hoveredId={hoveredId}
              incomeGeography={filters.incomeGeography}
              landUseFilter={filters.landUseFilter}
              fluUnknownCount={fluUnknownCount}
              onSelect={selectSite}
              onHover={setHoveredId}
              onClose={() => setSitesOpen(false)}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
