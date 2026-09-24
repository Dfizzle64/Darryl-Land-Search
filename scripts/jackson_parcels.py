"""Jackson County, Georgia parcels from the county Tax_Parcels service.

TOTALACRES is the 5–150 acre filter. Geometry is requested in WGS84 and checked
against the Jackson County, Georgia box so Jackson County, Missouri, Michigan,
and Wisconsin cannot land here. City Euclidean zoning on the county zoning
layer replaces a city-name stub. Maysville has no Euclidean field. Braselton
uses the zoning-land-use table when that code is clean. Future land use is the
county parcel layer, replaced inside a city by that city's NEGRC layer. Sales
stay null. Market value is the sum of the published fair-market components.
No Opportunity Zone designation is assigned.
"""

from __future__ import annotations

import urllib.parse
from collections import defaultdict

from parcel_geometry import esri_rings_to_geojson, point_in_geometry, polygon_parts

PARCEL_URL = "https://services8.arcgis.com/bcbi4lYRFOsss0F5/arcgis/rest/services/Tax_Parcels/FeatureServer/9/query"
ZONING_URL = "https://services8.arcgis.com/bcbi4lYRFOsss0F5/arcgis/rest/services/jackson_baselayers/FeatureServer/14/query"
FLU_URL = "https://services8.arcgis.com/bcbi4lYRFOsss0F5/arcgis/rest/services/jackson_baselayers/FeatureServer/15/query"
BRASELTON_URL = "https://services8.arcgis.com/bcbi4lYRFOsss0F5/arcgis/rest/services/jackson_baselayers/FeatureServer/19/query"
CITY_URL = "https://services8.arcgis.com/bcbi4lYRFOsss0F5/arcgis/rest/services/jackson_baselayers/FeatureServer/17/query"
NEGRC = "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/NEGRC_Future_Development_Map_Inventory_WFL1/FeatureServer"
# Jackson County, Georgia. Excludes Jackson MO/MI/WI and Jefferson Parish, Louisiana.
JACKSON_BOX = (-83.90, 33.94, -83.30, 34.35)
SOURCE = "ga-jackson-tax-parcels-9"
APPRAISER = "https://qpublic.schneidercorp.com/Application.aspx?App=JacksonCountyGA&Layer=Parcels&PageType=Report&KeyValue={parcelId}"

# City Euclidean columns on the county zoning polygons. Order is the fallback
# when a row has no city-name stub and more than one city column is filled.
CITY_FIELDS = (
    ("zoning_jeff", "JEFFERSON", "Jefferson"),
    ("zoning_commerce", "COMMERCE", "Commerce"),
    ("zoning_hoschton", "HOSCHTON", "Hoschton"),
    ("zoning_pendergrass", "PENDERGRASS", "Pendergrass"),
    ("zoning_arcade", "ARCADE", "Arcade"),
    ("zoning_nicholson", "NICHOLSON", "Nicholson"),
    ("zoning_talmo", "TALMO", "Talmo"),
)
CITY_STUBS = {name.upper() for _field, _prefix, name in CITY_FIELDS} | {"BRASELTON", "MAYSVILLE"}
PREFIX_CITY = {prefix: name for _field, prefix, name in CITY_FIELDS}
PREFIX_CITY["BRASELTON"] = "Braselton"
NEGRC_LAYERS = (
    ("Jefferson", 420, "negrc-jefferson-420"),
    ("Commerce", 418, "negrc-commerce-418"),
    ("Hoschton", 419, "negrc-hoschton-419"),
    ("Braselton", 417, "negrc-braselton-417"),
    ("Pendergrass", 422, "negrc-pendergrass-422"),
    ("Arcade", 414, "negrc-arcade-414"),
    ("Nicholson", 421, "negrc-nicholson-421"),
    ("Talmo", 425, "negrc-talmo-425"),
)


def jackson_spec() -> dict:
    return {
        "kind": "jackson",
        "source": SOURCE,
        "url": PARCEL_URL,
        "coverage": "complete-gte-5ac",
        "gaps": static_gaps(),
    }


def static_gaps() -> list[str]:
    return [
        "Jackson County parcels are Tax_Parcels/FeatureServer/9. Acreage is TOTALACRES, inclusive 5–150. acre_calc is not the filter. Features were requested in WGS84 and kept only inside the Jackson County, Georgia box.",
        "Situs is HOUSE_NO plus STREET_NAM when the house number is greater than 0. CITY, STATE, and ZIP on this layer are the mailing address and are not a municipality filter. Situs ZIP is not on the parcel layer.",
        "Market value is FMVRES + FMVCOM + FMVACC when that sum is greater than 0. Assessed value and taxable value are not on this layer.",
        "No public sale history. Last sale stays null. qPublic AppID=797 was not scraped.",
        "Zoning is joined on TAX_ID. A city-name value in ZONING is a stub, not a code. Jefferson, Commerce, Hoschton, Pendergrass, Arcade, Nicholson, and Talmo use the matching zoning_* field. Braselton prefers ZONINGLANDUSE.ZONING_BRASELTON when that value is a clean code, then zoning_braselton. The string <Null>, city names, and the Braselton field-name artifact are not codes. Maysville has no zoning_maysville field, so those parcels stay unzoned.",
        "Braselton and Maysville are multi-county. This extract is the Jackson County footprint only. Braselton zoning is partial: the town has no public FeatureServer, and dirty ZONING_BRASELTON values were dropped.",
        "Future land use is County_FutureLandUse_Polygons/15 joined on TAX_ID. A city-name FUTURELANDUSE value is a stub. Inside Jefferson, Commerce, Hoschton, Braselton, Pendergrass, Arcade, Nicholson, and Talmo, the matching NEGRC city layer replaces it when that polygon has a label. Pendergrass and Arcade NEGRC attributes are often blank, and those parcels fall back to a non-stub county future-land-use value. Maysville has no NEGRC future-land-use layer, and a Maysville centroid does not keep the county future-land-use value.",
        "Jackson County, Missouri, Michigan, and Wisconsin, Jefferson Parish, Louisiana, Jefferson County, Georgia, and ARC LandPro were not used.",
        "This extract does not assign Opportunity Zone designations.",
    ]


def _seed():
    import seed_market_parcels as seed

    return seed


def _fetch(url: str, params: dict) -> dict:
    return _seed().fetch_json(url, params, timeout=180)


def _page(url: str, where: str, fields: list[str], *, geometry: bool, page: int = 2000) -> list[dict]:
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


def pin_key(value: str | None) -> str:
    text = " ".join((value or "").upper().split())
    if not text:
        return ""
    sheet, _, rest = text.partition(" ")
    sheet = sheet.lstrip("0") or "0"
    return f"{sheet} {rest}".strip()


def usable_code(value: str | None) -> str | None:
    text = _seed().clean(value)
    if not text:
        return None
    token = text.upper()
    if token in {"<NULL>", "NULL", "NONE"}:
        return None
    if token in CITY_STUBS:
        return None
    if "FMV" in token or "REALPROP" in token or "DBO." in token:
        return None
    return text


def choose_zoning(row: dict | None, braselton_code: str | None) -> tuple[str | None, str | None]:
    row = row or {}
    raw = _seed().clean(row.get("ZONING"))
    stub = raw.upper() if raw and raw.upper() in CITY_STUBS else None
    if stub == "MAYSVILLE":
        return None, None
    if stub and stub != "BRASELTON":
        field, prefix, _name = next(item for item in CITY_FIELDS if item[2].upper() == stub)
        code = usable_code(row.get(field))
        return (code, prefix) if code else (None, None)
    if stub == "BRASELTON" or usable_code(row.get("zoning_braselton")):
        code = braselton_code or usable_code(row.get("zoning_braselton"))
        return (code, "BRASELTON") if code else (None, None)
    for field, prefix, _name in CITY_FIELDS:
        code = usable_code(row.get(field))
        if code:
            return code, prefix
    county = usable_code(raw)
    if county:
        return county, "JACKSON"
    if braselton_code:
        return braselton_code, "BRASELTON"
    return None, None


def _prepare_polygons(raw: list[dict], *, label_of) -> list[dict]:
    prepared: list[dict] = []
    for item in raw:
        attrs = item.get("attributes") or {}
        label = label_of(attrs)
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
        box_west, box_south, box_east, box_north = JACKSON_BOX
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
                "label": label,
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


def _situs(house, street: str | None) -> str | None:
    number = _seed().num(house)
    name = _seed().clean(street)
    if number is None or number <= 0 or not name:
        return None
    shown = str(int(number)) if number == int(number) else str(number)
    return f"{shown} {name}"


def _market_value(attrs: dict) -> float | None:
    num = _seed().num
    total = 0.0
    found = False
    for field in ("FMVRES", "FMVCOM", "FMVACC"):
        value = num(attrs.get(field))
        if value is None:
            continue
        found = True
        total += value
    if not found or total <= 0:
        return None
    return total


def _mailing_lines(attrs: dict) -> tuple[str | None, str | None]:
    clean = _seed().clean
    first = clean(attrs.get("ADDRESS1"))
    second = clean(attrs.get("ADDRESS2"))
    third = clean(attrs.get("ADDRESS3"))
    if second and not first:
        return second, third
    if first and second:
        return first, second
    return first or second, third


def download_jackson_county(county: dict, markets: list[str], spec: dict) -> dict:
    seed = _seed()
    clean = seed.clean
    num = seed.num
    print("Pulling Jackson County GA parcels", flush=True)
    where = "TOTALACRES>=5 AND TOTALACRES<=150"
    expected = seed.count_where(PARCEL_URL, where)
    raw = _page(
        PARCEL_URL,
        where,
        [
            "OBJECTID",
            "tax_id",
            "PARCEL_NO",
            "LASTNAME",
            "ADDRESS1",
            "ADDRESS2",
            "ADDRESS3",
            "CITY",
            "STATE",
            "ZIP",
            "HOUSE_NO",
            "STREET_NAM",
            "TOTALACRES",
            "FMVRES",
            "FMVCOM",
            "FMVACC",
            "DIGCLASS",
        ],
        geometry=True,
        page=1000,
    )
    if len(raw) != expected:
        raise RuntimeError(f"Jackson paged fetch returned {len(raw)}, expected {expected}")

    print("  zoning attributes", flush=True)
    zoning_rows = _page(
        ZONING_URL,
        "1=1",
        [
            "OBJECTID",
            "TAX_ID",
            "ZONING",
            "zoning_jeff",
            "zoning_commerce",
            "zoning_hoschton",
            "zoning_braselton",
            "zoning_pendergrass",
            "zoning_arcade",
            "zoning_nicholson",
            "zoning_talmo",
        ],
        geometry=False,
    )
    zoning_by_pin: dict[str, dict] = {}
    for item in zoning_rows:
        attrs = item.get("attributes") or {}
        key = pin_key(clean(attrs.get("TAX_ID")))
        if key and key not in zoning_by_pin:
            zoning_by_pin[key] = attrs

    print("  Braselton zoning table", flush=True)
    braselton_rows = _page(
        BRASELTON_URL,
        "ZONING_BRASELTON IS NOT NULL",
        ["OBJECTID", "PARCEL_NO", "ZONING_BRASELTON"],
        geometry=False,
    )
    braselton_by_pin: dict[str, str] = {}
    braselton_dropped = 0
    for item in braselton_rows:
        attrs = item.get("attributes") or {}
        key = pin_key(clean(attrs.get("PARCEL_NO")))
        code = usable_code(attrs.get("ZONING_BRASELTON"))
        if not key:
            continue
        if not code:
            braselton_dropped += 1
            continue
        braselton_by_pin.setdefault(key, code)

    print("  county future land use", flush=True)
    flu_rows = _page(FLU_URL, "1=1", ["OBJECTID", "TAX_ID", "FUTURELANDUSE"], geometry=False)
    flu_by_pin: dict[str, str] = {}
    for item in flu_rows:
        attrs = item.get("attributes") or {}
        key = pin_key(clean(attrs.get("TAX_ID")))
        label = usable_code(attrs.get("FUTURELANDUSE"))
        if key and label and key not in flu_by_pin:
            flu_by_pin[key] = label

    print("  city boundaries", flush=True)
    cities = _prepare_polygons(
        _page(CITY_URL, "1=1", ["OBJECTID", "AREANAME"], geometry=True, page=20),
        label_of=lambda attrs: clean(attrs.get("AREANAME")),
    )
    city_grid = _grid(cities)

    flu_grids: dict[str, tuple[str, dict]] = {}
    for city_name, layer_id, source in NEGRC_LAYERS:
        print(f"  NEGRC {city_name}", flush=True)
        raw_flu = _page(f"{NEGRC}/{layer_id}/query", "1=1", ["OBJECTID", "FDM_Short", "FDM_Long"], geometry=True, page=500)

        def label_of(attrs: dict, _clean=clean) -> dict:
            short = usable_code(attrs.get("FDM_Short"))
            long = usable_code(attrs.get("FDM_Long"))
            return {"code": short or long, "label": long or short}

        prepared = _prepare_polygons(raw_flu, label_of=label_of)
        flu_grids[city_name] = (source, _grid(prepared))
        print(f"    {len(prepared)} polygons in the Jackson box", flush=True)

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
        west, south, east, north = JACKSON_BOX
        if not (west <= lon <= east and south <= lat <= north):
            outside += 1
            dropped += 1
            continue
        acres = num(attrs.get("TOTALACRES"))
        if not seed.in_band(acres):
            dropped += 1
            continue
        parcel_id = clean(attrs.get("tax_id")) or clean(attrs.get("PARCEL_NO"))
        if not parcel_id:
            dropped += 1
            continue
        mail1, mail2 = _mailing_lines(attrs)
        city_hit = _hit(city_grid, lon, lat)
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
            owner=clean(attrs.get("LASTNAME")),
            situs=_situs(attrs.get("HOUSE_NO"), attrs.get("STREET_NAM")),
            city=city_hit["label"] if city_hit else None,
            zip_code=None,
            dor=clean(attrs.get("DIGCLASS")),
            market_value=_market_value(attrs),
            mail1=mail1,
            mail2=mail2,
            mail_city=clean(attrs.get("CITY")),
            mail_state=clean(attrs.get("STATE")),
            mail_zip=seed.zip_str(attrs.get("ZIP")),
        )
        feature["properties"]["appraiserUrl"] = APPRAISER.replace(
            "{parcelId}", urllib.parse.quote(parcel_id, safe="")
        )
        feature["properties"]["opportunityZone"] = None
        feature["properties"]["oz2Eligibility"] = None
        feature["properties"]["lastSale"] = {"date": None, "price": None, "qualified": None}
        previous = by_id.get(parcel_id)
        if previous is not None:
            dropped += 1
            if (feature["properties"]["acreage"] or 0) <= (previous["properties"]["acreage"] or 0):
                continue
        by_id[parcel_id] = feature

    zoning_counts: dict[str, int] = defaultdict(int)
    flu_counts: dict[str, int] = defaultdict(int)
    for feature in by_id.values():
        props = feature["properties"]
        key = pin_key(props["parcelId"])
        code, prefix = choose_zoning(zoning_by_pin.get(key), braselton_by_pin.get(key))
        if code and prefix:
            props["zoningCode"] = code
            props["jurisdictionPrefix"] = prefix
            zoning_counts[prefix] += 1
        else:
            zoning_counts["none"] += 1
        boundary_city = props.get("situsCity")
        flu_city = boundary_city if boundary_city in flu_grids else PREFIX_CITY.get(prefix or "")
        negrc = flu_grids.get(flu_city) if flu_city else None
        hit = _hit(negrc[1], *props["centroid"]) if negrc else None
        label = hit["label"] if hit else None
        if label and label.get("code"):
            props["flu"] = {
                "code": label["code"],
                "label": label["label"],
                "jurisdiction": flu_city.upper(),
                "source": negrc[0],
            }
            flu_counts[negrc[0]] += 1
            continue
        county_flu = flu_by_pin.get(key)
        if county_flu and boundary_city != "Maysville":
            props["flu"] = {
                "code": county_flu,
                "label": county_flu,
                "jurisdiction": "JACKSON",
                "source": "jackson-flu-15",
            }
            flu_counts["jackson-flu-15"] += 1
        else:
            flu_counts["none"] += 1

    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    if not features:
        raise RuntimeError("Jackson County extract kept no parcels")
    if outside:
        raise RuntimeError(f"{outside} Jackson parcels fell outside the Georgia box")
    path, lookup, tiles = seed.write_tiles(county, features)
    zoning_note = ", ".join(f"{name} {zoning_counts[name]}" for name in sorted(zoning_counts))
    flu_note = ", ".join(f"{name} {flu_counts[name]}" for name in sorted(flu_counts))
    notes = [
        f"{expected} source rows in the TOTALACRES 5–150 query; {len(features)} parcel ids kept.",
        f"Zoning joins: {zoning_note}.",
        f"Dirty Braselton zoning values dropped from the land-use table: {braselton_dropped}.",
        f"Future land use: {flu_note}.",
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
    download_jackson_county({"name": "Jackson", "fips": "13157", "state": "Georgia"}, ["Atlanta"], jackson_spec())
