import { describe, expect, it } from "vitest";
import {
  PARCEL_AUTO_ZOOM,
  PARCEL_MIN_ZOOM,
  PARCEL_ZOOM_HINT,
  createParcelTileCache,
  parcelTileBbox,
  parcelTileKeysForBbox,
  parcelVisibilityHint,
  parcelsAreVisible,
  shouldQueryParcelsForZoom,
  syncParcelTileCache,
  toggleParcelVisibility,
} from "../lib/parcelVisibility";

describe("parcel visibility", () => {
  it("shows every parcel outline from zoom 10", () => {
    expect(PARCEL_MIN_ZOOM).toBe(10);
    expect(PARCEL_AUTO_ZOOM).toBe(PARCEL_MIN_ZOOM);
    expect(parcelsAreVisible("auto", 9.9, false)).toBe(false);
    expect(parcelsAreVisible("auto", 10, false)).toBe(true);
    expect(parcelsAreVisible("auto", 12, false)).toBe(true);
    expect(parcelsAreVisible("manual-on", 9, false)).toBe(false);
    expect(parcelsAreVisible("manual-on", 10, false)).toBe(true);
  });

  it("keeps a manual off in place and lets manual on draw only at parcel zoom", () => {
    expect(parcelsAreVisible("manual-off", 14, true)).toBe(false);
    expect(toggleParcelVisibility("auto", 10, false)).toBe("manual-off");
    expect(toggleParcelVisibility("manual-off", 10, true)).toBe("auto");
    expect(toggleParcelVisibility("manual-off", 8, false)).toBe("manual-on");
    expect(parcelsAreVisible("manual-on", 8, false)).toBe(false);
    expect(toggleParcelVisibility("manual-on", 11, false)).toBe("manual-off");
  });

  it("queries parcels only once the camera is at the parcel zoom", () => {
    expect(shouldQueryParcelsForZoom("auto", 9.9)).toBe(false);
    expect(shouldQueryParcelsForZoom("auto", 10)).toBe(true);
    expect(shouldQueryParcelsForZoom("manual-on", 8)).toBe(false);
    expect(shouldQueryParcelsForZoom("manual-off", 8)).toBe(false);
    expect(shouldQueryParcelsForZoom("manual-off", 10)).toBe(true);
  });

  it("explains the zoom 10 threshold next to the toggle", () => {
    expect(parcelVisibilityHint("auto", false)).toBe(PARCEL_ZOOM_HINT);
    expect(parcelVisibilityHint("auto", false)).toMatch(/Zoom in to see parcels/);
    expect(parcelVisibilityHint("auto", false)).toMatch(/zoom 10/);
    expect(parcelVisibilityHint("manual-off")).toMatch(/until you turn Show parcels back on/i);
    expect(parcelVisibilityHint("manual-on", false)).toMatch(/Zoom in to see parcels/);
    expect(parcelVisibilityHint("manual-on", false)).toMatch(/zoom 10/);
    expect(parcelVisibilityHint("auto", true)).toMatch(/zoom 10/);
  });

  it("caches parcel tiles without a zoom key so a loaded area is not fetched again", () => {
    const bbox: [number, number, number, number] = [-81.6, 28.2, -81.1, 28.7];
    const keys = parcelTileKeysForBbox(bbox);
    expect(keys.length).toBeGreaterThan(1);
    expect(parcelTileKeysForBbox(bbox)).toEqual(keys);
    const tile = parcelTileBbox(keys[0]);
    expect(tile[2] - tile[0]).toBeCloseTo(0.25);
    expect(parcelTileKeysForBbox(tile)).toEqual([keys[0]]);
    const cache = createParcelTileCache<string>();
    syncParcelTileCache(cache, "orlando");
    cache.tiles.set(keys[0], "exact");
    syncParcelTileCache(cache, "orlando");
    expect(cache.tiles.get(keys[0])).toBe("exact");
    syncParcelTileCache(cache, "atlanta");
    expect(cache.tiles.size).toBe(0);
  });
});
