"use client";

import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { BasemapToggle } from "./BasemapToggle";
import {
  STREET_STYLE_CANDIDATES,
  addSatelliteSourceAndLayer,
  applyBasemap,
  excludedFillPaint,
  excludedLinePaint,
  oz2FillPaint,
  oz2LinePaint,
  ozFillPaint,
  ozLinePaint,
  parcelFillPaint,
  parcelLinePaint,
  trafficLinePaint,
  type BasemapMode,
} from "@/lib/basemap";
import {
  ORANGE_COUNTY_BOUNDS,
  ORANGE_COUNTY_CENTER,
  type OpportunityZoneCollection,
  type Oz2TractCollection,
  type OzFilter,
  type ParcelCollection,
} from "@/lib/types";

type SiteMapProps = {
  parcels: ParcelCollection;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  opportunityZones: OpportunityZoneCollection;
  oz2Tracts: Oz2TractCollection;
  matchedIds: Set<string>;
  selectedId: string | null;
  hoveredId: string | null;
  showExcluded: boolean;
  showTraffic: boolean;
  showOz: boolean;
  showOz2: boolean;
  ozFilter: OzFilter;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
};

function addOverlayLayers(
  map: MapLibreMap,
  parcels: ParcelCollection,
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>,
  opportunityZones: OpportunityZoneCollection,
  oz2Tracts: Oz2TractCollection,
  mode: BasemapMode,
) {
  map.addSource("oz2-tracts", { type: "geojson", data: oz2Tracts });
  map.addSource("opportunity-zones", { type: "geojson", data: opportunityZones });
  map.addSource("parcels", { type: "geojson", data: parcels, promoteId: "id" });
  map.addSource("traffic", { type: "geojson", data: traffic });

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
  matchedIds,
  selectedId,
  hoveredId,
  showExcluded,
  showTraffic,
  showOz,
  showOz2,
  ozFilter,
  onSelect,
  onHover,
}: SiteMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("Loading Orange County map…");
  const [basemap, setBasemap] = useState<BasemapMode>("streets");
  const callbacksRef = useRef({ onSelect, onHover });
  callbacksRef.current = { onSelect, onHover };
  const basemapRef = useRef(basemap);
  basemapRef.current = basemap;

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
          map.fitBounds(ORANGE_COUNTY_BOUNDS, { padding: 48, duration: 0 });
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
          addOverlayLayers(map, parcels, traffic, opportunityZones, oz2Tracts, basemapRef.current);
          addSatelliteSourceAndLayer(map);
          applyBasemap(map, basemapRef.current);

          const interactive = ["parcels-fill", "parcels-fill-excluded"];
          map.on("click", interactive, (event) => {
            const id = event.features?.[0]?.properties?.id;
            if (typeof id === "string") callbacksRef.current.onSelect(id);
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
  }, [parcels, traffic, opportunityZones, oz2Tracts]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    const ids = Array.from(matchedIds);
    const matchedFilter: maplibregl.FilterSpecification =
      ids.length === 0 ? ["==", ["get", "id"], "__none__"] : ["in", ["get", "id"], ["literal", ids]];
    const excludedFilter: maplibregl.FilterSpecification = ["!", matchedFilter];
    map.setFilter("parcels-fill", matchedFilter);
    map.setFilter("parcels-line", matchedFilter);
    map.setFilter("parcels-fill-excluded", showExcluded ? excludedFilter : ["==", ["get", "id"], "__none__"]);
    map.setFilter("parcels-line-excluded", showExcluded ? excludedFilter : ["==", ["get", "id"], "__none__"]);
    map.setLayoutProperty("traffic-line", "visibility", showTraffic ? "visible" : "none");
    map.setLayoutProperty("oz-fill", "visibility", showOz ? "visible" : "none");
    map.setLayoutProperty("oz-line", "visibility", showOz ? "visible" : "none");
    map.setLayoutProperty("oz2-fill", "visibility", showOz2 ? "visible" : "none");
    map.setLayoutProperty("oz2-line", "visibility", showOz2 ? "visible" : "none");
    const oz2Filter: maplibregl.FilterSpecification | null =
      ozFilter === "rural-eligible"
        ? ["==", ["get", "rural"], true]
        : ozFilter === "non-rural-eligible"
          ? ["==", ["get", "rural"], false]
          : null;
    map.setFilter("oz2-fill", oz2Filter);
    map.setFilter("oz2-line", oz2Filter);
  }, [matchedIds, showExcluded, showTraffic, showOz, showOz2, ozFilter, status]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || status !== "ready") return;
    applyBasemap(map, basemap);
    map.setLayoutProperty("traffic-line", "visibility", showTraffic ? "visible" : "none");
    map.setLayoutProperty("oz-fill", "visibility", showOz ? "visible" : "none");
    map.setLayoutProperty("oz-line", "visibility", showOz ? "visible" : "none");
    map.setLayoutProperty("oz2-fill", "visibility", showOz2 ? "visible" : "none");
    map.setLayoutProperty("oz2-line", "visibility", showOz2 ? "visible" : "none");
  }, [basemap, showTraffic, showOz, showOz2, status]);

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

  useEffect(() => {
    mapRef.current?.resize();
  }, [selectedId]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {status === "ready" ? <BasemapToggle value={basemap} onChange={setBasemap} /> : null}
      {status === "ready" && (showOz || showOz2) ? (
        <div className="pointer-events-none absolute bottom-3 left-3 z-10 max-w-[16rem] space-y-1 rounded-lg border border-white/10 bg-ink-900/90 px-2 py-1.5 text-[10px] leading-snug text-ink-300 sm:bottom-4 sm:left-4">
          {showOz2 ? (
            <>
              <p>
                <span className="mr-1.5 inline-block h-2 w-2 rounded-sm bg-[#3dbe86]" />
                OZ 2.0 rural-eligible (nomination only)
              </p>
              <p>
                <span className="mr-1.5 inline-block h-2 w-2 rounded-sm bg-[#5b8def]" />
                OZ 2.0 eligible, not rural
              </p>
            </>
          ) : null}
          {showOz ? (
            <p>
              <span className="mr-1.5 inline-block h-2 w-2 rounded-sm bg-[#c9a227]" />
              Designated QOZ (2018)
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
