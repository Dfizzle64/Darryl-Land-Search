#!/usr/bin/env python3
"""Stamp Manatee and Sarasota city zoning and future land use onto existing parcels.

Does not download county parcel polygons. Does not invent Opportunity Zones,
school grades, or base flood elevations. North Port and Venice future land use
stay blank. Anna Maria, Bradenton Beach, and Holmes Beach stay blank.

  python3 scripts/join_manatee_sarasota_municipal.py
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
CATALOG_PATH = ROOT / "data" / "manatee-sarasota-municipal.json"
SUMMARY_PATH = ROOT / "data" / "fixtures" / "manatee-sarasota-municipal-join.json"
COUNTY_DIR = ROOT / "data" / "fixtures" / "market-parcels" / "counties"
INDEX_PATH = ROOT / "data" / "fixtures" / "market-parcels" / "index.json"
META_PATH = ROOT / "data" / "fixtures" / "market-parcels" / "markets" / "tampa" / "meta.json"
CACHE = Path("/tmp/dls-manatee-sarasota")
USER_AGENT = "darryl-land-search/manatee-sarasota-municipal"
FROZEN = ("id", "parcelId", "acreage", "centroid", "opportunityZone", "oz2Eligibility", "source")
DOH_GAP = "No zoning or FLU on the Florida DOH extract."
FLU_GAP = "City future land use is not published on a usable layer and was not invented."
EXPECTED = ["Bradenton", "Palmetto", "Longboat Key", "Sarasota", "North Port", "Venice"]


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
    if names != EXPECTED:
        raise SystemExit(f"Unexpected city list: {names}")
    for place in catalog["places"]:
        if place["fluStatus"] == "gap" and place.get("flu"):
            raise SystemExit(f"{place['municipality']} future land use must stay a gap")
        for key in ("zoning", "flu"):
            layer = place.get(key)
            if layer and url_blocked(layer["url"], catalog["blockedUrlFragments"]):
                raise SystemExit(f"{place['municipality']} uses a blocked layer {layer['url']}")
    if any(item.get("cityRest") is not None for item in catalog["partials"]):
        raise SystemExit("Barrier-island towns must not invent a city service")
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

    def add(self, item: dict) -> None:
        west, south, east, north = item["bbox"]
        item["area"] = max(0.0, (east - west) * (north - south))
        ix0, iy0 = math.floor(west / self.cell), math.floor(south / self.cell)
        ix1, iy1 = math.floor(east / self.cell), math.floor(north / self.cell)
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
        for done, fut in enumerate(as_completed(futures), start=1):
            features.extend(fut.result())
            if done % 20 == 0:
                print(f"    {done}/{len(chunks)} batches", flush=True)
    if expected and len(features) < expected * 0.9:
        raise RuntimeError(f"{url} returned {len(features)} of {expected}")
    cached.write_text(json.dumps(features, separators=(",", ":")))
    return features


def verify_layer(catalog: dict, url: str, fips_list: list[str]) -> None:
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
    inside = False
    for fips in fips_list:
        box_west, box_south, box_east, box_north = catalog["counties"][fips]["box"]
        if west >= box_west and south >= box_south and east <= box_east and north <= box_north:
            inside = True
    if not inside or span > catalog["maxCitySpanDegrees"] or span <= 0 or max(abs(west), abs(east)) > 180:
        raise RuntimeError(f"{url} extent ({west:.3f},{south:.3f},{east:.3f},{north:.3f}) is outside the parent county")


def payload(attrs: dict, layer: dict, stubs: set[str]) -> dict | None:
    code = clean(attrs.get(layer["code"]))
    if not code or code.upper() in stubs:
        return None
    desc = clean(attrs.get(layer["desc"])) if layer.get("desc") else None
    if desc and (desc.upper() in stubs or desc == code):
        desc = None
    return {"code": code, "desc": desc, "source": layer["role"]}


def index_layer(catalog: dict, place: dict, layer: dict) -> SpatialIndex:
    verify_layer(catalog, layer["url"], place["fips"])
    raw = download_features(layer["url"], layer["fields"], layer["where"])
    stubs = {item.upper() for item in catalog["stubCodes"]}
    spatial = SpatialIndex()
    boxes = [catalog["counties"][fips]["box"] for fips in place["fips"]]
    kept = 0
    for feature in raw:
        geometry = esri_rings_to_geojson((feature.get("geometry") or {}).get("rings") or [])
        value = payload(feature.get("attributes") or {}, layer, stubs)
        if not geometry or not value:
            continue
        bbox = geometry_bbox(geometry)
        if not bbox:
            continue
        west, south, east, north = bbox
        if not any(west >= box[0] - 0.05 and south >= box[1] - 0.05 and east <= box[2] + 0.05 and north <= box[3] + 0.05 for box in boxes):
            continue
        spatial.add({**value, "geometry": geometry, "bbox": bbox})
        kept += 1
    print(f"    indexed {kept} {layer['role']}", flush=True)
    if kept < 1:
        raise RuntimeError(f"{layer['role']} indexed no polygons inside the county")
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


def replace_gap(props: dict, replacement: str | None) -> None:
    gaps = [gap for gap in (props.get("dataGaps") or []) if gap not in {DOH_GAP, FLU_GAP}]
    if replacement and replacement not in gaps:
        gaps.append(replacement)
    if gaps:
        props["dataGaps"] = gaps


def freeze(feature: dict) -> str:
    props = feature["properties"]
    row = {key: props.get(key) for key in FROZEN}
    row["geometry"] = feature.get("geometry")
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def apply_place(catalog: dict, place: dict, group: list[dict]) -> tuple[dict, list[dict]]:
    print(f"Join {place['municipality']} parcels {len(group)}", flush=True)
    zoning_spatial = index_layer(catalog, place, place["zoning"])
    flu_spatial = index_layer(catalog, place, place["flu"]) if place.get("flu") else None
    overlays = [{"role": place["zoning"]["role"], "url": place["zoning"]["url"]}]
    if place.get("flu"):
        overlays.append({"role": place["flu"]["role"], "url": place["flu"]["url"]})
    zoning_joined = 0
    flu_joined = 0
    for feature in group:
        props = feature["properties"]
        zone = lookup(zoning_spatial, feature)
        flu_hit = lookup(flu_spatial, feature) if flu_spatial is not None else None
        if zone and zone.get("code"):
            props["zoningCode"] = zone["code"]
            props["zoningDistrict"] = zone["code"]
            zoning_joined += 1
            props["municipal"] = {
                "placeId": place["id"],
                "placeName": place["municipality"],
                "zoningLayer": place["zoning"]["url"],
                "fluLayer": place["flu"]["url"] if place.get("flu") and flu_hit else None,
                "zoningLabel": zone.get("desc"),
                "fluGap": FLU_GAP if place["fluStatus"] == "gap" else None,
            }
        if flu_hit and flu_hit.get("code"):
            props["flu"] = {
                "code": flu_hit["code"],
                "label": flu_hit.get("desc") or flu_hit["code"],
                "jurisdiction": place["municipality"],
                "source": flu_hit["source"],
            }
            flu_joined += 1
        note = None
        if place["fluStatus"] == "gap":
            note = FLU_GAP
        elif not zone and not flu_hit:
            note = "City zoning and future land use polygons did not intersect this parcel."
        elif not zone:
            note = "City zoning polygon did not intersect this parcel."
        elif not flu_hit:
            note = "City future land use polygon did not intersect this parcel."
        replace_gap(props, note)
    print(f"  {place['municipality']} zoning {zoning_joined} flu {flu_joined}", flush=True)
    return {
        "parcels": len(group),
        "zoningJoined": zoning_joined,
        "fluJoined": flu_joined,
        "fluStatus": place["fluStatus"],
    }, overlays


def stamp_county(catalog: dict, fips: str, stats: dict[str, dict], overlays: list[dict]) -> dict:
    county = catalog["counties"][fips]
    county_path = COUNTY_DIR / fips / "county.json"
    row = json.loads(county_path.read_text())
    if row.get("source") != county["source"] or row.get("featureCount") != county["featureCount"]:
        raise SystemExit(f"{fips} shelf does not match the DOH extract")
    tiles = [(path, json.loads(path.read_text())) for path in sorted((COUNTY_DIR / fips / "tiles").glob("*.geojson"))]
    features: list[dict] = []
    for _path, collection in tiles:
        features.extend(collection.get("features") or [])
    if len(features) != county["featureCount"]:
        raise SystemExit(f"{fips} tile count {len(features)} != {county['featureCount']}")
    before = [freeze(feature) for feature in features]
    oz_before = sum(1 for feature in features if feature["properties"].get("opportunityZone"))
    by_situs: dict[str, list[dict]] = {}
    for feature in features:
        situs = (feature["properties"].get("situsCity") or "").strip().upper()
        if situs:
            by_situs.setdefault(situs, []).append(feature)
    for place in catalog["places"]:
        if fips not in place["fips"]:
            continue
        group: list[dict] = []
        for situs in place["situs"]:
            group.extend(by_situs.get(situs, []))
        place_stats, place_overlays = apply_place(catalog, place, group)
        stats.setdefault(place["municipality"], {"parcels": 0, "zoningJoined": 0, "fluJoined": 0, "fluStatus": place["fluStatus"]})
        stats[place["municipality"]]["parcels"] += place_stats["parcels"]
        stats[place["municipality"]]["zoningJoined"] += place_stats["zoningJoined"]
        stats[place["municipality"]]["fluJoined"] += place_stats["fluJoined"]
        for item in place_overlays:
            if item not in overlays:
                overlays.append(item)
    for partial in catalog["partials"]:
        if partial["fips"] != fips:
            continue
        for situs in partial["situs"]:
            for feature in by_situs.get(situs, []):
                props = feature["properties"]
                if props.get("zoningCode") or (props.get("flu") or {}).get("code"):
                    raise SystemExit(f"{partial['municipality']} received a zoning or future land use code")
                replace_gap(props, partial["note"])
    after = [freeze(feature) for feature in features]
    if after != before:
        raise SystemExit(f"{fips} parcel id, acreage, geometry, or Opportunity Zone fields changed")
    oz_after = sum(1 for feature in features if feature["properties"].get("opportunityZone"))
    if oz_after != oz_before:
        raise SystemExit(f"{fips} Opportunity Zone count changed")
    stubs = {item.upper() for item in catalog["stubCodes"]}
    for feature in features:
        code = (feature["properties"].get("zoningCode") or "").upper()
        flu_code = ((feature["properties"].get("flu") or {}).get("code") or "").upper()
        if code in stubs or flu_code in stubs:
            raise SystemExit(f"{fips} stored a stub code {code or flu_code}")
    zoning_total = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_total = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    written = 0
    for path, collection in tiles:
        encoded = json.dumps(collection, separators=(",", ":"))
        if encoded == path.read_text():
            continue
        path.write_text(encoded)
        written += 1
    row["gaps"] = gap_lines(catalog, fips, zoning_total, flu_total)
    row["zoningJoinedCount"] = zoning_total
    row["fluJoinedCount"] = flu_total
    county_path.write_text(json.dumps(row, indent=2) + "\n")
    print(f"{county['name']} tiles rewritten {written} zoning {zoning_total} flu {flu_total}", flush=True)
    return {
        "fips": fips,
        "name": county["name"],
        "source": county["source"],
        "featureCount": county["featureCount"],
        "zoningJoinedCount": zoning_total,
        "fluJoinedCount": flu_total,
        "opportunityZoneCount": oz_after,
        "tilesRewritten": written,
    }


def gap_lines(catalog: dict, fips: str, zoning: int, flu: int) -> list[str]:
    county = catalog["counties"][fips]
    if fips == "12081":
        return [
            "8098 source rows collapsed to 7239 parcel ids (duplicate ids, stacked units, or rings that failed the WGS84 check). The acreage query covered the county.",
            f"Florida DOH 5–150 acre parcels ({county['source']}, {zoning} zoning codes and {flu} future land use codes). County parcels were not re-downloaded.",
            "Bradenton and Palmetto zoning and future land use are city layers. Longboat Key uses the town zoning polygons and future land use layer.",
            "Anna Maria, Bradenton Beach, and Holmes Beach stay blank. PDF maps and parcel AM_, BB_, and HB_ fields are not a city service.",
            "Rejected: Northport, Alabama ArcGIS org 3u10F1chkeawsUZY. Manatee County Planning zoning is not copied into these cities.",
        ]
    return [
        f"Florida DOH 5–150 acre parcels ({county['source']}, {zoning} zoning codes and {flu} future land use codes). County parcels were not re-downloaded.",
        "City of Sarasota zoning is Zoning Districts and future land use is FutureLandUse layer 3. The county Hosted/CitySarasotaZoning copy is not used.",
        "North Port and Venice use Sarasota County Hosted zoning. City future land use for those two cities is still a gap.",
        "Longboat Key uses the town layers. Anna Maria is not in this county.",
        "Rejected: Northport, Alabama ArcGIS org 3u10F1chkeawsUZY, the token-gated Venice zoning view, and county FLUBoundary.",
    ]


def patch_lists(catalog: dict, summaries: list[dict]) -> None:
    by_fips = {item["fips"]: item for item in summaries}

    def walk(node: object) -> None:
        if isinstance(node, dict):
            fips = node.get("fips")
            summary = by_fips.get(fips) if isinstance(fips, str) else None
            if summary and node.get("name") == summary["name"]:
                node["gaps"] = gap_lines(catalog, fips, summary["zoningJoinedCount"], summary["fluJoinedCount"])
                node["zoningJoinedCount"] = summary["zoningJoinedCount"]
                node["fluJoinedCount"] = summary["fluJoinedCount"]
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for path in (INDEX_PATH, META_PATH):
        data = json.loads(path.read_text())
        walk(data)
        path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    catalog = load_catalog()
    stats: dict[str, dict] = {}
    overlays: list[dict] = []
    summaries = [stamp_county(catalog, fips, stats, overlays) for fips in ("12081", "12115")]
    for place in catalog["places"]:
        row = stats.get(place["municipality"]) or {}
        if place["fluStatus"] == "city" and (row.get("zoningJoined", 0) < 1 or row.get("fluJoined", 0) < 1):
            raise SystemExit(f"{place['municipality']} did not join zoning and future land use")
        if place["fluStatus"] == "gap" and (row.get("fluJoined", 0) != 0 or row.get("zoningJoined", 0) < 1):
            raise SystemExit(f"{place['municipality']} is not zoning-only: {row}")
    patch_lists(catalog, summaries)
    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "opportunityZonesInvented": 0,
                "schoolGradesInvented": 0,
                "baseFloodElevationsInvented": 0,
                "countyParcelsRedownloaded": False,
                "counties": summaries,
                "byPlace": stats,
                "overlays": overlays,
                "partials": [item["municipality"] for item in catalog["partials"]],
                "rejected": catalog["rejected"],
            },
            indent=2,
        )
        + "\n"
    )
    print("Manatee and Sarasota city overlays joined onto existing county parcels.", flush=True)


if __name__ == "__main__":
    main()
