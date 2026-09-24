#!/usr/bin/env python3
"""Treasure Coast / Melbourne–Vero parcel extract.

Wire order: Indian River, St. Lucie, Brevard Accela, Martin, Okeechobee.
Public GIS only. 5.0–150.0 acres. Municipal zoning and future land use are
joined from that city's own layer. County layers fill unincorporated land.
They are not copied onto a city that publishes no layer.

Rejected on purpose:
- Tuscaloosa County, Alabama layers titled IRC (not Indian River County).
- City of Ocoee (Orange County), which is not Okeechobee County.
- A thin Martin County AGOL clip used as the county roll.
- Fort Pierce Zoning FeatureServer/0, which is project points, not zoning.
- Melbourne, Australia. This Melbourne is Brevard County, Florida.

Eligible OZ 2.0 tracts are not designated QOZs. Layers named Opportunity Zone
are not joined onto parcels.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from parcel_geometry import contains_point, esri_rings_to_geojson, net_acres, representative_point, signed_area

MIN_ACRES = 5.0
MAX_ACRES = 150.0

# Extent centroid boxes for sources that must never be wired.
TUSCALOOSA_AL = (-87.85, 33.00, -87.20, 33.50)
OCOEE_ORANGE = (-81.62, 28.50, -81.48, 28.62)

FORT_PIERCE_ZONING_LAYER = 7
FORT_PIERCE_PROJECTS_LAYER = 0

COUNTY_BBOX = {
    "12061": (-80.95, 27.50, -80.25, 27.92),
    "12111": (-80.75, 27.15, -80.12, 27.62),
    "12009": (-81.05, 27.75, -80.38, 28.86),
    "12085": (-80.95, 26.90, -79.85, 27.34),
    "12093": (-81.32, 27.05, -80.58, 27.72),
}

NOT_A_MUNICIPALITY = {
    "st. lucie county",
    "saint lucie county",
    "unincorporated",
    "brevard county",
    "indian river county",
    "martin county",
    "okeechobee county",
}

MARTIN_ZONE_STUBS = {
    "stuart",
    "city of stuart",
    "sewall's point",
    "sewalls point",
    "jupiter island",
    "ocean breeze",
    "indiantown",
    "no data",
    "municipal",
    "municipal planning area",
}

PLACE_NAMES = {
    "vero beach": "Vero Beach",
    "sebastian": "Sebastian",
    "fellsmere": "Fellsmere",
    "orchid": "Orchid",
    "indian river shores": "Indian River Shores",
    "i r shores": "Indian River Shores",
    "fort pierce": "Fort Pierce",
    "ft pierce": "Fort Pierce",
    "ft. pierce": "Fort Pierce",
    "port st. lucie": "Port St. Lucie",
    "port st lucie": "Port St. Lucie",
    "st. lucie village": "St. Lucie Village",
    "saint lucie village": "St. Lucie Village",
    "stuart": "Stuart",
    "city of stuart": "Stuart",
    "sewall's point": "Sewall's Point",
    "sewalls point": "Sewall's Point",
    "jupiter island": "Jupiter Island",
    "ocean breeze": "Ocean Breeze",
    "indiantown": "Indiantown",
    "melbourne": "Melbourne",
    "west melbourne": "West Melbourne",
    "melbourne beach": "Melbourne Beach",
    "melbourne village": "Melbourne Village",
    "palm bay": "Palm Bay",
    "palm shores": "Palm Shores",
    "titusville": "Titusville",
    "cocoa": "Cocoa",
    "cocoa beach": "Cocoa Beach",
    "rockledge": "Rockledge",
    "cape canaveral": "Cape Canaveral",
    "satellite beach": "Satellite Beach",
    "indian harbour beach": "Indian Harbour Beach",
    "indialantic": "Indialantic",
    "malabar": "Malabar",
    "grant-valkaria": "Grant-Valkaria",
    "grant valkaria": "Grant-Valkaria",
    "okeechobee": "Okeechobee",
}

REJECT_NOTES = {
    "12061": "Rejected Tuscaloosa IRC AGOL. A layer titled IRC whose extent is Tuscaloosa County, Alabama is not Indian River County. Parcels are the Indian River property appraiser service on gisportal.ircgov.com.",
    "12111": "Rejected Fort Pierce Zoning FeatureServer/0. That layer is Current Project Development (projects), not zoning. City zoning is FeatureServer/7.",
    "12009": "Rejected Melbourne, Australia. Brevard Accela covers Brevard County, Florida (about longitude -81 to -80.4 and latitude 27.8 to 28.8), not Victoria.",
    "12085": "Rejected a thin Martin AGOL clip as the county roll. Parcels are geoweb.martin.fl.us base_map layer 10, which covers the county, not an Indiantown-sized extract.",
    "12093": "Rejected City of Ocoee (maps.ocoee.org, Orange County). These parcels are Okeechobee County, from the county planning Parcels_2022 service.",
}

ELIGIBLE_NOTE = (
    "Eligible is not designated. Layers named Opportunity Zone, including Fort Pierce Zoning layer 9 "
    "and the Okeechobee 2019 opportunity-zone service, are not joined. OZ 2.0 eligibility stays a census-tract overlay."
)

SPECS = {
    "12061": {
        "source": "fl-ircpa-parcels-12061",
        "query": "https://gisportal.ircgov.com/server3/rest/services/IRCPA/Parcels_MS/MapServer/0/query",
        "where": "LAND_ACRES>=5 AND LAND_ACRES<=150",
    },
    "12111": {
        "source": "fl-slc-parcels-12111",
        "query": "https://slcgis.stlucieco.gov/hosting/rest/services/Parcel_Boundaries/MapServer/0/query",
        "where": "TOTAL_ACRE>=5 AND TOTAL_ACRE<=150",
    },
    "12009": {
        "source": "fl-brevard-accela-12009",
        "query": "https://gis.brevardfl.gov/gissrv/rest/services/Accela/AccelaGIS_Layers_WKID2881/MapServer/5/query",
        "where": "ACRES>=5 AND ACRES<=150",
    },
    "12085": {
        "source": "fl-martin-geoweb-12085",
        "query": "https://geoweb.martin.fl.us/arcgis/rest/services/Administrative_Areas/base_map/MapServer/10/query",
        "where": "AREA_ACRES>=5 AND AREA_ACRES<=150",
    },
    "12093": {
        "source": "fl-okeechobee-planning-12093",
        "query": "https://services3.arcgis.com/jE4lvuOFtdtz6Lbl/arcgis/rest/services/Parcels_2022/FeatureServer/2/query",
        "where": "1=1",
    },
}


def treasure_coast_spec(fips: str) -> dict:
    spec = SPECS[fips]
    return {
        "kind": "treasure-coast",
        "url": spec["query"],
        "where": spec["where"],
        "source": spec["source"],
        "coverage": "complete-gte-5ac",
        "gaps": [REJECT_NOTES[fips], ELIGIBLE_NOTE],
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
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def digits_only(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def parcel_pin(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    if "." in text:
        head, frac = text.split(".", 1)
        if head and frac and set(frac) <= {"0"}:
            return head
    return text


def zip_str(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    digits = digits_only(text)
    if len(digits) >= 5:
        return digits[:5]
    return text[:10]


def in_band(acres: float | None) -> bool:
    return acres is not None and MIN_ACRES <= acres <= MAX_ACRES


def sale_year_month(year: Any, month: Any) -> str | None:
    y = num(year)
    if y is None or y < 1900 or y > 2100:
        return None
    m = num(month)
    month_num = int(m) if m and 1 <= m <= 12 else 1
    return f"{int(y):04d}-{month_num:02d}-01"


def place_name(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    key = " ".join(text.lower().replace("_", " ").split())
    if key in NOT_A_MUNICIPALITY:
        return None
    if key in PLACE_NAMES:
        return PLACE_NAMES[key]
    titled = text.title()
    if titled.lower() in NOT_A_MUNICIPALITY:
        return None
    return titled


def usable_code(value: Any, stubs: set[str] | None = None) -> str | None:
    text = clean(value)
    if not text:
        return None
    key = " ".join(text.lower().split())
    if key in {"none", "null", "n/a", "na", "no data", "unknown"}:
        return None
    if stubs and key in stubs:
        return None
    return text


def confidential_owner(value: Any) -> bool:
    if value is True or value == 1:
        return True
    return str(value or "").strip().lower() in {"y", "yes", "true", "1"}


def http_url(value: Any) -> str | None:
    text = clean(value)
    if text and text.lower().startswith("http"):
        return text
    return None


def join_parts(attrs: dict, keys: list[str]) -> str | None:
    parts: list[str] = []
    for key in keys:
        text = clean(attrs.get(key))
        if not text or text in {"0", "00"}:
            continue
        parts.append(text)
    return " ".join(parts) or None


def person_name(first: Any, last: Any) -> str | None:
    first_text = clean(first)
    last_text = clean(last)
    if first_text and last_text:
        return f"{first_text} {last_text}"
    return last_text or first_text


def extent_tuple(extent: dict | None) -> tuple[float, float, float, float] | None:
    if not extent:
        return None
    try:
        return (float(extent["xmin"]), float(extent["ymin"]), float(extent["xmax"]), float(extent["ymax"]))
    except (KeyError, TypeError, ValueError):
        return None


def _centroid_inside(box: tuple[float, float, float, float], lon: float, lat: float) -> bool:
    xmin, ymin, xmax, ymax = box
    return xmin <= lon <= xmax and ymin <= lat <= ymax


def foreign_extent_reason(extent: tuple[float, float, float, float] | None) -> str | None:
    """Name the trap when a layer is not on the Treasure Coast."""
    if extent is None:
        return None
    xmin, ymin, xmax, ymax = extent
    lon = (xmin + xmax) / 2
    lat = (ymin + ymax) / 2
    if _centroid_inside(TUSCALOOSA_AL, lon, lat):
        return (
            "Tuscaloosa County, Alabama is not Indian River County, Florida. "
            "IRC on gisportal.ircgov.com is the county that was wired."
        )
    if _centroid_inside(OCOEE_ORANGE, lon, lat):
        return "City of Ocoee is in Orange County. It is not Okeechobee County."
    if lat < 0 or lon > 0:
        return "That extent is outside Florida. Melbourne, Australia is not Melbourne in Brevard County."
    return None


def martin_roll_is_thin_clip(extent: tuple[float, float, float, float] | None) -> bool:
    """True when a Martin parcel layer is an Indiantown-sized clip, not the county roll."""
    if extent is None:
        return True
    xmin, ymin, xmax, ymax = extent
    return (xmax - xmin) < 0.45 or (ymax - ymin) < 0.18


def fort_pierce_layer_role(layer_id: int, name: str) -> str:
    lowered = (name or "").lower()
    if layer_id == FORT_PIERCE_PROJECTS_LAYER or "project" in lowered:
        return "reject-projects"
    if "opportunity" in lowered:
        return "reject-not-designation"
    if layer_id == FORT_PIERCE_ZONING_LAYER or lowered == "zoning":
        return "zoning"
    if "future" in lowered or "land use" in lowered or "landuse" in lowered:
        return "flu"
    return "ignore"


def flu_info(code: str | None, label: str | None, jurisdiction: str, source: str) -> dict | None:
    if not code:
        return None
    return {
        "code": code,
        "label": label or code,
        "jurisdiction": jurisdiction,
        "source": source,
    }


def point_in_county(fips: str, lon: float, lat: float) -> bool:
    box = COUNTY_BBOX[fips]
    return box[0] <= lon <= box[2] and box[1] <= lat <= box[3]


class PolyIndex:
    def __init__(self) -> None:
        self.items: list[tuple[float, float, float, float, float, dict, dict]] = []

    def add(self, geometry: dict | None, payload: dict) -> bool:
        if not geometry or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            return False
        xs: list[float] = []
        ys: list[float] = []
        coords = geometry.get("coordinates") or []
        if geometry["type"] == "Polygon":
            rings = coords[:1]
        else:
            rings = [part[0] for part in coords if part]
        for ring in rings:
            for point in ring:
                xs.append(float(point[0]))
                ys.append(float(point[1]))
        if not xs:
            return False
        area = abs(signed_area(rings[0])) if rings else 0.0
        self.items.append((min(xs), min(ys), max(xs), max(ys), area, geometry, payload))
        return True

    def find(self, lon: float, lat: float) -> dict | None:
        best: dict | None = None
        best_area: float | None = None
        for minx, miny, maxx, maxy, area, geometry, payload in self.items:
            if lon < minx or lon > maxx or lat < miny or lat > maxy:
                continue
            if not contains_point(geometry, lon, lat):
                continue
            if best_area is None or area < best_area:
                best = payload
                best_area = area
        return best

    def __len__(self) -> int:
        return len(self.items)


def geometry_from_esri(raw: dict | None) -> dict | None:
    if not raw or not raw.get("rings"):
        return None
    geometry, _acres = _rings(raw["rings"])
    return geometry


def _rings(rings: list) -> tuple[dict | None, float]:
    geometry = esri_rings_to_geojson(rings)
    return geometry, net_acres(rings)


def _seed():
    import seed_market_parcels as seed

    return seed


def layer_extent(query_url: str) -> tuple[float, float, float, float] | None:
    seed = _seed()
    base = query_url.split("/query")[0]
    data = seed.fetch_json(base + "/query", {"where": "1=1", "returnExtentOnly": "true", "outSR": "4326", "f": "json"})
    return extent_tuple(data.get("extent"))


def guard_layer(query_url: str, label: str, *, martin_roll: bool = False) -> tuple[float, float, float, float] | None:
    extent = layer_extent(query_url)
    reason = foreign_extent_reason(extent)
    if reason:
        raise RuntimeError(f"Rejected {label} ({query_url}): {reason}")
    if martin_roll and martin_roll_is_thin_clip(extent):
        raise RuntimeError(
            f"Rejected {label} as a thin Martin clip ({extent}). "
            "The county roll on geoweb.martin.fl.us is wider than an Indiantown extract."
        )
    return extent


def fetch_features(query_url: str, where: str, fields: list[str], *, geometry: bool) -> list[dict]:
    seed = _seed()
    ids = seed.fetch_object_ids(query_url, where)
    print(f"    {where[:80]} -> {len(ids)}", flush=True)
    features: list[dict] = []
    batch = 80 if geometry else 200
    for start in range(0, len(ids), batch):
        chunk = ids[start : start + batch]
        params = {
            "objectIds": ",".join(str(i) for i in chunk),
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "outSR": "4326",
            "f": "json",
        }
        data = seed.fetch_json(query_url, params, timeout=180)
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        features.extend(data.get("features") or [])
        if start == 0 or start + batch >= len(ids) or (start // batch) % 8 == 0:
            print(f"    fetched {min(start + batch, len(ids))}/{len(ids)}", flush=True)
    return features


def index_polygons(features: list[dict], payload_of: Callable[[dict], dict | None]) -> PolyIndex:
    index = PolyIndex()
    for feature in features:
        payload = payload_of(feature.get("attributes") or {})
        if not payload:
            continue
        geometry = geometry_from_esri(feature.get("geometry"))
        index.add(geometry, payload)
    return index


def muni_index(features: list[dict], name_field: str) -> PolyIndex:
    def payload(attrs: dict) -> dict | None:
        name = place_name(attrs.get(name_field))
        if not name:
            return None
        return {"name": name}

    return index_polygons(features, payload)


def code_index(
    features: list[dict],
    code_field: str,
    label_field: str | None = None,
    stubs: set[str] | None = None,
) -> PolyIndex:
    def payload(attrs: dict) -> dict | None:
        code = usable_code(attrs.get(code_field), stubs)
        if not code:
            return None
        label = clean(attrs.get(label_field)) if label_field else None
        return {"code": code, "label": label or code}

    return index_polygons(features, payload)


def empty_parcel(**kwargs: Any) -> dict:
    return _seed().empty_feature(**kwargs)


def apply_land_use(
    feature: dict,
    *,
    jurisdiction: str | None,
    zoning: dict | None,
    flu: dict | None,
    appraiser: str | None,
) -> None:
    props = feature["properties"]
    props["jurisdictionCode"] = jurisdiction
    if zoning:
        props["zoningCode"] = zoning["code"]
    if flu:
        props["flu"] = flu
    if appraiser:
        props["appraiserUrl"] = appraiser


def remember(stats: dict, key: str) -> None:
    stats[key] = stats.get(key, 0) + 1


def pull_indian_river(county: dict, markets: list[str]) -> tuple[list[dict], dict, list[str]]:
    parcels_url = SPECS["12061"]["query"]
    zoning_url = "https://gisportal.ircgov.com/server3/rest/services/Planning/IRC_Zoning_MS/MapServer/0/query"
    flu_url = "https://gisportal.ircgov.com/server3/rest/services/Planning/IRC_Future_Land_Use_MS/MapServer/0/query"
    muni_url = "https://gisportal.ircgov.com/server3/rest/services/IRCPA/Municipal_Boundaries_MS/MapServer/0/query"
    vero_zoning_url = "https://services1.arcgis.com/mK9abRqiJFkUgbPZ/arcgis/rest/services/ZoningDistricts/FeatureServer/0/query"
    vero_flu_url = "https://services1.arcgis.com/mK9abRqiJFkUgbPZ/arcgis/rest/services/ZoningFutureLandUse/FeatureServer/0/query"
    seb_zoning_url = "https://services3.arcgis.com/NkT47EHQsmn9GxB3/arcgis/rest/services/City_of_Sebastian_Zoning_Web_Map_WFL1/FeatureServer/3/query"
    seb_flu_url = "https://services3.arcgis.com/NkT47EHQsmn9GxB3/arcgis/rest/services/Future_Land_Use/FeatureServer/0/query"
    guard_layer(parcels_url, "Indian River parcels")
    guard_layer(vero_zoning_url, "Vero Beach zoning")
    print("  Indian River overlays", flush=True)
    places = muni_index(
        fetch_features(muni_url, "1=1", ["CITY_NAME2", "SHORT_NAME"], geometry=True),
        "CITY_NAME2",
    )
    county_zoning = code_index(
        fetch_features(zoning_url, "1=1", ["ZONING", "ZONING_ABV"], geometry=True),
        "ZONING",
    )
    county_flu = code_index(
        fetch_features(flu_url, "1=1", ["LAND_USE", "LandUse_Abv"], geometry=True),
        "LAND_USE",
        "LandUse_Abv",
    )
    vero_zoning = code_index(
        fetch_features(vero_zoning_url, "1=1", ["Code", "Description"], geometry=True),
        "Code",
        "Description",
    )
    vero_flu = code_index(
        fetch_features(vero_flu_url, "1=1", ["Code", "Description"], geometry=True),
        "Code",
        "Description",
    )
    seb_zoning = code_index(
        fetch_features(seb_zoning_url, "1=1", ["ZONING", "ZONE_NAME"], geometry=True),
        "ZONING",
        "ZONE_NAME",
    )
    seb_flu = code_index(
        fetch_features(seb_flu_url, "1=1", ["FLU"], geometry=True),
        "FLU",
    )
    city_zoning = {"Vero Beach": vero_zoning, "Sebastian": seb_zoning}
    city_flu = {"Vero Beach": vero_flu, "Sebastian": seb_flu}
    city_sources = {
        "Vero Beach": (
            "https://services1.arcgis.com/mK9abRqiJFkUgbPZ/arcgis/rest/services/ZoningDistricts/FeatureServer/0",
            "https://services1.arcgis.com/mK9abRqiJFkUgbPZ/arcgis/rest/services/ZoningFutureLandUse/FeatureServer/0",
        ),
        "Sebastian": (
            "https://services3.arcgis.com/NkT47EHQsmn9GxB3/arcgis/rest/services/City_of_Sebastian_Zoning_Web_Map_WFL1/FeatureServer/3",
            "https://services3.arcgis.com/NkT47EHQsmn9GxB3/arcgis/rest/services/Future_Land_Use/FeatureServer/0",
        ),
    }
    raw = fetch_features(
        parcels_url,
        SPECS["12061"]["where"],
        [
            "PP_PIN",
            "OWNER_NAME",
            "SITE_ADDR",
            "AD_CITY",
            "AD_ZIP",
            "LAND_ACRES",
            "PROPUSE_CD",
            "SALE_YEAR",
            "SALE_MONTH",
            "SALE_PRICE",
            "CAMA_VALUE",
            "TAXES",
            "OWN_ADDR1",
            "OWN_ADDR2",
            "OWN_CITY",
            "OWN_STATE",
            "OWN_ZIP",
            "LINK_TO_PA",
        ],
        geometry=True,
    )
    stats: dict[str, int] = {}
    features = _assemble(
        county,
        markets,
        raw,
        source=SPECS["12061"]["source"],
        places=places,
        city_zoning=city_zoning,
        city_flu=city_flu,
        county_zoning=county_zoning,
        county_flu=county_flu,
        county_zoning_jurisdiction="Unincorporated Indian River",
        county_flu_jurisdiction="Unincorporated Indian River",
        zoning_source="irc-unincorporated-zoning",
        flu_source="irc-unincorporated-flu",
        stats=stats,
        identify=lambda attrs: parcel_pin(attrs.get("PP_PIN")),
        acres_of=lambda attrs, _geom: num(attrs.get("LAND_ACRES")),
        fields=lambda attrs: {
            "owner": clean(attrs.get("OWNER_NAME")),
            "situs": clean(attrs.get("SITE_ADDR")),
            "city": place_name(attrs.get("AD_CITY")) or clean(attrs.get("AD_CITY")),
            "zip": zip_str(attrs.get("AD_ZIP")),
            "dor": clean(attrs.get("PROPUSE_CD")),
            "sale_price": num(attrs.get("SALE_PRICE")),
            "sale_date": sale_year_month(attrs.get("SALE_YEAR"), attrs.get("SALE_MONTH")),
            "market_value": num(attrs.get("CAMA_VALUE")),
            "taxes": num(attrs.get("TAXES")),
            "mail1": clean(attrs.get("OWN_ADDR1")),
            "mail2": clean(attrs.get("OWN_ADDR2")),
            "mail_city": clean(attrs.get("OWN_CITY")),
            "mail_state": clean(attrs.get("OWN_STATE")),
            "mail_zip": zip_str(attrs.get("OWN_ZIP")),
            "appraiser": http_url(attrs.get("LINK_TO_PA")) or "https://www.ircpa.org/",
        },
    )
    no_city_gis = ["Fellsmere", "Indian River Shores", "Orchid"]
    extra = _muni_extra(
        places,
        city_sources,
        stats,
        no_city_gis,
        unincorporated={
            "zoningUrl": zoning_url.split("/query")[0],
            "fluUrl": flu_url.split("/query")[0],
            "zoningFeatures": len(county_zoning),
            "fluFeatures": len(county_flu),
            "zoningJoined": stats.get("county-zoning", 0),
            "fluJoined": stats.get("county-flu", 0),
            "note": "IRC_Zoning_MS is the unincorporated area. It does not cover Vero Beach or Sebastian.",
        },
    )
    gaps = [
        REJECT_NOTES["12061"],
        ELIGIBLE_NOTE,
        "Fellsmere, Indian River Shores, and Orchid are municipalities on the county boundary layer and have no public zoning or FLU FeatureServer. Their parcels stay blank rather than inheriting unincorporated districts.",
        "County COS/COS_Zoning is the Sebastian mirror on the county server. The city zoning and FLU services are the ones joined.",
        "COVB on gisportal.ircgov.com requires a token. Vero Beach zoning and FLU come from the city's public FeatureServers.",
        "Assessed and taxable value are not on the property-appraiser parcel service. CAMA_VALUE is stored as tax.marketValue and TAXES as tax.taxes. SALE_VI_CD is not treated as a qualified-sale flag.",
        "No owner phone or email fields are copied.",
    ]
    extra["zoningJoinedCount"] = stats.get("county-zoning", 0) + stats.get("city-zoning", 0)
    extra["fluJoinedCount"] = stats.get("county-flu", 0) + stats.get("city-flu", 0)
    return features, extra, gaps


def pull_st_lucie(county: dict, markets: list[str]) -> tuple[list[dict], dict, list[str]]:
    parcels_url = SPECS["12111"]["query"]
    muni_url = "https://slcgis.stlucieco.gov/hosting/rest/services/Municipal/MunicipalBoundaries/MapServer/0/query"
    zoning_url = "https://slcgis.stlucieco.gov/hosting/rest/services/LandUse/Zoning/MapServer/0/query"
    flu_url = "https://slcgis.stlucieco.gov/hosting/rest/services/LandUse/FutureLandUse/MapServer/0/query"
    fp_zoning_url = "https://services1.arcgis.com/oDRzuf2MGmdEHAbQ/arcgis/rest/services/Zoning/FeatureServer/7/query"
    fp_flu_url = "https://services1.arcgis.com/oDRzuf2MGmdEHAbQ/arcgis/rest/services/FutureLandUse/FeatureServer/0/query"
    psl_zoning_url = "https://services1.arcgis.com/YdUP5V6WwzeG8T8r/arcgis/rest/services/Zoning/FeatureServer/1/query"
    psl_flu_url = "https://services1.arcgis.com/YdUP5V6WwzeG8T8r/arcgis/rest/services/LandUse/FeatureServer/0/query"
    role = fort_pierce_layer_role(0, "Current Project Development")
    if role != "reject-projects":
        raise RuntimeError("Fort Pierce layer 0 must stay rejected as projects")
    if fort_pierce_layer_role(7, "Zoning") != "zoning":
        raise RuntimeError("Fort Pierce zoning must be layer 7")
    if fort_pierce_layer_role(9, "Opportunity Zones") != "reject-not-designation":
        raise RuntimeError("Fort Pierce opportunity-zone layer must not be joined")
    guard_layer(parcels_url, "St. Lucie parcels")
    guard_layer(fp_zoning_url, "Fort Pierce zoning")
    print("  St. Lucie overlays", flush=True)
    places = muni_index(fetch_features(muni_url, "1=1", ["City"], geometry=True), "City")
    county_zoning = code_index(
        fetch_features(zoning_url, "Acres>=5 AND Acres<=150", ["Zoned", "Acres"], geometry=True),
        "Zoned",
    )
    county_flu = code_index(
        fetch_features(flu_url, "Area_ac>=5 AND Area_ac<=150", ["flucode", "Area_ac"], geometry=True),
        "flucode",
    )
    fp_zoning = code_index(
        fetch_features(fp_zoning_url, "Acre>=5 AND Acre<=150", ["Zoning", "ZoningDescription", "Acre"], geometry=True),
        "Zoning",
        "ZoningDescription",
    )
    fp_flu = code_index(
        fetch_features(fp_flu_url, "Acre>=5 AND Acre<=150", ["FutureLand", "LandUseDes", "Acre"], geometry=True),
        "FutureLand",
        "LandUseDes",
    )
    psl_zoning = code_index(
        fetch_features(psl_zoning_url, "1=1", ["ZOLEGEND", "ZONING"], geometry=True),
        "ZOLEGEND",
        "ZONING",
    )
    psl_flu = code_index(
        fetch_features(psl_flu_url, "1=1", ["LUCODE", "LULEGEND"], geometry=True),
        "LUCODE",
        "LULEGEND",
    )
    raw = fetch_features(
        parcels_url,
        SPECS["12111"]["where"],
        [
            "ParcelID",
            "PARCEL_NUMBER",
            "StreetNumber",
            "LocDirection",
            "StreetName",
            "LocationCity",
            "CuO1LastName",
            "CuO1FirstName",
            "CuO2LastName",
            "CuO2FirstName",
            "CuOStreet1",
            "CuOStreet2",
            "CuOCity",
            "CuOState",
            "CuOPostal",
            "LUC",
            "TOTAL_ACRE",
            "TotalAppraisedValue",
            "IsConfidential",
            "WebLink",
        ],
        geometry=True,
    )
    stats: dict[str, int] = {}
    features = _assemble(
        county,
        markets,
        raw,
        source=SPECS["12111"]["source"],
        places=places,
        city_zoning={"Fort Pierce": fp_zoning, "Port St. Lucie": psl_zoning},
        city_flu={"Fort Pierce": fp_flu, "Port St. Lucie": psl_flu},
        county_zoning=county_zoning,
        county_flu=county_flu,
        county_zoning_jurisdiction="Unincorporated St. Lucie",
        county_flu_jurisdiction="Unincorporated St. Lucie",
        zoning_source="slc-unincorporated-zoning",
        flu_source="slc-unincorporated-flu",
        stats=stats,
        identify=lambda attrs: parcel_pin(attrs.get("PARCEL_NUMBER")) or parcel_pin(attrs.get("ParcelID")),
        acres_of=lambda attrs, _geom: num(attrs.get("TOTAL_ACRE")),
        fields=lambda attrs: {
            "owner": None
            if confidential_owner(attrs.get("IsConfidential"))
            else person_name(attrs.get("CuO1FirstName"), attrs.get("CuO1LastName")),
            "owner2": None
            if confidential_owner(attrs.get("IsConfidential"))
            else person_name(attrs.get("CuO2FirstName"), attrs.get("CuO2LastName")),
            "situs": join_parts(attrs, ["StreetNumber", "LocDirection", "StreetName"]),
            "city": place_name(attrs.get("LocationCity")) or clean(attrs.get("LocationCity")),
            "dor": clean(attrs.get("LUC")),
            "market_value": num(attrs.get("TotalAppraisedValue")),
            "mail1": clean(attrs.get("CuOStreet1")),
            "mail2": clean(attrs.get("CuOStreet2")),
            "mail_city": clean(attrs.get("CuOCity")),
            "mail_state": clean(attrs.get("CuOState")),
            "mail_zip": zip_str(attrs.get("CuOPostal")),
            "appraiser": http_url(attrs.get("WebLink")) or "https://www.paslc.gov/",
        },
    )
    extra = _muni_extra(
        places,
        {
            "Fort Pierce": (fp_zoning_url.split("/query")[0], fp_flu_url.split("/query")[0]),
            "Port St. Lucie": (psl_zoning_url.split("/query")[0], psl_flu_url.split("/query")[0]),
        },
        stats,
        ["St. Lucie Village"],
        unincorporated={
            "zoningUrl": zoning_url.split("/query")[0],
            "fluUrl": flu_url.split("/query")[0],
            "zoningFeatures": len(county_zoning),
            "fluFeatures": len(county_flu),
            "zoningJoined": stats.get("county-zoning", 0),
            "fluJoined": stats.get("county-flu", 0),
            "note": "County zoning and FLU are the parcel-level MapServer, limited to the 5–150 acre band. The dissolved AGOL ZoningDistrictsCombined layer is not the zoning source.",
        },
    )
    gaps = [
        REJECT_NOTES["12111"],
        ELIGIBLE_NOTE,
        "St. Lucie Village is on the municipal boundary layer and has no public zoning or FLU service. Those parcels are not given county districts.",
        "Fort Pierce and Port St. Lucie zoning are the city layers. County zoning is unincorporated only.",
        "The parcel service has no sale date or price. TotalAppraisedValue is stored as tax.marketValue. Assessed, taxable, and a separate tax amount are not on this layer.",
        "Confidential owner flags blank the owner name. No phone or email is copied.",
    ]
    extra["zoningJoinedCount"] = stats.get("county-zoning", 0) + stats.get("city-zoning", 0)
    extra["fluJoinedCount"] = stats.get("county-flu", 0) + stats.get("city-flu", 0)
    return features, extra, gaps


def pull_brevard(county: dict, markets: list[str]) -> tuple[list[dict], dict, list[str]]:
    parcels_url = SPECS["12009"]["query"]
    zoning_url = "https://gis.brevardfl.gov/gissrv/rest/services/Accela/AccelaGIS_Layers_WKID2881/MapServer/7/query"
    flu_url = "https://gis.brevardfl.gov/gissrv/rest/services/Accela/AccelaGIS_Layers_WKID2881/MapServer/8/query"
    city_url = "https://gis.brevardfl.gov/gissrv/rest/services/Base_Map/General_WKID2881/MapServer/5/query"
    guard_layer(parcels_url, "Brevard Accela parcels")
    guard_layer(zoning_url, "Brevard Accela zoning")
    print("  Brevard Accela overlays", flush=True)
    places = muni_index(fetch_features(city_url, "1=1", ["CITY_NAME"], geometry=True), "CITY_NAME")
    county_zoning = code_index(
        fetch_features(zoning_url, "1=1", ["ZONING"], geometry=True),
        "ZONING",
    )
    county_flu = code_index(
        fetch_features(flu_url, "1=1", ["FLU"], geometry=True),
        "FLU",
    )
    raw = fetch_features(
        parcels_url,
        SPECS["12009"]["where"],
        [
            "PARCEL_ID",
            "ACRES",
            "USE_CODE",
            "STREET_NUMBER",
            "STREET_DIRECTION_PREFIX",
            "STREET_NAME",
            "STREET_TYPE",
            "CITY",
            "ZIP_CODE",
            "OWNER_NAME1",
            "OWNER_NAME2",
            "OWNER_STREET_NAME",
            "OWNER_ADDRESS2",
            "OWNER_CITY",
            "OWNER_STATE",
            "OWNER_ZIP5",
            "LAND_VALUE",
            "BLDG_VALUE",
        ],
        geometry=True,
    )
    stats: dict[str, int] = {}
    features = _assemble(
        county,
        markets,
        raw,
        source=SPECS["12009"]["source"],
        places=places,
        city_zoning={},
        city_flu={},
        county_zoning=county_zoning,
        county_flu=county_flu,
        county_zoning_jurisdiction="Unincorporated Brevard",
        county_flu_jurisdiction="Unincorporated Brevard",
        zoning_source="brevard-accela-zoning",
        flu_source="brevard-accela-flu",
        stats=stats,
        identify=lambda attrs: parcel_pin(attrs.get("PARCEL_ID")),
        acres_of=lambda attrs, _geom: num(attrs.get("ACRES")),
        fields=lambda attrs: {
            "owner": clean(attrs.get("OWNER_NAME1")),
            "owner2": clean(attrs.get("OWNER_NAME2")),
            "situs": join_parts(attrs, ["STREET_NUMBER", "STREET_DIRECTION_PREFIX", "STREET_NAME", "STREET_TYPE"]),
            "city": place_name(attrs.get("CITY")) or clean(attrs.get("CITY")),
            "zip": zip_str(attrs.get("ZIP_CODE")),
            "dor": clean(attrs.get("USE_CODE")),
            "mail1": clean(attrs.get("OWNER_STREET_NAME")),
            "mail2": clean(attrs.get("OWNER_ADDRESS2")),
            "mail_city": clean(attrs.get("OWNER_CITY")),
            "mail_state": clean(attrs.get("OWNER_STATE")),
            "mail_zip": zip_str(attrs.get("OWNER_ZIP5")),
            "appraiser": "https://www.bcpao.us/PropertySearch/#/nav/Search",
        },
    )
    city_names = sorted({item[6]["name"] for item in places.items})
    extra = _muni_extra(places, {}, stats, city_names, unincorporated={
        "zoningUrl": zoning_url.split("/query")[0],
        "fluUrl": flu_url.split("/query")[0],
        "zoningFeatures": len(county_zoning),
        "fluFeatures": len(county_flu),
        "zoningJoined": stats.get("county-zoning", 0),
        "fluJoined": stats.get("county-flu", 0),
        "note": "Accela zoning and future land use cover unincorporated Brevard. A downtown Melbourne point does not hit the zoning layer. Incorporated cities are named from General/City and are not given county districts.",
    })
    gaps = [
        REJECT_NOTES["12009"],
        ELIGIBLE_NOTE,
        "Incorporated Brevard cities (the General map City layer) have no public city zoning or FLU FeatureServer in this pull. Melbourne, Palm Bay, Titusville, Cocoa, and the other cities stay blank. Accela is not used as their ordinance.",
        "Parcel_by_Municipality_Ownership is municipal-owned parcels, not city limits, and is not the municipality layer.",
        "The Accela parcel layer has land and building values but no just value, taxable value, sale price, or sale date. Those tax fields stay empty. The appraiser link is the BCPAO search page, not a parcel deep link.",
        "Situs CITY on the parcel is a post-office place (Mims, Merritt Island, and similar) and is not the legal city. Legal cities come from the City polygon.",
        "No owner phone or email is copied.",
    ]
    extra["zoningJoinedCount"] = stats.get("county-zoning", 0)
    extra["fluJoinedCount"] = stats.get("county-flu", 0)
    return features, extra, gaps


def pull_martin(county: dict, markets: list[str]) -> tuple[list[dict], dict, list[str]]:
    parcels_url = SPECS["12085"]["query"]
    zoning_url = "https://geoweb.martin.fl.us/arcgis/rest/services/Administrative_Areas/Future_Landuse_Zoning/MapServer/1/query"
    flu_url = "https://geoweb.martin.fl.us/arcgis/rest/services/Administrative_Areas/Future_Landuse_Zoning/MapServer/0/query"
    muni_url = "https://geoweb.martin.fl.us/arcgis/rest/services/Administrative_Areas/Administrative_Areas/MapServer/0/query"
    stuart_url = "https://services.arcgis.com/RyoFD3Lw9KSERnvQ/arcgis/rest/services/COS_Zoning/FeatureServer/0/query"
    indian_url = "https://services6.arcgis.com/fwjLUNzkr85qH0zV/arcgis/rest/services/voi_zoning_public/FeatureServer/0/query"
    guard_layer(parcels_url, "Martin parcels", martin_roll=True)
    guard_layer(stuart_url, "Stuart zoning")
    print("  Martin overlays", flush=True)
    places = muni_index(fetch_features(muni_url, "1=1", ["DESC_"], geometry=True), "DESC_")
    county_zoning = code_index(
        fetch_features(zoning_url, "1=1", ["ZONING", "ZONING_DETAILS"], geometry=True),
        "ZONING",
        "ZONING_DETAILS",
        MARTIN_ZONE_STUBS,
    )
    county_flu = code_index(
        fetch_features(flu_url, "1=1", ["FUTURE_LANDUSE", "FLUM_DETAILS"], geometry=True),
        "FUTURE_LANDUSE",
        "FLUM_DETAILS",
        MARTIN_ZONE_STUBS,
    )
    stuart = code_index(
        fetch_features(stuart_url, "1=1", ["ZONING", "ZONING_SUB"], geometry=True),
        "ZONING",
        "ZONING_SUB",
    )
    indiantown = code_index(
        fetch_features(indian_url, "1=1", ["Abbrev", "zoning"], geometry=True),
        "Abbrev",
        "zoning",
    )
    raw = fetch_features(
        parcels_url,
        SPECS["12085"]["where"],
        [
            "PCN",
            "OWNER",
            "MAIL_ADDRESS",
            "MAIL_CITY",
            "MAIL_STATE",
            "MAIL_ZIP",
            "SITUS_HOUSE_",
            "SITUS_PREFIX",
            "SITUS_STREET",
            "SITUS_STREET_TYPE",
            "SITUS_POST_DIR",
            "SITUS_CITY",
            "SITUS_ZIP",
            "DOR_CODE",
            "AREA_ACRES",
        ],
        geometry=True,
    )
    stats: dict[str, int] = {}
    features = _assemble(
        county,
        markets,
        raw,
        source=SPECS["12085"]["source"],
        places=places,
        city_zoning={"Stuart": stuart, "Indiantown": indiantown},
        city_flu={},
        county_zoning=county_zoning,
        county_flu=county_flu,
        county_zoning_jurisdiction="Unincorporated Martin",
        county_flu_jurisdiction="Unincorporated Martin",
        zoning_source="martin-unincorporated-zoning",
        flu_source="martin-unincorporated-flu",
        stats=stats,
        identify=lambda attrs: parcel_pin(attrs.get("PCN")),
        acres_of=lambda attrs, _geom: num(attrs.get("AREA_ACRES")),
        fields=lambda attrs: {
            "owner": clean(attrs.get("OWNER")),
            "situs": join_parts(attrs, ["SITUS_HOUSE_", "SITUS_PREFIX", "SITUS_STREET", "SITUS_STREET_TYPE", "SITUS_POST_DIR"]),
            "city": place_name(attrs.get("SITUS_CITY")) or clean(attrs.get("SITUS_CITY")),
            "zip": zip_str(attrs.get("SITUS_ZIP")),
            "dor": clean(attrs.get("DOR_CODE")),
            "mail1": clean(attrs.get("MAIL_ADDRESS")),
            "mail_city": clean(attrs.get("MAIL_CITY")),
            "mail_state": clean(attrs.get("MAIL_STATE")),
            "mail_zip": zip_str(attrs.get("MAIL_ZIP")),
            "appraiser": "https://geoweb.martin.fl.us/info/pi.html?pcn=" + (parcel_pin(attrs.get("PCN")) or ""),
        },
    )
    extra = _muni_extra(
        places,
        {
            "Stuart": (stuart_url.split("/query")[0], None),
            "Indiantown": (indian_url.split("/query")[0], None),
        },
        stats,
        ["Jupiter Island", "Sewall's Point", "Ocean Breeze"],
        unincorporated={
            "zoningUrl": zoning_url.split("/query")[0],
            "fluUrl": flu_url.split("/query")[0],
            "zoningFeatures": len(county_zoning),
            "fluFeatures": len(county_flu),
            "zoningJoined": stats.get("county-zoning", 0),
            "fluJoined": stats.get("county-flu", 0),
            "note": "County zoning values that are only a municipality name (STUART and the other towns) are stubs and are not joined. Stuart uses the city zoning service. Indiantown uses the village zoning service.",
        },
    )
    gaps = [
        REJECT_NOTES["12085"],
        ELIGIBLE_NOTE,
        "Jupiter Island, Sewall's Point, and Ocean Breeze have no public zoning or FLU service. County polygons that only name the town are not used as their districts.",
        "Stuart FLU was not on the city zoning service. Indiantown publishes zoning and not a separate FLU layer. County FLU is unincorporated only.",
        "The parcel layer has owner, situs, mailing, and AREA_ACRES. It has no sale price, sale date, or tax values.",
        "No owner phone or email is copied.",
    ]
    extra["zoningJoinedCount"] = stats.get("county-zoning", 0) + stats.get("city-zoning", 0)
    extra["fluJoinedCount"] = stats.get("county-flu", 0) + stats.get("city-flu", 0)
    return features, extra, gaps


def pull_okeechobee(county: dict, markets: list[str]) -> tuple[list[dict], dict, list[str]]:
    parcels_url = SPECS["12093"]["query"]
    zoning_url = "https://services3.arcgis.com/jE4lvuOFtdtz6Lbl/arcgis/rest/services/Zoning/FeatureServer/0/query"
    flu_url = "https://services3.arcgis.com/jE4lvuOFtdtz6Lbl/arcgis/rest/services/Future_Land_Use/FeatureServer/83/query"
    guard_layer(parcels_url, "Okeechobee parcels")
    guard_layer(zoning_url, "Okeechobee zoning")
    print("  Okeechobee overlays", flush=True)
    county_zoning = code_index(
        fetch_features(zoning_url, "ACRES>=5", ["Zoning", "DESCRIPTION", "ACRES"], geometry=True),
        "Zoning",
        "DESCRIPTION",
    )
    county_flu = code_index(
        fetch_features(flu_url, "1=1", ["FLU", "Label"], geometry=True),
        "FLU",
        "Label",
    )
    raw = fetch_features(
        parcels_url,
        "1=1",
        [
            "PARCELNO",
            "own1",
            "own2",
            "addr_1",
            "addr_2",
            "o_city",
            "o_state",
            "o_zip",
            "str_num",
            "str_predir",
            "str_name",
            "str_sfx",
            "str_postdi",
            "s_city",
            "s_zip",
        ],
        geometry=True,
    )
    for item in raw:
        rings = (item.get("geometry") or {}).get("rings") or []
        item.setdefault("attributes", {})["_computed_acres"] = net_acres(rings) if rings else None
    stats: dict[str, int] = {}

    def acres_of(attrs: dict, geometry: dict | None) -> float | None:
        del geometry
        return num(attrs.get("_computed_acres"))

    features = _assemble(
        county,
        markets,
        raw,
        source=SPECS["12093"]["source"],
        places=PolyIndex(),
        city_zoning={},
        city_flu={},
        county_zoning=county_zoning,
        county_flu=county_flu,
        county_zoning_jurisdiction="Okeechobee County",
        county_flu_jurisdiction="Okeechobee County",
        zoning_source="okeechobee-county-zoning",
        flu_source="okeechobee-county-flu",
        stats=stats,
        identify=lambda attrs: parcel_pin(attrs.get("PARCELNO")),
        acres_of=acres_of,
        fields=lambda attrs: {
            "owner": clean(attrs.get("own1")),
            "owner2": clean(attrs.get("own2")),
            "situs": join_parts(attrs, ["str_num", "str_predir", "str_name", "str_sfx", "str_postdi"]),
            "city": place_name(attrs.get("s_city")) or clean(attrs.get("s_city")),
            "zip": zip_str(attrs.get("s_zip")),
            "mail1": clean(attrs.get("addr_1")),
            "mail2": clean(attrs.get("addr_2")),
            "mail_city": clean(attrs.get("o_city")),
            "mail_state": clean(attrs.get("o_state")),
            "mail_zip": zip_str(attrs.get("o_zip")),
            "appraiser": "https://www.okeechobeepa.com/gis/",
        },
        countywide_when_no_city=True,
    )
    extra = {
        "municipalities": [
            {
                "name": "Okeechobee",
                "independentGis": False,
                "zoningUrl": None,
                "fluUrl": None,
                "fluGap": "The City of Okeechobee has no separate public zoning or FLU service. County zoning is not labeled as the city ordinance. Situs city Okeechobee is a post office name and is not a city-limits join.",
                "join": None,
                "zoningJoined": 0,
                "fluJoined": 0,
            }
        ],
        "unincorporated": {
            "zoningUrl": zoning_url.split("/query")[0],
            "fluUrl": flu_url.split("/query")[0],
            "zoningFeatures": len(county_zoning),
            "fluFeatures": len(county_flu),
            "zoningJoined": stats.get("county-zoning", 0),
            "fluJoined": stats.get("county-flu", 0),
            "note": "No public city-limits layer was found, so county zoning and FLU are joined for the whole county extent and tagged Okeechobee County.",
        },
        "zoningJoinedCount": stats.get("county-zoning", 0),
        "fluJoinedCount": stats.get("county-flu", 0),
    }
    gaps = [
        REJECT_NOTES["12093"],
        ELIGIBLE_NOTE,
        "Optional county, included because the county planning services are public and the extent is Okeechobee County. There is no acreage column. Acres are computed from the polygon and then limited to 5.0–150.0.",
        "The City of Okeechobee is not split out. County zoning is not a city ordinance.",
        "No sale price, sale date, or tax values are on the parcel service. The appraiser link is the public GIS page, not a parcel deep link.",
        "Zoning polygons with ACRES>=5 are the join. A zone smaller than 5 acres is not applied.",
        "No owner phone or email is copied.",
    ]
    return features, extra, gaps


PULLS = {
    "12061": pull_indian_river,
    "12111": pull_st_lucie,
    "12009": pull_brevard,
    "12085": pull_martin,
    "12093": pull_okeechobee,
}


def _muni_extra(
    places: PolyIndex,
    city_sources: dict[str, tuple[str | None, str | None]],
    stats: dict[str, int],
    missing: list[str],
    *,
    unincorporated: dict,
) -> dict:
    names = sorted({item[6]["name"] for item in places.items} | set(city_sources) | set(missing))
    municipalities = []
    for name in names:
        zoning_url, flu_url = city_sources.get(name, (None, None))
        has_gis = bool(zoning_url or flu_url)
        municipalities.append(
            {
                "name": name,
                "independentGis": has_gis,
                "zoningUrl": zoning_url,
                "fluUrl": flu_url,
                "fluGap": None if flu_url or not has_gis else "No public FLU layer for this municipality.",
                "join": "spatial" if has_gis else None,
                "zoningJoined": stats.get(f"city-zoning:{name}", 0),
                "fluJoined": stats.get(f"city-flu:{name}", 0),
                "note": None
                if has_gis
                else "No public zoning or FLU service. County districts are not copied onto this municipality.",
            }
        )
    return {"municipalities": municipalities, "unincorporated": unincorporated}


def _assemble(
    county: dict,
    markets: list[str],
    raw: list[dict],
    *,
    source: str,
    places: PolyIndex,
    city_zoning: dict[str, PolyIndex],
    city_flu: dict[str, PolyIndex],
    county_zoning: PolyIndex,
    county_flu: PolyIndex,
    county_zoning_jurisdiction: str,
    county_flu_jurisdiction: str,
    zoning_source: str,
    flu_source: str,
    stats: dict[str, int],
    identify: Callable[[dict], str | None],
    acres_of: Callable[[dict, dict | None], float | None],
    fields: Callable[[dict], dict],
    countywide_when_no_city: bool = False,
) -> list[dict]:
    fips = county["fips"]
    by_id: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry = geometry_from_esri(item.get("geometry"))
        if not geometry:
            continue
        center = representative_point(geometry)
        if not center or not point_in_county(fips, center[0], center[1]):
            continue
        acres = acres_of(attrs, geometry)
        if not in_band(acres):
            continue
        parcel_id = identify(attrs)
        if not parcel_id:
            continue
        mapped = fields(attrs)
        price = mapped.get("sale_price")
        if price is not None and price <= 0:
            price = None
        feature = empty_parcel(
            fips=fips,
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source=source,
            owner=mapped.get("owner"),
            situs=mapped.get("situs"),
            city=mapped.get("city"),
            zip_code=mapped.get("zip"),
            dor=mapped.get("dor"),
            sale_price=price,
            sale_date=mapped.get("sale_date"),
            market_value=mapped.get("market_value"),
            assessed=mapped.get("assessed"),
            taxable=mapped.get("taxable"),
            mail1=mapped.get("mail1"),
            mail2=mapped.get("mail2"),
            mail_city=mapped.get("mail_city"),
            mail_state=mapped.get("mail_state"),
            mail_zip=mapped.get("mail_zip"),
        )
        feature["properties"]["ownerName2"] = mapped.get("owner2")
        if mapped.get("taxes") is not None:
            feature["properties"]["tax"]["taxes"] = mapped.get("taxes")
        place = places.find(center[0], center[1])
        city = place["name"] if place else None
        if city and mapped.get("city"):
            feature["properties"]["situsCity"] = city
        elif city:
            feature["properties"]["situsCity"] = city
        zoning_hit = None
        flu_hit = None
        zoning_jurisdiction = None
        flu_jurisdiction = None
        zoning_layer = None
        flu_layer = None
        if city and city in city_zoning:
            zoning_hit = city_zoning[city].find(center[0], center[1])
            zoning_jurisdiction = city
            zoning_layer = f"{city} zoning"
            if zoning_hit:
                remember(stats, "city-zoning")
                remember(stats, f"city-zoning:{city}")
        elif city and not countywide_when_no_city:
            remember(stats, f"city-gap:{city}")
        elif county_zoning:
            zoning_hit = county_zoning.find(center[0], center[1])
            zoning_jurisdiction = county_zoning_jurisdiction
            zoning_layer = zoning_source
            if zoning_hit:
                remember(stats, "county-zoning")
        if city and city in city_flu:
            flu_hit = city_flu[city].find(center[0], center[1])
            flu_jurisdiction = city
            flu_layer = f"{city} FLU"
            if flu_hit:
                remember(stats, "city-flu")
                remember(stats, f"city-flu:{city}")
        elif city and not countywide_when_no_city:
            remember(stats, f"city-flu-gap:{city}")
        elif county_flu:
            flu_hit = county_flu.find(center[0], center[1])
            flu_jurisdiction = county_flu_jurisdiction
            flu_layer = flu_source
            if flu_hit:
                remember(stats, "county-flu")
        jurisdiction = city or (county_zoning_jurisdiction if countywide_when_no_city else ("Unincorporated" if zoning_hit or flu_hit else None))
        apply_land_use(
            feature,
            jurisdiction=jurisdiction,
            zoning=zoning_hit,
            flu=flu_info(
                flu_hit["code"] if flu_hit else None,
                flu_hit.get("label") if flu_hit else None,
                flu_jurisdiction or "",
                flu_layer or flu_source,
            ),
            appraiser=mapped.get("appraiser"),
        )
        if zoning_hit and zoning_jurisdiction:
            feature["properties"]["jurisdictionCode"] = zoning_jurisdiction
        elif flu_hit and flu_jurisdiction:
            feature["properties"]["jurisdictionCode"] = flu_jurisdiction
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    if not features:
        raise RuntimeError(f"{county['name']} produced no 5–150 acre parcels inside the county bbox")
    if not all(in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{fips} emitted a parcel outside 5–150 acres")
    print(f"  {county['name']} kept {len(features)} stats {stats}", flush=True)
    return features


def download_treasure_coast(county: dict, markets: list[str], spec: dict) -> dict:
    seed = _seed()
    pull = PULLS[county["fips"]]
    features, extra, gaps = pull(county, markets)
    path, lookup, tiles = seed.write_tiles(county, features)
    print(f"  wrote {len(features)} {county['name']} tiles", flush=True)
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
        gaps=gaps,
        source_count=len(features),
        dropped=0,
        tile_count=tiles,
        extra=extra,
    )
