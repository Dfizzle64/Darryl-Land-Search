"""Effingham County, Georgia parcels from the county Parcels2024 service.

TOTALACRES is the 5–150 acre filter. Geometry is requested in WGS84 and checked
against the Effingham County, Georgia box so Effingham County, Illinois cannot
land here. Zoning is the parcel ZCODE. Future land use is FLUM EFF_REV2 joined
on parcel id. Sale price and market value come from ParcelUpdate when that
older table has a row. City zoning and city future land use are not invented.
No Opportunity Zone designation is assigned.
"""

from __future__ import annotations

import datetime
import urllib.parse
from collections import defaultdict

from parcel_geometry import esri_rings_to_geojson, point_in_geometry, polygon_parts

PARCEL_URL = "https://services.arcgis.com/9scQWTgPOi3GxJRr/arcgis/rest/services/Parcels2024/FeatureServer/0/query"
UPDATE_URL = "https://services.arcgis.com/9scQWTgPOi3GxJRr/arcgis/rest/services/ParcelUpdate/FeatureServer/0/query"
FLU_URL = "https://services.arcgis.com/9scQWTgPOi3GxJRr/arcgis/rest/services/FLUM_20240903_BOC_APPR_2/FeatureServer/0/query"
CITY_URL = "https://services.arcgis.com/9scQWTgPOi3GxJRr/arcgis/rest/services/County_Municipal_Boundaries/FeatureServer/0/query"
# Effingham County, Georgia. Excludes Effingham County, Illinois.
EFFINGHAM_BOX = (-81.65, 32.00, -81.05, 32.70)
SOURCE = "ga-effingham-parcels-2024"
APPRAISER = (
    "https://qpublic.schneidercorp.com/Application.aspx?AppID=666&LayerID=11348"
    "&PageTypeID=4&PageID=4716&KeyValue={parcelId}"
)
CITY_NAMES = {"Rincon", "Guyton", "Springfield"}
STUBS = {"<NULL>", "NULL", "NONE", "RINCON", "GUYTON", "SPRINGFIELD", "EFFINGHAM"}


def effingham_spec() -> dict:
    return {
        "kind": "effingham",
        "source": SOURCE,
        "url": PARCEL_URL,
        "coverage": "complete-gte-5ac",
        "gaps": static_gaps(),
    }


def static_gaps() -> list[str]:
    return [
        "Effingham County parcels are Parcels2024/FeatureServer/0. Acreage is TOTALACRES, inclusive 5–150. ACRES is not the filter. Features were requested in WGS84 and kept only inside the Effingham County, Georgia box.",
        "Mailing city is not a municipality. Rincon, Guyton, and Springfield come from County_Municipal_Boundaries. Bloomingdale, Savannah, and Meldrim postal names are not city limits.",
        "Zoning is the parcel ZCODE. There is no separate Euclidean zoning service. Rincon, Guyton, and Springfield have no public city zoning FeatureServer, so no city zoning code was invented. A city zoning map PDF can differ from ZCODE.",
        "Future land use is FLUM_20240903_BOC_APPR_2 EFF_REV2 joined on PARCEL_NO. That layer is smaller than Parcels2024, so some parcels have no future land use. City future-land-use services were not published and were not invented.",
        "Parcels2024 has SalesDate and esttax, and no sale price or current value. SALEPRICE and CURR_VAL are joined from ParcelUpdate when that parcel id is present. Missing joins stay null. Assessed value and taxable value are not on these layers. qPublic was not scraped.",
        "Effingham County, Illinois, Chatham County SAGIS, and ARC LandPro were not used.",
        "This extract does not assign Opportunity Zone designations.",
    ]


def _seed():
    import seed_market_parcels as seed

    return seed


def _fetch(url: str, params: dict) -> dict:
    return _seed().fetch_json(url, params, timeout=180)


def _page(url: str, where: str, fields: list[str], *, geometry: bool, order: str, page: int = 1000) -> list[dict]:
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
                "orderByFields": order,
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
        first = (batch[0].get("attributes") or {}).get(order)
        if isinstance(first, int) and first in seen:
            raise RuntimeError(f"paging repeated {order} {first} at offset {offset}")
        for item in batch:
            object_id = (item.get("attributes") or {}).get(order)
            if isinstance(object_id, int):
                seen.add(object_id)
        features.extend(batch)
        print(f"    {url.rsplit('/', 2)[-2]} {len(features)}", flush=True)
        if len(batch) < page:
            break
        offset += len(batch)
    return features


def pin_key(value: str | None) -> str:
    return " ".join((value or "").upper().split())


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


def _collapse(value: str | None) -> str | None:
    text = _seed().clean(value)
    if not text:
        return None
    return " ".join(text.split())


def _sale_date(value) -> str | None:
    if value is None or value == "":
        return None
    number = _seed().num(value)
    if number is not None:
        if number <= 0:
            return None
        if number > 10_000_000_000:
            moment = datetime.datetime.fromtimestamp(number / 1000, datetime.timezone.utc)
            return moment.date().isoformat()
        return None
    text = _seed().clean(value)
    if not text:
        return None
    return text[:10]


def _situs(attrs: dict) -> str | None:
    street = _collapse(attrs.get("StreetAdd"))
    if street:
        return street
    clean = _seed().clean
    number = _seed().num(attrs.get("HOUSE_NO"))
    parts = []
    if number is not None and number > 0:
        parts.append(str(int(number)) if number == int(number) else str(number))
    for field in ("stdirect", "STREET_NAM", "sttype"):
        piece = clean(attrs.get(field))
        if piece:
            parts.append(piece)
    return " ".join(parts) or None


def _prepare_cities(raw: list[dict]) -> list[dict]:
    prepared: list[dict] = []
    for item in raw:
        attrs = item.get("attributes") or {}
        name = _seed().clean(attrs.get("NAME"))
        if name not in CITY_NAMES:
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
        area = 0.0
        for poly in polygon_parts(geometry):
            outer = poly[0]
            for i in range(len(outer) - 1):
                area += outer[i][0] * outer[i + 1][1] - outer[i + 1][0] * outer[i][1]
        prepared.append(
            {
                "bbox": (min(xs), min(ys), max(xs), max(ys)),
                "area": abs(area / 2.0) or 1e-12,
                "name": name,
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


def download_effingham_county(county: dict, markets: list[str], spec: dict) -> dict:
    seed = _seed()
    clean = seed.clean
    num = seed.num
    print("Pulling Effingham County GA parcels", flush=True)
    where = "TOTALACRES>=5 AND TOTALACRES<=150"
    expected = seed.count_where(PARCEL_URL, where)
    raw = _page(
        PARCEL_URL,
        where,
        [
            "FID",
            "PARCEL_NO",
            "LASTNAME",
            "address1",
            "address2",
            "city",
            "state",
            "zip",
            "StreetAdd",
            "HOUSE_NO",
            "stdirect",
            "STREET_NAM",
            "sttype",
            "TOTALACRES",
            "SalesDate",
            "esttax",
            "ZCODE",
            "zoningcode",
            "OverlayDis",
            "DIGCLASS",
        ],
        geometry=True,
        order="FID",
    )
    if len(raw) != expected:
        raise RuntimeError(f"Effingham paged fetch returned {len(raw)}, expected {expected}")

    print("  ParcelUpdate price and value", flush=True)
    updates = _page(
        UPDATE_URL,
        "1=1",
        ["OBJECTID", "PARCEL_NO", "SALEPRICE", "CURR_VAL"],
        geometry=False,
        order="OBJECTID",
    )
    update_by_pin: dict[str, dict] = {}
    for item in updates:
        attrs = item.get("attributes") or {}
        key = pin_key(clean(attrs.get("PARCEL_NO")))
        if key and key not in update_by_pin:
            update_by_pin[key] = attrs

    print("  future land use", flush=True)
    flu_rows = _page(FLU_URL, "1=1", ["FID", "PARCEL_NO", "EFF_REV2"], geometry=False, order="FID")
    flu_by_pin: dict[str, str] = {}
    for item in flu_rows:
        attrs = item.get("attributes") or {}
        key = pin_key(clean(attrs.get("PARCEL_NO")))
        label = usable_code(attrs.get("EFF_REV2"))
        if key and label and key not in flu_by_pin:
            flu_by_pin[key] = label

    print("  city boundaries", flush=True)
    cities = _prepare_cities(_page(CITY_URL, "1=1", ["FID", "NAME"], geometry=True, order="FID", page=10))
    if len(cities) != 3:
        raise RuntimeError(f"Expected Rincon, Guyton, and Springfield, got {len(cities)}")
    city_grid = _grid(cities)

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
        west, south, east, north = EFFINGHAM_BOX
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
        key = pin_key(parcel_id)
        update = update_by_pin.get(key) or {}
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
            situs=_situs(attrs),
            city=city_hit["name"] if city_hit else None,
            zip_code=None,
            zoning=usable_code(attrs.get("ZCODE")) or usable_code(attrs.get("zoningcode")),
            dor=clean(attrs.get("DIGCLASS")),
            sale_date=_sale_date(attrs.get("SalesDate")),
            sale_price=_money(update.get("SALEPRICE")),
            market_value=_money(update.get("CURR_VAL")),
            mail1=_collapse(attrs.get("address1")),
            mail2=_collapse(attrs.get("address2")),
            mail_city=clean(attrs.get("city")),
            mail_state=clean(attrs.get("state")),
            mail_zip=seed.zip_str(attrs.get("zip")),
        )
        feature["properties"]["tax"]["taxes"] = _money(attrs.get("esttax"))
        feature["properties"]["jurisdictionPrefix"] = "EFFINGHAM"
        overlay = usable_code(attrs.get("OverlayDis"))
        if overlay:
            feature["properties"]["zoningOverlay"] = overlay
        flu = flu_by_pin.get(key)
        if flu:
            feature["properties"]["flu"] = {
                "code": flu,
                "label": flu,
                "jurisdiction": "EFFINGHAM",
                "source": "flum-20240903",
            }
        feature["properties"]["appraiserUrl"] = APPRAISER.replace("{parcelId}", urllib.parse.quote(parcel_id, safe=""))
        feature["properties"]["opportunityZone"] = None
        feature["properties"]["oz2Eligibility"] = None
        feature["properties"]["lastSale"]["qualified"] = None
        previous = by_id.get(parcel_id)
        if previous is not None:
            dropped += 1
            if (feature["properties"]["acreage"] or 0) <= (previous["properties"]["acreage"] or 0):
                continue
        by_id[parcel_id] = feature

    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    if not features:
        raise RuntimeError("Effingham County extract kept no parcels")
    if outside:
        raise RuntimeError(f"{outside} Effingham parcels fell outside the Georgia box")
    cities_count: dict[str, int] = defaultdict(int)
    zoned = 0
    flu_count = 0
    priced = 0
    valued = 0
    dated = 0
    for feature in features:
        props = feature["properties"]
        cities_count[props.get("situsCity") or "unincorporated"] += 1
        if props.get("zoningCode"):
            zoned += 1
        if props.get("flu"):
            flu_count += 1
        if props["lastSale"]["price"] is not None:
            priced += 1
        if props["lastSale"]["date"]:
            dated += 1
        if props["tax"]["marketValue"] is not None:
            valued += 1
    path, lookup, tiles = seed.write_tiles(county, features)
    city_note = ", ".join(f"{name} {cities_count[name]}" for name in sorted(cities_count))
    notes = [
        f"{expected} source rows in the TOTALACRES 5–150 query; {len(features)} parcel ids kept.",
        f"Municipal boundaries: {city_note}.",
        f"ZCODE filled on {zoned} parcels. Future land use joined on {flu_count}.",
        f"ParcelUpdate joined a sale price on {priced} parcels, a sale date is on {dated}, and a current value on {valued}.",
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
    download_effingham_county({"name": "Effingham", "fips": "13103", "state": "Georgia"}, ["Savannah"], effingham_spec())
