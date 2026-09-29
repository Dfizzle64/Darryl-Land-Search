#!/usr/bin/env python3
"""5.0–150.0 acre parcels for Alabama rural Opportunity Zone batch 2.

Reuses the batch 1 loader. Henry, Lawrence, and Coosa go first. The rest of
the queue is every other Alabama county card that still has a public parcel
polygon and is not already a complete 5.0–150.0 acre extract: Cleburne,
Houston, Lee, and Russell. Tuscaloosa is already complete and is not
re-pulled. Colbert is probed once and skipped when the service is still
stopped. The 26 Flagship counties have no public parcel map and are not
requested.

Does not add a market shelf. Counties already on a shelf stay there. Others
go on the nearest existing Alabama shelf. No Opportunity Zone status, school
grade, or base flood elevation is stored. Household income stays the ACS
B19013_001E join. Property-appraiser URLs are stored from the card pattern
and are not requested. A single sample account id is not copied onto every
parcel. Owner phone and email are not ingested. A confidential-owner flag
clears owner and mailing fields. Sale dates after the pull date are cleared.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import al_rural_oz_batch1_parcels as b1
import seed_market_parcels as seed

# Henry, Lawrence, Coosa first, then the other public-layer counties that
# batch 1 left. Colbert is last so the one retry does not block the rest.
QUEUE = [
    "01067",  # Henry
    "01079",  # Lawrence
    "01037",  # Coosa
    "01029",  # Cleburne
    "01069",  # Houston
    "01081",  # Lee
    "01113",  # Russell
    "01033",  # Colbert — one retry
]
# Flagship / no public parcel REST. Do not request these.
NO_PUBLIC_PARCEL = [
    "01007",  # Bibb
    "01013",  # Butler
    "01017",  # Chambers
    "01021",  # Chilton
    "01023",  # Choctaw
    "01025",  # Clarke
    "01027",  # Clay
    "01031",  # Coffee
    "01035",  # Conecuh
    "01039",  # Covington
    "01041",  # Crenshaw
    "01045",  # Dale
    "01053",  # Escambia
    "01057",  # Fayette
    "01061",  # Geneva
    "01075",  # Lamar
    "01085",  # Lowndes
    "01091",  # Marengo
    "01093",  # Marion
    "01105",  # Perry
    "01107",  # Pickens
    "01109",  # Pike
    "01111",  # Randolph
    "01123",  # Tallapoosa
    "01127",  # Walker
    "01129",  # Washington
]
TARGET = 20
RESULT_PATH = b1.CARDS / "batch2-result.json"
TRAILING_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})\s*$")
CONFIDENTIAL_TRUE = {"y", "yes", "true", "1", "t"}

# Nearest existing Alabama shelf. County seat to shelf city. An Alabama shelf
# is preferred over a nearer out-of-state shelf (Cleburne / Heflin vs Atlanta).
b1.NEAREST_AL_SHELF.update(
    {
        "01029": ["Birmingham"],  # Cleburne / Heflin
        "01037": ["Montgomery"],  # Coosa / Rockford
        "01067": ["Montgomery"],  # Henry / Abbeville
        "01069": ["Montgomery"],  # Houston / Dothan
        "01079": ["Huntsville"],  # Lawrence / Moulton
        "01081": ["Montgomery"],  # Lee / Opelika
        "01113": ["Montgomery"],  # Russell / Phenix City
    }
)
b1.CACHE_DIR = Path("/tmp/dls-al-rural-oz-batch2")

_parse_sale_date = b1.parse_sale_date
_split_city_state = b1.split_city_state
_attribute_field_map = b1.attribute_field_map
_feature_from = b1.feature_from
_pull_features = b1.pull_features


def parse_sale_date(value):
    """Batch 1 dates, plus a trailing M/D/YYYY on a deed book/page string."""
    parsed = _parse_sale_date(value)
    if parsed:
        return parsed
    text = seed.clean(value)
    if not text:
        return None
    match = TRAILING_DATE.search(text)
    if not match:
        return None
    month, day, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def split_city_state(value):
    """ZIP+4 written as nine digits (Henry MAILING3) still yields the 5-digit ZIP."""
    text = seed.clean(value)
    if not text:
        return None, None, None
    zip_match = re.search(r"(\d{5})(?:-?\d{4})?$", text)
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


def attribute_field_map(card, layer, available):
    field_map = _attribute_field_map(card, layer, available)
    rewritten = {}
    for key, label in field_map.items():
        text = label.split("(")[0].strip()
        if text == "lastSale.deedBookPageDate":
            rewritten[key] = "lastSale.date"
        else:
            rewritten[key] = label
    return rewritten


def card_links(card: dict) -> dict:
    """Batch 1 links, plus the statewide pass-2 block used by Cleburne, Houston, Lee, and Russell."""
    deep = {}
    sections = []
    for key in ("pass2RuralOz2026_09_28", "pass2Statewide2026_09_28", "pass2"):
        section = card.get(key) or {}
        if isinstance(section, dict):
            sections.append(section)
    for section in sections:
        if isinstance(section.get("deepLink"), dict) and not deep:
            deep = section["deepLink"]
    template = card.get("appraiserSearchUrl")
    pattern = deep.get("pattern") if isinstance(deep, dict) else None
    if isinstance(pattern, str) and "{PIN}" in pattern:
        template = pattern
    elif isinstance(template, str) and "{PIN}" not in template and "{parcelId}" not in template:
        template = pattern if isinstance(pattern, str) else None
    verified = str((deep or {}).get("verified") or "").strip().lower()
    gis = None
    for section in sections:
        gis_block = section.get("jurisdictionGisUrl")
        if isinstance(gis_block, dict) and isinstance(gis_block.get("url"), str):
            gis = gis_block["url"]
            break
    gis = gis or card.get("jurisdictionGisUrl") or card.get("publicGisUrl")
    return {
        "template": template if isinstance(template, str) else None,
        "pinNote": (deep or {}).get("pinField") if isinstance(deep, dict) else None,
        "pinField": b1.pin_field_name((deep or {}).get("pinField") if isinstance(deep, dict) else None),
        "gis": gis if isinstance(gis, str) else None,
        "verified": verified == "yes",
    }


def row_confidential(attrs: dict) -> bool:
    for key, value in attrs.items():
        if not re.search(r"confidential", str(key), re.I):
            continue
        text = str(value or "").strip().lower()
        if text in CONFIDENTIAL_TRUE:
            return True
    return False


def card_confidential(card: dict) -> bool:
    for key in ("confidentialOwner", "suppressOwner", "ownerConfidential"):
        flag = card.get(key)
        if flag in (True, "yes", "suppress", "true", "y"):
            return True
    for layer in card.get("layers") or []:
        if not isinstance(layer, dict) or layer.get("role") != "parcels":
            continue
        flag = layer.get("confidentialOwner") or layer.get("suppressOwner")
        if flag in (True, "yes", "suppress", "true", "y"):
            return True
    return False


def suppress_owner(feature: dict) -> None:
    props = feature["properties"]
    props["ownerName"] = None
    props["ownerName2"] = None
    mail = props.get("mailingAddress") or {}
    for key in list(mail):
        mail[key] = None


def scrub_contact_values(feature: dict) -> None:
    props = feature["properties"]
    if b1.sensitive_contact(props.get("ownerName")):
        props["ownerName"] = None
    if b1.sensitive_contact(props.get("ownerName2")):
        props["ownerName2"] = None
    mail = props.get("mailingAddress") or {}
    for key, value in list(mail.items()):
        if isinstance(value, str) and b1.sensitive_contact(value):
            mail[key] = None


def feature_from(attrs, geom, **kwargs):
    feature = _feature_from(attrs, geom, **kwargs)
    if feature is None:
        return None
    card = kwargs.get("card") or {}
    if row_confidential(attrs) or card_confidential(card):
        suppress_owner(feature)
    scrub_contact_values(feature)
    return feature


def pull_features(*args, **kwargs):
    features, dropped = _pull_features(*args, **kwargs)
    urls = [feature["properties"].get("appraiserUrl") for feature in features if feature["properties"].get("appraiserUrl")]
    if len(urls) > 10 and len(set(urls)) == 1:
        b1.log("  cleared one repeated appraiser URL so a sample account is not copied onto every parcel")
        for feature in features:
            feature["properties"]["appraiserUrl"] = None
    return features, dropped


b1.parse_sale_date = parse_sale_date
b1.split_city_state = split_city_state
b1.attribute_field_map = attribute_field_map
b1.card_links = card_links
b1.feature_from = feature_from
b1.pull_features = pull_features


def public_name(cards: dict, fips: str) -> str:
    card = cards.get(fips) or {}
    return b1.short_name(card, fips) if card else fips


def classify(cards: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    eligible: list[dict] = []
    skipped: list[dict] = []
    for fips in NO_PUBLIC_PARCEL:
        skipped.append(
            {
                "fips": fips,
                "name": public_name(cards, fips),
                "reason": "no public parcel map (Flagship or no parcel REST); not requested",
            }
        )
    for fips in QUEUE:
        card = cards.get(fips)
        name = public_name(cards, fips)
        if not card or card.get("level") != "county":
            skipped.append({"fips": fips, "name": name, "reason": "no county card"})
            continue
        current = b1.existing_row(fips)
        try:
            layer = b1.choose_layer(card)
            url = b1.query_url(str(layer["restUrl"]))
        except Exception as exc:  # noqa: BLE001
            reason = (
                "no public parcel layer (Flagship or no parcel REST)"
                if str(exc) == "no public parcel layer"
                else f"no public parcel layer ({exc})"
            )
            skipped.append({"fips": fips, "name": name, "reason": reason})
            continue
        if b1.fully_loaded(current):
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
    # Tuscaloosa was flagged as remaining and is already complete.
    tuscaloosa = b1.existing_row("01125")
    if b1.fully_loaded(tuscaloosa):
        skipped.append(
            {
                "fips": "01125",
                "name": "Tuscaloosa",
                "reason": f"already a complete 5.0–150.0 acre extract ({int(tuscaloosa.get('featureCount') or 0)} parcels)",
                "queryUrl": tuscaloosa.get("queryUrl"),
            }
        )
    return eligible, skipped


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
        catalog = json.loads(b1.CATALOG_PATH.read_text())
        seed.rebuild_indexes(catalog)
        return
    cards = b1.load_cards()
    eligible, skipped = classify(cards)
    b1.log(f"Eligible before probe: {len(eligible)}")
    probed: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(b1.probe_one, item) for item in eligible]
        for future in as_completed(futures):
            probed.append(future.result())
    by_fips = {item["fips"]: item for item in probed}
    ordered = [by_fips[item["fips"]] for item in eligible]
    reachable = []
    for item in ordered:
        if item["ok"]:
            reachable.append(item)
        else:
            skipped.append(
                {"fips": item["fips"], "name": item["name"], "reason": item["reason"], "queryUrl": item["queryUrl"]}
            )
    summary = {
        "reachable": [
            {
                "fips": item["fips"],
                "name": item["name"],
                "queryUrl": item["queryUrl"],
                "probeCount": item.get("probeCount"),
            }
            for item in reachable
        ],
        "skipped": [{key: value for key, value in item.items() if key not in {"card", "layer"}} for item in skipped],
    }
    print(json.dumps(summary, indent=2))
    if args.probe_only:
        return
    selected_filter = {item.lower() for item in args.county}
    queue = []
    for item in reachable:
        if selected_filter and item["fips"] not in selected_filter and item["name"].lower() not in selected_filter:
            continue
        queue.append(item)
    if not queue:
        raise SystemExit("No reachable counties")
    catalog = json.loads(b1.CATALOG_PATH.read_text())
    for item in queue:
        item["markets"] = b1.planned_markets(catalog, item["fips"], item["card"])
    kept: list[dict] = []
    index = 0
    goal = len(queue) if selected_filter else min(TARGET, len(queue))
    while len(kept) < goal and index < len(queue):
        batch = queue[index : index + max(1, args.workers)]
        index += len(batch)
        results: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=max(1, len(batch))) as pool:
            futures = {
                pool.submit(b1.download_county, item["card"], item["markets"], args.refresh): item for item in batch
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    results[item["fips"]] = {"ok": True, "pulled": future.result(), "item": item}
                except Exception as exc:  # noqa: BLE001
                    b1.restore_county(item["fips"])
                    b1.log(f"FAILED {item['fips']}: {exc}")
                    results[item["fips"]] = {"ok": False, "error": str(exc), "item": item}
        for item in batch:
            result = results[item["fips"]]
            if not result["ok"]:
                skipped.append(
                    {
                        "fips": item["fips"],
                        "name": item["name"],
                        "reason": f"download failed: {result['error']}",
                        "queryUrl": item["queryUrl"],
                    }
                )
                continue
            if selected_filter or len(kept) < TARGET:
                kept.append(result["pulled"])
                continue
            b1.restore_county(item["fips"])
            skipped.append({"fips": item["fips"], "name": item["name"], "reason": "batch already filled"})
    if not kept:
        raise SystemExit("No counties downloaded")
    for item in kept:
        b1.commit_markets(catalog, item["fips"], item["name"], item["markets"])
    b1.CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    report = {
        "pulled": kept,
        "skipped": [{key: value for key, value in item.items() if key not in {"card", "layer"}} for item in skipped],
    }
    RESULT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    if not args.skip_index:
        seed.rebuild_indexes(catalog)
    b1.log("Done " + json.dumps(kept, indent=2))


if __name__ == "__main__":
    sys.exit(main())
