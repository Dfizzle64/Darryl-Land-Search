#!/usr/bin/env python3
"""5.0–150.0 acre parcels for Florida rural OZ batch 2 (20 counties).

Same tile writer as batch 1 (0.25° grid, origin lon -83 / lat 27).
Does not add a market, switch markets, or store an Opportunity Zone status.
AADT stays the query-time FDOT join. Income stays ACS B19013_001E.

Counties already on the card endpoint at the card count are not re-downloaded.
Their appraiser and GIS links are filled from the card. These are replaced or
added from the card:

- Bay: TEST_Parcels/1 (the Hosted 2022 snapshot is not the source)
- Walton: EnerGov/4 GIS_ACRES (the previous extract was short)
- Putnam and Okeechobee: county polygons, acreage from FDOR LND_SQFOOT
- Columbia: Parcels_and_Addresses/2
- Jackson, Gadsden, Calhoun, Liberty: FDOR 2025 polygons in 0.1° tiles
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any

import seed_market_parcels as seed
from parcel_geometry import esri_rings_to_geojson

ROOT = seed.ROOT
CATALOG_PATH = seed.CATALOG_PATH
CACHE_DIR = Path("/tmp/dls-rural-oz-batch2")
FDOR_URL = (
    "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/"
    "Florida_Statewide_Cadastral/FeatureServer/0/query"
)
MIN_SQFT = 217800
MAX_SQFT = 6534000
TODAY = date.today().isoformat()
MONROE_CERT = Path(__file__).resolve().parent / "certs" / "digicert-global-g2-tls-rsa-sha256-2020-ca1.pem"
CENSUS_COUNTIES = ROOT / "data" / "fixtures" / "census" / "cb_2024_us_county_5m.geojson"

# Already on the card service, at the card count. Geometry is left in place.
KEEP_FIPS = {
    "12009",
    "12019",
    "12021",
    "12043",
    "12049",
    "12051",
    "12055",
    "12061",
    "12087",
    "12091",
    "12113",
}

ADD_TO_MARKET = {
    "Big Bend": [
        {"name": "Jackson", "state": "Florida", "fips": "12063"},
        {"name": "Calhoun", "state": "Florida", "fips": "12013"},
        {"name": "Liberty", "state": "Florida", "fips": "12077"},
    ],
    "North-Central Florida": [
        {"name": "Columbia", "state": "Florida", "fips": "12023"},
    ],
}

SECTION_FOR_NEW = {
    "12013": "Big Bend",
    "12023": "North-Central Florida",
    "12063": "Big Bend",
    "12077": "Big Bend",
}

# Appraiser template uses {id}. paVerified false means the pattern is stored
# and is not fetched during the build.
LINKS: dict[str, dict[str, Any]] = {
    "12005": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=834&PageTypeID=4&KeyValue={id}",
        "gis": "https://gis.baycountyfl.gov/bayview/",
        "paVerified": False,
    },
    "12009": {
        "appraiser": "https://www.bcpao.us/PropertySearch/#/account/{id}",
        "gis": "https://www.bcpao.us/map/",
        "paVerified": True,
        "id": "taxacct",
    },
    "12013": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=829&LayerID=15004&PageTypeID=4&PageID=6748&KeyValue={id}",
        "gis": "https://qpublic.schneidercorp.com/Application.aspx?AppID=829&LayerID=15004&PageTypeID=2&PageID=6748",
        "paVerified": False,
    },
    "12019": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=830&LayerID=15008&PageTypeID=4&PageID=6756&KeyValue={id}",
        "gis": "https://maps.claycountygov.com/clayview/",
        "paVerified": False,
    },
    "12021": {
        "appraiser": "https://www.collierappraiser.com/Main_Search/RecordDetail.html?FolioID={id}",
        "gis": "https://maps.collierappraiser.com/",
        "paVerified": False,
    },
    "12023": {
        "appraiser": "https://www.columbiacountyfla.com/ParcelDetails.aspx?ParcelNo={id}",
        "gis": "https://search.ccpafl.com/map/",
        "paVerified": True,
    },
    "12039": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=814&LayerID=14537&PageTypeID=4&KeyValue={id}",
        "gis": "https://qpublic.schneidercorp.com/Application.aspx?App=GadsdenCountyFL&PageType=Search",
        "paVerified": False,
    },
    "12043": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=818&LayerID=14562&PageTypeID=4&PageID=6420&KeyValue={id}",
        "gis": "https://experience.arcgis.com/experience/23cc21eddb2f40d897ed5c296e895d08",
        "paVerified": False,
    },
    "12049": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=813&LayerID=14471&PageTypeID=4&PageID=6254&KeyValue={id}",
        "gis": "https://experience.arcgis.com/experience/991bd3fbd52b4ea48fda046422d63283",
        "paVerified": False,
    },
    "12051": {
        "appraiser": None,
        "gis": "https://gis.hendryfla.net/",
        "paVerified": False,
    },
    "12055": {
        "appraiser": "https://www.hcpao.org/Search/Parcel/{id}",
        "gis": "https://www.hcpao.org/gis/",
        "paVerified": True,
        "id": "strap",
    },
    "12061": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=1109&PageTypeID=4&KeyValue={id}",
        "gis": "https://ircgis.maps.arcgis.com/home/index.html",
        "paVerified": False,
    },
    "12063": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=851&LayerID=15884&PageTypeID=4&PageID=7081&KeyValue={id}",
        "gis": "https://qpublic.schneidercorp.com/Application.aspx?AppID=851&LayerID=15884&PageTypeID=2&PageID=7081",
        "paVerified": False,
    },
    "12077": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=828&LayerID=15003&PageTypeID=4&PageID=13691&KeyValue={id}",
        "gis": "https://qpublic.schneidercorp.com/Application.aspx?AppID=828&LayerID=15003&PageTypeID=2&PageID=13691",
        "paVerified": False,
    },
    "12087": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=605&LayerID=9946&PageTypeID=4&PageID=7635&KeyValue={id}",
        "gis": "https://experience.arcgis.com/experience/258386d78ff64749be0acbfdb81d3e85",
        "paVerified": False,
    },
    "12091": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=855&LayerID=15999&PageTypeID=4&KeyValue={id}",
        "gis": "https://webgis.myokaloosa.com/webgis/",
        "paVerified": False,
    },
    "12093": {
        "appraiser": "https://www.okeechobeepa.com/gis/?pin={id}",
        "gis": "https://www.okeechobeegis.com/gis/",
        "paVerified": True,
        "id": "nodash",
    },
    "12107": {
        "appraiser": "https://apps.putnam-fl.com/pa/property/?type=api&parcel={id}",
        "gis": "https://pamap.putnam-fl.gov/PropertyAppraiserPublicMap/",
        "paVerified": True,
    },
    "12113": {
        "appraiser": None,
        "gis": "https://map.srcpa.gov/",
        "paVerified": False,
    },
    "12131": {
        "appraiser": "https://beacon.schneidercorp.com/Application.aspx?AppID=835&LayerID=15172&PageTypeID=4&KeyValue={id}",
        "gis": "https://experience.arcgis.com/experience/9ec6ea2db6424876ac7ba73a85b6fede",
        "paVerified": False,
    },
}

GAP_NOTES: dict[str, list[str]] = {
    "12005": [
        "Bay parcels are TEST_Parcels/FeatureServer/1 (DTAXACRES 5.0–150.0). The layer is queried only; it advertises public edits and is not written. Hosted/Parcels is the 2022 snapshot and is not this extract.",
        "FDOR joins need CO_NO=13 and A1RENUM with '-' removed. No Opportunity Zone status is stored.",
    ],
    "12009": [
        "FDOR joins need CO_NO=15 and PARCEL_ID exactly, including spaces, dashes, and '*'. The property-appraiser account is TaxAcct, not PARCEL_ID.",
    ],
    "12013": [
        "Calhoun polygons are FDOR Cadastral 2025, CO_NO=17, LND_SQFOOT 217800–6534000, fetched in 0.1° tiles. MIL1 2023 is not the polygon source.",
        "FDOR joins need CO_NO=17 and PARCEL_ID exactly. Placeholder ids such as WATER are dropped. No Opportunity Zone status is stored.",
    ],
    "12019": [
        "FDOR joins need CO_NO=20 and PIN_DSP (dashed section-township-range). The stored parcel id is the short PIN. PIN_DSP is not the parcel id.",
    ],
    "12021": [
        "Collier acreage is CAST(TOTALACRES AS FLOAT) on Parcels/FeatureServer/42. A numeric compare of the string field is not the filter. ParcelJoin/0 is dead and is not queried.",
        "FDOR joins need CO_NO=21 and FOLIO exactly, with leading zeros kept.",
    ],
    "12023": [
        "Columbia parcels are Parcels_and_Addresses/MapServer/2. Acreage is Acres, 5.0–150.0 inclusive.",
        "FDOR joins need CO_NO=22 and ParcelNo with '-' removed. Just value and the roll sale come from that FDOR row. No Opportunity Zone status is stored.",
    ],
    "12039": [
        "Gadsden polygons are FDOR Cadastral 2025, CO_NO=30, LND_SQFOOT 217800–6534000, fetched in 0.1° tiles. The county Gadsden_GIS_Feature_Layers service was rejected (duplicated and incomplete). MIL1 2023 is not the polygon source.",
        "FDOR joins need CO_NO=30 and PARCEL_ID exactly. No Opportunity Zone status is stored.",
    ],
    "12043": [
        "FDOR joins need CO_NO=32 and PARCELNO with '-' removed. The dashed PARCELNO does not match FDOR.",
    ],
    "12049": [
        "The parcel id is PIN_DSP. The field named PARCEL_ID is an HTML link and is not ingested.",
        "FDOR joins need CO_NO=35 and PIN_DSP with '-' removed.",
    ],
    "12051": [
        "Hendry does not ingest SSN1, SSN2, SS1CD, SS2CD, or CONFD. Owner phone and email are not ingested.",
        "FDOR joins need CO_NO=36 and PARCELNO exactly, including spaces, the dash, and the dot.",
    ],
    "12055": [
        "FDOR joins need CO_NO=38 and PARCELNO exactly. STRAP is a different key and is only the property-appraiser link.",
    ],
    "12061": [
        "FDOR joins need CO_NO=41 and PP_PIN exactly, including the trailing '.0'.",
    ],
    "12063": [
        "Jackson polygons are FDOR Cadastral 2025, CO_NO=42, LND_SQFOOT 217800–6534000, fetched in 0.1° tiles. No newer public county or property-appraiser parcel service was on the card. MIL1 2023 is not the polygon source.",
        "FDOR joins need CO_NO=42 and PARCEL_ID exactly. No Opportunity Zone status is stored.",
    ],
    "12077": [
        "Liberty polygons are FDOR Cadastral 2025, CO_NO=49, LND_SQFOOT 217800–6534000, fetched in 0.1° tiles. MIL1 2023 is not the polygon source.",
        "FDOR joins need CO_NO=49 and PARCEL_ID exactly. Multi-ring parcels are joined by id. No Opportunity Zone status is stored.",
    ],
    "12087": [
        "Monroe is mcgis4 Parcels/MapServer/0. The host sends only the leaf certificate, so reads use the pinned DigiCert Global G2 TLS RSA SHA256 2020 CA1 intermediate in scripts/certs. An unverified TLS context is not used.",
        "FDOR joins need CO_NO=54 and PARCEL_ID = SEC+TWP+' '+RNG+' '+RECHAR with '-' removed from RECHAR. Acreage is the polygon area, 5.0–150.0 inclusive. Shape.STArea() is rejected in the where clause, and AREA1 is not the stored acreage.",
    ],
    "12091": [
        "FDOR joins need CO_NO=56 and PATPCL_PIN with '-' removed. PATPCL_STRAP is a different key and is not the FDOR id.",
        "Sale dates after the load date are cleared. Owner phone and email are not ingested.",
    ],
    "12093": [
        "Okeechobee polygons are Tyler Display_Map/FeatureServer/2. Acreage is FDOR 2025 LND_SQFOOT / 43560 for CO_NO=57, not Shape__Area.",
        "FDOR joins need CO_NO=57 and trim(ParcelID) with '-' removed. Owner and mailing fields are omitted when the confidential column is populated. Owner phone and email are not ingested.",
    ],
    "12107": [
        "Putnam has no acreage on the property-appraiser layer. Acreage is FDOR 2025 LND_SQFOOT / 43560 for CO_NO=64.",
        "FDOR joins need CO_NO=64 and trim(PARCELID). Blank ids and '<New parcel>' placeholders are dropped. No Opportunity Zone status is stored.",
    ],
    "12113": [
        "Santa Rosa Basemap/1 is one row per address. The extract is deduped on Parcel. Acreage 5.0–150.0 is the distinct Parcel count.",
        "FDOR joins need CO_NO=67 and the dashed Parcel. ParNum with the dashes removed does not match. The field named ParcelID is the object id and is not the parcel id.",
    ],
    "12131": [
        "Walton parcels are EnerGov/FeatureServer/4. Acreage is GIS_ACRES, 5.0–150.0 inclusive. The object id field is OBJECTID_1.",
        "FDOR joins need CO_NO=76 and PARCELNO with '-' removed. Sale price is the FDOR roll price. Sale dates after the load date are cleared. No Opportunity Zone status is stored.",
    ],
}

FDOR_FIELDS = [
    "PARCEL_ID",
    "CO_NO",
    "LND_SQFOOT",
    "OWN_NAME",
    "OWN_ADDR1",
    "OWN_ADDR2",
    "OWN_CITY",
    "OWN_STATE",
    "OWN_ZIPCD",
    "JV",
    "AV_SD",
    "TV_SD",
    "DOR_UC",
    "SALE_PRC1",
    "SALE_YR1",
    "SALE_MO1",
    "QUAL_CD1",
    "PHY_ADDR1",
    "PHY_CITY",
    "PHY_ZIPCD",
]

SPECS: dict[str, dict] = {
    "12005": {
        "kind": "arcgis",
        "name": "Bay",
        "fips": "12005",
        "url": "https://gis.baycountyfl.gov/arcgis/rest/services/TEST_Parcels/FeatureServer/1/query",
        "where": "DTAXACRES>=5 AND DTAXACRES<=150",
        "outFields": [
            "A1RENUM",
            "DTAXACRES",
            "A2OWNAME",
            "DSITEADDR",
            "SALE1DATE",
            "SALE1PRADJ",
            "SALE1QU_VI",
            "VASJUST",
            "VASTOTAL",
            "VASTAXABLE",
            "DORAPPCODE",
            "A3MAILADDR",
            "A4MAILADDR",
            "A6MAILCITY",
            "A7MAILST",
            "A8MAILZIP",
        ],
        "idField": "A1RENUM",
        "acresField": "DTAXACRES",
        "ownerField": "A2OWNAME",
        "situsField": "DSITEADDR",
        "dorField": "DORAPPCODE",
        "salePriceField": "SALE1PRADJ",
        "saleDateField": "SALE1DATE",
        "marketValueField": "VASJUST",
        "assessedField": "VASTOTAL",
        "taxableField": "VASTAXABLE",
        "mail1Field": "A3MAILADDR",
        "mail2Field": "A4MAILADDR",
        "mailCityField": "A6MAILCITY",
        "mailStateField": "A7MAILST",
        "mailZipField": "A8MAILZIP",
        "source": "fl-bay-test-parcels-12005",
        "coverage": "complete-gte-5ac",
    },
    "12023": {
        "kind": "columbia",
        "name": "Columbia",
        "fips": "12023",
        "url": "https://gis.columbiacountyfla.com/hosting/rest/services/Parcels_and_Addresses/MapServer/2/query",
        "where": "Acres>=5 AND Acres<=150",
        "outFields": ["ParcelNo", "Acres", "Owner", "Url"],
        "idField": "ParcelNo",
        "acresField": "Acres",
        "ownerField": "Owner",
        "source": "fl-columbia-parcels-12023",
        "coverage": "complete-gte-5ac",
        "fdorCo": 22,
        "fdorKey": "dash",
    },
    "12131": {
        "kind": "walton",
        "name": "Walton",
        "fips": "12131",
        "url": "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/arcgis/rest/services/EnerGov/FeatureServer/4/query",
        "where": "GIS_ACRES>=5 AND GIS_ACRES<=150",
        "outFields": [
            "PARCELNO",
            "GIS_ACRES",
            "OWNER_NAME",
            "OWN_ADDRESS_1",
            "OWN_ADDRESS_2",
            "OWN_CITY",
            "OWN_STATE",
            "OWN_ZIPCODE",
            "SALE_DATE_1",
            "JUST_VALUE",
            "APPRAISED_VALUE",
            "USE_CODE",
        ],
        "idField": "PARCELNO",
        "acresField": "GIS_ACRES",
        "ownerField": "OWNER_NAME",
        "dorField": "USE_CODE",
        "saleDateField": "SALE_DATE_1",
        "marketValueField": "JUST_VALUE",
        "assessedField": "APPRAISED_VALUE",
        "mail1Field": "OWN_ADDRESS_1",
        "mail2Field": "OWN_ADDRESS_2",
        "mailCityField": "OWN_CITY",
        "mailStateField": "OWN_STATE",
        "mailZipField": "OWN_ZIPCODE",
        "source": "fl-walton-energov-12131",
        "coverage": "complete-gte-5ac",
        "fdorCo": 76,
        "fdorKey": "dash",
    },
    "12013": {"kind": "fdor", "name": "Calhoun", "fips": "12013", "co": 17, "source": "fl-fdor-cadastral-2025-12013"},
    "12039": {"kind": "fdor", "name": "Gadsden", "fips": "12039", "co": 30, "source": "fl-fdor-cadastral-2025-12039"},
    "12063": {"kind": "fdor", "name": "Jackson", "fips": "12063", "co": 42, "source": "fl-fdor-cadastral-2025-12063"},
    "12077": {"kind": "fdor", "name": "Liberty", "fips": "12077", "co": 49, "source": "fl-fdor-cadastral-2025-12077"},
    "12093": {
        "kind": "okee",
        "name": "Okeechobee",
        "fips": "12093",
        "co": 57,
        "url": "https://services3.arcgis.com/jE4lvuOFtdtz6Lbl/arcgis/rest/services/Tyler_Technologies_Display_Map/FeatureServer/2/query",
        "source": "fl-okeechobee-tyler-12093",
    },
    "12107": {
        "kind": "putnam",
        "name": "Putnam",
        "fips": "12107",
        "co": 64,
        "url": "https://pamap.putnam-fl.gov/server/rest/services/CadastralData/FeatureServer/2/query",
        "primary": "https://pamap.putnam-fl.gov/server/rest/services/CadastralData/FeatureServer/2/query",
        "twin": "https://gis.putnam-fl.com/arcserver/rest/services/Parcels_PA/FeatureServer/0/query",
        "source": "fl-putnam-parcels-pa-12107",
    },
}


def meaningful(value: Any) -> str | None:
    text = seed.clean(value)
    if not text:
        return None
    if text.upper() in {"*", "0", "0.0", "N/A", "NA", "NULL", "NONE", "N_A", "NAN"}:
        return None
    return text


def usable_parcel_id(value: Any) -> str | None:
    text = meaningful(value)
    if not text or text in {"?", "-", ".", "0"}:
        return None
    if text[0] in "*?":
        return None
    upper = text.upper()
    if upper in {"NULL", "NONE", "N/A", "NA", "WATER"} or "MULTI OWNER" in upper or "NEW PARCEL" in upper:
        return None
    if not any(ch.isalnum() for ch in text):
        return None
    return text


def dash_strip(value: str) -> str:
    return value.replace("-", "")


def nodash(value: str) -> str:
    return re.sub(r"[\s-]", "", value)


def quote_id(value: str) -> str:
    return urllib.parse.quote(value, safe="-._")


def apply_template(template: str | None, parcel_id: str) -> str | None:
    if not template or not parcel_id:
        return None
    return template.replace("{id}", quote_id(parcel_id))


def sale_iso(value: Any) -> str | None:
    text = meaningful(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if re.fullmatch(r"20\d{6}", digits) and len(text) <= 10:
        year, month, day = int(digits[0:4]), int(digits[4:6]), int(digits[6:8])
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
    parsed = seed.epoch_to_iso(value)
    if parsed:
        return parsed
    parsed = seed.text_date(text)
    if parsed:
        return parsed
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[:10]):
        return text[:10]
    return None


def clear_future_sale(props: dict) -> None:
    sale = props.get("lastSale") or {}
    sold = sale_iso(sale.get("date"))
    sale["date"] = sold
    if sold and sold > TODAY:
        sale["date"] = None
        sale["price"] = None
        sale["qualified"] = None
    props["lastSale"] = sale


def sanitize(features: list[dict]) -> None:
    for feature in features:
        props = feature["properties"]
        if props.get("situsAddress") in {"0", "0.0", "*"}:
            props["situsAddress"] = None
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        props["nearestRoad"] = None
        clear_future_sale(props)
        # Owner phone and email are never stored. Drop them if a source adds them later.
        for key in list(props):
            if re.search(r"phone|email", key, re.I):
                props.pop(key, None)


def attach_links(feature: dict, parcel_key: str | None = None) -> None:
    props = feature["properties"]
    link = LINKS[props["countyFips"]]
    gis = link.get("gis")
    if gis:
        props["gisViewerUrl"] = gis
    token = parcel_key or props.get("parcelId")
    mode = link.get("id")
    if mode == "nodash" and token:
        token = nodash(str(token))
    url = apply_template(link.get("appraiser"), str(token)) if token else None
    if url:
        props["appraiserUrl"] = url


def markets_for(catalog: dict, fips: str) -> list[str]:
    found: list[str] = []
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips and market["id"] not in found:
                found.append(market["id"])
    return found


def ensure_catalog(catalog: dict) -> dict:
    by_market = {market["id"]: market for market in catalog["markets"]}
    for market_id, additions in ADD_TO_MARKET.items():
        market = by_market[market_id]
        present = {county["fips"] for county in market["counties"]}
        for county in additions:
            if county["fips"] not in present:
                market["counties"].append(county)
                present.add(county["fips"])
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    return catalog


def county_dict(catalog: dict, fips: str, name: str) -> dict:
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips:
                return county
    return {"name": name, "state": "Florida", "fips": fips}


def county_bbox(fips: str) -> tuple[float, float, float, float]:
    data = json.loads(CENSUS_COUNTIES.read_text())
    for feature in data["features"]:
        props = feature.get("properties") or {}
        geoid = str(props.get("GEOID") or "").zfill(5)
        if geoid != fips:
            continue
        bounds = [180.0, 90.0, -180.0, -90.0]
        stack = [feature.get("geometry", {}).get("coordinates")]
        while stack:
            coords = stack.pop()
            if not isinstance(coords, list):
                continue
            if coords and isinstance(coords[0], (int, float)):
                bounds[0] = min(bounds[0], coords[0])
                bounds[1] = min(bounds[1], coords[1])
                bounds[2] = max(bounds[2], coords[0])
                bounds[3] = max(bounds[3], coords[1])
            else:
                stack.extend(coords)
        pad = 0.08
        return bounds[0] - pad, bounds[1] - pad, bounds[2] + pad, bounds[3] + pad
    raise RuntimeError(f"No census bbox for {fips}")


def iter_cells(bbox: tuple[float, float, float, float], step: float = 0.1):
    west, south, east, north = bbox
    x = west
    while x < east - 1e-9:
        y = south
        while y < north - 1e-9:
            yield x, y, min(x + step, east), min(y + step, north)
            y += step
        x += step


def fdor_where(co_no: int) -> str:
    return f"CO_NO={int(co_no)} AND LND_SQFOOT>={MIN_SQFT} AND LND_SQFOOT<={MAX_SQFT}"


def fdor_ids_cell(co_no: int, west: float, south: float, east: float, north: float, depth: int = 0) -> list[int]:
    geom = json.dumps(
        {"xmin": west, "ymin": south, "xmax": east, "ymax": north, "spatialReference": {"wkid": 4326}}
    )
    try:
        data = seed.fetch_json(
            FDOR_URL,
            {
                "where": fdor_where(co_no),
                "geometry": geom,
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "returnIdsOnly": "true",
                "f": "json",
            },
            timeout=120,
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:200])
        oids = data.get("objectIds")
        if oids is None:
            raise RuntimeError("objectIds null")
        return [int(i) for i in oids]
    except Exception as exc:  # noqa: BLE001
        if depth >= 3 or (east - west) < 0.03:
            print(f"  FDOR cell skip {west:.2f},{south:.2f} ({exc})", flush=True)
            return []
        mid_x = (west + east) / 2
        mid_y = (south + north) / 2
        parts = [
            (west, south, mid_x, mid_y),
            (mid_x, south, east, mid_y),
            (west, mid_y, mid_x, north),
            (mid_x, mid_y, east, north),
        ]
        found: list[int] = []
        for part in parts:
            found.extend(fdor_ids_cell(co_no, *part, depth + 1))
        return found


def fdor_ids(co_no: int, bbox: tuple[float, float, float, float]) -> list[int]:
    cells = list(iter_cells(bbox))
    print(f"  FDOR CO_NO={co_no} cells {len(cells)}", flush=True)
    found: set[int] = set()
    workers = 4
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fdor_ids_cell, co_no, *cell) for cell in cells]
        done = 0
        for future in as_completed(futures):
            found.update(future.result())
            done += 1
            if done % 8 == 0 or done == len(cells):
                print(f"  FDOR cells {done}/{len(cells)} ids {len(found)}", flush=True)
    return sorted(found)


def fdor_features(co_no: int, bbox: tuple[float, float, float, float], geometry: bool) -> list[dict]:
    cache_path = CACHE_DIR / f"fdor-{co_no}-{'geom' if geometry else 'attr'}.json"
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        print(f"  FDOR cache {co_no} {len(cached)}", flush=True)
        return cached
    ids = fdor_ids(co_no, bbox)
    print(f"  FDOR ids {len(ids)}", flush=True)
    raw = seed.fetch_by_ids(FDOR_URL, ids, FDOR_FIELDS, batch=80, return_geometry=geometry)
    kept = []
    for item in raw:
        attrs = item.get("attributes") or {}
        if int(attrs.get("CO_NO") or 0) != int(co_no):
            continue
        kept.append(item)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(kept))
    print(f"  FDOR rows {len(kept)}", flush=True)
    return kept


def merge_geometries(geometries: list[dict]) -> dict | None:
    polygons: list = []
    for geometry in geometries:
        if not geometry:
            continue
        if geometry.get("type") == "Polygon":
            polygons.append(geometry["coordinates"])
        elif geometry.get("type") == "MultiPolygon":
            polygons.extend(geometry["coordinates"])
    if not polygons:
        return None
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def fdor_acres(attrs: dict) -> float | None:
    sqft = seed.num(attrs.get("LND_SQFOOT"))
    if sqft is None:
        return None
    return sqft / 43560


def fdor_lookup(rows: list[dict], key_fn) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for item in rows:
        attrs = item.get("attributes") or {}
        parcel_id = usable_parcel_id(attrs.get("PARCEL_ID"))
        if not parcel_id:
            continue
        key = key_fn(parcel_id)
        previous = found.get(key)
        if previous is None:
            found[key] = item
    return found


def apply_fdor_values(props: dict, attrs: dict, *, acres: bool, sale_price: bool, tax: bool) -> None:
    if acres:
        value = fdor_acres(attrs)
        if value is not None:
            props["acreage"] = round(value, 4)
    if tax:
        just = seed.num(attrs.get("JV"))
        assessed = seed.num(attrs.get("AV_SD"))
        taxable = seed.num(attrs.get("TV_SD"))
        if just is not None and just > 0:
            props["tax"]["marketValue"] = just
        if assessed is not None and assessed > 0:
            props["tax"]["assessedValue"] = assessed
        if taxable is not None and taxable > 0:
            props["tax"]["taxableValue"] = taxable
        if not props.get("dorCode"):
            props["dorCode"] = meaningful(attrs.get("DOR_UC"))
    if sale_price:
        price = seed.num(attrs.get("SALE_PRC1"))
        if price is not None and price > 0 and not props["lastSale"].get("price"):
            props["lastSale"]["price"] = price
        if not props["lastSale"].get("date"):
            props["lastSale"]["date"] = seed.sale_date(attrs.get("SALE_YR1"), attrs.get("SALE_MO1"))
        if not props["lastSale"].get("qualified"):
            props["lastSale"]["qualified"] = meaningful(attrs.get("QUAL_CD1"))
    if not props.get("ownerName"):
        props["ownerName"] = meaningful(attrs.get("OWN_NAME"))
    mail = props.get("mailingAddress") or {}
    if not mail.get("line1"):
        mail["line1"] = meaningful(attrs.get("OWN_ADDR1"))
        mail["line2"] = meaningful(attrs.get("OWN_ADDR2"))
        mail["city"] = meaningful(attrs.get("OWN_CITY"))
        mail["state"] = meaningful(attrs.get("OWN_STATE"))
        mail["zip"] = seed.zip_str(attrs.get("OWN_ZIPCD"))
        props["mailingAddress"] = mail
    if not props.get("situsAddress"):
        props["situsAddress"] = meaningful(attrs.get("PHY_ADDR1"))
        props["situsCity"] = props.get("situsCity") or meaningful(attrs.get("PHY_CITY"))
        props["situsZip"] = props.get("situsZip") or seed.zip_str(attrs.get("PHY_ZIPCD"))


def features_from_fdor(rows: list[dict], county: dict, markets: list[str], source: str) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for item in rows:
        attrs = item.get("attributes") or {}
        parcel_id = usable_parcel_id(attrs.get("PARCEL_ID"))
        if not parcel_id:
            continue
        acres = fdor_acres(attrs)
        if not seed.in_band(acres):
            continue
        grouped.setdefault(parcel_id, []).append(item)
    features: list[dict] = []
    for parcel_id, items in grouped.items():
        geometries = []
        for item in items:
            geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
            if geometry:
                geometries.append(geometry)
        geometry = merge_geometries(geometries)
        center = seed.centroid_of(geometry) if geometry else None
        if not geometry or not seed.plausible_centroid(center):
            continue
        attrs = items[0].get("attributes") or {}
        acres = fdor_acres(attrs)
        if not seed.in_band(acres):
            continue
        feature = seed.empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,  # type: ignore[arg-type]
            geometry=geometry,
            center=center,  # type: ignore[arg-type]
            source=source,
            owner=meaningful(attrs.get("OWN_NAME")),
            situs=meaningful(attrs.get("PHY_ADDR1")),
            city=meaningful(attrs.get("PHY_CITY")),
            zip_code=seed.zip_str(attrs.get("PHY_ZIPCD")),
            dor=meaningful(attrs.get("DOR_UC")),
            sale_price=seed.num(attrs.get("SALE_PRC1")),
            sale_date=seed.sale_date(attrs.get("SALE_YR1"), attrs.get("SALE_MO1")),
            sale_qualified=meaningful(attrs.get("QUAL_CD1")),
            market_value=seed.num(attrs.get("JV")),
            assessed=seed.num(attrs.get("AV_SD")),
            taxable=seed.num(attrs.get("TV_SD")),
            mail1=meaningful(attrs.get("OWN_ADDR1")),
            mail2=meaningful(attrs.get("OWN_ADDR2")),
            mail_city=meaningful(attrs.get("OWN_CITY")),
            mail_state=meaningful(attrs.get("OWN_STATE")),
            mail_zip=seed.zip_str(attrs.get("OWN_ZIPCD")),
        )
        if feature["properties"]["lastSale"]["price"] is not None and feature["properties"]["lastSale"]["price"] <= 0:
            feature["properties"]["lastSale"]["price"] = None
        attach_links(feature)
        features.append(feature)
    sanitize(features)
    return features


def existing_props(fips: str) -> dict[str, dict]:
    folder = seed.COUNTY_DIR / fips / "tiles"
    found: dict[str, dict] = {}
    if not folder.exists():
        return found
    for path in folder.glob("*.geojson"):
        data = json.loads(path.read_text())
        for feature in data.get("features") or []:
            props = feature.get("properties") or {}
            parcel_id = props.get("parcelId")
            if parcel_id:
                found[str(parcel_id)] = props
    return found


def carry_forward(features: list[dict], previous: dict[str, dict]) -> int:
    copied = 0
    keys = ("zoningCode", "zoningDistrict", "flu", "jurisdictionCode")
    for feature in features:
        props = feature["properties"]
        old = previous.get(props["parcelId"])
        if not old:
            continue
        hit = False
        for key in keys:
            if old.get(key) and not props.get(key):
                props[key] = old[key]
                hit = True
        if hit:
            copied += 1
    return copied


def pull_arcgis(spec: dict, county: dict, markets: list[str]) -> tuple[list[dict], int, int]:
    ids, count = all_object_ids(spec["url"], spec["where"])
    print(f"  source rows {count} ids {len(ids)}", flush=True)
    raw = seed.fetch_by_ids(spec["url"], ids, spec["outFields"])
    features, dropped = seed.normalize_rows(raw, county, markets, spec)
    for feature in features:
        attach_links(feature)
        props = feature["properties"]
        if spec["fips"] == "12023":
            # Url is not an id field on normalize. Re-read is not available; template is the card link.
            pass
    sanitize(features)
    return features, count or len(ids), dropped


def all_object_ids(url: str, where: str) -> tuple[list[int], int]:
    count = seed.count_where(url, where)
    ids = seed.fetch_object_ids(url, where)
    if len(ids) >= max(1, int(count * 0.98)) or count == 0:
        return ids, count
    print(f"  returnIdsOnly {len(ids)} < count {count}; paging OBJECTID", flush=True)
    # Walton's object id field is OBJECTID_1. Page whichever field returnIdsOnly uses
    # by walking the id list we do have, then filling gaps is unnecessary if the
    # service simply truncated. Split the where with GIS_ACRES bands.
    collected = set(ids)
    # Fall back to acreage bands of 10 acres so each page stays under the id cap.
    start = 5.0
    while start < 150:
        end = min(150.0, start + 10)
        clause = f"({where}) AND GIS_ACRES>={start} AND GIS_ACRES<{end}" if end < 150 else f"({where}) AND GIS_ACRES>={start} AND GIS_ACRES<={end}"
        if "GIS_ACRES" not in where and "Acres" not in where and "DTAXACRES" not in where:
            break
        field = "GIS_ACRES" if "GIS_ACRES" in where else "Acres" if "Acres" in where else "DTAXACRES"
        clause = f"({where}) AND {field}>={start} AND {field}<{end}" if end < 150 else f"({where}) AND {field}>={start} AND {field}<={end}"
        try:
            collected.update(seed.fetch_object_ids(url, clause))
        except Exception as exc:  # noqa: BLE001
            print(f"  band {start} failed ({exc})", flush=True)
        start = end
    print(f"  banded ids {len(collected)}", flush=True)
    return sorted(collected), count


def join_fdor_on_features(features: list[dict], spec: dict) -> None:
    if not spec.get("fdorCo"):
        return
    bbox = county_bbox(spec["fips"])
    rows = fdor_features(spec["fdorCo"], bbox, geometry=False)
    table = fdor_lookup(rows, dash_strip if spec.get("fdorKey") == "dash" else (lambda value: value))
    hit = 0
    for feature in features:
        props = feature["properties"]
        key = dash_strip(props["parcelId"]) if spec.get("fdorKey") == "dash" else props["parcelId"]
        item = table.get(key)
        if not item:
            continue
        hit += 1
        apply_fdor_values(
            props,
            item.get("attributes") or {},
            acres=False,
            sale_price=True,
            tax=spec["fips"] == "12023",
        )
    print(f"  FDOR attribute hits {hit}/{len(features)}", flush=True)
    sanitize(features)


def pull_putnam(spec: dict, county: dict, markets: list[str]) -> tuple[list[dict], int, int]:
    bbox = county_bbox("12107")
    rows = fdor_features(64, bbox, geometry=False)
    table = fdor_lookup(rows, lambda value: value.strip())
    print(f"  FDOR 5–150 ids {len(table)}", flush=True)
    url = spec["primary"]
    try:
        count = seed.count_where(spec["primary"], "1=1")
        if count > 1000:
            print(f"  Putnam primary count {count}", flush=True)
        else:
            url = spec["twin"]
    except Exception as exc:  # noqa: BLE001
        url = spec["twin"]
        print(f"  Putnam primary unavailable ({exc}); using Parcels_PA twin", flush=True)
    spec["url"] = url
    ids = list(table)
    fields = [
        "PARCELID",
        "OWNERNME1",
        "OWNERNME2",
        "PSTLADDRESS",
        "PSTLCITY",
        "PSTLSTATE",
        "PSTLZIP5",
        "SITEADDRESS",
        "CNTASSDVAL",
        "LNDVALUE",
        "USECD",
    ]
    features: list[dict] = []
    missed = 0
    for start in range(0, len(ids), 40):
        chunk = ids[start : start + 40]
        quoted = ",".join("'" + value.replace("'", "''") + "'" for value in chunk)
        data = seed.fetch_json(
            url,
            {
                "where": f"PARCELID IN ({quoted})",
                "outFields": ",".join(fields),
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:240])
        seen = set()
        for item in data.get("features") or []:
            attrs = item.get("attributes") or {}
            parcel_id = usable_parcel_id(attrs.get("PARCELID"))
            if not parcel_id:
                continue
            seen.add(parcel_id.strip())
            fdor = table.get(parcel_id.strip())
            if not fdor:
                continue
            geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
            center = seed.centroid_of(geometry) if geometry else None
            if not geometry or not seed.plausible_centroid(center):
                missed += 1
                continue
            acres = fdor_acres(fdor.get("attributes") or {})
            if not seed.in_band(acres):
                continue
            feature = seed.empty_feature(
                fips="12107",
                county="Putnam",
                state="Florida",
                markets=markets,
                parcel_id=parcel_id.strip(),
                acreage=acres,  # type: ignore[arg-type]
                geometry=geometry,
                center=center,  # type: ignore[arg-type]
                source=spec["source"],
                owner=meaningful(attrs.get("OWNERNME1")),
                situs=meaningful(attrs.get("SITEADDRESS")),
                dor=meaningful(attrs.get("USECD")),
                assessed=seed.num(attrs.get("CNTASSDVAL")),
                mail1=meaningful(attrs.get("PSTLADDRESS")),
                mail_city=meaningful(attrs.get("PSTLCITY")),
                mail_state=meaningful(attrs.get("PSTLSTATE")),
                mail_zip=seed.zip_str(attrs.get("PSTLZIP5")),
            )
            feature["properties"]["ownerName2"] = meaningful(attrs.get("OWNERNME2"))
            apply_fdor_values(feature["properties"], fdor.get("attributes") or {}, acres=True, sale_price=True, tax=True)
            attach_links(feature)
            features.append(feature)
        missed += len(chunk) - len(seen)
        if start % 400 == 0:
            print(f"    putnam {min(start + 40, len(ids))}/{len(ids)}", flush=True)
    sanitize(features)
    by_id: dict[str, dict] = {}
    for feature in features:
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    print(f"  Putnam kept {len(features)} missed {missed}", flush=True)
    return features, len(table), missed


def pull_okee(spec: dict, county: dict, markets: list[str]) -> tuple[list[dict], int, int]:
    bbox = county_bbox("12093")
    rows = fdor_features(57, bbox, geometry=False)
    table = fdor_lookup(rows, nodash)
    print(f"  FDOR 5–150 ids {len(table)}", flush=True)
    url = spec["url"]
    ids = seed.fetch_object_ids(url, "1=1")
    print(f"  Tyler ids {len(ids)}", flush=True)
    fields = [
        "OBJECTID",
        "ParcelID",
        "Owner1",
        "Owner2",
        "OwnerAddress1",
        "OwnerAddress2",
        "OwnerCity",
        "OwnerState",
        "OwnerZip",
        "StreetNumber",
        "StreetName",
        "City",
        "Zip",
        "TaxValue",
        "confidential",
    ]
    attrs_only = seed.fetch_by_ids(url, ids, fields, batch=200, return_geometry=False)
    wanted: list[int] = []
    attr_by_oid: dict[int, dict] = {}
    for item in attrs_only:
        attrs = item.get("attributes") or {}
        parcel_id = usable_parcel_id(attrs.get("ParcelID"))
        oid = attrs.get("OBJECTID")
        if not parcel_id or oid is None:
            continue
        if nodash(parcel_id.strip()) not in table:
            continue
        wanted.append(int(oid))
        attr_by_oid[int(oid)] = attrs
    print(f"  Tyler in FDOR band {len(wanted)}", flush=True)
    raw = seed.fetch_by_ids(url, wanted, ["ParcelID", "OBJECTID"], batch=80, return_geometry=True)
    features: list[dict] = []
    missed = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        oid = int(attrs.get("OBJECTID") or 0)
        full = attr_by_oid.get(oid) or attrs
        parcel_id = usable_parcel_id(full.get("ParcelID"))
        if not parcel_id:
            missed += 1
            continue
        parcel_id = parcel_id.strip()
        fdor = table.get(nodash(parcel_id))
        if not fdor:
            missed += 1
            continue
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        center = seed.centroid_of(geometry) if geometry else None
        if not geometry or not seed.plausible_centroid(center):
            missed += 1
            continue
        acres = fdor_acres(fdor.get("attributes") or {})
        if not seed.in_band(acres):
            continue
        confidential = meaningful(full.get("confidential"))
        owner = None if confidential else meaningful(full.get("Owner1"))
        mail1 = None if confidential else meaningful(full.get("OwnerAddress1"))
        mail2 = None if confidential else meaningful(full.get("OwnerAddress2"))
        mail_city = None if confidential else meaningful(full.get("OwnerCity"))
        mail_state = None if confidential else meaningful(full.get("OwnerState"))
        mail_zip = None if confidential else seed.zip_str(full.get("OwnerZip"))
        number = meaningful(full.get("StreetNumber"))
        street = meaningful(full.get("StreetName"))
        situs = " ".join(part for part in (number, street) if part) or None
        feature = seed.empty_feature(
            fips="12093",
            county="Okeechobee",
            state="Florida",
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,  # type: ignore[arg-type]
            geometry=geometry,
            center=center,  # type: ignore[arg-type]
            source=spec["source"],
            owner=owner,
            situs=situs,
            city=meaningful(full.get("City")),
            zip_code=seed.zip_str(full.get("Zip")),
            taxable=seed.num(full.get("TaxValue")),
            mail1=mail1,
            mail2=mail2,
            mail_city=mail_city,
            mail_state=mail_state,
            mail_zip=mail_zip,
        )
        if not confidential:
            feature["properties"]["ownerName2"] = meaningful(full.get("Owner2"))
        apply_fdor_values(feature["properties"], fdor.get("attributes") or {}, acres=True, sale_price=True, tax=True)
        if confidential:
            feature["properties"]["ownerName"] = None
            feature["properties"]["ownerName2"] = None
            feature["properties"]["mailingAddress"] = {"line1": None, "line2": None, "city": None, "state": None, "zip": None}
        attach_links(feature)
        features.append(feature)
    sanitize(features)
    by_id: dict[str, dict] = {}
    for feature in features:
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    print(f"  Okeechobee kept {len(features)} geometry misses {missed}", flush=True)
    return features, len(table), missed


def write_county(county: dict, markets: list[str], spec: dict, features: list[dict], source_count: int, dropped: int) -> dict:
    previous = existing_props(county["fips"])
    copied = carry_forward(features, previous)
    gaps = list(GAP_NOTES.get(county["fips"]) or [])
    if copied:
        gaps.append(f"Zoning or future land use carried forward for {copied} parcel ids that still match.")
    if source_count and len(features) < int(source_count * 0.8):
        raise RuntimeError(f"{county['fips']} kept {len(features)} of {source_count}")
    if source_count and len(features) < source_count:
        gaps.insert(0, f"{source_count} rows matched the acreage filter; {len(features)} kept after the parcel-id and geometry checks.")
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{county['fips']} emitted a parcel outside 5–150 acres")
    path, lookup, tiles = seed.write_tiles(county, features)
    link = LINKS[county["fips"]]
    print(f"  kept {len(features)} tiles {tiles}", flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=spec["source"],
        query_url=spec.get("url") or FDOR_URL,
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        tile_count=tiles,
        extra={
            "paLinkVerified": bool(link.get("paVerified")),
            "appraiserSearchUrl": link.get("appraiser"),
            "gisViewerUrl": link.get("gis"),
            "minAcres": 5.0,
            "maxAcres": 150.0,
        },
    )


def download_one(catalog: dict, fips: str, refresh: bool) -> None:
    spec = SPECS[fips]
    county = county_dict(catalog, fips, spec["name"])
    markets = markets_for(catalog, fips)
    if not markets:
        raise RuntimeError(f"{fips} is not on a market shelf")
    cache_path = CACHE_DIR / f"{fips}.json"
    print(f"Pulling {spec['name']} {fips}", flush=True)
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text())
        features = cached["features"]
        if not features:
            features = None
    if cache_path.exists() and not refresh and features:
        for feature in features:
            feature["properties"]["marketIds"] = markets
        print(f"  cache hit {len(features)}", flush=True)
        write_county(county, markets, spec, features, cached.get("sourceCount") or len(features), cached.get("dropped") or 0)
        return
    if spec["kind"] == "fdor":
        bbox = county_bbox(fips)
        rows = fdor_features(spec["co"], bbox, geometry=True)
        features = features_from_fdor(rows, county, markets, spec["source"])
        source_count = len({parcel_id for item in rows if (parcel_id := usable_parcel_id((item.get("attributes") or {}).get("PARCEL_ID")))})
        dropped = max(0, source_count - len(features))
        spec = {**spec, "url": FDOR_URL}
    elif spec["kind"] == "putnam":
        features, source_count, dropped = pull_putnam(spec, county, markets)
    elif spec["kind"] == "okee":
        features, source_count, dropped = pull_okee(spec, county, markets)
    else:
        features, source_count, dropped = pull_arcgis(spec, county, markets)
        join_fdor_on_features(features, spec)
    write_county(county, markets, spec, features, source_count, dropped)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"sourceCount": source_count, "dropped": dropped, "features": features}))


def fetch_attribute_map(url: str, where: str, id_field: str, fields: list[str]) -> dict[str, dict]:
    ids = seed.fetch_object_ids(url, where)
    raw = seed.fetch_by_ids(url, ids, fields, batch=200, return_geometry=False)
    found: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        parcel_id = usable_parcel_id(attrs.get(id_field))
        if parcel_id:
            found[parcel_id] = attrs
    return found


def monroe_count() -> int:
    if not MONROE_CERT.exists():
        raise RuntimeError(f"Missing Monroe intermediate at {MONROE_CERT}")
    context = ssl.create_default_context()
    context.load_verify_locations(str(MONROE_CERT))
    url = (
        "https://mcgis4.monroecounty-fl.gov/public/rest/services/Parcels/MapServer/0/query"
        "?where=1%3D1&returnCountOnly=true&f=json"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/market-parcels"})
    with urllib.request.urlopen(req, timeout=90, context=context) as resp:
        data = json.loads(resp.read().decode())
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:200])
    return int(data["count"])


def stamp_kept(fips: str) -> None:
    folder = seed.COUNTY_DIR / fips / "tiles"
    if not folder.exists():
        raise RuntimeError(f"{fips} has no tiles to stamp")
    extra_ids: dict[str, str] = {}
    if fips == "12055":
        url = "https://gis.highlandsfl.gov/server/rest/services/Layers/PAO_Parcels/FeatureServer/0/query"
        table = fetch_attribute_map(url, "Calculated_Acres>=5 AND Calculated_Acres<=150", "PARCELNO", ["PARCELNO", "STRAP", "Strap_Link"])
        for parcel_id, attrs in table.items():
            link = meaningful(attrs.get("Strap_Link"))
            strap = meaningful(attrs.get("STRAP"))
            if link and link.lower().startswith("http"):
                extra_ids[parcel_id] = link
            elif strap:
                extra_ids[parcel_id] = apply_template(LINKS["12055"]["appraiser"], strap) or ""
        print(f"  Highlands STRAP links {len(extra_ids)}", flush=True)
    if fips == "12009":
        url = "https://gis.brevardfl.gov/gissrv/rest/services/Accela/AccelaGIS_Layers_WKID2881/MapServer/5/query"
        table = fetch_attribute_map(url, "ACRES>=5 AND ACRES<=150", "PARCEL_ID", ["PARCEL_ID", "TaxAcct", "OWNER_RENUMBER"])
        for parcel_id, attrs in table.items():
            account = meaningful(attrs.get("TaxAcct")) or meaningful(attrs.get("OWNER_RENUMBER"))
            if account:
                extra_ids[parcel_id] = apply_template(LINKS["12009"]["appraiser"], account) or ""
        print(f"  Brevard account links {len(extra_ids)}", flush=True)
    link = LINKS[fips]
    future_cleared = 0
    for path in folder.glob("*.geojson"):
        data = json.loads(path.read_text())
        for feature in data.get("features") or []:
            props = feature["properties"]
            before = (props.get("lastSale") or {}).get("date")
            clear_future_sale(props)
            if before and not (props.get("lastSale") or {}).get("date"):
                future_cleared += 1
            props["opportunityZone"] = None
            props["oz2Eligibility"] = None
            if link.get("gis"):
                props["gisViewerUrl"] = link["gis"]
            special = extra_ids.get(props.get("parcelId"))
            if special:
                props["appraiserUrl"] = special
            elif link.get("appraiser") and link.get("id") not in {"strap", "taxacct"}:
                existing = props.get("appraiserUrl") or ""
                parcel_id = str(props.get("parcelId") or "")
                if parcel_id and parcel_id in existing and "http" in existing.lower():
                    pass
                else:
                    token = nodash(parcel_id) if link.get("id") == "nodash" else parcel_id
                    props["appraiserUrl"] = apply_template(link["appraiser"], token)
            for key in list(props):
                if re.search(r"phone|email|ssn", key, re.I):
                    props.pop(key, None)
        path.write_text(json.dumps(data, separators=(",", ":")))
    row_path = seed.COUNTY_DIR / fips / "county.json"
    row = json.loads(row_path.read_text())
    gaps = list(row.get("gaps") or [])
    for note in GAP_NOTES.get(fips) or []:
        if note not in gaps:
            gaps.append(note)
    if fips == "12087":
        count = monroe_count()
        note = (
            f"Monroe parcel count on mcgis4 with the pinned DigiCert intermediate was {count}. "
            "The 5.0–150.0 acre extract is the polygon-area shelf already on this county."
        )
        if note not in gaps:
            gaps.append(note)
        print(f"  Monroe TLS count {count}", flush=True)
    if future_cleared:
        gaps.append(f"Cleared {future_cleared} sale dates after {TODAY}.")
    row["gaps"] = gaps
    row["paLinkVerified"] = bool(link.get("paVerified"))
    row["appraiserSearchUrl"] = link.get("appraiser")
    row["gisViewerUrl"] = link.get("gis")
    row_path.write_text(json.dumps(row, indent=2) + "\n")
    print(f"Stamped {fips} future sales cleared {future_cleared}", flush=True)


def meta_entry(row: dict) -> dict:
    return {
        "name": row["name"],
        "fips": row["fips"],
        "state": row["state"],
        "featureCount": row.get("featureCount") or 0,
        "coverage": row.get("coverage"),
        "partition": row.get("partition"),
        "minAcres": 5.0,
        "maxAcres": 150.0,
        "source": row.get("source"),
        "queryUrl": row.get("queryUrl"),
        "gaps": row.get("gaps") or [],
        "path": row.get("path"),
        "lookup": row.get("lookup"),
        "tileCount": row.get("tileCount"),
        "sourceCount": row.get("sourceCount"),
    }


def index_entry(row: dict) -> dict:
    return {
        "name": row["name"],
        "state": row["state"],
        "fips": row["fips"],
        "featureCount": row.get("featureCount") or 0,
        "coverage": row.get("coverage"),
        "minAcres": 5.0,
        "maxAcres": 150.0,
        "gaps": (row.get("gaps") or [])[:2],
    }


def recount(counties: list[dict]) -> tuple[int, int, int, int]:
    parcels = sum(int(county.get("featureCount") or 0) for county in counties)
    complete = sum(1 for county in counties if county.get("coverage") == "complete-gte-5ac" and county.get("featureCount"))
    sample = sum(1 for county in counties if county.get("coverage") in {"sample", "partial"} and county.get("featureCount"))
    gaps = sum(1 for county in counties if not county.get("featureCount"))
    return parcels, complete, sample, gaps


def upsert_section_row(text: str, section: str, row: str, county_name: str) -> str:
    marker = f"### {section}\n"
    start = text.find(marker)
    if start < 0:
        return text
    end = text.find("\n### ", start + len(marker))
    block = text[start:] if end < 0 else text[start:end]
    lines = block.splitlines()
    prefix = f"| {county_name} |"
    found = False
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = row
            found = True
    if not found:
        inserted = False
        for index, line in enumerate(lines):
            if not line.startswith("| ") or line.startswith("| ---") or line.startswith("| County"):
                continue
            existing = line.split("|")[1].strip()
            if county_name < existing:
                lines.insert(index, row)
                inserted = True
                break
        if not inserted:
            last = 0
            for index, line in enumerate(lines):
                if line.startswith("|"):
                    last = index
            lines.insert(last + 1, row)
    new_block = "\n".join(lines)
    if not new_block.endswith("\n"):
        new_block += "\n"
    if end < 0:
        return text[:start] + new_block
    return text[:start] + new_block + text[end:]


def refresh_manifests(catalog: dict, fips_set: set[str]) -> None:
    index_path = seed.OUT_DIR / "index.json"
    index = json.loads(index_path.read_text())
    docs = [(ROOT / "docs" / "market-parcels.md").read_text(), (seed.OUT_DIR / "coverage.md").read_text()]
    for market in catalog["markets"]:
        if not any(county["fips"] in fips_set for county in market["counties"]):
            continue
        rel = index["markets"][market["id"]]["path"]
        meta_path = ROOT / rel
        meta = json.loads(meta_path.read_text())
        meta_counties = {county["fips"]: county for county in meta.get("counties") or []}
        index_counties = {county["fips"]: county for county in index["markets"][market["id"]]["counties"]}
        for county in market["counties"]:
            file_path = seed.COUNTY_DIR / county["fips"] / "county.json"
            if not file_path.exists():
                continue
            row = json.loads(file_path.read_text())
            meta_counties[county["fips"]] = meta_entry(row)
            index_counties[county["fips"]] = index_entry(row)
        ordered_ids = sorted(meta_counties, key=lambda item: meta_counties[item]["name"])
        ordered = [meta_counties[item] for item in ordered_ids]
        meta["counties"] = ordered
        meta["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        parcels, complete, sample, gaps = recount(ordered)
        meta["parcelCount"] = parcels
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        summary = index["markets"][market["id"]]
        summary["parcelCount"] = parcels
        summary["completeCountyCount"] = complete
        summary["sampleCountyCount"] = sample
        summary["gapCountyCount"] = gaps
        summary["counties"] = [index_counties[item] for item in ordered_ids]
        line = (
            f"| {market['id']} | {summary['tier']} | {parcels:,} | {complete} | {sample} | {gaps} |"
        )
        for index_doc, text in enumerate(docs):
            text, _count = re.subn(rf"^\| {re.escape(market['id'])} \|.*$", line, text, count=1, flags=re.M)
            for county in ordered:
                row = (
                    f"| {county['name']} | {county['state']} | {county['fips']} | {county['coverage']} | "
                    f"{int(county['featureCount']):,} | {county.get('source')} |"
                )
                text = upsert_section_row(text, market["id"], row, county["name"])
            docs[index_doc] = text
        print(f"  {market['id']} parcels {parcels:,} complete {complete}", flush=True)
    index["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    (ROOT / "docs" / "market-parcels.md").write_text(docs[0])
    (seed.OUT_DIR / "coverage.md").write_text(docs[1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--stamp-only", action="store_true")
    args = parser.parse_args()
    catalog = ensure_catalog(json.loads(CATALOG_PATH.read_text()))
    selected = {item.lower() for item in args.county}
    pull = []
    for fips, spec in SPECS.items():
        if selected and fips not in selected and spec["name"].lower() not in selected:
            continue
        pull.append(fips)
    stamp = []
    for fips in sorted(KEEP_FIPS | set(SPECS)):
        if selected and fips not in selected:
            continue
        if fips in KEEP_FIPS or args.stamp_only:
            stamp.append(fips)
    if not args.stamp_only:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        workers = 1 if len(pull) < 2 else 2
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(download_one, catalog, fips, args.refresh): fips for fips in pull}
            for future in as_completed(futures):
                fips = futures[future]
                try:
                    future.result()
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{fips}: {exc}")
                    print(f"FAILED {fips}: {exc}", flush=True)
        if errors:
            raise SystemExit("County downloads failed:\n" + "\n".join(errors))
    for fips in stamp:
        if fips in KEEP_FIPS:
            stamp_kept(fips)
    refresh_manifests(catalog, set(SPECS) | KEEP_FIPS)
    print("Done", flush=True)


if __name__ == "__main__":
    sys.exit(main())
