"""Bartow County, Georgia parcel helpers.

Acreage stays on TOTALACRES. Stacked PARCELID parts are dissolved, not summed.
BartowZoning STZONECODE "Incorporated" is a city stub, not a zoning code.
Sales, FLU, and opportunity-zone fields are left empty on purpose.
"""

from __future__ import annotations

import math
from collections import defaultdict

from parcel_geometry import _inside_polygon, signed_area

# Padded around the live BartowLand extent (2026-09-24). Excludes City of Bartow, FL.
BARTOW_BOUNDS = (-85.08, 34.04, -84.60, 34.45)
CITY_ZONING_STUBS = {"incorporated"}
ZONING_CELL = 0.02


def clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def num(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def compose_situs(number, street, unit) -> str | None:
    """HOUSE_NO + STREET_NAM + UNIT. Blank and zero house numbers are omitted."""
    street_text = clean(street)
    unit_text = clean(unit)
    number_text = None
    parsed = num(number)
    if parsed is not None and parsed > 0:
        number_text = str(int(parsed)) if parsed == int(parsed) else str(parsed)
    elif parsed is None:
        raw = clean(number)
        if raw and raw not in {"0", "0.0"}:
            number_text = raw
    pieces = [part for part in (number_text, street_text) if part]
    line = " ".join(pieces) if pieces else None
    if line and unit_text and unit_text not in {"0", "0.0"}:
        line = f"{line} {unit_text}"
    return line


def positive_money(value) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def in_bartow_bounds(lon: float, lat: float, bounds: tuple[float, float, float, float] = BARTOW_BOUNDS) -> bool:
    west, south, east, north = bounds
    return west <= lon <= east and south <= lat <= north


def is_city_zoning_stub(code: str | None) -> bool:
    text = clean(code)
    return bool(text) and text.lower() in CITY_ZONING_STUBS


def normalize_zoning_code(code: str | None) -> tuple[str | None, str]:
    """Return (stored code, status). Status is joined, stub, or miss.

    Incorporated is counted as a stub and is not stored.
    """
    text = clean(code)
    if not text:
        return None, "miss"
    if text.lower() in CITY_ZONING_STUBS:
        return None, "stub"
    return text, "joined"


def choose_acreage(values: list, *, min_acres: float = 5.0, max_acres: float = 150.0) -> float | None:
    """Parcel-level TOTALACRES. Parts are not added together."""
    counts: dict[float, int] = {}
    for value in values:
        parsed = num(value)
        if parsed is None:
            continue
        key = round(parsed, 4)
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return None
    ranked = sorted(
        counts.items(),
        key=lambda item: (min_acres <= item[0] <= max_acres, item[1], item[0]),
        reverse=True,
    )
    return ranked[0][0]


def pick_attributes(records: list[dict], acres: float | None, acres_field: str, owner_field: str | None) -> dict:
    def score(attrs: dict) -> tuple[int, int]:
        value = num(attrs.get(acres_field)) if acres_field else None
        acre_match = int(value is not None and acres is not None and abs(value - acres) < 0.001)
        owner = 1 if owner_field and clean(attrs.get(owner_field)) else 0
        return acre_match, owner

    return max(records, key=score)


def unique_rings(ring_groups: list) -> tuple[list, int]:
    """Drop stacked copies of the same rings, then concatenate the distinct parts."""
    seen: set[tuple] = set()
    merged: list = []
    distinct = 0
    for rings in ring_groups:
        signature = []
        usable = []
        for ring in rings or []:
            if not ring or len(ring) < 4:
                continue
            signature.append(tuple((round(float(x), 5), round(float(y), 5)) for x, y in ring))
            usable.append(ring)
        if not signature:
            continue
        key = tuple(signature)
        if key in seen:
            continue
        seen.add(key)
        distinct += 1
        merged.extend(usable)
    return merged, distinct


def _esri_polygons(rings: list) -> list:
    polygons: list[list] = []
    current: list = []
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
    return polygons


def _bbox_of_rings(rings: list) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for ring in rings or []:
        for x, y in ring:
            xs.append(float(x))
            ys.append(float(y))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


class ZoningGrid:
    """Cell index of zoning polygons. Representative-point join, not a parcel overlay."""

    def __init__(self, cell: float = ZONING_CELL, bounds: tuple[float, float, float, float] = BARTOW_BOUNDS):
        self.cell = cell
        self.bounds = bounds
        self.items: list[dict] = []
        self.grid: dict[tuple[int, int], list[int]] = defaultdict(list)

    def add(self, code: str | None, rings: list) -> bool:
        text = clean(code)
        if not text or not rings:
            return False
        bbox = _bbox_of_rings(rings)
        if not bbox or not _intersects(bbox, self.bounds):
            return False
        polygons = _esri_polygons(rings)
        if not polygons:
            return False
        area = abs(signed_area(polygons[0][0]))
        index = len(self.items)
        self.items.append({"code": text, "bbox": bbox, "polygons": polygons, "area": area})
        west, south, east, north = bbox
        ix0 = math.floor(west / self.cell)
        ix1 = math.floor(east / self.cell)
        iy0 = math.floor(south / self.cell)
        iy1 = math.floor(north / self.cell)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.grid[(ix, iy)].append(index)
        return True

    def code_at(self, lon: float, lat: float) -> str | None:
        ix = math.floor(lon / self.cell)
        iy = math.floor(lat / self.cell)
        hits = []
        seen: set[int] = set()
        for item_index in self.grid.get((ix, iy), []):
            if item_index in seen:
                continue
            seen.add(item_index)
            item = self.items[item_index]
            west, south, east, north = item["bbox"]
            if lon < west or lon > east or lat < south or lat > north:
                continue
            if any(_inside_polygon(lon, lat, poly) for poly in item["polygons"]):
                hits.append(item)
        if not hits:
            return None
        hits.sort(key=lambda item: (is_city_zoning_stub(item["code"]), item["area"]))
        return hits[0]["code"]


def assign_zoning(features: list[dict], index: ZoningGrid) -> dict:
    joined = stub = missed = 0
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        raw = index.code_at(lon, lat)
        code, status = normalize_zoning_code(raw)
        feature["properties"]["zoningCode"] = code
        feature["properties"]["zoningDistrict"] = None
        if status == "joined":
            joined += 1
        elif status == "stub":
            stub += 1
        else:
            missed += 1
    total = len(features)
    return {"joined": joined, "stub": stub, "missed": missed, "total": total}


def bartow_gaps(*, source_rows: int, kept: int, distinct_parts: int, zoning: dict) -> list[str]:
    total = int(zoning.get("total") or 0)
    joined = int(zoning.get("joined") or 0)
    stub = int(zoning.get("stub") or 0)
    missed = int(zoning.get("missed") or 0)
    rate = (100.0 * joined / total) if total else 0.0
    return [
        (
            f"{source_rows} BartowLand features with TOTALACRES from 5 through 150 inclusive "
            f"dissolved to {kept} PARCELIDs. Acreage is TOTALACRES once per parcel, not the sum of parts. "
            f"{distinct_parts} parcels kept more than one distinct ring group."
        ),
        (
            f"County zoning join: {joined} of {total} parcels ({rate:.1f}%) received a BartowZoning "
            f"STZONECODE other than Incorporated. {stub} parcels fall in the Incorporated city stub and "
            f"have null zoningCode. {missed} parcels did not hit a zoning polygon."
        ),
        (
            "Sales gap: BartowLand has no sale fields. qPublic AppID=791 Sales Search is HTML only and was "
            "not scraped. lastSale price, date, and qualified stay null."
        ),
        (
            "FLU gap: no county-wide public future-land-use REST. The 2018 Future Land Use Map is a PDF "
            "(AGOL item 3c2f76d2227643c392c24600163cfbda). Existing land use was not stored as FLU."
        ),
        (
            "Municipalities are tax-district geography only (Tax_District_Desc on situsCity). City zoning "
            "and city FLU REST are gaps for Cartersville, Adairsville, Emerson, Euharlee, Kingston, White, "
            "and Taylorsville."
        ),
        (
            "Rejected twins: City of Bartow, Florida (Florida SR 2882) and Atlanta Regional Commission "
            "LandPro_2012. Thinner AGOL ParcelInfo/11 and Parcels/12 were not used."
        ),
        (
            "tax.assessedValue and tax.taxableValue are null. tax.marketValue is Total_Taxable_FMV when "
            "it is positive. Opportunity Zone and nomination-eligibility fields are null. Eligible is not designated."
        ),
    ]
