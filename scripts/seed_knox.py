#!/usr/bin/env python3
"""Knox County parcels plus zoning and future-land-use overlays.

Knox is not a Comptroller IMPACT county. This script never calls maps.cot.tn.gov.
Parcels come from the tokenless KGIS Portal Parcel_Search_Layer proxy.
Direct www.kgis.org/arcgis MapServers stay 401 and are not used.

  python3 scripts/seed_knox.py
  python3 scripts/seed_knox.py --refresh-overlays
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import seed_market_parcels as market  # noqa: E402

OUT = ROOT / "data" / "fixtures" / "knox"
CHECKED = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

PARCEL_QUERY = "https://www.kgis.org/arcgis/rest/services/Maps/GlobalSearch/MapServer/0/query"
PORTAL_QUERY = "https://www.kgis.org/gisportal/sharing/servers/871856067a1243bd899774b2072381c5/rest/services/Parcel_Search_Layer/MapServer/0/query"
PARCEL_WHERE = "CALCULATED_AREA >= 5 AND CALCULATED_AREA <= 150"
KNOX_GAPS = [
    "City of Knoxville future land use (PRLU) and the One Year Plan are not available to anonymous query. FLU stays null inside the city.",
    "Town of Farragut has no public future-land-use FeatureServer. FLU stays null in Farragut.",
    "Direct www.kgis.org/arcgis GlobalSearch and Property MapServers still return HTTP 401. This extract uses the public Parcel_Search_Layer portal proxy. Comptroller IMPACT is not used.",
]
PROPERTY_QUERY = "https://www.kgis.org/arcgis/rest/services/Maps/Property/MapServer/2/query"
PARCEL_EXPORT = "https://www.kgis.org/arcgis/rest/services/Maps/GlobalSearch/MapServer/export?bbox=-84.3,35.7,-83.5,36.3&bboxSR=4326&layers=show:0&f=json"
ZONING_LAYER = "https://services1.arcgis.com/QWaOgwdmpqI9HUzf/arcgis/rest/services/KnoxvilleKnoxCountyZoning/FeatureServer/2"
FLU_LAYER = "https://services1.arcgis.com/QWaOgwdmpqI9HUzf/arcgis/rest/services/Knox_County_Future_Land_Use/FeatureServer/326"
FARRAGUT_LAYER = "https://services6.arcgis.com/Ff4u1o0TAdiPJay7/arcgis/rest/services/Farragut_Zoning/FeatureServer/1"
CITY_LIMITS = "https://services2.arcgis.com/8uN5i97bMkq2Mzrt/arcgis/rest/services/Knoxville_City_Limits/FeatureServer/232"
FARRAGUT_BOUNDARY = "https://services1.arcgis.com/QWaOgwdmpqI9HUzf/arcgis/rest/services/AAS_Farragut_Boundaries/FeatureServer/0"
CITY_FLU = "https://www.kgis.org/gisserver/rest/services/City_Future_Land_Use_TNSP/MapServer?f=pjson"
ONE_YEAR = "https://www.kgis.org/arcgis/rest/services/Maps_Cached/OneYearPlan/MapServer/90?f=pjson"

PARCEL_FIELDS = [
    "OBJECTID",
    "PARCELID",
    "PARCELID_1",
    "BASE_PARCELID",
    "PBAID",
    "OWNER",
    "KGIS_OWNER",
    "ACCELA_OWNER",
    "FULL_ADDRESS",
    "RECORDED_AREA",
    "CALCULATED_AREA",
    "SYS_CALC_AREA",
    "LOC_HOUSE_NUMBER",
    "LOC_HOUSE_NUM_SUF",
    "LOC_STREET_PREFIX",
    "LOC_STREET_NAME",
    "LOC_STREET_TYPE",
    "LOC_STREET_SUFFIX",
    "LOC_UNIT",
    "MAIL_HOUSE_NUMBER",
    "MAIL_UNIT",
    "MAIL_STREET_NAME",
    "MAIL_STREET_EXTRA",
    "MAIL_CITY",
    "MAIL_STATE",
    "MAIL_ZIP_CODE",
    "MAIL_ZIP_CODE_SUF",
    "MAIL_COUNTRY",
    "FULL_MAIL_ADDRESS",
    "FULL_MAIL_ADDRESS_EXTRA",
    "FULL_MAIL_CITY_STATE_ZIP",
    "MAIL_ATTENTION",
    "DATE_PURCHASED",
    "PURCHASE_PRICE",
    "SALE_DATE",
    "VALIDITY_FLAG",
    "ODOC_BOOK",
    "ODOC_PAGE",
    "DEED_BOOK",
    "DEED_PAGE",
    "APPRAISED_LAND",
    "APPRAISED_BLDG",
    "APPRAISED_TOTAL",
    "ASSESSED_TOTAL",
    "LANDUSE",
    "TAX_CLASS",
    "TAX_DISTRICT",
    "PARCEL_TYPE",
    "SUBDIVISION_NAME",
]

USER_AGENT = "darryl-land-search/knox"


def probe(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read(240)
            snippet = body.decode("utf-8", "replace")
            arcgis_error = None
            if '"code": 499' in snippet or "Token Required" in snippet:
                arcgis_error = 499
            return {
                "url": url,
                "status": resp.status,
                "ok": 200 <= resp.status < 300 and arcgis_error is None,
                "arcgisError": arcgis_error,
                "snippet": snippet,
            }
    except urllib.error.HTTPError as exc:
        try:
            snippet = exc.read(240).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            snippet = ""
        return {"url": url, "status": exc.code, "ok": False, "snippet": snippet}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "status": None, "ok": False, "error": str(exc)[:240]}


def clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def zoning_code(zone1, zone2=None) -> str | None:
    primary = clean(zone1)
    secondary = clean(zone2)
    if primary and secondary and secondary != primary:
        if secondary.startswith("/") or secondary.startswith("-"):
            return f"{primary}{secondary}"
        return f"{primary} {secondary}"
    return primary or secondary


def fetch_layer(query_url: str, out_fields: list[str], where: str = "1=1", object_id: str = "OBJECTID") -> list[dict]:
    features: list[dict] = []
    offset = 0
    page = 2000
    while True:
        params = {
            "where": where,
            "outFields": ",".join(out_fields),
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
            "resultOffset": str(offset),
            "resultRecordCount": str(page),
            "orderByFields": object_id,
        }
        data = market.fetch_json(query_url, params, timeout=180)
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:400])
        batch = data.get("features") or []
        features.extend(batch)
        print(f"  {query_url.rsplit('/', 2)[-2]} +{len(batch)} (total {len(features)})", flush=True)
        if not batch or (not data.get("exceededTransferLimit") and len(batch) < page):
            break
        offset += len(batch)
        if offset > 200000:
            break
    return features


def esri_feature(row: dict, properties: dict) -> dict | None:
    geometry, _acres = market.rings_to_feature_geometry(row.get("geometry"))
    if not geometry:
        return None
    return {"type": "Feature", "properties": properties, "geometry": geometry}


def write_collection(name: str, features: list[dict]) -> None:
    path = OUT / name
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")))
    print(f"wrote {path.relative_to(ROOT)} ({len(features)} features, {path.stat().st_size} bytes)", flush=True)


def point_in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi:
            inside = not inside
        j = i
    return inside


def point_in_geometry(lon: float, lat: float, geometry: dict | None) -> bool:
    if not geometry:
        return False
    if geometry["type"] == "Polygon":
        rings = geometry["coordinates"]
        if not rings or not point_in_ring(lon, lat, rings[0]):
            return False
        return all(not point_in_ring(lon, lat, hole) for hole in rings[1:])
    return any(point_in_geometry(lon, lat, {"type": "Polygon", "coordinates": polygon}) for polygon in geometry["coordinates"])


def bbox_of(geometry: dict) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []

    def visit(value) -> None:
        if isinstance(value, list) and value and isinstance(value[0], (int, float)):
            xs.append(float(value[0]))
            ys.append(float(value[1]))
            return
        if isinstance(value, list):
            for child in value:
                visit(child)

    visit(geometry.get("coordinates"))
    if not xs:
        return (0, 0, 0, 0)
    return min(xs), min(ys), max(xs), max(ys)


def containing(lon: float, lat: float, features: list[dict], predicate=None) -> dict | None:
    best = None
    best_area = None
    for feature in features:
        if predicate and not predicate(feature):
            continue
        west, south, east, north = bbox_of(feature["geometry"])
        if lon < west or lon > east or lat < south or lat > north:
            continue
        if not point_in_geometry(lon, lat, feature["geometry"]):
            continue
        area = abs((east - west) * (north - south))
        if best is None or area < best_area:
            best = feature
            best_area = area
    return best


def load_collection(name: str) -> list[dict]:
    return json.loads((OUT / name).read_text())["features"]


def sample_joins(boundaries: dict[str, dict]) -> dict:
    candidates = {
        "downtown": (-83.920739, 35.960638),
        "farragut": (-84.1733, 35.884),
        "unincorporated": (-83.85, 36.1),
    }
    zoning = load_collection("zoning.geojson")
    flu = load_collection("county-flu.geojson")
    farragut = load_collection("farragut-zoning.geojson")
    samples = {}
    for name, (lon, lat) in candidates.items():
        if point_in_geometry(lon, lat, boundaries["farragut"]):
            municipality = "farragut"
        elif point_in_geometry(lon, lat, boundaries["knoxville"]):
            municipality = "knoxville"
        else:
            municipality = "unincorporated"
        zone = None
        place = None
        if municipality == "farragut":
            hit = containing(lon, lat, farragut)
            zone = hit["properties"]["zoningCode"] if hit else None
            zone_type = "Town of Farragut"
        else:
            wanted = "City of Knoxville" if municipality == "knoxville" else "Knox County"
            hit = containing(lon, lat, zoning, lambda feature, wanted=wanted: feature["properties"]["zoneType"] == wanted)
            zone = hit["properties"]["zoningCode"] if hit else None
            zone_type = wanted
            if municipality == "unincorporated":
                flu_hit = containing(lon, lat, flu)
                place = flu_hit["properties"]["placeType"] if flu_hit else None
        samples[name] = {
            "lon": lon,
            "lat": lat,
            "municipality": municipality,
            "zoningCode": zone,
            "zoneType": zone_type,
            "placeType": place,
        }
    return samples


def download_overlays() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    print("zoning", flush=True)
    zoning_rows = fetch_layer(
        f"{ZONING_LAYER}/query",
        ["ZONE1", "ZONE2", "AREA_ACRES", "ZONE_TYPE", "HIGH_DENSITY", "CONDITIONS"],
    )
    zoning = []
    zone_types: set[str] = set()
    city = county = 0
    for row in zoning_rows:
        attrs = row.get("attributes") or {}
        zone_type = clean(attrs.get("ZONE_TYPE"))
        if zone_type:
            zone_types.add(zone_type)
        if zone_type == "City of Knoxville":
            city += 1
        elif zone_type == "Knox County":
            county += 1
        feature = esri_feature(
            row,
            {
                "zone1": clean(attrs.get("ZONE1")),
                "zone2": clean(attrs.get("ZONE2")),
                "zoningCode": zoning_code(attrs.get("ZONE1"), attrs.get("ZONE2")),
                "zoneType": zone_type,
                "areaAcres": market.num(attrs.get("AREA_ACRES")),
                "source": "knoxville-knox-county-zoning",
            },
        )
        if feature:
            zoning.append(feature)
    write_collection("zoning.geojson", zoning)

    print("county FLU", flush=True)
    flu_rows = fetch_layer(f"{FLU_LAYER}/query", ["PLACETYPE", "GPP_COMPATIBILITY"])
    flu = []
    place_types: set[str] = set()
    for row in flu_rows:
        attrs = row.get("attributes") or {}
        place = clean(attrs.get("PLACETYPE"))
        if place:
            place_types.add(place)
        feature = esri_feature(
            row,
            {
                "placeType": place,
                "gppCompatibility": clean(attrs.get("GPP_COMPATIBILITY")),
                "source": "advance-knox",
            },
        )
        if feature:
            flu.append(feature)
    write_collection("county-flu.geojson", flu)

    print("Farragut zoning", flush=True)
    farr_rows = fetch_layer(f"{FARRAGUT_LAYER}/query", ["ZONE", "TYPE", "SOURCE", "CODE_URL", "AREA", "ACRES"])
    farr = []
    acres_band = 0
    for row in farr_rows:
        attrs = row.get("attributes") or {}
        acres = market.num(attrs.get("ACRES"))
        if acres is not None and 5 <= acres <= 150:
            acres_band += 1
        feature = esri_feature(
            row,
            {
                "zone": clean(attrs.get("ZONE")),
                "type": clean(attrs.get("TYPE")),
                "codeUrl": clean(attrs.get("CODE_URL")),
                "acres": acres,
                "zoningCode": zoning_code(attrs.get("ZONE")),
                "source": "farragut-zoning",
            },
        )
        if feature:
            farr.append(feature)
    write_collection("farragut-zoning.geojson", farr)

    print("municipalities", flush=True)
    city_rows = fetch_layer(f"{CITY_LIMITS}/query", ["SOURCE", "ACREAGE"], object_id="OBJECTID")
    farr_boundary_rows = fetch_layer(f"{FARRAGUT_BOUNDARY}/query", ["SOURCE", "ACREAGE"], object_id="OBJECTID")
    boundaries = []
    knoxville_geom = None
    farragut_geom = None
    for row in city_rows:
        feature = esri_feature(
            row,
            {"municipality": "knoxville", "name": "City of Knoxville", "source": "knoxville-city-limits"},
        )
        if feature:
            boundaries.append(feature)
            knoxville_geom = feature["geometry"]
    for row in farr_boundary_rows:
        feature = esri_feature(
            row,
            {"municipality": "farragut", "name": "Town of Farragut", "source": "knox-planning-farragut-boundary"},
        )
        if feature:
            boundaries.append(feature)
            farragut_geom = feature["geometry"]
    write_collection("municipalities.geojson", boundaries)
    if not knoxville_geom or not farragut_geom:
        raise RuntimeError("Municipality boundaries did not download")

    return {
        "zoning": {
            "count": len(zoning),
            "city": city,
            "county": county,
            "zoneTypes": sorted(zone_types),
            "farragutExcluded": "Farragut" not in " ".join(zone_types),
            "queryUrl": f"{ZONING_LAYER}/query",
        },
        "countyFlu": {
            "count": len(flu),
            "placeTypes": sorted(place_types),
            "queryUrl": f"{FLU_LAYER}/query",
        },
        "farragutZoning": {
            "count": len(farr),
            "acres5to150": acres_band,
            "queryUrl": f"{FARRAGUT_LAYER}/query",
        },
        "boundaries": {"knoxville": knoxville_geom, "farragut": farragut_geom},
    }


def access_label(probe: dict) -> str:
    if probe.get("arcgisError") == 499 or "Token Required" in (probe.get("snippet") or ""):
        return f"HTTP {probe.get('status')} with ArcGIS error 499 Token Required"
    return f"HTTP {probe.get('status')}"


def write_docs(summary: dict) -> None:
    zoning = summary["zoning"]
    flu = summary["countyFlu"]
    farr = summary["farragutZoning"]
    parcel = summary["parcel"]
    text = f"""# Knox County parcels, zoning, and future land use

Knox County (FIPS 47093) is in the Knoxville market. It includes the **City of Knoxville**, the **Town of Farragut**, and **unincorporated Knox County**. Knox is **not** a Tennessee Comptroller IMPACT county. This pull does not call `maps.cot.tn.gov`.

Checked {summary["checkedAt"]}.

## Parcels

Countywide parcels are the public KGIS Portal proxy `Parcel_Search_Layer` MapServer layer 0. The extract keeps `CALCULATED_AREA` from 5.0 through 150.0 inclusive ({parcel.get("count", 0):,} polygons kept, {parcel.get("sourceCount", 0):,} returned by that filter). Owner, situs, mailing, sale, appraised land/building/total, and assessed total are on the parcel. `RECORDED_AREA` is stored and is not used to add rows whose calculated acres are null.

Direct `www.kgis.org/arcgis` GlobalSearch query returned **HTTP {parcel.get("globalSearchStatus")}**. Property layer 2 returned **HTTP {parcel.get("propertyStatus")}**. Those hosts are not the extract. Comptroller IMPACT is not used.

Tiles: `data/fixtures/market-parcels/counties/47093/tiles`. Source id `kgis-parcel-search`.

Zoning and future land use are joined at the centroid after resolving Town of Farragut, then City of Knoxville, then unincorporated Knox County. Joined zoning: {parcel.get("zoningJoined", 0):,}. Joined unincorporated place types: {parcel.get("fluJoined", 0):,}.

Appraiser record, when a parcel id exists:

`https://propertyinfo.knoxcountytn.gov/Datalets/Datalet.aspx?ParcelID={{PARCELID}}&UseSearch=yes`

Search fallback: `https://propertyinfo.knoxcountytn.gov/search/CommonSearch.aspx?mode=parid`

## Municipalities

Resolve jurisdiction **before** the zoning or FLU join. Farragut is tested first, then the Knoxville city limits. Everything else is unincorporated. Farragut is not a `ZONE_TYPE` on the city/county zoning layer.

| Municipality | Zoning | Future land use |
| --- | --- | --- |
| City of Knoxville | `KnoxvilleKnoxCountyZoning` where `ZONE_TYPE` is `City of Knoxville`. Code is `ZONE1` plus non-empty `ZONE2`. | Honest gap. KGIS city future land use returned **{summary["cityFlu"]["futureLandUseLabel"]}**. The One Year Plan returned **{summary["cityFlu"]["oneYearPlanLabel"]}**. |
| Town of Farragut | `Farragut_Zoning` field `ZONE` ({farr["count"]} polygons; {farr["acres5to150"]} have `ACRES` from 5 through 150). | Honest gap. No public Farragut future-land-use FeatureServer. |
| Unincorporated Knox County | Same zoning service where `ZONE_TYPE` is `Knox County`. | Advance Knox `PLACETYPE` ({flu["count"]} polygons). Not applied inside the city or Farragut. |

## Overlays on disk

| File | Features | Source |
| --- | ---: | --- |
| `data/fixtures/knox/zoning.geojson` | {zoning["count"]} | {zoning["queryUrl"]} |
| `data/fixtures/knox/county-flu.geojson` | {flu["count"]} | {flu["queryUrl"]} |
| `data/fixtures/knox/farragut-zoning.geojson` | {farr["count"]} | {farr["queryUrl"]} |
| `data/fixtures/knox/municipalities.geojson` | 2 | Knoxville city limits and Farragut boundary |

Zoning `ZONE_TYPE` values: {", ".join(zoning["zoneTypes"])}. City polygons on the service: {zoning["city"]}. County polygons on the service: {zoning["county"]}. Place types: {", ".join(flu["placeTypes"])}.

Service counts include polygons that ring simplification could not keep. A centroid that lands on a right-of-way polygon joins that polygon.

`joinKnoxDesignation` in `src/lib/knox.ts` is the join. It is centroid-in-polygon, keeps the smallest containing polygon, and leaves city and Farragut FLU null.

Refresh:

```bash
npm run seed:knox
```
"""
    (ROOT / "docs" / "knox-parcels.md").write_text(text)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def knox_date(value) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        # Parcel Search dates are ArcGIS epoch milliseconds, including 1990s values below 1e12.
        try:
            parsed = datetime.fromtimestamp(value / 1000.0, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        if parsed.year < 1800 or parsed.year > 2200:
            return None
        return parsed.strftime("%Y-%m-%d")
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return text or None


def money(value):
    return market.num(value)


def sale_price(value):
    parsed = market.num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def mailing(attrs: dict) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    full = clean(attrs.get("FULL_MAIL_ADDRESS"))
    extra = clean(attrs.get("FULL_MAIL_ADDRESS_EXTRA"))
    if full:
        line1 = full
    else:
        parts = [clean(attrs.get(key)) for key in ("MAIL_HOUSE_NUMBER", "MAIL_UNIT", "MAIL_STREET_NAME", "MAIL_STREET_EXTRA")]
        line1 = " ".join(part for part in parts if part) or None
    line2_parts = []
    if extra and extra != full:
        line2_parts.append(extra)
    attention = clean(attrs.get("MAIL_ATTENTION"))
    if attention:
        line2_parts.append(attention)
    city = clean(attrs.get("MAIL_CITY"))
    state = clean(attrs.get("MAIL_STATE"))
    zip_code = clean(attrs.get("MAIL_ZIP_CODE"))
    suffix = clean(attrs.get("MAIL_ZIP_CODE_SUF"))
    if zip_code and suffix and "-" not in zip_code:
        zip_code = f"{zip_code}-{suffix}"
    return line1, ", ".join(line2_parts) or None, city, state, zip_code


def situs(attrs: dict) -> str | None:
    full = clean(attrs.get("FULL_ADDRESS"))
    if full:
        return full
    unit = clean(attrs.get("LOC_UNIT"))
    parts = [
        clean(attrs.get(key))
        for key in (
            "LOC_HOUSE_NUMBER",
            "LOC_HOUSE_NUM_SUF",
            "LOC_STREET_PREFIX",
            "LOC_STREET_NAME",
            "LOC_STREET_TYPE",
            "LOC_STREET_SUFFIX",
        )
    ]
    if unit:
        parts.append(f"Unit {unit}")
    return " ".join(part for part in parts if part) or None


def index_features(features: list[dict], cell: float = 0.05) -> dict:
    buckets: dict[tuple[int, int], list[dict]] = {}
    for feature in features:
        west, south, east, north = bbox_of(feature["geometry"])
        for i in range(int(west // cell), int(east // cell) + 1):
            for j in range(int(south // cell), int(north // cell) + 1):
                buckets.setdefault((i, j), []).append(feature)
    return buckets


def hits_at(buckets: dict, lon: float, lat: float, cell: float = 0.05) -> list[dict]:
    found = []
    for feature in buckets.get((int(lon // cell), int(lat // cell)), []):
        if point_in_geometry(lon, lat, feature["geometry"]):
            found.append(feature)
    return found


def smallest(features: list[dict]) -> dict | None:
    best = None
    best_area = None
    for feature in features:
        west, south, east, north = bbox_of(feature["geometry"])
        area = abs((east - west) * (north - south))
        if best is None or area < best_area:
            best = feature
            best_area = area
    return best


def load_boundaries() -> dict[str, dict]:
    features = load_collection("municipalities.geojson")
    return {
        "knoxville": next(feature["geometry"] for feature in features if feature["properties"]["municipality"] == "knoxville"),
        "farragut": next(feature["geometry"] for feature in features if feature["properties"]["municipality"] == "farragut"),
    }


def join_one(lon: float, lat: float, boundaries: dict, indexes: dict) -> dict:
    if point_in_geometry(lon, lat, boundaries["farragut"]):
        municipality = "farragut"
    elif point_in_geometry(lon, lat, boundaries["knoxville"]):
        municipality = "knoxville"
    else:
        municipality = "unincorporated"
    gaps: list[str] = []
    flu = None
    if municipality == "farragut":
        hit = smallest(hits_at(indexes["farragut"], lon, lat))
        zoning_code = hit["properties"].get("zoningCode") if hit else None
        zoning_district = hit["properties"].get("zone") if hit else None
        if not zoning_code:
            gaps.append("No Farragut zoning polygon contained this parcel centroid.")
        gaps.append("Town of Farragut has no public future-land-use FeatureServer. FLU stays null.")
        prefix, name = "FARRAGUT", "Town of Farragut"
    elif municipality == "knoxville":
        hit = smallest(hits_at(indexes["city"], lon, lat))
        zoning_code = hit["properties"].get("zoningCode") if hit else None
        zoning_district = hit["properties"].get("zone1") if hit else None
        if not zoning_code:
            gaps.append("No City of Knoxville zoning polygon contained this parcel centroid.")
        gaps.append("City of Knoxville future land use (PRLU) and the One Year Plan are not available to anonymous query. FLU stays null inside the city.")
        prefix, name = "KNOX-CITY", "City of Knoxville"
    else:
        hit = smallest(hits_at(indexes["county"], lon, lat))
        zoning_code = hit["properties"].get("zoningCode") if hit else None
        zoning_district = hit["properties"].get("zone1") if hit else None
        if not zoning_code:
            gaps.append("No Knox County zoning polygon contained this parcel centroid.")
        flu_hit = smallest(hits_at(indexes["flu"], lon, lat))
        place = flu_hit["properties"].get("placeType") if flu_hit else None
        if place:
            flu = {
                "code": place,
                "label": place,
                "jurisdiction": "KNOX-COUNTY",
                "source": flu_hit["properties"].get("source") or "advance-knox",
            }
        else:
            gaps.append("No Advance Knox place type contained this parcel centroid.")
        prefix, name = "KNOX-COUNTY", "Unincorporated Knox County"
    return {
        "municipality": municipality,
        "name": name,
        "prefix": prefix,
        "zoningCode": zoning_code,
        "zoningDistrict": zoning_district,
        "flu": flu,
        "dataGaps": gaps,
    }


def download_parcels(boundaries: dict) -> tuple[list[dict], dict]:
    print("parcels", flush=True)
    rows = fetch_layer(PORTAL_QUERY, PARCEL_FIELDS, where=PARCEL_WHERE)
    zoning = load_collection("zoning.geojson")
    indexes = {
        "city": index_features([feature for feature in zoning if feature["properties"].get("zoneType") == "City of Knoxville"]),
        "county": index_features([feature for feature in zoning if feature["properties"].get("zoneType") == "Knox County"]),
        "flu": index_features(load_collection("county-flu.geojson")),
        "farragut": index_features(load_collection("farragut-zoning.geojson")),
    }
    by_id: dict[str, dict] = {}
    dropped = 0
    municipalities = {"knoxville": 0, "farragut": 0, "unincorporated": 0}
    zoning_joined = 0
    flu_joined = 0
    for row in rows:
        attrs = row.get("attributes") or {}
        geometry, _acres = market.rings_to_feature_geometry(row.get("geometry"))
        if not geometry:
            dropped += 1
            continue
        center = market.centroid_of(geometry)
        if not center or not market.plausible_centroid(center):
            dropped += 1
            continue
        acres = market.num(attrs.get("CALCULATED_AREA"))
        if acres is None or acres < 5 or acres > 150:
            dropped += 1
            continue
        parcel_id = clean(attrs.get("PARCELID")) or clean(attrs.get("PARCELID_1"))
        if not parcel_id:
            dropped += 1
            continue
        designation = join_one(center[0], center[1], boundaries, indexes)
        line1, line2, mail_city, mail_state, mail_zip = mailing(attrs)
        feature = market.empty_feature(
            fips="47093",
            county="Knox",
            state="Tennessee",
            markets=["Knoxville"],
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source="kgis-parcel-search",
            owner=clean(attrs.get("OWNER")) or clean(attrs.get("KGIS_OWNER")) or clean(attrs.get("ACCELA_OWNER")),
            situs=situs(attrs),
            zoning=designation["zoningCode"],
            dor=clean(attrs.get("LANDUSE")),
            sale_price=sale_price(attrs.get("PURCHASE_PRICE")),
            sale_date=knox_date(attrs.get("SALE_DATE")),
            sale_qualified=clean(attrs.get("VALIDITY_FLAG")),
            market_value=money(attrs.get("APPRAISED_TOTAL")),
            assessed=money(attrs.get("ASSESSED_TOTAL")),
            mail1=line1,
            mail2=line2,
            mail_city=mail_city,
            mail_state=mail_state,
            mail_zip=mail_zip,
        )
        props = feature["properties"]
        props["zoningDistrict"] = designation["zoningDistrict"]
        props["jurisdictionPrefix"] = designation["prefix"]
        props["jurisdictionCode"] = designation["prefix"]
        props["flu"] = designation["flu"]
        props["appraiserUrl"] = (
            "https://propertyinfo.knoxcountytn.gov/Datalets/Datalet.aspx?ParcelID="
            + urllib.parse.quote(parcel_id)
            + "&UseSearch=yes"
        )
        props["dataGaps"] = designation["dataGaps"]
        props["municipality"] = designation["name"]
        props["baseParcelId"] = clean(attrs.get("BASE_PARCELID"))
        props["pbaid"] = clean(attrs.get("PBAID"))
        props["recordedAcreage"] = market.num(attrs.get("RECORDED_AREA"))
        props["tax"]["appraisedLand"] = money(attrs.get("APPRAISED_LAND"))
        props["tax"]["appraisedBuilding"] = money(attrs.get("APPRAISED_BLDG"))
        props["mailingAddress"]["zip"] = mail_zip
        props["lastSale"]["datePurchased"] = knox_date(attrs.get("DATE_PURCHASED"))
        props["lastSale"]["deedBook"] = clean(attrs.get("DEED_BOOK"))
        props["lastSale"]["deedPage"] = clean(attrs.get("DEED_PAGE"))
        props["lastSale"]["odocBook"] = clean(attrs.get("ODOC_BOOK"))
        props["lastSale"]["odocPage"] = clean(attrs.get("ODOC_PAGE"))
        previous = by_id.get(parcel_id)
        if previous is None or (props["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = sorted(by_id.values(), key=lambda item: item["properties"].get("acreage") or 0, reverse=True)
    for feature in features:
        municipalities[feature["properties"]["jurisdictionPrefix"] and {
            "KNOX-CITY": "knoxville",
            "FARRAGUT": "farragut",
            "KNOX-COUNTY": "unincorporated",
        }[feature["properties"]["jurisdictionPrefix"]]] += 1
        if feature["properties"].get("zoningCode"):
            zoning_joined += 1
        if feature["properties"].get("flu"):
            flu_joined += 1
    stats = {
        "blocked": False,
        "count": len(features),
        "sourceCount": len(rows),
        "dropped": dropped,
        "zoningJoined": zoning_joined,
        "fluJoined": flu_joined,
        "municipalities": municipalities,
        "queryUrl": PORTAL_QUERY,
    }
    return features, stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-overlays", action="store_true")
    args = parser.parse_args()
    overlays_ready = (OUT / "zoning.geojson").exists() and (OUT / "municipalities.geojson").exists()
    if args.refresh_overlays or not overlays_ready:
        overlays = download_overlays()
        boundaries = overlays.pop("boundaries")
        overlay_summary = overlays
    else:
        print("reusing overlay fixtures", flush=True)
        boundaries = load_boundaries()
        overlay_summary = {key: json.loads((OUT / "summary.json").read_text())[key] for key in ("zoning", "countyFlu", "farragutZoning")}
    print("probing parcel access", flush=True)
    global_search = probe(f"{PARCEL_QUERY}?where=1%3D1&returnCountOnly=true&f=json")
    property_layer = probe(f"{PROPERTY_QUERY}?where=1%3D1&returnCountOnly=true&f=json")
    export = probe(PARCEL_EXPORT)
    city_flu = probe(CITY_FLU)
    one_year = probe(ONE_YEAR)
    portal = probe(f"{PORTAL_QUERY}?where={urllib.parse.quote(PARCEL_WHERE)}&returnCountOnly=true&f=json")
    if portal.get("status") != 200:
        raise SystemExit(f"Parcel Search proxy did not answer: {portal}")
    features, parcel_stats = download_parcels(boundaries)
    if parcel_stats["count"] < 4000:
        raise SystemExit(f"Expected about 4569 Knox parcels, kept {parcel_stats['count']}")
    parcel_stats["globalSearchStatus"] = global_search.get("status")
    parcel_stats["propertyStatus"] = property_layer.get("status")
    parcel_stats["exportStatus"] = export.get("status")
    parcel_stats["portalStatus"] = portal.get("status")
    samples = sample_joins(boundaries)
    summary = {
        "checkedAt": CHECKED,
        "fips": "47093",
        "impact": False,
        "parcel": parcel_stats,
        "cityFlu": {
            "futureLandUseStatus": city_flu.get("status"),
            "futureLandUseLabel": access_label(city_flu),
            "oneYearPlanStatus": one_year.get("status"),
            "oneYearPlanLabel": access_label(one_year),
            "gap": True,
        },
        "samples": samples,
        **overlay_summary,
    }
    (OUT / "access.json").write_text(
        json.dumps(
            {
                "checkedAt": CHECKED,
                "portal": portal,
                "globalSearch": global_search,
                "property": property_layer,
                "export": export,
                "cityFlu": city_flu,
                "oneYearPlan": one_year,
            },
            indent=2,
        )
        + "\n"
    )
    write_docs(summary)
    county = {"name": "Knox", "state": "Tennessee", "fips": "47093"}
    path, lookup, tiles = market.write_tiles(county, features)
    market.county_row(
        county,
        ["Knoxville"],
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source="kgis-parcel-search",
        query_url=PORTAL_QUERY,
        gaps=KNOX_GAPS,
        source_count=parcel_stats["sourceCount"],
        dropped=parcel_stats["dropped"],
        tile_count=tiles,
    )
    market.rebuild_indexes(json.loads(market.CATALOG_PATH.read_text()))
    print(
        f"Knox parcels {len(features)} zoning {parcel_stats['zoningJoined']} flu {parcel_stats['fluJoined']} {parcel_stats['municipalities']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
