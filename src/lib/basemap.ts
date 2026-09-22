import type {
  CircleLayerSpecification,
  FillLayerSpecification,
  LineLayerSpecification,
  Map as MapLibreMap,
} from "maplibre-gl";

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
  "rural-fill",
  "rural-line",
  "mf-priority-a-fill",
  "mf-priority-a-line",
  "mf-priority-b-fill",
  "mf-priority-b-line",
  "rural-pins",
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

/**
 * Census-tract overlay swatches (street basemap). Orange/amber so tracts stay
 * distinct from green parcel fills. Satellite paint uses brighter variants.
 */
export const OZ_TRACT_SWATCH = {
  /** Stronger, warmer orange — OZ 2.0 rural-eligible tracts. */
  rural: "#f15a08",
  /** Lighter amber — OZ 2.0 eligible tracts that are not rural. */
  eligible: "#f0b429",
  /** Copper accent — current designated QOZ tracts (dashed outline on the map). */
  designated: "#c46a2f",
} as const;

/** Highlight for the SC multifamily shortlist. Neither color means designated. */
export const MF_PRIORITY_SWATCH = {
  tierA: "#ffe08a",
  tierB: "#7ec8ff",
} as const;

export function ozFillPaint(mode: BasemapMode): NonNullable<FillLayerSpecification["paint"]> {
  return mode === "satellite"
    ? { "fill-color": "#e88845", "fill-opacity": 0.36 }
    : { "fill-color": OZ_TRACT_SWATCH.designated, "fill-opacity": 0.26 };
}

export function ozLinePaint(mode: BasemapMode): NonNullable<LineLayerSpecification["paint"]> {
  return mode === "satellite"
    ? { "line-color": "#ffe4cf", "line-width": 2.1, "line-opacity": 0.95, "line-dasharray": [2, 1.2] }
    : { "line-color": "#f6d0b0", "line-width": 1.7, "line-opacity": 0.88, "line-dasharray": [2, 1.2] };
}

export function oz2FillPaint(mode: BasemapMode): NonNullable<FillLayerSpecification["paint"]> {
  const rural = mode === "satellite" ? "#ff7a29" : OZ_TRACT_SWATCH.rural;
  const other = mode === "satellite" ? "#ffd56a" : OZ_TRACT_SWATCH.eligible;
  const ruralOpacity = mode === "satellite" ? 0.42 : 0.32;
  const otherOpacity = mode === "satellite" ? 0.32 : 0.22;
  return {
    "fill-color": ["case", ["==", ["get", "rural"], true], rural, other],
    "fill-opacity": ["case", ["==", ["get", "rural"], true], ruralOpacity, otherOpacity],
  };
}

export function mfPriorityFillPaint(mode: BasemapMode, tier: "A" | "B"): NonNullable<FillLayerSpecification["paint"]> {
  const color = tier === "A" ? MF_PRIORITY_SWATCH.tierA : MF_PRIORITY_SWATCH.tierB;
  return {
    "fill-color": color,
    "fill-opacity": mode === "satellite" ? (tier === "A" ? 0.28 : 0.22) : tier === "A" ? 0.2 : 0.16,
  };
}

export function mfPriorityLinePaint(mode: BasemapMode, tier: "A" | "B"): NonNullable<LineLayerSpecification["paint"]> {
  const color = tier === "A" ? MF_PRIORITY_SWATCH.tierA : MF_PRIORITY_SWATCH.tierB;
  return {
    "line-color": color,
    "line-width": tier === "A" ? (mode === "satellite" ? 3.6 : 3.2) : mode === "satellite" ? 2.8 : 2.4,
    "line-opacity": mode === "satellite" ? 0.98 : 0.95,
  };
}

export function oz2LinePaint(mode: BasemapMode): NonNullable<LineLayerSpecification["paint"]> {
  const rural = mode === "satellite" ? "#ffe6d4" : "#ffd0b0";
  const other = mode === "satellite" ? "#fff3d4" : "#ffe7ad";
  return {
    "line-color": ["case", ["==", ["get", "rural"], true], rural, other],
    "line-width": ["case", ["==", ["get", "rural"], true], mode === "satellite" ? 2.8 : 2.5, mode === "satellite" ? 1.35 : 1.05],
    "line-opacity": mode === "satellite" ? 0.96 : 0.88,
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
    const beforeId = map.getLayer(FIRST_OVERLAY_LAYER_ID) ? FIRST_OVERLAY_LAYER_ID : undefined;
    try {
      map.addLayer(
        {
          id: SATELLITE_LAYER_ID,
          type: "raster",
          source: SATELLITE_SOURCE_ID,
          layout: { visibility: "none" },
        },
        beforeId,
      );
    } catch {
      if (!map.getLayer(SATELLITE_LAYER_ID)) {
        map.addLayer({
          id: SATELLITE_LAYER_ID,
          type: "raster",
          source: SATELLITE_SOURCE_ID,
          layout: { visibility: "none" },
        });
      }
    }
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
  setPaint(map, "rural-fill", oz2FillPaint(mode));
  setPaint(map, "rural-line", oz2LinePaint(mode));
  setPaint(map, "mf-priority-a-fill", mfPriorityFillPaint(mode, "A"));
  setPaint(map, "mf-priority-a-line", mfPriorityLinePaint(mode, "A"));
  setPaint(map, "mf-priority-b-fill", mfPriorityFillPaint(mode, "B"));
  setPaint(map, "mf-priority-b-line", mfPriorityLinePaint(mode, "B"));
  setPaint(map, "rural-pins", ruralPinPaint(mode));
}

export function ruralPinPaint(mode: BasemapMode): NonNullable<CircleLayerSpecification["paint"]> {
  const fallback = mode === "satellite" ? "#ff7a29" : OZ_TRACT_SWATCH.rural;
  return {
    "circle-color": ["match", ["coalesce", ["get", "mfTier"], ""], "A", MF_PRIORITY_SWATCH.tierA, "B", MF_PRIORITY_SWATCH.tierB, fallback],
    "circle-radius": [
      "interpolate",
      ["linear"],
      ["zoom"],
      6,
      ["match", ["coalesce", ["get", "mfTier"], ""], "A", 4.5, "B", 4, 3],
      10,
      ["match", ["coalesce", ["get", "mfTier"], ""], "A", 7, "B", 6, 5],
      13,
      ["match", ["coalesce", ["get", "mfTier"], ""], "A", 9, "B", 8, 7],
    ],
    "circle-stroke-color": mode === "satellite" ? "#fff6ee" : "#2a160c",
    "circle-stroke-width": ["match", ["coalesce", ["get", "mfTier"], ""], "A", 2.2, "B", 1.8, 1.25],
    "circle-opacity": 0.95,
  };
}
