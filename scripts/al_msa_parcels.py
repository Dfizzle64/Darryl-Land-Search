"""Tuscaloosa and Montgomery, Alabama MSA parcel specs and city zoning joins.

Public GIS only. Sale price is never invented. Eligible-tract rows are not
created here: these markets are parcel shelves on top of the existing map,
and nothing in this module marks a tract or parcel designated.

The New York AGOL Montgomery County parcel mirror (Amsterdam / SWIS) is rejected.
Wetumpka zoning returns HTTP 499 and is not queried. City of Tuscaloosa
Framework_Zoning_Map is a draft and is not joined.
"""

from __future__ import annotations

import json
import math
import threading
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parcel_geometry import esri_rings_to_geojson, net_acres

NY_MONTGOMERY_PARCEL_MIRROR = (
    "https://services6.arcgis.com/EbVsqZ18sv1kVJ3k/arcgis/rest/services/"
    "Montgomery_County_Parcels/FeatureServer/0"
)
NY_MONTGOMERY_ORG = "EbVsqZ18sv1kVJ3k"
WETUMPKA_ZONING_SERVICE = (
    "https://services5.arcgis.com/6AasMFHPoqawuioF/arcgis/rest/services/"
    "Zoning_Districts_Public/FeatureServer"
)
FRAMEWORK_ZONING_SERVICE = (
    "https://services1.arcgis.com/DADyRNMb7tdzKmmq/arcgis/rest/services/"
    "Framework_Zoning_Map/FeatureServer/0"
)

PRATTVILLE_VINTAGE = (
    "Prattville zoning is ZONING_JULY_2017 (internal layer name Zoning_2022). "
    "Vintage is unclear: sampled DATE_ZONED values are often May 1, 1987, with some later ordinances. "
    "Joined only where the polygon overlaps Autauga or Elmore parcels. Partial until a current official zoning service is confirmed."
)
WETUMPKA_GAP = (
    "City of Wetumpka Zoning_Districts_Public returns token required (HTTP 499). "
    "The zoning web map is not a public FeatureServer query. It was not downloaded and no Wetumpka zoning was invented."
)
HALE_PICKENS_GREENE = (
    "Hale, Pickens, and Greene counties are Flagship/CaptureCAMA HTML only in this pull. "
    "No usable public parcel REST. Polygons were not invented. Bibb County stays a Birmingham parcel gap for the same reason."
)
NO_SALE_PRICE = "No sale price on the public parcel layer. lastSale.price stays null."

CELL = 0.05

PARCEL_SPECS: dict[str, dict] = {
    "01125": {
        "kind": "arcgis",
        "url": "https://services.arcgis.com/AWzSDaKZ41uuVges/ArcGIS/rest/services/Parcels/FeatureServer/0/query",
        "where": "rtMAP_ACRE>=5 AND rtMAP_ACRE<=150",
        "outFields": [
            "Name",
            "pclnum",
            "ppin",
            "pcloNAME",
            "AddlNames",
            "pcliLocati",
            "rtMAP_ACRE",
            "deedDATE",
            "appraised",
            "TaxClass",
            "addSTRT1",
            "addSTRT2",
            "addCITY",
            "stABBR",
            "addZIP",
        ],
        "idField": "Name",
        "idFallbacks": ["pclnum"],
        "acresField": "rtMAP_ACRE",
        "ownerField": "pcloNAME",
        "owner2Field": "AddlNames",
        "situsField": "pcliLocati",
        "saleDateField": "deedDATE",
        "marketValueField": "appraised",
        "dorField": "TaxClass",
        "mail1Field": "addSTRT1",
        "mail2Field": "addSTRT2",
        "mailCityField": "addCITY",
        "mailStateField": "stABBR",
        "mailZipField": "addZIP",
        "source": "al-tuscaloosa-parcels",
        "coverage": "complete-gte-5ac",
        "joinProfile": "tuscaloosa",
        "appraiserUrl": "https://www.alabamagis.com/tuscaloosa/",
        "gaps": [
            NO_SALE_PRICE,
            "Acreage filter uses rtMAP_ACRE. rtDEED_ACR is often 0 and is not the filter.",
            "deedDATE is stored as lastSale.date when present. There is no sale price field.",
            "City of Tuscaloosa zoning is Zoning_Districts/3. Framework_Zoning_Map is a draft and was not joined.",
            "Northport zoning is NorthportZoning_Dec2024, joined on pclNUM digits to Name/pclnum, then by centroid.",
            "Northport future land use is FLU_240408, joined by centroid.",
            HALE_PICKENS_GREENE,
        ],
    },
    "01101": {
        "kind": "arcgis",
        "url": "https://gis.montgomeryal.gov/server/rest/services/Parcels/FeatureServer/0/query",
        "where": "Calc_Acre>=5 AND Calc_Acre<=150",
        "outFields": [
            "PID",
            "ParcelNo",
            "OwnerName",
            "OwnerName2",
            "MailAddress1",
            "MailAddress2",
            "MailCity",
            "MailState",
            "MailZip",
            "PropertyAddr1",
            "PropertyCity",
            "PropertyZip",
            "Calc_Acre",
            "TotalValue",
            "AssessmentClass",
            "InstDate",
        ],
        "idField": "PID",
        "idFallbacks": ["ParcelNo"],
        "acresField": "Calc_Acre",
        "ownerField": "OwnerName",
        "owner2Field": "OwnerName2",
        "situsField": "PropertyAddr1",
        "cityField": "PropertyCity",
        "zipField": "PropertyZip",
        "saleDateField": "InstDate",
        "marketValueField": "TotalValue",
        "dorField": "AssessmentClass",
        "mail1Field": "MailAddress1",
        "mail2Field": "MailAddress2",
        "mailCityField": "MailCity",
        "mailStateField": "MailState",
        "mailZipField": "MailZip",
        "source": "al-montgomery-parcels",
        "coverage": "complete-gte-5ac",
        "joinProfile": "montgomery",
        "appraiserUrl": "https://isv.kcsgis.com/al.montgomery_revenue/",
        "gaps": [
            NO_SALE_PRICE,
            "InstDate is null on the 5–150 acre public roll, so lastSale.date is null as well.",
            "Owner and address strings are trimmed. The New York AGOL Montgomery mirror (EbVsqZ18sv1kVJ3k, Amsterdam / SWIS) was rejected.",
            "City zoning is gis.montgomeryal.gov Zoning/0, joined by centroid. No public city FLU layer was verified.",
        ],
    },
    "01051": {
        "kind": "arcgis",
        "url": "https://web5.kcsgis.com/kcsgis/rest/services/Elmore/Public/MapServer/133/query",
        "where": "CALC_ACRE>=5 AND CALC_ACRE<=150",
        "outFields": [
            "PARCELID",
            "PID",
            "ParcelNo",
            "OwnerName",
            "OwnerName2",
            "MailAddress1",
            "MailAddress2",
            "MailCity",
            "MailState",
            "MailZip",
            "PropertyAddr1",
            "CALC_ACRE",
            "TotalValue",
            "AssessmentClass",
        ],
        "idField": "PARCELID",
        "idFallbacks": ["PID", "ParcelNo"],
        "acresField": "CALC_ACRE",
        "ownerField": "OwnerName",
        "owner2Field": "OwnerName2",
        "situsField": "PropertyAddr1",
        "marketValueField": "TotalValue",
        "dorField": "AssessmentClass",
        "mail1Field": "MailAddress1",
        "mail2Field": "MailAddress2",
        "mailCityField": "MailCity",
        "mailStateField": "MailState",
        "mailZipField": "MailZip",
        "source": "al-elmore-parcels",
        "coverage": "complete-gte-5ac",
        "joinProfile": "elmore",
        "appraiserUrl": "https://isv.kcsgis.com/al.elmore_revenue/",
        "gaps": [
            NO_SALE_PRICE,
            "Public/133 is the county parcel source. Public_2022 was not used.",
            "Millbrook zoning is Millbrook_GIS_View/2 (Zone_). Null Zone_ polygons are skipped.",
            PRATTVILLE_VINTAGE,
            WETUMPKA_GAP,
        ],
    },
    "01001": {
        "kind": "arcgis",
        "url": "https://services1.arcgis.com/fWUhmUATXl9W5CJW/arcgis/rest/services/Autauga_Parcels/FeatureServer/0/query",
        "where": "CALC_ACRE>=5 AND CALC_ACRE<=150",
        "outFields": [
            "PARCELID",
            "PARCEL_NUMBER",
            "OWNER_NAME1",
            "MAILING_ADDRESS1",
            "MAILING_CITY",
            "MAILING_STATE",
            "MAILING_ZIP",
            "PROPERTY_ADDRESS1",
            "CALC_ACRE",
            "TOTAL_VALUE",
            "ASSD_VALUE",
        ],
        "idField": "PARCELID",
        "idFallbacks": ["PARCEL_NUMBER"],
        "acresField": "CALC_ACRE",
        "ownerField": "OWNER_NAME1",
        "situsField": "PROPERTY_ADDRESS1",
        "marketValueField": "TOTAL_VALUE",
        "assessedField": "ASSD_VALUE",
        "mail1Field": "MAILING_ADDRESS1",
        "mailCityField": "MAILING_CITY",
        "mailStateField": "MAILING_STATE",
        "mailZipField": "MAILING_ZIP",
        "source": "al-autauga-parcels",
        "coverage": "complete-gte-5ac",
        "joinProfile": "autauga",
        "appraiserUrl": "https://autauga.capturecama.com/parcelviewer",
        "gaps": [
            NO_SALE_PRICE,
            "Autauga_Parcels on the Prattville AGOL org is the owner and tax source. The county Ering map is geometry-only and was not used.",
            "No Autauga county zoning REST. Prattville zoning is joined by centroid where it overlaps.",
            PRATTVILLE_VINTAGE,
            "Prattville Future_Land_Use_Layer has 13 coarse polygons and was not joined as site-level FLU.",
        ],
    },
}

GAP_SPECS: dict[str, dict] = {
    "01065": {
        "kind": "gap",
        "source": "unavailable",
        "queryUrl": None,
        "gaps": [
            "Hale County has Flagship/CaptureCAMA HTML only. No usable public parcel REST in this pull. Polygons were not invented.",
        ],
    },
    "01107": {
        "kind": "gap",
        "source": "unavailable",
        "queryUrl": None,
        "gaps": [
            "Pickens County has Flagship/CaptureCAMA HTML only. No usable public parcel REST in this pull. Polygons were not invented.",
        ],
    },
    "01063": {
        "kind": "gap",
        "source": "unavailable",
        "queryUrl": None,
        "gaps": [
            "Greene County has Flagship/CaptureCAMA HTML only. No usable public parcel REST in this pull. Polygons were not invented.",
        ],
    },
    "01085": {
        "kind": "gap",
        "source": "unavailable",
        "queryUrl": None,
        "gaps": [
            "Lowndes County is in the Montgomery, AL MSA. No public parcel card was verified in this pull. Polygons were not invented.",
        ],
    },
}


def al_county_spec(fips: str) -> dict | None:
    spec = PARCEL_SPECS.get(fips) or GAP_SPECS.get(fips)
    if spec and spec.get("url"):
        assert_public_alabama_url(spec["url"])
    return spec


def assert_public_alabama_url(url: str) -> None:
    if NY_MONTGOMERY_ORG in url or "Montgomery_County_Parcels" in url:
        raise RuntimeError(f"Rejected NY Montgomery parcel mirror: {url}")
    if "6AasMFHPoqawuioF" in url or "Zoning_Districts_Public" in url:
        raise RuntimeError(f"Wetumpka zoning is token-gated and is not queried: {url}")
    if "Framework_Zoning_Map" in url:
        raise RuntimeError(f"Tuscaloosa Framework zoning draft is not joined: {url}")


def parcel_key(value: Any) -> str | None:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits or None


def epoch_to_iso(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed <= 0:
        return None
    seconds = parsed / 1000.0 if abs(parsed) > 10_000_000_000 else parsed
    try:
        stamp = datetime.fromtimestamp(seconds, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    if stamp.year < 1900 or stamp.year > 2100:
        return None
    return stamp.date().isoformat()


def parcel_only_market_summaries() -> list[dict]:
    """Camera envelopes only. rowCount 0 means no eligible-tract rows were added."""
    return [
        {
            "market": "Tuscaloosa",
            "rowCount": 0,
            "ruralCount": 0,
            "urbanCount": 0,
            "bounds": [[-88.5, 32.48], [-87.15, 33.6]],
            "center": [-87.825, 33.04],
            "counties": [],
            "parcelOnly": True,
            "eligibleTractNote": (
                "No Rev. Proc. 2026-14 eligible-tract rows were added. "
                "Nothing in this market is marked designated."
            ),
        },
        {
            "market": "Montgomery",
            "rowCount": 0,
            "ruralCount": 0,
            "urbanCount": 0,
            "bounds": [[-86.9, 31.98], [-85.9, 32.88]],
            "center": [-86.4, 32.43],
            "counties": [],
            "parcelOnly": True,
            "eligibleTractNote": (
                "No Rev. Proc. 2026-14 eligible-tract rows were added. "
                "Nothing in this market is marked designated."
            ),
        },
    ]


def _fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/al-msa-parcels"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            if data.get("error"):
                raise RuntimeError(json.dumps(data["error"])[:300])
            return data
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed {url[:140]}: {last}")


def _fetch_ids(url: str, where: str) -> list[int]:
    data = _fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"})
    return [int(i) for i in (data.get("objectIds") or [])]


def _fetch_features(url: str, ids: list[int], out_fields: list[str], batch: int = 100) -> list[dict]:
    features: list[dict] = []
    total = len(ids)
    for start in range(0, total, batch):
        chunk = ids[start : start + batch]
        try:
            data = _fetch_json(
                url,
                {
                    "objectIds": ",".join(str(i) for i in chunk),
                    "outFields": ",".join(out_fields),
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "json",
                },
            )
        except RuntimeError:
            if len(chunk) > 20:
                features.extend(_fetch_features(url, chunk, out_fields, batch=max(10, len(chunk) // 2)))
                continue
            raise
        features.extend(data.get("features") or [])
        done = min(start + len(chunk), total)
        if done == total or done % 500 == 0:
            print(f"    overlay {done}/{total}", flush=True)
        time.sleep(0.04)
    return features


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def geometry_bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(coords: Any) -> None:
        if isinstance(coords, (list, tuple)) and coords and isinstance(coords[0], (int, float)):
            xs.append(float(coords[0]))
            ys.append(float(coords[1]))
            return
        if isinstance(coords, list):
            for item in coords:
                walk(item)

    walk(geometry.get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        intersects = (yi > y) != (yj > y)
        if intersects:
            denom = (yj - yi) if (yj - yi) != 0 else 1e-20
            x_at = (xj - xi) * (y - yi) / denom + xi
            if x < x_at:
                inside = not inside
        j = i
    return inside


def point_in_geometry(x: float, y: float, geometry: dict | None) -> bool:
    if not geometry:
        return False
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        if not coords or not _point_in_ring(x, y, coords[0]):
            return False
        return all(not _point_in_ring(x, y, hole) for hole in coords[1:])
    if kind == "MultiPolygon":
        return any(
            poly and _point_in_ring(x, y, poly[0]) and all(not _point_in_ring(x, y, hole) for hole in poly[1:])
            for poly in coords
        )
    return False


def _index_zones(zones: list[dict]) -> dict[tuple[int, int], list[dict]]:
    index: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for zone in zones:
        west, south, east, north = zone["bbox"]
        for ix in range(math.floor(west / CELL), math.floor(east / CELL) + 1):
            for iy in range(math.floor(south / CELL), math.floor(north / CELL) + 1):
                index[(ix, iy)].append(zone)
    return index


def _zones_at(index: dict[tuple[int, int], list[dict]], lon: float, lat: float) -> list[dict]:
    hits = []
    for zone in index.get((math.floor(lon / CELL), math.floor(lat / CELL)), []):
        west, south, east, north = zone["bbox"]
        if lon < west or lon > east or lat < south or lat > north:
            continue
        if point_in_geometry(lon, lat, zone["geometry"]):
            hits.append(zone)
    return hits


def _choose(hits: list[dict]) -> dict:
    return min(hits, key=lambda zone: (zone["area"], zone["code"]))


def _load_zone_layer(
    *,
    url: str,
    where: str,
    out_fields: list[str],
    code_field: str,
    jurisdiction: str,
    label_field: str | None = None,
    key_field: str | None = None,
    vintage: str | None = None,
) -> list[dict]:
    assert_public_alabama_url(url)
    print(f"  overlay {jurisdiction} {url}", flush=True)
    ids = _fetch_ids(url, where)
    raw = _fetch_features(url, ids, out_fields)
    zones: list[dict] = []
    for item in raw:
        attrs = item.get("attributes") or {}
        code = _clean(attrs.get(code_field))
        if not code:
            continue
        rings = (item.get("geometry") or {}).get("rings")
        if not rings:
            continue
        geometry, acres = esri_rings_to_geojson(rings), abs(net_acres(rings))
        if not geometry:
            continue
        bbox = geometry_bbox(geometry)
        if not bbox:
            continue
        label = _clean(attrs.get(label_field)) if label_field else None
        zones.append(
            {
                "jurisdiction": jurisdiction,
                "code": code,
                "label": label if label and label != code else None,
                "key": parcel_key(attrs.get(key_field)) if key_field else None,
                "vintage": vintage,
                "area": acres or 0,
                "bbox": bbox,
                "geometry": geometry,
            }
        )
    print(f"    {len(zones)} {jurisdiction} polygons", flush=True)
    return zones


def load_overlays() -> dict[str, Any]:
    """Download city overlays once per process. Rejects the NY mirror and Wetumpka."""
    tuscaloosa = _load_zone_layer(
        url="https://services1.arcgis.com/DADyRNMb7tdzKmmq/arcgis/rest/services/Tuscaloosa_City_Zoning_Districts/FeatureServer/3/query",
        where="1=1",
        out_fields=["zone_class", "zone_descript"],
        code_field="zone_class",
        label_field="zone_descript",
        jurisdiction="City of Tuscaloosa",
    )
    northport = _load_zone_layer(
        url="https://services2.arcgis.com/3u10F1chkeawsUZY/arcgis/rest/services/NorthportZoning_Dec2024/FeatureServer/0/query",
        where="ZoningType IS NOT NULL",
        out_fields=["pclNUM", "ZoningType", "ZoningCode"],
        code_field="ZoningType",
        label_field="ZoningCode",
        key_field="pclNUM",
        jurisdiction="Northport",
    )
    flu = _load_zone_layer(
        url="https://services2.arcgis.com/3u10F1chkeawsUZY/arcgis/rest/services/FLU_240408/FeatureServer/0/query",
        where="FLU IS NOT NULL",
        out_fields=["FLU"],
        code_field="FLU",
        jurisdiction="Northport",
    )
    montgomery = _load_zone_layer(
        url="https://gis.montgomeryal.gov/server/rest/services/Zoning/FeatureServer/0/query",
        where="ZoningCode IS NOT NULL",
        out_fields=["ZoningCode", "ZoningDesc"],
        code_field="ZoningCode",
        label_field="ZoningDesc",
        jurisdiction="City of Montgomery",
    )
    millbrook = _load_zone_layer(
        url="https://services5.arcgis.com/ta6tVbcGxSaoQQNU/arcgis/rest/services/Millbrook_GIS_View/FeatureServer/2/query",
        where="Zone_ IS NOT NULL AND Zone_<>''",
        out_fields=["Zone_", "Zone_Description"],
        code_field="Zone_",
        label_field="Zone_Description",
        jurisdiction="Millbrook",
    )
    prattville = _load_zone_layer(
        url="https://services1.arcgis.com/fWUhmUATXl9W5CJW/arcgis/rest/services/ZONING_JULY_2017/FeatureServer/0/query",
        where="ZONING_07 IS NOT NULL AND ZONING_07<>''",
        out_fields=["ZONING_07", "DATE_ZONED"],
        code_field="ZONING_07",
        jurisdiction="Prattville",
        vintage=PRATTVILLE_VINTAGE,
    )
    northport_by_key: dict[str, dict] = {}
    for zone in northport:
        if zone["key"] and zone["key"] not in northport_by_key:
            northport_by_key[zone["key"]] = zone
    return {
        "tuscaloosa": _index_zones(tuscaloosa),
        "northportByKey": northport_by_key,
        "northport": _index_zones(northport),
        "flu": _index_zones(flu),
        "montgomery": _index_zones(montgomery),
        "millbrook": _index_zones(millbrook),
        "prattville": _index_zones(prattville),
    }


_OVERLAYS: dict[str, Any] | None = None
_OVERLAY_LOCK = threading.Lock()


def overlays() -> dict[str, Any]:
    global _OVERLAYS
    with _OVERLAY_LOCK:
        if _OVERLAYS is None:
            _OVERLAYS = load_overlays()
        return _OVERLAYS


def _assign_zone(props: dict, zone: dict) -> None:
    props["zoningCode"] = zone["code"]
    props["zoningDistrict"] = zone["label"]
    props["jurisdictionCode"] = zone["jurisdiction"]


def _centroid(props: dict) -> tuple[float, float] | None:
    center = props.get("centroid") or [None, None]
    lon, lat = center[0], center[1]
    if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
        return float(lon), float(lat)
    return None


def apply_joins_local(features: list[dict], profile: str, prepared: dict[str, Any], appraiser_url: str | None) -> None:
    """Stamp zoning, Northport FLU, and honest gaps. Does not set a sale price."""
    outside = {
        "tuscaloosa": "Centroid is outside City of Tuscaloosa zoning districts and Northport zoning. Framework_Zoning_Map was not used.",
        "montgomery": "Centroid is outside City of Montgomery Zoning/0.",
        "elmore": "Centroid is outside Millbrook zoning and Prattville zoning. Wetumpka zoning was not joined (HTTP 499).",
        "autauga": "Centroid is outside Prattville zoning.",
    }[profile]
    for feature in features:
        props = feature["properties"]
        sale = props.setdefault("lastSale", {"date": None, "price": None, "qualified": None})
        sale["price"] = None
        props["appraiserUrl"] = appraiser_url
        props["oz2Eligibility"] = None
        props["opportunityZone"] = None
        center = _centroid(props)
        zone = None
        if profile == "tuscaloosa":
            key = parcel_key(props.get("parcelId"))
            zone = prepared["northportByKey"].get(key) if key else None
            if zone is None and center:
                hits = _zones_at(prepared["northport"], *center) or _zones_at(prepared["tuscaloosa"], *center)
                zone = _choose(hits) if hits else None
            if center:
                flu_hits = _zones_at(prepared["flu"], *center)
                if flu_hits:
                    flu = _choose(flu_hits)
                    props["flu"] = {
                        "code": flu["code"],
                        "label": flu["label"] or flu["code"],
                        "jurisdiction": "Northport",
                        "source": "FLU_240408",
                    }
        elif profile == "montgomery":
            if center:
                hits = _zones_at(prepared["montgomery"], *center)
                zone = _choose(hits) if hits else None
        elif profile in {"elmore", "autauga"}:
            if center:
                hits = []
                if profile == "elmore":
                    hits.extend(_zones_at(prepared["millbrook"], *center))
                hits.extend(_zones_at(prepared["prattville"], *center))
                zone = _choose(hits) if hits else None
        if zone:
            _assign_zone(props, zone)
        else:
            props["zoningCode"] = None
            props["zoningDistrict"] = None
            props["jurisdictionCode"] = None
        gaps = [NO_SALE_PRICE]
        if zone and zone["jurisdiction"] == "Prattville":
            gaps.append(PRATTVILLE_VINTAGE)
        elif zone is None:
            gaps.append(outside)
        props["dataGaps"] = gaps


def apply_al_joins(features: list[dict], spec: dict) -> None:
    profile = spec.get("joinProfile")
    if not profile or not features:
        return
    apply_joins_local(features, profile, overlays(), spec.get("appraiserUrl"))


def summarize_joined(features: list[dict]) -> dict:
    by: dict[str, int] = {}
    zoning = flu = sale_date = sale_price = prattville = 0
    for feature in features:
        props = feature.get("properties") or {}
        if props.get("zoningCode"):
            zoning += 1
            jurisdiction = props.get("jurisdictionCode") or "unknown"
            by[jurisdiction] = by.get(jurisdiction, 0) + 1
            if jurisdiction == "Prattville":
                prattville += 1
        if (props.get("flu") or {}).get("code"):
            flu += 1
        sale = props.get("lastSale") or {}
        if sale.get("price"):
            sale_price += 1
        if sale.get("date"):
            sale_date += 1
    total = len(features)
    return {
        "featureCount": total,
        "zoningJoined": zoning,
        "zoningRate": round(zoning / total, 4) if total else 0,
        "byJurisdiction": by,
        "fluJoined": flu,
        "fluRate": round(flu / total, 4) if total else 0,
        "prattvilleJoined": prattville,
        "salePriceNonNull": sale_price,
        "saleDateNonNull": sale_date,
    }


def write_al_msa_doc(county_dir: Path, dest: Path) -> None:
    wanted = ["01125", "01101", "01051", "01001", "01065", "01107", "01063", "01085"]
    rows = []
    for fips in wanted:
        path = county_dir / fips / "county.json"
        if path.exists():
            rows.append(json.loads(path.read_text()))
    lines = [
        "# Tuscaloosa and Montgomery MSA parcels",
        "",
        "Public GIS only. Acreage band is 5.0–150.0 inclusive. Sale price is null on every parcel.",
        "These markets have no new eligible-tract rows. Nothing here is an Opportunity Zone designation.",
        "",
        f"Rejected: `{NY_MONTGOMERY_PARCEL_MIRROR}` (New York East / Amsterdam sample, SWIS fields).",
        f"Not queried: `{WETUMPKA_ZONING_SERVICE}` (HTTP 499).",
        f"Not joined: `{FRAMEWORK_ZONING_SERVICE}` (draft, not the official zoning map).",
        "",
        PRATTVILLE_VINTAGE,
        "",
        "## Counties",
        "",
        "| County | FIPS | Parcels | Source count | Zoning joined | FLU joined | Sale dates | Sale prices |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        join = row.get("join") or {}
        lines.append(
            "| {name} | {fips} | {count:,} | {source} | {zoning} | {flu} | {dates} | {prices} |".format(
                name=row["name"],
                fips=row["fips"],
                count=int(row.get("featureCount") or 0),
                source=row.get("sourceCount") if row.get("sourceCount") is not None else "—",
                zoning=join.get("zoningJoined", "—"),
                flu=join.get("fluJoined", "—"),
                dates=join.get("saleDateNonNull", "—"),
                prices=join.get("salePriceNonNull", "—"),
            )
        )
    lines.extend(["", "## Zoning by city", ""])
    for row in rows:
        join = row.get("join") or {}
        by = join.get("byJurisdiction") or {}
        if not by and not join:
            continue
        rate = join.get("zoningRate")
        rate_text = f"{rate:.1%}" if isinstance(rate, float) else "—"
        bits = ", ".join(f"{name} {count:,}" for name, count in sorted(by.items())) or "none"
        lines.append(f"- **{row['name']}** ({row['fips']}): zoning join rate {rate_text} ({bits}).")
    lines.extend(
        [
            "",
            "## Remaining gaps",
            "",
            "- Hale County (01065), Pickens County (01107), and Greene County (01063): no public parcel REST.",
            "- Bibb County (01007): still a Birmingham parcel gap. No public REST in this pull.",
            "- Lowndes County (01085): Montgomery MSA county with no verified public parcel card.",
            "- Wetumpka: token-gated zoning (HTTP 499). Not joined.",
            "- Prattville future land use is 13 coarse polygons and was not joined as site-level FLU.",
            "- City of Montgomery has no separate public FLU FeatureServer in this pull.",
            "",
        ]
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n")
