#!/usr/bin/env python3
"""5.0–150.0 acre parcels for Alabama rural Opportunity Zone batch 1.

Walks data/al-parcel-cards/rural-oz2-candidate-counties-2026-09-28.csv in
priority order. A county is eligible when its county card has a public parcel
polygon (status usable, or partial when that is the only public layer) and the
repo does not already have a complete 5.0–150.0 acre extract. Flagship cards
with no parcel REST are skipped. If the live endpoint does not answer, that
county is skipped and the next CSV row is used. The first 20 that download are
written.

Does not add a market shelf. Counties already on a shelf stay there. Others go
on the nearest existing Alabama shelf. No Opportunity Zone status, school
grade, or base flood elevation is stored. Household income stays the ACS
B19013_001E join. AADT stays the query-time statewide join. Property-appraiser
URLs are stored from the card pattern and are not requested. Owner phone and
email are not ingested. Sale dates after the pull date are cleared.

Mobile account numbers drop leading zeros for links. Shelby uses the card
field map as written.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any

import yaml

import seed_market_parcels as seed

ROOT = seed.ROOT
CATALOG_PATH = seed.CATALOG_PATH
CARDS = ROOT / "data" / "al-parcel-cards"
CSV_PATH = CARDS / "rural-oz2-candidate-counties-2026-09-28.csv"
CACHE_DIR = Path("/tmp/dls-al-rural-oz-batch1")
TODAY = date.today().isoformat()
TARGET = 20
BANNED_FIELD = re.compile(r"phone|e-?mail|ssn|confidential", re.I)
EMAIL_VALUE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_VALUE = re.compile(r"^\+?1?[\s().-]*\d{3}[\s().-]*\d{3}[\s().-]*\d{4}$")
SQFT_MIN = 217800.0
SQFT_MAX = 6534000.0
# West, south, east, north. Drops a wrong-state service that still returns polygons.
AL_BBOX = (-88.55, 30.10, -84.75, 35.10)
FIELD_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PAID_VENDOR = re.compile(r"regrid|reportall", re.I)

# Nearest existing Alabama shelf when the card only says "Rural OZ 2.0"
# and the county is not already on a shelf. Distances are county seat to the
# shelf city; an Alabama shelf is preferred over a nearer out-of-state shelf.
NEAREST_AL_SHELF = {
    "01005": ["Montgomery"],  # Barbour / Clayton
    "01011": ["Montgomery"],  # Bullock / Union Springs
    "01015": ["Birmingham"],  # Calhoun / Anniston
    "01019": ["Huntsville"],  # Cherokee / Centre
    "01033": ["Huntsville"],  # Colbert / Tuscumbia
    "01037": ["Birmingham"],  # Coosa / Rockford
    "01047": ["Montgomery"],  # Dallas / Selma
    "01049": ["Huntsville"],  # DeKalb / Fort Payne
    "01055": ["Birmingham"],  # Etowah / Gadsden
    "01059": ["Huntsville"],  # Franklin / Russellville
    "01067": ["Montgomery"],  # Henry / Abbeville
    "01077": ["Huntsville"],  # Lauderdale / Florence
    "01079": ["Huntsville"],  # Lawrence / Moulton
    "01087": ["Montgomery"],  # Macon / Tuskegee
    "01099": ["Mobile"],  # Monroe / Monroeville
    "01119": ["Tuscaloosa"],  # Sumter / Livingston
    "01131": ["Montgomery"],  # Wilcox / Camden
    "01133": ["Huntsville"],  # Winston / Double Springs
}

PRINT_LOCK = threading.Lock()


def log(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


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


def fast_json(url: str, params: dict | None = None, timeout: int = 40) -> dict:
    return seed.fetch_json(url, params, timeout=timeout, retries=2)


def layer_meta(url: str) -> dict:
    return fast_json(service_base(url), {"f": "json"}, timeout=40)


def field_names(url: str) -> list[str]:
    data = layer_meta(url)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:240])
    names = [str(field.get("name")) for field in data.get("fields") or [] if field.get("name")]
    if not names:
        raise RuntimeError(f"No fields from {service_base(url)}")
    return names


def count_where(url: str, where: str) -> int:
    data = fast_json(url, {"where": where, "returnCountOnly": "true", "f": "json"}, timeout=50)
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
    text = re.sub(r"\s+County.*$", "", text).strip()
    return text or fallback


def choose_layer(card: dict) -> dict:
    layers = [
        layer
        for layer in card.get("layers") or []
        if layer.get("role") == "parcels" and layer.get("restUrl") and layer.get("geometry") == "polygon"
    ]
    usable = [layer for layer in layers if layer.get("status") == "usable"]
    partial = [layer for layer in layers if layer.get("status") == "partial"]
    pool = usable or partial
    if not pool:
        raise RuntimeError("no public parcel layer")
    countywide = [layer for layer in pool if str(layer.get("coverage") or "").startswith("county")]
    layer = (countywide or pool)[0]
    url = str(layer.get("restUrl") or "")
    if PAID_VENDOR.search(url):
        raise RuntimeError("paid vendor endpoint")
    return layer


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


def field_tokens(key: str) -> list[str]:
    chunks = key.split("+") if "+" in key else [key]
    tokens: list[str] = []
    for chunk in chunks:
        match = FIELD_TOKEN.search(chunk)
        if match and match.group(0) not in tokens:
            tokens.append(match.group(0))
    return tokens


def same_service(left: str | None, right: str | None) -> bool:
    return bool(left and right and norm_source(left) == norm_source(right))


def attribute_field_map(card: dict, layer: dict, available: set[str]) -> dict[str, str]:
    """Parcel field map as written, plus tax/sale/owner maps on the same service."""
    field_map = mapped_fields(layer)
    base = str(layer.get("restUrl") or "")
    extras: list[dict] = []
    for section in (card.get("fullSuite") or {}, card.get("pass2") or {}, card.get("pass2RuralOz2026_09_28") or {}):
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
        "tax.due": "taxes",
        "tax.landValue": "land",
        "tax.buildingValue": "building",
        "tax.improvementValue": "building",
        "mailingAddress.street": "mail1",
        "mailingAddress.line1": "mail1",
        "mailingAddress.line2": "mail2",
        "mailingAddress.street2": "mail2",
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
        "appraiserSearchUrl": "paUrl",
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


def sensitive_contact(value: str | None) -> bool:
    text = seed.clean(value)
    if not text:
        return False
    if EMAIL_VALUE.match(text):
        return True
    return bool(PHONE_VALUE.match(text))


def collect_mapped(attrs: dict, field_map: dict[str, str]) -> dict[str, Any]:
    buckets: dict[str, Any] = {}
    for key, label in field_map.items():
        bucket = target_bucket(label)
        if not bucket:
            continue
        tokens = field_tokens(key)
        if "+" in key:
            if bucket in {"market", "assessed", "taxable", "land", "building", "taxes"}:
                total = 0.0
                seen = False
                for part in tokens:
                    parsed = money(attrs.get(part))
                    if parsed is not None:
                        total += parsed
                        seen = True
                if seen and not buckets.get(bucket):
                    buckets[bucket] = total
            else:
                parts = [seed.clean(attrs.get(part)) for part in tokens]
                text = " ".join(part for part in parts if part) or None
                if text and not buckets.get(bucket):
                    buckets[bucket] = text
            continue
        name = tokens[0] if tokens else key.split()[0]
        raw = attrs.get(name)
        if bucket in {"market", "assessed", "taxable", "land", "building", "taxes", "salePrice", "acres"}:
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
    return buckets


def pin_field_name(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    match = FIELD_TOKEN.search(raw.strip())
    return match.group(0) if match else None


def strip_leading_zeros(value: str) -> str:
    stripped = value.lstrip("0")
    return stripped or "0"


def integral_text(value: Any) -> str | None:
    """ArcGIS doubles such as Cullman PIN 15934.0 are whole numbers, not dotted ids."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = seed.clean(value)
    if text and re.fullmatch(r"-?\d+\.0", text):
        return str(int(float(text)))
    return text


def link_pin(fips: str, pin_note: str | None, raw: Any) -> str | None:
    """Mobile account numbers lose leading zeros. Other pins are the card field."""
    text = integral_text(raw)
    if not text:
        return None
    note = pin_note or ""
    if fips == "01097" and "account" in note.lower():
        return strip_leading_zeros(text)
    if "leading zero" in note.lower():
        return strip_leading_zeros(text)
    return text


def apply_template(template: str | None, pin: str | None) -> str | None:
    if not template or not pin:
        return None
    if "{PIN}" not in template and "{parcelId}" not in template:
        return None
    encoded = urllib.parse.quote(pin, safe=".-_")
    return template.replace("{PIN}", encoded).replace("{parcelId}", encoded)


def card_links(card: dict) -> dict[str, Any]:
    deep = {}
    for section in (card.get("pass2RuralOz2026_09_28") or {}, card.get("pass2") or {}):
        if isinstance(section, dict) and isinstance(section.get("deepLink"), dict) and not deep:
            deep = section["deepLink"]
    template = card.get("appraiserSearchUrl")
    pattern = deep.get("pattern") if isinstance(deep, dict) else None
    if isinstance(pattern, str) and "{PIN}" in pattern:
        template = pattern
    elif isinstance(template, str) and "{PIN}" not in template and "{parcelId}" not in template:
        template = pattern if isinstance(pattern, str) else None
    verified = str((deep or {}).get("verified") or "").strip().lower()
    gis = None
    gis_block = (card.get("pass2RuralOz2026_09_28") or {}).get("jurisdictionGisUrl")
    if isinstance(gis_block, dict) and isinstance(gis_block.get("url"), str):
        gis = gis_block["url"]
    gis = gis or card.get("jurisdictionGisUrl") or card.get("publicGisUrl")
    return {
        "template": template if isinstance(template, str) else None,
        "pinNote": (deep or {}).get("pinField") if isinstance(deep, dict) else None,
        "pinField": pin_field_name((deep or {}).get("pinField") if isinstance(deep, dict) else None),
        "gis": gis if isinstance(gis, str) else None,
        "verified": verified == "yes",
    }


def in_alabama(center: tuple[float, float] | None) -> bool:
    if not center or not seed.plausible_centroid(center):
        return False
    lon, lat = center
    west, south, east, north = AL_BBOX
    return west <= lon <= east and south <= lat <= north


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


def feature_from(
    attrs: dict,
    geom: dict | None,
    *,
    card: dict,
    field_map: dict[str, str],
    markets: list[str],
    source: str,
    acres_scale: float,
    use_geometry_acres: bool,
    acre_field: str | None,
    links: dict,
) -> dict | None:
    geometry, computed = seed.rings_to_feature_geometry(geom)
    if not geometry:
        return None
    center = seed.centroid_of(geometry)
    if not in_alabama(center):
        return None
    mapped = collect_mapped(attrs, field_map)
    acres = None
    if acre_field and not use_geometry_acres:
        raw_acres = attrs.get(acre_field)
        acres = seed.num(str(raw_acres).replace(",", "")) if isinstance(raw_acres, str) else seed.num(raw_acres)
        if acres is not None and acres_scale != 1:
            acres = acres / acres_scale
    if acres is None:
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
    parcel_id = integral_text(mapped.get("parcelId"))
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
    owner = mapped.get("owner")
    owner2 = mapped.get("owner2")
    if sensitive_contact(owner):
        owner = None
    if sensitive_contact(owner2):
        owner2 = None
    county_name = short_name(card, "Alabama")
    feature = seed.empty_feature(
        fips=str(card["fips"]).zfill(5),
        county=county_name,
        state="Alabama",
        markets=markets,
        parcel_id=parcel_id,
        acreage=float(acres),
        geometry=geometry,
        center=center,  # type: ignore[arg-type]
        source=source,
        owner=owner,
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
    feature["properties"]["ownerName2"] = owner2
    if mapped.get("taxes"):
        feature["properties"]["tax"]["taxes"] = mapped["taxes"]
    if mapped.get("flu"):
        feature["properties"]["flu"] = {"code": mapped["flu"], "label": mapped["flu"], "jurisdiction": None}
    fips = str(card["fips"]).zfill(5)
    pin_raw = attrs.get(links["pinField"]) if links.get("pinField") else None
    pin = link_pin(fips, links.get("pinNote"), pin_raw)
    pa_url = mapped.get("paUrl")
    if isinstance(pa_url, str) and pa_url.lower().startswith("http") and "{PIN}" not in pa_url:
        feature["properties"]["appraiserUrl"] = pa_url
    else:
        feature["properties"]["appraiserUrl"] = apply_template(links.get("template"), pin or parcel_id)
    if links.get("gis"):
        feature["properties"]["gisViewerUrl"] = links["gis"]
    clear_future_sale(feature["properties"])
    scrub(feature["properties"])
    return feature


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


ACRE_LABELS = {"acreage", "acreagegis", "acreagegisalt", "acreagealt"}


def acre_field_candidates(layer: dict, field_map: dict[str, str], available: set[str]) -> list[str]:
    """Card acreageField first, then other acreage labels on the same field map."""
    ordered: list[str] = []
    preferred = layer.get("acreageField")
    if isinstance(preferred, str) and preferred in available:
        ordered.append(preferred)
    for key, label in field_map.items():
        text = label.split("(")[0].strip().lower()
        name = key.split()[0]
        if text in ACRE_LABELS and "+" not in key and name in available and name not in ordered:
            ordered.append(name)
    return ordered


def resolve_acres(
    url: str,
    where: str,
    layer: dict,
    field_map: dict[str, str],
    available: set[str],
) -> tuple[str, float, bool, int, str | None]:
    """Return where, acres scale, geometry-acres flag, source count, and acre field."""
    base = where or "1=1"
    total = count_where(url, base)
    if total <= 0:
        raise RuntimeError("source returned no features")
    scored: list[tuple[int, str, float, bool, str]] = []
    for field in acre_field_candidates(layer, field_map, available):
        numeric = f"({base}) AND {field}>=5 AND {field}<=150"
        sqft = f"({base}) AND {field}>={int(SQFT_MIN)} AND {field}<={int(SQFT_MAX)}"
        acre_count = try_count(url, numeric)
        sqft_count = try_count(url, sqft) if acre_count < 500 else 0
        if sqft_count >= 200 and sqft_count > acre_count * 5:
            scored.append((sqft_count, sqft, 43560.0, False, field))
            continue
        if acre_count > 0:
            scored.append((acre_count, numeric, 1.0, False, field))
            continue
        cast = f"({base}) AND CAST({field} AS FLOAT)>=5 AND CAST({field} AS FLOAT)<=150"
        cast_count = try_count(url, cast)
        if cast_count > 0:
            scored.append((cast_count, cast, 1.0, False, field))
    if scored:
        preferred = acre_field_candidates(layer, field_map, available)[:1]
        preferred_name = preferred[0] if preferred else None
        best = max(scored, key=lambda item: item[0])
        preferred_hit = next((item for item in scored if item[4] == preferred_name and item[2] == 1.0), None)
        # Keep the card's acreage field when it actually covers the band.
        # A near-empty deeded field loses to a mapped GIS acre field (Blount CalculatedAcreage).
        if preferred_hit and preferred_hit[0] >= 200 and preferred_hit[0] >= best[0] * 0.4:
            chosen = preferred_hit
        else:
            chosen = best
        # A field that covers only a sliver of the county (Wilcox CALC_ACRE) is not the band.
        sparse_band = chosen[0] < 1500 and chosen[0] < total * 0.08
        if (chosen[0] < 200 or sparse_band) and total <= 80000:
            return base, 1.0, True, total, None
        return chosen[1], chosen[2], False, chosen[0], chosen[4]
    if total > 80000:
        area = f"({base}) AND SHAPE.STArea()>={int(SQFT_MIN)} AND SHAPE.STArea()<={int(SQFT_MAX)}"
        area_count = try_count(url, area)
        if area_count > 0:
            return area, 1.0, True, area_count, None
        raise RuntimeError(f"no acreage filter and {total} features is too large to scan")
    return base, 1.0, True, total, None


def fetch_paged(url: str, where: str, out_fields: list[str]) -> list[dict]:
    meta = layer_meta(url)
    oid = str((meta.get("objectIdField") or "OBJECTID"))
    page_size = int(meta.get("maxRecordCount") or 1000)
    page_size = max(50, min(page_size, 1000))
    features: list[dict] = []
    seen: set[int] = set()
    offset = 0
    while True:
        data = seed.fetch_json(
            url,
            {
                "where": where,
                "outFields": ",".join(out_fields) if out_fields else "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "resultOffset": str(offset),
                "resultRecordCount": str(page_size),
                "orderByFields": oid,
                "f": "json",
            },
            timeout=180,
            retries=3,
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:240])
        batch = data.get("features") or []
        fresh = 0
        for item in batch:
            attrs = item.get("attributes") or {}
            key = attrs.get(oid)
            if isinstance(key, int) and key in seen:
                continue
            if isinstance(key, int):
                seen.add(key)
            features.append(item)
            fresh += 1
        log(f"    paged {len(features)}")
        if fresh == 0 or not data.get("exceededTransferLimit") and len(batch) < page_size:
            break
        offset += len(batch)
        if offset > 120000:
            break
    return features


def pull_raw(url: str, where: str, out_fields: list[str]) -> list[dict]:
    try:
        ids = seed.fetch_object_ids(url, where)
    except Exception as exc:  # noqa: BLE001
        log(f"    object ids failed ({exc}); paging")
        return fetch_paged(url, where, out_fields)
    if not ids:
        return fetch_paged(url, where, out_fields)
    return seed.fetch_by_ids(url, ids, out_fields, batch=80)


def pull_features(
    url: str,
    where: str,
    out_fields: list[str],
    card: dict,
    field_map: dict[str, str],
    markets: list[str],
    source: str,
    acres_scale: float,
    use_geometry_acres: bool,
    acre_field: str | None,
    links: dict,
) -> tuple[list[dict], int]:
    raw = pull_raw(url, where, out_fields)
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
            acre_field=acre_field,
            links=links,
        )
        if feature is None:
            dropped += 1
            continue
        features.append(feature)
    features = dedupe(features)
    return features, dropped


def markets_for(catalog: dict, fips: str) -> list[str]:
    found: list[str] = []
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips and market["id"] not in found:
                found.append(market["id"])
    return found


def planned_markets(catalog: dict, fips: str, card: dict) -> list[str]:
    existing = markets_for(catalog, fips)
    if existing:
        return existing
    shelf_ids = {market["id"] for market in catalog["markets"]}
    chosen: list[str] = []
    for label in card.get("markets") or []:
        if label in shelf_ids and label not in chosen:
            chosen.append(label)
    if not chosen:
        for market_id in NEAREST_AL_SHELF.get(fips, []):
            if market_id in shelf_ids and market_id not in chosen:
                chosen.append(market_id)
    if not chosen:
        raise RuntimeError(f"{fips} is not on an existing shelf")
    return chosen


def commit_markets(catalog: dict, fips: str, name: str, markets: list[str]) -> None:
    if markets_for(catalog, fips):
        return
    by_market = {market["id"]: market for market in catalog["markets"]}
    for market_id in markets:
        market = by_market[market_id]
        market["counties"].append({"name": name, "state": "Alabama", "fips": fips})


def gap_notes(card: dict, layer: dict, source_count: int, kept: int) -> list[str]:
    notes = []
    if source_count and kept < source_count:
        notes.append(
            f"Source query returned {source_count} rows; {kept} stayed in the 5.0–150.0 acre band after the parcel-id and geometry checks."
        )
    name = layer.get("name") or "card parcel layer"
    url = layer.get("restUrl")
    notes.append(
        f"Parcels are {name} ({url}). Acreage is 5.0–150.0 inclusive. No Opportunity Zone status, school grade, or base flood elevation is stored."
    )
    if layer.get("status") == "partial":
        notes.append("The card marks this public parcel layer partial. Attributes that are absent stay empty.")
    notes.append("Property-appraiser links are stored from the card pattern and were not requested.")
    notes.append("Owner phone and email are not ingested. ALDOT AADT stays the query-time statewide join.")
    for gap in card.get("gaps") or []:
        text = seed.clean(gap)
        if text and not BANNED_FIELD.search(text):
            notes.append(text)
    unique: list[str] = []
    for note in notes:
        if note not in unique:
            unique.append(note)
    return unique[:8]


def backup_county(fips: str) -> None:
    src = seed.COUNTY_DIR / fips
    dest = CACHE_DIR / "backup" / fips
    if dest.exists():
        shutil.rmtree(dest)
    if src.exists():
        shutil.copytree(src, dest)


def restore_county(fips: str) -> None:
    dest = seed.COUNTY_DIR / fips
    src = CACHE_DIR / "backup" / fips
    if dest.exists():
        shutil.rmtree(dest)
    if src.exists():
        shutil.copytree(src, dest)


def write_county(
    county: dict,
    markets: list[str],
    features: list[dict],
    *,
    source: str,
    url: str,
    gaps: list[str],
    source_count: int,
    dropped: int,
    links: dict,
) -> None:
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
            "appraiserSearchUrl": links.get("template"),
            "gisViewerUrl": links.get("gis"),
            "minAcres": 5.0,
            "maxAcres": 150.0,
        },
    )
    log(f"  kept {len(features)} tiles {tiles}")


def download_county(card: dict, markets: list[str], refresh: bool) -> dict:
    fips = str(card["fips"]).zfill(5)
    name = short_name(card, fips)
    layer = choose_layer(card)
    url = query_url(str(layer["restUrl"]))
    source = f"al-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}-parcels-{fips}"
    county = {"name": name, "state": "Alabama", "fips": fips}
    links = card_links(card)
    cache_path = CACHE_DIR / f"{fips}.json"
    backup_county(fips)
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features:
            log(f"Pulling {name} {fips} cache {len(features)}")
            for feature in features:
                feature["properties"]["marketIds"] = markets
                feature["properties"]["state"] = "Alabama"
                clear_future_sale(feature["properties"])
                scrub(feature["properties"])
            write_county(
                county,
                markets,
                features,
                source=source,
                url=cached.get("queryUrl") or url,
                gaps=cached.get("gaps") or [],
                source_count=int(cached.get("sourceCount") or len(features)),
                dropped=int(cached.get("dropped") or 0),
                links=links,
            )
            return {
                "fips": fips,
                "name": name,
                "featureCount": len(features),
                "queryUrl": cached.get("queryUrl") or url,
                "markets": markets,
                "source": source,
            }
    log(f"Pulling {name} {fips} {url}")
    available = set(field_names(url))
    field_map = attribute_field_map(card, layer, available)
    parcel_field = next(
        (key.split()[0] for key, label in field_map.items() if target_bucket(label) == "parcelId" and "+" not in key),
        None,
    )
    if parcel_field and parcel_field not in field_map and parcel_field in available:
        field_map[parcel_field] = "parcelId"
    card_where = layer.get("where") or "1=1"
    where, scale, geometry_acres, source_count, acre_field = resolve_acres(url, card_where, layer, field_map, available)
    log(f"  source rows {source_count} where {where[:160]}")
    out_fields = simple_sources(field_map, available)
    if parcel_field and parcel_field in available and parcel_field not in out_fields:
        out_fields.append(parcel_field)
    if acre_field and acre_field not in out_fields:
        out_fields.append(acre_field)
    pin_field = links.get("pinField")
    if isinstance(pin_field, str) and pin_field in available and pin_field not in out_fields:
        out_fields.append(pin_field)
    features, dropped = pull_features(
        url,
        where,
        out_fields,
        card,
        field_map,
        markets,
        source,
        scale,
        geometry_acres,
        acre_field if not geometry_acres else None,
        links,
    )
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
        links=links,
    )
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {"sourceCount": source_count, "dropped": dropped, "queryUrl": url, "gaps": gaps, "features": features},
                separators=(",", ":"),
            )
        )
    except OSError as exc:
        log(f"  cache skipped for {fips}: {exc}")
    return {
        "fips": fips,
        "name": name,
        "featureCount": len(features),
        "queryUrl": url,
        "markets": markets,
        "source": source,
        "sourceCount": source_count,
    }


def classify(cards: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    eligible: list[dict] = []
    skipped: list[dict] = []
    for row in csv_order():
        fips = str(row.get("county_fips") or row.get("fips") or "").zfill(5)
        name = row.get("county") or fips
        card = cards.get(fips)
        if not card or card.get("level") != "county":
            skipped.append({"fips": fips, "name": name, "reason": "no county card"})
            continue
        current = existing_row(fips)
        try:
            layer = choose_layer(card)
            url = query_url(str(layer["restUrl"]))
        except Exception as exc:  # noqa: BLE001
            reason = "no public parcel layer (Flagship or no parcel REST)" if str(exc) == "no public parcel layer" else f"no public parcel layer ({exc})"
            skipped.append({"fips": fips, "name": name, "reason": reason})
            continue
        if fully_loaded(current):
            count = int((current or {}).get("featureCount") or 0)
            skipped.append(
                {
                    "fips": fips,
                    "name": name,
                    "reason": f"already a complete 5.0–150.0 acre extract ({count} parcels)",
                    "queryUrl": (current or {}).get("queryUrl"),
                }
            )
            continue
        eligible.append({"fips": fips, "name": name, "card": card, "queryUrl": url, "layer": layer})
    return eligible, skipped


def probe_one(item: dict) -> dict:
    fips = item["fips"]
    url = item["queryUrl"]
    layer = item["layer"]
    try:
        if PAID_VENDOR.search(url):
            raise RuntimeError("paid vendor endpoint")
        available = set(field_names(url))
        field_map = attribute_field_map(item["card"], layer, available)
        where, _scale, geometry, count, _field = resolve_acres(url, layer.get("where") or "1=1", layer, field_map, available)
        log(f"SELECT {item['name']} {fips} rows {count}")
        return {**item, "ok": True, "where": where, "probeCount": count, "geometryAcres": geometry}
    except Exception as exc:  # noqa: BLE001
        log(f"SKIP {item['name']} {fips}: {exc}")
        return {**item, "ok": False, "reason": f"endpoint unreachable: {exc}"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--indexes-only", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.indexes_only:
        catalog = json.loads(CATALOG_PATH.read_text())
        seed.rebuild_indexes(catalog)
        return
    cards = load_cards()
    eligible, skipped = classify(cards)
    log(f"Eligible before probe: {len(eligible)}")
    probed: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(probe_one, item) for item in eligible]
        for future in as_completed(futures):
            probed.append(future.result())
    by_fips = {item["fips"]: item for item in probed}
    ordered = [by_fips[item["fips"]] for item in eligible]
    reachable = []
    for item in ordered:
        if item["ok"]:
            reachable.append(item)
        else:
            skipped.append({"fips": item["fips"], "name": item["name"], "reason": item["reason"], "queryUrl": item["queryUrl"]})
    summary = {
        "reachable": [{"fips": item["fips"], "name": item["name"], "queryUrl": item["queryUrl"], "probeCount": item.get("probeCount")} for item in reachable],
        "skipped": [{key: value for key, value in item.items() if key != "card" and key != "layer"} for item in skipped],
    }
    print(json.dumps(summary, indent=2))
    if args.probe_only:
        if len(reachable) < TARGET:
            raise SystemExit(f"Only {len(reachable)} reachable counties")
        return
    selected_filter = {item.lower() for item in args.county}
    queue = []
    for item in reachable:
        if selected_filter and item["fips"] not in selected_filter and item["name"].lower() not in selected_filter:
            continue
        queue.append(item)
    if not selected_filter and len(queue) < TARGET:
        raise SystemExit(f"Only {len(queue)} reachable counties; not writing a short batch")
    catalog = json.loads(CATALOG_PATH.read_text())
    for item in queue:
        item["markets"] = planned_markets(catalog, item["fips"], item["card"])
    kept: list[dict] = []
    index = 0
    goal = len(queue) if selected_filter else TARGET
    while len(kept) < goal and index < len(queue):
        # A full worker window lets a failure be replaced by the next row.
        # Successes past the goal are rolled back in priority order.
        batch = queue[index : index + max(1, args.workers)]
        index += len(batch)
        results: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=max(1, len(batch))) as pool:
            futures = {
                pool.submit(download_county, item["card"], item["markets"], args.refresh): item for item in batch
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    results[item["fips"]] = {"ok": True, "pulled": future.result(), "item": item}
                except Exception as exc:  # noqa: BLE001
                    restore_county(item["fips"])
                    log(f"FAILED {item['fips']}: {exc}")
                    results[item["fips"]] = {"ok": False, "error": str(exc), "item": item}
        for item in batch:
            result = results[item["fips"]]
            if not result["ok"]:
                skipped.append({"fips": item["fips"], "name": item["name"], "reason": f"download failed: {result['error']}", "queryUrl": item["queryUrl"]})
                continue
            if selected_filter or len(kept) < TARGET:
                kept.append(result["pulled"])
                continue
            restore_county(item["fips"])
            skipped.append({"fips": item["fips"], "name": item["name"], "reason": "batch already filled"})
    if not selected_filter and len(kept) < TARGET:
        raise SystemExit(f"Only {len(kept)} counties downloaded")
    for item in kept:
        commit_markets(catalog, item["fips"], item["name"], item["markets"])
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    report = {
        "pulled": kept,
        "skipped": [{key: value for key, value in item.items() if key not in {"card", "layer"}} for item in skipped],
    }
    (CARDS / "batch1-result.json").write_text(json.dumps(report, indent=2) + "\n")
    if not args.skip_index:
        seed.rebuild_indexes(catalog)
    log("Done " + json.dumps(kept, indent=2))


if __name__ == "__main__":
    sys.exit(main())
