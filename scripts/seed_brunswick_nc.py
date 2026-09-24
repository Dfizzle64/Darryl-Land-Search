#!/usr/bin/env python3
"""Brunswick County, NC (FIPS 37019) parcels in the 5–150 acre band.

Public GIS only. No paid vendors.

  Geometry: Brunswick SeamlessParcels layer 0, CALCAC 5.0–150.0 (~7.6k)
  Tax:      NC OneMap NC1Map_Parcels, stcntyfips 37019 and cntyfips 019
  Zoning:   MuniZoning layers 0–18 (municipalities). County Zoning attribute
            only where the centroid is outside those polygons.
  FLU:      FutureLandUse layer 0, centroid join
  OZ:       HUD 2010 designated QOZ polygons, separate from Rev. Proc. 2026-14
            tracts that are eligible for nomination and not designated.

Sale price is not on these layers. lastSale.date is DeedDate only.

  python3 scripts/seed_brunswick_nc.py
"""

from __future__ import annotations

import json
import math
import re
import struct
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from parcel_geometry import esri_rings_to_geojson, polygon_parts, representative_point, signed_area
from parcel_geometry import _inside_polygon
from seed_market_parcels import county_row, empty_feature, slug, write_tiles

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "market-parcel-counties.json"
OUT_DIR = ROOT / "data" / "fixtures" / "market-parcels"
CACHE = Path("/tmp/dls-brunswick-37019")
FIPS = "37019"
COUNTY_NAME = "Brunswick"
STATE = "North Carolina"
MARKET = "Wilmington"

SEAMLESS_QUERY = (
    "https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/SeamlessParcels/FeatureServer/0/query"
)
ONEMAP_QUERY = "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1/query"
ONEMAP_ZIP_LIST = "https://dit-cgia-gis-data.s3.amazonaws.com/?list-type=2&prefix=NCOM-data/parcels/brunswick-parcels-&max-keys=200"
ONEMAP_ZIP_BASE = "https://dit-cgia-gis-data.s3.amazonaws.com/"
TAX_FIELDS = (
    "PARNO",
    "ALTPARNO",
    "NPARNO",
    "OWNNAME",
    "OWNNAME2",
    "SITEADD",
    "SCITY",
    "SZIP",
    "PARVAL",
    "LANDVAL",
    "IMPROVVAL",
    "PARVALTYPE",
    "MAILADD",
    "MCITY",
    "MSTATE",
    "MZIP",
    "CNTYFIPS",
    "STCNTYFIPS",
)
MUNI_QUERY = "https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/MuniZoning/MapServer/{layer}/query"
FLU_QUERY = "https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/FutureLandUse/MapServer/0/query"
FLU_LAYER = "https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/FutureLandUse/MapServer/0"
HUD_QUERY = (
    "https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/FeatureServer/13/query"
)
ELIGIBLE_PACK = ROOT / "data" / "fixtures" / "oz2-eligible-packs.geojson"
NOTICE_PATH = ROOT / "data" / "fixtures" / "notice-2025-50-rural-geoids.json"
SOURCE = "bcgis-seamless-37019"
SALE_GAP = "Sale price is not published. DeedDate is the deed date only, not a price."
MIN_ACRES = 5.0
MAX_ACRES = 150.0

# Layers 0–18 are the incorporated places. CityDescription aliases are normalized.
MUNI_LAYERS: list[tuple[int, str, tuple[str, ...]]] = [
    (0, "Bald Head Island", ("VILLAGE OF BALD HEAD", "BHI MSD ZONE A", "BHI MSD ZONE B", "BALD HEAD ISLAND")),
    (1, "Belville", ("BELVILLE",)),
    (2, "Boiling Spring Lakes", ("BOILING SPRING LAKES",)),
    (3, "Bolivia", ("BOLIVIA",)),
    (4, "Calabash", ("CALABASH",)),
    (5, "Carolina Shores", ("CAROLINA SHORES",)),
    (6, "Caswell Beach", ("CASWELL BEACH",)),
    (7, "Holden Beach", ("HOLDEN BEACH",)),
    (8, "Leland", ("LELAND",)),
    (9, "Navassa", ("NAVASSA",)),
    (10, "Northwest", ("NORTHWEST",)),
    (11, "Oak Island", ("OAK ISLAND",)),
    (12, "Ocean Isle Beach", ("OCEAN ISLE BEACH", "OCEAN ISLE")),
    (13, "Sandy Creek", ("SANDY CREEK",)),
    (14, "Shallotte", ("SHALLOTTE",)),
    (15, "Southport", ("SOUTHPORT",)),
    (16, "St. James", ("ST JAMES", "ST. JAMES")),
    (17, "Sunset Beach", ("SUNSET BEACH",)),
    (18, "Varnamtown", ("VARNAMTOWN",)),
]

# Orange County planned-development tokens. A Brunswick code that matches one of
# these is stored so the Orange matcher does not treat it as an Orange PD.
ORANGE_PD_TOKENS = ("P-D", "PD", "PUD", "U-V", "PURD", "PUD-COMM", "PUD-MD", "PCD")
DEED_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


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
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def norm_place(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.upper().replace(".", " ").split())


def fetch_json(url: str, params: dict | None = None, timeout: int = 120, retries: int = 4) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/brunswick-37019"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and data.get("error") and attempt + 1 < retries:
                time.sleep(0.8 * (attempt + 1))
                continue
            return data
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:180]}: {last_err}")


def object_ids(url: str, where: str) -> list[int]:
    data = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    return [int(i) for i in (data.get("objectIds") or [])]


def fetch_id_chunks(url: str, ids: list[int], fields: list[str], batch: int, extra: dict | None = None) -> list[dict]:
    features: list[dict] = []

    def pull(chunk: list[int]) -> list[dict]:
        params = {
            "objectIds": ",".join(str(i) for i in chunk),
            "outFields": ",".join(fields),
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        }
        if extra:
            params.update(extra)
        try:
            data = fetch_json(url, params, timeout=180)
        except RuntimeError:
            if len(chunk) > 8:
                mid = len(chunk) // 2
                return pull(chunk[:mid]) + pull(chunk[mid:])
            raise
        if data.get("error"):
            if len(chunk) > 8:
                mid = len(chunk) // 2
                return pull(chunk[:mid]) + pull(chunk[mid:])
            raise RuntimeError(json.dumps(data["error"])[:300])
        return list(data.get("features") or [])

    total = len(ids)
    chunks = [ids[start : start + batch] for start in range(0, total, batch)]
    done = 0
    workers = 4 if total > 400 else 2
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(pull, chunk) for chunk in chunks]
        for future in as_completed(futures):
            features.extend(future.result())
            done += 1
            if done == 1 or done == len(chunks) or done % 25 == 0:
                print(f"    batches {done}/{len(chunks)} features {len(features)}", flush=True)
    return features


def load_cached(name: str) -> Any | None:
    path = CACHE / name
    if not path.exists():
        return None
    print(f"  cache {name}", flush=True)
    return json.loads(path.read_text())


def save_cached(name: str, payload: Any) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / name).write_text(json.dumps(payload))


class PolyIndex:
    def __init__(self, cell: float = 0.04) -> None:
        self.cell = cell
        self.grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.large: list[int] = []
        self.items: list[tuple[list, Any, float, tuple[float, float, float, float]]] = []

    def add(self, geometry: dict | None, payload: Any) -> None:
        if not geometry:
            return
        parts = polygon_parts(geometry)
        polys = []
        minx = miny = 1e9
        maxx = maxy = -1e9
        area = 0.0
        for poly in parts:
            if not poly or not poly[0] or len(poly[0]) < 4:
                continue
            xs = [p[0] for p in poly[0]]
            ys = [p[1] for p in poly[0]]
            bx0, bx1 = min(xs), max(xs)
            by0, by1 = min(ys), max(ys)
            minx, miny = min(minx, bx0), min(miny, by0)
            maxx, maxy = max(maxx, bx1), max(maxy, by1)
            area += abs(signed_area(poly[0]))
            polys.append(poly)
        if not polys:
            return
        idx = len(self.items)
        self.items.append((polys, payload, area, (minx, miny, maxx, maxy)))
        ix0, ix1 = math.floor(minx / self.cell), math.floor(maxx / self.cell)
        iy0, iy1 = math.floor(miny / self.cell), math.floor(maxy / self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 250:
            self.large.append(idx)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.grid[(ix, iy)].append(idx)

    def hits(self, lon: float, lat: float) -> list[tuple[float, Any]]:
        ids = list(self.grid.get((math.floor(lon / self.cell), math.floor(lat / self.cell)), []))
        ids.extend(self.large)
        found: list[tuple[float, Any]] = []
        seen: set[int] = set()
        for idx in ids:
            if idx in seen:
                continue
            seen.add(idx)
            polys, payload, area, bbox = self.items[idx]
            if not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
                continue
            if any(_inside_polygon(lon, lat, poly) for poly in polys):
                found.append((area, payload))
        found.sort(key=lambda item: item[0])
        return found


def esri_feature_geometry(feature: dict) -> dict | None:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") and geometry.get("coordinates"):
        return geometry
    rings = geometry.get("rings")
    if not rings:
        return None
    return esri_rings_to_geojson(rings)


def deed_date(raw: Any) -> str | None:
    text = clean(raw)
    if not text:
        return None
    match = DEED_RE.match(text)
    if not match:
        return None
    month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if not (1900 <= year <= 2100):
        return None
    try:
        datetime(year, month, day)
    except ValueError:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def collides_with_orange_pd(code: str) -> bool:
    district = code.upper().strip()
    for token in ORANGE_PD_TOKENS:
        if district == token:
            return True
        if district.startswith(token):
            nxt = district[len(token) : len(token) + 1]
            if nxt == "" or not nxt.isdigit():
                return True
        if district.endswith(" " + token) or district.endswith("-" + token):
            return True
    return False


def stored_zoning_district(code: str) -> str:
    """Keep the published code unless it would match an Orange County PD token.

    The Orange matcher treats a district that ends in ``-PD`` / ``-PUD`` as planned
    development. A ``brunswick:`` prefix still ends that way, so colliding codes are
    stored with hyphens turned into underscores. zoningCode stays the published value.
    """
    if collides_with_orange_pd(code):
        return "b0_" + code.replace("-", "_").replace(" ", "_")
    return code


def parsed_prefix(code: str) -> str | None:
    raw = code.strip().upper()
    head, *rest = raw.split("-")
    if head and rest and re.fullmatch(r"[A-Z]{2,3}", head):
        return head
    return None


def situs_line(attrs: dict) -> str | None:
    number = clean(attrs.get("HouseNumber"))
    if number:
        stripped = number.lstrip("0")
        number = stripped or "0"
    parts = [
        number,
        clean(attrs.get("StreetDirection")),
        clean(attrs.get("StreetName")),
        clean(attrs.get("StreetType")),
    ]
    line = " ".join(part for part in parts if part)
    return line or None


def zip_text(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    return text[:10]


def tract_name(tract: str | None, geoid: str | None, fallback: str | None) -> str | None:
    if fallback:
        return fallback
    digits = "".join(ch for ch in (tract or "") if ch.isdigit()) or ((geoid or "")[-6:] if geoid else "")
    if not digits:
        return geoid
    value = int(digits)
    pretty = str(value // 100) if value % 100 == 0 else f"{value / 100:.2f}".rstrip("0")
    return f"Census tract {pretty}"


def muni_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for _layer, name, aliases in MUNI_LAYERS:
        lookup[norm_place(name)] = name
        for alias in aliases:
            lookup[norm_place(alias)] = name
    return lookup


def municipality_name(city_description: str | None, places: dict[str, str]) -> str | None:
    return places.get(norm_place(city_description))


def load_parcels() -> list[dict]:
    cached = load_cached("parcels.json")
    if cached:
        return cached
    print("Pulling SeamlessParcels/0 CALCAC 5–150", flush=True)
    ids = object_ids(SEAMLESS_QUERY, "CALCAC >= 5 AND CALCAC <= 150")
    print(f"  object ids {len(ids)}", flush=True)
    fields = [
        "ParcelNumber",
        "PIN",
        "CALCAC",
        "Name1",
        "Name2",
        "Address1",
        "Address2",
        "Address3",
        "City",
        "State",
        "ZipCode",
        "CityDescription",
        "HouseNumber",
        "StreetName",
        "StreetType",
        "StreetDirection",
        "Zoning",
        "DeedDate",
        "TaxCard",
    ]
    raw = fetch_id_chunks(SEAMLESS_QUERY, ids, fields, batch=40)
    save_cached("parcels.json", raw)
    return raw


def latest_onemap_zip() -> tuple[str, str]:
    """Public county extract. The live query service is too slow for a countywide attribute join."""
    local = Path("/tmp/brunswick-parcels.zip")
    if local.exists() and local.stat().st_size > 1_000_000:
        return str(local), "brunswick-parcels-05-28-2026.zip"
    listing = urllib.request.urlopen(
        urllib.request.Request(ONEMAP_ZIP_LIST, headers={"User-Agent": "darryl-land-search/brunswick-37019"}),
        timeout=60,
    ).read().decode("utf-8", "replace")
    keys = re.findall(r"NCOM-data/parcels/brunswick-parcels-(\d{2})-(\d{2})-(\d{4})\.zip", listing)
    if not keys:
        raise RuntimeError("NC OneMap S3 listing has no Brunswick parcel zip")
    month, day, year = max(keys, key=lambda item: (int(item[2]), int(item[0]), int(item[1])))
    name = f"brunswick-parcels-{month}-{day}-{year}.zip"
    key = f"NCOM-data/parcels/{name}"
    dest = CACHE / name
    CACHE.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        print(f"  downloading {ONEMAP_ZIP_BASE}{key}", flush=True)
        with urllib.request.urlopen(
            urllib.request.Request(ONEMAP_ZIP_BASE + key, headers={"User-Agent": "darryl-land-search/brunswick-37019"}),
            timeout=180,
        ) as resp, dest.open("wb") as handle:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    return str(dest), name


def stream_tax_table(zip_path: str, wanted_parno: set[str], wanted_pin: set[str]) -> dict[str, dict]:
    by_parno: dict[str, dict] = {}
    by_pin: dict[str, dict] = {}
    with zipfile.ZipFile(zip_path) as archive:
        name = next(item for item in archive.namelist() if item.endswith("_poly.dbf"))
        with archive.open(name) as handle:
            prelude = handle.read(32)
            record_count = struct.unpack("<I", prelude[4:8])[0]
            header_len = struct.unpack("<H", prelude[8:10])[0]
            record_len = struct.unpack("<H", prelude[10:12])[0]
            rest = handle.read(header_len - 32)
            fields: list[tuple[str, int, int]] = []
            cursor = 1  # deletion flag
            index = 0
            while index + 32 <= len(rest) and rest[index] != 0x0D:
                field_name = rest[index : index + 11].split(b"\x00", 1)[0].decode("ascii", "replace")
                length = rest[index + 16]
                if field_name in TAX_FIELDS:
                    fields.append((field_name, cursor, length))
                cursor += length
                index += 32
            if cursor != record_len:
                raise RuntimeError(f"DBF record length {record_len} != field sum {cursor}")
            wanted = {item[0] for item in fields}
            missing = [name for name in ("PARNO", "ALTPARNO", "PARVAL", "CNTYFIPS", "STCNTYFIPS") if name not in wanted]
            if missing:
                raise RuntimeError(f"NC OneMap parcel table missing {missing}")
            kept = 0
            county_rows = 0
            for _ in range(record_count):
                raw = handle.read(record_len)
                if len(raw) < record_len:
                    break
                if raw[:1] == b"*":
                    continue
                parsed: dict[str, str] = {}
                for field_name, start, length in fields:
                    text = raw[start : start + length].decode("latin-1", "replace")
                    parsed[field_name.lower()] = text.replace("\x00", "").strip()
                if parsed.get("cntyfips") not in {None, "", "019"}:
                    continue
                if parsed.get("stcntyfips") not in {None, "", "37019"}:
                    continue
                county_rows += 1
                parno = parsed.get("parno") or ""
                pin = parsed.get("altparno") or ""
                if parno not in wanted_parno and pin not in wanted_pin:
                    continue
                kept += 1
                if parno:
                    by_parno[parno] = parsed
                if pin:
                    by_pin[pin] = parsed
            print(f"  OneMap table rows in county {county_rows}, matched keys {kept}", flush=True)
    return {"byParno": by_parno, "byPin": by_pin}


def load_tax(parcel_ids: list[str], pins: list[str]) -> dict[str, dict]:
    cached = load_cached("tax.json")
    if cached:
        return cached
    print("Joining NC OneMap tax attributes CNTYFIPS 37019 / cntyfips 019", flush=True)
    zip_path, zip_name = latest_onemap_zip()
    print(f"  using {zip_name}", flush=True)
    payload = stream_tax_table(zip_path, set(parcel_ids), set(pins))
    payload["sourceZip"] = zip_name
    save_cached("tax.json", payload)
    return payload


def load_zoning() -> PolyIndex:
    cached = load_cached("zoning.json")
    index = PolyIndex(0.03)
    rows = cached
    if rows is None:
        print("Pulling MuniZoning layers 0–18", flush=True)
        rows = []
        for layer, name, aliases in MUNI_LAYERS:
            ids = object_ids(MUNI_QUERY.format(layer=layer), "1=1")
            raw = fetch_id_chunks(MUNI_QUERY.format(layer=layer), ids, ["ZCODE"], batch=80) if ids else []
            kept = 0
            for feature in raw:
                geometry = esri_feature_geometry(feature)
                code = clean((feature.get("attributes") or {}).get("ZCODE"))
                if not geometry or not code:
                    continue
                rows.append({"name": name, "aliases": list(aliases), "code": code, "geometry": geometry})
                kept += 1
            print(f"  {layer} {name}: {kept}", flush=True)
        save_cached("zoning.json", rows)
    for row in rows:
        index.add(row["geometry"], {"name": row["name"], "aliases": [norm_place(a) for a in row["aliases"]], "code": row["code"]})
    print(f"  municipal zoning polygons {len(rows)}", flush=True)
    return index


def flu_labels() -> dict[str, str]:
    try:
        meta = fetch_json(FLU_LAYER, {"f": "json"})
    except RuntimeError:
        return {}
    labels: dict[str, str] = {}
    renderer = ((meta.get("drawingInfo") or {}).get("renderer") or {})
    for info in renderer.get("uniqueValueInfos") or []:
        value = clean(info.get("value"))
        label = clean(info.get("label"))
        if value and label:
            labels[value] = label
    return labels


def load_flu(labels: dict[str, str]) -> PolyIndex:
    cached = load_cached("flu.json")
    index = PolyIndex(0.03)
    rows = cached
    if rows is None:
        print("Pulling FutureLandUse/0", flush=True)
        ids = object_ids(FLU_QUERY, "1=1")
        print(f"  object ids {len(ids)}", flush=True)
        raw = fetch_id_chunks(
            FLU_QUERY,
            ids,
            ["FLU"],
            batch=80,
            extra={"maxAllowableOffset": "0.00004"},
        )
        rows = []
        for feature in raw:
            code = clean((feature.get("attributes") or {}).get("FLU"))
            geometry = esri_feature_geometry(feature)
            if not code or not geometry:
                continue
            rows.append({"code": code, "geometry": geometry})
        save_cached("flu.json", rows)
    for row in rows:
        code = row["code"]
        index.add(row["geometry"], {"code": code, "label": labels.get(code) or code})
    print(f"  future land use polygons {len(rows)}", flush=True)
    return index


def load_designated() -> PolyIndex:
    print("Pulling HUD designated QOZ polygons for county 019", flush=True)
    data = fetch_json(
        HUD_QUERY,
        {
            "where": "STATE='37' AND COUNTY='019'",
            "outFields": "GEOID10,TRACT,STATE_NAME,Rural",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    notice = set()
    if NOTICE_PATH.exists():
        notice = set(json.loads(NOTICE_PATH.read_text()).get("geoids") or [])
    index = PolyIndex(0.05)
    count = 0
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        geoid = clean(props.get("GEOID10") or props.get("geoid"))
        if not geoid or not feature.get("geometry"):
            continue
        rural_raw = props.get("Rural")
        notice_rural = geoid in notice
        index.add(
            feature["geometry"],
            {
                "inOpportunityZone": True,
                "tractGeoid": geoid,
                "tractName": tract_name(clean(props.get("TRACT")), geoid, None),
                "source": "hud-fs-13",
                "designatedRural": True if notice_rural else False,
                "hudRural": rural_raw,
            },
        )
        count += 1
    if count == 0:
        raise RuntimeError("HUD returned no designated QOZ polygons for Brunswick County")
    print(f"  designated tracts {count}", flush=True)
    return index


def load_eligible() -> PolyIndex:
    print("Loading Rev. Proc. 2026-14 eligible tracts for Brunswick (not designations)", flush=True)
    pack = json.loads(ELIGIBLE_PACK.read_text())
    index = PolyIndex(0.05)
    count = 0
    for feature in pack.get("features") or []:
        props = feature.get("properties") or {}
        geoid = clean(props.get("tractGeoid") or props.get("id"))
        if not geoid or not geoid.startswith(FIPS):
            continue
        if props.get("designation") != "eligible-for-nomination":
            continue
        rural = props.get("rural")
        index.add(
            feature.get("geometry"),
            {
                "eligible": True,
                "rural": True if rural is True else False if rural is False else None,
                "tractGeoid": geoid,
                "tractName": clean(props.get("name")),
                "designation": "eligible-for-nomination",
                "source": "rev-proc-2026-14",
            },
        )
        count += 1
    if count == 0:
        raise RuntimeError("Eligible pack has no Brunswick tracts")
    print(f"  eligible tracts {count}", flush=True)
    return index


def outside_zone() -> dict:
    return {
        "inOpportunityZone": False,
        "tractGeoid": None,
        "tractName": None,
        "source": "hud-fs-13",
        "designatedRural": None,
    }


def outside_eligible() -> dict:
    return {
        "eligible": False,
        "rural": None,
        "tractGeoid": None,
        "tractName": None,
        "designation": "not-eligible",
        "source": "rev-proc-2026-14",
    }


def choose_zoning(hits: list[tuple[float, Any]], city_norm: str) -> dict | None:
    if not hits:
        return None
    preferred = [item for item in hits if city_norm and (city_norm == norm_place(item[1]["name"]) or city_norm in item[1]["aliases"])]
    pool = preferred or hits
    return pool[0][1]


def positive(value: Any) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def build_features() -> tuple[list[dict], dict]:
    places = muni_lookup()
    muni_norms = set(places)
    parcels = load_parcels()
    parcel_ids: list[str] = []
    pins: list[str] = []
    for feature in parcels:
        attrs = feature.get("attributes") or {}
        parcel_id = clean(attrs.get("ParcelNumber"))
        pin = clean(attrs.get("PIN"))
        if parcel_id:
            parcel_ids.append(parcel_id)
        if pin:
            pins.append(pin)
    tax = load_tax(parcel_ids, pins)
    by_parno = tax["byParno"]
    by_pin = tax["byPin"]
    labels = flu_labels()
    zoning_index = load_zoning()
    flu_index = load_flu(labels)
    designated_index = load_designated()
    eligible_index = load_eligible()

    stats = {
        "sourceCount": len(parcels),
        "dropped": 0,
        "taxMatched": 0,
        "deedDates": 0,
        "deedUnparsed": 0,
        "muniHits": 0,
        "incorporatedMiss": 0,
        "fluHits": 0,
        "fluPlaceholder": 0,
        "designated": 0,
        "eligible": 0,
        "eligibleAndDesignated": 0,
        "parvalTypes": defaultdict(int),
        "taxSource": tax.get("sourceZip") or "nc-onemap-brunswick-parcels-zip",
    }
    by_id: dict[str, dict] = {}
    for feature in parcels:
        attrs = feature.get("attributes") or {}
        geometry = esri_feature_geometry(feature)
        if not geometry:
            stats["dropped"] += 1
            continue
        center = representative_point(geometry)
        if not center or not (-82 < center[0] < -77 and 33 < center[1] < 35):
            stats["dropped"] += 1
            continue
        acres = num(attrs.get("CALCAC"))
        if acres is None or acres < MIN_ACRES or acres > MAX_ACRES:
            stats["dropped"] += 1
            continue
        parcel_id = clean(attrs.get("ParcelNumber")) or clean(attrs.get("PIN"))
        if not parcel_id:
            stats["dropped"] += 1
            continue
        pin = clean(attrs.get("PIN"))
        tax_row = by_parno.get(parcel_id) or (by_pin.get(pin) if pin else None)
        if tax_row:
            stats["taxMatched"] += 1
            stats["parvalTypes"][clean(tax_row.get("parvaltype")) or "(blank)"] += 1
        city_name = municipality_name(attrs.get("CityDescription"), places)
        city_norm = norm_place(city_name) if city_name else ""
        zoning_hit = choose_zoning(zoning_index.hits(center[0], center[1]), city_norm)
        county_zoning = clean(attrs.get("Zoning"))
        if zoning_hit:
            stats["muniHits"] += 1
            zoning_code = zoning_hit["code"]
            jurisdiction = zoning_hit["name"]
            situs_city = zoning_hit["name"]
        else:
            zoning_code = county_zoning
            if city_name:
                stats["incorporatedMiss"] += 1
                jurisdiction = city_name
                situs_city = city_name
            else:
                jurisdiction = "Brunswick County"
                situs_city = None
        flu_hits = flu_index.hits(center[0], center[1])
        flu = None
        if flu_hits:
            flu_payload = flu_hits[0][1]
            if norm_place(flu_payload["code"]) in muni_norms:
                stats["fluPlaceholder"] += 1
            else:
                stats["fluHits"] += 1
                flu = {
                    "code": flu_payload["code"],
                    "label": flu_payload["label"],
                    "jurisdiction": "Brunswick County",
                    "source": FLU_LAYER,
                }
        designated_hits = designated_index.hits(center[0], center[1])
        eligible_hits = eligible_index.hits(center[0], center[1])
        opportunity = dict(designated_hits[0][1]) if designated_hits else outside_zone()
        opportunity.pop("hudRural", None)
        eligibility = dict(eligible_hits[0][1]) if eligible_hits else outside_eligible()
        if opportunity["inOpportunityZone"]:
            stats["designated"] += 1
        if eligibility["eligible"]:
            stats["eligible"] += 1
        if opportunity["inOpportunityZone"] and eligibility["eligible"]:
            stats["eligibleAndDesignated"] += 1
        # Eligible never writes the designated flag.
        if eligibility["eligible"] and eligibility["designation"] != "eligible-for-nomination":
            raise RuntimeError("eligible tract was stored as something other than eligible-for-nomination")
        deed_raw = clean(attrs.get("DeedDate"))
        deed = deed_date(deed_raw)
        if deed:
            stats["deedDates"] += 1
        elif deed_raw:
            stats["deedUnparsed"] += 1
        market_value = None
        if tax_row:
            kind = (clean(tax_row.get("parvaltype")) or "").lower()
            amount = positive(tax_row.get("parval"))
            if amount is not None and (not kind or "market" in kind):
                market_value = amount
        situs = situs_line(attrs) or (clean(tax_row.get("siteadd")) if tax_row else None)
        situs_zip = zip_text(tax_row.get("szip")) if tax_row else None
        owner = clean(attrs.get("Name1")) or (clean(tax_row.get("ownname")) if tax_row else None)
        owner2 = clean(attrs.get("Name2")) or (clean(tax_row.get("ownname2")) if tax_row else None)
        mail1 = clean(attrs.get("Address1"))
        mail2 = clean(attrs.get("Address2"))
        mail3 = clean(attrs.get("Address3"))
        if mail2 and mail3:
            mail2 = f"{mail2}, {mail3}"
        elif mail3 and not mail2:
            mail2 = mail3
        mail_city = clean(attrs.get("City"))
        mail_state = clean(attrs.get("State"))
        mail_zip = zip_text(attrs.get("ZipCode"))
        if not mail1 and not mail2 and tax_row:
            mail1 = clean(tax_row.get("mailadd"))
            mail_city = mail_city or clean(tax_row.get("mcity"))
            mail_state = mail_state or clean(tax_row.get("mstate"))
            mail_zip = mail_zip or zip_text(tax_row.get("mzip"))
        gaps = [SALE_GAP]
        if not tax_row:
            gaps.append("NC OneMap tax values for CNTYFIPS 37019 did not match this parcel number.")
        if city_name and not zoning_hit:
            gaps.append(
                f"CityDescription is {city_name}, but the centroid missed MuniZoning. The county Zoning attribute is not a municipal district."
            )
        card = clean(attrs.get("TaxCard"))
        if not card:
            card = f"https://tax.brunsco.net/ITSNet/AppraisalCard.aspx?parcel={urllib.parse.quote(parcel_id)}"
        built = empty_feature(
            fips=FIPS,
            county=COUNTY_NAME,
            state=STATE,
            markets=[MARKET],
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source=SOURCE,
            owner=owner,
            situs=situs,
            city=situs_city,
            zip_code=situs_zip,
            zoning=zoning_code,
            sale_price=None,
            sale_date=deed,
            sale_qualified=None,
            market_value=market_value,
            mail1=mail1,
            mail2=mail2,
            mail_city=mail_city,
            mail_state=mail_state,
            mail_zip=mail_zip,
        )
        props = built["properties"]
        props["ownerName2"] = owner2
        props["jurisdictionCode"] = jurisdiction
        props["jurisdictionPrefix"] = parsed_prefix(zoning_code) if zoning_code else None
        props["zoningDistrict"] = stored_zoning_district(zoning_code) if zoning_code else None
        props["flu"] = flu
        props["opportunityZone"] = opportunity
        props["oz2Eligibility"] = eligibility
        props["appraiserUrl"] = card
        props["dataGaps"] = gaps
        props["lastSale"] = {"date": deed, "price": None, "qualified": None}
        props["tax"]["assessedValue"] = None
        props["tax"]["taxableValue"] = None
        props["tax"]["taxes"] = None
        previous = by_id.get(parcel_id)
        if previous is None or (props["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = built
    features = list(by_id.values())
    features.sort(key=lambda row: (-(row["properties"]["acreage"] or 0), row["properties"]["parcelId"]))
    # Join stats follow the published ids. Duplicate parcel numbers were counted once per source row above.
    stats["featureCount"] = len(features)
    stats["taxMatched"] = 0
    stats["deedDates"] = 0
    stats["muniHits"] = 0
    stats["incorporatedMiss"] = 0
    stats["fluHits"] = 0
    stats["designated"] = 0
    stats["eligible"] = 0
    stats["eligibleAndDesignated"] = 0
    parval_types: dict[str, int] = defaultdict(int)
    for feature in features:
        props = feature["properties"]
        gaps = props.get("dataGaps") or []
        missed_tax = any("did not match" in gap for gap in gaps)
        missed_muni = any("missed MuniZoning" in gap for gap in gaps)
        if not missed_tax:
            stats["taxMatched"] += 1
            if props["tax"]["marketValue"] is not None:
                parval_types["Market"] += 1
            else:
                parval_types["(matched, no positive market value)"] += 1
        if props["lastSale"]["date"]:
            stats["deedDates"] += 1
        if props.get("jurisdictionCode") != "Brunswick County" and not missed_muni:
            stats["muniHits"] += 1
        if missed_muni:
            stats["incorporatedMiss"] += 1
        if props.get("flu"):
            stats["fluHits"] += 1
        if (props.get("opportunityZone") or {}).get("inOpportunityZone"):
            stats["designated"] += 1
        if (props.get("oz2Eligibility") or {}).get("eligible"):
            stats["eligible"] += 1
        if (props.get("opportunityZone") or {}).get("inOpportunityZone") and (props.get("oz2Eligibility") or {}).get("eligible"):
            stats["eligibleAndDesignated"] += 1
    stats["parvalTypes"] = dict(parval_types)
    return features, stats


def gap_lines(stats: dict) -> list[str]:
    return [
        "Sale price is not published on Brunswick SeamlessParcels or NC OneMap. lastSale.date is DeedDate only; lastSale.price and qualified are null.",
        "OZ 2.0 eligible tracts (Rev. Proc. 2026-14) are not designated QOZs. opportunityZone is only the HUD 2010 designated polygon join.",
        "Geometry and the 5.0–150.0 acre band are Brunswick County SeamlessParcels layer 0 on CALCAC (calculated GIS acres). DeedAcreage is text and is not the filter.",
        (
            f"Tax values are the public NC OneMap county parcel table ({stats.get('taxSource')}) for stcntyfips 37019 and cntyfips 019, joined on parcel number. "
            f"Matched {stats['taxMatched']} of {stats['featureCount']}. parval is market value when the roll type is Market. "
            "Land and improvement values are not stored as assessed value. Taxable value, the tax bill, and sale price are not published. OneMap saledatetx is not used."
        ),
        (
            f"Municipal zoning is a centroid join to MuniZoning layers 0–18 and replaces the county Zoning attribute inside a municipality "
            f"({stats['muniHits']} parcels). Unincorporated parcels keep SeamlessParcels.Zoning. "
            f"{stats['incorporatedMiss']} parcels have a municipal CityDescription but missed the zoning polygons. "
            "These codes are not Orange County multifamily districts."
        ),
        (
            f"Future land use is a centroid join to FutureLandUse layer 0 ({stats['fluHits']} of {stats['featureCount']}). "
            "Codes are stored as published and are not in the Orange County FLU knowledge base, so multifamily screening leaves them unknown. "
            "A FLU value that is only a municipality name is not a land-use designation. Municipal FLU maps are not a separate layer in this service."
        ),
        "SeamlessParcels mailing city is not the situs city. Situs city is the municipality from CityDescription or the MuniZoning polygon.",
        "The county UseCode is not a Florida DOR code and is not copied onto the parcel.",
    ]


def publish(features: list[dict], stats: dict, markets: list[str]) -> dict:
    county = {"name": COUNTY_NAME, "fips": FIPS, "state": STATE}
    path, lookup, tiles = write_tiles(county, features)
    gaps = gap_lines(stats)
    row = county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=SOURCE,
        query_url=SEAMLESS_QUERY,
        gaps=gaps,
        source_count=stats["sourceCount"],
        dropped=stats["dropped"],
        tile_count=tiles,
    )
    row["taxJoinedCount"] = stats["taxMatched"]
    row["muniZoningCount"] = stats["muniHits"]
    row["fluJoinedCount"] = stats["fluHits"]
    row["designatedOzCount"] = stats["designated"]
    row["oz2EligibleCount"] = stats["eligible"]
    row["eligibleAlsoDesignatedCount"] = stats["eligibleAndDesignated"]
    (OUT_DIR / "counties" / FIPS / "county.json").write_text(json.dumps(row, indent=2) + "\n")
    patch_market_indexes(row, markets)
    print(
        f"Brunswick {len(features)} parcels, tax {stats['taxMatched']}, muni zoning {stats['muniHits']}, "
        f"flu {stats['fluHits']}, designated {stats['designated']}, eligible {stats['eligible']}, "
        f"both {stats['eligibleAndDesignated']}, deed dates {stats['deedDates']}, dropped {stats['dropped']}",
        flush=True,
    )
    print(f"  parval types {stats['parvalTypes']}", flush=True)
    return row


def patch_market_indexes(row: dict, markets: list[str]) -> None:
    for market in markets:
        meta_path = OUT_DIR / "markets" / slug(market) / "meta.json"
        meta = json.loads(meta_path.read_text())
        old = next((item for item in meta["counties"] if item.get("fips") == FIPS), None)
        old_count = int(old.get("featureCount") or 0) if old else 0
        replacement = {
            "name": row["name"],
            "fips": row["fips"],
            "state": row["state"],
            "featureCount": row["featureCount"],
            "coverage": row["coverage"],
            "partition": row["partition"],
            "minAcres": MIN_ACRES,
            "maxAcres": MAX_ACRES,
            "source": row["source"],
            "queryUrl": row["queryUrl"],
            "gaps": row["gaps"],
            "path": row["path"],
            "lookup": row["lookup"],
            "tileCount": row["tileCount"],
            "sourceCount": row["sourceCount"],
        }
        counties = []
        replaced = False
        for item in meta["counties"]:
            if item.get("fips") == FIPS:
                counties.append(replacement)
                replaced = True
            else:
                counties.append(item)
        if not replaced:
            counties.append(replacement)
        counties.sort(key=lambda item: item["name"])
        meta["counties"] = counties
        meta["parcelCount"] = int(meta.get("parcelCount") or 0) - old_count + int(row["featureCount"])
        meta["generatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        index_path = OUT_DIR / "index.json"
        index = json.loads(index_path.read_text())
        summary = index["markets"][market]
        summary["parcelCount"] = meta["parcelCount"]
        summary["counties"] = [
            {
                "name": item["name"],
                "state": item["state"],
                "fips": item["fips"],
                "featureCount": item.get("featureCount") or 0,
                "coverage": item.get("coverage"),
                "minAcres": MIN_ACRES,
                "maxAcres": MAX_ACRES,
                "gaps": (item.get("gaps") or [])[:2],
            }
            for item in meta["counties"]
        ]
        index["generatedAt"] = meta["generatedAt"]
        index_path.write_text(json.dumps(index, indent=2) + "\n")
        patch_docs(old_count, int(row["featureCount"]), int(meta["parcelCount"]))


def patch_docs(old_county: int, new_county: int, market_total: int) -> None:
    files = [ROOT / "docs" / "market-parcels.md", OUT_DIR / "coverage.md"]
    old_county_line = f"| Brunswick | North Carolina | 37019 | complete-gte-5ac | {old_county:,} | nc-onemap-37019 |"
    new_county_line = f"| Brunswick | North Carolina | 37019 | complete-gte-5ac | {new_county:,} | {SOURCE} |"
    # The market total line is shared. Recompute from the previous published Wilmington total if present.
    for path in files:
        if not path.exists():
            continue
        text = path.read_text()
        text = re.sub(
            r"\| Brunswick \| North Carolina \| 37019 \| complete-gte-5ac \| [0-9,]+ \| [^|\n]+ \|",
            new_county_line,
            text,
        )
        text = text.replace(old_county_line, new_county_line)
        text = text.replace(
            "| North Carolina | NC OneMap `NC1Map_Parcels` polygons | Complete 5–150 acre extract. Most counties use `gisacres`. Cleveland, Columbus, Orange, and Warren store polygon acres because `gisacres` is 0 |",
            "| North Carolina | NC OneMap `NC1Map_Parcels` polygons | Complete 5–150 acre extract. Most counties use `gisacres`. Cleveland, Columbus, Orange, and Warren store polygon acres because `gisacres` is 0. Brunswick County is county SeamlessParcels (CALCAC 5–150), with NC OneMap tax attributes, MuniZoning layers 0–18, and FutureLandUse layer 0. Sale price is not published (DeedDate only) |",
        )
        text = text.replace(
            "Zoning is joined only when the county layer already carries a zoning field (DeKalb). It is not a multifamily knowledge-base match outside Orange County. Prefer **All parcels** in these markets.",
            "Zoning is joined only when a public layer carries it (DeKalb's tax parcels, and Brunswick County municipal zoning). It is not a multifamily knowledge-base match outside Orange County. Prefer **All parcels** in these markets.",
        )
        # Wilmington's previous total is whatever is on the summary row. Replace the whole row.
        text = re.sub(
            r"\| Wilmington \| other \| [0-9,]+ \| 6 \| 0 \| 0 \|",
            f"| Wilmington | other | {market_total:,} | 6 | 0 | 0 |",
            text,
            count=1,
        )
        path.write_text(text)


def seed_brunswick(county: dict | None = None, markets: list[str] | None = None) -> dict:
    if markets is None:
        catalog = json.loads(CATALOG_PATH.read_text())
        found: list[str] = []
        for market in catalog["markets"]:
            for item in market["counties"]:
                if item.get("fips") == FIPS and market["id"] not in found:
                    found.append(market["id"])
        markets = found or [MARKET]
    features, stats = build_features()
    if len(features) < 7000:
        raise RuntimeError(f"Expected about 7.6k Brunswick parcels in the 5–150 band, got {len(features)}")
    return publish(features, stats, markets)


def main() -> None:
    seed_brunswick()


if __name__ == "__main__":
    main()
