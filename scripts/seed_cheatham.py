#!/usr/bin/env python3
"""Cheatham County, Tennessee (FIPS 47021) parcel extract.

Preferred source is APSU CheatGIS MapServer/9. Comptroller COUNTY_ID is 11
and JUR is 011 — not FIPS 021. Acreage band is inclusive calc_acre 5–150,
parcel_typ 1. Zoning is cities-first (community polygon, then that city's
zoning layer). Unincorporated parcels use county zoning only. Future land
use stays null: growth layers are not entitlement.

IMPACT Parcels/0 and Themes/12 are siblings if APSU is unreachable. This
script does not call them when CheatGIS answers. It does not touch other
counties.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from parcel_geometry import _inside_polygon, polygon_parts, representative_point, signed_area
from seed_market_parcels import (
    COUNTY_DIR,
    MARKET_DIR,
    OUT_DIR,
    ROOT,
    clean,
    county_row,
    empty_feature,
    fetch_by_ids,
    fetch_object_ids,
    in_band,
    num,
    plausible_centroid,
    rings_to_feature_geometry,
    write_tiles,
    zip_str,
)

FIPS = "47021"
SOURCE = "apsu-cheatgis-47021"
SERVICE = "https://apnsgis4.apsu.edu/arcgis/rest/services/Cheatham/CheatGIS/MapServer"
PARCEL_URL = f"{SERVICE}/9/query"
WHERE = "parcel_typ=1 AND calc_acre>=5 AND calc_acre<=150"
COMPTROLLER_COUNTY_ID = 11
CACHE = Path("/tmp/dls-cheatham")

# County boundary extent (CheatGIS/14, 2026-09-23) with a small pad.
# Rejects the old COUNTY_ID=21 pull (DeKalb-side longitudes) and out-of-state twins.
BBOX = (-87.32, 36.02, -86.88, 36.48)

REJECTED_TWINS = [
    "Ashland County, Wisconsin (gis.ashlandcountywi.gov)",
    "Ashland County, Ohio",
    "City of Ashland, Kentucky (ashlandky.gov)",
    "Chatham County misspellings (NC/GA and other states)",
]

GAPS = [
    "Future land use is an honest REST gap for Cheatham County, Ashland City, Pleasant View, Kingston Springs, and Pegram. CheatGIS urban growth and Cheatham Growth layers are guidance only and are not parcel FLU or zoning entitlement.",
    "Zoning is a cities-first polygon join on APSU CheatGIS: Ashland City, Pleasant View, Kingston Springs, and Pegram inside their community limits, then unincorporated Cheatham zoning. City district codes are not applied outside those limits. The parcel zoning attribute is often blank and is not the district.",
    "Rejected twins: Ashland County, Wisconsin; Ashland County, Ohio; City of Ashland, Kentucky; and Chatham County misspellings. IMPACT COUNTY_ID is 11 and JUR is 011 (Comptroller), not FIPS 021. This extract is APSU CheatGIS MapServer/9, parcel_typ 1, calc_acre 5–150.",
]

FEATURE_GAPS = [
    "No public future land use polygons for Cheatham County or its cities. Urban growth boundaries are not zoning or FLU.",
]

PARCEL_FIELDS = [
    "objectid",
    "county_id",
    "parcel_typ",
    "gislink",
    "parcelid",
    "id",
    "calc_acre",
    "owner",
    "owner2",
    "mailaddr",
    "mailcity",
    "state",
    "zip",
    "address",
    "city",
    "landmktval",
    "impval",
    "appraisal",
    "assessment",
    "saledate",
    "price",
    "landuse",
]

# Communities layer names -> jurisdiction. Prefixes are local to this county.
CITIES = {
    "ASHLAND CITY": {"prefix": "ASH", "label": "Ashland City", "layer": 20, "code": "zone", "desc": "zoning"},
    "PLEASANT VIEW": {"prefix": "PVW", "label": "Pleasant View", "layer": 23, "code": "zone", "desc": "zoning"},
    "KINGSTON SPRINGS": {"prefix": "KGS", "label": "Kingston Springs", "layer": 19, "code": "zone", "desc": None},
    "PEGRAM": {"prefix": "PEG", "label": "Pegram", "layer": 22, "code": "zone", "desc": "zoning"},
}
COUNTY_ZONE = {"prefix": "CHE", "label": "Unincorporated Cheatham County", "layer": 21, "code": "zone_", "desc": "zoning"}

CITY_ATTR = {
    "030": "ASHLAND CITY",
    "583": "PLEASANT VIEW",
    "384": "KINGSTON SPRINGS",
    "574": "PEGRAM",
}


def positive(value: Any) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def iso_date(value: Any) -> str | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    seconds = parsed / 1000 if parsed > 10_000_000_000 else parsed
    if seconds < 0 or seconds > 4_102_444_800:
        return None
    try:
        stamp = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    if stamp.year < 1900 or stamp.year > 2100:
        return None
    return stamp.strftime("%Y-%m-%d")


def split_embedded_zone(raw: str | None) -> tuple[str | None, str | None]:
    """Kingston Springs stores code and description in one `zone` string."""
    text = clean(raw)
    if not text:
        return None, None
    if " - " in text:
        code, _, rest = text.partition(" - ")
        return clean(code), text
    if "-" in text and not re.match(r"^[A-Z]{1,3}-", text):
        code, _, _rest = text.partition("-")
        return clean(code), text
    return text, text


def city_attribute(raw: Any) -> str | None:
    text = clean(raw)
    if not text or text == "000":
        return None
    code = text.split(" ", 1)[0]
    return CITY_ATTR.get(code)


def prepare_geometry(geometry: dict | None) -> list[dict]:
    parts: list[dict] = []
    if not geometry:
        return parts
    for poly in polygon_parts(geometry):
        if not poly or not poly[0]:
            continue
        ring = poly[0]
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        parts.append(
            {
                "bbox": (min(xs), min(ys), max(xs), max(ys)),
                "poly": poly,
                "area": abs(signed_area(ring)),
            }
        )
    return parts


def covers(parts: list[dict], x: float, y: float) -> bool:
    for part in parts:
        minx, miny, maxx, maxy = part["bbox"]
        if x < minx or x > maxx or y < miny or y > maxy:
            continue
        if _inside_polygon(x, y, part["poly"]):
            return True
    return False


def sample_points(geometry: dict, rep: tuple[float, float]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = [rep]
    for poly in polygon_parts(geometry):
        ring = poly[0][:-1] if poly and len(poly[0]) > 1 else []
        if len(ring) < 3:
            continue
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        points.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
        step = max(1, len(ring) // 8)
        points.extend((float(p[0]), float(p[1])) for p in ring[::step][:8])
    unique: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for point in points:
        key = (round(point[0], 6), round(point[1], 6))
        if key in seen:
            continue
        seen.add(key)
        unique.append(point)
    return unique[:12]


def load_layer(layer: int, fields: list[str]) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"layer-{layer}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        if cached:
            print(f"  cache layer {layer} ({len(cached)})", flush=True)
            return cached
    url = f"{SERVICE}/{layer}/query"
    ids = fetch_object_ids(url, "1=1")
    raw = fetch_by_ids(url, ids, fields, batch=60)
    path.write_text(json.dumps(raw))
    print(f"  layer {layer} features {len(raw)}", flush=True)
    return raw


def load_parcels() -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "parcels.json"
    if path.exists():
        cached = json.loads(path.read_text())
        if cached:
            print(f"  cache parcels ({len(cached)})", flush=True)
            return cached
    ids = fetch_object_ids(PARCEL_URL, WHERE)
    print(f"  parcel ids {len(ids)}", flush=True)
    raw = fetch_by_ids(PARCEL_URL, ids, PARCEL_FIELDS, batch=80)
    path.write_text(json.dumps(raw))
    return raw


def zones_from(raw: list[dict], code_field: str, desc_field: str | None) -> list[dict]:
    zones: list[dict] = []
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _acres = rings_to_feature_geometry(item.get("geometry"))
        parts = prepare_geometry(geometry)
        if not parts:
            continue
        if desc_field:
            code = clean(attrs.get(code_field))
            desc = clean(attrs.get(desc_field)) or code
        else:
            code, desc = split_embedded_zone(attrs.get(code_field))
        if not code:
            continue
        zones.append({"code": code, "description": desc, "parts": parts})
    return zones


def communities_from(raw: list[dict]) -> list[dict]:
    places: list[dict] = []
    for item in raw:
        attrs = item.get("attributes") or {}
        name = clean(attrs.get("name"))
        if name not in CITIES:
            continue
        geometry, _acres = rings_to_feature_geometry(item.get("geometry"))
        parts = prepare_geometry(geometry)
        if not parts:
            continue
        places.append({"name": name, "parts": parts, "area": sum(part["area"] for part in parts)})
    return places


def in_county_bbox(lon: float, lat: float) -> bool:
    west, south, east, north = BBOX
    return west <= lon <= east and south <= lat <= north


def zoning_hit(points: list[tuple[float, float]], allowed, zones: list[dict]) -> dict | None:
    for x, y in points:
        if not allowed(x, y):
            continue
        for zone in zones:
            if covers(zone["parts"], x, y):
                return zone
    return None


def build_features(raw: list[dict], communities: list[dict], zones_by_name: dict[str, list[dict]]) -> tuple[list[dict], dict]:
    by_id: dict[str, dict] = {}
    dropped = 0
    stats = {
        "sourceRows": len(raw),
        "outsideBbox": 0,
        "badCountyId": 0,
        "countyIdAnomalies": 0,
        "badGislink": 0,
        "attributeOutsideLimits": 0,
        "jurisdictions": {
            name: {"parcels": 0, "zoned": 0} for name in [*CITIES.keys(), "UNINCORPORATED"]
        },
    }
    for item in raw:
        attrs = item.get("attributes") or {}
        parcel_id = clean(attrs.get("gislink"))
        if not parcel_id or not parcel_id.startswith("011"):
            stats["badGislink"] += 1
            dropped += 1
            continue
        county_id = int(attrs.get("county_id") or 0)
        if county_id != COMPTROLLER_COUNTY_ID:
            # A few CheatGIS rows leave county_id blank or stale. The 011 GIS link
            # on this county service is the Cheatham key; out-of-county twins do not use it.
            stats["countyIdAnomalies"] += 1
            if county_id not in {0, COMPTROLLER_COUNTY_ID}:
                stats["badCountyId"] += 1
        if int(attrs.get("parcel_typ") or 0) != 1:
            dropped += 1
            continue
        acres = num(attrs.get("calc_acre"))
        if not in_band(acres):
            dropped += 1
            continue
        geometry, _computed = rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            dropped += 1
            continue
        center = representative_point(geometry)
        if not center or not plausible_centroid(center) or not in_county_bbox(center[0], center[1]):
            stats["outsideBbox"] += 1
            dropped += 1
            continue
        points = sample_points(geometry, center)
        city_hits = [place for place in communities if covers(place["parts"], center[0], center[1])]
        city_hits.sort(key=lambda place: place["area"])
        city_name = city_hits[0]["name"] if city_hits else None
        attr_city = city_attribute(attrs.get("city"))
        if attr_city and attr_city != city_name:
            stats["attributeOutsideLimits"] += 1
        if city_name:
            spec = CITIES[city_name]
            city_parts = next(place["parts"] for place in communities if place["name"] == city_name)

            def inside_city(x: float, y: float, parts: list[dict] = city_parts) -> bool:
                return covers(parts, x, y)

            zone = zoning_hit(points, inside_city, zones_by_name[city_name])
        else:
            spec = COUNTY_ZONE

            def outside_cities(x: float, y: float) -> bool:
                return not any(covers(place["parts"], x, y) for place in communities)

            zone = zoning_hit(points, outside_cities, zones_by_name["UNINCORPORATED"])
        price = positive(attrs.get("price"))
        feature = empty_feature(
            fips=FIPS,
            county="Cheatham",
            state="Tennessee",
            markets=["Nashville"],
            parcel_id=parcel_id,
            acreage=acres,  # type: ignore[arg-type]
            geometry=geometry,
            center=center,
            source=SOURCE,
            owner=clean(attrs.get("owner")),
            situs=clean(attrs.get("address")),
            city=spec["label"] if city_name else "Unincorporated Cheatham County",
            zoning=zone["code"] if zone else None,
            dor=clean(attrs.get("landuse")),
            sale_price=price,
            sale_date=iso_date(attrs.get("saledate")),
            market_value=positive(attrs.get("appraisal")),
            assessed=positive(attrs.get("assessment")),
            mail1=clean(attrs.get("mailaddr")),
            mail_city=clean(attrs.get("mailcity")),
            mail_state=clean(attrs.get("state")),
            mail_zip=zip_str(attrs.get("zip")),
        )
        props = feature["properties"]
        props["ownerName2"] = clean(attrs.get("owner2"))
        props["zoningDistrict"] = zone["description"] if zone else None
        props["jurisdictionCode"] = spec["prefix"]
        props["jurisdictionPrefix"] = spec["prefix"]
        props["flu"] = None
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        props["appraiserUrl"] = f"https://assessment.cot.tn.gov/TPAD/Parcel/GIS?GISlink={quote(parcel_id)}"
        props["dataGaps"] = list(FEATURE_GAPS)
        previous = by_id.get(parcel_id)
        if previous is None or (props["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    prefix_to_name = {spec["prefix"]: name for name, spec in CITIES.items()}
    prefix_to_name[COUNTY_ZONE["prefix"]] = "UNINCORPORATED"
    for bucket in stats["jurisdictions"].values():
        bucket["parcels"] = 0
        bucket["zoned"] = 0
    for feature in features:
        key = prefix_to_name[feature["properties"]["jurisdictionPrefix"]]
        bucket = stats["jurisdictions"][key]
        bucket["parcels"] += 1
        if feature["properties"]["zoningCode"]:
            bucket["zoned"] += 1
    stats["kept"] = len(features)
    stats["dropped"] = dropped
    for bucket in stats["jurisdictions"].values():
        parcels = bucket["parcels"]
        bucket["rate"] = round(bucket["zoned"] / parcels, 4) if parcels else None
    return features, stats


def publish_nashville(row: dict) -> None:
    meta_path = MARKET_DIR / "nashville" / "meta.json"
    meta = json.loads(meta_path.read_text())
    for county in meta["counties"]:
        if county.get("fips") != FIPS:
            continue
        county["featureCount"] = row["featureCount"]
        county["coverage"] = row["coverage"]
        county["partition"] = row["partition"]
        county["minAcres"] = row["minAcres"]
        county["maxAcres"] = row["maxAcres"]
        county["source"] = row["source"]
        county["queryUrl"] = row["queryUrl"]
        county["gaps"] = row["gaps"]
        county["path"] = row["path"]
        county["lookup"] = row["lookup"]
        county["tileCount"] = row["tileCount"]
        county["sourceCount"] = row["sourceCount"]
    meta["parcelCount"] = sum(int(county.get("featureCount") or 0) for county in meta["counties"])
    meta["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")

    index_path = OUT_DIR / "index.json"
    index = json.loads(index_path.read_text())
    nashville = index["markets"]["Nashville"]
    nashville["parcelCount"] = meta["parcelCount"]
    for county in nashville["counties"]:
        if county.get("fips") != FIPS:
            continue
        county["featureCount"] = row["featureCount"]
        county["coverage"] = row["coverage"]
        county["minAcres"] = row["minAcres"]
        county["maxAcres"] = row["maxAcres"]
        county["gaps"] = list(row["gaps"] or [])[:2]
    index["generatedAt"] = meta["generatedAt"]
    index_path.write_text(json.dumps(index, indent=2) + "\n")

    count = int(row["featureCount"])
    parcel_total = int(meta["parcelCount"])
    cheatham_line = f"| Cheatham | Tennessee | 47021 | complete-gte-5ac | {count:,} | {SOURCE} |"
    for path in (OUT_DIR / "coverage.md", ROOT / "docs" / "market-parcels.md"):
        text = path.read_text()
        text = re.sub(
            r"\| Nashville \| primary \| [0-9,]+ \| 6 \| 0 \| 11 \|",
            f"| Nashville | primary | {parcel_total:,} | 6 | 0 | 11 |",
            text,
            count=1,
        )
        text = re.sub(
            r"\| Cheatham \| Tennessee \| 47021 \| complete-gte-5ac \| [0-9,]+ \| [^|\n]+ \|",
            cheatham_line,
            text,
            count=1,
        )
        path.write_text(text)
    print(f"  Nashville parcel count {parcel_total}", flush=True)


def seed_cheatham(markets: list[str] | None = None) -> dict:
    markets = markets or ["Nashville"]
    print("Pulling Cheatham County TN (47021) from APSU CheatGIS MapServer/9", flush=True)
    parcels = load_parcels()
    community_raw = load_layer(24, ["name"])
    communities = communities_from(community_raw)
    found = {place["name"] for place in communities}
    missing = [name for name in CITIES if name not in found]
    if missing:
        raise RuntimeError(f"Communities layer missing {missing}")
    zones_by_name: dict[str, list[dict]] = {}
    for name, spec in CITIES.items():
        fields = [spec["code"]] + ([spec["desc"]] if spec["desc"] else [])
        zones_by_name[name] = zones_from(load_layer(spec["layer"], fields), spec["code"], spec["desc"])
        print(f"  {name} zoning polygons {len(zones_by_name[name])}", flush=True)
    zones_by_name["UNINCORPORATED"] = zones_from(
        load_layer(COUNTY_ZONE["layer"], [COUNTY_ZONE["code"], COUNTY_ZONE["desc"]]),
        COUNTY_ZONE["code"],
        COUNTY_ZONE["desc"],
    )
    print(f"  county zoning polygons {len(zones_by_name['UNINCORPORATED'])}", flush=True)
    features, stats = build_features(parcels, communities, zones_by_name)
    if not features:
        raise RuntimeError("Cheatham extract kept zero parcels")
    if any(not in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Cheatham extract emitted a parcel outside 5–150 acres")
    gaps = list(GAPS)
    if stats["sourceRows"] != len(features):
        gaps.append(
            f"{stats['sourceRows']} CheatGIS rows in the parcel_typ=1 and calc_acre 5–150 query collapsed to {len(features)} GIS links. "
            f"{stats['countyIdAnomalies']} kept rows have a blank or non-11 county_id but an 011 GIS link on the Cheatham service."
        )
    county = {"name": "Cheatham", "fips": FIPS, "state": "Tennessee"}
    path, lookup, tiles = write_tiles(county, features)
    row = county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=SOURCE,
        query_url=PARCEL_URL,
        gaps=gaps,
        source_count=stats["sourceRows"],
        dropped=stats["sourceRows"] - len(features),
        tile_count=tiles,
    )
    row["comptrollerCountyId"] = COMPTROLLER_COUNTY_ID
    row["comptrollerJur"] = "011"
    row["rejectedTwins"] = list(REJECTED_TWINS)
    row["zoningJoin"] = stats["jurisdictions"]
    row["attributeOutsideCityLimits"] = stats["attributeOutsideLimits"]
    row["countyIdAnomalies"] = stats["countyIdAnomalies"]
    row["flu"] = "gap"
    (COUNTY_DIR / FIPS / "county.json").write_text(json.dumps(row, indent=2) + "\n")
    publish_nashville(row)
    print(json.dumps({"kept": len(features), "zoningJoin": stats["jurisdictions"], "dropped": stats}, indent=2), flush=True)
    return row


if __name__ == "__main__":
    try:
        seed_cheatham()
    except Exception as exc:  # noqa: BLE001
        print(f"Cheatham ingest failed: {exc}", file=sys.stderr)
        raise
