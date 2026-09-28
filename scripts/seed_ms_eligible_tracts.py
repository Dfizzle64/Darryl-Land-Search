#!/usr/bin/env python3
"""Build statewide Mississippi OZ 2.0 eligible tract polygons.

The eligibility list is the IRS Rev. Proc. 2026-14 appendix (State,
County, Census Tract Number, Rural Status). This script does not decide
which tracts are eligible and does not decide rural status. Mississippi
rows are state FIPS 28, keyed by the 11-digit 2020 tract GEOID.

Polygons are Census TIGER 2020 tracts (the same TIGERweb service the
market packs use), simplified the same way: 5 decimal places and about
0.001 degrees of offset. Household income is not copied onto the
features. The app joins ACS 5-year B19013 at load time, like the other
tract fixtures.

Usage:
  python3 scripts/seed_ms_eligible_tracts.py
"""

from __future__ import annotations

import io
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"
OUT = FIXTURES / "oz2-ms-statewide.geojson"
PACKS = FIXTURES / "oz2-eligible-packs.geojson"
RURAL = FIXTURES / "oz2-rural-markets.geojson"
ORANGE = FIXTURES / "oz2-eligible.geojson"
APPENDIX_URL = "https://www.irs.gov/pub/irs-drop/rp-26-14-appendix.xlsx"
TIGER_TRACTS_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/6/query"
)
CACHE = Path("/tmp/ms-tiger-2020-cache.json")
STATUS = "Eligible — not designated"
NOTE = (
    "Rev. Proc. 2026-14 appendix Rural Status: {status}. "
    "Statewide Mississippi eligible tract, not limited to a 90-minute market shed."
)
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
COORD_PRECISION = 5


def fetch_bytes(url: str, timeout: int = 120, retries: int = 4) -> bytes:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/ms-eligible-tracts"})
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


def load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for si in root.findall("m:si", NS):
        texts = [node.text or "" for node in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")]
        strings.append("".join(texts))
    return strings


def cell_text(cell: ET.Element, strings: list[str]) -> str:
    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return ""
    if cell.get("t") == "s":
        return strings[int(value.text)]
    return value.text


def county_name(raw: str) -> str:
    name = raw.strip()
    if name.lower().endswith(" county"):
        name = name[: -len(" county")].strip()
    return name


def rural_from_status(status: str) -> bool:
    token = status.strip().lower()
    if token == "rural":
        return True
    if token == "non-rural":
        return False
    raise RuntimeError(f"Unexpected Rev. Proc. 2026-14 Rural Status {status!r}; refusing to infer one")


def load_mississippi() -> dict[str, dict]:
    print(f"Downloading {APPENDIX_URL}")
    archive = zipfile.ZipFile(io.BytesIO(fetch_bytes(APPENDIX_URL)))
    strings = load_shared_strings(archive)
    sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows = sheet.findall("m:sheetData/m:row", NS)
    header = [cell_text(cell, strings).strip() for cell in rows[0].findall("m:c", NS)]
    expected = ["State", "County", "Census Tract Number", "Rural Status"]
    if header[:4] != expected:
        raise RuntimeError(f"Rev. Proc. 2026-14 appendix columns changed: {header[:4]}")

    tracts: dict[str, dict] = {}
    for row in rows[1:]:
        vals = ["", "", "", ""]
        for cell in row.findall("m:c", NS):
            ref = cell.get("r") or "A"
            idx = ord(ref[0]) - ord("A")
            if 0 <= idx < 4:
                vals[idx] = cell_text(cell, strings).strip()
        state, county, tract_raw, status = vals
        if state != "Mississippi":
            continue
        digits = "".join(ch for ch in tract_raw if ch.isdigit())
        if len(digits) == 10:
            digits = digits.zfill(11)
        if len(digits) != 11 or not digits.startswith("28"):
            raise RuntimeError(f"Mississippi tract number {tract_raw!r} is not a 2020 GEOID in state FIPS 28")
        if digits in tracts:
            raise RuntimeError(f"Rev. Proc. 2026-14 lists Mississippi GEOID {digits} more than once")
        rural = rural_from_status(status)
        tracts[digits] = {
            "tractGeoid": digits,
            "rural": rural,
            "ruralStatus": "Rural" if rural else "Non-rural",
            "state": "Mississippi",
            "county": county_name(county),
        }
    if not tracts:
        raise RuntimeError("Rev. Proc. 2026-14 appendix returned no Mississippi tracts")
    return tracts


def existing_ms_flags() -> dict[str, bool]:
    found: dict[str, bool] = {}
    for path in (RURAL, PACKS, ORANGE):
        collection = json.loads(path.read_text(encoding="utf-8"))
        for feature in collection.get("features") or []:
            props = feature.get("properties") or {}
            geoid = str(props.get("tractGeoid") or "")
            if not geoid.startswith("28"):
                continue
            rural = props.get("rural")
            if rural is not True and rural is not False:
                raise RuntimeError(f"{path.name} Mississippi tract {geoid} has no rural boolean")
            if geoid in found and found[geoid] is not rural:
                raise RuntimeError(f"{geoid} rural flag disagrees across existing fixtures")
            found[geoid] = rural
    return found


def load_cache() -> dict[str, dict]:
    if not CACHE.exists():
        return {}
    cached = json.loads(CACHE.read_text(encoding="utf-8"))
    return cached if isinstance(cached, dict) else {}


def save_cache(geometries: dict[str, dict]) -> None:
    CACHE.write_text(json.dumps(geometries), encoding="utf-8")


def fetch_tiger(geoids: list[str]) -> dict[str, dict]:
    geometries = load_cache()
    missing = [geoid for geoid in geoids if geoid not in geometries]
    print(f"TIGER: {len(geoids)} eligible, {len(geoids) - len(missing)} cached, {len(missing)} to fetch")
    for start in range(0, len(missing), 25):
        batch = missing[start : start + 25]
        quoted = ",".join(f"'{geoid}'" for geoid in batch)
        data = fetch_json(
            TIGER_TRACTS_URL,
            {
                "where": f"GEOID IN ({quoted})",
                "outFields": "GEOID,NAME,TRACT,INTPTLAT,INTPTLON",
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
                    "name": props.get("NAME") or None,
                    "tract": str(props.get("TRACT") or "") or None,
                    "lat": props.get("INTPTLAT"),
                    "lon": props.get("INTPTLON"),
                    "geometry": {
                        "type": geometry["type"],
                        "coordinates": round_coords(geometry.get("coordinates") or []),
                    },
                }
        if (start // 25) % 4 == 3:
            save_cache(geometries)
        time.sleep(0.15)
    save_cache(geometries)
    return geometries


def parse_internal_point(raw) -> float | None:
    if raw is None:
        return None
    try:
        value = float(str(raw).strip())
    except ValueError:
        return None
    return value


def build_features(tracts: dict[str, dict], geometries: dict[str, dict]) -> tuple[list[dict], list[str]]:
    features = []
    unmatched = []
    for geoid in sorted(tracts):
        row = tracts[geoid]
        geom = geometries.get(geoid)
        if not geom or not geom.get("geometry"):
            unmatched.append(geoid)
            continue
        lat = parse_internal_point(geom.get("lat"))
        lon = parse_internal_point(geom.get("lon"))
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            unmatched.append(geoid)
            continue
        name = geom.get("name") or f"Census tract {geoid}"
        features.append(
            {
                "type": "Feature",
                "id": geoid,
                "properties": {
                    "id": geoid,
                    "tractGeoid": geoid,
                    "tract": geom.get("tract"),
                    "name": name,
                    "county": row["county"],
                    "state": "Mississippi",
                    "rural": row["rural"],
                    "designation": "eligible-for-nomination",
                    "statusChip": STATUS,
                    "markets": [],
                    "packs": [],
                    "placeOrCorridor": name,
                    "notes": NOTE.format(status=row["ruralStatus"]),
                    "outerEdge": False,
                    "specialUse": len(geoid) == 11 and geoid[5:7] == "98",
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "source": "rev-proc-2026-14",
                },
                "geometry": geom["geometry"],
            }
        )
    return features, unmatched


def main() -> None:
    tracts = load_mississippi()
    existing = existing_ms_flags()
    mismatches = [
        geoid
        for geoid, rural in existing.items()
        if geoid not in tracts or tracts[geoid]["rural"] is not rural
    ]
    if mismatches:
        raise RuntimeError(
            "Existing Mississippi map tracts disagree with Rev. Proc. 2026-14, "
            f"including {mismatches[:8]}"
        )
    missing_from_appendix = [geoid for geoid in existing if geoid not in tracts]
    if missing_from_appendix:
        raise RuntimeError(f"Map tracts missing from the appendix: {missing_from_appendix[:8]}")

    geometries = fetch_tiger(sorted(tracts))
    features, unmatched = build_features(tracts, geometries)
    rural_count = sum(1 for feature in features if feature["properties"]["rural"] is True)
    nonrural_count = sum(1 for feature in features if feature["properties"]["rural"] is False)
    counties: dict[str, dict[str, int]] = {}
    for feature in features:
        props = feature["properties"]
        bucket = counties.setdefault(props["county"], {"rural": 0, "nonrural": 0})
        bucket["rural" if props["rural"] else "nonrural"] += 1
    rural_counties = sum(1 for bucket in counties.values() if bucket["rural"] > 0)
    collection = {
        "type": "FeatureCollection",
        "name": "oz2-ms-statewide",
        "source": APPENDIX_URL,
        "geometrySource": TIGER_TRACTS_URL.replace("/query", ""),
        "unmatchedGeoids": unmatched,
        "features": features,
    }
    OUT.write_text(json.dumps(collection, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {OUT.name}: features={len(features)} rural={rural_count} "
        f"nonrural={nonrural_count} counties={len(counties)} rural_counties={rural_counties} "
        f"already_on_map={len(existing)} unmatched={len(unmatched)} bytes={OUT.stat().st_size}"
    )
    if unmatched:
        print("Unmatched GEOIDs (no 2020 TIGER shape or internal point):")
        for geoid in unmatched:
            row = tracts[geoid]
            print(f"  {geoid} {row['county']} {row['ruralStatus']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
