"""Cobb County, Georgia (FIPS 13067) joins for the 5–150 acre market extract.

Parcels stay on the county tax-assessor daily layer. Zoning, future land use,
and qualified sales are public GIS joins. Municipalities are first-class.
Acworth and Austell have no public zoning/FLU service and stay blank.

Lookalikes are refused before a download: Smyrna, Tennessee; City of Boulder
(cob.org); Sampson County, North Carolina and Orange County, Virginia
federated layers; Athens-Clarke County. An archived Smyrna, Georgia
Opportunity Zone layer is not a designated QOZ and is not joined.
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from parcel_geometry import esri_rings_to_geojson, polygon_parts

# Padded around the tax-assessor parcel extent (-84.741, 33.743, -84.374, 34.082).
COBB_EXTENT = (-84.80, 33.70, -84.32, 34.15)

PARCEL_QUERY = (
    "https://gis.cobbcounty.gov/gisserver/rest/services/tax/taxassessorsdaily/MapServer/0/query"
)
SALES_QUERY = (
    "https://gis.cobbcounty.gov/gisserver/rest/services/tax/taxassessorsmapwm/MapServer/41/query"
)
ZONING_QUERY = (
    "https://gis.cobbcounty.gov/gisserver/rest/services/comdev/CobbZoningData/MapServer/6/query"
)
FLU_QUERY = (
    "https://gis.cobbcounty.gov/gisserver/rest/services/comdev/Future_Land_Use/FeatureServer/0/query"
)
CITY_LIMIT_QUERY = (
    "https://gis.cobbcounty.gov/gisserver/rest/services/comdev/City_Limit/MapServer/3/query"
)
MARIETTA_QUERY = (
    "https://services2.arcgis.com/OKqf9cl3ItPM5Rid/arcgis/rest/services/vZoning/FeatureServer/31/query"
)
SMYRNA_ZONING_QUERY = (
    "https://services2.arcgis.com/hE9igMm8RoNeQRbh/arcgis/rest/services/Zoning_Overlay/FeatureServer/23/query"
)
SMYRNA_FLU_QUERY = (
    "https://services2.arcgis.com/hE9igMm8RoNeQRbh/arcgis/rest/services/Future_Land_Use_Overlay/FeatureServer/24/query"
)
KENNESAW_ZONING_QUERY = (
    "https://services2.arcgis.com/XwGh5SYpBlXQGJEB/arcgis/rest/services/Zoning_Polygons/FeatureServer/1/query"
)
KENNESAW_FLU_QUERY = (
    "https://services2.arcgis.com/XwGh5SYpBlXQGJEB/arcgis/rest/services/Future_Land_Use/FeatureServer/23/query"
)
POWDER_ZONING_QUERY = (
    "https://services6.arcgis.com/hpvhAmRP1z50gTbO/ArcGIS/rest/services/Zoning/FeatureServer/0/query"
)
POWDER_FLU_QUERY = (
    "https://services6.arcgis.com/hpvhAmRP1z50gTbO/ArcGIS/rest/services/Character_Areas_(FLU_2022)/FeatureServer/0/query"
)

# Codes that are not a district. Smyrna draws unincorporated Cobb and ROW on the
# city overlay. Kennesaw tags county and utility polygons the same way.
SKIP_ZONING = {"", "ROW", "COBB", "COUNTY", "UTILITY", "NONE", "NULL"}
SKIP_FLU = {"", "ROW", "NONE", "NULL", "COBB"}

COUNTY_ZONING_CITIES = {"Unincorporated", "Mableton"}
APPRAISER_URL = "https://www.cobbcounty.gov/tax-assessor"
SOURCE = "ga-cobb-taxassessorsdaily"


def squash(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def rejection_for(url: str, extent: tuple[float | None, float | None, float | None, float | None] | None) -> str | None:
    """Refuse a layer that is not Cobb County, Georgia.

    Host checks run first so a mis-projected lookalike cannot slip through.
    Extent checks catch the same places when the host name is unfamiliar.
    """
    host = (url or "").lower()
    if any(token in host for token in ("smyrnatn", "smyrna-tn", "smyrna_tn", "cityofsmyrna.tn")):
        return "Smyrna, Tennessee is not the City of Smyrna, Georgia. Not joined."
    if "cob.org" in host or "bouldercolorado.gov" in host or "bouldercounty.gov" in host:
        return "City of Boulder (cob.org) is not Cobb County, Georgia. Not joined."
    if "sampson" in host:
        return "Sampson County, North Carolina is not Cobb County, Georgia. Not joined."
    if any(token in host for token in ("orangecountyva", "orange-va", "orange_va", "orangecova.gov")):
        return "Orange County, Virginia is not Cobb County, Georgia. Not joined."
    if any(token in host for token in ("accgov", "athensclarke", "athens-clarke", "athensclarkecounty")):
        return "Athens-Clarke County is not Cobb County, Georgia. Not joined."
    if extent is None:
        return "layer returned no WGS84 extent"
    west, south, east, north = extent
    if west is None or south is None or east is None or north is None:
        return "layer returned no WGS84 extent"
    if north < 32.2:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} is south of Georgia. Not joined."
        )
    cx = (west + east) / 2
    cy = (south + north) / 2
    if cx < -100:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} is in the Mountain West "
            "(Boulder / cob.org is not Cobb County, Georgia). Not joined."
        )
    if cy > 35.4 and -90.5 < cx < -85.2:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} is middle Tennessee "
            "(Smyrna, TN is not Smyrna, GA). Not joined."
        )
    if cx > -80 and cy > 36:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} is in Virginia "
            "(Orange County, VA is not Cobb County). Not joined."
        )
    if -78.9 < cx < -77.7 and 34.4 < cy < 35.4:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} is Sampson County, North Carolina, "
            "not Cobb County, Georgia. Not joined."
        )
    if cx > -83.7 and 33.7 < cy < 34.2:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} is east of Cobb "
            "(Athens-Clarke lookalike). Not joined."
        )
    cw, cs, ce, cn = COBB_EXTENT
    if east < cw or west > ce or north < cs or south > cn:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} does not intersect "
            "Cobb County, Georgia. Not joined."
        )
    return None


def esri_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        stamp = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(stamp):
        return None
    if stamp > 10_000_000_000:
        stamp /= 1000.0
    if stamp < 1_000_000_000:
        return None
    try:
        parsed = datetime.fromtimestamp(stamp, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    if parsed.year < 1900 or parsed.year > 2100:
        return None
    return parsed.strftime("%Y-%m-%d")


def _fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/cobb-ga"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:180]}: {last}")


def _extent(url: str, where: str = "1=1") -> tuple[float | None, float | None, float | None, float | None]:
    data = _fetch_json(url, {"where": where, "returnExtentOnly": "true", "outSR": "4326", "f": "json"})
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:240])
    extent = data.get("extent") or {}
    return extent.get("xmin"), extent.get("ymin"), extent.get("xmax"), extent.get("ymax")


def _object_ids(url: str, where: str) -> list[int]:
    data = _fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"})
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:240])
    return [int(i) for i in (data.get("objectIds") or [])]


def _point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geometry(x: float, y: float, geometry: dict) -> bool:
    for poly in polygon_parts(geometry):
        if not poly or not _point_in_ring(x, y, poly[0]):
            continue
        if any(_point_in_ring(x, y, hole) for hole in poly[1:]):
            continue
        return True
    return False


def _bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, (int, float)):
            return
        if node and isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        for item in node:
            walk(item)

    walk(geometry.get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


class _GridIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = {}
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        box = _bbox(feature["geometry"])
        if not box:
            return
        west, south, east, north = box
        feature["_bboxArea"] = max(0.0, (east - west) * (north - south))
        ix0, iy0 = math.floor(west / self.cell), math.floor(south / self.cell)
        ix1, iy1 = math.floor(east / self.cell), math.floor(north / self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 80:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets.setdefault((ix, iy), []).append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        ix, iy = math.floor(x / self.cell), math.floor(y / self.cell)
        found: list[dict] = []
        for feature in self.buckets.get((ix, iy), []):
            if _point_in_geometry(x, y, feature["geometry"]):
                found.append(feature)
        for feature in self.broad:
            if _point_in_geometry(x, y, feature["geometry"]):
                found.append(feature)
        if not found:
            return None
        found.sort(key=lambda item: item.get("_bboxArea") or 0)
        return found[0]


def _load_polygons(url: str, where: str, fields: list[str]) -> list[dict]:
    ids = _object_ids(url, where)
    features: list[dict] = []
    batch = 80
    total = len(ids)
    print(f"  overlay {total} {url.split('/rest/services/')[-1][:88]}", flush=True)
    for start in range(0, total, batch):
        chunk = ids[start : start + batch]
        params = {
            "objectIds": ",".join(str(i) for i in chunk),
            "outFields": ",".join(fields),
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        }
        try:
            data = _fetch_json(url, params)
        except RuntimeError:
            if len(chunk) > 20:
                mid = len(chunk) // 2
                features.extend(_load_polygons_ids(url, chunk[:mid], fields))
                features.extend(_load_polygons_ids(url, chunk[mid:], fields))
                continue
            raise
        if data.get("error"):
            if len(chunk) > 20:
                mid = len(chunk) // 2
                features.extend(_load_polygons_ids(url, chunk[:mid], fields))
                features.extend(_load_polygons_ids(url, chunk[mid:], fields))
                continue
            raise RuntimeError(json.dumps(data["error"])[:240])
        for item in data.get("features") or []:
            rings = (item.get("geometry") or {}).get("rings")
            if not rings:
                continue
            geom = esri_rings_to_geojson(rings)
            if not geom:
                continue
            features.append({"geometry": geom, "properties": item.get("attributes") or {}})
        done = min(start + len(chunk), total)
        if done == total or done % 800 == 0:
            print(f"    overlay {done}/{total}", flush=True)
        time.sleep(0.04)
    return features


def _load_polygons_ids(url: str, ids: list[int], fields: list[str]) -> list[dict]:
    if not ids:
        return []
    params = {
        "objectIds": ",".join(str(i) for i in ids),
        "outFields": ",".join(fields),
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
    }
    data = _fetch_json(url, params)
    if data.get("error"):
        if len(ids) > 10:
            mid = len(ids) // 2
            return _load_polygons_ids(url, ids[:mid], fields) + _load_polygons_ids(url, ids[mid:], fields)
        raise RuntimeError(json.dumps(data["error"])[:240])
    features: list[dict] = []
    for item in data.get("features") or []:
        rings = (item.get("geometry") or {}).get("rings")
        if not rings:
            continue
        geom = esri_rings_to_geojson(rings)
        if not geom:
            continue
        features.append({"geometry": geom, "properties": item.get("attributes") or {}})
    return features


def _guarded_polygons(label: str, url: str, where: str, fields: list[str], notes: list[str]) -> list[dict] | None:
    try:
        extent = _extent(url, where)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"{label} was not joined: {exc}")
        print(f"  skip {label}: {exc}", flush=True)
        return None
    problem = rejection_for(url, extent)
    if problem:
        notes.append(f"{label}: {problem}")
        print(f"  skip {label}: {problem}", flush=True)
        return None
    try:
        polygons = _load_polygons(url, where, fields)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"{label} was not joined: {exc}")
        print(f"  overlay failed {label}: {exc}", flush=True)
        return None
    west, south, east, north = extent
    print(f"  {label} extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} polygons {len(polygons)}", flush=True)
    return polygons


def _index(polygons: list[dict]) -> _GridIndex:
    index = _GridIndex()
    for feature in polygons:
        index.add(feature)
    return index


def _city_label(name: str) -> str:
    if name == "Unincorporated":
        return "Unincorporated Cobb"
    return name


def _assign_cities(features: list[dict], limits: list[dict]) -> dict[str, int]:
    index = _index(limits)
    counts: dict[str, int] = {}
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        hit = index.hit(lon, lat)
        name = squash((hit or {}).get("properties", {}).get("NAME")) if hit else None
        if not name:
            name = "Unincorporated"
        feature["properties"]["_cobbCity"] = name
        label = _city_label(name)
        feature["properties"]["jurisdictionCode"] = label
        if name != "Unincorporated":
            feature["properties"]["situsCity"] = name
        counts[name] = counts.get(name, 0) + 1
    return counts


def _set_zoning(feature: dict, code: str | None, city_label: str, skip: set[str]) -> bool:
    text = squash(code)
    if not text or text.upper() in skip:
        return False
    props = feature["properties"]
    props["zoningCode"] = text
    props["zoningDistrict"] = f"{city_label}:{text}"
    props["jurisdictionCode"] = city_label
    return True


def _set_flu(feature: dict, code: str | None, label: str | None, city_label: str, source: str, skip: set[str]) -> bool:
    text = squash(code)
    if not text or text.upper() in skip:
        return False
    feature["properties"]["flu"] = {
        "code": text,
        "label": squash(label) or text,
        "jurisdiction": city_label,
        "source": source,
    }
    return True


def _apply_field_layer(
    features: list[dict],
    polygons: list[dict],
    *,
    cities: set[str],
    city_label: str,
    zoning_field: str | None = None,
    flu_field: str | None = None,
    flu_label_field: str | None = None,
    zip_field: str | None = None,
    source: str,
    zoning_skip: set[str] | None = None,
    flu_skip: set[str] | None = None,
    overwrite_zoning: bool = False,
) -> tuple[int, int]:
    index = _index(polygons)
    zoning_hits = 0
    flu_hits = 0
    zskip = zoning_skip if zoning_skip is not None else SKIP_ZONING
    fskip = flu_skip if flu_skip is not None else SKIP_FLU
    for feature in features:
        props = feature["properties"]
        city_name = props.get("_cobbCity")
        if city_name not in cities:
            continue
        label = city_label or _city_label(city_name or "Unincorporated")
        lon, lat = props["centroid"]
        hit = index.hit(lon, lat)
        if not hit:
            continue
        attrs = hit["properties"]
        if zoning_field and (overwrite_zoning or not props.get("zoningCode")):
            if _set_zoning(feature, attrs.get(zoning_field), label, zskip):
                zoning_hits += 1
        if flu_field and (overwrite_zoning or not props.get("flu")):
            flu_label = attrs.get(flu_label_field) if flu_label_field else None
            if _set_flu(feature, attrs.get(flu_field), flu_label, label, source, fskip):
                flu_hits += 1
        if zip_field and not props.get("situsZip"):
            digits = "".join(ch for ch in str(attrs.get(zip_field) or "") if ch.isdigit())
            if len(digits) >= 5:
                props["situsZip"] = digits[:5]
    return zoning_hits, flu_hits


def _join_sales(features: list[dict]) -> tuple[int, str | None]:
    pins = [feature["properties"]["parcelId"] for feature in features if feature["properties"].get("parcelId")]
    latest: dict[str, tuple[str, float]] = {}
    try:
        _fetch_sales(pins, latest)
    except Exception as exc:  # noqa: BLE001
        return 0, f"ParcelSales (MapServer/41, STEB=FMV) was not joined: {exc}"
    kept = 0
    for feature in features:
        pin = feature["properties"].get("parcelId")
        row = latest.get(pin)
        if not row:
            continue
        date, price = row
        feature["properties"]["lastSale"] = {"date": date, "price": price, "qualified": "FMV"}
        kept += 1
    return kept, None


def _fetch_sales(pins: list[str], latest: dict[str, tuple[str, float]], batch: int = 30) -> None:
    for start in range(0, len(pins), batch):
        chunk = pins[start : start + batch]
        quoted = ",".join("'" + pin.replace("'", "") + "'" for pin in chunk)
        where = f"STEB='FMV' AND PRICE>0 AND PIN IN ({quoted})"
        params = {
            "where": where,
            "outFields": "PIN,SALEDT,PRICE,STEB",
            "returnGeometry": "false",
            "f": "json",
        }
        try:
            data = _fetch_json(SALES_QUERY, params)
        except RuntimeError:
            if len(chunk) > 8:
                _fetch_sales(chunk[: len(chunk) // 2], latest, batch=max(8, len(chunk) // 2))
                _fetch_sales(chunk[len(chunk) // 2 :], latest, batch=max(8, len(chunk) // 2))
                continue
            raise
        if data.get("error"):
            if len(chunk) > 8:
                _fetch_sales(chunk[: len(chunk) // 2], latest, batch=max(8, len(chunk) // 2))
                _fetch_sales(chunk[len(chunk) // 2 :], latest, batch=max(8, len(chunk) // 2))
                continue
            raise RuntimeError(json.dumps(data["error"])[:240])
        rows = data.get("features") or []
        if len(chunk) > 1 and (data.get("exceededTransferLimit") or len(rows) >= 900):
            _fetch_sales(chunk[: len(chunk) // 2], latest, batch=max(1, len(chunk) // 2))
            _fetch_sales(chunk[len(chunk) // 2 :], latest, batch=max(1, len(chunk) // 2))
            continue
        for item in rows:
            attrs = item.get("attributes") or {}
            steb = squash(attrs.get("STEB"))
            if steb != "FMV":
                continue
            pin = squash(attrs.get("PIN"))
            if not pin:
                continue
            try:
                price = float(attrs.get("PRICE"))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(price) or price <= 0:
                continue
            date = esri_date(attrs.get("SALEDT"))
            if not date:
                continue
            previous = latest.get(pin)
            if previous is None or date > previous[0] or (date == previous[0] and price > previous[1]):
                latest[pin] = (date, price)
        if start % 300 == 0:
            print(f"  sales pins {min(start + len(chunk), len(pins))}/{len(pins)}", flush=True)
        time.sleep(0.03)


def _squash_attributes(features: list[dict]) -> None:
    for feature in features:
        props = feature["properties"]
        for key in ("situsAddress", "ownerName", "ownerName2"):
            props[key] = squash(props.get(key))
        mail = props.get("mailingAddress") or {}
        for key in ("line1", "line2", "city", "state"):
            mail[key] = squash(mail.get(key))
        props["mailingAddress"] = mail


def enrich_cobb(features: list[dict]) -> list[str]:
    """Join city, zoning, FLU, and the latest qualified sale. Mutates features."""
    notes: list[str] = []
    _squash_attributes(features)
    for feature in features:
        feature["properties"]["opportunityZone"] = None
        feature["properties"]["oz2Eligibility"] = None
        feature["properties"]["appraiserUrl"] = APPRAISER_URL

    limits = _guarded_polygons(
        "Cobb city limits",
        CITY_LIMIT_QUERY,
        "1=1",
        ["NAME", "CityCode"],
        notes,
    )
    if not limits:
        notes.append(
            "City limits did not load, so municipality, city zoning, and city FLU were not assigned. "
            "Acworth and Austell remain gaps either way."
        )
        sales, sales_error = _join_sales(features)
        if sales_error:
            notes.append(sales_error)
        else:
            notes.append(f"ParcelSales STEB=FMV matched {sales} of {len(features)} parcels.")
        return notes

    counts = _assign_cities(features, limits)
    notes.append(
        "City limits (comdev/City_Limit MapServer/3): "
        + ", ".join(f"{name} {counts[name]}" for name in sorted(counts))
        + "."
    )

    county_zoning = _guarded_polygons(
        "Cobb zoning districts",
        ZONING_QUERY,
        "1=1",
        ["ZoningDistrict"],
        notes,
    )
    if county_zoning is not None:
        zoning_hits, _ = _apply_field_layer(
            features,
            county_zoning,
            cities=COUNTY_ZONING_CITIES,
            city_label="",
            zoning_field="ZoningDistrict",
            source="cobb-zoning-districts",
        )
        notes.append(
            f"CobbZoningData MapServer/6 ({len(county_zoning)} polygons) matched {zoning_hits} parcels "
            "labeled unincorporated Cobb or Mableton. Mableton centroids in this band did not intersect the layer "
            "(WGS84 extent starts near latitude 33.805), and there is no separate Mableton zoning service, so Mableton zoning stays blank."
        )

    county_flu = _guarded_polygons(
        "Cobb future land use",
        FLU_QUERY,
        "1=1",
        ["FLU_ABBR2", "FLU_DESCR2"],
        notes,
    )
    if county_flu is not None:
        _, flu_hits = _apply_field_layer(
            features,
            county_flu,
            cities=COUNTY_ZONING_CITIES,
            city_label="",
            flu_field="FLU_ABBR2",
            flu_label_field="FLU_DESCR2",
            source="cobb-future-land-use",
        )
        notes.append(
            f"Future_Land_Use FeatureServer/0 ({len(county_flu)} polygons, code FLU_ABBR2) "
            f"matched {flu_hits} unincorporated Cobb parcels. Mableton centroids did not intersect this layer, "
            "and Mableton has no city FLU service, so Mableton FLU stays blank. City FLU is a separate join."
        )

    marietta = _guarded_polygons(
        "Marietta zoning and FLU",
        MARIETTA_QUERY,
        "IN_CITY='Y'",
        ["ZONING", "FLU", "ZIP_CODE", "IN_CITY"],
        notes,
    )
    if marietta is not None:
        zoning_hits, flu_hits = _apply_field_layer(
            features,
            marietta,
            cities={"Marietta"},
            city_label="Marietta",
            zoning_field="ZONING",
            flu_field="FLU",
            zip_field="ZIP_CODE",
            source="marietta-parcels-public-view",
            overwrite_zoning=True,
        )
        notes.append(
            f"Marietta vZoning FeatureServer/31 (public parcel view, in-city) matched zoning {zoning_hits} "
            f"and FLU {flu_hits}. Marietta MapServers that were stopped or token-gated were not used."
        )

    smyrna_z = _guarded_polygons(
        "Smyrna GA zoning",
        SMYRNA_ZONING_QUERY,
        "1=1",
        ["Zoning", "Name"],
        notes,
    )
    if smyrna_z is not None:
        zoning_hits, _ = _apply_field_layer(
            features,
            smyrna_z,
            cities={"Smyrna"},
            city_label="Smyrna",
            zoning_field="Zoning",
            source="smyrna-ga-zoning-overlay",
            overwrite_zoning=True,
        )
        notes.append(
            f"Smyrna, Georgia Zoning_Overlay ({len(smyrna_z)} polygons, owner Smyrna_GA) matched {zoning_hits} parcels. "
            "Smyrna, Tennessee was not used. Codes Cobb and ROW on that overlay are not city districts. "
            "The archived Smyrna Opportunity Zone layer was not joined and is not a designated QOZ."
        )

    smyrna_f = _guarded_polygons(
        "Smyrna GA future land use",
        SMYRNA_FLU_QUERY,
        "1=1",
        ["FLU_2040", "FULM_Description"],
        notes,
    )
    if smyrna_f is not None:
        _, flu_hits = _apply_field_layer(
            features,
            smyrna_f,
            cities={"Smyrna"},
            city_label="Smyrna",
            flu_field="FLU_2040",
            flu_label_field="FULM_Description",
            source="smyrna-ga-flu-2040",
            overwrite_zoning=True,
        )
        notes.append(f"Smyrna, Georgia FLU_Overlay matched {flu_hits} parcels.")

    kennesaw_z = _guarded_polygons(
        "Kennesaw zoning",
        KENNESAW_ZONING_QUERY,
        "1=1",
        ["Zoning_1", "Classification"],
        notes,
    )
    if kennesaw_z is not None:
        zoning_hits, _ = _apply_field_layer(
            features,
            kennesaw_z,
            cities={"Kennesaw"},
            city_label="Kennesaw",
            zoning_field="Zoning_1",
            source="kennesaw-zoning-polygons",
            overwrite_zoning=True,
        )
        notes.append(
            f"Kennesaw Zoning_Polygons layer Zoning City ({len(kennesaw_z)} polygons) matched {zoning_hits} parcels. "
            "COUNTY and UTILITY labels on that layer are not districts."
        )

    kennesaw_f = _guarded_polygons(
        "Kennesaw future land use",
        KENNESAW_FLU_QUERY,
        "1=1",
        ["FLU", "FLU_Label"],
        notes,
    )
    if kennesaw_f is not None:
        _, flu_hits = _apply_field_layer(
            features,
            kennesaw_f,
            cities={"Kennesaw"},
            city_label="Kennesaw",
            flu_field="FLU",
            flu_label_field="FLU_Label",
            source="kennesaw-future-land-use",
            overwrite_zoning=True,
        )
        notes.append(f"Kennesaw Future_Land_Use matched {flu_hits} parcels.")

    powder_z = _guarded_polygons(
        "Powder Springs zoning",
        POWDER_ZONING_QUERY,
        "1=1",
        ["ZONING"],
        notes,
    )
    if powder_z is not None:
        zoning_hits, _ = _apply_field_layer(
            features,
            powder_z,
            cities={"Powder Springs"},
            city_label="Powder Springs",
            zoning_field="ZONING",
            source="powder-springs-zoning",
            overwrite_zoning=True,
        )
        notes.append(f"Powder Springs Zoning FeatureServer ({len(powder_z)} polygons) matched {zoning_hits} parcels.")

    powder_f = _guarded_polygons(
        "Powder Springs character areas",
        POWDER_FLU_QUERY,
        "1=1",
        ["F2022_CA", "Zoning"],
        notes,
    )
    if powder_f is not None:
        _, flu_hits = _apply_field_layer(
            features,
            powder_f,
            cities={"Powder Springs"},
            city_label="Powder Springs",
            flu_field="F2022_CA",
            source="powder-springs-character-area-2022",
            overwrite_zoning=True,
        )
        # Character-area zoning fills only parcels the district polygons missed.
        extra = 0
        index = _index(powder_f)
        for feature in features:
            props = feature["properties"]
            if props.get("_cobbCity") != "Powder Springs" or props.get("zoningCode"):
                continue
            lon, lat = props["centroid"]
            hit = index.hit(lon, lat)
            if hit and _set_zoning(feature, hit["properties"].get("Zoning"), "Powder Springs", SKIP_ZONING):
                extra += 1
        notes.append(
            f"Powder Springs character areas (F2022_CA, the public FLU stand-in) matched {flu_hits} parcels. "
            f"The same layer filled zoning on {extra} parcels the district polygons missed."
        )

    acworth = counts.get("Acworth", 0)
    austell = counts.get("Austell", 0)
    notes.append(
        f"Acworth ({acworth} parcels in the 5–150 acre band) and Austell ({austell}) have no public zoning or FLU REST service. "
        "Those fields stay blank. No city ordinance text was invented for them."
    )

    sales, sales_error = _join_sales(features)
    if sales_error:
        notes.append(sales_error)
    else:
        notes.append(
            f"ParcelSales MapServer/41 joined on PIN. STEB=FMV and price > 0 is the qualified filter. "
            f"The latest qualified sale was kept on {sales} of {len(features)} parcels. Other STEB codes were not stored."
        )

    for feature in features:
        feature["properties"].pop("_cobbCity", None)
        # Eligible nomination tracts are not designated QOZs. Never copy one into the other.
        feature["properties"]["opportunityZone"] = None
        feature["properties"]["oz2Eligibility"] = None
    return notes
