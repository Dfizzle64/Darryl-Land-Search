#!/usr/bin/env python3
"""Sumner County, Tennessee (FIPS 47165) 5–150 acre parcels.

Preferred source is Sumner 911 AGOL ParcelsCAMA FeatureServer/0
(PARCEL_TYP=1 and CALC_ACRE 5–150). Comptroller IMPACT (COUNTY_ID=83) and the
stale December 2023 hosted CAMA are siblings only. They are not downloaded.

City zoning is a spatial join. Future land use is joined only where a public
polygon layer exists (Gallatin Community Character, White House CompPlan
Future_LU). Westmoreland, Mitchellville, and unincorporated Sumner have no
public zoning REST. Nomination eligibility is not a designated QOZ and is not
written onto parcels.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from parcel_geometry import esri_rings_to_geojson, representative_point

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path("/tmp/dls-market-parcels")

PARCELS_QUERY = (
    "https://services8.arcgis.com/8jhIZBvwlxdbJdGN/arcgis/rest/services/ParcelsCAMA/FeatureServer/0/query"
)
CITIES_QUERY = (
    "https://services8.arcgis.com/8jhIZBvwlxdbJdGN/arcgis/rest/services/Cities/FeatureServer/0/query"
)
WHERE = "PARCEL_TYP=1 AND CALC_ACRE>=5 AND CALC_ACRE<=150"
SOURCE = "tn-sumner-911-parcels-cama"
VIEWER = "https://tn.sumner.geopowered.com/"
IMPACT_SIBLING = "https://maps.cot.tn.gov/server3/rest/services/IMPACT/Parcels/FeatureServer/0"
STALE_CAMA = "https://maps.cot.tn.gov/hosting/rest/services/Hosted/SUMNER_Dec2023_Parcels_CAMA_A/FeatureServer/0"

PARCEL_FIELDS = [
    "PARID",
    "PARCELID",
    "GISLINK",
    "CITYNUM",
    "ADDRESS",
    "OWNER",
    "OWNER2",
    "MAILADDR",
    "MAILCITY",
    "STATE",
    "ZIP",
    "MAILLINE1",
    "MAILLINE2",
    "SALEDATE",
    "PRICE",
    "APPRAISAL",
    "TAXYR",
    "CALC_ACRE",
    "PARCEL_TYP",
]

# Sumner 911 city NAME -> display name. *_ROBCO is the Robertson-side sliver
# the 911 layer still draws; a Sumner parcel that only hits that sliver keeps
# the city name.
CITY_DISPLAY = {
    "GALLATIN": "Gallatin",
    "HENDERSONVILLE": "Hendersonville",
    "PORTLAND": "Portland",
    "PORTLAND_ROBCO": "Portland",
    "WHITEHOUSE": "White House",
    "MILLERSVILLE": "Millersville",
    "MILLERSVILLE_ROBCO": "Millersville",
    "GOODLETTSVILLE": "Goodlettsville",
    "WESTMORELAND": "Westmoreland",
    "MITCHELLVILLE": "Mitchellville",
}

ZONING_LAYERS = {
    "Gallatin": {
        "url": "https://arcweb.gallatin-tn.gov/arcgis/rest/services/Features/Zoning/FeatureServer/1/query",
        "layer": "https://arcweb.gallatin-tn.gov/arcgis/rest/services/Features/Zoning/FeatureServer/1",
        "fields": ["ZONING"],
        "code": "ZONING",
    },
    "Hendersonville": {
        "url": "https://gis.hvilletn.org/gisapi/rest/services/HvilleTN_Zoning_UPDATED/MapServer/3/query",
        "layer": "https://gis.hvilletn.org/gisapi/rest/services/HvilleTN_Zoning_UPDATED/MapServer/3",
        "fields": ["ZONECODE", "ZONEDES"],
        "code": "ZONECODE",
        "label": "ZONEDES",
        "note": "ZONECODE includes MFR (Multi-Family Residential).",
    },
    "Portland": {
        "url": "https://services2.arcgis.com/T3IV683iYKk0vYAI/arcgis/rest/services/Planimetric_Parcels/FeatureServer/0/query",
        "layer": "https://services2.arcgis.com/T3IV683iYKk0vYAI/arcgis/rest/services/Planimetric_Parcels/FeatureServer/0",
        "fields": ["Zoning_Dis", "Zoning_Lab"],
        "code": "Zoning_Dis",
        "note": "City planimetric annexation polygons. Zoning_Dis includes RM-1 (High Density Residential).",
    },
    "White House": {
        "url": "https://gis.cityofwhitehouse.com/arcgis/rest/services/WhiteHouseTN_Zoning/FeatureServer/3/query",
        "layer": "https://gis.cityofwhitehouse.com/arcgis/rest/services/WhiteHouseTN_Zoning/FeatureServer/3",
        "fields": ["ZONECLASS", "ZONEDESC"],
        "code": "ZONECLASS",
        "label": "ZONEDESC",
        "note": "On-prem WhiteHouseTN_Zoning layer 3. The thinner AGOL ZoningDistricts service is not the overlay.",
    },
    "Millersville": {
        "url": "https://services.arcgis.com/jcrrmnzMsBOEAFJp/arcgis/rest/services/Millersville_Zoning_view/FeatureServer/5/query",
        "layer": "https://services.arcgis.com/jcrrmnzMsBOEAFJp/arcgis/rest/services/Millersville_Zoning_view/FeatureServer/5",
        "fields": ["ZONE_2021"],
        "code": "ZONE_2021",
    },
    "Goodlettsville": {
        "url": "https://services8.arcgis.com/qSbT66zM7qttH0fv/arcgis/rest/services/Zoning_District_2025/FeatureServer/0/query",
        "layer": "https://services8.arcgis.com/qSbT66zM7qttH0fv/arcgis/rest/services/Zoning_District_2025/FeatureServer/0",
        "fields": ["ZONECLASS", "ZONEDESC"],
        "code": "ZONECLASS",
        "label": "ZONEDESC",
        "note": "Goodlettsville AGOL org that also hosts Davidson County parcels. Metro Nashville Zoning MapServer was not used.",
    },
}

FLU_LAYERS = {
    "Gallatin": {
        "url": "https://arcweb.gallatin-tn.gov/arcgis/rest/services/Features/Community_Character/FeatureServer/0/query",
        "layer": "https://arcweb.gallatin-tn.gov/arcgis/rest/services/Features/Community_Character/FeatureServer/0",
        "fields": ["Type"],
        "code": "Type",
        "jurisdiction": "Gallatin",
    },
    "White House": {
        "url": "https://gis.cityofwhitehouse.com/arcgis/rest/services/WhiteHouseTN_CompPlan/FeatureServer/2/query",
        "layer": "https://gis.cityofwhitehouse.com/arcgis/rest/services/WhiteHouseTN_CompPlan/FeatureServer/2",
        "fields": ["Future_LU"],
        "code": "Future_LU",
        "jurisdiction": "White House",
    },
}

FLU_GAP_CITIES = ("Hendersonville", "Portland", "Millersville", "Goodlettsville", "Westmoreland", "Mitchellville")
ZONING_GAP_CITIES = ("Westmoreland", "Mitchellville")
SKIP_ZONE = {"", "UNKNOWN", "DE-ANNEXED", "NA", "N/A", "NONE", "NULL"}

UNINCORP_ZONING_GAP = "No public Sumner County unincorporated zoning REST. The CAMA ZONING attribute is not a municipal district."
CITY_ZONING_GAP = "No public zoning REST for this municipality."
CITY_ZONING_MISS = "Inside city limits, but the city zoning layer did not contain this point."
FLU_GAP = "No public future land use layer for this municipality."
FLU_MISS = "City future land use layer did not contain this point."


def sumner_spec() -> dict:
    return {
        "kind": "sumner",
        "url": PARCELS_QUERY,
        "source": SOURCE,
        "coverage": "complete-gte-5ac",
        "where": WHERE,
        "gaps": [
            "Sumner parcels come from Sumner 911 AGOL ParcelsCAMA, not Comptroller IMPACT.",
        ],
    }


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:  # NaN
        return None
    return parsed


def _zip(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return None


def parse_sale_date(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    if "/" in text:
        parts = text.split("/")
        if len(parts) != 3:
            return None
        month, day, year = parts
        if len(year) == 2:
            year = ("19" if int(year) > 50 else "20") + year
        try:
            y, m, d = int(year), int(month), int(day)
        except ValueError:
            return None
    elif len(text) == 8 and text.isdigit():
        y, m, d = int(text[:4]), int(text[4:6]), int(text[6:8])
    else:
        return None
    if y < 1900 or y > 2100 or not (1 <= m <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


def split_zone(value: Any) -> tuple[str | None, str | None]:
    text = _clean(value)
    if not text:
        return None, None
    if " - " in text:
        code, label = text.split(" - ", 1)
        code, label = code.strip(), label.strip()
        if code.upper() in SKIP_ZONE:
            return None, None
        return code, label or code
    if text.upper() in SKIP_ZONE:
        return None, None
    return text, text


def _inside_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def _inside(x: float, y: float, geometry: dict) -> bool:
    def poly_hit(poly: list) -> bool:
        if not poly or not _inside_ring(x, y, poly[0]):
            return False
        return not any(_inside_ring(x, y, hole) for hole in poly[1:])

    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        return poly_hit(coords)
    if kind == "MultiPolygon":
        return any(poly_hit(poly) for poly in coords)
    return False


def _bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if not node:
            return
        if isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        for child in node:
            walk(child)

    walk(geometry.get("coordinates"))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


class GridIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.overflow: list[dict] = []
        self.items: list[dict] = []

    def add(self, geometry: dict, payload: dict, rank: float) -> None:
        box = _bbox(geometry)
        if not box:
            return
        item = {"geometry": geometry, "payload": payload, "rank": rank, "box": box}
        self.items.append(item)
        x0, y0, x1, y1 = box
        if (x1 - x0) > 1.5 or (y1 - y0) > 1.5:
            self.overflow.append(item)
            return
        for ix in range(int(x0 // self.cell) - 1, int(x1 // self.cell) + 2):
            for iy in range(int(y0 // self.cell) - 1, int(y1 // self.cell) + 2):
                self.buckets[(ix, iy)].append(item)

    def hits(self, x: float, y: float) -> list[dict]:
        key = (int(x // self.cell), int(y // self.cell))
        found = []
        seen: set[int] = set()
        for item in self.buckets.get(key, []):
            seen.add(id(item))
            if _hit(item, x, y):
                found.append(item)
        for item in self.overflow:
            if id(item) in seen:
                continue
            if _hit(item, x, y):
                found.append(item)
        return found


def _hit(item: dict, x: float, y: float) -> bool:
    box = item["box"]
    if x < box[0] or x > box[2] or y < box[1] or y > box[3]:
        return False
    return _inside(x, y, item["geometry"])


def _to_geometry(raw: dict) -> dict | None:
    geom = raw.get("geometry") or {}
    rings = geom.get("rings")
    if not rings:
        return None
    return esri_rings_to_geojson(rings)


def _load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _pull_features(seed: Any, url: str, fields: list[str], where: str = "1=1") -> list[dict]:
    try:
        ids = seed.fetch_object_ids(url, where)
    except Exception as exc:  # noqa: BLE001
        print(f"    id query failed ({exc}); paging {url.split('/rest/')[-1][:80]}", flush=True)
        ids = []
    if ids:
        return seed.fetch_by_ids(url, ids, fields, batch=80)
    features: list[dict] = []
    offset = 0
    while True:
        data = seed.fetch_json(
            url,
            {
                "where": where,
                "outFields": ",".join(fields),
                "returnGeometry": "true",
                "outSR": "4326",
                "resultOffset": str(offset),
                "resultRecordCount": "400",
                "f": "json",
            },
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        batch = data.get("features") or []
        features.extend(batch)
        print(f"    paged {len(features)}", flush=True)
        if not batch or (not data.get("exceededTransferLimit") and len(batch) < 400):
            break
        offset += len(batch)
        if offset > 200000:
            break
    return features


def _index_polygons(raw: list[dict], payload_fn) -> GridIndex:
    index = GridIndex()
    for item in raw:
        geometry = _to_geometry(item)
        if not geometry:
            continue
        payload, rank = payload_fn(item.get("attributes") or {}, geometry)
        if payload is None:
            continue
        index.add(geometry, payload, rank)
    return index


def _zone_payload(spec: dict, attrs: dict, geometry: dict) -> tuple[dict | None, float]:
    code, split_label = split_zone(attrs.get(spec["code"]))
    if not code:
        return None, 0
    label = _clean(attrs.get(spec["label"])) if spec.get("label") else None
    if label and label.upper() in SKIP_ZONE:
        label = None
    district = label or split_label or code
    box = _bbox(geometry)
    rank = (box[2] - box[0]) * (box[3] - box[1]) if box else 1
    return {"code": code, "district": district}, rank


def _flu_payload(spec: dict, attrs: dict, geometry: dict) -> tuple[dict | None, float]:
    code = _clean(attrs.get(spec["code"]))
    if not code or code.upper() in SKIP_ZONE:
        return None, 0
    box = _bbox(geometry)
    rank = (box[2] - box[0]) * (box[3] - box[1]) if box else 1
    return {
        "code": code,
        "label": code,
        "jurisdiction": spec["jurisdiction"],
        "source": spec["layer"],
    }, rank


def _city_payload(attrs: dict, geometry: dict) -> tuple[dict | None, float]:
    raw = _clean(attrs.get("NAME"))
    if not raw:
        return None, 0
    display = CITY_DISPLAY.get(raw.upper(), raw.title())
    box = _bbox(geometry)
    area = (box[2] - box[0]) * (box[3] - box[1]) if box else 1
    # Prefer the Sumner city polygon over a Robertson sliver when both hit.
    rank = (1 if raw.upper().endswith("_ROBCO") else 0, area)
    return {"name": display, "raw": raw.upper()}, rank[0] * 10 + rank[1]


def _feature_gaps(city: str | None, zoned: bool, flu: dict | None) -> list[str]:
    gaps: list[str] = []
    if city is None:
        gaps.append(UNINCORP_ZONING_GAP)
        gaps.append(FLU_GAP)
    elif city in ZONING_GAP_CITIES:
        gaps.append(CITY_ZONING_GAP)
        gaps.append(FLU_GAP)
    else:
        if not zoned:
            gaps.append(CITY_ZONING_MISS)
        if city in FLU_LAYERS:
            if not flu:
                gaps.append(FLU_MISS)
        else:
            gaps.append(FLU_GAP)
    return gaps


def _build_feature(seed: Any, county: dict, markets: list[str], raw: dict, joins: dict) -> dict | None:
    attrs = raw.get("attributes") or {}
    if int(_num(attrs.get("PARCEL_TYP")) or 0) != 1:
        return None
    acres = _num(attrs.get("CALC_ACRE"))
    if not seed.in_band(acres):
        return None
    geometry = _to_geometry(raw)
    if not geometry:
        return None
    center = representative_point(geometry)
    if not center or not (-87.2 < center[0] < -85.7 and 35.9 < center[1] < 36.9):
        return None
    parcel_id = _clean(attrs.get("PARID")) or _clean(attrs.get("GISLINK"))
    if not parcel_id:
        return None
    city_hits = joins["cities"].hits(center[0], center[1])
    city = None
    if city_hits:
        city = min(city_hits, key=lambda item: item["rank"])["payload"]["name"]
    zoning = None
    zone_index = joins["zoning"].get(city) if city else None
    if zone_index is not None:
        hits = zone_index.hits(center[0], center[1])
        if hits:
            zoning = min(hits, key=lambda item: item["rank"])["payload"]
    flu = None
    flu_index = joins["flu"].get(city) if city else None
    if flu_index is not None:
        hits = flu_index.hits(center[0], center[1])
        if hits:
            flu = min(hits, key=lambda item: item["rank"])["payload"]
    price = _num(attrs.get("PRICE"))
    if price is not None and price <= 0:
        price = None
    appraisal = _num(attrs.get("APPRAISAL"))
    if appraisal is not None and appraisal <= 0:
        appraisal = None
    mail1 = _clean(attrs.get("MAILLINE1")) or _clean(attrs.get("MAILADDR"))
    feature = seed.empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=markets,
        parcel_id=parcel_id,
        acreage=acres,
        geometry=geometry,
        center=center,
        source=SOURCE,
        owner=_clean(attrs.get("OWNER")),
        situs=_clean(attrs.get("ADDRESS")),
        city=city,
        zip_code=None,
        zoning=zoning["code"] if zoning else None,
        sale_price=price,
        sale_date=parse_sale_date(attrs.get("SALEDATE")),
        market_value=appraisal,
        mail1=mail1,
        mail2=_clean(attrs.get("MAILLINE2")),
        mail_city=_clean(attrs.get("MAILCITY")),
        mail_state=_clean(attrs.get("STATE")),
        mail_zip=_zip(attrs.get("ZIP")),
    )
    props = feature["properties"]
    props["ownerName2"] = _clean(attrs.get("OWNER2"))
    props["zoningDistrict"] = zoning["district"] if zoning else None
    props["jurisdictionPrefix"] = city
    props["flu"] = flu
    props["appraiserUrl"] = VIEWER
    props["dataGaps"] = _feature_gaps(city, zoning is not None, flu)
    # Eligibility for nomination is not a designated Qualified Opportunity Zone.
    props["opportunityZone"] = None
    props["oz2Eligibility"] = None
    props["taxYear"] = int(_num(attrs.get("TAXYR")) or 0) or None
    return feature


def _prefer(candidate: dict, previous: dict) -> dict:
    cand = candidate["properties"]
    prev = previous["properties"]
    cand_year = cand.get("taxYear") or 0
    prev_year = prev.get("taxYear") or 0
    if cand_year != prev_year:
        return candidate if cand_year > prev_year else previous
    if (cand.get("acreage") or 0) > (prev.get("acreage") or 0):
        return candidate
    return previous


def download_sumner(county: dict, markets: list[str], spec: dict) -> dict:
    import seed_market_parcels as seed

    print(f"Pulling {county['name']} via {SOURCE}", flush=True)
    expected = seed.count_where(PARCELS_QUERY, WHERE)
    print(f"  source rows {expected}", flush=True)
    if expected < 15000 or expected > 22000:
        raise RuntimeError(f"Sumner 5–150 count {expected} is outside the expected ~17.5k band")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    parcel_cache = CACHE_DIR / "47165-parcels-raw.json"
    raw_parcels = _load_json(parcel_cache)
    if not isinstance(raw_parcels, list) or len(raw_parcels) < expected * 0.9:
        print("  downloading ParcelsCAMA", flush=True)
        raw_parcels = _pull_features(seed, PARCELS_QUERY, PARCEL_FIELDS, WHERE)
        parcel_cache.write_text(json.dumps(raw_parcels))
        print(f"  cached {len(raw_parcels)} parcel rows", flush=True)
    else:
        print(f"  parcel cache {len(raw_parcels)}", flush=True)

    joins = _load_joins(seed)
    built: dict[str, dict] = {}
    dropped = 0
    for index, raw in enumerate(raw_parcels, start=1):
        feature = _build_feature(seed, county, markets, raw, joins)
        if feature is None:
            dropped += 1
            continue
        parcel_id = feature["properties"]["parcelId"]
        previous = built.get(parcel_id)
        built[parcel_id] = feature if previous is None else _prefer(feature, previous)
        if index % 4000 == 0:
            print(f"  joined {index}/{len(raw_parcels)}", flush=True)
    features = list(built.values())
    for feature in features:
        feature["properties"].pop("taxYear", None)
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    if len(features) < 15000:
        raise RuntimeError(f"Only {len(features)} Sumner parcels survived geometry and acreage checks")
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Sumner extract emitted a parcel outside 5–150 acres")

    stats = _summarize(features)
    gaps = _county_gaps(stats, len(features))
    path, lookup, tiles = seed.write_tiles(county, features)
    row = seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=SOURCE,
        query_url=PARCELS_QUERY,
        gaps=gaps,
        source_count=expected,
        dropped=dropped,
        tile_count=tiles,
    )
    row["municipalities"] = stats["municipalities"]
    row["unincorporated"] = stats["unincorporated"]
    row["zoningJoinedCount"] = stats["zoned"]
    row["fluJoinedCount"] = stats["flu"]
    row["viewerUrl"] = VIEWER
    row["siblingsNotUsed"] = [
        {"role": "IMPACT fallback", "countyId": 83, "url": IMPACT_SIBLING},
        {"role": "stale Dec-2023 hosted CAMA", "url": STALE_CAMA},
    ]
    county_path = seed.COUNTY_DIR / county["fips"] / "county.json"
    county_path.write_text(json.dumps(row, indent=2) + "\n")
    print(
        f"  kept {len(features)} zoned {stats['zoned']} flu {stats['flu']} dropped {dropped} tiles {tiles}",
        flush=True,
    )
    return row


def _overlay_cache_ok(raw_sets: Any) -> bool:
    if not isinstance(raw_sets, dict):
        return False
    if len(raw_sets.get("cities") or []) < 8:
        return False
    zoning = raw_sets.get("zoning") or {}
    flu = raw_sets.get("flu") or {}
    if any(len(zoning.get(name) or []) < 5 for name in ZONING_LAYERS):
        return False
    if any(len(flu.get(name) or []) < 1 for name in FLU_LAYERS):
        return False
    return True


def _load_joins(seed: Any) -> dict:
    cache_path = CACHE_DIR / "47165-overlays.json"
    cached = _load_json(cache_path)
    raw_sets = cached if _overlay_cache_ok(cached) else {}
    if not raw_sets:
        raw_sets = {"cities": _pull_features(seed, CITIES_QUERY, ["NAME"])}
        print(f"  cities {len(raw_sets['cities'])}", flush=True)
        raw_sets["zoning"] = {}
        for name, spec in ZONING_LAYERS.items():
            print(f"  zoning {name}", flush=True)
            try:
                raw_sets["zoning"][name] = _pull_features(seed, spec["url"], spec["fields"])
            except Exception as exc:  # noqa: BLE001
                print(f"    {name} zoning failed: {exc}", flush=True)
                raw_sets["zoning"][name] = []
            print(f"    {len(raw_sets['zoning'][name])} polygons", flush=True)
        raw_sets["flu"] = {}
        for name, spec in FLU_LAYERS.items():
            print(f"  flu {name}", flush=True)
            try:
                raw_sets["flu"][name] = _pull_features(seed, spec["url"], spec["fields"])
            except Exception as exc:  # noqa: BLE001
                print(f"    {name} FLU failed: {exc}", flush=True)
                raw_sets["flu"][name] = []
            print(f"    {len(raw_sets['flu'][name])} polygons", flush=True)
        cache_path.write_text(json.dumps(raw_sets))

    cities = _index_polygons(raw_sets.get("cities") or [], _city_payload)
    zoning = {
        name: _index_polygons(
            (raw_sets.get("zoning") or {}).get(name) or [],
            lambda attrs, geometry, spec=spec: _zone_payload(spec, attrs, geometry),
        )
        for name, spec in ZONING_LAYERS.items()
    }
    flu = {
        name: _index_polygons(
            (raw_sets.get("flu") or {}).get(name) or [],
            lambda attrs, geometry, spec=spec: _flu_payload(spec, attrs, geometry),
        )
        for name, spec in FLU_LAYERS.items()
    }
    print(
        f"  indexed cities {len(cities.items)} "
        + " ".join(f"{name} z{len(index.items)}" for name, index in zoning.items())
        + " "
        + " ".join(f"{name} f{len(index.items)}" for name, index in flu.items()),
        flush=True,
    )
    return {"cities": cities, "zoning": zoning, "flu": flu}


def _summarize(features: list[dict]) -> dict:
    city_counts: Counter[str] = Counter()
    zone_counts: Counter[str] = Counter()
    flu_counts: Counter[str] = Counter()
    codes: Counter[str] = Counter()
    for feature in features:
        props = feature["properties"]
        city = props.get("jurisdictionPrefix") or "Unincorporated"
        city_counts[city] += 1
        if props.get("zoningCode"):
            zone_counts[city] += 1
            codes[f"{city}:{props['zoningCode']}"] += 1
        flu = props.get("flu") or {}
        if flu.get("code"):
            flu_counts[city] += 1
    municipalities = []
    for name in (
        "Gallatin",
        "Hendersonville",
        "Portland",
        "White House",
        "Millersville",
        "Goodlettsville",
        "Westmoreland",
        "Mitchellville",
    ):
        zoning = ZONING_LAYERS.get(name)
        flu = FLU_LAYERS.get(name)
        municipalities.append(
            {
                "name": name,
                "zoningUrl": zoning["layer"] if zoning else None,
                "fluUrl": flu["layer"] if flu else None,
                "parcels": city_counts[name],
                "zoningJoined": zone_counts[name],
                "fluJoined": flu_counts[name],
                "zoningGap": None if zoning else CITY_ZONING_GAP,
                "fluGap": None if flu else FLU_GAP,
                "note": (zoning or {}).get("note"),
            }
        )
    return {
        "cities": city_counts,
        "zoned": sum(zone_counts.values()),
        "flu": sum(flu_counts.values()),
        "codes": codes,
        "municipalities": municipalities,
        "unincorporated": {
            "parcels": city_counts["Unincorporated"],
            "zoningUrl": None,
            "fluUrl": None,
            "note": UNINCORP_ZONING_GAP,
        },
    }


def _county_gaps(stats: dict, kept: int) -> list[str]:
    city_note = ", ".join(
        f"{name} {count}" for name, count in sorted(stats["cities"].items(), key=lambda item: (-item[1], item[0]))
    )
    mfr = stats["codes"].get("Hendersonville:MFR", 0)
    rm1 = stats["codes"].get("Portland:RM-1", 0)
    return [
        (
            f"Parcels are Sumner 911 AGOL ParcelsCAMA FeatureServer/0 filtered to PARCEL_TYP=1 and CALC_ACRE 5–150 "
            f"({kept} kept). Comptroller IMPACT COUNTY_ID=83 ({IMPACT_SIBLING}) and the stale Dec-2023 hosted CAMA "
            f"({STALE_CAMA}) were not used. Source rows include the same PARID in TAXYR 2026 and 2027. "
            f"One record per PARID is kept, preferring the later tax year."
        ),
        (
            f"Municipal zoning joined on {stats['zoned']} of {kept} parcels. "
            f"Hendersonville MFR parcels: {mfr}. Portland RM-1 parcels: {rm1}. "
            f"City counts: {city_note}. "
            "Westmoreland and Mitchellville have no public zoning REST. "
            "Unincorporated Sumner has no county zoning REST. "
            "The CAMA ZONING field is not used as a district."
        ),
        (
            f"Future land use joined on {stats['flu']} parcels. "
            "Gallatin FLU is Community Character. White House FLU is CompPlan Future_LU. "
            "Hendersonville, Portland, Millersville, Goodlettsville, Westmoreland, Mitchellville, "
            "and unincorporated Sumner have no public FLU layer joined. "
            "Joined FLU codes are not in flu-config.json, so they stay unknown rather than multifamily."
        ),
        (
            "Goodlettsville zoning is Zoning_District_2025 on the city AGOL org that also hosts Davidson County parcels. "
            "Metro Nashville Zoning MapServer was down and was not used. "
            "White House zoning is the city WhiteHouseTN_Zoning FeatureServer layer 3, not the thinner AGOL ZoningDistricts copy. "
            "Portland zoning is planimetric annexation polygons (Zoning_Dis). "
            "Hendersonville zoning is HvilleTN_Zoning_UPDATED MapServer layer 3. "
            "Millersville zoning is Millersville_Zoning_view layer 5 (ZONE_2021)."
        ),
        (
            "Rev. Proc. 2026-14 nomination eligibility is not a designated Qualified Opportunity Zone. "
            "Neither a current QOZ flag nor an eligibility flag is stored on these parcels."
        ),
        (
            "Owner, mailing, situs street, last sale, and total appraisal come from ParcelsCAMA. "
            "A sale price or appraisal of 0 is stored as no value. Situs ZIP is not on this layer and is not copied from the mailing address. "
            f"The public property search is {VIEWER}. Owner phones and emails are not on these layers. "
            "Municipal zoning codes are not an Orange County multifamily knowledge-base match."
        ),
    ]
