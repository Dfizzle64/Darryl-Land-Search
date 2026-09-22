"use client";

import maplibregl, { type GeoJSONSource, type Map as MapLibreMap, type MapMouseEvent, type MapTouchEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { aoiFeatureCollection, normalizeBbox, type AoiLock } from "@/lib/aoi";
import { BasemapToggle } from "./BasemapToggle";
import { AoiControls } from "./AoiControls";
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
import { southCarolinaStatusHelp } from "@/lib/markets";
import { ORANGE_COUNTY_CENTER, SC_GOVERNOR_FILED_STATUS, type MarketId, type OpportunityZoneCollection, type Oz2TractCollection, type OzFilter, type ParcelCollection, type RuralMarketTractCollection } from "@/lib/types";

type LngLatBounds = [[number, number], [number, number]];

type SiteMapProps = {
  parcels: ParcelCollection;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  opportunityZones: OpportunityZoneCollection;
  oz2Tracts: Oz2TractCollection;
  ruralTracts: RuralMarketTractCollection;
  ruralPins: GeoJSON.FeatureCollection<GeoJSON.Point>;
  selectedId: string | null;
  hoveredId: string | null;
  selectedTractGeoid: string | null;
  showExcluded: boolean;
  showTraffic: boolean;
  showOz: boolean;
  showOz2: boolean;
  showParcels: boolean;
  parcelLayerVisible?: boolean;
  parcelVisibilityHint?: string;
  onToggleParcelLayer?: () => void;
  showOrangePilot: boolean;
  parcelsLoading?: boolean;
  market: MarketId;
  county: string | null;
  countyState: string | null;
  bounds: LngLatBounds;
  boundsKey: string;
  ozFilter: OzFilter;
  highlightTierA: string[];
  highlightTierB: string[];
  restrictGeoids: string[] | null;
  showMfLegend: boolean;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  onSelectTract: (geoid: string) => void;
  onViewportIdle?: (bbox: [number, number, number, number], zoom: number) => void;
  onZoom?: (zoom: number) => void;
  aoi?: AoiLock | null;
  aoiMatchedCount?: number;
  aoiTruncated?: boolean;
  onAoiChange?: (aoi: AoiLock | null) => void;
};

function geoidMatch(geoids: string[]): maplibregl.FilterSpecification {
  if (geoids.length === 0) return ["==", ["get", "tractGeoid"], "__none__"];
  return ["in", ["get", "tractGeoid"], ["literal", geoids]];
}

function ruralLayerFilter(
  market: MarketId,
  county: string | null,
  countyState: string | null,
  hideOrangeCounty: boolean,
  geoids: string[] | null = null,
): maplibregl.FilterSpecification {
  const parts: maplibregl.FilterSpecification[] = [["in", ["literal", market], ["get", "markets"]]];
  if (county && countyState) {
    parts.push(["==", ["get", "county"], county]);
    parts.push(["==", ["get", "state"], countyState]);
  }
  if (hideOrangeCounty) {
    parts.push(["!", ["all", ["==", ["get", "state"], "Florida"], ["==", ["get", "county"], "Orange"]]]);
  }
  if (geoids) parts.push(geoidMatch(geoids));
  if (parts.length === 1) return parts[0];
  return ["all", ...parts] as maplibregl.FilterSpecification;
}

function addOverlayLayers(
  map: MapLibreMap,
  parcels: ParcelCollection,
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>,
  opportunityZones: OpportunityZoneCollection,
  oz2Tracts: Oz2TractCollection,
  ruralTracts: RuralMarketTractCollection,
  ruralPins: GeoJSON.FeatureCollection<GeoJSON.Point>,
  mode: BasemapMode,
) {
  map.addSource("rural-tracts", { type: "geojson", data: ruralTracts, promoteId: "tractGeoid" });
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
}

export function SiteMap({
  parcels,
  traffic,
  opportunityZones,
  oz2Tracts,
  ruralTracts,
  ruralPins,
  selectedId,
  hoveredId,
  selectedTractGeoid,
  showExcluded,
  showTraffic,
  showOz,
  showOz2,
  showParcels,
  parcelLayerVisible,
  parcelVisibilityHint,
  onToggleParcelLayer,
  showOrangePilot,
  parcelsLoading = false,
  market,
  county,
  countyState,
  bounds,
  boundsKey,
  ozFilter,
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
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("Loading map…");
  const [basemap, setBasemap] = useState<BasemapMode>("streets");
  const [drawing, setDrawing] = useState(false);
  const callbacksRef = useRef({ onSelect, onHover, onSelectTract, onViewportIdle, onZoom, onAoiChange });
  callbacksRef.current = { onSelect, onHover, onSelectTract, onViewportIdle, onZoom, onAoiChange };
  const drawingRef = useRef(drawing);
  drawingRef.current = drawing;
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
          });
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
          addOverlayLayers(map, parcels, traffic, opportunityZones, oz2Tracts, ruralTracts, ruralPinsRef.current, basemapRef.current);
          addSatelliteSourceAndLayer(map);
          applyBasemap(map, basemapRef.current);

          const interactive = ["parcels-fill", "parcels-fill-excluded"];
          map.on("click", interactive, (event) => {
            if (drawingRef.current) return;
            const id = event.features?.[0]?.properties?.id;
            if (typeof id === "string") callbacksRef.current.onSelect(id);
          });
          const tractLayers = ["mf-priority-a-fill", "mf-priority-b-fill", "rural-fill", "rural-pins", "oz2-fill"];
          map.on("click", tractLayers, (event) => {
            if (drawingRef.current) return;
            const parcelHit = map.queryRenderedFeatures(event.point, { layers: interactive });
            if (parcelHit.length > 0) return;
            const props = event.features?.[0]?.properties;
            const geoid = props?.tractGeoid;
            const rural = props?.rural === true || props?.rural === "true";
            if (rural && typeof geoid === "string") callbacksRef.current.onSelectTract(geoid);
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
            callbacksRef.current.onZoom?.(map.getZoom());
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
  }, [traffic, opportunityZones, oz2Tracts, ruralTracts]);

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
    if (!map || status !== "ready" || !drawing) return;

    map.dragPan.disable();
    map.boxZoom.disable();
    map.doubleClickZoom.disable();
    map.scrollZoom.disable();
    map.touchZoomRotate.disable();
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
        map.dragPan.enable();
        map.boxZoom.enable();
        map.doubleClickZoom.enable();
        map.scrollZoom.enable();
        map.touchZoomRotate.enable();
        canvas.style.cursor = "";
      } catch {
        // Map already removed.
      }
    };
  }, [drawing, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const layerOn = parcelLayerVisible ?? showParcels;
    map.setFilter("parcels-fill", layerOn ? parcelMatchFilter : parcelHiddenFilter);
    map.setFilter("parcels-line", layerOn ? parcelMatchFilter : parcelHiddenFilter);
    map.setFilter("parcels-fill-excluded", layerOn && showExcluded ? parcelExcludedFilter : parcelHiddenFilter);
    map.setFilter("parcels-line-excluded", layerOn && showExcluded ? parcelExcludedFilter : parcelHiddenFilter);
    map.setLayoutProperty("traffic-line", "visibility", showOrangePilot && showTraffic ? "visible" : "none");
    map.setLayoutProperty("oz-fill", "visibility", showOrangePilot && showOz ? "visible" : "none");
    map.setLayoutProperty("oz-line", "visibility", showOrangePilot && showOz ? "visible" : "none");
    map.setLayoutProperty("oz2-fill", "visibility", showOrangePilot && showOz2 ? "visible" : "none");
    map.setLayoutProperty("oz2-line", "visibility", showOrangePilot && showOz2 ? "visible" : "none");
    const showRuralMarkets = showOz2 && ozFilter !== "non-rural-eligible";
    map.setLayoutProperty("rural-fill", "visibility", showRuralMarkets ? "visible" : "none");
    map.setLayoutProperty("rural-line", "visibility", showRuralMarkets ? "visible" : "none");
    map.setLayoutProperty("rural-pins", "visibility", showRuralMarkets ? "visible" : "none");
    for (const layerId of ["mf-priority-a-fill", "mf-priority-a-line", "mf-priority-b-fill", "mf-priority-b-line"]) {
      map.setLayoutProperty(layerId, "visibility", showRuralMarkets ? "visible" : "none");
    }
    const oz2Filter: maplibregl.FilterSpecification | null =
      ozFilter === "rural-eligible"
        ? ["==", ["get", "rural"], true]
        : ozFilter === "non-rural-eligible"
          ? ["==", ["get", "rural"], false]
          : null;
    map.setFilter("oz2-fill", oz2Filter);
    map.setFilter("oz2-line", oz2Filter);
    const ruralFilter = ruralLayerFilter(market, county, countyState, showOrangePilot, restrictGeoids);
    map.setFilter("rural-fill", ruralFilter);
    map.setFilter("rural-line", ruralFilter);
    const tierAFilter = ruralLayerFilter(market, county, countyState, showOrangePilot, highlightTierA);
    const tierBFilter = ruralLayerFilter(market, county, countyState, showOrangePilot, highlightTierB);
    map.setFilter("mf-priority-a-fill", tierAFilter);
    map.setFilter("mf-priority-a-line", tierAFilter);
    map.setFilter("mf-priority-b-fill", tierBFilter);
    map.setFilter("mf-priority-b-line", tierBFilter);
  }, [
    parcelLayerVisible,
    showExcluded,
    showTraffic,
    showOz,
    showOz2,
    showParcels,
    showOrangePilot,
    ozFilter,
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
    map.setLayoutProperty("traffic-line", "visibility", showOrangePilot && showTraffic ? "visible" : "none");
    map.setLayoutProperty("oz-fill", "visibility", showOrangePilot && showOz ? "visible" : "none");
    map.setLayoutProperty("oz-line", "visibility", showOrangePilot && showOz ? "visible" : "none");
    map.setLayoutProperty("oz2-fill", "visibility", showOrangePilot && showOz2 ? "visible" : "none");
    map.setLayoutProperty("oz2-line", "visibility", showOrangePilot && showOz2 ? "visible" : "none");
    const showRuralMarkets = showOz2 && ozFilter !== "non-rural-eligible";
    map.setLayoutProperty("rural-fill", "visibility", showRuralMarkets ? "visible" : "none");
    map.setLayoutProperty("rural-line", "visibility", showRuralMarkets ? "visible" : "none");
    map.setLayoutProperty("rural-pins", "visibility", showRuralMarkets ? "visible" : "none");
    for (const layerId of ["mf-priority-a-fill", "mf-priority-a-line", "mf-priority-b-fill", "mf-priority-b-line"]) {
      map.setLayoutProperty(layerId, "visibility", showRuralMarkets ? "visible" : "none");
    }
  }, [basemap, showTraffic, showOz, showOz2, showOrangePilot, ozFilter, status]);

  const previousHover = useRef<string | null>(null);
  const previousSelected = useRef<string | null>(null);

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
      const feature = parcels.features.find((item) => item.properties.id === selectedId);
      if (feature) {
        const [lng, lat] = feature.properties.centroid;
        map.easeTo({ center: [lng, lat], zoom: Math.max(map.getZoom(), 13), duration: 500 });
      }
    }
    previousSelected.current = selectedId;
  }, [selectedId, parcels.features, status]);

  const previousTract = useRef<string | null>(null);
  const skipInitialFit = useRef(true);
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
    if (skipInitialFit.current) {
      skipInitialFit.current = false;
      return;
    }
    map.fitBounds(bounds, { padding: 56, duration: 650, maxZoom: 11 });
  }, [bounds, boundsKey, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    if (previousTract.current) {
      for (const source of ["rural-tracts", "rural-pins"] as const) {
        map.setFeatureState({ source, id: previousTract.current }, { selected: false });
      }
    }
    if (selectedTractGeoid) {
      for (const source of ["rural-tracts", "rural-pins"] as const) {
        map.setFeatureState({ source, id: selectedTractGeoid }, { selected: true });
      }
      const pin = ruralPins.features.find((feature) => feature.properties?.tractGeoid === selectedTractGeoid);
      const coordinates = pin?.geometry?.coordinates;
      if (coordinates && coordinates.length >= 2) {
        map.easeTo({
          center: [coordinates[0], coordinates[1]],
          zoom: Math.max(map.getZoom(), 10),
          duration: 500,
        });
      }
    }
    previousTract.current = selectedTractGeoid;
  }, [selectedTractGeoid, ruralPins.features, status]);

  useEffect(() => {
    mapRef.current?.resize();
  }, [selectedId, selectedTractGeoid]);

  const scStatusHelp = southCarolinaStatusHelp(market, countyState);
  const layerOn = parcelLayerVisible ?? showParcels;

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {status === "ready" ? <BasemapToggle value={basemap} onChange={setBasemap} /> : null}
      {status === "ready" && showParcels && onToggleParcelLayer ? (
        <ParcelLayerToggle visible={layerOn} hint={parcelVisibilityHint ?? ""} onToggle={onToggleParcelLayer} />
      ) : null}
      {status === "ready" && showParcels ? (
        <AoiControls
          drawing={drawing}
          aoi={aoi}
          matchedCount={aoiMatchedCount}
          truncated={aoiTruncated}
          loading={parcelsLoading && Boolean(aoi)}
          onDraw={() => setDrawing(true)}
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
      {status === "ready" && (showOz || showOz2 || showParcels) ? (
        <div className="pointer-events-none absolute bottom-3 left-3 z-10 max-w-[20rem] space-y-1 rounded-lg border border-white/10 bg-ink-900/90 px-2 py-1.5 text-[10px] leading-snug text-ink-300 sm:bottom-4 sm:left-4">
          {aoi ? (
            <p>
              <span className="mr-1.5 inline-block h-2 w-3 border border-dashed border-clay-400 align-middle" />
              Area of interest
            </p>
          ) : null}
          {layerOn ? (
            <p>
              <span className="mr-1.5 inline-block h-2 w-2 rounded-sm align-middle bg-moss-400" />
              Parcels (matched)
              {parcelsLoading ? (aoi ? " · loading AOI…" : " · refreshing viewport…") : aoi ? " · AOI locked" : ""}
            </p>
          ) : null}
          {showOz2 ? (
            <>
              <p>
                <span
                  className="mr-1.5 inline-block h-2 w-2 rounded-sm align-middle"
                  style={{ backgroundColor: OZ_TRACT_SWATCH.rural }}
                />
                Eligible (rural) — not designated
              </p>
              {showOrangePilot ? (
                <p>
                  <span
                    className="mr-1.5 inline-block h-2 w-2 rounded-sm align-middle"
                    style={{ backgroundColor: OZ_TRACT_SWATCH.eligible }}
                  />
                  OZ 2.0 eligible, not rural (Orange County)
                </p>
              ) : null}
              {showMfLegend ? (
                <>
                  <p>
                    <span
                      className="mr-1.5 inline-block h-2 w-2 rounded-sm align-middle"
                      style={{ backgroundColor: MF_PRIORITY_SWATCH.tierA }}
                    />
                    SC MF priority · Tier A
                  </p>
                  <p>
                    <span
                      className="mr-1.5 inline-block h-2 w-2 rounded-sm align-middle"
                      style={{ backgroundColor: MF_PRIORITY_SWATCH.tierB }}
                    />
                    SC MF priority · Tier B
                  </p>
                </>
              ) : null}
            </>
          ) : null}
          <p className="text-ink-500">Pins mark tract internal points. 90-minute sheds are approximate county rings, not drive-time isochrones.</p>
          {scStatusHelp ? (
            <SouthCarolinaStatusNote note={SC_GOVERNOR_FILED_STATUS} className="text-ink-300" />
          ) : null}
          {showOz ? (
            <p>
              <span
                className="mr-1.5 inline-block h-2 w-2 rounded-sm align-middle"
                style={{
                  backgroundColor: OZ_TRACT_SWATCH.designated,
                  boxShadow: "inset 0 0 0 1px #f6d0b0",
                }}
              />
              Designated QOZ (2018), dashed
            </p>
          ) : null}
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
