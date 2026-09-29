#!/usr/bin/env python3
"""5.0–150.0 acre parcels for Georgia rural Opportunity Zone batch 1.

Walks data/ga-parcel-cards/_rural-oz2-pass2-results-2026-09-28.csv in order.
A row is eligible when pass 1 is usable, or partial only when the card layer
is county-wide, and the repo does not already have a complete 5.0–150.0 acre
extract. Gap and blocked rows have no public county-wide parcel REST and are
not requested. If the live endpoint does not answer, that county is skipped
and the next row is used. The first 20 that download are written.

Does not add a market shelf. Counties already on a shelf stay there. Others
go on the nearest existing Georgia shelf (Atlanta, Savannah, Chattanooga,
Valdosta, Macon, or Athens), measured from the Census county shape to the
shelf city. A Georgia shelf is preferred over a nearer out-of-state shelf.
No Opportunity Zone status, school grade, or base flood elevation is stored.
Household income stays the ACS B19013_001E join. GDOT AADT stays off the
parcel. Property-appraiser URLs are copied from the pass-2 template and are
not requested. A sample parcel id is never copied onto every parcel. Owner
phone and email are not ingested. A confidential-owner flag suppresses owner
and mailing fields. Sale dates after the pull date are cleared.
"""

from __future__ import annotations

import argparse
import csv
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
from urllib.parse import quote

import yaml

import nc_rural_oz_batch1_parcels as nc
import seed_market_parcels as seed

ROOT = seed.ROOT
CATALOG_PATH = seed.CATALOG_PATH
CARDS = ROOT / "data" / "ga-parcel-cards"
PASS2_PATH = CARDS / "_rural-oz2-pass2-results-2026-09-28.csv"
PASS1_PATH = CARDS / "_rural-oz2-pass1-results-2026-09-28.csv"
CACHE_DIR = Path("/tmp/dls-ga-rural-oz-batch1")
CENSUS_COUNTIES = ROOT / "data" / "fixtures" / "census" / "cb_2024_us_county_5m.geojson"
TODAY = date.today().isoformat()
TARGET = 20
RESULT_PATH = CARDS / "batch1-result.json"
# West, south, east, north. Drops a wrong-state service that still returns polygons.
GA_BBOX = (-85.70, 30.20, -80.65, 35.10)
# Shelf city coordinates. Georgia shelves only. Chattanooga already holds
# northwest Georgia counties, so it is an existing shelf for this state.
GA_SHELVES = {
    "Atlanta": (-84.3880, 33.7490),
    "Savannah": (-81.0998, 32.0835),
    "Chattanooga": (-85.3097, 35.0456),
    "Valdosta": (-83.2785, 30.8327),
    "Macon": (-83.6324, 32.8407),
    "Athens": (-83.3576, 33.9519),
}
PAID_VENDOR = re.compile(r"regrid|reportall|qpublic", re.I)
CONFIDENTIAL_KEY = re.compile(
    r"confidential|hide_?name|owner_?hide|redact_?owner|suppress_?owner",
    re.I,
)
AFFIRMATIVE = {"y", "yes", "true", "t", "1"}
SALE_DATE_NAME = re.compile(r"(sale_?date|saledate|deed_?date|sale_?dt|last_?sale_?dt)$", re.I)
SALE_PRICE_NAME = re.compile(r"(sale_?price|saleprice|sale_?amt|saleamt|sale_?prc|salep)$", re.I)
SALE_YEAR_NAME = re.compile(r"(sale_?year|saleyear|saleyr|saley)$", re.I)

PRINT_LOCK = threading.Lock()
CENTER_LOCK = threading.Lock()
CENTERS: dict[str, tuple[float, float]] | None = None
BBOXES: dict[str, tuple[float, float, float, float]] | None = None

_orig_bucket = nc.target_bucket


def target_bucket(label: str) -> str | None:
    text = label.split("(")[0].strip()
    extra = {
        "situsNumber": "situsNum",
        "situsStreet": "situsStreet",
        "situsStreetType": "situsType",
        "acreageDeed": "acres",
        "acreageGis": "acres",
        "acreageAssessed": "acres",
    }
    if text in extra:
        return extra[text]
    return _orig_bucket(label)


nc.target_bucket = target_bucket


def log(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def load_cards() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for path in CARDS.glob("*.yaml"):
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict) or data.get("level") != "county":
            continue
        fips = str(data.get("fips") or "").zfill(5)
        if fips.startswith("13"):
            found[fips] = data
    return found


def pass1_index() -> dict[str, dict]:
    found: dict[str, dict] = {}
    with PASS1_PATH.open(newline="") as handle:
        for row in csv.DictReader(handle):
            fips = str(row.get("fips") or "").zfill(5)
            found[fips] = row
    return found


def pass2_rows() -> list[dict]:
    rows = []
    with PASS2_PATH.open(newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    rows.sort(key=lambda item: int(item["order"]))
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


def pass1_kind(status: str) -> str:
    text = (status or "").strip().lower()
    if text.startswith("gap") or text.startswith("blocked"):
        return "skip"
    if text.startswith("usable"):
        return "usable"
    if text == "partial":
        return "partial"
    return "skip"


def county_wide_layer(card: dict) -> dict | None:
    for layer in card.get("layers") or []:
        if not isinstance(layer, dict) or layer.get("role") != "parcels":
            continue
        url = layer.get("restUrl")
        if not isinstance(url, str) or not url.startswith("http"):
            continue
        coverage = str(layer.get("coverage") or "").lower()
        status = str(layer.get("status") or "").lower()
        if coverage == "county-wide" and status in {"usable", "partial"}:
            return layer
    return None


def choose_layer(card: dict, pass1_url: str) -> dict | None:
    layers = []
    for layer in card.get("layers") or []:
        if not isinstance(layer, dict) or layer.get("role") != "parcels":
            continue
        url = layer.get("restUrl")
        if not isinstance(url, str) or not url.startswith("http"):
            continue
        if str(layer.get("status") or "").lower() == "gap":
            continue
        layers.append(layer)
    target = nc.norm_source(pass1_url)
    for layer in layers:
        if target and nc.norm_source(str(layer.get("restUrl"))) == target:
            return layer
    wide = county_wide_layer(card)
    if wide:
        return wide
    return layers[0] if layers else None


def rest_yes(status: str) -> bool:
    return (status or "").strip().lower().startswith("rest")


def guess_ga_tax(field: str) -> str | None:
    raw = field.strip()
    name = re.sub(r"[^a-z0-9]", "", raw.lower())
    if not name or name.startswith("prev") or name in {"taxyear", "taxyr", "previousvalue"}:
        return None
    if "phone" in name or "email" in name:
        return None
    if "land" in raw.lower() or name in {"lndvalue", "landval", "landvalue"} or name.startswith("lndval"):
        return "tax.landValue"
    if any(token in raw.lower() for token in ("impr", "improv", "bldg", "build")) or name in {
        "impval",
        "impvalue",
        "imprvalue",
    }:
        return "tax.improvementValue"
    if "taxable" in raw.lower() or "txbl" in name:
        return "tax.taxableValue"
    if name in {"avalue", "aval"} or "assess" in raw.lower() or "assd" in raw.lower():
        return "tax.assessedValue"
    if name in {"currval", "currentvalue", "fairmarke", "fairmarket", "fmv", "totval", "totalvalue"} or "market" in raw.lower():
        return "tax.marketValue"
    if name in {"fmvres", "fmvacc", "fmvcom", "fmvagr", "fmvind"}:
        return "tax.fmvPart"
    return nc.guess_tax_label(field)


def attribute_field_map(layer: dict, pass2: dict, available: set[str], id_field: str) -> dict[str, str]:
    field_map = {key: nc.refine_label(key, label) for key, label in nc.mapped_fields(layer).items()}
    lookup = {name.lower(): name for name in available}

    def live(name: str) -> str | None:
        if name in available:
            return name
        return lookup.get(name.lower())

    if not rest_yes(pass2["taxStatus"]):
        field_map = {key: label for key, label in field_map.items() if not label.startswith("tax.")}
    else:
        wanted = {item.lower() for item in pass2["taxFields"]}
        kept = {}
        for key, label in field_map.items():
            if label.startswith("tax.") and key.lower() not in wanted and key.split("+")[0].lower() not in wanted:
                continue
            kept[key] = label
        field_map = kept
        market_fields = []
        fmv_parts = []
        for name in pass2["taxFields"]:
            label = guess_ga_tax(name)
            found = live(name)
            if not found or not label:
                continue
            if label == "tax.fmvPart":
                fmv_parts.append(found)
                continue
            if label == "tax.marketValue":
                market_fields.append(found)
            if found not in field_map:
                field_map[found] = label
        if fmv_parts and not market_fields:
            if len(fmv_parts) == 1:
                field_map[fmv_parts[0]] = "tax.marketValue"
            else:
                field_map["+".join(fmv_parts)] = "tax.marketValue"
    if not rest_yes(pass2["saleStatus"]):
        field_map = {key: label for key, label in field_map.items() if nc.target_bucket(label) not in {"salePrice", "saleDate", "saleYear", "saleMonth", "saleQualified"}}
    else:
        for name in available:
            if name in field_map or nc.BANNED_FIELD.search(name):
                continue
            if SALE_PRICE_NAME.search(name):
                field_map[name] = "lastSale.price"
            elif SALE_YEAR_NAME.search(name):
                field_map[name] = "lastSale.year"
            elif SALE_DATE_NAME.search(name):
                field_map[name] = "lastSale.date"
    if not rest_yes(pass2["ownerStatus"]):
        field_map = {key: label for key, label in field_map.items() if nc.target_bucket(label) not in {"owner", "owner2"}}
    else:
        for index, name in enumerate(pass2["ownerFields"]):
            found = live(name)
            if not found or nc.BANNED_FIELD.search(found):
                continue
            label = "ownerName" if index == 0 else "ownerName2"
            if found not in field_map:
                field_map[found] = label
    found_id = live(id_field)
    if found_id and found_id not in field_map:
        field_map[found_id] = "parcelId"
    return field_map


def card_confidential(card: dict) -> bool:
    for key in ("confidentialOwner", "suppressOwner", "ownerConfidential"):
        if card.get(key) in (True, "yes", "suppress", "true", "y"):
            return True
    for layer in card.get("layers") or []:
        if not isinstance(layer, dict) or layer.get("role") != "parcels":
            continue
        if layer.get("confidentialOwner") in (True, "yes", "suppress", "true", "y") or layer.get("suppressOwner") in (
            True,
            "yes",
            "suppress",
            "true",
            "y",
        ):
            return True
    return False


def row_confidential(attrs: dict) -> bool:
    for key, value in attrs.items():
        if not CONFIDENTIAL_KEY.search(str(key)):
            continue
        if str(value or "").strip().lower() in AFFIRMATIVE:
            return True
    return False


def suppress_owner(feature: dict) -> None:
    props = feature["properties"]
    props["ownerName"] = None
    props["ownerName2"] = None
    mail = props.get("mailingAddress") or {}
    for key in list(mail):
        mail[key] = None


def in_georgia(center: tuple[float, float] | None) -> bool:
    if not center or not seed.plausible_centroid(center):
        return False
    lon, lat = center
    west, south, east, north = GA_BBOX
    return west <= lon <= east and south <= lat <= north


def in_county_bbox(center: tuple[float, float] | None, box: tuple[float, float, float, float] | None) -> bool:
    if not center or not box:
        return False
    lon, lat = center
    west, south, east, north = box
    pad = 0.08
    return west - pad <= lon <= east + pad and south - pad <= lat <= north + pad


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
    county_box: tuple[float, float, float, float] | None,
) -> dict | None:
    geometry, computed = seed.rings_to_feature_geometry(geom)
    if not geometry:
        return None
    center = seed.centroid_of(geometry)
    if not in_georgia(center) or not in_county_bbox(center, county_box):
        return None
    mapped = nc.collect_mapped(attrs, field_map)
    acres = None
    if acre_field and not use_geometry_acres:
        acres = nc.parse_acres(nc.attr_get(attrs, acre_field))
        if acres is not None and acres_scale != 1:
            acres = acres / acres_scale
    if acres is None or acres <= 0:
        acres = mapped.get("acres")
        if isinstance(acres, (int, float)) and acres_scale != 1 and acres:
            acres = acres / acres_scale
    if use_geometry_acres or acres is None or acres <= 0:
        acres = computed
    if acres is None:
        return None
    acres = round(float(acres), 4)
    if not seed.in_band(acres):
        return None
    parcel_id = nc.integral_text(mapped.get("parcelId"))
    if not parcel_id:
        return None
    situs = mapped.get("situs")
    if not situs:
        parts = [mapped.get("situsNum"), mapped.get("situsStreet")]
        if mapped.get("situsType") and mapped.get("situsStreet"):
            parts = [mapped.get("situsNum"), f"{mapped.get('situsStreet')} {mapped.get('situsType')}"]
        situs = " ".join(part for part in parts if part) or None
    mail_city = mapped.get("mailCity")
    mail_state = mapped.get("mailState")
    mail_zip = seed.zip_str(mapped.get("mailZip"))
    if mapped.get("mailCityState") and not (mail_city and mail_state):
        city, state, zip_code = nc.split_city_state(mapped.get("mailCityState"))
        mail_city = mail_city or city
        mail_state = mail_state or state
        mail_zip = mail_zip or zip_code
    if mapped.get("mailCityStateZip") and not mail_city:
        city, state, zip_code = nc.split_city_state(mapped.get("mailCityStateZip"))
        mail_city = city
        mail_state = mail_state or state
        mail_zip = mail_zip or zip_code
    owner = mapped.get("owner")
    owner2 = mapped.get("owner2")
    if nc.sensitive_contact(owner) or (owner and owner.strip().upper() in {"CONFIDENTIAL", "OWNER CONFIDENTIAL"}):
        owner = None
    if nc.sensitive_contact(owner2):
        owner2 = None
    sale_date = mapped.get("saleDate")
    if not sale_date and mapped.get("saleYear"):
        sale_date = seed.sale_date(mapped.get("saleYear"), mapped.get("saleMonth"))
    market_value = mapped.get("market")
    feature = seed.empty_feature(
        fips=str(card.get("fips") or "").zfill(5),
        county=name,
        state="Georgia",
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
        market_value=market_value,
        assessed=mapped.get("assessed"),
        taxable=mapped.get("taxable"),
        mail1=mapped.get("mail1") if not nc.sensitive_contact(mapped.get("mail1")) else None,
        mail2=mapped.get("mail2") if not nc.sensitive_contact(mapped.get("mail2")) else None,
        mail_city=mail_city,
        mail_state=mail_state,
        mail_zip=mail_zip,
    )
    feature["properties"]["ownerName2"] = owner2
    if mapped.get("taxes"):
        feature["properties"]["tax"]["taxes"] = mapped["taxes"]
    if mapped.get("land"):
        feature["properties"]["tax"]["landValue"] = mapped["land"]
    if mapped.get("building"):
        feature["properties"]["tax"]["improvementValue"] = mapped["building"]
    key_field = links.get("keyField")
    key_value = nc.integral_text(nc.attr_get(attrs, key_field)) if key_field else None
    token_value = key_value or parcel_id
    feature["properties"]["appraiserUrl"] = appraiser_url(links.get("template"), attrs, parcel_id, token_value, links.get("sample"))
    if links.get("gis"):
        feature["properties"]["gisViewerUrl"] = links["gis"]
    if row_confidential(attrs) or card_confidential(card) or owner is None and row_name_confidential(attrs, field_map):
        suppress_owner(feature)
    nc.clear_future_sale(feature["properties"])
    nc.scrub(feature["properties"])
    return feature


def row_name_confidential(attrs: dict, field_map: dict[str, str]) -> bool:
    for key, label in field_map.items():
        if nc.target_bucket(label) not in {"owner", "owner2"}:
            continue
        text = seed.clean(nc.attr_get(attrs, key.split("+")[0]))
        if text and text.upper() in {"CONFIDENTIAL", "OWNER CONFIDENTIAL"}:
            return True
    return False


def appraiser_url(template: str | None, attrs: dict, parcel_id: str, token_value: str, sample: str | None) -> str | None:
    if not template or "{" not in template:
        return None
    url = nc.fill_template(template, attrs, token_value)
    if not url or "{" in url:
        return None
    sample_text = (sample or "").strip()
    if not sample_text:
        return url
    own = {parcel_id.strip(), token_value.strip()}
    if sample_text in own:
        return url
    encoded = quote(sample_text, safe="")
    if sample_text in url or encoded in url:
        return None
    return url


def clear_repeated_links(features: list[dict]) -> None:
    urls = [feature["properties"].get("appraiserUrl") for feature in features if feature["properties"].get("appraiserUrl")]
    if len(urls) > 10 and len(set(urls)) == 1:
        log("  cleared one repeated appraiser URL so a sample id is not copied onto every parcel")
        for feature in features:
            feature["properties"]["appraiserUrl"] = None


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
    county_box: tuple[float, float, float, float] | None,
    expected: int | None,
) -> tuple[list[dict], int]:
    raw = nc.pull_raw(url, where, out_fields, str(card.get("fips") or "").zfill(5), order_field, expected)
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
            county_box=county_box,
        )
        if feature is None:
            dropped += 1
            continue
        features.append(feature)
    features = nc.dedupe(features)
    clear_repeated_links(features)
    return features, dropped


def ring_points(geometry: dict):
    kind = geometry.get("type")
    if kind == "Polygon":
        for ring in geometry.get("coordinates") or []:
            yield from ring
    elif kind == "MultiPolygon":
        for part in geometry.get("coordinates") or []:
            for ring in part:
                yield from ring


def load_census() -> None:
    global CENTERS, BBOXES
    with CENTER_LOCK:
        if CENTERS is not None and BBOXES is not None:
            return
        data = json.loads(CENSUS_COUNTIES.read_text())
        centers: dict[str, tuple[float, float]] = {}
        boxes: dict[str, tuple[float, float, float, float]] = {}
        for feature in data.get("features") or []:
            geoid = str((feature.get("properties") or {}).get("GEOID") or "")
            if not geoid.startswith("13"):
                continue
            geometry = feature.get("geometry") or {}
            points = list(ring_points(geometry))
            if not points:
                continue
            west = min(point[0] for point in points)
            east = max(point[0] for point in points)
            south = min(point[1] for point in points)
            north = max(point[1] for point in points)
            boxes[geoid] = (west, south, east, north)
            center = nc.ring_centroid(geometry)
            if center:
                centers[geoid] = center
        CENTERS = centers
        BBOXES = boxes


def county_centers() -> dict[str, tuple[float, float]]:
    load_census()
    return CENTERS or {}


def county_bboxes() -> dict[str, tuple[float, float, float, float]]:
    load_census()
    return BBOXES or {}


def nearest_shelf(fips: str) -> str:
    center = county_centers().get(fips)
    if not center:
        raise RuntimeError(f"{fips} has no Census county shape")
    return min(GA_SHELVES, key=lambda name: nc.haversine_km(center, GA_SHELVES[name]))


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
        by_market[market_id]["counties"].append({"name": name, "state": "Georgia", "fips": fips})


def short_name(text: str) -> str:
    return re.sub(r"\s+County$", "", text).strip()


def load_pass2(row: dict, card: dict) -> dict[str, Any]:
    block = card.get("pass2_2026-09-28") if isinstance(card.get("pass2_2026-09-28"), dict) else {}
    app = block.get("appraiserSearchUrl") if isinstance(block.get("appraiserSearchUrl"), dict) else {}
    gis_block = block.get("jurisdictionGisUrl") if isinstance(block.get("jurisdictionGisUrl"), dict) else {}
    template = row.get("appraiserTemplate") or app.get("template")
    if isinstance(template, str) and "{" not in template:
        template = None
    gis = row.get("jurisdictionGisUrl") or gis_block.get("county") or card.get("jurisdictionGisUrl")
    key_field = app.get("parcelIdField")
    tax_fields = [item.strip() for item in (row.get("taxFields") or "").split(";") if item.strip()]
    owner_field = (row.get("ownerField") or "").strip()
    verification = (row.get("deepLinkVerification") or "").strip().lower()
    return {
        "taxStatus": row.get("taxStatus") or "",
        "taxFields": tax_fields,
        "saleStatus": row.get("saleStatus") or "",
        "ownerStatus": row.get("ownerStatus") or "",
        "ownerFields": [owner_field] if owner_field else [],
        "template": template if isinstance(template, str) else None,
        "sample": (row.get("sampleParcelId") or app.get("sampleParcelId") or "").strip(),
        "keyField": key_field.strip() if isinstance(key_field, str) and key_field.strip() else None,
        "gis": gis if isinstance(gis, str) and gis.startswith("http") else None,
        "verified": verification == "verified-by-source",
        "verification": verification,
        "aadtStations": row.get("aadtStations") or "",
    }


def gap_notes(layer: dict, pass2: dict, source_count: int, kept: int, distinct_note: str | None) -> list[str]:
    notes = [
        f"Parcels are {layer.get('name') or 'the pass-1 parcel layer'} ({layer.get('restUrl')}). Acreage is 5.0–150.0 inclusive. No Opportunity Zone status, school grade, or base flood elevation is stored.",
        "Household income stays the ACS B19013_001E tract join. GDOT AADT is not copied onto the parcel.",
    ]
    if source_count and kept < source_count:
        notes.append(
            f"Source query returned {source_count} rows; {kept} distinct parcel ids stayed in the 5.0–150.0 acre band after the geometry check."
        )
    if distinct_note:
        notes.append(distinct_note)
    tax = pass2["taxStatus"] or "not stated"
    sale = pass2["saleStatus"] or "not stated"
    owner = pass2["ownerStatus"] or "not stated"
    notes.append(f"Pass 2 tax is {tax}, sale is {sale}, and owner is {owner}. HTML-only values were not scraped.")
    if pass2["taxStatus"] and not rest_yes(pass2["taxStatus"]):
        notes.append("Pass 2 tax is HTML-only. Assessed value and tax bills were not copied off qPublic.")
    if pass2["saleStatus"] and not rest_yes(pass2["saleStatus"]):
        notes.append("Pass 2 sale date and price are HTML-only and were not copied.")
    if pass2["ownerStatus"] and not rest_yes(pass2["ownerStatus"]):
        notes.append("Pass 2 owner name is HTML-only and was not copied.")
    notes.append(
        "Property-appraiser links use each parcel id in the pass-2 template and were not requested. Owner phone and email are not ingested."
    )
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
    ids = [feature["properties"]["parcelId"] for feature in features]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{county['fips']} stored a repeated parcel id")
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
            "pulledOn": TODAY,
            "minAcres": 5.0,
            "maxAcres": 150.0,
        },
    )
    log(f"  kept {len(features)} distinct ids, tiles {tiles}")


def classify(cards: dict[str, dict], pass1: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    eligible: list[dict] = []
    skipped: list[dict] = []
    for row in pass2_rows():
        fips = str(row["fips"]).zfill(5)
        name = short_name(row["county"])
        order = int(row["order"])
        kind = pass1_kind(row.get("pass1") or "")
        card = cards.get(fips)
        if kind == "skip":
            skipped.append(
                {
                    "order": order,
                    "fips": fips,
                    "name": name,
                    "reason": f"pass1 {row.get('pass1')}: no public county-wide parcel REST",
                }
            )
            continue
        if not card:
            skipped.append({"order": order, "fips": fips, "name": name, "reason": "no county card"})
            continue
        if kind == "partial" and not county_wide_layer(card):
            skipped.append(
                {
                    "order": order,
                    "fips": fips,
                    "name": name,
                    "reason": "partial layer is not county-wide",
                }
            )
            continue
        current = existing_row(fips)
        if fully_loaded(current):
            skipped.append(
                {
                    "order": order,
                    "fips": fips,
                    "name": name,
                    "reason": f"already a complete 5.0–150.0 acre extract ({int((current or {}).get('featureCount') or 0)} parcels)",
                    "queryUrl": (current or {}).get("queryUrl"),
                }
            )
            continue
        if kind not in {"usable", "partial"}:
            skipped.append({"order": order, "fips": fips, "name": name, "reason": f"pass1 {row.get('pass1')}"})
            continue
        prior = pass1.get(fips) or {}
        url = prior.get("restUrl") or ""
        layer = choose_layer(card, url)
        if not layer:
            skipped.append({"order": order, "fips": fips, "name": name, "reason": "no public parcel layer on the card"})
            continue
        layer_url = str(layer.get("restUrl"))
        if PAID_VENDOR.search(layer_url):
            skipped.append({"order": order, "fips": fips, "name": name, "reason": "parcel endpoint is not public county GIS"})
            continue
        expected_raw = prior.get("count5to150ac") or layer.get("liveCount5to150ac") or ""
        try:
            expected = int(str(expected_raw).replace(",", "")) if str(expected_raw).strip() else 0
        except ValueError:
            expected = 0
        eligible.append(
            {
                "order": order,
                "fips": fips,
                "name": name,
                "card": card,
                "layer": layer,
                "url": layer_url,
                "idField": str(prior.get("parcelIdField") or layer.get("parcelIdField") or "Parcel_No"),
                "acreField": str(layer.get("acreageField") or ""),
                "expected": expected,
                "pass2": load_pass2(row, card),
                "pass1Status": row.get("pass1"),
            }
        )
    return eligible, skipped


def probe_one(item: dict) -> dict:
    fips = item["fips"]
    try:
        url, meta = nc.open_service(item["url"])
        if PAID_VENDOR.search(url):
            raise RuntimeError("parcel endpoint is not public county GIS")
        available = set(nc.field_names(meta))
        acre_name = item["acreField"]
        where, scale, geometry, count, field = nc.resolve_acres(url, acre_name, False, [], available, int(item["expected"] or 0))
        lookup = {name.lower(): name for name in available}
        live_id = item["idField"] if item["idField"] in available else lookup.get(item["idField"].lower(), item["idField"])
        if live_id not in available:
            raise RuntimeError(f"parcel id field {item['idField']} is not on the layer")
        key_field = item["pass2"].get("keyField")
        if key_field and key_field not in available and lookup.get(key_field.lower()):
            item["pass2"]["keyField"] = lookup[key_field.lower()]
        elif key_field and key_field not in available:
            item["pass2"]["keyField"] = live_id
        log(f"SELECT {item['name']} {fips} rows {count}")
        return {
            **item,
            "ok": True,
            "queryUrl": url,
            "where": where,
            "probeCount": count,
            "geometryAcres": geometry,
            "acresScale": scale,
            "acreField": field,
            "idField": live_id,
            "fields": sorted(available),
        }
    except Exception as exc:  # noqa: BLE001
        log(f"SKIP {item['name']} {fips}: {exc}")
        return {**item, "ok": False, "reason": f"endpoint unreachable: {exc}"}


def download_county(item: dict, markets: list[str], refresh: bool) -> dict:
    card = item["card"]
    fips = item["fips"]
    name = item["name"]
    layer = item["layer"]
    url = item["queryUrl"]
    pass2 = item["pass2"]
    source = f"ga-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}-parcels-{fips}"
    county = {"name": name, "state": "Georgia", "fips": fips}
    links = {
        "template": pass2.get("template"),
        "gis": pass2.get("gis"),
        "verified": pass2.get("verified"),
        "sample": pass2.get("sample"),
        "keyField": pass2.get("keyField") or item["idField"],
    }
    box = county_bboxes().get(fips)
    cache_path = CACHE_DIR / f"{fips}.json"
    backup_county(fips)
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features and (not item["expected"] or len(features) >= int(item["expected"] * 0.7)):
            log(f"Pulling {name} {fips} cache {len(features)}")
            for feature in features:
                feature["properties"]["marketIds"] = markets
                feature["properties"]["state"] = "Georgia"
                nc.clear_future_sale(feature["properties"])
                nc.scrub(feature["properties"])
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
            return pulled_row(item, len(features), cached.get("queryUrl") or url, markets, source)
    log(f"Pulling {name} {fips} {url}")
    available = set(item["fields"])
    field_map = attribute_field_map(layer, pass2, available, item["idField"])
    out_fields = nc.simple_sources(field_map, available)
    acre_field = item.get("acreField")
    if acre_field and acre_field not in out_fields:
        out_fields.append(acre_field)
    key_field = links.get("keyField")
    if key_field and key_field in available and key_field not in out_fields:
        out_fields.append(key_field)
    features, dropped = pull_features(
        url,
        item["where"],
        out_fields,
        card,
        name,
        field_map,
        markets,
        source,
        float(item.get("acresScale") or 1),
        bool(item.get("geometryAcres")),
        None if item.get("geometryAcres") else acre_field,
        links,
        item["idField"],
        box,
        int(item.get("probeCount") or item.get("expected") or 0) or None,
    )
    raw_count = int(item.get("probeCount") or len(features))
    distinct_note = None
    if raw_count and len(features) < raw_count:
        distinct_note = f"Counted {len(features)} distinct parcel ids."
    gaps = gap_notes(layer, pass2, raw_count, len(features), distinct_note)
    write_county(
        county,
        markets,
        features,
        source=source,
        url=url,
        gaps=gaps,
        source_count=raw_count,
        dropped=dropped,
        links=links,
        expected=int(item["expected"] or 0),
    )
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "sourceCount": raw_count,
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
    return pulled_row(item, len(features), url, markets, source, raw_count)


def pulled_row(item: dict, count: int, url: str, markets: list[str], source: str, source_count: int | None = None) -> dict:
    return {
        "order": item["order"],
        "fips": item["fips"],
        "name": item["name"],
        "featureCount": count,
        "queryUrl": url,
        "markets": markets,
        "shelf": markets[0] if markets else None,
        "source": source,
        "sourceCount": source_count if source_count is not None else item.get("probeCount"),
        "pass1": item.get("pass1Status"),
        "taxStatus": item["pass2"].get("taxStatus"),
        "saleStatus": item["pass2"].get("saleStatus"),
        "ownerStatus": item["pass2"].get("ownerStatus"),
        "appraiserSearchUrl": item["pass2"].get("template"),
        "gisViewerUrl": item["pass2"].get("gis"),
        "paLinkVerified": bool(item["pass2"].get("verified")),
    }


def remaining_usable(cards: dict[str, dict], pass1: dict[str, dict], pulled_fips: set[str]) -> int:
    count = 0
    for row in pass2_rows():
        fips = str(row["fips"]).zfill(5)
        if fips in pulled_fips:
            continue
        kind = pass1_kind(row.get("pass1") or "")
        card = cards.get(fips)
        if kind == "usable" or (kind == "partial" and card and county_wide_layer(card)):
            if not fully_loaded(existing_row(fips)):
                count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--indexes-only", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.indexes_only:
        catalog = json.loads(CATALOG_PATH.read_text())
        seed.rebuild_indexes(catalog)
        return
    cards = load_cards()
    pass1 = pass1_index()
    eligible, skipped = classify(cards, pass1)
    log(f"Eligible before probe: {len(eligible)}")
    reachable: list[dict] = []
    cursor = 0
    while cursor < len(eligible) and len(reachable) < TARGET + 8:
        window = eligible[cursor : cursor + max(1, args.workers)]
        cursor += len(window)
        with ThreadPoolExecutor(max_workers=max(1, len(window))) as pool:
            futures = {pool.submit(probe_one, item): item for item in window}
            done = [future.result() for future in as_completed(futures)]
        by_fips = {item["fips"]: item for item in done}
        for item in window:
            probed = by_fips[item["fips"]]
            if probed["ok"]:
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
                            "queryUrl": item.get("queryUrl"),
                            "where": item.get("where"),
                        }
                        for item in reachable
                    ],
                    "skipped": skipped,
                },
                indent=2,
            )
        )
        return
    catalog = json.loads(CATALOG_PATH.read_text())
    for item in reachable:
        item["markets"] = planned_markets(catalog, item["fips"])
        log(f"SHELF {item['name']} {item['fips']} -> {', '.join(item['markets'])}")
    kept: list[dict] = []
    index = 0
    while len(kept) < TARGET and index < len(reachable):
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
                    restore_county(item["fips"])
                    log(f"FAILED {item['fips']}: {exc}")
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
            if len(kept) < TARGET:
                kept.append(result["pulled"])
                continue
            restore_county(item["fips"])
            skipped.append({"order": item["order"], "fips": item["fips"], "name": item["name"], "reason": "batch already filled"})
    if len(kept) < TARGET:
        raise SystemExit(f"Only {len(kept)} counties downloaded")
    for item in kept:
        commit_markets(catalog, item["fips"], item["name"], item["markets"])
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    # The batch stops at the 20th download. The next pass-2 row is the first
    # order this run did not keep. Ineligible rows at or before that point
    # were already decided and stay skipped.
    kept_orders = {item["order"] for item in kept}
    last_kept = max(kept_orders)
    next_order = None
    for row in pass2_rows():
        order = int(row["order"])
        if order > last_kept:
            next_order = order
            break
    pulled_fips = {item["fips"] for item in kept}
    # Recount after writes so freshly completed counties are not "remaining".
    report = {
        "pulled": kept,
        "skipped": skipped,
        "nextOrder": next_order,
        "remainingUsable": remaining_usable(cards, pass1, pulled_fips),
        "pulledOn": TODAY,
        "totalParcels": sum(item["featureCount"] for item in kept),
    }
    RESULT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    if not args.skip_index:
        seed.rebuild_indexes(catalog)
    log("Done " + json.dumps({"counties": len(kept), "parcels": report["totalParcels"], "nextOrder": next_order}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
