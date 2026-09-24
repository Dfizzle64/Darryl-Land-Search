#!/usr/bin/env python3
"""Stamp Volusia and Flagler city zoning and future land use onto existing parcels.

Does not download county parcels. Flagler layers are indexed even when no
12035 parcel fixture is present. Rules match src/lib/volusiaFlaglerMunicipal.ts
and data/volusia-flagler-municipal.json.

Usage:
  python3 scripts/join_volusia_flagler_municipal.py
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
CATALOG_PATH = ROOT / "data" / "volusia-flagler-municipal.json"
SUMMARY_PATH = ROOT / "data" / "fixtures" / "volusia-flagler-municipal-join.json"
CACHE = Path("/tmp/dls-vf-municipal")
USER_AGENT = "darryl-land-search/volusia-flagler-municipal"


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
    if value is None:
        return None
    if isinstance(value, bool):
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
    if not text:
        return None
    if text.lower() in {"null", "none", "nan"}:
        return None
    return text


def is_stub(catalog: dict, text: str | None) -> bool:
    if not text:
        return False
    return text in set(catalog.get("stubZoningCodes") or [])


def read_overlay_value(catalog: dict, attrs: dict, fields: list[str], label_fields: list[str] | None) -> dict | None:
    code = None
    for field in fields:
        text = clean_text(attrs.get(field))
        if not text or is_stub(catalog, text):
            continue
        code = text
        break
    if not code:
        return None
    label = None
    for field in label_fields or []:
        text = clean_text(attrs.get(field))
        if not text or is_stub(catalog, text):
            continue
        label = text
        break
    if label == code:
        label = None
    return {"code": code, "label": label}


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/").removesuffix("/query")


def blocked_urls(catalog: dict) -> list[str]:
    return [normalize_url(item["url"]).lower() for item in (catalog.get("rejected") or []) + (catalog.get("avoid") or [])]


def assert_catalog(catalog: dict) -> None:
    if not catalog.get("doNotInventOpportunityZones"):
        raise SystemExit("Catalog must keep doNotInventOpportunityZones true")
    banned = blocked_urls(catalog)
    for place in catalog["places"]:
        for layer in (place.get("zoning"), place.get("flu")):
            if not layer:
                continue
            for key in ("url", "attributeUrl"):
                url = layer.get(key)
                if not url:
                    continue
                normalized = normalize_url(url).lower()
                if any(normalized == item or normalized.startswith(item + "/") for item in banned):
                    raise SystemExit(f"{place['id']} uses a rejected layer {url}")
    countywide_fields = catalog["countywideZoning"]["fields"]
    if countywide_fields != ["OriginalZoningCode"]:
        raise SystemExit("Countywide zoning must use OriginalZoningCode only")


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


class GridIndex:
    def __init__(self, cell: float = 0.03) -> None:
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
    print(f"  {url.split('/services/')[-1][:70]} count {expected} ids {len(ids)}", flush=True)
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


def resolve_zoning(attribute: dict | None, city_hits: list[dict], uninc: dict | None, countywide: dict | None) -> dict | None:
    if attribute:
        return attribute
    city = most_local(city_hits)
    if city:
        return city
    if uninc:
        return uninc
    return countywide


def resolve_flu(places: dict[str, dict], zoning_place_id: str | None, flu_hits: list[dict]) -> dict | None:
    if not zoning_place_id:
        return most_local(flu_hits)
    place = places.get(zoning_place_id)
    if not place or place.get("fluGap") or not place.get("flu"):
        return None
    for hit in flu_hits:
        if hit["placeId"] == place["id"]:
            return hit
    return None


def place_for_jurisd(places: list[dict], jurisd: str | None) -> dict | None:
    if not jurisd:
        return None
    for place in places:
        if place.get("countywideJurisd") == jurisd or place.get("countywideFallback") == jurisd:
            return place
    return None


def holly_keys(parcel_id: str | None) -> list[str]:
    raw = (parcel_id or "").strip()
    if not raw:
        return []
    keys = {raw}
    stripped = raw.lstrip("0")
    if stripped:
        keys.add(stripped)
    return list(keys)


def index_layer(catalog: dict, place: dict, layer: dict, theme: str) -> list[dict]:
    fields = list(layer["fields"])
    label_fields = list(layer.get("labelFields") or [])
    raw = download_features(layer["url"], list(dict.fromkeys([*fields, *label_fields])))
    indexed: list[dict] = []
    for feature in raw:
        geometry = esri_rings_to_geojson((feature.get("geometry") or {}).get("rings") or [])
        if not geometry:
            continue
        value = read_overlay_value(catalog, feature.get("attributes") or {}, fields, label_fields)
        if not value:
            continue
        bbox = feature_bbox(geometry)
        if not bbox:
            continue
        indexed.append(
            {
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
        )
    print(f"    indexed {len(indexed)} {place['id']} {theme}", flush=True)
    return indexed


def load_holly_attributes(catalog: dict, place: dict) -> dict[str, dict]:
    layer = place["zoning"]
    raw = download_features(
        layer["attributeUrl"],
        ["PID", "ALTKEY", "ZONDIST", "JUR_ZONING"],
        geometry=False,
    )
    found: dict[str, dict] = {}
    for feature in raw:
        attrs = feature.get("attributes") or {}
        value = read_overlay_value(catalog, attrs, layer["fields"], layer.get("labelFields"))
        if not value:
            value = read_overlay_value(catalog, attrs, ["ZONDIST", "JUR_ZONING"], [])
        if not value:
            continue
        hit = {
            "placeId": place["id"],
            "kind": "city",
            "status": "usable",
            "rank": place["rank"],
            "areaSqM": 0,
            "code": value["code"],
            "label": value["label"],
            "layerUrl": layer["attributeUrl"],
            "countyFips": place["countyFips"],
        }
        for field in layer.get("idFields") or []:
            text = clean_text(attrs.get(field))
            if text:
                found[text] = hit
                stripped = text.lstrip("0")
                if stripped:
                    found[stripped] = hit
    print(f"    holly hill attribute keys {len(found)}", flush=True)
    return found


def index_countywide(catalog: dict) -> list[dict]:
    spec = catalog["countywideZoning"]
    fields = ["JURISD", "OriginalZoningCode", "Z_DESCRIP", "CityName"]
    raw = download_features(spec["url"], fields)
    indexed: list[dict] = []
    for feature in raw:
        attrs = feature.get("attributes") or {}
        geometry = esri_rings_to_geojson((feature.get("geometry") or {}).get("rings") or [])
        if not geometry:
            continue
        value = read_overlay_value(catalog, attrs, spec["fields"], spec.get("labelFields"))
        jurisd = clean_text(attrs.get("JURISD"))
        if not value or not jurisd:
            continue
        bbox = feature_bbox(geometry)
        if not bbox:
            continue
        indexed.append(
            {
                "bbox": bbox,
                "geometry": geometry,
                "jurisd": jurisd,
                "code": value["code"],
                "label": value["label"],
                "areaSqM": geometry_area(geometry),
                "layerUrl": spec["url"],
            }
        )
    print(f"    indexed {len(indexed)} countywide zoning polygons", flush=True)
    return indexed


def parcel_paths() -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    tiles = ROOT / "data" / "fixtures" / "market-parcels" / "counties" / "12127" / "tiles"
    for path in sorted(tiles.glob("*.geojson")):
        rows.append(("market-12127", path))
    orlando = ROOT / "data" / "fixtures" / "orlando-parcels" / "12127.geojson"
    if orlando.exists():
        rows.append(("orlando-sample-12127", orlando))
    flagler_tiles = ROOT / "data" / "fixtures" / "market-parcels" / "counties" / "12035"
    if flagler_tiles.exists():
        for path in sorted(flagler_tiles.rglob("*.geojson")):
            rows.append(("flagler-12035", path))
    flagler_orlando = ROOT / "data" / "fixtures" / "orlando-parcels" / "12035.geojson"
    if flagler_orlando.exists():
        rows.append(("flagler-12035", flagler_orlando))
    return rows


def stamp_feature(
    feature: dict,
    places: dict[str, dict],
    place_list: list[dict],
    zoning_index: GridIndex,
    flu_index: GridIndex,
    countywide_index: GridIndex,
    holly: dict[str, dict],
) -> str | None:
    props = feature.get("properties") or {}
    preserved_oz = props.get("opportunityZone")
    preserved_oz2 = props.get("oz2Eligibility")
    centroid = props.get("centroid") or []
    if len(centroid) != 2:
        return None
    lon, lat = float(centroid[0]), float(centroid[1])
    fips = str(props.get("countyFips") or "")
    if fips not in {"12127", "12035"}:
        return None

    attribute = None
    if fips == "12127":
        for key in holly_keys(props.get("parcelId")):
            attribute = holly.get(key)
            if attribute:
                break

    city_hits = []
    uninc = None
    for item in zoning_index.hits(lon, lat):
        if item["countyFips"] != fips:
            continue
        if item["kind"] == "unincorporated":
            if uninc is None or item["areaSqM"] < uninc["areaSqM"]:
                uninc = item
            continue
        city_hits.append(item)

    countywide_hits = []
    for item in countywide_index.hits(lon, lat):
        place = place_for_jurisd(place_list, item["jurisd"])
        if not place or place["countyFips"] != fips:
            continue
        countywide_hits.append(
            {
                "placeId": place["id"],
                "kind": place["kind"],
                "status": place["status"],
                "rank": place["rank"],
                "areaSqM": item["areaSqM"],
                "code": item["code"],
                "label": item["label"],
                "layerUrl": item["layerUrl"],
                "countyFips": fips,
            }
        )
    zoning = resolve_zoning(attribute, city_hits, uninc, most_local(countywide_hits))

    flu_hits = [item for item in flu_index.hits(lon, lat) if item["countyFips"] == fips]
    flu = resolve_flu(places, zoning["placeId"] if zoning else None, flu_hits)
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
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text())
    assert_catalog(catalog)
    places = {place["id"]: place for place in catalog["places"]}
    print("Downloading municipal layers", flush=True)
    zoning_index = GridIndex()
    flu_index = GridIndex()
    holly: dict[str, dict] = {}
    for place in catalog["places"]:
        zoning = place.get("zoning")
        flu = place.get("flu")
        if zoning and zoning.get("url"):
            for item in index_layer(catalog, place, zoning, "zoning"):
                zoning_index.add(item)
        if zoning and zoning.get("attributeUrl"):
            holly = load_holly_attributes(catalog, place)
        if flu and flu.get("url"):
            for item in index_layer(catalog, place, flu, "flu"):
                flu_index.add(item)
    countywide_index = GridIndex()
    for item in index_countywide(catalog):
        countywide_index.add(item)

    stats: dict[str, dict] = {}
    by_place: dict[str, dict[str, int]] = {}
    files = parcel_paths()
    flagler_files = [row for row in files if row[0] == "flagler-12035"]
    print(f"Stamping {len(files)} parcel files", flush=True)
    for bucket, path in files:
        collection = json.loads(path.read_text())
        changed = 0
        for feature in collection.get("features") or []:
            place_id = stamp_feature(
                feature,
                places,
                catalog["places"],
                zoning_index,
                flu_index,
                countywide_index,
                holly,
            )
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
            if bucket == "market-12127":
                place_row = by_place.setdefault(place_id, {"zoning": 0, "flu": 0})
                if props.get("zoningCode"):
                    place_row["zoning"] += 1
                if isinstance(flu, dict) and flu.get("code"):
                    place_row["flu"] += 1
            if props.get("zoningCode") in set(catalog["stubZoningCodes"]):
                raise SystemExit(f"Stub zoning written on {props.get('id')}")
            municipal = props.get("municipal") or {}
            for layer in (municipal.get("zoningLayer"), municipal.get("fluLayer")):
                if layer and any(
                    normalize_url(layer).lower() == item or normalize_url(layer).lower().startswith(item + "/")
                    for item in blocked_urls(catalog)
                ):
                    raise SystemExit(f"Rejected layer written on {props.get('id')}: {layer}")
        row = stats.setdefault(bucket, {"parcels": 0, "zoning": 0, "flu": 0, "files": 0})
        row["files"] += 1
        if changed:
            path.write_text(json.dumps(collection, separators=(",", ":"), ensure_ascii=False))
        print(f"  {path.name} stamped {changed}", flush=True)

    market = stats.get("market-12127", {"parcels": 0, "zoning": 0, "flu": 0, "files": 0})
    sample = stats.get("orlando-sample-12127", {"parcels": 0, "zoning": 0, "flu": 0, "files": 0})
    gap = (
        "City zoning and future land use are joined from municipal REST where a city polygon covers the centroid. "
        f"Melbourne extract joined zoning on {market['zoning']} parcels and FLU on {market['flu']} parcels. "
        "Volusia Open Data zoning layer 36 (ZONCODE 999) is not used. "
        "DeBary, New Smyrna Beach, Orange City, Lake Helen, and Pierson use CountywideZoning OriginalZoningCode only, not a city FLUM. "
        "Daytona Beach Shores and Beverly Beach are zoning-only. "
        "Flagler city layers are hosted on gis.palmcoast.gov; this repo has no Flagler parcel baseline."
    )

    def set_volusia(county: dict) -> None:
        if county.get("fips") != "12127":
            return
        county["gaps"] = [gap]
        county["zoningJoinedCount"] = market["zoning"]
        county["fluJoinedCount"] = market["flu"]

    patch_json(ROOT / "data" / "fixtures" / "market-parcels" / "counties" / "12127" / "county.json", set_volusia)
    patch_json(ROOT / "data" / "fixtures" / "market-parcels" / "index.json", lambda data: [
        set_volusia(county) for county in data.get("markets", {}).get("Melbourne", {}).get("counties", [])
    ])
    patch_json(
        ROOT / "data" / "fixtures" / "market-parcels" / "markets" / "melbourne" / "meta.json",
        lambda data: [set_volusia(county) for county in data.get("counties", [])],
    )

    def set_sample(data: dict) -> None:
        for county in data.get("counties", []):
            if county.get("fips") != "12127":
                continue
            county["zoningJoinedCount"] = sample["zoning"]
            county["fluJoinedCount"] = sample["flu"]
            county["gaps"] = [
                "DOH extract has no zoning. City zoning and FLU are centroid-joined from municipal REST. "
                f"This sample joined zoning {sample['zoning']} and FLU {sample['flu']}. "
                "ZONCODE 999 stubs and the Seattle future land use service are not used."
            ]

    patch_json(ROOT / "data" / "fixtures" / "orlando-parcels" / "meta.json", set_sample)
    # orlando-parcel-sources.json is kept as authored JSON. A full rewrite escapes
    # punctuation in unrelated counties, so only the Volusia gap line is replaced.
    sources = ROOT / "data" / "orlando-parcel-sources.json"
    sources_text = sources.read_text()
    volusia_gap = '"gaps": ["No zoning on DOH extract"]'
    replacement = (
        '"gaps": ["DOH extract has no zoning. City zoning and FLU are centroid-joined from municipal REST. '
        f'This sample joined zoning {sample["zoning"]} and FLU {sample["flu"]}. '
        'ZONCODE 999 stubs and the Seattle future land use service are not used."],\n'
        f'      "zoningJoinedCount": {sample["zoning"]},\n'
        f'      "fluJoinedCount": {sample["flu"]}'
    )
    marker = '"name": "Volusia"'
    start = sources_text.rfind(marker)
    if start >= 0:
        region = sources_text[start:]
        if volusia_gap in region:
            region = region.replace(volusia_gap, replacement, 1)
            sources.write_text(sources_text[:start] + region)
        elif '"zoningJoinedCount"' in region.split('"path"', 1)[0]:
            pass

    summary = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "catalog": "data/volusia-flagler-municipal.json",
        "flaglerHost": catalog["flaglerHost"]["note"],
        "rejectedNotUsed": [item["url"] for item in catalog["rejected"]],
        "baselines": {
            "market-12127": market,
            "orlando-sample-12127": sample,
            "flagler-12035": {
                "present": bool(flagler_files),
                "files": len(flagler_files),
                "parcels": stats.get("flagler-12035", {}).get("parcels", 0),
                "zoning": stats.get("flagler-12035", {}).get("zoning", 0),
                "flu": stats.get("flagler-12035", {}).get("flu", 0),
                "note": (
                    "Flagler parcel fixtures were stamped."
                    if flagler_files
                    else "No Flagler parcel fixture (FIPS 12035) is in this repo. City and unincorporated AGISO layers are cataloged on gis.palmcoast.gov and were not used as a reason to download new county parcels."
                ),
            },
        },
        "byPlace": by_place,
        "opportunityZonesInvented": 0,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["baselines"], indent=2))
    print(json.dumps(summary["byPlace"], indent=2))


if __name__ == "__main__":
    main()
