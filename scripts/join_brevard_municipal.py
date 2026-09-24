#!/usr/bin/env python3
"""Stamp Brevard city zoning and future land use onto existing parcels.

Does not download a new county cadastre. Palm Bay and Titusville stay on
their prior cards and are not joined here. County zoning and county FLU are
not copied into cities. Rules match src/lib/brevardMunicipal.ts and
data/brevard-municipal.json.

Usage:
  python3 scripts/join_brevard_municipal.py
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
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parcel_geometry import esri_rings_to_geojson, polygon_parts, ring_signed_m2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "brevard-municipal.json"
SUMMARY_PATH = ROOT / "data" / "fixtures" / "brevard-municipal-join.json"
CACHE = Path("/tmp/dls-brevard-municipal")
USER_AGENT = "darryl-land-search/brevard-municipal"
FIPS = "12009"


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


def clean_text(value: object) -> str | None:
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


def read_overlay_value(attrs: dict, fields: list[str], label_fields: list[str] | None) -> dict | None:
    code = None
    for field in fields:
        text = clean_text(attrs.get(field))
        if not text:
            continue
        code = text
        break
    if not code:
        return None
    label = None
    for field in label_fields or []:
        text = clean_text(attrs.get(field))
        if not text:
            continue
        label = text
        break
    if label == code:
        label = None
    return {"code": code, "label": label}


def attribute_keys(value: object) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    upper = text.upper()
    keys = [upper, " ".join(upper.split())]
    alnum = "".join(ch for ch in upper if ch.isalnum())
    if alnum:
        keys.append(alnum)
    digits = "".join(ch for ch in upper if ch.isdigit())
    if len(digits) >= 5:
        keys.append(digits)
        stripped = digits.lstrip("0")
        if stripped:
            keys.append(stripped)
    return list(dict.fromkeys(keys))


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/").removesuffix("/query")


def blocked_urls(catalog: dict) -> list[str]:
    return [normalize_url(item["url"]).lower() for item in catalog.get("rejected") or []]


def assert_catalog(catalog: dict) -> None:
    for flag in ("doNotInventOpportunityZones", "doNotInventSchoolGrades", "doNotInventBaseFloodElevations"):
        if not catalog.get(flag):
            raise SystemExit(f"Catalog must keep {flag} true")
    banned = blocked_urls(catalog)
    skipped = {item["id"] for item in catalog.get("skippedAlreadyCarded") or []}
    gaps = {item["id"] for item in catalog.get("gaps") or []}
    if skipped != {"palm-bay", "titusville"}:
        raise SystemExit("Palm Bay and Titusville must stay skipped, not re-wired")
    for place in catalog["places"]:
        if place["id"] in skipped or place["id"] in gaps:
            raise SystemExit(f"{place['id']} is not a new join target")
        if place["countyFips"] != FIPS:
            raise SystemExit(f"{place['id']} is not Brevard")
        for layer in (place.get("zoning"), place.get("flu")):
            if not layer:
                continue
            normalized = normalize_url(layer["url"]).lower()
            if any(normalized == item or normalized.startswith(item + "/") for item in banned):
                raise SystemExit(f"{place['id']} uses a rejected layer {layer['url']}")
            if "melbourneflorida.org" in normalized or "australia" in normalized:
                raise SystemExit(f"{place['id']} points at the wrong Melbourne")
    cocoa = next(place for place in catalog["places"] if place["id"] == "cocoa")
    if not cocoa["flu"]["url"].rstrip("/").endswith("FeatureServer/6"):
        raise SystemExit("Cocoa FLU must be FLU_Public_View layer 6")
    ihb = next(place for place in catalog["places"] if place["id"] == "indian-harbour-beach")
    if ihb.get("flu") or not ihb.get("fluGap"):
        raise SystemExit("Indian Harbour Beach FLU must stay blank")
    beach = next(place for place in catalog["places"] if place["id"] == "cocoa-beach")
    if not beach.get("unofficial") or beach.get("vintage") != "2021":
        raise SystemExit("Cocoa Beach must stay flagged unofficial 2021")
    melbourne = next(place for place in catalog["places"] if place["id"] == "melbourne")
    if melbourne["flu"].get("where") != "Status='Active / Current'":
        raise SystemExit("Melbourne FLU must filter Status Active / Current")


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


def feature_bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: object) -> None:
        if isinstance(node, (int, float)):
            return
        if isinstance(node, list) and node and isinstance(node[0], (int, float)):
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


def geometry_area(geometry: dict) -> float:
    total = 0.0
    for poly in polygon_parts(geometry):
        if poly:
            total += abs(ring_signed_m2(poly[0]))
    return total if total > 1 else 1.0


def in_brevard(catalog: dict, lon: float, lat: float) -> bool:
    west, south, east, north = catalog["brevardBbox"]
    return west <= lon <= east and south <= lat <= north


class GridIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = {}
        self.broad: list[dict] = []

    def add(self, item: dict) -> None:
        bbox = item["bbox"]
        west, south, east, north = bbox
        ix0 = math.floor(west / self.cell)
        ix1 = math.floor(east / self.cell)
        iy0 = math.floor(south / self.cell)
        iy1 = math.floor(north / self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 400:
            self.broad.append(item)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets.setdefault((ix, iy), []).append(item)

    def hits(self, x: float, y: float) -> list[dict]:
        ix = math.floor(x / self.cell)
        iy = math.floor(y / self.cell)
        found: list[dict] = []
        seen: set[int] = set()
        for item in self.buckets.get((ix, iy), []) + self.broad:
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            if point_in_geometry(x, y, item["geometry"]):
                found.append(item)
        return found


def cache_path(url: str, fields: list[str], where: str, geometry: bool) -> Path:
    key = hashlib.sha1(f"{url}|{','.join(fields)}|{where}|{geometry}".encode()).hexdigest()[:20]
    return CACHE / f"{key}.json"


def download_features(url: str, fields: list[str], where: str = "1=1", geometry: bool = True) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = cache_path(url, fields, where, geometry)
    if cached.exists():
        return json.loads(cached.read_text())
    query = url.rstrip("/") + "/query"
    counted = fetch_json(query, {"where": where, "returnCountOnly": "true", "f": "json"})
    expected = int(counted.get("count") or 0)
    id_payload = fetch_json(query, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    ids = [int(i) for i in (id_payload.get("objectIds") or [])]
    print(f"  {url.split('/services/')[-1][:80]} count {expected} ids {len(ids)}", flush=True)
    if expected and not ids:
        raise RuntimeError(f"No object ids for {url}")

    def pull(chunk: list[int], simplify: bool) -> list[dict]:
        params = {
            "objectIds": ",".join(str(i) for i in chunk),
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "outSR": "4326",
            "f": "json",
        }
        if geometry and simplify:
            params["maxAllowableOffset"] = "0.00008"
            params["geometryPrecision"] = "5"
        return fetch_json(query, params, timeout=180).get("features") or []

    features: list[dict] = []
    chunks = [ids[start : start + 80] for start in range(0, len(ids), 80)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(pull, chunk, True): chunk for chunk in chunks}
        done = 0
        for fut in as_completed(futures):
            chunk = futures[fut]
            try:
                features.extend(fut.result())
            except Exception:
                features.extend(pull(chunk, False))
            done += 1
            if done % 25 == 0:
                print(f"    {done}/{len(chunks)} batches", flush=True)
    if expected and len(features) < expected * 0.9:
        raise RuntimeError(f"{url} returned {len(features)} of {expected}")
    cached.write_text(json.dumps(features, separators=(",", ":")))
    return features


def most_local(hits: list[dict]) -> dict | None:
    if not hits:
        return None
    return sorted(hits, key=lambda item: (item["areaSqM"], item["rank"]))[0]


def resolve_zoning(attribute: dict | None, city_hits: list[dict]) -> dict | None:
    if attribute:
        return attribute
    return most_local(city_hits)


def resolve_flu(places: dict[str, dict], zoning_place_id: str | None, flu_hits: list[dict], attribute: dict | None) -> dict | None:
    if zoning_place_id:
        place = places.get(zoning_place_id)
        if not place or place.get("fluGap") or not place.get("flu"):
            return None
        if attribute and attribute["placeId"] == place["id"]:
            return attribute
        return most_local([hit for hit in flu_hits if hit["placeId"] == place["id"]])
    usable = []
    for hit in flu_hits:
        place = places.get(hit["placeId"])
        if place and not place.get("fluGap") and place.get("flu"):
            usable.append(hit)
    if attribute:
        place = places.get(attribute["placeId"])
        if place and not place.get("fluGap") and place.get("flu"):
            return attribute
    return most_local(usable)


def assert_brevard_layer(catalog: dict, place_id: str, theme: str, indexed: list[dict]) -> None:
    if not indexed:
        raise SystemExit(f"{place_id} {theme} returned no polygons inside the download")
    sample = indexed[:40]
    inside = 0
    for item in sample:
        west, south, east, north = item["bbox"]
        if in_brevard(catalog, (west + east) / 2, (south + north) / 2):
            inside += 1
    if inside == 0:
        raise SystemExit(f"{place_id} {theme} is outside Brevard County, Florida. Refusing a Melbourne namesake.")


def index_layer(catalog: dict, place: dict, layer: dict, theme: str) -> tuple[list[dict], dict[str, dict]]:
    fields = list(layer["fields"])
    label_fields = list(layer.get("labelFields") or [])
    id_fields = list(layer.get("idFields") or [])
    where = layer.get("where") or "1=1"
    raw = download_features(layer["url"], list(dict.fromkeys([*fields, *label_fields, *id_fields])), where)
    indexed: list[dict] = []
    attributes: dict[str, dict] = {}
    for feature in raw:
        geometry = esri_rings_to_geojson((feature.get("geometry") or {}).get("rings") or [])
        if not geometry:
            continue
        attrs = feature.get("attributes") or {}
        value = read_overlay_value(attrs, fields, label_fields)
        if not value:
            continue
        bbox = feature_bbox(geometry)
        if not bbox:
            continue
        hit = {
            "bbox": bbox,
            "geometry": geometry,
            "placeId": place["id"],
            "kind": place["kind"],
            "status": place["status"],
            "rank": place["rank"],
            "areaSqM": geometry_area(geometry),
            "code": value["code"],
            "label": value["label"],
            "layerUrl": layer["url"],
            "theme": theme,
            "countyFips": place["countyFips"],
        }
        indexed.append(hit)
        for field in id_fields:
            for key in attribute_keys(attrs.get(field)):
                previous = attributes.get(key)
                if previous is None:
                    attributes[key] = hit
                elif previous.get("placeId") != hit["placeId"]:
                    attributes[key] = {"ambiguous": True}
    attributes = {key: value for key, value in attributes.items() if not value.get("ambiguous")}
    assert_brevard_layer(catalog, place["id"], theme, indexed)
    print(f"    indexed {len(indexed)} {place['id']} {theme} attr {len(attributes)}", flush=True)
    return indexed, attributes


def merge_attributes(dest: dict[str, dict], incoming: dict[str, dict]) -> None:
    for key, hit in incoming.items():
        previous = dest.get(key)
        if previous and previous.get("placeId") != hit.get("placeId"):
            dest[key] = {"ambiguous": True}
        elif previous and previous.get("ambiguous"):
            continue
        else:
            dest[key] = hit


def lookup_attribute(index: dict[str, dict], parcel_id: object) -> dict | None:
    found: list[dict] = []
    seen: set[str] = set()
    for key in attribute_keys(parcel_id):
        hit = index.get(key)
        if not hit or hit.get("ambiguous"):
            continue
        if hit["placeId"] in seen:
            continue
        seen.add(hit["placeId"])
        found.append(hit)
    if len(found) != 1:
        return None
    return found[0]


def parcel_paths() -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    tiles = ROOT / "data" / "fixtures" / "market-parcels" / "counties" / FIPS / "tiles"
    for path in sorted(tiles.glob("*.geojson")):
        rows.append(("market-12009", path))
    orlando = ROOT / "data" / "fixtures" / "orlando-parcels" / "12009.geojson"
    if orlando.exists():
        rows.append(("orlando-sample-12009", orlando))
    return rows


def stamp_feature(
    feature: dict,
    places: dict[str, dict],
    zoning_index: GridIndex,
    flu_index: GridIndex,
    zoning_attr: dict[str, dict],
    flu_attr: dict[str, dict],
) -> str | None:
    props = feature.get("properties") or {}
    preserved_oz = props.get("opportunityZone")
    preserved_oz2 = props.get("oz2Eligibility")
    centroid = props.get("centroid") or []
    if len(centroid) != 2:
        return None
    if str(props.get("countyFips") or "") != FIPS:
        return None
    lon, lat = float(centroid[0]), float(centroid[1])
    zoning_attribute = lookup_attribute(zoning_attr, props.get("parcelId"))
    flu_attribute = lookup_attribute(flu_attr, props.get("parcelId"))
    city_hits = zoning_index.hits(lon, lat)
    zoning = resolve_zoning(zoning_attribute, city_hits)
    flu_hits = flu_index.hits(lon, lat)
    flu = resolve_flu(places, zoning["placeId"] if zoning else None, flu_hits, flu_attribute)
    if not zoning and not flu:
        return None
    place = places[(zoning or flu)["placeId"]]
    if zoning:
        props["zoningCode"] = zoning["code"]
        props["zoningDistrict"] = zoning["code"]
        props["jurisdictionPrefix"] = place["prefix"]
        props["jurisdictionCode"] = place["prefix"]
    if place.get("fluGap"):
        props["flu"] = None
        flu = None
    elif flu:
        props["flu"] = {
            "code": flu["code"],
            "label": flu["label"] or flu["code"],
            "jurisdiction": places[flu["placeId"]]["name"],
            "source": flu["layerUrl"],
        }
    zoning_place = places[zoning["placeId"]] if zoning else None
    flu_place = places[flu["placeId"]] if flu else None
    note_place = zoning_place or flu_place
    props["municipal"] = {
        "placeId": note_place["id"],
        "placeName": note_place["name"],
        "zoningLayer": zoning["layerUrl"] if zoning else None,
        "fluLayer": flu["layerUrl"] if flu else None,
        "zoningLabel": zoning.get("label") if zoning else None,
        "fluGap": note_place.get("fluGap") if zoning_place and zoning_place.get("fluGap") else None,
        "unofficial": bool(note_place.get("unofficial")),
        "vintage": note_place.get("vintage"),
        "join": "attribute" if (zoning_attribute and zoning and zoning_attribute["placeId"] == zoning["placeId"]) or (flu_attribute and flu and flu_attribute["placeId"] == flu["placeId"]) else "spatial",
    }
    props["opportunityZone"] = preserved_oz
    props["oz2Eligibility"] = preserved_oz2
    feature["properties"] = props
    return note_place["id"]


def patch_json(path: Path, mutate) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text())
    mutate(data)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def apply_gap(county: dict, gap: str, zoning: int, flu: int) -> None:
    if str(county.get("fips") or "") != FIPS:
        return
    kept = []
    for item in county.get("gaps") or []:
        text = str(item)
        if "No zoning" in text or "seed:brevard-municipal" in text or "City zoning and future land use are joined" in text:
            continue
        kept.append(item)
    county["gaps"] = [*kept, gap]
    county["zoningJoinedCount"] = zoning
    county["fluJoinedCount"] = flu


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text())
    assert_catalog(catalog)
    places = {place["id"]: place for place in catalog["places"]}
    print("Downloading Brevard municipal layers", flush=True)
    zoning_index = GridIndex()
    flu_index = GridIndex()
    zoning_attr: dict[str, dict] = {}
    flu_attr: dict[str, dict] = {}
    for place in catalog["places"]:
        zoning = place.get("zoning")
        flu = place.get("flu")
        if zoning and zoning.get("url"):
            indexed, attributes = index_layer(catalog, place, zoning, "zoning")
            for item in indexed:
                zoning_index.add(item)
            merge_attributes(zoning_attr, attributes)
        if flu and flu.get("url"):
            indexed, attributes = index_layer(catalog, place, flu, "flu")
            for item in indexed:
                flu_index.add(item)
            merge_attributes(flu_attr, attributes)

    stats: dict[str, dict] = {}
    by_place: dict[str, dict[str, int]] = {}
    files = parcel_paths()
    print(f"Stamping {len(files)} parcel files", flush=True)
    blocked = blocked_urls(catalog)
    for bucket, path in files:
        collection = json.loads(path.read_text())
        changed = 0
        for feature in collection.get("features") or []:
            place_id = stamp_feature(feature, places, zoning_index, flu_index, zoning_attr, flu_attr)
            if not place_id:
                continue
            changed += 1
            props = feature["properties"]
            row = stats.setdefault(bucket, {"parcels": 0, "zoning": 0, "flu": 0, "files": 0})
            row["parcels"] += 1
            if props.get("zoningCode"):
                row["zoning"] += 1
            flu = props.get("flu") or {}
            if isinstance(flu, dict) and flu.get("code"):
                row["flu"] += 1
            if bucket == "market-12009":
                place_row = by_place.setdefault(place_id, {"zoning": 0, "flu": 0, "unofficial": 0})
                if props.get("zoningCode"):
                    place_row["zoning"] += 1
                if isinstance(flu, dict) and flu.get("code"):
                    place_row["flu"] += 1
                if (props.get("municipal") or {}).get("unofficial"):
                    place_row["unofficial"] += 1
            municipal = props.get("municipal") or {}
            for layer in (municipal.get("zoningLayer"), municipal.get("fluLayer")):
                if not layer:
                    continue
                normalized = normalize_url(layer).lower()
                if any(normalized == item or normalized.startswith(item + "/") for item in blocked):
                    raise SystemExit(f"Rejected layer written on {props.get('id')}: {layer}")
            if place_id == "indian-harbour-beach" and props.get("flu"):
                raise SystemExit(f"Indian Harbour Beach FLU was written on {props.get('id')}")
            if place_id == "cocoa-beach" and not municipal.get("unofficial"):
                raise SystemExit(f"Cocoa Beach missing unofficial flag on {props.get('id')}")
            oz = props.get("opportunityZone") or {}
            if isinstance(oz, dict) and oz.get("source") and "brevard-municipal" in str(oz.get("source")):
                raise SystemExit("Opportunity Zone invented by the municipal join")
        row = stats.setdefault(bucket, {"parcels": 0, "zoning": 0, "flu": 0, "files": 0})
        row["files"] += 1
        if changed:
            path.write_text(json.dumps(collection, separators=(",", ":"), ensure_ascii=False))
        print(f"  {path.name} stamped {changed}", flush=True)

    market = stats.get("market-12009", {"parcels": 0, "zoning": 0, "flu": 0, "files": 0})
    sample = stats.get("orlando-sample-12009", {"parcels": 0, "zoning": 0, "flu": 0, "files": 0})
    gap = (
        "City zoning and future land use are centroid-joined from municipal REST, with TaxAcct, PID, or RENUM when the parcel id matches. "
        f"Melbourne market extract joined zoning on {market['zoning']} parcels and FLU on {market['flu']} parcels. "
        "Melbourne, West Melbourne, Rockledge, Satellite Beach, and Cocoa (prior zoning plus FLU_Public_View layer 6) are usable. "
        "Indian Harbour Beach is zoning only. Cocoa Beach is the unofficial 2021 parcel layer. "
        "Palm Bay and Titusville are prior cards and are not applied in this pass. "
        "Cape Canaveral, Indialantic, Melbourne Beach, Grant-Valkaria, Palm Shores, Melbourne Village, and Malabar have no public city REST. "
        "County Zoning_WKID2881, county FLU, and Accela zoning are not copied into these cities. "
        "Melbourne, Australia is rejected."
    )

    patch_json(ROOT / "data" / "fixtures" / "market-parcels" / "counties" / FIPS / "county.json", lambda county: apply_gap(county, gap, market["zoning"], market["flu"]))

    def patch_markets(data: dict) -> None:
        for market_row in (data.get("markets") or {}).values():
            for county in market_row.get("counties") or []:
                apply_gap(county, gap, market["zoning"], market["flu"])

    patch_json(ROOT / "data" / "fixtures" / "market-parcels" / "index.json", patch_markets)
    for meta_name in ("melbourne", "vero-beach"):
        patch_json(
            ROOT / "data" / "fixtures" / "market-parcels" / "markets" / meta_name / "meta.json",
            lambda data: [apply_gap(county, gap, market["zoning"], market["flu"]) for county in data.get("counties") or []],
        )

    def set_sample(data: dict) -> None:
        for county in data.get("counties") or []:
            if str(county.get("fips") or "") != FIPS:
                continue
            county["zoningJoinedCount"] = sample["zoning"]
            county["fluJoinedCount"] = sample["flu"]
            kept = [item for item in county.get("gaps") or [] if "No zoning" not in str(item)]
            county["gaps"] = [
                *kept,
                "DOH sample. City zoning and FLU are centroid-joined from municipal REST. "
                f"This sample joined zoning {sample['zoning']} and FLU {sample['flu']}. "
                "Titusville and Palm Bay are not applied here. County zoning is not a city substitute.",
            ]

    patch_json(ROOT / "data" / "fixtures" / "orlando-parcels" / "meta.json", set_sample)
    patch_json(ROOT / "data" / "orlando-parcel-sources.json", lambda data: set_sample(data))

    summary = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "catalog": "data/brevard-municipal.json",
        "wired": [place["id"] for place in catalog["places"] if place["status"] == "usable"],
        "partials": [
            {
                "id": place["id"],
                "unofficial": bool(place.get("unofficial")),
                "vintage": place.get("vintage"),
                "fluGap": place.get("fluGap"),
            }
            for place in catalog["places"]
            if place["status"] == "partial"
        ],
        "skippedAlreadyCarded": [item["id"] for item in catalog["skippedAlreadyCarded"]],
        "gaps": [item["id"] for item in catalog["gaps"]],
        "rejectedNotUsed": [item["url"] for item in catalog["rejected"]],
        "baselines": {"market-12009": market, "orlando-sample-12009": sample},
        "byPlace": by_place,
        "opportunityZonesInvented": 0,
        "schoolGradesInvented": 0,
        "baseFloodElevationsInvented": 0,
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["baselines"], indent=2))
    print(json.dumps(summary["byPlace"], indent=2))


if __name__ == "__main__":
    main()
