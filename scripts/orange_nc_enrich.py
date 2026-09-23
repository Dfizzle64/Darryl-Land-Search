#!/usr/bin/env python3
"""Orange County, NC (FIPS 37135) 5–150 acre parcel enrich for Raleigh-Durham.

Source of truth: data/gis-sources/nc-37135-orange.json (county card).

Primary parcels are county WebParcelService polygons (owner, mailing, tax,
last sale). Situs is joined from address points by PIN. Zoning is city-first:
Chapel Hill, Carrboro, and Hillsborough district layers inside those towns;
county WebZoningService districts only for unincorporated land. CH/CA/HI/ME/DU
on the county zoning layer are jurisdiction shells and are never stored as
district codes. Carrboro has no public FLU layer.

NC OneMap (cntyfips 135, recareano) is a fallback when the county parcel host
fails. Public GIS only — no paid vendors and no phone or email fields.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from seed_market_parcels import (  # noqa: E402
    CACHE_DIR,
    NC_URL,
    centroid_of,
    clean,
    count_where,
    county_row,
    empty_feature,
    fetch_by_ids,
    fetch_json,
    fetch_object_ids,
    in_band,
    num,
    plausible_centroid,
    rings_to_feature_geometry,
    write_tiles,
    zip_str,
)

FIPS = "37135"
SOURCE = "nc-orange-webparcel-37135"
FALLBACK_SOURCE = "nc-onemap-37135"
PARCEL_QUERY = "https://gis.orangecountync.gov/arcgis/rest/services/WebParcelService/MapServer/0/query"
ADDRESS_QUERY = "https://gis.orangecountync.gov/arcgis/rest/services/WebIdentifyServiceAnalysis/MapServer/1/query"
ADDRESS_ALT_QUERY = "https://gis.orangecountync.gov/arcgis/rest/services/LRCAMA/WebCamaAddresses/MapServer/0/query"
COUNTY_ZONING_QUERY = "https://gis.orangecountync.gov/arcgis/rest/services/WebZoningService/MapServer/22/query"
COUNTY_FLU_QUERY = "https://gis.orangecountync.gov/arcgis/rest/services/Future_Land_Use_Map/MapServer/12/query"
MUNI_QUERY = "https://gis.orangecountync.gov/arcgis/rest/services/WebMainService/MapServer/52/query"
CH_ZONING_QUERY = "https://gis-portal.townofchapelhill.org/server/rest/services/OpenData/Zoning_Districts/FeatureServer/0/query"
CH_FLU_QUERY = "https://services2.arcgis.com/7KRXAKALbBGlCW77/arcgis/rest/services/Future_Land_Use_Map_2050/FeatureServer/8/query"
CARRBORO_ZONING_QUERY = "https://gis.carrboronc.gov/server/rest/services/SP/ZoningSP/MapServer/30/query"
CARRBORO_CONDITIONAL_QUERY = "https://gis.carrboronc.gov/server/rest/services/SP/ZoningSP/MapServer/20/query"
HILLSBOROUGH_ZONING_QUERY = "https://services5.arcgis.com/m711BZ7Df3seMOYp/arcgis/rest/services/ZoningLayersII/FeatureServer/3/query"
HILLSBOROUGH_FLU_QUERY = "https://services5.arcgis.com/m711BZ7Df3seMOYp/arcgis/rest/services/HillsboroughLandUseII/FeatureServer/3/query"
APPRAISER_TEMPLATE = "https://property.spatialest.com/nc/orange/#/property/{pin}"
ACREAGE_WHERE = "CALC_ACRES >= 5 AND CALC_ACRES <= 150"
ONEMAP_WHERE = "cntyfips='135' AND recareano >= 5 AND recareano <= 150"

# County zoning layer uses these as jurisdiction placeholders, not districts.
SHELL_CODES = frozenset({"CH", "CA", "HI", "ME", "DU"})

CITY_TOKENS = (
    ("chapel hill", "chapel-hill"),
    ("carrboro", "carrboro"),
    ("hillsborough", "hillsborough"),
    ("mebane", "mebane"),
    ("durham", "durham"),
)

JURISDICTION = {
    "chapel-hill": ("CH", "Chapel Hill"),
    "carrboro": ("CA", "Carrboro"),
    "hillsborough": ("HI", "Hillsborough"),
    "mebane": ("ME", "Mebane"),
    "durham": ("DU", "Durham"),
    "county": ("OC", "Orange County"),
}

MUNI_NAME = {
    "CHAPEL HILL": "chapel-hill",
    "CARRBORO": "carrboro",
    "HILLSBOROUGH": "hillsborough",
    "MEBANE": "mebane",
    "DURHAM": "durham",
}
MUNI_CODE = {"CH": "chapel-hill", "CA": "carrboro", "HI": "hillsborough", "ME": "mebane", "DU": "durham"}

GAPS = [
    "Acreage is county GIS CALC_ACRES in the inclusive 5–150 band. Deed SIZE can differ and is not the filter.",
    "Situs is not on parcel polygons. Address points are joined by PIN from WebIdentifyServiceAnalysis/1. LRCAMA/WebCamaAddresses fills PINs that layer missed. PrimaryFlag YES is preferred.",
    "County WebZoningService district codes are used only for unincorporated County. CH, CA, HI, ME, and DU are jurisdiction shells and are never stored as zoning.",
    "Chapel Hill zoning is OpenData Zoning_Districts, Carrboro is ZoningSP/30 (conditional ZoningSP/20 when the PIN is listed), and Hillsborough is ZoningLayersII/3. Joined by a point inside the parcel.",
    "FLU is city-first: Chapel Hill Future Land Use Map 2050 (requested in WGS84; source is Web Mercator) and Hillsborough Land Use. County Future_Land_Use_Map/12 covers unincorporated land and Mebane/Durham edge. Carrboro has no public FLU FeatureServer.",
    "Last sale price is STAMPVALUE, a tax-stamp proxy, not deed consideration. There is no multi-sale history layer.",
    "tax.marketValue is total VALUATION, tax.assessedValue is LANDVALUE, and tax.taxableValue is USEVALUE when the parcel is in present-use. Building value is not a separate field.",
    "Mebane and Durham edge parcels have no Orange-hosted district zoning.",
    "Overlay districts (Chapel Hill, Carrboro, Hillsborough) are not joined.",
    "NC OneMap is fallback only (cntyfips 135, recareano). OneMap gisacres is 0 and siteadd is empty for Orange.",
    "No phones or emails. Public GIS only.",
]

PARCEL_FIELDS = [
    "PIN",
    "OWNER1",
    "OWNER1_LAST",
    "OWNER1_FIRST",
    "OWNER2",
    "OWNER2_LAST",
    "OWNER2_FIRST",
    "ADDRESS1",
    "ADDRESS2",
    "CITY",
    "STATE",
    "ZIPCODE",
    "CALC_ACRES",
    "DATESOLD",
    "DATESOLDTXT",
    "STAMPVALUE",
    "VALUATION",
    "LANDVALUE",
    "USEVALUE",
    "Zonings",
    "Zoning_Admin",
]
ADDRESS_FIELDS = ["PIN", "Add_St", "NG_FullAddress", "MailingCity", "ZipCode", "State", "PrimaryFlag"]
RAW_DIR = Path("/tmp/dls-orange-nc")


def district_code(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    if text.upper() in SHELL_CODES:
        return None
    return text


def cities_in_admin(admin: Any) -> list[str]:
    text = (clean(admin) or "").lower()
    return [code for token, code in CITY_TOKENS if token in text]


def person_name(display: Any, last: Any, first: Any) -> str | None:
    shown = clean(display)
    if shown:
        return shown
    parts = [part for part in (clean(first), clean(last)) if part]
    return " ".join(parts) or None


def money(value: Any) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def esri_date(value: Any) -> str | None:
    parsed = num(value)
    if parsed is None:
        return None
    seconds = parsed / 1000.0 if abs(parsed) > 10_000_000_000 else parsed
    try:
        stamp = datetime.fromtimestamp(seconds, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    if stamp.year < 1900 or stamp.year > 2100:
        return None
    return stamp.date().isoformat()


def parse_date_text(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    collapsed = re.sub(r"\s+", " ", text).strip()
    for fmt in ("%b %d %Y %I:%M%p", "%B %d %Y %I:%M%p", "%b %d %Y", "%B %d %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(collapsed, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def sale_date(epoch: Any, text: Any) -> str | None:
    return esri_date(epoch) or parse_date_text(epoch) or parse_date_text(text)


def appraiser_url(pin: str) -> str:
    return APPRAISER_TEMPLATE.format(pin=pin)


def is_primary_flag(value: Any) -> bool:
    return (clean(value) or "").upper() in {"YES", "Y", "TRUE", "1"}


def choose_situs(rows: list[dict]) -> dict[str, str | None] | None:
    usable = [row for row in rows if clean(row.get("Add_St")) or clean(row.get("NG_FullAddress"))]
    if not usable:
        return None
    usable.sort(key=lambda row: (0 if is_primary_flag(row.get("PrimaryFlag")) else 1, 0 if clean(row.get("Add_St")) else 1))
    best = usable[0]
    return {
        "situsAddress": clean(best.get("Add_St")) or clean(best.get("NG_FullAddress")),
        "situsCity": clean(best.get("MailingCity")),
        "situsZip": zip_str(best.get("ZipCode")),
        "situsState": clean(best.get("State")),
    }


def parse_pin_list(value: Any) -> list[str]:
    text = clean(value) or ""
    return [part for part in re.split(r"[,;\s]+", text) if part]


def _point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            denom = yj - yi
            if denom != 0 and x < (xj - xi) * (y - yi) / denom + xi:
                inside = not inside
        j = i
    return inside


def point_in_rings(x: float, y: float, rings: list[list[tuple[float, float]]]) -> bool:
    inside = False
    for ring in rings:
        if len(ring) >= 3 and _point_in_ring(x, y, ring):
            inside = not inside
    return inside


def _ring_area(ring: list[tuple[float, float]]) -> float:
    area = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _as_rings(geometry: dict | None) -> list[list[tuple[float, float]]]:
    if not geometry:
        return []
    raw_rings = geometry.get("rings")
    if not raw_rings:
        return []
    rings: list[list[tuple[float, float]]] = []
    for ring in raw_rings:
        coords = [(float(x), float(y)) for x, y in ring]
        if len(coords) >= 3:
            rings.append(coords)
    return rings


def interior_point(rings: list[list[tuple[float, float]]]) -> tuple[float, float] | None:
    if not rings or len(rings[0]) < 3:
        return None
    outer = rings[0]
    pts = outer[:-1] if outer[0] == outer[-1] and len(outer) > 1 else outer
    if not pts:
        return None
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    if point_in_rings(cx, cy, rings):
        return cx, cy
    for i in range(len(pts)):
        x2, y2 = pts[(i + 1) % len(pts)]
        mx = (pts[i][0] + x2) / 2.0
        my = (pts[i][1] + y2) / 2.0
        tx = (mx * 2.0 + cx) / 3.0
        ty = (my * 2.0 + cy) / 3.0
        if point_in_rings(tx, ty, rings):
            return tx, ty
    return cx, cy


class PolyIndex:
    def __init__(self, items: list[dict]):
        self.items = items

    def hits(self, x: float, y: float) -> list[dict]:
        found = []
        for item in self.items:
            minx, miny, maxx, maxy = item["bbox"]
            if x < minx or x > maxx or y < miny or y > maxy:
                continue
            if point_in_rings(x, y, item["rings"]):
                found.append(item)
        return found


def index_polygons(features: list[dict], read: Callable[[dict], dict | None]) -> PolyIndex:
    items: list[dict] = []
    for feature in features:
        payload = read(feature.get("attributes") or {})
        if not payload:
            continue
        rings = _as_rings(feature.get("geometry"))
        if not rings:
            continue
        xs = [p[0] for ring in rings for p in ring]
        ys = [p[1] for ring in rings for p in ring]
        if not xs:
            continue
        items.append(
            {
                **payload,
                "rings": rings,
                "bbox": (min(xs), min(ys), max(xs), max(ys)),
                "area": _ring_area(rings[0]),
            }
        )
    return PolyIndex(items)


def _pick(hits: list[dict], admin: Any) -> dict | None:
    if not hits:
        return None
    preferred = cities_in_admin(admin)
    for city in preferred:
        named = [hit for hit in hits if hit.get("jurisdiction") == city]
        if named:
            return min(named, key=lambda hit: hit["area"])
    return min(hits, key=lambda hit: hit["area"])


def assign_land_use(
    x: float,
    y: float,
    admin: Any,
    pin: str,
    *,
    chapel_hill_zoning: PolyIndex,
    carrboro_zoning: PolyIndex,
    hillsborough_zoning: PolyIndex,
    county_zoning: PolyIndex,
    municipal: PolyIndex,
    chapel_hill_flu: PolyIndex,
    hillsborough_flu: PolyIndex,
    county_flu: PolyIndex,
    carrboro_conditional: dict[str, str],
    county_attribute: Any,
) -> dict[str, Any]:
    city_hits = (
        chapel_hill_zoning.hits(x, y) + carrboro_zoning.hits(x, y) + hillsborough_zoning.hits(x, y)
    )
    city = _pick(city_hits, admin)
    boundary = _pick(municipal.hits(x, y), admin)
    jurisdiction = None
    zoning = None
    zoning_label = None
    if city:
        jurisdiction = city["jurisdiction"]
        zoning = city.get("code")
        zoning_label = city.get("label")
        if jurisdiction == "carrboro":
            conditional = carrboro_conditional.get(pin)
            if conditional:
                zoning = conditional
                zoning_label = zoning_label or "Conditional zoning"
    elif boundary and boundary.get("jurisdiction") in {"chapel-hill", "carrboro", "hillsborough", "mebane", "durham"}:
        jurisdiction = boundary["jurisdiction"]
    else:
        named = cities_in_admin(admin)
        admin_text = (clean(admin) or "").lower()
        if named and "county" not in admin_text:
            jurisdiction = named[0]
        else:
            jurisdiction = "county"
            zoning = district_code(county_attribute)
            if zoning is None:
                county_hit = _pick(county_zoning.hits(x, y), None)
                if county_hit:
                    zoning = county_hit.get("code")
                    zoning_label = county_hit.get("label")

    if jurisdiction in {"mebane", "durham"}:
        zoning = None
        zoning_label = None

    flu = None
    if jurisdiction == "chapel-hill":
        flu_hit = _pick(chapel_hill_flu.hits(x, y), None)
        if flu_hit:
            flu = flu_hit["flu"]
    elif jurisdiction == "hillsborough":
        flu_hit = _pick(hillsborough_flu.hits(x, y), None)
        if flu_hit:
            flu = flu_hit["flu"]
    elif jurisdiction == "carrboro":
        flu = None
    else:
        flu_hit = _pick(county_flu.hits(x, y), None)
        if flu_hit:
            flu = flu_hit["flu"]

    code, label = JURISDICTION.get(jurisdiction or "county", ("OC", "Orange County"))
    return {
        "jurisdiction": jurisdiction or "county",
        "jurisdictionCode": code,
        "jurisdictionLabel": label,
        "zoningCode": zoning,
        "zoningDistrict": zoning_label,
        "flu": flu,
    }


def _layer_base(query_url: str) -> str:
    base = query_url.split("?")[0]
    if base.endswith("/query"):
        return base[: -len("/query")]
    return base


def object_id_field(query_url: str) -> str:
    try:
        meta = fetch_json(_layer_base(query_url), {"f": "json"})
    except Exception:  # noqa: BLE001
        return "OBJECTID"
    return str(meta.get("objectIdField") or "OBJECTID")


def page_attributes(url: str, where: str, fields: list[str], page_size: int = 2000) -> list[dict]:
    oid = object_id_field(url)
    offset = 0
    rows: list[dict] = []
    while offset < 250_000:
        params = {
            "where": where,
            "outFields": ",".join(fields),
            "returnGeometry": "false",
            "orderByFields": oid,
            "resultOffset": str(offset),
            "resultRecordCount": str(page_size),
            "f": "json",
        }
        data = fetch_json(url, params, timeout=180)
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        feats = data.get("features") or []
        rows.extend(feats)
        if not feats or (not data.get("exceededTransferLimit") and len(feats) < page_size):
            break
        offset += len(feats)
    return rows


def fetch_layer(url: str, where: str, fields: list[str]) -> list[dict]:
    ids = fetch_object_ids(url, where)
    if not ids:
        return []
    print(f"    {url.split('/services/')[-1][:80]} ids {len(ids)}", flush=True)
    return fetch_by_ids(url, ids, fields, batch=80)


def _load_raw(name: str, loader: Callable[[], Any]) -> Any:
    path = RAW_DIR / f"{name}.json"
    if path.exists():
        print(f"  raw cache {name}", flush=True)
        return json.loads(path.read_text())
    data = loader()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


def _address_index(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for feature in rows:
        attrs = feature.get("attributes") or feature
        pin = clean(attrs.get("PIN"))
        if not pin:
            continue
        grouped.setdefault(pin, []).append(attrs)
    return grouped


def fetch_addresses_for_pins(url: str, pins: list[str]) -> list[dict]:
    rows: list[dict] = []
    step = 80
    for start in range(0, len(pins), step):
        chunk = pins[start : start + step]
        quoted = ",".join("'" + pin.replace("'", "") + "'" for pin in chunk)
        try:
            rows.extend(page_attributes(url, f"PIN IN ({quoted})", ADDRESS_FIELDS))
        except Exception as exc:  # noqa: BLE001
            print(f"    address batch failed ({exc}); shrinking", flush=True)
            for pin in chunk:
                try:
                    rows.extend(page_attributes(url, f"PIN='{pin}'", ADDRESS_FIELDS, page_size=50))
                except Exception as inner:  # noqa: BLE001
                    print(f"    skip pin {pin}: {inner}", flush=True)
        if start % 800 == 0:
            print(f"    addresses {min(start + step, len(pins))}/{len(pins)}", flush=True)
        time.sleep(0.02)
    return rows


def _flu_payload(code: str, jurisdiction: str, source: str) -> dict:
    return {"code": code, "label": code, "jurisdiction": jurisdiction, "source": source}


def build_indexes(layers: dict[str, list[dict]]) -> dict[str, Any]:
    def zoning_reader(field: str, jurisdiction: str):
        def read(attrs: dict) -> dict | None:
            code = district_code(attrs.get(field))
            if not code:
                return None
            label = clean(attrs.get("Zoning_Def")) or clean(attrs.get("DEFINITION")) or clean(attrs.get("NAME"))
            return {"jurisdiction": jurisdiction, "code": code, "label": label}

        return read

    def flu_reader(field: str, jurisdiction: str, source: str):
        def read(attrs: dict) -> dict | None:
            code = clean(attrs.get(field))
            if not code:
                return None
            return {"jurisdiction": jurisdiction, "flu": _flu_payload(code, jurisdiction, source)}

        return read

    def muni_reader(attrs: dict) -> dict | None:
        name = (clean(attrs.get("NAME")) or "").upper()
        code = (clean(attrs.get("CITYCODE")) or "").upper()
        jurisdiction = MUNI_NAME.get(name) or MUNI_CODE.get(code)
        if not jurisdiction:
            return None
        return {"jurisdiction": jurisdiction}

    def county_zoning_reader(attrs: dict) -> dict | None:
        jur = (clean(attrs.get("Jur")) or "").lower()
        if jur and jur != "county":
            return None
        code = district_code(attrs.get("Zoning"))
        if not code:
            return None
        return {"jurisdiction": "county", "code": code, "label": clean(attrs.get("Zoning_Def"))}

    conditional: dict[str, str] = {}
    for feature in layers.get("carrboro_conditional") or []:
        attrs = feature.get("attributes") or {}
        code = district_code(attrs.get("ZONING"))
        if not code:
            continue
        for pin in parse_pin_list(attrs.get("PINs")):
            conditional.setdefault(pin, code)

    return {
        "chapel_hill_zoning": index_polygons(layers.get("chapel_hill_zoning") or [], zoning_reader("ZONING", "chapel-hill")),
        "carrboro_zoning": index_polygons(layers.get("carrboro_zoning") or [], zoning_reader("ZONING", "carrboro")),
        "hillsborough_zoning": index_polygons(layers.get("hillsborough_zoning") or [], zoning_reader("ZoningType", "hillsborough")),
        "county_zoning": index_polygons(layers.get("county_zoning") or [], county_zoning_reader),
        "municipal": index_polygons(layers.get("municipal") or [], muni_reader),
        "chapel_hill_flu": index_polygons(layers.get("chapel_hill_flu") or [], flu_reader("LANDUSE", "Chapel Hill", "chapel-hill-flu-2050")),
        "hillsborough_flu": index_polygons(layers.get("hillsborough_flu") or [], flu_reader("MH_LU", "Hillsborough", "hillsborough-land-use")),
        "county_flu": index_polygons(layers.get("county_flu") or [], flu_reader("Legend", "Orange County", "orange-county-flu")),
        "carrboro_conditional": conditional,
    }


def features_from_parcels(
    raw: list[dict],
    county: dict,
    markets: list[str],
    *,
    addresses: dict[str, list[dict]],
    indexes: dict[str, Any],
    source: str,
    acres_field: str,
) -> tuple[list[dict], dict[str, int]]:
    by_id: dict[str, dict] = {}
    stats = {
        "situs": 0,
        "zoning": 0,
        "flu": 0,
        "chapel-hill": 0,
        "carrboro": 0,
        "hillsborough": 0,
        "county": 0,
        "mebane": 0,
        "durham": 0,
        "dropped": 0,
    }
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed = rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            stats["dropped"] += 1
            continue
        center = centroid_of(geometry)
        if not plausible_centroid(center):
            stats["dropped"] += 1
            continue
        acres = num(attrs.get(acres_field))
        if acres is None:
            acres = _computed
        if not in_band(acres):
            stats["dropped"] += 1
            continue
        pin = clean(attrs.get("PIN")) or clean(attrs.get("parno"))
        if not pin:
            stats["dropped"] += 1
            continue
        situs = choose_situs(addresses.get(pin) or [])
        rings = _as_rings(item.get("geometry"))
        point = interior_point(rings) or center
        land = assign_land_use(
            point[0],
            point[1],
            attrs.get("Zoning_Admin"),
            pin,
            chapel_hill_zoning=indexes["chapel_hill_zoning"],
            carrboro_zoning=indexes["carrboro_zoning"],
            hillsborough_zoning=indexes["hillsborough_zoning"],
            county_zoning=indexes["county_zoning"],
            municipal=indexes["municipal"],
            chapel_hill_flu=indexes["chapel_hill_flu"],
            hillsborough_flu=indexes["hillsborough_flu"],
            county_flu=indexes["county_flu"],
            carrboro_conditional=indexes["carrboro_conditional"],
            county_attribute=attrs.get("Zonings"),
        )
        price = money(attrs.get("STAMPVALUE"))
        sale_on = sale_date(attrs.get("DATESOLD") or attrs.get("saledate"), attrs.get("DATESOLDTXT") or attrs.get("saledatetx"))
        owner = person_name(attrs.get("OWNER1") or attrs.get("ownname"), attrs.get("OWNER1_LAST"), attrs.get("OWNER1_FIRST"))
        owner2 = person_name(attrs.get("OWNER2"), attrs.get("OWNER2_LAST"), attrs.get("OWNER2_FIRST"))
        feature = empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=pin,
            acreage=acres,
            geometry=geometry,
            center=center,  # type: ignore[arg-type]
            source=source,
            owner=owner,
            situs=situs["situsAddress"] if situs else clean(attrs.get("siteadd")),
            city=situs["situsCity"] if situs else clean(attrs.get("scity")),
            zip_code=situs["situsZip"] if situs else zip_str(attrs.get("szip")),
            zoning=land["zoningCode"],
            sale_price=price,
            sale_date=sale_on,
            sale_qualified="tax-stamp" if price else None,
            market_value=money(attrs.get("VALUATION") if "VALUATION" in attrs else attrs.get("parval")),
            assessed=money(attrs.get("LANDVALUE") if "LANDVALUE" in attrs else attrs.get("landval")),
            taxable=money(attrs.get("USEVALUE")),
            mail1=clean(attrs.get("ADDRESS1") or attrs.get("mailadd")),
            mail2=clean(attrs.get("ADDRESS2")),
            mail_city=clean(attrs.get("CITY") or attrs.get("mcity")),
            mail_state=clean(attrs.get("STATE") or attrs.get("mstate")),
            mail_zip=zip_str(attrs.get("ZIPCODE") or attrs.get("mzip")),
        )
        props = feature["properties"]
        props["ownerName2"] = owner2
        props["zoningDistrict"] = land["zoningDistrict"]
        props["jurisdictionCode"] = land["jurisdictionCode"]
        props["jurisdictionPrefix"] = land["jurisdictionCode"]
        props["flu"] = land["flu"]
        props["appraiserUrl"] = appraiser_url(pin)
        gaps: list[str] = []
        if price:
            gaps.append("Last sale price is a tax-stamp proxy, not deed consideration.")
        if land["jurisdiction"] == "carrboro":
            gaps.append("Carrboro has no public future land use layer.")
        if land["jurisdiction"] in {"mebane", "durham"}:
            gaps.append("No Orange-hosted district zoning for this municipality.")
        if gaps:
            props["dataGaps"] = gaps
        juris = land["jurisdiction"]
        if juris in stats:
            stats[juris] += 1
        if situs and situs.get("situsAddress"):
            stats["situs"] += 1
        if land["zoningCode"]:
            stats["zoning"] += 1
        if land["flu"]:
            stats["flu"] += 1
        previous = by_id.get(pin)
        if previous is None or (props["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[pin] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, stats


def _empty_indexes() -> dict[str, Any]:
    return {
        "chapel_hill_zoning": PolyIndex([]),
        "carrboro_zoning": PolyIndex([]),
        "hillsborough_zoning": PolyIndex([]),
        "county_zoning": PolyIndex([]),
        "municipal": PolyIndex([]),
        "chapel_hill_flu": PolyIndex([]),
        "hillsborough_flu": PolyIndex([]),
        "county_flu": PolyIndex([]),
        "carrboro_conditional": {},
    }


def load_join_layers() -> dict[str, Any]:
    specs = {
        "county_zoning": (COUNTY_ZONING_QUERY, "Jur='County'", ["Zoning", "Zoning_Def", "Jur", "Zoning_Admin"]),
        "county_flu": (COUNTY_FLU_QUERY, "1=1", ["Legend"]),
        "municipal": (MUNI_QUERY, "1=1", ["NAME", "CITYCODE"]),
        "chapel_hill_zoning": (CH_ZONING_QUERY, "1=1", ["ZONING", "NAME"]),
        "chapel_hill_flu": (CH_FLU_QUERY, "1=1", ["LANDUSE"]),
        "carrboro_zoning": (CARRBORO_ZONING_QUERY, "1=1", ["ZONING", "DEFINITION"]),
        "carrboro_conditional": (CARRBORO_CONDITIONAL_QUERY, "1=1", ["ZONING", "PINs"]),
        "hillsborough_zoning": (HILLSBOROUGH_ZONING_QUERY, "1=1", ["ZoningType", "ZoningCategory"]),
        "hillsborough_flu": (HILLSBOROUGH_FLU_QUERY, "1=1", ["MH_LU"]),
    }
    layers: dict[str, list[dict]] = {}
    for name, (url, where, fields) in specs.items():
        def loader(url=url, where=where, fields=fields, name=name) -> list[dict]:
            if name == "carrboro_conditional":
                return page_attributes(url, where, fields)
            return fetch_layer(url, where, fields)

        try:
            layers[name] = _load_raw(name, loader)
        except Exception as exc:  # noqa: BLE001
            print(f"  join layer {name} failed: {exc}", flush=True)
            layers[name] = []
    return build_indexes(layers)


def load_addresses(pins: list[str], *, cache: bool = True) -> dict[str, list[dict]]:
    def primary() -> list[dict]:
        return fetch_addresses_for_pins(ADDRESS_QUERY, pins)

    try:
        primary_rows = _load_raw("addresses-primary", primary) if cache else primary()
    except Exception as exc:  # noqa: BLE001
        print(f"  primary situs failed: {exc}", flush=True)
        primary_rows = []
    grouped = _address_index(primary_rows)
    missing = [pin for pin in pins if pin not in grouped]
    if missing:
        print(f"  situs fallback for {len(missing)} PINs", flush=True)

        def alt() -> list[dict]:
            return fetch_addresses_for_pins(ADDRESS_ALT_QUERY, missing)

        try:
            alt_rows = _load_raw("addresses-alt", alt) if cache else alt()
        except Exception as exc:  # noqa: BLE001
            print(f"  alternate situs failed: {exc}", flush=True)
            alt_rows = []
        for pin, rows in _address_index(alt_rows).items():
            grouped.setdefault(pin, rows)
    return grouped


def pull_county_parcels(limit: int | None = None) -> tuple[list[dict], int]:
    def loader() -> list[dict]:
        ids = fetch_object_ids(PARCEL_QUERY, ACREAGE_WHERE)
        use = ids[:limit] if limit else ids
        print(f"  parcel ids {len(use)}", flush=True)
        return fetch_by_ids(PARCEL_QUERY, use, PARCEL_FIELDS, batch=60)

    raw = _load_raw("parcels" if not limit else f"parcels-{limit}", loader)
    return raw, count_where(PARCEL_QUERY, ACREAGE_WHERE)


def pull_onemap_parcels() -> tuple[list[dict], int]:
    fields = ["parno", "ownname", "mailadd", "mcity", "mstate", "mzip", "siteadd", "scity", "recareano", "parval", "landval", "saledate", "saledatetx"]
    ids = fetch_object_ids(NC_URL, ONEMAP_WHERE)
    print(f"  onemap ids {len(ids)}", flush=True)
    raw = fetch_by_ids(NC_URL, ids, fields, batch=80)
    return raw, len(ids)


def build_features(county: dict, markets: list[str], *, limit: int | None = None) -> tuple[list[dict], dict[str, Any]]:
    raw, source_count = pull_county_parcels(limit)
    pins = []
    for item in raw:
        pin = clean((item.get("attributes") or {}).get("PIN"))
        if pin:
            pins.append(pin)
    addresses = load_addresses(sorted(set(pins)), cache=limit is None)
    indexes = load_join_layers()
    features, stats = features_from_parcels(
        raw,
        county,
        markets,
        addresses=addresses,
        indexes=indexes,
        source=SOURCE,
        acres_field="CALC_ACRES",
    )
    stats["sourceCount"] = source_count if not limit else len(raw)
    stats["source"] = SOURCE
    return features, stats


def build_fallback_features(county: dict, markets: list[str]) -> tuple[list[dict], dict[str, Any]]:
    raw, source_count = pull_onemap_parcels()
    pins = [clean((item.get("attributes") or {}).get("parno")) for item in raw]
    pins = [pin for pin in pins if pin]
    try:
        addresses = load_addresses(sorted(set(pins)))
    except Exception as exc:  # noqa: BLE001
        print(f"  fallback situs skipped: {exc}", flush=True)
        addresses = {}
    try:
        indexes = load_join_layers()
    except Exception as exc:  # noqa: BLE001
        print(f"  fallback zoning skipped: {exc}", flush=True)
        indexes = _empty_indexes()
    features, stats = features_from_parcels(
        raw,
        county,
        markets,
        addresses=addresses,
        indexes=indexes,
        source=FALLBACK_SOURCE,
        acres_field="recareano",
    )
    stats["sourceCount"] = source_count
    stats["source"] = FALLBACK_SOURCE
    return features, stats


def download_orange_nc(county: dict, markets: list[str], spec: dict) -> dict:
    fips = county["fips"]
    cache_path = CACHE_DIR / f"{fips}.json"
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features:
            print(f"  cache hit {len(features)}", flush=True)
            for feature in features:
                feature["properties"]["marketIds"] = markets
            path, lookup, tiles = write_tiles(county, features)
            row = county_row(
                county,
                markets,
                feature_count=len(features),
                coverage=spec.get("coverage") or "complete-gte-5ac",
                partition="tiles",
                path=path,
                lookup=lookup,
                source=cached.get("source") or SOURCE,
                query_url=spec.get("url") or PARCEL_QUERY,
                gaps=list(cached.get("gaps") or GAPS),
                source_count=cached.get("sourceCount"),
                dropped=cached.get("dropped"),
                tile_count=tiles,
            )
            if cached.get("enrich"):
                row["enrich"] = cached["enrich"]
                (ROOT / "data" / "fixtures" / "market-parcels" / "counties" / fips / "county.json").write_text(
                    json.dumps(row, indent=2) + "\n"
                )
            return row

    print(f"Pulling Orange County NC ({fips}) from WebParcelService", flush=True)
    gaps = list(GAPS)
    query_url = PARCEL_QUERY
    source = SOURCE
    try:
        features, stats = build_features(county, markets)
    except Exception as exc:  # noqa: BLE001
        print(f"  county parcels failed ({exc}); NC OneMap fallback", flush=True)
        features, stats = build_fallback_features(county, markets)
        source = FALLBACK_SOURCE
        query_url = NC_URL
        gaps = [
            f"County WebParcelService failed ({exc}). Fell back to NC OneMap cntyfips 135 using recareano.",
            *GAPS,
        ]
    if not features:
        raise RuntimeError("Orange County NC enrich produced no 5–150 acre parcels")
    if not all(in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Orange County NC emitted a parcel outside 5–150 acres")
    enrich = {
        "situsMatched": stats.get("situs", 0),
        "zoningMatched": stats.get("zoning", 0),
        "fluMatched": stats.get("flu", 0),
        "jurisdictions": {
            "chapelHill": stats.get("chapel-hill", 0),
            "carrboro": stats.get("carrboro", 0),
            "hillsborough": stats.get("hillsborough", 0),
            "county": stats.get("county", 0),
            "mebane": stats.get("mebane", 0),
            "durham": stats.get("durham", 0),
        },
    }
    print(
        f"  kept {len(features)} situs {enrich['situsMatched']} zoning {enrich['zoningMatched']} flu {enrich['fluMatched']}",
        flush=True,
    )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "sourceCount": stats.get("sourceCount"),
                "dropped": stats.get("dropped"),
                "source": source,
                "gaps": gaps,
                "enrich": enrich,
                "features": features,
            },
            separators=(",", ":"),
        )
    )
    path, lookup, tiles = write_tiles(county, features)
    row = county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=source,
        query_url=query_url,
        gaps=gaps,
        source_count=stats.get("sourceCount"),
        dropped=stats.get("dropped"),
        tile_count=tiles,
    )
    row["enrich"] = enrich
    (ROOT / "data" / "fixtures" / "market-parcels" / "counties" / fips / "county.json").write_text(json.dumps(row, indent=2) + "\n")
    return row


def _smoke(limit: int) -> None:
    county = {"name": "Orange", "fips": FIPS, "state": "North Carolina"}
    features, stats = build_features(county, ["Raleigh-Durham"], limit=limit)
    shells = [f for f in features if (f["properties"].get("zoningCode") or "").upper() in SHELL_CODES]
    carrboro_flu = [
        f
        for f in features
        if f["properties"].get("jurisdictionCode") == "CA" and f["properties"].get("flu")
    ]
    print(json.dumps({"features": len(features), "shells": len(shells), "carrboroFlu": len(carrboro_flu), "stats": stats}, indent=2))
    if features:
        sample = features[0]["properties"]
        print(json.dumps({k: sample[k] for k in ("parcelId", "ownerName", "situsAddress", "zoningCode", "jurisdictionCode", "flu", "appraiserUrl", "mailingAddress", "lastSale", "tax")}, indent=2))
    if shells or carrboro_flu:
        raise SystemExit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", type=int, default=0)
    args = parser.parse_args()
    if args.smoke:
        _smoke(args.smoke)
    else:
        raise SystemExit("Use scripts/seed_market_parcels.py --market Raleigh-Durham --county Orange --refresh")
