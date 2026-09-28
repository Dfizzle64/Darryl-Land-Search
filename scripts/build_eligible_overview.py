"""Precompute a small OZ 2.0 eligible-only overlay for zooms 4–7.

One simplified polygon per eligible tract, not a state dissolve. Dissolving
dropped tract GEOID and ACS income, so the median-income slider could not
hide individual tracts. Each feature keeps tractGeoid, the rural flag, and
medianHouseholdIncome when ACS 5-year 2020–2024 B19013 has a positive
estimate for that 2020 GEOID. Tracts missing from the table omit the
property (unknown income, not zero).

Tracts that are not on an eligibility fixture are omitted. South Carolina
keeps the governor-nominated GEOID list only.
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
MS_STATEWIDE = FIXTURES / "oz2-ms-statewide.geojson"
ACS = FIXTURES / "acs-b19013-tracts.json"
NOMINATED = ROOT / "data" / "oz" / "sc-oz2-nominated-official-sccommerce-2026-09-23.csv"

# ~2 km. Enough for a Southeast view at zooms 4–7; detail geometry takes over at 8.
TOLERANCE = 0.02

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


def income_by_geoid() -> dict[str, int]:
    table = json.loads(ACS.read_text())
    found: dict[str, int] = {}
    for geoid, row in (table.get("tracts") or {}).items():
        estimate = row.get("e") if isinstance(row, dict) else None
        if isinstance(estimate, (int, float)) and estimate > 0:
            found[str(geoid)] = int(estimate)
    return found


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
    if isinstance(value, (list, tuple)):
        return [round_coords(item, places) for item in value]
    return value


def polygonal(geom):
    geom = make_valid(geom)
    if geom.is_empty:
        return None
    if geom.geom_type == "GeometryCollection":
        parts = [part for part in geom.geoms if part.geom_type in ("Polygon", "MultiPolygon")]
        if not parts:
            return None
        geom = unary_union(parts)
    if geom.geom_type not in ("Polygon", "MultiPolygon") or geom.is_empty:
        return None
    return geom


def simplified(geom):
    base = make_valid(geom)
    out = polygonal(base.simplify(TOLERANCE, preserve_topology=True))
    if out is None:
        out = polygonal(base.simplify(TOLERANCE / 4, preserve_topology=True))
    if out is None:
        out = polygonal(base)
    return out


def main() -> None:
    nominated = nominated_geoids()
    incomes = income_by_geoid()
    seen: set[str] = set()
    skipped_sc = 0
    features = []
    sources = (
        FIXTURES / "oz2-rural-markets.geojson",
        FIXTURES / "oz2-eligible-packs.geojson",
        FIXTURES / "oz2-eligible.geojson",
        MS_STATEWIDE,
    )
    for path in sources:
        if not path.exists():
            raise RuntimeError(f"Missing eligible-tract fixture {path}")
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
            if props.get("rural") is not True and props.get("rural") is not False:
                continue
            geom = simplified(shape(feature["geometry"]))
            if geom is None:
                continue
            seen.add(geoid)
            geometry = mapping(geom)
            geometry["coordinates"] = round_coords(geometry["coordinates"])
            properties: dict = {
                "tractGeoid": geoid,
                "state": state,
                "rural": props.get("rural") is True,
                "eligible": True,
                "overview": True,
            }
            income = incomes.get(geoid)
            if income is not None:
                properties["medianHouseholdIncome"] = income
            features.append({"type": "Feature", "properties": properties, "geometry": geometry})

    features.sort(key=lambda feature: (feature["properties"]["state"], not feature["properties"]["rural"], feature["properties"]["tractGeoid"]))
    payload = {
        "type": "FeatureCollection",
        "name": "oz2-eligible-overview",
        "features": features,
    }
    text = json.dumps(payload, separators=(",", ":"))
    OUT.write_text(text)
    known = sum(1 for feature in features if "medianHouseholdIncome" in feature["properties"])
    print(
        f"wrote {OUT.name}: features={len(features)} tracts={len(seen)} "
        f"with_income={known} unknown_income={len(features) - known} "
        f"skipped_sc={skipped_sc} bytes={OUT.stat().st_size}"
    )


if __name__ == "__main__":
    main()
