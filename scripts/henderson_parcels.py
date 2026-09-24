"""Henderson County, North Carolina (Asheville MSA) parcel extract.

Primary parcels are the county FeatureServer, filtered on CALCULATED_ACRES
inclusive of 5.0–150.0. Zoning_aggregated is often the stub "Cities" inside
municipalities and is never copied onto a parcel. City zoning polygons are
joined first. Hendersonville future land use is the city 2045 layer (PIN
join) inside the city limits. Fletcher, Mills River, Laurel Park, and Flat
Rock have no public FLU service, so the county 2024 Future Land Use Map is
the fallback. Opportunity Zone fields stay empty.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from parcel_geometry import contains_point, esri_rings_to_geojson

FIPS = "37089"
SOURCE = "nc-henderson-parcels-37089"
FALLBACK_SOURCE = "nc-onemap-37089"
PARCEL_LAYER = "https://gisweb.hendersoncountync.gov/arcgis/rest/services/Parcels/FeatureServer/0"
ONEMAP_LAYER = "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1"
COUNTY_ZONING = "https://gisweb.hendersoncountync.gov/arcgis/rest/services/GISWeb/Primary_GISWeb_Layers/MapServer/85"
HVL_ZONING = "https://services1.arcgis.com/UTZTmZoX2rsa9yFA/arcgis/rest/services/COH_Zoning_Test/FeatureServer/0"
HVL_ZONING_FALLBACK = "https://gisweb.hendersoncountync.gov/arcgis/rest/services/GISWeb/Primary_GISWeb_Layers/MapServer/83"
FLETCHER_ZONING = "https://gisweb.hendersoncountync.gov/arcgis/rest/services/GISWeb/Primary_GISWeb_Layers/MapServer/80"
MILLS_RIVER_ZONING = "https://gisweb.hendersoncountync.gov/arcgis/rest/services/GISWeb/Primary_GISWeb_Layers/MapServer/81"
LAUREL_PARK_ZONING = "https://gisweb.hendersoncountync.gov/arcgis/rest/services/GISWeb/Primary_GISWeb_Layers/MapServer/82"
FLAT_ROCK_ZONING = "https://gisweb.hendersoncountync.gov/arcgis/rest/services/GISWeb/Primary_GISWeb_Layers/MapServer/79"
COUNTY_FLU = "https://gisweb.hendersoncountync.gov/arcgis/rest/services/GISWeb/Planning_and_Development/MapServer/88"
HVL_FLU = "https://services1.arcgis.com/UTZTmZoX2rsa9yFA/arcgis/rest/services/Future_Land_Use/FeatureServer/16"
MUNICIPAL_BOUNDARIES = "https://gisweb.hendersoncountync.gov/arcgis/rest/services/GISWeb/Primary_GISWeb_Layers/MapServer/96"
APPRAISER_SEARCH = "https://lrcpwa.ncptscloud.com/henderson/parcel-search"
CACHE_VERSION = 2

CITY_ORDER = ("Hendersonville", "Fletcher", "Mills River", "Laurel Park", "Flat Rock")
ROUTE_ORDER = (*CITY_ORDER, "Saluda")
STUB_ZONE_CODES = {"cities", "city", "no"}
FLU_GAP = "No dedicated public FLU service. County 2024 Future Land Use Map (Planning MapServer/88) is the fallback."
STUB_GAP = "Parcel Zoning_aggregated is often the stub Cities inside municipalities and is not used as zoning."

TAX_FIELDS = [
    "PIN",
    "REID",
    "PARCEL_PK",
    "CALCULATED_ACRES",
    "PROPERTY_OWNER",
    "OWNER_MAIL_1",
    "OWNER_MAIL_2",
    "OWNER_MAIL_CITY",
    "OWNER_MAIL_STATE",
    "OWNER_MAIL_ZIP",
    "LOCATION_ADDR",
    "PHYADDR_CITY",
    "PHYADDR_ZIP",
    "PKG_SALE_DATE",
    "PKG_SALE_PRICE",
    "LAND_SALE_DATE",
    "LAND_SALE_PRICE",
    "TOTAL_LAND_VALUE_ASSESSED",
    "TOTAL_BLDG_VALUE_ASSESSED",
    "TOTAL_PROP_VALUE",
    "Zoning_aggregated",
    "CITY",
    "ETJ",
    "LAND_CLASS",
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
    "szip",
    "gisacres",
    "saledate",
    "saledatetx",
    "landval",
    "improvval",
    "parval",
    "cntyfips",
]

GAPS = [
    STUB_GAP,
    "County zoning MapServer/85 ZONE_CODE values Cities and NO mark municipal land and are not joined.",
    "Hendersonville zoning is COH_Zoning_Test (county MapServer/83 if AGOL is down). Fletcher, Mills River, Laurel Park, and Flat Rock zoning are county-hosted.",
    "Hendersonville 2045 FLU is an attribute join on PIN for parcels routed to the city. Fletcher, Mills River, Laurel Park, and Flat Rock have no public FLU service. County Planning MapServer/88 is joined only where its polygon contains the parcel, and that map leaves most of those towns uncovered.",
    "Flat Rock tax CITY codes VH/BR/GR are not a zoning route. Those parcels use the municipal boundary or ETJ=FLAT ROCK.",
    "Saluda is a Polk County tip. No Saluda zoning layer is joined.",
    "Sales are the latest package sale on the parcel, otherwise the latest land sale. There is no multi-transfer sales layer.",
    "TOTAL_PROP_VALUE is tax.marketValue. Assessed value is land plus building assessed values when those fields are present.",
    "NC OneMap cntyfips 089 is the parcel fallback if the county FeatureServer is down. Acreage on this extract is CALCULATED_ACRES.",
    "Opportunity Zone and OZ 2.0 fields are not filled. Eligible tracts are not marked designated.",
    "Owner phones and emails are not on these public layers.",
]

PARCEL_GAPS = [
    "No multi-transfer sale history (latest package or land sale only).",
    STUB_GAP,
]


def henderson_spec() -> dict:
    return {
        "kind": "henderson",
        "url": f"{PARCEL_LAYER}/query",
        "where": "CALCULATED_ACRES>=5 AND CALCULATED_ACRES<=150",
        "source": SOURCE,
        "coverage": "complete-gte-5ac",
        "gaps": list(GAPS),
    }


def canonical_city(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    key = re.sub(r"\s+", " ", text.upper().replace("_", " ")).strip()
    named = {
        "HENDERSONVILLE": "Hendersonville",
        "FLETCHER": "Fletcher",
        "MILLS RIVER": "Mills River",
        "LAUREL PARK": "Laurel Park",
        "FLAT ROCK": "Flat Rock",
        "SALUDA": "Saluda",
    }
    if key in named:
        return named[key]
    # FLAT ROCK VH / BR / GR are tax subtypes, not a city route.
    return None


def etj_cities(value: Any) -> list[str]:
    text = _clean(value) or ""
    found: list[str] = []
    for part in text.split(","):
        city = canonical_city(part)
        if city and city not in found:
            found.append(city)
    return found


def route_jurisdiction(
    *,
    boundary_cities: list[str],
    etj: Any = None,
    city_code: Any = None,
) -> tuple[str | None, str]:
    """City first, then ETJ, then a real tax CITY. Flat Rock subtypes do not route."""
    for name in ROUTE_ORDER:
        if name in boundary_cities:
            return name, "limits"
    for name in ROUTE_ORDER:
        if name in etj_cities(etj):
            return name, "etj"
    mapped = canonical_city(city_code)
    if mapped:
        return mapped, "tax"
    return None, "county"


def is_stub_zone(code: Any) -> bool:
    text = (_clean(code) or "").lower()
    return text in STUB_ZONE_CODES


def is_cities_stub(value: Any) -> bool:
    return (_clean(value) or "").lower() == "cities"


def zoning_from_city(city: str, attrs: dict) -> tuple[str | None, str | None]:
    if city == "Hendersonville":
        return _clean(attrs.get("Zoning")), _clean(attrs.get("Zoning_Cla"))
    if city == "Fletcher":
        return _clean(attrs.get("Zoning")), None
    if city == "Mills River":
        return _clean(attrs.get("CLASSIFICA")), None
    if city == "Laurel Park":
        return _clean(attrs.get("Zone")), None
    if city == "Flat Rock":
        return _clean(attrs.get("ZONING")), None
    return None, None


def zoning_from_county(attrs: dict) -> tuple[str | None, str | None]:
    code = _clean(attrs.get("ZONE_CODE"))
    name = _clean(attrs.get("ZONING"))
    if not code or is_stub_zone(code):
        return None, None
    district = name if name and name != code else None
    return code, district


def parcel_pk(value: Any) -> str | None:
    number = _num(value)
    if number is None:
        text = _clean(value)
        if text and text.isdigit():
            return text
        return None
    if number <= 0:
        return None
    return str(int(number))


def appraiser_url(pk: str) -> str:
    return f"https://lrcpwa.ncptscloud.com/henderson/parcel-detail/{quote(pk, safe='')}"


def parse_sale_date(value: Any) -> str | None:
    text = _clean(value)
    if text:
        match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if match:
            month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[:10]):
            return text[:10]
    number = _num(value)
    if number is not None and number > 10_000_000_000:
        try:
            moment = datetime.fromtimestamp(number / 1000, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        if 1900 <= moment.year <= 2100:
            return moment.date().isoformat()
    return None


def situs_address(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    if text.upper() in {"0 NO ADDRESS ASSIGNED", "NO ADDRESS ASSIGNED", "0"}:
        return None
    return text


def positive(value: Any) -> float | None:
    number = _num(value)
    if number is None or number <= 0:
        return None
    return number


def pick_sale(attrs: dict) -> tuple[str | None, float | None]:
    package_date = parse_sale_date(attrs.get("PKG_SALE_DATE"))
    package_price = positive(attrs.get("PKG_SALE_PRICE"))
    if package_date or package_price:
        return package_date, package_price
    return parse_sale_date(attrs.get("LAND_SALE_DATE")), positive(attrs.get("LAND_SALE_PRICE"))


def map_parcel_attributes(attrs: dict) -> dict | None:
    pin = _clean(attrs.get("PIN")) or _clean(attrs.get("REID")) or parcel_pk(attrs.get("PARCEL_PK"))
    acres = _num(attrs.get("CALCULATED_ACRES"))
    if not pin or acres is None:
        return None
    sale_date, sale_price = pick_sale(attrs)
    land = _num(attrs.get("TOTAL_LAND_VALUE_ASSESSED"))
    building = _num(attrs.get("TOTAL_BLDG_VALUE_ASSESSED"))
    assessed = None
    if land is not None or building is not None:
        assessed = (land or 0) + (building or 0)
        if assessed <= 0:
            assessed = None
    pk = parcel_pk(attrs.get("PARCEL_PK"))
    return {
        "parcelId": pin,
        "acres": acres,
        "owner": _clean(attrs.get("PROPERTY_OWNER")),
        "situs": situs_address(attrs.get("LOCATION_ADDR")),
        "city": _clean(attrs.get("PHYADDR_CITY")),
        "zip": _zip(attrs.get("PHYADDR_ZIP")),
        "dor": _clean(attrs.get("LAND_CLASS")),
        "salePrice": sale_price,
        "saleDate": sale_date,
        "marketValue": positive(attrs.get("TOTAL_PROP_VALUE")),
        "assessed": assessed,
        "mail1": _clean(attrs.get("OWNER_MAIL_1")),
        "mail2": _clean(attrs.get("OWNER_MAIL_2")),
        "mailCity": _clean(attrs.get("OWNER_MAIL_CITY")),
        "mailState": _clean(attrs.get("OWNER_MAIL_STATE")),
        "mailZip": _zip(attrs.get("OWNER_MAIL_ZIP")),
        "zoningAggregated": _clean(attrs.get("Zoning_aggregated")),
        "cityCode": _clean(attrs.get("CITY")),
        "etj": _clean(attrs.get("ETJ")),
        "parcelPk": pk,
        "appraiserUrl": appraiser_url(pk) if pk else APPRAISER_SEARCH,
    }


def map_onemap_attributes(attrs: dict) -> dict | None:
    pin = _clean(attrs.get("parno"))
    acres = _num(attrs.get("gisacres"))
    if not pin or acres is None:
        return None
    return {
        "parcelId": pin,
        "acres": acres,
        "owner": _clean(attrs.get("ownname")),
        "situs": situs_address(attrs.get("siteadd")),
        "city": _clean(attrs.get("scity")),
        "zip": _zip(attrs.get("szip")),
        "dor": None,
        "salePrice": None,
        "saleDate": parse_sale_date(attrs.get("saledatetx")) or parse_sale_date(attrs.get("saledate")),
        "marketValue": positive(attrs.get("parval")),
        "assessed": positive(attrs.get("landval")),
        "mail1": _clean(attrs.get("mailadd")),
        "mail2": None,
        "mailCity": _clean(attrs.get("mcity")),
        "mailState": _clean(attrs.get("mstate")),
        "mailZip": _zip(attrs.get("mzip")),
        "zoningAggregated": None,
        "cityCode": None,
        "etj": None,
        "parcelPk": None,
        "appraiserUrl": APPRAISER_SEARCH,
    }


class SpatialIndex:
    def __init__(self, cell: float = 0.05) -> None:
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

    def hits(self, x: float, y: float) -> list[dict]:
        found: list[dict] = []
        seen: set[int] = set()
        candidates = list(self.buckets.get((_cell(x, self.cell), _cell(y, self.cell)), []))
        candidates.extend(self.broad)
        for feature in candidates:
            marker = id(feature)
            if marker in seen:
                continue
            seen.add(marker)
            if contains_point(feature.get("geometry"), x, y):
                found.append(feature)
        return found

    def hit(self, x: float, y: float) -> dict | None:
        found = self.hits(x, y)
        return found[0] if found else None


def index_features(features: list[dict]) -> SpatialIndex:
    index = SpatialIndex()
    for feature in features:
        index.add(feature)
    return index


def boundary_cities_at(index: SpatialIndex | None, lon: float, lat: float) -> list[str]:
    if index is None:
        return []
    found: list[str] = []
    for feature in index.hits(lon, lat):
        city = canonical_city((feature.get("properties") or {}).get("CITY"))
        if city and city not in found:
            found.append(city)
    return found


def apply_land_use(
    feature: dict,
    *,
    boundaries: SpatialIndex | None,
    zoning: dict[str, SpatialIndex],
    county_zoning: SpatialIndex | None,
    county_flu: SpatialIndex | None,
    hvl_flu_by_pin: dict[str, str],
) -> dict[str, Any]:
    """Join city zoning first. Never copy the Cities stub onto zoningCode."""
    props = feature["properties"]
    lon, lat = props["centroid"]
    city, kind = route_jurisdiction(
        boundary_cities=boundary_cities_at(boundaries, lon, lat),
        etj=props.get("etj"),
        city_code=props.get("cityCode"),
    )
    counts: dict[str, Any] = {
        "city": city or "",
        "kind": kind,
        "zoning": 0,
        "flu": 0,
        "fluSource": "",
        "stub": 1 if is_cities_stub(props.get("zoningAggregated")) else 0,
    }
    if not props.get("situsCity") and city:
        props["situsCity"] = city

    code = None
    district = None
    prefix = None
    if city in CITY_ORDER:
        city_index = zoning.get(city)
        hit = city_index.hit(lon, lat) if city_index else None
        if hit:
            code, district = zoning_from_city(city, hit.get("properties") or {})
        if code:
            prefix = city
        elif kind == "etj" and county_zoning is not None:
            county_hit = county_zoning.hit(lon, lat)
            if county_hit:
                code, district = zoning_from_county(county_hit.get("properties") or {})
                if code:
                    prefix = "Henderson County"
    elif county_zoning is not None:
        county_hit = county_zoning.hit(lon, lat)
        if county_hit:
            code, district = zoning_from_county(county_hit.get("properties") or {})
            if code:
                prefix = "Henderson County"
    if code and not is_stub_zone(code) and not is_cities_stub(code):
        props["zoningCode"] = code
        props["zoningDistrict"] = district
        props["jurisdictionPrefix"] = prefix
        counts["zoning"] = 1
    else:
        props["zoningCode"] = None
        props["zoningDistrict"] = None
        props["jurisdictionPrefix"] = city if city in CITY_ORDER else None

    flu = None
    pin = props.get("parcelId")
    city_flu = hvl_flu_by_pin.get(pin) if city == "Hendersonville" and pin else None
    if city_flu:
        flu = {
            "code": city_flu,
            "label": city_flu,
            "jurisdiction": "Hendersonville",
            "source": "hendersonville-2045-flu",
        }
    elif county_flu is not None:
        hit = county_flu.hit(lon, lat)
        if hit:
            raw = hit.get("properties") or {}
            flu_code = _clean(raw.get("FLU"))
            flu_name = _clean(raw.get("Land_Use"))
            if flu_code:
                flu = {
                    "code": flu_code,
                    "label": flu_name or flu_code,
                    "jurisdiction": "Henderson County",
                    "source": "henderson-county-flu-2024",
                }
    props["flu"] = flu
    if flu:
        counts["flu"] = 1
        counts["fluSource"] = flu["source"]

    gaps = list(PARCEL_GAPS)
    if city in CITY_ORDER and city != "Hendersonville":
        gaps.append(f"No dedicated public FLU for {city}. County 2024 FLU is used only where that polygon contains the parcel.")
    elif city == "Hendersonville" and (not flu or flu["source"] != "hendersonville-2045-flu"):
        gaps.append("Hendersonville 2045 FLU had no PIN match. County 2024 FLU is used only where that polygon contains the parcel.")
    if city == "Saluda":
        gaps.append("Saluda zoning is not on a Henderson County city layer.")
    props["dataGaps"] = gaps
    props.pop("zoningAggregated", None)
    props.pop("cityCode", None)
    props.pop("etj", None)
    return counts


def download_henderson(county: dict, markets: list[str], spec: dict) -> dict:
    import seed_market_parcels as seed

    cache_path = seed.CACHE_DIR / f"{county['fips']}-henderson-v{CACHE_VERSION}.json"
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = seed.json.loads(cache_path.read_text())
        if cached.get("version") == CACHE_VERSION and cached.get("features"):
            print(f"  cache hit {len(cached['features'])}", flush=True)
            return _write(seed, county, markets, cached)

    print("Pulling Henderson County via Parcels FeatureServer/0", flush=True)
    used_fallback = False
    fallback_reason = None
    try:
        expected = seed.count_where(f"{PARCEL_LAYER}/query", spec["where"])
        if expected <= 0:
            raise RuntimeError("County parcels returned no 5–150 acre rows")
        raw = _pull(seed, f"{PARCEL_LAYER}/query", spec["where"], TAX_FIELDS)
        features, dropped = _features_from_raw(seed, raw, county, markets, map_parcel_attributes, SOURCE)
        source = SOURCE
        query_url = f"{PARCEL_LAYER}/query"
    except Exception as exc:  # noqa: BLE001
        used_fallback = True
        fallback_reason = str(exc)
        print(f"  county parcels failed ({exc}); falling back to NC OneMap cntyfips 089", flush=True)
        where = "cntyfips='089' AND gisacres>=5 AND gisacres<=150"
        expected = seed.count_where(f"{ONEMAP_LAYER}/query", where)
        raw = _pull(seed, f"{ONEMAP_LAYER}/query", where, ONEMAP_FIELDS)
        features, dropped = _features_from_raw(seed, raw, county, markets, map_onemap_attributes, FALLBACK_SOURCE)
        source = FALLBACK_SOURCE
        query_url = f"{ONEMAP_LAYER}/query"

    if not used_fallback and len(features) < 5000:
        raise RuntimeError(f"Henderson kept {len(features)} of {expected} source rows. Refusing a thin extract.")

    joins = _load_joins(seed)
    stats = _enrich_all(features, joins)
    if stats["zoningPolygons"] > 50 and stats["zoningJoined"] == 0:
        raise RuntimeError("Henderson zoning polygons were fetched but none contained a parcel point")
    if stats["stubUsedAsZoning"]:
        raise RuntimeError("Zoning_aggregated Cities stub was copied onto a parcel")
    gaps = list(GAPS)
    if used_fallback:
        gaps.insert(0, f"County Parcels FeatureServer was unavailable ({fallback_reason}). This extract used NC OneMap cntyfips 089.")
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
    gaps = list(payload.get("gaps") or GAPS)
    source_count = payload.get("sourceCount")
    dropped = payload.get("dropped")
    if isinstance(source_count, int) and source_count > len(features):
        collapsed = source_count - len(features)
        note = (
            f"{source_count} source rows kept {len(features)} parcel ids. "
            f"{collapsed} duplicate PIN{'s' if collapsed != 1 else ''} collapsed to the larger part."
        )
        if note not in gaps:
            gaps.insert(0, note)
        dropped = collapsed
    for feature in features:
        feature["properties"]["marketIds"] = markets
    path, lookup, tiles = (None, None, 0)
    if features:
        path, lookup, tiles = seed.write_tiles(county, features)
    stats = payload.get("stats") or {}
    print(
        f"  kept {len(features)} zoning {stats.get('zoningJoined', 0)} "
        f"flu {stats.get('fluJoined', 0)} cities-stub {stats.get('citiesStub', 0)}",
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
        gaps=gaps,
        source_count=payload.get("sourceCount"),
        dropped=dropped,
        tile_count=tiles,
        extra={
            "crs": {"wkid": 102100, "latestWkid": 3857, "storedAs": 4326},
            "acreageField": "CALCULATED_ACRES",
            "municipalities": stats.get("municipalities") or [],
            "unincorporated": stats.get("unincorporated"),
            "zoningJoinedCount": stats.get("zoningJoined"),
            "fluJoinedCount": stats.get("fluJoined"),
            "citiesStubCount": stats.get("citiesStub"),
            "stubUsedAsZoning": stats.get("stubUsedAsZoning"),
            "appraiserSearchUrl": APPRAISER_SEARCH,
            "viewerLinkTemplate": "https://lrcpwa.ncptscloud.com/henderson/parcel-detail/{parcelPk}",
        },
    )


def _features_from_raw(seed: Any, raw: list[dict], county: dict, markets: list[str], mapper, source: str):
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
        lon, lat = center
        if not (-83.05 <= lon <= -82.05 and 35.0 <= lat <= 35.65):
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
            dor=mapped["dor"],
            sale_price=mapped["salePrice"],
            sale_date=mapped["saleDate"],
            market_value=mapped["marketValue"],
            assessed=mapped["assessed"],
            mail1=mapped["mail1"],
            mail2=mapped["mail2"],
            mail_city=mapped["mailCity"],
            mail_state=mapped["mailState"],
            mail_zip=mapped["mailZip"],
        )
        props = feature["properties"]
        props["appraiserUrl"] = mapped["appraiserUrl"]
        props["zoningAggregated"] = mapped["zoningAggregated"]
        props["cityCode"] = mapped["cityCode"]
        props["etj"] = mapped["etj"]
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        previous = by_id.get(mapped["parcelId"])
        if previous is None or (props["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[mapped["parcelId"]] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def _pull(seed: Any, url: str, where: str, fields: list[str]) -> list[dict]:
    ids = seed.fetch_object_ids(url, where)
    print(f"  {url.split('/rest/')[-1]} ids {len(ids)}", flush=True)
    return seed.fetch_by_ids(url, ids, fields, batch=80)


def _pull_attributes(seed: Any, url: str, fields: list[str]) -> list[dict]:
    """Page attributes without objectIds. A long objectIds query 404s on this AGOL layer."""
    rows: list[dict] = []
    offset = 0
    page = 2000
    while True:
        data = seed.fetch_json(
            url,
            {
                "where": "1=1",
                "outFields": ",".join(fields),
                "returnGeometry": "false",
                "orderByFields": "OBJECTID",
                "resultOffset": str(offset),
                "resultRecordCount": str(page),
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            raise RuntimeError(str(data["error"])[:300])
        batch = data.get("features") or []
        if not batch:
            break
        rows.extend(batch)
        print(f"  attributes {url.split('/rest/')[-1]} {len(rows)}", flush=True)
        if len(batch) < page and not data.get("exceededTransferLimit"):
            break
        offset += len(batch)
        if offset > 100_000:
            break
    return rows


def _load_joins(seed: Any) -> dict:
    zoning_catalog = [
        {
            "name": "Hendersonville",
            "url": f"{HVL_ZONING}/query",
            "fallback": f"{HVL_ZONING_FALLBACK}/query",
            "fields": ["Zoning", "Zoning_Cla"],
            "layerUrl": HVL_ZONING,
            "independentGis": True,
            "fluUrl": HVL_FLU,
            "fluGap": None,
        },
        {
            "name": "Fletcher",
            "url": f"{FLETCHER_ZONING}/query",
            "fields": ["Zoning"],
            "layerUrl": FLETCHER_ZONING,
            "independentGis": False,
            "fluUrl": COUNTY_FLU,
            "fluGap": FLU_GAP,
        },
        {
            "name": "Mills River",
            "url": f"{MILLS_RIVER_ZONING}/query",
            "fields": ["CLASSIFICA"],
            "layerUrl": MILLS_RIVER_ZONING,
            "independentGis": False,
            "fluUrl": COUNTY_FLU,
            "fluGap": FLU_GAP,
        },
        {
            "name": "Laurel Park",
            "url": f"{LAUREL_PARK_ZONING}/query",
            "fields": ["Zone"],
            "layerUrl": LAUREL_PARK_ZONING,
            "independentGis": False,
            "fluUrl": COUNTY_FLU,
            "fluGap": FLU_GAP,
        },
        {
            "name": "Flat Rock",
            "url": f"{FLAT_ROCK_ZONING}/query",
            "fields": ["ZONING"],
            "layerUrl": FLAT_ROCK_ZONING,
            "independentGis": False,
            "fluUrl": COUNTY_FLU,
            "fluGap": FLU_GAP,
        },
    ]
    zoning: dict[str, SpatialIndex] = {}
    municipalities = []
    zoning_polygons = 0
    for spec in zoning_catalog:
        features, used_url, error = _pull_polygons(seed, spec["url"], spec["fields"])
        note = None
        layer_url = spec["layerUrl"]
        if error and spec.get("fallback"):
            print(f"  {spec['name']} zoning fallback ({error})", flush=True)
            features, used_url, error = _pull_polygons(seed, spec["fallback"], spec["fields"])
            note = "City AGOL zoning was down; used county Primary_GISWeb_Layers/83."
            layer_url = HVL_ZONING_FALLBACK
        if error:
            print(f"  {spec['name']} zoning unavailable: {error}", flush=True)
        zoning[spec["name"]] = index_features(features)
        zoning_polygons += len(features)
        record = {
            "name": spec["name"],
            "independentGis": spec["independentGis"],
            "zoningUrl": layer_url,
            "fluUrl": spec.get("fluUrl"),
            "fluGap": spec.get("fluGap"),
            "join": "city zoning polygon; Hendersonville FLU by PIN; county FLU only where the 2024 polygon contains the point",
            "zoningFeatures": len(features),
            "parcelCount": 0,
            "limitsCount": 0,
            "zoningJoined": 0,
            "fluJoined": 0,
            "countyFluFallback": 0,
        }
        if note:
            record["note"] = note
        if used_url and error is None and spec.get("fallback") and layer_url == HVL_ZONING_FALLBACK:
            record["note"] = note
        municipalities.append(record)

    county_features, _, county_error = _pull_polygons(seed, f"{COUNTY_ZONING}/query", ["ZONE_CODE", "ZONING"])
    if county_error:
        print(f"  county zoning unavailable: {county_error}", flush=True)
    flu_features, _, flu_error = _pull_polygons(seed, f"{COUNTY_FLU}/query", ["FLU", "Land_Use"])
    if flu_error:
        print(f"  county FLU unavailable: {flu_error}", flush=True)
    limits, _, limits_error = _pull_polygons(seed, f"{MUNICIPAL_BOUNDARIES}/query", ["CITY"])
    if limits_error:
        print(f"  municipal boundaries unavailable: {limits_error}", flush=True)
    hvl_flu: dict[str, str] = {}
    try:
        for item in _pull_attributes(seed, f"{HVL_FLU}/query", ["PIN", "FLU"]):
            attrs = item.get("attributes") or {}
            pin = _clean(attrs.get("PIN"))
            code = _clean(attrs.get("FLU"))
            if not pin or not code:
                continue
            existing = hvl_flu.get(pin)
            if existing and code not in existing.split(" / "):
                hvl_flu[pin] = f"{existing} / {code}"
            elif not existing:
                hvl_flu[pin] = code
    except Exception as exc:  # noqa: BLE001
        print(f"  Hendersonville FLU unavailable: {exc}", flush=True)
    for record in municipalities:
        if record["name"] == "Hendersonville":
            record["fluFeatures"] = len(hvl_flu)
    unincorporated = {
        "zoningUrl": COUNTY_ZONING,
        "fluUrl": COUNTY_FLU,
        "zoningFeatures": len(county_features),
        "fluFeatures": len(flu_features),
        "parcelCount": 0,
        "zoningJoined": 0,
        "fluJoined": 0,
        "note": "Unincorporated zoning is ZONE_CODE. Cities and NO are municipal stubs and are not joined. FLU is the 2024 county map.",
    }
    return {
        "zoning": zoning,
        "countyZoning": index_features(county_features),
        "countyFlu": index_features(flu_features),
        "boundaries": index_features(limits),
        "hvlFlu": hvl_flu,
        "municipalities": municipalities,
        "unincorporated": unincorporated,
        "zoningPolygons": zoning_polygons + len(county_features),
    }


def _pull_polygons(seed: Any, url: str, fields: list[str]) -> tuple[list[dict], str, str | None]:
    try:
        raw = _pull(seed, url, "1=1", fields)
    except Exception as exc:  # noqa: BLE001
        return [], url, str(exc)
    features = []
    for item in raw:
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        if not geometry:
            continue
        features.append({"type": "Feature", "properties": item.get("attributes") or {}, "geometry": geometry})
    return features, url, None


def _enrich_all(features: list[dict], joins: dict) -> dict:
    zoning_joined = 0
    flu_joined = 0
    cities_stub = 0
    stub_used = 0
    by_name = {item["name"]: item for item in joins["municipalities"]}
    unincorporated = joins["unincorporated"]
    for feature in features:
        counts = apply_land_use(
            feature,
            boundaries=joins.get("boundaries"),
            zoning=joins["zoning"],
            county_zoning=joins.get("countyZoning"),
            county_flu=joins.get("countyFlu"),
            hvl_flu_by_pin=joins.get("hvlFlu") or {},
        )
        zoning_joined += counts["zoning"]
        flu_joined += counts["flu"]
        cities_stub += counts["stub"]
        code = feature["properties"].get("zoningCode")
        if is_stub_zone(code) or is_cities_stub(code):
            stub_used += 1
        city = counts["city"]
        if city in by_name:
            by_name[city]["parcelCount"] += 1
            if counts["kind"] == "limits":
                by_name[city]["limitsCount"] += 1
            if counts["zoning"] and feature["properties"].get("jurisdictionPrefix") == city:
                by_name[city]["zoningJoined"] += 1
            if counts["fluSource"] == "hendersonville-2045-flu" and city == "Hendersonville":
                by_name[city]["fluJoined"] += 1
            elif counts["fluSource"] == "henderson-county-flu-2024":
                by_name[city]["countyFluFallback"] += 1
        elif counts["kind"] == "county" or city in {"", "Saluda"}:
            if city != "Saluda":
                unincorporated["parcelCount"] += 1
                if counts["zoning"] and feature["properties"].get("jurisdictionPrefix") == "Henderson County":
                    unincorporated["zoningJoined"] += 1
                if counts["fluSource"] == "henderson-county-flu-2024":
                    unincorporated["fluJoined"] += 1
            else:
                saluda = by_name.setdefault(
                    "Saluda",
                    {
                        "name": "Saluda",
                        "independentGis": False,
                        "zoningUrl": None,
                        "fluUrl": COUNTY_FLU,
                        "fluGap": "Saluda is mostly Polk County. No Henderson Saluda zoning layer.",
                        "join": "no city zoning; county FLU only when the 2024 polygon contains the point",
                        "zoningFeatures": 0,
                        "parcelCount": 0,
                        "limitsCount": 0,
                        "zoningJoined": 0,
                        "fluJoined": 0,
                        "countyFluFallback": 0,
                    },
                )
                saluda["parcelCount"] += 1
                if counts["fluSource"] == "henderson-county-flu-2024":
                    saluda["fluJoined"] += 1
                    saluda["countyFluFallback"] += 1
    municipalities = [item for item in joins["municipalities"]]
    if "Saluda" in by_name and by_name["Saluda"] not in municipalities:
        municipalities.append(by_name["Saluda"])
    return {
        "zoningJoined": zoning_joined,
        "fluJoined": flu_joined,
        "citiesStub": cities_stub,
        "stubUsedAsZoning": stub_used,
        "zoningPolygons": joins.get("zoningPolygons") or 0,
        "municipalities": municipalities,
        "unincorporated": unincorporated,
    }


def _cell(value: float, cell: float) -> int:
    return math.floor(value / cell)


def _bbox(feature: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, (int, float)):
            return
        if node and isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        for item in node:
            walk(item)

    walk((feature.get("geometry") or {}).get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
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


def _zip(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return text[:10]
