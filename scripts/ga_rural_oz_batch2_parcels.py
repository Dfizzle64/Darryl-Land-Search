#!/usr/bin/env python3
"""5.0–150.0 acre parcels for Georgia rural Opportunity Zone batch 2.

Pass-2 orders 26 through 47 whose pass-1 status is usable: Appling, Atkinson,
Baldwin, Banks, Barrow, Bartow, Ben Hill, Brantley, Brooks, Bulloch, Butts,
Camden, Candler, Charlton, Chattahoochee, Clay, Coffee, Cook, Crawford, Crisp,
Decatur, and Dodge. A county that already has a complete 5.0–150.0 acre extract
is not re-pulled. Orders 25 and below belong to batch 1 and are not loaded.

Reuses the North Carolina rural-OZ parcel loader (paging, acre filter, field
map, appraiser template, confidential-owner suppression, tile writer) and the
market catalog shelf assignment. Counties already on a shelf stay there. Others
go on the nearest existing Georgia shelf (Atlanta, Savannah, Chattanooga,
Valdosta, Macon, or Athens). No new market shelf is added.

Public GIS only. qPublic and Beacon pages are not requested. Tax, sale, and
owner are stamped only from the public REST fields pass 2 published. A
property-appraiser URL is filled from the pass-2 template with that parcel's
id. Sale dates after the pull date are cleared. Owner phone and email are not
ingested. No Opportunity Zone status, school grade, or base flood elevation is
stored. Household income stays the ACS B19013_001E join. GDOT AADT stays the
query-time statewide join.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

import nc_rural_oz_batch3_parcels as nc
import seed_market_parcels as seed

ROOT = seed.ROOT
CATALOG_PATH = seed.CATALOG_PATH
CARDS = ROOT / "data" / "ga-parcel-cards"
PASS1_CSV = CARDS / "_rural-oz2-pass1-results-2026-09-28.csv"
PASS2_CSV = CARDS / "_rural-oz2-pass2-results-2026-09-28.csv"
CACHE_DIR = Path("/tmp/dls-ga-rural-oz-batch2")
ORDER_MIN = 26
ORDER_MAX = 47
# West, south, east, north. Drops a service that returns polygons outside Georgia.
GA_BBOX = (-85.70, 30.20, -80.65, 35.10)
# Existing shelves that already carry Georgia counties. City coordinates.
GA_SHELVES = {
    "Atlanta": (-84.3880, 33.7490),
    "Savannah": (-81.0912, 32.0809),
    "Chattanooga": (-85.3097, 35.0456),
    "Valdosta": (-83.2785, 30.8327),
    "Macon": (-83.6324, 32.8407),
    "Athens": (-83.3576, 33.9519),
}
COUNT_HINT = re.compile(r"5\s*[–-]\s*150[^0-9]{0,12}([\d,]{3,})", re.I)
PAID_VENDOR = nc.PAID_VENDOR

_ORIG_FEATURE = nc.feature_from
_ORIG_GUESS_TAX = nc.guess_tax_label
_ORIG_BUCKET = nc.target_bucket


def in_georgia(center: tuple[float, float] | None) -> bool:
    if not center or not seed.plausible_centroid(center):
        return False
    lon, lat = center
    west, south, east, north = GA_BBOX
    return west <= lon <= east and south <= lat <= north


def guess_tax_label(field: str) -> str | None:
    name = field.lower()
    if name in {"curr_val", "currentvalue", "current_val", "total_taxable_fmv"}:
        return "tax.marketValue"
    if name in {"a_value", "avalue"}:
        return "tax.landValue"
    if name in {"esttax", "est_tax"}:
        return "tax.due"
    if name in {"mavcurr", "mav_curr"}:
        return "tax.assessedValue"
    if name in {"fmvres", "fmvcom", "fmvacc", "prev_val"}:
        return None
    return _ORIG_GUESS_TAX(field)


def target_bucket(label: str) -> str | None:
    text = label.split("(")[0].strip()
    if text in {"tax.estimatedTax", "tax.due"}:
        return "taxes"
    if text in {"tax.fmvResidential", "tax.marketValueResidential", "tax.marketValueCommercial", "tax.marketValueAccessory", "tax.fmvCommercial", "tax.fmvAccessory", "tax.priorMarketValue"}:
        return None
    if text in {"appraiserReportUrl", "appraiserSearchUrl"}:
        # The pass-2 template is filled per parcel. A layer URL is not copied.
        return None
    return _ORIG_BUCKET(label)


def feature_from(*args: Any, **kwargs: Any) -> dict | None:
    feature = _ORIG_FEATURE(*args, **kwargs)
    if not feature:
        return None
    feature["properties"]["state"] = "Georgia"
    attrs = args[0] if args else kwargs.get("attrs") or {}
    owner = feature["properties"].get("ownerName")
    if owner:
        first = seed.clean(nc.attr_get(attrs, "firstname") or nc.attr_get(attrs, "FIRSTNAME"))
        if first and not nc.sensitive_contact(first) and first.upper() not in owner.upper():
            feature["properties"]["ownerName"] = f"{owner} {first}".strip()
    return feature


nc.in_north_carolina = in_georgia
nc.guess_tax_label = guess_tax_label
nc.target_bucket = target_bucket
nc.feature_from = feature_from


def log(message: str) -> None:
    nc.log(message)


def load_cards() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for path in sorted(CARDS.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        fips = str(data.get("fips") or "").zfill(5)
        if fips.strip("0"):
            data["fips"] = fips
            found[fips] = data
    return found


def pass_rows() -> list[dict]:
    pass1 = {row["fips"].zfill(5): row for row in csv.DictReader(PASS1_CSV.open())}
    rows = []
    for row in csv.DictReader(PASS2_CSV.open()):
        order = int(row["order"])
        if order < ORDER_MIN or order > ORDER_MAX:
            continue
        if row.get("pass1") != "usable":
            continue
        fips = row["fips"].zfill(5)
        base = pass1.get(fips) or {}
        rows.append({**base, **row, "fips": fips, "order": order})
    rows.sort(key=lambda item: item["order"])
    return rows


def acre_hint(card: dict) -> int:
    notes = []
    for layer in card.get("layers") or []:
        if layer.get("role") == "parcels" and layer.get("notes"):
            notes.append(str(layer.get("notes")))
    text = " ".join(notes)
    match = COUNT_HINT.search(text)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def parcel_layer(card: dict) -> dict | None:
    layers = [layer for layer in card.get("layers") or [] if layer.get("role") == "parcels" and layer.get("status") == "usable" and layer.get("restUrl")]
    return layers[0] if layers else None


def load_pass2(card: dict, row: dict) -> dict[str, Any]:
    block = card.get("pass2_2026-09-28") if isinstance(card.get("pass2_2026-09-28"), dict) else {}
    tax = block.get("tax") if isinstance(block.get("tax"), dict) else {}
    sales = block.get("sales") if isinstance(block.get("sales"), dict) else {}
    owner = block.get("ownerEntity") if isinstance(block.get("ownerEntity"), dict) else {}
    deep = block.get("appraiserSearchUrl") if isinstance(block.get("appraiserSearchUrl"), dict) else {}
    gis = block.get("jurisdictionGisUrl") if isinstance(block.get("jurisdictionGisUrl"), dict) else {}
    tax_status = str(row.get("taxStatus") or tax.get("status") or "")
    sale_status = str(row.get("saleStatus") or sales.get("status") or "")
    owner_status = str(row.get("ownerStatus") or owner.get("status") or "")
    tax_fields = [part.strip() for part in str(row.get("taxFields") or "").split(";") if part.strip()]
    if not tax_fields and isinstance(tax.get("valueFields"), list):
        tax_fields = [str(item) for item in tax.get("valueFields") if item]
    owner_field = str(row.get("ownerField") or owner.get("field") or "").strip()
    template = row.get("appraiserTemplate") if isinstance(row.get("appraiserTemplate"), str) else None
    if not template and isinstance(deep.get("template"), str):
        template = deep.get("template")
    gis_url = row.get("jurisdictionGisUrl") if isinstance(row.get("jurisdictionGisUrl"), str) else None
    if not gis_url and isinstance(gis.get("county"), str):
        gis_url = gis.get("county")
    verified = str(row.get("deepLinkVerification") or "").lower().startswith("verified")
    tax_rest = tax.get("restUrl") if isinstance(tax.get("restUrl"), str) else None
    parcel = parcel_layer(card) or {}
    parcel_rest = str(parcel.get("restUrl") or "")
    companion = None
    if tax_status == "REST" and tax_rest and nc.norm_source(tax_rest) != nc.norm_source(parcel_rest):
        companion = {"restUrl": tax_rest, "fields": tax_fields, "idField": str(parcel.get("fieldMap") and next(iter(parcel.get("fieldMap") or {"PARCEL_NO": "parcelId"})))}
        # The companion id is the tax layer's parcel id, named on the tax field map.
        tax_layers = [layer for layer in card.get("layers") or [] if layer.get("role") == "tax" and layer.get("restUrl")]
        if tax_layers:
            field_map = tax_layers[0].get("fieldMap") or {}
            for key, label in field_map.items():
                if label == "parcelId":
                    companion["idField"] = str(key)
                    break
    normalized_tax = "ok" if tax_status == "REST" else "gap"
    # Component deed prices and deed-book text are not a last-sale price or date.
    price_fields: list[str] = []
    date_fields: list[str] = []
    sale_note = str(sales.get("detail") or "")
    return {
        "present": True,
        "source": "rural-oz-pass2 csv",
        "taxStatus": normalized_tax,
        "taxFields": tax_fields if normalized_tax == "ok" else [],
        "taxFallback": None,
        "saleStatus": "ok" if sale_status == "REST" else ("partial" if "REST" in sale_status else "gap"),
        "priceFields": price_fields,
        "dateFields": date_fields,
        "saleNote": sale_note,
        "ownerStatus": "ok" if owner_status.startswith("REST") else "gap",
        "ownerFields": [owner_field] if owner_field and owner_status.startswith("REST") else [],
        "paTemplate": template,
        "paVerified": verified,
        "gis": gis_url,
        "aadtStations": None,
        "gaps": [],
        "companion": companion,
        "rawTax": tax_status,
        "rawSale": sale_status,
        "rawOwner": owner_status,
    }


def attribute_field_map(layer: dict, pass2: dict, available: set[str], id_field: str) -> dict[str, str]:
    field_map = nc.attribute_field_map(layer, pass2, available, id_field)
    if pass2.get("ownerStatus") != "ok":
        field_map = {key: label for key, label in field_map.items() if target_bucket(label) not in {"owner", "owner2"}}
    # Templates supply the appraiser link. Do not copy one sample URL from the layer.
    field_map = {key: label for key, label in field_map.items() if target_bucket(label) != "paUrl"}
    if pass2.get("rawSale") != "REST":
        field_map = {key: label for key, label in field_map.items() if target_bucket(label) != "salePrice"}
    return field_map


def resolve_acres_ga(url: str, acre_field: str, cast_hint: bool, extra: list[str], available: set[str], expected: int) -> tuple[str, float, bool, int, str | None]:
    where, scale, geometry, count, field = nc.resolve_acres(url, acre_field, cast_hint, extra, available, expected)
    lookup = {name.lower(): name for name in available}
    live = acre_field if acre_field in available else lookup.get((acre_field or "").lower())
    if live:
        acre_where = f"{live}>=5 AND {live}<=150"
        acre_count = nc.try_count(url, acre_where)
        if acre_count >= 50 and (scale != 1 or geometry):
            return acre_where, 1.0, False, acre_count, live
        if acre_count >= 50 and scale == 1 and not geometry:
            return where, scale, geometry, count, field
        if geometry and acre_count == 0:
            total = nc.try_count(url, "1=1") or count
            # Published acre text (for example "12.5 Ac") cannot be filtered in SQL.
            return "1=1", 1.0, False, total, live
    return where, scale, geometry, count, field


def fully_loaded(row: dict | None) -> bool:
    return nc.fully_loaded(row)


def existing_row(fips: str) -> dict | None:
    return nc.existing_row(fips)


_GA_CENTERS: dict[str, tuple[float, float]] | None = None


def georgia_centers() -> dict[str, tuple[float, float]]:
    global _GA_CENTERS
    if _GA_CENTERS is not None:
        return _GA_CENTERS
    data = json.loads(nc.CENSUS_COUNTIES.read_text())
    found: dict[str, tuple[float, float]] = {}
    for feature in data.get("features") or []:
        geoid = str((feature.get("properties") or {}).get("GEOID") or "")
        if not geoid.startswith("13"):
            continue
        center = nc.ring_centroid(feature.get("geometry") or {})
        if center:
            found[geoid] = center
    _GA_CENTERS = found
    return found


def nearest_shelf(fips: str) -> str:
    center = georgia_centers().get(fips)
    if not center:
        raise RuntimeError(f"{fips} has no Census county shape")
    return min(GA_SHELVES, key=lambda name: nc.haversine_km(center, GA_SHELVES[name]))


def markets_for(catalog: dict, fips: str) -> list[str]:
    return nc.markets_for(catalog, fips)


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
        by_market[market_id]["counties"].append({"name": name, "state": "Georgia", "fips": fips})


def gap_notes(item: dict, layer: dict, pass2: dict, source_count: int, kept: int, join_note: str | None) -> list[str]:
    acre_note = "Published acreage is filtered to 5.0–150.0 inclusive."
    if item.get("geometryAcres"):
        acre_note = "The parcel layer has no usable acre field, so acreage is geodesic polygon area, 5.0–150.0 inclusive."
    elif item.get("where") == "1=1" and item.get("acreField"):
        acre_note = f"Acreage is parsed from {item.get('acreField')} because the field is not numeric in SQL, then kept at 5.0–150.0 inclusive. Rows that do not parse use geodesic polygon area."
    notes = [
        f"Parcels are {layer.get('name') or 'the pass-1 parcel layer'} ({layer.get('restUrl')}). {acre_note} No Opportunity Zone status, school grade, or base flood elevation is stored.",
    ]
    if source_count and kept < source_count:
        notes.append(
            f"Source query returned {source_count} rows; {kept} distinct parcel ids stayed in the 5.0–150.0 acre band after the geometry check."
        )
    tax = pass2.get("rawTax") or "not stated"
    sale = pass2.get("rawSale") or "not stated"
    owner = pass2.get("rawOwner") or "not stated"
    notes.append(
        f"Pass 2 enrichment is from {pass2['source']} (tax {tax}, sale {sale}, owner {owner}). GDOT AADT stays the query-time statewide join."
    )
    if tax == "HTML-only":
        notes.append("Pass 2 tax is HTML-only. qPublic was not requested, and no tax value was copied from an HTML report.")
    if sale == "HTML-only":
        notes.append("Pass 2 sale is HTML-only. Zero-filled SALE_VAL columns are not stored as a sale price, and qPublic was not requested.")
    elif sale == "REST-partial":
        detail = pass2.get("saleNote") or "partial public sale fields"
        notes.append(f"Pass 2 sale is partial ({detail[:240]}). Deed book text and component prices are not stored as a last-sale price or date.")
    if owner == "HTML-only":
        notes.append("Pass 2 owner is HTML-only. Owner and mailing were not copied from an HTML report.")
    if join_note:
        notes.append(join_note)
    notes.append("Property-appraiser links are filled from the pass-2 template with each parcel id and were not requested. Owner phone and email are not ingested.")
    unique: list[str] = []
    for note in notes:
        if note and note not in unique:
            unique.append(note)
    return unique[:8]


def join_companion(features: list[dict], companion: dict) -> str | None:
    url = nc.query_url(str(companion["restUrl"]))
    id_field = str(companion.get("idField") or "PARCEL_NO")
    fields = [str(name) for name in companion.get("fields") or [] if name]
    out = [id_field, *fields, "MAILING_AD", "MAILING_CI", "MAILING_ST", "MAILING_ZI"]
    # Keep the request to fields the service is likely to have. Unknown names are harmless if we catch the error and retry.
    try:
        rows = nc.page_attributes(url, "1=1", [id_field, *fields])
    except Exception as exc:  # noqa: BLE001
        return f"Pass 2 tax companion did not answer ({exc})."
    index: dict[str, dict] = {}
    for row in rows:
        text = nc.integral_text(row.get(id_field))
        if text and text not in index:
            index[text] = row
    matched = 0
    valued = 0
    for feature in features:
        row = index.get(feature["properties"]["parcelId"])
        if not row:
            continue
        matched += 1
        tax = feature["properties"]["tax"]
        for name in fields:
            label = guess_tax_label(name)
            parsed = nc.money(row.get(name))
            if not label or parsed is None:
                continue
            slot = {"tax.marketValue": "marketValue", "tax.assessedValue": "assessedValue", "tax.taxableValue": "taxableValue", "tax.due": "taxes"}.get(label)
            if slot and tax.get(slot) is None:
                tax[slot] = parsed
                valued += 1
    return f"Tax values joined from {companion['restUrl']} on {id_field}: {matched} parcel ids matched, {valued} value fields filled."


def classify(cards: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    eligible: list[dict] = []
    skipped: list[dict] = []
    for row in pass_rows():
        fips = row["fips"]
        name = str(row.get("county") or fips)
        if int(row["order"]) <= 25:
            skipped.append({"fips": fips, "name": name, "reason": "pass-2 order 25 or lower is batch 1"})
            continue
        card = cards.get(fips)
        if not card:
            skipped.append({"fips": fips, "name": name, "reason": "no county card"})
            continue
        current = existing_row(fips)
        if fully_loaded(current):
            skipped.append(
                {
                    "fips": fips,
                    "name": name,
                    "reason": f"already a complete 5.0–150.0 acre extract ({int((current or {}).get('featureCount') or 0)} parcels)",
                    "queryUrl": (current or {}).get("queryUrl"),
                }
            )
            continue
        url = str(row.get("restUrl") or "")
        if not url:
            skipped.append({"fips": fips, "name": name, "reason": "pass 1 has no parcel REST url"})
            continue
        if PAID_VENDOR.search(url):
            skipped.append({"fips": fips, "name": name, "reason": "paid vendor endpoint"})
            continue
        layer = parcel_layer(card)
        if not layer:
            skipped.append({"fips": fips, "name": name, "reason": "card has no usable parcel layer"})
            continue
        id_field = str(row.get("parcelIdField") or "") or next(iter((layer.get("fieldMap") or {})), "")
        eligible.append(
            {
                "fips": fips,
                "name": name,
                "order": int(row["order"]),
                "url": url,
                "idField": id_field,
                "acreageRaw": str(layer.get("acreageField") or ""),
                "expected": acre_hint(card),
                "card": card,
                "passRow": row,
            }
        )
    return eligible, skipped


def probe_one(item: dict) -> dict:
    fips = item["fips"]
    try:
        url, meta = nc.open_service(nc.query_url(item["url"]))
        available = set(nc.field_names(meta))
        acre_name, cast_hint, extra = nc.acre_spec(item["acreageRaw"])
        layer = nc.choose_layer(item["card"], url, acre_name)
        where, scale, geometry, count, field = resolve_acres_ga(
            url, acre_name, cast_hint, extra, available, int(item["expected"] or 0)
        )
        lookup = {name.lower(): name for name in available}
        live_id = item["idField"] if item["idField"] in available else lookup.get(item["idField"].lower(), item["idField"])
        if live_id not in available:
            raise RuntimeError(f"parcel id field {item['idField']} is not on the layer")
        pass2 = load_pass2(item["card"], item["passRow"])
        log(f"SELECT {item['name']} {fips} rows {count} where {where[:80]} pass2 tax {pass2['rawTax']}")
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
        }
    except Exception as exc:  # noqa: BLE001
        log(f"SKIP {item['name']} {fips}: {exc}")
        return {**item, "ok": False, "reason": f"endpoint unreachable: {exc}"}


def pull_complete(
    url: str,
    where: str,
    out_fields: list[str],
    order_field: str | None,
    expected: int | None,
) -> list[dict]:
    """Page when returnIdsOnly comes back short of the count query."""
    ids: list[int] = []
    try:
        ids = seed.fetch_object_ids(url, where)
    except Exception as exc:  # noqa: BLE001
        log(f"    object ids failed ({exc}); paging")
        return nc.fetch_paged(url, where, out_fields, order_field, expected)
    if expected and ids and len(ids) < int(expected * 0.9):
        log(f"    object ids {len(ids)} short of {expected}; paging")
        return nc.fetch_paged(url, where, out_fields, order_field, expected)
    if not ids:
        return nc.fetch_paged(url, where, out_fields, order_field, expected)
    return seed.fetch_by_ids(url, ids, out_fields, batch=120)


def download_county(item: dict, markets: list[str], refresh: bool) -> dict:
    card = item["card"]
    fips = item["fips"]
    name = item["name"]
    layer = item["layer"]
    url = item["queryUrl"]
    pass2 = item["pass2"]
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    source = f"ga-{slug}-parcels-{fips}"
    county = {"name": name, "state": "Georgia", "fips": fips}
    links = nc.card_links(card, pass2)
    links["suppressOwner"] = nc.card_suppresses_owner(card)
    cache_path = CACHE_DIR / f"{fips}.json"
    nc.backup_county(fips)
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features:
            log(f"Pulling {name} {fips} cache {len(features)}")
            for feature in features:
                feature["properties"]["marketIds"] = markets
                feature["properties"]["state"] = "Georgia"
                nc.clear_future_sale(feature["properties"])
                nc.scrub(feature["properties"])
            nc.write_county(
                county,
                markets,
                features,
                source=source,
                url=cached.get("queryUrl") or url,
                gaps=cached.get("gaps") or [],
                source_count=int(cached.get("sourceCount") or len(features)),
                dropped=int(cached.get("dropped") or 0),
                links=links,
                expected=0,
            )
            return {
                "fips": fips,
                "name": name,
                "order": item["order"],
                "featureCount": len(features),
                "queryUrl": cached.get("queryUrl") or url,
                "markets": markets,
                "source": source,
                "pass2": pass2["source"],
            }
    log(f"Pulling {name} {fips} {url}")
    available = set(item["fields"])
    field_map = attribute_field_map(layer, pass2, available, item["idField"])
    acre_field = item.get("acreField")
    scale = float(item.get("acresScale") or 1)
    geometry_acres = bool(item.get("geometryAcres"))
    out_fields = nc.simple_sources(field_map, available)
    if acre_field and acre_field not in out_fields:
        out_fields.append(acre_field)
    field_lookup = {field_name.lower(): field_name for field_name in available}
    for field_name in nc.template_fields(links.get("template")):
        found = field_name if field_name in available else field_lookup.get(field_name.lower())
        if found and found not in out_fields and not re.search(r"phone|e-?mail|ssn", found, re.I):
            out_fields.append(found)
    for field_name in sorted(available):
        if nc.CONFIDENTIAL_FLAG.search(field_name) and not re.search(r"phone|e-?mail", field_name, re.I) and field_name not in out_fields:
            out_fields.append(field_name)
    for extra in ("firstname", "FIRSTNAME"):
        found = extra if extra in available else field_lookup.get(extra.lower())
        if found and found not in out_fields and pass2.get("ownerStatus") == "ok":
            out_fields.append(found)
    if item["idField"] not in out_fields:
        out_fields.append(item["idField"])
    raw = pull_complete(
        url,
        item["where"],
        out_fields,
        item["idField"],
        int(item.get("probeCount") or 0) or None,
    )
    features = []
    dropped = 0
    for raw_item in raw:
        feature = feature_from(
            raw_item.get("attributes") or {},
            raw_item.get("geometry"),
            card=card,
            name=name,
            field_map=field_map,
            markets=markets,
            source=source,
            acres_scale=scale,
            use_geometry_acres=geometry_acres,
            acre_field=None if geometry_acres else acre_field,
            links=links,
        )
        if feature is None:
            dropped += 1
            continue
        features.append(feature)
    features = nc.dedupe(features)
    join_note = None
    companion = pass2.get("companion")
    if companion:
        join_note = join_companion(features, companion)
    gaps = gap_notes(item, layer, pass2, int(item.get("probeCount") or len(features)), len(features), join_note)
    nc.write_county(
        county,
        markets,
        features,
        source=source,
        url=url,
        gaps=gaps,
        source_count=int(item.get("probeCount") or len(features)),
        dropped=dropped,
        links=links,
        expected=0,
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
        "order": item["order"],
        "featureCount": len(features),
        "queryUrl": url,
        "markets": markets,
        "source": source,
        "pass2": pass2["source"],
        "sourceCount": item.get("probeCount"),
        "tax": pass2.get("rawTax"),
        "sale": pass2.get("rawSale"),
        "owner": pass2.get("rawOwner"),
    }


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
    eligible, skipped = classify(cards)
    log(f"Eligible before probe: {len(eligible)}")
    wanted = {item.lower() for item in args.county}
    if wanted:
        eligible = [item for item in eligible if item["fips"] in wanted or item["name"].lower() in wanted]
    reachable: list[dict] = []
    cursor = 0
    while cursor < len(eligible):
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
                "order": item["order"],
                "fips": item["fips"],
                "name": item["name"],
                "queryUrl": item["queryUrl"],
                "probeCount": item.get("probeCount"),
                "where": item.get("where"),
                "geometryAcres": item.get("geometryAcres"),
                "acreField": item.get("acreField"),
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
    if not reachable:
        raise SystemExit("No reachable counties")
    catalog = json.loads(CATALOG_PATH.read_text())
    for item in reachable:
        item["markets"] = planned_markets(catalog, item["fips"])
        log(f"SHELF {item['name']} {item['fips']} -> {', '.join(item['markets'])}")
    kept: list[dict] = []
    index = 0
    while index < len(reachable):
        batch = reachable[index : index + max(1, args.workers)]
        index += len(batch)
        results: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=max(1, len(batch))) as pool:
            futures = {pool.submit(download_county, item, item["markets"], args.refresh): item for item in batch}
            for future in as_completed(futures):
                item = futures[future]
                try:
                    results[item["fips"]] = {"ok": True, "pulled": future.result()}
                except Exception as exc:  # noqa: BLE001
                    nc.restore_county(item["fips"])
                    log(f"FAILED {item['fips']}: {exc}")
                    results[item["fips"]] = {"ok": False, "error": str(exc)}
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
            kept.append(result["pulled"])
    if not kept:
        raise SystemExit("No counties downloaded")
    for item in kept:
        commit_markets(catalog, item["fips"], item["name"], item["markets"])
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    report = {"pulled": kept, "skipped": skipped}
    (CARDS / "batch2-result.json").write_text(json.dumps(report, indent=2) + "\n")
    if not args.skip_index:
        seed.rebuild_indexes(catalog)
    log("Done " + json.dumps([{k: item[k] for k in ("fips", "name", "featureCount", "markets")} for item in kept], indent=2))


if __name__ == "__main__":
    sys.exit(main())
