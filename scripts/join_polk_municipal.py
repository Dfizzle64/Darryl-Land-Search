#!/usr/bin/env python3
"""Stamp Polk County city zoning and future land use onto existing parcels.

Does not download a new county parcel shelf. Does not invent county LDC
zoning, copy county FLUNAME into zoningCode, or write Opportunity Zones.
Rules match src/lib/polkMunicipal.ts and data/polk-municipal.json.

Usage:
  python3 scripts/join_polk_municipal.py
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
CATALOG_PATH = ROOT / "data" / "polk-municipal.json"
SUMMARY_PATH = ROOT / "data" / "fixtures" / "polk-municipal-join.json"
TILES = ROOT / "data" / "fixtures" / "orlando-parcels" / "tiles" / "12105"
CACHE = Path("/tmp/dls-polk-municipal")
USER_AGENT = "darryl-land-search/polk-municipal"
FIPS = "12105"


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


def is_stub(catalog: dict, text: str | None) -> bool:
    if not text:
        return False
    stubs = {item.lower() for item in catalog.get("stubCodes") or []}
    return text.lower() in stubs


def is_polk_parcel_key(value: str | None) -> bool:
    text = (value or "").strip()
    return text.isdigit() and len(text) >= 15


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


def blocked_tokens(catalog: dict) -> list[str]:
    tokens: list[str] = []
    for item in catalog.get("rejected") or []:
        tokens.append(normalize_url(item["url"]).lower())
    county_flu = normalize_url((catalog.get("countyFluNotStamped") or {}).get("url") or "").lower()
    if county_flu:
        tokens.append(county_flu)
    return tokens


def url_is_blocked(url: str, tokens: list[str]) -> bool:
    normalized = normalize_url(url).lower()
    for token in tokens:
        if token.startswith("http"):
            if normalized == token or normalized.startswith(token + "/"):
                return True
        elif token and token in normalized:
            return True
    return False


def assert_catalog(catalog: dict) -> None:
    if not catalog.get("doNotInventOpportunityZones"):
        raise SystemExit("Catalog must keep doNotInventOpportunityZones true")
    if not catalog.get("doNotInventCountyLdcZoning"):
        raise SystemExit("Catalog must keep doNotInventCountyLdcZoning true")
    if catalog.get("countyLdcZoning", {}).get("status") != "gap":
        raise SystemExit("County LDC zoning must stay a gap")
    places = catalog["places"]
    if [place["id"] for place in places] != ["lakeland", "bartow", "auburndale", "lake-alfred", "lake-hamilton"]:
        raise SystemExit("Wire exactly Lakeland, Bartow, Auburndale, Lake Alfred, and Lake Hamilton")
    tokens = blocked_tokens(catalog)
    for place in places:
        for layer in (place["zoning"], place["flu"]):
            if url_is_blocked(layer["url"], tokens):
                raise SystemExit(f"{place['id']} uses a rejected or county layer {layer['url']}")
        for extra in place.get("notWired") or []:
            if extra["url"] in {place["zoning"]["url"], place["flu"]["url"]}:
                raise SystemExit(f"{place['id']} wired a layer marked unused")


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
        if isinstance(node, (int, float)) and not isinstance(node, bool):
            return
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


def bbox_in_polk(bbox: tuple[float, float, float, float], limits: list[float]) -> bool:
    west, south, east, north = bbox
    lon0, lat0, lon1, lat1 = limits
    return not (east < lon0 or west > lon1 or north < lat0 or south > lat1)


def geometry_area(geometry: dict) -> float:
    total = 0.0
    for poly in polygon_parts(geometry):
        if poly:
            total += abs(ring_signed_m2(poly[0]))
    return total if total > 1 else 1.0


class GridIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = {}
        self.broad: list[dict] = []

    def add(self, item: dict) -> None:
        west, south, east, north = item["bbox"]
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
            west, south, east, north = item["bbox"]
            if x < west or x > east or y < south or y > north:
                continue
            if point_in_geometry(x, y, item["geometry"]):
                found.append(item)
        return found


def cache_path(url: str, fields: list[str]) -> Path:
    key = hashlib.sha1(f"{url}|{','.join(fields)}".encode()).hexdigest()[:20]
    return CACHE / f"{key}.json"


def download_features(url: str, fields: list[str]) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = cache_path(url, fields)
    if cached.exists():
        return json.loads(cached.read_text())
    query = url.rstrip("/") + "/query"
    counted = fetch_json(query, {"where": "1=1", "returnCountOnly": "true", "f": "json"})
    expected = int(counted.get("count") or 0)
    id_payload = fetch_json(query, {"where": "1=1", "returnIdsOnly": "true", "f": "json"}, timeout=180)
    ids = [int(i) for i in (id_payload.get("objectIds") or [])]
    print(f"  {url.split('/services/')[-1][:80]} count {expected} ids {len(ids)}", flush=True)
    if expected and not ids:
        raise RuntimeError(f"No object ids for {url}")

    def pull(chunk: list[int], simplify: bool) -> list[dict]:
        params = {
            "objectIds": ",".join(str(i) for i in chunk),
            "outFields": ",".join(fields),
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        }
        if simplify:
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
            if done % 20 == 0:
                print(f"    {done}/{len(chunks)} batches", flush=True)
    if expected and len(features) < expected * 0.9:
        raise RuntimeError(f"{url} returned {len(features)} of {expected}")
    cached.write_text(json.dumps(features, separators=(",", ":")))
    return features


def most_local(hits: list[dict]) -> dict | None:
    if not hits:
        return None
    return sorted(hits, key=lambda item: (item["areaSqM"], item["rank"]))[0]


def resolve_hit(attribute: dict | None, spatial: list[dict]) -> dict | None:
    if attribute:
        return attribute
    return most_local(spatial)


def resolve_flu(zoning_place: str | None, attribute: dict | None, spatial: list[dict]) -> dict | None:
    if zoning_place:
        if attribute and attribute["placeId"] != zoning_place:
            attribute = None
        spatial = [item for item in spatial if item["placeId"] == zoning_place]
    return resolve_hit(attribute, spatial)


def index_layer(catalog: dict, place: dict, layer: dict, theme: str) -> tuple[list[dict], dict[str, dict]]:
    fields = list(layer["fields"])
    label_fields = list(layer.get("labelFields") or [])
    id_field = place.get("idField") if place.get("join") == "attribute-then-spatial" else None
    out_fields = list(dict.fromkeys([*fields, *label_fields, *([id_field] if id_field else [])]))
    raw = download_features(layer["url"], out_fields)
    limits = catalog["bbox"]
    indexed: list[dict] = []
    by_id: dict[str, dict] = {}
    outside = 0
    seen = 0
    for feature in raw:
        geometry = esri_rings_to_geojson((feature.get("geometry") or {}).get("rings") or [])
        attrs = feature.get("attributes") or {}
        value = read_overlay_value(catalog, attrs, fields, label_fields)
        if not geometry or not value:
            continue
        seen += 1
        bbox = feature_bbox(geometry)
        if not bbox or not bbox_in_polk(bbox, limits):
            outside += 1
            continue
        hit = {
            "bbox": bbox,
            "geometry": geometry,
            "placeId": place["id"],
            "rank": place["rank"],
            "areaSqM": geometry_area(geometry),
            "code": value["code"],
            "label": value["label"],
            "layerUrl": layer["url"],
            "theme": theme,
        }
        indexed.append(hit)
        if id_field:
            key = clean_text(attrs.get(id_field))
            if is_polk_parcel_key(key) and key not in by_id:
                by_id[key] = {
                    "placeId": place["id"],
                    "rank": place["rank"],
                    "areaSqM": 0,
                    "code": value["code"],
                    "label": value["label"],
                    "layerUrl": layer["url"],
                }
    if seen and outside / seen > 0.05:
        raise SystemExit(f"{place['id']} {theme} has {outside} of {seen} polygons outside Polk")
    print(f"    indexed {len(indexed)} {place['id']} {theme}; parcel keys {len(by_id)}; outside {outside}", flush=True)
    return indexed, by_id


def stamp_feature(
    feature: dict,
    places: dict[str, dict],
    place_ids: set[str],
    zoning_index: GridIndex,
    flu_index: GridIndex,
    zoning_ids: dict[str, dict],
    flu_ids: dict[str, dict],
) -> str | None:
    props = feature.get("properties") or {}
    if str(props.get("countyFips") or "") != FIPS:
        return None
    preserved_id = props.get("parcelId")
    preserved_acres = props.get("acreage")
    preserved_oz = props.get("opportunityZone")
    preserved_oz2 = props.get("oz2Eligibility")
    centroid = props.get("centroid") or []
    parcel_key = clean_text(preserved_id)
    lon = lat = None
    if len(centroid) == 2:
        lon, lat = float(centroid[0]), float(centroid[1])

    zoning_attr = zoning_ids.get(parcel_key) if parcel_key else None
    flu_attr = flu_ids.get(parcel_key) if parcel_key else None
    zoning_spatial = zoning_index.hits(lon, lat) if lon is not None else []
    flu_spatial = flu_index.hits(lon, lat) if lon is not None else []
    zoning = resolve_hit(zoning_attr, zoning_spatial)
    flu = resolve_flu(zoning["placeId"] if zoning else None, flu_attr, flu_spatial)

    note = props.get("municipal") if isinstance(props.get("municipal"), dict) else None
    if not zoning and not flu:
        if note and note.get("placeId") in place_ids:
            props["zoningCode"] = None
            props["zoningDistrict"] = None
            props["jurisdictionPrefix"] = None
            props["jurisdictionCode"] = None
            props["flu"] = None
            props["municipal"] = None
        props["parcelId"] = preserved_id
        props["acreage"] = preserved_acres
        props["opportunityZone"] = preserved_oz
        props["oz2Eligibility"] = preserved_oz2
        feature["properties"] = props
        return None

    place = places[(zoning or flu)["placeId"]]
    if zoning:
        props["zoningCode"] = zoning["code"]
        props["zoningDistrict"] = zoning["code"]
        props["jurisdictionPrefix"] = place["prefix"]
        props["jurisdictionCode"] = place["prefix"]
    else:
        props["zoningCode"] = None
        props["zoningDistrict"] = None
        props["jurisdictionPrefix"] = None
        props["jurisdictionCode"] = None
    if flu:
        flu_place = places[flu["placeId"]]
        props["flu"] = {
            "code": flu["code"],
            "label": flu["label"] or flu["code"],
            "jurisdiction": flu_place["name"],
            "source": flu["layerUrl"],
        }
    else:
        props["flu"] = None
    note_place = places[(zoning or flu)["placeId"]]
    props["municipal"] = {
        "placeId": note_place["id"],
        "placeName": note_place["name"],
        "zoningLayer": zoning["layerUrl"] if zoning else None,
        "fluLayer": flu["layerUrl"] if flu else None,
        "zoningLabel": zoning.get("label") if zoning else None,
        "fluGap": None,
    }
    props["parcelId"] = preserved_id
    props["acreage"] = preserved_acres
    props["opportunityZone"] = preserved_oz
    props["oz2Eligibility"] = preserved_oz2
    feature["properties"] = props
    return note_place["id"]


def gap_sentence(zoning: int, flu: int) -> str:
    return (
        "City zoning and future land use are joined for Lakeland, Bartow, Auburndale, Lake Alfred, and Lake Hamilton "
        f"onto the existing 5–150 acre parcels ({zoning} zoning, {flu} future land use). "
        "Lakeland is a centroid join. The other four cities use a Polk parcel id when the city layer has one, then the centroid. "
        "Polk County has no LDC zoning-district polygon, and county FLUNAME is not copied into zoning. "
        "County future land use is not stamped. "
        "Winter Haven, Haines City, Davenport, Fort Meade, Dundee, Eagle Lake, Frostproof, Mulberry, Polk City, "
        "Hillcrest Heights, and Highland Park stay blank. Lake Wales is token-blocked. "
        "Iowa Polk City, New Jersey Highland Park, Georgia Mulberry, the Georgia Bartow GIS host, and UK Dundee are rejected."
    )


def patch_sources_text(zoning: int, flu: int) -> None:
    """Edit only the Polk gaps inside orlando-parcel-sources.json.

    Rewriting that file with json.dumps escapes degree signs and en dashes
    that the file already stores as characters.
    """
    path = ROOT / "data" / "orlando-parcel-sources.json"
    text = path.read_text()
    start = text.find('"fips": "12105"')
    end = text.find('"name": "Seminole"', start)
    if start < 0 or end < 0:
        raise SystemExit("Could not find the Polk block in orlando-parcel-sources.json")
    block = text[start:end]
    old = "No zoning on the DOH extract."
    replacement = "City zoning is joined only for five Polk cities. County LDC zoning is still a gap."
    if old in block:
        block = block.replace(old, replacement, 1)
    elif replacement not in block:
        raise SystemExit("Polk source gaps no longer match the expected DOH sentence")
    note = json.dumps(gap_sentence(zoning, flu), ensure_ascii=False)
    if "joined for Lakeland" not in block:
        needle = '"The AGOL layer labeled Polk County parcels is in Minnesota and is not used."'
        if needle not in block:
            raise SystemExit("Polk Minnesota rejection line is missing")
        block = block.replace(needle, needle + ",\n        " + note, 1)
    path.write_text(text[:start] + block + text[end:])


def patch_json(path: Path, mutate) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text())
    mutate(data)
    path.write_text(json.dumps(data, indent=2) + "\n")


def apply_gap(county: dict, zoning: int, flu: int, keep_reuse: bool) -> None:
    if str(county.get("fips") or "") != FIPS:
        return
    note = gap_sentence(zoning, flu)
    kept: list[str] = []
    for item in county.get("gaps") or []:
        if item.startswith("City zoning and future land use are joined for Lakeland"):
            continue
        if "No zoning" in item or "no zoning" in item.lower() or "future land use on the Florida DOH" in item:
            continue
        kept.append(item)
    if keep_reuse and not any("Not re-scraped" in item or "reused" in item.lower() for item in kept):
        kept.insert(0, "Reused the Orlando complete 5.0–150.0 acre tiles. Not re-scraped.")
    kept.append(note)
    county["gaps"] = kept
    county["zoningJoinedCount"] = zoning
    county["fluJoinedCount"] = flu


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text())
    assert_catalog(catalog)
    places = {place["id"]: place for place in catalog["places"]}
    place_ids = set(places)
    tokens = blocked_tokens(catalog)
    print("Downloading Polk city layers", flush=True)
    zoning_index = GridIndex()
    flu_index = GridIndex()
    zoning_ids: dict[str, dict] = {}
    flu_ids: dict[str, dict] = {}
    downloaded: set[tuple[str, tuple[str, ...]]] = set()
    for place in catalog["places"]:
        for theme, layer, index, id_map in (
            ("zoning", place["zoning"], zoning_index, zoning_ids),
            ("flu", place["flu"], flu_index, flu_ids),
        ):
            fields = tuple(dict.fromkeys([*layer["fields"], *(layer.get("labelFields") or []), *([place["idField"]] if place.get("join") == "attribute-then-spatial" and place.get("idField") else [])]))
            key = (layer["url"], fields)
            if key in downloaded and place["id"] == "lake-alfred" and theme == "flu":
                pass
            items, by_id = index_layer(catalog, place, layer, theme)
            downloaded.add(key)
            for item in items:
                index.add(item)
            for parcel_id, hit in by_id.items():
                current = id_map.get(parcel_id)
                if current is None or hit["rank"] < current["rank"]:
                    id_map[parcel_id] = hit

    by_place: dict[str, dict[str, int]] = {place["id"]: {"zoning": 0, "flu": 0} for place in catalog["places"]}
    examples: dict[str, dict] = {}
    parcels = 0
    zoning_count = 0
    flu_count = 0
    oz_changed = 0
    files = 0
    paths = sorted(TILES.glob("*.geojson"))
    if not paths:
        raise SystemExit(f"No Polk tiles at {TILES}")
    print(f"Stamping {len(paths)} parcel tiles", flush=True)
    for path in paths:
        collection = json.loads(path.read_text())
        changed = 0
        for feature in collection.get("features") or []:
            props = feature.get("properties") or {}
            before_oz = json.dumps(props.get("opportunityZone"), sort_keys=True, default=str)
            before_oz2 = json.dumps(props.get("oz2Eligibility"), sort_keys=True, default=str)
            before_id = props.get("parcelId")
            before_acres = props.get("acreage")
            place_id = stamp_feature(feature, places, place_ids, zoning_index, flu_index, zoning_ids, flu_ids)
            props = feature["properties"]
            parcels += 1
            if props.get("parcelId") != before_id or props.get("acreage") != before_acres:
                raise SystemExit(f"Parcel id or acreage changed on {before_id}")
            if json.dumps(props.get("opportunityZone"), sort_keys=True, default=str) != before_oz:
                oz_changed += 1
            if json.dumps(props.get("oz2Eligibility"), sort_keys=True, default=str) != before_oz2:
                oz_changed += 1
            if not place_id:
                continue
            changed += 1
            if props.get("zoningCode"):
                zoning_count += 1
                by_place[place_id]["zoning"] += 1
            flu = props.get("flu") or {}
            if isinstance(flu, dict) and flu.get("code"):
                flu_count += 1
                by_place[place_id]["flu"] += 1
            municipal = props.get("municipal") or {}
            for layer in (municipal.get("zoningLayer"), municipal.get("fluLayer")):
                if layer and url_is_blocked(layer, tokens):
                    raise SystemExit(f"Rejected layer written on {props.get('parcelId')}: {layer}")
            if is_stub(catalog, props.get("zoningCode")) or (isinstance(flu, dict) and is_stub(catalog, flu.get("code"))):
                raise SystemExit(f"Stub code written on {props.get('parcelId')}")
            current = examples.get(place_id)
            has_zoning = bool(props.get("zoningCode"))
            if current is None or (has_zoning and not current.get("zoningCode")):
                examples[place_id] = {
                    "parcelId": props.get("parcelId"),
                    "tile": path.name,
                    "zoningCode": props.get("zoningCode"),
                    "flu": flu.get("code") if isinstance(flu, dict) else None,
                }
        if changed:
            path.write_text(json.dumps(collection, separators=(",", ":"), ensure_ascii=False))
        files += 1
        print(f"  {path.name} stamped {changed}", flush=True)

    if oz_changed:
        raise SystemExit(f"Opportunity Zone fields changed on {oz_changed} parcels")

    note_targets = [
        ROOT / "data" / "fixtures" / "market-parcels" / "counties" / "12105" / "county.json",
        ROOT / "data" / "fixtures" / "market-parcels" / "markets" / "tampa" / "meta.json",
        ROOT / "data" / "fixtures" / "market-parcels" / "index.json",
    ]

    def walk_counties(data: dict) -> None:
        if isinstance(data, dict) and data.get("fips") == FIPS and data.get("name") == "Polk":
            apply_gap(data, zoning_count, flu_count, keep_reuse=True)
        for value in (data.values() if isinstance(data, dict) else data if isinstance(data, list) else []):
            if isinstance(value, (dict, list)):
                walk_counties(value)

    for path in note_targets:
        patch_json(path, walk_counties)

    def set_orlando_meta(data: dict) -> None:
        for county in data.get("counties") or []:
            if county.get("fips") != FIPS:
                continue
            note = gap_sentence(zoning_count, flu_count)
            gaps = []
            for item in county.get("gaps") or []:
                if item.startswith("City zoning and future land use are joined for Lakeland"):
                    continue
                item = item.replace(
                    "No zoning or future land use on the Florida DOH EHWATER extract.",
                    "The Florida DOH extract has no zoning or future land use of its own.",
                )
                gaps.append(item)
            gaps.append(note)
            county["gaps"] = gaps
            county["zoningJoinedCount"] = zoning_count
            county["fluJoinedCount"] = flu_count

    patch_json(ROOT / "data" / "fixtures" / "orlando-parcels" / "meta.json", set_orlando_meta)

    patch_sources_text(zoning_count, flu_count)

    summary = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "catalog": "data/polk-municipal.json",
        "parcels": parcels,
        "files": files,
        "zoning": zoning_count,
        "flu": flu_count,
        "byPlace": by_place,
        "examples": examples,
        "opportunityZonesInvented": 0,
        "countyLdcZoning": "gap",
        "countyFluStamped": False,
        "rejectedNotUsed": [item["url"] for item in catalog["rejected"]],
        "notWired": ["winter-haven", "haines-city", "davenport", "fort-meade", "dundee", "eagle-lake", "frostproof", "mulberry", "polk-city", "hillcrest-heights", "highland-park", "lake-wales"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"parcels": parcels, "zoning": zoning_count, "flu": flu_count, "byPlace": by_place}, indent=2))


if __name__ == "__main__":
    main()
