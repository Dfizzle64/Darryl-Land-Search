import {
  MARKETS,
  ORANGE_COUNTY_BOUNDS,
  RURAL_ELIGIBLE_STATUS_CHIP,
  type MarketCountySummary,
  type MarketId,
  type MarketSummary,
  type RuralMarketTractRow,
  type RuralMarketsCatalog,
} from "./types";

export const STATE_ABBR: Record<string, string> = {
  Florida: "FL",
  Georgia: "GA",
  "South Carolina": "SC",
  "North Carolina": "NC",
  Tennessee: "TN",
};

export function isMarketId(value: string): value is MarketId {
  return (MARKETS as readonly string[]).includes(value);
}

/** State-aware county key so Charlotte's NC Union is not SC Union. */
export function countyKey(county: string, state: string): string {
  return `${state}|${county}`;
}

export function parseCountyKey(key: string): { state: string; county: string } | null {
  const split = key.indexOf("|");
  if (split <= 0) return null;
  return { state: key.slice(0, split), county: key.slice(split + 1) };
}

export function formatCountyLabel(county: string, state: string): string {
  const abbr = STATE_ABBR[state] ?? state;
  return `${county}, ${abbr}`;
}

export function marketSummary(catalog: RuralMarketsCatalog, market: MarketId): MarketSummary {
  const summary = catalog.markets.find((item) => item.market === market);
  if (!summary) {
    throw new Error(`Catalog is missing market ${market}`);
  }
  return summary;
}

export function filterRuralRows(
  rows: RuralMarketTractRow[],
  market: MarketId,
  county: string | null,
  state: string | null,
): RuralMarketTractRow[] {
  return rows.filter((row) => {
    if (row.market !== market) return false;
    if (county && row.county !== county) return false;
    if (state && row.state !== state) return false;
    return true;
  });
}

/**
 * Orange County parcel pilot (green parcels, all eligible tracts, designated
 * QOZ overlay, FDOT) stays on while Orlando is selected and the county filter
 * is all counties or Orange County, Florida.
 */
export function showOrangeCountyPilot(market: MarketId, county: string | null, state: string | null): boolean {
  if (market !== "Orlando") return false;
  if (!county && !state) return true;
  return county === "Orange" && state === "Florida";
}

export function viewBounds(
  summary: MarketSummary,
  rows: RuralMarketTractRow[],
  county: string | null,
  state: string | null,
): [[number, number], [number, number]] {
  if (showOrangeCountyPilot(summary.market, county, state) && county === "Orange") {
    return ORANGE_COUNTY_BOUNDS;
  }
  if (!county) return summary.bounds;
  const subset = rows.filter((row) => row.market === summary.market && row.county === county && row.state === state);
  if (subset.length === 0) return summary.bounds;
  let west = Math.min(...subset.map((row) => row.lon));
  let east = Math.max(...subset.map((row) => row.lon));
  let south = Math.min(...subset.map((row) => row.lat));
  let north = Math.max(...subset.map((row) => row.lat));
  if (east - west < 0.12) {
    const pad = (0.12 - (east - west)) / 2;
    west -= pad;
    east += pad;
  }
  if (north - south < 0.12) {
    const pad = (0.12 - (north - south)) / 2;
    south -= pad;
    north += pad;
  }
  return [
    [west, south],
    [east, north],
  ];
}

export function countyOptions(summary: MarketSummary): MarketCountySummary[] {
  return summary.counties;
}

export function ruralStatusChip(row: Pick<RuralMarketTractRow, "status"> | null | undefined): string {
  return row?.status || RURAL_ELIGIBLE_STATUS_CHIP;
}

export function isSouthCarolinaState(state: string | null | undefined): boolean {
  return state === "South Carolina";
}

/**
 * Charleston is entirely South Carolina. Charlotte’s shed includes York,
 * Lancaster, and Chester. Other markets in this app have no South Carolina tracts.
 */
export function viewIncludesSouthCarolina(market: MarketId, state: string | null): boolean {
  if (market === "Charleston") return true;
  if (market !== "Charlotte") return false;
  return state == null || isSouthCarolinaState(state);
}

/**
 * Help copy for a view that includes South Carolina tracts. Null for FL/GA/NC/TN-only views.
 * Does not name nominated GEOIDs — the public list is not posted.
 */
export function southCarolinaStatusHelp(market: MarketId, state: string | null): string | null {
  if (!viewIncludesSouthCarolina(market, state)) return null;
  if (market === "Charleston" || isSouthCarolinaState(state)) {
    return "South Carolina’s governor filed OZ 2.0 nominations with Treasury on Sep 10, 2026. The nominated tract list is not public yet, so these tracts stay eligible and are not designated.";
  }
  return "York, Lancaster, and Chester, South Carolina: the governor filed OZ 2.0 nominations on Sep 10, 2026. The list is not public yet, so those tracts stay eligible and are not designated. North Carolina tracts in this market stay eligible and are not designated.";
}

export function isOuterEdgeNote(notes: string | null | undefined): boolean {
  return Boolean(notes && notes.toLowerCase().includes("outer/uncertain edge"));
}
