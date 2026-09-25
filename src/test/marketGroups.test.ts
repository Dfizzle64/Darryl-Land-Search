import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { groupMarketsByState } from "../lib/marketGroups";
import { MARKETS, OTHER_MARKETS, PARCEL_MARKETS, type EligibleMarketsCatalog, type RuralMarketsCatalog, type SearchMarketId } from "../lib/types";

function load<T>(path: string): T {
  return JSON.parse(readFileSync(path, "utf8")) as T;
}

describe("markets grouped by state", () => {
  const groups = groupMarketsByState(
    load<RuralMarketsCatalog>("data/fixtures/oz2-rural-markets.json"),
    load<EligibleMarketsCatalog>("data/fixtures/oz2-urban-markets.json"),
    load<EligibleMarketsCatalog>("data/fixtures/oz2-other-msas.json"),
  );

  it("sorts states and the markets inside them", () => {
    const states = groups.map((group) => group.state);
    expect(states).toEqual([...states].sort((a, b) => a.localeCompare(b, "en", { sensitivity: "base" })));
    for (const group of groups) {
      expect(group.markets).toEqual(
        [...group.markets].sort((a, b) => a.localeCompare(b, "en", { sensitivity: "base" })),
      );
    }
  });

  it("keeps every existing market reachable, including South Florida and the other shelves", () => {
    const reachable = new Set<SearchMarketId>();
    for (const group of groups) {
      for (const market of group.markets) reachable.add(market);
    }
    const expected = [...MARKETS, ...OTHER_MARKETS, ...PARCEL_MARKETS];
    expect([...reachable].sort()).toEqual([...expected].sort());
    expect(expected).toHaveLength(reachable.size);

    const florida = groups.find((group) => group.state === "Florida");
    expect(florida?.markets).toContain("South Florida");
    expect(florida?.markets).toContain("Orlando");
    expect(florida?.markets).toContain("Heartland");
    expect(florida?.markets).toContain("SWFL");

    const alabama = groups.find((group) => group.state === "Alabama");
    expect(alabama?.markets).toEqual(
      expect.arrayContaining(["Birmingham", "Huntsville", "Mobile", "Montgomery", "Tuscaloosa"]),
    );

    expect(groups.find((group) => group.state === "North Carolina")?.markets).toContain("Asheville");
    expect(groups.find((group) => group.state === "North Carolina")?.markets).toContain("Charlotte");
    expect(groups.find((group) => group.state === "South Carolina")?.markets).toContain("Charlotte");
    expect(groups.find((group) => group.state === "South Carolina")?.markets).toContain("Hilton Head");
    expect(groups.find((group) => group.state === "Mississippi")?.markets).toContain("Jackson MS");
    expect(groups.find((group) => group.state === "Tennessee")?.markets).toContain("Jackson");
    expect(groups.find((group) => group.state === "Tennessee")?.markets).not.toContain("Jackson MS");
  });
});
