import { describe, expect, it } from "vitest";
import { loadEligiblePackTracts, loadOrangeTractIncomeMap } from "../lib/data/loadFixtures";
import {
  filterTractRowsByIncome,
  tractIncomeFilterActive,
  tractIncomeLayerFilter,
  tractIncomePasses,
} from "../lib/tractIncome";

describe("tract income", () => {
  it("treats missing AMI as unknown and does not invent a zero", () => {
    expect(tractIncomePasses(null, 80000, true)).toBe(true);
    expect(tractIncomePasses(undefined, 80000, false)).toBe(false);
    expect(tractIncomePasses(50000, 80000, true)).toBe(false);
    expect(tractIncomePasses(90000, 80000, true)).toBe(true);
    expect(tractIncomeFilterActive("blockGroup", 80000, false)).toBe(false);
    expect(tractIncomeFilterActive("tract", 0, true)).toBe(false);
    expect(tractIncomeLayerFilter("tract", 0, true)).toBeNull();
    expect(tractIncomeLayerFilter("blockGroup", 80000, false)).toBeNull();
    const knownOnly = tractIncomeLayerFilter("tract", 80000, false);
    expect(JSON.stringify(knownOnly)).toContain("medianHouseholdIncome");
    expect(JSON.stringify(knownOnly)).not.toContain("literal");
  });

  it("drops tracts below the minimum and keeps tracts with no AMI while unknown income is included", () => {
    const rows = [{ geoid: "known-low" }, { geoid: "known-high" }, { geoid: "missing" }];
    const lookup = { "known-low": 40000, "known-high": 120000 };
    const filters = { incomeGeography: "tract" as const, minIncome: 80000, includeUnknownIncome: true };
    expect(filterTractRowsByIncome(rows, lookup, filters).map((row) => row.geoid)).toEqual(["known-high", "missing"]);
    expect(
      filterTractRowsByIncome(rows, lookup, { ...filters, includeUnknownIncome: false }).map((row) => row.geoid),
    ).toEqual(["known-high"]);
    expect(filterTractRowsByIncome(rows, lookup, { ...filters, incomeGeography: "blockGroup" })).toHaveLength(3);
    expect(filterTractRowsByIncome(rows, lookup, { ...filters, minIncome: 0 })).toHaveLength(3);
  });

  it("stamps ACS income onto eligible tracts in Florida parcel counties and leaves other states unstamped", async () => {
    const [income, packs] = await Promise.all([loadOrangeTractIncomeMap(), loadEligiblePackTracts()]);
    const stamped = packs.features.filter((feature) => typeof feature.properties.medianHouseholdIncome === "number");
    expect(stamped.length).toBeGreaterThan(10);
    const orange = stamped.filter((feature) => feature.properties.tractGeoid.startsWith("12095"));
    expect(orange.length).toBeGreaterThan(10);
    expect(
      stamped.every((feature) => income.get(feature.properties.tractGeoid) === feature.properties.medianHouseholdIncome),
    ).toBe(true);
    const outsideFlorida = packs.features.find((feature) => !feature.properties.tractGeoid.startsWith("12"));
    expect(outsideFlorida).toBeTruthy();
    expect(outsideFlorida?.properties.medianHouseholdIncome).toBeUndefined();
  });
});