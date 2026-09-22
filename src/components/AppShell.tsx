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
  showOrlandoParcels,
  southCarolinaStatusHelp,
  viewBounds,
  viewIncludesSouthCarolina,
} from "@/lib/markets";
import { isFull5AcCounty, ORLANDO_FIPS_BY_NAME, ORLANDO_SHED_COUNTIES } from "@/lib/orlandoParcels";
import { rankSites } from "@/lib/score";
import {
  annotateRuralRows,
  countMfPriority,
  filterByMfPriority,
  geoidFilterForView,
  geoidsForHighlight,
  sortTractsForDisplay,
} from "@/lib/scMfPriority";
import {
  DEFAULT_FILTERS,
  MARKETS,
  SHED_CAVEAT,
  type FilterState,
  type FluConfig,
  type MarketId,
  type MfPriorityView,
  type OpportunityZoneCollection,
  type OrlandoParcelsMeta,
  type Oz2TractCollection,
  type ParcelCollection,
  type RuralMarketTractCollection,
  type RuralMarketsCatalog,
  type ScMfPriorityCatalog,
  type ZoningConfig,
} from "@/lib/types";

type AppShellProps = {
  parcels: ParcelCollection;
  orlandoParcelsMeta: OrlandoParcelsMeta;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  opportunityZones: OpportunityZoneCollection;
  oz2Tracts: Oz2TractCollection;
  ruralCatalog: RuralMarketsCatalog;
  ruralTracts: RuralMarketTractCollection;
  mfPriority: ScMfPriorityCatalog;
  zoningConfig: ZoningConfig;
  fluConfig: FluConfig;
  meta: Record<string, unknown>;
};

type InventoryTab = "sites" | "tracts";

const EMPTY_PARCELS: ParcelCollection = { type: "FeatureCollection", features: [] };

export function AppShell({
  parcels,
  orlandoParcelsMeta,
  traffic,
  opportunityZones,
  oz2Tracts,
  ruralCatalog,
  ruralTracts,
  mfPriority,
  zoningConfig,
  fluConfig,
  meta,
}: AppShellProps) {
  const [filters, setFilters] = useState<FilterState>({ ...DEFAULT_FILTERS, landUseFilter: "off" });
  const [market, setMarket] = useState<MarketId>("Orlando");
  const [county, setCounty] = useState<string | null>(null);
  const [countyState, setCountyState] = useState<string | null>(null);
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
  const [mfView, setMfView] = useState<MfPriorityView>("all");
  const [viewportParcels, setViewportParcels] = useState<ParcelCollection | null>(null);
  const [viewportStats, setViewportStats] = useState<{ totalInBbox: number; truncated: boolean } | null>(null);
  const [parcelsLoading, setParcelsLoading] = useState(true);
  const [parcelSource, setParcelSource] = useState<"fixture" | "live">("fixture");
  const [error, setError] = useState<string | null>(null);

  const summary = marketSummary(ruralCatalog, market);
  const scView = viewIncludesSouthCarolina(market, countyState);
  const activeMfView: MfPriorityView = scView ? mfView : "all";
  const annotatedRows = useMemo(() => annotateRuralRows(ruralCatalog.rows, mfPriority), [ruralCatalog.rows, mfPriority]);
  const marketTracts = useMemo(
    () => filterRuralRows(annotatedRows, market, county, countyState),
    [annotatedRows, market, county, countyState],
  );
  const visibleTracts = useMemo(
    () => sortTractsForDisplay(filterByMfPriority(marketTracts, activeMfView)),
    [marketTracts, activeMfView],
  );
  const priorityCounts = useMemo(() => countMfPriority(marketTracts), [marketTracts]);
  const highlightTierA = useMemo(
    () => geoidsForHighlight(marketTracts, activeMfView, "A"),
    [marketTracts, activeMfView],
  );
  const highlightTierB = useMemo(
    () => geoidsForHighlight(marketTracts, activeMfView, "B"),
    [marketTracts, activeMfView],
  );
  const restrictGeoids = useMemo(
    () => geoidFilterForView(marketTracts, activeMfView),
    [marketTracts, activeMfView],
  );
  const orlandoParcelsOn = showOrlandoParcels(market, county, countyState);
  const orangePilot = showOrangeCountyPilot(market, county, countyState);
  const statusHelp = southCarolinaStatusHelp(market, countyState);
  const bounds = useMemo(
    () =>
      viewBounds(summary, activeMfView === "all" ? annotatedRows : visibleTracts, county, countyState, {
        fitRows: activeMfView !== "all",
      }),
    [summary, annotatedRows, visibleTracts, county, countyState, activeMfView],
  );
  const boundsKey = `${market}|${countyState ?? ""}|${county ?? ""}|${activeMfView}`;

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
          placeOrCorridor: row.mfPriority?.place ?? row.placeOrCorridor,
          mfTier: row.mfPriority?.tier ?? "",
        },
        geometry: { type: "Point", coordinates: [row.lon, row.lat] },
      })),
    }),
    [visibleTracts],
  );

  const countyParcelFeatures = useMemo(() => {
    if (!orlandoParcelsOn) return EMPTY_PARCELS.features;
    if (!county) return parcels.features;
    const fips = ORLANDO_FIPS_BY_NAME[county];
    if (!fips) return [];
    return parcels.features.filter((feature) => feature.properties.countyFips === fips);
  }, [orlandoParcelsOn, parcels.features, county]);

  const activeParcels = useMemo<ParcelCollection>(() => {
    if (!orlandoParcelsOn) return EMPTY_PARCELS;
    if (viewportParcels) return viewportParcels;
    return { type: "FeatureCollection", features: countyParcelFeatures };
  }, [orlandoParcelsOn, viewportParcels, countyParcelFeatures]);

  const matched = useMemo(
    () => filterParcels(activeParcels.features, filters, zoningConfig, fluConfig),
    [activeParcels.features, filters, zoningConfig, fluConfig],
  );
  const ranked = useMemo(
    () => rankSites(matched, filters, zoningConfig, fluConfig),
    [matched, filters, zoningConfig, fluConfig],
  );
  const rankedVisible = useMemo(() => ranked.slice(0, 200), [ranked]);
  const fullAcreageCounties = useMemo(
    () => orlandoParcelsMeta.counties.filter((item) => item.coverage === "complete-gte-5ac"),
    [orlandoParcelsMeta.counties],
  );
  const fullAcreageParcelCount = useMemo(
    () => fullAcreageCounties.reduce((sum, item) => sum + item.featureCount, 0),
    [fullAcreageCounties],
  );
  const matchedIds = useMemo(() => new Set(matched.map((feature) => feature.properties.id)), [matched]);
  const selected = activeParcels.features.find((feature) => feature.properties.id === selectedId) ?? null;
  const selectedTract = visibleTracts.find((row) => row.geoid === selectedTractGeoid) ?? null;
  const fluUnknownCount = useMemo(
    () => activeParcels.features.filter((feature) => !feature.properties.flu?.code).length,
    [activeParcels.features],
  );
  const fluJoinedCount =
    typeof meta.fluJoinedCount === "number" && orangePilot && county === "Orange"
      ? meta.fluJoinedCount
      : activeParcels.features.length - fluUnknownCount;
  const hint = orlandoParcelsOn ? emptyStateHint(filters, matched.length, fluUnknownCount) : null;

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
    if (!orlandoParcelsOn) {
      setInventoryTab("tracts");
      setViewportParcels(null);
      setParcelsLoading(false);
      return;
    }
    setInventoryTab("sites");
  }, [orlandoParcelsOn]);

  useEffect(() => {
    // Outside Orange, zoning/FLU knowledge is mostly missing — default to all parcels.
    if (orlandoParcelsOn && county && county !== "Orange") {
      setFilters((prev) => (prev.landUseFilter === "zoning" ? { ...prev, landUseFilter: "off" } : prev));
    }
  }, [orlandoParcelsOn, county]);

  const loadViewportParcels = async (bbox: [number, number, number, number], zoom: number) => {
    if (!orlandoParcelsOn) return;
    // Live DOH fill is only for the thinner sample counties. The five core counties
    // already ship every ≥5 acre parcel, and live queries stay at that same cutoff.
    const useLive = zoom >= 11.5 && Boolean(county) && !isFull5AcCounty(county);
    const limit = useLive ? 900 : zoom >= 12 ? 3500 : 5000;
    setParcelsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        market: "Orlando",
        source: useLive ? "live" : "fixture",
        bbox: bbox.join(","),
        limit: String(limit),
      });
      if (county && countyState) {
        params.set("county", county);
        params.set("state", countyState);
      }
      const response = await fetch(`/api/parcels?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`Parcel load failed (${response.status})`);
      }
      const body = (await response.json()) as ParcelCollection & {
        error?: string;
        meta?: { totalInBbox?: number; truncated?: boolean };
      };
      if (body.error) throw new Error(body.error);
      setViewportParcels({ type: "FeatureCollection", features: body.features ?? [] });
      setViewportStats({
        totalInBbox: body.meta?.totalInBbox ?? body.features?.length ?? 0,
        truncated: Boolean(body.meta?.truncated),
      });
      setParcelSource(useLive ? "live" : "fixture");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to refresh parcels");
      setViewportParcels(null);
      setViewportStats(null);
      setParcelSource("fixture");
    } finally {
      setParcelsLoading(false);
    }
  };

  useEffect(() => {
    if (!scView && mfView !== "all") setMfView("all");
  }, [scView, mfView]);

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
    setViewportParcels(null);
    setInventoryTab(next === "Orlando" ? "sites" : "tracts");
  };

  const changeCounty = (key: string) => {
    const parsed = key ? parseCountyKey(key) : null;
    setCounty(parsed?.county ?? null);
    setCountyState(parsed?.state ?? null);
    setSelectedTractGeoid(null);
    setSelectedId(null);
    setViewportParcels(null);
  };

  const showSites = orlandoParcelsOn && inventoryTab === "sites";
  const tractEmptyMessage =
    activeMfView === "all"
      ? "No rural-eligible tracts in this county filter."
      : "No SC multifamily priority tracts in this county. The shortlist is a subset of rural-eligible tracts, not a nomination.";
  const priorityFilter = scView
    ? { priorityView: mfView, priorityCounts, onPriorityView: setMfView }
    : { priorityView: undefined, priorityCounts: undefined, onPriorityView: undefined };
  const countyOptions = useMemo(() => {
    if (market !== "Orlando") return summary.counties;
    // Ensure Seminole appears even with 0 rural tracts.
    const byKey = new Map(summary.counties.map((item) => [countyKey(item.county, item.state), item]));
    for (const shed of ORLANDO_SHED_COUNTIES) {
      const key = countyKey(shed.name, "Florida");
      if (!byKey.has(key)) {
        byKey.set(key, { county: shed.name, state: "Florida", count: 0, outerEdge: false });
      }
    }
    return Array.from(byKey.values()).sort((a, b) => a.county.localeCompare(b.county));
  }, [market, summary.counties]);

  const headerPlace =
    orlandoParcelsOn && county
      ? `${county} County, Florida`
      : orlandoParcelsOn
        ? "Orlando ~90-min shed"
        : market;

  return (
    <div className="flex h-dvh min-h-0 flex-col bg-ink-950 text-ink-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-3 md:px-5">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-clay-400">{headerPlace}</p>
          <h1 className="font-display text-xl tracking-tight text-white md:text-2xl">
            {orlandoParcelsOn ? "Multifamily site search" : "Rural-eligible tracts"}
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
              {countyOptions.map((item) => (
                <option key={countyKey(item.county, item.state)} value={countyKey(item.county, item.state)}>
                  {formatCountyLabel(item.county, item.state)} ({item.count}
                  {item.outerEdge ? ", outer edge" : ""})
                </option>
              ))}
            </select>
          </label>
          <p className="hidden text-right text-xs text-ink-500 sm:block">
            {visibleTracts.length.toLocaleString()}{" "}
            {activeMfView === "all" ? "rural-eligible" : "SC MF priority"}{" "}
            {visibleTracts.length === 1 ? "tract" : "tracts"}
            {orlandoParcelsOn ? (
              <span className="block text-[11px]">
                {matched.length.toLocaleString()} of {activeParcels.features.length.toLocaleString()} in view
                {parcelsLoading ? " · loading…" : ` · ${parcelSource}`}
                {viewportStats?.truncated ? (
                  <span className="block">
                    Showing a spread of this view. {viewportStats.totalInBbox.toLocaleString()} parcels meet the
                    fixture — zoom in for the rest.
                  </span>
                ) : null}
                <span className="block">
                  ≥5 ac fixtures: {fullAcreageParcelCount.toLocaleString()} in{" "}
                  {fullAcreageCounties.map((item) => item.name).join(", ")}
                </span>
              </span>
            ) : (
              <span className="block text-[11px]">Tract overlay and pins · parcels are Orlando-shed only for now</span>
            )}
          </p>
          {orlandoParcelsOn ? (
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
          totalCount={activeParcels.features.length}
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
          orlandoParcels={orlandoParcelsOn}
          market={market}
          tractCount={marketTracts.length}
          parcelNote={ruralCatalog.parcelNote}
          statusHelp={statusHelp}
          priorityView={priorityFilter.priorityView}
          priorityCounts={priorityFilter.priorityCounts}
          onPriorityView={priorityFilter.onPriorityView}
        />
        <main className="relative min-w-0 flex-1">
          <SiteMap
            parcels={activeParcels}
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
            showParcels={orlandoParcelsOn}
            showOrangePilot={orangePilot}
            parcelsLoading={parcelsLoading}
            market={market}
            county={county}
            countyState={countyState}
            bounds={bounds}
            boundsKey={boundsKey}
            ozFilter={filters.ozFilter}
            highlightTierA={highlightTierA}
            highlightTierB={highlightTierB}
            restrictGeoids={restrictGeoids}
            showMfLegend={scView}
            onSelect={selectSite}
            onHover={setHoveredId}
            onSelectTract={selectTract}
            onViewportIdle={orlandoParcelsOn ? loadViewportParcels : undefined}
          />
          <div className="pointer-events-none absolute bottom-3 right-3 top-16 z-10 hidden w-80 xl:block">
            <div className="pointer-events-auto flex h-full min-h-0 flex-col gap-2">
              {orlandoParcelsOn ? (
                <div className="flex gap-1">
                  <button
                    type="button"
                    className={`rounded-full border px-3 py-1 text-xs ${inventoryTab === "sites" ? "border-clay-400/50 bg-ink-800 text-white" : "border-white/10 bg-ink-900/80 text-ink-300"}`}
                    onClick={() => setInventoryTab("sites")}
                  >
                    Shed parcels
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
                    sites={rankedVisible}
                    matchedTotal={ranked.length}
                    selectedId={selectedId}
                    hoveredId={hoveredId}
                    incomeGeography={filters.incomeGeography}
                    landUseFilter={filters.landUseFilter}
                    fluUnknownCount={fluUnknownCount}
                    onSelect={selectSite}
                    onHover={setHoveredId}
                  />
                ) : (
                  <TractPanel
                    tracts={visibleTracts}
                    selectedGeoid={selectedTractGeoid}
                    onSelect={selectTract}
                    priorityView={priorityFilter.priorityView}
                    priorityCounts={priorityFilter.priorityCounts}
                    onPriorityView={priorityFilter.onPriorityView}
                    emptyMessage={tractEmptyMessage}
                  />
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
        {selected ? (
          <ParcelDrawer
            parcel={selected}
            zoningConfig={zoningConfig}
            fluConfig={fluConfig}
            filters={filters}
            onClose={() => setSelectedId(null)}
          />
        ) : (
          <TractDrawer tract={selectedTract} statusHelp={statusHelp} onClose={() => setSelectedTractGeoid(null)} />
        )}
      </div>

      {sitesOpen ? (
        <div className="fixed inset-0 z-40 xl:hidden">
          <button type="button" className="absolute inset-0 bg-black/50" aria-label="Close list" onClick={() => setSitesOpen(false)} />
          <div className="absolute inset-x-0 bottom-0 flex h-[75vh] flex-col rounded-t-3xl border border-white/10 bg-ink-900 shadow-2xl">
            {showSites ? (
              <SitesPanel
                variant="sheet"
                sites={rankedVisible}
                matchedTotal={ranked.length}
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
                priorityView={priorityFilter.priorityView}
                priorityCounts={priorityFilter.priorityCounts}
                onPriorityView={priorityFilter.onPriorityView}
                emptyMessage={tractEmptyMessage}
              />
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
