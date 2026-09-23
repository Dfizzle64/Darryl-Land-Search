import { describe, expect, it } from "vitest";
import {
  ESRI_HYBRID_ATTRIBUTION,
  ESRI_PLACES_TILES,
  ESRI_TRANSPORTATION_TILES,
  ESRI_WORLD_IMAGERY_ATTRIBUTION,
  ESRI_WORLD_IMAGERY_TILES,
  OVERLAY_LAYER_IDS,
  ESRI_STREETS_ATTRIBUTION,
  ESRI_WORLD_STREET_TILES,
  basemapAttribution,
  excludedFillPaint,
  excludedLinePaint,
  hybridImageryTileUrl,
  OZ_TRACT_SWATCH,
  oz2FillPaint,
  oz2LinePaint,
  ozFillPaint,
  ozLinePaint,
  parcelFillPaint,
  parcelLinePaint,
  parcelMatchFilter,
  rasterLayerVisibility,
  streetsTileUrl,
  trafficLinePaint,
} from "../lib/basemap";

describe("basemap helpers", () => {
  it("uses the public Esri World Imagery tile URL and credits Esri", () => {
    expect(ESRI_WORLD_IMAGERY_TILES).toBe(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    );
    expect(ESRI_WORLD_IMAGERY_ATTRIBUTION).toMatch(/Esri/);
    expect(ESRI_WORLD_IMAGERY_ATTRIBUTION).toMatch(/Maxar/);
    expect(ESRI_WORLD_IMAGERY_ATTRIBUTION).toMatch(/Earthstar Geographics/);
  });

  it("keeps overlay layer ids so a style swap can leave parcels and traffic in place", () => {
    expect(OVERLAY_LAYER_IDS).toEqual([
      "flood-raster",
      "wetlands-raster",
      "school-zone-raster",
      "school-ms-raster",
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
    ]);
  });

  it("uses keyless Esri streets and an imagery-plus-labels hybrid", () => {
    expect(ESRI_WORLD_STREET_TILES).toBe(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    );
    expect(ESRI_WORLD_STREET_TILES).toContain("{z}/{y}/{x}");
    expect(ESRI_WORLD_STREET_TILES).not.toMatch(/voyager|cartocdn|carto\.com/i);
    expect(ESRI_STREETS_ATTRIBUTION).toMatch(/Esri/);
    expect(ESRI_STREETS_ATTRIBUTION).toMatch(/OpenStreetMap/);
    expect(streetsTileUrl(null)).toBe(ESRI_WORLD_STREET_TILES);
    expect(streetsTileUrl(null)).not.toMatch(/voyager|cartocdn|carto\.com/i);
    expect(hybridImageryTileUrl(null)).toBe(ESRI_WORLD_IMAGERY_TILES);
    expect(ESRI_TRANSPORTATION_TILES).toContain("World_Transportation");
    expect(ESRI_PLACES_TILES).toContain("World_Boundaries_and_Places");
    expect(ESRI_HYBRID_ATTRIBUTION).toMatch(/Esri/);
    expect(streetsTileUrl("demo-key")).toContain("maps/streets-v2/256/");
    expect(streetsTileUrl("demo-key")).toContain("key=demo-key");
    expect(streetsTileUrl("demo-key")).not.toContain("World_Street_Map");
    expect(hybridImageryTileUrl("demo-key")).toContain("maps/hybrid/256/");
    expect(basemapAttribution("streets", null)).toBe(ESRI_STREETS_ATTRIBUTION);
    expect(basemapAttribution("streets", null)).not.toMatch(/CARTO|Voyager/);
    expect(basemapAttribution("satellite", null)).toMatch(/Esri/);
    expect(basemapAttribution("dark", null)).toMatch(/OpenFreeMap/);
    expect(basemapAttribution("streets", "demo-key")).toMatch(/MapTiler/);
    expect(rasterLayerVisibility("streets", true)).toEqual({
      "basemap-streets": "visible",
      "basemap-satellite": "none",
      "basemap-hybrid-roads": "none",
      "basemap-hybrid-places": "none",
    });
    expect(rasterLayerVisibility("satellite", true)).toEqual({
      "basemap-streets": "none",
      "basemap-satellite": "visible",
      "basemap-hybrid-roads": "visible",
      "basemap-hybrid-places": "visible",
    });
    expect(rasterLayerVisibility("satellite", false)["basemap-hybrid-roads"]).toBe("none");
    expect(rasterLayerVisibility("dark", true)["basemap-streets"]).toBe("none");
    expect(rasterLayerVisibility("dark", true)["basemap-satellite"]).toBe("none");
  });

  it("lowers parcel fill opacity and brightens outlines on satellite", () => {
    const streetFill = parcelFillPaint("streets")["fill-opacity"];
    const satelliteFill = parcelFillPaint("satellite")["fill-opacity"];
    expect(JSON.stringify(streetFill)).toContain("0.52");
    expect(JSON.stringify(streetFill)).toContain("0.16");
    expect(JSON.stringify(satelliteFill)).toContain("0.26");
    expect(JSON.stringify(parcelLinePaint("satellite")["line-width"])).toContain("1.7");
    expect(JSON.stringify(parcelLinePaint("satellite")["line-width"])).toContain("0.55");
    expect(JSON.stringify(parcelLinePaint("streets")["line-width"])).toContain("0.35");
    expect(JSON.stringify(parcelLinePaint("streets")["line-color"])).toContain("#0f5132");
    expect(JSON.stringify(parcelLinePaint("dark")["line-color"])).toContain("#b7e3cf");
    expect(JSON.stringify(oz2LinePaint("streets")["line-color"])).toContain("#9a3412");
    expect(ozLinePaint("streets")["line-color"]).toBe("#9a3412");
    expect(ozLinePaint("dark")["line-color"]).toBe("#f6d0b0");
    expect(parcelMatchFilter).toEqual(["==", ["get", "filterMatch"], 1]);
    expect(Number(excludedFillPaint("satellite")["fill-opacity"])).toBeLessThan(0.2);
    expect(Number(excludedLinePaint("satellite")["line-opacity"])).toBeGreaterThan(
      Number(excludedLinePaint("streets")["line-opacity"]),
    );
    expect(Number(trafficLinePaint("satellite")["line-opacity"])).toBeGreaterThan(
      Number(trafficLinePaint("streets")["line-opacity"]),
    );
    expect(Number(ozFillPaint("satellite")["fill-opacity"])).toBeGreaterThan(
      Number(ozFillPaint("streets")["fill-opacity"]),
    );
    expect(Number(ozLinePaint("satellite")["line-opacity"])).toBeGreaterThan(
      Number(ozLinePaint("streets")["line-opacity"]),
    );
    const streetOz2Opacity = oz2FillPaint("streets")["fill-opacity"];
    const satelliteOz2Opacity = oz2FillPaint("satellite")["fill-opacity"];
    expect(Array.isArray(streetOz2Opacity) ? streetOz2Opacity[3] : streetOz2Opacity).toBeLessThan(
      Array.isArray(satelliteOz2Opacity) ? Number(satelliteOz2Opacity[3]) : Number(satelliteOz2Opacity),
    );
    expect(JSON.stringify(oz2FillPaint("streets")["fill-color"])).toContain(OZ_TRACT_SWATCH.rural);
    expect(JSON.stringify(oz2FillPaint("streets")["fill-color"])).toContain(OZ_TRACT_SWATCH.eligible);
    expect(ozFillPaint("streets")["fill-color"]).toBe(OZ_TRACT_SWATCH.designated);
    expect(ozLinePaint("streets")["line-dasharray"]).toEqual([2, 1.2]);
    expect(Number(oz2LinePaint("satellite")["line-opacity"])).toBeGreaterThan(
      Number(oz2LinePaint("streets")["line-opacity"]),
    );
  });

  it("paints census tracts in distinct oranges and leaves parcel fills green", () => {
    const parcelFill = JSON.stringify(parcelFillPaint("streets")["fill-color"]);
    expect(parcelFill).toContain("#3f9d74");

    const rural = OZ_TRACT_SWATCH.rural;
    const eligible = OZ_TRACT_SWATCH.eligible;
    const designated = OZ_TRACT_SWATCH.designated;
    expect(new Set([rural, eligible, designated]).size).toBe(3);

    const tractPaint = [
      JSON.stringify(oz2FillPaint("streets")),
      JSON.stringify(oz2FillPaint("satellite")),
      JSON.stringify(ozFillPaint("streets")),
      JSON.stringify(ozFillPaint("satellite")),
    ].join(" ");
    expect(tractPaint).not.toMatch(/#3dbe86|#5ee0a0|#5b8def|#9ec1ff|#3f9d74/i);
    expect(JSON.stringify(oz2FillPaint("streets")["fill-opacity"])).toContain("0.32");
    expect(JSON.stringify(oz2FillPaint("streets")["fill-opacity"])).toContain("0.22");
    expect(JSON.stringify(oz2LinePaint("streets")["line-width"])).toContain("2.5");
    expect(JSON.stringify(oz2LinePaint("streets")["line-width"])).toContain("1.05");
  });
});
