"""Spalding County, Georgia public parcel spec and county zoning join.

Landbase is Parcels_Public_View (PARCEL_ID and JURISDICTION only). Acres are
GIS area in Georgia West State Plane feet. County zoning covers unincorporated
Spalding only. Griffin stays unzoned. FLU, sales, tax, and Opportunity Zone
fields stay null. University of Maryland / Regrid and ARC LandPro are not used.
"""

from __future__ import annotations

import math
from collections import defaultdict

from parcel_geometry import esri_rings_to_geojson, ga_west_ft_to_wgs84, geometry_contains, polygon_parts, signed_area


def spalding_spec() -> dict:
    return {
        "kind": "arcgis",
        "url": "https://services5.arcgis.com/IBG8fFojdkoiHAvQ/arcgis/rest/services/Parcels_Public_View/FeatureServer/1/query",
        "where": "1=1",
        "outFields": ["PARCEL_ID", "JURISDICTION"],
        "idField": "PARCEL_ID",
        "computeAcres": True,
        "planarFeet": "ga-west",
        "outSR": 102667,
        "paged": True,
        "pageSize": 2000,
        "jurisdictionField": "JURISDICTION",
        "zoningOverlay": {
            "url": "https://services5.arcgis.com/IBG8fFojdkoiHAvQ/arcgis/rest/services/Spalding_County_Zoning_(public_view)/FeatureServer/0/query",
            "labelField": "LABEL",
        },
        "source": "ga-spalding-parcels-public",
        "coverage": "complete-gte-5ac",
        "gaps": [
            "Spalding County Parcels public view is PARCEL_ID and JURISDICTION only. Owner, mailing, situs, tax, and last sale are null on this extract.",
            "GIS acres are computed from State Plane Georgia West feet (102667/2240) polygon area / 43560. Band is 5.0–150.0 inclusive.",
            "County zoning LABEL is joined only where JURISDICTION is COUNTY (unincorporated Spalding, including Orchard Hill and former Sunny Side). JURISDICTION CITY is Griffin and is left unzoned: the county zoning layer does not cover Griffin, and no verified Griffin zoning FeatureServer was used.",
            "Future land use is the Comp Plan 2042 PDF only. FLU is null.",
            "Sales and tax are qPublic AppID=766 HTML only and were not scraped. Last sale and tax values are null.",
            "Sunny Side's charter was repealed effective 2024-01-01. It is not treated as an incorporated municipality.",
            "Rejected substitutes were not used: University of Maryland Regrid ga_spalding extract and ARC LandPro.",
        ],
    }


def assert_ga_west_projection() -> None:
    lon, lat = ga_west_ft_to_wgs84(2268729.57984738, 1208629.65336716)
    if abs(lon + 84.2578550320386) > 1e-6 or abs(lat - 33.3226976969319) > 1e-6:
        raise RuntimeError(f"Georgia West projection drifted to {lon}, {lat}")


def _polygon_area(geometry: dict) -> float:
    area = 0.0
    for poly in polygon_parts(geometry):
        if poly and poly[0]:
            area += abs(signed_area(poly[0]))
    return area


def join_zoning_overlay(features: list[dict], overlay: dict) -> tuple[list[str], dict]:
    """Spatial-join county zoning. Griffin (JURISDICTION=CITY) stays unzoned."""
    import seed_market_parcels as seed

    print(f"  zoning overlay {overlay['url']}", flush=True)
    raw = seed.fetch_paged(overlay["url"], "1=1", [overlay["labelField"]], 4326, 2000)
    prepared: list[tuple] = []
    for item in raw:
        attrs = item.get("attributes") or {}
        label = seed.clean(attrs.get(overlay["labelField"]))
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        if not label or not geometry:
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
        prepared.append((min(xs), min(ys), max(xs), max(ys), _polygon_area(geometry), label, geometry))
    cell = 0.02
    grid: dict[tuple[int, int], list] = defaultdict(list)
    for item in prepared:
        west, south, east, north = item[:4]
        for ix in range(math.floor(west / cell), math.floor(east / cell) + 1):
            for iy in range(math.floor(south / cell), math.floor(north / cell) + 1):
                grid[(ix, iy)].append(item)
    zoned = 0
    city_null = 0
    county_miss = 0
    other_null = 0
    for feature in features:
        jurisdiction = (feature.pop("_jurisdiction", None) or "").strip().upper()
        props = feature["properties"]
        props["zoningCode"] = None
        props["zoningDistrict"] = None
        props["flu"] = None
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        if jurisdiction == "CITY":
            city_null += 1
            continue
        if jurisdiction != "COUNTY":
            other_null += 1
            continue
        lon, lat = props["centroid"]
        hits: list[tuple[float, str]] = []
        for item in grid.get((math.floor(lon / cell), math.floor(lat / cell)), []):
            west, south, east, north, area, label, geometry = item
            if lon < west or lon > east or lat < south or lat > north:
                continue
            if geometry_contains(geometry, lon, lat):
                hits.append((area, label))
        if not hits:
            county_miss += 1
            continue
        hits.sort()
        props["zoningCode"] = hits[0][1]
        zoned += 1
    print(
        f"  zoning county {zoned} griffin-null {city_null} county-miss {county_miss} other-null {other_null}",
        flush=True,
    )
    stats = {"zoned": zoned, "cityNull": city_null, "countyMiss": county_miss, "otherNull": other_null}
    note = (
        f"County zoning labels joined on {zoned} JURISDICTION=COUNTY parcels. "
        f"{city_null} Griffin CITY parcels in the acreage band were left unzoned. "
        f"{county_miss} COUNTY parcels had no county zoning intersect."
    )
    return [note], stats


def assert_spalding_extract(features: list[dict], stats: dict) -> None:
    count = len(features)
    if not 3500 <= count <= 4200:
        raise RuntimeError(f"Spalding 5–150 acre count {count} is outside the expected GIS band")
    if stats["cityNull"] < 50:
        raise RuntimeError(f"Expected Griffin CITY parcels in band, saw {stats['cityNull']}")
    if stats["zoned"] < 1000:
        raise RuntimeError(f"County zoning join kept only {stats['zoned']} parcels")
    if stats["otherNull"]:
        raise RuntimeError(f"Unexpected jurisdiction values on {stats['otherNull']} parcels")
    pins = {feature["properties"]["parcelId"]: feature for feature in features}
    county_pin = pins.get("244 02001B")
    if county_pin is None:
        raise RuntimeError("Geo pin 244 02001B missing from the 5–150 acre extract")
    lon, lat = county_pin["properties"]["centroid"]
    if not (-84.28 < lon < -84.23 and 33.30 < lat < 33.35):
        raise RuntimeError(f"Geo pin 244 02001B drifted to {lon}, {lat}")
    if not county_pin["properties"].get("zoningCode"):
        raise RuntimeError("County pin 244 02001B was left unzoned")
    for parcel_id in ("001 01001", "039 01003", "039 01004"):
        city = pins.get(parcel_id)
        if city is None:
            raise RuntimeError(f"Griffin pin {parcel_id} missing from the 5–150 acre extract")
        if city["properties"].get("zoningCode"):
            raise RuntimeError(f"Griffin pin {parcel_id} received county zoning {city['properties']['zoningCode']}")
    for feature in features:
        props = feature["properties"]
        if not str(props["id"]).startswith("13255:"):
            raise RuntimeError(f"Parcel id {props['id']} is missing the 13255 GEOID prefix")
        if props.get("countyFips") != "13255":
            raise RuntimeError(f"Parcel {props['id']} countyFips is {props.get('countyFips')}")
        if props.get("flu") is not None or props.get("opportunityZone") is not None or props.get("oz2Eligibility") is not None:
            raise RuntimeError(f"Parcel {props['id']} invented FLU or an Opportunity Zone")
        tax = props.get("tax") or {}
        sale = props.get("lastSale") or {}
        if tax.get("marketValue") is not None or tax.get("assessedValue") is not None or tax.get("taxableValue") is not None:
            raise RuntimeError(f"Parcel {props['id']} has tax values on a thin CAMA layer")
        if sale.get("price") is not None or sale.get("date") is not None:
            raise RuntimeError(f"Parcel {props['id']} has a sale on a layer with no sale history")
        if props.get("ownerName") or props.get("situsAddress") or props.get("situsCity"):
            raise RuntimeError(f"Parcel {props['id']} invented owner or situs")
        if "_jurisdiction" in feature:
            raise RuntimeError(f"Parcel {props['id']} leaked JURISDICTION onto the feature")
