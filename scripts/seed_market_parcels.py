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
import datetime
import json
import math
import threading
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from parcel_geometry import esri_rings_to_geojson, net_acres, representative_point
from pender_overlays import enrich_pender_features

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
    return esri_rings_to_geojson(geom["rings"]), net_acres(geom["rings"])


def centroid_of(geometry: dict) -> tuple[float, float] | None:
    return representative_point(geometry)


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


def epoch_to_iso(value: Any) -> str | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    seconds = parsed / 1000 if parsed > 10_000_000_000 else parsed
    if seconds < 0 or seconds > 4_102_444_800:
        return None
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).strftime("%Y-%m-%d")


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
        if spec.get("saleEpochField"):
            sold_on = epoch_to_iso(attrs.get(spec["saleEpochField"]))
        elif spec.get("saleYearField"):
            sold_on = sale_date(attrs.get("SALE_YR1"), attrs.get("SALE_MO1"))
        else:
            sold_on = None
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
            sale_date=sold_on,
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


def county_override(fips: str) -> dict | None:
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
    if fips == "37141":  # Pender NC — county Energov, not OneMap
        return {
            "kind": "arcgis",
            "url": "https://gis.pendercountync.gov/arcgis/rest/services/Energov/MapServer/1/query",
            "where": "ACRES>=5 AND ACRES<=150",
            "outFields": [
                "PIN",
                "NAME",
                "ADDR",
                "CITY",
                "STATE",
                "ZIP",
                "PROPERTY_ADDRESS",
                "ACRES",
                "SALE_PRICE",
                "DATE",
                "TOTAL_VALUE",
                "LAND_VALUE",
            ],
            "idField": "PIN",
            "acresField": "ACRES",
            "ownerField": "NAME",
            "situsField": "PROPERTY_ADDRESS",
            "salePriceField": "SALE_PRICE",
            "saleEpochField": "DATE",
            "marketValueField": "TOTAL_VALUE",
            "mail1Field": "ADDR",
            "mailCityField": "CITY",
            "mailStateField": "STATE",
            "mailZipField": "ZIP",
            "source": "nc-pender-energov-37141",
            "coverage": "complete-gte-5ac",
            "enrich": enrich_pender_features,
            "gaps": [
                "Imagine Pender 2050 (LayersPro/35) is joined by centroid. Municipal/ETJ is the county plan's placeholder inside towns, not a separate municipal future-land-use layer.",
                "Zoning and future-land-use codes are not in the Orange County multifamily knowledge base, so the land-use filter treats them as unknown rather than inventing entitlements.",
                "NC OneMap NC1Map_Parcels cntyfips='141' is the statewide parcel filter for Pender. This extract uses county Energov MapServer/1 (ACRES 5–150) instead of OneMap gisacres.",
                "Energov ACRES is the tax-roll acre field used for the 5.0–150.0 band. CALCACRES is GIS acreage and was not the filter.",
            ],
        }
    return None


def gap_reason(county: dict) -> str:
    state = county["state"]
    if state == "Georgia":
        return "No public statewide Georgia parcel polygon service. This county is not in the Cobb/DeKalb pull."
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
    extra: dict | None = None,
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
    for key, value in (extra or {}).items():
        if key not in row:
            row[key] = value
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
| North Carolina | NC OneMap `NC1Map_Parcels` polygons | Complete 5–150 acre extract. Most counties use `gisacres`. Cleveland, Columbus, Orange, and Warren store polygon acres because `gisacres` is 0. Pender (37141) uses county Energov parcels (`cntyfips='141'` is the OneMap filter, not this extract) |
| Tennessee | Comptroller IMPACT Parcels | Complete where `CALC_ACRE` returns rows. Several large counties are absent from that layer and stay gaps |
| Mississippi | MDEQ statewide parcels (2023) | Complete 5–150 acre extract on `GISACRES` |
| Arkansas | Arkansas GIS cadastre polygons | Complete band using polygon-derived acres |
| Georgia | Cobb and DeKalb county services only | Cobb complete. DeKalb is a polygon-acre sample. Other Georgia counties are gaps |
| South Carolina | Dorchester public parcels; Greenville city GIS | Dorchester complete. Greenville is a city-hosted sample. Charleston County's GIS requires a token. Other counties are gaps |
| Alabama | Jefferson County parcels | Jefferson is a complete 5–150 acre extract. Other Alabama counties are gaps |

Zoning is joined when the county layer already carries a zoning field (DeKalb) or a public zoning polygon is wired (Pender: LayersPro UDO/36 and Burgaw, St. Helena, Surf City, Topsail Beach, and Watha). Atkinson has no zoning layer. It is not a multifamily knowledge-base match outside Orange County. Eligible nomination tracts are not designated QOZs. Prefer **All parcels** in these markets.

## Coverage
"""


def download_county(county: dict, markets: list[str], spec: dict) -> dict:
    fips = county["fips"]
    cache_path = CACHE_DIR / f"{fips}.json"
    print(f"Pulling {county['name']} {county['state']} ({fips}) via {spec['source']}", flush=True)
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = json.loads(cache_path.read_text())
        if cached.get("features") and cached.get("source") == spec["source"]:
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
                extra=cached.get("extra") if isinstance(cached.get("extra"), dict) else None,
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
    if not all(in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{fips} emitted a parcel outside 5–150 acres")
    extra: dict = {}
    enrich_gaps: list[str] = []
    enrich = spec.get("enrich")
    if enrich and features:
        enrich_gaps, extra = enrich(features)
    coverage = spec["coverage"]
    gaps = [*enrich_gaps, *(spec.get("gaps") or [])]
    if expected and len(features) < expected and not spec.get("computeAcres"):
        gaps.append(
            f"{expected} source rows collapsed to {len(features)} parcel ids (duplicate ids, stacked units, or rings that failed the WGS84 check). The acreage query covered the county.",
        )
    if not features:
        coverage = "gap"
        gaps.insert(0, f"Source count was {expected} but none survived the 5–150 acre and WGS84 checks.")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "source": spec["source"],
                "sourceCount": expected,
                "dropped": dropped,
                "gaps": gaps,
                "extra": extra,
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
        extra=extra,
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
