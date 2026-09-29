import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  loadEligibleOverview,
  loadEligiblePackTracts,
  loadOpportunityZones,
  loadTractRentLookup,
  stampGeoidMetrics,
} from "../lib/data/loadFixtures";
import {
  ACS_MEDIAN_GROSS_RENT_TOP_CODE,
  DEFAULT_RENT_MINIMUMS,
  RENT_SLIDERS,
  TRACT_RENT_SOURCES,
  buildTractRentLookup,
  filterTractRowsByRent,
  finiteRentMetric,
  formatTractRentLines,
  rentFieldsFromRow,
  tractMetricEmptyMessage,
  tractMinimumLayerFilter,
  tractRentFilterActive,
  tractRentLayerFilter,
  tractRentPasses,
} from "../lib/tractRent";

const SAMPLE_GEOID = "01001020100";

describe("tract rent stamp", () => {
  it("copies only plain numbers and drops join codes", () => {
    const acs = TRACT_RENT_SOURCES[0];
    expect(
      rentFieldsFromRow(
        { e: 1049, m: 99, e2019: 749, g: 40.1, j: 1, z: 36067, c: 1001 },
        acs.fields,
      ),
    ).toEqual({
      medianGrossRent: 1049,
      medianGrossRentMoe: 99,
      medianGrossRentGrowth: 40.1,
    });
    expect(finiteRentMetric(0, "level")).toBeNull();
    expect(finiteRentMetric(-4, "growth")).toBe(-4);
    expect(finiteRentMetric(0, "growth")).toBe(0);
    expect(rentFieldsFromRow({ e: 0, g: 0 }, acs.fields)).toEqual({ medianGrossRentGrowth: 0 });
  });

  it("accepts a later Mississippi row without a state allow-list", () => {
    const lookup = buildTractRentLookup({
      "hud-safmr-2br-tracts.json": {
        tracts: {
          "28001000100": { e: 880, j: 2, c: 28001 },
        },
      },
    });
    expect(lookup.get("28001000100")).toEqual({ safmr2Br: 880 });
    const feature = { properties: { tractGeoid: "28001000100" } as { tractGeoid: string; safmr2Br?: number; j?: number } };
    stampGeoidMetrics([feature], lookup);
    expect(feature.properties).toEqual({ tractGeoid: "28001000100", safmr2Br: 880 });
    expect(feature.properties).not.toHaveProperty("j");
  });

  it("drops non-numeric values inside the generic stamp", () => {
    const feature = { properties: { tractGeoid: "1" } as { tractGeoid: string; safmr2Br?: number; note?: string } };
    stampGeoidMetrics([feature], new Map([["1", { safmr2Br: 900, note: "zip" }]]));
    expect(feature.properties).toEqual({ tractGeoid: "1", safmr2Br: 900 });
  });

  it("stamps the published series onto eligible tracts and the far-zoom overlay", async () => {
    const [lookup, packs, overview, zones] = await Promise.all([
      loadTractRentLookup(),
      loadEligiblePackTracts(),
      loadEligibleOverview(),
      loadOpportunityZones(),
    ]);
    const sample = lookup.get(SAMPLE_GEOID);
    expect(sample).toMatchObject({
      medianGrossRent: 1049,
      medianGrossRentMoe: 99,
      medianGrossRentGrowth: 40.1,
      safmr2Br: 1040,
      zoriMf5Plus: 1335,
      zoriMf5PlusGrowth: 3.8,
      zoriAll: 1761,
      zoriAllGrowth: 5.8,
      apartmentListCountyRent: 1267,
      apartmentListCountyRentGrowth: 2.4,
    });
    expect(Object.keys(sample ?? {}).sort()).toEqual(
      [
        "apartmentListCountyRent",
        "apartmentListCountyRentGrowth",
        "medianGrossRent",
        "medianGrossRentGrowth",
        "medianGrossRentMoe",
        "safmr2Br",
        "zoriAll",
        "zoriAllGrowth",
        "zoriMf5Plus",
        "zoriMf5PlusGrowth",
      ].sort(),
    );

    const stamped = packs.features.filter((feature) => typeof feature.properties.safmr2Br === "number");
    expect(stamped.length).toBeGreaterThan(10);
    expect(
      stamped.every((feature) => lookup.get(feature.properties.tractGeoid)?.safmr2Br === feature.properties.safmr2Br),
    ).toBe(true);
    for (const feature of packs.features) {
      const props = feature.properties as Record<string, unknown>;
      expect(props).not.toHaveProperty("j");
      expect(props).not.toHaveProperty("z");
      expect(props).not.toHaveProperty("c");
      expect(props).not.toHaveProperty("e2019");
    }

    const known = overview.features.find((feature) => lookup.has(String(feature.properties?.tractGeoid)));
    const geoid = String(known?.properties?.tractGeoid);
    expect(known?.properties?.safmr2Br).toBe(lookup.get(geoid)?.safmr2Br);
    const missingRent = overview.features.find((feature) => !lookup.has(String(feature.properties?.tractGeoid)));
    if (missingRent) {
      expect(missingRent.properties?.medianGrossRent).toBeUndefined();
      expect(missingRent.properties?.safmr2Br).toBeUndefined();
    }

    const baked = JSON.parse(readFileSync(path.join(process.cwd(), "data/fixtures/oz2-eligible-overview.geojson"), "utf8")) as {
      features: Array<{ properties: Record<string, unknown> }>;
    };
    const bakedKnown = baked.features.find((feature) => feature.properties.tractGeoid === geoid);
    expect(bakedKnown?.properties.safmr2Br).toBe(lookup.get(geoid)?.safmr2Br);
    expect(bakedKnown?.properties).not.toHaveProperty("j");
    expect(bakedKnown?.properties).not.toHaveProperty("z");
    expect(bakedKnown?.properties).not.toHaveProperty("c");
    const bakedMs = baked.features.find((feature) => String(feature.properties.tractGeoid).startsWith("28"));
    expect(bakedMs?.properties.safmr2Br).toBeUndefined();
    const zone = zones.features.find((feature) => lookup.has(feature.properties.tractGeoid));
    expect(zone?.properties.safmr2Br).toBe(lookup.get(zone?.properties.tractGeoid ?? "")?.safmr2Br);
  });
});

describe("tract rent filter", () => {
  it("stays off at zero and hides missing values once a minimum is set", () => {
    expect(tractMinimumLayerFilter("safmr2Br", 0)).toBeNull();
    expect(tractMinimumLayerFilter("safmr2Br", Number.NaN)).toBeNull();
    expect(tractRentLayerFilter(DEFAULT_RENT_MINIMUMS)).toBeNull();
    expect(tractRentFilterActive(DEFAULT_RENT_MINIMUMS)).toBe(false);
    const knownOnly = tractMinimumLayerFilter("medianGrossRent", 1500);
    expect(knownOnly).toEqual([
      "all",
      ["has", "medianGrossRent"],
      [">=", ["to-number", ["get", "medianGrossRent"]], 1500],
    ]);
    expect(JSON.stringify(knownOnly)).not.toContain('"any"');
    const combined = tractRentLayerFilter({
      ...DEFAULT_RENT_MINIMUMS,
      minSafmr2Br: 1200,
      minZoriMf5PlusGrowth: 1,
    });
    expect(JSON.stringify(combined)).toContain("safmr2Br");
    expect(JSON.stringify(combined)).toContain("zoriMf5PlusGrowth");
    expect(JSON.stringify(combined)).not.toContain('"any"');
    expect(tractRentPasses(undefined, 0)).toBe(true);
    expect(tractRentPasses(undefined, 1000)).toBe(false);
    expect(tractRentPasses(1000, 1000)).toBe(true);
    expect(tractRentPasses(999, 1000)).toBe(false);
  });

  it("filters tract rows the same way the layer filter does", () => {
    const rows = [{ geoid: "low" }, { geoid: "high" }, { geoid: "missing" }, { geoid: "flat" }];
    const rent = {
      low: { safmr2Br: 900, zoriMf5PlusGrowth: 2 },
      high: { safmr2Br: 1600, zoriMf5PlusGrowth: 2 },
      flat: { safmr2Br: 1600, zoriMf5PlusGrowth: 0 },
    };
    expect(filterTractRowsByRent(rows, rent, DEFAULT_RENT_MINIMUMS)).toHaveLength(4);
    expect(
      filterTractRowsByRent(rows, rent, { ...DEFAULT_RENT_MINIMUMS, minSafmr2Br: 1000 }).map((row) => row.geoid),
    ).toEqual(["high", "flat"]);
    expect(
      filterTractRowsByRent(rows, rent, { ...DEFAULT_RENT_MINIMUMS, minZoriMf5PlusGrowth: 1 }).map((row) => row.geoid),
    ).toEqual(["low", "high"]);
  });
});

describe("tract rent display", () => {
  it("labels each source and uses an em dash when the value is missing", () => {
    expect(formatTractRentLines(null)).toEqual([
      "ACS median gross rent: —",
      "HUD SAFMR 2BR: —",
      "Zillow MF 5+ (metro): —",
      "Zillow all homes (ZIP): —",
      "Apartment List: —",
    ]);
    expect(formatTractRentLines({ medianGrossRent: ACS_MEDIAN_GROSS_RENT_TOP_CODE, medianGrossRentGrowth: 12 })).toContain(
      "ACS median gross rent: $3,500+ · +12.0%",
    );
    expect(formatTractRentLines({ medianGrossRent: 1049, medianGrossRentMoe: 99, medianGrossRentGrowth: 40.1 })).toContain(
      "ACS median gross rent: $1,049 ± $99 · +40.1%",
    );
    expect(formatTractRentLines({ zoriMf5Plus: 1335 })).toContain("Zillow MF 5+ (metro): $1,335 · —");
    expect(formatTractRentLines({ zoriAllGrowth: -1.2, zoriAll: 1761 })).toContain("Zillow all homes (ZIP): $1,761 · -1.2%");
  });

  it("does not claim income is Orange County only", () => {
    const message = tractMetricEmptyMessage("eligible", true, false);
    expect(message).toContain("ACS 5-year 2020–2024 B19013");
    expect(message).not.toContain("Orange County");
    expect(tractMetricEmptyMessage("nominated", false, true)).toContain("no value for that source");
    const appShell = readFileSync(path.join(process.cwd(), "src/components/AppShell.tsx"), "utf8");
    expect(appShell).not.toContain("Only Orange County tracts have a joined ACS median income");
    expect(appShell).toContain("tractMetricEmptyMessage");
  });

  it("starts every rent slider at zero", () => {
    expect(RENT_SLIDERS.map((slider) => slider.label)).toEqual([
      "ACS median gross rent",
      "ACS median gross rent growth",
      "HUD SAFMR 2BR",
      "Zillow MF 5+ (metro)",
      "Zillow MF 5+ growth",
      "Zillow all homes (ZIP)",
      "Zillow all homes growth",
      "Apartment List",
      "Apartment List growth",
    ]);
    expect(RENT_SLIDERS.every((slider) => slider.min === 0 && DEFAULT_RENT_MINIMUMS[slider.key] === 0)).toBe(true);
    expect(RENT_SLIDERS.every((slider) => slider.note.length > 20)).toBe(true);
  });
});
