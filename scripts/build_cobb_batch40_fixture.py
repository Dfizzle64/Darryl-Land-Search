#!/usr/bin/env python3
"""Build the Cobb County batch-40 screening fixture.

Reads 13067-<parcelId>.json research files (school, flood, utility only) and
writes data/fixtures/screening/cobb-batch40.json. Opportunity Zone, income,
and AADT are not copied. Georgia CCRPI scores stay numeric — no A–F letters.
A base flood elevation is copied only when STATIC_BFE is a real number.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "fixtures" / "screening" / "cobb-batch40.json"


def blank(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def real_bfe(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number <= -999:
        return None
    return number


def layer(record: dict, name: str) -> dict:
    for item in record["layers"]:
        if item.get("layer") == name:
            return item
    raise KeyError(name)


def compact(record: dict) -> dict:
    school = layer(record, "school")["detail"]
    flood = layer(record, "flood")["detail"]
    utility = layer(record, "utility")["detail"]
    schools = []
    for zone in school["zoned"]:
        score = zone.get("ccrpi_2025")
        if not isinstance(score, (int, float)):
            raise ValueError(f"{record['parcel_id']} missing CCRPI for {zone.get('name')}")
        schools.append(
            {
                "level": zone["level"],
                "name": zone["name"],
                "schoolId": zone["schl_num"],
                "ccrpi": score,
                "distanceMiles": zone.get("distance_mi"),
            }
        )
    sewer_provider = blank(utility.get("sewer_provider"))
    sewer_gap = utility.get("sewer_status") == "gap_public_gis" or not sewer_provider
    electric = utility.get("electric_provider")
    also = [name for name in utility.get("electric_hifld_all") or [] if name != electric]
    if utility.get("gas_provider") not in (None, ""):
        raise ValueError(f"{record['parcel_id']} has a gas provider; this join leaves gas unknown")
    return {
        "parcelId": record["parcel_id"],
        "assignment": school.get("assignment_method"),
        "district": school.get("district"),
        "schools": schools,
        "flood": {
            "zone": flood["fld_zone"],
            "subtype": blank(flood.get("zone_subty")),
            "sfha": bool(flood.get("sfha")),
            "staticBfe": real_bfe(flood.get("static_bfe")),
            "datum": blank(flood.get("v_datum")),
        },
        "water": {
            "provider": utility["water_provider"],
            "fromBoundary": bool(utility.get("water_boundary_raw")),
        },
        "sewer": {
            "provider": None if sewer_gap else sewer_provider,
            "gap": sewer_gap,
            "notAnticipated": bool(utility.get("sewer_not_anticipated")),
        },
        "electric": {"provider": electric, "also": also},
        "gas": {"provider": None, "gap": True},
    }


def main() -> None:
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/cobb-batch40")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    files = sorted(source.glob("13067-*.json"))
    parcels = {}
    zones: Counter[str] = Counter()
    for path in files:
        record = json.loads(path.read_text())
        if record.get("county_fips") != "13067":
            raise SystemExit(f"{path.name} is not Cobb County")
        row = compact(record)
        parcels[row["parcelId"]] = row
        zones[row["flood"]["zone"]] += 1
    if len(parcels) != 40:
        raise SystemExit(f"expected 40 parcels, got {len(parcels)}")
    payload = {
        "countyFips": "13067",
        "market": "Atlanta",
        "asOf": "2026-09-23",
        "schoolYear": "2025",
        "parcelCount": 40,
        "letterGrades": "not_published_by_ga_post_2022_23",
        "omitted": ["opportunityZone", "income", "aadt"],
        "floodZoneCounts": dict(zones),
        "parcels": parcels,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {out} parcels={len(parcels)} zones={dict(zones)}")


if __name__ == "__main__":
    main()
