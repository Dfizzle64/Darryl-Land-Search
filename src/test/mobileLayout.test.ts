import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { activeFiltersLabel, countActiveFilters } from "../lib/activeFilters";
import { sheetExpandedAfterGesture } from "../lib/detailSheet";
import { PARCEL_MIN_ZOOM } from "../lib/parcelVisibility";
import { TRACT_MIN_ZOOM } from "../lib/censusTracts";
import { DEFAULT_SCREENING_TOGGLES } from "../lib/screening";
import { DEFAULT_FILTERS } from "../lib/types";

const appShell = readFileSync(new URL("../components/AppShell.tsx", import.meta.url), "utf8");
const filterSidebar = readFileSync(new URL("../components/FilterSidebar.tsx", import.meta.url), "utf8");
const parcelDrawer = readFileSync(new URL("../components/ParcelDrawer.tsx", import.meta.url), "utf8");
const tractDrawer = readFileSync(new URL("../components/TractDrawer.tsx", import.meta.url), "utf8");
const siteMap = readFileSync(new URL("../components/SiteMap.tsx", import.meta.url), "utf8");
const login = readFileSync(new URL("../app/login/page.tsx", import.meta.url), "utf8");
const layout = readFileSync(new URL("../app/layout.tsx", import.meta.url), "utf8");

const idle = {
  filters: { ...DEFAULT_FILTERS, landUseFilter: "off" as const },
  resetLandUse: "off" as const,
  showExcluded: false,
  showTraffic: true,
  showOz: false,
  showOz2: true,
  screening: { ...DEFAULT_SCREENING_TOGGLES },
};

describe("narrow screen sheets", () => {
  it("expands on an upward drag, collapses on a downward drag, and toggles on a tap", () => {
    expect(sheetExpandedAfterGesture(false, 40)).toBe(true);
    expect(sheetExpandedAfterGesture(true, -40)).toBe(false);
    expect(sheetExpandedAfterGesture(false, 0)).toBe(true);
    expect(sheetExpandedAfterGesture(true, 4)).toBe(false);
  });

  it("counts engaged sidebar controls and leaves the idle map at zero", () => {
    expect(countActiveFilters(idle)).toBe(0);
    expect(activeFiltersLabel(0)).toBe("0 filters active");
    expect(
      countActiveFilters({
        ...idle,
        filters: { ...idle.filters, considerOpportunityZone: true, ozFilter: "rural-eligible", minAcreage: 5, rentFiltersOn: true, minMedianGrossRent: 1200 },
        screening: { ...DEFAULT_SCREENING_TOGGLES, flood: true },
        showTraffic: false,
      }),
    ).toBe(7);
    expect(activeFiltersLabel(1)).toBe("1 filter active");
  });
});

describe("mobile layout source", () => {
  it("keeps a compact phone header and a filters sheet with a close control", () => {
    expect(appShell).toContain("MobileHeaderActions");
    expect(appShell).toContain("Land search");
    expect(appShell).toContain("dls-app-header");
    expect(filterSidebar).toContain("data-filter-drawer");
    expect(filterSidebar).toContain("Close filters");
    expect(filterSidebar).toContain("data-filters-active");
    expect(filterSidebar).toContain("filter-fold");
    expect(filterSidebar).toContain("Reset filters");
    expect(filterSidebar).toContain('id="rent-filters"');
  });

  it("peeks parcel and tract sheets and keeps the desktop pane class", () => {
    expect(parcelDrawer).toContain("data-sheet-peek");
    expect(parcelDrawer).toContain("data-sheet-actions");
    expect(parcelDrawer).toContain("Google Maps");
    expect(parcelDrawer).toContain("googleMapsUrl");
    expect(parcelDrawer).toContain("Export PDF");
    expect(parcelDrawer).toContain('import("@/lib/sitePdfExport")');
    expect(parcelDrawer).toContain("sheet-rest");
    expect(tractDrawer).toContain("sheet-rest");
    expect(tractDrawer).toContain("Expand details");
    for (const source of [parcelDrawer, tractDrawer]) {
      expect(source).toContain('pane ? "drawer-scroll h-full overflow-y-auto bg-ink-900 p-5"');
    }
  });

  it("shrinks map chrome on a phone without changing zoom thresholds or adding a mobile fetch", () => {
    expect(siteMap).toContain("MobileMapTools");
    expect(siteMap).toContain("data-mobile-zoom");
    expect(siteMap).toContain("absolute bottom-4 left-3");
    expect(siteMap).toContain("dls-wide");
    expect(PARCEL_MIN_ZOOM).toBe(10);
    expect(TRACT_MIN_ZOOM).toBe(4);
    expect(appShell).toContain("shouldQueryParcelsForZoom");
    expect(appShell).not.toContain("matchMedia");
    expect(siteMap).not.toContain("fetch(\"/api/parcels");
  });

  it("keeps the password gate page readable inside the safe area", () => {
    expect(layout).toContain('viewportFit: "cover"');
    expect(login).toContain("safe-area-inset-top");
    expect(login).toContain("safe-area-inset-bottom");
    expect(login).toContain("<LoginForm />");
  });
});
