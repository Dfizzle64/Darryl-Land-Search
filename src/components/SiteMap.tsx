"use client";

import maplibregl, { type GeoJSONSource, type Map as MapLibreMap, type MapMouseEvent, type MapTouchEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { aoiFeatureCollection, normalizeBbox, type AoiLock } from "@/lib/aoi";
import { applyMapGestures } from "@/lib/mapGestures";
import { BasemapToggle } from "./BasemapToggle";
import { AoiControls } from "./AoiControls";
import { MeasureControl } from "./MeasureControl";
import { ParcelLayerToggle } from "./ParcelLayerToggle";
import { SouthCarolinaStatusNote } from "./SouthCarolinaStatusNote";
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
  ruralPinPaint,
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
import { eligibleClassCut, southCarolinaStatusHelp } from "@/lib/markets";
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
import { tractClickFromFeature, type TractClickDetails } from "@/lib/tractCounty";
import { tractIncomeLayerFilter } from "@/lib/tractIncome";
import { ORANGE_COUNTY_CENTER, SC_GOVERNOR_FILED_STATUS, type EligiblePackTractCollection, type IncomeGeography, type OpportunityZoneCollection, type Oz2TractCollection, type OzFilter, type ParcelCollection, type RuralMarketTractCollection, type SearchMarketId, type TractClassView } from "@/lib/types";

type LngLatBounds = [[number, number], [number, number]];

type SiteMapProps = {
  parcels: ParcelCollection;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  opportunityZones: OpportunityZoneCollection;
  oz2Tracts: Oz2TractCollection;
  ruralTracts: RuralMarketTractCollection;
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
  showOrangePilot: boolean;
  parcelsLoading?: boolean;
  market: SearchMarketId;
  tractClass: TractClassView;
  onTractClass: (view: TractClassView) => void;
  county: string | null;
  countyState: string | null;
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

function geoidMatch(geoids: string[]): maplibregl.FilterSpecification {
  if (geoids.length === 0) return ["==", ["get", "tractGeoid"], "__none__"];
  return ["in", ["get", "tractGeoid"], ["literal", geoids]];
}

function andFilter(
  base: maplibregl.FilterSpecification | null,
  extra: maplibregl.FilterSpecification | null,
): maplibregl.FilterSpecification | null {
  if (!extra) return base;
  if (!base) return extra;
  return ["all", base, extra] as maplibregl.FilterSpecification;
}

function ruralLayerFilter(
  market: SearchMarketId,
  county: string | null,
  countyState: string | null,
  hideOrangeCounty: boolean,
  geoids: string[] | null = null,
  classCut: "all" | "rural" | "urban" | "none" = "all",
): maplibregl.FilterSpecification {
  const parts: maplibregl.FilterSpecification[] = [["in", ["literal", market], ["get", "markets"]]];
  if (county && countyState) {
    parts.push(["==", ["get", "county"], county]);
    parts.push(["==", ["get", "state"], countyState]);
  }
  if (hideOrangeCounty) {
    parts.push(["!", ["all", ["==", ["get", "state"], "Florida"], ["==", ["get", "county"], "Orange"]]]);
  }
  if (classCut === "none") parts.push(["==", ["get", "tractGeoid"], "__none__"]);
  if (classCut === "urban") parts.push(["==", ["get", "rural"], false]);
  if (classCut === "rural") parts.push(["==", ["get", "rural"], true]);
  if (geoids) parts.push(geoidMatch(geoids));
  if (parts.length === 1) return parts[0];
  return ["all", ...parts] as maplibregl.FilterSpecification;
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
  oz2Tracts: Oz2TractCollection,
  ruralTracts: RuralMarketTractCollection,
  eligibleTracts: EligiblePackTractCollection,
  ruralPins: GeoJSON.FeatureCollection<GeoJSON.Point>,
  mode: BasemapMode,
) {
  addScreeningLayers(map, mode);
  map.addSource("rural-tracts", { type: "geojson", data: ruralTracts, promoteId: "tractGeoid" });
  map.addSource("eligible-tracts", { type: "geojson", data: eligibleTracts, promoteId: "tractGeoid" });
  map.addSource("rural-pins", { type: "geojson", data: ruralPins, promoteId: "tractGeoid" });
  map.addSource("oz2-tracts", { type: "geojson", data: oz2Tracts, promoteId: "tractGeoid" });
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
    id: "rural-pins",
    type: "circle",
    source: "rural-pins",
    paint: ruralPinPaint(mode),
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
}

function showTractPopup(map: MapLibreMap, lngLat: maplibregl.LngLatLike, details: TractClickDetails) {
  const root = document.createElement("div");
  const place = document.createElement("p");
  place.style.fontWeight = "600";
  place.textContent = details.placeLabel;
  const geoid = document.createElement("p");
  geoid.textContent = `GEOID ${details.geoid}`;
  const status = document.createElement("p");
  status.textContent = details.status;
  const rural = document.createElement("p");
  rural.textContent = details.ruralLabel;
  root.append(place, geoid, status, rural);
  return new maplibregl.Popup({ closeButton: true, maxWidth: "280px", closeOnClick: false })
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
  showOrangePilot,
  parcelsLoading = false,
  market,
  tractClass,
  onTractClass,
  county,
  countyState,
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
  const idleTimer = useRef<number | null>(null);

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
          map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "bottom-right");
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
            oz2Tracts,
            ruralTracts,
            eligibleTracts,
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
            name.textContent = String(props.name ?? "School");
            const summary = document.createElement("p");
            summary.textContent = String(props.summary ?? "");
            root.append(name, summary);
            const href = typeof props.reportCardUrl === "string" ? props.reportCardUrl : "";
            if (href.startsWith("https://")) {
              const link = document.createElement("a");
              link.href = href;
              link.target = "_blank";
              link.rel = "noreferrer";
              link.textContent = "Official report card";
              root.append(link);
            }
            popupRef.current?.remove();
            popupRef.current = new maplibregl.Popup({ closeButton: true, maxWidth: "280px" })
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
          const tractLayers = ["mf-priority-a-fill", "mf-priority-b-fill", "eligible-fill", "rural-fill", "rural-pins", "oz2-fill", "oz-fill"];
          map.on("click", tractLayers, (event) => {
            if (drawingRef.current || measuringRef.current) return;
            const feature = event.features?.[0];
            const details = tractClickFromFeature({
              layerId: feature?.layer.id ?? "",
              properties: (feature?.properties ?? null) as Record<string, unknown> | null,
            });
            if (!details) return;
            const parcelHit = queryRendered(map, event.point, interactive);
            if (parcelHit.length > 0) {
              popupRef.current?.remove();
              popupRef.current = showTractPopup(map, event.lngLat, details);
              return;
            }
            if (details.kind === "eligible") {
              callbacksRef.current.onSelectTract(details.geoid);
              popupRef.current?.remove();
              popupRef.current = details.opensRuralDrawer ? null : showTractPopup(map, event.lngLat, details);
              return;
            }
            callbacksRef.current.onSelectTract(null);
            popupRef.current?.remove();
            popupRef.current = showTractPopup(map, event.lngLat, details);
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
          const emitZoom = () => {
            const zoomNow = map.getZoom();
            containerRef.current?.setAttribute("data-map-zoom", zoomNow.toFixed(2));
            callbacksRef.current.onZoom?.(zoomNow);
          };
          const emitViewport = () => {
            emitZoom();
            if (drawingRef.current || aoiRef.current) return;
            const cb = callbacksRef.current.onViewportIdle;
            if (!cb) return;
            const b = map.getBounds();
            cb([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()], map.getZoom());
          };
          map.on("zoom", emitZoom);
          map.on("moveend", () => {
            if (idleTimer.current) window.clearTimeout(idleTimer.current);
            idleTimer.current = window.setTimeout(emitViewport, 450);
          });
          emitViewport();

          mapRef.current = map;
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
    // Parcels / pins update through setData — remounting the map on every viewport refresh freezes the UI.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally omit parcels; see setData effect below
  }, [traffic, opportunityZones, oz2Tracts, ruralTracts, eligibleTracts]);

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
    const showRuralLayer = showOz2 && tractClass !== "urban" && ozFilter !== "non-rural-eligible";
    const showEligibleLayer = showOz2 && restrictGeoids == null && classCut !== "none";
    setVisibilitySafe(map, "rural-fill", showRuralLayer ? "visible" : "none");
    setVisibilitySafe(map, "rural-line", showRuralLayer ? "visible" : "none");
    setVisibilitySafe(map, "eligible-fill", showEligibleLayer ? "visible" : "none");
    setVisibilitySafe(map, "eligible-line", showEligibleLayer ? "visible" : "none");
    setVisibilitySafe(map, "rural-pins", showOz2 ? "visible" : "none");
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
    setFilterSafe(map, "oz2-fill", andFilter(oz2Filter, incomeFilter));
    setFilterSafe(map, "oz2-line", andFilter(oz2Filter, incomeFilter));
    const ruralFilter = ruralLayerFilter(market, county, countyState, showOrangePilot, restrictGeoids);
    setFilterSafe(map, "rural-fill", andFilter(ruralFilter, incomeFilter));
    setFilterSafe(map, "rural-line", andFilter(ruralFilter, incomeFilter));
    const eligibleFilter = ruralLayerFilter(market, county, countyState, showOrangePilot, null, classCut);
    setFilterSafe(map, "eligible-fill", andFilter(eligibleFilter, incomeFilter));
    setFilterSafe(map, "eligible-line", andFilter(eligibleFilter, incomeFilter));
    const tierAFilter = ruralLayerFilter(market, county, countyState, showOrangePilot, highlightTierA);
    const tierBFilter = ruralLayerFilter(market, county, countyState, showOrangePilot, highlightTierB);
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
    market,
    county,
    countyState,
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
    const showRuralLayer = showOz2 && tractClass !== "urban" && ozFilter !== "non-rural-eligible";
    const showEligibleLayer = showOz2 && restrictGeoids == null && classCut !== "none";
    setVisibilitySafe(map, "rural-fill", showRuralLayer ? "visible" : "none");
    setVisibilitySafe(map, "rural-line", showRuralLayer ? "visible" : "none");
    setVisibilitySafe(map, "eligible-fill", showEligibleLayer ? "visible" : "none");
    setVisibilitySafe(map, "eligible-line", showEligibleLayer ? "visible" : "none");
    setVisibilitySafe(map, "rural-pins", showOz2 ? "visible" : "none");
    for (const layerId of ["mf-priority-a-fill", "mf-priority-a-line", "mf-priority-b-fill", "mf-priority-b-line"]) {
      setVisibilitySafe(map, layerId, showRuralLayer ? "visible" : "none");
    }
  }, [basemap, showTraffic, showOz, showOz2, showOrangePilot, ozFilter, tractClass, restrictGeoids, status]);

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
          setCollection(sourceId, EMPTY_COLLECTION);
          return;
        }
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

  const scStatusHelp = southCarolinaStatusHelp(market, countyState);
  const layerOn = parcelLayerVisible ?? showParcels;

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
      {status === "ready" && showParcels && !layerOn ? (
        <div className="map-chrome absolute inset-x-3 top-28 z-20 flex justify-center sm:top-24">
          <div
            data-parcel-banner
            className="map-scrim max-w-md rounded-xl border px-3 py-2 text-center"
          >
            <p className="text-sm font-medium text-clay-400">Parcels are hidden</p>
            <p className="mt-1 text-xs leading-snug text-ink-100">
              {parcelVisibilityHint || "Zoom in to neighborhood level, lock an area, or turn Show parcels on."}
            </p>
          </div>
        </div>
      ) : null}
      {status === "ready" && (showOz || showOz2 || showParcels || screening.flood || screening.wetlands || screening.schools || screening.water || screening.sewer || screening.power) ? (
        <div className="map-chrome map-scrim absolute bottom-3 left-3 z-10 max-w-[17rem] rounded-xl border sm:bottom-4 sm:left-4 sm:max-w-[22rem]">
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
              <p>
                <span
                  className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                  style={{ backgroundColor: OZ_TRACT_SWATCH.rural }}
                />
                Rural eligible — not designated
              </p>
              <p>
                <span
                  className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                  style={{ backgroundColor: OZ_TRACT_SWATCH.urban }}
                />
                Urban eligible — not designated
              </p>
              {showOrangePilot ? (
                <p>
                  <span
                    className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                    style={{ backgroundColor: OZ_TRACT_SWATCH.eligible }}
                  />
                  Orange County urban eligible (amber overlay)
                </p>
              ) : null}
              {showMfLegend ? (
                <>
                  <p>
                    <span
                      className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                      style={{ backgroundColor: MF_PRIORITY_SWATCH.tierA }}
                    />
                    SC MF priority · Tier A
                  </p>
                  <p>
                    <span
                      className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle"
                      style={{ backgroundColor: MF_PRIORITY_SWATCH.tierB }}
                    />
                    SC MF priority · Tier B
                  </p>
                </>
              ) : null}
            </>
          ) : null}
          <p className="text-xs text-ink-100">Pins mark tract internal points. 90-minute sheds are approximate county rings, not drive-time isochrones.</p>
          {scStatusHelp ? (
            <SouthCarolinaStatusNote note={SC_GOVERNOR_FILED_STATUS} className="text-ink-300" />
          ) : null}
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
              Water service area (Orange County only)
            </p>
          ) : null}
          {screening.sewer ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle" style={{ backgroundColor: "#7a5cff" }} />
              Sewer service area (Orange County only)
            </p>
          ) : null}
          {screening.power ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-3.5 rounded-sm align-middle" style={{ backgroundColor: "#e0b15a" }} />
              Electric service area (Orange County; retail territory elsewhere)
            </p>
          ) : null}
          {screening.schools ? (
            <p>
              <span className="mr-2 inline-block h-3.5 w-3.5 rounded-full align-middle" style={{ backgroundColor: "#1f7a4d" }} />
              Schools · letter grade where published, CCRPI on Cobb and DeKalb batch parcels, OCPS / CMS / CCSD / DCSD zones
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
