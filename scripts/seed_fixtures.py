#!/usr/bin/env python3
"""Download a geographically mixed Orange County, FL pilot dataset.

Sources (public, no commercial parcel vendors):
  - OCPA parcel FeatureServer (owner, sale, tax, zoning, acreage, geometry)
  - FDOT AADT FeatureServer (nearest major-road traffic)
  - Census Reporter ACS 5-year B19013 (median household income)
  - Orange County + Orlando Future Land Use (joined by scripts/join_flu.py after this seed)
  - HUD/Treasury Opportunity Zones (joined by scripts/join_oz.py after FLU)
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

from parcel_geometry import esri_rings_to_geojson

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fixtures"
OUT.mkdir(parents=True, exist_ok=True)

OCPA_URL = "https://vgispublic.ocpafl.org/server/rest/services/Webmap/PARCEL/MapServer/4/query"
FDOT_URL = "https://gis.fdot.gov/arcgis/rest/services/RCI_Layers/FeatureServer/0/query"
CENSUS_REPORTER_DATA = "https://api.censusreporter.org/1.0/data/show/latest"
CENSUS_REPORTER_GEO = "https://api.censusreporter.org/1.0/geo/show/tiger2023"

OCPA_FIELDS = [
    "PARCEL",
    "NAME1",
    "NAME2",
    "PROP_NAME",
    "SITUS",
    "ZONING_CODE",
    "SALE_DATE",
    "SALE_ADJ_VALUE",
    "TOTAL_MKT",
    "TOTAL_ASSD",
    "TAXABLE",
    "TAXES",
    "ACREAGE",
    "ADD1",
    "ADD2",
    "CITY",
    "STATE",
    "ZIP",
    "DOR_CODE",
    "CITY_SITUS",
    "ZIP_SITUS",
    "QUAL_CODE",
    "CITY_CODE",
    "CONDO_FLAG",
]

# Multiple windows across Orange County so the map is not a single cluster.
BBOXES = [
    (-81.42, 28.50, -81.35, 28.56),  # downtown / mils
    (-81.39, 28.58, -81.32, 28.63),  # winter park
    (-81.55, 28.54, -81.47, 28.60),  # ocoee / west
    (-81.24, 28.57, -81.16, 28.64),  # ucf / east
    (-81.48, 28.42, -81.40, 28.48),  # i-drive / south-central
    (-81.53, 28.66, -81.45, 28.72),  # apopka
    (-81.36, 28.44, -81.28, 28.50),  # airport / south-east
    (-81.62, 28.46, -81.54, 28.53),  # windermere / west lakes
]

ZONING_QUERIES = [
    "ZONING_CODE LIKE '%R-3%' AND ACREAGE > 0.3 AND CONDO_FLAG <> 'C'",
    "ZONING_CODE LIKE '%U-R-3%' AND CONDO_FLAG <> 'C'",
    "(ZONING_CODE LIKE '%MXD%' OR ZONING_CODE LIKE '%MIXED%') AND ACREAGE > 0.2 AND CONDO_FLAG <> 'C'",
    "ZONING_CODE LIKE '%AC-%' AND ACREAGE > 0.25 AND CONDO_FLAG <> 'C'",
    "(ZONING_CODE LIKE '%P-D%' OR ZONING_CODE LIKE '%-PD%' OR ZONING_CODE LIKE '% PD%') AND ACREAGE > 0.75 AND CONDO_FLAG <> 'C'",
    "ZONING_CODE LIKE '%R-1%' AND ACREAGE > 0.45 AND CONDO_FLAG <> 'C'",
    "(ZONING_CODE LIKE '%C-1%' OR ZONING_CODE LIKE '%C-2%' OR ZONING_CODE LIKE '%P-O%') AND ACREAGE > 0.4 AND CONDO_FLAG <> 'C'",
]


def fetch_json(url: str, params: dict | None = None, timeout: int = 45, retries: int = 3) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "orange-county-mf-pilot/0.1"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 — seed script, retry then fail
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def arcgis_query(url: str, params: dict, page_size: int = 200, max_records: int = 400) -> list[dict]:
    features: list[dict] = []
    offset = 0
    while len(features) < max_records:
        page = dict(params)
        page["resultOffset"] = offset
        page["resultRecordCount"] = min(page_size, max_records - len(features))
        page.setdefault("f", "json")
        data = fetch_json(url, page)
        if data.get("error"):
            raise RuntimeError(f"ArcGIS error for {url}: {data['error']}")
        batch = data.get("features") or []
        features.extend(batch)
        if not data.get("exceededTransferLimit") and len(batch) < page["resultRecordCount"]:
            break
        if not batch:
            break
        offset += len(batch)
        time.sleep(0.15)
    return features


def rings_to_geojson(geom: dict | None) -> dict | None:
    if not geom or not geom.get("rings"):
        return None
    return esri_rings_to_geojson(geom["rings"])


def ring_area(coords: list[list[float]]) -> float:
    area = 0.0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def simplify_line(coords: list[list[float]], epsilon: float) -> list[list[float]]:
    if len(coords) < 5:
        return coords

    def perp_dist(p, a, b) -> float:
        if a == b:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / (
            (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
        )
        t = max(0.0, min(1.0, t))
        x = a[0] + t * (b[0] - a[0])
        y = a[1] + t * (b[1] - a[1])
        return math.hypot(p[0] - x, p[1] - y)

    def rdp(pts: list[list[float]]) -> list[list[float]]:
        if len(pts) < 3:
            return pts
        max_d = -1.0
        idx = 0
        for i in range(1, len(pts) - 1):
            d = perp_dist(pts[i], pts[0], pts[-1])
            if d > max_d:
                max_d = d
                idx = i
        if max_d > epsilon:
            return rdp(pts[: idx + 1])[:-1] + rdp(pts[idx:])
        return [pts[0], pts[-1]]

    simplified = rdp(coords)
    return simplified if len(simplified) >= 4 else coords


def centroid(geometry: dict) -> tuple[float, float]:
    polys = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    best = polys[0][0]
    a = ring_area(best)
    cx = cy = 0.0
    for i in range(len(best) - 1):
        x1, y1 = best[i]
        x2, y2 = best[i + 1]
        cross = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if a == 0:
        xs = [p[0] for p in best]
        ys = [p[1] for p in best]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    return (cx / (6 * a), cy / (6 * a))


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_feature(x: float, y: float, feature: dict) -> bool:
    geom = feature.get("geometry") or {}
    gtype = geom.get("type")
    coords = geom.get("coordinates") or []
    if gtype == "Polygon":
        if not coords or not point_in_ring(x, y, coords[0]):
            return False
        return all(not point_in_ring(x, y, hole) for hole in coords[1:])
    if gtype == "MultiPolygon":
        for poly in coords:
            if poly and point_in_ring(x, y, poly[0]) and all(not point_in_ring(x, y, hole) for hole in poly[1:]):
                return True
        return False
    return False


def dist_point_to_seg(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def min_dist_to_line(px: float, py: float, line: list[list[float]]) -> float:
    best = float("inf")
    for i in range(len(line) - 1):
        d = dist_point_to_seg(px, py, line[i][0], line[i][1], line[i + 1][0], line[i + 1][1])
        if d < best:
            best = d
    return best


def clean_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def epoch_to_iso(value) -> str | None:
    if value in (None, "", 0):
        return None
    try:
        ms = int(value)
        # OCPA uses a ~1900 sentinel for "no sale on record"
        if ms < 0 or ms < 315532800000:  # before 1980-01-01
            return None
        return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))
    except (TypeError, ValueError, OSError):
        return None


def parse_zoning(code: str | None) -> dict:
    if not code:
        return {"zoningCode": None, "zoningDistrict": None, "jurisdictionPrefix": None}
    raw = code.strip()
    jurisdiction = None
    rest = raw
    if "-" in raw and raw.split("-", 1)[0].isalpha() and len(raw.split("-", 1)[0]) <= 3:
        jurisdiction, rest = raw.split("-", 1)
    district = rest.split("/", 1)[0].strip()
    return {"zoningCode": raw, "zoningDistrict": district or None, "jurisdictionPrefix": jurisdiction}


def fetch_parcels() -> list[dict]:
    by_id: dict[str, dict] = {}
    for where in ZONING_QUERIES:
        print(f"OCPA zoning query: {where}")
        feats = arcgis_query(
            OCPA_URL,
            {
                "where": where,
                "outFields": ",".join(OCPA_FIELDS),
                "returnGeometry": "true",
                "outSR": 4326,
                "orderByFields": "ACREAGE DESC",
            },
            page_size=40,
            max_records=40,
        )
        for feat in feats:
            pid = clean_str((feat.get("attributes") or {}).get("PARCEL"))
            if pid:
                by_id[pid] = feat
        print(f"  total unique {len(by_id)}")

    for xmin, ymin, xmax, ymax in BBOXES:
        envelope = f"{xmin},{ymin},{xmax},{ymax}"
        print(f"OCPA bbox {xmin},{ymin} -> {xmax},{ymax}")
        feats = arcgis_query(
            OCPA_URL,
            {
                "where": "ACREAGE > 0.25 AND CONDO_FLAG <> 'C'",
                "outFields": ",".join(OCPA_FIELDS),
                "returnGeometry": "true",
                "outSR": 4326,
                "geometry": envelope,
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "orderByFields": "ACREAGE DESC",
            },
            page_size=40,
            max_records=30,
        )
        for feat in feats:
            pid = clean_str((feat.get("attributes") or {}).get("PARCEL"))
            if pid:
                by_id[pid] = feat
        print(f"  total unique {len(by_id)}")
    return list(by_id.values())


def fetch_aadt() -> list[dict]:
    print("FDOT AADT Orange County")
    feats = arcgis_query(
        FDOT_URL,
        {
            "where": "YEAR_=2025 AND COUNTY='Orange' AND AADT>0",
            "outFields": "AADT,ROADWAY,DESC_FRM,DESC_TO,YEAR_",
            "returnGeometry": "true",
            "outSR": 4326,
        },
        page_size=500,
        max_records=4000,
    )
    print(f"  segments {len(feats)}")
    return feats


def geoid_from_censusreporter(full_id: str) -> str:
    # 14000US12095010201 -> 12095010201
    if "US" in full_id:
        return full_id.split("US", 1)[1]
    return full_id


def fetch_income(level: str) -> tuple[dict[str, dict], dict]:
    geo_prefix = "140" if level == "tract" else "150"
    print(f"Census Reporter income {level}")
    data = fetch_json(
        CENSUS_REPORTER_DATA,
        {"table_ids": "B19013", "geo_ids": f"{geo_prefix}|05000US12095"},
        timeout=60,
    )
    incomes: dict[str, dict] = {}
    for full_id, payload in (data.get("data") or {}).items():
        geoid = geoid_from_censusreporter(full_id)
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
    print(f"  {level} rows {len(incomes)} release={data.get('release')}")
    print(f"Census Reporter geo {level}")
    geo = fetch_json(
        CENSUS_REPORTER_GEO,
        {"geo_ids": f"{geo_prefix}|05000US12095"},
        timeout=90,
    )
    return incomes, geo


def lookup_income(x: float, y: float, features: list[dict], incomes: dict[str, dict]) -> dict | None:
    for feat in features:
        if point_in_feature(x, y, feat):
            props = feat.get("properties") or {}
            raw_id = str(props.get("full_geoid") or props.get("geoid") or "")
            geoid = geoid_from_censusreporter(raw_id)
            found = incomes.get(geoid)
            if found:
                return found
            return {"geoid": geoid, "name": props.get("name"), "medianHouseholdIncome": None, "medianHouseholdIncomeMoe": None}
    return None


def nearest_aadt(x: float, y: float, roads: list[tuple[dict, list[list[float]]]]) -> dict | None:
    best = None
    best_d = float("inf")
    for props, line in roads:
        d = min_dist_to_line(x, y, line)
        if d < best_d:
            best_d = d
            best = (props, d)
    if not best:
        return None
    props, dist_deg = best
    # ~111_320 m per degree latitude; longitude scaled by cos(lat)
    meters = dist_deg * 111_320
    return {
        "aadt": props.get("AADT"),
        "year": props.get("YEAR_"),
        "roadwayId": clean_str(props.get("ROADWAY")),
        "from": clean_str(props.get("DESC_FRM")),
        "to": clean_str(props.get("DESC_TO")),
        "distanceMeters": round(meters),
    }


def main() -> None:
    parcels_raw = fetch_parcels()
    aadt_raw = fetch_aadt()
    tract_income, tract_geo = fetch_income("tract")
    bg_income, bg_geo = fetch_income("block_group")

    tract_features = tract_geo.get("features") or []
    bg_features = bg_geo.get("features") or []

    roads: list[tuple[dict, list[list[float]]]] = []
    traffic_features = []
    for feat in aadt_raw:
        geom = feat.get("geometry") or {}
        paths = geom.get("paths") or []
        if not paths:
            continue
        line = simplify_line([[round(x, 5), round(y, 5)] for x, y in paths[0]], 0.00025)
        if len(line) < 2:
            continue
        attrs = feat.get("attributes") or {}
        roads.append((attrs, line))
        if attrs.get("AADT") and attrs["AADT"] >= 15000:
            traffic_features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": line},
                    "properties": {
                        "aadt": attrs.get("AADT"),
                        "year": attrs.get("YEAR_"),
                        "roadwayId": clean_str(attrs.get("ROADWAY")),
                        "from": clean_str(attrs.get("DESC_FRM")),
                        "to": clean_str(attrs.get("DESC_TO")),
                    },
                }
            )

    parcel_features = []
    skipped = 0
    for feat in parcels_raw:
        attrs = feat.get("attributes") or {}
        geometry = rings_to_geojson(feat.get("geometry"))
        if not geometry:
            skipped += 1
            continue
        pid = clean_str(attrs.get("PARCEL"))
        if not pid:
            skipped += 1
            continue
        lon, lat = centroid(geometry)
        if not (-81.7 <= lon <= -80.9 and 28.3 <= lat <= 28.85):
            skipped += 1
            continue
        tract = lookup_income(lon, lat, tract_features, tract_income)
        block_group = lookup_income(lon, lat, bg_features, bg_income)
        traffic = nearest_aadt(lon, lat, roads)
        owner1 = clean_str(attrs.get("NAME1"))
        owner2 = clean_str(attrs.get("NAME2"))
        mailing = {
            "line1": clean_str(attrs.get("ADD1")),
            "line2": clean_str(attrs.get("ADD2")),
            "city": clean_str(attrs.get("CITY")),
            "state": clean_str(attrs.get("STATE")),
            "zip": clean_str(attrs.get("ZIP")),
        }
        parcel_features.append(
            {
                "type": "Feature",
                "id": pid,
                "geometry": geometry,
                "properties": {
                    "id": pid,
                    "parcelId": pid,
                    "situsAddress": clean_str(attrs.get("SITUS")),
                    "situsCity": clean_str(attrs.get("CITY_SITUS")),
                    "situsZip": clean_str(attrs.get("ZIP_SITUS")),
                    "jurisdictionCode": clean_str(attrs.get("CITY_CODE")),
                    "ownerName": owner1,
                    "ownerName2": owner2,
                    "propertyName": clean_str(attrs.get("PROP_NAME")),
                    **parse_zoning(clean_str(attrs.get("ZONING_CODE"))),
                    "dorCode": clean_str(attrs.get("DOR_CODE")),
                    "acreage": attrs.get("ACREAGE"),
                    "centroid": [round(lon, 6), round(lat, 6)],
                    "lastSale": {
                        "date": epoch_to_iso(attrs.get("SALE_DATE")),
                        "price": attrs.get("SALE_ADJ_VALUE") if epoch_to_iso(attrs.get("SALE_DATE")) else None,
                        "qualified": clean_str(attrs.get("QUAL_CODE")),
                    },
                    "tax": {
                        "marketValue": attrs.get("TOTAL_MKT"),
                        "assessedValue": attrs.get("TOTAL_ASSD"),
                        "taxableValue": attrs.get("TAXABLE"),
                        "taxes": attrs.get("TAXES"),
                    },
                    "mailingAddress": mailing,
                    "incomeTract": tract,
                    "incomeBlockGroup": block_group,
                    "nearestRoad": traffic,
                    "flu": None,
                    "source": "ocpa-webmap-parcels-fixture",
                },
            }
        )

    parcel_collection = {
        "type": "FeatureCollection",
        "name": "orange-county-parcels-pilot",
        "features": parcel_features,
    }
    traffic_collection = {
        "type": "FeatureCollection",
        "name": "orange-county-aadt-major-roads",
        "features": traffic_features,
    }

    def income_fc(incomes: dict[str, dict], geo: dict, name: str) -> dict:
        out_feats = []
        for feat in geo.get("features") or []:
            props = feat.get("properties") or {}
            raw_id = str(props.get("full_geoid") or props.get("geoid") or "")
            geoid = geoid_from_censusreporter(raw_id)
            income = incomes.get(geoid) or {}
            geom = feat.get("geometry")
            if not geom:
                continue
            # Keep a light overlay: skip huge geometry fidelity by simplifying polygons
            if geom.get("type") == "Polygon":
                geom = {
                    "type": "Polygon",
                    "coordinates": [simplify_line(ring, 0.00035) if i == 0 else ring for i, ring in enumerate(geom["coordinates"])],
                }
            elif geom.get("type") == "MultiPolygon":
                geom = {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [simplify_line(poly[0], 0.00035), *poly[1:]] if poly else poly for poly in geom["coordinates"]
                    ],
                }
            out_feats.append(
                {
                    "type": "Feature",
                    "id": geoid,
                    "geometry": geom,
                    "properties": {
                        "geoid": geoid,
                        "name": income.get("name") or props.get("name"),
                        "medianHouseholdIncome": income.get("medianHouseholdIncome"),
                        "medianHouseholdIncomeMoe": income.get("medianHouseholdIncomeMoe"),
                    },
                }
            )
        return {"type": "FeatureCollection", "name": name, "features": out_feats}

    meta = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "county": "Orange County, FL",
        "countyFips": "12095",
        "parcelCount": len(parcel_features),
        "skippedParcels": skipped,
        "aadtSegmentCount": len(roads),
        "majorRoadOverlayCount": len(traffic_features),
        "censusRelease": "ACS 2024 5-year via Census Reporter",
        "sources": {
            "parcels": OCPA_URL.replace("/query", ""),
            "aadt": FDOT_URL.replace("/query", ""),
            "income": CENSUS_REPORTER_DATA,
        },
        "notes": [
            "Parcel attributes and polygons come from the public OCPA ArcGIS FeatureServer.",
            "AADT is the nearest FDOT Orange County segment to the parcel centroid.",
            "Income is ACS median household income (B19013) assigned by point-in-polygon.",
            "FLU is joined afterward by npm run seed:flu (OC layer 21 + Orlando layer 83).",
            "This is a geographically mixed sample, not a complete county extract.",
        ],
    }

    (OUT / "parcels.geojson").write_text(json.dumps(parcel_collection, separators=(",", ":")))
    # Statewide tract income and FDOT segments live in the sidecar written by
    # scripts/seed_fl_signals.py. The Orange pilot seed must not replace them.
    if (OUT / "signals-meta.json").exists():
        print("Keeping income-tracts.geojson and traffic.geojson from seed_fl_signals.py")
    else:
        (OUT / "traffic.geojson").write_text(json.dumps(traffic_collection, separators=(",", ":")))
        (OUT / "income-tracts.geojson").write_text(
            json.dumps(income_fc(tract_income, tract_geo, "orange-county-acs-tracts"), separators=(",", ":"))
        )
    (OUT / "income-block-groups.geojson").write_text(
        json.dumps(income_fc(bg_income, bg_geo, "orange-county-acs-block-groups"), separators=(",", ":"))
    )
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({"parcels": len(parcel_features), "skipped": skipped, "aadt": len(roads), "overlay": len(traffic_features)}, indent=2))
    print("Next: python3 scripts/join_flu.py && python3 scripts/seed_zoning.py")


if __name__ == "__main__":
    main()
