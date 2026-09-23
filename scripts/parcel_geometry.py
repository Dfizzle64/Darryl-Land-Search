"""Esri polygon rings to GeoJSON, with a cadastral simplify tolerance.

ArcGIS exterior rings are clockwise. Holes are counter-clockwise.
GeoJSON (RFC 7946) wants the opposite winding. Treating a positive shoelace
area as a new exterior turns holes into extra polygons and later exteriors
into holes. That is the garbage-outline bug.

Simplify stays near 1–7 meters. The old path jumped to ~30 meters on dense
shorelines and, when that collapsed, kept the first three vertices.
"""

from __future__ import annotations

import math

# ~1.3 m, ~4 m, ~7 m at Florida latitudes. Do not jump to ~30 m.
BASE_TOL = 0.000012
RELAX_TOL = 0.000035
MAX_TOL = 0.00006


def signed_area(coords: list[list[float]]) -> float:
    area = 0.0
    for i in range(len(coords) - 1):
        area += coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1]
    return area / 2.0


def ring_signed_m2(coords: list[list[float]]) -> float:
    """Signed area in square meters. Clockwise ArcGIS rings are negative."""
    if len(coords) < 4:
        return 0.0
    lat0 = sum(p[1] for p in coords) / len(coords)
    kx = 111_320 * math.cos(math.radians(lat0))
    ky = 110_540
    area = 0.0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i][0] * kx, coords[i][1] * ky
        x2, y2 = coords[i + 1][0] * kx, coords[i + 1][1] * ky
        area += x1 * y2 - x2 * y1
    return area / 2.0


def perp_dist(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
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


def _close(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not points:
        return points
    if points[0] != points[-1]:
        return points + [points[0]]
    return points


def _round_ring(points: list[tuple[float, float]]) -> list[list[float]]:
    return [[round(x, 6), round(y, 6)] for x, y in points]


def simplify_ring(coords: list[list[float]], tol: float = BASE_TOL) -> list[list[float]]:
    """Simplify one ring. Never replace a real ring with its first three vertices."""
    if len(coords) < 4:
        return []
    open_ring = coords[:-1] if coords[0] == coords[-1] else list(coords)
    pts = [(float(x), float(y)) for x, y in open_ring]
    if len(pts) < 3:
        return []
    if len(pts) <= 4:
        return _round_ring(_close(pts))
    simplified = douglas_peucker(pts, tol)
    if len(simplified) > 500:
        simplified = douglas_peucker(pts, max(tol, RELAX_TOL))
    if len(simplified) > 800:
        simplified = douglas_peucker(pts, max(tol, MAX_TOL))
    if len(simplified) < 3:
        step = max(1, len(pts) // 80)
        simplified = pts[::step]
        if len(simplified) < 3:
            simplified = pts
    simplified = _close(simplified)
    if len(simplified) < 4:
        simplified = _close(pts)
    return _round_ring(simplified)


def _ensure_closed(raw: list[list[float]]) -> list[list[float]]:
    if raw[0] != raw[-1]:
        return raw + [raw[0]]
    return raw


def esri_rings_to_geojson(rings: list, tol: float = BASE_TOL) -> dict | None:
    """Group Esri rings into polygons and emit RFC 7946 winding."""
    polygons: list[list[list[list[float]]]] = []
    current: list[list[list[float]]] = []
    for ring in rings or []:
        raw = [[float(x), float(y)] for x, y in ring]
        if len(raw) < 4:
            continue
        raw = _ensure_closed(raw)
        area = signed_area(raw)
        if abs(area) < 1e-14:
            continue
        coords = simplify_ring(raw, tol)
        if len(coords) < 4:
            continue
        # Positive shoelace is counter-clockwise: an Esri hole.
        is_hole = area > 0
        if is_hole and current:
            current.append(coords)
        else:
            if current:
                polygons.append(current)
            current = [coords]
    if current:
        polygons.append(current)
    if not polygons:
        return None

    normalized: list[list[list[list[float]]]] = []
    for poly in polygons:
        outer = poly[0]
        if signed_area(outer) < 0:
            outer = list(reversed(outer))
        holes: list[list[list[float]]] = []
        for hole in poly[1:]:
            if signed_area(hole) > 0:
                hole = list(reversed(hole))
            holes.append(hole)
        normalized.append([outer, *holes])
    if len(normalized) == 1:
        return {"type": "Polygon", "coordinates": normalized[0]}
    return {"type": "MultiPolygon", "coordinates": normalized}


def polygon_parts(geometry: dict) -> list:
    if geometry.get("type") == "Polygon":
        return [geometry["coordinates"]]
    if geometry.get("type") == "MultiPolygon":
        return list(geometry["coordinates"])
    return []


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


def _inside_polygon(x: float, y: float, poly: list[list[list[float]]]) -> bool:
    if not poly or not _point_in_ring(x, y, poly[0]):
        return False
    return not any(_point_in_ring(x, y, hole) for hole in poly[1:])


def geometry_contains(geometry: dict | None, lon: float, lat: float) -> bool:
    if not geometry:
        return False
    return any(_inside_polygon(lon, lat, poly) for poly in polygon_parts(geometry))


def representative_point(geometry: dict) -> tuple[float, float] | None:
    """A point inside the largest part. Vertex averages fall outside concave rings."""
    parts = polygon_parts(geometry)
    best = None
    best_area = -1.0
    for poly in parts:
        if not poly or not poly[0]:
            continue
        area = abs(signed_area(poly[0]))
        if area > best_area:
            best_area = area
            best = poly
    if not best:
        return None
    ring = best[0]
    body = ring[:-1] if len(ring) > 1 else ring
    if not body:
        return None
    lon = sum(p[0] for p in body) / len(body)
    lat = sum(p[1] for p in body) / len(body)
    if _inside_polygon(lon, lat, best):
        return round(lon, 6), round(lat, 6)
    xs = [p[0] for p in body]
    ys = [p[1] for p in body]
    bx = (min(xs) + max(xs)) / 2
    by = (min(ys) + max(ys)) / 2
    if _inside_polygon(bx, by, best):
        return round(bx, 6), round(by, 6)
    step = max(1, len(body) // 16)
    for point in body[::step]:
        qlon = point[0] * 0.8 + lon * 0.2
        qlat = point[1] * 0.8 + lat * 0.2
        if _inside_polygon(qlon, qlat, best):
            return round(qlon, 6), round(qlat, 6)
    return round(body[0][0], 6), round(body[0][1], 6)


def net_acres(rings: list) -> float:
    net = 0.0
    for ring in rings or []:
        raw = [[float(x), float(y)] for x, y in ring]
        if len(raw) < 4:
            continue
        if raw[0] != raw[-1]:
            raw = raw + [raw[0]]
        net += ring_signed_m2(raw)
    return abs(net) / 4046.8564224
