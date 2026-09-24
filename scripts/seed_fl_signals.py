#!/usr/bin/env python3
"""Sidecar ACS income and FDOT AADT.

Parcel tiles do not store these fields. `/api/parcels` joins them at query time.

  python3 scripts/seed_fl_signals.py

Income is ACS 5-year 2020–2024 B19013 for every state with a live parcel
extract (`scripts/seed_se_acs_income.py`). AADT is FDOT RCI FeatureServer/0,
field AADT, YEAR_=2025. The service is EPSG:26917; the extract requests
outSR 4326. The map overlay stays the 15,000+ subset.

  python3 scripts/seed_fl_signals.py --aadt-only
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
FDOT_QUERY = "https://gis.fdot.gov/arcgis/rest/services/RCI_Layers/FeatureServer/0/query"
AADT_YEAR = 2025
MAJOR_AADT = 15000
# Layer maxRecordCount is 1000. A larger page is truncated and the next offset skips rows.
AADT_PAGE = 1000


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
                "resultRecordCount": AADT_PAGE,
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
            roadway = attrs.get("ROADWAY")
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": line},
                    "properties": {
                        "aadt": attrs.get("AADT"),
                        "year": attrs.get("YEAR_"),
                        "roadwayId": str(roadway).strip() if roadway not in (None, "") else None,
                        "from": (str(attrs.get("DESC_FRM") or "")).strip() or None,
                        "to": (str(attrs.get("DESC_TO") or "")).strip() or None,
                        "county": (str(attrs.get("COUNTY") or "")).strip() or None,
                    },
                }
            )
        print(f"  AADT {len(features)}")
        if not batch or len(batch) < AADT_PAGE:
            break
        offset += len(batch)
        time.sleep(0.05)
    return features


def _norm_county(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def require_footprint(segments: list[dict]) -> dict[str, int]:
    """Every Florida footprint county on the RCI layer, including Orange and Hillsborough."""
    from seed_state_aadt import FL

    by_norm = {_norm_county(name): fips for fips, name in FL.items()}
    counts: dict[str, int] = {}
    for feature in segments:
        props = feature.get("properties") or {}
        fips = by_norm.get(_norm_county(str(props.get("county") or "")))
        aadt = props.get("aadt")
        if not fips or not isinstance(aadt, (int, float)) or aadt <= 0:
            continue
        counts[fips] = counts.get(fips, 0) + 1
    missing = [f"{fips} {FL[fips]}" for fips in FL if fips not in counts]
    if missing:
        raise RuntimeError(f"FDOT RCI has no 2025 segments for {missing}")
    return counts


def write_aadt() -> None:
    print(f"FDOT RCI AADT {AADT_YEAR} {FDOT_QUERY}")
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
    counts = require_footprint(segments)
    meta = json.loads(META_OUT.read_text()) if META_OUT.exists() else {}
    notes = []
    for note in meta.get("notes") or []:
        if "RCI FeatureServer/0 returned HTTP 500" in note:
            continue
        if note.startswith("Florida AADT is the existing FDOT 2025 historical"):
            continue
        notes.append(note)
    rci_note = (
        "Florida AADT is FDOT RCI FeatureServer/0 (gis.fdot.gov), field AADT, YEAR_=2025, "
        "for every footprint county including Orange and Hillsborough. The service is EPSG:26917; "
        "this extract requested outSR 4326. Nearest segment to the parcel centroid within 15 km."
    )
    if rci_note not in notes:
        notes.append(rci_note)
    notes = [
        note
        for note in notes
        if note != "A parcel more than 15 km from the nearest FDOT segment stays unknown. AADT stays FDOT (Florida)."
    ]
    sources = dict(meta.get("stateAadtSources") or {})
    florida = dict(sources.get("FL") or {})
    florida.update(
        {
            "agency": "FDOT",
            "field": "AADT",
            "year": AADT_YEAR,
            "yearField": "YEAR_",
            "url": FDOT_QUERY.replace("/query", ""),
            "crs": "EPSG:26917",
        }
    )
    sources["FL"] = florida
    meta.update(
        {
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "aadtSource": FDOT_QUERY.replace("/query", ""),
            "aadtYear": AADT_YEAR,
            "aadtSegmentCount": len(segments),
            "majorRoadOverlayCount": len(overlay),
            "majorRoadMinAadt": MAJOR_AADT,
            "flAadtByCounty": dict(sorted(counts.items())),
            "stateAadtSources": sources,
            "notes": notes,
        }
    )
    META_OUT.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"segments {len(segments)} major overlay {len(overlay)} footprint counties {len(counts)}")


def main() -> None:
    import sys

    if "--aadt-only" not in sys.argv:
        from seed_se_acs_income import seed_income

        seed_income()
    write_aadt()


if __name__ == "__main__":
    main()
