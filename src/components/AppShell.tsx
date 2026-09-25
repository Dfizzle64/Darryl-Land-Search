"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { FilterSidebar } from "./FilterSidebar";
import { JumpToBar } from "./JumpToBar";
import { OzExplainer } from "./OzExplainer";
import { MarketMenu } from "./MarketMenu";
import { groupMarketsByState } from "@/lib/marketGroups";
import { SouthCarolinaStatusNote } from "./SouthCarolinaStatusNote";
import { ParcelDrawer } from "./ParcelDrawer";
import { SiteMap } from "./SiteMap";
import { SitesPanel } from "./SitesPanel";
import { TractDrawer } from "./TractDrawer";
import { TractPanel } from "./TractPanel";
import { AOI_PARCEL_LIMIT, featuresIntersectingBbox, type AoiLock } from "@/lib/aoi";
import {
  bboxContains,
  parcelAtPoint,
  ADDRESS_NOT_FOUND,
  coordinateError,
  parseLatLng,
  pointInBounds,
  SOUTH_FLORIDA_BOUNDS,
  type MapFlyTarget,
} from "@/lib/jumpTo";
import { appliedParcelFilters, emptyStateHint, filterParcels, parcelFilterKey, stampFilterMatch, writeParcelFilters } from "@/lib/filters";
import {
  isParcelVisibilityPreference,
  parcelVisibilityHint,
  parcelsAreVisible,
  PARCEL_VISIBILITY_STORAGE_KEY,
  shouldQueryParcelsForZoom,
  toggleParcelVisibility,
  type ParcelVisibilityPreference,
} from "@/lib/parcelVisibility";
import {
  catalogForMarket,
  countyKey,
  filterEligibleRows,
  filterRuralRows,
  formatCountyLabel,
  isPrimaryMarket,
  parseCountyKey,
  rowMatchesTractClass,
  showOrangeCountyPilot,
  showOrlandoParcels,
  southCarolinaOverlayMode,
  southCarolinaStatusHelp,
  summarizeCounties,
  viewBounds,
  viewIncludesSouthCarolina,
} from "@/lib/markets";
import { displayedOzTracts } from "@/lib/scNominatedTracts";
import { showMarketParcels, type MarketParcelIndex } from "@/lib/marketParcels";
import { isFull5AcCounty, ORLANDO_FIPS_BY_NAME, ORLANDO_SHED_COUNTIES } from "@/lib/orlandoParcels";
import { rankSites } from "@/lib/score";
import { DEFAULT_SCREENING_TOGGLES, type ScreeningPoint, type ScreeningToggles } from "@/lib/screening";
import { filterTractRowsByIncome, incomeByGeoidFromFeatures } from "@/lib/tractIncome";
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
  SHED_CAVEAT,
  type EligibleMarketsCatalog,
  type EligiblePackTractCollection,
  type EligibleTractRow,
  type FilterState,
  type FluConfig,
  type MfPriorityView,
  type OpportunityZoneCollection,
  type OrlandoParcelsMeta,
  type Oz2TractCollection,
  type ParcelCollection,
  type ParcelFeature,
  type RuralMarketTractCollection,
  type RuralMarketsCatalog,
  type ScMfPriorityCatalog,
  type SearchMarketId,
  type TractClassView,
  type ZoningConfig,
} from "@/lib/types";

type ParcelViewStats = { totalInBbox: number; totalMatching: number; truncated: boolean };

type ParcelResponse = ParcelCollection & {
  error?: string;
  excluded?: ParcelFeature[];
  meta?: { totalInBbox?: number; totalMatching?: number; truncated?: boolean };
};

type AppShellProps = {
  parcels: ParcelCollection;
  orlandoParcelsMeta: OrlandoParcelsMeta;
  marketParcelIndex: MarketParcelIndex;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  opportunityZones: OpportunityZoneCollection;
  oz2Tracts: Oz2TractCollection;
  ruralCatalog: RuralMarketsCatalog;
  ruralTracts: RuralMarketTractCollection;
  urbanCatalog: EligibleMarketsCatalog;
  otherCatalog: EligibleMarketsCatalog;
  eligibleTracts: EligiblePackTractCollection;
  mfPriority: ScMfPriorityCatalog;
  zoningConfig: ZoningConfig;
  fluConfig: FluConfig;
  meta: Record<string, unknown>;
};

type InventoryTab = "sites" | "tracts";

const RANKING_STORAGE_KEY = "dls.rankingExpanded";

const EMPTY_PARCELS: ParcelCollection = { type: "FeatureCollection", features: [] };

export function AppShell({
  parcels,
  orlandoParcelsMeta,
  marketParcelIndex,
  traffic,
  opportunityZones,
  oz2Tracts,
  ruralCatalog,
  ruralTracts,
  urbanCatalog,
  otherCatalog,
  eligibleTracts,
  mfPriority,
  zoningConfig,
  fluConfig,
  meta,
}: AppShellProps) {
  const [filters, setFilters] = useState<FilterState>({ ...DEFAULT_FILTERS, landUseFilter: "off" });
  const marketGroups = useMemo(
    () => groupMarketsByState(ruralCatalog, urbanCatalog, otherCatalog),
    [otherCatalog, ruralCatalog, urbanCatalog],
  );
  const [market, setMarket] = useState<SearchMarketId>("Orlando");
  const [tractClass, setTractClass] = useState<TractClassView>("both");
  const [county, setCounty] = useState<string | null>(null);
  const [countyState, setCountyState] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedTractGeoid, setSelectedTractGeoid] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(false);
  const [showTraffic, setShowTraffic] = useState(true);
  const [showOz, setShowOz] = useState(false);
  const [showOz2, setShowOz2] = useState(true);
  const [screening, setScreening] = useState<ScreeningToggles>(DEFAULT_SCREENING_TOGGLES);
  const [screeningPoint, setScreeningPoint] = useState<ScreeningPoint | null>(null);
  const [screeningStatus, setScreeningStatus] = useState<"idle" | "loading" | "error">("idle");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [sitesOpen, setSitesOpen] = useState(false);
  const [rankingExpanded, setRankingExpanded] = useState(false);
  const [ozHelpOpen, setOzHelpOpen] = useState(false);
  const [inventoryTab, setInventoryTab] = useState<InventoryTab>("sites");
  const [mfView, setMfView] = useState<MfPriorityView>("all");
  const [viewportParcels, setViewportParcels] = useState<ParcelCollection | null>(null);
  const [viewportStats, setViewportStats] = useState<ParcelViewStats | null>(null);
  const [aoi, setAoi] = useState<AoiLock | null>(null);
  const [lockedParcels, setLockedParcels] = useState<ParcelCollection | null>(null);
  const [aoiStats, setAoiStats] = useState<ParcelViewStats | null>(null);
  const [parcelPreference, setParcelPreference] = useState<ParcelVisibilityPreference>("auto");
  const [mapZoom, setMapZoom] = useState(9);
  const aoiRef = useRef(aoi);
  aoiRef.current = aoi;
  const viewportRequest = useRef(0);
  const aoiRequest = useRef(0);
  const [parcelsLoading, setParcelsLoading] = useState(true);
  const [parcelSource, setParcelSource] = useState<"fixture" | "live">("fixture");
  const [error, setError] = useState<string | null>(null);
  const [flyTarget, setFlyTarget] = useState<MapFlyTarget | null>(null);
  const [jumpNote, setJumpNote] = useState<string | null>(null);
  const [jumpError, setJumpError] = useState<string | null>(null);
  const [jumpBusy, setJumpBusy] = useState(false);
  const [parcelLoadStamp, setParcelLoadStamp] = useState(0);
  const [pick, setPick] = useState<{ lng: number; lat: number; key: number; loadStamp: number } | null>(null);

  const primaryMarket = isPrimaryMarket(market);
  // Stable across zoom updates. A fresh object here rebuilds map bounds and fitBounds snaps the camera back.
  const summary = useMemo(
    () => catalogForMarket(ruralCatalog, urbanCatalog, otherCatalog, market),
    [ruralCatalog, urbanCatalog, otherCatalog, market],
  );
  const scView = primaryMarket && viewIncludesSouthCarolina(market, countyState);
  const activeMfView: MfPriorityView = scView && tractClass !== "urban" ? mfView : "all";
  const annotatedRows = useMemo(() => annotateRuralRows(ruralCatalog.rows, mfPriority), [ruralCatalog.rows, mfPriority]);
  const ruralSide = useMemo(() => {
    const rows = !isPrimaryMarket(market)
      ? filterEligibleRows(otherCatalog.rows, market, county, countyState).filter((row) => row.rural === "Y")
      : filterRuralRows(annotatedRows, market, county, countyState);
    return displayedOzTracts(rows);
  }, [annotatedRows, county, countyState, market, otherCatalog.rows]);
  const urbanSide = useMemo(() => {
    const source = isPrimaryMarket(market) ? urbanCatalog.rows : otherCatalog.rows;
    return displayedOzTracts(filterEligibleRows(source, market, county, countyState).filter((row) => row.rural === "N"));
  }, [county, countyState, market, otherCatalog.rows, urbanCatalog.rows]);
  const classRows = useMemo(() => {
    const rows: EligibleTractRow[] = [];
    if (rowMatchesTractClass("Y", tractClass)) rows.push(...ruralSide);
    if (rowMatchesTractClass("N", tractClass)) rows.push(...urbanSide);
    return rows;
  }, [ruralSide, tractClass, urbanSide]);
  const tractIncomeByGeoid = useMemo(
    () => incomeByGeoidFromFeatures([ruralTracts, eligibleTracts, oz2Tracts]),
    [eligibleTracts, oz2Tracts, ruralTracts],
  );
  const ruralShown = useMemo(
    () => filterTractRowsByIncome(ruralSide, tractIncomeByGeoid, filters),
    [filters, ruralSide, tractIncomeByGeoid],
  );
  const urbanShown = useMemo(
    () => filterTractRowsByIncome(urbanSide, tractIncomeByGeoid, filters),
    [filters, tractIncomeByGeoid, urbanSide],
  );
  const classRowsShown = useMemo(() => {
    const rows: EligibleTractRow[] = [];
    if (rowMatchesTractClass("Y", tractClass)) rows.push(...ruralShown);
    if (rowMatchesTractClass("N", tractClass)) rows.push(...urbanShown);
    return rows;
  }, [ruralShown, tractClass, urbanShown]);
  const visibleTracts = useMemo(() => {
    if (activeMfView === "all") return sortTractsForDisplay(classRowsShown);
    return sortTractsForDisplay(filterByMfPriority(ruralShown, activeMfView));
  }, [activeMfView, classRowsShown, ruralShown]);
  const priorityCounts = useMemo(() => countMfPriority(ruralShown), [ruralShown]);
  const highlightTierA = useMemo(
    () => geoidsForHighlight(ruralShown, activeMfView, "A"),
    [ruralShown, activeMfView],
  );
  const highlightTierB = useMemo(
    () => geoidsForHighlight(ruralShown, activeMfView, "B"),
    [ruralShown, activeMfView],
  );
  const restrictGeoids = useMemo(
    () => geoidFilterForView(ruralShown, activeMfView),
    [ruralShown, activeMfView],
  );
  const orlandoParcelsOn = showOrlandoParcels(market, county, countyState);
  const marketParcelsOn = showMarketParcels(market, county, countyState, marketParcelIndex);
  const shedParcelsOn = orlandoParcelsOn || marketParcelsOn;
  const orangePilot = showOrangeCountyPilot(market, county, countyState);
  const parcelLayerVisible = shedParcelsOn && parcelsAreVisible(parcelPreference, mapZoom, Boolean(aoi));
  const visibilityHint = parcelVisibilityHint(parcelPreference, parcelLayerVisible);
  const filterKey = parcelFilterKey(filters);
  const statusHelp = southCarolinaStatusHelp(market, countyState);
  const overlayMode = southCarolinaOverlayMode(market, countyState);
  const bounds = useMemo(
    () =>
      viewBounds(summary, activeMfView === "all" ? classRows : visibleTracts, county, countyState, {
        fitRows: tractClass !== "both" || activeMfView !== "all" || Boolean(county),
      }),
    [summary, classRows, visibleTracts, county, countyState, activeMfView, tractClass],
  );
  const boundsKey = `${market}|${countyState ?? ""}|${county ?? ""}|${activeMfView}|${tractClass}`;

  const ruralPins = useMemo<GeoJSON.FeatureCollection<GeoJSON.Point>>(
    () => ({
      type: "FeatureCollection",
      features: visibleTracts.map((row) => ({
        type: "Feature",
        id: row.geoid,
        properties: {
          tractGeoid: row.geoid,
          rural: row.rural === "Y",
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
    if (!shedParcelsOn) return EMPTY_PARCELS.features;
    if (!county) return parcels.features;
    if (orlandoParcelsOn) {
      const fips = ORLANDO_FIPS_BY_NAME[county];
      if (!fips) return [];
      return parcels.features.filter((feature) => feature.properties.countyFips === fips);
    }
    return parcels.features.filter(
      (feature) => feature.properties.countyName === county && (!countyState || feature.properties.state === countyState),
    );
  }, [county, countyState, orlandoParcelsOn, parcels.features, shedParcelsOn]);

  const activeParcels = useMemo<ParcelCollection>(() => {
    if (!shedParcelsOn) return EMPTY_PARCELS;
    if (aoi) {
      return {
        type: "FeatureCollection",
        features: featuresIntersectingBbox(lockedParcels?.features ?? [], aoi.bbox),
      };
    }
    if (viewportParcels) return viewportParcels;
    return { type: "FeatureCollection", features: countyParcelFeatures };
  }, [shedParcelsOn, aoi, lockedParcels, viewportParcels, countyParcelFeatures]);

  const appliedFilters = useMemo(() => appliedParcelFilters(filters), [filters]);
  const matched = useMemo(
    () => filterParcels(activeParcels.features, appliedFilters, zoningConfig, fluConfig),
    [activeParcels.features, appliedFilters, zoningConfig, fluConfig],
  );
  const ranked = useMemo(
    () => rankSites(matched, appliedFilters, zoningConfig, fluConfig),
    [matched, appliedFilters, zoningConfig, fluConfig],
  );
  const rankedVisible = useMemo(() => ranked.slice(0, 200), [ranked]);
  const mapParcels = useMemo<ParcelCollection>(
    () => ({
      type: "FeatureCollection",
      features: stampFilterMatch(activeParcels.features, appliedFilters, zoningConfig, fluConfig),
    }),
    [activeParcels.features, appliedFilters, zoningConfig, fluConfig],
  );
  const parcelStats = aoi ? aoiStats : viewportStats;
  const filterMatchTotal = parcelStats?.totalMatching ?? matched.length;
  const parcelsInView = parcelStats?.totalInBbox ?? activeParcels.features.length;
  const fullAcreageCounties = useMemo(() => {
    if (market === "Orlando") {
      return orlandoParcelsMeta.counties.filter((item) => item.coverage === "complete-gte-5ac");
    }
    return (marketParcelIndex.markets[market]?.counties ?? []).filter((item) => item.coverage === "complete-gte-5ac");
  }, [market, marketParcelIndex.markets, orlandoParcelsMeta.counties]);
  const fullAcreageParcelCount = useMemo(
    () => fullAcreageCounties.reduce((sum, item) => sum + item.featureCount, 0),
    [fullAcreageCounties],
  );
  const matchedIds = useMemo(() => new Set(matched.map((feature) => feature.properties.id)), [matched]);
  const selected = activeParcels.features.find((feature) => feature.properties.id === selectedId) ?? null;
  const selectedTract = visibleTracts.find((row) => row.geoid === selectedTractGeoid) ?? null;
  const screeningFocus = selected
    ? { key: `parcel:${selected.properties.id}`, lon: selected.properties.centroid[0], lat: selected.properties.centroid[1] }
    : selectedTract
      ? { key: `tract:${selectedTract.geoid}`, lon: selectedTract.lon, lat: selectedTract.lat }
      : null;

  const screeningKey = screeningFocus?.key ?? null;
  const screeningLon = screeningFocus?.lon ?? null;
  const screeningLat = screeningFocus?.lat ?? null;
  const screeningParcelId =
    selected?.properties.countyFips === "13067" || selected?.properties.countyFips === "13089"
      ? selected.properties.parcelId
      : null;
  useEffect(() => {
    if (screeningKey == null || screeningLon == null || screeningLat == null) {
      setScreeningPoint(null);
      setScreeningStatus("idle");
      return;
    }
    const controller = new AbortController();
    setScreeningStatus("loading");
    setScreeningPoint(null);
    const params = new URLSearchParams({ lng: String(screeningLon), lat: String(screeningLat) });
    if (screeningParcelId) params.set("parcelId", screeningParcelId);
    fetch(`/api/screening/point?${params}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("screening failed");
        return (await response.json()) as ScreeningPoint;
      })
      .then((point) => {
        setScreeningPoint(point);
        setScreeningStatus("idle");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setScreeningStatus("error");
      });
    return () => controller.abort();
  }, [screeningKey, screeningLon, screeningLat, screeningParcelId]);
  const fluUnknownCount = useMemo(
    () => activeParcels.features.filter((feature) => !feature.properties.flu?.code).length,
    [activeParcels.features],
  );
  const fluJoinedCount =
    typeof meta.fluJoinedCount === "number" && orangePilot && county === "Orange"
      ? meta.fluJoinedCount
      : activeParcels.features.length - fluUnknownCount;
  const queryingParcels = shouldQueryParcelsForZoom(parcelPreference, mapZoom);
  const hint =
    shedParcelsOn && queryingParcels && !parcelsLoading && parcelStats
      ? emptyStateHint(appliedFilters, filterMatchTotal, fluUnknownCount)
      : null;

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
    if (!shedParcelsOn) {
      setInventoryTab("tracts");
      setViewportParcels(null);
      setViewportStats(null);
      setAoi(null);
      setLockedParcels(null);
      setAoiStats(null);
      setParcelsLoading(false);
      return;
    }
    setInventoryTab("sites");
  }, [shedParcelsOn]);

  useEffect(() => {
    // Outside Orange, zoning/FLU knowledge is mostly missing — default to all parcels.
    if (orlandoParcelsOn && county && county !== "Orange") {
      setFilters((prev) => (prev.landUseFilter === "zoning" ? { ...prev, landUseFilter: "off" } : prev));
    }
  }, [orlandoParcelsOn, county]);

  const filtersRef = useRef(filters);
  filtersRef.current = filters;
  const preferenceRef = useRef(parcelPreference);
  preferenceRef.current = parcelPreference;
  const showExcludedRef = useRef(showExcluded);
  showExcludedRef.current = showExcluded;
  const lastViewport = useRef<{ bbox: [number, number, number, number]; zoom: number } | null>(null);
  const loadViewportRef = useRef<(bbox: [number, number, number, number], zoom: number) => Promise<void>>(
    async () => {},
  );

  const loadViewportParcels = async (bbox: [number, number, number, number], zoom: number) => {
    lastViewport.current = { bbox, zoom };
    if (!shedParcelsOn || aoiRef.current) return;
    // Tract zoom stays unloaded. Once the camera is close enough for parcels,
    // keep querying even if outlines are hidden so the ranked list still filters.
    if (!shouldQueryParcelsForZoom(preferenceRef.current, zoom)) {
      viewportRequest.current += 1;
      setViewportParcels(EMPTY_PARCELS);
      setViewportStats(null);
      setParcelsLoading(false);
      return;
    }
    // Live DOH fill is only for the thinner sample counties, and only once the
    // view is tighter than the neighborhood gate. The complete counties already
    // ship every parcel from 5 through 150 acres.
    const useLive = orlandoParcelsOn && zoom >= 11.5 && Boolean(county) && !isFull5AcCounty(county);
    const limit = useLive ? 900 : zoom >= 13 ? 3500 : zoom >= 11.5 ? 2200 : 1600;
    const requestId = ++viewportRequest.current;
    setParcelsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        market,
        source: useLive ? "live" : "fixture",
        bbox: bbox.join(","),
        limit: String(limit),
      });
      if (county && countyState) {
        params.set("county", county);
        params.set("state", countyState);
      }
      writeParcelFilters(params, filtersRef.current, showExcludedRef.current);
      const response = await fetch(`/api/parcels?${params.toString()}`);
      if (requestId !== viewportRequest.current || aoiRef.current) return;
      if (!response.ok) {
        throw new Error(`Parcel load failed (${response.status})`);
      }
      const body = (await response.json()) as ParcelResponse;
      if (body.error) throw new Error(body.error);
      if (requestId !== viewportRequest.current || aoiRef.current) return;
      const features = featuresIntersectingBbox([...(body.features ?? []), ...(body.excluded ?? [])], bbox);
      setViewportParcels({ type: "FeatureCollection", features });
      setParcelLoadStamp((stamp) => stamp + 1);
      setViewportStats({
        totalInBbox: body.meta?.totalInBbox ?? features.length,
        totalMatching: body.meta?.totalMatching ?? body.features?.length ?? features.length,
        truncated: Boolean(body.meta?.truncated),
      });
      setParcelSource(useLive ? "live" : "fixture");
    } catch (err) {
      if (requestId !== viewportRequest.current || aoiRef.current) return;
      setError(err instanceof Error ? err.message : "Unable to refresh parcels");
      setViewportParcels(null);
      setViewportStats(null);
      setParcelSource("fixture");
    } finally {
      if (requestId === viewportRequest.current && !aoiRef.current) setParcelsLoading(false);
    }
  };
  loadViewportRef.current = loadViewportParcels;

  useEffect(() => {
    const stored = window.sessionStorage.getItem(PARCEL_VISIBILITY_STORAGE_KEY);
    if (isParcelVisibilityPreference(stored)) setParcelPreference(stored);
    if (window.sessionStorage.getItem(RANKING_STORAGE_KEY) === "1") setRankingExpanded(true);
  }, []);

  useEffect(() => {
    if (!shedParcelsOn || aoi) return;
    const last = lastViewport.current;
    if (!last) return;
    const timer = window.setTimeout(() => {
      void loadViewportRef.current(last.bbox, last.zoom);
    }, 280);
    return () => window.clearTimeout(timer);
  }, [filterKey, parcelPreference, showExcluded, shedParcelsOn, orlandoParcelsOn, county, countyState, aoi]);

  useEffect(() => {
    if (!shedParcelsOn || !aoi) {
      aoiRequest.current += 1;
      setLockedParcels(null);
      setAoiStats(null);
      return;
    }
    const requestId = ++aoiRequest.current;
    viewportRequest.current += 1;
    const bbox = aoi.bbox;
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({
        market,
        source: "fixture",
        bbox: bbox.join(","),
        limit: String(AOI_PARCEL_LIMIT),
      });
      if (county && countyState) {
        params.set("county", county);
        params.set("state", countyState);
      }
      writeParcelFilters(params, filters, showExcluded);
      setParcelsLoading(true);
      setError(null);
      void (async () => {
        try {
          const response = await fetch(`/api/parcels?${params.toString()}`);
          if (requestId !== aoiRequest.current) return;
          if (!response.ok) throw new Error(`Parcel load failed (${response.status})`);
          const body = (await response.json()) as ParcelResponse;
          if (body.error) throw new Error(body.error);
          if (requestId !== aoiRequest.current) return;
          const features = featuresIntersectingBbox([...(body.features ?? []), ...(body.excluded ?? [])], bbox);
          setLockedParcels({ type: "FeatureCollection", features });
          setAoiStats({
            totalInBbox: body.meta?.totalInBbox ?? features.length,
            totalMatching: body.meta?.totalMatching ?? body.features?.length ?? features.length,
            truncated: Boolean(body.meta?.truncated),
          });
          setParcelSource("fixture");
        } catch (err) {
          if (requestId !== aoiRequest.current) return;
          setError(err instanceof Error ? err.message : "Unable to load the locked area");
          setLockedParcels({ type: "FeatureCollection", features: [] });
          setAoiStats(null);
        } finally {
          if (requestId === aoiRequest.current) setParcelsLoading(false);
        }
      })();
    }, 280);
    return () => {
      window.clearTimeout(timer);
    };
  }, [aoi, shedParcelsOn, market, county, countyState, filterKey, showExcluded, filters]);

  useEffect(() => {
    if (!scView && mfView !== "all") setMfView("all");
  }, [scView, mfView]);

  const setRankingOpen = (next: boolean) => {
    setRankingExpanded(next);
    window.sessionStorage.setItem(RANKING_STORAGE_KEY, next ? "1" : "0");
  };

  const selectSite = (id: string) => {
    setSelectedId(id);
    setSelectedTractGeoid(null);
    setSitesOpen(false);
    setFiltersOpen(false);
  };

  const jumpToQuery = async (query: string) => {
    setJumpBusy(true);
    setJumpNote(null);
    setJumpError(null);
    try {
      const invalid = coordinateError(query);
      if (invalid) {
        setJumpError(invalid);
        return;
      }
      let point = parseLatLng(query);
      if (!point) {
        const response = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`);
        const body = (await response.json()) as { lng?: number; lat?: number; error?: string };
        if (!response.ok || !Number.isFinite(body.lng) || !Number.isFinite(body.lat)) {
          setJumpError(body.error || ADDRESS_NOT_FOUND);
          return;
        }
        point = { lng: body.lng as number, lat: body.lat as number };
      }
      const pad = 0.03;
      lastViewport.current = {
        bbox: [point.lng - pad, point.lat - pad, point.lng + pad, point.lat + pad],
        zoom: 14,
      };
      const inSouthFlorida = pointInBounds(point.lng, point.lat, SOUTH_FLORIDA_BOUNDS);
      const inCurrent = pointInBounds(point.lng, point.lat, summary.bounds);
      if (!inCurrent && inSouthFlorida && market !== "South Florida") {
        changeMarket("South Florida");
      } else if (county || countyState) {
        setCounty(null);
        setCountyState(null);
        setSelectedId(null);
        setViewportParcels(null);
      }
      const key = Date.now();
      setFlyTarget({ lng: point.lng, lat: point.lat, key });
      setPick({ lng: point.lng, lat: point.lat, key, loadStamp: parcelLoadStamp });
    } catch {
      setJumpError(ADDRESS_NOT_FOUND);
    } finally {
      setJumpBusy(false);
    }
  };

  useEffect(() => {
    if (!pick) return;
    const hit = parcelAtPoint(activeParcels.features, pick.lng, pick.lat);
    if (hit) {
      setSelectedId(hit.properties.id);
      setSelectedTractGeoid(null);
      setJumpNote(null);
      setJumpError(null);
      setPick(null);
      return;
    }
    if (!shedParcelsOn) {
      setJumpNote("Flew to that point.");
      setPick(null);
      return;
    }
    if (parcelsLoading || parcelLoadStamp === pick.loadStamp) return;
    const view = lastViewport.current;
    if (!view || !bboxContains(view.bbox, pick.lng, pick.lat)) return;
    setJumpNote("Flew to that point. No loaded parcel contains it.");
    setPick(null);
  }, [pick, activeParcels.features, parcelsLoading, parcelLoadStamp, shedParcelsOn]);

  const selectTract = (geoid: string | null) => {
    setSelectedTractGeoid(geoid);
    if (!geoid) return;
    setSelectedId(null);
    setSitesOpen(false);
    setFiltersOpen(false);
  };

  const changeMarket = (next: SearchMarketId) => {
    setMarket(next);
    setCounty(null);
    setCountyState(null);
    setSelectedTractGeoid(null);
    setSelectedId(null);
    setViewportParcels(null);
    setViewportStats(null);
    setAoi(null);
    setLockedParcels(null);
    setAoiStats(null);
    const nextParcels =
      showOrlandoParcels(next, null, null) || showMarketParcels(next, null, null, marketParcelIndex);
    setInventoryTab(nextParcels ? "sites" : "tracts");
  };

  const changeCounty = (key: string) => {
    const parsed = key ? parseCountyKey(key) : null;
    setCounty(parsed?.county ?? null);
    setCountyState(parsed?.state ?? null);
    setSelectedTractGeoid(null);
    setSelectedId(null);
    setViewportParcels(null);
  };

  const showSites = shedParcelsOn && inventoryTab === "sites";
  const incomeDroppedTracts =
    filters.incomeGeography === "tract" &&
    (filters.minIncome > 0 || !filters.includeUnknownIncome) &&
    classRowsShown.length < classRows.length;
  const tractNoun = overlayMode === "nominated-only" ? "nominated" : "eligible";
  const tractEmptyMessage = incomeDroppedTracts
    ? `No ${tractNoun} tracts pass the median-income filter. Only Orange County tracts have a joined ACS median income. Tracts without that attribute stay visible when Include unknown income is on.`
    : activeMfView === "all"
      ? tractClass === "urban"
        ? `No urban ${tractNoun} tracts in this county filter.`
        : tractClass === "rural"
          ? `No rural ${tractNoun} tracts in this county filter.`
          : `No ${tractNoun} tracts in this county filter.`
      : "No SC multifamily priority tracts in this county. On the map that shortlist is limited to Governor-nominated tracts, and it is not a nomination list.";
  const priorityFilter = scView && tractClass !== "urban"
    ? { priorityView: mfView, priorityCounts, onPriorityView: setMfView }
    : { priorityView: undefined, priorityCounts: undefined, onPriorityView: undefined };
  const countyOptions = useMemo(() => {
    const counted = summarizeCounties(classRowsShown);
    // Keep shed counties in the menu when the current class or income filter has zero tracts.
    const byKey = new Map(counted.map((item) => [countyKey(item.county, item.state), item]));
    const extras =
      market === "Orlando"
        ? ORLANDO_SHED_COUNTIES.map((shed) => ({ county: shed.name, state: "Florida" }))
        : (marketParcelIndex.markets[market]?.counties ?? []).map((item) => ({ county: item.name, state: item.state }));
    for (const shed of extras) {
      const key = countyKey(shed.county, shed.state);
      if (!byKey.has(key)) {
        byKey.set(key, { county: shed.county, state: shed.state, count: 0, outerEdge: false });
      }
    }
    return Array.from(byKey.values()).sort((a, b) => a.county.localeCompare(b.county) || a.state.localeCompare(b.state));
  }, [classRowsShown, market, marketParcelIndex.markets]);

  const marketCoverage = market === "Orlando" ? null : marketParcelIndex.markets[market];
  const headerPlace =
    shedParcelsOn && county
      ? `${county} County, ${countyState ?? ""}`
      : shedParcelsOn
        ? `${market} ~90-min shed`
        : market;

  return (
    <div className="flex h-dvh min-h-0 flex-col overflow-hidden bg-ink-950 text-ink-100">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-3 md:px-5">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-clay-400">{headerPlace}</p>
          <h1 className="font-display text-xl tracking-tight text-white md:text-2xl">
            {shedParcelsOn ? "Multifamily site search" : overlayMode === "nominated-only" ? "Nominated tracts" : "Eligible tracts"}
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="rounded-full border border-white/20 bg-ink-800 px-3 py-1.5 text-sm text-white"
            onClick={() => setOzHelpOpen(true)}
          >
            How OZ 2.0 works
          </button>
          <JumpToBar busy={jumpBusy} note={jumpNote} error={jumpError} onJump={(query) => void jumpToQuery(query)} />
          <div className="flex items-center gap-1 text-[11px] text-ink-500">
            <span>Market</span>
            <MarketMenu value={market} groups={marketGroups} onChange={changeMarket} />
          </div>
          <label className="text-[11px] text-ink-500">
            County
            <select
              aria-label="County"
              className="ml-1 max-w-[14rem] rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm text-white"
              value={county && countyState ? countyKey(county, countyState) : ""}
              onChange={(event) => changeCounty(event.target.value)}
            >
              <option value="">All counties ({classRowsShown.length})</option>
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
            {activeMfView === "all" ? "eligible" : "SC MF priority"}{" "}
            {visibleTracts.length === 1 ? "tract" : "tracts"}
            <span className="block text-[11px]">
              {ruralShown.length.toLocaleString()} rural · {urbanShown.length.toLocaleString()} urban
            </span>
            {shedParcelsOn ? (
              <span className="block text-[11px]">
                {filterMatchTotal.toLocaleString()} match
                {parcelsInView > 0 ? ` of ${parcelsInView.toLocaleString()}` : ""} {aoi ? "in AOI" : "in view"}
                {parcelsLoading ? " · loading…" : aoi ? " · locked" : parcelLayerVisible ? ` · ${parcelSource}` : " · parcels off"}
                {aoi && aoiStats?.truncated ? (
                  <span className="block">
                    {aoiStats.totalMatching.toLocaleString()} parcels match these filters inside the AOI (
                    {aoiStats.totalInBbox.toLocaleString()} in the boundary). The list is a stable spread — draw a
                    smaller area for the rest.
                  </span>
                ) : null}
                {!aoi && viewportStats?.truncated ? (
                  <span className="block">
                    Showing a spread of parcels that match these filters (
                    {viewportStats.totalMatching.toLocaleString()} match, {viewportStats.totalInBbox.toLocaleString()}{" "}
                    in the view). Zoom in for the rest.
                  </span>
                ) : null}
                <span className="block">
                  5–150 ac fixtures: {fullAcreageParcelCount.toLocaleString()} in{" "}
                  {fullAcreageCounties.map((item) => item.name).join(", ")}
                </span>
              </span>
              ) : (
              <span className="block text-[11px]">
                {marketCoverage
                  ? `Tract overlay · no 5–150 acre polygons in this pull (${marketCoverage.gapCountyCount} counties documented)`
                  : "Tract overlay · parcels stay on the Orlando shed"}
              </span>
            )}
          </p>
          {shedParcelsOn ? (
            <button
              type="button"
              className="rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm lg:hidden"
              onClick={() => {
                setInventoryTab("sites");
                setSitesOpen(true);
              }}
            >
              Sites ({filterMatchTotal.toLocaleString()})
            </button>
          ) : null}
          <button
            type="button"
            className="rounded-full border border-white/15 bg-ink-800 px-3 py-1.5 text-sm lg:hidden"
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

      <div className="flex min-h-0 flex-1 flex-nowrap">
        <FilterSidebar
          filters={filters}
          onChange={setFilters}
          zoningConfig={zoningConfig}
          fluConfig={fluConfig}
          matchedCount={filterMatchTotal}
          totalCount={parcelsInView}
          fluJoinedCount={fluJoinedCount}
          showExcluded={showExcluded}
          onShowExcluded={setShowExcluded}
          showTraffic={showTraffic}
          onShowTraffic={setShowTraffic}
          showOz={showOz}
          onShowOz={setShowOz}
          showOz2={showOz2}
          onShowOz2={setShowOz2}
          screening={screening}
          onScreening={(key, value) => setScreening((current) => ({ ...current, [key]: value }))}
          open={filtersOpen}
          onClose={() => setFiltersOpen(false)}
          meta={meta}
          orangePilot={orangePilot}
          orlandoParcels={shedParcelsOn}
          parcelCoverageNote={
            marketCoverage
              ? `${marketCoverage.parcelCount.toLocaleString()} parcels in the 5–150 acre band · ${marketCoverage.completeCountyCount} complete counties · ${marketCoverage.sampleCountyCount} sample · ${marketCoverage.gapCountyCount} not pulled`
              : null
          }
          market={market}
          county={county}
          countyState={countyState}
          marketStates={[...new Set(summary.counties.map((item) => item.state))]}
          tractCount={classRowsShown.length}
          ruralTractCount={ruralShown.length}
          urbanTractCount={urbanShown.length}
          parcelNote={ruralCatalog.parcelNote}
          statusHelp={statusHelp}
          priorityView={priorityFilter.priorityView}
          priorityCounts={priorityFilter.priorityCounts}
          onPriorityView={priorityFilter.onPriorityView}
        />
        <main className="relative min-w-0 flex-1">
          <SiteMap
            parcels={mapParcels}
            traffic={traffic}
            opportunityZones={opportunityZones}
            oz2Tracts={oz2Tracts}
            ruralTracts={ruralTracts}
            eligibleTracts={eligibleTracts}
            ruralPins={ruralPins}
            selectedId={selectedId}
            hoveredId={hoveredId}
            selectedTractGeoid={selectedTractGeoid}
            showExcluded={showExcluded}
            showTraffic={showTraffic}
            showOz={showOz}
            showOz2={showOz2}
            onToggleTractOverlay={() => setShowOz2((current) => !current)}
            screening={screening}
            showParcels={shedParcelsOn}
            parcelLayerVisible={parcelLayerVisible}
            parcelVisibilityHint={visibilityHint}
            onToggleParcelLayer={
              shedParcelsOn
                ? () => {
                    const next = toggleParcelVisibility(parcelPreference, mapZoom, Boolean(aoi));
                    setParcelPreference(next);
                    window.sessionStorage.setItem(PARCEL_VISIBILITY_STORAGE_KEY, next);
                  }
                : undefined
            }
            showOrangePilot={orangePilot}
            parcelsLoading={parcelsLoading}
            market={market}
            tractClass={tractClass}
            onTractClass={setTractClass}
            county={county}
            countyState={countyState}
            marketStates={[...new Set(summary.counties.map((item) => item.state))]}
            bounds={bounds}
            boundsKey={boundsKey}
            ozFilter={appliedFilters.ozFilter}
            minIncome={filters.minIncome}
            includeUnknownIncome={filters.includeUnknownIncome}
            incomeGeography={filters.incomeGeography}
            highlightTierA={highlightTierA}
            highlightTierB={highlightTierB}
            restrictGeoids={restrictGeoids}
            showMfLegend={scView}
            onSelect={selectSite}
            onHover={setHoveredId}
            onSelectTract={selectTract}
            flyTo={flyTarget}
            onViewportIdle={shedParcelsOn ? loadViewportParcels : undefined}
            onZoom={setMapZoom}
            aoi={shedParcelsOn ? aoi : null}
            aoiMatchedCount={filterMatchTotal}
            aoiTruncated={Boolean(aoiStats?.truncated)}
            onAoiChange={setAoi}
          />
          {hint && showSites ? (
            <div className="pointer-events-none absolute inset-x-0 top-4 flex justify-center px-4">
              <div className="pointer-events-none max-w-md rounded-2xl border border-white/10 bg-ink-900/95 px-4 py-3 text-sm shadow-2xl">
                <p className="font-medium text-white">No parcels match these filters</p>
                <p className="mt-1 text-ink-300">{hint}</p>
              </div>
            </div>
          ) : null}
          <button
            type="button"
            data-ranking-toggle
            aria-expanded={sitesOpen}
            aria-label="Show ranked sites"
            className="absolute right-0 top-1/2 z-30 flex h-14 w-7 -translate-y-1/2 items-center justify-center rounded-l-lg border border-r-0 border-white/20 bg-ink-900 text-lg text-white shadow-[0_8px_24px_rgba(0,0,0,0.45)] hover:bg-ink-800 lg:hidden"
            onClick={() => {
              setInventoryTab(shedParcelsOn ? "sites" : "tracts");
              setSitesOpen(true);
            }}
          >
            <span aria-hidden="true">‹</span>
          </button>
        </main>
        <aside
          id="ranked-sites-panel"
          data-ranking-panel
          className={`${rankingExpanded ? "lg:flex" : ""} hidden min-h-0 w-[22rem] shrink-0 flex-col border-l border-white/10 bg-ink-900`}
        >
          <div className="shrink-0 border-b border-white/10 px-3 py-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-[11px] uppercase tracking-[0.16em] text-clay-400">
                  {showSites ? "Ranked sites" : overlayMode === "nominated-only" ? "Nominated tracts" : "Eligible tracts"}
                </p>
                <p className="text-sm text-white">
                  {showSites
                    ? `${filterMatchTotal.toLocaleString()} matching parcels`
                    : `${visibleTracts.length.toLocaleString()} tracts`}
                </p>
              </div>
              <button
                type="button"
                className="rounded-full border border-white/20 bg-ink-800 px-3 py-1 text-sm text-white"
                aria-label="Hide ranked sites"
                onClick={() => setRankingOpen(false)}
              >
                ›
              </button>
            </div>
            {shedParcelsOn ? (
              <div className="mt-2 flex gap-1">
                <button
                  type="button"
                  className={`rounded-full border px-3 py-1 text-xs ${inventoryTab === "sites" ? "border-clay-400/50 bg-ink-800 text-white" : "border-white/10 text-ink-300"}`}
                  onClick={() => setInventoryTab("sites")}
                >
                  Shed parcels
                </button>
                <button
                  type="button"
                  className={`rounded-full border px-3 py-1 text-xs ${inventoryTab === "tracts" ? "border-clay-400/50 bg-ink-800 text-white" : "border-white/10 text-ink-300"}`}
                  onClick={() => setInventoryTab("tracts")}
                >
                  {overlayMode === "nominated-only" ? "Nominated tracts" : "Eligible tracts"}
                </button>
              </div>
            ) : null}
          </div>
          <div className="min-h-0 flex-1">
            {showSites ? (
              <SitesPanel
                variant="sheet"
                sites={rankedVisible}
                matchedTotal={filterMatchTotal}
                selectedId={selectedId}
                hoveredId={hoveredId}
                incomeGeography={filters.incomeGeography}
                landUseFilter={appliedFilters.landUseFilter}
                fluUnknownCount={fluUnknownCount}
                onSelect={selectSite}
                onHover={setHoveredId}
                onCollapse={() => setRankingOpen(false)}
              />
            ) : (
              <TractPanel
                variant="sheet"
                tracts={visibleTracts}
                selectedGeoid={selectedTractGeoid}
                onSelect={selectTract}
                onCollapse={() => setRankingOpen(false)}
                priorityView={priorityFilter.priorityView}
                priorityCounts={priorityFilter.priorityCounts}
                onPriorityView={priorityFilter.onPriorityView}
                emptyMessage={tractEmptyMessage}
                overlayMode={overlayMode}
              />
            )}
          </div>
        </aside>
        <aside
          data-selection-panel
          className="relative hidden min-h-0 w-[24rem] shrink-0 flex-col border-l border-white/10 bg-ink-900 lg:flex"
        >
          <button
            type="button"
            data-ranking-toggle
            aria-expanded={rankingExpanded}
            aria-controls="ranked-sites-panel"
            aria-label={rankingExpanded ? "Hide ranked sites" : "Show ranked sites"}
            className="absolute left-0 top-1/2 z-30 hidden h-14 w-7 -translate-x-full -translate-y-1/2 items-center justify-center rounded-l-lg border border-r-0 border-white/20 bg-ink-900 text-lg text-white shadow-[0_8px_24px_rgba(0,0,0,0.45)] hover:bg-ink-800 lg:flex"
            onClick={() => setRankingOpen(!rankingExpanded)}
          >
            <span aria-hidden="true">{rankingExpanded ? "›" : "‹"}</span>
          </button>
          <div className="min-h-0 flex-1 overflow-hidden">
            {selected ? (
              <ParcelDrawer
                layout="pane"
                parcel={selected}
                zoningConfig={zoningConfig}
                fluConfig={fluConfig}
                filters={appliedFilters}
                screeningPoint={screeningPoint}
                screeningStatus={screeningStatus}
                onClose={() => setSelectedId(null)}
              />
            ) : (
              <TractDrawer
                layout="pane"
                tract={selectedTract}
                statusHelp={statusHelp}
                overlayMode={overlayMode}
                screeningPoint={screeningPoint}
                screeningStatus={screeningStatus}
                onClose={() => setSelectedTractGeoid(null)}
              />
            )}
          </div>
        </aside>
        <div className="lg:hidden">
          {selected ? (
            <ParcelDrawer
              parcel={selected}
              zoningConfig={zoningConfig}
              fluConfig={fluConfig}
              filters={appliedFilters}
              screeningPoint={screeningPoint}
              screeningStatus={screeningStatus}
              onClose={() => setSelectedId(null)}
            />
          ) : (
            <TractDrawer
              tract={selectedTract}
              statusHelp={statusHelp}
              overlayMode={overlayMode}
              screeningPoint={screeningPoint}
              screeningStatus={screeningStatus}
              onClose={() => setSelectedTractGeoid(null)}
            />
          )}
        </div>
      </div>

      {sitesOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button type="button" className="absolute inset-0 bg-black/50" aria-label="Close list" onClick={() => setSitesOpen(false)} />
          <div className="absolute inset-x-0 bottom-0 flex h-[75vh] flex-col rounded-t-3xl border border-white/10 bg-ink-900 shadow-2xl">
            {showSites ? (
              <SitesPanel
                variant="sheet"
                sites={rankedVisible}
                matchedTotal={filterMatchTotal}
                selectedId={selectedId}
                hoveredId={hoveredId}
                incomeGeography={filters.incomeGeography}
                landUseFilter={appliedFilters.landUseFilter}
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
                overlayMode={overlayMode}
              />
            )}
          </div>
        </div>
      ) : null}
      <OzExplainer open={ozHelpOpen} onClose={() => setOzHelpOpen(false)} />
    </div>
  );
}
