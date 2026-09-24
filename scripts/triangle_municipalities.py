"""Research Triangle municipalities for market-parcel joins.

Durham County (37063) is wired: City + unincorporated share the joint UDO and
Place Type future land use. Chapel Hill, Morrisville, Raleigh, and Cary tips
inside Durham are first-class and use their own zoning polygons.

Wake (37183) and Orange (37135) stay on NC OneMap until a follow-up points
their parcel pull at ``layers_for_county`` and ``apply_triangle_joins``.
Those counties are listed on the shared tip layers so the hook is already
in the registry.
"""

from __future__ import annotations

import math
import time
import urllib.parse
from collections import defaultdict
from typing import Any, Callable

from seed_fixtures import point_in_feature

DURHAM_PARCEL_URL = (
    "https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Property/MapServer/4/query"
)
NC_ONEMAP_FALLBACK_URL = (
    "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1/query"
)
DURHAM_ZONING_URL = (
    "https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Planning/MapServer/12/query"
)
DURHAM_PLACE_TYPE_URL = (
    "https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Planning/MapServer/25/query"
)
CHAPEL_HILL_ZONING_URL = (
    "https://gis-portal.townofchapelhill.org/server/rest/services/OpenData/Zoning_Districts/FeatureServer/0/query"
)
CHAPEL_HILL_FLU_NOTE = (
    "Chapel Hill future land use is ImageServer only "
    "(gis-portal.townofchapelhill.org Future_Land_Uses) — no queryable polygons."
)
MORRISVILLE_ZONING_URL = "https://maps.wake.gov/arcgis/rest/services/Planning/Zoning/MapServer/22/query"
RALEIGH_ZONING_URL = "https://maps.raleighnc.gov/arcgis/rest/services/Planning/Zoning/MapServer/0/query"
CARY_ZONING_URL = "https://maps.raleighnc.gov/arcgis/rest/services/Planning/Zoning/MapServer/3/query"

APPRAISER_SEARCH_URL = "https://taxcama.dconc.gov/camapwa/"
VIEWER_URL = "https://maps.durhamnc.gov/"
APPRAISER_PK_TEMPLATE = "https://taxcama.dconc.gov/camapwa/PropertySummary.aspx?PARCELPK={pk}"
APPRAISER_REID_TEMPLATE = "https://taxcama.dconc.gov/camapwa/PropertySummary.aspx?REID={reid}"

# State-plane feet extent of Property/MapServer/4. Used to clip regional zoning
# layers (Raleigh, Cary, Chapel Hill, Morrisville) to the Durham County footprint.
DURHAM_EXTENT_2264 = {
    "xmin": 1995169.1468886435,
    "ymin": 769105.6817967296,
    "xmax": 2088928.376364559,
    "ymax": 906397.9994031489,
    "spatialReference": {"wkid": 2264},
}

WIRED_COUNTY_FIPS = {"37063"}
DURHAM_CACHE_VERSION = 1

TIP_IDS = ("chapel-hill", "morrisville", "raleigh", "cary")
DURHAM_IDS = ("durham-city", "durham-county")

FOLLOWUP_GAPS = {
    "37183": (
        "Follow-up: Wake stays on NC OneMap. Raleigh, Cary, and Morrisville zoning "
        "layers are registered in scripts/triangle_municipalities.py and are not "
        "joined onto Wake parcels in this pull."
    ),
    "37135": (
        "Follow-up: Orange stays on NC OneMap. Chapel Hill zoning is registered in "
        "scripts/triangle_municipalities.py and is not joined onto Orange parcels in "
        "this pull. Chapel Hill future land use remains ImageServer-only."
    ),
}

DURHAM_GAPS = [
    "Primary id is REID. PIN is unstable (Durham Tax Office) and is not used as parcelId. NC OneMap parno tracks PIN.",
    "Durham City and unincorporated Durham County share the joint City–County UDO (Planning/MapServer/12) and Place Type future land use (Planning/MapServer/25). A non-null Durham ZONING attribute is kept; null attributes are filled by a centroid spatial join.",
    "Chapel Hill, Morrisville, Raleigh, and Cary are first-class tip municipalities. Zoning is a centroid spatial join to that city's polygons when CITY/ETJ names the tip or the parcel ZONING attribute is null or tip-mixed. Durham UDO is not used as the only zoning for those tips.",
    "Tip-municipality future land use is thin. Chapel Hill Future_Land_Uses is ImageServer only. Morrisville, Raleigh, and Cary have no verified polygon FLU for the Durham County footprint, so those parcels keep flu null.",
    "Cary's public zoning layer exposes CLASS and NAME, not a ZONING field. Only a handful of Durham County parcels are in the Cary tip.",
    "Last sale is package sale (PKG_SALE_DATE/PRICE) with land sale as fallback. There is no multi-transfer sales layer. A sale price of 0 is stored as missing.",
    "If Property/MapServer/4 is unavailable, the seed falls back to NC OneMap FeatureServer/1 with cntyfips='063' (no sale price; parno is PIN).",
    "Owner phones and emails are not collected. The appraiser deep link is taxcama PropertySummary by PARCEL_PK, otherwise REID. Viewer: https://maps.durhamnc.gov/",
    "Wake (37183) and Orange (37135) stay on NC OneMap. Shared tip layers are registered for a follow-up and are not joined onto those counties in this pull.",
]

_ALIAS = {
    "DURHAM": "durham-city",
    "DURHAM CITY": "durham-city",
    "DURHAM COUNTY": "durham-county",
    "CHAPEL HILL": "chapel-hill",
    "CHAP HILL": "chapel-hill",
    "MORRISVILLE": "morrisville",
    "RALEIGH": "raleigh",
    "CARY": "cary",
}

_ANNOTATION_PREFIXES = ("CHAP HILL", "CHAPEL HILL", "COUNTY", "MORRISVILLE", "RALEIGH", "CARY")

FLU_GAPS = {
    "chapel-hill": CHAPEL_HILL_FLU_NOTE,
    "morrisville": "No public Morrisville polygon future land use was verified for the Durham County tip.",
    "raleigh": "No public Raleigh polygon future land use was verified for the Durham County tip.",
    "cary": "No public Cary polygon future land use was verified for the Durham County tip.",
}

NAMES = {
    "durham-city": "Durham",
    "durham-county": "Durham County",
    "chapel-hill": "Chapel Hill",
    "morrisville": "Morrisville",
    "raleigh": "Raleigh",
    "cary": "Cary",
}


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _tokens(value: Any) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    normalized = text.upper().replace("-", " ").replace("/", ",")
    tokens: list[str] = []
    for chunk in normalized.split(","):
        token = " ".join(chunk.split())
        if token:
            tokens.append(token)
    return tokens


def route_municipalities(city: Any, etj: Any) -> list[str]:
    """Ordered municipality ids named by parcel CITY and ETJ. Duplicates drop."""
    found: list[str] = []
    for token in _tokens(city) + _tokens(etj):
        muni_id = _ALIAS.get(token)
        if muni_id and muni_id not in found:
            found.append(muni_id)
    return found


def zoning_is_annotated(zoning: Any) -> bool:
    """True when the parcel ZONING string is a tip annotation rather than a code."""
    text = (_clean(zoning) or "").upper()
    if not text:
        return False
    if "," in text or "/" in text:
        return True
    for prefix in _ANNOTATION_PREFIXES:
        if text == prefix or text.startswith(prefix + " ") or text.startswith(prefix + ","):
            return True
    return False


def zoning_needs_polygon(zoning: Any, routes: list[str]) -> bool:
    """Spatial-join when the attribute is missing, tip-mixed, or the parcel is a tip."""
    if not _clean(zoning):
        return True
    if any(muni_id in TIP_IDS for muni_id in routes):
        return True
    return zoning_is_annotated(zoning)


def preferred_muni(routes: list[str]) -> str:
    for muni_id in routes:
        if muni_id in TIP_IDS:
            return muni_id
    if "durham-city" in routes:
        return "durham-city"
    if "durham-county" in routes:
        return "durham-county"
    return routes[0] if routes else "durham-county"


def preferred_durham(routes: list[str]) -> str:
    if "durham-city" in routes and "durham-county" not in routes:
        return "durham-city"
    if "durham-county" in routes and "durham-city" not in routes:
        return "durham-county"
    if "durham-city" in routes:
        return "durham-city"
    return "durham-county"


def epoch_ms_to_iso(value: Any) -> str | None:
    """ArcGIS epoch milliseconds, or epoch seconds, to YYYY-MM-DD. 0 and null are missing."""
    if value in (None, "", 0):
        return None
    if isinstance(value, str) and not value.strip().replace(".", "", 1).isdigit():
        text = value.strip()
        return text[:10] if len(text) >= 8 else None
    try:
        ms = int(float(value))
    except (TypeError, ValueError):
        return None
    if abs(ms) < 10_000_000_000:
        ms *= 1000
    if ms < -2_208_988_800_000 or ms > 4_102_444_800_000:
        return None
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000.0))
    except (OverflowError, OSError, ValueError):
        return None


def appraiser_url(reid: str, parcel_pk: Any) -> str:
    pk_text = _clean(parcel_pk)
    if pk_text:
        try:
            pk_text = str(int(float(pk_text)))
        except (TypeError, ValueError):
            if pk_text.endswith(".0"):
                pk_text = pk_text[:-2]
        if pk_text and pk_text not in {"0", "None"}:
            return APPRAISER_PK_TEMPLATE.format(pk=urllib.parse.quote(pk_text))
    return APPRAISER_REID_TEMPLATE.format(reid=urllib.parse.quote(str(reid)))


def _read_durham_zoning(attrs: dict) -> dict | None:
    code = _clean(attrs.get("UDO_LABEL")) or _clean(attrs.get("ZONE_CODE"))
    if not code:
        return None
    legend = _clean(attrs.get("UDO_LEGEND"))
    general = _clean(attrs.get("ZONE_GEN"))
    return {
        "zoningCode": code,
        "zoningDistrict": legend or general or code,
        "layer": "durham-udo",
    }


def _read_chapel_hill(attrs: dict) -> dict | None:
    code = _clean(attrs.get("ZONING"))
    if not code:
        return None
    name = _clean(attrs.get("NAME"))
    return {"zoningCode": code, "zoningDistrict": name or code, "layer": "chapel-hill-zoning"}


def _read_morrisville(attrs: dict) -> dict | None:
    code = _clean(attrs.get("CLASS"))
    if not code:
        return None
    conditional = _clean(attrs.get("COND_USE"))
    district = f"{code} ({conditional})" if conditional else code
    return {"zoningCode": code, "zoningDistrict": district, "layer": "morrisville-zoning"}


def _read_raleigh(attrs: dict) -> dict | None:
    code = _clean(attrs.get("ZONING"))
    if not code:
        return None
    label = _clean(attrs.get("ZONE_TYPE_DECODE")) or code
    return {"zoningCode": code, "zoningDistrict": label, "layer": "raleigh-zoning"}


def _read_cary(attrs: dict) -> dict | None:
    # The Cary layer has CLASS and NAME. It does not publish a ZONING field.
    code = _clean(attrs.get("CLASS")) or _clean(attrs.get("NAME"))
    if not code:
        return None
    name = _clean(attrs.get("NAME"))
    return {"zoningCode": code, "zoningDistrict": name or code, "layer": "cary-zoning"}


def _read_place_type(attrs: dict) -> dict | None:
    code = _clean(attrs.get("PlaceType"))
    if not code:
        return None
    label = _clean(attrs.get("PlaceTypeName")) or code
    return {
        "code": code,
        "label": label,
        "jurisdiction": "Durham",
        "source": "durham-place-type-25",
    }


def _layer(
    layer_id: str,
    url: str,
    out_fields: list[str],
    reader: Callable[[dict], dict | None],
    counties: list[str],
    *,
    clip: bool,
) -> dict:
    return {
        "id": layer_id,
        "url": url,
        "outFields": out_fields,
        "read": reader,
        "counties": counties,
        "clip": clip,
    }


ZONING_LAYERS: list[dict] = [
    _layer(
        "durham-udo",
        DURHAM_ZONING_URL,
        ["ZONE_CODE", "UDO_LABEL", "UDO_LEGEND", "ZONE_GEN"],
        _read_durham_zoning,
        ["37063"],
        clip=True,
    ),
    _layer(
        "chapel-hill-zoning",
        CHAPEL_HILL_ZONING_URL,
        ["ZONING", "NAME"],
        _read_chapel_hill,
        ["37063", "37135"],
        clip=True,
    ),
    _layer(
        "morrisville-zoning",
        MORRISVILLE_ZONING_URL,
        ["CLASS", "COND_USE"],
        _read_morrisville,
        ["37063", "37183"],
        clip=True,
    ),
    _layer(
        "raleigh-zoning",
        RALEIGH_ZONING_URL,
        ["ZONING", "ZONE_TYPE", "ZONE_TYPE_DECODE"],
        _read_raleigh,
        ["37063", "37183"],
        clip=True,
    ),
    _layer(
        "cary-zoning",
        CARY_ZONING_URL,
        ["CLASS", "NAME"],
        _read_cary,
        ["37063", "37183"],
        clip=True,
    ),
]

PLACE_TYPE_LAYER = _layer(
    "durham-place-type",
    DURHAM_PLACE_TYPE_URL,
    ["PlaceType", "PlaceTypeName"],
    _read_place_type,
    ["37063"],
    clip=True,
)

MUNICIPALITIES: list[dict] = [
    {
        "id": "durham-city",
        "name": "Durham",
        "role": "city",
        "udoGroup": "durham-city-county",
        "counties": ["37063"],
        "zoningLayer": "durham-udo",
        "flu": "durham-place-type",
    },
    {
        "id": "durham-county",
        "name": "Durham County",
        "role": "unincorporated",
        "udoGroup": "durham-city-county",
        "counties": ["37063"],
        "zoningLayer": "durham-udo",
        "flu": "durham-place-type",
    },
    {
        "id": "chapel-hill",
        "name": "Chapel Hill",
        "role": "tip",
        "udoGroup": None,
        "counties": ["37063", "37135"],
        "zoningLayer": "chapel-hill-zoning",
        "flu": None,
        "fluGap": CHAPEL_HILL_FLU_NOTE,
    },
    {
        "id": "morrisville",
        "name": "Morrisville",
        "role": "tip",
        "udoGroup": None,
        "counties": ["37063", "37183"],
        "zoningLayer": "morrisville-zoning",
        "flu": None,
        "fluGap": FLU_GAPS["morrisville"],
    },
    {
        "id": "raleigh",
        "name": "Raleigh",
        "role": "tip",
        "udoGroup": None,
        "counties": ["37063", "37183"],
        "zoningLayer": "raleigh-zoning",
        "flu": None,
        "fluGap": FLU_GAPS["raleigh"],
    },
    {
        "id": "cary",
        "name": "Cary",
        "role": "tip",
        "udoGroup": None,
        "counties": ["37063", "37183"],
        "zoningLayer": "cary-zoning",
        "flu": None,
        "fluGap": FLU_GAPS["cary"],
    },
]

MUNI_ZONING_LAYER = {muni["id"]: muni["zoningLayer"] for muni in MUNICIPALITIES}


def layers_for_county(fips: str) -> list[dict]:
    """Zoning layers a later Wake or Orange pull can request without a new registry."""
    return [layer for layer in ZONING_LAYERS if fips in layer["counties"]]


def place_type_for_county(fips: str) -> dict | None:
    if fips in PLACE_TYPE_LAYER["counties"]:
        return PLACE_TYPE_LAYER
    return None


def envelope_params() -> dict[str, str]:
    import json

    return {
        "geometry": json.dumps(DURHAM_EXTENT_2264),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "2264",
    }


def _feature_bbox(feature: dict) -> tuple[float, float, float, float] | None:
    coords: list[list[float]] = []

    def walk(node: Any) -> None:
        if not node:
            return
        if isinstance(node[0], (int, float)):
            coords.append(node)
            return
        for child in node:
            walk(child)

    walk((feature.get("geometry") or {}).get("coordinates") or [])
    if not coords:
        return None
    xs = [point[0] for point in coords]
    ys = [point[1] for point in coords]
    return min(xs), min(ys), max(xs), max(ys)


class GridIndex:
    def __init__(self, cell: float = 0.03) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = _feature_bbox(feature)
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

    def hit(self, lon: float, lat: float) -> dict | None:
        ix = math.floor(lon / self.cell)
        iy = math.floor(lat / self.cell)
        for feature in self.buckets.get((ix, iy), []):
            if point_in_feature(lon, lat, feature):
                return feature
        for feature in self.broad:
            if point_in_feature(lon, lat, feature):
                return feature
        return None


def index_polygons(features: list[dict], reader: Callable[[dict], dict | None]) -> tuple[GridIndex, int]:
    """features items are ``{geometry, attributes}``."""
    index = GridIndex(0.03)
    kept = 0
    for feature in features:
        payload = reader(feature.get("attributes") or {})
        if not payload:
            continue
        index.add({"type": "Feature", "geometry": feature["geometry"], "properties": payload})
        kept += 1
    return index, kept


def _hit_layer(index: GridIndex | None, lon: float, lat: float) -> dict | None:
    if index is None:
        return None
    found = index.hit(lon, lat)
    if not found:
        return None
    payload = dict(found.get("properties") or {})
    if not payload.get("zoningCode"):
        return None
    return payload


def polygon_zoning(
    lon: float,
    lat: float,
    routes: list[str],
    zoning_attr: str | None,
    indexes: dict[str, GridIndex],
    city_ids: list[str] | None = None,
) -> dict | None:
    """Tip polygons win over Durham UDO.

    When CITY names only a tip (even if ETJ also says Durham County), a miss keeps
    that tip and does not borrow the joint UDO. Mixed CITY labels may still use
    the UDO when the tip polygon does not contain the centroid.
    """
    named_by_city = city_ids if city_ids is not None else []
    city_tips = [muni_id for muni_id in named_by_city if muni_id in TIP_IDS]
    city_names_durham = any(muni_id in DURHAM_IDS for muni_id in named_by_city)
    authoritative_tips = city_tips if city_tips and not city_names_durham else []
    tip_routes = authoritative_tips or [muni_id for muni_id in routes if muni_id in TIP_IDS]
    durham_routes = [muni_id for muni_id in routes if muni_id in DURHAM_IDS]
    for muni_id in tip_routes:
        found = _hit_layer(indexes.get(MUNI_ZONING_LAYER[muni_id]), lon, lat)
        if found:
            found["municipalityId"] = muni_id
            return found
    if authoritative_tips:
        return None
    if durham_routes or not tip_routes:
        found = _hit_layer(indexes.get("durham-udo"), lon, lat)
        if found:
            found["municipalityId"] = preferred_durham(routes)
            return found
    if not _clean(zoning_attr):
        for muni_id in TIP_IDS:
            if muni_id in tip_routes:
                continue
            found = _hit_layer(indexes.get(MUNI_ZONING_LAYER[muni_id]), lon, lat)
            if found:
                found["municipalityId"] = muni_id
                return found
    return None


def apply_triangle_joins(
    features: list[dict],
    zoning_indexes: dict[str, GridIndex],
    place_index: GridIndex | None,
) -> dict[str, int]:
    """Stamp municipality, zoning, and FLU. Strips the temporary Durham routing keys."""
    stats: dict[str, int] = defaultdict(int)
    for feature in features:
        props = feature["properties"]
        city = props.pop("_durhamCity", None)
        etj = props.pop("_durhamEtj", None)
        zoning_attr = props.pop("_zoningAttribute", None)
        routes = route_municipalities(city, etj)
        city_ids = route_municipalities(city, None)
        if not routes:
            routes = ["durham-county"]
            stats["default-unincorporated"] += 1
        lon, lat = props["centroid"]
        needs = zoning_needs_polygon(zoning_attr, routes)
        chosen = (
            polygon_zoning(lon, lat, routes, zoning_attr, zoning_indexes, city_ids) if needs else None
        )
        gaps = list(props.get("dataGaps") or [])
        if chosen:
            props["zoningCode"] = chosen["zoningCode"]
            props["zoningDistrict"] = chosen["zoningDistrict"]
            muni_id = chosen["municipalityId"]
            stats["zoning-polygon"] += 1
        else:
            props["zoningCode"] = zoning_attr
            props["zoningDistrict"] = zoning_attr
            muni_id = preferred_muni(routes)
            if needs and zoning_attr:
                gaps.append("Municipal zoning polygon did not contain the centroid; parcel ZONING attribute kept.")
                stats["zoning-attribute-fallback"] += 1
            elif needs:
                gaps.append("No zoning polygon or parcel ZONING attribute.")
                stats["zoning-missing"] += 1
            else:
                stats["zoning-attribute"] += 1
        props["municipalityId"] = muni_id
        props["municipality"] = NAMES.get(muni_id, muni_id)
        props["jurisdictionCode"] = muni_id
        if muni_id in TIP_IDS:
            props["flu"] = None
            gap = FLU_GAPS.get(muni_id)
            if gap and gap not in gaps:
                gaps.append(gap)
            stats["flu-tip-gap"] += 1
        else:
            hit = place_index.hit(lon, lat) if place_index else None
            flu = (hit or {}).get("properties") if hit else None
            if flu and flu.get("code"):
                props["flu"] = {
                    "code": flu["code"],
                    "label": flu.get("label") or flu["code"],
                    "jurisdiction": flu.get("jurisdiction") or "Durham",
                    "source": flu.get("source") or "durham-place-type-25",
                }
                stats["flu-joined"] += 1
            else:
                props["flu"] = None
                stats["flu-miss"] += 1
        props["dataGaps"] = gaps
        stats[f"muni:{muni_id}"] += 1
    return dict(stats)


def municipality_summary(stats: dict[str, int]) -> list[dict]:
    rows = []
    for muni in MUNICIPALITIES:
        if "37063" not in muni["counties"]:
            continue
        rows.append(
            {
                "id": muni["id"],
                "name": muni["name"],
                "role": muni["role"],
                "zoningLayer": muni["zoningLayer"],
                "flu": muni["flu"],
                "parcelCount": int(stats.get(f"muni:{muni['id']}", 0)),
            }
        )
    return rows
