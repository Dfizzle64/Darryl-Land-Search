import type { FillLayerSpecification, LineLayerSpecification, Map as MapLibreMap } from "maplibre-gl";

export type BasemapMode = "streets" | "satellite";

/** Dark street styles already used by the app (OpenFreeMap, then Carto Dark Matter). */
export const STREET_STYLE_CANDIDATES = [
  "https://tiles.openfreemap.org/styles/dark",
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
] as const;

/** Esri World Imagery — public XYZ tiles, no API key. */
export const ESRI_WORLD_IMAGERY_TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

export const ESRI_WORLD_IMAGERY_ATTRIBUTION =
  "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community";

export const SATELLITE_SOURCE_ID = "basemap-satellite";
export const SATELLITE_LAYER_ID = "basemap-satellite";

export const OVERLAY_LAYER_IDS = [
  "oz2-fill",
  "oz2-line",
  "oz-fill",
  "oz-line",
  "traffic-line",
  "parcels-fill-excluded",
  "parcels-line-excluded",
  "parcels-fill",
  "parcels-line",
] as const;

export const FIRST_OVERLAY_LAYER_ID = OVERLAY_LAYER_IDS[0];

export function parcelFillPaint(mode: BasemapMode): NonNullable<FillLayerSpecification["paint"]> {
  return {
    "fill-color": [
      "case",
      ["boolean", ["feature-state", "selected"], false],
      "#f0c27a",
      ["boolean", ["feature-state", "hover"], false],
      "#8fd4b5",
      "#3f9d74",
    ],
    "fill-opacity":
      mode === "satellite"
        ? ["case", ["boolean", ["feature-state", "selected"], false], 0.5, ["boolean", ["feature-state", "hover"], false], 0.38, 0.26]
        : ["case", ["boolean", ["feature-state", "selected"], false], 0.78, 0.52],
  };
}

export function parcelLinePaint(mode: BasemapMode): NonNullable<LineLayerSpecification["paint"]> {
  if (mode === "satellite") {
    return {
      "line-color": [
        "case",
        ["boolean", ["feature-state", "selected"], false],
        "#ffe08a",
        ["boolean", ["feature-state", "hover"], false],
        "#ffffff",
        "#f3f7f5",
      ],
      "line-width": [
        "case",
        ["boolean", ["feature-state", "selected"], false],
        3,
        ["boolean", ["feature-state", "hover"], false],
        2.1,
        1.7,
      ],
    };
  }
  return {
    "line-color": ["case", ["boolean", ["feature-state", "selected"], false], "#f8e1b5", "#b7e3cf"],
    "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 2.4, 1],
  };
}

export function excludedFillPaint(mode: BasemapMode): NonNullable<FillLayerSpecification["paint"]> {
  return mode === "satellite"
    ? { "fill-color": "#d7dee6", "fill-opacity": 0.1 }
    : { "fill-color": "#6b7c8d", "fill-opacity": 0.08 };
}

export function excludedLinePaint(mode: BasemapMode): NonNullable<LineLayerSpecification["paint"]> {
  return mode === "satellite"
    ? { "line-color": "#e8eef4", "line-width": 0.95, "line-opacity": 0.65 }
    : { "line-color": "#6b7c8d", "line-width": 0.6, "line-opacity": 0.35 };
}

export function trafficLinePaint(mode: BasemapMode): NonNullable<LineLayerSpecification["paint"]> {
  return {
    "line-color": mode === "satellite" ? "#ffcc7a" : "#d7a36a",
    "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.6, 14, 2.4],
    "line-opacity": mode === "satellite" ? 0.9 : 0.55,
  };
}

export function ozFillPaint(mode: BasemapMode): NonNullable<FillLayerSpecification["paint"]> {
  return mode === "satellite"
    ? { "fill-color": "#f4c15d", "fill-opacity": 0.22 }
    : { "fill-color": "#c9a227", "fill-opacity": 0.18 };
}

export function ozLinePaint(mode: BasemapMode): NonNullable<LineLayerSpecification["paint"]> {
  return mode === "satellite"
    ? { "line-color": "#ffe08a", "line-width": 1.6, "line-opacity": 0.9 }
    : { "line-color": "#e4c36a", "line-width": 1.2, "line-opacity": 0.75 };
}

export function oz2FillPaint(mode: BasemapMode): NonNullable<FillLayerSpecification["paint"]> {
  const rural = mode === "satellite" ? "#5ee0a0" : "#3dbe86";
  const other = mode === "satellite" ? "#9ec1ff" : "#5b8def";
  return {
    "fill-color": ["case", ["==", ["get", "rural"], true], rural, other],
    "fill-opacity": mode === "satellite" ? 0.3 : 0.22,
  };
}

export function oz2LinePaint(mode: BasemapMode): NonNullable<LineLayerSpecification["paint"]> {
  const rural = mode === "satellite" ? "#e8fff3" : "#c8f5de";
  const other = mode === "satellite" ? "#e4eeff" : "#d5e4ff";
  return {
    "line-color": ["case", ["==", ["get", "rural"], true], rural, other],
    "line-width": ["case", ["==", ["get", "rural"], true], mode === "satellite" ? 2.8 : 2.4, mode === "satellite" ? 1.3 : 1],
    "line-opacity": mode === "satellite" ? 0.95 : 0.85,
  };
}

export function addSatelliteSourceAndLayer(map: MapLibreMap) {
  if (!map.getSource(SATELLITE_SOURCE_ID)) {
    map.addSource(SATELLITE_SOURCE_ID, {
      type: "raster",
      tiles: [ESRI_WORLD_IMAGERY_TILES],
      tileSize: 256,
      attribution: ESRI_WORLD_IMAGERY_ATTRIBUTION,
      maxzoom: 19,
    });
  }
  if (!map.getLayer(SATELLITE_LAYER_ID)) {
    map.addLayer(
      {
        id: SATELLITE_LAYER_ID,
        type: "raster",
        source: SATELLITE_SOURCE_ID,
        layout: { visibility: "none" },
      },
      FIRST_OVERLAY_LAYER_ID,
    );
  }
}

function setPaint(map: MapLibreMap, layerId: string, paint: Record<string, unknown>) {
  if (!map.getLayer(layerId)) return;
  for (const [property, value] of Object.entries(paint)) {
    map.setPaintProperty(layerId, property, value);
  }
}

/** Swap street vs satellite without dropping overlay sources, filters, or the camera. */
export function applyBasemap(map: MapLibreMap, mode: BasemapMode) {
  const style = map.getStyle();
  if (!style?.layers) return;

  const overlayIds = new Set<string>(OVERLAY_LAYER_IDS);

  for (const layer of style.layers) {
    if (layer.id === SATELLITE_LAYER_ID) {
      map.setLayoutProperty(layer.id, "visibility", mode === "satellite" ? "visible" : "none");
      continue;
    }
    if (overlayIds.has(layer.id)) continue;
    map.setLayoutProperty(layer.id, "visibility", mode === "streets" ? "visible" : "none");
  }

  setPaint(map, "parcels-fill", parcelFillPaint(mode));
  setPaint(map, "parcels-line", parcelLinePaint(mode));
  setPaint(map, "parcels-fill-excluded", excludedFillPaint(mode));
  setPaint(map, "parcels-line-excluded", excludedLinePaint(mode));
  setPaint(map, "traffic-line", trafficLinePaint(mode));
  setPaint(map, "oz-fill", ozFillPaint(mode));
  setPaint(map, "oz-line", ozLinePaint(mode));
  setPaint(map, "oz2-fill", oz2FillPaint(mode));
  setPaint(map, "oz2-line", oz2LinePaint(mode));
}
