#!/usr/bin/env python3
"""Join seven Florida city zoning and future-land-use layers onto existing parcels.

Public REST only. The join is centroid-in-polygon, and only inside that city's
limits. County stubs are not used inside these cities. Parcels outside the
seven cities are left alone, including Pensacola and every still-open municipal
gap. Wrong-state namesakes (Edgewood TX, Bonita NC, Fort Myers SC, Doraville GA)
are rejected by a Florida extent check before any parcel is stamped.

  python3 scripts/join_fl_muni_overlays.py
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parcel_geometry import esri_rings_to_geojson  # noqa: E402

SUMMARY_PATH = ROOT / "data" / "fixtures" / "fl-muni-overlays" / "summary.json"
ORLANDO_META = ROOT / "data" / "fixtures" / "orlando-parcels" / "meta.json"
ORLANDO_SOURCES = ROOT / "data" / "orlando-parcel-sources.json"
USER_AGENT = "darryl-land-search/fl-muni"

# Continental Florida. Edgewood, Texas is about -96.65, 32.70 and fails this box.
FL_BBOX = (-87.7, 24.3, -79.7, 31.1)
EDGEWOOD_TX_BBOX = (-96.85, 32.55, -96.45, 32.85)
COUNTY_STUBS = {"CITY", "MUNICIPAL", "MUNI", "COUNTY"}

# Verified public layers. Fort Myers is the CFMGIS ArcGIS Online service, not
# gis.fortmyers.gov. Bonita is the city EnerGov service, not Lee PA "Future Land Use BS".
CITIES: list[dict[str, Any]] = [
    {
        "id": "sanford",
        "name": "Sanford",
        "county": "Seminole",
        "fips": "12117",
        "prefix": "SAN",
        "anchor": (-81.2731, 28.8028),
        "limits": {
            "url": "https://gis.sanfordfl.gov/server/rest/services/City_Limits/MapServer/0/query",
            "where": "1=1",
            "fields": "OBJECTID",
        },
        "zoning": {
            "url": "https://gis.sanfordfl.gov/server/rest/services/Zoning/MapServer/0/query",
            "where": "1=1",
            "fields": "ZONECODE,ZONEDESC",
            "code": "ZONECODE",
            "label": "ZONEDESC",
        },
        "flu": {
            "url": "https://gis.sanfordfl.gov/server/rest/services/Land_Use/FeatureServer/2/query",
            "where": "1=1",
            "fields": "LANDUSECODE,LANDUSEDESC",
            "code": "LANDUSECODE",
            "label": "LANDUSEDESC",
        },
    },
    {
        "id": "kissimmee",
        "name": "Kissimmee",
        "county": "Osceola",
        "fips": "12097",
        "prefix": "KIS",
        "anchor": (-81.4076, 28.2919),
        "limits": {
            "url": "https://cw.kissimmee.gov/arcgis/rest/services/Address_Parcels_Centerlines/MapServer/7/query",
            "where": "PROPERTY_1='City'",
            "fields": "OBJECTID,PROPERTY_1",
        },
        "zoning": {
            "url": "https://cw.kissimmee.gov/arcgis/rest/services/Zoning_Districts/MapServer/10/query",
            "where": "1=1",
            "fields": "ZONING_COD,SUMMARY_LI",
            "code": "ZONING_COD",
            "label": "SUMMARY_LI",
        },
        "flu": {
            "url": "https://cw.kissimmee.gov/arcgis/rest/services/Future_Land_Use/MapServer/4/query",
            "where": "1=1",
            "fields": "PROP_FLUM,FLU_NAME",
            "code": "PROP_FLUM",
            "label": "FLU_NAME",
        },
    },
    {
        "id": "clermont",
        "name": "Clermont",
        "county": "Lake",
        "fips": "12069",
        "prefix": "CLM",
        "anchor": (-81.7729, 28.5494),
        "limits": {
            "url": "https://gis.lakecountyfl.gov/lakegis/rest/services/CityView/MapServer/16/query",
            "where": "City='CLERMONT'",
            "fields": "OBJECTID,City",
        },
        "zoning": {
            "url": "https://gis.lakecountyfl.gov/lakegis/rest/services/LocalGov/CityZoning/MapServer/1/query",
            "where": "1=1",
            "fields": "ZoningCode,City",
            "code": "ZoningCode",
            "label": "ZoningCode",
        },
        "flu": {
            "url": "https://gis.lakecountyfl.gov/lakegis/rest/services/CityView/MapServer/27/query",
            "where": "1=1",
            "fields": "FLUCode,City",
            "code": "FLUCode",
            "label": "FLUCode",
        },
    },
    {
        "id": "mount-dora",
        "name": "Mount Dora",
        "county": "Lake",
        "fips": "12069",
        "prefix": "MTD",
        "anchor": (-81.6445, 28.8025),
        "limits": {
            "url": "https://gis.lakecountyfl.gov/lakegis/rest/services/CityView/MapServer/16/query",
            "where": "City='MOUNT DORA'",
            "fields": "OBJECTID,City",
        },
        "zoning": {
            "url": "https://gis.lakecountyfl.gov/lakegis/rest/services/LocalGov/CityZoning/MapServer/4/query",
            "where": "1=1",
            "fields": "ZoningCode,City",
            "code": "ZoningCode",
            "label": "ZoningCode",
        },
        "flu": {
            "url": "https://gis.lakecountyfl.gov/lakegis/rest/services/CityView/MapServer/40/query",
            "where": "1=1",
            "fields": "FLUCode,City",
            "code": "FLUCode",
            "label": "FLUCode",
        },
    },
    {
        "id": "sanibel",
        "name": "Sanibel",
        "county": "Lee",
        "fips": "12071",
        "prefix": "SNB",
        "anchor": (-82.0223, 26.4484),
        # Sanibel LDC Ch. 126 zones the island by ecological zone. The same
        # FLUM series is the future land use map. The commercial map is 31
        # commercial polygons and is not the citywide zoning layer.
        "limitsFrom": "zoning",
        "zoning": {
            "url": "https://services7.arcgis.com/OnCt8XFWOgmkvMJE/arcgis/rest/services/Sanibel_Future_Land_Use_Map_Series_Ecological_Zones_Map_1989/FeatureServer/0/query",
            "where": "1=1",
            "fields": "ECO_ZONE,ZONE_NAME",
            "code": "ECO_ZONE",
            "label": "ZONE_NAME",
        },
        "flu": {
            "url": "https://services7.arcgis.com/OnCt8XFWOgmkvMJE/arcgis/rest/services/Sanibel_Future_Land_Use_Map_Series_Ecological_Zones_Map_1989/FeatureServer/0/query",
            "where": "1=1",
            "fields": "ECO_ZONE,ZONE_NAME",
            "code": "ECO_ZONE",
            "label": "ZONE_NAME",
        },
    },
    {
        "id": "fort-myers",
        "name": "Fort Myers",
        "county": "Lee",
        "fips": "12071",
        "prefix": "FTM",
        "anchor": (-81.8707, 26.6406),
        "limits": {
            "url": "https://services1.arcgis.com/T37xMyv8DRNzouiI/arcgis/rest/services/Fort_Myers_City_Boundary/FeatureServer/0/query",
            "where": "1=1",
            "fields": "objectid",
        },
        "zoning": {
            "url": "https://services1.arcgis.com/T37xMyv8DRNzouiI/arcgis/rest/services/Zoning1/FeatureServer/0/query",
            "where": "1=1",
            "fields": "District,DistrictName",
            "code": "District",
            "label": "DistrictName",
        },
        "flu": {
            "url": "https://services1.arcgis.com/T37xMyv8DRNzouiI/arcgis/rest/services/Fort_Myers_Future_Land_Use/FeatureServer/0/query",
            "where": "1=1",
            "fields": "Category,CategoryName",
            "code": "Category",
            "label": "CategoryName",
        },
    },
    {
        "id": "bonita-springs",
        "name": "Bonita Springs",
        "county": "Lee",
        "fips": "12071",
        "prefix": "BNS",
        "anchor": (-81.7787, 26.3398),
        "limits": {
            "url": "https://services9.arcgis.com/YMMDDoyt1fVMlPjl/arcgis/rest/services/FL_Data/FeatureServer/8/query",
            "where": "City='Bonita Springs'",
            "fields": "OBJECTID,City",
        },
        "zoning": {
            "url": "https://services9.arcgis.com/YMMDDoyt1fVMlPjl/arcgis/rest/services/EG_Data_v2/FeatureServer/21/query",
            "where": "1=1",
            "fields": "ZONINGCATEGORY",
            "code": "ZONINGCATEGORY",
            "label": "ZONINGCATEGORY",
        },
        "flu": {
            "url": "https://services9.arcgis.com/YMMDDoyt1fVMlPjl/arcgis/rest/services/EG_Data_v2/FeatureServer/16/query",
            "where": "1=1",
            "fields": "Landuse",
            "code": "Landuse",
            "label": "Landuse",
        },
    },
]

GAP_NOTES = {
    "12069": (
        "Clermont and Mount Dora zoning and future land use are joined from city layers inside those city limits. "
        "Other Lake municipalities stay null."
    ),
    "12097": (
        "Kissimmee zoning and future land use are joined from the city REST layers inside Kissimmee city limits. "
        "Other Osceola municipalities stay null."
    ),
    "12117": (
        "Sanford zoning and future land use are joined from the city REST layers inside Sanford city limits. "
        "Other Seminole municipalities stay null."
    ),
}


def in_bbox(lon: float, lat: float, box: tuple[float, float, float, float]) -> bool:
    west, south, east, north = box
    return west <= lon <= east and south <= lat <= north


def in_florida(lon: float, lat: float) -> bool:
    return in_bbox(lon, lat, FL_BBOX)


def is_edgewood_tx(lon: float, lat: float) -> bool:
    return in_bbox(lon, lat, EDGEWOOD_TX_BBOX)


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def zone_token(value: Any) -> str | None:
    """Keep a short district code when the GIS value is 'R-1 SINGLE FAMILY ...'."""
    text = clean(value)
    if not text:
        return None
    if " " in text:
        head, rest = text.split(" ", 1)
        if head and len(head) <= 24 and rest[:1].isalpha() and len(rest) > 8:
            return head
    return text


def zone_label(code: str | None, raw: Any) -> str | None:
    text = clean(raw)
    if not text:
        return code
    if code and text.upper() == code.upper():
        return code
    return text


def point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def point_in_feature(x: float, y: float, feature: dict) -> bool:
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        rings = geom["coordinates"]
        if not rings or not point_in_ring(x, y, rings[0]):
            return False
        return all(not point_in_ring(x, y, hole) for hole in rings[1:])
    if geom.get("type") == "MultiPolygon":
        for poly in geom["coordinates"]:
            if poly and point_in_ring(x, y, poly[0]) and all(not point_in_ring(x, y, hole) for hole in poly[1:]):
                return True
    return False


def feature_bbox(feature: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, (int, float)):
            return
        if node and isinstance(node[0], (int, float)) and not isinstance(node[0], bool):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        if isinstance(node, list):
            for item in node:
                walk(item)

    walk((feature.get("geometry") or {}).get("coordinates"))
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def ring_area(ring: list) -> float:
    area = 0.0
    for i in range(len(ring) - 1):
        area += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(area) / 2.0


def feature_area(feature: dict) -> float:
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        rings = geom["coordinates"]
        return ring_area(rings[0]) if rings else 0.0
    if geom.get("type") == "MultiPolygon":
        return sum(ring_area(poly[0]) for poly in geom["coordinates"] if poly)
    return 0.0


class SpatialIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = feature.get("_bbox")
        if not bbox:
            return
        west, south, east, north = bbox
        ix0, ix1 = int(west // self.cell), int(east // self.cell)
        iy0, iy1 = int(south // self.cell), int(north // self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 400:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        ix, iy = int(x // self.cell), int(y // self.cell)
        best = None
        best_area = None
        seen: set[int] = set()
        for feature in self.buckets.get((ix, iy), []) + self.broad:
            marker = id(feature)
            if marker in seen:
                continue
            seen.add(marker)
            west, south, east, north = feature["_bbox"]
            if x < west or x > east or y < south or y > north:
                continue
            if not point_in_feature(x, y, feature):
                continue
            area = feature["_area"]
            if best is None or area < best_area:
                best = feature
                best_area = area
        return best


def prepare_feature(geometry: dict, properties: dict) -> dict | None:
    feature = {"type": "Feature", "properties": properties, "geometry": geometry}
    bbox = feature_bbox(feature)
    if not bbox:
        return None
    feature["_bbox"] = bbox
    feature["_area"] = feature_area(feature) or 1e-12
    return feature


def index_features(features: list[dict]) -> SpatialIndex:
    index = SpatialIndex()
    for feature in features:
        index.add(feature)
    return index


def layer_rejection(features: list[dict], anchor: tuple[float, float], label: str, require_anchor_hit: bool) -> str | None:
    if not features:
        return f"{label} returned no polygons"
    centers: list[tuple[float, float]] = []
    for feature in features:
        bbox = feature.get("_bbox")
        if not bbox:
            continue
        west, south, east, north = bbox
        centers.append(((west + east) / 2, (south + north) / 2))
    if not centers:
        return f"{label} has no extent"
    if any(is_edgewood_tx(lon, lat) for lon, lat in centers):
        return f"{label} intersects Edgewood, Texas and was rejected"
    lons = sorted(lon for lon, _lat in centers)
    lats = sorted(lat for _lon, lat in centers)
    median = (lons[len(lons) // 2], lats[len(lats) // 2])
    if not in_florida(*median):
        return f"{label} median {median[0]:.4f},{median[1]:.4f} is outside Florida"
    outside = sum(1 for lon, lat in centers if not in_florida(lon, lat))
    if outside:
        return f"{label} has {outside} polygons outside Florida"
    west = min(box[0] for box in (feature["_bbox"] for feature in features))
    south = min(box[1] for box in (feature["_bbox"] for feature in features))
    east = max(box[2] for box in (feature["_bbox"] for feature in features))
    north = max(box[3] for box in (feature["_bbox"] for feature in features))
    lon, lat = anchor
    if not (west - 0.08 <= lon <= east + 0.08 and south - 0.08 <= lat <= north + 0.08):
        return f"{label} extent does not cover the Florida city anchor {lon},{lat}"
    if require_anchor_hit and not any(point_in_feature(lon, lat, feature) for feature in features):
        return f"{label} does not contain the Florida city anchor {lon},{lat}"
    if is_edgewood_tx(lon, lat) or not in_florida(lon, lat):
        return f"{label} anchor is not in Florida"
    return None


def fetch_json(url: str, params: dict[str, str], timeout: int = 180) -> dict:
    payload = urllib.parse.urlencode(params).encode()
    request = urllib.request.Request(url, data=payload, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def fetch_polygons(url: str, where: str, fields: str) -> list[dict]:
    id_payload = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"})
    if id_payload.get("error"):
        raise RuntimeError(json.dumps(id_payload["error"])[:300])
    object_ids = id_payload.get("objectIds") or []
    object_field = id_payload.get("objectIdFieldName") or "OBJECTID"
    features: list[dict] = []
    step = 80
    for start in range(0, len(object_ids), step):
        chunk = object_ids[start : start + step]
        data = fetch_json(
            url,
            {
                "objectIds": ",".join(str(item) for item in chunk),
                "outFields": fields,
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            },
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        for row in data.get("features") or []:
            geometry = esri_rings_to_geojson((row.get("geometry") or {}).get("rings") or [])
            if not geometry:
                continue
            prepared = prepare_feature(geometry, row.get("attributes") or {})
            if prepared:
                features.append(prepared)
        print(f"    {url.rsplit('/', 2)[-2]} {min(start + step, len(object_ids))}/{len(object_ids)}", flush=True)
    if not object_ids and object_field:
        print(f"    {url} returned no object ids", flush=True)
    return features


def load_indexed_layer(spec: dict, anchor: tuple[float, float], label: str, require_anchor_hit: bool) -> tuple[SpatialIndex, list[dict], str | None]:
    features = fetch_polygons(spec["url"], spec["where"], spec["fields"])
    reason = layer_rejection(features, anchor, label, require_anchor_hit)
    if reason:
        return SpatialIndex(), [], reason
    return index_features(features), features, None


def florida_parcel_files() -> list[Path]:
    roots = [
        ROOT / "data" / "fixtures" / "orlando-parcels",
        ROOT / "data" / "fixtures" / "market-parcels" / "counties",
    ]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.geojson"):
            if "lookup" in path.parts:
                continue
            fips = path.parent.name if path.parent.name.isdigit() else path.stem
            if fips.startswith("12"):
                found.append(path)
    return sorted(found)


def parcel_centroid(feature: dict) -> tuple[float, float] | None:
    props = feature.get("properties") or {}
    centroid = props.get("centroid")
    if isinstance(centroid, list) and len(centroid) >= 2:
        try:
            lon, lat = float(centroid[0]), float(centroid[1])
        except (TypeError, ValueError):
            return None
        if in_florida(lon, lat):
            return lon, lat
    return None


def apply_city(props: dict, city: dict, zoning_hit: dict | None, flu_hit: dict | None) -> tuple[bool, bool]:
    """Stamp city zoning and FLU. Returns (zoning_joined, flu_joined)."""
    prefix = city["prefix"]
    props["jurisdictionPrefix"] = prefix
    props["jurisdictionCode"] = prefix
    zoning_joined = False
    flu_joined = False
    if zoning_hit:
        raw = zoning_hit["properties"].get(city["zoning"]["code"])
        code = zone_token(raw)
        if code:
            props["zoningCode"] = code
            props["zoningDistrict"] = zone_label(code, zoning_hit["properties"].get(city["zoning"]["label"]))
            zoning_joined = True
    elif clean(props.get("zoningCode")) and clean(props.get("zoningCode")).upper() in COUNTY_STUBS:
        props["zoningCode"] = None
        props["zoningDistrict"] = None
    if flu_hit:
        raw = flu_hit["properties"].get(city["flu"]["code"])
        code = zone_token(raw)
        if code:
            label = zone_label(code, flu_hit["properties"].get(city["flu"]["label"]))
            props["flu"] = {
                "code": code,
                "label": label or code,
                "jurisdiction": city["name"],
                "source": city["flu"]["url"].replace("/query", ""),
            }
            flu_joined = True
    elif isinstance(props.get("flu"), dict) and clean((props.get("flu") or {}).get("code")) in COUNTY_STUBS:
        props["flu"] = None
    return zoning_joined, flu_joined


def join_feature(feature: dict, cities: list[dict]) -> str | None:
    """Return the city id stamped, or None when the parcel is outside all seven."""
    props = feature.get("properties") or {}
    if (props.get("state") or "Florida") != "Florida":
        return None
    centroid = parcel_centroid(feature)
    if not centroid:
        return None
    lon, lat = centroid
    if is_edgewood_tx(lon, lat) or not in_florida(lon, lat):
        return None
    containing = []
    for city in cities:
        if city.get("rejected"):
            continue
        hit = city["limitsIndex"].hit(lon, lat)
        if hit:
            containing.append((hit["_area"], city, hit))
    if not containing:
        return None
    _area, city, _limits_hit = min(containing, key=lambda item: item[0])
    zoning_hit = city["zoningIndex"].hit(lon, lat)
    flu_hit = city["fluIndex"].hit(lon, lat)
    apply_city(props, city, zoning_hit, flu_hit)
    return city["id"]


def distinct_codes(features: list[dict], field: str, limit: int = 12) -> list[str]:
    seen: list[str] = []
    for feature in features:
        token = zone_token((feature.get("properties") or {}).get(field))
        if token and token not in seen:
            seen.append(token)
        if len(seen) >= limit:
            break
    return seen


def update_gap_lists(path: Path, counts: dict[str, dict[str, int]]) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text())
    counties = data.get("counties") or []
    for county in counties:
        fips = county.get("fips")
        note = GAP_NOTES.get(fips)
        if not note:
            continue
        stats = counts.get(fips) or {}
        if not stats.get("inside"):
            continue
        gaps = []
        replaced = False
        for gap in county.get("gaps") or []:
            if "No zoning" in gap or "zoning and future land use are joined" in gap or "zoning and FLU are joined" in gap:
                if not replaced:
                    gaps.append(note)
                    replaced = True
                continue
            gaps.append(gap)
        if not replaced:
            gaps.append(note)
        county["gaps"] = gaps
        if "zoningJoinedCount" in county or path == ORLANDO_META:
            county["zoningJoinedCount"] = stats.get("zoning", county.get("zoningJoinedCount"))
            county["fluJoinedCount"] = stats.get("flu", county.get("fluJoinedCount"))
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    prepared: list[dict] = []
    for city in CITIES:
        print(f"Loading {city['name']}", flush=True)
        anchor = tuple(city["anchor"])
        try:
            if city.get("limitsFrom") == "zoning":
                zoning_index, zoning_features, zoning_reason = load_indexed_layer(
                    city["zoning"], anchor, f"{city['name']} zoning", True
                )
                limits_index, limits_features, limits_reason = zoning_index, zoning_features, zoning_reason
                flu_index, flu_features, flu_reason = load_indexed_layer(
                    city["flu"], anchor, f"{city['name']} FLU", False
                )
                if city["flu"]["url"] == city["zoning"]["url"]:
                    flu_index, flu_features, flu_reason = zoning_index, zoning_features, zoning_reason
            else:
                limits_index, limits_features, limits_reason = load_indexed_layer(
                    city["limits"], anchor, f"{city['name']} limits", True
                )
                zoning_index, zoning_features, zoning_reason = load_indexed_layer(
                    city["zoning"], anchor, f"{city['name']} zoning", False
                )
                flu_index, flu_features, flu_reason = load_indexed_layer(
                    city["flu"], anchor, f"{city['name']} FLU", False
                )
        except Exception as exc:  # noqa: BLE001
            limits_reason = zoning_reason = flu_reason = str(exc)[:400]
            limits_index = zoning_index = flu_index = SpatialIndex()
            limits_features = zoning_features = flu_features = []
        rejected = limits_reason or zoning_reason or flu_reason
        city.update(
            {
                "limitsIndex": limits_index,
                "zoningIndex": zoning_index,
                "fluIndex": flu_index,
                "limitsFeatures": limits_features,
                "zoningFeatures": zoning_features,
                "fluFeatures": flu_features,
                "rejected": rejected,
            }
        )
        if rejected:
            print(f"  REJECTED {rejected}", flush=True)
        else:
            print(
                f"  ok limits {len(limits_features)} zoning {len(zoning_features)} flu {len(flu_features)}",
                flush=True,
            )
        prepared.append(city)

    usable = [city for city in prepared if not city.get("rejected")]
    stats = {
        city["id"]: {
            "inside": 0,
            "zoning": 0,
            "flu": 0,
            "zoningMiss": 0,
            "fluMiss": 0,
        }
        for city in CITIES
    }
    fips_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"inside": 0, "zoning": 0, "flu": 0})
    files_changed = 0
    for path in florida_parcel_files():
        text = path.read_text()
        data = json.loads(text)
        changed = False
        for feature in data.get("features") or []:
            before = json.dumps(feature.get("properties"), sort_keys=True)
            city_id = join_feature(feature, usable)
            if not city_id:
                continue
            after = json.dumps(feature.get("properties"), sort_keys=True)
            if before == after:
                # Still inside, but values were already stamped.
                pass
            else:
                changed = True
            props = feature["properties"]
            bucket = stats[city_id]
            bucket["inside"] += 1
            fips = str(props.get("countyFips") or "")
            fips_stats[fips]["inside"] += 1
            if props.get("zoningCode"):
                bucket["zoning"] += 1
                fips_stats[fips]["zoning"] += 1
            else:
                bucket["zoningMiss"] += 1
            flu = props.get("flu") if isinstance(props.get("flu"), dict) else None
            if flu and flu.get("code"):
                bucket["flu"] += 1
                fips_stats[fips]["flu"] += 1
            else:
                bucket["fluMiss"] += 1
        if changed:
            rendered = json.dumps(data, separators=(",", ":"))
            if rendered != text:
                path.write_text(rendered)
                files_changed += 1
                print(f"updated {path.relative_to(ROOT)}", flush=True)

    update_gap_lists(ORLANDO_META, fips_stats)
    update_gap_lists(ORLANDO_SOURCES, fips_stats)

    city_reports = []
    for city in CITIES:
        city_reports.append(
            {
                "id": city["id"],
                "name": city["name"],
                "county": city["county"],
                "fips": city["fips"],
                "prefix": city["prefix"],
                "anchor": list(city["anchor"]),
                "floridaVerified": not bool(city.get("rejected")),
                "rejected": city.get("rejected"),
                "limits": None if city.get("limitsFrom") == "zoning" else city["limits"]["url"].replace("/query", ""),
                "zoning": city["zoning"]["url"].replace("/query", ""),
                "flu": city["flu"]["url"].replace("/query", ""),
                "polygonCounts": {
                    "limits": len(city.get("limitsFeatures") or []),
                    "zoning": len(city.get("zoningFeatures") or []),
                    "flu": len(city.get("fluFeatures") or []),
                },
                "sampleZoning": distinct_codes(city.get("zoningFeatures") or [], city["zoning"]["code"]),
                "sampleFlu": distinct_codes(city.get("fluFeatures") or [], city["flu"]["code"]),
                "parcelsInside": stats[city["id"]]["inside"],
                "zoningJoined": stats[city["id"]]["zoning"],
                "fluJoined": stats[city["id"]]["flu"],
                "zoningMissInside": stats[city["id"]]["zoningMiss"],
                "fluMissInside": stats[city["id"]]["fluMiss"],
            }
        )

    summary = {
        "checkedAt": checked,
        "note": (
            "Centroid join of seven closed Florida city layers onto parcels already on the shelf. "
            "Acreage was not re-extracted. Pensacola stays a gap (HTTP 523). "
            "Other municipal rows stay null. Edgewood, Texas is rejected."
        ),
        "notUsed": [
            "https://gis.fortmyers.gov — prior TLS failure; Fort Myers uses the CFMGIS ArcGIS Online zoning and FLU services",
            "https://gissvr.leepa.org/gissvr/rest/services/Zoning/MapServer/4 — Lee County copy of Fort Myers zoning, not the city service",
            "https://gissvr.leepa.org/gissvr/rest/services/Zoning/MapServer/14 — Lee County Future Land Use BS stub, not Bonita Springs EnerGov",
            "Edgewood, Texas — wrong-state namesake, not Orange County Edgewood and not joined",
        ],
        "leftNull": [
            "Pensacola (Escambia) remains HTTP 523. No zoning was invented.",
            "The still-open municipal rows besides these seven cities were not filled.",
            "Lee County has no parcel polygons on this shelf, so Sanibel, Fort Myers, and Bonita Springs join counts stay zero until parcels exist.",
        ],
        "filesChanged": files_changed,
        "cities": city_reports,
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({city["id"]: {"inside": city["parcelsInside"], "zoning": city["zoningJoined"], "flu": city["fluJoined"], "rejected": city["rejected"]} for city in city_reports}, indent=2))


if __name__ == "__main__":
    main()
