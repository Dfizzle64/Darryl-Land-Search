"use client";

import { useEffect, useMemo, useState } from "react";
import { FilterSidebar } from "./FilterSidebar";
import { SouthCarolinaStatusNote } from "./SouthCarolinaStatusNote";
import { ParcelDrawer } from "./ParcelDrawer";
import { SiteMap } from "./SiteMap";
import { SitesPanel } from "./SitesPanel";
import { TractDrawer } from "./TractDrawer";
import { TractPanel } from "./TractPanel";
import { emptyStateHint, filterParcels } from "@/lib/filters";
import {
  countyKey,
  filterRuralRows,
  formatCountyLabel,
  marketSummary,
  parseCountyKey,
  showOrangeCountyPilot,
  southCarolinaStatusHelp,
  viewBounds,
} from "@/lib/markets";
import { rankSites } from "@/lib/score";
import {
  DEFAULT_FILTERS,
  MARKETS,
  SHED_CAVEAT,
  type FilterState,
  type FluConfig,
  type MarketId,
  type OpportunityZoneCollection,
  type Oz2TractCollection,
  type ParcelCollection,
  type RuralMarketTractCollection,
  type RuralMarketsCatalog,
  type ZoningConfig,
} from "@/lib/types";

type AppShellProps = {
  parcels: ParcelCollection;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  opportunityZones: OpportunityZoneCollection;
  oz2Tracts: Oz2TractCollection;
  ruralCatalog: RuralMarketsCatalog;
  ruralTracts: RuralMarketTractCollection;
  zoningConfig: ZoningConfig;
  fluConfig: FluConfig;
  meta: Record<string, unknown>;
};

type InventoryTab = "sites" | "tracts";

export function AppShell({
  parcels,
  traffic,
  opportunityZones,
  oz2Tracts,
  ruralCatalog,
  ruralTracts,
  zoningConfig,
  fluConfig,
  meta,
}: AppShellProps) {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [market, setMarket] = useState<MarketId>("Orlando");
  const [county, setCounty] = useState<string | null>("Orange");
  const [countyState, setCountyState] = useState<string | null>("Florida");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedTractGeoid, setSelectedTractGeoid] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(false);
  const [showTraffic, setShowTraffic] = useState(true);
  const [showOz, setShowOz] = useState(false);
  const [showOz2, setShowOz2] = useState(true);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [sitesOpen, setSitesOpen] = useState(false);
  const [inventoryTab, setInventoryTab] = useState<InventoryTab>("sites");
  const [error] = useState<string | null>(null);

  const summary = marketSummary(ruralCatalog, market);
  const visibleTracts = useMemo(
    () => filterRuralRows(ruralCatalog.rows, market, county, countyState),
    [ruralCatalog.rows, market, county, countyState],
  );
  const orangePilot = showOrangeCountyPilot(market, county, countyState);
  const statusHelp = southCarolinaStatusHelp(market, countyState);
  const bounds = useMemo(
    () => viewBounds(summary, ruralCatalog.rows, county, countyState),
    [summary, ruralCatalog.rows, county, countyState],
  );
  const boundsKey = `${market}|${countyState ?? ""}|${county ?? ""}`;

  const ruralPins = useMemo<GeoJSON.FeatureCollection<GeoJSON.Point>>(
    () => ({
      type: "FeatureCollection",
      features: visibleTracts.map((row) => ({
        type: "Feature",
        id: row.geoid,
        properties: {
          tractGeoid: row.geoid,
          rural: true,
          county: row.county,
          state: row.state,
          placeOrCorridor: row.placeOrCorridor,
        },
        geometry: { type: "Point", coordinates: [row.lon, row.lat] },
      })),
    }),
    [visibleTracts],
  );

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
  const selectedTract = visibleTracts.find((row) => row.geoid === selectedTractGeoid) ?? null;
  const fluUnknownCount = useMemo(
    () => parcels.features.filter((feature) => !feature.properties.flu?.code).length,
    [parcels.features],
  );
  const fluJoinedCount =
    typeof meta.fluJoinedCount === "number" ? meta.fluJoinedCount : parcels.features.length - fluUnknownCount;
  const hint = orangePilot ? emptyStateHint(filters, matched.length, fluUnknownCount) : null;

  useEffect(() => {
    if (selectedId && !matchedIds.has(selectedId) && !showExcluded) {
      setSelectedId(null);
    }
  }, [matchedIds, selectedId, showExcluded]);

  useEffect(() => {
    if (selectedTractGeoid && !visibleTracts.some((row) => row.geoid === selectedTractGeoid)) {
      setSelectedTractGeoid(null);
    }
  }, [selectedTractGeoid, visibleTracts]);

  useEffect(() => {
    if (!orangePilot) setInventoryTab("tracts");
  }, [orangePilot]);

  const selectSite = (id: string) => {
    setSelectedId(id);
    setSelectedTractGeoid(null);
    setSitesOpen(false);
    setFiltersOpen(false);
  };

  const selectTract = (geoid: string) => {
    setSelectedTractGeoid(geoid);
    setSelectedId(null);
    setSitesOpen(false);
    setFiltersOpen(false);
  };

  const changeMarket = (next: MarketId) => {
    setMarket(next);
    setCounty(null);
    setCountyState(null);
    setSelectedTractGeoid(null);
    setSelectedId(null);
    setInventoryTab("tracts");
  };

  const changeCounty = (key: string) => {
    const parsed = key ? parseCountyKey(key) : null;
    setCounty(parsed?.county ?? null);
    setCountyState(parsed?.state ?? null);
    setSelectedTractGeoid(null);
  };

  const showSites = orangePilot && inventoryTab === "sites";

  return (
    <div className="flex h-dvh min-h-0 flex-col bg-ink-950 text-ink-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-3 md:px-5">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-clay-400">
            {orangePilot && county === "Orange" ? "Orange County, Florida" : market}
          </p>
          <h1 className="font-display text-xl tracking-tight text-white md:text-2xl">
            {orangePilot && county === "Orange" ? "Multifamily site search" : "Rural-eligible tracts"}
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-[11px] text-ink-500">
            Market
            <select
              aria-label="Market"
              className="ml-1 rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm text-white"
              value={market}
              onChange={(event) => changeMarket(event.target.value as MarketId)}
            >
              {MARKETS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[11px] text-ink-500">
            County
            <select
              aria-label="County"
              className="ml-1 max-w-[14rem] rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm text-white"
              value={county && countyState ? countyKey(county, countyState) : ""}
              onChange={(event) => changeCounty(event.target.value)}
            >
              <option value="">All counties ({summary.rowCount})</option>
              {summary.counties.map((item) => (
                <option key={countyKey(item.county, item.state)} value={countyKey(item.county, item.state)}>
                  {formatCountyLabel(item.county, item.state)} ({item.count}
                  {item.outerEdge ? ", outer edge" : ""})
                </option>
              ))}
            </select>
          </label>
          <p className="hidden text-right text-xs text-ink-500 sm:block">
            {visibleTracts.length.toLocaleString()} rural-eligible {visibleTracts.length === 1 ? "tract" : "tracts"}
            {orangePilot ? (
              <span className="block text-[11px]">
                {matched.length.toLocaleString()} of {parcels.features.length.toLocaleString()} Orange County sample parcels
              </span>
            ) : (
              <span className="block text-[11px]">Tract overlay and pins · parcel extract is Orange County only</span>
            )}
          </p>
          {orangePilot ? (
            <button
              type="button"
              className="rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm xl:hidden"
              onClick={() => {
                setInventoryTab("sites");
                setSitesOpen(true);
              }}
            >
              Sites ({matched.length.toLocaleString()})
            </button>
          ) : null}
          <button
            type="button"
            className="rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm xl:hidden"
            onClick={() => {
              setInventoryTab("tracts");
              setSitesOpen(true);
            }}
          >
            Tracts ({visibleTracts.length.toLocaleString()})
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
      <p className="border-b border-white/10 px-4 py-2 text-[11px] leading-relaxed text-ink-500 md:px-5">{SHED_CAVEAT}</p>
      {statusHelp ? (
        <SouthCarolinaStatusNote
          note={statusHelp}
          className="border-b border-white/10 px-4 py-2 text-[11px] leading-relaxed text-ink-300 md:px-5"
        />
      ) : null}

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
          orangePilot={orangePilot}
          market={market}
          tractCount={visibleTracts.length}
          parcelNote={ruralCatalog.parcelNote}
          statusHelp={statusHelp}
        />
        <main className="relative min-w-0 flex-1">
          <SiteMap
            parcels={parcels}
            traffic={traffic}
            opportunityZones={opportunityZones}
            oz2Tracts={oz2Tracts}
            ruralTracts={ruralTracts}
            ruralPins={ruralPins}
            matchedIds={matchedIds}
            selectedId={selectedId}
            hoveredId={hoveredId}
            selectedTractGeoid={selectedTractGeoid}
            showExcluded={showExcluded}
            showTraffic={showTraffic}
            showOz={showOz}
            showOz2={showOz2}
            showOrangePilot={orangePilot}
            market={market}
            county={county}
            countyState={countyState}
            bounds={bounds}
            boundsKey={boundsKey}
            ozFilter={filters.ozFilter}
            onSelect={selectSite}
            onHover={setHoveredId}
            onSelectTract={selectTract}
          />
          <div className="pointer-events-none absolute bottom-3 right-3 top-16 z-10 hidden w-80 xl:block">
            <div className="pointer-events-auto flex h-full min-h-0 flex-col gap-2">
              {orangePilot ? (
                <div className="flex gap-1">
                  <button
                    type="button"
                    className={`rounded-full border px-3 py-1 text-xs ${inventoryTab === "sites" ? "border-clay-400/50 bg-ink-800 text-white" : "border-white/10 bg-ink-900/80 text-ink-300"}`}
                    onClick={() => setInventoryTab("sites")}
                  >
                    Orange County parcels
                  </button>
                  <button
                    type="button"
                    className={`rounded-full border px-3 py-1 text-xs ${inventoryTab === "tracts" ? "border-clay-400/50 bg-ink-800 text-white" : "border-white/10 bg-ink-900/80 text-ink-300"}`}
                    onClick={() => setInventoryTab("tracts")}
                  >
                    Rural tracts
                  </button>
                </div>
              ) : null}
              <div className="min-h-0 flex-1">
                {showSites ? (
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
                ) : (
                  <TractPanel tracts={visibleTracts} selectedGeoid={selectedTractGeoid} onSelect={selectTract} />
                )}
              </div>
            </div>
          </div>
          {hint && showSites ? (
            <div className="pointer-events-none absolute inset-x-0 top-4 flex justify-center px-4 xl:pr-[22rem]">
              <div className="pointer-events-auto max-w-md rounded-2xl border border-white/10 bg-ink-900/95 px-4 py-3 text-sm shadow-2xl">
                <p className="font-medium text-white">No parcels match these filters</p>
                <p className="mt-1 text-ink-300">{hint}</p>
              </div>
            </div>
          ) : null}
        </main>
        {selectedTract || !orangePilot ? (
          <TractDrawer tract={selectedTract} statusHelp={statusHelp} onClose={() => setSelectedTractGeoid(null)} />
        ) : (
          <ParcelDrawer
            parcel={selected}
            zoningConfig={zoningConfig}
            fluConfig={fluConfig}
            filters={filters}
            onClose={() => setSelectedId(null)}
          />
        )}
      </div>

      {sitesOpen ? (
        <div className="fixed inset-0 z-40 xl:hidden">
          <button type="button" className="absolute inset-0 bg-black/50" aria-label="Close list" onClick={() => setSitesOpen(false)} />
          <div className="absolute inset-x-0 bottom-0 flex h-[75vh] flex-col rounded-t-3xl border border-white/10 bg-ink-900 shadow-2xl">
            {showSites ? (
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
            ) : (
              <TractPanel
                variant="sheet"
                tracts={visibleTracts}
                selectedGeoid={selectedTractGeoid}
                onSelect={selectTract}
                onClose={() => setSitesOpen(false)}
              />
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
