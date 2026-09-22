"use client";

import maplibregl, { type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { BasemapToggle } from "./BasemapToggle";
import {
  STREET_STYLE_CANDIDATES,
  addSatelliteSourceAndLayer,
  applyBasemap,
  excludedFillPaint,
  excludedLinePaint,
  OZ_TRACT_SWATCH,
  oz2FillPaint,
  oz2LinePaint,
  ozFillPaint,
  ozLinePaint,
  parcelFillPaint,
  parcelLinePaint,
  ruralPinPaint,
  trafficLinePaint,
  type BasemapMode,
} from "@/lib/basemap";
import { ORANGE_COUNTY_CENTER, type MarketId, type OpportunityZoneCollection, type Oz2TractCollection, type OzFilter, type ParcelCollection, type RuralMarketTractCollection } from "@/lib/types";

type LngLatBounds = [[number, number], [number, number]];

type SiteMapProps = {
  parcels: ParcelCollection;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  opportunityZones: OpportunityZoneCollection;
  oz2Tracts: Oz2TractCollection;
  ruralTracts: RuralMarketTractCollection;
  ruralPins: GeoJSON.FeatureCollection<GeoJSON.Point>;
  matchedIds: Set<string>;
  selectedId: string | null;
  hoveredId: string | null;
  selectedTractGeoid: string | null;
  showExcluded: boolean;
  showTraffic: boolean;
  showOz: boolean;
  showOz2: boolean;
  showOrangePilot: boolean;
  market: MarketId;
  county: string | null;
  countyState: string | null;
  bounds: LngLatBounds;
  boundsKey: string;
  ozFilter: OzFilter;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  onSelectTract: (geoid: string) => void;
};

function ruralLayerFilter(
  market: MarketId,
  county: string | null,
  countyState: string | null,
  hideOrangeCounty: boolean,
): maplibregl.FilterSpecification {
  const parts: maplibregl.FilterSpecification[] = [["in", ["literal", market], ["get", "markets"]]];
  if (county && countyState) {
    parts.push(["==", ["get", "county"], county]);
    parts.push(["==", ["get", "state"], countyState]);
  }
  if (hideOrangeCounty) {
    parts.push(["!", ["all", ["==", ["get", "state"], "Florida"], ["==", ["get", "county"], "Orange"]]]);
  }
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
}

export function SiteMap({
  parcels,
  traffic,
  opportunityZones,
  oz2Tracts,
  ruralTracts,
  ruralPins,
  matchedIds,
  selectedId,
  hoveredId,
  selectedTractGeoid,
  showExcluded,
  showTraffic,
  showOz,
  showOz2,
  showOrangePilot,
  market,
  county,
  countyState,
  bounds,
  boundsKey,
  ozFilter,
  onSelect,
  onHover,
  onSelectTract,
}: SiteMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("Loading map…");
  const [basemap, setBasemap] = useState<BasemapMode>("streets");
  const callbacksRef = useRef({ onSelect, onHover, onSelectTract });
  callbacksRef.current = { onSelect, onHover, onSelectTract };
  const basemapRef = useRef(basemap);
  basemapRef.current = basemap;
  const boundsRef = useRef(bounds);
  boundsRef.current = bounds;
  const ruralPinsRef = useRef(ruralPins);
  ruralPinsRef.current = ruralPins;

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
            const id = event.features?.[0]?.properties?.id;
            if (typeof id === "string") callbacksRef.current.onSelect(id);
          });
          const tractLayers = ["rural-fill", "rural-pins", "oz2-fill"];
          map.on("click", tractLayers, (event) => {
            const parcelHit = map.queryRenderedFeatures(event.point, { layers: interactive });
            if (parcelHit.length > 0) return;
            const props = event.features?.[0]?.properties;
            const geoid = props?.tractGeoid;
            const rural = props?.rural === true || props?.rural === "true";
            if (rural && typeof geoid === "string") callbacksRef.current.onSelectTract(geoid);
          });
          map.on("mousemove", interactive, (event) => {
            map.getCanvas().style.cursor = "pointer";
            const id = event.features?.[0]?.properties?.id;
            callbacksRef.current.onHover(typeof id === "string" ? id : null);
          });
          map.on("mouseleave", interactive, () => {
            map.getCanvas().style.cursor = "";
            callbacksRef.current.onHover(null);
          });

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
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // Pins update through setData. Keeping them out of this effect avoids remounting the map.
  }, [parcels, traffic, opportunityZones, oz2Tracts, ruralTracts]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const ids = Array.from(matchedIds);
    const matchedFilter: maplibregl.FilterSpecification =
      ids.length === 0 ? ["==", ["get", "id"], "__none__"] : ["in", ["get", "id"], ["literal", ids]];
    const excludedFilter: maplibregl.FilterSpecification = ["!", matchedFilter];
    const none: maplibregl.FilterSpecification = ["==", ["get", "id"], "__none__"];
    map.setFilter("parcels-fill", showOrangePilot ? matchedFilter : none);
    map.setFilter("parcels-line", showOrangePilot ? matchedFilter : none);
    map.setFilter("parcels-fill-excluded", showOrangePilot && showExcluded ? excludedFilter : none);
    map.setFilter("parcels-line-excluded", showOrangePilot && showExcluded ? excludedFilter : none);
    map.setLayoutProperty("traffic-line", "visibility", showOrangePilot && showTraffic ? "visible" : "none");
    map.setLayoutProperty("oz-fill", "visibility", showOrangePilot && showOz ? "visible" : "none");
    map.setLayoutProperty("oz-line", "visibility", showOrangePilot && showOz ? "visible" : "none");
    map.setLayoutProperty("oz2-fill", "visibility", showOrangePilot && showOz2 ? "visible" : "none");
    map.setLayoutProperty("oz2-line", "visibility", showOrangePilot && showOz2 ? "visible" : "none");
    const showRuralMarkets = showOz2 && ozFilter !== "non-rural-eligible";
    map.setLayoutProperty("rural-fill", "visibility", showRuralMarkets ? "visible" : "none");
    map.setLayoutProperty("rural-line", "visibility", showRuralMarkets ? "visible" : "none");
    map.setLayoutProperty("rural-pins", "visibility", showRuralMarkets ? "visible" : "none");
    const oz2Filter: maplibregl.FilterSpecification | null =
      ozFilter === "rural-eligible"
        ? ["==", ["get", "rural"], true]
        : ozFilter === "non-rural-eligible"
          ? ["==", ["get", "rural"], false]
          : null;
    map.setFilter("oz2-fill", oz2Filter);
    map.setFilter("oz2-line", oz2Filter);
    const ruralFilter = ruralLayerFilter(market, county, countyState, showOrangePilot);
    map.setFilter("rural-fill", ruralFilter);
    map.setFilter("rural-line", ruralFilter);
  }, [matchedIds, showExcluded, showTraffic, showOz, showOz2, showOrangePilot, ozFilter, market, county, countyState, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
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

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {status === "ready" ? <BasemapToggle value={basemap} onChange={setBasemap} /> : null}
      {status === "ready" && (showOz || showOz2) ? (
        <div className="pointer-events-none absolute bottom-3 left-3 z-10 max-w-[16rem] space-y-1 rounded-lg border border-white/10 bg-ink-900/90 px-2 py-1.5 text-[10px] leading-snug text-ink-300 sm:bottom-4 sm:left-4">
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
            </>
          ) : null}
          <p className="text-ink-500">Pins mark tract internal points. 90-minute sheds are approximate county rings, not drive-time isochrones.</p>
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
