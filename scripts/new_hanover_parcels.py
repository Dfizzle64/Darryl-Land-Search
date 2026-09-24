"""New Hanover County (Wilmington MSA) parcel extract.

Geometry is county Parcels/0 in the 5–150 acre band. Owner, situs, last sale,
and appraised value come from IASTAX/1 joined on MAPIDKEY. Zoning is city-first
for Wilmington, Carolina Beach, and Wrightsville Beach, then county Zoning/1.
PlanNHC_FLUM/8 place types cover unincorporated land only.

Create Wilmington future land use has no feature service. Wilmington
Planning/LandUse is existing land use and is not joined as FLU. Kure Beach
does not publish zoning polygons.

OZ 2.0 nomination eligibility is not a designated Qualified Opportunity Zone.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from parcel_geometry import contains_point, esri_rings_to_geojson

ROOT = Path(__file__).resolve().parents[1]
FIPS = "37129"
SOURCE = "nc-new-hanover-parcels-37129"
FALLBACK_SOURCE = "nc-onemap-37129"
CACHE_VERSION = 1

PARCEL_LAYER = "https://gis.nhcgov.com/server/rest/services/Layers/Parcels/FeatureServer/0"
TAX_LAYER = "https://gis.nhcgov.com/server/rest/services/Layers/IASTAX/FeatureServer/1"
COUNTY_ZONING = "https://gis.nhcgov.com/server/rest/services/Layers/Zoning/FeatureServer/1"
MUNI_LAYER = "https://gis.nhcgov.com/server/rest/services/Layers/MuniLimits/FeatureServer/0"
FLUM_LAYER = "https://gis.nhcgov.com/server/rest/services/Thematic/PlanNHC_FLUM/MapServer/8"
WILMINGTON_ZONING = "https://gis.wilmingtonnc.gov/arcgis/rest/services/Planning/Zoning/MapServer/0"
CAROLINA_ZONING = "https://cw.carolinabeach.org/arcgis/rest/services/GISViewer/GIS_Viewer/MapServer/21"
WRIGHTSVILLE_ZONING = (
    "https://services3.arcgis.com/XyPkMiF0OxEhc77I/arcgis/rest/services/WrightsvilleBeachZoning/FeatureServer/0"
)
ONEMAP_LAYER = "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1"
HUD_OZ_QUERY = (
    "https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/FeatureServer/13/query"
)
OZ2_PACKS = ROOT / "data" / "fixtures" / "oz2-eligible-packs.geojson"
TAX_SEARCH = "https://etax.nhcgov.com/pt/main/home.aspx"

PARCEL_FIELDS = ["PID", "PIN", "MAPID", "MAPIDKEY", "ACRES"]
TAX_FIELDS = [
    "MAPIDKEY",
    "PARID",
    "OWN1",
    "OWNER_STREET",
    "OWNER_STREETTYPE",
    "OWNER_DIR",
    "OWNER_UNITDESC",
    "OWNER_UNITNO",
    "OWNER_CITY",
    "OWNER_STATE",
    "OWNER_ZIP",
    "OWNER_ADDR1",
    "OWNER_ADDR2",
    "ADRNO",
    "ADRDIR",
    "ADRSTR",
    "ADRSUF",
    "UNITNO",
    "CITYNAME",
    "MUNI",
    "ZONING",
    "LUC",
    "APRTOT",
    "SALE_DATE",
    "SALE_PRICE",
]
ONEMAP_FIELDS = ["parno", "ownname", "siteadd", "scity", "gisacres", "parval", "landval", "saledatetx", "cntyfips"]

CITY_FIRST = ("Wilmington", "Carolina Beach", "Wrightsville Beach")
PLACEHOLDER_ZONING = {"CITY", "WB", "CB", "KB"}
MUNI_NAMES = {
    "WILMINGTON": "Wilmington",
    "CAROLINA BEACH": "Carolina Beach",
    "WRIGHTSVILLE BEACH": "Wrightsville Beach",
    "KURE BEACH": "Kure Beach",
}

GAPS = [
    "Geometry is New Hanover Parcels/FeatureServer/0 where ACRES is 5.0–150.0. NC OneMap cntyfips='129' is the fallback if that layer fails.",
    "IASTAX/1 is joined on MAPIDKEY. APRTOT is the appraised total, not tax.marketValue, a taxable value, or a tax bill. SALE_PRICE of 0 is missing. There is no qualified-sale flag and no multi-year sale history.",
    "Zoning is city-first. Wilmington Planning/Zoning/0, Carolina Beach GIS_Viewer/21, and Wrightsville Beach WrightsvilleBeachZoning/0 override county Zoning/1. County codes CITY, WB, CB, and KB are municipal stamps, not districts, and are not stored.",
    "Kure Beach zoning polygons are not published. Those parcels stay unzoned instead of receiving a county stamp.",
    "PlanNHC_FLUM/8 place types are joined only outside municipal limits. Create Wilmington future land use has no feature service. Wilmington Planning/LandUse is existing land use and is not joined as FLU. Carolina Beach, Wrightsville Beach, and Kure Beach have no public FLU feature service.",
    "OZ 2.0 eligibility (Rev. Proc. 2026-14) is a separate centroid join from current HUD/Treasury designated QOZs. Eligible is not designated.",
    "No stable etax parcel deep link. The link is the Property Assessment search home. Owner phones and emails are not on these layers. Situs has no ZIP.",
]

WILMINGTON_FLU_GAP = "Create Wilmington future land use has no public feature service."
KURE_ZONING_GAP = "Kure Beach zoning polygons are not published."
OTHER_CITY_FLU_GAP = "No public municipal future land use feature service. PlanNHC place types are not applied inside city limits."
TAX_GAP = "No separate market value, taxable value, or tax bill on IASTAX. Assessed value is APRTOT."


def new_hanover_spec() -> dict:
    return {
        "kind": "new-hanover",
        "url": f"{PARCEL_LAYER}/query",
        "where": "ACRES>=5 AND ACRES<=150",
        "source": SOURCE,
        "coverage": "complete-gte-5ac",
        "gaps": list(GAPS),
    }


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\u00a0", " ").strip()
    return text or None


def num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        return None
    return parsed


def zip_str(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return text[:10]


def title_place(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    return " ".join(part.capitalize() if part.isupper() else part for part in text.split())


def mapidkey_from_pin(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    if "." in text:
        head, frac = text.split(".", 1)
        if head and frac and set(frac) <= {"0"}:
            return head
    return text


def money(value: Any) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def parse_sale_date(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    if len(text) >= 10 and text[4] == "-" and text[:4].isdigit():
        year = int(text[:4])
        if 1900 <= year <= 2100:
            return text[:10]
    return None


def parse_sale_price(value: Any) -> float | None:
    return money(value)


def assemble_situs(attrs: dict) -> str | None:
    number = num(attrs.get("ADRNO"))
    parts: list[str] = []
    if number is not None and number > 0:
        parts.append(str(int(number)))
    for key in ("ADRDIR", "ADRSTR", "ADRSUF"):
        text = clean(attrs.get(key))
        if text and text not in {"0", "00"}:
            parts.append(text)
    line = " ".join(parts)
    unit = clean(attrs.get("UNITNO"))
    if unit and unit not in {"0", "00"}:
        line = f"{line} {unit}".strip()
    return line or None


def assemble_mail(attrs: dict) -> tuple[str | None, str | None]:
    line1 = clean(attrs.get("OWNER_ADDR1"))
    line2 = clean(attrs.get("OWNER_ADDR2"))
    if line1:
        return line1, line2
    street = clean(attrs.get("OWNER_STREET"))
    if not street:
        return None, line2
    bits = [street]
    for key in ("OWNER_STREETTYPE", "OWNER_DIR"):
        text = clean(attrs.get(key))
        if text:
            bits.append(text)
    line = " ".join(bits)
    unit_bits = [clean(attrs.get("OWNER_UNITDESC")), clean(attrs.get("OWNER_UNITNO"))]
    unit = " ".join(bit for bit in unit_bits if bit)
    if unit:
        line = f"{line} {unit}"
    return line, line2


def wrightsville_code(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    suffix = " Zoning District"
    if text.lower().endswith(suffix.lower()):
        text = text[: -len(suffix)].strip()
    return text or None


def is_placeholder_zoning(value: Any) -> bool:
    text = clean(value)
    return bool(text and text.upper() in PLACEHOLDER_ZONING)


def municipality_name(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    if text.upper() == "UNINCORPORATED":
        return None
    return MUNI_NAMES.get(text.upper(), title_place(text))


def county_zoning_from(attrs: dict) -> tuple[str | None, str | None]:
    code = clean(attrs.get("ZONING"))
    if not code or is_placeholder_zoning(code):
        return None, None
    display = clean(attrs.get("ZONINGTXT"))
    district = display if display and display != code else None
    return code, district


def wilmington_zoning_from(attrs: dict) -> tuple[str | None, str | None]:
    code = clean(attrs.get("Zoning"))
    if not code or is_placeholder_zoning(code):
        return None, None
    case = clean(attrs.get("CaseNumber"))
    return code, case


def carolina_zoning_from(attrs: dict) -> tuple[str | None, str | None]:
    code = clean(attrs.get("ZONE"))
    if not code or is_placeholder_zoning(code):
        return None, None
    return code, None


def map_tax_attributes(attrs: dict) -> dict:
    mail1, mail2 = assemble_mail(attrs)
    return {
        "owner": clean(attrs.get("OWN1")),
        "situs": assemble_situs(attrs),
        "city": title_place(attrs.get("CITYNAME")),
        "mail1": mail1,
        "mail2": mail2,
        "mailCity": title_place(attrs.get("OWNER_CITY")),
        "mailState": clean(attrs.get("OWNER_STATE")),
        "mailZip": zip_str(attrs.get("OWNER_ZIP")),
        "saleDate": parse_sale_date(attrs.get("SALE_DATE")),
        "salePrice": parse_sale_price(attrs.get("SALE_PRICE")),
        "assessed": money(attrs.get("APRTOT")),
        "dor": clean(attrs.get("LUC")),
        "taxMuni": clean(attrs.get("MUNI")),
        "taxZoning": clean(attrs.get("ZONING")),
    }


def _cell(value: float, size: float) -> int:
    return int(value // size)


def _bbox(feature: dict) -> tuple[float, float, float, float] | None:
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []

    def walk(node: Any, acc: list[tuple[float, float]]) -> None:
        if isinstance(node, (int, float)):
            return
        if len(node) >= 2 and isinstance(node[0], (int, float)) and isinstance(node[1], (int, float)):
            acc.append((float(node[0]), float(node[1])))
            return
        for child in node:
            walk(child, acc)

    points: list[tuple[float, float]] = []
    walk(coords, points)
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


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
        if not isinstance(feature, dict):
            raise TypeError(f"overlay feature is {type(feature).__name__}: {feature!r}"[:240])
        geometry = feature.get("geometry")
        if geometry is not None and not isinstance(geometry, dict):
            raise TypeError(f"overlay geometry is {type(geometry).__name__}")
        index.add(feature)
    return index


def _zone_from(kind: str, attrs: dict) -> tuple[str | None, str | None]:
    if kind == "wilmington":
        return wilmington_zoning_from(attrs)
    if kind == "carolina":
        return carolina_zoning_from(attrs)
    if kind == "wrightsville":
        code = wrightsville_code(attrs.get("Name"))
        if not code or is_placeholder_zoning(code):
            return None, None
        return code, None
    return county_zoning_from(attrs)


def apply_overlays(
    feature: dict,
    *,
    municipalities: SpatialIndex | None,
    city_zoning: dict[str, SpatialIndex],
    county_zoning: SpatialIndex | None,
    flum: SpatialIndex | None,
    designated: SpatialIndex | None,
    eligible: SpatialIndex | None,
    designated_source: str | None,
) -> dict[str, str | int]:
    """Join zoning, place types, and the two opportunity-zone layers."""
    props = feature["properties"]
    lon, lat = props["centroid"]
    counts: dict[str, str | int] = {"zoning": 0, "flu": 0, "eligible": 0, "designated": 0, "town": ""}
    muni_hit = municipalities.hit(lon, lat) if municipalities is not None else None
    muni_props = (muni_hit or {}).get("properties") or {}
    jurisdiction = municipality_name(muni_props.get("CITY"))
    juris_code = clean(muni_props.get("JURIS"))
    muni_known = muni_hit is not None

    city_layer = {
        "Wilmington": "wilmington",
        "Carolina Beach": "carolina",
        "Wrightsville Beach": "wrightsville",
    }
    chosen_name = None
    chosen_kind = None
    chosen_attrs = None
    if jurisdiction in city_layer:
        kind = city_layer[jurisdiction]
        layer = city_zoning.get(jurisdiction)
        hit = layer.hit(lon, lat) if layer is not None else None
        if hit:
            chosen_name, chosen_kind, chosen_attrs = jurisdiction, kind, hit.get("properties") or {}
    elif jurisdiction != "Kure Beach":
        # No municipal hit: city polygons win before the county layer. A known
        # unincorporated parcel stays on county Zoning/1.
        if not muni_known:
            for name in CITY_FIRST:
                layer = city_zoning.get(name)
                if layer is None:
                    continue
                hit = layer.hit(lon, lat)
                if not hit:
                    continue
                code, _district = _zone_from(city_layer[name], hit.get("properties") or {})
                if not code:
                    continue
                chosen_name, chosen_kind, chosen_attrs = name, city_layer[name], hit.get("properties") or {}
                jurisdiction = name
                break
        if chosen_name is None and county_zoning is not None:
            hit = county_zoning.hit(lon, lat)
            if hit:
                chosen_name, chosen_kind, chosen_attrs = "New Hanover", "county", hit.get("properties") or {}

    if chosen_kind and chosen_attrs is not None:
        code, district = _zone_from(chosen_kind, chosen_attrs)
        if code:
            props["zoningCode"] = code
            props["zoningDistrict"] = district
            props["jurisdictionPrefix"] = chosen_name
            counts["zoning"] = 1
    if jurisdiction in (*CITY_FIRST, "Kure Beach"):
        props["jurisdictionPrefix"] = jurisdiction
    elif muni_known and jurisdiction is None and not props.get("jurisdictionPrefix"):
        props["jurisdictionPrefix"] = "New Hanover"
    if jurisdiction is None and props.get("jurisdictionPrefix") in CITY_FIRST:
        jurisdiction = props.get("jurisdictionPrefix")
    if juris_code and jurisdiction in {None, "New Hanover"}:
        props["jurisdictionCode"] = juris_code
    elif jurisdiction == "Wilmington":
        props["jurisdictionCode"] = "WM"
    elif jurisdiction == "Carolina Beach":
        props["jurisdictionCode"] = "CB"
    elif jurisdiction == "Wrightsville Beach":
        props["jurisdictionCode"] = "WB"
    elif jurisdiction == "Kure Beach":
        props["jurisdictionCode"] = "KB"
    elif juris_code:
        props["jurisdictionCode"] = juris_code

    counts["town"] = jurisdiction or ""
    flu = None
    if jurisdiction is None and flum is not None:
        hit = flum.hit(lon, lat)
        place = clean((hit or {}).get("properties", {}).get("PlaceType")) if hit else None
        if place:
            flu = {
                "code": place,
                "label": place,
                "jurisdiction": "New Hanover",
                "source": "plan-nhc-flum-8",
            }
    props["flu"] = flu
    if flu:
        counts["flu"] = 1

    gaps = [TAX_GAP]
    if jurisdiction == "Wilmington":
        gaps.append(WILMINGTON_FLU_GAP)
    elif jurisdiction == "Kure Beach":
        gaps.append(KURE_ZONING_GAP)
        gaps.append(OTHER_CITY_FLU_GAP)
    elif jurisdiction in {"Carolina Beach", "Wrightsville Beach"}:
        gaps.append(OTHER_CITY_FLU_GAP)
    props["dataGaps"] = gaps

    designated_hit = designated.hit(lon, lat) if designated is not None else None
    if designated is not None:
        if designated_hit:
            dprops = designated_hit.get("properties") or {}
            props["opportunityZone"] = {
                "inOpportunityZone": True,
                "tractGeoid": dprops.get("tractGeoid"),
                "tractName": dprops.get("name"),
                "source": designated_source,
                "designatedRural": dprops.get("rural"),
            }
            counts["designated"] = 1
        else:
            props["opportunityZone"] = {
                "inOpportunityZone": False,
                "tractGeoid": None,
                "tractName": None,
                "source": designated_source,
                "designatedRural": None,
            }
    eligible_hit = eligible.hit(lon, lat) if eligible is not None else None
    if eligible is not None:
        if eligible_hit:
            eprops = eligible_hit.get("properties") or {}
            rural = eprops.get("rural")
            props["oz2Eligibility"] = {
                "eligible": True,
                "rural": True if rural is True else False if rural is False else None,
                "tractGeoid": eprops.get("tractGeoid"),
                "tractName": eprops.get("name"),
                "designation": "eligible-for-nomination",
                "source": eprops.get("source") or "rev-proc-2026-14",
            }
            counts["eligible"] = 1
        else:
            props["oz2Eligibility"] = {
                "eligible": False,
                "rural": None,
                "tractGeoid": None,
                "tractName": None,
                "designation": "not-eligible",
                "source": "rev-proc-2026-14",
            }
    return counts


def esri_feature(item: dict, properties: dict) -> dict | None:
    geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
    if not geometry:
        return None
    return {"type": "Feature", "properties": properties, "geometry": geometry}


def viewer_url() -> str:
    return TAX_SEARCH


def _quote_key(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def download_new_hanover(county: dict, markets: list[str], spec: dict) -> dict:
    import seed_market_parcels as seed

    cache_path = seed.CACHE_DIR / f"{county['fips']}.json"
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = json.loads(cache_path.read_text())
        if cached.get("version") == CACHE_VERSION and cached.get("features"):
            print(f"  cache hit {len(cached['features'])}", flush=True)
            return _write(seed, county, markets, cached)

    print(f"Pulling {county['name']} via Parcels/0 + IASTAX/1", flush=True)
    used_fallback = False
    fallback_reason = None
    try:
        where = spec["where"]
        expected = seed.count_where(f"{PARCEL_LAYER}/query", where)
        if expected <= 0:
            raise RuntimeError("Parcels/0 returned no 5–150 acre rows")
        raw = _pull(seed, f"{PARCEL_LAYER}/query", where, PARCEL_FIELDS)
        features, dropped = _features_from_parcels(seed, raw, county, markets)
        source = SOURCE
        query_url = f"{PARCEL_LAYER}/query"
    except Exception as exc:  # noqa: BLE001
        used_fallback = True
        fallback_reason = str(exc)
        print(f"  Parcels/0 failed ({exc}); falling back to NC OneMap cntyfips 129", flush=True)
        where = "cntyfips='129' AND gisacres>=5 AND gisacres<=150"
        expected = seed.count_where(f"{ONEMAP_LAYER}/query", where)
        raw = _pull(seed, f"{ONEMAP_LAYER}/query", where, ONEMAP_FIELDS)
        features, dropped = _features_from_onemap(seed, raw, county, markets)
        source = FALLBACK_SOURCE
        query_url = f"{ONEMAP_LAYER}/query"

    tax_rows = _load_tax(seed, [feature["properties"]["mapIdKey"] for feature in features if feature["properties"].get("mapIdKey")])
    for feature in features:
        key = feature["properties"].get("mapIdKey")
        row = tax_rows.get(key) if key else None
        if not row:
            continue
        mapped = map_tax_attributes(row)
        props = feature["properties"]
        props["ownerName"] = mapped["owner"] or props.get("ownerName")
        props["situsAddress"] = mapped["situs"] or props.get("situsAddress")
        props["situsCity"] = mapped["city"] or props.get("situsCity")
        props["dorCode"] = mapped["dor"]
        props["lastSale"] = {"date": mapped["saleDate"], "price": mapped["salePrice"], "qualified": None}
        props["tax"] = {
            "marketValue": None,
            "assessedValue": mapped["assessed"],
            "taxableValue": None,
            "taxes": None,
        }
        props["mailingAddress"] = {
            "line1": mapped["mail1"],
            "line2": mapped["mail2"],
            "city": mapped["mailCity"],
            "state": mapped["mailState"],
            "zip": mapped["mailZip"],
        }
        props.pop("mapIdKey", None)

    for feature in features:
        feature["properties"].pop("mapIdKey", None)

    joins = _load_joins(seed)
    stats = _enrich_all(features, joins)
    if not used_fallback and stats["wilmingtonZoningFeatures"] > 50 and stats["wilmingtonJoined"] == 0 and stats["wilmingtonParcels"] > 20:
        raise RuntimeError("Wilmington zoning polygons were fetched but none contained a city parcel")
    gaps = list(GAPS)
    collapsed = max(0, int(expected) - int(dropped) - len(features))
    if collapsed:
        gaps.append(
            f"{collapsed} duplicate PINs in the 5–150 acre query collapsed to the larger outline. The acreage filter still covered the county."
        )
    if used_fallback:
        gaps.insert(
            0,
            f"County Parcels/0 was unavailable ({fallback_reason}). Geometry fell back to NC OneMap cntyfips='129'.",
        )
    if not joins.get("designatedSource"):
        gaps.append("HUD designated Opportunity Zone polygons were not fetched. Eligibility was still joined and was not copied onto the designated flag.")
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
    cache_path.write_text(json.dumps(payload, separators=(",", ":")))
    return _write(seed, county, markets, payload)


def _write(seed: Any, county: dict, markets: list[str], payload: dict) -> dict:
    features = payload["features"]
    for feature in features:
        feature["properties"]["marketIds"] = markets
        feature["properties"].pop("mapIdKey", None)
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("37129 emitted a parcel outside 5–150 acres")
    path, lookup, tiles = (None, None, 0)
    if features:
        path, lookup, tiles = seed.write_tiles(county, features)
    stats = payload.get("stats") or {}
    print(
        f"  kept {len(features)} zoning {stats.get('zoningJoined', 0)} flu {stats.get('fluJoined', 0)} "
        f"eligible {stats.get('eligibleJoined', 0)} designated {stats.get('designatedJoined', 0)}",
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
            "crs": {"wkid": 103122, "latestWkid": 6543, "storedAs": 4326},
            "municipalities": stats.get("municipalities") or [],
            "unincorporated": stats.get("unincorporated"),
            "zoningJoinedCount": stats.get("zoningJoined"),
            "fluJoinedCount": stats.get("fluJoined"),
            "oz2EligibleCount": stats.get("eligibleJoined"),
            "designatedOzCount": stats.get("designatedJoined"),
            "viewerLinkTemplate": TAX_SEARCH,
            "appraiserSearchUrl": TAX_SEARCH,
        },
    )


def _features_from_parcels(seed: Any, raw: list[dict], county: dict, markets: list[str]):
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        acres = num(attrs.get("ACRES"))
        geometry, computed = seed.rings_to_feature_geometry(item.get("geometry"))
        if acres is None:
            acres = computed
        if not geometry or not seed.in_band(acres):
            dropped += 1
            continue
        center = seed.centroid_of(geometry)
        if not seed.plausible_centroid(center):
            dropped += 1
            continue
        parcel_id = clean(attrs.get("PIN")) or clean(attrs.get("MAPID")) or mapidkey_from_pin(attrs.get("MAPIDKEY"))
        map_key = clean(attrs.get("MAPIDKEY")) or mapidkey_from_pin(parcel_id)
        if not parcel_id or not map_key:
            dropped += 1
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
            source=SOURCE,
        )
        feature["properties"]["mapIdKey"] = map_key
        feature["properties"]["appraiserUrl"] = viewer_url()
        feature["properties"]["tax"]["marketValue"] = None
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def _features_from_onemap(seed: Any, raw: list[dict], county: dict, markets: list[str]):
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        acres = num(attrs.get("gisacres"))
        geometry, computed = seed.rings_to_feature_geometry(item.get("geometry"))
        if acres is None:
            acres = computed
        if not geometry or not seed.in_band(acres):
            dropped += 1
            continue
        center = seed.centroid_of(geometry)
        if not seed.plausible_centroid(center):
            dropped += 1
            continue
        parcel_id = clean(attrs.get("parno"))
        map_key = mapidkey_from_pin(parcel_id)
        if not parcel_id or not map_key:
            dropped += 1
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
            source=FALLBACK_SOURCE,
            owner=clean(attrs.get("ownname")),
            situs=clean(attrs.get("siteadd")),
            city=title_place(attrs.get("scity")),
            market_value=None,
            assessed=money(attrs.get("parval")),
        )
        feature["properties"]["mapIdKey"] = map_key
        feature["properties"]["appraiserUrl"] = viewer_url()
        feature["properties"]["tax"]["marketValue"] = None
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def _pull(seed: Any, url: str, where: str, fields: list[str]) -> list[dict]:
    ids = seed.fetch_object_ids(url, where)
    print(f"  {url.split('/rest/')[-1]} ids {len(ids)}", flush=True)
    return seed.fetch_by_ids(url, ids, fields, batch=80)


def _load_tax(seed: Any, keys: list[str]) -> dict[str, dict]:
    unique = [key for key in dict.fromkeys(keys) if key]
    found: dict[str, dict] = {}
    print(f"  IASTAX keys {len(unique)}", flush=True)
    for start in range(0, len(unique), 40):
        chunk = unique[start : start + 40]
        where = "MAPIDKEY IN (" + ",".join(_quote_key(key) for key in chunk) + ")"
        data = seed.fetch_json(
            f"{TAX_LAYER}/query",
            {
                "where": where,
                "outFields": ",".join(TAX_FIELDS),
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=120,
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        for item in data.get("features") or []:
            attrs = item.get("attributes") or {}
            key = clean(attrs.get("MAPIDKEY"))
            if not key:
                continue
            previous = found.get(key)
            if previous is None or (money(attrs.get("APRTOT")) or 0) > (money(previous.get("APRTOT")) or 0):
                found[key] = attrs
    print(f"  IASTAX matched {len(found)}", flush=True)
    return found


def _layer_features(seed: Any, url: str, fields: list[str], prop_keys: list[str]) -> list[dict]:
    raw = _pull(seed, url, "1=1", fields)
    features = []
    for item in raw:
        attrs = item.get("attributes") or {}
        feature = esri_feature(item, {key: attrs.get(key) for key in prop_keys})
        if feature:
            features.append(feature)
    return features


def _load_joins(seed: Any) -> dict:
    print("  zoning, place types, municipal limits", flush=True)
    muni = _layer_features(seed, f"{MUNI_LAYER}/query", ["CITY", "JURIS"], ["CITY", "JURIS"])
    county = _layer_features(
        seed,
        f"{COUNTY_ZONING}/query",
        ["ZONING", "ZONINGTXT", "CDFLAG"],
        ["ZONING", "ZONINGTXT"],
    )
    wilmington = _layer_features(
        seed,
        f"{WILMINGTON_ZONING}/query",
        ["Zoning", "CaseNumber", "CaseType"],
        ["Zoning", "CaseNumber", "CaseType"],
    )
    carolina = _layer_features(seed, f"{CAROLINA_ZONING}/query", ["ZONE", "NH_Codes"], ["ZONE"])
    wrightsville = _layer_features(seed, f"{WRIGHTSVILLE_ZONING}/query", ["Name"], ["Name"])
    flum = _layer_features(seed, f"{FLUM_LAYER}/query", ["PlaceType"], ["PlaceType"])
    designated, designated_source = _load_designated(seed)
    eligible = _load_eligible()
    return {
        "municipalities": index_features(muni),
        "county": index_features(county),
        "countyCount": len(county),
        "cities": {
            "Wilmington": index_features(wilmington),
            "Carolina Beach": index_features(carolina),
            "Wrightsville Beach": index_features(wrightsville),
        },
        "cityCounts": {
            "Wilmington": len(wilmington),
            "Carolina Beach": len(carolina),
            "Wrightsville Beach": len(wrightsville),
        },
        "flum": index_features(flum),
        "flumCount": len(flum),
        "designated": index_features(designated) if designated else None,
        "designatedCount": len(designated),
        "designatedSource": designated_source,
        "eligible": index_features(eligible) if eligible else None,
        "eligibleCount": len(eligible),
    }


def _load_designated(seed: Any) -> tuple[list[dict], str | None]:
    try:
        data = seed.fetch_json(
            HUD_OZ_QUERY,
            {
                "where": "STATE='37' AND COUNTY='129'",
                "outFields": "GEOID10,STATE,COUNTY,TRACT,STATE_NAME,Rural",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
            },
            timeout=120,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  designated QOZ fetch failed: {exc}", flush=True)
        return [], None
    if data.get("error"):
        print(f"  designated QOZ error: {data['error']}", flush=True)
        return [], None
    features = []
    for item in data.get("features") or []:
        props = item.get("properties") or {}
        geoid = clean(props.get("GEOID10"))
        if not geoid or not item.get("geometry"):
            continue
        rural_raw = props.get("Rural")
        rural = None
        if isinstance(rural_raw, str) and rural_raw.strip():
            rural = rural_raw.strip().upper() in {"Y", "YES", "1", "TRUE"}
        tract = clean(props.get("TRACT")) or geoid[-6:]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "tractGeoid": geoid,
                    "name": f"Census tract {tract}" if tract else None,
                    "rural": rural,
                },
                "geometry": item["geometry"],
            }
        )
    print(f"  designated QOZ tracts {len(features)}", flush=True)
    return features, HUD_OZ_QUERY.replace("/query", "")


def _load_eligible() -> list[dict]:
    if not OZ2_PACKS.exists():
        return []
    data = json.loads(OZ2_PACKS.read_text())
    features = []
    for item in data.get("features") or []:
        props = item.get("properties") or {}
        geoid = str(props.get("tractGeoid") or "")
        if not geoid.startswith("37129") or not item.get("geometry"):
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "tractGeoid": geoid,
                    "name": props.get("name"),
                    "rural": props.get("rural"),
                    "source": props.get("source") or "rev-proc-2026-14",
                    "designation": "eligible-for-nomination",
                },
                "geometry": item["geometry"],
            }
        )
    print(f"  OZ 2.0 eligible tracts {len(features)}", flush=True)
    return features


def _enrich_all(features: list[dict], joins: dict) -> dict:
    zoning_joined = 0
    flu_joined = 0
    eligible_joined = 0
    designated_joined = 0
    by_town: dict[str, dict[str, int]] = defaultdict(lambda: {"zoning": 0, "flu": 0, "parcels": 0})
    for feature in features:
        counts = apply_overlays(
            feature,
            municipalities=joins["municipalities"],
            city_zoning=joins["cities"],
            county_zoning=joins["county"],
            flum=joins["flum"],
            designated=joins["designated"],
            eligible=joins["eligible"],
            designated_source=joins["designatedSource"],
        )
        town = str(counts.get("town") or "")
        bucket = "Unincorporated" if not town else town
        by_town[bucket]["parcels"] += 1
        if counts["zoning"]:
            zoning_joined += 1
            by_town[bucket]["zoning"] += 1
        if counts["flu"]:
            flu_joined += 1
            by_town[bucket]["flu"] += 1
        eligible_joined += int(counts["eligible"])
        designated_joined += int(counts["designated"])
    municipalities = []
    for name, url, independent, flu_gap in (
        ("Wilmington", WILMINGTON_ZONING, True, "Create Wilmington future land use has no feature service. Planning/LandUse is existing land use, not FLU."),
        ("Carolina Beach", CAROLINA_ZONING, True, "No public Carolina Beach FLU feature service."),
        ("Wrightsville Beach", WRIGHTSVILLE_ZONING, True, "No public Wrightsville Beach FLU feature service."),
        ("Kure Beach", None, False, "No public Kure Beach FLU feature service."),
    ):
        stats = by_town.get(name) or {"zoning": 0, "flu": 0, "parcels": 0}
        municipalities.append(
            {
                "name": name,
                "independentGis": independent,
                "zoningUrl": url,
                "fluUrl": None,
                "fluGap": flu_gap,
                "join": "city zoning first, then county Zoning/1; PlanNHC place types stay outside city limits",
                "zoningFeatures": joins["cityCounts"].get(name),
                "zoningJoined": stats["zoning"],
                "fluJoined": stats["flu"],
                "parcelCount": stats["parcels"],
            }
        )
    unincorporated = by_town.get("Unincorporated") or {"zoning": 0, "flu": 0, "parcels": 0}
    return {
        "zoningJoined": zoning_joined,
        "fluJoined": flu_joined,
        "eligibleJoined": eligible_joined,
        "designatedJoined": designated_joined,
        "wilmingtonZoningFeatures": joins["cityCounts"].get("Wilmington") or 0,
        "wilmingtonJoined": (by_town.get("Wilmington") or {}).get("zoning") or 0,
        "wilmingtonParcels": (by_town.get("Wilmington") or {}).get("parcels") or 0,
        "municipalities": municipalities,
        "unincorporated": {
            "zoningUrl": COUNTY_ZONING,
            "fluUrl": FLUM_LAYER,
            "zoningFeatures": joins["countyCount"],
            "fluFeatures": joins["flumCount"],
            "zoningJoined": unincorporated["zoning"],
            "fluJoined": unincorporated["flu"],
            "parcelCount": unincorporated["parcels"],
            "note": "PlanNHC place types for unincorporated land. Municipal stamps CITY, WB, CB, and KB are not zoning districts.",
        },
    }

