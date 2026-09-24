"""Carroll County, Georgia (FIPS 13045) 5–150 GIS-acre extract.

The live GMASS parcel FeatureServer is blocked. Countywide geometry and parcel
ids come from the OpenAddresses job 910028 snapshot (pid + polygon only).
GIS acres are the equirectangular area of those polygons. Carrollton CITY_PARCEL,
ZONING, and FUTURE_LAND_USE join on parcel id. Villa Rica zoning, future land
use, and the Carroll-side parcel extract join only when the id is already on
this Carroll landbase, so Douglas-side Villa Rica rows stay out.

County Euclidean zoning and future land use are PDF-only gaps. Sales are the
commercial/industrial ExportFeatures subset. Temple, Bremen, Mount Zion,
Bowdon, Whitesburg, and Roopville have no public zoning service. Opportunity
Zone fields stay empty. Carroll County, Maryland and Carroll County, Ohio are
not used, and neither is ARC LandPro.
"""

from __future__ import annotations

import gzip
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import seed_market_parcels as seed
from parcel_geometry import representative_point, ring_signed_m2

SQM_PER_ACRE = 4046.8564224
FIPS = "13045"
SOURCE = "oa-carroll-ga-910028"
OA_PARCELS = "https://v2.openaddresses.io/batch-prod/job/910028/source.geojson.gz"
OA_ADDRESSES = "https://v2.openaddresses.io/batch-prod/job/910027/source.geojson.gz"
CARROLLTON_PARCELS = "https://services1.arcgis.com/T9kPZugHsZ2SNOXt/arcgis/rest/services/CITY_PARCEL/FeatureServer/0/query"
CARROLLTON_ZONING = "https://services1.arcgis.com/T9kPZugHsZ2SNOXt/arcgis/rest/services/ZONING/FeatureServer/0/query"
CARROLLTON_FLU = "https://services1.arcgis.com/T9kPZugHsZ2SNOXt/arcgis/rest/services/FUTURE_LAND_USE/FeatureServer/0/query"
VILLA_RICA_ZONING = "https://services2.arcgis.com/dW3WG2w9z33TTLpl/arcgis/rest/services/Map/FeatureServer/0/query"
VILLA_RICA_FLU = "https://services2.arcgis.com/dW3WG2w9z33TTLpl/arcgis/rest/services/Map/FeatureServer/3/query"
VILLA_RICA_PARCELS = "https://services2.arcgis.com/dW3WG2w9z33TTLpl/arcgis/rest/services/Map/FeatureServer/1/query"
SALES_URL = "https://services.arcgis.com/ISpzx3B5ZsVA6e1Z/ArcGIS/rest/services/Carroll_Sales_ExportFeatures/FeatureServer/0/query"
APPRAISER_SEARCH = "https://qpublic.schneidercorp.com/Application.aspx?AppID=663&LayerID=15076&PageTypeID=1"
APPRAISER_REPORT = "https://qpublic.schneidercorp.com/Application.aspx?AppID=663&LayerID=15076&PageTypeID=4&KeyValue="
# OpenAddresses harvest bounds for Carroll County, Georgia. Not Carroll MD/OH.
CARROLL_BOX = (-85.338, 33.426, -84.810, 33.812)
CACHE = Path("/tmp/dls-carroll")


def carroll_spec() -> dict:
    return {
        "kind": "carroll",
        "source": SOURCE,
        "url": OA_PARCELS,
        "coverage": "complete-gte-5ac",
    }


def norm_id(value: Any) -> str | None:
    text = seed.clean(value)
    if not text:
        return None
    return " ".join(text.split())


def id_keys(value: Any) -> list[str]:
    text = norm_id(value)
    if not text:
        return []
    collapsed = "".join(text.split())
    keys = [text]
    if collapsed != text:
        keys.append(collapsed)
    return keys


def geojson_acres(geometry: dict | None) -> float:
    if not geometry:
        return 0.0
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    polygons = [coords] if kind == "Polygon" else coords if kind == "MultiPolygon" else []
    net = 0.0
    for poly in polygons:
        if not poly:
            continue
        for index, ring in enumerate(poly):
            raw = [[float(x), float(y)] for x, y in ring]
            if len(raw) < 4:
                continue
            if raw[0] != raw[-1]:
                raw.append(raw[0])
            signed = abs(ring_signed_m2(raw))
            net += signed if index == 0 else -signed
    return max(0.0, net) / SQM_PER_ACRE


def in_carroll_ga(lon: float, lat: float) -> bool:
    west, south, east, north = CARROLL_BOX
    return west <= lon <= east and south <= lat <= north


def simplify_geometry(geometry: dict) -> dict:
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        return {"type": "Polygon", "coordinates": [seed.simplify_ring(ring) for ring in coords if len(ring) >= 4]}
    if kind == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [[seed.simplify_ring(ring) for ring in poly if len(ring) >= 4] for poly in coords],
        }
    raise RuntimeError(f"Unsupported geometry {kind}")


def point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_feature(x: float, y: float, feature: dict) -> bool:
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        rings = geom.get("coordinates") or []
        if not rings or not point_in_ring(x, y, rings[0]):
            return False
        return not any(point_in_ring(x, y, hole) for hole in rings[1:])
    if geom.get("type") == "MultiPolygon":
        for poly in geom.get("coordinates") or []:
            if poly and point_in_ring(x, y, poly[0]) and not any(point_in_ring(x, y, hole) for hole in poly[1:]):
                return True
    return False


class GridIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)

    def add(self, feature: dict) -> None:
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates") or []
        points = []
        if geom.get("type") == "Polygon":
            points = coords[0] if coords else []
        elif geom.get("type") == "MultiPolygon":
            points = [pt for poly in coords for pt in (poly[0] if poly else [])]
        if not points:
            return
        xs = [float(p[0]) for p in points]
        ys = [float(p[1]) for p in points]
        ix0, ix1 = int(min(xs) // self.cell), int(max(xs) // self.cell)
        iy0, iy1 = int(min(ys) // self.cell), int(max(ys) // self.cell)
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        for feature in self.buckets.get((int(x // self.cell), int(y // self.cell)), []):
            if point_in_feature(x, y, feature):
                return feature
        return None


def download_gzip(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"  cache {dest.name}", flush=True)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  download {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/market-parcels"})
    with urllib.request.urlopen(req, timeout=180) as resp, dest.open("wb") as handle:
        handle.write(resp.read())


def iter_ndjson_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line in {"[", "]"}:
                continue
            if line.endswith(","):
                line = line[:-1]
            if line.startswith("{") and '"type"' in line:
                yield json.loads(line)


def fetch_layer(name: str, url: str, fields: list[str], *, geometry: bool) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{name}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        print(f"  cache {name} {len(cached)}", flush=True)
        return cached
    rows: list[dict] = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "outSR": "4326",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": 2000,
        }
        data = seed.fetch_json(url, params, timeout=180)
        if data.get("error"):
            raise RuntimeError(f"{name}: {json.dumps(data['error'])[:300]}")
        batch = data.get("features") or []
        rows.extend(batch)
        print(f"  {name} {len(rows)}", flush=True)
        if not batch or (not data.get("exceededTransferLimit") and len(batch) < 2000):
            break
        offset += len(batch)
    path.write_text(json.dumps(rows))
    return rows


def index_attrs(rows: list[dict], field: str) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        attrs = row.get("attributes") or {}
        for key in id_keys(attrs.get(field)):
            indexed.setdefault(key, attrs)
    return indexed


def lookup_attr(index: dict[str, dict], parcel_id: str) -> dict | None:
    for key in id_keys(parcel_id):
        found = index.get(key)
        if found:
            return found
    return None


def sale_date(value: Any) -> str | None:
    number = seed.num(value)
    if number is None:
        return None
    if number > 10_000_000_000:
        number = number / 1000.0
    if number < 1_000_000_000:
        return None
    return datetime.fromtimestamp(number, tz=timezone.utc).date().isoformat()


def join_name(attrs: dict, *fields: str) -> str | None:
    parts = [seed.clean(attrs.get(field)) for field in fields]
    text = " ".join(part for part in parts if part)
    return text or None


def load_landbase() -> tuple[dict[str, dict], dict]:
    raw_path = CACHE / "oa-910028.geojson.gz"
    download_gzip(OA_PARCELS, raw_path)
    grouped: dict[str, list[dict]] = defaultdict(list)
    source_rows = 0
    outside = 0
    blank = 0
    for feature in iter_ndjson_gz(raw_path):
        source_rows += 1
        props = feature.get("properties") or {}
        parcel_id = norm_id(props.get("pid"))
        geometry = feature.get("geometry")
        if not parcel_id or not geometry:
            blank += 1
            continue
        center = representative_point(geometry)
        if not center or not in_carroll_ga(center[0], center[1]):
            outside += 1
            continue
        grouped[parcel_id].append({"geometry": geometry, "acres": geojson_acres(geometry)})
    kept: dict[str, dict] = {}
    below = 0
    above = 0
    duplicate_groups = 0
    for parcel_id, parts in grouped.items():
        if len(parts) > 1:
            duplicate_groups += 1
        acres = sum(part["acres"] for part in parts)
        if acres < seed.MIN_ACRES:
            below += 1
            continue
        if acres > seed.MAX_ACRES:
            above += 1
            continue
        if len(parts) == 1:
            geometry = parts[0]["geometry"]
        else:
            polygons = []
            for part in parts:
                geom = part["geometry"]
                if geom.get("type") == "Polygon":
                    polygons.append(geom["coordinates"])
                elif geom.get("type") == "MultiPolygon":
                    polygons.extend(geom["coordinates"])
            geometry = {"type": "MultiPolygon", "coordinates": polygons}
        geometry = simplify_geometry(geometry)
        center = representative_point(geometry)
        if not center or not in_carroll_ga(center[0], center[1]):
            outside += 1
            continue
        kept[parcel_id] = {"acres": acres, "geometry": geometry, "center": center}
    stats = {
        "sourceRows": source_rows,
        "blankPid": blank,
        "outsideCarrollGa": outside,
        "duplicateGroups": duplicate_groups,
        "belowBand": below,
        "aboveBand": above,
        "kept": len(kept),
    }
    print(f"  landbase {stats}", flush=True)
    return kept, stats


def address_situs(kept_features: dict[str, dict]) -> dict[str, str]:
    path = CACHE / "oa-910027.geojson.gz"
    download_gzip(OA_ADDRESSES, path)
    index = GridIndex()
    for parcel_id, item in kept_features.items():
        index.add({"id": parcel_id, "geometry": item["geometry"]})
    found: dict[str, str] = {}
    for feature in iter_ndjson_gz(path):
        geom = feature.get("geometry") or {}
        if geom.get("type") != "Point":
            continue
        lon, lat = geom.get("coordinates") or [None, None]
        if lon is None or not in_carroll_ga(float(lon), float(lat)):
            continue
        hit = index.hit(float(lon), float(lat))
        if not hit or hit["id"] in found:
            continue
        props = feature.get("properties") or {}
        number = seed.clean(props.get("number"))
        street = seed.clean(props.get("street"))
        line = " ".join(part for part in (number, street) if part)
        if line:
            found[hit["id"]] = line
    print(f"  address points joined {len(found)}", flush=True)
    return found


def build_features(county: dict, markets: list[str]) -> tuple[list[dict], dict, list[str]]:
    kept, stats = load_landbase()
    carrollton = index_attrs(
        fetch_layer(
            "carrollton-parcels",
            CARROLLTON_PARCELS,
            [
                "Parcel_no",
                "LASTNAME",
                "FIRSTNAME",
                "MIDDLE",
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
                "CURR_VAL",
                "LEGAL_DESC",
            ],
            geometry=False,
        ),
        "Parcel_no",
    )
    carrollton_zoning = index_attrs(
        fetch_layer("carrollton-zoning", CARROLLTON_ZONING, ["Parcel_no", "Zoning"], geometry=False),
        "Parcel_no",
    )
    carrollton_flu = index_attrs(
        fetch_layer("carrollton-flu", CARROLLTON_FLU, ["pin", "F2023FLU"], geometry=False),
        "pin",
    )
    villa_zoning = index_attrs(
        fetch_layer("villa-rica-zoning", VILLA_RICA_ZONING, ["PIN", "Proposed_Z"], geometry=False),
        "PIN",
    )
    villa_parcels = index_attrs(
        fetch_layer(
            "villa-rica-parcels",
            VILLA_RICA_PARCELS,
            ["Parcel_no", "Address", "LASTNAME", "CURR_VAL"],
            geometry=False,
        ),
        "Parcel_no",
    )
    sales = index_attrs(
        fetch_layer(
            "carroll-sales",
            SALES_URL,
            ["Parcel_no", "Sale_Date", "Sale_Price", "QUALIFIER", "Class"],
            geometry=False,
        ),
        "Parcel_no",
    )
    flu_rows = fetch_layer("villa-rica-flu", VILLA_RICA_FLU, ["District"], geometry=True)
    flu_index = GridIndex(cell=0.05)
    for row in flu_rows:
        attrs = row.get("attributes") or {}
        district = seed.clean(attrs.get("District"))
        geom = row.get("geometry")
        if not district or not geom or not geom.get("rings"):
            continue
        from parcel_geometry import esri_rings_to_geojson

        geometry = esri_rings_to_geojson(geom["rings"])
        if geometry:
            flu_index.add({"geometry": geometry, "district": district})

    situs_by_id = address_situs(kept)
    features: list[dict] = []
    counts = {
        "carrolltonCama": 0,
        "villaRicaCama": 0,
        "ownerFilled": 0,
        "marketValueFilled": 0,
        "carrolltonZoning": 0,
        "villaRicaZoning": 0,
        "zoningUnmatched": 0,
        "carrolltonFlu": 0,
        "villaRicaFlu": 0,
        "fluUnmatched": 0,
        "commercialSales": 0,
        "situsFromAddresses": 0,
        "situsFromCity": 0,
    }
    for parcel_id, item in kept.items():
        city = lookup_attr(carrollton, parcel_id)
        villa = lookup_attr(villa_parcels, parcel_id)
        owner = None
        mail1 = mail2 = mail_city = mail_state = mail_zip = None
        situs = None
        zip_code = None
        market_value = None
        if city:
            counts["carrolltonCama"] += 1
            owner = join_name(city, "LASTNAME", "FIRSTNAME", "MIDDLE")
            mail1 = seed.clean(city.get("ADDRESS1"))
            mail2 = seed.clean(city.get("ADDRESS2"))
            extra = seed.clean(city.get("ADDRESS3"))
            if extra:
                mail2 = " ".join(part for part in (mail2, extra) if part)
            mail_city = seed.clean(city.get("CITY"))
            mail_state = seed.clean(city.get("STATE"))
            mail_zip = seed.zip_str(city.get("ZIP_1"))
            situs = join_name(city, "HOUSE_NO", "STDIRECT", "STREET_NAM", "STTYPE", "UNIT")
            zip_code = seed.zip_str(city.get("ZIP"))
            market_value = seed.num(city.get("CURR_VAL"))
        elif villa:
            counts["villaRicaCama"] += 1
            owner = seed.clean(villa.get("LASTNAME"))
            situs = seed.clean(villa.get("Address"))
            market_value = seed.num(villa.get("CURR_VAL"))
        if situs:
            counts["situsFromCity"] += 1
        elif parcel_id in situs_by_id:
            situs = situs_by_id[parcel_id]
            counts["situsFromAddresses"] += 1
        if owner:
            counts["ownerFilled"] += 1
        if market_value is not None and market_value > 0:
            counts["marketValueFilled"] += 1
        else:
            market_value = None

        zoning = None
        prefix = None
        city_zone = lookup_attr(carrollton_zoning, parcel_id)
        villa_zone = lookup_attr(villa_zoning, parcel_id)
        if city and city_zone and seed.clean(city_zone.get("Zoning")):
            zoning = seed.clean(city_zone.get("Zoning"))
            prefix = "CARROLLTON"
            counts["carrolltonZoning"] += 1
        elif villa_zone and seed.clean(villa_zone.get("Proposed_Z")) and (villa or not city):
            zoning = seed.clean(villa_zone.get("Proposed_Z"))
            prefix = "VILLARICA"
            counts["villaRicaZoning"] += 1
        else:
            counts["zoningUnmatched"] += 1

        flu = None
        city_flu = lookup_attr(carrollton_flu, parcel_id)
        flu_code = seed.clean(city_flu.get("F2023FLU")) if city_flu else None
        if city and flu_code:
            flu = {
                "code": flu_code,
                "label": flu_code,
                "jurisdiction": "Carrollton",
                "source": "carrollton-future-land-use",
            }
            counts["carrolltonFlu"] += 1
        else:
            hit = flu_index.hit(item["center"][0], item["center"][1])
            district = seed.clean(hit.get("district")) if hit else None
            if district and (villa or prefix == "VILLARICA"):
                flu = {
                    "code": district,
                    "label": district,
                    "jurisdiction": "Villa Rica",
                    "source": "villa-rica-map-3",
                }
                counts["villaRicaFlu"] += 1
            else:
                counts["fluUnmatched"] += 1

        sale = lookup_attr(sales, parcel_id)
        sale_price = seed.num(sale.get("Sale_Price")) if sale else None
        sale_when = sale_date(sale.get("Sale_Date")) if sale else None
        qualifier = seed.clean(sale.get("QUALIFIER")) if sale else None
        if sale_price is None or sale_price <= 0:
            sale_price = None
        if sale_price is None and not sale_when:
            qualifier = None
        else:
            counts["commercialSales"] += 1

        feature = seed.empty_feature(
            fips=FIPS,
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=item["acres"],
            geometry=item["geometry"],
            center=item["center"],
            source=SOURCE,
            owner=owner,
            situs=situs,
            zip_code=zip_code,
            zoning=zoning,
            sale_price=sale_price,
            sale_date=sale_when,
            sale_qualified=qualifier,
            market_value=market_value,
            mail1=mail1,
            mail2=mail2,
            mail_city=mail_city,
            mail_state=mail_state,
            mail_zip=mail_zip,
        )
        feature["properties"]["jurisdictionPrefix"] = prefix
        feature["properties"]["flu"] = flu
        feature["properties"]["appraiserUrl"] = APPRAISER_REPORT + urllib.parse.quote(parcel_id)
        feature["properties"]["opportunityZone"] = None
        feature["properties"]["oz2Eligibility"] = None
        gaps = []
        if not zoning:
            gaps.append("No Carrollton or Carroll-side Villa Rica zoning polygon matched.")
        if flu is None:
            gaps.append("County future land use is a PDF. No Carrollton or Villa Rica FLU polygon matched.")
        if not owner:
            gaps.append("No countywide CAMA. Owner is filled only from Carrollton or the Villa Rica Carroll extract.")
        if sale_price is None and not sale_when:
            gaps.append("No residential sale. Carroll_Sales_ExportFeatures is a commercial/industrial subset.")
        feature["properties"]["dataGaps"] = gaps
        features.append(feature)
    stats.update(counts)
    notes = gap_lines(stats)
    return features, stats, notes


def gap_lines(stats: dict) -> list[str]:
    return [
        (
            f"Kept {stats['kept']} Carroll County, Georgia parcels in the inclusive 5–150 GIS-acre band "
            f"from OpenAddresses job 910028 ({stats['sourceRows']} polygons, pid only). "
            f"The live Carroll_Parcels_20240923_ExportFeatures service is blocked. "
            f"GIS acres are equirectangular polygon area. Duplicate pid groups: {stats['duplicateGroups']}. "
            f"Below 5 acres: {stats['belowBand']}. Above 150 acres: {stats['aboveBand']}."
        ),
        (
            f"Carrollton CITY_PARCEL matched {stats['carrolltonCama']} kept parcels. "
            f"Villa Rica Map/1 Carroll extract matched {stats['villaRicaCama']}. "
            f"Owner filled {stats['ownerFilled']}. Current value filled {stats['marketValueFilled']}. "
            "There is no countywide owner, mailing, or tax roll on the OpenAddresses snapshot. "
            "Assessed value, taxable value, and tax amount were not on the public layers used here."
        ),
        (
            f"City zoning joined Carrollton {stats['carrolltonZoning']} and Villa Rica Proposed_Z "
            f"{stats['villaRicaZoning']}; unmatched {stats['zoningUnmatched']}. "
            "Villa Rica is clipped to parcel ids on this Carroll landbase so Douglas-side rows are excluded. "
            "County Euclidean zoning is the 2025 PDF only. "
            "Temple, Bremen, Mount Zion, Bowdon, Whitesburg, and Roopville have no public zoning service."
        ),
        (
            f"Future land use joined Carrollton F2023FLU {stats['carrolltonFlu']} and Villa Rica districts "
            f"{stats['villaRicaFlu']}; unmatched {stats['fluUnmatched']}. "
            "County future land use is the 2023 PDF only. FAXNUMBER was not collected."
        ),
        (
            f"Sales joined from Carroll_Sales_ExportFeatures for {stats['commercialSales']} kept parcels. "
            "That layer is a commercial/industrial subset, not residential sales history. "
            f"Soft situs from OpenAddresses address points: {stats['situsFromAddresses']}. "
            f"City situs: {stats['situsFromCity']}."
        ),
        (
            "Opportunity Zone and OZ 2.0 were not assigned. "
            "Rejected Carroll County, Maryland, Carroll County, Ohio, Carrollton Texas, Carrollton Kentucky, "
            "and ARC LandPro. This extract is Carroll County, Georgia (FIPS 13045)."
        ),
    ]


def download_carroll_county(county: dict, markets: list[str], spec: dict) -> dict:
    if county["fips"] != FIPS:
        raise RuntimeError(f"Carroll loader called for {county['fips']}")
    features, stats, gaps = build_features(county, markets)
    path, lookup, tiles = seed.write_tiles(county, features)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=spec["coverage"],
        partition="tiles",
        path=path,
        lookup=lookup,
        source=SOURCE,
        query_url=OA_PARCELS,
        gaps=gaps,
        source_count=stats["sourceRows"],
        dropped=stats["sourceRows"] - len(features),
        tile_count=tiles,
        extra={"stats": stats, "appraiserSearchUrl": APPRAISER_SEARCH},
    )


def main() -> None:
    catalog = json.loads(seed.CATALOG_PATH.read_text())
    county = next(item for market in catalog["markets"] for item in market["counties"] if item["fips"] == FIPS)
    download_carroll_county(county, ["Atlanta"], carroll_spec())
    seed.rebuild_indexes(catalog)


if __name__ == "__main__":
    main()
