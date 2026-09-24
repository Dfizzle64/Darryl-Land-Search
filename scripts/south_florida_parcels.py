#!/usr/bin/env python3
"""Wave 0 South Florida parcel extract.

Miami-Dade 12086, Monroe 12087, Broward 12011 (partial), and Palm Beach 12099.
Acreage is 5.0–150.0 inclusive. Utilities, school grades, base flood
elevations, and Opportunity Zone status are not joined.

Broward BCPA MapServer/16 is folio and geometry. The FDOR CO_NO=16 join was
not applied. BMSD zoning is unincorporated only.
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

FIPS = ("12086", "12087", "12011", "12099")

# Generous envelopes. They reject namesake counties, not shoreline slivers.
COUNTY_BBOX = {
    "12086": (-81.05, 25.10, -80.00, 26.05),
    "12087": (-83.20, 24.35, -80.10, 25.90),
    "12011": (-81.00, 25.90, -80.00, 26.55),
    "12099": (-81.00, 26.25, -79.90, 27.10),
}

# Hosts whose public cards document a broken or fragile TLS chain.
TLS_FALLBACK_HOSTS = {
    "mcgis4.monroecounty-fl.gov",
    "maps.co.palm-beach.fl.us",
}

REJECTED_URLS = (
    "maps.monroecounty.gov",
    "gis.bcpa.net",
    "mdc_parcels",
    "MD_LandInformation/MapServer/24",
    "CAD911",
    "pbcgov.org/papa",
    "opendata.pbcgov.org",
    "PZB/FLU_ATLAS",
    "PZB/LU_APP",
    "BMSDParcelAddress",
    "AAA_GIS",
)

BLANK_CODES = {
    "",
    "N/A",
    "NA",
    "NONE",
    "NULL",
    "UNKNOWN",
    "TBD",
    "WATER",
    "UNINCORPORATED",
    "MIAMI-DADE",
    "MIAMI-DADE COUNTY",
    "COUNTY",
}

MIAMI_PARCELS = "https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/26/query"
MIAMI_ZONE_COUNTY = "https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/18/query"
MIAMI_ZONE_CITY = "https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/19/query"
MIAMI_FLU = "https://gisweb.miamidade.gov/arcgis/rest/services/LandManagement/MD_CDMP/MapServer/7/query"
MIAMI_PA = "https://apps.miamidadepa.gov/ComparableSales/#/?folio={FOLIO}"
MIAMI_PA_API = (
    "https://apps.miamidadepa.gov/PApublicServiceProxy/PaServicesProxy.ashx"
    "?Operation=GetPropertySearchByFolio&clientAppName=PropertySearch&folioNumber={FOLIO}"
)

MONROE_PARCELS = "https://mcgis4.monroecounty-fl.gov/public/rest/services/Parcels/MapServer/0/query"
MONROE_ZONING = "https://mcgis4.monroecounty-fl.gov/public/rest/services/APO_GIS/MapServer/19/query"
MONROE_FLU = "https://mcgis4.monroecounty-fl.gov/public/rest/services/APO_GIS/MapServer/20/query"
MONROE_PA = (
    "https://qpublic.schneidercorp.com/Application.aspx?AppID=605&LayerID=9946"
    "&PageTypeID=4&PageID=7635&KeyValue={RECHAR}"
)

BROWARD_PARCELS = "https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN26/MapServer/16/query"
BROWARD_FDOR = (
    "https://services9.arcgis.com/Gh9awoU677aKree0/ArcGIS/rest/services/"
    "Florida_Statewide_Cadastral/FeatureServer/0/query"
)
BROWARD_BMSD_ZONING = (
    "https://services.arcgis.com/JMAJrTsHNLrSsWf5/ArcGIS/rest/services/"
    "Broward_Municipal_Service_District_Zoning/FeatureServer/2/query"
)
BROWARD_MOSAIC = "https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN26/MapServer/9/query"
BROWARD_FLU = "https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN26/MapServer/10/query"
BROWARD_PA = "https://bcpa.net/RecInfo.asp?URL_Folio={FOLIO}"

PALM_PARCELS = "https://gis.pbcgov.org/arcgis/rest/services/Parcels/PARCEL_INFO/FeatureServer/4/query"
PALM_ZONING = "https://maps.co.palm-beach.fl.us/arcgis/rest/services/OpenData/Planning_Open_Data/MapServer/9/query"
PALM_FLU = "https://maps.co.palm-beach.fl.us/arcgis/rest/services/OpenData/open_data_v2/FeatureServer/6/query"
PALM_PA = "https://pbcpao.gov/Property/Details?parcelId={PARID}"

SPECS: dict[str, dict] = {
    "12086": {
        "kind": "south-florida",
        "source": "fl-miami-dade-landinformation-26",
        "coverage": "complete-gte-5ac",
        "url": MIAMI_PARCELS,
        "layerId": 26,
        "status": "live",
        "appraiserSearchUrl": MIAMI_PA,
        "paApiTemplate": MIAMI_PA_API,
        "fieldMap": {
            "FOLIO": "parcelId",
            "TRUE_OWNER1": "ownerName",
            "TRUE_OWNER2": "ownerName2",
            "TRUE_OWNER3": "ownerName3",
            "TRUE_MAILING_ADDR1": "mailingAddress.street",
            "TRUE_SITE_ADDR": "situsAddress",
            "TRUE_SITE_CITY": "situsCity",
            "TOTAL_VAL_CUR": "tax.marketValue",
            "LAND_VAL_CUR": "tax.landValue",
            "BUILDING_VAL_CUR": "tax.improvementValue",
            "DOR_CODE_CUR": "dorCode",
            "LOT_SIZE": "lotSizeSqFt",
        },
        "gaps": [
            "Wave 0 is South Florida only. Miami-Dade parcels are MD_LandInformation MapServer/26. Acreage is LOT_SIZE square feet divided by 43560, 5.0–150.0 inclusive.",
            "PRIMARY_ZONE is a property-appraiser neighborhood code, not a zoning district. Zoning is Zone_Poly_U (unincorporated) or MunicipalZone. It is not copied from PRIMARY_ZONE.",
            "Last sale is not on the parcel layer. The property-appraiser folio API is the sales source and is not copied onto the row. Assessed and taxable value are richer on that API than TOTAL_VAL_CUR.",
            "Land and improvement amounts are published on the layer. This shelf stores market value from TOTAL_VAL_CUR. It does not invent a separate land or improvement column.",
            "GDSC mdc_parcels, MapServer/24 points, and CAD911/22 were not used.",
        ],
    },
    "12087": {
        "kind": "south-florida",
        "source": "fl-monroe-apo-parcels-0",
        "coverage": "complete-gte-5ac",
        "url": MONROE_PARCELS,
        "layerId": 0,
        "status": "live",
        "appraiserSearchUrl": MONROE_PA,
        "fieldMap": {
            "RECHAR": "parcelId",
            "NAME": "ownerName",
            "LOCATION": "situsAddress",
            "KEYNAME": "situsIsland",
            "SALE1": "lastSale.price",
            "M1": "lastSale.month",
            "Y1": "lastSale.year",
            "PJUST1": "tax.marketValue",
            "PASSD1": "tax.assessedValue",
            "PTAX1": "tax.taxableValue",
            "PC": "dorCode",
        },
        "gaps": [
            "Monroe parcels are mcgis4 Parcels MapServer/0. The server certificate does not verify with the default OpenSSL trust store, so ingest retries that host without certificate verification. qPublic HTML often returns Cloudflare 403 to bots. The record link is still the human URL.",
            "Acreage is the WGS84 polygon area. Shape.STArea() is rejected in SQL on this service. AREA1 is inconsistent for condos and is not the stored acreage.",
            "SALE1 can include bulk or condo package prices. PC is stored as dorCode. Its mapping to the Florida DOR use code is not confirmed.",
            "City zoning (Key West, Marathon, and the other municipalities) was not inventoried. County Land Use Districts and the FLUM are the joined layers.",
            "maps.monroecounty.gov Hosted Parcels_Public is Monroe County, New York, and was not used.",
        ],
    },
    "12011": {
        "kind": "south-florida",
        "source": "fl-broward-bcpa-jan26-16",
        "coverage": "partial",
        "url": BROWARD_PARCELS,
        "layerId": 16,
        "status": "partial",
        "appraiserSearchUrl": BROWARD_PA,
        "camaUrl": BROWARD_FDOR,
        "fieldMap": {"FOLIO": "parcelId"},
        "camaFieldMap": {
            "PARCEL_ID": "parcelId",
            "OWN_NAME": "ownerName",
            "PHY_ADDR1": "situsAddress",
            "JV": "tax.marketValue",
            "AV_SD": "tax.assessedValue",
            "TV_SD": "tax.taxableValue",
            "SALE_PRC1": "lastSale.price",
            "SALE_YR1": "lastSale.year",
            "DOR_UC": "dorCode",
        },
        "gaps": [
            "Partial. BCPA MapServer/16 (BCPA_EXTERNAL_JAN26) is folio and geometry only. Acreage is the polygon area, 5.0–150.0 inclusive. gis.bcpa.net does not resolve. The service name rotates yearly.",
            "Countywide CAMA is not on that layer. The FDOR CO_NO=16 join (PARCEL_ID=FOLIO) did not return from batched queries, so owner, sale, and value are not on these rows. BMSDParcelAddress is an unincorporated subset and is not the county roll.",
            "BMSD zoning covers unincorporated Broward only. The city zoning mosaic (MapServer/9) is partial: many ZONE_NAME values are blank, N/A, or WATER, and it is not a city ordinance. Authoritative city zoning was not invented.",
            "County land use (MapServer/10) stores numeric SLUC1 codes, not plain-language future-land-use labels. BCPA sales layers were not queried.",
        ],
    },
    "12099": {
        "kind": "south-florida",
        "source": "fl-palm-beach-parcel-info-4",
        "coverage": "partial",
        "url": PALM_PARCELS,
        "layerId": 4,
        "status": "live",
        "appraiserSearchUrl": PALM_PA,
        "fieldMap": {
            "PARID": "parcelId",
            "ACRES": "acreage",
            "OWNER_NAME1": "ownerName",
            "OWNER_NAME2": "ownerName2",
            "SITE_ADDR_STR": "situsAddress",
            "MUNICIPALITY": "situsCity",
            "PRICE": "lastSale.price",
            "SALE_DATE": "lastSale.date",
            "QUAL_CODE": "lastSale.qualified",
            "TOTAL_MARKET": "tax.marketValue",
            "ASSESSED_VAL": "tax.assessedValue",
            "TOTAL_TAXABLE": "tax.taxableValue",
            "PROPERTY_USE": "dorCode",
        },
        "gaps": [
            "Partial. PARCEL_INFO reports about 146,014 object ids with ACRES from 5.0 through 150.0. This extract kept the parcels that survived geometry normalize and parcel-id dedupe, not that full object-id count. PROPERTY_USE is text, not a numeric DOR code.",
            "Zoning is the unincorporated OpenData layer only. Municipal zoning is not on this card. West Palm Beach and Boca Raton city layers were not joined.",
            "Future land use is open_data_v2. maps.co.palm-beach.fl.us TLS is fragile from some clients. The gis.pbcgov.org OpenData mirror requires a token and was not used. opendata.pbcgov.org does not resolve.",
            "The legacy pbcgov.org/papa PropertyDetail URL redirects home and is not the record link.",
        ],
    },
}


def south_florida_spec(fips: str) -> dict:
    spec = SPECS[fips]
    return {
        "kind": spec["kind"],
        "source": spec["source"],
        "coverage": spec["coverage"],
        "url": spec["url"],
        "gaps": list(spec["gaps"]),
        "status": spec["status"],
    }


def in_band(acres: float | None) -> bool:
    return isinstance(acres, (int, float)) and MIN_ACRES <= float(acres) <= MAX_ACRES


def acres_from_sqft(value: Any) -> float | None:
    number = _num(value)
    if number is None or number <= 0:
        return None
    return number / SQFT_PER_ACRE


def in_county(fips: str, lon: float, lat: float) -> bool:
    west, south, east, north = COUNTY_BBOX[fips]
    return west <= lon <= east and south <= lat <= north


def usable_code(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    if text.upper() in BLANK_CODES:
        return None
    return text


def layer_home(query_url: str) -> str:
    if query_url.endswith("/query"):
        return query_url[: -len("/query")]
    return query_url


def gis_viewer_url(fips: str, jurisdiction: str | None, *, zoned: bool) -> str:
    """REST home of the zoning layer that won, or the county parcel service when zoning missed."""
    parcels = {
        "12086": layer_home(MIAMI_PARCELS),
        "12087": layer_home(MONROE_PARCELS),
        "12011": layer_home(BROWARD_PARCELS),
        "12099": layer_home(PALM_PARCELS),
    }[fips]
    if not zoned:
        return parcels
    if fips == "12086":
        return layer_home(MIAMI_ZONE_COUNTY if jurisdiction == "Unincorporated" else MIAMI_ZONE_CITY)
    if fips == "12087":
        return layer_home(MONROE_ZONING)
    if fips == "12011":
        return layer_home(BROWARD_BMSD_ZONING if jurisdiction == "Unincorporated" else BROWARD_MOSAIC)
    return layer_home(PALM_ZONING)


def appraiser_url(fips: str, parcel_id: str) -> str:
    token = urllib.parse.quote(parcel_id, safe="")
    if fips == "12086":
        folio = "".join(ch for ch in parcel_id if ch.isdigit()) or parcel_id
        return MIAMI_PA.replace("{FOLIO}", urllib.parse.quote(folio, safe=""))
    if fips == "12087":
        return MONROE_PA.replace("{RECHAR}", token)
    if fips == "12011":
        return BROWARD_PA.replace("{FOLIO}", token)
    if fips == "12099":
        return PALM_PA.replace("{PARID}", token)
    raise KeyError(fips)


def rejected_url(url: str) -> str | None:
    for needle in REJECTED_URLS:
        if needle in url:
            return needle
    return None


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


def _parcel_id(value: Any) -> str | None:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return _clean(value)


def _is_tls_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "certificate" in text or "ssl" in text or "tls" in text or "eof" in text


def _fetch_once(url: str, params: dict | None, timeout: int, insecure: bool) -> dict:
    full = url
    if params:
        full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": "darryl-land-search/south-florida"})
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


TLS_FALLBACK_USED: set[str] = set()


def _query(url: str, params: dict, timeout: int = 180) -> dict:
    data = fetch_json(url, params, timeout=timeout)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    return data


def count_where(url: str, where: str) -> int:
    data = _query(url, {"where": where, "returnCountOnly": "true", "f": "json"})
    count = data.get("count")
    if not isinstance(count, int):
        raise RuntimeError(f"No count from {url}")
    return count


def fetch_object_ids(url: str, where: str) -> list[int]:
    data = _query(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=240)
    return [int(i) for i in (data.get("objectIds") or [])]


def fetch_by_ids(
    url: str,
    ids: list[int],
    out_fields: list[str],
    *,
    geometry: bool,
    batch: int = 120,
) -> list[dict]:
    features: list[dict] = []
    params_base = {"outFields": ",".join(out_fields), "returnGeometry": "true" if geometry else "false", "f": "json"}
    if geometry:
        params_base["outSR"] = "4326"
    total = len(ids)
    start = 0
    while start < total:
        chunk = ids[start : start + batch]
        params = dict(params_base)
        params["objectIds"] = ",".join(str(i) for i in chunk)
        try:
            data = _query(url, params, timeout=180)
        except Exception as exc:
            if len(chunk) > 1:
                mid = max(1, len(chunk) // 2)
                features.extend(fetch_by_ids(url, chunk[:mid], out_fields, geometry=geometry, batch=mid))
                features.extend(fetch_by_ids(url, chunk[mid:], out_fields, geometry=geometry, batch=max(1, len(chunk) - mid)))
                start += len(chunk)
                continue
            print(f"    skip object {chunk[0]} ({exc})", flush=True)
            start += len(chunk)
            continue
        page = data.get("features") or []
        if len(page) < len(chunk) and len(chunk) > 1:
            print(f"    short page {len(page)}/{len(chunk)} {url.rsplit('/', 2)[-2]}", flush=True)
            mid = max(1, len(chunk) // 2)
            features.extend(fetch_by_ids(url, chunk[:mid], out_fields, geometry=geometry, batch=mid))
            features.extend(fetch_by_ids(url, chunk[mid:], out_fields, geometry=geometry, batch=max(1, len(chunk) - mid)))
            start += len(chunk)
            continue
        features.extend(page)
        start += len(chunk)
        if start == len(chunk) or start == total or start % 800 == 0:
            print(f"    {start}/{total} {url.rsplit('/', 2)[-2]}", flush=True)
        time.sleep(0.01)
    return features


def fetch_layer(url: str, where: str, out_fields: list[str], *, geometry: bool) -> list[dict]:
    ids = fetch_object_ids(url, where)
    if not ids:
        return []
    return fetch_by_ids(url, ids, out_fields, geometry=geometry)


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
    if kind == "Polygon":
        rings = coords
    elif kind == "MultiPolygon":
        rings = [ring for poly in coords for ring in poly]
    else:
        return None
    for ring in rings:
        for x, y in ring:
            xs.append(float(x))
            ys.append(float(y))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def index_polygons(raw: list[dict], code_field: str, label_field: str | None = None, extra: str | None = None) -> SpatialIndex:
    index = SpatialIndex()
    for item in raw:
        rings = (item.get("geometry") or {}).get("rings")
        geometry = esri_rings_to_geojson(rings) if rings else None
        if not geometry:
            continue
        attrs = item.get("attributes") or {}
        code = usable_code(attrs.get(code_field))
        if not code:
            continue
        feature = {
            "geometry": geometry,
            "code": code,
            "label": _clean(attrs.get(label_field)) if label_field else None,
            "extra": _clean(attrs.get(extra)) if extra else None,
        }
        index.add(feature)
    return index


def _seed():
    import seed_market_parcels as seed

    return seed


def _geometry_feature(seed: Any, item: dict) -> tuple[dict | None, float, tuple[float, float] | None]:
    geometry, acres = seed.rings_to_feature_geometry(item.get("geometry"))
    if not geometry:
        return None, 0.0, None
    center = seed.centroid_of(geometry)
    if not seed.plausible_centroid(center):
        return None, 0.0, None
    return geometry, acres, center


def _base_feature(
    seed: Any,
    county: dict,
    markets: list[str],
    source: str,
    *,
    parcel_id: str,
    acres: float,
    geometry: dict,
    center: tuple[float, float],
    owner: str | None = None,
    owner2: str | None = None,
    situs: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
    dor: str | None = None,
    sale_price: float | None = None,
    sale_date: str | None = None,
    sale_qualified: str | None = None,
    market_value: float | None = None,
    assessed: float | None = None,
    taxable: float | None = None,
    mail1: str | None = None,
    mail2: str | None = None,
    mail_city: str | None = None,
    mail_state: str | None = None,
    mail_zip: str | None = None,
    jurisdiction: str | None = None,
    gaps: list[str] | None = None,
) -> dict | None:
    if not in_band(acres) or not in_county(county["fips"], center[0], center[1]):
        return None
    feature = seed.empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=markets,
        parcel_id=parcel_id,
        acreage=acres,
        geometry=geometry,
        center=center,
        source=source,
        owner=owner,
        situs=situs,
        city=city,
        zip_code=zip_code,
        dor=dor,
        sale_price=sale_price,
        sale_date=sale_date,
        sale_qualified=sale_qualified,
        market_value=market_value,
        assessed=assessed,
        taxable=taxable,
        mail1=mail1,
        mail2=mail2,
        mail_city=mail_city,
        mail_state=mail_state,
        mail_zip=mail_zip,
        jurisdiction=jurisdiction,
    )
    feature["properties"]["ownerName2"] = owner2
    feature["properties"]["appraiserUrl"] = appraiser_url(county["fips"], parcel_id)
    feature["properties"]["gisViewerUrl"] = gis_viewer_url(county["fips"], None, zoned=False)
    feature["properties"]["dataGaps"] = list(gaps or [])
    feature["properties"]["opportunityZone"] = None
    feature["properties"]["oz2Eligibility"] = None
    feature["properties"]["nearestRoad"] = None
    return feature


def _set_zoning(feature: dict, code: str | None, jurisdiction: str, label: str | None = None) -> bool:
    text = usable_code(code)
    if not text:
        return False
    props = feature["properties"]
    props["zoningCode"] = text
    pretty = label if label and label != text else text
    props["zoningDistrict"] = f"{jurisdiction}:{pretty}"
    props["jurisdictionCode"] = jurisdiction
    fips = props.get("countyFips")
    if fips in SPECS:
        props["gisViewerUrl"] = gis_viewer_url(fips, jurisdiction, zoned=True)
    return True


def _set_flu(feature: dict, code: str | None, jurisdiction: str, source: str, label: str | None = None) -> bool:
    text = usable_code(code)
    if not text:
        return False
    feature["properties"]["flu"] = {
        "code": text,
        "label": (label or text).strip(),
        "jurisdiction": jurisdiction,
        "source": source,
    }
    return True


def _apply_hit(feature: dict, hit: dict | None, jurisdiction: str, source: str, *, zoning: bool) -> bool:
    if not hit:
        return False
    if zoning:
        return _set_zoning(feature, hit.get("code"), jurisdiction, hit.get("label"))
    return _set_flu(feature, hit.get("code"), jurisdiction, source, hit.get("label"))


def miami_where() -> str:
    return (
        f"(LOT_SIZE>={int(MIN_SQFT)} AND LOT_SIZE<={int(MAX_SQFT)}) OR "
        f"((LOT_SIZE IS NULL OR LOT_SIZE=0) AND Shape.STArea()>={int(MIN_SQFT)} AND Shape.STArea()<={int(MAX_SQFT)})"
    )


def normalize_miami(seed: Any, county: dict, markets: list[str], item: dict) -> dict | None:
    attrs = item.get("attributes") or item.get("properties") or {}
    geometry, gis_acres, center = _geometry_feature(seed, item)
    if not geometry or not center:
        return None
    acres = acres_from_sqft(attrs.get("LOT_SIZE"))
    if not in_band(acres):
        acres = gis_acres
    parcel_id = _parcel_id(attrs.get("FOLIO"))
    if not parcel_id:
        return None
    mail2 = " ".join(
        part
        for part in (_clean(attrs.get("TRUE_MAILING_ADDR2")), _clean(attrs.get("TRUE_MAILING_ADDR3")))
        if part
    ) or None
    owner2 = _clean(attrs.get("TRUE_OWNER2"))
    owner3 = _clean(attrs.get("TRUE_OWNER3"))
    if owner3:
        owner2 = f"{owner2}; {owner3}" if owner2 else owner3
    feature = _base_feature(
        seed,
        county,
        markets,
        SPECS["12086"]["source"],
        parcel_id=parcel_id,
        acres=acres or 0,
        geometry=geometry,
        center=center,
        owner=_clean(attrs.get("TRUE_OWNER1")),
        owner2=owner2,
        situs=_clean(attrs.get("TRUE_SITE_ADDR")),
        city=_clean(attrs.get("TRUE_SITE_CITY")),
        zip_code=seed.zip_str(attrs.get("TRUE_SITE_ZIP_CODE")),
        dor=_clean(attrs.get("DOR_CODE_CUR")),
        market_value=_positive(attrs.get("TOTAL_VAL_CUR")),
        mail1=_clean(attrs.get("TRUE_MAILING_ADDR1")),
        mail2=mail2,
        mail_city=_clean(attrs.get("TRUE_MAILING_CITY")),
        mail_state=_clean(attrs.get("TRUE_MAILING_STATE")),
        mail_zip=seed.zip_str(attrs.get("TRUE_MAILING_ZIP_CODE")),
        gaps=["Last sale is not on the Miami-Dade parcel layer."],
    )
    return feature


def normalize_monroe(seed: Any, county: dict, markets: list[str], item: dict) -> dict | None:
    attrs = item.get("attributes") or item.get("properties") or {}
    geometry, gis_acres, center = _geometry_feature(seed, item)
    if not geometry or not center:
        return None
    parcel_id = _parcel_id(attrs.get("RECHAR"))
    if not parcel_id:
        return None
    sale = seed.sale_date(attrs.get("Y1"), attrs.get("M1"))
    feature = _base_feature(
        seed,
        county,
        markets,
        SPECS["12087"]["source"],
        parcel_id=parcel_id,
        acres=gis_acres,
        geometry=geometry,
        center=center,
        owner=_clean(attrs.get("NAME")),
        situs=_clean(attrs.get("LOCATION")) or _clean(attrs.get("PHYS_ADDR_LBL")),
        city=_clean(attrs.get("KEYNAME")),
        dor=_clean(attrs.get("PC")),
        sale_price=_positive(attrs.get("SALE1")),
        sale_date=sale,
        market_value=_positive(attrs.get("PJUST1")),
        assessed=_positive(attrs.get("PASSD1")),
        taxable=_positive(attrs.get("PTAX1")),
        mail1=_clean(attrs.get("ADD1")),
        mail2=_clean(attrs.get("ADD2")),
        mail_city=_clean(attrs.get("CITY")),
        mail_state=_clean(attrs.get("STATE")),
        mail_zip=seed.zip_str(attrs.get("ZIP")),
        gaps=["Monroe PC is not confirmed as a Florida DOR use code."],
    )
    if feature:
        link = _clean(attrs.get("MCPA_URL"))
        if link and "schneidercorp.com" in link:
            feature["properties"]["appraiserUrl"] = link
    return feature


def normalize_broward_geometry(seed: Any, county: dict, markets: list[str], item: dict) -> dict | None:
    attrs = item.get("attributes") or item.get("properties") or {}
    geometry, gis_acres, center = _geometry_feature(seed, item)
    if not geometry or not center:
        return None
    parcel_id = _parcel_id(attrs.get("FOLIO"))
    if not parcel_id:
        return None
    return _base_feature(
        seed,
        county,
        markets,
        SPECS["12011"]["source"],
        parcel_id=parcel_id,
        acres=gis_acres,
        geometry=geometry,
        center=center,
        gaps=["BCPA MapServer/16 is folio and geometry only. The FDOR CO_NO=16 join was not applied."],
    )


def apply_fdor(seed: Any, feature: dict, attrs: dict) -> None:
    if _num(attrs.get("CO_NO")) != 16:
        return
    props = feature["properties"]
    props["ownerName"] = _clean(attrs.get("OWN_NAME"))
    props["situsAddress"] = _clean(attrs.get("PHY_ADDR1")) or props.get("situsAddress")
    props["situsCity"] = _clean(attrs.get("PHY_CITY"))
    props["situsZip"] = seed.zip_str(attrs.get("PHY_ZIPCD"))
    props["dorCode"] = _clean(attrs.get("DOR_UC"))
    props["mailingAddress"] = {
        "line1": _clean(attrs.get("OWN_ADDR1")),
        "line2": None,
        "city": _clean(attrs.get("OWN_CITY")),
        "state": _clean(attrs.get("OWN_STATE")),
        "zip": seed.zip_str(attrs.get("OWN_ZIPCD")),
    }
    props["tax"] = {
        "marketValue": _positive(attrs.get("JV")),
        "assessedValue": _positive(attrs.get("AV_SD")),
        "taxableValue": _positive(attrs.get("TV_SD")),
        "taxes": None,
    }
    props["lastSale"] = {
        "date": seed.sale_date(attrs.get("SALE_YR1"), None),
        "price": _positive(attrs.get("SALE_PRC1")),
        "qualified": _clean(attrs.get("QUAL_CD1")),
    }
    props["dataGaps"] = [
        "Owner, sale, and CAMA are the FDOR statewide cadastral join (CO_NO=16, PARCEL_ID=FOLIO), not the BCPA polygon."
    ]


def normalize_palm_beach(seed: Any, county: dict, markets: list[str], item: dict) -> dict | None:
    attrs = item.get("attributes") or item.get("properties") or {}
    geometry, gis_acres, center = _geometry_feature(seed, item)
    if not geometry or not center:
        return None
    parcel_id = _parcel_id(attrs.get("PARID"))
    if not parcel_id:
        return None
    acres = _num(attrs.get("ACRES"))
    if not in_band(acres):
        acres = gis_acres
    sale_date = seed.text_date(attrs.get("SALE_DATE")) or seed.epoch_to_iso(attrs.get("SALE_DATE"))
    return _base_feature(
        seed,
        county,
        markets,
        SPECS["12099"]["source"],
        parcel_id=parcel_id,
        acres=acres or 0,
        geometry=geometry,
        center=center,
        owner=_clean(attrs.get("OWNER_NAME1")),
        owner2=_clean(attrs.get("OWNER_NAME2")),
        situs=_clean(attrs.get("SITE_ADDR_STR")),
        city=_clean(attrs.get("MUNICIPALITY")),
        dor=_clean(attrs.get("PROPERTY_USE")),
        sale_price=_positive(attrs.get("PRICE")),
        sale_date=sale_date,
        sale_qualified=_clean(attrs.get("QUAL_CODE")),
        market_value=_positive(attrs.get("TOTAL_MARKET")),
        assessed=_positive(attrs.get("ASSESSED_VAL")),
        taxable=_positive(attrs.get("TOTAL_TAXABLE")),
        mail1=_clean(attrs.get("PADDR1")),
        mail2=_clean(attrs.get("PADDR2")),
        mail_city=_clean(attrs.get("CITYNAME")),
        mail_state=_clean(attrs.get("STATE")),
        mail_zip=seed.zip_str(attrs.get("ZIP1")),
        gaps=["PROPERTY_USE is text, not a numeric DOR use code."],
    )


def _join_pair(
    features: list[dict],
    primary: SpatialIndex,
    primary_jurisdiction: str,
    secondary: SpatialIndex | None,
    secondary_jurisdiction: str,
    flu: SpatialIndex | None,
    flu_jurisdiction: str,
    flu_source: str,
    *,
    city_name_field: bool = False,
) -> tuple[int, int]:
    zoned = 0
    flued = 0
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        city_hit = secondary.hit(lon, lat) if secondary else None
        county_hit = primary.hit(lon, lat)
        city_name = usable_code(city_hit.get("extra")) if city_hit else None
        if city_name_field and city_hit and city_name:
            applied = _apply_hit(feature, city_hit, city_name, "", zoning=True)
        elif city_hit and not city_name_field:
            applied = _apply_hit(feature, city_hit, secondary_jurisdiction, "", zoning=True)
        else:
            applied = _apply_hit(feature, county_hit, primary_jurisdiction, "", zoning=True)
        if applied:
            zoned += 1
        flu_hit = flu.hit(lon, lat) if flu else None
        if flu_hit and _apply_hit(feature, flu_hit, flu_jurisdiction, flu_source, zoning=False):
            flued += 1
    return zoned, flued


def _pull_miami(seed: Any, county: dict, markets: list[str], notes: list[str]) -> list[dict]:
    where = miami_where()
    try:
        count_where(MIAMI_PARCELS, where)
    except Exception:
        where = f"LOT_SIZE>={int(MIN_SQFT)} AND LOT_SIZE<={int(MAX_SQFT)}"
        notes.append("Miami-Dade null LOT_SIZE shape-area clause was rejected. The extract uses LOT_SIZE only.")
    fields = [
        "FOLIO",
        "TRUE_OWNER1",
        "TRUE_OWNER2",
        "TRUE_OWNER3",
        "TRUE_MAILING_ADDR1",
        "TRUE_MAILING_ADDR2",
        "TRUE_MAILING_ADDR3",
        "TRUE_MAILING_CITY",
        "TRUE_MAILING_STATE",
        "TRUE_MAILING_ZIP_CODE",
        "TRUE_SITE_ADDR",
        "TRUE_SITE_CITY",
        "TRUE_SITE_ZIP_CODE",
        "TOTAL_VAL_CUR",
        "LAND_VAL_CUR",
        "BUILDING_VAL_CUR",
        "DOR_CODE_CUR",
        "DOR_DESC",
        "PRIMARY_ZONE",
        "LOT_SIZE",
    ]
    raw = fetch_layer(MIAMI_PARCELS, where, fields, geometry=True)
    features = []
    for item in raw:
        feature = normalize_miami(seed, county, markets, item)
        if feature:
            features.append(feature)
    features = _dedupe(features)
    county_zone = index_polygons(fetch_layer(MIAMI_ZONE_COUNTY, "1=1", ["ZONE", "ZONE_DESC"], geometry=True), "ZONE", "ZONE_DESC")
    city_zone = index_polygons(
        fetch_layer(MIAMI_ZONE_CITY, "1=1", ["ZONE", "ZONEDESC", "MUNICNAME"], geometry=True),
        "ZONE",
        "ZONEDESC",
        "MUNICNAME",
    )
    flu = index_polygons(fetch_layer(MIAMI_FLU, "1=1", ["DESCRIPTION"], geometry=True), "DESCRIPTION")
    zoned, flued = _join_pair(
        features,
        county_zone,
        "Unincorporated",
        city_zone,
        "Municipal",
        flu,
        "Miami-Dade",
        "miamidade-cdmp",
        city_name_field=True,
    )
    notes.append(f"Miami-Dade zoning joined {zoned}/{len(features)}. CDMP future land use joined {flued}/{len(features)}.")
    return features


def _pull_monroe(seed: Any, county: dict, markets: list[str], notes: list[str]) -> list[dict]:
    fields = [
        "RECHAR",
        "AK",
        "RPNUMBER",
        "NAME",
        "ADD1",
        "ADD2",
        "CITY",
        "STATE",
        "ZIP",
        "LOCATION",
        "KEYNAME",
        "PHYS_ADDR_LBL",
        "SALE1",
        "M1",
        "Y1",
        "PJUST1",
        "PASSD1",
        "PTAX1",
        "PLAND1",
        "PBLDG1",
        "PYEAR1",
        "PC",
        "MCPA_URL",
    ]
    ids = fetch_object_ids(MONROE_PARCELS, "1=1")
    kept: list[dict] = []
    batch = 60
    for start in range(0, len(ids), batch):
        chunk = fetch_by_ids(MONROE_PARCELS, ids[start : start + batch], ["RECHAR"], geometry=True)
        for item in chunk:
            geometry, acres, center = _geometry_feature(seed, item)
            if not geometry or not center or not in_band(acres):
                continue
            if not in_county("12087", center[0], center[1]):
                continue
            attrs = item.get("attributes") or {}
            kept.append({"objectId": attrs.get("OBJECTID") or item.get("attributes", {}).get("OBJECTID"), "item": item, "acres": acres})
        if start % 3000 == 0:
            print(f"    monroe scan {start}/{len(ids)} kept {len(kept)}", flush=True)
    # Second pass needs attributes. Re-fetch kept ids if present, else use geometry pass ids from the raw item.
    # objectIds are not always echoed. Re-query by RECHAR chunks.
    by_id: dict[str, dict] = {}
    rechars = []
    for row in kept:
        attrs = row["item"].get("attributes") or {}
        parcel_id = _parcel_id(attrs.get("RECHAR"))
        if parcel_id:
            rechars.append(parcel_id)
            by_id[parcel_id] = row
    features = []
    for start in range(0, len(rechars), 40):
        quoted = ",".join("'" + rid.replace("'", "''") + "'" for rid in rechars[start : start + 40])
        data = _query(
            MONROE_PARCELS,
            {"where": f"RECHAR IN ({quoted})", "outFields": ",".join(fields), "returnGeometry": "false", "f": "json"},
        )
        for item in data.get("features") or []:
            attrs = item.get("attributes") or {}
            parcel_id = _parcel_id(attrs.get("RECHAR"))
            prior = by_id.get(parcel_id or "")
            if not prior:
                continue
            merged = {"attributes": attrs, "geometry": prior["item"].get("geometry")}
            feature = normalize_monroe(seed, county, markets, merged)
            if feature:
                features.append(feature)
    features = _dedupe(features)
    zoning = index_polygons(fetch_layer(MONROE_ZONING, "1=1", ["ZONE_", "Zone_Desc"], geometry=True), "ZONE_", "Zone_Desc")
    flu = index_polygons(fetch_layer(MONROE_FLU, "1=1", ["FLUM", "FLUM_Label", "FLUMDESC"], geometry=True), "FLUM", "FLUMDESC")
    zoned, flued = _join_pair(features, zoning, "Monroe", None, "", flu, "Monroe", "monroe-flum")
    if "mcgis4.monroecounty-fl.gov" in TLS_FALLBACK_USED:
        notes.append("Monroe TLS verification failed. Ingest used the documented certificate fallback for mcgis4.monroecounty-fl.gov.")
    notes.append(f"Monroe zoning joined {zoned}/{len(features)}. FLUM joined {flued}/{len(features)}.")
    return features


def _folio_keys(value: Any) -> list[str]:
    text = _parcel_id(value) or ""
    keys: list[str] = []
    digits = "".join(ch for ch in text if ch.isdigit())
    for key in (text, digits, digits.lstrip("0")):
        if key and key not in keys:
            keys.append(key)
    return keys


def _fdor_for(folios: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for start in range(0, len(folios), 25):
        chunk = folios[start : start + 25]
        quoted = ",".join("'" + folio.replace("'", "''") + "'" for folio in chunk)
        try:
            data = _query(
                BROWARD_FDOR,
                {
                    "where": f"PARCEL_ID IN ({quoted})",
                    "outFields": "PARCEL_ID,CO_NO,OWN_NAME,OWN_ADDR1,OWN_CITY,OWN_STATE,OWN_ZIPCD,PHY_ADDR1,PHY_CITY,PHY_ZIPCD,LND_SQFOOT,SALE_PRC1,SALE_YR1,QUAL_CD1,JV,AV_SD,TV_SD,DOR_UC",
                    "returnGeometry": "false",
                    "f": "json",
                },
                timeout=90,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"    fdor batch failed {exc}", flush=True)
            continue
        for item in data.get("features") or []:
            attrs = item.get("attributes") or {}
            if _num(attrs.get("CO_NO")) != 16:
                continue
            for key in _folio_keys(attrs.get("PARCEL_ID")):
                found[key] = attrs
        time.sleep(0.05)
    return found


def _pull_broward(seed: Any, county: dict, markets: list[str], notes: list[str]) -> list[dict]:
    where = f"Shape.STArea()>={int(MIN_SQFT)} AND Shape.STArea()<={int(MAX_SQFT)}"
    raw = fetch_layer(BROWARD_PARCELS, where, ["FOLIO"], geometry=True)
    features = []
    for item in raw:
        feature = normalize_broward_geometry(seed, county, markets, item)
        if feature:
            features.append(feature)
    features = _dedupe(features)
    notes.append(
        "FDOR CO_NO=16 was not joined. Batched PARCEL_ID queries did not return, "
        "so this partial extract is folio and geometry from BCPA MapServer/16."
    )
    bmsd = index_polygons(
        fetch_layer(BROWARD_BMSD_ZONING, "1=1", ["ZONING", "DESCRIPTION", "FOLIO"], geometry=True),
        "ZONING",
        "DESCRIPTION",
    )
    mosaic = index_polygons(fetch_layer(BROWARD_MOSAIC, "1=1", ["ZONE_NAME"], geometry=True), "ZONE_NAME")
    flu = index_polygons(fetch_layer(BROWARD_FLU, "1=1", ["SLUC1"], geometry=True), "SLUC1")
    zoned, flued = _join_pair(
        features,
        mosaic,
        "Broward municipal mosaic",
        bmsd,
        "Unincorporated",
        flu,
        "Broward",
        "broward-sluc1",
    )
    notes.append(
        f"Broward zoning joined {zoned}/{len(features)} (BMSD wins inside the unincorporated district). "
        f"Numeric SLUC1 future land use joined {flued}/{len(features)}."
    )
    return features


def _pull_palm_beach(seed: Any, county: dict, markets: list[str], notes: list[str]) -> list[dict]:
    fields = [
        "PARID",
        "PARCEL_NUMBER",
        "ACRES",
        "OWNER_NAME1",
        "OWNER_NAME2",
        "PADDR1",
        "PADDR2",
        "CITYNAME",
        "STATE",
        "ZIP1",
        "SITE_ADDR_STR",
        "MUNICIPALITY",
        "PRICE",
        "SALE_DATE",
        "QUAL_CODE",
        "TOTAL_MARKET",
        "LAND_MARKET",
        "IMPRV_MRKT",
        "ASSESSED_VAL",
        "TOTAL_TAXABLE",
        "PROPERTY_USE",
    ]
    raw = fetch_layer(PALM_PARCELS, "ACRES>=5 AND ACRES<=150", fields, geometry=True)
    features = []
    for item in raw:
        feature = normalize_palm_beach(seed, county, markets, item)
        if feature:
            features.append(feature)
    features = _dedupe(features)
    zoning = index_polygons(
        fetch_layer(PALM_ZONING, "1=1", ["FCODE", "FNAME", "ZONING_DESC"], geometry=True),
        "FCODE",
        "ZONING_DESC",
    )
    flu = index_polygons(
        fetch_layer(PALM_FLU, "1=1", ["FLU_CODE", "FLU_DESC", "FCODE", "FNAME"], geometry=True),
        "FLU_CODE",
        "FLU_DESC",
    )
    zoned, flued = _join_pair(features, zoning, "Unincorporated", None, "", flu, "Palm Beach", "palm-beach-flu")
    if "maps.co.palm-beach.fl.us" in TLS_FALLBACK_USED:
        notes.append("Palm Beach zoning host TLS verification failed. Ingest used the documented certificate fallback.")
    notes.append(f"Palm Beach unincorporated zoning joined {zoned}/{len(features)}. Future land use joined {flued}/{len(features)}.")
    return features


def _dedupe(features: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for feature in features:
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    rows = list(by_id.values())
    rows.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return rows


def download_south_florida(county: dict, markets: list[str], spec: dict) -> dict:
    seed = _seed()
    fips = county["fips"]
    print(f"Pulling {county['name']} FL ({fips}) via {spec['source']}", flush=True)
    notes: list[str] = []
    if fips == "12086":
        features = _pull_miami(seed, county, markets, notes)
    elif fips == "12087":
        features = _pull_monroe(seed, county, markets, notes)
    elif fips == "12011":
        features = _pull_broward(seed, county, markets, notes)
    elif fips == "12099":
        features = _pull_palm_beach(seed, county, markets, notes)
    else:
        raise RuntimeError(f"{fips} is not a Wave 0 South Florida county")
    if not features:
        raise RuntimeError(f"{fips} kept no 5–150 acre parcels")
    if not all(in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{fips} emitted a parcel outside 5–150 acres")
    for feature in features:
        feature["properties"]["marketIds"] = list(markets)
        props = feature["properties"]
        if props.get("opportunityZone") or props.get("siteScreening") or props.get("nearestRoad"):
            raise RuntimeError(f"{fips} invented a screening field")
    path, lookup, tiles = seed.write_tiles(county, features)
    gaps = [*(spec.get("gaps") or []), *notes]
    print(f"  kept {len(features)} ({spec['coverage']})", flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=spec["coverage"],
        partition="tiles",
        path=path,
        lookup=lookup,
        source=spec["source"],
        query_url=spec["url"],
        gaps=gaps,
        source_count=len(features),
        dropped=0,
        tile_count=tiles,
    )


def refresh_south_florida_index() -> None:
    """Patch the South Florida shelf into the parcel index without rewriting other markets."""
    seed = _seed()
    index_path = seed.OUT_DIR / "index.json"
    index = json.loads(index_path.read_text())
    rows = []
    for fips in FIPS:
        path = seed.COUNTY_DIR / fips / "county.json"
        if path.exists():
            rows.append(json.loads(path.read_text()))
    rows.sort(key=lambda row: row["name"])
    parcel_count = sum(int(row.get("featureCount") or 0) for row in rows)
    complete = [row for row in rows if row.get("coverage") == "complete-gte-5ac" and row.get("featureCount")]
    sample = [row for row in rows if row.get("coverage") in {"sample", "partial"} and row.get("featureCount")]
    gaps = [row for row in rows if not row.get("featureCount")]
    meta = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "market": "South Florida",
        "tier": "shelf",
        "parcelCount": parcel_count,
        "coreMinAcres": MIN_ACRES,
        "coreMaxAcres": MAX_ACRES,
        "tile": {"originLon": seed.ORIGIN_LON, "originLat": seed.ORIGIN_LAT, "tileDeg": seed.TILE_DEG},
        "notes": [
            "Wave 0 is South Florida only: Miami-Dade, Monroe, Broward, and Palm Beach.",
            "Loaded only when this market is selected.",
            "Acreage is 5.0–150.0 inclusive. Utilities are not joined.",
            "Broward is partial. BCPA MapServer/16 is folio and geometry. The FDOR CAMA join was not applied.",
        ],
        "counties": rows,
    }
    rel = "data/fixtures/market-parcels/markets/south-florida/meta.json"
    market_path = seed.ROOT / rel
    market_path.parent.mkdir(parents=True, exist_ok=True)
    market_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    index["markets"]["South Florida"] = {
        "tier": "shelf",
        "parcelCount": parcel_count,
        "completeCountyCount": len(complete),
        "sampleCountyCount": len(sample),
        "gapCountyCount": len(gaps),
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
            for row in rows
        ],
    }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")


COUNTIES = {
    "12086": {"name": "Miami-Dade", "state": "Florida", "fips": "12086"},
    "12087": {"name": "Monroe", "state": "Florida", "fips": "12087"},
    "12011": {"name": "Broward", "state": "Florida", "fips": "12011"},
    "12099": {"name": "Palm Beach", "state": "Florida", "fips": "12099"},
}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--no-index", action="store_true")
    args = parser.parse_args()
    wanted = {name.lower() for name in args.county}
    for fips, county in COUNTIES.items():
        if wanted and county["name"].lower() not in wanted:
            continue
        download_south_florida(county, ["South Florida"], south_florida_spec(fips))
    if not args.no_index:
        refresh_south_florida_index()


if __name__ == "__main__":
    main()
