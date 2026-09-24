"""DeKalb County, Georgia (FIPS 13089) parcel extract.

County roll is Tax_Parcels_Assessment_View layer 2, filtered to 5.0–150.0 acres
on ACREAGE. Municipal zoning and future land use are first-class. County
Zoning_District and LandUse fill unincorporated land only.

Decatur, Illinois and the DeKalb counties in Alabama, Illinois, Indiana, and
Tennessee are rejected before a join. There is no public sale table.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from parcel_geometry import esri_rings_to_geojson, polygon_parts

FIPS = "13089"
SOURCE = "ga-dekalb-assessment-view-2"
PARCEL_LAYER = (
    "https://dcgis.dekalbcountyga.gov/mapping/rest/services/"
    "Tax_Parcels_Assessment_View/FeatureServer/2"
)
ZONING_LAYER = "https://dcgis.dekalbcountyga.gov/mapping/rest/services/Zoning_District/FeatureServer/0"
FLU_LAYER = "https://dcgis.dekalbcountyga.gov/mapping/rest/services/LandUse/FeatureServer/0"
MUNICIPAL_LAYER = (
    "https://dcgis.dekalbcountyga.gov/mapping/rest/services/Municipal_Boundary/FeatureServer/0"
)
APPRAISER_URL = "https://propertyappraisal.dekalbcountyga.gov/"
CACHE_NAME = "13089-assessment-v1.json"

# DeKalb County, Georgia. Atlanta's citywide layers intersect this box.
DEKALB_GA = (-84.42, 33.62, -84.05, 33.98)
# Centroids outside this box are not the county roll.
PARCEL_BOX = (-84.50, 33.55, -84.00, 34.05)

FOREIGN_EXTENTS = (
    ("Decatur, Illinois", (-89.15, 39.70, -88.70, 40.05)),
    ("DeKalb County, Alabama", (-86.35, 34.20, -85.45, 34.95)),
    ("DeKalb County, Illinois", (-89.30, 41.50, -88.30, 42.25)),
    ("DeKalb County, Indiana", (-85.35, 41.15, -84.75, 41.75)),
    ("DeKalb County, Tennessee", (-86.15, 35.75, -85.40, 36.25)),
)

GAPS = [
    "No sale price, sale date, or qualified flag. Tax_Parcels_Assessment_View has no sale history. Delinquent-tax layers are not sales and are not joined.",
    "Municipal zoning and future land use are joined where a public layer exists (Decatur, Brookhaven, Dunwoody, Doraville, Tucker, Stonecrest, and Atlanta inside DeKalb). Chamblee is future land use only. Stone Mountain, Avondale Estates, Clarkston, Lithonia, and Pine Lake have no public zoning or FLU service and stay blank.",
    "City of Atlanta zoning and future land use are citywide. They are joined only where DeKalb's municipal boundary says Atlanta. Decatur, Illinois (decaturil.gov) and DeKalb counties in Alabama, Illinois, Indiana, and Tennessee are not FIPS 13089 and are not joined.",
    "County Zoning_District and LandUse fill unincorporated DeKalb only. They are not copied onto city parcels. The parcel ZONING attribute is a fallback for unincorporated parcels the county polygon missed.",
    "Parcel CITY is the situs postal city, not the municipality. jurisdictionCode comes from Municipal_Boundary.",
    "OZ 2.0 eligibility is not a designated QOZ. This extract does not write opportunityZone from an eligible tract.",
    "Owner phone and email are not on the public assessment layer. TOTAPR1 is the appraised value and CNTASSDVAL is the county assessed value.",
]

GAP_CITIES = (
    "Stone Mountain",
    "Avondale Estates",
    "Clarkston",
    "Lithonia",
    "Pine Lake",
)

PARCEL_FIELDS = [
    "PARCELID",
    "ACREAGE",
    "SITEADDRESS",
    "CITY",
    "ZIP",
    "OWNERNME1",
    "OWNERNME2",
    "PSTLADDRESS",
    "PSTLCITY",
    "PSTLSTATE",
    "PSTLZIP5",
    "TOTAPR1",
    "CNTASSDVAL",
    "CNTTXBLVAL",
    "ZONING",
    "LANDUSE",
    "CVTTXDSCRP",
]


def dekalb_spec() -> dict:
    return {
        "kind": "dekalb",
        "url": f"{PARCEL_LAYER}/query",
        "where": "ACREAGE>=5 AND ACREAGE<=150",
        "source": SOURCE,
        "coverage": "complete-gte-5ac",
        "gaps": list(GAPS),
        "appraiserUrl": APPRAISER_URL,
    }


def extent_rejection(
    bbox: tuple[float | None, float | None, float | None, float | None],
    url: str = "",
) -> str | None:
    """Return a reason to skip a layer, or None when it may be joined."""
    if url and "decaturil" in url.lower():
        return (
            "Decatur, Illinois layer (decaturil.gov). Not the City of Decatur, Georgia. Not joined."
        )
    west, south, east, north = bbox
    if west is None or south is None or east is None or north is None:
        return "layer returned no WGS84 extent"
    cx = (west + east) / 2
    cy = (south + north) / 2
    for name, (fw, fs, fe, fn) in FOREIGN_EXTENTS:
        if fw <= cx <= fe and fs <= cy <= fn:
            return f"extent is {name}, not DeKalb County, Georgia (FIPS 13089). Not joined."
    if north < 30.3 or south > 35.1 or east < -85.7 or west > -80.6:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} is outside Georgia. Not joined."
        )
    if (east - west) > 2.5 or (north - south) > 2.5:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} is too broad to be a "
            "DeKalb County or city layer. Not joined."
        )
    dw, ds, de, dn = DEKALB_GA
    if east < dw or west > de or north < ds or south > dn:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} does not intersect "
            "DeKalb County, Georgia. Not joined."
        )
    return None


def parcel_keys(value: Any) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    spaced = " ".join(text.split()).upper()
    compact = "".join(text.split()).upper()
    keys: list[str] = []
    for key in (text, spaced, compact):
        if key and key not in keys:
            keys.append(key)
    return keys


def label_text(value: Any, code: str) -> str:
    text = _clean(value)
    if not text or text.lower().startswith("http"):
        return code
    return text


def zoning_district_label(place: str, code: str) -> str:
    """City or county prefix so a bare code is not an Orange County district."""
    return f"{place}:{code}"


def map_assessment(attrs: dict) -> dict | None:
    """Map one assessment row. Sales stay empty. Acres must already be in band."""
    parcel_id = _clean(attrs.get("PARCELID"))
    acres = _num(attrs.get("ACREAGE"))
    if not parcel_id or acres is None or acres < 5 or acres > 150:
        return None
    taxable = _num(attrs.get("CNTTXBLVAL"))
    if taxable is not None and taxable <= 0:
        taxable = None
    market = _num(attrs.get("TOTAPR1"))
    assessed = _num(attrs.get("CNTASSDVAL"))
    if market is not None and market <= 0:
        market = None
    if assessed is not None and assessed <= 0:
        assessed = None
    return {
        "parcelId": parcel_id,
        "acreage": round(acres, 4),
        "ownerName": _clean(attrs.get("OWNERNME1")),
        "ownerName2": _clean(attrs.get("OWNERNME2")),
        "situsAddress": _clean(attrs.get("SITEADDRESS")),
        "situsCity": _clean(attrs.get("CITY")),
        "situsZip": _zip(attrs.get("ZIP")),
        "mail1": _clean(attrs.get("PSTLADDRESS")),
        "mailCity": _clean(attrs.get("PSTLCITY")),
        "mailState": _clean(attrs.get("PSTLSTATE")),
        "mailZip": _zip(attrs.get("PSTLZIP5")),
        "marketValue": market,
        "assessedValue": assessed,
        "taxableValue": taxable,
        "taxDistrict": _clean(attrs.get("CVTTXDSCRP")),
        "rollZoning": _clean(attrs.get("ZONING")),
        "rollLandUse": _clean(attrs.get("LANDUSE")),
    }


def _set_zoning(feature: dict, code: str, place: str) -> None:
    props = feature["properties"]
    if props.get("zoningCode"):
        return
    props["zoningCode"] = code
    props["zoningDistrict"] = zoning_district_label(place, code)


def _set_flu(feature: dict, code: str, label: str | None, place: str, source: str) -> None:
    props = feature["properties"]
    if props.get("flu"):
        return
    props["flu"] = {
        "code": code,
        "label": label or code,
        "jurisdiction": place,
        "source": source,
    }


def _feature_bbox(feature: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, (int, float)) and not isinstance(node, bool):
            return
        if node and isinstance(node[0], (int, float)) and not isinstance(node[0], bool):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        for item in node:
            walk(item)

    walk((feature.get("geometry") or {}).get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


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


class SpatialIndex:
    """Smallest containing polygon wins."""

    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = _feature_bbox(feature)
        if not bbox:
            return
        west, south, east, north = bbox
        feature["_bboxArea"] = max(0.0, (east - west) * (north - south))
        ix0, iy0 = int(west // self.cell), int(south // self.cell)
        ix1, iy1 = int(east // self.cell), int(north // self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 80:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        ix, iy = int(x // self.cell), int(y // self.cell)
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


def attribute_index(rows: list[dict], id_fields: list[str]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for row in rows:
        for field in id_fields:
            for key in parcel_keys(row.get(field)):
                lookup.setdefault(key, row)
    return lookup


def lookup_parcel(index: dict[str, dict], parcel_id: str) -> dict | None:
    for key in parcel_keys(parcel_id):
        found = index.get(key)
        if found:
            return found
    return None


def assign_jurisdictions(features: list[dict], boundaries: list[dict]) -> dict[str, int]:
    """Stamp jurisdictionCode from DeKalb municipal boundaries. Postal CITY stays put."""
    index = SpatialIndex(cell=0.05)
    for feature in boundaries:
        index.add(feature)
    counts: dict[str, int] = defaultdict(int)
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        hit = index.hit(lon, lat)
        name = _clean((hit or {}).get("properties", {}).get("NAME")) if hit else None
        jurisdiction = name or "Unincorporated"
        feature["properties"]["jurisdictionCode"] = jurisdiction
        counts[jurisdiction] += 1
    return dict(counts)


def apply_city_layers(features: list[dict], cities: list[dict]) -> list[dict]:
    """Join each city's zoning and FLU only onto parcels inside that city."""
    summaries: list[dict] = []
    for city in cities:
        name = city["name"]
        summary = {
            "name": name,
            "state": "Georgia",
            "independentGis": bool(city.get("zoning") or city.get("flu")),
            "zoningUrl": (city.get("zoning") or {}).get("url"),
            "fluUrl": (city.get("flu") or {}).get("url"),
            "join": city.get("join"),
            "note": city.get("note"),
            "fluGap": city.get("fluGap"),
            "zoningJoined": 0,
            "fluJoined": 0,
            "zoningFeatures": (city.get("zoning") or {}).get("featureCount") or 0,
            "fluFeatures": (city.get("flu") or {}).get("featureCount") or 0,
        }
        targets = [feature for feature in features if feature["properties"].get("jurisdictionCode") == name]
        zoning = city.get("zoning")
        if zoning and not zoning.get("rejected"):
            summary["zoningJoined"] = _apply_overlay(targets, zoning, name, "zoning")
        flu = city.get("flu")
        if flu and not flu.get("rejected"):
            summary["fluJoined"] = _apply_overlay(targets, flu, name, "flu")
        if not zoning and not flu:
            summary["fluGap"] = city.get("fluGap") or "No public zoning or future land use service."
            summary["independentGis"] = False
        summaries.append(summary)
    return summaries


def apply_unincorporated(features: list[dict], county: dict) -> dict:
    """County zoning and FLU, then the tax-roll zoning attribute, unincorporated only."""
    targets = [
        feature for feature in features if feature["properties"].get("jurisdictionCode") == "Unincorporated"
    ]
    zoning_joined = 0
    flu_joined = 0
    attribute_zoning = 0
    if county.get("zoning"):
        zoning_joined = _apply_overlay(targets, county["zoning"], "DeKalb", "zoning")
    if county.get("flu"):
        flu_joined = _apply_overlay(targets, county["flu"], "DeKalb", "flu")
    for feature in targets:
        props = feature["properties"]
        if not props.get("zoningCode") and props.get("_rollZoning"):
            _set_zoning(feature, props["_rollZoning"], "DeKalb")
            attribute_zoning += 1
        if not props.get("flu") and props.get("_rollLandUse"):
            _set_flu(feature, props["_rollLandUse"], props["_rollLandUse"], "DeKalb", "dekalb-tax-roll-landuse")
            flu_joined += 1
    return {
        "zoningUrl": ZONING_LAYER,
        "fluUrl": FLU_LAYER,
        "zoningFeatures": (county.get("zoning") or {}).get("featureCount") or 0,
        "fluFeatures": (county.get("flu") or {}).get("featureCount") or 0,
        "zoningJoined": zoning_joined,
        "fluJoined": flu_joined,
        "attributeZoningCount": attribute_zoning,
        "parcelCount": len(targets),
        "note": "Unincorporated only. County polygons are not applied inside municipalities.",
    }


def _apply_overlay(features: list[dict], overlay: dict, place: str, kind: str) -> int:
    matched = 0
    source = overlay.get("source") or place
    if overlay.get("method") == "attribute":
        index = overlay.get("index") or {}
        for feature in features:
            row = lookup_parcel(index, feature["properties"].get("parcelId") or "")
            if not row:
                continue
            if _write_code(feature, row, overlay, place, source, kind):
                matched += 1
        return matched
    spatial: SpatialIndex | None = overlay.get("spatial")
    if spatial is None:
        return 0
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        hit = spatial.hit(lon, lat)
        if not hit:
            continue
        if _write_code(feature, hit.get("properties") or {}, overlay, place, source, kind):
            matched += 1
    return matched


def _write_code(feature: dict, row: dict, overlay: dict, place: str, source: str, kind: str) -> bool:
    code = _clean(row.get(overlay.get("codeField") or ""))
    if not code and overlay.get("codeFallback"):
        code = _clean(row.get(overlay["codeFallback"]))
    if not code:
        return False
    if kind == "zoning":
        if feature["properties"].get("zoningCode"):
            return False
        _set_zoning(feature, code, place)
        return True
    if feature["properties"].get("flu"):
        return False
    label = label_text(row.get(overlay.get("labelField") or ""), code)
    _set_flu(feature, code, label, place, source)
    return True


def city_catalog() -> list[dict]:
    """Public layers named on the DeKalb card. Gap cities have no URL."""
    root = "https://services.arcgis.com/36QtML6Mf01B1N0W/arcgis/rest/services"
    doraville = (
        "https://services5.arcgis.com/HPK9d3vzjakSFUjJ/arcgis/rest/services/"
        "Zoning_and_Land_Use_Map___City_of_Doraville_WFL1/FeatureServer"
    )
    stone = "https://services8.arcgis.com/2Oj4p0oK7rnTYNHA/arcgis/rest/services"
    atlanta_z = "https://gis.atlantaga.gov/dpcd/rest/services/OpenDataService1/FeatureServer/22/query"
    atlanta_f = (
        "https://gis.atlantaga.gov/dpcd/rest/services/LandUsePlanning/LandUsePlanning/MapServer/8/query"
    )
    cities: list[dict] = [
        {
            "name": "Decatur",
            "join": "spatial",
            "note": "City of Decatur, Georgia (decatur_admin). Not Decatur, Illinois.",
            "zoning": {
                "url": f"{root}/Zoning/FeatureServer/0/query",
                "method": "spatial",
                "fields": ["ZONECLASS", "ZONEDESC"],
                "codeField": "ZONECLASS",
                "labelField": "ZONEDESC",
                "source": "decatur-ga-zoning",
            },
            "flu": {
                "url": f"{root}/Decatur_Future_Land_Use/FeatureServer/0/query",
                "method": "spatial",
                "fields": ["LANDUSECODE", "LANDUSEDESC"],
                "codeField": "LANDUSECODE",
                "labelField": "LANDUSEDESC",
                "source": "decatur-ga-future-land-use",
            },
        },
        {
            "name": "Brookhaven",
            "join": "attribute parcel id; character areas are spatial",
            "zoning": {
                "url": "https://gis.brookhavenga.gov/arcgis/rest/services/LandUsePlanning/LandUsePlanning/MapServer/3/query",
                "method": "attribute",
                "idFields": ["PARCELID"],
                "fields": ["PARCELID", "ZONECLASS", "ZONEDESC"],
                "codeField": "ZONECLASS",
                "labelField": "ZONEDESC",
                "source": "brookhaven-zoning",
            },
            "flu": {
                "url": "https://gis.brookhavenga.gov/arcgis/rest/services/LandUsePlanning/LandUsePlanning/MapServer/1/query",
                "method": "spatial",
                "fields": ["NAME"],
                "codeField": "NAME",
                "source": "brookhaven-character-areas",
            },
        },
        {
            "name": "Dunwoody",
            "join": "spatial",
            "zoning": {
                "url": "https://dungisapp.dunwoodyga.gov/arcgis/rest/services/Zoning/MapServer/3/query",
                "method": "spatial",
                "fields": ["Zoning", "Label"],
                "codeField": "Zoning",
                "labelField": "Label",
                "source": "dunwoody-zoning",
            },
            "flu": {
                "url": "https://dungisapp.dunwoodyga.gov/arcgis/rest/services/Zoning/MapServer/1/query",
                "method": "spatial",
                "fields": ["Name"],
                "codeField": "Name",
                "source": "dunwoody-future-land-use",
            },
        },
        {
            "name": "Doraville",
            "join": "attribute parcel id",
            "zoning": {
                "url": f"{doraville}/0/query",
                "method": "attribute",
                "idFields": ["PARCELID"],
                "fields": ["PARCELID", "ZONE_ID", "ZDistNm"],
                "codeField": "ZONE_ID",
                "labelField": "ZDistNm",
                "source": "doraville-zoning",
            },
            "flu": {
                "url": f"{doraville}/1/query",
                "method": "attribute",
                "idFields": ["PARCELID"],
                "fields": ["PARCELID", "FDM", "LU_NAME"],
                "codeField": "FDM",
                "labelField": "LU_NAME",
                "source": "doraville-future-land-use",
            },
        },
        {
            "name": "Tucker",
            "join": "attribute parcel id for zoning; spatial future land use",
            "zoning": {
                "url": "https://tuckergis.interdev.com/arcgis/rest/services/Planning/Zoning/FeatureServer/0/query",
                "method": "attribute",
                "idFields": ["PARCEL_ID"],
                "fields": ["PARCEL_ID", "ZONING"],
                "codeField": "ZONING",
                "source": "tucker-zoning",
            },
            "flu": {
                "url": "https://tuckergis.interdev.com/arcgis/rest/services/Planning/FutureLandUse/FeatureServer/0/query",
                "method": "spatial",
                "fields": ["LANDUSECOD", "LANDUSEDES"],
                "codeField": "LANDUSECOD",
                "labelField": "LANDUSEDES",
                "source": "tucker-future-land-use",
            },
        },
        {
            "name": "Stonecrest",
            "join": "attribute parcel id",
            "zoning": {
                "url": f"{stone}/Zoning_view/FeatureServer/0/query",
                "method": "attribute",
                "idFields": ["PARCELID"],
                "fields": ["PARCELID", "ZONECLASS"],
                "codeField": "ZONECLASS",
                "source": "stonecrest-zoning",
            },
            "flu": {
                "url": f"{stone}/Future_Land_Use_view/FeatureServer/0/query",
                "method": "attribute",
                "idFields": ["PARCELID"],
                "fields": ["PARCELID", "LANDUSECODE", "LANDUSEDESC"],
                "codeField": "LANDUSECODE",
                "labelField": "LANDUSEDESC",
                "source": "stonecrest-future-land-use",
            },
        },
        {
            "name": "Chamblee",
            "join": "attribute parcel id",
            "note": "FLU only. TaxParcelZoning is not treated as the official zoning map and is not joined.",
            "fluGap": None,
            "zoning": None,
            "flu": {
                "url": "https://gis.chambleega.gov/arcgis/rest/services/Planning_and_Development/FutureLandUseParcels/MapServer/0/query",
                "method": "attribute",
                "idFields": ["PARCELID"],
                "fields": ["PARCELID", "LANDUSECODE", "LANDUSEDESC"],
                "codeField": "LANDUSECODE",
                "labelField": "LANDUSEDESC",
                "source": "chamblee-future-land-use",
            },
        },
        {
            "name": "Atlanta",
            "join": "spatial, DeKalb municipal boundary only",
            "note": "Citywide Atlanta layers. Joined only where jurisdictionCode is Atlanta inside DeKalb County.",
            "zoning": {
                "url": atlanta_z,
                "method": "spatial",
                "fields": ["ZONECLASS", "ZONING", "ZONEDESC"],
                "codeField": "ZONECLASS",
                "codeFallback": "ZONING",
                "source": "atlanta-zoning",
            },
            "flu": {
                "url": atlanta_f,
                "method": "spatial",
                "fields": ["LANDUSECOD", "LANDUSEDES"],
                "codeField": "LANDUSECOD",
                "labelField": "LANDUSEDES",
                "source": "atlanta-future-land-use",
            },
        },
    ]
    for name in GAP_CITIES:
        cities.append(
            {
                "name": name,
                "join": None,
                "zoning": None,
                "flu": None,
                "fluGap": "No public zoning or future land use FeatureServer.",
                "note": "Gap. County zoning is not copied in to fill it.",
            }
        )
    return cities


def download_dekalb(county: dict, markets: list[str], spec: dict) -> dict:
    import json
    from pathlib import Path

    import seed_market_parcels as seed

    print(f"Pulling {county['name']} {county['state']} ({FIPS}) via {spec['source']}", flush=True)
    cache_path = seed.CACHE_DIR / CACHE_NAME
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        features = cached["features"]
        dropped = int(cached.get("dropped") or 0)
        source_count = int(cached.get("sourceCount") or 0)
        print(f"  cache hit {len(features)}", flush=True)
        for feature in features:
            feature["properties"]["marketIds"] = markets
    else:
        where = spec["where"]
        source_count = seed.count_where(spec["url"], where)
        print(f"  source rows {source_count}", flush=True)
        ids = seed.fetch_object_ids(spec["url"], where)
        raw = seed.fetch_by_ids(spec["url"], ids, PARCEL_FIELDS)
        features, dropped = _features_from_raw(seed, raw, county, markets)
        seed.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {"sourceCount": source_count, "dropped": dropped, "features": features},
                separators=(",", ":"),
            )
        )
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("DeKalb emitted a parcel outside 5–150 acres")
    for feature in features:
        feature["properties"]["lastSale"] = {"date": None, "price": None, "qualified": None}
        feature["properties"]["opportunityZone"] = None
        feature["properties"]["oz2Eligibility"] = None

    boundaries = _load_boundaries(seed)
    counts = assign_jurisdictions(features, boundaries)
    print(f"  jurisdictions {counts}", flush=True)
    cities = city_catalog()
    for city in cities:
        for key in ("zoning", "flu"):
            layer = city.get(key)
            if not layer:
                continue
            loaded = _load_overlay(seed, layer)
            if loaded.get("rejected"):
                layer["rejected"] = loaded["rejected"]
                city["note"] = ((city.get("note") or "") + " " + loaded["rejected"]).strip()
                continue
            layer.update(loaded)
    summaries = apply_city_layers(features, cities)
    county_layers = {
        "zoning": _load_named_overlay(
            seed,
            {
                "url": f"{ZONING_LAYER}/query",
                "method": "spatial",
                "fields": ["ZONECLASS", "ZONEDESC"],
                "codeField": "ZONECLASS",
                "labelField": "ZONEDESC",
                "source": "dekalb-zoning-district",
            },
        ),
        "flu": _load_named_overlay(
            seed,
            {
                "url": f"{FLU_LAYER}/query",
                "method": "spatial",
                "fields": ["LANDUSECODE", "LANDUSEDESC"],
                "codeField": "LANDUSECODE",
                "labelField": "LANDUSEDESC",
                "source": "dekalb-future-land-use",
            },
        ),
    }
    unincorporated = apply_unincorporated(features, county_layers)
    for feature in features:
        props = feature["properties"]
        props.pop("_rollZoning", None)
        props.pop("_rollLandUse", None)

    zoning_count = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_count = sum(1 for feature in features if feature["properties"].get("flu"))
    path, lookup, tiles = (None, None, 0)
    if features:
        path, lookup, tiles = seed.write_tiles(county, features)
    print(f"  kept {len(features)} zoning {zoning_count} flu {flu_count}", flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=spec["coverage"] if features else "gap",
        partition="tiles" if features else "none",
        path=path,
        lookup=lookup,
        source=spec["source"],
        query_url=spec["url"],
        gaps=list(spec.get("gaps") or []),
        source_count=source_count,
        dropped=dropped,
        tile_count=tiles,
        extra={
            "municipalities": summaries,
            "unincorporated": unincorporated,
            "jurisdictionCounts": counts,
            "zoningJoinedCount": zoning_count,
            "fluJoinedCount": flu_count,
            "sales": {
                "joined": False,
                "reason": "No public sale history on the assessment view. Delinquent tax is not a sale.",
            },
            "appraiserUrl": APPRAISER_URL,
            "rejected": [
                "Decatur, Illinois (maps.decaturil.gov and any extent centered on Decatur, IL).",
                "DeKalb County, Alabama; DeKalb County, Illinois; DeKalb County, Indiana; DeKalb County, Tennessee.",
            ],
        },
    )


def _features_from_raw(seed: Any, raw: list[dict], county: dict, markets: list[str]) -> tuple[list[dict], int]:
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        mapped = map_assessment(attrs)
        geometry, _computed = seed.rings_to_feature_geometry(item.get("geometry"))
        if not mapped or not geometry:
            dropped += 1
            continue
        center = seed.centroid_of(geometry)
        if not seed.plausible_centroid(center):
            dropped += 1
            continue
        lon, lat = center
        west, south, east, north = PARCEL_BOX
        if not (west <= lon <= east and south <= lat <= north):
            dropped += 1
            continue
        feature = seed.empty_feature(
            fips=FIPS,
            county=county["name"],
            state="Georgia",
            markets=markets,
            parcel_id=mapped["parcelId"],
            acreage=mapped["acreage"],
            geometry=geometry,
            center=center,
            source=SOURCE,
            owner=mapped["ownerName"],
            situs=mapped["situsAddress"],
            city=mapped["situsCity"],
            zip_code=mapped["situsZip"],
            dor=mapped["taxDistrict"],
            market_value=mapped["marketValue"],
            assessed=mapped["assessedValue"],
            taxable=mapped["taxableValue"],
            mail1=mapped["mail1"],
            mail_city=mapped["mailCity"],
            mail_state=mapped["mailState"],
            mail_zip=mapped["mailZip"],
        )
        props = feature["properties"]
        props["ownerName2"] = mapped["ownerName2"]
        props["appraiserUrl"] = APPRAISER_URL
        props["jurisdictionCode"] = None
        props["_rollZoning"] = mapped["rollZoning"]
        props["_rollLandUse"] = mapped["rollLandUse"]
        props["lastSale"] = {"date": None, "price": None, "qualified": None}
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        previous = by_id.get(mapped["parcelId"])
        if previous is None or mapped["acreage"] > (previous["properties"].get("acreage") or 0):
            by_id[mapped["parcelId"]] = feature
        else:
            dropped += 1
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def _load_boundaries(seed: Any) -> list[dict]:
    layer = {
        "url": f"{MUNICIPAL_LAYER}/query",
        "method": "spatial",
        "fields": ["NAME"],
        "codeField": "NAME",
        "source": "dekalb-municipal-boundary",
    }
    loaded = _load_overlay(seed, layer)
    return loaded.get("features") or []


def _load_named_overlay(seed: Any, layer: dict) -> dict:
    """Keep code fields. _load_overlay returns only the downloaded index."""
    loaded = _load_overlay(seed, layer)
    layer.update(loaded)
    return layer


def _load_overlay(seed: Any, layer: dict) -> dict:
    url = layer["url"]
    try:
        bbox = _layer_extent(seed, url)
    except Exception as exc:  # noqa: BLE001
        print(f"  overlay failed extent {url.split('/rest/services/')[-1][:80]}: {exc}", flush=True)
        return {"rejected": f"extent query failed: {exc}", "featureCount": 0}
    problem = extent_rejection(bbox, url)
    if problem:
        print(f"  skip {problem}", flush=True)
        return {"rejected": problem, "featureCount": 0}
    fields = list(layer.get("fields") or [])
    try:
        if layer.get("method") == "attribute":
            rows = _pull_attributes(seed, url, fields)
            print(f"  attribute {len(rows)} {url.split('/rest/services/')[-1][:80]}", flush=True)
            return {"index": attribute_index(rows, layer.get("idFields") or []), "featureCount": len(rows)}
        features = _pull_polygons(seed, url, fields)
        print(f"  spatial {len(features)} {url.split('/rest/services/')[-1][:80]}", flush=True)
        index = SpatialIndex()
        for feature in features:
            index.add(feature)
        return {"spatial": index, "features": features, "featureCount": len(features)}
    except Exception as exc:  # noqa: BLE001
        print(f"  overlay failed {url.split('/rest/services/')[-1][:80]}: {exc}", flush=True)
        return {"rejected": str(exc), "featureCount": 0}


def _layer_extent(seed: Any, url: str) -> tuple[float | None, float | None, float | None, float | None]:
    data = seed.fetch_json(url, {"where": "1=1", "returnExtentOnly": "true", "outSR": "4326", "f": "json"})
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:240])
    extent = data.get("extent") or {}
    return extent.get("xmin"), extent.get("ymin"), extent.get("xmax"), extent.get("ymax")


def _pull_attributes(seed: Any, url: str, fields: list[str]) -> list[dict]:
    ids = seed.fetch_object_ids(url, "1=1")
    rows: list[dict] = []
    batch = 200
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
        )
        if data.get("error"):
            raise RuntimeError(str(data["error"])[:240])
        for item in data.get("features") or []:
            rows.append(item.get("attributes") or {})
    return rows


def _pull_polygons(seed: Any, url: str, fields: list[str]) -> list[dict]:
    ids = seed.fetch_object_ids(url, "1=1")
    raw = seed.fetch_by_ids(url, ids, fields, batch=80)
    features: list[dict] = []
    for item in raw:
        rings = (item.get("geometry") or {}).get("rings")
        if not rings:
            continue
        geometry = esri_rings_to_geojson(rings)
        if not geometry:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": item.get("attributes") or {},
            }
        )
    return features


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
    return parsed


def _zip(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return text
