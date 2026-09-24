#!/usr/bin/env python3
"""Seed the South Carolina multifamily priority shortlist.

Reads data/sc-oz2-mf-priority-shortlist.csv and checks every GEOID against the
seven-market rural-eligible table. This is a likelihood ranking among tracts
that are already eligible and rural. It does not nominate or designate anything.

Usage:
  python3 scripts/seed_sc_mf_priority.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHORTLIST_CSV = ROOT / "data" / "sc-oz2-mf-priority-shortlist.csv"
RURAL_CSV = ROOT / "data" / "oz2-7markets-90min-rural-eligible.csv"
FIXTURES = ROOT / "data" / "fixtures"
OUT_PATH = FIXTURES / "sc-oz2-mf-priority.json"

STATUS_CHIP = "Eligible (rural) — not designated"
GOVERNOR_FILED = (
    "SC: Governor filed nominations with Treasury (Sep 10, 2026 per SC Commerce). "
    "Official nominated tract list is not publicly posted. Tracts on this map are not designated QOZs."
)
SOURCE_STATUS = (
    "Eligible rural — SC Gov filed statewide Sep 10 2026 / not designated; "
    "this GEOID not confirmed nominated"
)
DISCLAIMER = (
    "INTERNAL multifamily hunt ranking among rural-eligible tracts "
    "(Charleston + York/Lancaster/Chester scope). NOT SC Commerce, NOT a nomination list, "
    "NOT OZ designation. Tier A = chase first. Tier B = secondary / still map-worthy."
)
EXPECTED_COLUMNS = [
    "market",
    "county",
    "geoid",
    "place",
    "rural",
    "status",
    "tier",
    "mf_rationale",
    "acreage_realism",
    "lat",
    "lon",
    "notes",
]


def load_rural_index() -> dict[str, dict]:
    if not RURAL_CSV.exists():
        raise RuntimeError(f"Missing seven-market CSV: {RURAL_CSV}")
    index: dict[str, dict] = {}
    with RURAL_CSV.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            geoid = raw["geoid"].strip()
            index[geoid] = {
                "market": raw["market"].strip(),
                "state": raw["state"].strip(),
                "county": raw["county"].strip(),
                "lat": float(raw["lat"]),
                "lon": float(raw["lon"]),
            }
    return index


def load_shortlist(rural: dict[str, dict]) -> list[dict]:
    if not SHORTLIST_CSV.exists():
        raise RuntimeError(f"Missing shortlist CSV: {SHORTLIST_CSV}")
    rows: list[dict] = []
    seen: set[str] = set()
    with SHORTLIST_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise RuntimeError(f"Shortlist columns changed: {reader.fieldnames}")
        for raw in reader:
            geoid = raw["geoid"].strip()
            if len(geoid) != 11 or not geoid.isdigit():
                raise RuntimeError(f"GEOID {geoid!r} is not an 11-digit tract id")
            if geoid in seen:
                raise RuntimeError(f"Duplicate shortlist GEOID {geoid}")
            seen.add(geoid)
            if raw["rural"].strip() != "Y":
                raise RuntimeError(f"{geoid} is not marked rural")
            if raw["status"].strip() != SOURCE_STATUS:
                raise RuntimeError(
                    f"{geoid} status changed. Refusing to seed a label that is not "
                    "eligible / not designated / not confirmed nominated."
                )
            tier = raw["tier"].strip()
            if tier not in {"A", "B"}:
                raise RuntimeError(f"{geoid} tier {tier!r} is not A or B")
            market = raw["market"].strip()
            if market not in {"Charleston", "Charlotte"}:
                raise RuntimeError(f"{geoid} market {market!r} is outside the SC shortlist markets")
            county = raw["county"].strip()
            place = raw["place"].strip()
            rationale = raw["mf_rationale"].strip()
            realism = raw["acreage_realism"].strip()
            notes = raw["notes"].strip()
            if not place or not rationale or not notes:
                raise RuntimeError(f"{geoid} is missing place, rationale, or notes")
            if realism not in {"High", "Med"}:
                raise RuntimeError(f"{geoid} acreage realism {realism!r} is not High or Med")
            parent = rural.get(geoid)
            if not parent:
                raise RuntimeError(f"{geoid} is not in the seven-market rural-eligible CSV")
            if parent["market"] != market or parent["county"] != county:
                raise RuntimeError(
                    f"{geoid} market/county {market}/{county} does not match "
                    f"{parent['market']}/{parent['county']}"
                )
            if parent["state"] != "South Carolina":
                raise RuntimeError(f"{geoid} is not a South Carolina tract in the rural pack")
            lat = float(raw["lat"])
            lon = float(raw["lon"])
            if abs(lat - parent["lat"]) > 1e-4 or abs(lon - parent["lon"]) > 1e-4:
                raise RuntimeError(f"{geoid} coordinates do not match the rural-eligible CSV")
            rows.append(
                {
                    "market": market,
                    "state": "South Carolina",
                    "county": county,
                    "geoid": geoid,
                    "place": place,
                    "rural": "Y",
                    "status": STATUS_CHIP,
                    "tier": tier,
                    "rank": len(rows) + 1,
                    "mfRationale": rationale,
                    "acreageRealism": realism,
                    "lat": lat,
                    "lon": lon,
                    "notes": notes,
                    "sourceStatus": SOURCE_STATUS,
                }
            )
    if not rows:
        raise RuntimeError("Shortlist CSV has no rows")
    return rows


def main() -> None:
    rows = load_shortlist(load_rural_index())
    tier_a = sum(1 for row in rows if row["tier"] == "A")
    tier_b = sum(1 for row in rows if row["tier"] == "B")
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    catalog = {
        "generatedAt": generated_at,
        "sourceCsv": "data/sc-oz2-mf-priority-shortlist.csv",
        "statusChip": STATUS_CHIP,
        "governorFiledStatus": GOVERNOR_FILED,
        "disclaimer": DISCLAIMER,
        "rowCount": len(rows),
        "tierACount": tier_a,
        "tierBCount": tier_b,
        "rows": rows,
    }
    FIXTURES.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUT_PATH.name}: {len(rows)} tracts "
        f"({tier_a} Tier A, {tier_b} Tier B), chip {STATUS_CHIP!r}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"seed_sc_mf_priority failed: {exc}", file=sys.stderr)
        sys.exit(1)
