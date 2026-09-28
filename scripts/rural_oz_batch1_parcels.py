#!/usr/bin/env python3
"""5.0–150.0 acre parcels for the rural OZ pass-1 Florida counties.

Uses the market-parcel tile writer (0.25° grid, origin lon -83 / lat 27).
Does not add markets, cap the extract, or store an Opportunity Zone status.

Counties already on the card source at the card count are left in place:
Polk, Hernando, Lake, Pasco, and DeSoto.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import seed_market_parcels as seed
from parcel_geometry import esri_rings_to_geojson

ROOT = seed.ROOT
CATALOG_PATH = seed.CATALOG_PATH
CACHE_DIR = Path("/tmp/dls-rural-oz-batch1")
FDOR_URL = (
    "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/"
    "Florida_Statewide_Cadastral/FeatureServer/0/query"
)
SRWMD = "http://gis.srwmd.state.fl.us/arcgis/rest/services/SRWMDGIS/SRWMD_Parcels/FeatureServer"

# Counties whose live extract already matches the card. Do not download again.
SKIP_FIPS = {"12027", "12053", "12069", "12101", "12105"}

ADD_TO_MARKET = {
    "North-Central Florida": [
        {"name": "Hamilton", "state": "Florida", "fips": "12047"},
        {"name": "Lafayette", "state": "Florida", "fips": "12067"},
        {"name": "Marion", "state": "Florida", "fips": "12083"},
        {"name": "Suwannee", "state": "Florida", "fips": "12121"},
        {"name": "Union", "state": "Florida", "fips": "12125"},
    ],
    "Pensacola": [
        {"name": "Holmes", "state": "Florida", "fips": "12059"},
    ],
}

SECTION_FOR_NEW = {
    "12047": "North-Central Florida",
    "12059": "Pensacola",
    "12067": "North-Central Florida",
    "12083": "North-Central Florida",
    "12121": "North-Central Florida",
    "12125": "North-Central Florida",
}


def srwmd(layer: int, fips: str, name: str, note: str) -> dict:
    return {
        "kind": "arcgis",
        "name": name,
        "fips": fips,
        "url": f"{SRWMD}/{layer}/query",
        "where": "AREANO>=5 AND AREANO<=150",
        "outFields": [
            "PARNO",
            "AREANO",
            "OWNNAME",
            "OWNERNAME",
            "SITEADD",
            "PARVAL",
            "PARUSECODE",
            "SALE1_AMT",
            "SALE1_DATE",
            "OWNERADD1",
            "OWNERCITY",
            "OWNERSTATE",
            "OWNERZIP",
            "SCITY",
        ],
        "idField": "PARNO",
        "acresField": "AREANO",
        "ownerField": "OWNNAME",
        "situsField": "SITEADD",
        "cityField": "SCITY",
        "dorField": "PARUSECODE",
        "salePriceField": "SALE1_AMT",
        "saleDateField": "SALE1_DATE",
        "marketValueField": "PARVAL",
        "mail1Field": "OWNERADD1",
        "mailCityField": "OWNERCITY",
        "mailStateField": "OWNERSTATE",
        "mailZipField": "OWNERZIP",
        "source": f"fl-srwmd-parcels-{fips}",
        "coverage": "complete-gte-5ac",
        "expected": None,
        "gaps": [
            note,
            "Acreage is AREANO, 5.0–150.0 inclusive. The id is PARNO (PARCELID is empty except Levy). Leading spaces are trimmed. Placeholder ids are dropped. http only.",
            "No Opportunity Zone status is stored. Zoning and future land use are not on this SRWMD roll.",
        ],
    }


SPECS: dict[str, dict] = {
    "12007": srwmd(
        2,
        "12007",
        "Bradford",
        "Upgrade off the Florida DOH roll (593 parcels). SRWMD layer 2 is the countywide 5–150 acre extract. FDOR joins for this county need CO_NO=14.",
    ),
    "12017": {
        "kind": "arcgis",
        "name": "Citrus",
        "fips": "12017",
        "url": "https://www25.swfwmd.state.fl.us/arcgis12/rest/services/BaseVector/parcel_search/MapServer/2/query",
        "where": "AREANO>=5 AND AREANO<=150",
        "outFields": ["PARCELID", "AREANO", "OWNNAME", "SITEADD", "PARVAL", "PARUSECODE", "SALE1_AMT", "SALE1_DATE", "OWNERADD1", "OWNERCITY", "OWNERSTATE", "OWNERZIP", "SCITY"],
        "idField": "PARCELID",
        "acresField": "AREANO",
        "ownerField": "OWNNAME",
        "situsField": "SITEADD",
        "cityField": "SCITY",
        "dorField": "PARUSECODE",
        "salePriceField": "SALE1_AMT",
        "saleDateField": "SALE1_DATE",
        "marketValueField": "PARVAL",
        "mail1Field": "OWNERADD1",
        "mailCityField": "OWNERCITY",
        "mailStateField": "OWNERSTATE",
        "mailZipField": "OWNERZIP",
        "source": "fl-citrus-swfwmd-12017",
        "coverage": "complete-gte-5ac",
        "gaps": [
            "Parcels are SWFWMD parcel_search layer 2. Acreage is AREANO (ACRES is empty), 5.0–150.0 inclusive. PARCELID keeps embedded spaces.",
            "Replaces the Florida DOH tiles. Zoning copied only when the parcel id still matches the previous extract.",
            "No Opportunity Zone status is stored.",
        ],
    },
    "12029": srwmd(4, "12029", "Dixie", "SRWMD layer 4 replaces the Big Bend gap. FDOR joins need CO_NO=25."),
    "12047": srwmd(6, "12047", "Hamilton", "SRWMD layer 6. FDOR joins need CO_NO=34."),
    "12059": {
        "kind": "arcgis",
        "name": "Holmes",
        "fips": "12059",
        "url": "https://services.arcgis.com/yghUoIoA2Cd2cWki/arcgis/rest/services/Holmes_Parcels/FeatureServer/0/query",
        "where": "Gis_Acres>=5 AND Gis_Acres<=150",
        "outFields": ["PARCELNO", "Gis_Acres", "DOR_PCN"],
        "idField": "PARCELNO",
        "acresField": "Gis_Acres",
        "source": "fl-holmes-taxparcels-12059",
        "coverage": "complete-gte-5ac",
        "gaps": [
            "Holmes TaxParcels (Holmes_Parcels/0). Acreage is Gis_Acres, 5.0–150.0 inclusive. The id is PARCELNO.",
            "Owner is not on this layer. The Panda maintenance-request layer is not this source and is not ingested.",
            "No Opportunity Zone status is stored. FDOR joins need CO_NO=40 and a PARCELNO with '.' and '-' removed.",
        ],
    },
    "12067": srwmd(8, "12067", "Lafayette", "SRWMD layer 8. FDOR joins need CO_NO=44."),
    "12075": srwmd(
        9,
        "12075",
        "Levy",
        "Upgrade off the Florida DOH roll. SRWMD layer 9. PARNO matches PARCELID here. FDOR joins need CO_NO=48.",
    ),
    "12079": srwmd(10, "12079", "Madison", "SRWMD layer 10 replaces the Big Bend gap. FDOR joins need CO_NO=50."),
    "12083": {
        "kind": "arcgis",
        "name": "Marion",
        "fips": "12083",
        "url": "https://gis.marionfl.org/public/rest/services/General/ParcelsAndSubdivisions/MapServer/0/query",
        "where": "ACRES>=5 AND ACRES<=150",
        "outFields": ["PARCEL", "ACRES", "NAME", "TOT_VAL", "ASSD_VAL"],
        "idField": "PARCEL",
        "acresField": "ACRES",
        "ownerField": "NAME",
        "marketValueField": "TOT_VAL",
        "assessedField": "ASSD_VAL",
        "source": "fl-marion-parcels-12083",
        "coverage": "complete-gte-5ac",
        "gaps": [
            "County ParcelsAndSubdivisions MapServer/0. Acreage is ACRES, 5.0–150.0 inclusive. Replaces the Orlando 120-parcel sample on the map.",
            "The Orlando sample file is unchanged and is not drawn once this extract is larger. No Opportunity Zone status is stored.",
            "FDOR joins need CO_NO=52 and PARCEL kept dashed.",
        ],
    },
    "12099": {"kind": "palm", "name": "Palm Beach", "fips": "12099"},
    "12109": {"kind": "stjohns", "name": "St. Johns", "fips": "12109"},
    "12119": {
        "kind": "arcgis",
        "name": "Sumter",
        "fips": "12119",
        "url": "https://services8.arcgis.com/FTrtUCmxaVKdPC5e/arcgis/rest/services/Parcels_gdb/FeatureServer/0/query",
        "where": "Shape_STAr>=217800 AND Shape_STAr<=6534000",
        "outFields": ["PIN", "Shape_STAr", "Owners_Nam", "DOR_LUC", "Site_Addr_"],
        "idField": "PIN",
        "acresField": "Shape_STAr",
        "acresScale": 43560,
        "ownerField": "Owners_Nam",
        "situsField": "Site_Addr_",
        "dorField": "DOR_LUC",
        "source": "fl-sumter-bocc-parcels-12119",
        "coverage": "complete-gte-5ac",
        "gaps": [
            "Sumter BOCC Parcels_gdb. Acreage is Shape_STAr / 43560, 5.0–150.0 inclusive. Acres_Lot_ is a string and is not the acreage.",
            "Replaces the Tampa DOH tiles. Orlando SWFWMD tiles are a separate shelf and were not rewritten.",
            "No Opportunity Zone status is stored. FDOR joins need CO_NO=70 and PIN exactly.",
        ],
    },
    "12121": srwmd(11, "12121", "Suwannee", "SRWMD layer 11. FDOR joins need CO_NO=71. Some PARNO values have a leading space; it is trimmed."),
    "12123": srwmd(12, "12123", "Taylor", "SRWMD layer 12 replaces the Big Bend gap. FDOR joins need CO_NO=72."),
    "12125": srwmd(
        13,
        "12125",
        "Union",
        "SRWMD layer 13. The Panda UnionMaintenanceRequests layer is publicly editable and is not ingested.",
    ),
}


def usable_parcel_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"?", "-", ".", "0"}:
        return None
    if text[0] in "*?":
        return None
    upper = text.upper()
    if upper in {"NULL", "NONE", "N/A", "NA"} or "MULTI OWNER" in upper:
        return None
    if not any(ch.isalnum() for ch in text):
        return None
    return text


def markets_for(catalog: dict, fips: str) -> list[str]:
    found: list[str] = []
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips and market["id"] not in found:
                found.append(market["id"])
    return found


def ensure_catalog(catalog: dict) -> dict:
    by_market = {market["id"]: market for market in catalog["markets"]}
    for market_id, additions in ADD_TO_MARKET.items():
        market = by_market[market_id]
        present = {county["fips"] for county in market["counties"]}
        for county in additions:
            if county["fips"] not in present:
                market["counties"].append(county)
                present.add(county["fips"])
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    return catalog


def all_object_ids(url: str, where: str) -> tuple[list[int], int]:
    count = seed.count_where(url, where)
    ids = seed.fetch_object_ids(url, where)
    if len(ids) >= max(1, int(count * 0.98)) or count == 0:
        return ids, count
    print(f"  returnIdsOnly {len(ids)} < count {count}; paging OBJECTID", flush=True)
    stats = seed.fetch_json(
        url,
        {
            "where": where,
            "returnGeometry": "false",
            "outStatistics": json.dumps(
                [
                    {"statisticType": "min", "onStatisticField": "OBJECTID", "outStatisticFieldName": "mn"},
                    {"statisticType": "max", "onStatisticField": "OBJECTID", "outStatisticFieldName": "mx"},
                ]
            ),
            "f": "json",
        },
    )
    attrs = ((stats.get("features") or [{}])[0].get("attributes") or {})
    mn = int(attrs["mn"])
    mx = int(attrs["mx"])
    collected: list[int] = []
    step = 4000
    start = mn
    while start <= mx:
        clause = f"({where}) AND OBJECTID>={start} AND OBJECTID<{start + step}"
        collected.extend(seed.fetch_object_ids(url, clause))
        start += step
    deduped = sorted(set(collected))
    print(f"  OBJECTID pages {len(deduped)}", flush=True)
    return deduped, count


def prepare_raw(raw: list[dict], spec: dict) -> list[dict]:
    kept: list[dict] = []
    for item in raw:
        attrs = dict(item.get("attributes") or {})
        parcel_id = usable_parcel_id(attrs.get(spec["idField"]))
        if not parcel_id:
            continue
        attrs[spec["idField"]] = parcel_id
        if spec.get("ownerField") == "OWNNAME" and not seed.clean(attrs.get("OWNNAME")):
            attrs["OWNNAME"] = attrs.get("OWNERNAME")
        kept.append({"attributes": attrs, "geometry": item.get("geometry")})
    return kept


def sanitize(features: list[dict]) -> None:
    for feature in features:
        props = feature["properties"]
        if props.get("situsAddress") in {"0", "0.0"}:
            props["situsAddress"] = None
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        props["nearestRoad"] = None


def existing_props(fips: str) -> dict[str, dict]:
    folder = seed.COUNTY_DIR / fips / "tiles"
    found: dict[str, dict] = {}
    if not folder.exists():
        return found
    for path in folder.glob("*.geojson"):
        data = json.loads(path.read_text())
        for feature in data.get("features") or []:
            props = feature.get("properties") or {}
            parcel_id = props.get("parcelId")
            if parcel_id:
                found[str(parcel_id)] = props
    return found


def carry_forward(features: list[dict], previous: dict[str, dict]) -> int:
    copied = 0
    keys = ("zoningCode", "zoningDistrict", "flu", "jurisdictionCode", "appraiserUrl", "gisViewerUrl")
    for feature in features:
        props = feature["properties"]
        old = previous.get(props["parcelId"])
        if not old:
            continue
        hit = False
        for key in keys:
            if old.get(key) and not props.get(key):
                props[key] = old[key]
                hit = True
        if hit:
            copied += 1
    return copied


def pull_arcgis(spec: dict, county: dict, markets: list[str]) -> tuple[list[dict], int, int]:
    ids, count = all_object_ids(spec["url"], spec["where"])
    print(f"  source rows {count} ids {len(ids)}", flush=True)
    raw = seed.fetch_by_ids(spec["url"], ids, spec["outFields"])
    prepared = prepare_raw(raw, spec)
    features, dropped = seed.normalize_rows(prepared, county, markets, spec)
    sanitize(features)
    if features and not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{spec['fips']} emitted a parcel outside 5–150 acres")
    return features, count, dropped + (len(raw) - len(prepared))


def fdor_box(west: float, south: float, east: float, north: float, depth: int = 0) -> list[dict]:
    geom = json.dumps(
        {
            "xmin": west,
            "ymin": south,
            "xmax": east,
            "ymax": north,
            "spatialReference": {"wkid": 4326},
        }
    )
    where = "CO_NO=65 AND LND_SQFOOT>=217800 AND LND_SQFOOT<=6534000"
    rows: list[dict] = []
    offset = 0
    try:
        while True:
            data = seed.fetch_json(
                FDOR_URL,
                {
                    "where": where,
                    "geometry": geom,
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "PARCEL_ID,LND_SQFOOT,CO_NO",
                    "returnGeometry": "false",
                    "resultOffset": str(offset),
                    "resultRecordCount": "2000",
                    "f": "json",
                },
                timeout=90,
            )
            if data.get("error"):
                raise RuntimeError(json.dumps(data["error"])[:240])
            batch = data.get("features") or []
            rows.extend(batch)
            if not data.get("exceededTransferLimit") and len(batch) < 2000:
                break
            if not batch:
                break
            offset += len(batch)
        return rows
    except Exception as exc:  # noqa: BLE001
        if depth >= 2:
            raise
        print(f"  FDOR cell retry {west:.2f},{south:.2f} ({exc})", flush=True)
        mid_x = (west + east) / 2
        mid_y = (south + north) / 2
        parts = [
            (west, south, mid_x, mid_y),
            (mid_x, south, east, mid_y),
            (west, mid_y, mid_x, north),
            (mid_x, mid_y, east, north),
        ]
        merged: list[dict] = []
        for part in parts:
            merged.extend(fdor_box(*part, depth + 1))
        return merged


def st_johns_acres() -> dict[str, float]:
    acres: dict[str, float] = {}
    west, south, east, north = -81.70, 29.59, -81.18, 30.29
    step = 0.1
    x = west
    cells = 0
    while x < east - 1e-9:
        y = south
        while y < north - 1e-9:
            cells += 1
            rows = fdor_box(x, y, min(x + step, east), min(y + step, north))
            for item in rows:
                attrs = item.get("attributes") or {}
                if int(attrs.get("CO_NO") or 0) != 65:
                    continue
                parcel_id = usable_parcel_id(attrs.get("PARCEL_ID"))
                if not parcel_id:
                    continue
                sqft = seed.num(attrs.get("LND_SQFOOT"))
                if sqft is None:
                    continue
                value = sqft / 43560
                if not seed.in_band(value):
                    continue
                # Duplicate FDOR rows for one PARCEL_ID collapse to one acreage.
                if parcel_id not in acres:
                    acres[parcel_id] = value
            y += step
        x += step
        print(f"  FDOR cells {cells} unique {len(acres)}", flush=True)
    return acres


def merge_geometries(geometries: list[dict]) -> dict | None:
    polygons: list = []
    for geometry in geometries:
        if not geometry:
            continue
        if geometry.get("type") == "Polygon":
            polygons.append(geometry["coordinates"])
        elif geometry.get("type") == "MultiPolygon":
            polygons.extend(geometry["coordinates"])
    if not polygons:
        return None
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def pull_st_johns(county: dict, markets: list[str]) -> tuple[list[dict], int, int]:
    acres = st_johns_acres()
    print(f"  FDOR 5–150 ids {len(acres)}", flush=True)
    url = "https://www.gis.sjcfl.us/portal_sjcgis/rest/services/Hosted/Parcel/FeatureServer/0/query"
    fields = ["pin", "strap", "prp_name", "prp_addr", "use_code", "saledate", "own_addres", "own_city", "own_state", "own_zipcod"]
    ids = list(acres)
    grouped: dict[str, list[dict]] = {}
    for start in range(0, len(ids), 40):
        chunk = ids[start : start + 40]
        quoted = ",".join("'" + value.replace("'", "''") + "'" for value in chunk)
        data = seed.fetch_json(
            url,
            {
                "where": f"strap IN ({quoted})",
                "outFields": ",".join(fields),
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:240])
        for item in data.get("features") or []:
            strap = usable_parcel_id((item.get("attributes") or {}).get("strap"))
            if strap:
                grouped.setdefault(strap, []).append(item)
        if start % 400 == 0:
            print(f"    straps {min(start + 40, len(ids))}/{len(ids)}", flush=True)
        time.sleep(0.02)
    features: list[dict] = []
    missed = 0
    for strap, items in grouped.items():
        geometries = []
        attrs = items[0].get("attributes") or {}
        for item in items:
            geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
            if geometry:
                geometries.append(geometry)
        geometry = merge_geometries(geometries)
        center = seed.centroid_of(geometry) if geometry else None
        if not geometry or not seed.plausible_centroid(center):
            missed += 1
            continue
        pin = usable_parcel_id(attrs.get("pin")) or strap
        feature = seed.empty_feature(
            fips="12109",
            county="St. Johns",
            state="Florida",
            markets=markets,
            parcel_id=pin,
            acreage=acres[strap],
            geometry=geometry,
            center=center,  # type: ignore[arg-type]
            source="fl-sjc-hosted-parcel-12109",
            owner=seed.clean(attrs.get("prp_name")),
            situs=seed.clean(attrs.get("prp_addr")),
            dor=seed.clean(attrs.get("use_code")),
            sale_date=seed.epoch_to_iso(attrs.get("saledate")) or seed.text_date(attrs.get("saledate")),
            mail1=seed.clean(attrs.get("own_addres")),
            mail_city=seed.clean(attrs.get("own_city")),
            mail_state=seed.clean(attrs.get("own_state")),
            mail_zip=seed.zip_str(attrs.get("own_zipcod")),
        )
        features.append(feature)
    missed += len(acres) - len(grouped)
    sanitize(features)
    by_id: dict[str, dict] = {}
    for feature in features:
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("12109 emitted a parcel outside 5–150 acres")
    print(f"  county geometry misses {missed}", flush=True)
    return features, len(acres), missed


def pull_palm(county: dict, markets: list[str]) -> dict:
    from south_florida_parcels import download_south_florida, south_florida_spec

    spec = south_florida_spec("12099")
    return download_south_florida(county, markets, spec)


def write_county(county: dict, markets: list[str], spec: dict, features: list[dict], source_count: int, dropped: int) -> dict:
    previous = existing_props(county["fips"])
    copied = carry_forward(features, previous)
    if copied:
        spec = dict(spec)
        gaps = list(spec.get("gaps") or [])
        gaps.append(f"Zoning, future land use, or appraiser links carried forward for {copied} parcel ids that still match.")
        spec["gaps"] = gaps
    if source_count and len(features) < int(source_count * 0.8):
        raise RuntimeError(f"{county['fips']} kept {len(features)} of {source_count}")
    if source_count and len(features) < source_count:
        gaps = list(spec.get("gaps") or [])
        gaps.insert(0, f"{source_count} rows matched the acreage filter; {len(features)} kept after the parcel-id and geometry checks.")
        spec = dict(spec)
        spec["gaps"] = gaps
    path, lookup, tiles = seed.write_tiles(county, features)
    print(f"  kept {len(features)} tiles {tiles}", flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=spec.get("coverage") or "complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=spec["source"],
        query_url=spec.get("url"),
        gaps=list(spec.get("gaps") or []),
        source_count=source_count,
        dropped=dropped,
        tile_count=tiles,
    )


def county_dict(catalog: dict, fips: str, name: str) -> dict:
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips:
                return county
    return {"name": name, "state": "Florida", "fips": fips}


def download_one(catalog: dict, fips: str, refresh: bool) -> dict | None:
    spec = SPECS[fips]
    county = county_dict(catalog, fips, spec["name"])
    markets = markets_for(catalog, fips)
    if not markets:
        raise RuntimeError(f"{fips} is not on a market shelf")
    cache_path = CACHE_DIR / f"{fips}.json"
    print(f"Pulling {spec['name']} {fips}", flush=True)
    if spec["kind"] == "palm":
        if cache_path.exists() and not refresh:
            print("  palm cache hit", flush=True)
            cached = json.loads(cache_path.read_text())
            return cached["row"]
        row = pull_palm(county, markets)
        cache_path.write_text(json.dumps({"row": row}))
        return row
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text())
        features = cached["features"]
        for feature in features:
            feature["properties"]["marketIds"] = markets
        print(f"  cache hit {len(features)}", flush=True)
        return write_county(county, markets, spec, features, cached.get("sourceCount") or len(features), cached.get("dropped") or 0)
    if spec["kind"] == "stjohns":
        features, source_count, dropped = pull_st_johns(county, markets)
        spec = {
            **spec,
            "source": "fl-sjc-hosted-parcel-12109",
            "coverage": "complete-gte-5ac",
            "url": "https://www.gis.sjcfl.us/portal_sjcgis/rest/services/Hosted/Parcel/FeatureServer/0/query",
            "gaps": [
                "No acreage field on Hosted/Parcel. Acreage is FDOR 2025 LND_SQFOOT / 43560 for CO_NO=65, deduped on PARCEL_ID. Geometry is the county layer dissolved by strap.",
                "Pins repeat across polygon pieces, so SHAPE__Area is not the parcel acreage. The Panda maintenance layer is not used.",
                "No Opportunity Zone status is stored. Zoning carried forward only when the pin still matches.",
            ],
        }
    else:
        features, source_count, dropped = pull_arcgis(spec, county, markets)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"sourceCount": source_count, "dropped": dropped, "features": features}, separators=(",", ":"))
    )
    return write_county(county, markets, spec, features, source_count, dropped)


def meta_entry(row: dict) -> dict:
    return {
        "name": row["name"],
        "fips": row["fips"],
        "state": row["state"],
        "featureCount": row.get("featureCount") or 0,
        "coverage": row.get("coverage"),
        "partition": row.get("partition"),
        "minAcres": 5.0,
        "maxAcres": 150.0,
        "source": row.get("source"),
        "queryUrl": row.get("queryUrl"),
        "gaps": row.get("gaps") or [],
        "path": row.get("path"),
        "lookup": row.get("lookup"),
        "tileCount": row.get("tileCount"),
        "sourceCount": row.get("sourceCount"),
    }


def index_entry(row: dict) -> dict:
    return {
        "name": row["name"],
        "state": row["state"],
        "fips": row["fips"],
        "featureCount": row.get("featureCount") or 0,
        "coverage": row.get("coverage"),
        "minAcres": 5.0,
        "maxAcres": 150.0,
        "gaps": (row.get("gaps") or [])[:2],
    }


def recount(counties: list[dict]) -> tuple[int, int, int, int]:
    parcels = sum(int(county.get("featureCount") or 0) for county in counties)
    complete = sum(1 for county in counties if county.get("coverage") == "complete-gte-5ac" and county.get("featureCount"))
    sample = sum(1 for county in counties if county.get("coverage") in {"sample", "partial"} and county.get("featureCount"))
    gaps = sum(1 for county in counties if not county.get("featureCount"))
    return parcels, complete, sample, gaps


def refresh_manifests(catalog: dict, fips_set: set[str]) -> None:
    index_path = seed.OUT_DIR / "index.json"
    index = json.loads(index_path.read_text())
    for market in catalog["markets"]:
        if not any(county["fips"] in fips_set for county in market["counties"]):
            continue
        rel = index["markets"][market["id"]]["path"]
        meta_path = ROOT / rel
        meta = json.loads(meta_path.read_text())
        meta_counties = {county["fips"]: county for county in meta.get("counties") or []}
        index_counties = {county["fips"]: county for county in index["markets"][market["id"]]["counties"]}
        for county in market["counties"]:
            file_path = seed.COUNTY_DIR / county["fips"] / "county.json"
            if not file_path.exists():
                continue
            row = json.loads(file_path.read_text())
            meta_counties[county["fips"]] = meta_entry(row)
            index_counties[county["fips"]] = index_entry(row)
        ordered = sorted(meta_counties.values(), key=lambda item: item["name"])
        meta["counties"] = ordered
        meta["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        parcels, complete, sample, gaps = recount(ordered)
        meta["parcelCount"] = parcels
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        summary = index["markets"][market["id"]]
        summary["parcelCount"] = parcels
        summary["completeCountyCount"] = complete
        summary["sampleCountyCount"] = sample
        summary["gapCountyCount"] = gaps
        summary["counties"] = [index_counties[county["fips"]] for county in ordered]
    index["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    patch_docs(index)


def patch_docs(index: dict) -> None:
    docs = ROOT / "docs" / "market-parcels.md"
    text = docs.read_text()
    for market_id, summary in index["markets"].items():
        line = (
            f"| {market_id} | {summary['tier']} | {summary['parcelCount']:,} | "
            f"{summary['completeCountyCount']} | {summary['sampleCountyCount']} | {summary['gapCountyCount']} |"
        )
        text, _count = re.subn(rf"^\| {re.escape(market_id)} \|.*$", line, text, count=1, flags=re.M)
        for county in summary["counties"]:
            row = (
                f"| {county['name']} | {county['state']} | {county['fips']} | {county['coverage']} | "
                f"{int(county['featureCount']):,} | {json.loads((seed.COUNTY_DIR / county['fips'] / 'county.json').read_text()).get('source')} |"
            )
            updated, hits = re.subn(
                rf"^\| {re.escape(county['name'])} \| {re.escape(county['state'])} \| {county['fips']} \|.*$",
                row,
                text,
                flags=re.M,
            )
            text = updated
            if hits == 0 and county["fips"] in SECTION_FOR_NEW:
                section = SECTION_FOR_NEW[county["fips"]]
                text = insert_section_row(text, section, row)
    text = text.replace(
        "Broward and Palm Beach stay partial.",
        "Broward stays partial. Palm Beach is the MapServer extract with condo units excluded.",
    )
    docs.write_text(text)
    south = ROOT / "docs" / "south-florida-parcels.md"
    south_text = south.read_text()
    palm = json.loads((seed.COUNTY_DIR / "12099" / "county.json").read_text())
    south_text = south_text.replace(
        "| Palm Beach | 12099 | partial | PARCEL_INFO FeatureServer/4 | `https://gis.pbcgov.org/arcgis/rest/services/Parcels/PARCEL_INFO/FeatureServer/4` |",
        "| Palm Beach | 12099 | live | PARCEL_INFO MapServer/4, CONDO='NO' | `https://gis.pbcgov.org/arcgis/rest/services/Parcels/PARCEL_INFO/MapServer/4` |",
    )
    south_text = south_text.replace(
        "Broward and Palm Beach stay partial.",
        "Broward stays partial. Palm Beach is the MapServer extract with condo units excluded.",
    )
    south_text = south_text.replace(
        "- **Palm Beach count.** The ACRES 5.0–150.0 query reports about 146,014 object ids. This shelf kept the parcels that survived geometry normalize and parcel-id dedupe, so Palm Beach is partial, not a full object-id extract. `maps.co.palm-beach.fl.us` TLS is fragile. The token-gated OpenData mirror and `opendata.pbcgov.org` are not used. `PROPERTY_USE` is text, not a numeric DOR code.",
        f"- **Palm Beach count.** MapServer/4 with ACRES 5.0–150.0 and CONDO='NO' is {palm['featureCount']:,} parcels. Condo units inherit the parent ACRES, so the unfiltered count is not this shelf. The FeatureServer advertises public edits and is not queried. `maps.co.palm-beach.fl.us` TLS is fragile. `PROPERTY_USE` is text, not a numeric DOR code.",
    )
    south.write_text(south_text)
    patch_north_central_doc()
    patch_orlando_doc()


def insert_section_row(text: str, section: str, row: str) -> str:
    marker = f"### {section}\n"
    start = text.find(marker)
    if start < 0:
        return text
    end = text.find("\n### ", start + len(marker))
    block = text[start:] if end < 0 else text[start:end]
    lines = block.splitlines()
    inserted = False
    rebuilt: list[str] = []
    for index, line in enumerate(lines):
        rebuilt.append(line)
        if not inserted and line.startswith("| ---"):
            # Insert after the separator; the following loop keeps existing rows.
            continue
    # Append before the trailing prose (first non-table line after the header).
    table_end = 0
    for index, line in enumerate(lines):
        if index > 2 and line.startswith("|"):
            table_end = index
    if table_end:
        lines.insert(table_end + 1, row)
        inserted = True
    if not inserted:
        return text
    new_block = "\n".join(lines)
    if not new_block.endswith("\n"):
        new_block += "\n"
    if end < 0:
        return text[:start] + new_block
    return text[:start] + new_block + text[end:]


def patch_north_central_doc() -> None:
    path = ROOT / "docs" / "north-central-fl-parcels.md"
    if not path.exists():
        return
    text = path.read_text()
    text = text.replace(
        "`seed:parcels:north-central` passes `--refresh` so Hernando and Citrus replace the earlier Florida DOH-only tiles. Those two counties stay on the Tampa list as well. The shared tile files are the upgraded extract. Marion is not in this market and the Orlando sample is not rewritten.",
        "`seed:parcels:north-central` passes `--refresh` so Hernando and Citrus replace the earlier Florida DOH-only tiles. Those two counties stay on the Tampa list as well. The shared tile files are the upgraded extract. Bradford, Levy, Hamilton, Lafayette, Marion, Suwannee, and Union are on this shelf. The Orlando Marion sample file is not rewritten.",
    )
    replacements = {
        "| Levy | 10,200 | 10,984 | DOH acreage only. Partial |": "| Levy | {levy} | {levy_src} | SRWMD layer 9. PARNO |",
        "| Citrus | 5,807 | 5,813 | DOH polygons plus corporate limits and county zoning centroids |": "| Citrus | {citrus} | {citrus_src} | SWFWMD layer 2. AREANO. Prior zoning kept when the parcel id matches |",
        "| Bradford | 593 | 598 | DOH acreage only. Partial |": "| Bradford | {bradford} | {bradford_src} | SRWMD layer 2. PARNO |",
        "| Levy | 10,200 | 10,984 | https://www.qpublic.net/fl/levy/ |": "| Levy | {levy} | {levy_src} | https://www.qpublic.net/fl/levy/ |",
        "| Bradford | 593 | 598 | https://www.bradfordappraiser.com/ |": "| Bradford | {bradford} | {bradford_src} | https://www.bradfordappraiser.com/ |",
    }

    def count_of(fips: str) -> tuple[str, str]:
        row = json.loads((seed.COUNTY_DIR / fips / "county.json").read_text())
        return f"{int(row['featureCount']):,}", f"{int(row.get('sourceCount') or row['featureCount']):,}"

    levy, levy_src = count_of("12075")
    citrus, citrus_src = count_of("12017")
    bradford, bradford_src = count_of("12007")
    values = {
        "levy": levy,
        "levy_src": levy_src,
        "citrus": citrus,
        "citrus_src": citrus_src,
        "bradford": bradford,
        "bradford_src": bradford_src,
    }
    for old, new in replacements.items():
        text = text.replace(old, new.format(**values))
    text = text.replace(
        "### Levy, Gilchrist, and Bradford (partial)\n\nThese stay on the Florida DOH 5–150 acre roll. No public municipal boundary, zoning, or future-land-use service was verified, so zoning and FLU are blank and `PHY_CITY` is not treated as a municipality.",
        "### Levy, Gilchrist, and Bradford\n\nLevy and Bradford are the SRWMD April 2025 roll (`AREANO`, id `PARNO`). Gilchrist stays on the Florida DOH 5–150 acre roll. No public municipal boundary, zoning, or future-land-use service was verified for these three, so zoning and FLU are blank.",
    )
    text = text.replace(
        "- Marion. Same Orlando central sample as before. No Marion tiles were rewritten and Marion is not a second market listing.",
        "- Marion is the county ParcelsAndSubdivisions MapServer/0 extract on this shelf. The Orlando sample file is unchanged and is not drawn once this extract is larger.",
    )
    path.write_text(text)


def patch_orlando_doc() -> None:
    path = ROOT / "docs" / "orlando-parcels.md"
    if not path.exists():
        return
    text = path.read_text()
    text = text.replace(
        "Marion was checked and not seeded: [ParcelsAndSubdivisions/0](https://gis.marionfl.org/public/rest/services/General/ParcelsAndSubdivisions/MapServer/0), [FLU /6](https://gis.marionfl.org/public/rest/services/General/PlanningZoning/MapServer/6) (`PARCELID` join), [Zoning /20](https://gis.marionfl.org/public/rest/services/General/PlanningZoning/MapServer/20). About 17,840 parcels sit in the 5–150 acre band.",
        "Marion's full 5–150 acre extract is the North-Central Florida market shelf ([ParcelsAndSubdivisions/0](https://gis.marionfl.org/public/rest/services/General/ParcelsAndSubdivisions/MapServer/0)). This Orlando file stays the 120-parcel sample and is not drawn when the market extract is larger. FLU and zoning were not joined on the market shelf.",
    )
    text = text.replace(
        "- Brevard, Marion, and Volusia are still windowed samples around rural tracts, not every 5–150 acre parcel.",
        "- Brevard and Volusia are still windowed samples around rural tracts, not every 5–150 acre parcel. Marion's sample file remains here; the countywide roll is the North-Central Florida shelf.",
    )
    path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    catalog = ensure_catalog(json.loads(CATALOG_PATH.read_text()))
    selected = {item.lower() for item in args.county}
    fips_list = []
    for fips, spec in SPECS.items():
        if fips in SKIP_FIPS:
            continue
        if selected and fips not in selected and spec["name"].lower() not in selected:
            continue
        fips_list.append(fips)
    touched = set(fips_list)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    workers = 1 if len(fips_list) < 2 else 3
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_one, catalog, fips, args.refresh): fips for fips in fips_list}
        for future in as_completed(futures):
            fips = futures[future]
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{fips}: {exc}")
                print(f"FAILED {fips}: {exc}", flush=True)
    if errors:
        raise SystemExit("County downloads failed:\n" + "\n".join(errors))
    refresh_manifests(catalog, touched | SKIP_FIPS)
    print("Done", flush=True)


if __name__ == "__main__":
    sys.exit(main())
