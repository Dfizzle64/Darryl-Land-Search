"""Wake County, NC (FIPS 37183) parcel enrich for the Raleigh–Durham market.

Primary polygons are Wake Property/Parcels. Zoning is routed by
PLANNING_JURISDICTION to county Planning/Zoning MapServer layers 14–28
(Raleigh is MapServer/23 — the Zoning FeatureServer omits it). Future land
use is joined only where a public municipal layer exists. NC OneMap
``cntyfips='183'`` is the fallback when the county parcel service fails.

Designations are copied from those layers. Nothing in here invents a
multifamily or future-land-use category.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Callable

FIPS = "37183"
SOURCE = "nc-wake-county-parcels"
FALLBACK_SOURCE = "nc-onemap-37183"

PARCEL_URLS = [
    "https://maps.wakegov.com/arcgis/rest/services/Property/Parcels/FeatureServer/0/query",
    "https://maps.wake.gov/arcgis/rest/services/Property/Parcels/FeatureServer/0/query",
]
ONEMAP_URLS = [
    "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1/query",
    "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1/query",
]
ZONING_ROOT = "https://maps.wake.gov/arcgis/rest/services/Planning/Zoning/MapServer"
APPRAISER_TEMPLATE = "https://services.wakegov.com/realestate/Account.asp?id={reid}"
APPRAISER_SEARCH = "https://services.wakegov.com/realestate/"

PARCEL_WHERE = "CALC_AREA>=5 AND CALC_AREA<=150"
ONEMAP_WHERE = "cntyfips='183' AND gisacres>=5 AND gisacres<=150"

PARCEL_FIELDS = [
    "PIN_NUM",
    "REID",
    "PARCEL_PK",
    "CALC_AREA",
    "DEED_ACRES",
    "OWNER",
    "ADDR1",
    "ADDR2",
    "ADDR3",
    "SITE_ADDRESS",
    "CITY_DECODE",
    "ZIPNUM",
    "SALE_DATE",
    "TOTSALPRICE",
    "LAND_VAL",
    "BLDG_VAL",
    "TOTAL_VALUE_ASSD",
    "PLANNING_JURISDICTION",
    "LAND_CLASS_DECODE",
]

ONEMAP_FIELDS = [
    "parno",
    "ownname",
    "siteadd",
    "scity",
    "gisacres",
    "mailadd",
    "mcity",
    "mstate",
    "mzip",
    "saledate",
    "saledatetx",
    "parval",
    "landval",
    "improvval",
    "cntyfips",
]

# Codes are the parcel PLANNING_JURISDICTION values. City layers are preferred
# over county zoning. County MapServer/17 is unincorporated (WC) only.
JURISDICTIONS: dict[str, dict[str, Any]] = {
    "RA": {
        "name": "Raleigh",
        "zoning": {"layer": 23, "code": ["ZONING"], "label": ["ZONE_TYPE_DECODE"]},
        "flu": {
            "url": "https://maps.raleighnc.gov/arcgis/rest/services/Planning/FutureLandUse/MapServer/0/query",
            "code": ["LAND_USE"],
            "label": ["LAND_USE"],
            "source": "Raleigh Future Land Use",
        },
    },
    "CA": {
        "name": "Cary",
        "zoning": {"layer": 16, "code": ["CLASS"], "label": ["NAME"]},
        "flu": {
            "url": "https://maps-apis.carync.gov/server/rest/services/LandUse/LandUsePlanning/FeatureServer/18/query",
            "code": ["FRAMEWORKCODE"],
            "label": ["FRAMEWORKCODE"],
            "source": "Cary Future Growth Framework",
        },
    },
    "AP": {
        "name": "Apex",
        "zoning": {"layer": 14, "code": ["CLASS"]},
        "flu": {
            "url": "https://services1.arcgis.com/nry3yyvaEfskMEXA/arcgis/rest/services/2045_Future_Land_Use/FeatureServer/3/query",
            "code": ["Class"],
            "label": ["Class"],
            "source": "Apex 2045 Future Land Classifications",
        },
    },
    "HS": {
        "name": "Holly Springs",
        "zoning": {"layer": 20, "code": ["CLASS"]},
        "flu": {
            "url": "https://gis.hollyspringsnc.us/ths_arcserver/rest/services/Planning/Future_Land_Use/MapServer/0/query",
            "code": ["CODE"],
            "label": ["NAME", "CODE"],
            "source": "Holly Springs Future Land Use",
        },
    },
    "FV": {
        "name": "Fuquay-Varina",
        "zoning": {"layer": 18, "code": ["CLASS"]},
        "flu": {
            "url": "https://gis1.fuquay-varina.org/server/rest/services/Public/Land_Use_Plan/MapServer/0/query",
            "code": ["land_use"],
            "label": ["land_use"],
            "source": "Fuquay-Varina Land Use Plan",
        },
    },
    "GA": {
        "name": "Garner",
        "zoning": {"layer": 19, "code": ["CLASS"]},
        "flu": {
            "url": "https://services1.arcgis.com/o3ok0s2woZDh8Saq/arcgis/rest/services/Garner_Forward_Character_Typology/FeatureServer/4/query",
            "code": ["Use_"],
            "label": ["Use_"],
            "source": "Garner Forward character typology (coarse, 8 polygons)",
        },
    },
    "KN": {
        "name": "Knightdale",
        "zoning": {"layer": 21, "code": ["CLASS"]},
        "flu": {
            "url": "https://services1.arcgis.com/a7CWfuGP5ZnLYE7I/arcgis/rest/services/Knightdale_Future_Land_Use/FeatureServer/0/query",
            "code": ["CATEGORY"],
            "label": ["CATEGORY"],
            "pinFields": ["PIN_NUM", "REID"],
            "geometry": False,
            "source": "Knightdale Future Land Use (PIN join; source CRS is Web Mercator)",
        },
    },
    "MO": {
        "name": "Morrisville",
        "zoning": {"layer": 22, "code": ["CLASS"]},
        "flu": {
            "url": "https://services.arcgis.com/ud8kSLNkfBb9WX8U/arcgis/rest/services/Draft_Future_Land_Use_Base_Map/FeatureServer/1/query",
            "code": ["FutureUse2", "HLA_FLU"],
            "label": ["FutureUse2", "HLA_Label", "HLA_FLU"],
            "source": "Morrisville draft future land use",
        },
    },
    "RO": {
        "name": "Rolesville",
        "zoning": {"layer": 24, "code": ["CLASS"]},
        "fluGap": "No public future land use layer for Rolesville.",
    },
    "WF": {
        "name": "Wake Forest",
        "zoning": {"layer": 25, "code": ["ZONECLASS", "CLASS", "ZONELABEL"]},
        "flu": {
            "url": "https://services1.arcgis.com/gqTCvanrwF2z2HEu/arcgis/rest/services/LandUse/FeatureServer/0/query",
            "code": ["LandUseCat"],
            "label": ["LandUseCat"],
            "source": "Wake Forest LandUse (coarse existing categories, not a detailed FLU map)",
        },
    },
    "WE": {
        "name": "Wendell",
        "zoning": {"layer": 26, "code": ["CLASS"]},
        "flu": {
            "url": "https://services5.arcgis.com/eqafRVo2WxMvxwGw/arcgis/rest/services/Future_Land_Use_Map/FeatureServer/0/query",
            "code": ["PLACETYPE"],
            "label": ["PLACETYPE"],
            "pinFields": ["PIN_NUM", "REID"],
            "geometry": False,
            "source": "Wendell Future Land Use (PIN join)",
        },
    },
    "ZB": {
        "name": "Zebulon",
        "zoning": {"layer": 27, "code": ["CLASS"]},
        "fluGap": "No public future land use layer for Zebulon.",
    },
    "AN": {
        "name": "Angier",
        "zoning": {"layer": 15, "code": ["CLASS"]},
        "fluGap": "No public future land use layer for Angier.",
    },
    "WC": {
        "name": "Wake County",
        "zoning": {"layer": 17, "code": ["CLASS"]},
        "fluGap": "No countywide future land use layer for unincorporated Wake County.",
    },
    "RD": {
        "name": "RDU Airport",
        "zoning": {"layer": 28, "code": ["CLASS"]},
        "fluGap": "No public future land use layer for RDU Airport zoning.",
    },
    "DU": {"name": "Durham", "fluGap": "Durham-edge parcels have no Wake zoning or FLU layer on this service."},
    "CL": {"name": "Clayton", "fluGap": "Clayton-edge parcels have no Wake zoning or FLU layer on this service."},
    "RP": {"name": "Research Triangle Park", "fluGap": "No public RTP future land use layer on the Wake zoning service."},
}

CITY_ZONING_CODES = ["RA", "CA", "AP", "HS", "FV", "GA", "KN", "MO", "RO", "WF", "WE", "ZB", "AN", "RD"]

WAKE_GAPS = [
    "No countywide future land use layer. FLU is joined only from the municipal public layers that exist.",
    "Rolesville and Zebulon have zoning and no public FLU REST layer. Angier, Durham-edge, Clayton-edge, RTP, and RDU Airport also have no verified public FLU layer.",
    "Wake Forest land use is a coarse category layer, not a detailed future land use map. Garner FLU is an 8-polygon character typology. Morrisville FLU is a draft layer.",
    "Knightdale FLU is joined on PIN_NUM because that layer is Web Mercator. Wendell FLU is joined on PIN_NUM.",
    "Raleigh zoning is Planning/Zoning MapServer/23. The county Zoning FeatureServer omits Raleigh.",
    "County zoning (MapServer/17) covers unincorporated PLANNING_JURISDICTION=WC only.",
    "Morrisville zoning is a sparse public layer (about 32 polygons).",
    "Last sale only (SALE_DATE and TOTSALPRICE). No multi-transfer sales history on this layer.",
    "Tax figure is assessed value (TOTAL_VALUE_ASSD). Property/Parcels has no separate market value.",
    "Owner phones and emails are not collected.",
]

_CITY_LINE = re.compile(r"^(?P<city>.+?)\s+(?P<state>[A-Z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)$")
_ISO_DAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_SLASH_DAY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def first_clean(attrs: dict, fields: list[str]) -> str | None:
    for field in fields:
        text = clean(attrs.get(field))
        if text and text not in {"0", "null", "Null"}:
            return text
    return None


def pin_key(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    return re.sub(r"[^0-9A-Za-z]", "", text).upper()


def appraiser_url(reid: Any) -> str:
    text = clean(reid)
    if not text:
        return APPRAISER_SEARCH
    return APPRAISER_TEMPLATE.format(reid=text)


def epoch_to_iso(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        text = value.strip()
        iso = _ISO_DAY.match(text)
        if iso:
            return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"
        slash = _SLASH_DAY.match(text)
        if slash:
            month, day, year = int(slash.group(1)), int(slash.group(2)), int(slash.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
        try:
            value = float(text)
        except ValueError:
            return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number <= 0:
        return None
    seconds = number / 1000.0 if number > 10_000_000_000 else number
    if seconds < 315532800 or seconds > 4102444800:
        return None
    return datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%d")


def parse_mailing(addr1: Any, addr2: Any, addr3: Any) -> dict[str, str | None]:
    """Split Wake ADDR1/ADDR2/ADDR3. The city/state/ZIP line is often ADDR2, sometimes ADDR3."""
    streets: list[str] = []
    city = state = zip_code = None
    for raw in (addr1, addr2, addr3):
        text = clean(raw)
        if not text:
            continue
        normalized = re.sub(r"\s+", " ", text.replace(",", " ").replace(".", " ")).strip().upper()
        match = _CITY_LINE.match(normalized)
        if match and city is None:
            city = match.group("city").strip(" -")
            state = match.group("state")
            zip_code = match.group("zip")[:5]
            continue
        streets.append(text)
    return {
        "line1": streets[0] if streets else None,
        "line2": streets[1] if len(streets) > 1 else None,
        "city": city,
        "state": state,
        "zip": zip_code,
    }


def positive_price(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number <= 0:
        return None
    return number


def assessed_value(attrs: dict) -> float | None:
    total = attrs.get("TOTAL_VALUE_ASSD")
    if total is not None and total != "":
        try:
            number = float(total)
        except (TypeError, ValueError):
            number = None
        if number is not None and number == number and number >= 0:
            return number
    parts = []
    for field in ("LAND_VAL", "BLDG_VAL"):
        try:
            number = float(attrs.get(field))
        except (TypeError, ValueError):
            continue
        if number == number and number >= 0:
            parts.append(number)
    if parts and any(part > 0 for part in parts):
        return sum(parts)
    return None


def signed_area(ring: list[list[float]]) -> float:
    area = 0.0
    for index in range(len(ring) - 1):
        x1, y1 = ring[index]
        x2, y2 = ring[index + 1]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    count = len(ring)
    if count < 4:
        return False
    previous = count - 1
    for index in range(count):
        x1, y1 = ring[index]
        x2, y2 = ring[previous]
        if (y1 > lat) != (y2 > lat):
            denom = y2 - y1
            if denom == 0:
                previous = index
                continue
            cross = (x2 - x1) * (lat - y1) / denom + x1
            if lon < cross:
                inside = not inside
        previous = index
    return inside


def esri_parts(geom: dict | None, outer_negative: bool) -> list[tuple[list[list[float]], list[list[list[float]]]]]:
    rings = (geom or {}).get("rings") or []
    parts: list[tuple[list[list[float]], list[list[list[float]]]]] = []
    exterior: list[list[float]] | None = None
    holes: list[list[list[float]]] = []
    for ring in rings:
        coords = [[float(x), float(y)] for x, y in ring]
        if len(coords) < 4:
            continue
        if coords[0] != coords[-1]:
            coords = coords + [coords[0]]
        area = signed_area(coords)
        is_outer = area < 0 if outer_negative else area > 0
        if area == 0:
            is_outer = exterior is None
        if is_outer:
            if exterior is not None:
                parts.append((exterior, holes))
            exterior = coords
            holes = []
        elif exterior is None:
            exterior = coords
            holes = []
        else:
            holes.append(coords)
    if exterior is not None:
        parts.append((exterior, holes))
    return parts


def _ring_centroid(ring: list[list[float]]) -> tuple[float, float] | None:
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    if not pts:
        return None
    return sum(point[0] for point in pts) / len(pts), sum(point[1] for point in pts) / len(pts)


def contains_parts(lon: float, lat: float, parts: list[tuple[list[list[float]], list[list[list[float]]]]]) -> bool:
    for exterior, holes in parts:
        if point_in_ring(lon, lat, exterior) and not any(point_in_ring(lon, lat, hole) for hole in holes):
            return True
    return False


def detect_outer_negative(geoms: list[dict]) -> bool:
    samples = []
    for geom in geoms:
        if len(samples) >= 12:
            break
        rings = geom.get("rings") or []
        if rings:
            samples.append(geom)
    if not samples:
        return True
    scores = {True: 0, False: 0}
    for geom in samples:
        for outer_negative in (True, False):
            parts = esri_parts(geom, outer_negative)
            if not parts:
                continue
            center = _ring_centroid(parts[0][0])
            if center and contains_parts(center[0], center[1], parts):
                scores[outer_negative] += 1
    return scores[True] >= scores[False]


class PolyIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.bins: dict[tuple[int, int], list[tuple[tuple[float, float, float, float], list, Any]]] = defaultdict(list)

    def add(self, geom: dict | None, payload: Any, outer_negative: bool) -> None:
        parts = esri_parts(geom, outer_negative)
        if not parts:
            return
        minx = miny = float("inf")
        maxx = maxy = float("-inf")
        area = 0.0
        for exterior, _holes in parts:
            area += abs(signed_area(exterior))
            for lon, lat in exterior:
                minx = min(minx, lon)
                miny = min(miny, lat)
                maxx = max(maxx, lon)
                maxy = max(maxy, lat)
        record = ((minx, miny, maxx, maxy), parts, area, payload)
        x0 = int(minx // self.cell)
        x1 = int(maxx // self.cell)
        y0 = int(miny // self.cell)
        y1 = int(maxy // self.cell)
        for ix in range(x0, x1 + 1):
            for iy in range(y0, y1 + 1):
                self.bins[(ix, iy)].append(record)

    def hit(self, lon: float, lat: float) -> Any | None:
        payload, _area = self.hit_with_area(lon, lat)
        return payload

    def hit_with_area(self, lon: float, lat: float) -> tuple[Any | None, float]:
        best = None
        best_area = float("inf")
        seen: set[int] = set()
        ix = int(lon // self.cell)
        iy = int(lat // self.cell)
        for record in self.bins.get((ix, iy), []):
            identity = id(record)
            if identity in seen:
                continue
            seen.add(identity)
            (minx, miny, maxx, maxy), parts, area, payload = record
            if lon < minx or lon > maxx or lat < miny or lat > maxy:
                continue
            if area < best_area and contains_parts(lon, lat, parts):
                best = payload
                best_area = area
        return best, best_area


def _load_layer(fetch_object_ids: Callable, fetch_by_ids: Callable, url: str, fields: list[str], geometry: bool) -> list[dict]:
    ids = fetch_object_ids(url, "1=1")
    if not ids:
        return []
    return fetch_by_ids(url, ids, fields, batch=80 if geometry else 200, return_geometry=geometry)


def build_poly_index(features: list[dict], payload_of: Callable[[dict], Any]) -> PolyIndex:
    geoms = [item.get("geometry") or {} for item in features]
    outer_negative = detect_outer_negative(geoms)
    index = PolyIndex()
    for item in features:
        payload = payload_of(item.get("attributes") or {})
        if payload is None:
            continue
        index.add(item.get("geometry"), payload, outer_negative)
    return index


def build_pin_index(features: list[dict], pin_fields: list[str], payload_of: Callable[[dict], Any]) -> dict[str, Any]:
    index: dict[str, Any] = {}
    for item in features:
        attrs = item.get("attributes") or {}
        payload = payload_of(attrs)
        if payload is None:
            continue
        for field in pin_fields:
            key = pin_key(attrs.get(field))
            if key and key not in index:
                index[key] = payload
    return index


def jurisdiction_meta(code: str | None) -> dict[str, Any] | None:
    if not code:
        return None
    return JURISDICTIONS.get(code.upper())


def static_gaps() -> list[str]:
    return list(WAKE_GAPS)


def _zoning_fields(spec: dict) -> list[str]:
    fields = list(spec.get("code") or [])
    for field in spec.get("label") or []:
        if field not in fields:
            fields.append(field)
    return fields


def _flu_payload(attrs: dict, spec: dict, jurisdiction: str) -> dict | None:
    code = first_clean(attrs, spec.get("code") or [])
    label = first_clean(attrs, spec.get("label") or []) or code
    if not code and not label:
        return None
    return {
        "code": code or label,
        "label": label or code,
        "jurisdiction": jurisdiction,
        "source": spec.get("source"),
    }


def pull_wake(county: dict, markets: list[str], hooks: dict[str, Callable]) -> dict[str, Any]:
    fetch_json = hooks["fetch_json"]
    fetch_object_ids = hooks["fetch_object_ids"]
    fetch_by_ids = hooks["fetch_by_ids"]
    empty_feature = hooks["empty_feature"]
    rings_to_feature_geometry = hooks["rings_to_feature_geometry"]
    centroid_of = hooks["centroid_of"]
    plausible_centroid = hooks["plausible_centroid"]
    zip_str = hooks["zip_str"]
    in_band = hooks["in_band"]
    count_where = hooks["count_where"]

    parcel_url = None
    expected = 0
    primary_error = None
    for url in PARCEL_URLS:
        try:
            expected = count_where(url, PARCEL_WHERE)
            parcel_url = url
            if expected > 0:
                break
        except Exception as exc:  # noqa: BLE001
            primary_error = exc
            print(f"  wake primary failed {url[:80]}: {exc}", flush=True)
    used_fallback = parcel_url is None or expected <= 0
    if used_fallback:
        for url in ONEMAP_URLS:
            try:
                expected = count_where(url, ONEMAP_WHERE)
                parcel_url = url
                if expected > 0:
                    break
            except Exception as exc:  # noqa: BLE001
                primary_error = exc
                print(f"  wake onemap failed {url[:80]}: {exc}", flush=True)
        if parcel_url is None or expected <= 0:
            raise RuntimeError(f"Wake parcel sources failed: {primary_error}")

    print(f"  wake source rows {expected} via {parcel_url}", flush=True)
    fields = ONEMAP_FIELDS if used_fallback else PARCEL_FIELDS
    where = ONEMAP_WHERE if used_fallback else PARCEL_WHERE
    ids = fetch_object_ids(parcel_url, where)
    raw = fetch_by_ids(parcel_url, ids, fields, batch=100, return_geometry=True)

    zoning_indexes: dict[str, PolyIndex] = {}
    flu_indexes: dict[str, PolyIndex] = {}
    flu_pins: dict[str, dict[str, Any]] = {}
    if not used_fallback:
        _load_joins(fetch_object_ids, fetch_by_ids, fetch_json, zoning_indexes, flu_indexes, flu_pins)
    else:
        # OneMap has no planning jurisdiction. Still join the municipal layers spatially.
        _load_joins(fetch_object_ids, fetch_by_ids, fetch_json, zoning_indexes, flu_indexes, flu_pins)

    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        feature, parcel_key = _normalize_parcel(
            item,
            county=county,
            markets=markets,
            fallback=used_fallback,
            empty_feature=empty_feature,
            rings_to_feature_geometry=rings_to_feature_geometry,
            centroid_of=centroid_of,
            plausible_centroid=plausible_centroid,
            zip_str=zip_str,
            in_band=in_band,
            zoning_indexes=zoning_indexes,
            flu_indexes=flu_indexes,
            flu_pins=flu_pins,
        )
        if feature is None or parcel_key is None:
            dropped += 1
            continue
        previous = by_id.get(parcel_key)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_key] = feature

    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    stats = _stats(features)
    gaps = _gap_lines(stats, used_fallback, primary_error)
    return {
        "features": features,
        "dropped": dropped,
        "sourceCount": expected,
        "source": FALLBACK_SOURCE if used_fallback else SOURCE,
        "queryUrl": parcel_url,
        "gaps": gaps,
        "coverage": "complete-gte-5ac" if features else "gap",
        "stats": stats,
    }


def _load_joins(fetch_object_ids, fetch_by_ids, fetch_json, zoning_indexes, flu_indexes, flu_pins) -> None:
    loaded_zoning: set[int] = set()
    for code, meta in JURISDICTIONS.items():
        zoning = meta.get("zoning")
        if zoning and zoning["layer"] not in loaded_zoning:
            url = f"{ZONING_ROOT}/{zoning['layer']}/query"
            fields = _zoning_fields(zoning)
            print(f"  zoning {meta['name']} layer {zoning['layer']}", flush=True)
            try:
                rows = _load_layer(fetch_object_ids, fetch_by_ids, url, fields, True)
            except Exception as exc:  # noqa: BLE001
                print(f"    zoning skipped: {exc}", flush=True)
                rows = []
            index = build_poly_index(rows, lambda attrs, spec=zoning, name=meta["name"]: _zoning_payload(attrs, spec, name))
            zoning_indexes[code] = index
            loaded_zoning.add(zoning["layer"])
        elif zoning:
            # Same layer object is not shared across codes today; copy by reusing the built index.
            donor = next(key for key, item in JURISDICTIONS.items() if item.get("zoning", {}).get("layer") == zoning["layer"] and key in zoning_indexes)
            zoning_indexes[code] = zoning_indexes[donor]
        flu = meta.get("flu")
        if not flu:
            continue
        print(f"  flu {meta['name']}", flush=True)
        try:
            rows = _load_layer(
                fetch_object_ids,
                fetch_by_ids,
                flu["url"],
                list(dict.fromkeys([*(flu.get("code") or []), *(flu.get("label") or []), *(flu.get("pinFields") or [])])),
                bool(flu.get("geometry", True)),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"    flu skipped: {exc}", flush=True)
            rows = []
        if flu.get("geometry", True):
            flu_indexes[code] = build_poly_index(
                rows,
                lambda attrs, spec=flu, name=meta["name"]: _flu_payload(attrs, spec, name),
            )
        else:
            flu_pins[code] = build_pin_index(
                rows,
                flu.get("pinFields") or ["PIN_NUM"],
                lambda attrs, spec=flu, name=meta["name"]: _flu_payload(attrs, spec, name),
            )
    # fetch_json is part of the hook surface for callers that want a count probe.
    del fetch_json


def _zoning_payload(attrs: dict, spec: dict, jurisdiction: str) -> str | None:
    code = first_clean(attrs, spec.get("code") or [])
    if not code:
        return None
    label = first_clean(attrs, spec.get("label") or [])
    if label and label.upper() != code.upper():
        return f"{code} ({label})"
    return code


def _normalize_parcel(
    item: dict,
    *,
    county: dict,
    markets: list[str],
    fallback: bool,
    empty_feature: Callable,
    rings_to_feature_geometry: Callable,
    centroid_of: Callable,
    plausible_centroid: Callable,
    zip_str: Callable,
    in_band: Callable,
    zoning_indexes: dict[str, PolyIndex],
    flu_indexes: dict[str, PolyIndex],
    flu_pins: dict[str, dict[str, Any]],
) -> tuple[dict | None, str | None]:
    attrs = item.get("attributes") or {}
    geometry, computed = rings_to_feature_geometry(item.get("geometry"))
    if not geometry:
        return None, None
    center = centroid_of(geometry)
    if not plausible_centroid(center):
        return None, None
    if fallback:
        acres = attrs.get("gisacres")
        try:
            acres_n = float(acres) if acres is not None else None
        except (TypeError, ValueError):
            acres_n = None
        if acres_n is None:
            acres_n = computed
        parcel_id = clean(attrs.get("parno"))
        mailing = {
            "line1": clean(attrs.get("mailadd")),
            "line2": None,
            "city": clean(attrs.get("mcity")),
            "state": clean(attrs.get("mstate")),
            "zip": zip_str(attrs.get("mzip")),
        }
        sale = epoch_to_iso(attrs.get("saledatetx")) or epoch_to_iso(attrs.get("saledate"))
        price = None
        assessed = positive_price(attrs.get("landval"))
        market = positive_price(attrs.get("parval"))
        owner = clean(attrs.get("ownname"))
        situs = clean(attrs.get("siteadd"))
        city = clean(attrs.get("scity"))
        zip_code = None
        juris_code = None
        reid = None
        dor = None
        pin_for_join = parcel_id
    else:
        try:
            acres_n = float(attrs.get("CALC_AREA"))
        except (TypeError, ValueError):
            acres_n = None
        parcel_id = clean(attrs.get("PIN_NUM")) or clean(attrs.get("REID")) or clean(attrs.get("PARCEL_PK"))
        mailing = parse_mailing(attrs.get("ADDR1"), attrs.get("ADDR2"), attrs.get("ADDR3"))
        sale = epoch_to_iso(attrs.get("SALE_DATE"))
        price = positive_price(attrs.get("TOTSALPRICE"))
        assessed = assessed_value(attrs)
        market = None
        owner = clean(attrs.get("OWNER"))
        situs = clean(attrs.get("SITE_ADDRESS"))
        city = clean(attrs.get("CITY_DECODE"))
        zip_code = zip_str(attrs.get("ZIPNUM"))
        juris_code = clean(attrs.get("PLANNING_JURISDICTION"))
        if juris_code:
            juris_code = juris_code.upper()
        reid = clean(attrs.get("REID"))
        dor = clean(attrs.get("LAND_CLASS_DECODE"))
        pin_for_join = clean(attrs.get("PIN_NUM"))
    if not in_band(acres_n) or not parcel_id or center is None:
        return None, None

    zoning, flu, gaps, stored_juris = _join_labels(
        juris_code,
        center,
        pin_for_join,
        None if fallback else reid,
        zoning_indexes,
        flu_indexes,
        flu_pins,
        allow_spatial_route=fallback or not juris_code,
    )
    feature = empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=markets,
        parcel_id=parcel_id,
        acreage=acres_n,
        geometry=geometry,
        center=center,
        source=FALLBACK_SOURCE if fallback else SOURCE,
        owner=owner,
        situs=situs,
        city=city,
        zip_code=zip_code,
        zoning=zoning,
        dor=dor,
        sale_price=price,
        sale_date=sale,
        market_value=market,
        assessed=assessed,
        mail1=mailing["line1"],
        mail2=mailing["line2"],
        mail_city=mailing["city"],
        mail_state=mailing["state"],
        mail_zip=mailing["zip"],
    )
    props = feature["properties"]
    props["jurisdictionCode"] = stored_juris or juris_code
    props["appraiserUrl"] = appraiser_url(reid) if not fallback else APPRAISER_SEARCH
    props["flu"] = flu
    if gaps:
        props["dataGaps"] = gaps
    return feature, parcel_id


def _join_labels(
    juris_code: str | None,
    center: tuple[float, float],
    pin: str | None,
    reid: str | None,
    zoning_indexes: dict[str, PolyIndex],
    flu_indexes: dict[str, PolyIndex],
    flu_pins: dict[str, dict[str, Any]],
    allow_spatial_route: bool,
) -> tuple[str | None, dict | None, list[str], str | None]:
    original = juris_code
    meta = jurisdiction_meta(juris_code)
    gaps: list[str] = []
    zoning = None
    flu = None
    routed = juris_code if meta and meta.get("zoning") else None
    if routed and routed in zoning_indexes:
        zoning = zoning_indexes[routed].hit(center[0], center[1])
    elif allow_spatial_route:
        zoning, routed = _most_local_zoning(center, zoning_indexes)
        if routed:
            meta = jurisdiction_meta(routed)
    if meta and meta.get("fluGap") and not meta.get("flu"):
        gaps.append(meta["fluGap"])
    flu_code = routed or (juris_code if meta and meta.get("flu") else None)
    if flu_code and flu_code in flu_pins:
        table = flu_pins[flu_code]
        flu = None
        for key in (pin_key(pin), pin_key(reid)):
            if key and key in table:
                flu = table[key]
                break
    elif flu_code and flu_code in flu_indexes:
        flu = flu_indexes[flu_code].hit(center[0], center[1])
    if zoning is None and (routed or (meta and meta.get("zoning"))):
        name = (meta or {}).get("name") or routed or "this jurisdiction"
        gaps.append(f"No zoning polygon hit in the {name} layer.")
    stored = original or routed
    return zoning, flu, gaps, stored


def _most_local_zoning(center: tuple[float, float], zoning_indexes: dict[str, PolyIndex]) -> tuple[str | None, str | None]:
    """Smallest containing city polygon wins. County zoning is only the fallback."""
    best_label = None
    best_code = None
    best_area = float("inf")
    for code in CITY_ZONING_CODES:
        index = zoning_indexes.get(code)
        if not index:
            continue
        label, area = index.hit_with_area(center[0], center[1])
        if label and area < best_area:
            best_label = label
            best_code = code
            best_area = area
    if best_label:
        return best_label, best_code
    county = zoning_indexes.get("WC")
    if county:
        label = county.hit(center[0], center[1])
        if label:
            return label, "WC"
    return None, None


def _stats(features: list[dict]) -> dict[str, int]:
    stats = {
        "parcels": len(features),
        "owner": 0,
        "mailing": 0,
        "situs": 0,
        "sale": 0,
        "assessed": 0,
        "zoning": 0,
        "flu": 0,
    }
    for feature in features:
        props = feature["properties"]
        if props.get("ownerName"):
            stats["owner"] += 1
        mail = props.get("mailingAddress") or {}
        if mail.get("line1") or mail.get("city"):
            stats["mailing"] += 1
        if props.get("situsAddress"):
            stats["situs"] += 1
        sale = props.get("lastSale") or {}
        if sale.get("date") or sale.get("price"):
            stats["sale"] += 1
        tax = props.get("tax") or {}
        if tax.get("assessedValue") is not None or tax.get("marketValue") is not None:
            stats["assessed"] += 1
        if props.get("zoningCode"):
            stats["zoning"] += 1
        if (props.get("flu") or {}).get("code"):
            stats["flu"] += 1
    return stats


def _gap_lines(stats: dict[str, int], fallback: bool, primary_error: Exception | None) -> list[str]:
    summary = (
        f"Wake 5–150 acre extract: {stats['parcels']} parcels; "
        f"owner {stats['owner']}; mailing {stats['mailing']}; situs {stats['situs']}; "
        f"sale {stats['sale']}; tax value {stats['assessed']}; "
        f"zoning {stats['zoning']}; future land use {stats['flu']}."
    )
    lines = [summary]
    if fallback:
        reason = f" Primary Property/Parcels query failed ({primary_error})." if primary_error else ""
        lines.append(
            "Fallback NC OneMap FeatureServer/1 with cntyfips='183'. OneMap has no sale price and no PLANNING_JURISDICTION."
            + reason
        )
    lines.extend(static_gaps())
    return lines
