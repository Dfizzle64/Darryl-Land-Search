#!/usr/bin/env python3
"""Join HUD/Treasury Qualified Opportunity Zone tracts onto the parcel fixture.

Primary source (public, no paid vendors):
  HUD GIS Opportunity Zones FeatureServer layer 13
  (Treasury-certified QOZs for IRC §§ 1400Z-1 / 1400Z-2; 2010 Census tracts)

Fallback:
  Orange County open-data Opportunity Zones (Public_Dynamic / 61), which is the
  same 2010 tract set as designated for this county.

Join is centroid-in-polygon against the official 2010 QOZ polygons — not ACS
2020 tract GEOIDs, which do not match the designation vintage.

Usage:
  python3 scripts/join_oz.py
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARCELS = ROOT / "data" / "fixtures" / "parcels.geojson"
META = ROOT / "data" / "fixtures" / "meta.json"
OZ_POLYS = ROOT / "data" / "fixtures" / "opportunity-zones.geojson"
OZ_LOOKUP = ROOT / "data" / "fixtures" / "oz-lookup.json"

HUD_OZ_URL = "https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/FeatureServer/13/query"
OC_OZ_URL = "https://ocgis4.ocfl.net/arcgis/rest/services/Public_Dynamic/MapServer/61/query"

ORANGE_COUNTY_FIPS = "12095"
COORD_PRECISION = 5  # ~1.1 m; keeps the overlay fixture small enough for git


def fetch_json(url: str, params: dict | None = None, timeout: int = 60, retries: int = 3) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "orange-county-mf-pilot/0.3"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def round_coords(value, precision: int = COORD_PRECISION):
    if isinstance(value, (int, float)):
        return round(float(value), precision)
    if isinstance(value, list):
        return [round_coords(item, precision) for item in value]
    return value


def simplify_feature(feature: dict) -> dict:
    geom = feature.get("geometry") or {}
    props = feature.get("properties") or {}
    geoid = str(props.get("GEOID10") or props.get("geoid") or "").strip()
    tract = str(props.get("TRACT") or props.get("tract") or geoid[-6:] if len(geoid) >= 6 else "").strip()
    rural_raw = props.get("Rural") or props.get("rural")
    rural = None
    if isinstance(rural_raw, str) and rural_raw.strip():
        rural = rural_raw.strip().upper() in {"Y", "YES", "1", "TRUE"}
    name = tract_name(tract, geoid)
    county, state = county_state_from_source(props, geoid)
    return {
        "type": "Feature",
        "id": geoid,
        "properties": {
            "id": geoid,
            "tractGeoid": geoid,
            "tract": tract or None,
            "name": name,
            "rural": rural,
            "county": county,
            "state": state,
        },
        "geometry": {
            "type": geom.get("type"),
            "coordinates": round_coords(geom.get("coordinates") or []),
        },
    }


def county_state_from_source(props: dict, geoid: str) -> tuple[str | None, str | None]:
    """Orange County designated overlay is the HUD extract for state 12, county 095."""
    state_fips = str(props.get("STATE") or "")
    county_fips = str(props.get("COUNTY") or "")
    if county_fips.isdigit():
        county_fips = county_fips.zfill(3)
    state_name = props.get("STATE_NAME") if isinstance(props.get("STATE_NAME"), str) else None
    if geoid.startswith("12095") or (state_fips == "12" and county_fips == "095"):
        return "Orange", state_name or "Florida"
    return None, state_name


def tract_name(tract: str, geoid: str) -> str:
    digits = "".join(ch for ch in tract if ch.isdigit()) or (geoid[-6:] if geoid else "")
    if not digits:
        return geoid or "Opportunity Zone"
    value = int(digits)
    if value % 100 == 0:
        pretty = str(value // 100)
    else:
        pretty = f"{value / 100:.2f}".rstrip("0")
    return f"Census tract {pretty}"


def fetch_hud_zones() -> tuple[list[dict], str]:
    data = fetch_json(
        HUD_OZ_URL,
        {
            "where": "STATE='12' AND COUNTY='095'",
            "outFields": "GEOID10,STATE,COUNTY,TRACT,STATE_NAME,Rural",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )
    if data.get("error"):
        raise RuntimeError(data["error"])
    features = [simplify_feature(feat) for feat in data.get("features") or [] if feat.get("geometry")]
    features = [feat for feat in features if feat["properties"]["tractGeoid"]]
    if not features:
        raise RuntimeError("HUD Opportunity Zone query returned no Orange County polygons")
    return features, HUD_OZ_URL.replace("/query", "")


def fetch_oc_zones() -> tuple[list[dict], str]:
    data = fetch_json(
        OC_OZ_URL,
        {
            "where": "1=1",
            "outFields": "GEOID10,NAME10,TRACT",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )
    if data.get("error"):
        raise RuntimeError(data["error"])
    features = [simplify_feature(feat) for feat in data.get("features") or [] if feat.get("geometry")]
    features = [feat for feat in features if feat["properties"]["tractGeoid"]]
    if not features:
        raise RuntimeError("Orange County Opportunity Zone query returned no polygons")
    return features, OC_OZ_URL.replace("/query", "")


def point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        intersects = (yi > y) != (yj > y)
        if intersects:
            denom = (yj - yi) if (yj - yi) != 0 else 1e-20
            x_at = (xj - xi) * (y - yi) / denom + xi
            if x < x_at:
                inside = not inside
        j = i
    return inside


def point_in_polygon_rings(x: float, y: float, rings: list) -> bool:
    if not rings:
        return False
    if not point_in_ring(x, y, rings[0]):
        return False
    for hole in rings[1:]:
        if point_in_ring(x, y, hole):
            return False
    return True


def point_in_geometry(x: float, y: float, geometry: dict | None) -> bool:
    if not geometry:
        return False
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        return point_in_polygon_rings(x, y, coords)
    if kind == "MultiPolygon":
        return any(point_in_polygon_rings(x, y, poly) for poly in coords)
    return False


def join_centroid(lon: float, lat: float, zones: list[dict]) -> dict | None:
    for zone in zones:
        if point_in_geometry(lon, lat, zone.get("geometry")):
            return zone["properties"]
    return None


def main() -> None:
    source_url = HUD_OZ_URL.replace("/query", "")
    source_id = "hud-fs-13"
    try:
        zones, source_url = fetch_hud_zones()
        source_id = "hud-fs-13"
        print(f"HUD Opportunity Zones: {len(zones)} Orange County tracts")
    except Exception as hud_exc:  # noqa: BLE001
        print(f"HUD fetch failed ({hud_exc}); trying Orange County GIS fallback")
        zones, source_url = fetch_oc_zones()
        source_id = "ocfl-public-dynamic-61"
        print(f"Orange County Opportunity Zones: {len(zones)} tracts")

    collection = json.loads(PARCELS.read_text())
    features = collection.get("features") or []
    print(f"Joining Opportunity Zones onto {len(features)} parcels")

    lookup: dict[str, dict | None] = {}
    in_count = 0
    missing_centroid = 0
    for feat in features:
        props = feat.setdefault("properties", {})
        pid = props.get("id") or ""
        centroid = props.get("centroid") or []
        if len(centroid) != 2:
            props["opportunityZone"] = None
            lookup[pid] = None
            missing_centroid += 1
            continue
        hit = join_centroid(float(centroid[0]), float(centroid[1]), zones)
        if hit:
            info = {
                "inOpportunityZone": True,
                "tractGeoid": hit.get("tractGeoid"),
                "tractName": hit.get("name"),
                "source": source_id,
            }
            in_count += 1
        else:
            info = {
                "inOpportunityZone": False,
                "tractGeoid": None,
                "tractName": None,
                "source": source_id,
            }
        props["opportunityZone"] = info
        lookup[pid] = info

    overlay = {
        "type": "FeatureCollection",
        "name": "orange-county-fl-opportunity-zones",
        "features": zones,
    }
    OZ_POLYS.write_text(json.dumps(overlay, separators=(",", ":")))
    PARCELS.write_text(json.dumps(collection, separators=(",", ":")))

    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    OZ_LOOKUP.write_text(
        json.dumps(
            {
                "generatedAt": generated_at,
                "parcelCount": len(features),
                "inOpportunityZoneCount": in_count,
                "missingCentroid": missing_centroid,
                "tractCount": len(zones),
                "source": source_url,
                "sourceId": source_id,
                "joinMethod": "parcel-centroid-in-2010-qoz-polygon",
                "notes": [
                    "Qualified Opportunity Zones are 2010 Census tracts certified by Treasury.",
                    "Do not join via ACS 2020 tract GEOIDs; those vintages do not match.",
                ],
                "byParcel": lookup,
            },
            indent=2,
        )
    )

    if META.exists():
        meta = json.loads(META.read_text())
        meta["ozJoinedAt"] = generated_at
        meta["ozJoinedCount"] = in_count
        meta["ozTractCount"] = len(zones)
        meta["ozSource"] = source_url
        sources = meta.get("sources") or {}
        sources["opportunityZones"] = source_url
        meta["sources"] = sources
        notes = meta.get("notes") or []
        oz_note = (
            "Opportunity Zones are HUD/Treasury QOZ polygons (2010 tracts) joined by parcel centroid. "
            "ACS 2020 tract IDs are not used for the join."
        )
        if oz_note not in notes:
            notes.append(oz_note)
        meta["notes"] = notes
        META.write_text(json.dumps(meta, indent=2))

    print(
        json.dumps(
            {
                "inOpportunityZone": in_count,
                "total": len(features),
                "tracts": len(zones),
                "source": source_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
