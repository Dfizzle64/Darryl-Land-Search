import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { loadEligibleOverview, loadMsStatewideTracts, loadOrangeTractIncomeMap } from "../lib/data/loadFixtures";
import { mergeMsStatewideTracts, msStatewideTractRows } from "../lib/msStatewideTracts";
import { ELIGIBLE_NOT_DESIGNATED_STATUS, type EligiblePackTractCollection } from "../lib/types";

const OTHER_STATE_TRACT_COUNTS: Record<string, { rural: number; urban: number }> = {
  Alabama: { rural: 83, urban: 188 },
  Arkansas: { rural: 19, urban: 1 },
  Florida: { rural: 202, urban: 668 },
  Georgia: { rural: 103, urban: 381 },
  "North Carolina": { rural: 204, urban: 314 },
  "South Carolina": { rural: 47, urban: 28 },
  Tennessee: { rural: 85, urban: 253 },
};

function loadJson<T>(path: string): T {
  return JSON.parse(readFileSync(path, "utf8")) as T;
}

describe("Mississippi statewide eligible tracts", () => {
  const file = loadJson<EligiblePackTractCollection & { unmatchedGeoids?: string[] }>(
    "data/fixtures/oz2-ms-statewide.geojson",
  );

  it("matches the Rev. Proc. 2026-14 appendix counts", () => {
    expect(file.unmatchedGeoids ?? []).toEqual([]);
    expect(file.features).toHaveLength(404);
    const rural = file.features.filter((feature) => feature.properties.rural === true);
    const urban = file.features.filter((feature) => feature.properties.rural === false);
    expect(rural).toHaveLength(320);
    expect(urban).toHaveLength(84);
    const counties = new Set(file.features.map((feature) => feature.properties.county));
    const ruralCounties = new Set(rural.map((feature) => feature.properties.county));
    expect(counties.size).toBe(81);
    expect(ruralCounties.size).toBe(80);
    const washington = rural.filter((feature) => feature.properties.county === "Washington");
    expect(washington).toHaveLength(15);
    const desoto = file.features.filter((feature) => feature.properties.county === "DeSoto");
    expect(desoto.filter((feature) => feature.properties.rural)).toHaveLength(0);
    expect(desoto).toHaveLength(8);
  });

  it("keeps every tract on a 2020 Mississippi GEOID with an appendix rural flag", () => {
    const geoids = file.features.map((feature) => feature.properties.tractGeoid);
    expect(new Set(geoids).size).toBe(geoids.length);
    for (const feature of file.features) {
      const props = feature.properties;
      expect(props.tractGeoid).toMatch(/^28\d{9}$/);
      expect(props.state).toBe("Mississippi");
      expect(props.county.endsWith("County")).toBe(false);
      expect(props.rural === true || props.rural === false).toBe(true);
      expect(props.designation).toBe("eligible-for-nomination");
      expect(props.statusChip).toBe(ELIGIBLE_NOT_DESIGNATED_STATUS);
      expect(props.source).toBe("rev-proc-2026-14");
      expect(props.markets).toEqual([]);
      expect(feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon").toBe(true);
    }
    const rows = msStatewideTractRows(file);
    expect(rows).toHaveLength(404);
    expect(rows.every((row) => row.market === "Mississippi")).toBe(true);
  });

  it("does not replace tracts the market packs already draw", () => {
    const packs = loadJson<EligiblePackTractCollection>("data/fixtures/oz2-eligible-packs.geojson");
    const rural = loadJson<EligiblePackTractCollection>("data/fixtures/oz2-rural-markets.geojson");
    const orange = loadJson<EligiblePackTractCollection>("data/fixtures/oz2-eligible.geojson");
    expect(packs.features).toHaveLength(2466);
    const packMs = packs.features.filter((feature) => feature.properties.tractGeoid.startsWith("28"));
    expect(packMs).toHaveLength(25);
    const byGeoid = new Map(file.features.map((feature) => [feature.properties.tractGeoid, feature]));
    for (const feature of packMs) {
      const statewide = byGeoid.get(feature.properties.tractGeoid);
      expect(statewide?.properties.rural).toBe(feature.properties.rural);
      expect(statewide?.properties.county).toBe(feature.properties.county);
    }
    const merged = mergeMsStatewideTracts(packs, rural, orange, file);
    expect(merged.features).toHaveLength(2466 + 379);
    const mergedMs = merged.features.filter((feature) => feature.properties.tractGeoid.startsWith("28"));
    expect(new Set(mergedMs.map((feature) => feature.properties.tractGeoid)).size).toBe(404);
    const first = merged.features.find((feature) => feature.properties.tractGeoid === packMs[0].properties.tractGeoid);
    expect(first).toBe(packMs[0]);
  });

  it("joins ACS B19013 income and leaves tracts missing from that table unknown", async () => {
    const [income, tracts] = await Promise.all([loadOrangeTractIncomeMap(), loadMsStatewideTracts()]);
    let known = 0;
    let unknown = 0;
    for (const feature of tracts.features) {
      const table = income.get(feature.properties.tractGeoid);
      const stamped = feature.properties.medianHouseholdIncome;
      if (table == null) {
        expect(stamped).toBeUndefined();
        unknown += 1;
      } else {
        expect(stamped).toBe(table);
        expect(stamped).toBeGreaterThan(0);
        known += 1;
      }
    }
    expect(known).toBe(399);
    expect(unknown).toBe(5);
  });

  it("puts every eligible tract on the far-zoom overlay with ACS income", async () => {
    const [overview, income] = await Promise.all([loadEligibleOverview(), loadOrangeTractIncomeMap()]);
    const counts = new Map<string, { rural: number; urban: number }>();
    const geoids = new Set<string>();
    for (const feature of overview.features) {
      const props = feature.properties as {
        state?: string;
        rural?: boolean;
        tractGeoid?: string;
        medianHouseholdIncome?: number;
      };
      expect(props.tractGeoid).toMatch(/^\d{11}$/);
      expect(props.state).toBeTruthy();
      expect(props.rural === true || props.rural === false).toBe(true);
      geoids.add(props.tractGeoid!);
      const bucket = counts.get(props.state!) ?? { rural: 0, urban: 0 };
      if (props.rural) bucket.rural += 1;
      else bucket.urban += 1;
      counts.set(props.state!, bucket);
      const table = income.get(props.tractGeoid!);
      if (table == null) expect(props.medianHouseholdIncome).toBeUndefined();
      else expect(props.medianHouseholdIncome).toBe(table);
    }
    expect(geoids.size).toBe(overview.features.length);
    expect(counts.get("Mississippi")).toEqual({ rural: 320, urban: 84 });
    for (const [state, expected] of Object.entries(OTHER_STATE_TRACT_COUNTS)) {
      expect(counts.get(state)).toEqual(expected);
    }
    for (const geoid of ["28049003200", "28075000401", "28121020500", "28121020805", "28151002000"]) {
      const feature = overview.features.find((item) => (item.properties as { tractGeoid?: string }).tractGeoid === geoid);
      expect(feature).toBeTruthy();
      expect((feature?.properties as { medianHouseholdIncome?: number }).medianHouseholdIncome).toBeUndefined();
    }
  });
});
