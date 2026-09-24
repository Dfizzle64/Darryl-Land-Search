#!/usr/bin/env python3
"""Jacksonville shed parcel extract for the market-parcel tiles.

Wire order: Duval, St. Johns, Clay, Nassau, Baker. Public ArcGIS only.
City zoning/FLU replaces the county layer inside city limits. Gaps stay gaps.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

# west, south, east, north. Padded service extents converted from Web Mercator.
FL_BBOX = (-87.65, 24.40, -79.95, 31.05)
COUNTY_BBOX = {
    "12031": (-82.0795, 30.0739, -81.3508, 30.6158),
    "12109": (-81.6993, 29.5929, -81.1827, 30.2830),
    "12019": (-82.0843, 29.6885, -81.5727, 30.2249),
    "12089": (-82.0854, 30.2434, -81.3945, 30.8626),
    "12003": (-82.4895, 30.1069, -82.0192, 30.6143),
}

SEPARATE_DUVAL = {
    "JACKSONVILLE BEACH": "Jacksonville Beach",
    "ATLANTIC BEACH": "Atlantic Beach",
    "NEPTUNE BEACH": "Neptune Beach",
    "BALDWIN": "Baldwin",
}

APPRAISER = {
    "12031": "https://paopropertysearch.coj.net/",
    "12109": "https://www.sjcpa.gov/",
    "12019": "https://www.ccpao.com/",
    "12089": "https://ncpafl.com/",
    "12003": "https://bakerpa.com/",
}

NASSAU = "https://maps.ncpafl.com/ncflpa_arcgis/rest/services/nassau/NassauCountyPublicTaxMap/MapServer"
BAKER_ORG = "https://services6.arcgis.com/HSWu3dhzHf7nZfIa/arcgis/rest/services"


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def money(value: Any, minimum: float = 1) -> float | None:
    parsed = num(value)
    if parsed is None or parsed < minimum:
        return None
    return parsed


def compact_id(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    return "".join(text.upper().split())


def join_parts(*parts: Any) -> str | None:
    bits = [text for text in (clean(part) for part in parts) if text]
    return " ".join(bits) or None


def in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    west, south, east, north = bbox
    return west <= lon <= east and south <= lat <= north


def in_florida(lon: float, lat: float) -> bool:
    return in_bbox(lon, lat, FL_BBOX)


def in_county(fips: str, lon: float, lat: float) -> bool:
    bbox = COUNTY_BBOX.get(fips)
    return bool(bbox) and in_bbox(lon, lat, bbox) and in_florida(lon, lat)


def separate_duval_city(value: Any) -> str | None:
    text = " ".join(str(value or "").upper().split())
    return SEPARATE_DUVAL.get(text)


def compose_duval_sale(month: Any, day: Any, year: Any) -> str | None:
    parsed_year = num(year)
    if parsed_year is None:
        return None
    y = int(parsed_year)
    if y < 100:
        y += 2000 if y < 70 else 1900
    if y < 1950 or y > 2026:
        return None
    parsed_month = num(month)
    parsed_day = num(day)
    month_num = int(parsed_month) if parsed_month and 1 <= parsed_month <= 12 else 1
    day_num = int(parsed_day) if parsed_day and 1 <= parsed_day <= 31 else 1
    try:
        return date(y, month_num, day_num).isoformat()
    except ValueError:
        return date(y, month_num, 1).isoformat()


def iso_from_any(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                parsed = datetime.strptime(text, fmt).date()
            except ValueError:
                continue
            if 1950 <= parsed.year <= 2026:
                return parsed.isoformat()
        if not re.fullmatch(r"-?\d+(\.\d+)?", text):
            return None
    parsed_num = num(value)
    if parsed_num is None:
        return None
    if 19_500_101 <= parsed_num <= 20_261_231:
        text = f"{int(parsed_num):08d}"
        try:
            parsed = datetime.strptime(text, "%Y%m%d").date()
            if 1950 <= parsed.year <= 2026:
                return parsed.isoformat()
        except ValueError:
            pass
    try:
        if parsed_num > 10_000_000_000_000:
            seconds = parsed_num / 1_000_000
        elif parsed_num > 10_000_000_000:
            seconds = parsed_num / 1000
        elif parsed_num > 10_000_000:
            seconds = parsed_num
        else:
            parsed = (datetime(1899, 12, 30) + timedelta(days=float(parsed_num))).date()
            if 1950 <= parsed.year <= 2026:
                return parsed.isoformat()
            return None
        if not 0 <= seconds <= 4_102_444_800:
            return None
        parsed = datetime.utcfromtimestamp(seconds).date()
    except (OverflowError, OSError, ValueError):
        return None
    if 1950 <= parsed.year <= 2026:
        return parsed.isoformat()
    return None


def split_city_line(value: Any) -> tuple[str | None, str | None, str | None]:
    text = clean(value)
    if not text:
        return None, None, None
    match = re.fullmatch(r"(.+?),\s*([A-Za-z]{2})\s+(\d{5})(?:-\d{4})?", text)
    if not match:
        return text, None, None
    return match.group(1).strip(), match.group(2).upper(), match.group(3)


def flu_info(code: Any, label: Any, jurisdiction: str, source: str) -> dict | None:
    code_text = clean(code)
    label_text = clean(label)
    if not code_text and not label_text:
        return None
    return {
        "code": code_text or label_text,
        "label": label_text or code_text,
        "jurisdiction": jurisdiction,
        "source": source,
    }


def shoelace(ring: list[list[float]]) -> float:
    area = 0.0
    for i in range(len(ring) - 1):
        area += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return area / 2.0


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        yi = ring[i][1]
        yj = ring[j][1]
        if (yi > lat) != (yj > lat):
            xi = ring[i][0]
            xj = ring[j][0]
            denom = yj - yi
            if denom == 0:
                j = i
                continue
            cross = (xj - xi) * (lat - yi) / denom + xi
            if lon < cross:
                inside = not inside
        j = i
    return inside


def group_rings(rings: list) -> list[tuple[list[list[float]], list]]:
    prepared: list[tuple[list[list[float]], float]] = []
    for ring in rings:
        coords = [[float(x), float(y)] for x, y in ring]
        if len(coords) < 4:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        prepared.append((coords, shoelace(coords)))
    if not prepared:
        return []
    _, major = max(prepared, key=lambda item: abs(item[1]))
    exterior_negative = major < 0
    polygons: list[tuple[list[list[float]], list]] = []
    current: tuple[list[list[float]], list] | None = None
    for coords, area in prepared:
        is_exterior = (area < 0) if exterior_negative else (area > 0)
        if current is None or is_exterior:
            current = (coords, [])
            polygons.append(current)
        else:
            current[1].append(coords)
    return polygons


class SpatialIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list] = defaultdict(list)
        self.outside = 0
        self.kept = 0

    def add(self, rings: list, payload: dict) -> None:
        polygons = group_rings(rings)
        if not polygons:
            return
        xs: list[float] = []
        ys: list[float] = []
        for outer, _holes in polygons:
            for x, y in outer:
                xs.append(x)
                ys.append(y)
        bbox = (min(xs), min(ys), max(xs), max(ys))
        if bbox[2] < FL_BBOX[0] or bbox[0] > FL_BBOX[2] or bbox[3] < FL_BBOX[1] or bbox[1] > FL_BBOX[3]:
            self.outside += 1
            return
        area = sum(abs(shoelace(outer)) for outer, _holes in polygons)
        item = (bbox, polygons, payload, area)
        self.kept += 1
        x0 = int(bbox[0] // self.cell)
        x1 = int(bbox[2] // self.cell)
        y0 = int(bbox[1] // self.cell)
        y1 = int(bbox[3] // self.cell)
        for ix in range(x0, x1 + 1):
            for iy in range(y0, y1 + 1):
                self.buckets[(ix, iy)].append(item)

    def query(self, lon: float, lat: float) -> dict | None:
        hits = []
        for item in self.buckets.get((int(lon // self.cell), int(lat // self.cell)), []):
            bbox, polygons, payload, area = item
            if not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
                continue
            if any(point_in_ring(lon, lat, outer) and not any(point_in_ring(lon, lat, hole) for hole in holes) for outer, holes in polygons):
                hits.append((area, payload))
        if not hits:
            return None
        hits.sort(key=lambda row: row[0])
        return hits[0][1]


def add_gap(feature: dict, text: str) -> None:
    gaps = feature["properties"].setdefault("dataGaps", [])
    if text not in gaps:
        gaps.append(text)


def fetch_paged(seed: Any, url: str, where: str, fields: list[str], geometry: bool) -> list[dict]:
    features: list[dict] = []
    seen: set[Any] = set()
    offset = 0
    while offset < 400000:
        data = seed.fetch_json(
            url,
            {
                "where": where,
                "outFields": ",".join(fields),
                "returnGeometry": "true" if geometry else "false",
                "outSR": "4326",
                "resultOffset": str(offset),
                "resultRecordCount": "2000",
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            raise RuntimeError(str(data["error"])[:240])
        batch = data.get("features") or []
        fresh = 0
        for feature in batch:
            attrs = feature.get("attributes") or {}
            oid = attrs.get("OBJECTID", attrs.get("objectid", attrs.get("FID", attrs.get("objectId"))))
            key = oid if oid is not None else (offset, fresh)
            if key in seen:
                continue
            seen.add(key)
            features.append(feature)
            fresh += 1
        if fresh == 0 or not batch:
            break
        offset += len(batch)
        if not data.get("exceededTransferLimit") and len(batch) < 2000:
            break
    return features


def fetch_features(seed: Any, url: str, where: str, fields: list[str], geometry: bool = True) -> list[dict]:
    expected = seed.count_where(url, where)
    if expected <= 0:
        return []
    rows: list[dict] = []
    try:
        rows = fetch_paged(seed, url, where, fields, geometry)
    except Exception as exc:  # noqa: BLE001
        print(f"    paged fetch failed: {exc}", flush=True)
    if len(rows) < expected:
        print(f"    paged {len(rows)}/{expected}; using object ids", flush=True)
        ids = seed.fetch_object_ids(url, where)
        if geometry:
            rows = seed.fetch_by_ids(url, ids, fields)
        else:
            rows = fetch_attrs_by_ids(seed, url, ids, fields)
    print(f"    fetched {len(rows)} from {url.rsplit('/rest/', 1)[-1][:80]}", flush=True)
    return rows


def fetch_attrs_by_ids(seed: Any, url: str, ids: list[int], fields: list[str], batch: int = 200) -> list[dict]:
    features: list[dict] = []
    for start in range(0, len(ids), batch):
        chunk = ids[start : start + batch]
        data = seed.fetch_json(
            url,
            {
                "objectIds": ",".join(str(i) for i in chunk),
                "outFields": ",".join(fields),
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            if len(chunk) > 40:
                features.extend(fetch_attrs_by_ids(seed, url, chunk, fields, batch=max(20, len(chunk) // 2)))
                continue
            raise RuntimeError(str(data["error"])[:240])
        features.extend(data.get("features") or [])
    return features


def fetch_in(seed: Any, url: str, field: str, ids: list[str], fields: list[str]) -> list[dict]:
    found: list[dict] = []
    unique = [item for item in dict.fromkeys(ids) if item]
    step = 50

    def pull(group: list[str]) -> None:
        if not group:
            return
        quoted = ",".join("'" + item.replace("'", "''") + "'" for item in group)
        try:
            data = seed.fetch_json(
                url,
                {
                    "where": f"{field} IN ({quoted})",
                    "outFields": ",".join(fields),
                    "returnGeometry": "false",
                    "f": "json",
                },
                timeout=120,
            )
        except Exception:
            if len(group) > 8:
                mid = len(group) // 2
                pull(group[:mid])
                pull(group[mid:])
                return
            raise
        if data.get("error"):
            if len(group) > 8:
                mid = len(group) // 2
                pull(group[:mid])
                pull(group[mid:])
                return
            raise RuntimeError(str(data["error"])[:240])
        found.extend(data.get("features") or [])

    for start in range(0, len(unique), step):
        pull(unique[start : start + step])
    return found


def index_attrs(features: list[dict], *fields: str) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for feature in features:
        attrs = feature.get("attributes") or {}
        for field in fields:
            key = compact_id(attrs.get(field))
            if key and key not in indexed:
                indexed[key] = attrs
    return indexed


def load_index(seed: Any, url: str, fields: list[str], label: str) -> SpatialIndex:
    print(f"  overlay {label}", flush=True)
    rows = fetch_features(seed, url, "1=1", fields, geometry=True)
    index = SpatialIndex()
    for row in rows:
        rings = (row.get("geometry") or {}).get("rings") or []
        index.add(rings, row.get("attributes") or {})
    if rows and index.outside > index.kept:
        raise RuntimeError(f"{label} geometries fell outside Florida. Refusing to join a bad spatial reference.")
    print(f"    {label}: {index.kept} polygons, {index.outside} outside Florida", flush=True)
    return index


def try_index(seed: Any, url: str, fields: list[str], label: str, gaps: list[str]) -> SpatialIndex | None:
    try:
        return load_index(seed, url, fields, label)
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"{label} overlay failed: {exc}")
        print(f"    gap {label}: {exc}", flush=True)
        return None


def hit(index: SpatialIndex | None, lon: float, lat: float) -> dict | None:
    if index is None:
        return None
    return index.query(lon, lat)


def geometry_feature(seed: Any, item: dict, fips: str) -> tuple[dict | None, float, tuple[float, float] | None]:
    geometry, computed = seed.rings_to_feature_geometry(item.get("geometry"))
    if not geometry:
        return None, computed, None
    center = seed.centroid_of(geometry)
    if not center or not in_county(fips, center[0], center[1]):
        return None, computed, center
    return geometry, computed, center


def remember(by_id: dict[str, dict], feature: dict) -> None:
    parcel_id = feature["properties"]["parcelId"]
    previous = by_id.get(parcel_id)
    if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
        by_id[parcel_id] = feature


def base_feature(seed: Any, county: dict, markets: list[str], **kwargs: Any) -> dict:
    return seed.empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=markets,
        source=kwargs.pop("source"),
        **kwargs,
    )


def pull_duval(seed: Any, county: dict, markets: list[str]) -> tuple[list[dict], list[str], int, int]:
    url = "https://maps.coj.net/coj/rest/services/CityBiz/Parcels/MapServer/0/query"
    fields = [
        "RE",
        "ACRES",
        "LNAMEOWNER",
        "LNAME2",
        "MAILADDR1",
        "MAILADDR2",
        "MAILADDR3",
        "MAILCITY",
        "MAILSTATE",
        "MAILZIP",
        "STREET_NO",
        "ST_DIR",
        "ST_NAME",
        "ST_TYPE",
        "UNIT_NO",
        "ADDRCITY",
        "ZIPCODE",
        "SALESLMM",
        "SALESLDD",
        "SALESLYY",
        "CAMA_VAL",
        "TOT_LND_VA",
        "TOT_BLD_VA",
        "ZON_LABEL",
        "LND_LABEL",
        "PUSE",
    ]
    raw = fetch_features(seed, url, "ACRES>=5 AND ACRES<=150", fields, geometry=True)
    beach = try_index(
        seed,
        "https://services1.arcgis.com/Yd24wKbBcPMKoWvP/arcgis/rest/services/Jacksonville_Beach_Zoning_v1_WFL1/FeatureServer/2/query",
        ["CATEGORY", "Descriptio"],
        "Jacksonville Beach zoning",
        [],
    )
    overlay_gaps: list[str] = []
    if beach is None:
        overlay_gaps.append("Jacksonville Beach zoning overlay failed.")
    by_id: dict[str, dict] = {}
    dropped = 0
    beach_hits = 0
    separate_hits = {"Atlantic Beach": 0, "Neptune Beach": 0, "Baldwin": 0, "Jacksonville Beach": 0}
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed, center = geometry_feature(seed, item, "12031")
        acres = num(attrs.get("ACRES"))
        parcel_id = clean(attrs.get("RE"))
        if not geometry or not center or not parcel_id or not seed.in_band(acres):
            dropped += 1
            continue
        cama = money(attrs.get("CAMA_VAL"), 1000)
        if cama is None:
            land = num(attrs.get("TOT_LND_VA")) or 0
            bldg = num(attrs.get("TOT_BLD_VA")) or 0
            cama = land + bldg if land + bldg >= 1000 else None
        city_name = separate_duval_city(attrs.get("ADDRCITY"))
        zoning = clean(attrs.get("ZON_LABEL"))
        flu = flu_info(attrs.get("LND_LABEL"), attrs.get("LND_LABEL"), "Jacksonville", "coj-parcels-LND_LABEL")
        jurisdiction = "Jacksonville"
        gaps = ["Sale price is not on the CityBiz parcel layer."]
        if city_name in {"Atlantic Beach", "Neptune Beach", "Baldwin"}:
            zoning = None
            flu = None
            jurisdiction = city_name
            gaps.append(f"{city_name} has no public zoning or FLU service. Jacksonville zoning attributes were not used.")
            separate_hits[city_name] += 1
        feature = base_feature(
            seed,
            county,
            markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source="fl-coj-citybiz-parcels-12031",
            owner=clean(attrs.get("LNAMEOWNER")),
            owner2=clean(attrs.get("LNAME2")),
            situs=join_parts(attrs.get("STREET_NO"), attrs.get("ST_DIR"), attrs.get("ST_NAME"), attrs.get("ST_TYPE"), attrs.get("UNIT_NO")),
            city=clean(attrs.get("ADDRCITY")),
            zip_code=seed.zip_str(attrs.get("ZIPCODE")),
            zoning=zoning,
            jurisdiction=jurisdiction,
            dor=clean(attrs.get("PUSE")),
            sale_date=compose_duval_sale(attrs.get("SALESLMM"), attrs.get("SALESLDD"), attrs.get("SALESLYY")),
            market_value=cama,
            mail1=clean(attrs.get("MAILADDR1")),
            mail2=join_parts(attrs.get("MAILADDR2"), attrs.get("MAILADDR3")),
            mail_city=clean(attrs.get("MAILCITY")),
            mail_state=clean(attrs.get("MAILSTATE")),
            mail_zip=seed.zip_str(attrs.get("MAILZIP")),
            flu=flu,
            appraiser_url=APPRAISER["12031"],
            data_gaps=gaps,
        )
        beach_hit = hit(beach, center[0], center[1])
        if beach_hit and city_name not in {"Atlantic Beach", "Neptune Beach", "Baldwin"}:
            feature["properties"]["jurisdictionCode"] = "Jacksonville Beach"
            feature["properties"]["zoningCode"] = clean(beach_hit.get("CATEGORY"))
            feature["properties"]["zoningDistrict"] = clean(beach_hit.get("Descriptio"))
            feature["properties"]["flu"] = None
            add_gap(feature, "Jacksonville Beach has no public FLU service.")
            if not feature["properties"]["zoningCode"]:
                add_gap(feature, "Jacksonville Beach zoning polygon did not include a category.")
            beach_hits += 1
            separate_hits["Jacksonville Beach"] += 1
        elif city_name == "Jacksonville Beach":
            feature["properties"]["jurisdictionCode"] = "Jacksonville Beach"
            feature["properties"]["zoningCode"] = None
            feature["properties"]["flu"] = None
            add_gap(feature, "Situs city is Jacksonville Beach, but the city zoning polygon missed this centroid.")
            add_gap(feature, "Jacksonville Beach has no public FLU service.")
            separate_hits["Jacksonville Beach"] += 1
        remember(by_id, feature)
    gaps = [
        "Sale price is not on CityBiz/Parcels. The property appraiser sales download is the price source and is not joined here.",
        "CAMA_VAL is the market value when it is at least $1,000. Smaller placeholders fall back to land plus building value. Assessed and taxable value are not on this layer.",
        "ZON_LABEL and LND_LABEL are consolidated Jacksonville attributes, not official zoning for Jacksonville Beach, Atlantic Beach, Neptune Beach, or Baldwin.",
        "No public Jacksonville zoning-district service was verified. Paid NLR zoning was not used.",
        f"Jacksonville Beach zoning applied to {beach_hits} parcels.",
        f"Atlantic Beach parcels left without city zoning: {separate_hits['Atlantic Beach']}.",
        f"Neptune Beach parcels left without city zoning: {separate_hits['Neptune Beach']}.",
        f"Baldwin parcels left without city zoning: {separate_hits['Baldwin']}.",
        *overlay_gaps,
    ]
    return list(by_id.values()), gaps, len(raw), dropped


def pull_st_johns(seed: Any, county: dict, markets: list[str]) -> tuple[list[dict], list[str], int, int]:
    url = "https://www.gis.sjcfl.us/portal_sjcgis/rest/services/Hosted/Parcel/FeatureServer/0/query"
    fields = [
        "pin",
        "strap",
        "prp_name",
        "prp_addr",
        "own_addres",
        "own_addr_1",
        "own_addr_2",
        "own_city",
        "own_state",
        "own_zipcod",
        "use_code",
        "use_desc",
        "saledate",
    ]
    where = "SHAPE__Area>=22000 AND SHAPE__Area<=1000000"
    raw = fetch_features(seed, url, where, fields, geometry=True)
    gaps: list[str] = []
    zoning = try_index(seed, "https://www.gis.sjcfl.us/portal_sjcgis/rest/services/Hosted/Zoning/FeatureServer/0/query", ["zoning"], "St. Johns unincorporated zoning", gaps)
    flu = try_index(seed, "https://www.gis.sjcfl.us/portal_sjcgis/rest/services/Hosted/Future_Land_Use/FeatureServer/0/query", ["futluse1"], "St. Johns future land use", gaps)
    limits = try_index(seed, "https://www.gis.sjcfl.us/portal_sjcgis/rest/services/Hosted/City_Limit/FeatureServer/0/query", ["name"], "St. Johns city limits", gaps)
    staug_z = try_index(seed, "https://services.arcgis.com/2HXAtOKdBRSMj8is/arcgis/rest/services/Zoning_Current_View/FeatureServer/0/query", ["ZONECLASS", "ZONEDESC"], "St. Augustine zoning", gaps)
    staug_flu = try_index(seed, "https://services.arcgis.com/2HXAtOKdBRSMj8is/arcgis/rest/services/Land_Use_Current_View/FeatureServer/1/query", ["LANDUSECODE", "LANDUSEDESC", "STRAP"], "St. Augustine future land use", gaps)
    pv = try_index(seed, "https://www.gis.sjcfl.us/portal_sjcgis/rest/services/Hosted/Ponte_Vedra_Zoning_District/FeatureServer/0/query", ["district"], "Ponte Vedra zoning district", gaps)
    sab_index: dict[str, dict] = {}
    try:
        sab_rows = fetch_features(
            seed,
            "https://services1.arcgis.com/t2yugAJW83eUIFui/arcgis/rest/services/St_Augustine_Beach_Zoning_view/FeatureServer/0/query",
            "1=1",
            ["PIN", "STRAP", "Zoning"],
            geometry=False,
        )
        sab_index = index_attrs(sab_rows, "PIN", "STRAP")
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"St. Augustine Beach zoning overlay failed: {exc}")
    by_id: dict[str, dict] = {}
    dropped = 0
    counts = {"staug": 0, "sab": 0, "marineland": 0, "pv": 0}
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, computed, center = geometry_feature(seed, item, "12109")
        parcel_id = clean(attrs.get("pin")) or clean(attrs.get("strap"))
        if not geometry or not center or not parcel_id or not seed.in_band(computed):
            dropped += 1
            continue
        zone_hit = hit(zoning, center[0], center[1])
        flu_hit = hit(flu, center[0], center[1])
        limit_hit = hit(limits, center[0], center[1])
        city = " ".join(str((limit_hit or {}).get("name") or "").upper().split())
        jurisdiction = "St. Johns County"
        zoning_code = clean((zone_hit or {}).get("zoning"))
        zoning_district = None
        flu_value = flu_info((flu_hit or {}).get("futluse1"), (flu_hit or {}).get("futluse1"), "St. Johns County", "sjc-future-land-use")
        parcel_gaps = [
            "Acreage is computed from the parcel polygon. Sale price and tax values are not on the public parcel layer.",
        ]
        if city == "CITY OF ST. AUGUSTINE":
            jurisdiction = "St. Augustine"
            zoning_code = None
            flu_value = None
            city_zone = hit(staug_z, center[0], center[1])
            city_flu = hit(staug_flu, center[0], center[1])
            if city_zone:
                zoning_code = clean(city_zone.get("ZONECLASS"))
                zoning_district = clean(city_zone.get("ZONEDESC"))
            else:
                parcel_gaps.append("Inside St. Augustine, but the city zoning layer missed this centroid.")
            if city_flu:
                flu_value = flu_info(city_flu.get("LANDUSECODE"), city_flu.get("LANDUSEDESC"), "St. Augustine", "staug-land-use")
            else:
                parcel_gaps.append("Inside St. Augustine, but the city future land use layer missed this centroid.")
            counts["staug"] += 1
        elif city == "CITY OF ST. AUGUSTINE BEACH":
            jurisdiction = "St. Augustine Beach"
            zoning_code = None
            matched = sab_index.get(compact_id(attrs.get("pin")) or "") or sab_index.get(compact_id(attrs.get("strap")) or "")
            if matched:
                zoning_code = clean(matched.get("Zoning"))
            else:
                parcel_gaps.append("Inside St. Augustine Beach, but no PIN/STRAP match on the city zoning layer.")
            parcel_gaps.append("St. Augustine Beach has no public FLU service. County future land use was kept and is not city-official.")
            if flu_value:
                flu_value = dict(flu_value)
                flu_value["jurisdiction"] = "St. Johns County"
                flu_value["source"] = "sjc-future-land-use-not-sab-official"
            counts["sab"] += 1
        elif city == "TOWN OF MARINELAND":
            jurisdiction = "Marineland"
            zoning_code = None
            parcel_gaps.append("Marineland has no public zoning or FLU service. County future land use was kept and is not city-official.")
            counts["marineland"] += 1
        else:
            pv_hit = hit(pv, center[0], center[1])
            if pv_hit and clean(pv_hit.get("district")):
                zoning_district = clean(pv_hit.get("district"))
                counts["pv"] += 1
        feature = base_feature(
            seed,
            county,
            markets,
            parcel_id=parcel_id,
            acreage=computed,
            geometry=geometry,
            center=center,
            source="fl-sjc-hosted-parcel-12109",
            owner=clean(attrs.get("prp_name")),
            situs=clean(attrs.get("prp_addr")),
            zoning=zoning_code,
            zoning_district=zoning_district,
            jurisdiction=jurisdiction,
            dor=clean(attrs.get("use_code")) or clean(attrs.get("use_desc")),
            sale_date=iso_from_any(attrs.get("saledate")),
            mail1=clean(attrs.get("own_addres")),
            mail2=join_parts(attrs.get("own_addr_1"), attrs.get("own_addr_2")),
            mail_city=clean(attrs.get("own_city")),
            mail_state=clean(attrs.get("own_state")),
            mail_zip=seed.zip_str(attrs.get("own_zipcod")),
            flu=flu_value,
            appraiser_url=APPRAISER["12109"],
            data_gaps=parcel_gaps,
        )
        remember(by_id, feature)
    gaps.extend(
        [
            "No acreage field on Hosted/Parcel. Acres are computed from WGS84 rings after a Web Mercator SHAPE__Area prefilter.",
            "Sale price and tax values are not on the public parcel layer.",
            "Unincorporated zoning does not cover St. Augustine, St. Augustine Beach, or Marineland.",
            f"St. Augustine parcels in the 5–150 acre band: {counts['staug']}.",
            f"St. Augustine Beach parcels in the 5–150 acre band: {counts['sab']}. St. Augustine Beach FLU is a gap.",
            f"Marineland parcels left without city zoning: {counts['marineland']}.",
            f"Ponte Vedra overlay labeled on {counts['pv']} unincorporated parcels.",
        ]
    )
    return list(by_id.values()), gaps, len(raw), dropped


def pull_clay(seed: Any, county: dict, markets: list[str]) -> tuple[list[dict], list[str], int, int]:
    utility = "https://maps.clayutility.org/server/rest/services/Parcels_LGIM/MapServer/0/query"
    cama = "https://maps.claycountygov.com:6443/arcgis/rest/services/Parcel/MapServer/0/query"
    fields = ["PIN", "GISACRES", "OWNER_NAME", "USECD", "USEDESC", "HOUSE_NO", "STREET", "ST_MD", "ST_DIR", "ST_CITY", "ST_ZIP5"]
    raw = fetch_features(seed, utility, "GISACRES>=5 AND GISACRES<=150", fields, geometry=True)
    pins = [clean((item.get("attributes") or {}).get("PIN")) for item in raw]
    pins = [pin for pin in pins if pin]
    cama_index: dict[str, dict] = {}
    gaps: list[str] = []
    try:
        cama_rows = fetch_in(
            seed,
            cama,
            "PIN",
            pins,
            ["PIN", "Name", "Usedesc", "HouseNo", "StreetName", "StreetMd", "StreetDir", "StreetUnit", "StreetCity", "StreetZip5", "Address1", "Address2", "Address3", "City", "StateProvince", "ZipCode"],
        )
        cama_index = index_attrs(cama_rows, "PIN")
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"Clay county CAMA attribute join failed: {exc}")
    zoning = try_index(seed, "https://maps.claycountygov.com:6443/arcgis/rest/services/Zoning/MapServer/3/query", ["Zoning"], "Clay zoning", gaps)
    flu = try_index(seed, "https://maps.claycountygov.com:6443/arcgis/rest/services/FLUM/MapServer/5/query", ["FLUM"], "Clay future land use", gaps)
    gcs_boundary = try_index(seed, "https://maps.claycountygov.com:6443/arcgis/rest/services/Green_Cove_Springs_Boundary/MapServer/0/query", ["OBJECTID"], "Green Cove Springs boundary", gaps)
    orange = try_index(seed, "https://maps.claycountygov.com:6443/arcgis/rest/services/Orange_Park_Boundary/MapServer/0/query", ["OBJECTID"], "Orange Park boundary", gaps)
    keystone = try_index(seed, "https://maps.claycountygov.com:6443/arcgis/rest/services/Keystone_Heights_Boundary/MapServer/0/query", ["OBJECTID"], "Keystone Heights boundary", gaps)
    penney = try_index(seed, "https://maps.claycountygov.com:6443/arcgis/rest/services/Penney_Farms_Boundary/MapServer/0/query", ["OBJECTID"], "Penney Farms boundary", gaps)
    gcs_zone_index: dict[str, dict] = {}
    gcs_flu_index: dict[str, dict] = {}
    gcs_zone_spatial = None
    gcs_flu_spatial = None
    elu_index: dict[str, dict] = {}
    try:
        gcs_zone_index = index_attrs(
            fetch_features(seed, "https://services2.arcgis.com/R0MaBWycrb80Pvlu/arcgis/rest/services/Zoning/FeatureServer/0/query", "1=1", ["PIN", "ZONING", "USEDESC"], geometry=False),
            "PIN",
        )
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"Green Cove Springs zoning attribute join failed: {exc}")
    try:
        gcs_flu_index = index_attrs(
            fetch_features(seed, "https://services2.arcgis.com/R0MaBWycrb80Pvlu/arcgis/rest/services/GreenCoveSpringsPlanning/FeatureServer/2/query", "1=1", ["PIN", "SMEflu"], geometry=False),
            "PIN",
        )
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"Green Cove Springs future land use attribute join failed: {exc}")
    if not gcs_zone_index:
        gcs_zone_spatial = try_index(seed, "https://services2.arcgis.com/R0MaBWycrb80Pvlu/arcgis/rest/services/Zoning/FeatureServer/0/query", ["PIN", "ZONING", "USEDESC"], "Green Cove Springs zoning", gaps)
    if not gcs_flu_index:
        gcs_flu_spatial = try_index(seed, "https://services2.arcgis.com/R0MaBWycrb80Pvlu/arcgis/rest/services/GreenCoveSpringsPlanning/FeatureServer/2/query", ["PIN", "SMEflu"], "Green Cove Springs future land use", gaps)
    try:
        elu_index = index_attrs(
            fetch_features(
                seed,
                "https://services2.arcgis.com/R0MaBWycrb80Pvlu/arcgis/rest/services/GreenCoveSpringsPlanning/FeatureServer/4/query",
                "1=1",
                ["PIN", "JustValue", "AssdValueN", "TaxableVal", "SaleDate1", "AdjPrice1", "Qual1"],
                geometry=False,
            ),
            "PIN",
        )
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"Green Cove Springs existing-land-use sale/tax join failed: {exc}")
    by_id: dict[str, dict] = {}
    dropped = 0
    counts = {"gcs": 0, "orange": 0, "keystone": 0, "penney": 0, "cama": 0}
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed, center = geometry_feature(seed, item, "12019")
        acres = num(attrs.get("GISACRES"))
        parcel_id = clean(attrs.get("PIN"))
        if not geometry or not center or not parcel_id or not seed.in_band(acres):
            dropped += 1
            continue
        key = compact_id(parcel_id)
        cama_attrs = cama_index.get(key or "")
        if cama_attrs:
            counts["cama"] += 1
        owner = clean((cama_attrs or {}).get("Name")) or clean(attrs.get("OWNER_NAME"))
        situs = join_parts(
            (cama_attrs or {}).get("HouseNo"),
            (cama_attrs or {}).get("StreetName"),
            (cama_attrs or {}).get("StreetMd"),
            (cama_attrs or {}).get("StreetDir"),
            (cama_attrs or {}).get("StreetUnit"),
        ) or join_parts(attrs.get("HOUSE_NO"), attrs.get("STREET"), attrs.get("ST_MD"), attrs.get("ST_DIR"))
        city = clean((cama_attrs or {}).get("StreetCity")) or clean(attrs.get("ST_CITY"))
        zip_code = seed.zip_str((cama_attrs or {}).get("StreetZip5") if cama_attrs else None) or seed.zip_str(attrs.get("ST_ZIP5"))
        dor = clean(attrs.get("USECD")) or clean((cama_attrs or {}).get("Usedesc")) or clean(attrs.get("USEDESC"))
        zone_hit = hit(zoning, center[0], center[1])
        flu_hit = hit(flu, center[0], center[1])
        zoning_code = clean((zone_hit or {}).get("Zoning"))
        flu_value = flu_info((flu_hit or {}).get("FLUM"), (flu_hit or {}).get("FLUM"), "Clay County", "clay-flum")
        jurisdiction = "Clay County"
        parcel_gaps = ["No sale price, sale date, or tax values on the public county parcel layers."]
        gap_city = None
        if hit(orange, center[0], center[1]):
            gap_city = "Orange Park"
        elif hit(keystone, center[0], center[1]):
            gap_city = "Keystone Heights"
        elif hit(penney, center[0], center[1]):
            gap_city = "Penney Farms"
        in_gcs = bool(hit(gcs_boundary, center[0], center[1]) or (key and key in gcs_zone_index))
        if gap_city and not in_gcs:
            zoning_code = None
            flu_value = None
            jurisdiction = gap_city
            parcel_gaps.append(f"{gap_city} has no public zoning or FLU service. County zoning was not used inside the city.")
        if in_gcs:
            jurisdiction = "Green Cove Springs"
            gcs_zone = gcs_zone_index.get(key or "") or hit(gcs_zone_spatial, center[0], center[1]) or {}
            gcs_flu = gcs_flu_index.get(key or "") or hit(gcs_flu_spatial, center[0], center[1]) or {}
            zoning_code = clean(gcs_zone.get("ZONING"))
            flu_value = flu_info(gcs_flu.get("SMEflu"), gcs_flu.get("SMEflu"), "Green Cove Springs", "gcs-planning-flu")
            if not zoning_code:
                parcel_gaps.append("Inside Green Cove Springs, but city zoning did not match this PIN or centroid.")
            if not flu_value:
                parcel_gaps.append("Inside Green Cove Springs, but city future land use did not match this PIN or centroid.")
            elu = elu_index.get(key or "")
            sale_date = iso_from_any((elu or {}).get("SaleDate1")) if elu else None
            sale_price = money((elu or {}).get("AdjPrice1")) if elu else None
            if elu and (sale_date or sale_price or money((elu or {}).get("JustValue"))):
                parcel_gaps = [gap for gap in parcel_gaps if not gap.startswith("No sale price")]
            counts["gcs"] += 1
        else:
            elu = None
            sale_date = None
            sale_price = None
        feature = base_feature(
            seed,
            county,
            markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source="fl-clay-parcels-lgim-12019",
            owner=owner,
            situs=situs,
            city=city,
            zip_code=zip_code,
            zoning=zoning_code,
            jurisdiction=jurisdiction,
            dor=dor,
            sale_date=sale_date,
            sale_price=sale_price,
            sale_qualified=clean((elu or {}).get("Qual1")) if elu else None,
            market_value=money((elu or {}).get("JustValue")) if elu else None,
            assessed=money((elu or {}).get("AssdValueN")) if elu else None,
            taxable=money((elu or {}).get("TaxableVal")) if elu else None,
            mail1=clean((cama_attrs or {}).get("Address1")),
            mail2=join_parts((cama_attrs or {}).get("Address2"), (cama_attrs or {}).get("Address3")),
            mail_city=clean((cama_attrs or {}).get("City")),
            mail_state=clean((cama_attrs or {}).get("StateProvince")),
            mail_zip=seed.zip_str((cama_attrs or {}).get("ZipCode") if cama_attrs else None),
            flu=flu_value,
            appraiser_url=APPRAISER["12019"],
            data_gaps=parcel_gaps,
        )
        remember(by_id, feature)
    # fix keystone/penney counters that I botched in the loop - recount from features
    orange_n = sum(1 for feature in by_id.values() if feature["properties"].get("jurisdictionCode") == "Orange Park")
    keystone_n = sum(1 for feature in by_id.values() if feature["properties"].get("jurisdictionCode") == "Keystone Heights")
    penney_n = sum(1 for feature in by_id.values() if feature["properties"].get("jurisdictionCode") == "Penney Farms")
    gaps.extend(
        [
            "Acreage is GISACRES from the Clay utility parcel layer, joined to county Parcel CAMA attributes on PIN.",
            "County parcel REST has no sale price, sale date, or tax values. Green Cove Springs existing land use supplies those inside the city only.",
            f"County CAMA attributes joined for {counts['cama']} parcels.",
            f"Green Cove Springs zoning applied to {counts['gcs']} parcels.",
            f"Orange Park parcels left without city zoning: {orange_n}.",
            f"Keystone Heights parcels left without city zoning: {keystone_n}.",
            f"Penney Farms parcels left without city zoning: {penney_n}.",
        ]
    )
    return list(by_id.values()), gaps, len(raw), dropped


def pull_nassau(seed: Any, county: dict, markets: list[str]) -> tuple[list[dict], list[str], int, int]:
    url = f"{NASSAU}/144/query"
    fields = [
        "PIN",
        "GISCalculatedAcre",
        "Name",
        "Maddr_1",
        "M_addr_2",
        "Mcity",
        "Mstate",
        "Mzip",
        "Situs_full",
        "Just_val",
        "cap_val_nonSCH",
        "tax_val_nonSCH",
        "parcel_use_cd",
    ]
    raw = fetch_features(seed, url, "GISCalculatedAcre>=5 AND GISCalculatedAcre<=150", fields, geometry=True)
    gaps: list[str] = []
    zoning = try_index(seed, f"{NASSAU}/154/query", ["ZONING", "zoning_description"], "Nassau unincorporated zoning", gaps)
    flu = try_index(seed, f"{NASSAU}/156/query", ["FLUM", "Abb"], "Nassau unincorporated future land use", gaps)
    fb_z = try_index(seed, f"{NASSAU}/297/query", ["ZONING", "zoning_description"], "Fernandina Beach zoning", gaps)
    fb_flu = try_index(seed, f"{NASSAU}/164/query", ["LANDUSE", "FLUM"], "Fernandina Beach future land use", gaps)
    hi_z = try_index(seed, f"{NASSAU}/158/query", ["ZONING", "zoning_description"], "Hilliard zoning", gaps)
    hi_flu = try_index(seed, f"{NASSAU}/159/query", ["Land_Use", "FLUMH"], "Hilliard future land use", gaps)
    callahan = try_index(seed, f"{NASSAU}/299/query", ["LU_", "Zone_Code"], "Callahan future land use", gaps)
    by_id: dict[str, dict] = {}
    dropped = 0
    counts = {"fb": 0, "hilliard": 0, "callahan": 0}
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed, center = geometry_feature(seed, item, "12089")
        acres = num(attrs.get("GISCalculatedAcre"))
        parcel_id = clean(attrs.get("PIN"))
        if not geometry or not center or not parcel_id or not seed.in_band(acres):
            dropped += 1
            continue
        zone_hit = hit(zoning, center[0], center[1])
        flu_hit = hit(flu, center[0], center[1])
        zoning_code = clean((zone_hit or {}).get("ZONING"))
        zoning_district = clean((zone_hit or {}).get("zoning_description"))
        flu_value = flu_info((flu_hit or {}).get("Abb"), (flu_hit or {}).get("FLUM"), "Nassau County", "nassau-unincorp-flu")
        jurisdiction = "Nassau County"
        parcel_gaps = ["Last sale is not on the Nassau land-parcel layer."]
        city_zone = hit(fb_z, center[0], center[1])
        city_flu = hit(fb_flu, center[0], center[1])
        city_name = None
        if city_zone or city_flu:
            city_name = "Fernandina Beach"
            counts["fb"] += 1
        else:
            city_zone = hit(hi_z, center[0], center[1])
            city_flu = hit(hi_flu, center[0], center[1])
            if city_zone or city_flu:
                city_name = "Hilliard"
                counts["hilliard"] += 1
        if city_name == "Fernandina Beach":
            jurisdiction = city_name
            zoning_code = clean((city_zone or {}).get("ZONING"))
            zoning_district = clean((city_zone or {}).get("zoning_description"))
            if city_flu:
                flu_value = flu_info(city_flu.get("LANDUSE"), city_flu.get("FLUM"), city_name, "fernandina-beach-flu")
            else:
                flu_value = None
                parcel_gaps.append("Inside Fernandina Beach zoning, but the city FLU layer missed this centroid.")
            if not zoning_code:
                parcel_gaps.append("Inside Fernandina Beach, but the city zoning layer missed this centroid.")
        elif city_name == "Hilliard":
            jurisdiction = city_name
            zoning_code = clean((city_zone or {}).get("ZONING"))
            zoning_district = clean((city_zone or {}).get("zoning_description"))
            if city_flu:
                flu_value = flu_info(city_flu.get("FLUMH") or city_flu.get("Land_Use"), city_flu.get("Land_Use"), city_name, "hilliard-flu")
            else:
                flu_value = None
            if not zoning_code:
                parcel_gaps.append("Inside Hilliard, but the city zoning layer missed this centroid.")
        else:
            callahan_hit = hit(callahan, center[0], center[1])
            if callahan_hit:
                jurisdiction = "Callahan"
                zoning_code = clean(callahan_hit.get("Zone_Code"))
                zoning_district = None
                flu_value = flu_info(callahan_hit.get("LU_"), callahan_hit.get("LU_"), "Callahan", "callahan-flu")
                parcel_gaps.append("Callahan has no separate zoning layer. Zone_Code is taken from the future land use layer.")
                counts["callahan"] += 1
        feature = base_feature(
            seed,
            county,
            markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source="fl-nassau-taxmap-12089",
            owner=clean(attrs.get("Name")),
            situs=clean(attrs.get("Situs_full")),
            zoning=zoning_code,
            zoning_district=zoning_district,
            jurisdiction=jurisdiction,
            dor=clean(attrs.get("parcel_use_cd")),
            market_value=money(attrs.get("Just_val")),
            assessed=money(attrs.get("cap_val_nonSCH")),
            taxable=money(attrs.get("tax_val_nonSCH")),
            mail1=clean(attrs.get("Maddr_1")),
            mail2=clean(attrs.get("M_addr_2")),
            mail_city=clean(attrs.get("Mcity")),
            mail_state=clean(attrs.get("Mstate")),
            mail_zip=seed.zip_str(attrs.get("Mzip")),
            flu=flu_value,
            appraiser_url=APPRAISER["12089"],
            data_gaps=parcel_gaps,
        )
        remember(by_id, feature)
    if len(raw) > len(by_id):
        gaps.append(
            f"{len(raw)} source rows collapsed to {len(by_id)} parcel ids. Repeated PINs on the tax map were kept once."
        )
    gaps.extend(
        [
            "Last sale is not on MapServer/144. Yearly sales sublayers were not joined.",
            "Assessed and taxable values are the non-school county figures (cap_val_nonSCH and tax_val_nonSCH). School and city columns are not summed.",
            "Unincorporated zoning and FLU are replaced inside Fernandina Beach, Hilliard, and Callahan.",
            f"Fernandina Beach parcels in the 5–150 acre band: {counts['fb']}.",
            f"Hilliard parcels in the 5–150 acre band: {counts['hilliard']}.",
            f"Callahan parcels in the 5–150 acre band: {counts['callahan']}. Callahan has no separate zoning layer.",
        ]
    )
    return list(by_id.values()), gaps, len(raw), dropped


def baker_sales(seed: Any, gaps: list[str]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for name in ("2025_sales", "2024_sales", "24_Sales", "23_Sales"):
        url = f"{BAKER_ORG}/{name}/FeatureServer/0"
        try:
            meta = seed.fetch_json(url, {"f": "json"})
        except Exception as exc:  # noqa: BLE001
            gaps.append(f"Baker {name} was not readable: {exc}")
            continue
        if meta.get("error"):
            message = json.dumps(meta["error"])
            if "Token" in message:
                gaps.append(f"Baker {name} requires a token and was not joined.")
            else:
                gaps.append(f"Baker {name} was not readable: {message[:180]}")
            continue
        names = [field.get("name") for field in meta.get("fields") or []]
        by_name = {item.upper(): item for item in names if item}
        pin = by_name.get("PIN")
        date_field = by_name.get("DATE_OF_SALE") or by_name.get("DATE_OF_SA")
        if date_field is None:
            date_field = next((item for item in names if item and item.lower().endswith("sale_1")), None)
        price_field = by_name.get("SALES_PRICE")
        if price_field is None:
            price_field = next((item for item in names if item and item.lower().endswith("sale_2")), None) or by_name.get("SALES_PRIC")
        qual_field = by_name.get("QUALIFICATION_CODE") or by_name.get("QUALIFICAT")
        if qual_field is None:
            qual_field = next((item for item in names if item and item.lower().endswith("sale_6")), None)
        if not pin or not date_field or not price_field:
            gaps.append(f"Baker {name} field map was not verified, so that sales layer was skipped.")
            continue
        out = [pin, date_field, price_field] + ([qual_field] if qual_field else [])
        try:
            rows = fetch_features(seed, url + "/query", "1=1", out, geometry=False)
        except Exception as exc:  # noqa: BLE001
            gaps.append(f"Baker {name} query failed: {exc}")
            continue
        for row in rows:
            attrs = row.get("attributes") or {}
            key = compact_id(attrs.get(pin))
            sold = iso_from_any(attrs.get(date_field))
            if not key or not sold:
                continue
            current = latest.get(key)
            if current and current["date"] >= sold:
                continue
            latest[key] = {
                "date": sold,
                "price": money(attrs.get(price_field)),
                "qualified": clean(attrs.get(qual_field)) if qual_field else None,
            }
    return latest


def pull_baker(seed: Any, county: dict, markets: list[str]) -> tuple[list[dict], list[str], int, int]:
    url = f"{BAKER_ORG}/parcels_web2/FeatureServer/0/query"
    fields = ["PIN", "PARCELNO", "GIS_Acreag", "Zoning", "cama0827_O", "cama0827_1", "cama0827_M", "cama0827_C", "cama0827_S", "cama0827_4", "cama0827_U", "cama0827_5"]
    raw = fetch_features(seed, url, "GIS_Acreag>=5 AND GIS_Acreag<=150", fields, geometry=True)
    gaps: list[str] = []
    zone_index: dict[str, dict] = {}
    try:
        zone_index = index_attrs(
            fetch_features(seed, f"{BAKER_ORG}/zoning/FeatureServer/0/query", "1=1", ["PIN", "ZONE_CODE"], geometry=False),
            "PIN",
        )
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"Baker zoning attribute join failed: {exc}")
    zone_spatial = None if zone_index else try_index(seed, f"{BAKER_ORG}/zoning/FeatureServer/0/query", ["PIN", "ZONE_CODE"], "Baker zoning", gaps)
    # Most FLU polygons have a blank PARCEL_ID. Join the district polygon spatially.
    flu_spatial = try_index(seed, f"{BAKER_ORG}/FLU/FeatureServer/0/query", ["PARCEL_ID", "FLU"], "Baker future land use", gaps)
    sales = baker_sales(seed, gaps)
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed, center = geometry_feature(seed, item, "12003")
        acres = num(attrs.get("GIS_Acreag"))
        parcel_id = clean(attrs.get("PIN")) or clean(attrs.get("PARCELNO"))
        if not geometry or not center or not parcel_id or not seed.in_band(acres):
            dropped += 1
            continue
        key = compact_id(parcel_id)
        zone_attrs = zone_index.get(key or "") or hit(zone_spatial, center[0], center[1]) or {}
        flu_attrs = hit(flu_spatial, center[0], center[1]) or {}
        mail_city, mail_state, mail_zip = split_city_line(attrs.get("cama0827_C"))
        sale = sales.get(key or "") or sales.get(compact_id(attrs.get("PARCELNO")) or "")
        feature = base_feature(
            seed,
            county,
            markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source="fl-baker-parcels-web2-12003",
            owner=clean(attrs.get("cama0827_O")),
            owner2=clean(attrs.get("cama0827_1")),
            situs=clean(attrs.get("cama0827_S")),
            city=clean(attrs.get("cama0827_4")),
            zoning=clean(zone_attrs.get("ZONE_CODE")) or clean(attrs.get("Zoning")),
            jurisdiction="Baker County",
            dor=clean(attrs.get("cama0827_U")),
            sale_date=(sale or {}).get("date"),
            sale_price=(sale or {}).get("price"),
            sale_qualified=(sale or {}).get("qualified"),
            mail1=clean(attrs.get("cama0827_M")),
            mail_city=mail_city,
            mail_state=mail_state,
            mail_zip=mail_zip,
            flu=flu_info(flu_attrs.get("FLU"), flu_attrs.get("FLU"), "Baker County", "baker-flu"),
            appraiser_url=APPRAISER["12003"],
            data_gaps=["Tax columns on parcels_web2 are unlabeled CAMA fields and were not mapped."],
        )
        remember(by_id, feature)
    zoned = sum(1 for feature in by_id.values() if feature["properties"].get("zoningCode"))
    flued = sum(1 for feature in by_id.values() if feature["properties"].get("flu"))
    sold = sum(1 for feature in by_id.values() if (feature["properties"].get("lastSale") or {}).get("date"))
    gaps.extend(
        [
            "Tax values on parcels_web2 use unlabeled cama0827 columns and were not mapped.",
            "Macclenny and Glen St. Mary have no separate public zoning service. County zoning and FLU are applied countywide.",
            f"Zoning joined on {zoned} of {len(by_id)} parcels.",
            f"FLU joined on {flued} of {len(by_id)} parcels.",
            f"Sales joined on {sold} of {len(by_id)} parcels from the public year sales layers.",
        ]
    )
    return list(by_id.values()), gaps, len(raw), dropped


PULLS = {
    "12031": pull_duval,
    "12109": pull_st_johns,
    "12019": pull_clay,
    "12089": pull_nassau,
    "12003": pull_baker,
}


def pull(seed: Any, county: dict, markets: list[str], spec: dict) -> dict:
    fips = county["fips"]
    cache_path = seed.CACHE_DIR / f"{fips}-jax.json"
    print(f"Pulling {county['name']} {county['state']} ({fips}) via {spec['source']}", flush=True)
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features:
            print(f"  cache hit {len(features)}", flush=True)
            for feature in features:
                feature["properties"]["marketIds"] = markets
            path, lookup, tiles = seed.write_tiles(county, features)
            return seed.county_row(
                county,
                markets,
                feature_count=len(features),
                coverage=spec["coverage"],
                partition="tiles",
                path=path,
                lookup=lookup,
                source=spec["source"],
                query_url=spec["url"],
                gaps=cached.get("gaps") or [],
                source_count=cached.get("sourceCount"),
                dropped=cached.get("dropped"),
                tile_count=tiles,
            )
    fn = PULLS[fips]
    features, gaps, source_count, dropped = fn(seed, county, markets)
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{fips} emitted a parcel outside 5–150 acres")
    if not all(in_county(fips, feature["properties"]["centroid"][0], feature["properties"]["centroid"][1]) for feature in features):
        raise RuntimeError(f"{fips} emitted a centroid outside its Florida county extent")
    features.sort(key=lambda row: row["properties"].get("parcelId") or "")
    seed.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"sourceCount": source_count, "dropped": dropped, "gaps": gaps, "features": features}, separators=(",", ":")))
    coverage = spec["coverage"] if features else "gap"
    if not features:
        gaps.insert(0, "Source rows did not survive the 5–150 acre and Florida extent checks.")
    path, lookup, tiles = (None, None, 0)
    if features:
        path, lookup, tiles = seed.write_tiles(county, features)
    print(f"  kept {len(features)} ({coverage})", flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=coverage,
        partition="tiles" if features else "none",
        path=path,
        lookup=lookup,
        source=spec["source"],
        query_url=spec["url"],
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        tile_count=tiles,
    )
