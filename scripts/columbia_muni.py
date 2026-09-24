"""Municipal zoning and City of Columbia labels for the Columbia MSA parcel pull.

Public layers only. Richland County has no countywide parcel FeatureServer; this
module does not call richlandmaps.com PHP/TMS endpoints.
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any

LEX_PLAN = "https://maps.lex-co.com/agstserver/rest/services/PlanZoning/MapServer"
COLA_ZONING_URL = "https://gis.columbiasc.gov/cola/rest/services/InnercityMap/ZoningInfo/MapServer/7/query"
COLA_FLU_URL = "https://gis.columbiasc.gov/cola/rest/services/EnerGov/EnergovInformationPublic/MapServer/15/query"
LEX_APPRAISER = "https://maps.lex-co.com/OneMap/"
RICHLAND_APPRAISER = "https://property.spatialest.com/sc/richland#/"
COLA_FLU_SOURCE = "coc-energov-mapserver-15"

CITY_ONLY_GAP = (
    "City of Columbia only (CityLimit=Y). Not a Richland County-wide roll. "
    "Acreage is GIS area from Shape_Area. This city layer has no sale price or tax value."
)


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/columbia-muni"})
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


def tms_keys(value: Any) -> list[str]:
    text = clean(value)
    if not text:
        return []
    upper = text.upper()
    compact = "".join(ch for ch in upper if ch.isalnum())
    keys = [upper]
    if compact and compact not in keys:
        keys.append(compact)
    return keys


def point_in_ring(x: float, y: float, ring: list) -> bool:
    if len(ring) < 4:
        return False
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        if (yi > y) != (yj > y):
            denom = yj - yi
            if denom == 0:
                j = i
                continue
            x_cross = (xj - xi) * (y - yi) / denom + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_rings(x: float, y: float, rings: list) -> bool:
    """Even-odd across every ring so holes (and separate parts) stay correct."""
    hits = 0
    for ring in rings:
        if point_in_ring(x, y, ring):
            hits += 1
    return hits % 2 == 1


def ring_bbox(rings: list) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for ring in rings:
        for pt in ring:
            if len(pt) < 2:
                continue
            xs.append(float(pt[0]))
            ys.append(float(pt[1]))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def assert_wgs84(items: list[dict], label: str) -> None:
    if not items:
        return
    minx = min(item["bbox"][0] for item in items)
    maxx = max(item["bbox"][2] for item in items)
    miny = min(item["bbox"][1] for item in items)
    maxy = max(item["bbox"][3] for item in items)
    if minx < -90 or maxx > -70 or miny < 24 or maxy > 37:
        raise RuntimeError(f"{label} geometry is outside the Southeast WGS84 window ({minx},{miny},{maxx},{maxy})")


class PolyIndex:
    def __init__(self, items: list[dict], cell: float = 0.03) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        for item in items:
            minx, miny, maxx, maxy = item["bbox"]
            ix0, ix1 = math.floor(minx / cell), math.floor(maxx / cell)
            iy0, iy1 = math.floor(miny / cell), math.floor(maxy / cell)
            for ix in range(ix0, ix1 + 1):
                for iy in range(iy0, iy1 + 1):
                    self.buckets[(ix, iy)].append(item)

    def hit(self, lon: float, lat: float) -> dict | None:
        key = (math.floor(lon / self.cell), math.floor(lat / self.cell))
        for item in self.buckets.get(key, []):
            minx, miny, maxx, maxy = item["bbox"]
            if lon < minx or lon > maxx or lat < miny or lat > maxy:
                continue
            if point_in_rings(lon, lat, item["rings"]):
                return item
        return None


def fetch_ids(url: str, where: str) -> list[int]:
    data = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    return [int(i) for i in (data.get("objectIds") or [])]


def fetch_features(url: str, ids: list[int], out_fields: list[str], geometry: bool, batch: int = 100) -> list[dict]:
    features: list[dict] = []
    total = len(ids)
    for start in range(0, total, batch):
        chunk = ids[start : start + batch]
        params = {
            "objectIds": ",".join(str(i) for i in chunk),
            "outFields": ",".join(out_fields),
            "returnGeometry": "true" if geometry else "false",
            "f": "json",
        }
        if geometry:
            params["outSR"] = "4326"
        try:
            data = fetch_json(url, params, timeout=180)
        except RuntimeError:
            if len(chunk) > 25:
                features.extend(fetch_features(url, chunk, out_fields, geometry, batch=max(15, len(chunk) // 2)))
                continue
            raise
        if data.get("error"):
            if len(chunk) > 25:
                features.extend(fetch_features(url, chunk, out_fields, geometry, batch=max(15, len(chunk) // 2)))
                continue
            raise RuntimeError(json.dumps(data["error"])[:300])
        features.extend(data.get("features") or [])
        done = min(start + len(chunk), total)
        if done == len(chunk) or done == total or done % 500 == 0:
            print(f"    overlay {done}/{total} {url.rsplit('/', 2)[-2]}", flush=True)
    return features


def load_layer(url: str, where: str, out_fields: list[str], geometry: bool) -> list[dict]:
    ids = fetch_ids(url, where)
    if not ids:
        return []
    print(f"  overlay {len(ids)} from {url}", flush=True)
    return fetch_features(url, ids, out_fields, geometry)


def index_attributes(rows: list[dict], id_field: str, code_field: str, name_field: str | None, jurisdiction: str) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for item in rows:
        attrs = item.get("attributes") or {}
        code = clean(attrs.get(code_field))
        if not code:
            continue
        record = {
            "code": code,
            "description": clean(attrs.get(name_field)) if name_field else None,
            "jurisdiction": jurisdiction,
        }
        for key in tms_keys(attrs.get(id_field)):
            lookup.setdefault(key, record)
    return lookup


def polygons_from(rows: list[dict], code_field: str, name_field: str | None, jurisdiction_field: str | None, default_jurisdiction: str) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        attrs = row.get("attributes") or {}
        code = clean(attrs.get(code_field))
        rings = (row.get("geometry") or {}).get("rings") or []
        bbox = ring_bbox(rings)
        if not code or not bbox:
            continue
        jurisdiction = clean(attrs.get(jurisdiction_field)) if jurisdiction_field else None
        items.append(
            {
                "code": code,
                "description": clean(attrs.get(name_field)) if name_field else None,
                "jurisdiction": jurisdiction or default_jurisdiction,
                "rings": rings,
                "bbox": bbox,
            }
        )
    return items


def flu_polygons(rows: list[dict]) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        attrs = row.get("attributes") or {}
        code = clean(attrs.get("DevType"))
        rings = (row.get("geometry") or {}).get("rings") or []
        bbox = ring_bbox(rings)
        if not code or not bbox:
            continue
        items.append(
            {
                "code": code,
                "description": clean(attrs.get("Name")) or code,
                "jurisdiction": "City of Columbia",
                "rings": rings,
                "bbox": bbox,
            }
        )
    return items


def lookup_tms(table: dict[str, dict], parcel_id: str) -> dict | None:
    for key in tms_keys(parcel_id):
        hit = table.get(key)
        if hit:
            return hit
    return None


def apply_flu(features: list[dict], index: PolyIndex | None) -> int:
    if index is None:
        return 0
    joined = 0
    for feature in features:
        props = feature.get("properties") or {}
        center = props.get("centroid") or []
        if len(center) < 2:
            continue
        hit = index.hit(float(center[0]), float(center[1]))
        if not hit:
            continue
        props["flu"] = {
            "code": hit["code"],
            "label": hit["description"] or hit["code"],
            "jurisdiction": "City of Columbia",
            "source": COLA_FLU_SOURCE,
        }
        joined += 1
    return joined


def apply_lexington_zoning(
    features: list[dict],
    *,
    chapin: dict[str, dict],
    west: PolyIndex | None,
    cayce: PolyIndex | None,
    columbia: dict[str, dict],
    county: PolyIndex | None,
) -> dict[str, int]:
    counts = {
        "chapin": 0,
        "westColumbia": 0,
        "cayce": 0,
        "columbia": 0,
        "parcelAttribute": 0,
        "countyPlan": 0,
        "blank": 0,
    }
    for feature in features:
        props = feature["properties"]
        center = props.get("centroid") or [None, None]
        lon = float(center[0]) if center[0] is not None else None
        lat = float(center[1]) if center[1] is not None else None
        chosen = lookup_tms(chapin, props.get("parcelId") or "")
        source = "chapin" if chosen else None
        if chosen is None and west is not None and lon is not None and lat is not None:
            chosen = west.hit(lon, lat)
            source = "westColumbia" if chosen else None
        if chosen is None and cayce is not None and lon is not None and lat is not None:
            chosen = cayce.hit(lon, lat)
            source = "cayce" if chosen else None
        if chosen is None:
            chosen = lookup_tms(columbia, props.get("parcelId") or "")
            source = "columbia" if chosen else None
        if chosen is None and props.get("zoningCode"):
            counts["parcelAttribute"] += 1
            props["appraiserUrl"] = LEX_APPRAISER
            continue
        if chosen is None and county is not None and lon is not None and lat is not None:
            chosen = county.hit(lon, lat)
            source = "countyPlan" if chosen else None
        if chosen is None or source is None:
            counts["blank"] += 1
            props["appraiserUrl"] = LEX_APPRAISER
            continue
        props["zoningCode"] = chosen["code"]
        props["zoningDistrict"] = chosen.get("description")
        props["jurisdictionCode"] = chosen.get("jurisdiction")
        props["appraiserUrl"] = LEX_APPRAISER
        counts[source] += 1
    return counts


def apply_columbia_city_labels(features: list[dict]) -> None:
    for feature in features:
        props = feature["properties"]
        props["jurisdictionCode"] = "City of Columbia"
        props["appraiserUrl"] = RICHLAND_APPRAISER
        props["dataGaps"] = [CITY_ONLY_GAP]
        district = props.get("zoningDistrict")
        code = props.get("zoningCode")
        if district and code and district == code:
            props["zoningDistrict"] = None


def load_flu_index() -> tuple[PolyIndex | None, str | None]:
    try:
        rows = load_layer(COLA_FLU_URL, "1=1", ["DevType", "Name"], True)
        polys = flu_polygons(rows)
        assert_wgs84(polys, "City of Columbia FLU")
        return (PolyIndex(polys) if polys else None), None
    except Exception as exc:  # noqa: BLE001
        return None, f"City of Columbia FLU join failed: {exc}"


def enrich_lexington(features: list[dict]) -> list[str]:
    notes: list[str] = []
    chapin: dict[str, dict] = {}
    columbia: dict[str, dict] = {}
    west_index = None
    cayce_index = None
    county_index = None
    try:
        rows = load_layer(
            f"{LEX_PLAN}/15/query",
            "1=1",
            ["TMS", "ZoningCode", "ZoningName"],
            False,
        )
        chapin = index_attributes(rows, "TMS", "ZoningCode", "ZoningName", "Town of Chapin")
    except Exception as exc:  # noqa: BLE001
        notes.append(f"Chapin zoning join failed: {exc}")
    try:
        rows = load_layer(
            f"{LEX_PLAN}/8/query",
            "1=1",
            ["Zoning", "Description", "Jurisdiction"],
            True,
        )
        polys = polygons_from(rows, "Zoning", "Description", "Jurisdiction", "City of West Columbia")
        assert_wgs84(polys, "West Columbia zoning")
        west_index = PolyIndex(polys) if polys else None
    except Exception as exc:  # noqa: BLE001
        notes.append(f"West Columbia zoning join failed: {exc}")
    try:
        rows = load_layer(
            f"{LEX_PLAN}/12/query",
            "1=1",
            ["Zoning", "Description", "Jurisdiction"],
            True,
        )
        polys = polygons_from(rows, "Zoning", "Description", "Jurisdiction", "City of Cayce")
        assert_wgs84(polys, "Cayce zoning")
        cayce_index = PolyIndex(polys) if polys else None
    except Exception as exc:  # noqa: BLE001
        notes.append(f"Cayce zoning join failed: {exc}")
    try:
        rows = load_layer(
            COLA_ZONING_URL,
            "County='Lexington' AND CityLimit='Y'",
            ["TMS", "ZoningDistrict", "CityLimit", "County"],
            False,
        )
        columbia = index_attributes(rows, "TMS", "ZoningDistrict", None, "City of Columbia")
    except Exception as exc:  # noqa: BLE001
        notes.append(f"City of Columbia zoning join failed: {exc}")
    try:
        rows = load_layer(
            f"{LEX_PLAN}/6/query",
            "1=1",
            ["NameAbbr", "Name"],
            True,
        )
        polys = polygons_from(rows, "NameAbbr", "Name", None, "Lexington County")
        assert_wgs84(polys, "Lexington County zoning")
        county_index = PolyIndex(polys) if polys else None
    except Exception as exc:  # noqa: BLE001
        notes.append(f"Lexington County zoning join failed: {exc}")
    flu_index, flu_error = load_flu_index()
    if flu_error:
        notes.append(flu_error)
    counts = apply_lexington_zoning(
        features,
        chapin=chapin,
        west=west_index,
        cayce=cayce_index,
        columbia=columbia,
        county=county_index,
    )
    flu_n = apply_flu(features, flu_index)
    notes.append(
        "Zoning join counts — "
        f"Chapin {counts['chapin']}, West Columbia {counts['westColumbia']}, "
        f"Cayce {counts['cayce']}, City of Columbia {counts['columbia']}, "
        f"parcel attribute {counts['parcelAttribute']}, county PlanZoning {counts['countyPlan']}, "
        f"still blank {counts['blank']}. City of Columbia FLU centroids {flu_n}."
    )
    return notes


def enrich_columbia_city(features: list[dict]) -> list[str]:
    notes: list[str] = []
    apply_columbia_city_labels(features)
    flu_index, flu_error = load_flu_index()
    if flu_error:
        notes.append(flu_error)
    flu_n = apply_flu(features, flu_index)
    notes.append(f"City of Columbia FLU centroids {flu_n}. Zoning stays the parcel ZoningDistrict.")
    return notes


def enrich_market_parcels(kind: str, features: list[dict]) -> list[str]:
    if kind == "lexington":
        return enrich_lexington(features)
    if kind == "columbia-city":
        return enrich_columbia_city(features)
    return [f"Unknown municipal enrich kind: {kind}"]


def _self_test() -> None:
    square = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]
    hole = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8], [0.2, 0.2]]
    assert point_in_ring(0.5, 0.5, square)
    assert not point_in_ring(2.0, 2.0, square)
    assert point_in_rings(0.1, 0.1, [square, hole])
    assert not point_in_rings(0.5, 0.5, [square, hole])
    assert tms_keys("005200-04-076") == ["005200-04-076", "00520004076"]
    chapin = {"000700-05-032": {"code": "SR1", "description": "Suburban Residential 1", "jurisdiction": "Town of Chapin"}}
    west = PolyIndex(
        [
            {
                "code": "R1",
                "description": "High Density Residential",
                "jurisdiction": "City of West Columbia",
                "rings": [[[-81.1, 33.9], [-81.0, 33.9], [-81.0, 34.0], [-81.1, 34.0], [-81.1, 33.9]]],
                "bbox": (-81.1, 33.9, -81.0, 34.0),
            }
        ]
    )
    county = PolyIndex(
        [
            {
                "code": "RD",
                "description": "Restrictive Development",
                "jurisdiction": "Lexington County",
                "rings": [[[-81.3, 33.9], [-81.2, 33.9], [-81.2, 34.0], [-81.3, 34.0], [-81.3, 33.9]]],
                "bbox": (-81.3, 33.9, -81.2, 34.0),
            }
        ]
    )
    columbia = {"00520004076": {"code": "RSF-1", "description": None, "jurisdiction": "City of Columbia"}}
    features = [
        {
            "properties": {
                "parcelId": "000700-05-032",
                "zoningCode": "RD",
                "centroid": [-81.05, 33.95],
            }
        },
        {
            "properties": {
                "parcelId": "005200-04-076",
                "zoningCode": None,
                "centroid": [-81.25, 33.95],
            }
        },
        {
            "properties": {
                "parcelId": "999",
                "zoningCode": None,
                "centroid": [-81.05, 33.95],
            }
        },
        {
            "properties": {
                "parcelId": "888",
                "zoningCode": "AG",
                "centroid": [-81.25, 33.95],
            }
        },
    ]
    counts = apply_lexington_zoning(features, chapin=chapin, west=west, cayce=None, columbia=columbia, county=county)
    assert counts["chapin"] == 1
    assert features[0]["properties"]["zoningCode"] == "SR1"
    assert features[0]["properties"]["jurisdictionCode"] == "Town of Chapin"
    assert counts["columbia"] == 1
    assert features[1]["properties"]["zoningCode"] == "RSF-1"
    assert features[1]["properties"]["jurisdictionCode"] == "City of Columbia"
    assert counts["westColumbia"] == 1
    assert features[2]["properties"]["jurisdictionCode"] == "City of West Columbia"
    assert counts["parcelAttribute"] == 1
    assert features[3]["properties"]["zoningCode"] == "AG"
    assert "jurisdictionCode" not in features[3]["properties"]
    city = [{"properties": {"zoningCode": "PD", "zoningDistrict": "PD", "centroid": [-81.05, 33.95]}}]
    apply_columbia_city_labels(city)
    assert city[0]["properties"]["jurisdictionCode"] == "City of Columbia"
    assert "Richland County-wide" in city[0]["properties"]["dataGaps"][0]
    assert city[0]["properties"]["zoningDistrict"] is None
    flu = PolyIndex(
        [
            {
                "code": "UCMF",
                "description": "Urban Core Multifamily",
                "jurisdiction": "City of Columbia",
                "rings": [[[-81.1, 33.9], [-81.0, 33.9], [-81.0, 34.0], [-81.1, 34.0], [-81.1, 33.9]]],
                "bbox": (-81.1, 33.9, -81.0, 34.0),
            }
        ]
    )
    assert apply_flu(features, flu) == 2
    assert features[0]["properties"]["flu"]["jurisdiction"] == "City of Columbia"
    assert features[0]["properties"]["flu"]["code"] == "UCMF"
    print("columbia_muni self-test ok")


if __name__ == "__main__":
    _self_test()
