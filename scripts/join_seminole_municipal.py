#!/usr/bin/env python3
"""Stamp Seminole County city zoning and future land use onto existing parcels.

Does not download county parcel polygons. Does not invent Opportunity Zones.
Longwood stays blank. County Land_Use CITY stubs are not stored. Oviedo uses
the city DevelopmentServices MapServer, not the retired AGOL DSZoning service.

  python3 scripts/join_seminole_municipal.py
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
CATALOG_PATH = ROOT / "data" / "seminole-municipal.json"
SUMMARY_PATH = ROOT / "data" / "fixtures" / "seminole-municipal-join.json"
TILES = ROOT / "data" / "fixtures" / "orlando-parcels" / "tiles" / "12117"
META_PATH = ROOT / "data" / "fixtures" / "orlando-parcels" / "meta.json"
SOURCES_PATH = ROOT / "data" / "orlando-parcel-sources.json"
CACHE = Path("/tmp/dls-seminole-municipal")
USER_AGENT = "darryl-land-search/seminole-municipal"
FIPS = "12117"
FROZEN = ("id", "parcelId", "acreage", "centroid", "opportunityZone", "oz2Eligibility", "source")
DOH_ZONING_GAP = "No zoning or future land use on the Florida DOH EHWATER extract. Owner, sale, and tax are the public FDOR fields when that roll has them."
LONGWOOD_GAP = "Longwood has no public zoning or future land use service. County Land_Use CITY stubs were not stored."


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


def norm_id(value: object) -> str | None:
    text = clean(value)
    if not text:
        return None
    key = "".join(ch for ch in text.upper() if ch.isalnum())
    return key or None


def query_url(url: str) -> str:
    return url if url.endswith("/query") else url.rstrip("/") + "/query"


def url_blocked(url: str, fragments: list[str]) -> bool:
    lowered = url.lower()
    return any(fragment.lower() in lowered for fragment in fragments)


def load_catalog() -> dict:
    catalog = json.loads(CATALOG_PATH.read_text())
    if not catalog.get("doNotInventOpportunityZones"):
        raise SystemExit("Catalog must keep doNotInventOpportunityZones true")
    if not catalog.get("doNotRedownloadCountyParcels"):
        raise SystemExit("Catalog must keep doNotRedownloadCountyParcels true")
    names = [place["municipality"] for place in catalog["places"]]
    if names != ["Casselberry", "Winter Springs", "Lake Mary", "Sanford", "Oviedo", "Altamonte Springs"]:
        raise SystemExit(f"Unexpected city list: {names}")
    fragments = catalog["blockedUrlFragments"]
    for place in catalog["places"]:
        for layer in (place["zoning"], place["flu"]):
            if url_blocked(layer["url"], fragments):
                raise SystemExit(f"{place['municipality']} uses a blocked layer {layer['url']}")
            if "DSZoning" in layer["url"]:
                raise SystemExit("Oviedo retired DSZoning must not be called")
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
    counted = fetch_json(query, {"where": where, "returnCountOnly": "true", "f": "json"})
    expected = int(counted.get("count") or 0)
    id_payload = fetch_json(query, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    ids = [int(i) for i in (id_payload.get("objectIds") or [])]
    print(f"  {url.split('/services/')[-1][:80]} count {expected} ids {len(ids)}", flush=True)
    if expected and not ids:
        raise RuntimeError(f"No object ids for {url}")

    def pull(chunk: list[int]) -> list[dict]:
        params = {
            "objectIds": ",".join(str(i) for i in chunk),
            "outFields": ",".join(fields),
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        }
        return fetch_json(query, params, timeout=180).get("features") or []

    features: list[dict] = []
    chunks = [ids[index : index + 80] for index in range(0, len(ids), 80)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(pull, chunk): chunk for chunk in chunks}
        for done, fut in enumerate(as_completed(futures), start=1):
            features.extend(fut.result())
            if done % 25 == 0:
                print(f"    {done}/{len(chunks)} batches", flush=True)
    if expected and len(features) < expected * 0.9:
        raise RuntimeError(f"{url} returned {len(features)} of {expected}")
    cached.write_text(json.dumps(features, separators=(",", ":")))
    return features


def verify_layer(catalog: dict, url: str) -> None:
    if url_blocked(url, catalog["blockedUrlFragments"]):
        raise RuntimeError(f"{url} is blocked and was not queried")
    meta = fetch_json(url, {"f": "json"}, timeout=60, retries=3)
    if meta.get("error") or "Polygon" not in str(meta.get("geometryType") or ""):
        raise RuntimeError(f"{url} did not return a polygon layer")
    extent = (
        fetch_json(
            query_url(url),
            {"where": "1=1", "returnExtentOnly": "true", "outSR": "4326", "f": "json"},
            timeout=60,
            retries=3,
        ).get("extent")
        or {}
    )
    west, south, east, north = (float(extent[key]) for key in ("xmin", "ymin", "xmax", "ymax"))
    box_west, box_south, box_east, box_north = catalog["box"]
    span = max(east - west, north - south)
    outside = west < box_west or south < box_south or east > box_east or north > box_north
    if outside or span > catalog["maxCitySpanDegrees"] or span <= 0 or max(abs(west), abs(east)) > 180:
        raise RuntimeError(f"{url} extent ({west:.3f},{south:.3f},{east:.3f},{north:.3f}) is outside Seminole County")
    count = int(
        fetch_json(query_url(url), {"where": "1=1", "returnCountOnly": "true", "f": "json"}, timeout=60, retries=3).get("count")
        or 0
    )
    if count < 10 or count > 40000:
        raise RuntimeError(f"{url} feature count {count} is not a city overlay")


def payload(attrs: dict, layer: dict, stubs: set[str]) -> dict | None:
    code = clean(attrs.get(layer["code"]))
    if not code or code.upper() in stubs:
        return None
    desc = clean(attrs.get(layer["desc"])) if layer.get("desc") else None
    if desc and desc.upper() in stubs:
        desc = None
    if desc == code:
        desc = None
    return {"code": code, "desc": desc, "source": layer["role"]}


def index_layer(catalog: dict, place: dict, layer: dict) -> tuple[dict[str, dict], SpatialIndex]:
    verify_layer(catalog, layer["url"])
    fields = list(dict.fromkeys([*layer["fields"], *([place["idField"]] if place.get("idField") else [])]))
    raw = download_features(layer["url"], fields, layer["where"])
    stubs = {item.upper() for item in catalog["stubCodes"]}
    by_id: dict[str, dict] = {}
    spatial = SpatialIndex()
    box = catalog["box"]
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
        if west < box[0] - 0.02 or south < box[1] - 0.02 or east > box[2] + 0.02 or north > box[3] + 0.02:
            continue
        item = {**value, "geometry": geometry, "bbox": bbox}
        spatial.add(item)
        kept += 1
        if place.get("idField"):
            key = norm_id((feature.get("attributes") or {}).get(place["idField"]))
            if key and key not in by_id:
                by_id[key] = value
    print(f"    indexed {kept} {layer['role']} ids {len(by_id)}", flush=True)
    if kept < 1:
        raise RuntimeError(f"{layer['role']} indexed no polygons inside Seminole County")
    return by_id, spatial


def candidate_points(feature: dict) -> list[tuple[float, float]]:
    centroid = feature["properties"].get("centroid") or [None, None]
    points: list[tuple[float, float]] = []
    if centroid[0] is not None:
        points.append((float(centroid[0]), float(centroid[1])))
    geometry = feature.get("geometry") or {}
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    outer: list = []
    if gtype == "Polygon" and coords:
        outer = coords[0]
    elif gtype == "MultiPolygon" and coords and coords[0]:
        outer = coords[0][0]
    if len(outer) < 4:
        return points
    xs = [point[0] for point in outer]
    ys = [point[1] for point in outer]
    west, east = min(xs), max(xs)
    south, north = min(ys), max(ys)
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


def lookup(by_id: dict[str, dict], spatial: SpatialIndex, feature: dict) -> dict | None:
    key = norm_id(feature["properties"].get("parcelId"))
    if key and key in by_id:
        return by_id[key]
    for x, y in candidate_points(feature):
        hit = spatial.hit(x, y)
        if hit:
            return {"code": hit["code"], "desc": hit.get("desc"), "source": hit["source"]}
    return None


def replace_doh_gap(props: dict, replacement: str | None) -> None:
    gaps = [gap for gap in (props.get("dataGaps") or []) if gap != DOH_ZONING_GAP and gap != LONGWOOD_GAP]
    if replacement and replacement not in gaps:
        gaps.append(replacement)
    props["dataGaps"] = gaps


def freeze(feature: dict) -> str:
    props = feature["properties"]
    payload_row = {key: props.get(key) for key in FROZEN}
    payload_row["geometry"] = feature.get("geometry")
    return json.dumps(payload_row, sort_keys=True, separators=(",", ":"))


def stamp(catalog: dict) -> dict:
    tiles = [(path, json.loads(path.read_text())) for path in sorted(TILES.glob("*.geojson"))]
    features: list[dict] = []
    for _path, collection in tiles:
        features.extend(collection.get("features") or [])
    if len(features) != 4788:
        raise SystemExit(f"Seminole tile count {len(features)} is not the existing 4,788 parcel shelf")
    before = [freeze(feature) for feature in features]
    oz_before = sum(1 for feature in features if feature["properties"].get("opportunityZone"))
    by_situs: dict[str, list[dict]] = {}
    for feature in features:
        situs = (feature["properties"].get("situsCity") or "").strip().upper()
        if situs:
            by_situs.setdefault(situs, []).append(feature)

    stats: dict[str, dict] = {}
    overlays: list[dict] = []
    for place in catalog["places"]:
        group: list[dict] = []
        for situs in place["situs"]:
            group.extend(by_situs.get(situs, []))
        print(f"Join {place['municipality']} parcels {len(group)}", flush=True)
        zoning_ids, zoning_spatial = index_layer(catalog, place, place["zoning"])
        flu_ids, flu_spatial = index_layer(catalog, place, place["flu"])
        overlays.append({"role": place["zoning"]["role"], "url": place["zoning"]["url"]})
        overlays.append({"role": place["flu"]["role"], "url": place["flu"]["url"]})
        zoning_joined = 0
        flu_joined = 0
        for feature in group:
            props = feature["properties"]
            zone = lookup(zoning_ids, zoning_spatial, feature)
            flu_hit = lookup(flu_ids, flu_spatial, feature)
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
                    "fluGap": None,
                }
            else:
                props["zoningCode"] = None
                props["zoningDistrict"] = None
            if flu_hit and flu_hit.get("code"):
                props["flu"] = {
                    "code": flu_hit["code"],
                    "label": flu_hit.get("desc") or flu_hit["code"],
                    "jurisdiction": place["municipality"],
                    "source": flu_hit["source"],
                }
                flu_joined += 1
                if props.get("municipal"):
                    props["municipal"]["fluLayer"] = place["flu"]["url"]
            else:
                props["flu"] = None
            if zone or flu_hit:
                note = None
                if not zone:
                    note = "City zoning polygon did not intersect this parcel."
                elif not flu_hit:
                    note = "City future land use polygon did not intersect this parcel."
                replace_doh_gap(props, note)
            else:
                replace_doh_gap(props, "City zoning and future land use polygons did not intersect this parcel.")
        stats[place["municipality"]] = {
            "parcels": len(group),
            "zoningJoined": zoning_joined,
            "fluJoined": flu_joined,
        }
        print(f"  {place['municipality']} zoning {zoning_joined} flu {flu_joined}", flush=True)
        if group and (zoning_joined < 1 or flu_joined < 1):
            raise SystemExit(f"{place['municipality']} did not join zoning and future land use")

    for situs in catalog["gaps"][0]["situs"]:
        for feature in by_situs.get(situs, []):
            props = feature["properties"]
            if props.get("zoningCode") or (props.get("flu") or {}).get("code"):
                raise SystemExit("Longwood received a zoning or future land use code")
            replace_doh_gap(props, LONGWOOD_GAP)

    after = [freeze(feature) for feature in features]
    if after != before:
        raise SystemExit("Seminole parcel id, acreage, geometry, or Opportunity Zone fields changed")
    oz_after = sum(1 for feature in features if feature["properties"].get("opportunityZone"))
    if oz_after != oz_before:
        raise SystemExit(f"Opportunity Zone count changed {oz_before} -> {oz_after}")
    stubs = {item.upper() for item in catalog["stubCodes"]}
    for feature in features:
        code = (feature["properties"].get("zoningCode") or "").upper()
        if code in stubs:
            raise SystemExit(f"Stub zoning code stored: {code}")

    zoning_total = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_total = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    written = 0
    for path, collection in tiles:
        encoded = json.dumps(collection, separators=(",", ":"))
        if encoded == path.read_text():
            continue
        path.write_text(encoded)
        written += 1
    print(f"Seminole tiles rewritten {written} zoning {zoning_total} flu {flu_total}", flush=True)
    summary = {
        "fips": FIPS,
        "source": catalog["source"],
        "featureCount": len(features),
        "zoningJoinedCount": zoning_total,
        "fluJoinedCount": flu_total,
        "opportunityZonesInvented": 0,
        "opportunityZoneCount": oz_after,
        "countyParcelsRedownloaded": False,
        "tilesRewritten": written,
        "byPlace": stats,
        "overlays": overlays,
        "rejected": catalog["rejected"],
        "gaps": [gap["municipality"] for gap in catalog["gaps"]],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def gap_lines(summary: dict) -> list[str]:
    zoning = summary["zoningJoinedCount"]
    flu = summary["fluJoinedCount"]
    return [
        "Acreage band is 5.0–150.0 acres (FDOR LND_SQFOOT / 43560). Parcels under 5 or over 150 are excluded.",
        (
            f"City zoning and future land use are joined for Casselberry, Winter Springs, Lake Mary, Sanford, Oviedo, "
            f"and Altamonte Springs onto the existing DOH parcels ({zoning} zoning, {flu} future land use). "
            "Casselberry joins on PARCEL and Winter Springs on PIN, then a point inside the parcel. "
            "The other four cities are spatial. Oviedo uses maps.cityofoviedo.net DevelopmentServices MapServer 11 and 10. "
            "The retired AGOL DSZoning service is not called."
        ),
        "Longwood stays blank. County Land_Use FeatureServer 0 and 1 are not stamped, and CITY or SEMINOLE COUNTY placeholders are not stored.",
        "Unincorporated situs labels and Winter Park, Apopka, and Maitland stay blank.",
        "OZ 2.0 here is the seven-market rural-eligible tract pack only, not every eligible tract in the county.",
        "Median household income and FDOT AADT are joined at query time for Florida counties, not stored on each tile.",
    ]


def patch_meta(summary: dict) -> None:
    data = json.loads(META_PATH.read_text())
    found = False
    for county in data.get("counties") or []:
        if county.get("fips") != FIPS or county.get("name") != "Seminole":
            continue
        found = True
        if county.get("featureCount") != 4788 or county.get("source") != "doh-ehwaters":
            raise SystemExit("Refusing to retarget the Seminole parcel shelf")
        county["gaps"] = gap_lines(summary)
        county["zoningJoinedCount"] = summary["zoningJoinedCount"]
        county["fluJoinedCount"] = summary["fluJoinedCount"]
    if not found:
        raise SystemExit("Seminole block missing from orlando parcel meta")
    META_PATH.write_text(json.dumps(data, indent=2) + "\n")


def patch_sources(summary: dict) -> None:
    text = SOURCES_PATH.read_text()
    start = text.find('"fips": "12117"')
    end = text.find('"name": "Sumter"', start)
    if start < 0 or end < 0:
        raise SystemExit("Could not find the Seminole block in orlando-parcel-sources.json")
    block = text[start:end]
    old = "No zoning on the DOH extract."
    note = (
        f"City zoning and future land use are joined for Casselberry, Winter Springs, Lake Mary, Sanford, Oviedo, "
        f"and Altamonte Springs ({summary['zoningJoinedCount']} zoning, {summary['fluJoinedCount']} future land use). "
        "Longwood stays blank. County Land_Use is not stamped. Oviedo retired DSZoning is not called."
    )
    if old not in block:
        raise SystemExit("Seminole source gap sentence is missing")
    block = block.replace(old, note, 1)
    SOURCES_PATH.write_text(text[:start] + block + text[end:])


def main() -> None:
    catalog = load_catalog()
    summary = stamp(catalog)
    patch_meta(summary)
    patch_sources(summary)
    print("Seminole city overlays joined onto existing county parcels.", flush=True)


if __name__ == "__main__":
    main()
