import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  absorbEligibleTractTiles,
  createEligibleTractTileCache,
  detailTractsVisibleAtZoom,
  eligibleOverviewFilter,
  eligibleOverviewShownFilter,
  eligibleTractOverlayFilter,
  isDrawnEligibleTract,
  overviewTractsVisibleAtZoom,
  syncEligibleTractTileCache,
  TRACT_DETAIL_MIN_ZOOM,
  TRACT_MIN_ZOOM,
  TRACT_TILE_DEGREES,
  TRACT_VIEWPORT_DEBOUNCE_MS,
  tractGridKeysForBbox,
  tractsVisibleAtZoom,
  type IndexedTractFeature,
} from "../lib/censusTracts";

function tract(geoid: string, rural: boolean | null, state: string, lng = -81.4, lat = 28.5): IndexedTractFeature {
  return {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [lng, lat],
          [lng + 0.2, lat],
          [lng + 0.2, lat + 0.2],
          [lng, lat],
        ],
      ],
    },
    properties: {
      tractGeoid: geoid,
      state,
      rural,
    },
  };
}

describe("eligible tract overlay", () => {
  it("shows eligible tracts from a Southeast view and detail geometry from zoom 8", () => {
    expect(TRACT_MIN_ZOOM).toBe(4);
    expect(TRACT_DETAIL_MIN_ZOOM).toBe(8);
    expect(TRACT_VIEWPORT_DEBOUNCE_MS).toBeGreaterThanOrEqual(250);
    expect(TRACT_VIEWPORT_DEBOUNCE_MS).toBeLessThanOrEqual(400);
    expect(tractsVisibleAtZoom(3.9)).toBe(false);
    expect(tractsVisibleAtZoom(4)).toBe(true);
    expect(overviewTractsVisibleAtZoom(4)).toBe(true);
    expect(overviewTractsVisibleAtZoom(7.9)).toBe(true);
    expect(overviewTractsVisibleAtZoom(8)).toBe(false);
    expect(detailTractsVisibleAtZoom(7.9)).toBe(false);
    expect(detailTractsVisibleAtZoom(8)).toBe(true);
  });

  it("keys detail tiles on a stable grid and does not refetch a loaded tile", () => {
    const bbox: [number, number, number, number] = [-82.2, 28.1, -81.1, 28.9];
    const keys = tractGridKeysForBbox(bbox);
    expect(keys).toEqual(tractGridKeysForBbox(bbox));
    expect(keys.every((key) => /^\-?\d+:\-?\d+$/.test(key))).toBe(true);
    expect(keys.join("|")).not.toMatch(/zoom|far|mid|near/);
    expect(tractGridKeysForBbox([-81.2, 28.2, -81.05, 28.4])).toEqual(["-41:14"]);
    expect(TRACT_TILE_DEGREES).toBe(2);

    const cache = createEligibleTractTileCache();
    const groups = {
      rural: [tract("12095016605", true, "Florida")],
      eligible: [tract("13051000100", false, "Georgia", -84.4, 33.7)],
      oz2: [tract("12095015204", false, "Florida", -81.3, 28.6)],
    };
    syncEligibleTractTileCache(cache, groups, "sig");
    syncEligibleTractTileCache(cache, groups, "sig");
    const first = absorbEligibleTractTiles(cache, keys);
    expect(first.rural || first.oz2).toBe(true);
    const loaded = cache.loaded.size;
    const again = absorbEligibleTractTiles(cache, keys);
    expect(again).toEqual({ rural: false, eligible: false, oz2: false });
    expect(cache.loaded.size).toBe(loaded);
    expect(cache.rural.size).toBe(1);
    expect([...cache.eligible.keys()]).toEqual([]);
  });

  it("does not draw a tract that has no eligibility flag or a non-nominated South Carolina tract", () => {
    expect(isDrawnEligibleTract({ tractGeoid: "12095016605", state: "Florida", rural: true })).toBe(true);
    expect(isDrawnEligibleTract({ tractGeoid: "12095016605", state: "Florida", rural: null })).toBe(false);
    expect(isDrawnEligibleTract({ tractGeoid: "12095016605", state: "Florida" })).toBe(false);
    expect(isDrawnEligibleTract({ state: "Florida", rural: true })).toBe(false);
    expect(isDrawnEligibleTract({ tractGeoid: "45019000100", state: "South Carolina", rural: false })).toBe(false);

    const cache = createEligibleTractTileCache();
    syncEligibleTractTileCache(
      cache,
      {
        rural: [],
        eligible: [
          tract("45019000100", false, "South Carolina", -79.9, 32.8),
          tract("37119000100", false, "North Carolina", -80.8, 35.2),
        ],
        oz2: [tract("12095010000", null, "Florida")],
      },
      "eligibility",
    );
    absorbEligibleTractTiles(cache, tractGridKeysForBbox([-85, 24, -75, 37]));
    expect([...cache.eligible.keys()]).toEqual(["37119000100"]);
    expect(cache.oz2.size).toBe(0);
  });

  it("filters rural and urban without a market clause", () => {
    const both = JSON.stringify(eligibleTractOverlayFilter());
    expect(both).not.toContain("markets");
    expect(both).not.toContain("Orlando");
    expect(both).toContain("South Carolina");
    expect(JSON.stringify(eligibleTractOverlayFilter({ classCut: "rural" }))).toContain("true");
    expect(JSON.stringify(eligibleTractOverlayFilter({ classCut: "urban" }))).toContain("false");
    expect(JSON.stringify(eligibleTractOverlayFilter({ classCut: "none" }))).toContain("__none__");
    expect(JSON.stringify(eligibleTractOverlayFilter({ hideOrangeCounty: true }))).toContain("Orange");
    expect(eligibleOverviewFilter("all")).toBeNull();
    expect(eligibleOverviewFilter("rural")).toEqual(["==", ["get", "rural"], true]);
    expect(eligibleOverviewFilter("urban")).toEqual(["==", ["get", "rural"], false]);
    expect(JSON.stringify(eligibleOverviewFilter("none"))).not.toContain("tractGeoid");
    const shown = JSON.stringify(eligibleOverviewShownFilter("all", null));
    expect(shown).toContain("South Carolina");
    expect(shown).not.toContain("medianHouseholdIncome");
    const filtered = JSON.stringify(eligibleOverviewShownFilter("rural", ["has", "medianHouseholdIncome"]));
    expect(filtered).toContain("medianHouseholdIncome");
    expect(filtered).toContain("true");
  });

  it("keeps ACS income on features merged into the detail cache", () => {
    const cache = createEligibleTractTileCache();
    const georgia = tract("13051000100", false, "Georgia", -84.4, 33.7);
    georgia.properties.medianHouseholdIncome = 42000;
    const missing = tract("28049003200", true, "Mississippi", -90.4, 32.3);
    syncEligibleTractTileCache(
      cache,
      { rural: [missing], eligible: [georgia], oz2: [] },
      "income",
    );
    absorbEligibleTractTiles(cache, tractGridKeysForBbox([-91, 31, -83, 35]));
    expect(cache.eligible.get("13051000100")?.properties.medianHouseholdIncome).toBe(42000);
    expect(cache.rural.get("28049003200")?.properties.medianHouseholdIncome).toBeUndefined();
  });

  it("ships one simplified eligible tract per feature for the far zoom", () => {
    const file = path.join(process.cwd(), "data/fixtures/oz2-eligible-overview.geojson");
    const raw = readFileSync(file, "utf8");
    expect(raw.length).toBeLessThan(1_600_000);
    const collection = JSON.parse(raw) as {
      features: Array<{
        properties: {
          state: string;
          rural: boolean;
          eligible: boolean;
          overview: boolean;
          tractGeoid: string;
          medianHouseholdIncome?: number;
        };
        geometry: GeoJSON.Geometry;
      }>;
    };
    expect(collection.features.length).toBeGreaterThan(2000);
    expect(collection.features.length).toBeLessThan(4000);
    let points = 0;
    const states = new Set<string>();
    const geoids = new Set<string>();
    for (const feature of collection.features) {
      expect(feature.properties.eligible).toBe(true);
      expect(feature.properties.overview).toBe(true);
      expect(typeof feature.properties.rural).toBe("boolean");
      expect(feature.properties.tractGeoid).toMatch(/^\d{11}$/);
      expect(feature.properties).not.toHaveProperty("tractCount");
      if (feature.properties.medianHouseholdIncome != null) {
        expect(feature.properties.medianHouseholdIncome).toBeGreaterThan(0);
      }
      geoids.add(feature.properties.tractGeoid);
      states.add(feature.properties.state);
      const walk = (coords: unknown) => {
        if (!Array.isArray(coords)) return;
        if (typeof coords[0] === "number") {
          points += 1;
          return;
        }
        for (const child of coords) walk(child);
      };
      walk((feature.geometry as { coordinates: unknown }).coordinates);
    }
    expect(geoids.size).toBe(collection.features.length);
    expect(points).toBeGreaterThan(1000);
    expect(points).toBeLessThan(80_000);
    expect(states.has("Florida")).toBe(true);
    expect(states.has("South Carolina")).toBe(true);
    expect(states.has("Georgia")).toBe(true);
    expect(states.has("Mississippi")).toBe(true);
  });
});
