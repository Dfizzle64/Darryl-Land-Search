"""Hall County, Georgia parcels from the official hallgis MapServer.

DEED_ACRE is the 5–150 acre filter. Geometry is requested in WGS84 and checked
against the Hall County, Georgia box so Hall, Nebraska and Gainesville, Florida
cannot land here. County zoning is ZoningTab/15. Gainesville, Flowery Branch,
and Oakwood city zoning replace it. MUNI stubs are not zoning codes. Future
land use is HC_FLU_2024 by parcel id, with Gainesville FLU_2022 inside that
city. Sales stay null. CUR_VALUE is the published market value; land value is
not copied into it. No Opportunity Zone designation is assigned.
"""

from __future__ import annotations

import urllib.parse
from collections import defaultdict

from parcel_geometry import esri_rings_to_geojson, point_in_geometry, polygon_parts

PARCEL_URL = "https://hallgis.hallcounty.org/arcgis/rest/services/HallCo_Addr_Pcl_Rds/MapServer/1/query"
ZONING_LAYERS = (
    ("https://hallgis.hallcounty.org/arcgis/rest/services/ZoningTab/MapServer/14/query", "GAINESVILLE", "GVL"),
    ("https://hallgis.hallcounty.org/arcgis/rest/services/ZoningTab/MapServer/13/query", "FLOWERY BRANCH", "FLB"),
    ("https://hallgis.hallcounty.org/arcgis/rest/services/ZoningTab/MapServer/16/query", "OAKWOOD", "OAK"),
    ("https://hallgis.hallcounty.org/arcgis/rest/services/ZoningTab/MapServer/15/query", "HALL COUNTY", "HAL"),
)
FLU_URL = "https://hallgis.hallcounty.org/arcgis/rest/services/HC_FutureLandUse_2024/MapServer/0/query"
GAINESVILLE_FLU_URL = "https://hallgis.hallcounty.org/arcgis/rest/services/Gnvl_FutureLandUse/MapServer/3/query"
# Hall County, Georgia. Excludes Hall, Nebraska and Gainesville, Florida.
HALL_BOX = (-84.25, 34.00, -83.45, 34.65)
SOURCE = "ga-hall-addr-pcl-1"
APPRAISER = "https://qpublic.schneidercorp.com/Application.aspx?App=HallCountyGA&Layer=Parcels&PageType=Report&KeyValue={parcelId}"


def hall_spec() -> dict:
    return {
        "kind": "hall",
        "source": SOURCE,
        "url": PARCEL_URL,
        "coverage": "complete-gte-5ac",
        "gaps": static_gaps(),
    }


def static_gaps() -> list[str]:
    return [
        "Hall County parcels are hallgis.hallcounty.org HallCo_Addr_Pcl_Rds/MapServer/1. Acreage is deeded DEED_ACRE, inclusive 5–150. CALC_ACRE is not the filter. The service is State Plane Georgia West; features were requested in WGS84 and kept only inside the Hall County, Georgia box.",
        "Owner and mailing are blank when NO_RELEASE is 1. Those names were not backfilled from qPublic.",
        "SITE_CITY is the postal community, not a city-limits filter. Gainesville postal addresses include unincorporated parcels.",
        "CUR_VALUE is the published fair-market string. Assessed value and taxable value are not on this layer. LAND_VALUE is not copied to market value.",
        "No public sale history. Last sale stays null. qPublic AppID=724 was not scraped.",
        "Zoning is a centroid join. City layers win: Gainesville ZoningTab/14, Flowery Branch /13, Oakwood /16, then unincorporated Hall County ZoningTab/15. ZN_CLASS MUNI is not a zoning code.",
        "Lula, Clermont, Gillsville, Braselton, Buford, and Rest Haven publish MUNI stubs only. Their Euclidean zoning stays null. Braselton, Buford, Lula, Gillsville, and Rest Haven are multi-county; this extract is the Hall County footprint only.",
        "Future land use is HC_FutureLandUse_2024/0 joined on pin. Inside Gainesville city limits, Gnvl_FutureLandUse/3 FLU_2022 replaces it. Flowery Branch, Gillsville, Braselton, Buford, and Rest Haven have no city future-land-use service. County future land use inside those cities is the county comp-plan polygon, not a city-adopted map.",
        "Hall County, Nebraska, Gainesville, Florida, and ARC LandPro were not used.",
        "This extract does not assign Opportunity Zone designations.",
    ]


def _seed():
    import seed_market_parcels as seed

    return seed


def _fetch(url: str, params: dict) -> dict:
    return _seed().fetch_json(url, params, timeout=180)


def _page(url: str, where: str, fields: list[str], *, geometry: bool, out_sr: int = 4326, page: int = 1000) -> list[dict]:
    features: list[dict] = []
    offset = 0
    while True:
        data = _fetch(
            url,
            {
                "where": where,
                "outFields": ",".join(fields),
                "returnGeometry": "true" if geometry else "false",
                "outSR": str(out_sr),
                "orderByFields": "OBJECTID",
                "resultOffset": str(offset),
                "resultRecordCount": str(page),
                "f": "json",
            },
        )
        if data.get("error"):
            raise RuntimeError(str(data["error"])[:300])
        batch = data.get("features") or []
        features.extend(batch)
        print(f"    {url.rsplit('/', 2)[-2]} {len(features)}", flush=True)
        if len(batch) < page:
            break
        offset += len(batch)
    return features


def _prepare_polygons(raw: list[dict], code_field: str, jurisdiction: str, prefix: str) -> list[dict]:
    clean = _seed().clean
    prepared: list[dict] = []
    for item in raw:
        attrs = item.get("attributes") or {}
        code = clean(attrs.get(code_field))
        if not code or code.upper() == "MUNI":
            continue
        layer_jurisdiction = clean(attrs.get("ZN_JURISDI"))
        if layer_jurisdiction and layer_jurisdiction.upper() != jurisdiction:
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
                "code": code,
                "jurisdiction": jurisdiction,
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


def _pin_key(value: str | None) -> str:
    return " ".join((value or "").upper().split())


def download_hall_county(county: dict, markets: list[str], spec: dict) -> dict:
    seed = _seed()
    clean = seed.clean
    num = seed.num
    print("Pulling Hall County GA parcels", flush=True)
    expected = seed.count_where(PARCEL_URL, "DEED_ACRE>=5 AND DEED_ACRE<=150")
    raw = _page(
        PARCEL_URL,
        "DEED_ACRE>=5 AND DEED_ACRE<=150",
        [
            "PIN",
            "OWNER",
            "MAILADR1",
            "MAILADR2",
            "MAILCITY",
            "MAILSTATE",
            "MAILZIP",
            "SITE_LOCATION",
            "SITE_CITY",
            "ZIP",
            "DEED_ACRE",
            "CUR_VALUE",
            "DIGCLASS",
            "NO_RELEASE",
        ],
        geometry=True,
    )
    if len(raw) != expected:
        raise RuntimeError(f"Hall paged fetch returned {len(raw)}, expected {expected}")

    zoning_grids = []
    for url, jurisdiction, prefix in ZONING_LAYERS:
        print(f"  zoning {jurisdiction}", flush=True)
        layer = _page(url, "1=1", ["ZN_CLASS", "ZN_JURISDI"], geometry=True, page=500)
        prepared = _prepare_polygons(layer, "ZN_CLASS", jurisdiction, prefix)
        zoning_grids.append((jurisdiction, _grid(prepared)))
        print(f"    {len(prepared)} zoning polygons", flush=True)

    print("  county FLU pins", flush=True)
    flu_rows = _page(FLU_URL, "1=1", ["pin", "FLU"], geometry=False, page=2000)
    flu_by_pin: dict[str, str] = {}
    for item in flu_rows:
        attrs = item.get("attributes") or {}
        pin = _pin_key(clean(attrs.get("pin")))
        label = clean(attrs.get("FLU"))
        if pin and label and pin not in flu_by_pin:
            flu_by_pin[pin] = label
    print("  Gainesville FLU", flush=True)
    gainesville_flu = _prepare_polygons(
        _page(GAINESVILLE_FLU_URL, "1=1", ["FLU_2022"], geometry=True, page=20),
        "FLU_2022",
        "GAINESVILLE",
        "GVL",
    )
    gainesville_grid = _grid(gainesville_flu)

    by_id: dict[str, dict] = {}
    dropped = 0
    outside = 0
    suppressed = 0
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
        west, south, east, north = HALL_BOX
        if not (west <= lon <= east and south <= lat <= north):
            outside += 1
            dropped += 1
            continue
        acres = num(attrs.get("DEED_ACRE"))
        if not seed.in_band(acres):
            dropped += 1
            continue
        parcel_id = clean(attrs.get("PIN"))
        if not parcel_id:
            dropped += 1
            continue
        release = attrs.get("NO_RELEASE")
        private = str(release).strip() in {"1", "1.0"}
        if private:
            suppressed += 1
        market = num(attrs.get("CUR_VALUE"))
        if market is not None and market <= 0:
            market = None
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
            owner=None if private else clean(attrs.get("OWNER")),
            situs=clean(attrs.get("SITE_LOCATION")),
            city=clean(attrs.get("SITE_CITY")),
            zip_code=seed.zip_str(attrs.get("ZIP")),
            dor=clean(attrs.get("DIGCLASS")),
            market_value=market,
            mail1=None if private else clean(attrs.get("MAILADR1")),
            mail2=None if private else clean(attrs.get("MAILADR2")),
            mail_city=None if private else clean(attrs.get("MAILCITY")),
            mail_state=None if private else clean(attrs.get("MAILSTATE")),
            mail_zip=None if private else seed.zip_str(attrs.get("MAILZIP")),
        )
        feature["properties"]["appraiserUrl"] = APPRAISER.replace(
            "{parcelId}", urllib.parse.quote(parcel_id, safe="")
        )
        feature["properties"]["opportunityZone"] = None
        feature["properties"]["oz2Eligibility"] = None
        feature["properties"]["lastSale"] = {"date": None, "price": None, "qualified": None}
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature

    zoning_counts = {name: 0 for name, _grid in zoning_grids}
    flu_county = 0
    flu_gainesville = 0
    for feature in by_id.values():
        lon, lat = feature["properties"]["centroid"]
        chosen = None
        for jurisdiction, grid in zoning_grids:
            hit = _hit(grid, lon, lat)
            if hit:
                chosen = hit
                zoning_counts[jurisdiction] += 1
                break
        if chosen:
            feature["properties"]["zoningCode"] = chosen["code"]
            feature["properties"]["jurisdictionPrefix"] = chosen["prefix"]
        gainesville = _hit(gainesville_grid, lon, lat)
        if gainesville:
            feature["properties"]["flu"] = {
                "code": gainesville["code"],
                "label": gainesville["code"],
                "jurisdiction": "GAINESVILLE",
                "source": "gnvl-flu-2022",
            }
            flu_gainesville += 1
            continue
        label = flu_by_pin.get(_pin_key(feature["properties"]["parcelId"]))
        if label:
            feature["properties"]["flu"] = {
                "code": label,
                "label": label,
                "jurisdiction": "HALL",
                "source": "hc-flu-2024",
            }
            flu_county += 1

    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    if not features:
        raise RuntimeError("Hall County extract kept no parcels")
    if outside:
        raise RuntimeError(f"{outside} Hall parcels fell outside the Georgia box")
    path, lookup, tiles = seed.write_tiles(county, features)
    notes = [
        f"{expected} source rows in the DEED_ACRE 5–150 query; {len(features)} parcel ids kept.",
        f"Owner and mailing suppressed on {suppressed} NO_RELEASE parcels.",
        "Zoning centroids: "
        + ", ".join(f"{name} {zoning_counts[name]}" for name, _grid in zoning_grids)
        + f"; {len(features) - sum(zoning_counts.values())} parcels left unzoned.",
        f"Future land use: Gainesville FLU_2022 on {flu_gainesville} parcels; county HC_FLU_2024 on {flu_county}; {len(features) - flu_gainesville - flu_county} with no future land use.",
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
    download_hall_county({"name": "Hall", "fips": "13139", "state": "Georgia"}, ["Atlanta"], hall_spec())
