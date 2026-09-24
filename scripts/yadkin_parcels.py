"""Yadkin County, North Carolina parcel enrichments.

Public county GIS only (CountyGISmap). Town zoning layers are first-class.
The Land Use layer is USDA cropland and is never stored as future land use.
OZ 2.0 eligibility is not a designated Qualified Opportunity Zone.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from parcel_geometry import esri_rings_to_geojson, polygon_parts, signed_area

ROOT = Path(__file__).resolve().parents[1]
GIS = "https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer"
HUD_OZ_URL = (
    "https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/FeatureServer/13/query"
)
TIGER_TRACTS_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/6/query"
)
FLU_MAP = "https://www.yadkincountync.gov/DocumentCenter/View/6126/Future-Land-Use-Map-"
FLU_PLAN = (
    "https://www.yadkincountync.gov/DocumentCenter/View/5990/Yadkin-County-Comprehensive-Land-Use-Plan-2023-"
)

# County zoning codes that are not a base district. TZ means "see the town layer".
COUNTY_PLACEHOLDERS = {"TZ"}
COUNTY_OVERLAYS = {"WO", "AO-1"}

TOWN_LAYERS = (
    {"layer": 41, "prefix": "BVN", "name": "Boonville", "code": "BOONVILLE_", "label": "BOONVILLE1"},
    {"layer": 42, "prefix": "EBD", "name": "East Bend", "code": "ZONING_NO", "label": "ZONING_NAM"},
    {"layer": 43, "prefix": "JVL", "name": "Jonesville", "code": "ZONING", "label": "JONESVILLE"},
    {"layer": 44, "prefix": "YVL", "name": "Yadkinville", "code": "ZONE_CODE", "label": "ZONE"},
)
LIMIT_PREFIX = {
    "BOONVILLE": "BVN",
    "EAST BEND": "EBD",
    "JONESVILLE": "JVL",
    "YADKINVILLE": "YVL",
}
CELL = 0.04


def yadkin_parcel_spec() -> dict:
    return {
        "kind": "arcgis",
        "url": f"{GIS}/1/query",
        "where": "TOTAL_ACRES>=5 AND TOTAL_ACRES<=150",
        "outFields": [
            "PIN",
            "PARCEL_NO",
            "TOTAL_ACRES",
            "NAME1",
            "NAME2",
            "STREET_ADDRESS",
            "ADDRESS1",
            "ADDRESS2",
            "CITY",
            "STATE",
            "ZIP",
            "LAND_FMV_CURRENT",
            "BLDG_FMV_CURRENT",
            "LAND_ASV_CURRENT",
            "SALES_AMT",
            "DEED_DATE",
            "QUALIFIED_CODE",
        ],
        "idField": "PIN",
        "idFallbacks": ["PARCEL_NO"],
        "acresField": "TOTAL_ACRES",
        "ownerField": "NAME1",
        "owner2Field": "NAME2",
        "situsField": "STREET_ADDRESS",
        "mail1Field": "ADDRESS1",
        "mail2Field": "ADDRESS2",
        "mailCityField": "CITY",
        "mailStateField": "STATE",
        "mailZipField": "ZIP",
        "marketValueSum": ["LAND_FMV_CURRENT", "BLDG_FMV_CURRENT"],
        "assessedField": "LAND_ASV_CURRENT",
        "salePriceField": "SALES_AMT",
        "saleEpochField": "DEED_DATE",
        "saleQualifiedField": "QUALIFIED_CODE",
        "source": "nc-yadkin-county-gis",
        "coverage": "complete-gte-5ac",
        "enrich": "yadkin",
        "ignoreCache": True,
        "batch": 200,
        "gaps": [
            "Parcels are Yadkin County GIS CountyGISmap/MapServer/1, filtered on TOTAL_ACRES 5.0–150.0. NC OneMap cntyfips='197' is a count cross-check only; gisacres is not the stored acreage.",
            "Zoning is county-hosted. Town layers are first-class: Boonville MapServer/41, East Bend /42, Jonesville /43, Yadkinville /44. County zoning is /40. A county TZ placeholder is not stored as the district when a town layer hits, and TZ is never stored by itself. Town Limits with ETJ are /45. Joined codes are not an Orange County multifamily knowledge-base match.",
            (
                "Future land use is a PDF-only gap. CountyGISmap/MapServer/38 Land Use is USDA cropland "
                "(Corn, Soybeans, Fallow/Idle Cropland, and other CLASS_NAME values), not the adopted future land use map. "
                "Those classes are not joined as planning FLU. "
                f"2023 Future Land Use Map: {FLU_MAP} "
                f"2023 Comprehensive Land Use Plan: {FLU_PLAN}"
            ),
            "Opportunity zones: inOpportunityZone is only the HUD designated 2010 QOZ. oz2Eligibility is Rev. Proc. 2026-14 nomination eligibility on 2020 tracts. Eligible is not a designated QOZ.",
        ],
    }


def _point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _inside_polygon(x: float, y: float, poly: list) -> bool:
    if not poly or not _point_in_ring(x, y, poly[0]):
        return False
    return not any(_point_in_ring(x, y, hole) for hole in poly[1:])


def contains(geometry: dict, x: float, y: float) -> bool:
    return any(_inside_polygon(x, y, poly) for poly in polygon_parts(geometry))


def _iter_xy(geometry: dict):
    coords = geometry.get("coordinates") or []
    if geometry.get("type") == "Polygon":
        for ring in coords:
            for point in ring:
                yield point[0], point[1]
    elif geometry.get("type") == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                for point in ring:
                    yield point[0], point[1]


def _bbox(geometry: dict) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for x, y in _iter_xy(geometry):
        xs.append(x)
        ys.append(y)
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    return min(xs), min(ys), max(xs), max(ys)


def _area(geometry: dict) -> float:
    total = 0.0
    for poly in polygon_parts(geometry):
        if poly and poly[0]:
            total += abs(signed_area(poly[0]))
    return total


class Grid:
    def __init__(self) -> None:
        self.bins: dict[tuple[int, int], list[dict]] = defaultdict(list)

    def add(self, item: dict) -> None:
        west, south, east, north = item["bbox"]
        x0, x1 = math.floor(west / CELL), math.floor(east / CELL)
        y0, y1 = math.floor(south / CELL), math.floor(north / CELL)
        for ix in range(x0, x1 + 1):
            for iy in range(y0, y1 + 1):
                self.bins[(ix, iy)].append(item)

    def at(self, lon: float, lat: float) -> list[dict]:
        return self.bins.get((math.floor(lon / CELL), math.floor(lat / CELL)), [])


def _attr(attrs: dict, name: str) -> str | None:
    value = attrs.get(name)
    if value is None:
        value = attrs.get(name.upper())
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _tract_label(tract: str, geoid: str) -> str:
    digits = "".join(ch for ch in tract if ch.isdigit()) or (geoid[-6:] if len(geoid) >= 6 else "")
    if not digits:
        return geoid or "Opportunity Zone"
    value = int(digits)
    pretty = str(value // 100) if value % 100 == 0 else f"{value / 100:.2f}".rstrip("0").rstrip(".")
    return f"Census tract {pretty}"


def _prefixed(prefix: str, code: str) -> str:
    upper = " ".join(code.upper().split())
    if upper.startswith(f"{prefix}-"):
        return upper
    return f"{prefix}-{upper}"


def load_polygons(query_url: str, fields: list[str]) -> list[dict]:
    from seed_market_parcels import fetch_by_ids, fetch_object_ids

    ids = fetch_object_ids(query_url, "1=1")
    raw = fetch_by_ids(query_url, ids, fields, batch=120)
    loaded: list[dict] = []
    for item in raw:
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        if not geometry:
            continue
        loaded.append(
            {
                "attributes": item.get("attributes") or {},
                "geometry": geometry,
                "bbox": _bbox(geometry),
                "area": _area(geometry),
            }
        )
    return loaded


def _indexed(rows: list[dict]) -> Grid:
    grid = Grid()
    for row in rows:
        grid.add(row)
    return grid


def _hits(grid: Grid, lon: float, lat: float) -> list[dict]:
    found = []
    for item in grid.at(lon, lat):
        if contains(item["geometry"], lon, lat):
            found.append(item)
    return found


def _smallest(items: list[dict]) -> dict:
    return min(items, key=lambda item: item["area"] or 1e9)


def _limit_prefix(name: str) -> str | None:
    token = name.upper().replace(" ETJ", "").strip()
    return LIMIT_PREFIX.get(token)


def load_eligible_tracts() -> dict[str, bool]:
    payload = json.loads((ROOT / "data" / "fixtures" / "oz2-other-msas.json").read_text())
    found: dict[str, bool] = {}
    for row in payload.get("rows") or []:
        if row.get("county") != "Yadkin" or row.get("state") != "North Carolina":
            continue
        status = str(row.get("status") or "")
        lowered = status.lower()
        if "not designated" not in lowered:
            raise RuntimeError(f"Yadkin OZ 2.0 row {row.get('geoid')} is not labeled eligible-not-designated: {status!r}")
        rural_token = str(row.get("rural") or "").strip().upper()
        if rural_token == "Y":
            rural = True
        elif rural_token == "N":
            rural = False
        else:
            raise RuntimeError(f"Refusing to infer rural status for {row.get('geoid')}: {row.get('rural')!r}")
        geoid = str(row["geoid"])
        if geoid in found and found[geoid] != rural:
            raise RuntimeError(f"Conflicting rural flag for {geoid}")
        found[geoid] = rural
    if not found:
        raise RuntimeError("oz2-other-msas.json has no Yadkin County eligible tracts")
    return found


def load_notice_geoids() -> set[str]:
    payload = json.loads((ROOT / "data" / "fixtures" / "notice-2025-50-rural-geoids.json").read_text())
    if isinstance(payload, dict):
        values = payload.get("geoids") or payload.get("rows") or []
    else:
        values = payload
    return {str(item) for item in values}


def fetch_designated_zones() -> list[dict]:
    from seed_market_parcels import fetch_json

    data = fetch_json(
        HUD_OZ_URL,
        {
            "where": "STATE='37' AND COUNTY='197'",
            "outFields": "GEOID10,TRACT,Rural",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    zones = []
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry")
        geoid = str(props.get("GEOID10") or "")
        if not geoid or not geometry:
            continue
        name = _tract_label(str(props.get("TRACT") or ""), geoid)
        zones.append(
            {
                "geoid": geoid,
                "name": str(name),
                "hudRural": str(props.get("Rural") or "").strip().upper() == "Y",
                "geometry": geometry,
            }
        )
    if not zones:
        raise RuntimeError("HUD Opportunity Zones returned no Yadkin County (197) designated tracts")
    return zones


def fetch_eligible_zones(eligible: dict[str, bool]) -> list[dict]:
    from seed_market_parcels import fetch_json

    quoted = ",".join(f"'{geoid}'" for geoid in sorted(eligible))
    data = fetch_json(
        TIGER_TRACTS_URL,
        {
            "where": f"GEOID IN ({quoted})",
            "outFields": "GEOID,NAME,TRACT",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    zones = []
    seen: set[str] = set()
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry")
        geoid = str(props.get("GEOID") or "")
        if geoid not in eligible or not geometry:
            continue
        seen.add(geoid)
        zones.append(
            {
                "geoid": geoid,
                "name": str(props.get("NAME") or geoid),
                "rural": eligible[geoid],
                "geometry": geometry,
            }
        )
    missing = sorted(set(eligible) - seen)
    if missing:
        raise RuntimeError(f"TIGER 2020 did not return Yadkin eligible tract(s) {', '.join(missing)}")
    return zones


def land_use_classes() -> list[str]:
    """Distinct cropland classes. Fetched only so they can be refused as FLU."""
    from seed_market_parcels import fetch_json

    data = fetch_json(
        f"{GIS}/38/query",
        {
            "where": "1=1",
            "outFields": "CLASS_NAME",
            "returnGeometry": "false",
            "returnDistinctValues": "true",
            "f": "json",
        },
    )
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    classes = []
    for feature in data.get("features") or []:
        name = _attr(feature.get("attributes") or {}, "CLASS_NAME")
        if name:
            classes.append(name)
    if not classes:
        raise RuntimeError("Yadkin Land Use layer returned no CLASS_NAME values")
    upper = {item.upper() for item in classes}
    if not any("CROPLAND" in item or "SOYBEAN" in item or item == "CORN" for item in upper):
        raise RuntimeError(f"Land Use layer did not look like cropland: {classes[:8]}")
    return sorted(classes)


def onemap_cross_check() -> int | None:
    from seed_market_parcels import NC_URL, count_where

    try:
        return count_where(NC_URL, "cntyfips='197' AND gisacres>=5 AND gisacres<=150")
    except Exception as exc:  # noqa: BLE001
        print(f"  OneMap cross-check failed: {exc}", flush=True)
        return None


def _apply_zone(props: dict, prefix: str, code: str, label: str | None) -> None:
    props["zoningCode"] = _prefixed(prefix, code)
    props["zoningDistrict"] = label or code
    props["jurisdictionPrefix"] = prefix
    props["jurisdictionCode"] = prefix


def enrich_yadkin(features: list[dict]) -> dict:
    print("  land use classes (not joined)", flush=True)
    classes = land_use_classes()
    blocked = {item.upper() for item in classes}

    print("  county zoning /40", flush=True)
    county_rows = load_polygons(f"{GIS}/40/query", ["ZONING", "ZONE_NAME", "ACRES"])
    if len(county_rows) < 10:
        raise RuntimeError(f"County zoning layer returned {len(county_rows)} polygons")
    county_grid = _indexed(county_rows)

    town_grids: dict[str, Grid] = {}
    town_names = {spec["prefix"]: spec["name"] for spec in TOWN_LAYERS}
    for spec in TOWN_LAYERS:
        print(f"  {spec['name']} zoning /{spec['layer']}", flush=True)
        rows = load_polygons(f"{GIS}/{spec['layer']}/query", [spec["code"], spec["label"]])
        if not rows:
            raise RuntimeError(f"{spec['name']} zoning layer /{spec['layer']} returned no polygons")
        for row in rows:
            row["prefix"] = spec["prefix"]
            row["code"] = _attr(row["attributes"], spec["code"])
            row["label"] = _attr(row["attributes"], spec["label"])
        usable = [row for row in rows if row["code"]]
        if not usable:
            raise RuntimeError(f"{spec['name']} zoning polygons have no district code")
        town_grids[spec["prefix"]] = _indexed(usable)
        print(f"    {len(usable)} districts", flush=True)

    print("  town limits /45", flush=True)
    limits = load_polygons(f"{GIS}/45/query", ["NAME"])
    if len(limits) < 4:
        raise RuntimeError(f"Town limits layer returned {len(limits)} polygons")
    for row in limits:
        row["name"] = _attr(row["attributes"], "NAME") or ""
        row["prefix"] = _limit_prefix(row["name"])
        row["etj"] = row["name"].upper().endswith("ETJ")
    limit_grid = _indexed(limits)

    print("  designated QOZ and OZ 2.0 tracts", flush=True)
    eligible = load_eligible_tracts()
    notice = load_notice_geoids()
    designated = fetch_designated_zones()
    eligible_zones = fetch_eligible_zones(eligible)
    designated_ids = {zone["geoid"] for zone in designated}
    overlap = designated_ids & set(eligible)
    if overlap:
        raise RuntimeError(f"Designated QOZ GEOID collided with an eligible 2020 tract: {sorted(overlap)}")

    onemap_count = onemap_cross_check()
    counts: dict[str, int] = defaultdict(int)
    designated_n = 0
    eligible_n = 0
    both_n = 0

    for feature in features:
        props = feature["properties"]
        if props.get("flu") not in (None,):
            raise RuntimeError("Yadkin enrich received a parcel that already had FLU")
        props["flu"] = None
        lon, lat = props["centroid"]

        town_hits: list[dict] = []
        for prefix, grid in town_grids.items():
            for item in _hits(grid, lon, lat):
                if item.get("code"):
                    town_hits.append(item)
        limit_hits = [item for item in _hits(limit_grid, lon, lat) if item.get("prefix")]
        corporate = [item for item in limit_hits if not item["etj"]]
        if corporate and not props.get("situsCity"):
            props["situsCity"] = corporate[0]["name"].title()

        county_hits = _hits(county_grid, lon, lat)
        for item in county_hits:
            code = _attr(item["attributes"], "ZONING")
            if code and code.upper() in COUNTY_PLACEHOLDERS:
                counts["TZ"] += 1

        if town_hits:
            limit_prefixes = {item["prefix"] for item in limit_hits}
            preferred = [item for item in town_hits if item["prefix"] in limit_prefixes]
            chosen = _smallest(preferred or town_hits)
            _apply_zone(props, chosen["prefix"], chosen["code"], chosen["label"])
            counts[chosen["prefix"]] += 1
        else:
            base = []
            overlays = []
            for item in county_hits:
                code = _attr(item["attributes"], "ZONING")
                if not code:
                    continue
                token = code.upper()
                if token in COUNTY_PLACEHOLDERS:
                    continue
                label = _attr(item["attributes"], "ZONE_NAME")
                packed = {**item, "code": code, "label": label}
                if token in COUNTY_OVERLAYS:
                    overlays.append(packed)
                else:
                    base.append(packed)
            picked = _smallest(base) if base else (_smallest(overlays) if overlays else None)
            if picked:
                _apply_zone(props, "YAD", picked["code"], picked["label"])
                counts["YAD"] += 1
            else:
                counts["unzoned"] += 1

        zone = next((item for item in designated if contains(item["geometry"], lon, lat)), None)
        if zone:
            props["opportunityZone"] = {
                "inOpportunityZone": True,
                "tractGeoid": zone["geoid"],
                "tractName": zone["name"],
                "source": "hud-fs-13",
                "designatedRural": zone["geoid"] in notice,
            }
            designated_n += 1
        else:
            props["opportunityZone"] = {
                "inOpportunityZone": False,
                "tractGeoid": None,
                "tractName": None,
                "source": "hud-fs-13",
                "designatedRural": None,
            }

        eligible_hit = next((item for item in eligible_zones if contains(item["geometry"], lon, lat)), None)
        if eligible_hit:
            props["oz2Eligibility"] = {
                "eligible": True,
                "rural": eligible_hit["rural"],
                "tractGeoid": eligible_hit["geoid"],
                "tractName": eligible_hit["name"],
                "designation": "eligible-for-nomination",
                "source": "rev-proc-2026-14",
            }
            eligible_n += 1
        else:
            props["oz2Eligibility"] = {
                "eligible": False,
                "rural": None,
                "tractGeoid": None,
                "tractName": None,
                "designation": "not-eligible",
                "source": "rev-proc-2026-14",
            }

        oz = props["opportunityZone"]
        oz2 = props["oz2Eligibility"]
        if oz2["eligible"] and oz["inOpportunityZone"]:
            both_n += 1
            if oz2["tractGeoid"] == oz["tractGeoid"]:
                raise RuntimeError("Eligible tract GEOID was written as the designated QOZ")
        if oz2["designation"] not in {"eligible-for-nomination", "not-eligible"}:
            raise RuntimeError(f"Unexpected OZ 2.0 designation {oz2['designation']}")
        code = str(props.get("zoningCode") or "").upper()
        district = str(props.get("zoningDistrict") or "").upper()
        if code in blocked or district in blocked:
            raise RuntimeError(f"Cropland class stored as zoning on {props.get('parcelId')}: {code}")

    town_joined = sum(counts[prefix] for prefix in town_names)
    if town_joined < 1:
        raise RuntimeError("Town zoning layers loaded but no 5–150 acre centroid hit a town district")
    if counts["YAD"] < 500:
        raise RuntimeError(f"County zoning join looks incomplete ({counts['YAD']} parcels)")
    if eligible_n < 1:
        raise RuntimeError("No Yadkin parcel centroid fell in an OZ 2.0 eligible tract")

    prefix_bits = ", ".join(f"{prefix} {counts[prefix]}" for prefix in ("YAD", *town_names))
    onemap_text = (
        f"NC OneMap cntyfips='197' and gisacres 5–150 returned {onemap_count:,} polygons."
        if onemap_count is not None
        else "NC OneMap cntyfips='197' cross-check did not return a count; county GIS remains the parcel source."
    )
    gap_lines = [
        f"{onemap_text} Stored features: {len(features):,} from county TOTAL_ACRES.",
        (
            f"Zoning joined on {len(features) - counts['unzoned']:,}/{len(features):,} parcels ({prefix_bits}). "
            f"County TZ placeholders skipped on {counts['TZ']:,} centroid hits. "
            "Town district wins over county TZ."
        ),
        (
            f"Designated QOZ centroids: {designated_n:,} in 2010 tract(s) {', '.join(sorted(designated_ids))} (HUD). "
            f"OZ 2.0 eligible centroids: {eligible_n:,} in 2020 tract(s) {', '.join(sorted(eligible))}. "
            f"Parcels in both geographies: {both_n:,}. Eligible is not a designated QOZ."
        ),
    ]
    print("  " + " | ".join(gap_lines), flush=True)
    return {
        "gapLines": gap_lines,
        "parcelSource": f"{GIS}/1",
        "onemapWhere": "cntyfips='197' AND gisacres>=5 AND gisacres<=150",
        "onemapCount": onemap_count,
        "zoningByPrefix": {prefix: counts[prefix] for prefix in ("YAD", *town_names)},
        "townPlaceholderHits": counts["TZ"],
        "unzoned": counts["unzoned"],
        "designatedQozParcels": designated_n,
        "designatedQozGeoids": sorted(designated_ids),
        "oz2EligibleParcels": eligible_n,
        "oz2EligibleGeoids": sorted(eligible),
        "oz2RuralByGeoid": {geoid: eligible[geoid] for geoid in sorted(eligible)},
        "parcelsInBothOzGeographies": both_n,
        "fluJoined": 0,
        "fluGap": "pdf-only",
        "landUseLayer": f"{GIS}/38",
        "ignoredLandUseClasses": classes,
        "fluMap": FLU_MAP,
        "fluPlan": FLU_PLAN,
    }
