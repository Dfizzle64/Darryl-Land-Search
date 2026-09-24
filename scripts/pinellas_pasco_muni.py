#!/usr/bin/env python3
"""Stamp Pinellas and Pasco city zoning and future land use onto existing parcels.

Does not download county parcel polygons. Does not invent Opportunity Zones.
St. Petersburg, Clearwater, and Largo are left as they already are on this shelf.
Largo does not get a zoning code from mowing or community-standards layers.

  python3 scripts/pinellas_pasco_muni.py
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
CATALOG_PATH = ROOT / "data" / "pinellas-pasco-municipal.json"
SUMMARY_PATH = ROOT / "data" / "fixtures" / "pinellas-pasco-municipal-join.json"
COUNTY_DIR = ROOT / "data" / "fixtures" / "market-parcels" / "counties"
INDEX_PATH = ROOT / "data" / "fixtures" / "market-parcels" / "index.json"
TAMPA_META = ROOT / "data" / "fixtures" / "market-parcels" / "markets" / "tampa" / "meta.json"
CACHE = Path("/tmp/dls-pinellas-pasco")
USER_AGENT = "darryl-land-search/pinellas-pasco-muni"
PCGIS = "https://services.arcgis.com/f5HgUpxURgEzTccH/arcgis/rest/services"
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
    fragments = catalog["blockedUrlFragments"]
    for place in places_for(catalog, None):
        for layer in (place.get("zoning"), place.get("flu")):
            if not layer:
                continue
            if url_blocked(layer["url"], fragments):
                raise SystemExit(f"{place['municipality']} uses a blocked layer {layer['url']}")
    return catalog


def pcgis(service: str) -> str:
    return f"{PCGIS}/{service}/FeatureServer/0"


def places_for(catalog: dict, fips: str | None) -> list[dict]:
    wired = []
    for place in catalog["wired"]:
        item = dict(place)
        item["kind"] = "wired"
        wired.append(item)
    partials = []
    for partial in catalog["partials"]:
        slug = partial["municipality"].lower().replace(" ", "-")
        partials.append(
            {
                "municipality": partial["municipality"],
                "fips": "12103",
                "situs": partial["situs"],
                "fluStatus": "gap",
                "kind": "partial",
                "zoning": {
                    "role": f"{slug}-zoning",
                    "url": pcgis(partial["service"]),
                    "fields": ["ZONING"],
                    "code": "ZONING",
                    "desc": None,
                    "where": "ZONING IS NOT NULL",
                },
                "flu": None,
            }
        )
    rows = wired + partials
    if fips is None:
        return rows
    return [row for row in rows if row["fips"] == fips]


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
    def __init__(self, cell: float = 0.02) -> None:
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
        done = 0
        for fut in as_completed(futures):
            features.extend(fut.result())
            done += 1
            if done % 20 == 0:
                print(f"    {done}/{len(chunks)} batches", flush=True)
    if expected and len(features) < expected * 0.9:
        raise RuntimeError(f"{url} returned {len(features)} of {expected}")
    cached.write_text(json.dumps(features, separators=(",", ":")))
    return features


def verify_layer(catalog: dict, url: str, fips: str) -> None:
    if url_blocked(url, catalog["blockedUrlFragments"]):
        raise RuntimeError(f"{url} is a blocked namesake and was not queried")
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
    box_west, box_south, box_east, box_north = catalog["counties"][fips]["box"]
    span = max(east - west, north - south)
    outside = west < box_west or south < box_south or east > box_east or north > box_north
    if outside or span > catalog["maxCitySpanDegrees"] or span <= 0:
        raise RuntimeError(
            f"{url} extent ({west:.3f},{south:.3f},{east:.3f},{north:.3f}) is outside the parent county"
        )
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
    hit = {"code": code, "desc": desc, "source": layer["role"]}
    flum_field = layer.get("flum")
    if flum_field:
        flum = clean(attrs.get(flum_field))
        if flum and flum.upper() not in stubs:
            hit["flum"] = flum
    return hit


def index_layer(catalog: dict, place: dict, layer: dict) -> tuple[dict[str, dict], SpatialIndex]:
    verify_layer(catalog, layer["url"], place["fips"])
    fields = list(dict.fromkeys([*layer["fields"], *([place["idField"]] if place.get("idField") else [])]))
    raw = download_features(layer["url"], fields, layer["where"])
    stubs = {item.upper() for item in catalog["stubCodes"]}
    by_id: dict[str, dict] = {}
    spatial = SpatialIndex()
    box = catalog["counties"][place["fips"]]["box"]
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
        if max(abs(west), abs(east)) > 180 or max(abs(south), abs(north)) > 90:
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
        raise RuntimeError(f"{layer['role']} indexed no polygons inside the county")
    return by_id, spatial


def candidate_points(feature: dict) -> list[tuple[float, float]]:
    """Centroid plus a few points inside the parcel. Large waterfront parcels miss on the centroid alone."""
    centroid = feature["properties"].get("centroid") or [None, None]
    points: list[tuple[float, float]] = []
    if centroid[0] is not None:
        points.append((float(centroid[0]), float(centroid[1])))
    geometry = feature.get("geometry") or {}
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    outer = []
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
    hit = None
    for x, y in candidate_points(feature):
        hit = spatial.hit(x, y)
        if hit:
            break
    if not hit:
        return None
    return {"code": hit["code"], "desc": hit.get("desc"), "source": hit["source"], **({"flum": hit["flum"]} if hit.get("flum") else {})}


def flu_payload(hit: dict, municipality: str) -> dict:
    return {
        "code": hit["code"],
        "label": hit.get("desc") or hit["code"],
        "jurisdiction": municipality,
        "source": hit["source"],
    }


def load_tiles(fips: str) -> list[tuple[Path, dict]]:
    folder = COUNTY_DIR / fips / "tiles"
    return [(path, json.loads(path.read_text())) for path in sorted(folder.glob("*.geojson"))]


def freeze(feature: dict) -> str:
    props = feature["properties"]
    payload_row = {key: props.get(key) for key in FROZEN}
    payload_row["geometry"] = feature.get("geometry")
    return json.dumps(payload_row, sort_keys=True, separators=(",", ":"))


def gap_lines(catalog: dict, fips: str, stats: dict[str, dict], zoning: int, flu: int) -> list[str]:
    county = catalog["counties"][fips]
    if fips == "12103":
        return [
            f"Florida DOH 5–150 acre parcels ({county['source']}, {zoning} city zoning codes and {flu} city future land use codes on this shelf). County parcels were not re-downloaded.",
            "Dunedin, Pinellas Park, Tarpon Springs, Safety Harbor, and Oldsmar have city zoning and future land use. Join is the city parcel id when it matches the DOH strap, otherwise a point inside the parcel.",
            "Seminole, South Pasadena, Treasure Island, Kenneth City, North Redington Beach, Indian Shores, Belleair, Indian Rocks Beach, and Madeira Beach use the Pinellas County GIS city zoning view where the parcel intersects it. City future land use stays blank. The countywide plan map is not stored. North Redington Beach has no situs parcels on this 5–150 acre shelf. Redington Shores is on that same view, and its two situs parcels on this shelf do not intersect the zoning polygons.",
            "Largo zoning is a gap. Largo future land use is not on this shelf and was not invented from mowing or community-standards layers.",
            "Gulfport, Belleair Beach, Belleair Bluffs, Redington Beach, and St. Pete Beach have no verified city zoning or future land use layer.",
            "St. Petersburg and Clearwater zoning were not copied from the Tampa parcel re-extract. They stay blank on this shelf.",
            "Rejected namesakes: Hernando Zoning_Flu (Weeki Wachee), Anderson County California Zoning_view, and Gulfport, Mississippi GPT_Zoning.",
        ]
    return [
        f"Florida DOH 5–150 acre parcels ({county['source']}, {zoning} city zoning codes and {flu} city future land use codes on this shelf). County parcels were not re-downloaded.",
        "New Port Richey zoning and future land use are the city WFL1 layers. Zephyrhills uses the citywide Euclidean layers. The traditional city center layer is not stacked.",
        "Port Richey, Dade City, San Antonio, and St. Leo stay blank.",
        "County ZN_TYPE placeholders NPR, PR, SA, DC, and ZH are not stored as districts.",
        "Rejected namesakes: Hernando Zoning_Flu (Weeki Wachee), Anderson County California Zoning_view, and Gulfport, Mississippi GPT_Zoning.",
    ]


def apply_county(catalog: dict, fips: str) -> dict:
    county_path = COUNTY_DIR / fips / "county.json"
    row = json.loads(county_path.read_text())
    if row.get("source") != catalog["counties"][fips]["source"]:
        raise SystemExit(f"{fips} source changed; refusing to stamp a different parcel shelf")
    tiles = load_tiles(fips)
    features: list[dict] = []
    for _path, collection in tiles:
        features.extend(collection.get("features") or [])
    if len(features) != row["featureCount"]:
        raise SystemExit(f"{fips} tile count {len(features)} != county.json {row['featureCount']}")
    before = [freeze(feature) for feature in features]
    oz_before = sum(1 for feature in features if feature["properties"].get("opportunityZone"))

    by_situs: dict[str, list[dict]] = {}
    for feature in features:
        situs = (feature["properties"].get("situsCity") or "").strip().upper()
        if situs:
            by_situs.setdefault(situs, []).append(feature)

    overlays: list[dict] = []
    stats: dict[str, dict] = {}
    stubs = {item.upper() for item in catalog["stubCodes"]}
    for place in places_for(catalog, fips):
        group: list[dict] = []
        for situs in place["situs"]:
            group.extend(by_situs.get(situs, []))
        print(f"Join {place['municipality']} parcels {len(group)}", flush=True)
        zoning_ids, zoning_spatial = index_layer(catalog, place, place["zoning"])
        flu_ids = flu_spatial = None
        if place.get("flu"):
            flu_ids, flu_spatial = index_layer(catalog, place, place["flu"])
        overlays.append({"role": place["zoning"]["role"], "url": place["zoning"]["url"]})
        if place.get("flu"):
            overlays.append({"role": place["flu"]["role"], "url": place["flu"]["url"]})
        zoning_joined = 0
        flu_joined = 0
        for feature in group:
            props = feature["properties"]
            code = (props.get("zoningCode") or "").upper()
            if code in stubs:
                props["zoningCode"] = None
                props["zoningDistrict"] = None
            zone = lookup(zoning_ids, zoning_spatial, feature)
            flu_hit = lookup(flu_ids, flu_spatial, feature) if flu_ids is not None and flu_spatial is not None else None
            gaps = [gap for gap in (props.get("dataGaps") or []) if "Pinellas" not in gap and "Pasco" not in gap and "city" not in gap.lower()]
            if zone and zone.get("code"):
                props["zoningCode"] = zone["code"]
                props["zoningDistrict"] = zone["code"]
                zoning_joined += 1
                props["municipal"] = {
                    "placeId": place["municipality"].lower().replace(" ", "-"),
                    "placeName": place["municipality"],
                    "zoningLayer": place["zoning"]["url"],
                    "fluLayer": (place.get("flu") or {}).get("url"),
                    "zoningLabel": zone.get("desc"),
                    "fluGap": catalog["partialFluGap"] if place["fluStatus"] == "gap" else None,
                }
            else:
                gaps.append("City zoning polygon did not intersect this parcel.")
            if flu_hit and flu_hit.get("code"):
                props["flu"] = flu_payload(flu_hit, place["municipality"])
                flu_joined += 1
                if props.get("municipal"):
                    props["municipal"]["fluLayer"] = place["flu"]["url"]
            elif place["fluStatus"] == "city" and zone and zone.get("flum"):
                props["flu"] = {
                    "code": zone["flum"],
                    "label": zone["flum"],
                    "jurisdiction": place["municipality"],
                    "source": "oldsmar-parcel-flum",
                }
                flu_joined += 1
            elif place["fluStatus"] == "city":
                gaps.append("City future land use polygon did not intersect this parcel.")
            else:
                gaps.append(catalog["partialFluGap"])
            if gaps:
                props["dataGaps"] = gaps
            elif "dataGaps" in props and not props["dataGaps"]:
                props.pop("dataGaps", None)
        stats[place["municipality"]] = {
            "parcels": len(group),
            "zoningJoined": zoning_joined,
            "fluJoined": flu_joined,
            "fluStatus": place["fluStatus"],
        }
        print(f"  {place['municipality']} zoning {zoning_joined} flu {flu_joined}", flush=True)

    after = [freeze(feature) for feature in features]
    if after != before:
        raise SystemExit(f"{fips} parcel id, acreage, geometry, or Opportunity Zone fields changed")
    oz_after = sum(1 for feature in features if feature["properties"].get("opportunityZone"))
    if oz_after != oz_before:
        raise SystemExit(f"{fips} Opportunity Zone count changed {oz_before} -> {oz_after}")

    require_joins(stats)
    zoning_total = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_total = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    owned = {item["role"] for item in overlays}
    kept = [item for item in row.get("overlays") or [] if item.get("role") not in owned]
    rejected = list(catalog["rejected"])
    row["gaps"] = gap_lines(catalog, fips, stats, zoning_total, flu_total)
    row["overlays"] = kept + overlays
    row["rejected"] = rejected
    row["zoningJoinedCount"] = zoning_total
    row["fluJoinedCount"] = flu_total
    row["municipalOverlayJoins"] = stats
    row["featureCount"] = len(features)
    row["source"] = catalog["counties"][fips]["source"]

    written = 0
    for path, collection in tiles:
        encoded = json.dumps(collection, separators=(",", ":"))
        if encoded == path.read_text():
            continue
        path.write_text(encoded)
        written += 1
    county_path.write_text(json.dumps(row, indent=2) + "\n")
    print(f"{row['name']} tiles rewritten {written} zoning {zoning_total} flu {flu_total}", flush=True)
    return {
        "fips": fips,
        "name": row["name"],
        "source": row["source"],
        "featureCount": len(features),
        "zoningJoinedCount": zoning_total,
        "fluJoinedCount": flu_total,
        "opportunityZonesInvented": 0,
        "opportunityZoneCount": oz_after,
        "tilesRewritten": written,
        "byPlace": stats,
        "overlays": overlays,
    }


def require_joins(stats: dict[str, dict]) -> None:
    for name in ("Dunedin", "Pinellas Park", "Tarpon Springs", "Safety Harbor", "Oldsmar", "New Port Richey", "Zephyrhills"):
        row = stats.get(name)
        if not row:
            continue
        if row["parcels"] < 1 or row["zoningJoined"] < 1 or row["fluJoined"] < 1:
            raise SystemExit(f"{name} did not join zoning and future land use: {row}")
    for name, row in stats.items():
        if row["fluStatus"] != "gap":
            continue
        if row["fluJoined"] != 0:
            raise SystemExit(f"{name} partial stored a future land use code")
        if row["parcels"] >= 20 and row["zoningJoined"] < 1:
            raise SystemExit(f"{name} zoning view did not join: {row}")


def patch_gap_lists(catalog: dict, summaries: list[dict]) -> None:
    by_fips = {item["fips"]: item for item in summaries}

    def walk(node: object) -> None:
        if isinstance(node, dict):
            fips = node.get("fips")
            if fips in by_fips and node.get("name") in {"Pinellas", "Pasco"}:
                summary = by_fips[fips]
                node["gaps"] = gap_lines(
                    catalog, fips, summary["byPlace"], summary["zoningJoinedCount"], summary["fluJoinedCount"]
                )
                node["zoningJoinedCount"] = summary["zoningJoinedCount"]
                node["fluJoinedCount"] = summary["fluJoinedCount"]
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for path in (INDEX_PATH, TAMPA_META):
        data = json.loads(path.read_text())
        walk(data)
        path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    catalog = load_catalog()
    summaries = [apply_county(catalog, fips) for fips in ("12103", "12101")]
    patch_gap_lists(catalog, summaries)
    summary = {
        "opportunityZonesInvented": 0,
        "countyParcelsRedownloaded": False,
        "counties": summaries,
        "rejected": catalog["rejected"],
        "gaps": [gap["municipality"] for gap in catalog["gaps"]],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    print("Pinellas and Pasco city overlays joined onto existing county parcels.", flush=True)


if __name__ == "__main__":
    main()
