"""Valdosta, Macon, Athens, Hilton Head, and Jackson MS parcel shelves.

Public GIS only. Acreage is 5–150 inclusive. Opportunity Zone designations,
school letter grades, and base flood elevations are not assigned.

Mississippi layers are read from gis.cmpdd.org. That host omits the GoDaddy
intermediate, so the pinned public intermediate in scripts/certs is added to
the trust store. gis3.cmpdd.org and portal.cmpdd.org are not used.
"""

from __future__ import annotations

import math
import re
import ssl
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

from parcel_geometry import contains_point, esri_rings_to_geojson

import seed_market_parcels as seed

ROOT = Path(__file__).resolve().parents[1]
GDIG2 = Path(__file__).resolve().parent / "certs" / "godaddy-g2.pem"
REJECTED_HOSTS = ("gis3.cmpdd.org", "portal.cmpdd.org")

QPUBLIC = "https://qpublic.schneidercorp.com/Application.aspx?App={app}&Layer=Parcels&PageType=Report&KeyValue="

NO_OZ = "No Opportunity Zone designation, school letter grade, or base flood elevation was assigned."
STATE_AADT = (
    "Traffic counts use the statewide state DOT layer for this footprint. "
    "Florida FDOT segments are not copied onto these parcels. A count farther than 15 km stays unknown."
)
NO_AADT = STATE_AADT


def install_gis_ssl() -> None:
    """Trust gis.cmpdd.org even though the server sends only the leaf certificate."""
    if not GDIG2.exists():
        raise RuntimeError(f"Missing GoDaddy intermediate at {GDIG2}")
    context = ssl.create_default_context()
    context.load_verify_locations(str(GDIG2))
    urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=context)))


def norm_id(value: Any) -> str | None:
    text = seed.clean(value)
    if not text:
        return None
    compact = re.sub(r"\s+", "", text).upper()
    return compact or None


def combine_codes(codes: list[str]) -> str | None:
    unique: list[str] = []
    for code in codes:
        text = seed.clean(code)
        if text and text not in unique:
            unique.append(text)
    if not unique:
        return None
    return " / ".join(unique[:8])


def in_box(lon: float, lat: float, box: tuple[float, float, float, float]) -> bool:
    west, south, east, north = box
    return west <= lon <= east and south <= lat <= north


def drop_nominal_sale(price: float | None, nominal: set[float]) -> float | None:
    if price is None:
        return None
    if price <= 0 or price in nominal:
        return None
    return price


def _require_host(url: str) -> None:
    if any(host in url for host in REJECTED_HOSTS):
        raise RuntimeError(f"Rejected CMPDD host in {url}")


def _parcel(**kwargs: Any) -> dict:
    url = kwargs["url"]
    _require_host(url)
    return kwargs


def _layer(**kwargs: Any) -> dict:
    _require_host(kwargs["url"])
    return kwargs


def specs() -> dict[str, dict]:
    lowndes_box = (-83.60, 30.50, -83.00, 31.25)
    bibb_box = (-84.15, 32.45, -83.35, 33.15)
    clarke_box = (-83.65, 33.80, -83.10, 34.15)
    beaufort_box = (-81.25, 32.00, -80.30, 32.75)
    jackson_box = (-91.40, 31.45, -89.35, 33.25)
    return {
        "13185": {
            "fips": "13185",
            "source": "ga-lowndes-valor-taxparcels",
            "box": lowndes_box,
            "reportUrl": QPUBLIC.format(app="LowndesCountyGA"),
            "nominalSales": set(),
            "parcel": _parcel(
                url="https://www.valorgis.com/arcgis/rest/services/TaxOffice/TaxParcels/FeatureServer/0/query",
                where="TOTALACRES>=5 AND TOTALACRES<=150",
                outFields=[
                    "PARCEL_NO",
                    "LASTNAME",
                    "HOUSE_NO",
                    "STDIRECT",
                    "STREET_NAM",
                    "STTYPE",
                    "TOTALACRES",
                    "CURR_VAL",
                    "SALE_VAL",
                    "ZONINGCODE",
                    "DIGCLASS",
                    "ADDRESS2",
                    "CITY",
                    "STATE",
                    "ZIP",
                ],
                idField="PARCEL_NO",
                acresField="TOTALACRES",
                ownerField="LASTNAME",
                situsParts=["HOUSE_NO", "STDIRECT", "STREET_NAM", "STTYPE"],
                zoningField="ZONINGCODE",
                dorField="DIGCLASS",
                salePriceField="SALE_VAL",
                marketValueField="CURR_VAL",
                mail1Field="ADDRESS2",
                mailCityField="CITY",
                mailStateField="STATE",
                mailZipField="ZIP",
                source="ga-lowndes-valor-taxparcels",
            ),
            "layers": [
                _layer(
                    url="https://www.valorgis.com/arcgis/rest/services/PlanningDevelopment/Zoning_Detailed/MapServer/0/query",
                    where="1=1",
                    field="ZOTXT",
                    target="zoning",
                    how="spatial",
                    mode="override",
                ),
                _layer(
                    url="https://www.valorgis.com/arcgis/rest/services/PlanningDevelopment/character_areas/MapServer/0/query",
                    where="1=1",
                    field="Character_",
                    target="flu",
                    how="spatial",
                    mode="override",
                ),
                _layer(
                    url="https://www.valorgis.com/arcgis/rest/services/Valor/MunicipalBoundaries_CitiesShaded/MapServer/0/query",
                    where="1=1",
                    field="NOTE_",
                    target="jurisdiction",
                    how="spatial",
                    mode="fill",
                ),
            ],
            "gaps": [
                "Lowndes County, Georgia (FIPS 13185, Valdosta). VALOR TaxOffice/TaxParcels FeatureServer/0. TOTALACRES 5–150 inclusive. Not Lowndes County, Mississippi or Alabama.",
                "Zoning is PlanningDevelopment/Zoning_Detailed ZOTXT. Parcel ZONINGCODE remains only where the polygon join misses. Lake Park, Dasher, and Remerton have no city zoning FeatureServer.",
                "Future land use is Greater Lowndes character_areas. The map date is about 2006; the 2021 plan and draft 2026 update may supersede it.",
                "Mailing ZIP is essentially empty. Assessed MAV fields are present and unfilled. On-parcel sales are thin, and property_sales year layers stop at 2021.",
                "Mailing city is not a municipality filter.",
                STATE_AADT,
                NO_OZ,
            ],
        },
        "13021": {
            "fips": "13021",
            "source": "ga-bibb-parcelcama-2025",
            "box": bibb_box,
            "reportUrl": QPUBLIC.format(app="BibbCountyGA"),
            "nominalSales": {1.0, 100.0},
            "parcel": _parcel(
                url="https://services2.arcgis.com/zPFLSOZ5HzUzzTQb/arcgis/rest/services/ParcelCAMA_Current_2025/FeatureServer/0/query",
                where="TOTALACRES_1>=5 AND TOTALACRES_1<=150",
                outFields=[
                    "PARCEL_NO_1",
                    "LASTNAME",
                    "SITEADDRESS",
                    "SITE_ZIP",
                    "TOTALACRES_1",
                    "SALEPRICE",
                    "SALEDATE",
                    "CURR_VAL",
                    "ZONINGCODE",
                    "DIGCLASS",
                    "ADDRESS1",
                    "CITY",
                    "STATE",
                    "ZIP",
                ],
                idField="PARCEL_NO_1",
                acresField="TOTALACRES_1",
                ownerField="LASTNAME",
                situsField="SITEADDRESS",
                zipField="SITE_ZIP",
                zoningField="ZONINGCODE",
                dorField="DIGCLASS",
                salePriceField="SALEPRICE",
                saleDateField="SALEDATE",
                marketValueField="CURR_VAL",
                mail1Field="ADDRESS1",
                mailCityField="CITY",
                mailStateField="STATE",
                mailZipField="ZIP",
                source="ga-bibb-parcelcama-2025",
            ),
            "layers": [
                _layer(
                    url="https://services2.arcgis.com/zPFLSOZ5HzUzzTQb/arcgis/rest/services/ZoningDistrictsNew/FeatureServer/0/query",
                    where="1=1",
                    field="ZONECLASS",
                    target="zoning",
                    how="spatial",
                    mode="override",
                ),
                _layer(
                    url="https://services2.arcgis.com/zPFLSOZ5HzUzzTQb/arcgis/rest/services/MATS_Future_LandUse_2050/FeatureServer/0/query",
                    where="1=1",
                    field="FLU2050",
                    target="flu",
                    how="spatial",
                    mode="override",
                ),
            ],
            "gaps": [
                "Bibb County, Georgia (FIPS 13021) is consolidated Macon-Bibb. ParcelCAMA_Current_2025. TOTALACRES_1 5–150 inclusive. Not Bibb County, Alabama, and not Macon County, Georgia.",
                "City of Macon and Payne City dissolved in 2014. There is no separate city parcel layer.",
                "Zoning is ZoningDistrictsNew ZONECLASS. Parcel ZONINGCODE remains only where the polygon misses.",
                "Future land use is MATS_Future_LandUse_2050. Certify against the adopted comprehensive plan.",
                "No assessed value on this WinGAP extract. Sale prices of 0, 1, and 100 are dropped as nominal. Only the latest sale is on the polygon.",
                "gis.maconbibb.us was down on the research pass and was not used.",
                STATE_AADT,
                NO_OZ,
            ],
        },
        "13059": {
            "fips": "13059",
            "source": "ga-clarke-acc-parcels",
            "box": clarke_box,
            "reportUrl": QPUBLIC.format(app="ClarkeCountyGA"),
            "nominalSales": set(),
            "parcel": _parcel(
                url="https://enigma.accgov.com/server/rest/services/ACC_Parcels/FeatureServer/0/query",
                where="ACRES>=5 AND ACRES<=150",
                outFields=["PARCEL_NO", "OWNER_NAME", "PAR_ADD", "ACRES", "OWNER_ADD", "CITY", "STATE", "ZIP"],
                idField="PARCEL_NO",
                acresField="ACRES",
                ownerField="OWNER_NAME",
                situsField="PAR_ADD",
                mail1Field="OWNER_ADD",
                mailCityField="CITY",
                mailStateField="STATE",
                mailZipField="ZIP",
                source="ga-clarke-acc-parcels",
            ),
            "layers": [
                _layer(
                    url="https://enigma.accgov.com/server/rest/services/PlanningViewer2025/FeatureServer/14/query",
                    where="1=1",
                    idField="PARCEL_NO",
                    fields={"CurrentZn": "zoning"},
                    how="attribute",
                    mode="override",
                ),
                _layer(
                    url="https://enigma.accgov.com/server/rest/services/PlanningViewer2025/FeatureServer/41/query",
                    where="1=1",
                    idField="PARCEL_NO",
                    fields={"Updated_FL": "flu"},
                    how="attribute",
                    mode="override",
                ),
                _layer(
                    url="https://enigma.accgov.com/server/rest/services/Parcel_Sales_2018/MapServer/1/query",
                    where="1=1",
                    idField="PARCEL_NO",
                    fields={"NET_SP": "salePrice", "SALEDATE": "saleDate"},
                    how="attribute",
                    mode="fill",
                ),
                _layer(
                    url="https://enigma.accgov.com/server/rest/services/Winterville_Boundary/FeatureServer/0/query",
                    where="1=1",
                    field="NAME",
                    how="spatial",
                    mode="clear",
                    names=["winterville"],
                    jurisdiction="Winterville",
                ),
                _layer(
                    url="https://enigma.accgov.com/server/rest/services/Bogart_Boundary/FeatureServer/0/query",
                    where="1=1",
                    field="NAME",
                    how="spatial",
                    mode="clear",
                    names=["bogart"],
                    jurisdiction="Bogart",
                ),
            ],
            "gaps": [
                "Clarke County, Georgia (FIPS 13059, Athens-Clarke). ACC_Parcels on enigma.accgov.com. ACRES 5–150 inclusive. Not Clarke County, Virginia or Alabama, and not Athens, Ohio or Texas.",
                "Zoning is PlanningViewer2025/14 CurrentZn. Future land use is PlanningViewer2025/41 Updated_FL.",
                "Winterville and Bogart keep their own zoning. ACC CurrentZn and FLU are cleared inside those city limits and are not treated as the city codes.",
                "No market or assessed value on the public parcel REST. qPublic App=ClarkeCountyGA (AppID 630) is the tax record.",
                "Parcel_Sales_2018 is calendar year 2018 only. Later sales are not on a public year layer.",
                NO_AADT,
                NO_OZ,
            ],
        },
        "45013": {
            "fips": "45013",
            "source": "sc-beaufort-energov-parcels",
            "box": beaufort_box,
            "nominalSales": set(),
            "parcel": _parcel(
                url="https://gis.beaufortcountysc.gov/server/rest/services/EnerGov/MapServer/1/query",
                where="CAST(GisFile_Acres AS FLOAT)>=5 AND CAST(GisFile_Acres AS FLOAT)<=150",
                outFields=[
                    "GisFile_PIN",
                    "GisFile_Owner1",
                    "GisFile_SitusAddre",
                    "GisFile_MailingAdd",
                    "GisFile_City",
                    "GisFile_State",
                    "GisFile_ZIP",
                    "GisFile_Acres",
                    "GisFile_ClassCode",
                    "GisFile_SalePrice",
                    "GisFile_SaleDate",
                    "GisFile_Appraised",
                    "GisFile_Assessed",
                    "GisFile_Taxable",
                ],
                idField="GisFile_PIN",
                acresField="GisFile_Acres",
                ownerField="GisFile_Owner1",
                situsField="GisFile_SitusAddre",
                dorField="GisFile_ClassCode",
                salePriceField="GisFile_SalePrice",
                saleDateField="GisFile_SaleDate",
                marketValueField="GisFile_Appraised",
                assessedField="GisFile_Assessed",
                taxableField="GisFile_Taxable",
                mail1Field="GisFile_MailingAdd",
                mailCityField="GisFile_City",
                mailStateField="GisFile_State",
                mailZipField="GisFile_ZIP",
                source="sc-beaufort-energov-parcels",
            ),
            "layers": [
                _layer(
                    url="https://gis.beaufortcountysc.gov/server/rest/services/BC_FLU/MapServer/0/query",
                    where="1=1",
                    idField="PIN_",
                    fields={"FutureLandUse": "flu"},
                    how="attribute",
                    mode="fill",
                ),
                _layer(
                    url="https://gis.beaufortcountysc.gov/server/rest/services/Zoning/MapServer/9/query",
                    where="1=1",
                    field="FBCode",
                    target="zoning",
                    how="spatial",
                    mode="fill",
                ),
                _layer(
                    url="https://maps.hiltonheadislandsc.gov/server/rest/services/Energov/EnergovLayers/MapServer/7/query",
                    where="1=1",
                    field="NEW_ZONE",
                    target="zoning",
                    how="spatial",
                    mode="override",
                    jurisdiction="Town of Hilton Head Island",
                ),
                _layer(
                    url="https://gis.beaufortcountysc.gov/server/rest/services/Hosted/AddressParcels/FeatureServer/1/query",
                    where="jurisdiction='Bluffton'",
                    idField="pin_",
                    fields={"zoning": "zoning", "flu": "flu"},
                    how="attribute",
                    mode="override",
                    jurisdiction="Town of Bluffton",
                ),
            ],
            "gaps": [
                "Beaufort County, South Carolina (FIPS 45013). EnerGov/MapServer/1. GisFile_Acres is text and is cast for the 5–150 band. The legacy Parcels/LiveParcels service was 404 and was not used.",
                "County zoning is Zoning/MapServer/9 FBCode where the centroid falls in that polygon. It is the unincorporated Community Development Code.",
                "Town of Hilton Head Island zoning is EnergovLayers/7 NEW_ZONE and replaces the county code inside the town.",
                "Town of Bluffton zoning and future land use come from Hosted/AddressParcels where jurisdiction is Bluffton. That layer is southern Beaufort only and is not the county parcel source.",
                "City of Beaufort and Town of Port Royal have no public zoning FeatureServer on this pass. County CDC codes are not invented for them. Where the county polygon does not cover them, zoning stays empty.",
                "Future land use is BC_FLU FutureLandUse joined on PIN. Hilton Head Landuse___Current is an existing-use inventory and was not stored as future land use.",
                "Last sale only. No multi-sale table.",
                STATE_AADT,
                NO_OZ,
            ],
        },
        "28121": _ms_cama(
            "28121",
            "ms-rankin-cmpdd-parcels",
            "https://gis.cmpdd.org/server/rest/services/Hosted/Rankin_County_Feature_Layer/FeatureServer/8/query",
            jackson_box,
            "https://www.deltacomputersystems.com/ms/ms61/plinkquerym.html",
            [
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Rankin_County_Feature_Layer/FeatureServer/16/query",
                    where="1=1",
                    idField="parcel_id",
                    altIdField="ppin_1",
                    fields={"zoning2025": "zoning"},
                    how="attribute",
                    mode="fill",
                ),
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Rankin_County_Feature_Layer/FeatureServer/32/query",
                    where="1=1",
                    idField="parcel_id",
                    altIdField="ppin",
                    fields={"fulu2025": "flu"},
                    how="attribute",
                    mode="fill",
                ),
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Brandon_Zoning_and_Land_Use_2025/FeatureServer/9/query",
                    where="1=1",
                    idField="parcel_id",
                    altIdField="ppin",
                    fields={"zoning2025": "zoning"},
                    how="attribute",
                    mode="override",
                    jurisdiction="Brandon",
                ),
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Brandon_Zoning_and_Land_Use_2025/FeatureServer/10/query",
                    where="1=1",
                    idField="parcel_id",
                    altIdField="ppin",
                    fields={"fulu2025": "flu"},
                    how="attribute",
                    mode="override",
                ),
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Flowood_Feature_Layer/FeatureServer/7/query",
                    where="1=1",
                    idField="parcel_id",
                    altIdField="ppin",
                    fields={"zone": "zoning"},
                    how="attribute",
                    mode="override",
                    jurisdiction="Flowood",
                ),
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Pearl_FULU_2026/FeatureServer/5/query",
                    where="1=1",
                    idField="parcel_id",
                    altIdField="ppin",
                    fields={"fulu2026": "flu"},
                    how="attribute",
                    mode="override",
                    jurisdiction="Pearl",
                ),
            ],
            [
                "Rankin County, Mississippi (FIPS 28121). CMPDD Hosted Rankin_County_Feature_Layer/8 on gis.cmpdd.org. arcacres 5–150 inclusive.",
                "County zoning is FeatureServer/16 zoning2025. County future land use is FeatureServer/32 fulu2025.",
                "Brandon zoning and future land use replace the county values on a parcel-id match. Flowood zoning (December 2025) replaces the county code. Flowood draft land use was not joined.",
                "Pearl has future land use for 2026 and no city zoning layer. County zoning stays. Pearl future land use replaces the county future land use on a match.",
                "Ridgeland has no verified public zoning REST on this pass. No Ridgeland code was invented.",
                "No sale price on this layer. deed_date is the deed date, not a qualified sale price.",
                STATE_AADT,
                NO_OZ,
            ],
        ),
        "28089": _ms_cama(
            "28089",
            "ms-madison-cmpdd-parcels",
            "https://gis.cmpdd.org/server/rest/services/Hosted/Madison_County_Map/FeatureServer/36/query",
            jackson_box,
            "https://www.madison-co.com/elected-offices/tax-assessor/real-property-search",
            [
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Madison_County_Map/FeatureServer/27/query",
                    where="1=1",
                    idField="parcel_id",
                    altIdField="ppin",
                    fields={"zone_2025": "zoning"},
                    how="attribute",
                    mode="fill",
                ),
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Madison_County_Map/FeatureServer/33/query",
                    where="1=1",
                    idField="parcel_id_",
                    fields={"fulu": "flu"},
                    how="attribute",
                    mode="fill",
                ),
            ],
            [
                "Madison County, Mississippi (FIPS 28089). CMPDD Madison_County_Map/36 on gis.cmpdd.org. Not Madison County, Tennessee.",
                "Zoning is FeatureServer/27 zone_2025. Future land use is FeatureServer/33 fulu.",
                "Gluckstadt zoning is a December 2021 layer and was not fully field-mapped. It was not joined. County zone_2025 remains inside Gluckstadt.",
                "City of Madison publishes existing and future land use in a viewer and no zoning layer on this pass. No city zoning was invented.",
                "Ridgeland zoning was not found as public REST.",
                STATE_AADT,
                NO_OZ,
            ],
            acres="arcacres",
            owner="name",
            mail1="address_1",
            street_no="street_number",
            street="street_name",
            market="true_total_value",
            assessed="assessed_total_value",
            extra_fields=["assessed_total_value"],
        ),
        "28049": {
            "fips": "28049",
            "source": "ms-hinds-maris-august-2024",
            "box": jackson_box,
            "nominalSales": set(),
            "parcel": _parcel(
                url="https://gis.mississippi.edu/server/rest/services/Cadastral/MS_Parcels_August_2024/MapServer/1/query",
                where="STCNTYFIPS='28049' AND GISACRES>=5 AND GISACRES<=150",
                outFields=["PARNO", "OWNNAME", "SITEADD", "SCITY", "GISACRES", "TOTVAL", "LANDVAL"],
                idField="PARNO",
                acresField="GISACRES",
                ownerField="OWNNAME",
                situsField="SITEADD",
                cityField="SCITY",
                marketValueField="TOTVAL",
                source="ms-hinds-maris-august-2024",
            ),
            "layers": [
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/City_of_Jackson_Feature_Layer/FeatureServer/21/query",
                    where="zoneclass<>' ' AND zoneclass<>''",
                    idField="dpin",
                    altIdField="parcel",
                    fields={"zoneclass": "zoning"},
                    how="attribute",
                    mode="override",
                    jurisdiction="City of Jackson",
                ),
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Clinton_Feature_Layer/FeatureServer/32/query",
                    where="zoning2017<>' ' AND zoning2017<>''",
                    idField="parcel",
                    fields={"zoning2017": "zoning"},
                    how="attribute",
                    mode="override",
                    jurisdiction="Clinton",
                ),
            ],
            "gaps": [
                "Hinds County, Mississippi (FIPS 28049). MARIS MS_Parcels_August_2024 West filtered by STCNTYFIPS='28049'. GISACRES 5–150 inclusive. CNTYNAME and unpadded CNTYFIPS filters return nothing and were not used.",
                "Hinds has no county zoning or future land use REST. Unincorporated parcels stay unzoned. No code was invented for them.",
                "City of Jackson zoning is CMPDD City_of_Jackson_Feature_Layer/21 zoneclass, joined on dpin = PARNO. Existing land use exlu2019 is not future land use and was not stored as flu.",
                "Clinton zoning is Clinton_Feature_Layer/32 zoning2017. Clinton land use plan fields were not mapped on the card and were not joined.",
                "Byram zoning was not found as public REST.",
                "MARIS mail and deed fields are empty for Hinds. Owner, situs, and total value come from the state fabric. Assessed value stays empty. The landroll HTML search is the tax record.",
                STATE_AADT,
                NO_OZ,
            ],
        },
        "28029": _ms_mdeq(
            "28029",
            "ms-copiah-cmpdd-parcels",
            "https://gis.cmpdd.org/server/rest/services/Hosted/Copiah_County_Feature_Layer/FeatureServer/3/query",
            jackson_box,
            "https://cmpdd.org/maps/",
            [],
            [
                "Copiah County, Mississippi (FIPS 28029). CMPDD Copiah_County_Feature_Layer/3 on gis.cmpdd.org. gisacres 5–150 inclusive.",
                "No county zoning or future land use REST. Both stay empty.",
                NO_AADT,
                NO_OZ,
            ],
        ),
        "28127": _ms_mdeq(
            "28127",
            "ms-simpson-cmpdd-parcels",
            "https://gis.cmpdd.org/server/rest/services/Hosted/Simpson_County_Feature_Layer/FeatureServer/3/query",
            jackson_box,
            "https://cmpdd.org/maps/",
            [
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Simpson_County_Feature_Layer/FeatureServer/37/query",
                    where="1=1",
                    idField="parcel_id",
                    altIdField="ppin",
                    fields={"fulu_2023": "flu"},
                    how="attribute",
                    mode="fill",
                ),
            ],
            [
                "Simpson County, Mississippi (FIPS 28127). CMPDD Simpson_County_Feature_Layer/3. gisacres 5–150 inclusive.",
                "Future land use is Simpson_FULU_2023 fulu_2023.",
                "County zoning is a gap. Magee, Mendenhall, and D'Lo layers are 2008–2010 and were not joined as current zoning.",
                NO_AADT,
                NO_OZ,
            ],
        ),
        "28149": _ms_mdeq(
            "28149",
            "ms-warren-cmpdd-parcels",
            "https://gis.cmpdd.org/server/rest/services/Hosted/Warren_County_Feature_Layer/FeatureServer/4/query",
            jackson_box,
            "https://cmpdd.org/maps/",
            [
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Warren_County_Feature_Layer/FeatureServer/7/query",
                    where="1=1",
                    field="fulu",
                    target="flu",
                    how="spatial",
                    mode="fill",
                    legend={
                        "0": "Agricultural/Vacant",
                        "1": "Estate Residential",
                        "2": "Low Density Residential",
                        "3": "Medium Density Residential",
                        "4": "High Density Residential",
                        "5": "Manufactured Homes",
                        "6": "Low Intensity Commercial",
                        "7": "General Commercial",
                        "8": "High Intensity Commercial",
                        "9": "Light Industrial",
                        "10": "Heavy Industrial",
                        "11": "Parks/Open Space",
                        "12": "Public/Semi-Public",
                        "13": "Water Bodies",
                        "16": "Mineral Extraction/Surface Mining",
                    },
                ),
            ],
            [
                "Warren County, Mississippi (FIPS 28149). CMPDD Warren_County_Feature_Layer/4. gisacres 5–150 inclusive.",
                "Future land use is FeatureServer/7 fulu, joined by centroid. Integer codes are the published renderer labels (0 is Agricultural/Vacant). County zoning is a gap and the parcel zoning attribute was not copied.",
                NO_AADT,
                NO_OZ,
            ],
        ),
        "28163": _ms_mdeq(
            "28163",
            "ms-yazoo-cmpdd-2026-parcels",
            "https://gis.cmpdd.org/server/rest/services/Hosted/Yazoo_County_2026_layers/FeatureServer/2/query",
            jackson_box,
            "https://cmpdd.org/maps/",
            [
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Yazoo_County_2026_layers/FeatureServer/18/query",
                    where="1=1",
                    idField="altparno",
                    altIdField="ppin",
                    fields={"zoning_2026": "zoning"},
                    how="attribute",
                    mode="fill",
                ),
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Yazoo_County_2026_layers/FeatureServer/5/query",
                    where="1=1",
                    idField="ppin",
                    fields={"fulu_2026": "flu"},
                    how="attribute",
                    mode="fill",
                ),
                _layer(
                    url="https://gis.cmpdd.org/server/rest/services/Hosted/Yazoo_City_Feature_Layer/FeatureServer/16/query",
                    where="1=1",
                    idField="parcel_id",
                    altIdField="ppin",
                    fields={"zoning2019": "zoning", "salepric": "salePrice", "fulu2019": "flu"},
                    how="attribute",
                    mode="override",
                    jurisdiction="Yazoo City",
                ),
            ],
            [
                "Yazoo County, Mississippi (FIPS 28163). CMPDD Yazoo_County_2026_layers/2. gisacres 5–150 inclusive.",
                "County zoning is FeatureServer/18 zoning_2026. County future land use is FeatureServer/5 fulu_2026.",
                "Yazoo City zoning, future land use, and sale price replace the county values on a parcel-id match. salepric is the municipal sale field.",
                NO_AADT,
                NO_OZ,
            ],
        ),
    }


def _ms_cama(
    fips: str,
    source: str,
    url: str,
    box: tuple[float, float, float, float],
    appraiser: str,
    layers: list[dict],
    gaps: list[str],
    *,
    acres: str = "arcacres",
    owner: str = "ownername",
    mail1: str = "address1",
    street_no: str = "street_num",
    street: str = "street",
    market: str = "totalvalue",
    assessed: str | None = None,
    extra_fields: list[str] | None = None,
) -> dict:
    fields = [
        "parcel_id",
        "ppin",
        owner,
        mail1,
        "city",
        "state",
        "zip",
        street_no,
        street,
        acres,
        market,
        "deed_date",
    ]
    if assessed:
        fields.append(assessed)
    for name in extra_fields or []:
        if name not in fields:
            fields.append(name)
    parcel = _parcel(
        url=url,
        where=f"{acres}>=5 AND {acres}<=150",
        outFields=fields,
        idField="parcel_id",
        altIdField="ppin",
        acresField=acres,
        ownerField=owner,
        situsParts=[street_no, street],
        saleDateField="deed_date",
        marketValueField=market,
        mail1Field=mail1,
        mailCityField="city",
        mailStateField="state",
        mailZipField="zip",
        source=source,
    )
    if assessed:
        parcel["assessedField"] = assessed
    return {
        "fips": fips,
        "source": source,
        "box": box,
        "appraiserUrl": appraiser,
        "nominalSales": set(),
        "parcel": parcel,
        "layers": layers,
        "gaps": gaps,
    }


def _ms_mdeq(
    fips: str,
    source: str,
    url: str,
    box: tuple[float, float, float, float],
    appraiser: str,
    layers: list[dict],
    gaps: list[str],
) -> dict:
    return {
        "fips": fips,
        "source": source,
        "box": box,
        "appraiserUrl": appraiser,
        "nominalSales": set(),
        "parcel": _parcel(
            url=url,
            where="gisacres>=5 AND gisacres<=150",
            outFields=[
                "altparno",
                "ppin",
                "ownname",
                "mailadd1",
                "mcity1",
                "mstate1",
                "mzip1",
                "siteadd",
                "scity",
                "gisacres",
                "totval",
                "deeddate",
            ],
            idField="altparno",
            altIdField="ppin",
            acresField="gisacres",
            ownerField="ownname",
            situsField="siteadd",
            cityField="scity",
            saleDateField="deeddate",
            marketValueField="totval",
            mail1Field="mailadd1",
            mailCityField="mcity1",
            mailStateField="mstate1",
            mailZipField="mzip1",
            source=source,
        ),
        "layers": layers,
        "gaps": gaps,
    }


def metro_spec(fips: str) -> dict:
    spec = specs()[fips]
    return {
        "kind": "new-metro",
        "source": spec["source"],
        "url": spec["parcel"]["url"],
        "coverage": "complete-gte-5ac",
        "fips": fips,
    }


def _bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    coords: list[list[float]] = []

    def walk(node: Any) -> None:
        if isinstance(node, (list, tuple)) and node and isinstance(node[0], (int, float)):
            coords.append([float(node[0]), float(node[1])])
            return
        if isinstance(node, list):
            for item in node:
                walk(item)

    walk(geometry.get("coordinates"))
    if not coords:
        return None
    return (
        min(point[0] for point in coords),
        min(point[1] for point in coords),
        max(point[0] for point in coords),
        max(point[1] for point in coords),
    )


class PolyGrid:
    def __init__(self, cell: float = 0.05) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list] = defaultdict(list)

    def add(self, geometry: dict, payload: str) -> None:
        box = _bbox(geometry)
        if not box:
            return
        item = (box, geometry, payload)
        ix0 = math.floor(box[0] / self.cell)
        ix1 = math.floor(box[2] / self.cell)
        iy0 = math.floor(box[1] / self.cell)
        iy1 = math.floor(box[3] / self.cell)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(item)

    def hits(self, lon: float, lat: float) -> list[str]:
        ix = math.floor(lon / self.cell)
        iy = math.floor(lat / self.cell)
        found: list[str] = []
        for box, geometry, payload in self.buckets.get((ix, iy), []):
            if lon < box[0] or lon > box[2] or lat < box[1] or lat > box[3]:
                continue
            if payload in found:
                continue
            if contains_point(geometry, lon, lat):
                found.append(payload)
        return found


def fetch_table(url: str, where: str, fields: list[str], *, geometry: bool) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    page = 800 if geometry else 2000
    while True:
        params = {
            "where": where,
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "resultOffset": str(offset),
            "resultRecordCount": str(page),
            "f": "json",
        }
        if geometry:
            params["outSR"] = "4326"
        data = seed.fetch_json(url, params, timeout=180)
        if data.get("error"):
            message = str(data["error"])
            if offset == 0 and "Pagination" in message:
                ids = seed.fetch_object_ids(url, where)
                return seed.fetch_by_ids(url, ids, fields, batch=60 if geometry else 200, return_geometry=geometry)
            raise RuntimeError(message[:300])
        batch = data.get("features") or []
        rows.extend(batch)
        if not batch or (not data.get("exceededTransferLimit") and len(batch) < page):
            break
        offset += len(batch)
        print(f"    table {len(rows)}", flush=True)
    return rows


def _keys_for(feature: dict) -> list[str]:
    props = feature["properties"]
    keys: list[str] = []
    for value in (props.get("parcelId"), props.get("_altParcelId")):
        text = seed.clean(value)
        compact = norm_id(value)
        for key in (text, compact):
            if key and key not in keys:
                keys.append(key)
    return keys


def _index_features(features: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = defaultdict(list)
    for feature in features:
        for key in _keys_for(feature):
            index[key].append(feature)
    return index


def _put(feature: dict, target: str, value: str | None, mode: str) -> bool:
    if not value:
        return False
    props = feature["properties"]
    if target == "zoning":
        if mode == "fill" and props.get("zoningCode"):
            return False
        props["zoningCode"] = value
        return True
    if target == "flu":
        if mode == "fill" and props.get("flu"):
            return False
        props["flu"] = value
        return True
    if target == "jurisdiction":
        if mode == "fill" and props.get("jurisdictionCode"):
            return False
        props["jurisdictionCode"] = value
        return True
    if target == "salePrice":
        price = drop_nominal_sale(seed.num(value), set())
        if price is None:
            return False
        if mode == "fill" and props["lastSale"].get("price"):
            return False
        props["lastSale"]["price"] = price
        return True
    if target == "saleDate":
        sold = seed.epoch_to_iso(value) or seed.text_date(value)
        if not sold:
            return False
        if mode == "fill" and props["lastSale"].get("date"):
            return False
        props["lastSale"]["date"] = sold
        return True
    return False


def _remember(table: dict[str, dict[str, list[str]]], key: str, target: str, value: Any) -> None:
    text = seed.clean(value)
    if not key or not text:
        return
    bucket = table.setdefault(key, {}).setdefault(target, [])
    if text not in bucket:
        bucket.append(text)


def apply_attribute(features: list[dict], layer: dict) -> int:
    fields = list(layer["fields"])
    id_field = layer["idField"]
    alt = layer.get("altIdField")
    out = [id_field, *fields]
    if alt and alt not in out:
        out.append(alt)
    rows = fetch_table(layer["url"], layer["where"], out, geometry=False)
    table: dict[str, dict[str, list[str]]] = {}
    for row in rows:
        attrs = row.get("attributes") or {}
        for raw_key in (attrs.get(id_field), attrs.get(alt) if alt else None):
            text = seed.clean(raw_key)
            compact = norm_id(raw_key)
            for key in {text, compact}:
                if not key:
                    continue
                for source, target in layer["fields"].items():
                    _remember(table, key, target, attrs.get(source))
    index = _index_features(features)
    changed = 0
    seen: set[int] = set()
    mode = layer["mode"]
    for key, payload in table.items():
        for feature in index.get(key, []):
            marker = id(feature)
            if marker in seen:
                continue
            wrote = False
            for target, codes in payload.items():
                value = codes[-1] if target in {"salePrice", "saleDate"} else combine_codes(codes)
                if _put(feature, target, value, mode):
                    wrote = True
            if wrote and layer.get("jurisdiction"):
                _put(feature, "jurisdiction", layer["jurisdiction"], "override" if mode == "override" else "fill")
            if wrote:
                seen.add(marker)
                changed += 1
    print(f"    attribute {layer['url'].split('/services/')[-1][:70]} -> {changed}", flush=True)
    return changed


def apply_spatial(features: list[dict], layer: dict) -> int:
    rows = fetch_table(layer["url"], layer["where"], [layer["field"]], geometry=True)
    grid = PolyGrid()
    for row in rows:
        attrs = row.get("attributes") or {}
        code = seed.clean(attrs.get(layer["field"]))
        if not code:
            continue
        code = (layer.get("legend") or {}).get(code, code)
        if layer.get("names") and not any(name in code.lower() for name in layer["names"]):
            continue
        geometry = esri_rings_to_geojson((row.get("geometry") or {}).get("rings") or [])
        if geometry:
            grid.add(geometry, code)
    changed = 0
    mode = layer["mode"]
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        hits = grid.hits(lon, lat)
        if not hits:
            continue
        if mode == "clear":
            feature["properties"]["zoningCode"] = None
            feature["properties"]["flu"] = None
            feature["properties"]["jurisdictionCode"] = layer.get("jurisdiction") or hits[0]
            changed += 1
            continue
        target = layer["target"]
        if _put(feature, target, combine_codes(hits), mode):
            if layer.get("jurisdiction") and target == "zoning":
                _put(feature, "jurisdiction", layer["jurisdiction"], "override")
            changed += 1
        elif layer.get("jurisdiction") and target == "jurisdiction":
            pass
    print(f"    spatial {layer['field']} -> {changed}", flush=True)
    return changed


def clean_situs(features: list[dict]) -> None:
    for feature in features:
        situs = feature["properties"].get("situsAddress")
        if not situs:
            continue
        text = re.sub(r"^0+\s+", "", str(situs)).strip()
        if re.fullmatch(r"0+", text):
            text = ""
        feature["properties"]["situsAddress"] = text or None


def download_new_metro(county: dict, markets: list[str], spec: dict) -> dict:
    install_gis_ssl()
    full = specs()[county["fips"]]
    if county["fips"] != full["fips"]:
        raise RuntimeError(f"New metro ingest expected {full['fips']}, got {county['fips']}")
    parcel = full["parcel"]
    print(f"Pulling {county['name']} {county['state']} ({county['fips']}) via {full['source']}", flush=True)
    expected = seed.count_where(parcel["url"], parcel["where"])
    print(f"  source rows {expected}", flush=True)
    ids = seed.fetch_object_ids(parcel["url"], parcel["where"])
    raw = seed.fetch_by_ids(parcel["url"], ids, parcel["outFields"])
    features, dropped = seed.normalize_rows(raw, county, markets, parcel)
    kept: list[dict] = []
    outside = 0
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        if in_box(lon, lat, full["box"]):
            kept.append(feature)
        else:
            outside += 1
    features = kept
    if outside:
        print(f"  dropped {outside} outside {county['name']} box", flush=True)
    if not features:
        return seed.county_row(
            county,
            markets,
            feature_count=0,
            coverage="gap",
            partition="none",
            path=None,
            lookup=None,
            source=full["source"],
            query_url=parcel["url"],
            gaps=[
                f"Source count was {expected} but none survived the 5–150 acre band and the {county['name']} geography check.",
                *full["gaps"],
            ],
            source_count=expected,
            dropped=dropped + outside,
        )
    clean_situs(features)
    nominal = full.get("nominalSales") or set()
    for feature in features:
        sale = feature["properties"]["lastSale"]
        sale["price"] = drop_nominal_sale(sale.get("price"), nominal)
        feature["properties"]["opportunityZone"] = None
        feature["properties"]["oz2Eligibility"] = None
        if full.get("reportUrl"):
            feature["properties"]["appraiserUrl"] = full["reportUrl"] + urllib.parse.quote(feature["properties"]["parcelId"])
        elif full.get("appraiserUrl"):
            feature["properties"]["appraiserUrl"] = full["appraiserUrl"]
    for layer in full["layers"]:
        if layer["how"] == "attribute":
            apply_attribute(features, layer)
        else:
            apply_spatial(features, layer)
    for feature in features:
        feature["properties"].pop("_altParcelId", None)
        if not seed.in_band(feature["properties"].get("acreage")):
            raise RuntimeError(f"{county['fips']} left the 5–150 acre band")
    zoning_joined = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_joined = sum(1 for feature in features if feature["properties"].get("flu"))
    sale_prices = sum(1 for feature in features if feature["properties"]["lastSale"].get("price"))
    by_jurisdiction: dict[str, int] = defaultdict(int)
    for feature in features:
        name = feature["properties"].get("jurisdictionCode")
        if name:
            by_jurisdiction[name] += 1
    path, lookup, tiles = seed.write_tiles(county, features)
    print(f"  kept {len(features)} zoning {zoning_joined} flu {flu_joined}", flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=full["source"],
        query_url=parcel["url"],
        gaps=full["gaps"],
        source_count=expected,
        dropped=dropped + outside,
        tile_count=tiles,
        extra={
            "zoningJoinedCount": zoning_joined,
            "fluJoinedCount": flu_joined,
            "join": {
                "zoningJoined": zoning_joined,
                "fluJoined": flu_joined,
                "salePriceNonNull": sale_prices,
                "byJurisdiction": dict(by_jurisdiction),
                "outsideBox": outside,
            },
        },
    )
