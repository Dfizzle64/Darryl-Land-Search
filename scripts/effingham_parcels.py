"""Effingham County, Georgia (FIPS 13103) 5–150 acre extract for Savannah.

Preferred geometry is Parcels2024. Sale price and market value are joined from
ParcelUpdate, then the 2024-09-03 FLUM, because Parcels2024 has a sale date and
no sale price. Effingham County, Illinois is not used. Opportunity Zone fields
are not assigned.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import seed_market_parcels as seed
from parcel_geometry import contains_point, esri_rings_to_geojson

FIPS = "13103"
SOURCE = "ga-effingham-parcels-2024"
PARCELS = "https://services.arcgis.com/9scQWTgPOi3GxJRr/arcgis/rest/services/Parcels2024/FeatureServer/0/query"
PARCEL_UPDATE = "https://services.arcgis.com/9scQWTgPOi3GxJRr/arcgis/rest/services/ParcelUpdate/FeatureServer/0/query"
FLUM = "https://services.arcgis.com/9scQWTgPOi3GxJRr/arcgis/rest/services/FLUM_20240903_BOC_APPR_2/FeatureServer/0/query"
MUNICIPAL = "https://services.arcgis.com/9scQWTgPOi3GxJRr/arcgis/rest/services/County_Municipal_Boundaries/FeatureServer/0/query"
APPRAISER_SEARCH = "https://qpublic.schneidercorp.com/Application.aspx?App=EffinghamCountyGA&Layer=Parcels&PageType=Search"
APPRAISER_REPORT = (
    "https://qpublic.schneidercorp.com/Application.aspx?AppID=666&LayerID=11348&PageTypeID=4&PageID=4716&KeyValue="
)
# Effingham County, Georgia, northwest of Savannah. Not Effingham County, Illinois (~-88.5, 39).
EFFINGHAM_BOX = (-81.60, 31.95, -81.00, 32.60)
OUT_FIELDS = [
    "PARCEL_NO",
    "PIN",
    "LASTNAME",
    "TOTALACRES",
    "StreetAdd",
    "SalesDate",
    "address1",
    "address2",
    "city",
    "state",
    "zip",
    "esttax",
    "ZCODE",
    "TAXDISTRIC",
    "DIGCLASS",
    "OverlayDis",
]


def effingham_spec() -> dict:
    return {
        "kind": "effingham",
        "source": SOURCE,
        "url": PARCELS,
        "coverage": "complete-gte-5ac",
    }


def _epoch_to_iso(value: Any) -> str | None:
    parsed = seed.num(value)
    if parsed is None or parsed <= 0:
        return None
    seconds = parsed / 1000 if parsed > 10_000_000_000 else parsed
    if seconds < 0 or seconds > 4_102_444_800:
        return None
    try:
        text = time.strftime("%Y-%m-%d", time.gmtime(seconds))
    except (OverflowError, OSError, ValueError):
        return None
    year = int(text[:4])
    if year < 1950 or year > 2035:
        return None
    return text


def _positive(value: Any) -> float | None:
    parsed = seed.num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _situs(value: Any) -> str | None:
    text = seed.clean(value)
    if not text:
        return None
    if text.startswith("0 "):
        text = text[2:].strip()
    return text or None


def _paged_attributes(url: str, where: str, fields: list[str], page: int) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    order = "OBJECTID"
    while True:
        params = {
            "where": where,
            "outFields": ",".join(fields),
            "returnGeometry": "false",
            "resultOffset": str(offset),
            "resultRecordCount": str(page),
            "f": "json",
        }
        if order:
            params["orderByFields"] = order
        data = seed.fetch_json(url, params, timeout=180)
        if data.get("error") and order:
            order = ""
            continue
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        batch = data.get("features") or []
        rows.extend(batch)
        print(f"    {url.rsplit('/', 2)[-2]} {len(rows)}", flush=True)
        if not batch or (not data.get("exceededTransferLimit") and len(batch) < page):
            break
        offset += len(batch)
    return rows


def _cities() -> list[dict]:
    data = seed.fetch_json(
        MUNICIPAL,
        {"where": "1=1", "outFields": "NAME", "returnGeometry": "true", "outSR": "4326", "f": "json"},
        timeout=120,
    )
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    rows = []
    for feature in data.get("features") or []:
        geometry = esri_rings_to_geojson((feature.get("geometry") or {}).get("rings") or [])
        name = seed.clean((feature.get("attributes") or {}).get("NAME"))
        if geometry and name:
            rows.append({"name": name.title(), "geometry": geometry})
    return rows


def _money_from(*values: Any) -> float | None:
    for value in values:
        parsed = _positive(value)
        if parsed is not None:
            return parsed
    return None


def download_effingham(county: dict, markets: list[str], spec: dict) -> dict:
    if county["fips"] != FIPS:
        raise RuntimeError(f"Effingham ingest is Census FIPS {FIPS}, not {county['fips']}")
    where = "TOTALACRES>=5 AND TOTALACRES<=150"
    print(f"Pulling Effingham County GA ({FIPS})", flush=True)
    ids = seed.fetch_object_ids(PARCELS, where)
    raw = seed.fetch_by_ids(PARCELS, ids, OUT_FIELDS, batch=100)
    print("  joining ParcelUpdate and FLUM attributes", flush=True)
    updates = _paged_attributes(
        PARCEL_UPDATE,
        "1=1",
        ["PARCEL_NO", "SALEPRICE", "CURR_VAL", "fmvres", "fmvcom", "fmvacc", "SalesDate"],
        1000,
    )
    flum_rows = _paged_attributes(FLUM, "1=1", ["PARCEL_NO", "EFF_REV2", "SALEPRICE", "CURR_VAL"], 2000)
    cities = _cities()
    update_by_id: dict[str, dict] = {}
    for feature in updates:
        attrs = feature.get("attributes") or {}
        parcel_id = seed.clean(attrs.get("PARCEL_NO"))
        if parcel_id:
            update_by_id[parcel_id] = attrs
    flum_by_id: dict[str, dict] = {}
    for feature in flum_rows:
        attrs = feature.get("attributes") or {}
        parcel_id = seed.clean(attrs.get("PARCEL_NO"))
        if parcel_id:
            flum_by_id[parcel_id] = attrs
    by_id: dict[str, dict] = {}
    dropped_geom = 0
    dropped_box = 0
    dropped_band = 0
    duplicate_groups = 0
    zoning_joined = 0
    flu_joined = 0
    price_joined = 0
    date_filled = 0
    market_filled = 0
    city_hits = {"Rincon": 0, "Guyton": 0, "Springfield": 0}
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
        if not (EFFINGHAM_BOX[0] <= lon <= EFFINGHAM_BOX[2] and EFFINGHAM_BOX[1] <= lat <= EFFINGHAM_BOX[3]):
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
        update = update_by_id.get(parcel_id) or {}
        flum = flum_by_id.get(parcel_id) or {}
        sale_price = _money_from(update.get("SALEPRICE"), flum.get("SALEPRICE"))
        market_value = _money_from(update.get("CURR_VAL"), flum.get("CURR_VAL"))
        if market_value is None:
            parts = [_positive(update.get(key)) for key in ("fmvres", "fmvcom", "fmvacc")]
            present = [part for part in parts if part is not None]
            if present:
                market_value = round(sum(present), 2)
        sale_on = _epoch_to_iso(attrs.get("SalesDate")) or _epoch_to_iso(update.get("SalesDate"))
        taxes = _positive(attrs.get("esttax"))
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
            situs=_situs(attrs.get("StreetAdd")),
            zoning=seed.clean(attrs.get("ZCODE")),
            dor=seed.clean(attrs.get("DIGCLASS")),
            sale_price=sale_price,
            sale_date=sale_on,
            market_value=market_value,
            mail1=seed.clean(attrs.get("address1")),
            mail2=seed.clean(attrs.get("address2")),
            mail_city=seed.clean(attrs.get("city")),
            mail_state=seed.clean(attrs.get("state")),
            mail_zip=seed.zip_str(attrs.get("zip")),
        )
        props = feature["properties"]
        props["appraiserUrl"] = APPRAISER_REPORT + parcel_id
        if taxes is not None:
            props["tax"]["taxes"] = taxes
        overlay = seed.clean(attrs.get("OverlayDis"))
        if overlay:
            props["zoningOverlay"] = overlay
        flu_label = seed.clean(flum.get("EFF_REV2"))
        if flu_label:
            props["flu"] = {
                "code": flu_label,
                "label": flu_label,
                "jurisdiction": "Effingham County",
                "source": "effingham-flum-20240903",
            }
            flu_joined += 1
        for city in cities:
            if contains_point(city["geometry"], lon, lat):
                props["situsCity"] = city["name"]
                props["jurisdictionPrefix"] = city["name"]
                city_hits[city["name"]] = city_hits.get(city["name"], 0) + 1
                break
        if props["zoningCode"]:
            zoning_joined += 1
        if sale_price:
            price_joined += 1
        if sale_on:
            date_filled += 1
        if market_value:
            market_filled += 1
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
        raise RuntimeError("Effingham extract kept zero parcels")
    if any(not seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Effingham extract emitted a parcel outside 5–150 acres")
    if dropped_box:
        raise RuntimeError(f"Effingham extract rejected {dropped_box} centroids outside Effingham County, Georgia")
    zoning_joined = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_joined = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    price_joined = sum(1 for feature in features if feature["properties"]["lastSale"].get("price"))
    date_filled = sum(1 for feature in features if feature["properties"]["lastSale"].get("date"))
    market_filled = sum(1 for feature in features if feature["properties"]["tax"].get("marketValue"))
    city_hits = {"Rincon": 0, "Guyton": 0, "Springfield": 0}
    for feature in features:
        city = feature["properties"].get("situsCity")
        if city in city_hits:
            city_hits[city] += 1
    path, lookup, tiles = seed.write_tiles(county, features)
    gaps = [
        f"Kept {len(features)} Effingham County, Georgia parcels in the inclusive 5–150 acre band from Parcels2024 ({len(ids)} source rows). TOTALACRES is the acreage field.",
        "Parcels2024 has SalesDate and no SALEPRICE or CURR_VAL. lastSale.price and tax.marketValue are joined from ParcelUpdate on PARCEL_NO, then from FLUM_20240903_BOC_APPR_2 when ParcelUpdate has no positive value. Newer parcels can miss that join.",
        "REASON is on Parcels2024 and is not a documented sale-quality flag, so lastSale.qualified stays null. There is no multi-sale history on the REST layer.",
        "No assessed or taxable value is on the public REST layers. esttax is stored as tax.taxes when it is positive. tax.assessedValue and tax.taxableValue stay null.",
        "Zoning is parcel-attributed ZCODE. No separate Euclidean zoning polygon service was found. Rincon, Guyton, and Springfield zoning maps are PDF or county ZCODE; no city zoning FeatureServer was used.",
        "Future land use is EFF_REV2 on FLUM_20240903_BOC_APPR_2 joined by PARCEL_NO. That layer has fewer polygons than Parcels2024, so some parcels have no FLU.",
        "Situs city is a spatial hit on County_Municipal_Boundaries (Rincon, Guyton, Springfield). The parcel city field is owner mailing and is not a municipality filter. Meldrim has no city polygon.",
        "Rejected Effingham County, Illinois, SAGIS/Chatham ParcelDigest, and paid parcel vendors. Opportunity Zone and OZ 2.0 fields were not assigned.",
    ]
    stats = {
        "sourceRows": len(ids),
        "kept": len(features),
        "duplicateGroups": duplicate_groups,
        "droppedGeometry": dropped_geom,
        "droppedOutsideEffinghamGa": dropped_box,
        "droppedBand": dropped_band,
        "zoningJoined": zoning_joined,
        "fluJoined": flu_joined,
        "salePriceJoined": price_joined,
        "saleDateFilled": date_filled,
        "marketValueFilled": market_filled,
        "rincon": city_hits.get("Rincon", 0),
        "guyton": city_hits.get("Guyton", 0),
        "springfield": city_hits.get("Springfield", 0),
        "parcelUpdateRows": len(updates),
        "flumRows": len(flum_rows),
        "situsFilled": sum(1 for feature in features if feature["properties"].get("situsAddress")),
    }
    print(f"  kept {len(features)} Effingham parcels {stats}", flush=True)
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
    download_effingham(county, ["Savannah"], effingham_spec())
    seed.rebuild_indexes(catalog)


if __name__ == "__main__":
    main()
