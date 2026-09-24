"""Walton County, Georgia (FIPS 13297) 5–150 GIS-acre extract.

Landbase is choosewalton Walton_County_Zoning/29. The service is named Zoning,
but FLU and Description are character areas, not Euclidean districts. Owner,
mailing, tax, and sale are not on that layer. Monroe City Parcels join on
Parcel_No. Monroe, Loganville, and Social Circle Euclidean zoning join by
centroid because LG* and SC* names are not Parcel_No values.

waltongis walton_parcels_view is token/subscription blocked. This module does
not call it, does not use Walton County FL Beacon AppID=835, and does not use
ARC LandPro. Opportunity Zone fields stay empty.
"""

from __future__ import annotations

import json
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import seed_market_parcels as seed

SQM_PER_ACRE = 4046.8564224
WALTON_FIPS = "13297"
SOURCE = "ga-walton-choosewalton-parcels"
PARCELS_URL = (
    "https://services.arcgis.com/ftUt0Vfnzfo0Cs96/arcgis/rest/services/"
    "Walton_County_Zoning/FeatureServer/29/query"
)
MONROE_CAMA_URL = (
    "https://services9.arcgis.com/tX7O9qMhrJRPSGto/ArcGIS/rest/services/"
    "Monroe_Zoning___Character_Districts_Map_WFL1/FeatureServer/1/query"
)
MONROE_ZONING_URL = (
    "https://services9.arcgis.com/tX7O9qMhrJRPSGto/ArcGIS/rest/services/"
    "Monroe_Zoning___Character_Districts_Map_WFL1/FeatureServer/15/query"
)
MONROE_CHARACTER_URL = (
    "https://services9.arcgis.com/tX7O9qMhrJRPSGto/ArcGIS/rest/services/"
    "Monroe_Zoning___Character_Districts_Map_WFL1/FeatureServer/13/query"
)
LOGANVILLE_ZONING_URL = (
    "https://services.arcgis.com/ftUt0Vfnzfo0Cs96/arcgis/rest/services/"
    "Loganville_Zoning/FeatureServer/38/query"
)
SOCIAL_ZONING_URL = (
    "https://services.arcgis.com/ftUt0Vfnzfo0Cs96/arcgis/rest/services/"
    "Social_Circle_Zoning/FeatureServer/35/query"
)
LOGANVILLE_FLU_URL = (
    "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/"
    "NEGRC_Future_Development_Map_Inventory_WFL1/FeatureServer/468/query"
)
SOCIAL_FLU_URL = (
    "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/"
    "NEGRC_Future_Development_Map_Inventory_WFL1/FeatureServer/469/query"
)
WALNUT_FLU_URL = (
    "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/"
    "NEGRC_Future_Development_Map_Inventory_WFL1/FeatureServer/471/query"
)
APPRAISER_REPORT = (
    "https://qpublic.schneidercorp.com/Application.aspx?App=waltonCountyGA&Layer=Parcels&PageType=Report&KeyValue="
)

# Published choosewalton character areas. These are future land use, not zoning codes.
COUNTY_CHARACTER = {
    "Suburban",
    "Neighborhood Residential",
    "Conservation",
    "Rural Residential and Agriculture",
    "Highway Corridor",
    "Employment Center",
    "Village Center",
}

# Monroe City Parcels zoningcode uses R1 where the zoning map uses R-1.
MONROE_CAMA_ZONING = {
    "R1": "R-1",
    "R1A": "R-1A",
    "R2": "R-2",
    "R3": "R-3",
    "B1": "B-1",
    "B2": "B-2",
    "B3": "B-3",
    "M1": "M-1",
    "PRD": "PRD",
    "PCD": "PCD",
    "MIX": "MIX",
    "MH": "MH",
    "P": "P",
}

CHARACTER_NOTE = "County FLU/Description is a character area, not Euclidean zoning."
SALE_NOTE = "No public sale price or date."
CAMA_MISS = (
    "No countywide owner or tax. Monroe City Parcels did not match this Parcel_No. "
    "waltongis walton_parcels_view is not public (499/403)."
)
CAMA_HIT = (
    "Owner and market value are Monroe city CAMA only. "
    "Countywide owner, tax, and sales are not on a public layer."
)
ZONING_MISS = "No city Euclidean zoning hit. County zoning is qPublic HTML only."


def band_where() -> str:
    low = 5 * SQM_PER_ACRE
    high = 150 * SQM_PER_ACRE
    return f"Shape__Area>={low} AND Shape__Area<={high}"


def walton_ga_point(center: tuple[float, float] | None) -> bool:
    """Walton County, Georgia. Rejects Walton County, Florida (~-86, 30.4)."""
    if not center:
        return False
    lon, lat = center
    return -84.05 <= lon <= -83.40 and 33.50 <= lat <= 34.05


def part_key(part: dict) -> tuple:
    """Identical copied rings share area and centroid even if simplification jitters vertices."""
    center = seed.centroid_of(part["geometry"])
    area_key = round(part["area"])
    if not center:
        return ("no-center", area_key, id(part))
    return (area_key, round(center[0], 4), round(center[1], 4))


def combine_geometries(geometries: list[dict]) -> dict | None:
    parts: list = []
    for geometry in geometries:
        if geometry.get("type") == "Polygon":
            parts.append(geometry["coordinates"])
        elif geometry.get("type") == "MultiPolygon":
            parts.extend(geometry["coordinates"])
    if not parts:
        return None
    if len(parts) == 1:
        return {"type": "Polygon", "coordinates": parts[0]}
    return {"type": "MultiPolygon", "coordinates": parts}


def feature_bbox(feature: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if not node or isinstance(node, (int, float)):
            return
        if isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        for item in node:
            walk(item)

    walk((feature.get("geometry") or {}).get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def point_in_ring(x: float, y: float, ring: list) -> bool:
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


class GridIndex:
    def __init__(self, cell: float = 0.012) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = feature_bbox(feature)
        if not bbox:
            return
        west, south, east, north = bbox
        ix0 = int(west // self.cell)
        ix1 = int(east // self.cell)
        iy0 = int(south // self.cell)
        iy1 = int(north // self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 80:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        ix = int(x // self.cell)
        iy = int(y // self.cell)
        for feature in self.buckets.get((ix, iy), []):
            if point_in_feature(x, y, feature):
                return feature
        for feature in self.broad:
            if point_in_feature(x, y, feature):
                return feature
        return None


def load_raw(name: str, url: str, fields: list[str], where: str, *, geometry: bool, batch: int) -> list[dict]:
    folder = seed.CACHE_DIR / "walton-raw"
    path = folder / f"{name}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        print(f"  raw cache {name} {len(cached)}", flush=True)
        return cached
    ids = seed.fetch_object_ids(url, where)
    print(f"  fetch {name} {len(ids)}", flush=True)
    raw = seed.fetch_by_ids(url, ids, fields, batch=batch, return_geometry=geometry)
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, separators=(",", ":")))
    return raw


def county_flu(code: str | None, label: str | None) -> dict | None:
    if not code and not label:
        return None
    return {
        "code": code or label,
        "label": label or code,
        "jurisdiction": "Walton County",
        "source": "ga-walton-choosewalton-character-flu",
    }


def owner_name(attrs: dict) -> str | None:
    last = seed.clean(attrs.get("lastname"))
    first = seed.clean(attrs.get("firstname"))
    middle = seed.clean(attrs.get("middle"))
    given = " ".join(part for part in (first, middle) if part)
    if last and given:
        return f"{last}, {given}"
    return last or given or None


def situs_line(attrs: dict) -> str | None:
    number = seed.num(attrs.get("house_no"))
    number_text = None
    if number is not None and number > 0:
        number_text = str(int(number)) if number.is_integer() else str(number)
    parts = [
        number_text,
        seed.clean(attrs.get("stdirect")),
        seed.clean(attrs.get("street_nam")),
        seed.clean(attrs.get("sttype")),
        seed.clean(attrs.get("unit")),
    ]
    text = " ".join(part for part in parts if part)
    return text or None


def monroe_zoning_label(raw: str | None) -> str | None:
    code = seed.clean(raw)
    if not code or "/" in code:
        return code
    return MONROE_CAMA_ZONING.get(code.upper(), code)


def zoning_props(attrs: dict, city: str, prefix: str) -> dict | None:
    code = seed.clean(attrs.get("ZONING") or attrs.get("Zoning"))
    if not code or code in COUNTY_CHARACTER:
        return None
    return {"zoningCode": code, "city": city, "prefix": prefix}


def flu_props(attrs: dict, jurisdiction: str, source: str, code_field: str, label_field: str) -> dict | None:
    code = seed.clean(attrs.get(code_field))
    label = seed.clean(attrs.get(label_field))
    if not code and not label:
        return None
    return {
        "code": code or label,
        "label": label or code,
        "jurisdiction": jurisdiction,
        "source": source,
    }


def index_polygons(raw: list[dict], prop_fn) -> GridIndex:
    index = GridIndex()
    for item in raw:
        geometry, _acres = seed.rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            continue
        props = prop_fn(item.get("attributes") or {})
        if not props:
            continue
        index.add({"type": "Feature", "geometry": geometry, "properties": props})
    return index


def dissolve_landbase(raw: list[dict], county: dict, markets: list[str]) -> tuple[list[dict], dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    stats = {
        "blankParcelRows": 0,
        "utilityRows": 0,
        "geometryDropped": 0,
        "outsideBand": 0,
        "outsideGeorgia": 0,
        "duplicateGroups": 0,
        "duplicateExtraRings": 0,
    }
    for item in raw:
        attrs = item.get("attributes") or {}
        parcel_id = seed.clean(attrs.get("Parcel_No"))
        if not parcel_id:
            stats["blankParcelRows"] += 1
            continue
        if parcel_id.upper() == "UTILITY":
            stats["utilityRows"] += 1
            continue
        area = seed.num(attrs.get("Shape__Area"))
        if area is None:
            stats["geometryDropped"] += 1
            continue
        acres = round(area / SQM_PER_ACRE, 4)
        if not seed.in_band(acres):
            stats["outsideBand"] += 1
            continue
        geometry, _computed = seed.rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            stats["geometryDropped"] += 1
            continue
        groups[parcel_id].append(
            {
                "acres": acres,
                "area": area,
                "geometry": geometry,
                "flu": seed.clean(attrs.get("FLU")),
                "description": seed.clean(attrs.get("Description")),
            }
        )

    features: list[dict] = []
    for parcel_id, parts in groups.items():
        unique: list[dict] = []
        seen: set[tuple] = set()
        for part in parts:
            signature = part_key(part)
            if signature in seen:
                continue
            seen.add(signature)
            unique.append(part)
        if not unique:
            stats["geometryDropped"] += len(parts)
            continue
        if len(unique) == 1:
            geometry = unique[0]["geometry"]
            acres = unique[0]["acres"]
            flu_code = unique[0]["flu"]
            flu_label = unique[0]["description"]
        else:
            acres = round(sum(part["area"] for part in unique) / SQM_PER_ACRE, 4)
            if not seed.in_band(acres):
                stats["outsideBand"] += len(parts)
                continue
            geometry = combine_geometries([part["geometry"] for part in unique])
            if not geometry:
                stats["geometryDropped"] += len(parts)
                continue
            flu_code = next((part["flu"] for part in unique if part["flu"]), None)
            flu_label = next((part["description"] for part in unique if part["description"]), None)
        center = seed.centroid_of(geometry)
        if not walton_ga_point(center):
            stats["outsideGeorgia"] += len(parts)
            continue
        if len(parts) > 1:
            stats["duplicateGroups"] += 1
            stats["duplicateExtraRings"] += len(parts) - 1
        feature = seed.empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,  # type: ignore[arg-type]
            source=SOURCE,
        )
        feature["properties"]["flu"] = county_flu(flu_code, flu_label)
        feature["properties"]["appraiserUrl"] = APPRAISER_REPORT + urllib.parse.quote(parcel_id)
        features.append(feature)
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    consumed = (
        stats["blankParcelRows"]
        + stats["utilityRows"]
        + stats["geometryDropped"]
        + stats["outsideBand"]
        + stats["outsideGeorgia"]
        + stats["duplicateExtraRings"]
        + len(features)
    )
    if consumed != len(raw):
        raise RuntimeError(f"Walton dissolve accounted {consumed} rows but downloaded {len(raw)}")
    return features, stats


def apply_monroe_cama(features: list[dict], raw: list[dict]) -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        parcel_id = seed.clean(attrs.get("Parcel_No"))
        if parcel_id:
            by_id[parcel_id.upper()] = attrs
    return by_id


def enrich(features: list[dict], cama: dict[str, dict], layers: dict[str, GridIndex]) -> dict:
    counts = {
        "monroeCamaMatched": 0,
        "monroeOwnerFilled": 0,
        "monroeMarketValueFilled": 0,
        "zoningMonroe": 0,
        "zoningLoganville": 0,
        "zoningSocialCircle": 0,
        "zoningMonroeCamaFallback": 0,
        "zoningUnmatched": 0,
        "fluCounty": 0,
        "fluMonroeCharacter": 0,
        "fluLoganville": 0,
        "fluSocialCircle": 0,
        "fluWalnutGrove": 0,
        "fluMissing": 0,
    }
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        parcel_key = str(props["parcelId"]).upper()
        cama_row = cama.get(parcel_key)
        if cama_row:
            counts["monroeCamaMatched"] += 1
            owner = owner_name(cama_row)
            if owner:
                props["ownerName"] = owner
                counts["monroeOwnerFilled"] += 1
            line1 = seed.clean(cama_row.get("address1"))
            line2 = seed.clean(cama_row.get("address2")) or seed.clean(cama_row.get("address3"))
            props["mailingAddress"] = {
                "line1": line1,
                "line2": line2,
                "city": seed.clean(cama_row.get("city")),
                "state": seed.clean(cama_row.get("state")),
                "zip": seed.zip_str(cama_row.get("zip_code")),
            }
            situs = situs_line(cama_row)
            if situs:
                props["situsAddress"] = situs
            props["situsCity"] = "Monroe"
            situs_zip = seed.zip_str(cama_row.get("zip"))
            if situs_zip:
                props["situsZip"] = situs_zip
            market_value = seed.num(cama_row.get("curr_val"))
            if market_value is not None and market_value > 0:
                props["tax"]["marketValue"] = market_value
                counts["monroeMarketValueFilled"] += 1

        zoning_hit = None
        zoning_key = None
        for key in ("monroeZoning", "loganvilleZoning", "socialCircleZoning"):
            layer = layers.get(key)
            if not layer:
                continue
            zoning_hit = layer.hit(lon, lat)
            if zoning_hit:
                zoning_key = key
                break
        if zoning_hit:
            zoning = zoning_hit["properties"]
            props["zoningCode"] = zoning["zoningCode"]
            props["jurisdictionPrefix"] = zoning["prefix"]
            props["jurisdictionCode"] = zoning["city"]
            if not props.get("situsCity"):
                props["situsCity"] = zoning["city"]
            counts[{"monroeZoning": "zoningMonroe", "loganvilleZoning": "zoningLoganville", "socialCircleZoning": "zoningSocialCircle"}[zoning_key]] += 1
        elif cama_row:
            fallback = monroe_zoning_label(cama_row.get("zoningcode"))
            if fallback and fallback not in COUNTY_CHARACTER:
                props["zoningCode"] = fallback
                props["jurisdictionPrefix"] = "MONROE"
                props["jurisdictionCode"] = "Monroe"
                counts["zoningMonroeCamaFallback"] += 1
            else:
                counts["zoningUnmatched"] += 1
        else:
            counts["zoningUnmatched"] += 1

        flu_hit = None
        flu_key = None
        for key in ("monroeCharacter", "loganvilleFlu", "socialCircleFlu", "walnutGroveFlu"):
            layer = layers.get(key)
            if not layer:
                continue
            flu_hit = layer.hit(lon, lat)
            if flu_hit:
                flu_key = key
                break
        if flu_hit:
            props["flu"] = flu_hit["properties"]
            counts[
                {
                    "monroeCharacter": "fluMonroeCharacter",
                    "loganvilleFlu": "fluLoganville",
                    "socialCircleFlu": "fluSocialCircle",
                    "walnutGroveFlu": "fluWalnutGrove",
                }[flu_key]
            ] += 1
        elif props.get("flu"):
            counts["fluCounty"] += 1
        else:
            counts["fluMissing"] += 1

        gaps = [CHARACTER_NOTE, SALE_NOTE]
        gaps.append(CAMA_HIT if cama_row else CAMA_MISS)
        if not props.get("zoningCode"):
            gaps.append(ZONING_MISS)
        props["dataGaps"] = gaps
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        if props.get("zoningCode") in COUNTY_CHARACTER:
            raise RuntimeError(f"{props['parcelId']} stored a character area as Euclidean zoning")
    return counts


def gap_lines(kept: int, source_band: int, dissolve_stats: dict, join_counts: dict, monroe_layer: int, layer_notes: list[str]) -> list[str]:
    return [
        (
            f"Kept {kept} Walton County, Georgia parcels in the inclusive 5–150 GIS-acre band "
            f"from choosewalton Walton_County_Zoning/29 ({source_band} source rows). "
            f"Duplicate Parcel_No rings were dissolved ({dissolve_stats['duplicateGroups']} duplicate groups, "
            f"{dissolve_stats['duplicateExtraRings']} extra rings). "
            f"Blank Parcel_No rows dropped: {dissolve_stats['blankParcelRows']}. "
            f"Shared UTILITY ids dropped: {dissolve_stats['utilityRows']}."
        ),
        (
            f"Monroe City Parcels CAMA matched {join_counts['monroeCamaMatched']} of {kept} kept parcels "
            f"(owner filled {join_counts['monroeOwnerFilled']}, curr_val filled {join_counts['monroeMarketValueFilled']}). "
            f"The Monroe layer has {monroe_layer} city parcels. Most Monroe Parcel_No values are M* or NM* and do not equal "
            "the county C* or N* numbers, so only shared Parcel_No values were joined. "
            "waltongis walton_parcels_view is token/subscription blocked (499/403), so there is no countywide owner, mailing, or tax."
        ),
        (
            "City Euclidean zoning spatial join: "
            f"Monroe {join_counts['zoningMonroe']}, Loganville {join_counts['zoningLoganville']}, "
            f"Social Circle {join_counts['zoningSocialCircle']}, "
            f"Monroe CAMA zoning fallback {join_counts['zoningMonroeCamaFallback']}, "
            f"unmatched {join_counts['zoningUnmatched']}. "
            "LG* and SC* names were not used as Parcel_No keys. "
            "County Euclidean zoning (A-1/R-1 and the rest of the county ordinance) is qPublic HTML only."
        ),
        (
            "FLU and Description on the county landbase are character areas "
            "(Suburban, Neighborhood Residential, Conservation, Rural Residential and Agriculture, "
            "Highway Corridor, Employment Center, Village Center), not Euclidean zoning. "
            f"City character/FLU replaced that label where the centroid hit: "
            f"Monroe character {join_counts['fluMonroeCharacter']}, "
            f"Loganville NEGRC {join_counts['fluLoganville']}, "
            f"Social Circle NEGRC {join_counts['fluSocialCircle']}, "
            f"Walnut Grove NEGRC {join_counts['fluWalnutGrove']}, "
            f"county character kept {join_counts['fluCounty']}."
        ),
        (
            "No public sale price or date. Monroe sale fields are unused. "
            "No countywide tax roll. Assessed value, taxable value, and tax amount were not on the public layers used here. "
            "Opportunity Zone and OZ 2.0 were not assigned."
        ),
        (
            "Rejected Walton County, Florida Beacon AppID=835 and ARC LandPro. "
            "This extract is Walton County, Georgia (FIPS 13297). "
            "Loganville zoning polygons can extend into Gwinnett; only Walton landbase parcels are included."
        ),
        *layer_notes,
    ]


def download_walton_county(county: dict, markets: list[str], spec: dict) -> dict:
    fips = county["fips"]
    if fips != WALTON_FIPS:
        raise RuntimeError(f"Walton loader called for {fips}")
    cache_path = seed.CACHE_DIR / f"{fips}.json"
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features:
            print(f"  cache hit Walton {len(features)}", flush=True)
            for feature in features:
                feature["properties"]["marketIds"] = markets
                feature["properties"]["opportunityZone"] = None
                feature["properties"]["oz2Eligibility"] = None
            path, lookup, tiles = seed.write_tiles(county, features)
            return seed.county_row(
                county,
                markets,
                feature_count=len(features),
                coverage=spec["coverage"],
                partition="tiles",
                path=path,
                lookup=lookup,
                source=SOURCE,
                query_url=PARCELS_URL,
                gaps=list(cached.get("gaps") or []),
                source_count=cached.get("sourceCount"),
                dropped=cached.get("dropped"),
                tile_count=tiles,
                stats=cached.get("stats"),
            )

    print(f"Pulling Walton County GA ({fips}) via {SOURCE}", flush=True)
    source_band = seed.count_where(PARCELS_URL, band_where())
    print(f"  source rows in 5–150 GIS acres {source_band}", flush=True)
    raw_parcels = load_raw(
        "landbase",
        PARCELS_URL,
        ["Parcel_No", "FLU", "Description", "Shape__Area"],
        band_where(),
        geometry=True,
        batch=80,
    )
    features, dissolve_stats = dissolve_landbase(raw_parcels, county, markets)
    if not features:
        raise RuntimeError("Walton landbase produced no 5–150 acre parcels")
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Walton emitted a parcel outside 5–150 acres")
    if any(feature["properties"]["centroid"][1] < 32 for feature in features):
        raise RuntimeError("Walton extract included a Florida-latitude centroid")

    layer_notes: list[str] = []
    jobs = [
        ("monroeCama", MONROE_CAMA_URL, ["Parcel_No", "lastname", "firstname", "middle", "address1", "address2", "address3", "city", "state", "zip_code", "house_no", "stdirect", "street_nam", "sttype", "unit", "zip", "zoningcode", "curr_val"], False, 200),
        ("monroeZoning", MONROE_ZONING_URL, ["ZONING", "PARCELNO"], True, 100),
        ("loganvilleZoning", LOGANVILLE_ZONING_URL, ["Name", "Zoning", "Description"], True, 100),
        ("socialCircleZoning", SOCIAL_ZONING_URL, ["Name", "Zoning", "Description"], True, 100),
        ("monroeCharacter", MONROE_CHARACTER_URL, ["DIST", "PLND_DST", "PD_ZNG"], True, 100),
        ("loganvilleFlu", LOGANVILLE_FLU_URL, ["FDM_Short", "FDM_Long"], True, 100),
        ("socialCircleFlu", SOCIAL_FLU_URL, ["FDM_Short", "FDM_Long"], True, 80),
        ("walnutGroveFlu", WALNUT_FLU_URL, ["FDM_Short", "FDM_Long"], True, 80),
    ]

    raw_layers: dict[str, list[dict]] = {}

    def run_job(job: tuple) -> tuple[str, list[dict] | None, str | None]:
        name, url, fields, geometry, batch = job
        try:
            return name, load_raw(name, url, fields, "1=1", geometry=geometry, batch=batch), None
        except Exception as exc:  # noqa: BLE001
            return name, None, str(exc)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run_job, job) for job in jobs]
        for future in as_completed(futures):
            name, raw, error = future.result()
            if error or raw is None:
                layer_notes.append(f"{name} failed to download ({error}). That join was skipped.")
                print(f"  {name} failed {error}", flush=True)
                continue
            raw_layers[name] = raw
            print(f"  {name} rows {len(raw)}", flush=True)

    cama = apply_monroe_cama(features, raw_layers.get("monroeCama") or [])
    try:
        monroe_layer = seed.count_where(MONROE_CAMA_URL, "1=1")
    except Exception as exc:  # noqa: BLE001
        monroe_layer = len(raw_layers.get("monroeCama") or [])
        layer_notes.append(f"Monroe CAMA count failed ({exc}). Used the downloaded row count.")

    layers = {
        "monroeZoning": index_polygons(
            raw_layers.get("monroeZoning") or [],
            lambda attrs: zoning_props(attrs, "Monroe", "MONROE"),
        ),
        "loganvilleZoning": index_polygons(
            raw_layers.get("loganvilleZoning") or [],
            lambda attrs: zoning_props(attrs, "Loganville", "LOGANVILLE"),
        ),
        "socialCircleZoning": index_polygons(
            raw_layers.get("socialCircleZoning") or [],
            lambda attrs: zoning_props(attrs, "Social Circle", "SOCIALCIRCLE"),
        ),
        "monroeCharacter": index_polygons(
            raw_layers.get("monroeCharacter") or [],
            lambda attrs: flu_props(attrs, "Monroe", "monroe-character-districts", "DIST", "DIST"),
        ),
        "loganvilleFlu": index_polygons(
            raw_layers.get("loganvilleFlu") or [],
            lambda attrs: flu_props(attrs, "Loganville", "negrc-loganville-flu-2022", "FDM_Short", "FDM_Long"),
        ),
        "socialCircleFlu": index_polygons(
            raw_layers.get("socialCircleFlu") or [],
            lambda attrs: flu_props(attrs, "Social Circle", "negrc-social-circle-ca-2025", "FDM_Short", "FDM_Long"),
        ),
        "walnutGroveFlu": index_polygons(
            raw_layers.get("walnutGroveFlu") or [],
            lambda attrs: flu_props(attrs, "Walnut Grove", "negrc-walnut-grove-flu-2022", "FDM_Short", "FDM_Long"),
        ),
    }
    join_counts = enrich(features, cama, layers)
    gaps = gap_lines(len(features), source_band, dissolve_stats, join_counts, monroe_layer, layer_notes)
    dropped = source_band - len(features)
    stats = {
        "sourceBandCount": source_band,
        "downloadedRows": len(raw_parcels),
        "kept": len(features),
        "monroeCamaLayerCount": monroe_layer,
        **dissolve_stats,
        **join_counts,
    }
    seed.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {"sourceCount": source_band, "dropped": dropped, "gaps": gaps, "stats": stats, "features": features},
            separators=(",", ":"),
        )
    )
    path, lookup, tiles = seed.write_tiles(county, features)
    print(
        f"  kept {len(features)} monroe cama {join_counts['monroeCamaMatched']} "
        f"zoning {join_counts['zoningMonroe']}/{join_counts['zoningLoganville']}/{join_counts['zoningSocialCircle']}",
        flush=True,
    )
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=SOURCE,
        query_url=PARCELS_URL,
        gaps=gaps,
        source_count=source_band,
        dropped=dropped,
        tile_count=tiles,
        stats=stats,
    )
