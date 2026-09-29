#!/usr/bin/env python3
"""5.0–150.0 acre parcels for South Carolina rural OZ batch 2.

Reuses the batch 1 loader, shelf assignment, and tile writer. Walks the interim
CSV after Jasper, skips counties that already have a complete 5.0–150.0 acre
extract, and retries Anderson. If fewer than 20 rural-OZ rows remain, remaining
South Carolina county cards with a usable public parcel layer fill the batch.

Does not add a market shelf, switch markets, or store an Opportunity Zone
status, a school grade, or a base flood elevation. Household income stays the
ACS B19013_001E join. Owner phone and email are not ingested. Sale dates after
the pull date are cleared. A confidential-owner flag on a record suppresses
owner and mailing fields.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import certifi

import sc_rural_oz_batch1_parcels as b1
import seed_market_parcels as seed

ROOT = seed.ROOT
CARDS = b1.CARDS
CACHE_DIR = Path("/tmp/dls-sc-rural-oz-batch2")
TARGET = 20
JASPER_FIPS = "45053"
ANDERSON_FIPS = "45007"
PRINT_LOCK = threading.Lock()
HTML_TAG = re.compile(r"<[^>]+>", re.I)
CONFIDENTIAL_KEY = re.compile(r"confidential|redact", re.I)
CONFIDENTIAL_YES = {"yes", "y", "true", "1", "confidential"}

# County-specific CAMA layers, same idea as the batch 1 Kershaw and Edgefield hints.
b1.LAYER_URL_HINT.update(
    {
        "45065": "Edgefield_McCormick_Greenwood_Web_Map_WFL1/FeatureServer/7",
        "45081": "ParcelViewers/PublicWebsite_Pro/MapServer/4",
        "45089": "Georgetown_Williamsburg_Web_Map_WFL1/FeatureServer/4",
    }
)

_ORIG_FETCH = seed.fetch_json
_ORIG_TOKENS = b1.field_tokens
_ORIG_BUCKET = b1.target_bucket
_ORIG_COLLECT = b1.collect_mapped
_ORIG_FEATURE = b1.feature_from
_ORIG_RESOLVE = b1.resolve_acres
_ORIG_PARSE = b1.parse_sale_date
_ANDERSON_CTX: ssl.SSLContext | None = None


def log(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def anderson_ssl_context() -> ssl.SSLContext:
    """Trust store plus the DigiCert intermediate Anderson's server omits."""
    global _ANDERSON_CTX
    if _ANDERSON_CTX is not None:
        return _ANDERSON_CTX
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pem_path = CACHE_DIR / "digicert-g2.pem"
    if not pem_path.exists():
        req = urllib.request.Request(
            "http://cacerts.digicert.com/DigiCertGlobalG2TLSRSASHA2562020CA1-1.crt",
            headers={"User-Agent": "darryl-land-search/market-parcels"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            blob = resp.read()
        if blob.startswith(b"-----BEGIN"):
            pem_path.write_bytes(blob)
        else:
            from cryptography import x509
            from cryptography.hazmat.primitives import serialization

            cert = x509.load_der_x509_certificate(blob)
            pem_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    ctx = ssl.create_default_context(cafile=certifi.where())
    ctx.load_verify_locations(cafile=str(pem_path))
    _ANDERSON_CTX = ctx
    return ctx


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if "andersoncountysc.org" not in url:
        return _ORIG_FETCH(url, params, timeout=timeout, retries=retries)
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    ctx = anderson_ssl_context()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/market-parcels"})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:160]}: {last}")


def field_tokens(key: str) -> list[str]:
    chunks = key.split("+") if "+" in key else [key]
    tokens: list[str] = []
    for chunk in chunks:
        chunk = re.sub(r"\(.*$", "", chunk).strip()
        if "." in chunk and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", chunk):
            if chunk not in tokens:
                tokens.append(chunk)
            continue
        match = b1.FIELD_TOKEN.search(chunk)
        if match and match.group(0) not in tokens:
            tokens.append(match.group(0))
    return tokens


def target_bucket(label: str) -> str | None:
    text = label.split("(")[0].strip()
    extra = {
        "mailingAddress": "mail1",
        "mailingAddress2": "mail2",
        "mailingCity": "mailCity",
        "mailingState": "mailState",
        "mailingZip": "mailZip",
        "mailingCityState": "mailCityState",
        "mailingCityStateZip": "mailCityStateZip",
        "acreageGis": "acresAlt",
        "acreageDeed": "acresAlt",
        "gisAcres": "acresAlt",
        "lastSale.year": "saleYear",
        "lastSale.month": "saleMonth",
        "lastSale.day": "saleDay",
    }
    return extra.get(text) or _ORIG_BUCKET(label)


def _parsed_acres(value) -> float | None:
    if isinstance(value, str):
        value = value.replace(",", "").replace("$", "").strip()
    parsed = seed.num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def collect_mapped(attrs: dict, field_map: dict[str, str]) -> dict:
    buckets = _ORIG_COLLECT(attrs, field_map)
    acres = buckets.get("acres")
    if isinstance(acres, (int, float)) and not seed.in_band(float(acres)):
        buckets.pop("acres", None)
    if not (isinstance(buckets.get("acres"), (int, float)) and seed.in_band(float(buckets["acres"]))):
        for key, label in field_map.items():
            if target_bucket(label) not in {"acres", "acresAlt"}:
                continue
            for name in field_tokens(key):
                parsed = _parsed_acres(attrs.get(name))
                if parsed is not None and seed.in_band(parsed):
                    buckets["acres"] = parsed
                    break
            if isinstance(buckets.get("acres"), (int, float)) and seed.in_band(float(buckets["acres"])):
                break
    if not buckets.get("saleDate"):
        year = seed.num(attrs.get("SALE_YEAR"))
        month = seed.num(attrs.get("SALE_MONTH"))
        day = seed.num(attrs.get("SALE_DAY"))
        if year and month and day and 1900 <= int(year) <= 2100 and 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
            buckets["saleDate"] = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        elif year and 1900 <= int(year) <= 2100 and not month and not day:
            buckets["saleDate"] = f"{int(year):04d}-01-01"
    return buckets


def parse_sale_date(value):
    """US dates from SC CAMA text, plus the batch 1 parser."""
    if value is None or value == "":
        return None
    text = str(value).strip()
    match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if match:
        month, day, year = (int(part) for part in match.groups())
        if year <= 1900 or year > 2100 or not (1 <= month <= 12 and 1 <= day <= 31):
            return None
        return f"{year:04d}-{month:02d}-{day:02d}"
    parsed = _ORIG_PARSE(value)
    if parsed and parsed <= "1900-12-31":
        return None
    return parsed


def strip_html(value):
    if not isinstance(value, str) or "<" not in value:
        return value
    text = HTML_TAG.sub(" ", value)
    return re.sub(r"\s+", " ", text).strip() or None


def confidential_owner(attrs: dict) -> bool:
    for key, value in attrs.items():
        if not CONFIDENTIAL_KEY.search(str(key)):
            continue
        if str(value).strip().lower() in CONFIDENTIAL_YES:
            return True
    return False


def feature_from(attrs, geom, **kwargs):
    feature = _ORIG_FEATURE(attrs, geom, **kwargs)
    if not feature:
        return None
    props = feature["properties"]
    for key in ("ownerName", "ownerName2", "situsAddress", "situsCity"):
        if isinstance(props.get(key), str):
            props[key] = strip_html(props[key])
    mail = props.get("mailingAddress") or {}
    for key, value in list(mail.items()):
        if isinstance(value, str):
            cleaned = strip_html(value)
            if key == "city" and isinstance(cleaned, str):
                cleaned = cleaned.strip(" ,") or None
            mail[key] = cleaned
    if confidential_owner(attrs):
        props["ownerName"] = None
        props["ownerName2"] = None
        props["mailingAddress"] = {key: None for key in ("line1", "line2", "city", "state", "zip")}
    card = kwargs.get("card") or {}
    if str(card.get("fips") or "").zfill(5) == ANDERSON_FIPS:
        lookup = seed.clean(attrs.get("ACPASS_LOOKUP"))
        if lookup:
            props["appraiserUrl"] = f"https://acpass.andersoncountysc.org/asrdetails.cgi?mapno={lookup}"
    b1.clear_future_sale(props)
    b1.scrub(props)
    return feature


def resolve_acres(url: str, where: str, acre_field: str | None, available: set[str]):
    where_out, scale, geometry_acres, count = _ORIG_RESOLVE(url, where, acre_field, available)
    base = where or "1=1"
    if where_out == base and count > 6000:
        for shape in ("SHAPE.STArea()", "Shape.STArea()"):
            area = f"({base}) AND {shape}>={int(b1.SQFT_MIN)} AND {shape}<={int(b1.SQFT_MAX)}"
            area_count = b1.try_count(url, area)
            if area_count > 0:
                return area, scale, False, area_count
    return where_out, scale, geometry_acres, count


def install_patches() -> None:
    seed.fetch_json = fetch_json
    b1.field_tokens = field_tokens
    b1.target_bucket = target_bucket
    b1.collect_mapped = collect_mapped
    b1.feature_from = feature_from
    b1.resolve_acres = resolve_acres
    b1.parse_sale_date = parse_sale_date


def consider(row: dict, cards: dict[str, dict], chosen: list[dict], skipped: list[dict]) -> None:
    fips = str(row["county_fips"]).zfill(5)
    name = row.get("county") or fips
    card = cards.get(fips)
    if not card or card.get("level") != "county":
        skipped.append({"fips": fips, "name": name, "reason": "no county card"})
        return
    current = b1.existing_row(fips)
    try:
        layer = b1.choose_layer(card)
        url = b1.query_url(str(layer["restUrl"]))
    except Exception as exc:  # noqa: BLE001
        skipped.append({"fips": fips, "name": name, "reason": f"card layer: {exc}"})
        log(f"SKIP {name} {fips}: {exc}")
        return
    if b1.fully_loaded(current):
        same = b1.norm_source((current or {}).get("queryUrl")) == b1.norm_source(url)
        why = "already loaded from the same source" if same else "already a complete 5.0–150.0 acre extract"
        skipped.append({"fips": fips, "name": name, "reason": why, "queryUrl": (current or {}).get("queryUrl")})
        log(f"SKIP {name} {fips}: {why}")
        return
    if current and b1.norm_source(current.get("queryUrl")) == b1.norm_source(url) and int(current.get("featureCount") or 0) > 0:
        skipped.append({"fips": fips, "name": name, "reason": "already loaded from the same source"})
        return
    try:
        available = set(b1.field_names(url))
        acre_field = layer.get("acreageField") if layer.get("acreageField") in available else None
        b1.resolve_acres(url, layer.get("where") or "1=1", acre_field, available)
    except Exception as exc:  # noqa: BLE001
        skipped.append({"fips": fips, "name": name, "reason": f"endpoint unreachable: {exc}", "queryUrl": url})
        log(f"SKIP {name} {fips}: {exc}")
        return
    chosen.append({"fips": fips, "name": name, "card": card, "queryUrl": url})
    log(f"SELECT {name} {fips}")


def select_counties(cards: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    chosen: list[dict] = []
    skipped: list[dict] = []
    rows = b1.csv_order()
    by_fips = {str(row["county_fips"]).zfill(5): row for row in rows}
    seen: set[str] = set()
    if ANDERSON_FIPS in by_fips and len(chosen) < TARGET:
        consider(by_fips[ANDERSON_FIPS], cards, chosen, skipped)
        seen.add(ANDERSON_FIPS)
    after = False
    for row in rows:
        fips = str(row["county_fips"]).zfill(5)
        if fips == JASPER_FIPS:
            after = True
            continue
        if not after or fips in seen:
            continue
        seen.add(fips)
        if len(chosen) >= TARGET:
            continue
        consider(row, cards, chosen, skipped)
    if len(chosen) < TARGET:
        for fips in sorted(cards):
            if len(chosen) >= TARGET:
                break
            if fips in seen:
                continue
            current = b1.existing_row(fips)
            if b1.fully_loaded(current):
                continue
            seen.add(fips)
            name = b1.short_name(cards[fips], fips)
            consider({"county_fips": fips, "county": name}, cards, chosen, skipped)
    return chosen, skipped


def attach_anderson_owners(features: list[dict]) -> int:
    """Owner names from the RFA statewide layer named on the Anderson card."""
    url = "https://services9.arcgis.com/RvqSyw3diI7dTKo5/arcgis/rest/services/Lexington_Richland_Web_Map_WFL1/FeatureServer/18/query"
    pending = [feature for feature in features if not feature["properties"].get("ownerName")]
    found = 0
    ids = [feature["properties"]["parcelId"] for feature in pending]
    by_id = {feature["properties"]["parcelId"]: feature for feature in pending}
    for start in range(0, len(ids), 40):
        chunk = ids[start : start + 40]
        quoted = ",".join("'" + item.replace("'", "''") + "'" for item in chunk)
        try:
            data = seed.fetch_json(
                url,
                {
                    "where": f"County='Anderson County' AND T_Map_Number IN ({quoted})",
                    "outFields": "T_Map_Number,Ownership",
                    "returnGeometry": "false",
                    "f": "json",
                },
                timeout=90,
            )
        except Exception:
            continue
        for item in data.get("features") or []:
            attrs = item.get("attributes") or {}
            parcel_id = seed.clean(attrs.get("T_Map_Number"))
            owner = seed.clean(attrs.get("Ownership"))
            feature = by_id.get(parcel_id or "")
            if feature and owner:
                feature["properties"]["ownerName"] = owner
                found += 1
    return found


def download_one(catalog: dict, card: dict, refresh: bool) -> dict:
    fips = str(card["fips"]).zfill(5)
    b1.CACHE_DIR = CACHE_DIR
    result = b1.download_county(catalog, card, refresh)
    if fips == ANDERSON_FIPS:
        cache_path = CACHE_DIR / f"{fips}.json"
        if cache_path.exists():
            cached = json.loads(cache_path.read_text())
            features = cached.get("features") or []
            joined = attach_anderson_owners(features)
            log(f"  Anderson RFA owners joined {joined}")
            if joined:
                markets = b1.markets_for(catalog, fips)
                for feature in features:
                    feature["properties"]["marketIds"] = markets
                    b1.clear_future_sale(feature["properties"])
                name = b1.short_name(card, fips)
                county = b1.county_dict(catalog, fips, name)
                b1.write_county(
                    county,
                    markets,
                    features,
                    source=f"sc-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}-parcels-{fips}",
                    url=result["queryUrl"],
                    gaps=cached.get("gaps") or [],
                    source_count=int(cached.get("sourceCount") or len(features)),
                    dropped=int(cached.get("dropped") or 0),
                    links=b1.card_links(card),
                )
                cache_path.write_text(json.dumps(cached))
                result["featureCount"] = len(features)
                result["ownersJoined"] = joined
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    install_patches()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cards = b1.load_cards()
    chosen, skipped = select_counties(cards)
    summary = {
        "selected": [{"fips": item["fips"], "name": item["name"], "queryUrl": item["queryUrl"]} for item in chosen],
        "skipped": skipped,
    }
    log(json.dumps(summary, indent=2))
    if args.refresh and args.county:
        have = {item["fips"] for item in chosen}
        for token in args.county:
            fips = token.zfill(5) if token.isdigit() else None
            card = None
            if fips and fips in cards:
                card = cards[fips]
            else:
                for candidate in cards.values():
                    if b1.short_name(candidate, "").lower() == token.lower():
                        card = candidate
                        fips = str(candidate["fips"]).zfill(5)
                        break
            if not card or not fips or fips in have:
                continue
            layer = b1.choose_layer(card)
            url = b1.query_url(str(layer["restUrl"]))
            chosen.append({"fips": fips, "name": b1.short_name(card, fips), "card": card, "queryUrl": url})
            log(f"REFRESH {fips}")
    if args.probe_only:
        return
    if not chosen:
        raise SystemExit("No reachable counties")
    catalog = json.loads(seed.CATALOG_PATH.read_text())
    for item in chosen:
        b1.ensure_on_shelves(catalog, item["fips"], b1.short_name(item["card"], item["name"]), item["card"])
    selected = {item.lower() for item in args.county}
    work = [
        item
        for item in chosen
        if not selected or item["fips"] in selected or item["name"].lower() in selected
    ]
    pulled: list[dict] = []
    errors: list[str] = []
    lock = threading.Lock()

    def run(item: dict) -> None:
        try:
            result = download_one(catalog, item["card"], args.refresh)
            with lock:
                pulled.append(result)
        except Exception as exc:  # noqa: BLE001
            message = f"{item['fips']} {item['name']}: {exc}"
            log(f"FAILED {message}")
            with lock:
                errors.append(message)
                skipped.append({"fips": item["fips"], "name": item["name"], "reason": f"download failed: {exc}", "queryUrl": item["queryUrl"]})

    workers = max(1, args.workers)
    if workers == 1 or len(work) == 1:
        for item in work:
            run(item)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run, item) for item in work]
            for future in as_completed(futures):
                future.result()
    seed.CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    if not args.skip_index:
        seed.rebuild_indexes(catalog)
    report_path = CARDS / "batch2-result.json"
    if args.county and report_path.exists():
        previous = json.loads(report_path.read_text())
        by_fips = {item["fips"]: item for item in previous.get("pulled") or []}
        for item in pulled:
            by_fips[item["fips"]] = item
        report = {
            "pulled": list(by_fips.values()),
            "skipped": previous.get("skipped") or skipped,
            "errors": errors,
        }
    else:
        report = {"pulled": pulled, "skipped": skipped, "errors": errors}
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    log("Done " + json.dumps(pulled, indent=2))
    if errors:
        raise SystemExit("County downloads failed:\n" + "\n".join(errors))


if __name__ == "__main__":
    sys.exit(main())
