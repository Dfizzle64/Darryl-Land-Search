"""Davidson County (Metro Nashville) parcel extract.

Uses Metro GIS Cadastral/Parcels MapServer layer 0. Davidson is not a
Tennessee Comptroller IMPACT county, so this module never calls IMPACT.

NashvilleNext community character (Planning/CCM layer 2) is a spatial join.
It is preferred future policy, not a zoning entitlement.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable
from urllib.parse import quote
from zoneinfo import ZoneInfo

from parcel_geometry import esri_rings_to_geojson, point_in_geometry, polygon_parts, representative_point

PARCEL_QUERY = "https://maps.nashville.gov/arcgis/rest/services/Cadastral/Parcels/MapServer/0/query"
CCM_QUERY = "https://maps.nashville.gov/arcgis/rest/services/Planning/CCM/MapServer/2/query"
OVERLAY_QUERY = "https://maps.nashville.gov/arcgis/rest/services/Zoning/ZoningOverlayDistricts/MapServer/0/query"
JURISDICTION_QUERY = "https://maps.nashville.gov/arcgis/rest/services/Boundaries/Jurisdictions/MapServer/2/query"
METRO_ZONING_META = "https://maps.nashville.gov/arcgis/rest/services/Zoning/Zoning/MapServer"
GOODLETTSVILLE_ZONING = (
    "https://services8.arcgis.com/qSbT66zM7qttH0fv/arcgis/rest/services/ZONINGARGISMAP/FeatureServer/2/query"
)
GOODLETTSVILLE_OVERLAYS = (
    (
        "https://services8.arcgis.com/qSbT66zM7qttH0fv/arcgis/rest/services/ZONINGARGISMAP/FeatureServer/1/query",
        "INT Interchange Overlay",
    ),
    (
        "https://services8.arcgis.com/qSbT66zM7qttH0fv/arcgis/rest/services/ZONINGARGISMAP/FeatureServer/3/query",
        "CCO Commercial Core Overlay",
    ),
)
METRO_JURISDICTION = "Metro Nashville"
SATELLITE_NAMES = {
    "CITY OF BELLE MEADE": "Belle Meade",
    "CITY OF BERRY HILL": "Berry Hill",
    "CITY OF FOREST HILLS": "Forest Hills",
    "CITY OF GOODLETTSVILLE": "Goodlettsville",
    "CITY OF OAK HILL": "Oak Hill",
    "CITY OF RIDGETOP": "Ridgetop",
}
ZONING_GAP_CITIES = {"Belle Meade", "Berry Hill", "Forest Hills", "Oak Hill", "Ridgetop"}
ZZ_TOKEN = re.compile(r"^\dZZ$", re.IGNORECASE)
PARCEL_VIEWER = "https://maps.nashville.gov/ParcelViewer/"
WEBPRO_SEARCH = "https://portal.padctn.org/OFS/WP/PropertySearch/QuickSearch"
CCM_SOURCE = "nashville-next-ccm"
SOURCE_ID = "tn-metro-davidson-parcels"
CENTRAL = ZoneInfo("America/Chicago")
CELL_DEG = 0.05

PARCEL_FIELDS = [
    "OBJECTID",
    "APN",
    "STANPAR",
    "ParID",
    "Owner",
    "OwnAddr1",
    "OwnAddr2",
    "OwnAddr3",
    "OwnCity",
    "OwnState",
    "OwnZip",
    "OwnCountry",
    "PropAddr",
    "PropHouse",
    "PropStreet",
    "PropSuite",
    "PropCity",
    "PropState",
    "PropZip",
    "PropDate",
    "OwnDate",
    "SalePrice",
    "ValidSale",
    "SaleCode",
    "SaleSrc",
    "Acres",
    "DeededAcreage",
    "LandAppr",
    "ImprAppr",
    "TotlAppr",
    "LandAssd",
    "ImprAssd",
    "TotlAssd",
    "Zoning",
    "LUCode",
    "LUDesc",
]

GAPS = [
    "Davidson County is not a Tennessee Comptroller IMPACT county. Polygons, owner, mailing, situs, sale, appraisal, and the parcel Zoning attribute come from Metro GIS Cadastral/Parcels MapServer layer 0 (APN). No IMPACT assessment feed was used. Authoritative record cards are on Davidson WebPro.",
    "Planning/CCM layer 2 PolicyCode and PolicyDesc are NashvilleNext community character policy, joined by polygon intersection. That is preferred future policy guidance, not a zoning entitlement and not Future Land Use. Parcels that cross a policy boundary keep the additional policies on the label.",
    "PropDate is the layer alias Property Date and OwnDate is Owner Instrument Date. The sale date is that best-available proxy, not a guaranteed last-sale date. Confirm history in WebPro. SaleCode and SaleSrc are copied through; a blank ValidSale stays blank and is not treated as a qualified sale.",
    "Outside satellite cities, displayed zoning is the Metro parcel Zoning attribute with *ZZ placeholder tokens removed. *ZZ is not a Metro Zoning Ordinance district. Metro Zoning/Zoning is rechecked at ingest and is not required for this extract.",
    "Satellite cities (Belle Meade, Berry Hill, Forest Hills, Goodlettsville, Oak Hill, Ridgetop) come from Boundaries/Jurisdictions MapServer layer 2 Name. The most local code wins. Goodlettsville zoning is ZONINGARGISMAP FeatureServer layer 2 ZONECLASS / ZONEDESC, joined only to the Davidson portion of the city. Belle Meade, Berry Hill, Forest Hills, Oak Hill, and Ridgetop have no public zoning FeatureServer, so their city zoning stays blank instead of copying the Metro parcel attribute or *ZZ. Satellite-city future land use is a gap: NashvilleNext CCM is Metro guidance and is cleared inside satellite limits.",
    "Zoning overlays from ZoningOverlayDistricts are supplemental constraints (historic, urban design, airport impact, and similar), not the base zone.",
    "Median household income and FDOT AADT are not joined. Those sidecars are Florida extracts, so Davidson stays unknown.",
    "DeededAcreage is kept when the layer sends it. StatedArea is not converted, because the layer does not document its unit.",
]


def davidson_spec() -> dict:
    return {
        "kind": "arcgis",
        "profile": "davidson",
        "url": PARCEL_QUERY,
        "where": "Acres >= 5 AND Acres <= 150",
        "outFields": PARCEL_FIELDS,
        "batch": 60,
        "idField": "APN",
        "idFallbacks": ["STANPAR", "ParID"],
        "acresField": "Acres",
        "ownerField": "Owner",
        "situsField": "PropAddr",
        "cityField": "PropCity",
        "zipField": "PropZip",
        "zoningField": "Zoning",
        "salePriceField": "SalePrice",
        "marketValueField": "TotlAppr",
        "assessedField": "TotlAssd",
        "mail1Field": "OwnAddr1",
        "mailCityField": "OwnCity",
        "mailStateField": "OwnState",
        "mailZipField": "OwnZip",
        "source": SOURCE_ID,
        "coverage": "complete-gte-5ac",
        "gaps": list(GAPS),
        "patch": patch_davidson_feature,
    }


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def central_date(value: Any) -> str | None:
    """ArcGIS epoch to the Central Time calendar date (ISO 8601)."""
    parsed = _num(value)
    if parsed is None or parsed <= 0:
        return None
    seconds = parsed / 1000.0 if parsed > 10_000_000_000 else parsed
    if seconds < 0 or seconds > 4_000_000_000:
        return None
    try:
        moment = datetime.fromtimestamp(seconds, CENTRAL)
    except (OverflowError, OSError, ValueError):
        return None
    return moment.date().isoformat()


def patch_davidson_feature(feature: dict, attrs: dict) -> None:
    props = feature["properties"]
    situs = _clean(attrs.get("PropAddr"))
    if not situs:
        situs = " ".join(
            part
            for part in (
                _clean(attrs.get("PropHouse")),
                _clean(attrs.get("PropStreet")),
                _clean(attrs.get("PropSuite")),
            )
            if part
        ) or None
    props["situsAddress"] = situs
    owner = _clean(attrs.get("Owner"))
    if owner:
        props["ownerName"] = owner
    zoning = _clean(attrs.get("Zoning"))
    props["zoningCode"] = zoning
    props["zoningDistrict"] = zoning
    props["parcelZoning"] = zoning
    props["zoningSource"] = "metro-parcel-attribute"
    props["jurisdictionCode"] = METRO_JURISDICTION

    mail_extra = [
        part
        for part in (_clean(attrs.get("OwnAddr2")), _clean(attrs.get("OwnAddr3")))
        if part
    ]
    country = _clean(attrs.get("OwnCountry"))
    if country and country.upper() not in {"US", "USA", "UNITED STATES"}:
        mail_extra.append(country)
    props["mailingAddress"]["line1"] = _clean(attrs.get("OwnAddr1"))
    props["mailingAddress"]["line2"] = "\n".join(mail_extra) or None

    prop_date = central_date(attrs.get("PropDate"))
    own_date = central_date(attrs.get("OwnDate"))
    notes: list[str] = []
    if own_date and prop_date and own_date != prop_date:
        notes.append(f"Owner instrument {own_date}")
    valid = _clean(attrs.get("ValidSale"))
    sale_code = _clean(attrs.get("SaleCode"))
    sale_src = _clean(attrs.get("SaleSrc"))
    if valid:
        notes.append(f"ValidSale {valid}")
    if sale_code:
        notes.append(f"SaleCode {sale_code}")
    if sale_src:
        notes.append(f"SaleSrc {sale_src}")
    props["lastSale"]["date"] = prop_date or own_date
    props["lastSale"]["qualified"] = " · ".join(notes) or None

    tax = props["tax"]
    tax["landAppraised"] = _num(attrs.get("LandAppr"))
    tax["improvementAppraised"] = _num(attrs.get("ImprAppr"))
    tax["landAssessed"] = _num(attrs.get("LandAssd"))
    tax["improvementAssessed"] = _num(attrs.get("ImprAssd"))

    stanpar = _clean(attrs.get("STANPAR"))
    par_id = _clean(attrs.get("ParID"))
    if stanpar:
        props["stanpar"] = stanpar
    if par_id:
        props["parId"] = par_id
    deeded = _num(attrs.get("DeededAcreage"))
    if deeded is not None and deeded > 0:
        props["deededAcreage"] = round(deeded, 4)
    land_code = _clean(attrs.get("LUCode"))
    land_desc = _clean(attrs.get("LUDesc"))
    if land_code and land_desc:
        props["landUse"] = f"{land_code} · {land_desc}"
    elif land_desc or land_code:
        props["landUse"] = land_desc or land_code

    props["appraiserUrl"] = f"{PARCEL_VIEWER}?parcelID={quote(str(props['parcelId']))}"
    props["flu"] = None


def _fetch_ids(fetch_json: Callable, url: str, where: str) -> list[int]:
    data = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:300])
    return [int(item) for item in (data.get("objectIds") or [])]


def _fetch_batch(fetch_json: Callable, url: str, ids: list[int], out_fields: list[str]) -> list[dict]:
    data = fetch_json(
        url,
        {
            "objectIds": ",".join(str(item) for item in ids),
            "outFields": ",".join(out_fields),
            "returnGeometry": "true",
            "outSR": "4326",
            "maxAllowableOffset": "0.00015",
            "geometryPrecision": "5",
            "f": "json",
        },
        timeout=180,
    )
    if data.get("error"):
        if len(ids) > 20:
            mid = len(ids) // 2
            return _fetch_batch(fetch_json, url, ids[:mid], out_fields) + _fetch_batch(
                fetch_json, url, ids[mid:], out_fields
            )
        raise RuntimeError(str(data["error"])[:300])
    return data.get("features") or []


def _fetch_features(
    fetch_json: Callable,
    url: str,
    where: str,
    out_fields: list[str],
    *,
    batch: int,
    label: str,
) -> list[dict]:
    ids = _fetch_ids(fetch_json, url, where)
    print(f"  {label} features {len(ids)}", flush=True)
    if not ids:
        return []
    chunks = [ids[start : start + batch] for start in range(0, len(ids), batch)]
    features: list[dict] = []
    workers = 4 if len(chunks) > 4 else 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_fetch_batch, fetch_json, url, chunk, out_fields) for chunk in chunks]
        done = 0
        for future in as_completed(futures):
            features.extend(future.result())
            done += 1
            if done == 1 or done == len(chunks) or done % 25 == 0:
                print(f"    {label} batches {done}/{len(chunks)}", flush=True)
    return features


def _bbox(geometry: dict) -> tuple[float, float, float, float] | None:
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


def _intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


class _Grid:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], list[dict]] = defaultdict(list)

    def add(self, geometry: dict, payload: dict) -> None:
        box = _bbox(geometry)
        if not box:
            return
        item = {
            "bbox": box,
            "geometry": geometry,
            "payload": payload,
            "rep": representative_point(geometry),
        }
        ix0 = math.floor(box[0] / CELL_DEG)
        ix1 = math.floor(box[2] / CELL_DEG)
        iy0 = math.floor(box[1] / CELL_DEG)
        iy1 = math.floor(box[3] / CELL_DEG)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.cells[(ix, iy)].append(item)

    def search(self, box: tuple[float, float, float, float]) -> list[dict]:
        ix0 = math.floor(box[0] / CELL_DEG)
        ix1 = math.floor(box[2] / CELL_DEG)
        iy0 = math.floor(box[1] / CELL_DEG)
        iy1 = math.floor(box[3] / CELL_DEG)
        seen: set[int] = set()
        found: list[dict] = []
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                for item in self.cells.get((ix, iy), []):
                    marker = id(item)
                    if marker in seen:
                        continue
                    seen.add(marker)
                    if _intersects(item["bbox"], box):
                        found.append(item)
        return found


def _sample_points(geometry: dict, centroid: list[float] | None) -> list[tuple[float, float, int]]:
    points: list[tuple[float, float, int]] = []
    if centroid and len(centroid) == 2:
        points.append((float(centroid[0]), float(centroid[1]), 4))
    for poly in polygon_parts(geometry):
        if not poly or not poly[0]:
            continue
        outer = poly[0]
        step = max(1, len(outer) // 18)
        for x, y in outer[::step]:
            points.append((float(x), float(y), 1))
    return points


def _policy_label(primary: dict, others: list[dict]) -> str:
    label = primary.get("desc") or primary.get("code") or "Community character"
    transect = primary.get("transect")
    if transect and transect not in label:
        label = f"{label} · {transect}"
    if others:
        extra = ", ".join(
            f"{item.get('desc') or item['code']} ({item['code']})" for item in others[:5] if item.get("code")
        )
        if extra:
            label = f"{label}; also {extra}"
    return label


def join_community_character(features: list[dict], fetch_json: Callable) -> int:
    raw = _fetch_features(
        fetch_json,
        CCM_QUERY,
        "1=1",
        ["PolicyCode", "PolicyDesc", "Transect", "DateAdopted"],
        batch=120,
        label="CCM",
    )
    grid = _Grid()
    kept = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        code = _clean(attrs.get("PolicyCode"))
        if not code:
            continue
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [], tol=0.00008)
        if not geometry:
            continue
        grid.add(
            geometry,
            {
                "code": code,
                "desc": _clean(attrs.get("PolicyDesc")),
                "transect": _clean(attrs.get("Transect")),
                "adopted": _clean(attrs.get("DateAdopted")),
            },
        )
        kept += 1
    print(f"  CCM polygons indexed {kept}", flush=True)
    matched = 0
    for index, feature in enumerate(features, start=1):
        geometry = feature.get("geometry")
        box = _bbox(geometry) if geometry else None
        if not box:
            continue
        scores: dict[str, dict] = {}
        samples = _sample_points(geometry, feature["properties"].get("centroid"))
        for item in grid.search(box):
            payload = item["payload"]
            score = 0
            item_box = item["bbox"]
            for x, y, weight in samples:
                if x < item_box[0] or x > item_box[2] or y < item_box[1] or y > item_box[3]:
                    continue
                if point_in_geometry(x, y, item["geometry"]):
                    score += weight
            rep = item["rep"]
            if rep and point_in_geometry(rep[0], rep[1], geometry):
                score += 3
            if score <= 0:
                continue
            slot = scores.get(payload["code"])
            if slot is None or score > slot["score"]:
                scores[payload["code"]] = {**payload, "score": score}
        if not scores:
            feature["properties"]["flu"] = None
            continue
        ordered = sorted(scores.values(), key=lambda row: (-row["score"], row["code"]))
        primary = ordered[0]
        feature["properties"]["flu"] = {
            "code": primary["code"],
            "label": _policy_label(primary, ordered[1:]),
            "jurisdiction": "NashvilleNext",
            "source": CCM_SOURCE,
        }
        matched += 1
        if index == 1 or index == len(features) or index % 2000 == 0:
            print(f"    CCM join {index}/{len(features)}", flush=True)
    return matched


def join_overlays(features: list[dict], fetch_json: Callable) -> int:
    raw = _fetch_features(
        fetch_json,
        OVERLAY_QUERY,
        "1=1",
        ["ZONE_DESC", "NAME"],
        batch=150,
        label="overlays",
    )
    grid = _Grid()
    for item in raw:
        attrs = item.get("attributes") or {}
        kind = _clean(attrs.get("ZONE_DESC"))
        if not kind:
            continue
        name = _clean(attrs.get("NAME"))
        label = f"{kind} — {name}" if name else kind
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [], tol=0.00008)
        if not geometry:
            continue
        grid.add(geometry, {"label": label})
    matched = 0
    for feature in features:
        geometry = feature.get("geometry")
        box = _bbox(geometry) if geometry else None
        if not box:
            continue
        labels: list[str] = []
        centroid = feature["properties"].get("centroid") or [None, None]
        for item in grid.search(box):
            hit = False
            if centroid[0] is not None and point_in_geometry(float(centroid[0]), float(centroid[1]), item["geometry"]):
                hit = True
            elif item["rep"] and point_in_geometry(item["rep"][0], item["rep"][1], geometry):
                hit = True
            else:
                for poly in polygon_parts(geometry):
                    if poly and poly[0] and point_in_geometry(poly[0][0][0], poly[0][0][1], item["geometry"]):
                        hit = True
                        break
            if hit:
                label = item["payload"]["label"]
                if label not in labels:
                    labels.append(label)
        feature["properties"]["zoningOverlays"] = labels[:8] or None
        if labels:
            matched += 1
    return matched


def _metro_display_zoning(raw: str | None) -> str | None:
    if not raw:
        return None
    kept = [part.strip() for part in re.split(r"[,;/]", raw) if part.strip() and not ZZ_TOKEN.match(part.strip())]
    return ", ".join(kept) or None


def _fetch_polygons(fetch_json: Callable, url: str, fields: str) -> list[dict]:
    """Read a small polygon layer. Falls back without generalization if the server rejects it."""
    base = {
        "where": "1=1",
        "outFields": fields,
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
    }
    data = fetch_json(url, {**base, "maxAllowableOffset": "0.00008", "geometryPrecision": "5"}, timeout=120)
    if data.get("error"):
        data = fetch_json(url, base, timeout=120)
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:300])
    features = list(data.get("features") or [])
    offset = len(features)
    while data.get("exceededTransferLimit"):
        page = fetch_json(url, {**base, "resultOffset": str(offset), "resultRecordCount": "500"}, timeout=120)
        if page.get("error"):
            raise RuntimeError(str(page["error"])[:300])
        batch = page.get("features") or []
        if not batch:
            break
        features.extend(batch)
        offset += len(batch)
        data = page
    return features


def _city_at_point(x: float, y: float, cities: list[dict]) -> str | None:
    """A parcel is inside a satellite city when its representative point is inside that polygon."""
    found: list[str] = []
    for city in cities:
        box = city["bbox"]
        if x < box[0] or x > box[2] or y < box[1] or y > box[3]:
            continue
        if point_in_geometry(x, y, city["geometry"]) and city["name"] not in found:
            found.append(city["name"])
    return found[0] if found else None


def _city_of(geometry: dict, cities: list[dict], centroid: list | None) -> str | None:
    if centroid and len(centroid) == 2:
        try:
            return _city_at_point(float(centroid[0]), float(centroid[1]), cities)
        except (TypeError, ValueError):
            return None
    rep = representative_point(geometry)
    if not rep:
        return None
    return _city_at_point(rep[0], rep[1], cities)


def _load_satellites(fetch_json: Callable) -> list[dict]:
    raw = _fetch_polygons(fetch_json, JURISDICTION_QUERY, "Name")
    cities: list[dict] = []
    for item in raw:
        name = SATELLITE_NAMES.get(_clean((item.get("attributes") or {}).get("Name")) or "")
        if not name:
            continue
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [], tol=0.00005)
        box = _bbox(geometry) if geometry else None
        if not geometry or not box:
            continue
        cities.append({"name": name, "geometry": geometry, "bbox": box})
    if not cities:
        raise RuntimeError("Satellite City layer returned no Name polygons")
    return cities


def _load_goodlettsville_zones(fetch_json: Callable) -> _Grid:
    raw = _fetch_polygons(fetch_json, GOODLETTSVILLE_ZONING, "ZONECLASS,ZONEDESC")
    grid = _Grid()
    for item in raw:
        attrs = item.get("attributes") or {}
        code = _clean(attrs.get("ZONECLASS"))
        if not code:
            continue
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [], tol=0.00008)
        if not geometry:
            continue
        grid.add(geometry, {"code": code, "desc": _clean(attrs.get("ZONEDESC"))})
    return grid


def _goodlettsville_zone(geometry: dict, grid: _Grid, centroid: list | None) -> dict | None:
    point: tuple[float, float] | None = None
    if centroid and len(centroid) == 2:
        try:
            point = (float(centroid[0]), float(centroid[1]))
        except (TypeError, ValueError):
            point = None
    if point is None:
        point = representative_point(geometry)
    if not point:
        return None
    x, y = point
    best: dict | None = None
    best_area: float | None = None
    for item in grid.search((x, y, x, y)):
        if not point_in_geometry(x, y, item["geometry"]):
            continue
        box = item["bbox"]
        area = (box[2] - box[0]) * (box[3] - box[1])
        if best is None or best_area is None or area < best_area:
            best = item["payload"]
            best_area = area
    return best


def _probe_metro_zoning(fetch_json: Callable) -> str:
    try:
        data = fetch_json(METRO_ZONING_META, {"f": "pjson"}, timeout=40)
    except Exception as exc:  # noqa: BLE001
        return (
            f"Metro Zoning/Zoning MapServer was not readable ({exc}). "
            "The parcel Zoning attribute remains the Metro source. This extract does not depend on that service."
        )
    error = data.get("error") or {}
    if error:
        code = error.get("code")
        message = str(error.get("message") or "")[:160]
        return (
            f"Metro Zoning/Zoning MapServer returned ArcGIS code {code} at ingest ({message}). "
            "Outside satellite cities the parcel Zoning attribute is the zoning source. "
            "The 500 service is not a hard dependency."
        )
    return (
        "Metro Zoning/Zoning MapServer responded, but this extract still prefers the parcel Zoning attribute "
        "and does not replace it with that service."
    )


def apply_municipalities(features: list[dict], fetch_json: Callable) -> list[str]:
    """Resolve satellite cities, then keep the most local zoning that public REST can support."""
    notes: list[str] = []
    cities = _load_satellites(fetch_json)
    print(f"  satellite polygons {len(cities)}", flush=True)
    zones = _load_goodlettsville_zones(fetch_json)
    print("  Goodlettsville zoning indexed", flush=True)
    for feature in features:
        props = feature["properties"]
        if not props.get("parcelZoning"):
            props["parcelZoning"] = props.get("zoningCode")
        geometry = feature.get("geometry")
        centroid = props.get("centroid")
        city = _city_of(geometry, cities, centroid) if geometry else None
        if city:
            props["jurisdictionCode"] = city
            props["flu"] = None
            props["zoningOverlays"] = None
            props["zoningDescription"] = None
            props["metroZoningPolygon"] = None
            if city == "Goodlettsville":
                hit = _goodlettsville_zone(geometry, zones, centroid) if geometry else None
                if hit:
                    props["zoningCode"] = hit["code"]
                    props["zoningDistrict"] = hit["code"]
                    props["zoningDescription"] = hit.get("desc")
                    props["zoningSource"] = "goodlettsville-zoningargismap-2"
                else:
                    props["zoningCode"] = None
                    props["zoningDistrict"] = None
                    props["zoningSource"] = "goodlettsville-unmatched"
            else:
                props["zoningCode"] = None
                props["zoningDistrict"] = None
                props["zoningSource"] = "satellite-zoning-rest-gap"
        else:
            props["jurisdictionCode"] = METRO_JURISDICTION
            displayed = _metro_display_zoning(props.get("parcelZoning"))
            props["zoningCode"] = displayed
            props["zoningDistrict"] = displayed
            props["zoningDescription"] = None
            props["zoningSource"] = "metro-parcel-attribute"
    overlay_hits = _join_goodlettsville_overlays(features, fetch_json)
    notes.append(_probe_metro_zoning(fetch_json))
    if overlay_hits:
        notes.append(
            f"Goodlettsville interchange and commercial-core overlays intersect {overlay_hits} Davidson parcels. They are supplemental, not the base zone."
        )
    return notes


def _join_goodlettsville_overlays(features: list[dict], fetch_json: Callable) -> int:
    targets = [feature for feature in features if feature["properties"].get("jurisdictionCode") == "Goodlettsville"]
    if not targets:
        return 0
    grids: list[tuple[str, _Grid]] = []
    for url, label in GOODLETTSVILLE_OVERLAYS:
        try:
            raw = _fetch_polygons(fetch_json, url, "OBJECTID")
        except Exception as exc:  # noqa: BLE001
            print(f"  Goodlettsville overlay skipped {label}: {exc}", flush=True)
            continue
        grid = _Grid()
        for item in raw:
            geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [], tol=0.00008)
            if geometry:
                grid.add(geometry, {"label": label})
        grids.append((label, grid))
    matched = 0
    for feature in targets:
        geometry = feature.get("geometry")
        box = _bbox(geometry) if geometry else None
        if not box:
            continue
        labels: list[str] = []
        centroid = (feature["properties"].get("centroid") or [None, None])
        for _label, grid in grids:
            for item in grid.search(box):
                hit = centroid[0] is not None and point_in_geometry(float(centroid[0]), float(centroid[1]), item["geometry"])
                if not hit and item["rep"] and geometry and point_in_geometry(item["rep"][0], item["rep"][1], geometry):
                    hit = True
                if hit and item["payload"]["label"] not in labels:
                    labels.append(item["payload"]["label"])
        if labels:
            feature["properties"]["zoningOverlays"] = labels
            matched += 1
    return matched


def davidson_runtime_notes(features: list[dict]) -> list[str]:
    total = len(features)
    by_city: dict[str, int] = defaultdict(int)
    goodlettsville_zoned = 0
    ccm = 0
    metro_overlays = 0
    for feature in features:
        props = feature["properties"]
        city = props.get("jurisdictionCode") or METRO_JURISDICTION
        by_city[city] += 1
        if city == "Goodlettsville" and props.get("zoningSource") == "goodlettsville-zoningargismap-2":
            goodlettsville_zoned += 1
        if (props.get("flu") or {}).get("source") == CCM_SOURCE:
            ccm += 1
        if city == METRO_JURISDICTION and props.get("zoningOverlays"):
            metro_overlays += 1
    city_bits = ", ".join(f"{name} {by_city[name]}" for name in sorted(by_city) if name != METRO_JURISDICTION)
    return [
        f"Satellite City join on the 5–150 acre extract: {METRO_JURISDICTION} {by_city[METRO_JURISDICTION]}"
        + (f"; {city_bits}" if city_bits else "")
        + f" of {total}.",
        f"Goodlettsville ZONECLASS matched {goodlettsville_zoned} of {by_city['Goodlettsville']} Davidson parcels in that city.",
        f"NashvilleNext CCM stays on {ccm} Metro parcels. Satellite parcels are blank: no public city FLU layer, and CCM is not their comprehensive plan.",
        f"Metro zoning overlays remain on {metro_overlays} parcels outside satellite cities. They do not replace the parcel Zoning attribute.",
    ]


def rebuild_davidson_gaps(features: list[dict], *, source_count: int | None, extra: list[str]) -> list[str]:
    gaps = list(GAPS)
    if source_count and source_count != len(features):
        gaps.insert(
            0,
            f"{source_count} source rows collapsed to {len(features)} parcel ids (duplicate ids, stacked units, or rings that failed the WGS84 check). The acreage query covered the county.",
        )
    return [*gaps, *davidson_runtime_notes(features), *extra]


def enrich_davidson(features: list[dict], fetch_json: Callable) -> list[str]:
    notes: list[str] = []
    try:
        join_community_character(features, fetch_json)
    except Exception as exc:  # noqa: BLE001
        notes.append(
            f"NashvilleNext CCM spatial join failed ({exc}). Community character was left blank rather than invented."
        )
    try:
        join_overlays(features, fetch_json)
    except Exception as exc:  # noqa: BLE001
        notes.append(
            f"Zoning overlay join failed ({exc}). Base zoning remains the parcel Zoning attribute only."
        )
    # Satellite resolution runs after CCM and Metro overlays so city parcels can drop both.
    notes.extend(apply_municipalities(features, fetch_json))
    return notes
