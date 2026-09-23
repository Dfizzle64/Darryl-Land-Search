"""Mecklenburg County (Charlotte MSA) parcel extract.

TaxParcel_camadata has owner, tax, situs, and last-sale fields but does not
return geometry. Outlines come from Tax/ParcelsViewer. Zoning, the latest
priced sale, and Charlotte 2040 Place Types are joined onto those outlines.
NC OneMap (cntyfips 119) is the geometry fallback.
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from parcel_geometry import esri_rings_to_geojson, geometry_contains, polygon_parts, representative_point

CACHE_DIR = Path("/tmp/dls-market-parcels/meck-37119")
ACRE_WHERE = "gisacres>=5 AND gisacres<=150"
VIEWER_URL = "https://meckags.mecklenburgcountync.gov/server/rest/services/Tax/ParcelsViewer/MapServer/0/query"
CAMA_URL = "https://meckgis.mecklenburgcountync.gov/server/rest/services/TaxParcel_camadata/MapServer/0/query"
ZONING_URL = "https://meckgis.mecklenburgcountync.gov/server/rest/services/ParcelsZoningZipcode/FeatureServer/0/query"
SALES_URL = "https://meckgis.mecklenburgcountync.gov/server/rest/services/TaxParcelSales/FeatureServer/0/query"
FLU_URL = "https://services.arcgis.com/9Nl857LBlQVyzq54/arcgis/rest/services/Charlotte_Future_2040_Policy_Map/FeatureServer/0/query"
ONEMAP_URLS = [
    "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1/query",
    "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1/query",
]
POLARIS = "https://polaris3g.mecklenburgcountync.gov/pid/{pid}"
PLACE_TYPE_GAP = (
    "Outside Charlotte 2040 Place Types. That layer is city jurisdiction only; towns are not covered."
)
WEAK_SALE = {"TEMP", "N/A", "NA"}
SKIP_CITY = {"UNINC", "UNINCORPORATED", "NONE", "NULL", "N/A"}


class MeckSourceError(RuntimeError):
    pass


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
    if not math.isfinite(parsed):
        return None
    return parsed


def zip_str(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return text[:10]


def money(value: Any) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def person_name(last: Any, first: Any) -> str | None:
    last_s = clean(last)
    first_s = clean(first)
    if last_s and first_s:
        return f"{last_s} {first_s}"
    return last_s or first_s


def epoch_to_iso(value: Any) -> str | None:
    text = clean(value)
    if text and len(text) >= 10 and text[4] == "-" and text[:4].isdigit():
        return text[:10]
    parsed = num(value)
    if parsed is None:
        return None
    if parsed > 10_000_000_000:
        parsed = parsed / 1000.0
    if parsed < 100_000_000 or parsed > 4_000_000_000:
        return None
    return time.strftime("%Y-%m-%d", time.gmtime(parsed))


def pick_sale(rows: list[dict]) -> dict | None:
    """Latest positive-price sale, then any non-temporary row, then the newest row."""
    usable = [row for row in rows if row]
    if not usable:
        return None

    def rank(row: dict) -> tuple:
        price = num(row.get("saleprice")) or 0
        when = num(row.get("saledate")) or 0
        if when > 10_000_000_000:
            when = when / 1000.0
        validity = (clean(row.get("salesvalidity")) or "").upper()
        return (1 if price > 0 else 0, 0 if validity in WEAK_SALE else 1, when)

    return max(usable, key=rank)


def situs_city(*candidates: Any) -> str | None:
    for candidate in candidates:
        text = clean(candidate)
        if text and text.upper() not in SKIP_CITY:
            return text
    return None


def situs_line(number: Any, street: Any, address: Any) -> str | None:
    number_s = clean(number)
    street_s = clean(street)
    if number_s and street_s:
        return f"{number_s} {street_s}"
    return clean(address)


def combine_zones(codes: list[str]) -> str | None:
    unique = sorted({code for code in (clean(item) for item in codes) if code})
    if not unique:
        return None
    return " / ".join(unique)


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    body = urllib.parse.urlencode(params or {}).encode()
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "User-Agent": "darryl-land-search/market-parcels",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:160]}: {last}")


def fetch_ids(url: str, where: str) -> list[int]:
    data = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    return [int(item) for item in (data.get("objectIds") or [])]


def _query_ids(url: str, ids: list[int], fields: list[str], geometry: bool) -> list[dict]:
    if not ids:
        return []
    data = fetch_json(
        url,
        {
            "objectIds": ",".join(str(item) for item in ids),
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "outSR": "4326",
            "f": "json",
        },
        timeout=180,
    )
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    features = data.get("features") or []
    if geometry and features and "geometry" not in features[0]:
        raise RuntimeError(f"{url} returned attributes without geometry")
    if len(features) >= 2000 and len(ids) > 8:
        raise RuntimeError("page hit max record count")
    return features


def fetch_by_object_ids(
    url: str,
    ids: list[int],
    fields: list[str],
    *,
    geometry: bool,
    batch: int,
    workers: int = 4,
) -> list[dict]:
    if not ids:
        return []

    def pull(chunk: list[int]) -> list[dict]:
        try:
            return _query_ids(url, chunk, fields, geometry)
        except RuntimeError:
            if len(chunk) <= 8:
                raise
            mid = len(chunk) // 2
            return pull(chunk[:mid]) + pull(chunk[mid:])

    chunks = [ids[index : index + batch] for index in range(0, len(ids), batch)]
    features: list[dict] = []
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(chunks)))) as pool:
        futures = [pool.submit(pull, chunk) for chunk in chunks]
        for future in as_completed(futures):
            rows = future.result()
            features.extend(rows)
            done += 1
            if done == 1 or done == len(chunks) or done % 8 == 0:
                print(f"    {done}/{len(chunks)} batches", flush=True)
    return features


def load_layer(
    name: str,
    url: str,
    where: str,
    fields: list[str],
    *,
    geometry: bool,
    batch: int,
    ignore_cache: bool,
) -> list[dict]:
    path = CACHE_DIR / f"{name}.json"
    if path.exists() and not ignore_cache:
        cached = json.loads(path.read_text())
        print(f"  cache {name} ({len(cached)} rows)", flush=True)
        return cached
    print(f"  query {name}", flush=True)
    ids = fetch_ids(url, where)
    print(f"    {len(ids)} ids", flush=True)
    rows = fetch_by_object_ids(url, ids, fields, geometry=geometry, batch=batch)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, separators=(",", ":")))
    return rows


def _geometry_of(item: dict) -> dict | None:
    geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
    if not geometry:
        return None
    center = representative_point(geometry)
    if not center:
        return None
    lon, lat = center
    if not (-81.6 < lon < -80.3 and 34.9 < lat < 35.6):
        return None
    return geometry


def _merge_geometry(left: dict, right: dict) -> dict:
    def parts(geometry: dict) -> list:
        if geometry.get("type") == "Polygon":
            return [geometry["coordinates"]]
        return list(geometry.get("coordinates") or [])

    coords = parts(left) + parts(right)
    if len(coords) == 1:
        return {"type": "Polygon", "coordinates": coords[0]}
    return {"type": "MultiPolygon", "coordinates": coords}


def outlines_from_viewer(raw: list[dict]) -> list[dict]:
    by_pin: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        pin = clean(attrs.get("nc_pin"))
        geometry = _geometry_of(item)
        acres = num(attrs.get("gisacres"))
        if not pin or not geometry or acres is None:
            continue
        row = {
            "pin": pin,
            "pid": clean(attrs.get("pid")),
            "acres": acres,
            "geometry": geometry,
            "onemap": False,
        }
        previous = by_pin.get(pin)
        if previous is None:
            by_pin[pin] = row
            continue
        if abs(previous["acres"] - acres) <= 0.05:
            prev_pts = json.dumps(previous["geometry"]).__len__()
            next_pts = json.dumps(geometry).__len__()
            if next_pts > prev_pts:
                by_pin[pin] = row
            continue
        previous["geometry"] = _merge_geometry(previous["geometry"], geometry)
        previous["acres"] = max(previous["acres"], acres)
    return list(by_pin.values())


def outlines_from_onemap(raw: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        parno = clean(attrs.get("parno"))
        geometry = _geometry_of(item)
        acres = num(attrs.get("gisacres"))
        if not parno or not geometry or acres is None:
            continue
        row = {
            "pin": None,
            "pid": None,
            "parno": parno,
            "acres": acres,
            "geometry": geometry,
            "onemap": True,
            "ownname": clean(attrs.get("ownname")),
            "siteadd": clean(attrs.get("siteadd")),
            "scity": clean(attrs.get("scity")),
            "parval": attrs.get("parval"),
            "landval": attrs.get("landval"),
            "saledate": attrs.get("saledate") or attrs.get("saledatetx"),
            "mailadd": clean(attrs.get("mailadd")),
            "mcity": clean(attrs.get("mcity")),
            "mstate": clean(attrs.get("mstate")),
            "mzip": attrs.get("mzip"),
        }
        previous = by_id.get(parno)
        if previous is None or acres > previous["acres"]:
            by_id[parno] = row
    return list(by_id.values())


def index_cama(raw: list[dict]) -> dict[str, dict]:
    """Best tax account per nc_pin, plus pid and parcelid aliases."""
    by_pin: dict[str, dict] = {}

    def rank(attrs: dict) -> tuple:
        flag = num(attrs.get("condo_town_flag"))
        standard = 1 if flag == 0 else 0
        return (standard, num(attrs.get("totlandval")) or 0, num(attrs.get("saleprice")) or 0)

    for item in raw:
        attrs = item.get("attributes") or {}
        pin = clean(attrs.get("nc_pin"))
        if not pin:
            continue
        current = by_pin.get(pin)
        if current is None or rank(attrs) > rank(current):
            by_pin[pin] = attrs
    by_pid: dict[str, dict] = {}
    by_parcelid: dict[str, dict] = {}
    for attrs in by_pin.values():
        pid = clean(attrs.get("pid"))
        parcelid = clean(attrs.get("parcelid"))
        if pid:
            by_pid[pid] = attrs
        if parcelid:
            by_parcelid[parcelid] = attrs
    return {"by_pin": by_pin, "by_pid": by_pid, "by_parcelid": by_parcelid, "rows": len(raw), "pins": len(by_pin)}


def lookup_cama(index: dict, outline: dict) -> dict | None:
    pin = outline.get("pin")
    if pin and pin in index["by_pin"]:
        return index["by_pin"][pin]
    for key in (outline.get("pid"), outline.get("parno")):
        if key and key in index["by_pid"]:
            return index["by_pid"][key]
        if key and key in index["by_parcelid"]:
            return index["by_parcelid"][key]
    return None


def index_zones(raw: list[dict]) -> dict[str, dict]:
    grouped: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        pin = clean(attrs.get("nc_pin"))
        code = clean(attrs.get("zone_class"))
        if not pin:
            continue
        slot = grouped.setdefault(pin, {"codes": [], "zip": None, "po": None, "pid": None})
        if code and code not in slot["codes"]:
            slot["codes"].append(code)
        if not slot["zip"]:
            slot["zip"] = zip_str(attrs.get("zip"))
        if not slot["po"]:
            slot["po"] = clean(attrs.get("po_name"))
        if not slot["pid"]:
            slot["pid"] = clean(attrs.get("pid"))
    return grouped


def fetch_sales(parcel_ids: list[str], ignore_cache: bool) -> dict[str, list[dict]]:
    path = CACHE_DIR / "sales.json"
    if path.exists() and not ignore_cache:
        cached = json.loads(path.read_text())
        print(f"  cache sales ({len(cached)} parcel ids)", flush=True)
        return cached
    unique = sorted({clean(item) for item in parcel_ids if clean(item)})
    print(f"  query sales for {len(unique)} parcel ids", flush=True)
    found: dict[str, list[dict]] = defaultdict(list)

    def pull(chunk: list[str]) -> list[dict]:
        quoted = ",".join("'" + item.replace("'", "''") + "'" for item in chunk)
        data = fetch_json(
            SALES_URL,
            {
                "where": f"parcelid IN ({quoted})",
                "outFields": "parcelid,saledate,saleprice,salesvalidity",
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            if len(chunk) == 1:
                raise RuntimeError(json.dumps(data["error"])[:240])
            mid = len(chunk) // 2
            return pull(chunk[:mid]) + pull(chunk[mid:])
        features = data.get("features") or []
        if len(features) >= 2000 and len(chunk) > 1:
            mid = len(chunk) // 2
            return pull(chunk[:mid]) + pull(chunk[mid:])
        return features

    chunks = [unique[index : index + 40] for index in range(0, len(unique), 40)]
    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(pull, chunk) for chunk in chunks]
        for future in as_completed(futures):
            for item in future.result():
                attrs = item.get("attributes") or {}
                parcelid = clean(attrs.get("parcelid"))
                if parcelid:
                    found[parcelid].append(attrs)
            done += 1
            if done == 1 or done == len(chunks) or done % 20 == 0:
                print(f"    sales {done}/{len(chunks)}", flush=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(found, separators=(",", ":")))
    return found


def _bbox(geometry: dict) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for poly in polygon_parts(geometry):
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def place_type_index(raw: list[dict]) -> list[dict]:
    polys = []
    for item in raw:
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        if not geometry:
            continue
        attrs = item.get("attributes") or {}
        code = clean(attrs.get("PlaceTypeCde"))
        label = clean(attrs.get("PlaceTypeFullTxt"))
        if not code and not label:
            continue
        minx, miny, maxx, maxy = _bbox(geometry)
        polys.append(
            {
                "code": code,
                "label": label,
                "geometry": geometry,
                "bbox": [minx, miny, maxx, maxy],
                "area": (maxx - minx) * (maxy - miny),
            }
        )
    return polys


def flu_grid(polys: list[dict]) -> dict[tuple[int, int], list[dict]]:
    cell = 0.05
    grid: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for poly in polys:
        minx, miny, maxx, maxy = poly["bbox"]
        for ix in range(math.floor(minx / cell), math.floor(maxx / cell) + 1):
            for iy in range(math.floor(miny / cell), math.floor(maxy / cell) + 1):
                grid[(ix, iy)].append(poly)
    return grid


def flu_at(grid: dict[tuple[int, int], list[dict]], geometry: dict, center: tuple[float, float]) -> dict | None:
    if not grid:
        return None
    points = [center]
    parts = polygon_parts(geometry)
    if parts and parts[0] and parts[0][0]:
        ring = parts[0][0]
        step = max(1, len(ring) // 4)
        points.extend((point[0], point[1]) for point in ring[::step][:4])
    cell = 0.05
    hits: list[dict] = []
    seen: set[int] = set()
    for lon, lat in points:
        ix = math.floor(lon / cell)
        iy = math.floor(lat / cell)
        for poly in grid.get((ix, iy), []):
            ident = id(poly)
            if ident in seen:
                continue
            if geometry_contains(poly["geometry"], lon, lat):
                seen.add(ident)
                hits.append(poly)
        if hits:
            break
    if not hits:
        return None
    chosen = min(hits, key=lambda poly: poly["area"])
    return {
        "code": chosen["code"],
        "label": chosen["label"],
        "jurisdiction": "Charlotte",
        "source": "Charlotte Future 2040 Policy Map",
    }


def _load_outlines(ignore_cache: bool) -> tuple[list[dict], str, str | None]:
    errors: list[str] = []
    try:
        raw = load_layer(
            "viewer",
            VIEWER_URL,
            ACRE_WHERE,
            ["nc_pin", "pid", "gisacres"],
            geometry=True,
            batch=50,
            ignore_cache=ignore_cache,
        )
        outlines = outlines_from_viewer(raw)
        if outlines:
            return outlines, "parcels-viewer", None
        errors.append("ParcelsViewer returned no usable polygons")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"ParcelsViewer failed ({exc})")
    last = errors[-1]
    for url in ONEMAP_URLS:
        try:
            raw = load_layer(
                "onemap-" + ("feature" if "FeatureServer" in url else "map"),
                url,
                "cntyfips='119' AND gisacres>=5 AND gisacres<=150",
                ["parno", "ownname", "siteadd", "scity", "gisacres", "parval", "landval", "saledate", "saledatetx", "mailadd", "mcity", "mstate", "mzip"],
                geometry=True,
                batch=80,
                ignore_cache=ignore_cache,
            )
            outlines = outlines_from_onemap(raw)
            if outlines:
                return outlines, "nc-onemap", last
        except Exception as exc:  # noqa: BLE001
            last = f"{last}; NC OneMap failed ({exc})"
    raise MeckSourceError(last)


def _optional(label: str, loader: Callable[[], Any]) -> tuple[Any, str | None]:
    try:
        return loader(), None
    except Exception as exc:  # noqa: BLE001
        print(f"  {label} failed: {exc}", flush=True)
        return None, str(exc)


def build_mecklenburg_features(markets: list[str], ignore_cache: bool = False) -> tuple[list[dict], dict]:
    import seed_market_parcels as parcels

    outlines, geometry_source, geometry_error = _load_outlines(ignore_cache)
    print(f"  {len(outlines)} outlines via {geometry_source}", flush=True)

    cama_raw, cama_error = _optional(
        "cama",
        lambda: load_layer(
            "cama",
            CAMA_URL,
            ACRE_WHERE,
            [
                "pid",
                "nc_pin",
                "parcelid",
                "gisacres",
                "condo_town_flag",
                "ownrlstnme",
                "ownrfrstnme",
                "ownr2lstnme",
                "ownr2frstnme",
                "mailaddr1",
                "mailaddr2",
                "zipcode",
                "state",
                "address",
                "streetnumber",
                "streetname",
                "loccity",
                "city",
                "saledate",
                "saleprice",
                "validsale",
                "totlandval",
                "totalvalue",
                "totmarkval",
            ],
            geometry=False,
            batch=400,
            ignore_cache=ignore_cache,
        ),
    )
    cama_index = index_cama(cama_raw or [])
    zones_raw, zoning_error = _optional(
        "zoning",
        lambda: load_layer(
            "zoning",
            ZONING_URL,
            ACRE_WHERE,
            ["nc_pin", "pid", "zone_class", "zip", "po_name"],
            geometry=False,
            batch=500,
            ignore_cache=ignore_cache,
        ),
    )
    zones = index_zones(zones_raw or [])

    parcel_ids = []
    for outline in outlines:
        account = lookup_cama(cama_index, outline)
        if account:
            parcel_ids.append(account.get("parcelid"))
    sales: dict[str, list[dict]] = {}
    sales_error = None
    if parcel_ids:
        try:
            sales = fetch_sales(parcel_ids, ignore_cache)
        except Exception as exc:  # noqa: BLE001
            sales_error = str(exc)
            print(f"  sales failed: {exc}", flush=True)

    flu_raw, flu_error = _optional(
        "place types",
        lambda: load_layer(
            "place-types",
            FLU_URL,
            "1=1",
            ["PlaceTypeFullTxt", "PlaceTypeCde"],
            geometry=True,
            batch=100,
            ignore_cache=ignore_cache,
        ),
    )
    place_types = place_type_index(flu_raw or [])
    place_grid = flu_grid(place_types)
    print(f"  {len(place_types)} place type polygons", flush=True)

    by_id: dict[str, dict] = {}
    stats = {
        "cama_joined": 0,
        "zoned": 0,
        "flu": 0,
        "sales_priced": 0,
        "cama_sale_only": 0,
        "owners": 0,
    }
    for outline in outlines:
        account = lookup_cama(cama_index, outline)
        pin = clean((account or {}).get("nc_pin")) or outline.get("pin")
        pid = clean((account or {}).get("pid")) or outline.get("pid") or (zones.get(pin) or {}).get("pid")
        parcel_id = pin or pid or outline.get("parno")
        if not parcel_id:
            continue
        acres = num(outline.get("acres"))
        if not parcels.in_band(acres):
            continue
        geometry = outline["geometry"]
        center = representative_point(geometry)
        if not center or not parcels.plausible_centroid(center):
            continue
        zone = zones.get(pin or "") or {}
        zone_code = combine_zones(zone.get("codes") or [])
        sale_rows: list[dict] = []
        parcelid = clean((account or {}).get("parcelid"))
        if parcelid:
            for row in sales.get(parcelid) or []:
                tagged = dict(row)
                tagged["_from"] = "sales"
                sale_rows.append(tagged)
        if account:
            sale_rows.append(
                {
                    "saledate": account.get("saledate"),
                    "saleprice": account.get("saleprice"),
                    "salesvalidity": account.get("validsale"),
                    "_from": "cama",
                }
            )
        elif outline.get("onemap") and outline.get("saledate"):
            sale_rows.append({"saledate": outline.get("saledate"), "saleprice": None, "salesvalidity": None, "_from": "onemap"})
        best = pick_sale(sale_rows)
        price = money((best or {}).get("saleprice"))
        sale_on = epoch_to_iso((best or {}).get("saledate")) if best else None
        qualified = clean((best or {}).get("salesvalidity")) if best else None
        if best and best.get("_from") == "sales" and price is not None:
            stats["sales_priced"] += 1
        elif best and best.get("_from") == "cama" and (price is not None or sale_on):
            stats["cama_sale_only"] += 1
        flu = flu_at(place_grid, geometry, center) if not flu_error else None
        gaps: list[str] = []
        if account is None:
            gaps.append("No TaxParcel_camadata account matched this PIN.")
        if not zone_code:
            gaps.append("No zone_class on ParcelsZoningZipcode for this PIN.")
        if flu is None:
            gaps.append(PLACE_TYPE_GAP)
        if account:
            owner = person_name(account.get("ownrlstnme"), account.get("ownrfrstnme"))
            owner2 = person_name(account.get("ownr2lstnme"), account.get("ownr2frstnme"))
            situs = situs_line(account.get("streetnumber"), account.get("streetname"), account.get("address"))
            city = situs_city(account.get("loccity"), account.get("city"), zone.get("po"))
            mail1 = clean(account.get("mailaddr1"))
            mail2 = clean(account.get("mailaddr2"))
            mail_state = clean(account.get("state"))
            mail_zip = zip_str(account.get("zipcode"))
            market_value = money(account.get("totmarkval"))
            assessed = money(account.get("totalvalue"))
            stats["cama_joined"] += 1
        else:
            owner = outline.get("ownname")
            owner2 = None
            situs = outline.get("siteadd")
            city = situs_city(outline.get("scity"), zone.get("po"))
            mail1 = outline.get("mailadd")
            mail2 = None
            mail_state = clean(outline.get("mstate"))
            mail_zip = zip_str(outline.get("mzip"))
            market_value = money(outline.get("parval"))
            assessed = money(outline.get("landval"))
        if owner:
            stats["owners"] += 1
        if zone_code:
            stats["zoned"] += 1
        if flu:
            stats["flu"] += 1
        feature = parcels.empty_feature(
            fips="37119",
            county="Mecklenburg",
            state="North Carolina",
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source="meck-taxparcel-camadata-37119" if geometry_source == "parcels-viewer" else "meck-taxparcel-camadata-37119+nc-onemap",
            owner=owner,
            owner2=owner2,
            situs=situs,
            city=city,
            zip_code=zone.get("zip") or zip_str(outline.get("mzip")),
            zoning=zone_code,
            sale_price=price,
            sale_date=sale_on,
            sale_qualified=qualified,
            market_value=market_value,
            assessed=assessed,
            mail1=mail1,
            mail2=mail2,
            mail_state=mail_state,
            mail_zip=mail_zip,
            appraiser_url=POLARIS.format(pid=urllib.parse.quote(pid)) if pid else None,
            flu=flu,
            data_gaps=gaps,
        )
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature

    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    kept = len(features)
    cama_rows = cama_index["rows"]
    gaps = [
        (
            f"{cama_rows} TaxParcel_camadata rows with gisacres 5–150 collapse onto {kept} parcel outlines "
            f"({stats['cama_joined']} joined to owner, tax, and sale; {cama_index['pins']} unique nc_pin values in that account pull). "
            "Condo and townhouse accounts that share an nc_pin are one polygon."
        ),
        (
            "Outlines are Mecklenburg Tax/ParcelsViewer polygons. TaxParcel_camadata does not return geometry."
            if geometry_source == "parcels-viewer"
            else f"County parcel polygons were unavailable ({geometry_error}). Outlines fell back to NC OneMap where cntyfips='119'."
        ),
        (
            f"zone_class joined from ParcelsZoningZipcode for {stats['zoned']} of {kept} parcels. "
            "There is no single countywide zoning service. Charlotte zoning polygons do not cover Cornelius, Davidson, "
            "Huntersville, Matthews, Mint Hill, Pineville, or Stallings. Town codes are stored only when this parcel join published them. "
            "Split zones are combined on zoningCode."
        ),
        (
            f"Charlotte 2040 Place Types joined for {stats['flu']} of {kept} parcels. "
            "The rest are outside that city layer, which does not cover Mecklenburg towns. "
            "The legacy area-plan future land use overlay is not used as current policy."
        ),
        (
            f"TaxParcelSales supplied the latest positive-price sale for {stats['sales_priced']} parcels. "
            f"CAMA saledate/saleprice fills the drawer for {stats['cama_sale_only']} other parcels. "
            "The full sale history (about 1.6 million rows) is not stored. Grantor and grantee are not copied."
        ),
        (
            "gisacres is GIS acreage, not deed acreage. Owner phones and emails are not on these public layers and are not scraped. "
            "POLARIS links use pid: https://polaris3g.mecklenburgcountync.gov/pid/{pid}."
        ),
    ]
    if cama_error:
        gaps.append(f"TaxParcel_camadata join failed ({cama_error}). Owner, tax, and CAMA sale were left empty where OneMap had no substitute.")
    if zoning_error:
        gaps.append(f"ParcelsZoningZipcode join failed ({zoning_error}). Zoning codes were left empty.")
    if sales_error:
        gaps.append(f"TaxParcelSales join failed ({sales_error}). Last sale is the CAMA saledate/saleprice only.")
    if flu_error:
        gaps.append(f"Charlotte 2040 Place Types join failed ({flu_error}). Future land use was left empty.")
    return features, {
        "gaps": gaps,
        "geometrySource": geometry_source,
        "sourceCount": cama_rows or len(outlines),
        "dropped": max((cama_rows or len(outlines)) - kept, 0),
        "stats": stats,
    }


def _self_check() -> None:
    assert person_name("ZIMMERMANN", "MARGARET U F") == "ZIMMERMANN MARGARET U F"
    assert person_name("ACME LLC", None) == "ACME LLC"
    assert epoch_to_iso(1501214400000) == "2017-07-28"
    assert epoch_to_iso("2017-07-28T00:00:00") == "2017-07-28"
    assert money(0) is None
    assert money(200000) == 200000
    assert situs_city("UNINC", "HUNTERSVILLE") == "HUNTERSVILLE"
    assert situs_line("16101", "MCAULEY RD", "16101 MCAULEY RD UNINC NC") == "16101 MCAULEY RD"
    assert combine_zones(["N1-A", "INST(CD)", "N1-A"]) == "INST(CD) / N1-A"
    chosen = pick_sale(
        [
            {"saledate": 1112587200000, "saleprice": 0, "salesvalidity": "X", "_from": "cama"},
            {"saledate": 1404792000000, "saleprice": 0, "salesvalidity": "C", "_from": "sales"},
            {"saledate": 1501214400000, "saleprice": 200000, "salesvalidity": " ", "_from": "sales"},
        ]
    )
    assert chosen is not None
    assert chosen["saleprice"] == 200000
    assert combine_zones([]) is None
    print("mecklenburg parcel self-check ok")


if __name__ == "__main__":
    _self_check()
