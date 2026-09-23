import type {
  CircleLayerSpecification,
  FillLayerSpecification,
  ExpressionSpecification,
  FilterSpecification,
  LineLayerSpecification,
  Map as MapLibreMap,
} from "maplibre-gl";

export type BasemapMode = "streets" | "satellite" | "dark";

/** Dark street styles already used by the app (OpenFreeMap, then Carto Dark Matter). */
export const STREET_STYLE_CANDIDATES = [
  "https://tiles.openfreemap.org/styles/dark",
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
] as const;

/**
 * Keyless navigation streets. Esri World Street Map is a public XYZ raster (roads,
 * labels, and places) with no API key and no watermark. It uses the same overlay
 * path as satellite, so toggling basemaps does not reload the OpenFreeMap dark style
 * or drop parcel layers. MapTiler Streets v2 replaces it when NEXT_PUBLIC_MAPTILER_KEY
 * is set. CARTO Voyager is not the fallback: that raster now requires a key and
 * paints "API KEY REQUIRED" tiles.
 */
export const ESRI_WORLD_STREET_TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}";

export const ESRI_STREETS_ATTRIBUTION =
  "Tiles © Esri — Sources: Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), Esri Korea, Esri (Thailand), NGCC, © OpenStreetMap contributors, and the GIS User Community";

/** Esri World Imagery — public XYZ tiles, no API key. */
export const ESRI_WORLD_IMAGERY_TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

/** Roads drawn on top of imagery for the keyless hybrid. */
export const ESRI_TRANSPORTATION_TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}";

/** City, place, and boundary labels for the keyless hybrid. */
export const ESRI_PLACES_TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}";

export const ESRI_WORLD_IMAGERY_ATTRIBUTION =
  "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community";

export const ESRI_HYBRID_ATTRIBUTION =
  "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community. Roads and place labels © Esri.";

export const MAPTILER_ATTRIBUTION = "© MapTiler © OpenStreetMap contributors";

export const DARK_BASEMAP_ATTRIBUTION = "© OpenFreeMap © OpenStreetMap contributors";

export const SATELLITE_SOURCE_ID = "basemap-satellite";
export const SATELLITE_LAYER_ID = "basemap-satellite";
export const STREETS_SOURCE_ID = "basemap-streets";
export const STREETS_LAYER_ID = "basemap-streets";
export const HYBRID_ROADS_SOURCE_ID = "basemap-hybrid-roads";
export const HYBRID_ROADS_LAYER_ID = "basemap-hybrid-roads";
export const HYBRID_PLACES_SOURCE_ID = "basemap-hybrid-places";
export const HYBRID_PLACES_LAYER_ID = "basemap-hybrid-places";

export function maptilerKeyFrom(envValue: string | undefined | null): string | null {
  const key = envValue?.trim();
  return key ? key : null;
}

/** Inlined at build time for client bundles. Empty when the key is unset. */
export const MAPTILER_KEY = maptilerKeyFrom(process.env.NEXT_PUBLIC_MAPTILER_KEY);

export function streetsTileUrl(key: string | null = MAPTILER_KEY): string {
  if (key) return `https://api.maptiler.com/maps/streets-v2/256/{z}/{x}/{y}.png?key=${encodeURIComponent(key)}`;
  return ESRI_WORLD_STREET_TILES;
}

export function hybridImageryTileUrl(key: string | null = MAPTILER_KEY): string {
  if (key) return `https://api.maptiler.com/maps/hybrid/256/{z}/{x}/{y}.jpg?key=${encodeURIComponent(key)}`;
  return ESRI_WORLD_IMAGERY_TILES;
}

/** MapTiler hybrid tiles already include roads and labels, so the Esri reference stack stays off. */
export function usesEsriHybridReference(key: string | null = MAPTILER_KEY): boolean {
  return !key;
}

export function basemapAttribution(mode: BasemapMode, key: string | null = MAPTILER_KEY): string {
  if (mode === "dark") return DARK_BASEMAP_ATTRIBUTION;
  if (mode === "streets") return key ? MAPTILER_ATTRIBUTION : ESRI_STREETS_ATTRIBUTION;
  return key ? MAPTILER_ATTRIBUTION : ESRI_HYBRID_ATTRIBUTION;
}

export function rasterLayerVisibility(
  mode: BasemapMode,
  includeHybridReference = usesEsriHybridReference(),
): Record<string, "visible" | "none"> {
  const hybrid = mode === "satellite";
  return {
    [STREETS_LAYER_ID]: mode === "streets" ? "visible" : "none",
    [SATELLITE_LAYER_ID]: hybrid ? "visible" : "none",
    [HYBRID_ROADS_LAYER_ID]: hybrid && includeHybridReference ? "visible" : "none",
    [HYBRID_PLACES_LAYER_ID]: hybrid && includeHybridReference ? "visible" : "none",
  };
}

export const OVERLAY_LAYER_IDS = [
  "flood-raster",
  "wetlands-raster",
  "school-zone-raster",
  "school-ms-raster",
  "school-cms-es-raster",
  "school-cms-ms-raster",
  "school-cms-hs-raster",
  "water-fill",
  "water-line",
  "sewer-fill",
  "sewer-line",
  "power-fill",
  "power-line",
  "rural-fill",
  "rural-line",
  "eligible-fill",
  "eligible-line",
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
  "schools-circle",
  "aoi-fill",
  "aoi-line",
  "measure-casing",
  "measure-line",
  "measure-vertices",
] as const;

export const FIRST_OVERLAY_LAYER_ID = OVERLAY_LAYER_IDS[0];

/** Constant-size filters. A literal id list breaks once the viewport holds thousands of parcels. */
export const parcelMatchFilter: FilterSpecification = ["==", ["get", "filterMatch"], 1];
export const parcelExcludedFilter: FilterSpecification = ["==", ["get", "filterMatch"], 0];
export const parcelHiddenFilter: FilterSpecification = ["==", ["get", "filterMatch"], -1];

/**
 * Neighborhood zoom (the auto-on gate) stays light: lower fill, thinner line.
 * Close zoom uses the original street/satellite weights. Selection stays strong.
 * Zoom interpolation has to be the top-level expression. MapLibre rejects ["zoom"] nested in a case.
 */
function parcelZoomStops(
  quiet: number,
  mid: number,
  full: number,
  selected: number,
  hover: number,
): ExpressionSpecification {
  const at = (base: number): ExpressionSpecification => [
    "case",
    ["boolean", ["feature-state", "selected"], false],
    selected,
    ["boolean", ["feature-state", "hover"], false],
    hover,
    base,
  ];
  // First stop is neighborhood zoom (the auto-on gate), not the old 11 stop.
  return ["interpolate", ["linear"], ["zoom"], 10, at(quiet), 12.5, at(mid), 14.5, at(full)];
}

export function parcelFillPaint(mode: BasemapMode): NonNullable<FillLayerSpecification["paint"]> {
  const quiet = mode === "satellite" ? 0.1 : 0.16;
  const mid = mode === "satellite" ? 0.16 : 0.28;
  const full = mode === "satellite" ? 0.26 : 0.52;
  return {
    "fill-color": [
      "case",
      ["boolean", ["feature-state", "selected"], false],
      "#f0c27a",
      ["boolean", ["feature-state", "hover"], false],
      "#8fd4b5",
      "#3f9d74",
    ],
    "fill-opacity": parcelZoomStops(
      quiet,
      mid,
      full,
      mode === "satellite" ? 0.5 : 0.78,
      mode === "satellite" ? 0.38 : 0.62,
    ),
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
      "line-width": parcelZoomStops(0.55, 0.9, 1.7, 2.6, 1.6),
    };
  }
  const onLightStreets = mode === "streets";
  return {
    "line-color": [
      "case",
      ["boolean", ["feature-state", "selected"], false],
      onLightStreets ? "#9a3412" : "#f8e1b5",
      onLightStreets ? "#0f5132" : "#b7e3cf",
    ],
    "line-width": parcelZoomStops(0.35, 0.6, 1, 2.2, 1.3),
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
  /** Lighter amber — Orange County OZ 2.0 tracts that are not rural. */
  eligible: "#f0b429",
  /** Blue — urban / non-rural eligible tracts outside the Orange County amber overlay. */
  urban: "#3d7dff",
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
  if (mode === "satellite") {
    return { "line-color": "#ffe4cf", "line-width": 2.1, "line-opacity": 0.95, "line-dasharray": [2, 1.2] };
  }
  return {
    "line-color": mode === "streets" ? "#9a3412" : "#f6d0b0",
    "line-width": 1.7,
    "line-opacity": 0.88,
    "line-dasharray": [2, 1.2],
  };
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

export function eligiblePackFillPaint(mode: BasemapMode): NonNullable<FillLayerSpecification["paint"]> {
  const rural = mode === "satellite" ? "#ff7a29" : OZ_TRACT_SWATCH.rural;
  const urban = mode === "satellite" ? "#8eb6ff" : OZ_TRACT_SWATCH.urban;
  const ruralOpacity = mode === "satellite" ? 0.42 : 0.32;
  const urbanOpacity = mode === "satellite" ? 0.38 : 0.28;
  return {
    "fill-color": ["case", ["==", ["get", "rural"], true], rural, urban],
    "fill-opacity": ["case", ["==", ["get", "rural"], true], ruralOpacity, urbanOpacity],
  };
}

export function eligiblePackLinePaint(mode: BasemapMode): NonNullable<LineLayerSpecification["paint"]> {
  const rural = mode === "satellite" ? "#ffe6d4" : "#ffd0b0";
  const urban = mode === "satellite" ? "#d6e6ff" : "#c5d8ff";
  return {
    "line-color": ["case", ["==", ["get", "rural"], true], rural, urban],
    "line-width": ["case", ["==", ["get", "rural"], true], mode === "satellite" ? 2.8 : 2.5, mode === "satellite" ? 1.6 : 1.25],
    "line-opacity": mode === "satellite" ? 0.96 : 0.9,
  };
}

export function oz2LinePaint(mode: BasemapMode): NonNullable<LineLayerSpecification["paint"]> {
  const rural = mode === "satellite" ? "#ffe6d4" : mode === "streets" ? "#9a3412" : "#ffd0b0";
  const other = mode === "satellite" ? "#fff3d4" : mode === "streets" ? "#b45309" : "#ffe7ad";
  return {
    "line-color": ["case", ["==", ["get", "rural"], true], rural, other],
    "line-width": ["case", ["==", ["get", "rural"], true], mode === "satellite" ? 2.8 : 2.5, mode === "satellite" ? 1.35 : 1.05],
    "line-opacity": mode === "satellite" ? 0.96 : 0.88,
  };
}

function addRasterLayer(
  map: MapLibreMap,
  sourceId: string,
  layerId: string,
  tiles: string[],
  attribution: string,
  maxzoom: number,
) {
  if (!map.getSource(sourceId)) {
    map.addSource(sourceId, {
      type: "raster",
      tiles,
      tileSize: 256,
      attribution,
      maxzoom,
    });
  }
  if (map.getLayer(layerId)) return;
  const beforeId = map.getLayer(FIRST_OVERLAY_LAYER_ID) ? FIRST_OVERLAY_LAYER_ID : undefined;
  const layer = {
    id: layerId,
    type: "raster" as const,
    source: sourceId,
    layout: { visibility: "none" as const },
  };
  try {
    map.addLayer(layer, beforeId);
  } catch {
    if (!map.getLayer(layerId)) map.addLayer(layer);
  }
}

/** Streets raster, imagery, and (keyless) hybrid reference labels. Idempotent. */
export function addBasemapRasterLayers(map: MapLibreMap, key: string | null = MAPTILER_KEY) {
  const maptiler = Boolean(key);
  addRasterLayer(
    map,
    STREETS_SOURCE_ID,
    STREETS_LAYER_ID,
    [streetsTileUrl(key)],
    maptiler ? MAPTILER_ATTRIBUTION : ESRI_STREETS_ATTRIBUTION,
    20,
  );
  addRasterLayer(
    map,
    SATELLITE_SOURCE_ID,
    SATELLITE_LAYER_ID,
    [hybridImageryTileUrl(key)],
    maptiler ? MAPTILER_ATTRIBUTION : ESRI_WORLD_IMAGERY_ATTRIBUTION,
    19,
  );
  addRasterLayer(map, HYBRID_ROADS_SOURCE_ID, HYBRID_ROADS_LAYER_ID, [ESRI_TRANSPORTATION_TILES], ESRI_HYBRID_ATTRIBUTION, 19);
  addRasterLayer(map, HYBRID_PLACES_SOURCE_ID, HYBRID_PLACES_LAYER_ID, [ESRI_PLACES_TILES], ESRI_HYBRID_ATTRIBUTION, 19);
}

export function addSatelliteSourceAndLayer(map: MapLibreMap) {
  addBasemapRasterLayers(map);
}

function setPaint(map: MapLibreMap, layerId: string, paint: Record<string, unknown>) {
  if (!map.getLayer(layerId)) return;
  for (const [property, value] of Object.entries(paint)) {
    map.setPaintProperty(layerId, property, value);
  }
}

/** Swap streets, hybrid, or dark without dropping overlay sources, filters, or the camera. */
export function applyBasemap(map: MapLibreMap, mode: BasemapMode) {
  const style = map.getStyle();
  if (!style?.layers) return;

  const overlayIds = new Set<string>(OVERLAY_LAYER_IDS);
  const rasters = rasterLayerVisibility(mode);

  for (const layer of style.layers) {
    const raster = rasters[layer.id];
    if (raster) {
      map.setLayoutProperty(layer.id, "visibility", raster);
      continue;
    }
    if (overlayIds.has(layer.id)) continue;
    map.setLayoutProperty(layer.id, "visibility", mode === "dark" ? "visible" : "none");
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
  setPaint(map, "eligible-fill", eligiblePackFillPaint(mode));
  setPaint(map, "eligible-line", eligiblePackLinePaint(mode));
  setPaint(map, "mf-priority-a-fill", mfPriorityFillPaint(mode, "A"));
  setPaint(map, "mf-priority-a-line", mfPriorityLinePaint(mode, "A"));
  setPaint(map, "mf-priority-b-fill", mfPriorityFillPaint(mode, "B"));
  setPaint(map, "mf-priority-b-line", mfPriorityLinePaint(mode, "B"));
  setPaint(map, "rural-pins", ruralPinPaint(mode));
}

export function ruralPinPaint(mode: BasemapMode): NonNullable<CircleLayerSpecification["paint"]> {
  const rural = mode === "satellite" ? "#ff7a29" : OZ_TRACT_SWATCH.rural;
  const urban = mode === "satellite" ? "#8eb6ff" : OZ_TRACT_SWATCH.urban;
  const fallback: ExpressionSpecification = ["case", ["==", ["get", "rural"], false], urban, rural];
  return {
    "circle-color": [
      "match",
      ["coalesce", ["get", "mfTier"], ""],
      "A",
      MF_PRIORITY_SWATCH.tierA,
      "B",
      MF_PRIORITY_SWATCH.tierB,
      fallback,
    ],
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
