"""Precompute a small OZ 2.0 eligible-only overlay for zooms 4–7.

Dissolves known eligible tract polygons by state and rural/urban, then
simplifies. Tracts that are not on an eligibility fixture are omitted.
South Carolina keeps the governor-nominated GEOID list only.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"
OUT = FIXTURES / "oz2-eligible-overview.geojson"
NOMINATED = ROOT / "data" / "oz" / "sc-oz2-nominated-official-sccommerce-2026-09-23.csv"

# ~2 km before union, ~4 km after. Far enough for a Southeast view.
PRE_TOLERANCE = 0.02
POST_TOLERANCE = 0.04

STATE_BY_FIPS = {
    "01": "Alabama",
    "05": "Arkansas",
    "12": "Florida",
    "13": "Georgia",
    "28": "Mississippi",
    "37": "North Carolina",
    "45": "South Carolina",
    "47": "Tennessee",
}


def nominated_geoids() -> set[str]:
    with NOMINATED.open(newline="") as handle:
        rows = csv.DictReader(handle)
        return {row["geoid"].strip() for row in rows if row.get("geoid")}


def state_of(props: dict) -> str | None:
    state = props.get("state")
    if isinstance(state, str) and state.strip():
        return state.strip()
    geoid = str(props.get("tractGeoid") or "")
    return STATE_BY_FIPS.get(geoid[:2])


def show_tract(props: dict, nominated: set[str]) -> bool:
    geoid = str(props.get("tractGeoid") or "")
    if len(geoid) < 11:
        return False
    state = state_of(props)
    if state == "South Carolina" or geoid.startswith("45"):
        return geoid in nominated
    return True


def round_coords(value, places: int = 4):
    if isinstance(value, float):
        return round(value, places)
    if isinstance(value, list):
        return [round_coords(item, places) for item in value]
    return value


def main() -> None:
    nominated = nominated_geoids()
    groups: dict[tuple[str, bool], list] = {}
    seen: set[str] = set()
    skipped_sc = 0
    for path in (
        FIXTURES / "oz2-rural-markets.geojson",
        FIXTURES / "oz2-eligible-packs.geojson",
        FIXTURES / "oz2-eligible.geojson",
    ):
        collection = json.loads(path.read_text())
        for feature in collection["features"]:
            props = feature.get("properties") or {}
            geoid = str(props.get("tractGeoid") or "")
            if geoid in seen:
                continue
            if not show_tract(props, nominated):
                if geoid.startswith("45"):
                    skipped_sc += 1
                continue
            state = state_of(props)
            if not state:
                continue
            geom = shape(feature["geometry"])
            if geom.is_empty:
                continue
            geom = make_valid(geom).simplify(PRE_TOLERANCE, preserve_topology=True)
            if geom.is_empty:
                continue
            seen.add(geoid)
            rural = props.get("rural") is True
            groups.setdefault((state, rural), []).append(geom)

    features = []
    for (state, rural), geoms in sorted(groups.items(), key=lambda item: (item[0][0], not item[0][1])):
        merged = make_valid(unary_union(geoms)).simplify(POST_TOLERANCE, preserve_topology=True)
        if merged.is_empty:
            continue
        geometry = mapping(merged)
        geometry["coordinates"] = round_coords(geometry["coordinates"])
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "state": state,
                    "rural": rural,
                    "eligible": True,
                    "overview": True,
                    "tractCount": len(geoms),
                },
                "geometry": geometry,
            }
        )

    payload = {
        "type": "FeatureCollection",
        "name": "oz2-eligible-overview",
        "features": features,
    }
    text = json.dumps(payload, separators=(",", ":"))
    OUT.write_text(text)
    print(
        f"wrote {OUT.name}: features={len(features)} tracts={len(seen)} "
        f"skipped_sc={skipped_sc} bytes={OUT.stat().st_size}"
    )


if __name__ == "__main__":
    main()
