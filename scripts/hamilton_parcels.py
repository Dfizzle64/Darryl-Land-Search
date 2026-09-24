#!/usr/bin/env python3
"""Hamilton County, Tennessee parcels from public county GIS (not IMPACT).

Live_Parcels MapServer layer 0 is the parcel contract. Zoning is not on that
layer; it is joined from municipal, Chattanooga, RPA, and unincorporated
polygons. Plan Hamilton place types are the only public FLU-like layer.
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from parcel_geometry import esri_rings_to_geojson, polygon_parts, representative_point

REST = "https://mapsdev.hamiltontn.gov/hcwa03/rest/services"
PARCEL_QUERY = f"{REST}/Live_Parcels/MapServer/0/query"
SOURCE = "tn-hamilton-live-parcels"
MIN_ACRES = 5.0
MAX_ACRES = 150.0
WHERE = "CALCACRES >= 5 AND CALCACRES <= 150"

PLACEHOLDER_ZONES = {
    "COLLEGEDALE",
    "RED BANK",
    "SIGNAL MTN",
    "SIGNAL MOUNTAIN",
    "SODDY DAISY",
    "SODDY-DAISY",
    "N/A",
}

PLACE_LABELS = {
    "CA": "Campus",
    "CR": "Countryside Residential",
    "IN": "Industrial",
    "MD": "Maker District",
    "MR": "Mixed Residential",
    "NN": "Neighborhood Node",
    "PR": "Preserve",
    "RC": "Rural Commercial",
    "RR-A": "Resort Recreation",
    "RR-B": "Resort Recreation",
    "SR": "Suburban Residential",
    "UR": "Urban Residential",
    "VC": "Village Center",
    "XR": "Crossroads",
    "N/A": "McDonald Farm",
}

PARCEL_FIELDS = [
    "OBJECTID",
    "PBA_NUM",
    "GISLINK",
    "TAX_MAP_NO",
    "OWNERNAME1",
    "OWNERNAME2",
    "ADDRESS",
    "STNUM",
    "DIRPFX",
    "STNAME",
    "TYPESFX",
    "MASTNUM",
    "MADIRPFX",
    "MASTNAME",
    "MATYPESFX",
    "MALINE2",
    "MACITY",
    "MASTATE",
    "MAZIP",
    "CALCACRES",
    "LANDVALUE",
    "BUILDVALUE",
    "YardItemsV",
    "APPVALUE",
    "ASSVALUE",
    "SALE1DATE",
    "SALE1CONSD",
    "SALE1BOOK",
    "SALE1PAGE",
    "SALE2DATE",
    "SALE2CONSD",
    "SALE2BOOK",
    "SALE2PAGE",
    "SALE3DATE",
    "SALE3CONSD",
    "SALE3BOOK",
    "SALE3PAGE",
    "SALE4DATE",
    "SALE4CONSD",
    "SALE4BOOK",
    "SALE4PAGE",
    "LUCODE",
    "RecordsOnl",
]

# code field, optional alternate, jurisdiction, source label
ZONING_LAYERS = [
    ("redbank-rev", f"{REST}/Live_PropertyZoning/MapServer/2/query", "ZONE", "PropZon", "Red Bank", "Live_PropertyZoning/2 revised conditions"),
    ("redbank", f"{REST}/Live_PropertyZoning/MapServer/3/query", "ZONE", None, "Red Bank", "Live_PropertyZoning/3 Red Bank"),
    ("collegedale", f"{REST}/Live_PropertyZoning/MapServer/1/query", "Zone_Curre", None, "Collegedale", "Live_PropertyZoning/1 Collegedale"),
    ("soddy", f"{REST}/Live_PropertyZoning/MapServer/4/query", "ZONE", None, "Soddy Daisy", "Live_PropertyZoning/4 Soddy Daisy"),
    ("signal", f"{REST}/Live_PropertyZoning/MapServer/5/query", "ZONE", None, "Signal Mountain", "Live_PropertyZoning/5 Signal Mountain"),
    ("chattanooga", f"{REST}/Live_PropertyZoning/MapServer/14/query", "new_zone", "old_zone", "Chattanooga", "Live_PropertyZoning/14 Chattanooga"),
    ("chattanooga-pw", "https://pwgis.chattanooga.gov/arcgis/rest/services/Misc/Zoning/MapServer/0/query", "ZONE", None, "Chattanooga", "Chattanooga Public Works Misc/Zoning"),
    ("east-ridge", f"{REST}/OpenGov/Live_East_Ridge/MapServer/12/query", "ZONE", None, "East Ridge", "OpenGov/Live_East_Ridge/12"),
    ("temp-rpa", f"{REST}/TempZoningRPA/MapServer/3/query", "new_zone", "ZONE", "RPA", "TempZoningRPA/3"),
    ("rpa", f"{REST}/Live_PropertyZoning/MapServer/16/query", "ZONE", None, "RPA", "Live_PropertyZoning/16"),
    ("uninc", f"{REST}/PlanHamilton/MapServer/4/query", "ZONE", "new_zone", "Unincorporated Hamilton", "PlanHamilton/4 unincorporated zoning"),
]

MUNI_QUERY = f"{REST}/Live_Administrative/MapServer/2/query"
# Admin layer NAME values. Hamilton County is the county row, not a city.
CITY_ZONING_LAYER = {
    "East Ridge": "east-ridge",
    "Red Bank": "redbank",
    "Soddy Daisy": "soddy",
    "Signal Mountain": "signal",
    "Collegedale": "collegedale",
}
GAP_CITIES = {"Lookout Mountain", "Lakesite", "Walden", "Ridgeside"}
WIRED_CITIES = set(CITY_ZONING_LAYER) | {"Chattanooga"} | GAP_CITIES
PLACE_QUERY = f"{REST}/PlanHamilton/MapServer/3/query"
PLACE_SOURCE = f"{REST}/PlanHamilton/MapServer/3"
ASSESSOR_SEARCH = "https://assessor.hamiltontn.gov/search"

GAPS = [
    "Hamilton County is not an IMPACT county. Parcels are Hamilton County Live_Parcels MapServer layer 0 filtered on CALCACRES 5–150, not Comptroller IMPACT.",
    "Owner, mailing, situs, land/building/yard/appraised/assessed values, and four sale slots come from that parcel layer. RecordsOnl is the assessor card. A sale consideration of 0 is kept as no price.",
    "Municipality comes from Live_Administrative MapServer layer 2. Inside a city, that city's zoning layer wins over county RPA zoning.",
    "Chattanooga zoning is Live_PropertyZoning layer 14 (new_zone), then the city Public Works Misc/Zoning mirror. East Ridge zoning is OpenGov/Live_East_Ridge layer 12, not Live_PropertyZoning layers 1–5. Red Bank, Soddy Daisy, Signal Mountain, and Collegedale use Live_PropertyZoning layers 3, 4, 5, and 1. Red Bank revised conditions (layer 2) are supplemental.",
    "Lookout Mountain, Lakesite, Walden, and Ridgeside have no dedicated zoning REST layer. County RPA zoning is not used as their city code.",
    "Unincorporated zoning falls through TempZoningRPA layer 3, Live_PropertyZoning layer 16, then PlanHamilton unincorporated zoning. RPA labels such as Collegedale, Red Bank, and Signal Mtn are coverage placeholders, not city district codes.",
    "PlanHamilton PlaceTypesPlanHamilton layer 3 is policy guidance for unincorporated geography, not a zoning entitlement, and it is not applied inside city limits. City of Chattanooga Place Type (https://planchattanooga.org/draft/) was reconfirmed on 2026-09-23: pwgis.chattanooga.gov has no Place Type FeatureServer. East Ridge, Red Bank, Soddy Daisy, Signal Mountain, Collegedale, Lookout Mountain, Lakesite, Walden, and Ridgeside also have no public Place Type layer.",
    "County GIS polygons are representational, not survey-grade. The next countywide reappraisal is January 1, 2029.",
]


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/hamilton-parcels"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:180]}: {last}")


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


def zone_code(*values: Any) -> str | None:
    for value in values:
        text = clean(value)
        if not text:
            continue
        if text.upper() in PLACEHOLDER_ZONES:
            continue
        return text
    return None


def epoch_date(value: Any) -> str | None:
    parsed = num(value)
    if parsed is None or parsed == 0:
        return None
    seconds = parsed / 1000.0 if abs(parsed) > 10_000_000_000 else parsed
    try:
        stamp = datetime.fromtimestamp(seconds, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    if stamp.year < 1800 or stamp.year > 2100:
        return None
    return stamp.date().isoformat()


def join_parts(*values: Any) -> str | None:
    bits: list[str] = []
    for value in values:
        text = clean(value)
        if text and text != "0":
            bits.append(text)
    return " ".join(bits) or None


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


def _point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_geometry(lon: float, lat: float, geometry: dict) -> bool:
    for poly in polygon_parts(geometry):
        if not poly or not _point_in_ring(lon, lat, poly[0]):
            continue
        if any(_point_in_ring(lon, lat, hole) for hole in poly[1:]):
            continue
        return True
    return False


def geometry_bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for poly in polygon_parts(geometry):
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


class GridIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.items: list[dict] = []

    def add(self, geometry: dict, props: dict) -> None:
        bbox = geometry_bbox(geometry)
        if not bbox:
            return
        idx = len(self.items)
        self.items.append({"bbox": bbox, "geometry": geometry, "props": props})
        ix0 = math.floor(bbox[0] / self.cell)
        ix1 = math.floor(bbox[2] / self.cell)
        iy0 = math.floor(bbox[1] / self.cell)
        iy1 = math.floor(bbox[3] / self.cell)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(idx)

    def containing(self, lon: float, lat: float) -> list[dict]:
        ix = math.floor(lon / self.cell)
        iy = math.floor(lat / self.cell)
        hits: list[dict] = []
        seen: set[int] = set()
        for idx in self.buckets.get((ix, iy), []):
            if idx in seen:
                continue
            seen.add(idx)
            item = self.items[idx]
            west, south, east, north = item["bbox"]
            if not (west <= lon <= east and south <= lat <= north):
                continue
            if point_in_geometry(lon, lat, item["geometry"]):
                hits.append(item["props"])
        return hits


def fetch_pages(url: str, where: str, fields: list[str], page: int = 1000) -> list[dict]:
    offset = 0
    rows: list[dict] = []
    use_order = True
    while True:
        params: dict[str, str] = {
            "where": where,
            "outFields": ",".join(fields),
            "returnGeometry": "true",
            "outSR": "4326",
            "resultOffset": str(offset),
            "resultRecordCount": str(page),
            "f": "json",
        }
        if use_order:
            params["orderByFields"] = "OBJECTID"
        data = fetch_json(url, params)
        if data.get("error") and use_order and offset == 0:
            use_order = False
            continue
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        chunk = data.get("features") or []
        rows.extend(chunk)
        if len(chunk) < page and not data.get("exceededTransferLimit"):
            break
        if not chunk:
            break
        offset += len(chunk)
        print(f"    {url.split('/MapServer/')[-1]} offset {offset}", flush=True)
    return rows


def fetch_by_ids(url: str, ids: list[int], fields: list[str], batch: int = 80) -> list[dict]:
    rows: list[dict] = []
    total = len(ids)
    for start in range(0, total, batch):
        chunk = ids[start : start + batch]
        params = {
            "objectIds": ",".join(str(i) for i in chunk),
            "outFields": ",".join(fields),
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        }
        try:
            data = fetch_json(url, params)
        except RuntimeError:
            if len(chunk) > 40:
                rows.extend(fetch_by_ids(url, chunk, fields, batch=max(20, len(chunk) // 2)))
                continue
            raise
        if data.get("error"):
            if len(chunk) > 40:
                rows.extend(fetch_by_ids(url, chunk, fields, batch=max(20, len(chunk) // 2)))
                continue
            raise RuntimeError(json.dumps(data["error"])[:300])
        rows.extend(data.get("features") or [])
        done = min(start + len(chunk), total)
        if done == len(chunk) or done == total or done % 1000 < batch:
            print(f"    parcels {done}/{total}", flush=True)
    return rows


def build_index(features: list[dict], to_props) -> GridIndex:
    index = GridIndex()
    for feature in features:
        props = to_props(feature.get("attributes") or {})
        if not props or not props.get("code"):
            continue
        geometry = esri_rings_to_geojson((feature.get("geometry") or {}).get("rings") or [])
        if not geometry:
            continue
        bbox = geometry_bbox(geometry)
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) if bbox else 1e9
        props.setdefault("sort", props.get("acres") if props.get("acres") is not None else area)
        index.add(geometry, props)
    return index


def best_hit(hits: list[dict]) -> dict | None:
    coded = [hit for hit in hits if hit.get("code")]
    if not coded:
        return None
    return min(coded, key=lambda hit: hit.get("sort") if hit.get("sort") is not None else 1e18)


def sample_points(geometry: dict, center: tuple[float, float]) -> list[tuple[float, float]]:
    points = [center]
    for poly in polygon_parts(geometry):
        if not poly or not poly[0]:
            continue
        body = poly[0][:-1] if len(poly[0]) > 1 else poly[0]
        step = max(1, len(body) // 8)
        for point in body[::step][:8]:
            points.append((float(point[0]), float(point[1])))
        break
    return points


def hits_at(index: GridIndex, points: list[tuple[float, float]]) -> list[dict]:
    best: dict[str, dict] = {}
    for lon, lat in points:
        for hit in index.containing(lon, lat):
            key = str(hit.get("code"))
            previous = best.get(key)
            if previous is None or (hit.get("sort") or 1e18) < (previous.get("sort") or 1e18):
                best[key] = hit
    return list(best.values())


def sale_slot(attrs: dict, slot: int) -> dict | None:
    date = epoch_date(attrs.get(f"SALE{slot}DATE"))
    price = num(attrs.get(f"SALE{slot}CONSD"))
    if price is not None and price <= 0:
        price = None
    book = clean(attrs.get(f"SALE{slot}BOOK"))
    page = clean(attrs.get(f"SALE{slot}PAGE"))
    if date is None and price is None and not book and not page:
        return None
    return {"date": date, "price": price, "book": book, "page": page}


def load_zoning() -> dict[str, GridIndex]:
    indexes: dict[str, GridIndex] = {}
    for key, url, primary, alternate, jurisdiction, label in ZONING_LAYERS:
        fields = [primary] + ([alternate] if alternate else [])
        print(f"  zoning {label}", flush=True)
        rows = fetch_pages(url, "1=1", ["OBJECTID", *fields])

        def to_props(attrs: dict, primary=primary, alternate=alternate, jurisdiction=jurisdiction, label=label) -> dict | None:
            code = zone_code(attrs.get(primary), attrs.get(alternate) if alternate else None)
            if not code:
                return None
            return {"code": code, "jurisdiction": jurisdiction, "layer": label}

        indexes[key] = build_index(rows, to_props)
        print(f"    indexed {len(indexes[key].items)}", flush=True)
    return indexes


def load_place_types() -> GridIndex:
    print("  place types PlanHamilton/3", flush=True)
    rows = fetch_pages(PLACE_QUERY, "1=1", ["PlaceType", "Label", "Acres", "SubPlanArea"])

    def to_props(attrs: dict) -> dict | None:
        code = clean(attrs.get("PlaceType"))
        if not code:
            return None
        label = clean(attrs.get("Label")) or PLACE_LABELS.get(code) or code
        acres = num(attrs.get("Acres"))
        return {"code": code, "label": label, "acres": acres}

    index = build_index(rows, to_props)
    print(f"    indexed {len(index.items)}", flush=True)
    return index


def load_municipalities() -> GridIndex:
    print("  municipalities Live_Administrative/2", flush=True)
    rows = fetch_pages(MUNI_QUERY, "1=1", ["NAME"])

    def to_props(attrs: dict) -> dict | None:
        name = clean(attrs.get("NAME"))
        if not name:
            return None
        return {"code": name, "name": name}

    index = build_index(rows, to_props)
    print(f"    indexed {len(index.items)}", flush=True)
    return index


def city_at(munis: GridIndex, lon: float, lat: float) -> str | None:
    """Smallest incorporated polygon. The county row is not a city."""
    hits = [hit for hit in munis.containing(lon, lat) if (hit.get("name") or "").upper() != "HAMILTON COUNTY"]
    if not hits:
        return None
    return min(hits, key=lambda hit: hit.get("sort") if hit.get("sort") is not None else 1e18)["name"]


def layer_hit(indexes: dict[str, GridIndex], key: str, points: list[tuple[float, float]]) -> dict | None:
    found = best_hit(hits_at(indexes[key], points[:1]))
    if found:
        return found
    found = best_hit(hits_at(indexes[key], points[1:]))
    if not found:
        return None
    found = dict(found)
    found["layer"] = f"{found['layer']} (parcel overlap)"
    return found


def resolve_zoning(indexes: dict[str, GridIndex], city: str | None, points: list[tuple[float, float]]) -> dict | None:
    """City zoning wins inside city limits. County RPA is only the unincorporated fallback."""
    if city in GAP_CITIES:
        return {"code": None, "jurisdiction": city, "layer": None, "gapCity": True}
    if city == "Chattanooga":
        for key in ("chattanooga", "chattanooga-pw"):
            hit = layer_hit(indexes, key, points)
            if hit:
                hit = dict(hit)
                hit["jurisdiction"] = "Chattanooga"
                return hit
        for key in ("temp-rpa", "rpa"):
            hit = layer_hit(indexes, key, points)
            if hit:
                return {
                    "code": hit["code"],
                    "jurisdiction": "Chattanooga",
                    "layer": f"{hit['layer']} fallback; city zoning layer missed this point",
                }
        return {"code": None, "jurisdiction": "Chattanooga", "layer": None, "missed": True}
    if city == "Red Bank":
        base = layer_hit(indexes, "redbank", points)
        revised = layer_hit(indexes, "redbank-rev", points)
        if base:
            chosen = dict(base)
            chosen["jurisdiction"] = "Red Bank"
            if revised and revised.get("code") and revised["code"] != base.get("code"):
                chosen["revised"] = revised["code"]
            return chosen
        if revised:
            revised = dict(revised)
            revised["jurisdiction"] = "Red Bank"
            return revised
        return {"code": None, "jurisdiction": "Red Bank", "layer": None, "missed": True}
    if city in CITY_ZONING_LAYER:
        hit = layer_hit(indexes, CITY_ZONING_LAYER[city], points)
        if hit:
            hit = dict(hit)
            hit["jurisdiction"] = city
            return hit
        return {"code": None, "jurisdiction": city, "layer": None, "missed": True}
    for key in ("temp-rpa", "rpa", "uninc"):
        hit = layer_hit(indexes, key, points)
        if hit:
            hit = dict(hit)
            hit["jurisdiction"] = "Unincorporated Hamilton"
            return hit
    return None


def resolve_flu(index: GridIndex, points: list[tuple[float, float]]) -> dict | None:
    centroid_hits = hits_at(index, points[:1])
    other_hits = hits_at(index, points[1:])
    primary = best_hit(centroid_hits) or best_hit(other_hits)
    if not primary:
        return None
    codes = []
    for hit in centroid_hits + other_hits:
        if hit["code"] not in codes:
            codes.append(hit["code"])
    extras = [code for code in codes if code != primary["code"]][:4]
    label = primary.get("label") or PLACE_LABELS.get(primary["code"]) or primary["code"]
    if extras:
        extra_labels = [PLACE_LABELS.get(code, code) for code in extras]
        label = f"{label}; also {', '.join(extra_labels)}"
    return {
        "code": primary["code"],
        "label": label,
        "jurisdiction": "Plan Hamilton",
        "source": PLACE_SOURCE,
    }


def feature_gaps(city: str | None, zoning: dict | None, flu: dict | None) -> list[str]:
    gaps: list[str] = []
    if zoning and zoning.get("code"):
        gaps.append(f"Zoning joined from {zoning['jurisdiction']} ({zoning['layer']}).")
        if zoning.get("revised"):
            gaps.append(f"Red Bank revised-conditions layer also reports {zoning['revised']}. The base city district is shown.")
        if city in WIRED_CITIES:
            gaps.append(f"{zoning['jurisdiction']} city zoning is used inside the city limit. County RPA zoning is not this city's code.")
    elif city in GAP_CITIES:
        gaps.append(
            f"{city} has no dedicated zoning REST layer. County RPA zoning was not stored as the {city} city code."
        )
    elif city:
        gaps.append(f"Inside {city} limits, but the city zoning layer did not cover this parcel. County RPA zoning was not substituted.")
    else:
        gaps.append("No unincorporated RPA or Plan Hamilton zoning polygon covered this parcel.")
    if city == "Chattanooga":
        gaps.append(
            "City of Chattanooga Place Type draft (https://planchattanooga.org/draft/) has no confirmed public FeatureServer. Plan Hamilton place types are not applied inside the city."
        )
    elif city:
        gaps.append(f"{city} has no public Place Type / FLU layer. Plan Hamilton place types are not applied inside the city.")
    elif flu:
        gaps.append("Plan Hamilton place type is unincorporated policy guidance, not a zoning entitlement.")
    else:
        gaps.append("No Plan Hamilton place type intersects this unincorporated parcel.")
    return gaps


def normalize_parcel(
    item: dict,
    county: dict,
    markets: list[str],
    zoning_indexes: dict[str, GridIndex],
    places: GridIndex,
    munis: GridIndex,
) -> dict | None:
    attrs = item.get("attributes") or {}
    geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
    if not geometry:
        return None
    center = representative_point(geometry)
    if not center:
        return None
    lon, lat = center
    if not (-86.3 < lon < -84.6 and 34.7 < lat < 35.55):
        return None
    acres = num(attrs.get("CALCACRES"))
    if not in_band(acres):
        return None
    parcel_id = clean(attrs.get("TAX_MAP_NO")) or clean(attrs.get("GISLINK")) or clean(attrs.get("PBA_NUM"))
    if not parcel_id:
        oid = attrs.get("OBJECTID")
        parcel_id = clean(oid)
    if not parcel_id:
        return None
    points = sample_points(geometry, center)
    city = city_at(munis, center[0], center[1])
    zoning = resolve_zoning(zoning_indexes, city, points)
    flu = None if city else resolve_flu(places, points)
    zone_code_value = zoning.get("code") if zoning else None
    jurisdiction = (zoning.get("jurisdiction") if zoning else None) or city or "Unincorporated Hamilton"
    sale = sale_slot(attrs, 1) or {"date": None, "price": None, "book": None, "page": None}
    prior = [slot for slot in (sale_slot(attrs, n) for n in (2, 3, 4)) if slot]
    card = clean(attrs.get("RecordsOnl"))
    if card and not card.lower().startswith("http"):
        card = None
    feature_id = f"{county['fips']}:{parcel_id}"
    return {
        "type": "Feature",
        "id": feature_id,
        "properties": {
            "id": feature_id,
            "parcelId": parcel_id,
            "countyFips": county["fips"],
            "countyName": county["name"],
            "state": county["state"],
            "marketIds": markets,
            "situsAddress": clean(attrs.get("ADDRESS")) or join_parts(attrs.get("STNUM"), attrs.get("DIRPFX"), attrs.get("STNAME"), attrs.get("TYPESFX")),
            "situsCity": None,
            "situsZip": None,
            "jurisdictionCode": None,
            "ownerName": clean(attrs.get("OWNERNAME1")),
            "ownerName2": clean(attrs.get("OWNERNAME2")),
            "propertyName": None,
            "zoningCode": zone_code_value,
            "zoningDistrict": zone_code_value,
            "jurisdictionPrefix": jurisdiction,
            "dorCode": None,
            "acreage": round(acres, 4),
            "centroid": [center[0], center[1]],
            "lastSale": {
                "date": sale["date"],
                "price": sale["price"],
                "qualified": None,
                "book": sale["book"],
                "page": sale["page"],
            },
            "priorSales": prior,
            "tax": {
                "marketValue": num(attrs.get("APPVALUE")),
                "assessedValue": num(attrs.get("ASSVALUE")),
                "taxableValue": None,
                "taxes": None,
                "landValue": num(attrs.get("LANDVALUE")),
                "buildingValue": num(attrs.get("BUILDVALUE")),
                "yardItemsValue": num(attrs.get("YardItemsV")),
            },
            "mailingAddress": {
                "line1": join_parts(attrs.get("MASTNUM"), attrs.get("MADIRPFX"), attrs.get("MASTNAME"), attrs.get("MATYPESFX")),
                "line2": clean(attrs.get("MALINE2")),
                "city": clean(attrs.get("MACITY")),
                "state": clean(attrs.get("MASTATE")),
                "zip": zip_str(attrs.get("MAZIP")),
            },
            "incomeTract": None,
            "incomeBlockGroup": None,
            "nearestRoad": None,
            "flu": flu,
            "opportunityZone": None,
            "oz2Eligibility": None,
            "appraiserUrl": card or ASSESSOR_SEARCH,
            "gisLink": clean(attrs.get("GISLINK")),
            "pbaNum": clean(attrs.get("PBA_NUM")),
            "dataGaps": feature_gaps(city, zoning, flu),
            "source": SOURCE,
        },
        "geometry": geometry,
    }


def pull_hamilton(county: dict, markets: list[str]) -> dict:
    print(f"Hamilton Live_Parcels count check", flush=True)
    counted = fetch_json(PARCEL_QUERY, {"where": WHERE, "returnCountOnly": "true", "f": "json"})
    if counted.get("error"):
        raise RuntimeError(json.dumps(counted["error"])[:300])
    expected = int(counted.get("count") or 0)
    print(f"  source rows {expected}", flush=True)
    ids_payload = fetch_json(PARCEL_QUERY, {"where": WHERE, "returnIdsOnly": "true", "f": "json"})
    if ids_payload.get("error"):
        raise RuntimeError(json.dumps(ids_payload["error"])[:300])
    ids = [int(i) for i in (ids_payload.get("objectIds") or [])]
    raw = fetch_by_ids(PARCEL_QUERY, ids, PARCEL_FIELDS)
    munis = load_municipalities()
    zoning_indexes = load_zoning()
    places = load_place_types()
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        feature = normalize_parcel(item, county, markets, zoning_indexes, places, munis)
        if not feature:
            dropped += 1
            continue
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
        else:
            dropped += 1
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    zoned = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flued = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    by_city: dict[str, int] = defaultdict(int)
    for feature in features:
        name = feature["properties"].get("jurisdictionPrefix") or "Unincorporated Hamilton"
        by_city[name] += 1
    municipal = sum(by_city.get(name, 0) for name in sorted(WIRED_CITIES))
    gaps = list(GAPS)
    city_note = ", ".join(f"{name} {by_city.get(name, 0)}" for name in sorted(WIRED_CITIES | {"Unincorporated Hamilton"}))
    gaps.insert(
        0,
        f"Zoning joined on {zoned} of {len(features)} parcels. Plan Hamilton place type joined on {flued} unincorporated parcels. City counts: {city_note}.",
    )
    print(f"  kept {len(features)} zoned {zoned} flu {flued} dropped {dropped}", flush=True)
    return {
        "features": features,
        "sourceCount": expected,
        "dropped": dropped,
        "gaps": gaps,
        "source": SOURCE,
        "url": PARCEL_QUERY,
        "coverage": "complete-gte-5ac" if features else "gap",
    }
