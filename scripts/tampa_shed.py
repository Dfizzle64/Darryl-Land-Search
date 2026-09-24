#!/usr/bin/env python3
"""Tampa shed parcel extract: Hillsborough, Pasco, Pinellas, and a Polk upgrade.

Public ArcGIS REST only. Acreage band is 5.0–150.0 inclusive. City zoning and
future land use are joined onto county parcel polygons. Orlando tiles are not
rewritten. Polk market tiles replace the reused DOH extract for Tampa only.

  python3 scripts/seed_tampa_shed.py
  python3 scripts/seed_tampa_shed.py --county Hillsborough
  python3 scripts/seed_tampa_shed.py --refresh
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path("/tmp/dls-tampa-shed")
ORLANDO_POLK_TILES = ROOT / "data" / "fixtures" / "orlando-parcels" / "tiles" / "12105"

PASCO_SUBSET_URL = (
    "https://pascogis.pascocountyfl.net/giswebeserver/rest/services/Hosted/"
    "County_Master_Property_List/FeatureServer/0"
)
LAKELAND_TLS_ZONING_URL = (
    "https://gismims.lakelandgov.net/portal/rest/services/Public/Lakeland10_Zoning/FeatureServer/0"
)
LAKELAND_TLS_FLU_URL = (
    "https://gismims.lakelandgov.net/portal/rest/services/Public/Lakeland10_FutureLandUse/FeatureServer/0"
)
LAKELAND_ZONING_URL = (
    "https://services1.arcgis.com/mcbQY5xNGGGM1vBX/arcgis/rest/services/Zoning/FeatureServer/0"
)
LAKELAND_FLU_URL = (
    "https://services1.arcgis.com/mcbQY5xNGGGM1vBX/arcgis/rest/services/Future_Land_Use/FeatureServer/0"
)
# west, south, east, north. A city overlay must sit inside this box and span less than 1.5°.
FLORIDA_CITY_BBOX = (-87.8, 24.3, -79.7, 31.1)

PASCO_CITY_STUBS = {"NPR", "PR", "SA", "DC", "ZH"}

# Verified from PIN prefix and situs, not from an unverified card note that swaps A and T.
# A- / strap ending A is Tampa. T- is Temple Terrace. P- is Plant City. U- is unincorporated.
HC_MUNI = {
    "U": "Unincorporated Hillsborough",
    "A": "Tampa",
    "P": "Plant City",
    "T": "Temple Terrace",
}

PASCO_MUNI = {
    "UNINCORPORATED PASCO COUNTY": "Unincorporated Pasco",
    "CITY OF NEW PORT RICHEY": "New Port Richey",
    "CITY OF PORT RICHEY": "Port Richey",
    "CITY OF SAN ANTONIO": "San Antonio",
    "CITY OF DADE CITY": "Dade City",
    "CITY OF ZEPHYRHILLS": "Zephyrhills",
    "TOWN OF ST LEO": "St. Leo",
}

PINELLAS_CITY_LABELS = {
    "ST PETERSBURG": "St. Petersburg",
    "CLEARWATER": "Clearwater",
    "LARGO": "Largo",
    "BELLEAIR": "Belleair",
    "BELLEAIR BLUFFS": "Belleair Bluffs",
    "DUNEDIN": "Dunedin",
    "GULFPORT": "Gulfport",
    "INDIAN ROCKS BEACH": "Indian Rocks Beach",
    "INDIAN SHORES": "Indian Shores",
    "KENNETH CITY": "Kenneth City",
    "MADEIRA BEACH": "Madeira Beach",
    "NORTH REDINGTON BEACH": "North Redington Beach",
    "OLDSMAR": "Oldsmar",
    "PINELLAS PARK": "Pinellas Park",
    "SAFETY HARBOR": "Safety Harbor",
    "SEMINOLE": "Seminole",
    "SOUTH PASADENA": "South Pasadena",
    "ST PETE BEACH": "St. Pete Beach",
    "TARPON SPRINGS": "Tarpon Springs",
    "TREASURE ISLAND": "Treasure Island",
    "PALM HARBOR": "Palm Harbor",
    "TIERRA VERDE": "Tierra Verde",
}

# Incorporated Pinellas cities with no verified zoning/FLU FeatureServer.
PINELLAS_GAP_CITIES = {
    "BELLEAIR",
    "BELLEAIR BLUFFS",
    "DUNEDIN",
    "GULFPORT",
    "INDIAN ROCKS BEACH",
    "INDIAN SHORES",
    "KENNETH CITY",
    "MADEIRA BEACH",
    "NORTH REDINGTON BEACH",
    "OLDSMAR",
    "PINELLAS PARK",
    "SAFETY HARBOR",
    "SEMINOLE",
    "SOUTH PASADENA",
    "ST PETE BEACH",
    "TARPON SPRINGS",
    "TREASURE ISLAND",
}

APPRAISER_URLS = {
    "12057": "https://www.hcpafl.org/",
    "12101": "https://www.pascopa.com/",
    "12103": "https://www.pcpao.org/",
    "12105": "https://www.polkpa.org/",
}

HC_GAPS = [
    "Hillsborough sale flag VI is vacant/improved, not an FDOR qualified (Q/U) sale.",
    "Unincorporated zoning is RegulatoryZoning/8. Tampa, Temple Terrace, and Plant City zoning are city layers joined onto county parcels.",
    "Temple Terrace zoning joins on FOLIO. Tampa and Plant City zoning are spatial. Future land use is Planning/4 filtered by JURISDICTION.",
    "MUNI letters were verified from the PIN prefix: A is Tampa, T is Temple Terrace, P is Plant City, U is unincorporated.",
]

PASCO_GAPS = [
    "Pasco parcels are PascoMapper/7 (countywide). Hosted County_Master_Property_List FeatureServer/0 is a ~2,266-feature subset and is not used.",
    "Unincorporated zoning and FLU are Landuse_Planning district polygons. County ZN_TYPE values NPR, PR, SA, DC, and ZH are city placeholders, not districts.",
    "New Port Richey zoning and FLU are the city WFL1 layers, joined on HPARCEL when present and spatially otherwise. Zephyrhills zoning and FLU are the citywide Euclidean layers, joined spatially.",
    "Port Richey, Dade City, San Antonio, and St. Leo have no verified public city zoning/FLU FeatureServer. Parcel attribute strings stay hints.",
]

PINELLAS_GAPS = [
    "Pinellas public parcels have taxable, land, and improvement values but no just/market value.",
    "Unincorporated zoning and FLU are PublicWebGIS Landuse_Zoning and are not applied inside cities.",
    "St. Petersburg and Clearwater have city zoning and FLU. Largo has future land use only. Largo mowing and community-standards layers are not LDC zoning districts.",
    "Dunedin, Pinellas Park, Tarpon Springs, Safety Harbor, and Oldsmar join city zoning and future land use onto county parcels. Pinellas Park uses PARCELID when the city layer has it, then the centroid. Oldsmar's county situs label is wider than the city zoning polygons; parcels outside those polygons stay empty.",
    "Seminole, South Pasadena, Treasure Island, Kenneth City, North Redington Beach, Indian Shores, Belleair, Indian Rocks Beach, Redington Shores, and Madeira Beach use Pinellas County GIS city zoning views. Their city future land use is a gap. The countywide plan map is not stored as a city FLUM.",
    "Gulfport, Belleair Beach, Belleair Bluffs, Redington Beach, and St. Pete Beach have no verified city zoning or future land use layer.",
]

POLK_GAPS = [
    "Polk market parcels are Property_Appraiser MapServer/134. Orlando shed tiles are unchanged.",
    "No countywide zoning-district polygons are published. County FLU 2030 (FLUNAME / FLU_LDC) is land use only and is not stored as zoning.",
    "Property Appraiser parcels have no sale fields. A sale is copied from the FDOR/DOH extract when the parcel id matches.",
    "Lakeland zoning and future land use are city AGOL polygons (LABEL / DESIGNATIO) joined onto county parcels inside the city. Winter Haven has no verified public zoning FeatureServer.",
]


def spec_for_fips(fips: str) -> dict:
    specs = {
        "12057": {
            "kind": "tampa-shed",
            "source": "fl-hillsborough-parcelpublishing-12",
            "url": "https://maps.hillsboroughcounty.org/arcgis1a/rest/services/SDEMapServices/ParcelPublishing/FeatureServer/12/query",
            "coverage": "complete-gte-5ac",
            "gaps": list(HC_GAPS),
        },
        "12101": {
            "kind": "tampa-shed",
            "source": "fl-pasco-pascomapper-7",
            "url": "https://pascogis.pascocountyfl.net/giswebmm/rest/services/PascoMapper/Parcels/MapServer/7/query",
            "coverage": "complete-gte-5ac",
            "gaps": list(PASCO_GAPS),
        },
        "12103": {
            "kind": "tampa-shed",
            "source": "fl-pinellas-publicwebgis-1",
            "url": "https://egis.pinellas.gov/gis/rest/services/PublicWebGIS/Parcels/MapServer/1/query",
            "coverage": "complete-gte-5ac",
            "gaps": list(PINELLAS_GAPS),
        },
        "12105": {
            "kind": "tampa-shed",
            "source": "fl-polk-property-appraiser-134",
            "url": "https://gis.polk-county.net/hosting/rest/services/All-In-One_Viewer/Property_Appraiser/MapServer/134/query",
            "coverage": "complete-gte-5ac",
            "gaps": list(POLK_GAPS),
        },
    }
    if fips not in specs:
        raise KeyError(fips)
    return specs[fips]


def _seed():
    import sys

    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    import seed_market_parcels as seed

    return seed


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    return _seed().fetch_json(url, params, timeout=timeout, retries=retries)


def clean(value: Any) -> str | None:
    return _seed().clean(value)


def num(value: Any) -> float | None:
    return _seed().num(value)


def norm_key(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    return " ".join(text.upper().replace(".", " ").split())


def title_place(value: Any, labels: dict[str, str] | None = None) -> str | None:
    key = norm_key(value)
    if not key:
        return None
    if labels and key in labels:
        return labels[key]
    parts = []
    for word in key.split():
        if word in {"N", "S", "E", "W", "NE", "NW", "SE", "SW", "FL", "US"}:
            parts.append(word)
        else:
            parts.append(word.capitalize())
    return " ".join(parts)


def epoch_to_iso(value: Any) -> str | None:
    text = clean(value)
    if text and len(text) >= 10 and text[4] == "-" and text[:4].isdigit():
        return text[:10]
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    if parsed > 10_000_000_000:
        parsed = parsed / 1000.0
    # Seconds since 1970. Reject years and other small numbers, and far-future millis left unscaled.
    if parsed < 10_000_000 or parsed > 5_000_000_000:
        return None
    try:
        return datetime.fromtimestamp(parsed, timezone.utc).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        return None


def qualified_sale(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    token = text.upper()
    if token in {"V", "I", "VI"}:
        return None
    if len(token) <= 3:
        return token
    return None


def money(value: Any, *, keep_zero: bool = False) -> float | None:
    parsed = num(value)
    if parsed is None:
        return None
    if parsed < 0:
        return None
    if parsed == 0 and not keep_zero:
        return None
    return parsed


def fetch_ids(url: str, where: str) -> list[int]:
    last_error = "no response"
    for attempt in range(6):
        data = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=240)
        if not data.get("error"):
            return [int(item) for item in (data.get("objectIds") or [])]
        last_error = json.dumps(data["error"])[:300]
        print(f"    id query retry {attempt + 1}: {last_error[:160]}", flush=True)
        time.sleep(2.5 * (attempt + 1))
    raise RuntimeError(last_error)


def fetch_chunk(url: str, ids: list[int], fields: list[str], depth: int = 0) -> list[dict]:
    params = {
        "objectIds": ",".join(str(item) for item in ids),
        "outFields": ",".join(fields),
        "returnGeometry": "true",
        "outSR": "4326",
        "geometryPrecision": "5",
        "f": "json",
    }
    data = None
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            data = fetch_json(url, params, timeout=180, retries=3)
            last_error = None
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    if data is None:
        if len(ids) > 6 and depth < 6:
            mid = len(ids) // 2
            return fetch_chunk(url, ids[:mid], fields, depth + 1) + fetch_chunk(url, ids[mid:], fields, depth + 1)
        raise last_error or RuntimeError(f"Failed chunk from {url}")
    if data.get("error"):
        message = json.dumps(data["error"])[:300]
        if len(ids) > 6 and depth < 6:
            mid = len(ids) // 2
            return fetch_chunk(url, ids[:mid], fields, depth + 1) + fetch_chunk(url, ids[mid:], fields, depth + 1)
        if depth < 4:
            time.sleep(2.0 * (depth + 1))
            return fetch_chunk(url, ids, fields, depth + 1)
        raise RuntimeError(message)
    features = data.get("features") or []
    if features:
        geom = features[0].get("geometry") or {}
        ring = (geom.get("rings") or [[]])[0]
        if ring:
            x = float(ring[0][0])
            if abs(x) > 180:
                raise RuntimeError(f"{url} returned coordinates outside WGS84 ({x})")
    return features


def cache_file(key: str, where: str, fields: list[str]) -> Path:
    digest = hashlib.sha1(f"{where}|{','.join(fields)}".encode()).hexdigest()[:10]
    return CACHE_DIR / f"{key}-{digest}.json"


def download_layer(
    key: str,
    url: str,
    where: str,
    fields: list[str],
    *,
    redownload: bool,
    batch: int = 50,
    workers: int = 4,
) -> list[dict]:
    path = cache_file(key, where, fields)
    if path.exists() and not redownload:
        cached = json.loads(path.read_text())
        print(f"  cache {key} {len(cached)}", flush=True)
        return cached
    ids = fetch_ids(url, where)
    print(f"  {key} ids {len(ids)}", flush=True)
    if not ids:
        return []
    chunks = [ids[index : index + batch] for index in range(0, len(ids), batch)]
    features: list[dict] = []
    lock = threading.Lock()
    done = 0

    def run(chunk: list[int]) -> list[dict]:
        return fetch_chunk(url, chunk, fields)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run, chunk) for chunk in chunks]
        for future in as_completed(futures):
            part = future.result()
            with lock:
                features.extend(part)
                done += 1
                if done == 1 or done == len(chunks) or done % 25 == 0:
                    print(f"    {key} {len(features)}/{len(ids)}", flush=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(features, separators=(",", ":")))
    return features


def prepare_rings(geom: dict | None) -> list[list[list[float]]]:
    seed = _seed()
    rings: list[list[list[float]]] = []
    for ring in (geom or {}).get("rings") or []:
        raw = [[float(point[0]), float(point[1])] for point in ring if len(point) >= 2]
        if len(raw) < 4:
            continue
        simple = seed.simplify_ring(raw, 0.00005)
        if len(simple) >= 4:
            rings.append(simple)
    return rings


def ring_bbox(rings: list[list[list[float]]]) -> tuple[float, float, float, float]:
    xs = [point[0] for ring in rings for point in ring]
    ys = [point[1] for ring in rings for point in ring]
    return min(xs), min(ys), max(xs), max(ys)


def ring_area(ring: list[list[float]]) -> float:
    area = 0.0
    for index in range(len(ring) - 1):
        x1, y1 = ring[index]
        x2, y2 = ring[index + 1]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    count = len(ring)
    previous = count - 1
    for index in range(count):
        xi, yi = ring[index]
        xj, yj = ring[previous]
        if (yi > y) != (yj > y):
            denom = yj - yi
            if denom != 0:
                cross = (xj - xi) * (y - yi) / denom + xi
                if x < cross:
                    inside = not inside
        previous = index
    return inside


def point_in_rings(x: float, y: float, rings: list[list[list[float]]]) -> bool:
    inside = False
    for ring in rings:
        if point_in_ring(x, y, ring):
            inside = not inside
    return inside


def geometry_rings(geometry: dict) -> list[list[list[float]]]:
    if geometry.get("type") == "Polygon":
        return geometry.get("coordinates") or []
    rings: list[list[list[float]]] = []
    for polygon in geometry.get("coordinates") or []:
        rings.extend(polygon)
    return rings


def candidate_points(geometry: dict, center: tuple[float, float]) -> list[tuple[float, float]]:
    """Centroid plus a few in-polygon samples. Split-zoned parcels can miss on the centroid alone."""
    points = [center]
    rings = geometry_rings(geometry)
    if not rings:
        return points
    outer = rings[0]
    xs = [point[0] for point in outer]
    ys = [point[1] for point in outer]
    west, east = min(xs), max(xs)
    south, north = min(ys), max(ys)
    if east == west or north == south:
        return points
    for i in range(4):
        for j in range(4):
            x = west + (east - west) * (i + 0.5) / 4
            y = south + (north - south) * (j + 0.5) / 4
            if point_in_rings(x, y, rings):
                points.append((x, y))
            if len(points) >= 5:
                return points
    return points


def first_overlay(index: "SpatialIndex", points: list[tuple[float, float]], accept: Callable[[dict], bool] | None = None) -> dict | None:
    for x, y in points:
        hit = index.hit(x, y, accept=accept)
        if hit:
            return hit
    return None


class SpatialIndex:
    def __init__(self, features: list[dict], attr: Callable[[dict], dict], cell: float = 0.04):
        self.cell = cell
        self.grid: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.overflow: list[dict] = []
        for feature in features:
            rings = prepare_rings(feature.get("geometry"))
            if not rings:
                continue
            west, south, east, north = ring_bbox(rings)
            payload = attr(feature.get("attributes") or {})
            if not payload:
                continue
            item = {
                "rings": rings,
                "bbox": (west, south, east, north),
                "area": ring_area(rings[0]),
                "attr": payload,
            }
            ix0 = math.floor(west / cell)
            ix1 = math.floor(east / cell)
            iy0 = math.floor(south / cell)
            iy1 = math.floor(north / cell)
            cells = (ix1 - ix0 + 1) * (iy1 - iy0 + 1)
            if cells > 80:
                self.overflow.append(item)
                continue
            for ix in range(ix0, ix1 + 1):
                for iy in range(iy0, iy1 + 1):
                    self.grid[(ix, iy)].append(item)

    def hit(self, x: float, y: float, accept: Callable[[dict], bool] | None = None) -> dict | None:
        ix = math.floor(x / self.cell)
        iy = math.floor(y / self.cell)
        candidates = list(self.grid.get((ix, iy), [])) + self.overflow
        found: list[dict] = []
        for item in candidates:
            west, south, east, north = item["bbox"]
            if x < west or x > east or y < south or y > north:
                continue
            if not point_in_rings(x, y, item["rings"]):
                continue
            if accept and not accept(item["attr"]):
                continue
            found.append(item)
        if not found:
            return None
        found.sort(key=lambda item: item["area"])
        return found[0]["attr"]


def load_polk_fdor() -> dict[str, dict]:
    found: dict[str, dict] = {}
    if not ORLANDO_POLK_TILES.exists():
        return found
    for path in ORLANDO_POLK_TILES.glob("*.geojson"):
        data = json.loads(path.read_text())
        for feature in data.get("features") or []:
            props = feature.get("properties") or {}
            parcel_id = props.get("parcelId")
            if parcel_id:
                found[str(parcel_id)] = props
    return found


def verify_florida_polygon(url: str) -> str | None:
    """Return a gap note when the layer is not a small polygon service inside Florida."""
    try:
        headers = {"User-Agent": "darryl-land-search/tampa-shed"}
        meta_req = urllib.request.Request(url + "?" + urllib.parse.urlencode({"f": "json"}), headers=headers)
        with urllib.request.urlopen(meta_req, timeout=30) as resp:
            meta = json.loads(resp.read().decode("utf-8"))
        if meta.get("error") or "Polygon" not in str(meta.get("geometryType") or ""):
            return f"{url} did not return a polygon layer and was not joined."
        extent_req = urllib.request.Request(
            url
            + "/query?"
            + urllib.parse.urlencode(
                {"where": "1=1", "returnExtentOnly": "true", "outSR": "4326", "f": "json"}
            ),
            headers=headers,
        )
        with urllib.request.urlopen(extent_req, timeout=30) as resp:
            extent = (json.loads(resp.read().decode("utf-8")).get("extent") or {})
        west, south, east, north = (float(extent[key]) for key in ("xmin", "ymin", "xmax", "ymax"))
        box_west, box_south, box_east, box_north = FLORIDA_CITY_BBOX
        outside = (
            west < box_west
            or south < box_south
            or east > box_east
            or north > box_north
            or east - west > 1.5
            or north - south > 1.5
            or east <= west
            or north <= south
        )
        if outside:
            return (
                f"{url} extent is outside the Florida city box "
                f"({west:.3f},{south:.3f},{east:.3f},{north:.3f}) and was not joined."
            )
        count_req = urllib.request.Request(
            url + "/query?" + urllib.parse.urlencode({"where": "1=1", "returnCountOnly": "true", "f": "json"}),
            headers=headers,
        )
        with urllib.request.urlopen(count_req, timeout=30) as resp:
            count = int(json.loads(resp.read().decode("utf-8")).get("count") or 0)
        if count < 50 or count > 8000:
            return f"{url} feature count {count} is not a city overlay and was not joined."
        return None
    except Exception as exc:  # noqa: BLE001
        return f"{url} failed verification ({exc.__class__.__name__}) and was not joined."


def compose(
    *,
    county: dict,
    markets: list[str],
    source: str,
    parcel_id: str,
    acreage: float,
    geometry: dict,
    center: tuple[float, float],
    owner: str | None = None,
    owner2: str | None = None,
    situs: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
    dor: str | None = None,
    sale_price: float | None = None,
    sale_date: str | None = None,
    sale_qualified: str | None = None,
    market_value: float | None = None,
    assessed: float | None = None,
    taxable: float | None = None,
    mail1: str | None = None,
    mail2: str | None = None,
    mail_city: str | None = None,
    mail_state: str | None = None,
    mail_zip: str | None = None,
    municipality: str | None = None,
    jurisdiction_code: str | None = None,
    zoning_code: str | None = None,
    zoning_description: str | None = None,
    flu: dict | None = None,
    data_gaps: list[str] | None = None,
    extra: dict | None = None,
) -> dict:
    seed = _seed()
    feature = seed.empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=markets,
        parcel_id=parcel_id,
        acreage=acreage,
        geometry=geometry,
        center=center,
        source=source,
        owner=owner,
        situs=situs,
        city=city,
        zip_code=zip_code,
        zoning=zoning_code,
        dor=dor,
        sale_price=sale_price,
        sale_date=sale_date,
        sale_qualified=sale_qualified,
        market_value=market_value,
        assessed=assessed,
        taxable=taxable,
        mail1=mail1,
        mail2=mail2,
        mail_city=mail_city,
        mail_state=mail_state,
        mail_zip=mail_zip,
    )
    props = feature["properties"]
    props["ownerName2"] = owner2
    props["municipality"] = municipality
    props["jurisdictionCode"] = jurisdiction_code
    props["zoningDistrict"] = zoning_code
    props["zoningDescription"] = zoning_description
    props["flu"] = flu
    props["appraiserUrl"] = APPRAISER_URLS[county["fips"]]
    props["dataGaps"] = data_gaps or []
    if extra:
        props.update(extra)
    return feature


def geometry_of(raw: dict, county: dict) -> tuple[dict, tuple[float, float], float] | None:
    seed = _seed()
    geometry, _computed = seed.rings_to_feature_geometry(raw.get("geometry"))
    if not geometry:
        return None
    center = seed.centroid_of(geometry)
    if not seed.plausible_centroid(center):
        return None
    return geometry, center, 0.0  # type: ignore[return-value]


def finish_features(raw_features: list[dict]) -> list[dict]:
    seed = _seed()
    by_id: dict[str, dict] = {}
    for feature in raw_features:
        parcel_id = feature["properties"]["parcelId"]
        if not seed.in_band(feature["properties"].get("acreage")):
            continue
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features


def write_county(
    county: dict,
    markets: list[str],
    spec: dict,
    features: list[dict],
    *,
    source_count: int,
    dropped: int,
    zoning_joined: int,
    flu_joined: int,
    municipality_counts: dict[str, int],
    gaps: list[str],
    overlays: list[dict],
    rejected: list[str],
) -> dict:
    seed = _seed()
    path, lookup, tiles = seed.write_tiles(county, features)
    row = seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=spec["coverage"],
        partition="tiles",
        path=path,
        lookup=lookup,
        source=spec["source"],
        query_url=spec["url"],
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        tile_count=tiles,
    )
    row["zoningJoinedCount"] = zoning_joined
    row["fluJoinedCount"] = flu_joined
    row["municipalityCounts"] = municipality_counts
    row["overlays"] = overlays
    row["rejected"] = rejected
    target = seed.COUNTY_DIR / county["fips"] / "county.json"
    target.write_text(json.dumps(row, indent=2) + "\n")
    return row


def tally(features: list[dict]) -> tuple[int, int, dict[str, int]]:
    zoning = 0
    flu = 0
    munis: dict[str, int] = defaultdict(int)
    for feature in features:
        props = feature["properties"]
        if props.get("zoningCode"):
            zoning += 1
        if (props.get("flu") or {}).get("code"):
            flu += 1
        label = props.get("municipality") or "Unknown"
        munis[label] += 1
    return zoning, flu, dict(sorted(munis.items(), key=lambda item: (-item[1], item[0])))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def build_hillsborough(county: dict, markets: list[str], spec: dict, redownload: bool) -> dict:
    parcel_url = spec["url"]
    parcels = download_layer(
        "12057-parcels",
        parcel_url,
        "ACREAGE >= 5 AND ACREAGE <= 150",
        [
            "FOLIO",
            "PIN",
            "STRAP",
            "ACREAGE",
            "OWNER",
            "ADDR_1",
            "ADDR_2",
            "CITY",
            "STATE",
            "ZIP",
            "SITE_ADDR",
            "SITE_CITY",
            "SITE_ZIP",
            "S_AMT",
            "S_DATE",
            "VI",
            "JUST",
            "MARKET_VAL",
            "ASD_VAL",
            "TAX_VAL",
            "DOR_CODE",
            "MUNI",
        ],
        redownload=redownload,
        batch=40,
    )
    zoning = download_layer(
        "12057-zoning",
        "https://maps.hillsboroughcounty.org/arcgis1a/rest/services/SDEMapServices/RegulatoryZoning/FeatureServer/8/query",
        "1=1",
        ["NZONE", "NZONE_DESC"],
        redownload=redownload,
        batch=40,
    )
    flu = download_layer(
        "12057-flu",
        "https://maps.hillsboroughcounty.org/arcgis1a/rest/services/SDEMapServices/Planning/FeatureServer/4/query",
        "1=1",
        ["FLUE", "FLU_DESC", "JURISDICTION"],
        redownload=redownload,
        batch=40,
    )
    tampa = download_layer(
        "12057-tampa-zoning",
        "https://arcgis.tampagov.net/arcgis/rest/services/OpenData/Planning/MapServer/28/query",
        "1=1",
        ["ZONECLASS", "ZONEDESC"],
        redownload=redownload,
        batch=40,
    )
    temple = download_layer(
        "12057-tt-zoning",
        "https://gis.tpcmaps.org/arcgis/rest/services/Rezoning/Zoning/MapServer/0/query",
        "1=1",
        ["FOLIO", "ZONING", "LABEL"],
        redownload=redownload,
        batch=40,
    )
    plant = download_layer(
        "12057-pc-zoning",
        "https://gis.tpcmaps.org/arcgis/rest/services/Rezoning/Zoning/MapServer/2/query",
        "1=1",
        ["PCZONING"],
        redownload=redownload,
        batch=40,
    )
    print("  indexing Hillsborough overlays", flush=True)
    county_zoning = SpatialIndex(
        zoning,
        lambda attrs: {"code": clean(attrs.get("NZONE")), "desc": clean(attrs.get("NZONE_DESC")), "source": "hillsborough-regulatory-zoning"}
        if clean(attrs.get("NZONE"))
        else {},
    )
    flu_index = SpatialIndex(
        flu,
        lambda attrs: {
            "code": clean(attrs.get("FLUE")),
            "label": clean(attrs.get("FLU_DESC")),
            "jurisdiction": clean(attrs.get("JURISDICTION")),
            "source": "hillsborough-planning-flu",
        }
        if clean(attrs.get("FLUE"))
        else {},
    )
    tampa_index = SpatialIndex(
        tampa,
        lambda attrs: {"code": clean(attrs.get("ZONECLASS")), "desc": clean(attrs.get("ZONEDESC")), "source": "tampa-zoning"}
        if clean(attrs.get("ZONECLASS"))
        else {},
    )
    temple_index = SpatialIndex(
        temple,
        lambda attrs: {"code": clean(attrs.get("ZONING")), "desc": clean(attrs.get("LABEL")), "source": "temple-terrace-zoning"}
        if clean(attrs.get("ZONING"))
        else {},
    )
    plant_index = SpatialIndex(
        plant,
        lambda attrs: {"code": clean(attrs.get("PCZONING")), "desc": None, "source": "plant-city-zoning"}
        if clean(attrs.get("PCZONING"))
        else {},
    )
    temple_by_folio: dict[str, dict] = {}
    for feature in temple:
        attrs = feature.get("attributes") or {}
        folio = clean(attrs.get("FOLIO"))
        code = clean(attrs.get("ZONING"))
        if folio and code:
            temple_by_folio[folio] = {"code": code, "desc": clean(attrs.get("LABEL")), "source": "temple-terrace-zoning"}

    seed = _seed()
    built: list[dict] = []
    dropped = 0
    for raw in parcels:
        attrs = raw.get("attributes") or {}
        parsed = geometry_of(raw, county)
        acres = num(attrs.get("ACREAGE"))
        if not parsed or not seed.in_band(acres):
            dropped += 1
            continue
        geometry, center, _unused = parsed
        parcel_id = clean(attrs.get("FOLIO")) or clean(attrs.get("PIN")) or clean(attrs.get("STRAP"))
        if not parcel_id:
            dropped += 1
            continue
        muni_code = (clean(attrs.get("MUNI")) or "").upper() or None
        municipality = HC_MUNI.get(muni_code or "")
        points = candidate_points(geometry, center)
        zone = None
        flu_hit = None
        expected_flu = None
        if muni_code == "A":
            zone = first_overlay(tampa_index, points)
            expected_flu = "TAMPA"
        elif muni_code == "T":
            zone = temple_by_folio.get(parcel_id) or first_overlay(temple_index, points)
            expected_flu = "TEMPLE TERRACE"
        elif muni_code == "P":
            zone = first_overlay(plant_index, points)
            expected_flu = "PLANT CITY"
        elif muni_code == "U":
            zone = first_overlay(county_zoning, points)
            expected_flu = "HILLSBOROUGH COUNTY"
        else:
            for index, label, flu_name in (
                (tampa_index, "Tampa", "TAMPA"),
                (temple_index, "Temple Terrace", "TEMPLE TERRACE"),
                (plant_index, "Plant City", "PLANT CITY"),
                (county_zoning, "Unincorporated Hillsborough", "HILLSBOROUGH COUNTY"),
            ):
                candidate = first_overlay(index, points)
                if candidate:
                    zone = candidate
                    municipality = label
                    expected_flu = flu_name
                    break
        if expected_flu:
            flu_hit = first_overlay(
                flu_index,
                points,
                accept=lambda attr, name=expected_flu: (attr.get("jurisdiction") or "").upper() == name,
            )
        gaps = list(HC_GAPS)
        if zone is None:
            gaps.append("Zoning polygon did not intersect this parcel.")
        flu_payload = None
        if flu_hit and flu_hit.get("code"):
            flu_payload = {
                "code": flu_hit["code"],
                "label": flu_hit.get("label") or flu_hit["code"],
                "jurisdiction": municipality,
                "source": flu_hit.get("source"),
            }
        else:
            gaps.append("Future land use polygon for this jurisdiction did not intersect this parcel.")
        built.append(
            compose(
                county=county,
                markets=markets,
                source=spec["source"],
                parcel_id=parcel_id,
                acreage=acres or 0,
                geometry=geometry,
                center=center,
                owner=clean(attrs.get("OWNER")),
                situs=clean(attrs.get("SITE_ADDR")),
                city=title_place(attrs.get("SITE_CITY")),
                zip_code=seed.zip_str(attrs.get("SITE_ZIP")),
                dor=clean(attrs.get("DOR_CODE")),
                sale_price=money(attrs.get("S_AMT")),
                sale_date=epoch_to_iso(attrs.get("S_DATE")),
                sale_qualified=None,
                market_value=money(attrs.get("JUST")) or money(attrs.get("MARKET_VAL")),
                assessed=money(attrs.get("ASD_VAL"), keep_zero=True),
                taxable=money(attrs.get("TAX_VAL"), keep_zero=True),
                mail1=clean(attrs.get("ADDR_1")),
                mail2=clean(attrs.get("ADDR_2")),
                mail_city=title_place(attrs.get("CITY")),
                mail_state=clean(attrs.get("STATE")),
                mail_zip=seed.zip_str(attrs.get("ZIP")),
                municipality=municipality,
                jurisdiction_code=muni_code if muni_code in HC_MUNI else None,
                zoning_code=(zone or {}).get("code"),
                zoning_description=(zone or {}).get("desc"),
                flu=flu_payload,
                data_gaps=gaps,
            )
        )
    features = finish_features(built)
    zoning_joined, flu_joined, munis = tally(features)
    sample = next((feature for feature in features if feature["properties"]["parcelId"] == "0000080100"), None)
    require(sample is not None, "Hillsborough sample FOLIO 0000080100 missing")
    require(sample["properties"]["municipality"] == "Unincorporated Hillsborough", "Sample folio municipality")
    require(sample["properties"]["lastSale"]["qualified"] is None, "VI must not be stored as a qualified sale")
    require((sample["properties"]["tax"]["marketValue"] or 0) > 0, "Sample folio market value")
    require(12000 <= len(features) <= 16000, f"Hillsborough count {len(features)}")
    require(zoning_joined >= 8000, f"Hillsborough zoning joins {zoning_joined}")
    require(flu_joined >= 8000, f"Hillsborough FLU joins {flu_joined}")
    for label in ("Tampa", "Temple Terrace", "Plant City", "Unincorporated Hillsborough"):
        require(munis.get(label, 0) >= 20, f"Hillsborough municipality {label} count {munis.get(label, 0)}")
    tampa_zoned = sum(1 for feature in features if feature["properties"].get("municipality") == "Tampa" and feature["properties"].get("zoningCode"))
    terrace_zoned = sum(
        1 for feature in features if feature["properties"].get("municipality") == "Temple Terrace" and feature["properties"].get("zoningCode")
    )
    require(tampa_zoned >= 400, f"Tampa zoning joins {tampa_zoned}")
    require(terrace_zoned >= 40, f"Temple Terrace zoning joins {terrace_zoned}")
    print(f"  Hillsborough kept {len(features)} zoning {zoning_joined} flu {flu_joined} tampa {tampa_zoned} tt {terrace_zoned}", flush=True)
    return write_county(
        county,
        markets,
        spec,
        features,
        source_count=len(parcels),
        dropped=dropped,
        zoning_joined=zoning_joined,
        flu_joined=flu_joined,
        municipality_counts=munis,
        gaps=list(HC_GAPS),
        overlays=[
            {"role": "county-zoning", "url": "https://maps.hillsboroughcounty.org/arcgis1a/rest/services/SDEMapServices/RegulatoryZoning/FeatureServer/8"},
            {"role": "flu", "url": "https://maps.hillsboroughcounty.org/arcgis1a/rest/services/SDEMapServices/Planning/FeatureServer/4"},
            {"role": "tampa-zoning", "url": "https://arcgis.tampagov.net/arcgis/rest/services/OpenData/Planning/MapServer/28"},
            {"role": "temple-terrace-zoning", "url": "https://gis.tpcmaps.org/arcgis/rest/services/Rezoning/Zoning/MapServer/0"},
            {"role": "plant-city-zoning", "url": "https://gis.tpcmaps.org/arcgis/rest/services/Rezoning/Zoning/MapServer/2"},
        ],
        rejected=[],
    )


def build_pasco(county: dict, markets: list[str], spec: dict, redownload: bool) -> dict:
    parcels = download_layer(
        "12101-parcels",
        spec["url"],
        "SITE_ACRES >= 5 AND SITE_ACRES <= 150",
        [
            "HPARCEL",
            "LPARCEL",
            "SITE_ACRES",
            "OWNER_NAME_1",
            "OWNER_NAME_2",
            "MAILING_ADDRESS_1",
            "MAILING_ADDRESS_2",
            "MAILING_CITY",
            "MAILING_STATE",
            "MAILING_ZIP",
            "SITE_ADDRESS",
            "SITE_MAILING_CITY",
            "SITE_ZIP",
            "SALE_AMOUNT",
            "SALE_DATE",
            "SALE_QUALIFIED",
            "JUST_VALUE",
            "ASSD_VAL_COUNTY",
            "TAXABLE_VAL_COUNTY",
            "ZONING",
            "FUTURELANDUSE",
            "LAND_USE_CODE",
            "JURISDICTION_NAME",
        ],
        redownload=redownload,
        batch=40,
    )
    zoning = download_layer(
        "12101-zoning",
        "https://pascogis.pascocountyfl.net/giswebmm/rest/services/FeatureDatasets/Landuse_Planning/MapServer/4/query",
        "1=1",
        ["ZN_TYPE", "ZONEID"],
        redownload=redownload,
        batch=40,
    )
    flu = download_layer(
        "12101-flu",
        "https://pascogis.pascocountyfl.net/giswebmm/rest/services/FeatureDatasets/Landuse_Planning/MapServer/1/query",
        "1=1",
        ["FLU_CODE", "DESCRIPTION"],
        redownload=redownload,
        batch=40,
    )
    print("  indexing Pasco overlays", flush=True)
    zoning_index = SpatialIndex(
        zoning,
        lambda attrs: {"code": clean(attrs.get("ZN_TYPE")), "source": "pasco-landuse-zoning"} if clean(attrs.get("ZN_TYPE")) else {},
    )
    flu_index = SpatialIndex(
        flu,
        lambda attrs: {
            "code": clean(attrs.get("FLU_CODE")),
            "label": clean(attrs.get("DESCRIPTION")),
            "source": "pasco-landuse-flu",
        }
        if clean(attrs.get("FLU_CODE"))
        else {},
    )
    seed = _seed()
    built: list[dict] = []
    dropped = 0
    for raw in parcels:
        attrs = raw.get("attributes") or {}
        parsed = geometry_of(raw, county)
        acres = num(attrs.get("SITE_ACRES"))
        if not parsed or not seed.in_band(acres):
            dropped += 1
            continue
        geometry, center, _unused = parsed
        parcel_id = clean(attrs.get("HPARCEL")) or clean(attrs.get("LPARCEL"))
        if not parcel_id:
            dropped += 1
            continue
        jurisdiction = norm_key(attrs.get("JURISDICTION_NAME")) or ""
        municipality = PASCO_MUNI.get(jurisdiction) or title_place(attrs.get("JURISDICTION_NAME"))
        unincorporated = jurisdiction == "UNINCORPORATED PASCO COUNTY"
        points = candidate_points(geometry, center)
        gaps = list(PASCO_GAPS)
        zoning_code = None
        zoning_description = None
        flu_payload = None
        if unincorporated:
            zone = first_overlay(zoning_index, points)
            code = (zone or {}).get("code")
            if code and code.upper() not in PASCO_CITY_STUBS:
                zoning_code = code
                zoning_description = None
            elif code:
                gaps.append(f"County zoning code {code} is a city placeholder and was not stored as a district.")
            else:
                gaps.append("County zoning polygon did not intersect this unincorporated parcel.")
            flu_hit = first_overlay(flu_index, points)
            if flu_hit and flu_hit.get("code"):
                flu_payload = {
                    "code": flu_hit["code"],
                    "label": flu_hit.get("label") or flu_hit["code"],
                    "jurisdiction": municipality,
                    "source": flu_hit.get("source"),
                }
            else:
                hint = clean(attrs.get("FUTURELANDUSE"))
                if hint:
                    flu_payload = {
                        "code": hint,
                        "label": hint,
                        "jurisdiction": municipality,
                        "source": "pasco-parcel-attribute",
                    }
        else:
            hint = clean(attrs.get("ZONING"))
            if hint:
                zoning_description = f"Parcel attribute hint only: {hint}. Not a verified city zoning district."
            flu_hint = clean(attrs.get("FUTURELANDUSE"))
            if flu_hint:
                flu_payload = {
                    "code": flu_hint,
                    "label": flu_hint,
                    "jurisdiction": municipality,
                    "source": "pasco-parcel-attribute",
                }
            gaps.append("Inside a Pasco city. County district polygons and NPR/PR/SA placeholders were not applied.")
        built.append(
            compose(
                county=county,
                markets=markets,
                source=spec["source"],
                parcel_id=parcel_id,
                acreage=acres or 0,
                geometry=geometry,
                center=center,
                owner=clean(attrs.get("OWNER_NAME_1")),
                owner2=clean(attrs.get("OWNER_NAME_2")),
                situs=clean(attrs.get("SITE_ADDRESS")),
                city=title_place(attrs.get("SITE_MAILING_CITY")),
                zip_code=seed.zip_str(attrs.get("SITE_ZIP")),
                dor=clean(attrs.get("LAND_USE_CODE")),
                sale_price=money(attrs.get("SALE_AMOUNT")),
                sale_date=epoch_to_iso(attrs.get("SALE_DATE")),
                sale_qualified=qualified_sale(attrs.get("SALE_QUALIFIED")),
                market_value=money(attrs.get("JUST_VALUE"), keep_zero=True),
                assessed=money(attrs.get("ASSD_VAL_COUNTY"), keep_zero=True),
                taxable=money(attrs.get("TAXABLE_VAL_COUNTY"), keep_zero=True),
                mail1=clean(attrs.get("MAILING_ADDRESS_1")),
                mail2=clean(attrs.get("MAILING_ADDRESS_2")),
                mail_city=title_place(attrs.get("MAILING_CITY")),
                mail_state=clean(attrs.get("MAILING_STATE")),
                mail_zip=seed.zip_str(attrs.get("MAILING_ZIP")),
                municipality=municipality,
                jurisdiction_code="UNINC" if unincorporated else jurisdiction.replace(" ", "-")[:32],
                zoning_code=zoning_code,
                zoning_description=zoning_description,
                flu=flu_payload,
                data_gaps=gaps,
            )
        )
    features = finish_features(built)
    zoning_joined, flu_joined, munis = tally(features)
    require(10000 <= len(features) <= 16000, f"Pasco count {len(features)} looks like the subset trap or a bad filter")
    require(PASCO_SUBSET_URL not in spec["url"], "Pasco subset URL must not be the parcel source")
    require(munis.get("Unincorporated Pasco", 0) >= 1000, "Pasco unincorporated parcels missing")
    require(zoning_joined >= 2000, f"Pasco official zoning joins {zoning_joined}")
    require(any(name != "Unincorporated Pasco" and count >= 10 for name, count in munis.items()), "Pasco cities unlabeled")
    from pinellas_pasco_muni import apply_municipal_overlays

    city_overlays = apply_municipal_overlays(features, "12101", redownload=redownload)
    zoning_joined, flu_joined, munis = tally(features)
    city_stub_as_code = sum(
        1 for feature in features if (feature["properties"].get("zoningCode") or "").upper() in {"NPR", "PR", "SA", "DC", "ZH"}
    )
    require(city_stub_as_code == 0, "Pasco city stub codes were stored as zoning districts")
    print(f"  Pasco kept {len(features)} zoning {zoning_joined} flu {flu_joined}", flush=True)
    row = write_county(
        county,
        markets,
        spec,
        features,
        source_count=len(parcels),
        dropped=dropped,
        zoning_joined=zoning_joined,
        flu_joined=flu_joined,
        municipality_counts=munis,
        gaps=list(PASCO_GAPS),
        overlays=[
            {"role": "zoning", "url": "https://pascogis.pascocountyfl.net/giswebmm/rest/services/FeatureDatasets/Landuse_Planning/MapServer/4"},
            {"role": "flu", "url": "https://pascogis.pascocountyfl.net/giswebmm/rest/services/FeatureDatasets/Landuse_Planning/MapServer/1"},
            *city_overlays["overlays"],
        ],
        rejected=[PASCO_SUBSET_URL, *city_overlays["rejected"]],
    )
    row["municipalOverlayJoins"] = city_overlays["stats"]
    target = _seed().COUNTY_DIR / county["fips"] / "county.json"
    target.write_text(json.dumps(row, indent=2) + "\n")
    return row


def pinellas_place(value: Any) -> str | None:
    return title_place(value, PINELLAS_CITY_LABELS)


def build_pinellas(county: dict, markets: list[str], spec: dict, redownload: bool) -> dict:
    parcels = download_layer(
        "12103-parcels",
        spec["url"],
        "Acres >= 5 AND Acres <= 150",
        [
            "PARCELID",
            "STRAP",
            "Acres",
            "OWNER1",
            "OWNER2",
            "OWNADD_1",
            "OWNADD_2",
            "OWNCITY",
            "OWNSTATE",
            "OWNZIP",
            "SITE_ADDRESS",
            "SITE_CITY",
            "SITE_ZIP",
            "SALEPRICE1",
            "SALEDATE1",
            "TAXABLE_VALUE",
            "LAND_VALUE",
            "IMP_VALUE",
            "LAND_USE_CODE",
            "USE_CODE",
        ],
        redownload=redownload,
        batch=35,
        workers=5,
    )
    uninc_zoning = download_layer(
        "12103-uninc-zoning",
        "https://egis.pinellas.gov/gis/rest/services/PublicWebGIS/Landuse_Zoning/MapServer/1/query",
        "1=1",
        ["ZONECLASS", "ZONEDESC"],
        redownload=redownload,
        batch=30,
    )
    uninc_flu = download_layer(
        "12103-uninc-flu",
        "https://egis.pinellas.gov/gis/rest/services/PublicWebGIS/Landuse_Zoning/MapServer/0/query",
        "1=1",
        ["LANDUSECODE", "LANDUSEDESC"],
        redownload=redownload,
        batch=30,
    )
    stpete_zoning = download_layer(
        "12103-stpete-zoning",
        "https://egis.stpete.org/arcgis/rest/services/ServicesDOTS/Zoning/MapServer/0/query",
        "1=1",
        ["ZONECLASS", "ZONEDESC"],
        redownload=redownload,
        batch=30,
    )
    stpete_flu = download_layer(
        "12103-stpete-flu",
        "https://egis.stpete.org/arcgis/rest/services/ServicesDOTS/Zoning/MapServer/2/query",
        "1=1",
        ["LANDUSECODE"],
        redownload=redownload,
        batch=30,
    )
    clearwater_zoning = download_layer(
        "12103-clearwater-zoning",
        "https://gis.myclearwater.com/arcgis/rest/services/ArcGISMapServices/Zoning_WGS84/MapServer/1/query",
        "1=1",
        ["ZONING", "ZONING_DESC"],
        redownload=redownload,
        batch=30,
    )
    clearwater_flu = download_layer(
        "12103-clearwater-flu",
        "https://gis.myclearwater.com/arcgis/rest/services/ArcGISMapServices/FLU_w_PPC_Colors_WGS84/MapServer/0/query",
        "1=1",
        ["LU"],
        redownload=redownload,
        batch=30,
    )
    largo_flu = download_layer(
        "12103-largo-flu",
        "https://maps.largo.com/arcgis/rest/services/VUEWorks_GIS_Map_Production/MapServer/1162/query",
        "1=1",
        ["Future_Land_Use_Code", "Future_Land_Use_Description"],
        redownload=redownload,
        batch=30,
    )
    print("  indexing Pinellas overlays", flush=True)

    def zone_attr(code_field: str, desc_field: str | None, source: str) -> Callable[[dict], dict]:
        def read(attrs: dict) -> dict:
            code = clean(attrs.get(code_field))
            if not code:
                return {}
            desc = clean(attrs.get(desc_field)) if desc_field else None
            return {"code": code, "desc": desc, "source": source}

        return read

    def flu_attr(code_field: str, desc_field: str | None, source: str) -> Callable[[dict], dict]:
        def read(attrs: dict) -> dict:
            code = clean(attrs.get(code_field))
            if not code:
                return {}
            desc = clean(attrs.get(desc_field)) if desc_field else None
            return {"code": code, "label": desc or code, "source": source}

        return read

    indexes = {
        "uninc_z": SpatialIndex(uninc_zoning, zone_attr("ZONECLASS", "ZONEDESC", "pinellas-uninc-zoning")),
        "uninc_f": SpatialIndex(uninc_flu, flu_attr("LANDUSECODE", "LANDUSEDESC", "pinellas-uninc-flu")),
        "stpete_z": SpatialIndex(stpete_zoning, zone_attr("ZONECLASS", "ZONEDESC", "st-petersburg-zoning")),
        "stpete_f": SpatialIndex(stpete_flu, flu_attr("LANDUSECODE", None, "st-petersburg-flu")),
        "clear_z": SpatialIndex(clearwater_zoning, zone_attr("ZONING", "ZONING_DESC", "clearwater-zoning")),
        "clear_f": SpatialIndex(clearwater_flu, flu_attr("LU", None, "clearwater-flu")),
        "largo_f": SpatialIndex(largo_flu, flu_attr("Future_Land_Use_Code", "Future_Land_Use_Description", "largo-flu")),
    }
    seed = _seed()
    built: list[dict] = []
    dropped = 0
    for raw in parcels:
        attrs = raw.get("attributes") or {}
        parsed = geometry_of(raw, county)
        acres = num(attrs.get("Acres"))
        if not parsed or not seed.in_band(acres):
            dropped += 1
            continue
        geometry, center, _unused = parsed
        parcel_id = clean(attrs.get("PARCELID")) or clean(attrs.get("STRAP"))
        if not parcel_id:
            dropped += 1
            continue
        city_key = norm_key(attrs.get("SITE_CITY"))
        points = candidate_points(geometry, center)
        gaps = list(PINELLAS_GAPS)
        zone = None
        flu_hit = None
        if city_key == "ST PETERSBURG":
            municipality = "St. Petersburg"
            zone = first_overlay(indexes["stpete_z"], points)
            flu_hit = first_overlay(indexes["stpete_f"], points)
        elif city_key == "CLEARWATER":
            municipality = "Clearwater"
            zone = first_overlay(indexes["clear_z"], points)
            flu_hit = first_overlay(indexes["clear_f"], points)
        elif city_key == "LARGO":
            municipality = "Largo"
            flu_hit = first_overlay(indexes["largo_f"], points)
            gaps.append("Largo publishes future land use only. No dedicated zoning layer was found.")
        elif city_key in PINELLAS_GAP_CITIES:
            municipality = pinellas_place(city_key)
            gaps.append("No verified public zoning/FLU layer for this Pinellas municipality. Unincorporated layers were not applied.")
        elif city_key is None:
            municipality = None
            for label, z_key, f_key in (
                ("St. Petersburg", "stpete_z", "stpete_f"),
                ("Clearwater", "clear_z", "clear_f"),
                ("Largo", None, "largo_f"),
            ):
                flu_try = first_overlay(indexes[f_key], points)
                zone_try = first_overlay(indexes[z_key], points) if z_key else None
                if flu_try or zone_try:
                    municipality = label
                    zone = zone_try
                    flu_hit = flu_try
                    if label == "Largo":
                        gaps.append("Largo publishes future land use only. No dedicated zoning layer was found.")
                    break
            if municipality is None:
                zone = first_overlay(indexes["uninc_z"], points)
                flu_hit = first_overlay(indexes["uninc_f"], points)
                if zone or flu_hit:
                    municipality = "Unincorporated Pinellas"
                else:
                    gaps.append("Municipality was not on the parcel and no city or unincorporated overlay contained the centroid.")
        else:
            municipality = "Unincorporated Pinellas"
            zone = first_overlay(indexes["uninc_z"], points)
            flu_hit = first_overlay(indexes["uninc_f"], points)
        if municipality in {"St. Petersburg", "Clearwater"} and zone is None:
            gaps.append("City zoning polygon did not intersect this parcel.")
        flu_payload = None
        if flu_hit and flu_hit.get("code"):
            flu_payload = {
                "code": flu_hit["code"],
                "label": flu_hit.get("label") or flu_hit["code"],
                "jurisdiction": municipality,
                "source": flu_hit.get("source"),
            }
        built.append(
            compose(
                county=county,
                markets=markets,
                source=spec["source"],
                parcel_id=parcel_id,
                acreage=acres or 0,
                geometry=geometry,
                center=center,
                owner=clean(attrs.get("OWNER1")),
                owner2=clean(attrs.get("OWNER2")),
                situs=clean(attrs.get("SITE_ADDRESS")),
                city=pinellas_place(attrs.get("SITE_CITY")),
                zip_code=seed.zip_str(attrs.get("SITE_ZIP")),
                dor=clean(attrs.get("LAND_USE_CODE")) or clean(attrs.get("USE_CODE")),
                sale_price=money(attrs.get("SALEPRICE1")),
                sale_date=epoch_to_iso(attrs.get("SALEDATE1")),
                market_value=None,
                assessed=None,
                taxable=money(attrs.get("TAXABLE_VALUE"), keep_zero=True),
                mail1=clean(attrs.get("OWNADD_1")),
                mail2=clean(attrs.get("OWNADD_2")),
                mail_city=title_place(attrs.get("OWNCITY")),
                mail_state=clean(attrs.get("OWNSTATE")),
                mail_zip=seed.zip_str(attrs.get("OWNZIP")),
                municipality=municipality,
                jurisdiction_code=municipality,
                zoning_code=(zone or {}).get("code"),
                zoning_description=(zone or {}).get("desc"),
                flu=flu_payload,
                data_gaps=gaps,
            )
        )
        built[-1]["properties"]["tax"]["marketValue"] = None
    features = finish_features(built)
    for feature in features:
        require(feature["properties"]["tax"]["marketValue"] is None, "Pinellas market value must stay empty")
    from pinellas_pasco_muni import apply_municipal_overlays

    city_overlays = apply_municipal_overlays(features, "12103", redownload=redownload)
    zoning_joined, flu_joined, munis = tally(features)
    require(35000 <= len(features) <= 50000, f"Pinellas count {len(features)}")
    require(zoning_joined >= 2000, f"Pinellas zoning joins {zoning_joined}")
    require(flu_joined >= 2000, f"Pinellas FLU joins {flu_joined}")
    for label in ("St. Petersburg", "Clearwater", "Largo", "Unincorporated Pinellas"):
        require(munis.get(label, 0) >= 20, f"Pinellas municipality {label} count {munis.get(label, 0)}")
    print(f"  Pinellas kept {len(features)} zoning {zoning_joined} flu {flu_joined}", flush=True)
    row = write_county(
        county,
        markets,
        spec,
        features,
        source_count=len(parcels),
        dropped=dropped,
        zoning_joined=zoning_joined,
        flu_joined=flu_joined,
        municipality_counts=munis,
        gaps=list(PINELLAS_GAPS),
        overlays=[
            {"role": "uninc-zoning", "url": "https://egis.pinellas.gov/gis/rest/services/PublicWebGIS/Landuse_Zoning/MapServer/1"},
            {"role": "uninc-flu", "url": "https://egis.pinellas.gov/gis/rest/services/PublicWebGIS/Landuse_Zoning/MapServer/0"},
            {"role": "st-petersburg-zoning", "url": "https://egis.stpete.org/arcgis/rest/services/ServicesDOTS/Zoning/MapServer/0"},
            {"role": "st-petersburg-flu", "url": "https://egis.stpete.org/arcgis/rest/services/ServicesDOTS/Zoning/MapServer/2"},
            {"role": "clearwater-zoning", "url": "https://gis.myclearwater.com/arcgis/rest/services/ArcGISMapServices/Zoning_WGS84/MapServer/1"},
            {"role": "clearwater-flu", "url": "https://gis.myclearwater.com/arcgis/rest/services/ArcGISMapServices/FLU_w_PPC_Colors_WGS84/MapServer/0"},
            {"role": "largo-flu", "url": "https://maps.largo.com/arcgis/rest/services/VUEWorks_GIS_Map_Production/MapServer/1162"},
            *city_overlays["overlays"],
        ],
        rejected=[
            "https://egis.pinellas.gov/gis/rest/services/AGO/Planning_LandUse/MapServer",
            *city_overlays["rejected"],
        ],
    )
    row["municipalOverlayJoins"] = city_overlays["stats"]
    target = _seed().COUNTY_DIR / county["fips"] / "county.json"
    target.write_text(json.dumps(row, indent=2) + "\n")
    return row


def polk_situs(attrs: dict) -> str | None:
    number = clean(attrs.get("PROP_ADRNO"))
    if number in {"0", "0.0"}:
        number = None
    parts = [number, clean(attrs.get("PROP_ADRDIR")), clean(attrs.get("PROP_ADRSTR")), clean(attrs.get("PROP_ADRSUF"))]
    text = " ".join(part for part in parts if part)
    return text or None


def build_polk(county: dict, markets: list[str], spec: dict, redownload: bool) -> dict:
    zoning_note = verify_florida_polygon(LAKELAND_ZONING_URL)
    flu_note = verify_florida_polygon(LAKELAND_FLU_URL)
    gaps = list(POLK_GAPS)
    if zoning_note or flu_note:
        replacement = " ".join(note for note in (zoning_note, flu_note) if note)
        gaps = [gap if "Lakeland zoning and future land use" not in gap else replacement for gap in gaps]
    parcels = download_layer(
        "12105-parcels",
        spec["url"],
        "GIS_ACREAGE >= 5 AND GIS_ACREAGE <= 150",
        [
            "PARCELID",
            "PR_STRAP",
            "GIS_ACREAGE",
            "TOT_ACREAGE",
            "NAME",
            "MAIL_ADDR_1",
            "MAIL_ADDR_2",
            "MAIL_ADDR_3",
            "MAIL_ZIP",
            "PROP_ADRNO",
            "PROP_ADRDIR",
            "PROP_ADRSTR",
            "PROP_ADRSUF",
            "PROP_CITY",
            "PROP_ZIP",
            "TOTALVAL",
            "ASSESSVAL",
            "TAXVAL",
            "DOR_CD",
        ],
        redownload=redownload,
        batch=30,
        workers=4,
    )
    flu = download_layer(
        "12105-flu",
        "https://gis.polk-county.net/hosting/rest/services/All-In-One_Viewer/Land_Use_and_Zoning/FeatureServer/10/query",
        "1=1",
        ["FLUNAME", "FLU_LDC", "FLU_CP", "CITY_NAME"],
        redownload=redownload,
        batch=30,
    )
    lakeland_zoning: list[dict] = []
    lakeland_flu: list[dict] = []
    if zoning_note is None:
        lakeland_zoning = download_layer(
            "12105-lakeland-zoning",
            LAKELAND_ZONING_URL + "/query",
            "1=1",
            ["LABEL", "DESIGNATIO"],
            redownload=redownload,
            batch=80,
        )
    if flu_note is None:
        lakeland_flu = download_layer(
            "12105-lakeland-flu",
            LAKELAND_FLU_URL + "/query",
            "1=1",
            ["LABEL", "DESIGNATIO"],
            redownload=redownload,
            batch=80,
        )
    print("  indexing Polk FLU, Lakeland overlays, and FDOR sales", flush=True)
    lakeland_zoning_index = SpatialIndex(
        lakeland_zoning,
        lambda attrs: {"code": clean(attrs.get("LABEL")), "desc": clean(attrs.get("DESIGNATIO"))}
        if clean(attrs.get("LABEL"))
        else {},
    )
    lakeland_flu_index = SpatialIndex(
        lakeland_flu,
        lambda attrs: {
            "code": clean(attrs.get("LABEL")),
            "label": clean(attrs.get("DESIGNATIO")) or clean(attrs.get("LABEL")),
        }
        if clean(attrs.get("LABEL"))
        else {},
    )
    flu_index = SpatialIndex(
        flu,
        lambda attrs: {
            "code": clean(attrs.get("FLU_LDC")) or clean(attrs.get("FLUNAME")),
            "label": clean(attrs.get("FLUNAME")) or clean(attrs.get("FLU_LDC")),
            "city": clean(attrs.get("CITY_NAME")),
            "source": "polk-flu-2030",
        }
        if (clean(attrs.get("FLU_LDC")) or clean(attrs.get("FLUNAME")))
        else {},
    )
    prior = load_polk_fdor()
    seed = _seed()
    built: list[dict] = []
    dropped = 0
    sales_copied = 0
    for raw in parcels:
        attrs = raw.get("attributes") or {}
        parsed = geometry_of(raw, county)
        acres = num(attrs.get("GIS_ACREAGE"))
        if acres is None:
            acres = num(attrs.get("TOT_ACREAGE"))
        if not parsed or not seed.in_band(acres):
            dropped += 1
            continue
        geometry, center, _unused = parsed
        parcel_id = clean(attrs.get("PARCELID")) or clean(attrs.get("PR_STRAP"))
        if not parcel_id:
            dropped += 1
            continue
        city_name = title_place(attrs.get("PROP_CITY"))
        municipality = city_name or "Unincorporated Polk"
        points = candidate_points(geometry, center)
        city_zone = first_overlay(lakeland_zoning_index, points) if lakeland_zoning else None
        city_flu = first_overlay(lakeland_flu_index, points) if lakeland_flu else None
        flu_hit = None if city_flu and city_flu.get("code") else first_overlay(flu_index, points)
        flu_payload = None
        parcel_gaps = list(gaps)
        zoning_code = (city_zone or {}).get("code")
        zoning_description = (city_zone or {}).get("desc")
        if city_flu and city_flu.get("code"):
            flu_payload = {
                "code": city_flu["code"],
                "label": city_flu.get("label") or city_flu["code"],
                "jurisdiction": "Lakeland",
                "source": "lakeland-flu",
            }
        elif flu_hit and flu_hit.get("code"):
            flu_city = clean(flu_hit.get("city"))
            flu_payload = {
                "code": flu_hit["code"],
                "label": flu_hit.get("label") or flu_hit["code"],
                "jurisdiction": title_place(flu_city) or "Unincorporated Polk",
                "source": "polk-flu-2030",
            }
        else:
            parcel_gaps.append("FLU 2030 polygon did not intersect this parcel.")
        if municipality == "Lakeland" and not zoning_code:
            parcel_gaps.append("Lakeland zoning polygon did not intersect this parcel.")
        if municipality == "Lakeland" and not (city_flu and city_flu.get("code")):
            parcel_gaps.append("Lakeland future land use polygon did not intersect this parcel.")
        previous = prior.get(parcel_id) or {}
        last_sale = previous.get("lastSale") or {}
        sale_price = money(last_sale.get("price"))
        sale_date = clean(last_sale.get("date"))
        sale_qualified = qualified_sale(last_sale.get("qualified"))
        if sale_price or sale_date:
            sales_copied += 1
        extra = {}
        if previous.get("oz2Eligibility") is not None:
            extra["oz2Eligibility"] = previous.get("oz2Eligibility")
        if previous.get("opportunityZone") is not None:
            extra["opportunityZone"] = previous.get("opportunityZone")
        mail3 = clean(attrs.get("MAIL_ADDR_3"))
        built.append(
            compose(
                county=county,
                markets=markets,
                source=spec["source"],
                parcel_id=parcel_id,
                acreage=acres or 0,
                geometry=geometry,
                center=center,
                owner=clean(attrs.get("NAME")),
                situs=polk_situs(attrs),
                city=city_name,
                zip_code=seed.zip_str(attrs.get("PROP_ZIP")),
                dor=clean(attrs.get("DOR_CD")),
                sale_price=sale_price,
                sale_date=sale_date,
                sale_qualified=sale_qualified,
                market_value=money(attrs.get("TOTALVAL"), keep_zero=True),
                assessed=money(attrs.get("ASSESSVAL"), keep_zero=True),
                taxable=money(attrs.get("TAXVAL"), keep_zero=True),
                mail1=clean(attrs.get("MAIL_ADDR_1")),
                mail2=clean(attrs.get("MAIL_ADDR_2")),
                mail_city=mail3,
                mail_zip=None if mail3 and seed.zip_str(attrs.get("MAIL_ZIP")) and (seed.zip_str(attrs.get("MAIL_ZIP")) or "") in mail3 else seed.zip_str(attrs.get("MAIL_ZIP")),
                municipality=municipality,
                jurisdiction_code=municipality,
                zoning_code=zoning_code,
                zoning_description=zoning_description,
                flu=flu_payload,
                data_gaps=parcel_gaps,
                extra=extra or None,
            )
        )
    features = finish_features(built)
    zoning_joined, flu_joined, munis = tally(features)
    sample = next((feature for feature in features if feature["properties"]["parcelId"] == "222601000000021030"), None)
    require(sample is not None, "Polk sample PARCELID 222601000000021030 missing")
    require(sample["properties"]["zoningCode"] is None, "Polk sample must not invent zoning")
    require(abs((sample["properties"]["acreage"] or 0) - 103.85) < 1, "Polk sample acreage")
    require(18000 <= len(features) <= 23000, f"Polk count {len(features)}")
    require(flu_joined >= 2000, f"Polk FLU joins {flu_joined}")
    require(all(feature["properties"].get("marketIds") == markets for feature in features[:20]), "Polk market ids")
    require("Orlando" not in (features[0]["properties"].get("marketIds") or []), "Polk market tiles must not be tagged Orlando")
    lakeland_zoned = sum(
        1
        for feature in features
        if feature["properties"].get("municipality") == "Lakeland" and feature["properties"].get("zoningCode")
    )
    lakeland_flu_joined = sum(
        1 for feature in features if (feature["properties"].get("flu") or {}).get("source") == "lakeland-flu"
    )
    outside_city = sorted(
        {
            str(feature["properties"].get("municipality") or "Unknown")
            for feature in features
            if feature["properties"].get("zoningCode") and feature["properties"].get("municipality") != "Lakeland"
        }
    )
    if zoning_note is None:
        require(lakeland_zoned >= 100, f"Lakeland zoning joins {lakeland_zoned}")
        require(zoning_joined < len(features) / 2, "Lakeland zoning must not cover countywide Polk")
        if outside_city:
            print(f"  Lakeland zoning also hit: {', '.join(outside_city)}", flush=True)
    else:
        require(zoning_joined == 0, "Unverified Lakeland zoning must stay empty")
    if flu_note is None:
        require(lakeland_flu_joined >= 50, f"Lakeland FLU joins {lakeland_flu_joined}")
    print(
        f"  Polk kept {len(features)} zoning {zoning_joined} flu {flu_joined} "
        f"lakeland zoning {lakeland_zoned} lakeland flu {lakeland_flu_joined} fdor sales {sales_copied}",
        flush=True,
    )
    row = write_county(
        county,
        markets,
        spec,
        features,
        source_count=len(parcels),
        dropped=dropped,
        zoning_joined=zoning_joined,
        flu_joined=flu_joined,
        municipality_counts=munis,
        gaps=gaps,
        overlays=[
            {"role": "flu-2030", "url": "https://gis.polk-county.net/hosting/rest/services/All-In-One_Viewer/Land_Use_and_Zoning/FeatureServer/10"},
            *([{"role": "lakeland-zoning", "url": LAKELAND_ZONING_URL}] if zoning_note is None else []),
            *([{"role": "lakeland-flu", "url": LAKELAND_FLU_URL}] if flu_note is None else []),
        ],
        rejected=[
            "Polk zoning-district polygons — none published on Land_Use_and_Zoning",
            LAKELAND_TLS_ZONING_URL,
            LAKELAND_TLS_FLU_URL,
            *([LAKELAND_ZONING_URL] if zoning_note else []),
            *([LAKELAND_FLU_URL] if flu_note else []),
        ],
    )
    row["fdorSaleCopiedCount"] = sales_copied
    row["lakelandZoningJoinedCount"] = lakeland_zoned
    row["lakelandFluJoinedCount"] = lakeland_flu_joined
    target = _seed().COUNTY_DIR / county["fips"] / "county.json"
    target.write_text(json.dumps(row, indent=2) + "\n")
    return row


BUILDERS = {
    "12057": build_hillsborough,
    "12101": build_pasco,
    "12103": build_pinellas,
    "12105": build_polk,
}


def pull_county(county: dict, markets: list[str], *, redownload: bool = False) -> dict:
    spec = spec_for_fips(county["fips"])
    print(f"Tampa shed {county['name']} ({county['fips']}) via {spec['source']}", flush=True)
    started = time.time()
    row = BUILDERS[county["fips"]](county, markets, spec, redownload)
    print(f"  finished {county['name']} in {time.time() - started:.0f}s", flush=True)
    return row


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    seed = _seed()
    catalog = json.loads((ROOT / "data" / "market-parcel-counties.json").read_text())
    wanted = {name.lower() for name in args.county} or {"hillsborough", "pasco", "pinellas", "polk"}
    full_markets: dict[str, list[str]] = defaultdict(list)
    chosen: dict[str, dict] = {}
    for market in catalog["markets"]:
        for county in market["counties"]:
            if market["id"] not in full_markets[county["fips"]]:
                full_markets[county["fips"]].append(market["id"])
            if county["name"].lower() in wanted:
                chosen[county["fips"]] = county
    order = ["12057", "12101", "12103", "12105"]
    for fips in order:
        county = chosen.get(fips)
        if not county:
            continue
        pull_county(county, full_markets[fips], redownload=args.refresh)
    seed.rebuild_indexes(catalog)
    print("Tampa shed indexes refreshed.", flush=True)


if __name__ == "__main__":
    main()
