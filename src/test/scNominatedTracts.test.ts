import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { displayStatusChip, filterEligibleRows, filterRuralRows, southCarolinaOverlayMode } from "../lib/markets";
import { describeOz2Eligibility } from "../lib/opportunityZone";
import {
  displayedOzTracts,
  displayTractNotes,
  isScGovernorNominatedGeoid,
  parseScNominatedCsv,
  scGovernorNominatedGeoids,
  scNominatedOverlayFilter,
  showOzTractInScMarkets,
  SC_NOMINATED_SOURCE_CSV,
} from "../lib/scNominatedTracts";
import { tractClickFromFeature } from "../lib/tractCounty";
import {
  ELIGIBLE_NOT_DESIGNATED_STATUS,
  RURAL_ELIGIBLE_STATUS_CHIP,
  SC_GOVERNOR_NOMINATED_STATUS,
  type EligibleMarketsCatalog,
  type RuralMarketsCatalog,
} from "../lib/types";

const NOMINATED_HITS = [
  "45015020712",
  "45015020506",
  "45015020201",
  "45035010200",
  "45075010200",
  "45091061601",
  "45091061602",
];

const STILL_ELIGIBLE = [
  "45019002503",
  "45015020504",
  "45015020303",
  "45035010301",
  "45035010302",
  "45057011001",
  "12095016605",
];

function loadRural(): RuralMarketsCatalog {
  return JSON.parse(readFileSync("data/fixtures/oz2-rural-markets.json", "utf8")) as RuralMarketsCatalog;
}

function loadUrban(): EligibleMarketsCatalog {
  return JSON.parse(readFileSync("data/fixtures/oz2-urban-markets.json", "utf8")) as EligibleMarketsCatalog;
}

function loadOther(): EligibleMarketsCatalog {
  return JSON.parse(readFileSync("data/fixtures/oz2-other-msas.json", "utf8")) as EligibleMarketsCatalog;
}

describe("official South Carolina nominated GEOIDs", () => {
  const csvText = readFileSync(SC_NOMINATED_SOURCE_CSV, "utf8");
  const parsed = parseScNominatedCsv(csvText);
  const official = scGovernorNominatedGeoids();

  it("loads the committed CSV as 112 tracts, 84 rural and 28 non-rural", () => {
    expect(parsed.geoids).toHaveLength(112);
    expect(new Set(parsed.geoids).size).toBe(112);
    expect(parsed.ruralCount).toBe(84);
    expect(parsed.nonRuralCount).toBe(28);
    expect(official.size).toBe(112);
    expect([...official].sort()).toEqual([...parsed.geoids].sort());
  });

  it("soft-upgrades only the official GEOIDs and leaves the eligible-only examples eligible", () => {
    for (const geoid of NOMINATED_HITS) {
      expect(isScGovernorNominatedGeoid(geoid)).toBe(true);
      expect(displayStatusChip({ market: "Charleston", rural: "Y", geoid })).toBe(SC_GOVERNOR_NOMINATED_STATUS);
    }
    for (const geoid of STILL_ELIGIBLE) {
      expect(isScGovernorNominatedGeoid(geoid)).toBe(false);
    }
    expect(displayStatusChip({ market: "Charleston", rural: "Y", geoid: "45019002503" })).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
    expect(displayStatusChip({ market: "Charleston", rural: "Y", geoid: "45035010301" })).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
    expect(displayStatusChip({ market: "Charlotte", rural: "Y", geoid: "45057011001" })).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
    expect(displayStatusChip({ market: "Orlando", rural: "Y", geoid: "12095016605" })).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
    expect(displayStatusChip({ market: "Charleston", rural: "N", geoid: "45019000700" })).toBe(SC_GOVERNOR_NOMINATED_STATUS);
    expect(displayStatusChip({ market: "Charleston", rural: "N", geoid: "45019002503" })).toBe(ELIGIBLE_NOT_DESIGNATED_STATUS);
    expect(SC_GOVERNOR_NOMINATED_STATUS).not.toMatch(/^designated/i);
    expect(SC_GOVERNOR_NOMINATED_STATUS).not.toMatch(/QOZ/);
  });

  it("labels catalog rows on screen from GEOID membership, not from county", () => {
    const rows = [...loadRural().rows, ...loadUrban().rows, ...loadOther().rows];
    const nominated = rows.filter((row) => official.has(row.geoid));
    const untouched = rows.filter((row) => !official.has(row.geoid));
    expect(nominated.length).toBeGreaterThan(0);
    expect(untouched.length).toBeGreaterThan(nominated.length);
    expect(nominated.every((row) => displayStatusChip(row) === SC_GOVERNOR_NOMINATED_STATUS)).toBe(true);
    expect(untouched.every((row) => displayStatusChip(row) !== SC_GOVERNOR_NOMINATED_STATUS)).toBe(true);
    expect(rows.every((row) => !/^designated/i.test(displayStatusChip(row)))).toBe(true);

    const byMarket = (market: string) => nominated.filter((row) => row.market === market).map((row) => row.geoid);
    for (const geoid of NOMINATED_HITS) {
      expect(rows.some((row) => row.geoid === geoid)).toBe(true);
    }
    expect(byMarket("Charleston")).toEqual(expect.arrayContaining(["45015020712", "45015020506", "45015020201", "45035010200"]));
    expect(byMarket("Charlotte")).toEqual(expect.arrayContaining(["45091061601", "45091061602"]));
    expect(byMarket("Columbia")).toContain("45075010200");
    expect(byMarket("Greenville").length).toBeGreaterThan(0);
    expect(byMarket("Savannah").length).toBeGreaterThan(0);
    expect(byMarket("Orlando")).toHaveLength(0);
    expect(byMarket("Atlanta")).toHaveLength(0);
  });

  it("keeps the map popup and parcel copy off designation", () => {
    const nominated = tractClickFromFeature({
      layerId: "rural-fill",
      properties: { tractGeoid: "45015020712", county: "Berkeley", state: "South Carolina", rural: true },
    });
    expect(nominated?.status).toBe(SC_GOVERNOR_NOMINATED_STATUS);
    expect(nominated?.statusDetail).toMatch(/not a designated QOZ/i);
    expect(nominated?.statusDetail).toMatch(/not a tax benefit/i);
    expect(nominated?.kind).toBe("eligible");

    const eligible = tractClickFromFeature({
      layerId: "rural-fill",
      properties: { tractGeoid: "45035010301", county: "Dorchester", state: "South Carolina", rural: true },
    });
    expect(eligible?.status).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
    expect(eligible?.statusDetail).toBeNull();

    const overlay = tractClickFromFeature({
      layerId: "oz-fill",
      properties: { tractGeoid: "45015020712", county: "Berkeley", state: "South Carolina", rural: true },
    });
    expect(overlay?.status).toMatch(/current designated QOZ/i);
    expect(overlay?.status).toMatch(/not a 2027 designation/i);
    expect(overlay?.statusDetail).toBeNull();

    const parcel = describeOz2Eligibility({
      eligible: true,
      rural: true,
      tractGeoid: "45091061601",
      tractName: "Census Tract 616.01",
      designation: "eligible-for-nomination",
      source: "rev-proc-2026-14",
    });
    expect(parcel.statusChip).toBe(SC_GOVERNOR_NOMINATED_STATUS);
    expect(parcel.detail).toMatch(/awaiting Treasury/i);
    expect(parcel.detail).toMatch(/not a designated QOZ/i);
    expect(parcel.detail).not.toMatch(/has not been nominated/i);
    expect(parcel.detail).not.toMatch(/certified as a 2027 qoz/i);

    const missed = describeOz2Eligibility({
      eligible: true,
      rural: true,
      tractGeoid: "45015020504",
      tractName: null,
      designation: "eligible-for-nomination",
      source: "rev-proc-2026-14",
    });
    expect(missed.shown).toBe(false);
    expect(missed.statusChip).toBeNull();
    expect(missed.label).toMatch(/nominated list/);
    expect(missed.label.toLowerCase().startsWith("not on south carolina")).toBe(true);
    expect(missed.detail).toMatch(/does not show it/i);
    expect(missed.detail).not.toMatch(/Eligible \(rural\)/);
    expect(missed.eligible).toBe(true);

    const florida = describeOz2Eligibility({
      eligible: true,
      rural: true,
      tractGeoid: "12095016605",
      tractName: null,
      designation: "eligible-for-nomination",
      source: "rev-proc-2026-14",
    });
    expect(florida.shown).toBe(true);
    expect(florida.statusChip).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
  });

  it("replaces the unpublished-list note without inventing a designation", () => {
    const stale =
      "Rev. Proc. 2026-14 appendix Rural (entirely rural); Eligible — not designated (SC Governor-filed Sep 10, 2026; nominated GEOID list not public)";
    expect(displayTractNotes(stale, "45015020712")).toMatch(/Governor-nominated \/ awaiting Treasury/);
    expect(displayTractNotes(stale, "45015020712")).not.toMatch(/list not public/i);
    expect(displayTractNotes(stale, "45015020504")).toMatch(/not on South Carolina’s official nominated list/);
    expect(displayTractNotes(stale, "45015020504")).not.toMatch(/^designated/i);
    expect(displayTractNotes("Rev. Proc. 2026-14 appendix Rural (entirely rural)", "45015020712")).not.toMatch(/Governor-nominated/);
  });

  it("keeps nominated South Carolina tracts and drops eligible-only ones, including by FIPS", () => {
    for (const geoid of NOMINATED_HITS) {
      expect(showOzTractInScMarkets({ state: "South Carolina", geoid })).toBe(true);
      expect(showOzTractInScMarkets({ geoid })).toBe(true);
    }
    for (const geoid of STILL_ELIGIBLE.filter((id) => id.startsWith("45"))) {
      expect(showOzTractInScMarkets({ state: "South Carolina", geoid })).toBe(false);
      expect(showOzTractInScMarkets({ state: "Georgia", geoid })).toBe(false);
      expect(showOzTractInScMarkets({ geoid })).toBe(false);
    }
    expect(showOzTractInScMarkets({ state: "Florida", geoid: "12095016605" })).toBe(true);
    expect(showOzTractInScMarkets({ state: "North Carolina", geoid: "37119000100" })).toBe(true);
    expect(showOzTractInScMarkets({ state: "Georgia", geoid: "13051000100" })).toBe(true);
    expect(showOzTractInScMarkets({ state: "South Carolina", geoid: "13051000100" })).toBe(false);
  });

  it("limits South Carolina catalog rows on the map and list to the nominated set", () => {
    const rural = loadRural();
    const urban = loadUrban();
    const other = loadOther();
    const official = scGovernorNominatedGeoids();

    const charleston = displayedOzTracts([
      ...filterRuralRows(rural.rows, "Charleston", null, null),
      ...filterEligibleRows(urban.rows, "Charleston", null, null),
    ]);
    expect(charleston.length).toBeGreaterThan(0);
    expect(charleston.length).toBeLessThan(
      filterRuralRows(rural.rows, "Charleston", null, null).length + filterEligibleRows(urban.rows, "Charleston", null, null).length,
    );
    expect(charleston.every((row) => row.state === "South Carolina" && official.has(row.geoid))).toBe(true);
    expect(charleston.some((row) => row.geoid === "45019002503" || row.geoid === "45035010301")).toBe(false);
    expect(charleston.some((row) => row.geoid === "45015020712")).toBe(true);

    const charlotteNc = displayedOzTracts(filterRuralRows(rural.rows, "Charlotte", null, "North Carolina"));
    expect(charlotteNc).toEqual(filterRuralRows(rural.rows, "Charlotte", null, "North Carolina"));
    const charlotteSc = displayedOzTracts(filterRuralRows(rural.rows, "Charlotte", null, "South Carolina"));
    expect(charlotteSc.length).toBeGreaterThan(0);
    expect(charlotteSc.every((row) => official.has(row.geoid))).toBe(true);
    expect(charlotteSc.some((row) => row.geoid === "45057011001")).toBe(false);
    expect(charlotteSc.some((row) => row.geoid === "45091061601")).toBe(true);

    const orlando = displayedOzTracts(filterRuralRows(rural.rows, "Orlando", null, null));
    expect(orlando).toHaveLength(filterRuralRows(rural.rows, "Orlando", null, null).length);

    const savannahGa = displayedOzTracts(filterEligibleRows(other.rows, "Savannah", null, "Georgia"));
    expect(savannahGa).toEqual(filterEligibleRows(other.rows, "Savannah", null, "Georgia"));
    const savannahSc = displayedOzTracts(filterEligibleRows(other.rows, "Savannah", null, "South Carolina"));
    expect(savannahSc.length).toBeGreaterThan(0);
    expect(savannahSc.every((row) => official.has(row.geoid))).toBe(true);

    expect(southCarolinaOverlayMode("Charleston", null)).toBe("nominated-only");
    expect(southCarolinaOverlayMode("Charlotte", "South Carolina")).toBe("nominated-only");
    expect(southCarolinaOverlayMode("Charlotte", null)).toBe("mixed");
    expect(southCarolinaOverlayMode("Charlotte", "North Carolina")).toBe("eligible");
    expect(southCarolinaOverlayMode("Orlando", null)).toBe("eligible");
    expect(southCarolinaOverlayMode("Savannah", "Georgia")).toBe("eligible");
    expect(southCarolinaOverlayMode("Savannah", null)).toBe("mixed");
  });

  it("encodes the map filter as nominated membership or not a South Carolina tract", () => {
    const filter = scNominatedOverlayFilter();
    expect(filter[0]).toBe("any");
    const membership = filter[1] as unknown[];
    expect(membership[0]).toBe("in");
    const literal = membership[2] as unknown[];
    expect(literal[0]).toBe("literal");
    expect(literal[1]).toEqual([...scGovernorNominatedGeoids()].sort());
    const guard = JSON.stringify(filter[2]);
    expect(guard).toContain("South Carolina");
    expect(guard).toContain("45");
    expect(guard).not.toContain("Florida");
    expect(guard).not.toContain("North Carolina");
    expect(guard).not.toContain("Georgia");
  });
});
