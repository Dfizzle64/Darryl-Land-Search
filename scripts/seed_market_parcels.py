#!/usr/bin/env python3
"""Seed 5.0–150.0 acre parcel tiles for every MSA except Orlando.

Orlando stays on data/fixtures/orlando-parcels. Counties that already have a
complete Orlando extract (Orange, Osceola, Polk) are referenced, not re-downloaded.

  python3 scripts/seed_market_parcels.py
  python3 scripts/seed_market_parcels.py --market Tampa
  python3 scripts/seed_market_parcels.py --county Hardee --market Tampa
  python3 scripts/seed_market_parcels.py --refresh

Tile origin matches ORLANDO_PARCEL_TILE in src/lib/orlandoParcels.ts.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import threading
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "market-parcel-counties.json"
OUT_DIR = ROOT / "data" / "fixtures" / "market-parcels"
COUNTY_DIR = OUT_DIR / "counties"
MARKET_DIR = OUT_DIR / "markets"
ORLANDO_DIR = ROOT / "data" / "fixtures" / "orlando-parcels"
CACHE_DIR = Path("/tmp/dls-market-parcels")
DOH_BASE = "https://gis.floridahealth.gov/server/rest/services/EHWATER/Parcels/MapServer"

# Keep in sync with src/lib/orlandoParcels.ts ORLANDO_PARCEL_TILE.
ORIGIN_LON = -83.0
ORIGIN_LAT = 27.0
TILE_DEG = 0.25
MIN_ACRES = 5.0
MAX_ACRES = 150.0
MIN_SQFT = 217800
MAX_SQFT = 6534000

# Complete Orlando extracts reused as-is. Sample Orlando counties are not reused.
ORLANDO_REUSE = {"12095", "12097", "12105"}

FL_DOH_LAYER = {
    "12009": 4,
    "12017": 8,
    "12033": 15,
    "12049": 23,
    "12053": 25,
    "12057": 27,
    "12061": 29,
    "12081": 39,
    "12085": 41,
    "12091": 45,
    "12093": 46,
    "12101": 50,
    "12103": 51,
    "12111": 55,
    "12113": 56,
    "12115": 57,
    "12119": 59,
    "12127": 63,
    "12131": 65,
}

NC_URL = "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1/query"
TN_URL = "https://maps.cot.tn.gov/server3/rest/services/IMPACT/Parcels/FeatureServer/0/query"
MS_URL = "https://mgis19.mdeq.ms.gov/arcgis/rest/services/GeologyParcelAndFloodGIS/Parcels_Statewide_2023/FeatureServer/3/query"
AR_URL = "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6/query"

DOH_FIELDS = [
    "PARCEL_ID",
    "OWN_NAME",
    "PHY_ADDR1",
    "PHY_CITY",
    "PHY_ZIPCD",
    "LND_SQFOOT",
    "JV",
    "AV_SD",
    "TV_SD",
    "DOR_UC",
    "SALE_PRC1",
    "SALE_YR1",
    "SALE_MO1",
    "QUAL_CD1",
    "OWN_ADDR1",
    "OWN_ADDR2",
    "OWN_CITY",
    "OWN_STATE",
    "OWN_ZIPCD",
]

WRITE_LOCK = threading.Lock()


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/market-parcels"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:160]}: {last}")


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def zip_str(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return text[:10]


def in_band(acres: float | None) -> bool:
    return acres is not None and MIN_ACRES <= acres <= MAX_ACRES


def slug(market: str) -> str:
    return market.lower().replace(" ", "-")


def perp_dist(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def douglas_peucker(points: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points
    stack = [(0, len(points) - 1)]
    keep = {0, len(points) - 1}
    while stack:
        start, end = stack.pop()
        max_d = 0.0
        idx = None
        for i in range(start + 1, end):
            dist = perp_dist(points[i], points[start], points[end])
            if dist > max_d:
                max_d = dist
                idx = i
        if idx is not None and max_d > tol:
            keep.add(idx)
            stack.append((start, idx))
            stack.append((idx, end))
    return [points[i] for i in sorted(keep)]


def simplify_ring(coords: list[list[float]], tol: float = 0.00008) -> list[list[float]]:
    if len(coords) <= 4:
        return [[round(x, 5), round(y, 5)] for x, y in coords]
    open_ring = coords[:-1] if coords[0] == coords[-1] else list(coords)
    pts = [(float(x), float(y)) for x, y in open_ring]
    use = tol
    if len(pts) > 900:
        use = max(tol, 0.00028)
    elif len(pts) > 280:
        use = max(tol, 0.00014)
    simplified = douglas_peucker(pts, use)
    if len(simplified) < 3:
        step = max(1, len(pts) // 12)
        simplified = pts[::step][:12]
    if simplified[0] != simplified[-1]:
        simplified = simplified + [simplified[0]]
    if len(simplified) < 4:
        simplified = pts[:3] + [pts[0]]
    return [[round(x, 5), round(y, 5)] for x, y in simplified]


def ring_signed_m2(coords: list[list[float]]) -> float:
    """Signed area in square meters. Clockwise ArcGIS rings are negative."""
    if len(coords) < 4:
        return 0.0
    lat0 = sum(p[1] for p in coords) / len(coords)
    kx = 111_320 * math.cos(math.radians(lat0))
    ky = 110_540
    area = 0.0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i][0] * kx, coords[i][1] * ky
        x2, y2 = coords[i + 1][0] * kx, coords[i + 1][1] * ky
        area += x1 * y2 - x2 * y1
    return area / 2.0


def rings_to_feature_geometry(geom: dict | None) -> tuple[dict | None, float]:
    if not geom or not geom.get("rings"):
        return None, 0.0
    polygons: list[list[list[list[float]]]] = []
    current: list[list[list[float]]] = []
    net_m2 = 0.0
    for ring in geom["rings"]:
        raw = [[float(x), float(y)] for x, y in ring]
        if len(raw) < 4:
            continue
        net_m2 += ring_signed_m2(raw)
        coords = simplify_ring(raw)
        if len(coords) < 4:
            continue
        area = 0.0
        for i in range(len(coords) - 1):
            area += coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1]
        if not current or area > 0:
            if current:
                polygons.append(current)
            current = [coords]
        else:
            current.append(coords)
    if current:
        polygons.append(current)
    acres = abs(net_m2) / 4046.8564224
    if not polygons:
        return None, acres
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}, acres
    return {"type": "MultiPolygon", "coordinates": polygons}, acres


def centroid_of(geometry: dict) -> tuple[float, float] | None:
    ring = None
    if geometry.get("type") == "Polygon":
        ring = geometry["coordinates"][0]
    elif geometry.get("type") == "MultiPolygon" and geometry["coordinates"]:
        ring = geometry["coordinates"][0][0]
    if not ring:
        return None
    pts = ring[:-1] if len(ring) > 1 else ring
    if not pts:
        return None
    lon = sum(p[0] for p in pts) / len(pts)
    lat = sum(p[1] for p in pts) / len(pts)
    return round(lon, 6), round(lat, 6)


def plausible_centroid(center: tuple[float, float] | None) -> bool:
    if not center:
        return False
    lon, lat = center
    return -93.5 < lon < -75 and 24 < lat < 37.6


def empty_feature(
    *,
    fips: str,
    county: str,
    state: str,
    markets: list[str],
    parcel_id: str,
    acreage: float,
    geometry: dict,
    center: tuple[float, float],
    source: str,
    owner: str | None = None,
    situs: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
    zoning: str | None = None,
    dor: str | None = None,
    sale_price: float | None = None,
    sale_date: str | None = None,
    sale_qualified: str | None = None,
    market_value: float | None = None,
    assessed: float | None = None,
    taxable: float | None = None,
    mail1: str | None = None,
    mail2: str | None = None,
    mail_city: str | None = None,
    mail_state: str | None = None,
    mail_zip: str | None = None,
) -> dict:
    feature_id = f"{fips}:{parcel_id}"
    return {
        "type": "Feature",
        "id": feature_id,
        "properties": {
            "id": feature_id,
            "parcelId": parcel_id,
            "countyFips": fips,
            "countyName": county,
            "state": state,
            "marketIds": markets,
            "situsAddress": situs,
            "situsCity": city,
            "situsZip": zip_code,
            "jurisdictionCode": None,
            "ownerName": owner,
            "ownerName2": None,
            "propertyName": None,
            "zoningCode": zoning,
            "zoningDistrict": None,
            "jurisdictionPrefix": None,
            "dorCode": dor,
            "acreage": round(acreage, 4),
            "centroid": [center[0], center[1]],
            "lastSale": {"date": sale_date, "price": sale_price, "qualified": sale_qualified},
            "tax": {
                "marketValue": market_value,
                "assessedValue": assessed,
                "taxableValue": taxable,
                "taxes": None,
            },
            "mailingAddress": {
                "line1": mail1,
                "line2": mail2,
                "city": mail_city,
                "state": mail_state,
                "zip": mail_zip,
            },
            "incomeTract": None,
            "incomeBlockGroup": None,
            "nearestRoad": None,
            "flu": None,
            "opportunityZone": None,
            "oz2Eligibility": None,
            "source": source,
        },
        "geometry": geometry,
    }


def count_where(url: str, where: str) -> int:
    data = fetch_json(url, {"where": where, "returnCountOnly": "true", "f": "json"})
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    count = data.get("count")
    if not isinstance(count, int):
        raise RuntimeError(f"No count from {url}: {str(data)[:200]}")
    return count


def fetch_object_ids(url: str, where: str) -> list[int]:
    data = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    return [int(i) for i in (data.get("objectIds") or [])]


def fetch_by_ids(url: str, ids: list[int], out_fields: list[str], batch: int = 120) -> list[dict]:
    features: list[dict] = []
    total = len(ids)
    params = {
        "outFields": ",".join(out_fields),
        "returnGeometry": "true",
        "outSR": "4326",
    }
    for start in range(0, total, batch):
        chunk = ids[start : start + batch]
        query = dict(params)
        query["objectIds"] = ",".join(str(i) for i in chunk)
        query["f"] = "json"
        try:
            data = fetch_json(url, query, timeout=180)
        except RuntimeError:
            if len(chunk) > 30:
                features.extend(fetch_by_ids(url, chunk, out_fields, batch=max(20, len(chunk) // 2)))
                continue
            raise
        if data.get("error"):
            if len(chunk) > 30:
                features.extend(fetch_by_ids(url, chunk, out_fields, batch=max(20, len(chunk) // 2)))
                continue
            raise RuntimeError(json.dumps(data["error"])[:300])
        features.extend(data.get("features") or [])
        done = min(start + len(chunk), total)
        if done == len(chunk) or done == total or done % 480 == 0:
            print(f"    {done}/{total}", flush=True)
        time.sleep(0.05)
    return features


def sale_date(year: Any, month: Any) -> str | None:
    y = num(year)
    if y is None or y < 1900 or y > 2100:
        return None
    m = num(month)
    month_num = int(m) if m and 1 <= m <= 12 else 1
    return f"{int(y):04d}-{month_num:02d}-01"


def normalize_rows(
    raw: list[dict],
    county: dict,
    markets: list[str],
    spec: dict,
) -> tuple[list[dict], int]:
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, computed = rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            dropped += 1
            continue
        center = centroid_of(geometry)
        if not plausible_centroid(center):
            dropped += 1
            continue
        acres = num(attrs.get(spec["acresField"])) if spec.get("acresField") else None
        scale = spec.get("acresScale") or 1
        if acres is not None and scale != 1:
            acres = acres / scale
        if spec.get("computeAcres") or acres is None:
            acres = computed
        if not in_band(acres):
            dropped += 1
            continue
        parcel_id = clean(attrs.get(spec["idField"])) if spec.get("idField") else None
        if not parcel_id:
            for key in spec.get("idFallbacks") or []:
                parcel_id = clean(attrs.get(key))
                if parcel_id:
                    break
        if not parcel_id:
            oid = attrs.get("OBJECTID") or attrs.get("objectid")
            parcel_id = clean(oid)
        if not parcel_id:
            dropped += 1
            continue
        price = num(attrs.get(spec["salePriceField"])) if spec.get("salePriceField") else None
        if price is not None and price <= 0:
            price = None
        feature = empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,  # type: ignore[arg-type]
            source=spec["source"],
            owner=clean(attrs.get(spec["ownerField"])) if spec.get("ownerField") else None,
            situs=clean(attrs.get(spec["situsField"])) if spec.get("situsField") else None,
            city=clean(attrs.get(spec["cityField"])) if spec.get("cityField") else None,
            zip_code=zip_str(attrs.get(spec["zipField"])) if spec.get("zipField") else None,
            zoning=clean(attrs.get(spec["zoningField"])) if spec.get("zoningField") else None,
            dor=clean(attrs.get(spec["dorField"])) if spec.get("dorField") else None,
            sale_price=price,
            sale_date=sale_date(attrs.get("SALE_YR1"), attrs.get("SALE_MO1")) if spec.get("saleYearField") else None,
            sale_qualified=clean(attrs.get("QUAL_CD1")) if spec.get("saleYearField") else None,
            market_value=num(attrs.get(spec["marketValueField"])) if spec.get("marketValueField") else None,
            assessed=num(attrs.get(spec["assessedField"])) if spec.get("assessedField") else None,
            taxable=num(attrs.get(spec["taxableField"])) if spec.get("taxableField") else None,
            mail1=clean(attrs.get(spec["mail1Field"])) if spec.get("mail1Field") else None,
            mail2=clean(attrs.get(spec["mail2Field"])) if spec.get("mail2Field") else None,
            mail_city=clean(attrs.get(spec["mailCityField"])) if spec.get("mailCityField") else None,
            mail_state=clean(attrs.get(spec["mailStateField"])) if spec.get("mailStateField") else None,
            mail_zip=zip_str(attrs.get(spec["mailZipField"])) if spec.get("mailZipField") else None,
        )
        if spec.get("appraiserHtmlField"):
            feature["properties"]["appraiserUrl"] = qpublic_href(
                attrs.get(spec["appraiserHtmlField"]), parcel_id
            )
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def fl_spec(fips: str) -> dict:
    layer = FL_DOH_LAYER[fips]
    return {
        "kind": "arcgis",
        "url": f"{DOH_BASE}/{layer}/query",
        "where": f"LND_SQFOOT >= {MIN_SQFT} AND LND_SQFOOT <= {MAX_SQFT}",
        "outFields": DOH_FIELDS,
        "idField": "PARCEL_ID",
        "acresField": "LND_SQFOOT",
        "acresScale": 43560,
        "ownerField": "OWN_NAME",
        "situsField": "PHY_ADDR1",
        "cityField": "PHY_CITY",
        "zipField": "PHY_ZIPCD",
        "dorField": "DOR_UC",
        "salePriceField": "SALE_PRC1",
        "saleYearField": "SALE_YR1",
        "marketValueField": "JV",
        "assessedField": "AV_SD",
        "taxableField": "TV_SD",
        "mail1Field": "OWN_ADDR1",
        "mail2Field": "OWN_ADDR2",
        "mailCityField": "OWN_CITY",
        "mailStateField": "OWN_STATE",
        "mailZipField": "OWN_ZIPCD",
        "source": f"fl-doh-ehwaters-{fips}",
        "coverage": "complete-gte-5ac",
        "gaps": ["No zoning or FLU on the Florida DOH extract."],
    }


def nc_spec(fips: str) -> dict:
    county3 = fips[2:]
    return {
        "kind": "arcgis",
        "url": NC_URL,
        "where": f"cntyfips='{county3}' AND gisacres>=5 AND gisacres<=150",
        "outFields": ["parno", "ownname", "siteadd", "scity", "gisacres", "cntyfips", "parval", "landval", "saledatetx"],
        "idField": "parno",
        "acresField": "gisacres",
        "ownerField": "ownname",
        "situsField": "siteadd",
        "cityField": "scity",
        "marketValueField": "parval",
        "assessedField": "landval",
        "source": f"nc-onemap-{fips}",
        "coverage": "complete-gte-5ac",
        "gaps": ["NC OneMap gisacres is GIS acreage, not a deed acreage field. No zoning join."],
        "fallbackWhere": f"cntyfips='{county3}'",
        "fallbackNote": "NC OneMap gisacres is 0 for this county. Acres were computed from the polygon and then limited to 5.0–150.0.",
    }


def tn_spec(fips: str) -> dict:
    county_id = int(fips[2:])
    return {
        "kind": "arcgis",
        "url": TN_URL,
        "where": f"COUNTY_ID={county_id} AND CALC_ACRE>=5 AND CALC_ACRE<=150",
        "outFields": ["GISLINK", "COUNTY_ID", "CALC_ACRE", "PARCELWP"],
        "idField": "GISLINK",
        "acresField": "CALC_ACRE",
        "source": f"tn-impact-{fips}",
        "coverage": "complete-gte-5ac",
        "gaps": [
            "Tennessee Comptroller IMPACT parcel layer has calculated acres and a GIS link. Owner, situs, and zoning are not on this layer.",
        ],
        "emptyGap": "Tennessee IMPACT Parcels returned no 5–150 acre features for this county. Davidson-scale counties are sometimes hosted only by the county, and several Nashville-ring counties are absent from this statewide layer.",
    }


def ms_spec(fips: str) -> dict:
    county3 = fips[2:]
    return {
        "kind": "arcgis",
        "url": MS_URL,
        "where": f"CNTYFIPS='{county3}' AND GISACRES>=5 AND GISACRES<=150",
        "outFields": ["PARNO", "OWNNAME", "SITEADD", "SCITY", "SZIP", "GISACRES", "CNTYNAME", "STCNTYFIPS"],
        "idField": "PARNO",
        "acresField": "GISACRES",
        "ownerField": "OWNNAME",
        "situsField": "SITEADD",
        "cityField": "SCITY",
        "zipField": "SZIP",
        "source": f"ms-mdeq-2023-{fips}",
        "coverage": "complete-gte-5ac",
        "gaps": ["Mississippi MDEQ 2023 statewide parcels. GIS acres, no zoning join. Vintage is 2023, not a live roll."],
    }


def ar_spec(fips: str) -> dict:
    return {
        "kind": "arcgis",
        "url": AR_URL,
        "where": f"countyfips='{fips}'",
        "outFields": ["parcelid", "ownername", "adrlabel", "adrcity", "adrzip5", "countyfips", "assessvalue", "landvalue", "totalvalue"],
        "idField": "parcelid",
        "computeAcres": True,
        "ownerField": "ownername",
        "situsField": "adrlabel",
        "cityField": "adrcity",
        "zipField": "adrzip5",
        "assessedField": "assessvalue",
        "marketValueField": "totalvalue",
        "source": f"ar-cadastre-{fips}",
        "coverage": "complete-gte-5ac",
        "gaps": [
            "Arkansas cadastre has no acreage field. Stored acres are computed from the polygon. The state notes some counties are not countywide.",
        ],
    }


QPUBLIC_HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)
HENRY_APPRAISER_SEARCH = "https://qpublic.schneidercorp.com/Application.aspx?App=HenryCountyGA&PageType=Search"
HENRY_QPUBLIC = (
    "https://qpublic.schneidercorp.com/Application.aspx?AppID=1035&LayerID=22139"
    "&PageTypeID=4&PageID=15803&KeyValue="
)
# Padded Henry County parcel extent (WGS84). Centroids are computed from simplified rings.
HENRY_LON_MIN, HENRY_LAT_MIN, HENRY_LON_MAX, HENRY_LAT_MAX = -84.45, 33.22, -83.85, 33.72
HENRY_OTHER_CITIES = {"stockbridge", "hampton", "locust grove"}

HENRY_PARCELS_URL = "https://arcgis.co.henry.ga.us/server/rest/services/Parcels/MapServer/12/query"
HENRY_ZONING_URL = (
    "https://arcgis.co.henry.ga.us/server/rest/services/Current_Zoning_and_Future_Land_Use/MapServer/0/query"
)
HENRY_FLU_URL = "https://arcgis.co.henry.ga.us/server/rest/services/Planning/Future_Land_Use/FeatureServer/0/query"
HENRY_MCDONOUGH_CLIP_URL = "https://arcgis.co.henry.ga.us/server/rest/services/McDonough/FeatureServer/3/query"
HENRY_STOCKBRIDGE_CLIP_URL = "https://arcgis.co.henry.ga.us/server/rest/services/Stockbridge/FeatureServer/2/query"
HENRY_LOCUST_GROVE_CLIP_URL = (
    "https://arcgis.co.henry.ga.us/server/rest/services/Locust_Grove/Locust_Grove/FeatureServer/1/query"
)
HENRY_GMC_ZONING_URL = (
    "https://services3.arcgis.com/7ScJ8q0HhcQyXcHe/arcgis/rest/services/mcd_Planning_view/FeatureServer/1/query"
)
HENRY_GMC_PARCELS_URL = (
    "https://services3.arcgis.com/7ScJ8q0HhcQyXcHe/arcgis/rest/services/mcd_Planning_view/FeatureServer/0/query"
)

HENRY_GAPS = [
    "County Parcels/MapServer/12 has situs and ACREAGE_1. It does not publish ownerName, mailing address, tax values, or last sale. CAMA is qPublic HTML (AppID=1035, LayerID=22139, PageTypeID=4, PageID=15803, KeyValue=PARCEL_NO). The deep link is stored on each parcel.",
    "Zoning is joined from Current_Zoning_and_Future_Land_Use/MapServer/0 on PARCEL_NO. Unincorporated parcels use ZONING. When ZONING is CITY the county CityZoning stub is the fallback. McDonough prefers GMC mcd_Planning_view/FeatureServer/1 district polygons (centroid in polygon), then county McDonough/FeatureServer/3. Stockbridge uses county Stockbridge/FeatureServer/2. Locust Grove uses county Locust_Grove/FeatureServer/1. Hampton has no city REST; CityZoning stub only. Flippen is unincorporated and has no city layer.",
    "Rejected services8.arcgis.com/gbzZfTaSTnfRdQPt (CITYNAME=Mustang, ST_FIPS=40, Oklahoma) as a wrong-state Hampton lookalike. It is not queried.",
    "FLU is Planning/Future_Land_Use/FeatureServer/0 FLU2023 joined on PARCEL_NO. Code CITY is not stored; city comprehensive-plan FLU is PDF, not REST. The layer publishes codes without a legend expansion, so the code is the label. Parcel-layer ZONING and FUTURE_LAN are often null and are not the join source.",
    "McDonough owner names come only from GMC mcd_Planning_view/FeatureServer/0 OWNER_NAME when the parcel is inside McDonough (FLU municipal, county city clip, or a GMC zoning hit when municipal is blank). GMC ACRES is not used (often 0; the GMC count does not match the county clip). That layer has no mailing, tax, or sale.",
    "Stockbridge city AGOL webapp was not used (item inaccessible). No Locust Grove or Hampton city-owned zoning FeatureServer was verified. No emails or phones. No paid vendors.",
    "POSTALCITY can include Ellenwood, Rex, Jonesboro, Jackson, or Jenkinsburg. Those are postal places, not Henry incorporated municipalities. Incorporated names on FLU MUNICIPAL are McDonough, Stockbridge, Hampton, and Locust Grove. Flippen is unincorporated and has no city layer.",
]


def prefer_henry_zoning(old: dict, new: dict) -> dict:
    """Stacked zoning rows: keep a real district over a blank or CITY-only stub."""

    def rank(attrs: dict) -> int:
        zoning = (clean_code(attrs.get("ZONING")) or "").upper()
        city = clean_code(attrs.get("CityZoning")) or ""
        if zoning and zoning != "CITY":
            return 3
        if city:
            return 2
        if zoning:
            return 1
        return 0

    return new if rank(new) > rank(old) else old


def prefer_henry_flu(old: dict, new: dict) -> dict:
    def rank(attrs: dict) -> int:
        code = (clean_code(attrs.get("FLU2023")) or "").upper()
        municipal = clean(attrs.get("MUNICIPAL")) or ""
        score = 0
        if code and code != "CITY":
            score += 4
        elif code == "CITY":
            score += 1
        if municipal:
            score += 2
        return score

    return new if rank(new) > rank(old) else old


def qpublic_href(raw: Any, parcel_id: str) -> str:
    text = clean(raw) or ""
    match = QPUBLIC_HREF_RE.search(text)
    if match:
        return match.group(1).replace("&amp;", "&")
    return HENRY_QPUBLIC + urllib.parse.quote(parcel_id, safe="")


def clean_code(value: Any) -> str | None:
    text = clean(value)
    if not text or text.upper() in {"NULL", "NONE", "N/A", "NA"}:
        return None
    return text


def henry_municipal(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    return {
        "henry county": "Henry County",
        "mcdonough": "McDonough",
        "stockbridge": "Stockbridge",
        "hampton": "Hampton",
        "locust grove": "Locust Grove",
        "flippen": "Flippen",
    }.get(text.lower(), text)


def fetch_paged(
    url: str,
    where: str,
    out_fields: list[str],
    *,
    geometry: bool,
    page_size: int = 2000,
) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    last_first: Any = None
    fields = list(out_fields)
    if "OBJECTID" not in fields and "objectid" not in fields:
        fields = ["OBJECTID", *fields]
    for _page in range(80):
        params: dict[str, str] = {
            "where": where,
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "resultOffset": str(offset),
            "resultRecordCount": str(page_size),
            "orderByFields": "OBJECTID",
            "f": "json",
        }
        if geometry:
            params["outSR"] = "4326"
        data = fetch_json(url, params, timeout=180)
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        batch = data.get("features") or []
        if not batch:
            break
        first_oid = (batch[0].get("attributes") or {}).get("OBJECTID")
        if first_oid is not None and first_oid == last_first:
            raise RuntimeError(f"Pagination stuck at OBJECTID {first_oid} for {url[:80]}")
        last_first = first_oid
        rows.extend(batch)
        print(f"    paged {len(rows)} {url.split('/rest/services/')[-1][:72]}", flush=True)
        if len(batch) < page_size:
            break
        offset += len(batch)
        time.sleep(0.05)
    return rows


def fetch_attrs_in(
    url: str,
    id_field: str,
    ids: list[str],
    out_fields: list[str],
    batch: int = 80,
    prefer=None,
) -> dict[str, dict]:
    found: dict[str, dict] = {}
    total = len(ids)
    label = url.split("/rest/services/")[-1][:64]
    for start in range(0, total, batch):
        chunk = ids[start : start + batch]
        quoted = ",".join("'" + pid.replace("'", "''") + "'" for pid in chunk)
        data = fetch_json(
            url,
            {
                "where": f"{id_field} IN ({quoted})",
                "outFields": ",".join(out_fields),
                "returnGeometry": "false",
                "f": "json",
            },
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        for row in data.get("features") or []:
            attrs = row.get("attributes") or {}
            pid = clean(attrs.get(id_field))
            if not pid:
                continue
            if pid in found and prefer:
                found[pid] = prefer(found[pid], attrs)
            else:
                found[pid] = attrs
        done = min(start + len(chunk), total)
        if done == len(chunk) or done == total or done % (batch * 10) == 0:
            print(f"    joined {done}/{total} {label}", flush=True)
        time.sleep(0.02)
    return found


def fetch_attributes_once(url: str, where: str, out_fields: list[str]) -> list[dict]:
    """One page, no OBJECTID order. Henry city clips use FID and are under maxRecordCount."""
    data = fetch_json(
        url,
        {
            "where": where,
            "outFields": ",".join(out_fields),
            "returnGeometry": "false",
            "resultRecordCount": "2000",
            "f": "json",
        },
        timeout=180,
    )
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    rows = data.get("features") or []
    if data.get("exceededTransferLimit"):
        raise RuntimeError(f"Attribute query needs another page: {url[:100]}")
    return rows


def index_by_parcel(rows: list[dict], id_field: str, needed: set[str] | None = None) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for row in rows:
        attrs = row.get("attributes") or {}
        pid = clean(attrs.get(id_field))
        if not pid:
            continue
        if needed is not None and pid not in needed:
            continue
        found[pid] = attrs
    return found


def point_in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    count = len(ring)
    if count < 3:
        return False
    previous = count - 1
    for index in range(count):
        x1, y1 = ring[index][0], ring[index][1]
        x2, y2 = ring[previous][0], ring[previous][1]
        if (y1 > lat) != (y2 > lat):
            span = y2 - y1
            if span != 0:
                x_cross = (x2 - x1) * (lat - y1) / span + x1
                if lon < x_cross:
                    inside = not inside
        previous = index
    return inside


class ZoningPolyIndex:
    """Each ArcGIS ring is tested on its own. The smallest containing ring wins.

    Multipart district polygons stay searchable, and a ring inside another ring
    (a smaller district, or a hole stored on the same feature) keeps that feature's
    code instead of being dropped as a hole.
    """

    def __init__(self, raw: list[dict]):
        self.items: list[tuple[tuple[float, float, float, float], list, str, float]] = []
        for item in raw:
            code = clean_code((item.get("attributes") or {}).get("CODE"))
            rings = (item.get("geometry") or {}).get("rings") or []
            if not code:
                continue
            for ring in rings:
                if len(ring) < 4:
                    continue
                xs = [point[0] for point in ring]
                ys = [point[1] for point in ring]
                area = 0.0
                for index in range(len(ring) - 1):
                    area += ring[index][0] * ring[index + 1][1] - ring[index + 1][0] * ring[index][1]
                self.items.append(((min(xs), min(ys), max(xs), max(ys)), ring, code, abs(area) / 2.0 or 1.0))

    def hit(self, lon: float, lat: float) -> str | None:
        hits: list[tuple[float, str]] = []
        for (minx, miny, maxx, maxy), ring, code, area in self.items:
            if lon < minx or lon > maxx or lat < miny or lat > maxy:
                continue
            if point_in_ring(lon, lat, ring):
                hits.append((area, code))
        if not hits:
            return None
        hits.sort()
        return hits[0][1]


def enrich_henry_features(features: list[dict], spec: dict) -> None:
    """Join Henry zoning, FLU, city overlays, McDonough owner, and qPublic gaps.

    Owner, mailing, tax, and sale stay empty except McDonough ownerName. County
    FLU code CITY is left unset. Mustang, Oklahoma is never requested.
    """
    needed = {feature["properties"]["parcelId"] for feature in features}
    print(f"  Henry enrich for {len(needed)} parcels", flush=True)
    print("  zoning attributes", flush=True)
    id_list = sorted(needed)
    zoning_by_id = fetch_attrs_in(
        HENRY_ZONING_URL,
        "PARCEL_NO",
        id_list,
        ["PARCEL_NO", "ZONING", "CityZoning", "Spl_Zoning"],
        prefer=prefer_henry_zoning,
    )
    print("  FLU attributes", flush=True)
    flu_by_id = fetch_attrs_in(
        HENRY_FLU_URL,
        "PARCEL_NO",
        id_list,
        ["PARCEL_NO", "FLU2023", "MUNICIPAL"],
        prefer=prefer_henry_flu,
    )
    band = "ACREAGE_1>=5 AND ACREAGE_1<=150"
    print("  city zoning clips", flush=True)
    mcd_clip = index_by_parcel(
        fetch_attributes_once(HENRY_MCDONOUGH_CLIP_URL, band, ["PARCEL_NO", "ZONING", "MUNICIPAL"]),
        "PARCEL_NO",
    )
    stock_clip = index_by_parcel(
        fetch_attributes_once(HENRY_STOCKBRIDGE_CLIP_URL, band, ["PARCEL_NO", "ZONING"]),
        "PARCEL_NO",
    )
    locust_clip = index_by_parcel(
        fetch_attributes_once(HENRY_LOCUST_GROVE_CLIP_URL, band, ["PARCEL_NO", "ZONING"]),
        "PARCEL_NO",
    )
    print(
        f"    clips McDonough {len(mcd_clip)} Stockbridge {len(stock_clip)} Locust Grove {len(locust_clip)}",
        flush=True,
    )
    print("  GMC McDonough zoning polygons", flush=True)
    gmc_index = ZoningPolyIndex(
        fetch_paged(HENRY_GMC_ZONING_URL, "1=1", ["CODE", "Display", "Descri"], geometry=True, page_size=200)
    )
    print(f"    GMC polygons {len(gmc_index.items)}", flush=True)
    print("  GMC McDonough owner names", flush=True)
    owners = index_by_parcel(
        fetch_paged(HENRY_GMC_PARCELS_URL, "1=1", ["PARCEL_ID", "OWNER_NAME"], geometry=False),
        "PARCEL_ID",
    )

    def clip_misses(municipal_name: str, clip: dict[str, dict]) -> list[str]:
        missing = []
        for feature in features:
            pid = feature["properties"]["parcelId"]
            municipal = henry_municipal((flu_by_id.get(pid) or {}).get("MUNICIPAL"))
            if municipal == municipal_name and pid not in clip:
                missing.append(pid)
        return missing

    for municipal_name, clip, url in (
        ("McDonough", mcd_clip, HENRY_MCDONOUGH_CLIP_URL),
        ("Stockbridge", stock_clip, HENRY_STOCKBRIDGE_CLIP_URL),
        ("Locust Grove", locust_clip, HENRY_LOCUST_GROVE_CLIP_URL),
    ):
        missing = clip_misses(municipal_name, clip)
        if missing:
            print(f"    {municipal_name} clip miss {len(missing)}", flush=True)
            clip.update(fetch_attrs_in(url, "PARCEL_NO", missing, ["PARCEL_NO", "ZONING"]))

    stats = {
        "zoning": 0,
        "gmc": 0,
        "mcd_clip": 0,
        "stockbridge": 0,
        "locust": 0,
        "county": 0,
        "city_stub": 0,
        "hampton_stub": 0,
        "zoning_miss": 0,
        "city_blank": 0,
        "no_zoning_row": 0,
        "flu": 0,
        "flu_city": 0,
        "flu_miss": 0,
        "owner": 0,
        "outside": 0,
        "overlay": 0,
        "flippen": 0,
    }
    kept: list[dict] = []
    base_gap = (
        "No mailing address, tax value, or last sale on Henry County public REST. "
        "CAMA is qPublic HTML; the QPublic deep link is kept."
    )
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        if not (HENRY_LON_MIN <= lon <= HENRY_LON_MAX and HENRY_LAT_MIN <= lat <= HENRY_LAT_MAX):
            stats["outside"] += 1
            continue
        pid = props["parcelId"]
        flu_attrs = flu_by_id.get(pid) or {}
        municipal = henry_municipal(flu_attrs.get("MUNICIPAL"))
        muni_key = (municipal or "").lower()
        zoning_attrs = zoning_by_id.get(pid) or {}
        county_zoning = clean_code(zoning_attrs.get("ZONING"))
        city_zoning = clean_code(zoning_attrs.get("CityZoning"))
        overlay = clean_code(zoning_attrs.get("Spl_Zoning"))
        gmc_code = gmc_index.hit(lon, lat)
        in_mcd_clip = pid in mcd_clip
        in_mcdonough = muni_key == "mcdonough" or in_mcd_clip or (
            bool(gmc_code) and muni_key not in HENRY_OTHER_CITIES and muni_key != "henry county"
        )
        zoning_code = None
        zoning_source = None
        mcd_clip_code = clean_code((mcd_clip.get(pid) or {}).get("ZONING"))
        stock_code = clean_code((stock_clip.get(pid) or {}).get("ZONING"))
        locust_code = clean_code((locust_clip.get(pid) or {}).get("ZONING"))
        if in_mcdonough and gmc_code:
            zoning_code, zoning_source = gmc_code, "gmc"
        elif in_mcdonough and mcd_clip_code:
            zoning_code, zoning_source = mcd_clip_code, "mcd_clip"
        elif (muni_key == "stockbridge" or pid in stock_clip) and stock_code:
            zoning_code, zoning_source = stock_code, "stockbridge"
        elif (muni_key == "locust grove" or pid in locust_clip) and locust_code:
            zoning_code, zoning_source = locust_code, "locust"
        elif county_zoning and county_zoning.upper() != "CITY":
            zoning_code, zoning_source = county_zoning, "county"
        elif city_zoning:
            zoning_source = "hampton_stub" if muni_key == "hampton" else "city_stub"
            zoning_code = city_zoning
        if zoning_code:
            stats["zoning"] += 1
            stats[zoning_source or "zoning_miss"] += 1
            props["zoningCode"] = zoning_code
            # Keep the full code. Parser would treat RA-200 / RM-75 as a jurisdiction prefix.
            props["zoningDistrict"] = zoning_code
        else:
            props["zoningCode"] = None
            props["zoningDistrict"] = None
            if county_zoning and county_zoning.upper() == "CITY":
                stats["city_blank"] += 1
            elif pid not in zoning_by_id:
                stats["no_zoning_row"] += 1
            else:
                stats["zoning_miss"] += 1
        if overlay:
            stats["overlay"] += 1

        flu_code = clean_code(flu_attrs.get("FLU2023"))
        if flu_code and flu_code.upper() == "CITY":
            stats["flu_city"] += 1
            props["flu"] = None
        elif flu_code:
            stats["flu"] += 1
            props["flu"] = {
                "code": flu_code,
                "label": flu_code,
                "jurisdiction": municipal or "Henry County",
                "source": "henry-planning-flu2023",
            }
        else:
            stats["flu_miss"] += 1
            props["flu"] = None
        props["jurisdictionCode"] = municipal

        owner = None
        if in_mcdonough:
            owner = clean((owners.get(pid) or {}).get("OWNER_NAME"))
        props["ownerName"] = owner
        if owner:
            stats["owner"] += 1
        # County REST has none of these. Do not copy GMC acres or invent CAMA fields.
        props["lastSale"] = {"date": None, "price": None, "qualified": None}
        props["tax"] = {"marketValue": None, "assessedValue": None, "taxableValue": None, "taxes": None}
        props["mailingAddress"] = {"line1": None, "line2": None, "city": None, "state": None, "zip": None}
        if not props.get("appraiserUrl"):
            props["appraiserUrl"] = HENRY_QPUBLIC + urllib.parse.quote(pid, safe="")

        gaps = [base_gap]
        if owner:
            gaps.append(
                "Owner name is from McDonough GMC planning parcels only. Acreage stays county ACREAGE_1. "
                "That layer has no mailing address, tax value, or last sale."
            )
        else:
            gaps.append(
                "Owner name is not on countywide REST. McDonough GMC owner names are joined only inside that city."
            )
        if props["flu"] is None and muni_key in {"mcdonough", "stockbridge", "hampton", "locust grove"}:
            gaps.append(
                f"{municipal} future land use is not on REST (county FLU2023 is CITY or blank). "
                "City comprehensive-plan FLU was not invented."
            )
        elif props["flu"] is None:
            gaps.append("No county FLU2023 class joined for this parcel.")
        if zoning_source == "hampton_stub":
            gaps.append(
                "Hampton zoning is the county CityZoning stub. No Hampton city FeatureServer. "
                "Mustang, Oklahoma AGOL was rejected (wrong state)."
            )
        elif zoning_source == "city_stub":
            gaps.append("City zoning is the county CityZoning stub, not a city-owned zoning layer.")
        elif county_zoning and county_zoning.upper() == "CITY":
            gaps.append(
                "County zoning code is CITY but CityZoning is blank, and no city-clip district matched."
            )
        elif not zoning_code:
            gaps.append("No Current Zoning row matched this PARCEL_NO.")
        if overlay:
            gaps.append(f"County special zoning overlay: {overlay}.")
        if muni_key == "flippen":
            stats["flippen"] += 1
            gaps.append("Flippen is unincorporated and has no city zoning or FLU layer.")
        props["dataGaps"] = gaps
        props["source"] = spec["source"]
        kept.append(feature)

    features[:] = kept
    total = len(kept)
    spec["gaps"] = [
        (
            f"Henry 5–150 acre join: zoning {stats['zoning']}/{total} "
            f"(GMC McDonough {stats['gmc']}, McDonough clip {stats['mcd_clip']}, "
            f"Stockbridge clip {stats['stockbridge']}, Locust Grove clip {stats['locust']}, "
            f"county ZONING {stats['county']}, CityZoning stub {stats['city_stub']}, "
            f"Hampton CityZoning stub {stats['hampton_stub']}, "
            f"CITY with blank CityZoning {stats['city_blank']}, "
            f"no zoning row {stats['no_zoning_row']}, other unmatched {stats['zoning_miss']}). "
            f"FLU {stats['flu']}/{total}; FLU2023=CITY left blank on {stats['flu_city']}; "
            f"no FLU row {stats['flu_miss']}. McDonough owner names {stats['owner']}. "
            f"Special overlays noted {stats['overlay']}. "
            f"Centroids outside Henry extent dropped {stats['outside']}."
        ),
        *HENRY_GAPS,
    ]
    print(
        f"  Henry kept {total} zoning {stats['zoning']} flu {stats['flu']} "
        f"city-placeholder {stats['flu_city']} owners {stats['owner']}",
        flush=True,
    )


def county_override(fips: str) -> dict | None:
    if fips == "13151":  # Henry GA — Atlanta. Public GIS only; CAMA stays on qPublic.
        return {
            "kind": "arcgis",
            "url": HENRY_PARCELS_URL,
            "where": "ACREAGE_1>=5 AND ACREAGE_1<=150",
            "outFields": [
                "PARCEL_NO",
                "ACREAGE_1",
                "FULLADDRES",
                "POSTALCITY",
                "ZIP",
                "QPublic",
            ],
            "idField": "PARCEL_NO",
            "acresField": "ACREAGE_1",
            "situsField": "FULLADDRES",
            "cityField": "POSTALCITY",
            "zipField": "ZIP",
            "appraiserHtmlField": "QPublic",
            "enrich": "henry-ga",
            "source": "ga-henry-parcels",
            "coverage": "complete-gte-5ac",
            "gaps": list(HENRY_GAPS),
        }
    if fips == "13067":  # Cobb GA
        return {
            "kind": "arcgis",
            "url": "https://gis.cobbcounty.org/gisserver/rest/services/cobbpublic/Parcels/MapServer/3/query",
            "where": "ACRES>=5 AND ACRES<=150",
            "outFields": ["PIN", "ACRES", "SITUS_ADDR", "OWNER_NAM1", "OWNER_ADDR", "OWNER_CITY", "OWNER_STAT", "OWNER_ZIP"],
            "idField": "PIN",
            "acresField": "ACRES",
            "ownerField": "OWNER_NAM1",
            "situsField": "SITUS_ADDR",
            "mail1Field": "OWNER_ADDR",
            "mailCityField": "OWNER_CITY",
            "mailStateField": "OWNER_STAT",
            "mailZipField": "OWNER_ZIP",
            "source": "ga-cobb-parcels",
            "coverage": "complete-gte-5ac",
            "gaps": ["Cobb County open parcels. No zoning join on this layer."],
        }
    if fips == "13089":  # DeKalb GA
        return {
            "kind": "arcgis",
            "url": "https://dcgis.dekalbcountyga.gov/hosted/rest/services/Tax_Parcels/FeatureServer/0/query",
            "where": "Shape__Area>=20000 AND Shape__Area<=2000000",
            "outFields": ["PARCELID", "SITEADDRESS", "OWNERNME1", "ZONING", "CITY", "ZIP", "PSTLADDRESS", "PSTLCITY", "PSTLSTATE", "PSTLZIP5"],
            "idField": "PARCELID",
            "computeAcres": True,
            "ownerField": "OWNERNME1",
            "situsField": "SITEADDRESS",
            "cityField": "CITY",
            "zipField": "ZIP",
            "zoningField": "ZONING",
            "mail1Field": "PSTLADDRESS",
            "mailCityField": "PSTLCITY",
            "mailStateField": "PSTLSTATE",
            "mailZipField": "PSTLZIP5",
            "source": "ga-dekalb-tax-parcels",
            "coverage": "sample",
            "gaps": [
                "DeKalb's public layer has no deed-acre field. Acres are computed from the polygon inside a Shape__Area window, so this county is a large sample, not a certified complete roll.",
            ],
        }
    if fips == "45035":  # Dorchester SC
        return {
            "kind": "arcgis",
            "url": "https://gisportal.dorchestercounty.net/hosting/rest/services/General_Data/Parcels_Public/MapServer/0/query",
            "where": "GIS_ACREAGE>=5 AND GIS_ACREAGE<=150",
            "outFields": ["TMS", "OWNER", "GIS_ACREAGE", "TAXED_ACRES", "MAILING_ADDRESS", "CITY_STATE_ZIP"],
            "idField": "TMS",
            "acresField": "GIS_ACREAGE",
            "ownerField": "OWNER",
            "mail1Field": "MAILING_ADDRESS",
            "source": "sc-dorchester-parcels-public",
            "coverage": "complete-gte-5ac",
            "gaps": ["Dorchester public parcels. Situs is not on this layer. No zoning join."],
        }
    if fips == "01073":  # Jefferson AL
        return {
            "kind": "arcgis",
            "url": "https://jccgis.jccal.org/server/rest/services/Basemap/Parcels/MapServer/0/query",
            "where": "GIS_ACRES>=5 AND GIS_ACRES<=150",
            "outFields": ["PID", "Unique_ID", "ParcelNo", "PARCELID", "OWNERNAME", "GIS_ACRES", "ADDR_APR", "Property_City", "CITY", "ZIP"],
            "idField": "PID",
            "idFallbacks": ["ParcelNo", "PARCELID", "Unique_ID"],
            "acresField": "GIS_ACRES",
            "ownerField": "OWNERNAME",
            "situsField": "ADDR_APR",
            "cityField": "Property_City",
            "zipField": "ZIP",
            "source": "al-jefferson-parcels",
            "coverage": "complete-gte-5ac",
            "gaps": ["Jefferson County public parcels. Owner and situs are sparse on this layer. No zoning join."],
        }
    if fips == "45045":  # Greenville SC
        return {
            "kind": "arcgis",
            "url": "https://citygis.greenvillesc.gov/arcgis/rest/services/GeneralData/GeneralData_WGS84/MapServer/2/query",
            "where": "GIS_ACRES>=5 AND GIS_ACRES<=150",
            "outFields": ["PIN", "GIS_ACRES", "NAMECO", "POWNNM", "STREET", "CITY", "ZIP5"],
            "idField": "PIN",
            "acresField": "GIS_ACRES",
            "ownerField": "NAMECO",
            "situsField": "STREET",
            "cityField": "CITY",
            "zipField": "ZIP5",
            "source": "sc-greenville-city-gis",
            "coverage": "sample",
            "gaps": [
                "Published by City of Greenville GIS. The 5–150 acre count on this layer is too small to treat as all of Greenville County. Sample, not a countywide roll.",
            ],
        }
    return None


def gap_reason(county: dict) -> str:
    state = county["state"]
    if state == "Georgia":
        return "No public statewide Georgia parcel polygon service. This county is not in the Cobb, DeKalb, or Henry pull."
    if state == "South Carolina":
        return "Statewide South Carolina open data is parcel centroids (Revenue and Fiscal Affairs), not polygons. This county's polygon service was missing or token-gated (Charleston County GIS requires a token)."
    if state == "Alabama":
        return "Alabama has no unified statewide parcel service. This county was not on a verified open polygon endpoint in this pull."
    if state == "Tennessee":
        return "Tennessee IMPACT did not publish this county, and no substitute county endpoint was wired."
    return "No open parcel polygon endpoint was confirmed for this county."


def spec_for(county: dict) -> dict:
    fips = county["fips"]
    if fips in ORLANDO_REUSE:
        return {"kind": "reuse-orlando"}
    override = county_override(fips)
    if override:
        return override
    state = county["state"]
    if state == "Florida" and fips in FL_DOH_LAYER:
        return fl_spec(fips)
    if state == "North Carolina":
        return nc_spec(fips)
    if state == "Tennessee":
        return tn_spec(fips)
    if state == "Mississippi":
        return ms_spec(fips)
    if state == "Arkansas":
        return ar_spec(fips)
    return {"kind": "gap", "reason": gap_reason(county), "source": "unavailable", "queryUrl": None, "gaps": [gap_reason(county)]}


def tile_key(lon: float, lat: float) -> tuple[int, int]:
    return math.floor((lon - ORIGIN_LON) / TILE_DEG), math.floor((lat - ORIGIN_LAT) / TILE_DEG)


def write_tiles(county: dict, features: list[dict]) -> tuple[str, str, int]:
    fips = county["fips"]
    folder = COUNTY_DIR / fips / "tiles"
    if folder.exists():
        for child in folder.glob("*.geojson"):
            child.unlink()
    folder.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[int, int], list[dict]] = defaultdict(list)
    lookup: dict[str, str] = {}
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        key = tile_key(lon, lat)
        grouped[key].append(feature)
        lookup[feature["properties"]["parcelId"]] = f"{key[0]}_{key[1]}"
    for (ix, iy), group in grouped.items():
        path = folder / f"{ix}_{iy}.geojson"
        path.write_text(
            json.dumps(
                {"type": "FeatureCollection", "name": f"{fips}-{ix}_{iy}", "features": group},
                separators=(",", ":"),
            )
        )
    lookup_path = COUNTY_DIR / fips / "lookup.json"
    lookup_path.write_text(json.dumps(lookup, separators=(",", ":")))
    return str(folder.relative_to(ROOT)), str(lookup_path.relative_to(ROOT)), len(grouped)


def county_row(
    county: dict,
    markets: list[str],
    *,
    feature_count: int,
    coverage: str,
    partition: str,
    path: str | None,
    lookup: str | None,
    source: str,
    query_url: str | None,
    gaps: list[str],
    source_count: int | None = None,
    dropped: int | None = None,
    tile_count: int | None = None,
) -> dict:
    row = {
        "name": county["name"],
        "fips": county["fips"],
        "state": county["state"],
        "markets": markets,
        "featureCount": feature_count,
        "coverage": coverage,
        "partition": partition,
        "minAcres": MIN_ACRES,
        "maxAcres": MAX_ACRES,
        "source": source,
        "queryUrl": query_url,
        "gaps": gaps,
        "path": path,
        "lookup": lookup,
        "sourceCount": source_count,
        "dropped": dropped,
        "tileCount": tile_count,
    }
    (COUNTY_DIR / county["fips"]).mkdir(parents=True, exist_ok=True)
    (COUNTY_DIR / county["fips"] / "county.json").write_text(json.dumps(row, indent=2) + "\n")
    return row


def load_county_rows() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not COUNTY_DIR.exists():
        return rows
    for path in COUNTY_DIR.glob("*/county.json"):
        rows[path.parent.name] = json.loads(path.read_text())
    return rows


def orlando_county(fips: str) -> dict | None:
    meta_path = ORLANDO_DIR / "meta.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text())
    for county in meta.get("counties") or []:
        if county.get("fips") == fips and county.get("coverage") == "complete-gte-5ac":
            return county
    return None


def rebuild_indexes(catalog: dict) -> None:
    rows = load_county_rows()
    MARKET_DIR.mkdir(parents=True, exist_ok=True)
    index_markets: dict[str, dict] = {}
    coverage_lines = [
        "# Market parcel coverage",
        "",
        "Acreage band is **5.0–150.0 inclusive**. Orlando is not re-scraped. Complete Orlando counties that also sit in another shed (Orange, Osceola, Polk) are reused in place.",
        "",
        "Parcels stay off until neighborhood zoom, an area lock, or Show parcels. The map requests the selected market's viewport tiles only.",
        "",
        "| Market | Tier | Parcels | Complete counties | Sample counties | Gaps |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    detail_lines = ["", "## Counties", ""]
    for market in catalog["markets"]:
        market_rows = []
        for county in market["counties"]:
            row = rows.get(county["fips"])
            if not row:
                continue
            market_rows.append(row)
        parcel_count = sum(int(row.get("featureCount") or 0) for row in market_rows)
        complete = [row for row in market_rows if row.get("coverage") == "complete-gte-5ac" and row.get("featureCount")]
        sample = [row for row in market_rows if row.get("coverage") == "sample" and row.get("featureCount")]
        gaps = [row for row in market_rows if not row.get("featureCount")]
        meta = {
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "market": market["id"],
            "tier": market["tier"],
            "parcelCount": parcel_count,
            "coreMinAcres": MIN_ACRES,
            "coreMaxAcres": MAX_ACRES,
            "tile": {"originLon": ORIGIN_LON, "originLat": ORIGIN_LAT, "tileDeg": TILE_DEG},
            "notes": [
                "Loaded only when this market is selected.",
                "Viewport tiles use the same 0.25° grid as Orlando (origin lon -83, lat 27).",
                "Orange, Osceola, and Polk point at the existing Orlando complete extract.",
            ],
            "counties": [
                {
                    "name": row["name"],
                    "fips": row["fips"],
                    "state": row["state"],
                    "featureCount": row.get("featureCount") or 0,
                    "coverage": row.get("coverage"),
                    "partition": row.get("partition"),
                    "minAcres": MIN_ACRES,
                    "maxAcres": MAX_ACRES,
                    "source": row.get("source"),
                    "queryUrl": row.get("queryUrl"),
                    "gaps": row.get("gaps") or [],
                    "path": row.get("path"),
                    "lookup": row.get("lookup"),
                    "tileCount": row.get("tileCount"),
                    "sourceCount": row.get("sourceCount"),
                }
                for row in sorted(market_rows, key=lambda item: item["name"])
            ],
        }
        rel = f"data/fixtures/market-parcels/markets/{slug(market['id'])}/meta.json"
        market_path = ROOT / rel
        market_path.parent.mkdir(parents=True, exist_ok=True)
        market_path.write_text(json.dumps(meta, indent=2) + "\n")
        index_markets[market["id"]] = {
            "tier": market["tier"],
            "parcelCount": parcel_count,
            "completeCountyCount": len(complete),
            "sampleCountyCount": len(sample),
            "gapCountyCount": len(gaps),
            "path": rel,
            "counties": [
                {
                    "name": row["name"],
                    "state": row["state"],
                    "fips": row["fips"],
                    "featureCount": row.get("featureCount") or 0,
                    "coverage": row.get("coverage"),
                    "minAcres": MIN_ACRES,
                    "maxAcres": MAX_ACRES,
                    "gaps": (row.get("gaps") or [])[:2],
                }
                for row in meta["counties"]
            ],
        }
        coverage_lines.append(
            f"| {market['id']} | {market['tier']} | {parcel_count:,} | {len(complete)} | {len(sample)} | {len(gaps)} |"
        )
        detail_lines.append(f"### {market['id']}")
        detail_lines.append("")
        detail_lines.append("| County | State | FIPS | Coverage | Parcels | Source |")
        detail_lines.append("| --- | --- | --- | --- | ---: | --- |")
        for row in meta["counties"]:
            detail_lines.append(
                f"| {row['name']} | {row['state']} | {row['fips']} | {row['coverage']} | {row['featureCount']:,} | {row['source']} |"
            )
        detail_lines.append("")
    index = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "coreMinAcres": MIN_ACRES,
        "coreMaxAcres": MAX_ACRES,
        "tile": {"originLon": ORIGIN_LON, "originLat": ORIGIN_LAT, "tileDeg": TILE_DEG},
        "orlando": "unchanged — see data/fixtures/orlando-parcels",
        "markets": index_markets,
    }
    (OUT_DIR / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    coverage = "\n".join(coverage_lines + detail_lines) + "\n"
    (OUT_DIR / "coverage.md").write_text(coverage)
    docs = ROOT / "docs" / "market-parcels.md"
    docs.write_text(INTRO_DOC + "\n" + coverage)


INTRO_DOC = """# Market parcels (every MSA except Orlando)

Orlando keeps `scripts/seed_orlando_parcels.py` and `data/fixtures/orlando-parcels`. This pull does not rewrite those tiles.

Other markets use the same 0.25° tile grid (origin longitude -83, latitude 27) under `data/fixtures/market-parcels/counties/{fips}/tiles`. The home page does not embed the polygons. `GET /api/parcels?market={Market}&bbox=w,s,e,n` reads only the tiles for **that market** that intersect the viewport. Outlines stay off until neighborhood zoom (about 10.5), an area is locked, or Show parcels is on — the same gate as Orlando.

Orange, Osceola, and Polk already have a complete 5.0–150.0 acre Orlando extract. Tampa and Melbourne point at those tiles instead of downloading them again.

## Refresh

```bash
npm run seed:parcels:markets
python3 scripts/seed_market_parcels.py --market Charlotte
python3 scripts/seed_market_parcels.py --market Tampa --county Hardee
python3 scripts/seed_market_parcels.py --refresh
```

A finished county is skipped unless `--refresh` is passed. Cached normalized features, when present, live under `/tmp/dls-market-parcels`.

## Sources

| State | Endpoint | What shipped |
| --- | --- | --- |
| Florida | Florida DOH EHWATER Parcels | Complete 5–150 acre extract where the county is not already an Orlando complete county |
| North Carolina | NC OneMap `NC1Map_Parcels` polygons | Complete 5–150 acre extract. Most counties use `gisacres`. Cleveland, Columbus, Orange, and Warren store polygon acres because `gisacres` is 0 |
| Tennessee | Comptroller IMPACT Parcels | Complete where `CALC_ACRE` returns rows. Several large counties are absent from that layer and stay gaps |
| Mississippi | MDEQ statewide parcels (2023) | Complete 5–150 acre extract on `GISACRES` |
| Arkansas | Arkansas GIS cadastre polygons | Complete band using polygon-derived acres |
| Georgia | Cobb, DeKalb, and Henry county services | Cobb complete. Henry complete on county `ACREAGE_1` with zoning and FLU joins; owner, mailing, tax, and sale stay on qPublic. DeKalb is a polygon-acre sample. Other Georgia counties are gaps |
| South Carolina | Dorchester public parcels; Greenville city GIS | Dorchester complete. Greenville is a city-hosted sample. Charleston County's GIS requires a token. Other counties are gaps |
| Alabama | Jefferson County parcels | Jefferson is a complete 5–150 acre extract. Other Alabama counties are gaps |

Zoning is joined when the county parcel layer already carries a zoning field (DeKalb) or a separate public zoning layer is wired (Henry). It is not a multifamily knowledge-base match outside Orange County. Prefer **All parcels** in these markets.

Henry County (13151, Atlanta) uses `Parcels/MapServer/12` for the 5.0–150.0 acre band (`ACREAGE_1` and situs). Zoning joins from `Current_Zoning_and_Future_Land_Use/MapServer/0` on `PARCEL_NO` (`ZONING`, and `CityZoning` when the county code is `CITY`). McDonough prefers GMC zoning district polygons, then the county McDonough parcel clip. Stockbridge and Locust Grove use the county city-clip `ZONING` attribute. Hampton has no city GIS REST, so zoning stays the county `CityZoning` stub. Flippen is unincorporated. A Mustang, Oklahoma AGOL layer is not used. Future land use is `Planning/Future_Land_Use/FeatureServer/0` `FLU2023`. Code `CITY` is left blank because city comprehensive-plan FLU is not on REST. The parcel-layer `ZONING` and `FUTURE_LAN` fields are often null and are not the join. Owner, mailing, tax, and last sale are not on county REST. Each parcel keeps the qPublic deep link (`AppID=1035`, `KeyValue` = parcel id). McDonough GMC planning parcels supply `ownerName` inside that city only.

## Coverage
"""


def download_county(county: dict, markets: list[str], spec: dict) -> dict:
    fips = county["fips"]
    cache_path = CACHE_DIR / f"{fips}.json"
    print(f"Pulling {county['name']} {county['state']} ({fips}) via {spec['source']}", flush=True)
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = json.loads(cache_path.read_text())
        if cached.get("features"):
            print(f"  cache hit {len(cached['features'])}", flush=True)
            features = cached["features"]
            for feature in features:
                feature["properties"]["marketIds"] = markets
            path, lookup, tiles = write_tiles(county, features)
            return county_row(
                county,
                markets,
                feature_count=len(features),
                coverage=spec["coverage"] if len(features) else "gap",
                partition="tiles" if features else "none",
                path=path if features else None,
                lookup=lookup if features else None,
                source=spec["source"],
                query_url=spec["url"],
                gaps=list(cached.get("gaps") or spec.get("gaps") or []),
                source_count=cached.get("sourceCount"),
                dropped=cached.get("dropped"),
                tile_count=tiles,
            )
    try:
        expected = count_where(spec["url"], spec["where"])
    except Exception as exc:  # noqa: BLE001
        reason = f"Query failed: {exc}"
        print(f"  gap {reason}", flush=True)
        return county_row(
            county,
            markets,
            feature_count=0,
            coverage="gap",
            partition="none",
            path=None,
            lookup=None,
            source=spec["source"],
            query_url=spec["url"],
            gaps=[reason, *(spec.get("gaps") or [])],
        )
    if expected <= 0 and spec.get("fallbackWhere"):
        total = count_where(spec["url"], spec["fallbackWhere"])
        if total > 0:
            print(f"  acre field empty; computing acres for {total} county parcels", flush=True)
            spec = dict(spec)
            spec["where"] = spec["fallbackWhere"]
            spec["computeAcres"] = True
            spec["acresField"] = None
            note = spec.get("fallbackNote")
            gaps = list(spec.get("gaps") or [])
            if note:
                gaps.insert(0, note)
            spec["gaps"] = gaps
            expected = total
    if expected <= 0:
        reason = spec.get("emptyGap") or "Source returned zero parcels in the requested filter."
        print(f"  gap {reason}", flush=True)
        return county_row(
            county,
            markets,
            feature_count=0,
            coverage="gap",
            partition="none",
            path=None,
            lookup=None,
            source=spec["source"],
            query_url=spec["url"],
            gaps=[reason, *(spec.get("gaps") or [])],
            source_count=0,
        )
    print(f"  source rows {expected}", flush=True)
    ids = fetch_object_ids(spec["url"], spec["where"])
    raw = fetch_by_ids(spec["url"], ids, spec["outFields"])
    features, dropped = normalize_rows(raw, county, markets, spec)
    if spec.get("enrich") == "henry-ga":
        before = len(features)
        enrich_henry_features(features, spec)
        dropped += before - len(features)
    if not all(in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{fips} emitted a parcel outside 5–150 acres")
    coverage = spec["coverage"]
    gaps = list(spec.get("gaps") or [])
    if expected and len(features) < expected and not spec.get("computeAcres"):
        if dropped:
            collapse = (
                f"{expected} source rows collapsed to {len(features)} parcel ids "
                "(duplicate ids, stacked units, or rings that failed the WGS84 check). "
                "The acreage query covered the county."
            )
        else:
            collapse = (
                f"{expected} source rows collapsed to {len(features)} parcel ids because the parcel id repeats. "
                "None failed the acreage band or the WGS84 centroid check. The acreage query covered the county."
            )
        gaps.insert(0, collapse)
    if not features:
        coverage = "gap"
        gaps.insert(0, f"Source count was {expected} but none survived the 5–150 acre and WGS84 checks.")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "sourceCount": expected,
                "dropped": dropped,
                "gaps": gaps,
                "features": features,
            },
            separators=(",", ":"),
        )
    )
    path, lookup, tiles = (None, None, 0)
    if features:
        path, lookup, tiles = write_tiles(county, features)
    print(f"  kept {len(features)} ({coverage})", flush=True)
    return county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=coverage,
        partition="tiles" if features else "none",
        path=path,
        lookup=lookup,
        source=spec["source"],
        query_url=spec["url"],
        gaps=gaps,
        source_count=expected,
        dropped=dropped,
        tile_count=tiles,
    )


def write_reuse(county: dict, markets: list[str]) -> None:
    existing = orlando_county(county["fips"])
    if not existing:
        county_row(
            county,
            markets,
            feature_count=0,
            coverage="gap",
            partition="none",
            path=None,
            lookup=None,
            source="orlando-reuse-missing",
            query_url=None,
            gaps=["Expected an Orlando complete extract to reuse, but meta.json did not list it."],
        )
        return
    county_row(
        county,
        markets,
        feature_count=int(existing.get("featureCount") or 0),
        coverage="complete-gte-5ac",
        partition=existing.get("partition") or "tiles",
        path=existing.get("path"),
        lookup=f"data/fixtures/orlando-parcels/lookup/{county['fips']}.json",
        source="reused-orlando-complete-5-150",
        query_url=existing.get("queryUrl"),
        gaps=["Reused the Orlando complete 5.0–150.0 acre tiles. Not re-scraped."],
        source_count=existing.get("sourceCount"),
        tile_count=existing.get("tileCount"),
    )


def write_gap(county: dict, markets: list[str], spec: dict) -> None:
    county_row(
        county,
        markets,
        feature_count=0,
        coverage="gap",
        partition="none",
        path=None,
        lookup=None,
        source=spec.get("source") or "unavailable",
        query_url=spec.get("queryUrl"),
        gaps=spec.get("gaps") or [spec.get("reason") or "No source"],
    )


def priority_of(markets: list[str], catalog: dict) -> tuple[int, str]:
    tiers = {market["id"]: 0 if market["tier"] == "primary" else 1 for market in catalog["markets"]}
    order = {market["id"]: index for index, market in enumerate(catalog["markets"])}
    best = min(markets, key=lambda name: (tiers.get(name, 9), order.get(name, 99)))
    return tiers.get(best, 9), best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", action="append", default=[])
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--tier", choices=["primary", "other", "all"], default="all")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text())
    selected = set(args.market)
    county_filter = {name.lower() for name in args.county}
    grouped: dict[str, dict] = {}
    for market in catalog["markets"]:
        if args.tier != "all" and market["tier"] != args.tier:
            continue
        if selected and market["id"] not in selected:
            continue
        for county in market["counties"]:
            if county_filter and county["name"].lower() not in county_filter:
                continue
            slot = grouped.setdefault(county["fips"], {"county": county, "markets": []})
            if market["id"] not in slot["markets"]:
                slot["markets"].append(market["id"])

    # When a filter is set, still let county.json keep markets from the full catalog.
    full_markets: dict[str, list[str]] = defaultdict(list)
    for market in catalog["markets"]:
        for county in market["counties"]:
            if market["id"] not in full_markets[county["fips"]]:
                full_markets[county["fips"]].append(market["id"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    for fips, slot in grouped.items():
        markets = full_markets[fips]
        spec = spec_for(slot["county"])
        existing = COUNTY_DIR / fips / "county.json"
        if spec["kind"] == "gap":
            if not existing.exists() or args.refresh:
                write_gap(slot["county"], markets, spec)
            continue
        if spec["kind"] == "reuse-orlando":
            if not existing.exists() or args.refresh:
                write_reuse(slot["county"], markets)
            continue
        if existing.exists() and not args.refresh:
            row = json.loads(existing.read_text())
            if row.get("featureCount") and row.get("coverage") in {"complete-gte-5ac", "sample"}:
                row["markets"] = markets
                (COUNTY_DIR / fips / "county.json").write_text(json.dumps(row, indent=2) + "\n")
                continue
        jobs.append((priority_of(markets, catalog), slot["county"]["name"], slot["county"], markets, spec))

    jobs.sort()
    with WRITE_LOCK:
        rebuild_indexes(catalog)
    print(f"{len(jobs)} counties to pull, {len(grouped)} selected", flush=True)

    def run(job: tuple) -> None:
        _priority, _name, county, markets, spec = job
        try:
            download_county(county, markets, spec)
        except Exception as exc:  # noqa: BLE001
            print(f"  failed {county['name']} {county['fips']}: {exc}", flush=True)
            county_row(
                county,
                markets,
                feature_count=0,
                coverage="gap",
                partition="none",
                path=None,
                lookup=None,
                source=spec.get("source") or "error",
                query_url=spec.get("url"),
                gaps=[f"Download failed: {exc}", *(spec.get("gaps") or [])],
            )
        with WRITE_LOCK:
            rebuild_indexes(catalog)

    if jobs:
        workers = max(1, min(args.workers, len(jobs)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run, job) for job in jobs]
            for future in as_completed(futures):
                future.result()
    with WRITE_LOCK:
        rebuild_indexes(catalog)
    index = json.loads((OUT_DIR / "index.json").read_text())
    print("Done.", flush=True)
    for name, summary in index["markets"].items():
        print(
            f"  {name}: {summary['parcelCount']} parcels, "
            f"{summary['completeCountyCount']} complete, {summary['sampleCountyCount']} sample, "
            f"{summary['gapCountyCount']} gaps",
            flush=True,
        )


if __name__ == "__main__":
    main()
