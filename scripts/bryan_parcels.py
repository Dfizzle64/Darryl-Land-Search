"""Bryan County, Georgia (FIPS 13029) 5–150 acre extract for Savannah.

Preferred layer is the county PropertyDetails MapServer. Bryan County, Texas
and Bryan County, Oklahoma are not used. SAGIS is Chatham-only and is not used.
Sales are a Beacon HTML gap. MAVCURR is present and unused. Opportunity Zone
fields are not assigned.
"""

from __future__ import annotations

import json
from pathlib import Path

import seed_market_parcels as seed
from parcel_geometry import contains_point, esri_rings_to_geojson

FIPS = "13029"
SOURCE = "ga-bryan-property-details"
PARCELS = "https://bryangis.bryan-county.org/arcgis/rest/services/PropertyDetails/MapServer/0/query"
FLU = "https://bryangis.bryan-county.org/arcgis/rest/services/2023ComprehensivePlan/MapServer/4/query"
MUNICIPAL = "https://bryangis.bryan-county.org/arcgis/rest/services/MunicipalBoundaries/MapServer/0/query"
APPRAISER_SEARCH = "https://qpublic.net/ga/bryan/"
APPRAISER_REPORT = (
    "https://beacon.schneidercorp.com/Application.aspx?AppID=639&LayerID=11303&PageTypeID=4&KeyValue="
)
# Bryan County, Georgia, southwest of Savannah. Not Bryan TX (~-96) or Bryan OK.
BRYAN_BOX = (-81.80, 31.65, -81.05, 32.30)
ZONING_STUBS = {"CITY"}
OUT_FIELDS = [
    "PARCEL_NO",
    "LASTNAME",
    "ADDRESS1",
    "ADDRESS2",
    "ADDRESS3",
    "CITY",
    "STATE",
    "ZIP_1",
    "HOUSE_NO",
    "STDIRECT",
    "STREET_NAM",
    "STTYPE",
    "UNIT",
    "ZIP",
    "TOTALACRES",
    "CURR_VAL",
    "MAVCURR",
    "ZONINGCODE",
    "TAXDISTRIC",
    "DIGCLASS",
]


def bryan_spec() -> dict:
    return {
        "kind": "bryan",
        "source": SOURCE,
        "url": PARCELS,
        "coverage": "complete-gte-5ac",
    }


def _house(value) -> str | None:
    parsed = seed.num(value)
    if parsed is None or parsed <= 0:
        return None
    return str(int(parsed)) if parsed == int(parsed) else str(parsed)


def _piece(value) -> str | None:
    text = seed.clean(value)
    if not text or text in {"0", "0.0"}:
        return None
    return text


def _situs(attrs: dict) -> str | None:
    parts = [
        _house(attrs.get("HOUSE_NO")),
        _piece(attrs.get("STDIRECT")),
        _piece(attrs.get("STREET_NAM")),
        _piece(attrs.get("STTYPE")),
        _piece(attrs.get("UNIT")),
    ]
    line = " ".join(part for part in parts if part)
    return line or None


def _zoning(value) -> str | None:
    text = seed.clean(value)
    if not text or text.upper() in ZONING_STUBS:
        return None
    return text


def _polygons(url: str, fields: list[str]) -> list[dict]:
    data = seed.fetch_json(
        url,
        {"where": "1=1", "outFields": ",".join(fields), "returnGeometry": "true", "outSR": "4326", "f": "json"},
        timeout=180,
    )
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    rows = []
    for feature in data.get("features") or []:
        geometry = esri_rings_to_geojson((feature.get("geometry") or {}).get("rings") or [])
        if not geometry:
            continue
        rows.append({"attributes": feature.get("attributes") or {}, "geometry": geometry})
    return rows


def _hit(rows: list[dict], lon: float, lat: float) -> dict | None:
    found = None
    for row in rows:
        if contains_point(row["geometry"], lon, lat):
            found = row
            break
    return found


def download_bryan(county: dict, markets: list[str], spec: dict) -> dict:
    if county["fips"] != FIPS:
        raise RuntimeError(f"Bryan ingest is Census FIPS {FIPS}, not {county['fips']}")
    where = "TOTALACRES>=5 AND TOTALACRES<=150"
    print(f"Pulling Bryan County GA ({FIPS})", flush=True)
    ids = seed.fetch_object_ids(PARCELS, where)
    raw = seed.fetch_by_ids(PARCELS, ids, OUT_FIELDS, batch=80)
    flu_polys = _polygons(FLU, ["LANDUSEDESC", "LANDUSECODE"])
    cities = _polygons(MUNICIPAL, ["NAME"])
    by_id: dict[str, dict] = {}
    dropped_geom = 0
    dropped_box = 0
    dropped_band = 0
    duplicate_groups = 0
    zoning_joined = 0
    zoning_stub = 0
    flu_joined = 0
    city_hits = {"Richmond Hill": 0, "Pembroke": 0}
    market_filled = 0
    situs_filled = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed = seed.rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            dropped_geom += 1
            continue
        center = seed.centroid_of(geometry)
        if not center or not seed.plausible_centroid(center):
            dropped_geom += 1
            continue
        lon, lat = center
        if not (BRYAN_BOX[0] <= lon <= BRYAN_BOX[2] and BRYAN_BOX[1] <= lat <= BRYAN_BOX[3]):
            dropped_box += 1
            continue
        acres = seed.num(attrs.get("TOTALACRES"))
        if not seed.in_band(acres):
            dropped_band += 1
            continue
        parcel_id = seed.clean(attrs.get("PARCEL_NO"))
        if not parcel_id:
            dropped_geom += 1
            continue
        zoning_raw = seed.clean(attrs.get("ZONINGCODE"))
        zoning = _zoning(zoning_raw)
        if zoning_raw and zoning_raw.upper() in ZONING_STUBS:
            zoning_stub += 1
        market_value = seed.num(attrs.get("CURR_VAL"))
        if market_value is not None and market_value <= 0:
            market_value = None
        feature = seed.empty_feature(
            fips=FIPS,
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source=SOURCE,
            owner=seed.clean(attrs.get("LASTNAME")),
            situs=_situs(attrs),
            zip_code=seed.zip_str(attrs.get("ZIP")),
            zoning=zoning,
            dor=seed.clean(attrs.get("DIGCLASS")),
            market_value=market_value,
            mail1=seed.clean(attrs.get("ADDRESS1")),
            mail2=seed.clean(attrs.get("ADDRESS2")) or seed.clean(attrs.get("ADDRESS3")),
            mail_city=seed.clean(attrs.get("CITY")),
            mail_state=seed.clean(attrs.get("STATE")),
            mail_zip=seed.zip_str(attrs.get("ZIP_1")),
        )
        props = feature["properties"]
        props["appraiserUrl"] = APPRAISER_REPORT + parcel_id
        flu = _hit(flu_polys, lon, lat)
        if flu:
            label = seed.clean(flu["attributes"].get("LANDUSEDESC"))
            if label:
                props["flu"] = {
                    "code": label,
                    "label": label,
                    "jurisdiction": "Bryan County",
                    "source": "bryan-2023-comp-plan-flu",
                }
                flu_joined += 1
        city = _hit(cities, lon, lat)
        if city:
            name = seed.clean(city["attributes"].get("NAME"))
            if name:
                titled = name.title()
                props["situsCity"] = titled
                props["jurisdictionPrefix"] = titled
                city_hits[titled] = city_hits.get(titled, 0) + 1
        if zoning:
            zoning_joined += 1
        if market_value:
            market_filled += 1
        if props["situsAddress"]:
            situs_filled += 1
        previous = by_id.get(parcel_id)
        if previous is None:
            by_id[parcel_id] = feature
        else:
            duplicate_groups += 1
            if (props["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
                by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    if not features:
        raise RuntimeError("Bryan extract kept zero parcels")
    if any(not seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Bryan extract emitted a parcel outside 5–150 acres")
    if dropped_box:
        raise RuntimeError(f"Bryan extract rejected {dropped_box} centroids outside Bryan County, Georgia")
    zoning_joined = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_joined = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    market_filled = sum(1 for feature in features if feature["properties"]["tax"].get("marketValue"))
    situs_filled = sum(1 for feature in features if feature["properties"].get("situsAddress"))
    city_hits = {"Richmond Hill": 0, "Pembroke": 0}
    for feature in features:
        city = feature["properties"].get("situsCity")
        if city in city_hits:
            city_hits[city] += 1
    path, lookup, tiles = seed.write_tiles(county, features)
    gaps = [
        f"Kept {len(features)} Bryan County, Georgia parcels in the inclusive 5–150 acre band from PropertyDetails MapServer/0 ({len(ids)} source rows, {duplicate_groups} extra parts with the same PARCEL_NO collapsed). TOTALACRES is the deeded acreage field.",
        "Owner mailing CITY/STATE/ADDRESS2 are nationwide mailing addresses and are not a municipality filter. Situs city is the MunicipalBoundaries spatial hit (Richmond Hill or Pembroke) only.",
        "ZONINGCODE is the parcel zoning string, including city-style codes. The value CITY is a stub and is not stored. County Zoning/0 is dissolved UDO polygons and was not preferred over the parcel code.",
        "Future land use is a centroid join to 2023ComprehensivePlan MapServer/4 LANDUSEDESC. Richmond Hill and Pembroke have no city future-land-use FeatureServer.",
        "No public REST sale price or sale date. Beacon/qPublic AppID=639 LayerID=11303 sales search is HTML only and was not scraped. HISTYR/HISTVAL are assessment years, not sales.",
        "MAVCURR and the other MAV assessed fields are on the layer and were not used because the live assessed values are empty. tax.marketValue is CURR_VAL when it is positive. Assessed and taxable values stay null.",
        "PropertyDetails does not support pagination. Rows were read by object id. The stale Parcels/MapServer URL and the thinner Evolve parcel layer were not used.",
        "Rejected Bryan County, Texas, Bryan County, Oklahoma, and SAGIS (Chatham-only). Opportunity Zone and OZ 2.0 fields were not assigned.",
    ]
    stats = {
        "sourceRows": len(ids),
        "kept": len(features),
        "duplicateGroups": duplicate_groups,
        "droppedGeometry": dropped_geom,
        "droppedOutsideBryanGa": dropped_box,
        "droppedBand": dropped_band,
        "zoningJoined": zoning_joined,
        "zoningStubCity": zoning_stub,
        "fluJoined": flu_joined,
        "marketValueFilled": market_filled,
        "situsFilled": situs_filled,
        "richmondHill": city_hits.get("Richmond Hill", 0),
        "pembroke": city_hits.get("Pembroke", 0),
    }
    print(f"  kept {len(features)} Bryan parcels {stats}", flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=SOURCE,
        query_url=PARCELS,
        gaps=gaps,
        source_count=len(ids),
        dropped=len(ids) - len(features),
        tile_count=tiles,
        extra={"stats": stats, "appraiserSearchUrl": APPRAISER_SEARCH},
    )


def main() -> None:
    catalog = json.loads((Path(__file__).resolve().parents[1] / "data" / "market-parcel-counties.json").read_text())
    county = next(
        county
        for market in catalog["markets"]
        if market["id"] == "Savannah"
        for county in market["counties"]
        if county["fips"] == FIPS
    )
    download_bryan(county, ["Savannah"], bryan_spec())
    seed.rebuild_indexes(catalog)


if __name__ == "__main__":
    main()
