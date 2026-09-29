#!/usr/bin/env python3
"""5.0–150.0 acre parcels for Florida rural OZ batch 3 (19 counties).

Same 0.25° tile writer as batches 1 and 2 (origin lon -83 / lat 27).
Does not add a market shelf or switch markets. Osceola and Orange stay on
the Orlando tile folders the site already reads. Franklin and Gulf join Big
Bend. Washington joins Pensacola. AADT stays the query-time FDOT join.
Income stays ACS B19013_001E. No Opportunity Zone status is stored.

MIL1 2023 is not a polygon source. Washington_2024_DOR_Parcels is the
personal re-host and is not queried.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any

import seed_market_parcels as seed
from parcel_geometry import esri_rings_to_geojson, geodesic_acres
from rural_oz_batch2_parcels import (
    apply_template,
    county_dict,
    dash_strip,
    index_entry,
    markets_for,
    meaningful,
    meta_entry,
    nodash,
    recount,
    sale_iso,
    sanitize,
    upsert_section_row,
    usable_parcel_id,
)

ROOT = seed.ROOT
CATALOG_PATH = seed.CATALOG_PATH
CACHE_DIR = Path("/tmp/dls-rural-oz-batch3")
FDOR_URL = (
    "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/"
    "Florida_Statewide_Cadastral/FeatureServer/0/query"
)
SWFWMD_CHARLOTTE = (
    "https://www25.swfwmd.state.fl.us/arcgis12/rest/services/BaseVector/"
    "parcel_search/MapServer/1/query"
)
TODAY = date.today().isoformat()
ORLANDO_FIPS = {"12095", "12097"}
BLANK_MAIL = {"line1": None, "line2": None, "city": None, "state": None, "zip": None}

FDOR_FIELDS = [
    "PARCEL_ID",
    "CO_NO",
    "ALT_KEY",
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

ADD_TO_MARKET = {
    "Big Bend": [
        {"name": "Franklin", "state": "Florida", "fips": "12037"},
        {"name": "Gulf", "state": "Florida", "fips": "12045"},
    ],
    "Pensacola": [
        {"name": "Washington", "state": "Florida", "fips": "12133"},
    ],
}

LINKS: dict[str, dict[str, Any]] = {
    "12001": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=1081&LayerID=26490&PageTypeID=4&PageID=10770&KeyValue={id}",
        "gis": "https://mapgenius.alachuacounty.us/",
        "paVerified": True,
    },
    "12003": {
        "appraiser": "https://bakerpa.com/propertydetails.php?parcel={id}",
        "gis": "https://bakerpa.com/map2/",
        "paVerified": True,
        "id": "nodash",
    },
    "12015": {
        "appraiser": "https://www.ccappraiser.com/Show_parcel.asp?acct={id}&gen=T&tax=T&bld=T&oth=T&sal=T&lnd=T&leg=T",
        "gis": "https://agis.charlottecountyfl.gov/ccgis/",
        "paVerified": True,
    },
    "12033": {
        "appraiser": "https://www.escpa.org/cama/Detail_a.aspx?s={id}",
        "gis": "https://maps.roktech.net/escambia_gomaps4/?mapName=General",
        "paVerified": True,
    },
    "12037": {
        "appraiser": "https://franklin-search.gsacorp.io/parcel/{id}",
        "gis": "https://gis.arpc.org/arcgis/apps/webappviewer/index.html?id=959fb7cf8450449987d52f296b6dde0e",
        "paVerified": True,
        "id": "franklin",
    },
    "12045": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=819&LayerID=15077&PageTypeID=4&PageID=6812&KeyValue={id}",
        "gis": "https://maps2.roktech.net/GulfGoMaps4/?mapName=GIS",
        "paVerified": False,
    },
    "12057": {
        "appraiser": "https://gis.hcpafl.org/PropertySearch/#/parcel/basic/{id}",
        "gis": "https://gis.hcpafl.org/GisSearch/",
        "paVerified": True,
        "token": "STRAP",
    },
    "12065": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=866&LayerID=16381&PageTypeID=4&PageID=7228&KeyValue={id}",
        "gis": "https://gisdata-jcpa.hub.arcgis.com",
        "paVerified": False,
    },
    "12071": {
        "appraiser": "https://www.leepa.org/Display/Displayparcel.aspx?folioID={id}",
        "gis": "https://gissvr.leepa.org/geoview2/",
        "paVerified": False,
        "token": "FOLIOID",
    },
    "12073": {
        "appraiser": "https://search.leonpa.gov/Property/Details/{id}",
        "gis": "https://tlcgis.leoncountyfl.gov/Propinfo/index.html",
        "paVerified": False,
    },
    "12085": {
        "appraiser": "https://www.pamartinfl.gov/app/search/view/{id}",
        "gis": "https://geoweb.martin.fl.us/general/",
        "paVerified": True,
        "token": "AIN",
    },
    "12086": {
        "appraiser": "https://apps.miamidadepa.gov/PropertySearch/#/?folio={id}",
        "gis": "https://experience.arcgis.com/experience/74e9a9f78b094ba2b17d86a0bfeb2eeb",
        "paVerified": True,
    },
    "12089": {
        "appraiser": "https://search.ncpafl.com/search/r/{id}",
        "gis": "https://maps.ncpafl.com/nassautaxmap/",
        "paVerified": True,
    },
    "12095": {
        "appraiser": "https://ocpaweb.ocpafl.org/parcelsearch/Parcel%20ID/{id}",
        "gis": "https://www.ocfl.net/PlanningDevelopment/InteractiveMapping.aspx",
        "paVerified": True,
    },
    "12097": {
        "appraiser": "https://maps.property-appraiser.org/?PIN={id}",
        "gis": "https://maps.property-appraiser.org/",
        "paVerified": False,
    },
    "12111": {
        "appraiser": "http://apps.paslc.gov/rerecordcard/{id}",
        "gis": "https://map.paslc.gov/",
        "paVerified": False,
        "token": "AccountNumber",
    },
    "12127": {
        "appraiser": "https://vcpa.vcgov.org/parcel/summary/?altkey={id}",
        "gis": "https://vcpa.vcgov.org/search/map",
        "paVerified": True,
        "token": "ALTKEY",
    },
    "12129": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=836&LayerID=15205&PageTypeID=4&PageID=6833&KeyValue={id}",
        "gis": "https://gis-portal-update-wakullaplanning.hub.arcgis.com/",
        "paVerified": False,
    },
    "12133": {
        "appraiser": "https://qpublic.schneidercorp.com/Application.aspx?AppID=896&LayerID=16944&PageTypeID=4&PageID=7615&KeyValue={id}",
        "gis": "https://qpublic.schneidercorp.com/Application.aspx?AppID=896&LayerID=16944&PageTypeID=2&PageID=7613",
        "paVerified": False,
    },
}

GAP_NOTES: dict[str, list[str]] = {
    "12001": [
        "Alachua parcels are Parcels35/FeatureServer/0. Acreage is acres, 5.0–150.0 inclusive.",
        "FDOR joins need CO_NO=11 and the dashed parcel id. Assessed and taxable values come from that FDOR row. firstName1 is the full owner name. No Opportunity Zone status is stored.",
    ],
    "12003": [
        "Baker parcels are parcels_web2/FeatureServer/0. Acreage is GIS_Acreag, 5.0–150.0 inclusive. MIL1 2023 is not the polygon source.",
        "FDOR joins need CO_NO=12 and PIN with '-' removed. The property-appraiser link uses that undashed id. No Opportunity Zone status is stored.",
    ],
    "12015": [
        "Charlotte parcels are CCGISLayers/MapServer/27. Acreage is SWFWMD parcel_search/1 AREANO joined on ACCOUNT = PARCELID, 5.0–150.0 inclusive. The Florida DOH extract is not this shelf.",
        "FDOR joins need CO_NO=18 and ACCOUNT exactly. No Opportunity Zone status is stored.",
    ],
    "12033": [
        "Escambia parcels are Individual_Layers/parcels/MapServer/0. Acreage is LANDSIZE, 5.0–150.0 inclusive. The parcel id is REFERENCE.",
        "Where CONFCD='Y', OWNER and every MAIL* field are dropped and the site address is treated as sensitive. Owner phone and email are not ingested.",
        "FDOR joins need CO_NO=27 and REFERENCE exactly. REFNUM with dashes does not match. Sale price and taxable value come from that FDOR row. No Opportunity Zone status is stored.",
    ],
    "12037": [
        "Franklin polygons are ARPC Hosted/Parcels_2023. Acreage is the geodesic shape area, 5.0–150.0 inclusive. FDOR LND_SQFOOT is zero on most coastal parcels and is not the acreage.",
        "FDOR joins need CO_NO=29 and parcelno exactly. Owner, tax, and the roll sale come from that FDOR row. MIL1 2023 is not the polygon source. No Opportunity Zone status is stored.",
    ],
    "12045": [
        "Gulf parcels are GoMaps4/MapServer/12. Acreage is ACREAGE, 5.0–150.0 inclusive. The property-appraiser pattern is stored and was not health-checked.",
        "FDOR joins need CO_NO=33 and PIN_NODELIM exactly. MIL1 2023 is not the polygon source. No Opportunity Zone status is stored.",
    ],
    "12057": [
        "Hillsborough parcels are ParcelPublishing/MapServer/12. The FeatureServer advertises public edits and is queried read-only through the MapServer twin. Acreage is ACREAGE, 5.0–150.0 inclusive. The stored parcel id is FOLIO.",
        "Mailing address is suppressed where OWNER contains 'Confidential'. Owner phone and email are not ingested.",
        "FDOR joins need CO_NO=39 and STRAP exactly. FOLIO is ALT_KEY, not PARCEL_ID. No Opportunity Zone status is stored.",
    ],
    "12065": [
        "Jefferson parcels are JC__PARCELS_view/FeatureServer/0. Acreage is COGO_ACRES, 5.0–150.0 inclusive. Road placeholder 00-00-00-0000-0RDS-0000 is dropped.",
        "OwnerPhone and OwnerEmail are present on the Jefferson roll and are not ingested.",
        "FDOR joins need CO_NO=43 and the dashed PARCELID. Owner, tax, and the roll sale come from that FDOR row. The property-appraiser pattern is stored and was not health-checked. MIL1 2023 is not the polygon source. No Opportunity Zone status is stored.",
    ],
    "12071": [
        "Lee parcels are ParcelAddress/MapServer/0 with CONDOTYPE IS NULL so condo units do not inherit the parent acreage. Acreage is GISACRES, 5.0–150.0 inclusive.",
        "HIDE_STRAP Y/C is redacted to OBOR at the source. OBOR is stored as null. Owner phone and email are not ingested.",
        "FDOR joins need CO_NO=46 and STRAP exactly. The property-appraiser pattern uses FOLIOID and was not health-checked. No Opportunity Zone status is stored.",
    ],
    "12073": [
        "Leon parcels are TLC_OverlayParnal_D_WM/MapServer/0. Acreage is CALC_ACREA, 5.0–150.0 inclusive. Phone columns are not requested.",
        "Where SECURE='S', owner and mailing address are suppressed.",
        "FDOR joins need CO_NO=47 and TAXID exactly. The property-appraiser pattern is stored and was not health-checked. No Opportunity Zone status is stored.",
    ],
    "12085": [
        "Martin parcels are geoweb base_map/MapServer/10. Acreage is AREA_ACRES, 5.0–150.0 inclusive. The stored parcel id is PCN.",
        "FDOR joins need CO_NO=53 and PCN re-dashed 2-2-2-3-3-5-1. The raw 18-digit PCN does not match PARCEL_ID. ALT_KEY is ACCOUNT. Tax and the roll sale come from that FDOR row. No Opportunity Zone status is stored.",
    ],
    "12086": [
        "Miami-Dade parcels are MD_LandInformation/MapServer/26. Acreage is LOT_SIZE square feet / 43560, 5.0–150.0 inclusive. Multipart rows are deduped on FOLIO. Condo units do not inherit parent acreage, so there is no condo filter.",
        "PRIMARY_ZONE is a property-appraiser neighborhood code, not a zoning district. The parcel layer has no sale. The roll sale comes from FDOR.",
        "FDOR joins need CO_NO=23 and FOLIO exactly. No Opportunity Zone status is stored.",
    ],
    "12089": [
        "Nassau parcels are NassauCountyPublicTaxMap/MapServer/144. Acreage is GISCalculatedAcre, 5.0–150.0 inclusive. Repeated PINs are kept once.",
        "FDOR joins need CO_NO=55 and PIN with '-' removed. The dashed PIN does not match. MIL1 2023 is not the polygon source. No Opportunity Zone status is stored.",
    ],
    "12095": [
        "Orange parcels are AGOL_Open_Data/MapServer/56. The acreage filter is ACREAGE BETWEEN 5 AND 150 because the host rejects >= and <=. The OCPA Webmap/PARCEL extract is not this shelf.",
        "Where NAME1='CONFIDENTIAL', NAME1, NAME2, and the mailing address are suppressed.",
        "FDOR joins need CO_NO=58 and PARCEL with the 1st and 3rd 2-digit groups swapped (or ALT_KEY = PARCEL). No Opportunity Zone status is stored.",
    ],
    "12097": [
        "Osceola parcels are read from Parcels/MapServer/3. FeatureServer/3 advertises public edits and is not written. Acreage is TotalAcres, 5.0–150.0 inclusive. Tiles stay on the Orlando shelf.",
        "FDOR joins need CO_NO=59 and PIN exactly. The property-appraiser pattern is stored and was not health-checked. No Opportunity Zone status is stored.",
    ],
    "12111": [
        "St. Lucie parcels are Parcel_Boundaries/FeatureServer/0. Acreage is TOTAL_ACRE, 5.0–150.0 inclusive. The parcel id is the dashed ParcelID. Null ParcelIDs are dropped. PARCEL_NUMBER does not match FDOR.",
        "Where IsConfidential is set, CuO owner and mailing fields are suppressed.",
        "FDOR joins need CO_NO=66 and the dashed ParcelID. The property-appraiser pattern uses AccountNumber and was not health-checked. No Opportunity Zone status is stored.",
    ],
    "12127": [
        "Volusia parcels are Open_Data_3/FeatureServer/34. Acreage is CALCACRES, 5.0–150.0 inclusive. The parcel id is PID. DORPID is not the FDOR key. The Florida DOH extract is not this shelf.",
        "FDOR joins need CO_NO=74 and PID exactly. ALT_KEY is ALTKEY. No Opportunity Zone status is stored.",
    ],
    "12129": [
        "Wakulla parcels are ParcelM/FeatureServer/0. Acreage is MAP_ACRES, 5.0–150.0 inclusive. MIL1 2023 is not the polygon source.",
        "FDOR joins need CO_NO=75 and PARCEL_ID with '-' removed. Owner, tax, and the roll sale come from that FDOR row. The property-appraiser pattern is stored and was not health-checked. No Opportunity Zone status is stored.",
    ],
    "12133": [
        "Washington parcels are WashingtonParcelsAGOL/FeatureServer/0. Acreage is CALC_ACRES, 5.0–150.0 inclusive. Washington_2024_DOR_Parcels is an unofficial personal re-host and is not queried.",
        "FDOR joins need CO_NO=77 and PARCELNO exactly. Owner, tax, and the roll sale come from that FDOR row. The property-appraiser pattern is stored and was not health-checked. MIL1 2023 is not the polygon source. No Opportunity Zone status is stored.",
    ],
}


def arcgis(
    fips: str,
    name: str,
    url: str,
    where: str,
    fields: list[str],
    id_field: str,
    acres_field: str,
    source: str,
    **extra: Any,
) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "kind": "arcgis",
        "fips": fips,
        "name": name,
        "url": url,
        "where": where,
        "outFields": fields,
        "idField": id_field,
        "acresField": acres_field,
        "source": source,
    }
    spec.update(extra)
    return spec


SPECS: dict[str, dict[str, Any]] = {
    "12001": arcgis(
        "12001",
        "Alachua",
        "https://services1.arcgis.com/MiBZ4u97DWldovjI/arcgis/rest/services/Parcels35/FeatureServer/0/query",
        "acres>=5 AND acres<=150",
        ["parcel", "acres", "firstName1", "Address1", "Address2", "city", "state", "zip", "SaleAmount", "SaleDate", "JustValue", "puse"],
        "parcel",
        "acres",
        "fl-alachua-parcels35-12001",
        ownerField="firstName1",
        situsField=None,
        mail1Field="Address1",
        mail2Field="Address2",
        mailCityField="city",
        mailStateField="state",
        mailZipField="zip",
        dorField="puse",
        salePriceField="SaleAmount",
        saleDateField="SaleDate",
        marketValueField="JustValue",
        fdorCo=11,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
    ),
    "12003": arcgis(
        "12003",
        "Baker",
        "https://services6.arcgis.com/HSWu3dhzHf7nZfIa/arcgis/rest/services/parcels_web2/FeatureServer/0/query",
        "GIS_Acreag>=5 AND GIS_Acreag<=150",
        ["PIN", "GIS_Acreag", "cama0827_O", "Zoning"],
        "PIN",
        "GIS_Acreag",
        "fl-baker-parcels-web2-12003",
        ownerField="cama0827_O",
        zoningField="Zoning",
        fdorCo=12,
        fdorKey="dash",
        fdorTax=True,
        fdorSale=True,
        fdorOwner=True,
    ),
    "12015": {
        "kind": "charlotte",
        "fips": "12015",
        "name": "Charlotte",
        "url": "https://agis3.charlottecountyfl.gov/arcgis/rest/services/Essentials/CCGISLayers/MapServer/27/query",
        "source": "fl-charlotte-ccgis-12015",
        "fdorCo": 18,
        "fdorKey": "exact",
        "fdorTax": True,
        "fdorSale": True,
    },
    "12033": arcgis(
        "12033",
        "Escambia",
        "https://gismaps.myescambia.com/arcgis/rest/services/Individual_Layers/parcels/MapServer/0/query",
        "LANDSIZE>=5 AND LANDSIZE<=150",
        ["REFERENCE", "LANDSIZE", "OWNER", "MAILADDRESS1", "MAILADDRESS2", "MAILCITY", "MAILSTATE", "MAILZIP", "SITEADDR", "CITY", "ZIP", "CURRMKT", "CAPPEDVALUE", "DORCD", "CONFCD"],
        "REFERENCE",
        "LANDSIZE",
        "fl-panhandle-12033",
        ownerField="OWNER",
        situsField="SITEADDR",
        cityField="CITY",
        zipField="ZIP",
        dorField="DORCD",
        marketValueField="CURRMKT",
        assessedField="CAPPEDVALUE",
        mail1Field="MAILADDRESS1",
        mail2Field="MAILADDRESS2",
        mailCityField="MAILCITY",
        mailStateField="MAILSTATE",
        mailZipField="MAILZIP",
        fdorCo=27,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
    ),
    "12037": {
        "kind": "franklin",
        "fips": "12037",
        "name": "Franklin",
        "url": "https://gis.arpc.org/server/rest/services/Hosted/Parcels_2023/FeatureServer/0/query",
        "source": "fl-franklin-parcels-2023-12037",
        "fdorCo": 29,
        "fdorKey": "exact",
    },
    "12045": arcgis(
        "12045",
        "Gulf",
        "https://arcgis5.roktech.net/arcgis/rest/services/gulf/GoMaps4/MapServer/12/query",
        "ACREAGE>=5 AND ACREAGE<=150",
        ["PIN_NODELIM", "PIN_DSP", "ACREAGE", "OWNER_NAME", "ADDRESS_1", "CITY_NAME", "ST", "ZIPCODE", "HOUSE_NO", "STREET", "ST_CITY", "USECD"],
        "PIN_NODELIM",
        "ACREAGE",
        "fl-gulf-gomaps4-12045",
        ownerField="OWNER_NAME",
        mail1Field="ADDRESS_1",
        mailCityField="CITY_NAME",
        mailStateField="ST",
        mailZipField="ZIPCODE",
        cityField="ST_CITY",
        dorField="USECD",
        situsParts=["HOUSE_NO", "STREET"],
        fdorCo=33,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
        fdorOwner=True,
    ),
    "12057": arcgis(
        "12057",
        "Hillsborough",
        "https://maps.hillsboroughcounty.org/arcgis1a/rest/services/SDEMapServices/ParcelPublishing/MapServer/12/query",
        "ACREAGE>=5 AND ACREAGE<=150",
        ["FOLIO", "STRAP", "ACREAGE", "OWNER", "ADDR_1", "ADDR_2", "CITY", "STATE", "ZIP", "SITE_ADDR", "SITE_CITY", "SITE_ZIP", "S_AMT", "S_DATE", "JUST", "ASD_VAL", "TAX_VAL", "DOR_CODE"],
        "FOLIO",
        "ACREAGE",
        "fl-hillsborough-parcelpublishing-12",
        ownerField="OWNER",
        situsField="SITE_ADDR",
        cityField="SITE_CITY",
        zipField="SITE_ZIP",
        dorField="DOR_CODE",
        salePriceField="S_AMT",
        saleDateField="S_DATE",
        marketValueField="JUST",
        assessedField="ASD_VAL",
        taxableField="TAX_VAL",
        mail1Field="ADDR_1",
        mail2Field="ADDR_2",
        mailCityField="CITY",
        mailStateField="STATE",
        mailZipField="ZIP",
        fdorCo=39,
        fdorKey="token",
        fdorToken="STRAP",
        fdorTax=True,
        fdorSale=True,
    ),
    "12065": arcgis(
        "12065",
        "Jefferson",
        "https://services5.arcgis.com/vFMp1Ly1q6rKKp0o/arcgis/rest/services/JC__PARCELS_view/FeatureServer/0/query",
        "COGO_ACRES>=5 AND COGO_ACRES<=150",
        ["PARCELID", "COGO_ACRES", "Prop_ID"],
        "PARCELID",
        "COGO_ACRES",
        "fl-jefferson-pa-parcels-12065",
        fdorCo=43,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
        fdorOwner=True,
        fdorSitus=True,
    ),
    "12071": arcgis(
        "12071",
        "Lee",
        "https://gismapserver.leegov.com/gisserver910/rest/services/Layers/ParcelAddress/MapServer/0/query",
        "GISACRES>=5 AND GISACRES<=150 AND CONDOTYPE IS NULL",
        ["STRAP", "FOLIOID", "GISACRES", "O_NAME", "O_OTHERS", "O_ADDR1", "O_ADDR2", "O_CITY", "O_STATE", "O_ZIP", "SITEADDR", "SITECITY", "SITEZIP", "S_1AMOUNT", "S_1DATE", "JUST", "ASSESSED", "TAXABLE", "ZONING", "DORCODE", "HIDE_STRAP"],
        "STRAP",
        "GISACRES",
        "fl-lee-parceladdress",
        ownerField="O_NAME",
        situsField="SITEADDR",
        cityField="SITECITY",
        zipField="SITEZIP",
        dorField="DORCODE",
        zoningField="ZONING",
        salePriceField="S_1AMOUNT",
        saleDateField="S_1DATE",
        marketValueField="JUST",
        assessedField="ASSESSED",
        taxableField="TAXABLE",
        mail1Field="O_ADDR1",
        mail2Field="O_ADDR2",
        mailCityField="O_CITY",
        mailStateField="O_STATE",
        mailZipField="O_ZIP",
        fdorCo=46,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
    ),
    "12073": arcgis(
        "12073",
        "Leon",
        "https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/TLC_OverlayParnal_D_WM/MapServer/0/query",
        "CALC_ACREA>=5 AND CALC_ACREA<=150",
        ["TAXID", "CALC_ACREA", "OWNER1", "OWNER2", "ADDR1", "ADDR2", "ADDR3", "ZIP1", "SITEADDR", "PRICE_S1", "SALEDTE_S1", "QUAL_S1", "PYR_MARKET", "PYR_TAXABL", "PROP_USE", "SECURE"],
        "TAXID",
        "CALC_ACREA",
        "fl-leon-overlay-parcel-12073",
        fallbackUrl="https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/TLC_OverlayParcel_D_WM/MapServer/0/query",
        ownerField="OWNER1",
        situsField="SITEADDR",
        dorField="PROP_USE",
        salePriceField="PRICE_S1",
        saleDateField="SALEDTE_S1",
        marketValueField="PYR_MARKET",
        assessedField="PYR_TAXABL",
        mail1Field="ADDR1",
        mail2Field="ADDR2",
        mailZipField="ZIP1",
        fdorCo=47,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
    ),
    "12085": arcgis(
        "12085",
        "Martin",
        "https://geoweb.martin.fl.us/arcgis/rest/services/Administrative_Areas/base_map/MapServer/10/query",
        "AREA_ACRES>=5 AND AREA_ACRES<=150",
        ["PCN", "AIN", "ACCOUNT", "AREA_ACRES", "OWNER", "MAIL_ADDRESS", "MAIL_CITY", "MAIL_STATE", "MAIL_ZIP", "SITUS_HOUSE_", "SITUS_PREFIX", "SITUS_STREET", "SITUS_STREET_TYPE", "SITUS_CITY", "SITUS_ZIP", "DOR_CODE"],
        "PCN",
        "AREA_ACRES",
        "fl-martin-geoweb-12085",
        ownerField="OWNER",
        cityField="SITUS_CITY",
        zipField="SITUS_ZIP",
        dorField="DOR_CODE",
        mail1Field="MAIL_ADDRESS",
        mailCityField="MAIL_CITY",
        mailStateField="MAIL_STATE",
        mailZipField="MAIL_ZIP",
        situsParts=["SITUS_HOUSE_", "SITUS_PREFIX", "SITUS_STREET", "SITUS_STREET_TYPE"],
        fdorCo=53,
        fdorKey="martin",
        fdorTax=True,
        fdorSale=True,
    ),
    "12086": arcgis(
        "12086",
        "Miami-Dade",
        "https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/26/query",
        "LOT_SIZE>=217800 AND LOT_SIZE<=6534000",
        ["FOLIO", "TRUE_OWNER1", "TRUE_OWNER2", "TRUE_MAILING_ADDR1", "TRUE_MAILING_CITY", "TRUE_MAILING_STATE", "TRUE_MAILING_ZIP_CODE", "TRUE_SITE_ADDR", "TRUE_SITE_CITY", "TRUE_SITE_ZIP_CODE", "TOTAL_VAL_CUR", "DOR_CODE_CUR", "LOT_SIZE"],
        "FOLIO",
        "LOT_SIZE",
        "fl-miami-dade-landinformation-26",
        acresScale=43560,
        merge=True,
        ownerField="TRUE_OWNER1",
        situsField="TRUE_SITE_ADDR",
        cityField="TRUE_SITE_CITY",
        zipField="TRUE_SITE_ZIP_CODE",
        dorField="DOR_CODE_CUR",
        marketValueField="TOTAL_VAL_CUR",
        mail1Field="TRUE_MAILING_ADDR1",
        mailCityField="TRUE_MAILING_CITY",
        mailStateField="TRUE_MAILING_STATE",
        mailZipField="TRUE_MAILING_ZIP_CODE",
        fdorCo=23,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
    ),
    "12089": arcgis(
        "12089",
        "Nassau",
        "https://maps.ncpafl.com/ncflpa_arcgis/rest/services/nassau/NassauCountyPublicTaxMap/MapServer/144/query",
        "GISCalculatedAcre>=5 AND GISCalculatedAcre<=150",
        ["PIN", "GISCalculatedAcre", "Name", "Maddr_1", "Mcity", "Mstate", "Mzip", "Situs_full", "Just_val", "parcel_use_cd"],
        "PIN",
        "GISCalculatedAcre",
        "fl-nassau-taxmap-12089",
        dedupe=True,
        ownerField="Name",
        situsField="Situs_full",
        dorField="parcel_use_cd",
        marketValueField="Just_val",
        mail1Field="Maddr_1",
        mailCityField="Mcity",
        mailStateField="Mstate",
        mailZipField="Mzip",
        fdorCo=55,
        fdorKey="dash",
        fdorTax=True,
        fdorSale=True,
    ),
    "12095": arcgis(
        "12095",
        "Orange",
        "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/56/query",
        "ACREAGE BETWEEN 5 AND 150",
        ["PARCEL", "ACREAGE", "NAME1", "NAME2", "ADD1", "ADD2", "CITY", "STATE", "ZIP", "SITUS", "CITY_SITUS", "ZIP_SITUS", "SALE_DATE", "SALE_ADJ_VALUE", "QUAL_CODE", "TOTAL_MKT", "TOTAL_ASSD", "TAXABLE", "DOR_CODE"],
        "PARCEL",
        "ACREAGE",
        "fl-orange-agol-open-data-12095",
        ownerField="NAME1",
        situsField="SITUS",
        cityField="CITY_SITUS",
        zipField="ZIP_SITUS",
        dorField="DOR_CODE",
        salePriceField="SALE_ADJ_VALUE",
        saleDateField="SALE_DATE",
        marketValueField="TOTAL_MKT",
        assessedField="TOTAL_ASSD",
        taxableField="TAXABLE",
        mail1Field="ADD1",
        mail2Field="ADD2",
        mailCityField="CITY",
        mailStateField="STATE",
        mailZipField="ZIP",
        featureMarkets=["Orlando"],
        fdorCo=58,
        fdorKey="orange",
        fdorTax=True,
        fdorSale=True,
    ),
    "12097": arcgis(
        "12097",
        "Osceola",
        "https://gis.osceola.org/hosting/rest/services/Parcels/MapServer/3/query",
        "TotalAcres>=5 AND TotalAcres<=150",
        ["PIN", "TotalAcres", "Owner1", "Owner2", "BillingAdd", "BillingA_1", "City", "State", "Zip", "StreetNumb", "StreetName", "LocCity", "LocZip", "SalePrice", "SaleDate", "Q_U", "CurrJust", "AssessedVa", "DORCode"],
        "PIN",
        "TotalAcres",
        "osceola-parcels-12097",
        insecure=True,
        ownerField="Owner1",
        cityField="LocCity",
        zipField="LocZip",
        dorField="DORCode",
        salePriceField="SalePrice",
        saleDateField="SaleDate",
        marketValueField="CurrJust",
        assessedField="AssessedVa",
        mail1Field="BillingAdd",
        mail2Field="BillingA_1",
        mailCityField="City",
        mailStateField="State",
        mailZipField="Zip",
        situsParts=["StreetNumb", "StreetName"],
        featureMarkets=["Orlando"],
        fdorCo=59,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
    ),
    "12111": arcgis(
        "12111",
        "St. Lucie",
        "https://slcgis.stlucieco.gov/hosting/rest/services/Parcel_Boundaries/FeatureServer/0/query",
        "TOTAL_ACRE>=5 AND TOTAL_ACRE<=150 AND ParcelID IS NOT NULL AND ParcelID<>''",
        ["ParcelID", "AccountNumber", "TOTAL_ACRE", "CuO1LastName", "CuO1FirstName", "CuO2LastName", "CuO2FirstName", "CuOStreet1", "CuOStreet2", "CuOCity", "CuOState", "CuOPostal", "StreetNumber", "StreetName", "LocationCity", "TotalAppraisedValue", "LUC", "IsConfidential"],
        "ParcelID",
        "TOTAL_ACRE",
        "fl-slc-parcels-12111",
        dorField="LUC",
        marketValueField="TotalAppraisedValue",
        cityField="LocationCity",
        situsParts=["StreetNumber", "StreetName"],
        mail1Field="CuOStreet1",
        mail2Field="CuOStreet2",
        mailCityField="CuOCity",
        mailStateField="CuOState",
        mailZipField="CuOPostal",
        fdorCo=66,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
    ),
    "12127": arcgis(
        "12127",
        "Volusia",
        "https://maps5.vcgov.org/arcgis/rest/services/Open_Data/Open_Data_3/FeatureServer/34/query",
        "CALCACRES>=5 AND CALCACRES<=150",
        ["PID", "ALTKEY", "CALCACRES", "OWNER1", "MAILADDR1", "MAILADDR2", "MAILCITY", "MAILSTATE", "MAILZIP", "ADDRFULL", "CITYNAME", "ZIP1", "LASTSALEPRICE", "LASTSALEDT", "TOTJUST", "PC"],
        "PID",
        "CALCACRES",
        "fl-volusia-open-data-12127",
        ownerField="OWNER1",
        situsField="ADDRFULL",
        cityField="CITYNAME",
        zipField="ZIP1",
        dorField="PC",
        salePriceField="LASTSALEPRICE",
        saleDateField="LASTSALEDT",
        marketValueField="TOTJUST",
        mail1Field="MAILADDR1",
        mail2Field="MAILADDR2",
        mailCityField="MAILCITY",
        mailStateField="MAILSTATE",
        mailZipField="MAILZIP",
        fdorCo=74,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
    ),
    "12129": arcgis(
        "12129",
        "Wakulla",
        "https://services9.arcgis.com/vAltLjtfYIJc7pDt/arcgis/rest/services/ParcelM/FeatureServer/0/query",
        "MAP_ACRES>=5 AND MAP_ACRES<=150",
        ["PARCEL_ID", "MAP_ACRES"],
        "PARCEL_ID",
        "MAP_ACRES",
        "fl-wakulla-parcelm-12129",
        fdorCo=75,
        fdorKey="dash",
        fdorTax=True,
        fdorSale=True,
        fdorOwner=True,
        fdorSitus=True,
    ),
    "12133": arcgis(
        "12133",
        "Washington",
        "https://services2.arcgis.com/xDFo56nFuq1SBnBw/arcgis/rest/services/WashingtonParcelsAGOL/FeatureServer/0/query",
        "CALC_ACRES>=5 AND CALC_ACRES<=150",
        ["PARCELNO", "CALC_ACRES", "SITE_ADDRE", "CITY"],
        "PARCELNO",
        "CALC_ACRES",
        "fl-washington-agol-12133",
        situsField="SITE_ADDRE",
        cityField="CITY",
        fdorCo=77,
        fdorKey="exact",
        fdorTax=True,
        fdorSale=True,
        fdorOwner=True,
        fdorSitus=True,
    ),
}


def id_text(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return usable_parcel_id(value)


def martin_redash(pcn: str) -> str:
    digits = re.sub(r"\D", "", pcn)
    if len(digits) != 18:
        return pcn
    return f"{digits[0:2]}-{digits[2:4]}-{digits[4:6]}-{digits[6:9]}-{digits[9:12]}-{digits[12:17]}-{digits[17]}"


def orange_swap(parcel: str) -> str:
    if len(parcel) < 6:
        return parcel
    return parcel[4:6] + parcel[2:4] + parcel[0:2] + parcel[6:]


def franklin_gsa(parcelno: str) -> str:
    if len(parcelno) < 8:
        return parcelno
    head, rest = parcelno[:8], parcelno[8:]
    return f"{head[5:8]}{head[2:5]}{head[:2]}{rest}"


def mmyyyy(value: Any) -> str | None:
    text = meaningful(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) == 6 and text.count("-") == 0 and not text[:4].isdigit():
        month, year = int(digits[:2]), int(digits[2:])
        if 1 <= month <= 12 and 1900 <= year <= 2100:
            return f"{year:04d}-{month:02d}-01"
    if re.fullmatch(r"\d{2}/\d{4}", text):
        month, year = int(text[:2]), int(text[3:])
        if 1 <= month <= 12 and 1900 <= year <= 2100:
            return f"{year:04d}-{month:02d}-01"
    return None


def blank_mail() -> dict[str, None]:
    return dict(BLANK_MAIL)


def confidential_flag(value: Any) -> bool:
    if value is None or value is False:
        return False
    if value is True:
        return True
    text = str(value).strip().upper()
    return text in {"1", "Y", "YES", "TRUE", "S"}


def clear_owner(props: dict, *, situs: bool = False, mail_only: bool = False) -> None:
    if not mail_only:
        props["ownerName"] = None
        props["ownerName2"] = None
        props["_suppressOwner"] = True
    props["mailingAddress"] = blank_mail()
    props["_suppressMail"] = True
    if situs:
        props["situsAddress"] = None
        props["situsCity"] = None
        props["situsZip"] = None
        props["_suppressSitus"] = True


def apply_privacy(spec: dict, attrs: dict, props: dict) -> None:
    fips = spec["fips"]
    if fips == "12033" and str(attrs.get("CONFCD") or "").strip().upper() == "Y":
        clear_owner(props, situs=True)
    elif fips == "12057" and "CONFIDENTIAL" in str(attrs.get("OWNER") or props.get("ownerName") or "").upper():
        clear_owner(props, mail_only=True)
    elif fips == "12095" and str(attrs.get("NAME1") or "").strip().upper() == "CONFIDENTIAL":
        clear_owner(props)
    elif fips == "12073" and str(attrs.get("SECURE") or "").strip().upper() == "S":
        clear_owner(props)
    elif fips == "12111" and confidential_flag(attrs.get("IsConfidential")):
        clear_owner(props)
    elif fips == "12071":
        hidden = str(attrs.get("HIDE_STRAP") or "").strip().upper() in {"Y", "C"}
        obor = str(attrs.get("O_NAME") or props.get("ownerName") or "").strip().upper() == "OBOR"
        if hidden or obor:
            clear_owner(props)
    if fips == "12111" and not props.get("_suppressOwner"):
        last = meaningful(attrs.get("CuO1LastName"))
        first = meaningful(attrs.get("CuO1FirstName"))
        owner = " ".join(part for part in (last, first) if part) or None
        if owner and owner.strip().upper() == "RESIDENT":
            owner = None
        props["ownerName"] = owner
        last2 = meaningful(attrs.get("CuO2LastName"))
        first2 = meaningful(attrs.get("CuO2FirstName"))
        owner2 = " ".join(part for part in (last2, first2) if part) or None
        if owner2 and owner2.strip().upper() == "RESIDENT":
            owner2 = None
        props["ownerName2"] = owner2
        mail = props.get("mailingAddress") or {}
        if str(mail.get("line1") or "").strip().upper() == "TBD":
            props["mailingAddress"] = blank_mail()
    if fips == "12095" and not props.get("_suppressOwner"):
        props["ownerName2"] = meaningful(attrs.get("NAME2"))
    if fips == "12073" and not props.get("_suppressOwner"):
        props["ownerName2"] = meaningful(attrs.get("OWNER2"))
    if fips == "12071" and not props.get("_suppressOwner"):
        props["ownerName2"] = meaningful(attrs.get("O_OTHERS"))
    if fips == "12097" and not props.get("lastSale", {}).get("qualified"):
        props["lastSale"]["qualified"] = meaningful(attrs.get("Q_U"))
    if fips == "12073" and not props.get("lastSale", {}).get("qualified"):
        props["lastSale"]["qualified"] = meaningful(attrs.get("QUAL_S1"))
    if fips == "12095" and not props.get("lastSale", {}).get("qualified"):
        props["lastSale"]["qualified"] = meaningful(attrs.get("QUAL_CODE"))
    sold = props.get("lastSale", {}).get("date")
    if not sold:
        parsed = mmyyyy(attrs.get(spec.get("saleDateField") or ""))
        if parsed:
            props["lastSale"]["date"] = parsed
    token_field = (LINKS.get(fips) or {}).get("token")
    if token_field:
        token = id_text(attrs.get(token_field))
        if token:
            props["_linkToken"] = token


def fdor_lookup_key(spec: dict, parcel_id: str, props: dict) -> str:
    mode = spec.get("fdorKey")
    if mode == "dash":
        return dash_strip(parcel_id)
    if mode == "martin":
        return martin_redash(parcel_id)
    if mode == "orange":
        return orange_swap(parcel_id)
    if mode == "token":
        return str(props.get("_linkToken") or parcel_id)
    return parcel_id


def install_fetch(insecure: bool) -> Any:
    if not insecure:
        return None
    original = seed.fetch_json

    def wrapped(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
        try:
            return original(url, params, timeout=timeout, retries=2)
        except Exception as exc:  # noqa: BLE001
            text = str(exc).upper()
            if "CERTIFICATE" not in text and "SSL" not in text and "TLS" not in text:
                raise
            print("  Osceola TLS chain incomplete; public GET continues without verifying the leaf", flush=True)
            query = url
            if params:
                import urllib.parse

                query = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
            req = urllib.request.Request(query, headers={"User-Agent": "darryl-land-search/market-parcels"})
            with urllib.request.urlopen(req, timeout=timeout, context=ssl._create_unverified_context()) as resp:
                return json.loads(resp.read().decode("utf-8"))

    seed.fetch_json = wrapped
    return original


def restore_fetch(original: Any) -> None:
    if original is not None:
        seed.fetch_json = original


def collect_ids(url: str, where: str) -> tuple[list[int], int]:
    count = seed.count_where(url, where)
    try:
        ids = seed.fetch_object_ids(url, where)
    except Exception as exc:  # noqa: BLE001
        print(f"  returnIdsOnly failed ({exc}); paging", flush=True)
        ids = []
    if ids and (count == 0 or len(ids) >= int(count * 0.98)):
        return ids, count
    print(f"  ids {len(ids)} count {count}; resultOffset paging", flush=True)
    return ids, count


def page_rows(url: str, where: str, fields: list[str]) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    page = 500
    while offset < 250000:
        data = seed.fetch_json(
            url,
            {
                "where": where,
                "outFields": ",".join(fields),
                "returnGeometry": "true",
                "outSR": "4326",
                "resultOffset": str(offset),
                "resultRecordCount": str(page),
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:240])
        batch = data.get("features") or []
        rows.extend(batch)
        print(f"    offset {offset} +{len(batch)}", flush=True)
        if len(batch) < page:
            break
        offset += len(batch)
    return rows


def pull_rows(spec: dict) -> tuple[list[dict], int]:
    ids, count = collect_ids(spec["url"], spec["where"])
    if ids and (not count or len(ids) >= int(count * 0.98)):
        raw = seed.fetch_by_ids(spec["url"], ids, spec["outFields"])
        return raw, count or len(ids)
    raw = page_rows(spec["url"], spec["where"], spec["outFields"])
    return raw, count or len(raw)


def feature_markets(spec: dict, markets: list[str]) -> list[str]:
    return list(spec.get("featureMarkets") or markets)


def row_is_sensitive(spec: dict, attrs: dict) -> bool:
    fips = spec["fips"]
    if fips == "12033" and str(attrs.get("CONFCD") or "").strip().upper() == "Y":
        return True
    if fips == "12057" and "CONFIDENTIAL" in str(attrs.get("OWNER") or "").upper():
        return True
    if fips == "12095" and str(attrs.get("NAME1") or "").strip().upper() == "CONFIDENTIAL":
        return True
    if fips == "12073" and str(attrs.get("SECURE") or "").strip().upper() == "S":
        return True
    if fips == "12111" and confidential_flag(attrs.get("IsConfidential")):
        return True
    if fips == "12071":
        hidden = str(attrs.get("HIDE_STRAP") or "").strip().upper() in {"Y", "C"}
        obor = str(attrs.get("O_NAME") or "").strip().upper() == "OBOR"
        return hidden or obor
    return False


def existing_props(fips: str) -> dict[str, dict]:
    folders = [seed.COUNTY_DIR / fips / "tiles"]
    if fips in ORLANDO_FIPS:
        folders.insert(0, ROOT / "data" / "fixtures" / "orlando-parcels" / "tiles" / fips)
    found: dict[str, dict] = {}
    for folder in folders:
        if not folder.exists():
            continue
        for path in folder.glob("*.geojson"):
            data = json.loads(path.read_text())
            for feature in data.get("features") or []:
                props = feature.get("properties") or {}
                parcel_id = props.get("parcelId")
                if parcel_id and str(parcel_id) not in found:
                    found[str(parcel_id)] = props
    return found


def rows_to_features(raw: list[dict], spec: dict, county: dict, markets: list[str]) -> tuple[list[dict], int]:
    if spec.get("merge"):
        return merge_rows(raw, spec, county, markets)
    normalize_spec = dict(spec)
    features, dropped = seed.normalize_rows(raw, county, feature_markets(spec, markets), normalize_spec)
    attrs_by_id: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        parcel_id = seed.clean(attrs.get(spec["idField"]))
        if not parcel_id:
            continue
        current = attrs_by_id.get(parcel_id)
        if current is None or row_is_sensitive(spec, attrs):
            attrs_by_id[parcel_id] = attrs
    kept: list[dict] = []
    for feature in features:
        props = feature["properties"]
        parcel_id = props["parcelId"]
        if spec["fips"] == "12065" and "0RDS" in parcel_id.upper():
            dropped += 1
            continue
        attrs = attrs_by_id.get(parcel_id) or {}
        apply_privacy(spec, attrs, props)
        kept.append(feature)
    return kept, dropped


def merge_rows(raw: list[dict], spec: dict, county: dict, markets: list[str]) -> tuple[list[dict], int]:
    grouped: dict[str, dict[str, Any]] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        parcel_id = id_text(attrs.get(spec["idField"]))
        if not parcel_id:
            dropped += 1
            continue
        acres = seed.num(attrs.get(spec["acresField"]))
        scale = spec.get("acresScale") or 1
        if acres is not None and scale != 1:
            acres = acres / scale
        if not seed.in_band(acres):
            dropped += 1
            continue
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        bucket = grouped.setdefault(parcel_id, {"attrs": attrs, "geoms": [], "acres": acres})
        if geometry:
            bucket["geoms"].append(geometry)
        if row_is_sensitive(spec, attrs) or (
            (attrs.get(spec.get("ownerField") or "") or "") and not (bucket["attrs"].get(spec.get("ownerField") or "") or "")
        ):
            bucket["attrs"] = attrs
        if acres and (bucket["acres"] or 0) < acres:
            bucket["acres"] = acres
    features: list[dict] = []
    for parcel_id, bucket in grouped.items():
        geometry = merge_polygons(bucket["geoms"])
        center = seed.centroid_of(geometry) if geometry else None
        if not geometry or not seed.plausible_centroid(center):
            dropped += 1
            continue
        attrs = bucket["attrs"]
        feature = build_feature(spec, county, markets, parcel_id, bucket["acres"], geometry, center, attrs)
        apply_privacy(spec, attrs, feature["properties"])
        features.append(feature)
    return features, dropped


def merge_polygons(geometries: list[dict]) -> dict | None:
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


def build_feature(spec, county, markets, parcel_id, acres, geometry, center, attrs) -> dict:
    situs = meaningful(attrs.get(spec["situsField"])) if spec.get("situsField") else None
    if not situs and spec.get("situsParts"):
        parts = [meaningful(attrs.get(key)) for key in spec["situsParts"]]
        situs = " ".join(part for part in parts if part) or None
    price = seed.num(attrs.get(spec["salePriceField"])) if spec.get("salePriceField") else None
    if price is not None and price <= 0:
        price = None
    sold = None
    if spec.get("saleDateField"):
        sold = sale_iso(attrs.get(spec["saleDateField"])) or mmyyyy(attrs.get(spec["saleDateField"]))
    return seed.empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=feature_markets(spec, markets),
        parcel_id=parcel_id,
        acreage=acres,
        geometry=geometry,
        center=center,
        source=spec["source"],
        owner=meaningful(attrs.get(spec["ownerField"])) if spec.get("ownerField") else None,
        situs=situs,
        city=meaningful(attrs.get(spec["cityField"])) if spec.get("cityField") else None,
        zip_code=seed.zip_str(attrs.get(spec["zipField"])) if spec.get("zipField") else None,
        zoning=meaningful(attrs.get(spec["zoningField"])) if spec.get("zoningField") else None,
        dor=meaningful(attrs.get(spec["dorField"])) if spec.get("dorField") else None,
        sale_price=price,
        sale_date=sold,
        market_value=seed.num(attrs.get(spec["marketValueField"])) if spec.get("marketValueField") else None,
        assessed=seed.num(attrs.get(spec["assessedField"])) if spec.get("assessedField") else None,
        taxable=seed.num(attrs.get(spec["taxableField"])) if spec.get("taxableField") else None,
        mail1=meaningful(attrs.get(spec["mail1Field"])) if spec.get("mail1Field") else None,
        mail2=meaningful(attrs.get(spec["mail2Field"])) if spec.get("mail2Field") else None,
        mail_city=meaningful(attrs.get(spec["mailCityField"])) if spec.get("mailCityField") else None,
        mail_state=meaningful(attrs.get(spec["mailStateField"])) if spec.get("mailStateField") else None,
        mail_zip=seed.zip_str(attrs.get(spec["mailZipField"])) if spec.get("mailZipField") else None,
    )


def fdor_attributes(co_no: int, keys: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    unique = [key for key in dict.fromkeys(keys) if key]
    for start in range(0, len(unique), 40):
        chunk = unique[start : start + 40]
        quoted = ",".join("'" + value.replace("'", "''") + "'" for value in chunk)
        data = seed.fetch_json(
            FDOR_URL,
            {
                "where": f"CO_NO={int(co_no)} AND PARCEL_ID IN ({quoted})",
                "outFields": ",".join(FDOR_FIELDS),
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=120,
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:240])
        for item in data.get("features") or []:
            attrs = item.get("attributes") or {}
            if int(attrs.get("CO_NO") or 0) != int(co_no):
                continue
            parcel_id = usable_parcel_id(attrs.get("PARCEL_ID"))
            if parcel_id and parcel_id not in found:
                found[parcel_id] = attrs
        if start and start % 400 == 0:
            print(f"    FDOR {min(start + 40, len(unique))}/{len(unique)}", flush=True)
    return found


def fill_fdor(props: dict, attrs: dict, spec: dict) -> None:
    tax = props.setdefault("tax", {})
    if spec.get("fdorTax"):
        just = seed.num(attrs.get("JV"))
        assessed = seed.num(attrs.get("AV_SD"))
        taxable = seed.num(attrs.get("TV_SD"))
        if just and just > 0 and not tax.get("marketValue"):
            tax["marketValue"] = just
        if assessed and assessed > 0 and not tax.get("assessedValue"):
            tax["assessedValue"] = assessed
        if taxable is not None and taxable > 0 and not tax.get("taxableValue"):
            tax["taxableValue"] = taxable
        if not props.get("dorCode"):
            props["dorCode"] = meaningful(attrs.get("DOR_UC"))
    sale = props.setdefault("lastSale", {})
    if spec.get("fdorSale"):
        price = seed.num(attrs.get("SALE_PRC1"))
        if price and price > 0 and not sale.get("price"):
            sale["price"] = price
        if not sale.get("date"):
            sale["date"] = seed.sale_date(attrs.get("SALE_YR1"), attrs.get("SALE_MO1"))
        if not sale.get("qualified"):
            sale["qualified"] = meaningful(attrs.get("QUAL_CD1"))
    if spec.get("fdorOwner") and not props.get("_suppressOwner") and not props.get("ownerName"):
        props["ownerName"] = meaningful(attrs.get("OWN_NAME"))
    if spec.get("fdorOwner") and not props.get("_suppressMail"):
        mail = props.setdefault("mailingAddress", blank_mail())
        if not mail.get("line1"):
            mail["line1"] = meaningful(attrs.get("OWN_ADDR1"))
            mail["line2"] = meaningful(attrs.get("OWN_ADDR2"))
            mail["city"] = meaningful(attrs.get("OWN_CITY"))
            mail["state"] = meaningful(attrs.get("OWN_STATE"))
            mail["zip"] = seed.zip_str(attrs.get("OWN_ZIPCD"))
    if spec.get("fdorSitus") and not props.get("_suppressSitus") and not props.get("situsAddress"):
        props["situsAddress"] = meaningful(attrs.get("PHY_ADDR1"))
        props["situsCity"] = props.get("situsCity") or meaningful(attrs.get("PHY_CITY"))
        props["situsZip"] = props.get("situsZip") or seed.zip_str(attrs.get("PHY_ZIPCD"))


def join_fdor(features: list[dict], spec: dict) -> None:
    if not spec.get("fdorCo"):
        return
    keys = [fdor_lookup_key(spec, feature["properties"]["parcelId"], feature["properties"]) for feature in features]
    table = fdor_attributes(int(spec["fdorCo"]), keys)
    hit = 0
    for feature in features:
        props = feature["properties"]
        item = table.get(fdor_lookup_key(spec, props["parcelId"], props))
        if not item:
            continue
        hit += 1
        fill_fdor(props, item, spec)
    print(f"  FDOR CO_NO={spec['fdorCo']} hits {hit}/{len(features)}", flush=True)


def attach_links(feature: dict) -> None:
    props = feature["properties"]
    link = LINKS[props["countyFips"]]
    props["gisViewerUrl"] = link.get("gis")
    token = props.get("_linkToken") or props.get("parcelId")
    mode = link.get("id")
    if mode == "nodash" and token:
        token = nodash(str(token))
    if mode == "franklin" and props.get("parcelId"):
        token = franklin_gsa(str(props["parcelId"]))
    url = apply_template(link.get("appraiser"), str(token)) if token else None
    if url:
        props["appraiserUrl"] = url
    for key in list(props):
        if key.startswith("_"):
            props.pop(key, None)


def scrub(features: list[dict]) -> None:
    sanitize(features)
    for feature in features:
        props = feature["properties"]
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        for key in list(props):
            if key.startswith("_") or re.search(r"phone|email", key, re.I):
                props.pop(key, None)


def pull_arcgis(spec: dict, county: dict, markets: list[str]) -> tuple[list[dict], int, int]:
    original = install_fetch(bool(spec.get("insecure")))
    try:
        if spec.get("fallbackUrl"):
            try:
                seed.count_where(spec["url"], "1=1")
            except Exception as exc:  # noqa: BLE001
                print(f"  primary unavailable ({exc}); using {spec['fallbackUrl']}", flush=True)
                spec["url"] = spec["fallbackUrl"]
        raw, count = pull_rows(spec)
    finally:
        restore_fetch(original)
    print(f"  source rows {count} fetched {len(raw)}", flush=True)
    features, dropped = rows_to_features(raw, spec, county, markets)
    join_fdor(features, spec)
    for feature in features:
        attach_links(feature)
    scrub(features)
    return features, count or len(raw), dropped


def pull_franklin(spec: dict, county: dict, markets: list[str]) -> tuple[list[dict], int, int]:
    ids, count = collect_ids(spec["url"], "1=1")
    print(f"  Franklin fabric {count} ids {len(ids)}", flush=True)
    fields = ["parcelno", "parcelid"]
    raw = seed.fetch_by_ids(spec["url"], ids, fields) if ids else page_rows(spec["url"], "1=1", fields)
    features: list[dict] = []
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        parcel_id = id_text(attrs.get("parcelno"))
        rings = (item.get("geometry") or {}).get("rings") or []
        if not parcel_id or not rings:
            dropped += 1
            continue
        try:
            acres = geodesic_acres(rings)
        except Exception:  # noqa: BLE001
            from parcel_geometry import net_acres

            acres = net_acres(rings)
        if not seed.in_band(acres):
            continue
        geometry = esri_rings_to_geojson(rings)
        center = seed.centroid_of(geometry) if geometry else None
        if not geometry or not seed.plausible_centroid(center):
            dropped += 1
            continue
        feature = seed.empty_feature(
            fips="12037",
            county="Franklin",
            state="Florida",
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source=spec["source"],
        )
        features.append(feature)
    print(f"  Franklin in band {len(features)}", flush=True)
    join_fdor(features, {**spec, "fdorOwner": True, "fdorTax": True, "fdorSale": True, "fdorSitus": True})
    for feature in features:
        attach_links(feature)
    scrub(features)
    return features, len(features) + dropped, dropped


def pull_charlotte(spec: dict, county: dict, markets: list[str]) -> tuple[list[dict], int, int]:
    where = "AREANO>=5 AND AREANO<=150 AND PARCELID<>''"
    ids, count = collect_ids(SWFWMD_CHARLOTTE, where)
    print(f"  SWFWMD Charlotte {count} ids {len(ids)}", flush=True)
    fields = ["PARCELID", "AREANO", "SALE1_AMT", "SALE1_DATE"]
    raw = seed.fetch_by_ids(SWFWMD_CHARLOTTE, ids, fields) if len(ids) >= int((count or 1) * 0.9) else page_rows(SWFWMD_CHARLOTTE, where, fields)
    acres_by_id: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        parcel_id = id_text(attrs.get("PARCELID"))
        acres = seed.num(attrs.get("AREANO"))
        if not parcel_id or not seed.in_band(acres):
            continue
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        current = acres_by_id.get(parcel_id)
        if current is None or (acres or 0) > (current.get("acres") or 0):
            acres_by_id[parcel_id] = {"acres": acres, "geometry": geometry, "sale": seed.num(attrs.get("SALE1_AMT")), "sold": sale_iso(attrs.get("SALE1_DATE"))}
    print(f"  SWFWMD distinct {len(acres_by_id)}", flush=True)
    county_fields = [
        "ACCOUNT",
        "ownersname",
        "mailingaddress",
        "mailingaddress2",
        "city",
        "state",
        "zipcode",
        "propertyaddress",
        "zoningcode",
        "usecode",
        "totvalue",
        "assessedvalue",
        "lastsaleno70cent",
    ]
    county_attrs: dict[str, dict] = {}
    county_geom: dict[str, dict] = {}
    keys = list(acres_by_id)
    for start in range(0, len(keys), 40):
        chunk = keys[start : start + 40]
        quoted = ",".join("'" + value.replace("'", "''") + "'" for value in chunk)
        data = seed.fetch_json(
            spec["url"],
            {
                "where": f"ACCOUNT IN ({quoted})",
                "outFields": ",".join(county_fields),
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:240])
        for item in data.get("features") or []:
            attrs = item.get("attributes") or {}
            account = id_text(attrs.get("ACCOUNT"))
            if not account:
                continue
            county_attrs[account] = attrs
            geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
            if geometry:
                county_geom[account] = geometry
        if start and start % 400 == 0:
            print(f"    county {min(start + 40, len(keys))}/{len(keys)}", flush=True)
    features: list[dict] = []
    dropped = 0
    for parcel_id, row in acres_by_id.items():
        attrs = county_attrs.get(parcel_id) or {}
        geometry = county_geom.get(parcel_id) or row.get("geometry")
        center = seed.centroid_of(geometry) if geometry else None
        if not geometry or not seed.plausible_centroid(center):
            dropped += 1
            continue
        price = seed.num(row.get("sale"))
        if price is not None and price <= 0:
            price = None
        feature = seed.empty_feature(
            fips="12015",
            county="Charlotte",
            state="Florida",
            markets=markets,
            parcel_id=parcel_id,
            acreage=row["acres"],
            geometry=geometry,
            center=center,
            source=spec["source"],
            owner=meaningful(attrs.get("ownersname")),
            situs=meaningful(attrs.get("propertyaddress")),
            dor=meaningful(attrs.get("usecode")),
            zoning=meaningful(attrs.get("zoningcode")),
            sale_price=price,
            sale_date=sale_iso(attrs.get("lastsaleno70cent")) or row.get("sold"),
            market_value=seed.num(str(attrs.get("totvalue") or "").replace(",", "").replace("$", "")),
            assessed=seed.num(str(attrs.get("assessedvalue") or "").replace(",", "").replace("$", "")),
            mail1=meaningful(attrs.get("mailingaddress")),
            mail2=meaningful(attrs.get("mailingaddress2")),
            mail_city=meaningful(attrs.get("city")),
            mail_state=meaningful(attrs.get("state")),
            mail_zip=seed.zip_str(attrs.get("zipcode")),
        )
        features.append(feature)
    join_fdor(features, spec)
    for feature in features:
        attach_links(feature)
    scrub(features)
    return features, count or len(acres_by_id), dropped


def carry_forward(features: list[dict], previous: dict[str, dict]) -> int:
    copied = 0
    keys = (
        "zoningCode",
        "zoningDistrict",
        "zoningDescription",
        "flu",
        "jurisdictionCode",
        "jurisdictionPrefix",
        "municipal",
        "municipality",
    )
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


def write_tiles_at(fips: str, features: list[dict], folder: Path, lookup_path: Path) -> int:
    if folder.exists():
        for child in folder.glob("*.geojson"):
            child.unlink()
    folder.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[int, int], list[dict]] = {}
    lookup: dict[str, str] = {}
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        key = seed.tile_key(lon, lat)
        grouped.setdefault(key, []).append(feature)
        lookup[feature["properties"]["parcelId"]] = f"{key[0]}_{key[1]}"
    for (ix, iy), group in grouped.items():
        path = folder / f"{ix}_{iy}.geojson"
        path.write_text(json.dumps({"type": "FeatureCollection", "name": f"{fips}-{ix}_{iy}", "features": group}, separators=(",", ":")))
    lookup_path.parent.mkdir(parents=True, exist_ok=True)
    lookup_path.write_text(json.dumps(lookup, separators=(",", ":")))
    return len(grouped)


def update_orlando(fips: str, row: dict) -> None:
    if fips not in ORLANDO_FIPS:
        return
    meta_path = ROOT / "data" / "fixtures" / "orlando-parcels" / "meta.json"
    meta = json.loads(meta_path.read_text())
    zoning = flu = 0
    folder = ROOT / row["path"]
    for path in folder.glob("*.geojson"):
        data = json.loads(path.read_text())
        for feature in data.get("features") or []:
            props = feature.get("properties") or {}
            if props.get("zoningCode"):
                zoning += 1
            flu_value = props.get("flu")
            if isinstance(flu_value, dict) and flu_value.get("code"):
                flu += 1
    for county in meta.get("counties") or []:
        if county.get("fips") != fips:
            continue
        county["featureCount"] = row["featureCount"]
        county["queryUrl"] = row["queryUrl"]
        county["source"] = "osceola-parcels" if fips == "12097" else row["source"]
        county["zoningJoinedCount"] = zoning
        county["fluJoinedCount"] = flu
        county["sourceCount"] = row.get("sourceCount")
        county["tileCount"] = row.get("tileCount")
        county["minAcres"] = 5.0
        county["maxAcres"] = 150.0
        county["coverage"] = "complete-gte-5ac"
        county["partition"] = "tiles"
        gaps = list(county.get("gaps") or [])
        for note in row.get("gaps") or []:
            if note not in gaps:
                gaps.append(note)
        county["gaps"] = gaps
    meta["parcelCount"] = sum(int(county.get("featureCount") or 0) for county in meta.get("counties") or [])
    meta["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")


def write_county(county: dict, markets: list[str], spec: dict, features: list[dict], source_count: int, dropped: int) -> None:
    previous = existing_props(county["fips"])
    copied = carry_forward(features, previous)
    by_id: dict[str, dict] = {}
    for feature in features:
        parcel_id = feature["properties"]["parcelId"]
        previous_feature = by_id.get(parcel_id)
        if previous_feature is None or (feature["properties"]["acreage"] or 0) > (previous_feature["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    if not features:
        raise RuntimeError(f"{county['fips']} kept no parcels")
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{county['fips']} emitted a parcel outside 5–150 acres")
    floor = 0.5 if spec.get("dedupe") or spec.get("merge") or spec.get("kind") == "franklin" else 0.75
    if source_count and len(features) < source_count * floor and spec.get("kind") != "franklin":
        raise RuntimeError(f"{county['fips']} kept {len(features)} of {source_count}")
    fips = county["fips"]
    if fips in ORLANDO_FIPS:
        folder = ROOT / "data" / "fixtures" / "orlando-parcels" / "tiles" / fips
        lookup = ROOT / "data" / "fixtures" / "orlando-parcels" / "lookup" / f"{fips}.json"
        tiles = write_tiles_at(fips, features, folder, lookup)
        path = str(folder.relative_to(ROOT))
        lookup_rel = str(lookup.relative_to(ROOT))
    else:
        path, lookup_rel, tiles = seed.write_tiles(county, features)
    gaps = list(GAP_NOTES.get(fips) or [])
    if copied:
        gaps.append(f"Zoning or future land use carried forward for {copied} parcel ids that still match.")
    if source_count and len(features) < source_count:
        gaps.insert(0, f"{source_count} rows matched the acreage filter; {len(features)} kept after the parcel-id and geometry checks.")
    link = LINKS[fips]
    print(f"  kept {len(features)} tiles {tiles}", flush=True)
    row = seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup_rel,
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
    update_orlando(fips, row)


def download_one(catalog: dict, fips: str, refresh: bool) -> None:
    spec = SPECS[fips]
    county = county_dict(catalog, fips, spec["name"])
    markets = markets_for(catalog, fips)
    if not markets:
        raise RuntimeError(f"{fips} is not on a market shelf")
    cache_path = CACHE_DIR / f"{fips}.json"
    print(f"Pulling {spec['name']} {fips} -> {', '.join(markets)}", flush=True)
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features:
            for feature in features:
                feature["properties"]["marketIds"] = feature_markets(spec, markets)
            print(f"  cache hit {len(features)}", flush=True)
            write_county(county, markets, spec, features, cached.get("sourceCount") or len(features), cached.get("dropped") or 0)
            return
    kind = spec.get("kind")
    if kind == "charlotte":
        features, source_count, dropped = pull_charlotte(spec, county, markets)
    elif kind == "franklin":
        features, source_count, dropped = pull_franklin(spec, county, markets)
    else:
        features, source_count, dropped = pull_arcgis(spec, county, markets)
    write_county(county, markets, spec, features, source_count, dropped)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"sourceCount": source_count, "dropped": dropped, "features": features}))


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
        line = f"| {market['id']} | {summary['tier']} | {parcels:,} | {complete} | {sample} | {gaps} |"
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


def restore_volusia_notes() -> None:
    path = seed.COUNTY_DIR / "12127" / "county.json"
    if not path.exists():
        return
    row = json.loads(path.read_text())
    gaps = list(row.get("gaps") or [])
    for note in GAP_NOTES["12127"]:
        if note not in gaps:
            gaps.append(note)
    row["gaps"] = gaps
    link = LINKS["12127"]
    row["paLinkVerified"] = bool(link.get("paVerified"))
    row["appraiserSearchUrl"] = link.get("appraiser")
    row["gisViewerUrl"] = link.get("gis")
    row["queryUrl"] = SPECS["12127"]["url"]
    row["source"] = SPECS["12127"]["source"]
    path.write_text(json.dumps(row, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--manifests-only", action="store_true")
    args = parser.parse_args()
    catalog = ensure_catalog(json.loads(CATALOG_PATH.read_text()))
    selected = {item.lower() for item in args.county}
    pull = []
    for fips, spec in SPECS.items():
        if selected and fips not in selected and spec["name"].lower() not in selected:
            continue
        pull.append(fips)
    if not args.manifests_only:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        errors: list[str] = []

        def run_group(group: list[str], workers: int) -> None:
            if not group:
                return
            if workers < 2 or len(group) < 2:
                for fips in group:
                    try:
                        download_one(catalog, fips, args.refresh)
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"{fips}: {exc}")
                        print(f"FAILED {fips}: {exc}", flush=True)
                return
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(download_one, catalog, fips, args.refresh): fips for fips in group}
                for future in as_completed(futures):
                    fips = futures[future]
                    try:
                        future.result()
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"{fips}: {exc}")
                        print(f"FAILED {fips}: {exc}", flush=True)

        # Osceola swaps the shared fetch for an unverified TLS retry. Keep it off the pool.
        run_group([fips for fips in pull if SPECS[fips].get("insecure")], 1)
        run_group([fips for fips in pull if not SPECS[fips].get("insecure")], 2 if len(pull) > 1 else 1)
        if errors:
            raise SystemExit("County downloads failed:\n" + "\n".join(errors))
        if "12127" in pull:
            import join_volusia_flagler_municipal

            join_volusia_flagler_municipal.main()
            restore_volusia_notes()
    refresh_manifests(catalog, set(SPECS))
    print("Done", flush=True)


if __name__ == "__main__":
    sys.exit(main())
