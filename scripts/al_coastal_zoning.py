"""City zoning overlays for Baldwin and Mobile county parcels.

County parcels stay the ownership, tax, and acreage source. These helpers only
attach a zoning code. Gulf Shores, Orange Beach, and the City of Mobile are
spatial. Foley joins on Baldwin PID. Daphne and Fairhope base zoning are not
joined — callers document those gaps.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from parcel_geometry import signed_area

CELL_DEG = 0.02
LARGE_SPAN = 0.35


def zone_label(raw: Any, domain: dict[int, str]) -> tuple[str | None, bool]:
    """Return (label, decoded_from_domain). Integers use the coded-value domain when present."""
    if raw is None or raw == "":
        return None, False
    if isinstance(raw, str) and not raw.strip():
        return None, False
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        text = str(raw).strip()
        return (text or None), False
    if not math.isfinite(parsed):
        return None, False
    key = int(parsed)
    if domain and key in domain:
        return domain[key], True
    if parsed == key:
        return str(key), False
    return str(parsed), False


def _closed(ring: list) -> list[list[float]]:
    raw = [[float(x), float(y)] for x, y in ring]
    if len(raw) < 4:
        return []
    if raw[0] != raw[-1]:
        raw = raw + [raw[0]]
    return raw


def _parts(rings: list) -> list[list[list[list[float]]]]:
    """Esri rings: clockwise exteriors (negative shoelace), counter-clockwise holes."""
    parts: list[list[list[list[float]]]] = []
    current: list[list[list[float]]] | None = None
    for ring in rings or []:
        raw = _closed(ring)
        if not raw:
            continue
        area = signed_area(raw)
        if abs(area) < 1e-14:
            continue
        if area > 0 and current is not None:
            current.append(raw)
        else:
            if current:
                parts.append(current)
            current = [raw]
    if current:
        parts.append(current)
    return parts


def _point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def rings_contain(lon: float, lat: float, rings: list) -> bool:
    for poly in _parts(rings):
        if not poly or not _point_in_ring(lon, lat, poly[0]):
            continue
        if any(_point_in_ring(lon, lat, hole) for hole in poly[1:]):
            continue
        return True
    return False


def polygon_record(rings: list, code: str, district: str | None) -> dict | None:
    xs: list[float] = []
    ys: list[float] = []
    for ring in rings or []:
        for x, y in ring:
            xs.append(float(x))
            ys.append(float(y))
    if not xs:
        return None
    if max(abs(min(xs)), abs(max(xs))) > 180 or max(abs(min(ys)), abs(max(ys))) > 90:
        return None
    outer = _closed(rings[0])
    area = abs(signed_area(outer)) if outer else 0.0
    return {
        "code": code,
        "district": district,
        "rings": rings,
        "bbox": (min(xs), min(ys), max(xs), max(ys)),
        "area": area,
    }


def spatial_index(polys: list[dict]) -> tuple[dict[tuple[int, int], list[int]], list[int]]:
    index: dict[tuple[int, int], list[int]] = defaultdict(list)
    large: list[int] = []
    for i, poly in enumerate(polys):
        minx, miny, maxx, maxy = poly["bbox"]
        if (maxx - minx) > LARGE_SPAN or (maxy - miny) > LARGE_SPAN:
            large.append(i)
            continue
        ix0 = math.floor(minx / CELL_DEG)
        ix1 = math.floor(maxx / CELL_DEG)
        iy0 = math.floor(miny / CELL_DEG)
        iy1 = math.floor(maxy / CELL_DEG)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                index[(ix, iy)].append(i)
    return index, large


def best_polygon(index: dict, large: list[int], polys: list[dict], lon: float, lat: float) -> dict | None:
    cell = (math.floor(lon / CELL_DEG), math.floor(lat / CELL_DEG))
    best = None
    for i in [*index.get(cell, ()), *large]:
        poly = polys[i]
        minx, miny, maxx, maxy = poly["bbox"]
        if not (minx <= lon <= maxx and miny <= lat <= maxy):
            continue
        if not rings_contain(lon, lat, poly["rings"]):
            continue
        if best is None or poly["area"] < best["area"]:
            best = poly
    return best


def apply_spatial_overlay(
    features: list[dict],
    polys: list[dict],
    *,
    city: str,
    replace: bool,
) -> int:
    """Set zoning from the smallest containing polygon. County fill uses replace=False."""
    if not polys:
        return 0
    index, large = spatial_index(polys)
    hits = 0
    for feature in features:
        props = feature["properties"]
        if not replace and props.get("zoningCode"):
            continue
        lon, lat = props["centroid"]
        best = best_polygon(index, large, polys, lon, lat)
        if not best:
            continue
        props["zoningCode"] = best["code"]
        props["zoningDistrict"] = best.get("district")
        props["jurisdictionCode"] = city
        props["_zoningSource"] = city
        hits += 1
    return hits


def apply_pid_overlay(features: list[dict], table: dict[str, dict], *, city: str) -> int:
    """Foley: Baldwin PID → city Zoning/FeatureServer/3. City code replaces county zoning."""
    hits = 0
    for feature in features:
        props = feature["properties"]
        key = props.get("_joinKey")
        row = table.get(key) if key else None
        if not row or not row.get("code"):
            continue
        props["zoningCode"] = row["code"]
        props["zoningDistrict"] = row.get("district")
        props["jurisdictionCode"] = city
        props["_zoningSource"] = city
        hits += 1
    return hits


def strip_internal(features: list[dict]) -> None:
    for feature in features:
        props = feature["properties"]
        props.pop("_joinKey", None)
        props.pop("_zoningSource", None)
