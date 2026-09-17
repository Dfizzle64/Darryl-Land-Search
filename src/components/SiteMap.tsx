"use client";

import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { ORANGE_COUNTY_BOUNDS, ORANGE_COUNTY_CENTER, type ParcelCollection } from "@/lib/types";

const STYLE_CANDIDATES = [
  "https://tiles.openfreemap.org/styles/dark",
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
];

type SiteMapProps = {
  parcels: ParcelCollection;
  traffic: GeoJSON.FeatureCollection<GeoJSON.LineString>;
  matchedIds: Set<string>;
  selectedId: string | null;
  hoveredId: string | null;
  showExcluded: boolean;
  showTraffic: boolean;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
};

export function SiteMap({
  parcels,
  traffic,
  matchedIds,
  selectedId,
  hoveredId,
  showExcluded,
  showTraffic,
  onSelect,
  onHover,
}: SiteMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("Loading Orange County map…");
  const callbacksRef = useRef({ onSelect, onHover });
  callbacksRef.current = { onSelect, onHover };

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let cancelled = false;

    const start = async () => {
      let lastError: unknown;
      for (const style of STYLE_CANDIDATES) {
        try {
          const map = new maplibregl.Map({
            container: containerRef.current!,
            style,
            center: ORANGE_COUNTY_CENTER,
            zoom: 9.4,
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
          map.addSource("parcels", { type: "geojson", data: parcels, promoteId: "id" });
          map.addSource("traffic", { type: "geojson", data: traffic });

          map.addLayer({
            id: "traffic-line",
            type: "line",
            source: "traffic",
            paint: {
              "line-color": "#d7a36a",
              "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.6, 14, 2.4],
              "line-opacity": 0.55,
            },
          });
          map.addLayer({
            id: "parcels-fill-excluded",
            type: "fill",
            source: "parcels",
            paint: { "fill-color": "#6b7c8d", "fill-opacity": 0.08 },
          });
          map.addLayer({
            id: "parcels-line-excluded",
            type: "line",
            source: "parcels",
            paint: { "line-color": "#6b7c8d", "line-width": 0.6, "line-opacity": 0.35 },
          });
          map.addLayer({
            id: "parcels-fill",
            type: "fill",
            source: "parcels",
            paint: {
              "fill-color": [
                "case",
                ["boolean", ["feature-state", "selected"], false],
                "#f0c27a",
                ["boolean", ["feature-state", "hover"], false],
                "#8fd4b5",
                "#3f9d74",
              ],
              "fill-opacity": [
                "case",
                ["boolean", ["feature-state", "selected"], false],
                0.78,
                0.52,
              ],
            },
          });
          map.addLayer({
            id: "parcels-line",
            type: "line",
            source: "parcels",
            paint: {
              "line-color": [
                "case",
                ["boolean", ["feature-state", "selected"], false],
                "#f8e1b5",
                "#b7e3cf",
              ],
              "line-width": [
                "case",
                ["boolean", ["feature-state", "selected"], false],
                2.4,
                1,
              ],
            },
          });

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
  }, [parcels, traffic]);

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
  }, [matchedIds, showExcluded, showTraffic, status]);

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
