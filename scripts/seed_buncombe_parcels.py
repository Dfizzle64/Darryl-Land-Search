#!/usr/bin/env python3
"""Buncombe County (FIPS 37021) 5–150 acre parcels for the Asheville market.

Wire-first source is county opendata Property FeatureServer/1. NC OneMap
gisacres is 0 for this county and is not used for the acreage filter.

  python3 scripts/seed_buncombe_parcels.py
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

from parcel_geometry import esri_rings_to_geojson, polygon_parts, signed_area
from parcel_geometry import _inside_polygon
from seed_market_parcels import (
    COUNTY_DIR,
    MAX_ACRES,
    MIN_ACRES,
    OUT_DIR,
    centroid_of,
    clean,
    county_row,
    empty_feature,
    fetch_json,
    in_band,
    plausible_centroid,
    rings_to_feature_geometry,
    write_tiles,
    zip_str,
)

NC_EXCISE_RATE = 0.002
SOURCE = "nc-buncombe-opendata-37021"
PARCEL_URL = "https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/1"
PROPCARD = "https://prc-buncombe.spatialest.com/#/property/"
CACHE = Path("/tmp/dls-buncombe")

MUNICIPALITIES = {
    "CAS": "Asheville",
    "CBF": "Biltmore Forest",
    "CBM": "Black Mountain",
    "CMT": "Montreat",
    "CWO": "Woodfin",
    "CWV": "Weaverville",
}

CITY_ORDER = ["CAS", "CWV", "CBM", "CWO", "CMT", "CBF", ""]

PARCEL_FIELDS = [
    "PIN",
    "Acreage",
    "Owner",
    "Address",
    "CityName",
    "State",
    "Zipcode",
    "CareOf",
    "HouseNumber",
    "NumberSuffix",
    "StreetPrefix",
    "StreetName",
    "StreetType",
    "StreetPostDirection",
    "DeedDate",
    "SalePrice",
    "Stamps",
    "TotalMarketValue",
    "AppraisedValue",
    "TaxValue",
    "LandValue",
    "BuildingValue",
    "City",
    "Class",
    "PropCard",
]

ZONING_LAYERS = {
    "county": {
        "url": "https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/5",
        "field": "ZoningCode",
    },
    "asheville": {
        "url": "https://gis.ashevillenc.gov/server/rest/services/Districts/ZoningDistricts/FeatureServer/11",
        "field": "districts",
        "overlay": "overlay_type",
    },
    "weaverville": {
        "url": "https://services5.arcgis.com/lA7fMEY4qaPiZF6g/arcgis/rest/services/Zoning_ForApp/FeatureServer/0",
        "field": "Code",
    },
    "blackMountain": {
        "url": "https://gis.buncombecounty.org/arcgis/rest/services/bcmapimage2_B/MapServer/31",
        "field": "ZoneCode",
    },
    "woodfin": {
        "url": "https://gis.buncombecounty.org/arcgis/rest/services/bcmapimage2_B/MapServer/30",
        "field": "ZoneCode",
    },
    "montreat": {
        "url": "https://gis.buncombecounty.org/arcgis/rest/services/Montreat_Map/FeatureServer/0",
        "field": "Zoning",
    },
}

FLU_LAYERS = {
    "asheville": {
        "url": "https://gis.ashevillenc.gov/server/rest/services/Planning/FutureLandUseOverlay/FeatureServer/67",
        "field": "commtype",
        "source": "asheville-future-land-use",
        "jurisdiction": "ASHEVILLE",
    },
    "gec": {
        "url": "https://gis.buncombecounty.org/arcgis/rest/services/bcmap_vt/MapServer/57",
        "field": "Name",
        "source": "buncombe-growth-equity-conservation",
        "jurisdiction": "BUNCOMBE",
    },
}

ASHEVILLE_PARCEL_ZONING = "https://gis.ashevillenc.gov/server/rest/services/Planning/PropertyZoningCategories/FeatureServer/79"


def cast_money(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def parse_deed_date(value) -> str | None:
    text = "" if value is None else str(value).strip()
    if len(text) != 8 or not text.isdigit():
        return None
    year = int(text[0:4])
    month = int(text[4:6])
    day = int(text[6:8])
    if year < 1900 or year > 2100 or month < 1 or month > 12 or day < 1 or day > 31:
        return None
    return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"


def compose_situs(attrs: dict) -> str | None:
    def piece(key: str) -> str | None:
        return clean(attrs.get(key))

    number = piece("HouseNumber")
    suffix = piece("NumberSuffix")
    house = None
    if number and suffix:
        house = f"{number}{suffix}" if len(suffix) == 1 else f"{number} {suffix}"
    else:
        house = number
    street = " ".join(
        part
        for part in [piece("StreetPrefix"), piece("StreetName"), piece("StreetType"), piece("StreetPostDirection")]
        if part
    )
    line = " ".join(part for part in [house, street] if part)
    return line or None


def trusted_sale_price(sale_price, stamps, land_value, market_value):
    price = sale_price
    if price is None or not math.isfinite(price) or price <= 0:
        return None
    stamp = stamps if stamps is not None and math.isfinite(stamps) else 0
    land = land_value if land_value is not None and math.isfinite(land_value) and land_value > 0 else 0
    market = market_value if market_value is not None and math.isfinite(market_value) and market_value > 0 else 0
    if stamp > 0:
        implied = stamp / NC_EXCISE_RATE
        ratio = price / implied if implied else 0
        if 0.75 <= ratio <= 1.25:
            return price
        return None
    if price < 25000:
        return None
    anchor_low = land if land > 0 else market
    anchor_high = market if market > 0 else land
    if anchor_low <= 0 and anchor_high <= 0:
        return price
    if price < 0.2 * anchor_low or price > 4 * anchor_high:
        return None
    return price


def propcard(pin: str, raw) -> str:
    expected = f"{PROPCARD}{pin}"
    text = clean(raw)
    if text and text.startswith(PROPCARD) and pin in text:
        return text
    return expected


def self_test() -> None:
    assert trusted_sale_price(0, 0, 100000, 100000) is None
    assert trusted_sale_price(1100, 4000, 359700, 776900) is None
    assert trusted_sale_price(2700, 0, 33300, 348000) is None
    assert trusted_sale_price(21700, 0, 218400, 709000) is None
    assert trusted_sale_price(632100, 70921, 1951300, 42101600) is None
    assert trusted_sale_price(200000, 400, 150000, 250000) == 200000
    assert trusted_sale_price(370100, 0, 489200, 859300) == 370100
    assert trusted_sale_price(5450500, 0, 4274900, 16723400) == 5450500
    assert compose_situs(
        {
            "HouseNumber": "438",
            "NumberSuffix": "",
            "StreetPrefix": "",
            "StreetName": "SANDY MUSH CREEK",
            "StreetType": "RD",
            "StreetPostDirection": "",
        }
    ) == "438 SANDY MUSH CREEK RD"
    assert parse_deed_date("20250626") == "2025-06-26"
    assert cast_money("348000") == 348000
    assert propcard("963470749800000", "https://example.com/x") == f"{PROPCARD}963470749800000"


def query_url(layer_url: str) -> str:
    return layer_url if layer_url.endswith("/query") else layer_url.rstrip("/") + "/query"


def fetch_layer(url: str, where: str, fields: list[str], geometry: bool, order_by: str | None = None) -> list[dict]:
    features: list[dict] = []
    offset = 0
    page = 200 if geometry else 2000
    while True:
        params = {
            "where": where,
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "resultOffset": str(offset),
            "resultRecordCount": str(page),
            "f": "json",
        }
        if order_by:
            params["orderByFields"] = order_by
        if geometry:
            params["outSR"] = "4326"
        data = fetch_json(query_url(url), params, timeout=240)
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:400])
        batch = data.get("features") or []
        features.extend(batch)
        print(f"    {url.rsplit('/', 1)[-1]} {len(features)}", flush=True)
        if not batch or not data.get("exceededTransferLimit"):
            break
        offset += len(batch)
        time.sleep(0.05)
    return features


def cached_layer(name: str, url: str, where: str, fields: list[str], geometry: bool, order_by: str | None = None) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{name}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        if cached.get("where") == where and cached.get("features"):
            print(f"  cache {name} {len(cached['features'])}", flush=True)
            return cached["features"]
    print(f"  fetch {name}", flush=True)
    features = fetch_layer(url, where, fields, geometry, order_by)
    path.write_text(json.dumps({"where": where, "features": features}))
    return features


def geom_bbox(geometry: dict) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for poly in polygon_parts(geometry):
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def zone_area(geometry: dict) -> float:
    parts = polygon_parts(geometry)
    if not parts or not parts[0]:
        return 0.0
    return abs(signed_area(parts[0][0]))


def point_in_geom(lon: float, lat: float, geometry: dict) -> bool:
    return any(_inside_polygon(lon, lat, poly) for poly in polygon_parts(geometry))


def prepare_zones(features: list[dict], field: str, overlay_field: str | None = None) -> list[dict]:
    zones = []
    for item in features:
        attrs = item.get("attributes") or {}
        code = clean(attrs.get(field))
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        if not code or not geometry:
            continue
        overlay_raw = clean(attrs.get(overlay_field)) if overlay_field else None
        zones.append(
            {
                "code": code,
                "geometry": geometry,
                "bbox": geom_bbox(geometry),
                "area": zone_area(geometry),
                "overlay": bool(overlay_raw),
            }
        )
    return zones


def assign_zone(lon: float, lat: float, zones: list[dict]) -> str | None:
    hits = []
    for zone in zones:
        minx, miny, maxx, maxy = zone["bbox"]
        if lon < minx or lon > maxx or lat < miny or lat > maxy:
            continue
        if point_in_geom(lon, lat, zone["geometry"]):
            hits.append(zone)
    if not hits:
        return None
    base = [zone for zone in hits if not zone["overlay"]]
    pool = base or hits
    pool.sort(key=lambda zone: zone["area"])
    return pool[0]["code"]


def assign_flu(lon: float, lat: float, zones: list[dict], source: str, jurisdiction: str) -> dict | None:
    code = assign_zone(lon, lat, zones)
    if not code:
        return None
    return {"code": code, "label": code, "jurisdiction": jurisdiction, "source": source}


def load_reference_layers() -> dict:
    zones = {}
    for key, spec in ZONING_LAYERS.items():
        fields = [spec["field"]]
        if spec.get("overlay"):
            fields.append(spec["overlay"])
        raw = cached_layer(f"zone-{key}", spec["url"], "1=1", fields, True)
        zones[key] = prepare_zones(raw, spec["field"], spec.get("overlay"))
        print(f"  zones {key} {len(zones[key])}", flush=True)
    flu = {}
    for key, spec in FLU_LAYERS.items():
        raw = cached_layer(f"flu-{key}", spec["url"], "1=1", [spec["field"]], True)
        flu[key] = prepare_zones(raw, spec["field"])
        print(f"  flu {key} {len(flu[key])}", flush=True)
    zoning_rows = cached_layer(
        "asheville-pin-zoning",
        ASHEVILLE_PARCEL_ZONING,
        "tax_acreage >= 5 AND tax_acreage <= 150",
        ["pinnum", "districts"],
        False,
    )
    by_pin = {}
    for item in zoning_rows:
        attrs = item.get("attributes") or {}
        pin = clean(attrs.get("pinnum"))
        code = clean(attrs.get("districts"))
        if pin and code:
            by_pin[pin] = code
    print(f"  asheville pin zoning {len(by_pin)}", flush=True)
    return {"zones": zones, "flu": flu, "ashevillePins": by_pin}


def parcel_gaps(city: str, zoning: str | None, flu: dict | None) -> list[str]:
    gaps = []
    if city == "CBF":
        gaps.append("Biltmore Forest zoning is PDF-only. No public zoning REST, so zoning is left blank.")
    elif not zoning:
        gaps.append("No zoning polygon matched this parcel on the public layer for its municipality.")
    if city == "CAS" and not flu:
        gaps.append("Asheville Future Land Use overlay did not cover this parcel.")
    elif city in {"CWV", "CBM", "CWO", "CMT", "CBF"}:
        gaps.append("No public future-land-use REST for this municipality.")
    return gaps


def build_features(raw: list[dict], county: dict, markets: list[str], layers: dict) -> tuple[list[dict], dict]:
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed = rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            dropped += 1
            continue
        center = centroid_of(geometry)
        if not plausible_centroid(center):
            dropped += 1
            continue
        acres = cast_money(attrs.get("Acreage"))
        if not in_band(acres):
            dropped += 1
            continue
        pin = clean(attrs.get("PIN"))
        if not pin:
            dropped += 1
            continue
        city = clean(attrs.get("City")) or ""
        if city not in MUNICIPALITIES and city != "":
            city = ""
        land = cast_money(attrs.get("LandValue"))
        market_value = cast_money(attrs.get("TotalMarketValue"))
        price_raw = cast_money(attrs.get("SalePrice"))
        stamps = cast_money(attrs.get("Stamps"))
        price = trusted_sale_price(price_raw, stamps, land, market_value)
        lon, lat = center
        zoning = None
        flu = None
        if city == "CAS":
            zoning = layers["ashevillePins"].get(pin) or assign_zone(lon, lat, layers["zones"]["asheville"])
            flu = assign_flu(lon, lat, layers["flu"]["asheville"], "asheville-future-land-use", "ASHEVILLE")
        elif city == "CWV":
            zoning = assign_zone(lon, lat, layers["zones"]["weaverville"])
        elif city == "CBM":
            zoning = assign_zone(lon, lat, layers["zones"]["blackMountain"])
        elif city == "CWO":
            zoning = assign_zone(lon, lat, layers["zones"]["woodfin"])
        elif city == "CMT":
            zoning = assign_zone(lon, lat, layers["zones"]["montreat"])
        elif city == "CBF":
            zoning = None
            flu = None
        elif city == "":
            zoning = assign_zone(lon, lat, layers["zones"]["county"])
            flu = assign_flu(lon, lat, layers["flu"]["gec"], "buncombe-growth-equity-conservation", "BUNCOMBE")
        feature = empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=pin,
            acreage=acres,
            geometry=geometry,
            center=center,
            source=SOURCE,
            owner=clean(attrs.get("Owner")),
            situs=compose_situs(attrs),
            city=MUNICIPALITIES.get(city),
            zip_code=None,
            zoning=zoning,
            dor=clean(attrs.get("Class")),
            sale_price=price,
            sale_date=parse_deed_date(attrs.get("DeedDate")),
            market_value=market_value,
            assessed=cast_money(attrs.get("AppraisedValue")),
            taxable=cast_money(attrs.get("TaxValue")),
            mail1=clean(attrs.get("Address")),
            mail2=clean(attrs.get("CareOf")),
            mail_city=clean(attrs.get("CityName")),
            mail_state=clean(attrs.get("State")),
            mail_zip=zip_str(attrs.get("Zipcode")),
        )
        props = feature["properties"]
        props["jurisdictionCode"] = city or "UNINC"
        props["jurisdictionPrefix"] = city or "UNINC"
        props["flu"] = flu
        props["appraiserUrl"] = propcard(pin, attrs.get("PropCard"))
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        gaps = parcel_gaps(city, zoning, flu)
        if gaps:
            props["dataGaps"] = gaps
        feature["_saleNonZero"] = bool(price_raw is not None and price_raw > 0)
        previous = by_id.get(pin)
        if previous is None or (props["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[pin] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    counts = {
        code: {"parcels": 0, "zoning": 0, "flu": 0}
        for code in CITY_ORDER
    }
    sale_nonzero = 0
    sale_trusted = 0
    for feature in features:
        props = feature["properties"]
        code = props.get("jurisdictionCode") or "UNINC"
        code = "" if code == "UNINC" else code
        if code not in counts:
            counts[code] = {"parcels": 0, "zoning": 0, "flu": 0}
        counts[code]["parcels"] += 1
        if props.get("zoningCode"):
            counts[code]["zoning"] += 1
        if props.get("flu"):
            counts[code]["flu"] += 1
        if feature.pop("_saleNonZero", False):
            sale_nonzero += 1
        if props["lastSale"]["price"] is not None:
            sale_trusted += 1
    by_city = {}
    for code in CITY_ORDER:
        row = counts[code]
        name = MUNICIPALITIES.get(code, "Unincorporated")
        entry = {
            "code": code or "UNINC",
            "parcels": row["parcels"],
            "zoning": row["zoning"],
            "flu": row["flu"],
            "zoningRate": round(row["zoning"] / row["parcels"], 4) if row["parcels"] else 0,
            "fluRate": round(row["flu"] / row["parcels"], 4) if row["parcels"] else 0,
        }
        if code == "CBF":
            entry["zoningGap"] = "pdf-only"
        by_city[name] = entry
    stats = {
        "kept": len(features),
        "dropped": dropped,
        "sourceRows": len(raw),
        "sale": {
            "nonZeroSource": sale_nonzero,
            "trusted": sale_trusted,
            "nulledUntrusted": sale_nonzero - sale_trusted,
        },
        "byCity": by_city,
    }
    return features, stats


def gap_notes(stats: dict) -> list[str]:
    cities = stats["byCity"]
    sale = stats["sale"]
    collapsed = stats["sourceRows"] - stats["kept"]
    lines = [
        "Biltmore Forest zoning is PDF-only (biltmoreforest.org planning maps). City CBF parcels stay blank. County zoning is not applied inside the town.",
        (
            f"SalePrice was non-zero on {sale['nonZeroSource']} parcels and kept on {sale['trusted']}. "
            "A price is kept only when it is within 25% of excise stamps divided by 0.002, or when stamps are 0, "
            "the price is at least $25,000, and it sits between 20% of land value and 4× total market value. "
            "Other SalePrice values are null. DeedDate is still stored. Prices are not reconstructed from stamps."
        ),
        "Asheville zoning is the city Property Zoning Categories pin join, with ZoningDistricts as a spatial fallback. Asheville FLU is FutureLandUseOverlay commtype.",
        "Weaverville zoning is town AGOL Zoning_ForApp. Black Mountain, Woodfin, and Montreat use the county-hosted town layers. Those four towns have no public FLU REST.",
        "Unincorporated zoning is county opendata FeatureServer/5 only. Unincorporated FLU is the Growth, Equity and Conservation place category, not a municipal future land use map.",
        "NC OneMap gisacres is 0 for Buncombe. Acreage is the county Property field, inclusive 5 through 150.",
    ]
    if collapsed:
        lines.append(
            f"{stats['sourceRows']} source rows in the acreage band collapsed to {stats['kept']} parcel IDs. "
            "PIN 967680537500000 is published four times with the same acreage; one record is kept."
        )
    asheville = cities["Asheville"]
    if asheville["parcels"] != asheville["zoning"]:
        lines.append(
            f"Asheville zoning matched {asheville['zoning']} of {asheville['parcels']}. "
            "The rest have a blank district on Property Zoning Categories and the parcel point misses ZoningDistricts, so no code was guessed."
        )
    for name, row in cities.items():
        lines.append(
            f"{name}: {row['parcels']} parcels, zoning {row['zoning']} ({row['zoningRate']:.1%}), FLU {row['flu']} ({row['fluRate']:.1%})."
        )
    return lines


def write_market_meta(row: dict) -> None:
    meta = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "market": "Asheville",
        "tier": "other",
        "parcelCount": row["featureCount"],
        "coreMinAcres": MIN_ACRES,
        "coreMaxAcres": MAX_ACRES,
        "tile": {"originLon": -83.0, "originLat": 27.0, "tileDeg": 0.25},
        "notes": [
            "Loaded only when Asheville is selected.",
            "Buncombe parcels come from county opendata Property, not NC OneMap.",
            "Zoning is cities-first. County zoning applies only where City is blank.",
            "Biltmore Forest zoning is a documented PDF gap.",
            "No opportunity zone designation is joined. Eligible is not designated.",
        ],
        "counties": [
            {
                "name": row["name"],
                "fips": row["fips"],
                "state": row["state"],
                "featureCount": row["featureCount"],
                "coverage": row["coverage"],
                "partition": row["partition"],
                "minAcres": MIN_ACRES,
                "maxAcres": MAX_ACRES,
                "source": row["source"],
                "queryUrl": row["queryUrl"],
                "gaps": row["gaps"],
                "path": row["path"],
                "lookup": row["lookup"],
                "tileCount": row["tileCount"],
                "sourceCount": row["sourceCount"],
            }
        ],
    }
    path = OUT_DIR / "markets" / "asheville" / "meta.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2) + "\n")


def patch_index(row: dict) -> None:
    index_path = OUT_DIR / "index.json"
    index = json.loads(index_path.read_text())
    index["markets"]["Asheville"] = {
        "tier": "other",
        "parcelCount": row["featureCount"],
        "completeCountyCount": 1 if row["featureCount"] else 0,
        "sampleCountyCount": 0,
        "gapCountyCount": 0 if row["featureCount"] else 1,
        "path": "data/fixtures/market-parcels/markets/asheville/meta.json",
        "counties": [
            {
                "name": "Buncombe",
                "state": "North Carolina",
                "fips": "37021",
                "featureCount": row["featureCount"],
                "coverage": row["coverage"],
                "minAcres": MIN_ACRES,
                "maxAcres": MAX_ACRES,
                "gaps": (row.get("gaps") or [])[:2],
            }
        ],
    }
    index_path.write_text(json.dumps(index, indent=2) + "\n")


def ingest_buncombe(county: dict, markets: list[str]) -> dict:
    self_test()
    where = f"Acreage >= {MIN_ACRES} AND Acreage <= {MAX_ACRES}"
    raw = cached_layer("parcels", PARCEL_URL, where, PARCEL_FIELDS, True, "PIN")
    layers = load_reference_layers()
    features, stats = build_features(raw, county, markets, layers)
    if not features:
        raise RuntimeError("Buncombe extract kept zero parcels")
    if not all(in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Buncombe extract emitted a parcel outside 5–150 acres")
    path, lookup, tiles = write_tiles(county, features)
    gaps = gap_notes(stats)
    row = county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=SOURCE,
        query_url=query_url(PARCEL_URL),
        gaps=gaps,
        source_count=len(raw),
        dropped=stats["dropped"],
        tile_count=tiles,
    )
    stats_path = COUNTY_DIR / county["fips"] / "join-stats.json"
    stats_path.write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2), flush=True)
    return row


def main() -> None:
    county = {"name": "Buncombe", "state": "North Carolina", "fips": "37021"}
    markets = ["Asheville"]
    row = ingest_buncombe(county, markets)
    write_market_meta(row)
    patch_index(row)
    print(f"kept {row['featureCount']} tiles {row['tileCount']}", flush=True)


if __name__ == "__main__":
    main()
