#!/usr/bin/env python3
"""5.0–150.0 acre parcels for South Carolina rural OZ batch 1.

Reads county cards (not city cards) in the interim CSV order. A county that
already has a complete 5.0–150.0 acre extract is skipped. If the live card
endpoint does not answer, that county is skipped and the next CSV row is used.
The first 20 counties that answer are written.

Does not add a market shelf, switch markets, or store an Opportunity Zone
status, a school grade, or a base flood elevation. Household income stays the
ACS B19013_001E join. AADT stays the query-time statewide join. qPublic and
Beacon property-appraiser patterns are stored and are not requested.
Owner phone and email are not ingested. Sale dates after the pull date are
cleared.

Berkeley's card says internet_map_with_api/MapServer/4. Kershaw and Edgefield
use the new RFA CAMA layers on the cards, not the geometry-only county views.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import yaml

import seed_market_parcels as seed

ROOT = seed.ROOT
CATALOG_PATH = seed.CATALOG_PATH
CARDS = ROOT / "data" / "sc-parcel-cards"
CSV_PATH = CARDS / "rural-oz-interim-counties-2026-09-28.csv"
CACHE_DIR = Path("/tmp/dls-sc-rural-oz-batch1")
TODAY = date.today().isoformat()
TARGET = 20
BANNED_FIELD = re.compile(r"phone|e-?mail|ssn|confidential", re.I)
SQFT_MIN = 217800.0
SQFT_MAX = 6534000.0

# Card source when it is not the first usable parcels layer.
LAYER_URL_HINT = {
    "45015": "internet_map_with_api/MapServer/4",
    "45037": "Edgefield_McCormick_Greenwood_Web_Map_WFL1/FeatureServer/9",
    "45055": "Fairfield_Kershaw_Richland_Map_WFL1/FeatureServer/7",
}

# Polygon layer paired with an attribute table that holds acreage.
SPLIT_LAYERS = {
    "45043": {
        "attributes": "GCGIS_OpenData/FeatureServer/7",
        "polygons": "GCGIS_OpenData/FeatureServer/2",
        "attrId": "ParcelID",
        "polyId": "TMS",
        "acres": "TotalLandArea",
    }
}

SHELF_ALIAS = {
    "Augusta": "Columbia",
    "Spartanburg": "Greenville",
    "Greenwood": "Greenville",
    "Hilton Head": "Hilton Head",
}


def query_url(rest: str) -> str:
    base = rest.split("?")[0].rstrip("/")
    if not base.endswith("/query"):
        base += "/query"
    return base


def service_base(url: str) -> str:
    base = url.split("?")[0].rstrip("/")
    if base.endswith("/query"):
        base = base[: -len("/query")]
    return base


def norm_source(url: str | None) -> str:
    if not url:
        return ""
    return service_base(url).lower()


def fast_json(url: str, params: dict | None = None, timeout: int = 25) -> dict:
    return seed.fetch_json(url, params, timeout=timeout, retries=2)


def layer_meta(url: str) -> dict:
    return fast_json(service_base(url), {"f": "json"}, timeout=30)


def field_names(url: str) -> list[str]:
    data = layer_meta(url)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:240])
    names = [str(field.get("name")) for field in data.get("fields") or [] if field.get("name")]
    if not names:
        raise RuntimeError(f"No fields from {service_base(url)}")
    return names


def count_where(url: str, where: str) -> int:
    data = fast_json(url, {"where": where, "returnCountOnly": "true", "f": "json"}, timeout=40)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:240])
    count = data.get("count")
    if not isinstance(count, int):
        raise RuntimeError(f"No count from {url}: {str(data)[:160]}")
    return count


def load_cards() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for path in CARDS.glob("*.yaml"):
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict) or data.get("level") != "county":
            continue
        fips = str(data.get("fips") or "").zfill(5)
        if fips:
            found[fips] = data
    return found


def csv_order() -> list[dict]:
    rows = []
    with CSV_PATH.open(newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    return rows


def existing_row(fips: str) -> dict | None:
    path = seed.COUNTY_DIR / fips / "county.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def fully_loaded(row: dict | None) -> bool:
    if not row:
        return False
    return row.get("coverage") == "complete-gte-5ac" and int(row.get("featureCount") or 0) > 0


def short_name(card: dict, fallback: str) -> str:
    text = str(card.get("jurisdiction") or fallback)
    return re.sub(r"\s+County$", "", text).strip() or fallback


def choose_layer(card: dict) -> dict:
    fips = str(card["fips"]).zfill(5)
    layers = [layer for layer in card.get("layers") or [] if layer.get("restUrl")]
    hint = LAYER_URL_HINT.get(fips)
    if hint:
        for layer in layers:
            if hint in str(layer.get("restUrl")):
                return layer
        raise RuntimeError(f"{fips} card is missing {hint}")
    usable = [
        layer
        for layer in layers
        if layer.get("role") == "parcels" and layer.get("status") == "usable" and layer.get("geometry") in {None, "polygon"}
    ]
    countywide = [layer for layer in usable if str(layer.get("coverage") or "").startswith("county")]
    pool = countywide or usable
    if not pool:
        raise RuntimeError(f"{fips} has no usable parcel layer")
    return pool[0]


def mapped_fields(layer: dict) -> dict[str, str]:
    raw = layer.get("fieldMap") or {}
    cleaned: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        if BANNED_FIELD.search(key) or BANNED_FIELD.search(value):
            continue
        cleaned[key.strip()] = value.strip()
    return cleaned


FIELD_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def field_tokens(key: str) -> list[str]:
    chunks = key.split("+") if "+" in key else [key]
    tokens: list[str] = []
    for chunk in chunks:
        match = FIELD_TOKEN.search(chunk)
        if match and match.group(0) not in tokens:
            tokens.append(match.group(0))
    return tokens


def resolve_field_key(key: str, label: str, available: set[str]) -> str:
    """Drop parenthetical notes and apply a documented CAMA_Table_ prefix."""
    tokens = field_tokens(key)
    if not tokens:
        return key
    resolved: list[str] = []
    changed = False
    for token in tokens:
        if token in available:
            resolved.append(token)
            continue
        prefixed = f"CAMA_Table_{token}"
        if prefixed in available and "CAMA_Table_" in label:
            resolved.append(prefixed)
            changed = True
            continue
        resolved.append(token)
    if not changed:
        return key
    return "+".join(resolved) if "+" in key else resolved[0]


def same_service(left: str | None, right: str | None) -> bool:
    return bool(left and right and norm_source(left) == norm_source(right))


def attribute_field_map(card: dict, layer: dict, available: set[str]) -> dict[str, str]:
    """Parcel field map plus tax, sale, and owner maps on the same public service."""
    field_map = mapped_fields(layer)
    base = str(layer.get("restUrl") or "")
    extras: list[dict] = []
    for other in card.get("layers") or []:
        if other is layer:
            continue
        if isinstance(other.get("fieldMap"), dict) and same_service(str(other.get("restUrl") or ""), base):
            extras.append(other["fieldMap"])
    for section in (card.get("fullSuite") or {}, card.get("pass2") or {}):
        if not isinstance(section, dict):
            continue
        for key in ("tax", "sale", "owner"):
            block = section.get(key)
            if not isinstance(block, dict) or not isinstance(block.get("fieldMap"), dict):
                continue
            source = str(block.get("restUrl") or block.get("source") or "")
            if same_service(source, base):
                extras.append(block["fieldMap"])
    for extra in extras:
        for key, label in mapped_fields({"fieldMap": extra}).items():
            key = resolve_field_key(key, label, available)
            if key in field_map:
                continue
            if not any(token in available for token in field_tokens(key)):
                continue
            field_map[key] = label
    return field_map


def simple_sources(field_map: dict[str, str], available: set[str]) -> list[str]:
    wanted: list[str] = []
    for key in field_map:
        for name in field_tokens(key):
            if name in available and name not in wanted:
                wanted.append(name)
    return wanted


def target_bucket(label: str) -> str | None:
    text = label.split("(")[0].strip()
    aliases = {
        "parcelId": "parcelId",
        "ownerName": "owner",
        "ownerName2": "owner2",
        "acreage": "acres",
        "acreageRaw": "acres",
        "zoning": "zoning",
        "zoningCode": "zoning",
        "landUse": "dor",
        "dorCode": "dor",
        "lastSale.date": "saleDate",
        "lastSale.price": "salePrice",
        "lastSale.qualified": "saleQualified",
        "tax.marketValue": "market",
        "tax.assessedValue": "assessed",
        "tax.taxableValue": "taxable",
        "tax.landValue": "land",
        "tax.buildingValue": "building",
        "tax.improvementValue": "building",
        "mailingAddress.street": "mail1",
        "mailingAddress.line1": "mail1",
        "mailingAddress.line2": "mail2",
        "mailingAddress.city": "mailCity",
        "mailingAddress.state": "mailState",
        "mailingAddress.zip": "mailZip",
        "mailingAddress.cityState": "mailCityState",
        "mailingAddress.cityStateZip": "mailCityStateZip",
        "situsAddress": "situs",
        "situsAddress.number": "situsNum",
        "situsAddress.street": "situsStreet",
        "situsCity": "situsCity",
        "situsZip": "situsZip",
        "appraiserDeepLink": "paUrl",
        "flu": "flu",
    }
    return aliases.get(text)


def parse_sale_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d{8}", text):
        year = int(text[:4])
        if 1900 <= year <= 2100:
            return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    if re.fullmatch(r"\d{4}", text):
        year = int(text)
        if 1900 <= year <= 2100:
            return f"{year:04d}-01-01"
    iso = seed.epoch_to_iso(value)
    if iso:
        return iso
    return seed.text_date(value)


def clear_future_sale(props: dict) -> None:
    sale = props.get("lastSale") or {}
    sold = sale.get("date")
    if sold and sold > TODAY:
        sale["date"] = None
        props["lastSale"] = sale


def split_city_state(value: str | None) -> tuple[str | None, str | None, str | None]:
    text = seed.clean(value)
    if not text:
        return None, None, None
    zip_match = re.search(r"(\d{5})(?:-\d{4})?$", text)
    zip_code = zip_match.group(1) if zip_match else None
    if zip_match:
        text = text[: zip_match.start()].strip(" ,")
    parts = text.split()
    state = None
    if parts and re.fullmatch(r"[A-Za-z]{2}", parts[-1]):
        state = parts[-1].upper()
        parts = parts[:-1]
    city = " ".join(parts) or None
    return city, state, zip_code


def money(value: Any) -> float | None:
    if isinstance(value, str):
        value = value.replace(",", "").replace("$", "").strip()
    parsed = seed.num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def collect_mapped(attrs: dict, field_map: dict[str, str]) -> dict[str, Any]:
    buckets: dict[str, Any] = {}
    sums: dict[str, float] = {}
    for key, label in field_map.items():
        bucket = target_bucket(label)
        if not bucket:
            continue
        tokens = field_tokens(key)
        if "+" in key:
            if bucket in {"market", "assessed", "taxable", "land", "building"}:
                total = 0.0
                seen = False
                for part in tokens:
                    parsed = money(attrs.get(part))
                    if parsed is not None:
                        total += parsed
                        seen = True
                if seen:
                    sums[bucket] = total
            else:
                parts = [seed.clean(attrs.get(part)) for part in tokens]
                text = " ".join(part for part in parts if part) or None
                if text and not buckets.get(bucket):
                    buckets[bucket] = text
            continue
        name = tokens[0] if tokens else key.split()[0]
        raw = attrs.get(name)
        if bucket in {"market", "assessed", "taxable", "land", "building", "salePrice", "acres"}:
            parsed = seed.num(str(raw).replace(",", "")) if isinstance(raw, str) else seed.num(raw)
            if bucket == "acres":
                if parsed is not None and buckets.get("acres") is None:
                    buckets["acres"] = parsed
            elif parsed is not None and parsed > 0 and buckets.get(bucket) is None:
                buckets[bucket] = parsed
            continue
        if bucket == "saleDate":
            parsed_date = parse_sale_date(raw)
            if parsed_date and not buckets.get("saleDate"):
                buckets["saleDate"] = parsed_date
            continue
        text = seed.clean(raw)
        if text and not buckets.get(bucket):
            buckets[bucket] = text
    for bucket, total in sums.items():
        if total > 0 and not buckets.get(bucket):
            buckets[bucket] = total
    return buckets


def apply_template(template: str | None, parcel_id: str) -> str | None:
    if not template or "{parcelId}" not in template:
        return None
    # Jasper TaxPINs publish an embedded space; qPublic KeyValue is the dashed id.
    return template.replace("{parcelId}", parcel_id.replace(" ", ""))


def card_links(card: dict) -> dict[str, Any]:
    suite = card.get("fullSuite") or {}
    deep = suite.get("paDeepLink") if isinstance(suite.get("paDeepLink"), dict) else {}
    pass2 = (card.get("pass2") or {}).get("paLink") if isinstance(card.get("pass2"), dict) else {}
    pass2 = pass2 or {}
    template = deep.get("template") or card.get("appraiserDeepLink")
    if not template:
        candidate = pass2.get("pattern") or pass2.get("idTransform") or ""
        match = re.search(r"https?://\S*\{parcelId\}\S*", str(candidate))
        if match:
            template = match.group(0).rstrip(").,")
    gis = card.get("publicGisUrl") or card.get("jurisdictionGisUrl")
    search = card.get("appraiserSearchUrl") or (deep.get("searchUrl") if isinstance(deep, dict) else None)
    if not template and isinstance(search, str) and "{parcelId}" in search:
        template = search
    return {
        "template": template if isinstance(template, str) else None,
        "gis": gis if isinstance(gis, str) else None,
        "search": search if isinstance(search, str) else None,
        "paVerified": False,
    }


def feature_from(attrs: dict, geom: dict | None, *, card: dict, field_map: dict[str, str], markets: list[str], source: str, acres_scale: float, use_geometry_acres: bool) -> dict | None:
    geometry, computed = seed.rings_to_feature_geometry(geom)
    if not geometry:
        return None
    center = seed.centroid_of(geometry)
    if not seed.plausible_centroid(center):
        return None
    mapped = collect_mapped(attrs, field_map)
    acres = mapped.get("acres")
    if isinstance(acres, str):
        acres = seed.num(acres.replace(",", ""))
    if acres is not None and acres_scale != 1:
        acres = acres / acres_scale
    if use_geometry_acres or acres is None:
        acres = computed
    if acres is None:
        return None
    acres = round(float(acres), 4)
    if not seed.in_band(acres):
        return None
    parcel_id = seed.clean(mapped.get("parcelId"))
    if not parcel_id:
        return None
    situs = mapped.get("situs")
    if not situs:
        parts = [mapped.get("situsNum"), mapped.get("situsStreet")]
        situs = " ".join(part for part in parts if part) or None
    mail_city = mapped.get("mailCity")
    mail_state = mapped.get("mailState")
    mail_zip = seed.zip_str(mapped.get("mailZip"))
    if mapped.get("mailCityState") and not (mail_city and mail_state):
        city, state, zip_code = split_city_state(mapped.get("mailCityState"))
        mail_city = mail_city or city
        mail_state = mail_state or state
        mail_zip = mail_zip or zip_code
    if mapped.get("mailCityStateZip") and not mail_city:
        city, state, zip_code = split_city_state(mapped.get("mailCityStateZip"))
        mail_city = city
        mail_state = mail_state or state
        mail_zip = mail_zip or zip_code
    county_name = short_name(card, "South Carolina")
    feature = seed.empty_feature(
        fips=str(card["fips"]).zfill(5),
        county=county_name,
        state="South Carolina",
        markets=markets,
        parcel_id=parcel_id,
        acreage=float(acres),
        geometry=geometry,
        center=center,  # type: ignore[arg-type]
        source=source,
        owner=mapped.get("owner"),
        situs=situs,
        city=mapped.get("situsCity"),
        zip_code=seed.zip_str(mapped.get("situsZip")),
        zoning=mapped.get("zoning"),
        dor=mapped.get("dor"),
        sale_price=mapped.get("salePrice"),
        sale_date=mapped.get("saleDate"),
        sale_qualified=mapped.get("saleQualified"),
        market_value=mapped.get("market"),
        assessed=mapped.get("assessed"),
        taxable=mapped.get("taxable"),
        mail1=mapped.get("mail1"),
        mail2=mapped.get("mail2"),
        mail_city=mail_city,
        mail_state=mail_state,
        mail_zip=mail_zip,
    )
    feature["properties"]["ownerName2"] = mapped.get("owner2")
    if mapped.get("flu"):
        feature["properties"]["flu"] = {"code": mapped["flu"], "label": mapped["flu"], "jurisdiction": None}
    links = card_links(card)
    pa_url = mapped.get("paUrl")
    if isinstance(pa_url, str) and pa_url.lower().startswith("http"):
        feature["properties"]["appraiserUrl"] = pa_url
    else:
        feature["properties"]["appraiserUrl"] = apply_template(links["template"], parcel_id)
    if links["gis"]:
        feature["properties"]["gisViewerUrl"] = links["gis"]
    clear_future_sale(feature["properties"])
    scrub(feature["properties"])
    return feature


def scrub(value: Any) -> None:
    if isinstance(value, dict):
        for key in list(value):
            if BANNED_FIELD.search(str(key)):
                value.pop(key, None)
            else:
                scrub(value[key])
    elif isinstance(value, list):
        for item in value:
            scrub(item)


def dedupe(features: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for feature in features:
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    return list(by_id.values())


def try_count(url: str, where: str) -> int:
    try:
        return count_where(url, where)
    except Exception:
        return 0


def resolve_acres(url: str, where: str, acre_field: str | None, available: set[str]) -> tuple[str, float, bool, int]:
    """Return where, acres scale, whether to use geometry acres, and source count.

    A field whose 5–150 count is tiny next to a square-foot band (Greenwood Area)
    is square feet. String acre fields (Clarendon, Hampton) fall through to CAST
    or a client-side parse.
    """
    base = where or "1=1"
    if acre_field and acre_field in available:
        numeric = f"({base}) AND {acre_field}>=5 AND {acre_field}<=150"
        sqft = f"({base}) AND {acre_field}>={int(SQFT_MIN)} AND {acre_field}<={int(SQFT_MAX)}"
        acre_count = try_count(url, numeric)
        sqft_count = try_count(url, sqft) if acre_count < 500 else 0
        if sqft_count >= 200 and sqft_count > acre_count * 5:
            return sqft, 43560.0, False, sqft_count
        if acre_count > 0:
            return numeric, 1.0, False, acre_count
        cast = f"({base}) AND CAST({acre_field} AS FLOAT)>=5 AND CAST({acre_field} AS FLOAT)<=150"
        cast_count = try_count(url, cast)
        if cast_count > 0:
            return cast, 1.0, False, cast_count
        total = try_count(url, base)
        if 0 < total <= 80000:
            return base, 1.0, False, total
    total = count_where(url, base)
    if total <= 0:
        raise RuntimeError("source returned no features")
    if total > 80000:
        area = f"({base}) AND SHAPE.STArea()>={int(SQFT_MIN)} AND SHAPE.STArea()<={int(SQFT_MAX)}"
        area_count = try_count(url, area)
        if area_count > 0:
            return area, 1.0, True, area_count
        raise RuntimeError(f"no acreage filter and {total} features is too large to scan")
    return base, 1.0, True, total


def pull_features(url: str, where: str, out_fields: list[str], card: dict, field_map: dict[str, str], markets: list[str], source: str, acres_scale: float, use_geometry_acres: bool) -> tuple[list[dict], int]:
    ids = seed.fetch_object_ids(url, where)
    raw = seed.fetch_by_ids(url, ids, out_fields, batch=80)
    features: list[dict] = []
    dropped = 0
    for item in raw:
        feature = feature_from(
            item.get("attributes") or {},
            item.get("geometry"),
            card=card,
            field_map=field_map,
            markets=markets,
            source=source,
            acres_scale=acres_scale,
            use_geometry_acres=use_geometry_acres,
        )
        if feature is None:
            dropped += 1
            continue
        features.append(feature)
    features = dedupe(features)
    return features, dropped


def pull_georgetown(card: dict, markets: list[str], source: str) -> tuple[list[dict], str, int, int]:
    layers = [layer for layer in card.get("layers") or [] if layer.get("restUrl")]
    attr_layer = next(layer for layer in layers if "FeatureServer/7" in layer["restUrl"])
    poly_layer = next(layer for layer in layers if "FeatureServer/2" in layer["restUrl"])
    attr_url = query_url(attr_layer["restUrl"])
    poly_url = query_url(poly_layer["restUrl"])
    attr_fields = set(field_names(attr_url))
    poly_fields = set(field_names(poly_url))
    attr_map = attribute_field_map(card, attr_layer, attr_fields)
    poly_map = mapped_fields(poly_layer)
    where, scale, geometry_acres, source_count = resolve_acres(attr_url, "1=1", "TotalLandArea", attr_fields)
    print(f"  Georgetown table rows {source_count}", flush=True)
    attr_out = simple_sources(attr_map, attr_fields)
    for extra in ("ParcelID", "GisLookUpKey", "TotalLandArea"):
        if extra in attr_fields and extra not in attr_out:
            attr_out.append(extra)
    ids = seed.fetch_object_ids(attr_url, where)
    rows = seed.fetch_by_ids(attr_url, ids, attr_out, batch=200, return_geometry=False)
    by_norm: dict[str, dict] = {}
    for item in rows:
        attrs = item.get("attributes") or {}
        parcel_id = seed.clean(attrs.get("ParcelID")) or seed.clean(attrs.get("GisLookUpKey"))
        if not parcel_id:
            continue
        by_norm[re.sub(r"[^A-Za-z0-9]", "", parcel_id).upper()] = attrs
    print(f"  Georgetown attributes {len(by_norm)}", flush=True)
    poly_out = [name for name in ("TMS", "Zone") if name in poly_fields]
    features: list[dict] = []
    keys = list(by_norm)
    for start in range(0, len(keys), 40):
        chunk = keys[start : start + 40]
        raw_ids = []
        for key in chunk:
            attrs = by_norm[key]
            raw = seed.clean(attrs.get("ParcelID"))
            if raw:
                raw_ids.append(raw)
        quoted_raw = ",".join("'" + item.replace("'", "''") + "'" for item in raw_ids)
        where_poly = f"TMS IN ({quoted_raw})" if quoted_raw else "1=0"
        try:
            data = seed.fetch_json(
                poly_url,
                {
                    "where": where_poly,
                    "outFields": ",".join(poly_out or ["TMS"]),
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "json",
                },
                timeout=120,
            )
        except Exception:
            data = {}
        if data.get("error"):
            continue
        polys = data.get("features") or []
        for item in polys:
            attrs = dict(item.get("attributes") or {})
            tms = seed.clean(attrs.get("TMS"))
            if not tms:
                continue
            joined = by_norm.get(re.sub(r"[^A-Za-z0-9]", "", tms).upper())
            if not joined:
                continue
            merged = dict(joined)
            merged.update(attrs)
            merged["parcelId"] = tms
            field_map = dict(attr_map)
            field_map.update(poly_map)
            field_map["parcelId"] = "parcelId"
            feature = feature_from(
                merged,
                item.get("geometry"),
                card=card,
                field_map={**field_map, "ParcelID": "parcelId", "TMS": "parcelId"},
                markets=markets,
                source=source,
                acres_scale=scale,
                use_geometry_acres=geometry_acres,
            )
            if feature:
                features.append(feature)
        if start and start % 400 == 0:
            print(f"    georgetown polygons {start}/{len(keys)} kept {len(features)}", flush=True)
    features = dedupe(features)
    return features, poly_url, source_count, max(0, source_count - len(features))


def markets_for(catalog: dict, fips: str) -> list[str]:
    found: list[str] = []
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips and market["id"] not in found:
                found.append(market["id"])
    return found


def ensure_on_shelves(catalog: dict, fips: str, name: str, card: dict) -> list[str]:
    existing = markets_for(catalog, fips)
    if existing:
        return existing
    shelf_ids = {market["id"] for market in catalog["markets"]}
    chosen: list[str] = []
    for label in card.get("markets") or []:
        target = label if label in shelf_ids else SHELF_ALIAS.get(label)
        if target in shelf_ids and target not in chosen:
            chosen.append(target)
    if not chosen:
        raise RuntimeError(f"{name} {fips} is not on an existing shelf")
    by_market = {market["id"]: market for market in catalog["markets"]}
    for market_id in chosen:
        market = by_market[market_id]
        market["counties"].append({"name": name, "state": "South Carolina", "fips": fips})
    return chosen


def county_dict(catalog: dict, fips: str, name: str) -> dict:
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips:
                return county
    return {"name": name, "state": "South Carolina", "fips": fips}


def gap_notes(card: dict, layer: dict, source_count: int, kept: int) -> list[str]:
    notes = []
    if source_count and kept < source_count:
        notes.append(f"Source query returned {source_count} rows; {kept} stayed in the 5.0–150.0 acre band after the parcel-id and geometry checks.")
    name = layer.get("name") or "card parcel layer"
    url = layer.get("restUrl")
    notes.append(
        f"Parcels are {name} ({url}). Acreage is 5.0–150.0 inclusive. No Opportunity Zone status, school grade, or base flood elevation is stored."
    )
    suite = card.get("fullSuite") or {}
    for key in ("tax", "sale", "owner"):
        block = suite.get(key) if isinstance(suite.get(key), dict) else {}
        reason = seed.clean(block.get("reason")) if isinstance(block, dict) else None
        status = block.get("status") if isinstance(block, dict) else None
        if reason:
            notes.append(f"{key} {status}: {reason}")
    notes.append("qPublic and Beacon property-appraiser links are stored as patterns and were not requested.")
    notes.append("Owner phone and email are not ingested. SCDOT AADT stays the query-time statewide join.")
    for gap in card.get("gaps") or []:
        text = seed.clean(gap)
        if text and "phone" not in text.lower():
            notes.append(text)
    # de-dupe
    unique: list[str] = []
    for note in notes:
        if note not in unique:
            unique.append(note)
    return unique[:8]


def write_county(county: dict, markets: list[str], features: list[dict], *, source: str, url: str, gaps: list[str], source_count: int, dropped: int, links: dict) -> None:
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{county['fips']} emitted a parcel outside 5–150 acres")
    if len(features) < 50:
        raise RuntimeError(f"{county['fips']} kept only {len(features)} parcels")
    path, lookup, tiles = seed.write_tiles(county, features)
    seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=source,
        query_url=url,
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        tile_count=tiles,
        extra={
            "paLinkVerified": False,
            "appraiserSearchUrl": links.get("template") or links.get("search"),
            "gisViewerUrl": links.get("gis"),
            "minAcres": 5.0,
            "maxAcres": 150.0,
        },
    )
    print(f"  kept {len(features)} tiles {tiles}", flush=True)


def download_county(catalog: dict, card: dict, refresh: bool) -> dict:
    fips = str(card["fips"]).zfill(5)
    name = short_name(card, fips)
    layer = choose_layer(card)
    url = query_url(str(layer["restUrl"]))
    source = f"sc-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}-parcels-{fips}"
    markets = ensure_on_shelves(catalog, fips, name, card)
    county = county_dict(catalog, fips, name)
    county["name"] = name
    county["state"] = "South Carolina"
    cache_path = CACHE_DIR / f"{fips}.json"
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features:
            print(f"Pulling {name} {fips} cache {len(features)}", flush=True)
            for feature in features:
                feature["properties"]["marketIds"] = markets
                clear_future_sale(feature["properties"])
            write_county(
                county,
                markets,
                features,
                source=source,
                url=cached.get("queryUrl") or url,
                gaps=cached.get("gaps") or [],
                source_count=int(cached.get("sourceCount") or len(features)),
                dropped=int(cached.get("dropped") or 0),
                links=card_links(card),
            )
            return {"fips": fips, "name": name, "featureCount": len(features), "queryUrl": cached.get("queryUrl") or url}
    print(f"Pulling {name} {fips} {url}", flush=True)
    if fips in SPLIT_LAYERS:
        features, poly_url, source_count, dropped = pull_georgetown(card, markets, source)
        url = poly_url
    else:
        available = set(field_names(url))
        field_map = attribute_field_map(card, layer, available)
        parcel_field = layer.get("parcelIdField") or next((key.split()[0] for key, label in field_map.items() if target_bucket(label) == "parcelId"), None)
        if parcel_field and parcel_field not in field_map and parcel_field in available:
            field_map[parcel_field] = "parcelId"
        acre_field = layer.get("acreageField") if layer.get("acreageField") in available else None
        if acre_field is None:
            for key, label in field_map.items():
                if target_bucket(label) == "acres" and "+" not in key and key.split()[0] in available:
                    acre_field = key.split()[0]
                    break
        card_where = layer.get("where") or "1=1"
        where, scale, geometry_acres, source_count = resolve_acres(url, card_where, acre_field, available)
        print(f"  source rows {source_count} where {where[:140]}", flush=True)
        out_fields = simple_sources(field_map, available)
        if parcel_field and parcel_field in available and parcel_field not in out_fields:
            out_fields.append(parcel_field)
        if acre_field and acre_field not in out_fields:
            out_fields.append(acre_field)
        features, dropped = pull_features(url, where, out_fields, card, field_map, markets, source, scale, geometry_acres)
    if source_count and len(features) < int(source_count * 0.5) and len(features) < 200:
        raise RuntimeError(f"kept {len(features)} of {source_count}")
    gaps = gap_notes(card, layer, source_count, len(features))
    write_county(
        county,
        markets,
        features,
        source=source,
        url=url,
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        links=card_links(card),
    )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"sourceCount": source_count, "dropped": dropped, "queryUrl": url, "gaps": gaps, "features": features}))
    return {"fips": fips, "name": name, "featureCount": len(features), "queryUrl": url, "sourceCount": source_count}


def select_counties(cards: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    chosen: list[dict] = []
    skipped: list[dict] = []
    for row in csv_order():
        if len(chosen) >= TARGET:
            break
        fips = str(row["county_fips"]).zfill(5)
        name = row["county"]
        card = cards.get(fips)
        if not card or card.get("level") != "county":
            skipped.append({"fips": fips, "name": name, "reason": "no county card"})
            continue
        current = existing_row(fips)
        try:
            layer = choose_layer(card)
            url = query_url(str(layer["restUrl"]))
        except Exception as exc:  # noqa: BLE001
            skipped.append({"fips": fips, "name": name, "reason": f"card layer: {exc}"})
            continue
        if fully_loaded(current):
            same = norm_source((current or {}).get("queryUrl")) == norm_source(url)
            why = "already loaded from the same source" if same else "already a complete 5.0–150.0 acre extract"
            skipped.append({"fips": fips, "name": name, "reason": why, "queryUrl": (current or {}).get("queryUrl")})
            continue
        if current and norm_source(current.get("queryUrl")) == norm_source(url) and int(current.get("featureCount") or 0) > 0:
            skipped.append({"fips": fips, "name": name, "reason": "already loaded from the same source"})
            continue
        try:
            if fips in SPLIT_LAYERS:
                count_where(url, "1=1")
            else:
                available = set(field_names(url))
                acre_field = layer.get("acreageField") if layer.get("acreageField") in available else None
                resolve_acres(url, layer.get("where") or "1=1", acre_field, available)
        except Exception as exc:  # noqa: BLE001
            skipped.append({"fips": fips, "name": name, "reason": f"endpoint unreachable: {exc}", "queryUrl": url})
            print(f"SKIP {name} {fips}: {exc}", flush=True)
            continue
        chosen.append({"fips": fips, "name": name, "card": card, "queryUrl": url})
        print(f"SELECT {name} {fips}", flush=True)
    return chosen, skipped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--skip-index", action="store_true")
    args = parser.parse_args()
    cards = load_cards()
    chosen, skipped = select_counties(cards)
    summary = {
        "selected": [{"fips": item["fips"], "name": item["name"], "queryUrl": item["queryUrl"]} for item in chosen],
        "skipped": skipped,
    }
    print(json.dumps(summary, indent=2))
    if args.probe_only:
        if len(chosen) < TARGET:
            raise SystemExit(f"Only {len(chosen)} reachable counties")
        return
    if len(chosen) < TARGET:
        raise SystemExit(f"Only {len(chosen)} reachable counties; not writing a short batch")
    catalog = json.loads(CATALOG_PATH.read_text())
    selected = {item.lower() for item in args.county}
    pulled = []
    errors: list[str] = []
    for item in chosen:
        if selected and item["fips"] not in selected and item["name"].lower() not in selected:
            continue
        try:
            pulled.append(download_county(catalog, item["card"], args.refresh))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{item['fips']} {item['name']}: {exc}")
            print(f"FAILED {item['fips']}: {exc}", flush=True)
            skipped.append({"fips": item["fips"], "name": item["name"], "reason": f"download failed: {exc}"})
    if errors:
        raise SystemExit("County downloads failed:\n" + "\n".join(errors))
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    if not args.skip_index:
        seed.rebuild_indexes(catalog)
    report = {"pulled": pulled, "skipped": skipped}
    (CARDS / "batch1-result.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Done", json.dumps(pulled, indent=2))


if __name__ == "__main__":
    sys.exit(main())
