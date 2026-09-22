import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { filterRuralRows, viewBounds } from "../lib/markets";
import {
  annotateRuralRows,
  countMfPriority,
  filterByMfPriority,
  geoidFilterForView,
  geoidsForHighlight,
  sortTractsForDisplay,
  tractPlaceLabel,
} from "../lib/scMfPriority";
import {
  RURAL_ELIGIBLE_STATUS_CHIP,
  SC_GOVERNOR_FILED_STATUS,
  type RuralMarketsCatalog,
  type ScMfPriorityCatalog,
} from "../lib/types";

const TIER_A = [
  "45015020712",
  "45015020506",
  "45015020504",
  "45035010301",
  "45019002503",
  "45091061602",
  "45091061601",
  "45057011001",
  "45015020303",
  "45035010302",
];

const TIER_B = [
  "45015020201",
  "45015020101",
  "45015020202",
  "45057010500",
  "45057010300",
  "45023020700",
  "45023020800",
  "45019002402",
  "45035010200",
  "45029970601",
  "45075010200",
  "45023020900",
];

function loadPriority(): ScMfPriorityCatalog {
  return JSON.parse(readFileSync("data/fixtures/sc-oz2-mf-priority.json", "utf8")) as ScMfPriorityCatalog;
}

function loadRural(): RuralMarketsCatalog {
  return JSON.parse(readFileSync("data/fixtures/oz2-rural-markets.json", "utf8")) as RuralMarketsCatalog;
}

function parseCsv(text: string): Record<string, string>[] {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(",");
  return lines.slice(1).map((line) => {
    const cells = line.split(",");
    const row: Record<string, string> = {};
    headers.forEach((header, index) => {
      row[header] = cells[index] ?? "";
    });
    return row;
  });
}

describe("South Carolina multifamily priority shortlist", () => {
  const priority = loadPriority();
  const rural = loadRural();
  const csv = parseCsv(readFileSync("data/sc-oz2-mf-priority-shortlist.csv", "utf8"));

  it("seeds 22 rural-eligible tracts, 10 Tier A and 12 Tier B, without changing the status chip", () => {
    expect(priority.rowCount).toBe(22);
    expect(priority.rows).toHaveLength(22);
    expect(priority.tierACount).toBe(10);
    expect(priority.tierBCount).toBe(12);
    expect(priority.statusChip).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
    expect(priority.governorFiledStatus).toBe(SC_GOVERNOR_FILED_STATUS);
    expect(priority.rows.every((row) => row.status === RURAL_ELIGIBLE_STATUS_CHIP)).toBe(true);
    expect(priority.rows.every((row) => row.rural === "Y" && row.state === "South Carolina")).toBe(true);
    expect(priority.sourceCsv).toBe("data/sc-oz2-mf-priority-shortlist.csv");
    expect(JSON.stringify(priority)).not.toMatch(/certified 2027/i);
    expect(priority.disclaimer.toLowerCase()).toContain("not a nominated");
    expect(priority.disclaimer.toLowerCase()).toContain("not a designation");
  });

  it("matches the CSV places, tiers, and notes, including the top GEOIDs", () => {
    expect(csv).toHaveLength(22);
    expect(priority.rows.map((row) => row.geoid)).toEqual(csv.map((row) => row.geoid));
    expect(priority.rows.filter((row) => row.tier === "A").map((row) => row.geoid)).toEqual(TIER_A);
    expect(priority.rows.filter((row) => row.tier === "B").map((row) => row.geoid)).toEqual(TIER_B);
    for (const [index, row] of priority.rows.entries()) {
      const source = csv[index];
      expect(row.rank).toBe(index + 1);
      expect(row.place).toBe(source.place);
      expect(row.tier).toBe(source.tier);
      expect(row.county).toBe(source.county);
      expect(row.market).toBe(source.market);
      expect(row.mfRationale).toBe(source.mf_rationale);
      expect(row.acreageRealism).toBe(source.acreage_realism);
      expect(row.notes).toBe(source.notes);
      expect(row.sourceStatus).toContain("not designated");
      expect(row.sourceStatus).toContain("not confirmed nominated");
      expect(source.status).toBe(row.sourceStatus);
    }
  });

  it("joins each GEOID onto the existing seven-market rural row and leaves other markets alone", () => {
    const annotated = annotateRuralRows(rural.rows, priority);
    expect(annotated).toHaveLength(446);
    expect(annotated.filter((row) => row.mfPriority).length).toBe(22);
    expect(rural.rows.every((row) => row.mfPriority == null)).toBe(true);
    expect(rural.rowCount).toBe(446);

    for (const item of priority.rows) {
      const matches = annotated.filter((row) => row.geoid === item.geoid);
      expect(matches).toHaveLength(1);
      expect(matches[0].market).toBe(item.market);
      expect(matches[0].county).toBe(item.county);
      expect(matches[0].state).toBe("South Carolina");
      expect(matches[0].status).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
      expect(matches[0].mfPriority?.tier).toBe(item.tier);
      expect(matches[0].mfPriority?.place).toBe(item.place);
      expect(tractPlaceLabel(matches[0])).toBe(item.place);
    }

    const charleston = filterRuralRows(annotated, "Charleston", null, null);
    const charlotte = filterRuralRows(annotated, "Charlotte", null, null);
    expect(countMfPriority(charleston)).toEqual({ all: 49, priority: 14, A: 7, B: 7 });
    expect(countMfPriority(charlotte)).toEqual({ all: 60, priority: 8, A: 3, B: 5 });
    expect(countMfPriority(filterRuralRows(annotated, "Orlando", null, null)).priority).toBe(0);
    expect(filterRuralRows(annotated, "Orlando", "Orange", "Florida").map((row) => row.geoid)).toEqual(["12095016605"]);
    expect(filterRuralRows(annotated, "Charlotte", "Union", "North Carolina")).toHaveLength(1);
    expect(filterRuralRows(annotated, "Charlotte", "York", "South Carolina").every((row) => row.mfPriority?.tier === "A")).toBe(
      true,
    );
  });

  it("filters and highlights Tier A versus Tier B without dropping the rural chip", () => {
    const charleston = sortTractsForDisplay(
      filterByMfPriority(annotateRuralRows(filterRuralRows(rural.rows, "Charleston", null, null), priority), "all"),
    );
    expect(charleston[0].geoid).toBe("45015020712");
    expect(charleston[0].mfPriority?.tier).toBe("A");
    expect(filterByMfPriority(charleston, "A")).toHaveLength(7);
    expect(filterByMfPriority(charleston, "B")).toHaveLength(7);
    expect(filterByMfPriority(charleston, "priority")).toHaveLength(14);
    expect(geoidFilterForView(charleston, "all")).toBeNull();
    expect(geoidFilterForView(charleston, "A")).toHaveLength(7);
    expect(geoidsForHighlight(charleston, "B", "A")).toEqual([]);
    expect(geoidsForHighlight(charleston, "priority", "A")).toContain("45015020712");
    expect(geoidsForHighlight(charleston, "all", "B")).toContain("45015020201");
    expect(geoidsForHighlight(charleston, "all", "B")).not.toContain("45023020700");
    expect(filterByMfPriority(charleston, "priority").every((row) => row.status === RURAL_ELIGIBLE_STATUS_CHIP)).toBe(true);

    const chester = filterByMfPriority(
      annotateRuralRows(filterRuralRows(rural.rows, "Charlotte", "Chester", "South Carolina"), priority),
      "priority",
    );
    expect(chester.map((row) => row.geoid).sort()).toEqual(["45023020700", "45023020800", "45023020900"]);
    expect(chester.every((row) => row.mfPriority?.tier === "B")).toBe(true);
  });

  it("fits the camera to a priority subset and keeps the Orange County pilot bounds", () => {
    const annotated = annotateRuralRows(rural.rows, priority);
    const summary = rural.markets.find((item) => item.market === "Charleston");
    expect(summary).toBeTruthy();
    const tierA = filterByMfPriority(filterRuralRows(annotated, "Charleston", null, null), "A");
    const fitted = viewBounds(summary!, tierA, null, null, { fitRows: true });
    const full = viewBounds(summary!, annotated, null, null);
    expect(full).toEqual(summary!.bounds);
    const area = (bounds: [[number, number], [number, number]]) =>
      (bounds[1][0] - bounds[0][0]) * (bounds[1][1] - bounds[0][1]);
    expect(area(fitted)).toBeLessThan(area(full));
    expect(fitted[1][0]).toBeLessThan(0);

    const orlando = rural.markets.find((item) => item.market === "Orlando");
    const pilot = viewBounds(orlando!, annotated, "Orange", "Florida", { fitRows: true });
    expect(pilot[0][0]).toBeLessThan(-81.6);
    expect(pilot[1][0]).toBeGreaterThan(-81.1);
  });
});
