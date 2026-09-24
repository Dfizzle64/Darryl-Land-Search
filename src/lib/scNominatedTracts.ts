import nominatedCsv from "../../data/oz/sc-oz2-nominated-official-sccommerce-2026-09-23.csv?raw";
import { SC_GOVERNOR_NOMINATED_STATUS } from "./types";

export const SC_NOMINATED_SOURCE_CSV = "data/oz/sc-oz2-nominated-official-sccommerce-2026-09-23.csv";

const STALE_SC_NOTE =
  "Eligible — not designated (SC Governor-filed Sep 10, 2026; nominated GEOID list not public)";

export type ScNominatedCsvSummary = {
  geoids: string[];
  ruralCount: number;
  nonRuralCount: number;
};

/** Exact GEOID membership from the official SC Commerce CSV. Counties are not inferred. */
export function parseScNominatedCsv(text: string): ScNominatedCsvSummary {
  const lines = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  if (lines.length < 2) throw new Error("SC nominated CSV is empty");
  const header = lines[0].split(",").map((cell) => cell.trim());
  const geoidIdx = header.indexOf("geoid");
  const typeIdx = header.indexOf("type");
  if (geoidIdx < 0 || typeIdx < 0) throw new Error("SC nominated CSV is missing geoid or type");

  const geoids: string[] = [];
  const seen = new Set<string>();
  let ruralCount = 0;
  let nonRuralCount = 0;
  for (const line of lines.slice(1)) {
    if (!line.trim()) continue;
    const cells = line.split(",");
    const geoid = cells[geoidIdx]?.trim() ?? "";
    const type = cells[typeIdx]?.trim() ?? "";
    if (!/^\d{11}$/.test(geoid)) throw new Error(`SC nominated CSV has a bad GEOID: ${geoid}`);
    if (seen.has(geoid)) throw new Error(`SC nominated CSV repeats GEOID ${geoid}`);
    seen.add(geoid);
    geoids.push(geoid);
    if (type === "Rural") ruralCount += 1;
    else if (type === "Non-rural") nonRuralCount += 1;
    else throw new Error(`SC nominated CSV has a bad type for ${geoid}: ${type}`);
  }
  return { geoids, ruralCount, nonRuralCount };
}

const parsed = parseScNominatedCsv(nominatedCsv);
if (parsed.geoids.length !== 112 || parsed.ruralCount !== 84 || parsed.nonRuralCount !== 28) {
  throw new Error(
    `SC nominated list expected 112 tracts (84 rural / 28 non-rural), got ${parsed.geoids.length} (${parsed.ruralCount} rural / ${parsed.nonRuralCount} non-rural)`,
  );
}

const SC_GOVERNOR_NOMINATED_GEOIDS = new Set(parsed.geoids);

export function scGovernorNominatedGeoids(): ReadonlySet<string> {
  return SC_GOVERNOR_NOMINATED_GEOIDS;
}

export function isScGovernorNominatedGeoid(geoid: string | null | undefined): boolean {
  return Boolean(geoid && SC_GOVERNOR_NOMINATED_GEOIDS.has(geoid));
}

/** Soft-upgrade only. Eligible chips stay in place when the GEOID is not on the official list. */
export function scTractStatusChip(geoid: string | null | undefined, eligibleChip: string): string {
  return isScGovernorNominatedGeoid(geoid) ? SC_GOVERNOR_NOMINATED_STATUS : eligibleChip;
}

/**
 * Stored notes still describe the pre-list filing. The chip is the status;
 * this only stops the drawer from saying the GEOID list is unpublished.
 */
export function displayTractNotes(notes: string, geoid: string): string {
  if (!notes.includes(STALE_SC_NOTE)) return notes;
  const replacement = isScGovernorNominatedGeoid(geoid)
    ? "Governor-nominated / awaiting Treasury (SC Commerce Final Recommendations dated 2026-09-22; not a designated QOZ)"
    : "Eligible — not designated (not on South Carolina’s official nominated list)";
  return notes.replaceAll(STALE_SC_NOTE, replacement);
}
