import { describe, expect, it } from "vitest";
import {
  PARCEL_AUTO_ZOOM,
  PARCEL_DETAIL_ZOOM,
  PARCEL_LOW_ZOOM_LIMIT,
  PARCEL_MIN_ZOOM,
  PARCEL_ZOOM_HINT,
  createParcelRangeCache,
  parcelGeometryBand,
  parcelRangeKey,
  parcelVisibilityHint,
  parcelsAreVisible,
  shouldQueryParcelsForZoom,
  syncParcelRangeCache,
  toggleParcelVisibility,
} from "../lib/parcelVisibility";

describe("parcel visibility", () => {
  it("shows parcel polygons from zoom 8 and keeps full geometry for zoom 13", () => {
    expect(PARCEL_MIN_ZOOM).toBe(8);
    expect(PARCEL_DETAIL_ZOOM).toBe(13);
    expect(PARCEL_LOW_ZOOM_LIMIT).toBe(1600);
    expect(PARCEL_AUTO_ZOOM).toBe(PARCEL_MIN_ZOOM);
    expect(parcelsAreVisible("auto", 7.9, false)).toBe(false);
    expect(parcelsAreVisible("auto", 8, false)).toBe(true);
    expect(parcelsAreVisible("auto", 12.9, false)).toBe(true);
    expect(parcelsAreVisible("manual-on", 7, false)).toBe(false);
    expect(parcelsAreVisible("manual-on", 8, false)).toBe(true);
    expect(parcelGeometryBand(8)).toBe("low");
    expect(parcelGeometryBand(12.9)).toBe("low");
    expect(parcelGeometryBand(13)).toBe("detail");
  });

  it("keeps a manual off in place and lets manual on draw only at parcel zoom", () => {
    expect(parcelsAreVisible("manual-off", 14, true)).toBe(false);
    expect(toggleParcelVisibility("auto", 8, false)).toBe("manual-off");
    expect(toggleParcelVisibility("manual-off", 8, true)).toBe("auto");
    expect(toggleParcelVisibility("manual-off", 6, false)).toBe("manual-on");
    expect(parcelsAreVisible("manual-on", 6, false)).toBe(false);
    expect(toggleParcelVisibility("manual-on", 9, false)).toBe("manual-off");
  });

  it("queries parcels only once the camera is at the parcel zoom", () => {
    expect(shouldQueryParcelsForZoom("auto", 7.9)).toBe(false);
    expect(shouldQueryParcelsForZoom("auto", 8)).toBe(true);
    expect(shouldQueryParcelsForZoom("manual-on", 7)).toBe(false);
    expect(shouldQueryParcelsForZoom("manual-off", 7)).toBe(false);
    expect(shouldQueryParcelsForZoom("manual-off", 8)).toBe(true);
  });

  it("explains the zoom 8 threshold next to the toggle", () => {
    expect(parcelVisibilityHint("auto", false)).toBe(PARCEL_ZOOM_HINT);
    expect(parcelVisibilityHint("auto", false)).toMatch(/Zoom in to see parcels/);
    expect(parcelVisibilityHint("auto", false)).toMatch(/zoom 8/);
    expect(parcelVisibilityHint("manual-off")).toMatch(/until you turn Show parcels back on/i);
    expect(parcelVisibilityHint("manual-on", false)).toMatch(/Zoom in to see parcels/);
    expect(parcelVisibilityHint("manual-on", false)).toMatch(/zoom 8/);
    expect(parcelVisibilityHint("auto", true)).toMatch(/zoom 8/);
  });

  it("reuses a loaded view inside the same zoom band and does not key the cache on the exact zoom", () => {
    const bbox: [number, number, number, number] = [-81.6, 28.2, -81.1, 28.7];
    const low = parcelRangeKey(bbox, 8);
    expect(low).toBe(parcelRangeKey(bbox, 12));
    expect(low).not.toBe(parcelRangeKey(bbox, 13));
    expect(low).not.toMatch(/\|8\b|\|12\b/);
    const cache = createParcelRangeCache<string>();
    syncParcelRangeCache(cache, "orlando");
    cache.ranges.set(low, "sample");
    syncParcelRangeCache(cache, "orlando");
    expect(cache.ranges.get(low)).toBe("sample");
    syncParcelRangeCache(cache, "atlanta");
    expect(cache.ranges.size).toBe(0);
  });
});
