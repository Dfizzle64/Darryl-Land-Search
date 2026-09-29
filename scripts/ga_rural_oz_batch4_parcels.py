#!/usr/bin/env python3
"""5.0–150.0 acre parcels for Georgia rural Opportunity Zone batch 4.

Reuses the batch 1 loader. The queue is pass-2 orders 70 through 92 whose
pass-1 status is usable, plus a patient retry of Franklin (order 7) and
Habersham (order 10). Orders 26–69 belong to other batches and are not
requested. A county that already has a complete 5.0–150.0 acre extract is
not re-pulled. A layer that is not county-wide is rejected.

Schneider WFS hosts are queried with small pages and retries with backoff.
If the service still does not answer, that county is skipped.

Does not add a market shelf. Counties already on a shelf stay there. Others
go on the nearest existing Georgia shelf. No Opportunity Zone status, school
grade, or base flood elevation is stored. Household income stays the ACS
B19013_001E join. GDOT AADT stays off the parcel. Property-appraiser URLs
use each parcel id in the pass-2 template and are not requested. A sample
parcel id is never copied onto every parcel. Owner phone and email are not
ingested. A confidential-owner flag suppresses owner and mailing fields.
Sale dates after the pull date are cleared.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import ga_rural_oz_batch1_parcels as b1
import nc_rural_oz_batch1_parcels as nc
import seed_market_parcels as seed

BATCH_ORDERS = set(range(70, 93)) | {7, 10}
SCHNEIDER_HOST = "wfs.schneidercorp.com"
RESULT_PATH = b1.CARDS / "batch4-result.json"
b1.CACHE_DIR = Path("/tmp/dls-ga-rural-oz-batch4")
SALE_NOTES: dict[str, str] = {}
ID_PRIORITY = (
    "parcel_no",
    "parcelno",
    "parcel_id",
    "parcelid",
    "pin",
    "parcel_pin",
    "parcel_num",
    "parcelnum",
    "tax_number",
    "parcel_ful",
    "par_id",
    "parid",
    "name",
    "map_par",
)


def source_name(name: str, fips: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"ga-{slug}-parcels-{fips}"


def is_schneider(url: str | None) -> bool:
    return bool(url) and SCHNEIDER_HOST in url


_fetch_json = seed.fetch_json
_simple_sources = nc.simple_sources
_pull_raw = nc.pull_raw
_pull_features = b1.pull_features
_gap_notes = b1.gap_notes
_attribute_field_map = b1.attribute_field_map


def patient_fetch(url: str, params: dict | None = None, timeout: int = 70, retries: int = 3) -> dict:
    """Small-budget retries for wfs.schneidercorp.com. TLS verification stays on."""
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        if attempt:
            delay = min(45, 8 * (2 ** (attempt - 1)))
            b1.log(f"    schneider backoff {delay}s (attempt {attempt + 1})")
            time.sleep(delay)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/market-parcels"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
        error = data.get("error") if isinstance(data, dict) else None
        code = int(error.get("code") or 0) if isinstance(error, dict) else 0
        if code in {500, 503, 504}:
            last = RuntimeError(json.dumps(error)[:200])
            continue
        return data
    raise RuntimeError(f"Failed to fetch {url[:160]}: {last}")


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if is_schneider(url):
        return patient_fetch(url, params, timeout=max(70, min(timeout, 90)), retries=max(3, min(retries, 4)))
    return _fetch_json(url, params, timeout=timeout, retries=retries)


def simple_sources(field_map: dict[str, str], available: set[str]) -> list[str]:
    fields = _simple_sources(field_map, available)
    for name in sorted(available):
        if name in fields or not b1.CONFIDENTIAL_KEY.search(name):
            continue
        if re.search(r"phone|e-?mail", name, re.I):
            continue
        fields.append(name)
    return fields


def patient_page(
    url: str,
    where: str,
    out_fields: list[str],
    order_field: str | None,
    expected: int | None,
) -> list[dict]:
    meta = fetch_json(nc.service_base(url), {"f": "json"}, timeout=60, retries=3)
    page_size = 40
    order = order_field or meta.get("objectIdField") or "OBJECTID"
    features: list[dict] = []
    seen: set[str] = set()
    offset = 0
    while offset <= 80000:
        params = {
            "where": where,
            "outFields": ",".join(out_fields) if out_fields else "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "resultRecordCount": str(page_size),
            "orderByFields": str(order),
            "f": "json",
        }
        if offset:
            params["resultOffset"] = str(offset)
        data = fetch_json(url, params, timeout=75, retries=3)
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
        b1.log(f"    schneider page {len(features)}")
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
    if is_schneider(url):
        return patient_page(url, where, out_fields, order_field, expected)
    return _pull_raw(url, where, out_fields, fips, order_field, expected)


def discover_id(names: list[str]) -> str | None:
    compact = {re.sub(r"[^a-z0-9]", "", name.lower()): name for name in names}
    for key in ID_PRIORITY:
        if key in compact:
            return compact[key]
    for name in names:
        token = re.sub(r"[^a-z0-9]", "", name.lower())
        if token in {"objectid", "objectid12", "shape", "shapearea", "shapelength", "starea", "stlength"}:
            continue
        if "parcel" in token or token in {"pin", "apn"}:
            return name
    return None


def declared_id(item: dict, prior: dict) -> str:
    text = str(prior.get("parcelIdField") or "").strip()
    if text:
        return text
    layer = item["layer"]
    for key, label in (layer.get("fieldMap") or {}).items():
        if str(label).split("(")[0].strip() == "parcelId":
            return str(key)
    return ""


def external_sale_layer(card: dict, parcel_url: str) -> dict | None:
    block = card.get("pass2_2026-09-28") if isinstance(card.get("pass2_2026-09-28"), dict) else {}
    sales = block.get("sales") if isinstance(block.get("sales"), dict) else {}
    if not str(sales.get("status") or "").lower().startswith("rest"):
        return None
    parcel = nc.norm_source(parcel_url)
    for layer in card.get("layers") or []:
        if not isinstance(layer, dict) or layer.get("role") != "sales":
            continue
        url = layer.get("restUrl")
        if not isinstance(url, str) or not url.startswith("http"):
            continue
        coverage = str(layer.get("coverage") or "").lower()
        if coverage and coverage != "county-wide":
            continue
        if nc.norm_source(url) == parcel:
            continue
        return layer
    return None


def page_attributes_offset(url: str, out_fields: list[str]) -> list[dict]:
    """Offset paging for a MapServer that rejects orderByFields."""
    rows: list[dict] = []
    offset = 0
    page_size = 1000
    while offset < 80000:
        params = {
            "where": "1=1",
            "outFields": ",".join(out_fields),
            "returnGeometry": "false",
            "resultRecordCount": str(page_size),
            "f": "json",
        }
        if offset:
            params["resultOffset"] = str(offset)
        data = seed.fetch_json(url, params, timeout=90, retries=3)
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


def join_external_sales(features: list[dict], card: dict, parcel_url: str) -> str | None:
    layer = external_sale_layer(card, parcel_url)
    if not layer:
        return None
    field_map = layer.get("fieldMap") if isinstance(layer.get("fieldMap"), dict) else {}
    id_key = None
    slots: dict[str, str] = {}
    for key, label in field_map.items():
        if not isinstance(key, str) or not isinstance(label, str):
            continue
        text = label.split("(")[0].strip()
        if text == "parcelId" and id_key is None:
            id_key = key
        elif text in {"lastSale.date", "lastSale.price", "lastSale.year", "lastSale.qualified"}:
            slots[key] = text
    if not id_key or not slots:
        return "Pass 2 sale layer has no parcel id and sale date or price, so it was not joined."
    try:
        query, meta = nc.open_service(str(layer["restUrl"]))
        available = set(nc.field_names(meta))
        lookup = {name.lower(): name for name in available}
        live_id = id_key if id_key in available else lookup.get(id_key.lower())
        if not live_id:
            return "Pass 2 sale layer parcel id was not on the service, so sales were not joined."
        wanted = [live_id]
        live_slots: dict[str, str] = {}
        for key, label in slots.items():
            found = key if key in available else lookup.get(key.lower())
            if found and found not in wanted:
                wanted.append(found)
                live_slots[found] = label
        try:
            rows = nc.page_attributes(query, "1=1", wanted)
        except Exception:
            rows = page_attributes_offset(query, wanted)
    except Exception as exc:  # noqa: BLE001
        return f"Pass 2 sale layer did not answer ({exc})."
    index: dict[str, dict] = {}
    for row in rows:
        parcel_id = nc.integral_text(row.get(live_id))
        if not parcel_id:
            continue
        previous = index.get(parcel_id)
        if previous is None or _sale_rank(row, live_slots) >= _sale_rank(previous, live_slots):
            index[parcel_id] = row
    matched = 0
    for feature in features:
        row = index.get(feature["properties"]["parcelId"])
        if not row:
            continue
        sale = feature["properties"].get("lastSale") or {"date": None, "price": None, "qualified": None}
        changed = False
        for key, label in live_slots.items():
            raw = row.get(key)
            if label == "lastSale.price" and sale.get("price") is None:
                price = nc.money(raw)
                if price:
                    sale["price"] = price
                    changed = True
            elif label == "lastSale.date" and not sale.get("date"):
                parsed = nc.parse_sale_date(raw)
                if parsed:
                    sale["date"] = parsed
                    changed = True
            elif label == "lastSale.year" and not sale.get("date"):
                parsed = seed.sale_date(raw, None)
                if parsed:
                    sale["date"] = parsed
                    changed = True
            elif label == "lastSale.qualified" and not sale.get("qualified"):
                text = seed.clean(raw)
                if text:
                    sale["qualified"] = text
                    changed = True
        if not changed:
            continue
        feature["properties"]["lastSale"] = sale
        nc.clear_future_sale(feature["properties"])
        matched += 1
    return f"Pass 2 sale attributes were joined from {layer.get('name') or 'the sale layer'} onto {matched} parcels."


def _sale_rank(row: dict, slots: dict[str, str]) -> tuple:
    date_text = ""
    price = 0.0
    for key, label in slots.items():
        if label == "lastSale.date":
            date_text = nc.parse_sale_date(row.get(key)) or date_text
        elif label == "lastSale.year" and not date_text:
            date_text = seed.sale_date(row.get(key), None) or ""
        elif label == "lastSale.price":
            price = nc.money(row.get(key)) or 0.0
    return date_text, price


def pull_features(*args, **kwargs):
    features, dropped = _pull_features(*args, **kwargs)
    card = kwargs["card"] if "card" in kwargs else (args[3] if len(args) > 3 else None)
    url = kwargs["url"] if "url" in kwargs else (args[0] if args else None)
    if isinstance(card, dict) and isinstance(url, str):
        note = join_external_sales(features, card, url)
        if note:
            SALE_NOTES[nc.norm_source(url)] = note
            b1.log(f"  {note}")
    return features, dropped


def gap_notes(layer, pass2, source_count, kept, distinct_note):
    notes = _gap_notes(layer, pass2, source_count, kept, distinct_note)
    extra = SALE_NOTES.pop(nc.norm_source(str(layer.get("restUrl") or "")), None)
    if extra:
        notes.insert(2, extra)
    return notes[:8]


def attribute_field_map(layer: dict, pass2: dict, available: set[str], id_field: str) -> dict[str, str]:
    """Pass-2 owner field wins when the card labeled it as something other than owner."""
    field_map = _attribute_field_map(layer, pass2, available, id_field)
    if not b1.rest_yes(pass2.get("ownerStatus") or ""):
        return field_map
    lookup = {name.lower(): name for name in available}
    for index, name in enumerate(pass2.get("ownerFields") or []):
        found = name if name in available else lookup.get(name.lower())
        if not found or nc.BANNED_FIELD.search(found):
            continue
        label = "ownerName" if index == 0 else "ownerName2"
        current = field_map.get(found)
        if current is None or nc.target_bucket(current) not in {"owner", "owner2"}:
            field_map[found] = label
    return field_map


def install() -> None:
    seed.fetch_json = fetch_json
    nc.simple_sources = simple_sources
    nc.pull_raw = pull_raw
    b1.pull_features = pull_features
    b1.gap_notes = gap_notes
    b1.attribute_field_map = attribute_field_map


def classify_batch(cards: dict, pass1: dict) -> tuple[list[dict], list[dict]]:
    eligible, skipped = b1.classify(cards, pass1)
    kept: list[dict] = []
    batch_skipped: list[dict] = []
    for item in eligible:
        if item["order"] not in BATCH_ORDERS:
            continue
        status = str(item.get("pass1Status") or "")
        if not status.lower().startswith("usable"):
            batch_skipped.append(
                {
                    "order": item["order"],
                    "fips": item["fips"],
                    "name": item["name"],
                    "reason": f"pass1 {status}",
                }
            )
            continue
        coverage = str(item["layer"].get("coverage") or "").lower()
        if coverage != "county-wide":
            batch_skipped.append(
                {
                    "order": item["order"],
                    "fips": item["fips"],
                    "name": item["name"],
                    "reason": f"layer is not county-wide ({coverage or 'unset'})",
                    "queryUrl": item.get("url"),
                }
            )
            continue
        prior = pass1.get(item["fips"]) or {}
        item["idField"] = declared_id(item, prior)
        try:
            item["liveCount"] = int(str(prior.get("liveCount") or "0").replace(",", "") or 0)
        except ValueError:
            item["liveCount"] = 0
        kept.append(item)
    for item in skipped:
        if item["order"] in BATCH_ORDERS:
            batch_skipped.append(item)
    kept.sort(key=lambda row: (row["order"] in {7, 10}, row["order"]))
    return kept, batch_skipped


def probe_one(item: dict) -> dict:
    if not item.get("idField"):
        try:
            _url, meta = nc.open_service(item["url"])
            found = discover_id(nc.field_names(meta))
        except Exception as exc:  # noqa: BLE001
            b1.log(f"SKIP {item['name']} {item['fips']}: {exc}")
            return {**item, "ok": False, "reason": f"endpoint unreachable: {exc}"}
        if not found:
            reason = "county-wide layer has no parcel id field"
            b1.log(f"SKIP {item['name']} {item['fips']}: {reason}")
            return {**item, "ok": False, "reason": reason}
        item = {**item, "idField": found}
    if is_schneider(item.get("url")):
        try:
            query, meta = nc.open_service(item["url"])
            order = item["idField"] if item["idField"] in set(nc.field_names(meta)) else "OBJECTID"
            fetch_json(
                query,
                {
                    "where": "1=1",
                    "outFields": item["idField"],
                    "returnGeometry": "false",
                    "resultRecordCount": "5",
                    "orderByFields": order,
                    "f": "json",
                },
                timeout=75,
                retries=3,
            )
        except Exception as exc:  # noqa: BLE001
            b1.log(f"SKIP {item['name']} {item['fips']}: {exc}")
            return {
                **item,
                "ok": False,
                "reason": f"endpoint unreachable after retries with backoff: {exc}",
            }
    result = b1.probe_one(item)
    if not result.get("ok"):
        return result
    total = int(result.get("probeCount") or 0) if result.get("geometryAcres") else 0
    if not is_schneider(result.get("queryUrl")) and not result.get("geometryAcres"):
        try:
            total = nc.count_where(result["queryUrl"], "1=1")
        except Exception as exc:  # noqa: BLE001
            return {**result, "ok": False, "reason": f"endpoint unreachable: {exc}"}
    live = int(item.get("liveCount") or 0)
    if not is_schneider(result.get("queryUrl")) and live >= 500 and total and total < int(live * 0.5):
        reason = f"layer returned {total} features against pass-1 county count {live}; not county-wide"
        b1.log(f"SKIP {item['name']} {item['fips']}: {reason}")
        return {**result, "ok": False, "reason": reason}
    if not item.get("expected") and not result.get("geometryAcres"):
        result["expected"] = int(result.get("probeCount") or 0)
    return result


def recovered_pulls(skipped: list[dict]) -> tuple[list[dict], list[dict]]:
    pulled: list[dict] = []
    rest: list[dict] = []
    for item in skipped:
        reason = item.get("reason") or ""
        if "already a complete" not in reason or item["order"] not in BATCH_ORDERS:
            rest.append(item)
            continue
        row = b1.existing_row(item["fips"]) or {}
        if row.get("source") != source_name(item["name"], item["fips"]):
            rest.append(item)
            continue
        markets = row.get("markets") or []
        pulled.append(
            {
                "order": item["order"],
                "fips": item["fips"],
                "name": item["name"],
                "featureCount": int(row.get("featureCount") or 0),
                "queryUrl": row.get("queryUrl"),
                "markets": markets,
                "shelf": markets[0] if markets else None,
                "source": row.get("source"),
                "sourceCount": row.get("sourceCount"),
                "pass1": "usable",
                "appraiserSearchUrl": row.get("appraiserSearchUrl"),
                "gisViewerUrl": row.get("gisViewerUrl"),
                "paLinkVerified": bool(row.get("paLinkVerified")),
                "recovered": True,
            }
        )
    return pulled, rest


def restamp_external_sales(fips_list: list[str] | None = None) -> None:
    """Join a separate pass-2 sale layer onto tiles already written by this batch."""
    install()
    cards = b1.load_cards()
    report = json.loads(RESULT_PATH.read_text()) if RESULT_PATH.exists() else {"pulled": []}
    wanted = {item["fips"] for item in report.get("pulled") or []}
    if fips_list:
        wanted &= set(fips_list)
    for fips in sorted(wanted):
        card = cards.get(fips)
        row_path = seed.COUNTY_DIR / fips / "county.json"
        if not card or not row_path.exists():
            continue
        row = json.loads(row_path.read_text())
        if external_sale_layer(card, row.get("queryUrl") or "") is None:
            continue
        tiles = list((seed.COUNTY_DIR / fips / "tiles").glob("*.geojson"))
        loaded = [(path, json.loads(path.read_text())) for path in tiles]
        features = [feature for _path, collection in loaded for feature in collection.get("features") or []]
        note = join_external_sales(features, card, row.get("queryUrl") or "")
        if not note:
            continue
        b1.log(f"  {row.get('name')} {note}")
        for path, collection in loaded:
            path.write_text(json.dumps(collection, separators=(",", ":")))
        gaps = [note_text for note_text in (row.get("gaps") or []) if "sale layer did not answer" not in note_text]
        if note not in gaps:
            gaps.insert(2, note)
        row["gaps"] = gaps[:8]
        row_path.write_text(json.dumps(row, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--indexes-only", action="store_true")
    parser.add_argument("--stamp-sales", action="store_true")
    parser.add_argument("--fips", action="append", default=[])
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.stamp_sales:
        restamp_external_sales(args.fips or None)
        return
    install()
    if args.indexes_only:
        catalog = json.loads(b1.CATALOG_PATH.read_text())
        seed.rebuild_indexes(catalog)
        return
    cards = b1.load_cards()
    pass1 = b1.pass1_index()
    eligible, skipped = classify_batch(cards, pass1)
    if args.fips:
        wanted = {item.zfill(5) for item in args.fips}
        eligible = [item for item in eligible if item["fips"] in wanted]
        skipped = [item for item in skipped if item["fips"] in wanted]
    already, skipped = recovered_pulls(skipped)
    b1.log(f"Eligible before probe: {len(eligible)}; already written this batch: {len(already)}")
    normals = [item for item in eligible if not is_schneider(item.get("url"))]
    slow = [item for item in eligible if is_schneider(item.get("url"))]
    reachable: list[dict] = []

    def take(items: list[dict]) -> None:
        cursor = 0
        while cursor < len(items):
            window = items[cursor : cursor + max(1, args.workers)]
            cursor += len(window)
            with ThreadPoolExecutor(max_workers=max(1, len(window))) as pool:
                futures = {pool.submit(probe_one, item): item for item in window}
                done = {futures[future]["fips"]: future.result() for future in as_completed(futures)}
            for item in window:
                probed = done[item["fips"]]
                if probed.get("ok"):
                    reachable.append(probed)
                else:
                    skipped.append(
                        {
                            "order": probed["order"],
                            "fips": probed["fips"],
                            "name": probed["name"],
                            "reason": probed.get("reason") or "endpoint unreachable",
                            "queryUrl": probed.get("url"),
                        }
                    )

    # Schneider retries run beside the fast probes so a dead WFS does not
    # hold the rest of the batch.
    slow_pool = ThreadPoolExecutor(max_workers=max(1, len(slow) or 1))
    slow_futures = {slow_pool.submit(probe_one, item): item for item in slow}
    take(normals)
    for future in as_completed(slow_futures):
        item = slow_futures[future]
        probed = future.result()
        if probed.get("ok"):
            reachable.append(probed)
        else:
            skipped.append(
                {
                    "order": item["order"],
                    "fips": item["fips"],
                    "name": item["name"],
                    "reason": probed.get("reason") or "endpoint unreachable",
                    "queryUrl": item.get("url"),
                }
            )
    slow_pool.shutdown(wait=True)
    reachable.sort(key=lambda row: row["order"])
    if args.probe_only:
        print(
            json.dumps(
                {
                    "reachable": [
                        {
                            "order": item["order"],
                            "fips": item["fips"],
                            "name": item["name"],
                            "probeCount": item.get("probeCount"),
                            "expected": item.get("expected"),
                            "geometryAcres": item.get("geometryAcres"),
                            "queryUrl": item.get("queryUrl"),
                            "where": item.get("where"),
                            "idField": item.get("idField"),
                        }
                        for item in reachable
                    ],
                    "skipped": skipped,
                    "already": already,
                },
                indent=2,
            )
        )
        return
    catalog = json.loads(b1.CATALOG_PATH.read_text())
    kept = list(already)
    for item in already:
        markets = item.get("markets") or []
        if markets:
            b1.commit_markets(catalog, item["fips"], item["name"], markets)
    index = 0
    while index < len(reachable):
        batch = reachable[index : index + max(1, args.workers)]
        index += len(batch)
        for item in batch:
            item["markets"] = b1.planned_markets(catalog, item["fips"])
            b1.log(f"SHELF {item['name']} {item['fips']} -> {', '.join(item['markets'])}")
        results: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=max(1, len(batch))) as pool:
            futures = {
                pool.submit(b1.download_county, item, item["markets"], args.refresh): item for item in batch
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    results[item["fips"]] = {"ok": True, "pulled": future.result()}
                except Exception as exc:  # noqa: BLE001
                    b1.restore_county(item["fips"])
                    b1.log(f"FAILED {item['fips']}: {exc}")
                    results[item["fips"]] = {"ok": False, "error": str(exc)}
        for item in batch:
            result = results[item["fips"]]
            if not result["ok"]:
                skipped.append(
                    {
                        "order": item["order"],
                        "fips": item["fips"],
                        "name": item["name"],
                        "reason": f"download failed: {result['error']}",
                        "queryUrl": item.get("queryUrl"),
                    }
                )
                continue
            b1.commit_markets(catalog, item["fips"], item["name"], item["markets"])
            kept.append(result["pulled"])
    if not kept:
        raise SystemExit("No batch 4 counties downloaded")
    b1.CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    if args.fips and RESULT_PATH.exists():
        previous = json.loads(RESULT_PATH.read_text())
        by_fips = {item["fips"]: item for item in previous.get("pulled") or []}
        for item in kept:
            by_fips[item["fips"]] = item
        kept = list(by_fips.values())
        seen = {item["fips"] for item in skipped}
        skipped = [item for item in previous.get("skipped") or [] if item["fips"] not in seen] + skipped
    kept.sort(key=lambda row: row["order"])
    skipped.sort(key=lambda row: row["order"])
    report = {
        "pulled": kept,
        "skipped": skipped,
        "excludedOrders": "26-69 are Georgia rural OZ batches 2 and 3 and were not requested",
        "pulledOn": b1.TODAY,
        "totalParcels": sum(item["featureCount"] for item in kept),
    }
    RESULT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    if not args.skip_index:
        seed.rebuild_indexes(catalog)
    b1.log(
        "Done "
        + json.dumps(
            {"counties": len(kept), "parcels": report["totalParcels"], "skipped": [item["name"] for item in skipped]},
            indent=2,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
