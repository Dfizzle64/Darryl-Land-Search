"""Iredell County (Charlotte MSA) parcel extract.

County TaxSQL_Parcels cover incorporated and unincorporated land. Municipal
zoning and FLU are first-class polygon layers, spatial-joined in the shared
WKID 102719 / 2264 and stored as WGS84. NC OneMap cntyfips 097 is the fallback
when the county parcel host is down.

Horizon Plan "Municipal Planning Area" values are stubs and are not treated as
city future land use. The TaxSQL Market field is an adjustment factor, not
dollars.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from parcel_geometry import contains_point, esri_rings_to_geojson

FIPS = "37097"
SOURCE = "nc-iredell-taxsql-37097"
FALLBACK_SOURCE = "nc-onemap-37097"
PARCEL_LAYER = "https://maps.iredellcountync.gov/server/rest/services/Data/TaxSQL_Parcels/FeatureServer/0"
ONEMAP_LAYER = "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1"
ZONING_ROOT = "https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer"
CITY_LIMITS = "https://maps.iredellcountync.gov/server/rest/services/Data/CityLimits/FeatureServer/0"
MOORESVILLE_ZONING = "https://gis.mooresvillenc.gov/gisadmin/rest/services/PlanningServices/MapServer/1"
MOORESVILLE_FCLU = "https://gis.mooresvillenc.gov/gisadmin/rest/services/Planning/FCLU/FeatureServer/0"
MOORESVILLE_ZONING_MIRROR = f"{ZONING_ROOT}/3"
VIEWER = "https://iredellcountync.mapgeo.io/datasets/properties?query={pin}"
CACHE_VERSION = 1

TOWNS = ("Mooresville", "Statesville", "Troutman", "Harmony", "Love Valley", "Davidson")
TOWNS_WITHOUT_FLU = ("Statesville", "Troutman", "Harmony", "Love Valley", "Davidson")
OVERLAY_ONLY = {"CZ", "CUD", "PRD", "CONDITIONAL"}

TAX_FIELDS = [
    "PIN",
    "ACCOUNT",
    "TaxAcres",
    "Jan1Own1",
    "Jan1Own2",
    "Name",
    "ADD1",
    "ADD2",
    "ADD3",
    "CITY",
    "STATE",
    "ZIP",
    "HouseNumber",
    "SDIR",
    "STREET",
    "STYPE",
    "ST_SUFFIX",
    "CityLocationCode",
    "CityLocationDescription",
    "Sale_Date",
    "Sales_Price",
    "QualifiedCode",
    "Land_Value",
    "Bldg_Value",
    "Total_Value",
    "Zoning",
    "Land_Use_Code",
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
    "landval",
    "improvval",
    "parval",
    "cntyfips",
]

GAPS = [
    "No multi-year sale history on parcels. TaxSQL_Parcels has the last sale only. Tax/Sales_2024 is a single-year extract and is not a sale-history table.",
    "FLU outside Mooresville is mostly a gap. Statesville Land Development Plan 2045 is PDF-only. Troutman, Harmony, Love Valley, and the Davidson Iredell tip have no public FLU FeatureServer. Horizon Plan 2030 Municipal Planning Area values are stubs and are not joined as city FLU.",
    "The TaxSQL Market field is an adjustment factor, not dollar tax.marketValue. Assessed value is Total_Value.",
    "Situs has no ZIP. CityLocationDescription supplies a municipality only when it names one. Mailing CITY can be out of county and is not copied onto the situs.",
    "Municipal zoning is a spatial join. Mooresville uses the town PlanningServices layer. Statesville, Troutman, Harmony, Love Valley, and the Davidson Iredell tip use county Zoning MapServer layers 1, 2, 4, 5, and 6. Unincorporated zoning is layer 0. The parcel Zoning attribute is used only when no polygon contains the representative point.",
    "Mooresville FLU is FCLU F2019_LU_1. Unincorporated FLU is Horizon Plan 2030 FUTURE_LANDUSE when the value is not a Municipal Planning Area stub.",
    "No stable taxweb parcel deep link. The viewer link is MapGeo ?query={PIN} with a trailing .000 stripped. Tax search stays on the BasicSearch form.",
    "NC OneMap FeatureServer/1 where cntyfips='097' is the parcel fallback if TaxSQL_Parcels is down. County and town layers share WKID 102719/2264; tiles are stored in WGS84.",
    "Owner phones and emails are not on these public layers.",
]

PARCEL_GAPS = [
    "No multi-year sale history (last sale only).",
    "Market is an adjustment factor, not a dollar market value.",
]
TOWN_FLU_GAP = "No public FLU layer for this municipality."


def iredell_spec() -> dict:
    return {
        "kind": "iredell",
        "url": f"{PARCEL_LAYER}/query",
        "where": "TaxAcres>=5 AND TaxAcres<=150",
        "source": SOURCE,
        "coverage": "complete-gte-5ac",
        "gaps": list(GAPS),
    }


def normalize_pin(value: Any) -> str | None:
    """Strip a trailing all-zero decimal (.000) used by TaxSQL and MapGeo search."""
    text = _clean(value)
    if not text:
        return None
    if "." in text:
        head, frac = text.split(".", 1)
        if head and frac and set(frac) <= {"0"}:
            return head
    return text


def viewer_url(pin: str) -> str:
    from urllib.parse import quote

    return VIEWER.format(pin=quote(pin, safe=""))


def is_horizon_stub(value: Any) -> bool:
    text = (_clean(value) or "").lower()
    return "municipal planning area" in text


def assemble_situs(attrs: dict) -> str | None:
    parts: list[str] = []
    for key in ("HouseNumber", "SDIR", "STREET", "STYPE", "ST_SUFFIX"):
        text = _clean(attrs.get(key))
        if not text or text in {"0", "00"}:
            continue
        parts.append(text)
    return " ".join(parts) or None


def situs_city_hint(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    return {
        "statesville": "Statesville",
        "troutman": "Troutman",
        "mooresville": "Mooresville",
        "harmony": "Harmony",
        "love valley": "Love Valley",
        "davidson": "Davidson",
    }.get(text.lower())


def parse_sale_date(value: Any) -> str | None:
    text = _clean(value)
    if text:
        match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if match:
            month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return text
    number = _num(value)
    if number is not None and number > 10_000_000_000:
        try:
            moment = datetime.fromtimestamp(number / 1000, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        if 1900 <= moment.year <= 2100:
            return moment.date().isoformat()
    return None


def market_value_dollars(attrs: dict) -> None:
    """TaxSQL Market / MarketFactor is not a dollar market value."""
    del attrs
    return None


def map_taxsql_attributes(attrs: dict) -> dict | None:
    pin = normalize_pin(attrs.get("PIN")) or normalize_pin(attrs.get("ACCOUNT"))
    acres = _num(attrs.get("TaxAcres"))
    if not pin or acres is None:
        return None
    owner = _clean(attrs.get("Jan1Own1")) or _clean(attrs.get("Name"))
    owner2 = _clean(attrs.get("Jan1Own2")) if _clean(attrs.get("Jan1Own1")) else None
    line2_parts = [_clean(attrs.get("ADD2")), _clean(attrs.get("ADD3"))]
    price = _num(attrs.get("Sales_Price"))
    if price is not None and price <= 0:
        price = None
    assessed = _num(attrs.get("Total_Value"))
    if assessed is not None and assessed <= 0:
        assessed = None
    code = _clean(attrs.get("CityLocationCode"))
    return {
        "parcelId": pin,
        "acres": acres,
        "owner": owner,
        "owner2": owner2,
        "situs": assemble_situs(attrs),
        "city": situs_city_hint(attrs.get("CityLocationDescription")),
        "zip": None,
        "dor": _clean(attrs.get("Land_Use_Code")),
        "salePrice": price,
        "saleDate": parse_sale_date(attrs.get("Sale_Date")),
        "saleQualified": _clean(attrs.get("QualifiedCode")),
        "marketValue": market_value_dollars(attrs),
        "assessed": assessed,
        "mail1": _clean(attrs.get("ADD1")),
        "mail2": ", ".join(part for part in line2_parts if part) or None,
        "mailCity": _clean(attrs.get("CITY")),
        "mailState": _clean(attrs.get("STATE")),
        "mailZip": _zip(attrs.get("ZIP")),
        "zoningAttribute": _clean(attrs.get("Zoning")),
        "jurisdictionCode": None if code in {None, "00", "0"} else code,
    }


def map_onemap_attributes(attrs: dict) -> dict | None:
    pin = normalize_pin(attrs.get("parno"))
    acres = _num(attrs.get("gisacres"))
    if not pin or acres is None:
        return None
    assessed = _num(attrs.get("parval"))
    if assessed is not None and assessed <= 0:
        assessed = None
    sale = parse_sale_date(attrs.get("saledatetx")) or parse_sale_date(attrs.get("saledate"))
    return {
        "parcelId": pin,
        "acres": acres,
        "owner": _clean(attrs.get("ownname")),
        "owner2": None,
        "situs": _clean(attrs.get("siteadd")),
        "city": situs_city_hint(attrs.get("scity")) or _clean(attrs.get("scity")),
        "zip": None,
        "dor": None,
        "salePrice": None,
        "saleDate": sale,
        "saleQualified": None,
        "marketValue": None,
        "assessed": assessed,
        "mail1": _clean(attrs.get("mailadd")),
        "mail2": None,
        "mailCity": _clean(attrs.get("mcity")),
        "mailState": _clean(attrs.get("mstate")),
        "mailZip": _zip(attrs.get("mzip")),
        "zoningAttribute": None,
        "jurisdictionCode": None,
    }


def zoning_from_mooresville(attrs: dict) -> tuple[str | None, str | None]:
    display = _clean(attrs.get("ZDISPLAY"))
    tax = _clean(attrs.get("ZoningTax"))
    if tax and (not display or display.upper() in OVERLAY_ONLY):
        return tax, display
    if display:
        return display, tax if tax and tax != display else None
    return tax, None


def zoning_from_county(attrs: dict) -> tuple[str | None, str | None]:
    code = _clean(attrs.get("ZONING")) or _clean(attrs.get("ZDISPLAY"))
    display = _clean(attrs.get("ZDISPLAY"))
    district = display if display and display != code else None
    return code, district


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
        for feature in self.buckets.get((_cell(x, self.cell), _cell(y, self.cell)), []):
            if contains_point(feature.get("geometry"), x, y):
                return feature
        for feature in self.broad:
            if contains_point(feature.get("geometry"), x, y):
                return feature
        return None


def index_features(features: list[dict]) -> SpatialIndex:
    index = SpatialIndex()
    for feature in features:
        index.add(feature)
    return index


def apply_land_use(
    feature: dict,
    *,
    zoning_layers: list[dict],
    city_limits: SpatialIndex | None,
    fclu: SpatialIndex | None,
    horizon: SpatialIndex | None,
) -> dict[str, int]:
    """Spatial-join zoning and FLU. Returns counters for this one parcel."""
    props = feature["properties"]
    lon, lat = props["centroid"]
    counts = {"zoning": 0, "attribute": 0, "flu": 0, "town": "", "zoningName": ""}
    if not props.get("situsCity") and city_limits is not None:
        limits = city_limits.hit(lon, lat)
        if limits:
            props["situsCity"] = _title_city((limits.get("properties") or {}).get("NAME"))

    zoning_name = None
    for layer in zoning_layers:
        hit = layer["index"].hit(lon, lat)
        if not hit:
            continue
        if layer["kind"] == "mooresville":
            code, district = zoning_from_mooresville(hit["properties"])
        else:
            code, district = zoning_from_county(hit["properties"])
        if not code:
            continue
        props["zoningCode"] = code
        props["zoningDistrict"] = district
        props["jurisdictionPrefix"] = layer["name"]
        zoning_name = layer["name"]
        counts["zoning"] = 1
        counts["zoningName"] = layer["name"]
        break
    if counts["zoning"] == 0 and props.get("zoningAttribute"):
        props["zoningCode"] = props["zoningAttribute"]
        counts["attribute"] = 1

    town = _town_name(props.get("situsCity"), zoning_name or props.get("jurisdictionPrefix"))
    counts["town"] = town or ""
    flu = None
    if town == "Mooresville" and fclu is not None:
        hit = fclu.hit(lon, lat)
        code = _clean((hit or {}).get("properties", {}).get("F2019_LU_1")) if hit else None
        if code:
            flu = {"code": code, "label": code, "jurisdiction": "Mooresville", "source": "mooresville-fclu"}
    elif town is None and horizon is not None:
        hit = horizon.hit(lon, lat)
        value = _clean((hit or {}).get("properties", {}).get("FUTURE_LANDUSE")) if hit else None
        if value and not is_horizon_stub(value):
            flu = {
                "code": value,
                "label": value,
                "jurisdiction": "Iredell",
                "source": "iredell-horizon-2030",
            }
    props["flu"] = flu
    if flu:
        counts["flu"] = 1
    gaps = list(PARCEL_GAPS)
    if town in TOWNS_WITHOUT_FLU:
        gaps.append(TOWN_FLU_GAP)
    props["dataGaps"] = gaps
    props.pop("zoningAttribute", None)
    return counts


def download_iredell(county: dict, markets: list[str], spec: dict) -> dict:
    import seed_market_parcels as seed

    cache_path = seed.CACHE_DIR / f"{county['fips']}.json"
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = seed.json.loads(cache_path.read_text())
        if cached.get("version") == CACHE_VERSION and cached.get("features"):
            print(f"  cache hit {len(cached['features'])}", flush=True)
            return _write(seed, county, markets, cached)

    print(f"Pulling {county['name']} via TaxSQL_Parcels", flush=True)
    used_fallback = False
    fallback_reason = None
    try:
        expected = seed.count_where(f"{PARCEL_LAYER}/query", spec["where"])
        if expected <= 0:
            raise RuntimeError("TaxSQL_Parcels returned no 5–150 acre rows")
        raw = _pull(seed, f"{PARCEL_LAYER}/query", spec["where"], TAX_FIELDS)
        features, dropped = _features_from_raw(seed, raw, county, markets, map_taxsql_attributes, SOURCE)
        source = SOURCE
        query_url = f"{PARCEL_LAYER}/query"
    except Exception as exc:  # noqa: BLE001
        used_fallback = True
        fallback_reason = str(exc)
        print(f"  TaxSQL failed ({exc}); falling back to NC OneMap cntyfips 097", flush=True)
        where = "cntyfips='097' AND gisacres>=5 AND gisacres<=150"
        expected = seed.count_where(f"{ONEMAP_LAYER}/query", where)
        raw = _pull(seed, f"{ONEMAP_LAYER}/query", where, ONEMAP_FIELDS)
        features, dropped = _features_from_raw(seed, raw, county, markets, map_onemap_attributes, FALLBACK_SOURCE)
        source = FALLBACK_SOURCE
        query_url = f"{ONEMAP_LAYER}/query"

    joins = _load_joins(seed)
    stats = _enrich_all(features, joins)
    if not used_fallback and stats["zoningPolygons"] > 100 and stats["zoningJoined"] == 0:
        raise RuntimeError("Iredell zoning polygons were fetched but none contained a parcel point")
    gaps = list(GAPS)
    if used_fallback:
        gaps.insert(0, f"TaxSQL_Parcels was unavailable ({fallback_reason}). This extract used NC OneMap cntyfips 097.")
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
        f"flu {stats.get('fluJoined', 0)} attribute-only {stats.get('attributeZoning', 0)}",
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
            "viewerLinkTemplate": VIEWER,
            "appraiserSearchUrl": "https://taxweb.iredellcountync.gov/PublicAccess/BasicSearch.aspx",
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
            sale_qualified=mapped["saleQualified"],
            market_value=mapped["marketValue"],
            assessed=mapped["assessed"],
            mail1=mapped["mail1"],
            mail2=mapped["mail2"],
            mail_city=mapped["mailCity"],
            mail_state=mapped["mailState"],
            mail_zip=mapped["mailZip"],
        )
        props = feature["properties"]
        props["ownerName2"] = mapped["owner2"]
        props["jurisdictionCode"] = mapped["jurisdictionCode"]
        props["appraiserUrl"] = viewer_url(mapped["parcelId"])
        props["zoningAttribute"] = mapped["zoningAttribute"]
        previous = by_id.get(mapped["parcelId"])
        if previous is None or (props["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[mapped["parcelId"]] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def _pull(seed: Any, url: str, where: str, fields: list[str]) -> list[dict]:
    ids = seed.fetch_object_ids(url, where)
    print(f"  {url.split('/rest/')[-1]} ids {len(ids)}", flush=True)
    return seed.fetch_by_ids(url, ids, fields, batch=60)


def _load_joins(seed: Any) -> dict:
    zoning_catalog = [
        {
            "name": "Mooresville",
            "kind": "mooresville",
            "url": f"{MOORESVILLE_ZONING}/query",
            "fallback": f"{MOORESVILLE_ZONING_MIRROR}/query",
            "fields": ["ZDISPLAY", "ZoningTax", "CaseNumber", "ApprovalDate", "OLDZONING"],
            "layerUrl": MOORESVILLE_ZONING,
            "independentGis": True,
            "fluUrl": MOORESVILLE_FCLU,
            "fluGap": None,
        },
        {
            "name": "Statesville",
            "kind": "county",
            "url": f"{ZONING_ROOT}/1/query",
            "fields": ["ZONING", "ZDISPLAY", "JURISDIC", "CUD", "PRD"],
            "layerUrl": f"{ZONING_ROOT}/1",
            "independentGis": False,
            "fluUrl": None,
            "fluGap": "Land Development Plan 2045 is PDF-only. No public FLU FeatureServer.",
        },
        {
            "name": "Troutman",
            "kind": "county",
            "url": f"{ZONING_ROOT}/2/query",
            "fields": ["ZONING", "ZDISPLAY", "JURISDIC"],
            "layerUrl": f"{ZONING_ROOT}/2",
            "independentGis": False,
            "fluUrl": None,
            "fluGap": "No town FLU FeatureServer. Horizon Municipal Planning Area is a stub.",
        },
        {
            "name": "Harmony",
            "kind": "county",
            "url": f"{ZONING_ROOT}/4/query",
            "fields": ["ZONING", "ZDISPLAY", "JURISDIC"],
            "layerUrl": f"{ZONING_ROOT}/4",
            "independentGis": False,
            "fluUrl": None,
            "fluGap": "No town FLU FeatureServer.",
        },
        {
            "name": "Love Valley",
            "kind": "county",
            "url": f"{ZONING_ROOT}/5/query",
            "fields": ["ZONING", "ZDISPLAY", "JURISDIC"],
            "layerUrl": f"{ZONING_ROOT}/5",
            "independentGis": False,
            "fluUrl": None,
            "fluGap": "No town FLU FeatureServer.",
        },
        {
            "name": "Davidson",
            "kind": "county",
            "url": f"{ZONING_ROOT}/6/query",
            "fields": ["ZONING", "ZDISPLAY", "JURISDIC"],
            "layerUrl": f"{ZONING_ROOT}/6",
            "independentGis": False,
            "fluUrl": None,
            "fluGap": "Iredell tip only. No Iredell-side FLU FeatureServer. Mecklenburg Davidson zoning is not applied to Iredell parcels.",
        },
        {
            "name": "Iredell",
            "kind": "county",
            "url": f"{ZONING_ROOT}/0/query",
            "fields": ["ZONING", "ZDISPLAY", "JURISDIC", "CUD", "PRD"],
            "layerUrl": f"{ZONING_ROOT}/0",
            "independentGis": False,
            "fluUrl": f"{ZONING_ROOT}/7",
            "fluGap": None,
            "unincorporated": True,
        },
    ]
    zoning_layers = []
    municipalities = []
    unincorporated = None
    for spec in zoning_catalog:
        features, used_url, error = _pull_polygons(seed, spec["url"], spec["fields"])
        note = None
        if error and spec.get("fallback"):
            print(f"  {spec['name']} zoning fallback ({error})", flush=True)
            features, used_url, error = _pull_polygons(seed, spec["fallback"], spec["fields"])
            note = "Town host failed; used the county Zoning/3 mirror."
        if error:
            print(f"  {spec['name']} zoning unavailable: {error}", flush=True)
        layer = {
            "name": spec["name"],
            "kind": spec["kind"],
            "index": index_features(features),
            "unincorporated": bool(spec.get("unincorporated")),
        }
        zoning_layers.append(layer)
        record = {
            "name": spec["name"],
            "independentGis": spec["independentGis"],
            "zoningUrl": spec["layerUrl"] if not note else MOORESVILLE_ZONING_MIRROR,
            "fluUrl": spec.get("fluUrl"),
            "fluGap": spec.get("fluGap"),
            "join": "spatial city zoning/FLU to county parcels (WKID 102719/2264)",
            "zoningFeatures": len(features),
            "zoningJoined": 0,
            "fluJoined": 0,
        }
        if note:
            record["note"] = note
        if spec.get("unincorporated"):
            unincorporated = {
                "zoningUrl": spec["layerUrl"],
                "fluUrl": spec.get("fluUrl"),
                "zoningFeatures": len(features),
                "fluFeatures": 0,
                "zoningJoined": 0,
                "fluJoined": 0,
                "note": "Horizon Plan 2030 for unincorporated FLU. Municipal Planning Area values are stubs and are not joined.",
            }
        else:
            municipalities.append(record)

    fclu_features, _, fclu_error = _pull_polygons(seed, f"{MOORESVILLE_FCLU}/query", ["F2019_LU_1"])
    if fclu_error:
        print(f"  Mooresville FCLU unavailable: {fclu_error}", flush=True)
    horizon_features, _, horizon_error = _pull_polygons(seed, f"{ZONING_ROOT}/7/query", ["FUTURE_LANDUSE"])
    if horizon_error:
        print(f"  Horizon FLU unavailable: {horizon_error}", flush=True)
    limits, _, limits_error = _pull_polygons(seed, f"{CITY_LIMITS}/query", ["NAME"])
    if limits_error:
        print(f"  City limits unavailable: {limits_error}", flush=True)
    for record in municipalities:
        if record["name"] == "Mooresville":
            record["fluFeatures"] = len(fclu_features)
            record["fluUrl"] = MOORESVILLE_FCLU
    if unincorporated is not None:
        unincorporated["fluFeatures"] = len(horizon_features)
    return {
        "zoning": zoning_layers,
        "cityLimits": index_features(limits),
        "fclu": index_features(fclu_features),
        "horizon": index_features(horizon_features),
        "municipalities": municipalities,
        "unincorporated": unincorporated,
        "zoningPolygons": sum(item["zoningFeatures"] for item in municipalities) + (unincorporated or {}).get("zoningFeatures", 0),
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
    attribute = 0
    by_name = {item["name"]: item for item in joins["municipalities"]}
    unincorporated = joins.get("unincorporated")
    for feature in features:
        counts = apply_land_use(
            feature,
            zoning_layers=joins["zoning"],
            city_limits=joins.get("cityLimits"),
            fclu=joins.get("fclu"),
            horizon=joins.get("horizon"),
        )
        zoning_joined += counts["zoning"]
        flu_joined += counts["flu"]
        attribute += counts["attribute"]
        zoning_name = counts["zoningName"]
        if zoning_name in by_name and counts["zoning"]:
            by_name[zoning_name]["zoningJoined"] += 1
        if unincorporated is not None and zoning_name == "Iredell" and counts["zoning"]:
            unincorporated["zoningJoined"] += 1
        source = (feature["properties"].get("flu") or {}).get("source")
        if source == "mooresville-fclu" and "Mooresville" in by_name:
            by_name["Mooresville"]["fluJoined"] += 1
        if unincorporated is not None and source == "iredell-horizon-2030":
            unincorporated["fluJoined"] += 1
    return {
        "zoningJoined": zoning_joined,
        "fluJoined": flu_joined,
        "attributeZoning": attribute,
        "zoningPolygons": joins.get("zoningPolygons") or 0,
        "municipalities": joins["municipalities"],
        "unincorporated": unincorporated,
    }


def _town_name(city: str | None, prefix: str | None) -> str | None:
    if city in TOWNS:
        return city
    if prefix in TOWNS:
        return prefix
    return None


def _title_city(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    return situs_city_hint(text) or situs_city_hint(text.replace("_", " "))


def _cell(value: float, cell: float) -> int:
    import math

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
