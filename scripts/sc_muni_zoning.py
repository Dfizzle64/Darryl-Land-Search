#!/usr/bin/env python3
"""Join public South Carolina municipal zoning and FLU onto county parcel extracts.

City layers win over county layers. Rejected wrong-geography services are never
queried. The inclusive 5–150 acre set is not filtered again. Opportunity-zone
fields are left untouched — eligible is not designated.

  python3 scripts/join_sc_muni_zoning.py
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data" / "fixtures" / "market-parcels" / "sc-muni-zoning.json"

FOUNTAIN_INN_URL = "https://services3.arcgis.com/YQLyddqtM8cTAr6Y/arcgis/rest/services/Zoning_2026/FeatureServer/1/query"
GREENVILLE_CITY_ZONING_URL = "https://citygis.greenvillesc.gov/arcgis/rest/services/AddressSearch/Regulation/MapServer/7/query"
GREER_URL = "https://services1.arcgis.com/bskBH6JV42oEWJvZ/arcgis/rest/services/Greer_UDO_ZoningMap/FeatureServer/0/query"
GREENVILLE_COUNTY_ZONING_URL = "https://www.gcgis.org/arcgis3/rest/services/GCGIA/GCGIA_FeatureAccess/FeatureServer/13/query"
GREENVILLE_FLU_URL = "https://www.gcgis.org/arcgis3/rest/services/GCGIA/GCGIA_FeatureAccess/FeatureServer/21/query"
SUMMERVILLE_URL = "https://services8.arcgis.com/0zSnoqwLCR3i1Yfw/arcgis/rest/services/Zoning_View_Layer/FeatureServer/4/query"
FOLLY_URL = "https://gisccapps.charlestoncounty.org/arcgis/rest/services/FOLLY/FollyViewer/MapServer/19/query"
CHARLESTON_CITY_ZONING_URL = "https://gis.charleston-sc.gov/arcgis2/rest/services/External/mapnetExternal/MapServer/12/query"
CHARLESTON_CITY_FLU_URL = "https://gis.charleston-sc.gov/arcgis2/rest/services/External/mapnetExternal/MapServer/382/query"
NORTH_CHARLESTON_URL = "https://arc.northcharleston.org/arcgis/rest/services/DYlayers/Zoning/MapServer/0/query"
MOUNT_PLEASANT_URL = "https://maps.tompsc.com/arcgis/rest/services/Parcel_Search_New/MPSC_Zoning_New/MapServer/2/query"
CHARLESTON_COUNTY_ZONING_URL = "https://gisccapps.charlestoncounty.org/arcgis/rest/services/ENERGOV/energov_css/MapServer/7/query"
CHARLESTON_COUNTY_FLU_URL = "https://gisccapps.charlestoncounty.org/arcgis/rest/services/GIS_VIEWER/External_GIS_Website/MapServer/60/query"
BERKELEY_COUNTY_ZONING_URL = "https://gis.berkeleycountysc.gov/arcgis/rest/services/API/internet_map_with_api/MapServer/33/query"
GOOSE_CREEK_URL = "https://gis.berkeleycountysc.gov/arcgis/rest/services/API/internet_map_with_api/MapServer/37/query"
HANAHAN_URL = "https://gis.berkeleycountysc.gov/arcgis/rest/services/API/internet_map_with_api/MapServer/38/query"
MONCKS_CORNER_URL = "https://gis.berkeleycountysc.gov/arcgis/rest/services/API/internet_map_with_api/MapServer/45/query"
DORCHESTER_PARCEL_URL = "https://gisportal.dorchestercounty.net/hosting/rest/services/General_Data/Parcels_Public/MapServer/0/query"
IOP_ORG = "https://services7.arcgis.com/Cv3A9wUHusU2ofWZ/arcgis/rest/services"

# District code is the service name. PDD is excluded: the card says QA before production.
IOP_DISTRICTS = (
    ("SR1_ExportFeaturesNew", "SR-1"),
    ("SR2_SetbackIncluded", "SR-2"),
    ("SR3_SetbackIncluded", "SR-3"),
    ("GC1", "GC-1"),
    ("GC2", "GC-2"),
    ("GC3", "GC-3"),
    ("LC_ExportFeatures", "LC"),
    ("Conservation_Recreation_District", "Conservation-Recreation"),
)
IOP_EXCLUDED = ("PDD",)

# Situs cities where county (and other cities') zoning is not a substitute.
GAP_PLACES = frozenset({"ISLE OF PALMS", "SULLIVANS ISLAND", "SULLIVAN ISLAND", "JAMES ISLAND"})

BANNED_URL_FRAGMENTS = (
    "ZoningFireSewer",
    "SimpsonvilleZoning",
    "xKvDQ9PmaqgzOpn2",
    "New_FI_Zoning_Swipe",
    "City_of_Folly_Beach_Zoning",
    "Greenville_Base_Data",
    "/PDD/",
    "Zoning_2025",
)

REJECTED = [
    {
        "name": "SimpsonvilleZoning AGOL",
        "reason": "Owner triples hosts Shelby County, Tennessee (shelbypz.com). Wrong-geography twin of Simpsonville, SC. Not queried.",
    },
    {
        "name": "Fountain Inn ZoningFireSewer/2",
        "reason": "Codes R-7.5/R-20/UNZONED on a county-scale extent. Not the Fountain Inn UDO. Not queried.",
    },
    {
        "name": "Fountain Inn consultant New_Zoning swipe map",
        "reason": "Third-party MPM_stewartinc host. City Zoning_2026 is the usable layer. Not queried.",
    },
    {
        "name": "Sullivan's Island Zoning_2025",
        "reason": "Unofficial AGOL (the_charliosouljah), not town-hosted. Not queried.",
    },
    {
        "name": "Folly Beach CofC/SCGIS AGOL",
        "reason": "Alternate of county FollyViewer/19. County layer is the usable source. Not queried.",
    },
    {
        "name": "AGOL Greenville_Base_Data tax parcels",
        "reason": "City-extent subset, not countywide. Not queried.",
    },
    {
        "name": "Isle of Palms PDD FeatureServer",
        "reason": "Card count looks oversized versus a typical PDD inventory. Left as a gap pending QA. Not queried.",
    },
]

HONEST_GAPS = [
    "Sullivan's Island: official zoning is PDF / Instant app only. Unofficial Zoning_2025 was not joined.",
    "James Island: PDF/static maps only. No municipal zoning REST. County External/ENERGOV is a municipal overlay, not the ZLDR zoning layer, and is not used as James Island zoning.",
    "Mauldin, Simpsonville, and Travelers Rest: no city FeatureServer. County JCODE on GCGIA Zoning/13 is the public layer. SimpsonvilleZoning AGOL is Shelby County, Tennessee.",
    "Isle of Palms: district services are partial and have no ZONING field. PDD was not joined.",
    "Fountain Inn on the Laurens side and Greer on the Spartanburg side are not joined — those counties have no parcel extract.",
    "Berkeley and Dorchester have no field-mapped future-land-use layer on these cards.",
    "Eligible tracts are not designated Opportunity Zones. This join does not write opportunityZone or oz2Eligibility.",
]

FOUNTAIN_INN_REJECTED_CODES = frozenset({"R-7.5", "R-20"})


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def epoch_to_iso(value: Any) -> str | None:
    from datetime import datetime, timezone

    parsed = num(value)
    if parsed is None:
        return None
    if abs(parsed) > 10_000_000_000:
        parsed = parsed / 1000.0
    if parsed < -2_208_988_800 or parsed > 4_102_444_800:
        return None
    try:
        stamp = datetime.fromtimestamp(parsed, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    if 1900 <= stamp.year <= 2100:
        return stamp.date().isoformat()
    return None


def parcel_keys(value: Any) -> list[str]:
    raw = "".join(str(value or "").upper().split())
    if not raw or raw in {"NONE", "NULL"}:
        return []
    keys = [raw]
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 5:
        keys.append(digits)
        stripped = digits.lstrip("0")
        if len(stripped) >= 5 and stripped != digits:
            keys.append(stripped)
    seen: set[str] = set()
    unique: list[str] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            unique.append(key)
    return unique


def normalize_place(value: Any) -> str:
    text = (clean(value) or "").upper().replace("'", "").replace(".", "")
    return " ".join(text.split())


def is_gap_place(feature: dict) -> bool:
    place = normalize_place((feature.get("properties") or {}).get("situsCity"))
    return any(token in place for token in GAP_PLACES)


def north_charleston_code(attrs: dict) -> str | None:
    """ZONETYPE is the district label (B-2). ZONECODE on this layer is a numeric class."""
    return clean(attrs.get("ZONETYPE")) or clean(attrs.get("ZONECODE"))


def iop_url(service: str) -> str:
    return f"{IOP_ORG}/{service}/FeatureServer/0/query"


def queried_iop_urls() -> list[str]:
    return [iop_url(service) for service, _code in IOP_DISTRICTS]


def assert_urls_allowed(urls: list[str]) -> None:
    for url in urls:
        for fragment in BANNED_URL_FRAGMENTS:
            if fragment.lower() in url.lower():
                raise RuntimeError(f"Refusing rejected layer {url}")


def rows_for_county(rows: list[dict], county: str) -> list[dict]:
    want = county.upper()
    return [row for row in rows if (clean(row.get("County")) or "").upper() == want]


def index_codes(rows: list[dict], id_fields: list[str], code_fn: Callable[[dict], str | None]) -> dict[str, str]:
    table: dict[str, str] = {}
    for row in rows:
        code = code_fn(row)
        if not code:
            continue
        for field in id_fields:
            for key in parcel_keys(row.get(field)):
                table[key] = code
    return table


def lookup_code(table: dict[str, str], raw_ids: list[Any]) -> str | None:
    for raw in raw_ids:
        for key in parcel_keys(raw):
            code = table.get(key)
            if code:
                return code
    return None


def feature_ids(feature: dict) -> list[Any]:
    props = feature.get("properties") or {}
    return [props.get("parcelId"), props.get("_altParcelId")]


def overlay_attribute(features: list[dict], table: dict[str, str], source: str) -> int:
    matched = 0
    for feature in features:
        code = lookup_code(table, feature_ids(feature))
        if not code:
            continue
        props = feature["properties"]
        props["zoningCode"] = code
        props["_zoningSource"] = source
        matched += 1
    return matched


def _point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _inside(x: float, y: float, geometry: dict) -> bool:
    kind = geometry.get("type")
    if kind == "Polygon":
        rings = geometry.get("coordinates") or []
        if not rings or not _point_in_ring(x, y, rings[0]):
            return False
        return not any(_point_in_ring(x, y, hole) for hole in rings[1:])
    if kind == "MultiPolygon":
        for rings in geometry.get("coordinates") or []:
            if rings and _point_in_ring(x, y, rings[0]) and not any(_point_in_ring(x, y, hole) for hole in rings[1:]):
                return True
    return False


def _bbox(geometry: dict) -> tuple[float, float, float, float] | None:
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

    walk(geometry.get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


class GridIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = _bbox(feature.get("geometry") or {})
        if not bbox:
            return
        west, south, east, north = bbox
        ix0 = math.floor(west / self.cell)
        ix1 = math.floor(east / self.cell)
        iy0 = math.floor(south / self.cell)
        iy1 = math.floor(north / self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 400:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        ix = math.floor(x / self.cell)
        iy = math.floor(y / self.cell)
        for feature in self.buckets.get((ix, iy), []):
            if _inside(x, y, feature["geometry"]):
                return feature["properties"]
        for feature in self.broad:
            if _inside(x, y, feature["geometry"]):
                return feature["properties"]
        return None


def overlay_spatial(features: list[dict], index: GridIndex, *, field: str, skip: Callable[[dict], bool] | None = None) -> int:
    matched = 0
    for feature in features:
        if skip and skip(feature):
            continue
        centroid = (feature.get("properties") or {}).get("centroid") or [None, None]
        if centroid[0] is None:
            continue
        payload = index.hit(float(centroid[0]), float(centroid[1]))
        if not payload or not payload.get("code"):
            continue
        props = feature["properties"]
        if field == "flu":
            props["flu"] = {
                "code": payload["code"],
                "label": payload.get("label") or payload["code"],
                "jurisdiction": payload.get("jurisdiction"),
                "source": payload["source"],
            }
            props["_fluSource"] = payload["source"]
        else:
            props["zoningCode"] = payload["code"]
            props["_zoningSource"] = payload["source"]
        matched += 1
    return matched


def _seed():
    import seed_market_parcels as seed

    return seed


def fetch_attributes(url: str, where: str, fields: list[str], queried: list[str]) -> list[dict]:
    assert_urls_allowed([url])
    queried.append(url)
    seed = _seed()
    count = seed.count_where(url, where)
    print(f"  attributes {count} {url.split('/rest/services/')[-1][:90]}", flush=True)
    if count <= 0:
        return []
    ids = seed.fetch_object_ids(url, where)
    raw = seed.fetch_by_ids(url, ids, fields, batch=200, return_geometry=False)
    return [item.get("attributes") or {} for item in raw]


def fetch_spatial(url: str, where: str, fields: list[str], payload_fn: Callable[[dict], dict | None], queried: list[str]) -> GridIndex:
    from parcel_geometry import esri_rings_to_geojson

    assert_urls_allowed([url])
    queried.append(url)
    seed = _seed()
    count = seed.count_where(url, where)
    print(f"  spatial {count} {url.split('/rest/services/')[-1][:90]}", flush=True)
    index = GridIndex(0.02)
    if count <= 0:
        return index
    ids = seed.fetch_object_ids(url, where)
    raw = seed.fetch_by_ids(url, ids, fields, batch=60, return_geometry=True)
    kept = 0
    for item in raw:
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [], tol=0.00003)
        if not geometry:
            continue
        payload = payload_fn(item.get("attributes") or {})
        if not payload or not payload.get("code"):
            continue
        index.add({"geometry": geometry, "properties": payload})
        kept += 1
    print(f"    indexed {kept}", flush=True)
    return index


def _code_payload(code: Any, source: str, **extra: Any) -> dict | None:
    text = clean(code)
    if not text or text.upper() in {"NULL", "NONE"}:
        return None
    payload = {"code": text, "source": source}
    payload.update(extra)
    return payload


def join_greenville(features: list[dict], queried: list[str]) -> None:
    county = fetch_spatial(
        GREENVILLE_COUNTY_ZONING_URL,
        "1=1",
        ["ZONING", "JCODE"],
        lambda attrs: _code_payload(
            attrs.get("ZONING"),
            f"greenville-county:{jurisdiction_code(attrs.get('JCODE'))}",
        ),
        queried,
    )
    overlay_spatial(features, county, field="zoning")
    city = fetch_spatial(
        GREENVILLE_CITY_ZONING_URL,
        "1=1",
        ["ZONING"],
        lambda attrs: _code_payload(attrs.get("ZONING"), "greenville-city"),
        queried,
    )
    overlay_spatial(features, city, field="zoning")
    greer = fetch_spatial(
        GREER_URL,
        "1=1",
        ["Pro_Zoning"],
        lambda attrs: _code_payload(attrs.get("Pro_Zoning"), "greer"),
        queried,
    )
    overlay_spatial(features, greer, field="zoning")
    fountain = fetch_spatial(
        FOUNTAIN_INN_URL,
        "1=1",
        ["Zoning", "ZoningLabel"],
        lambda attrs: _code_payload(attrs.get("Zoning"), "fountain-inn", label=clean(attrs.get("ZoningLabel"))),
        queried,
    )
    overlay_spatial(features, fountain, field="zoning")
    flu = fetch_spatial(
        GREENVILLE_FLU_URL,
        "1=1",
        ["FLU", "CharacterA"],
        lambda attrs: _code_payload(
            attrs.get("FLU"),
            "greenville-county-flu",
            label=clean(attrs.get("CharacterA")) or clean(attrs.get("FLU")),
            jurisdiction="Greenville County",
        ),
        queried,
    )
    overlay_spatial(features, flu, field="flu")


def join_charleston(features: list[dict], queried: list[str]) -> None:
    county = fetch_spatial(
        CHARLESTON_COUNTY_ZONING_URL,
        "1=1",
        ["ZONING", "ZONE_DESC"],
        lambda attrs: _code_payload(attrs.get("ZONING"), "charleston-county"),
        queried,
    )
    overlay_spatial(features, county, field="zoning", skip=is_gap_place)
    north = fetch_spatial(
        NORTH_CHARLESTON_URL,
        "1=1",
        ["ZONECODE", "ZONETYPE", "ZONEDESC"],
        lambda attrs: _code_payload(north_charleston_code(attrs), "north-charleston"),
        queried,
    )
    overlay_spatial(features, north, field="zoning", skip=is_gap_place)
    city = fetch_spatial(
        CHARLESTON_CITY_ZONING_URL,
        "1=1",
        ["ZONE_BASE", "PUD_NAME"],
        lambda attrs: _code_payload(attrs.get("ZONE_BASE"), "charleston-city"),
        queried,
    )
    overlay_spatial(features, city, field="zoning", skip=is_gap_place)
    pleasant_rows = fetch_attributes(MOUNT_PLEASANT_URL, "1=1", ["PARCEL_ID", "ZONINGVALU"], queried)
    pleasant = index_codes(
        [row for row in pleasant_rows if (clean(row.get("ZONINGVALU")) or "").upper() not in {"COUNTY", "AWENDAW"}],
        ["PARCEL_ID"],
        lambda row: clean(row.get("ZONINGVALU")),
    )
    overlay_attribute(features, pleasant, "mount-pleasant")
    summerville = index_codes(
        rows_for_county(fetch_attributes(SUMMERVILLE_URL, "County='CHARLESTON'", ["TMS", "PID", "Zone_Class", "County"], queried), "CHARLESTON"),
        ["TMS", "PID"],
        lambda row: clean(row.get("Zone_Class")),
    )
    overlay_attribute(features, summerville, "summerville-charleston")
    folly = index_codes(
        fetch_attributes(FOLLY_URL, "1=1", ["PID", "zoning"], queried),
        ["PID"],
        lambda row: clean(row.get("zoning")),
    )
    overlay_attribute(features, folly, "folly-beach")
    for service, district in IOP_DISTRICTS:
        rows = fetch_attributes(iop_url(service), "1=1", ["PARCEL_ID", "PID"], queried)
        table = index_codes(rows, ["PARCEL_ID", "PID"], lambda _row, code=district: code)
        overlay_attribute(features, table, f"isle-of-palms:{district}")
    flu = fetch_spatial(
        CHARLESTON_COUNTY_FLU_URL,
        "1=1",
        ["REC_USE", "ProtectTyp"],
        lambda attrs: _code_payload(
            attrs.get("REC_USE"),
            "charleston-county-flu",
            label=clean(attrs.get("ProtectTyp")) or clean(attrs.get("REC_USE")),
            jurisdiction="Charleston County",
        ),
        queried,
    )
    overlay_spatial(features, flu, field="flu")
    city_flu = fetch_spatial(
        CHARLESTON_CITY_FLU_URL,
        "1=1",
        ["LAND_USE", "Name"],
        lambda attrs: _code_payload(
            attrs.get("LAND_USE"),
            "charleston-city-flu",
            label=clean(attrs.get("LAND_USE")),
            jurisdiction="City of Charleston",
        ),
        queried,
    )
    overlay_spatial(features, city_flu, field="flu")


def join_berkeley(features: list[dict], queried: list[str]) -> None:
    county_rows = fetch_attributes(BERKELEY_COUNTY_ZONING_URL, "1=1", ["ZONE", "O_TMS"], queried)
    overlay_attribute(
        features,
        index_codes(county_rows, ["O_TMS"], lambda row: clean(row.get("ZONE"))),
        "berkeley-county",
    )
    summerville = index_codes(
        rows_for_county(fetch_attributes(SUMMERVILLE_URL, "County='BERKELEY'", ["TMS", "PID", "Zone_Class", "County"], queried), "BERKELEY"),
        ["TMS", "PID"],
        lambda row: clean(row.get("Zone_Class")),
    )
    overlay_attribute(features, summerville, "summerville-berkeley")
    for url, source in (
        (GOOSE_CREEK_URL, "goose-creek"),
        (HANAHAN_URL, "hanahan"),
        (MONCKS_CORNER_URL, "moncks-corner"),
    ):
        rows = fetch_attributes(url, "1=1", ["ZONE", "O_TMS"], queried)
        overlay_attribute(features, index_codes(rows, ["O_TMS"], lambda row: clean(row.get("ZONE"))), source)


def enrich_dorchester(features: list[dict], queried: list[str]) -> None:
    rows = fetch_attributes(
        DORCHESTER_PARCEL_URL,
        "GIS_ACREAGE>=5 AND GIS_ACREAGE<=150",
        ["TMS", "ZONINGCODE", "PROPERTY_LOCATION", "JURISDICTION", "SALE_PRICE", "SALE_DATE"],
        queried,
    )
    by_key: dict[str, dict] = {}
    for row in rows:
        for key in parcel_keys(row.get("TMS")):
            by_key[key] = row
    for feature in features:
        props = feature["properties"]
        row = None
        for key in parcel_keys(props.get("parcelId")):
            row = by_key.get(key)
            if row:
                break
        if not row:
            continue
        code = clean(row.get("ZONINGCODE"))
        if code and not props.get("zoningCode"):
            props["zoningCode"] = code
            props["_zoningSource"] = "dorchester-county"
        situs = clean(row.get("PROPERTY_LOCATION"))
        if situs and not props.get("situsAddress"):
            props["situsAddress"] = situs
        juris = clean(row.get("JURISDICTION"))
        if juris and not props.get("jurisdictionCode"):
            props["jurisdictionCode"] = juris
        sale = dict(props.get("lastSale") or {"date": None, "price": None, "qualified": None})
        if not sale.get("date"):
            sale["date"] = epoch_to_iso(row.get("SALE_DATE"))
        if not sale.get("price"):
            price = num(row.get("SALE_PRICE"))
            sale["price"] = price if price and price > 0 else None
        props["lastSale"] = sale


def join_dorchester(features: list[dict], queried: list[str]) -> None:
    enrich_dorchester(features, queried)
    summerville = index_codes(
        rows_for_county(fetch_attributes(SUMMERVILLE_URL, "County='DORCHESTER'", ["TMS", "PID", "Zone_Class", "County"], queried), "DORCHESTER"),
        ["TMS", "PID"],
        lambda row: clean(row.get("Zone_Class")),
    )
    overlay_attribute(features, summerville, "summerville-dorchester")


def _tally(features: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for feature in features:
        source = (feature.get("properties") or {}).get("_zoningSource")
        if source:
            counts[source] += 1
    return dict(counts)


def _samples(features: list[dict]) -> list[dict]:
    seen: set[str] = set()
    samples: list[dict] = []
    for feature in features:
        props = feature["properties"]
        source = props.get("_zoningSource")
        if not source or source in seen:
            continue
        seen.add(source)
        samples.append(
            {
                "source": source,
                "parcelId": props.get("parcelId"),
                "zoningCode": props.get("zoningCode"),
                "acreage": props.get("acreage"),
            }
        )
    return samples


def _codes(features: list[dict]) -> dict[str, list[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for feature in features:
        props = feature["properties"]
        source = props.get("_zoningSource")
        code = props.get("zoningCode")
        if source and code:
            found[source].add(str(code))
    return {key: sorted(values) for key, values in found.items()}


def _city_rows(counts: dict[str, int], groups: list[tuple[str, list[str], str, str]]) -> dict[str, dict]:
    cities: dict[str, dict] = {}
    for name, sources, status, note in groups:
        joined = sum(counts.get(source, 0) for source in sources)
        cities[name] = {"joined": joined, "status": status, "note": note}
    return cities


def jurisdiction_code(value: Any) -> str:
    text = clean(value) or "unknown"
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _section(fips: str, name: str, features: list[dict], queried: list[str], groups: list[tuple[str, list[str], str, str]], notes: list[str]) -> dict:
    counts = _tally(features)
    zoning_joined = sum(1 for feature in features if (feature["properties"].get("zoningCode")))
    flu_joined = sum(1 for feature in features if ((feature["properties"].get("flu") or {}) or {}).get("code"))
    cities = _city_rows(counts, groups)
    lines = [
        f"Inclusive 5–150 acre extract kept ({len(features)} parcels). Zoning joined on {zoning_joined}. FLU joined on {flu_joined}.",
    ]
    for city, row in cities.items():
        lines.append(f"{city}: {row['joined']} ({row['status']}). {row['note']}")
    lines.extend(notes)
    return {
        "fips": fips,
        "name": name,
        "parcels": len(features),
        "zoningJoined": zoning_joined,
        "fluJoined": flu_joined,
        "bySource": counts,
        "cities": cities,
        "samples": _samples(features),
        "codes": _codes(features),
        "queried": queried,
        "gaps": lines,
    }


def _strip_private(features: list[dict]) -> None:
    for feature in features:
        props = feature["properties"]
        props.pop("_altParcelId", None)
        props.pop("_zoningSource", None)
        props.pop("_fluSource", None)


def _store(section: dict) -> None:
    report = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "band": {"min": 5.0, "max": 150.0, "inclusive": True},
        "opportunityZones": "Parcel opportunityZone and oz2Eligibility are not modified. Eligible is not designated.",
        "rejected": REJECTED,
        "honestGaps": HONEST_GAPS,
        "counties": {},
    }
    if REPORT_PATH.exists():
        previous = json.loads(REPORT_PATH.read_text())
        report["counties"] = previous.get("counties") or {}
    report["counties"][section["fips"]] = section
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")


def join_features(fips: str, features: list[dict]) -> tuple[list[dict], list[str]]:
    queried: list[str] = []
    if fips == "45045":
        join_greenville(features, queried)
        section = _section(
            fips,
            "Greenville",
            features,
            queried,
            [
                ("Fountain Inn", ["fountain-inn"], "usable", "City Zoning_2026 dissolved districts, spatial join onto Greenville County parcels."),
                ("City of Greenville", ["greenville-city"], "usable", "AddressSearch/Regulation/7 Development Code districts."),
                ("Greer", ["greer"], "usable", "Greer UDO Pro_Zoning on the Greenville County side."),
                ("Mauldin", ["greenville-county:45115"], "no-city-rest", "No city FeatureServer. County JCODE 45115 only."),
                ("Simpsonville", ["greenville-county:66580"], "no-city-rest", "No city FeatureServer. SimpsonvilleZoning AGOL is Shelby TN and was rejected."),
                ("Travelers Rest", ["greenville-county:72430"], "no-city-rest", "No city FeatureServer. County JCODE 72430 only."),
                ("Greenville County", ["greenville-county:45045"], "usable", "Unincorporated county zoning on GCGIA/13."),
            ],
            [
                "Laurens-side Fountain Inn and Spartanburg-side Greer are not in this extract.",
                "Fountain Inn consultant swipe map and ZoningFireSewer/2 were not queried.",
                "No city FLU for Fountain Inn. County FLU/21 is joined.",
            ],
        )
    elif fips == "45019":
        join_charleston(features, queried)
        iop_sources = [f"isle-of-palms:{code}" for _service, code in IOP_DISTRICTS]
        section = _section(
            fips,
            "Charleston",
            features,
            queried,
            [
                ("Folly Beach", ["folly-beach"], "usable", "Charleston County FOLLY/FollyViewer/19 joined on PID."),
                ("Isle of Palms", iop_sources, "partial", "District services stamped from the service name. PDD not joined."),
                ("Summerville", ["summerville-charleston"], "usable", "Town Zoning_View_Layer filtered to County=CHARLESTON."),
                ("City of Charleston", ["charleston-city"], "usable", "mapnetExternal/12 ZONE_BASE."),
                ("North Charleston", ["north-charleston"], "usable", "DYlayers/Zoning ZONETYPE."),
                ("Mount Pleasant", ["mount-pleasant"], "usable", "MPSC_Zoning_New/2. COUNTY and AWENDAW values dropped."),
                ("Charleston County", ["charleston-county"], "usable", "energov_css/7 for the remainder. Not applied on Sullivan's Island, James Island, or Isle of Palms situs cities."),
                ("Sullivan's Island", [], "gap", "No town REST. Unofficial Zoning_2025 not queried."),
                ("James Island", [], "gap", "PDF/static only. No municipal zoning REST. County External/ENERGOV is a municipal overlay, not ZLDR."),
            ],
            [
                "County FLU External_GIS_Website/60 and City of Charleston mapnetExternal/382 LAND_USE are joined. City FLU wins inside the city.",
                "Token-walled Parcel_Search and Public_Search were not used.",
            ],
        )
    elif fips == "45015":
        join_berkeley(features, queried)
        section = _section(
            fips,
            "Berkeley",
            features,
            queried,
            [
                ("Goose Creek", ["goose-creek"], "usable", "internet_map_with_api/37 ZONE joined on O_TMS."),
                ("Hanahan", ["hanahan"], "usable", "internet_map_with_api/38 ZONE joined on O_TMS."),
                ("Moncks Corner", ["moncks-corner"], "usable", "internet_map_with_api/45 ZONE joined on O_TMS."),
                ("Summerville", ["summerville-berkeley"], "usable", "Town layer filtered to County=BERKELEY."),
                ("Berkeley County", ["berkeley-county"], "usable", "internet_map_with_api/33 where no city layer hit."),
            ],
            ["Future land use on New_Parcel_Zoning was not field-mapped. No FLU join."],
        )
    elif fips == "45035":
        join_dorchester(features, queried)
        section = _section(
            fips,
            "Dorchester",
            features,
            queried,
            [
                ("Summerville", ["summerville-dorchester"], "usable", "Town Zone_Class filtered to County=DORCHESTER, joined on TMS over county ZONINGCODE."),
                ("Dorchester County", ["dorchester-county"], "usable", "ZONINGCODE on Parcels_Public for parcels outside the town join."),
            ],
            [
                "Existing 5–150 acre parcel set was kept. Situs filled from PROPERTY_LOCATION when the extract had none.",
                "No assessed market value on the public parcel layer. No FLU layer on this card.",
            ],
        )
    else:
        raise RuntimeError(f"No South Carolina municipal join for {fips}")
    assert_urls_allowed(queried)
    fountain_codes = set(section["codes"].get("fountain-inn") or [])
    if fountain_codes & FOUNTAIN_INN_REJECTED_CODES:
        raise RuntimeError(f"Fountain Inn join picked up rejected codes {sorted(fountain_codes & FOUNTAIN_INN_REJECTED_CODES)}")
    _store(section)
    _strip_private(features)
    print(
        f"  joined {section['name']}: zoning {section['zoningJoined']}/{section['parcels']} flu {section['fluJoined']}",
        flush=True,
    )
    return features, list(section["gaps"])


def _county_record(catalog: dict, fips: str) -> dict:
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips:
                return county
    raise KeyError(fips)


def _markets_for(catalog: dict, fips: str) -> list[str]:
    names: list[str] = []
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips and market["id"] not in names:
                names.append(market["id"])
    return names


def patch_existing_dorchester() -> None:
    """Attribute-join Dorchester zoning without adding or dropping parcels."""
    import seed_market_parcels as seed

    folder = seed.COUNTY_DIR / "45035" / "tiles"
    features: list[dict] = []
    for path in sorted(folder.glob("*.geojson")):
        features.extend(json.loads(path.read_text()).get("features") or [])
    before = [(feature["properties"]["parcelId"], feature["properties"]["acreage"]) for feature in features]
    before_oz = [
        (feature["properties"].get("opportunityZone"), feature["properties"].get("oz2Eligibility")) for feature in features
    ]
    features, gaps = join_features("45035", features)
    after = [(feature["properties"]["parcelId"], feature["properties"]["acreage"]) for feature in features]
    after_oz = [
        (feature["properties"].get("opportunityZone"), feature["properties"].get("oz2Eligibility")) for feature in features
    ]
    if before != after:
        raise RuntimeError("Dorchester parcel ids or acreage changed during zoning join")
    if before_oz != after_oz:
        raise RuntimeError("Dorchester opportunity-zone fields changed during zoning join")
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Dorchester join emitted a parcel outside 5–150 acres")
    existing = json.loads((seed.COUNTY_DIR / "45035" / "county.json").read_text())
    county = {"name": existing["name"], "fips": "45035", "state": existing["state"]}
    path, lookup, tiles = seed.write_tiles(county, features)
    seed.county_row(
        county,
        existing.get("markets") or ["Charleston"],
        feature_count=len(features),
        coverage=existing["coverage"],
        partition="tiles",
        path=path,
        lookup=lookup,
        source=existing["source"],
        query_url=existing["queryUrl"],
        gaps=gaps,
        source_count=existing.get("sourceCount"),
        dropped=existing.get("dropped"),
        tile_count=tiles,
    )


def main() -> None:
    import seed_market_parcels as seed

    catalog = json.loads(seed.CATALOG_PATH.read_text())
    originals = {path: path.read_text() for path in seed.MARKET_DIR.glob("*/meta.json")}
    for fips in ("45015", "45019", "45045"):
        county = _county_record(catalog, fips)
        spec = seed.county_override(fips)
        if not spec:
            raise RuntimeError(f"Missing spec for {fips}")
        seed.download_county(county, _markets_for(catalog, fips), spec)
    patch_existing_dorchester()
    seed.rebuild_indexes(catalog)
    for path, text in originals.items():
        old = json.loads(text)
        new = json.loads(path.read_text())
        old.pop("generatedAt", None)
        body = dict(new)
        body.pop("generatedAt", None)
        if old == body:
            path.write_text(text)
    print(f"Wrote {REPORT_PATH}", flush=True)


if __name__ == "__main__":
    main()
