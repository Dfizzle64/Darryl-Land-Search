#!/usr/bin/env python3
"""Build offline fixtures for OZ 2.0 urban (7 markets) and other-MSA packs.

Sources (Rev. Proc. 2026-14, approximate 90-minute county rings):

  data/oz2-7markets-90min-urban-eligible.csv   — non-rural eligible, primary 7
  data/oz2-other-msas-eligible.csv             — rural + non-rural, 15 smaller MSAs
  data/oz2-other-msas-rural-eligible.csv       — rural split (checked, not the join source)
  data/oz2-other-msas-urban-eligible.csv       — urban split (checked, not the join source)

Polygons come from Census TIGER 2020 tracts. Gazetteer lat/lon in the CSVs
are kept for pins. Dual-listed tracts stay as separate catalog rows. Polygon
features are unique by GEOID and carry every market they belong to.

Status is stored as the CSV label "Eligible — not designated". This script
does not mark any tract nominated or designated.

Usage:
  python3 scripts/seed_oz2_eligible_packs.py
  python3 scripts/seed_oz2_eligible_packs.py --offline
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
DATA = ROOT / "data"
FIXTURES = DATA / "fixtures"
URBAN_CSV = DATA / "oz2-7markets-90min-urban-eligible.csv"
OTHER_CSV = DATA / "oz2-other-msas-eligible.csv"
OTHER_RURAL_CSV = DATA / "oz2-other-msas-rural-eligible.csv"
OTHER_URBAN_CSV = DATA / "oz2-other-msas-urban-eligible.csv"
RURAL7_POLYS = FIXTURES / "oz2-rural-markets.geojson"
ORANGE_POLYS = FIXTURES / "oz2-eligible.geojson"
CACHE_PATH = FIXTURES / "tiger-tract-cache.json"
URBAN_CATALOG = FIXTURES / "oz2-urban-markets.json"
OTHER_CATALOG = FIXTURES / "oz2-other-msas.json"
POLYS_PATH = FIXTURES / "oz2-eligible-packs.geojson"

TIGER_TRACTS_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/6/query"
)

PRIMARY_MARKETS = (
    "Atlanta",
    "Tampa",
    "Orlando",
    "Charleston",
    "Nashville",
    "Charlotte",
    "Raleigh-Durham",
)
OTHER_MARKETS = (
    "Vero Beach",
    "Melbourne",
    "Jacksonville",
    "Pensacola",
    "Birmingham",
    "Mobile",
    "Huntsville",
    "Savannah",
    "Columbia",
    "Greenville",
    "Chattanooga",
    "Knoxville",
    "Memphis",
    "Winston-Salem",
    "Wilmington",
)

URBAN_EXPECTED = {
    "Atlanta": 342,
    "Tampa": 251,
    "Orlando": 216,
    "Charleston": 30,
    "Nashville": 82,
    "Charlotte": 144,
    "Raleigh-Durham": 79,
}
OTHER_EXPECTED = {
    "Vero Beach": (62, 25, 37),
    "Melbourne": (175, 24, 151),
    "Jacksonville": (98, 8, 90),
    "Pensacola": (49, 22, 27),
    "Birmingham": (152, 42, 110),
    "Mobile": (66, 15, 51),
    "Huntsville": (58, 31, 27),
    "Savannah": (64, 31, 33),
    "Columbia": (105, 62, 43),
    "Greenville": (105, 70, 35),
    "Chattanooga": (47, 21, 26),
    "Knoxville": (70, 41, 29),
    "Memphis": (175, 44, 131),
    "Winston-Salem": (105, 24, 81),
    "Wilmington": (55, 31, 24),
}

STATUS = "Eligible — not designated"
SHED_CAVEAT = (
    "90-minute sheds are approximate county rings, not drive-time isochrones. "
    "Outer-edge counties are flagged in tract notes."
)
COLUMNS = [
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
COORD_PRECISION = 5


def fetch_bytes(url: str, timeout: int = 120, retries: int = 4) -> bytes:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/oz2-eligible-packs"})
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


def load_csv(path: Path, allowed_markets: tuple[str, ...], allowed_rural: set[str]) -> list[dict]:
    if not path.exists():
        raise RuntimeError(f"Missing source CSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS:
            raise RuntimeError(f"{path.name} columns changed: {reader.fieldnames}")
        rows = []
        for raw in reader:
            market = raw["market"].strip()
            if market not in allowed_markets:
                raise RuntimeError(f"{path.name} unexpected market {market!r}")
            geoid = raw["geoid"].strip()
            if len(geoid) != 11 or not geoid.isdigit():
                raise RuntimeError(f"{geoid!r} is not an 11-digit tract id")
            rural = raw["rural"].strip()
            if rural not in allowed_rural:
                raise RuntimeError(f"{geoid} rural flag {rural!r} is not allowed in {path.name}")
            status = raw["status"].strip()
            if status != STATUS:
                raise RuntimeError(f"{geoid} status {status!r} is not {STATUS!r}")
            if "designated" in status.lower() and "not designated" not in status.lower():
                raise RuntimeError(f"{geoid} was marked designated")
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
                    "rural": rural,
                    "status": STATUS,
                    "lat": lat,
                    "lon": lon,
                    "notes": notes,
                    "outerEdge": is_outer_edge(notes),
                    "specialUse": is_special_use(geoid),
                    "governorFiled": "governor-filed" in notes.lower(),
                }
            )
    return rows


def assert_counts(rows: list[dict], expected: dict[str, int], label: str, unique: int) -> None:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["market"]] += 1
    if sum(expected.values()) != len(rows):
        raise RuntimeError(f"{label}: expected {sum(expected.values())} rows, found {len(rows)}")
    for market, count in expected.items():
        if counts[market] != count:
            raise RuntimeError(f"{label}: {market} expected {count} rows, found {counts[market]}")
    found_unique = len({row["geoid"] for row in rows})
    if found_unique != unique:
        raise RuntimeError(f"{label}: expected {unique} unique GEOIDs, found {found_unique}")


def assert_other_splits(rows: list[dict]) -> None:
    for market, (total, rural, urban) in OTHER_EXPECTED.items():
        subset = [row for row in rows if row["market"] == market]
        rural_n = sum(1 for row in subset if row["rural"] == "Y")
        urban_n = sum(1 for row in subset if row["rural"] == "N")
        if len(subset) != total or rural_n != rural or urban_n != urban:
            raise RuntimeError(
                f"{market}: expected {total} ({rural} rural / {urban} urban), "
                f"found {len(subset)} ({rural_n} rural / {urban_n} urban)"
            )
    if not OTHER_RURAL_CSV.exists() or not OTHER_URBAN_CSV.exists():
        raise RuntimeError("Other-MSA rural/urban split CSVs are missing")
    rural_rows = load_csv(OTHER_RURAL_CSV, OTHER_MARKETS, {"Y"})
    urban_rows = load_csv(OTHER_URBAN_CSV, OTHER_MARKETS, {"N"})
    if len(rural_rows) != 491 or len(urban_rows) != 895:
        raise RuntimeError(f"Split sizes drifted: rural {len(rural_rows)} urban {len(urban_rows)}")
    rural_keys = {(row["market"], row["geoid"]) for row in rural_rows}
    urban_keys = {(row["market"], row["geoid"]) for row in urban_rows}
    main_rural = {(row["market"], row["geoid"]) for row in rows if row["rural"] == "Y"}
    main_urban = {(row["market"], row["geoid"]) for row in rows if row["rural"] == "N"}
    if rural_keys != main_rural or urban_keys != main_urban:
        raise RuntimeError("Other-MSA split CSVs do not match the combined eligible file")


def assert_sc_notes(rows: list[dict], label: str) -> None:
    sc = [row for row in rows if row["state"] == "South Carolina"]
    if not sc:
        raise RuntimeError(f"{label} has no South Carolina rows")
    missing = [row["geoid"] for row in sc if not row["governorFiled"]]
    if missing:
        raise RuntimeError(f"{label} South Carolina rows missing governor-filed notes, including {missing[:5]}")
    for row in sc:
        if row["status"] != STATUS:
            raise RuntimeError(f"{row['geoid']} South Carolina status was rewritten")


def summarize(rows: list[dict], markets: tuple[str, ...]) -> list[dict]:
    summaries = []
    for market in markets:
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
        summaries.append(
            {
                "market": market,
                "rowCount": len(subset),
                "ruralCount": sum(1 for row in subset if row["rural"] == "Y"),
                "urbanCount": sum(1 for row in subset if row["rural"] == "N"),
                "bounds": [[min(lons), min(lats)], [max(lons), max(lats)]],
                "center": [round(sum(lons) / len(lons), 5), round(sum(lats) / len(lats), 5)],
                "counties": sorted(counties.values(), key=lambda item: (item["state"], item["county"])),
            }
        )
    return summaries


def harvest_geometries(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    collection = json.loads(path.read_text(encoding="utf-8"))
    found = {}
    for feature in collection.get("features") or []:
        props = feature.get("properties") or {}
        geoid = str(props.get("tractGeoid") or props.get("GEOID") or "")
        geometry = feature.get("geometry")
        if geoid and geometry and geometry.get("type") in {"Polygon", "MultiPolygon"}:
            found[geoid] = {
                "name": props.get("name") or geoid,
                "tract": props.get("tract"),
                "geometry": geometry,
            }
    return found


def load_cache() -> dict[str, dict]:
    found = {}
    found.update(harvest_geometries(RURAL7_POLYS))
    found.update(harvest_geometries(ORANGE_POLYS))
    found.update(harvest_geometries(POLYS_PATH))
    if CACHE_PATH.exists():
        cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if isinstance(cached, dict):
            found.update(cached)
    return found


def save_cache(geometries: dict[str, dict]) -> None:
    CACHE_PATH.write_text(json.dumps(geometries), encoding="utf-8")


def fetch_tiger_tracts(geoids: list[str], geometries: dict[str, dict]) -> dict[str, dict]:
    missing = [geoid for geoid in geoids if geoid not in geometries]
    print(f"TIGER: {len(geoids)} unique, {len(geoids) - len(missing)} cached, {len(missing)} to fetch")
    for start in range(0, len(missing), 25):
        batch = missing[start : start + 25]
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
        print(f"TIGER batch {start // 25 + 1}: requested {len(batch)}, got {len(features)}")
        for feature in features:
            props = feature.get("properties") or {}
            geoid = str(props.get("GEOID") or "")
            geometry = feature.get("geometry") or {}
            if geoid and geometry.get("type") in {"Polygon", "MultiPolygon"}:
                geometries[geoid] = {
                    "name": props.get("NAME") or geoid,
                    "tract": str(props.get("TRACT") or "") or None,
                    "geometry": {
                        "type": geometry["type"],
                        "coordinates": round_coords(geometry.get("coordinates") or []),
                    },
                }
        if (start // 25) % 8 == 7:
            save_cache(geometries)
        time.sleep(0.15)
    still_missing = [geoid for geoid in geoids if geoid not in geometries]
    if still_missing:
        raise RuntimeError(f"Census TIGER 2020 is missing {len(still_missing)} tracts, including {still_missing[:8]}")
    save_cache(geometries)
    return geometries


def build_features(groups: list[tuple[str, list[dict]]], geometries: dict[str, dict]) -> list[dict]:
    by_geoid: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for pack, rows in groups:
        for row in rows:
            by_geoid[row["geoid"]].append((pack, row))
    features = []
    for geoid in sorted(by_geoid):
        group = by_geoid[geoid]
        counties = {(row["county"], row["state"]) for _, row in group}
        rural_flags = {row["rural"] for _, row in group}
        if len(counties) != 1 or len(rural_flags) != 1:
            raise RuntimeError(f"{geoid} listings disagree on county or rural flag")
        first = group[0][1]
        market_order = list(PRIMARY_MARKETS) + list(OTHER_MARKETS)
        markets = [market for market in market_order if any(row["market"] == market for _, row in group)]
        packs = []
        for pack, _row in group:
            if pack not in packs:
                packs.append(pack)
        geom = geometries.get(geoid)
        if not geom:
            raise RuntimeError(f"No polygon for {geoid}")
        # Notes can differ when one market flags an outer edge and another does not.
        # The catalog row keeps the market-specific note. The polygon keeps one note
        # for the feature; the drawer reads the catalog.
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
                    "rural": first["rural"] == "Y",
                    "designation": "eligible-for-nomination",
                    "statusChip": STATUS,
                    "markets": markets,
                    "packs": packs,
                    "placeOrCorridor": first["placeOrCorridor"],
                    "notes": first["notes"],
                    "outerEdge": any(row["outerEdge"] for _, row in group),
                    "specialUse": first["specialUse"],
                    "lat": first["lat"],
                    "lon": first["lon"],
                    "source": "rev-proc-2026-14",
                },
                "geometry": geom["geometry"],
            }
        )
    return features


def catalog_payload(rows: list[dict], markets: tuple[str, ...], source_csv: str, pack: str) -> dict:
    unique = {row["geoid"] for row in rows}
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    public_rows = []
    for row in rows:
        public = {key: value for key, value in row.items() if key != "governorFiled"}
        public_rows.append(public)
    return {
        "generatedAt": generated_at,
        "sourceCsv": source_csv,
        "geometrySource": TIGER_TRACTS_URL.replace("/query", ""),
        "shedCaveat": SHED_CAVEAT,
        "statusChip": STATUS,
        "pack": pack,
        "rowCount": len(rows),
        "uniqueGeoidCount": len(unique),
        "ruralRowCount": sum(1 for row in rows if row["rural"] == "Y"),
        "urbanRowCount": sum(1 for row in rows if row["rural"] == "N"),
        "markets": summarize(rows, markets),
        "rows": public_rows,
    }


def main() -> None:
    offline = "--offline" in sys.argv
    urban_rows = load_csv(URBAN_CSV, PRIMARY_MARKETS, {"N"})
    other_rows = load_csv(OTHER_CSV, OTHER_MARKETS, {"Y", "N"})
    assert_counts(urban_rows, URBAN_EXPECTED, "urban-7", 1103)
    assert_counts(other_rows, {market: total for market, (total, _r, _u) in OTHER_EXPECTED.items()}, "other-msas", 1341)
    assert_other_splits(other_rows)
    assert_sc_notes(urban_rows, "urban-7")
    assert_sc_notes(other_rows, "other-msas")
    if any(row["rural"] != "N" for row in urban_rows):
        raise RuntimeError("Urban pack includes a rural row")
    overlap = {row["geoid"] for row in urban_rows} & {row["geoid"] for row in other_rows}
    if len(overlap) != 159:
        raise RuntimeError(f"Expected 159 GEOIDs shared by the urban-7 and other-MSA packs, found {len(overlap)}")

    geometries = load_cache()
    unique = sorted({row["geoid"] for row in urban_rows} | {row["geoid"] for row in other_rows})
    if len(unique) != 2285:
        raise RuntimeError(f"Expected 2285 combined unique GEOIDs, found {len(unique)}")
    if offline:
        missing = [geoid for geoid in unique if geoid not in geometries]
        if missing:
            raise RuntimeError(f"--offline is missing {len(missing)} polygons, including {missing[:8]}")
    else:
        geometries = fetch_tiger_tracts(unique, geometries)

    features = build_features([("urban-7", urban_rows), ("other-msas", other_rows)], geometries)
    if len(features) != 2285:
        raise RuntimeError(f"Expected 2285 polygons, built {len(features)}")
    urban_catalog = catalog_payload(urban_rows, PRIMARY_MARKETS, "data/oz2-7markets-90min-urban-eligible.csv", "urban-7")
    other_catalog = catalog_payload(other_rows, OTHER_MARKETS, "data/oz2-other-msas-eligible.csv", "other-msas")
    collection = {
        "type": "FeatureCollection",
        "name": "oz2-eligible-packs",
        "features": features,
    }
    FIXTURES.mkdir(parents=True, exist_ok=True)
    URBAN_CATALOG.write_text(json.dumps(urban_catalog, indent=2) + "\n", encoding="utf-8")
    OTHER_CATALOG.write_text(json.dumps(other_catalog, indent=2) + "\n", encoding="utf-8")
    POLYS_PATH.write_text(json.dumps(collection, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {URBAN_CATALOG.name} ({urban_catalog['rowCount']} rows, {urban_catalog['uniqueGeoidCount']} GEOIDs), "
        f"{OTHER_CATALOG.name} ({other_catalog['rowCount']} rows, {other_catalog['ruralRowCount']} rural / "
        f"{other_catalog['urbanRowCount']} urban, {other_catalog['uniqueGeoidCount']} GEOIDs), "
        f"{POLYS_PATH.name} ({len(features)} polygons, {POLYS_PATH.stat().st_size} bytes)"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"seed_oz2_eligible_packs failed: {exc}", file=sys.stderr)
        sys.exit(1)
