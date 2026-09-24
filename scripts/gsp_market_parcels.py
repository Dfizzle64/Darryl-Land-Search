#!/usr/bin/env python3
"""Greenville County and Spartanburg County 5–150 acre parcel enrich.

Public GIS only. Parcel attributes come from the county cadastral layer.
Zoning is joined from the municipal layers named on the county and city
cards. Coarse county EnerGov districts and wrong-geography layers are not
written as zoning.

  python3 scripts/gsp_market_parcels.py --self-check
"""

from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from typing import Any, Callable

import seed_market_parcels as seed

GREENVILLE_PARCELS = "https://www.gcgis.org/arcgis3/rest/services/GCGIA/GCGIA_FeatureAccess/FeatureServer/10/query"
GREENVILLE_ZONING = "https://www.gcgis.org/arcgis3/rest/services/GCGIA/GCGIA_FeatureAccess/FeatureServer/13/query"
GREENVILLE_CITY_ZONING = "https://citygis.greenvillesc.gov/arcgis/rest/services/AddressSearch/Regulation/MapServer/7/query"
GREER_ZONING = "https://services1.arcgis.com/bskBH6JV42oEWJvZ/arcgis/rest/services/Greer_UDO_ZoningMap/FeatureServer/0/query"
SPARTANBURG_PARCELS = "https://maps.spartanburgcounty.org/server/rest/services/GIS/CAMA_Parcels/FeatureServer/0/query"
SPARTANBURG_CITY_ZONING = "https://services9.arcgis.com/HoRra3ATPLGmyjn6/arcgis/rest/services/Zoning_Layer_2026/FeatureServer/0/query"
SPARTANBURG_CITY_PARCELS = "https://services9.arcgis.com/HoRra3ATPLGmyjn6/arcgis/rest/services/Parcel_Info_1_2026/FeatureServer/0/query"
SPARTANBURG_MUNICIPALITIES = "https://maps.spartanburgcounty.org/server/rest/services/BasemapFeatures/MapServer/4/query"
INMAN_ZONING = "https://services1.arcgis.com/V7y6OwUBYsqBoMer/arcgis/rest/services/City_of_Inman_Interactive_Zoning_Map___5_25_WFL1/FeatureServer/2/query"
WELLFORD_ZONING = "https://services3.arcgis.com/1ttwkTr24vz3npzH/arcgis/rest/services/WellfordZoning_Jan2026_WFL1/FeatureServer/2/query"
LYMAN_ZONING = "https://services7.arcgis.com/6RbHWnr6Sl6FYOC4/arcgis/rest/services/TOL_Zoning_Map_WFL1/FeatureServer"
ENERGOV_ZONING = "https://maps.spartanburgcounty.org/server/rest/services/EnerGov/Display_Map/MapServer/12/query"

GREENVILLE_APPRAISER = "https://www.greenvillecounty.org/AppsAS400/RealProperty/"
SPARTANBURG_APPRAISER = "https://www.spartanburgcounty.gov/288/Assessor-Property-Records-Search"

# County Zoning/13 JCODE values from the Greenville County card.
GREENVILLE_JCODE = {
    "45045": "Unincorporated Greenville County",
    "30850": "City of Greenville",
    "30985": "City of Greer",
    "45115": "City of Mauldin",
    "66580": "City of Simpsonville",
    "72430": "City of Travelers Rest",
    "27070": "City of Fountain Inn",
}

# Layer id is the district. Counts and names are from TOL_Zoning_Map_WFL1.
LYMAN_LAYERS = {
    11: "R-15",
    12: "R-8",
    13: "RPH",
    14: "MHP",
    15: "R-8/10",
    16: "RM",
    17: "RBD",
    18: "NBD",
    19: "CBD",
    20: "GBD1",
    21: "GBD2",
    22: "GI",
}

# Higher priority wins. City layers outrank the county JCODE fallback.
PRIORITY_COUNTY = 10
PRIORITY_LYMAN = 25
PRIORITY_CITY_ATTRIBUTE = 30
PRIORITY_CITY = 40

CACHE_VERSION = "gsp-v1"


def epoch_date(value: Any) -> str | None:
    """ArcGIS epoch milliseconds. Calendar date is the UTC date.

    County services store either UTC midnight or Eastern midnight (04:00 or
    05:00 UTC). Both share the UTC calendar day. Converting Eastern midnight
    to the previous local evening would shift the deed date.
    """
    number = seed.num(value)
    if number is None:
        return None
    if number > 1_000_000_000_000:
        number = number / 1000.0
    if number < 0 or number > 4_000_000_000:
        return None
    when = dt.datetime.fromtimestamp(number, dt.timezone.utc)
    if when.year < 1900 or when.year > 2100:
        return None
    return when.strftime("%Y-%m-%d")


def money(value: Any) -> float | None:
    number = seed.num(value)
    if number is None or number <= 0:
        return None
    return round(number, 2)


def money_sum(left: Any, right: Any) -> float | None:
    left_n = seed.num(left)
    right_n = seed.num(right)
    if left_n is None and right_n is None:
        return None
    total = (left_n or 0) + (right_n or 0)
    if total <= 0:
        return None
    return round(total, 2)


def join_situs(number: Any, street: Any) -> str | None:
    house = seed.clean(number)
    name = seed.clean(street)
    if house in {None, "0"}:
        return name
    if house and name:
        return f"{house} {name}"
    return house or name


def different_name(primary: str | None, secondary: str | None) -> str | None:
    if not secondary:
        return None
    if primary and secondary.strip().upper() == primary.strip().upper():
        return None
    return secondary


def title_place(value: str) -> str:
    small = {"of", "and"}
    parts = []
    for index, part in enumerate(value.split()):
        lower = part.lower()
        if index and lower in small:
            parts.append(lower)
        else:
            parts.append(lower.capitalize())
    return " ".join(parts)


def point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    count = len(ring)
    if count < 3:
        return False
    j = count - 1
    for i in range(count):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            denom = yj - yi
            if denom != 0 and x < (xj - xi) * (y - yi) / denom + xi:
                inside = not inside
        j = i
    return inside


def point_in_rings(x: float, y: float, rings: list[list[tuple[float, float]]]) -> bool:
    inside = False
    for ring in rings:
        if point_in_ring(x, y, ring):
            inside = not inside
    return inside


def esri_rings(geometry: dict | None) -> list[list[tuple[float, float]]]:
    if not geometry:
        return []
    rings = []
    for ring in geometry.get("rings") or []:
        coords = [(float(x), float(y)) for x, y in ring]
        if len(coords) >= 3:
            rings.append(coords)
    return rings


def ring_bbox(rings: list[list[tuple[float, float]]]) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for ring in rings:
        for x, y in ring:
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def bbox_area(bbox: tuple[float, float, float, float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


class ZoneIndex:
    """Grid of zoning polygons. Large county shells stay on a short side list."""

    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.items: list[dict] = []
        self.broad: list[int] = []

    def add(self, geometry: dict | None, payload: dict) -> None:
        rings = esri_rings(geometry)
        bbox = ring_bbox(rings)
        if not bbox or not rings:
            return
        item = {**payload, "rings": rings, "bbox": bbox, "area": bbox_area(bbox)}
        index = len(self.items)
        self.items.append(item)
        minx, miny, maxx, maxy = bbox
        if (maxx - minx) > 0.35 or (maxy - miny) > 0.35:
            self.broad.append(index)
            return
        ix0 = math.floor(minx / self.cell)
        iy0 = math.floor(miny / self.cell)
        ix1 = math.floor(maxx / self.cell)
        iy1 = math.floor(maxy / self.cell)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.cells[(ix, iy)].append(index)

    def hits(self, x: float, y: float) -> list[dict]:
        ix = math.floor(x / self.cell)
        iy = math.floor(y / self.cell)
        seen: set[int] = set()
        found: list[dict] = []
        for index in self.cells.get((ix, iy), []) + self.broad:
            if index in seen:
                continue
            seen.add(index)
            item = self.items[index]
            minx, miny, maxx, maxy = item["bbox"]
            if x < minx or x > maxx or y < miny or y > maxy:
                continue
            if point_in_rings(x, y, item["rings"]):
                found.append(item)
        return found


def interior_points(geometry: dict) -> list[tuple[float, float]]:
    center = seed.centroid_of(geometry)
    points: list[tuple[float, float]] = []
    if center:
        points.append(center)
    ring: list[list[float]] | None = None
    if geometry.get("type") == "Polygon":
        ring = geometry["coordinates"][0]
    elif geometry.get("type") == "MultiPolygon" and geometry["coordinates"]:
        ring = geometry["coordinates"][0][0]
    if not center or not ring or len(ring) < 4:
        return points
    body = ring[:-1]
    step = max(1, len(body) // 6)
    for index in range(0, len(body), step):
        vx, vy = body[index]
        points.append((center[0] * 0.65 + vx * 0.35, center[1] * 0.65 + vy * 0.35))
    return points


def choose_hit(hits: list[dict]) -> dict | None:
    if not hits:
        return None
    best = hits[0]
    for hit in hits[1:]:
        if hit["priority"] > best["priority"]:
            best = hit
        elif hit["priority"] == best["priority"] and hit["area"] < best["area"]:
            best = hit
    return best


def apply_hit(feature: dict, hit: dict | None) -> None:
    if not hit or not hit.get("code"):
        return
    props = feature["properties"]
    code = str(hit["code"]).strip()
    if not code:
        return
    props["zoningCode"] = code
    # Keep the full code. "R-15" must not be split into a jurisdiction prefix.
    props["zoningDistrict"] = code
    props["zoningSource"] = hit.get("source")
    if hit.get("municipality"):
        props["municipality"] = hit["municipality"]
    if hit.get("jcode"):
        props["jurisdictionCode"] = str(hit["jcode"])


def load_layer(
    url: str,
    where: str,
    fields: list[str],
    *,
    geometry: bool,
    batch: int = 100,
) -> list[dict]:
    ids = seed.fetch_object_ids(url, where)
    if not ids:
        return []
    return seed.fetch_by_ids(url, ids, fields, batch=batch, return_geometry=geometry)


def load_layer_soft(label: str, url: str, where: str, fields: list[str], *, geometry: bool, notes: list[str]) -> list[dict]:
    try:
        rows = load_layer(url, where, fields, geometry=geometry)
        print(f"  {label}: {len(rows)}", flush=True)
        return rows
    except Exception as exc:  # noqa: BLE001
        message = f"{label} failed ({exc}). Zoning from that layer was not joined."
        print(f"  {message}", flush=True)
        notes.append(message)
        return []


def index_zones(rows: list[dict], builder: Callable[[dict], dict | None]) -> ZoneIndex:
    index = ZoneIndex()
    for row in rows:
        payload = builder(row.get("attributes") or {})
        if not payload:
            continue
        index.add(row.get("geometry"), payload)
    return index


def zoning_for_feature(feature: dict, *indexes: ZoneIndex) -> dict | None:
    hits: list[dict] = []
    for point in interior_points(feature["geometry"]):
        for index in indexes:
            hits.extend(index.hits(point[0], point[1]))
    return choose_hit(hits)


def greenville_feature(item: dict, county: dict, markets: list[str], source: str) -> dict | None:
    attrs = item.get("attributes") or {}
    geometry, _computed = seed.rings_to_feature_geometry(item.get("geometry"))
    if not geometry:
        return None
    center = seed.centroid_of(geometry)
    if not seed.plausible_centroid(center):
        return None
    acres = seed.num(attrs.get("TACRES"))
    if not seed.in_band(acres):
        return None
    parcel_id = seed.clean(attrs.get("PIN"))
    if not parcel_id:
        return None
    owner = seed.clean(attrs.get("OWNAM1"))
    fair = money(attrs.get("FAIRMKTVAL"))
    taxable_market = money(attrs.get("TAXMKTVAL"))
    market_value = fair if fair is not None else taxable_market
    taxable = taxable_market if fair is not None else None
    return seed.empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=markets,
        parcel_id=parcel_id,
        acreage=acres,  # type: ignore[arg-type]
        geometry=geometry,
        center=center,  # type: ignore[arg-type]
        source=source,
        owner=owner,
        owner2=different_name(owner, seed.clean(attrs.get("OWNAM2"))),
        situs=join_situs(attrs.get("STRNUM"), attrs.get("LOCATE")),
        dor=seed.clean(attrs.get("LANDUSE")),
        sale_price=money(attrs.get("SLPRICE")),
        sale_date=epoch_date(attrs.get("DEEDDATE")),
        market_value=market_value,
        taxable=taxable,
        taxes=money(attrs.get("TOTTAX")),
        mail1=seed.clean(attrs.get("STREET")),
        mail2=seed.clean(attrs.get("NAMECO")),
        mail_city=seed.clean(attrs.get("CITY")),
        mail_state=seed.clean(attrs.get("STATE")),
        mail_zip=seed.zip_str(attrs.get("ZIP5")),
        jurisdiction=seed.clean(attrs.get("JURIS")),
        appraiser_url=GREENVILLE_APPRAISER,
    )


def spartanburg_feature(item: dict, county: dict, markets: list[str], source: str) -> dict | None:
    attrs = item.get("attributes") or {}
    geometry, _computed = seed.rings_to_feature_geometry(item.get("geometry"))
    if not geometry:
        return None
    center = seed.centroid_of(geometry)
    if not seed.plausible_centroid(center):
        return None
    acres = seed.num(attrs.get("Acreage"))
    if not seed.in_band(acres):
        return None
    parcel_id = seed.clean(attrs.get("MAPNUMBER")) or seed.clean(attrs.get("GISParcelNumber"))
    if not parcel_id:
        return None
    owner = seed.clean(attrs.get("OwnerName"))
    situs = join_situs(attrs.get("StreetNumber"), attrs.get("StreetName")) or seed.clean(attrs.get("PropertyLocation"))
    return seed.empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=markets,
        parcel_id=parcel_id,
        acreage=acres,  # type: ignore[arg-type]
        geometry=geometry,
        center=center,  # type: ignore[arg-type]
        source=source,
        owner=owner,
        owner2=different_name(owner, seed.clean(attrs.get("TaxpayerName"))),
        situs=situs,
        city=seed.clean(attrs.get("StreetCommunity")),
        zip_code=seed.zip_str(attrs.get("StreetZip")),
        dor=seed.clean(attrs.get("LandUse")),
        sale_price=money(attrs.get("SaleAmount")),
        sale_date=epoch_date(attrs.get("SaleDate")),
        market_value=money_sum(attrs.get("CurrentAppraisedLandValue"), attrs.get("CurrentAppraisedBuildingValue")),
        assessed=money_sum(attrs.get("CurrentAssessedLandValue"), attrs.get("CurrentAssessedBuildingValue")),
        taxable=money_sum(attrs.get("CurrentTaxableLandValue"), attrs.get("CurrentTaxableBuildingValue")),
        mail1=seed.clean(attrs.get("StreetAddress")),
        mail_city=seed.clean(attrs.get("City")),
        mail_state=seed.clean(attrs.get("State")),
        mail_zip=seed.zip_str(attrs.get("Zip")),
        jurisdiction=seed.clean(attrs.get("TownCode")),
        appraiser_url=SPARTANBURG_APPRAISER,
    )


def collapse_features(built: list[dict]) -> tuple[list[dict], int]:
    by_id: dict[str, dict] = {}
    dropped = 0
    for feature in built:
        if feature is None:
            dropped += 1
            continue
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
        else:
            dropped += 1
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def greenville_county_payload(attrs: dict) -> dict | None:
    code = seed.clean(attrs.get("ZONING"))
    jcode = seed.clean(attrs.get("JCODE"))
    if not code:
        return None
    return {
        "code": code,
        "priority": PRIORITY_COUNTY,
        "source": "gcgia-zoning-13",
        "jcode": jcode,
        "municipality": GREENVILLE_JCODE.get(jcode or "", None),
    }


def code_payload(attrs: dict, field: str, *, priority: int, source: str, municipality: str, jcode: str | None = None) -> dict | None:
    code = seed.clean(attrs.get(field))
    if not code:
        return None
    payload = {"code": code, "priority": priority, "source": source, "municipality": municipality}
    if jcode:
        payload["jcode"] = jcode
    return payload


def enrich_greenville(features: list[dict], notes: list[str]) -> dict[str, int]:
    county_rows = load_layer_soft(
        "GCGIA zoning/13",
        GREENVILLE_ZONING,
        "1=1",
        ["ZONING", "JCODE"],
        geometry=True,
        notes=notes,
    )
    city_rows = load_layer_soft(
        "City of Greenville regulation/7",
        GREENVILLE_CITY_ZONING,
        "1=1",
        ["ZONING"],
        geometry=True,
        notes=notes,
    )
    greer_rows = load_layer_soft(
        "Greer UDO",
        GREER_ZONING,
        "1=1",
        ["Pro_Zoning"],
        geometry=True,
        notes=notes,
    )
    county_index = index_zones(county_rows, greenville_county_payload)
    city_index = index_zones(
        city_rows,
        lambda attrs: code_payload(
            attrs,
            "ZONING",
            priority=PRIORITY_CITY,
            source="greenville-city-regulation-7",
            municipality="City of Greenville",
            jcode="30850",
        ),
    )
    greer_index = index_zones(
        greer_rows,
        lambda attrs: code_payload(
            attrs,
            "Pro_Zoning",
            priority=PRIORITY_CITY,
            source="greer-udo",
            municipality="City of Greer",
            jcode="30985",
        ),
    )
    counts: dict[str, int] = defaultdict(int)
    for feature in features:
        hit = zoning_for_feature(feature, city_index, greer_index, county_index)
        apply_hit(feature, hit)
        counts[hit["source"] if hit else "none"] += 1
    return dict(counts)


def attribute_map(rows: list[dict], id_field: str, code_field: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for row in rows:
        attrs = row.get("attributes") or {}
        parcel_id = seed.clean(attrs.get(id_field))
        code = seed.clean(attrs.get(code_field))
        if parcel_id and code:
            found[parcel_id.upper()] = code
    return found


def spartanburg_place(name: str) -> str | None:
    label = name.strip().upper()
    if not label or label.endswith(" COUNTY"):
        return None
    if label == "UNINCORPORATED":
        return "Unincorporated Spartanburg County"
    if label == "GREER":
        return "City of Greer"
    return title_place(label)


def enrich_spartanburg(features: list[dict], notes: list[str]) -> dict[str, int]:
    muni_rows = load_layer_soft(
        "Spartanburg municipalities",
        SPARTANBURG_MUNICIPALITIES,
        "1=1",
        ["MUNICIPALITY"],
        geometry=True,
        notes=notes,
    )
    city_rows = load_layer_soft(
        "Spartanburg Zoning_Layer_2026",
        SPARTANBURG_CITY_ZONING,
        "1=1",
        ["CityofSp_2", "Zoning_J_1"],
        geometry=True,
        notes=notes,
    )
    info_rows = load_layer_soft(
        "Spartanburg Parcel_Info zoning",
        SPARTANBURG_CITY_PARCELS,
        "1=1",
        ["MAPNUMBER", "ZoningDist"],
        geometry=False,
        notes=notes,
    )
    inman_rows = load_layer_soft(
        "Inman zoning",
        INMAN_ZONING,
        "1=1",
        ["MAPNUMBER", "Zoning"],
        geometry=False,
        notes=notes,
    )
    wellford_rows = load_layer_soft(
        "Wellford zoning",
        WELLFORD_ZONING,
        "1=1",
        ["MAPNUMBER", "Zoning_Cla"],
        geometry=False,
        notes=notes,
    )
    greer_rows = load_layer_soft(
        "Greer UDO",
        GREER_ZONING,
        "1=1",
        ["Pro_Zoning"],
        geometry=True,
        notes=notes,
    )
    lyman_index = ZoneIndex()
    for layer_id, code in LYMAN_LAYERS.items():
        rows = load_layer_soft(
            f"Lyman {code}",
            f"{LYMAN_ZONING}/{layer_id}/query",
            "1=1",
            ["OBJECTID"],
            geometry=True,
            notes=notes,
        )
        for row in rows:
            lyman_index.add(
                row.get("geometry"),
                {
                    "code": code,
                    "priority": PRIORITY_LYMAN,
                    "source": "lyman-tol-layer",
                    "municipality": "Lyman",
                },
            )

    def muni_payload(attrs: dict) -> dict | None:
        raw = seed.clean(attrs.get("MUNICIPALITY"))
        if not raw:
            return None
        place = spartanburg_place(raw)
        if not place or place.startswith("Unincorporated"):
            # The unincorporated shell is a 100k-vertex county polygon. Parcels
            # already come from county CAMA, so a miss on the incorporated
            # places is the unincorporated remainder.
            return None
        return {"code": "", "priority": 5, "source": "spartanburg-municipalities", "municipality": place, "placeOnly": True}

    muni_index = index_zones(muni_rows, muni_payload)

    def city_code(attrs: dict) -> dict | None:
        code = seed.clean(attrs.get("Zoning_J_1")) or seed.clean(attrs.get("CityofSp_2"))
        if not code:
            return None
        return {
            "code": code,
            "priority": PRIORITY_CITY,
            "source": "spartanburg-zoning-2026",
            "municipality": "Spartanburg",
        }

    city_index = index_zones(city_rows, city_code)
    greer_index = index_zones(
        greer_rows,
        lambda attrs: code_payload(
            attrs,
            "Pro_Zoning",
            priority=PRIORITY_CITY,
            source="greer-udo",
            municipality="City of Greer",
        ),
    )
    inman = attribute_map(inman_rows, "MAPNUMBER", "Zoning")
    wellford = attribute_map(wellford_rows, "MAPNUMBER", "Zoning_Cla")
    city_attr = attribute_map(info_rows, "MAPNUMBER", "ZoningDist")

    counts: dict[str, int] = defaultdict(int)
    for feature in features:
        props = feature["properties"]
        place_hit = zoning_for_feature(feature, muni_index)
        props["municipality"] = place_hit["municipality"] if place_hit and place_hit.get("municipality") else "Unincorporated Spartanburg County"
        key = str(props["parcelId"]).upper()
        attr_hit = None
        if key in inman:
            attr_hit = {"code": inman[key], "priority": PRIORITY_CITY, "source": "inman-zoning", "municipality": "Inman", "area": 0}
        elif key in wellford:
            attr_hit = {
                "code": wellford[key],
                "priority": PRIORITY_CITY,
                "source": "wellford-zoning",
                "municipality": "Wellford",
                "area": 0,
            }
        elif key in city_attr:
            attr_hit = {
                "code": city_attr[key],
                "priority": PRIORITY_CITY_ATTRIBUTE,
                "source": "spartanburg-parcel-info",
                "municipality": "Spartanburg",
                "area": 0,
            }
        spatial = zoning_for_feature(feature, city_index, greer_index, lyman_index)
        chosen = choose_hit([hit for hit in (attr_hit, spatial) if hit])
        apply_hit(feature, chosen)
        counts[chosen["source"] if chosen else "none"] += 1
    if ENERGOV_ZONING:
        notes.append(
            "Spartanburg County EnerGov zoning (Display_Map/12) is three coarse districts and was not copied onto parcels."
        )
    return dict(counts)


def pull(county: dict, markets: list[str], spec: dict) -> dict:
    fips = county["fips"]
    which = spec["gsp"]
    cache_path = seed.CACHE_DIR / f"{fips}-{CACHE_VERSION}.json"
    print(f"Pulling {county['name']} {county['state']} ({fips}) via {spec['source']}", flush=True)
    if cache_path.exists() and not spec.get("ignoreCache"):
        import json

        cached = json.loads(cache_path.read_text())
        if cached.get("version") == CACHE_VERSION and cached.get("features"):
            print(f"  cache hit {len(cached['features'])}", flush=True)
            features = cached["features"]
            for feature in features:
                feature["properties"]["marketIds"] = markets
            path, lookup, tiles = seed.write_tiles(county, features)
            return seed.county_row(
                county,
                markets,
                feature_count=len(features),
                coverage=spec["coverage"] if features else "gap",
                partition="tiles" if features else "none",
                path=path if features else None,
                lookup=lookup if features else None,
                source=spec["source"],
                query_url=spec["url"],
                gaps=list(cached.get("gaps") or spec.get("gaps") or []),
                source_count=cached.get("sourceCount"),
                dropped=cached.get("dropped"),
                tile_count=tiles,
            )

    try:
        expected = seed.count_where(spec["url"], spec["where"])
    except Exception as exc:  # noqa: BLE001
        reason = f"Query failed: {exc}"
        print(f"  gap {reason}", flush=True)
        return seed.county_row(
            county,
            markets,
            feature_count=0,
            coverage="gap",
            partition="none",
            path=None,
            lookup=None,
            source=spec["source"],
            query_url=spec["url"],
            gaps=[reason, *(spec.get("gaps") or [])],
        )
    print(f"  source rows {expected}", flush=True)
    if which == "greenville":
        fields = [
            "PIN",
            "OWNAM1",
            "OWNAM2",
            "NAMECO",
            "STREET",
            "CITY",
            "STATE",
            "ZIP5",
            "STRNUM",
            "LOCATE",
            "TACRES",
            "LANDUSE",
            "SLPRICE",
            "DEEDDATE",
            "TAXMKTVAL",
            "FAIRMKTVAL",
            "TOTTAX",
            "JURIS",
        ]
        raw = load_layer(spec["url"], spec["where"], fields, geometry=True)
        built = [greenville_feature(item, county, markets, spec["source"]) for item in raw]
    elif which == "spartanburg":
        fields = [
            "MAPNUMBER",
            "GISParcelNumber",
            "OwnerName",
            "TaxpayerName",
            "StreetAddress",
            "City",
            "State",
            "Zip",
            "PropertyLocation",
            "StreetNumber",
            "StreetName",
            "StreetCommunity",
            "StreetZip",
            "Acreage",
            "LandUse",
            "SaleDate",
            "SaleAmount",
            "CurrentAppraisedLandValue",
            "CurrentAppraisedBuildingValue",
            "CurrentAssessedLandValue",
            "CurrentAssessedBuildingValue",
            "CurrentTaxableLandValue",
            "CurrentTaxableBuildingValue",
            "TownCode",
        ]
        raw = load_layer(spec["url"], spec["where"], fields, geometry=True)
        built = [spartanburg_feature(item, county, markets, spec["source"]) for item in raw]
    else:
        raise RuntimeError(f"Unknown GSP county {which}")

    kept = [item for item in built if item is not None]
    features, duplicate_dropped = collapse_features(kept)
    dropped = (len(raw) - len(kept)) + duplicate_dropped
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{fips} emitted a parcel outside 5–150 acres")

    notes: list[str] = []
    print(f"  joining zoning for {len(features)} parcels", flush=True)
    if which == "greenville":
        counts = enrich_greenville(features, notes)
    else:
        counts = enrich_spartanburg(features, notes)
    joined = len(features) - counts.get("none", 0)
    summary = "Zoning joined for {joined} of {total} parcels ({detail}).".format(
        joined=joined,
        total=len(features),
        detail=", ".join(f"{name} {count}" for name, count in sorted(counts.items())),
    )
    print(f"  {summary}", flush=True)
    gaps = [summary, *notes, *(spec.get("gaps") or [])]
    import json

    seed.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {"version": CACHE_VERSION, "sourceCount": expected, "dropped": dropped, "gaps": gaps, "features": features},
            separators=(",", ":"),
        )
    )
    path, lookup, tiles = (None, None, 0)
    if features:
        path, lookup, tiles = seed.write_tiles(county, features)
    print(f"  kept {len(features)} ({spec['coverage']})", flush=True)
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
        gaps=gaps,
        source_count=expected,
        dropped=dropped,
        tile_count=tiles,
    )


def self_check() -> None:
    square = [[(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0), (0.0, 0.0)]]
    hole = square + [[(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)]]
    assert point_in_rings(1, 1, square)
    assert not point_in_rings(3, 1, square)
    assert not point_in_rings(1, 1, hole)
    assert point_in_rings(0.2, 0.2, hole)
    assert epoch_date(1649131200000) == "2022-04-05"
    assert epoch_date(1355356800000) == "2012-12-13"
    assert money(0) is None
    assert money(10) == 10
    assert money_sum(69649, 0) == 69649
    assert join_situs("0", "ADGER ST") == "ADGER ST"
    assert join_situs("903", "MAIN") == "903 MAIN"
    feature = greenville_feature(
        {
            "attributes": {
                "PIN": "0006000401600",
                "OWNAM1": "EDGE ON NORTH MAIN PROPERTY OW",
                "OWNAM2": "",
                "NAMECO": "",
                "STREET": "8 EDGE CT UNIT B",
                "CITY": "GREENVILLE",
                "STATE": "SC",
                "ZIP5": "29609",
                "STRNUM": "903",
                "LOCATE": "MAIN",
                "TACRES": 5.85,
                "LANDUSE": "1181",
                "SLPRICE": 10,
                "DEEDDATE": 1649131200000,
                "TAXMKTVAL": 2920,
                "FAIRMKTVAL": 2920,
                "TOTTAX": 1472.22,
                "JURIS": "C",
            },
            "geometry": {"rings": [[[-82.4, 34.8], [-82.39, 34.8], [-82.39, 34.81], [-82.4, 34.81], [-82.4, 34.8]]]},
        },
        {"fips": "45045", "name": "Greenville", "state": "South Carolina"},
        ["Greenville"],
        "sc-greenville-gcgia-tax-parcel",
    )
    assert feature is not None
    props = feature["properties"]
    assert props["situsAddress"] == "903 MAIN"
    assert props["mailingAddress"]["line1"] == "8 EDGE CT UNIT B"
    assert props["mailingAddress"]["city"] == "GREENVILLE"
    assert props["lastSale"]["date"] == "2022-04-05"
    assert props["lastSale"]["price"] == 10
    assert props["tax"]["taxes"] == 1472.22
    assert props["ownerName"]
    fair = greenville_feature(
        {
            "attributes": {
                "PIN": "0015000100901",
                "OWNAM1": "BISHOP OF CHARLESTON",
                "STRNUM": "101",
                "LOCATE": "HAMPTON",
                "TACRES": 9.57,
                "SLPRICE": 0,
                "TAXMKTVAL": 6108960,
                "FAIRMKTVAL": 25099580,
                "TOTTAX": 7197.52,
                "STREET": "901 ORANGE GROVE RD",
                "CITY": "CHARLESTON",
                "STATE": "SC",
                "ZIP5": "29407",
            },
            "geometry": {"rings": [[[-82.4, 34.8], [-82.39, 34.8], [-82.39, 34.81], [-82.4, 34.81], [-82.4, 34.8]]]},
        },
        {"fips": "45045", "name": "Greenville", "state": "South Carolina"},
        ["Greenville"],
        "sc-greenville-gcgia-tax-parcel",
    )
    assert fair is not None
    assert fair["properties"]["tax"]["marketValue"] == 25099580
    assert fair["properties"]["tax"]["taxableValue"] == 6108960
    assert fair["properties"]["lastSale"]["price"] is None
    chosen = choose_hit(
        [
            {"code": "R-7.5", "priority": PRIORITY_COUNTY, "source": "gcgia-zoning-13", "area": 10, "municipality": "Unincorporated Greenville County"},
            {"code": "RNX-B", "priority": PRIORITY_CITY, "source": "greenville-city-regulation-7", "area": 2, "municipality": "City of Greenville"},
        ]
    )
    assert chosen is not None and chosen["code"] == "RNX-B"
    assert spartanburg_place("GREENVILLE COUNTY") is None
    assert spartanburg_place("UNINCORPORATED") == "Unincorporated Spartanburg County"
    assert spartanburg_place("CENTRAL PACOLET") == "Central Pacolet"
    assert spartanburg_place("GREER") == "City of Greer"
    assert "Campobello_Zoning" not in GREER_ZONING
    assert "Base_Data" not in GREENVILLE_PARCELS
    print("gsp self-check ok")


if __name__ == "__main__":
    import sys

    if "--self-check" in sys.argv:
        self_check()
    else:
        raise SystemExit("Run scripts/seed_market_parcels.py --market Greenville --county Greenville --county Spartanburg --refresh")
