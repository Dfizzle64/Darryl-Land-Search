#!/usr/bin/env python3
"""Knox County overlays, and parcels when KGIS anonymous query is open.

Knox is not a Comptroller IMPACT county. This script never calls maps.cot.tn.gov.

  python3 scripts/seed_knox.py

When GlobalSearch /query is still HTTP 401, parcel tiles are removed and the
county stays a documented ingestion blocker. Zoning, unincorporated future land
use, Farragut zoning, and municipality boundaries are still refreshed.
"""

from __future__ import annotations

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

## Parcel pull — ingestion blocker

Anonymous `GET` of KGIS `Maps/GlobalSearch/MapServer/0/query` returned **HTTP {parcel["globalSearchStatus"]}**. `Maps/Property/MapServer/2/query` returned **HTTP {parcel["propertyStatus"]}**. The MapServer export returned **HTTP {parcel["exportStatus"]}**. Geocortex Essentials publishes the field list for the same GlobalSearch layer, and a guest query is not supported. No tokenless countywide parcel polygon service or open-data download was found (`City_Parcel_Merged_HEX` is a hex grid, not the cadastre).

Parcel polygons and owner, mailing, situs, sale, and value attributes are **not** in `data/fixtures/market-parcels/counties/47093`. The previous IMPACT tile extract was removed so it is not presented as the Knox roll.

When anonymous query starts returning features, filter `CALCULATED_AREA` from 5 through 150 inclusive (`RECORDED_AREA` only when calculated acres are null) and map attributes with `mapKnoxParcel` in `src/lib/knox.ts`. Do not backfill from a paid vendor.

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


def main() -> None:
    overlays = download_overlays()
    boundaries = overlays.pop("boundaries")
    print("probing parcel access", flush=True)
    global_search = probe(f"{PARCEL_QUERY}?where=1%3D1&returnCountOnly=true&f=json")
    property_layer = probe(f"{PROPERTY_QUERY}?where=1%3D1&returnCountOnly=true&f=json")
    export = probe(PARCEL_EXPORT)
    city_flu = probe(CITY_FLU)
    one_year = probe(ONE_YEAR)
    samples = sample_joins(boundaries)
    parcel_open = global_search.get("status") == 200
    summary = {
        "checkedAt": CHECKED,
        "fips": "47093",
        "impact": False,
        "parcel": {
            "blocked": not parcel_open,
            "globalSearchStatus": global_search.get("status"),
            "propertyStatus": property_layer.get("status"),
            "exportStatus": export.get("status"),
            "queryUrl": PARCEL_QUERY,
        },
        "cityFlu": {
            "futureLandUseStatus": city_flu.get("status"),
            "futureLandUseLabel": access_label(city_flu),
            "oneYearPlanStatus": one_year.get("status"),
            "oneYearPlanLabel": access_label(one_year),
            "gap": True,
        },
        "samples": samples,
        **overlays,
    }
    probes = {
        "checkedAt": CHECKED,
        "globalSearch": global_search,
        "property": property_layer,
        "export": export,
        "cityFlu": city_flu,
        "oneYearPlan": one_year,
    }
    (OUT / "access.json").write_text(json.dumps(probes, indent=2) + "\n")
    write_docs(summary)

    catalog = json.loads(market.CATALOG_PATH.read_text())
    county = {"name": "Knox", "state": "Tennessee", "fips": "47093"}
    if parcel_open:
        raise SystemExit(
            "KGIS GlobalSearch query returned HTTP 200. Parcel paging is still an ingestion step: "
            "do not mark Knox complete from IMPACT, and do not invent polygons."
        )
    spec = market.spec_for(county)
    if spec.get("source") != "kgis-globalsearch-blocked":
        raise SystemExit(f"Knox spec drifted back to {spec.get('source')}")
    if "cot.tn.gov" in json.dumps(spec):
        raise SystemExit("Knox spec still points at Comptroller IMPACT")
    market.write_gap(county, ["Knoxville"], spec)
    market.rebuild_indexes(catalog)
    print("Knox parcel pull remains blocked. Overlays are on disk.", flush=True)
    print(json.dumps(samples, indent=2), flush=True)


if __name__ == "__main__":
    main()
