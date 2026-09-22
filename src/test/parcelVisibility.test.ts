import { describe, expect, it } from "vitest";
import {
  PARCEL_AUTO_ZOOM,
  parcelVisibilityHint,
  parcelsAreVisible,
  toggleParcelVisibility,
} from "../lib/parcelVisibility";

describe("parcel visibility", () => {
  it("hides parcels at shed zoom and shows them once the zoom gate or an AOI is active", () => {
    expect(PARCEL_AUTO_ZOOM).toBeGreaterThanOrEqual(11);
    expect(PARCEL_AUTO_ZOOM).toBeLessThanOrEqual(12);
    expect(parcelsAreVisible("auto", 9.4, false)).toBe(false);
    expect(parcelsAreVisible("auto", 11, false)).toBe(false);
    expect(parcelsAreVisible("auto", PARCEL_AUTO_ZOOM, false)).toBe(true);
    expect(parcelsAreVisible("auto", 9, true)).toBe(true);
  });

  it("keeps a manual off in place until the user turns parcels back on", () => {
    expect(parcelsAreVisible("manual-off", 14, true)).toBe(false);
    expect(toggleParcelVisibility("auto", 13, false)).toBe("manual-off");
    expect(toggleParcelVisibility("manual-off", 13, true)).toBe("auto");
    expect(toggleParcelVisibility("manual-off", 9, false)).toBe("manual-on");
    expect(parcelsAreVisible("manual-on", 9, false)).toBe(true);
    expect(toggleParcelVisibility("manual-on", 9, false)).toBe("manual-off");
  });

  it("explains zoom, AOI, and the manual override next to the toggle", () => {
    expect(parcelVisibilityHint("auto")).toMatch(/11\.5/);
    expect(parcelVisibilityHint("auto")).toMatch(/lock an area/i);
    expect(parcelVisibilityHint("manual-off")).toMatch(/until you turn parcels back on/i);
    expect(parcelVisibilityHint("manual-on")).toMatch(/every zoom/i);
  });
});
