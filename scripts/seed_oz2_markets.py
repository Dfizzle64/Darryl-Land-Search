#!/usr/bin/env python3
"""Build offline fixtures for seven Southeast rural OZ 2.0 markets.

The source of truth is data/oz2-7markets-90min-rural-eligible.csv (Rev. Proc.
2026-14 entirely-rural tracts inside approximate 90-minute county rings).
This script does not classify rural status and does not download parcel
extracts. Polygons come from Census TIGER 2020 tracts. Lat/lon in the CSV
are Census Gazetteer internal points and are kept for map pins.

Dual-listed tracts (Polk and Sumter, Florida under both Tampa and Orlando)
stay as separate catalog rows. Polygon features are unique by GEOID and
carry every market they belong to.

Usage:
  python3 scripts/seed_oz2_markets.py
  python3 scripts/seed_oz2_markets.py --offline
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "oz2-7markets-90min-rural-eligible.csv"
FIXTURES = ROOT / "data" / "fixtures"
CATALOG_PATH = FIXTURES / "oz2-rural-markets.json"
POLYS_PATH = FIXTURES / "oz2-rural-markets.geojson"

TIGER_TRACTS_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/6/query"
)

MARKETS = (
    "Atlanta",
    "Tampa",
    "Orlando",
    "Charleston",
    "Nashville",
    "Charlotte",
    "Raleigh-Durham",
)
EXPECTED_ROWS = {
    "Atlanta": 73,
    "Tampa": 66,
    "Orlando": 64,
    "Charleston": 49,
    "Nashville": 26,
    "Charlotte": 60,
    "Raleigh-Durham": 108,
}
EXPECTED_ROW_COUNT = 446
EXPECTED_UNIQUE = 424
EXPECTED_ORANGE_RURAL = "12095016605"
STATUS_CHIP = "Eligible (rural) — not designated"
SHED_CAVEAT = (
    "90-minute sheds are approximate county rings, not drive-time isochrones. "
    "Outer-edge counties are flagged in tract notes."
)
COORD_PRECISION = 5


def fetch_bytes(url: str, timeout: int = 120, retries: int = 4) -> bytes:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/oz2-markets"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1.4 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def fetch_json(url: str, params: dict, timeout: int = 120) -> dict:
    full = url + "?" + urllib.parse.urlencode(params)
    return json.loads(fetch_bytes(full, timeout=timeout).decode("utf-8"))


def round_coords(value, precision: int = COORD_PRECISION):
    if isinstance(value, (int, float)):
        return round(float(value), precision)
    if isinstance(value, list):
        return [round_coords(item, precision) for item in value]
    return value


def is_outer_edge(notes: str) -> bool:
    return "outer/uncertain edge" in notes.lower()


def is_special_use(geoid: str) -> bool:
    return len(geoid) == 11 and geoid[5:7] == "98"


def load_rows() -> list[dict]:
    if not CSV_PATH.exists():
        raise RuntimeError(f"Missing source CSV: {CSV_PATH}")
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        expected_cols = [
            "market",
            "state",
            "county",
            "geoid",
            "place_or_corridor",
            "rural",
            "status",
            "lat",
            "lon",
            "notes",
        ]
        if reader.fieldnames != expected_cols:
            raise RuntimeError(f"CSV columns changed: {reader.fieldnames}")
        rows = []
        for raw in reader:
            market = raw["market"].strip()
            if market not in MARKETS:
                raise RuntimeError(f"Unexpected market {market!r}")
            geoid = raw["geoid"].strip()
            if len(geoid) != 11 or not geoid.isdigit():
                raise RuntimeError(f"GEOID {geoid!r} is not an 11-digit tract id")
            if raw["rural"].strip() != "Y":
                raise RuntimeError(f"{geoid} is not rural; this pack is entirely rural only")
            if raw["status"].strip() != "Eligible — not designated":
                raise RuntimeError(f"{geoid} status {raw['status']!r} is not the eligible-not-designated label")
            lat = float(raw["lat"])
            lon = float(raw["lon"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise RuntimeError(f"{geoid} has invalid coordinates {lat}, {lon}")
            notes = raw["notes"].strip()
            rows.append(
                {
                    "market": market,
                    "state": raw["state"].strip(),
                    "county": raw["county"].strip(),
                    "geoid": geoid,
                    "placeOrCorridor": raw["place_or_corridor"].strip(),
                    "rural": "Y",
                    "status": STATUS_CHIP,
                    "lat": lat,
                    "lon": lon,
                    "notes": notes,
                    "outerEdge": is_outer_edge(notes),
                    "specialUse": is_special_use(geoid),
                }
            )
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["market"]] += 1
    if len(rows) != EXPECTED_ROW_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_ROW_COUNT} CSV rows, found {len(rows)}")
    for market, expected in EXPECTED_ROWS.items():
        if counts[market] != expected:
            raise RuntimeError(f"{market} expected {expected} rows, found {counts[market]}")
    unique = {row["geoid"] for row in rows}
    if len(unique) != EXPECTED_UNIQUE:
        raise RuntimeError(f"Expected {EXPECTED_UNIQUE} unique GEOIDs, found {len(unique)}")
    orange = [row for row in rows if row["geoid"] == EXPECTED_ORANGE_RURAL]
    if len(orange) != 1 or orange[0]["market"] != "Orlando" or orange[0]["county"] != "Orange":
        raise RuntimeError(f"Orange County rural tract {EXPECTED_ORANGE_RURAL} is missing from the Orlando market")
    return rows


def summarize(rows: list[dict]) -> list[dict]:
    markets = []
    for market in MARKETS:
        subset = [row for row in rows if row["market"] == market]
        lons = [row["lon"] for row in subset]
        lats = [row["lat"] for row in subset]
        counties: dict[tuple[str, str], dict] = {}
        for row in subset:
            key = (row["county"], row["state"])
            bucket = counties.setdefault(
                key,
                {"county": row["county"], "state": row["state"], "count": 0, "outerEdge": False},
            )
            bucket["count"] += 1
            bucket["outerEdge"] = bucket["outerEdge"] or row["outerEdge"]
        county_rows = sorted(counties.values(), key=lambda item: (item["state"], item["county"]))
        markets.append(
            {
                "market": market,
                "rowCount": len(subset),
                "bounds": [[min(lons), min(lats)], [max(lons), max(lats)]],
                "center": [round(sum(lons) / len(lons), 5), round(sum(lats) / len(lats), 5)],
                "counties": county_rows,
            }
        )
    return markets


def fetch_tiger_tracts(geoids: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for start in range(0, len(geoids), 20):
        batch = geoids[start : start + 20]
        quoted = ",".join(f"'{geoid}'" for geoid in batch)
        data = fetch_json(
            TIGER_TRACTS_URL,
            {
                "where": f"GEOID IN ({quoted})",
                "outFields": "GEOID,NAME,TRACT,STATE,COUNTY",
                "returnGeometry": "true",
                "outSR": "4326",
                "geometryPrecision": "5",
                "maxAllowableOffset": "0.001",
                "f": "geojson",
            },
        )
        if data.get("error"):
            raise RuntimeError(data["error"])
        features = data.get("features") or []
        print(f"TIGER batch {start // 20 + 1}: requested {len(batch)}, got {len(features)}")
        for feature in features:
            props = feature.get("properties") or {}
            geoid = str(props.get("GEOID") or "")
            geometry = feature.get("geometry") or {}
            if geoid and geometry.get("type") in {"Polygon", "MultiPolygon"}:
                found[geoid] = {
                    "name": props.get("NAME") or geoid,
                    "tract": str(props.get("TRACT") or "") or None,
                    "geometry": {
                        "type": geometry["type"],
                        "coordinates": round_coords(geometry.get("coordinates") or []),
                    },
                }
        time.sleep(0.2)
    missing = [geoid for geoid in geoids if geoid not in found]
    if missing:
        raise RuntimeError(f"Census TIGER 2020 is missing {len(missing)} tracts, including {missing[:8]}")
    return found


def load_cached_geometries() -> dict[str, dict]:
    if not POLYS_PATH.exists():
        raise RuntimeError(f"--offline needs an existing polygon fixture at {POLYS_PATH}")
    collection = json.loads(POLYS_PATH.read_text(encoding="utf-8"))
    found = {}
    for feature in collection.get("features") or []:
        props = feature.get("properties") or {}
        geoid = str(props.get("tractGeoid") or "")
        geometry = feature.get("geometry")
        if geoid and geometry:
            found[geoid] = {
                "name": props.get("name") or geoid,
                "tract": props.get("tract"),
                "geometry": geometry,
            }
    return found


def build_features(rows: list[dict], geometries: dict[str, dict]) -> list[dict]:
    by_geoid: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_geoid[row["geoid"]].append(row)
    features = []
    for geoid in sorted(by_geoid):
        group = by_geoid[geoid]
        first = group[0]
        markets = [market for market in MARKETS if any(row["market"] == market for row in group)]
        places = {row["placeOrCorridor"] for row in group}
        notes = {row["notes"] for row in group}
        counties = {(row["county"], row["state"]) for row in group}
        if len(places) != 1 or len(notes) != 1 or len(counties) != 1:
            raise RuntimeError(f"{geoid} dual-listing attributes disagree; refusing to collapse the polygon")
        geom = geometries.get(geoid)
        if not geom:
            raise RuntimeError(f"No polygon for {geoid}")
        features.append(
            {
                "type": "Feature",
                "id": geoid,
                "properties": {
                    "id": geoid,
                    "tractGeoid": geoid,
                    "tract": geom.get("tract"),
                    "name": geom.get("name") or first["placeOrCorridor"],
                    "county": first["county"],
                    "state": first["state"],
                    "rural": True,
                    "designation": "eligible-for-nomination",
                    "statusChip": STATUS_CHIP,
                    "markets": markets,
                    "placeOrCorridor": first["placeOrCorridor"],
                    "notes": first["notes"],
                    "outerEdge": first["outerEdge"],
                    "specialUse": first["specialUse"],
                    "lat": first["lat"],
                    "lon": first["lon"],
                    "source": "rev-proc-2026-14",
                },
                "geometry": geom["geometry"],
            }
        )
    return features


def main() -> None:
    offline = "--offline" in sys.argv
    rows = load_rows()
    markets = summarize(rows)
    unique = sorted({row["geoid"] for row in rows})
    geometries = load_cached_geometries() if offline else fetch_tiger_tracts(unique)
    features = build_features(rows, geometries)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    catalog = {
        "generatedAt": generated_at,
        "sourceCsv": "data/oz2-7markets-90min-rural-eligible.csv",
        "geometrySource": TIGER_TRACTS_URL.replace("/query", ""),
        "shedCaveat": SHED_CAVEAT,
        "statusChip": STATUS_CHIP,
        "rowCount": len(rows),
        "uniqueGeoidCount": len(unique),
        "parcelNote": (
            "Lake, Orange, Osceola, Polk, and Seminole include every public parcel of 5.0 acres or more from Florida DOH EHWATER "
            "(Orange zoning and FLU from OCPA and county open data). Brevard, Marion, Sumter, and Volusia remain thinner samples. "
            "Other metros stay rural-tract overlays."
        ),
        "markets": markets,
        "rows": rows,
    }
    collection = {
        "type": "FeatureCollection",
        "name": "oz2-7markets-90min-rural-eligible",
        "features": features,
    }
    FIXTURES.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    POLYS_PATH.write_text(json.dumps(collection, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {CATALOG_PATH.name} ({len(rows)} rows, {len(unique)} GEOIDs) and "
        f"{POLYS_PATH.name} ({POLYS_PATH.stat().st_size} bytes)"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"seed_oz2_markets failed: {exc}", file=sys.stderr)
        sys.exit(1)
