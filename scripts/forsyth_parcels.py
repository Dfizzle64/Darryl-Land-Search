"""Forsyth County, North Carolina (Winston-Salem MSA, FIPS 37067) parcel extract.

This is MapForsyth — not Forsyth County, Georgia (FIPS 13117, Cumming).

Parcels, zoning, and sales use MapForsyth AGOL. Future land use is a PIN join
to the county Proposed Residential Land Use layer, with Kernersville town GIS
and High Point city Place Types preferred where those municipalities apply.
NC OneMap cntyfips 067 supplies the land/improvement split and is the parcel
fallback if Parcels_Hosted is down. Growth Management Areas 2045 are noted on
the land-use label and are not used as a place type.
"""

from __future__ import annotations

import math
import re
import ssl
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote, urlparse

from parcel_geometry import contains_point, esri_rings_to_geojson

FIPS = "37067"
GEORGIA_FIPS = "13117"
SOURCE = "nc-mapforsyth-37067"
FALLBACK_SOURCE = "nc-onemap-37067"
CACHE_VERSION = 1

PARCEL_LAYER = "https://services1.arcgis.com/5Yf8nIJWE7cxpd3N/arcgis/rest/services/Parcels_Hosted/FeatureServer/0"
PARCEL_COUNTY = "https://maps.co.forsyth.nc.us/arcgis/rest/services/CAD/CAD_Parcels/FeatureServer/0"
ZONING_LAYER = "https://services1.arcgis.com/5Yf8nIJWE7cxpd3N/arcgis/rest/services/Zoning_Hosted/FeatureServer/0"
SALES_LAYER = "https://services1.arcgis.com/5Yf8nIJWE7cxpd3N/arcgis/rest/services/SalesApp_Hosted/FeatureServer/0"
FLU_LAYER = "https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/LandUse_PotentialResidentialGrowth/FeatureServer/0"
GMA_LAYER = "https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Planning_Inspection/FeatureServer/15"
LIMITS_LAYER = "https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Planning_Inspection/FeatureServer/0"
KE_ZONING = "https://gis.toknc.com/server/rest/services/CommunityDevelopment/Zoning/FeatureServer/14"
KE_FLU = "https://gis.toknc.com/server/rest/services/CommunityDevelopment/Land_Use_Plan/FeatureServer/2"
HP_ZONING = "https://gisentapp01.highpointnc.gov/server/rest/services/Zoning/MapServer/0"
HP_FLU = "https://gisentapp01.highpointnc.gov/server/rest/services/Planning/MapServer/29"
ONEMAP_LAYER = "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1"
ONEMAP_ALT = "https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1"
VIEWER = "https://lrcpwa.ncptscloud.com/forsyth/parcel-detail/{parcel_pk}"
SEARCH_URL = "https://lrcpwa.ncptscloud.com/forsyth/parcel-search"

WHERE_BAND = "CALCULATEDACREAGE>=5 AND CALCULATEDACREAGE<=150"
ONEMAP_WHERE = "cntyfips='067' AND gisacres>=5 AND gisacres<=150"

LOOKALIKE_BITS = ("cumming", "forsythco.com", "forsythcountyga", "fips=13117", "13117")
KE_HOST = "gis.toknc.com"
_KE_SSL = ssl._create_unverified_context()

MUNI_NAMES = {
    "WS": "Winston-Salem",
    "KE": "Kernersville",
    "CL": "Clemmons",
    "LE": "Lewisville",
    "WA": "Walkertown",
    "RH": "Rural Hall",
    "TO": "Tobaccoville",
    "BE": "Bethania",
    "HP": "High Point",
    "KI": "King",
    "FC": "Forsyth County",
    "UNINC": "Unincorporated",
    "KV": "KV",
}
FC_CORPORATE = {"RH", "TO", "BE"}
NO_DEDICATED_FLU = {"CL", "LE", "WA", "RH", "TO", "BE"}

PARCEL_FIELDS = [
    "TAXPIN",
    "PIN",
    "PARCEL_PK",
    "REID",
    "CALCULATEDACREAGE",
    "ACREAGE",
    "CURRENTOWNERNAME1",
    "CURRENTOWNERNAME2",
    "CURRENTOWNERADDRESS",
    "CURRENTOWNERCITYSTZIP",
    "PROPERTYADDRESS",
    "CURRENTDEEDDATE",
    "LASTQUALIFIEDSALEPRICE",
    "TOTALVALUE",
    "PRZONING",
    "Detailed_Property_Info_Link",
]
ONEMAP_FIELDS = [
    "parno",
    "ownname",
    "mailadd",
    "mcity",
    "mstate",
    "mzip",
    "siteadd",
    "scity",
    "gisacres",
    "saledate",
    "saledatetx",
    "parval",
    "landval",
    "improvval",
    "cntyfips",
]

CITY_ST_ZIP = re.compile(
    r"^(?P<city>.*?)(?:,\s*|\s+)(?P<state>[A-Za-z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)$"
)

GAPS = [
    "MapForsyth Parcels_Hosted TOTALVALUE is a string assessed total with no land/building split. NC OneMap cntyfips 067 landval and improvval fill that split when the PIN matches. OneMap parval is not stored as a market value.",
    "LASTQUALIFIEDSALEPRICE is 0 on most 5–150 acre parcels. A qualified SalesApp transfer (XFER_QUALCODE Q, positive price, latest date) fills the sale. Disqualified (DQ) transfers are not used. CURRENTDEEDDATE is a deed date when no qualified sale is found.",
    "No dedicated public FLU FeatureServer for Clemmons, Lewisville, Walkertown, Rural Hall, Tobaccoville, or Bethania. Those use county Proposed Residential Land Use (PIN join). Clemmons and Kernersville area-plan categories differ from the rest of that layer.",
    "High Point county zoning is only about 8 polygons. City Zoning MapServer/0 is preferred for the Forsyth tip and is citywide, so only Forsyth parcel centroids are joined. Place Types (about 68) are coarse.",
    "Kernersville town GIS (gis.toknc.com) presents a certificate this client cannot verify. Town zoning and PROP_LU are still read for KE. County Zoning_Hosted KE is the fallback.",
    "Rural Hall, Tobaccoville, and Bethania have corporate limits. Their zoning jurisdiction on the county layer is typically FC, not a separate municipal code.",
    "King (KI) is a Stokes edge on the county zoning layer. Stokes County GIS is out of scope. KV is a rare zoning jurisdiction code and is not treated as a municipality.",
    "Growth Management Areas 2045 are five legacy areas (the layer describes 1 as Urban through 5 as Rural). They are appended to a future-land-use label and are not used as a place type when ProposedLU is missing.",
    "Tax/Beltway January 2016 parcels are stale and are not wired. County REST can be flaky, so parcels, zoning, and sales use the AGOL mirrors. FLU, corporate limits, and GMA are county host only.",
    "No owner phones or emails. Forsyth County, Georgia (FIPS 13117, Cumming) is a different county and is not this extract. No paid vendor data.",
]


def forsyth_spec() -> dict:
    return {
        "kind": "forsyth",
        "url": f"{PARCEL_LAYER}/query",
        "where": WHERE_BAND,
        "source": SOURCE,
        "coverage": "complete-gte-5ac",
        "gaps": list(GAPS),
    }


def assert_nc_forsyth(county: dict) -> None:
    """Refuse Forsyth County, Georgia and any other same-name county."""
    fips = str(county.get("fips") or "")
    state = str(county.get("state") or "")
    if fips == GEORGIA_FIPS or "georgia" in state.lower():
        raise RuntimeError(
            "Refusing Forsyth County, Georgia (FIPS 13117, Cumming). This adapter is MapForsyth FIPS 37067."
        )
    if fips != FIPS or state != "North Carolina":
        raise RuntimeError(
            f"Refusing {county.get('name')} {state} {fips}. MapForsyth parcel enrich is Forsyth County, North Carolina FIPS 37067."
        )


def assert_public_nc(url: str) -> None:
    lower = url.lower()
    if any(bit in lower for bit in LOOKALIKE_BITS):
        raise RuntimeError(f"Refusing Forsyth GA / Cumming lookalike URL: {url}")


def pin_key(value: Any) -> str | None:
    """Match TAXPIN `####-##-####.00` to ProposedLU PIN `####-##-####.000`."""
    text = _clean(value)
    if not text:
        return None
    if "." in text:
        head, frac = text.split(".", 1)
        frac = frac.rstrip("0")
        return head if head and not frac else (f"{head}.{frac}" if head else text)
    return text


def parse_city_st_zip(value: Any) -> tuple[str | None, str | None, str | None]:
    text = _squeeze(value)
    if not text:
        return None, None, None
    match = CITY_ST_ZIP.match(text)
    if not match:
        return None, None, None
    city = _squeeze(match.group("city"))
    state = match.group("state").upper()
    zip_code = match.group("zip")[:5]
    return city, state, zip_code


def parse_epoch_date(value: Any) -> str | None:
    text = _clean(value)
    if text and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    if text:
        match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if match:
            month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
    number = _num(value)
    if number is None:
        return None
    seconds = number / 1000 if number > 10_000_000_000 else number
    if seconds < 10_000_000:
        return None
    try:
        moment = datetime.fromtimestamp(seconds, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    if 1900 <= moment.year <= 2100:
        return moment.date().isoformat()
    return None


def cast_money(value: Any) -> float | None:
    if isinstance(value, str):
        value = value.replace(",", "").replace("$", "").strip()
    number = _num(value)
    if number is None or number <= 0:
        return None
    return number


def cast_value_or_zero(value: Any) -> float | None:
    """Keep a real zero (vacant improvement value) and drop nulls."""
    number = _num(value)
    if number is None or number < 0:
        return None
    return number


def viewer_url(parcel_pk: Any, published: Any) -> str:
    link = _clean(published)
    if link and "ncptscloud.com/forsyth/" in link.lower() and not any(bit in link.lower() for bit in LOOKALIKE_BITS):
        return link
    pk = _clean(parcel_pk)
    if pk:
        return VIEWER.format(parcel_pk=quote(pk, safe=""))
    return SEARCH_URL


def gma_suffix(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    if text == "1":
        return "GMA 1 (Urban)"
    if text == "5":
        return "GMA 5 (Rural)"
    return f"GMA {text}"


def map_parcel_attributes(attrs: dict) -> dict | None:
    pin = _clean(attrs.get("TAXPIN")) or _clean(attrs.get("PIN"))
    acres = _num(attrs.get("CALCULATEDACREAGE"))
    if acres is None:
        acres = _num(attrs.get("ACREAGE"))
    if not pin or acres is None:
        return None
    owner = _squeeze(attrs.get("CURRENTOWNERNAME1"))
    owner2 = _squeeze(attrs.get("CURRENTOWNERNAME2"))
    if owner2 and owner2 == owner:
        owner2 = None
    city, state, zip_code = parse_city_st_zip(attrs.get("CURRENTOWNERCITYSTZIP"))
    raw_city = None if city else _squeeze(attrs.get("CURRENTOWNERCITYSTZIP"))
    price = cast_money(attrs.get("LASTQUALIFIEDSALEPRICE"))
    return {
        "parcelId": pin,
        "pinKey": pin_key(pin),
        "parcelPk": _clean(attrs.get("PARCEL_PK")),
        "acres": acres,
        "owner": owner,
        "owner2": owner2,
        "situs": _squeeze(attrs.get("PROPERTYADDRESS")),
        "city": None,
        "zip": None,
        "salePrice": price,
        "saleDate": parse_epoch_date(attrs.get("CURRENTDEEDDATE")),
        "saleQualified": "Q" if price else None,
        "assessed": cast_money(attrs.get("TOTALVALUE")),
        "mail1": _squeeze(attrs.get("CURRENTOWNERADDRESS")),
        "mail2": raw_city,
        "mailCity": city,
        "mailState": state,
        "mailZip": zip_code,
        "zoningAttribute": _squeeze(attrs.get("PRZONING")),
        "appraiserUrl": viewer_url(attrs.get("PARCEL_PK"), attrs.get("Detailed_Property_Info_Link")),
    }


def map_onemap_attributes(attrs: dict) -> dict | None:
    pin = _clean(attrs.get("parno"))
    acres = _num(attrs.get("gisacres"))
    if not pin or acres is None:
        return None
    mail_zip = _zip(attrs.get("mzip"))
    return {
        "parcelId": pin,
        "pinKey": pin_key(pin),
        "parcelPk": None,
        "acres": acres,
        "owner": _squeeze(attrs.get("ownname")),
        "owner2": None,
        "situs": _squeeze(attrs.get("siteadd")),
        "city": _title_place(attrs.get("scity")),
        "zip": None,
        "salePrice": None,
        "saleDate": parse_epoch_date(attrs.get("saledatetx")) or parse_epoch_date(attrs.get("saledate")),
        "saleQualified": None,
        "assessed": cast_money(attrs.get("parval")),
        "mail1": _squeeze(attrs.get("mailadd")),
        "mail2": None,
        "mailCity": _squeeze(attrs.get("mcity")),
        "mailState": _squeeze(attrs.get("mstate")),
        "mailZip": mail_zip,
        "zoningAttribute": None,
        "appraiserUrl": SEARCH_URL,
        "landValue": cast_value_or_zero(attrs.get("landval")),
        "improvementValue": cast_value_or_zero(attrs.get("improvval")),
    }


class SpatialIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = _bbox(feature)
        if not bbox:
            return
        west, south, east, north = bbox
        ix0, ix1 = _cell(west, self.cell), _cell(east, self.cell)
        iy0, iy1 = _cell(south, self.cell), _cell(north, self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 400:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        """Smallest containing polygon, so a town district beats a county-sized ring."""
        found: list[dict] = []
        for feature in self.buckets.get((_cell(x, self.cell), _cell(y, self.cell)), []):
            if contains_point(feature.get("geometry"), x, y):
                found.append(feature)
        for feature in self.broad:
            if contains_point(feature.get("geometry"), x, y):
                found.append(feature)
        if not found:
            return None
        return min(found, key=_bbox_area)


def index_features(features: list[dict]) -> SpatialIndex:
    index = SpatialIndex()
    for feature in features:
        index.add(feature)
    return index


def apply_land_use(feature: dict, joins: dict) -> dict[str, int]:
    props = feature["properties"]
    point = props.get("joinPoint") or props.get("centroid") or [None, None]
    lon, lat = point
    counts = {"zoning": 0, "attribute": 0, "flu": 0, "sale": 0, "values": 0, "gma": 0, "place": ""}
    limits_code = None
    if lon is not None and joins.get("limits") is not None:
        hit = joins["limits"].hit(lon, lat)
        if hit:
            limits_code = _clean((hit.get("properties") or {}).get("MUNICIPALITY"))
    county_attrs: dict = {}
    if lon is not None and joins.get("countyZoning") is not None:
        hit = joins["countyZoning"].hit(lon, lat)
        if hit:
            county_attrs = hit.get("properties") or {}
    juris = _clean(county_attrs.get("ZONING_JURISDICTION"))
    place = _place_code(limits_code, juris)
    counts["place"] = place or ""
    if not props.get("situsCity"):
        props["situsCity"] = _situs_city(limits_code)

    zoning_code = None
    zoning_district = None
    prefix = MUNI_NAMES.get(place or "", None)
    local = None
    if place == "KE" or juris == "KE":
        local = _layer_hit(joins.get("keZoning"), lon, lat)
        zoning_code = _clean((local or {}).get("ZONING"))
        if zoning_code:
            prefix = "Kernersville"
    elif place == "HP" or juris == "HP":
        local = _layer_hit(joins.get("hpZoning"), lon, lat)
        zoning_code = _clean((local or {}).get("ZONE"))
        dist = _clean((local or {}).get("DIST"))
        if zoning_code:
            prefix = "High Point"
            zoning_district = dist if dist and dist != zoning_code else None
    if not zoning_code:
        zoning_code = _clean(county_attrs.get("ZONING_DISTRICT"))
        if zoning_code and juris:
            prefix = MUNI_NAMES.get(juris, prefix)
    if zoning_code:
        props["zoningCode"] = zoning_code
        props["zoningDistrict"] = zoning_district
        props["jurisdictionPrefix"] = prefix
        counts["zoning"] = 1
    elif props.get("zoningAttribute"):
        props["zoningCode"] = props["zoningAttribute"]
        props["jurisdictionPrefix"] = prefix
        counts["attribute"] = 1
    props["jurisdictionCode"] = place if place not in {None, "UNINC"} else juris

    flu = _flu_for(place, juris, lon, lat, props.get("pinKey"), joins)
    gma_code = None
    if lon is not None and joins.get("gma") is not None:
        hit = joins["gma"].hit(lon, lat)
        if hit:
            gma_code = _clean((hit.get("properties") or {}).get("GROWTHMANAGEMENTAREA"))
            counts["gma"] = 1
    if flu and gma_code:
        suffix = gma_suffix(gma_code)
        if suffix and suffix not in (flu.get("label") or ""):
            flu["label"] = f"{flu['label']} · {suffix}"
    props["flu"] = flu
    if flu:
        counts["flu"] = 1

    sale = (joins.get("sales") or {}).get(props.get("pinKey"))
    last = props.get("lastSale") or {}
    if sale and not last.get("price"):
        if sale.get("date"):
            last["date"] = sale["date"]
        last["price"] = sale["price"]
        last["qualified"] = "Q"
        props["lastSale"] = last
        counts["sale"] = 1

    values = (joins.get("values") or {}).get(props.get("pinKey"))
    tax = props.setdefault("tax", {})
    if values:
        if tax.get("assessedValue") is None and values.get("total"):
            tax["assessedValue"] = values["total"]
        if values.get("land") is not None:
            tax["landValue"] = values["land"]
        if values.get("improve") is not None:
            tax["improvementValue"] = values["improve"]
        counts["values"] = 1
    elif tax.get("landValue") is not None or tax.get("improvementValue") is not None:
        counts["values"] = 1
        values = {"land": tax.get("landValue"), "improve": tax.get("improvementValue")}

    props["dataGaps"] = _parcel_gaps(props, place, flu, counts, values)
    props.pop("zoningAttribute", None)
    props.pop("pinKey", None)
    props.pop("joinPoint", None)
    return counts


def _flu_for(place: str | None, juris: str | None, lon: float | None, lat: float | None, pin: str | None, joins: dict) -> dict | None:
    local_ke = place == "KE" or juris == "KE"
    local_hp = place == "HP" or juris == "HP"
    if local_ke and lon is not None:
        hit = _layer_hit(joins.get("keFlu"), lon, lat)
        code = _clean((hit or {}).get("PROP_LU"))
        if code:
            return {"code": code, "label": code, "jurisdiction": "Kernersville", "source": "kernersville-land-use-plan"}
    if local_hp and lon is not None:
        hit = _layer_hit(joins.get("hpFlu"), lon, lat)
        code = _clean((hit or {}).get("PlaceTypes")) or _clean((hit or {}).get("PT_All"))
        if code:
            return {"code": code, "label": code, "jurisdiction": "High Point", "source": "highpoint-place-types"}
    row = (joins.get("proposed") or {}).get(pin or "")
    if not row:
        return None
    code = row.get("code")
    label = row.get("label") or code
    if not code and not label:
        return None
    jurisdiction = MUNI_NAMES.get(place or "", "Forsyth County")
    return {
        "code": code or label,
        "label": label or code,
        "jurisdiction": jurisdiction,
        "source": "forsyth-proposed-lu",
        "areaPlan": row.get("areaPlan"),
    }


def _parcel_gaps(props: dict, place: str | None, flu: dict | None, counts: dict, values: dict | None) -> list[str]:
    gaps = ["County TOTALVALUE has no land/building split."]
    if not values:
        gaps.append("NC OneMap did not match this PIN for land and improvement values.")
    if not (props.get("lastSale") or {}).get("price"):
        gaps.append("No qualified sale price on the parcel or in SalesApp.")
    elif counts["sale"] == 0 and (props.get("lastSale") or {}).get("date"):
        gaps.append("Sale date is the deed date (CURRENTDEEDDATE), not a SalesApp transfer date.")
    if counts["zoning"] == 0 and counts["attribute"] == 1:
        gaps.append("Zoning is the parcel PRZONING attribute. No zoning polygon contained the point.")
    if place in FC_CORPORATE:
        gaps.append(f"{MUNI_NAMES.get(place, place)} corporate limits use Forsyth County (FC) zoning, not a separate code.")
    if place == "KI":
        gaps.append("King zoning here is the Stokes edge only. Stokes County GIS is out of scope.")
    if place == "KV" or (props.get("jurisdictionCode") == "KV"):
        gaps.append("ZONING_JURISDICTION KV is a rare code and should be verified.")
    if flu and flu.get("source") == "forsyth-proposed-lu":
        area = (flu.get("areaPlan") or "").lower()
        if place == "CL" or "clemmons" in area:
            gaps.append("Clemmons has no dedicated FLU layer. County ProposedLU categories differ for that area plan.")
        elif place in NO_DEDICATED_FLU:
            gaps.append(f"{MUNI_NAMES.get(place, place)} has no dedicated FLU layer. County ProposedLU is the join.")
        elif place == "KE" or "kernersville" in area:
            gaps.append("Kernersville town land-use plan missed this point. County ProposedLU categories differ for Kernersville.")
        elif place == "HP":
            gaps.append("High Point Place Types missed this tip parcel. County ProposedLU is the fallback.")
    elif flu is None and place in NO_DEDICATED_FLU | {"KE", "HP"}:
        gaps.append(f"No future land use polygon for {MUNI_NAMES.get(place or '', 'this municipality')}.")
    if flu and "areaPlan" in flu:
        flu.pop("areaPlan", None)
    return gaps


def download_forsyth(county: dict, markets: list[str], spec: dict) -> dict:
    import seed_market_parcels as seed

    assert_nc_forsyth(county)
    cache_path = seed.CACHE_DIR / f"{county['fips']}.json"
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = seed.json.loads(cache_path.read_text())
        if cached.get("version") == CACHE_VERSION and cached.get("features"):
            print(f"  cache hit {len(cached['features'])}", flush=True)
            return _write(seed, county, markets, cached)

    print("Pulling Forsyth NC via MapForsyth Parcels_Hosted (not Forsyth GA)", flush=True)
    used_fallback = False
    fallback_reason = None
    try:
        expected = seed.count_where(f"{PARCEL_LAYER}/query", spec["where"])
        if expected <= 0:
            raise RuntimeError("Parcels_Hosted returned no 5–150 acre rows")
        raw = _pull_geo(seed, f"{PARCEL_LAYER}/query", spec["where"], PARCEL_FIELDS)
        features, dropped = _features_from_raw(seed, raw, county, markets, map_parcel_attributes, SOURCE)
        source = SOURCE
        query_url = f"{PARCEL_LAYER}/query"
        if len(features) < 1000:
            raise RuntimeError(f"Parcels_Hosted kept only {len(features)} rows")
    except Exception as exc:  # noqa: BLE001
        used_fallback = True
        fallback_reason = str(exc)
        print(f"  Parcels_Hosted failed ({exc}); falling back to NC OneMap cntyfips 067", flush=True)
        expected = seed.count_where(f"{ONEMAP_LAYER}/query", ONEMAP_WHERE)
        raw = _pull_geo(seed, f"{ONEMAP_LAYER}/query", ONEMAP_WHERE, ONEMAP_FIELDS)
        features, dropped = _features_from_raw(seed, raw, county, markets, map_onemap_attributes, FALLBACK_SOURCE)
        source = FALLBACK_SOURCE
        query_url = f"{ONEMAP_LAYER}/query"

    joins = _load_joins(seed, features, used_fallback)
    stats = _enrich_all(features, joins)
    gaps = list(GAPS)
    if used_fallback:
        gaps.insert(0, f"Parcels_Hosted was unavailable ({fallback_reason}). This extract used NC OneMap cntyfips 067.")
    gaps.append(
        "Measured on this extract: "
        f"{len(features)} parcels in CALCULATEDACREAGE 5–150. "
        f"Zoning polygons {stats['zoningJoined']}, PRZONING attribute fallback {stats['attributeZoning']}, "
        f"FLU {stats['fluJoined']} (county ProposedLU is a residential-growth subset, not a countywide future-land-use map), "
        f"qualified SalesApp fills {stats['salesFilled']}, OneMap land/improve {stats['valuesJoined']}, "
        f"GMA touches {stats['gmaJoined']} and is not stored as FLU."
    )
    for note in joins.get("notes") or []:
        if note not in gaps:
            gaps.append(note)
    payload = {
        "version": CACHE_VERSION,
        "source": source,
        "queryUrl": query_url,
        "sourceCount": expected,
        "dropped": dropped,
        "features": features,
        "gaps": gaps,
        "stats": stats,
        "coverage": spec["coverage"],
    }
    seed.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(seed.json.dumps(payload, separators=(",", ":")))
    return _write(seed, county, markets, payload)


def _write(seed: Any, county: dict, markets: list[str], payload: dict) -> dict:
    features = payload["features"]
    for feature in features:
        feature["properties"]["marketIds"] = markets
    path, lookup, tiles = (None, None, 0)
    if features:
        path, lookup, tiles = seed.write_tiles(county, features)
    stats = payload.get("stats") or {}
    print(
        f"  kept {len(features)} zoning {stats.get('zoningJoined', 0)} "
        f"attribute {stats.get('attributeZoning', 0)} flu {stats.get('fluJoined', 0)} "
        f"sales {stats.get('salesFilled', 0)} onemap {stats.get('valuesJoined', 0)}",
        flush=True,
    )
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=payload.get("coverage") or ("complete-gte-5ac" if features else "gap"),
        partition="tiles" if features else "none",
        path=path,
        lookup=lookup,
        source=payload.get("source") or SOURCE,
        query_url=payload.get("queryUrl"),
        gaps=list(payload.get("gaps") or GAPS),
        source_count=payload.get("sourceCount"),
        dropped=payload.get("dropped"),
        tile_count=tiles,
        extra={
            "crs": {"wkid": 102719, "latestWkid": 2264, "storedAs": 4326},
            "municipalities": stats.get("municipalities") or [],
            "unincorporated": stats.get("unincorporated"),
            "zoningJoinedCount": stats.get("zoningJoined"),
            "fluJoinedCount": stats.get("fluJoined"),
            "attributeZoningCount": stats.get("attributeZoning"),
            "salesFilledCount": stats.get("salesFilled"),
            "oneMapValueCount": stats.get("valuesJoined"),
            "gmaJoinedCount": stats.get("gmaJoined"),
            "viewerLinkTemplate": VIEWER,
            "appraiserSearchUrl": SEARCH_URL,
            "rejectedLookalikes": ["Forsyth County, Georgia FIPS 13117 / Cumming"],
        },
    )


def _features_from_raw(seed: Any, raw: list[dict], county: dict, markets: list[str], mapper, source: str):
    from parcel_geometry import representative_point

    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        mapped = mapper(attrs)
        geometry, _computed = seed.rings_to_feature_geometry(item.get("geometry"))
        if not mapped or not geometry:
            dropped += 1
            continue
        center = seed.centroid_of(geometry)
        if not seed.plausible_centroid(center) or not seed.in_band(mapped["acres"]):
            dropped += 1
            continue
        feature = seed.empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=mapped["parcelId"],
            acreage=mapped["acres"],
            geometry=geometry,
            center=center,
            source=source,
            owner=mapped["owner"],
            situs=mapped["situs"],
            city=mapped["city"],
            zip_code=mapped["zip"],
            zoning=None,
            sale_price=mapped["salePrice"],
            sale_date=mapped["saleDate"],
            sale_qualified=mapped["saleQualified"],
            assessed=mapped["assessed"],
            mail1=mapped["mail1"],
            mail2=mapped["mail2"],
            mail_city=mapped["mailCity"],
            mail_state=mapped["mailState"],
            mail_zip=mapped["mailZip"],
        )
        props = feature["properties"]
        props["ownerName2"] = mapped["owner2"]
        props["appraiserUrl"] = mapped["appraiserUrl"]
        props["zoningAttribute"] = mapped["zoningAttribute"]
        props["pinKey"] = mapped["pinKey"]
        inside = representative_point(geometry)
        props["joinPoint"] = list(inside) if inside else list(center)
        if mapped.get("landValue") is not None:
            props["tax"]["landValue"] = mapped["landValue"]
        if mapped.get("improvementValue") is not None:
            props["tax"]["improvementValue"] = mapped["improvementValue"]
        previous = by_id.get(mapped["parcelId"])
        if previous is None or (props["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[mapped["parcelId"]] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def _load_joins(seed: Any, features: list[dict], used_fallback: bool) -> dict:
    notes: list[str] = []
    county_zones, zoning_error = _safe_polygons(
        seed, f"{ZONING_LAYER}/query", ["ZONING_DISTRICT", "ZONING_JURISDICTION"], "Zoning_Hosted"
    )
    if zoning_error:
        notes.append(f"Zoning_Hosted was unavailable ({zoning_error}). Parcel PRZONING is the only zoning.")
    limits, limits_error = _safe_polygons(seed, f"{LIMITS_LAYER}/query", ["MUNICIPALITY", "JURISDICTION"], "Corporate limits")
    if limits_error:
        notes.append(f"Corporate limits were unavailable ({limits_error}). Rural Hall, Tobaccoville, and Bethania may not be named.")
    gma, gma_error = _safe_polygons(seed, f"{GMA_LAYER}/query", ["GROWTHMANAGEMENTAREA"], "GMA 2045")
    if gma_error:
        notes.append(f"Growth Management Areas 2045 were unavailable ({gma_error}).")
    ke_zones, ke_z_error = _safe_ke(f"{KE_ZONING}/query", ["ZONING", "DOCKET"])
    if ke_z_error:
        notes.append(f"Kernersville zoning was unavailable ({ke_z_error}). County KE zoning is the fallback.")
    ke_flu, ke_f_error = _safe_ke(f"{KE_FLU}/query", ["PROP_LU"])
    if ke_f_error:
        notes.append(f"Kernersville land-use plan was unavailable ({ke_f_error}).")
    hp_zones, hp_z_error = _safe_polygons(seed, f"{HP_ZONING}/query", ["ZONE", "DIST"], "High Point zoning")
    if hp_z_error:
        notes.append(f"High Point zoning was unavailable ({hp_z_error}). County HP zoning is sparse.")
    hp_flu, hp_f_error = _safe_polygons(seed, f"{HP_FLU}/query", ["PlaceTypes", "PT_All"], "High Point place types")
    if hp_f_error:
        notes.append(f"High Point Place Types were unavailable ({hp_f_error}).")

    proposed: dict[str, dict] = {}
    flu_error = None
    try:
        rows = _page_attributes(seed.fetch_json, f"{FLU_LAYER}/query", "1=1", ["PIN", "ProposedLU", "CommonProposedLU", "AreaPlan"])
        for item in rows:
            attrs = item.get("attributes") or {}
            key = pin_key(attrs.get("PIN"))
            label = _squeeze(attrs.get("ProposedLU"))
            code = _squeeze(attrs.get("CommonProposedLU")) or label
            if not key or not (code or label):
                continue
            proposed[key] = {"code": code, "label": label or code, "areaPlan": _clean(attrs.get("AreaPlan"))}
        print(f"  ProposedLU pins {len(proposed)}", flush=True)
    except Exception as exc:  # noqa: BLE001
        flu_error = str(exc)
        notes.append(f"County ProposedLU was unavailable ({exc}). FLU is limited to Kernersville and High Point where those layers hit.")
    if flu_error is None and not proposed:
        notes.append("County ProposedLU returned no PIN rows.")

    sales: dict[str, dict] = {}
    try:
        sales = _latest_qualified_sales(seed.fetch_json, f"{SALES_LAYER}/query")
        print(f"  qualified sales pins {len(sales)}", flush=True)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"SalesApp_Hosted was unavailable ({exc}). Zero LASTQUALIFIEDSALEPRICE stays empty.")

    values: dict[str, dict] = {}
    if not used_fallback:
        try:
            values = _onemap_values(seed)
            print(f"  OneMap value pins {len(values)}", flush=True)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"NC OneMap land/improve split was unavailable ({exc}).")
            if not values:
                notes.append("Primary parcels still have TOTALVALUE only.")

    municipalities = _municipality_templates(len(county_zones), len(ke_zones), len(ke_flu), len(hp_zones), len(hp_flu), len(proposed))
    unincorporated = {
        "zoningUrl": ZONING_LAYER,
        "fluUrl": FLU_LAYER,
        "zoningFeatures": len(county_zones),
        "fluFeatures": len(proposed),
        "zoningJoined": 0,
        "fluJoined": 0,
        "note": "Forsyth County (FC) zoning plus county ProposedLU. Rural Hall, Tobaccoville, and Bethania are corporate towns on this same FC zoning.",
    }
    return {
        "limits": index_features(limits),
        "countyZoning": index_features(county_zones),
        "keZoning": index_features(ke_zones),
        "hpZoning": index_features(hp_zones),
        "keFlu": index_features(ke_flu),
        "hpFlu": index_features(hp_flu),
        "gma": index_features(gma),
        "proposed": proposed,
        "sales": sales,
        "values": values,
        "notes": notes,
        "municipalities": municipalities,
        "unincorporated": unincorporated,
        "zoningPolygons": len(county_zones),
    }


def _municipality_templates(
    county_n: int, ke_z: int, ke_f: int, hp_z: int, hp_f: int, proposed_n: int
) -> list[dict]:
    def row(code: str, *, independent: bool, zoning_url: str, flu_url: str | None, flu_gap: str | None, note: str, zoning_n: int, flu_n: int) -> dict:
        return {
            "code": code,
            "name": MUNI_NAMES[code],
            "independentGis": independent,
            "zoningUrl": zoning_url,
            "fluUrl": flu_url,
            "fluGap": flu_gap,
            "join": "spatial zoning (WKID 2264 stored as WGS84); FLU by PIN or local polygon",
            "zoningFeatures": zoning_n,
            "fluFeatures": flu_n,
            "zoningJoined": 0,
            "fluJoined": 0,
            "note": note,
        }

    return [
        row("WS", independent=False, zoning_url=ZONING_LAYER, flu_url=FLU_LAYER, flu_gap=None, zoning_n=county_n, flu_n=proposed_n, note="Winston-Salem uses MapForsyth Zoning_Hosted (WS) and county ProposedLU plus GMA 2045."),
        row("KE", independent=True, zoning_url=KE_ZONING, flu_url=KE_FLU, flu_gap=None, zoning_n=ke_z, flu_n=ke_f, note="Town zoning and PROP_LU are preferred. The town certificate does not verify; county KE zoning is the fallback."),
        row("CL", independent=False, zoning_url=ZONING_LAYER, flu_url=None, flu_gap="No dedicated Clemmons FLU FeatureServer. County ProposedLU is joined with a category caveat.", zoning_n=county_n, flu_n=proposed_n, note="Zoning_Hosted filter CL. Clemmons OpenGov mirrors the county zoning schema and is not a second roll."),
        row("LE", independent=False, zoning_url=ZONING_LAYER, flu_url=None, flu_gap="No dedicated Lewisville FLU FeatureServer.", zoning_n=county_n, flu_n=proposed_n, note="Zoning_Hosted filter LE. FLU is county ProposedLU."),
        row("WA", independent=False, zoning_url=ZONING_LAYER, flu_url=None, flu_gap="No dedicated Walkertown FLU FeatureServer.", zoning_n=county_n, flu_n=proposed_n, note="Zoning_Hosted filter WA. FLU is county ProposedLU."),
        row("RH", independent=False, zoning_url=ZONING_LAYER, flu_url=None, flu_gap="No dedicated Rural Hall FLU FeatureServer.", zoning_n=county_n, flu_n=proposed_n, note="Corporate limits only. Zoning is typically FC."),
        row("TO", independent=False, zoning_url=ZONING_LAYER, flu_url=None, flu_gap="No dedicated Tobaccoville FLU FeatureServer.", zoning_n=county_n, flu_n=proposed_n, note="Corporate limits only. Zoning is typically FC."),
        row("BE", independent=False, zoning_url=ZONING_LAYER, flu_url=None, flu_gap="No dedicated Bethania FLU FeatureServer.", zoning_n=county_n, flu_n=proposed_n, note="Corporate limits only. Zoning is typically FC."),
        row("HP", independent=True, zoning_url=HP_ZONING, flu_url=HP_FLU, flu_gap=None, zoning_n=hp_z, flu_n=hp_f, note="City zoning and Place Types are preferred and clipped by joining only Forsyth centroids. County HP zoning is sparse."),
        row("KI", independent=False, zoning_url=ZONING_LAYER, flu_url=None, flu_gap="King is a Stokes edge. No Forsyth-side town FLU.", zoning_n=county_n, flu_n=0, note="A handful of KI zoning polygons. Stokes County GIS is out of scope."),
    ]


def _enrich_all(features: list[dict], joins: dict) -> dict:
    zoning_joined = 0
    flu_joined = 0
    attribute = 0
    sales_filled = 0
    values_joined = 0
    gma_joined = 0
    by_code = {item["code"]: item for item in joins["municipalities"]}
    unincorporated = joins.get("unincorporated")
    for feature in features:
        counts = apply_land_use(feature, joins)
        zoning_joined += counts["zoning"]
        flu_joined += counts["flu"]
        attribute += counts["attribute"]
        sales_filled += counts["sale"]
        values_joined += counts["values"]
        gma_joined += counts["gma"]
        place = counts["place"]
        record = by_code.get(place or "")
        if record is not None:
            if counts["zoning"]:
                record["zoningJoined"] += 1
            if counts["flu"]:
                record["fluJoined"] += 1
        elif unincorporated is not None and place in {None, "", "FC", "UNINC"}:
            if counts["zoning"]:
                unincorporated["zoningJoined"] += 1
            if counts["flu"]:
                unincorporated["fluJoined"] += 1
    if joins.get("zoningPolygons", 0) > 100 and zoning_joined == 0 and attribute == 0:
        raise RuntimeError("Forsyth zoning polygons were fetched but none contained a parcel point")
    return {
        "zoningJoined": zoning_joined,
        "fluJoined": flu_joined,
        "attributeZoning": attribute,
        "salesFilled": sales_filled,
        "valuesJoined": values_joined,
        "gmaJoined": gma_joined,
        "zoningPolygons": joins.get("zoningPolygons") or 0,
        "municipalities": joins["municipalities"],
        "unincorporated": unincorporated,
    }


def _latest_qualified_sales(fetch: Callable, url: str) -> dict[str, dict]:
    assert_public_nc(url)
    rows = _page_attributes(fetch, url, "XFER_QUALCODE LIKE 'Q%' AND XFER_SALEPRICE>0", ["XFER_PIN", "XFER_XFERDATE", "XFER_SALEPRICE", "XFER_QUALCODE"])
    best: dict[str, dict] = {}
    for item in rows:
        attrs = item.get("attributes") or {}
        qual = (_clean(attrs.get("XFER_QUALCODE")) or "").upper()
        if not qual.startswith("Q") or qual.startswith("DQ"):
            continue
        price = cast_money(attrs.get("XFER_SALEPRICE"))
        key = pin_key(attrs.get("XFER_PIN"))
        if not key or price is None:
            continue
        date = parse_epoch_date(attrs.get("XFER_XFERDATE"))
        current = best.get(key)
        if current is None or _sale_is_newer(date, price, current):
            best[key] = {"date": date, "price": price, "qualified": "Q"}
    return best


def _sale_is_newer(date: str | None, price: float, current: dict) -> bool:
    old = current.get("date")
    if date and not old:
        return True
    if old and not date:
        return False
    if date != old:
        return (date or "") > (old or "")
    return price > (current.get("price") or 0)


def _onemap_values(seed: Any) -> dict[str, dict]:
    del seed
    values: dict[str, dict] = {}
    last_error = None
    for layer in (ONEMAP_LAYER, ONEMAP_ALT):
        try:
            rows = _page_attributes(
                _fetch_public,
                f"{layer}/query",
                ONEMAP_WHERE,
                ["parno", "landval", "improvval", "parval"],
                page=1000,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
        for item in rows:
            attrs = item.get("attributes") or {}
            key = pin_key(attrs.get("parno"))
            if not key:
                continue
            values[key] = {
                "land": cast_value_or_zero(attrs.get("landval")),
                "improve": cast_value_or_zero(attrs.get("improvval")),
                "total": cast_money(attrs.get("parval")),
            }
        if values:
            return values
    if last_error and not values:
        raise RuntimeError(last_error)
    return values


def _safe_polygons(seed: Any, url: str, fields: list[str], label: str) -> tuple[list[dict], str | None]:
    try:
        features = _polygons_via_seed(seed, url, fields)
        print(f"  {label} polygons {len(features)}", flush=True)
        return features, None
    except Exception as exc:  # noqa: BLE001
        print(f"  {label} unavailable: {exc}", flush=True)
        return [], str(exc)


def _safe_ke(url: str, fields: list[str]) -> tuple[list[dict], str | None]:
    try:
        assert_public_nc(url)
        raw = _pull_geo_custom(_fetch_ke, url, "1=1", fields)
        features = _esri_features(raw)
        print(f"  Kernersville {url.rsplit('/', 2)[-2]} polygons {len(features)}", flush=True)
        return features, None
    except Exception as exc:  # noqa: BLE001
        print(f"  Kernersville unavailable: {exc}", flush=True)
        return [], str(exc)


def _polygons_via_seed(seed: Any, url: str, fields: list[str]) -> list[dict]:
    assert_public_nc(url)
    ids = seed.fetch_object_ids(url, "1=1")
    print(f"  {url.split('/rest/')[-1]} ids {len(ids)}", flush=True)
    raw = seed.fetch_by_ids(url, ids, fields, batch=100) if ids else []
    return _esri_features(raw)


def _pull_geo(seed: Any, url: str, where: str, fields: list[str]) -> list[dict]:
    assert_public_nc(url)
    ids = seed.fetch_object_ids(url, where)
    print(f"  parcel ids {len(ids)}", flush=True)
    if not ids:
        return []
    return seed.fetch_by_ids(url, ids, fields, batch=80)


def _pull_geo_custom(fetch: Callable, url: str, where: str, fields: list[str]) -> list[dict]:
    data = fetch(url, {"where": where, "returnIdsOnly": "true", "f": "json"})
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:240])
    ids = [int(i) for i in (data.get("objectIds") or [])]
    raw: list[dict] = []
    for start in range(0, len(ids), 80):
        chunk = ids[start : start + 80]
        page = fetch(
            url,
            {
                "objectIds": ",".join(str(i) for i in chunk),
                "outFields": ",".join(fields),
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            },
        )
        if page.get("error"):
            raise RuntimeError(str(page["error"])[:240])
        raw.extend(page.get("features") or [])
    return raw


def _esri_features(raw: list[dict]) -> list[dict]:
    features = []
    for item in raw:
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        if not geometry:
            continue
        features.append({"type": "Feature", "properties": item.get("attributes") or {}, "geometry": geometry})
    return features


def _page_attributes(fetch: Callable, url: str, where: str, fields: list[str], page: int = 2000) -> list[dict]:
    assert_public_nc(url)
    rows: list[dict] = []
    offset = 0
    seen: set[str] = set()
    while offset < 250000:
        params = {
            "where": where,
            "outFields": ",".join(fields),
            "returnGeometry": "false",
            "resultOffset": str(offset),
            "resultRecordCount": str(page),
            "orderByFields": "OBJECTID",
            "f": "json",
        }
        data = fetch(url, params)
        if data.get("error"):
            message = str(data["error"])
            if offset == 0 and "orderBy" in message.lower():
                params.pop("orderByFields")
                data = fetch(url, params)
            if data.get("error"):
                raise RuntimeError(message[:300])
        batch = data.get("features") or []
        if not batch:
            break
        signature = str((batch[0].get("attributes") or {}).get("OBJECTID") or batch[0].get("attributes"))
        if signature in seen:
            break
        seen.add(signature)
        rows.extend(batch)
        offset += len(batch)
        if len(batch) < page and not data.get("exceededTransferLimit"):
            break
        print(f"    attributes {offset}", flush=True)
    return rows


def _fetch_public(url: str, params: dict | None = None) -> dict:
    """Shorter timeout than the seeder. OneMap count queries can hang."""
    import json
    import time
    import urllib.parse
    import urllib.request

    assert_public_nc(url)
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/forsyth-nc"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:160]}: {last}")


def _fetch_ke(url: str, params: dict | None = None) -> dict:
    import json
    import time
    import urllib.parse
    import urllib.request

    assert_public_nc(url)
    if urlparse(url).netloc != KE_HOST:
        raise RuntimeError(f"Refusing unverified TLS for non-Kernersville host: {url}")
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/forsyth-nc"})
            with urllib.request.urlopen(req, timeout=180, context=_KE_SSL) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Kernersville GIS failed: {last}")


def _layer_hit(index: SpatialIndex | None, lon: float | None, lat: float | None) -> dict | None:
    if index is None or lon is None or lat is None:
        return None
    feature = index.hit(lon, lat)
    if not feature:
        return None
    return feature.get("properties") or {}


def _place_code(limits: str | None, juris: str | None) -> str | None:
    if limits and limits != "UNINC":
        return limits
    if juris and juris != "FC":
        return juris
    if limits == "UNINC" or juris == "FC":
        return "FC"
    return juris or limits


def _situs_city(code: str | None) -> str | None:
    if not code or code in {"UNINC", "FC", "KV"}:
        return None
    return MUNI_NAMES.get(code)


def _title_place(value: Any) -> str | None:
    text = _squeeze(value)
    if not text:
        return None
    return " ".join(part.capitalize() for part in text.split(" "))


def _cell(value: float, cell: float) -> int:
    return math.floor(value / cell)


def _bbox(feature: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, (int, float)) or not node:
            return
        if isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        for item in node:
            walk(item)

    walk((feature.get("geometry") or {}).get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_area(feature: dict) -> float:
    bbox = _bbox(feature)
    if not bbox:
        return 1e99
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _squeeze(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    return " ".join(text.split())


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


def _zip(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return text[:10]
