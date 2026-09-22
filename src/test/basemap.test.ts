import { describe, expect, it } from "vitest";
import {
  ESRI_WORLD_IMAGERY_ATTRIBUTION,
  ESRI_WORLD_IMAGERY_TILES,
  OVERLAY_LAYER_IDS,
  excludedFillPaint,
  excludedLinePaint,
  oz2FillPaint,
  oz2LinePaint,
  ozFillPaint,
  ozLinePaint,
  parcelFillPaint,
  parcelLinePaint,
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
      "oz2-fill",
      "oz2-line",
      "oz-fill",
      "oz-line",
      "traffic-line",
      "parcels-fill-excluded",
      "parcels-line-excluded",
      "parcels-fill",
      "parcels-line",
    ]);
  });

  it("lowers parcel fill opacity and brightens outlines on satellite", () => {
    const streetFill = parcelFillPaint("streets")["fill-opacity"];
    const satelliteFill = parcelFillPaint("satellite")["fill-opacity"];
    expect(JSON.stringify(streetFill)).toContain("0.52");
    expect(JSON.stringify(satelliteFill)).toContain("0.26");
    expect(JSON.stringify(parcelLinePaint("satellite")["line-width"])).toContain("1.7");
    expect(JSON.stringify(parcelLinePaint("streets")["line-width"])).toContain("1");
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
    expect(Number(oz2FillPaint("satellite")["fill-opacity"])).toBeGreaterThan(
      Number(oz2FillPaint("streets")["fill-opacity"]),
    );
    expect(JSON.stringify(oz2FillPaint("streets")["fill-color"])).toContain("#3dbe86");
    expect(JSON.stringify(oz2FillPaint("streets")["fill-color"])).toContain("#5b8def");
    expect(Number(oz2LinePaint("satellite")["line-opacity"])).toBeGreaterThan(
      Number(oz2LinePaint("streets")["line-opacity"]),
    );
  });
});
