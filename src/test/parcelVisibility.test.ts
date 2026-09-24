import { describe, expect, it } from "vitest";
import {
  PARCEL_AUTO_ZOOM,
  PARCEL_MIN_ZOOM,
  PARCEL_ZOOM_HINT,
  parcelVisibilityHint,
  parcelsAreVisible,
  shouldQueryParcelsForZoom,
  toggleParcelVisibility,
} from "../lib/parcelVisibility";

describe("parcel visibility", () => {
  it("hides parcel polygons below the tract zoom and shows them at zoom 13", () => {
    expect(PARCEL_MIN_ZOOM).toBe(13);
    expect(PARCEL_AUTO_ZOOM).toBe(PARCEL_MIN_ZOOM);
    expect(parcelsAreVisible("auto", 8, false)).toBe(false);
    expect(parcelsAreVisible("auto", 12.9, false)).toBe(false);
    expect(parcelsAreVisible("auto", 13, false)).toBe(true);
    expect(parcelsAreVisible("auto", 9, true)).toBe(false);
    expect(parcelsAreVisible("manual-on", 10, false)).toBe(false);
    expect(parcelsAreVisible("manual-on", 14, false)).toBe(true);
  });

  it("keeps a manual off in place and lets manual on draw only at parcel zoom", () => {
    expect(parcelsAreVisible("manual-off", 14, true)).toBe(false);
    expect(toggleParcelVisibility("auto", 13, false)).toBe("manual-off");
    expect(toggleParcelVisibility("manual-off", 13, true)).toBe("auto");
    expect(toggleParcelVisibility("manual-off", 9, false)).toBe("manual-on");
    expect(parcelsAreVisible("manual-on", 9, false)).toBe(false);
    expect(toggleParcelVisibility("manual-on", 14, false)).toBe("manual-off");
  });

  it("queries parcels only once the camera is at the parcel zoom", () => {
    expect(shouldQueryParcelsForZoom("auto", 12)).toBe(false);
    expect(shouldQueryParcelsForZoom("auto", 13)).toBe(true);
    expect(shouldQueryParcelsForZoom("manual-on", 8)).toBe(false);
    expect(shouldQueryParcelsForZoom("manual-off", 8)).toBe(false);
    expect(shouldQueryParcelsForZoom("manual-off", 13)).toBe(true);
  });

  it("explains the closer zoom next to the toggle", () => {
    expect(parcelVisibilityHint("auto", false)).toBe(PARCEL_ZOOM_HINT);
    expect(parcelVisibilityHint("auto", false)).toMatch(/Zoom in to see parcels/);
    expect(parcelVisibilityHint("manual-off")).toMatch(/until you turn Show parcels back on/i);
    expect(parcelVisibilityHint("manual-on", false)).toMatch(/Zoom in to see parcels/);
    expect(parcelVisibilityHint("auto", true)).toMatch(/closer zoom/i);
  });
});
