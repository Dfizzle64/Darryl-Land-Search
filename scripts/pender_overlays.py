"""Join public Pender County zoning, future land use, and nomination eligibility.

Parcel geometry comes from Energov MapServer layer 1. Zoning polygons are
LayersPro county UDO layer 36 and the municipal layers that actually exist:
Burgaw 39, St. Helena 40, Surf City 41, Topsail Beach 42, and Watha 43.
Atkinson is on the municipal boundary layer and has no zoning layer.

Imagine Pender 2050 future land use is LayersPro layer 35. Rev. Proc. 2026-14
eligibility is joined only from the local nomination pack and is stored as
eligible-for-nomination. It is not copied onto the designated Opportunity Zone
flag. Notice 2025-50 rural designated tracts stay off that flag.
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from parcel_geometry import signed_area

ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / "data" / "fixtures" / "oz2-eligible-packs.geojson"

ENERGOV_PARCELS = "https://gis.pendercountync.gov/arcgis/rest/services/Energov/MapServer/1/query"
LAYERS = "https://gis.pendercountync.gov/arcgis/rest/services/LayersPro/MapServer"
FLU_LAYER = 35
UDO_LAYER = 36
MUNI_BOUNDARY_LAYER = 9
APPRAISER_URL = "https://mss.pendercountync.gov/css/citizens/RealEstate/Default.aspx?mode=new"
FLU_SOURCE = f"{LAYERS}/{FLU_LAYER}"

# Corporate-limit name -> zoning layer. Atkinson and Wallace are absent on purpose.
MUNI_ZONING = {
    "BURGAW": {"layer": 39, "field": "Zoning_Dis", "prefix": "BUR", "name": "Burgaw"},
    "ST HELENA": {"layer": 40, "field": "ZONING", "prefix": "STH", "name": "St. Helena"},
    "SURF CITY": {"layer": 41, "field": "ZONE", "prefix": "SUR", "name": "Surf City"},
    "TOPSAIL BEACH": {"layer": 42, "field": "ZONING_", "prefix": "TOP", "name": "Topsail Beach"},
    "WATHA": {"layer": 43, "field": "ZONING_", "prefix": "WAT", "name": "Watha"},
}

ATKINSON_GAP = (
    "Town of Atkinson has no public zoning layer. LayersPro municipal zoning is "
    "Burgaw (39), St. Helena (40), Surf City (41), Topsail Beach (42), and Watha (43). "
    "County UDO is not applied inside Atkinson corporate limits."
)
WALLACE_GAP = (
    "Wallace corporate limits have no LayersPro zoning layer. County UDO is not applied inside those limits."
)
ELIGIBLE_TRACTS = ("37141920204", "37141920403")
DESIGNATED_RURAL_NOT_ELIGIBILITY = ("37141920601", "37141920602")

CELL = 0.02
BLANK_CODES = {"", "NONE", "NULL", "INCORP"}


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/pender"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:160]}: {last}")


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def esri_polygons(rings: list) -> list[list[list[list[float]]]]:
    """Group Esri rings into polygons without simplifying. Exterior first, then holes."""
    polygons: list[list[list[list[float]]]] = []
    current: list[list[list[float]]] = []
    for ring in rings or []:
        raw = [[float(pt[0]), float(pt[1])] for pt in ring]
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


def polygon_area(polygons: list[list[list[list[float]]]]) -> float:
    total = 0.0
    for rings in polygons:
        if rings:
            total += abs(signed_area(rings[0]))
    return total


def bbox_of(polygons: list[list[list[list[float]]]]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for rings in polygons:
        for ring in rings:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def contains(x: float, y: float, polygons: list[list[list[list[float]]]]) -> bool:
    for rings in polygons:
        if not rings or not point_in_ring(x, y, rings[0]):
            continue
        if any(point_in_ring(x, y, hole) for hole in rings[1:]):
            continue
        return True
    return False


class GridIndex:
    def __init__(self) -> None:
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.large: list[dict] = []

    def add(self, polygons: list[list[list[list[float]]]], payload: dict) -> None:
        if not polygons:
            return
        item = {
            "polygons": polygons,
            "bbox": bbox_of(polygons),
            "area": polygon_area(polygons),
            "payload": payload,
        }
        minx, miny, maxx, maxy = item["bbox"]
        ix0 = math.floor(minx / CELL)
        iy0 = math.floor(miny / CELL)
        ix1 = math.floor(maxx / CELL)
        iy1 = math.floor(maxy / CELL)
        span = (ix1 - ix0 + 1) * (iy1 - iy0 + 1)
        if span > 2500:
            self.large.append(item)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(item)

    def hits(self, x: float, y: float) -> list[dict]:
        found: list[dict] = []
        ix = math.floor(x / CELL)
        iy = math.floor(y / CELL)
        for item in self.buckets.get((ix, iy), []) + self.large:
            minx, miny, maxx, maxy = item["bbox"]
            if x < minx or x > maxx or y < miny or y > maxy:
                continue
            if contains(x, y, item["polygons"]):
                found.append(item)
        found.sort(key=lambda item: item["area"])
        return found


def clean_code(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in BLANK_CODES:
        return None
    return text


def classify_pender_hit(
    *,
    town: str | None,
    muni_hits: list[dict],
    udo_code: str | None,
    udo_desc: str | None,
    flu_label: str | None,
) -> dict:
    """Pick a zoning code without inventing Atkinson zoning or a multifamily status."""
    town_key = (town or "").upper().strip()
    gaps: list[str] = []
    zoning_code = None
    zoning_district = None
    prefix = None

    usable = [hit for hit in muni_hits if clean_code(hit.get("code"))]
    matched = [hit for hit in usable if town_key and hit.get("town_key") == town_key]
    chosen = None
    if town_key == "ATKINSON":
        gaps.append(ATKINSON_GAP)
    elif town_key == "WALLACE":
        gaps.append(WALLACE_GAP)
    elif matched:
        chosen = matched[0]
    elif not town_key and usable:
        chosen = usable[0]
    elif town_key in MUNI_ZONING:
        name = MUNI_ZONING[town_key]["name"]
        gaps.append(
            f"{name} corporate limits are not covered by that town's LayersPro zoning polygon at this centroid."
        )
    else:
        code = clean_code(udo_code)
        if code:
            zoning_code = code
            zoning_district = (udo_desc or "").strip() or None
            prefix = "PND"
        elif (udo_code or "").strip().upper() == "INCORP" or town_key:
            label = town_key.title() if town_key else "an incorporated area"
            gaps.append(
                f"County UDO marks this centroid incorporated ({label}) and no municipal zoning polygon covers it."
            )

    if chosen:
        zoning_code = clean_code(chosen.get("code"))
        prefix = chosen.get("prefix")
        zoning_district = chosen.get("name")

    flu = None
    label = (flu_label or "").strip()
    if label:
        flu = {
            "code": label,
            "label": label,
            "jurisdiction": "Pender County",
            "source": FLU_SOURCE,
        }

    return {
        "zoningCode": zoning_code,
        "zoningDistrict": zoning_district,
        "jurisdictionPrefix": prefix,
        "jurisdictionCode": prefix,
        "flu": flu,
        "dataGaps": gaps,
    }


def _query_url(layer_id: int) -> str:
    return f"{LAYERS}/{layer_id}/query"


def _load_layer(index: GridIndex, layer_id: int, fields: list[str], payload_of) -> int:
    url = _query_url(layer_id)
    data = fetch_json(url, {"where": "1=1", "returnIdsOnly": "true", "f": "json"})
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    ids = [int(i) for i in (data.get("objectIds") or [])]
    kept = 0
    seen = 0
    batch = 250
    pending = [ids[start : start + batch] for start in range(0, len(ids), batch)]
    while pending:
        piece = pending.pop()
        try:
            page = fetch_json(
                url,
                {
                    "objectIds": ",".join(str(i) for i in piece),
                    "outFields": ",".join(fields),
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "json",
                },
                timeout=180,
            )
        except RuntimeError:
            if len(piece) <= 20:
                raise
            mid = len(piece) // 2
            pending.append(piece[mid:])
            pending.append(piece[:mid])
            continue
        if page.get("error"):
            if len(piece) <= 20:
                raise RuntimeError(json.dumps(page["error"])[:300])
            mid = len(piece) // 2
            pending.append(piece[mid:])
            pending.append(piece[:mid])
            continue
        for feature in page.get("features") or []:
            polygons = esri_polygons((feature.get("geometry") or {}).get("rings") or [])
            payload = payload_of(feature.get("attributes") or {})
            if payload is None or not polygons:
                continue
            index.add(polygons, payload)
            kept += 1
        seen += len(piece)
        if seen == len(ids) or seen % 2000 < len(piece):
            print(f"    layer {layer_id}: {seen}/{len(ids)}", flush=True)
    return kept


def _eligible_tracts() -> list[dict]:
    if not PACK_PATH.exists():
        return []
    collection = json.loads(PACK_PATH.read_text())
    tracts = []
    for feature in collection.get("features") or []:
        props = feature.get("properties") or {}
        if props.get("tractGeoid") not in ELIGIBLE_TRACTS:
            continue
        if props.get("designation") != "eligible-for-nomination":
            raise RuntimeError(f"Pack tract {props.get('tractGeoid')} is not stored as eligible-for-nomination")
        tracts.append(feature)
    return tracts


def _oz2_at(x: float, y: float, tracts: list[dict]) -> dict | None:
    for feature in tracts:
        geometry = feature.get("geometry") or {}
        gtype = geometry.get("type")
        coords = geometry.get("coordinates") or []
        polygons = [coords] if gtype == "Polygon" else coords if gtype == "MultiPolygon" else []
        if not contains(x, y, polygons):
            continue
        props = feature.get("properties") or {}
        return {
            "eligible": True,
            "rural": props.get("rural") is True,
            "tractGeoid": props.get("tractGeoid"),
            "tractName": props.get("name"),
            "designation": "eligible-for-nomination",
        }
    return None


def fetch_flu_by_centroid(points: list[tuple[str, float, float]], workers: int = 8) -> dict[str, str | None]:
    """Layer 35 advertises polygons but its query endpoint returns no rings.

    A centroid intersect still returns CA_FLU_013. One distinct category is kept.
    Overlapping categories are left unknown rather than picked.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    url = _query_url(FLU_LAYER)
    labels: dict[str, str | None] = {}

    def one(item: tuple[str, float, float]) -> tuple[str, str | None]:
        pid, x, y = item
        geom = json.dumps({"x": x, "y": y, "spatialReference": {"wkid": 4326}})
        page = fetch_json(
            url,
            {
                "geometry": geom,
                "geometryType": "esriGeometryPoint",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "where": "1=1",
                "outFields": "CA_FLU_013",
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=60,
            retries=4,
        )
        if page.get("error"):
            raise RuntimeError(json.dumps(page["error"])[:200])
        found: list[str] = []
        for feature in page.get("features") or []:
            label = str((feature.get("attributes") or {}).get("CA_FLU_013") or "").strip()
            if label and label not in found:
                found.append(label)
        if len(found) == 1:
            return pid, found[0]
        return pid, None

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, point) for point in points]
        for future in as_completed(futures):
            pid, label = future.result()
            labels[pid] = label
            done += 1
            if done == len(points) or done % 500 == 0:
                print(f"    Imagine Pender 2050 centroids {done}/{len(points)}", flush=True)
    return labels


def enrich_pender_features(features: list[dict]) -> tuple[list[str], dict]:
    print("  joining LayersPro zoning, Imagine Pender 2050, and nomination tracts", flush=True)
    zoning_index = GridIndex()
    town_index = GridIndex()

    def udo_payload(attrs: dict) -> dict | None:
        return {"kind": "udo", "code": attrs.get("UDO_ZONING"), "desc": attrs.get("DESC_")}

    _load_layer(zoning_index, UDO_LAYER, ["UDO_ZONING", "DESC_"], udo_payload)
    for town_key, spec in MUNI_ZONING.items():
        field = spec["field"]

        def payload_of(attrs: dict, town_key: str = town_key, spec: dict = spec, field: str = field) -> dict | None:
            return {
                "kind": "muni",
                "code": attrs.get(field),
                "prefix": spec["prefix"],
                "name": spec["name"],
                "town_key": town_key,
            }

        _load_layer(zoning_index, spec["layer"], [field], payload_of)

    def town_payload(attrs: dict) -> dict | None:
        name = attrs.get("ALPHA")
        if not isinstance(name, str) or not name.strip():
            return None
        return {"kind": "town", "name": name.strip()}

    _load_layer(town_index, MUNI_BOUNDARY_LAYER, ["ALPHA"], town_payload)
    flu_by_id = fetch_flu_by_centroid(
        [(feature["properties"]["id"], feature["properties"]["centroid"][0], feature["properties"]["centroid"][1]) for feature in features]
    )
    tracts = _eligible_tracts()

    zoning_joined = 0
    flu_joined = 0
    atkinson = 0
    wallace = 0
    oz2_joined = 0
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        town_hits = town_index.hits(lon, lat)
        town = town_hits[0]["payload"]["name"] if town_hits else None
        zone_hits = zoning_index.hits(lon, lat)
        muni_hits = [item["payload"] | {"area": item["area"]} for item in zone_hits if item["payload"].get("kind") == "muni"]
        muni_hits.sort(key=lambda hit: hit.get("area") or 0)
        udo = next((item["payload"] for item in zone_hits if item["payload"].get("kind") == "udo"), None)
        flu_label = flu_by_id.get(props["id"])
        assigned = classify_pender_hit(
            town=town,
            muni_hits=muni_hits,
            udo_code=(udo or {}).get("code"),
            udo_desc=(udo or {}).get("desc"),
            flu_label=flu_label,
        )
        props["zoningCode"] = assigned["zoningCode"]
        props["zoningDistrict"] = assigned["zoningDistrict"]
        props["jurisdictionPrefix"] = assigned["jurisdictionPrefix"]
        props["jurisdictionCode"] = assigned["jurisdictionCode"]
        props["flu"] = assigned["flu"]
        if assigned["dataGaps"]:
            props["dataGaps"] = assigned["dataGaps"]
        else:
            props.pop("dataGaps", None)
        props["appraiserUrl"] = APPRAISER_URL
        # Nomination eligibility is not a designated QOZ. Leave opportunityZone unset.
        props["opportunityZone"] = None
        oz2 = _oz2_at(lon, lat, tracts)
        props["oz2Eligibility"] = oz2
        if assigned["zoningCode"]:
            zoning_joined += 1
        if assigned["flu"]:
            flu_joined += 1
        if town and town.upper().strip() == "ATKINSON":
            atkinson += 1
            if assigned["zoningCode"]:
                raise RuntimeError("Atkinson parcel received a zoning code")
        if town and town.upper().strip() == "WALLACE":
            wallace += 1
            if assigned["zoningCode"]:
                raise RuntimeError("Wallace parcel received a zoning code")
        if oz2:
            if oz2["designation"] != "eligible-for-nomination" or oz2["eligible"] is not True:
                raise RuntimeError("Refusing to store a Pender tract as a designated QOZ")
            if oz2["tractGeoid"] in DESIGNATED_RURAL_NOT_ELIGIBILITY:
                raise RuntimeError("Notice 2025-50 designated tract was copied onto eligibility")
            oz2_joined += 1
        if props.get("opportunityZone"):
            raise RuntimeError("Eligibility join wrote a designated Opportunity Zone")

    gaps = [
        f"{ATKINSON_GAP} {atkinson} parcels in the 5–150 acre extract have a centroid in the Atkinson corporate limit and are left unzoned.",
        (
            "Rev. Proc. 2026-14 eligibility is not a 2027 QOZ designation. "
            f"Centroids in pack tracts {ELIGIBLE_TRACTS[0]} and {ELIGIBLE_TRACTS[1]} "
            f"({oz2_joined} parcels) are stored as eligible-for-nomination only. "
            "opportunityZone is not set from that list. Notice 2025-50 rural designated tracts "
            f"{DESIGNATED_RURAL_NOT_ELIGIBILITY[0]} and {DESIGNATED_RURAL_NOT_ELIGIBILITY[1]} "
            "are current designated QOZs and are not copied onto oz2Eligibility."
        ),
        (
            f"Wallace corporate limits have no LayersPro zoning layer. {wallace} parcels in this "
            "5–150 acre extract have a centroid inside those limits and are left unzoned."
        ),
        f"Joined zoning on {zoning_joined} parcels and Imagine Pender 2050 future land use on {flu_joined} parcels by centroid.",
    ]
    extra = {
        "zoningJoinedCount": zoning_joined,
        "fluJoinedCount": flu_joined,
        "atkinsonUnzonedCount": atkinson,
        "wallaceUnzonedCount": wallace,
        "oz2EligibleCount": oz2_joined,
    }
    print(
        f"  zoning {zoning_joined} flu {flu_joined} atkinson {atkinson} wallace {wallace} oz2 {oz2_joined}",
        flush=True,
    )
    return gaps, extra


def _self_check() -> None:
    atkinson = classify_pender_hit(
        town="ATKINSON",
        muni_hits=[{"code": "R-12", "prefix": "BUR", "name": "Burgaw", "town_key": "BURGAW"}],
        udo_code="RA",
        udo_desc="Rural Agricultural",
        flu_label="Municipal/ETJ",
    )
    assert atkinson["zoningCode"] is None
    assert atkinson["flu"]["code"] == "Municipal/ETJ"
    assert any("Atkinson" in gap for gap in atkinson["dataGaps"])

    burgaw = classify_pender_hit(
        town="Burgaw",
        muni_hits=[{"code": "R-12", "prefix": "BUR", "name": "Burgaw", "town_key": "BURGAW", "area": 1}],
        udo_code="INCORP",
        udo_desc=None,
        flu_label="Residential Neighborhood",
    )
    assert burgaw["zoningCode"] == "R-12"
    assert burgaw["jurisdictionPrefix"] == "BUR"
    assert burgaw["dataGaps"] == []

    county = classify_pender_hit(
        town=None,
        muni_hits=[],
        udo_code="RA",
        udo_desc="Rural Agricultural",
        flu_label="Rural Agricultural",
    )
    assert county["zoningCode"] == "RA"
    assert county["jurisdictionPrefix"] == "PND"

    uncovered = classify_pender_hit(
        town="WATHA",
        muni_hits=[],
        udo_code="RA",
        udo_desc="Rural Agricultural",
        flu_label=None,
    )
    assert uncovered["zoningCode"] is None
    assert uncovered["flu"] is None

    blank = classify_pender_hit(
        town=None,
        muni_hits=[{"code": "None", "prefix": "TOP", "name": "Topsail Beach", "town_key": "TOPSAIL BEACH"}],
        udo_code="INCORP",
        udo_desc=None,
        flu_label=None,
    )
    assert blank["zoningCode"] is None
    print("pender classify self-check ok")


if __name__ == "__main__":
    _self_check()
