import { mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import { canonicalStreet, stateAbbr } from "../src/lib/parcelAddress";

const roots = ["data/fixtures/market-parcels", "data/fixtures/orlando-parcels"];
const outDir = path.join("data", "address-index");

const files: string[] = [];
for (const root of roots) walk(path.join(process.cwd(), root), files);
files.sort();

const seen = new Set<string>();
const buckets = new Map<string, string[]>();
let scanned = 0;
let kept = 0;

for (const file of files) {
  extract(readFileSync(file, "utf8"));
  scanned += 1;
  if (scanned % 250 === 0) console.log(`scanned ${scanned}/${files.length} kept ${kept}`);
}

mkdirSync(outDir, { recursive: true });
const states = [...buckets.keys()].sort();
for (const state of states) {
  const lines = buckets.get(state) ?? [];
  lines.sort();
  const target = path.join(outDir, `${state}.tsv`);
  writeFileSync(target, lines.join("\n") + (lines.length ? "\n" : ""));
  console.log(`${state} ${lines.length} ${target}`);
}
console.log(`files ${files.length} rows ${kept} states ${states.length}`);

function walk(dir: string, out: string[]) {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (name.endsWith(".geojson")) out.push(full);
  }
}

function extract(text: string) {
  const needle = '"situsAddress":';
  let idx = 0;
  while ((idx = text.indexOf(needle, idx)) !== -1) {
    const state = lastState(text.slice(Math.max(0, idx - 800), idx));
    const abbr = stateAbbr(state);
    const head = text.slice(idx, idx + 600);
    const parsed = head.match(
      /^"situsAddress":(?:"((?:\\.|[^"\\])*)"|null),"situsCity":(?:"((?:\\.|[^"\\])*)"|null),"situsZip":(?:"((?:\\.|[^"\\])*)"|null)/,
    );
    if (!parsed?.[1] || !abbr) {
      idx += needle.length;
      continue;
    }
    const canon = canonicalStreet(unescape(parsed[1]));
    if (!canon.number || !canon.street) {
      idx += needle.length;
      continue;
    }
    const centroid = text.slice(idx, idx + 4000).match(/"centroid":\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)/);
    if (!centroid) {
      idx += needle.length;
      continue;
    }
    const city = (parsed[2] ? unescape(parsed[2]) : "").toUpperCase().replace(/[^A-Z0-9]+/g, " ").replace(/\s+/g, " ").trim();
    const zip = (parsed[3] ?? "").match(/\d{5}/)?.[0] ?? "";
    const lng = Number(centroid[1]);
    const lat = Number(centroid[2]);
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
      idx += needle.length;
      continue;
    }
    const key = `${abbr}\t${canon.number}\t${canon.street}\t${city}\t${zip}`;
    if (!seen.has(key)) {
      seen.add(key);
      const line = `${canon.number}\t${canon.street}\t${city}\t${zip}\t${lng.toFixed(5)}\t${lat.toFixed(5)}`;
      const bucket = buckets.get(abbr);
      if (bucket) bucket.push(line);
      else buckets.set(abbr, [line]);
      kept += 1;
    }
    idx += needle.length;
  }
}

function lastState(slice: string): string | null {
  const matches = slice.match(/"state":"([^"]+)"/g);
  if (!matches?.length) return null;
  return matches[matches.length - 1]?.match(/"state":"([^"]+)"/)?.[1] ?? null;
}

function unescape(value: string): string {
  return value.replace(/\\"/g, '"').replace(/\\\\/g, "\\");
}
