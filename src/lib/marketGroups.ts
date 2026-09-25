import { catalogForMarket } from "./markets";
import {
  MARKETS,
  OTHER_MARKETS,
  PARCEL_MARKETS,
  type EligibleMarketsCatalog,
  type RuralMarketsCatalog,
  type SearchMarketId,
} from "./types";

/**
 * Shelves whose catalog row has no county list. The city is still that state.
 * Tuscaloosa and Montgomery are Alabama parcel shelves with empty county arrays.
 */
const SHELF_STATE: Partial<Record<SearchMarketId, string>> = {
  Tuscaloosa: "Alabama",
  Montgomery: "Alabama",
};

export type MarketStateGroup = {
  state: string;
  markets: SearchMarketId[];
};

/**
 * States A to Z. Markets A to Z inside each state.
 * A market that covers more than one state is listed under each of those states
 * so every existing market stays reachable, including the South Florida shelf.
 */
export function groupMarketsByState(
  ruralCatalog: RuralMarketsCatalog,
  urbanCatalog: EligibleMarketsCatalog,
  otherCatalog: EligibleMarketsCatalog,
): MarketStateGroup[] {
  const byState = new Map<string, Set<SearchMarketId>>();
  const ids: SearchMarketId[] = [...MARKETS, ...OTHER_MARKETS, ...PARCEL_MARKETS];
  for (const market of ids) {
    const summary = catalogForMarket(ruralCatalog, urbanCatalog, otherCatalog, market);
    const states = [...new Set(summary.counties.map((county) => county.state).filter((state) => state.length > 0))];
    if (states.length === 0) {
      const fallback = SHELF_STATE[market];
      if (fallback) states.push(fallback);
    }
    for (const state of states) {
      const bucket = byState.get(state) ?? new Set<SearchMarketId>();
      bucket.add(market);
      byState.set(state, bucket);
    }
  }
  return [...byState.entries()]
    .sort((a, b) => a[0].localeCompare(b[0], "en", { sensitivity: "base" }))
    .map(([state, markets]) => ({
      state,
      markets: [...markets].sort((a, b) => a.localeCompare(b, "en", { sensitivity: "base" })),
    }));
}
