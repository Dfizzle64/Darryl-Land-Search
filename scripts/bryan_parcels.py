"""Bryan County, Georgia parcels from the county PropertyDetails service.

TOTALACRES is the 5–150 acre filter. Geometry is requested in WGS84 and checked
against the Bryan County, Georgia box so Bryan County, Texas and Bryan County,
Oklahoma cannot land here. Unincorporated zoning is the county Zoning layer.
Inside Pembroke and Richmond Hill the parcel ZONINGCODE is used, and CITY stubs
and slash splits are not stored. Future land use is the 2023 comprehensive plan
outside those cities. City future land use is not invented. Sales stay null.
No Opportunity Zone designation is assigned.
"""

from __future__ import annotations

import urllib.parse
from collections import defaultdict

from parcel_geometry import esri_rings_to_geojson, point_in_geometry, polygon_parts

PARCEL_URL = "https://bryangis.bryan-county.org/arcgis/rest/services/PropertyDetails/MapServer/0/query"
ZONING_URL = "https://bryangis.bryan-county.org/arcgis/rest/services/Zoning/MapServer/0/query"
FLU_URL = "https://bryangis.bryan-county.org/arcgis/rest/services/2023ComprehensivePlan/MapServer/4/query"
CITY_URL = "https://bryangis.bryan-county.org/arcgis/rest/services/MunicipalBoundaries/MapServer/0/query"
# Bryan County, Georgia, southwest of Savannah. Excludes Bryan County, Texas and Bryan County, Oklahoma.
BRYAN_BOX = (-81.85, 31.70, -81.05, 32.30)
SOURCE = "ga-bryan-property-details"
APPRAISER = (
    "https://qpublic.schneidercorp.com/Application.aspx?AppID=639&LayerID=11303"
    "&PageTypeID=4&KeyValue={parcelId}"
)
CITY_DISPLAY = {"PEMBROKE": "Pembroke", "RICHMOND HILL": "Richmond Hill"}
STUBS = {"<NULL>", "NULL", "NONE", "N/A", "NA", "CITY", "PEMBROKE", "RICHMOND HILL", "BRYAN"}


def bryan_spec() -> dict:
    return {
        "kind": "bryan",
        "source": SOURCE,
        "url": PARCEL_URL,
        "coverage": "complete-gte-5ac",
        "gaps": static_gaps(),
    }


def static_gaps() -> list[str]:
    return [
        "Bryan County parcels are PropertyDetails/MapServer/0. Acreage is TOTALACRES, inclusive 5–150. Features were requested in WGS84 and kept only inside the Bryan County, Georgia box.",
        "Mailing city is not a municipality. Pembroke and Richmond Hill come from MunicipalBoundaries. TAXDISTRIC is not the city filter.",
        "Unincorporated zoning is Zoning/MapServer/0 ZONECLASS. Inside Pembroke and Richmond Hill the parcel ZONINGCODE is used. There is no city zoning FeatureServer. CITY is a stub. A slash that is not a published district is a split and is not stored. A city zoning map PDF can differ from ZONINGCODE.",
        "Future land use is 2023ComprehensivePlan/MapServer/4 LANDUSEDESC for unincorporated parcels. Pembroke and Richmond Hill have no city future-land-use service, so city future land use was not invented. Legacy comprehensive-plan city-limit stubs were not used.",
        "Sales stay null. Beacon AppID=639 was not scraped. HISTYR and HISTVAL are assessment history, not sales. MAVCURR is unused on this layer, so assessed value and taxable value stay null. CURR_VAL is the market value.",
        "Bryan County, Texas, Bryan County, Oklahoma, Chatham County SAGIS, and ARC LandPro were not used.",
        "This extract does not assign Opportunity Zone designations.",
    ]


def _seed():
    import seed_market_parcels as seed

    return seed


def _fetch(url: str, params: dict) -> dict:
    return _seed().fetch_json(url, params, timeout=180)


def _by_ids(url: str, ids: list[int], fields: list[str]) -> list[dict]:
    features: list[dict] = []
    page = 80
    for start in range(0, len(ids), page):
        chunk = ids[start : start + page]
        data = _fetch(
            url,
            {
                "objectIds": ",".join(str(item) for item in chunk),
                "outFields": ",".join(fields),
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "json",
            },
        )
        if data.get("error"):
            raise RuntimeError(str(data["error"])[:300])
        features.extend(data.get("features") or [])
        print(f"    parcels {len(features)}", flush=True)
    return features


def _layer(url: str, fields: list[str]) -> list[dict]:
    data = _fetch(
        url,
        {
            "where": "1=1",
            "outFields": ",".join(fields),
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        },
    )
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:300])
    return data.get("features") or []


def _money(value) -> float | None:
    number = _seed().num(value)
    if number is None or number <= 0:
        return None
    return round(number, 2)


def _collapse(value: str | None) -> str | None:
    text = _seed().clean(value)
    if not text:
        return None
    return " ".join(text.split())


def _situs(attrs: dict) -> str | None:
    number = _seed().num(attrs.get("HOUSE_NO"))
    if number is None or number <= 0:
        return None
    parts = [str(int(number)) if number == int(number) else str(number)]
    for field in ("STDIRECT", "STREET_NAM", "STTYPE", "UNIT"):
        piece = _seed().clean(attrs.get(field))
        if piece:
            parts.append(piece)
    return " ".join(parts)


def _prepare(raw: list[dict], name_field: str, code_field: str, names: dict[str, str] | None = None) -> list[dict]:
    prepared: list[dict] = []
    for item in raw:
        attrs = item.get("attributes") or {}
        raw_name = _seed().clean(attrs.get(name_field))
        if not raw_name:
            continue
        key = raw_name.upper()
        if names is not None and key not in names:
            continue
        label = names[key] if names is not None else raw_name
        code = _seed().clean(attrs.get(code_field)) if code_field != name_field else label
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        if not geometry or not code:
            continue
        xs: list[float] = []
        ys: list[float] = []
        for poly in polygon_parts(geometry):
            for ring in poly:
                for x, y in ring:
                    xs.append(x)
                    ys.append(y)
        if not xs:
            continue
        area = 0.0
        for poly in polygon_parts(geometry):
            outer = poly[0]
            for i in range(len(outer) - 1):
                area += outer[i][0] * outer[i + 1][1] - outer[i + 1][0] * outer[i][1]
        prepared.append(
            {
                "bbox": (min(xs), min(ys), max(xs), max(ys)),
                "area": abs(area / 2.0) or 1e-12,
                "name": label,
                "code": code,
                "geometry": geometry,
            }
        )
    return prepared


def _grid(prepared: list[dict], cell: float = 0.02) -> dict[tuple[int, int], list[dict]]:
    import math

    grid: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for poly in prepared:
        west, south, east, north = poly["bbox"]
        for ix in range(math.floor(west / cell), math.floor(east / cell) + 1):
            for iy in range(math.floor(south / cell), math.floor(north / cell) + 1):
                grid[(ix, iy)].append(poly)
    return grid


def _hit(grid: dict, lon: float, lat: float, cell: float = 0.02) -> dict | None:
    import math

    hits = []
    for poly in grid.get((math.floor(lon / cell), math.floor(lat / cell)), []):
        west, south, east, north = poly["bbox"]
        if lon < west or lon > east or lat < south or lat > north:
            continue
        if point_in_geometry(lon, lat, poly["geometry"]):
            hits.append(poly)
    if not hits:
        return None
    return min(hits, key=lambda poly: poly["area"])


def _merge(left: dict, right: dict) -> dict:
    parts = polygon_parts(left) + polygon_parts(right)
    if len(parts) == 1:
        return {"type": "Polygon", "coordinates": parts[0]}
    return {"type": "MultiPolygon", "coordinates": parts}


def _parcel_code(value: str | None, districts: set[str]) -> tuple[str | None, str | None]:
    text = _collapse(value)
    if not text:
        return None, None
    if text.upper() in STUBS:
        return None, "stub"
    if text.upper() in districts or text in districts:
        return text, None
    if "/" in text:
        return None, "split"
    return text, None


def download_bryan_county(county: dict, markets: list[str], spec: dict) -> dict:
    seed = _seed()
    clean = seed.clean
    num = seed.num
    print("Pulling Bryan County GA parcels", flush=True)
    where = "TOTALACRES>=5 AND TOTALACRES<=150"
    expected = seed.count_where(PARCEL_URL, where)
    ids = seed.fetch_object_ids(PARCEL_URL, where)
    if len(ids) != expected:
        raise RuntimeError(f"Bryan id list {len(ids)} did not match count {expected}")
    raw = _by_ids(
        PARCEL_URL,
        ids,
        [
            "FID",
            "PARCEL_NO",
            "LASTNAME",
            "ADDRESS1",
            "ADDRESS2",
            "ADDRESS3",
            "CITY",
            "STATE",
            "ZIP",
            "ZIP_1",
            "HOUSE_NO",
            "STDIRECT",
            "STREET_NAM",
            "STTYPE",
            "UNIT",
            "TOTALACRES",
            "CURR_VAL",
            "ZONINGCODE",
            "DIGCLASS",
        ],
    )
    if len(raw) != expected:
        raise RuntimeError(f"Bryan paged fetch returned {len(raw)}, expected {expected}")

    print("  zoning, future land use, cities", flush=True)
    zoning = _prepare(_layer(ZONING_URL, ["OBJECTID", "ZONECLASS", "ZONEDESC"]), "ZONECLASS", "ZONECLASS")
    districts = {item["code"].upper() for item in zoning}
    if "A-5" not in districts or "P/I" not in districts:
        raise RuntimeError(f"Bryan zoning districts missing A-5 or P/I: {sorted(districts)}")
    flu_polys = _prepare(_layer(FLU_URL, ["OBJECTID", "LANDUSEDESC"]), "LANDUSEDESC", "LANDUSEDESC")
    if len(flu_polys) < 11:
        raise RuntimeError(f"Expected 11 Bryan future-land-use polygons, got {len(flu_polys)}")
    cities = _prepare(_layer(CITY_URL, ["OBJECTID", "NAME"]), "NAME", "NAME", CITY_DISPLAY)
    if len(cities) != 2:
        raise RuntimeError(f"Expected Pembroke and Richmond Hill, got {[item['name'] for item in cities]}")
    zoning_grid = _grid(zoning)
    flu_grid = _grid(flu_polys)
    city_grid = _grid(cities)

    by_id: dict[str, dict] = {}
    dropped = 0
    outside = 0
    merged = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed = seed.rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            dropped += 1
            continue
        center = seed.centroid_of(geometry)
        if not seed.plausible_centroid(center):
            dropped += 1
            continue
        lon, lat = center
        west, south, east, north = BRYAN_BOX
        if not (west <= lon <= east and south <= lat <= north):
            outside += 1
            dropped += 1
            continue
        acres = num(attrs.get("TOTALACRES"))
        if not seed.in_band(acres):
            dropped += 1
            continue
        parcel_id = clean(attrs.get("PARCEL_NO"))
        if not parcel_id:
            dropped += 1
            continue
        line1 = _collapse(attrs.get("ADDRESS2"))
        extra = _collapse(attrs.get("ADDRESS1"))
        line2 = _collapse(attrs.get("ADDRESS3"))
        if extra:
            line1, line2 = extra, line1 or line2
        pending = {
            "attrs": attrs,
            "geometry": geometry,
            "acres": acres,
            "line1": line1,
            "line2": line2,
        }
        previous = by_id.get(parcel_id)
        if previous is not None:
            merged += 1
            dropped += 1
            pending["geometry"] = _merge(previous["geometry"], geometry)
            if (acres or 0) <= (previous["acres"] or 0):
                previous["geometry"] = pending["geometry"]
                continue
        by_id[parcel_id] = pending

    features = []
    city_counts: dict[str, int] = defaultdict(int)
    zoning_counts: dict[str, int] = defaultdict(int)
    unzoned = 0
    stubs = 0
    splits = 0
    flu_count = 0
    valued = 0
    for parcel_id, pending in by_id.items():
        attrs = pending["attrs"]
        geometry = pending["geometry"]
        center = seed.centroid_of(geometry)
        if not center:
            dropped += 1
            continue
        lon, lat = center
        west, south, east, north = BRYAN_BOX
        if not (west <= lon <= east and south <= lat <= north):
            outside += 1
            dropped += 1
            continue
        city_hit = _hit(city_grid, lon, lat)
        city_name = city_hit["name"] if city_hit else None
        code, reject = _parcel_code(attrs.get("ZONINGCODE"), districts)
        if reject == "stub":
            stubs += 1
        elif reject == "split":
            splits += 1
        if city_name:
            zoning = code
            prefix = city_name.upper()
            place = city_name
        else:
            zone_hit = _hit(zoning_grid, lon, lat)
            if zone_hit:
                zoning = zone_hit["code"]
                prefix = "BRYAN"
                place = "Bryan County"
            else:
                zoning = code
                prefix = "BRYAN"
                place = "Bryan County"
        feature = seed.empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=pending["acres"],
            geometry=geometry,
            center=center,
            source=SOURCE,
            owner=clean(attrs.get("LASTNAME")),
            situs=_situs(attrs),
            city=city_name,
            zip_code=seed.zip_str(attrs.get("ZIP")),
            zoning=zoning,
            dor=clean(attrs.get("DIGCLASS")),
            market_value=_money(attrs.get("CURR_VAL")),
            mail1=pending["line1"],
            mail2=pending["line2"],
            mail_city=clean(attrs.get("CITY")),
            mail_state=clean(attrs.get("STATE")),
            mail_zip=seed.zip_str(attrs.get("ZIP_1")),
        )
        props = feature["properties"]
        if zoning:
            props["jurisdictionPrefix"] = prefix
            props["zoningDistrict"] = f"{place}:{zoning}"
            zoning_counts[place] += 1
        else:
            unzoned += 1
        if not city_name:
            flu_hit = _hit(flu_grid, lon, lat)
            if flu_hit:
                props["flu"] = {
                    "code": flu_hit["code"],
                    "label": flu_hit["code"],
                    "jurisdiction": "BRYAN",
                    "source": "bryan-comp-plan-2023",
                }
                flu_count += 1
        props["appraiserUrl"] = APPRAISER.replace("{parcelId}", urllib.parse.quote(parcel_id, safe=""))
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        props["lastSale"] = {"date": None, "price": None, "qualified": None}
        props["tax"]["assessedValue"] = None
        props["tax"]["taxableValue"] = None
        city_counts[city_name or "unincorporated"] += 1
        if props["tax"]["marketValue"] is not None:
            valued += 1
        features.append(feature)

    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    if not features:
        raise RuntimeError("Bryan County extract kept no parcels")
    if outside:
        raise RuntimeError(f"{outside} Bryan parcels fell outside the Georgia box")
    path, lookup, tiles = seed.write_tiles(county, features)
    city_note = ", ".join(f"{name} {city_counts[name]}" for name in sorted(city_counts))
    zone_note = ", ".join(f"{name} {zoning_counts[name]}" for name in sorted(zoning_counts))
    notes = [
        f"{expected} source rows in the TOTALACRES 5–150 query; {len(features)} parcel ids kept.",
        f"{merged} extra rows with the same parcel id were merged into the kept polygon.",
        f"Municipal boundaries: {city_note}.",
        f"Zoning: {zone_note}. Unzoned {unzoned}. Parcel CITY stubs {stubs}. Parcel attributes with a non-district slash {splits}.",
        f"Future land use joined on {flu_count} unincorporated parcels. Current value on {valued}.",
    ]
    print("\n".join(notes), flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=SOURCE,
        query_url=PARCEL_URL,
        gaps=[*static_gaps(), *notes],
        source_count=expected,
        dropped=dropped,
        tile_count=tiles,
    )


if __name__ == "__main__":
    download_bryan_county({"name": "Bryan", "fips": "13029", "state": "Georgia"}, ["Savannah"], bryan_spec())
