"""Rutherford County, TN (FIPS 47149) 5–150 acre parcel enrich.

Public AGOL Parcel_Data only. Rutherford is not an IMPACT county. City zoning
is joined inside Murfreesboro, Smyrna, and La Vergne. Unincorporated parcels
use county zoning plus Character Areas. Eagleville has no public zoning
FeatureServer. Smyrna, La Vergne, and Eagleville have no public FLU layer.
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable

FIPS = "47149"
SOURCE = "tn-rutherford-agol-parcels"
PARCEL_QUERY = (
    "https://services5.arcgis.com/A5C0MR9xfkxVRwat/arcgis/rest/services/"
    "Parcel_Data/FeatureServer/1/query"
)
APPRAISER_URL = "https://secured.rutherfordcountytn.gov/OFS/WP/PropertySearch/QuickSearch"

COUNTY_ZONING_QUERY = (
    "https://maps.rutherfordcountytn.gov/server/rest/services/Planning/"
    "Planning_Zoning_Subdivisions/MapServer/2/query"
)
SMYRNA_TOWN_QUERY = (
    "https://maps.townofsmyrna.org/server/rest/services/Public_Access/"
    "Smyrna_Online_Utility_Map/MapServer/24/query"
)
SMYRNA_TOWN_META = (
    "https://maps.townofsmyrna.org/server/rest/services/Public_Access/"
    "Smyrna_Online_Utility_Map/MapServer/24"
)
SMYRNA_MIRROR_QUERY = (
    "https://maps.rutherfordcountytn.gov/server/rest/services/Planning/"
    "Smyrna_and_LaVergne_Zoning/MapServer/0/query"
)
SMYRNA_MIRROR_META = (
    "https://maps.rutherfordcountytn.gov/server/rest/services/Planning/"
    "Smyrna_and_LaVergne_Zoning/MapServer/0"
)
LAVERGNE_QUERY = (
    "https://maps.rutherfordcountytn.gov/server/rest/services/Planning/"
    "Smyrna_and_LaVergne_Zoning/MapServer/1/query"
)
MURFREESBORO_ZONING_QUERY = (
    "https://maps.murfreesborotn.gov/server/rest/services/Cityworks/GovUnits/FeatureServer/24/query"
)
MURFREESBORO_FLU_QUERY = (
    "https://maps.murfreesborotn.gov/server/rest/services/RSA_FLU_2023_update/MapServer/1/query"
)
CHARACTER_QUERY = (
    "https://maps.rutherfordcountytn.gov/server/rest/services/Planning/"
    "Planning__Engineering_Comprehensive_Plan/MapServer/3/query"
)

PARCEL_FIELDS = [
    "OBJECTID",
    "GISLINK",
    "ParcelID",
    "PropertyID",
    "CAMAACCT",
    "CITYCODE",
    "PARCEL_TYPE",
    "CALCACRES",
    "DEEDACRES",
    "Owner1",
    "Owner2",
    "Owner3",
    "MailingAddress",
    "MailingAddress2",
    "MailingCity",
    "MailingState",
    "MailingZipCode",
    "STREETADDRESS",
    "FormattedLocation",
    "STREETNO",
    "STREETDIR",
    "STREETNAME",
    "STREETSUF",
    "CITY",
    "ZIP",
    "SaleDate",
    "SalePrice",
    "LegalReference",
    "Grantor",
    "Grantee",
    "TotalLandValue",
    "TotalBuildingValue",
    "TotalYardItemValue",
    "TotalValue",
    "TotalAssessedValue",
    "TotalLandValueWithAg",
    "AgriculturalCredit",
    "ZONING",
    "SUBDIVISION",
    "GREENBELT",
    "TAXYEAR",
]

# Parcel CITYCODE domain. 217 and nulls are noise, not a fifth city.
MUNICIPALITIES = {
    "000": {"prefix": "RUT", "name": "Unincorporated Rutherford", "kind": "unincorporated"},
    "227": {"prefix": "EAG", "name": "Eagleville", "kind": "eagleville"},
    "400": {"prefix": "LVG", "name": "La Vergne", "kind": "lavergne"},
    "515": {"prefix": "MUR", "name": "Murfreesboro", "kind": "murfreesboro"},
    "674": {"prefix": "SMY", "name": "Smyrna", "kind": "smyrna"},
}

BASE_GAPS = [
    "Rutherford is not an IMPACT county. Parcels come from the public AGOL Parcel_Data FeatureServer (PARCEL_TYPE=1, CALCACRES 5–150). ParcelID is the display id; GISLINK is kept for joins. COUNTY/COUNTYID 075 is the comptroller county number, not FIPS.",
    "Assessor WebPro Quick Search is the property-record portal. No stable public deep link was verified — search by ParcelID. Alias portal rcpatn.com. Do not use the token-gated maps.rutherfordcountytn.gov Assessor folder.",
    "City zoning is joined on countywide parcels after CITYCODE: Murfreesboro 515 (GovUnits SubZoning), Smyrna 674 (town MapServer, county mirror fallback), La Vergne 400 (county mirror Zoning_Typ). Unincorporated 000 uses county Planning_Zoning_Subdivisions ZONEABBRV. Eagleville 227 has no public zoning FeatureServer; the parcel ZONING attribute is the only label.",
    "La Vergne adopted a zoning ordinance dated 2025-10-09 that says the legal zoning map is the city GIS layer. The county mirror still carries the prior district set. Re-validate before treating Zoning_Typ as post-adoption entitlement.",
    "FLU is Murfreesboro RSA 2023 (flut_pri, plan guidance, not an entitlement) inside CITYCODE 515, and county Character Areas (guidance) for unincorporated parcels via GISLINK. No public Smyrna, La Vergne, or Eagleville future-land-use FeatureServer was verified.",
    "Zoning and Murfreesboro FLU use a centroid-in-polygon join. Character Areas join on GISLINK. Multifamily tokens cover Murfreesboro RM-12/RM-16, Smyrna R-5/R-6, and county RMF only. Other districts stay unscored.",
]


def rutherford_spec() -> dict:
    return {
        "kind": "arcgis",
        "url": PARCEL_QUERY,
        "where": "PARCEL_TYPE=1 AND CALCACRES>=5 AND CALCACRES<=150",
        "outFields": PARCEL_FIELDS,
        "idField": "ParcelID",
        "idFallbacks": ["GISLINK"],
        "acresField": "CALCACRES",
        "source": SOURCE,
        "coverage": "complete-gte-5ac",
        "normalizer": "rutherford",
        "gaps": list(BASE_GAPS),
    }


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


def city_code(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    if text.isdigit():
        return text.zfill(3)
    return text


def arcgis_date(value: Any) -> str | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    seconds = parsed / 1000.0 if parsed > 10_000_000_000 else parsed
    try:
        when = datetime.fromtimestamp(seconds, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    if when.year < 1900 or when.year > 2100:
        return None
    return when.date().isoformat()


def join_owners(attrs: dict) -> tuple[str | None, str | None]:
    names = [clean(attrs.get(key)) for key in ("Owner1", "Owner2", "Owner3")]
    present = [name for name in names if name]
    if not present:
        return None, None
    if len(present) == 1:
        return present[0], None
    return present[0], " / ".join(present[1:])


def situs_address(attrs: dict) -> str | None:
    street = clean(attrs.get("STREETADDRESS")) or clean(attrs.get("FormattedLocation"))
    if street:
        return street
    parts = [clean(attrs.get(key)) for key in ("STREETNO", "STREETDIR", "STREETNAME", "STREETSUF")]
    joined = " ".join(part for part in parts if part)
    return joined or None


def municipality(code: str | None) -> dict:
    if code and code in MUNICIPALITIES:
        return MUNICIPALITIES[code]
    return {"prefix": "UNK", "name": "Unknown Rutherford jurisdiction", "kind": "unknown"}


def prefixed_code(prefix: str, district: str | None) -> str | None:
    token = clean(district)
    if not token:
        return None
    upper = token.upper()
    head = f"{prefix}-"
    if upper.startswith(head):
        return upper
    return f"{prefix}-{upper}"


def feature_gaps(code: str | None) -> list[str]:
    kind = municipality(code)["kind"]
    gaps = [
        "Assessor search is Rutherford WebPro Quick Search by ParcelID. No stable parcel deep link was verified.",
    ]
    if kind == "murfreesboro":
        gaps.append(
            "Murfreesboro zoning is the city GovUnits layer. RSA FLU 2023 is plan guidance, not a zoning entitlement, and is not applied outside CITYCODE 515."
        )
    elif kind == "smyrna":
        gaps.append("Smyrna has no public future-land-use FeatureServer. FLU is left null.")
    elif kind == "lavergne":
        gaps.append(
            "La Vergne zoning is the county mirror. The 2025-10-09 ordinance says the legal map is the city GIS layer. No public La Vergne FLU FeatureServer."
        )
    elif kind == "eagleville":
        gaps.append(
            "Eagleville has no public zoning or future-land-use FeatureServer. Zoning is the parcel attribute only, and FLU is null."
        )
    elif kind == "unincorporated":
        gaps.append(
            "Unincorporated zoning is the county ordinance layer (includes RMF). Character Areas are comprehensive-plan guidance, not zoning."
        )
    else:
        gaps.append(
            "CITYCODE is missing or not one of 000/227/400/515/674. No city zoning layer was applied. FLU was not inferred."
        )
    return gaps


def normalize_rutherford_feature(
    attrs: dict,
    esri_geometry: dict | None,
    *,
    county: dict,
    markets: list[str],
    empty_feature: Callable[..., dict],
    rings_to_feature_geometry: Callable[[dict | None], tuple[dict | None, float]],
    centroid_of: Callable[[dict], tuple[float, float] | None],
    plausible_centroid: Callable[[tuple[float, float] | None], bool],
    in_band: Callable[[float | None], bool],
) -> dict | None:
    parcel_type = attrs.get("PARCEL_TYPE")
    if parcel_type not in (None, 1, "1"):
        return None
    geometry, geodesic = rings_to_feature_geometry(esri_geometry)
    if not geometry:
        return None
    center = centroid_of(geometry)
    if not plausible_centroid(center):
        return None
    acres = num(attrs.get("CALCACRES"))
    if not in_band(acres):
        return None
    parcel_id = clean(attrs.get("ParcelID")) or clean(attrs.get("GISLINK"))
    if not parcel_id:
        return None
    code = city_code(attrs.get("CITYCODE"))
    place = municipality(code)
    owner, owner2 = join_owners(attrs)
    price = num(attrs.get("SalePrice"))
    if price is not None and price <= 0:
        price = None
    attribute_zoning = clean(attrs.get("ZONING"))
    feature = empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=markets,
        parcel_id=parcel_id,
        acreage=float(acres),
        geometry=geometry,
        center=center,  # type: ignore[arg-type]
        source=SOURCE,
        owner=owner,
        situs=situs_address(attrs),
        city=clean(attrs.get("CITY")),
        zip_code=zip_str(attrs.get("ZIP")),
        sale_price=price,
        sale_date=arcgis_date(attrs.get("SaleDate")),
        market_value=num(attrs.get("TotalValue")),
        assessed=num(attrs.get("TotalAssessedValue")),
        mail1=clean(attrs.get("MailingAddress")),
        mail2=clean(attrs.get("MailingAddress2")),
        mail_city=clean(attrs.get("MailingCity")),
        mail_state=clean(attrs.get("MailingState")),
        mail_zip=zip_str(attrs.get("MailingZipCode")),
    )
    props = feature["properties"]
    props["ownerName2"] = owner2
    props["jurisdictionCode"] = code
    props["cityCode"] = code
    props["jurisdictionPrefix"] = place["prefix"] if code in MUNICIPALITIES else None
    props["gisLink"] = clean(attrs.get("GISLINK"))
    props["deedAcres"] = num(attrs.get("DEEDACRES"))
    props["geodesicAcres"] = round(geodesic, 2) if geodesic else None
    props["propertyId"] = clean(attrs.get("PropertyID"))
    props["camaAccount"] = clean(attrs.get("CAMAACCT"))
    props["parcelZoningAttribute"] = attribute_zoning
    props["zoningCode"] = None
    props["zoningDistrict"] = None
    props["zoningLabel"] = None
    props["zoningSource"] = None
    props["appraiserUrl"] = APPRAISER_URL
    props["dataGaps"] = feature_gaps(code)
    props["tax"].update(
        {
            "taxableValue": None,
            "taxes": None,
            "landValue": num(attrs.get("TotalLandValue")),
            "buildingValue": num(attrs.get("TotalBuildingValue")),
            "yardItemValue": num(attrs.get("TotalYardItemValue")),
            "landValueWithAg": num(attrs.get("TotalLandValueWithAg")),
            "agriculturalCredit": num(attrs.get("AgriculturalCredit")),
        }
    )
    props["lastSale"].update(
        {
            "legalReference": clean(attrs.get("LegalReference")),
            "grantor": clean(attrs.get("Grantor")),
            "grantee": clean(attrs.get("Grantee")),
        }
    )
    if attribute_zoning and place["kind"] == "eagleville":
        apply_zoning(props, attribute_zoning, None, "eagleville-parcel-attribute")
    return feature


def apply_zoning(props: dict, district: str | None, label: str | None, source: str) -> None:
    prefix = props.get("jurisdictionPrefix") or municipality(props.get("jurisdictionCode"))["prefix"]
    coded = prefixed_code(prefix, district)
    if not coded:
        return
    short = coded.split("-", 1)[1]
    props["zoningCode"] = coded
    props["zoningDistrict"] = short
    props["zoningLabel"] = clean(label) if clean(label) and clean(label) != short else None
    props["zoningSource"] = source


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


def point_in_feature(x: float, y: float, feature: dict) -> bool:
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        rings = geom["coordinates"]
        if not rings or not point_in_ring(x, y, rings[0]):
            return False
        return not any(point_in_ring(x, y, hole) for hole in rings[1:])
    if geom.get("type") == "MultiPolygon":
        for poly in geom["coordinates"]:
            if poly and point_in_ring(x, y, poly[0]) and not any(point_in_ring(x, y, hole) for hole in poly[1:]):
                return True
    return False


def feature_bbox(feature: dict) -> tuple[float, float, float, float] | None:
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

    walk((feature.get("geometry") or {}).get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


class GridIndex:
    def __init__(self, cell: float = 0.03) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = feature_bbox(feature)
        if not bbox:
            return
        west, south, east, north = bbox
        ix0 = math.floor(west / self.cell)
        ix1 = math.floor(east / self.cell)
        iy0 = math.floor(south / self.cell)
        iy1 = math.floor(north / self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 500:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        ix = math.floor(x / self.cell)
        iy = math.floor(y / self.cell)
        for feature in self.buckets.get((ix, iy), []):
            if point_in_feature(x, y, feature):
                return feature
        for feature in self.broad:
            if point_in_feature(x, y, feature):
                return feature
        return None


def representative_points(feature: dict) -> list[tuple[float, float]]:
    props = feature["properties"]
    points: list[tuple[float, float]] = []
    centroid = props.get("centroid")
    if centroid and len(centroid) == 2:
        points.append((float(centroid[0]), float(centroid[1])))
    geom = feature.get("geometry") or {}
    ring = None
    if geom.get("type") == "Polygon":
        ring = geom["coordinates"][0]
    elif geom.get("type") == "MultiPolygon" and geom["coordinates"]:
        ring = geom["coordinates"][0][0]
    if ring:
        body = ring[:-1] if len(ring) > 1 else ring
        if body:
            points.append((float(body[0][0]), float(body[0][1])))
            mid = body[len(body) // 2]
            points.append((float(mid[0]), float(mid[1])))
    return points


def first_hit(index: GridIndex | None, feature: dict) -> dict | None:
    if index is None:
        return None
    for lon, lat in representative_points(feature):
        found = index.hit(lon, lat)
        if found:
            return found
    return None


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/rutherford-parcels"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.1 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:180]}: {last}")


def fetch_object_ids(url: str, where: str = "1=1") -> list[int]:
    data = fetch_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=180)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    return [int(item) for item in (data.get("objectIds") or [])]


def fetch_attributes_by_ids(url: str, ids: list[int], out_fields: list[str], batch: int = 200) -> list[dict]:
    rows: list[dict] = []
    for start in range(0, len(ids), batch):
        chunk = ids[start : start + batch]
        data = fetch_json(
            url,
            {
                "objectIds": ",".join(str(item) for item in chunk),
                "outFields": ",".join(out_fields),
                "returnGeometry": "true",
                "outSR": "4326",
                "geometryPrecision": "5",
                "maxAllowableOffset": "0.00012",
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            if len(chunk) > 40:
                rows.extend(fetch_attributes_by_ids(url, chunk, out_fields, batch=max(20, len(chunk) // 2)))
                continue
            raise RuntimeError(json.dumps(data["error"])[:300])
        rows.extend(data.get("features") or [])
        time.sleep(0.03)
    return rows


def coded_values(meta_url: str, field_name: str) -> dict[int, str]:
    data = fetch_json(meta_url, {"f": "pjson"}, timeout=60)
    found: dict[int, str] = {}
    for field in data.get("fields") or []:
        if field.get("name") != field_name:
            continue
        for entry in (field.get("domain") or {}).get("codedValues") or []:
            try:
                found[int(entry["code"])] = str(entry["name"])
            except (KeyError, TypeError, ValueError):
                continue
    return found


def load_polygon_index(
    url: str,
    out_fields: list[str],
    label: str,
    to_props: Callable[[dict], dict | None],
) -> GridIndex:
    ids = fetch_object_ids(url)
    print(f"  {label} polygons {len(ids)}", flush=True)
    raw = fetch_attributes_by_ids(url, ids, out_fields)
    from seed_market_parcels import rings_to_feature_geometry

    index = GridIndex()
    kept = 0
    for item in raw:
        geometry, _acres = rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            continue
        payload = to_props(item.get("attributes") or {})
        if not payload:
            continue
        index.add({"type": "Feature", "geometry": geometry, "properties": payload})
        kept += 1
    print(f"    indexed {kept}", flush=True)
    return index


def murfreesboro_zoning_props(attrs: dict) -> dict | None:
    district = clean(attrs.get("SubZoning"))
    if not district:
        return None
    label = clean(attrs.get("GenZoning"))
    return {"district": district, "label": label}


def county_zoning_props(attrs: dict) -> dict | None:
    district = clean(attrs.get("ZONEABBRV"))
    if not district:
        return None
    label = clean(attrs.get("ZONE_DIST")) or clean(attrs.get("ZONING"))
    return {"district": district, "label": label}


def lavergne_zoning_props(attrs: dict) -> dict | None:
    district = clean(attrs.get("Zoning_Typ"))
    if not district:
        return None
    return {"district": district, "label": None}


def smyrna_props_factory(zone_id_names: dict[int, str], dist_names: dict[int, str]) -> Callable[[dict], dict | None]:
    def to_props(attrs: dict) -> dict | None:
        text = clean(attrs.get("ZoningText"))
        zone_id = attrs.get("ZONE_ID")
        dist = attrs.get("ZONING_DIST")
        district = None
        try:
            if zone_id is not None and zone_id != "":
                district = zone_id_names.get(int(zone_id))
        except (TypeError, ValueError):
            district = None
        label = text
        try:
            if dist is not None and dist != "":
                label = label or dist_names.get(int(dist))
        except (TypeError, ValueError):
            pass
        if not district and label:
            district = label.split()[0]
        if not district:
            return None
        return {"district": district, "label": label}

    return to_props


def rsa_props(attrs: dict) -> dict | None:
    code = clean(attrs.get("flut_pri"))
    if not code:
        return None
    return {
        "code": f"MUR-{code.upper()}",
        "label": clean(attrs.get("label")) or code,
        "jurisdiction": "MUR",
        "source": "murfreesboro-rsa-flu-2023",
    }


def load_smyrna_index() -> tuple[GridIndex | None, str, str | None]:
    try:
        zone_ids = coded_values(SMYRNA_TOWN_META, "ZONE_ID")
        dist_names = coded_values(SMYRNA_TOWN_META, "ZONING_DIST")
        if not zone_ids:
            raise RuntimeError("Smyrna town layer returned no ZONE_ID domain")
        index = load_polygon_index(
            SMYRNA_TOWN_QUERY,
            ["ZONE_ID", "ZONING_DIST", "ZoningText"],
            "Smyrna town zoning",
            smyrna_props_factory(zone_ids, dist_names),
        )
        return index, "smyrna-town-mapserver-24", None
    except Exception as exc:  # noqa: BLE001
        print(f"  Smyrna town layer failed ({exc}); using county mirror", flush=True)
        zone_ids = coded_values(SMYRNA_MIRROR_META, "ZONE_ID")
        dist_names = coded_values(SMYRNA_MIRROR_META, "ZONING_DIST")
        index = load_polygon_index(
            SMYRNA_MIRROR_QUERY,
            ["ZONE_ID", "ZONING_DIST"],
            "Smyrna county mirror",
            smyrna_props_factory(zone_ids, dist_names),
        )
        return index, "smyrna-county-mirror", f"Smyrna town MapServer failed ({exc}). Zoning used the county mirror."


def character_by_gislink(gislinks: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    unique = [link for link in dict.fromkeys(gislinks) if link]
    if not unique:
        return found
    print(f"  Character Areas attribute join for {len(unique)} GISLINK values", flush=True)

    def one(chunk: list[str]) -> list[dict]:
        quoted = ",".join("'" + link.replace("'", "''") + "'" for link in chunk)
        data = fetch_json(
            CHARACTER_QUERY,
            {
                "where": f"GISLINK IN ({quoted})",
                "outFields": "GISLINK,FLU,CHAR,FLU_type,JURIS",
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=90,
        )
        if data.get("error"):
            if len(chunk) > 1:
                mid = len(chunk) // 2
                return one(chunk[:mid]) + one(chunk[mid:])
            raise RuntimeError(json.dumps(data["error"])[:300])
        return data.get("features") or []

    chunks = [unique[index : index + 40] for index in range(0, len(unique), 40)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(one, chunk) for chunk in chunks]
        done = 0
        for future in as_completed(futures):
            for item in future.result():
                attrs = item.get("attributes") or {}
                link = clean(attrs.get("GISLINK"))
                code = clean(attrs.get("FLU")) or clean(attrs.get("CHAR"))
                if not link or not code or link in found:
                    continue
                label_bits = [bit for bit in (clean(attrs.get("FLU")), clean(attrs.get("CHAR")), clean(attrs.get("FLU_type"))) if bit]
                found[link] = {
                    "code": f"RUT-{code.upper()}",
                    "label": " · ".join(label_bits),
                    "jurisdiction": "RUT",
                    "source": "rutherford-character-areas",
                }
            done += 1
            if done == len(chunks) or done % 25 == 0:
                print(f"    character batches {done}/{len(chunks)} matched {len(found)}", flush=True)
    return found


def assign_overlays(
    features: list[dict],
    *,
    murfreesboro: GridIndex | None,
    smyrna: GridIndex | None,
    smyrna_source: str,
    lavergne: GridIndex | None,
    county_zoning: GridIndex | None,
    rsa: GridIndex | None,
    characters: dict[str, dict],
) -> dict[str, int]:
    stats = {
        "murfreesboroZoning": 0,
        "smyrnaZoning": 0,
        "lavergneZoning": 0,
        "countyZoning": 0,
        "eaglevilleAttribute": 0,
        "parcelAttributeFallback": 0,
        "zoningMiss": 0,
        "rsaFlu": 0,
        "characterFlu": 0,
        "fluGap": 0,
    }
    for feature in features:
        props = feature["properties"]
        kind = municipality(props.get("jurisdictionCode"))["kind"]
        attribute = props.get("parcelZoningAttribute")
        hit = None
        source = None
        if kind == "murfreesboro":
            hit = first_hit(murfreesboro, feature)
            source = "murfreesboro-govunits-zoning"
        elif kind == "smyrna":
            hit = first_hit(smyrna, feature)
            source = smyrna_source
        elif kind == "lavergne":
            hit = first_hit(lavergne, feature)
            source = "lavergne-county-mirror"
        elif kind == "unincorporated":
            hit = first_hit(county_zoning, feature)
            source = "rutherford-county-zoning"
        if hit and source:
            payload = hit["properties"]
            apply_zoning(props, payload.get("district"), payload.get("label"), source)
            stats[
                {
                    "murfreesboro": "murfreesboroZoning",
                    "smyrna": "smyrnaZoning",
                    "lavergne": "lavergneZoning",
                    "unincorporated": "countyZoning",
                }[kind]
            ] += 1
        elif kind == "eagleville" and props.get("zoningCode"):
            stats["eaglevilleAttribute"] += 1
        elif attribute and kind != "eagleville":
            apply_zoning(props, attribute, None, "parcel-attribute")
            stats["parcelAttributeFallback"] += 1
        elif not props.get("zoningCode"):
            stats["zoningMiss"] += 1

        if kind == "murfreesboro":
            flu_hit = first_hit(rsa, feature)
            flu = (flu_hit or {}).get("properties") if flu_hit else None
            if flu and flu.get("code"):
                props["flu"] = {
                    "code": flu["code"],
                    "label": flu.get("label"),
                    "jurisdiction": "MUR",
                    "source": flu.get("source"),
                }
                stats["rsaFlu"] += 1
            else:
                stats["fluGap"] += 1
        elif kind == "unincorporated":
            flu = characters.get(props.get("gisLink") or "")
            if flu:
                props["flu"] = flu
                stats["characterFlu"] += 1
            else:
                stats["fluGap"] += 1
        else:
            props["flu"] = None
            stats["fluGap"] += 1
    return stats


def features_from_rutherford(raw: list[dict], county: dict, markets: list[str]) -> tuple[list[dict], int, list[str]]:
    from seed_market_parcels import (
        centroid_of,
        empty_feature,
        in_band,
        plausible_centroid,
        rings_to_feature_geometry,
    )

    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        feature = normalize_rutherford_feature(
            item.get("attributes") or {},
            item.get("geometry"),
            county=county,
            markets=markets,
            empty_feature=empty_feature,
            rings_to_feature_geometry=rings_to_feature_geometry,
            centroid_of=centroid_of,
            plausible_centroid=plausible_centroid,
            in_band=in_band,
        )
        if not feature:
            dropped += 1
            continue
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    print(f"  normalized {len(features)} Rutherford parcels (dropped {dropped})", flush=True)

    extra_gaps: list[str] = []
    try:
        murfreesboro = load_polygon_index(
            MURFREESBORO_ZONING_QUERY,
            ["SubZoning", "GenZoning"],
            "Murfreesboro zoning",
            murfreesboro_zoning_props,
        )
    except Exception as exc:  # noqa: BLE001
        murfreesboro = None
        extra_gaps.append(f"Murfreesboro zoning layer failed ({exc}). City parcels fell back to the parcel ZONING attribute.")
    smyrna_source = "smyrna-town-mapserver-24"
    try:
        smyrna, smyrna_source, smyrna_gap = load_smyrna_index()
        if smyrna_gap:
            extra_gaps.append(smyrna_gap)
    except Exception as exc:  # noqa: BLE001
        smyrna = None
        extra_gaps.append(f"Smyrna zoning failed ({exc}). CITYCODE 674 fell back to the parcel ZONING attribute.")
    try:
        lavergne = load_polygon_index(
            LAVERGNE_QUERY,
            ["Zoning_Typ"],
            "La Vergne zoning",
            lavergne_zoning_props,
        )
    except Exception as exc:  # noqa: BLE001
        lavergne = None
        extra_gaps.append(f"La Vergne county-mirror zoning failed ({exc}).")
    try:
        county_zoning = load_polygon_index(
            COUNTY_ZONING_QUERY,
            ["ZONEABBRV", "ZONING", "ZONE_DIST"],
            "County zoning",
            county_zoning_props,
        )
    except Exception as exc:  # noqa: BLE001
        county_zoning = None
        extra_gaps.append(f"County zoning MapServer failed ({exc}). Unincorporated parcels fell back to the parcel ZONING attribute.")
    try:
        rsa = load_polygon_index(
            MURFREESBORO_FLU_QUERY,
            ["flut_pri", "label"],
            "Murfreesboro RSA FLU",
            rsa_props,
        )
    except Exception as exc:  # noqa: BLE001
        rsa = None
        extra_gaps.append(f"Murfreesboro RSA FLU layer failed ({exc}). Murfreesboro FLU was left null.")

    gislinks = [
        feature["properties"].get("gisLink")
        for feature in features
        if municipality(feature["properties"].get("jurisdictionCode"))["kind"] == "unincorporated"
        and feature["properties"].get("gisLink")
    ]
    try:
        characters = character_by_gislink(gislinks)
    except Exception as exc:  # noqa: BLE001
        characters = {}
        extra_gaps.append(f"County Character Areas join failed ({exc}). Unincorporated FLU was left null.")

    stats = assign_overlays(
        features,
        murfreesboro=murfreesboro,
        smyrna=smyrna,
        smyrna_source=smyrna_source,
        lavergne=lavergne,
        county_zoning=county_zoning,
        rsa=rsa,
        characters=characters,
    )
    summary = (
        "Join counts — zoning "
        f"Murfreesboro {stats['murfreesboroZoning']}, Smyrna {stats['smyrnaZoning']}, "
        f"La Vergne {stats['lavergneZoning']}, county {stats['countyZoning']}, "
        f"Eagleville attribute {stats['eaglevilleAttribute']}, "
        f"parcel-attribute fallback {stats['parcelAttributeFallback']}, "
        f"zoning miss {stats['zoningMiss']}; "
        f"FLU RSA {stats['rsaFlu']}, Character Areas {stats['characterFlu']}, FLU gap {stats['fluGap']}."
    )
    print(f"  {summary}", flush=True)
    extra_gaps.insert(0, summary)
    return features, dropped, extra_gaps
