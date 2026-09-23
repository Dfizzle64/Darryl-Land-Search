#!/usr/bin/env python3
"""Build Orange County municipal zoning/FLU overlay fixtures from public GIS.

Reads data/municipal-overlays.json. Active cities only. Gap cities are not fetched.
Rejects any layer whose geometry is outside Florida, and any host that is the
Edgewood, Texas ETCOG service.

Owner names, mailing addresses, sale prices, and tax values are not requested.

  python3 scripts/build_municipal_overlays.py
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "municipal-overlays.json"
FIXTURE_DIR = ROOT / "data" / "fixtures" / "municipal-overlays"
USER_AGENT = "darryl-land-search/municipal-overlay"
FLORIDA = (-87.7, 24.3, -79.6, 31.1)
ORANGE = (-81.7, 28.3, -80.85, 28.85)
REJECTED_HOSTS = ("maps.etcog.org", "etcog.org")


def fetch_json(url: str, params: dict | None = None, timeout: int = 90, retries: int = 4) -> dict:
    full = url
    if params:
        full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            if isinstance(body, dict) and body.get("error"):
                raise RuntimeError(str(body["error"]))
            return body
        except Exception as exc:  # noqa: BLE001 — retry public GIS blips
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url} failed: {last}")


def in_box(lon: float, lat: float, box: tuple[float, float, float, float]) -> bool:
    west, south, east, north = box
    return west <= lon <= east and south <= lat <= north


def perp_dist(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def douglas_peucker(points: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points
    stack = [(0, len(points) - 1)]
    keep = {0, len(points) - 1}
    while stack:
        start, end = stack.pop()
        max_d = 0.0
        idx = None
        for i in range(start + 1, end):
            dist = perp_dist(points[i], points[start], points[end])
            if dist > max_d:
                max_d = dist
                idx = i
        if idx is not None and max_d > tol:
            keep.add(idx)
            stack.append((start, idx))
            stack.append((idx, end))
    return [points[i] for i in sorted(keep)]


def simplify_ring(coords: list[list[float]], tol: float = 0.00012) -> list[list[float]]:
    if len(coords) < 4:
        return []
    open_ring = coords[:-1] if coords[0] == coords[-1] else list(coords)
    pts = [(float(x), float(y)) for x, y in open_ring]
    use = tol if len(pts) < 400 else tol * 2
    simplified = douglas_peucker(pts, use)
    if len(simplified) < 3:
        simplified = douglas_peucker(pts, use / 20)
    if len(simplified) < 3:
        return []
    rounded = [[round(x, 5), round(y, 5)] for x, y in simplified]
    if rounded[0] != rounded[-1]:
        rounded.append(rounded[0])
    return rounded if len(rounded) >= 4 else []


def rings_to_polygons(geom: dict | None) -> list[list[list[list[float]]]] | None:
    if not geom or not geom.get("rings"):
        return None
    polygons: list[list[list[list[float]]]] = []
    current: list[list[list[float]]] = []
    for ring in geom["rings"]:
        coords = simplify_ring([[float(x), float(y)] for x, y in ring])
        if len(coords) < 4:
            continue
        area = 0.0
        for i in range(len(coords) - 1):
            area += coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1]
        if not current or area > 0:
            if current:
                polygons.append(current)
            current = [coords]
        else:
            current.append(coords)
    if current:
        polygons.append(current)
    return polygons or None


def polygon_bbox(polygons: list[list[list[list[float]]]]) -> list[float]:
    xs: list[float] = []
    ys: list[float] = []
    for poly in polygons:
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    return [min(xs), min(ys), max(xs), max(ys)]


def polygon_centroid(polygons: list[list[list[list[float]]]]) -> tuple[float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for poly in polygons:
        if not poly:
            continue
        ring = poly[0]
        body = ring[:-1] if len(ring) > 1 else ring
        xs.extend(p[0] for p in body)
        ys.extend(p[1] for p in body)
    if not xs:
        return None
    return sum(xs) / len(xs), sum(ys) / len(ys)


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NULL", "NONE", "<NULL>"}:
        return None
    return text


def num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def assert_allowed_url(url: str) -> None:
    lowered = url.lower()
    for host in REJECTED_HOSTS:
        if host in lowered:
            raise SystemExit(f"Refusing rejected host in {url}")


def layer_meta(url: str) -> dict:
    assert_allowed_url(url)
    meta = fetch_json(url, {"f": "json"})
    name = str(meta.get("name") or "")
    geom = str(meta.get("geometryType") or "")
    if "Polygon" not in geom:
        raise SystemExit(f"{url} is {geom or 'not a polygon'}, not a zoning/FLU polygon layer")
    oid = meta.get("objectIdField") or "OBJECTID"
    for field in meta.get("fields") or []:
        if field.get("type") == "esriFieldTypeOID":
            oid = field["name"]
            break
    return {"name": name, "objectIdField": oid, "fields": {f["name"] for f in meta.get("fields") or []}}


def raw_centroid(geom: dict | None) -> tuple[float, float] | None:
    rings = (geom or {}).get("rings") or []
    if not rings or not rings[0]:
        return None
    xs = [float(point[0]) for point in rings[0]]
    ys = [float(point[1]) for point in rings[0]]
    if not xs:
        return None
    return sum(xs) / len(xs), sum(ys) / len(ys)


def probe_florida(url: str, oid: str, object_id: int, label: str) -> tuple[float, float]:
    data = fetch_json(
        url.rstrip("/") + "/query",
        {
            "objectIds": str(object_id),
            "outFields": oid,
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        },
    )
    features = data.get("features") or []
    if not features:
        raise SystemExit(f"{label} returned no features: {url}")
    center = raw_centroid(features[0].get("geometry") or {})
    if not center or not in_box(center[0], center[1], FLORIDA):
        raise SystemExit(f"{label} sample centroid {center} is outside Florida. Refusing {url}")
    if not in_box(center[0], center[1], ORANGE):
        raise SystemExit(f"{label} sample centroid {center} is outside Orange County, Florida. Refusing {url}")
    print(f"  florida ok {label} centroid ({center[0]:.5f}, {center[1]:.5f})")
    return center


def fetch_ids(url: str, oid: str) -> list[int]:
    data = fetch_json(url.rstrip("/") + "/query", {"where": "1=1", "returnIdsOnly": "true", "f": "json"})
    ids = data.get("objectIds") or []
    if not ids:
        raise SystemExit(f"No object ids for {url}")
    return [int(i) for i in ids]


def fetch_batch(url: str, ids: list[int], out_fields: str, geometry: bool) -> list[dict]:
    params = {
        "objectIds": ",".join(str(i) for i in ids),
        "outFields": out_fields,
        "returnGeometry": "true" if geometry else "false",
        "f": "json",
    }
    if geometry:
        params["outSR"] = "4326"
        params["geometryPrecision"] = "5"
        params["maxAllowableOffset"] = "0.00015"
    try:
        data = fetch_json(url.rstrip("/") + "/query", params)
    except RuntimeError:
        if not geometry:
            raise
        params.pop("maxAllowableOffset", None)
        data = fetch_json(url.rstrip("/") + "/query", params)
    return data.get("features") or []


def wanted_fields(layer: dict, meta_fields: set[str]) -> list[str]:
    names = [
        layer.get("parcelIdField"),
        layer.get("altParcelIdField"),
        layer.get("zoningField"),
        layer.get("zoningLabelField"),
        layer.get("fluField"),
        layer.get("fluLabelField"),
        layer.get("altFluField"),
        layer.get("acreageField"),
    ]
    return [name for name in names if name and name in meta_fields]


def record_from_attrs(attrs: dict, layer: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    zoning = clean(attrs.get(layer.get("zoningField") or ""))
    label = clean(attrs.get(layer.get("zoningLabelField") or ""))
    flu = clean(attrs.get(layer.get("fluField") or ""))
    flu_label = clean(attrs.get(layer.get("fluLabelField") or ""))
    alt_flu = clean(attrs.get(layer.get("altFluField") or ""))
    if zoning and zoning.upper() != "CITY":
        out["z"] = zoning
    if label and label != zoning:
        out["zl"] = label
    if flu:
        out["f"] = flu
    elif alt_flu:
        out["f"] = alt_flu
    if flu_label and flu_label != out.get("f"):
        out["fl"] = flu_label
    return out


def parcel_keys(value: str | None) -> list[str]:
    if not value:
        return []
    raw = value.strip().upper()
    if ":" in raw:
        raw = raw.split(":")[-1]
    bare = raw[6:] if raw.startswith("12095-") else raw
    if not any(ch.isdigit() for ch in bare):
        return []
    if not 8 <= len(bare) <= 24:
        return []
    keys = []
    for key in (bare, f"12095-{bare}"):
        if key not in keys:
            keys.append(key)
    return keys


def merge_attr(existing: dict[str, str], incoming: dict[str, str]) -> dict[str, str]:
    merged = dict(existing)
    for key, value in incoming.items():
        if value and not merged.get(key):
            merged[key] = value
    return merged


def build_city(city: dict) -> dict:
    print(f"\n{city['name']}")
    attributes: dict[str, dict[str, str]] = {}
    spatial: list[dict] = []
    dropped_outside = 0
    kept_geom = 0
    for layer in city.get("layers") or []:
        url = layer["url"]
        meta = layer_meta(url)
        fields = wanted_fields(layer, meta["fields"])
        if layer.get("zoningField") and layer["zoningField"] not in meta["fields"]:
            raise SystemExit(f"{url} missing zoning field {layer['zoningField']}")
        if layer.get("fluField") and layer["fluField"] not in meta["fields"] and not layer.get("altFluField"):
            raise SystemExit(f"{url} missing FLU field {layer['fluField']}")
        ids = fetch_ids(url, meta["objectIdField"])
        probe_florida(url, meta["objectIdField"], ids[0], f"{city['id']}:{layer['role']}")
        print(f"  {layer['role']} {len(ids)} features, fields {', '.join(fields) or '(none)'}")
        geometry_mode = layer.get("geometry") or "none"
        field_names = [meta["objectIdField"], *fields]
        out_fields = ",".join(dict.fromkeys(field_names))
        geom_ids: list[int] = []
        for start in range(0, len(ids), 150):
            chunk = ids[start : start + 150]
            features = fetch_batch(url, chunk, out_fields, False)
            for feature in features:
                attrs = feature.get("attributes") or {}
                rec = record_from_attrs(attrs, layer)
                pid = clean(attrs.get(layer.get("parcelIdField") or ""))
                alt = clean(attrs.get(layer.get("altParcelIdField") or ""))
                for key in parcel_keys(pid) + parcel_keys(alt):
                    attributes[key] = merge_attr(attributes.get(key, {}), rec)
                if geometry_mode == "none":
                    continue
                feature_id = attrs.get(meta["objectIdField"])
                if feature_id is None:
                    continue
                feature_id = int(feature_id)
                acres = num(attrs.get(layer.get("acreageField") or ""))
                if geometry_mode == "acres-gte-5" and acres is not None and (acres < 5 or acres > 150):
                    continue
                geom_ids.append(feature_id)
            if start and start % 1500 == 0:
                print(f"    attributes {start}/{len(ids)}")
        for start in range(0, len(geom_ids), 80):
            chunk = geom_ids[start : start + 80]
            features = fetch_batch(url, chunk, out_fields, True)
            for feature in features:
                attrs = feature.get("attributes") or {}
                polygons = rings_to_polygons(feature.get("geometry") or {})
                if not polygons:
                    continue
                center = polygon_centroid(polygons)
                if not center or not in_box(center[0], center[1], FLORIDA) or not in_box(center[0], center[1], ORANGE):
                    dropped_outside += 1
                    continue
                rec = record_from_attrs(attrs, layer)
                pid = clean(attrs.get(layer.get("parcelIdField") or ""))
                item = dict(rec)
                item["b"] = polygon_bbox(polygons)
                item["g"] = polygons
                keys = parcel_keys(pid)
                if keys:
                    item["id"] = keys[0]
                spatial.append(item)
                kept_geom += 1
            if start and start % 800 == 0:
                print(f"    geometry {start}/{len(geom_ids)}")
    if dropped_outside:
        raise SystemExit(f"{city['id']} dropped {dropped_outside} features outside Orange County, Florida")
    xs0 = [item["b"][0] for item in spatial]
    ys0 = [item["b"][1] for item in spatial]
    xs1 = [item["b"][2] for item in spatial]
    ys1 = [item["b"][3] for item in spatial]
    bbox = [min(xs0), min(ys0), max(xs1), max(ys1)] if spatial else None
    if bbox and (not in_box((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2, FLORIDA)):
        raise SystemExit(f"{city['id']} union bbox {bbox} is outside Florida")
    if bbox and (bbox[0] < ORANGE[0] or bbox[2] > ORANGE[2] or bbox[1] < ORANGE[1] or bbox[3] > ORANGE[3]):
        # A simplified ring can sit a hair outside the loose county box. Reject only clear misses.
        if bbox[0] < -83 or bbox[2] > -80 or bbox[1] < 27.5 or bbox[3] > 29.2:
            raise SystemExit(f"{city['id']} union bbox {bbox} is not in the Orlando area")
    bare_ids = {key for key in attributes if not key.startswith("12095-")}
    summary = {
        "id": city["id"],
        "name": city["name"],
        "prefix": city["prefix"],
        "attributeParcels": len(bare_ids),
        "spatialPolygons": len(spatial),
        "bbox": bbox,
    }
    print(f"  wrote preview {summary}")
    return {
        "id": city["id"],
        "name": city["name"],
        "prefix": city["prefix"],
        "status": "active",
        "coverage": "city-only",
        "bbox": bbox,
        "attributes": attributes,
        "spatial": spatial,
        "summary": summary,
    }


def code_counts(city_fixture: dict) -> dict[str, list[list[Any]]]:
    zoning: dict[str, int] = {}
    flu: dict[str, int] = {}
    seen: set[str] = set()
    for key, rec in city_fixture["attributes"].items():
        if key.startswith("12095-"):
            continue
        token = key
        if token in seen:
            continue
        seen.add(token)
        if rec.get("z"):
            zoning[rec["z"]] = zoning.get(rec["z"], 0) + 1
        if rec.get("f"):
            flu[rec["f"]] = flu.get(rec["f"], 0) + 1
    if not zoning or not flu:
        for item in city_fixture["spatial"]:
            if item.get("z"):
                zoning[item["z"]] = zoning.get(item["z"], 0) + 1
            if item.get("f"):
                flu[item["f"]] = flu.get(item["f"], 0) + 1
    def top(counts: dict[str, int]) -> list[list[Any]]:
        return [[code, count] for code, count in sorted(counts.items(), key=lambda kv: -kv[1])[:40]]

    return {"zoning": top(zoning), "flu": top(flu)}


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text())
    for rejected in registry.get("rejected") or []:
        assert_allowed_url("https://example.com/")  # keep helper referenced
        url = str(rejected.get("url") or "")
        if "etcog.org" not in url.lower():
            raise SystemExit("Expected the Edgewood, Texas service to stay on the rejected list")
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    codes: dict[str, Any] = {}
    for city in registry["cities"]:
        if city.get("status") != "active":
            print(f"skip gap {city['id']}")
            continue
        for layer in city.get("layers") or []:
            assert_allowed_url(layer["url"])
        built = build_city(city)
        summary = built.pop("summary")
        path = ROOT / city["fixture"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(built, separators=(",", ":")))
        print(f"  bytes {path.stat().st_size}")
        summaries.append(summary)
        codes[city["id"]] = code_counts(built)
    coverage = {
        "generatedFrom": "data/municipal-overlays.json",
        "floridaBbox": list(FLORIDA),
        "cities": summaries,
        "codes": codes,
        "gaps": [city["id"] for city in registry["cities"] if city.get("status") != "active"],
        "rejected": [item["id"] for item in registry.get("rejected") or []],
    }
    (FIXTURE_DIR / "coverage.json").write_text(json.dumps(coverage, indent=2))
    print("\ncoverage", FIXTURE_DIR / "coverage.json")


if __name__ == "__main__":
    main()
