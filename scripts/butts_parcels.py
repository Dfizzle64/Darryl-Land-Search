"""Butts County, Georgia parcels from the SchneiderCorp qPublic MapServer.

TOTALACRES is the 5–150 acre filter. Geometry is requested in WGS84 and checked
against the Butts County, Georgia box so Butte County, California and Jackson,
Mississippi cannot land here. City zoning polygons win over the county layer.
Unincorporated parcels use the parcel Zoning_01 code, then County Zoning.
Future land use and sales stay null. CURR_VAL and ESTTAX are the published
tax figures. No Opportunity Zone designation is assigned.
"""

from __future__ import annotations

import urllib.parse
from collections import defaultdict

from parcel_geometry import esri_rings_to_geojson, point_in_geometry, polygon_parts

QUERY = "https://wfs.schneidercorp.com/arcgis/rest/services/ButtsCountyGA_WFS/MapServer/{layer}/query"
PARCEL_URL = QUERY.format(layer=0)
# Butts County, Georgia. Excludes Butte County, California and Jackson, Mississippi.
BUTTS_BOX = (-84.20, 33.10, -83.70, 33.55)
SOURCE = "ga-butts-wfs-0"
APPRAISER = "https://qpublic.schneidercorp.com/Application.aspx?App=ButtsCountyGA&Layer=Parcels&PageType=Report&KeyValue={parcelId}"
CITY_LAYERS = (
    (4, "JACKSON", "Jackson", 2),
    (5, "FLOVILLA", "Flovilla", 1),
    (6, "JENKINSBURG", "Jenkinsburg", 3),
)
COUNTY_LAYER = (3, "BUTTS", 0)
CITY_NAMES = {name: prefix for _layer, prefix, name, _jurisdiction in CITY_LAYERS}
STUBS = {"COUNTY", "JACKSON", "FLOVILLA", "JENKINSBURG", "FLOWVILLA", "<NULL>", "NULL", "NONE"}


def butts_spec() -> dict:
    return {
        "kind": "butts",
        "source": SOURCE,
        "url": PARCEL_URL,
        "coverage": "complete-gte-5ac",
        "gaps": static_gaps(),
    }


def static_gaps() -> list[str]:
    return [
        "Butts County parcels are wfs.schneidercorp.com ButtsCountyGA_WFS/MapServer/0. Acreage is TOTALACRES, inclusive 5–150. DEED_ACRES is not the filter. The service is State Plane Georgia West; features were requested in WGS84 and kept only inside the Butts County, Georgia box.",
        "PropCity is the municipality flag. County means unincorporated. OwnerCity is the mailing city and is not a municipality filter. PropZip is sparse on this layer. Site Structure Address Post_Code was not joined, so most situs ZIP values stay null.",
        "CURR_VAL is the published current value. ESTTAX is the published estimated tax. Assessed value and taxable value are not on this layer.",
        "SALES_AREA is a neighborhood code, not a deed. Last sale stays null. qPublic App=ButtsCountyGA was not scraped.",
        "City zoning is a centroid join: City of Jackson MapServer/4, Flovilla MapServer/5 (layer title Flowvilla), then Jenkinsburg MapServer/6. A city PropCity with no city polygon uses Zoning_01. Unincorporated parcels use Zoning_01 when that code is filled, then dissolved County Zoning MapServer/3. Zoning_02 and Zoning_03 split codes are not stored.",
        "Future land use is the Butts County Comprehensive Plan PDF. No future-land-use service was joined. City of Jackson's comprehensive plan is also a PDF.",
        "Butte County, California, Jackson, Mississippi, Jackson County, Georgia, and ARC LandPro were not used.",
        "This extract does not assign Opportunity Zone designations.",
    ]


def _seed():
    import seed_market_parcels as seed

    return seed


def _fetch(url: str, params: dict) -> dict:
    return _seed().fetch_json(url, params, timeout=180)


def _page(url: str, where: str, fields: list[str], *, geometry: bool, page: int = 1000) -> list[dict]:
    features: list[dict] = []
    offset = 0
    seen: set[int] = set()
    while True:
        data = _fetch(
            url,
            {
                "where": where,
                "outFields": ",".join(fields),
                "returnGeometry": "true" if geometry else "false",
                "outSR": "4326",
                "orderByFields": "OBJECTID",
                "resultOffset": str(offset),
                "resultRecordCount": str(page),
                "f": "json",
            },
        )
        if data.get("error"):
            raise RuntimeError(str(data["error"])[:300])
        batch = data.get("features") or []
        if not batch:
            break
        first = (batch[0].get("attributes") or {}).get("OBJECTID")
        if isinstance(first, int) and first in seen:
            raise RuntimeError(f"paging repeated OBJECTID {first} at offset {offset}")
        for item in batch:
            object_id = (item.get("attributes") or {}).get("OBJECTID")
            if isinstance(object_id, int):
                seen.add(object_id)
        features.extend(batch)
        print(f"    {url.rsplit('/', 2)[-2]} {len(features)}", flush=True)
        if len(batch) < page:
            break
        offset += len(batch)
    return features


def usable_code(value: str | None) -> str | None:
    text = _seed().clean(value)
    if not text:
        return None
    if text.upper() in STUBS:
        return None
    return text


def _money(value) -> float | None:
    number = _seed().num(value)
    if number is None or number <= 0:
        return None
    return round(number, 2)


def _situs(value: str | None) -> str | None:
    text = _seed().clean(value)
    if not text:
        return None
    return " ".join(text.split())


def _jurisdiction_ok(attrs: dict, expected: int) -> bool:
    raw = attrs.get("Jurisdiction")
    if raw is None or str(raw).strip() == "":
        return True
    try:
        return int(float(raw)) == expected
    except (TypeError, ValueError):
        return False


def _prepare_polygons(raw: list[dict], prefix: str, jurisdiction: int) -> list[dict]:
    prepared: list[dict] = []
    for item in raw:
        attrs = item.get("attributes") or {}
        if not _jurisdiction_ok(attrs, jurisdiction):
            continue
        code = usable_code(attrs.get("Zoning"))
        if not code:
            continue
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        if not geometry:
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
        west, south, east, north = min(xs), min(ys), max(xs), max(ys)
        box_west, box_south, box_east, box_north = BUTTS_BOX
        if east < box_west or west > box_east or north < box_south or south > box_north:
            continue
        area = 0.0
        for poly in polygon_parts(geometry):
            outer = poly[0]
            for i in range(len(outer) - 1):
                area += outer[i][0] * outer[i + 1][1] - outer[i + 1][0] * outer[i][1]
        prepared.append(
            {
                "bbox": (west, south, east, north),
                "area": abs(area / 2.0) or 1e-12,
                "code": code,
                "prefix": prefix,
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


def download_butts_county(county: dict, markets: list[str], spec: dict) -> dict:
    seed = _seed()
    clean = seed.clean
    num = seed.num
    print("Pulling Butts County GA parcels", flush=True)
    where = "TOTALACRES>=5 AND TOTALACRES<=150"
    expected = seed.count_where(PARCEL_URL, where)
    raw = _page(
        PARCEL_URL,
        where,
        [
            "OBJECTID",
            "PARCEL_NO",
            "GSI_PIN",
            "_v_ON",
            "OwnerAddr",
            "OwnerCity",
            "OwnerState",
            "OwnerZip",
            "PropAddr",
            "PropCity",
            "PropZip",
            "TOTALACRES",
            "CURR_VAL",
            "ESTTAX",
            "Zoning_01",
            "Zoning_02",
            "Zoning_03",
            "DIGCLASS",
        ],
        geometry=True,
    )
    if len(raw) != expected:
        raise RuntimeError(f"Butts paged fetch returned {len(raw)}, expected {expected}")

    city_grids = []
    for layer, prefix, name, jurisdiction in CITY_LAYERS:
        print(f"  zoning {name}", flush=True)
        prepared = _prepare_polygons(
            _page(QUERY.format(layer=layer), "1=1", ["OBJECTID", "Zoning", "Jurisdiction"], geometry=True, page=500),
            prefix,
            jurisdiction,
        )
        city_grids.append((name, prefix, _grid(prepared)))
        print(f"    {len(prepared)} zoning polygons", flush=True)
    print("  county zoning", flush=True)
    county_prepared = _prepare_polygons(
        _page(QUERY.format(layer=COUNTY_LAYER[0]), "1=1", ["OBJECTID", "Zoning", "Jurisdiction"], geometry=True, page=500),
        COUNTY_LAYER[1],
        COUNTY_LAYER[2],
    )
    county_grid = _grid(county_prepared)
    print(f"    {len(county_prepared)} county zoning polygons", flush=True)

    by_id: dict[str, dict] = {}
    dropped = 0
    outside = 0
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
        west, south, east, north = BUTTS_BOX
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
        prop_city = clean(attrs.get("PropCity"))
        situs_city = prop_city if prop_city in CITY_NAMES else None
        feature = seed.empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source=SOURCE,
            owner=clean(attrs.get("_v_ON")),
            situs=_situs(attrs.get("PropAddr")),
            city=situs_city,
            zip_code=seed.zip_str(attrs.get("PropZip")),
            dor=clean(attrs.get("DIGCLASS")),
            market_value=_money(attrs.get("CURR_VAL")),
            mail1=_situs(attrs.get("OwnerAddr")),
            mail_city=clean(attrs.get("OwnerCity")),
            mail_state=clean(attrs.get("OwnerState")),
            mail_zip=seed.zip_str(attrs.get("OwnerZip")),
        )
        feature["properties"]["tax"]["taxes"] = _money(attrs.get("ESTTAX"))
        feature["properties"]["appraiserUrl"] = APPRAISER.replace(
            "{parcelId}", urllib.parse.quote(parcel_id, safe="")
        )
        feature["properties"]["opportunityZone"] = None
        feature["properties"]["oz2Eligibility"] = None
        feature["properties"]["lastSale"] = {"date": None, "price": None, "qualified": None}
        feature["properties"]["flu"] = None
        feature["_zoning01"] = usable_code(attrs.get("Zoning_01"))
        feature["_propCity"] = prop_city
        feature["_split"] = bool(usable_code(attrs.get("Zoning_02")) or usable_code(attrs.get("Zoning_03")))
        previous = by_id.get(parcel_id)
        if previous is not None:
            dropped += 1
            if (feature["properties"]["acreage"] or 0) <= (previous["properties"]["acreage"] or 0):
                continue
        by_id[parcel_id] = feature

    zoning_counts: dict[str, int] = defaultdict(int)
    zoning_sources: dict[str, int] = defaultdict(int)
    split_zoning = sum(1 for feature in by_id.values() if feature.get("_split"))
    for feature in by_id.values():
        feature.pop("_split", None)
        props = feature["properties"]
        lon, lat = props["centroid"]
        chosen = None
        source = None
        for _name, _prefix, grid in city_grids:
            hit = _hit(grid, lon, lat)
            if hit:
                chosen = hit
                source = "city-polygon"
                break
        if chosen is None:
            city_prefix = CITY_NAMES.get(feature.get("_propCity") or "")
            attribute = feature.get("_zoning01")
            if city_prefix and attribute:
                props["zoningCode"] = attribute
                props["jurisdictionPrefix"] = city_prefix
                zoning_counts[city_prefix] += 1
                zoning_sources["city-attribute"] += 1
                feature.pop("_zoning01", None)
                feature.pop("_propCity", None)
                continue
            if city_prefix:
                zoning_counts["none"] += 1
                zoning_sources["city-missing"] += 1
                feature.pop("_zoning01", None)
                feature.pop("_propCity", None)
                continue
            if attribute:
                props["zoningCode"] = attribute
                props["jurisdictionPrefix"] = "BUTTS"
                zoning_counts["BUTTS"] += 1
                zoning_sources["county-attribute"] += 1
                feature.pop("_zoning01", None)
                feature.pop("_propCity", None)
                continue
            county_hit = _hit(county_grid, lon, lat)
            if county_hit:
                chosen = county_hit
                source = "county-polygon"
        if chosen:
            props["zoningCode"] = chosen["code"]
            props["jurisdictionPrefix"] = chosen["prefix"]
            zoning_counts[chosen["prefix"]] += 1
            zoning_sources[source or "polygon"] += 1
        else:
            zoning_counts["none"] += 1
            zoning_sources["none"] += 1
        feature.pop("_zoning01", None)
        feature.pop("_propCity", None)
        feature.pop("_split", None)

    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    if not features:
        raise RuntimeError("Butts County extract kept no parcels")
    if outside:
        raise RuntimeError(f"{outside} Butts parcels fell outside the Georgia box")
    path, lookup, tiles = seed.write_tiles(county, features)
    zoning_note = ", ".join(f"{name} {zoning_counts[name]}" for name in sorted(zoning_counts))
    source_note = ", ".join(f"{name} {zoning_sources[name]}" for name in sorted(zoning_sources))
    notes = [
        f"{expected} source rows in the TOTALACRES 5–150 query; {len(features)} parcel ids kept.",
        f"Zoning joins: {zoning_note}.",
        f"Zoning sources: {source_note}.",
        f"{split_zoning} kept parcels have Zoning_02 or Zoning_03 split codes that were not stored.",
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
    download_butts_county({"name": "Butts", "fips": "13035", "state": "Georgia"}, ["Atlanta"], butts_spec())
