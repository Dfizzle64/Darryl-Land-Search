#!/usr/bin/env python3
"""5.0–150.0 acre parcels for North Carolina rural Opportunity Zone batch 1.

Walks the pass-1 table in data/nc-parcel-cards/_progress/RURAL_OZ_PASS1_2026-09-28.md
in row order. A row is eligible when its status is verified or fixed and the
repo does not already have a complete 5.0–150.0 acre extract. If the live
endpoint does not answer, that county is skipped and the next row is used.
The first 20 that download are written.

Does not add a market shelf. Counties already on a shelf stay there. Others
go on the nearest existing North Carolina shelf (Asheville, Charlotte,
Raleigh-Durham, Wilmington, or Winston-Salem), measured from the Census county
shape to the shelf city. No Opportunity Zone status, school grade, or base
flood elevation is stored. Household income stays the ACS B19013_001E join.
NCDOT AADT stays the query-time statewide join. Property-appraiser URLs are
copied from the card or pass-2 pattern and are not requested. Owner phone and
email are not ingested. Sale dates after the pull date are cleared.

Pass 2 (tax, sale, owner, property-appraiser deep link, county GIS link, AADT
station note) is read from the card's pass2 block or from
_progress/rural-oz-pass2/res/{fips}.json. A county with neither keeps the
parcel-layer attributes on its card.

County quirks from the pass-1 notes:
- Alexander pages with orderByFields set (the MapServer has no object id).
- Ashe pages with resultRecordCount (an unpaged geometry query stops at 500).
- Hoke uses the county AGOL June2025/1 layer named in the table.
- Swain and Jackson acreage fields are strings and use CAST(... AS FLOAT).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any

import yaml

import seed_market_parcels as seed

ROOT = seed.ROOT
CATALOG_PATH = seed.CATALOG_PATH
CARDS = ROOT / "data" / "nc-parcel-cards"
PASS1_PATH = CARDS / "_progress" / "RURAL_OZ_PASS1_2026-09-28.md"
PASS2_RES = CARDS / "_progress" / "rural-oz-pass2" / "res"
CACHE_DIR = Path("/tmp/dls-nc-rural-oz-batch1")
CENSUS_COUNTIES = ROOT / "data" / "fixtures" / "census" / "cb_2024_us_county_5m.geojson"
TODAY = date.today().isoformat()
TARGET = 20
NC_ONEMAP = (
    "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1/query"
)
BANNED_FIELD = re.compile(r"phone|e-?mail|ssn|areacode|confidential", re.I)
EMAIL_VALUE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_VALUE = re.compile(r"^\+?1?[\s().-]*\d{3}[\s().-]*\d{3}[\s().-]*\d{4}$")
FIELD_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PAID_VENDOR = re.compile(r"regrid|reportall", re.I)
PLACEHOLDER = re.compile(r"\{([A-Za-z0-9_]+)(?::([0-9]*d))?\}")
# West, south, east, north. Drops a wrong-state service that still returns polygons.
NC_BBOX = (-84.55, 33.70, -75.30, 36.62)
# Shelf city coordinates. Raleigh-Durham is the midpoint of Raleigh and Durham.
NC_SHELVES = {
    "Asheville": (-82.5515, 35.5951),
    "Charlotte": (-80.8431, 35.2271),
    "Raleigh-Durham": (-78.7684, 35.8868),
    "Wilmington": (-77.9447, 34.2257),
    "Winston-Salem": (-80.2442, 36.0999),
}
# These MapServers reject resultRecordCount unless orderByFields is set, and
# they do not publish an object id. Page on the parcel id field.
ORDER_BY_PARCEL = {"37003"}
# A geometry query without resultRecordCount stops at 500.
FORCE_PAGE = {"37009"}

PRINT_LOCK = threading.Lock()
CENTER_LOCK = threading.Lock()
CENTERS: dict[str, tuple[float, float]] | None = None


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


def swap_scheme(url: str) -> str | None:
    if url.startswith("https://"):
        return "http://" + url[len("https://") :]
    if url.startswith("http://"):
        return "https://" + url[len("http://") :]
    return None


def fast_json(url: str, params: dict | None = None, timeout: int = 40) -> dict:
    return seed.fetch_json(url, params, timeout=timeout, retries=2)


def open_service(url: str) -> tuple[str, dict]:
    """Return the URL scheme that answered and the layer metadata."""
    candidates = [url]
    alt = swap_scheme(url)
    if alt:
        candidates.append(alt)
    last: Exception | None = None
    for candidate in candidates:
        try:
            data = fast_json(service_base(candidate), {"f": "json"}, timeout=40)
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
        if data.get("error"):
            last = RuntimeError(json.dumps(data["error"])[:240])
            continue
        if not data.get("fields"):
            last = RuntimeError(f"No fields from {service_base(candidate)}")
            continue
        return query_url(candidate), data
    raise RuntimeError(f"endpoint unreachable: {last}")


def field_names(meta: dict) -> list[str]:
    return [str(field.get("name")) for field in meta.get("fields") or [] if field.get("name")]


def count_where(url: str, where: str) -> int:
    data = fast_json(url, {"where": where, "returnCountOnly": "true", "f": "json"}, timeout=50)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:240])
    count = data.get("count")
    if not isinstance(count, int):
        raise RuntimeError(f"No count from {url}: {str(data)[:160]}")
    return count


def try_count(url: str, where: str) -> int:
    try:
        return count_where(url, where)
    except Exception:
        return 0


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


def table_rows() -> list[dict]:
    rows = []
    for line in PASS1_PATH.read_text().splitlines():
        if not line.startswith("| 37"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 10:
            continue
        rows.append(
            {
                "fips": cells[0].zfill(5),
                "name": re.sub(r"\s+", " ", cells[1]).strip(),
                "url": cells[3],
                "idField": cells[4],
                "acreageRaw": cells[6],
                "expected": int(cells[7].replace(",", "") or "0"),
                "status": cells[8].lower(),
                "notes": cells[9],
            }
        )
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
    text = str(card.get("jurisdiction") or card.get("county") or fallback)
    text = re.sub(r"\s+County.*$", "", text).strip()
    return text or fallback


def acre_spec(raw: str) -> tuple[str, bool, list[str]]:
    """Field name, whether to CAST AS FLOAT, and extra where clauses."""
    name = ""
    match = FIELD_TOKEN.search(raw or "")
    if match:
        name = match.group(0)
    cast = "cast" in (raw or "").lower() or "string" in (raw or "").lower()
    extra: list[str] = []
    if "LegalLandType" in (raw or ""):
        extra.append("LegalLandType='AC'")
    return name, cast, extra


def choose_layer(card: dict, table_url: str, acre_field: str) -> dict:
    target = norm_source(table_url)
    layers = [layer for layer in card.get("layers") or [] if layer.get("restUrl")]
    for layer in layers:
        if norm_source(str(layer.get("restUrl"))) == target:
            return layer
    suffix = table_url.rstrip("/").split("/services/")[-1].lower()
    for layer in layers:
        if suffix and suffix in str(layer.get("restUrl") or "").lower():
            return layer
    return {
        "role": "parcels",
        "name": "pass-1 parcel layer",
        "restUrl": table_url,
        "geometry": "polygon",
        "status": "usable",
        "acreageField": acre_field,
        "fieldMap": {},
    }


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


def refine_label(field: str, label: str) -> str:
    name = field.upper()
    text = label.split("(")[0].strip()
    if text in {"mailingAddress", "mailingAddress.full"} or text.startswith("mailingAddress"):
        if "CITY" in name and "STATE" not in name:
            return "mailingAddress.city"
        if name.endswith("STATE") or "STATE" in name and "ESTATE" not in name:
            return "mailingAddress.state"
        if "ZIP" in name:
            return "mailingAddress.zip"
        if any(token in name for token in ("ADDR2", "ADDRESS2", "LINE2", "STREET2")):
            return "mailingAddress.street2"
        if text == "mailingAddress":
            return "mailingAddress.street"
        return text
    if text == "situsAddress":
        if "CITY" in name:
            return "situsCity"
        if "ZIP" in name:
            return "situsZip"
        if "NUM" in name and "STREET" not in name:
            return "situsAddress.number"
        if "STREET" in name or "NAME" in name and "OWNER" not in name:
            return "situsAddress.street"
    if text == "ownerName" and any(token in name for token in ("NAME2", "OWNER2", "OWN2", "NAME_2")):
        return "ownerName2"
    return text


def target_bucket(label: str) -> str | None:
    text = label.split("(")[0].strip()
    aliases = {
        "parcelId": "parcelId",
        "ownerName": "owner",
        "ownerName2": "owner2",
        "acreage": "acres",
        "acreageGis": "acres",
        "acreageAssessed": "acres",
        "acreageLegal": "acres",
        "zoning": "zoning",
        "zoningCode": "zoning",
        "landUse": "dor",
        "dorCode": "dor",
        "useCode": "dor",
        "lastSale.date": "saleDate",
        "lastSale.dateText": "saleDate",
        "lastSale.dateYyyymmdd": "saleDate",
        "lastSale.deedDate": "saleDate",
        "lastSale.currentDeedDate": "saleDate",
        "lastSale.year": "saleYear",
        "lastSale.recordedYear": "saleYear",
        "lastSale.recordedMonth": "saleMonth",
        "lastSale.price": "salePrice",
        "lastSale.qualified": "saleQualified",
        "tax.marketValue": "market",
        "tax.totalValue": "market",
        "tax.assessedValue": "assessed",
        "tax.taxableValue": "taxable",
        "tax.due": "taxes",
        "tax.principalDue": "taxes",
        "tax.landValue": "land",
        "tax.landMarketValue": "land",
        "tax.buildingValue": "building",
        "tax.improvementValue": "building",
        "tax.improvementMarketValue": "building",
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
        "situsAddress.streetName": "situsStreet",
        "situsCity": "situsCity",
        "situsZip": "situsZip",
        "appraiserDeepLink": "paUrl",
        "appraiserSearchUrl": "paUrl",
        "flu": "flu",
    }
    return aliases.get(text)


def guess_tax_label(field: str) -> str | None:
    name = field.lower()
    if BANNED_FIELD.search(name):
        return None
    if any(token in name for token in ("land",)):
        return "tax.landValue"
    if any(token in name for token in ("bldg", "build", "struct", "improv")):
        return "tax.improvementValue"
    if "taxable" in name:
        return "tax.taxableValue"
    if any(token in name for token in ("assess", "assd", "assed")):
        return "tax.assessedValue"
    if any(token in name for token in ("market", "mkt", "tot_val", "total_valu", "totval", "netval", "parval", "totalvalue")):
        return "tax.marketValue"
    return None


def guess_date_label(field: str) -> str:
    name = field.lower()
    if name in {"saleyear", "sale_year", "saleyr"} or name.endswith("year") and "sale" in name:
        return "lastSale.year"
    return "lastSale.date"


def load_pass2(card: dict, fips: str) -> dict[str, Any]:
    block = card.get("pass2") if isinstance(card.get("pass2"), dict) else None
    if block and (block.get("tax") or block.get("paDeepLink") or block.get("aadt")):
        tax = block.get("tax") if isinstance(block.get("tax"), dict) else {}
        sale = block.get("sale") if isinstance(block.get("sale"), dict) else {}
        owner = block.get("ownerEntity") if isinstance(block.get("ownerEntity"), dict) else {}
        deep = block.get("paDeepLink") if isinstance(block.get("paDeepLink"), dict) else {}
        gis = block.get("gisViewer") if isinstance(block.get("gisViewer"), dict) else {}
        aadt = block.get("aadt") if isinstance(block.get("aadt"), dict) else {}
        primary = (aadt.get("primary2022") or {}) if isinstance(aadt.get("primary2022"), dict) else {}
        fallback = tax.get("fallback") if isinstance(tax.get("fallback"), dict) else None
        return {
            "present": True,
            "source": "card pass2",
            "taxStatus": str(tax.get("status") or ""),
            "taxFields": [str(item) for item in tax.get("fields") or [] if isinstance(item, str)],
            "taxFallback": fallback if fallback and fallback.get("restUrl") else None,
            "saleStatus": str(sale.get("status") or ""),
            "priceFields": [str(item) for item in sale.get("priceFields") or [] if isinstance(item, str)],
            "dateFields": [str(item) for item in sale.get("dateFields") or [] if isinstance(item, str)],
            "saleNote": str(sale.get("note") or ""),
            "ownerFields": [str(item) for item in owner.get("ownerFields") or [] if isinstance(item, str)],
            "paTemplate": deep.get("template") if isinstance(deep.get("template"), str) else None,
            "paVerified": bool(deep.get("contentVerified")),
            "gis": gis.get("url") if isinstance(gis.get("url"), str) else None,
            "aadtStations": primary.get("liveStationCount"),
            "gaps": [str(item) for item in block.get("gaps") or [] if item],
        }
    path = PASS2_RES / f"{fips}.json"
    if path.exists():
        data = json.loads(path.read_text())
        sample = data.get("sample") if isinstance(data.get("sample"), dict) else {}
        pa_url = data.get("pa_url") if isinstance(data.get("pa_url"), str) else None
        template = None
        if pa_url:
            candidates = [str(value).strip() for value in sample.values() if value is not None]
            candidates.sort(key=len, reverse=True)
            for text in candidates:
                if len(text) >= 5 and text in pa_url:
                    template = pa_url.replace(text, "{parcelId}", 1)
                    break
        verified = bool(data.get("pa_has_id")) and str(data.get("pa_http") or "").startswith("200")
        return {
            "present": True,
            "source": "rural-oz-pass2 res",
            "taxStatus": "ok" if data.get("tax") else "",
            "taxFields": [str(key) for key, count in (data.get("tax") or {}).items() if isinstance(count, int) and count > 0],
            "taxFallback": None,
            "saleStatus": "ok" if data.get("price") or data.get("date") else "",
            "priceFields": [str(key) for key, count in (data.get("price") or {}).items() if isinstance(count, int) and count > 0],
            "dateFields": [str(key) for key, count in (data.get("date") or {}).items() if isinstance(count, int) and count > 0],
            "saleNote": "",
            "ownerFields": [],
            "paTemplate": template,
            "paVerified": verified,
            "gis": data.get("gis_url") if isinstance(data.get("gis_url"), str) else None,
            "aadtStations": data.get("aadt22_count"),
            "gaps": [],
        }
    return {
        "present": False,
        "source": None,
        "taxStatus": "",
        "taxFields": [],
        "taxFallback": None,
        "saleStatus": "",
        "priceFields": [],
        "dateFields": [],
        "saleNote": "",
        "ownerFields": [],
        "paTemplate": None,
        "paVerified": False,
        "gis": None,
        "aadtStations": None,
        "gaps": [],
    }


def attribute_field_map(layer: dict, pass2: dict, available: set[str], id_field: str) -> dict[str, str]:
    field_map = {key: refine_label(key, label) for key, label in mapped_fields(layer).items()}
    if pass2["taxStatus"] in {"gap", "scrubbed"}:
        field_map = {key: label for key, label in field_map.items() if not label.startswith("tax.")}
    if pass2["present"] and not pass2["priceFields"]:
        field_map = {key: label for key, label in field_map.items() if target_bucket(label) != "salePrice"}
    lookup = {name.lower(): name for name in available}

    def live(name: str) -> str | None:
        if name in available:
            return name
        return lookup.get(name.lower())

    def add(name: str, label: str) -> None:
        found = live(name)
        if not found or BANNED_FIELD.search(found):
            return
        if found not in field_map:
            field_map[found] = label

    if pass2["taxStatus"] == "ok":
        for name in pass2["taxFields"]:
            label = guess_tax_label(name)
            if label:
                add(name, label)
    for name in pass2["priceFields"]:
        if "stamp" in name.lower():
            continue
        add(name, "lastSale.price")
    for name in pass2["dateFields"]:
        add(name, guess_date_label(name))
    for index, name in enumerate(pass2["ownerFields"]):
        add(name, "ownerName" if index == 0 else "ownerName2")
    found_id = live(id_field)
    if found_id and found_id not in field_map:
        field_map[found_id] = "parcelId"
    return field_map


def simple_sources(field_map: dict[str, str], available: set[str]) -> list[str]:
    wanted: list[str] = []
    lookup = {name.lower(): name for name in available}
    for key in field_map:
        for name in field_tokens(key):
            found = name if name in available else lookup.get(name.lower())
            if found and found not in wanted and not BANNED_FIELD.search(found):
                wanted.append(found)
    return wanted


def resolve_acres(
    url: str,
    acre_field: str,
    cast_hint: bool,
    extra: list[str],
    available: set[str],
    expected: int,
) -> tuple[str, float, bool, int, str | None]:
    lookup = {name.lower(): name for name in available}
    field = acre_field if acre_field in available else lookup.get(acre_field.lower())
    total = count_where(url, "1=1")
    if total <= 0:
        raise RuntimeError("source returned no features")
    variants: list[tuple[str, float, str | None]] = []
    if field:
        expr = field
        cast_expr = f"CAST({field} AS FLOAT)"
        extras = " AND ".join(extra)
        suffix = f" AND {extras}" if extras else ""
        variants.append((f"{expr}>=5 AND {expr}<=150{suffix}", 1.0, field))
        if cast_hint:
            variants.insert(0, (f"{cast_expr}>=5 AND {cast_expr}<=150{suffix}", 1.0, field))
        else:
            variants.append((f"{cast_expr}>=5 AND {cast_expr}<=150{suffix}", 1.0, field))
        variants.append((f"{expr}>={int(seed.MIN_SQFT)} AND {expr}<={int(seed.MAX_SQFT)}{suffix}", 43560.0, field))
    scored: list[tuple[int, str, float, str | None]] = []
    for where, scale, name in variants:
        count = try_count(url, where)
        if count > 0:
            scored.append((count, where, scale, name))
    if scored:
        if expected > 0:
            chosen = min(scored, key=lambda item: (abs(item[0] - expected), -item[0]))
        else:
            chosen = max(scored, key=lambda item: item[0])
        if chosen[0] < 50 and total <= 80000:
            return "1=1", 1.0, True, total, None
        return chosen[1], chosen[2], False, chosen[0], chosen[3]
    if total > 80000:
        raise RuntimeError(f"no acreage filter and {total} features is too large to scan")
    return "1=1", 1.0, True, total, None


def parse_sale_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    if text in {"0", "00000000"}:
        return None
    if re.fullmatch(r"\d{8}", text):
        year = int(text[:4])
        if 1900 <= year <= 2100:
            return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    if re.fullmatch(r"\d{4}", text):
        year = int(text)
        if 1900 <= year <= 2100:
            return f"{year:04d}-01-01"
    number = seed.num(value)
    if number is not None and abs(number) < 100_000:
        return None
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


def parse_acres(value: Any) -> float | None:
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if not match:
            return None
        return seed.num(match.group(0))
    return seed.num(value)


def sensitive_contact(value: str | None) -> bool:
    text = seed.clean(value)
    if not text:
        return False
    if EMAIL_VALUE.match(text):
        return True
    return bool(PHONE_VALUE.match(text))


def attr_get(attrs: dict, name: str) -> Any:
    if name in attrs:
        return attrs[name]
    lowered = name.lower()
    for key, value in attrs.items():
        if str(key).lower() == lowered:
            return value
    return None


def integral_text(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = seed.clean(value)
    if text and re.fullmatch(r"-?\d+\.0", text):
        return str(int(float(text)))
    return text


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
                    parsed = money(attr_get(attrs, part))
                    if parsed is not None:
                        total += parsed
                        seen = True
                if seen and not buckets.get(bucket):
                    buckets[bucket] = total
            else:
                parts = [seed.clean(attr_get(attrs, part)) for part in tokens]
                text = " ".join(part for part in parts if part) or None
                if text and not buckets.get(bucket):
                    buckets[bucket] = text
            continue
        name = tokens[0] if tokens else key.split()[0]
        raw = attr_get(attrs, name)
        if bucket in {"market", "assessed", "taxable", "land", "building", "taxes", "salePrice", "acres"}:
            parsed = parse_acres(raw) if bucket == "acres" else money(raw)
            if parsed is not None and buckets.get(bucket) is None:
                buckets[bucket] = parsed
            continue
        if bucket in {"saleDate", "saleYear", "saleMonth"}:
            if bucket == "saleDate":
                parsed_date = parse_sale_date(raw)
                if parsed_date and not buckets.get("saleDate"):
                    buckets["saleDate"] = parsed_date
            else:
                parsed_num = seed.num(raw)
                if parsed_num is not None and buckets.get(bucket) is None:
                    buckets[bucket] = parsed_num
            continue
        text = integral_text(raw) if bucket == "parcelId" else seed.clean(raw)
        if text and not buckets.get(bucket):
            buckets[bucket] = text
    return buckets


def fill_template(template: str | None, attrs: dict, parcel_id: str) -> str | None:
    if not template:
        return None
    if "{" not in template:
        return template

    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        fmt = match.group(2)
        source = token
        transform = None
        if token.endswith("_NO_DASHES"):
            source = token[: -len("_NO_DASHES")]
            transform = "nodash"
        raw = attr_get(attrs, source)
        if raw is None and token.lower() in {"pin", "parcelid", "id", "parcel"}:
            raw = parcel_id
        if raw is None:
            return match.group(0)
        text = integral_text(raw) or ""
        if transform == "nodash":
            text = text.replace("-", "")
        if fmt and fmt.endswith("d"):
            width = int(fmt[:-1] or "0")
            digits = re.sub(r"\D", "", text) or "0"
            text = str(int(digits)).zfill(width)
        from urllib.parse import quote

        return quote(text, safe=".-_")

    filled = PLACEHOLDER.sub(repl, template)
    if "{" in filled:
        return None
    return filled


BAKED_ACCOUNT = re.compile(r"(?:owner\s*id|ownerid)=\d{4,}", re.I)


def card_placeholder(card: dict) -> str | None:
    for key in ("appraiserSearchUrl", "ncptsDeepLinkTemplate", "viewerLinkTemplate"):
        value = card.get(key)
        if isinstance(value, str) and "{" in value:
            return value
    return None


def card_links(card: dict, pass2: dict) -> dict[str, Any]:
    template = pass2.get("paTemplate") if isinstance(pass2.get("paTemplate"), str) else None
    # A pass-2 sample URL can leave one account number on every parcel. The card
    # placeholder template is the public pattern for that case.
    placeholder = card_placeholder(card)
    if placeholder and (not template or BAKED_ACCOUNT.search(template)):
        template = placeholder
    if not template:
        for key in ("appraiserSearchUrl", "ncptsSearchUrl"):
            value = card.get(key)
            if isinstance(value, str) and value.startswith("http"):
                template = value
                break
    gis = pass2.get("gis") if isinstance(pass2.get("gis"), str) else None
    if not gis:
        for key in ("jurisdictionGisUrl", "publicGisUrl", "gisViewerUrl"):
            value = card.get(key)
            if isinstance(value, str) and value.startswith("http"):
                gis = value
                break
    return {
        "template": template,
        "gis": gis,
        "verified": bool(pass2.get("paVerified")),
    }


def in_north_carolina(center: tuple[float, float] | None) -> bool:
    if not center or not seed.plausible_centroid(center):
        return False
    lon, lat = center
    west, south, east, north = NC_BBOX
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
    name: str,
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
    if not in_north_carolina(center):
        return None
    mapped = collect_mapped(attrs, field_map)
    acres = None
    if acre_field and not use_geometry_acres:
        acres = parse_acres(attr_get(attrs, acre_field))
        if acres is not None and acres_scale != 1:
            acres = acres / acres_scale
    if acres is None or acres <= 0:
        acres = mapped.get("acres")
        if isinstance(acres, (int, float)) and acres_scale != 1:
            acres = acres / acres_scale
    if use_geometry_acres or acres is None or acres <= 0:
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
    sale_date = mapped.get("saleDate")
    if not sale_date and mapped.get("saleYear"):
        sale_date = seed.sale_date(mapped.get("saleYear"), mapped.get("saleMonth"))
    feature = seed.empty_feature(
        fips=str(card.get("fips") or "").zfill(5),
        county=name,
        state="North Carolina",
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
        sale_date=sale_date,
        sale_qualified=mapped.get("saleQualified"),
        market_value=mapped.get("market"),
        assessed=mapped.get("assessed"),
        taxable=mapped.get("taxable"),
        mail1=mapped.get("mail1") if not sensitive_contact(mapped.get("mail1")) else None,
        mail2=mapped.get("mail2") if not sensitive_contact(mapped.get("mail2")) else None,
        mail_city=mail_city,
        mail_state=mail_state,
        mail_zip=mail_zip,
    )
    feature["properties"]["ownerName2"] = owner2
    if mapped.get("taxes"):
        feature["properties"]["tax"]["taxes"] = mapped["taxes"]
    if mapped.get("flu"):
        feature["properties"]["flu"] = {"code": mapped["flu"], "label": mapped["flu"], "jurisdiction": None}
    pa_url = mapped.get("paUrl")
    if isinstance(pa_url, str) and pa_url.lower().startswith("http") and "{" not in pa_url:
        feature["properties"]["appraiserUrl"] = pa_url
    else:
        feature["properties"]["appraiserUrl"] = fill_template(links.get("template"), attrs, parcel_id)
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


def fetch_paged(
    url: str,
    where: str,
    out_fields: list[str],
    order_field: str | None,
    expected: int | None = None,
) -> list[dict]:
    meta = fast_json(service_base(url), {"f": "json"}, timeout=40)
    page_size = int(meta.get("maxRecordCount") or 1000)
    page_size = max(50, min(page_size, 1000))
    order = order_field or meta.get("objectIdField")
    features: list[dict] = []
    seen: set[str] = set()
    offset = 0
    # A geometry response can end a page early without exceededTransferLimit.
    # Keep going until the page repeats or the expected count is in hand.
    while offset <= 120000:
        params = {
            "where": where,
            "outFields": ",".join(out_fields) if out_fields else "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "resultRecordCount": str(page_size),
            "f": "json",
        }
        if order:
            params["orderByFields"] = str(order)
        if offset:
            params["resultOffset"] = str(offset)
        data = seed.fetch_json(url, params, timeout=180, retries=3)
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:240])
        batch = data.get("features") or []
        fresh = 0
        for item in batch:
            attrs = item.get("attributes") or {}
            marker = str(attrs.get(str(order)) if order else "") or json.dumps(attrs, sort_keys=True, default=str)[:180]
            if marker in seen:
                continue
            seen.add(marker)
            features.append(item)
            fresh += 1
        log(f"    paged {len(features)}")
        if not batch or fresh == 0:
            break
        done = expected and len(features) >= expected
        short = len(batch) < page_size and not data.get("exceededTransferLimit")
        if done or (short and (not expected or len(features) >= int(expected * 0.98))):
            break
        offset += len(batch)
    return features


def pull_raw(
    url: str,
    where: str,
    out_fields: list[str],
    fips: str,
    order_field: str | None,
    expected: int | None = None,
) -> list[dict]:
    if fips in FORCE_PAGE or fips in ORDER_BY_PARCEL:
        return fetch_paged(url, where, out_fields, order_field, expected)
    try:
        ids = seed.fetch_object_ids(url, where)
    except Exception as exc:  # noqa: BLE001
        log(f"    object ids failed ({exc}); paging")
        return fetch_paged(url, where, out_fields, order_field)
    if not ids:
        return fetch_paged(url, where, out_fields, order_field, expected)
    return seed.fetch_by_ids(url, ids, out_fields, batch=80)


def page_attributes(url: str, where: str, out_fields: list[str]) -> list[dict]:
    meta = fast_json(service_base(url), {"f": "json"}, timeout=40)
    oid = str(meta.get("objectIdField") or "OBJECTID")
    page_size = max(50, min(int(meta.get("maxRecordCount") or 1000), 2000))
    rows: list[dict] = []
    offset = 0
    while offset < 80000:
        params = {
            "where": where,
            "outFields": ",".join(out_fields),
            "returnGeometry": "false",
            "resultRecordCount": str(page_size),
            "orderByFields": oid,
            "f": "json",
        }
        if offset:
            params["resultOffset"] = str(offset)
        data = seed.fetch_json(url, params, timeout=90, retries=2)
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:240])
        batch = data.get("features") or []
        if not batch:
            break
        rows.extend(item.get("attributes") or {} for item in batch)
        if len(batch) < page_size and not data.get("exceededTransferLimit"):
            break
        offset += len(batch)
    return rows


def join_onemap(features: list[dict], fips: str, pass2: dict) -> str | None:
    """Copy tax or sale attributes from a pass-2 fallback layer. Never requests a PA page."""
    jobs: list[dict] = []
    fallback = pass2.get("taxFallback")
    if isinstance(fallback, dict) and fallback.get("restUrl") and fallback.get("fields"):
        jobs.append(
            {
                "url": query_url(str(fallback["restUrl"])),
                "where": str(fallback.get("where") or f"cntyfips='{fips[2:]}'"),
                "fields": [str(item) for item in fallback["fields"]],
                "kind": "tax",
            }
        )
    note = str(pass2.get("saleNote") or "")
    if not pass2.get("dateFields") and "onemap" in note.lower() and "saledate" in note.lower():
        jobs.append(
            {
                "url": NC_ONEMAP,
                "where": f"cntyfips='{fips[2:]}' AND saledatetx IS NOT NULL",
                "fields": ["saledatetx"],
                "kind": "sale",
            }
        )
    if not jobs:
        return None
    notes = []
    for job in jobs:
        fields = ["parno", "altparno", *job["fields"]]
        try:
            rows = page_attributes(job["url"], job["where"], fields)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Pass 2 {job['kind']} join did not answer ({exc}).")
            continue
        index: dict[str, dict] = {}
        for row in rows:
            for key in ("parno", "altparno"):
                text = integral_text(row.get(key))
                if text and text not in index:
                    index[text] = row
        matched = 0
        for feature in features:
            row = index.get(feature["properties"]["parcelId"])
            if not row:
                continue
            matched += 1
            if job["kind"] == "tax":
                tax = feature["properties"]["tax"]
                for name in job["fields"]:
                    label = guess_tax_label(name)
                    parsed = money(row.get(name))
                    if not label or parsed is None:
                        continue
                    slot = {
                        "tax.marketValue": "marketValue",
                        "tax.assessedValue": "assessedValue",
                        "tax.taxableValue": "taxableValue",
                        "tax.landValue": "marketValue",
                        "tax.improvementValue": "assessedValue",
                    }.get(label)
                    # Land and improvement stay in market/assessed only when those are empty.
                    if name.lower().startswith("par") or "market" in name.lower() or name.lower() in {"parval"}:
                        if tax.get("marketValue") is None:
                            tax["marketValue"] = parsed
                    elif "land" in name.lower():
                        if tax.get("marketValue") is None:
                            tax["marketValue"] = parsed
                    elif any(token in name.lower() for token in ("improv", "bldg", "build")):
                        if tax.get("assessedValue") is None:
                            tax["assessedValue"] = parsed
                    elif slot and tax.get(slot) is None:
                        tax[slot] = parsed
            else:
                sold = parse_sale_date(row.get("saledatetx"))
                if sold and not feature["properties"]["lastSale"].get("date"):
                    feature["properties"]["lastSale"]["date"] = sold
                    clear_future_sale(feature["properties"])
        notes.append(f"Pass 2 {job['kind']} join matched {matched} of {len(features)} parcel ids.")
    return " ".join(notes) if notes else None


def ring_centroid(geometry: dict) -> tuple[float, float] | None:
    if geometry.get("type") == "Polygon":
        ring = geometry["coordinates"][0]
    elif geometry.get("type") == "MultiPolygon":
        ring = max(geometry["coordinates"], key=lambda part: len(part[0]))[0]
    else:
        return None
    if not ring:
        return None
    return sum(point[0] for point in ring) / len(ring), sum(point[1] for point in ring) / len(ring)


def county_centers() -> dict[str, tuple[float, float]]:
    global CENTERS
    with CENTER_LOCK:
        if CENTERS is not None:
            return CENTERS
        data = json.loads(CENSUS_COUNTIES.read_text())
        found: dict[str, tuple[float, float]] = {}
        for feature in data.get("features") or []:
            geoid = str((feature.get("properties") or {}).get("GEOID") or "")
            if not geoid.startswith("37"):
                continue
            center = ring_centroid(feature.get("geometry") or {})
            if center:
                found[geoid] = center
        CENTERS = found
        return found


def haversine_km(left: tuple[float, float], right: tuple[float, float]) -> float:
    lon1, lat1 = math.radians(left[0]), math.radians(left[1])
    lon2, lat2 = math.radians(right[0]), math.radians(right[1])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    step = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(min(1.0, math.sqrt(step)))


def nearest_shelf(fips: str) -> str:
    center = county_centers().get(fips)
    if not center:
        raise RuntimeError(f"{fips} has no Census county shape")
    return min(NC_SHELVES, key=lambda name: haversine_km(center, NC_SHELVES[name]))


def markets_for(catalog: dict, fips: str) -> list[str]:
    found: list[str] = []
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips and market["id"] not in found:
                found.append(market["id"])
    return found


def planned_markets(catalog: dict, fips: str) -> list[str]:
    existing = markets_for(catalog, fips)
    if existing:
        return existing
    shelf = nearest_shelf(fips)
    if shelf not in {market["id"] for market in catalog["markets"]}:
        raise RuntimeError(f"{fips} nearest shelf {shelf} is not in the catalog")
    return [shelf]


def commit_markets(catalog: dict, fips: str, name: str, markets: list[str]) -> None:
    if markets_for(catalog, fips):
        return
    by_market = {market["id"]: market for market in catalog["markets"]}
    for market_id in markets:
        by_market[market_id]["counties"].append({"name": name, "state": "North Carolina", "fips": fips})


def gap_notes(
    table: dict,
    layer: dict,
    pass2: dict,
    source_count: int,
    kept: int,
    join_note: str | None,
) -> list[str]:
    notes = [
        f"Parcels are {layer.get('name') or 'the pass-1 parcel layer'} ({layer.get('restUrl')}). Acreage is 5.0–150.0 inclusive. No Opportunity Zone status, school grade, or base flood elevation is stored.",
    ]
    if source_count and kept < source_count:
        notes.append(
            f"Source query returned {source_count} rows; {kept} stayed in the 5.0–150.0 acre band after the parcel-id and geometry checks."
        )
    if pass2["present"]:
        tax = pass2["taxStatus"] or "not stated"
        sale = pass2["saleStatus"] or "not stated"
        stations = pass2.get("aadtStations")
        station_text = f" Pass 2 counted {stations} NCDOT 2022 AADT stations." if stations else ""
        notes.append(
            f"Pass 2 enrichment is from {pass2['source']} (tax {tax}, sale {sale}).{station_text} NCDOT AADT stays the query-time statewide join."
        )
        if pass2["taxStatus"] in {"gap", "scrubbed"}:
            notes.append(f"Pass 2 tax status is {pass2['taxStatus']}. Scrubbed or missing tax values were not copied off the parcel layer.")
        if pass2["saleStatus"] in {"gap", "partial"} and pass2.get("saleNote"):
            notes.append(f"Pass 2 sale: {pass2['saleNote'][:280]}")
    else:
        notes.append(
            "Pass 2 enrichment was not on the card or in rural-oz-pass2 results. Tax, sale, and owner are the parcel-layer attributes only. NCDOT AADT stays the query-time statewide join."
        )
    if join_note:
        notes.append(join_note)
    if table.get("fips") == "37003":
        notes.append(
            "Alexander pages with orderByFields because the MapServer has no object id. returnCountOnly repeats PROPERTY 99999 rows, so that raw count is higher than the distinct parcel ids that page."
        )
    if table.get("fips") == "37009":
        notes.append("Ashe pages with resultRecordCount. An unpaged geometry query on this MapServer stops at 500.")
    if table.get("notes"):
        text = seed.clean(table["notes"])
        if text and not BANNED_FIELD.search(text):
            notes.append(text[:360])
    notes.append("Property-appraiser links are stored from the card or pass-2 pattern and were not requested. Owner phone and email are not ingested.")
    unique: list[str] = []
    for note in notes:
        if note and note not in unique:
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
    expected: int,
) -> None:
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{county['fips']} emitted a parcel outside 5–150 acres")
    floor = max(50, int(expected * 0.7)) if expected else 50
    if len(features) < floor:
        raise RuntimeError(f"{county['fips']} kept {len(features)} of expected {expected}")
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
            "paLinkVerified": bool(links.get("verified")),
            "appraiserSearchUrl": links.get("template"),
            "gisViewerUrl": links.get("gis"),
            "minAcres": 5.0,
            "maxAcres": 150.0,
        },
    )
    log(f"  kept {len(features)} tiles {tiles}")


def pull_features(
    url: str,
    where: str,
    out_fields: list[str],
    card: dict,
    name: str,
    field_map: dict[str, str],
    markets: list[str],
    source: str,
    acres_scale: float,
    use_geometry_acres: bool,
    acre_field: str | None,
    links: dict,
    order_field: str | None,
    expected: int | None = None,
) -> tuple[list[dict], int]:
    raw = pull_raw(url, where, out_fields, str(card.get("fips") or "").zfill(5), order_field, expected)
    features: list[dict] = []
    dropped = 0
    for item in raw:
        feature = feature_from(
            item.get("attributes") or {},
            item.get("geometry"),
            card=card,
            name=name,
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
    return dedupe(features), dropped


def download_county(item: dict, markets: list[str], refresh: bool) -> dict:
    card = item["card"]
    fips = item["fips"]
    name = item["name"]
    layer = item["layer"]
    url = item["queryUrl"]
    pass2 = item["pass2"]
    source = f"nc-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}-parcels-{fips}"
    county = {"name": name, "state": "North Carolina", "fips": fips}
    links = card_links(card, pass2)
    cache_path = CACHE_DIR / f"{fips}.json"
    backup_county(fips)
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features and (not item["expected"] or len(features) >= int(item["expected"] * 0.7)):
            log(f"Pulling {name} {fips} cache {len(features)}")
            for feature in features:
                feature["properties"]["marketIds"] = markets
                feature["properties"]["state"] = "North Carolina"
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
                expected=int(item["expected"] or 0),
            )
            return {
                "fips": fips,
                "name": name,
                "featureCount": len(features),
                "queryUrl": cached.get("queryUrl") or url,
                "markets": markets,
                "source": source,
                "pass2": pass2["source"],
            }
    log(f"Pulling {name} {fips} {url}")
    available = set(item["fields"])
    field_map = attribute_field_map(layer, pass2, available, item["idField"])
    where = item["where"]
    acre_field = item.get("acreField")
    scale = float(item.get("acresScale") or 1)
    geometry_acres = bool(item.get("geometryAcres"))
    out_fields = simple_sources(field_map, available)
    if acre_field and acre_field not in out_fields:
        out_fields.append(acre_field)
    order_field = item["idField"] if fips in ORDER_BY_PARCEL else None
    if order_field and order_field not in available:
        order_field = next(iter(available))
    features, dropped = pull_features(
        url,
        where,
        out_fields,
        card,
        name,
        field_map,
        markets,
        source,
        scale,
        geometry_acres,
        None if geometry_acres else acre_field,
        links,
        order_field or item["idField"],
        int(item.get("expected") or item.get("probeCount") or 0) or None,
    )
    join_note = join_onemap(features, fips, pass2)
    gaps = gap_notes(item, layer, pass2, int(item.get("probeCount") or len(features)), len(features), join_note)
    write_county(
        county,
        markets,
        features,
        source=source,
        url=url,
        gaps=gaps,
        source_count=int(item.get("probeCount") or len(features)),
        dropped=dropped,
        links=links,
        expected=int(item["expected"] or 0),
    )
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "sourceCount": item.get("probeCount"),
                    "dropped": dropped,
                    "queryUrl": url,
                    "gaps": gaps,
                    "features": features,
                },
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
        "pass2": pass2["source"],
        "sourceCount": item.get("probeCount"),
    }


def classify(cards: dict[str, dict], reload: set[str] | None = None) -> tuple[list[dict], list[dict]]:
    eligible: list[dict] = []
    skipped: list[dict] = []
    reload = reload or set()
    for row in table_rows():
        fips = row["fips"]
        name = row["name"]
        if row["status"] not in {"verified", "fixed"}:
            skipped.append({"fips": fips, "name": name, "reason": f"status {row['status']}"})
            continue
        card = cards.get(fips)
        if not card:
            skipped.append({"fips": fips, "name": name, "reason": "no county card"})
            continue
        current = existing_row(fips)
        if fully_loaded(current) and fips not in reload and name.lower() not in reload:
            skipped.append(
                {
                    "fips": fips,
                    "name": name,
                    "reason": f"already a complete 5.0–150.0 acre extract ({int((current or {}).get('featureCount') or 0)} parcels)",
                    "queryUrl": (current or {}).get("queryUrl"),
                }
            )
            continue
        if PAID_VENDOR.search(row["url"]):
            skipped.append({"fips": fips, "name": name, "reason": "paid vendor endpoint"})
            continue
        eligible.append({**row, "card": card})
    return eligible, skipped


def probe_one(item: dict) -> dict:
    fips = item["fips"]
    try:
        url, meta = open_service(query_url(item["url"]))
        available = set(field_names(meta))
        acre_name, cast_hint, extra = acre_spec(item["acreageRaw"])
        layer = choose_layer(item["card"], url, acre_name)
        where, scale, geometry, count, field = resolve_acres(
            url, acre_name, cast_hint, extra, available, int(item["expected"] or 0)
        )
        lookup = {name.lower(): name for name in available}
        live_id = item["idField"] if item["idField"] in available else lookup.get(item["idField"].lower(), item["idField"])
        pass2 = load_pass2(item["card"], fips)
        log(f"SELECT {item['name']} {fips} rows {count} pass2 {pass2['source']}")
        return {
            **item,
            "idField": live_id,
            "ok": True,
            "queryUrl": url,
            "where": where,
            "probeCount": count,
            "geometryAcres": geometry,
            "acresScale": scale,
            "acreField": field,
            "fields": sorted(available),
            "layer": layer,
            "pass2": pass2,
            "metaOrder": meta.get("objectIdField"),
        }
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
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.indexes_only:
        catalog = json.loads(CATALOG_PATH.read_text())
        seed.rebuild_indexes(catalog)
        return
    cards = load_cards()
    reload = {item.lower() for item in args.county} if args.refresh and args.county else set()
    eligible, skipped = classify(cards, reload)
    log(f"Eligible before probe: {len(eligible)}")
    # Probe in table order and stop once there are enough reachable counties
    # to fill the batch, plus a few spares in case a download fails.
    spare = 0 if args.county else 6
    probe_goal = len(reload) or 1 if args.county else TARGET + spare
    reachable: list[dict] = []
    cursor = 0
    while cursor < len(eligible) and len(reachable) < probe_goal:
        window = eligible[cursor : cursor + max(1, args.workers)]
        cursor += len(window)
        with ThreadPoolExecutor(max_workers=max(1, len(window))) as pool:
            futures = {pool.submit(probe_one, item): item for item in window}
            done = []
            for future in as_completed(futures):
                done.append(future.result())
        by_fips = {item["fips"]: item for item in done}
        for item in window:
            probed = by_fips[item["fips"]]
            if probed["ok"]:
                reachable.append(probed)
            else:
                skipped.append(
                    {
                        "fips": probed["fips"],
                        "name": probed["name"],
                        "reason": probed["reason"],
                        "queryUrl": probed.get("url"),
                    }
                )
    summary = {
        "reachable": [
            {
                "fips": item["fips"],
                "name": item["name"],
                "queryUrl": item["queryUrl"],
                "probeCount": item.get("probeCount"),
                "pass2": (item.get("pass2") or {}).get("source"),
                "where": item.get("where"),
            }
            for item in reachable
        ],
        "skipped": skipped,
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
        item["markets"] = planned_markets(catalog, item["fips"])
        log(f"SHELF {item['name']} {item['fips']} -> {', '.join(item['markets'])}")
    kept: list[dict] = []
    index = 0
    goal = len(queue) if selected_filter else TARGET
    while len(kept) < goal and index < len(queue):
        batch = queue[index : index + max(1, args.workers)]
        index += len(batch)
        results: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=max(1, len(batch))) as pool:
            futures = {pool.submit(download_county, item, item["markets"], args.refresh): item for item in batch}
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
                skipped.append(
                    {
                        "fips": item["fips"],
                        "name": item["name"],
                        "reason": f"download failed: {result['error']}",
                        "queryUrl": item.get("queryUrl"),
                    }
                )
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
    report_path = CARDS / "batch1-result.json"
    if args.county and report_path.exists():
        previous = json.loads(report_path.read_text())
        by_fips = {item["fips"]: item for item in previous.get("pulled") or []}
        order = [item["fips"] for item in previous.get("pulled") or []]
        for item in kept:
            if item["fips"] not in by_fips:
                order.append(item["fips"])
            by_fips[item["fips"]] = item
        report = {"pulled": [by_fips[fips] for fips in order], "skipped": previous.get("skipped") or skipped}
    else:
        report = {"pulled": kept, "skipped": skipped}
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if not args.skip_index:
        seed.rebuild_indexes(catalog)
    log("Done " + json.dumps(kept, indent=2))


if __name__ == "__main__":
    sys.exit(main())
