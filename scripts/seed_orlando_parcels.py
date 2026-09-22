#!/usr/bin/env python3
"""Seed partitioned Orlando ~90-min shed parcel fixtures from public GIS.

Primary source: Florida DOH EHWATER Parcels MapServer (FDOR NAL attributes).
Orange County keeps the richer OCPA pilot fixture and is copied into the
partition set with county metadata.

This writes a *filtered demo subset* (acreage + rural-tract windows), not a
multi-GB full-county dump. Re-run anytime:

  npm run seed:parcels:orlando

Optional flags:
  --per-county N     max features per county (default 180)
  --min-acres X      minimum acreage filter (default 1.0)
  --county NAME      only one county
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "fixtures" / "orlando-parcels"
SOURCES = ROOT / "data" / "orlando-parcel-sources.json"
RURAL_CSV = ROOT / "data" / "oz2-7markets-90min-rural-eligible.csv"
ORANGE_PARCELS = ROOT / "data" / "fixtures" / "parcels.geojson"
RURAL_GEOJSON = ROOT / "data" / "fixtures" / "oz2-rural-markets.geojson"
META_OUT = OUT_DIR / "meta.json"

DOH_BASE = "https://gis.floridahealth.gov/server/rest/services/EHWATER/Parcels/MapServer"
DOH_FIELDS = [
    "PARCEL_ID",
    "OWN_NAME",
    "PHY_ADDR1",
    "PHY_ADDR2",
    "PHY_CITY",
    "PHY_ZIPCD",
    "LND_SQFOOT",
    "JV",
    "AV_SD",
    "TV_SD",
    "DOR_UC",
    "SALE_PRC1",
    "SALE_YR1",
    "SALE_MO1",
    "QUAL_CD1",
    "OWN_ADDR1",
    "OWN_ADDR2",
    "OWN_CITY",
    "OWN_STATE",
    "OWN_ZIPCD",
    "CO_NO",
]

# Pad around rural tract Gazetteer points (degrees ≈ miles).
TRACT_PAD = 0.045  # ~3 miles
SAMPLE_WINDOWS: dict[str, list[tuple[float, float, float, float]]] = {
    # Extra windows so counties with few/no rural tracts (Seminole) still get parcels.
    "Seminole": [(-81.38, 28.68, -81.28, 28.78), (-81.32, 28.74, -81.22, 28.84)],
    "Orange": [(-81.25, 28.52, -81.15, 28.62)],
}


def fetch_json(url: str, params: dict | None = None, timeout: int = 90, retries: int = 4) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/orlando-parcels"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last}")


def simplify_ring(coords: list[list[float]], tol: float = 0.00012) -> list[list[float]]:
    if len(coords) <= 4:
        return coords
    # Douglas-Peucker-ish 1-pass radial filter for fixture size.
    out = [coords[0]]
    for pt in coords[1:-1]:
        prev = out[-1]
        if abs(pt[0] - prev[0]) >= tol or abs(pt[1] - prev[1]) >= tol:
            out.append(pt)
    out.append(coords[-1])
    if out[0] != out[-1]:
        out.append(out[0])
    if len(out) < 4:
        return coords
    return [[round(x, 6), round(y, 6)] for x, y in out]


def rings_to_geojson(geom: dict | None) -> dict | None:
    if not geom or not geom.get("rings"):
        return None
    polygons: list[list[list[list[float]]]] = []
    current: list[list[list[float]]] = []
    for ring in geom["rings"]:
        coords = simplify_ring([[float(x), float(y)] for x, y in ring])
        if len(coords) < 4:
            continue
        # Positive area = outer ring (lon/lat shoelace sign depends on orientation).
        area = 0.0
        for i in range(len(coords) - 1):
            area += coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1]
        if not current or area > 0:
            if current:
                polygons.append(current)
            current = [coords]
        else:
            current.append(coords)
    if current:
        polygons.append(current)
    if not polygons:
        return None
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def centroid(geom: dict) -> tuple[float, float] | None:
    coords = geom["coordinates"]
    ring = coords[0] if geom["type"] == "Polygon" else coords[0][0]
    if len(ring) < 2:
        return None
    xs = [p[0] for p in ring[:-1]]
    ys = [p[1] for p in ring[:-1]]
    return (round(sum(xs) / len(xs), 6), round(sum(ys) / len(ys), 6))


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def zip_str(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(int(float(value))).zfill(5)[:5]
    except (TypeError, ValueError):
        return clean(value)


def sale_date(year: Any, month: Any) -> str | None:
    try:
        y = int(float(year))
        m = int(float(month)) if month not in (None, "", "0", 0) else 1
        if y < 1900 or y > 2100:
            return None
        return f"{y:04d}-{m:02d}-01"
    except (TypeError, ValueError):
        return None


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_feature(x: float, y: float, feature: dict) -> bool:
    geom = feature.get("geometry") or {}
    if geom.get("type") == "Polygon":
        rings = geom["coordinates"]
        if not point_in_ring(x, y, rings[0]):
            return False
        for hole in rings[1:]:
            if point_in_ring(x, y, hole):
                return False
        return True
    if geom.get("type") == "MultiPolygon":
        for poly in geom["coordinates"]:
            if point_in_ring(x, y, poly[0]) and not any(point_in_ring(x, y, h) for h in poly[1:]):
                return True
    return False


def load_orlando_rural_windows() -> dict[str, list[tuple[float, float, float, float]]]:
    windows: dict[str, list[tuple[float, float, float, float]]] = {k: list(v) for k, v in SAMPLE_WINDOWS.items()}
    with RURAL_CSV.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row["market"] != "Orlando" or row["state"] != "Florida":
                continue
            county = row["county"]
            lon = float(row["lon"])
            lat = float(row["lat"])
            windows.setdefault(county, []).append(
                (lon - TRACT_PAD, lat - TRACT_PAD, lon + TRACT_PAD, lat + TRACT_PAD)
            )
    return windows


def load_orlando_rural_polys() -> list[dict]:
    data = json.loads(RURAL_GEOJSON.read_text())
    out = []
    for feature in data["features"]:
        markets = feature["properties"].get("markets") or []
        if "Orlando" in markets:
            out.append(feature)
    return out


def normalize_doh(
    attrs: dict,
    geom: dict,
    county: dict,
) -> dict | None:
    geometry = rings_to_geojson(geom)
    if not geometry:
        return None
    center = centroid(geometry)
    if not center:
        return None
    parcel_id = clean(attrs.get("PARCEL_ID"))
    if not parcel_id:
        return None
    sqft = attrs.get("LND_SQFOOT")
    acreage = None
    try:
        if sqft is not None and float(sqft) > 0:
            acreage = round(float(sqft) / 43560.0, 4)
    except (TypeError, ValueError):
        acreage = None
    fips = county["fips"]
    feature_id = f"{fips}:{parcel_id}"
    price = attrs.get("SALE_PRC1")
    try:
        price_n = float(price) if price is not None else None
        if price_n is not None and price_n <= 0:
            price_n = None
    except (TypeError, ValueError):
        price_n = None
    return {
        "type": "Feature",
        "id": feature_id,
        "properties": {
            "id": feature_id,
            "parcelId": parcel_id,
            "countyFips": fips,
            "countyName": county["name"],
            "state": "Florida",
            "marketIds": ["Orlando"],
            "situsAddress": clean(attrs.get("PHY_ADDR1")),
            "situsCity": clean(attrs.get("PHY_CITY")),
            "situsZip": zip_str(attrs.get("PHY_ZIPCD")),
            "jurisdictionCode": None,
            "ownerName": clean(attrs.get("OWN_NAME")),
            "ownerName2": None,
            "propertyName": None,
            "zoningCode": None,
            "zoningDistrict": None,
            "jurisdictionPrefix": None,
            "dorCode": clean(attrs.get("DOR_UC")),
            "acreage": acreage,
            "centroid": list(center),
            "lastSale": {
                "date": sale_date(attrs.get("SALE_YR1"), attrs.get("SALE_MO1")),
                "price": price_n,
                "qualified": clean(attrs.get("QUAL_CD1")),
            },
            "tax": {
                "marketValue": _num(attrs.get("JV")),
                "assessedValue": _num(attrs.get("AV_SD")),
                "taxableValue": _num(attrs.get("TV_SD")),
                "taxes": None,
            },
            "mailingAddress": {
                "line1": clean(attrs.get("OWN_ADDR1")),
                "line2": clean(attrs.get("OWN_ADDR2")),
                "city": clean(attrs.get("OWN_CITY")),
                "state": clean(attrs.get("OWN_STATE")),
                "zip": zip_str(attrs.get("OWN_ZIPCD")),
            },
            "incomeTract": None,
            "incomeBlockGroup": None,
            "nearestRoad": None,
            "flu": None,
            "opportunityZone": None,
            "oz2Eligibility": None,
            "appraiserUrl": county.get("appraiserSearchUrl"),
            "source": f"fl-doh-ehwaters-{fips}",
            "dataGaps": county.get("gaps") or [],
        },
        "geometry": geometry,
    }


def _num(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def query_window(
    layer_id: int,
    bbox: tuple[float, float, float, float],
    min_sqft: float,
    page_size: int,
    max_records: int,
) -> list[dict]:
    url = f"{DOH_BASE}/{layer_id}/query"
    west, south, east, north = bbox
    features: list[dict] = []
    offset = 0
    while len(features) < max_records:
        params = {
            "where": f"LND_SQFOOT > {int(min_sqft)}",
            "geometry": json.dumps(
                {"xmin": west, "ymin": south, "xmax": east, "ymax": north, "spatialReference": {"wkid": 4326}}
            ),
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": ",".join(DOH_FIELDS),
            "returnGeometry": "true",
            "outSR": 4326,
            "resultOffset": offset,
            "resultRecordCount": min(page_size, max_records - len(features)),
            "f": "json",
        }
        data = fetch_json(url, params)
        if data.get("error"):
            raise RuntimeError(data["error"])
        batch = data.get("features") or []
        features.extend(batch)
        if not data.get("exceededTransferLimit") and len(batch) < params["resultRecordCount"]:
            break
        if not batch:
            break
        offset += len(batch)
        time.sleep(0.12)
    return features


def stamp_oz2(feature: dict, rural_polys: list[dict]) -> None:
    cx, cy = feature["properties"]["centroid"]
    for poly in rural_polys:
        if point_in_feature(cx, cy, poly):
            props = poly["properties"]
            feature["properties"]["oz2Eligibility"] = {
                "eligible": True,
                "rural": True,
                "tractGeoid": props.get("tractGeoid"),
                "tractName": props.get("name") or props.get("tract"),
                "designation": "eligible-for-nomination",
                "source": "rev-proc-2026-14",
            }
            return
    feature["properties"]["oz2Eligibility"] = {
        "eligible": False,
        "rural": None,
        "tractGeoid": None,
        "tractName": None,
        "designation": "not-eligible",
        "source": "rev-proc-2026-14",
    }


def copy_orange_pilot() -> list[dict]:
    data = json.loads(ORANGE_PARCELS.read_text())
    out = []
    for feature in data["features"]:
        props = dict(feature["properties"])
        props["countyFips"] = "12095"
        props["countyName"] = "Orange"
        props["state"] = "Florida"
        props["marketIds"] = ["Orlando"]
        props["appraiserUrl"] = "https://ocpaweb.ocpafl.org/site/parcelsearch"
        props.setdefault("dataGaps", [])
        # Keep original id; OCPA ids are unique within Orange.
        out.append(
            {
                "type": "Feature",
                "id": props["id"],
                "properties": props,
                "geometry": feature["geometry"],
            }
        )
    return out


def seed_county(
    county: dict,
    windows: list[tuple[float, float, float, float]],
    rural_polys: list[dict],
    per_county: int,
    min_acres: float,
) -> list[dict]:
    if county["name"] == "Orange":
        # Prefer OCPA pilot richness; still stamp county metadata.
        features = copy_orange_pilot()
        for feature in features:
            if feature["properties"].get("oz2Eligibility") is None:
                stamp_oz2(feature, rural_polys)
        return features

    min_sqft = min_acres * 43560.0
    layer_id = county["dohLayerId"]
    by_id: dict[str, dict] = {}
    per_window = max(40, per_county // max(1, len(windows)))
    for bbox in windows:
        raw = query_window(layer_id, bbox, min_sqft, page_size=100, max_records=per_window)
        for item in raw:
            feature = normalize_doh(item.get("attributes") or {}, item.get("geometry") or {}, county)
            if not feature:
                continue
            stamp_oz2(feature, rural_polys)
            by_id[feature["properties"]["id"]] = feature
            if len(by_id) >= per_county:
                break
        if len(by_id) >= per_county:
            break
        time.sleep(0.2)
    # Prefer larger acreage then rural-eligible for the ranked list.
    features = list(by_id.values())
    features.sort(
        key=lambda f: (
            1 if f["properties"].get("oz2Eligibility", {}).get("rural") else 0,
            f["properties"].get("acreage") or 0,
        ),
        reverse=True,
    )
    return features[:per_county]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-county", type=int, default=180)
    parser.add_argument("--min-acres", type=float, default=1.0)
    parser.add_argument("--county", type=str, default="")
    args = parser.parse_args()

    sources = json.loads(SOURCES.read_text())
    windows = load_orlando_rural_windows()
    rural_polys = load_orlando_rural_polys()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    meta_counties: list[dict] = []
    total = 0
    for county in sources["counties"]:
        if args.county and county["name"].lower() != args.county.lower():
            continue
        county_windows = windows.get(county["name"]) or SAMPLE_WINDOWS.get(county["name"]) or []
        if not county_windows:
            # County-wide fallback envelope from rural catalog notes — use a mid-county pad.
            print(f"skip {county['name']}: no windows")
            continue
        print(f"Seeding {county['name']} ({len(county_windows)} windows)…")
        features = seed_county(county, county_windows, rural_polys, args.per_county, args.min_acres)
        path = OUT_DIR / f"{county['fips']}.geojson"
        collection = {
            "type": "FeatureCollection",
            "name": f"orlando-shed-{county['name'].lower()}",
            "features": features,
        }
        path.write_text(json.dumps(collection, separators=(",", ":")))
        rural_n = sum(1 for f in features if (f["properties"].get("oz2Eligibility") or {}).get("rural"))
        meta_counties.append(
            {
                "name": county["name"],
                "fips": county["fips"],
                "featureCount": len(features),
                "ruralEligibleParcelCount": rural_n,
                "source": county["preferredSource"],
                "queryUrl": county["queryUrl"],
                "gaps": county.get("gaps") or [],
                "path": str(path.relative_to(ROOT)),
            }
        )
        total += len(features)
        print(f"  wrote {len(features)} features ({rural_n} rural-eligible centroids) → {path.name}")

    meta = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "market": "Orlando",
        "parcelCount": total,
        "perCountyCap": args.per_county,
        "minAcres": args.min_acres,
        "sourcesDoc": "data/orlando-parcel-sources.json",
        "notes": [
            "Partitioned demo fixtures for the Orlando ~90-minute county shed.",
            "Not a complete cadastral extract. Re-pull with npm run seed:parcels:orlando.",
            "Live viewport queries use the same DOH layers via /api/parcels?source=live.",
            "Zoning/FLU are Orange County OCPA pilot only; other counties degrade gracefully.",
        ],
        "counties": meta_counties,
    }
    META_OUT.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Done. {total} parcels across {len(meta_counties)} counties → {OUT_DIR}")


if __name__ == "__main__":
    main()
