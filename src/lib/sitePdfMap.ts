import maplibregl, { type Map as MapLibreMap, type StyleSpecification } from "maplibre-gl";
import {
  ESRI_STREETS_ATTRIBUTION,
  ESRI_WORLD_STREET_TILES,
  OZ_TRACT_SWATCH,
  ruralTractFill,
  ruralTractLine,
} from "./basemap";
import { SitePdfError, chooseScaleBar, contextBbox, haversineMeters, locatorBbox } from "./sitePdfGeometry";
import type { TractGeometryRecord } from "./sitePdf";

const MAIN_W = 1040;
const MAIN_H = 600;
const LOCATOR_W = 360;
const LOCATOR_H = 260;

function streetStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {
      basemap: {
        type: "raster",
        tiles: [ESRI_WORLD_STREET_TILES],
        tileSize: 256,
        maxzoom: 19,
        attribution: ESRI_STREETS_ATTRIBUTION,
      },
    },
    layers: [
      { id: "background", type: "background", paint: { "background-color": "#e6e1d6" } },
      { id: "basemap", type: "raster", source: "basemap" },
    ],
  };
}

function waitFor(map: MapLibreMap, event: "load" | "idle", timeoutMs: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new SitePdfError("Could not export the PDF. The map did not finish loading. Try again."));
    }, timeoutMs);
    map.once(event, () => {
      window.clearTimeout(timer);
      resolve();
    });
  });
}

async function waitForTiles(map: MapLibreMap): Promise<void> {
  const started = Date.now();
  while (Date.now() - started < 12000) {
    if (map.loaded() && map.areTilesLoaded()) {
      await new Promise((resolve) => window.setTimeout(resolve, 150));
      if (map.areTilesLoaded()) return;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 200));
  }
  throw new SitePdfError("Could not export the PDF. The map did not finish loading. Try again.");
}

function metersPerPixel(map: MapLibreMap): number {
  const width = map.getContainer().clientWidth;
  const y = map.getContainer().clientHeight / 2;
  const left = map.unproject([width * 0.35, y]);
  const right = map.unproject([width * 0.65, y]);
  const span = width * 0.3;
  if (span <= 0) return 1;
  return haversineMeters([left.lng, left.lat], [right.lng, right.lat]) / span;
}

function snapshot(map: MapLibreMap, decorate: boolean): { url: string; scaleLabel: string } {
  const glCanvas = map.getCanvas();
  const out = document.createElement("canvas");
  out.width = glCanvas.width;
  out.height = glCanvas.height;
  const ctx = out.getContext("2d");
  if (!ctx) throw new SitePdfError("Could not export the PDF. The map did not finish loading. Try again.");
  let scaleLabel = "";
  try {
    ctx.drawImage(glCanvas, 0, 0);
    if (decorate) {
      const ratio = glCanvas.width / Math.max(1, map.getContainer().clientWidth);
      const scale = chooseScaleBar(metersPerPixel(map));
      scaleLabel = scale.label;
      drawScaleBar(ctx, out.width, out.height, scale.pixels * ratio, scale.label, ratio);
      drawNorthArrow(ctx, out.width - 28 * ratio, 28 * ratio, ratio);
    }
    if (canvasLooksBlank(out)) {
      throw new SitePdfError("Could not export the PDF. The basemap blocked image capture.");
    }
    return { url: out.toDataURL("image/jpeg", 0.86), scaleLabel };
  } catch (error) {
    if (error instanceof SitePdfError) throw error;
    throw new SitePdfError("Could not export the PDF. The basemap blocked image capture.");
  }
}

function canvasLooksBlank(canvas: HTMLCanvasElement): boolean {
  const sample = document.createElement("canvas");
  sample.width = 8;
  sample.height = 8;
  const ctx = sample.getContext("2d", { willReadFrequently: true });
  if (!ctx) return false;
  ctx.drawImage(canvas, 0, 0, canvas.width, canvas.height, 0, 0, 8, 8);
  const data = ctx.getImageData(0, 0, 8, 8).data;
  let min = 255 * 3;
  let max = 0;
  for (let i = 0; i < data.length; i += 4) {
    const value = data[i] + data[i + 1] + data[i + 2];
    if (value < min) min = value;
    if (value > max) max = value;
  }
  return max - min < 18;
}

function drawScaleBar(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  barPx: number,
  label: string,
  ratio: number,
) {
  const bar = Math.max(48 * ratio, Math.min(barPx, width * 0.42));
  const x = width - bar - 18 * ratio;
  const y = height - 22 * ratio;
  ctx.save();
  ctx.fillStyle = "rgba(255,255,255,0.92)";
  ctx.fillRect(x - 8 * ratio, y - 18 * ratio, bar + 16 * ratio, 28 * ratio);
  ctx.strokeStyle = "#16202c";
  ctx.lineWidth = 2.2 * ratio;
  ctx.beginPath();
  ctx.moveTo(x, y - 5 * ratio);
  ctx.lineTo(x, y + 3 * ratio);
  ctx.lineTo(x + bar, y + 3 * ratio);
  ctx.lineTo(x + bar, y - 5 * ratio);
  ctx.stroke();
  ctx.fillStyle = "#16202c";
  ctx.font = `600 ${12 * ratio}px Helvetica, Arial, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText(label, x + bar / 2, y - 6 * ratio);
  ctx.restore();
}

function drawNorthArrow(ctx: CanvasRenderingContext2D, x: number, y: number, ratio: number) {
  const radius = 15 * ratio;
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = "rgba(255,255,255,0.94)";
  ctx.beginPath();
  ctx.arc(0, 0, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#16202c";
  ctx.lineWidth = 1.25 * ratio;
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(0, -radius + 4 * ratio);
  ctx.lineTo(5.5 * ratio, 6 * ratio);
  ctx.lineTo(0, 2 * ratio);
  ctx.closePath();
  ctx.fillStyle = "#9a3412";
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(0, -radius + 4 * ratio);
  ctx.lineTo(-5.5 * ratio, 6 * ratio);
  ctx.lineTo(0, 2 * ratio);
  ctx.closePath();
  ctx.fillStyle = "#16202c";
  ctx.fill();
  ctx.fillStyle = "#16202c";
  ctx.font = `700 ${8 * ratio}px Helvetica, Arial, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("N", 0, radius * 0.45);
  ctx.restore();
}

async function withMap<T>(width: number, height: number, draw: (map: MapLibreMap) => Promise<T>): Promise<T> {
  const host = document.createElement("div");
  host.setAttribute("data-site-pdf-map", "true");
  host.style.cssText = `position:fixed;left:-14000px;top:0;width:${width}px;height:${height}px;overflow:hidden;pointer-events:none;`;
  document.body.appendChild(host);
  let map: MapLibreMap | null = null;
  try {
    map = new maplibregl.Map({
      container: host,
      style: streetStyle(),
      center: [-81.4, 28.5],
      zoom: 10,
      interactive: false,
      attributionControl: false,
      fadeDuration: 0,
      pixelRatio: 2,
      canvasContextAttributes: {
        preserveDrawingBuffer: true,
        antialias: true,
        failIfMajorPerformanceCaveat: false,
      },
    });
    const active = map;
    await Promise.race([
      waitFor(active, "load", 12000),
      new Promise<void>((_, reject) => {
        active.on("error", (event) => {
          const message = event.error?.message ?? "";
          if (/webgl/i.test(message)) {
            reject(new SitePdfError("Could not export the PDF. The map did not finish loading. Try again."));
          }
        });
      }),
    ]);
    active.resize();
    return await draw(active);
  } catch (error) {
    if (error instanceof SitePdfError) throw error;
    throw new SitePdfError("Could not export the PDF. The map did not finish loading. Try again.");
  } finally {
    map?.remove();
    host.remove();
  }
}

function fit(map: MapLibreMap, box: [number, number, number, number], padding: number, maxZoom: number) {
  const [west, south, east, north] = box;
  map.fitBounds(
    [
      [west, south],
      [east, north],
    ],
    { padding, maxZoom, duration: 0, animate: false },
  );
}

function addTract(map: MapLibreMap, tract: TractGeometryRecord) {
  const rural = tract.rural;
  const fill = rural ? ruralTractFill("streets") : { color: OZ_TRACT_SWATCH.urban, opacity: 0.28 };
  const line = rural ? ruralTractLine("streets") : { color: "#1d4ed8", width: 1.4, opacity: 0.95 };
  map.addSource("pdf-tract", {
    type: "geojson",
    data: { type: "Feature", properties: {}, geometry: tract.geometry },
  });
  map.addLayer({
    id: "pdf-tract-fill",
    type: "fill",
    source: "pdf-tract",
    paint: { "fill-color": fill.color, "fill-opacity": fill.opacity },
  });
  map.addLayer({
    id: "pdf-tract-line",
    type: "line",
    source: "pdf-tract",
    paint: { "line-color": line.color, "line-width": line.width, "line-opacity": line.opacity },
  });
}

function addParcel(map: MapLibreMap, geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon) {
  map.addSource("pdf-parcel", {
    type: "geojson",
    data: { type: "Feature", properties: {}, geometry },
  });
  map.addLayer({
    id: "pdf-parcel-fill",
    type: "fill",
    source: "pdf-parcel",
    paint: { "fill-color": "#f0c27a", "fill-opacity": 0.45 },
  });
  map.addLayer({
    id: "pdf-parcel-line",
    type: "line",
    source: "pdf-parcel",
    paint: { "line-color": "#9a3412", "line-width": 3, "line-opacity": 1 },
  });
}

export async function captureSiteMaps(input: {
  parcel: GeoJSON.Polygon | GeoJSON.MultiPolygon;
  centroid: [number, number];
  eligibleTract: TractGeometryRecord | null;
}): Promise<{ main: string; locator: string; scaleLabel: string }> {
  const parcelBox = contextBbox(input.parcel);
  if (!parcelBox) throw new SitePdfError("Could not export the PDF. This parcel has no boundary to draw.");

  const main = await withMap(MAIN_W, MAIN_H, async (map) => {
    if (input.eligibleTract) addTract(map, input.eligibleTract);
    addParcel(map, input.parcel);
    fit(map, parcelBox, 72, 16);
    await waitForTiles(map);
    return snapshot(map, true);
  });

  const [lon, lat] = input.centroid;
  const locator = await withMap(LOCATOR_W, LOCATOR_H, async (map) => {
    map.addSource("pdf-marker", {
      type: "geojson",
      data: { type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [lon, lat] } },
    });
    map.addLayer({
      id: "pdf-marker",
      type: "circle",
      source: "pdf-marker",
      paint: {
        "circle-radius": 7,
        "circle-color": "#9a3412",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });
    fit(map, locatorBbox(lon, lat), 12, 8);
    await waitForTiles(map);
    return snapshot(map, false);
  });

  return { main: main.url, locator: locator.url, scaleLabel: main.scaleLabel };
}
