#!/usr/bin/env python3
"""Dickson County, Tennessee (FIPS 47043) parcel extract for the Nashville market.

IMPACT county number is 22 (JUR '022'). That is the Comptroller id, not FIPS 043.
Geometry: IMPACT Parcels/0, PARCEL_TYPE=1, CALC_ACRE inclusive 5–150.
Attributes: Parcel_Layer_Themes/12 joined on GISLINK, latest TAXYR.
Zoning: City of Dickson Current_Zo, White Bluff Zone_Curre, county Zone_Curre
after city-limits resolution. Burns / Charlotte / Vanleer / Slayden and FLU stay null.

If maps.cot.tn.gov returns 403, pass --shapefile-dir pointing at the weekly
Comptroller zip contents (parcel polygons plus Assessment_Data_022.dbf).

  python3 scripts/seed_dickson_parcels.py
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from seed_market_parcels import (
    COUNTY_DIR,
    MAX_ACRES,
    MIN_ACRES,
    ROOT,
    centroid_of,
    clean,
    county_row,
    empty_feature,
    in_band,
    num,
    plausible_centroid,
    rings_to_feature_geometry,
    write_tiles,
    zip_str,
)

FIPS = "47043"
COUNTY_ID = 22
JUR = "022"
GEOM_URL = "https://maps.cot.tn.gov/server3/rest/services/IMPACT/Parcels/FeatureServer/0/query"
THEMES_URL = "https://maps.cot.tn.gov/server3/rest/services/IMPACT/Parcel_Layer_Themes/FeatureServer/12/query"
CITY_LIMITS_URL = "https://services5.arcgis.com/o0K7afBI69raYtru/arcgis/rest/services/City_Limits_Dickson_County/FeatureServer/0/query"
COUNTY_BOUNDARY_URL = "https://services5.arcgis.com/o0K7afBI69raYtru/arcgis/rest/services/Dickson_County_Boundary/FeatureServer/0/query"
DICKSON_ZONING_URL = "https://services7.arcgis.com/Gld89lf779txw3q4/arcgis/rest/services/City_of_Dickson_Zoning_View/FeatureServer/0/query"
WHITE_BLUFF_ZONING_URL = "https://services5.arcgis.com/o0K7afBI69raYtru/arcgis/rest/services/WhiteBluff_Zoning/FeatureServer/0/query"
COUNTY_ZONING_URL = "https://services5.arcgis.com/o0K7afBI69raYtru/arcgis/rest/services/Dickson_County_Zoning/FeatureServer/0/query"
CACHE_DIR = Path("/tmp/dls-dickson")
SOURCE = "tn-impact-47043"

# Assessor tax-district codes. Polygon city limits win when they disagree.
CITYNUM_TO_NAME = {
    "203": "Dickson",
    "770": "White Bluff",
    "102": "Burns",
    "129": "Charlotte",
    "749": "Vanleer",
    "668": "Slayden",
}
GAP_TOWNS = {"Burns", "Charlotte", "Vanleer", "Slayden"}
ZONING_SOURCES = {
    "Dickson": {
        "url": DICKSON_ZONING_URL,
        "code": "Current_Zo",
        "desc": "Zoning_Des",
        "label": "City of Dickson City_of_Dickson_Zoning_View Current_Zo",
    },
    "White Bluff": {
        "url": WHITE_BLUFF_ZONING_URL,
        "code": "Zone_Curre",
        "desc": "ZoneDesc",
        "descFallback": "Zone_Descr",
        "label": "White Bluff WhiteBluff_Zoning Zone_Curre",
    },
    "Dickson County": {
        "url": COUNTY_ZONING_URL,
        "code": "Zone_Curre",
        "desc": "Zoning_Des",
        "label": "Dickson County Dickson_County_Zoning Zone_Curre",
    },
}
THEME_FIELDS = [
    "GISLINK",
    "JUR",
    "PARID",
    "TAXYR",
    "PARCELID",
    "ID",
    "CITYNUM",
    "ST_NUM",
    "STREET",
    "ADDRESS",
    "OWNER",
    "OWNER2",
    "MAILADDR",
    "MAILCITY",
    "STATE",
    "ZIP",
    "MAILLINE1",
    "MAILLINE2",
    "MAILLINE3",
    "ZONING",
    "CALC_ACRE",
    "LANDVAL",
    "IMPVAL",
    "OBYVAL",
    "APPRAISAL",
    "SALEDATE",
    "PRICE",
    "VI",
    "AR",
    "DEEDBKPG",
    "V_SALEDATE",
    "V_PRICE",
    "LANDUSE",
    "PROPTYPE",
    "COUNTY",
]
GEOM_WHERE = f"COUNTY_ID={COUNTY_ID} AND PARCEL_TYPE=1 AND CALC_ACRE>={MIN_ACRES} AND CALC_ACRE<={MAX_ACRES}"

GAPS = [
    "No adopted future-land-use FeatureServer. The 2043 Comp Plan draft and UGB/PGA layers are growth context only and were not written as parcel FLU. Sale date and price are often blank or zero. REST exposes appraisal (APPRAISAL), not assessed or taxable value.",
    "Geometry is IMPACT Parcels COUNTY_ID=22, PARCEL_TYPE=1, CALC_ACRE 5–150 inclusive. Attributes are Parcel_Layer_Themes JUR='022' joined on GISLINK using the latest TAXYR. FIPS 47043 is the GEOID; 022 is the Comptroller county number, not the FIPS suffix. A previous extract used COUNTY_ID=43 and was replaced. Seven polygons in the acreage band share GISLINK 'TVA', have no Themes row, and were not stored under an invented parcel id.",
    "Dickinson ND, Dixon CA, and Charlotte County FL were not used. Opportunity Zone designation was not inferred from nomination eligibility.",
]


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; DarrylLandSearch/1.0; county-research)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(json.dumps(payload["error"])[:400])
            return payload
        except Exception as exc:  # noqa: BLE001
            last = exc
            message = str(exc)
            if "403" in message and attempt == retries - 1:
                break
            time.sleep(1.1 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:180]}: {last}")


def object_ids(url: str, where: str) -> list[int]:
    data = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    return [int(i) for i in (data.get("objectIds") or [])]


def fetch_oids(url: str, ids: list[int], *, fields: list[str], geometry: bool, batch: int) -> list[dict]:
    features: list[dict] = []
    total = len(ids)
    for start in range(0, total, batch):
        chunk = ids[start : start + batch]
        params = {
            "objectIds": ",".join(str(i) for i in chunk),
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "f": "json",
        }
        if geometry:
            params["outSR"] = "4326"
        try:
            data = fetch_json(url, params, timeout=180)
        except RuntimeError:
            if len(chunk) > 20:
                features.extend(fetch_oids(url, chunk, fields=fields, geometry=geometry, batch=max(10, len(chunk) // 2)))
                continue
            raise
        features.extend(data.get("features") or [])
        done = min(start + len(chunk), total)
        if done == len(chunk) or done == total or done % (batch * 4) == 0:
            print(f"    {done}/{total}", flush=True)
        time.sleep(0.02)
    return features


def collapsed(value: str) -> str:
    return " ".join(value.split())


def link_keys(value: object) -> list[str]:
    text = clean(value)
    if not text:
        return []
    keys = [text]
    flat = collapsed(text)
    if flat != text:
        keys.append(flat)
    return keys


def parse_date(value: object) -> str | None:
    text = clean(value)
    if not text:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def money(value: object) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return round(parsed, 2)


def as_shape(geojson: dict):
    geom = shape(geojson)
    if geom.is_empty:
        return None
    if not geom.is_valid:
        geom = geom.buffer(0)
    if geom.is_empty:
        return None
    return geom


def load_json(path: Path):
    return json.loads(path.read_text())


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def download_geometry(refresh: bool) -> tuple[list[dict], int]:
    cache = CACHE_DIR / "geometry.json"
    if cache.exists() and not refresh:
        cached = load_json(cache)
        print(f"  geometry cache {len(cached['rows'])} (source {cached['sourceCount']})", flush=True)
        return cached["rows"], int(cached["sourceCount"])
    print("  counting IMPACT Parcels COUNTY_ID=22 PARCEL_TYPE=1 CALC_ACRE 5–150", flush=True)
    counted = fetch_json(GEOM_URL, {"where": GEOM_WHERE, "returnCountOnly": "true", "f": "json"})
    source_count = int(counted["count"])
    print(f"  source rows {source_count}", flush=True)
    ids = object_ids(GEOM_URL, GEOM_WHERE)
    raw = fetch_oids(
        GEOM_URL,
        ids,
        fields=["OBJECTID", "COUNTY_ID", "PARCEL_TYPE", "GISLINK", "CALC_ACRE"],
        geometry=True,
        batch=50,
    )
    rows = []
    dropped_geom = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed = rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            dropped_geom += 1
            continue
        gislink = clean(attrs.get("GISLINK"))
        acres = num(attrs.get("CALC_ACRE"))
        if not gislink or not gislink.startswith("022"):
            dropped_geom += 1
            continue
        if not in_band(acres):
            dropped_geom += 1
            continue
        rows.append({"gislink": gislink, "acreage": acres, "geometry": geometry})
    save_json(cache, {"sourceCount": source_count, "droppedGeometry": dropped_geom, "rows": rows})
    print(f"  geometry kept {len(rows)} dropped {dropped_geom}", flush=True)
    return rows, source_count


def download_themes(refresh: bool) -> dict[str, dict]:
    cache = CACHE_DIR / "themes.json"
    if cache.exists() and not refresh:
        rows = load_json(cache)
        print(f"  themes cache {len(rows)}", flush=True)
        return {row["GISLINK"]: row for row in rows}
    print("  pulling Parcel_Layer_Themes JUR='022'", flush=True)
    ids = object_ids(THEMES_URL, f"JUR='{JUR}'")
    raw = fetch_oids(THEMES_URL, ids, fields=THEME_FIELDS, geometry=False, batch=250)
    best: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        gislink = clean(attrs.get("GISLINK"))
        if not gislink:
            continue
        current = best.get(gislink)
        taxyr = int(num(attrs.get("TAXYR")) or 0)
        if current is None or taxyr >= int(num(current.get("TAXYR")) or 0):
            attrs = dict(attrs)
            attrs["GISLINK"] = gislink
            best[gislink] = attrs
    save_json(cache, list(best.values()))
    print(f"  themes unique GISLINK {len(best)} from {len(raw)} rows", flush=True)
    return best


def theme_index(rows: dict[str, dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for attrs in rows.values():
        for key in link_keys(attrs.get("GISLINK")):
            current = indexed.get(key)
            taxyr = int(num(attrs.get("TAXYR")) or 0)
            if current is None or taxyr >= int(num(current.get("TAXYR")) or 0):
                indexed[key] = attrs
    return indexed


def lookup_theme(index: dict[str, dict], gislink: str) -> dict | None:
    for key in link_keys(gislink):
        found = index.get(key)
        if found:
            return found
    return None


def download_polygons(url: str, fields: list[str], cache_name: str, refresh: bool) -> list[dict]:
    cache = CACHE_DIR / cache_name
    if cache.exists() and not refresh:
        rows = load_json(cache)
        print(f"  {cache_name} cache {len(rows)}", flush=True)
        return rows
    print(f"  pulling {cache_name}", flush=True)
    ids = object_ids(url, "1=1")
    raw = fetch_oids(url, ids, fields=["OBJECTID", *fields], geometry=True, batch=80)
    rows = []
    for item in raw:
        geometry, _acres = rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            continue
        attrs = item.get("attributes") or {}
        rows.append({"attributes": {key: attrs.get(key) for key in fields}, "geometry": geometry})
    save_json(cache, rows)
    print(f"  {cache_name} polygons {len(rows)}", flush=True)
    return rows


def assert_lonlat(geom, label: str) -> None:
    minx, miny, maxx, maxy = geom.bounds
    if not (-90 < minx < -80 and -90 < maxx < -80 and 34 < miny < 37 and 34 < maxy < 37):
        raise RuntimeError(f"{label} is not in a Dickson County lon/lat extent: {geom.bounds}")


class ZoneIndex:
    def __init__(self, rows: list[dict], code_field: str, desc_field: str, desc_fallback: str | None = None):
        self.geoms = []
        self.codes: list[str] = []
        self.descs: list[str | None] = []
        for row in rows:
            geom = as_shape(row["geometry"])
            if geom is None:
                continue
            attrs = row["attributes"]
            code = clean(attrs.get(code_field))
            desc = clean(attrs.get(desc_field))
            if desc is None and desc_fallback:
                desc = clean(attrs.get(desc_fallback))
            self.geoms.append(geom)
            self.codes.append(code or "")
            self.descs.append(desc)
        self.tree = STRtree(self.geoms) if self.geoms else None

    def assign(self, parcel, point: Point) -> tuple[str | None, str | None, str]:
        if self.tree is None or parcel.is_empty:
            return None, None, "miss"
        hits = [int(i) for i in self.tree.query(parcel, predicate="intersects")]
        point_best: tuple[float, str, str | None] | None = None
        area_best: tuple[float, str, str | None] | None = None
        parcel_area = parcel.area or 0.0
        for idx in hits:
            code = self.codes[idx]
            if not code:
                continue
            poly = self.geoms[idx]
            try:
                overlap = poly.intersection(parcel).area
            except Exception:  # noqa: BLE001
                continue
            if overlap <= 0:
                continue
            if poly.covers(point):
                if point_best is None or overlap > point_best[0]:
                    point_best = (overlap, code, self.descs[idx])
            elif area_best is None or overlap > area_best[0]:
                area_best = (overlap, code, self.descs[idx])
        if point_best:
            return point_best[1], point_best[2], "interior"
        if area_best and parcel_area > 0 and area_best[0] / parcel_area >= 0.05:
            return area_best[1], area_best[2], "overlap"
        return None, None, "miss"


def situs_from(attrs: dict) -> str | None:
    address = clean(attrs.get("ADDRESS"))
    if address:
        return address
    number = clean(attrs.get("ST_NUM"))
    street = clean(attrs.get("STREET"))
    parts = [part for part in (number, street) if part]
    return " ".join(parts) or None


def mailing_from(attrs: dict) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    city = clean(attrs.get("MAILCITY"))
    state = clean(attrs.get("STATE"))
    zip_code = zip_str(attrs.get("ZIP"))
    line1 = clean(attrs.get("MAILADDR")) or clean(attrs.get("MAILLINE1"))
    city_line = " ".join(part for part in (city, state, zip_code) if part).upper()

    def extra(value: object) -> str | None:
        text = clean(value)
        if not text or text == line1:
            return None
        if " ".join(text.split()).upper() == city_line:
            return None
        return text

    line2 = extra(attrs.get("MAILLINE2"))
    line3 = extra(attrs.get("MAILLINE3"))
    if line2 and line3 and line3 not in line2:
        line2 = f"{line2}, {line3}"
    elif not line2:
        line2 = line3
    return line1, line2, city, state, zip_code


def sale_from(attrs: dict) -> tuple[str | None, float | None, str | None]:
    date = parse_date(attrs.get("SALEDATE"))
    price = money(attrs.get("PRICE"))
    used_vacant = False
    if date is None and price is None:
        vacant_date = parse_date(attrs.get("V_SALEDATE"))
        vacant_price = money(attrs.get("V_PRICE"))
        if vacant_date or vacant_price:
            date, price = vacant_date, vacant_price
            used_vacant = True
    bits = []
    vi = clean(attrs.get("VI"))
    ar = clean(attrs.get("AR"))
    deed = clean(attrs.get("DEEDBKPG"))
    if vi:
        bits.append(f"VI={vi}")
    if ar:
        bits.append(f"AR={ar}")
    if used_vacant:
        bits.append("vacant-land")
    if (date or price) and deed:
        bits.append(f"deed {deed}")
    qualified = " ".join(bits) or None
    if date is None and price is None:
        return None, None, None
    return date, price, qualified


def dor_from(attrs: dict) -> str | None:
    landuse = clean(attrs.get("LANDUSE"))
    proptype = clean(attrs.get("PROPTYPE"))
    if proptype in {"0", "00"}:
        proptype = None
    return landuse or proptype


def resolve_jurisdiction(parcel, point: Point, cities: list[tuple[str, object]]) -> str | None:
    """City name when the parcel is inside that municipality. None is unincorporated."""
    containing: list[tuple[float, str]] = []
    overlapping: list[tuple[float, str]] = []
    parcel_area = parcel.area or 0.0
    for name, city in cities:
        if not city.intersects(parcel):
            continue
        try:
            overlap = city.intersection(parcel).area
        except Exception:  # noqa: BLE001
            continue
        if overlap <= 0:
            continue
        if city.covers(point):
            containing.append((overlap, name))
        else:
            overlapping.append((overlap, name))
    if containing:
        return max(containing)[1]
    if overlapping and parcel_area > 0:
        overlap, name = max(overlapping)
        if overlap / parcel_area >= 0.5:
            return name
    return None


def build_features(geom_rows: list[dict], themes: dict[str, dict], zones: dict[str, ZoneIndex], cities, county_geom) -> tuple[list[dict], dict]:
    indexed = theme_index(themes)
    by_id: dict[str, dict] = {}
    contribs: dict[str, dict] = {}
    stats = {
        "droppedDuplicateId": 0,
        "droppedOutsideCounty": 0,
        "droppedBadGeometry": 0,
        "themesMatched": 0,
        "ownerCount": 0,
        "situsCount": 0,
        "mailingCount": 0,
        "saleCount": 0,
        "appraisalCount": 0,
        "camaZoningNonBlank": 0,
        "citynumPolygonDisagree": 0,
        "taxYears": {},
        "jurisdictions": {},
        "zoningMethods": {"interior": 0, "overlap": 0, "miss": 0, "gap-town": 0},
    }
    for row in geom_rows:
        parcel = as_shape(row["geometry"])
        if parcel is None:
            stats["droppedBadGeometry"] += 1
            continue
        center = centroid_of(row["geometry"])
        if not plausible_centroid(center):
            stats["droppedBadGeometry"] += 1
            continue
        point = Point(center[0], center[1])
        if county_geom is not None and not county_geom.covers(point) and not county_geom.intersects(parcel):
            # COUNTY_ID=22 already scopes the roll. Drop only a point that is clearly
            # outside Dickson, not a survey sliver on the county line.
            if county_geom.distance(point) > 0.02:
                stats["droppedOutsideCounty"] += 1
                continue
        point_xy = center
        attrs = lookup_theme(indexed, row["gislink"]) or {}
        owner = clean(attrs.get("OWNER"))
        owner2 = clean(attrs.get("OWNER2"))
        situs = situs_from(attrs) if attrs else None
        mail1, mail2, mail_city, mail_state, mail_zip = mailing_from(attrs) if attrs else (None, None, None, None, None)
        sale_date, sale_price, sale_qualified = sale_from(attrs) if attrs else (None, None, None)
        jurisdiction = resolve_jurisdiction(parcel, point, cities)
        citynum = clean(attrs.get("CITYNUM")) if attrs else None
        citynum_name = CITYNUM_TO_NAME.get(citynum or "")
        polygon_name = jurisdiction
        if jurisdiction in GAP_TOWNS:
            prefix = jurisdiction
            zoning_code, zoning_desc, method = None, None, "gap-town"
        elif jurisdiction in ZONING_SOURCES:
            zoning_code, zoning_desc, method = zones[jurisdiction].assign(parcel, point)
            prefix = jurisdiction
        else:
            zoning_code, zoning_desc, method = zones["Dickson County"].assign(parcel, point)
            prefix = "Dickson County"
        feature = empty_feature(
            fips=FIPS,
            county="Dickson",
            state="Tennessee",
            markets=["Nashville"],
            parcel_id=row["gislink"],
            acreage=float(row["acreage"]),
            geometry=row["geometry"],
            center=point_xy,
            source=SOURCE,
            owner=owner,
            situs=situs,
            city=jurisdiction,
            zip_code=None,
            zoning=zoning_code,
            dor=dor_from(attrs) if attrs else None,
            sale_price=sale_price,
            sale_date=sale_date,
            sale_qualified=sale_qualified,
            market_value=money(attrs.get("APPRAISAL")) if attrs else None,
            assessed=None,
            taxable=None,
            mail1=mail1,
            mail2=mail2,
            mail_city=mail_city,
            mail_state=mail_state,
            mail_zip=mail_zip,
        )
        props = feature["properties"]
        props["ownerName2"] = owner2
        props["jurisdictionCode"] = citynum
        props["jurisdictionPrefix"] = prefix
        props["zoningDistrict"] = zoning_desc
        props["appraiserUrl"] = "https://assessment.cot.tn.gov/TPAD/Parcel/GIS?GISlink=" + urllib.parse.quote(row["gislink"], safe="")
        props["flu"] = None
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        previous = by_id.get(row["gislink"])
        if previous is not None:
            stats["droppedDuplicateId"] += 1
            if (feature["properties"]["acreage"] or 0) <= (previous["properties"]["acreage"] or 0):
                continue
        by_id[row["gislink"]] = feature
        year = str(int(num(attrs.get("TAXYR")) or 0)) if attrs else None
        contribs[row["gislink"]] = {
            "themesMatched": bool(attrs),
            "taxYear": year,
            "owner": bool(owner),
            "situs": bool(situs),
            "mailing": bool(mail1 or mail_city),
            "sale": bool(sale_date or sale_price),
            "appraisal": bool(money(attrs.get("APPRAISAL"))) if attrs else False,
            "camaZoning": bool(clean(attrs.get("ZONING"))) if attrs else False,
            "disagree": citynum_name != polygon_name,
            "prefix": prefix,
            "zoning": bool(zoning_code),
            "method": method,
        }
    for contrib in contribs.values():
        if contrib["themesMatched"]:
            stats["themesMatched"] += 1
            year = contrib["taxYear"] or "0"
            stats["taxYears"][year] = stats["taxYears"].get(year, 0) + 1
        stats["ownerCount"] += int(contrib["owner"])
        stats["situsCount"] += int(contrib["situs"])
        stats["mailingCount"] += int(contrib["mailing"])
        stats["saleCount"] += int(contrib["sale"])
        stats["appraisalCount"] += int(contrib["appraisal"])
        stats["camaZoningNonBlank"] += int(contrib["camaZoning"])
        stats["citynumPolygonDisagree"] += int(contrib["disagree"])
        stats["zoningMethods"][contrib["method"]] = stats["zoningMethods"].get(contrib["method"], 0) + 1
        bucket = stats["jurisdictions"].setdefault(contrib["prefix"], {"parcels": 0, "zoningJoined": 0})
        bucket["parcels"] += 1
        bucket["zoningJoined"] += int(contrib["zoning"])
    features = list(by_id.values())
    features.sort(key=lambda item: item["properties"].get("acreage") or 0, reverse=True)
    return features, stats


def load_cities(refresh: bool) -> list[tuple[str, object]]:
    rows = download_polygons(CITY_LIMITS_URL, ["NAME"], "city-limits.json", refresh)
    cities = []
    for row in rows:
        name = clean((row.get("attributes") or {}).get("NAME"))
        geom = as_shape(row["geometry"])
        if not name or geom is None:
            continue
        assert_lonlat(geom, f"city limits {name}")
        cities.append((name, geom))
    names = sorted(name for name, _geom in cities)
    expected = ["Burns", "Charlotte", "Dickson", "Slayden", "Vanleer", "White Bluff"]
    if names != expected:
        raise RuntimeError(f"City limits names {names} did not match {expected}")
    return cities


def load_county(refresh: bool):
    rows = download_polygons(COUNTY_BOUNDARY_URL, ["NAMELSADCO"], "county-boundary.json", refresh)
    geoms = [as_shape(row["geometry"]) for row in rows]
    geoms = [geom for geom in geoms if geom is not None]
    if not geoms:
        raise RuntimeError("Dickson County boundary returned no polygons")
    county = geoms[0]
    for geom in geoms[1:]:
        county = county.union(geom)
    assert_lonlat(county, "county boundary")
    return county


def load_zones(refresh: bool) -> dict[str, ZoneIndex]:
    loaded = {}
    for name, spec in ZONING_SOURCES.items():
        slug = name.lower().replace(" ", "-")
        fields = []
        for key in (spec["code"], spec["desc"], spec.get("descFallback")):
            if key and key not in fields:
                fields.append(key)
        rows = download_polygons(spec["url"], fields, f"zoning-{slug}.json", refresh)
        loaded[name] = ZoneIndex(rows, spec["code"], spec["desc"], spec.get("descFallback"))
        print(f"  {name} zoning polygons {len(loaded[name].geoms)}", flush=True)
    return loaded


def coverage_gaps(stats: dict) -> list[str]:
    jur = stats["jurisdictions"]

    def count(name: str, key: str) -> int:
        return int(jur.get(name, {}).get(key) or 0)

    zoning = (
        "Zoning polygons are joined only inside the resolved jurisdiction. "
        f"City of Dickson Current_Zo {count('Dickson', 'zoningJoined')}/{count('Dickson', 'parcels')}, "
        f"White Bluff Zone_Curre {count('White Bluff', 'zoningJoined')}/{count('White Bluff', 'parcels')}, "
        f"county Zone_Curre {count('Dickson County', 'zoningJoined')}/{count('Dickson County', 'parcels')}. "
        f"Burns ({count('Burns', 'parcels')}), Charlotte ({count('Charlotte', 'parcels')}), "
        f"Vanleer ({count('Vanleer', 'parcels')}), and Slayden ({count('Slayden', 'parcels')}) "
        "have no public zoning FeatureServer (Burns is a 2016 PDF), so those parcels stay unzoned. "
        f"IMPACT Themes ZONING was non-blank on {stats['camaZoningNonBlank']} parcels and was not copied. "
        "County Zone_Curre is 164 district polygons; A1 is only 6 of them, and those large polygons cover most rural acreage."
    )
    return [zoning, *GAPS]


def publish(features: list[dict], source_count: int, dropped: int, stats: dict) -> dict:
    county = {"name": "Dickson", "fips": FIPS, "state": "Tennessee"}
    _path, _lookup, tiles = write_tiles(county, features)
    row = county_row(
        county,
        ["Nashville"],
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=f"data/fixtures/market-parcels/counties/{FIPS}/tiles",
        lookup=f"data/fixtures/market-parcels/counties/{FIPS}/lookup.json",
        source=SOURCE,
        query_url=GEOM_URL,
        gaps=coverage_gaps(stats),
        source_count=source_count,
        dropped=dropped,
        tile_count=tiles,
    )
    zoning_joined = sum(bucket["zoningJoined"] for bucket in stats["jurisdictions"].values())
    kept = len(features)
    ingest = {
        "impactCountyId": COUNTY_ID,
        "jur": JUR,
        "geoidFips": FIPS,
        "parcelType": 1,
        "acreageField": "CALC_ACRE",
        "acreageBand": [MIN_ACRES, MAX_ACRES],
        "geometryQueryCount": source_count,
        "kept": kept,
        "themesRowsDeduped": None,
        "themesMatched": stats["themesMatched"],
        "themesUnmatched": kept - stats["themesMatched"],
        "themesTaxYearsOnKept": stats["taxYears"],
        "ownerCount": stats["ownerCount"],
        "situsCount": stats["situsCount"],
        "mailingCount": stats["mailingCount"],
        "saleCount": stats["saleCount"],
        "appraisalCount": stats["appraisalCount"],
        "camaZoningNonBlankIgnored": stats["camaZoningNonBlank"],
        "citynumPolygonDisagree": stats["citynumPolygonDisagree"],
        "jurisdictions": stats["jurisdictions"],
        "zoningJoined": zoning_joined,
        "zoningJoinRate": round(zoning_joined / kept, 4) if kept else 0,
        "zoningMethods": stats["zoningMethods"],
        "fluJoined": 0,
        "opportunityZoneDesignated": 0,
        "assessedValueInvented": False,
        "rejectedTwins": ["Dickinson ND gis.dickinsongov.com", "Dixon CA City_of_Dixon_Zoning", "Charlotte County FL"],
        "droppedDuplicateId": stats["droppedDuplicateId"],
        "droppedOutsideCounty": stats["droppedOutsideCounty"],
        "droppedBadGeometry": stats["droppedBadGeometry"],
    }
    for name, spec in ZONING_SOURCES.items():
        if name in ingest["jurisdictions"]:
            ingest["jurisdictions"][name]["source"] = spec["label"]
    for town in sorted(GAP_TOWNS):
        if town in ingest["jurisdictions"]:
            ingest["jurisdictions"][town]["source"] = "honest REST gap"
    if "Dickson County" in ingest["jurisdictions"]:
        ingest["jurisdictions"]["Dickson County"]["source"] = ZONING_SOURCES["Dickson County"]["label"]
    row["ingest"] = ingest
    (COUNTY_DIR / FIPS / "county.json").write_text(json.dumps(row, indent=2) + "\n")
    refresh_nashville(row)
    return row


def refresh_nashville(row: dict) -> None:
    meta_path = ROOT / "data/fixtures/market-parcels/markets/nashville/meta.json"
    meta = json.loads(meta_path.read_text())
    total = 0
    for county in meta["counties"]:
        if county["fips"] == FIPS:
            county.update(
                {
                    "featureCount": row["featureCount"],
                    "coverage": row["coverage"],
                    "partition": row["partition"],
                    "source": row["source"],
                    "queryUrl": row["queryUrl"],
                    "gaps": row["gaps"],
                    "path": row["path"],
                    "lookup": row["lookup"],
                    "tileCount": row["tileCount"],
                    "sourceCount": row["sourceCount"],
                }
            )
        total += int(county.get("featureCount") or 0)
    meta["parcelCount"] = total
    meta["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")

    index_path = ROOT / "data/fixtures/market-parcels/index.json"
    index = json.loads(index_path.read_text())
    nashville = index["markets"]["Nashville"]
    nashville["parcelCount"] = total
    for county in nashville["counties"]:
        if county["fips"] == FIPS:
            county["featureCount"] = row["featureCount"]
            county["coverage"] = row["coverage"]
            county["gaps"] = row["gaps"][:2]
    index["generatedAt"] = meta["generatedAt"]
    index_path.write_text(json.dumps(index, indent=2) + "\n")

    formatted = f"{total:,}"
    dickson = f"{row['featureCount']:,}"
    for path in (
        ROOT / "docs/market-parcels.md",
        ROOT / "data/fixtures/market-parcels/coverage.md",
    ):
        text = path.read_text()
        text2, n1 = re.subn(
            r"\| Nashville \| primary \| [0-9,]+ \| 6 \| 0 \| 11 \|",
            f"| Nashville | primary | {formatted} | 6 | 0 | 11 |",
            text,
            count=1,
        )
        text3, n2 = re.subn(
            r"\| Dickson \| Tennessee \| 47043 \| complete-gte-5ac \| [0-9,]+ \| tn-impact-47043 \|",
            f"| Dickson | Tennessee | 47043 | complete-gte-5ac | {dickson} | tn-impact-47043 |",
            text2,
            count=1,
        )
        if n1 != 1 or n2 != 1:
            raise RuntimeError(f"Could not refresh Dickson counts in {path} ({n1}, {n2})")
        path.write_text(text3)


def shapefile_fallback(directory: Path) -> tuple[list[dict], dict[str, dict], int]:
    """Offline twin: weekly Comptroller polygons plus Assessment_Data_022.dbf on GISLINK."""
    try:
        import shapefile  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Shapefile fallback needs pyshp (`pip install pyshp`).") from exc
    shp_paths = [path for path in directory.rglob("*.shp") if "assessment" not in path.name.lower()]
    if not shp_paths:
        raise RuntimeError(f"No parcel shapefile under {directory}")
    reader = shapefile.Reader(str(shp_paths[0]))
    fields = [field[0] for field in reader.fields[1:]]
    rows = []
    for record, shape_rec in zip(reader.iterRecords(), reader.iterShapes()):
        attrs = {fields[i]: record[i] for i in range(len(fields))}
        upper = {str(key).upper(): value for key, value in attrs.items()}
        county = num(upper.get("COUNTY_ID"))
        parcel_type = num(upper.get("PARCEL_TYPE"))
        acres = num(upper.get("CALC_ACRE"))
        gislink = clean(upper.get("GISLINK"))
        if county is not None and int(county) != COUNTY_ID:
            continue
        if parcel_type is not None and int(parcel_type) != 1:
            continue
        if not gislink or not gislink.startswith("022") or not in_band(acres):
            continue
        if shape_rec.shapeType not in (5, 15, 25, 31):
            continue
        sample_x = [point[0] for point in shape_rec.points[:5]]
        if sample_x and max(abs(x) for x in sample_x) > 180:
            raise RuntimeError("Shapefile is not longitude/latitude. Reproject to EPSG:4326 before --shapefile-dir.")
        points = shape_rec.points
        parts = list(shape_rec.parts) + [len(points)]
        esri_rings = []
        for start, end in zip(parts, parts[1:]):
            ring = [[float(x), float(y)] for x, y in points[start:end]]
            if len(ring) >= 4:
                esri_rings.append(ring)
        geometry, _computed = rings_to_feature_geometry({"rings": esri_rings})
        if not geometry:
            continue
        rows.append({"gislink": gislink, "acreage": acres, "geometry": geometry})
    dbf_path = next(directory.rglob("Assessment_Data_022.dbf"), None)
    if dbf_path is None:
        raise RuntimeError("Assessment_Data_022.dbf was not in the shapefile directory")
    return rows, read_assessment_dbf(dbf_path), len(rows)


def read_assessment_dbf(path: Path) -> dict[str, dict]:
    """Read Assessment_Data_022.dbf without requiring a sibling .shp."""
    try:
        from dbfread import DBF  # type: ignore
    except ImportError:
        DBF = None
    best: dict[str, dict] = {}
    if DBF is not None:
        for record in DBF(str(path), encoding="latin-1", char_decode_errors="ignore"):
            attrs = {str(key).upper(): value for key, value in dict(record).items()}
            gislink = clean(attrs.get("GISLINK"))
            if not gislink:
                continue
            taxyr = int(num(attrs.get("TAXYR")) or 0)
            current = best.get(gislink)
            if current is None or taxyr >= int(num(current.get("TAXYR")) or 0):
                best[gislink] = attrs
        return best
    # Minimal dBase III reader for the weekly fallback.
    data = path.read_bytes()
    count = int.from_bytes(data[4:8], "little")
    header_len = int.from_bytes(data[8:10], "little")
    record_len = int.from_bytes(data[10:12], "little")
    fields = []
    offset = 32
    while offset < header_len - 1 and data[offset] != 0x0D:
        name = data[offset : offset + 11].split(b"\x00", 1)[0].decode("ascii", "ignore").upper()
        ftype = chr(data[offset + 11])
        flen = data[offset + 16]
        fields.append((name, ftype, flen))
        offset += 32
    for index in range(count):
        start = header_len + index * record_len
        rec = data[start : start + record_len]
        if not rec or rec[0:1] == b"*":
            continue
        cursor = 1
        attrs: dict[str, object] = {}
        for name, ftype, flen in fields:
            raw = rec[cursor : cursor + flen]
            cursor += flen
            text = raw.decode("latin-1", "ignore").strip()
            if ftype in {"N", "F"}:
                attrs[name] = num(text)
            else:
                attrs[name] = text
        gislink = clean(attrs.get("GISLINK"))
        if not gislink:
            continue
        taxyr = int(num(attrs.get("TAXYR")) or 0)
        current = best.get(gislink)
        if current is None or taxyr >= int(num(current.get("TAXYR")) or 0):
            best[gislink] = attrs
    return best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Ignore /tmp/dls-dickson caches and pull again")
    parser.add_argument(
        "--shapefile-dir",
        default="",
        help="Weekly Comptroller extract directory (polygons + Assessment_Data_022.dbf) if IMPACT REST is blocked",
    )
    args = parser.parse_args()
    print("Dickson County TN FIPS 47043 / IMPACT COUNTY_ID 22", flush=True)
    shapefile_dir = Path(args.shapefile_dir) if args.shapefile_dir else None
    try:
        if shapefile_dir:
            print(f"Using shapefile fallback {shapefile_dir}", flush=True)
            geom_rows, themes, source_count = shapefile_fallback(shapefile_dir)
        else:
            geom_rows, source_count = download_geometry(args.refresh)
            themes = download_themes(args.refresh)
    except RuntimeError as exc:
        message = str(exc)
        if "403" in message and shapefile_dir is None:
            raise SystemExit(
                "maps.cot.tn.gov returned 403. Re-run with --shapefile-dir pointing at the weekly "
                "Comptroller Dickson download (parcel shapefile joined to Assessment_Data_022.dbf on GISLINK). "
                f"Underlying error: {message}"
            ) from exc
        raise
    cities = load_cities(args.refresh)
    county_geom = load_county(args.refresh)
    zones = load_zones(args.refresh)
    features, stats = build_features(geom_rows, themes, zones, cities, county_geom)
    if not features:
        raise SystemExit("No Dickson parcels survived the 5–150 acre and county checks")
    if any(not str(feature["properties"]["parcelId"]).startswith("022") for feature in features):
        raise SystemExit("A kept parcel id does not start with Comptroller county 022")
    if any(not in_band(feature["properties"]["acreage"]) for feature in features):
        raise SystemExit("A kept parcel is outside 5–150 acres")
    dropped = source_count - len(features)
    if dropped < 0:
        dropped = stats["droppedDuplicateId"] + stats["droppedOutsideCounty"] + stats["droppedBadGeometry"]
    row = publish(features, source_count, dropped, stats)
    ingest = row["ingest"]
    ingest["themesRowsDeduped"] = len(themes)
    (COUNTY_DIR / FIPS / "county.json").write_text(json.dumps(row, indent=2) + "\n")
    print(json.dumps({"featureCount": row["featureCount"], "ingest": ingest}, indent=2), flush=True)


if __name__ == "__main__":
    main()
