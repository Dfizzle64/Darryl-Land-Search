#!/usr/bin/env python3
"""FL-rest batch 1 parcel extract.

Twenty Florida counties that had no 5–150 acre parcels on main, or only a
sample or gap row. Acreage is 5.0–150.0 inclusive. Public GIS only.
Read-only GET queries. Owner phone and email are never requested.

FDOR Florida_Statewide_Cadastral 2025 is an attribute join on PARCEL_ID.
A county-number-only filter is not used. Madison, Taylor, and Dixie have no
queryable zoning or future land use. Their future-land-use fallback is the
2008 statewide broad category layer, labeled as such, and those counties
stay partial.
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any

from parcel_geometry import contains_point, esri_rings_to_geojson

MIN_ACRES = 5.0
MAX_ACRES = 150.0
MIN_SQFT = 217800.0
MAX_SQFT = 6534000.0
SQFT_PER_ACRE = 43560.0

FDOR_URL = (
    "https://services9.arcgis.com/Gh9awoU677aKree0/ArcGIS/rest/services/"
    "Florida_Statewide_Cadastral/FeatureServer/0/query"
)
FDOR_FIELDS = [
    "PARCEL_ID",
    "OWN_NAME",
    "OWN_ADDR1",
    "OWN_CITY",
    "OWN_STATE",
    "OWN_ZIPCD",
    "PHY_ADDR1",
    "PHY_CITY",
    "PHY_ZIPCD",
    "LND_SQFOOT",
    "JV",
    "AV_SD",
    "TV_SD",
    "DOR_UC",
    "SALE_PRC1",
    "SALE_YR1",
    "QUAL_CD1",
]
GEOPLAN_URL = "https://services.arcgis.com/LBbVDC0hKPAnLRpO/arcgis/rest/services/FLU_L2_2020/FeatureServer/0/query"
GEOPLAN_LABEL = "2008 statewide broad land-use categories, not current zoning"
OWNER_CONFLICT = (
    "Property appraiser warns owner names may be swapped after a data migration. "
    "This row uses the FDOR owner because it differs from the county roll name."
)
FORBIDDEN_FIELDS = ("OwnerPhone", "OwnerEmail")

# Hosts the research cards call out for a certificate fallback. None of these 20 do.
TLS_FALLBACK_HOSTS: set[str] = set()
TLS_FALLBACK_USED: set[str] = set()

FIPS = (
    "12013",
    "12023",
    "12029",
    "12035",
    "12037",
    "12039",
    "12045",
    "12047",
    "12059",
    "12063",
    "12065",
    "12067",
    "12077",
    "12079",
    "12083",
    "12121",
    "12123",
    "12125",
    "12129",
    "12133",
)

PARTIAL_FIPS = (
    "12029",
    "12037",
    "12045",
    "12047",
    "12059",
    "12067",
    "12079",
    "12121",
    "12123",
    "12125",
)
GEOPLAN_FIPS = ("12029", "12079", "12123")
SEARCH_ONLY_FIPS = ("12039", "12079", "12083")

# west, south, east, north. Generous enough for shoreline parcels, tight enough
# to reject namesake counties in other states.
COUNTY_BBOX = {
    "12013": (-85.45, 30.10, -84.80, 30.70),
    "12023": (-82.95, 29.80, -82.25, 30.65),
    "12029": (-83.55, 29.30, -82.85, 29.95),
    "12035": (-81.60, 29.25, -80.95, 29.80),
    "12037": (-85.30, 29.50, -84.20, 30.10),
    "12039": (-85.05, 30.35, -84.20, 30.80),
    "12045": (-85.50, 29.50, -84.85, 30.30),
    "12047": (-83.35, 30.20, -82.50, 30.75),
    "12059": (-86.15, 30.65, -85.45, 31.10),
    "12063": (-85.55, 30.50, -84.65, 31.10),
    "12065": (-84.20, 30.15, -83.60, 30.70),
    "12067": (-83.45, 29.80, -82.95, 30.30),
    "12077": (-85.20, 29.90, -84.40, 30.60),
    "12079": (-83.90, 30.15, -83.15, 30.70),
    "12083": (-82.75, 28.90, -81.70, 29.60),
    "12121": (-83.30, 29.90, -82.60, 30.55),
    "12123": (-84.05, 29.65, -83.20, 30.35),
    "12125": (-82.60, 29.85, -82.15, 30.25),
    "12129": (-84.75, 29.90, -83.95, 30.35),
    "12133": (-85.90, 30.35, -85.30, 30.90),
}

MIL1 = "https://gis.arpc.org/server/rest/services/Florida_Statewide_Cadastral_MIL1/MapServer/0/query"
MIL1_FIELDS = [
    "PARCELID",
    "ACRES",
    "ONAME",
    "OADDR1",
    "OCITY",
    "OSTATE",
    "OZIPCD",
    "PHYADDR1",
    "PHYCITY",
    "PHYZIP",
    "SALEPRC1",
    "SALEYR1",
    "JV",
    "AV_SD",
    "TV_SD",
    "DORUC",
]
SRWMD = "http://gis.srwmd.state.fl.us/arcgis/rest/services/SRWMDGIS/SRWMD_Parcels/FeatureServer/{layer}/query"
SRWMD_FIELDS = [
    "PIN",
    "PARNO",
    "AREANO",
    "OWNNAME",
    "MAILADD",
    "SITEADD",
    "SCITY",
    "SALE1_AMT",
    "SALE1_YEAR",
    "PARVAL",
    "ASSD_TOT",
    "PARUSECODE",
]

JEFFERSON_ZONING_FIELDS = ["parcelid", "Zoning"]
FRANKLIN_ZONING_FIELDS = ["parcelid", "zonecode", "zonecat"]

MARKETS = {
    "12013": "Panhandle Florida",
    "12023": "North Florida",
    "12029": "Big Bend",
    "12035": "North Florida",
    "12037": "Panhandle Florida",
    "12039": "Big Bend",
    "12045": "Panhandle Florida",
    "12047": "North Florida",
    "12059": "Panhandle Florida",
    "12063": "Panhandle Florida",
    "12065": "Big Bend",
    "12067": "North Florida",
    "12077": "Panhandle Florida",
    "12079": "Big Bend",
    "12083": "North-Central Florida",
    "12121": "North Florida",
    "12123": "Big Bend",
    "12125": "North Florida",
    "12129": "Big Bend",
    "12133": "Panhandle Florida",
}

NEW_SHELVES = ("North Florida", "Panhandle Florida")


SPECS: dict[str, dict] = {}


def _mil1(name: str, fips: str, source: str, where_name: str) -> dict:
    return {
        "url": MIL1,
        "where": f"CNTYNAME='{where_name}' AND ACRES>=5 AND ACRES<=150",
        "fields": list(MIL1_FIELDS),
        "id": "PARCELID",
        "acres": "ACRES",
        "owner": "ONAME",
        "situs": "PHYADDR1",
        "city": "PHYCITY",
        "zip": "PHYZIP",
        "mail": "OADDR1",
        "mailCity": "OCITY",
        "mailState": "OSTATE",
        "mailZip": "OZIPCD",
        "dor": "DORUC",
        "marketValue": "JV",
        "assessed": "AV_SD",
        "taxable": "TV_SD",
        "salePrice": "SALEPRC1",
        "saleYear": "SALEYR1",
        "source": source,
    }


def _srwmd(layer: int, source: str) -> dict:
    return {
        "url": SRWMD.format(layer=layer),
        "where": "AREANO>=5 AND AREANO<=150",
        "fields": list(SRWMD_FIELDS),
        "id": "PIN",
        "acres": "AREANO",
        "owner": "OWNNAME",
        "situs": "SITEADD",
        "city": "SCITY",
        "mail": "MAILADD",
        "dor": "PARUSECODE",
        "marketValue": "PARVAL",
        "assessed": "ASSD_TOT",
        "salePrice": "SALE1_AMT",
        "saleYear": "SALE1_YEAR",
        "source": source,
    }


def _init_specs() -> None:
    def base(name: str, status: str, parcels: dict, **extra: Any) -> dict:
        fips_gaps = extra.pop("gaps")
        row = {
            "name": name,
            "status": status,
            "coverage": "partial" if status == "partial" else "complete-gte-5ac",
            "parcels": parcels,
            "source": parcels["source"],
            "url": parcels["url"],
            "fdor": extra.pop("fdor", "fill"),
            "fdorKey": extra.pop("fdorKey", "exact"),
            "appraiser": extra.pop("appraiser"),
            "deepLink": extra.pop("deepLink", True),
            "gis": extra.pop("gis"),
            "gisAlt": extra.pop("gisAlt", None),
            "parcelIdLabel": extra.pop("parcelIdLabel", "Parcel ID"),
            "overlays": extra.pop("overlays", []),
            "gaps": fips_gaps,
            "featureGaps": extra.pop("featureGaps", []),
        }
        row.update(extra)
        return row

    geo = lambda county: {  # noqa: E731
        "role": "flu",
        "kind": "polygons",
        "url": GEOPLAN_URL,
        "where": f"COUNTY='{county}'",
        "fields": ["FLU_L2_DESC", "JURISDICT", "COUNTY"],
        "codeField": "FLU_L2_DESC",
        "labelMode": "geoplan",
        "jurisdictionField": "JURISDICT",
        "source": GEOPLAN_LABEL,
    }

    SPECS.update(
        {
            "12013": base(
                "Calhoun",
                "live",
                _mil1("Calhoun", "12013", "fl-calhoun-mil1-12013", "CALHOUN"),
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?AppID=829&LayerID=15004&PageTypeID=4&PageID=6748&KeyValue={id}",
                gis="https://qpublic.schneidercorp.com/Application.aspx?AppID=829&LayerID=15004&PageTypeID=2&PageID=6748",
                overlays=[
                    {
                        "role": "flu",
                        "kind": "categories",
                        "source": "calhoun-flum2",
                        "jurisdiction": "Calhoun",
                        "layers": [
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Calhoun_FLUM2/FeatureServer/2/query", "Public/Institutional"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Calhoun_FLUM2/FeatureServer/3/query", "Recreation/Open Space"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Calhoun_FLUM2/FeatureServer/4/query", "Residential"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Calhoun_FLUM2/FeatureServer/5/query", "Mixed Use Residential"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Calhoun_FLUM2/FeatureServer/6/query", "Urban Fringe"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Calhoun_FLUM2/FeatureServer/7/query", "Industrial"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Calhoun_FLUM2/FeatureServer/8/query", "Light Industrial"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Calhoun_FLUM2/FeatureServer/10/query", "Agriculture"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Blountstown_FLUM/FeatureServer/0/query", "Residential", "Blountstown"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Blountstown_FLUM/FeatureServer/1/query", "Institutional", "Blountstown"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Blountstown_FLUM/FeatureServer/2/query", "Industrial", "Blountstown"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Blountstown_FLUM/FeatureServer/3/query", "Commercial", "Blountstown"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Blountstown_FLUM/FeatureServer/4/query", "Agriculture", "Blountstown"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Altha_FLUM/FeatureServer/0/query", "Residential", "Altha"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Altha_FLUM/FeatureServer/1/query", "Recreation", "Altha"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Altha_FLUM/FeatureServer/2/query", "Public Use", "Altha"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Altha_FLUM/FeatureServer/4/query", "Commercial", "Altha"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Altha_FLUM/FeatureServer/5/query", "Agriculture", "Altha"),
                        ],
                    }
                ],
                gaps=[
                    "Calhoun parcels are ARPC Florida_Statewide_Cadastral_MIL1 filtered to CNTYNAME='CALHOUN'. Acreage is ACRES, 5.0–150.0 inclusive. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PARCEL_ID.",
                    "County zoning is not a FeatureServer. Future land use is Calhoun_FLUM2 category layers plus Blountstown and Altha city layers. Alabama Calhoun GIS was not used.",
                ],
                featureGaps=["No county zoning layer. Future land use is the FLUM category, not a zoning district."],
            ),
            "12023": base(
                "Columbia",
                "live",
                {
                    "url": "https://gis.columbiacountyfla.com/hosting/rest/services/Parcels_and_Addresses/MapServer/2/query",
                    "where": "Acres>=5 AND Acres<=150",
                    "fields": ["ParcelNo", "Acres", "Owner", "Url"],
                    "id": "ParcelNo",
                    "acres": "Acres",
                    "owner": "Owner",
                    "source": "fl-columbia-parcels-12023",
                },
                appraiser="https://www.columbiacountyfla.com/ParcelDetails.aspx?ParcelNo={id}",
                gis="https://columbia.floridapa.com/gis/",
                gisAlt="https://search.ccpafl.com/map/",
                parcelIdLabel="Parcel Number",
                overlays=[
                    {
                        "role": "zoning",
                        "kind": "polygons",
                        "url": "https://gis.columbiacountyfla.com/hosting/rest/services/Zoning_Atlas/FeatureServer/1/query",
                        "where": "1=1",
                        "fields": ["FinalZng"],
                        "codeField": "FinalZng",
                        "jurisdiction": "Columbia",
                        "source": "columbia-zoning-atlas",
                    },
                    {
                        "role": "flu",
                        "kind": "polygons",
                        "url": "https://gis.columbiacountyfla.com/hosting/rest/services/Future_Land_Use/FeatureServer/1/query",
                        "where": "1=1",
                        "fields": ["COFU_ID"],
                        "codeField": "COFU_ID",
                        "jurisdiction": "Columbia",
                        "source": "columbia-future-land-use",
                    },
                ],
                gaps=[
                    "Columbia parcels are Parcels_and_Addresses MapServer/2. Acreage is Acres, 5.0–150.0 inclusive. The layer has owner and acres. Just value and DOR use are not on the layer.",
                    "County ParcelNo and the FDOR PARCEL_ID are different formats. The FDOR join is by parcel id only. Rows that do not match stay without a FDOR value.",
                    "Zoning geometry queries are flaky on this host. The atlas is still the zoning source when the query returns.",
                ],
            ),
            "12029": base(
                "Dixie",
                "partial",
                _mil1("Dixie", "12029", "fl-dixie-mil1-12029", "DIXIE"),
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?AppID=867&LayerID=16385&PageTypeID=4&PageID=7230&KeyValue={id}",
                gis="https://qpublic.schneidercorp.com/Application.aspx?AppID=867&LayerID=16385&PageTypeID=2&PageID=7230",
                overlays=[geo("DIXIE")],
                gaps=[
                    "Partial. Dixie parcels are ARPC MIL1 filtered to CNTYNAME='DIXIE'. FDOR 2025 fills blank owner, value, DOR use, acreage, and roll-year sale by PARCEL_ID.",
                    "No queryable zoning or future land use. The land-development atlas is a PDF. Future land use on these rows is the UF GeoPlan 2008 statewide broad land-use categories, not current zoning.",
                    "The property-appraiser detail page uses the same PageID as the search page. Sale history beyond the FDOR roll year is not on this extract.",
                ],
                featureGaps=[GEOPLAN_LABEL],
            ),
            "12035": base(
                "Flagler",
                "live",
                {
                    "url": "https://services3.arcgis.com/hSKL9bYjhP4rHxSD/arcgis/rest/services/Flagler_County_Parcels/FeatureServer/0/query",
                    "where": "legal_acreage>=5 AND legal_acreage<=150",
                    "fields": [
                        "PARCELNO",
                        "legal_acreage",
                        "file_as_name",
                        "situs_num",
                        "situs_street",
                        "situs_city",
                        "SaleAdj1",
                        "saleDt1",
                        "JustVal",
                        "Assessed_val",
                    ],
                    "id": "PARCELNO",
                    "acres": "legal_acreage",
                    "owner": "file_as_name",
                    "situsParts": ["situs_num", "situs_street"],
                    "city": "situs_city",
                    "marketValue": "JustVal",
                    "assessed": "Assessed_val",
                    "salePrice": "SaleAdj1",
                    "saleEpoch": "saleDt1",
                    "source": "fl-flagler-parcels-12035",
                },
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?AppID=598&LayerID=9801&PageTypeID=4&PageID=4330&KeyValue={id}",
                gis="https://qpublic.schneidercorp.com/Application.aspx?AppID=598&LayerID=9801&PageTypeID=2&PageID=4328",
                parcelIdLabel="Parcel Number",
                overlays=[
                    {
                        "role": "zoning",
                        "kind": "polygons",
                        "url": "https://gis.palmcoast.gov/hosting/rest/services/External/AGISO_FlaglerZoning/MapServer/0/query",
                        "where": "1=1",
                        "fields": ["ZONECODE", "ZONENAME", "CITYNAME"],
                        "codeField": "ZONECODE",
                        "labelField": "ZONENAME",
                        "jurisdictionField": "CITYNAME",
                        "source": "flagler-zoning",
                    },
                    {
                        "role": "flu",
                        "kind": "polygons",
                        "url": "https://gis.palmcoast.gov/hosting/rest/services/External/AGISO_FlaglerFLU/MapServer/0/query",
                        "where": "1=1",
                        "fields": ["Label", "LandUse", "CityName"],
                        "codeField": "LandUse",
                        "labelField": "Label",
                        "jurisdictionField": "CityName",
                        "source": "flagler-flu",
                    },
                ],
                gaps=[
                    "Flagler parcels are Flagler_County_Parcels. Acreage is legal_acreage, 5.0–150.0 inclusive. FDOR 2025 fills blank DOR use and roll-year sale by PARCEL_ID.",
                    "Zoning and future land use are the unincorporated Palm Coast GIS layers. Beverly Beach future land use is a gap on the municipal card and is not invented here.",
                ],
            ),
            "12037": base(
                "Franklin",
                "partial",
                _mil1("Franklin", "12037", "fl-franklin-mil1-12037", "FRANKLIN"),
                appraiser="https://franklin-search.gsacorp.io/parcel/{id}",
                gis="https://franklin-search.gsacorp.io/map",
                overlays=[
                    {
                        "role": "zoning",
                        "kind": "attributes",
                        "url": "https://gis.arpc.org/server/rest/services/Hosted/Franklin_Zones_2292024/FeatureServer/0/query",
                        "where": "1=1",
                        "fields": list(FRANKLIN_ZONING_FIELDS),
                        "idField": "parcelid",
                        "codeField": "zonecode",
                        "labelField": "zonecat",
                        "jurisdiction": "Franklin",
                        "source": "franklin-zones",
                    },
                    {
                        "role": "both",
                        "kind": "polygons",
                        "url": "https://gis.arpc.org/server/rest/services/Hosted/Carrabelle_FLUM_and_Zoning_Districts/FeatureServer/0/query",
                        "where": "1=1",
                        "fields": ["zone_code", "zonecategory", "flumcode", "flumcategory"],
                        "codeField": "zone_code",
                        "labelField": "zonecategory",
                        "fluCodeField": "flumcode",
                        "fluLabelField": "flumcategory",
                        "jurisdiction": "Carrabelle",
                        "source": "carrabelle-flum-zoning",
                        "overrideZoning": True,
                    },
                ],
                gaps=[
                    "Partial. Franklin parcels are ARPC MIL1 filtered to CNTYNAME='FRANKLIN'. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PARCEL_ID.",
                    "County zoning is Franklin_Zones_2292024 joined on parcel id. Unincorporated future land use is not a queryable layer. Carrabelle city zoning and future land use are joined inside that city layer.",
                ],
                featureGaps=["Unincorporated Franklin future land use is not a queryable layer. Carrabelle is the city layer."],
            ),
            "12039": base(
                "Gadsden",
                "live",
                _mil1("Gadsden", "12039", "fl-gadsden-mil1-12039", "GADSDEN"),
                fdor="prefer-owner",
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?App=GadsdenCountyFL&PageType=Search",
                deepLink=False,
                gis="https://qpublic.schneidercorp.com/Application.aspx?App=GadsdenCountyFL&PageType=Search",
                overlays=[
                    {
                        "role": "both",
                        "kind": "polygons",
                        "url": "https://gis.arpc.org/server/rest/services/Hosted/Gadsden_GIS_Feature_Layers/FeatureServer/9/query",
                        "where": "1=1",
                        "fields": ["zone", "zone_full", "city"],
                        "codeField": "zone",
                        "labelField": "zone_full",
                        "jurisdiction": "Gadsden",
                        "source": "gadsden-flum-as-zoning",
                    },
                    {
                        "role": "zoning",
                        "kind": "polygons",
                        "url": "https://gis.arpc.org/server/rest/services/Hosted/Quincy_Layers/FeatureServer/13/query",
                        "where": "1=1",
                        "fields": ["zoningcode", "category"],
                        "codeField": "zoningcode",
                        "labelField": "category",
                        "jurisdiction": "Quincy",
                        "source": "quincy-zoning",
                        "overrideZoning": True,
                    },
                    {
                        "role": "zoning",
                        "kind": "polygons",
                        "url": "https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Havana_Zoning_Districts_WFL1/FeatureServer/6/query",
                        "where": "1=1",
                        "fields": ["Category"],
                        "codeField": "Category",
                        "jurisdiction": "Havana",
                        "source": "havana-zoning",
                        "overrideZoning": True,
                    },
                ],
                gaps=[
                    "Gadsden parcels are ARPC MIL1 filtered to CNTYNAME='GADSDEN'. Acreage is ACRES, 5.0–150.0 inclusive. FDOR 2025 is preferred for the owner name. County-roll names that differ are flagged. Just value, DOR use, and roll-year sale fill from FDOR when the county layer is blank.",
                    "Unincorporated zoning is the December 2020 future-land-use category. County code treats that category as the land-use district. Quincy and Havana zoning polygons override it inside those cities. Chattahoochee, Greensboro, Gretna, and Midway zoning were not found.",
                    "The property appraiser link is a search page. The parcel id is not in the URL. City of Gadsden, Alabama was not used.",
                ],
                featureGaps=[
                    "Property appraiser link is a search page. The parcel id is not in the URL.",
                    "Unincorporated zoning is the future land use category from county code, not a separate zoning atlas.",
                ],
            ),
            "12045": base(
                "Gulf",
                "partial",
                _mil1("Gulf", "12045", "fl-gulf-mil1-12045", "GULF"),
                appraiser="https://beacon.schneidercorp.com/Application.aspx?AppID=819&LayerID=15077&PageTypeID=4&PageID=6812&KeyValue={id}",
                gis="https://beacon.schneidercorp.com/Application.aspx?AppID=819&LayerID=15077&PageTypeID=2&PageID=6812",
                gaps=[
                    "Partial. Gulf parcels are ARPC MIL1 filtered to CNTYNAME='GULF'. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PARCEL_ID.",
                    "No queryable county zoning or future land use. Port St. Joe and Wewahitchka ARPC layers are vulnerability layers, not zoning, and were not used.",
                ],
                featureGaps=["No queryable Gulf County zoning or future land use layer."],
            ),
            "12047": base(
                "Hamilton",
                "partial",
                _mil1("Hamilton", "12047", "fl-hamilton-mil1-12047", "HAMILTON"),
                appraiser="https://beacon.schneidercorp.com/Application.aspx?AppID=817&LayerID=14544&PageTypeID=4&PageID=6409&KeyValue={id}",
                gis="https://beacon.schneidercorp.com/Application.aspx?AppID=817&LayerID=14544&PageTypeID=2&PageID=6409",
                gaps=[
                    "Partial. Hamilton parcels are ARPC MIL1 filtered to CNTYNAME='HAMILTON'. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PARCEL_ID.",
                    "No county enterprise zoning or future-land-use service. Hamilton County, Ohio and other namesakes were not used.",
                ],
                featureGaps=["No queryable Hamilton County zoning or future land use layer."],
            ),
            "12059": base(
                "Holmes",
                "partial",
                _mil1("Holmes", "12059", "fl-holmes-mil1-12059", "HOLMES"),
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?AppID=821&LayerID=14700&PageTypeID=4&PageID=6565&KeyValue={id}",
                gis="https://qpublic.schneidercorp.com/Application.aspx?AppID=821&LayerID=14700&PageTypeID=2&PageID=6565",
                gaps=[
                    "Partial. Holmes parcels are ARPC MIL1 filtered to CNTYNAME='HOLMES'. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PARCEL_ID.",
                    "The county regulates by future land use, and that map is a PDF. There is no zoning district layer and no future-land-use FeatureServer.",
                ],
                featureGaps=["Holmes future land use is a PDF. No zoning district layer was published."],
            ),
            "12063": base(
                "Jackson",
                "live",
                _mil1("Jackson", "12063", "fl-jackson-mil1-12063", "JACKSON"),
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?AppID=851&LayerID=15884&PageTypeID=4&PageID=7081&KeyValue={id}",
                gis="https://qpublic.schneidercorp.com/Application.aspx?AppID=851&LayerID=15884&PageTypeID=2&PageID=7081",
                overlays=[
                    {
                        "role": "flu",
                        "kind": "polygons",
                        "url": "https://gis.arpc.org/server/rest/services/Counties/Jackson_FLUM/MapServer/0/query",
                        "where": "1=1",
                        "fields": ["LU_Code", "LAND_USE"],
                        "codeField": "LU_Code",
                        "labelField": "LAND_USE",
                        "jurisdiction": "Jackson",
                        "source": "jackson-flum",
                    }
                ],
                gaps=[
                    "Jackson parcels are ARPC MIL1 filtered to CNTYNAME='JACKSON'. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PARCEL_ID.",
                    "Future land use is Counties/Jackson_FLUM. There is no countywide zoning FeatureServer. Jackson County in other states was not used.",
                ],
                featureGaps=["No countywide Jackson zoning layer. Future land use is the county FLUM."],
            ),
            "12065": base(
                "Jefferson",
                "live",
                {
                    "url": "https://services5.arcgis.com/vFMp1Ly1q6rKKp0o/arcgis/rest/services/JC__PARCELS_view/FeatureServer/0/query",
                    "where": "COGO_ACRES>=5 AND COGO_ACRES<=150",
                    "fields": ["PARCELID", "COGO_ACRES", "Prop_ID"],
                    "id": "PARCELID",
                    "acres": "COGO_ACRES",
                    "source": "fl-jefferson-parcels-12065",
                },
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?AppID=866&LayerID=16381&PageTypeID=4&PageID=7228&KeyValue={id}",
                gis="https://qpublic.schneidercorp.com/Application.aspx?AppID=866&LayerID=16381&PageTypeID=2&PageID=7228",
                overlays=[
                    {
                        "role": "zoning",
                        "kind": "attributes",
                        "url": "https://services5.arcgis.com/vFMp1Ly1q6rKKp0o/arcgis/rest/services/JefCo_Parcels_20260122_162231/FeatureServer/0/query",
                        "where": "1=1",
                        "fields": list(JEFFERSON_ZONING_FIELDS),
                        "idField": "parcelid",
                        "codeField": "Zoning",
                        "jurisdiction": "Jefferson",
                        "source": "jefferson-land-use-district",
                        "dedupe": True,
                        "byParcelIds": True,
                    },
                    {
                        "role": "zoning",
                        "kind": "polygons",
                        "url": "https://services5.arcgis.com/vFMp1Ly1q6rKKp0o/arcgis/rest/services/JC_CITY_ZONING_view/FeatureServer/0/query",
                        "where": "1=1",
                        "fields": ["ZONES", "ZONENAME"],
                        "codeField": "ZONES",
                        "labelField": "ZONENAME",
                        "jurisdiction": "Monticello",
                        "source": "monticello-zoning",
                        "overrideZoning": True,
                    },
                    {
                        "role": "flu",
                        "kind": "polygons",
                        "url": "https://services5.arcgis.com/vFMp1Ly1q6rKKp0o/arcgis/rest/services/JC_CITY_FLUM_view/FeatureServer/0/query",
                        "where": "1=1",
                        "fields": ["CODE", "CODENAME"],
                        "codeField": "CODE",
                        "labelField": "CODENAME",
                        "jurisdiction": "Monticello",
                        "source": "monticello-flum",
                    },
                    {
                        "role": "flu",
                        "kind": "polygons",
                        "url": "https://gis.arpc.org/server/rest/services/MapImages/Future_Land_Use_Maps/MapServer/8/query",
                        "where": "1=1",
                        "fields": ["PARCELID", "FLUM_NAME"],
                        "codeField": "FLUM_NAME",
                        "jurisdiction": "Jefferson",
                        "source": "jefferson-flum-legacy",
                        "optional": True,
                    },
                ],
                gaps=[
                    "Jefferson parcels are JC__PARCELS_view. Acreage is COGO_ACRES, 5.0–150.0 inclusive. The parcel layer has no owner. FDOR 2025 fills owner, value, DOR use, and roll-year sale by PARCEL_ID.",
                    "Unincorporated zoning is the land-use district attribute. That layer repeats each parcel about 14 times, so it is deduped on parcel id. OwnerPhone and OwnerEmail are not requested.",
                    "Monticello zoning and future land use override inside the city polygons. The county FLUM is a legacy shapefile and may be missing. Jefferson County, Alabama was not used.",
                ],
                featureGaps=["Sale history beyond the FDOR roll year is not on this extract."],
            ),
            "12067": base(
                "Lafayette",
                "partial",
                _srwmd(8, "fl-lafayette-srwmd-12067"),
                appraiser="https://beacon.schneidercorp.com/Application.aspx?AppID=1396&LayerID=47258&PageTypeID=4&PageID=19927&KeyValue={id}",
                gis="https://beacon.schneidercorp.com/Application.aspx?AppID=1396&LayerID=47258&PageTypeID=2&PageID=19927",
                gaps=[
                    "Partial. Lafayette parcels are SRWMD_Parcels layer 8. Acreage is AREANO, 5.0–150.0 inclusive. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PIN.",
                    "No queryable zoning or future land use. Lafayette County in other states was not used.",
                ],
                featureGaps=["No queryable Lafayette County zoning or future land use layer."],
            ),
            "12077": base(
                "Liberty",
                "live",
                _mil1("Liberty", "12077", "fl-liberty-mil1-12077", "LIBERTY"),
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?AppID=828&LayerID=15003&PageTypeID=4&PageID=13691&KeyValue={id}",
                gis="https://qpublic.schneidercorp.com/Application.aspx?AppID=828&LayerID=15003&PageTypeID=2&PageID=13691",
                overlays=[
                    {
                        "role": "flu",
                        "kind": "categories",
                        "source": "liberty-flum",
                        "jurisdiction": "Liberty",
                        "layers": [
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Liberty_FLUM/FeatureServer/0/query", "Rural Village"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Liberty_FLUM/FeatureServer/1/query", "Prison"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Liberty_FLUM/FeatureServer/2/query", "Conservation"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Liberty_FLUM/FeatureServer/3/query", "Suburban"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Liberty_FLUM/FeatureServer/4/query", "Rural Residential"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Liberty_FLUM/FeatureServer/5/query", "Industrial"),
                            ("https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Liberty_FLUM/FeatureServer/6/query", "Agriculture"),
                        ],
                    },
                    {
                        "role": "flu",
                        "kind": "polygons",
                        "url": "https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Bristol_FLUM/FeatureServer/0/query",
                        "where": "1=1",
                        "fields": ["Category"],
                        "codeField": "Category",
                        "jurisdiction": "Bristol",
                        "source": "bristol-flum",
                    },
                ],
                gaps=[
                    "Liberty parcels are ARPC MIL1 filtered to CNTYNAME='LIBERTY'. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PARCEL_ID.",
                    "Future land use is Liberty_FLUM category layers plus Bristol. There is no countywide zoning FeatureServer. Liberty County, Georgia was not used.",
                ],
                featureGaps=["No countywide Liberty zoning layer. Future land use is the FLUM category."],
            ),
            "12079": base(
                "Madison",
                "partial",
                {
                    "url": "https://services3.arcgis.com/DvTqoyLKkslnGFR5/arcgis/rest/services/Madison_County_Florida/FeatureServer/0/query",
                    "where": f"LND_SQFOOT>={int(MIN_SQFT)} AND LND_SQFOOT<={int(MAX_SQFT)}",
                    "fields": [
                        "PARCEL_ID",
                        "LND_SQFOOT",
                        "OWN_NAME",
                        "OWN_ADDR1",
                        "PHY_ADDR1",
                        "PHY_CITY",
                        "SALE_PRC1",
                        "SALE_YR1",
                        "JV",
                        "AV_SD",
                        "TV_SD",
                        "DOR_UC",
                    ],
                    "id": "PARCEL_ID",
                    "acresSqft": "LND_SQFOOT",
                    "owner": "OWN_NAME",
                    "situs": "PHY_ADDR1",
                    "city": "PHY_CITY",
                    "mail": "OWN_ADDR1",
                    "dor": "DOR_UC",
                    "marketValue": "JV",
                    "assessed": "AV_SD",
                    "taxable": "TV_SD",
                    "salePrice": "SALE_PRC1",
                    "saleYear": "SALE_YR1",
                    "source": "fl-madison-sdl-12079",
                },
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?App=MadisonCountyFL&Layer=Parcels&PageType=Search",
                deepLink=False,
                gis="https://planning.madisoncountyfla.com/gis/",
                overlays=[geo("MADISON")],
                gaps=[
                    "Partial. Madison polygons are the SpatialDataLogic 2024 county extract. Acreage is land square feet divided by 43560, 5.0–150.0 inclusive. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PARCEL_ID. CO_NO=50 is the FDOR county number.",
                    "County future land use is the zoning-equivalent district under the land-development code, but the county map is render-only. These rows use the UF GeoPlan 2008 statewide broad land-use categories, not current zoning.",
                    "The property appraiser link is a search page. The GSA detail host was not verified, so the parcel id is not put in the URL.",
                ],
                featureGaps=[
                    GEOPLAN_LABEL,
                    "Property appraiser link is a search page. The parcel id is not in the URL.",
                ],
            ),
            "12083": base(
                "Marion",
                "live",
                {
                    "url": "https://gis.marionfl.org/public/rest/services/General/ParcelsAndSubdivisions/MapServer/0/query",
                    "where": "ACRES>=5 AND ACRES<=150",
                    "fields": ["PARCEL", "ALT_Key", "ACRES", "NAME", "ADD_1", "ADD_2", "CITY", "ZIP", "SITUS_1", "SITUS_2", "PR_1", "MO1", "YR1", "Q1"],
                    "id": "PARCEL",
                    "acres": "ACRES",
                    "owner": "NAME",
                    "situs": "SITUS_1",
                    "mail": "ADD_1",
                    "mail2": "ADD_2",
                    "salePrice": "PR_1",
                    "saleMonth": "MO1",
                    "saleYear": "YR1",
                    "saleQualified": "Q1",
                    "source": "fl-marion-parcels-12083",
                },
                appraiser="https://www.pa.marion.fl.us/PropertySearch.aspx",
                deepLink=False,
                gis="https://gis.marionfl.org/",
                overlays=[
                    {
                        "role": "zoning",
                        "kind": "polygons",
                        "url": "https://gis.marionfl.org/public/rest/services/General/PlanningZoning/MapServer/20/query",
                        "where": "1=1",
                        "fields": ["ZONECLASS", "ZONEDESC"],
                        "codeField": "ZONECLASS",
                        "labelField": "ZONEDESC",
                        "jurisdiction": "Marion",
                        "source": "marion-zoning",
                    },
                    {
                        "role": "flu",
                        "kind": "attributes",
                        "url": "https://gis.marionfl.org/public/rest/services/General/PlanningZoning/MapServer/6/query",
                        "where": "1=1",
                        "fields": ["PARCELID", "GS_FLUM", "LANDUSECOD"],
                        "idField": "PARCELID",
                        "codeField": "LANDUSECOD",
                        "labelField": "GS_FLUM",
                        "jurisdiction": "Marion",
                        "source": "marion-flu",
                        "byParcelIds": True,
                    },
                ],
                gaps=[
                    "Marion parcels are ParcelsAndSubdivisions MapServer/0. Acreage is ACRES, 5.0–150.0 inclusive. FDOR 2025 fills blank just value and DOR use by PARCEL_ID.",
                    "Zoning is PlanningZoning MapServer/20. Future land use is joined on PARCELID from MapServer/6. The parcel ZONE1 attribute is not stored as zoning.",
                    "The property appraiser link is a search page. A stable parcel URL was not verified, so the parcel id is not put in the URL. Q1 is stored as the county qualified flag and was not remapped.",
                ],
                featureGaps=["Property appraiser link is a search page. The parcel id is not in the URL."],
            ),
            "12121": base(
                "Suwannee",
                "partial",
                _srwmd(11, "fl-suwannee-srwmd-12121"),
                appraiser="https://suwannee-search.gsacorp.io/parcel/{id}",
                gis="https://suwannee-search.gsacorp.io/map",
                gaps=[
                    "Partial. Suwannee parcels are SRWMD_Parcels layer 11. Acreage is AREANO, 5.0–150.0 inclusive. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PIN.",
                    "No queryable zoning or future land use.",
                ],
                featureGaps=["No queryable Suwannee County zoning or future land use layer."],
            ),
            "12123": base(
                "Taylor",
                "partial",
                _mil1("Taylor", "12123", "fl-taylor-mil1-12123", "TAYLOR"),
                appraiser="https://beacon.schneidercorp.com/Application.aspx?AppID=792&LayerID=11749&PageTypeID=4&PageID=5268&KeyValue={id}",
                gis="https://beacon.schneidercorp.com/Application.aspx?AppID=792&LayerID=11749&PageTypeID=2&PageID=5268",
                overlays=[geo("TAYLOR")],
                gaps=[
                    "Partial. Taylor parcels are ARPC MIL1 filtered to CNTYNAME='TAYLOR'. FDOR 2025 fills blank acreage, owner, value, DOR use, and roll-year sale by PARCEL_ID.",
                    "County future land use is the zoning-equivalent district, and the adopted map is a PDF. These rows use the UF GeoPlan 2008 statewide broad land-use categories, not current zoning. Perry zoning is a PDF. Perry, Utah was not used.",
                ],
                featureGaps=[GEOPLAN_LABEL],
            ),
            "12125": base(
                "Union",
                "partial",
                _srwmd(13, "fl-union-srwmd-12125"),
                appraiser="https://union.floridapa.com/GIS/?pin={id}",
                gis="https://union.floridapa.com/GIS/",
                parcelIdLabel="PIN",
                gaps=[
                    "Partial. Union parcels are SRWMD_Parcels layer 13, Lake Butler, Florida. Acreage is AREANO, 5.0–150.0 inclusive. FDOR 2025 fills blank owner, value, DOR use, and roll-year sale by PIN.",
                    "No queryable zoning or future land use. Union County in South Carolina, North Carolina, and other states was not used.",
                ],
                featureGaps=["No queryable Union County, Florida zoning or future land use layer."],
            ),
            "12129": base(
                "Wakulla",
                "live",
                {
                    "url": "https://services9.arcgis.com/vAltLjtfYIJc7pDt/arcgis/rest/services/ParcelM/FeatureServer/0/query",
                    "where": "MAP_ACRES>=5 AND MAP_ACRES<=150",
                    "fields": ["PARCEL_ID", "MAP_ACRES", "URL"],
                    "id": "PARCEL_ID",
                    "acres": "MAP_ACRES",
                    "source": "fl-wakulla-parcelm-12129",
                },
                fdorKey="strip-dashes",
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?AppID=836&LayerID=15205&PageTypeID=4&PageID=6833&KeyValue={id}",
                gis="https://gis-portal-update-wakullaplanning.hub.arcgis.com/",
                overlays=[
                    {
                        "role": "zoning",
                        "kind": "polygons",
                        "url": "https://services9.arcgis.com/vAltLjtfYIJc7pDt/arcgis/rest/services/Zoning_Map/FeatureServer/30/query",
                        "where": "1=1",
                        "fields": ["CUR_ZONING", "ZONE_TYPE"],
                        "codeField": "CUR_ZONING",
                        "labelField": "ZONE_TYPE",
                        "jurisdiction": "Wakulla",
                        "source": "wakulla-zoning",
                    },
                    {
                        "role": "flu",
                        "kind": "polygons",
                        "url": "https://services9.arcgis.com/vAltLjtfYIJc7pDt/arcgis/rest/services/Future_Land_Use/FeatureServer/8/query",
                        "where": "1=1",
                        "fields": ["LAND_USE", "Abbr", "Des"],
                        "codeField": "Abbr",
                        "labelField": "LAND_USE",
                        "jurisdiction": "Wakulla",
                        "source": "wakulla-flu",
                    },
                ],
                gaps=[
                    "Wakulla parcels are ParcelM. Acreage is MAP_ACRES, 5.0–150.0 inclusive. The layer has no owner or value. FDOR 2025 joins on PARCEL_ID with dashes removed.",
                    "Zoning is Zoning_Map layer 30. Future land use is Future_Land_Use layer 8. Sopchoppy and St. Marks city zoning are not separate layers on this card.",
                    "Sale history beyond the FDOR roll year is not on this extract.",
                ],
            ),
            "12133": base(
                "Washington",
                "live",
                {
                    "url": "https://services2.arcgis.com/xDFo56nFuq1SBnBw/arcgis/rest/services/WashingtonParcelsAGOL/FeatureServer/0/query",
                    "where": "CALC_ACRES>=5 AND CALC_ACRES<=150",
                    "fields": ["PARCELNO", "CALC_ACRES", "SITE_ADDRE", "CITY"],
                    "id": "PARCELNO",
                    "acres": "CALC_ACRES",
                    "situs": "SITE_ADDRE",
                    "city": "CITY",
                    "source": "fl-washington-agol-12133",
                },
                appraiser="https://qpublic.schneidercorp.com/Application.aspx?AppID=896&LayerID=16944&PageTypeID=4&PageID=7615&KeyValue={id}",
                gis="https://qpublic.schneidercorp.com/Application.aspx?AppID=896&LayerID=16944&PageTypeID=2&PageID=7613",
                overlays=[
                    {
                        "role": "flu",
                        "kind": "polygons",
                        "url": "https://services2.arcgis.com/xDFo56nFuq1SBnBw/arcgis/rest/services/WashingtonFLUM_D/FeatureServer/0/query",
                        "where": "1=1",
                        "fields": ["FLU"],
                        "codeField": "FLU",
                        "jurisdiction": "Washington",
                        "source": "washington-flum",
                    },
                    {
                        "role": "flu",
                        "kind": "polygons",
                        "url": "https://services2.arcgis.com/xDFo56nFuq1SBnBw/arcgis/rest/services/EbroFLU/FeatureServer/0/query",
                        "where": "1=1",
                        "fields": ["FLU"],
                        "codeField": "FLU",
                        "jurisdiction": "Ebro",
                        "source": "ebro-flu",
                    },
                ],
                gaps=[
                    "Washington parcels are WashingtonParcelsAGOL. Acreage is CALC_ACRES, 5.0–150.0 inclusive. Owner, value, DOR use, and roll-year sale come from the FDOR 2025 join on PARCEL_ID.",
                    "Future land use is WashingtonFLUM_D, with Ebro inside the town layer. There is no countywide zoning FeatureServer.",
                ],
                featureGaps=["No countywide Washington zoning layer. Future land use is the county FLUM."],
            ),
        }
    )


_init_specs()


def fl_rest_spec(fips: str) -> dict:
    spec = SPECS[fips]
    return {
        "kind": "fl-rest-batch1",
        "source": spec["source"],
        "coverage": spec["coverage"],
        "url": spec["url"],
        "gaps": list(spec["gaps"]),
        "status": spec["status"],
    }


def in_band(acres: float | None) -> bool:
    return isinstance(acres, (int, float)) and not isinstance(acres, bool) and MIN_ACRES <= float(acres) <= MAX_ACRES


def acres_from_sqft(value: Any) -> float | None:
    number = _num(value)
    if number is None or number <= 0:
        return None
    return number / SQFT_PER_ACRE


def in_county(fips: str, lon: float, lat: float) -> bool:
    west, south, east, north = COUNTY_BBOX[fips]
    return west <= lon <= east and south <= lat <= north


def fdor_parcel_key(fips: str, parcel_id: str) -> str:
    if SPECS[fips]["fdorKey"] == "strip-dashes":
        return parcel_id.replace("-", "")
    return parcel_id


def fdor_where(parcel_ids: list[str]) -> str:
    quoted = ",".join("'" + parcel_id.replace("'", "''") + "'" for parcel_id in parcel_ids)
    return f"PARCEL_ID IN ({quoted})"


def prefer_fdor_owner(county_owner: str | None, fdor_owner: str | None) -> tuple[str | None, bool]:
    county = _clean(county_owner)
    fdor = _clean(fdor_owner)
    if not fdor:
        return county, False
    conflict = bool(county and _norm_owner(county) != _norm_owner(fdor))
    return fdor, conflict


def _norm_owner(value: str) -> str:
    text = " ".join(value.upper().replace("&", " ").replace(",", " ").split())
    return text.strip()


def appraiser_url(fips: str, parcel_id: str) -> str:
    spec = SPECS[fips]
    template = spec["appraiser"]
    if not spec["deepLink"]:
        return template
    token = urllib.parse.quote(parcel_id, safe="")
    return template.replace("{id}", token)


def gis_viewer_url(fips: str) -> str:
    return SPECS[fips]["gis"]


def gis_viewer_url_alt(fips: str) -> str | None:
    return SPECS[fips].get("gisAlt")


def assert_out_fields(fields: list[str]) -> None:
    for field in fields:
        if field in FORBIDDEN_FIELDS or field.lower() in {"ownerphone", "owneremail"}:
            raise RuntimeError(f"refusing to request {field}")


def dedupe_attribute_rows(rows: list[dict], id_field: str, code_field: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for row in rows:
        parcel_id = _parcel_id(row.get(id_field))
        code = usable_code(row.get(code_field))
        if not parcel_id or not code:
            continue
        if parcel_id not in found:
            found[parcel_id] = code
    return found


def usable_code(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    if text.upper() in {"", "N/A", "NA", "NONE", "NULL", "UNKNOWN", "TBD", "0"}:
        return None
    return text


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text or None


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def _positive(value: Any) -> float | None:
    parsed = _num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _year(value: Any) -> int | None:
    parsed = _num(value)
    if parsed is None:
        return None
    year = int(parsed)
    if 1980 <= year <= 2026:
        return year
    return None


def _parcel_id(value: Any) -> str | None:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return _clean(value)


def _zip(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 5 or len(digits) == 9:
        return digits[:5]
    return None


def _city(value: Any) -> str | None:
    text = _clean(value)
    if not text or text in {"0", "00"}:
        return None
    if text.replace(".", "", 1).isdigit():
        return None
    return text


def _is_tls_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "certificate" in text or "ssl" in text or "tls" in text


def _fetch_once(url: str, params: dict | None, timeout: int, insecure: bool) -> dict:
    full = url
    if params:
        full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": "darryl-land-search/fl-rest-batch1"}, method="GET")
    context = ssl._create_unverified_context() if insecure else ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_json(url: str, params: dict | None = None, timeout: int = 180) -> dict:
    host = urllib.parse.urlparse(url).hostname or ""
    if host in TLS_FALLBACK_USED:
        return _fetch_once(url, params, timeout, insecure=True)
    try:
        return _fetch_once(url, params, timeout, insecure=False)
    except Exception as exc:  # noqa: BLE001
        if host in TLS_FALLBACK_HOSTS and _is_tls_error(exc):
            TLS_FALLBACK_USED.add(host)
            return _fetch_once(url, params, timeout, insecure=True)
        raise


def _query(url: str, params: dict, timeout: int = 180) -> dict:
    data = fetch_json(url, params, timeout=timeout)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    return data


def fetch_object_ids(url: str, where: str) -> list[int]:
    data = _query(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=240)
    return [int(item) for item in (data.get("objectIds") or [])]


def fetch_by_ids(url: str, ids: list[int], out_fields: list[str], *, geometry: bool, batch: int = 20) -> list[dict]:
    assert_out_fields(out_fields)
    features: list[dict] = []
    params_base = {"outFields": ",".join(out_fields), "returnGeometry": "true" if geometry else "false", "f": "json"}
    if geometry:
        params_base["outSR"] = "4326"
    start = 0
    total = len(ids)
    while start < total:
        chunk = ids[start : start + batch]
        params = dict(params_base)
        params["objectIds"] = ",".join(str(item) for item in chunk)
        try:
            data = _query(url, params, timeout=180)
        except Exception as exc:
            if len(chunk) > 1:
                mid = max(1, len(chunk) // 2)
                features.extend(fetch_by_ids(url, chunk[:mid], out_fields, geometry=geometry, batch=mid))
                features.extend(fetch_by_ids(url, chunk[mid:], out_fields, geometry=geometry, batch=max(1, len(chunk) - mid)))
                start += len(chunk)
                continue
            message = str(exc)
            if "outFields" in message and "invalid" in message.lower():
                raise RuntimeError(message) from exc
            print(f"    skip object {chunk[0]} ({exc})", flush=True)
            start += len(chunk)
            continue
        page = data.get("features") or []
        if len(page) < len(chunk) and len(chunk) > 1:
            mid = max(1, len(chunk) // 2)
            features.extend(fetch_by_ids(url, chunk[:mid], out_fields, geometry=geometry, batch=mid))
            features.extend(fetch_by_ids(url, chunk[mid:], out_fields, geometry=geometry, batch=max(1, len(chunk) - mid)))
            start += len(chunk)
            continue
        features.extend(page)
        start += len(chunk)
        if start == len(chunk) or start == total or start % 1000 < batch:
            print(f"    {min(start, total)}/{total} {url.rsplit('/', 2)[-2]}", flush=True)
    return features


def fetch_layer(url: str, where: str, out_fields: list[str], *, geometry: bool) -> list[dict]:
    assert_out_fields(out_fields)
    try:
        ids = fetch_object_ids(url, where)
    except Exception as exc:
        print(f"    id query failed ({exc}); trying one page", flush=True)
        ids = []
    if ids:
        return fetch_by_ids(url, ids, out_fields, geometry=geometry)
    params = {
        "where": where,
        "outFields": ",".join(out_fields),
        "returnGeometry": "true" if geometry else "false",
        "f": "json",
    }
    if geometry:
        params["outSR"] = "4326"
    data = _query(url, params, timeout=240)
    return data.get("features") or []


class SpatialIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = _bbox(feature.get("geometry"))
        if not bbox:
            return
        west, south, east, north = bbox
        feature["_bboxArea"] = max(0.0, (east - west) * (north - south))
        ix0, ix1 = int(west // self.cell), int(east // self.cell)
        iy0, iy1 = int(south // self.cell), int(north // self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 400:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        found: list[dict] = []
        for feature in self.buckets.get((int(x // self.cell), int(y // self.cell)), []):
            if contains_point(feature.get("geometry"), x, y):
                found.append(feature)
        for feature in self.broad:
            if contains_point(feature.get("geometry"), x, y):
                found.append(feature)
        if not found:
            return None
        found.sort(key=lambda item: item.get("_bboxArea") or 0)
        return found[0]


def _bbox(geometry: dict | None) -> tuple[float, float, float, float] | None:
    if not geometry:
        return None
    xs: list[float] = []
    ys: list[float] = []
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    rings = coords if kind == "Polygon" else [ring for poly in coords for ring in poly] if kind == "MultiPolygon" else []
    for ring in rings:
        for x, y in ring:
            xs.append(float(x))
            ys.append(float(y))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _seed():
    import seed_market_parcels as seed

    return seed


def _geometry_feature(seed: Any, item: dict) -> tuple[dict | None, tuple[float, float] | None]:
    geometry, _acres = seed.rings_to_feature_geometry(item.get("geometry"))
    if not geometry:
        return None, None
    center = seed.centroid_of(geometry)
    if not seed.plausible_centroid(center):
        return None, None
    return geometry, center


def _situs(attrs: dict, parcels: dict) -> str | None:
    parts = parcels.get("situsParts")
    if parts:
        bits = [_clean(attrs.get(field)) for field in parts]
        text = " ".join(bit for bit in bits if bit)
        return text or None
    return _clean(attrs.get(parcels.get("situs") or ""))


def _sale_date(attrs: dict, parcels: dict) -> str | None:
    if parcels.get("saleEpoch"):
        raw = _num(attrs.get(parcels["saleEpoch"]))
        if raw and raw > 10_000_000_000:
            stamp = time.gmtime(raw / 1000.0)
            if 1980 <= stamp.tm_year <= 2026:
                return f"{stamp.tm_year:04d}-{stamp.tm_mon:02d}-{stamp.tm_mday:02d}"
        return None
    year = _year(attrs.get(parcels.get("saleYear")))
    month = _num(attrs.get(parcels.get("saleMonth"))) if parcels.get("saleMonth") else None
    if year and month and 1 <= int(month) <= 12:
        return f"{year:04d}-{int(month):02d}"
    if year:
        return str(year)
    return None


def _apply_fdor(feature: dict, row: dict | None, mode: str) -> bool:
    if not row:
        return False
    props = feature["properties"]
    if mode == "prefer-owner":
        owner, conflict = prefer_fdor_owner(props.get("ownerName"), row.get("OWN_NAME"))
        if owner:
            props["ownerName"] = owner
        if conflict:
            gaps = list(props.get("dataGaps") or [])
            if OWNER_CONFLICT not in gaps:
                gaps.append(OWNER_CONFLICT)
            props["dataGaps"] = gaps
    elif not props.get("ownerName"):
        props["ownerName"] = _clean(row.get("OWN_NAME"))
    if not props.get("situsAddress"):
        props["situsAddress"] = _clean(row.get("PHY_ADDR1"))
    if not props.get("situsCity"):
        props["situsCity"] = _city(row.get("PHY_CITY"))
    if not props.get("situsZip"):
        props["situsZip"] = _zip(row.get("PHY_ZIPCD"))
    mail = props.setdefault("mailingAddress", {})
    if not mail.get("line1"):
        mail["line1"] = _clean(row.get("OWN_ADDR1"))
    if not mail.get("city"):
        mail["city"] = _city(row.get("OWN_CITY"))
    if not mail.get("state"):
        mail["state"] = _clean(row.get("OWN_STATE"))
    if not mail.get("zip"):
        mail["zip"] = _zip(row.get("OWN_ZIPCD"))
    tax = props.setdefault("tax", {})
    if not _positive(tax.get("marketValue")):
        tax["marketValue"] = _positive(row.get("JV"))
    if not _positive(tax.get("assessedValue")):
        tax["assessedValue"] = _positive(row.get("AV_SD"))
    if not _positive(tax.get("taxableValue")):
        tax["taxableValue"] = _positive(row.get("TV_SD"))
    if not props.get("dorCode"):
        props["dorCode"] = usable_code(row.get("DOR_UC"))
    sale = props.setdefault("lastSale", {})
    if not sale.get("date"):
        year = _year(row.get("SALE_YR1"))
        if year:
            sale["date"] = str(year)
    if not _positive(sale.get("price")):
        sale["price"] = _positive(row.get("SALE_PRC1"))
    if not sale.get("qualified"):
        qualified = _clean(row.get("QUAL_CD1"))
        if qualified and qualified not in {"0"}:
            sale["qualified"] = qualified
    if not in_band(props.get("acreage")):
        acres = acres_from_sqft(row.get("LND_SQFOOT"))
        if acres is not None:
            props["acreage"] = round(acres, 4)
    return True


def fetch_fdor(keys: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    unique = [key for key in dict.fromkeys(keys) if key]
    batch = 40
    for start in range(0, len(unique), batch):
        chunk = unique[start : start + batch]
        try:
            data = _query(
                FDOR_URL,
                {
                    "where": fdor_where(chunk),
                    "outFields": ",".join(FDOR_FIELDS),
                    "returnGeometry": "false",
                    "f": "json",
                },
                timeout=90,
            )
        except Exception as exc:
            if len(chunk) > 1:
                found.update(fetch_fdor(chunk[: len(chunk) // 2]))
                found.update(fetch_fdor(chunk[len(chunk) // 2 :]))
                continue
            print(f"    fdor skip {chunk[0]} ({exc})", flush=True)
            continue
        for item in data.get("features") or []:
            attrs = item.get("attributes") or {}
            parcel_id = _parcel_id(attrs.get("PARCEL_ID"))
            if parcel_id:
                found[parcel_id] = attrs
        if start % 400 == 0:
            print(f"    fdor {min(start + batch, len(unique))}/{len(unique)}", flush=True)
    return found


def _index_polygons(raw: list[dict], overlay: dict) -> SpatialIndex:
    index = SpatialIndex()
    code_field = overlay.get("codeField")
    for item in raw:
        rings = (item.get("geometry") or {}).get("rings")
        geometry = esri_rings_to_geojson(rings) if rings else None
        if not geometry:
            continue
        attrs = item.get("attributes") or {}
        code = usable_code(attrs.get(code_field)) if code_field else usable_code(overlay.get("code"))
        if not code and overlay.get("kind") != "categories":
            continue
        if not code:
            code = overlay.get("code")
        if not code:
            continue
        label = _clean(attrs.get(overlay.get("labelField"))) if overlay.get("labelField") else None
        jurisdiction = _clean(attrs.get(overlay.get("jurisdictionField"))) if overlay.get("jurisdictionField") else overlay.get("jurisdiction")
        feature = {
            "geometry": geometry,
            "code": code,
            "label": label,
            "jurisdiction": jurisdiction or overlay.get("jurisdiction") or "",
            "fluCode": usable_code(attrs.get(overlay.get("fluCodeField"))) if overlay.get("fluCodeField") else None,
            "fluLabel": _clean(attrs.get(overlay.get("fluLabelField"))) if overlay.get("fluLabelField") else None,
            "overlay": overlay,
        }
        index.add(feature)
    return index


def _index_categories(overlay: dict) -> SpatialIndex:
    index = SpatialIndex()
    for layer in overlay["layers"]:
        url, code = layer[0], layer[1]
        jurisdiction = layer[2] if len(layer) > 2 else overlay.get("jurisdiction") or ""
        try:
            raw = fetch_layer(url, "1=1", ["*"], geometry=True)
        except Exception as exc:
            print(f"    category skip {code} ({exc})", flush=True)
            continue
        for item in raw:
            rings = (item.get("geometry") or {}).get("rings")
            geometry = esri_rings_to_geojson(rings) if rings else None
            if not geometry:
                continue
            index.add(
                {
                    "geometry": geometry,
                    "code": code,
                    "label": code,
                    "jurisdiction": jurisdiction,
                    "fluCode": None,
                    "fluLabel": None,
                    "overlay": overlay,
                }
            )
    return index


def _fetch_attribute_table(overlay: dict, parcel_ids: list[str] | None) -> dict[str, dict]:
    table: dict[str, dict] = {}
    fields = list(overlay["fields"])
    assert_out_fields(fields)
    if overlay.get("byParcelIds") and parcel_ids:
        id_field = overlay["idField"]
        batch = 60
        for start in range(0, len(parcel_ids), batch):
            chunk = parcel_ids[start : start + batch]
            where = f"{id_field} IN ({','.join(chr(39) + item.replace(chr(39), chr(39) * 2) + chr(39) for item in chunk)})"
            try:
                rows = fetch_layer(overlay["url"], where, fields, geometry=False)
            except Exception as exc:
                print(f"    attribute batch failed ({exc})", flush=True)
                continue
            for item in rows:
                attrs = item.get("attributes") or {}
                parcel_id = _parcel_id(attrs.get(id_field))
                if not parcel_id:
                    continue
                if overlay.get("dedupe") and parcel_id in table:
                    continue
                table[parcel_id] = attrs
        return table
    rows = fetch_layer(overlay["url"], overlay.get("where") or "1=1", fields, geometry=False)
    id_field = overlay["idField"]
    code_field = overlay["codeField"]
    collapsed = dedupe_attribute_rows([item.get("attributes") or {} for item in rows], id_field, code_field)
    labels: dict[str, str | None] = {}
    if overlay.get("labelField"):
        for item in rows:
            attrs = item.get("attributes") or {}
            parcel_id = _parcel_id(attrs.get(id_field))
            if parcel_id and parcel_id not in labels:
                labels[parcel_id] = _clean(attrs.get(overlay["labelField"]))
    for parcel_id, code in collapsed.items():
        table[parcel_id] = {code_field: code, overlay.get("labelField") or "_label": labels.get(parcel_id)}
    return table


def _set_zoning(feature: dict, code: str | None, jurisdiction: str, label: str | None) -> bool:
    text = usable_code(code)
    if not text:
        return False
    props = feature["properties"]
    props["zoningCode"] = text
    pretty = label if label and label != text else text
    props["zoningDistrict"] = f"{jurisdiction}:{pretty}" if jurisdiction else pretty
    props["jurisdictionCode"] = jurisdiction or props.get("jurisdictionCode")
    return True


def _set_flu(feature: dict, code: str | None, jurisdiction: str, source: str, label: str | None, label_mode: str | None) -> bool:
    text = usable_code(code)
    if not text:
        return False
    shown = label or text
    if label_mode == "geoplan":
        shown = f"{text} — {GEOPLAN_LABEL}"
        source = GEOPLAN_LABEL
    feature["properties"]["flu"] = {
        "code": text,
        "label": shown,
        "jurisdiction": jurisdiction,
        "source": source,
    }
    return True


def _apply_hit(feature: dict, hit: dict) -> tuple[bool, bool]:
    overlay = hit["overlay"]
    role = overlay["role"]
    jurisdiction = hit.get("jurisdiction") or overlay.get("jurisdiction") or ""
    zoned = False
    flued = False
    if role in {"zoning", "both"}:
        zoned = _set_zoning(feature, hit.get("code"), jurisdiction, hit.get("label"))
    if role in {"flu", "both"} or hit.get("fluCode"):
        flu_code = hit.get("fluCode") or (hit.get("code") if role in {"flu", "both"} else None)
        flu_label = hit.get("fluLabel") or (hit.get("label") if role in {"flu", "both"} else None)
        if flu_code:
            flued = _set_flu(feature, flu_code, jurisdiction, overlay.get("source") or "", flu_label, overlay.get("labelMode"))
    return zoned, flued


def _apply_overlays(features: list[dict], overlays: list[dict], notes: list[str]) -> None:
    parcel_ids = [feature["properties"]["parcelId"] for feature in features]
    for overlay in overlays:
        try:
            if overlay["kind"] == "attributes":
                table = _fetch_attribute_table(overlay, parcel_ids if overlay.get("byParcelIds") else None)
                hits = 0
                for feature in features:
                    attrs = table.get(feature["properties"]["parcelId"])
                    if not attrs:
                        continue
                    hit = {
                        "code": attrs.get(overlay["codeField"]),
                        "label": attrs.get(overlay.get("labelField")),
                        "jurisdiction": overlay.get("jurisdiction"),
                        "fluCode": attrs.get(overlay["fluCodeField"]) if overlay.get("fluCodeField") else None,
                        "fluLabel": attrs.get(overlay["fluLabelField"]) if overlay.get("fluLabelField") else None,
                        "overlay": overlay,
                    }
                    zoned, flued = _apply_hit(feature, hit)
                    if zoned or flued:
                        hits += 1
                notes.append(f"{overlay['source']} joined {hits}/{len(features)}.")
                continue
            if overlay["kind"] == "categories":
                index = _index_categories(overlay)
            else:
                raw = fetch_layer(overlay["url"], overlay.get("where") or "1=1", overlay["fields"], geometry=True)
                index = _index_polygons(raw, overlay)
            hits = 0
            for feature in features:
                lon, lat = feature["properties"]["centroid"]
                found = index.hit(lon, lat)
                if not found:
                    continue
                zoned, flued = _apply_hit(feature, found)
                if zoned or flued:
                    hits += 1
            notes.append(f"{overlay.get('source') or overlay['role']} joined {hits}/{len(features)}.")
        except Exception as exc:
            if overlay.get("optional"):
                notes.append(f"{overlay.get('source') or overlay['role']} was not joined ({exc}).")
                continue
            raise


def _build_features(seed: Any, county: dict, markets: list[str], spec: dict) -> tuple[list[dict], list[str]]:
    parcels = spec["parcels"]
    raw = fetch_layer(parcels["url"], parcels["where"], parcels["fields"], geometry=True)
    features: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        attrs = item.get("attributes") or {}
        parcel_id = _parcel_id(attrs.get(parcels["id"]))
        if not parcel_id or parcel_id in seen:
            continue
        if parcels.get("acresSqft"):
            acres = acres_from_sqft(attrs.get(parcels["acresSqft"]))
        else:
            acres = _num(attrs.get(parcels.get("acres")))
        if acres is None:
            continue
        acres = round(float(acres), 4)
        if not in_band(acres):
            continue
        geometry, center = _geometry_feature(seed, item)
        if not geometry or not center or not in_county(county["fips"], center[0], center[1]):
            continue
        feature = seed.empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source=spec["source"],
            owner=_clean(attrs.get(parcels.get("owner") or "")),
            situs=_situs(attrs, parcels),
            city=_city(attrs.get(parcels.get("city") or "")),
            zip_code=_zip(attrs.get(parcels.get("zip") or "")),
            dor=usable_code(attrs.get(parcels.get("dor") or "")),
            sale_price=_positive(attrs.get(parcels.get("salePrice") or "")),
            sale_date=_sale_date(attrs, parcels),
            sale_qualified=usable_code(attrs.get(parcels.get("saleQualified") or "")),
            market_value=_positive(attrs.get(parcels.get("marketValue") or "")),
            assessed=_positive(attrs.get(parcels.get("assessed") or "")),
            taxable=_positive(attrs.get(parcels.get("taxable") or "")),
            mail1=_clean(attrs.get(parcels.get("mail") or "")),
            mail2=_clean(attrs.get(parcels.get("mail2") or "")),
            mail_city=_city(attrs.get(parcels.get("mailCity") or "")),
            mail_state=_clean(attrs.get(parcels.get("mailState") or "")),
            mail_zip=_zip(attrs.get(parcels.get("mailZip") or "")),
        )
        feature["properties"]["appraiserUrl"] = appraiser_url(county["fips"], parcel_id)
        feature["properties"]["gisViewerUrl"] = gis_viewer_url(county["fips"])
        feature["properties"]["gisViewerUrlAlt"] = gis_viewer_url_alt(county["fips"])
        feature["properties"]["dataGaps"] = list(spec.get("featureGaps") or [])
        feature["properties"]["opportunityZone"] = None
        feature["properties"]["oz2Eligibility"] = None
        feature["properties"]["nearestRoad"] = None
        seen.add(parcel_id)
        features.append(feature)
    notes: list[str] = []
    keys = [fdor_parcel_key(county["fips"], feature["properties"]["parcelId"]) for feature in features]
    fdor = fetch_fdor(keys)
    matched = 0
    conflicts = 0
    for feature in features:
        key = fdor_parcel_key(county["fips"], feature["properties"]["parcelId"])
        row = fdor.get(key)
        if _apply_fdor(feature, row, spec["fdor"]):
            matched += 1
        if OWNER_CONFLICT in (feature["properties"].get("dataGaps") or []):
            conflicts += 1
        if not in_band(feature["properties"].get("acreage")):
            feature["properties"]["_drop"] = True
    kept = [feature for feature in features if not feature["properties"].pop("_drop", False)]
    notes.append(f"FDOR 2025 joined {matched}/{len(features)} parcel ids. County-number-only filters were not used.")
    if spec["fdor"] == "prefer-owner":
        notes.append(f"FDOR owner replaced a conflicting county-roll name on {conflicts} parcels.")
    if matched * 2 < len(features):
        notes.append("FDOR parcel-id match covered less than half of this county. Unmatched rows keep the county attributes only.")
    _apply_overlays(kept, spec.get("overlays") or [], notes)
    kept.sort(key=lambda row: row["properties"]["parcelId"])
    return kept, notes


def download_fl_rest(county: dict, markets: list[str], spec: dict | None = None) -> dict:
    seed = _seed()
    fips = county["fips"]
    full = SPECS[fips]
    if spec is None:
        spec = fl_rest_spec(fips)
    print(f"Pulling {county['name']} FL ({fips}) via {full['source']}", flush=True)
    features, notes = _build_features(seed, county, markets, full)
    if not features:
        raise RuntimeError(f"{fips} kept no 5–150 acre parcels")
    if not all(in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{fips} emitted a parcel outside 5–150 acres")
    for feature in features:
        feature["properties"]["marketIds"] = list(markets)
        props = feature["properties"]
        if props.get("opportunityZone") or props.get("nearestRoad"):
            raise RuntimeError(f"{fips} invented a screening field")
        blob = json.dumps(props)
        if "OwnerPhone" in blob or "OwnerEmail" in blob:
            raise RuntimeError(f"{fips} wrote a forbidden owner field")
    path, lookup, tiles = seed.write_tiles(county, features)
    gaps = [*(full.get("gaps") or []), *notes]
    print(f"  kept {len(features)} ({full['coverage']})", flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=full["coverage"],
        partition="tiles",
        path=path,
        lookup=lookup,
        source=full["source"],
        query_url=full["url"],
        gaps=gaps,
        source_count=len(features),
        dropped=0,
        tile_count=tiles,
    )


def _public_row(row: dict) -> dict:
    return {
        "name": row["name"],
        "fips": row["fips"],
        "state": row["state"],
        "markets": row.get("markets") or [MARKETS[row["fips"]]],
        "featureCount": row.get("featureCount") or 0,
        "coverage": row.get("coverage"),
        "partition": row.get("partition"),
        "minAcres": MIN_ACRES,
        "maxAcres": MAX_ACRES,
        "source": row.get("source"),
        "queryUrl": row.get("queryUrl"),
        "gaps": row.get("gaps") or [],
        "path": row.get("path"),
        "lookup": row.get("lookup"),
        "sourceCount": row.get("sourceCount"),
        "dropped": row.get("dropped"),
        "tileCount": row.get("tileCount"),
    }


def _summary_counts(rows: list[dict]) -> tuple[int, int, int, int]:
    parcel_count = sum(int(row.get("featureCount") or 0) for row in rows)
    complete = sum(1 for row in rows if row.get("coverage") == "complete-gte-5ac" and row.get("featureCount"))
    sample = sum(1 for row in rows if row.get("coverage") in {"sample", "partial"} and row.get("featureCount"))
    gaps = sum(1 for row in rows if not row.get("featureCount"))
    return parcel_count, complete, sample, gaps


def _coverage_line(row: dict) -> str:
    count = int(row.get("featureCount") or 0)
    return f"| {row['name']} | {row['state']} | {row['fips']} | {row.get('coverage')} | {count:,} | {row.get('source')} |"


def refresh_fl_rest_index() -> None:
    """Patch these counties into the existing shelves without rewriting other markets."""
    seed = _seed()
    index_path = seed.OUT_DIR / "index.json"
    index = json.loads(index_path.read_text())
    by_market: dict[str, list[dict]] = defaultdict(list)
    for fips in FIPS:
        path = seed.COUNTY_DIR / fips / "county.json"
        if not path.exists():
            continue
        by_market[MARKETS[fips]].append(json.loads(path.read_text()))

    for market, rows in by_market.items():
        rows.sort(key=lambda row: row["name"])
        if market in NEW_SHELVES:
            meta_rows = [_public_row(row) for row in rows]
            tier = "shelf"
        else:
            rel_existing = index["markets"][market]["path"]
            meta_path = seed.ROOT / rel_existing
            meta = json.loads(meta_path.read_text())
            incoming = {row["fips"]: _public_row(row) for row in rows}
            merged = []
            seen = set()
            for old in meta.get("counties") or []:
                if old["fips"] in incoming:
                    merged.append(incoming[old["fips"]])
                    seen.add(old["fips"])
                else:
                    merged.append(old)
            for fips, row in incoming.items():
                if fips not in seen:
                    merged.append(row)
            merged.sort(key=lambda row: row["name"])
            meta_rows = merged
            tier = meta.get("tier") or "other"
        parcel_count, complete, sample, gaps = _summary_counts(meta_rows)
        rel = f"data/fixtures/market-parcels/markets/{seed.slug(market)}/meta.json"
        meta_out = {
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "market": market,
            "tier": tier,
            "parcelCount": parcel_count,
            "coreMinAcres": MIN_ACRES,
            "coreMaxAcres": MAX_ACRES,
            "tile": {"originLon": seed.ORIGIN_LON, "originLat": seed.ORIGIN_LAT, "tileDeg": seed.TILE_DEG},
            "notes": _new_shelf_notes(market),
        }
        if market not in NEW_SHELVES:
            previous = json.loads((seed.ROOT / index["markets"][market]["path"]).read_text())
            note = "FL-rest batch 1 updated parcel rows on this shelf. Eligible tracts were not added."
            notes = list(previous.get("notes") or [])
            if note not in notes:
                notes.append(note)
            meta_out["notes"] = notes
            meta_out["tier"] = previous.get("tier") or tier
        meta_out["counties"] = meta_rows
        market_path = seed.ROOT / rel
        market_path.parent.mkdir(parents=True, exist_ok=True)
        market_path.write_text(json.dumps(meta_out, indent=2, ensure_ascii=False) + "\n")
        index["markets"][market] = {
            "tier": meta_out["tier"],
            "parcelCount": parcel_count,
            "completeCountyCount": complete,
            "sampleCountyCount": sample,
            "gapCountyCount": gaps,
            "path": rel,
            "counties": [
                {
                    "name": row["name"],
                    "state": row["state"],
                    "fips": row["fips"],
                    "featureCount": row.get("featureCount") or 0,
                    "coverage": row.get("coverage"),
                    "minAcres": MIN_ACRES,
                    "maxAcres": MAX_ACRES,
                    "gaps": (row.get("gaps") or [])[:2],
                }
                for row in meta_rows
            ],
        }
        _patch_coverage(seed.ROOT, market, meta_rows, parcel_count, complete, sample, gaps, meta_out["tier"])
    index["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")


def _new_shelf_notes(market: str) -> list[str]:
    notes = [
        "Loaded only when this market is selected.",
        "Acreage is 5.0–150.0 inclusive. Utilities are not joined.",
        "FL-rest batch 1 parcel shelf. Eligible tracts were not added.",
    ]
    if market == "North Florida":
        notes.append("Hamilton, Lafayette, Suwannee, and Union stay partial.")
    elif market == "Panhandle Florida":
        notes.append("Franklin, Gulf, and Holmes stay partial.")
    return notes


def _patch_coverage(root: Any, market: str, rows: list[dict], parcel_count: int, complete: int, sample: int, gaps: int, tier: str) -> None:
    summary = f"| {market} | {tier} | {parcel_count:,} | {complete} | {sample} | {gaps} |"
    owned = {row["fips"] for row in rows}
    for relative in ("data/fixtures/market-parcels/coverage.md", "docs/market-parcels.md"):
        path = root / relative
        if not path.exists():
            continue
        lines = path.read_text().splitlines()
        replaced = False
        for index, line in enumerate(lines):
            if line.startswith(f"| {market} |"):
                lines[index] = summary
                replaced = True
                break
        if not replaced and market in NEW_SHELVES:
            for index, line in enumerate(lines):
                if line.startswith("| Jackson MS |"):
                    lines.insert(index + 1, summary)
                    break
        if market in NEW_SHELVES:
            if not any(line.startswith(f"### {market}") for line in lines):
                lines.extend(["", f"### {market}", "", "| County | State | FIPS | Coverage | Parcels | Source |", "| --- | --- | --- | --- | ---: | --- |"])
                for row in rows:
                    lines.append(_coverage_line(row))
            else:
                rewritten: list[str] = []
                for line in lines:
                    matched = next((row for row in rows if line.startswith(f"| {row['name']} | {row['state']} | {row['fips']} |")), None)
                    rewritten.append(_coverage_line(matched) if matched else line)
                lines = rewritten
            path.write_text("\n".join(lines) + "\n")
            continue
        updated: list[str] = []
        seen = set()
        for line in lines:
            matched = None
            for row in rows:
                if line.startswith(f"| {row['name']} | {row['state']} | {row['fips']} |"):
                    matched = row
                    break
            if matched:
                updated.append(_coverage_line(matched))
                seen.add(matched["fips"])
                if (
                    market == "North-Central Florida"
                    and matched["fips"] == "12075"
                    and "12083" in owned
                    and "12083" not in seen
                ):
                    marion = next(row for row in rows if row["fips"] == "12083")
                    updated.append(_coverage_line(marion))
                    seen.add("12083")
            else:
                updated.append(line)
        path.write_text("\n".join(updated) + "\n")


COUNTIES = {fips: {"name": SPECS[fips]["name"], "state": "Florida", "fips": fips} for fips in FIPS}


def main() -> None:
    import argparse
    from concurrent.futures import ThreadPoolExecutor, as_completed

    parser = argparse.ArgumentParser()
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--no-index", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    wanted = {name.lower() for name in args.county}
    jobs = []
    for fips, county in COUNTIES.items():
        if wanted and county["name"].lower() not in wanted and fips not in wanted:
            continue
        jobs.append((fips, county, [MARKETS[fips]]))

    errors: list[str] = []

    def run(job: tuple) -> None:
        fips, county, markets = job
        try:
            download_fl_rest(county, markets)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{county['name']} {fips}: {exc}")
            print(f"FAILED {county['name']} {fips}: {exc}", flush=True)

    if jobs:
        workers = max(1, min(args.workers, len(jobs)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run, job) for job in jobs]
            for future in as_completed(futures):
                future.result()
    if not args.no_index:
        refresh_fl_rest_index()
    if errors:
        raise SystemExit("County downloads failed:\n" + "\n".join(errors))


if __name__ == "__main__":
    main()
