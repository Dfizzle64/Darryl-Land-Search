import { readFileSync } from "node:fs";
import path from "node:path";
import { findParcelHits, parseAddressQuery, type ParcelAddressHit } from "./parcelAddress";

const cache = new Map<string, string>();

/** One state file, cached after the first read. Missing states are an empty index. */
export function parcelHits(query: string, read: (state: string) => string | null = readParcelState): ParcelAddressHit[] {
  const state = parseAddressQuery(query).state;
  if (!state) return [];
  return findParcelHits(read(state) ?? "", query);
}

export function readParcelState(state: string): string | null {
  const abbr = state.toUpperCase();
  if (cache.has(abbr)) return cache.get(abbr) ?? null;
  try {
    const text = readFileSync(path.join(process.cwd(), "data", "address-index", `${abbr}.tsv`), "utf8");
    cache.set(abbr, text);
    return text;
  } catch {
    cache.set(abbr, "");
    return "";
  }
}

