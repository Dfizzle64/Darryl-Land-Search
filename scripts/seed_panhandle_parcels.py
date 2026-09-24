#!/usr/bin/env python3
"""Seed the Florida panhandle shelf (5.0–150.0 acres) from public county and city GIS.

Wire order: Bay (12005) → Okaloosa (12091) → Walton (12131) → Escambia (12033) → Santa Rosa (12113).

Field maps follow the 2026-09-23 panhandle card. City zoning and FLU replace county
districts inside city layers. The FGDL statewide "Zoning" service
(services5.arcgis.com/GcvM6vDlR2gM4x31) is rejected — it is not Destin.

  python3 scripts/seed_panhandle_parcels.py
  python3 scripts/seed_panhandle_parcels.py --county Bay
  python3 scripts/seed_panhandle_parcels.py --refresh

No phone numbers or email addresses are requested or stored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

from seed_market_parcels import (
    CATALOG_PATH,
    COUNTY_DIR,
    clean,
    county_row,
    count_where,
    empty_feature,
    fetch_by_ids,
    fetch_json,
    fetch_object_ids,
    in_band,
    num,
    rebuild_indexes,
    centroid_of,
    plausible_centroid,
    simplify_ring,
    write_tiles,
    zip_str,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "panhandle-parcel-sources.json"
CACHE_DIR = Path("/tmp/dls-panhandle/raw")

WIRE_ORDER = ("12005", "12091", "12131", "12033", "12113")

# Wrong geography / wrong purpose. Never queried.
REJECTED = [
    {
        "url": "https://services5.arcgis.com/GcvM6vDlR2gM4x31/arcgis/rest/services/Zoning/FeatureServer",
        "status": "wrong-geography",
        "reason": (
            "FGDL statewide Albers parcel/tax layer titled Zoning. Not Destin city zoning. "
            "Rejected 2026-09-23."
        ),
    },
    {
        "name": "Monroe County AGOL twin titled Walton County Tax Parcels",
        "status": "wrong-geography",
        "reason": "Unrelated web-map twin. Not a Walton County property-appraiser source.",
    },
]

PANHANDLE_BOX = (-88.05, 29.75, -85.05, 31.15)
COUNTY_BOX = {
    "12005": (-86.45, 29.85, -85.15, 30.75),
    "12091": (-86.98, 30.25, -86.25, 31.08),
    "12131": (-86.55, 30.18, -85.70, 31.05),
    "12033": (-87.75, 30.15, -86.80, 31.08),
    "12113": (-87.45, 30.25, -86.65, 31.08),
}

BAY_SUB = {
    "1": "Bay County",
    "2": "Callaway",
    "3": "Lynn Haven",
    "4": "Mexico Beach",
    "5": "Panama City",
    "6": "Panama City Beach",
}

PENSACOLA_ZONING_URL = "https://gis.cityofpensacola.com/arcgis/rest/services/Planning/Zoning/MapServer"

LAYERS = {
    "bay_parcels": "https://gis.baycountyfl.gov/arcgis/rest/services/Hosted/Parcels/FeatureServer/0",
    "bay_zoning": "https://gis.baycountyfl.gov/arcgis/rest/services/LandUsePlanning/MapServer/1",
    "bay_flu": "https://gis.baycountyfl.gov/arcgis/rest/services/LandUsePlanning/MapServer/2",
    "pcb_zoning": "https://services7.arcgis.com/HMHYRsYOvuxpp8zD/arcgis/rest/services/Land_Use_and_Zoning/FeatureServer/47",
    "pcb_flu": "https://services7.arcgis.com/HMHYRsYOvuxpp8zD/arcgis/rest/services/Land_Use_and_Zoning/FeatureServer/49",
    "okaloosa_parcels": "https://okgis.myokaloosa.com/arcgis/rest/services/internet_webgis/MapServer/17",
    "okaloosa_zoning": "https://okgis.myokaloosa.com/arcgis/rest/services/internet_webgis/MapServer/515",
    "okaloosa_flu": "https://okgis.myokaloosa.com/arcgis/rest/services/internet_webgis/MapServer/44",
    "destin_zoning": "https://services9.arcgis.com/pzsl4efLIySC22jh/arcgis/rest/services/Zoning_JulyB_WFL1/FeatureServer/0",
    "destin_flu": "https://services9.arcgis.com/pzsl4efLIySC22jh/arcgis/rest/services/LandUse_DND25_WFL1/FeatureServer/2",
    "fwb_zoning": "https://gis.fwb.org/arcgis/rest/services/Maps/Zoning/MapServer/0",
    "fwb_flu": "https://gis.fwb.org/arcgis/rest/services/Maps/FLU/MapServer/0",
    "walton_parcels": "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/arcgis/rest/services/EnerGov/FeatureServer/4",
    "walton_zoning": "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/arcgis/rest/services/EnerGov/FeatureServer/19",
    "walton_flu": "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/arcgis/rest/services/EnerGov/FeatureServer/15",
    "walton_muni": "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/ArcGIS/rest/services/CitizenServe/FeatureServer/40",
    "dfs_zoning": "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/arcgis/rest/services/WeeklyUpdatesDFS/FeatureServer/7",
    "dfs_flu": "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/arcgis/rest/services/WeeklyUpdatesDFS/FeatureServer/6",
    "freeport_zoning": "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/arcgis/rest/services/WeeklyUpdatesFreeport/FeatureServer/7",
    "freeport_flu": "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/arcgis/rest/services/WeeklyUpdatesFreeport/FeatureServer/6",
    "paxton_flu": "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/arcgis/rest/services/WeeklyUpdatesPaxton/FeatureServer/6",
    "escambia_parcels": "https://gismaps.myescambia.com/arcgis/rest/services/Individual_Layers/parcels/MapServer/0",
    "escambia_zoning": "https://gismaps.myescambia.com/arcgis/rest/services/AccelaMain/MapServer/20",
    "escambia_flu": "https://gismaps.myescambia.com/arcgis/rest/services/AccelaMain/MapServer/22",
    "santarosa_parcels": "https://cloud.santarosa.fl.gov/arcgis/rest/services/santarosa/SRC_Basemap_Districts_Overlay/MapServer/1",
    "santarosa_zoning": "https://cloud.santarosa.fl.gov/arcgis/rest/services/Hosted/ZONE/FeatureServer/0",
    "santarosa_flu": "https://cloud.santarosa.fl.gov/arcgis/rest/services/Hosted/OpenDataFlum/FeatureServer/0",
    "milton_zoning": "https://cloud.santarosa.fl.gov/arcgis/rest/services/Hosted/City_of_Milton_Zoning/FeatureServer/0",
    "gulfbreeze_zoning": "https://cloud.santarosa.fl.gov/arcgis/rest/services/Hosted/Gulf_Breeze_Zoning/FeatureServer/0",
    "jay_zoning": "https://cloud.santarosa.fl.gov/arcgis/rest/services/Hosted/TownOfJayZoning/FeatureServer/0",
}

ADJACENT_GAP = (
    "Not inventoried this pass: Leon (12073), Gulf (12045), Franklin (12037), Jackson (12063), "
    "Holmes (12059), Washington (12133), Calhoun (12013), Gadsden (12039), Jefferson (12065), "
    "Wakulla (12129), Liberty (12077)."
)


def assert_allowed(url: str) -> None:
    lowered = url.lower()
    if "gcvm6vdlr2gm4x31" in lowered or "services5.arcgis.com/gcvm6vdlr2gm4x31" in lowered:
        raise RuntimeError(f"Rejected wrong-geography endpoint: {url}")


def query_url(layer: str) -> str:
    assert_allowed(layer)
    return layer if layer.rstrip("/").endswith("/query") else layer.rstrip("/") + "/query"


def code_text(value: object) -> str | None:
    if value is None or value is False:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if float(value).is_integer():
            return str(int(value))
        return str(value)
    text = str(value).strip()
    return text or None


def norm_id(value: object) -> str | None:
    text = clean(value)
    if not text:
        return None
    return "".join(text.upper().split())


def parse_sale_date(value: object) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)) or float(value) <= 0:
            return None
        iv = int(value)
        text = str(iv)
        if len(text) == 8 and text[:2] in {"19", "20"}:
            year, month, day = int(text[:4]), int(text[4:6]), int(text[6:8])
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
        return None
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return None


def money(value: object, *, drop_nonpositive: bool = False) -> float | None:
    parsed = num(value)
    if parsed is None:
        return None
    if drop_nonpositive and parsed <= 0:
        return None
    return parsed


def split_city_state_zip(value: object) -> tuple[str | None, str | None, str | None]:
    text = clean(value)
    if not text:
        return None, None, None
    parts = text.split()
    if len(parts) >= 3 and len(parts[-2]) == 2 and parts[-2].isalpha() and parts[-1][:5].isdigit():
        city = " ".join(parts[:-2]) or None
        return city, parts[-2].upper(), parts[-1][:5]
    return text, None, None


def mail_lines(*parts: object) -> tuple[str | None, str | None]:
    lines = [clean(part) for part in parts]
    lines = [line for line in lines if line]
    if not lines:
        return None, None
    return lines[0], " ".join(lines[1:]) if len(lines) > 1 else None


def ring_area(coords: list[list[float]]) -> float:
    area = 0.0
    for i in range(len(coords) - 1):
        area += coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1]
    return area / 2.0


def group_rings(rings: list) -> list[list[list[list[float]]]]:
    prepared: list[tuple[float, list[list[float]]]] = []
    for ring in rings:
        raw = [[float(x), float(y)] for x, y in ring]
        if len(raw) < 4:
            continue
        prepared.append((ring_area(raw), simplify_ring(raw, 0.00006)))
    if not prepared:
        return []
    exterior_positive = prepared[0][0] > 0
    polygons: list[list[list[list[float]]]] = []
    current: list[list[list[float]]] = []
    for area, coords in prepared:
        if len(coords) < 4:
            continue
        is_exterior = area > 0 if exterior_positive else area < 0
        if not current or is_exterior:
            if current:
                polygons.append(current)
            current = [coords]
        else:
            current.append(coords)
    if current:
        polygons.append(current)
    return polygons


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def point_in_parts(x: float, y: float, parts: list[list[list[list[float]]]]) -> bool:
    for poly in parts:
        if not poly:
            continue
        if point_in_ring(x, y, poly[0]) and not any(point_in_ring(x, y, hole) for hole in poly[1:]):
            return True
    return False


class SpatialIndex:
    def __init__(self) -> None:
        self.cell = 0.08
        self.bins: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.items: list[tuple] = []
        self.centers: list[tuple[float, float]] = []

    def add(self, rings: list, payload: dict) -> bool:
        parts = group_rings(rings)
        if not parts:
            return False
        xs: list[float] = []
        ys: list[float] = []
        area = 0.0
        for poly in parts:
            area += abs(ring_area(poly[0]))
            for ring in poly:
                for x, y in ring:
                    xs.append(x)
                    ys.append(y)
        if not xs:
            return False
        bbox = (min(xs), min(ys), max(xs), max(ys))
        idx = len(self.items)
        self.items.append((parts, payload, bbox, area))
        self.centers.append(((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2))
        ix0 = math.floor(bbox[0] / self.cell)
        ix1 = math.floor(bbox[2] / self.cell)
        iy0 = math.floor(bbox[1] / self.cell)
        iy1 = math.floor(bbox[3] / self.cell)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.bins[(ix, iy)].append(idx)
        return True

    def query(self, x: float, y: float) -> dict | None:
        best = None
        best_area = None
        ix = math.floor(x / self.cell)
        iy = math.floor(y / self.cell)
        for idx in self.bins.get((ix, iy), ()):
            parts, payload, bbox, area = self.items[idx]
            if x < bbox[0] or x > bbox[2] or y < bbox[1] or y > bbox[3]:
                continue
            if not point_in_parts(x, y, parts):
                continue
            if best_area is None or area < best_area:
                best = payload
                best_area = area
        return best


def inside(point: tuple[float, float], box: tuple[float, float, float, float]) -> bool:
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def verify_centers(centers: list[tuple[float, float]], box: tuple[float, float, float, float], label: str, tight: tuple[float, float, float, float] | None = None) -> None:
    if not centers:
        raise RuntimeError(f"{label} returned no polygons")
    pan_hits = sum(1 for point in centers if inside(point, PANHANDLE_BOX))
    if pan_hits / len(centers) < 0.9:
        raise RuntimeError(f"{label} failed panhandle geo-verify ({pan_hits}/{len(centers)} centers inside Florida panhandle)")
    pad = (box[0] - 0.2, box[1] - 0.15, box[2] + 0.2, box[3] + 0.15)
    box_hits = sum(1 for point in centers if inside(point, pad))
    if box_hits / len(centers) < 0.8:
        raise RuntimeError(f"{label} extent does not match the county ({box_hits}/{len(centers)} centers in range)")
    if tight:
        lons = sorted(point[0] for point in centers)
        lats = sorted(point[1] for point in centers)
        median = (lons[len(lons) // 2], lats[len(lats) // 2])
        if not inside(median, tight):
            raise RuntimeError(f"{label} median {median[0]:.4f},{median[1]:.4f} is outside {tight}")


def load_features(url: str, where: str, fields: list[str]) -> list[dict]:
    assert_allowed(url)
    digest = hashlib.sha1(f"{url}|{where}|{','.join(fields)}".encode()).hexdigest()[:20]
    path = CACHE_DIR / f"{digest}.json"
    label = url.split("/rest/services/")[-1][:72]
    if path.exists():
        payload = json.loads(path.read_text())
        if isinstance(payload, dict):
            payload = payload.get("features") or []
        print(f"    cache {len(payload)} {label}", flush=True)
        return payload
    ids = list(dict.fromkeys(fetch_object_ids(url, where)))
    print(f"    ids {len(ids)} {label}", flush=True)
    raw = fetch_by_ids(url, ids, fields, batch=160)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw))
    return raw


def load_overlay(
    layer: str,
    fields: list[str],
    *,
    label: str,
    box: tuple[float, float, float, float],
    tight: tuple[float, float, float, float] | None = None,
    id_field: str | None = None,
) -> tuple[SpatialIndex, dict[str, dict]]:
    raw = load_features(query_url(layer), "1=1", fields)
    index = SpatialIndex()
    by_id: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        rings = (item.get("geometry") or {}).get("rings") or []
        payload = {key: attrs.get(key) for key in fields}
        index.add(rings, payload)
        if id_field:
            key = norm_id(attrs.get(id_field))
            if key and key not in by_id:
                by_id[key] = payload
    verify_centers(index.centers, box, label, tight=tight)
    print(f"    {label}: {len(index.items)} polygons, {len(by_id)} keyed ids", flush=True)
    return index, by_id


def try_overlay(layer: str, fields: list[str], **kwargs) -> tuple[SpatialIndex | None, dict[str, dict], str | None]:
    label = kwargs.get("label", layer)
    try:
        index, by_id = load_overlay(layer, fields, **kwargs)
        return index, by_id, None
    except Exception as exc:  # noqa: BLE001
        print(f"    skip {label}: {exc}", flush=True)
        return None, {}, str(exc)


def flu_info(code: object, label: object, jurisdiction: str, source: str) -> dict | None:
    text = code_text(code)
    if not text:
        return None
    pretty = clean(label)
    if pretty and pretty == text:
        pretty = text
    return {
        "code": text,
        "label": pretty or text,
        "jurisdiction": jurisdiction,
        "source": source,
    }


def finish_feature(
    *,
    county: dict,
    markets: list[str],
    parcel_id: str,
    acres: float,
    geometry: dict,
    center: tuple[float, float],
    source: str,
    owner: str | None,
    owner2: str | None,
    situs: str | None,
    city: str | None,
    zip_code: str | None,
    zoning: str | None,
    district: str | None,
    jurisdiction: str | None,
    prefix: str | None,
    dor: str | None,
    sale_price: float | None,
    sale_date: str | None,
    sale_qualified: str | None,
    market_value: float | None,
    assessed: float | None,
    taxable: float | None,
    mail1: str | None,
    mail2: str | None,
    mail_city: str | None,
    mail_state: str | None,
    mail_zip: str | None,
    appraiser: str | None,
    flu: dict | None,
    gaps: list[str],
) -> dict:
    feature = empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=markets,
        parcel_id=parcel_id,
        acreage=acres,
        geometry=geometry,
        center=center,
        source=source,
        owner=owner,
        situs=situs,
        city=city,
        zip_code=zip_code,
        zoning=zoning,
        dor=dor,
        sale_price=sale_price,
        sale_date=sale_date,
        sale_qualified=sale_qualified,
        market_value=market_value,
        assessed=assessed,
        taxable=taxable,
        mail1=mail1,
        mail2=mail2,
        mail_city=mail_city,
        mail_state=mail_state,
        mail_zip=mail_zip,
    )
    props = feature["properties"]
    props["ownerName2"] = owner2
    props["zoningDistrict"] = district
    props["jurisdictionCode"] = jurisdiction
    props["jurisdictionPrefix"] = prefix
    props["flu"] = flu
    props["appraiserUrl"] = appraiser
    props["dataGaps"] = gaps
    return feature


def geometry_of(item: dict, fips: str) -> tuple[dict | None, tuple[float, float] | None, float | None]:
    geometry = arcgis_to_geojson(item.get("geometry"))
    if not geometry:
        return None, None, None
    center = centroid_of(geometry)
    if not center or not plausible_centroid(center):
        return None, None, None
    box = COUNTY_BOX[fips]
    pad = (box[0] - 0.08, box[1] - 0.08, box[2] + 0.08, box[3] + 0.08)
    if not inside(center, pad):
        return None, None, None
    return geometry, center, None


def base_from_item(item: dict, fips: str, acres_field: str) -> tuple[dict | None, str | None]:
    attrs = item.get("attributes") or {}
    acres = num(attrs.get(acres_field))
    geometry, center, _ = geometry_of(item, fips)
    if not geometry or not center or not in_band(acres):
        return None, "drop"
    return {"attrs": attrs, "acres": acres, "geometry": geometry, "center": center}, None


def hit(index: SpatialIndex | None, center: tuple[float, float]) -> dict | None:
    if index is None:
        return None
    return index.query(center[0], center[1])


def probe_http(url: str) -> str:
    assert_allowed(url)
    target = url + ("&" if "?" in url else "?") + "f=json"
    req = urllib.request.Request(target, headers={"User-Agent": "darryl-land-search/market-parcels"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return str(resp.status)
    except urllib.error.HTTPError as exc:
        return str(exc.code)
    except Exception as exc:  # noqa: BLE001
        return f"error:{exc.__class__.__name__}"


def geometry_parts(geom: dict) -> list:
    if geom.get("type") == "Polygon":
        return [geom["coordinates"]]
    if geom.get("type") == "MultiPolygon":
        return list(geom["coordinates"])
    return []


def part_signature(part: list) -> tuple:
    ring = part[0] if part else []
    step = max(1, len(ring) // 12)
    return (
        len(part),
        len(ring),
        tuple((round(point[0], 5), round(point[1], 5)) for point in ring[::step]),
    )


def merge_geometry(left: dict, right: dict) -> dict:
    coords = []
    seen: set[tuple] = set()
    for part in geometry_parts(left) + geometry_parts(right):
        if not part:
            continue
        signature = part_signature(part)
        if signature in seen:
            continue
        seen.add(signature)
        coords.append(part)
    if len(coords) == 1:
        return {"type": "Polygon", "coordinates": coords[0]}
    return {"type": "MultiPolygon", "coordinates": coords}


def arcgis_to_geojson(geom: dict | None) -> dict | None:
    """Convert ArcGIS rings, keeping holes as holes. Exterior winding follows the first ring."""
    parts = group_rings((geom or {}).get("rings") or [])
    if not parts:
        return None
    if len(parts) == 1:
        return {"type": "Polygon", "coordinates": parts[0]}
    return {"type": "MultiPolygon", "coordinates": parts}


def is_unit_address(text: str | None) -> bool:
    if not text:
        return False
    upper = f" {text.upper()} "
    return " APT " in upper or " UNIT " in upper or " # " in upper


def prefer_duplicate_attributes(keep: dict, other: dict) -> None:
    """Stacked-unit rows share a polygon. Keep one situs and do not sum values."""
    props = keep["properties"]
    incoming = other["properties"]
    current = props.get("situsAddress")
    new_situs = incoming.get("situsAddress")
    if new_situs and (not current or (is_unit_address(current) and not is_unit_address(new_situs))):
        props["situsAddress"] = new_situs
        if incoming.get("situsCity"):
            props["situsCity"] = incoming["situsCity"]
        if incoming.get("situsZip"):
            props["situsZip"] = incoming["situsZip"]
    if not props.get("ownerName") and incoming.get("ownerName"):
        props["ownerName"] = incoming["ownerName"]
    if not props.get("ownerName2") and incoming.get("ownerName2"):
        props["ownerName2"] = incoming["ownerName2"]
    tax = props.get("tax") or {}
    other_tax = incoming.get("tax") or {}
    if (tax.get("marketValue") or 0) <= 0 and (other_tax.get("marketValue") or 0) > 0:
        tax["marketValue"] = other_tax["marketValue"]
        props["tax"] = tax


def collapse_note(source_count: int, kept: int, merged_parts: int, repeated_rows: int) -> str | None:
    if source_count and (kept < source_count or repeated_rows or merged_parts):
        return (
            f"{source_count} source rows became {kept} parcel ids. "
            f"{merged_parts} split pieces with a new shape were merged. "
            f"{repeated_rows} repeated rows with the same polygon (stacked units or duplicate ids) were collapsed to one feature. "
            "Acreage and tax values are not summed across those rows. "
            "Rows that failed the WGS84 or county-extent check were dropped."
        )
    return None


def store_county(
    county: dict,
    markets: list[str],
    features: list[dict],
    *,
    source: str,
    query: str,
    gaps: list[str],
    source_count: int,
    dropped: int,
    merged_parts: int = 0,
    repeated_rows: int = 0,
) -> dict:
    if not features:
        raise RuntimeError(f"{county['fips']} kept no 5–150 acre parcels")
    if not all(in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{county['fips']} emitted a parcel outside 5–150 acres")
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    path, lookup, tiles = write_tiles(county, features)
    zoning_n = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_n = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    sale_n = sum(1 for feature in features if (feature["properties"].get("lastSale") or {}).get("price") is not None)
    date_n = sum(1 for feature in features if (feature["properties"].get("lastSale") or {}).get("date"))
    situs_n = sum(1 for feature in features if feature["properties"].get("situsAddress"))
    owner_n = sum(1 for feature in features if feature["properties"].get("ownerName"))
    summary = (
        f"Joined zoning on {zoning_n} of {len(features)} parcels and FLU on {flu_n}. "
        f"Owner {owner_n}, situs {situs_n}, sale price {sale_n}, sale date {date_n}."
    )
    gap_list = [summary, *gaps]
    note = collapse_note(source_count, len(features), merged_parts, repeated_rows)
    if note:
        gap_list.insert(1, note)
    row = county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=source,
        query_url=query,
        gaps=gap_list,
        source_count=source_count,
        dropped=dropped,
        tile_count=tiles,
    )
    row["zoningJoinedCount"] = zoning_n
    row["fluJoinedCount"] = flu_n
    row["salePriceCount"] = sale_n
    row["saleDateCount"] = date_n
    row["situsCount"] = situs_n
    row["ownerCount"] = owner_n
    (COUNTY_DIR / county["fips"] / "county.json").write_text(json.dumps(row, indent=2) + "\n")
    print(
        f"  kept {len(features)} zoning {zoning_n} flu {flu_n} sale {sale_n} situs {situs_n}",
        flush=True,
    )
    return row


def dedupe(rows: list[dict], county: dict, markets: list[str], source: str, build) -> tuple[list[dict], int, int, int]:
    by_id: dict[str, dict] = {}
    dropped = 0
    merged_parts = 0
    repeated_rows = 0
    for item in rows:
        feature = build(item, county, markets, source)
        if feature is None:
            dropped += 1
            continue
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None:
            by_id[parcel_id] = feature
            continue
        keep = previous
        other = feature
        if (feature["properties"].get("acreage") or 0) > (previous["properties"].get("acreage") or 0):
            keep = feature
            other = previous
        before = len(geometry_parts(keep["geometry"]))
        keep["geometry"] = merge_geometry(keep["geometry"], other["geometry"])
        added = len(geometry_parts(keep["geometry"])) - before
        if added > 0:
            merged_parts += added
            c1 = keep["properties"]["centroid"]
            c2 = other["properties"]["centroid"]
            keep["properties"]["centroid"] = [round((c1[0] + c2[0]) / 2, 6), round((c1[1] + c2[1]) / 2, 6)]
        else:
            repeated_rows += 1
            prefer_duplicate_attributes(keep, other)
        by_id[parcel_id] = keep
    return list(by_id.values()), dropped, merged_parts, repeated_rows


def seed_bay(county: dict, markets: list[str]) -> dict:
    fips = "12005"
    box = COUNTY_BOX[fips]
    zoning, _, zoning_err = try_overlay(
        LAYERS["bay_zoning"],
        ["ZONING", "SUB_ZONING", "Label"],
        label="Bay LandUsePlanning zoning",
        box=box,
    )
    flu_index, _, flu_err = try_overlay(
        LAYERS["bay_flu"],
        ["FLU_CODE", "SUB_FLU", "Label"],
        label="Bay LandUsePlanning FLU",
        box=box,
    )
    pcb_z, _, pcb_z_err = try_overlay(
        LAYERS["pcb_zoning"],
        ["ZONING", "SUB_ZONING", "Label"],
        label="Panama City Beach zoning",
        box=box,
        tight=(-86.25, 30.05, -85.65, 30.40),
    )
    pcb_f, _, pcb_f_err = try_overlay(
        LAYERS["pcb_flu"],
        ["FLU_CODE", "SUB_FLU", "Label"],
        label="Panama City Beach FLU",
        box=box,
        tight=(-86.25, 30.05, -85.65, 30.40),
    )
    where = "dtaxacres>=5 AND dtaxacres<=150"
    url = query_url(LAYERS["bay_parcels"])
    source_count = count_where(url, where)
    fields = [
        "a1renum",
        "re_label",
        "dtaxacres",
        "a2owname",
        "a3mailaddr",
        "a4mailaddr",
        "a5mailaddr",
        "a6mailcity",
        "a7mailst",
        "a8mailzip",
        "dsiteaddr",
        "dsitezip",
        "sale1pradj",
        "sale1date",
        "sale1qu_vi",
        "vasjust",
        "vastotal",
        "vastaxable",
        "dorappcode",
        "plink",
    ]
    raw = load_features(url, where, fields)
    hits = {"pcb_zoning": 0, "pcb_flu": 0, "county_zoning": 0, "county_flu": 0}

    def build(item: dict, county: dict, markets: list[str], source: str) -> dict | None:
        parsed, _ = base_from_item(item, fips, "dtaxacres")
        if not parsed:
            return None
        attrs = parsed["attrs"]
        parcel_id = clean(attrs.get("a1renum")) or clean(attrs.get("re_label"))
        if not parcel_id:
            return None
        center = parsed["center"]
        city_z = hit(pcb_z, center)
        city_f = hit(pcb_f, center)
        county_z = hit(zoning, center)
        county_f = hit(flu_index, center)
        district = None
        prefix = None
        if city_z:
            hits["pcb_zoning"] += 1
            zoning_code = code_text(city_z.get("ZONING"))
            district = clean(city_z.get("Label"))
            jurisdiction = "Panama City Beach"
            prefix = code_text(city_z.get("SUB_ZONING")) or "6"
        elif county_z:
            hits["county_zoning"] += 1
            zoning_code = code_text(county_z.get("ZONING"))
            district = clean(county_z.get("Label"))
            prefix = code_text(county_z.get("SUB_ZONING"))
            jurisdiction = BAY_SUB.get(prefix or "", "Bay County")
        else:
            zoning_code = None
            jurisdiction = None
        if city_f:
            hits["pcb_flu"] += 1
            flu_value = flu_info(city_f.get("FLU_CODE"), city_f.get("Label"), "Panama City Beach", LAYERS["pcb_flu"])
        elif county_f:
            hits["county_flu"] += 1
            sub = code_text(county_f.get("SUB_FLU"))
            flu_value = flu_info(
                county_f.get("FLU_CODE"),
                county_f.get("Label"),
                BAY_SUB.get(sub or "", "Bay County"),
                LAYERS["bay_flu"],
            )
        else:
            flu_value = None
        mail1, mail2 = mail_lines(attrs.get("a3mailaddr"), attrs.get("a4mailaddr"), attrs.get("a5mailaddr"))
        return finish_feature(
            county=county,
            markets=markets,
            parcel_id=parcel_id,
            acres=parsed["acres"],
            geometry=parsed["geometry"],
            center=center,
            source=source,
            owner=clean(attrs.get("a2owname")),
            owner2=None,
            situs=clean(attrs.get("dsiteaddr")),
            city=None,
            zip_code=zip_str(attrs.get("dsitezip")),
            zoning=zoning_code,
            district=district,
            jurisdiction=jurisdiction,
            prefix=prefix,
            dor=code_text(attrs.get("dorappcode")),
            sale_price=money(attrs.get("sale1pradj"), drop_nonpositive=True),
            sale_date=parse_sale_date(attrs.get("sale1date")),
            sale_qualified=clean(attrs.get("sale1qu_vi")),
            market_value=money(attrs.get("vasjust")),
            assessed=money(attrs.get("vastotal")),
            taxable=money(attrs.get("vastaxable")),
            mail1=mail1,
            mail2=mail2,
            mail_city=clean(attrs.get("a6mailcity")),
            mail_state=clean(attrs.get("a7mailst")),
            mail_zip=zip_str(attrs.get("a8mailzip")),
            appraiser=clean(attrs.get("plink")) or "https://qpublic.schneidercorp.com/Application.aspx?AppID=834",
            flu=flu_value,
            gaps=[],
        )

    features, dropped, merged_parts, repeated_rows = dedupe(raw, county, markets, "fl-panhandle-12005", build)
    gaps = [
        "Official zoning and FLU come from LandUsePlanning MapServer 1 and 2 (spatial). Parcel zoning/flu attributes are often null and are not used.",
        (
            "Panama City Beach uses city Land_Use_and_Zoning FeatureServer 47 (zoning) and 49 (FLU) when the centroid hits those polygons; "
            f"otherwise SUB_ZONING on the county layer (1 Bay County, 2 Callaway, 3 Lynn Haven, 4 Mexico Beach, 5 Panama City, 6 Panama City Beach). "
            f"PCB zoning hits {hits['pcb_zoning']}, county zoning hits {hits['county_zoning']}."
        ),
        "Parker and Springfield have no dedicated city REST this pass. They are not separate SUB_ZONING codes. A parcel there keeps the county multi-jurisdiction district only when that polygon intersects it.",
        "Situs on rural samples is often legal or acre text (dsiteaddr), not a street address. The field is still the published situs.",
        ADJACENT_GAP,
    ]
    if zoning_err:
        gaps.append(f"Bay county zoning layer was not applied: {zoning_err}")
    if flu_err:
        gaps.append(f"Bay county FLU layer was not applied: {flu_err}")
    if pcb_z_err:
        gaps.append(f"Panama City Beach zoning layer failed geo-verify or download ({pcb_z_err}). County SUB_ZONING=6 remains the PCB twin.")
    if pcb_f_err:
        gaps.append(f"Panama City Beach FLU layer failed geo-verify or download ({pcb_f_err}). County SUB_FLU=6 remains the PCB twin.")
    return store_county(
        county,
        markets,
        features,
        source="fl-panhandle-12005",
        query=url,
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        merged_parts=merged_parts,
        repeated_rows=repeated_rows,
    )


def seed_okaloosa(county: dict, markets: list[str]) -> dict:
    fips = "12091"
    box = COUNTY_BOX[fips]
    zoning, _, zoning_err = try_overlay(
        LAYERS["okaloosa_zoning"],
        ["ZNGPY_ZONE"],
        label="Okaloosa unincorporated zoning",
        box=box,
    )
    flu, _, flu_err = try_overlay(
        LAYERS["okaloosa_flu"],
        ["FLUPY_ZONE"],
        label="Okaloosa unincorporated FLU",
        box=box,
    )
    destin_box = (-86.56, 30.36, -86.38, 30.44)
    destin_z, _, destin_z_err = try_overlay(
        LAYERS["destin_zoning"],
        ["Zone_ABBR", "Zone_Label", "Zone_"],
        label="Destin zoning",
        box=box,
        tight=destin_box,
    )
    destin_f, _, destin_f_err = try_overlay(
        LAYERS["destin_flu"],
        ["LU_CODE", "LAND_USE", "DESCRIPTIO"],
        label="Destin land use",
        box=box,
        tight=destin_box,
    )
    fwb_box = (-86.75, 30.36, -86.48, 30.50)
    fwb_z, _, fwb_z_err = try_overlay(
        LAYERS["fwb_zoning"],
        ["Zoning", "Zoning_Desc", "FLU", "FLU_Desc"],
        label="Fort Walton Beach zoning",
        box=box,
        tight=fwb_box,
    )
    fwb_f, _, fwb_f_err = try_overlay(
        LAYERS["fwb_flu"],
        ["FLU", "FLU_Desc"],
        label="Fort Walton Beach FLU",
        box=box,
        tight=fwb_box,
    )
    where = "PATPCL_GIS_ACRE>=5 AND PATPCL_GIS_ACRE<=150"
    url = query_url(LAYERS["okaloosa_parcels"])
    source_count = count_where(url, where)
    fields = [
        "PATPCL_PIN",
        "PATPCL_STRAP",
        "PATPCL_GIS_ACRE",
        "PATPCL_OWNER",
        "PATPCL_ADDR1",
        "PATPCL_ADDR2",
        "PATPCL_ADDR3",
        "PATPCL_CITY",
        "PATPCL_STATE",
        "PATPCL_ZIPCODE",
        "PATPCL_SALE1",
        "PATPCL_SALEDT1",
        "PATPCL_QUAL1",
        "PATPCL_JUSTVAL",
        "PATPCL_ASSEDVAL",
        "PATPCL_TAXVAL",
        "PATPCL_USECODE",
    ]
    raw = load_features(url, where, fields)
    hits = {"destin": 0, "fwb": 0, "county": 0}

    def build(item: dict, county: dict, markets: list[str], source: str) -> dict | None:
        parsed, _ = base_from_item(item, fips, "PATPCL_GIS_ACRE")
        if not parsed:
            return None
        attrs = parsed["attrs"]
        parcel_id = clean(attrs.get("PATPCL_PIN")) or clean(attrs.get("PATPCL_STRAP"))
        if not parcel_id:
            return None
        center = parsed["center"]
        destin_zone = hit(destin_z, center)
        destin_use = hit(destin_f, center)
        fwb_zone = hit(fwb_z, center)
        fwb_use = hit(fwb_f, center)
        county_zone = hit(zoning, center)
        county_use = hit(flu, center)
        district = None
        gaps = ["Situs address is not published on Okaloosa PARCELS/17 (mailing only)."]
        if destin_zone:
            hits["destin"] += 1
            zoning_code = code_text(destin_zone.get("Zone_ABBR")) or code_text(destin_zone.get("Zone_Label"))
            district = clean(destin_zone.get("Zone_")) or clean(destin_zone.get("Zone_Label"))
            jurisdiction = "Destin"
            flu_row = flu_info(
                (destin_use or {}).get("LU_CODE"),
                (destin_use or {}).get("LAND_USE") or (destin_use or {}).get("DESCRIPTIO"),
                "Destin",
                LAYERS["destin_flu"],
            )
        elif fwb_zone or fwb_use:
            hits["fwb"] += 1
            zoning_code = code_text((fwb_zone or {}).get("Zoning"))
            district = clean((fwb_zone or {}).get("Zoning_Desc"))
            jurisdiction = "Fort Walton Beach"
            flu_source = fwb_use or fwb_zone or {}
            flu_row = flu_info(flu_source.get("FLU"), flu_source.get("FLU_Desc"), "Fort Walton Beach", LAYERS["fwb_flu"])
        else:
            if county_zone or county_use:
                hits["county"] += 1
            zoning_code = code_text((county_zone or {}).get("ZNGPY_ZONE")) if county_zone else None
            jurisdiction = "Okaloosa County (unincorporated)" if zoning_code or county_use else None
            flu_row = flu_info(
                (county_use or {}).get("FLUPY_ZONE") if county_use else None,
                (county_use or {}).get("FLUPY_ZONE") if county_use else None,
                "Okaloosa County (unincorporated)",
                LAYERS["okaloosa_flu"],
            )
        mail1, mail2 = mail_lines(attrs.get("PATPCL_ADDR1"), attrs.get("PATPCL_ADDR2"), attrs.get("PATPCL_ADDR3"))
        return finish_feature(
            county=county,
            markets=markets,
            parcel_id=parcel_id,
            acres=parsed["acres"],
            geometry=parsed["geometry"],
            center=center,
            source=source,
            owner=clean(attrs.get("PATPCL_OWNER")),
            owner2=None,
            situs=None,
            city=None,
            zip_code=None,
            zoning=zoning_code,
            district=district,
            jurisdiction=jurisdiction,
            prefix=None,
            dor=code_text(attrs.get("PATPCL_USECODE")),
            sale_price=money(attrs.get("PATPCL_SALE1"), drop_nonpositive=True),
            sale_date=parse_sale_date(attrs.get("PATPCL_SALEDT1")),
            sale_qualified=code_text(attrs.get("PATPCL_QUAL1")),
            market_value=money(attrs.get("PATPCL_JUSTVAL")),
            assessed=money(attrs.get("PATPCL_ASSEDVAL")),
            taxable=money(attrs.get("PATPCL_TAXVAL")),
            mail1=mail1,
            mail2=mail2,
            mail_city=clean(attrs.get("PATPCL_CITY")),
            mail_state=clean(attrs.get("PATPCL_STATE")),
            mail_zip=zip_str(attrs.get("PATPCL_ZIPCODE")),
            appraiser="https://www.okaloosapa.com/",
            flu=flu_row,
            gaps=gaps,
        )

    features, dropped, merged_parts, repeated_rows = dedupe(raw, county, markets, "fl-panhandle-12091", build)
    gaps = [
        "Situs is a gap on internet_webgis PARCELS/17. Mailing address is stored. No separate situs fields.",
        (
            "County Zoning/515 and Future Land Use/44 are unincorporated only. They are not treated as city law. "
            f"Unincorporated zoning/FLU hits {hits['county']}. Destin zoning hits {hits['destin']}. Fort Walton Beach hits {hits['fwb']}."
        ),
        "Destin zoning is Zoning_JulyB_WFL1/0 (geo-verified Destin FL, about -86.52 to -86.40). Destin FLU is LandUse_DND25_WFL1/2 (LU_CODE). The FGDL statewide Zoning service is not used.",
        "Fort Walton Beach zoning is gis.fwb.org Maps/Zoning/0. FLU prefers Maps/FLU/0 and falls back to the FLU attributes on the zoning layer.",
        "Crestview, Niceville, Valparaiso, Mary Esther, Laurel Hill, Cinco Bayou, and Shalimar have no verified public city FeatureServer this pass. Unincorporated county codes are not copied onto those cities.",
        "Appraiser link is the Okaloosa PA portal. The layer does not publish a verified per-parcel URL. Search uses PATPCL_PIN.",
        ADJACENT_GAP,
    ]
    for label, err in (
        ("Okaloosa zoning", zoning_err),
        ("Okaloosa FLU", flu_err),
        ("Destin zoning", destin_z_err),
        ("Destin FLU", destin_f_err),
        ("Fort Walton Beach zoning", fwb_z_err),
        ("Fort Walton Beach FLU", fwb_f_err),
    ):
        if err:
            gaps.append(f"{label} was not applied: {err}")
    return store_county(
        county,
        markets,
        features,
        source="fl-panhandle-12091",
        query=url,
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        merged_parts=merged_parts,
        repeated_rows=repeated_rows,
    )


def seed_walton(county: dict, markets: list[str]) -> dict:
    fips = "12131"
    box = COUNTY_BOX[fips]
    muni, _, muni_err = try_overlay(
        LAYERS["walton_muni"],
        ["Name"],
        label="Walton municipalities",
        box=box,
    )
    zoning, _, zoning_err = try_overlay(
        LAYERS["walton_zoning"],
        ["ZONE_CLASS", "PLAN_AREA"],
        label="Walton EnerGov zoning",
        box=box,
    )
    flu, _, flu_err = try_overlay(
        LAYERS["walton_flu"],
        ["FLU_CLASS", "FLU_TYPE", "SubType"],
        label="Walton EnerGov FLU",
        box=box,
    )
    dfs_z, dfs_z_ids, dfs_z_err = try_overlay(
        LAYERS["dfs_zoning"],
        ["PARCELNO", "ZONING"],
        label="DeFuniak Springs zoning",
        box=box,
        id_field="PARCELNO",
    )
    dfs_f, dfs_f_ids, dfs_f_err = try_overlay(
        LAYERS["dfs_flu"],
        ["PARCELNO", "FLU"],
        label="DeFuniak Springs FLU",
        box=box,
        id_field="PARCELNO",
    )
    fp_z, _, fp_z_err = try_overlay(
        LAYERS["freeport_zoning"],
        ["Zoning", "Description"],
        label="Freeport zoning",
        box=box,
    )
    fp_f, _, fp_f_err = try_overlay(
        LAYERS["freeport_flu"],
        ["Land_Use", "Description"],
        label="Freeport FLU",
        box=box,
    )
    pax_f, _, pax_err = try_overlay(
        LAYERS["paxton_flu"],
        ["FLU_CLASS", "SubType"],
        label="Paxton FLU",
        box=box,
    )
    where = "GIS_ACRES>=5 AND GIS_ACRES<=150"
    url = query_url(LAYERS["walton_parcels"])
    source_count = count_where(url, where)
    fields = [
        "PARCELNO",
        "GIS_ACRES",
        "OWNER_NAME",
        "OWN_ADDRESS_1",
        "OWN_ADDRESS_2",
        "OWN_CITY",
        "OWN_STATE",
        "OWN_ZIPCODE",
        "SALE_DATE_1",
        "JUST_VALUE",
        "APPRAISED_VALUE",
        "USE_CODE",
    ]
    raw = load_features(url, where, fields)
    hits = {"dfs": 0, "freeport": 0, "paxton": 0, "county": 0}
    freeport_zones: set[str] = set()
    freeport_uses: set[str] = set()

    def city_name(center: tuple[float, float]) -> str | None:
        row = hit(muni, center)
        return clean((row or {}).get("Name"))

    def build(item: dict, county: dict, markets: list[str], source: str) -> dict | None:
        parsed, _ = base_from_item(item, fips, "GIS_ACRES")
        if not parsed:
            return None
        attrs = parsed["attrs"]
        parcel_id = clean(attrs.get("PARCELNO"))
        if not parcel_id:
            return None
        center = parsed["center"]
        city = city_name(center)
        key = norm_id(parcel_id)
        zoning_code = None
        district = None
        jurisdiction = None
        flu_row = None
        gaps = [
            "Situs address is not published on the Walton EnerGov parcel layer.",
            "Sale price is not published (sale date only).",
        ]
        if city == "DeFuniak Springs":
            hits["dfs"] += 1
            zone_row = dfs_z_ids.get(key) if key else None
            if zone_row is None:
                zone_row = hit(dfs_z, center)
            use_row = dfs_f_ids.get(key) if key else None
            if use_row is None:
                use_row = hit(dfs_f, center)
            zoning_code = code_text((zone_row or {}).get("ZONING"))
            jurisdiction = "DeFuniak Springs"
            flu_row = flu_info((use_row or {}).get("FLU"), (use_row or {}).get("FLU"), "DeFuniak Springs", LAYERS["dfs_flu"])
        elif city == "Freeport":
            hits["freeport"] += 1
            zone_row = hit(fp_z, center)
            use_row = hit(fp_f, center)
            zoning_code = code_text((zone_row or {}).get("Zoning"))
            district = clean((zone_row or {}).get("Description"))
            if zoning_code:
                freeport_zones.add(zoning_code)
            land_use = code_text((use_row or {}).get("Land_Use"))
            if land_use:
                freeport_uses.add(land_use)
            jurisdiction = "Freeport"
            flu_row = flu_info(land_use, clean((use_row or {}).get("Description")), "Freeport", LAYERS["freeport_flu"])
            gaps.append(
                "Freeport zoning is a numeric code (0–16 on the card) with a blank Description. The number is stored with no invented district name."
            )
        elif city == "Paxton":
            hits["paxton"] += 1
            use_row = hit(pax_f, center)
            jurisdiction = "Paxton"
            subtype = (use_row or {}).get("SubType")
            label = subtype if isinstance(subtype, str) and clean(subtype) else None
            flu_row = flu_info((use_row or {}).get("FLU_CLASS"), label, "Paxton", LAYERS["paxton_flu"])
            gaps.append("Paxton zoning is a gap. Only Paxton FLU was verified (WeeklyUpdatesPaxton/6). County zoning is not applied inside Paxton.")
        else:
            zone_row = hit(zoning, center)
            use_row = hit(flu, center)
            if zone_row or use_row:
                hits["county"] += 1
            zoning_code = code_text((zone_row or {}).get("ZONE_CLASS")) if zone_row else None
            district = clean((zone_row or {}).get("PLAN_AREA")) if zone_row else None
            jurisdiction = "Walton County" if zoning_code or use_row else None
            flu_code = code_text((use_row or {}).get("FLU_TYPE")) if use_row else None
            flu_label = clean((use_row or {}).get("FLU_CLASS")) if use_row else None
            flu_row = flu_info(flu_code or flu_label, flu_label, "Walton County", LAYERS["walton_flu"])
        mail1, mail2 = mail_lines(attrs.get("OWN_ADDRESS_1"), attrs.get("OWN_ADDRESS_2"))
        return finish_feature(
            county=county,
            markets=markets,
            parcel_id=parcel_id,
            acres=parsed["acres"],
            geometry=parsed["geometry"],
            center=center,
            source=source,
            owner=clean(attrs.get("OWNER_NAME")),
            owner2=None,
            situs=None,
            city=None,
            zip_code=None,
            zoning=zoning_code,
            district=district,
            jurisdiction=jurisdiction,
            prefix=None,
            dor=code_text(attrs.get("USE_CODE")),
            sale_price=None,
            sale_date=parse_sale_date(attrs.get("SALE_DATE_1")),
            sale_qualified=None,
            market_value=money(attrs.get("JUST_VALUE")),
            assessed=money(attrs.get("APPRAISED_VALUE")),
            taxable=None,
            mail1=mail1,
            mail2=mail2,
            mail_city=clean(attrs.get("OWN_CITY")),
            mail_state=clean(attrs.get("OWN_STATE")),
            mail_zip=zip_str(attrs.get("OWN_ZIPCODE")),
            appraiser="https://www.waltonpa.com/",
            flu=flu_row,
            gaps=gaps,
        )

    features, dropped, merged_parts, repeated_rows = dedupe(raw, county, markets, "fl-panhandle-12131", build)
    observed_zones = ", ".join(sorted(freeport_zones, key=lambda item: (len(item), item))[:12]) or "none in the 5–150 acre band"
    observed_uses = ", ".join(sorted(freeport_uses, key=lambda item: (len(item), item))[:12]) or "none in the 5–150 acre band"
    gaps = [
        "Situs is a gap on EnerGov Parcels/4. Sale price is a gap (SALE_DATE_1 only; book/page is not a price and is not stored).",
        (
            "County EnerGov zoning/19 (ZONE_CLASS) and FLU/15 (FLU_TYPE code, FLU_CLASS label) apply outside city limits. "
            "DeFuniak Springs, Freeport, and Paxton use city layers. County districts are not applied inside those cities. "
            f"Hits: county {hits['county']}, DeFuniak Springs {hits['dfs']}, Freeport {hits['freeport']}, Paxton {hits['paxton']}."
        ),
        "DeFuniak Springs zoning and FLU join on PARCELNO (WeeklyUpdatesDFS/7 and /6), with a spatial fallback on the same city layers.",
        (
            "Freeport zoning (WeeklyUpdatesFreeport/7) is numeric and Description was blank on the samples. "
            f"Observed zoning codes in this extract: {observed_zones}. Do not treat the number as a named district until the city LDC legend is confirmed."
        ),
        (
            "Freeport FLU (WeeklyUpdatesFreeport/6) Land_Use was numeric and Description was blank on first ingest. "
            f"Observed Land_Use codes: {observed_uses}. The code is stored. No legend was invented."
        ),
        "Paxton FLU is WeeklyUpdatesPaxton/6 (FLU_CLASS). SubType is numeric and is not expanded into a name. Paxton zoning is a gap.",
        "A Monroe County layer titled Walton County Tax Parcels was rejected as wrong geography.",
        "Appraiser link is the Walton PA portal. No verified per-parcel deep link is on the layer. Search uses PARCELNO.",
        ADJACENT_GAP,
    ]
    for label, err in (
        ("Walton municipalities", muni_err),
        ("Walton zoning", zoning_err),
        ("Walton FLU", flu_err),
        ("DeFuniak Springs zoning", dfs_z_err),
        ("DeFuniak Springs FLU", dfs_f_err),
        ("Freeport zoning", fp_z_err),
        ("Freeport FLU", fp_f_err),
        ("Paxton FLU", pax_err),
    ):
        if err:
            gaps.append(f"{label} was not applied: {err}")
    return store_county(
        county,
        markets,
        features,
        source="fl-panhandle-12131",
        query=url,
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        merged_parts=merged_parts,
        repeated_rows=repeated_rows,
    )


def seed_escambia(county: dict, markets: list[str]) -> dict:
    fips = "12033"
    box = COUNTY_BOX[fips]
    zoning, _, zoning_err = try_overlay(
        LAYERS["escambia_zoning"],
        ["ZONING"],
        label="Escambia Accela zoning",
        box=box,
    )
    flu, _, flu_err = try_overlay(
        LAYERS["escambia_flu"],
        ["FLU_LABEL"],
        label="Escambia FLU 2030",
        box=box,
    )
    pensacola_status = probe_http(PENSACOLA_ZONING_URL)
    where = "LANDSIZE>=5 AND LANDSIZE<=150"
    url = query_url(LAYERS["escambia_parcels"])
    source_count = count_where(url, where)
    fields = [
        "REFERENCE",
        "REFNUM",
        "LANDSIZE",
        "OWNER",
        "MAILADDRESS1",
        "MAILADDRESS2",
        "MAILCITY",
        "MAILSTATE",
        "MAILZIP",
        "SITEADDR",
        "CITY",
        "ZIP",
        "CITYCD",
        "CURRMKT",
        "CURRASDLAND",
        "CURRASDBLDG",
        "CURRASDXF",
        "DORCD",
        "LINK",
    ]
    raw = load_features(url, where, fields)
    city_hits = {"Pensacola": 0, "Century": 0}

    def assessed_of(attrs: dict) -> float | None:
        parts = [num(attrs.get(key)) for key in ("CURRASDLAND", "CURRASDBLDG", "CURRASDXF")]
        if all(part is None for part in parts):
            return None
        return sum(part or 0 for part in parts)

    def build(item: dict, county: dict, markets: list[str], source: str) -> dict | None:
        parsed, _ = base_from_item(item, fips, "LANDSIZE")
        if not parsed:
            return None
        attrs = parsed["attrs"]
        parcel_id = clean(attrs.get("REFERENCE")) or clean(attrs.get("REFNUM"))
        if not parcel_id:
            return None
        center = parsed["center"]
        zone_row = hit(zoning, center)
        use_row = hit(flu, center)
        city_code = (clean(attrs.get("CITYCD")) or "").upper()
        if city_code in {"B", "Z"}:
            city_name = "Pensacola"
        elif city_code == "F":
            city_name = "Century"
        else:
            city_name = None
        if city_name:
            city_hits[city_name] += 1
        gaps = ["No sale price or sale date on the Escambia parcel layer. SOHYEAR is not a sale date and is not stored."]
        if city_name == "Pensacola":
            jurisdiction = "Pensacola"
            flu_jurisdiction = "Escambia Accela — Pensacola city REST blocked"
            gaps.append(
                f"Pensacola city Planning/Zoning returned HTTP {pensacola_status} on gis.cityofpensacola.com. "
                "Zoning and FLU are Escambia Accela (MapServer 20 and 22) until that city service recovers and its field map is re-verified. "
                "No separate Pensacola FLU REST was verified."
            )
        elif city_name == "Century":
            jurisdiction = "Century"
            flu_jurisdiction = "Escambia Accela — Century has no city layer"
            gaps.append("Century has no verified public zoning/FLU FeatureServer. County Accela zoning and FLU are used.")
        else:
            jurisdiction = "Escambia County" if zone_row or use_row else None
            flu_jurisdiction = "Escambia County"
        return finish_feature(
            county=county,
            markets=markets,
            parcel_id=parcel_id,
            acres=parsed["acres"],
            geometry=parsed["geometry"],
            center=center,
            source=source,
            owner=clean(attrs.get("OWNER")),
            owner2=None,
            situs=clean(attrs.get("SITEADDR")),
            city=clean(attrs.get("CITY")),
            zip_code=zip_str(attrs.get("ZIP")),
            zoning=code_text((zone_row or {}).get("ZONING")) if zone_row else None,
            district=None,
            jurisdiction=jurisdiction,
            prefix=city_code or None,
            dor=code_text(attrs.get("DORCD")),
            sale_price=None,
            sale_date=None,
            sale_qualified=None,
            market_value=money(attrs.get("CURRMKT")),
            assessed=assessed_of(attrs),
            taxable=None,
            mail1=clean(attrs.get("MAILADDRESS1")),
            mail2=clean(attrs.get("MAILADDRESS2")),
            mail_city=clean(attrs.get("MAILCITY")),
            mail_state=clean(attrs.get("MAILSTATE")),
            mail_zip=zip_str(attrs.get("MAILZIP")),
            appraiser=clean(attrs.get("LINK")) or "https://www.escpa.org/",
            flu=flu_info((use_row or {}).get("FLU_LABEL") if use_row else None, (use_row or {}).get("FLU_LABEL") if use_row else None, flu_jurisdiction, LAYERS["escambia_flu"]),
            gaps=gaps,
        )

    features, dropped, merged_parts, repeated_rows = dedupe(raw, county, markets, "fl-panhandle-12033", build)
    gaps = [
        "No lastSale price or date on Individual_Layers/parcels. SOHYEAR is not a sale date and is not stored.",
        (
            f"Pensacola city Planning/Zoning ({PENSACOLA_ZONING_URL}) probe returned HTTP {pensacola_status}. "
            "City parcels keep Escambia Accela zoning (AccelaMain/20, field ZONING) and FLU 2030 (AccelaMain/22, field FLU_LABEL) "
            f"until the city REST recovers. Pensacola CITYCD B/Z parcels in this extract: {city_hits['Pensacola']}. "
            "No separate Pensacola FLU layer was verified."
        ),
        f"Century (CITYCD F) has no public zoning/FLU FeatureServer. County Accela is used. Century parcels in this extract: {city_hits['Century']}.",
        "Assessed value is CURRASDLAND + CURRASDBLDG + CURRASDXF. CAPPEDVALUE is not stored as the assessed total.",
        "Appraiser URL is the parcel LINK field when present (escpa.org cama detail).",
        ADJACENT_GAP,
    ]
    if zoning_err:
        gaps.append(f"Escambia Accela zoning was not applied: {zoning_err}")
    if flu_err:
        gaps.append(f"Escambia FLU was not applied: {flu_err}")
    return store_county(
        county,
        markets,
        features,
        source="fl-panhandle-12033",
        query=url,
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        merged_parts=merged_parts,
        repeated_rows=repeated_rows,
    )


def seed_santarosa(county: dict, markets: list[str]) -> dict:
    fips = "12113"
    box = COUNTY_BOX[fips]
    zoning, _, zoning_err = try_overlay(
        LAYERS["santarosa_zoning"],
        ["district", "description"],
        label="Santa Rosa ZONE",
        box=box,
    )
    flu, _, flu_err = try_overlay(
        LAYERS["santarosa_flu"],
        ["category", "descriptio"],
        label="Santa Rosa FLUM",
        box=box,
    )
    milton, _, milton_err = try_overlay(
        LAYERS["milton_zoning"],
        ["zone_code"],
        label="Milton zoning",
        box=box,
    )
    gulf, gulf_ids, gulf_err = try_overlay(
        LAYERS["gulfbreeze_zoning"],
        ["par_num", "zoning", "flum"],
        label="Gulf Breeze zoning",
        box=box,
        id_field="par_num",
    )
    jay, _, jay_err = try_overlay(
        LAYERS["jay_zoning"],
        ["zone", "district"],
        label="Jay zoning",
        box=box,
    )
    where = "Acreage>=5 AND Acreage<=150"
    url = query_url(LAYERS["santarosa_parcels"])
    source_count = count_where(url, where)
    fields = [
        "ParNum",
        "Parcel",
        "Acreage",
        "Owner1",
        "Owner2",
        "MailingAddr1",
        "MailingAddr2",
        "MailingCityStZip",
        "Address",
        "ParStrNum",
        "ParStrName",
        "City",
        "Zipcode",
        "TotalValue",
        "PropertyUse",
    ]
    raw = load_features(url, where, fields)
    hits = {"milton": 0, "gulf": 0, "jay": 0, "county": 0}

    def build(item: dict, county: dict, markets: list[str], source: str) -> dict | None:
        parsed, _ = base_from_item(item, fips, "Acreage")
        if not parsed:
            return None
        attrs = parsed["attrs"]
        parcel_id = clean(attrs.get("ParNum")) or clean(attrs.get("Parcel"))
        if not parcel_id:
            return None
        center = parsed["center"]
        county_zone = hit(zoning, center)
        county_use = hit(flu, center)
        milton_zone = hit(milton, center)
        jay_zone = hit(jay, center)
        gulf_row = gulf_ids.get(norm_id(attrs.get("ParNum")) or "")
        if gulf_row is None:
            gulf_row = hit(gulf, center)
        zoning_code = code_text((county_zone or {}).get("district")) if county_zone else None
        district = clean((county_zone or {}).get("description")) if county_zone else None
        jurisdiction = "Santa Rosa County" if zoning_code or county_use else None
        flu_jurisdiction = "Santa Rosa County"
        flu_row = flu_info(
            (county_use or {}).get("category") if county_use else None,
            (county_use or {}).get("descriptio") if county_use else None,
            flu_jurisdiction,
            LAYERS["santarosa_flu"],
        )
        gaps = [
            "No sale price or sale date on Santa Rosa Basemap Parcels/1.",
            "dorCode is PropertyUse text, not a numeric FDOR use code.",
        ]
        if county_zone or county_use:
            hits["county"] += 1
        if milton_zone:
            hits["milton"] += 1
            zoning_code = code_text(milton_zone.get("zone_code")) or zoning_code
            district = None
            jurisdiction = "Milton"
            gaps.append("Milton FLU is a gap. Future land use stays on Santa Rosa OpenDataFlum when that polygon intersects the parcel.")
            if flu_row:
                flu_row = dict(flu_row)
                flu_row["jurisdiction"] = "Santa Rosa FLUM (no Milton FLU layer)"
        if jay_zone:
            hits["jay"] += 1
            zoning_code = code_text(jay_zone.get("zone")) or zoning_code
            district = clean(jay_zone.get("district"))
            jurisdiction = "Jay"
        if gulf_row:
            hits["gulf"] += 1
            zoning_code = code_text(gulf_row.get("zoning")) or zoning_code
            district = None
            jurisdiction = "Gulf Breeze"
            city_flu = flu_info(gulf_row.get("flum"), gulf_row.get("flum"), "Gulf Breeze", LAYERS["gulfbreeze_zoning"])
            if city_flu:
                flu_row = city_flu
        situs = clean(attrs.get("Address"))
        if not situs:
            number = clean(attrs.get("ParStrNum"))
            street = clean(attrs.get("ParStrName"))
            situs = " ".join(part for part in (number, street) if part) or None
        mail_city, mail_state, mail_zip = split_city_state_zip(attrs.get("MailingCityStZip"))
        return finish_feature(
            county=county,
            markets=markets,
            parcel_id=parcel_id,
            acres=parsed["acres"],
            geometry=parsed["geometry"],
            center=center,
            source=source,
            owner=clean(attrs.get("Owner1")),
            owner2=clean(attrs.get("Owner2")),
            situs=situs,
            city=clean(attrs.get("City")),
            zip_code=zip_str(attrs.get("Zipcode")),
            zoning=zoning_code,
            district=district,
            jurisdiction=jurisdiction,
            prefix=None,
            dor=clean(attrs.get("PropertyUse")),
            sale_price=None,
            sale_date=None,
            sale_qualified=None,
            market_value=money(attrs.get("TotalValue")),
            assessed=None,
            taxable=None,
            mail1=clean(attrs.get("MailingAddr1")),
            mail2=clean(attrs.get("MailingAddr2")),
            mail_city=mail_city,
            mail_state=mail_state,
            mail_zip=mail_zip,
            appraiser="https://srcpa.gov/search",
            flu=flu_row,
            gaps=gaps,
        )

    features, dropped, merged_parts, repeated_rows = dedupe(raw, county, markets, "fl-panhandle-12113", build)
    gulf_n = len(gulf_ids)
    gaps = [
        "No lastSale on Basemap Parcels/1. Market value is TotalValue and is not summed across repeated rows. dorCode is PropertyUse text, not a numeric FDOR code.",
        "This basemap has no stable object id. returnCountOnly counts repeated rows (stacked units and duplicate ids), not unique ParNum values. Identical polygons are stored once. A kept situs may be one unit address, not a rollup of units.",
        (
            "County zoning is Hosted/ZONE district. County FLU is Hosted/OpenDataFlum category. "
            "Milton, Gulf Breeze, and Jay override inside their city layers. "
            f"Hits: county layer {hits['county']}, Milton {hits['milton']}, Gulf Breeze {hits['gulf']}, Jay {hits['jay']}."
        ),
        "Milton zoning is City_of_Milton_Zoning zone_code. Milton FLU was not verified; county FLUM remains for those parcels.",
        (
            f"Gulf Breeze joins Hosted/Gulf_Breeze_Zoning on par_num = ParNum, with a spatial fallback. "
            f"The public layer keyed {gulf_n} parcel ids. It is not a complete citywide district mosaic. "
            "Unmatched parcels are not assumed to be Gulf Breeze, because no separate city-limits layer was on the card. They keep county ZONE/FLUM when those intersect."
        ),
        "Jay zoning is TownOfJayZoning zone (district is the description). No Jay FLU layer was verified.",
        "Pace and Navarre Beach are not separate cities on this card.",
        "Appraiser link is https://srcpa.gov/search. No verified per-parcel deep link is on the layer. Search uses ParNum.",
        "Mailing city/state/zip are parsed from MailingCityStZip. The combined MailingAddr blob repeats the owner name and is not stored.",
        ADJACENT_GAP,
    ]
    for label, err in (
        ("Santa Rosa zoning", zoning_err),
        ("Santa Rosa FLUM", flu_err),
        ("Milton zoning", milton_err),
        ("Gulf Breeze zoning", gulf_err),
        ("Jay zoning", jay_err),
    ):
        if err:
            gaps.append(f"{label} was not applied: {err}")
    return store_county(
        county,
        markets,
        features,
        source="fl-panhandle-12113",
        query=url,
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        merged_parts=merged_parts,
        repeated_rows=repeated_rows,
    )


SEEDERS = {
    "12005": seed_bay,
    "12091": seed_okaloosa,
    "12131": seed_walton,
    "12033": seed_escambia,
    "12113": seed_santarosa,
}


def manifest() -> dict:
    return {
        "generatedFrom": "scripts/seed_panhandle_parcels.py",
        "verifiedOn": "2026-09-23",
        "market": "Pensacola",
        "acreage": {"min": 5, "max": 150},
        "wireOrder": list(WIRE_ORDER),
        "rejected": REJECTED,
        "adjacentGap": ADJACENT_GAP,
        "phonesOrEmails": False,
        "layers": LAYERS,
        "pensacolaCityZoning": {
            "url": PENSACOLA_ZONING_URL,
            "status": "blocked-523",
            "workaround": "Escambia AccelaMain/MapServer/20 zoning and AccelaMain/MapServer/22 FLU until the city REST recovers.",
        },
        "freeportZoning": {
            "url": LAYERS["freeport_zoning"],
            "status": "partial",
            "caveat": "Zoning is a numeric SmallInteger 0–16 with blank Description. Stored as the number. No LDC legend is applied.",
        },
        "counties": [
            {
                "name": "Bay",
                "fips": "12005",
                "parcelUrl": LAYERS["bay_parcels"],
                "acresField": "dtaxacres",
                "parcelId": "a1renum",
                "sale": "sale1pradj / sale1date / sale1qu_vi",
                "situs": "dsiteaddr / dsitezip",
            },
            {
                "name": "Okaloosa",
                "fips": "12091",
                "parcelUrl": LAYERS["okaloosa_parcels"],
                "acresField": "PATPCL_GIS_ACRE",
                "parcelId": "PATPCL_PIN",
                "sale": "PATPCL_SALE1 / PATPCL_SALEDT1 / PATPCL_QUAL1",
                "situs": None,
            },
            {
                "name": "Walton",
                "fips": "12131",
                "parcelUrl": LAYERS["walton_parcels"],
                "acresField": "GIS_ACRES",
                "parcelId": "PARCELNO",
                "sale": "SALE_DATE_1 only; price is a gap",
                "situs": None,
            },
            {
                "name": "Escambia",
                "fips": "12033",
                "parcelUrl": LAYERS["escambia_parcels"],
                "acresField": "LANDSIZE",
                "parcelId": "REFERENCE",
                "sale": None,
                "situs": "SITEADDR / CITY / ZIP",
            },
            {
                "name": "Santa Rosa",
                "fips": "12113",
                "parcelUrl": LAYERS["santarosa_parcels"],
                "acresField": "Acreage",
                "parcelId": "ParNum",
                "sale": None,
                "situs": "Address or ParStrNum + ParStrName / City / Zipcode",
            },
        ],
    }


def write_manifest() -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest(), indent=2) + "\n")


def self_check() -> None:
    for layer in LAYERS.values():
        assert_allowed(layer)
    try:
        assert_allowed(REJECTED[0]["url"])
    except RuntimeError:
        pass
    else:
        raise RuntimeError("FGDL Destin false-positive was not rejected")
    assert parse_sale_date(19770101) == "1977-01-01"
    assert parse_sale_date("2021-06-04") == "2021-06-04"
    assert parse_sale_date("2021-06-26T00:00:00Z") == "2021-06-26"
    assert money(0, drop_nonpositive=True) is None
    index = SpatialIndex()
    exterior = [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]
    hole = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8], [0.2, 0.2]]
    assert index.add([exterior, hole], {"code": "IN"})
    assert (index.query(0.1, 0.1) or {}).get("code") == "IN"
    assert index.query(0.5, 0.5) is None
    assert index.query(2, 2) is None
    write_manifest()


def county_record(catalog: dict, fips: str) -> tuple[dict, list[str]]:
    found = None
    markets: list[str] = []
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips:
                found = county
                if market["id"] not in markets:
                    markets.append(market["id"])
    if not found:
        names = {
            "12005": "Bay",
            "12091": "Okaloosa",
            "12131": "Walton",
            "12033": "Escambia",
            "12113": "Santa Rosa",
        }
        found = {"name": names[fips], "state": "Florida", "fips": fips}
        markets = ["Pensacola"]
    return found, markets


def seed_panhandle_county(county: dict, markets: list[str], *, refresh: bool = False) -> dict:
    fips = county["fips"]
    seeder = SEEDERS.get(fips)
    if not seeder:
        raise RuntimeError(f"{fips} is not a panhandle shelf county")
    existing = COUNTY_DIR / fips / "county.json"
    if existing.exists() and not refresh:
        row = json.loads(existing.read_text())
        if str(row.get("source") or "").startswith("fl-panhandle-") and row.get("featureCount") and row.get("zoningJoinedCount"):
            print(f"Skip {county['name']} {fips} (already fl-panhandle)", flush=True)
            row["markets"] = markets
            existing.write_text(json.dumps(row, indent=2) + "\n")
            return row
    print(f"Panhandle {county['name']} {fips}", flush=True)
    return seeder(county, markets)


def selected_fips(names: list[str]) -> list[str]:
    if not names:
        return list(WIRE_ORDER)
    wanted = []
    aliases = {
        "bay": "12005",
        "okaloosa": "12091",
        "walton": "12131",
        "escambia": "12033",
        "santa rosa": "12113",
        "santarosa": "12113",
    }
    for name in names:
        key = name.strip().lower()
        fips = aliases.get(key, key)
        if fips not in SEEDERS:
            raise SystemExit(f"Unknown panhandle county {name}")
        if fips not in wanted:
            wanted.append(fips)
    return [fips for fips in WIRE_ORDER if fips in wanted]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    self_check()
    catalog = json.loads(CATALOG_PATH.read_text())
    for fips in selected_fips(args.county):
        county, markets = county_record(catalog, fips)
        seed_panhandle_county(county, markets, refresh=args.refresh or True)
    rebuild_indexes(catalog)
    print("Panhandle shelf seed finished.", flush=True)


if __name__ == "__main__":
    main()
