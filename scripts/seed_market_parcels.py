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
    owner2: str | None = None,
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
            "ownerName2": owner2,
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


def fetch_by_ids(
    url: str,
    ids: list[int],
    out_fields: list[str],
    batch: int = 120,
    return_geometry: bool = True,
) -> list[dict]:
    features: list[dict] = []
    total = len(ids)
    params = {
        "outFields": ",".join(out_fields),
        "returnGeometry": "true" if return_geometry else "false",
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
                features.extend(
                    fetch_by_ids(
                        url,
                        chunk,
                        out_fields,
                        batch=max(20, len(chunk) // 2),
                        return_geometry=return_geometry,
                    )
                )
                continue
            raise
        if data.get("error"):
            if len(chunk) > 30:
                features.extend(
                    fetch_by_ids(
                        url,
                        chunk,
                        out_fields,
                        batch=max(20, len(chunk) // 2),
                        return_geometry=return_geometry,
                    )
                )
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
        sold = None
        qualified = None
        if spec.get("saleYearField"):
            sold = sale_date(attrs.get("SALE_YR1"), attrs.get("SALE_MO1"))
            qualified = clean(attrs.get("QUAL_CD1"))
        elif spec.get("saleDateField"):
            sold = parse_any_sale_date(attrs.get(spec["saleDateField"]))
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
            owner2=clean(attrs.get(spec["owner2Field"])) if spec.get("owner2Field") else None,
            situs=clean(attrs.get(spec["situsField"])) if spec.get("situsField") else None,
            city=clean(attrs.get(spec["cityField"])) if spec.get("cityField") else None,
            zip_code=zip_str(attrs.get(spec["zipField"])) if spec.get("zipField") else None,
            zoning=clean(attrs.get(spec["zoningField"])) if spec.get("zoningField") else None,
            dor=clean(attrs.get(spec["dorField"])) if spec.get("dorField") else None,
            sale_price=price,
            sale_date=sold,
            sale_qualified=qualified,
            market_value=num(attrs.get(spec["marketValueField"])) if spec.get("marketValueField") else None,
            assessed=num(attrs.get(spec["assessedField"])) if spec.get("assessedField") else None,
            taxable=num(attrs.get(spec["taxableField"])) if spec.get("taxableField") else None,
            mail1=clean(attrs.get(spec["mail1Field"])) if spec.get("mail1Field") else None,
            mail2=clean(attrs.get(spec["mail2Field"])) if spec.get("mail2Field") else None,
            mail_city=clean(attrs.get(spec["mailCityField"])) if spec.get("mailCityField") else None,
            mail_state=clean(attrs.get(spec["mailStateField"])) if spec.get("mailStateField") else None,
            mail_zip=zip_str(attrs.get(spec["mailZipField"])) if spec.get("mailZipField") else None,
        )
        if spec.get("taxPinField"):
            feature["properties"]["_taxPin"] = clean(attrs.get(spec["taxPinField"]))
        if spec.get("zoningDescriptionField"):
            feature["properties"]["_zoningDesc"] = clean(attrs.get(spec["zoningDescriptionField"]))
        if spec.get("districtField"):
            feature["properties"]["_district"] = clean(attrs.get(spec["districtField"]))
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


def pin_key(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    return " ".join(text.upper().split())


def nospace_key(value: Any) -> str | None:
    text = pin_key(value)
    if not text:
        return None
    return text.replace(" ", "")


def parse_mdy(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    parts = text.split("/")
    if len(parts) != 3:
        return None
    try:
        month, day, year = (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None
    if year < 100:
        year += 2000 if year < 70 else 1900
    if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_any_sale_date(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    if "/" in text:
        return parse_mdy(text)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) != 8:
        return None
    year, month, day = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
    if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def market_sale_price(value: Any) -> float | None:
    """Land Value Table stores 0 and 1 for non-market instruments. There is no qualified flag."""
    price = num(value)
    if price is None or price <= 1:
        return None
    return price


def flu_info(code: Any, label: Any, jurisdiction: str, source: str) -> dict | None:
    text = clean(code)
    if not text:
        return None
    return {
        "code": text,
        "label": clean(label) or text,
        "jurisdiction": jurisdiction,
        "source": source,
    }


def page_features(
    url: str,
    where: str,
    fields: list[str],
    *,
    geometry: bool,
    page: int,
) -> list[dict] | None:
    """Page with resultOffset. None means the server repeated a page and offset is unsafe."""
    rows: list[dict] = []
    offset = 0
    seen: set[int] = set()
    label = url.split("/services/")[-1][:72]
    while offset < 400000:
        data = fetch_json(
            url,
            {
                "where": where,
                "outFields": ",".join(fields),
                "returnGeometry": "true" if geometry else "false",
                "outSR": "4326",
                "resultOffset": str(offset),
                "resultRecordCount": str(page),
                "f": "json",
            },
            timeout=120,
        )
        if data.get("error"):
            if page > 80:
                page = max(80, page // 2)
                continue
            raise RuntimeError(json.dumps(data["error"])[:300])
        feats = data.get("features") or []
        fresh = 0
        for feature in feats:
            attrs = feature.get("attributes") or {}
            oid = attrs.get("OBJECTID", attrs.get("OBJECTID1", attrs.get("OBJECTID_1", attrs.get("objectid"))))
            if isinstance(oid, int):
                if oid in seen:
                    print(f"    offset ignored for {label}", flush=True)
                    return None
                seen.add(oid)
            fresh += 1
        rows.extend(feats)
        print(f"    {len(rows)} {label}", flush=True)
        if not feats or (len(feats) < page and not data.get("exceededTransferLimit")):
            return rows
        offset += len(feats)
    return rows


def load_layer(
    url: str,
    where: str,
    fields: list[str],
    *,
    geometry: bool,
    batch: int = 120,
) -> list[dict]:
    paged = page_features(url, where, fields, geometry=geometry, page=400 if geometry else 2000)
    if paged is not None:
        return paged
    ids = fetch_object_ids(url, where)
    print(f"    {len(ids)} rows {url.split('/services/')[-1][:72]}", flush=True)
    if not ids:
        return []
    return fetch_by_ids(url, ids, fields, batch=min(batch, 80), return_geometry=geometry)


def query_attributes_in(url: str, field: str, values: list[str], out_fields: list[str], batch: int = 60) -> list[dict]:
    rows: list[dict] = []
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    for start in range(0, len(unique), batch):
        chunk = unique[start : start + batch]
        quoted = ",".join("'" + value.replace("'", "''") + "'" for value in chunk)
        data = fetch_json(
            url,
            {
                "where": f"{field} IN ({quoted})",
                "outFields": ",".join(out_fields),
                "returnGeometry": "false",
                "f": "json",
            },
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        rows.extend(data.get("features") or [])
        done = min(start + len(chunk), len(unique))
        if done == len(chunk) or done == len(unique) or done % (batch * 8) == 0:
            print(f"    {field} {done}/{len(unique)}", flush=True)
    return rows


def index_attrs(rows: list[dict], fields: list[str]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        attrs = row.get("attributes") or {}
        for field in fields:
            for key in (pin_key(attrs.get(field)), nospace_key(attrs.get(field))):
                if key and key not in indexed:
                    indexed[key] = attrs
    return indexed


def lookup_attr(index: dict[str, dict], *values: Any) -> dict | None:
    for value in values:
        for key in (pin_key(value), nospace_key(value)):
            if key and key in index:
                return index[key]
    return None


def ring_contains(x: float, y: float, ring: list) -> bool:
    inside = False
    count = len(ring)
    if count < 3:
        return False
    previous = count - 1
    for index in range(count):
        xi, yi = ring[index][0], ring[index][1]
        xj, yj = ring[previous][0], ring[previous][1]
        if (yi > y) != (yj > y):
            span = yj - yi
            if span != 0 and x < (xj - xi) * (y - yi) / span + xi:
                inside = not inside
        previous = index
    return inside


def rings_contain(x: float, y: float, rings: list) -> bool:
    hits = 0
    for ring in rings:
        if ring_contains(x, y, ring):
            hits += 1
    return hits % 2 == 1


class PolyIndex:
    """Grid index for point-in-polygon against ArcGIS rings in WGS84."""

    def __init__(self, cell: float = 0.03) -> None:
        self.cell = cell
        self.grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.wide: list[int] = []
        self.items: list[tuple] = []

    def add(self, feature: dict, props: dict) -> None:
        rings = (feature.get("geometry") or {}).get("rings") or []
        if not rings:
            return
        xs = [point[0] for ring in rings for point in ring]
        ys = [point[1] for ring in rings for point in ring]
        if not xs:
            return
        bbox = (min(xs), min(ys), max(xs), max(ys))
        area = abs(ring_signed_m2(rings[0])) if rings[0] else 0.0
        index = len(self.items)
        self.items.append((rings, props, bbox, area))
        x0, x1 = math.floor(bbox[0] / self.cell), math.floor(bbox[2] / self.cell)
        y0, y1 = math.floor(bbox[1] / self.cell), math.floor(bbox[3] / self.cell)
        if (x1 - x0 + 1) * (y1 - y0 + 1) > 600:
            self.wide.append(index)
            return
        for ix in range(x0, x1 + 1):
            for iy in range(y0, y1 + 1):
                self.grid[(ix, iy)].append(index)

    def hits(self, lon: float, lat: float) -> list[dict]:
        key = (math.floor(lon / self.cell), math.floor(lat / self.cell))
        found: list[tuple[float, dict]] = []
        for index in [*self.grid.get(key, []), *self.wide]:
            rings, props, bbox, area = self.items[index]
            if not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
                continue
            if rings_contain(lon, lat, rings):
                found.append((area, props))
        found.sort(key=lambda item: item[0])
        return [props for _area, props in found]


def index_polygons(features: list[dict], prop_fn) -> PolyIndex:
    index = PolyIndex()
    for feature in features:
        props = prop_fn(feature.get("attributes") or {})
        if props:
            index.add(feature, props)
    return index


def stamp_notes(feature: dict, gaps: list[str], appraiser_url: str) -> None:
    props = feature["properties"]
    props["dataGaps"] = gaps
    props["appraiserUrl"] = appraiser_url
    props.pop("_taxPin", None)
    props.pop("_zoningDesc", None)
    props.pop("_district", None)


def jurisdiction_counts(features: list[dict]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for feature in features:
        code = feature["properties"].get("jurisdictionCode") or "UNKNOWN"
        counts[code] += 1
    parts = [f"{name} {counts[name]}" for name in sorted(counts)]
    return "Parcels in this 5–150 acre extract by zoning jurisdiction: " + ", ".join(parts) + "."


DULUTH_UDC = {
    "1": "RA-200",
    "2": "R-100",
    "3": "R-75",
    "4": "RM",
    "5": "R-50",
    "6": "HRD",
    "7": "C-1",
    "8": "C-2",
    "9": "HC-R",
    "10": "HC-A",
    "11": "O-I",
    "12": "O-N",
    "13": "CBD",
    "14": "M-1",
    "15": "M-2",
    "16": "RD",
    "17": "PUD",
}

GWINNETT_APPRAISER = (
    "https://qpublic.schneidercorp.com/Application.aspx?AppID=1282&LayerID=43872&PageTypeID=2&PageID=16058"
)
CHEROKEE_APPRAISER = "https://property.spatialest.com/ga/cherokee/"
CHEROKEE_CITY_NAMES = {
    2: "Ball Ground",
    3: "Canton",
    4: "Holly Springs",
    5: "Nelson",
    6: "Waleska",
    7: "Woodstock",
    8: "Mountain Park",
}
CHEROKEE_FLU = {
    1: "Utilities",
    2: "Workplace Center",
    3: "Regional Center",
    4: "Urban Core",
    5: "Neighborhood Living",
    6: "Suburban Living",
    7: "Suburban Growth",
    8: "Country Estates",
    9: "Rural Places",
    10: "Natural Preserve",
    11: "Bells Ferry LCI",
    12: "SW Cherokee",
    13: "Wild Cat",
    14: "Scenic Corridor",
    15: "Corridor and Nodes",
    16: "Community Village",
}
GWINNETT_FEATURE_GAPS = [
    "No lastSale.qualified flag. Sale amounts of 0 or 1 are omitted as non-market.",
    "County 2045 Future Development is 16 coarse polygons and is not joined as parcel FLU.",
    "No tax.taxableValue. TOTVAL1 and TAXTOT1 were parsed from strings.",
]
CHEROKEE_FEATURE_GAPS = [
    "No public sale price, date, or qualified flag. Sale history is Spatialest only.",
    "Tax market value is partial AGOL CURR_VAL when joined. No assessed or taxable value.",
    "Future Development FLU is coarse plan geography, not a parcel-level land-use code.",
]


def enrich_gwinnett(features: list[dict]) -> list[str]:
    zoning_url = "https://services3.arcgis.com/RfpmnkSAQleRbndX/arcgis/rest/services/Property_and_Tax/FeatureServer/1/query"
    sales_url = "https://services3.arcgis.com/RfpmnkSAQleRbndX/arcgis/rest/services/Property_and_Tax/FeatureServer/10/query"
    lawrenceville_url = "https://gisinfo.lawrencevillega.org/server/rest/services/PlanningDevelopment/PlanningDevelopment/MapServer/2/query"
    lawrenceville_flu_url = "https://gisinfo.lawrencevillega.org/server/rest/services/PlanningDevelopment/PlanningDevelopment/MapServer/0/query"
    duluth_url = "https://services7.arcgis.com/ZTAeUzNBWlnSi6by/arcgis/rest/services/Zoning2024/FeatureServer/150/query"
    duluth_flu_url = "https://services7.arcgis.com/ZTAeUzNBWlnSi6by/arcgis/rest/services/CharacterAreas/FeatureServer/108/query"
    ptc_url = "https://services3.arcgis.com/jEYjQXUX2JTVoctH/arcgis/rest/services/Parcel_Zoning_Sept_2022/FeatureServer/37/query"
    ptc_flu_url = "https://services3.arcgis.com/jEYjQXUX2JTVoctH/arcgis/rest/services/PTC_Character_Area/FeatureServer/15/query"

    zoning_rows = load_layer(zoning_url, "1=1", ["TYPE", "JURISDICTION"], geometry=True, batch=80)
    zoning_index = index_polygons(
        zoning_rows,
        lambda attrs: {"code": clean(attrs.get("TYPE")), "jurisdiction": clean(attrs.get("JURISDICTION"))}
        if clean(attrs.get("TYPE")) or clean(attrs.get("JURISDICTION"))
        else None,
    )
    lawrenceville = index_attrs(
        load_layer(lawrenceville_url, "1=1", ["PIN", "ZoningCode", "ZoningCodeDescription"], geometry=False, batch=400),
        ["PIN"],
    )
    duluth = index_attrs(
        load_layer(duluth_url, "1=1", ["PIN", "UDC_Zoning", "ZONEDESC"], geometry=False, batch=300),
        ["PIN"],
    )
    ptc_rows = load_layer(ptc_url, "1=1", ["TYPE"], geometry=True, batch=80)
    ptc_index = index_polygons(ptc_rows, lambda attrs: {"code": clean(attrs.get("TYPE"))} if clean(attrs.get("TYPE")) else None)
    law_flu = index_polygons(
        load_layer(lawrenceville_flu_url, "1=1", ["CharacterAreas2045"], geometry=True, batch=20),
        lambda attrs: {"code": clean(attrs.get("CharacterAreas2045"))} if clean(attrs.get("CharacterAreas2045")) else None,
    )
    duluth_flu = index_polygons(
        load_layer(duluth_flu_url, "1=1", ["CHARC_AREA", "Label"], geometry=True, batch=20),
        lambda attrs: {"code": clean(attrs.get("CHARC_AREA")), "label": clean(attrs.get("Label"))}
        if clean(attrs.get("CHARC_AREA")) or clean(attrs.get("Label"))
        else None,
    )
    ptc_flu = index_attrs(
        load_layer(ptc_flu_url, "1=1", ["PIN", "Character_", "Character1"], geometry=False, batch=300),
        ["PIN"],
    )
    taxpins = [feature["properties"].get("_taxPin") for feature in features]
    sales = index_attrs(
        query_attributes_in(sales_url, "PIN", [pin for pin in taxpins if pin], ["PIN", "SALE1AMT", "SALE1D"]),
        ["PIN"],
    )

    city_hits = {"LAWRENCEVILLE": 0, "DULUTH": 0, "PEACHTREE CORNERS": 0}
    county_zone = 0
    sale_prices = 0
    flu_hits = 0
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        zone_hits = zoning_index.hits(lon, lat)
        zone = zone_hits[0] if zone_hits else None
        if zone:
            county_zone += 1
            if zone.get("code"):
                props["zoningCode"] = zone["code"]
            if zone.get("jurisdiction"):
                props["jurisdictionCode"] = zone["jurisdiction"]
        jurisdiction = (props.get("jurisdictionCode") or "").upper()
        if jurisdiction == "LAWRENCEVILLE":
            city = lookup_attr(lawrenceville, props.get("parcelId"))
            code = clean(city.get("ZoningCode")) if city else None
            if code:
                props["zoningCode"] = code
                city_hits["LAWRENCEVILLE"] += 1
            flu = law_flu.hits(lon, lat)
            if flu and flu[0].get("code"):
                props["flu"] = flu_info(flu[0]["code"], flu[0]["code"], "Lawrenceville", "lawrenceville-character-areas-2045")
                flu_hits += 1
        elif jurisdiction == "DULUTH":
            city = lookup_attr(duluth, props.get("parcelId"))
            raw_code = clean(city.get("UDC_Zoning")) if city else None
            code = DULUTH_UDC.get(raw_code or "")
            if code:
                props["zoningCode"] = code
                city_hits["DULUTH"] += 1
            flu = duluth_flu.hits(lon, lat)
            if flu and (flu[0].get("code") or flu[0].get("label")):
                props["flu"] = flu_info(
                    flu[0].get("code") or flu[0].get("label"),
                    flu[0].get("label") or flu[0].get("code"),
                    "Duluth",
                    "duluth-character-areas-2024",
                )
                flu_hits += 1
        elif jurisdiction == "PEACHTREE CORNERS":
            city = ptc_index.hits(lon, lat)
            if city and city[0].get("code"):
                props["zoningCode"] = city[0]["code"]
                city_hits["PEACHTREE CORNERS"] += 1
            flu_row = lookup_attr(ptc_flu, props.get("parcelId"))
            code = clean(flu_row.get("Character_")) if flu_row else None
            if code:
                props["flu"] = flu_info(
                    code,
                    clean(flu_row.get("Character1")) if flu_row else code,
                    "Peachtree Corners",
                    "ptc-character-area",
                )
                flu_hits += 1
        sale = lookup_attr(sales, props.get("_taxPin"))
        if sale:
            price = market_sale_price(sale.get("SALE1AMT"))
            sold = parse_mdy(sale.get("SALE1D"))
            props["lastSale"] = {"date": sold, "price": price, "qualified": None}
            if price is not None:
                sale_prices += 1
        else:
            props["lastSale"] = {"date": None, "price": None, "qualified": None}
        stamp_notes(feature, GWINNETT_FEATURE_GAPS, GWINNETT_APPRAISER)
    return [
        jurisdiction_counts(features),
        (
            f"County zoning polygon hit {county_zone} of {len(features)} parcels. "
            f"City REST zoning replaced the county code for Lawrenceville {city_hits['LAWRENCEVILLE']}, "
            f"Duluth {city_hits['DULUTH']}, Peachtree Corners {city_hits['PEACHTREE CORNERS']}. "
            f"Character-area FLU joined for {flu_hits} parcels in those three cities. "
            f"Land Value Table prices above $1 joined for {sale_prices} parcels. qualified is always null."
        ),
    ]


def enrich_cherokee(features: list[dict]) -> list[str]:
    portal_url = "https://gis.cherokeecountyga.gov/arcgis/rest/services/ZoningOnlinePortal/MapServer/3/query"
    cities_url = "https://gis.cherokeecountyga.gov/arcgis/rest/services/MainLayersPRO/MapServer/28/query"
    flu_url = "https://gis.cherokeecountyga.gov/arcgis/rest/services/MainLayersPRO/MapServer/42/query"
    value_url = "https://services9.arcgis.com/CAVmSZdRT9pdZgEk/arcgis/rest/services/Cherokee_County_Parcels_2025/FeatureServer/2/query"
    canton_url = "https://services6.arcgis.com/dpaY3zboICQILFY5/arcgis/rest/services/Canton_Zoning_Parcels/FeatureServer/0/query"
    canton_flu_url = "https://services6.arcgis.com/dpaY3zboICQILFY5/arcgis/rest/services/Character_Area_Future_Land_Use/FeatureServer/0/query"
    woodstock_url = "https://gis.woodstockga.gov/arcgis/rest/services/OpsLayers/CD_ZoningCodes/MapServer/2/query"
    woodstock_flu_url = "https://gis.woodstockga.gov/arcgis/rest/services/OpsLayers/CD_FutureDevelopment/MapServer/1/query"
    ball_url = "https://services9.arcgis.com/CAVmSZdRT9pdZgEk/arcgis/rest/services/Zoning_August_2024/FeatureServer/0/query"

    ids = [feature["properties"].get("parcelId") for feature in features]
    portal = index_attrs(
        query_attributes_in(portal_url, "TIN__No_Spaces_", [pin for pin in ids if pin], ["TIN__No_Spaces_", "Zoning"]),
        ["TIN__No_Spaces_"],
    )
    values = index_attrs(
        query_attributes_in(value_url, "TINNoSpace", [pin for pin in ids if pin], ["TINNoSpace", "CURR_VAL"]),
        ["TINNoSpace"],
    )
    canton = index_attrs(
        load_layer(canton_url, "1=1", ["TINNoSpace", "TIN", "CantonZoning"], geometry=False, batch=300),
        ["TINNoSpace", "TIN"],
    )
    ball = index_attrs(
        load_layer(ball_url, "1=1", ["TINNoSpace", "TIN", "Zoning", "Zoning_Description"], geometry=False, batch=200),
        ["TINNoSpace", "TIN"],
    )
    def cherokee_city(attrs: dict) -> dict | None:
        try:
            name = CHEROKEE_CITY_NAMES.get(int(attrs.get("Jurisidiction")))
        except (TypeError, ValueError):
            return None
        return {"name": name} if name else None

    cities = index_polygons(
        load_layer(cities_url, "1=1", ["Jurisidiction", "CityCodes"], geometry=True, batch=10),
        cherokee_city,
    )
    county_flu = index_polygons(
        load_layer(flu_url, "1=1", ["AreaType"], geometry=True, batch=40),
        lambda attrs: {"code": attrs.get("AreaType")} if attrs.get("AreaType") is not None else None,
    )
    canton_flu = index_polygons(
        load_layer(canton_flu_url, "1=1", ["Character_Area"], geometry=True, batch=20),
        lambda attrs: {"code": clean(attrs.get("Character_Area"))} if clean(attrs.get("Character_Area")) else None,
    )
    woodstock = index_polygons(
        load_layer(woodstock_url, "1=1", ["ZONING", "Description"], geometry=True, batch=20),
        lambda attrs: {"code": clean(attrs.get("ZONING")), "label": clean(attrs.get("Description"))}
        if clean(attrs.get("ZONING")) or clean(attrs.get("Description"))
        else None,
    )
    woodstock_flu = index_polygons(
        load_layer(woodstock_flu_url, "1=1", ["CharacterA"], geometry=True, batch=10),
        lambda attrs: {"code": clean(attrs.get("CharacterA"))} if clean(attrs.get("CharacterA")) else None,
    )

    portal_hits = 0
    city_hits = {"Canton": 0, "Woodstock": 0, "Ball Ground": 0}
    gap_cities = {"Holly Springs": 0, "Waleska": 0, "Nelson": 0, "Mountain Park": 0}
    value_hits = 0
    flu_hits = 0
    unresolved_city = 0
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        parcel_id = props.get("parcelId")
        portal_row = lookup_attr(portal, parcel_id)
        portal_code = clean(portal_row.get("Zoning")) if portal_row else None
        if portal_code and portal_code.upper() != "CITY":
            props["zoningCode"] = portal_code
            portal_hits += 1
        city_hit = cities.hits(lon, lat)
        city_name = city_hit[0]["name"] if city_hit else None
        if city_name:
            props["jurisdictionCode"] = city_name
        else:
            props["jurisdictionCode"] = "UNINCORPORATED"
        zoning_flag = (props.get("zoningCode") or "").upper() == "CITY" or (portal_code or "").upper() == "CITY"
        if zoning_flag and city_name == "Canton":
            city = lookup_attr(canton, parcel_id)
            code = clean(city.get("CantonZoning")) if city else None
            if code:
                props["zoningCode"] = code
                city_hits["Canton"] += 1
        elif zoning_flag and city_name == "Woodstock":
            zones = woodstock.hits(lon, lat)
            base = [item for item in zones if (item.get("code") or "").upper() != "OVER"]
            overlay = [item for item in zones if (item.get("code") or "").upper() == "OVER"]
            if base and base[0].get("code"):
                props["zoningCode"] = base[0]["code"]
                city_hits["Woodstock"] += 1
            elif overlay and (overlay[0].get("label") or overlay[0].get("code")):
                props["zoningCode"] = overlay[0].get("label") or overlay[0].get("code")
                city_hits["Woodstock"] += 1
        elif zoning_flag and city_name == "Ball Ground":
            city = lookup_attr(ball, parcel_id)
            code = clean(city.get("Zoning")) if city else None
            if code:
                props["zoningCode"] = code
                city_hits["Ball Ground"] += 1
        elif zoning_flag and city_name in gap_cities:
            gap_cities[city_name] += 1
        elif zoning_flag:
            unresolved_city += 1
        plan = county_flu.hits(lon, lat)
        if plan and plan[0].get("code") is not None:
            try:
                area_code = int(plan[0]["code"])
            except (TypeError, ValueError):
                area_code = None
            if area_code is not None:
                props["flu"] = flu_info(
                    str(area_code),
                    CHEROKEE_FLU.get(area_code, str(area_code)),
                    "Cherokee County",
                    "cherokee-future-development",
                )
                flu_hits += 1
        if city_name == "Canton":
            local = canton_flu.hits(lon, lat)
            if local and local[0].get("code"):
                props["flu"] = flu_info(local[0]["code"], local[0]["code"], "Canton", "canton-character-area-flu")
        elif city_name == "Woodstock":
            local = woodstock_flu.hits(lon, lat)
            if local and local[0].get("code"):
                props["flu"] = flu_info(local[0]["code"], local[0]["code"], "Woodstock", "woodstock-future-development")
        value = lookup_attr(values, parcel_id)
        market = num(value.get("CURR_VAL")) if value else None
        if market is not None and market > 0:
            props["tax"]["marketValue"] = market
            value_hits += 1
        props["tax"]["assessedValue"] = None
        props["tax"]["taxableValue"] = None
        props["lastSale"] = {"date": None, "price": None, "qualified": None}
        stamp_notes(feature, CHEROKEE_FEATURE_GAPS, CHEROKEE_APPRAISER)
    gap_text = ", ".join(f"{name} {gap_cities[name]}" for name in gap_cities)
    return [
        jurisdiction_counts(features),
        (
            f"ZoningOnlinePortal codes joined for {portal_hits} unincorporated-style parcels. "
            f"CITY overlays: Canton {city_hits['Canton']}, Woodstock {city_hits['Woodstock']}, "
            f"Ball Ground {city_hits['Ball Ground']}. Zoning=CITY left unresolved for {gap_text}"
            f"{'' if unresolved_city == 0 else f', plus {unresolved_city} outside a city polygon'}. "
            f"Coarse Future Development FLU joined for {flu_hits} parcels; Canton and Woodstock character areas replace it inside those cities. "
            f"CURR_VAL market proxy joined for {value_hits} parcels. No sale price or date."
        ),
    ]


CLAYTON_DISTRICT = {
    "1": "UNINCORPORATED",
    "8": "UNINCORPORATED",
    "2": "COLLEGE PARK",
    "3": "FOREST PARK",
    "4": "JONESBORO",
    "5": "MORROW",
    "6": "RIVERDALE",
    "7": "LAKE CITY",
    "9": "LOVEJOY",
}
CLAYTON_APPRAISER = "https://publicaccess.claytoncountyga.gov/search/commonsearch.aspx?mode=realprop"
CLAYTON_FEATURE_GAPS = [
    "No lastSale.qualified flag. A sale price of 0 is omitted.",
    "PEZ future land use and Comp Plan 2039 cover unincorporated parcels. City FLU is not on those layers.",
    "No tax.taxableValue. Most city zoning is the coarse county ZONE code.",
]


def enrich_clayton(features: list[dict]) -> list[str]:
    pez_url = "https://gis.claytoncountyga.gov/server/rest/services/Hosted/PEZ_CurrentZoningProCached/FeatureServer/1/query"
    comp_url = "https://services5.arcgis.com/m528W8U8YDYeMPrQ/arcgis/rest/services/Comp_Plan_Deliverables_06202024/FeatureServer/0/query"
    unincorporated = []
    for feature in features:
        district = CLAYTON_DISTRICT.get(feature["properties"].get("_district") or "")
        feature["properties"]["jurisdictionCode"] = district
        if district == "UNINCORPORATED":
            unincorporated.append(feature["properties"].get("parcelId"))
    pez = index_attrs(
        query_attributes_in(
            pez_url,
            "parcelid",
            [pin for pin in unincorporated if pin],
            ["parcelid", "zoning", "futurelu"],
        ),
        ["parcelid"],
    )
    pez_zone = 0
    pez_flu = 0
    missing_flu: list[str] = []
    rex = 0
    sale_prices = 0
    for feature in features:
        props = feature["properties"]
        if props.get("jurisdictionCode") == "UNINCORPORATED" and (props.get("situsCity") or "").upper() == "REX":
            rex += 1
        if props.get("jurisdictionCode") == "UNINCORPORATED":
            row = lookup_attr(pez, props.get("parcelId"))
            code = clean(row.get("zoning")) if row else None
            flu = clean(row.get("futurelu")) if row else None
            if code:
                props["zoningCode"] = code
                pez_zone += 1
            if flu:
                props["flu"] = flu_info(flu, flu, "Clayton County", "clayton-pez-futurelu")
                pez_flu += 1
            elif props.get("parcelId"):
                missing_flu.append(props["parcelId"])
        if props.get("lastSale", {}).get("price") is not None:
            sale_prices += 1
        props["lastSale"]["qualified"] = None
    comp_flu = 0
    if missing_flu:
        comp = index_attrs(
            query_attributes_in(comp_url, "PARCELID", missing_flu, ["PARCELID", "F2039_FLUM"]),
            ["PARCELID"],
        )
        for feature in features:
            props = feature["properties"]
            if props.get("flu"):
                continue
            row = lookup_attr(comp, props.get("parcelId"))
            flu = clean(row.get("F2039_FLUM")) if row else None
            if flu:
                props["flu"] = flu_info(flu, flu, "Clayton County", "clayton-comp-plan-2039-flum")
                comp_flu += 1
    for feature in features:
        stamp_notes(feature, CLAYTON_FEATURE_GAPS, CLAYTON_APPRAISER)
    return [
        jurisdiction_counts(features),
        (
            f"Unincorporated zoning replaced from PEZ CurrentZoning for {pez_zone} parcels. "
            f"PEZ futurelu joined for {pez_flu}; Comp Plan 2039 FLUM filled {comp_flu} more. "
            f"City parcels keep TaxAssessor ZONE (Forest Park is the richest code set; "
            f"Morrow, Jonesboro, Riverdale, Lake City, and Lovejoy are mostly coarse R/C/I). "
            f"Rex is unincorporated: {rex} parcels in this band use county zoning, not a city district. "
            f"Sale prices above 0: {sale_prices}. qualified is always null."
        ),
    ]


def enrich_county(name: str, features: list[dict]) -> list[str]:
    if name == "gwinnett":
        return enrich_gwinnett(features)
    if name == "cherokee":
        return enrich_cherokee(features)
    if name == "clayton":
        return enrich_clayton(features)
    raise RuntimeError(f"Unknown parcel enricher {name}")


def county_override(fips: str) -> dict | None:
    if fips == "13057":  # Cherokee GA
        return {
            "kind": "arcgis",
            "url": "https://gis.cherokeecountyga.gov/arcgis/rest/services/MainLayersPRO/MapServer/1/query",
            "where": "Acreage>=5 AND Acreage<=150",
            "outFields": [
                "TIN",
                "TINNoSpace",
                "PIN",
                "Acreage",
                "OWNER",
                "Mailing_Address",
                "Mailing_Suite",
                "Mailing_City",
                "Mailing_State",
                "Mailing_Zip",
                "Property_Address",
                "Property_City",
                "Property_Zip",
                "Zoning",
            ],
            "idField": "TINNoSpace",
            "idFallbacks": ["TIN", "PIN"],
            "acresField": "Acreage",
            "ownerField": "OWNER",
            "situsField": "Property_Address",
            "cityField": "Property_City",
            "zipField": "Property_Zip",
            "zoningField": "Zoning",
            "mail1Field": "Mailing_Address",
            "mail2Field": "Mailing_Suite",
            "mailCityField": "Mailing_City",
            "mailStateField": "Mailing_State",
            "mailZipField": "Mailing_Zip",
            "source": "ga-cherokee-mainlayers-parcels",
            "coverage": "complete-gte-5ac",
            "enrich": "cherokee",
            "gaps": [
                "Parcels are Cherokee MainLayersPRO MapServer/1 on gis.cherokeecountyga.gov. gis.cherokeega.com is not used (certificate hostname mismatch).",
                "AGOL Cherokee_County_Parcels_2025 is a slightly older backup. It is not the polygon source. CURR_VAL from that backup is joined as a partial tax.marketValue only.",
                "No assessed value, taxable value, or land/improvement split on the county REST layers.",
                "No public sale price, sale date, or lastSale.qualified. Parcels have DEEDBOOK/DEEDPAGE only. Sale history is Spatialest HTML, not a GIS join.",
                "Unincorporated zoning comes from ZoningOnlinePortal MapServer/3 (TYPE equivalent field Zoning) joined on TINNoSpace. County Zoning=CITY is only a municipal flag.",
                "Canton, Woodstock, and Ball Ground replace Zoning=CITY from each city's public REST. Holly Springs, Waleska, Nelson, and Mountain Park have no public zoning REST, so those parcels stay CITY.",
                "Future Development MapServer/42 (205 AreaType polygons) is a coarse FLU join, not parcel-level future land use. Canton and Woodstock character areas replace it inside those cities. Ball Ground has no city FLU layer.",
                "Appraiser search is https://property.spatialest.com/ga/cherokee/.",
            ],
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
    if fips == "13135":  # Gwinnett GA
        return {
            "kind": "arcgis",
            "url": "https://gis3.gwinnettcounty.com/mapvis/rest/services/GISDataBrowser/GC_Parcel/MapServer/6/query",
            "where": "CALCULATEDACREAGE>=5 AND CALCULATEDACREAGE<=150",
            "outFields": [
                "PIN",
                "TAXPIN",
                "CALCULATEDACREAGE",
                "OWNER1",
                "OWNER2",
                "LOCADDR",
                "LOCCITY",
                "LOCZIP",
                "MAILADDR",
                "MAILCITY",
                "MAILSTAT",
                "MAILZIP",
                "TOTVAL1",
                "TAXTOT1",
                "ZONING",
                "ZONEDESC",
                "PROPCLAS",
            ],
            "idField": "PIN",
            "idFallbacks": ["TAXPIN"],
            "acresField": "CALCULATEDACREAGE",
            "ownerField": "OWNER1",
            "owner2Field": "OWNER2",
            "situsField": "LOCADDR",
            "cityField": "LOCCITY",
            "zipField": "LOCZIP",
            "zoningField": "ZONING",
            "zoningDescriptionField": "ZONEDESC",
            "dorField": "PROPCLAS",
            "marketValueField": "TOTVAL1",
            "assessedField": "TAXTOT1",
            "mail1Field": "MAILADDR",
            "mailCityField": "MAILCITY",
            "mailStateField": "MAILSTAT",
            "mailZipField": "MAILZIP",
            "taxPinField": "TAXPIN",
            "source": "ga-gwinnett-gc-parcel",
            "coverage": "complete-gte-5ac",
            "enrich": "gwinnett",
            "gaps": [
                "Parcels are Gwinnett GC_Parcel MapServer/6. AGOL Property_and_Tax FeatureServer/0 is geometry and PIN only and is not the parcel source.",
                "Acreage is CALCULATEDACREAGE 5–150. Deeded acreage is often 0 and was not used.",
                "Zoning polygons are county-wide Property_and_Tax FeatureServer/1 (TYPE and JURISDICTION), including unincorporated. The parcel CAMA ZONING string is only the fallback.",
                "Lawrenceville, Duluth, and Peachtree Corners replace TYPE with the city's own REST zoning where the parcel joins. Duluth uses the UDC_Zoning domain (RA-200 through PUD), not the joined county CAMA code.",
                "Other municipalities (Suwanee, Norcross, Snellville, Buford, Sugar Hill, Lilburn, Dacula, Grayson, Berkeley Lake, Loganville, Auburn, Braselton, Mulberry, Rest Haven) have no independent public zoning REST. They use the county zoning layer filtered by JURISDICTION.",
                "Sales join Property_and_Tax FeatureServer/10 (Land Value Table) on TAXPIN = trimmed PIN, using SALE1AMT and SALE1D. There is no lastSale.qualified flag. Amounts of 0 or 1 are omitted.",
                "County 2045 Future Development (GC_Planning/7) is 16 coarse INTENSITY polygons and is not joined as parcel FLU. Character-area FLU is joined only for Lawrenceville, Duluth, and Peachtree Corners.",
                "TOTVAL1 and TAXTOT1 are parsed from strings. There is no tax.taxableValue.",
                "Buford, Loganville, Auburn, and Braselton cross county lines. This extract covers the Gwinnett footprint only.",
                "Appraiser search is qPublic AppID 1282. Automated clients often get a CDN 403; the page is public for people.",
            ],
        }
    if fips == "13063":  # Clayton GA
        return {
            "kind": "arcgis",
            "url": "https://gis.claytoncountyga.gov/server/rest/services/TaxAssessor/Parcels/MapServer/0/query",
            "where": "ACERAGE>=5 AND ACERAGE<=150",
            "outFields": [
                "PARCELID",
                "ACERAGE",
                "OWNERNME",
                "PSTLADDRES",
                "PSTLCITY",
                "PSTLSTATE",
                "PSTLZIP5",
                "SITEADDRES",
                "SITECITY",
                "SITEZIP5",
                "ZONE",
                "APPRVAL",
                "ASSESSVAL",
                "SALEDATE",
                "SALEPRICE",
                "LANDUSEC",
                "CVTTXCD",
            ],
            "idField": "PARCELID",
            "acresField": "ACERAGE",
            "ownerField": "OWNERNME",
            "situsField": "SITEADDRES",
            "cityField": "SITECITY",
            "zipField": "SITEZIP5",
            "zoningField": "ZONE",
            "dorField": "LANDUSEC",
            "marketValueField": "APPRVAL",
            "assessedField": "ASSESSVAL",
            "salePriceField": "SALEPRICE",
            "saleDateField": "SALEDATE",
            "mail1Field": "PSTLADDRES",
            "mailCityField": "PSTLCITY",
            "mailStateField": "PSTLSTATE",
            "mailZipField": "PSTLZIP5",
            "districtField": "CVTTXCD",
            "source": "ga-clayton-tax-parcels",
            "coverage": "complete-gte-5ac",
            "enrich": "clayton",
            "gaps": [
                "Parcels are Clayton TaxAssessor/Parcels MapServer/0. Acreage field on the service is spelled ACERAGE.",
                "Owner, situs, ZONE, APPRVAL, ASSESSVAL, SALEDATE, and SALEPRICE are on the parcel polygon. Value and sale fields are strings.",
                "There is no lastSale.qualified flag. A sale price of 0 is omitted. Multi-sale history is the publicaccess sales search, not a GIS join.",
                "Unincorporated zoning and FLU join Hosted PEZ_CurrentZoningProCached FeatureServer/1 on PARCELID (zoning + futurelu). Comp Plan 2039 FLUM fills unincorporated parcels the PEZ futurelu misses.",
                "PEZ and Comp Plan 2039 do not cover city parcels. Forest Park, Morrow, Jonesboro, Riverdale, Lake City, and Lovejoy use county ZONE filtered by CVTTXCD. Forest Park codes are the richest. The other cities are mostly coarse R/C/I. No independent city zoning FeatureServer is wired.",
                "Rex is an unincorporated place, not a tax district. Those parcels stay on county PEZ/ZONE. There is no Rex zoning layer.",
                "College Park (CVTTXCD 2) is only the Clayton footprint. The Fulton side is out of this extract.",
                "FLUM_Composite_04122024 is a 15-feature sample and is not used. Future Land Use 2034 is older and is not the FLU source.",
                "No tax.taxableValue field.",
                "Appraiser search is https://publicaccess.claytoncountyga.gov/search/commonsearch.aspx?mode=realprop.",
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
        return "No public statewide Georgia parcel polygon service. This county is not in the Cobb, DeKalb, Cherokee, Clayton, or Gwinnett pull."
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
| Georgia | Cobb, DeKalb, and Gwinnett county services. Cherokee and Clayton adapters are in the seeder | Cobb complete. DeKalb is a polygon-acre sample. Gwinnett is a complete 5–150 acre extract. Cherokee and Clayton are wired in `county_override` and stay gaps until that pull is run. Other Georgia counties are gaps |
| South Carolina | Dorchester public parcels; Greenville city GIS | Dorchester complete. Greenville is a city-hosted sample. Charleston County's GIS requires a token. Other counties are gaps |
| Alabama | Jefferson County parcels | Jefferson is a complete 5–150 acre extract. Other Alabama counties are gaps |

Zoning is joined when a public county or city layer carries it. DeKalb uses the parcel zoning attribute. Gwinnett uses county-wide zoning polygons (TYPE and JURISDICTION), then city zoning for Lawrenceville, Duluth, and Peachtree Corners. Cherokee and Clayton seed adapters are in the script and were not tiled in this pull. It is not a multifamily knowledge-base match outside Orange County. Prefer **All parcels** in these markets.

## Gwinnett

Gwinnett parcels come from `GC_Parcel` MapServer/6 (owner, situs, string tax values, CAMA zoning). AGOL `Property_and_Tax` FeatureServer/0 is geometry and PIN only and is not the parcel source. Zoning is the county-wide FeatureServer/1 layer, which covers unincorporated and every municipality. Lawrenceville, Duluth, and Peachtree Corners then replace that code from each city's REST. Suwanee, Norcross, Snellville, Buford, Sugar Hill, Lilburn, Dacula, Grayson, Berkeley Lake, Loganville, Auburn, Braselton, Mulberry, and Rest Haven stay on the county `JURISDICTION` filter. Sales join the Land Value Table on TAXPIN (`SALE1AMT` / `SALE1D`). There is no sale qualified flag. The 2045 Future Development Map is 16 coarse polygons and is not parcel FLU. Character-area FLU is joined only inside Lawrenceville, Duluth, and Peachtree Corners. Human search is qPublic AppID 1282.

Cherokee and Clayton adapters are in `county_override` (`--county Cherokee`, `--county Clayton`) and are not tiled yet. Cherokee would use MainLayersPRO MapServer/1 on `gis.cherokeecountyga.gov` (not `gis.cherokeega.com`). It has no sale price or date; `CURR_VAL` on the older AGOL backup is only a partial market-value join. Unincorporated zoning is ZoningOnlinePortal MapServer/3. `Zoning=CITY` would use Canton, Woodstock, and Ball Ground. Holly Springs, Waleska, Nelson, and Mountain Park have no public zoning service. Clayton would use TaxAssessor/Parcels MapServer/0. Sales there have no qualified flag. Unincorporated zoning and future land use would join PEZ FeatureServer/1 on `PARCELID`, with Comp Plan 2039 as the fallback. Forest Park, Morrow, Jonesboro, Riverdale, Lake City, and Lovejoy stay on county `ZONE` filtered by `CVTTXCD`. Rex is unincorporated.

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
                gaps=list(spec.get("gaps") or []),
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
    if spec.get("enrich"):
        print(f"  enrich {spec['enrich']}", flush=True)
        extra_gaps = enrich_county(spec["enrich"], features)
        spec = dict(spec)
        spec["gaps"] = [*(spec.get("gaps") or []), *extra_gaps]
    if not all(in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{fips} emitted a parcel outside 5–150 acres")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"sourceCount": expected, "dropped": dropped, "features": features}, separators=(",", ":"))
    )
    coverage = spec["coverage"]
    gaps = list(spec.get("gaps") or [])
    if expected and len(features) < expected and not spec.get("computeAcres"):
        gaps.insert(
            0,
            f"{expected} source rows collapsed to {len(features)} parcel ids (duplicate ids, stacked units, or rings that failed the WGS84 check). The acreage query covered the county.",
        )
    if not features:
        coverage = "gap"
        gaps.insert(0, f"Source count was {expected} but none survived the 5–150 acre and WGS84 checks.")
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
