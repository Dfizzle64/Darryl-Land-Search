#!/usr/bin/env python3
"""ACS 5-year 2020–2024 tract median household income for live parcel markets.

One B19013 layer covers every state that already has a parcel extract:
Alabama, Arkansas, Florida, Georgia, Mississippi, North Carolina, South
Carolina, and Tennessee. The estimate is B19013_001E (2024
inflation-adjusted dollars) and the margin of error is B19013_001M.

Preferred pull, when CENSUS_API_KEY is set:

  https://api.census.gov/data/2024/acs/acs5
    ?get=NAME,B19013_001E,B19013_001M&for=tract:*&in=state:XX&in=county:*

This environment has no key (api.census.gov returns Missing Key). The same
published cells are read from the Census Bureau table-based summary file
acsdt5y2024-b19013.dat (B19013_E001 / B19013_M001). County, ZIP, and CHAS
tables are not substitutes.

  python3 scripts/seed_se_acs_income.py

Writes:
  data/fixtures/acs-b19013-tracts.json   every tract in the seven states
  data/fixtures/income-tracts.geojson    2024 TIGER tract polygons for counties
                                         that have a parcel extract (centroid fallback)

Parcel tiles are not updated. Query time prefers an 11-digit 2020 tract GEOID
and uses centroid-in-tract only when the parcel has no GEOID.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import shapefile

from parcel_geometry import esri_rings_to_geojson

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "data" / "fixtures"
TABLE_OUT = FIX / "acs-b19013-tracts.json"
INCOME_OUT = FIX / "income-tracts.geojson"
META_OUT = FIX / "signals-meta.json"
CACHE = Path("/tmp/acs-b19013")

VINTAGE = "acs5_2020_2024"
API = "https://api.census.gov/data/2024/acs/acs5"
SUMMARY_URL = (
    "https://www2.census.gov/programs-surveys/acs/summary_file/2024/"
    "table-based-SF/data/5YRData/acsdt5y2024-b19013.dat"
)
COUNTY_URL = "https://www2.census.gov/geo/docs/reference/codes2020/national_county2020.txt"
# ~9 m. Tight enough for a 5-acre centroid, loose enough to keep the sidecar small.
POLYGON_TOL = 0.00008

# States with a live parcel extract on main. Not a new metro shelf.
SE_STATES = {
    "01": "Alabama",
    "05": "Arkansas",
    "12": "Florida",
    "13": "Georgia",
    "28": "Mississippi",
    "37": "North Carolina",
    "45": "South Carolina",
    "47": "Tennessee",
}

# Census nulls and suppression codes. A non-positive median is not a dollar income.
SENTINELS = {
    None,
    "",
    "-666666666",
    "-999999999",
    "-222222222",
    "-333333333",
    "-555555555",
    "null",
    "NULL",
}


def fetch_bytes(url: str, dest: Path, timeout: int = 180) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  cached {dest.name} ({dest.stat().st_size} bytes)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/se-acs"})
    print(f"  GET {url}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dest.write_bytes(resp.read())
    print(f"  wrote {dest.name} ({dest.stat().st_size} bytes)")


def parse_number(raw: str | None) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if text in SENTINELS:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if not (value > 0) or value >= 1_000_000_000:
        return None
    return value


def parse_moe(raw: str | None, estimate: float | None) -> float | None:
    if estimate is None:
        return None
    if raw is None:
        return None
    text = str(raw).strip()
    if text in SENTINELS:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if value < 0 or value >= 1_000_000_000:
        return None
    return value


def parcel_county_fips() -> list[str]:
    found: set[str] = set()
    orlando = json.loads((FIX / "orlando-parcels" / "meta.json").read_text())
    for county in orlando.get("counties") or []:
        fips = str(county.get("fips") or "")
        if fips[:2] in SE_STATES:
            found.add(fips.zfill(5))
    index = json.loads((FIX / "market-parcels" / "index.json").read_text())
    for summary in (index.get("markets") or {}).values():
        for county in summary.get("counties") or []:
            fips = str(county.get("fips") or "")
            if fips[:2] not in SE_STATES:
                continue
            count = county.get("featureCount")
            if count == 0:
                continue
            found.add(fips.zfill(5))
    return sorted(found)


def load_county_names() -> dict[str, str]:
    dest = CACHE / "national_county2020.txt"
    fetch_bytes(COUNTY_URL, dest, timeout=60)
    names: dict[str, str] = {}
    lines = dest.read_text(encoding="latin-1").splitlines()
    header = [cell.strip().upper() for cell in lines[0].split("|")] if lines else []
    for line in lines[1:]:
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 3:
            continue
        row = dict(zip(header, cells)) if header and "STATEFP" in header else {}
        if row:
            state = row.get("STATEFP", "")
            county = row.get("COUNTYFP", "")
            name = row.get("COUNTYNAME") or row.get("COUNTY_NAME") or ""
        else:
            # STATE|STATEFP|COUNTYFP|COUNTYNS|COUNTYNAME|CLASSFP
            state = cells[1] if len(cells) > 2 else ""
            county = cells[2] if len(cells) > 3 else ""
            name = cells[4] if len(cells) > 4 else ""
        if state in SE_STATES and county and name:
            names[f"{state}{county}"] = name
    if len(names) < 100:
        raise RuntimeError(f"County name file produced only {len(names)} Southeast rows")
    return names


def rows_from_api(key: str) -> tuple[dict[str, dict], str]:
    table: dict[str, dict] = {}
    for state in SE_STATES:
        query = urllib.parse.urlencode(
            [
                ("get", "NAME,B19013_001E,B19013_001M"),
                ("for", "tract:*"),
                ("in", f"state:{state}"),
                ("in", "county:*"),
                ("key", key),
            ]
        )
        url = f"{API}?{query}"
        req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/se-acs"})
        print(f"  API state {state}")
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        header, *body = payload
        name_i = header.index("NAME")
        est_i = header.index("B19013_001E")
        moe_i = header.index("B19013_001M")
        state_i = header.index("state")
        county_i = header.index("county")
        tract_i = header.index("tract")
        for row in body:
            geoid = f"{row[state_i]}{row[county_i]}{row[tract_i]}"
            if len(geoid) != 11:
                continue
            estimate = parse_number(row[est_i])
            table[geoid] = {
                "e": estimate,
                "m": parse_moe(row[moe_i], estimate),
                "n": row[name_i] or None,
            }
        time.sleep(0.2)
    return table, API


def rows_from_summary() -> tuple[dict[str, dict], str]:
    dest = CACHE / "acsdt5y2024-b19013.dat"
    fetch_bytes(SUMMARY_URL, dest, timeout=180)
    table: dict[str, dict] = {}
    with dest.open(encoding="utf-8", errors="replace") as handle:
        header = handle.readline().strip().split("|")
        columns = {name: index for index, name in enumerate(header)}
        geo_i = columns.get("GEO_ID")
        est_i = columns.get("B19013_E001", columns.get("B19013_001E"))
        moe_i = columns.get("B19013_M001", columns.get("B19013_001M"))
        if geo_i is None or est_i is None or moe_i is None:
            raise RuntimeError(f"Unexpected B19013 header: {header[:8]}")
        for line in handle:
            cells = line.rstrip("\n").split("|")
            if len(cells) <= max(geo_i, est_i, moe_i):
                continue
            geo = cells[geo_i]
            if not geo.startswith("1400000US"):
                continue
            geoid = geo[9:]
            if len(geoid) != 11 or geoid[:2] not in SE_STATES:
                continue
            estimate = parse_number(cells[est_i])
            table[geoid] = {
                "e": estimate,
                "m": parse_moe(cells[moe_i], estimate),
                "n": None,
            }
    return table, SUMMARY_URL


def load_estimates() -> tuple[dict[str, dict], str]:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if key:
        print("Census API 2024 ACS5")
        return rows_from_api(key)
    print("No CENSUS_API_KEY; reading the official 2024 ACS 5-year summary file")
    return rows_from_summary()


def shape_rings(shp: shapefile.Shape) -> list[list[tuple[float, float]]]:
    points = shp.points
    parts = list(shp.parts) + [len(points)]
    rings = []
    for start, end in zip(parts, parts[1:]):
        ring = points[start:end]
        if len(ring) >= 4:
            rings.append(ring)
    return rings


def attach_tiger_names_and_polygons(
    table: dict[str, dict],
    counties: set[str],
    county_names: dict[str, str],
) -> list[dict]:
    features: list[dict] = []
    for state, state_name in SE_STATES.items():
        zip_path = CACHE / f"tl_2024_{state}_tract.zip"
        fetch_bytes(
            f"https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_{state}_tract.zip",
            zip_path,
            timeout=180,
        )
        extract = CACHE / f"tl_2024_{state}_tract"
        if not (extract / f"tl_2024_{state}_tract.shp").exists():
            extract.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract)
        reader = shapefile.Reader(str(extract / f"tl_2024_{state}_tract.shp"))
        field_names = [field[0] for field in reader.fields[1:]]
        geoid_i = field_names.index("GEOID") if "GEOID" in field_names else field_names.index("GEOID20")
        name_i = field_names.index("NAMELSAD") if "NAMELSAD" in field_names else None
        kept = 0
        for rec, shp in zip(reader.records(), reader.shapes()):
            geoid = str(rec[geoid_i])
            if len(geoid) != 11 or geoid[:2] != state:
                continue
            namelsad = str(rec[name_i]) if name_i is not None else f"Census Tract {geoid[5:]}"
            county = county_names.get(geoid[:5])
            label = f"{namelsad}, {county} County, {state_name}" if county else f"{namelsad}, {state_name}"
            row = table.get(geoid)
            if row is None:
                row = {"e": None, "m": None, "n": label}
                table[geoid] = row
            elif not row.get("n"):
                row["n"] = label
            if geoid[:5] not in counties:
                continue
            geometry = esri_rings_to_geojson(shape_rings(shp), POLYGON_TOL)
            if not geometry:
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "geoid": geoid,
                        "name": row.get("n"),
                        "medianHouseholdIncome": row.get("e"),
                        "medianHouseholdIncomeMoe": row.get("m"),
                        "vintage": VINTAGE,
                        "table": "B19013",
                        "estimate": "B19013_001E",
                    },
                }
            )
            kept += 1
        reader.close()
        print(f"  {state_name} parcel-county tracts {kept}")
    return features


def write_meta(table: dict[str, dict], features: list[dict], counties: list[str], source: str) -> None:
    meta = json.loads(META_OUT.read_text()) if META_OUT.exists() else {}
    known = sum(1 for row in table.values() if row.get("e") is not None)
    meta.update(
        {
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "incomeSource": source,
            "incomeApi": f"{API}?get=NAME,B19013_001E,B19013_001M&for=tract:*&in=state:XX&in=county:*",
            "incomeTable": "B19013",
            "incomeEstimate": "B19013_001E",
            "incomeMoe": "B19013_001M",
            "incomeVintage": VINTAGE,
            "incomeDollars": "2024 inflation-adjusted",
            "incomeStates": sorted(SE_STATES),
            "incomeCounties": counties,
            "incomeTractCount": len(table),
            "incomeKnownCount": known,
            "incomePolygonCount": len(features),
        }
    )
    notes = [
        "Tract median household income is ACS 5-year 2020–2024 B19013_001E (2024 inflation-adjusted dollars) for every state with a live parcel extract (AL, AR, FL, GA, MS, NC, SC, TN).",
        "Join prefers the parcel's 11-digit 2020 tract GEOID. Centroid-in-tract is only the fallback when that GEOID is missing.",
        "BEA county income, IRS SOI ZIP income, and HUD CHAS are not the tract household-income field.",
        "Income and AADT are not stored on parcel tiles.",
        "A parcel more than 15 km from the nearest FDOT segment stays unknown. AADT stays FDOT (Florida).",
        "Block-group income remains the Orange County pilot fixture.",
    ]
    if source == SUMMARY_URL:
        notes.insert(
            1,
            "This build read the Census table-based summary file because CENSUS_API_KEY was unset. B19013_E001 is the same cell as B19013_001E.",
        )
    meta["notes"] = notes
    META_OUT.write_text(json.dumps(meta, indent=2) + "\n")


def seed_income() -> None:
    counties = parcel_county_fips()
    if "12095" not in counties:
        raise RuntimeError("Orange County FIPS missing from parcel fixtures")
    print(f"Parcel counties in the seven states: {len(counties)}")
    county_names = load_county_names()
    table, source = load_estimates()
    if not any(geoid.startswith("12095") for geoid in table):
        raise RuntimeError("Orange County tracts missing from ACS 2024 B19013")
    for state in SE_STATES:
        if not any(geoid.startswith(state) for geoid in table):
            raise RuntimeError(f"No ACS tracts for state {state}")
    features = attach_tiger_names_and_polygons(table, set(counties), county_names)
    polygon_geoids = {feature["properties"]["geoid"] for feature in features}
    missing = [fips for fips in counties if not any(geoid.startswith(fips) for geoid in polygon_geoids)]
    if missing:
        raise RuntimeError(f"No tract polygons for parcel counties {missing[:12]}")
    known = sum(1 for row in table.values() if row.get("e") is not None)
    TABLE_OUT.write_text(
        json.dumps(
            {
                "vintage": VINTAGE,
                "table": "B19013",
                "estimate": "B19013_001E",
                "moe": "B19013_001M",
                "dollars": "2024 inflation-adjusted",
                "source": source,
                "api": f"{API}?get=NAME,B19013_001E,B19013_001M&for=tract:*&in=state:XX&in=county:*",
                "states": sorted(SE_STATES),
                "tracts": table,
            },
            separators=(",", ":"),
        )
    )
    INCOME_OUT.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "name": "se-acs5-2020-2024-b19013",
                "vintage": VINTAGE,
                "features": features,
            },
            separators=(",", ":"),
        )
    )
    write_meta(table, features, counties, source)
    print(
        f"tracts {len(table)} with a median {known}; "
        f"polygons {len(features)}; table {TABLE_OUT.stat().st_size} bytes; "
        f"geojson {INCOME_OUT.stat().st_size} bytes"
    )


if __name__ == "__main__":
    seed_income()
