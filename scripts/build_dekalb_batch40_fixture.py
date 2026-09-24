#!/usr/bin/env python3
"""Build the DeKalb County batch-40 screening fixture.

Reads 13089-<parcelId>.json research files (school, flood, utility only) and
writes data/fixtures/screening/dekalb-batch40.json. Opportunity Zone, income,
and AADT are not copied. Georgia CCRPI scores stay numeric — no A–F letters.
A base flood elevation is copied only when STATIC_BFE is a real number.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "fixtures" / "screening" / "dekalb-batch40.json"
LOOKUP = ROOT / "data" / "fixtures" / "market-parcels" / "counties" / "13089" / "lookup.json"


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


def proxy_for(provider: str | None) -> str:
    if provider and "City of Atlanta" in provider:
        return "atlanta-dwm"
    return "dekalb-dwm"


def compact(record: dict) -> dict:
    school = layer(record, "school")["detail"]
    flood = layer(record, "flood")["detail"]
    utility = layer(record, "utility")["detail"]
    schools = []
    for zone in school["zoned"]:
        score = zone.get("ccrpi_2025")
        if not isinstance(score, (int, float)):
            raise ValueError(f"{record['parcel_id']} missing CCRPI for {zone.get('name')}")
        system_id = blank(zone.get("system_id")) or "644"
        school_id = blank(zone.get("school_id"))
        schl_num = blank(zone.get("schl_num"))
        gadoe = f"{system_id}-{school_id}" if school_id else schl_num
        if not gadoe:
            raise ValueError(f"{record['parcel_id']} missing a school id for {zone.get('name')}")
        distance = zone.get("distance_mi")
        schools.append(
            {
                "level": zone["level"],
                "name": zone["name"],
                "schoolId": gadoe,
                "ccrpi": score,
                "distanceMiles": float(distance) if isinstance(distance, (int, float)) else None,
            }
        )
    if len(schools) != 3:
        raise ValueError(f"{record['parcel_id']} expected 3 zoned schools, got {len(schools)}")
    sewer_provider = blank(utility.get("sewer_provider"))
    sewer_gap = utility.get("sewer_status") == "gap_public_gis" or not sewer_provider
    electric = utility.get("electric_provider")
    if not electric:
        raise ValueError(f"{record['parcel_id']} missing an electric provider")
    also = [name for name in utility.get("electric_hifld_all") or [] if name != electric]
    if utility.get("gas_provider") not in (None, ""):
        raise ValueError(f"{record['parcel_id']} has a gas provider; this join leaves gas unknown")
    water_provider = utility.get("water_provider")
    if not water_provider:
        raise ValueError(f"{record['parcel_id']} missing a water provider")
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
            "datum": blank(flood.get("v_datum")) if real_bfe(flood.get("static_bfe")) is not None else None,
        },
        "water": {
            "provider": water_provider,
            "fromBoundary": bool(utility.get("atl_dwm_polygon_hit")),
            "proxy": proxy_for(water_provider),
        },
        "sewer": {
            "provider": None if sewer_gap else sewer_provider,
            "gap": sewer_gap,
            "proxy": proxy_for(None if sewer_gap else sewer_provider),
        },
        "electric": {"provider": electric, "also": also},
        "gas": {"provider": None, "gap": True},
    }


def main() -> None:
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dekalb-enrich")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    lookup = json.loads(LOOKUP.read_text())
    files = sorted(source.glob("13089-*.json"))
    parcels = {}
    zones: Counter[str] = Counter()
    for path in files:
        record = json.loads(path.read_text())
        if record.get("county_fips") != "13089":
            raise SystemExit(f"{path.name} is not DeKalb County")
        row = compact(record)
        if row["parcelId"] not in lookup:
            raise SystemExit(f"{row['parcelId']} is not in the DeKalb parcel lookup")
        parcels[row["parcelId"]] = row
        zones[row["flood"]["zone"]] += 1
    if len(parcels) != 40:
        raise SystemExit(f"expected 40 parcels, got {len(parcels)}")
    payload = {
        "countyFips": "13089",
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
