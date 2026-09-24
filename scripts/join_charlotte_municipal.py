#!/usr/bin/env python3
"""Stamp Punta Gorda zoning and future land use onto existing Charlotte County parcels.

Punta Gorda is the only incorporated city in FIPS 12015. The city layers are
ZoningOfficial_View/0 (Zoning_Cla) and FLU_All_2045/5 (LUName). County
ZONE_='CITY' and NEWLU='City' stubs are not stored. Charlotte, North Carolina,
Punta Gorda, Belize, and BO_Charlotte prefer-official copies are refused.

This script does not download county parcel polygons. This checkout has no
Charlotte County, Florida parcel shelf, so the join records zero stamps and
does not create one. If that shelf is already present, the same city layers
are stamped onto it.

  python3 scripts/join_charlotte_municipal.py
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parcel_geometry import esri_rings_to_geojson  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "charlotte-municipal.json"
SUMMARY_PATH = ROOT / "data" / "fixtures" / "charlotte-municipal-join.json"
COUNTY_DIR = ROOT / "data" / "fixtures" / "market-parcels" / "counties"
FIPS = "12015"
CACHE = Path("/tmp/dls-charlotte-municipal")
USER_AGENT = "darryl-land-search/charlotte-municipal"
FROZEN = ("id", "parcelId", "acreage", "centroid", "opportunityZone", "oz2Eligibility", "source")


def fetch_json(url: str, params: dict | None = None, timeout: int = 120, retries: int = 4) -> dict:
    payload = urllib.parse.urlencode(params or {}).encode()
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and data.get("error"):
                raise RuntimeError(json.dumps(data["error"])[:300])
            return data
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed {url[:160]}: {last}")


def clean(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        text = str(int(value)) if value.is_integer() else str(value)
    elif isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if not text or text.lower() in {"null", "none", "nan"}:
        return None
    return text


def query_url(url: str) -> str:
    return url if url.endswith("/query") else url.rstrip("/") + "/query"


def url_blocked(url: str, fragments: list[str]) -> bool:
    lowered = url.lower()
    return any(fragment.lower() in lowered for fragment in fragments)


def load_catalog() -> dict:
    catalog = json.loads(CATALOG_PATH.read_text())
    if not catalog.get("doNotInventOpportunityZones") or not catalog.get("doNotRedownloadCountyParcels"):
        raise SystemExit("Catalog must refuse invented Opportunity Zones and new county parcels")
    if not catalog.get("doNotInventSchoolGrades") or not catalog.get("doNotInventBaseFloodElevations"):
        raise SystemExit("Catalog must refuse invented school grades and base flood elevations")
    names = [place["municipality"] for place in catalog["places"]]
    if names != ["Punta Gorda"]:
        raise SystemExit(f"Unexpected city list: {names}")
    county = catalog["counties"][FIPS]
    if county.get("parcelBaseline") or county.get("featureCount"):
        raise SystemExit("Catalog must not claim a Charlotte County parcel shelf that this join downloads")
    for place in catalog["places"]:
        if place["fluStatus"] != "city" or not place.get("flu"):
            raise SystemExit("Punta Gorda must carry city zoning and future land use")
        for key in ("zoning", "flu"):
            layer = place[key]
            if url_blocked(layer["url"], catalog["blockedUrlFragments"]):
                raise SystemExit(f"{place['municipality']} uses a blocked layer {layer['url']}")
    return catalog


def point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_geometry(x: float, y: float, geometry: dict) -> bool:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if gtype == "Polygon":
        if not coords or not point_in_ring(x, y, coords[0]):
            return False
        return all(not point_in_ring(x, y, hole) for hole in coords[1:])
    if gtype == "MultiPolygon":
        for poly in coords:
            if poly and point_in_ring(x, y, poly[0]) and all(not point_in_ring(x, y, hole) for hole in poly[1:]):
                return True
    return False


def geometry_bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: object) -> None:
        if isinstance(node, list) and node and isinstance(node[0], (int, float)) and not isinstance(node[0], bool):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        if isinstance(node, list):
            for item in node:
                walk(item)

    walk(geometry.get("coordinates"))
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


class SpatialIndex:
    def __init__(self, cell: float = 0.01) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = {}
        self.broad: list[dict] = []
        self.count = 0

    def add(self, item: dict) -> None:
        west, south, east, north = item["bbox"]
        item["area"] = max(0.0, (east - west) * (north - south))
        ix0, iy0 = math.floor(west / self.cell), math.floor(south / self.cell)
        ix1, iy1 = math.floor(east / self.cell), math.floor(north / self.cell)
        self.count += 1
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 80:
            self.broad.append(item)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets.setdefault((ix, iy), []).append(item)

    def hit(self, x: float, y: float) -> dict | None:
        ix, iy = math.floor(x / self.cell), math.floor(y / self.cell)
        found: list[dict] = []
        seen: set[int] = set()
        for item in self.buckets.get((ix, iy), []) + self.broad:
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            west, south, east, north = item["bbox"]
            if x < west or x > east or y < south or y > north:
                continue
            if point_in_geometry(x, y, item["geometry"]):
                found.append(item)
        if not found:
            return None
        found.sort(key=lambda item: item["area"])
        return found[0]


def cache_path(url: str, fields: list[str], where: str) -> Path:
    key = hashlib.sha1(f"{url}|{','.join(fields)}|{where}".encode()).hexdigest()[:20]
    return CACHE / f"{key}.json"


def download_features(url: str, fields: list[str], where: str) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = cache_path(url, fields, where)
    if cached.exists():
        return json.loads(cached.read_text())
    query = query_url(url)
    expected = int(fetch_json(query, {"where": where, "returnCountOnly": "true", "f": "json"}).get("count") or 0)
    ids = [int(i) for i in (fetch_json(query, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180).get("objectIds") or [])]
    print(f"  {url.split('/services/')[-1][:80]} count {expected} ids {len(ids)}", flush=True)
    if expected and not ids:
        raise RuntimeError(f"No object ids for {url}")

    def pull(chunk: list[int]) -> list[dict]:
        return fetch_json(
            query,
            {
                "objectIds": ",".join(str(i) for i in chunk),
                "outFields": ",".join(fields),
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            },
            timeout=180,
        ).get("features") or []

    features: list[dict] = []
    chunks = [ids[index : index + 80] for index in range(0, len(ids), 80)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(pull, chunk) for chunk in chunks]
        for fut in as_completed(futures):
            features.extend(fut.result())
    if expected and len(features) < expected * 0.9:
        raise RuntimeError(f"{url} returned {len(features)} of {expected}")
    cached.write_text(json.dumps(features, separators=(",", ":")))
    return features


def verify_layer(catalog: dict, url: str) -> None:
    if url_blocked(url, catalog["blockedUrlFragments"]):
        raise RuntimeError(f"{url} is blocked and was not queried")
    meta = fetch_json(url, {"f": "json"}, timeout=60, retries=3)
    if "Polygon" not in str(meta.get("geometryType") or ""):
        raise RuntimeError(f"{url} did not return a polygon layer")
    extent = (
        fetch_json(query_url(url), {"where": "1=1", "returnExtentOnly": "true", "outSR": "4326", "f": "json"}, timeout=60).get("extent")
        or {}
    )
    west, south, east, north = (float(extent[key]) for key in ("xmin", "ymin", "xmax", "ymax"))
    span = max(east - west, north - south)
    box_west, box_south, box_east, box_north = catalog["counties"][FIPS]["box"]
    inside = west >= box_west and south >= box_south and east <= box_east and north <= box_north
    if not inside or span > catalog["maxCitySpanDegrees"] or span <= 0:
        raise RuntimeError(f"{url} extent ({west:.3f},{south:.3f},{east:.3f},{north:.3f}) is outside Charlotte County, Florida")


def payload(attrs: dict, layer: dict, stubs: set[str]) -> dict | None:
    code = clean(attrs.get(layer["code"]))
    if not code or code.upper() in stubs:
        return None
    desc = clean(attrs.get(layer["desc"])) if layer.get("desc") else None
    if desc and (desc.upper() in stubs or desc == code):
        desc = None
    return {"code": code, "desc": desc, "source": layer["role"]}


def index_layer(catalog: dict, place: dict, layer: dict) -> SpatialIndex:
    verify_layer(catalog, layer["url"])
    raw = download_features(layer["url"], layer["fields"], layer["where"])
    stubs = {item.upper() for item in catalog["stubCodes"]}
    spatial = SpatialIndex()
    box = catalog["counties"][FIPS]["box"]
    for feature in raw:
        geometry = esri_rings_to_geojson((feature.get("geometry") or {}).get("rings") or [])
        value = payload(feature.get("attributes") or {}, layer, stubs)
        if not geometry or not value:
            continue
        bbox = geometry_bbox(geometry)
        if not bbox:
            continue
        west, south, east, north = bbox
        if not (west >= box[0] - 0.02 and south >= box[1] - 0.02 and east <= box[2] + 0.02 and north <= box[3] + 0.02):
            continue
        spatial.add({**value, "geometry": geometry, "bbox": bbox})
    print(f"    indexed {spatial.count} {layer['role']}", flush=True)
    if spatial.count < 1:
        raise RuntimeError(f"{layer['role']} indexed no polygons inside Charlotte County, Florida")
    return spatial


def candidate_points(feature: dict) -> list[tuple[float, float]]:
    centroid = feature["properties"].get("centroid") or [None, None]
    points: list[tuple[float, float]] = []
    if centroid[0] is not None:
        points.append((float(centroid[0]), float(centroid[1])))
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []
    outer: list = []
    if geometry.get("type") == "Polygon" and coords:
        outer = coords[0]
    elif geometry.get("type") == "MultiPolygon" and coords and coords[0]:
        outer = coords[0][0]
    if len(outer) < 4:
        return points
    xs = [point[0] for point in outer]
    ys = [point[1] for point in outer]
    west, east, south, north = min(xs), max(xs), min(ys), max(ys)
    if east == west or north == south:
        return points
    for i in range(4):
        for j in range(4):
            x = west + (east - west) * (i + 0.5) / 4
            y = south + (north - south) * (j + 0.5) / 4
            if point_in_geometry(x, y, geometry):
                points.append((x, y))
            if len(points) >= 5:
                return points
    return points


def lookup(spatial: SpatialIndex, feature: dict) -> dict | None:
    for x, y in candidate_points(feature):
        hit = spatial.hit(x, y)
        if hit:
            return {"code": hit["code"], "desc": hit.get("desc"), "source": hit["source"]}
    return None


def freeze(feature: dict) -> str:
    props = feature["properties"]
    row = {key: props.get(key) for key in FROZEN}
    row["geometry"] = feature.get("geometry")
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def stamp_existing(catalog: dict, place: dict, zoning_spatial: SpatialIndex, flu_spatial: SpatialIndex) -> dict:
    county_path = COUNTY_DIR / FIPS / "county.json"
    row = json.loads(county_path.read_text())
    tiles = [(path, json.loads(path.read_text())) for path in sorted((COUNTY_DIR / FIPS / "tiles").glob("*.geojson"))]
    features: list[dict] = []
    for _path, collection in tiles:
        features.extend(collection.get("features") or [])
    if len(features) != row.get("featureCount"):
        raise SystemExit(f"{FIPS} tile count {len(features)} != county.json {row.get('featureCount')}")
    before = [freeze(feature) for feature in features]
    oz_before = sum(1 for feature in features if feature["properties"].get("opportunityZone"))
    situs_names = {item.upper() for item in place["situs"]}
    group = [
        feature
        for feature in features
        if (feature["properties"].get("situsCity") or "").strip().upper() in situs_names
    ]
    zoning_joined = 0
    flu_joined = 0
    stubs = {item.upper() for item in catalog["stubCodes"]}
    for feature in group:
        props = feature["properties"]
        zone = lookup(zoning_spatial, feature)
        flu_hit = lookup(flu_spatial, feature)
        if zone and zone.get("code"):
            props["zoningCode"] = zone["code"]
            props["zoningDistrict"] = zone["code"]
            zoning_joined += 1
            props["municipal"] = {
                "placeId": place["id"],
                "placeName": place["municipality"],
                "zoningLayer": place["zoning"]["url"],
                "fluLayer": place["flu"]["url"] if flu_hit else None,
                "zoningLabel": zone.get("desc"),
            }
        if flu_hit and flu_hit.get("code"):
            props["flu"] = {
                "code": flu_hit["code"],
                "label": flu_hit.get("desc") or flu_hit["code"],
                "jurisdiction": place["municipality"],
                "source": flu_hit["source"],
            }
            flu_joined += 1
    after = [freeze(feature) for feature in features]
    if after != before:
        raise SystemExit(f"{FIPS} parcel id, acreage, geometry, or Opportunity Zone fields changed")
    oz_after = sum(1 for feature in features if feature["properties"].get("opportunityZone"))
    if oz_after != oz_before:
        raise SystemExit(f"{FIPS} Opportunity Zone count changed")
    for feature in features:
        code = (feature["properties"].get("zoningCode") or "").upper()
        flu_code = ((feature["properties"].get("flu") or {}).get("code") or "").upper()
        if code in stubs or flu_code in stubs:
            raise SystemExit(f"{FIPS} stored a stub code {code or flu_code}")
    zoning_total = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_total = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    written = 0
    for path, collection in tiles:
        encoded = json.dumps(collection, separators=(",", ":"))
        if encoded == path.read_text():
            continue
        path.write_text(encoded)
        written += 1
    row["zoningJoinedCount"] = zoning_total
    row["fluJoinedCount"] = flu_total
    county_path.write_text(json.dumps(row, indent=2) + "\n")
    print(f"Punta Gorda zoning {zoning_joined} flu {flu_joined} tiles {written}", flush=True)
    if zoning_total < 1 or flu_total < 1:
        raise SystemExit("Existing Charlotte County parcels did not receive city zoning and future land use")
    return {
        "fips": FIPS,
        "name": "Charlotte",
        "source": row.get("source"),
        "featureCount": len(features),
        "zoningJoinedCount": zoning_total,
        "fluJoinedCount": flu_total,
        "opportunityZoneCount": oz_after,
        "tilesRewritten": written,
        "parcels": len(group),
        "zoningJoined": zoning_joined,
        "fluJoined": flu_joined,
    }


def main() -> None:
    catalog = load_catalog()
    place = catalog["places"][0]
    zoning_spatial = index_layer(catalog, place, place["zoning"])
    flu_spatial = index_layer(catalog, place, place["flu"])
    tile_dir = COUNTY_DIR / FIPS / "tiles"
    has_tiles = tile_dir.is_dir() and any(tile_dir.glob("*.geojson"))
    if has_tiles:
        stamped = stamp_existing(catalog, place, zoning_spatial, flu_spatial)
        county_row = stamped
        place_row = {
            "parcels": stamped["parcels"],
            "zoningJoined": stamped["zoningJoined"],
            "fluJoined": stamped["fluJoined"],
            "indexedZoning": zoning_spatial.count,
            "indexedFlu": flu_spatial.count,
            "fluStatus": "city",
        }
        baseline = True
    else:
        if (COUNTY_DIR / FIPS).exists():
            raise SystemExit(f"{FIPS} folder exists without tiles; refusing to invent a parcel shelf")
        county_row = {
            "fips": FIPS,
            "name": "Charlotte",
            "source": None,
            "featureCount": 0,
            "zoningJoinedCount": 0,
            "fluJoinedCount": 0,
            "opportunityZoneCount": 0,
            "tilesRewritten": 0,
        }
        place_row = {
            "parcels": 0,
            "zoningJoined": 0,
            "fluJoined": 0,
            "indexedZoning": zoning_spatial.count,
            "indexedFlu": flu_spatial.count,
            "fluStatus": "city",
        }
        baseline = False
        print("No Charlotte County, Florida parcel shelf. City layers indexed and nothing was stamped.", flush=True)
    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "opportunityZonesInvented": 0,
                "schoolGradesInvented": 0,
                "baseFloodElevationsInvented": 0,
                "countyParcelsRedownloaded": False,
                "parcelBaseline": baseline,
                "counties": [county_row],
                "byPlace": {"Punta Gorda": place_row},
                "overlays": [
                    {"role": place["zoning"]["role"], "url": place["zoning"]["url"]},
                    {"role": place["flu"]["role"], "url": place["flu"]["url"]},
                ],
                "rejected": catalog["rejected"],
            },
            indent=2,
        )
        + "\n"
    )
    print("Punta Gorda city overlays checked. County parcels were not downloaded.", flush=True)


if __name__ == "__main__":
    main()
