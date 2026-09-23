#!/usr/bin/env python3
"""Seed Orlando shed parcel fixtures from public GIS.

Core counties (Lake, Orange, Osceola, Polk, Seminole) are a complete extract of
parcels whose FDOR land area is from 5.0 through 150.0 acres
(``217800 <= LND_SQFOOT <= 6534000``) from Florida DOH EHWATER. Orange is enriched with
OCPA zoning / owner / sale / tax and with Orange County + Orlando future land
use. Geometries are simplified and written as viewport tiles.

Brevard, Marion, Sumter, and Volusia stay on the thinner sample unless
``--refresh-samples`` is passed.

  npm run seed:parcels:orlando
  python3 scripts/seed_orlando_parcels.py --full-core
  python3 scripts/seed_orlando_parcels.py --county Polk --full-core
  python3 scripts/seed_orlando_parcels.py --sample --per-county 120

Tile origin matches ``ORLANDO_PARCEL_TILE`` in src/lib/orlandoParcels.ts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from parcel_geometry import esri_rings_to_geojson, representative_point, simplify_ring as simplify_ring_shared
from seed_fixtures import epoch_to_iso, parse_zoning

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "fixtures" / "orlando-parcels"
TILE_DIR = OUT_DIR / "tiles"
LOOKUP_DIR = OUT_DIR / "lookup"
SOURCES = ROOT / "data" / "orlando-parcel-sources.json"
RURAL_CSV = ROOT / "data" / "oz2-7markets-90min-rural-eligible.csv"
ORANGE_PARCELS = ROOT / "data" / "fixtures" / "parcels.geojson"
RURAL_GEOJSON = ROOT / "data" / "fixtures" / "oz2-rural-markets.geojson"
OZ_POLYS = ROOT / "data" / "fixtures" / "opportunity-zones.geojson"
OZ2_POLYS = ROOT / "data" / "fixtures" / "oz2-eligible.geojson"
META_OUT = OUT_DIR / "meta.json"
CACHE_DIR = Path("/tmp/dls-orlando-core")

DOH_BASE = "https://gis.floridahealth.gov/server/rest/services/EHWATER/Parcels/MapServer"
OCPA_QUERY = "https://vgispublic.ocpafl.org/server/rest/services/Webmap/PARCEL/MapServer/4/query"
OC_FLU_URL = "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21/query"
ORL_FLU_URL = "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83/query"

# Keep in sync with src/lib/orlandoParcels.ts ORLANDO_PARCEL_TILE.
ORIGIN_LON = -83.0
ORIGIN_LAT = 27.0
TILE_DEG = 0.25
MIN_ACRES = 5.0
MAX_ACRES = 150.0
MIN_SQFT = 217800  # 5.0 * 43560
MAX_SQFT = 6534000  # 150.0 * 43560
CORE_COUNTIES = ("Lake", "Orange", "Osceola", "Polk", "Seminole")

DOH_FIELDS = [
    "PARCEL_ID",
    "OWN_NAME",
    "PHY_ADDR1",
    "PHY_ADDR2",
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
    "CO_NO",
]
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
]

TRACT_PAD = 0.045
SAMPLE_WINDOWS: dict[str, list[tuple[float, float, float, float]]] = {
    "Seminole": [(-81.38, 28.68, -81.28, 28.78), (-81.32, 28.74, -81.22, 28.84)],
    "Orange": [(-81.25, 28.52, -81.15, 28.62)],
}

OC_LABELS = {
    "R": "Rural / Agricultural",
    "1/1": "Rural Settlement 1/1",
    "1/2": "Rural Settlement 1/2",
    "1/5": "Rural Settlement 1/5",
    "LD": "Low Density Residential",
    "LM": "Low-Medium Density Residential",
    "MD": "Medium Density Residential",
    "HD": "High Density Residential",
    "TND": "Traditional Neighborhood",
    "NAC": "Neighborhood Activity Corridor",
    "NC": "Neighborhood Center",
    "NR": "Neighborhood Residential",
    "ACR": "Activity Center Residential",
    "ACMU": "Activity Center Mixed Use",
    "CVC": "Community Village Center",
    "V": "Village (Horizon West)",
    "O": "Office",
    "C": "Commercial",
    "I": "Industrial",
    "IN": "Institutional",
    "E": "Education",
    "P/R": "Parks / Recreation",
    "PRES": "Preservation",
    "PD": "Planned Development",
    "WB": "Water Body",
    "City": "Municipal (county placeholder)",
}
ORL_LABELS = {
    "RES-LOW": "Residential, Low Intensity",
    "RES-MED": "Residential, Medium Intensity",
    "RES-HIGH": "Residential, High Intensity",
    "MU-ND": "Mixed Use / Neighborhood Development",
    "MUC-MED": "Mixed Use Corridor, Medium Intensity",
    "MUC-HIGH": "Mixed Use Corridor, High Intensity",
    "NEIGH-AC": "Neighborhood Activity Center",
    "COMM-AC": "Community Activity Center",
    "UR-AC": "Urban Activity Center",
    "MET-AC": "Metropolitan Activity Center",
    "DT-AC": "Downtown Activity Center",
    "URB-VIL": "Urban Village",
    "OFFICE-LOW": "Office, Low Intensity",
    "OFFICE-MED": "Office, Medium Intensity",
    "OFFICE-HIGH": "Office, High Intensity",
    "INDUST": "Industrial",
    "CONSERV": "Conservation",
    "PUB-REC-INST": "Public / Recreational and Institutional",
    "AIR-HIGH": "Airport Support, High Intensity",
    "AIR-MED": "Airport Support, Medium Intensity",
}


def fetch_json(url: str, params: dict | None = None, timeout: int = 120, retries: int = 5) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/orlando-parcels"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.4 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:180]}: {last}")


def simplify_ring(coords: list[list[float]], tol: float = 0.000012) -> list[list[float]]:
    return simplify_ring_shared(coords, tol)


def rings_to_geojson(geom: dict | None) -> dict | None:
    if not geom or not geom.get("rings"):
        return None
    return esri_rings_to_geojson(geom["rings"])


def centroid(geom: dict) -> tuple[float, float] | None:
    return representative_point(geom)


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def zip_str(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(int(float(value))).zfill(5)[:5]
    except (TypeError, ValueError):
        return clean(value)


def sale_date(year: Any, month: Any) -> str | None:
    try:
        y = int(float(year))
        m = int(float(month)) if month not in (None, "", "0", 0) else 1
        if y < 1900 or y > 2100:
            return None
        if m < 1 or m > 12:
            m = 1
        return f"{y:04d}-{m:02d}-01"
    except (TypeError, ValueError):
        return None


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_feature(x: float, y: float, feature: dict) -> bool:
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        rings = geom["coordinates"]
        if not rings or not point_in_ring(x, y, rings[0]):
            return False
        for hole in rings[1:]:
            if point_in_ring(x, y, hole):
                return False
        return True
    if geom.get("type") == "MultiPolygon":
        for poly in geom["coordinates"]:
            if poly and point_in_ring(x, y, poly[0]) and not any(point_in_ring(x, y, h) for h in poly[1:]):
                return True
    return False


def feature_bbox(feature: dict) -> tuple[float, float, float, float] | None:
    geom = feature.get("geometry") or {}
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, (int, float)):
            return
        if node and isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        for item in node:
            walk(item)

    walk(geom.get("coordinates") or [])
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


class GridIndex:
    def __init__(self, cell: float = 0.03) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = feature_bbox(feature)
        if not bbox:
            return
        west, south, east, north = bbox
        ix0 = math.floor(west / self.cell)
        ix1 = math.floor(east / self.cell)
        iy0 = math.floor(south / self.cell)
        iy1 = math.floor(north / self.cell)
        # Very large polygons are tested on every query instead of filling the grid.
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 500:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        ix = math.floor(x / self.cell)
        iy = math.floor(y / self.cell)
        for feature in self.buckets.get((ix, iy), []):
            if point_in_feature(x, y, feature):
                return feature
        for feature in self.broad:
            if point_in_feature(x, y, feature):
                return feature
        return None


def load_orlando_rural_windows() -> dict[str, list[tuple[float, float, float, float]]]:
    windows: dict[str, list[tuple[float, float, float, float]]] = {k: list(v) for k, v in SAMPLE_WINDOWS.items()}
    with RURAL_CSV.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row["market"] != "Orlando" or row["state"] != "Florida":
                continue
            county = row["county"]
            lon = float(row["lon"])
            lat = float(row["lat"])
            windows.setdefault(county, []).append(
                (lon - TRACT_PAD, lat - TRACT_PAD, lon + TRACT_PAD, lat + TRACT_PAD)
            )
    return windows


def load_geojson_features(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("features") or []


def normalize_doh(attrs: dict, geom: dict, county: dict) -> dict | None:
    sqft = _num(attrs.get("LND_SQFOOT"))
    if sqft is None or sqft < MIN_SQFT or sqft > MAX_SQFT:
        return None
    geometry = rings_to_geojson(geom)
    if not geometry:
        return None
    center = centroid(geometry)
    if not center:
        return None
    if not (-88 < center[0] < -79 and 24 < center[1] < 31.5):
        return None
    parcel_id = clean(attrs.get("PARCEL_ID"))
    if not parcel_id:
        return None
    acreage = round(sqft / 43560.0, 4)
    if acreage < MIN_ACRES or acreage > MAX_ACRES:
        return None
    fips = county["fips"]
    feature_id = f"{fips}:{parcel_id}"
    price = _num(attrs.get("SALE_PRC1"))
    if price is not None and price <= 0:
        price = None
    return {
        "type": "Feature",
        "id": feature_id,
        "properties": {
            "id": feature_id,
            "parcelId": parcel_id,
            "countyFips": fips,
            "countyName": county["name"],
            "state": "Florida",
            "marketIds": ["Orlando"],
            "situsAddress": clean(attrs.get("PHY_ADDR1")),
            "situsCity": clean(attrs.get("PHY_CITY")),
            "situsZip": zip_str(attrs.get("PHY_ZIPCD")),
            "jurisdictionCode": None,
            "ownerName": clean(attrs.get("OWN_NAME")),
            "ownerName2": None,
            "propertyName": None,
            "zoningCode": None,
            "zoningDistrict": None,
            "jurisdictionPrefix": None,
            "dorCode": clean(attrs.get("DOR_UC")),
            "acreage": acreage,
            "acreageSource": "fdor-lnd-sqfoot",
            "centroid": list(center),
            "lastSale": {
                "date": sale_date(attrs.get("SALE_YR1"), attrs.get("SALE_MO1")),
                "price": price,
                "qualified": clean(attrs.get("QUAL_CD1")),
            },
            "tax": {
                "marketValue": _num(attrs.get("JV")),
                "assessedValue": _num(attrs.get("AV_SD")),
                "taxableValue": _num(attrs.get("TV_SD")),
                "taxes": None,
            },
            "mailingAddress": {
                "line1": clean(attrs.get("OWN_ADDR1")),
                "line2": clean(attrs.get("OWN_ADDR2")),
                "city": clean(attrs.get("OWN_CITY")),
                "state": clean(attrs.get("OWN_STATE")),
                "zip": zip_str(attrs.get("OWN_ZIPCD")),
            },
            "incomeTract": None,
            "incomeBlockGroup": None,
            "nearestRoad": None,
            "flu": None,
            "opportunityZone": None,
            "oz2Eligibility": None,
            "appraiserUrl": county.get("appraiserSearchUrl"),
            "source": f"fl-doh-ehwaters-{fips}",
            "dataGaps": list(county.get("gaps") or []),
        },
        "geometry": geometry,
    }


def count_where(url: str, where: str) -> int:
    data = fetch_json(url, {"where": where, "returnCountOnly": "true", "f": "json"})
    if data.get("error"):
        raise RuntimeError(data["error"])
    count = data.get("count")
    if not isinstance(count, int):
        raise RuntimeError(f"No count from {url}: {data}")
    return count


def fetch_object_ids(url: str, where: str) -> list[int]:
    data = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    if data.get("error"):
        raise RuntimeError(data["error"])
    ids = data.get("objectIds") or []
    return [int(i) for i in ids]


def fetch_by_object_ids(url: str, ids: list[int], params: dict, batch: int = 250) -> list[dict]:
    features: list[dict] = []
    total = len(ids)
    for start in range(0, total, batch):
        chunk = ids[start : start + batch]
        query = dict(params)
        query["objectIds"] = ",".join(str(i) for i in chunk)
        query["f"] = "json"
        try:
            data = fetch_json(url, query, timeout=180)
        except RuntimeError:
            if len(chunk) > 40:
                features.extend(fetch_by_object_ids(url, chunk, params, batch=max(40, len(chunk) // 2)))
                continue
            raise
        if data.get("error"):
            if len(chunk) > 40:
                features.extend(fetch_by_object_ids(url, chunk, params, batch=max(40, len(chunk) // 2)))
                continue
            raise RuntimeError(data["error"])
        features.extend(data.get("features") or [])
        done = min(start + batch, total)
        if done == batch or done == total or done % (batch * 4) == 0:
            print(f"    {done}/{total}")
        time.sleep(0.08)
    return features


def polygon_parts(geometry: dict) -> list:
    if geometry.get("type") == "Polygon":
        return [geometry["coordinates"]]
    if geometry.get("type") == "MultiPolygon":
        return list(geometry["coordinates"])
    return []


def merge_parcel_parts(existing: dict, extra: dict) -> dict:
    parts = polygon_parts(existing["geometry"]) + polygon_parts(extra["geometry"])
    geometry = {"type": "MultiPolygon", "coordinates": parts}
    center = centroid(geometry)
    if center:
        existing["properties"]["centroid"] = list(center)
    existing["geometry"] = geometry
    return existing


def download_core_county(county: dict) -> tuple[list[dict], int, int, int]:
    layer = county["dohLayerId"]
    url = f"{DOH_BASE}/{layer}/query"
    where = f"LND_SQFOOT >= {MIN_SQFT} AND LND_SQFOOT <= {MAX_SQFT}"
    expected = count_where(url, where)
    cache_path = CACHE_DIR / f"{county['fips']}-geom2.json"
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        if cached.get("geometryVersion") == 2 and cached.get("sourceCount") == expected and cached.get("features"):
            print(f"  cache hit {cache_path.name} ({len(cached['features'])} features, source {expected})")
            return (
                cached["features"],
                expected,
                int(cached.get("dropped") or 0),
                int(cached.get("merged") or 0),
            )

    print(f"  DOH object ids: {expected}")
    ids = fetch_object_ids(url, where)
    raw = fetch_by_object_ids(
        url,
        ids,
        {
            "outFields": ",".join(DOH_FIELDS),
            "returnGeometry": "true",
            "outSR": 4326,
        },
        batch=200,
    )
    by_id: dict[str, dict] = {}
    dropped = 0
    merged = 0
    for item in raw:
        feature = normalize_doh(item.get("attributes") or {}, item.get("geometry") or {}, county)
        if not feature:
            dropped += 1
            continue
        feature_id = feature["properties"]["id"]
        previous = by_id.get(feature_id)
        if previous is None:
            by_id[feature_id] = feature
            continue
        merged += 1
        by_id[feature_id] = merge_parcel_parts(previous, feature)
    features = list(by_id.values())
    if merged:
        print(f"  merged {merged} extra parts into {len(features)} parcel ids")
    accounted = len(features) + merged
    if accounted < expected * 0.97:
        raise RuntimeError(
            f"{county['name']} kept {len(features)} parcels plus {merged} merged parts from {expected} source rows (dropped {dropped}). Refusing a thin extract."
        )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "geometryVersion": 2,
                "sourceCount": expected,
                "dropped": dropped,
                "merged": merged,
                "features": features,
            }
        )
    )
    print(f"  normalized {len(features)} (dropped {dropped}, merged parts {merged}, source {expected})")
    return features, expected, dropped, merged


def enrich_orange_ocpa(features: list[dict]) -> int:
    ids = [f["properties"]["parcelId"] for f in features]
    found: dict[str, dict] = {}

    def one_batch(chunk: list[str]) -> list[dict]:
        where = "PARCEL IN (" + ",".join("'" + pid.replace("'", "''") + "'" for pid in chunk) + ")"
        data = fetch_json(
            OCPA_QUERY,
            {
                "where": where,
                "outFields": ",".join(OCPA_FIELDS),
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=90,
        )
        if data.get("error"):
            raise RuntimeError(data["error"])
        return data.get("features") or []

    print(f"  OCPA attribute join for {len(ids)} parcels")
    batches = [ids[i : i + 60] for i in range(0, len(ids), 60)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(one_batch, chunk) for chunk in batches]
        done = 0
        for fut in as_completed(futures):
            for item in fut.result():
                attrs = item.get("attributes") or {}
                pid = clean(attrs.get("PARCEL"))
                if pid:
                    found[pid] = attrs
            done += 1
            if done % 40 == 0 or done == len(batches):
                print(f"    ocpa batches {done}/{len(batches)} matched {len(found)}")

    matched = 0
    for feature in features:
        props = feature["properties"]
        attrs = found.get(props["parcelId"])
        if not attrs:
            continue
        matched += 1
        zoning = parse_zoning(clean(attrs.get("ZONING_CODE")))
        props.update(zoning)
        props["jurisdictionCode"] = zoning.get("jurisdictionPrefix")
        ocpa_acres = _num(attrs.get("ACREAGE"))
        if ocpa_acres is not None and MIN_ACRES <= ocpa_acres <= MAX_ACRES:
            props["acreage"] = round(ocpa_acres, 4)
            props["acreageSource"] = "ocpa-acreage"
        if clean(attrs.get("NAME1")):
            props["ownerName"] = clean(attrs.get("NAME1"))
        props["ownerName2"] = clean(attrs.get("NAME2"))
        props["propertyName"] = clean(attrs.get("PROP_NAME"))
        if clean(attrs.get("SITUS")):
            props["situsAddress"] = clean(attrs.get("SITUS"))
        if clean(attrs.get("CITY_SITUS")):
            props["situsCity"] = clean(attrs.get("CITY_SITUS"))
        if zip_str(attrs.get("ZIP_SITUS")):
            props["situsZip"] = zip_str(attrs.get("ZIP_SITUS"))
        price = _num(attrs.get("SALE_ADJ_VALUE"))
        if price is not None and price <= 0:
            price = None
        sale_iso = epoch_to_iso(attrs.get("SALE_DATE"))
        if sale_iso or price is not None or clean(attrs.get("QUAL_CODE")):
            props["lastSale"] = {
                "date": sale_iso or props["lastSale"]["date"],
                "price": price if price is not None else props["lastSale"]["price"],
                "qualified": clean(attrs.get("QUAL_CODE")) or props["lastSale"]["qualified"],
            }
        props["tax"] = {
            "marketValue": _num(attrs.get("TOTAL_MKT")),
            "assessedValue": _num(attrs.get("TOTAL_ASSD")),
            "taxableValue": _num(attrs.get("TAXABLE")),
            "taxes": _num(attrs.get("TAXES")),
        }
        if clean(attrs.get("ADD1")):
            props["mailingAddress"] = {
                "line1": clean(attrs.get("ADD1")),
                "line2": clean(attrs.get("ADD2")),
                "city": clean(attrs.get("CITY")),
                "state": clean(attrs.get("STATE")),
                "zip": zip_str(attrs.get("ZIP")),
            }
        if clean(attrs.get("DOR_CODE")):
            props["dorCode"] = clean(attrs.get("DOR_CODE"))
        props["source"] = "fl-doh-ehwaters-12095+ocpa"
        props["appraiserUrl"] = "https://ocpaweb.ocpafl.org/site/parcelsearch"
    print(f"  OCPA matched {matched}/{len(features)}")
    return matched


def download_flu_layer(url: str, out_fields: str, label_fn) -> GridIndex:
    print(f"  FLU {url.split('/MapServer/')[-1]}")
    expected = count_where(url, "1=1")
    ids = fetch_object_ids(url, "1=1")
    raw = fetch_by_object_ids(
        url,
        ids,
        {
            "where": "1=1",
            "outFields": out_fields,
            "returnGeometry": "true",
            "outSR": 4326,
            "maxAllowableOffset": 0.0002,
            "geometryPrecision": 5,
        },
        batch=120,
    )
    index = GridIndex(0.04)
    kept = 0
    for item in raw:
        geometry = rings_to_geojson(item.get("geometry") or {})
        if not geometry:
            continue
        payload = label_fn(item.get("attributes") or {})
        if not payload:
            continue
        index.add({"type": "Feature", "geometry": geometry, "properties": payload})
        kept += 1
    print(f"    indexed {kept} / source {expected}")
    return index


def oc_flu(attrs: dict) -> dict | None:
    code = clean(attrs.get("LAND_USE"))
    if not code:
        return None
    label = clean(attrs.get("LABEL")) or OC_LABELS.get(code) or code
    return {"code": code, "label": label, "jurisdiction": "ORG", "source": "ocfl-agol-21"}


def orl_flu(attrs: dict) -> dict | None:
    code = clean(attrs.get("LANDUSETYPE"))
    if not code:
        return None
    return {"code": code, "label": ORL_LABELS.get(code, code), "jurisdiction": "ORL", "source": "ocfl-agol-83"}


def join_orange_flu(features: list[dict]) -> tuple[int, dict[str, int]]:
    county_index = download_flu_layer(OC_FLU_URL, "LAND_USE,LABEL", oc_flu)
    city_index = download_flu_layer(ORL_FLU_URL, "LANDUSETYPE", orl_flu)
    joined = 0
    gaps: dict[str, int] = {}
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        prefix = (props.get("jurisdictionPrefix") or "").upper()
        city = city_index.hit(lon, lat) if prefix == "ORL" else None
        county = county_index.hit(lon, lat)
        county_props = (county or {}).get("properties")
        city_props = (city or {}).get("properties")
        if prefix == "ORL" and not city_props:
            city = city_index.hit(lon, lat)
            city_props = (city or {}).get("properties")
        if city_props:
            props["flu"] = city_props
            joined += 1
            continue
        if county_props and county_props.get("code") not in {None, "City"}:
            props["flu"] = county_props
            joined += 1
            continue
        if county_props:
            gaps["county-city-placeholder"] = gaps.get("county-city-placeholder", 0) + 1
            # City placeholder means a municipality. Try Orlando layer once more for unlabeled cities.
            if not city_props:
                city = city_index.hit(lon, lat)
                city_props = (city or {}).get("properties")
            if city_props:
                props["flu"] = city_props
                joined += 1
            continue
        gaps["no-hit"] = gaps.get("no-hit", 0) + 1
    print(f"  FLU joined {joined}/{len(features)} gaps {gaps}")
    return joined, gaps


def stamp_overlays(features: list[dict], county_name: str) -> tuple[int, int]:
    rural_index = GridIndex(0.06)
    for feature in load_geojson_features(RURAL_GEOJSON):
        props = feature.get("properties") or {}
        if "Orlando" in (props.get("markets") or []) and props.get("county") == county_name:
            rural_index.add(feature)

    oz2_index = GridIndex(0.08)
    if county_name == "Orange":
        for feature in load_geojson_features(OZ2_POLYS):
            oz2_index.add(feature)
    oz_index = GridIndex(0.08)
    if county_name == "Orange":
        for feature in load_geojson_features(OZ_POLYS):
            oz_index.add(feature)

    rural_n = 0
    eligible_n = 0
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        if county_name == "Orange":
            hit = oz2_index.hit(lon, lat)
            if hit:
                hp = hit["properties"]
                props["oz2Eligibility"] = {
                    "eligible": True,
                    "rural": bool(hp.get("rural")),
                    "tractGeoid": hp.get("tractGeoid"),
                    "tractName": hp.get("name"),
                    "designation": "eligible-for-nomination",
                    "source": "rev-proc-2026-14",
                }
            else:
                props["oz2Eligibility"] = {
                    "eligible": False,
                    "rural": None,
                    "tractGeoid": None,
                    "tractName": None,
                    "designation": "not-eligible",
                    "source": "rev-proc-2026-14",
                }
            zone = oz_index.hit(lon, lat)
            if zone:
                zp = zone["properties"]
                props["opportunityZone"] = {
                    "inOpportunityZone": True,
                    "tractGeoid": zp.get("tractGeoid"),
                    "tractName": zp.get("name"),
                    "source": "hud-fs-13",
                    "designatedRural": zp.get("rural"),
                }
            else:
                props["opportunityZone"] = {
                    "inOpportunityZone": False,
                    "tractGeoid": None,
                    "tractName": None,
                    "source": "hud-fs-13",
                    "designatedRural": None,
                }
        else:
            hit = rural_index.hit(lon, lat)
            if hit:
                hp = hit["properties"]
                props["oz2Eligibility"] = {
                    "eligible": True,
                    "rural": True,
                    "tractGeoid": hp.get("tractGeoid"),
                    "tractName": hp.get("name"),
                    "designation": "eligible-for-nomination",
                    "source": "rev-proc-2026-14",
                }
            else:
                props["oz2Eligibility"] = {
                    "eligible": False,
                    "rural": None,
                    "tractGeoid": None,
                    "tractName": None,
                    "designation": "not-eligible",
                    "source": "rev-proc-2026-14",
                }
        oz2 = props.get("oz2Eligibility") or {}
        if oz2.get("eligible"):
            eligible_n += 1
        if oz2.get("rural"):
            rural_n += 1
    return rural_n, eligible_n


def tile_key(lon: float, lat: float) -> tuple[int, int]:
    ix = math.floor((lon - ORIGIN_LON) / TILE_DEG)
    iy = math.floor((lat - ORIGIN_LAT) / TILE_DEG)
    return ix, iy


def write_tiles(county: dict, features: list[dict]) -> tuple[str, int, dict[str, str]]:
    fips = county["fips"]
    folder = TILE_DIR / fips
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)
    legacy = OUT_DIR / f"{fips}.geojson"
    if legacy.exists():
        legacy.unlink()
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
                {
                    "type": "FeatureCollection",
                    "name": f"orlando-{fips}-{ix}_{iy}",
                    "features": group,
                },
                separators=(",", ":"),
            )
        )
    LOOKUP_DIR.mkdir(parents=True, exist_ok=True)
    (LOOKUP_DIR / f"{fips}.json").write_text(json.dumps(lookup, separators=(",", ":")))
    rel = str(folder.relative_to(ROOT))
    return rel, len(grouped), lookup


def query_window(layer_id: int, bbox: tuple[float, float, float, float], min_sqft: float, page_size: int, max_records: int) -> list[dict]:
    url = f"{DOH_BASE}/{layer_id}/query"
    west, south, east, north = bbox
    features: list[dict] = []
    offset = 0
    while len(features) < max_records:
        params = {
            "where": f"LND_SQFOOT > {int(min_sqft)}",
            "geometry": json.dumps(
                {"xmin": west, "ymin": south, "xmax": east, "ymax": north, "spatialReference": {"wkid": 4326}}
            ),
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": ",".join(DOH_FIELDS),
            "returnGeometry": "true",
            "outSR": 4326,
            "resultOffset": offset,
            "resultRecordCount": min(page_size, max_records - len(features)),
            "f": "json",
        }
        data = fetch_json(url, params)
        if data.get("error"):
            raise RuntimeError(data["error"])
        batch = data.get("features") or []
        features.extend(batch)
        if not data.get("exceededTransferLimit") and len(batch) < params["resultRecordCount"]:
            break
        if not batch:
            break
        offset += len(batch)
        time.sleep(0.12)
    return features


def seed_sample_county(county: dict, windows: list[tuple[float, float, float, float]], per_county: int, min_acres: float) -> list[dict]:
    min_sqft = min_acres * 43560.0
    by_id: dict[str, dict] = {}
    per_window = max(40, per_county // max(1, len(windows)))
    for bbox in windows:
        raw = query_window(county["dohLayerId"], bbox, min_sqft, page_size=100, max_records=per_window)
        for item in raw:
            # Sample path may include parcels under 5 acres. Bypass the core acreage gate.
            attrs = item.get("attributes") or {}
            geom = item.get("geometry") or {}
            sqft = _num(attrs.get("LND_SQFOOT")) or 0
            feature = normalize_doh({**attrs, "LND_SQFOOT": max(sqft, MIN_SQFT)}, geom, county)
            if not feature:
                continue
            if sqft > 0:
                feature["properties"]["acreage"] = round(sqft / 43560.0, 4)
                feature["properties"]["acreageSource"] = "fdor-lnd-sqfoot"
            by_id[feature["properties"]["id"]] = feature
            if len(by_id) >= per_county:
                break
        if len(by_id) >= per_county:
            break
        time.sleep(0.15)
    features = list(by_id.values())
    features.sort(key=lambda f: f["properties"].get("acreage") or 0, reverse=True)
    return features[:per_county]


def write_sample_file(county: dict, features: list[dict]) -> str:
    path = OUT_DIR / f"{county['fips']}.geojson"
    path.write_text(
        json.dumps(
            {"type": "FeatureCollection", "name": f"orlando-shed-{county['name'].lower()}", "features": features},
            separators=(",", ":"),
        )
    )
    return str(path.relative_to(ROOT))


def county_meta_row(
    county: dict,
    features: list[dict],
    *,
    coverage: str,
    partition: str,
    path: str,
    min_acres: float,
    extra: dict | None = None,
) -> dict:
    rural_n = sum(1 for f in features if (f["properties"].get("oz2Eligibility") or {}).get("rural"))
    eligible_n = sum(1 for f in features if (f["properties"].get("oz2Eligibility") or {}).get("eligible"))
    zoning_n = sum(1 for f in features if f["properties"].get("zoningCode"))
    flu_n = sum(1 for f in features if (f["properties"].get("flu") or {}).get("code"))
    row = {
        "name": county["name"],
        "fips": county["fips"],
        "featureCount": len(features),
        "ruralEligibleParcelCount": rural_n,
        "oz2EligibleParcelCount": eligible_n,
        "zoningJoinedCount": zoning_n,
        "fluJoinedCount": flu_n,
        "coverage": coverage,
        "partition": partition,
        "minAcres": min_acres,
        "source": county["preferredSource"],
        "queryUrl": county["queryUrl"],
        "gaps": county.get("gaps") or [],
        "path": path,
    }
    if extra:
        row.update(extra)
    return row


def load_existing_meta() -> dict[str, dict]:
    if not META_OUT.exists():
        return {}
    data = json.loads(META_OUT.read_text())
    return {county["fips"]: county for county in data.get("counties") or []}


def preserve_sample_row(county: dict, existing: dict | None) -> dict | None:
    path = OUT_DIR / f"{county['fips']}.geojson"
    if existing and existing.get("partition") != "tiles" and path.exists():
        row = dict(existing)
        row["coverage"] = "sample"
        row["partition"] = "file"
        row["minAcres"] = existing.get("minAcres") or 1.0
        row["path"] = str(path.relative_to(ROOT))
        row.setdefault("gaps", county.get("gaps") or [])
        row.setdefault("source", county["preferredSource"])
        row.setdefault("queryUrl", county["queryUrl"])
        return row
    if path.exists():
        collection = json.loads(path.read_text())
        features = collection.get("features") or []
        return county_meta_row(
            county,
            features,
            coverage="sample",
            partition="file",
            path=str(path.relative_to(ROOT)),
            min_acres=1.0,
        )
    return None


def in_core_acreage_band(acres: Any) -> bool:
    value = _num(acres)
    if value is None:
        return False
    return MIN_ACRES <= value <= MAX_ACRES


def normalize_ocpa_shape(attrs: dict, geom: dict) -> dict | None:
    geometry = rings_to_geojson(geom)
    if not geometry:
        return None
    center = centroid(geometry)
    if not center or not (-88 < center[0] < -79 and 24 < center[1] < 31.5):
        return None
    parcel_id = clean(attrs.get("PARCEL"))
    if not parcel_id:
        return None
    acres = _num(attrs.get("ACREAGE"))
    if acres is None:
        return None
    zoning = parse_zoning(clean(attrs.get("ZONING_CODE")))
    price = _num(attrs.get("SALE_ADJ_VALUE"))
    if price is not None and price <= 0:
        price = None
    feature_id = f"12095:{parcel_id}"
    return {
        "type": "Feature",
        "id": feature_id,
        "properties": {
            "id": feature_id,
            "parcelId": parcel_id,
            "countyFips": "12095",
            "countyName": "Orange",
            "state": "Florida",
            "marketIds": ["Orlando"],
            "situsAddress": clean(attrs.get("SITUS")),
            "situsCity": clean(attrs.get("CITY_SITUS")),
            "situsZip": zip_str(attrs.get("ZIP_SITUS")),
            "jurisdictionCode": zoning.get("jurisdictionPrefix"),
            "ownerName": clean(attrs.get("NAME1")),
            "ownerName2": clean(attrs.get("NAME2")),
            "propertyName": clean(attrs.get("PROP_NAME")),
            "zoningCode": zoning.get("zoningCode"),
            "zoningDistrict": zoning.get("zoningDistrict"),
            "jurisdictionPrefix": zoning.get("jurisdictionPrefix"),
            "dorCode": clean(attrs.get("DOR_CODE")),
            "acreage": round(acres, 4),
            "acreageSource": "ocpa-acreage",
            "centroid": list(center),
            "lastSale": {
                "date": epoch_to_iso(attrs.get("SALE_DATE")),
                "price": price,
                "qualified": clean(attrs.get("QUAL_CODE")),
            },
            "tax": {
                "marketValue": _num(attrs.get("TOTAL_MKT")),
                "assessedValue": _num(attrs.get("TOTAL_ASSD")),
                "taxableValue": _num(attrs.get("TAXABLE")),
                "taxes": _num(attrs.get("TAXES")),
            },
            "mailingAddress": {
                "line1": clean(attrs.get("ADD1")),
                "line2": clean(attrs.get("ADD2")),
                "city": clean(attrs.get("CITY")),
                "state": clean(attrs.get("STATE")),
                "zip": zip_str(attrs.get("ZIP")),
            },
            "incomeTract": None,
            "incomeBlockGroup": None,
            "nearestRoad": None,
            "flu": None,
            "opportunityZone": None,
            "oz2Eligibility": None,
            "appraiserUrl": "https://ocpaweb.ocpafl.org/site/parcelsearch",
            "source": "ocpa-webmap-12095",
            "dataGaps": [
                "Income and AADT are joined at query time from ACS and FDOT, not stored on the tile.",
                "Future land use is Orange County and Orlando only. Other cities often stay unknown.",
            ],
        },
        "geometry": geometry,
    }


def combine_ocpa_parts(parts: list[dict]) -> dict:
    host = max(parts, key=lambda feature: feature["properties"].get("acreage") or 0)
    acres = [feature["properties"]["acreage"] for feature in parts if feature["properties"].get("acreage") is not None]
    if acres and max(acres) - min(acres) <= 0.05:
        acreage = round(max(acres), 4)
        host["properties"]["acreageSource"] = "ocpa-acreage"
    else:
        acreage = round(sum(acres), 4)
        host["properties"]["acreageSource"] = "ocpa-part-sum"
    polygons: list = []
    for feature in parts:
        polygons.extend(polygon_parts(feature["geometry"]))
    geometry = {"type": "Polygon", "coordinates": polygons[0]} if len(polygons) == 1 else {
        "type": "MultiPolygon",
        "coordinates": polygons,
    }
    center = centroid(geometry)
    host = {
        **host,
        "geometry": geometry,
        "properties": {**host["properties"], "acreage": acreage},
    }
    if center:
        host["properties"]["centroid"] = list(center)
    return host


def download_orange_ocpa(county: dict) -> tuple[list[dict], int, int, int]:
    """Cadastral geometry and tax attributes from the public OCPA parcel layer.

    DOH statewide polygons are a thinner copy and were over-simplified. OCPA is
    the county cadastre. Shapes that share a parcel id are one tax account.
    """
    where = f"ACREAGE >= {MIN_ACRES} AND ACREAGE <= {MAX_ACRES}"
    expected = count_where(OCPA_QUERY, where)
    cache_path = CACHE_DIR / "orange-ocpa-geom2.json"
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        if cached.get("geometryVersion") == 2 and cached.get("sourceCount") == expected and cached.get("features"):
            print(f"  OCPA cache hit ({len(cached['features'])} parcels, source shapes {expected})")
            return (
                cached["features"],
                expected,
                int(cached.get("dropped") or 0),
                int(cached.get("merged") or 0),
            )

    print(f"  OCPA shapes in the {MIN_ACRES}–{MAX_ACRES} acre band: {expected}")
    ids = fetch_object_ids(OCPA_QUERY, where)
    raw = fetch_by_object_ids(
        OCPA_QUERY,
        ids,
        {"outFields": ",".join(OCPA_FIELDS), "returnGeometry": "true", "outSR": 4326},
        batch=60,
    )
    parcel_ids = []
    seen_ids: set[str] = set()
    for item in raw:
        pid = clean((item.get("attributes") or {}).get("PARCEL"))
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            parcel_ids.append(pid)
    print(f"  fetching every shape for {len(parcel_ids)} parcel ids")
    by_parcel_raw: dict[str, list[dict]] = defaultdict(list)
    for start in range(0, len(parcel_ids), 40):
        chunk = parcel_ids[start : start + 40]
        clause = "PARCEL IN (" + ",".join("'" + pid.replace("'", "''") + "'" for pid in chunk) + ")"
        data = fetch_json(
            OCPA_QUERY,
            {
                "where": clause,
                "outFields": ",".join(OCPA_FIELDS),
                "returnGeometry": "true",
                "outSR": 4326,
                "f": "json",
            },
            timeout=120,
        )
        if data.get("error"):
            raise RuntimeError(data["error"])
        for item in data.get("features") or []:
            pid = clean((item.get("attributes") or {}).get("PARCEL"))
            if pid:
                by_parcel_raw[pid].append(item)
        if start == 0 or start + 40 >= len(parcel_ids) or (start // 40) % 25 == 0:
            print(f"    parcel batches {min(start + 40, len(parcel_ids))}/{len(parcel_ids)}")
        time.sleep(0.05)

    features: list[dict] = []
    dropped = 0
    merged = 0
    for pid, items in by_parcel_raw.items():
        parts: list[dict] = []
        for item in items:
            feature = normalize_ocpa_shape(item.get("attributes") or {}, item.get("geometry") or {})
            if feature:
                parts.append(feature)
            else:
                dropped += 1
        if not parts:
            continue
        if len(parts) > 1:
            merged += len(parts) - 1
        features.append(combine_ocpa_parts(parts) if len(parts) > 1 else parts[0])
    if len(features) < max(1, int(len(parcel_ids) * 0.9)):
        raise RuntimeError(
            f"Orange OCPA kept {len(features)} of {len(parcel_ids)} parcel ids. Refusing a thin extract."
        )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "geometryVersion": 2,
                "sourceCount": expected,
                "dropped": dropped,
                "merged": merged,
                "features": features,
            }
        )
    )
    print(f"  OCPA normalized {len(features)} parcels (dropped shapes {dropped}, merged parts {merged})")
    return features, expected, dropped, merged


def seed_one_core(county: dict, skip_flu: bool) -> dict:
    print(f"Seeding complete 5–150 ac {county['name']}…")
    ocpa_matched = 0
    flu_gaps: dict[str, int] = {}
    if county["name"] == "Orange":
        features, source_count, dropped, merged_parts = download_orange_ocpa(county)
        ocpa_matched = len(features)
        if not skip_flu:
            _joined, flu_gaps = join_orange_flu(features)
        county = {
            **county,
            "preferredSource": "ocpa-webmap",
            "gaps": [
                "Acreage band is 5.0–150.0 acres on the public OCPA parcel layer. Multipart tax accounts sum their piece acres and drop out above 150.",
                "Geometry, owner, mailing, sale, tax, and zoning come from OCPA. Parcels that exist only on the older DOH extract are not drawn.",
                "FLU is centroid-joined to Orange County open-data layer 21 and Orlando layer 83. Other cities often stay unknown.",
                "Median household income and FDOT AADT are not copied onto each tile. /api/parcels joins them at query time.",
            ],
        }
    else:
        features, source_count, dropped, merged_parts = download_core_county(county)
        county = {
            **county,
            "gaps": [
                "Acreage band is 5.0–150.0 acres (FDOR LND_SQFOOT / 43560). Parcels under 5 or over 150 are excluded.",
                "No zoning or future land use on the Florida DOH EHWATER extract. Owner, sale, and tax are the public FDOR fields when that roll has them.",
                "OZ 2.0 here is the seven-market rural-eligible tract pack only, not every eligible tract in the county.",
                "Median household income and FDOT AADT are joined at query time for Florida counties, not stored on each tile.",
            ],
        }
    before_cap = len(features)
    features = [feature for feature in features if in_core_acreage_band(feature["properties"].get("acreage"))]
    excluded_over_max = before_cap - len(features)
    if excluded_over_max:
        print(f"  dropped {excluded_over_max} parcels outside {MIN_ACRES}–{MAX_ACRES} acres")
    rural_n, eligible_n = stamp_overlays(features, county["name"])
    gaps = list(county.get("gaps") or [])
    for feature in features:
        feature["properties"]["dataGaps"] = gaps
    rel, tile_count, _lookup = write_tiles(county, features)
    print(f"  wrote {len(features)} features in {tile_count} tiles ({rural_n} rural-eligible)")
    return county_meta_row(
        county,
        features,
        coverage="complete-gte-5ac",
        partition="tiles",
        path=rel,
        min_acres=MIN_ACRES,
        extra={
            "maxAcres": MAX_ACRES,
            "sourceCount": source_count,
            "excludedOverMaxAcres": excluded_over_max,
            "droppedNoGeometry": dropped,
            "mergedParts": merged_parts,
            "tileCount": tile_count,
            "ocpaMatchedCount": ocpa_matched,
            "fluGaps": flu_gaps,
            "ruralEligibleParcelCount": rural_n,
            "oz2EligibleParcelCount": eligible_n,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-county", type=int, default=120, help="Sample cap for non-core counties")
    parser.add_argument("--min-acres", type=float, default=1.0, help="Sample-mode minimum acreage")
    parser.add_argument("--county", type=str, default="")
    parser.add_argument("--full-core", action="store_true", help="Download every 5–150 acre parcel in the five core counties")
    parser.add_argument("--sample", action="store_true", help="Refresh windowed samples instead of the full core extract")
    parser.add_argument("--refresh-samples", action="store_true", help="Also re-download Brevard/Marion/Sumter/Volusia samples")
    parser.add_argument("--skip-flu", action="store_true")
    args = parser.parse_args()
    full_core = args.full_core or not args.sample

    sources = json.loads(SOURCES.read_text())
    windows = load_orlando_rural_windows()
    existing = load_existing_meta()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for county in sources["counties"]:
        if args.county and county["name"].lower() != args.county.lower():
            preserved = preserve_sample_row(county, existing.get(county["fips"]))
            if county["name"] in CORE_COUNTIES and existing.get(county["fips"], {}).get("coverage") == "complete-gte-5ac":
                rows.append(existing[county["fips"]])
                continue
            if preserved:
                rows.append(preserved)
            continue

        is_core = county["name"] in CORE_COUNTIES
        if full_core and is_core:
            rows.append(seed_one_core(county, skip_flu=args.skip_flu))
            continue

        if not args.refresh_samples and not args.sample and preserve_sample_row(county, existing.get(county["fips"])):
            print(f"Keeping existing sample for {county['name']}")
            rows.append(preserve_sample_row(county, existing.get(county["fips"])))
            continue

        county_windows = windows.get(county["name"]) or []
        if not county_windows:
            print(f"skip {county['name']}: no windows")
            preserved = preserve_sample_row(county, existing.get(county["fips"]))
            if preserved:
                rows.append(preserved)
            continue
        print(f"Seeding sample {county['name']} ({len(county_windows)} windows)…")
        features = seed_sample_county(county, county_windows, args.per_county, args.min_acres)
        rural_n, eligible_n = stamp_overlays(features, county["name"])
        rel = write_sample_file(county, features)
        row = county_meta_row(
            county,
            features,
            coverage="sample",
            partition="file",
            path=rel,
            min_acres=args.min_acres,
            extra={"ruralEligibleParcelCount": rural_n, "oz2EligibleParcelCount": eligible_n},
        )
        rows.append(row)
        print(f"  wrote {len(features)} sample features")

    rows.sort(key=lambda row: row["name"])
    total = sum(row["featureCount"] for row in rows)
    meta = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "market": "Orlando",
        "parcelCount": total,
        "perCountyCap": None if full_core else args.per_county,
        "minAcres": None,
        "coreMinAcres": MIN_ACRES,
        "coreMaxAcres": MAX_ACRES,
        "tile": {"originLon": ORIGIN_LON, "originLat": ORIGIN_LAT, "tileDeg": TILE_DEG},
        "sourcesDoc": "data/orlando-parcel-sources.json",
        "notes": [
            "Lake, Osceola, Polk, and Seminole are complete DOH extracts of parcels from 5.0 through 150.0 acres (LND_SQFOOT / 43560). Orange is the OCPA cadastre in that same acreage band.",
            "Brevard, Marion, Sumter, and Volusia remain thinner viewport samples in this build.",
            "Core counties are partitioned into 0.25° tiles. The map loads a viewport through /api/parcels.",
            "Orange geometry, owner, mailing, sale, tax, and zoning come from OCPA. FLU is Orange County + Orlando only.",
            "Median household income and FDOT AADT are joined at query time from sidecar fixtures, not stored on tiles.",
            "Re-pull with npm run seed:parcels:orlando.",
        ],
        "counties": rows,
    }
    META_OUT.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Done. {total} parcels across {len(rows)} counties → {OUT_DIR}")
    for row in rows:
        print(
            f"  {row['name']}: {row['featureCount']} {row['coverage']} "
            f"zoning {row.get('zoningJoinedCount', 0)} flu {row.get('fluJoinedCount', 0)}"
        )


if __name__ == "__main__":
    main()
