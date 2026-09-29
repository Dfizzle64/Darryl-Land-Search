#!/usr/bin/env python3
"""5.0–150.0 acre parcels for Georgia rural Opportunity Zone batch 3.

Reuses the batch 1 parcel loader, shelf assignment, and tile writer. This batch
is pass-2 orders 48 through 69 whose pass-1 status is usable: Dooly, Echols,
Emanuel, Evans, Fayette, Floyd, Glynn, Grady, Greene, Hall, Henry, Houston,
Irwin, Jackson, Jeff Davis, Lanier, Laurens, Liberty, Long, Lowndes, Lumpkin,
and McDuffie. A county that already has a complete 5.0–150.0 acre extract is
not pulled again. An endpoint that does not answer is skipped. Nothing outside
orders 48–69 is loaded.

Does not add a market shelf. Counties already on a shelf stay there. Others
go on the nearest existing Georgia shelf (Atlanta, Savannah, Chattanooga,
Valdosta, Macon, or Athens). No Opportunity Zone status, school grade, or base
flood elevation is stored. Household income stays the ACS B19013_001E join.
GDOT AADT stays off the parcel. Property-appraiser URLs are filled from the
pass-2 template with each parcel's own id and are not requested. Owner phone
and email are not ingested. A confidential-owner or no-release flag suppresses
owner and mailing fields. Sale dates after the pull date are cleared.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import ga_rural_oz_batch1_parcels as b1
import nc_rural_oz_batch1_parcels as nc
import seed_market_parcels as seed

ORDER_MIN = 48
ORDER_MAX = 69
CACHE_DIR = Path("/tmp/dls-ga-rural-oz-batch3")
RESULT_PATH = b1.CARDS / "batch3-result.json"
PRIVACY_FIELD = re.compile(r"no_?release|owner_?privacy|privacy_?flag|confidential|hide_?name|redact_?owner", re.I)
SHAPE_AREA = re.compile(r"^shape__?area$", re.I)

_ORIG_ROWS = b1.pass2_rows
_ORIG_BUCKET = b1.target_bucket
_ORIG_MAP = b1.attribute_field_map
_ORIG_CONFIDENTIAL = b1.row_confidential
_ORIG_GAPS = b1.gap_notes
_ORIG_RESOLVE = nc.resolve_acres
_ORIG_FILL = nc.fill_template
_ORIG_DOWNLOAD = b1.download_county
_ORIG_APPRAISER = b1.appraiser_url
GENERIC_LINK_FIELDS = {"pin", "parcelid", "id", "parcel"}
A_VALUE = {"avalue", "aval"}
_CURRENT: dict[str, str] = {}


def pass2_rows() -> list[dict]:
    """Usable pass-1 rows in this batch only. Partial and later orders stay out."""
    selected = []
    for row in _ORIG_ROWS():
        order = int(row["order"])
        if order < ORDER_MIN or order > ORDER_MAX:
            continue
        if b1.pass1_kind(row.get("pass1") or "") != "usable":
            continue
        selected.append(row)
    return selected


def target_bucket(label: str) -> str | None:
    text = label.split("(")[0].strip()
    extra = {
        "mailingCity": "mailCity",
        "mailingState": "mailState",
        "mailingZip": "mailZip",
        "mailingAddress2": "mail2",
        "ownerFirstName": "ownerFirst",
        "ownerNameFirst": "ownerFirst",
        "situsStreetDir": "situsDir",
        "situsUnit": "situsUnit",
        "acreageGisSqFt": None,
    }
    if text in extra:
        return extra[text]
    return _ORIG_BUCKET(label)


def attribute_field_map(layer: dict, pass2: dict, available: set[str], id_field: str) -> dict[str, str]:
    field_map = _ORIG_MAP(layer, pass2, available, id_field)
    for name in sorted(available):
        if not PRIVACY_FIELD.search(name) or re.search(r"phone|e-?mail", name, re.I):
            continue
        if name not in field_map:
            field_map[name] = "ownerPrivacyFlag"
    fixed: dict[str, str] = {}
    for key, label in field_map.items():
        base = re.sub(r"[^a-z0-9]", "", key.split("+")[0].lower())
        # WinGAP a_value is land. mavcurr is the assessed field and is empty on these layers.
        if label == "tax.assessedValue" and base in A_VALUE:
            label = "tax.landValue"
        fixed[key] = label
    return fixed


def appraiser_url(template: str | None, attrs: dict, parcel_id: str, token_value: str, sample: str | None) -> str | None:
    """Keep a link whose parcel id merely contains the pass-2 sample string.

    Dooly parcel ``21      1`` contains sample ``1      1``. Evans parcel
    ``028    018 001`` starts with sample ``028    018``. Those are different
    parcels. A single URL copied onto every parcel is still cleared later.
    """
    del sample
    return _ORIG_APPRAISER(template, attrs, parcel_id, token_value, None)


def fill_template(template: str | None, attrs: dict, parcel_id: str) -> str | None:
    """Use the explicit link key for {parcelId}. A same-named attribute can be a shorter sibling."""
    if isinstance(attrs, dict):
        attrs = {key: value for key, value in attrs.items() if str(key).lower() not in GENERIC_LINK_FIELDS}
    return _ORIG_FILL(template, attrs, parcel_id)


def row_confidential(attrs: dict) -> bool:
    if _ORIG_CONFIDENTIAL(attrs):
        return True
    for key, value in attrs.items():
        if not PRIVACY_FIELD.search(str(key)):
            continue
        if str(value or "").strip().lower() in b1.AFFIRMATIVE:
            return True
    return False


def resolve_acres(url: str, acre_field: str, cast_hint: bool, extra: list[str], available: set[str], expected: int):
    """Glynn publishes State Plane square feet on Shape__Area. Do not treat that as acres."""
    lookup = {name.lower(): name for name in available}
    field = acre_field if acre_field in available else lookup.get((acre_field or "").lower())
    if field and SHAPE_AREA.match(field):
        where = f"{field}>={int(seed.MIN_SQFT)} AND {field}<={int(seed.MAX_SQFT)}"
        count = nc.count_where(url, where)
        if count <= 0:
            raise RuntimeError(f"{field} square-foot filter returned no parcels")
        return where, 43560.0, False, count, field
    return _ORIG_RESOLVE(url, acre_field, cast_hint, extra, available, expected)


def gap_notes(layer: dict, pass2: dict, source_count: int, kept: int, distinct_note: str | None) -> list[str]:
    notes = _ORIG_GAPS(layer, pass2, source_count, kept, distinct_note)
    acre = str(layer.get("acreageField") or "")
    if SHAPE_AREA.match(acre):
        notes.insert(
            1,
            "Shape__Area is Georgia East State Plane square feet. Stored acres are that area divided by 43560, then kept only inside 5.0–150.0.",
        )
    if pass2.get("saleStatus") and b1.rest_yes(pass2["saleStatus"]):
        notes.append(
            "Pass 2 sale status is REST. A sale price or date is stored only when that field is on the public parcel layer."
        )
    fips = _CURRENT.get("fips") or ""
    name = (_CURRENT.get("name") or "").lower()
    caveat = None
    if name == "lanier" or fips == "13173":
        caveat = "Pass 2 names owner field LASTNAME, but the live FeatureServer does not publish that field, so owner stays empty."
    elif name in {"dooly", "echols", "greene"} or fips in {"13093", "13101", "13133"}:
        caveat = "WinGAP a_value is stored as land value. It is not the 40 percent assessed amount, and mavcurr is empty, so assessed value stays blank."
    elif name == "hall" or fips == "13139":
        caveat = "A NO_RELEASE flag suppresses owner and mailing fields."
    elif name == "floyd" or fips == "13115":
        caveat = "Pass 2 sale status is REST, but the live CurrentParcels layer has no sale price or date field, so sale stays empty."
    elif name == "jackson" or fips == "13157":
        caveat = "Market value is the sum of FMVRES, FMVCOM, and FMVACC. The total stays empty when those components are zero."
    if caveat:
        notes.insert(2, caveat)
    unique: list[str] = []
    for note in notes:
        if note and note not in unique:
            unique.append(note)
    return unique[:8]


def download_county(item: dict, markets: list[str], refresh: bool) -> dict:
    _CURRENT["fips"] = str(item.get("fips") or "")
    _CURRENT["name"] = str(item.get("name") or "")
    try:
        return _ORIG_DOWNLOAD(item, markets, refresh)
    finally:
        _CURRENT.clear()


def install_patches() -> None:
    b1.pass2_rows = pass2_rows
    b1.target_bucket = target_bucket
    nc.target_bucket = target_bucket
    b1.attribute_field_map = attribute_field_map
    b1.row_confidential = row_confidential
    b1.gap_notes = gap_notes
    nc.resolve_acres = resolve_acres
    nc.fill_template = fill_template
    b1.appraiser_url = appraiser_url
    b1.download_county = download_county
    b1.CACHE_DIR = CACHE_DIR
    b1.RESULT_PATH = RESULT_PATH


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--indexes-only", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    install_patches()
    if args.indexes_only:
        catalog = json.loads(b1.CATALOG_PATH.read_text())
        seed.rebuild_indexes(catalog)
        return
    cards = b1.load_cards()
    pass1 = b1.pass1_index()
    eligible, skipped = b1.classify(cards, pass1)
    outside = [item for item in eligible if not (ORDER_MIN <= int(item["order"]) <= ORDER_MAX)]
    if outside:
        raise SystemExit(f"Refusing to load orders outside {ORDER_MIN}-{ORDER_MAX}: {[item['fips'] for item in outside]}")
    b1.log(f"Eligible before probe: {len(eligible)}")
    reachable: list[dict] = []
    cursor = 0
    while cursor < len(eligible):
        window = eligible[cursor : cursor + max(1, args.workers)]
        cursor += len(window)
        with ThreadPoolExecutor(max_workers=max(1, len(window))) as pool:
            futures = {pool.submit(b1.probe_one, item): item for item in window}
            done = [future.result() for future in as_completed(futures)]
        by_fips = {item["fips"]: item for item in done}
        for item in window:
            probed = by_fips[item["fips"]]
            if probed["ok"]:
                if not probed.get("expected"):
                    probed["expected"] = int(probed.get("probeCount") or 0)
                reachable.append(probed)
            else:
                skipped.append(
                    {
                        "order": probed["order"],
                        "fips": probed["fips"],
                        "name": probed["name"],
                        "reason": probed["reason"],
                        "queryUrl": probed.get("url"),
                    }
                )
    summary = {
        "reachable": [
            {
                "order": item["order"],
                "fips": item["fips"],
                "name": item["name"],
                "probeCount": item.get("probeCount"),
                "where": item.get("where"),
                "acresScale": item.get("acresScale"),
            }
            for item in reachable
        ],
        "skipped": skipped,
    }
    print(json.dumps(summary, indent=2))
    if args.probe_only:
        if not reachable:
            raise SystemExit("No reachable counties")
        return
    catalog = json.loads(b1.CATALOG_PATH.read_text())
    for item in reachable:
        item["markets"] = b1.planned_markets(catalog, item["fips"])
        b1.log(f"SHELF {item['name']} {item['fips']} -> {', '.join(item['markets'])}")
    kept: list[dict] = []
    index = 0
    while index < len(reachable):
        batch = reachable[index : index + max(1, args.workers)]
        index += len(batch)
        results: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=max(1, len(batch))) as pool:
            futures = {pool.submit(b1.download_county, item, item["markets"], args.refresh): item for item in batch}
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
            kept.append(result["pulled"])
    if not kept:
        raise SystemExit("No counties downloaded")
    kept.sort(key=lambda item: item["order"])
    for item in kept:
        b1.commit_markets(catalog, item["fips"], item["name"], item["markets"])
    b1.CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    report = {
        "orders": [ORDER_MIN, ORDER_MAX],
        "pulled": kept,
        "skipped": skipped,
        "pulledOn": b1.TODAY,
        "totalParcels": sum(item["featureCount"] for item in kept),
    }
    RESULT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    if not args.skip_index:
        seed.rebuild_indexes(catalog)
    b1.log("Done " + json.dumps({"counties": len(kept), "parcels": report["totalParcels"]}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
