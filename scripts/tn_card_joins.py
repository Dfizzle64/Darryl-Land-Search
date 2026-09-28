"""Per-county joins from the Tennessee research cards.

Geometry and owner stay on the OIR layer, except Hickman, Chester, and
Sevier. Sevier geometry and CAMA come from the county-hosted layer. This
module adds sale, mailing, zoning, and future-land-use layers that are
not already on that geometry source. Join URLs are read from
data/tn-rural-parcel-sources.json when the county block sets them.
AADT is not joined here.
"""

from __future__ import annotations

import math
from collections import defaultdict

from parcel_geometry import esri_rings_to_geojson, point_in_geometry

from tn_oir_parcels import (
    clean,
    fetch_object_ids,
    gis_keys,
    iter_by_ids,
    num,
    slash_date_to_iso,
    trailing_year,
)

OVERTON_QUERY = (
    "https://services1.arcgis.com/EMZFDxQzNQloLbAf/arcgis/rest/services/"
    "Overton_Parcels/FeatureServer/0/query"
)


def configured_url(row: dict, key: str, fallback: str) -> str:
    """Prefer the endpoint manifest so a card refresh is a JSON edit plus a re-run."""
    url = (row.get("joins") or {}).get(key)
    if isinstance(url, str) and url.strip():
        return url.strip()
    return fallback


def bbox_of(geometry: dict) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    coords = geometry.get("coordinates") or []
    if geometry.get("type") == "Polygon":
        parts = [coords]
    else:
        parts = coords
    for poly in parts:
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    if not xs:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


class ZoneGrid:
    def __init__(self, cell: float = 0.05) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)

    def add_many(self, items: list[dict]) -> None:
        for item in items:
            minx, miny, maxx, maxy = item["bbox"]
            ix0 = math.floor(minx / self.cell)
            ix1 = math.floor(maxx / self.cell)
            iy0 = math.floor(miny / self.cell)
            iy1 = math.floor(maxy / self.cell)
            for ix in range(ix0, ix1 + 1):
                for iy in range(iy0, iy1 + 1):
                    self.buckets[(ix, iy)].append(item)

    def stamp(self, features: list[dict], *, overwrite: bool) -> int:
        stamped = 0
        for feature in features:
            props = feature["properties"]
            if props.get("zoningCode") and not overwrite:
                continue
            lon, lat = props["centroid"]
            cell = (math.floor(lon / self.cell), math.floor(lat / self.cell))
            for item in self.buckets.get(cell, []):
                minx, miny, maxx, maxy = item["bbox"]
                if not (minx <= lon <= maxx and miny <= lat <= maxy):
                    continue
                if not point_in_geometry(lon, lat, item["geometry"]):
                    continue
                props["zoningCode"] = item["code"]
                props["zoningDistrict"] = item.get("label")
                stamped += 1
                break
        return stamped

    def stamp_flu(self, features: list[dict], jurisdiction: str, source: str) -> int:
        stamped = 0
        for feature in features:
            props = feature["properties"]
            lon, lat = props["centroid"]
            cell = (math.floor(lon / self.cell), math.floor(lat / self.cell))
            for item in self.buckets.get(cell, []):
                minx, miny, maxx, maxy = item["bbox"]
                if not (minx <= lon <= maxx and miny <= lat <= maxy):
                    continue
                if not point_in_geometry(lon, lat, item["geometry"]):
                    continue
                props["flu"] = {
                    "code": item["code"],
                    "label": item.get("label") or item["code"],
                    "jurisdiction": jurisdiction,
                    "source": source,
                }
                stamped += 1
                break
        return stamped


def attr_get(attrs: dict, name: str | None):
    if not name:
        return None
    if name in attrs:
        return attrs[name]
    lowered = name.lower()
    for key, value in attrs.items():
        if key.lower() == lowered:
            return value
    return None


def load_polygons(
    url: str,
    *,
    code_field: str | None,
    label_field: str | None = None,
    code_constant: str | None = None,
    where: str = "1=1",
) -> list[dict]:
    fields = [name for name in (code_field, label_field) if name]
    if not fields:
        fields = ["*"]
    ids = fetch_object_ids(url, where)
    items: list[dict] = []
    for page in iter_by_ids(url, ids, fields, geometry=True, batch=60):
        for raw in page:
            rings = (raw.get("geometry") or {}).get("rings")
            geometry = esri_rings_to_geojson(rings or [], simplify=False)
            if not geometry:
                continue
            attrs = raw.get("attributes") or {}
            code = code_constant or clean(attr_get(attrs, code_field))
            if not code:
                continue
            label = clean(attr_get(attrs, label_field)) if label_field else None
            items.append({"geometry": geometry, "code": code, "label": label, "bbox": bbox_of(geometry)})
    return items


def try_polygons(label: str, url: str, notes: list[str], **kwargs) -> list[dict] | None:
    try:
        items = load_polygons(url, **kwargs)
        print(f"    {label}: {len(items)} polygons", flush=True)
        return items
    except Exception as exc:  # noqa: BLE001
        print(f"    {label} failed: {exc}", flush=True)
        notes.append(f"{label} was on the research card but the query failed ({exc}). Zoning was not invented.")
        return None


def attribute_index(url: str, id_field: str, fields: list[str]) -> dict[str, dict]:
    ids = fetch_object_ids(url, "1=1")
    index: dict[str, dict] = {}
    wanted = list(dict.fromkeys([id_field, *fields]))
    for page in iter_by_ids(url, ids, wanted, geometry=False, batch=400):
        for raw in page:
            attrs = raw.get("attributes") or {}
            for key in gis_keys(attr_get(attrs, id_field)):
                index.setdefault(key, attrs)
    return index


def match_attrs(feature: dict, index: dict[str, dict]) -> dict | None:
    for key in gis_keys(feature["properties"].get("parcelId")):
        found = index.get(key)
        if found:
            return found
    return None


def stamp_attribute_zoning(features: list[dict], index: dict[str, dict], code_field: str, *, overwrite: bool) -> int:
    stamped = 0
    for feature in features:
        props = feature["properties"]
        if props.get("zoningCode") and not overwrite:
            continue
        attrs = match_attrs(feature, index)
        if not attrs:
            continue
        code = clean(attr_get(attrs, code_field))
        if not code:
            continue
        props["zoningCode"] = code
        props["zoningDistrict"] = None
        stamped += 1
    return stamped


def sevierville_polygons(notes: list[str], row: dict) -> list[dict] | None:
    """Prefer the proposed abbreviation, then ZONE_, inside the city polygons only."""
    url = configured_url(
        row,
        "cityZoning",
        "https://gis.seviervilletn.org/arcgis/rest/services/DeptMaps/GIS_Department_Layers/MapServer/205/query",
    )
    try:
        ids = fetch_object_ids(url, "1=1")
        items: list[dict] = []
        for page in iter_by_ids(url, ids, ["ProposedZoneAbrev", "ZONE_", "ProposedZoneName"], geometry=True, batch=40):
            for raw in page:
                rings = (raw.get("geometry") or {}).get("rings")
                geometry = esri_rings_to_geojson(rings or [], simplify=False)
                if not geometry:
                    continue
                attrs = raw.get("attributes") or {}
                code = clean(attr_get(attrs, "ProposedZoneAbrev")) or clean(attr_get(attrs, "ZONE_"))
                if not code:
                    continue
                items.append(
                    {
                        "geometry": geometry,
                        "code": code,
                        "label": clean(attr_get(attrs, "ProposedZoneName")),
                        "bbox": bbox_of(geometry),
                    }
                )
        print(f"    Sevierville zoning: {len(items)} polygons", flush=True)
        return items
    except Exception as exc:  # noqa: BLE001
        notes.append(f"Sevierville city zoning query failed ({exc}). City zoning was not invented.")
        return None


def join_overton(features: list[dict], row: dict) -> dict:
    print("  Overton UCDD CAMA join", flush=True)
    index = attribute_index(
        configured_url(row, "cama", OVERTON_QUERY),
        "GISLINK",
        ["SALEDATE", "PRICE", "APPRAISAL", "MAILADDR", "MAILCITY", "STATE", "ZIP", "ZONING", "PARCELID"],
    )
    matched = sales = values = mailed = zoned = 0
    for feature in features:
        attrs = match_attrs(feature, index)
        if not attrs:
            continue
        matched += 1
        props = feature["properties"]
        year = trailing_year(attrs.get("PARCELID"))
        sold = slash_date_to_iso(attrs.get("SALEDATE"))
        price = num(attrs.get("PRICE"))
        if price is not None and price <= 0:
            price = None
        appraisal = num(attrs.get("APPRAISAL"))
        if appraisal is not None and appraisal <= 0:
            appraisal = None
        if sold or price is not None:
            sale = {"date": sold, "price": price, "qualified": None}
            if year:
                sale["vintage"] = year
            props["lastSale"] = sale
            sales += 1
        if appraisal is not None:
            props["tax"]["marketValue"] = appraisal
            if year:
                props["tax"]["vintage"] = year
            values += 1
        mail1 = clean(attrs.get("MAILADDR"))
        mail_city = clean(attrs.get("MAILCITY"))
        mail_state = clean(attrs.get("STATE"))
        mail_zip = clean(attrs.get("ZIP"))
        if mail1 or mail_city:
            props["mailingAddress"] = {
                "line1": mail1,
                "line2": None,
                "city": mail_city,
                "state": mail_state,
                "zip": mail_zip,
            }
            mailed += 1
        zone = clean(attrs.get("ZONING"))
        if zone:
            props["zoningCode"] = zone
            zoned += 1
    return {
        "overtonCamaMatched": matched,
        "overtonSaleCount": sales,
        "overtonAppraisalCount": values,
        "overtonMailCount": mailed,
        "overtonZoningCount": zoned,
    }


def add_grid(grid: ZoneGrid | None, items: list[dict] | None) -> ZoneGrid | None:
    if not items:
        return grid
    if grid is None:
        grid = ZoneGrid()
    grid.add_many(items)
    return grid


def join_zoning(features: list[dict], row: dict, notes: list[str]) -> dict:
    zoning_before = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_stamped = 0
    fips = row["fips"]
    if fips == "47001":
        print("  Anderson zoning attribute join", flush=True)
        try:
            index = attribute_index(
                configured_url(
                    row,
                    "zoning",
                    "https://services8.arcgis.com/vL7QLF4BNi1wukPE/arcgis/rest/services/AndersonTN_PSALayers/FeatureServer/3/query",
                ),
                "GISLINK",
                ["ZONING_1"],
            )
            stamped = stamp_attribute_zoning(features, index, "ZONING_1", overwrite=False)
            notes.append(
                f"Anderson zoning is AndersonTN_PSALayers ZONING_1 joined on GISLINK ({stamped} parcels). A code of CITY is the published city flag and was not resolved to a municipal district."
            )
        except Exception as exc:  # noqa: BLE001
            notes.append(f"AndersonTN_PSALayers zoning query failed ({exc}). Zoning was not invented.")
    elif fips == "47015":
        items = try_polygons(
            "Cannon zoning",
            configured_url(
                row,
                "zoning",
                "https://services1.arcgis.com/EMZFDxQzNQloLbAf/arcgis/rest/services/Cannon_County_Zoning_220331/FeatureServer/0/query",
            ),
            notes,
            code_field="ZONING",
        )
        grid = add_grid(None, items)
        if grid:
            grid.stamp(features, overwrite=False)
            notes.append("Cannon zoning is the four UCDD districts (A-1, C-1, I-1, R-1), stamped by centroid.")
    elif fips == "47043":
        # City polygons win over the unincorporated map.
        county = try_polygons(
            "Dickson County zoning",
            configured_url(
                row,
                "countyZoning",
                "https://services5.arcgis.com/o0K7afBI69raYtru/arcgis/rest/services/Dickson_County_Zoning/FeatureServer/0/query",
            ),
            notes,
            code_field="Zone_Curre",
            label_field="Zoning_Des",
        )
        city = try_polygons(
            "City of Dickson zoning",
            configured_url(
                row,
                "cityZoning",
                "https://services7.arcgis.com/Gld89lf779txw3q4/arcgis/rest/services/City_of_Dickson_Zoning_View/FeatureServer/0/query",
            ),
            notes,
            code_field="Current_Zo",
            label_field="Zoning_Des",
        )
        white_bluff = try_polygons(
            "White Bluff zoning",
            configured_url(
                row,
                "whiteBluffZoning",
                "https://services5.arcgis.com/o0K7afBI69raYtru/arcgis/rest/services/WhiteBluff_Zoning/FeatureServer/0/query",
            ),
            notes,
            code_field="Zone_Curre",
            label_field="ZoneDesc",
        )
        grid = add_grid(None, county)
        if grid:
            grid.stamp(features, overwrite=False)
        cities = ZoneGrid()
        if city:
            cities.add_many(city)
        if white_bluff:
            cities.add_many(white_bluff)
        if city or white_bluff:
            cities.stamp(features, overwrite=True)
        notes.append(
            "Dickson zoning is the unincorporated county layer, overwritten inside the City of Dickson and White Bluff polygons. Burns, Charlotte, Vanleer, and Slayden have no public zoning layer. Future land use is not on a public layer."
        )
    elif fips == "47147":
        flu_stamped += robertson_zoning(features, notes, row)
    elif fips == "47155":
        print("  Sevier zoning attribute join", flush=True)
        try:
            index = attribute_index(
                configured_url(
                    row,
                    "countyZoning",
                    "https://gis.seviervilletn.org/arcgis/rest/services/DeptMaps/SevierCountyZoning/MapServer/0/query",
                ),
                "GISLINK",
                ["Zoning"],
            )
            stamp_attribute_zoning(features, index, "Zoning", overwrite=False)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"SevierCountyZoning query failed ({exc}). Zoning was not invented.")
        city = sevierville_polygons(notes, row)
        if city:
            grid = ZoneGrid()
            grid.add_many(city)
            grid.stamp(features, overwrite=True)
        notes.append(
            "Sevier county zoning is SevierCountyZoning joined on GISLINK. Sevierville city zoning overwrites parcels whose centroids fall in that city layer. It is not applied outside the city."
        )
    elif fips == "47189":
        flu_stamped += wilson_zoning(features, notes, row)
    zoning_after = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_after = sum(1 for feature in features if feature["properties"].get("flu"))
    return {
        "zoningJoined": zoning_after,
        "zoningAdded": max(0, zoning_after - zoning_before),
        "fluJoined": flu_after or flu_stamped,
    }


def robertson_zoning(features: list[dict], notes: list[str], row: dict) -> int:
    print("  Robertson zoning", flush=True)
    try:
        index = attribute_index(
            configured_url(
                row,
                "unincorporatedZoning",
                "https://apnsgis4.apsu.edu/arcgis/rest/services/Robertson/RobertsonGIS/MapServer/9/query",
            ),
            "gislink",
            ["zoning"],
        )
        stamp_attribute_zoning(features, index, "zoning", overwrite=False)
    except Exception as exc:  # noqa: BLE001
        notes.append(
            f"APSU Robertson unincorporated zoning (2014 digitizing, card status partial) query failed ({exc})."
        )
    cities = ZoneGrid()
    springfield_root = configured_url(
        row,
        "springfieldRoot",
        "https://services6.arcgis.com/OvhYC4wRuXsRGdB3/arcgis/rest/services/Springfield_Current_Zoning/FeatureServer",
    )
    names = {
        1: "RS15",
        2: "Specific_Plan",
        3: "RS20_PUD",
        4: "RS20",
        5: "RS10",
        6: "RI",
        7: "R40",
        8: "R20_PUD",
        9: "R20",
        10: "R15",
        11: "R10_PUD",
        12: "R10",
        13: "R7_PUD",
        14: "R7",
        15: "MRO",
        16: "MPO",
        17: "MH",
        18: "CS",
        19: "CLS",
        20: "CG",
        21: "CC",
        22: "A_AG",
    }
    for layer_id, code in names.items():
        items = try_polygons(
            f"Springfield {code}",
            f"{springfield_root}/{layer_id}/query",
            notes,
            code_field=None,
            code_constant=code,
        )
        if items:
            cities.add_many(items)
    for label, url, code_field, label_field in (
        (
            "Greenbrier zoning",
            configured_url(
                row,
                "greenbrierZoning",
                "https://services3.arcgis.com/2J1sItLsWSeMbkZB/arcgis/rest/services/Zoning_Public_View/FeatureServer/0/query",
            ),
            "ZoneCode",
            "ZoneName",
        ),
        (
            "White House zoning",
            configured_url(
                row,
                "whiteHouseZoning",
                "https://gis.cityofwhitehouse.com/arcgis/rest/services/WhiteHouseTN_Zoning/FeatureServer/3/query",
            ),
            "ZONECLASS",
            "ZONEDESC",
        ),
        (
            "Millersville zoning",
            configured_url(
                row,
                "millersvilleZoning",
                "https://services.arcgis.com/jcrrmnzMsBOEAFJp/arcgis/rest/services/Millersville_Zoning_view/FeatureServer/5/query",
            ),
            "ZONE_2021",
            None,
        ),
        (
            "Adams zoning",
            configured_url(
                row,
                "adamsZoning",
                "https://apnsgis4.apsu.edu/arcgis/rest/services/Robertson/RobertsonGIS/MapServer/6/query",
            ),
            "zoning_1",
            "zone_id",
        ),
        (
            "Orlinda zoning",
            configured_url(
                row,
                "orlindaZoning",
                "https://apnsgis4.apsu.edu/arcgis/rest/services/Robertson/RobertsonGIS/MapServer/8/query",
            ),
            "zoning",
            "zone_id",
        ),
        (
            "Cedar Hill zoning",
            configured_url(
                row,
                "cedarHillZoning",
                "https://apnsgis4.apsu.edu/arcgis/rest/services/Robertson/RobertsonGIS/MapServer/7/query",
            ),
            "zone",
            "zoning",
        ),
    ):
        items = try_polygons(label, url, notes, code_field=code_field, label_field=label_field)
        if items:
            cities.add_many(items)
    cities.stamp(features, overwrite=True)
    flu_items = try_polygons(
        "White House future land use",
        configured_url(
            row,
            "whiteHouseFlu",
            "https://gis.cityofwhitehouse.com/arcgis/rest/services/WhiteHouseTN_CompPlan/FeatureServer/2/query",
        ),
        notes,
        code_field="Future_LU",
    )
    flu_count = 0
    if flu_items:
        flu_grid = ZoneGrid()
        flu_grid.add_many(flu_items)
        flu_count = flu_grid.stamp_flu(features, "White House", "WhiteHouseTN_CompPlan/2")
    notes.append(
        "Robertson zoning is APSU unincorporated zoning where a GISLINK matches, overwritten by Springfield, Greenbrier, White House, Millersville, Adams, Orlinda, and Cedar Hill polygons. City layers are not applied outside their polygons. White House future land use is stamped only inside that layer. Greenbrier, West Virginia was not used."
    )
    return flu_count


def wilson_zoning(features: list[dict], notes: list[str], row: dict) -> int:
    print("  Wilson zoning", flush=True)
    cities = ZoneGrid()
    lebanon = try_polygons(
        "Lebanon zoning",
        configured_url(
            row,
            "lebanonZoning",
            "https://maps.lebanontn.org/arcgis/rest/services/Hosted/Zoning_Districts/FeatureServer/0/query",
        ),
        notes,
        code_field="zone",
    )
    mtj = try_polygons(
        "Mt. Juliet zoning",
        configured_url(
            row,
            "mtJulietZoning",
            "https://utility.arcgis.com/usrsvcs/servers/5e2f5bfd27984da89b2e45a726d0e37b/rest/services/Planning___Zoning/FeatureServer/5/query",
        ),
        notes,
        code_field="Zone_Curre",
    )
    if lebanon:
        cities.add_many(lebanon)
    if mtj:
        cities.add_many(mtj)
    cities.stamp(features, overwrite=False)
    flu_items = try_polygons(
        "Mt. Juliet future land use",
        configured_url(
            row,
            "mtJulietFlu",
            "https://utility.arcgis.com/usrsvcs/servers/5e2f5bfd27984da89b2e45a726d0e37b/rest/services/Planning___Zoning/FeatureServer/1/query",
        ),
        notes,
        code_field="FLU_Lisa",
    )
    flu_count = 0
    if flu_items:
        flu_grid = ZoneGrid()
        flu_grid.add_many(flu_items)
        flu_count = flu_grid.stamp_flu(features, "Mt. Juliet", "Planning___Zoning/1")
    notes.append(
        "Wilson has no countywide zoning layer. Lebanon and Mt. Juliet zoning are stamped only where the centroid falls in those city polygons. Mt. Juliet future land use is the same kind of city-only stamp. Cookeville is not in Wilson."
    )
    return flu_count


def apply_card_details(features: list[dict], row: dict) -> dict:
    """Mutate features with card-specific sale, mailing, zoning, and FLU."""
    notes: list[str] = []
    stats: dict = {}
    fips = row["fips"]
    if fips == "47133":
        try:
            stats.update(join_overton(features, row))
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Overton UCDD CAMA join failed ({exc}). Sale and appraisal were not invented.")
        else:
            notes.append(
                "Overton has no countywide zoning FeatureServer. A non-blank ZONING value on the UCDD roll is kept. Future land use stays empty."
            )
    if fips in {"47001", "47015", "47043", "47147", "47155", "47189"}:
        try:
            stats.update(join_zoning(features, row, notes))
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Zoning join failed ({exc}). Zoning was not invented.")
    elif fips not in {"47023", "47133"}:
        notes.append(
            "No usable countywide zoning or future-land-use FeatureServer is on the research card. Those fields stay empty."
        )
    stats["gapNotes"] = notes
    return stats
