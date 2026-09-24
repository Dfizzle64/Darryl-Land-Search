"""Municipal zoning and FLU joins for the Alabama GIS re-chase.

Public layers only. City codes replace a county baseline inside that city.
Fairhope AO/MO polygons are recorded as overlays and never become zoningCode.
Key joins (PID, PIN, PARCELID, Assess_Num) run first. Centroid spatial join
fills city parcels whose ids did not match.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Callable

from parcel_geometry import point_in_geometry, signed_area

FetchIds = Callable[[str, str], list[int]]
FetchByIds = Callable[..., list[dict]]

OVERLAY_MARKERS = ("overlay",)


def norm_key(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().upper().split())
    if not text or text in {"0", "NONE", "NULL"}:
        return None
    return text


def compact_key(value: str) -> str:
    return "".join(ch for ch in value if not ch.isspace())


def is_overlay_label(value: str | None) -> bool:
    if not value:
        return False
    text = value.strip().lower()
    return any(marker in text for marker in OVERLAY_MARKERS)


def parcel_lookup_keys(props: dict) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add(raw: Any) -> None:
        key = norm_key(raw)
        if not key or key in seen:
            return
        seen.add(key)
        ordered.append(key)
        compact = compact_key(key)
        if compact != key and compact not in seen:
            seen.add(compact)
            ordered.append(compact)

    for alt in props.get("_altIds") or []:
        add(alt)
    add(props.get("parcelId"))
    return ordered


def _index_record(index: dict[str, dict], keys: list[Any], record: dict) -> None:
    for raw in keys:
        key = norm_key(raw)
        if not key:
            continue
        index.setdefault(key, record)
        compact = compact_key(key)
        index.setdefault(compact, record)


def _lookup(index: dict[str, dict], props: dict) -> dict | None:
    for key in parcel_lookup_keys(props):
        hit = index.get(key)
        if hit:
            return hit
    return None


def _rings_to_geometry(rings: list) -> dict | None:
    """Group Esri rings without simplifying. Join tests want the published outline."""
    polygons: list[list[list[list[float]]]] = []
    current: list[list[list[float]]] = []
    for ring in rings or []:
        raw = [[float(x), float(y)] for x, y in ring]
        if len(raw) < 4:
            continue
        if raw[0] != raw[-1]:
            raw = raw + [raw[0]]
        area = signed_area(raw)
        if abs(area) < 1e-14:
            continue
        is_hole = area > 0
        if is_hole and current:
            current.append(raw)
        else:
            if current:
                polygons.append(current)
            current = [raw]
    if current:
        polygons.append(current)
    if not polygons:
        return None
    normalized: list[list[list[list[float]]]] = []
    for poly in polygons:
        outer = poly[0]
        if signed_area(outer) < 0:
            outer = list(reversed(outer))
        holes = []
        for hole in poly[1:]:
            if signed_area(hole) > 0:
                hole = list(reversed(hole))
            holes.append(hole)
        normalized.append([outer, *holes])
    if len(normalized) == 1:
        return {"type": "Polygon", "coordinates": normalized[0]}
    return {"type": "MultiPolygon", "coordinates": normalized}


def _bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    parts = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    for poly in parts:
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _area(geometry: dict) -> float:
    parts = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    total = 0.0
    for poly in parts:
        if poly:
            total += abs(signed_area(poly[0]))
    return total


class PolyGrid:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.bins: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.large: list[int] = []
        self.items: list[dict] = []

    def add(self, geometry: dict, payload: dict) -> None:
        bbox = _bbox(geometry)
        if not bbox:
            return
        idx = len(self.items)
        self.items.append({"geometry": geometry, "bbox": bbox, "area": _area(geometry), **payload})
        minx, miny, maxx, maxy = bbox
        ix0, ix1 = math.floor(minx / self.cell), math.floor(maxx / self.cell)
        iy0, iy1 = math.floor(miny / self.cell), math.floor(maxy / self.cell)
        span = (ix1 - ix0 + 1) * (iy1 - iy0 + 1)
        if span > 250:
            self.large.append(idx)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.bins[(ix, iy)].append(idx)

    def containing(self, lon: float, lat: float) -> list[dict]:
        ix = math.floor(lon / self.cell)
        iy = math.floor(lat / self.cell)
        hits: list[dict] = []
        seen: set[int] = set()
        for idx in [*self.bins.get((ix, iy), []), *self.large]:
            if idx in seen:
                continue
            seen.add(idx)
            item = self.items[idx]
            west, south, east, north = item["bbox"]
            if lon < west or lon > east or lat < south or lat > north:
                continue
            if point_in_geometry(lon, lat, item["geometry"]):
                hits.append(item)
        return hits


def _load(
    layer: dict,
    fields: list[str],
    fetch_object_ids: FetchIds,
    fetch_by_ids: FetchByIds,
    *,
    geometry: bool,
) -> list[dict]:
    url = layer["url"]
    where = layer.get("where") or "1=1"
    ids = fetch_object_ids(url, where)
    print(f"  join layer {len(ids)} {url.split('/services/')[-1][:96]}", flush=True)
    if not ids:
        return []
    batch = 70 if geometry else 300
    return fetch_by_ids(url, ids, fields, batch=batch, return_geometry=geometry)


def _clean(value: Any) -> str | None:
    key = norm_key(value)
    if not key:
        return None
    return str(value).strip()


def _centroid(props: dict) -> tuple[float, float] | None:
    center = props.get("centroid") or [None, None]
    lon, lat = center[0], center[1]
    if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
        return float(lon), float(lat)
    return None


def _assign_city(props: dict, city: str, code: str, district: str | None) -> None:
    if is_overlay_label(code):
        return
    props["zoningCode"] = code
    props["zoningDistrict"] = district if district and district.upper() != code.upper() else None
    props["jurisdictionCode"] = city


def apply_municipal_joins(
    features: list[dict],
    municipal: dict,
    fetch_object_ids: FetchIds,
    fetch_by_ids: FetchByIds,
) -> list[str]:
    notes: list[str] = []
    stats: dict[str, int] = defaultdict(int)
    city_names = {city["name"] for city in municipal.get("cities") or []}

    for city in municipal.get("cities") or []:
        fields = list(dict.fromkeys([*city["keyFields"], city["codeField"], city.get("districtField") or city["codeField"]]))
        try:
            rows = _load(city, fields, fetch_object_ids, fetch_by_ids, geometry=True)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{city['name']} zoning was not joined: {exc}")
            continue
        index: dict[str, dict] = {}
        grid = PolyGrid()
        kept = 0
        for row in rows:
            attrs = row.get("attributes") or {}
            code = _clean(attrs.get(city["codeField"]))
            if not code or is_overlay_label(code):
                continue
            district = _clean(attrs.get(city["districtField"])) if city.get("districtField") else None
            record = {"city": city["name"], "code": code, "district": district}
            _index_record(index, [attrs.get(key) for key in city["keyFields"]], record)
            geometry = _rings_to_geometry((row.get("geometry") or {}).get("rings"))
            if geometry:
                grid.add(geometry, record)
                kept += 1
        print(f"  {city['name']} zoning index {len(index)} keys, {kept} polygons", flush=True)
        for feature in features:
            props = feature["properties"]
            if props.get("jurisdictionCode") in city_names:
                continue
            hit = _lookup(index, props)
            how = "key"
            if hit is None:
                center = _centroid(props)
                if center is None:
                    continue
                spatial = grid.containing(center[0], center[1])
                same = [item for item in spatial if item["city"] == city["name"]]
                if not same:
                    continue
                hit = min(same, key=lambda item: item["area"])
                how = "spatial"
            before = props.get("jurisdictionCode")
            _assign_city(props, city["name"], hit["code"], hit.get("district"))
            if props.get("jurisdictionCode") != city["name"]:
                continue
            stats[f"{city['name']} {how}"] += 1
            stats[city["name"]] += 1
            if before == "Baldwin County":
                stats[f"{city['name']} replaced county"] += 1

    county = municipal.get("countyZoning")
    if county:
        try:
            fields = [county["codeField"]]
            if county.get("districtField"):
                fields.append(county["districtField"])
            rows = _load(county, fields, fetch_object_ids, fetch_by_ids, geometry=True)
            grid = PolyGrid()
            for row in rows:
                attrs = row.get("attributes") or {}
                code = _clean(attrs.get(county["codeField"]))
                if not code or is_overlay_label(code):
                    continue
                geometry = _rings_to_geometry((row.get("geometry") or {}).get("rings"))
                if not geometry:
                    continue
                district = _clean(attrs.get(county["districtField"])) if county.get("districtField") else None
                grid.add(geometry, {"code": code, "district": district})
            print(f"  county zoning polygons {len(grid.items)}", flush=True)
            for feature in features:
                props = feature["properties"]
                if props.get("zoningCode") or props.get("jurisdictionCode") in city_names:
                    continue
                center = _centroid(props)
                if center is None:
                    continue
                hits = grid.containing(center[0], center[1])
                if not hits:
                    continue
                hit = min(hits, key=lambda item: item["area"])
                props["zoningCode"] = hit["code"]
                props["zoningDistrict"] = hit["district"] if hit.get("district") and hit["district"].upper() != hit["code"].upper() else None
                props["jurisdictionCode"] = county.get("name") or "Baldwin County"
                stats["county zoning"] += 1
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Baldwin County Zoning/42 was not joined: {exc}")

    flu = municipal.get("flu")
    if flu:
        fields = list(dict.fromkeys([*flu["keyFields"], flu["codeField"], flu.get("labelField") or flu["codeField"]]))
        try:
            rows = _load(flu, fields, fetch_object_ids, fetch_by_ids, geometry=True)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{flu['name']} FLU was not joined: {exc}")
            rows = []
        index = {}
        grid = PolyGrid()
        for row in rows:
            attrs = row.get("attributes") or {}
            code = _clean(attrs.get(flu["codeField"]))
            if not code:
                continue
            label = _clean(attrs.get(flu["labelField"])) if flu.get("labelField") else None
            record = {
                "code": code,
                "label": label or code,
                "jurisdiction": flu["name"],
                "source": flu["source"],
            }
            _index_record(index, [attrs.get(key) for key in flu["keyFields"]], record)
            geometry = _rings_to_geometry((row.get("geometry") or {}).get("rings"))
            if geometry:
                grid.add(geometry, record)
        for feature in features:
            props = feature["properties"]
            if props.get("jurisdictionCode") in city_names - {flu["name"]}:
                continue
            hit = _lookup(index, props)
            how = "key"
            if hit is None:
                center = _centroid(props)
                if center is None:
                    continue
                spatial = grid.containing(center[0], center[1])
                if not spatial:
                    continue
                hit = min(spatial, key=lambda item: item["area"])
                how = "spatial"
            props["flu"] = {
                "code": hit["code"],
                "label": hit.get("label") or hit["code"],
                "jurisdiction": flu["name"],
                "source": flu["source"],
            }
            stats[f"{flu['name']} FLU {how}"] += 1
            stats[f"{flu['name']} FLU"] += 1
            if props.get("jurisdictionCode") == "Baldwin County":
                props["zoningCode"] = None
                props["zoningDistrict"] = None
                props["jurisdictionCode"] = flu["name"]
                stats[f"{flu['name']} cleared county zoning"] += 1
            elif not props.get("jurisdictionCode"):
                props["jurisdictionCode"] = flu["name"]

    for overlay in municipal.get("overlays") or []:
        try:
            rows = _load(overlay, [overlay["nameField"]], fetch_object_ids, fetch_by_ids, geometry=True)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{overlay.get('label') or 'Overlay'} was not joined: {exc}")
            continue
        grid = PolyGrid()
        for row in rows:
            attrs = row.get("attributes") or {}
            name = _clean(attrs.get(overlay["nameField"]))
            geometry = _rings_to_geometry((row.get("geometry") or {}).get("rings"))
            if name and geometry:
                grid.add(geometry, {"name": name})
        for feature in features:
            props = feature["properties"]
            center = _centroid(props)
            if center is None:
                continue
            hits = grid.containing(center[0], center[1])
            if not hits:
                continue
            names = []
            for hit in hits:
                if hit["name"] not in names:
                    names.append(hit["name"])
            props["zoningOverlay"] = "; ".join(names)
            stats["overlay"] += 1
            if is_overlay_label(props.get("zoningCode")):
                props["zoningCode"] = None
                props["zoningDistrict"] = None

    for feature in features:
        feature["properties"].pop("_altIds", None)

    bits = []
    for city in municipal.get("cities") or []:
        name = city["name"]
        if name not in stats:
            continue
        bits.append(
            f"{name} zoning {stats[name]} "
            f"(key {stats.get(f'{name} key', 0)}, spatial {stats.get(f'{name} spatial', 0)})"
        )
    if "county zoning" in stats:
        bits.append(f"Baldwin County Zoning/42 baseline {stats['county zoning']}")
    flu_name = (municipal.get("flu") or {}).get("name")
    if flu_name and stats.get(f"{flu_name} FLU"):
        bits.append(
            f"{flu_name} FLU {stats[f'{flu_name} FLU']} "
            f"(key {stats.get(f'{flu_name} FLU key', 0)}, spatial {stats.get(f'{flu_name} FLU spatial', 0)})"
        )
        cleared = stats.get(f"{flu_name} cleared county zoning", 0)
        if cleared:
            bits.append(f"{flu_name} cleared county Zoning/42 on {cleared} parcels that only matched the city FLU layer")
    if stats.get("overlay"):
        bits.append(
            f"Fairhope AO/MO overlay enrichment {stats['overlay']} parcels; overlay names are not used as zoning codes"
        )
    if bits:
        notes.insert(0, "Municipal join: " + "; ".join(bits) + ".")
    return notes
