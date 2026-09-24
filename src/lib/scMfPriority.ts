import type {
  MfPriorityInfo,
  MfPriorityTier,
  MfPriorityView,
  RuralMarketTractRow,
  ScMfPriorityCatalog,
  ScMfPriorityTract,
} from "./types";

export const MF_PRIORITY_DISCLAIMER =
  "INTERNAL multifamily hunt ranking among rural-eligible tracts (Charleston + York/Lancaster/Chester scope). NOT SC Commerce, NOT a nomination list, NOT OZ designation. Tier A = chase first. Tier B = secondary / still map-worthy.";

export const NOM_WATCH_CAVEAT =
  "Nom-watch in the notes is an inference from corridor growth, not a confirmed nomination.";

export function mfPriorityLookup(catalog: ScMfPriorityCatalog): Map<string, ScMfPriorityTract> {
  return new Map(catalog.rows.map((row) => [row.geoid, row]));
}

export function toMfPriorityInfo(row: ScMfPriorityTract): MfPriorityInfo {
  return {
    tier: row.tier,
    rank: row.rank,
    place: row.place,
    mfRationale: row.mfRationale,
    acreageRealism: row.acreageRealism,
    notes: row.notes,
  };
}

/** Attach shortlist fields without changing status, market, or the seven-market place label. */
export function annotateRuralRows(rows: RuralMarketTractRow[], catalog: ScMfPriorityCatalog): RuralMarketTractRow[] {
  const lookup = mfPriorityLookup(catalog);
  return rows.map((row) => {
    const priority = lookup.get(row.geoid);
    if (!priority || priority.market !== row.market) return row;
    return { ...row, mfPriority: toMfPriorityInfo(priority) };
  });
}

export function filterByMfPriority<T extends { mfPriority?: MfPriorityInfo | null }>(rows: T[], view: MfPriorityView): T[] {
  if (view === "all") return rows;
  return rows.filter((row) => {
    const tier = row.mfPriority?.tier;
    if (!tier) return false;
    if (view === "priority") return true;
    return tier === view;
  });
}

/** Tier A, then Tier B (CSV rank), then the rest of the rural pack. */
export function sortTractsForDisplay<T extends { mfPriority?: MfPriorityInfo | null }>(rows: T[]): T[] {
  const group = (row: T) => {
    if (row.mfPriority?.tier === "A") return 0;
    if (row.mfPriority?.tier === "B") return 1;
    return 2;
  };
  return [...rows].sort((a, b) => {
    const byGroup = group(a) - group(b);
    if (byGroup !== 0) return byGroup;
    const aRank = a.mfPriority?.rank ?? Number.MAX_SAFE_INTEGER;
    const bRank = b.mfPriority?.rank ?? Number.MAX_SAFE_INTEGER;
    return aRank - bRank;
  });
}

export function countMfPriority(rows: Array<{ mfPriority?: MfPriorityInfo | null }>): { all: number; priority: number; A: number; B: number } {
  let priority = 0;
  let tierA = 0;
  let tierB = 0;
  for (const row of rows) {
    if (row.mfPriority?.tier === "A") {
      priority += 1;
      tierA += 1;
    } else if (row.mfPriority?.tier === "B") {
      priority += 1;
      tierB += 1;
    }
  }
  return { all: rows.length, priority, A: tierA, B: tierB };
}

export function geoidsForHighlight(
  rows: Array<{ geoid: string; mfPriority?: MfPriorityInfo | null }>,
  view: MfPriorityView,
  tier: MfPriorityTier,
): string[] {
  if (view !== "all" && view !== "priority" && view !== tier) return [];
  return rows.filter((row) => row.mfPriority?.tier === tier).map((row) => row.geoid);
}

/** Null means the rural layer stays on the full county/market set. */
export function geoidFilterForView(
  rows: Array<{ geoid: string; mfPriority?: MfPriorityInfo | null }>,
  view: MfPriorityView,
): string[] | null {
  if (view === "all") return null;
  return filterByMfPriority(rows, view).map((row) => row.geoid);
}

export function tractPlaceLabel(row: { placeOrCorridor: string; mfPriority?: MfPriorityInfo | null }): string {
  return row.mfPriority?.place || row.placeOrCorridor;
}
