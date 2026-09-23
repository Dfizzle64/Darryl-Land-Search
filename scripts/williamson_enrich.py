"""Williamson County, TN (FIPS 47187) public-GIS enricher.

Not a Comptroller IMPACT county. Parcels come from IDT/DataPull MapServer
layer 10 over HTTP (the HTTPS certificate does not match the hostname).
The MapServer speaks JSON only, so rings are converted here.

Jurisdiction is Corporate Limits (layer 2) when the centroid falls in a city,
otherwise the CITY tax-district code. City zoning and FLU are joined only
inside that city. Franklin Envision and Fairview 2040 are not applied outside
those limits. Nolensville and Thompson's Station have no public zoning REST.
"""

from __future__ import annotations

import math
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

PARCEL_QUERY = (
    "http://arcgis2.williamsoncounty-tn.gov/arcgis/rest/services/IDT/DataPull/MapServer/10/query"
)
LIMITS_QUERY = (
    "http://arcgis2.williamsoncounty-tn.gov/arcgis/rest/services/IDT/DataPull/MapServer/2/query"
)
COUNTY_ZONING_QUERY = (
    "http://arcgis2.williamsoncounty-tn.gov/arcgis/rest/services/IDT/DataPull/MapServer/0/query"
)
FRANKLIN_ZONING_QUERY = (
    "https://publicmaps.franklintn.gov/arcgis/rest/services/Maps/ZoningWebMercator/MapServer/9/query"
)
FRANKLIN_FLU_QUERY = (
    "https://publicmaps.franklintn.gov/arcgis/rest/services/Maps/ZoningWebMercator/MapServer/30/query"
)
BRENTWOOD_ZONING_QUERY = (
    "https://maps.brentwoodtn.gov/arcgis/rest/services/Datasets/AdministrativeAreas/MapServer/9/query"
)
FAIRVIEW_ZONING_QUERY = (
    "https://services6.arcgis.com/sCdesv1knCIWF2x3/arcgis/rest/services/Fairview_Zoning_Public/FeatureServer/0/query"
)
FAIRVIEW_FLU_QUERY = (
    "https://services6.arcgis.com/sCdesv1knCIWF2x3/arcgis/rest/services/Fairview_2040_Land_Use_Public/FeatureServer/0/query"
)
SPRING_HILL_ZONING_QUERY = (
    "https://services1.arcgis.com/tF0XsRR9ptiKNVW2/arcgis/rest/services/Zoning_Spring_Hill_view/FeatureServer/2/query"
)

INIGO_SEARCH = "https://inigo.williamson-tn.org/property_search/"
NOLENSVILLE_PORTAL = "https://nolensvilletn.interactivegis.com/map/"
THOMPSONS_PORTAL = "https://thompsons-station.gov/mapping-gis"
SOURCE = "tn-williamson-datapull-47187"
ACREAGE_WHERE = "CALC_ACRE >= 5 AND CALC_ACRE <= 150"

PARCEL_FIELDS = [
    "OBJECTID",
    "GISLINK",
    "lrsn",
    "parcel_id",
    "CITY",
    "ADDRESS",
    "streetnumber",
    "streetnumbersfx",
    "streetname",
    "owner1",
    "owner2",
    "own_street",
    "own_city",
    "own_state",
    "own_zip",
    "pxfer_date",
    "pxfer_da_1",
    "deed_book",
    "deed_page",
    "deed_bK",
    "deed_pG",
    "considerat",
    "consider_1",
    "land_marke",
    "imp_val",
    "total_mark",
    "land_asses",
    "imp_assess",
    "total_asse",
    "AC",
    "ACc",
    "CALC_ACRE",
    "SUBDIVISION",
    "property_T",
    "PARCEL_TYP",
    "SQFT_ASSES",
    "neighborho",
]

# CITY is a tax-district code, not a municipality name. 000264 and blank are
# not mapped: only Corporate Limits can place those parcels in a city.
CITY_TAX_CODES = {
    "000": "UNINCORPORATED",
    "086": "BRENTWOOD",
    "263967": "FRANKLIN",
    "263264": "FRANKLIN",
    "701": "SPRING HILL",
    "535": "NOLENSVILLE",
    "255": "FAIRVIEW",
    "718": "THOMPSONS STATION",
}

JURISDICTION_PREFIX = {
    "FRANKLIN": "FRK",
    "BRENTWOOD": "BRW",
    "SPRING HILL": "SPH",
    "FAIRVIEW": "FRV",
    "NOLENSVILLE": "NOL",
    "THOMPSONS STATION": "THS",
    "UNINCORPORATED": "WIL",
}

JURISDICTION_NAME = {
    "FRANKLIN": "Franklin",
    "BRENTWOOD": "Brentwood",
    "SPRING HILL": "Spring Hill",
    "FAIRVIEW": "Fairview",
    "NOLENSVILLE": "Nolensville",
    "THOMPSONS STATION": "Thompson's Station",
    "UNINCORPORATED": "Unincorporated Williamson",
}

ZONING_SOURCE = {
    "FRANKLIN": "franklin-zoningwebmercator-9",
    "BRENTWOOD": "brentwood-administrativeareas-9",
    "FAIRVIEW": "fairview-zoning-public",
    "SPRING HILL": "spring-hill-zoning-view-2",
    "UNINCORPORATED": "williamson-datapull-zones-0",
}


def williamson_spec() -> dict:
    return {
        "kind": "williamson",
        "url": PARCEL_QUERY,
        "where": ACREAGE_WHERE,
        "source": SOURCE,
        "coverage": "complete-gte-5ac",
        "gaps": [],
    }


def squash(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def city_tax_code(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def preserve_id(value: Any) -> str | None:
    """Keep internal spacing. GISLINK and parcel_id are fixed-width assessor ids."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def zip5(value: Any) -> str | None:
    text = squash(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return text[:10]


def epoch_to_iso(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed <= 0:
        return None
    if parsed > 10_000_000_000:
        parsed = parsed / 1000.0
    if parsed < 1_000_000_000:
        return None
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(parsed))
    except (OverflowError, OSError, ValueError):
        return None


def positive_money(value: Any, num: Callable[[Any], float | None]) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def keep_number(value: Any, num: Callable[[Any], float | None]) -> float | None:
    return num(value)


def situs_from_attrs(attrs: dict) -> str | None:
    address = squash(attrs.get("ADDRESS"))
    if address:
        return address
    parts = [squash(attrs.get(key)) for key in ("streetnumber", "streetnumbersfx", "streetname")]
    text = " ".join(part for part in parts if part)
    return text or None


def resolve_jurisdiction(city_code: str, limits_name: str | None) -> tuple[str, str]:
    """Return (jurisdiction key, how it was chosen).

    Corporate Limits win when the centroid is inside a city. Otherwise the
    CITY tax code is the first pass. 000264 and blank codes stay
    unincorporated unless the limits polygon says otherwise.
    """
    code = city_tax_code(city_code)
    limits = squash(limits_name)
    if limits:
        key = limits.upper()
        if key in JURISDICTION_PREFIX:
            return key, "corporate-limits"
    mapped = CITY_TAX_CODES.get(code)
    if mapped:
        return mapped, "city-tax-code"
    return "UNINCORPORATED", "unincorporated-fallback"


def jurisdiction_gaps(key: str, city_code: str, how: str) -> list[str]:
    gaps: list[str] = []
    code = city_tax_code(city_code)
    if code == "000264" and how != "corporate-limits":
        gaps.append(
            "CITY 000264 is a Franklin-area fringe tax code. The centroid is outside Corporate Limits, so Franklin zoning and Envision FLU were not applied."
        )
    if key == "NOLENSVILLE":
        gaps.append(
            f"Nolensville has no public zoning or FLU REST layer. Ownership geometry is the county parcel; zoning is the town viewer at {NOLENSVILLE_PORTAL}."
        )
    elif key == "THOMPSONS STATION":
        gaps.append(
            f"Thompson's Station has no public zoning or FLU REST layer. Ownership geometry is the county parcel; zoning is the town GIS page at {THOMPSONS_PORTAL}."
        )
    elif key == "BRENTWOOD":
        gaps.append("No public Brentwood future-land-use layer. FLU is null.")
    elif key == "SPRING HILL":
        gaps.append(
            "No public Spring Hill future-land-use layer. Zoning is the Williamson portion only; Maury County parcels are not in this extract."
        )
    elif key == "UNINCORPORATED":
        gaps.append("No countywide future-land-use layer. FLU is null outside Franklin and Fairview.")
    elif key == "FRANKLIN":
        gaps.append("Franklin Envision Design Concepts are policy guidance, not a zoning entitlement.")
    elif key == "FAIRVIEW":
        gaps.append("Fairview 2040 FUT_LU is policy guidance, not a zoning entitlement.")
    return gaps


def split_county_zone(value: Any) -> tuple[str | None, str | None]:
    text = squash(value)
    if not text:
        return None, None
    if " - " in text:
        code, _rest = text.split(" - ", 1)
        code = code.strip() or text
        return code, text
    return text, text


def _point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_feature(x: float, y: float, feature: dict) -> bool:
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        rings = geom["coordinates"]
        if not rings or not _point_in_ring(x, y, rings[0]):
            return False
        return not any(_point_in_ring(x, y, hole) for hole in rings[1:])
    if geom.get("type") == "MultiPolygon":
        for poly in geom["coordinates"]:
            if poly and _point_in_ring(x, y, poly[0]) and not any(_point_in_ring(x, y, hole) for hole in poly[1:]):
                return True
    return False


def _feature_bbox(feature: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, (list, tuple)) and node and isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        if isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk((feature.get("geometry") or {}).get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


class GridIndex:
    def __init__(self, cell: float = 0.03) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = _feature_bbox(feature)
        if not bbox:
            return
        west, south, east, north = bbox
        ix0 = math.floor(west / self.cell)
        ix1 = math.floor(east / self.cell)
        iy0 = math.floor(south / self.cell)
        iy1 = math.floor(north / self.cell)
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
            if _point_in_feature(x, y, feature):
                return feature
        for feature in self.broad:
            if _point_in_feature(x, y, feature):
                return feature
        return None


def _query_ids(fetch_json: Callable, url: str, where: str) -> list[int]:
    data = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:300])
    return [int(item) for item in (data.get("objectIds") or [])]


def _fetch_id_chunk(fetch_json: Callable, url: str, ids: list[int], out_fields: list[str], geometry_params: dict | None) -> list[dict]:
    params = {
        "objectIds": ",".join(str(item) for item in ids),
        "outFields": ",".join(out_fields),
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
    }
    if geometry_params:
        params.update(geometry_params)
    try:
        data = fetch_json(url, params, timeout=180)
    except RuntimeError:
        if len(ids) > 8:
            mid = len(ids) // 2
            return _fetch_id_chunk(fetch_json, url, ids[:mid], out_fields, geometry_params) + _fetch_id_chunk(
                fetch_json, url, ids[mid:], out_fields, geometry_params
            )
        raise
    if data.get("error"):
        if len(ids) > 8:
            mid = len(ids) // 2
            return _fetch_id_chunk(fetch_json, url, ids[:mid], out_fields, geometry_params) + _fetch_id_chunk(
                fetch_json, url, ids[mid:], out_fields, geometry_params
            )
        raise RuntimeError(str(data["error"])[:300])
    features = data.get("features") or []
    if len(features) < len(ids) and len(ids) > 8:
        mid = len(ids) // 2
        return _fetch_id_chunk(fetch_json, url, ids[:mid], out_fields, geometry_params) + _fetch_id_chunk(
            fetch_json, url, ids[mid:], out_fields, geometry_params
        )
    return features


def fetch_layer(
    fetch_json: Callable,
    url: str,
    where: str,
    out_fields: list[str],
    *,
    batch: int = 80,
    geometry_params: dict | None = None,
    label: str = "layer",
) -> list[dict]:
    ids = _query_ids(fetch_json, url, where)
    print(f"  {label}: {len(ids)} features", flush=True)
    features: list[dict] = []
    for start in range(0, len(ids), batch):
        chunk = ids[start : start + batch]
        features.extend(_fetch_id_chunk(fetch_json, url, chunk, out_fields, geometry_params))
        done = min(start + batch, len(ids))
        if done == len(ids) or done % (batch * 4) == 0:
            print(f"    {label} {done}/{len(ids)}", flush=True)
        time.sleep(0.02)
    return features


def esri_rings_to_geometry(geom: dict | None) -> tuple[dict | None, float]:
    """Group Esri JSON rings into GeoJSON.

    Exterior rings are clockwise (negative shoelace) and start a polygon.
    Counterclockwise rings are holes. This is the opposite of treating every
    positive ring as a new part, which drops later exteriors on multi-part
    zoning polygons.
    """
    if not geom or not geom.get("rings"):
        return None, 0.0
    polygons: list[list[list[list[float]]]] = []
    current: list[list[list[float]]] = []
    for ring in geom["rings"]:
        coords = [[float(x), float(y)] for x, y in ring]
        if len(coords) < 4:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        area = 0.0
        for i in range(len(coords) - 1):
            area += coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1]
        if not current or area < 0:
            if current:
                polygons.append(current)
            current = [coords]
        else:
            current.append(coords)
    if current:
        polygons.append(current)
    if not polygons:
        return None, 0.0
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}, 0.0
    return {"type": "MultiPolygon", "coordinates": polygons}, 0.0


def _index_layer(raw: list[dict], rings_to_geometry: Callable, payload_fn: Callable[[dict], dict | None]) -> tuple[GridIndex, int]:
    del rings_to_geometry  # Parcel tiles keep the shared simplifier. Joins need Esri ring order.
    index = GridIndex(0.03)
    kept = 0
    for item in raw:
        geometry, _acres = esri_rings_to_geometry(item.get("geometry"))
        if not geometry:
            continue
        payload = payload_fn(item.get("attributes") or {})
        if not payload:
            continue
        index.add({"type": "Feature", "geometry": geometry, "properties": payload})
        kept += 1
    return index, kept


def _limits_payload(attrs: dict) -> dict | None:
    name = squash(attrs.get("NAME"))
    if not name:
        return None
    return {"name": name.upper()}


def _county_zone_payload(attrs: dict) -> dict | None:
    code, district = split_county_zone(attrs.get("ZONES"))
    if not code:
        return None
    return {"code": code, "district": district}


def _franklin_zone_payload(attrs: dict) -> dict | None:
    code = squash(attrs.get("ZONECLASS"))
    if not code:
        return None
    return {"code": code, "district": squash(attrs.get("ZONEDESC")) or code}


def _brentwood_zone_payload(attrs: dict) -> dict | None:
    code = squash(attrs.get("Zoning"))
    if not code:
        return None
    return {"code": code, "district": code}


def _fairview_zone_payload(attrs: dict) -> dict | None:
    code = squash(attrs.get("Zoning"))
    if not code:
        return None
    return {"code": code, "district": code}


def _spring_hill_zone_payload(attrs: dict) -> dict | None:
    code = squash(attrs.get("Zone"))
    if not code:
        return None
    label = squash(attrs.get("Label")) or code
    overlay = squash(attrs.get("Overlay"))
    district = f"{label} (overlay {overlay})" if overlay else label
    return {"code": code, "district": district}


def _franklin_flu_payload(attrs: dict) -> dict | None:
    code = squash(attrs.get("DCABBREV"))
    if not code:
        return None
    return {
        "code": code,
        "label": squash(attrs.get("DESIGNCON")) or code,
        "jurisdiction": "FRK",
        "source": "franklin-envision-design-concepts",
    }


def _fairview_flu_payload(attrs: dict) -> dict | None:
    code = squash(attrs.get("FUT_LU"))
    if not code:
        return None
    return {
        "code": code,
        "label": code,
        "jurisdiction": "FRV",
        "source": "fairview-2040",
    }


def _load_reference_layers(fetch_json: Callable, rings_to_geometry: Callable) -> dict[str, Any]:
    simplify = {"maxAllowableOffset": "0.00012", "geometryPrecision": "5"}
    jobs = {
        "limits": (LIMITS_QUERY, "1=1", ["NAME"], None, _limits_payload, "corporate-limits"),
        "county_zoning": (COUNTY_ZONING_QUERY, "1=1", ["ZONES"], None, _county_zone_payload, "county-zones"),
        "franklin_zoning": (FRANKLIN_ZONING_QUERY, "1=1", ["ZONECLASS", "ZONEDESC"], simplify, _franklin_zone_payload, "franklin-zoning"),
        "franklin_flu": (FRANKLIN_FLU_QUERY, "1=1", ["DCABBREV", "DESIGNCON"], simplify, _franklin_flu_payload, "franklin-flu"),
        "brentwood_zoning": (BRENTWOOD_ZONING_QUERY, "1=1", ["Zoning"], simplify, _brentwood_zone_payload, "brentwood-zoning"),
        "fairview_zoning": (
            FAIRVIEW_ZONING_QUERY,
            "Zoning IS NOT NULL AND Zoning <> ''",
            ["Zoning"],
            simplify,
            _fairview_zone_payload,
            "fairview-zoning",
        ),
        "fairview_flu": (FAIRVIEW_FLU_QUERY, "FUT_LU IS NOT NULL AND FUT_LU <> ''", ["FUT_LU"], simplify, _fairview_flu_payload, "fairview-flu"),
        "spring_hill_zoning": (
            SPRING_HILL_ZONING_QUERY,
            "1=1",
            ["Zone", "Label", "Overlay"],
            simplify,
            _spring_hill_zone_payload,
            "spring-hill-zoning",
        ),
    }

    def one(spec: tuple) -> tuple[GridIndex, int]:
        url, where, fields, geom, payload_fn, label = spec
        raw = fetch_layer(fetch_json, url, where, fields, geometry_params=geom, label=label, batch=100)
        return _index_layer(raw, rings_to_geometry, payload_fn)

    loaded: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        future_map = {pool.submit(one, spec): name for name, spec in jobs.items()}
        for future in as_completed(future_map):
            name = future_map[future]
            index, count = future.result()
            loaded[name] = index
            loaded[f"{name}_count"] = count
            print(f"  indexed {name} {count}", flush=True)
    return loaded


def _assessor_block(attrs: dict, num: Callable[[Any], float | None]) -> dict:
    return {
        "lrsn": preserve_id(attrs.get("lrsn")),
        "parcelId": preserve_id(attrs.get("parcel_id")),
        "cityTaxCode": city_tax_code(attrs.get("CITY")) or None,
        "subdivision": squash(attrs.get("SUBDIVISION")),
        "propertyType": squash(attrs.get("property_T")),
        "parcelType": squash(attrs.get("PARCEL_TYP")),
        "neighborhood": squash(attrs.get("neighborho")),
        "sqftAssessed": keep_number(attrs.get("SQFT_ASSES"), num),
        "acresAc": keep_number(attrs.get("AC"), num),
        "acresAcc": keep_number(attrs.get("ACc"), num),
        "acreageField": "CALC_ACRE",
    }


def _sale_block(attrs: dict, num: Callable[[Any], float | None]) -> dict:
    return {
        "date": epoch_to_iso(attrs.get("pxfer_date")),
        "price": positive_money(attrs.get("considerat"), num),
        "qualified": None,
        "deedBook": squash(attrs.get("deed_book")) or squash(attrs.get("deed_bK")),
        "deedPage": squash(attrs.get("deed_page")) or squash(attrs.get("deed_pG")),
        "priorDate": epoch_to_iso(attrs.get("pxfer_da_1")),
        "priorPrice": positive_money(attrs.get("consider_1"), num),
    }


def _tax_block(attrs: dict, num: Callable[[Any], float | None]) -> dict:
    return {
        "marketValue": keep_number(attrs.get("total_mark"), num),
        "assessedValue": keep_number(attrs.get("total_asse"), num),
        "taxableValue": None,
        "taxes": None,
        "landMarket": keep_number(attrs.get("land_marke"), num),
        "improvementMarket": keep_number(attrs.get("imp_val"), num),
        "landAssessed": keep_number(attrs.get("land_asses"), num),
        "improvementAssessed": keep_number(attrs.get("imp_assess"), num),
    }


def normalize_williamson_rows(
    raw: list[dict],
    county: dict,
    markets: list[str],
    *,
    empty_feature: Callable,
    rings_to_geometry: Callable,
    centroid_of: Callable,
    plausible_centroid: Callable,
    in_band: Callable,
    num: Callable,
) -> tuple[list[dict], int]:
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed = rings_to_geometry(item.get("geometry"))
        if not geometry:
            dropped += 1
            continue
        center = centroid_of(geometry)
        if not plausible_centroid(center):
            dropped += 1
            continue
        acres = num(attrs.get("CALC_ACRE"))
        if not in_band(acres):
            dropped += 1
            continue
        parcel_id = preserve_id(attrs.get("GISLINK")) or preserve_id(attrs.get("parcel_id"))
        if not parcel_id:
            dropped += 1
            continue
        sale = _sale_block(attrs, num)
        tax = _tax_block(attrs, num)
        feature = empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source=SOURCE,
            owner=squash(attrs.get("owner1")),
            situs=situs_from_attrs(attrs),
            city=None,
            zip_code=None,
            zoning=None,
            sale_price=sale["price"],
            sale_date=sale["date"],
            market_value=tax["marketValue"],
            assessed=tax["assessedValue"],
            mail1=squash(attrs.get("own_street")),
            mail_city=squash(attrs.get("own_city")),
            mail_state=squash(attrs.get("own_state")),
            mail_zip=zip5(attrs.get("own_zip")),
        )
        props = feature["properties"]
        props["ownerName2"] = squash(attrs.get("owner2"))
        props["lastSale"] = sale
        props["tax"] = tax
        props["assessor"] = _assessor_block(attrs, num)
        props["acreageSource"] = "CALC_ACRE"
        props["appraiserUrl"] = INIGO_SEARCH
        props["_cityTaxCode"] = city_tax_code(attrs.get("CITY"))
        previous = by_id.get(parcel_id)
        if previous is None or (props.get("acreage") or 0) > (previous["properties"].get("acreage") or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def apply_williamson_joins(features: list[dict], layers: dict[str, Any]) -> dict[str, Any]:
    zoning_indexes = {
        "FRANKLIN": layers["franklin_zoning"],
        "BRENTWOOD": layers["brentwood_zoning"],
        "FAIRVIEW": layers["fairview_zoning"],
        "SPRING HILL": layers["spring_hill_zoning"],
        "UNINCORPORATED": layers["county_zoning"],
    }
    flu_indexes = {
        "FRANKLIN": layers["franklin_flu"],
        "FAIRVIEW": layers["fairview_flu"],
    }
    by_juris: Counter[str] = Counter()
    zoning_hits: Counter[str] = Counter()
    flu_hits: Counter[str] = Counter()
    how_counts: Counter[str] = Counter()
    limits_disagreements = 0
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        limits_hit = layers["limits"].hit(lon, lat)
        limits_name = (limits_hit or {}).get("properties", {}).get("name")
        city_code = props.pop("_cityTaxCode", "") or (props.get("assessor") or {}).get("cityTaxCode") or ""
        key, how = resolve_jurisdiction(str(city_code), limits_name)
        mapped = CITY_TAX_CODES.get(city_tax_code(city_code))
        if how == "corporate-limits" and mapped and mapped != key and mapped != "UNINCORPORATED":
            limits_disagreements += 1
        how_counts[how] += 1
        by_juris[key] += 1
        prefix = JURISDICTION_PREFIX[key]
        props["jurisdictionCode"] = prefix
        props["jurisdictionPrefix"] = prefix
        props["situsCity"] = JURISDICTION_NAME[key]
        props["zoningSource"] = None
        gaps = jurisdiction_gaps(key, str(city_code), how)
        zone_index = zoning_indexes.get(key)
        if zone_index is None:
            props["zoningCode"] = None
            props["zoningDistrict"] = None
        else:
            zone_hit = zone_index.hit(lon, lat)
            zone_props = (zone_hit or {}).get("properties")
            if zone_props and zone_props.get("code"):
                props["zoningCode"] = zone_props["code"]
                props["zoningDistrict"] = zone_props.get("district") or zone_props["code"]
                props["zoningSource"] = ZONING_SOURCE[key]
                zoning_hits[key] += 1
            else:
                props["zoningCode"] = None
                props["zoningDistrict"] = None
                gaps.append(f"No {JURISDICTION_NAME[key]} zoning polygon contains this centroid.")
        flu_index = flu_indexes.get(key)
        if flu_index is None:
            props["flu"] = None
        else:
            flu_hit = flu_index.hit(lon, lat)
            flu_props = (flu_hit or {}).get("properties")
            if flu_props and flu_props.get("code"):
                props["flu"] = {
                    "code": flu_props["code"],
                    "label": flu_props.get("label") or flu_props["code"],
                    "jurisdiction": flu_props.get("jurisdiction") or prefix,
                    "source": flu_props.get("source"),
                }
                flu_hits[key] += 1
            else:
                props["flu"] = None
                gaps.append(f"No {JURISDICTION_NAME[key]} future-land-use polygon contains this centroid.")
        props["dataGaps"] = gaps
    return {
        "byJurisdiction": dict(by_juris),
        "zoningJoined": dict(zoning_hits),
        "fluJoined": dict(flu_hits),
        "jurisdictionHow": dict(how_counts),
        "limitsDisagreements": limits_disagreements,
        "layerCounts": {
            "corporateLimits": layers.get("limits_count"),
            "countyZoning": layers.get("county_zoning_count"),
            "franklinZoning": layers.get("franklin_zoning_count"),
            "franklinFlu": layers.get("franklin_flu_count"),
            "brentwoodZoning": layers.get("brentwood_zoning_count"),
            "fairviewZoning": layers.get("fairview_zoning_count"),
            "fairviewFlu": layers.get("fairview_flu_count"),
            "springHillZoning": layers.get("spring_hill_zoning_count"),
        },
    }


def williamson_gap_lines(kept: int, source_count: int, dropped: int, stats: dict) -> list[str]:
    zoning = stats.get("zoningJoined") or {}
    flu = stats.get("fluJoined") or {}
    juris = stats.get("byJurisdiction") or {}
    zoning_total = sum(zoning.values())
    flu_total = sum(flu.values())
    collapsed = max(0, source_count - dropped - kept)
    collapse_note = f" {collapsed} extra GISLINK rows collapsed to the larger CALC_ACRE." if collapsed else ""
    return [
        (
            f"Williamson is not Comptroller IMPACT. {kept} parcels kept from IDT/DataPull layer 10 "
            f"(source rows {source_count}, geometry/acreage drops {dropped}) using CALC_ACRE 5–150 inclusive.{collapse_note} "
            f"AC and ACc are secondary assessor acres, not the filter. Query format is Esri JSON (no geoJSON); rings were converted to GeoJSON."
        ),
        (
            "Jurisdiction is Corporate Limits layer 2 when the centroid is inside a city, otherwise the CITY tax code. "
            f"Resolved {juris}. Limits overrode a mapped city code on {stats.get('limitsDisagreements', 0)} parcels. "
            "CITY 000264 and blank codes are not treated as Franklin unless Corporate Limits say so."
        ),
        (
            f"City-only zoning on countywide parcels: zoning joined {zoning_total} ({zoning}); "
            f"FLU joined {flu_total} ({flu}). Franklin FLU is Envision Design Concepts (DCABBREV) inside Franklin only. "
            "Fairview FLU is Fairview 2040 FUT_LU inside Fairview only. "
            "Brentwood, Spring Hill, Nolensville, Thompson's Station, and unincorporated Williamson have no joined FLU."
        ),
        (
            "Zoning REST used: Franklin ZoningWebMercator/9 ZONECLASS, Brentwood AdministrativeAreas/9 Zoning, "
            "Fairview_Zoning_Public Zoning, Spring Hill Zoning_Spring_Hill_view/2 Zone (Williamson parcels only), "
            "unincorporated IDT/DataPull layer 0 ZONES. Overlay layers and the 1988/2013 county zoning archives are not joined. "
            f"Nolensville portal {NOLENSVILLE_PORTAL}. Thompson's Station portal {THOMPSONS_PORTAL}."
        ),
        (
            f"Assessor card is Inigo search ({INIGO_SEARCH}). parcel/{{lrsn}} needs a page CSRF, so appraiserUrl is the search landing. "
            "Owner mailing is the assessor address only. No email or phone enrichment. "
            "Williamson zoning and FLU codes are stored raw and are not in the Orange County multifamily list."
        ),
    ]


def pull_williamson(
    county: dict,
    markets: list[str],
    *,
    fetch_json: Callable,
    empty_feature: Callable,
    rings_to_geometry: Callable,
    centroid_of: Callable,
    plausible_centroid: Callable,
    in_band: Callable,
    num: Callable,
) -> tuple[list[dict], dict]:
    print("  Williamson parcels (HTTP JSON, CALC_ACRE 5–150)", flush=True)
    raw = fetch_layer(
        fetch_json,
        PARCEL_QUERY,
        ACREAGE_WHERE,
        PARCEL_FIELDS,
        batch=60,
        label="parcels",
    )
    features, dropped = normalize_williamson_rows(
        raw,
        county,
        markets,
        empty_feature=empty_feature,
        rings_to_geometry=rings_to_geometry,
        centroid_of=centroid_of,
        plausible_centroid=plausible_centroid,
        in_band=in_band,
        num=num,
    )
    if features:
        lon, lat = features[0]["properties"]["centroid"]
        if not (-87.6 < lon < -86.2 and 35.5 < lat < 36.3):
            raise RuntimeError(f"Williamson centroid {lon},{lat} is outside the county envelope; geometry was not WGS84")
    print(f"  normalized {len(features)} parcels (dropped {dropped})", flush=True)
    if len(features) < 9000:
        raise RuntimeError(f"Williamson kept {len(features)} of {len(raw)} rows. Refusing a thin extract.")
    layers = _load_reference_layers(fetch_json, rings_to_geometry)
    stats = apply_williamson_joins(features, layers)
    stats["sourceCount"] = len(raw)
    stats["dropped"] = dropped
    stats["kept"] = len(features)
    print(
        f"  jurisdiction {stats['byJurisdiction']} zoning {stats['zoningJoined']} flu {stats['fluJoined']}",
        flush=True,
    )
    return features, stats


def _self_check() -> None:
    assert epoch_to_iso(1565568000000) == "2019-08-12"
    assert epoch_to_iso(None) is None
    assert epoch_to_iso(0) is None
    assert situs_from_attrs({"ADDRESS": "  1026 HOLLY TREE GAP RD  "}) == "1026 HOLLY TREE GAP RD"
    assert situs_from_attrs({"ADDRESS": " ", "streetnumber": "10", "streetnumbersfx": " ", "streetname": "MAIN ST"}) == "10 MAIN ST"
    assert squash(" ") is None
    assert resolve_jurisdiction("086", None) == ("BRENTWOOD", "city-tax-code")
    assert resolve_jurisdiction("263967", "BRENTWOOD") == ("BRENTWOOD", "corporate-limits")
    assert resolve_jurisdiction("000264", None) == ("UNINCORPORATED", "unincorporated-fallback")
    assert resolve_jurisdiction("000264", "FRANKLIN") == ("FRANKLIN", "corporate-limits")
    assert resolve_jurisdiction(" ", None)[0] == "UNINCORPORATED"
    assert resolve_jurisdiction("000", "NOLENSVILLE") == ("NOLENSVILLE", "corporate-limits")
    assert split_county_zone("RD- 1 - Rural Development - 1") == ("RD- 1", "RD- 1 - Rural Development - 1")
    assert split_county_zone("College Grove Village") == ("College Grove Village", "College Grove Village")
    code, _district = split_county_zone("SIC - Suburban Infill and Conservation")
    assert code == "SIC"
    nol_gaps = jurisdiction_gaps("NOLENSVILLE", "535", "city-tax-code")
    assert any("nolensvilletn.interactivegis.com" in gap for gap in nol_gaps)
    ths_gaps = jurisdiction_gaps("THOMPSONS STATION", "718", "corporate-limits")
    assert any("thompsons-station.gov" in gap for gap in ths_gaps)
    assert jurisdiction_gaps("FRANKLIN", "000", "corporate-limits")
    fringe = jurisdiction_gaps("UNINCORPORATED", "000264", "unincorporated-fallback")
    assert any("000264" in gap for gap in fringe)
    assert "FRANKLIN" not in CITY_TAX_CODES.get("000264", "")
    # Clockwise exteriors (negative shoelace). The second ring must stay its own polygon.
    outer = [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]
    second = [[2.0, 2.0], [2.0, 3.0], [3.0, 3.0], [3.0, 2.0], [2.0, 2.0]]
    geometry, _acres = esri_rings_to_geometry({"rings": [outer, second]})
    assert geometry and geometry["type"] == "MultiPolygon"
    assert _point_in_feature(2.5, 2.5, {"type": "Feature", "geometry": geometry, "properties": {}})
    hole = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8], [0.2, 0.2]]
    holed, _acres = esri_rings_to_geometry({"rings": [outer, hole]})
    assert holed and holed["type"] == "Polygon"
    assert not _point_in_feature(0.5, 0.5, {"type": "Feature", "geometry": holed, "properties": {}})
    sale = _sale_block(
        {"pxfer_date": 1565568000000, "considerat": 1000000, "deed_book": "7718", "deed_page": "932", "consider_1": 0},
        lambda value: None if value in (None, "") else float(value),
    )
    assert sale["date"] == "2019-08-12"
    assert sale["price"] == 1000000
    assert sale["priorPrice"] is None
    assert sale["deedBook"] == "7718"
    print("williamson enrich self-check ok")


if __name__ == "__main__":
    _self_check()
