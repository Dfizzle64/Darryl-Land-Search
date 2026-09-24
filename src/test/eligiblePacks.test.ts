import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  displayStatusChip,
  eligibleClassCut,
  filterEligibleRows,
  governorFiledInNotes,
  isOtherMarketId,
  isPrimaryMarket,
  rowMatchesTractClass,
  showsGovernorFiledSoftCopy,
  southCarolinaStatusHelp,
  viewIncludesSouthCarolina,
} from "../lib/markets";
import {
  ELIGIBLE_NOT_DESIGNATED_STATUS,
  MARKETS,
  OTHER_MARKETS,
  RURAL_ELIGIBLE_STATUS_CHIP,
  type EligibleMarketsCatalog,
  type EligiblePackTractCollection,
  type MarketId,
  type OtherMarketId,
} from "../lib/types";

const URBAN_ROWS: Record<MarketId, number> = {
  Atlanta: 342,
  Tampa: 251,
  Orlando: 216,
  Charleston: 30,
  Nashville: 82,
  Charlotte: 144,
  "Raleigh-Durham": 79,
};

const OTHER_ROWS: Record<Exclude<OtherMarketId, "Asheville">, { total: number; rural: number; urban: number }> = {
  "Vero Beach": { total: 62, rural: 25, urban: 37 },
  Melbourne: { total: 175, rural: 24, urban: 151 },
  Jacksonville: { total: 98, rural: 8, urban: 90 },
  Pensacola: { total: 49, rural: 22, urban: 27 },
  Birmingham: { total: 152, rural: 42, urban: 110 },
  Mobile: { total: 66, rural: 15, urban: 51 },
  Huntsville: { total: 58, rural: 31, urban: 27 },
  Savannah: { total: 64, rural: 31, urban: 33 },
  Columbia: { total: 105, rural: 62, urban: 43 },
  Greenville: { total: 105, rural: 70, urban: 35 },
  Chattanooga: { total: 47, rural: 21, urban: 26 },
  Knoxville: { total: 70, rural: 41, urban: 29 },
  Memphis: { total: 175, rural: 44, urban: 131 },
  "Winston-Salem": { total: 105, rural: 24, urban: 81 },
  Wilmington: { total: 55, rural: 31, urban: 24 },
};

function loadUrban(): EligibleMarketsCatalog {
  return JSON.parse(readFileSync("data/fixtures/oz2-urban-markets.json", "utf8")) as EligibleMarketsCatalog;
}

function loadOther(): EligibleMarketsCatalog {
  return JSON.parse(readFileSync("data/fixtures/oz2-other-msas.json", "utf8")) as EligibleMarketsCatalog;
}

describe("urban eligible pack for the seven markets", () => {
  const catalog = loadUrban();

  it("keeps 1144 rows, 1103 GEOIDs, and the eligible — not designated chip", () => {
    expect(catalog.pack).toBe("urban-7");
    expect(catalog.rowCount).toBe(1144);
    expect(catalog.rows).toHaveLength(1144);
    expect(catalog.uniqueGeoidCount).toBe(1103);
    expect(catalog.urbanRowCount).toBe(1144);
    expect(catalog.ruralRowCount).toBe(0);
    expect(catalog.statusChip).toBe(ELIGIBLE_NOT_DESIGNATED_STATUS);
    expect(catalog.rows.every((row) => row.rural === "N")).toBe(true);
    expect(catalog.rows.every((row) => row.status === ELIGIBLE_NOT_DESIGNATED_STATUS)).toBe(true);
    expect(JSON.stringify(catalog.rows)).not.toMatch(/certified 2027/i);
    expect(catalog.rows.every((row) => !/^designated/i.test(row.status))).toBe(true);
  });

  it("matches the urban market counts and keeps South Carolina governor-filed notes", () => {
    for (const market of MARKETS) {
      const rows = filterEligibleRows(catalog.rows, market, null, null);
      expect(rows).toHaveLength(URBAN_ROWS[market]);
      expect(catalog.markets.find((item) => item.market === market)?.urbanCount).toBe(URBAN_ROWS[market]);
    }
    const southCarolina = catalog.rows.filter((row) => row.state === "South Carolina");
    expect(southCarolina.length).toBeGreaterThan(0);
    expect(southCarolina.every((row) => governorFiledInNotes(row.notes))).toBe(true);
    expect(southCarolina.every((row) => row.status === ELIGIBLE_NOT_DESIGNATED_STATUS)).toBe(true);
    expect(southCarolina.every((row) => showsGovernorFiledSoftCopy(row))).toBe(true);
  });
});

describe("other MSA eligible pack", () => {
  const catalog = loadOther();

  it("keeps 1386 rows, 1341 GEOIDs, 491 rural and 895 urban", () => {
    expect(catalog.pack).toBe("other-msas");
    expect(catalog.rowCount).toBe(1386);
    expect(catalog.uniqueGeoidCount).toBe(1341);
    expect(catalog.ruralRowCount).toBe(491);
    expect(catalog.urbanRowCount).toBe(895);
    expect(new Set(catalog.rows.map((row) => row.geoid)).size).toBe(1341);
    expect(catalog.statusChip).toBe(ELIGIBLE_NOT_DESIGNATED_STATUS);
    expect(catalog.rows.every((row) => row.status === ELIGIBLE_NOT_DESIGNATED_STATUS)).toBe(true);
    expect(catalog.rows.every((row) => row.rural === "Y" || row.rural === "N")).toBe(true);
    expect(JSON.stringify(catalog.rows)).not.toMatch(/nominated geoid list is public/i);
  });

  it("matches each smaller market and does not treat them as primary", () => {
    expect(OTHER_MARKETS).toHaveLength(16);
    expect(OTHER_MARKETS[2]).toBe("Jacksonville");
    expect(OTHER_MARKETS[OTHER_MARKETS.length - 1]).toBe("Asheville");
    for (const market of OTHER_MARKETS) {
      const rows = filterEligibleRows(catalog.rows, market, null, null);
      if (market === "Asheville") {
        expect(rows).toHaveLength(0);
        continue;
      }
      const expected = OTHER_ROWS[market];
      expect(rows).toHaveLength(expected.total);
      expect(rows.filter((row) => row.rural === "Y")).toHaveLength(expected.rural);
      expect(rows.filter((row) => row.rural === "N")).toHaveLength(expected.urban);
      expect(isOtherMarketId(market)).toBe(true);
      expect(isPrimaryMarket(market)).toBe(false);
      expect(displayStatusChip(rows[0])).toBe(ELIGIBLE_NOT_DESIGNATED_STATUS);
    }
  });

  it("keeps governor-filed soft copy on South Carolina rows and nowhere else as a status", () => {
    const southCarolina = catalog.rows.filter((row) => row.state === "South Carolina");
    expect(southCarolina.length).toBeGreaterThan(100);
    expect(southCarolina.every((row) => governorFiledInNotes(row.notes))).toBe(true);
    expect(southCarolina.every((row) => row.status === ELIGIBLE_NOT_DESIGNATED_STATUS)).toBe(true);
    const memphis = filterEligibleRows(catalog.rows, "Memphis", null, null);
    expect(memphis.some((row) => row.state === "Arkansas")).toBe(true);
    expect(memphis.some((row) => row.state === "Mississippi")).toBe(true);
    expect(memphis.every((row) => !governorFiledInNotes(row.notes))).toBe(true);
  });

  it("lists Jacksonville as an other market on the OMB MSA core counties", () => {
    expect(isOtherMarketId("Jacksonville")).toBe(true);
    expect(isPrimaryMarket("Jacksonville")).toBe(false);
    const rows = filterEligibleRows(catalog.rows, "Jacksonville", null, null);
    expect(rows).toHaveLength(98);
    expect(rows.every((row) => row.state === "Florida")).toBe(true);
    expect(rows.every((row) => row.status === ELIGIBLE_NOT_DESIGNATED_STATUS)).toBe(true);
    expect(rows.every((row) => row.outerEdge === false)).toBe(true);
    expect(rows.every((row) => !/^designated/i.test(row.status))).toBe(true);
    expect(displayStatusChip(rows.find((row) => row.rural === "Y")!)).toBe(ELIGIBLE_NOT_DESIGNATED_STATUS);
    const fips: Record<string, string> = {
      Baker: "12003",
      Clay: "12019",
      Duval: "12031",
      Nassau: "12089",
      "St. Johns": "12109",
    };
    expect(new Set(rows.map((row) => row.county))).toEqual(new Set(Object.keys(fips)));
    for (const row of rows) {
      expect(row.geoid.startsWith(fips[row.county])).toBe(true);
    }
    const duval = filterEligibleRows(rows, "Jacksonville", "Duval", "Florida");
    expect(duval).toHaveLength(86);
    expect(duval.every((row) => row.rural === "N")).toBe(true);
    expect(rows.filter((row) => row.rural === "Y").map((row) => row.county).sort()).toEqual([
      "Baker",
      "Clay",
      "Clay",
      "Clay",
      "Clay",
      "Nassau",
      "St. Johns",
      "St. Johns",
    ]);
  });

  it("dual-lists Brevard tracts under Vero Beach and Melbourne", () => {
    const vero = new Set(filterEligibleRows(catalog.rows, "Vero Beach", "Brevard", "Florida").map((row) => row.geoid));
    const melbourne = new Set(filterEligibleRows(catalog.rows, "Melbourne", "Brevard", "Florida").map((row) => row.geoid));
    expect(vero.size).toBeGreaterThan(0);
    expect([...vero].every((geoid) => melbourne.has(geoid))).toBe(true);
  });
});

describe("eligible pack polygons", () => {
  it("joins every urban and other-MSA GEOID to a tract polygon that is not designated", () => {
    const urban = loadUrban();
    const other = loadOther();
    const collection = JSON.parse(
      readFileSync("data/fixtures/oz2-eligible-packs.geojson", "utf8"),
    ) as EligiblePackTractCollection;
    const geoids = new Set([...urban.rows.map((row) => row.geoid), ...other.rows.map((row) => row.geoid)]);
    expect(geoids.size).toBe(2285);
    expect(collection.features).toHaveLength(2285);
    expect(new Set(collection.features.map((feature) => feature.properties.tractGeoid))).toEqual(geoids);
    expect(
      collection.features.every(
        (feature) =>
          feature.properties.designation === "eligible-for-nomination" &&
          feature.properties.statusChip === ELIGIBLE_NOT_DESIGNATED_STATUS &&
          feature.properties.source === "rev-proc-2026-14" &&
          (feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon") &&
          !/^designated/i.test(feature.properties.statusChip),
      ),
    ).toBe(true);
    const shared = collection.features.find((feature) => feature.properties.markets.includes("Melbourne") && feature.properties.markets.includes("Vero Beach"));
    expect(shared?.properties.rural).toBe(true);
    const jacksonville = collection.features.filter((feature) => feature.properties.markets.includes("Jacksonville"));
    expect(jacksonville).toHaveLength(98);
    expect(jacksonville.every((feature) => feature.properties.markets.length === 1)).toBe(true);
    expect(jacksonville.every((feature) => feature.properties.packs.includes("other-msas"))).toBe(true);
    expect(jacksonville.filter((feature) => feature.properties.rural)).toHaveLength(8);
    expect(jacksonville.filter((feature) => !feature.properties.rural)).toHaveLength(90);
  });
});

describe("tract class and South Carolina help for the new markets", () => {
  it("filters rural versus urban without inventing a designated chip", () => {
    expect(rowMatchesTractClass("Y", "both")).toBe(true);
    expect(rowMatchesTractClass("N", "urban")).toBe(true);
    expect(rowMatchesTractClass("Y", "urban")).toBe(false);
    expect(eligibleClassCut("both", "either")).toBe("all");
    expect(eligibleClassCut("urban", "either")).toBe("urban");
    expect(eligibleClassCut("rural", "non-rural-eligible")).toBe("none");
    expect(displayStatusChip({ market: "Orlando", rural: "Y", status: ELIGIBLE_NOT_DESIGNATED_STATUS })).toBe(
      RURAL_ELIGIBLE_STATUS_CHIP,
    );
    expect(displayStatusChip({ market: "Orlando", rural: "N" })).toBe(ELIGIBLE_NOT_DESIGNATED_STATUS);
    expect(displayStatusChip({ market: "Birmingham", rural: "Y" })).toBe(ELIGIBLE_NOT_DESIGNATED_STATUS);
    expect(displayStatusChip({ market: "Birmingham", rural: "Y" })).not.toMatch(/^designated/i);
  });

  it("shows governor-filed help for Columbia, Greenville, and Savannah’s South Carolina fringe", () => {
    expect(viewIncludesSouthCarolina("Columbia", null)).toBe(true);
    expect(viewIncludesSouthCarolina("Greenville", null)).toBe(true);
    expect(viewIncludesSouthCarolina("Savannah", null)).toBe(true);
    expect(viewIncludesSouthCarolina("Savannah", "South Carolina")).toBe(true);
    expect(viewIncludesSouthCarolina("Savannah", "Georgia")).toBe(false);
    expect(viewIncludesSouthCarolina("Memphis", null)).toBe(false);
    expect(southCarolinaStatusHelp("Columbia", null)).toMatch(/not designated/i);
    expect(southCarolinaStatusHelp("Greenville", null)).toMatch(/not public/i);
    expect(southCarolinaStatusHelp("Savannah", null)).toMatch(/Beaufort and Jasper/);
    expect(southCarolinaStatusHelp("Savannah", "Georgia")).toBeNull();
    expect(southCarolinaStatusHelp("Birmingham", null)).toBeNull();
    for (const note of [
      southCarolinaStatusHelp("Columbia", null),
      southCarolinaStatusHelp("Savannah", "South Carolina"),
    ]) {
      expect(note).not.toMatch(/\b\d{11}\b/);
      expect(note).not.toMatch(/^designated/i);
    }
  });
});
