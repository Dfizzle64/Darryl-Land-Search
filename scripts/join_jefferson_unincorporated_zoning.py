#!/usr/bin/env python3
"""Fill blank Jefferson County, Alabama zoning from the county unincorporated layer.

City codes already on a parcel are left alone. The layer is
DDS/FutureLandUse FeatureServer/4, named Zoning, field ZNCODE.
Description: authoritative zoning for unincorporated Jefferson County.
"""

from __future__ import annotations

import json
from pathlib import Path

from al_coastal_zoning import apply_spatial_overlay, polygon_record, strip_internal
from seed_state_aadt import page_query

ROOT = Path(__file__).resolve().parents[1]
COUNTY = ROOT / "data" / "fixtures" / "market-parcels" / "counties" / "01073"
TILES = COUNTY / "tiles"
URL = "https://jccgis.jccal.org/server/rest/services/DDS/FutureLandUse/FeatureServer/4/query"
SOURCE = "https://jccgis.jccal.org/server/rest/services/DDS/FutureLandUse/FeatureServer/4"


def load_zones() -> list[dict]:
    rows = page_query(
        URL,
        {
            "where": "ZNCODE IS NOT NULL AND ZNCODE<>''",
            "outFields": "ZNCODE,OBJECTID",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultRecordCount": 2000,
        },
    )
    polys = []
    for item in rows:
        code = str((item.get("attributes") or {}).get("ZNCODE") or "").strip()
        rings = (item.get("geometry") or {}).get("rings")
        if not code or not rings:
            continue
        record = polygon_record(rings, code, code)
        if record:
            polys.append(record)
    print(f"  zoning polygons {len(polys)}")
    return polys


def main() -> None:
    polys = load_zones()
    if len(polys) < 100:
        raise RuntimeError(f"Jefferson zoning layer returned only {len(polys)} polygons")
    kept_city: dict[str, str] = {}
    hits = 0
    parcels = 0
    for path in sorted(TILES.glob("*.geojson")):
        data = json.loads(path.read_text())
        features = data.get("features") or []
        for feature in features:
            props = feature["properties"]
            parcels += 1
            if props.get("zoningCode"):
                kept_city[props["parcelId"]] = props["zoningCode"]
        hits += apply_spatial_overlay(features, polys, city="Unincorporated Jefferson", replace=False)
        strip_internal(features)
        for feature in features:
            props = feature["properties"]
            prior = kept_city.get(props["parcelId"])
            if prior and props.get("zoningCode") != prior:
                raise RuntimeError(f"City zoning overwritten on {props['parcelId']}")
        path.write_text(json.dumps(data, separators=(",", ":")))
    blank = parcels - len(kept_city) - hits
    print(f"  parcels {parcels} city kept {len(kept_city)} unincorporated filled {hits} still blank {blank}")
    if hits < 100:
        raise RuntimeError(f"Unincorporated join only filled {hits} parcels")
    meta_path = COUNTY / "county.json"
    meta = json.loads(meta_path.read_text())
    note = (
        f"Unincorporated zoning is Jefferson County DDS/FutureLandUse FeatureServer/4 "
        f"({SOURCE}) field ZNCODE, joined by centroid where the parcel had no city code. "
        f"Filled {hits} parcels. {blank} parcels still have no zoning polygon. "
        f"City codes already on {len(kept_city)} parcels were not replaced."
    )
    gaps = [gap for gap in meta.get("gaps") or [] if "No zoning join" not in gap and "Unincorporated zoning is Jefferson" not in gap]
    gaps.append(note)
    meta["gaps"] = gaps
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    summary = {
        "source": SOURCE,
        "field": "ZNCODE",
        "polygons": len(polys),
        "cityKept": len(kept_city),
        "unincorporatedFilled": hits,
        "stillBlank": blank,
    }
    (COUNTY / "zoning-join.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("wrote", COUNTY / "zoning-join.json")


if __name__ == "__main__":
    main()
