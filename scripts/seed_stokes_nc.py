#!/usr/bin/env python3
"""Stokes County, NC (FIPS 37169) parcel tiles for the Winston-Salem market.

Public GIS only. Pages follow each layer's maxRecordCount, capped at 2000.

  Parcels   https://stokescountygis.com/server/rest/services/AllLayers/MapServer/24
  Zoning    AllLayers/MapServer/27
  FLU       WebApp2026/MapServer/34  (Land Use 2035)
  King QA   https://www.webgis.net/arcgis/rest/services/NC/CityOfKing/MapServer/7
  OneMap QA NC1Map_Parcels cntyfips='169'

Acreage band is CALCULATED_ACREAGE 5.0–150.0 inclusive. OZ 2.0 eligibility
(Rev. Proc. 2026-14, 2020 tracts) is stored on oz2Eligibility and is never
written as a designated QOZ. Designated status is the HUD 2010 tract join only.

  python3 scripts/seed_stokes_nc.py
"""

from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from pathlib import Path

from join_oz import point_in_geometry
from parcel_geometry import esri_rings_to_geojson, signed_area
from seed_market_parcels import (
    CATALOG_PATH,
    COUNTY_DIR,
    MAX_ACRES,
    MIN_ACRES,
    OUT_DIR,
    ROOT,
    centroid_of,
    clean,
    county_row,
    empty_feature,
    fetch_json,
    in_band,
    num,
    plausible_centroid,
    rings_to_feature_geometry,
    write_tiles,
    zip_str,
)

FIPS = "37169"
SOURCE = "nc-stokes-alllayers-24"
PAGE_CAP = 2000
PARCEL_URL = "https://stokescountygis.com/server/rest/services/AllLayers/MapServer/24/query"
ZONING_URL = "https://stokescountygis.com/server/rest/services/AllLayers/MapServer/27/query"
FLU_URL = "https://stokescountygis.com/server/rest/services/WebApp2026/MapServer/34/query"
KING_URL = "https://www.webgis.net/arcgis/rest/services/NC/CityOfKing/MapServer/7/query"
ONEMAP_URL = "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1/query"
HUD_OZ_URL = "https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/FeatureServer/13/query"
ELIGIBLE_PACK = ROOT / "data" / "fixtures" / "oz2-eligible-packs.geojson"
NOTICE_PATH = ROOT / "data" / "fixtures" / "notice-2025-50-rural-geoids.json"
OTHER_MSAS = ROOT / "data" / "fixtures" / "oz2-other-msas.json"
DOC_PATH = ROOT / "docs" / "stokes-nc-parcels.md"

PARCEL_WHERE = "CALCULATED_ACREAGE>=5 AND CALCULATED_ACREAGE<=150"
PARCEL_FIELDS = ",".join(
    [
        "OBJECTID",
        "PIN",
        "PARCEL_NUMBER",
        "PHYSICAL_ADDRESS",
        "PHYS_ADDR_CITY",
        "PHYS_ADDR_ZIP",
        "PROPERTY_OWNER_1",
        "PROPERTY_OWNER_2",
        "OWNER_MAIL_ADDR_1",
        "OWNER_MAIL_ADDR_2",
        "OWNER_MAIL_ADDR_CITY",
        "OWNER_MAIL_ADDR_STATE",
        "OWNER_MAIL_ADDR_ZIP",
        "CALCULATED_ACREAGE",
        "DEEDED_ACREAGE",
        "ZONING",
        "PLANNING_JURIS",
        "TOTAL_PROPERTY_VALUE",
        "TOTAL_LAND_VAL_ASSESSED",
        "TOTAL_BLDG_VAL_ASSESSED",
        "PACKAGE_SALE_DATE",
        "PACKAGE_SALE_PRICE",
        "LAND_SALE_DATE",
        "LAND_SALE_PRICE",
    ]
)


def layer_max_records(query_url: str) -> int:
    meta_url = query_url.replace("/query", "")
    meta = fetch_json(meta_url, {"f": "json"}, timeout=60)
    raw = meta.get("maxRecordCount") or PAGE_CAP
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return PAGE_CAP


def page_size_for(query_url: str) -> int:
    return min(PAGE_CAP, layer_max_records(query_url))


def epoch_to_iso(value: object) -> str | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    seconds = parsed / 1000.0 if parsed > 10_000_000_000 else parsed
    if seconds < 31536000:
        return None
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(seconds))
    except (OverflowError, ValueError, OSError):
        return None


def money(value: object) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def paginate(
    url: str,
    where: str,
    out_fields: str,
    *,
    geometry: bool,
    oid_field: str,
    page_size: int,
    label: str,
    max_allowable_offset: float | None = None,
) -> list[dict]:
    rows: list[dict] = []
    seen: set[object] = set()
    offset = 0
    while True:
        params = {
            "where": where,
            "outFields": out_fields,
            "returnGeometry": "true" if geometry else "false",
            "orderByFields": oid_field,
            "resultOffset": str(offset),
            "resultRecordCount": str(page_size),
            "f": "json",
        }
        if geometry:
            params["outSR"] = "4326"
            if max_allowable_offset is not None:
                params["maxAllowableOffset"] = str(max_allowable_offset)
                params["geometryPrecision"] = "5"
        data = fetch_json(url, params, timeout=180)
        if data.get("error"):
            raise RuntimeError(f"{label} page offset {offset}: {json.dumps(data['error'])[:300]}")
        feats = data.get("features") or []
        if not feats:
            break
        first = (feats[0].get("attributes") or {}).get(oid_field)
        if first in seen:
            raise RuntimeError(f"{label} pagination repeated OBJECTID {first} at offset {offset}")
        fresh = 0
        for feat in feats:
            oid = (feat.get("attributes") or {}).get(oid_field)
            if oid in seen:
                continue
            seen.add(oid)
            rows.append(feat)
            fresh += 1
        print(f"  {label} {len(rows)}", flush=True)
        if len(feats) < page_size:
            break
        offset += len(feats)
        if offset > 250000:
            raise RuntimeError(f"{label} pagination ran away")
        time.sleep(0.05)
        if fresh == 0:
            break
    return rows


def count_only(url: str, where: str) -> int:
    data = fetch_json(url, {"where": where, "returnCountOnly": "true", "f": "json"})
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    count = data.get("count")
    if not isinstance(count, int):
        raise RuntimeError(f"No count from {url}")
    return count


def geom_area(geometry: dict) -> float:
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon" and coords:
        return abs(signed_area(coords[0]))
    if kind == "MultiPolygon":
        return sum(abs(signed_area(poly[0])) for poly in coords if poly)
    return 0.0


def geometry_bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: object) -> None:
        if isinstance(node, (list, tuple)) and node and isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        if isinstance(node, list):
            for child in node:
                walk(child)

    walk(geometry.get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


class GridIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = geometry_bbox(feature.get("geometry") or {})
        if not bbox:
            return
        west, south, east, north = bbox
        ix0, iy0 = int(west // self.cell), int(south // self.cell)
        ix1, iy1 = int(east // self.cell), int(north // self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 400:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, lon: float, lat: float) -> dict | None:
        ix, iy = int(lon // self.cell), int(lat // self.cell)
        found: list[dict] = []
        for feature in self.buckets.get((ix, iy), []):
            if point_in_geometry(lon, lat, feature.get("geometry")):
                found.append(feature)
        for feature in self.broad:
            if point_in_geometry(lon, lat, feature.get("geometry")):
                found.append(feature)
        if not found:
            return None
        return min(found, key=lambda item: item.get("area") or 1e18)


def index_polygons(raw: list[dict], label_fn) -> GridIndex:
    index = GridIndex(0.02)
    kept = 0
    for item in raw:
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        payload = label_fn(item.get("attributes") or {})
        if not geometry or not payload:
            continue
        index.add({"geometry": geometry, "properties": payload, "area": geom_area(geometry)})
        kept += 1
    print(f"  indexed {kept}", flush=True)
    return index


def zoning_payload(attrs: dict) -> dict | None:
    code = clean(attrs.get("ZONING"))
    if not code:
        return None
    return {
        "code": code,
        "jurisdiction": clean(attrs.get("ZONING_JURI")),
        "area": clean(attrs.get("ZONE_AREA")),
    }


def flu_payload(attrs: dict) -> dict | None:
    code = clean(attrs.get("LUP_CODE"))
    if not code:
        return None
    return {
        "code": code,
        "label": clean(attrs.get("LUP_DESC")) or code,
        "jurisdiction": clean(attrs.get("ZONING_JUR")) or clean(attrs.get("ZONE_AREA")),
        "source": "stokes-webapp2026-land-use-2035",
    }


def pick_sale(attrs: dict) -> tuple[float | None, str | None]:
    options: list[tuple[str, float, str | None]] = []
    for date_key, price_key in (
        ("PACKAGE_SALE_DATE", "PACKAGE_SALE_PRICE"),
        ("LAND_SALE_DATE", "LAND_SALE_PRICE"),
    ):
        price = money(attrs.get(price_key))
        if price is None:
            continue
        sold = epoch_to_iso(attrs.get(date_key))
        options.append((sold or "", price, sold))
    if not options:
        return None, None
    options.sort()
    _key, price, sold = options[-1]
    return price, sold


def tract_name(tract: str | None, geoid: str) -> str:
    digits = "".join(ch for ch in (tract or "") if ch.isdigit()) or (geoid[-6:] if len(geoid) >= 6 else "")
    if not digits:
        return geoid or "Opportunity Zone"
    value = int(digits)
    pretty = str(value // 100) if value % 100 == 0 else f"{value / 100:.2f}".rstrip("0")
    return f"Census tract {pretty}"


def load_eligible() -> list[dict]:
    pack = json.loads(ELIGIBLE_PACK.read_text())
    catalog = json.loads(OTHER_MSAS.read_text())
    catalog_ids = {
        str(row.get("geoid"))
        for row in catalog.get("rows") or catalog.get("tracts") or []
        if row.get("county") == "Stokes" and row.get("state") == "North Carolina"
    }
    # oz2-other-msas.json stores tracts under "tracts" in some builds and a flat list in others.
    if not catalog_ids:
        rows = catalog.get("features") or catalog.get("items") or []
        if isinstance(catalog, dict):
            for value in catalog.values():
                if isinstance(value, list) and value and isinstance(value[0], dict) and "geoid" in value[0]:
                    rows = value
                    break
        catalog_ids = {
            str(row.get("geoid"))
            for row in rows
            if isinstance(row, dict) and row.get("county") == "Stokes" and row.get("state") == "North Carolina"
        }
    zones = []
    for feature in pack.get("features") or []:
        props = feature.get("properties") or {}
        geoid = str(props.get("tractGeoid") or "")
        if not geoid.startswith(FIPS):
            continue
        if props.get("designation") != "eligible-for-nomination":
            raise RuntimeError(f"{geoid} is not marked eligible-for-nomination in the OZ 2.0 pack")
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise RuntimeError(f"{geoid} is missing a polygon")
        zones.append(
            {
                "geoid": geoid,
                "name": props.get("name") or geoid,
                "rural": props.get("rural") is True,
                "statusChip": props.get("statusChip") or "Eligible — not designated",
                "geometry": geometry,
            }
        )
    found = {zone["geoid"] for zone in zones}
    if catalog_ids and found != catalog_ids:
        raise RuntimeError(f"Stokes eligible pack {sorted(found)} != catalog {sorted(catalog_ids)}")
    if len(zones) < 1:
        raise RuntimeError("No Stokes OZ 2.0 eligible tract polygons in oz2-eligible-packs.geojson")
    return zones


def load_designated() -> list[dict]:
    data = fetch_json(
        HUD_OZ_URL,
        {
            "where": "STATE='37' AND COUNTY='169'",
            "outFields": "GEOID10,TRACT,STATE,COUNTY",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
        timeout=120,
    )
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    notice = set(json.loads(NOTICE_PATH.read_text()).get("geoids") or [])
    zones = []
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        geoid = str(props.get("GEOID10") or props.get("geoid") or "").strip()
        geometry = feature.get("geometry") or {}
        if not geoid or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            continue
        zones.append(
            {
                "geoid": geoid,
                "name": tract_name(str(props.get("TRACT") or ""), geoid),
                "rural": geoid in notice,
                "geometry": geometry,
            }
        )
    if not zones:
        raise RuntimeError("HUD Opportunity Zones returned no Stokes County (37169) designated tracts")
    return zones


def hit_zone(lon: float, lat: float, zones: list[dict]) -> dict | None:
    for zone in zones:
        if point_in_geometry(lon, lat, zone.get("geometry")):
            return zone
    return None


def normalize_parcels(raw: list[dict], county: dict, markets: list[str]) -> tuple[list[dict], int]:
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed = rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            dropped += 1
            continue
        center = centroid_of(geometry)
        if not plausible_centroid(center):
            dropped += 1
            continue
        acres = num(attrs.get("CALCULATED_ACREAGE"))
        if not in_band(acres):
            dropped += 1
            continue
        parcel_id = clean(attrs.get("PIN"))
        if not parcel_id:
            dropped += 1
            continue
        price, sold = pick_sale(attrs)
        assessed_parts = [money(attrs.get("TOTAL_LAND_VAL_ASSESSED")), money(attrs.get("TOTAL_BLDG_VAL_ASSESSED"))]
        assessed = sum(part for part in assessed_parts if part is not None) or None
        feature = empty_feature(
            fips=FIPS,
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,  # type: ignore[arg-type]
            source=SOURCE,
            owner=clean(attrs.get("PROPERTY_OWNER_1")),
            situs=clean(attrs.get("PHYSICAL_ADDRESS")),
            city=clean(attrs.get("PHYS_ADDR_CITY")),
            zip_code=zip_str(attrs.get("PHYS_ADDR_ZIP")),
            zoning=clean(attrs.get("ZONING")),
            sale_price=price,
            sale_date=sold,
            market_value=money(attrs.get("TOTAL_PROPERTY_VALUE")),
            assessed=assessed,
            mail1=clean(attrs.get("OWNER_MAIL_ADDR_1")),
            mail2=clean(attrs.get("OWNER_MAIL_ADDR_2")),
            mail_city=clean(attrs.get("OWNER_MAIL_ADDR_CITY")),
            mail_state=clean(attrs.get("OWNER_MAIL_ADDR_STATE")),
            mail_zip=zip_str(attrs.get("OWNER_MAIL_ADDR_ZIP")),
        )
        props = feature["properties"]
        props["ownerName2"] = clean(attrs.get("PROPERTY_OWNER_2"))
        juris = clean(attrs.get("PLANNING_JURIS"))
        props["jurisdictionCode"] = juris
        props["jurisdictionPrefix"] = juris
        props["_assessorZoning"] = clean(attrs.get("ZONING"))
        previous = by_id.get(parcel_id)
        if previous is None or (props.get("acreage") or 0) > (previous["properties"].get("acreage") or 0):
            by_id[parcel_id] = feature
        else:
            dropped += 1
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def join_polygons(features: list[dict], zoning: GridIndex, flu: GridIndex) -> dict[str, int]:
    stats = {
        "zoningJoined": 0,
        "zoningAssessorMismatch": 0,
        "zoningAssessorBlankFilled": 0,
        "zoningMissed": 0,
        "fluJoined": 0,
        "fluMissed": 0,
    }
    for index, feature in enumerate(features, start=1):
        if index == 1 or index % 2000 == 0 or index == len(features):
            print(f"  zoning/flu join {index}/{len(features)}", flush=True)
        props = feature["properties"]
        lon, lat = props["centroid"]
        zone = zoning.hit(lon, lat)
        assessor = props.pop("_assessorZoning", None)
        if zone:
            code = zone["properties"]["code"]
            props["zoningCode"] = code
            stats["zoningJoined"] += 1
            if assessor and assessor != code:
                stats["zoningAssessorMismatch"] += 1
            if not assessor:
                stats["zoningAssessorBlankFilled"] += 1
        else:
            props["zoningCode"] = assessor
            stats["zoningMissed"] += 1
        flu_hit = flu.hit(lon, lat)
        if flu_hit:
            props["flu"] = flu_hit["properties"]
            stats["fluJoined"] += 1
        else:
            props["flu"] = None
            stats["fluMissed"] += 1
    return stats


def join_zones(features: list[dict], eligible: list[dict], designated: list[dict]) -> dict[str, int]:
    eligible_ids = {zone["geoid"] for zone in eligible}
    designated_ids = {zone["geoid"] for zone in designated}
    if eligible_ids & designated_ids:
        raise RuntimeError(
            f"Eligible and designated GEOIDs overlap ({sorted(eligible_ids & designated_ids)}). Refusing to conflate them."
        )
    stats = {
        "eligibleParcels": 0,
        "designatedParcels": 0,
        "eligibleAlsoDesignated": 0,
        "sameGeoid": 0,
    }
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        elig = hit_zone(lon, lat, eligible)
        des = hit_zone(lon, lat, designated)
        if elig:
            props["oz2Eligibility"] = {
                "eligible": True,
                "rural": True if elig["rural"] else False,
                "tractGeoid": elig["geoid"],
                "tractName": elig["name"],
                "designation": "eligible-for-nomination",
                "source": "rev-proc-2026-14",
                "statusChip": elig["statusChip"],
            }
            stats["eligibleParcels"] += 1
        else:
            props["oz2Eligibility"] = {
                "eligible": False,
                "rural": None,
                "tractGeoid": None,
                "tractName": None,
                "designation": "not-eligible",
                "source": "rev-proc-2026-14",
                "statusChip": None,
            }
        if des:
            props["opportunityZone"] = {
                "inOpportunityZone": True,
                "tractGeoid": des["geoid"],
                "tractName": des["name"],
                "source": "hud-opportunity-zones-2010",
                "designatedRural": des["rural"],
            }
            stats["designatedParcels"] += 1
        else:
            props["opportunityZone"] = {
                "inOpportunityZone": False,
                "tractGeoid": None,
                "tractName": None,
                "source": "hud-opportunity-zones-2010",
                "designatedRural": None,
            }
        oz2 = props["oz2Eligibility"]
        oz = props["opportunityZone"]
        if oz2["eligible"] and oz["inOpportunityZone"]:
            stats["eligibleAlsoDesignated"] += 1
        if oz2.get("tractGeoid") and oz.get("tractGeoid") and oz2["tractGeoid"] == oz["tractGeoid"]:
            stats["sameGeoid"] += 1
        if oz2["eligible"] and oz2["designation"] != "eligible-for-nomination":
            raise RuntimeError("Eligible parcel was not labeled eligible-for-nomination")
        if oz2["eligible"] and oz.get("tractGeoid") == oz2["tractGeoid"]:
            raise RuntimeError(f"Eligible GEOID {oz2['tractGeoid']} was stored as the designated tract")
    if stats["sameGeoid"]:
        raise RuntimeError("A parcel reused one GEOID for eligibility and designation")
    return stats


def qa_onemap(pins: set[str], acres_by_pin: dict[str, float]) -> dict[str, int]:
    page = page_size_for(ONEMAP_URL)
    where = "cntyfips='169' AND gisacres>=5 AND gisacres<=150"
    expected = count_only(ONEMAP_URL, where)
    print(f"OneMap QA {expected} rows, page {page}", flush=True)
    raw = paginate(
        ONEMAP_URL,
        where,
        "objectid,parno,gisacres",
        geometry=False,
        oid_field="objectid",
        page_size=page,
        label="onemap",
    )
    onemap: dict[str, float] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        pin = clean(attrs.get("parno"))
        acres = num(attrs.get("gisacres"))
        if pin and acres is not None:
            onemap[pin] = acres
    only_county = pins - set(onemap)
    only_onemap = set(onemap) - pins
    acre_mismatch = 0
    for pin, gisacres in onemap.items():
        local = acres_by_pin.get(pin)
        if local is None:
            continue
        if abs(local - gisacres) > 0.05:
            acre_mismatch += 1
    return {
        "pageSize": page,
        "sourceCount": expected,
        "fetched": len(onemap),
        "countyOnly": len(only_county),
        "onemapOnly": len(only_onemap),
        "acreMismatch": acre_mismatch,
    }


def qa_king(pins: set[str], zoning_by_pin: dict[str, str | None]) -> dict[str, int]:
    page = page_size_for(KING_URL)
    where = "County='Stokes' AND CALCULATED_ACREAGE>=5 AND CALCULATED_ACREAGE<=150"
    expected = count_only(KING_URL, where)
    forsyth = count_only(KING_URL, "County='Forsyth'")
    print(f"King QA Stokes band {expected}, Forsyth excluded {forsyth}, page {page}", flush=True)
    raw = paginate(
        KING_URL,
        where,
        "OBJECTID,PIN,ZONING,County,CALCULATED_ACREAGE",
        geometry=False,
        oid_field="OBJECTID",
        page_size=page,
        label="king",
    )
    matched = 0
    missing = 0
    zoning_mismatch = 0
    forsyth_in_page = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        if clean(attrs.get("County")) == "Forsyth":
            forsyth_in_page += 1
            continue
        pin = clean(attrs.get("PIN"))
        if not pin or pin not in pins:
            missing += 1
            continue
        matched += 1
        king_zone = clean(attrs.get("ZONING"))
        local = zoning_by_pin.get(pin)
        if king_zone and local and king_zone != local:
            zoning_mismatch += 1
    return {
        "pageSize": page,
        "stokesBand": expected,
        "fetched": len(raw),
        "matched": matched,
        "missingFromCounty": missing,
        "zoningMismatch": zoning_mismatch,
        "forsythExcluded": forsyth,
        "forsythLeaked": forsyth_in_page,
    }


def build_gaps(
    *,
    source_count: int,
    kept: int,
    dropped: int,
    deeded_band: int,
    joins: dict[str, int],
    zones: dict[str, int],
    onemap: dict[str, int],
    king: dict[str, int],
    eligible_ids: list[str],
    designated_ids: list[str],
    parcel_page: int,
    zoning_page: int,
    flu_page: int,
) -> list[str]:
    gaps = [
        (
            "OZ 2.0 eligibility is not a designated QOZ. "
            f"Rev. Proc. 2026-14 tracts {', '.join(eligible_ids)} stay on oz2Eligibility as eligible-for-nomination. "
            f"Designated status is only the HUD 2010 join ({', '.join(designated_ids)}). "
            f"{zones['eligibleParcels']} centroids are eligible; {zones['designatedParcels']} are in a current designated tract; "
            f"{zones['eligibleAlsoDesignated']} sit in both geographies with different GEOIDs."
        ),
        (
            f"Stored acreage is Stokes CALCULATED_ACREAGE (GIS), the same figure NC OneMap publishes as gisacres. "
            f"DEEDED_ACREAGE in the numeric 5–150 band is {deeded_band:,} and is not the filter. "
            f"County query returned {source_count:,} rows; {kept:,} unique PINs were kept. "
            f"The other {source_count - kept:,} rows were duplicate PINs or failed the ring or centroid check."
        ),
        (
            f"Zoning is AllLayers/MapServer/27 (page size {zoning_page}), joined by centroid. "
            f"{joins['zoningJoined']:,} hit a polygon; {joins['zoningMissed']:,} did not and kept the assessor ZONING field when it was present. "
            f"{joins['zoningAssessorMismatch']:,} assessor codes disagree with the polygon; the polygon wins. "
            f"{joins['zoningAssessorBlankFilled']:,} blank assessor codes were filled from the polygon. "
            "Stokes codes are not in the Orange County multifamily zoning knowledge base."
        ),
        (
            f"Future land use is WebApp2026/MapServer/34 Land Use 2035 (requested page size {flu_page}). "
            "Ungeneralized geometry pages above about 200 features return HTTP 500, so the polygons are simplified with maxAllowableOffset 0.00008 degrees (about 8 meters) before the centroid join. "
            "This is not a separate municipal FLU layer. "
            f"{joins['fluJoined']:,} centroids hit a polygon; {joins['fluMissed']:,} have no FLU. "
            "King, Walnut Cove, Danbury, and other towns do not have a separate public FLU service wired here."
        ),
        (
            f"City of King WebGIS CityOfKing/MapServer/7 is a QA crosswalk, not the county roll. "
            f"Its maxRecordCount pages at {king['pageSize']} (the service cap; below the 2000 used for county layers). "
            f"{king['stokesBand']:,} King rows are Stokes and inside 5–150 calculated acres; {king['matched']:,} match a county PIN; "
            f"{king['missingFromCounty']:,} do not; {king['zoningMismatch']:,} zoning codes disagree. "
            f"{king['forsythExcluded']:,} Forsyth County parcels on that layer are excluded."
        ),
        (
            f"NC OneMap cntyfips='169' and gisacres 5–150 is a QA crosswalk (page size {onemap['pageSize']}), not the geometry source. "
            f"OneMap count {onemap['sourceCount']:,} ({onemap['fetched']:,} unique parnos); {onemap['countyOnly']:,} county PINs are absent there; "
            f"{onemap['onemapOnly']:,} OneMap parnos are absent from the county extract; "
            f"{onemap['acreMismatch']:,} shared PINs differ by more than 0.05 acres."
        ),
        (
            "No public Stokes parcel-search deep link was confirmed, so appraiserUrl is empty. "
            "LAND_CLASS is not a Florida DOR use code. Sale qualification is not on the county layer. "
            "Income and traffic are not joined. "
            f"County parcel pages use resultOffset at {parcel_page}, the AllLayers maxRecordCount."
        ),
    ]
    return gaps


def write_doc(gaps: list[str], qa: dict, kept: int) -> None:
    lines = [
        "# Stokes County, North Carolina (37169)",
        "",
        "Winston-Salem market. Public GIS only. Acreage band is **5.0–150.0** on county `CALCULATED_ACREAGE`.",
        "",
        f"Kept **{kept:,}** parcels from AllLayers/MapServer/24 (`{SOURCE}`).",
        "",
        "## Sources",
        "",
        "| Role | Service | Page size |",
        "| --- | --- | ---: |",
        f"| Parcels | `{PARCEL_URL.replace('/query', '')}` | {qa['parcelPageSize']} |",
        f"| Zoning | `{ZONING_URL.replace('/query', '')}` | {qa['zoningPageSize']} |",
        f"| Land Use 2035 | `{FLU_URL.replace('/query', '')}` | {qa['fluPageSize']} |",
        f"| King QA | `{KING_URL.replace('/query', '')}` | {qa['king']['pageSize']} |",
        f"| OneMap QA | `{ONEMAP_URL}` `cntyfips='169'` | {qa['onemap']['pageSize']} |",
        "",
        "Eligible OZ 2.0 tracts come from `data/fixtures/oz2-eligible-packs.geojson` (Rev. Proc. 2026-14). They are not designated. Designated tracts come from the HUD Opportunity Zones service (2010 census geography). Notice 2025-50 only flags whether a designated tract is rural.",
        "",
        "## Gaps",
        "",
    ]
    for gap in gaps:
        lines.append(f"- {gap}")
    lines.append("")
    DOC_PATH.write_text("\n".join(lines))


def patch_indexes(feature_count: int, gaps: list[str], source_count: int, tile_count: int) -> None:
    generated = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    index_path = OUT_DIR / "index.json"
    index = json.loads(index_path.read_text())
    market = index["markets"]["Winston-Salem"]
    entry = next(item for item in market["counties"] if item["fips"] == FIPS)
    old = int(entry["featureCount"])
    market["parcelCount"] = int(market["parcelCount"]) - old + feature_count
    entry["featureCount"] = feature_count
    entry["coverage"] = "complete-gte-5ac"
    entry["gaps"] = gaps[:2]
    index["generatedAt"] = generated
    index_path.write_text(json.dumps(index, indent=2) + "\n")

    meta_path = OUT_DIR / "markets" / "winston-salem" / "meta.json"
    meta = json.loads(meta_path.read_text())
    meta_entry = next(item for item in meta["counties"] if item["fips"] == FIPS)
    meta["parcelCount"] = int(meta["parcelCount"]) - int(meta_entry["featureCount"]) + feature_count
    meta["generatedAt"] = generated
    meta_entry.update(
        {
            "featureCount": feature_count,
            "coverage": "complete-gte-5ac",
            "source": SOURCE,
            "queryUrl": PARCEL_URL,
            "gaps": gaps,
            "sourceCount": source_count,
            "tileCount": tile_count,
        }
    )
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")

    winston_total = f"{market['parcelCount']:,}"
    stokes_row = f"| Stokes | North Carolina | 37169 | complete-gte-5ac | {feature_count:,} | {SOURCE} |"
    for path in (ROOT / "docs" / "market-parcels.md", OUT_DIR / "coverage.md"):
        text = path.read_text()
        text = re.sub(
            r"\| Stokes \| North Carolina \| 37169 \| complete-gte-5ac \| [0-9,]+ \| [^|\n]+ \|",
            stokes_row,
            text,
        )
        text = re.sub(
            r"\| Winston-Salem \| other \| [0-9,]+ \| 9 \| 0 \| 0 \|",
            f"| Winston-Salem | other | {winston_total} | 9 | 0 | 0 |",
            text,
        )
        path.write_text(text)


def seed_stokes_county(county: dict, markets: list[str]) -> dict:
    print(f"Pulling Stokes NC ({FIPS}) from county GIS", flush=True)
    parcel_page = page_size_for(PARCEL_URL)
    zoning_page = page_size_for(ZONING_URL)
    flu_page = page_size_for(FLU_URL)
    source_count = count_only(PARCEL_URL, PARCEL_WHERE)
    deeded_band = count_only(PARCEL_URL, "DEEDED_ACREAGE>=5 AND DEEDED_ACREAGE<=150")
    print(f"  calculated 5–150 {source_count}, deeded 5–150 {deeded_band}, page {parcel_page}", flush=True)
    if source_count < 8000 or source_count > 10000:
        raise RuntimeError(f"Unexpected Stokes calculated-acre count {source_count}")

    raw = paginate(
        PARCEL_URL,
        PARCEL_WHERE,
        PARCEL_FIELDS,
        geometry=True,
        oid_field="OBJECTID",
        page_size=parcel_page,
        label="parcels",
    )
    if len(raw) < source_count:
        raise RuntimeError(f"Parcel pages returned {len(raw)} of {source_count}")
    features, dropped = normalize_parcels(raw, county, markets)
    if len(features) < 8000:
        raise RuntimeError(f"Only {len(features)} Stokes parcels survived")
    print(f"  kept {len(features)} dropped {dropped}", flush=True)

    print("Zoning layer 27", flush=True)
    zoning_raw = paginate(
        ZONING_URL,
        "1=1",
        "OBJECTID,ZONING,ZONING_JURI,ZONE_AREA",
        geometry=True,
        oid_field="OBJECTID",
        page_size=zoning_page,
        label="zoning",
    )
    zoning_index = index_polygons(zoning_raw, zoning_payload)

    print("Land Use 2035 layer 34", flush=True)
    # Ungeneralized Land Use 2035 pages above ~200 features return HTTP 500.
    # 0.00008 degrees is about 8 meters. The request still asks for up to 2000 rows.
    flu_raw = paginate(
        FLU_URL,
        "1=1",
        "OBJECTID_1,LUP_CODE,LUP_DESC,ZONING_JUR,ZONE_AREA",
        geometry=True,
        oid_field="OBJECTID_1",
        page_size=flu_page,
        label="flu",
        max_allowable_offset=0.00008,
    )
    flu_index = index_polygons(flu_raw, flu_payload)
    joins = join_polygons(features, zoning_index, flu_index)
    print(f"  joins {joins}", flush=True)

    eligible = load_eligible()
    designated = load_designated()
    zone_stats = join_zones(features, eligible, designated)
    print(
        f"  eligible {zone_stats['eligibleParcels']} designated {zone_stats['designatedParcels']} both {zone_stats['eligibleAlsoDesignated']}",
        flush=True,
    )

    pins = {feature["properties"]["parcelId"] for feature in features}
    acres_by_pin = {feature["properties"]["parcelId"]: feature["properties"]["acreage"] for feature in features}
    zoning_by_pin = {feature["properties"]["parcelId"]: feature["properties"].get("zoningCode") for feature in features}
    onemap = qa_onemap(pins, acres_by_pin)
    king = qa_king(pins, zoning_by_pin)
    if king["forsythLeaked"]:
        raise RuntimeError("Forsyth parcels leaked into the King Stokes QA page")

    eligible_ids = sorted(zone["geoid"] for zone in eligible)
    designated_ids = sorted(zone["geoid"] for zone in designated)
    gaps = build_gaps(
        source_count=source_count,
        kept=len(features),
        dropped=dropped,
        deeded_band=deeded_band,
        joins=joins,
        zones=zone_stats,
        onemap=onemap,
        king=king,
        eligible_ids=eligible_ids,
        designated_ids=designated_ids,
        parcel_page=parcel_page,
        zoning_page=zoning_page,
        flu_page=flu_page,
    )
    if not all(in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Stokes extract emitted a parcel outside 5–150 acres")

    _path, _lookup, tile_count = write_tiles(county, features)
    row = county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=f"data/fixtures/market-parcels/counties/{FIPS}/tiles",
        lookup=f"data/fixtures/market-parcels/counties/{FIPS}/lookup.json",
        source=SOURCE,
        query_url=PARCEL_URL,
        gaps=gaps,
        source_count=source_count,
        dropped=source_count - len(features),
        tile_count=tile_count,
    )
    qa = {
        "parcelPageSize": parcel_page,
        "zoningPageSize": zoning_page,
        "fluPageSize": flu_page,
        "deededBand": deeded_band,
        "joins": joins,
        "zones": {
            **zone_stats,
            "eligibleGeoids": eligible_ids,
            "designatedGeoids": designated_ids,
        },
        "onemap": onemap,
        "king": king,
    }
    county_path = COUNTY_DIR / FIPS / "county.json"
    saved = json.loads(county_path.read_text())
    saved["qa"] = qa
    saved["layers"] = {
        "parcels": PARCEL_URL.replace("/query", ""),
        "zoning": ZONING_URL.replace("/query", ""),
        "flu": FLU_URL.replace("/query", ""),
        "kingQa": KING_URL.replace("/query", ""),
        "oneMap": ONEMAP_URL,
    }
    county_path.write_text(json.dumps(saved, indent=2) + "\n")
    write_doc(gaps, qa, len(features))
    patch_indexes(len(features), gaps, source_count, tile_count)
    print(f"Stokes kept {len(features)} across {tile_count} tiles", flush=True)
    return row


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text())
    county = None
    markets: list[str] = []
    for market in catalog["markets"]:
        for item in market["counties"]:
            if item["fips"] == FIPS:
                county = item
                if market["id"] not in markets:
                    markets.append(market["id"])
    if county is None:
        raise SystemExit("Stokes County is missing from data/market-parcel-counties.json")
    seed_stokes_county(county, markets)


if __name__ == "__main__":
    main()
