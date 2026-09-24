#!/usr/bin/env python3
"""Sidecar ACS income and FDOT AADT for Florida parcel counties.

Parcel tiles do not store these fields. Copying a tract median onto every
parcel in that tract would bloat the extracts without adding a new fact.
`/api/parcels` joins this sidecar at query time.

  python3 scripts/seed_fl_signals.py

Income is Census Reporter ACS 5-year B19013 for every Florida county that
already has a parcel extract. AADT is the public FDOT historical count layer
for 2025 (all segments). The map overlay stays the 15,000+ subset.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from parcel_geometry import douglas_peucker

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "data" / "fixtures"
INCOME_OUT = FIX / "income-tracts.geojson"
SEGMENTS_OUT = FIX / "aadt-segments.geojson"
TRAFFIC_OUT = FIX / "traffic.geojson"
META_OUT = FIX / "signals-meta.json"

REPORTER_DATA = "https://api.censusreporter.org/1.0/data/show/latest"
REPORTER_GEO = "https://api.censusreporter.org/1.0/geo/show/tiger2023"
FDOT_QUERY = (
    "https://services1.arcgis.com/O1JpcwDW8sjYuddV/arcgis/rest/services/"
    "Annual_Average_Daily_Traffic_Historical_TDA/FeatureServer/0/query"
)
AADT_YEAR = 2025
MAJOR_AADT = 15000


def fetch_json(url: str, params: dict | None = None, timeout: int = 120, retries: int = 4) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/fl-signals"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:160]}: {last}")


def geoid_from_reporter(full_id: str) -> str:
    if "US" in full_id:
        return full_id.split("US", 1)[1]
    return full_id


def florida_parcel_fips() -> list[str]:
    found: set[str] = set()
    orlando = json.loads((FIX / "orlando-parcels" / "meta.json").read_text())
    for county in orlando.get("counties") or []:
        fips = str(county.get("fips") or "")
        if fips.startswith("12"):
            found.add(fips)
    index = json.loads((FIX / "market-parcels" / "index.json").read_text())
    for summary in (index.get("markets") or {}).values():
        for county in summary.get("counties") or []:
            if county.get("state") == "Florida" and county.get("fips"):
                found.add(str(county["fips"]))
    return sorted(found)


def income_county_fips() -> list[str]:
    """Florida parcel counties, plus Atlanta and Charleston.

    Those two markets use the same query-time tract join as Orlando. A reseed
    that only rewrote Florida would make their income slider a no-op again.
    """
    found = set(florida_parcel_fips())
    for market in ("atlanta", "charleston"):
        meta_path = FIX / "market-parcels" / "markets" / market / "meta.json"
        meta = json.loads(meta_path.read_text())
        for county in meta.get("counties") or []:
            if (county.get("featureCount") or 0) > 0 and county.get("fips"):
                found.add(str(county["fips"]))
    return sorted(found)


def round_coords(node):
    if isinstance(node, (int, float)):
        return node
    if node and isinstance(node[0], (int, float)):
        return [round(float(node[0]), 5), round(float(node[1]), 5)]
    return [round_coords(item) for item in node]


def fetch_county_income(fips: str) -> list[dict]:
    data = fetch_json(REPORTER_DATA, {"table_ids": "B19013", "geo_ids": f"140|05000US{fips}"}, timeout=90)
    incomes: dict[str, dict] = {}
    for full_id, payload in (data.get("data") or {}).items():
        geoid = geoid_from_reporter(full_id)
        estimate = ((payload.get("B19013") or {}).get("estimate") or {}).get("B19013001")
        moe = ((payload.get("B19013") or {}).get("error") or {}).get("B19013001")
        name = ((data.get("geography") or {}).get(full_id) or {}).get("name")
        if estimate in (None, -666666666, -999999999):
            estimate = None
        incomes[geoid] = {
            "geoid": geoid,
            "name": name,
            "medianHouseholdIncome": estimate,
            "medianHouseholdIncomeMoe": moe if estimate is not None else None,
        }
    geo = fetch_json(REPORTER_GEO, {"geo_ids": f"140|05000US{fips}"}, timeout=120)
    features = []
    for feature in geo.get("features") or []:
        props = feature.get("properties") or {}
        raw_id = str(props.get("full_geoid") or props.get("geoid") or "")
        geoid = geoid_from_reporter(raw_id)
        income = incomes.get(geoid)
        if not geoid or not feature.get("geometry"):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": feature["geometry"]["type"],
                    "coordinates": round_coords(feature["geometry"].get("coordinates") or []),
                },
                "properties": income
                or {
                    "geoid": geoid,
                    "name": props.get("name"),
                    "medianHouseholdIncome": None,
                    "medianHouseholdIncomeMoe": None,
                },
            }
        )
    return features


def simplify_line(path: list) -> list[list[float]]:
    pts = [(float(x), float(y)) for x, y in path]
    if len(pts) > 8:
        pts = douglas_peucker(pts, 0.00008)
    return [[round(x, 5), round(y, 5)] for x, y in pts]


def fetch_aadt() -> list[dict]:
    features: list[dict] = []
    offset = 0
    while True:
        data = fetch_json(
            FDOT_QUERY,
            {
                "where": f"YEAR_={AADT_YEAR} AND AADT>0",
                "outFields": "AADT,ROADWAY,DESC_FRM,DESC_TO,YEAR_,COUNTY",
                "returnGeometry": "true",
                "outSR": 4326,
                "resultOffset": offset,
                "resultRecordCount": 2000,
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            raise RuntimeError(data["error"])
        batch = data.get("features") or []
        for item in batch:
            attrs = item.get("attributes") or {}
            paths = (item.get("geometry") or {}).get("paths") or []
            if not paths:
                continue
            line = simplify_line(paths[0])
            if len(line) < 2:
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": line},
                    "properties": {
                        "aadt": attrs.get("AADT"),
                        "year": attrs.get("YEAR_"),
                        "roadwayId": (attrs.get("ROADWAY") or "").strip() or None,
                        "from": (attrs.get("DESC_FRM") or "").strip() or None,
                        "to": (attrs.get("DESC_TO") or "").strip() or None,
                        "county": (attrs.get("COUNTY") or "").strip() or None,
                    },
                }
            )
        print(f"  AADT {len(features)}")
        if not data.get("exceededTransferLimit") and len(batch) < 2000:
            break
        if not batch:
            break
        offset += len(batch)
        time.sleep(0.05)
    return features


def main() -> None:
    fips_list = income_county_fips()
    if "12095" not in fips_list:
        raise RuntimeError("Orange County FIPS missing from parcel fixtures")
    print(f"Florida parcel counties: {len(fips_list)}")
    income_features: list[dict] = []
    failed: list[str] = []
    for fips in fips_list:
        try:
            rows = fetch_county_income(fips)
        except Exception as exc:  # noqa: BLE001
            print(f"  {fips} failed: {exc}")
            failed.append(fips)
            continue
        print(f"  {fips} tracts {len(rows)}")
        income_features.extend(rows)
        time.sleep(0.15)
    if failed:
        raise RuntimeError(f"Income download failed for {failed}")
    if not any(feature["properties"]["geoid"].startswith("12095") for feature in income_features):
        raise RuntimeError("Orange County tracts missing from the income sidecar")
    known = sum(1 for feature in income_features if feature["properties"].get("medianHouseholdIncome") is not None)
    INCOME_OUT.write_text(
        json.dumps(
            {"type": "FeatureCollection", "name": "florida-parcel-counties-acs-b19013", "features": income_features},
            separators=(",", ":"),
        )
    )
    print(f"income tracts {len(income_features)} with a median {known}")

    print(f"FDOT AADT {AADT_YEAR}")
    segments = fetch_aadt()
    if len(segments) < 10000:
        raise RuntimeError(f"FDOT returned only {len(segments)} segments")
    SEGMENTS_OUT.write_text(
        json.dumps(
            {"type": "FeatureCollection", "name": f"fdot-aadt-{AADT_YEAR}", "features": segments},
            separators=(",", ":"),
        )
    )
    major = [feature for feature in segments if (feature["properties"].get("aadt") or 0) >= MAJOR_AADT]
    for feature in major:
        props = dict(feature["properties"])
        props.pop("county", None)
        feature = {**feature, "properties": props}
    # rebuild without county on the overlay the map already expects
    overlay = []
    for feature in major:
        props = {key: value for key, value in feature["properties"].items() if key != "county"}
        overlay.append({**feature, "properties": props})
    TRAFFIC_OUT.write_text(
        json.dumps(
            {"type": "FeatureCollection", "name": f"fdot-aadt-{AADT_YEAR}-major", "features": overlay},
            separators=(",", ":"),
        )
    )
    META_OUT.write_text(
        json.dumps(
            {
                "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "incomeSource": REPORTER_DATA,
                "incomeTable": "B19013",
                "incomeCounties": fips_list,
                "incomeTractCount": len(income_features),
                "incomeKnownCount": known,
                "aadtSource": FDOT_QUERY.replace("/query", ""),
                "aadtYear": AADT_YEAR,
                "aadtSegmentCount": len(segments),
                "majorRoadOverlayCount": len(overlay),
                "majorRoadMinAadt": MAJOR_AADT,
                "notes": [
                    "Income and AADT are not stored on parcel tiles.",
                    "A parcel more than 15 km from the nearest FDOT segment stays unknown.",
                    "Block-group income remains the Orange County pilot fixture.",
                    "Tract median income is joined for Florida parcel counties plus Atlanta and Charleston parcel counties. Other states stay unknown. AADT stays FDOT (Florida).",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(f"segments {len(segments)} major overlay {len(overlay)}")


if __name__ == "__main__":
    main()
