import { describe, expect, it } from "vitest";
import {
  PARCEL_AUTO_ZOOM,
  PARCEL_ZOOM_HINT,
  parcelVisibilityHint,
  parcelsAreVisible,
  shouldQueryParcelsForZoom,
  toggleParcelVisibility,
} from "../lib/parcelVisibility";

describe("parcel visibility", () => {
  it("hides parcels at shed zoom and shows them at neighborhood zoom or with an AOI", () => {
    expect(PARCEL_AUTO_ZOOM).toBe(10.5);
    expect(parcelsAreVisible("auto", 9.4, false)).toBe(false);
    expect(parcelsAreVisible("auto", 10, false)).toBe(false);
    expect(parcelsAreVisible("auto", 11, false)).toBe(true);
    expect(parcelsAreVisible("auto", PARCEL_AUTO_ZOOM, false)).toBe(true);
    expect(parcelsAreVisible("auto", 9, true)).toBe(true);
  });

  it("keeps a manual off in place and lets manual on draw at any zoom", () => {
    expect(parcelsAreVisible("manual-off", 14, true)).toBe(false);
    expect(toggleParcelVisibility("auto", 13, false)).toBe("manual-off");
    expect(toggleParcelVisibility("manual-off", 13, true)).toBe("auto");
    expect(toggleParcelVisibility("manual-off", 9, false)).toBe("manual-on");
    expect(parcelsAreVisible("manual-on", 9, false)).toBe(true);
    expect(toggleParcelVisibility("manual-on", 9, false)).toBe("manual-off");
  });

  it("queries the shed when Show parcels is forced on, and skips auto mode below the gate", () => {
    expect(shouldQueryParcelsForZoom("auto", 10)).toBe(false);
    expect(shouldQueryParcelsForZoom("auto", 10.5)).toBe(true);
    expect(shouldQueryParcelsForZoom("manual-on", 8)).toBe(true);
    expect(shouldQueryParcelsForZoom("manual-off", 8)).toBe(false);
    expect(shouldQueryParcelsForZoom("manual-off", 12)).toBe(true);
  });

  it("explains zoom, AOI, and the manual override next to the toggle", () => {
    expect(parcelVisibilityHint("auto", false)).toBe(PARCEL_ZOOM_HINT);
    expect(parcelVisibilityHint("auto", false)).toMatch(/Zoom in to neighborhood level, lock an area, or turn Show parcels on/);
    expect(parcelVisibilityHint("manual-off")).toMatch(/until you turn Show parcels back on/i);
    expect(parcelVisibilityHint("manual-on")).toMatch(/every zoom/i);
    expect(parcelVisibilityHint("auto", true)).toMatch(/neighborhood zoom/i);
  });
});
