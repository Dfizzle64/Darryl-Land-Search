import {
  ELIGIBLE_NOT_DESIGNATED_STATUS,
  MARKETS,
  ORANGE_COUNTY_BOUNDS,
  OTHER_MARKETS,
  PARCEL_MARKETS,
  RURAL_ELIGIBLE_STATUS_CHIP,
  SC_GOVERNOR_FILED_STATUS,
  type EligibleMarketsCatalog,
  type EligibleTractRow,
  type MarketCountySummary,
  type MarketId,
  type MarketSummary,
  type OtherMarketId,
  type ParcelMarketId,
  type RuralMarketTractRow,
  type RuralMarketsCatalog,
  type SearchMarketId,
  type TractClassView,
} from "./types";
import { showOrangeCountyPilot, showOrlandoParcels } from "./orlandoParcels";

export { showOrangeCountyPilot, showOrlandoParcels } from "./orlandoParcels";

export const STATE_ABBR: Record<string, string> = {
  Florida: "FL",
  Georgia: "GA",
  "South Carolina": "SC",
  "North Carolina": "NC",
  Tennessee: "TN",
  Alabama: "AL",
  Mississippi: "MS",
  Arkansas: "AR",
};

export function isMarketId(value: string): value is MarketId {
  return (MARKETS as readonly string[]).includes(value);
}

export function isOtherMarketId(value: string): value is OtherMarketId {
  return (OTHER_MARKETS as readonly string[]).includes(value);
}

export function isParcelMarketId(value: string): value is ParcelMarketId {
  return (PARCEL_MARKETS as readonly string[]).includes(value);
}

export function isSearchMarketId(value: string): value is SearchMarketId {
  return isMarketId(value) || isOtherMarketId(value) || isParcelMarketId(value);
}

/**
 * Asheville is Henderson plus Buncombe parcels. No eligible-tract rows are added,
 * and nothing in this summary is a designated Opportunity Zone.
 * Heartland is the Florida shelf. It also has no eligible-tract rows.
 */
const PARCEL_MARKET_SUMMARIES: Record<ParcelMarketId, MarketSummary> = {
  Asheville: {
    market: "Asheville",
    rowCount: 0,
    ruralCount: 0,
    urbanCount: 0,
    bounds: [
      [-82.95, 35.05],
      [-82.15, 35.82],
    ],
    center: [-82.55, 35.435],
    counties: [
      { county: "Buncombe", state: "North Carolina", count: 0, outerEdge: false },
      { county: "Henderson", state: "North Carolina", count: 0, outerEdge: false },
    ],
  },
};

const PARCEL_ONLY_MARKETS: Partial<Record<SearchMarketId, MarketSummary>> = {
  Heartland: {
    market: "Heartland",
    rowCount: 0,
    ruralCount: 0,
    urbanCount: 0,
    bounds: [
      [-82.25, 26.05],
      [-80.65, 27.85],
    ],
    center: [-81.45, 26.95],
    counties: [
      { county: "DeSoto", state: "Florida", count: 0, outerEdge: false },
      { county: "Glades", state: "Florida", count: 0, outerEdge: false },
      { county: "Hardee", state: "Florida", count: 0, outerEdge: false },
      { county: "Hendry", state: "Florida", count: 0, outerEdge: false },
      { county: "Highlands", state: "Florida", count: 0, outerEdge: false },
    ],
  },
};

export function parcelMarketSummary(market: ParcelMarketId): MarketSummary {
  return PARCEL_MARKET_SUMMARIES[market];
}

export function isPrimaryMarket(value: string): value is MarketId {
  return isMarketId(value);
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

export function marketSummary(
  catalog: { markets: MarketSummary[] },
  market: SearchMarketId,
): MarketSummary {
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

export function viewBounds(
  summary: MarketSummary,
  rows: Array<{ market: string; county: string; state: string; lat: number; lon: number }>,
  county: string | null,
  state: string | null,
  options?: { fitRows?: boolean },
): [[number, number], [number, number]] {
  if (showOrangeCountyPilot(summary.market, county, state) && county === "Orange") {
    return ORANGE_COUNTY_BOUNDS;
  }
  if (!county && !options?.fitRows) return summary.bounds;
  const subset = !county
    ? rows.filter((row) => row.market === summary.market)
    : rows.filter((row) => row.market === summary.market && row.county === county && row.state === state);
  if (subset.length === 0) {
    // Seminole has parcels but 0 rural-eligible tracts — use a county envelope.
    if (showOrlandoParcels(summary.market, county, state) && county === "Seminole") {
      return [
        [-81.48, 28.6],
        [-81.08, 28.88],
      ];
    }
    return summary.bounds;
  }
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
const ENTIRELY_SOUTH_CAROLINA_MARKETS = new Set<SearchMarketId>(["Charleston", "Columbia", "Greenville"]);

/**
 * Charleston, Columbia, and Greenville are entirely South Carolina.
 * Charlotte’s shed includes York, Lancaster, and Chester.
 * Savannah’s shed includes Beaufort and Jasper.
 */
export function viewIncludesSouthCarolina(market: SearchMarketId, state: string | null): boolean {
  if (ENTIRELY_SOUTH_CAROLINA_MARKETS.has(market)) return true;
  if (market === "Charlotte" || market === "Savannah") {
    return state == null || isSouthCarolinaState(state);
  }
  return false;
}

/**
 * Help copy for a view that includes South Carolina tracts. Null for FL/GA/NC/TN-only views.
 * Does not name nominated GEOIDs — the public list is not posted.
 */
export function southCarolinaStatusHelp(market: SearchMarketId, state: string | null): string | null {
  if (!viewIncludesSouthCarolina(market, state)) return null;
  if (market === "Charlotte" && !isSouthCarolinaState(state)) {
    return `${SC_GOVERNOR_FILED_STATUS} In this shed that filing covers York, Lancaster, and Chester. North Carolina tracts stay on the eligible list and are not designated QOZs.`;
  }
  if (market === "Savannah" && !isSouthCarolinaState(state)) {
    return `${SC_GOVERNOR_FILED_STATUS} In this shed that filing covers Beaufort and Jasper. Georgia tracts stay on the eligible list and are not designated QOZs.`;
  }
  return SC_GOVERNOR_FILED_STATUS;
}

export function filterEligibleRows(
  rows: EligibleTractRow[],
  market: SearchMarketId,
  county: string | null,
  state: string | null,
): EligibleTractRow[] {
  return rows.filter((row) => {
    if (row.market !== market) return false;
    if (county && row.county !== county) return false;
    if (state && row.state !== state) return false;
    return true;
  });
}

export function rowMatchesTractClass(rural: "Y" | "N", view: TractClassView): boolean {
  if (view === "both") return true;
  return view === "rural" ? rural === "Y" : rural === "N";
}

/**
 * Map-layer rural/urban cut. "none" means the rural and urban filters contradict
 * (for example the parcel filter is rural-eligible while the legend is urban).
 */
export function eligibleClassCut(
  tractClass: TractClassView,
  ozFilter: "either" | "in" | "out" | "rural-eligible" | "non-rural-eligible",
): "all" | "rural" | "urban" | "none" {
  const rural = tractClass === "rural" || ozFilter === "rural-eligible";
  const urban = tractClass === "urban" || ozFilter === "non-rural-eligible";
  if (rural && urban) return "none";
  if (rural) return "rural";
  if (urban) return "urban";
  return "all";
}

export function displayStatusChip(row: { market: string; rural: "Y" | "N"; status?: string | null }): string {
  if (row.rural === "Y" && isPrimaryMarket(row.market)) return RURAL_ELIGIBLE_STATUS_CHIP;
  return ELIGIBLE_NOT_DESIGNATED_STATUS;
}

export function governorFiledInNotes(notes: string | null | undefined): boolean {
  return Boolean(notes && notes.toLowerCase().includes("governor-filed"));
}

export function showsGovernorFiledSoftCopy(row: { state: string; notes: string }): boolean {
  return isSouthCarolinaState(row.state) || governorFiledInNotes(row.notes);
}

export function summarizeCounties(
  rows: Array<Pick<RuralMarketTractRow, "county" | "state" | "outerEdge">>,
): MarketCountySummary[] {
  const counties = new Map<string, MarketCountySummary>();
  for (const row of rows) {
    const key = countyKey(row.county, row.state);
    const bucket = counties.get(key) ?? { county: row.county, state: row.state, count: 0, outerEdge: false };
    bucket.count += 1;
    bucket.outerEdge = bucket.outerEdge || row.outerEdge;
    counties.set(key, bucket);
  }
  return Array.from(counties.values()).sort((a, b) => a.state.localeCompare(b.state) || a.county.localeCompare(b.county));
}

export function unionBounds(
  left: [[number, number], [number, number]],
  right: [[number, number], [number, number]],
): [[number, number], [number, number]] {
  return [
    [Math.min(left[0][0], right[0][0]), Math.min(left[0][1], right[0][1])],
    [Math.max(left[1][0], right[1][0]), Math.max(left[1][1], right[1][1])],
  ];
}

export function catalogForMarket(
  ruralCatalog: RuralMarketsCatalog,
  urbanCatalog: EligibleMarketsCatalog,
  otherCatalog: EligibleMarketsCatalog,
  market: SearchMarketId,
): MarketSummary {
  if (isParcelMarketId(market)) return parcelMarketSummary(market);
  const catalog = isPrimaryMarket(market) ? ruralCatalog : otherCatalog;
  if (!isPrimaryMarket(market)) {
    const summary = catalog.markets.find((item) => item.market === market);
    if (summary) return summary;
    const parcelOnly = PARCEL_ONLY_MARKETS[market];
    if (parcelOnly) return parcelOnly;
    throw new Error(`Catalog is missing market ${market}`);
  }
  const rural = marketSummary(ruralCatalog, market);
  const urban = urbanCatalog.markets.find((item) => item.market === market);
  if (!urban) return rural;
  return {
    ...rural,
    ruralCount: rural.rowCount,
    urbanCount: urban.rowCount,
    bounds: unionBounds(rural.bounds, urban.bounds),
  };
}

export function isOuterEdgeNote(notes: string | null | undefined): boolean {
  return Boolean(notes && notes.toLowerCase().includes("outer/uncertain edge"));
}
