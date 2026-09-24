#!/usr/bin/env python3
"""State DOT traffic counts for the priority counties that are not Florida.

Florida stays on the existing FDOT 2025 sidecar (`aadt-segments.geojson`).
The FDOT RCI FeatureServer/0 URL returned HTTP 500 in this environment, so
this script does not replace that layer.

Each other state uses the statewide open service from the 2026-09-24 rollup,
filtered to the stamped priority counties. Counts are copied from the published
field. Zero and missing values are left out. No count is estimated.

  python3 scripts/seed_state_aadt.py
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
OUT = FIX / "aadt-state-dots.geojson"
META = FIX / "signals-meta.json"

# Padded county envelopes, WGS84. Used only where the service has no county field (GDOT).
GA_ENVELOPES = {
    "13121": [-84.90, 33.48, -84.05, 34.22],  # Fulton
    "13067": [-84.92, 33.75, -84.32, 34.18],  # Cobb
    "13089": [-84.45, 33.62, -84.00, 34.00],  # DeKalb
    "13185": [-83.62, 30.52, -82.98, 31.08],  # Lowndes
    "13021": [-83.90, 32.62, -83.48, 32.98],  # Bibb
}


def fetch_json(url: str, params: dict, timeout: int = 120) -> dict:
    full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": "darryl-land-search/state-aadt"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed {url[:80]}: {last}")


def simplify_line(path: list) -> list[list[float]]:
    pts = [(float(x), float(y)) for x, y in path]
    if len(pts) > 8:
        pts = douglas_peucker(pts, 0.00008)
    return [[round(x, 5), round(y, 5)] for x, y in pts]


def as_count(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0 or number > 500_000:
        return None
    return int(round(number))


def as_year(value) -> int | None:
    try:
        year = int(float(value))
    except (TypeError, ValueError):
        return None
    return year if 1990 <= year <= 2035 else None


def line_features(item: dict, props: dict) -> list[dict]:
    paths = (item.get("geometry") or {}).get("paths") or []
    out = []
    for path in paths[:1]:
        line = simplify_line(path)
        if len(line) < 2:
            continue
        out.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": line}, "properties": props})
    return out


def point_feature(item: dict, props: dict) -> dict | None:
    geom = item.get("geometry") or {}
    x = geom.get("x")
    y = geom.get("y")
    if x is None or y is None:
        return None
    lon, lat = round(float(x), 5), round(float(y), 5)
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[lon, lat], [lon, lat]]},
        "properties": props,
    }


def page_query(url: str, params: dict) -> list[dict]:
    features: list[dict] = []
    offset = 0
    page_size = int(params.get("resultRecordCount") or 2000)
    while offset < 250_000:
        data = fetch_json(url, {**params, "resultOffset": offset, "f": "json"})
        if data.get("error"):
            raise RuntimeError(data["error"])
        batch = data.get("features") or []
        if not batch:
            break
        features.extend(batch)
        offset += len(batch)
        if len(batch) < page_size:
            break
        time.sleep(0.05)
    return features


def props(aadt: int, year: int | None, roadway: str | None, agency: str, state: str, fips: str) -> dict:
    return {
        "aadt": aadt,
        "year": year,
        "roadwayId": roadway,
        "from": None,
        "to": None,
        "agency": agency,
        "state": state,
        "countyFips": fips,
    }


def fetch_nc() -> list[dict]:
    url = "https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query"
    counties = {"MECKLENBURG": "37119", "WAKE": "37183", "DURHAM": "37063"}
    where = "COUNTY IN ('MECKLENBURG','WAKE','DURHAM')"
    rows = page_query(
        url,
        {
            "where": where,
            "outFields": "FID,COUNTY,AADT_2022,ROUTE",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultRecordCount": 1000,
        },
    )
    out = []
    seen = set()
    for item in rows:
        attrs = item.get("attributes") or {}
        oid = attrs.get("FID")
        if oid in seen:
            continue
        seen.add(oid)
        count = as_count(attrs.get("AADT_2022"))
        fips = counties.get(str(attrs.get("COUNTY") or "").upper())
        if count is None or not fips:
            continue
        feature = point_feature(item, props(count, 2022, (attrs.get("ROUTE") or None), "NCDOT", "North Carolina", fips))
        if feature:
            out.append(feature)
    print(f"  NC stations {len(out)}")
    return out


def fetch_sc() -> list[dict]:
    url = "https://services1.arcgis.com/VaY7cY9pvUYUP1Lf/arcgis/rest/services/2025_Statewide_Traffic_Points/FeatureServer/0/query"
    # CountyName is stored uppercase (BEAUFORT, not Beaufort).
    counties = {"CHARLESTON": "45019", "DORCHESTER": "45035", "BERKELEY": "45015", "BEAUFORT": "45013"}
    names = "','".join(counties)
    rows = page_query(
        url,
        {
            "where": f"CountyName IN ('{names}')",
            "outFields": "CountyName,FactoredAA,FactoredA1,OBJECTID",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultRecordCount": 2000,
        },
    )
    out = []
    seen = set()
    for item in rows:
        attrs = item.get("attributes") or {}
        oid = attrs.get("OBJECTID")
        if oid in seen:
            continue
        seen.add(oid)
        count = as_count(attrs.get("FactoredAA"))
        fips = counties.get(attrs.get("CountyName"))
        if count is None or not fips:
            continue
        feature = point_feature(
            item,
            props(count, as_year(attrs.get("FactoredA1")) or 2025, None, "SCDOT", "South Carolina", fips),
        )
        if feature:
            out.append(feature)
    print(f"  SC points {len(out)}")
    return out


def fetch_tn() -> list[dict]:
    url = "https://services2.arcgis.com/nf3p7v7Zy4fTOh6M/arcgis/rest/services/Traffic_Lines/FeatureServer/0/query"
    # TDOT county number 19 is Davidson (confirmed against a Nashville envelope).
    rows = page_query(
        url,
        {
            "where": "COUNTY_NUMBER='19' AND AADT>0",
            "outFields": "COUNTY_NUMBER,AADT,AADTYEAR,OBJECTID",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultRecordCount": 2000,
        },
    )
    out = []
    seen = set()
    for item in rows:
        attrs = item.get("attributes") or {}
        oid = attrs.get("OBJECTID")
        if oid in seen:
            continue
        seen.add(oid)
        count = as_count(attrs.get("AADT"))
        if count is None:
            continue
        out.extend(
            line_features(
                item,
                props(count, as_year(attrs.get("AADTYEAR")), None, "TDOT", "Tennessee", "47037"),
            )
        )
    print(f"  TN Davidson segments {len(out)}")
    return out


def fetch_ms() -> list[dict]:
    url = "https://services.arcgis.com/04HiymDgLlsbhaV4/arcgis/rest/services/Mississippi_RCI/FeatureServer/3/query"
    # COUNTYNMBR is not the FIPS county code. Interior samples:
    # Clinton and Raymond (Hinds) are 25, Canton and Gluckstadt (Madison) are 45,
    # Flowood and Pelahatchie (Rankin) are 61. Codes 49, 89, and 121 are other counties.
    counties = {25: "28049", 45: "28089", 61: "28121"}
    rows = page_query(
        url,
        {
            "where": "COUNTYNMBR IN (25,45,61) AND ADT_21>0",
            "outFields": "COUNTYNMBR,ADT_21,OBJECTID",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultRecordCount": 2000,
        },
    )
    out = []
    seen = set()
    for item in rows:
        attrs = item.get("attributes") or {}
        oid = attrs.get("OBJECTID")
        if oid in seen:
            continue
        seen.add(oid)
        count = as_count(attrs.get("ADT_21"))
        fips = counties.get(int(attrs.get("COUNTYNMBR") or 0))
        if count is None or not fips:
            continue
        out.extend(line_features(item, props(count, 2021, None, "Mississippi RCI", "Mississippi", fips)))
    print(f"  MS segments {len(out)}")
    return out


def _point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def load_ga_tracts() -> tuple[list[dict], dict[tuple[int, int], list[int]]]:
    """TIGER 2024 tract rings for the five priority counties. GDOT has no county field.

    The state county zip 404s. Tract GEOID[:5] is the county. A road midpoint that
    falls in one of these tracts is tagged with that county and not a neighboring box.
    """
    import zipfile
    from collections import defaultdict

    import shapefile

    url = "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_13_tract.zip"
    cache = Path("/tmp/acs-b19013/tl_2024_13_tract.zip")
    folder = cache.parent / "tl_2024_13_tract"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists() or cache.stat().st_size < 1000:
        req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/state-aadt"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            cache.write_bytes(resp.read())
    if not (folder / "tl_2024_13_tract.shp").exists():
        folder.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(cache) as archive:
            archive.extractall(folder)
    wanted = set(GA_ENVELOPES)
    reader = shapefile.Reader(str(folder / "tl_2024_13_tract"))
    names = [field[0] for field in reader.fields[1:]]
    geoid_i = names.index("GEOID")
    tracts: list[dict] = []
    index: dict[tuple[int, int], list[int]] = defaultdict(list)
    seen_counties: set[str] = set()
    for shape, record in zip(reader.shapes(), reader.records(), strict=True):
        geoid = str(record[geoid_i])
        fips = geoid[:5]
        if fips not in wanted:
            continue
        seen_counties.add(fips)
        minx, miny, maxx, maxy = shape.bbox
        parts = list(shape.parts) + [len(shape.points)]
        rings = []
        for start, end in zip(parts, parts[1:]):
            ring = [(float(x), float(y)) for x, y in shape.points[start:end]]
            if len(ring) >= 4:
                rings.append(ring)
        if not rings:
            continue
        slot = len(tracts)
        tracts.append({"fips": fips, "bbox": (minx, miny, maxx, maxy), "rings": rings})
        ix0, ix1 = int(minx // 0.05), int(maxx // 0.05)
        iy0, iy1 = int(miny // 0.05), int(maxy // 0.05)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                index[(ix, iy)].append(slot)
    missing = wanted - seen_counties
    if missing:
        raise RuntimeError(f"TIGER tracts missing counties {sorted(missing)}")
    return tracts, index


def county_for_point(
    lon: float,
    lat: float,
    tracts: list[dict],
    index: dict[tuple[int, int], list[int]],
) -> str | None:
    for slot in index.get((int(lon // 0.05), int(lat // 0.05)), ()):
        tract = tracts[slot]
        minx, miny, maxx, maxy = tract["bbox"]
        if not (minx <= lon <= maxx and miny <= lat <= maxy):
            continue
        if any(_point_in_ring(lon, lat, ring) for ring in tract["rings"]):
            return tract["fips"]
    return None


def fetch_ga() -> list[dict]:
    url = "https://maps.itos.uga.edu/arcgis/rest/services/GDOT/GDOT_FunctionalClass/MapServer/21/query"
    tracts, tract_index = load_ga_tracts()
    out = []
    seen = set()
    by_fips = {fips: 0 for fips in GA_ENVELOPES}
    for fips, box in GA_ENVELOPES.items():
        west, south, east, north = box
        rows = page_query(
            url,
            {
                "where": "AADT>0",
                "geometry": json.dumps({"xmin": west, "ymin": south, "xmax": east, "ymax": north}),
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "AADT,Road,OBJECTID",
                "returnGeometry": "true",
                "outSR": 4326,
                "resultRecordCount": 1000,
            },
        )
        for item in rows:
            attrs = item.get("attributes") or {}
            oid = attrs.get("OBJECTID")
            if oid in seen:
                continue
            count = as_count(attrs.get("AADT"))
            paths = (item.get("geometry") or {}).get("paths") or []
            if count is None or not paths or not paths[0]:
                continue
            mid = paths[0][len(paths[0]) // 2]
            tagged = county_for_point(float(mid[0]), float(mid[1]), tracts, tract_index)
            if tagged not in GA_ENVELOPES:
                continue
            seen.add(oid)
            features = line_features(item, props(count, None, (attrs.get("Road") or None), "GDOT", "Georgia", tagged))
            by_fips[tagged] = by_fips.get(tagged, 0) + len(features)
            out.extend(features)
    for fips, kept in by_fips.items():
        print(f"  GA {fips} segments {kept}")
    return out


def main() -> None:
    features: list[dict] = []
    features.extend(fetch_nc())
    features.extend(fetch_sc())
    features.extend(fetch_tn())
    features.extend(fetch_ms())
    features.extend(fetch_ga())
    if len(features) < 100:
        raise RuntimeError(f"State DOT download returned only {len(features)} counts")
    OUT.write_text(
        json.dumps(
            {"type": "FeatureCollection", "name": "state-dot-aadt-priority-counties", "features": features},
            separators=(",", ":"),
        )
    )
    by_fips: dict[str, int] = {}
    for feature in features:
        fips = feature["properties"]["countyFips"]
        by_fips[fips] = by_fips.get(fips, 0) + 1
    meta = json.loads(META.read_text()) if META.exists() else {}
    notes = [note for note in (meta.get("notes") or []) if "AADT" not in note and "FDOT" not in note]
    notes.append(
        "Florida AADT is the existing FDOT 2025 historical count layer. gis.fdot.gov RCI FeatureServer/0 returned HTTP 500 here, so that URL was not used."
    )
    notes.append(
        "NC, GA, SC, TN, and MS priority counties use the state DOT (or documented statewide) layer filtered to those counties. Mississippi COUNTYNMBR is not FIPS: Hinds 25, Madison 45, Rankin 61. GDOT MapServer/21 has no county field, so a segment is kept only when its midpoint falls in that county's TIGER tract. That layer is sparse. Alabama and Arkansas have no verified AADT join. Other counties in a covered state stay unknown."
    )
    notes.append("A parcel more than 15 km from the nearest count stays unknown. Outside Florida the drawer label is Nearest AADT, not FDOT.")
    meta.update(
        {
            "stateAadtSource": "priority-county state DOT layers, 2026-09-24 rollup",
            "stateAadtCount": len(features),
            "stateAadtByCounty": dict(sorted(by_fips.items())),
            "notes": notes,
        }
    )
    META.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote {len(features)} counts, {OUT.stat().st_size} bytes")
    missing = [
        fips
        for fips in [
            "37119",
            "37183",
            "37063",
            "13121",
            "13067",
            "13089",
            "13185",
            "13021",
            "45019",
            "45035",
            "45015",
            "45013",
            "47037",
            "28049",
            "28089",
            "28121",
        ]
        if fips not in by_fips
    ]
    if missing:
        raise RuntimeError(f"No counts for {missing}")


if __name__ == "__main__":
    main()
