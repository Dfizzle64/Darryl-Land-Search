"use client";

import maplibregl, { type GeoJSONSource, type Map as MapLibreMap, type MapMouseEvent, type MapTouchEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./mapPopup.css";
import { useEffect, useRef, useState } from "react";
import { aoiFeatureCollection, normalizeBbox, type AoiLock } from "@/lib/aoi";
import { screeningLegendLine } from "@/lib/screeningLayerHelp";
import { applyMapGestures } from "@/lib/mapGestures";
import { BasemapToggle } from "./BasemapToggle";
import { AoiControls } from "./AoiControls";
import { MeasureControl } from "./MeasureControl";
import { ParcelLayerToggle } from "./ParcelLayerToggle";
import {
  STREET_STYLE_CANDIDATES,
  addSatelliteSourceAndLayer,
  applyBasemap,
  excludedFillPaint,
  excludedLinePaint,
  MF_PRIORITY_SWATCH,
  OZ_TRACT_SWATCH,
  mfPriorityFillPaint,
  mfPriorityLinePaint,
  eligiblePackFillPaint,
  eligiblePackLinePaint,
  oz2FillPaint,
  oz2LinePaint,
  ozFillPaint,
  ozLinePaint,
  parcelExcludedFilter,
  parcelFillPaint,
  parcelHiddenFilter,
  parcelLinePaint,
  parcelMatchFilter,
  trafficLinePaint,
  type BasemapMode,
} from "@/lib/basemap";
import {
  MEASURE_CASING_COLOR,
  MEASURE_LINE_COLOR,
  appendMeasurePoint,
  measureFeatureCollection,
  type LngLat,
} from "@/lib/measure";
import { formatUsd } from "@/lib/format";
import {
  absorbEligibleTractTiles,
  createEligibleTractTileCache,
  detailTractsVisibleAtZoom,
  eligibleOverviewFilter,
  eligibleTractOverlayFilter,
  syncEligibleTractTileCache,
  TRACT_DETAIL_MIN_ZOOM,
  TRACT_MIN_ZOOM,
  TRACT_VIEWPORT_DEBOUNCE_MS,
  tractGridKeysForBbox,
  type EligibleTractTileCache,
} from "@/lib/censusTracts";
import { MAP_SCALE } from "@/lib/mapScale";
import { eligibleClassCut, southCarolinaOverlayMode } from "@/lib/markets";
import { PARCEL_MIN_ZOOM } from "@/lib/parcelVisibility";
import { scNominatedOverlayFilter, showOzTractInScMarkets } from "@/lib/scNominatedTracts";
import {
  arcgisExportTileUrl,
  CCSD_ZONE_MAP,
  CMS_ELEM_MAP,
  CMS_HIGH_MAP,
  CMS_MIDDLE_MAP,
  FEMA_FLOOD_LAYER,
  FEMA_NFHL_SERVICE,
  FEMA_SOURCE,
  NWI_SERVICE,
  NWI_SOURCE,
  ORANGE_MIDDLE_MAP,
  ORANGE_OPEN_DATA,
  type ScreeningToggles,
} from "@/lib/screening";
import { type MapFlyTarget } from "@/lib/jumpTo";
import { tractClickFromFeature, tractPopupRuralLine, type TractClickDetails } from "@/lib/tractCounty";
import { tractIncomeFilterActive, tractIncomeLayerFilter } from "@/lib/tractIncome";
import { ORANGE_COUNTY_CENTER, MF_PRIORITY_LEGEND_BLURB, MF_PRIORITY_TIER_A_MEANING, MF_PRIORITY_TIER_B_MEANING, RURAL_ELIGIBLE_LEGEND_BLURB, SC_NOMINATED_RURAL_LEGEND_BLURB, SC_NOMINATED_URBAN_LEGEND_BLURB, URBAN_ELIGIBLE_LEGEND_BLURB, type EligiblePackTractCollection, type IncomeGeography, type OpportunityZoneCollection, type Oz2TractCollection, type OzFilter, type ParcelCollection, type RuralMarketTractCollection, type SearchMarketId, type TractClassView } from "@/lib/types";

type LngLatBounds = [[number, number], [number, number]];

type SiteMapProps = {
  parcels: ParcelCollection;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  opportunityZones: OpportunityZoneCollection;
  oz2Tracts: Oz2TractCollection;
  ruralTracts: RuralMarketTractCollection;
  eligibleOverview: GeoJSON.FeatureCollection;
  eligibleTracts: EligiblePackTractCollection;
  ruralPins: GeoJSON.FeatureCollection<GeoJSON.Point>;
  selectedId: string | null;
  hoveredId: string | null;
  selectedTractGeoid: string | null;
  showExcluded: boolean;
  showTraffic: boolean;
  showOz: boolean;
  showOz2: boolean;
  screening: ScreeningToggles;
  showParcels: boolean;
  parcelLayerVisible?: boolean;
  parcelVisibilityHint?: string;
  onToggleParcelLayer?: () => void;
  onToggleTractOverlay?: () => void;
  showOrangePilot: boolean;
  parcelsLoading?: boolean;
  market: SearchMarketId;
  tractClass: TractClassView;
  onTractClass: (view: TractClassView) => void;
  county: string | null;
  countyState: string | null;
  marketStates: string[];
  bounds: LngLatBounds;
  boundsKey: string;
  ozFilter: OzFilter;
  minIncome: number;
  includeUnknownIncome: boolean;
  incomeGeography: IncomeGeography;
  highlightTierA: string[];
  highlightTierB: string[];
  restrictGeoids: string[] | null;
  showMfLegend: boolean;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  onSelectTract: (geoid: string | null) => void;
  flyTo?: MapFlyTarget | null;
  onViewportIdle?: (bbox: [number, number, number, number], zoom: number) => void;
  onZoom?: (zoom: number) => void;
  aoi?: AoiLock | null;
  aoiMatchedCount?: number;
  aoiTruncated?: boolean;
  onAoiChange?: (aoi: AoiLock | null) => void;
};

function queryRendered(map: MapLibreMap, point: maplibregl.PointLike, layers: string[]) {
  const present = layers.filter((layerId) => map.getLayer(layerId));
  if (present.length === 0) return [];
  return map.queryRenderedFeatures(point, { layers: present });
}

function setFilterSafe(map: MapLibreMap, layerId: string, filter: maplibregl.FilterSpecification | null) {
  if (!map.getLayer(layerId)) return;
  map.setFilter(layerId, filter);
}

function setVisibilitySafe(map: MapLibreMap, layerId: string, visibility: "visible" | "none") {
  if (!map.getLayer(layerId)) return;
  map.setLayoutProperty(layerId, "visibility", visibility);
}

function andFilter(
  base: maplibregl.FilterSpecification | null,
  extra: maplibregl.FilterSpecification | null,
): maplibregl.FilterSpecification | null {
  if (!extra) return base;
  if (!base) return extra;
  return ["all", base, extra] as maplibregl.FilterSpecification;
}

function tractOverlayFilter(
  hideOrangeCounty: boolean,
  geoids: string[] | null = null,
  classCut: "all" | "rural" | "urban" | "none" = "all",
): maplibregl.FilterSpecification {
  return eligibleTractOverlayFilter({
    hideOrangeCounty,
    geoids,
    classCut,
  }) as maplibregl.FilterSpecification;
}

const EMPTY_COLLECTION: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

function utilityPaint(color: string, mode: BasemapMode) {
  return {
    fill: { "fill-color": color, "fill-opacity": mode === "satellite" ? 0.28 : 0.22 },
    line: { "line-color": color, "line-width": 1.25, "line-opacity": 0.9 },
  };
}

function addScreeningLayers(map: MapLibreMap, mode: BasemapMode) {
  map.addSource("flood-raster", {
    type: "raster",
    tiles: [arcgisExportTileUrl(FEMA_NFHL_SERVICE, FEMA_FLOOD_LAYER)],
    tileSize: 256,
    attribution: FEMA_SOURCE,
  });
  map.addLayer({
    id: "flood-raster",
    type: "raster",
    source: "flood-raster",
    minzoom: 8,
    layout: { visibility: "none" },
    paint: { "raster-opacity": 0.55 },
  });
  map.addSource("wetlands-raster", {
    type: "raster",
    tiles: [arcgisExportTileUrl(NWI_SERVICE, "0")],
    tileSize: 256,
    attribution: NWI_SOURCE,
  });
  map.addLayer({
    id: "wetlands-raster",
    type: "raster",
    source: "wetlands-raster",
    minzoom: 11,
    layout: { visibility: "none" },
    paint: { "raster-opacity": 0.62 },
  });
  map.addSource("school-zone-raster", {
    type: "raster",
    tiles: [arcgisExportTileUrl(ORANGE_OPEN_DATA, "90,91")],
    tileSize: 256,
    attribution: "Orange County Public Schools attendance zones",
  });
  map.addLayer({
    id: "school-zone-raster",
    type: "raster",
    source: "school-zone-raster",
    minzoom: 9,
    layout: { visibility: "none" },
    paint: { "raster-opacity": 0.45 },
  });
  map.addSource("school-ms-raster", {
    type: "raster",
    tiles: [arcgisExportTileUrl(ORANGE_MIDDLE_MAP, "66")],
    tileSize: 256,
    attribution: "Orange County middle school attendance zones",
  });
  map.addLayer({
    id: "school-ms-raster",
    type: "raster",
    source: "school-ms-raster",
    minzoom: 9,
    layout: { visibility: "none" },
    paint: { "raster-opacity": 0.35 },
  });
  const cmsZones = [
    ["school-cms-es-raster", CMS_ELEM_MAP, "Charlotte-Mecklenburg elementary attendance zones"],
    ["school-cms-ms-raster", CMS_MIDDLE_MAP, "Charlotte-Mecklenburg middle attendance zones"],
    ["school-cms-hs-raster", CMS_HIGH_MAP, "Charlotte-Mecklenburg high school attendance zones"],
  ] as const;
  for (const [id, service, attribution] of cmsZones) {
    map.addSource(id, {
      type: "raster",
      tiles: [arcgisExportTileUrl(service, "0")],
      tileSize: 256,
      attribution,
    });
    map.addLayer({
      id,
      type: "raster",
      source: id,
      minzoom: 9,
      layout: { visibility: "none" },
      paint: { "raster-opacity": 0.4 },
    });
  }
  map.addSource("school-ccsd-raster", {
    type: "raster",
    tiles: [arcgisExportTileUrl(CCSD_ZONE_MAP, "0,1,2")],
    tileSize: 256,
    attribution: "Cobb County School District attendance zones",
  });
  map.addLayer({
    id: "school-ccsd-raster",
    type: "raster",
    source: "school-ccsd-raster",
    minzoom: 9,
    layout: { visibility: "none" },
    paint: { "raster-opacity": 0.4 },
  });
  const utilities = [
    ["water", "#3d7dff"],
    ["sewer", "#7a5cff"],
    ["power", "#e0b15a"],
  ] as const;
  map.addSource("dcsd-zones", { type: "geojson", data: EMPTY_COLLECTION });
  map.addLayer({
    id: "dcsd-zones-fill",
    type: "fill",
    source: "dcsd-zones",
    layout: { visibility: "none" },
    paint: {
      "fill-color": ["match", ["get", "level"], "Elementary", "#1f7a4d", "Middle", "#3d7dff", "High", "#c4473a", "#1f7a4d"],
      "fill-opacity": mode === "satellite" ? 0.22 : 0.16,
    },
  });
  map.addLayer({
    id: "dcsd-zones-line",
    type: "line",
    source: "dcsd-zones",
    layout: { visibility: "none" },
    paint: {
      "line-color": ["match", ["get", "level"], "Elementary", "#1f7a4d", "Middle", "#3d7dff", "High", "#c4473a", "#1f7a4d"],
      "line-width": 1.25,
      "line-opacity": 0.9,
    },
  });
  for (const [kind, color] of utilities) {
    const paint = utilityPaint(color, mode);
    map.addSource(kind, { type: "geojson", data: EMPTY_COLLECTION });
    map.addLayer({
      id: `${kind}-fill`,
      type: "fill",
      source: kind,
      layout: { visibility: "none" },
      paint: paint.fill,
    });
    map.addLayer({
      id: `${kind}-line`,
      type: "line",
      source: kind,
      layout: { visibility: "none" },
      paint: paint.line,
    });
  }
}

function addOverlayLayers(
  map: MapLibreMap,
  parcels: ParcelCollection,
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>,
  opportunityZones: OpportunityZoneCollection,
  eligibleOverview: GeoJSON.FeatureCollection,
  ruralPins: GeoJSON.FeatureCollection<GeoJSON.Point>,
  mode: BasemapMode,
) {
  addScreeningLayers(map, mode);
  map.addSource("eligible-overview", {
    type: "geojson",
    data: eligibleOverview,
    maxzoom: TRACT_DETAIL_MIN_ZOOM,
    attribution: "OZ 2.0 eligible tracts (simplified)",
  });
  map.addLayer({
    id: "eligible-overview-fill",
    type: "fill",
    source: "eligible-overview",
    minzoom: TRACT_MIN_ZOOM,
    maxzoom: TRACT_DETAIL_MIN_ZOOM,
    paint: oz2FillPaint(mode),
  });
  map.addLayer({
    id: "eligible-overview-line",
    type: "line",
    source: "eligible-overview",
    minzoom: TRACT_MIN_ZOOM,
    maxzoom: TRACT_DETAIL_MIN_ZOOM,
    paint: oz2LinePaint(mode),
  });
  // Detail geometry is merged by viewport tile. Sources stay put; setData grows them.
  map.addSource("rural-tracts", {
    type: "geojson",
    data: EMPTY_COLLECTION,
    promoteId: "tractGeoid",
  });
  map.addSource("eligible-tracts", {
    type: "geojson",
    data: EMPTY_COLLECTION,
    promoteId: "tractGeoid",
  });
  map.addSource("rural-pins", { type: "geojson", data: ruralPins, promoteId: "tractGeoid" });
  map.addSource("oz2-tracts", {
    type: "geojson",
    data: EMPTY_COLLECTION,
    promoteId: "tractGeoid",
  });
  map.addSource("opportunity-zones", { type: "geojson", data: opportunityZones });
  map.addSource("parcels", { type: "geojson", data: parcels, promoteId: "id" });
  map.addSource("traffic", { type: "geojson", data: traffic });

  map.addLayer({
    id: "rural-fill",
    type: "fill",
    source: "rural-tracts",
    paint: oz2FillPaint(mode),
  });
  map.addLayer({
    id: "rural-line",
    type: "line",
    source: "rural-tracts",
    paint: oz2LinePaint(mode),
  });
  map.addLayer({
    id: "eligible-fill",
    type: "fill",
    source: "eligible-tracts",
    paint: eligiblePackFillPaint(mode),
  });
  map.addLayer({
    id: "eligible-line",
    type: "line",
    source: "eligible-tracts",
    paint: eligiblePackLinePaint(mode),
  });
  map.addLayer({
    id: "mf-priority-a-fill",
    type: "fill",
    source: "rural-tracts",
    paint: mfPriorityFillPaint(mode, "A"),
  });
  map.addLayer({
    id: "mf-priority-a-line",
    type: "line",
    source: "rural-tracts",
    paint: mfPriorityLinePaint(mode, "A"),
  });
  map.addLayer({
    id: "mf-priority-b-fill",
    type: "fill",
    source: "rural-tracts",
    paint: mfPriorityFillPaint(mode, "B"),
  });
  map.addLayer({
    id: "mf-priority-b-line",
    type: "line",
    source: "rural-tracts",
    paint: mfPriorityLinePaint(mode, "B"),
  });
  map.addLayer({
    id: "oz2-fill",
    type: "fill",
    source: "oz2-tracts",
    paint: oz2FillPaint(mode),
  });
  map.addLayer({
    id: "oz2-line",
    type: "line",
    source: "oz2-tracts",
    paint: oz2LinePaint(mode),
  });
  map.addLayer({
    id: "oz-fill",
    type: "fill",
    source: "opportunity-zones",
    layout: { visibility: "none" },
    paint: ozFillPaint(mode),
  });
  map.addLayer({
    id: "oz-line",
    type: "line",
    source: "opportunity-zones",
    layout: { visibility: "none" },
    paint: ozLinePaint(mode),
  });
  map.addLayer({
    id: "traffic-line",
    type: "line",
    source: "traffic",
    paint: trafficLinePaint(mode),
  });
  map.addLayer({
    id: "parcels-fill-excluded",
    type: "fill",
    source: "parcels",
    paint: excludedFillPaint(mode),
  });
  map.addLayer({
    id: "parcels-line-excluded",
    type: "line",
    source: "parcels",
    paint: excludedLinePaint(mode),
  });
  map.addLayer({
    id: "parcels-fill",
    type: "fill",
    source: "parcels",
    paint: parcelFillPaint(mode),
  });
  map.addLayer({
    id: "parcels-line",
    type: "line",
    source: "parcels",
    paint: parcelLinePaint(mode),
  });
  map.addSource("schools", { type: "geojson", data: EMPTY_COLLECTION });
  map.addLayer({
    id: "schools-circle",
    type: "circle",
    source: "schools",
    layout: { visibility: "none" },
    paint: {
      "circle-radius": 6,
      "circle-stroke-width": 1.25,
      "circle-stroke-color": "#ffffff",
      "circle-color": [
        "match",
        ["upcase", ["coalesce", ["get", "rating"], ""]],
        "A",
        "#1f7a4d",
        "B",
        "#3f9d74",
        "C",
        "#e0b15a",
        "D",
        "#d4783a",
        "F",
        "#c4473a",
        "#8b97a3",
      ],
    },
  });
  map.addSource("aoi", { type: "geojson", data: aoiFeatureCollection(null) });
  map.addLayer({
    id: "aoi-fill",
    type: "fill",
    source: "aoi",
    paint: { "fill-color": "#e7b07a", "fill-opacity": 0.1 },
  });
  map.addLayer({
    id: "aoi-line",
    type: "line",
    source: "aoi",
    paint: {
      "line-color": "#f0c27a",
      "line-width": 2.25,
      "line-dasharray": [1.5, 1],
    },
  });
  map.addSource("measure", { type: "geojson", data: measureFeatureCollection([]) });
  map.addLayer({
    id: "measure-casing",
    type: "line",
    source: "measure",
    filter: ["==", ["get", "kind"], "line"],
    paint: { "line-color": MEASURE_CASING_COLOR, "line-width": 6, "line-opacity": 0.95 },
  });
  map.addLayer({
    id: "measure-line",
    type: "line",
    source: "measure",
    filter: ["==", ["get", "kind"], "line"],
    paint: { "line-color": MEASURE_LINE_COLOR, "line-width": 3, "line-opacity": 1 },
  });
  map.addLayer({
    id: "measure-vertices",
    type: "circle",
    source: "measure",
    filter: ["==", ["get", "kind"], "vertex"],
    paint: {
      "circle-radius": 5,
      "circle-color": MEASURE_LINE_COLOR,
      "circle-stroke-color": MEASURE_CASING_COLOR,
      "circle-stroke-width": 2,
    },
  });
  for (const layerId of ["eligible-overview-fill", "eligible-overview-line"]) {
    map.setLayerZoomRange(layerId, TRACT_MIN_ZOOM, TRACT_DETAIL_MIN_ZOOM);
  }
  for (const layerId of [
    "rural-fill",
    "rural-line",
    "eligible-fill",
    "eligible-line",
    "mf-priority-a-fill",
    "mf-priority-a-line",
    "mf-priority-b-fill",
    "mf-priority-b-line",
    "oz2-fill",
    "oz2-line",
    "oz-fill",
    "oz-line",
  ]) {
    map.setLayerZoomRange(layerId, TRACT_DETAIL_MIN_ZOOM, 24);
  }
  for (const layerId of ["parcels-fill", "parcels-line", "parcels-fill-excluded", "parcels-line-excluded"]) {
    map.setLayerZoomRange(layerId, PARCEL_MIN_ZOOM, 24);
  }
}

const POPUP_TEXT = "#12202b";

function incomeLineFrom(value: unknown): string | null {
  const income = typeof value === "number" ? value : typeof value === "string" && value.trim() ? Number(value) : Number.NaN;
  if (!Number.isFinite(income) || income <= 0) return null;
  return `Median household income ${formatUsd(income)} (ACS 5-year B19013)`;
}

function showTractPopup(
  map: MapLibreMap,
  lngLat: maplibregl.LngLatLike,
  details: TractClickDetails,
  incomeLine: string | null = null,
) {
  const root = document.createElement("div");
  root.style.color = POPUP_TEXT;
  const kicker = document.createElement("p");
  kicker.textContent = "Census tract";
  kicker.style.margin = "0 0 2px";
  kicker.style.fontSize = "11px";
  kicker.style.letterSpacing = "0.08em";
  kicker.style.textTransform = "uppercase";
  kicker.style.color = "#3d4a57";
  const place = document.createElement("p");
  place.style.margin = "0";
  place.style.fontWeight = "600";
  place.style.color = POPUP_TEXT;
  place.textContent = details.placeLabel;
  const geoid = document.createElement("p");
  geoid.style.margin = "2px 0 0";
  geoid.style.fontWeight = "600";
  geoid.style.color = POPUP_TEXT;
  geoid.textContent = `GEOID ${details.geoid}`;
  const status = document.createElement("p");
  status.style.margin = "2px 0 0";
  status.style.color = POPUP_TEXT;
  status.textContent = details.status;
  const lines = [kicker, place, geoid, status];
  if (details.statusDetail) {
    const detail = document.createElement("p");
    detail.style.margin = "2px 0 0";
    detail.style.color = POPUP_TEXT;
    detail.textContent = details.statusDetail;
    lines.push(detail);
  }
  const ruralLine = tractPopupRuralLine(details.ruralLabel);
  if (ruralLine) {
    const rural = document.createElement("p");
    rural.style.margin = "2px 0 0";
    rural.style.color = POPUP_TEXT;
    rural.textContent = ruralLine;
    lines.push(rural);
  }
  if (incomeLine) {
    const income = document.createElement("p");
    income.style.margin = "2px 0 0";
    income.style.color = POPUP_TEXT;
    income.textContent = incomeLine;
    lines.push(income);
  }
  root.append(...lines);
  return new maplibregl.Popup({
    closeButton: true,
    maxWidth: "280px",
    closeOnClick: false,
    className: "dls-map-popup",
  })
    .setLngLat(lngLat)
    .setDOMContent(root)
    .addTo(map);
}

export function SiteMap({
  parcels,
  traffic,
  opportunityZones,
  oz2Tracts,
  ruralTracts,
  eligibleOverview,
  eligibleTracts,
  ruralPins,
  selectedId,
  hoveredId,
  selectedTractGeoid,
  showExcluded,
  showTraffic,
  showOz,
  showOz2,
  screening,
  showParcels,
  parcelLayerVisible,
  parcelVisibilityHint,
  onToggleParcelLayer,
  onToggleTractOverlay,
  showOrangePilot,
  parcelsLoading = false,
  market,
  tractClass,
  onTractClass,
  county,
  countyState,
  marketStates,
  bounds,
  boundsKey,
  ozFilter,
  minIncome,
  includeUnknownIncome,
  incomeGeography,
  highlightTierA,
  highlightTierB,
  restrictGeoids,
  showMfLegend,
  onSelect,
  onHover,
  onSelectTract,
  flyTo = null,
  onViewportIdle,
  onZoom,
  aoi = null,
  aoiMatchedCount = 0,
  aoiTruncated = false,
  onAoiChange,
}: SiteMapProps) {
  const shellRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("Loading map…");
  const [basemap, setBasemap] = useState<BasemapMode>("streets");
  const [drawing, setDrawing] = useState(false);
  const [measuring, setMeasuring] = useState(false);
  const [measurePoints, setMeasurePoints] = useState<LngLat[]>([]);
  const callbacksRef = useRef({ onSelect, onHover, onSelectTract, onViewportIdle, onZoom, onAoiChange });
  callbacksRef.current = { onSelect, onHover, onSelectTract, onViewportIdle, onZoom, onAoiChange };
  const drawingRef = useRef(drawing);
  drawingRef.current = drawing;
  const measuringRef = useRef(measuring);
  measuringRef.current = measuring;
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const aoiRef = useRef(aoi);
  aoiRef.current = aoi;
  const basemapRef = useRef(basemap);
  basemapRef.current = basemap;
  const boundsRef = useRef(bounds);
  boundsRef.current = bounds;
  const ruralPinsRef = useRef(ruralPins);
  ruralPinsRef.current = ruralPins;
  const overviewRef = useRef(eligibleOverview);
  overviewRef.current = eligibleOverview;
  const ruralTractsRef = useRef(ruralTracts);
  ruralTractsRef.current = ruralTracts;
  const eligibleTractsRef = useRef(eligibleTracts);
  eligibleTractsRef.current = eligibleTracts;
  const oz2TractsRef = useRef(oz2Tracts);
  oz2TractsRef.current = oz2Tracts;
  const tractTileCacheRef = useRef<EligibleTractTileCache | null>(null);
  if (!tractTileCacheRef.current) tractTileCacheRef.current = createEligibleTractTileCache();
  const tractSourceMapRef = useRef<MapLibreMap | null>(null);
  const idleTimer = useRef<number | null>(null);
  const loadDetailRef = useRef<() => void>(() => {});
  loadDetailRef.current = () => {
    const map = mapRef.current;
    const cache = tractTileCacheRef.current;
    if (!map || !cache) return;
    const rural = ruralTractsRef.current;
    const eligible = eligibleTractsRef.current;
    const oz2 = oz2TractsRef.current;
    const signature = `${rural.features.length}|${eligible.features.length}|${oz2.features.length}|${rural.features[0]?.properties.tractGeoid ?? ""}|${eligible.features[0]?.properties.tractGeoid ?? ""}|${oz2.features[0]?.properties.tractGeoid ?? ""}`;
    syncEligibleTractTileCache(
      cache,
      {
        rural: rural.features,
        eligible: eligible.features,
        oz2: oz2.features,
      },
      signature,
    );
    if (tractSourceMapRef.current !== map) {
      tractSourceMapRef.current = map;
      cache.loaded.clear();
      cache.rural.clear();
      cache.eligible.clear();
      cache.oz2.clear();
    }
    if (!detailTractsVisibleAtZoom(map.getZoom())) return;
    const camera = map.getBounds();
    const changed = absorbEligibleTractTiles(
      cache,
      tractGridKeysForBbox([camera.getWest(), camera.getSouth(), camera.getEast(), camera.getNorth()]),
    );
    const push = (sourceId: string, features: GeoJSON.Feature[]) => {
      const source = map.getSource(sourceId);
      if (source?.type === "geojson") {
        (source as GeoJSONSource).setData({ type: "FeatureCollection", features });
      }
    };
    if (changed.rural) push("rural-tracts", [...cache.rural.values()]);
    if (changed.eligible) push("eligible-tracts", [...cache.eligible.values()]);
    if (changed.oz2) push("oz2-tracts", [...cache.oz2.values()]);
  };

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let cancelled = false;

    const start = async () => {
      let lastError: unknown;
      for (const style of STREET_STYLE_CANDIDATES) {
        try {
          const map = new maplibregl.Map({
            container: containerRef.current!,
            style,
            center: ORANGE_COUNTY_CENTER,
            zoom: 9.4,
            attributionControl: { compact: true },
            scrollZoom: true,
            dragPan: true,
            touchZoomRotate: true,
            doubleClickZoom: true,
            boxZoom: true,
            keyboard: true,
            cooperativeGestures: false,
          });
          applyMapGestures(map, false);
          map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), MAP_SCALE.position);
          map.addControl(
            new maplibregl.ScaleControl({ maxWidth: MAP_SCALE.maxWidth, unit: MAP_SCALE.unit }),
            MAP_SCALE.position,
          );
          const scaleEl = map.getContainer().querySelector<HTMLElement>(".maplibregl-ctrl-scale");
          if (scaleEl) {
            scaleEl.classList.add("dls-map-scale");
            map.getContainer().appendChild(scaleEl);
          }
          map.fitBounds(boundsRef.current, { padding: 48, duration: 0, maxZoom: 11 });
          await new Promise<void>((resolve, reject) => {
            const timer = window.setTimeout(() => reject(new Error("Basemap timed out")), 15000);
            map.once("load", () => {
              window.clearTimeout(timer);
              resolve();
            });
          });
          if (cancelled) {
            map.remove();
            return;
          }
          addOverlayLayers(
            map,
            parcels,
            traffic,
            opportunityZones,
            overviewRef.current,
            ruralPinsRef.current,
            basemapRef.current,
          );
          addSatelliteSourceAndLayer(map);
          applyBasemap(map, basemapRef.current);

          map.on("click", "schools-circle", (event) => {
            if (drawingRef.current || measuringRef.current) return;
            const props = event.features?.[0]?.properties;
            if (!props) return;
            const root = document.createElement("div");
            const name = document.createElement("p");
            name.style.fontWeight = "600";
            name.style.color = "#12202b";
            name.style.margin = "0";
            name.textContent = String(props.name ?? "School");
            const summary = document.createElement("p");
            summary.style.color = "#12202b";
            summary.style.margin = "2px 0 0";
            summary.textContent = String(props.summary ?? "");
            root.append(name, summary);
            const href = typeof props.reportCardUrl === "string" ? props.reportCardUrl : "";
            if (href.startsWith("https://")) {
              const link = document.createElement("a");
              link.href = href;
              link.target = "_blank";
              link.rel = "noreferrer";
              link.style.color = "#12202b";
              link.textContent = "Official report card";
              root.append(link);
            }
            popupRef.current?.remove();
            popupRef.current = new maplibregl.Popup({ closeButton: true, maxWidth: "280px", className: "dls-map-popup" })
              .setLngLat(event.lngLat)
              .setDOMContent(root)
              .addTo(map);
          });

          const interactive = ["parcels-fill", "parcels-fill-excluded"];
          map.on("click", interactive, (event) => {
            if (drawingRef.current || measuringRef.current) return;
            if (queryRendered(map, event.point, ["schools-circle"]).length > 0) return;
            const id = event.features?.[0]?.properties?.id;
            if (typeof id === "string") callbacksRef.current.onSelect(id);
          });
          const tractLayers = ["mf-priority-a-fill", "mf-priority-b-fill", "eligible-fill", "rural-fill", "oz2-fill", "oz-fill"];
          map.on("click", tractLayers, (event) => {
            if (drawingRef.current || measuringRef.current) return;
            const feature = event.features?.[0];
            const details = tractClickFromFeature({
              layerId: feature?.layer.id ?? "",
              properties: (feature?.properties ?? null) as Record<string, unknown> | null,
            });
            if (!details) return;
            if (details.kind === "eligible" && !showOzTractInScMarkets({ state: details.state, geoid: details.geoid })) return;
            const income = incomeLineFrom(feature?.properties?.medianHouseholdIncome);
            const parcelHit = queryRendered(map, event.point, interactive);
            if (parcelHit.length > 0) {
              popupRef.current?.remove();
              popupRef.current = showTractPopup(map, event.lngLat, details, income);
              return;
            }
            if (details.kind === "eligible") {
              callbacksRef.current.onSelectTract(details.geoid);
              popupRef.current?.remove();
              popupRef.current = details.opensRuralDrawer ? null : showTractPopup(map, event.lngLat, details, income);
              return;
            }
            callbacksRef.current.onSelectTract(null);
            popupRef.current?.remove();
            popupRef.current = showTractPopup(map, event.lngLat, details, income);
          });
          map.on("click", (event) => {
            if (!measuringRef.current || drawingRef.current) return;
            const next: LngLat = [event.lngLat.lng, event.lngLat.lat];
            setMeasurePoints((points) => appendMeasurePoint(points, next));
          });
          map.on("mousemove", interactive, (event) => {
            if (drawingRef.current) return;
            map.getCanvas().style.cursor = "pointer";
            const id = event.features?.[0]?.properties?.id;
            callbacksRef.current.onHover(typeof id === "string" ? id : null);
          });
          map.on("mouseleave", interactive, () => {
            if (drawingRef.current) return;
            map.getCanvas().style.cursor = "";
            callbacksRef.current.onHover(null);
          });
          const paintZoomAttr = () => {
            containerRef.current?.setAttribute("data-map-zoom", map.getZoom().toFixed(2));
          };
          const emitViewport = () => {
            paintZoomAttr();
            const zoomNow = map.getZoom();
            callbacksRef.current.onZoom?.(zoomNow);
            if (drawingRef.current || aoiRef.current) return;
            const cb = callbacksRef.current.onViewportIdle;
            if (!cb) return;
            const b = map.getBounds();
            cb([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()], zoomNow);
          };
          map.on("zoom", paintZoomAttr);
          map.on("moveend", () => {
            if (idleTimer.current) window.clearTimeout(idleTimer.current);
            idleTimer.current = window.setTimeout(emitViewport, TRACT_VIEWPORT_DEBOUNCE_MS);
          });
          mapRef.current = map;
          emitViewport();
          loadDetailRef.current();
          setStatus("ready");
          setMessage("");
          return;
        } catch (error) {
          lastError = error;
        }
      }
      if (!cancelled) {
        setStatus("error");
        setMessage(lastError instanceof Error ? lastError.message : "Map failed to load");
      }
    };

    void start();
    return () => {
      cancelled = true;
      if (idleTimer.current) window.clearTimeout(idleTimer.current);
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // Parcels, pins, and tract polygons update through setData. Remounting the map
    // on those refreshes drops the tile cache and freezes the UI.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sources update through setData
  }, [traffic, opportunityZones]);

  useEffect(() => {
    const shell = shellRef.current;
    if (!shell) return;
    const onWheel = (event: WheelEvent) => {
      if (!event.isTrusted) return;
      const map = mapRef.current;
      if (!map) return;
      const target = event.target;
      if (!(target instanceof Node) || !shell.contains(target)) return;
      if (map.getCanvasContainer().contains(target)) return;
      if (target instanceof Element && target.closest("[data-map-scroll]")) return;
      event.preventDefault();
      map.getCanvas().dispatchEvent(
        new WheelEvent("wheel", {
          bubbles: true,
          cancelable: true,
          deltaX: event.deltaX,
          deltaY: event.deltaY,
          deltaZ: event.deltaZ,
          deltaMode: event.deltaMode,
          clientX: event.clientX,
          clientY: event.clientY,
          ctrlKey: event.ctrlKey,
          metaKey: event.metaKey,
          shiftKey: event.shiftKey,
          altKey: event.altKey,
        }),
      );
    };
    shell.addEventListener("wheel", onWheel, { capture: true, passive: false });
    return () => shell.removeEventListener("wheel", onWheel, { capture: true });
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const source = map.getSource("parcels");
    if (source?.type === "geojson") {
      (source as GeoJSONSource).setData(parcels);
    }
  }, [parcels, status]);

  useEffect(() => {
    if (!showParcels && drawing) setDrawing(false);
  }, [showParcels, drawing]);

  useEffect(() => {
    if (drawing && measuring) {
      setMeasuring(false);
      setMeasurePoints([]);
    }
  }, [drawing, measuring]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const source = map.getSource("measure");
    if (source?.type === "geojson") {
      (source as GeoJSONSource).setData(measureFeatureCollection(measurePoints));
    }
  }, [measurePoints, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    if (measuring) {
      map.doubleClickZoom.disable();
      map.getCanvas().style.cursor = "crosshair";
    } else if (!drawing) {
      map.doubleClickZoom.enable();
      map.getCanvas().style.cursor = "";
    }
  }, [measuring, drawing, status]);

  useEffect(() => {
    if (!measuring) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMeasuring(false);
        setMeasurePoints([]);
        popupRef.current?.remove();
        popupRef.current = null;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [measuring]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready" || drawing) return;
    const source = map.getSource("aoi");
    if (source?.type === "geojson") {
      (source as GeoJSONSource).setData(aoiFeatureCollection(aoi?.bbox ?? null));
    }
  }, [aoi, drawing, status]);

  const hadAoi = useRef(false);
  useEffect(() => {
    const wasLocked = hadAoi.current;
    hadAoi.current = Boolean(aoi);
    if (!wasLocked || aoi || status !== "ready") return;
    const map = mapRef.current;
    if (!map) return;
    const boundsNow = map.getBounds();
    callbacksRef.current.onViewportIdle?.(
      [boundsNow.getWest(), boundsNow.getSouth(), boundsNow.getEast(), boundsNow.getNorth()],
      map.getZoom(),
    );
  }, [aoi, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    applyMapGestures(map, drawing, measuring);
    if (!drawing) return;

    const canvas = map.getCanvas();
    canvas.style.cursor = "crosshair";

    let origin: { lng: number; lat: number } | null = null;
    let last: { lng: number; lat: number } | null = null;

    const preview = (lng: number, lat: number) => {
      if (!origin) return;
      last = { lng, lat };
      const bbox = normalizeBbox(origin.lng, origin.lat, lng, lat);
      const source = map.getSource("aoi");
      if (source?.type === "geojson") {
        (source as GeoJSONSource).setData(aoiFeatureCollection(bbox));
      }
    };

    const finish = (lng: number, lat: number) => {
      if (!origin) return;
      const start = origin;
      origin = null;
      const bbox = normalizeBbox(start.lng, start.lat, lng, lat);
      if (!bbox) {
        const source = map.getSource("aoi");
        if (source?.type === "geojson") {
          (source as GeoJSONSource).setData(aoiFeatureCollection(aoiRef.current?.bbox ?? null));
        }
        return;
      }
      callbacksRef.current.onAoiChange?.({ bbox, source: "draw" });
      setDrawing(false);
    };

    const onMouseDown = (event: MapMouseEvent) => {
      event.preventDefault();
      origin = { lng: event.lngLat.lng, lat: event.lngLat.lat };
      last = origin;
    };
    const onMouseMove = (event: MapMouseEvent) => {
      if (!origin) return;
      preview(event.lngLat.lng, event.lngLat.lat);
    };
    const onMouseUp = (event: MapMouseEvent) => {
      finish(event.lngLat.lng, event.lngLat.lat);
    };
    const onWindowMouseUp = (event: MouseEvent) => {
      if (!origin || !last) return;
      if (event.target === canvas) return;
      const target = event.target;
      if (target instanceof Element && target.closest("[data-aoi-controls]")) {
        origin = null;
        const source = map.getSource("aoi");
        if (source?.type === "geojson") {
          (source as GeoJSONSource).setData(aoiFeatureCollection(aoiRef.current?.bbox ?? null));
        }
        return;
      }
      finish(last.lng, last.lat);
    };
    const onTouchStart = (event: MapTouchEvent) => {
      if (event.originalEvent.touches.length !== 1) return;
      event.preventDefault();
      origin = { lng: event.lngLat.lng, lat: event.lngLat.lat };
    };
    const onTouchMove = (event: MapTouchEvent) => {
      if (!origin) return;
      preview(event.lngLat.lng, event.lngLat.lat);
    };
    const onTouchEnd = (event: MapTouchEvent) => {
      finish(event.lngLat.lng, event.lngLat.lat);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawing(false);
    };

    map.on("mousedown", onMouseDown);
    map.on("mousemove", onMouseMove);
    map.on("mouseup", onMouseUp);
    map.on("touchstart", onTouchStart);
    map.on("touchmove", onTouchMove);
    map.on("touchend", onTouchEnd);
    window.addEventListener("mouseup", onWindowMouseUp);
    window.addEventListener("keydown", onKey);

    return () => {
      map.off("mousedown", onMouseDown);
      map.off("mousemove", onMouseMove);
      map.off("mouseup", onMouseUp);
      map.off("touchstart", onTouchStart);
      map.off("touchmove", onTouchMove);
      map.off("touchend", onTouchEnd);
      window.removeEventListener("mouseup", onWindowMouseUp);
      window.removeEventListener("keydown", onKey);
      try {
        applyMapGestures(map, false, measuringRef.current);
        canvas.style.cursor = "";
      } catch {
        // Map already removed.
      }
    };
  }, [drawing, measuring, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const layerOn = parcelLayerVisible ?? showParcels;
    setFilterSafe(map, "parcels-fill", layerOn ? parcelMatchFilter : parcelHiddenFilter);
    setFilterSafe(map, "parcels-line", layerOn ? parcelMatchFilter : parcelHiddenFilter);
    setFilterSafe(map, "parcels-fill-excluded", layerOn && showExcluded ? parcelExcludedFilter : parcelHiddenFilter);
    setFilterSafe(map, "parcels-line-excluded", layerOn && showExcluded ? parcelExcludedFilter : parcelHiddenFilter);
    setVisibilitySafe(map, "traffic-line", showOrangePilot && showTraffic ? "visible" : "none");
    setVisibilitySafe(map, "oz-fill", showOrangePilot && showOz ? "visible" : "none");
    setVisibilitySafe(map, "oz-line", showOrangePilot && showOz ? "visible" : "none");
    setVisibilitySafe(map, "oz2-fill", showOrangePilot && showOz2 ? "visible" : "none");
    setVisibilitySafe(map, "oz2-line", showOrangePilot && showOz2 ? "visible" : "none");
    const classCut = eligibleClassCut(tractClass, ozFilter);
    const incomeActive = tractIncomeFilterActive(incomeGeography, minIncome, includeUnknownIncome);
    const showOverview = showOz2 && classCut !== "none" && restrictGeoids == null && !incomeActive;
    const showRuralLayer = showOz2 && tractClass !== "urban" && ozFilter !== "non-rural-eligible";
    const showEligibleLayer = showOz2 && restrictGeoids == null && classCut !== "none";
    setVisibilitySafe(map, "eligible-overview-fill", showOverview ? "visible" : "none");
    setVisibilitySafe(map, "eligible-overview-line", showOverview ? "visible" : "none");
    setVisibilitySafe(map, "rural-fill", showRuralLayer ? "visible" : "none");
    setVisibilitySafe(map, "rural-line", showRuralLayer ? "visible" : "none");
    setVisibilitySafe(map, "eligible-fill", showEligibleLayer ? "visible" : "none");
    setVisibilitySafe(map, "eligible-line", showEligibleLayer ? "visible" : "none");
    for (const layerId of ["mf-priority-a-fill", "mf-priority-a-line", "mf-priority-b-fill", "mf-priority-b-line"]) {
      setVisibilitySafe(map, layerId, showRuralLayer ? "visible" : "none");
    }
    const incomeFilter = tractIncomeLayerFilter(
      incomeGeography,
      minIncome,
      includeUnknownIncome,
    ) as maplibregl.FilterSpecification | null;
    const oz2Filter: maplibregl.FilterSpecification | null =
      classCut === "all"
        ? null
        : classCut === "none"
          ? ["==", ["get", "tractGeoid"], "__none__"]
          : ["==", ["get", "rural"], classCut === "rural"];
    const oz2Shown = andFilter(oz2Filter, scNominatedOverlayFilter() as maplibregl.FilterSpecification);
    setFilterSafe(map, "oz2-fill", andFilter(oz2Shown, incomeFilter));
    setFilterSafe(map, "oz2-line", andFilter(oz2Shown, incomeFilter));
    const overviewFilter = eligibleOverviewFilter(classCut) as maplibregl.FilterSpecification | null;
    setFilterSafe(map, "eligible-overview-fill", overviewFilter);
    setFilterSafe(map, "eligible-overview-line", overviewFilter);
    const ruralFilter = tractOverlayFilter(showOrangePilot, restrictGeoids);
    setFilterSafe(map, "rural-fill", andFilter(ruralFilter, incomeFilter));
    setFilterSafe(map, "rural-line", andFilter(ruralFilter, incomeFilter));
    const eligibleFilter = tractOverlayFilter(showOrangePilot, null, classCut);
    setFilterSafe(map, "eligible-fill", andFilter(eligibleFilter, incomeFilter));
    setFilterSafe(map, "eligible-line", andFilter(eligibleFilter, incomeFilter));
    const tierAFilter = tractOverlayFilter(showOrangePilot, highlightTierA);
    const tierBFilter = tractOverlayFilter(showOrangePilot, highlightTierB);
    setFilterSafe(map, "mf-priority-a-fill", andFilter(tierAFilter, incomeFilter));
    setFilterSafe(map, "mf-priority-a-line", andFilter(tierAFilter, incomeFilter));
    setFilterSafe(map, "mf-priority-b-fill", andFilter(tierBFilter, incomeFilter));
    setFilterSafe(map, "mf-priority-b-line", andFilter(tierBFilter, incomeFilter));
  }, [
    parcelLayerVisible,
    showExcluded,
    showTraffic,
    showOz,
    showOz2,
    showParcels,
    showOrangePilot,
    ozFilter,
    minIncome,
    includeUnknownIncome,
    incomeGeography,
    tractClass,
    status,
    highlightTierA,
    highlightTierB,
    restrictGeoids,
  ]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    addSatelliteSourceAndLayer(map);
    applyBasemap(map, basemap);
    setVisibilitySafe(map, "traffic-line", showOrangePilot && showTraffic ? "visible" : "none");
    setVisibilitySafe(map, "oz-fill", showOrangePilot && showOz ? "visible" : "none");
    setVisibilitySafe(map, "oz-line", showOrangePilot && showOz ? "visible" : "none");
    setVisibilitySafe(map, "oz2-fill", showOrangePilot && showOz2 ? "visible" : "none");
    setVisibilitySafe(map, "oz2-line", showOrangePilot && showOz2 ? "visible" : "none");
    const classCut = eligibleClassCut(tractClass, ozFilter);
    const incomeActive = tractIncomeFilterActive(incomeGeography, minIncome, includeUnknownIncome);
    const showOverview = showOz2 && classCut !== "none" && restrictGeoids == null && !incomeActive;
    const showRuralLayer = showOz2 && tractClass !== "urban" && ozFilter !== "non-rural-eligible";
    const showEligibleLayer = showOz2 && restrictGeoids == null && classCut !== "none";
    setVisibilitySafe(map, "eligible-overview-fill", showOverview ? "visible" : "none");
    setVisibilitySafe(map, "eligible-overview-line", showOverview ? "visible" : "none");
    setVisibilitySafe(map, "rural-fill", showRuralLayer ? "visible" : "none");
    setVisibilitySafe(map, "rural-line", showRuralLayer ? "visible" : "none");
    setVisibilitySafe(map, "eligible-fill", showEligibleLayer ? "visible" : "none");
    setVisibilitySafe(map, "eligible-line", showEligibleLayer ? "visible" : "none");
    for (const layerId of ["mf-priority-a-fill", "mf-priority-a-line", "mf-priority-b-fill", "mf-priority-b-line"]) {
      setVisibilitySafe(map, layerId, showRuralLayer ? "visible" : "none");
    }
  }, [
    basemap,
    showTraffic,
    showOz,
    showOz2,
    showOrangePilot,
    ozFilter,
    tractClass,
    restrictGeoids,
    status,
    minIncome,
    includeUnknownIncome,
    incomeGeography,
  ]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const show = (ids: string[], on: boolean) => {
      for (const id of ids) setVisibilitySafe(map, id, on ? "visible" : "none");
    };
    show(["flood-raster"], screening.flood);
    show(["wetlands-raster"], screening.wetlands);
    show(["water-fill", "water-line"], screening.water);
    show(["sewer-fill", "sewer-line"], screening.sewer);
    show(["power-fill", "power-line"], screening.power);
    show(
      [
        "schools-circle",
        "school-zone-raster",
        "school-ms-raster",
        "school-cms-es-raster",
        "school-cms-ms-raster",
        "school-cms-hs-raster",
        "school-ccsd-raster",
        "dcsd-zones-fill",
        "dcsd-zones-line",
      ],
      screening.schools,
    );
  }, [screening, status, basemap]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    let timer: number | null = null;
    let requestId = 0;
    const clearedSources = new Set<string>();
    const setCollection = (sourceId: string, data: GeoJSON.FeatureCollection) => {
      const source = map.getSource(sourceId);
      if (source?.type === "geojson") (source as GeoJSONSource).setData(data);
    };
    const load = () => {
      const camera = map.getBounds();
      const bbox = [camera.getWest(), camera.getSouth(), camera.getEast(), camera.getNorth()].join(",");
      const id = ++requestId;
      const pull = async (url: string, sourceId: string, enabled: boolean) => {
        if (!enabled) {
          if (clearedSources.has(sourceId)) return;
          clearedSources.add(sourceId);
          setCollection(sourceId, EMPTY_COLLECTION);
          return;
        }
        clearedSources.delete(sourceId);
        try {
          const response = await fetch(url);
          if (!response.ok || id !== requestId) return;
          const payload = (await response.json()) as GeoJSON.FeatureCollection;
          if (id !== requestId) return;
          setCollection(sourceId, { type: "FeatureCollection", features: payload.features ?? [] });
        } catch {
          if (id === requestId) setCollection(sourceId, EMPTY_COLLECTION);
        }
      };
      void pull(`/api/screening/schools?bbox=${bbox}`, "schools", screening.schools);
      void pull(`/api/screening/dcsd-zones?bbox=${bbox}`, "dcsd-zones", screening.schools);
      void pull(`/api/screening/utilities?layer=water&bbox=${bbox}`, "water", screening.water);
      void pull(`/api/screening/utilities?layer=sewer&bbox=${bbox}`, "sewer", screening.sewer);
      void pull(`/api/screening/utilities?layer=power&bbox=${bbox}`, "power", screening.power);
    };
    const schedule = () => {
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(load, 350);
    };
    schedule();
    map.on("moveend", schedule);
    return () => {
      requestId += 1;
      map.off("moveend", schedule);
      if (timer) window.clearTimeout(timer);
    };
  }, [screening, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    let timer: number | null = null;
    const schedule = () => {
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(() => loadDetailRef.current(), TRACT_VIEWPORT_DEBOUNCE_MS);
    };
    schedule();
    map.on("moveend", schedule);
    return () => {
      map.off("moveend", schedule);
      if (timer) window.clearTimeout(timer);
    };
  }, [status]);

  const previousHover = useRef<string | null>(null);
  const previousSelected = useRef<string | null>(null);
  const flewToParcel = useRef<string | null>(null);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    if (previousHover.current) {
      map.setFeatureState({ source: "parcels", id: previousHover.current }, { hover: false });
    }
    if (hoveredId) {
      map.setFeatureState({ source: "parcels", id: hoveredId }, { hover: true });
    }
    previousHover.current = hoveredId;
  }, [hoveredId, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    if (previousSelected.current) {
      map.setFeatureState({ source: "parcels", id: previousSelected.current }, { selected: false });
    }
    if (selectedId) {
      map.setFeatureState({ source: "parcels", id: selectedId }, { selected: true });
      if (flewToParcel.current !== selectedId) {
        const feature = parcels.features.find((item) => item.properties.id === selectedId);
        if (feature) {
          const [lng, lat] = feature.properties.centroid;
          map.easeTo({ center: [lng, lat], zoom: Math.max(map.getZoom(), 13), duration: 500 });
          flewToParcel.current = selectedId;
        }
      }
    } else {
      flewToParcel.current = null;
    }
    previousSelected.current = selectedId;
  }, [selectedId, parcels.features, status]);

  const previousTract = useRef<string | null>(null);
  const flewToTract = useRef<string | null>(null);
  const skipInitialFit = useRef(true);
  const fittedBoundsKey = useRef<string | null>(null);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const pinSource = map.getSource("rural-pins");
    if (pinSource?.type === "geojson") {
      (pinSource as GeoJSONSource).setData(ruralPins);
    }
  }, [ruralPins, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    // Same shed with a new array must not refit, or +/- and the scroll wheel snap back.
    const signature = `${boundsKey}|${bounds.map((pair) => pair.join(",")).join("|")}`;
    if (skipInitialFit.current) {
      skipInitialFit.current = false;
      fittedBoundsKey.current = signature;
      return;
    }
    if (fittedBoundsKey.current === signature) return;
    fittedBoundsKey.current = signature;
    map.fitBounds(bounds, { padding: 56, duration: 650, maxZoom: 11 });
  }, [bounds, boundsKey, status]);

  const flewToPoint = useRef<number | null>(null);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready" || !flyTo) return;
    if (flewToPoint.current === flyTo.key) return;
    flewToPoint.current = flyTo.key;
    map.easeTo({
      center: [flyTo.lng, flyTo.lat],
      zoom: Math.max(map.getZoom(), 14),
      duration: 700,
    });
  }, [flyTo, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const ruralIds = new Set(ruralTracts.features.map((feature) => feature.properties.tractGeoid));
    const eligibleIds = new Set(eligibleTracts.features.map((feature) => feature.properties.tractGeoid));
    const pinIds = new Set(
      ruralPins.features.map((feature) => feature.properties?.tractGeoid).filter((geoid): geoid is string => typeof geoid === "string"),
    );
    const setTractState = (id: string, selected: boolean) => {
      if (ruralIds.has(id)) map.setFeatureState({ source: "rural-tracts", id }, { selected });
      if (eligibleIds.has(id)) map.setFeatureState({ source: "eligible-tracts", id }, { selected });
      if (pinIds.has(id)) map.setFeatureState({ source: "rural-pins", id }, { selected });
    };
    if (previousTract.current) setTractState(previousTract.current, false);
    if (selectedTractGeoid) {
      setTractState(selectedTractGeoid, true);
      if (flewToTract.current !== selectedTractGeoid) {
        const pin = ruralPins.features.find((feature) => feature.properties?.tractGeoid === selectedTractGeoid);
        const coordinates = pin?.geometry?.coordinates;
        if (coordinates && coordinates.length >= 2) {
          map.easeTo({
            center: [coordinates[0], coordinates[1]],
            zoom: Math.max(map.getZoom(), 10),
            duration: 500,
          });
          flewToTract.current = selectedTractGeoid;
        }
      }
    } else {
      flewToTract.current = null;
    }
    previousTract.current = selectedTractGeoid;
  }, [selectedTractGeoid, ruralPins.features, ruralTracts.features, eligibleTracts.features, status]);

  useEffect(() => {
    mapRef.current?.resize();
  }, [selectedId, selectedTractGeoid]);

  const overlayMode = southCarolinaOverlayMode(market, countyState);
  const tractToggleName =
    overlayMode === "nominated-only" ? "nominated census tracts" : overlayMode === "mixed" ? "census tracts" : "eligible census tracts";
  const layerOn = parcelLayerVisible ?? showParcels;
  const legendScope = { market, county, state: countyState, states: marketStates };

  return (
    <div ref={shellRef} className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {status === "ready" ? (
        <div className="map-chrome absolute left-3 top-3 z-30 flex flex-col items-start gap-2 sm:left-4 sm:top-4">
          <BasemapToggle value={basemap} onChange={setBasemap} />
          <MeasureControl
            active={measuring}
            points={measurePoints}
            onStart={() => {
              setDrawing(false);
              setMeasuring(true);
            }}
            onClear={() => setMeasurePoints([])}
            onCancel={() => {
              setMeasuring(false);
              setMeasurePoints([]);
            }}
          />
          {showParcels && onToggleParcelLayer ? (
            <ParcelLayerToggle visible={layerOn} hint={parcelVisibilityHint ?? ""} onToggle={onToggleParcelLayer} />
          ) : null}
          {onToggleTractOverlay ? (
            <button
              type="button"
              data-tract-toggle
              aria-pressed={showOz2}
              aria-label={showOz2 ? `Hide ${tractToggleName}` : `Show ${tractToggleName}`}
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                onToggleTractOverlay();
              }}
              className={`rounded-full border px-3.5 py-2 text-sm font-semibold ${
                showOz2
                  ? "map-scrim text-white"
                  : "border-ink-950 bg-clay-500 text-ink-950 shadow-[0_10px_28px_rgba(0,0,0,0.55)] hover:bg-clay-400"
              }`}
            >
              {showOz2 ? "Hide tracts" : "Show tracts"}
            </button>
          ) : null}
        </div>
      ) : null}
      {status === "ready" && showParcels ? (
        <AoiControls
          drawing={drawing}
          aoi={aoi}
          matchedCount={aoiMatchedCount}
          truncated={aoiTruncated}
          loading={parcelsLoading && Boolean(aoi)}
          onDraw={() => {
            setMeasuring(false);
            setMeasurePoints([]);
            setDrawing(true);
          }}
          onCancelDraw={() => setDrawing(false)}
          onClear={() => {
            setDrawing(false);
            onAoiChange?.(null);
          }}
          onLockView={() => {
            const map = mapRef.current;
            if (!map) return;
            const camera = map.getBounds();
            const bbox = normalizeBbox(camera.getWest(), camera.getSouth(), camera.getEast(), camera.getNorth());
            if (!bbox) return;
            setDrawing(false);
            onAoiChange?.({ bbox, source: "bounds" });
          }}
        />
      ) : null}
      {status === "ready" && (showOz || showOz2 || showParcels || screening.flood || screening.wetlands || screening.schools || screening.water || screening.sewer || screening.power) ? (
        <div className="map-chrome map-scrim absolute bottom-3 left-3 z-10 max-w-[min(17rem,calc(100%-12rem))] rounded-xl border sm:bottom-4 sm:left-4 sm:max-w-[min(22rem,calc(100%-12rem))]">
          <div className="legend-scroll max-h-[42vh] space-y-1.5 overflow-y-auto px-3 py-2.5 text-sm leading-snug">
          {aoi ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-5 border border-dashed border-clay-400 align-middle" />
              Area of interest
            </p>
          ) : null}
          {layerOn ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle bg-moss-400" />
              Parcels (matched)
              {parcelsLoading ? (aoi ? " · loading AOI…" : " · refreshing viewport…") : aoi ? " · AOI locked" : ""}
            </p>
          ) : null}
          {showOz2 ? (
            <>
              <div className="flex gap-1 pb-1" role="group" aria-label="Rural or urban eligible tracts">
                {(
                  [
                    ["both", "Both"],
                    ["rural", "Rural"],
                    ["urban", "Urban"],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={tractClass === value}
                    className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
                      tractClass === value ? "map-scrim-active border-white" : "border-white/55 text-white hover:bg-white/10"
                    }`}
                    onClick={() => onTractClass(value)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-ink-100">
                Only OZ 2.0 eligible tracts are drawn. They stay on the map as you pan, from a Southeast-wide view in
                to the tract boundary. Tracts without eligibility data are not shown.
              </p>
              <p className="text-[10px] uppercase tracking-[0.14em] text-ink-300">
                {overlayMode === "nominated-only" ? "South Carolina nominations" : "OZ eligibility"}
              </p>
              {overlayMode === "nominated-only" ? (
                <>
                  <p>
                    <span
                      className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                      style={{ backgroundColor: OZ_TRACT_SWATCH.rural }}
                    />
                    Rural · Governor-nominated
                    <span className="mt-0.5 block text-xs text-ink-100">{SC_NOMINATED_RURAL_LEGEND_BLURB}</span>
                  </p>
                  <p>
                    <span
                      className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                      style={{ backgroundColor: OZ_TRACT_SWATCH.urban }}
                    />
                    Urban · Governor-nominated
                    <span className="mt-0.5 block text-xs text-ink-100">{SC_NOMINATED_URBAN_LEGEND_BLURB}</span>
                  </p>
                  <p className="text-xs text-ink-100">
                    Eligible tracts that were not nominated are not shown. Not a designated QOZ. Nomination alone is not
                    a tax benefit.
                  </p>
                </>
              ) : (
                <>
                  <p>
                    <span
                      className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                      style={{ backgroundColor: OZ_TRACT_SWATCH.rural }}
                    />
                    Rural eligible — not designated
                    <span className="mt-0.5 block text-xs text-ink-100">{RURAL_ELIGIBLE_LEGEND_BLURB}</span>
                  </p>
                  <p>
                    <span
                      className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                      style={{ backgroundColor: OZ_TRACT_SWATCH.urban }}
                    />
                    Urban eligible — not designated
                    <span className="mt-0.5 block text-xs text-ink-100">{URBAN_ELIGIBLE_LEGEND_BLURB}</span>
                  </p>
                  {overlayMode === "mixed" ? (
                    <p className="text-xs text-ink-100">
                      South Carolina tracts on this map are Governor-nominated only. Eligible tracts that were not
                      nominated are not shown. Other states stay on the eligible list and are not designated.
                    </p>
                  ) : null}
                </>
              )}
              {showMfLegend ? (
                <div className="space-y-1.5 border-t border-white/20 pt-1.5">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-ink-300">MF priority</p>
                  <p className="text-xs text-ink-100">{MF_PRIORITY_LEGEND_BLURB}</p>
                  <p>
                    <span
                      className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                      style={{ backgroundColor: MF_PRIORITY_SWATCH.tierA }}
                    />
                    SC MF priority · Tier A
                    <span className="mt-0.5 block text-xs text-ink-100">{MF_PRIORITY_TIER_A_MEANING}</span>
                  </p>
                  <p>
                    <span
                      className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                      style={{ backgroundColor: MF_PRIORITY_SWATCH.tierB }}
                    />
                    SC MF priority · Tier B
                    <span className="mt-0.5 block text-xs text-ink-100">{MF_PRIORITY_TIER_B_MEANING}</span>
                  </p>
                </div>
              ) : null}
            </>
          ) : null}
          <p className="text-xs text-ink-100">90-minute sheds are approximate county rings, not drive-time isochrones. Tract polygons have no center dot.</p>
          {screening.flood ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle" style={{ backgroundColor: "#3b6ea5" }} />
              FEMA flood zones
            </p>
          ) : null}
          {screening.wetlands ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle" style={{ backgroundColor: "#2f6b4f" }} />
              Wetlands (NWI, closer zoom)
            </p>
          ) : null}
          {screening.water ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle" style={{ backgroundColor: "#3d7dff" }} />
              {screeningLegendLine("water", legendScope)}
            </p>
          ) : null}
          {screening.sewer ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle" style={{ backgroundColor: "#7a5cff" }} />
              {screeningLegendLine("sewer", legendScope)}
            </p>
          ) : null}
          {screening.power ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle" style={{ backgroundColor: "#e0b15a" }} />
              {screeningLegendLine("power", legendScope)}
            </p>
          ) : null}
          {screening.schools ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-3.5 rounded-full align-middle" style={{ backgroundColor: "#1f7a4d" }} />
              {screeningLegendLine("schools", legendScope)}
            </p>
          ) : null}
          {screening.flood || screening.wetlands || screening.schools || screening.water || screening.sewer || screening.power ? (
            <p className="text-xs text-ink-100">
              School dots and utility areas load at about county zoom. Wetlands draw when you zoom in. No grade or service connection is invented.
            </p>
          ) : null}
          {showOz ? (
            <p>
              <span
                className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                style={{
                  backgroundColor: OZ_TRACT_SWATCH.designated,
                  boxShadow: "inset 0 0 0 1px #f6d0b0",
                }}
              />
              Designated QOZ (2018), dashed
            </p>
          ) : null}
          </div>
        </div>
      ) : null}
      {status !== "ready" ? (
        <div className="absolute inset-0 flex items-center justify-center bg-ink-950/80">
          <div className="rounded-2xl border border-white/10 bg-ink-900 px-5 py-4 text-sm">
            <p className="font-medium text-white">{status === "error" ? "Map error" : "Loading map"}</p>
            <p className="mt-1 text-ink-300">{message}</p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
