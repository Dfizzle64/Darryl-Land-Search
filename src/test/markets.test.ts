import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  countyKey,
  filterRuralRows,
  formatCountyLabel,
  otherMarketDisplayOrder,
  showOrangeCountyPilot,
  southCarolinaStatusHelp,
  viewBounds,
  viewIncludesSouthCarolina,
} from "../lib/markets";
import {
  MARKETS,
  OTHER_MARKETS,
  PARCEL_MARKETS,
  RURAL_ELIGIBLE_STATUS_CHIP,
  SC_GOVERNOR_FILED_STATUS,
  SHED_CAVEAT,
  type MarketId,
  type RuralMarketTractCollection,
  type RuralMarketsCatalog,
  type RuralMarketTractRow,
} from "../lib/types";

const EXPECTED_ROWS: Record<MarketId, number> = {
  Atlanta: 73,
  Tampa: 66,
  Orlando: 64,
  Charleston: 49,
  Nashville: 26,
  Charlotte: 60,
  "Raleigh-Durham": 108,
};

function loadCatalog(): RuralMarketsCatalog {
  return JSON.parse(readFileSync("data/fixtures/oz2-rural-markets.json", "utf8")) as RuralMarketsCatalog;
}

describe("other market display order", () => {
  it("sorts Other MSAs A to Z without reordering the source arrays", () => {
    const source = [...OTHER_MARKETS, ...PARCEL_MARKETS];
    expect(otherMarketDisplayOrder()).toEqual([
      "Asheville",
      "Athens",
      "Big Bend",
      "Birmingham",
      "Chattanooga",
      "Columbia",
      "Greenville",
      "Heartland",
      "Hilton Head",
      "Huntsville",
      "Jackson",
      "Jackson MS",
      "Jacksonville",
      "Knoxville",
      "Macon",
      "Melbourne",
      "Memphis",
      "Mobile",
      "Montgomery",
      "North-Central Florida",
      "Pensacola",
      "Savannah",
      "SWFL",
      "Tuscaloosa",
      "Valdosta",
      "Vero Beach",
      "Wilmington",
      "Winston-Salem",
    ]);
    expect(OTHER_MARKETS[0]).toBe("SWFL");
    expect(OTHER_MARKETS[1]).toBe("Heartland");
    expect(PARCEL_MARKETS).toEqual(["Asheville"]);
    expect(MARKETS).toEqual([
      "Atlanta",
      "Tampa",
      "Orlando",
      "Charleston",
      "Nashville",
      "Charlotte",
      "Raleigh-Durham",
    ]);
    expect(source).not.toEqual(otherMarketDisplayOrder());
  });
});

describe("seven-market rural OZ 2.0 pack", () => {
  const catalog = loadCatalog();

  it("keeps 446 rows, 424 unique GEOIDs, and the required status chip", () => {
    expect(catalog.rowCount).toBe(446);
    expect(catalog.rows).toHaveLength(446);
    expect(catalog.uniqueGeoidCount).toBe(424);
    expect(new Set(catalog.rows.map((row) => row.geoid)).size).toBe(424);
    expect(catalog.statusChip).toBe(RURAL_ELIGIBLE_STATUS_CHIP);
    expect(catalog.shedCaveat).toBe(SHED_CAVEAT);
    expect(catalog.rows.every((row) => row.status === RURAL_ELIGIBLE_STATUS_CHIP)).toBe(true);
    expect(catalog.rows.every((row) => row.rural === "Y")).toBe(true);
    expect(JSON.stringify(catalog.rows)).not.toMatch(/certified 2027/i);
  });

  it("matches the market row counts", () => {
    for (const market of MARKETS) {
      expect(filterRuralRows(catalog.rows, market, null, null)).toHaveLength(EXPECTED_ROWS[market]);
      expect(catalog.markets.find((item) => item.market === market)?.rowCount).toBe(EXPECTED_ROWS[market]);
    }
  });

  it("lists Polk and Sumter tracts under both Tampa and Orlando", () => {
    const dual = new Map<string, Set<string>>();
    for (const row of catalog.rows) {
      const markets = dual.get(row.geoid) ?? new Set<string>();
      markets.add(row.market);
      dual.set(row.geoid, markets);
    }
    const shared = [...dual.entries()].filter(([, markets]) => markets.has("Tampa") && markets.has("Orlando"));
    expect(shared.length).toBe(22);
    const counties = new Set(
      shared.map(([geoid]) => catalog.rows.find((row) => row.geoid === geoid)?.county),
    );
    expect(counties).toEqual(new Set(["Polk", "Sumter"]));
    const sample = shared[0][0];
    expect(filterRuralRows(catalog.rows, "Tampa", null, null).some((row) => row.geoid === sample)).toBe(true);
    expect(filterRuralRows(catalog.rows, "Orlando", null, null).some((row) => row.geoid === sample)).toBe(true);
  });

  it("keeps Charlotte Union in North Carolina and the Orange County rural tract on Orlando", () => {
    const union = filterRuralRows(catalog.rows, "Charlotte", "Union", "North Carolina");
    expect(union).toHaveLength(1);
    expect(union[0].state).toBe("North Carolina");
    expect(filterRuralRows(catalog.rows, "Charlotte", "Union", "South Carolina")).toHaveLength(0);
    expect(formatCountyLabel("Union", "North Carolina")).toBe("Union, NC");
    expect(countyKey("Union", "North Carolina")).not.toBe(countyKey("Union", "South Carolina"));

    const orange = filterRuralRows(catalog.rows, "Orlando", "Orange", "Florida");
    expect(orange.map((row) => row.geoid)).toEqual(["12095016605"]);
    expect(orange[0].outerEdge).toBe(false);
  });

  it("flags outer-edge counties in notes and keeps the Orange County pilot camera", () => {
    const banks = filterRuralRows(catalog.rows, "Atlanta", "Banks", "Georgia");
    expect(banks.length).toBeGreaterThan(0);
    expect(banks.every((row) => row.outerEdge)).toBe(true);
    expect(banks[0].notes.toLowerCase()).toContain("outer/uncertain edge");

    const summary = catalog.markets.find((item) => item.market === "Orlando");
    expect(summary).toBeTruthy();
    const pilotBounds = viewBounds(summary!, catalog.rows, "Orange", "Florida");
    expect(pilotBounds[0][0]).toBeLessThan(-81.6);
    expect(pilotBounds[1][0]).toBeGreaterThan(-81.1);
    expect(showOrangeCountyPilot("Orlando", "Orange", "Florida")).toBe(true);
    expect(showOrangeCountyPilot("Orlando", null, null)).toBe(true);
    expect(showOrangeCountyPilot("Orlando", "Polk", "Florida")).toBe(false);
    expect(showOrangeCountyPilot("Atlanta", null, null)).toBe(false);
  });

  it("documents Orlando shed parcels beyond the Orange sample", () => {
    expect(catalog.parcelNote.toLowerCase()).toContain("brevard");
    expect(catalog.parcelNote.toLowerCase()).toContain("volusia");
    expect(catalog.parcelNote.toLowerCase()).not.toContain("parcel extract is orange county only");
  });

  it("joins every GEOID to a 2020 tract polygon tagged rural and not designated", () => {
    const collection = JSON.parse(
      readFileSync("data/fixtures/oz2-rural-markets.geojson", "utf8"),
    ) as RuralMarketTractCollection;
    const geoids = new Set(catalog.rows.map((row) => row.geoid));
    expect(collection.features).toHaveLength(geoids.size);
    const drawn = new Set(collection.features.map((feature) => feature.properties.tractGeoid));
    expect(drawn).toEqual(geoids);
    expect(
      collection.features.every(
        (feature) =>
          feature.properties.rural === true &&
          feature.properties.designation === "eligible-for-nomination" &&
          feature.properties.statusChip === RURAL_ELIGIBLE_STATUS_CHIP &&
          feature.properties.source === "rev-proc-2026-14" &&
          (feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon"),
      ),
    ).toBe(true);
    const shared = collection.features.find((feature) => feature.properties.markets.length > 1);
    expect(shared?.properties.markets).toEqual(["Tampa", "Orlando"]);
    expect(collection.features.some((feature) => feature.properties.tractGeoid === "12095016605")).toBe(true);
  });
});

describe("filterRuralRows", () => {
  const rows: RuralMarketTractRow[] = [
    {
      market: "Tampa",
      state: "Florida",
      county: "Polk",
      geoid: "12105014104",
      placeOrCorridor: "Polk",
      rural: "Y",
      status: RURAL_ELIGIBLE_STATUS_CHIP,
      lat: 28,
      lon: -82,
      notes: "Rev. Proc. 2026-14 appendix Rural (entirely rural)",
      outerEdge: false,
      specialUse: false,
    },
    {
      market: "Orlando",
      state: "Florida",
      county: "Polk",
      geoid: "12105014104",
      placeOrCorridor: "Polk",
      rural: "Y",
      status: RURAL_ELIGIBLE_STATUS_CHIP,
      lat: 28,
      lon: -82,
      notes: "Rev. Proc. 2026-14 appendix Rural (entirely rural)",
      outerEdge: false,
      specialUse: false,
    },
  ];

  it("does not drop a dual-listed row when the other market is selected", () => {
    expect(filterRuralRows(rows, "Tampa", "Polk", "Florida")).toHaveLength(1);
    expect(filterRuralRows(rows, "Orlando", "Polk", "Florida")).toHaveLength(1);
    expect(filterRuralRows(rows, "Tampa", "Polk", "Georgia")).toHaveLength(0);
  });
});

describe("South Carolina governor-filed status copy", () => {
  const catalog = loadCatalog();

  it("keeps the eligible chip and adds governor-filed help only for South Carolina views", () => {
    expect(SC_GOVERNOR_FILED_STATUS).toBe(
      "SC: Governor filed nominations with Treasury (Sep 10, 2026 per SC Commerce). Official nominated tract list is not publicly posted. Tracts on this map are not designated QOZs.",
    );
    expect(SC_GOVERNOR_FILED_STATUS).not.toMatch(/^designated/i);

    expect(viewIncludesSouthCarolina("Charleston", null)).toBe(true);
    expect(viewIncludesSouthCarolina("Charlotte", null)).toBe(true);
    expect(viewIncludesSouthCarolina("Charlotte", "South Carolina")).toBe(true);
    expect(viewIncludesSouthCarolina("Charlotte", "North Carolina")).toBe(false);
    for (const market of ["Atlanta", "Tampa", "Orlando", "Nashville", "Raleigh-Durham"] as const) {
      expect(viewIncludesSouthCarolina(market, null)).toBe(false);
      expect(southCarolinaStatusHelp(market, null)).toBeNull();
    }

    const charleston = southCarolinaStatusHelp("Charleston", null);
    const york = southCarolinaStatusHelp("Charlotte", "South Carolina");
    const charlotteAll = southCarolinaStatusHelp("Charlotte", null);
    expect(charleston).toMatch(/not public/i);
    expect(charleston).toMatch(/not designated/i);
    expect(york).toMatch(/not designated/i);
    expect(charlotteAll).toMatch(/York, Lancaster, and Chester/);
    expect(charlotteAll).toMatch(/North Carolina/);
    expect(southCarolinaStatusHelp("Charlotte", "North Carolina")).toBeNull();

    for (const note of [charleston, york, charlotteAll]) {
      expect(note).not.toMatch(/\b\d{11}\b/);
      expect(note).not.toMatch(/certified 2027/i);
    }
  });

  it("does not relabel Florida, Georgia, North Carolina, or Tennessee rows", () => {
    const untouched = catalog.rows.filter((row) => row.state !== "South Carolina");
    expect(untouched.length).toBeGreaterThan(0);
    expect(untouched.every((row) => row.status === RURAL_ELIGIBLE_STATUS_CHIP)).toBe(true);
    expect(catalog.rows.filter((row) => row.state === "South Carolina").every((row) => row.status === RURAL_ELIGIBLE_STATUS_CHIP)).toBe(
      true,
    );
    expect(filterRuralRows(catalog.rows, "Charlotte", "York", "South Carolina").length).toBeGreaterThan(0);
    expect(filterRuralRows(catalog.rows, "Charlotte", "Lancaster", "South Carolina").length).toBeGreaterThan(0);
    expect(filterRuralRows(catalog.rows, "Charleston", null, null).every((row) => row.state === "South Carolina")).toBe(
      true,
    );
  });
});
